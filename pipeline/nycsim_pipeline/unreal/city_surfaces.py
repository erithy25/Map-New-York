"""What the engine has to know to draw the city's own surfaces, and what it deliberately may not.

The exported city -- 2,840 tile ``.glb`` files -- names its materials and carries no images.  That
is on purpose and it is half a contract: the file says ``NYCSIM_red_brick`` and the *consumer*
resolves the name.  The comparison renderer has held up its half since J63 and dresses each slot
from ``blender/common/texture_catalog.json``.  **Unreal has never held up its half**: no material
instance anywhere in ``unreal/`` names ``red_brick`` or any other surface, and the manifest carried
no texture entry at all, so a player saw nineteen solid RGB values where the sheets show brick,
limestone and asphalt (docs/DEVIATIONS.md J63, engine half).

This module computes the contract once, from the same sources the renderer uses, so the two cannot
drift:

* the **names** are read out of every exported tile rather than listed by hand.  A list was tried
  and was wrong: written from one tile it held sixteen of the nineteen, and the trim tool that
  believed it deleted ``precast`` (396 tiles), ``stucco`` (156) and ``vinyl_siding`` -- 1,086 tiles,
  the third most common surface in the city.  A list of names is a claim about 2,840 files.
* the **level** is ``shellmat``'s authored albedo, and the scale that takes a scan to it is the same
  arithmetic ``blender/verify/scene.py::_normalise_albedo`` publishes on every sheet, capped the
  same way at 4.0 with the residual stated rather than hidden (J66).
* the **tiling** is the catalogue's measured ``physical_size_m`` and the colour map's own pixel
  aspect, because three of these scans are 2:1 and tiling one as if it were square draws its
  content at twice its height (J73).

And it carries the **absences**.  Six pavement names, eight structure names and eleven park names
resolve to no surface, each for a stated reason -- there is no cobble in the catalogue, a lane
marking is paint rather than the asphalt under it, and nothing in this build says what a seawall is
clad in.  Shipping those as "unknown" rather than omitting them is the point: an engine that quietly
gave a pier deck the nearest concrete would be inventing a survey.
"""
from __future__ import annotations

import json
import struct
import importlib.util
import sys
from pathlib import Path
from typing import Any

#: The correction from a scan's own exposure to the albedo the material's stage authored is capped
#: here, and the residual is published.  Two stops: past that the scan is a different *material*
#: rather than a different exposure, and multiplying an sRGB image by fourteen bleaches out the
#: grain it was fetched for.  Same constant as ``blender/verify/scene.py::ALBEDO_SCALE_CAP``; the
#: test holds the two together.
ALBEDO_SCALE_CAP = 4.0

#: Maps the engine is given.  ``ao`` is baked into the colour at export and ``displacement`` would
#: subdivide a million-triangle shell, so neither travels -- the same four the renderer loads.
#: ``metalness`` is the catalogue's own key for it; the engine parameter is called Metallic.
CITY_MAPS = ("color", "roughness", "normal", "metalness")

#: Albedo the road surfaces are normalised to.  ``shellmat`` knows the shell classes and returns a
#: 0.6 grey DEFAULT for anything else, so asking it about asphalt would brighten the road six-fold.
#: These are ``PAVEMENT_KINDS``' own numbers, and they are the same two the renderer uses (J66).
PAVEMENT_ALBEDO: dict[str, tuple[float, float, float]] = {
    "asphalt": (0.055, 0.055, 0.058),
    "concrete_sidewalk": (0.34, 0.335, 0.32),
}

#: Exported pavement material name -> the catalogue surface it is drawn with.  Copied deliberately
#: rather than derived from the suffix, because the suffix is actively wrong twice:
#: ``pave_marking_white_asphalt`` and ``pave_marking_yellow_asphalt`` are **paint**, and giving them
#: the asphalt they are painted on would erase every lane line and stop bar in the city (J52).
PAVEMENT_SURFACE: dict[str, str] = {
    "pave_roadbed_asphalt": "asphalt",
    "pave_crosswalk_asphalt": "asphalt",
    "pave_parking_lot_asphalt": "asphalt",
    "pave_roadbed_concrete": "concrete",
    "pave_sidewalk_concrete": "concrete_sidewalk",
    "pave_median_concrete": "concrete_sidewalk",
    "pave_plaza_concrete": "concrete_sidewalk",
    "pave_curb_concrete": "concrete_sidewalk",
    "pave_curb_ramp_concrete": "concrete_sidewalk",
}

#: Every other exported material name, and why it is given no surface.  These are shipped as
#: refusals rather than left out: an engine that guessed would be inventing a survey.
UNRESOLVED_REASON: dict[str, str] = {
    "pave_marking_white_asphalt": "paint, not the asphalt under it; giving it a surface would erase every lane line (J52)",
    "pave_marking_yellow_asphalt": "paint, not the asphalt under it; giving it a surface would erase every centre line (J52)",
    "pave_roadbed_cobble": "the catalogue holds no cobble, and the nearest brick is not it",
    "pave_roadbed_gravel": "the catalogue holds no gravel roadbed",
    "pave_roadbed_steel": "a steel plate roadbed; the catalogue's metal is a panel, not a plate",
    "struct_el_steel": "nothing in this build says what the elevated structure is finished in",
    "struct_seawall": "nothing in this build says what a seawall is clad in, and choosing would be invention",
    "struct_pier_deck": "nothing in this build says what a pier deck is decked in",
    "struct_pier_pile": "nothing in this build says what a pier pile is",
    "struct_canopy": "nothing in this build says what a platform canopy is roofed in",
    "struct_platform": "nothing in this build says what a station platform is surfaced in",
    "struct_jetty": "nothing in this build says what a jetty is built of",
    "struct_station_house": "nothing in this build says what a station house is clad in",
    "struct_viaduct_concrete": "a concrete viaduct; no survey says which concrete, and the shell classes are buildings",
    "park_recreation_grass": "park surfaces are an open gap in their own right (docs/DEVIATIONS.md J40)",
    "park_park_ground_grass": "park surfaces are an open gap in their own right (J40)",
    "park_greenstreet_grass": "park surfaces are an open gap in their own right (J40)",
    "park_cemetery_grass": "park surfaces are an open gap in their own right (J40)",
    "park_grass_field_grass": "park surfaces are an open gap in their own right (J40)",
    "park_vacant_bare": "park surfaces are an open gap in their own right (J40)",
    "park_court_sport_hard": "a sport court's acrylic is not in the catalogue (J40)",
    "park_ballfield_ball_dirt": "infield dirt is not in the catalogue (J40)",
    "park_pool_water": "pool water is drawn by the water material, not a surface texture",
    "park_skating_rink_ice": "rink ice is drawn by the water material, not a surface texture",
    "park_track_track": "a running track's surfacing is not in the catalogue (J40)",
}

#: Surfaces that resolve a name and are still drawn analytically on purpose.  Glass is the whole
#: list: a photograph of a curtain wall is a photograph of what it reflects.
ANALYTIC = {"glass_curtain"}


def tile_material_names(tiles_root: Path) -> dict[str, int]:
    """Every material name in every exported tile, with how many slots carry it.

    Read from the files rather than listed, for the reason the module docstring gives.  The glTF
    JSON chunk is parsed directly: opening 2,840 files through a glTF library costs minutes and
    the only thing wanted here is ``materials[].name``.
    """
    out: dict[str, int] = {}
    if not tiles_root.is_dir():
        return out
    for g in sorted(tiles_root.glob("**/*.glb")):
        if "_merged" in str(g):
            continue                     # the distant skyline re-uses the same names
        try:
            with g.open("rb") as f:
                if f.read(4) != b"glTF":
                    continue
                struct.unpack("<II", f.read(8))
                length, _ = struct.unpack("<II", f.read(8))
                doc = json.loads(f.read(length))
        except (OSError, ValueError, struct.error):
            continue
        for m in doc.get("materials", []):
            n = str(m.get("name") or "")
            if n:
                out[n] = out.get(n, 0) + 1
    return out


def texture_albedo(path: Path) -> float | None:
    """Mean **linear-light** value of a colour map, or None if it cannot be read.

    The same measurement ``blender/verify/scene.py::_texture_albedo`` takes, down to the 256 px
    thumbnail, so the scale this module publishes is the scale the sheets show.
    """
    try:
        import numpy as np
        from PIL import Image
    except ImportError:                                    # pragma: no cover
        return None
    try:
        im = Image.open(path).convert("RGB")
    except (OSError, ValueError):
        return None
    im.thumbnail((256, 256))
    a = np.asarray(im, dtype=np.float64) / 255.0
    lin = np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)
    return float(lin.mean())


def image_aspect(path: Path) -> float | None:
    """``width / height`` of a colour map. Three of these scans are 2:1 (J73)."""
    try:
        from PIL import Image
    except ImportError:                                    # pragma: no cover
        return None
    try:
        with Image.open(path) as im:
            w, h = im.size
    except (OSError, ValueError):
        return None
    return (w / h) if w and h else None


def albedo_correction(have: float | None, target_rgb) -> dict[str, Any] | None:
    """The scalar that takes a scan's own level to the one its stage authored, and what it cost.

    Scalar and not per-channel, deliberately: a per-channel correction forces the scan's hue to the
    class hue and throws away the one thing about colour a photograph does measure (J66).
    """
    if not have or have <= 1e-6:
        return None
    want = float(sum(target_rgb[:3])) / 3.0
    k = want / have
    capped = False
    if k > ALBEDO_SCALE_CAP:
        k, capped = ALBEDO_SCALE_CAP, True
    elif k < 1.0 / ALBEDO_SCALE_CAP:
        k, capped = 1.0 / ALBEDO_SCALE_CAP, True
    if abs(k - 1.0) < 0.02:
        return {"texture_albedo": round(have, 4), "target_albedo": round(want, 4), "scale": 1.0}
    out: dict[str, Any] = {"texture_albedo": round(have, 4), "target_albedo": round(want, 4),
                           "scale": round(k, 3)}
    if capped:
        out["capped_at"] = ALBEDO_SCALE_CAP
        out["residual"] = round(want / (have * k), 3)
        out["note"] = ("the catalogue's texture for this class is the wrong material, not the wrong "
                       "exposure; the level is corrected as far as it can be without destroying "
                       "the grain and the remaining factor is stated")
    return out


def _load_from_root(repo_root: Path, relative: str, module: str):
    """Import ``blender/<relative>/<module>.py`` from *this* root, not from whichever is loaded.

    These two modules used to be brought in with ``sys.path.insert`` and a bare ``import``.  That
    reads the *name* from ``sys.modules``, so once any root had been loaded every later call got
    that one back and ``repo_root`` was silently ignored: a manifest generated over a temporary
    tree came out carrying absolute texture paths from the real repository, ten entries where the
    tree held one.  Found by bisecting a test that failed only when it ran after the Blender scene
    tests.  Loading by file location under a root-qualified name gives one module object per root
    and claims no global name.
    """
    path = repo_root / "blender" / relative / f"{module}.py"
    if not path.is_file():
        raise FileNotFoundError(f"{module}.py not found under {repo_root}")
    key = f"_nycsim_city_surfaces.{abs(hash(str(repo_root.resolve())))}.{module}"
    cached = sys.modules.get(key)
    if cached is not None:
        return cached
    spec = importlib.util.spec_from_file_location(key, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    loaded = importlib.util.module_from_spec(spec)
    # Its own siblings are imported by bare name, so the directory still has to be reachable.
    sibling = str(path.parent)
    if sibling not in sys.path:
        sys.path.insert(0, sibling)
    sys.modules[key] = loaded
    try:
        spec.loader.exec_module(loaded)
    except BaseException:
        sys.modules.pop(key, None)
        raise
    return loaded


def _shellmat(repo_root: Path):
    """``blender/buildings/shellmat.py``, which imports no ``bpy`` at module level and says so."""
    return _load_from_root(repo_root, "buildings", "shellmat")


def _textures(repo_root: Path):
    """``blender/common/textures.py``: the catalogue, its aliases and the files on disk."""
    return _load_from_root(repo_root, "common", "textures")


def build(repo_root: Path, tiles_root: Path, *, resolution: str = "2K",
          surface_class: dict[str, int] | None = None) -> dict[str, Any]:
    """The whole contract: one entry per surface, one binding per exported material name.

    Returns the block the manifest publishes as ``city_surfaces``.  Nothing here reads Unreal or
    Blender; it is the same arithmetic over the same files, so a test can hold it against what the
    render records already publish.
    """
    shellmat = _shellmat(repo_root)
    tx = _textures(repo_root)
    names = tile_material_names(tiles_root)

    shells = sorted(n[len("NYCSIM_"):] for n in names if n.startswith("NYCSIM_"))
    wanted = list(dict.fromkeys(shells + sorted(set(PAVEMENT_SURFACE.values()))))

    surfaces: dict[str, Any] = {}
    for name in wanted:
        entry: dict[str, Any] = {
            "slots_in_tiles": names.get(f"NYCSIM_{name}", 0),
            "drawn_by": "the class's own analytic shading" if name in ANALYTIC else "a photographic scan",
        }
        if name in ANALYTIC:
            entry["analytic_reason"] = ("a photograph of a curtain wall is a photograph of what it "
                                        "reflects; this surface is shaded and not textured, here "
                                        "and in the renders")
        spec = shellmat.spec(name)
        entry["shading"] = {
            "base_color": [round(float(c), 4) for c in spec.base_color],
            "roughness": round(float(spec.roughness), 3),
            "metallic": round(float(spec.metallic), 3),
            "specular": round(float(spec.specular), 3),
            "ior": round(float(spec.ior), 3),
            "tone_amp": round(float(spec.tone_amp), 3),
            "rough_amp": round(float(spec.rough_amp), 3),
        }
        try:
            cat = tx.resolve(name)
        except Exception as exc:                            # noqa: BLE001 - a name with no catalogue entry
            entry["textured"] = False
            entry["reason"] = f"not in blender/common/texture_catalog.json ({exc})"
            surfaces[name] = entry
            continue
        entry["asset_id"] = cat.get("asset_id")
        entry["physical_size_m"] = cat.get("physical_size_m")
        entry["physical_size_source"] = cat.get("physical_size_source")
        if name in ANALYTIC:
            entry["textured"] = False
            surfaces[name] = entry
            continue
        # ``_existing_set`` and not ``get_texture_set``: the latter *downloads* a missing set, and
        # a manifest run must not reach the network or spend disk.  A surface whose files are not
        # on disk is reported as untextured with the command that fetches it.
        have = tx._existing_set(cat["asset_id"], resolution) or {}
        maps = {m: str(Path(have[m]).resolve()) for m in CITY_MAPS
                if have.get(m) and Path(have[m]).is_file()}
        entry["maps"] = {k: v for k, v in maps.items()}
        if "color" not in maps:
            entry["textured"] = False
            entry["reason"] = (f"no colour map on disk at {resolution}; re-fetch with "
                               f"`python3 blender/common/textures.py --fetch {name}`")
            surfaces[name] = entry
            continue
        entry["textured"] = True
        colour = Path(maps["color"])
        entry["tile_aspect"] = image_aspect(colour)
        target = PAVEMENT_ALBEDO.get(name) or spec.base_color
        entry["albedo_target_from"] = ("PAVEMENT_KINDS" if name in PAVEMENT_ALBEDO
                                       else "shellmat.spec")
        alb = albedo_correction(texture_albedo(colour), target)
        if alb is not None:
            entry["albedo"] = alb
        surfaces[name] = entry

    # An instance is keyed on the (surface, surface class) *pair*, not on the surface alone, and
    # that is not a detail.  Five pavement names resolve to ``concrete_sidewalk`` and they do not
    # share a surface class: a curb ramp and a sidewalk are class 9, a median, a plaza and a curb
    # are class 2.  A single shared instance carries one ``phys_material``, so it would have given
    # one of those two groups the other's tyre friction -- every curb ramp in the city gripping
    # like a median, or the reverse.  The visual parameters come from the surface and the physics
    # from the class, so the instance is the pair of them.
    bindings: dict[str, Any] = {}
    for n, count in sorted(names.items()):
        if n.startswith("NYCSIM_"):
            surface = n[len("NYCSIM_"):]
            bindings[n] = {"surface": surface, "slots": count,
                           "instance": f"MI_NYC_{surface}", "surface_class": None}
        elif n in PAVEMENT_SURFACE:
            surface = PAVEMENT_SURFACE[n]
            sc = surface_class.get(n) if surface_class else None
            bindings[n] = {"surface": surface, "slots": count, "surface_class": sc,
                           "instance": (f"MI_NYC_{surface}" if sc is None
                                        else f"MI_NYC_{surface}_sc{sc}")}
        else:
            bindings[n] = {"surface": None, "slots": count, "instance": None,
                           "reason": UNRESOLVED_REASON.get(n, "no surface is claimed for this name")}

    # One instance per distinct binding, so the engine builds exactly what the tiles ask for.
    instances: dict[str, Any] = {}
    for n, bnd in bindings.items():
        inst = bnd.get("instance")
        if not inst:
            continue
        rec = instances.setdefault(inst, {"surface": bnd["surface"],
                                          "surface_class": bnd.get("surface_class"),
                                          "from_material_names": [], "slots": 0})
        rec["from_material_names"].append(n)
        rec["slots"] += bnd["slots"]
    for rec in instances.values():
        rec["from_material_names"].sort()

    textured = sorted(k for k, v in surfaces.items() if v.get("textured"))
    return {
        "schema_version": 1,
        "material_master": "M_NYC_Master",
        "instance_prefix": "MI_NYC_",
        "resolution": resolution,
        "uv_note": ("shell UVs are metres -- U is arc length along the facade, V is height above "
                    "ground -- and pavement UVs are metres planar in NYC_TM, so a surface tiles at "
                    "1/physical_size_m along U and 1/(physical_size_m * tile_aspect) along V"),
        "albedo_note": ("scale multiplies the sampled colour so its mean linear albedo is the one "
                        "the surface's own stage authored; where capped_at is present the scan is "
                        "the wrong material rather than the wrong exposure and residual states what "
                        "is left (J66)"),
        "instance_note": ("an instance is keyed on the (surface, surface class) pair: five "
                          "pavement names resolve to concrete_sidewalk and they do not share a "
                          "surface class, so one shared instance would give a curb ramp a median's "
                          "tyre friction"),
        "surfaces": surfaces,
        "slot_bindings": bindings,
        "instances": instances,
        "counts": {
            "material_names_in_tiles": len(names),
            "surfaces": len(surfaces),
            "textured": len(textured),
            "analytic": len([k for k in surfaces if k in ANALYTIC]),
            "instances": len(instances),
            "bound_slots": sum(v["slots"] for v in bindings.values() if v.get("surface")),
            "unbound_slots": sum(v["slots"] for v in bindings.values() if not v.get("surface")),
        },
    }
