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
REVEAL = 0.115                 # sash set back 4 1/2 in from the brick face
GLASS_T = 0.006
STONE_LINTEL_H = 0.150         # 6 in stone lintel
STONE_LINTEL_EAR = 0.115       # bears 4 1/2 in each side
STONE_PROJ = 0.040             # face projection of trim stone
SILL_H = 0.100                 # 4 in stone sill
SILL_PROJ = 0.065
SILL_EAR = 0.075
SILL_SLOPE = 0.020             # wash across the sill
FLOOR_H = 3.05                 # 10 ft tenement floor-to-floor
GROUND_H = 4.20                # ground-floor commercial storey
RAIL_H = 0.860                 # 34 in fire-escape / stoop railing
PICKET = 0.014                 # 9/16 in square picket

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
    K.flat("paint_navy", (0.035, 0.055, 0.13), 0.45)
    K.flat("paint_red", (0.42, 0.05, 0.05), 0.5)
    K.flat("paint_blue", (0.05, 0.13, 0.35), 0.5)
    K.flat("paint_yellow", (0.72, 0.55, 0.06), 0.5)
    K.flat("paint_white", (0.86, 0.86, 0.84), 0.55)
    K.flat("paint_black", (0.035, 0.035, 0.035), 0.5)
    K.flat("paint_grey", (0.32, 0.33, 0.34), 0.55)
    K.flat("rubber_black", (0.02, 0.02, 0.022), 0.85)
    K.flat("foliage_green", (0.075, 0.22, 0.06), 0.72)
    K.flat("foliage_green_dry", (0.20, 0.24, 0.09), 0.8)
    K.flat("soil", (0.06, 0.045, 0.035), 0.9)
    K.flat("chrome", (0.62, 0.63, 0.65), 0.18, metallic=1.0)
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
        wall, floor, ceil = (26, 27, 32), (16, 16, 20), (30, 32, 38)
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


def commercial_card_image(kind: str) -> str:
    """Card seen through a shopfront transom for kinds with no modelled interior: shelving bands and ceiling lights."""
    from PIL import Image, ImageDraw, ImageFilter
    p = _gen_dir() / f"commercial_card_{kind}.png"
    if p.exists():
        return str(p)
    W = H = 512
    img = Image.new("RGB", (W, H), (54, 52, 48))
    d = ImageDraw.Draw(img)
    for i in range(5):
        y = int(H * (0.24 + i * 0.14))
        d.rectangle([0, y, W, y + int(H * 0.09)], fill=(96, 88, 76))
        for k in range(14):
            x = int(W * k / 14.0)
            d.rectangle([x + 3, y + 3, x + int(W / 14.0) - 4, y + int(H * 0.09) - 3],
                        fill=(70 + (k * 37) % 120, 60 + (k * 61) % 120, 55 + (k * 23) % 120))
    for k in range(3):
        d.rectangle([int(W * 0.08), int(H * (0.06 + 0.05 * k)), int(W * 0.92), int(H * (0.085 + 0.05 * k))], fill=(240, 244, 235))
    img = img.filter(ImageFilter.GaussianBlur(2.5))
    img.save(p)
    return str(p)


def sign_band_image(text: str, fg: Sequence[int], bg: Sequence[int], *, key: str) -> str:
    """Sign-band / awning-valance texture: a 1024 x 256 strip with the shop name set in Overpass."""
    from PIL import Image, ImageDraw, ImageFont
    p = _gen_dir() / f"sign_{key}.png"
    if p.exists():
        return str(p)
    W, H = 1024, 256
    img = Image.new("RGB", (W, H), tuple(bg))
    d = ImageDraw.Draw(img)
    font_path = K.nb.ASSETS / "fonts" / "Overpass" / "overpass-bold.otf"
    size = 132
    font = ImageFont.truetype(str(font_path), size) if font_path.exists() else ImageFont.load_default()
    while font_path.exists() and d.textlength(text, font=font) > W * 0.92 and size > 24:
        size -= 6
        font = ImageFont.truetype(str(font_path), size)
    w = d.textlength(text, font=font)
    d.text(((W - w) / 2, (H - size * 1.05) / 2), text, font=font, fill=tuple(fg))
    d.rectangle([0, 0, W - 1, H - 1], outline=tuple(int(c * 0.7) for c in bg), width=6)
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
    for _ in range(520):
        cx, cy = rnd() * W, rnd() * H
        r = 12 + rnd() * 20
        g = 60 + int(rnd() * 90)
        col = (int(g * 0.35), g, int(g * 0.30), 255)
        d.polygon([(cx, cy - r), (cx + r * 0.75, cy - r * 0.2), (cx + r * 0.35, cy + r * 0.9),
                   (cx - r * 0.35, cy + r * 0.9), (cx - r * 0.75, cy - r * 0.2)], fill=col)
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


# --------------------------------------------------------------------------- masonry opening parts
def reveal(m: K.Mesh, x0: float, x1: float, z0: float, z1: float, depth: float, mat: str, *, head: bool = True,
           sill: bool = True) -> None:
    """Jamb / head / sill liner of a masonry opening: faces from the wall plane (y = 0) inwards to y = depth,
    normals pointing into the opening."""
    m.face([(x0, 0, z0), (x0, depth, z0), (x0, depth, z1), (x0, 0, z1)], mat)           # left jamb -> +X
    m.face([(x1, depth, z0), (x1, 0, z0), (x1, 0, z1), (x1, depth, z1)], mat)           # right jamb -> -X
    if head:
        m.face([(x0, 0, z1), (x0, depth, z1), (x1, depth, z1), (x1, 0, z1)], mat, flip=True)
    if sill:
        m.face([(x0, 0, z0), (x1, 0, z0), (x1, depth, z0), (x0, depth, z0)], mat, flip=True)


def stone_lintel(m: K.Mesh, x0: float, x1: float, z: float, mat: str = "limestone", *, h: float = STONE_LINTEL_H,
                 ear: float = STONE_LINTEL_EAR, proj: float = STONE_PROJ, depth: float = WYTHE) -> None:
    """Projecting stone lintel bearing ``ear`` each side of the opening, sitting with its underside at z."""
    m.box((x0 - ear, -proj, z), (x1 + ear, depth, z + h), mat)


def keyed_lintel(m: K.Mesh, x0: float, x1: float, z: float, mat: str = "limestone") -> None:
    """Stone lintel with a raised keystone (Renaissance-revival apartment houses)."""
    stone_lintel(m, x0, x1, z, mat)
    cx = (x0 + x1) / 2
    m.box((cx - 0.115, -STONE_PROJ - 0.025, z - 0.045), (cx + 0.115, WYTHE, z + STONE_LINTEL_H + 0.075), mat)


def soldier_lintel(m: K.Mesh, x0: float, x1: float, z: float, mat: str = "red_brick") -> None:
    """Brick soldier course (bricks on end) over the opening: 2 cm proud of the wall face."""
    m.box((x0 - 0.02, -0.020, z), (x1 + 0.02, WYTHE, z + BRICK_LEN), mat)


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
               ear: float = SILL_EAR, proj: float = SILL_PROJ, depth: float = WYTHE) -> None:
    """Projecting stone sill with a wash (top slopes down towards the street)."""
    a, b = x0 - ear, x1 + ear
    zt_out, zt_in = z + h - SILL_SLOPE, z + h
    m.face([(a, -proj, z), (b, -proj, z), (b, -proj, zt_out), (a, -proj, zt_out)], mat)                     # front
    m.face([(a, -proj, zt_out), (b, -proj, zt_out), (b, depth, zt_in), (a, depth, zt_in)], mat)             # wash
    m.face([(a, depth, zt_in), (b, depth, zt_in), (b, depth, z), (a, depth, z)], mat)                       # back
    m.face([(a, -proj, z), (a, -proj, zt_out), (a, depth, zt_in), (a, depth, z)], mat)                      # -X end
    m.face([(b, depth, z), (b, depth, zt_in), (b, -proj, zt_out), (b, -proj, z)], mat)                      # +X end
    m.face([(a, -proj, z), (a, depth, z), (b, depth, z), (b, -proj, z)], mat)                               # soffit


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


def interior_card(m: K.Mesh, x0: float, x1: float, z0: float, z1: float, y: float, lit: bool) -> None:
    """Card of interior imagery a few centimetres behind the glass (kills the 'hollow box' look from the street)."""
    mat = "interior_lit" if lit else "interior_unlit"
    m.face([(x0, y, z0), (x1, y, z0), (x1, y, z1), (x0, y, z1)], mat,
           uvs=[(0, 0), (2, 0), (2, 2), (0, 2)])


def double_hung(m: K.Mesh, x0: float, x1: float, z0: float, z1: float, *, lights_x: int = 1, lights_z: int = 1,
                frame_mat: str = SASH_WHITE, reveal_depth: float = REVEAL, lit: bool | None = None) -> None:
    """Complete double-hung window inside an opening x0..x1 / z0..z1: outer frame, upper and lower sash with the
    lower sash outboard, meeting rail overlap, and an interior card."""
    m.frame(x0, x1, z0, z1, reveal_depth - 0.012, reveal_depth + 0.070, CASING * 0.75, frame_mat)
    fx0, fx1 = x0 + CASING * 0.75, x1 - CASING * 0.75
    fz0, fz1 = z0 + CASING * 0.75, z1 - CASING * 0.75
    mid = (fz0 + fz1) / 2
    sash(m, fx0, fx1, mid - MEETING_RAIL / 2, fz1, reveal_depth + 0.030, lights_x=lights_x, lights_z=lights_z, frame_mat=frame_mat)
    sash(m, fx0, fx1, fz0, mid + MEETING_RAIL / 2, reveal_depth - 0.010, lights_x=lights_x, lights_z=lights_z, frame_mat=frame_mat)
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
                   width: float = 0.090, scroll: int = 5) -> None:
    """Scrolled cornice bracket (pressed metal / wood): an S-curve profile swept ``width`` across."""
    prof = [(y_face, z0)]
    for i in range(scroll + 1):
        t = i / scroll
        prof.append((y_face - proj * math.sin(t * math.pi / 2) ** 1.4, z0 + (z1 - z0) * t))
    prof.append((y_face, z1))
    m.extrude_profile(prof, x - width / 2, x + width / 2, mat, closed=True, caps=True, flip=True)


def dentils(m: K.Mesh, x0: float, x1: float, z0: float, z1: float, y_face: float, proj: float, mat: str,
            *, pitch: float = 0.120, ratio: float = 0.5) -> None:
    """Dentil course under a cornice or string course."""
    n = max(1, int((x1 - x0) / pitch))
    w = pitch * ratio
    for k in range(n):
        cx = x0 + pitch * (k + 0.5)
        m.box((cx - w / 2, y_face - proj, z0), (cx + w / 2, y_face, z1), mat)
