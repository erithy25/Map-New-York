"""Shell material definitions for the building stage (no ``bpy`` at import time).

The shells used to ship one flat colour, one roughness and one metallic value per material class.
That is what made the Lower Manhattan skyline render as "flat pastel solids" in the comparison
lane's Brooklyn Heights Promenade assessment while the photograph showed dark glass with a tonal
range from near-black to specular white.  Two things were missing and both are authored here:

**Reflectance.**  A curtain-wall tower is dark and mirror-like: almost all of what the eye sees on
it is a reflection of the sky above and of the buildings opposite, which is where the near-black to
specular-white range comes from.  A base colour with 4 % Fresnel and roughness 0.12 cannot produce
that.  Each class now carries the full analytic set — base colour, roughness, metallic, specular
level, IOR — and glass is authored as a dark, low-roughness, part-metallic surface.  This is a
*shading* approximation, not a measurement: no reflectance was measured for any NYC building, and
ADR-004 governs how the class itself was assigned.

**Per-building variation.**  One colour per class makes a block of brownstones a single flat wall.
``lit_seed`` (DATA_CONTRACTS §5.2) exists so per-building variation can be deterministic, and
:func:`tone_index` / :func:`tone_of` turn it into a small, quantised tint offset.  It is quantised
rather than continuous because the shipped glTF carries one material per primitive: a continuous
per-building colour would need a per-vertex ``COLOR_0``, which Blender writes as float32 VEC3 and
which measured at **+23 % on the tile file** — too much for the ADR-003 budget — while
``TONES`` materials per class cost only their own JSON.

Nothing here is texture-mapped: analytic materials only, following the vehicles lane
(`docs/verification/vehicles/REPORT.md` §6.2), so none of this costs disk.
"""
from __future__ import annotations

from dataclasses import dataclass

#: Tone buckets per material class.  3 is the most that stays inside a few per cent of tile bytes.
TONES = 3


@dataclass(frozen=True)
class ShellMaterial:
    """One material class as the shell renders it."""

    base_color: tuple[float, float, float]
    roughness: float = 0.72
    metallic: float = 0.0
    #: Principled "Specular IOR Level" — 0.5 is the 4 % dielectric default, higher is glossier.
    specular: float = 0.5
    ior: float = 1.45
    #: peak relative brightness offset of the outer tone buckets (0.10 = +-10 %)
    tone_amp: float = 0.0
    #: peak roughness offset of the outer tone buckets, absolute
    rough_amp: float = 0.0


# Masonry and stone vary building to building far more than they vary within a class, so they carry
# the largest tone amplitude.  Glass varies mostly in *roughness* — the difference between a 1960s
# tower and a 2010s one is how sharp the reflection is — so its colour amplitude is small and its
# roughness amplitude is not.
MATERIALS: dict[str, ShellMaterial] = {
    "red_brick":          ShellMaterial((0.42, 0.16, 0.12), 0.78, 0.0, 0.42, 1.45, 0.12, 0.05),
    "brown_brick":        ShellMaterial((0.31, 0.20, 0.15), 0.78, 0.0, 0.42, 1.45, 0.12, 0.05),
    "tan_brick":          ShellMaterial((0.62, 0.51, 0.37), 0.76, 0.0, 0.42, 1.45, 0.10, 0.05),
    "white_glazed_brick": ShellMaterial((0.80, 0.79, 0.74), 0.45, 0.0, 0.60, 1.50, 0.06, 0.06),
    "brownstone":         ShellMaterial((0.34, 0.22, 0.15), 0.80, 0.0, 0.40, 1.45, 0.12, 0.04),
    "limestone":          ShellMaterial((0.72, 0.68, 0.58), 0.66, 0.0, 0.45, 1.48, 0.08, 0.05),
    "terracotta":         ShellMaterial((0.60, 0.33, 0.22), 0.62, 0.0, 0.50, 1.48, 0.10, 0.05),
    "cast_iron":          ShellMaterial((0.16, 0.17, 0.17), 0.42, 0.85, 0.55, 2.20, 0.06, 0.06),
    # dark, sharp and part-metallic: the sky and the tower opposite are most of what is seen on it
    "glass_curtain":      ShellMaterial((0.085, 0.105, 0.125), 0.075, 0.55, 0.85, 1.52, 0.05, 0.05),
    "concrete":           ShellMaterial((0.55, 0.54, 0.51), 0.80, 0.0, 0.38, 1.45, 0.09, 0.05),
    "stucco":             ShellMaterial((0.72, 0.68, 0.60), 0.84, 0.0, 0.34, 1.45, 0.09, 0.04),
    "vinyl_siding":       ShellMaterial((0.70, 0.70, 0.66), 0.58, 0.0, 0.48, 1.47, 0.10, 0.04),
    "wood_clapboard":     ShellMaterial((0.60, 0.56, 0.48), 0.70, 0.0, 0.40, 1.45, 0.12, 0.04),
    "stone_rubble":       ShellMaterial((0.45, 0.43, 0.39), 0.86, 0.0, 0.34, 1.45, 0.10, 0.04),
    "metal_panel":        ShellMaterial((0.48, 0.50, 0.52), 0.32, 0.80, 0.60, 2.00, 0.07, 0.06),
    "granite":            ShellMaterial((0.40, 0.39, 0.38), 0.38, 0.0, 0.60, 1.55, 0.08, 0.06),
    "precast":            ShellMaterial((0.63, 0.62, 0.59), 0.74, 0.0, 0.40, 1.45, 0.08, 0.05),
    "roof_membrane":      ShellMaterial((0.30, 0.30, 0.31), 0.86, 0.0, 0.32, 1.45, 0.06, 0.03),
    "tar_roof":           ShellMaterial((0.13, 0.13, 0.13), 0.90, 0.0, 0.28, 1.45, 0.05, 0.03),
    "corrugated_metal":   ShellMaterial((0.45, 0.46, 0.47), 0.44, 0.80, 0.55, 2.00, 0.07, 0.06),
}

DEFAULT = ShellMaterial((0.60, 0.60, 0.60), 0.72, 0.0, 0.50, 1.45, 0.06, 0.03)


def spec(name: str) -> ShellMaterial:
    return MATERIALS.get(name, DEFAULT)


def tone_index(lit_seed: int, tones: int = TONES) -> int:
    """Which tone bucket a building falls in.  Deterministic, from ``lit_seed`` alone.

    The engine reproduces it from the two exported halves:
    ``lit_seed = _LIT_SEED_HI * 65536 + _LIT_SEED_LO``, then this hash.  It is a plain
    multiply-xor-shift so a shader can do it in two instructions; the constant is the 32-bit
    golden-ratio odd multiplier used elsewhere in this project for seed mixing.
    """
    h = (int(lit_seed) & 0xFFFFFFFF) * 2654435761 & 0xFFFFFFFF
    h ^= h >> 15
    return int(h % max(int(tones), 1))


def _offset(i: int, tones: int) -> float:
    """Tone bucket -> symmetric offset in [-1, 1] (a single bucket gets 0)."""
    if tones <= 1:
        return 0.0
    return (2.0 * i / (tones - 1)) - 1.0


def tone_of(name: str, i: int, tones: int = TONES) -> tuple[tuple[float, float, float], float]:
    """``(base_color, roughness)`` of one tone bucket of one class."""
    m = spec(name)
    k = _offset(i, tones)
    scale = 1.0 + m.tone_amp * k
    col = tuple(min(1.0, max(0.0, c * scale)) for c in m.base_color)
    rough = min(1.0, max(0.015, m.roughness + m.rough_amp * k))
    return col, rough  # type: ignore[return-value]


def material_key(name: str, tone: int) -> str:
    """glTF material / Blender object suffix for a class and tone bucket."""
    return name if tone == 0 else f"{name}_t{int(tone)}"


def base_class(key: str) -> str:
    """Inverse of :func:`material_key` — the class a possibly tone-suffixed name belongs to."""
    if key in MATERIALS:
        return key
    head, _, tail = key.rpartition("_t")
    if head and tail.isdigit() and head in MATERIALS:
        return head
    return key


def tone_of_key(key: str) -> int:
    if key in MATERIALS:
        return 0
    head, _, tail = key.rpartition("_t")
    if head and tail.isdigit() and head in MATERIALS:
        return int(tail)
    return 0


def build_bpy_material(key: str):
    """Create (or fetch) the Blender material for ``NYCSIM_<key>``."""
    import bpy

    bname = f"NYCSIM_{key}"
    mat = bpy.data.materials.get(bname)
    if mat is not None:
        return mat
    name = base_class(key)
    col, rough = tone_of(name, tone_of_key(key))
    m = spec(name)
    mat = bpy.data.materials.new(bname)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (col[0], col[1], col[2], 1.0)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = m.metallic
    for socket, value in (("Specular IOR Level", m.specular), ("IOR", m.ior)):
        if socket in bsdf.inputs:
            bsdf.inputs[socket].default_value = value
    return mat
