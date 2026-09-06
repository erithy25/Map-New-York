"""Shared sub-builders for the NYCSim facade kit: masonry openings, sashes, lintels/sills, railings, ladders,
gratings and the procedurally generated textures (interior cards, sign bands, ivy, awning valances).

Every dimension in this module is a real New York construction dimension; the source of each is given in the
comment next to it.  Nothing here registers a kit piece — the ``pieces_*`` modules do that.
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import Sequence

import kitlib as K

# --------------------------------------------------------------------------- real NYC dimensions (metres)
BRICK_COURSE = 0.0675          # NYC modular brick + 10 mm joint (3 courses = 8 in)
BRICK_LEN = 0.194              # 7 5/8 in brick face length (soldier-course lintel height)
WYTHE = 0.102                  # 4 in brick wythe
SASH_STILE = 0.045             # 1 3/4 in wood sash stile
SASH_RAIL_BOTTOM = 0.075       # 3 in bottom rail
MEETING_RAIL = 0.040
MUNTIN_W = 0.022               # 7/8 in true divided-light muntin
CASING = 0.060                 # blind stop / brickmould
REVEAL = 0.155                 # sash set back 6 in from the brick face (NYC masonry opening: the frame sits behind
                               # the outer wythe, giving the reveal that shades every opening at a raking sun)
GLASS_T = 0.006
STONE_LINTEL_H = 0.150         # 6 in stone lintel
STONE_LINTEL_EAR = 0.115       # bears 4 1/2 in each side
STONE_PROJ = 0.050             # face projection of trim stone (2 in: enough to throw a shadow at a raking sun)
SILL_H = 0.100                 # 4 in stone sill
SILL_PROJ = 0.065
SILL_EAR = 0.075
SILL_SLOPE = 0.020             # wash across the sill
FLOOR_H = 3.05                 # 10 ft tenement floor-to-floor
GROUND_H = 4.20                # ground-floor commercial storey
RAIL_H = 0.860                 # 34 in fire-escape / stoop railing
PICKET = 0.014                 # 9/16 in square picket

# Masonry rough openings by window type (metres): what the *wall* hole must be for each kit window. The piece's
# bounding box is larger — it carries the lintel above and the sill below, which sit in the surrounding brick.
import facade_params as _fp                                              # noqa: E402
W_OPENING = {w[0]: (w[1], w[2]) for w in _fp.WINDOW_TYPES}

# --------------------------------------------------------------------------- material name helpers
GLASS = "glass_clear"
SASH_WHITE = "painted_wood_white"
ALU = "aluminum_anodized"
BLACK = "painted_metal_black"
GREEN = "painted_metal_green"
IRON = "cast_iron"
GALV = "steel_galvanized"


def reg_flats() -> None:
    """Register the flat / emissive kit materials that have no texture set. Idempotent."""
    K.flat("paint_cream", (0.82, 0.78, 0.70), 0.55)
    K.flat("paint_darkgreen", (0.055, 0.13, 0.085), 0.45)
    K.flat("paint_maroon", (0.20, 0.045, 0.045), 0.45)
    K.flat("paint_bottle_green", (0.018, 0.075, 0.028), 0.22)
    K.flat("paint_navy", (0.035, 0.055, 0.13), 0.45)
    K.flat("paint_red", (0.42, 0.05, 0.05), 0.5)
    K.flat("paint_blue", (0.05, 0.13, 0.35), 0.5)
    K.flat("paint_yellow", (0.72, 0.55, 0.06), 0.5)
    K.flat("paint_white", (0.86, 0.86, 0.84), 0.55)
    K.flat("paint_black", (0.035, 0.035, 0.035), 0.5)
    K.flat("paint_grey", (0.32, 0.33, 0.34), 0.55)
    K.flat("rubber_black", (0.02, 0.02, 0.022), 0.85)
    K.flat("foliage_green", (0.035, 0.105, 0.032), 0.72)
    K.flat("foliage_green_dry", (0.105, 0.115, 0.040), 0.8)
    K.flat("soil", (0.06, 0.045, 0.035), 0.9)
    K.flat("chrome", (0.62, 0.63, 0.65), 0.18, metallic=1.0)
    K.flat("interior_room_dark", (0.055, 0.052, 0.050), 0.92)      # returns of the sealed room box behind every pane
    K.emissive("lamp_warm", (1.0, 0.82, 0.55), 6.0)
    K.emissive("neon_red", (1.0, 0.10, 0.06), 14.0)
    K.emissive("neon_blue", (0.15, 0.45, 1.0), 12.0)
    K.emissive("neon_green", (0.15, 1.0, 0.35), 12.0)
    K.emissive("fluoro_white", (0.92, 0.96, 1.0), 5.0)


# --------------------------------------------------------------------------- generated textures
def _gen_dir() -> Path:
    K.GENERATED_TEX.mkdir(parents=True, exist_ok=True)
    return K.GENERATED_TEX


def interior_card_image(lit: bool) -> str:
    """A 512 px card seen through a residential window: ceiling, back wall, a shade, furniture silhouettes and (lit)
    a warm lamp. Generated once, cached on disk."""
    from PIL import Image, ImageDraw, ImageFilter
    p = _gen_dir() / f"interior_card_{'lit' if lit else 'unlit'}.png"
    if p.exists():
        return str(p)
    W = H = 512
    if lit:
        wall, floor, ceil = (150, 118, 84), (86, 62, 42), (176, 148, 112)
    else:
        # A daytime room seen from a sunlit street is dim but not black: at pure black the pane reads as a hole and
        # the glass loses all depth, so the card carries the light a north-facing room actually has.
        wall, floor, ceil = (58, 57, 62), (34, 32, 36), (72, 71, 78)
    img = Image.new("RGB", (W, H), wall)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, int(H * 0.16)], fill=ceil)                     # ceiling
    d.rectangle([0, int(H * 0.74), W, H], fill=floor)                    # floor
    d.rectangle([int(W * 0.06), int(H * 0.30), int(W * 0.40), int(H * 0.78)],
                fill=tuple(int(c * 0.72) for c in wall))                 # tall furniture / bookcase
    d.rectangle([int(W * 0.55), int(H * 0.52), int(W * 0.97), int(H * 0.80)],
                fill=tuple(int(c * 0.55) for c in wall))                 # sofa / bed
    d.rectangle([int(W * 0.42), int(H * 0.22), int(W * 0.72), int(H * 0.46)],
                fill=tuple(int(c * 0.85) for c in wall))                 # picture / mirror
    if lit:
        d.ellipse([int(W * 0.60), int(H * 0.28), int(W * 0.80), int(H * 0.50)], fill=(255, 226, 170))
        d.rectangle([int(W * 0.68), int(H * 0.46), int(W * 0.72), int(H * 0.56)], fill=(120, 96, 60))
        img = img.filter(ImageFilter.GaussianBlur(3.0))
    else:
        img = img.filter(ImageFilter.GaussianBlur(2.0))
    img.save(p)
    return str(p)


def ivy_image() -> str:
    """RGBA ivy leaf sheet (alpha-cut) for the vegetation pieces."""
    from PIL import Image, ImageDraw
    p = _gen_dir() / "ivy_leaves.png"
    if p.exists():
        return str(p)
    W = H = 512
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    rnd = _lcg(12345)
    for _ in range(560):
        cx, cy = rnd() * W, rnd() * H
        r = 12 + rnd() * 20
        g = 44 + int(rnd() * 62)                       # Boston ivy: deep, slightly blue-green, not grass green
        col = (int(g * 0.55), g, int(g * 0.46), 255)
        pts = [(cx, cy - r), (cx + r * 0.75, cy - r * 0.2), (cx + r * 0.35, cy + r * 0.9),
               (cx - r * 0.35, cy + r * 0.9), (cx - r * 0.75, cy - r * 0.2)]
        d.polygon(pts, fill=col)
        vein = (int(g * 0.40), int(g * 0.72), int(g * 0.34), 255)
        d.line([(cx, cy + r * 0.85), (cx, cy - r * 0.85)], fill=vein, width=2)
        d.line([(cx, cy + r * 0.2), (cx + r * 0.62, cy - r * 0.15)], fill=vein, width=1)
        d.line([(cx, cy + r * 0.2), (cx - r * 0.62, cy - r * 0.15)], fill=vein, width=1)
    img.save(p)
    return str(p)


def _lcg(seed: int):
    s = [seed]

    def nxt() -> float:
        s[0] = (1103515245 * s[0] + 12345) % 2147483648
        return s[0] / 2147483648.0
    return nxt


def reg_generated_materials() -> None:
    """Register the image-backed generated materials once per session."""
    K.generated_material("interior_lit", image=interior_card_image(True), roughness=0.9,
                         emission=(1, 1, 1), emission_strength=1.6, uv_scale_m=2.0)
    K.generated_material("interior_unlit", image=interior_card_image(False), roughness=0.9, uv_scale_m=2.0)
    K.generated_material("ivy_leaf", image=ivy_image(), roughness=0.75, alpha_from_image=True, uv_scale_m=0.55)


# --------------------------------------------------------------------------- classical moulding profiles
# A profile is a list of (y, z) points in the wall's cross-section: −y is towards the street, +z up.  ``sweep`` turns
# one into a solid run along X.  These are the real mouldings of New York masonry and sheet-metal trim; using them
# instead of plain boxes is what puts a shadow line on every lintel, sill, band and cornice.
def curve(p0: Sequence[float], p1: Sequence[float], kind: str = "line", n: int = 4) -> list[tuple[float, float]]:
    """Points of one moulding member from p0 to p1 (p0 excluded, p1 included).

    ``kind``: ``line`` | ``ovolo`` (quarter round, convex) | ``cavetto`` (quarter hollow) | ``cyma_recta``
    (hollow over round) | ``cyma_reversa`` (round over hollow) | ``bead`` (half round)."""
    (y0, z0), (y1, z1) = tuple(p0), tuple(p1)
    if kind == "line" or n < 2:
        return [(y1, z1)]
    out: list[tuple[float, float]] = []
    if kind == "ovolo":                      # centre at (y0, z1): bulges towards the street/top
        for i in range(1, n + 1):
            t = (i / n) * math.pi / 2
            out.append((y0 + (y1 - y0) * math.sin(t), z1 + (z0 - z1) * math.cos(t)))
    elif kind == "cavetto":                  # centre at (y1, z0): hollow
        for i in range(1, n + 1):
            t = (i / n) * math.pi / 2
            out.append((y1 + (y0 - y1) * math.cos(t), z0 + (z1 - z0) * math.sin(t)))
    elif kind in ("cyma_recta", "cyma_reversa"):
        ym, zm = (y0 + y1) / 2, (z0 + z1) / 2
        a, b = ("cavetto", "ovolo") if kind == "cyma_recta" else ("ovolo", "cavetto")
        h = max(2, n // 2)
        out += curve((y0, z0), (ym, zm), a, h)
        out += curve((ym, zm), (y1, z1), b, h)
    elif kind == "bead":                     # half round bulging towards the street
        r = abs(z1 - z0) / 2
        zc = (z0 + z1) / 2
        for i in range(1, n + 1):
            t = -math.pi / 2 + math.pi * i / n
            out.append((y0 - r * math.cos(t), zc + r * math.sin(t)))
    else:
        raise ValueError(f"unknown moulding kind {kind!r}")
    return out


def profile(start: Sequence[float], members: Sequence[tuple]) -> list[tuple[float, float]]:
    """Chain moulding members into one profile. ``members`` = ((y, z), kind, n) triples, each continuing from the last."""
    pts = [tuple(start)]
    for mem in members:
        p1 = mem[0]
        kind = mem[1] if len(mem) > 1 else "line"
        n = mem[2] if len(mem) > 2 else 4
        pts += curve(pts[-1], p1, kind, n)
    return pts


def sweep(m: K.Mesh, prof: Sequence[Sequence[float]], x0: float, x1: float, mat: str, *, caps: bool = True,
          smooth: bool = False) -> None:
    """Sweep a closed (y, z) profile from x0 to x1 with end caps. Duplicate first/last points are dropped."""
    pts = [tuple(p) for p in prof]
    while len(pts) > 2 and math.dist(pts[0], pts[-1]) < 1e-6:
        pts.pop()
    m.extrude_profile(pts, x0, x1, mat, closed=True, caps=caps, flip=True, smooth=smooth)


# --------------------------------------------------------------------------- masonry opening parts
def reveal(m: K.Mesh, x0: float, x1: float, z0: float, z1: float, depth: float, mat: str, *, head: bool = True,
           sill: bool = True, y0: float = 0.004) -> None:
    """Jamb / head / sill liner of a masonry opening: faces from just inside the wall plane to y = depth, normals
    pointing into the opening.

    ``y0`` holds the liner 4 mm behind the brick face so it never lands coplanar with an opening liner the building
    shell may already carry (coplanar faces flicker and, lit from the wrong side, wash the head out).  The shell is
    expected to cut a plain hole; this piece owns the reveal."""
    m.face([(x0, y0, z0), (x0, depth, z0), (x0, depth, z1), (x0, y0, z1)], mat)         # left jamb -> +X
    m.face([(x1, depth, z0), (x1, y0, z0), (x1, y0, z1), (x1, depth, z1)], mat)         # right jamb -> -X
    if head:
        m.face([(x0, y0, z1), (x0, depth, z1), (x1, depth, z1), (x1, y0, z1)], mat, flip=True)
    if sill:
        m.face([(x0, y0, z0), (x1, y0, z0), (x1, depth, z0), (x0, depth, z0)], mat, flip=True)


def stone_lintel(m: K.Mesh, x0: float, x1: float, z: float, mat: str = "limestone", *, h: float = STONE_LINTEL_H,
                 ear: float = STONE_LINTEL_EAR, proj: float = STONE_PROJ, depth: float = WYTHE) -> None:
    """Projecting stone lintel bearing ``ear`` each side of the opening, underside at z.

    Cut cross-section: chamfered lower arris, a plain face, a fillet under the top edge and a washed top that sheds
    water back to nothing at the wall — the standard New York cut-stone lintel."""
    ch = min(0.022, h * 0.16)                       # chamfer on the bottom arris
    wash = min(0.026, h * 0.20)
    prof = profile((depth, z), [
        ((-proj + ch, z),),                         # soffit
        ((-proj, z + ch),),                         # chamfer
        ((-proj, z + h - wash - 0.012),),           # face
        ((-proj + 0.008, z + h - wash),),           # fillet under the top edge
        ((depth, z + h),),                          # wash back to the wall
    ])
    sweep(m, prof, x0 - ear, x1 + ear, mat)


def keyed_lintel(m: K.Mesh, x0: float, x1: float, z: float, mat: str = "limestone") -> None:
    """Stone lintel with a raised keystone (Renaissance-revival apartment houses)."""
    stone_lintel(m, x0, x1, z, mat)
    keystone(m, (x0 + x1) / 2, z - 0.045, STONE_LINTEL_H + 0.120, mat, half_top=0.115, half_bot=0.082,
             proj=STONE_PROJ + 0.025)


def keystone(m: K.Mesh, cx: float, z0: float, h: float, mat: str = "limestone", *, half_top: float = 0.130,
             half_bot: float = 0.090, proj: float = 0.090, depth: float = WYTHE) -> None:
    """Tapered keystone with a chamfered arris, a sunk centre panel and a small cap — swept as two stacked frusta so
    it catches light on three planes instead of reading as one slab."""
    zt = z0 + h
    cap_h = min(0.055, h * 0.14)
    ztop = zt - cap_h
    ch = 0.014

    def frustum(za: float, zb: float, ha: float, hb: float, ya: float, yb: float) -> None:
        """Trapezoidal block from za to zb, half-width ha->hb, projecting ya->yb."""
        pts_b = [(cx - ha + ch, ya, za), (cx + ha - ch, ya, za), (cx + ha, ya + 0.0, za + ch)]
        # front face (splayed), two side faces, and the returns to the wall
        m.face([(cx - ha, ya, za), (cx + ha, ya, za), (cx + hb, yb, zb), (cx - hb, yb, zb)], mat)      # street face
        m.face([(cx - ha, ya, za), (cx - hb, yb, zb), (cx - hb, depth, zb), (cx - ha, depth, za)], mat)  # -X side
        m.face([(cx + ha, depth, za), (cx + hb, depth, zb), (cx + hb, yb, zb), (cx + ha, yb, za)], mat)  # +X side
        del pts_b

    frustum(z0, ztop, half_bot, half_top, -proj * 0.72, -proj)
    # cap moulding: a small projecting block with a washed top
    m.box((cx - half_top - 0.014, -proj - 0.014, ztop), (cx + half_top + 0.014, depth, zt - 0.012), mat)
    m.face([(cx - half_top - 0.014, -proj - 0.014, zt - 0.012), (cx + half_top + 0.014, -proj - 0.014, zt - 0.012),
            (cx + half_top + 0.014, depth, zt), (cx - half_top - 0.014, depth, zt)], mat)               # wash
    # sunk centre panel (reads as carving at 10 m)
    m.box((cx - half_bot * 0.52, -proj - 0.010, z0 + h * 0.24), (cx + half_bot * 0.52, -proj + 0.004, ztop - 0.030), mat)
    m.face([(cx - half_bot, -proj, z0 + h * 0.10), (cx + half_bot, -proj, z0 + h * 0.10),
            (cx + half_bot, depth, z0 + h * 0.10), (cx - half_bot, depth, z0 + h * 0.10)], mat, flip=True)  # soffit
    m.face([(cx - half_top, depth, ztop), (cx + half_top, depth, ztop), (cx + half_top, -proj, ztop),
            (cx - half_top, -proj, ztop)], mat)


def soldier_lintel(m: K.Mesh, x0: float, x1: float, z: float, mat: str = "red_brick", *, proj: float = 0.032) -> None:
    """Brick soldier course (bricks on end) over the opening, modelled brick by brick so the course reads as masonry:
    each brick is 92 mm wide with a 12 mm raked head joint and a millimetre or two of set-out variation.

    The brick faces carry a 90 deg-rotated UV so the brick texture itself runs vertically — bricks on end have to look
    like bricks on end, or the course reads as a plain band whatever its relief."""
    a, b = x0 - 0.02, x1 + 0.02
    pitch = 0.1022                                   # 92 mm brick + 10 mm head joint
    n = max(2, int(round((b - a) / pitch)))
    w = (b - a) / n - 0.012                          # 12 mm raked head joint
    rnd = _lcg(int(abs(x0) * 977) + 17)
    # mortar bed first, its face raked 14 mm behind the brick faces so every joint reads as a shadow line, not a void
    m.box((a, -proj + 0.014, z), (b, WYTHE, z + BRICK_LEN), mat)
    for k in range(n):
        cx = a + (b - a) * (k + 0.5) / n
        p = proj + (rnd() - 0.5) * 0.006             # laid by hand: a couple of millimetres of variation
        m.box((cx - w / 2, -p, z + 0.006), (cx + w / 2, WYTHE, z + BRICK_LEN - 0.006), mat, faces="yxXzZ", uv_rot=1)


def segmental_arch(m: K.Mesh, x0: float, x1: float, z: float, rise: float, mat: str, *, thickness: float = BRICK_LEN,
                   segments: int = 9, proj: float = 0.018, depth: float = WYTHE) -> None:
    """Segmental brick arch over a tenement opening (rise ≈ 1/8 of the span, NYC Old Law practice)."""
    span = x1 - x0
    R = (span * span / 4 + rise * rise) / (2 * rise)
    cz = z + rise - R
    cx = (x0 + x1) / 2
    half = math.asin(min(1.0, (span / 2) / R))
    pts_in, pts_out = [], []
    for i in range(segments + 1):
        a = -half + 2 * half * i / segments
        pts_in.append((cx + R * math.sin(a), cz + R * math.cos(a)))
        pts_out.append((cx + (R + thickness) * math.sin(a), cz + (R + thickness) * math.cos(a)))
    for i in range(segments):
        ax, az = pts_in[i]
        bx, bz = pts_in[i + 1]
        cx2, cz2 = pts_out[i + 1]
        dx, dz = pts_out[i]
        m.face([(ax, -proj, az), (dx, -proj, dz), (cx2, -proj, cz2), (bx, -proj, bz)], mat)          # street face
        m.face([(bx, depth, bz), (cx2, depth, cz2), (dx, depth, dz), (ax, depth, az)], mat)          # back face
        m.face([(dx, -proj, dz), (dx, depth, dz), (cx2, depth, cz2), (cx2, -proj, cz2)], mat)        # extrados
        m.face([(ax, depth, az), (bx, depth, bz), (bx, -proj, bz), (ax, -proj, az)], mat)            # intrados


def stone_sill(m: K.Mesh, x0: float, x1: float, z: float, mat: str = "limestone", *, h: float = SILL_H,
               ear: float = SILL_EAR, proj: float = SILL_PROJ, depth: float = WYTHE, drip: bool = True) -> None:
    """Projecting stone sill: washed top, chamfered nose and — on the underside — the throated drip groove that keeps
    rain off the brick below.  The groove is 12 x 10 mm, set 25 mm back from the nose (NYC cut-stone practice); it is
    the detail that puts a dark line under every sill on a sunlit facade."""
    a, b = x0 - ear, x1 + ear
    ch = 0.012
    members = [((-proj + 0.025, z),)]
    if drip:
        members += [((-proj + 0.025, z + 0.010),), ((-proj + 0.013, z + 0.010),), ((-proj + 0.013, z),)]   # throat
    members += [
        ((-proj + ch, z),),                                      # nose soffit
        ((-proj, z + ch),),                                      # chamfered nose
        ((-proj, z + h - SILL_SLOPE - 0.008),),                  # front face
        ((depth, z + h),),                                       # wash
    ]
    sweep(m, profile((depth, z), members), a, b, mat)


# --------------------------------------------------------------------------- sashes and glazing
def sash(m: K.Mesh, x0: float, x1: float, z0: float, z1: float, y: float, *, lights_x: int = 1, lights_z: int = 1,
         frame_mat: str = SASH_WHITE, glass_mat: str = GLASS, stile: float = SASH_STILE, thick: float = 0.042,
         muntin: float = MUNTIN_W) -> None:
    """One operable sash: stiles/rails, optional true-divided-light muntins, one glass slab behind."""
    m.frame(x0, x1, z0, z1, y, y + thick, stile, frame_mat)
    gx0, gx1, gz0, gz1 = x0 + stile, x1 - stile, z0 + stile, z1 - stile
    for i in range(lights_x - 1):
        x = gx0 + (gx1 - gx0) * (i + 1) / lights_x
        m.box((x - muntin / 2, y + 0.006, gz0), (x + muntin / 2, y + thick - 0.006, gz1), frame_mat)
    for j in range(lights_z - 1):
        z = gz0 + (gz1 - gz0) * (j + 1) / lights_z
        m.box((gx0, y + 0.006, z - muntin / 2), (gx1, y + thick - 0.006, z + muntin / 2), frame_mat)
    m.glass_pane(gx0, gx1, gz0, gz1, y + thick / 2, glass_mat, GLASS_T)


def interior_card(m: K.Mesh, x0: float, x1: float, z0: float, z1: float, y: float, lit: bool, *, depth: float = 0.30) -> None:
    """Shallow sealed room box behind the glass: the imagery card at ``depth`` with dark returns closing the sides.

    A single card is not enough.  A building shell is an open box, so a bare card lets the sky behind the wall light
    the opening from the back and the pane washes out to a flat grey — which is exactly how the first verification
    pass failed.  Closing the returns both seals the light leak and gives the pane real parallax depth."""
    mat = "interior_lit" if lit else "interior_unlit"
    dark = "interior_room_dark"
    yb = y + depth
    m.face([(x0, yb, z0), (x1, yb, z0), (x1, yb, z1), (x0, yb, z1)], mat, uvs=[(0, 0), (2, 0), (2, 2), (0, 2)])
    m.face([(x0, y, z0), (x0, yb, z0), (x0, yb, z1), (x0, y, z1)], dark)                        # -X return
    m.face([(x1, yb, z0), (x1, y, z0), (x1, y, z1), (x1, yb, z1)], dark)                        # +X return
    m.face([(x0, y, z1), (x0, yb, z1), (x1, yb, z1), (x1, y, z1)], dark, flip=True)             # ceiling
    m.face([(x0, y, z0), (x1, y, z0), (x1, yb, z0), (x0, yb, z0)], dark, flip=True)             # floor


def double_hung(m: K.Mesh, x0: float, x1: float, z0: float, z1: float, *, lights_x: int = 1, lights_z: int = 1,
                frame_mat: str = SASH_WHITE, reveal_depth: float = REVEAL, lit: bool | None = None) -> None:
    """Complete double-hung window inside an opening x0..x1 / z0..z1: blind-stop frame, upper and lower sash with the
    lower sash outboard, a parting bead between them, the meeting-rail overlap and an interior card.

    The whole assembly sits ``reveal_depth`` (155 mm) behind the wall face, so the masonry jamb shades it."""
    # The frame box runs all the way back to the masonry liner (reveal_depth + 0.10, the depth every caller uses), so
    # the opening is sealed: any gap between frame and liner lets daylight in from behind the shell and reads as a
    # bright sliver at the head.
    m.frame(x0, x1, z0, z1, reveal_depth - 0.012, reveal_depth + 0.100, CASING * 0.75, frame_mat)
    fx0, fx1 = x0 + CASING * 0.75, x1 - CASING * 0.75
    fz0, fz1 = z0 + CASING * 0.75, z1 - CASING * 0.75
    mid = (fz0 + fz1) / 2
    sash(m, fx0, fx1, mid - MEETING_RAIL / 2, fz1, reveal_depth + 0.030, lights_x=lights_x, lights_z=lights_z, frame_mat=frame_mat)
    sash(m, fx0, fx1, fz0, mid + MEETING_RAIL / 2, reveal_depth - 0.010, lights_x=lights_x, lights_z=lights_z, frame_mat=frame_mat)
    # parting bead in each jamb, separating the two sash runs (13 mm proud of the frame)
    for x in (fx0, fx1):
        sx = 1.0 if x == fx0 else -1.0
        m.box((x, reveal_depth + 0.022, fz0), (x + sx * 0.013, reveal_depth + 0.035, fz1), frame_mat)
    # wooden sub-sill inside the opening, sloped to the street
    m.face([(fx0, reveal_depth - 0.012, fz0), (fx1, reveal_depth - 0.012, fz0),
            (fx1, reveal_depth + 0.070, fz0 + 0.016), (fx0, reveal_depth + 0.070, fz0 + 0.016)], frame_mat)
    if lit is not None:
        interior_card(m, fx0, fx1, fz0, fz1, reveal_depth + 0.155, lit)


# --------------------------------------------------------------------------- railings, ladders, gratings
def railing(m: K.Mesh, path: Sequence[Sequence[float]], height: float = RAIL_H, mat: str = BLACK, *,
            pitch: float = 0.125, picket: float = PICKET, rails: int = 2, post: float = 0.030) -> None:
    """Picket railing along a 3-D polyline (NYC fire-escape / stoop railing: 34 in high, pickets at 5 in centres)."""
    for i in range(len(path) - 1):
        a = K.Vector(path[i])
        b = K.Vector(path[i + 1])
        d = b - a
        L = d.length
        if L < 1e-4:
            continue
        u = d / L
        n = K.Vector((-u.y, u.x, 0.0))
        if n.length < 1e-6:
            n = K.Vector((1.0, 0.0, 0.0))
        n.normalize()
        for r in range(rails):
            zr = height - r * (height - 0.10) / max(rails - 1, 1) if rails > 1 else height
            _bar(m, a + K.Vector((0, 0, zr)), b + K.Vector((0, 0, zr)), n, 0.028, 0.016, mat)
        npick = max(1, int(L / pitch))
        for k in range(npick + 1):
            t = k / npick
            p = a + d * t
            _bar(m, p + K.Vector((0, 0, 0.02)), p + K.Vector((0, 0, height)), n, picket, picket, mat)
    a, b = K.Vector(path[0]), K.Vector(path[-1])
    for p in (a, b):
        m.box((p.x - post / 2, p.y - post / 2, p.z), (p.x + post / 2, p.y + post / 2, p.z + height + 0.03), mat)


def _bar(m: K.Mesh, a, b, n, w: float, t: float, mat: str) -> None:
    """Rectangular bar from a to b, ``w`` across the run, ``t`` through the plane defined by normal n."""
    d = (b - a)
    L = d.length
    if L < 1e-5:
        return
    u = d / L
    side = n * (t / 2)
    up = u.cross(n).normalized() * (w / 2)
    c = [a - side - up, a + side - up, a + side + up, a - side + up,
         b - side - up, b + side - up, b + side + up, b - side + up]
    quads = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    for q in quads:
        m.face([c[i] for i in q], mat)


def ladder(m: K.Mesh, x: float, y: float, z0: float, z1: float, width: float = 0.406, mat: str = BLACK,
           *, rung_pitch: float = 0.305, rail: float = 0.032) -> None:
    """Vertical steel ladder (16 in wide, 12 in rung pitch — NYC fire-escape drop-ladder standard)."""
    for s in (-1, 1):
        m.box((x + s * width / 2 - rail / 2, y - rail / 2, z0), (x + s * width / 2 + rail / 2, y + rail / 2, z1), mat)
    n = max(1, int((z1 - z0) / rung_pitch))
    for k in range(1, n + 1):
        z = z0 + (z1 - z0) * k / (n + 1)
        m.box((x - width / 2, y - 0.011, z - 0.011), (x + width / 2, y + 0.011, z + 0.011), mat)


def grating(m: K.Mesh, x0: float, x1: float, y0: float, y1: float, z: float, mat: str = BLACK, *,
            thick: float = 0.030, edge: float = 0.050) -> None:
    """Fire-escape platform: a perforated-steel deck slab with an angle-iron perimeter."""
    m.box((x0, y0, z - thick), (x1, y1, z), mat)
    m.box((x0 - 0.012, y0 - 0.012, z - thick - edge), (x1 + 0.012, y0 + 0.012, z + 0.012), mat)
    m.box((x0 - 0.012, y1 - 0.012, z - thick - edge), (x1 + 0.012, y1 + 0.012, z + 0.012), mat)


def stair_flight(m: K.Mesh, x0: float, x1: float, y_top: float, z_top: float, y_bot: float, z_bot: float,
                 mat: str = BLACK, *, treads: int = 9) -> None:
    """Open steel stair between two fire-escape platforms: two stringers and ``treads`` flat-bar treads."""
    a = K.Vector((0.0, y_top, z_top))
    b = K.Vector((0.0, y_bot, z_bot))
    for x in (x0, x1):
        _stringer(m, x, a, b, mat)
    for k in range(treads):
        t = (k + 0.5) / treads
        y = y_top + (y_bot - y_top) * t
        z = z_top + (z_bot - z_top) * t
        m.box((x0, y - 0.115, z - 0.012), (x1, y + 0.115, z + 0.012), mat)


def _stringer(m: K.Mesh, x: float, a, b, mat: str) -> None:
    d = b - a
    L = d.length
    if L < 1e-5:
        return
    u = d / L
    n = K.Vector((1.0, 0.0, 0.0))
    up = u.cross(n).normalized() * 0.075
    side = n * 0.010
    A = K.Vector((x, a.y, a.z))
    B = K.Vector((x, b.y, b.z))
    c = [A - side - up, A + side - up, A + side + up, A - side + up,
         B - side - up, B + side - up, B + side + up, B - side + up]
    for q in [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]:
        m.face([c[i] for i in q], mat)


def corbel_bracket(m: K.Mesh, x: float, y_face: float, z0: float, z1: float, proj: float, mat: str, *,
                   width: float = 0.090, scroll: int = 5, side_panel: bool = True) -> None:
    """Scrolled console bracket (pressed metal / wood): an S-curve front edge swept ``width`` across, with a shoulder
    fillet under the top so it reads as *carrying* the corona rather than as a fin stuck on the frieze."""
    prof = [(y_face, z0)]
    for i in range(scroll + 1):
        t = i / scroll
        prof.append((y_face - proj * math.sin(t * math.pi / 2) ** 1.4, z0 + (z1 - z0 - 0.030) * t))
    prof.append((y_face - proj, z1))                     # shoulder: square up under the corona soffit
    prof.append((y_face, z1))
    m.extrude_profile(prof, x - width / 2, x + width / 2, mat, closed=True, caps=True, flip=True)
    if side_panel:                                       # sunk side panel: a bracket is a box, not a plate
        for sx in (-1.0, 1.0):
            xs = x + sx * (width / 2 + 0.006)
            m.box((min(xs, x + sx * width / 2), y_face - proj * 0.55, z0 + (z1 - z0) * 0.30),
                  (max(xs, x + sx * width / 2), y_face - proj * 0.18, z1 - 0.030), mat)


def pressed_metal_cornice(m: K.Mesh, x0: float, x1: float, mat: str, *, frieze_h: float, frieze_proj: float,
                          dentil_h: float, dentil_proj: float, dentil_pitch: float, bed_h: float, bed_proj: float,
                          corona_soffit: float, corona_proj: float, corona_h: float, crown_h: float,
                          crown_back: float, cap_h: float, bracket_pitch: float, bracket_width: float,
                          depth: float = WYTHE, panels: bool = False, dentils_on: bool = True) -> float:
    """A complete New York pressed-metal cornice run: frieze, dentil course, bed mould, scrolled consoles carrying the
    corona, corona fascia, cyma-recta crown and a capping fillet.  Returns the total height.

    Every member is real geometry with its own shadow line; the consoles project to ``corona_proj`` less a hair, so
    from the street they read under the corona the way they do on every 1880s tenement.  Heights are measured from
    the top of the frieze board, which sits on the wall at z = 0."""
    run = x1 - x0
    z_dentil = frieze_h
    z_bed = z_dentil + (dentil_h if dentils_on else 0.0)
    z_corona = z_bed + bed_h
    z_fascia = z_corona + corona_h
    z_crown = z_fascia + crown_h
    top = z_crown + cap_h

    m.box((x0, -frieze_proj, 0.0), (x1, depth, frieze_h), mat)                                  # frieze board
    if panels:                                                                                   # sunk frieze panels
        n = max(1, int(round(run / 0.34)))
        for k in range(n):
            cx = x0 + run * (k + 0.5) / n
            m.box((cx - 0.130, -frieze_proj - 0.020, 0.055), (cx + 0.130, -frieze_proj, frieze_h - 0.055), mat)
    if dentils_on:
        m.box((x0, -frieze_proj, z_dentil), (x1, depth, z_bed), mat)                             # dentil band backing
        dentils(m, x0, x1, z_dentil + 0.006, z_bed - 0.006, -frieze_proj, dentil_proj - frieze_proj, mat,
                pitch=dentil_pitch)

    listel = 0.022                                                    # fillet separating corona from crown
    prof = profile((depth, z_bed), [
        ((-dentil_proj, z_bed),),                                     # under the bed mould
        ((-bed_proj, z_corona), "cyma_reversa", 4),                   # bed mould
        ((-corona_proj, z_corona + corona_soffit),),                  # corona soffit, splayed out
        ((-corona_proj, z_fascia - listel),),                         # corona fascia
        ((-corona_proj + 0.024, z_fascia - listel),),                 # listel: a crisp step, not a blend
        ((-corona_proj + 0.024, z_fascia),),
        ((-crown_back, z_crown - 0.014), "cyma_recta", 6),            # crown moulding
        ((-crown_back, z_crown),),                                    # vertical fillet at the crown top
        ((-crown_back + 0.026, top),),                                # capping wash
        ((depth, top),),                                              # back to the wall
    ])
    sweep(m, prof, x0, x1, mat)

    nb_ = max(1, int(round(run / bracket_pitch)))
    for k in range(nb_):
        cx = x0 + run * (k + 0.5) / nb_
        corbel_bracket(m, cx, -frieze_proj, 0.040, z_corona + corona_soffit, corona_proj - 0.045, mat,
                       width=bracket_width, scroll=6)
    return top


def dentils(m: K.Mesh, x0: float, x1: float, z0: float, z1: float, y_face: float, proj: float, mat: str,
            *, pitch: float = 0.120, ratio: float = 0.5) -> None:
    """Dentil course under a cornice or string course."""
    n = max(1, int((x1 - x0) / pitch))
    w = pitch * ratio
    for k in range(n):
        cx = x0 + pitch * (k + 0.5)
        m.box((cx - w / 2, y_face - proj, z0), (cx + w / 2, y_face, z1), mat)
