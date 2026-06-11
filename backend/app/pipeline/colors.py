"""Deterministic per-brand colours.

Shared by the annotated video (box colour) and the detection timeline (bar
colour) so a brand's box and its timeline track are the SAME colour. Uses a
stable FNV-1a hash — NOT Python's builtin hash(), which is salted per process
and would change colours on every restart.
"""
from __future__ import annotations

import colorsys


def _stable_hash(s: str) -> int:
    h = 2166136261
    for ch in s.encode("utf-8"):
        h = ((h ^ ch) * 16777619) & 0xFFFFFFFF
    return h


def brand_rgb(key: str) -> tuple[int, int, int]:
    hue = (_stable_hash(key) % 360) / 360.0
    r, g, b = colorsys.hsv_to_rgb(hue, 0.85, 1.0)
    return (int(r * 255), int(g * 255), int(b * 255))


def brand_bgr(key: str) -> tuple[int, int, int]:
    r, g, b = brand_rgb(key)
    return (b, g, r)


def brand_hex(key: str) -> str:
    r, g, b = brand_rgb(key)
    return f"#{r:02x}{g:02x}{b:02x}"
