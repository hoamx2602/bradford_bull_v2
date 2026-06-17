"""Prepare Remotion assets: narration audio, footage images, demo clip, durations.

Generates British voice-over per scene with macOS `say`, measures each clip,
copies the motivation footage frames + the annotated demo clip into public/, and
writes src/durations.json so the Remotion compositions can size each scene to its
narration. Run once (or whenever narration text changes):

    python3 video/scripts/prep_assets.py
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent          # video/
REPO = ROOT.parent
AUDIO = ROOT / "public" / "audio"
IMG = ROOT / "public" / "img"
AUDIO.mkdir(parents=True, exist_ok=True)
IMG.mkdir(parents=True, exist_ok=True)

VOICE, WPM = "Daniel", 170

NARRATION = {
    "title": "Welcome to LogoLense, an AI-powered sponsorship analytics platform, built by "
             "MSc Applied Artificial Intelligence and Data Analytics students at the University "
             "of Bradford, in collaboration with Bradford Bulls Rugby League Club.",
    "team": "Meet the team behind LogoLense, led by Edward, and supported by our academic "
            "supervisors and advisor.",
    "credits": "Developed with real-world guidance from Bradford Bulls, and Ian Stafford.",
    "motivation": "Sponsorship is a multi-billion-pound industry. Brands invest heavily to place "
                  "their logos on shirts, boards and equipment. But measuring how visible those "
                  "logos actually are is difficult, and still done largely by hand. Visibility "
                  "shifts constantly with player movement, camera angles, and the flow of the match.",
    "what": "LogoLense turns match footage into objective brand-visibility data. For sponsors, it "
            "measures exposure and return on investment. For clubs, it supports evidence-based "
            "pricing. And for brand designers, it reveals what actually makes a logo stand out on the pitch.",
    "pipeline": "At its core is a computer-vision pipeline. Match video is broken into frames. "
                "Players are detected and tracked across the sequence. Sponsor logos are identified, "
                "filtered to the target team, and scored for visibility, combining their size, "
                "position and clarity into a single exposure metric.",
    "demo": "Here it is in action. Watch the system build up, layer by layer: detecting players, "
            "tracking them, then locking onto every sponsor logo and scoring its visibility in real time.",
    "results": "Even in a single fourteen-second clip, LogoLense detects nine different sponsor "
               "brands, and reveals how dramatically their visibility changes as players move and the camera shifts.",
    "challenges": "Real match footage is messy: overlapping players, motion blur, changing camera "
                  "angles, lighting, and small or partly hidden logos. LogoLense is built to stay accurate through all of it.",
    "impact": "The result is automated sponsorship reporting and marketing intelligence, and a "
              "foundation for real-time, multi-sport brand analytics in the future.",
    "closing": "LogoLense. Transforming sponsorship analytics through artificial intelligence.",
}


def duration(path: Path) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "csv=p=0", str(path)], capture_output=True, text=True)
    return round(float(out.stdout.strip()), 3)


def main() -> None:
    durations = {}
    for sid, text in NARRATION.items():
        aiff = AUDIO / f"{sid}.aiff"
        mp3 = AUDIO / f"{sid}.mp3"
        subprocess.run(["say", "-v", VOICE, "-r", str(WPM), "-o", str(aiff), text], check=True)
        subprocess.run(["ffmpeg", "-y", "-i", str(aiff), "-ar", "44100", "-ac", "2",
                        "-b:a", "160k", str(mp3)], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        aiff.unlink(missing_ok=True)
        durations[sid] = duration(mp3)
        print(f"  voice {sid:11s} {durations[sid]:5.1f}s")

    # footage images for the motivation image-swap + general use
    for i in range(1, 5):
        src = REPO / "backend" / "scripts" / "video_assets" / f"motiv_{i}.png"
        if src.exists():
            shutil.copy(src, IMG / f"motiv_{i}.png")
    # annotated demo clip (section 5)
    demo_src = REPO / "demo_logolense_audio.mp4"
    if demo_src.exists():
        shutil.copy(demo_src, ROOT / "public" / "demo.mp4")
        durations["demo_video"] = duration(demo_src)
        print(f"  demo clip   {durations['demo_video']:5.1f}s")

    (ROOT / "src" / "durations.json").write_text(json.dumps(durations, indent=2))
    print("wrote src/durations.json:", durations)


if __name__ == "__main__":
    main()
