"""The 12-dimensional pedestrian variety vector - the contract between ``core/peds`` and this lane.

The pedestrian simulation owns the vector and this module *consumes* it.  Its shape is fixed by
``docs/verification/traffic/REPORT.md`` §7: twelve floats, each in ``[0, 1]``, each quantised to a fixed
number of levels, in this order::

     #  dimension          levels
     0  age band                4
     1  stature                 6
     2  body mass               6
     3  skin tone               8
     4  hair style             10
     5  hair colour             8
     6  top garment            10
     7  top colour             12
     8  bottom garment          8
     9  bottom colour          12
    10  footwear                6
    11  accessory              10

4·6·6·8·10·8·10·12·8·12·6·10 = **63 700 992 000** distinguishable appearances, which is the number the
traffic report quotes, so the two sides agree by construction rather than by coincidence
(:func:`distinguishable_appearances` recomputes it and ``tests/test_character.py`` asserts the figure).

Decoding a float to a level is ``floor(v * levels)`` clamped to ``levels - 1``.  That inverts both of the
encodings a producer might reasonably use - ``k / (levels - 1)`` and the bin-centre ``(k + 0.5) / levels`` -
so the C++ side is free to use either.

Two things the vector does not carry, and how they are resolved here rather than invented:

**Sex.**  There is no sex dimension.  Each hairstyle carries the sex it is worn by in this city
(:data:`HAIR_STYLES`); the two unisex styles resolve from the parity of the stature and body-mass levels, so
the result is deterministic in the vector alone and both sexes appear.

**Gait.**  Activity comes from the simulation, not from appearance, so the vector carries no walk style.  The
playback rate of the shared locomotion clips is derived from the age band and the body mass
(:func:`gait_for`) - an 84-year-old and a very heavy pedestrian walk slower, a child faster - which is an
appearance-driven property and therefore legitimately derivable from these twelve numbers.
"""
from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from typing import Sequence

#: The contract: (dimension name, number of quantisation levels), in order.
PED_DIMENSIONS: tuple[tuple[str, int], ...] = (
    ("age_band", 4),
    ("stature", 6),
    ("body_mass", 6),
    ("skin_tone", 8),
    ("hair_style", 10),
    ("hair_colour", 8),
    ("top_garment", 10),
    ("top_colour", 12),
    ("bottom_garment", 8),
    ("bottom_colour", 12),
    ("footwear", 6),
    ("accessory", 10),
)
DIMENSION_NAMES: tuple[str, ...] = tuple(name for name, _ in PED_DIMENSIONS)
DIMENSION_LEVELS: tuple[int, ...] = tuple(levels for _, levels in PED_DIMENSIONS)
CONTRACT_VERSION = 2


def distinguishable_appearances() -> int:
    """The size of the appearance space the contract spans."""
    total = 1
    for levels in DIMENSION_LEVELS:
        total *= levels
    return total


# ------------------------------------------------------------------------------------------------- tables
#: MakeHuman's `age` macro is 1 year at 0.0, 25 years at 0.5 and 90 years at 1.0.
AGE_BANDS: tuple[dict, ...] = (
    {"id": "child", "age": 0.20, "label": "child, about 8", "years": 8},
    {"id": "young_adult", "age": 0.44, "label": "young adult, about 22", "years": 22},
    {"id": "middle_aged", "age": 0.62, "label": "middle-aged, about 45", "years": 45},
    {"id": "older", "age": 0.84, "label": "older, about 70", "years": 70},
)

#: MakeHuman's `height` macro. Combined with age and sex this spans roughly 1.25 m (child) to 1.95 m.
STATURES: tuple[dict, ...] = (
    {"id": "very_short", "height": 0.24},
    {"id": "short", "height": 0.40},
    {"id": "below_average", "height": 0.50},
    {"id": "average", "height": 0.60},
    {"id": "tall", "height": 0.74},
    {"id": "very_tall", "height": 0.90},
)

#: MakeHuman's `weight` macro with the `muscle` macro that goes with it - a heavy body is not a muscular one.
BODY_MASSES: tuple[dict, ...] = (
    {"id": "slight", "weight": 0.28, "muscle": 0.40},
    {"id": "lean", "weight": 0.40, "muscle": 0.54},
    {"id": "average", "weight": 0.52, "muscle": 0.56},
    {"id": "solid", "weight": 0.63, "muscle": 0.62},
    {"id": "heavy", "weight": 0.76, "muscle": 0.48},
    {"id": "very_heavy", "weight": 0.90, "muscle": 0.42},
)

#: Eight skin tones, light to dark.  Each carries the MakeHuman ethnic macro mix that produces the facial
#: morphology that goes with it and the family of CC0 skin materials to draw from; the actual material is
#: picked per age band and sex by :meth:`PedAppearance.skin_material`.  The distribution the simulation
#: samples is its own business - this table only says what each of the eight levels *is*.
SKIN_TONES: tuple[dict, ...] = (
    {"id": "very_fair", "family": "caucasian", "african": 0.02, "asian": 0.05, "caucasian": 0.93},
    {"id": "fair", "family": "caucasian", "african": 0.05, "asian": 0.10, "caucasian": 0.85},
    {"id": "light_olive", "family": "caucasian", "african": 0.08, "asian": 0.30, "caucasian": 0.62},
    {"id": "east_asian", "family": "asian", "african": 0.02, "asian": 0.92, "caucasian": 0.06},
    {"id": "tan", "family": "caucasian", "african": 0.26, "asian": 0.22, "caucasian": 0.52},
    {"id": "brown", "family": "african", "african": 0.55, "asian": 0.15, "caucasian": 0.30},
    {"id": "deep_brown", "family": "african", "african": 0.80, "asian": 0.05, "caucasian": 0.15},
    {"id": "dark", "family": "african", "african": 0.95, "asian": 0.02, "caucasian": 0.03},
)

#: Ten hairstyles.  ``sex`` is the MakeHuman `gender` macro worn with the style (1 = male); ``None`` means
#: unisex and is resolved from the rest of the vector.  ``asset`` is a MakeHuman CC0 hair mesh, except the
#: buzz cut, which MakeHuman has none of and which :func:`wardrobe.build_procedural_hair` cuts from the
#: scalp.  MakeHuman's `braid01` and the procedural top knot are in the wardrobe but outside the ten.
HAIR_STYLES: tuple[dict, ...] = (
    {"id": "buzz", "asset": "buzzcut", "procedural": True, "sex": 0.95, "label": "Buzz cut"},
    {"id": "short_crop", "asset": "short01", "procedural": False, "sex": 0.93, "label": "Short crop"},
    {"id": "side_part", "asset": "short02", "procedural": False, "sex": 0.90, "label": "Short side-part"},
    {"id": "textured", "asset": "short03", "procedural": False, "sex": 0.86, "label": "Short textured"},
    {"id": "short_curly", "asset": "short04", "procedural": False, "sex": None, "label": "Short curly"},
    {"id": "afro", "asset": "afro01", "procedural": False, "sex": None, "label": "Afro"},
    {"id": "bob", "asset": "bob01", "procedural": False, "sex": 0.08, "label": "Bob"},
    {"id": "long_bob", "asset": "bob02", "procedural": False, "sex": 0.08, "label": "Long bob"},
    {"id": "long", "asset": "long01", "procedural": False, "sex": 0.06, "label": "Long straight"},
    {"id": "ponytail", "asset": "ponytail01", "procedural": False, "sex": 0.07, "label": "Ponytail"},
)

#: Eight hair colours as sRGB hex, dark to light plus the two grey ones an older band needs.
HAIR_COLOURS: tuple[dict, ...] = (
    {"id": "black", "hex": "0f0d0c"},
    {"id": "dark_brown", "hex": "2a1a12"},
    {"id": "brown", "hex": "48301d"},
    {"id": "chestnut", "hex": "6a4324"},
    {"id": "auburn", "hex": "77361a"},
    {"id": "dark_blond", "hex": "8b6a39"},
    {"id": "blond", "hex": "c1a163"},
    {"id": "grey", "hex": "9b9994"},
)

#: Ten upper-body looks.  A look is a *base* wardrobe top and an optional layer over it, because "what a
#: pedestrian's top half looks like" is a garment plus what is worn over it, not one mesh.  ``base`` is None
#: for the suit: `suit_jacket_charcoal` is `male_elegantsuit01`, whose shirt and tie are part of the same
#: mesh, so a separate shirt under it only pokes through (:attr:`wardrobe.Garment.includes_shirt`).
TOP_GARMENTS: tuple[dict, ...] = (
    {"id": "tee", "base": "tee_white", "outer": None, "label": "Crew tee"},
    {"id": "tank", "base": "tank_grey", "outer": None, "label": "Tank top"},
    {"id": "polo", "base": "polo_grey", "outer": None, "label": "Polo shirt"},
    {"id": "button_shirt", "base": "shirt_oxford", "outer": None, "label": "Button-down shirt"},
    {"id": "scrubs", "base": "scrubs_top", "outer": None, "label": "Hospital scrubs"},
    {"id": "long_sleeve", "base": "longsleeve_navy", "outer": None, "label": "Long-sleeve tee"},
    {"id": "knit", "base": "sweater_knit", "outer": None, "label": "Knit sweater"},
    {"id": "hoodie", "base": "hoodie_grey", "outer": None, "label": "Pullover hoodie"},
    {"id": "jacket", "base": "tee_black", "outer": "jacket_field", "label": "Field jacket over a tee"},
    {"id": "suit", "base": None, "outer": "suit_jacket_charcoal", "label": "Suit jacket"},
)

#: Twelve garment colours for the top and twelve for the bottom, as sRGB hex.  They are separate tables
#: because the colours trousers come in are not the colours t-shirts come in.
TOP_COLOURS: tuple[dict, ...] = (
    {"id": "white", "hex": "e8e6e1"}, {"id": "black", "hex": "1b1b1d"},
    {"id": "grey", "hex": "6c6f74"}, {"id": "navy", "hex": "22304a"},
    {"id": "olive", "hex": "4a4e39"}, {"id": "burgundy", "hex": "5c2029"},
    {"id": "forest", "hex": "24402f"}, {"id": "mustard", "hex": "a97c2a"},
    {"id": "rust", "hex": "8c4a24"}, {"id": "sky", "hex": "7d9ec4"},
    {"id": "cream", "hex": "d8ccb4"}, {"id": "plum", "hex": "4a3a5e"},
)
BOTTOM_COLOURS: tuple[dict, ...] = (
    {"id": "indigo", "hex": "2f4260"}, {"id": "black", "hex": "1c1c1e"},
    {"id": "charcoal", "hex": "35373c"}, {"id": "khaki", "hex": "9c8a68"},
    {"id": "olive", "hex": "5a5d44"}, {"id": "grey", "hex": "6a6c70"},
    {"id": "stone", "hex": "b0a894"}, {"id": "brown", "hex": "4d3a29"},
    {"id": "light_denim", "hex": "6f8bad"}, {"id": "navy", "hex": "222c40"},
    {"id": "wine", "hex": "4a2530"}, {"id": "off_white", "hex": "e2ded4"},
)

#: Eight bottoms - eight different *cuts*, since the colour is a dimension of its own.
BOTTOM_GARMENTS: tuple[dict, ...] = (
    {"id": "jeans", "item": "jeans_indigo", "label": "Jeans"},
    {"id": "chinos", "item": "chinos_khaki", "label": "Chinos"},
    {"id": "suit_trousers", "item": "suit_trousers", "label": "Suit trousers"},
    {"id": "scrubs", "item": "scrubs_pants", "label": "Scrubs trousers"},
    {"id": "joggers", "item": "joggers_grey", "label": "Joggers"},
    {"id": "cargo", "item": "cargo_olive", "label": "Cargo trousers"},
    {"id": "shorts", "item": "shorts_denim", "label": "Denim shorts"},
    {"id": "kids_jeans", "item": "kids_jeans", "label": "Kid's jeans"},
)

#: Six footwear levels - six different MakeHuman shoe meshes, not six colours of one.
FOOTWEAR: tuple[dict, ...] = (
    {"id": "sneakers_white", "item": "sneakers_white", "label": "White sneakers"},
    {"id": "sneakers_black", "item": "sneakers_black", "label": "Black sneakers"},
    {"id": "work_boots", "item": "boots_work", "label": "Work boots"},
    {"id": "dress_shoes", "item": "shoes_dress", "label": "Dress shoes"},
    {"id": "loafers", "item": "shoes_loafer", "label": "Loafers"},
    {"id": "ankle_boots", "item": "boots_chelsea", "label": "Ankle boots"},
)

#: Ten accessory levels, of three kinds: nothing, a carried item, or something worn.  ``kind`` says which
#: builder realises it - a wardrobe garment, one of :data:`wardrobe.BAG_SPECS`, one of
#: :data:`wardrobe.HAT_SPECS`, or a fitted MakeHuman mesh.
ACCESSORIES: tuple[dict, ...] = (
    {"id": "none", "kind": None, "ref": None, "label": "Nothing"},
    {"id": "backpack", "kind": "bag", "ref": "backpack", "label": "Backpack"},
    {"id": "tote", "kind": "bag", "ref": "tote", "label": "Tote bag"},
    {"id": "shoulder_bag", "kind": "bag", "ref": "shoulder_bag", "label": "Shoulder bag"},
    {"id": "delivery_box", "kind": "bag", "ref": "delivery_box", "label": "Courier's insulated box"},
    {"id": "briefcase", "kind": "bag", "ref": "briefcase", "label": "Briefcase"},
    {"id": "glasses", "kind": "mhclo", "ref": "kwnet_at_optical_glasses", "label": "Glasses"},
    {"id": "cap", "kind": "hat", "ref": "cap_backwards", "label": "Backwards cap"},
    {"id": "beanie", "kind": "hat", "ref": "beanie_grey", "label": "Beanie"},
    {"id": "hivis_vest", "kind": "garment", "ref": "vest_hivis", "label": "ANSI class-2 hi-vis vest"},
)

_TABLES: dict[str, tuple[dict, ...]] = {
    "age_band": AGE_BANDS, "stature": STATURES, "body_mass": BODY_MASSES, "skin_tone": SKIN_TONES,
    "hair_style": HAIR_STYLES, "hair_colour": HAIR_COLOURS, "top_garment": TOP_GARMENTS,
    "top_colour": TOP_COLOURS, "bottom_garment": BOTTOM_GARMENTS, "bottom_colour": BOTTOM_COLOURS,
    "footwear": FOOTWEAR, "accessory": ACCESSORIES,
}
for _name, _levels in PED_DIMENSIONS:                     # the tables *are* the contract; keep them honest
    if len(_TABLES[_name]) != _levels:
        raise AssertionError(f"{_name}: table has {len(_TABLES[_name])} entries, contract says {_levels}")


# ------------------------------------------------------------------------------------------------ decoding
def quantise(value: float, levels: int) -> int:
    """One contract float to its level index."""
    if not math.isfinite(value):
        raise ValueError(f"variety value {value!r} is not finite")
    if not -1e-9 <= value <= 1.0 + 1e-9:
        raise ValueError(f"variety value {value!r} is outside [0, 1]")
    return min(max(int(value * levels), 0), levels - 1)


def levels_of(vector: Sequence[float]) -> tuple[int, ...]:
    """Quantise a whole 12-float contract vector."""
    if len(vector) != len(PED_DIMENSIONS):
        raise ValueError(f"variety vector has {len(vector)} dimensions, the contract has "
                         f"{len(PED_DIMENSIONS)}")
    return tuple(quantise(v, levels) for v, (_n, levels) in zip(vector, PED_DIMENSIONS))


def _linear(hex_code: str) -> tuple[float, float, float]:
    def lin(v: float) -> float:
        return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
    return tuple(lin(int(hex_code[i:i + 2], 16) / 255.0) for i in (0, 2, 4))  # type: ignore[return-value]


@dataclass(frozen=True)
class PedAppearance:
    """One pedestrian's decoded appearance: twelve level indices and everything they resolve to."""

    levels: tuple[int, ...]

    # -- raw level access -------------------------------------------------------------------------------
    def level(self, dimension: str) -> int:
        return self.levels[DIMENSION_NAMES.index(dimension)]

    def entry(self, dimension: str) -> dict:
        return _TABLES[dimension][self.level(dimension)]

    # -- body -------------------------------------------------------------------------------------------
    @property
    def sex(self) -> float:
        """The MakeHuman `gender` macro, 1 = male.

        Unisex hairstyles resolve from the parity of the stature and body-mass levels: deterministic in the
        vector, independent of any hash, and it splits those two styles evenly across the population.
        """
        declared = self.entry("hair_style")["sex"]
        if declared is not None:
            return float(declared)
        return 0.90 if (self.level("stature") + self.level("body_mass")) % 2 == 0 else 0.10

    @property
    def is_male(self) -> bool:
        return self.sex >= 0.5

    def macros(self) -> dict[str, float]:
        """The MakeHuman macro targets this appearance asks for."""
        age = self.entry("age_band")
        stature = self.entry("stature")
        mass = self.entry("body_mass")
        tone = self.entry("skin_tone")
        return {
            "gender": self.sex,
            "age": age["age"],
            "height": stature["height"],
            "weight": mass["weight"],
            "muscle": mass["muscle"],
            # Children are proportioned differently from adults; MakeHuman's `proportions` macro carries it.
            "proportions": 0.45 if age["id"] == "child" else 0.60,
            "cupsize": 0.0 if self.is_male else 0.45,
            "firmness": 0.5 if age["id"] in ("child", "young_adult") else 0.35,
            "african": tone["african"], "asian": tone["asian"], "caucasian": tone["caucasian"],
        }

    def skin_material(self) -> str:
        """The MakeHuman CC0 skin material for this tone, age band and sex."""
        age_word = {"child": "young", "young_adult": "young", "middle_aged": "middleage",
                    "older": "old"}[self.entry("age_band")["id"]]
        family = self.entry("skin_tone")["family"]
        return f"{age_word}_{family}_{'male' if self.is_male else 'female'}"

    # -- hair -------------------------------------------------------------------------------------------
    @property
    def hair(self) -> dict:
        return self.entry("hair_style")

    def hair_colour_rgb(self) -> tuple[float, float, float]:
        """Linear RGB, greyed towards the older band's own grey rather than by an extra dimension."""
        base = _linear(self.entry("hair_colour")["hex"])
        if self.entry("age_band")["id"] == "older":
            grey = _linear("9b9994")
            return tuple(b + (g - b) * 0.45 for b, g in zip(base, grey))  # type: ignore[return-value]
        return base

    # -- clothes ----------------------------------------------------------------------------------------
    def outfit(self) -> tuple[str, ...]:
        """The wardrobe item ids to put on this pedestrian, in load order."""
        top = self.entry("top_garment")
        items: list[str] = []
        if top["base"]:
            items.append(top["base"])
        items.append(self.entry("bottom_garment")["item"])
        if top["outer"]:
            items.append(top["outer"])
        accessory = self.entry("accessory")
        if accessory["kind"] == "garment":
            items.append(accessory["ref"])
        items.append(self.entry("footwear")["item"])
        return tuple(items)

    def colours(self) -> dict[str, tuple[float, float, float]]:
        """{wardrobe item id: linear RGB} - the tint the vector asks for, overriding the catalogue colour."""
        top = self.entry("top_garment")
        top_rgb = _linear(self.entry("top_colour")["hex"])
        bottom_rgb = _linear(self.entry("bottom_colour")["hex"])
        out: dict[str, tuple[float, float, float]] = {
            self.entry("bottom_garment")["item"]: bottom_rgb,
        }
        # The colour dimension names the *outermost* top: a jacket's colour is what you see, and the layer
        # under it keeps its own catalogue colour so the two do not come out identical.
        out[top["outer"] or top["base"]] = top_rgb
        return out

    # -- gait -------------------------------------------------------------------------------------------
    def gait(self) -> dict:
        return gait_for(self.entry("age_band")["id"], self.entry("body_mass")["id"])

    # -- reporting --------------------------------------------------------------------------------------
    def resolve(self) -> dict:
        """Human-readable resolution of every dimension, for the catalogue and the line-up render."""
        out = {name: self.entry(name)["id"] for name in DIMENSION_NAMES}
        out["sex"] = "male" if self.is_male else "female"
        out["skin_material"] = self.skin_material()
        out["outfit"] = list(self.outfit())
        out["gait"] = self.gait()["id"]
        return out


def gait_for(age_band: str, body_mass: str) -> dict:
    """Locomotion playback rate and posture from the two dimensions that legitimately drive them.

    Cadence data: a healthy adult walks at about 1.4 m/s, over-65s at about 1.1 m/s (a 0.78 factor), and
    children of eight at a higher cadence over a shorter stride.  Carrying more mass slows the cadence
    slightly.  The clip itself is the shared retargeted CMU walk; only its rate and a small spinal lean vary.
    """
    rate = {"child": 1.10, "young_adult": 1.04, "middle_aged": 1.00, "older": 0.78}[age_band]
    rate *= {"slight": 1.02, "lean": 1.01, "average": 1.0, "solid": 0.98, "heavy": 0.93,
             "very_heavy": 0.88}[body_mass]
    stoop = {"child": -1.0, "young_adult": 0.0, "middle_aged": 1.5, "older": 6.0}[age_band]
    stoop += {"slight": 0.0, "lean": 0.0, "average": 0.0, "solid": 0.5, "heavy": 1.5,
              "very_heavy": 2.5}[body_mass]
    ident = f"{age_band}_{body_mass}"
    return {"id": ident, "clip": "walk", "rate": round(rate, 4), "stoop_deg": round(stoop, 2)}


# ------------------------------------------------------------------------------------------------ sampling
def vector_from_seed(seed: int) -> tuple[float, ...]:
    """A deterministic contract vector from a 64-bit seed - bin centres, so it round-trips exactly.

    The runtime derives its own vectors; this exists so the build can generate a reproducible cast and so a
    test can check that decoding is stable.
    """
    digest = hashlib.blake2b(int(seed).to_bytes(8, "little", signed=False), digest_size=32).digest()
    return tuple((digest[i] % levels + 0.5) / levels for i, (_n, levels) in enumerate(PED_DIMENSIONS))


def spread_vectors(count: int, *, seed: int = 0x4E5943) -> list[tuple[float, ...]]:
    """``count`` contract vectors that between them exercise every level of every dimension.

    A plain hash of ``count`` seeds leaves whole levels unused when ``count`` is small - with 24 draws the
    chance of covering all 12 colours is negligible - and a cast that never wears half the wardrobe is not
    evidence that the wardrobe works.  So each dimension is walked as its own rotated cycle: dimension *d*
    takes level ``(i * stride_d + offset_d) mod levels_d``, with a stride coprime to the level count, which
    covers every level in the first ``levels_d`` draws and never repeats a whole vector within ``count``.
    """
    if count < 1:
        raise ValueError("count must be positive")
    digest = hashlib.blake2b(int(seed).to_bytes(8, "little", signed=False), digest_size=64).digest()
    out: list[tuple[float, ...]] = []
    for i in range(count):
        values = []
        for d, (_name, levels) in enumerate(PED_DIMENSIONS):
            stride = 1
            for candidate in range(max(levels // 2, 1), levels):
                if math.gcd(candidate, levels) == 1:
                    stride = candidate
                    break
            offset = digest[d] % levels
            level = (i * stride + offset) % levels
            values.append((level + 0.5) / levels)
        out.append(tuple(values))
    return out


def contract() -> dict:
    """The machine-readable contract published in ``blender_out/character/npc_variety.json``."""
    return {
        "schema_version": CONTRACT_VERSION,
        "source": "docs/verification/traffic/REPORT.md section 7",
        "encoding": "12 floats in [0,1]; level = clamp(floor(v * levels), 0, levels-1)",
        "dimensions": [{"index": i, "name": name, "levels": levels}
                       for i, (name, levels) in enumerate(PED_DIMENSIONS)],
        "distinguishable_appearances": distinguishable_appearances(),
        "derived": {
            "sex": "hair style's own sex; the two unisex styles use the parity of stature + body mass",
            "gait": "playback rate and spinal lean from age band and body mass (variety.gait_for)",
        },
        "tables": {
            "age_band": [dict(e) for e in AGE_BANDS],
            "stature": [dict(e) for e in STATURES],
            "body_mass": [dict(e) for e in BODY_MASSES],
            "skin_tone": [dict(e) for e in SKIN_TONES],
            "hair_style": [dict(e) for e in HAIR_STYLES],
            "hair_colour": [dict(e) for e in HAIR_COLOURS],
            "top_garment": [dict(e) for e in TOP_GARMENTS],
            "top_colour": [dict(e) for e in TOP_COLOURS],
            "bottom_garment": [dict(e) for e in BOTTOM_GARMENTS],
            "bottom_colour": [dict(e) for e in BOTTOM_COLOURS],
            "footwear": [dict(e) for e in FOOTWEAR],
            "accessory": [dict(e) for e in ACCESSORIES],
        },
        "wardrobe_items_reachable": sorted({
            item for entry in TOP_GARMENTS for item in (entry["base"], entry["outer"]) if item
        } | {e["item"] for e in BOTTOM_GARMENTS} | {e["item"] for e in FOOTWEAR}
            | {e["ref"] for e in ACCESSORIES if e["kind"] == "garment"}),
        "wardrobe_items_total": _wardrobe_size(),
    }


def _wardrobe_size() -> int:
    """How many items the wardrobe catalogue holds.

    Imported lazily: :mod:`wardrobe` pulls in ``bpy``, and everything above this line is plain Python so the
    contract can be decoded and tested without starting Blender.
    """
    import wardrobe  # noqa: PLC0415

    return len(wardrobe.WARDROBE)


def decode(vector: Sequence[float]) -> PedAppearance:
    """The entry point: one contract vector to one buildable appearance."""
    return PedAppearance(levels=levels_of(vector))
