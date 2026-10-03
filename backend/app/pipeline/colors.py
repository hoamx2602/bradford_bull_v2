"""Deterministic per-brand colours.

Shared by the annotated video (box colour) and the detection timeline (bar
colour) so a brand's box and its timeline track are the SAME colour. Uses a
stable FNV-1a hash — NOT Python's builtin hash(), which is salted per process
and would change colours on every restart.
"""
from __future__ import annotations

import colorsys
from app.config import normalize_class

# Explicit distinct colours for the trained sponsor roster; hashing alone can
# put different brands only one degree apart on the hue wheel.
BRAND_HEX = dict(zip(
    ['aon','asc_group','atm','bartercard','cch','chadlaw','ellgren','em_workwear',
     'fairway','floor_tonic','klg','mcp','mna_cladding','mna_support_service',
     'paints_lacquers','romantica','top_notch'],
    ['#FF6B6B','#00D4FF','#FBBF24','#A78BFA','#34D399','#F472B6','#60A5FA',
     '#FB923C','#B8E986','#F5A6C8','#FFE14D','#FF8A65','#80CBC4','#E879F9',
     '#B0BEC5','#FFFFFF','#C5F000']))
ALIASES = {'acs_group':'asc_group','romatica':'romantica',
           'mna_support':'mna_support_service'}


def _stable_hash(s: str) -> int:
    h = 2166136261
    for ch in s.encode("utf-8"):
        h = ((h ^ ch) * 16777619) & 0xFFFFFFFF
    return h


def brand_rgb(key: str) -> tuple[int, int, int]:
    key = normalize_class(key)
    key = ALIASES.get(key, key)
    if key in BRAND_HEX:
        color = BRAND_HEX[key].lstrip('#')
        return tuple(int(color[i:i+2],16) for i in (0,2,4))
    hue = (_stable_hash(key) % 360) / 360.0
    r, g, b = colorsys.hsv_to_rgb(hue, 0.85, 1.0)
    return (int(r * 255), int(g * 255), int(b * 255))


def brand_bgr(key: str) -> tuple[int, int, int]:
    r, g, b = brand_rgb(key)
    return (b, g, r)


def brand_hex(key: str) -> str:
    r, g, b = brand_rgb(key)
    return f"#{r:02x}{g:02x}{b:02x}"
