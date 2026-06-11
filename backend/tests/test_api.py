"""End-to-end HTTP smoke test: upload -> poll -> fetch result.

Uses a tiny synthetic video (no logos) so it exercises the full job lifecycle
and response contracts without depending on detection content. The real YOLO
model still loads, so this test is slower than the unit tests.
"""
from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture(scope="module")
def client():
    with TestClient(create_app()) as c:
        yield c


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_upload_poll_fetch(client, synthetic_video):
    with synthetic_video.open("rb") as fh:
        r = client.post(
            "/api/jobs",
            files={"video": ("synthetic.mp4", fh, "video/mp4")},
            data={
                "eventName": "Smoke Test",
                "audienceSize": "1000000",
                "placementType": "Live Broadcast TV",
                "cpmBase": "22",
            },
        )
    assert r.status_code == 201, r.text
    job_id = r.json()["jobId"]
    assert r.json()["status"] == "queued"

    # Poll until the in-process worker finishes (model load + a few frames).
    deadline = time.time() + 120
    status = None
    while time.time() < deadline:
        s = client.get(f"/api/jobs/{job_id}").json()
        status = s["status"]
        assert 0 <= s["progress"] <= 100
        if status in ("done", "error"):
            break
        time.sleep(1.0)

    assert status == "done", f"job ended as {status}: {s.get('error')}"
    analysis_id = s["analysisId"]
    assert analysis_id

    # Detail endpoint returns the full AnalysisResult contract.
    a = client.get(f"/api/analyses/{analysis_id}").json()
    for key in (
        "id", "eventName", "videoName", "videoDurationSeconds", "analyzedAt",
        "metadata", "logos", "bodyZones", "totalEmvUsd",
        "totalQualityExposureSeconds", "avgVisibilityScore",
    ):
        assert key in a, f"missing {key}"
    assert a["eventName"] == "Smoke Test"
    assert isinstance(a["logos"], list)
    assert len(a["bodyZones"]) == 18
    assert a["metadata"]["placementMultiplier"] == 1.0

    # List + CSV export.
    lst = client.get("/api/analyses").json()
    assert any(m["id"] == analysis_id for m in lst)
    csv = client.get(f"/api/analyses/{analysis_id}/export.csv")
    assert csv.status_code == 200
    assert "brand" in csv.text
