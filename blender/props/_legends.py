"""Procedurally drawn RGBA legends baked as the *default* content of the runtime-swappable material slots.

Nothing here is a placeholder: each image is drawn to the published layout of the sign it represents (MUTCD
Standard Highway Signs for the federal regulatory signs, NYC DOT practice for the parking regulations and the
street-name blade) using the SIL-OFL Overpass typeface, an open Highway Gothic derivative shipped in
``assets/fonts/Overpass``. The engine overwrites the ``SIGN_FACE`` texture per instance from
``roads/signs.parquet`` (mutcd_code + text), so these are what a sign shows before that data is bound.

All functions are idempotent and cache into ``blender_out/props/textures/``; they need only PIL + numpy.
"""
from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

import _core as C

OUT = C.TEX_OUT
FONT_BOLD = C.FONT_BOLD
FONT_SEMI = C.FONT_SEMIBOLD

# MUTCD colours as sRGB bytes (same specs as C.MUTCD, kept here in 8-bit form for PIL).
RED = (176, 28, 46, 255)
WHITE = (242, 242, 242, 255)
BLACK = (17, 17, 17, 255)
GREEN = (0, 107, 84, 255)
ORANGE = (232, 119, 34, 255)
YELLOW = (255, 205, 0, 255)
BLUE = (0, 63, 135, 255)
PED_ORANGE = (255, 121, 24, 255)
PED_WHITE = (245, 245, 235, 255)


def _font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    path = FONT_BOLD if bold else FONT_SEMI
    if not Path(path).exists():
        raise FileNotFoundError(f"font missing: {path}")
    return ImageFont.truetype(str(path), size)


def _fit_text(draw: ImageDraw.ImageDraw, text: str, box_w: int, max_h: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    """Largest font size whose rendering of ``text`` fits in ``box_w`` x ``max_h``."""
    lo, hi = 6, max_h * 2
    best = _font(lo, bold)
    while lo <= hi:
        mid = (lo + hi) // 2
        f = _font(mid, bold)
        l, t, r, b = draw.textbbox((0, 0), text, font=f)
        if (r - l) <= box_w and (b - t) <= max_h:
            best, lo = f, mid + 1
        else:
            hi = mid - 1
    return best


def _centered(draw: ImageDraw.ImageDraw, xy, text: str, font, fill, anchor: str = "mm") -> None:
    draw.text(xy, text, font=font, fill=fill, anchor=anchor)


def _save(im: Image.Image, name: str) -> Path:
    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / name
    im.save(p)
    return p


def _px(width_m: float, height_m: float, ppm: int = 512) -> tuple[int, int]:
    """Pixel size of a sign face at ``ppm`` pixels per metre, clamped to sane texture sizes."""
    return (max(32, min(2048, round(width_m * ppm))), max(32, min(2048, round(height_m * ppm))))


# ------------------------------------------------------------------------------------- regulatory sign faces
def stop_r1_1(size_m: float = 0.762) -> Path:
    """R1-1: 30 in octagon, retroreflective red with a white border 0.75 in from the edge and 10 in STOP legend."""
    name = "sign_r1_1_stop.png"
    if (OUT / name).exists():
        return OUT / name
    n = _px(size_m, size_m)[0]
    im = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    r = n / 2 / math.cos(math.pi / 8)
    oct_pts = [(n / 2 + r * math.cos(math.pi / 8 + math.tau * k / 8), n / 2 + r * math.sin(math.pi / 8 + math.tau * k / 8)) for k in range(8)]
    d.polygon(oct_pts, fill=RED)
    inset = n * 0.030          # 0.75 in white border on a 30 in sign
    r2 = (n / 2 - inset) / math.cos(math.pi / 8)
    d.line([*[(n / 2 + r2 * math.cos(math.pi / 8 + math.tau * k / 8), n / 2 + r2 * math.sin(math.pi / 8 + math.tau * k / 8))
              for k in range(8)], (n / 2 + r2 * math.cos(math.pi / 8), n / 2 + r2 * math.sin(math.pi / 8))],
           fill=WHITE, width=max(2, round(n * 0.024)), joint="curve")
    f = _fit_text(d, "STOP", int(n * 0.74), int(n * 0.34))
    _centered(d, (n / 2, n / 2), "STOP", f, WHITE)
    return _save(im, name)


def yield_r1_2(w_m: float = 0.914, h_m: float = 0.792) -> Path:
    """R1-2: 36 in equilateral triangle, point down, red border 2.75 in wide, white field, red YIELD legend."""
    name = "sign_r1_2_yield.png"
    if (OUT / name).exists():
        return OUT / name
    w, h = _px(w_m, h_m)
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    tri = [(0, 0), (w - 1, 0), (w / 2, h - 1)]
    d.polygon(tri, fill=RED)
    m = w * 0.105
    inner = [(m * 1.05, m * 0.62), (w - m * 1.05, m * 0.62), (w / 2, h - m * 1.25)]
    d.polygon(inner, fill=WHITE)
    f = _fit_text(d, "YIELD", int(w * 0.52), int(h * 0.20))
    _centered(d, (w / 2, h * 0.34), "YIELD", f, RED)
    return _save(im, name)


def one_way_r6_1(w_m: float = 0.914, h_m: float = 0.305, direction: str = "right") -> Path:
    """R6-1: 36 x 12 in black plaque, white arrow at the pointing end and ONE WAY legend."""
    name = f"sign_r6_1_oneway_{direction}.png"
    if (OUT / name).exists():
        return OUT / name
    w, h = _px(w_m, h_m)
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, w - 1, h - 1], fill=BLACK)
    b = max(2, round(h * 0.045))
    d.rectangle([b, b, w - 1 - b, h - 1 - b], outline=WHITE, width=b)
    # arrow occupies the leading 45 % of the plaque, legend the trailing 55 %
    ax0, ax1 = w * 0.075, w * 0.46
    shaft_h = h * 0.16
    head_w = (ax1 - ax0) * 0.34
    cy = h / 2
    if direction == "right":
        d.polygon([(ax0, cy - shaft_h / 2), (ax1 - head_w, cy - shaft_h / 2), (ax1 - head_w, cy - shaft_h * 1.35),
                   (ax1, cy), (ax1 - head_w, cy + shaft_h * 1.35), (ax1 - head_w, cy + shaft_h / 2), (ax0, cy + shaft_h / 2)], fill=WHITE)
        tx = (ax1 + w * 0.94) / 2
    else:
        d.polygon([(ax1, cy - shaft_h / 2), (ax0 + head_w, cy - shaft_h / 2), (ax0 + head_w, cy - shaft_h * 1.35),
                   (ax0, cy), (ax0 + head_w, cy + shaft_h * 1.35), (ax0 + head_w, cy + shaft_h / 2), (ax1, cy + shaft_h / 2)], fill=WHITE)
        tx = (ax1 + w * 0.94) / 2
    f = _fit_text(d, "ONE WAY", int(w * 0.44), int(h * 0.52))
    _centered(d, (tx, cy), "ONE WAY", f, WHITE)
    return _save(im, name)


def speed_limit_r2_1(mph: int = 25, w_m: float = 0.610, h_m: float = 0.762) -> Path:
    """R2-1: 24 x 30 in white plaque, black border, SPEED / LIMIT / numeral. NYC citywide default limit is 25 mph."""
    name = f"sign_r2_1_speed_{mph}.png"
    if (OUT / name).exists():
        return OUT / name
    w, h = _px(w_m, h_m)
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, w - 1, h - 1], fill=WHITE)
    b = max(2, round(w * 0.030))
    d.rectangle([b, b, w - 1 - b, h - 1 - b], outline=BLACK, width=b)
    f1 = _fit_text(d, "SPEED", int(w * 0.72), int(h * 0.145))
    f2 = _fit_text(d, "LIMIT", int(w * 0.72), int(h * 0.145))
    f3 = _fit_text(d, str(mph), int(w * 0.62), int(h * 0.42))
    _centered(d, (w / 2, h * 0.155), "SPEED", f1, BLACK)
    _centered(d, (w / 2, h * 0.315), "LIMIT", f2, BLACK)
    _centered(d, (w / 2, h * 0.655), str(mph), f3, BLACK)
    return _save(im, name)


def _arrow_glyph(d: ImageDraw.ImageDraw, x: float, y: float, size: float, up: bool, color) -> None:
    s = size
    if up:
        d.polygon([(x, y - s), (x + s * 0.62, y - s * 0.18), (x + s * 0.26, y - s * 0.18), (x + s * 0.26, y + s),
                   (x - s * 0.26, y + s), (x - s * 0.26, y - s * 0.18), (x - s * 0.62, y - s * 0.18)], fill=color)
    else:
        d.polygon([(x, y + s), (x + s * 0.62, y + s * 0.18), (x + s * 0.26, y + s * 0.18), (x + s * 0.26, y - s),
                   (x - s * 0.26, y - s), (x - s * 0.26, y + s * 0.18), (x - s * 0.62, y + s * 0.18)], fill=color)


def _broom_glyph(d: ImageDraw.ImageDraw, cx: float, cy: float, s: float, color) -> None:
    """The broom pictogram of the NYC alternate-side-parking (street cleaning) signs: handle up-left, head down-right."""
    ux, uy = 0.55, -0.83                       # unit vector along the handle (up and to the right)
    hw = s * 0.10
    hx, hy = cx - ux * s * 0.15, cy - uy * s * 0.15
    d.polygon([(hx - uy * hw, hy + ux * hw), (hx + uy * hw, hy - ux * hw),
               (hx + ux * s * 1.55 + uy * hw, hy + uy * s * 1.55 - ux * hw),
               (hx + ux * s * 1.55 - uy * hw, hy + uy * s * 1.55 + ux * hw)], fill=color)
    # head: a trapezoid widening away from the handle, with bristles
    bx, by = cx - ux * s * 0.20, cy - uy * s * 0.20
    w0, w1 = s * 0.30, s * 0.70
    tipx, tipy = bx - ux * s * 0.55, by - uy * s * 0.55
    d.polygon([(bx - uy * w0, by + ux * w0), (bx + uy * w0, by - ux * w0),
               (tipx + uy * w1, tipy - ux * w1), (tipx - uy * w1, tipy + ux * w1)], fill=color)
    for i in range(7):
        t = -1.0 + 2.0 * i / 6.0
        sx, sy = bx + uy * w0 * t, by - ux * w0 * t
        ex, ey = tipx + uy * w1 * t - ux * s * 0.42, tipy - ux * w1 * t - uy * s * 0.42
        d.line([(sx, sy), (ex, ey)], fill=color, width=max(2, int(s * 0.10)))


def nyc_parking(lines: tuple[tuple[str, str], ...], w_m: float, h_m: float, name: str, *, arrows: str = "",
                symbol: str = "") -> Path:
    """NYC DOT parking regulation sign: white retroreflective plaque, red legend for prohibitions and green for
    permissions, a hairline border and (optionally) the double-headed regulation arrows. ``lines`` is
    ((text, "red"|"green"|"black"), ...) top to bottom; ``arrows`` is "" | "up" | "down" | "both"."""
    if (OUT / name).exists():
        return OUT / name
    w, h = _px(w_m, h_m, ppm=640)
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, w - 1, h - 1], fill=WHITE)
    b = max(2, round(w * 0.028))
    color_of = {"red": RED, "green": GREEN, "black": BLACK}
    d.rectangle([b, b, w - 1 - b, h - 1 - b], outline=color_of[lines[0][1]], width=b)
    top = h * 0.06
    arrow_h = h * 0.10 if arrows else 0.0
    if arrows:
        ay = h * 0.10
        c = color_of[lines[0][1]]
        if arrows in ("up", "both"):
            _arrow_glyph(d, w * 0.16, ay, w * 0.075, True, c)
        if arrows in ("down", "both"):
            _arrow_glyph(d, w * 0.84, ay, w * 0.075, False, c)
        top = ay + arrow_h
    sym_h = h * 0.26 if symbol else 0.0
    avail = h * 0.94 - top - sym_h
    lh = avail / len(lines)
    for i, (text, col) in enumerate(lines):
        f = _fit_text(d, text, int(w * 0.86), int(lh * 0.80))
        _centered(d, (w / 2, top + lh * (i + 0.5)), text, f, color_of[col])
    if symbol == "broom":
        _broom_glyph(d, w * 0.5, h * 0.94 - sym_h * 0.50, sym_h * 0.40, color_of[lines[0][1]])
    return _save(im, name)


def street_name_blade(street: str = "W 42 ST", block: str = "500", w_m: float = 0.762, h_m: float = 0.152) -> Path:
    """NYC street-name blade: reflective green field, white Highway-Gothic legend and a white hairline border,
    with the hundred-block number set small at the leading edge (the current DOT mixed-case blade layout)."""
    name = "sign_street_name.png"
    if (OUT / name).exists():
        return OUT / name
    w, h = _px(w_m, h_m, ppm=900)
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, w - 1, h - 1], fill=GREEN)
    b = max(2, round(h * 0.055))
    d.rectangle([b, b, w - 1 - b, h - 1 - b], outline=WHITE, width=b)
    fb = _fit_text(d, block, int(w * 0.13), int(h * 0.34))
    _centered(d, (w * 0.09, h * 0.30), block, fb, WHITE)
    f = _fit_text(d, street, int(w * 0.76), int(h * 0.60))
    _centered(d, (w * 0.55, h * 0.53), street, f, WHITE)
    return _save(im, name)


def road_work_w20_1(w_m: float = 1.219, h_m: float = 1.219) -> Path:
    """W20-1 ROAD WORK AHEAD: 48 in orange diamond with a black border and legend (rotated 45 deg on the blank)."""
    name = "sign_w20_1_roadwork.png"
    if (OUT / name).exists():
        return OUT / name
    w, h = _px(w_m, h_m, ppm=384)
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.polygon([(w / 2, 0), (w - 1, h / 2), (w / 2, h - 1), (0, h / 2)], fill=ORANGE)
    m = w * 0.055
    d.line([(w / 2, m * 1.42), (w - m * 1.42, h / 2), (w / 2, h - m * 1.42), (m * 1.42, h / 2), (w / 2, m * 1.42)],
           fill=BLACK, width=max(2, round(w * 0.020)), joint="curve")
    for i, t in enumerate(("ROAD", "WORK", "AHEAD")):
        f = _fit_text(d, t, int(w * 0.55), int(h * 0.135))
        _centered(d, (w / 2, h * (0.335 + 0.165 * i)), t, f, BLACK)
    return _save(im, name)


def push_button_r10_3e(w_m: float = 0.229, h_m: float = 0.305) -> Path:
    """R10-3e: push button for walk signal, with the walking-person symbol."""
    name = "sign_r10_3e_pushbutton.png"
    if (OUT / name).exists():
        return OUT / name
    w, h = _px(w_m, h_m, ppm=900)
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, w - 1, h - 1], fill=WHITE)
    b = max(2, round(w * 0.035))
    d.rectangle([b, b, w - 1 - b, h - 1 - b], outline=BLACK, width=b)
    for i, t in enumerate(("PUSH", "BUTTON", "FOR")):
        f = _fit_text(d, t, int(w * 0.80), int(h * 0.105))
        _centered(d, (w / 2, h * (0.13 + 0.115 * i)), t, f, BLACK)
    _walking_person(d, w * 0.5, h * 0.66, h * 0.13, BLACK)
    f = _fit_text(d, "SIGNAL", int(w * 0.80), int(h * 0.10))
    _centered(d, (w / 2, h * 0.90), "SIGNAL", f, BLACK)
    return _save(im, name)


# ------------------------------------------------------------------------------------- pedestrian signal faces
def _upraised_hand(d: ImageDraw.ImageDraw, cx: float, cy: float, s: float, color) -> None:
    """MUTCD upraised-palm symbol: four fingers, a thumb and a squared palm/wrist."""
    fw = s * 0.155                      # finger width
    for i, (dx, top) in enumerate(((-0.255, 0.62), (-0.085, 0.78), (0.085, 0.74), (0.255, 0.58))):
        x = cx + dx * s
        d.rounded_rectangle([x - fw / 2, cy - top * s, x + fw / 2, cy + s * 0.16], radius=fw * 0.45, fill=color)
    d.polygon([(cx - s * 0.36, cy - s * 0.05), (cx - s * 0.58, cy + s * 0.22), (cx - s * 0.46, cy + s * 0.40),
               (cx - s * 0.26, cy + s * 0.20)], fill=color)
    d.rounded_rectangle([cx - s * 0.36, cy - s * 0.10, cx + s * 0.36, cy + s * 0.72], radius=s * 0.12, fill=color)


def _walking_person(d: ImageDraw.ImageDraw, cx: float, cy: float, s: float, color) -> None:
    """MUTCD walking-person symbol: head, torso, striding legs, swinging arms (facing the reader's left)."""
    d.ellipse([cx - s * 0.20, cy - s * 1.30, cx + s * 0.20, cy - s * 0.90], fill=color)
    d.polygon([(cx - s * 0.22, cy - s * 0.85), (cx + s * 0.24, cy - s * 0.85), (cx + s * 0.20, cy + s * 0.02),
               (cx - s * 0.18, cy + s * 0.02)], fill=color)
    d.polygon([(cx - s * 0.20, cy - s * 0.80), (cx - s * 0.60, cy - s * 0.32), (cx - s * 0.44, cy - s * 0.16),
               (cx - s * 0.06, cy - s * 0.62)], fill=color)           # trailing arm
    d.polygon([(cx + s * 0.16, cy - s * 0.78), (cx + s * 0.52, cy - s * 0.40), (cx + s * 0.40, cy - s * 0.22),
               (cx + s * 0.04, cy - s * 0.58)], fill=color)           # leading arm
    d.polygon([(cx - s * 0.16, cy - s * 0.04), (cx + s * 0.04, cy - s * 0.04), (cx - s * 0.26, cy + s * 1.00),
               (cx - s * 0.50, cy + s * 0.94)], fill=color)           # trailing leg
    d.polygon([(cx + s * 0.02, cy - s * 0.04), (cx + s * 0.22, cy - s * 0.04), (cx + s * 0.50, cy + s * 0.92),
               (cx + s * 0.26, cy + s * 1.00)], fill=color)           # leading leg


def ped_symbol(kind: str = "hand") -> Path:
    """The left module of a NYC countdown pedestrian signal: portland-orange hand or white walking person on black."""
    name = f"ped_symbol_{kind}.png"
    if (OUT / name).exists():
        return OUT / name
    n = 256
    im = Image.new("RGBA", (n, n), (10, 10, 10, 255))
    d = ImageDraw.Draw(im)
    if kind == "hand":
        _upraised_hand(d, n * 0.5, n * 0.52, n * 0.40, PED_ORANGE)
    else:
        _walking_person(d, n * 0.5, n * 0.46, n * 0.38, PED_WHITE)
    return _save(im, name)


def ped_countdown(value: int = 12) -> Path:
    """The right module: two seven-segment portland-orange numerals on black."""
    name = f"ped_countdown_{value:02d}.png"
    if (OUT / name).exists():
        return OUT / name
    w, h = 176, 256
    im = Image.new("RGBA", (w, h), (10, 10, 10, 255))
    d = ImageDraw.Draw(im)
    seg = {0: "abcdef", 1: "bc", 2: "abdeg", 3: "abcdg", 4: "bcfg", 5: "acdfg", 6: "acdefg", 7: "abc", 8: "abcdefg", 9: "abcdfg"}
    for i, ch in enumerate(f"{value:02d}"):
        x0 = w * (0.08 + 0.47 * i)
        _seven_segment(d, x0, h * 0.12, w * 0.37, h * 0.76, seg[int(ch)], PED_ORANGE)
    return _save(im, name)


def _seven_segment(d: ImageDraw.ImageDraw, x: float, y: float, w: float, h: float, on: str, color) -> None:
    t = min(w, h * 0.5) * 0.24
    mid = y + h / 2
    bars = {"a": (x, y, x + w, y + t), "d": (x, y + h - t, x + w, y + h), "g": (x, mid - t / 2, x + w, mid + t / 2),
            "f": (x, y, x + t, mid), "b": (x + w - t, y, x + w, mid), "e": (x, mid, x + t, y + h), "c": (x + w - t, mid, x + w, y + h)}
    for k in on:
        d.rectangle(bars[k], fill=color)


# ------------------------------------------------------------------------------------- other faces
def linknyc_screen() -> Path:
    """LinkNYC display: the kiosk's idle screen — dark field, wordmark and the free-wifi strapline."""
    name = "linknyc_screen.png"
    if (OUT / name).exists():
        return OUT / name
    w, h = 512, 288
    im = Image.new("RGBA", (w, h), (12, 16, 26, 255))
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, w - 1, int(h * 0.30)], fill=(20, 60, 150, 255))
    f = _fit_text(d, "LinkNYC", int(w * 0.55), int(h * 0.18))
    _centered(d, (w / 2, h * 0.16), "LinkNYC", f, (245, 245, 245, 255))
    f2 = _fit_text(d, "FREE GIGABIT WI-FI", int(w * 0.78), int(h * 0.12))
    _centered(d, (w / 2, h * 0.50), "FREE GIGABIT WI-FI", f2, (200, 225, 255, 255))
    f3 = _fit_text(d, "PHONE CALLS  •  CHARGING  •  MAPS", int(w * 0.86), int(h * 0.09))
    _centered(d, (w / 2, h * 0.72), "PHONE CALLS  •  CHARGING  •  MAPS", f3, (150, 180, 220, 255))
    return _save(im, name)


def flag_us(w: int = 760, h: int = 400) -> Path:
    """US flag, exact proportions: hoist 1.0, fly 1.9, union 7/13 hoist x 0.76 fly, 13 stripes, 50 stars 9/6-5."""
    name = "flag_us.png"
    if (OUT / name).exists():
        return OUT / name
    old_glory_red, old_glory_blue = (178, 34, 52, 255), (60, 59, 110, 255)
    im = Image.new("RGBA", (w, h), (255, 255, 255, 255))
    d = ImageDraw.Draw(im)
    # Executive Order 10834 proportions: hoist A = 1.0, fly B = 1.9, union 0.5385 x 0.76,
    # star spacing 0.054 (hoist) x 0.063 (fly), star diameter 0.0616 of the hoist.
    upx = w / 1.9                      # pixels per "hoist unit"
    sh = h / 13.0
    for i in range(13):
        if i % 2 == 0:
            d.rectangle([0, i * sh, w, (i + 1) * sh], fill=old_glory_red)
    uw, uh = 0.76 * upx, sh * 7
    d.rectangle([0, 0, uw, uh], fill=old_glory_blue)
    star_r = 0.0616 / 2 * h
    for row in range(9):                                    # 6-5-6-5-6-5-6-5-6
        cnt = 6 if row % 2 == 0 else 5
        for col in range(cnt):
            cx = 0.063 * (2 * col + (1 if row % 2 == 0 else 2)) * upx
            cy = 0.054 * (row + 1) * h
            _star(d, cx, cy, star_r, (255, 255, 255, 255))
    return _save(im, name)


def _star(d: ImageDraw.ImageDraw, cx: float, cy: float, r: float, color) -> None:
    pts = []
    for i in range(10):
        a = -math.pi / 2 + math.pi * i / 5
        rr = r if i % 2 == 0 else r * 0.382
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    d.polygon(pts, fill=color)


def flag_nyc(w: int = 760, h: int = 400) -> Path:
    """Flag of the City of New York: blue-white-orange vertical tricolour (the Dutch Prince's flag colours) with the
    city seal centred in blue on the white bar. The seal is drawn as its principal charges — the windmill sails
    saltire, the two beavers, the two flour barrels and the date 1625 — not as the full engraved arms."""
    name = "flag_nyc.png"
    if (OUT / name).exists():
        return OUT / name
    blue, orange = (0, 47, 108, 255), (255, 108, 12, 255)
    im = Image.new("RGBA", (w, h), (255, 255, 255, 255))
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, w / 3, h], fill=blue)
    d.rectangle([2 * w / 3, 0, w, h], fill=orange)
    cx, cy, r = w / 2, h * 0.47, h * 0.30
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=blue, width=max(2, int(h * 0.012)))
    # windmill sails: a saltire of four tapered vanes
    for k in range(4):
        a = math.pi / 4 + k * math.pi / 2
        tip = (cx + r * 0.72 * math.cos(a), cy + r * 0.72 * math.sin(a))
        n = (-math.sin(a), math.cos(a))
        d.polygon([(cx + n[0] * r * 0.05, cy + n[1] * r * 0.05), (tip[0] + n[0] * r * 0.13, tip[1] + n[1] * r * 0.13),
                   (tip[0] - n[0] * r * 0.13, tip[1] - n[1] * r * 0.13), (cx - n[0] * r * 0.05, cy - n[1] * r * 0.05)], fill=blue)
    for sgn in (-1, 1):                      # beavers, above and below the hub
        by = cy + sgn * r * 0.44
        d.ellipse([cx - r * 0.16, by - r * 0.085, cx + r * 0.10, by + r * 0.085], fill=blue)
        d.polygon([(cx + r * 0.08, by - r * 0.02), (cx + r * 0.26, by - r * 0.09), (cx + r * 0.26, by + r * 0.05)], fill=blue)
    for sgn in (-1, 1):                      # flour barrels, left and right of the hub
        bx = cx + sgn * r * 0.46
        d.rounded_rectangle([bx - r * 0.10, cy - r * 0.13, bx + r * 0.10, cy + r * 0.13], radius=r * 0.05, fill=blue)
    f = _fit_text(d, "1625", int(r * 0.9), int(r * 0.22))
    _centered(d, (cx, cy + r * 0.82), "1625", f, blue)
    return _save(im, name)


def newsstand_ad() -> Path:
    """Back-lit advertising panel of the Cemusa street furniture (blank house ad, as delivered before a campaign)."""
    name = "ad_panel.png"
    if (OUT / name).exists():
        return OUT / name
    w, h = 384, 768
    im = Image.new("RGBA", (w, h), (238, 238, 240, 255))
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, w - 1, h - 1], outline=(200, 200, 205, 255), width=6)
    d.rectangle([w * 0.10, h * 0.10, w * 0.90, h * 0.62], fill=(30, 60, 120, 255))
    f = _fit_text(d, "NYC", int(w * 0.55), int(h * 0.12))
    _centered(d, (w / 2, h * 0.36), "NYC", f, (255, 255, 255, 255))
    f2 = _fit_text(d, "ADVERTISING SPACE", int(w * 0.80), int(h * 0.05))
    _centered(d, (w / 2, h * 0.74), "ADVERTISING SPACE", f2, (90, 90, 95, 255))
    return _save(im, name)


def subway_wordmark() -> Path:
    """The white-on-black SUBWAY plate carried by the entrance railing sign frame."""
    name = "subway_wordmark.png"
    if (OUT / name).exists():
        return OUT / name
    w, h = 768, 192
    im = Image.new("RGBA", (w, h), (12, 12, 12, 255))
    d = ImageDraw.Draw(im)
    f = _fit_text(d, "SUBWAY", int(w * 0.86), int(h * 0.62))
    _centered(d, (w / 2, h / 2), "SUBWAY", f, (245, 245, 245, 255))
    return _save(im, name)


def generate_all() -> dict[str, str]:
    """Bake every legend (used by the build and by the tests)."""
    made = {
        "stop": stop_r1_1(), "yield": yield_r1_2(), "one_way": one_way_r6_1(), "speed": speed_limit_r2_1(),
        "street_name": street_name_blade(), "road_work": road_work_w20_1(), "push_button": push_button_r10_3e(),
        "ped_hand": ped_symbol("hand"), "ped_man": ped_symbol("man"), "ped_count": ped_countdown(12),
        "linknyc": linknyc_screen(), "flag_us": flag_us(), "flag_nyc": flag_nyc(), "ad": newsstand_ad(),
        "subway": subway_wordmark(),
        "parking_no_standing": nyc_parking((("NO", "red"), ("STANDING", "red"), ("ANYTIME", "red")), 0.305, 0.457,
                                           "sign_nyc_no_standing.png", arrows="both"),
        "parking_alt_side": nyc_parking((("NO PARKING", "red"), ("8AM - 9:30AM", "red"), ("MON & THURS", "red"),
                                         ("STREET CLEANING", "red")), 0.305, 0.610,
                                        "sign_nyc_alt_side.png", arrows="both", symbol="broom"),
    }
    return {k: str(v) for k, v in made.items()}


if __name__ == "__main__":
    for k, v in generate_all().items():
        print(f"{k:22s} {v}")
