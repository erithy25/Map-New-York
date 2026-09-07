"""Shell material definitions for the building stage (no ``bpy`` at import time).

The shells shipped one flat colour, one roughness and one metallic value per material class.  That
is what made the Lower Manhattan skyline render as "flat pastel solids: pale pink, pale blue,
white" in the comparison lane's Brooklyn Heights Promenade assessment, against a photograph whose
towers are "dark glass with strong vertical banding and a wide tonal range from near-black to
specular white".  Two of the three missing pieces are authored here.

**Reflectance.**  A curtain-wall tower is dark and mirror-like: nearly everything the eye sees on it
is a reflection of the sky above and of the tower opposite, which is where the near-black to
specular-white range comes from.  A 4 % Fresnel dielectric at roughness 0.12 cannot produce that.
Each class now carries the full analytic set — base colour, roughness, metallic, specular level,
IOR — and glass is authored dark, sharp and part-metallic.  These are *shading* choices, not
measurements: no reflectance was measured for any NYC building, and which class a building is
assigned is governed by ADR-004 and flagged by the ``MATERIAL_REAL`` fidelity bit.

**Per-building variation.**  One colour per class makes a block of brownstones a single flat wall.
``lit_seed`` (DATA_CONTRACTS §5.2) exists so per-building variation can be deterministic, and
:func:`variation` turns it into a signed offset in [-1, 1] that :func:`shaded` applies to the base
colour and the roughness.  The formula is deliberately shader-shaped — two multiplies, a sine and a
fract — so the Unreal master material and the Cycles verification shader can both evaluate it from
the ``_LIT_SEED_HI`` / ``_LIT_SEED_LO`` vertex attributes the shells already carry.  **It costs no
bytes and no draw calls**: the alternative, a per-vertex ``COLOR_0``, measured +23 % on the tile
file (Blender writes vertex colour as float32 VEC3), and splitting a class into tone materials
would break the "one mesh per (tile, material class)" rule of ARCHITECTURE §4.3.  The consequence
is that the variation lives in the *shader*, so a consumer that renders the glTF material as-is
sees the class colour without it; ``blender/buildings/render_verify.py`` implements it.

The third missing piece, the spandrel band at each floor line, is **not** delivered: it needs
either a shader (the shell already carries what one would need — metre UVs with ``v`` = height
above grade, plus ``_FLOOR_HEIGHT`` and ``_GROUND_FLOOR_HEIGHT`` per vertex) or geometry the disk
budget will not pay for.  See :func:`floor_band_uv` for the exact expression an engine should use.

Nothing here is texture-mapped: analytic materials only, following the vehicles lane
(``docs/verification/vehicles/REPORT.md`` §6.2), so none of it costs disk.
"""
from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class ShellMaterial:
    """One material class as the shell renders it."""

    base_color: tuple[float, float, float]
    roughness: float = 0.72
    metallic: float = 0.0
    #: Principled "Specular IOR Level" — 0.5 is the 4 % dielectric default, higher is glossier.
    specular: float = 0.5
    ior: float = 1.45
    #: peak relative brightness offset per building (0.12 = +-12 %)
    tone_amp: float = 0.0
    #: peak roughness offset per building, absolute
    rough_amp: float = 0.0


# Masonry and stone vary building to building far more than they vary within a class, so they carry
# the largest tone amplitude.  Glass varies mostly in *roughness* — the difference between a 1960s
# tower and a 2010s one is how sharp its reflection is — so its colour amplitude is small and its
# roughness amplitude is not.
MATERIALS: dict[str, ShellMaterial] = {
    "red_brick":          ShellMaterial((0.42, 0.16, 0.12), 0.78, 0.0, 0.42, 1.45, 0.14, 0.06),
    "brown_brick":        ShellMaterial((0.31, 0.20, 0.15), 0.78, 0.0, 0.42, 1.45, 0.14, 0.06),
    "tan_brick":          ShellMaterial((0.62, 0.51, 0.37), 0.76, 0.0, 0.42, 1.45, 0.12, 0.06),
    "white_glazed_brick": ShellMaterial((0.80, 0.79, 0.74), 0.45, 0.0, 0.60, 1.50, 0.07, 0.06),
    "brownstone":         ShellMaterial((0.34, 0.22, 0.15), 0.80, 0.0, 0.40, 1.45, 0.14, 0.05),
    "limestone":          ShellMaterial((0.72, 0.68, 0.58), 0.66, 0.0, 0.45, 1.48, 0.09, 0.05),
    "terracotta":         ShellMaterial((0.60, 0.33, 0.22), 0.62, 0.0, 0.50, 1.48, 0.12, 0.05),
    "cast_iron":          ShellMaterial((0.16, 0.17, 0.17), 0.42, 0.85, 0.55, 2.20, 0.07, 0.06),
    # dark, sharp and part-metallic: the sky and the tower opposite are most of what is seen on it
    "glass_curtain":      ShellMaterial((0.085, 0.105, 0.125), 0.075, 0.55, 0.85, 1.52, 0.06, 0.05),
    "concrete":           ShellMaterial((0.55, 0.54, 0.51), 0.80, 0.0, 0.38, 1.45, 0.10, 0.05),
    "stucco":             ShellMaterial((0.72, 0.68, 0.60), 0.84, 0.0, 0.34, 1.45, 0.10, 0.05),
    "vinyl_siding":       ShellMaterial((0.70, 0.70, 0.66), 0.58, 0.0, 0.48, 1.47, 0.11, 0.05),
    "wood_clapboard":     ShellMaterial((0.60, 0.56, 0.48), 0.70, 0.0, 0.40, 1.45, 0.13, 0.05),
    "stone_rubble":       ShellMaterial((0.45, 0.43, 0.39), 0.86, 0.0, 0.34, 1.45, 0.11, 0.05),
    "metal_panel":        ShellMaterial((0.48, 0.50, 0.52), 0.32, 0.80, 0.60, 2.00, 0.08, 0.06),
    "granite":            ShellMaterial((0.40, 0.39, 0.38), 0.38, 0.0, 0.60, 1.55, 0.09, 0.06),
    "precast":            ShellMaterial((0.63, 0.62, 0.59), 0.74, 0.0, 0.40, 1.45, 0.09, 0.05),
    "roof_membrane":      ShellMaterial((0.30, 0.30, 0.31), 0.86, 0.0, 0.32, 1.45, 0.07, 0.04),
    "tar_roof":           ShellMaterial((0.13, 0.13, 0.13), 0.90, 0.0, 0.28, 1.45, 0.06, 0.03),
    "corrugated_metal":   ShellMaterial((0.45, 0.46, 0.47), 0.44, 0.80, 0.55, 2.00, 0.08, 0.06),
}

DEFAULT = ShellMaterial((0.60, 0.60, 0.60), 0.72, 0.0, 0.50, 1.45, 0.07, 0.04)

#: The hash constants, named once so the engine and the renderer cannot drift apart.
VAR_A, VAR_B, VAR_C = 12.9898, 78.233, 43758.5453


def spec(name: str) -> ShellMaterial:
    return MATERIALS.get(name, DEFAULT)


def variation(lit_seed_hi: float, lit_seed_lo: float) -> float:
    """Per-building offset in [-1, 1] from the two exported halves of ``lit_seed``.

    ``fract(sin(hi*A + lo*B) * C) * 2 - 1`` — the standard GPU value hash, evaluated on the halves
    rather than on ``lit_seed`` itself because ``lit_seed`` is a uint32 and does not survive float32
    (which is exactly why the shells ship it in halves at all).
    """
    s = math.sin(float(lit_seed_hi) * VAR_A + float(lit_seed_lo) * VAR_B) * VAR_C
    return (s - math.floor(s)) * 2.0 - 1.0


def shaded(name: str, k: float) -> tuple[tuple[float, float, float], float]:
    """``(base_color, roughness)`` for one building, given its :func:`variation` value ``k``."""
    m = spec(name)
    scale = 1.0 + m.tone_amp * k
    col = tuple(min(1.0, max(0.0, c * scale)) for c in m.base_color)
    rough = min(1.0, max(0.015, m.roughness + m.rough_amp * k))
    return col, rough  # type: ignore[return-value]


def floor_band_uv(v_m: float, ground_floor_height: float, floor_height: float,
                  band_m: float = 0.9) -> float:
    """1 inside the spandrel band of the floor containing height ``v_m``, else 0.

    Not applied by any shipped material — it is the expression an engine master material should use
    to put the dark spandrel band on a curtain wall, written here so the shell's UV and attribute
    contract has one authoritative reading.  ``v_m`` is the shell's metre UV ``v`` (height above
    ``ground_z``); the band sits at the bottom of each floor.
    """
    fh = max(float(floor_height), 0.1)
    above = float(v_m) - float(ground_floor_height)
    if above < 0.0:
        return 0.0
    return 1.0 if (above % fh) < min(band_m, fh * 0.5) else 0.0


def build_bpy_material(name: str, k: float = 0.0):
    """Create (or fetch) the flat Blender material for one class, at variation ``k``."""
    import bpy

    bname = f"NYCSIM_{name}" if k == 0.0 else f"NYCSIM_{name}_k{k:+.3f}"
    mat = bpy.data.materials.get(bname)
    if mat is not None:
        return mat
    col, rough = shaded(name, k)
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
