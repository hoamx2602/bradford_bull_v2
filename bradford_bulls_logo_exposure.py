"""
Bradford Bulls — Logo Exposure Detection System
================================================
Modular Python source that the Colab notebook imports.
"""

# ─────────────────────────────────────────────
# SECTION 1 – CONFIGURATION
# ─────────────────────────────────────────────

# All sponsor logos mapped to their kit position(s).
# position_key MUST match KIT_POSITIONS keys below.
SPONSOR_CONFIG = {
    "topnotch": {
        "display_name": "Top Notch",
        "logo_files": ["13 - Top Notch Logo.png"],
        "kit": "home",
        "positions": ["chest_front"],
        "pricing_pct": 0.26,
    },
    "floor_tonic": {
        "display_name": "Floor Tonic",
        "logo_files": ["Floor tonic Logo.jpg"],
        "kit": "away",
        "positions": ["chest_front"],
        "pricing_pct": 0.26,
    },
    "aon": {
        "display_name": "AON",
        "logo_files": [
            "1 - aon_logo_signature_red_rgb (2).png",
            "1 - aon_logo_white_rgb (3).png",
        ],
        "kit": "both",
        "positions": ["shorts_back_right"],
        "pricing_pct": 0.03,
    },
    "klg_europe": {
        "display_name": "KLG Europe",
        "logo_files": ["7 - KLG Transparent Final.png"],
        "kit": "both",
        "positions": ["shorts_back_left"],
        "pricing_pct": 0.05,
    },
    "acs_group": {
        "display_name": "ACS Group",
        "logo_files": ["acs_group.jpg"],
        "kit": "both",
        "positions": ["back_lower"],
        "pricing_pct": 0.03,
    },
    "mcp": {
        "display_name": "MCP",
        "logo_files": ["9 - MCP.png", "8 - MCP Away.png"],
        "kit": "both",
        "positions": ["back_upper"],
        "pricing_pct": 0.08,
    },
    "romantica": {
        "display_name": "Romantica Beds",
        "logo_files": [
            "Romantica Beds - Logo FINAL WHITE.jpg",
            "romantica black.jpg",
        ],
        "kit": "both",
        "positions": ["chest_left"],
        "pricing_pct": 0.07,
    },
    "bartercard": {
        "display_name": "Bartercard",
        "logo_files": ["Bartercard.jpg"],
        "kit": "both",
        "positions": ["chest_right", "back_mid"],
        "pricing_pct": 0.11,
    },
    "atm_hospitality": {
        "display_name": "ATM Hospitality",
        "logo_files": ["2 - ATM-Hospitality-Logo-New-Font.png"],
        "kit": "both",
        "positions": ["sleeve_right"],
        "pricing_pct": 0.04,
    },
    "cedar_court": {
        "display_name": "Cedar Court Hotels",
        "logo_files": ["3 - CCH - Master Logo Black [A3 Digital].png",
                       "3 - CCH - Master Logo White [A3 Digital].png"],
        "kit": "both",
        "positions": ["shorts_front"],
        "pricing_pct": 0.03,
    },
    "mna_cladding": {
        "display_name": "MNA Cladding",
        "logo_files": ["10 - MNA Cladding.png"],
        "kit": "both",
        "positions": ["collar_left"],
        "pricing_pct": 0.04,
    },
    "mna_support": {
        "display_name": "MNA Support Services",
        "logo_files": ["11 - MNA Support Services.png"],
        "kit": "both",
        "positions": ["collar_right"],
        "pricing_pct": 0.04,
    },
    "fairway": {
        "display_name": "Fairway Flooring",
        "logo_files": ["6 - Fairway Flooring Ltd Logo nO NUMBER.jpg"],
        "kit": "both",
        "positions": ["back_top"],
        "pricing_pct": 0.05,
    },
    "chadlaw": {
        "display_name": "ChadLaw",
        "logo_files": ["4 - ChadLaw1.png"],
        "kit": "both",
        "positions": ["sleeve_left"],
        "pricing_pct": 0.04,
    },
    "em_workwear": {
        "display_name": "EM Workwear",
        "logo_files": ["5 - EM workwear logo.png"],
        "kit": "both",
        "positions": ["socks"],
        "pricing_pct": 0.01,
    },
    "paints_laquers": {
        "display_name": "Paints & Laquers",
        "logo_files": ["Paints & Laquers Logo FINAL.jpg"],
        "kit": "both",
        "positions": ["shorts_back_center"],
        "pricing_pct": 0.03,
    },
}

# Pose-based ROI definitions.
# Each position maps to a lambda(keypoints) that returns (x1, y1, x2, y2)
# relative to the player bounding box.  Filled during pose module init.
# keypoints shape: (17, 3) — [x, y, conf] in absolute image coords.
#   COCO indices: 0=nose, 5=l_shoulder, 6=r_shoulder, 7=l_elbow, 8=r_elbow,
#                 11=l_hip, 12=r_hip, 13=l_knee, 14=r_knee
KIT_POSITIONS = {
    # Front-facing regions
    "chest_front":       {"facing": "front", "roi_fn": "chest_front"},
    "chest_left":        {"facing": "front", "roi_fn": "chest_left"},
    "chest_right":       {"facing": "front", "roi_fn": "chest_right"},
    "collar_left":       {"facing": "front", "roi_fn": "collar_left"},
    "collar_right":      {"facing": "front", "roi_fn": "collar_right"},
    "sleeve_left":       {"facing": "front", "roi_fn": "sleeve_left"},
    "sleeve_right":      {"facing": "front", "roi_fn": "sleeve_right"},
    "shorts_front":      {"facing": "front", "roi_fn": "shorts_front"},
    # Back-facing regions
    "back_top":          {"facing": "back",  "roi_fn": "back_top"},
    "back_upper":        {"facing": "back",  "roi_fn": "back_upper"},
    "back_mid":          {"facing": "back",  "roi_fn": "back_mid"},
    "back_lower":        {"facing": "back",  "roi_fn": "back_lower"},
    "shorts_back_left":  {"facing": "back",  "roi_fn": "shorts_back_left"},
    "shorts_back_right": {"facing": "back",  "roi_fn": "shorts_back_right"},
    "shorts_back_center":{"facing": "back",  "roi_fn": "shorts_back_center"},
    # Both
    "socks":             {"facing": "any",   "roi_fn": "socks"},
}

# Kit detection colour ranges in HSV
KIT_COLOR_PROFILES = {
    "home": {   # dominant white + red/amber/black bands
        "dominant_hsv": [(0, 0, 200), (180, 30, 255)],   # white range
        "accent_hsv":   [(0, 120, 100), (10, 255, 255)],  # red range
    },
    "away": {   # dominant black + red/amber/white bands
        "dominant_hsv": [(0, 0, 0), (180, 255, 60)],     # black range
        "accent_hsv":   [(0, 120, 100), (10, 255, 255)],  # red range
    },
}

# Quality score weights
QUALITY_WEIGHTS = {
    "size":      0.30,
    "position":  0.25,
    "clarity":   0.25,
    "occlusion": 0.20,
}

# Processing settings
PROC_SETTINGS = {
    "sample_fps": 2,          # frames to sample per second (2 = every 0.5s)
    "detect_conf": 0.35,      # YOLO person detection confidence
    "pose_conf":   0.30,
    "template_match_thresh": 0.45,  # ORB match ratio threshold
    "min_logo_px":  20,       # ignore logos smaller than this (px side)
    "blur_thresh":  80.0,     # Laplacian variance below = blurry
    "occlusion_pause_thresh": 0.80,  # > 80% occluded → pause timer
}
