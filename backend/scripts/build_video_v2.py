"""LogoLense full video — animated build (v2).

Upgrade over build_video.py: real motion design + voice-over.

  * Avenir Next type, gradient background with soft colour glows.
  * Every scene ANIMATES in: headlines fade+rise, bullets stagger, the pipeline
    draws node-by-node with connectors, result numbers count up.
  * British voice-over (macOS `say -v Daniel`) is generated per scene, and each
    scene's on-screen duration is stretched to its narration length, so picture
    and voice stay locked.
  * Section 5 is the real demo footage with the voice-over mixed over the crowd.

No external services — `say`, PIL and ffmpeg only. Add background music later in
an editor (a licensing/taste choice) and re-mux; everything else is final.

    conda run -n bradford_bulls_logo python scripts/build_video_v2.py \
        --demo ../demo_logolense_audio.mp4 --output ../logolense_full_v2.mp4
"""
from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

W, H, FPS = 1920, 1080, 30
VOICE, WPM = "Daniel", 170

# palette
WHITE = (242, 245, 250)
MUTED = (150, 162, 178)
AMBER = (245, 172, 32)
BLUE = (70, 140, 255)
RED = (226, 56, 86)
CARD = (26, 32, 42)

ASSETS = Path(__file__).resolve().parent / "video_assets"
TTC = "/System/Library/Fonts/Avenir Next.ttc"
_IDX = {"black": 0, "bold": 0, "demi": 2, "med": 5, "reg": 7}
_fc: dict = {}
_img_cache: dict = {}


def F(kind: str, size: int) -> ImageFont.FreeTypeFont:
    key = (kind, size)
    if key not in _fc:
        _fc[key] = ImageFont.truetype(TTC, size, index=_IDX[kind])
    return _fc[key]


CONTENT = {
    "title": "LogoLense",
    "subtitle": "Intelligent Sponsorship Visibility & Brand Analytics Using AI",
    "tagline": "Transforming Sponsorship Analytics Through Artificial Intelligence.",
    "team_name": "VisionAI Analytics Team",
    "team_lead": "Edward",
    "members": ["Student Name 1", "Student Name 2", "Student Name 3", "Student Name 4"],
    "programme": "MSc Applied Artificial Intelligence & Data Analytics",
    "supervisors": ["Irfan Mehmood", "Tillal Eldabi"],
    "advisor": "Takao Maruyama",
    "collaborator": "Bradford Bulls Rugby League Club",
    "contact": "Ian Stafford",
    "university": "University of Bradford",
}

NARRATION = {
    "title": "Welcome to LogoLense, an AI-powered sponsorship analytics platform, "
             "built by MSc Applied Artificial Intelligence and Data Analytics students "
             "at the University of Bradford, in collaboration with Bradford Bulls Rugby League Club.",
    "team": "Meet the team behind LogoLense, led by Edward, and supported by our "
            "academic supervisors and advisor.",
    "credits": "Developed with real-world guidance from Bradford Bulls, and Ian Stafford.",
    "motivation": "Sponsorship is a multi-billion-pound industry. Brands invest heavily to "
                  "place their logos on shirts, boards and equipment. But measuring how visible "
                  "those logos actually are is difficult, and still done largely by hand. "
                  "Visibility shifts constantly with player movement, camera angles, and the flow of the match.",
    "what": "LogoLense turns match footage into objective brand-visibility data. For sponsors, "
            "it measures exposure and return on investment. For clubs, it supports evidence-based "
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

# ── easing / colour ──────────────────────────────────────────────────────
def ease(x: float) -> float:
    x = max(0.0, min(1.0, x))
    return 1 - (1 - x) ** 3


def seg(p: float, a: float, b: float) -> float:
    return ease((p - a) / (b - a)) if b > a else (1.0 if p >= b else 0.0)


def A(c, a: float):
    return (c[0], c[1], c[2], max(0, min(255, int(255 * a))))


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


# ── background (built once) ──────────────────────────────────────────────
def make_bg() -> Image.Image:
    base = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(base)
    top, bot = (18, 23, 32), (8, 11, 16)
    for y in range(H):
        d.line([(0, y), (W, y)], fill=lerp(top, bot, y / H))
    glow = Image.new("RGB", (W, H), (0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse([-300, -400, 760, 560], fill=(70, 46, 0))      # amber top-left
    gd.ellipse([W - 700, H - 460, W + 260, H + 320], fill=(0, 28, 70))  # blue br
    base = ImageChops.add(base, glow.filter(ImageFilter.GaussianBlur(200)))
    d = ImageDraw.Draw(base)
    for gy in range(0, H, 64):                                 # faint dot grid
        for gx in range(0, W, 64):
            d.point((gx, gy), fill=(38, 44, 54))
    return base.convert("RGBA")


BG = make_bg()


# ── text helpers (RGBA overlay) ──────────────────────────────────────────
def tw(d, s, f):
    return d.textbbox((0, 0), s, font=f)[2]


def center(d, s, f, y, c, a=1.0, rise=0.0):
    d.text(((W - tw(d, s, f)) / 2, y + rise), s, font=f, fill=A(c, a))


def left(d, s, f, x, y, c, a=1.0, rise=0.0):
    d.text((x, y + rise), s, font=f, fill=A(c, a))


def chip(d, s, x, y, p, c=AMBER):
    a = seg(p, 0.0, 0.18)
    f = F("demi", 26)
    w = tw(d, s, f)
    d.rounded_rectangle([x, y, x + w + 34, y + 46], radius=23, fill=A(c, a))
    d.text((x + 17, y + 9), s, font=f, fill=A((10, 12, 16), a))


def header(d, kicker, title, p):
    chip(d, kicker, 120, 96, p)
    a = seg(p, 0.08, 0.4)
    left(d, title, F("bold", 66), 120, 158, WHITE, a, rise=(1 - a) * 18)
    wln = int(150 * seg(p, 0.2, 0.55))
    if wln:
        d.rounded_rectangle([124, 250, 124 + wln, 258], radius=4, fill=A(AMBER, 1))


def asset(img, d, name, x, y, w, h, label, a=1.0):
    p = ASSETS / name
    if p.exists():
        im = Image.open(p).convert("RGBA")
        im.thumbnail((w, h))
        if a < 1:
            im.putalpha(im.getchannel("A").point(lambda v: int(v * a)))
        img.alpha_composite(im, (x + (w - im.width) // 2, y + (h - im.height) // 2))
    else:
        d.rounded_rectangle([x, y, x + w, y + h], radius=16,
                            outline=A(MUTED, a * 0.7), width=2)
        f = F("reg", 24)
        d.text((x + (w - tw(d, label, f)) // 2, y + h // 2 - 14), label,
               font=f, fill=A(MUTED, a))


def panel_image(name, w, h, radius=22):
    """Cover-fit an asset image into w×h with rounded corners (cached)."""
    key = (name, w, h)
    if key in _img_cache:
        return _img_cache[key]
    p = ASSETS / name
    if not p.exists():
        _img_cache[key] = None
        return None
    im = Image.open(p).convert("RGB")
    sr = max(w / im.width, h / im.height)
    im = im.resize((int(im.width * sr) + 1, int(im.height * sr) + 1))
    cx, cy = (im.width - w) // 2, (im.height - h) // 2
    im = im.crop((cx, cy, cx + w, cy + h)).convert("RGBA")
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, w - 1, h - 1], radius=radius, fill=255)
    im.putalpha(mask)
    _img_cache[key] = im
    return im


def blit(img, name, x, y, w, h, alpha=1.0, radius=22, border=AMBER):
    """Composite a rounded cover-fit image with a border onto `img` (RGBA)."""
    im = panel_image(name, w, h, radius)
    if im is None:
        d = ImageDraw.Draw(img)
        d.rounded_rectangle([x, y, x + w, y + h], radius=radius,
                            outline=A(MUTED, alpha * 0.6), width=2)
        return
    if alpha < 1:
        im = im.copy()
        im.putalpha(im.getchannel("A").point(lambda v: int(v * alpha)))
    img.alpha_composite(im, (x, y))
    bd = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(bd).rounded_rectangle([0, 0, w - 1, h - 1], radius=radius,
                                         outline=A(border, alpha), width=3)
    img.alpha_composite(bd, (x, y))


# ── scenes: f(img, d, p) drawing onto RGBA overlay `d`, progress p∈[0,1] ──
def sc_motivation(img, d, p):
    header(d, "MOTIVATION", "A multi-billion-pound question", p)
    items = ["Brands invest millions in sponsorship.",
             "Visibility is still measured by hand.",
             "Exposure shifts with player & camera movement.",
             "Sponsors need objective, data-driven proof."]
    pics = ["motiv_1.png", "motiv_2.png", "motiv_3.png", "motiv_4.png"]
    caps = ["Jersey & board sponsorship", "Reviewed manually",
            "Movement & camera angles", "Automated, data-driven"]
    starts = [0.22, 0.42, 0.60, 0.78]
    px, py, pw, ph = 1050, 350, 760, 470

    # right-hand image panel: previous image holds, current crossfades in
    panel_a = seg(p, 0.16, 0.32)
    if panel_a > 0:
        k = max((i for i, s in enumerate(starts) if p >= s), default=0)
        if k >= 1:
            blit(img, pics[k - 1], px, py, pw, ph, alpha=1.0)
            a_new = seg(p, starts[k], starts[k] + 0.14)
        else:
            a_new = panel_a
        blit(img, pics[k], px, py, pw, ph, alpha=a_new)
        # caption bar inside the panel (drawn on overlay so it sits on top)
        ca = a_new if k >= 1 else panel_a
        d.rounded_rectangle([px, py + ph - 56, px + pw, py + ph], radius=22,
                            fill=A((8, 10, 14), ca * 0.66))
        d.rectangle([px, py + ph - 56, px + pw, py + ph - 34], fill=A((8, 10, 14), ca * 0.66))
        left(d, caps[k], F("demi", 26), px + 24, py + ph - 44, WHITE, ca)

    # left-hand bullets; the one matching the current image is highlighted
    k = max((i for i, s in enumerate(starts) if p >= s), default=0)
    for i, (it, s) in enumerate(zip(items, starts)):
        a = seg(p, s, s + 0.18)
        if a <= 0:
            continue
        y = 392 + i * 104
        active = i == k and panel_a > 0
        r = 11 if active else 8
        d.ellipse([130, y + 14, 130 + 2 * r, y + 14 + 2 * r],
                  fill=A(AMBER if active else MUTED, a))
        left(d, it, F("med", 35), 168, y, WHITE if active else MUTED, a, rise=(1 - a) * 20)


def sc_title(img, d, p):
    a = seg(p, 0.05, 0.45)
    sz = int(150 * (0.94 + 0.06 * a))
    center(d, CONTENT["title"], F("bold", sz), 350, WHITE, a)
    wln = int(560 * seg(p, 0.25, 0.7))
    if wln:
        d.rounded_rectangle([(W - wln) // 2, 530, (W + wln) // 2, 540],
                            radius=5, fill=A(AMBER, 1))
    center(d, CONTENT["subtitle"], F("med", 40), 575, MUTED,
           seg(p, 0.4, 0.75), rise=(1 - seg(p, 0.4, 0.75)) * 16)
    center(d, CONTENT["tagline"], F("demi", 30), 705, AMBER, seg(p, 0.6, 0.9))


def sc_team(img, d, p):
    header(d, "THE TEAM", CONTENT["team_name"], p)
    n, bw, bh, gap = 5, 250, 250, 40
    x0 = (W - (n * bw + (n - 1) * gap)) // 2
    labels = [f"Lead · {CONTENT['team_lead']}"] + CONTENT["members"]
    files = ["lead.png", "m1.png", "m2.png", "m3.png", "m4.png"]
    for i in range(n):
        a = seg(p, 0.25 + i * 0.1, 0.5 + i * 0.1)
        x = x0 + i * (bw + gap)
        asset(img, d, files[i], x, int(390 + (1 - a) * 24), bw, bh, "Photo", a)
        nm = labels[i]
        left(d, nm, F("demi", 27), x + (bw - tw(d, nm, F("demi", 27))) // 2, 660, WHITE, a)
    center(d, CONTENT["programme"] + " Students", F("reg", 34), 770, MUTED, seg(p, 0.7, 0.95))


def sc_credits(img, d, p):
    header(d, "SUPERVISION & COLLABORATION", "Guidance & Partnership", p)
    y = 360
    a1 = seg(p, 0.2, 0.5)
    left(d, "Supervisors", F("demi", 38), 120, y, AMBER, a1)
    for i, s in enumerate(CONTENT["supervisors"]):
        left(d, s, F("med", 36), 120, y + 62 + i * 54, WHITE, seg(p, 0.28 + i * 0.06, 0.6))
    left(d, "Advisor", F("demi", 38), 120, y + 210, AMBER, seg(p, 0.4, 0.7))
    left(d, CONTENT["advisor"], F("med", 36), 120, y + 272, WHITE, seg(p, 0.46, 0.74))
    a2 = seg(p, 0.45, 0.75)
    left(d, "Industry Collaborator", F("demi", 38), 980, y, AMBER, a2)
    left(d, CONTENT["collaborator"], F("med", 36), 980, y + 62, WHITE, seg(p, 0.5, 0.8))
    left(d, "Contact · " + CONTENT["contact"], F("reg", 30), 980, y + 116, MUTED, seg(p, 0.55, 0.85))
    a3 = seg(p, 0.6, 0.92)
    asset(img, d, "bulls_logo.png", 980, y + 180, 210, 210, "Bulls logo", a3)
    asset(img, d, "ian.png", 1215, y + 180, 210, 210, "Ian Stafford", a3)
    asset(img, d, "uni_logo.png", 1450, y + 180, 330, 210, "Univ. of Bradford", a3)


def sc_bullets(kicker, title, items):
    def render(img, d, p):
        header(d, kicker, title, p)
        for i, it in enumerate(items):
            a = seg(p, 0.25 + i * 0.13, 0.5 + i * 0.13)
            y = 360 + i * 92
            d.ellipse([130, y + 16, 150, y + 36], fill=A(AMBER, a))
            left(d, it, F("med", 40), 178, y, WHITE, a, rise=(1 - a) * 22)
    return render


def sc_what(img, d, p):
    header(d, "WHAT IS LOGOLENSE", "One platform, three audiences", p)
    cols = [
        ("For Sponsors", BLUE, ["Measure logo exposure", "Evaluate sponsorship ROI", "Compare across matches"]),
        ("For Clubs", AMBER, ["Evidence-based pricing", "Objective visibility reports", "New commercial value"]),
        ("For Designers", RED, ["See what drives visibility", "Optimise size & contrast", "Design for the pitch"]),
    ]
    cw, gap = 520, 40
    x0 = (W - (3 * cw + 2 * gap)) // 2
    for i, (t, c, items) in enumerate(cols):
        a = seg(p, 0.25 + i * 0.12, 0.55 + i * 0.12)
        x = x0 + i * (cw + gap)
        yo = int((1 - a) * 30)
        d.rounded_rectangle([x, 340 + yo, x + cw, 880 + yo], radius=22, fill=A(CARD, a))
        d.rounded_rectangle([x, 340 + yo, x + cw, 412 + yo], radius=22, fill=A(c, a))
        d.rectangle([x, 384 + yo, x + cw, 412 + yo], fill=A(c, a))
        left(d, t, F("demi", 36), x + (cw - tw(d, t, F("demi", 36))) // 2, 354 + yo, (12, 14, 18), a)
        for j, it in enumerate(items):
            ja = seg(p, 0.4 + i * 0.1 + j * 0.05, 0.7 + i * 0.1 + j * 0.05)
            yy = 470 + yo + j * 78
            d.ellipse([x + 40, yy + 12, x + 56, yy + 28], fill=A(c, ja))
            left(d, it, F("reg", 33), x + 74, yy, WHITE, ja)


def sc_pipeline(img, d, p):
    header(d, "OUR AI SOLUTION", "The processing pipeline", p)
    steps = [("Match\nVideo", MUTED), ("Frame\nExtraction", MUTED),
             ("Player\nDetection", BLUE), ("Multi-Object\nTracking", BLUE),
             ("Logo\nDetection", AMBER), ("Visibility\nScoring", AMBER),
             ("Exposure\n& EMV", RED), ("Analytics\nDashboard", RED)]
    n = len(steps)
    bw, bh = 195, 150
    gap = (W - 240 - n * bw) // (n - 1)
    y = 410
    for i, (label, c) in enumerate(steps):
        a = seg(p, 0.12 + i * 0.085, 0.32 + i * 0.085)
        if a <= 0:
            continue
        x = 120 + i * (bw + gap)
        yo = int((1 - a) * 26)
        glow = seg(p, 0.12 + i * 0.085, 0.2 + i * 0.085) - seg(p, 0.28 + i * 0.085, 0.42 + i * 0.085)
        if glow > 0:
            d.rounded_rectangle([x - 6, y + yo - 6, x + bw + 6, y + bh + yo + 6],
                                radius=20, fill=A(c, glow * 0.35))
        d.rounded_rectangle([x, y + yo, x + bw, y + bh + yo], radius=16,
                            fill=A(CARD, a), outline=A(c, a), width=3)
        for j, ln in enumerate(label.split("\n")):
            left(d, ln, F("demi", 25), x + (bw - tw(d, ln, F("demi", 25))) // 2,
                 y + yo + 44 + j * 32, WHITE, a)
        if i < n - 1:
            ca = seg(p, 0.2 + i * 0.085, 0.3 + i * 0.085)
            if ca > 0:
                ax = x + bw + gap // 2
                d.polygon([(x + bw + 6, y + bh // 2 - 9), (x + bw + 6, y + bh // 2 + 9),
                           (ax + 6, y + bh // 2)], fill=A(AMBER, ca))
    af = seg(p, 0.7, 0.95)
    center(d, "Computer Vision  ·  Deep Learning  ·  Object Detection  ·  Multi-Object Tracking  ·  Logo Recognition",
           F("reg", 31), 720, MUTED, af)
    center(d, "YOLO11-pose   →   ByteTrack   →   YOLO26m / RF-DETR   →   SigLIP team filter   →   Visibility = Size × Position × Clarity",
           F("demi", 27), 800, AMBER, seg(p, 0.78, 0.98))


def sc_results(img, d, p):
    header(d, "RESULTS & FINDINGS", "Visibility is never constant", p)
    # big count-up number
    val = int(round(9 * seg(p, 0.15, 0.55)))
    a = seg(p, 0.15, 0.45)
    left(d, str(val), F("bold", 150), 150, 350, AMBER, a)
    left(d, "sponsor brands detected", F("med", 40), 150, 520, WHITE, seg(p, 0.3, 0.6))
    left(d, "in a single 14-second clip", F("reg", 32), 150, 575, MUTED, seg(p, 0.35, 0.65))
    items = ["Per-logo visibility scored live (size × position × clarity).",
             "Same sponsor swings from fully visible to occluded in seconds.",
             "Camera angle & player position drive most of the variance."]
    for i, it in enumerate(items):
        ia = seg(p, 0.45 + i * 0.13, 0.7 + i * 0.13)
        yy = 400 + i * 86
        d.ellipse([980, yy + 14, 998, yy + 32], fill=A(AMBER, ia))
        left(d, it, F("reg", 32), 1024, yy, WHITE, ia, rise=(1 - ia) * 16)


def sc_challenges(img, d, p):
    header(d, "REAL-WORLD CHALLENGES", "Built for messy match footage", p)
    items = ["Overlapping players & occlusion", "Motion blur in fast action",
             "Varying camera angles", "Scale changes near / far",
             "Lighting & weather", "Small / partial logos"]
    cw = 760
    for i, it in enumerate(items):
        a = seg(p, 0.22 + i * 0.1, 0.5 + i * 0.1)
        x = 130 + (i % 2) * (cw + 60)
        y = 380 + (i // 2) * 128
        xo = int((1 - a) * 24)
        d.rounded_rectangle([x - xo, y, x + cw - xo, y + 100], radius=16, fill=A(CARD, a))
        d.ellipse([x + 24 - xo, y + 38, x + 48 - xo, y + 62], fill=A(RED, a))
        left(d, it, F("demi", 34), x + 72 - xo, y + 28, WHITE, a)


def sc_impact(img, d, p):
    header(d, "IMPACT & FUTURE", "Where LogoLense goes next", p)
    left(d, "Impact today", F("demi", 38), 130, 350, AMBER, seg(p, 0.2, 0.5))
    for i, it in enumerate(["Automated sponsorship reporting", "Brand & marketing intelligence",
                            "Business decision support"]):
        a = seg(p, 0.28 + i * 0.1, 0.55 + i * 0.1)
        yy = 420 + i * 78
        d.ellipse([130, yy + 12, 146, yy + 28], fill=A(AMBER, a))
        left(d, it, F("reg", 36), 168, yy, WHITE, a, rise=(1 - a) * 16)
    left(d, "Future", F("demi", 38), 1010, 350, BLUE, seg(p, 0.4, 0.7))
    for i, it in enumerate(["Real-time match analytics", "Multi-sport deployment",
                            "Advanced sponsor valuation", "Live dashboard integration"]):
        a = seg(p, 0.48 + i * 0.09, 0.74 + i * 0.09)
        yy = 420 + i * 70
        d.ellipse([1010, yy + 10, 1026, yy + 26], fill=A(BLUE, a))
        left(d, it, F("reg", 34), 1048, yy, WHITE, a, rise=(1 - a) * 14)


def sc_closing(img, d, p):
    a = seg(p, 0.05, 0.4)
    center(d, CONTENT["title"], F("bold", 110), 330, WHITE, a)
    wln = int(640 * seg(p, 0.25, 0.65))
    if wln:
        d.rounded_rectangle([(W - wln) // 2, 470, (W + wln) // 2, 478], radius=4, fill=A(AMBER, 1))
    center(d, CONTENT["tagline"], F("demi", 38), 510, AMBER, seg(p, 0.4, 0.75))
    center(d, CONTENT["team_name"] + "   ·   " + CONTENT["university"],
           F("reg", 32), 640, MUTED, seg(p, 0.55, 0.85))
    aa = seg(p, 0.65, 0.95)
    asset(img, d, "uni_logo.png", 770, 740, 170, 120, "Univ.", aa)
    asset(img, d, "bulls_logo.png", 990, 740, 170, 120, "Bulls", aa)


# (id, render_fn)  — demo is inserted between pipeline and results
SCENES = [
    ("title", sc_title), ("team", sc_team), ("credits", sc_credits),
    ("motivation", sc_motivation),
    ("what", sc_what), ("pipeline", sc_pipeline),
    ("results", sc_results), ("challenges", sc_challenges),
    ("impact", sc_impact), ("closing", sc_closing),
]
DEMO_AFTER = "pipeline"

ENC = ["-c:v", "libx264", "-preset", "medium", "-pix_fmt", "yuv420p", "-r", str(FPS),
       "-c:a", "aac", "-ar", "44100", "-ac", "2"]
LEAD, TAIL = 0.45, 0.9   # silence before/after voice within a scene


def run(cmd, **kw):
    return subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL,
                          stderr=subprocess.PIPE, **kw)


def gen_voice(text: str, wav: Path) -> float:
    aiff = wav.with_suffix(".aiff")
    run(["say", "-v", VOICE, "-r", str(WPM), "-o", str(aiff), text])
    run(["ffmpeg", "-y", "-i", str(aiff), "-ar", "44100", "-ac", "2", str(wav)])
    aiff.unlink(missing_ok=True)
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "csv=p=0", str(wav)], capture_output=True, text=True)
    return float(out.stdout.strip())


def render_scene(fn, dur: float, wav: Path, out: Path) -> None:
    nframes = max(1, int(round(dur * FPS)))
    proc = subprocess.Popen(
        ["ffmpeg", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
         "-r", str(FPS), "-i", "-", "-i", str(wav),
         "-filter_complex", f"[1:a]adelay={int(LEAD*1000)}|{int(LEAD*1000)},apad[a]",
         "-map", "0:v", "-map", "[a]", *ENC, "-shortest", str(out)],
        stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    for f in range(nframes):
        p = f / max(1, nframes - 1)
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(ov)
        frame = BG.copy()
        fn(frame, d, p)
        frame.alpha_composite(ov)
        # gentle global fade in/out
        fade = min(seg(p, 0.0, 0.06), seg(1 - p, 0.0, 0.05))
        if fade < 1:
            frame = Image.blend(Image.new("RGBA", (W, H), (8, 11, 16, 255)), frame, fade)
        proc.stdin.write(frame.convert("RGB").tobytes())
    proc.stdin.close()
    proc.wait()


def render_demo(src: Path, wav: Path, out: Path) -> None:
    vf = ("scale=1920:1080:force_original_aspect_ratio=decrease,"
          "pad=1920:1080:(ow-iw)/2:(oh-ih)/2,setsar=1,format=yuv420p")
    # mix demo crowd (quiet) with the voice-over (delayed in)
    fc = (f"{vf}[v];[0:a]volume=0.25[a0];"
          f"[1:a]adelay={int(LEAD*1000)}|{int(LEAD*1000)},volume=1.7[a1];"
          f"[a0][a1]amix=inputs=2:duration=first:dropout_transition=0[a]")
    run(["ffmpeg", "-y", "-i", str(src), "-i", str(wav), "-filter_complex", fc,
         "-map", "[v]", "-map", "[a]", *ENC, str(out)])


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--demo", required=True, type=Path)
    ap.add_argument("--output", required=True, type=Path)
    ap.add_argument("--workdir", type=Path, default=Path("/tmp/ll_v2"))
    args = ap.parse_args()
    args.workdir.mkdir(parents=True, exist_ok=True)

    clips: list[Path] = []
    for sid, fn in SCENES:
        wav = args.workdir / f"{sid}.wav"
        vdur = gen_voice(NARRATION[sid], wav)
        dur = LEAD + vdur + TAIL
        out = args.workdir / f"clip_{sid}.mp4"
        print(f"  {sid:11s} voice {vdur:4.1f}s -> scene {dur:4.1f}s", flush=True)
        render_scene(fn, dur, wav, out)
        clips.append(out)
        if sid == DEMO_AFTER:
            dwav = args.workdir / "demo.wav"
            gen_voice(NARRATION["demo"], dwav)
            dclip = args.workdir / "clip_demo.mp4"
            print("  demo        real footage + voice-over", flush=True)
            render_demo(args.demo, dwav, dclip)
            clips.append(dclip)

    listf = args.workdir / "concat.txt"
    listf.write_text("".join(f"file '{c}'\n" for c in clips))
    print("  concat ->", args.output, flush=True)
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(listf), "-c", "copy", str(args.output)])
    print(f"done -> {args.output}")


if __name__ == "__main__":
    main()
