"""Capture the dashboard figures from the running application.

Prerequisites — start both services first, then run this script:

    # backend (serves the 23 stored analyses from backend/data/app.db)
    cd backend && ../.venv-app/Scripts/python -m uvicorn app.main:app --port 8000

    # frontend
    cd logo-analytics && npx next dev -p 3000

    python screenshot_dashboard.py

Produces figures/fig_dashboard.png (Figure 9) and figures/fig_kit3d.png
(Figure 10). It drives the Edge already installed on the machine rather than
downloading a browser, and forces WebGL through the software rasteriser so the
three.js kit model renders headless.

The preview videos are seeked to a chosen timestamp and paused, because a
video element screenshots as a blank poster otherwise. The timestamp is chosen
to land on a wide stadium shot in which no individual is identifiable.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent
FIG = ROOT / "figures"
SHOTS = ROOT / ".shots"
BASE = "http://127.0.0.1:3000"

ARGS = ["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader",
        "--autoplay-policy=no-user-gesture-required"]

# Seek every <video> on the page, then pause, and resolve once the frame is
# actually decoded — otherwise the screenshot catches an empty poster.
SEEK_JS = """
(t) => Promise.all([...document.querySelectorAll('video')].map(v => new Promise(res => {
  v.muted = true;
  const done = () => { v.pause(); res(v.currentTime); };
  if (v.readyState >= 1) { v.currentTime = t; v.addEventListener('seeked', done, {once:true}); }
  else { v.addEventListener('loadedmetadata', () => {
           v.currentTime = t; v.addEventListener('seeked', done, {once:true});
         }, {once:true}); }
  setTimeout(() => res(-1), 8000);
})))
"""

# Crop boxes into the full-page captures, at device_scale_factor 2. Each is
# kept to a single screenful of content: stacking two views into one image
# makes it too tall for the page, and the type ends up too small to read.
CROPS = {
    "overview": (330, 150, 2900, 1960),    # header, KPI row, EMV trend
    "match": (330, 1600, 2900, 4400),      # match KPIs, preview video, brand timeline
    "kit3d": (330, 2420, 2900, 4150),      # 3D kit model and the ranked slot list
}

TARGETS = {
    "overview": "fig_dashboard_overview.png",
    "match": "fig_dashboard_match.png",
    "kit3d": "fig_kit3d.png",
}


def capture():
    SHOTS.mkdir(exist_ok=True)
    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel="msedge", headless=True, args=ARGS)
        page = browser.new_page(viewport={"width": 1600, "height": 1150},
                                device_scale_factor=2)
        page.goto(BASE + "/dashboard", wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(4000)

        # 12.0s lands on a ruck in the rendered preview where the annotated
        # boxes are dense; the default poster frame is an empty stadium shot,
        # which shows nothing of what the system does.
        for tab, seek, name in [("Overview", None, "overview"),
                                ("Match Videos", 12.0, "match"),
                                ("Body Segmentation", None, "kit3d")]:
            page.get_by_role("button", name=tab, exact=False).first.click()
            page.wait_for_timeout(3200)
            if seek is not None:
                page.evaluate(SEEK_JS, seek)
                page.wait_for_timeout(2500)
            page.screenshot(path=SHOTS / f"{name}.png", full_page=True)
            print(f"  captured {tab}")
        browser.close()


def compose():
    for name, box in CROPS.items():
        img = Image.open(SHOTS / f"{name}.png").crop(box)
        out = FIG / TARGETS[name]
        img.save(out, quality=92)
        print(f"  wrote {out.name}  ({img.width}x{img.height})")


if __name__ == "__main__":
    import sys
    if "--compose-only" not in sys.argv:
        capture()
    compose()
