"""Build the full LogoLense marketing/demo video (the 8-section structure).

Renders every section as a 1920x1080 slide with PIL, then stitches them together
with ffmpeg around the real demo footage (section 5) into one finished MP4:

    1 Title + Team        2 Motivation        3 What is LogoLense
    4 AI Pipeline         5 Live Demo (real)  6 Results
    7 Challenges          8 Impact + Tagline

Everything is config-driven (see CONTENT below): edit names / bullet text / slide
durations and re-run. Optional real assets (team photo, university + club logos,
member headshots) are read from ``scripts/video_assets/`` if present; otherwise a
labelled placeholder box is drawn so the video always builds.

The result has silent slides + the demo's crowd audio. Add narration + music in
a normal editor (CapCut/DaVinci) as the final polish step — those are licensing /
voice choices a script shouldn't fabricate.

    conda run -n bradford_bulls_logo python scripts/build_video.py \
        --demo ../demo_logolense_audio.mp4 --output ../logolense_full.mp4
"""
from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# ── palette ──────────────────────────────────────────────────────────────
BG = (13, 17, 23)            # near-black
BG2 = (22, 27, 34)
WHITE = (240, 243, 247)
MUTED = (150, 160, 172)
AMBER = (240, 165, 0)        # LogoLense accent
RED = (200, 16, 46)          # Bradford Bulls red
BLUE = (31, 111, 235)

W, H = 1920, 1080
ASSETS = Path(__file__).resolve().parent / "video_assets"

# ── EDIT ME: all text content lives here ─────────────────────────────────
CONTENT = {
    "title": "LogoLense",
    "subtitle": "Intelligent Sponsorship Visibility & Brand Analytics Using AI",
    "tagline": "Transforming Sponsorship Analytics Through Artificial Intelligence.",
    "team_name": "VisionAI Analytics Team",
    "team_lead": "Edward",
    "members": ["Student Name 1", "Student Name 2", "Student Name 3", "Student Name 4"],
    "programme": "MSc Applied Artificial Intelligence & Data Analytics",
    "supervisors": ["Dr. Irfan Mehmood", "Prof. Tillal Eldabi"],
    "advisor": "Dr. Takao Maruyama",
    "collaborator": "Bradford Bulls Rugby League Club",
    "collaborator_contact": "Ian Stafford",
    "university": "University of Bradford",
}

# ── fonts ────────────────────────────────────────────────────────────────
_FONT_CANDIDATES = {
    "black": ["/System/Library/Fonts/Supplemental/Arial Black.ttf"],
    "bold": ["/System/Library/Fonts/Supplemental/Arial Bold.ttf"],
    "reg": ["/System/Library/Fonts/Supplemental/Arial.ttf"],
}


def font(kind: str, size: int) -> ImageFont.FreeTypeFont:
    for path in _FONT_CANDIDATES[kind]:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


# ── drawing helpers ──────────────────────────────────────────────────────
def canvas(bg=BG) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("RGB", (W, H), bg)
    return img, ImageDraw.Draw(img)


def _w(draw, text, fnt) -> int:
    b = draw.textbbox((0, 0), text, font=fnt)
    return b[2] - b[0]


def center(draw, text, fnt, y, color=WHITE) -> None:
    draw.text(((W - _w(draw, text, fnt)) // 2, y), text, font=fnt, fill=color)


def left(draw, text, fnt, x, y, color=WHITE) -> None:
    draw.text((x, y), text, font=fnt, fill=color)


def accent_bar(draw, y=0, h=8, color=AMBER) -> None:
    draw.rectangle([0, y, W, y + h], fill=color)


def chip(draw, text, x, y, color=AMBER, fg=BG) -> int:
    f = font("bold", 30)
    tw = _w(draw, text, f)
    draw.rounded_rectangle([x, y, x + tw + 36, y + 50], radius=25, fill=color)
    draw.text((x + 18, y + 8), text, font=f, fill=fg)
    return x + tw + 36


def header(draw, kicker, title) -> None:
    accent_bar(draw)
    chip(draw, kicker, 120, 90)
    left(draw, title, font("black", 70), 120, 165, WHITE)
    draw.rectangle([124, 260, 124 + 90, 268], fill=AMBER)


def placeholder(draw, x, y, w, h, label) -> None:
    draw.rounded_rectangle([x, y, x + w, y + h], radius=16, outline=MUTED, width=2)
    f = font("reg", 26)
    draw.text((x + (w - _w(draw, label, f)) // 2, y + h // 2 - 16),
              label, font=f, fill=MUTED)


def paste_asset(img, draw, name, x, y, w, h, label) -> None:
    """Paste video_assets/<name> fitted into the box, else a placeholder."""
    p = ASSETS / name
    if p.exists():
        a = Image.open(p).convert("RGB")
        a.thumbnail((w, h))
        img.paste(a, (x + (w - a.width) // 2, y + (h - a.height) // 2))
    else:
        placeholder(draw, x, y, w, h, label)


def bullets(draw, items, x, y, gap=78, fnt=None, color=WHITE, dot=AMBER) -> None:
    fnt = fnt or font("reg", 42)
    for i, it in enumerate(items):
        cy = y + i * gap
        draw.ellipse([x, cy + 14, x + 14, cy + 28], fill=dot)
        draw.text((x + 34, cy), it, font=fnt, fill=color)


# ── section slides ───────────────────────────────────────────────────────
def slide_title() -> Image.Image:
    img, d = canvas()
    accent_bar(d, 0, 8)
    accent_bar(d, H - 8, 8)
    center(d, CONTENT["title"], font("black", 150), 360, WHITE)
    # accent underline
    tw = _w(d, CONTENT["title"], font("black", 150))
    d.rectangle([(W - tw) // 2, 530, (W + tw) // 2, 540], fill=AMBER)
    center(d, CONTENT["subtitle"], font("reg", 44), 580, MUTED)
    center(d, CONTENT["tagline"], font("bold", 30), 720, AMBER)
    return img


def slide_team() -> Image.Image:
    img, d = canvas()
    header(d, "THE TEAM", CONTENT["team_name"])
    # five headshots row
    n = 5
    bw, bh, gap = 250, 250, 40
    total = n * bw + (n - 1) * gap
    x0 = (W - total) // 2
    labels = [f"Lead · {CONTENT['team_lead']}"] + CONTENT["members"]
    files = ["lead.png", "m1.png", "m2.png", "m3.png", "m4.png"]
    for i in range(n):
        x = x0 + i * (bw + gap)
        paste_asset(img, d, files[i], x, 380, bw, bh, "Photo")
        nm = labels[i]
        f = font("bold", 28)
        d.text((x + (bw - _w(d, nm, f)) // 2, 645), nm, font=f, fill=WHITE)
    center(d, CONTENT["programme"] + " Students", font("reg", 36), 760, MUTED)
    return img


def slide_credits() -> Image.Image:
    img, d = canvas()
    header(d, "SUPERVISION & COLLABORATION", "Guidance & Partnership")
    col = font("bold", 40)
    val = font("reg", 38)
    y = 360
    left(d, "Supervisors", col, 120, y, AMBER)
    for i, s in enumerate(CONTENT["supervisors"]):
        left(d, s, val, 120, y + 60 + i * 56, WHITE)
    left(d, "Advisor", col, 120, y + 220, AMBER)
    left(d, CONTENT["advisor"], val, 120, y + 280, WHITE)
    # collaborator block (right)
    left(d, "Industry Collaborator", col, 980, y, AMBER)
    left(d, CONTENT["collaborator"], val, 980, y + 60, WHITE)
    left(d, "Contact · " + CONTENT["collaborator_contact"], font("reg", 32),
         980, y + 116, MUTED)
    paste_asset(img, d, "bulls_logo.png", 980, y + 180, 220, 220, "Bulls logo")
    paste_asset(img, d, "ian.png", 1230, y + 180, 220, 220, "Ian Stafford")
    paste_asset(img, d, "uni_logo.png", 1470, y + 180, 330, 220, "Univ. of Bradford")
    return img


def slide_motivation_1() -> Image.Image:
    img, d = canvas()
    header(d, "MOTIVATION", "A multi-billion-pound question")
    bullets(d, [
        "Brands invest heavily in jersey, board & equipment sponsorship.",
        "Yet actual logo visibility is measured by hand — slow and subjective.",
        "Visibility shifts with player movement, camera angles & match dynamics.",
        "Clubs and sponsors need objective, data-driven proof of exposure.",
    ], 130, 360)
    return img


def slide_what_is() -> Image.Image:
    img, d = canvas()
    header(d, "WHAT IS LOGOLENSE", "One platform, three audiences")
    cols = [
        ("For Sponsors", BLUE, ["Measure logo exposure", "Evaluate sponsorship ROI",
                                 "Compare across matches"]),
        ("For Clubs", AMBER, ["Evidence-based pricing", "Objective visibility reports",
                               "New commercial value"]),
        ("For Designers", RED, ["See what drives visibility", "Optimise size & contrast",
                                 "Design for the pitch"]),
    ]
    cw, gap = 520, 40
    x0 = (W - (3 * cw + 2 * gap)) // 2
    for i, (t, c, items) in enumerate(cols):
        x = x0 + i * (cw + gap)
        d.rounded_rectangle([x, 340, x + cw, 880], radius=20, fill=BG2)
        d.rounded_rectangle([x, 340, x + cw, 410], radius=20, fill=c)
        d.rectangle([x, 380, x + cw, 410], fill=c)
        f = font("bold", 38)
        d.text((x + (cw - _w(d, t, f)) // 2, 352), t, font=f, fill=BG)
        bullets(d, items, x + 40, 460, gap=80, fnt=font("reg", 34))
    return img


def slide_pipeline() -> Image.Image:
    img, d = canvas()
    header(d, "OUR AI SOLUTION", "The processing pipeline")
    steps = [
        ("Match\nVideo", MUTED), ("Frame\nExtraction", MUTED),
        ("Player\nDetection", BLUE), ("Multi-Object\nTracking", BLUE),
        ("Logo\nDetection", AMBER), ("Visibility\nScoring", AMBER),
        ("Exposure\n& EMV", RED), ("Analytics\nDashboard", RED),
    ]
    n = len(steps)
    bw, bh = 195, 150
    gap = (W - 240 - n * bw) // (n - 1)
    y = 430
    fb = font("bold", 26)
    for i, (label, c) in enumerate(steps):
        x = 120 + i * (bw + gap)
        d.rounded_rectangle([x, y, x + bw, y + bh], radius=16, fill=BG2, outline=c, width=3)
        lines = label.split("\n")
        for j, ln in enumerate(lines):
            d.text((x + (bw - _w(d, ln, fb)) // 2, y + 45 + j * 34), ln, font=fb, fill=WHITE)
        if i < n - 1:
            ax = x + bw + gap // 2
            d.polygon([(x + bw + 6, y + bh // 2 - 9), (x + bw + 6, y + bh // 2 + 9),
                       (ax + 4, y + bh // 2)], fill=AMBER)
    tech = "Computer Vision  ·  Deep Learning  ·  Object Detection  ·  Multi-Object Tracking  ·  Logo Recognition"
    center(d, tech, font("reg", 32), 720, MUTED)
    models = "YOLO11-pose   →   ByteTrack   →   YOLO26m / RF-DETR   →   SigLIP team filter   →   Visibility = Size x Position x Clarity"
    center(d, models, font("bold", 28), 800, AMBER)
    return img


def slide_results() -> Image.Image:
    img, d = canvas()
    header(d, "RESULTS & FINDINGS", "Visibility is never constant")
    bullets(d, [
        "9 distinct sponsor brands detected in a single 14-second clip.",
        "Per-logo visibility scored live (size x position x clarity).",
        "Same sponsor swings from highly visible to fully occluded in seconds.",
        "Camera angle & player position drive most of the exposure variance.",
    ], 130, 360)
    return img


def slide_challenges() -> Image.Image:
    img, d = canvas()
    header(d, "REAL-WORLD CHALLENGES", "Built for messy match footage")
    items = ["Overlapping players & occlusion", "Motion blur in fast action",
             "Varying camera angles", "Scale changes near/far",
             "Lighting & weather", "Small / partial logos"]
    cw = 760
    for i, it in enumerate(items):
        col = i % 2
        row = i // 2
        x = 130 + col * (cw + 60)
        y = 380 + row * 130
        d.rounded_rectangle([x, y, x + cw, y + 100], radius=16, fill=BG2)
        d.ellipse([x + 24, y + 38, x + 48, y + 62], fill=RED)
        d.text((x + 72, y + 30), it, font=font("bold", 36), fill=WHITE)
    return img


def slide_impact() -> Image.Image:
    img, d = canvas()
    header(d, "IMPACT & FUTURE", "Where LogoLense goes next")
    bullets(d, ["Automated sponsorship reporting", "Brand performance & marketing intelligence",
                "Broadcast & business decision support"], 130, 360, fnt=font("reg", 40))
    left(d, "Future", font("bold", 40), 980, 360, AMBER)
    bullets(d, ["Real-time match analytics", "Multi-sport deployment",
                "Advanced sponsor valuation", "Live dashboard integration"],
            980, 430, gap=70, fnt=font("reg", 36))
    return img


def slide_closing() -> Image.Image:
    img, d = canvas()
    accent_bar(d, 0, 8)
    accent_bar(d, H - 8, 8)
    center(d, CONTENT["title"], font("black", 110), 330, WHITE)
    center(d, CONTENT["tagline"], font("bold", 40), 500, AMBER)
    center(d, CONTENT["team_name"] + "   ·   " + CONTENT["university"],
           font("reg", 34), 640, MUTED)
    paste_asset(img, d, "uni_logo.png", 760, 740, 180, 130, "Univ.")
    paste_asset(img, d, "bulls_logo.png", 980, 740, 180, 130, "Bulls")
    return img


# (render_fn, seconds)
SLIDES = [
    (slide_title, 6), (slide_team, 7), (slide_credits, 6),
    (slide_motivation_1, 14), (slide_what_is, 16), (slide_pipeline, 18),
    # section 5 = the real demo clip, inserted in assembly
    (slide_results, 14), (slide_challenges, 14), (slide_impact, 14),
    (slide_closing, 7),
]
DEMO_AFTER = 6  # insert demo clip after this many slides (i.e. before results)

VF_COMMON = "scale=1920:1080,setsar=1,format=yuv420p"
ENC = ["-c:v", "libx264", "-preset", "medium", "-pix_fmt", "yuv420p", "-r", "30",
       "-c:a", "aac", "-ar", "44100", "-ac", "2"]


def run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


def slide_clip(png: Path, dur: int, out: Path) -> None:
    vf = f"{VF_COMMON},fade=t=in:st=0:d=0.4,fade=t=out:st={dur - 0.4}:d=0.4"
    run(["ffmpeg", "-y", "-loop", "1", "-framerate", "30", "-t", str(dur), "-i", str(png),
         "-f", "lavfi", "-t", str(dur), "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
         "-vf", vf, *ENC, "-shortest", str(out)])


def demo_clip(src: Path, out: Path) -> None:
    vf = ("scale=1920:1080:force_original_aspect_ratio=decrease,"
          "pad=1920:1080:(ow-iw)/2:(oh-ih)/2,setsar=1,format=yuv420p")
    # add silent audio if the source has none, else keep its audio
    run(["ffmpeg", "-y", "-i", str(src),
         "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
         "-vf", vf, "-map", "0:v", "-map", "1:a", "-shortest", *ENC, str(out)])


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--demo", required=True, type=Path, help="section-5 demo footage")
    ap.add_argument("--output", required=True, type=Path)
    ap.add_argument("--workdir", type=Path, default=Path("/tmp/ll_build"))
    args = ap.parse_args()
    args.workdir.mkdir(parents=True, exist_ok=True)

    clips: list[Path] = []
    for i, (fn, dur) in enumerate(SLIDES):
        png = args.workdir / f"slide_{i:02d}.png"
        fn().save(png)
        clip = args.workdir / f"clip_{i:02d}.mp4"
        print(f"  slide {i:02d} ({fn.__name__}, {dur}s)", flush=True)
        slide_clip(png, dur, clip)
        clips.append(clip)
        if i + 1 == DEMO_AFTER:
            print("  inserting demo footage (section 5)", flush=True)
            dclip = args.workdir / "clip_demo.mp4"
            demo_clip(args.demo, dclip)
            clips.append(dclip)

    listf = args.workdir / "concat.txt"
    listf.write_text("".join(f"file '{c}'\n" for c in clips))
    print("  concatenating ->", args.output, flush=True)
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(listf),
         "-c", "copy", str(args.output)])
    print(f"done -> {args.output}")


if __name__ == "__main__":
    main()
