"""Recalculate stored analyses with the time-normalised EMV v2 formula.

The detection and exposure stages are deterministic inputs to pricing and are
already stored in ``result_json``.  This migration therefore re-prices existing
analyses without re-running video inference.  It is dry-run by default and
creates a timestamped database backup before ``--apply`` changes any row.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from app.pipeline.pricing import REFERENCE_SPOT_SECONDS, emv_for_logo


BACKEND_DIR = Path(__file__).resolve().parents[1]
DEFAULT_DB = BACKEND_DIR / "data" / "app.db"


def _reprice(result: dict) -> tuple[dict, float, float]:
    metadata = dict(result.get("metadata") or {})
    if metadata.get("emvModelVersion") == "time-normalised-v2":
        total = float(result.get("totalEmvUsd", 0.0))
        return result, total, total
    audience = int(metadata.get("audienceSize", 0))
    cpm = float(metadata.get("cpmBase", 0.0))
    placement = float(metadata.get("placementMultiplier", 1.0))

    old_total = float(result.get("totalEmvUsd", 0.0))
    new_total = 0.0
    logos = []
    for original in result.get("logos", []):
        logo = dict(original)
        quality_seconds = float(logo.get("qualityExposureSeconds", 0.0))
        # Existing v1 values were calculated from the unrounded internal
        # quality-seconds.  Dividing those values by 30 preserves that precision;
        # the public JSON only retains qualityExposureSeconds to two decimals.
        if "emvUsd" in logo:
            logo["emvUsd"] = round(float(logo["emvUsd"]) / REFERENCE_SPOT_SECONDS, 2)
        else:
            logo["emvUsd"] = round(
                emv_for_logo(
                    quality_seconds,
                    cpm_base=cpm,
                    audience_size=audience,
                    placement_mult=placement,
                ),
                2,
            )
        new_total += logo["emvUsd"]
        logos.append(logo)

    metadata["referenceSpotSeconds"] = REFERENCE_SPOT_SECONDS
    metadata["emvModelVersion"] = "time-normalised-v2"
    result = dict(result)
    result["metadata"] = metadata
    result["logos"] = logos
    result["totalEmvUsd"] = round(new_total, 2)
    return result, old_total, result["totalEmvUsd"]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()

    db_path = args.db.resolve()
    if not db_path.is_file():
        raise SystemExit(f"database not found: {db_path}")

    connection = sqlite3.connect(db_path)
    rows = connection.execute(
        "SELECT id, event_name, total_emv_usd, result_json FROM analyses "
        "ORDER BY analyzed_at"
    ).fetchall()

    changes = []
    for analysis_id, event_name, column_total, raw_json in rows:
        updated, old_total, new_total = _reprice(json.loads(raw_json))
        changes.append(
            {
                "id": analysis_id,
                "eventName": event_name,
                "oldTotalEmvUsd": round(old_total, 2),
                "newTotalEmvUsd": round(new_total, 2),
                "ratio": round(new_total / old_total, 6) if old_total else None,
            }
        )
    backup_path = None
    if args.apply:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        backup_path = db_path.with_name(f"{db_path.stem}.before-emv-v2.{stamp}{db_path.suffix}")
        shutil.copy2(db_path, backup_path)

        for analysis_id, _event_name, _column_total, raw_json in rows:
            updated, _old_total, new_total = _reprice(json.loads(raw_json))
            connection.execute(
                "UPDATE analyses SET total_emv_usd = ?, result_json = ? WHERE id = ?",
                (new_total, json.dumps(updated, separators=(",", ":")), analysis_id),
            )
        connection.commit()

    connection.close()

    summary = {
        "formula": "(qualityExposureSeconds / 30) * (CPM / 1000) * audience * placementMultiplier",
        "modelVersion": "time-normalised-v2",
        "referenceSpotSeconds": REFERENCE_SPOT_SECONDS,
        "applied": args.apply,
        "database": str(db_path),
        "backup": str(backup_path) if backup_path else None,
        "analysisCount": len(changes),
        "oldPortfolioEmvUsd": round(sum(c["oldTotalEmvUsd"] for c in changes), 2),
        "newPortfolioEmvUsd": round(sum(c["newTotalEmvUsd"] for c in changes), 2),
        "analyses": changes,
    }
    rendered = json.dumps(summary, indent=2)
    print(rendered)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(rendered + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
