"""Generates a game-style heart icon (red body, thick dark outline, glossy highlight).

Usage: python3 tools/make_heart.py
Writes PNGs with transparent background into assets/ui/.
"""
import os

import numpy as np
from PIL import Image

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "assets", "ui")

# Palette sampled from the reference HP bar
OUTLINE = np.array([0x2A, 0x2A, 0x2A], float)
RED = np.array([0xE0, 0x44, 0x37], float)        # main body (slightly brighter than the reference)
RED_SHADE = np.array([0xA8, 0x30, 0x2A], float)  # shadow at the lower-left edge
RED_RIM = np.array([0x7A, 0x24, 0x22], float)    # thin dark-red rim inside the outline
WHITE = np.array([0xFF, 0xFF, 0xFF], float)

SUPERSAMPLE = 8


def sd_circle(x, y, cx, cy, r):
    return np.hypot(x - cx, y - cy) - r


def sd_segment(x, y, ax, ay, bx, by):
    px, py = x - ax, y - ay
    dx, dy = bx - ax, by - ay
    t = np.clip((px * dx + py * dy) / (dx * dx + dy * dy), 0, 1)
    return np.hypot(px - t * dx, py - t * dy)


def sd_polygon(x, y, pts):
    d = np.full(x.shape, np.inf)
    inside = np.zeros(x.shape, bool)
    n = len(pts)
    for i in range(n):
        ax, ay = pts[i]
        bx, by = pts[(i + 1) % n]
        d = np.minimum(d, sd_segment(x, y, ax, ay, bx, by))
        cond = ((ay > y) != (by > y)) & (x < (bx - ax) * (y - ay) / (by - ay + 1e-12) + ax)
        inside ^= cond
    return np.where(inside, -d, d)


def sd_heart(x, y):
    """Heart in a [-1, 1] box: two round lobes and a point at the bottom."""
    r = 0.47
    lx, rx, cy = -0.46, 0.46, -0.30
    tip = (0.0, 0.90)
    # Tangent points of the lobes, so the sides blend smoothly into the tip
    def tangent(cx):
        dx, dy = tip[0] - cx, tip[1] - cy
        dist = np.hypot(dx, dy)
        ang = np.arctan2(dy, dx) - np.sign(cx) * np.arccos(r / dist)
        return cx + r * np.cos(ang), cy + r * np.sin(ang)
    tl, tr = tangent(lx), tangent(rx)
    body = sd_polygon(x, y, [tl, tip, tr, (rx, cy), (lx, cy)])
    # Centre fill keeps the inside smooth between the lobes (no seam in the shading)
    body = np.minimum(body, sd_circle(x, y, 0.0, 0.05, 0.43))
    return np.minimum(np.minimum(sd_circle(x, y, lx, cy, r), sd_circle(x, y, rx, cy, r)), body)


def smoothstep(e0, e1, v):
    t = np.clip((v - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


def render(size, outline=0.13):
    n = size * SUPERSAMPLE
    c = (np.arange(n) + 0.5) / n * 2.0 - 1.0
    x, y = np.meshgrid(c * 1.12, c * 1.12 + 0.03)
    d = sd_heart(x, y)

    # Body shading: lit from the upper right, shadow toward the lower left
    light = np.clip(0.55 + 0.45 * (x * 0.6 - y * 0.8), 0, 1)
    edge = smoothstep(-0.22, 0.0, d)  # 0 deep inside, 1 at the edge
    shade = np.clip(edge * (1.0 - light) * 1.6, 0, 1)[..., None]
    col = RED * (1 - shade) + RED_SHADE * shade

    # Thin dark-red rim just inside the outline
    rim = smoothstep(-0.06, -0.01, d)[..., None]
    col = col * (1 - rim) + RED_RIM * rim

    # Main glossy highlight: a crescent on the upper-right lobe
    hl = sd_circle(x, y, 0.46, -0.30, 0.31)
    cut = sd_circle(x, y, 0.36, -0.20, 0.30)
    crescent = np.maximum(hl, -cut)
    crescent = np.maximum(crescent, -(y + 0.65 - x * 0.0))  # keep it under the top edge
    hmask = ((crescent < 0) & (y < 0.05) & (x > 0.22)).astype(float)[..., None]
    col = col * (1 - hmask) + WHITE * hmask

    # Small extra sparkle on the left lobe (the "slight change" vs. the reference)
    spark = (sd_circle(x, y, -0.58, -0.44, 0.075) < 0).astype(float)[..., None]
    col = col * (1 - spark * 0.85) + WHITE * spark * 0.85

    # Thick dark outline around everything
    is_outline = ((d >= 0) & (d < outline))[..., None]
    col = np.where(is_outline, OUTLINE, col)
    alpha = (d < outline).astype(float)

    rgba = np.dstack([col * alpha[..., None], alpha * 255])
    img = Image.fromarray(rgba.clip(0, 255).astype(np.uint8), "RGBA")
    # Downsample premultiplied colour for clean anti-aliasing, then un-premultiply
    small = np.asarray(img.resize((size, size), Image.BOX), float)
    a = small[..., 3:4] / 255.0
    rgb = np.where(a > 0, small[..., :3] / np.maximum(a, 1e-6), 0)
    out = np.dstack([rgb, small[..., 3:4]]).clip(0, 255).astype(np.uint8)
    return Image.fromarray(out, "RGBA")


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    for size in (24, 32, 64, 128, 256, 512):
        render(size).save(os.path.join(OUT_DIR, f"heart_{size}.png"))
    # Pixel-art variant: 24px icon scaled up without smoothing
    render(24).resize((192, 192), Image.NEAREST).save(os.path.join(OUT_DIR, "heart_24_x8_pixel.png"))


if __name__ == "__main__":
    main()
