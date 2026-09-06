"""Generated textures (PIL): tyre sidewall lettering, gauge faces, screens, plates, LED signs, taxi roof light,
leather seams and the per-vehicle livery atlas with its UV layout.

All images are written to ``blender_out/vehicles/textures/`` and embedded into the glb by the exporter.
No trademarked artwork is reproduced: wordmarks are set in Liberation Sans / DejaVu (stated in the report).
"""
from __future__ import annotations

import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from . import env
from .geom import FONT_DEJAVU_BOLD, FONT_MONO_BOLD, FONT_SANS, FONT_SANS_BOLD, FONT_SERIF_BOLD_ITALIC

log = env.log
RGB = tuple[int, int, int]


def hex_rgb(h: str) -> RGB:
    h = h.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def _font(path: str, px: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, max(6, int(px)))


def save(img: Image.Image, name: str) -> Path:
    env.TEX_DIR.mkdir(parents=True, exist_ok=True)
    p = env.TEX_DIR / f"{name}.png"
    img.save(p, optimize=False)
    return p


def text_fit(draw: ImageDraw.ImageDraw, xy: tuple[float, float], text: str, *, height_px: float, fill: RGB,
             font_path: str = FONT_SANS_BOLD, anchor: str = "mm", max_width_px: float | None = None, stroke: int = 0,
             stroke_fill: RGB | None = None) -> None:
    """Draw text with the cap height ≈ ``height_px`` (shrinks to fit ``max_width_px``)."""
    px = int(height_px * 1.35)
    font = _font(font_path, px)
    if max_width_px:
        while px > 6 and draw.textlength(text, font=font) > max_width_px:
            px -= 1
            font = _font(font_path, px)
    draw.text(xy, text, font=font, fill=fill, anchor=anchor, stroke_width=stroke, stroke_fill=stroke_fill)


# --------------------------------------------------------------------------- tyre sidewall
def tyre_sidewall(name: str, *, size_text: str, brand: str = "NYCSIM", model: str = "TOURING A/S",
                  v_sidewall_outer: tuple[float, float] = (0.05, 0.36), v_tread: tuple[float, float] = (0.40, 0.60),
                  w: int = 2048, h: int = 1024) -> Path:
    """Colour map in the revolve UV space of ``geom.revolve_bm`` (u around, v along the profile from the inner bead
    over the outer sidewall, tread and inner sidewall). Lettering is raised-look light grey on black."""
    img = Image.new("RGB", (w, h), (18, 18, 18))
    d = ImageDraw.Draw(img)
    v0, v1 = v_sidewall_outer
    y0, y1 = int((1 - v1) * h), int((1 - v0) * h)  # PIL y down
    # subtle rubber shading bands
    for y in range(y0, y1):
        t = (y - y0) / max(1, (y1 - y0))
        g = int(16 + 10 * math.sin(t * math.pi))
        d.line([(0, y), (w, y)], fill=(g, g, g))
    band_h = y1 - y0
    # tread: darker with groove lines (the geometry carries the real grooves; this only shades)
    t0, t1 = int((1 - v_tread[1]) * h), int((1 - v_tread[0]) * h)
    d.rectangle([0, t0, w, t1], fill=(12, 12, 12))
    for k in range(1, 5):
        yy = t0 + (t1 - t0) * k / 5
        d.line([(0, yy), (w, yy)], fill=(6, 6, 6), width=3)
    # lettering around the circumference: brand twice (opposite sides), size + markings between
    letter = (150, 150, 150)
    small = (120, 120, 120)
    cy = y0 + band_h * 0.45
    big_h = band_h * 0.30
    for k in range(2):
        cx = w * (0.25 + 0.5 * k)
        text_fit(d, (cx, cy), brand, height_px=big_h, fill=letter, font_path=FONT_DEJAVU_BOLD)
        text_fit(d, (cx, cy + band_h * 0.30), model, height_px=big_h * 0.45, fill=small, font_path=FONT_SANS_BOLD)
    for k in range(2):
        cx = w * (0.0 + 0.5 * k)
        text_fit(d, ((cx + w * 0.02) % w + w * 0.0, cy), size_text, height_px=big_h * 0.55, fill=letter, font_path=FONT_SANS_BOLD, anchor="lm")
        text_fit(d, ((cx + w * 0.02) % w, cy + band_h * 0.28), "TUBELESS RADIAL  M+S", height_px=big_h * 0.28, fill=small, anchor="lm")
        text_fit(d, ((cx + w * 0.02) % w, cy - band_h * 0.28), "TREADWEAR 500  TRACTION A  TEMPERATURE A", height_px=big_h * 0.22, fill=small, anchor="lm")
    # DOT code + max load line near the bead
    text_fit(d, (w * 0.75, y1 - band_h * 0.12), "DOT B3 NY 2919  MAX LOAD 670 kg (1477 lbs)  MAX PRESS 350 kPa (51 psi)", height_px=band_h * 0.09, fill=small)
    # inner sidewall (v > tread): plain
    return save(img, name)


# --------------------------------------------------------------------------- gauges and screens
def gauge_speedo(name: str = "gauge_speedo_160mph", *, max_mph: int = 160, w: int = 1024) -> Path:
    """Analogue speedometer face, 0..max_mph over a 240° sweep (7:30 to 4:30 o'clock), km/h inner ring,
    black face with white graduations; needle is a separate mesh, not painted."""
    img = Image.new("RGB", (w, w), (0, 0, 0))
    d = ImageDraw.Draw(img)
    c = w / 2
    R = w * 0.47
    d.ellipse([c - R, c - R, c + R, c + R], fill=(8, 8, 9), outline=(40, 40, 42), width=3)
    sweep = 240.0
    start = 210.0  # degrees, measured counter-clockwise from +x (PIL y is down -> we negate below)

    def polar(r: float, ang_deg: float) -> tuple[float, float]:
        a = math.radians(ang_deg)
        return (c + r * math.cos(a), c - r * math.sin(a))

    for mph in range(0, max_mph + 1, 5):
        frac = mph / max_mph
        ang = start - sweep * frac
        major = mph % 20 == 0
        r1 = R * 0.93
        r0 = R * (0.80 if major else 0.87)
        d.line([polar(r0, ang), polar(r1, ang)], fill=(235, 235, 235), width=6 if major else 3)
        if major:
            x, y = polar(R * 0.68, ang)
            text_fit(d, (x, y), str(mph), height_px=w * 0.055, fill=(240, 240, 240), font_path=FONT_SANS_BOLD)
    text_fit(d, (c, c + R * 0.25), "MPH", height_px=w * 0.035, fill=(200, 200, 200))
    # km/h inner ring (0..260 every 20)
    for kmh in range(0, 261, 20):
        mph_eq = kmh / 1.609344
        if mph_eq > max_mph:
            break
        ang = start - sweep * (mph_eq / max_mph)
        d.line([polar(R * 0.50, ang), polar(R * 0.54, ang)], fill=(150, 150, 150), width=2)
        x, y = polar(R * 0.43, ang)
        text_fit(d, (x, y), str(kmh), height_px=w * 0.026, fill=(160, 160, 160), font_path=FONT_SANS)
    text_fit(d, (c, c + R * 0.35), "km/h", height_px=w * 0.022, fill=(140, 140, 140), font_path=FONT_SANS)
    # hub
    d.ellipse([c - w * 0.03, c - w * 0.03, c + w * 0.03, c + w * 0.03], fill=(30, 30, 30))
    return save(img, name)


def cluster_lcd(name: str, *, w: int = 768, h: int = 512, title: str = "EV / HYBRID", accent: RGB = (80, 200, 255),
                bars: int = 12) -> Path:
    """Generic in-cluster LCD default image (the runtime redraws the slot). Dark UI, one arc meter, labels."""
    img = Image.new("RGB", (w, h), (4, 6, 10))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, w, h], outline=(30, 34, 40), width=4)
    text_fit(d, (w / 2, h * 0.12), title, height_px=h * 0.08, fill=(200, 205, 210))
    cx, cy, r = w / 2, h * 0.62, h * 0.36
    for i in range(bars):
        a0 = 200 - i * (220 / bars)
        col = accent if i < bars * 0.55 else (60, 66, 74)
        d.arc([cx - r, cy - r, cx + r, cy + r], start=-a0, end=-(a0 - 220 / bars * 0.8), fill=col, width=int(h * 0.05))
    text_fit(d, (w / 2, cy), "READY", height_px=h * 0.09, fill=(230, 230, 230))
    text_fit(d, (w * 0.5, h * 0.9), "ODO 038452 mi   RANGE 412 mi", height_px=h * 0.045, fill=(150, 155, 160), font_path=FONT_SANS)
    return save(img, name)


def screen_home(name: str = "screen_center_8in", *, w: int = 1024, h: int = 576) -> Path:
    """Generic 8-inch infotainment home screen (tiles: Navigation, Audio, Phone, Climate). Not a vendor UI."""
    img = Image.new("RGB", (w, h), (10, 14, 22))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, w, h * 0.12], fill=(18, 24, 36))
    text_fit(d, (w * 0.02, h * 0.06), "12:47  72°F  Broadway & W 57th St", height_px=h * 0.045, fill=(220, 225, 230), anchor="lm", font_path=FONT_SANS)
    tiles = [("NAVIGATION", (28, 90, 160)), ("AUDIO  FM 93.9", (40, 40, 60)), ("PHONE", (40, 60, 40)), ("CLIMATE  70°F", (60, 40, 40))]
    gx, gy = w * 0.03, h * 0.16
    tw, th = w * 0.455, h * 0.38
    for i, (label, col) in enumerate(tiles):
        x = gx + (i % 2) * (tw + w * 0.03)
        y = gy + (i // 2) * (th + h * 0.06)
        d.rounded_rectangle([x, y, x + tw, y + th], radius=int(h * 0.03), fill=col)
        text_fit(d, (x + tw * 0.05, y + th * 0.8), label, height_px=th * 0.16, fill=(235, 235, 240), anchor="lm")
    return save(img, name)


def plate_ny(name: str, number: str, *, w: int = 1024, h: int = 512, style: str = "passenger") -> Path:
    """NY-style plate: white field, dark-blue characters, blue header 'NEW YORK', footer 'EXCELSIOR'. This is a
    generated approximation of the current design (no DMV artwork); ``style='taxi'`` adds 'T&LC' and a yellow field."""
    field = (255, 226, 60) if style == "taxi" else (250, 250, 248)
    img = Image.new("RGB", (w, h), field)
    d = ImageDraw.Draw(img)
    blue = (14, 40, 96)
    d.rectangle([0, 0, w, h * 0.19], fill=(20, 52, 120))
    text_fit(d, (w / 2, h * 0.095), "NEW YORK", height_px=h * 0.10, fill=(255, 255, 255))
    text_fit(d, (w / 2, h * 0.58), number, height_px=h * 0.38, fill=blue, font_path=FONT_SANS_BOLD, max_width_px=w * 0.9)
    text_fit(d, (w / 2, h * 0.90), "T&LC" if style == "taxi" else "EXCELSIOR", height_px=h * 0.08, fill=blue)
    d.rectangle([0, 0, w - 1, h - 1], outline=(180, 180, 180), width=6)
    for cx in (w * 0.15, w * 0.85):
        d.ellipse([cx - 12, h * 0.05 - 12 + h * 0.19 * 0, cx + 12, h * 0.05 + 12], fill=(60, 60, 60))
    return save(img, name)


def led_sign(name: str, text: str, *, w: int = 1024, h: int = 256, color: RGB = (255, 150, 20), dot: int = 6,
             sub: str | None = None) -> Path:
    """Amber LED dot-matrix destination sign (SIGN_FRONT/SIDE/REAR default image; runtime redraws)."""
    base = Image.new("RGB", (w, h), (2, 2, 2))
    txt = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(txt)
    if sub:
        text_fit(d, (w / 2, h * 0.32), text, height_px=h * 0.36, fill=255, font_path=FONT_DEJAVU_BOLD, max_width_px=w * 0.95)
        text_fit(d, (w / 2, h * 0.75), sub, height_px=h * 0.26, fill=255, font_path=FONT_DEJAVU_BOLD, max_width_px=w * 0.95)
    else:
        text_fit(d, (w / 2, h / 2), text, height_px=h * 0.5, fill=255, font_path=FONT_DEJAVU_BOLD, max_width_px=w * 0.95)
    # dot matrix mask
    mask = Image.new("L", (w, h), 0)
    md = ImageDraw.Draw(mask)
    step = dot + 2
    for y in range(0, h, step):
        for x in range(0, w, step):
            md.ellipse([x, y, x + dot, y + dot], fill=255)
    lit = Image.new("RGB", (w, h), color)
    both = Image.composite(lit, base, Image.fromarray((__import__("numpy").asarray(txt) / 255 * __import__("numpy").asarray(mask)).astype("uint8")))
    both = both.filter(ImageFilter.GaussianBlur(0.6))
    return save(both, name)


def taxi_roof_light(name: str, medallion: str, *, w: int = 1024, h: int = 256, boro: bool = False) -> Path:
    """Roof light face: medallion number (lit) with 'OFF DUTY' side lamps. TAXI_ROOF slot default image."""
    bg = (255, 235, 120) if not boro else (200, 245, 170)
    img = Image.new("RGB", (w, h), bg)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, w * 0.18, h], fill=(50, 50, 50))
    d.rectangle([w * 0.82, 0, w, h], fill=(50, 50, 50))
    text_fit(d, (w * 0.09, h / 2), "OFF\nDUTY", height_px=h * 0.16, fill=(240, 240, 240), font_path=FONT_SANS_BOLD)
    text_fit(d, (w * 0.91, h / 2), "OFF\nDUTY", height_px=h * 0.16, fill=(240, 240, 240), font_path=FONT_SANS_BOLD)
    text_fit(d, (w / 2, h * 0.5), medallion, height_px=h * 0.6, fill=(10, 10, 10), font_path=FONT_DEJAVU_BOLD, max_width_px=w * 0.58)
    return save(img, name)


def ad_panel(name: str, *, w: int = 1024, h: int = 384, headline: str = "NYCSim — Drive all five boroughs",
             bg: RGB = (250, 250, 250), fg: RGB = (20, 20, 20)) -> Path:
    img = Image.new("RGB", (w, h), bg)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, w, h * 0.08], fill=(230, 40, 40))
    text_fit(d, (w / 2, h * 0.5), headline, height_px=h * 0.16, fill=fg, max_width_px=w * 0.92)
    text_fit(d, (w / 2, h * 0.82), "Ad panel slot — TAXI_AD_REAR (UV 0..1)", height_px=h * 0.07, fill=(90, 90, 90), font_path=FONT_SANS)
    return save(img, name)


def leather_seams(name: str = "leather_black_seams", *, w: int = 1024, rgb: RGB = (28, 26, 24), seam: RGB = (150, 140, 120),
                  panels: int = 6) -> Path:
    """Leather colour map with stitched panel seams (UV box-projected on seats, 0.5 m per tile)."""
    img = Image.new("RGB", (w, w), rgb)
    d = ImageDraw.Draw(img)
    import numpy as np
    rng = np.random.default_rng(3)
    grain = rng.normal(0, 4, (w, w, 1)).astype("int16")
    arr = np.clip(np.asarray(img).astype("int16") + grain, 0, 255).astype("uint8")
    img = Image.fromarray(arr)
    d = ImageDraw.Draw(img)
    step = w / panels
    for i in range(1, panels):
        y = int(i * step)
        d.line([(0, y), (w, y)], fill=(12, 11, 10), width=5)
        for x in range(0, w, 22):  # stitches
            d.line([(x, y - 9), (x + 10, y - 9)], fill=seam, width=3)
            d.line([(x, y + 9), (x + 10, y + 9)], fill=seam, width=3)
    return save(img, name)


def wordmark(name: str, text: str, *, w: int = 1024, h: int = 256, fg: RGB = (255, 255, 255), bg: RGB | None = None,
             font_path: str = FONT_SANS_BOLD, italic: bool = False) -> Path:
    """Transparent decal with a single wordmark (placards, app stickers)."""
    img = Image.new("RGBA", (w, h), (*bg, 255) if bg else (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    text_fit(d, (w / 2, h / 2), text, height_px=h * 0.55, fill=(*fg, 255), font_path=FONT_SERIF_BOLD_ITALIC if italic else font_path, max_width_px=w * 0.94)
    return save(img, name)


# --------------------------------------------------------------------------- livery atlas
@dataclass
class Atlas:
    """UV layout of a vehicle body: side_l / side_r (top half), top / front / rear (bottom half).
    Faces are assigned by dominant normal; painters draw in metres via the px_* helpers.

    Orientation matches a viewer standing outside: on the left side +X (front) is to the viewer's left, so u grows
    with -x; on the right side u grows with +x; front: u grows with +y; rear: u grows with -y; top: u with x, v with y."""
    x_min: float
    x_max: float
    z_max: float
    half_width: float
    size: tuple[int, int] = (4096, 2048)
    margin: float = 0.02

    def _rect(self, region: str) -> tuple[float, float, float, float]:
        return {"side_l": (0.0, 0.5, 0.5, 1.0), "side_r": (0.5, 1.0, 0.5, 1.0), "top": (0.0, 0.5, 0.0, 0.5),
                "front": (0.5, 0.75, 0.0, 0.5), "rear": (0.75, 1.0, 0.0, 0.5)}[region]

    def _norm(self, region: str, a: float, b: float) -> tuple[float, float]:
        """(a, b) world coords of the region's (horizontal, vertical) axes -> UV inside the region rect."""
        u0, u1, v0, v1 = self._rect(region)
        L = self.x_max - self.x_min
        if region == "side_l":
            fa = (self.x_max - a) / L
            fb = b / self.z_max
        elif region == "side_r":
            fa = (a - self.x_min) / L
            fb = b / self.z_max
        elif region == "top":
            fa = (a - self.x_min) / L
            fb = (b + self.half_width) / (2 * self.half_width)
        elif region == "front":
            fa = (a + self.half_width) / (2 * self.half_width)
            fb = b / self.z_max
        else:  # rear
            fa = (self.half_width - a) / (2 * self.half_width)
            fb = b / self.z_max
        m = self.margin
        fa = m + (1 - 2 * m) * min(max(fa, 0.0), 1.0)
        fb = m + (1 - 2 * m) * min(max(fb, 0.0), 1.0)
        return (u0 + (u1 - u0) * fa, v0 + (v1 - v0) * fb)

    def uv(self, co, normal) -> tuple[float, float]:
        nx, ny, nz = abs(normal.x), abs(normal.y), abs(normal.z)
        if nz >= nx and nz >= ny:
            return self._norm("top", co.x, co.y)
        if ny >= nx:
            return self._norm("side_l" if normal.y > 0 else "side_r", co.x, co.z)
        return self._norm("front" if normal.x > 0 else "rear", co.y, co.z)

    # pixel helpers for painters (PIL y grows downward)
    def px(self, region: str, a: float, b: float) -> tuple[float, float]:
        u, v = self._norm(region, a, b)
        return (u * self.size[0], (1.0 - v) * self.size[1])

    def px_per_m(self, region: str) -> tuple[float, float]:
        """(horizontal, vertical) pixels per metre in a region."""
        ax, ay = self.px(region, 0.0, 0.0)
        if region in ("side_l", "side_r"):
            bx, by = self.px(region, 1.0 if region == "side_r" else -1.0, 1.0)
        elif region == "top":
            bx, by = self.px(region, 1.0, 1.0)
        else:
            bx, by = self.px(region, 1.0 if region == "front" else -1.0, 1.0)
        return (abs(bx - ax), abs(by - ay))

    def region_box(self, region: str) -> tuple[int, int, int, int]:
        u0, u1, v0, v1 = self._rect(region)
        W, H = self.size
        return (int(u0 * W), int((1 - v1) * H), int(u1 * W), int((1 - v0) * H))


class Painter:
    """Draw livery elements in metres onto the atlas image."""

    def __init__(self, atlas: Atlas, base: RGB):
        self.atlas = atlas
        self.img = Image.new("RGB", atlas.size, base)
        self.d = ImageDraw.Draw(self.img)

    def fill_region(self, region: str, rgb: RGB) -> None:
        self.d.rectangle(self.atlas.region_box(region), fill=rgb)

    def rect(self, region: str, a0: float, b0: float, a1: float, b1: float, rgb: RGB) -> None:
        x0, y0 = self.atlas.px(region, a0, b0)
        x1, y1 = self.atlas.px(region, a1, b1)
        self.d.rectangle([min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)], fill=rgb)

    def band(self, z0: float, z1: float, rgb: RGB, *, sides: bool = True, front: bool = False, rear: bool = False,
             x0: float | None = None, x1: float | None = None) -> None:
        """Horizontal stripe between heights z0..z1 (all around by default)."""
        a = self.atlas
        xa = a.x_min if x0 is None else x0
        xb = a.x_max if x1 is None else x1
        if sides:
            for side in ("side_l", "side_r"):
                self.rect(side, xa, z0, xb, z1, rgb)
        if front:
            self.rect("front", -a.half_width, z0, a.half_width, z1, rgb)
        if rear:
            self.rect("rear", -a.half_width, z0, a.half_width, z1, rgb)

    def checker(self, z0: float, z1: float, rows: int = 2, colors: tuple[RGB, RGB] = ((0, 0, 0), (255, 255, 255)),
                x0: float | None = None, x1: float | None = None) -> None:
        a = self.atlas
        xa = a.x_min if x0 is None else x0
        xb = a.x_max if x1 is None else x1
        cell = (z1 - z0) / rows
        n = int((xb - xa) / cell)
        for side in ("side_l", "side_r"):
            for i in range(n):
                for r in range(rows):
                    col = colors[(i + r) % 2]
                    self.rect(side, xa + i * cell, z0 + r * cell, xa + (i + 1) * cell, z0 + (r + 1) * cell, col)

    def text(self, region: str, a: float, b: float, text: str, height_m: float, rgb: RGB, *, font_path: str = FONT_SANS_BOLD,
             anchor: str = "mm", max_width_m: float | None = None, stroke_m: float = 0.0, stroke_rgb: RGB | None = None) -> None:
        x, y = self.atlas.px(region, a, b)
        ppm_h, ppm_v = self.atlas.px_per_m(region)
        text_fit(self.d, (x, y), text, height_px=height_m * ppm_v, fill=rgb, font_path=font_path, anchor=anchor,
                 max_width_px=max_width_m * ppm_h if max_width_m else None, stroke=int(stroke_m * ppm_v), stroke_fill=stroke_rgb)

    def text_both_sides(self, x: float, z: float, text: str, height_m: float, rgb: RGB, **kw) -> None:
        for side in ("side_l", "side_r"):
            self.text(side, x, z, text, height_m, rgb, **kw)

    def circle(self, region: str, a: float, b: float, radius_m: float, rgb: RGB, outline: RGB | None = None, width_m: float = 0.0) -> None:
        x, y = self.atlas.px(region, a, b)
        ppm_h, ppm_v = self.atlas.px_per_m(region)
        rx, ry = radius_m * ppm_h, radius_m * ppm_v
        self.d.ellipse([x - rx, y - ry, x + rx, y + ry], fill=rgb, outline=outline, width=int(width_m * ppm_v))

    def polygon(self, region: str, pts_m: Sequence[tuple[float, float]], rgb: RGB) -> None:
        self.d.polygon([self.atlas.px(region, a, b) for a, b in pts_m], fill=rgb)

    def diagonal_band(self, region: str, a0: float, b0: float, a1: float, b1: float, width_m: float, rgb: RGB) -> None:
        """Sloping stripe from (a0,b0) to (a1,b1) with the given vertical thickness."""
        self.polygon(region, [(a0, b0), (a1, b1), (a1, b1 + width_m), (a0, b0 + width_m)], rgb)

    def save(self, name: str) -> Path:
        return save(self.img, name)


def nyc_taxi_logo(p: Painter, region: str, x: float, z: float, scale: float = 1.0) -> None:
    """'NYC' wordmark + circled 'T' emblem as used on medallion cabs (type set in Liberation Sans, not the official
    artwork)."""
    h = 0.13 * scale
    p.text(region, x - 0.16 * scale, z, "NYC", h, (0, 0, 0), font_path=FONT_DEJAVU_BOLD)
    p.circle(region, x + 0.14 * scale, z, 0.085 * scale, (0, 0, 0))
    p.text(region, x + 0.14 * scale, z, "T", 0.10 * scale, (247, 181, 0), font_path=FONT_DEJAVU_BOLD)
    p.text(region, x, z - 0.11 * scale, "TAXI", 0.05 * scale, (0, 0, 0))


def tlc_diamond(p: Painter, region: str, a: float, b: float, size: float = 0.09) -> None:
    """TLC 'diamond' FHV inspection sticker (generic geometry: black diamond, white 'T&LC' text)."""
    p.polygon(region, [(a, b + size), (a + size, b), (a, b - size), (a - size, b)], (20, 20, 20))
    p.text(region, a, b, "T&LC", size * 0.45, (255, 255, 255))
