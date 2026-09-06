"""Procedural alpha leaf cards and tree impostors for the street-tree props.

Nothing is downloaded: every leaf silhouette is drawn from the species' botanical leaf form (palmate for the
maples and the planetree, pinnately compound for honeylocust and Sophora, pinnately lobed for pin oak, cordate
for littleleaf linden, obovate-glossy for Callery pear, elliptic-serrate for zelkova, flabellate for ginkgo),
composited into a 2x2 cluster atlas with alpha, and cached in ``blender_out/props/textures/``.

The LOD1 impostor is drawn from the *same* geometry the LOD0 tree is built from — the leaf-card centres and the
branch polyline are projected orthographically — so the billboard silhouette matches the mesh it replaces.
"""
from __future__ import annotations

import math
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

import _core as C

OUT = C.TEX_OUT
ATLAS_PX = 512
IMPOSTOR_PX = 512

# Per-species leaf form and summer colour (sRGB). Colours are the mid-summer foliage of the species; the engine
# drives autumn colour from the season, so only the summer set is baked.
LEAF_FORMS: dict[str, dict] = {
    "planetree":        {"kind": "palmate", "lobes": 5, "green": (86, 122, 60), "green2": (108, 145, 72), "size": 0.86},
    "honeylocust":      {"kind": "pinnate", "pairs": 9, "green": (124, 156, 74), "green2": (146, 176, 92), "size": 0.95},
    "callery_pear":     {"kind": "ovate", "green": (52, 92, 52), "green2": (74, 116, 66), "size": 0.70, "gloss": True},
    "pin_oak":          {"kind": "oak", "green": (58, 92, 50), "green2": (80, 116, 62), "size": 0.80},
    "norway_maple":     {"kind": "palmate", "lobes": 5, "green": (54, 88, 48), "green2": (74, 110, 60), "size": 0.92, "broad": True},
    "littleleaf_linden": {"kind": "cordate", "green": (92, 128, 62), "green2": (114, 150, 78), "size": 0.66},
    "ginkgo":           {"kind": "fan", "green": (122, 152, 66), "green2": (146, 174, 86), "size": 0.62},
    "zelkova":          {"kind": "elliptic", "green": (80, 116, 60), "green2": (102, 138, 74), "size": 0.60},
    "sophora":          {"kind": "pinnate", "pairs": 7, "green": (96, 138, 66), "green2": (118, 158, 84), "size": 0.88},
    "red_maple":        {"kind": "palmate", "lobes": 3, "green": (72, 108, 56), "green2": (94, 130, 70), "size": 0.80},
}


# ------------------------------------------------------------------------------------- leaf silhouettes
def _blade(width: float, p: float, q: float, n: int = 40, serr: int = 0, amp: float = 0.0,
           lobe: int = 0, lobe_depth: float = 0.0) -> list[tuple[float, float]]:
    """Half-width profile w(t) swept up the midrib, mirrored into a closed outline (t = 0 petiole, 1 tip)."""
    raw = [(i / n, (max(i / n, 1e-4) ** p) * ((1.0 - i / n) ** q)) for i in range(n + 1)]
    m = max(w for _, w in raw) or 1.0
    right = []
    for t, w in raw:
        ww = width * w / m
        if serr:
            ww *= 1.0 + amp * math.sin(serr * math.pi * t)
        if lobe:
            ww *= 1.0 - lobe_depth * (0.5 - 0.5 * math.cos(2.0 * lobe * math.pi * t))
        right.append((ww, t))
    return right + [(-w, t) for w, t in reversed(right)]


def leaf_shapes(kind: str, form: dict) -> list[list[tuple[float, float]]]:
    """Polygons of one leaf in a unit frame: petiole at (0, 0), tip at (0, 1), width within +-0.5."""
    if kind == "palmate":
        lobes = form.get("lobes", 5)
        span = math.radians(105.0 if form.get("broad") else 95.0)
        pts = []
        n = 132
        for i in range(n + 1):
            phi = -span + 2 * span * i / n
            u = phi / span * math.pi                       # -pi..pi across the blade
            lobe = abs(math.cos(lobes / 2.0 * u)) ** 0.42
            r = 0.52 * (0.34 + 0.66 * lobe)
            sinus = 1.0 - 0.16 * (1.0 - lobe)              # deep sinuses between the lobes
            pts.append((r * math.sin(phi) * 1.05, 0.10 + r * math.cos(phi) * sinus * 1.75))
        return [pts + [(0.0, 0.0)]]
    if kind == "oak":
        return [_blade(0.33, 0.46, 0.60, 72, lobe=5, lobe_depth=0.46, serr=0)]
    if kind == "ovate":
        return [_blade(0.27, 0.50, 0.68, 40, serr=26, amp=0.035)]
    if kind == "elliptic":
        return [_blade(0.22, 0.42, 0.70, 40, serr=20, amp=0.075)]
    if kind == "cordate":
        blade = _blade(0.33, 0.30, 0.78, 44, serr=24, amp=0.045)
        # heart-shaped base: two small lobes below the petiole insertion
        base = [(0.10, -0.02), (0.16, -0.07), (0.06, -0.10), (0.0, -0.05), (-0.06, -0.10), (-0.16, -0.07), (-0.10, -0.02)]
        return [blade + base]
    if kind == "fan":
        pts = [(0.0, 0.0)]
        n = 40
        for i in range(n + 1):
            a = math.radians(-58.0 + 116.0 * i / n)
            notch = 1.0 - 0.20 * math.exp(-((a / math.radians(9.0)) ** 2))
            r = 1.0 * notch
            pts.append((r * math.sin(a) * 0.62, r * math.cos(a)))
        return [pts]
    if kind == "pinnate":
        pairs = form.get("pairs", 9)
        polys = [[(-0.009, 0.0), (0.009, 0.0), (0.005, 1.0), (-0.005, 1.0)]]     # rachis
        for k in range(pairs):
            t = 0.08 + 0.90 * k / max(1, pairs - 1)
            ll = 0.21 * (1.0 - 0.30 * abs(t - 0.50))
            lw = ll * 0.40
            for sgn in (-1.0, 1.0):
                a = math.radians(48.0) * sgn
                cx, cy = sgn * 0.02, t
                poly = []
                for i in range(13):
                    u = i / 12
                    w = lw * math.sin(math.pi * max(u, 1e-3) ** 0.6)
                    poly.append((u * ll, w))
                for i in range(12, -1, -1):
                    u = i / 12
                    w = lw * math.sin(math.pi * max(u, 1e-3) ** 0.6)
                    poly.append((u * ll, -w))
                polys.append([(cx + x * math.cos(a) - y * math.sin(a), cy + x * math.sin(a) + y * math.cos(a)) for x, y in poly])
        return polys
    raise ValueError(f"unknown leaf kind {kind}")


def _draw_leaf(d: ImageDraw.ImageDraw, polys, cx: float, cy: float, size: float, rot_deg: float, color, vein) -> None:
    ca, sa = math.cos(math.radians(rot_deg)), math.sin(math.radians(rot_deg))
    compound = len(polys) > 1
    edge = max(1, int(size * 0.009)) if compound else 0
    for i, poly in enumerate(polys):
        pts = [(cx + (x * ca - y * sa) * size, cy - (x * sa + y * ca) * size) for x, y in poly]
        # compound leaves get a thin vein-coloured edge so the individual leaflets stay legible at texture scale
        d.polygon(pts, fill=color, outline=vein if compound else None, width=edge)
        if i == 0 and not compound:
            d.line([(cx, cy), (cx - sa * size, cy - ca * size)], fill=vein, width=max(1, int(size * 0.018)))


def leaf_atlas(species: str, seed: int = 7) -> Path:
    """2x2 atlas of leaf-cluster cards for one species (RGBA, straight alpha)."""
    name = f"leaf_{species}.png"
    if (OUT / name).exists():
        return OUT / name
    form = LEAF_FORMS[species]
    polys = leaf_shapes(form["kind"], form)
    rng = random.Random(seed)
    im = Image.new("RGBA", (ATLAS_PX, ATLAS_PX), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    half = ATLAS_PX // 2
    for q in range(4):
        ox, oy = (q % 2) * half, (q // 2) * half
        n_leaves = 9 if form["kind"] != "pinnate" else 7
        for _ in range(n_leaves):
            base = form["green"] if rng.random() < 0.55 else form["green2"]
            jitter = rng.randint(-14, 14)
            color = tuple(max(0, min(255, c + jitter)) for c in base) + (255,)
            vein = tuple(max(0, int(c * 0.72)) for c in base) + (255,)
            size = half * form["size"] * rng.uniform(0.45, 0.70)
            cx = ox + half * rng.uniform(0.22, 0.78)
            cy = oy + half * rng.uniform(0.30, 0.92)
            _draw_leaf(d, polys, cx, cy, size, rng.uniform(0, 360), color, vein)
    OUT.mkdir(parents=True, exist_ok=True)
    im.save(OUT / name)
    return OUT / name


def leaf_card_uv(index: int) -> tuple[float, float, float, float]:
    """(u0, v0, u1, v1) of one of the four cluster cards in the atlas."""
    q = index % 4
    return (0.5 * (q % 2), 0.5 * (q // 2), 0.5 * (q % 2) + 0.5, 0.5 * (q // 2) + 0.5)


# ------------------------------------------------------------------------------------- impostor billboards
def impostor(name: str, branch_segments, leaf_points, height: float, half_width: float, species: str,
             bare: bool) -> Path:
    """Orthographic RGBA silhouette of the tree that LOD0 actually built: branches as tapered strokes, leaf cards
    as soft blobs in the species' foliage colour. ``branch_segments`` is [((x,z),(x,z),radius), ...] in metres,
    ``leaf_points`` is [(x, z, card_size_m), ...]."""
    path = OUT / f"impostor_{name}.png"
    if path.exists():
        return path
    form = LEAF_FORMS[species]
    px = IMPOSTOR_PX
    scale = px / (2.0 * max(half_width, height / 2.0) * 1.04)
    cx = px / 2.0

    def to_px(x, z):
        return (cx + x * scale, px - 4.0 - z * scale)

    im = Image.new("RGBA", (px, px), (0, 0, 0, 0))
    if not bare:
        foliage = Image.new("RGBA", (px, px), (0, 0, 0, 0))
        fd = ImageDraw.Draw(foliage)
        rng = random.Random(len(leaf_points) * 977 + 13)
        for (x, z, s) in leaf_points:
            r = max(2.0, s * scale * 0.62)
            base = form["green"] if rng.random() < 0.5 else form["green2"]
            j = rng.randint(-12, 12)
            col = tuple(max(0, min(255, c + j)) for c in base) + (236,)
            px0, py0 = to_px(x, z)
            fd.ellipse([px0 - r, py0 - r * 0.82, px0 + r, py0 + r * 0.82], fill=col)
        foliage = foliage.filter(ImageFilter.GaussianBlur(px / 220.0))
        im.alpha_composite(foliage)
    wood = Image.new("RGBA", (px, px), (0, 0, 0, 0))
    wd = ImageDraw.Draw(wood)
    for (a, b, radius) in branch_segments:
        w = max(1.0, radius * 2.0 * scale)
        wd.line([to_px(*a), to_px(*b)], fill=(74, 62, 50, 255), width=int(round(w)))
    im.alpha_composite(wood)
    if not bare:                                    # a second, thinner foliage pass in front of the branches
        front = Image.new("RGBA", (px, px), (0, 0, 0, 0))
        fd = ImageDraw.Draw(front)
        rng = random.Random(len(leaf_points) * 31 + 5)
        for (x, z, s) in leaf_points:
            if rng.random() < 0.45:
                continue
            r = max(2.0, s * scale * 0.52)
            base = form["green2"]
            col = tuple(max(0, min(255, c + rng.randint(-10, 16))) for c in base) + (210,)
            px0, py0 = to_px(x, z)
            fd.ellipse([px0 - r, py0 - r * 0.8, px0 + r, py0 + r * 0.8], fill=col)
        im.alpha_composite(front.filter(ImageFilter.GaussianBlur(px / 240.0)))
    OUT.mkdir(parents=True, exist_ok=True)
    im.save(path)
    return path


def generate_all_atlases() -> dict[str, str]:
    return {s: str(leaf_atlas(s)) for s in LEAF_FORMS}


if __name__ == "__main__":
    for k, v in generate_all_atlases().items():
        print(f"{k:20s} {v}")
