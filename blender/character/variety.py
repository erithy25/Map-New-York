"""The 12-dimensional pedestrian variety vector - the contract between this lane and ``core/peds``.

``core/peds`` was still empty when this stage ran, so the vector is *defined* here and published as
``blender_out/character/npc_variety.json`` for the peds agent to consume.  Each dimension is an unsigned
8-bit index into a fixed table, so one pedestrian's appearance is 12 bytes and the C++ side needs no strings:

===  =====================  =======================================================================
 #   dimension              meaning
===  =====================  =======================================================================
 0   ``body_preset``        index into :data:`BODY_PRESETS` (24 MakeHuman macro-target bodies)
 1   ``skin_tone``          index into :data:`SKIN_TONES` (18 MakeHuman CC0 skin materials)
 2   ``hair``               index into :data:`wardrobe.HAIRSTYLES` (12 styles, 255 = bald/covered)
 3   ``top``                index into :data:`TOPS` (wardrobe items with slot ``top``)
 4   ``bottom``             index into :data:`BOTTOMS`
 5   ``shoes``              index into :data:`SHOES`
 6   ``outerwear``          index into :data:`OUTERWEAR`, 255 = none
 7   ``bag``                index into :data:`BAGS`, 255 = none
 8   ``hat``                index into :data:`HATS`, 255 = none
 9   ``glasses``            index into :data:`GLASSES`, 255 = none
10   ``height_scale``       0-255 mapped linearly onto [0.97, 1.03] of the preset's height
11   ``walk_style``         index into :data:`WALK_STYLES` - which locomotion clip set and playback rate
===  =====================  =======================================================================

The same 12 bytes drive the Blender build (this module) and the runtime instancing, so a pedestrian looks the
same in a verification render as it will in the engine.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

import wardrobe

NONE = 255

#: 24 base bodies spread across the MakeHuman macro targets (gender, age, muscle, weight, height,
#: proportions and the three ethnic components).  The distribution follows the 2020 Census ACS profile of
#: New York City: 30.9 % White non-Hispanic, 28.7 % Hispanic, 20.2 % Black, 15.6 % Asian.
BODY_PRESETS: tuple[dict, ...] = (
    # MakeHuman's `age` macro is 1 year at 0.0, 25 years at 0.5 and 90 years at 1.0, so an adult never has
    # age below ~0.42; `height` 0.4-0.8 spans roughly 1.55-1.95 m once gender and age are applied.
    {"id": "m_young_slim", "gender": 0.92, "age": 0.44, "muscle": 0.45, "weight": 0.38, "height": 0.62,
     "proportions": 0.6, "african": 0.10, "asian": 0.10, "caucasian": 0.80},
    {"id": "m_young_athletic", "gender": 0.95, "age": 0.46, "muscle": 0.76, "weight": 0.52, "height": 0.70,
     "proportions": 0.7, "african": 0.75, "asian": 0.05, "caucasian": 0.20},
    {"id": "m_young_heavy", "gender": 0.90, "age": 0.48, "muscle": 0.45, "weight": 0.78, "height": 0.58,
     "proportions": 0.5, "african": 0.20, "asian": 0.15, "caucasian": 0.65},
    {"id": "m_young_asian", "gender": 0.90, "age": 0.43, "muscle": 0.50, "weight": 0.42, "height": 0.52,
     "proportions": 0.6, "african": 0.02, "asian": 0.93, "caucasian": 0.05},
    {"id": "m_mid_average", "gender": 0.90, "age": 0.58, "muscle": 0.52, "weight": 0.56, "height": 0.60,
     "proportions": 0.5, "african": 0.12, "asian": 0.12, "caucasian": 0.76},
    {"id": "m_mid_stocky", "gender": 0.93, "age": 0.62, "muscle": 0.66, "weight": 0.70, "height": 0.50,
     "proportions": 0.45, "african": 0.30, "asian": 0.10, "caucasian": 0.60},
    {"id": "m_mid_hispanic", "gender": 0.90, "age": 0.56, "muscle": 0.55, "weight": 0.58, "height": 0.52,
     "proportions": 0.55, "african": 0.25, "asian": 0.20, "caucasian": 0.55},
    {"id": "m_mid_tall", "gender": 0.94, "age": 0.54, "muscle": 0.60, "weight": 0.48, "height": 0.80,
     "proportions": 0.7, "african": 0.15, "asian": 0.05, "caucasian": 0.80},
    {"id": "m_old_lean", "gender": 0.88, "age": 0.80, "muscle": 0.36, "weight": 0.42, "height": 0.52,
     "proportions": 0.4, "african": 0.10, "asian": 0.15, "caucasian": 0.75},
    {"id": "m_old_heavy", "gender": 0.88, "age": 0.84, "muscle": 0.40, "weight": 0.74, "height": 0.48,
     "proportions": 0.4, "african": 0.55, "asian": 0.10, "caucasian": 0.35},
    {"id": "m_old_asian", "gender": 0.88, "age": 0.82, "muscle": 0.38, "weight": 0.45, "height": 0.44,
     "proportions": 0.45, "african": 0.02, "asian": 0.92, "caucasian": 0.06},
    {"id": "m_teen", "gender": 0.85, "age": 0.34, "muscle": 0.40, "weight": 0.38, "height": 0.55,
     "proportions": 0.6, "african": 0.35, "asian": 0.20, "caucasian": 0.45},
    {"id": "f_young_slim", "gender": 0.08, "age": 0.44, "muscle": 0.36, "weight": 0.36, "height": 0.55,
     "proportions": 0.65, "african": 0.10, "asian": 0.12, "caucasian": 0.78},
    {"id": "f_young_athletic", "gender": 0.05, "age": 0.45, "muscle": 0.68, "weight": 0.46, "height": 0.60,
     "proportions": 0.7, "african": 0.70, "asian": 0.05, "caucasian": 0.25},
    {"id": "f_young_curvy", "gender": 0.05, "age": 0.48, "muscle": 0.42, "weight": 0.68, "height": 0.52,
     "proportions": 0.6, "african": 0.30, "asian": 0.15, "caucasian": 0.55},
    {"id": "f_young_asian", "gender": 0.06, "age": 0.43, "muscle": 0.40, "weight": 0.34, "height": 0.45,
     "proportions": 0.6, "african": 0.02, "asian": 0.93, "caucasian": 0.05},
    {"id": "f_mid_average", "gender": 0.08, "age": 0.58, "muscle": 0.44, "weight": 0.55, "height": 0.53,
     "proportions": 0.5, "african": 0.15, "asian": 0.15, "caucasian": 0.70},
    {"id": "f_mid_hispanic", "gender": 0.08, "age": 0.56, "muscle": 0.46, "weight": 0.62, "height": 0.48,
     "proportions": 0.5, "african": 0.28, "asian": 0.20, "caucasian": 0.52},
    {"id": "f_mid_tall", "gender": 0.10, "age": 0.54, "muscle": 0.50, "weight": 0.44, "height": 0.72,
     "proportions": 0.7, "african": 0.20, "asian": 0.05, "caucasian": 0.75},
    {"id": "f_old_lean", "gender": 0.10, "age": 0.82, "muscle": 0.32, "weight": 0.42, "height": 0.45,
     "proportions": 0.4, "african": 0.12, "asian": 0.15, "caucasian": 0.73},
    {"id": "f_old_heavy", "gender": 0.10, "age": 0.85, "muscle": 0.34, "weight": 0.72, "height": 0.42,
     "proportions": 0.4, "african": 0.50, "asian": 0.12, "caucasian": 0.38},
    {"id": "f_teen", "gender": 0.12, "age": 0.33, "muscle": 0.36, "weight": 0.36, "height": 0.50,
     "proportions": 0.65, "african": 0.30, "asian": 0.25, "caucasian": 0.45},
    {"id": "child_boy", "gender": 0.80, "age": 0.17, "muscle": 0.40, "weight": 0.45, "height": 0.40,
     "proportions": 0.5, "african": 0.30, "asian": 0.20, "caucasian": 0.50},
    {"id": "child_girl", "gender": 0.20, "age": 0.16, "muscle": 0.38, "weight": 0.44, "height": 0.38,
     "proportions": 0.5, "african": 0.25, "asian": 0.25, "caucasian": 0.50},
)

#: MakeHuman CC0 skin materials, ordered light to dark within each age band.
SKIN_TONES: tuple[str, ...] = (
    "young_caucasian_female", "young_caucasian_female2", "young_caucasian_male", "young_caucasian_male2",
    "young_asian_female", "young_asian_male", "young_african_female", "young_african_male",
    "middleage_caucasian_female", "middleage_caucasian_male", "middleage_asian_female",
    "middleage_asian_male", "middleage_african_female", "middleage_african_male",
    "old_caucasian_female", "old_caucasian_male", "old_asian_male", "old_african_male",
)

TOPS: tuple[str, ...] = tuple(g.item_id for g in wardrobe.WARDROBE if g.slot == "top")
BOTTOMS: tuple[str, ...] = tuple(g.item_id for g in wardrobe.WARDROBE if g.slot == "bottom")
SHOES: tuple[str, ...] = tuple(g.item_id for g in wardrobe.WARDROBE if g.slot == "shoes")
OUTERWEAR: tuple[str, ...] = tuple(g.item_id for g in wardrobe.WARDROBE if g.slot == "outerwear")
HATS: tuple[str, ...] = ("hijab_navy", "cap_backwards", "beanie_grey", "fedora01")

#: Carried items. ``backpack`` and ``tote`` are procedural; ``delivery_box`` is the insulated cube every
#: e-bike courier in Manhattan has on their back.
BAGS: tuple[str, ...] = ("backpack", "tote", "shoulder_bag", "delivery_box", "shopping_bags", "briefcase")
GLASSES: tuple[str, ...] = ("kwnet_at_optical_glasses", "spamrakuen_tbm_glasses_frames_01",
                            "toigo_round_glasses_leopard", "ews_3d_glasses")

#: Locomotion styles: which clip the runtime plays and at what rate, plus the posture offsets applied at
#: build time so two pedestrians with the same clip still do not look identical.
WALK_STYLES: tuple[dict, ...] = (
    {"id": "relaxed", "clip": "walk", "rate": 0.94, "stoop_deg": 1.0, "arm_swing": 1.0},
    {"id": "brisk", "clip": "walk", "rate": 1.14, "stoop_deg": -1.0, "arm_swing": 1.2},
    {"id": "hurried", "clip": "jog", "rate": 0.86, "stoop_deg": -2.0, "arm_swing": 1.3},
    {"id": "strolling", "clip": "walk", "rate": 0.80, "stoop_deg": 2.0, "arm_swing": 0.85},
    {"id": "elderly", "clip": "walk", "rate": 0.72, "stoop_deg": 6.0, "arm_swing": 0.6},
    {"id": "phone", "clip": "phone_walk", "rate": 0.90, "stoop_deg": 4.0, "arm_swing": 0.4},
    {"id": "umbrella", "clip": "walk", "rate": 0.92, "stoop_deg": 2.0, "arm_swing": 0.5},
    {"id": "loaded", "clip": "walk", "rate": 0.84, "stoop_deg": 5.0, "arm_swing": 0.5},
)

DIMENSIONS: tuple[str, ...] = ("body_preset", "skin_tone", "hair", "top", "bottom", "shoes", "outerwear",
                               "bag", "hat", "glasses", "height_scale", "walk_style")

TABLE_SIZES: dict[str, int] = {
    "body_preset": len(BODY_PRESETS), "skin_tone": len(SKIN_TONES), "hair": len(wardrobe.HAIRSTYLES),
    "top": len(TOPS), "bottom": len(BOTTOMS), "shoes": len(SHOES), "outerwear": len(OUTERWEAR),
    "bag": len(BAGS), "hat": len(HATS), "glasses": len(GLASSES), "height_scale": 256,
    "walk_style": len(WALK_STYLES),
}

#: Within-preset stature variation. Kept narrow (+/-3 %): the presets' own `height` macro
#: already spans the population, and compounding the two produced 1.3 m adults.
HEIGHT_SCALE_RANGE = (0.97, 1.03)


@dataclass
class VarietyVector:
    """One pedestrian's 12 bytes."""

    body_preset: int = 0
    skin_tone: int = 0
    hair: int = 0
    top: int = 0
    bottom: int = 0
    shoes: int = 0
    outerwear: int = NONE
    bag: int = NONE
    hat: int = NONE
    glasses: int = NONE
    height_scale: int = 128
    walk_style: int = 0

    def as_bytes(self) -> bytes:
        return bytes(getattr(self, d) for d in DIMENSIONS)

    def as_dict(self) -> dict:
        return {d: getattr(self, d) for d in DIMENSIONS}

    @property
    def height_multiplier(self) -> float:
        lo, hi = HEIGHT_SCALE_RANGE
        return lo + (hi - lo) * (self.height_scale / 255.0)

    def resolve(self) -> dict:
        """Human-readable resolution of every index (used by the catalog and the line-up render)."""
        preset = BODY_PRESETS[self.body_preset % len(BODY_PRESETS)]
        return {
            "body_preset": preset["id"],
            "skin_tone": SKIN_TONES[self.skin_tone % len(SKIN_TONES)],
            "hair": None if self.hair == NONE else wardrobe.HAIRSTYLES[self.hair % len(wardrobe.HAIRSTYLES)][0],
            "top": TOPS[self.top % len(TOPS)],
            "bottom": BOTTOMS[self.bottom % len(BOTTOMS)],
            "shoes": SHOES[self.shoes % len(SHOES)],
            "outerwear": None if self.outerwear == NONE else OUTERWEAR[self.outerwear % len(OUTERWEAR)],
            "bag": None if self.bag == NONE else BAGS[self.bag % len(BAGS)],
            "hat": None if self.hat == NONE else HATS[self.hat % len(HATS)],
            "glasses": None if self.glasses == NONE else GLASSES[self.glasses % len(GLASSES)],
            "height_multiplier": round(self.height_multiplier, 4),
            "walk_style": WALK_STYLES[self.walk_style % len(WALK_STYLES)]["id"],
        }

    @classmethod
    def from_seed(cls, seed: int, *, none_rates: dict[str, float] | None = None) -> "VarietyVector":
        """Deterministic vector from a 64-bit seed (the same hash the runtime will use).

        The runtime derives the seed from the pedestrian's spawn id, so a given pedestrian always looks the
        same.  ``none_rates`` gives the probability that an optional slot is empty.
        """
        rates = {"outerwear": 0.35, "bag": 0.45, "hat": 0.72, "glasses": 0.78, "hair": 0.04}
        rates.update(none_rates or {})
        digest = hashlib.blake2b(seed.to_bytes(8, "little", signed=False), digest_size=32).digest()
        vector = cls()
        for i, dim in enumerate(DIMENSIONS):
            raw = digest[i]
            size = TABLE_SIZES[dim]
            if dim in rates and (digest[i + 16] / 255.0) < rates[dim]:
                setattr(vector, dim, NONE)
                continue
            setattr(vector, dim, raw % size if size < 256 else raw)
        return vector


def contract() -> dict:
    """The machine-readable contract published for ``core/peds``."""
    return {
        "schema_version": 1,
        "dimensions": list(DIMENSIONS),
        "encoding": "12 x uint8, index into the table named by the dimension; 255 = absent for optional slots",
        "none_value": NONE,
        "tables": {
            "body_preset": [p["id"] for p in BODY_PRESETS],
            "skin_tone": list(SKIN_TONES),
            "hair": [h[0] for h in wardrobe.HAIRSTYLES],
            "top": list(TOPS), "bottom": list(BOTTOMS), "shoes": list(SHOES),
            "outerwear": list(OUTERWEAR), "bag": list(BAGS), "hat": list(HATS), "glasses": list(GLASSES),
            "walk_style": [w["id"] for w in WALK_STYLES],
        },
        "height_scale": {"range": list(HEIGHT_SCALE_RANGE), "encoding": "linear over 0..255"},
        "walk_styles": list(WALK_STYLES),
        "seed_hash": "blake2b(seed_le_u64, digest_size=32); byte i = dimension i, byte i+16 = absence roll",
    }
