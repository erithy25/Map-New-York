"""Illuminated signage: shopfront fascia sign bands and LED display modules, with their sign faces.

Why this module exists
----------------------
The kit already modelled two bulletin billboards and a small projecting bracket sign, and the facade stage never
placed either.  The consequence was measured in the comparison lane: the Times Square daylight frame carries "no
signage of any kind - not a screen, not a billboard, not a shopfront sign, not a lit letter", and at night "the
emissive content of the model city is close to zero".  A New York street is a lit surface before it is anything
else, so the missing pieces are these.

What a sign here may and may not say
------------------------------------
ADR-004 governs appearance; deviation B5 records that advertising *copy* has no source in this environment and that
inventing it would be fabrication.  That reasoning is kept exactly: **nothing here carries invented advertising**.

* ``SIGN_FACE`` - a blank internally-lit panel.  This is what a shopfront gets when the building carries a **real**
  business name (DCWP licence / DOHMH permit / OSM ``name``): the name lives in ``awning_text`` on the same ``bin``
  in ``tiles/{tile}/buildings.parquet``, and the runtime binds it to this slot per instance.  An instanced offline
  render carries one texture per piece, not 30,381, so the verification frames show the lit panel without its
  legend and the report says so.
* ``SIGN_FACE_<KIND>`` - the generic New York trade wording for a storefront kind ("DELI GROCERY", "NAILS & SPA",
  "PHARMACY").  That wording is already shipped in ``awning_text`` for the storefronts with no known business name,
  and is flagged ``awning_real = false`` per building; baking it here states nothing the data does not already say.
* ``SIGN_FACE_LED_*`` - the physical face of an LED display: the pixel matrix itself on its black substrate.  It
  depicts the *hardware*, never any content, so a screen can be modelled where the zoning says a screen exists
  without asserting what it shows.

No brand, logo, product or slogan appears anywhere in this file, and the only words baked into a texture are the
generic trade wording the pipeline already publishes.

Slot naming follows the props library's runtime contract: a slot whose name begins with ``SIGN_FACE`` is a
runtime-swappable face whose UV 0..1 covers the visible panel exactly, u to the reader's right, v upwards.
"""
from __future__ import annotations

from pathlib import Path

import kitlib as K
import pieces_common as P
import facade_params as fp

# --------------------------------------------------------------------------- dimensions (real NYC sign practice)
BAND_W = 3.600           # nominal fascia band width: one 12 ft shopfront bay module
BAND_H = 0.800           # the sign fascia of a New York shopfront storey (pieces_storefront: Z_SIGN -> H_TOTAL)
BAND_D = 0.240           # projection of an internally-lit box sign off the fascia
BAND_FRAME = 0.055       # aluminium retainer around the face

LED_PANEL_W = 6.100      # 20 ft: the common modular display width
LED_PANEL_H = 3.050      # 10 ft
LED_BLADE_W = 3.050      # a vertical spectacular blade, 10 x 24 ft
LED_BLADE_H = 7.320
LED_RIBBON_W = 12.190    # a horizontal ribbon board, 40 x 4 ft
LED_RIBBON_H = 1.220
LED_D = 0.360            # cabinet depth: face plane to the wall plate
LED_BBOX_D = 0.500       # cabinet plus the galvanised standoff frame behind it
LED_PITCH_MM = 16.0      # pixel pitch of a large-format outdoor display

#: Generic New York trade wording per storefront kind.  This table mirrors
#: ``nycsim_pipeline.facade.derive.GENERIC_AWNING``, which is the authority because the pipeline writes that wording
#: into ``awning_text``.  ``pipeline/tests/test_facade_signage.py`` asserts the two agree exactly, so a baked legend
#: can never drift from the text the data ships.
GENERIC_SIGN_TEXT: dict[str, str] = {
    "bodega": "GROCERY - DELI - BEER",
    "deli": "DELI GROCERY",
    "pharmacy": "PHARMACY",
    "restaurant": "RESTAURANT",
    "bar": "BAR",
    "nail_hair": "NAILS & SPA",
    "laundromat": "LAUNDROMAT",
    "bank": "BANK",
    "clothing": "CLOTHING",
    "electronics": "ELECTRONICS",
    "grocery": "SUPERMARKET",
    "hardware": "HARDWARE",
    "coffee": "COFFEE",
    "pizza": "PIZZA",
    "dry_cleaner": "DRY CLEANERS",
    "generic_retail": "OPEN",
    "office_lobby": "",
    "residential_lobby": "",
    "garage_door": "",
    "vacant": "",
}

#: The kinds that get a worded band.  The rest (lobbies, a garage door, a vacant shop) carry no fascia legend at all.
WORDED_KINDS: tuple[str, ...] = tuple(k for k in fp.STOREFRONT_KINDS if GENERIC_SIGN_TEXT.get(k))

#: Field and letter colours per kind, as sRGB bytes.  These are ordinary New York shopfront sign colours - a plastic
#: box sign is white, red, green, blue or yellow - and carry no brand identity.
SIGN_COLOURS: dict[str, tuple[tuple[int, int, int], tuple[int, int, int]]] = {
    "bodega": ((196, 32, 34), (250, 248, 240)),
    "deli": ((214, 226, 236), (24, 46, 96)),
    "pharmacy": ((240, 240, 236), (28, 84, 52)),
    "restaurant": ((26, 58, 40), (244, 232, 198)),
    "bar": ((32, 34, 40), (226, 200, 130)),
    "nail_hair": ((246, 240, 246), (168, 42, 118)),
    "laundromat": ((238, 238, 234), (32, 82, 156)),
    "bank": ((238, 238, 232), (28, 44, 82)),
    "clothing": ((240, 238, 232), (36, 36, 38)),
    "electronics": ((28, 30, 36), (236, 232, 226)),
    "grocery": ((222, 68, 40), (250, 248, 240)),
    "hardware": ((236, 178, 32), (36, 34, 30)),
    "coffee": ((240, 234, 222), (74, 48, 30)),
    "pizza": ((236, 238, 232), (198, 40, 34)),
    "dry_cleaner": ((236, 238, 240), (34, 76, 140)),
    "generic_retail": ((242, 240, 234), (40, 40, 42)),
}

#: Emission strengths.  A plastic box sign is a lamp behind a diffuser; an LED display is brighter again; bulletin
#: vinyl only reflects its floodlights, so it carries the low term the kit already uses for a dim interior card.
#: The LED figure is set against the reference photographs rather than guessed: a large outdoor display runs at a
#: luminance comparable to a bright daytime sky and several stops above a night street, so at 3.0 the panel sits
#: just below the sky in the daylight frame and clips in the night frame, which is what the two photographs show.
#: Driving it to full white instead put 6.9 % of the daylight frame above 0.90 luma against the photograph's 3.3 %.
BAND_EMISSION = 2.2
LED_EMISSION = 3.0
BULLETIN_EMISSION = 0.55

TEX_PX_PER_M = 280       # sign legends are read at street distance; 280 px/m is one pixel per 3.6 mm
MAX_TEX_PX = 1536        # the kit embeds its textures in the glb, so a face texture stays inside this


def _gen_dir() -> Path:
    K.GENERATED_TEX.mkdir(parents=True, exist_ok=True)
    return K.GENERATED_TEX


def _font(size: int):
    from PIL import ImageFont
    path = Path(__file__).resolve().parents[3] / "assets" / "fonts" / "Overpass" / "overpass-bold.otf"
    if not path.exists():
        raise FileNotFoundError(f"sign legend font missing: {path}")
    return ImageFont.truetype(str(path), size)


def _fit(draw, text: str, box_w: int, box_h: int):
    """Largest Overpass Bold size whose rendering of ``text`` fits inside ``box_w`` x ``box_h``."""
    lo, hi, best = 6, max(8, box_h * 2), _font(6)
    while lo <= hi:
        mid = (lo + hi) // 2
        f = _font(mid)
        left, top, right, bottom = draw.textbbox((0, 0), text, font=f)
        if (right - left) <= box_w and (bottom - top) <= box_h:
            best, lo = f, mid + 1
        else:
            hi = mid - 1
    return best


def band_face_image(kind: str | None) -> str:
    """Sign-face image for a shopfront fascia band: the generic wording for ``kind``, or a blank panel for ``None``.

    A blank panel is what a shopfront with a *real* business name gets: the name is in the data, the runtime binds
    it, and this file asserts nothing about it.
    """
    from PIL import Image, ImageDraw
    p = _gen_dir() / f"sign_band_{kind or 'blank'}.png"
    if p.exists():
        return str(p)
    w, h = round(BAND_W * TEX_PX_PER_M), round(BAND_H * TEX_PX_PER_M)
    field, letter = SIGN_COLOURS.get(kind or "", ((246, 246, 242), (40, 40, 42)))
    img = Image.new("RGB", (w, h), field)
    d = ImageDraw.Draw(img)
    inset = round(h * 0.055)
    shade = tuple(int(c * 0.72) for c in field)
    d.rectangle([0, 0, w - 1, inset], fill=shade)                       # shadow under the top retainer
    d.rectangle([0, h - 1 - inset, w - 1, h - 1], fill=shade)
    text = GENERIC_SIGN_TEXT.get(kind or "", "")
    if text:
        f = _fit(d, text, int(w * 0.90), int(h * 0.52))
        d.text((w / 2, h / 2), text, font=f, fill=letter, anchor="mm")
    img.save(p)
    return str(p)


def led_face_image(tag: str, w_m: float, h_m: float) -> str:
    """The face of an LED display at its real pixel pitch: the matrix on its black substrate, and nothing else.

    Drawn one texel block per physical LED pixel across the whole panel, so the face reads as a screen rather than
    as a light box.  It carries no imagery and no text: the model asserts that a display is mounted here, never
    what it shows.
    """
    from PIL import Image, ImageDraw
    p = _gen_dir() / f"sign_led_{tag}.png"
    if p.exists():
        return str(p)
    pitch = LED_PITCH_MM / 1000.0
    nx, ny = max(8, round(w_m / pitch)), max(8, round(h_m / pitch))
    px = max(2, min(4, MAX_TEX_PX // max(nx, ny)))
    img = Image.new("RGB", (nx * px, ny * px), (7, 7, 9))
    d = ImageDraw.Draw(img)
    rnd = _lcg(20260907)
    for j in range(ny):
        for i in range(nx):
            x0, y0 = i * px, j * px
            # A white LED pixel is three emitters behind one lens; the lens reads as a single bright dot whose
            # brightness varies slightly from pixel to pixel.  No pattern, no shape, no legend.
            v = 0.78 + 0.22 * rnd()
            d.rectangle([x0, y0, x0 + px - 2, y0 + px - 2], fill=(int(236 * v), int(238 * v), int(232 * v)))
    img.save(p)
    return str(p)


def _lcg(seed: int):
    s = [seed]

    def nxt() -> float:
        s[0] = (1103515245 * s[0] + 12345) % 2147483648
        return s[0] / 2147483648.0
    return nxt


#: LED display sizes: piece id suffix -> (width m, height m, sign-face slot).
LED_SIZES: dict[str, tuple[float, float, str]] = {
    "panel_wall": (LED_PANEL_W, LED_PANEL_H, "SIGN_FACE_LED_PANEL"),
    "blade_tall": (LED_BLADE_W, LED_BLADE_H, "SIGN_FACE_LED_BLADE"),
    "ribbon": (LED_RIBBON_W, LED_RIBBON_H, "SIGN_FACE_LED_RIBBON"),
}


def reg_sign_materials() -> None:
    """Register every sign-face material.  Idempotent: ``kitlib`` caches materials by name."""
    K.generated_material("SIGN_FACE", image=band_face_image(None), roughness=0.42,
                         emission=(1, 1, 1), emission_strength=BAND_EMISSION)
    for kind in WORDED_KINDS:
        K.generated_material(f"SIGN_FACE_{kind.upper()}", image=band_face_image(kind), roughness=0.42,
                             emission=(1, 1, 1), emission_strength=BAND_EMISSION)
    for tag, (w, h, slot) in LED_SIZES.items():
        K.generated_material(slot, image=led_face_image(tag, w, h), roughness=0.30,
                             emission=(1, 1, 1), emission_strength=LED_EMISSION)
    # Blank floodlit bulletin vinyl for the two billboard pieces. It is white because an unposted bulletin is
    # white, and it stays blank because no source in this environment says what any New York bulletin carries.
    K.generated_material("SIGN_FACE_BULLETIN", base_color=(0.86, 0.86, 0.83, 1.0), roughness=0.55,
                         emission=(0.86, 0.86, 0.83), emission_strength=BULLETIN_EMISSION)


reg_sign_materials()


# --------------------------------------------------------------------------- shopfront fascia sign band
def _band(face_mat: str) -> K.Mesh:
    """Internally-lit box sign across the fascia of a shopfront: aluminium can, retainer frame, acrylic face."""
    m = K.Mesh()
    x0, x1 = -BAND_W / 2, BAND_W / 2
    y_out, y_face, y_back = -BAND_D + 0.02, -BAND_D + 0.038, 0.02
    f = BAND_FRAME
    m.box((x0, y_face, 0.0), (x1, y_back, BAND_H), P.ALU, faces="xXzZY")            # the can
    m.box((x0, y_out, 0.0), (x1, y_face, f), P.ALU)                                 # retainer, bottom
    m.box((x0, y_out, BAND_H - f), (x1, y_face, BAND_H), P.ALU)                     # retainer, top
    for xa, xb in ((x0, x0 + f), (x1 - f, x1)):                                     # retainer, ends
        m.box((xa, y_out, 0.0), (xb, y_face, BAND_H), P.ALU)
    # the illuminated face, unit UV (u to the reader's right, v up) so a runtime can swap the legend per instance
    m.face([(x0 + f, y_face, f), (x1 - f, y_face, f), (x1 - f, y_face, BAND_H - f), (x0 + f, y_face, BAND_H - f)],
           face_mat, uvs=[(0, 0), (1, 0), (1, 1), (0, 1)])
    return m


def _band_lod(face_mat: str) -> K.Mesh:
    m = K.Mesh()
    x0, x1 = -BAND_W / 2, BAND_W / 2
    y_face = -BAND_D + 0.038
    m.face([(x0, y_face, 0.0), (x1, y_face, 0.0), (x1, y_face, BAND_H), (x0, y_face, BAND_H)], face_mat,
           uvs=[(0, 0), (1, 0), (1, 1), (0, 1)])
    return m


def _reg_band(pid: str, face_mat: str, description: str, extra: dict) -> None:
    @K.register(pid, "storefront", anchor="wall_bottom_centre", nominal_size=(BAND_W, BAND_D, BAND_H),
                description=description, features=["storefront"], budget=6000,
                lod1=lambda _f=face_mat: _band_lod(_f), extra=extra)
    def _b(_f=face_mat):
        return _band(_f)


_reg_band(
    "storefront_sign_band", "SIGN_FACE",
    "Internally-lit shopfront fascia box sign, 3.60 x 0.80 m: aluminium can, retainer frame and a blank acrylic "
    "face on the runtime-swappable SIGN_FACE slot (UV 0..1 spans the face). Placed where the building carries a "
    "real business name, which the runtime binds from awning_text on the same bin.",
    {"sign_face_slot": "SIGN_FACE", "sign_face_uv": "0..1 over the visible face, u right, v up",
     "legend": "", "legend_source": "runtime, from buildings.parquet awning_text"})

for _kind in WORDED_KINDS:
    _reg_band(
        f"storefront_sign_band_{_kind}", f"SIGN_FACE_{_kind.upper()}",
        f"Internally-lit shopfront fascia box sign, 3.60 x 0.80 m, carrying the generic New York trade wording "
        f"\"{GENERIC_SIGN_TEXT[_kind]}\" for a {_kind.replace('_', ' ')} - the same wording the pipeline writes into "
        f"awning_text where no business name is known (awning_real = false).",
        {"sign_face_slot": f"SIGN_FACE_{_kind.upper()}", "sign_face_uv": "0..1 over the visible face, u right, v up",
         "storefront_kind": _kind, "legend": GENERIC_SIGN_TEXT[_kind],
         "legend_source": "facade.derive.GENERIC_AWNING (generic trade wording, not a business name)"})


# --------------------------------------------------------------------------- LED display modules
def _led(w: float, h: float, face_mat: str) -> K.Mesh:
    """A modular LED display cabinet on a galvanised standoff frame: black surround and the emissive matrix face."""
    m = K.Mesh()
    x0, x1 = -w / 2, w / 2
    y_out, y_face, y_back = -LED_D + 0.02, -LED_D + 0.04, 0.02
    bez = 0.070 if h > 2.0 else 0.050
    m.box((x0, y_face, 0.0), (x1, y_back, h), P.BLACK, faces="xXzZY")               # cabinet
    m.box((x0, y_out, 0.0), (x1, y_face, bez), P.BLACK)                             # bezel, bottom
    m.box((x0, y_out, h - bez), (x1, y_face, h), P.BLACK)                           # bezel, top
    for xa, xb in ((x0, x0 + bez), (x1 - bez, x1)):                                 # bezel, ends
        m.box((xa, y_out, 0.0), (xb, y_face, h), P.BLACK)
    m.face([(x0 + bez, y_face, bez), (x1 - bez, y_face, bez), (x1 - bez, y_face, h - bez), (x0 + bez, y_face, h - bez)],
           face_mat, uvs=[(0, 0), (1, 0), (1, 1), (0, 1)])
    posts = max(2, int(round(w / 3.0)) + 1)                                         # standoff frame behind the can
    for k in range(posts):
        x = min(max(x0 + w * k / (posts - 1), x0 + 0.07), x1 - 0.07)
        m.box((x - 0.055, y_back - 0.006, 0.05), (x + 0.055, y_back + 0.14, h - 0.05), P.GALV)
    for z in (min(0.16, h * 0.2), max(h - 0.16, h * 0.8)):
        m.box((x0 + 0.07, y_back - 0.002, z - 0.045), (x1 - 0.07, y_back + 0.12, z + 0.045), P.GALV)
    return m


def _led_lod(w: float, h: float, face_mat: str) -> K.Mesh:
    m = K.Mesh()
    x0, x1 = -w / 2, w / 2
    y_face = -LED_D + 0.04
    m.face([(x0, y_face, 0.0), (x1, y_face, 0.0), (x1, y_face, h), (x0, y_face, h)], face_mat,
           uvs=[(0, 0), (1, 0), (1, 1), (0, 1)])
    return m


_LED_DESCRIPTION = {
    "panel_wall": "Wall-mounted modular LED display, 6.10 x 3.05 m (20 x 10 ft) at 16 mm pixel pitch on a galvanised "
                  "standoff frame. Tiles edge to edge to clad a frontage.",
    "blade_tall": "Vertical LED spectacular blade, 3.05 x 7.32 m (10 x 24 ft) at 16 mm pixel pitch on a galvanised "
                  "standoff frame; the tall format that turns a Midtown corner.",
    "ribbon": "Horizontal LED ribbon board, 12.19 x 1.22 m (40 x 4 ft) at 16 mm pixel pitch: the band that runs "
              "across a frontage above the shopfronts.",
}


def _reg_led(tag: str, w: float, h: float, slot: str) -> None:
    @K.register(f"sign_led_{tag}", "billboard", anchor="wall_bottom_centre", nominal_size=(w, LED_BBOX_D, h),
                description=_LED_DESCRIPTION[tag] + f" The face is the {slot} slot: the pixel matrix itself, "
                                                    f"carrying no content.",
                features=["billboard"], budget=2500, lod1=lambda: _led_lod(w, h, slot),
                extra={"sign_face_slot": slot, "sign_face_uv": "0..1 over the visible face, u right, v up",
                       "pixel_pitch_mm": LED_PITCH_MM, "face_size_m": [round(w, 3), round(h, 3)],
                       "content": "none: the face models the display hardware, never an advertisement"})
    def _p():
        return _led(w, h, slot)


for _tag, (_w, _h, _slot) in LED_SIZES.items():
    _reg_led(_tag, _w, _h, _slot)
