"""The road-surface stage: geometry, and the three documents that have to agree about friction.

``blender/roads/build_pavement.py`` is the first consumer of ``data/processed/roads/pavement`` that
is not the still-frame renderer, and the first thing in the project that puts a drivable surface in
front of the car.  What it ships has to be watertight, has to follow the ground it is draped on, and
has to name a surface class that means the same thing in Blender, in ``DefaultEngine.ini`` and in the
C++ tyre model -- three files that nothing had ever compared.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import numpy as np
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "blender" / "roads"))
sys.path.insert(0, str(REPO_ROOT / "pipeline"))

import pvlib  # noqa: E402

DEFAULT_ENGINE_INI = REPO_ROOT / "unreal" / "NYCSim" / "Config" / "DefaultEngine.ini"
DYNAMICS_H = (REPO_ROOT / "unreal" / "NYCSim" / "Source" / "NYCSimRuntime" / "Private"
              / "CoreAdapter" / "GameplayVehicleDynamics.h")


# --------------------------------------------------------------------------- geometry


def _edge_use(tris: np.ndarray) -> dict:
    use: dict = {}
    for a, b, c in tris:
        for p, q in ((a, b), (b, c), (c, a)):
            k = (min(int(p), int(q)), max(int(p), int(q)))
            use[k] = use.get(k, 0) + 1
    return use


def test_the_refined_surface_has_no_t_junctions():
    """Every interior edge is shared by exactly two triangles, every boundary edge by one.

    Longest-edge bisection that splits one triangle without splitting its neighbour leaves a vertex
    sitting in the middle of the neighbour's edge, and the crack that opens there is a line of
    background straight through the road.  The refinement marks edges globally, once, so the two
    triangles that share one are always split together; this is the assertion that keeps it that way.
    """
    verts = np.array([[0.0, 0.0], [100.0, 0.0], [0.0, 100.0]])
    tris = np.array([[0, 1, 2]])

    def bumpy(x, y):
        return 3.0 * np.sin(x / 12.0) * np.cos(y / 9.0)

    v, t = pvlib.refine_to_terrain(verts, tris, bumpy, tol_m=0.03, min_edge_m=0.5, max_edge_m=20.0)
    counts = sorted(set(_edge_use(t).values()))
    assert counts and max(counts) <= 2, f"an edge is shared by {max(counts)} triangles"
    assert len(t) > len(tris), "a 100 m triangle over a 3 m bumpy surface was not refined at all"


def test_the_refinement_conserves_the_plan_area_exactly():
    """Subdivision may not add or lose surface: a road that grew is a road in the wrong place."""
    verts = np.array([[0.0, 0.0], [60.0, 0.0], [60.0, 40.0], [0.0, 40.0]])
    tris = np.array([[0, 1, 2], [0, 2, 3]])
    v, t = pvlib.refine_to_terrain(verts, tris, lambda x, y: x * 0.02 + np.sin(y / 7.0),
                                   tol_m=0.02, min_edge_m=0.5, max_edge_m=15.0)
    area = sum(abs(np.cross(v[b] - v[a], v[c] - v[a])) / 2.0 for a, b, c in t)
    assert area == pytest.approx(60.0 * 40.0, rel=1e-9)


def test_the_refinement_actually_brings_the_surface_within_tolerance():
    """The criterion is the error, so the error is what the test measures.

    Refining to a fixed edge length would pass a shape test and still leave the road hanging: on the
    real data a 4 m cap cost 8.1 million triangles in one tile and the tail of the draping error was
    barely better than at 25 m.  What matters is the distance from the ground, sampled *inside* the
    triangles rather than at the corners the refinement is guaranteed to have got right.
    """
    def ground(x, y):
        return 2.5 * np.sin(np.asarray(x) / 18.0) + 1.5 * np.cos(np.asarray(y) / 23.0)

    verts = np.array([[0.0, 0.0], [80.0, 0.0], [80.0, 80.0], [0.0, 80.0]])
    tris = np.array([[0, 1, 2], [0, 2, 3]])
    tol = 0.05
    v, t = pvlib.refine_to_terrain(verts, tris, ground, tol_m=tol, min_edge_m=0.4, max_edge_m=25.0)
    z = ground(v[:, 0], v[:, 1])
    rng = np.random.default_rng(11)
    w = rng.random((len(t), 3))
    w /= w.sum(axis=1, keepdims=True)
    p = (v[t] * w[:, :, None]).sum(axis=1)
    mesh_z = (z[t] * w).sum(axis=1)
    err = np.abs(mesh_z - ground(p[:, 0], p[:, 1]))
    coarse = np.abs(0.0 - ground(40.0, 40.0))
    assert np.percentile(err, 99) < 4.0 * tol, (
        f"99th percentile draping error {np.percentile(err, 99):.3f} m against a {tol} m tolerance")
    assert err.max() < coarse, "refinement did not improve on the unrefined surface at all"


def test_the_boundary_loops_are_the_real_boundary_and_wound_for_the_skirt():
    """A square with a square hole: two loops, the outer one counter-clockwise, the hole clockwise.

    The skirt is raised on these loops, and a wall's outward face is decided by the loop's winding.
    Get it backwards and every kerb in the city is inside-out -- invisible from the street, solid
    from underneath.
    """
    import mapbox_earcut as earcut

    outer = np.array([[0.0, 0.0], [10.0, 0.0], [10.0, 10.0], [0.0, 10.0]])
    hole = np.array([[4.0, 4.0], [4.0, 6.0], [6.0, 6.0], [6.0, 4.0]])   # clockwise
    pts = np.vstack([outer, hole])
    tris = earcut.triangulate_float64(pts, np.array([4, 8])).reshape(-1, 3)
    loops = pvlib.boundary_loops(tris)
    assert len(loops) == 2, f"expected an outer loop and a hole, got {len(loops)}"

    def signed_area(loop):
        c = pts[loop]
        return float(np.dot(c[:, 0], np.roll(c[:, 1], -1)) - np.dot(c[:, 1], np.roll(c[:, 0], -1))) / 2.0

    areas = sorted(signed_area(loop) for loop in loops)
    assert areas[0] < 0.0 < areas[1], f"loop windings are {areas}, expected one of each sign"
    assert abs(areas[1]) == pytest.approx(100.0), "the outer loop is not the outline"
    assert abs(areas[0]) == pytest.approx(4.0), "the inner loop is not the hole"


def test_the_curb_reveal_is_the_real_fifteen_centimetres():
    """Roadbed +0.10, everything walked on +0.25: the step between them is New York's kerb."""
    roadbed = pvlib.PAVEMENT_KINDS[0][1]
    for kind in (1, 2, 3, 4):
        assert pvlib.PAVEMENT_KINDS[kind][1] - roadbed == pytest.approx(0.15), (
            f"kind {kind} ({pvlib.PAVEMENT_KINDS[kind][0]}) sits "
            f"{pvlib.PAVEMENT_KINDS[kind][1] - roadbed:.3f} m above the roadbed, not 0.15")
    crosswalk = pvlib.PAVEMENT_KINDS[5][1] - roadbed
    assert 0.005 <= crosswalk <= 0.03, (
        f"the crosswalk stands {crosswalk * 1000:.0f} mm proud of the roadbed; thermoplastic is "
        f"a few millimetres, and anything a car can feel is wrong")


def test_the_curb_carries_a_skirt_deep_enough_to_reach_the_roadbed():
    """The kerb's vertical face is the point of the skirt, so it has to span the reveal."""
    reveal = pvlib.PAVEMENT_KINDS[4][1] - pvlib.PAVEMENT_KINDS[0][1]
    assert pvlib.PAVEMENT_KINDS[4][2] > reveal, (
        f"the kerb's skirt is {pvlib.PAVEMENT_KINDS[4][2]:.2f} m against a {reveal:.2f} m reveal, so "
        f"its face stops short of the road and daylight shows under it")


# --------------------------------------------------------------------------- the friction contract


def _engine_surface_classes() -> dict[int, str]:
    """``SurfaceClass`` from ``GameplayVehicleDynamics.h``, by declared value."""
    text = DYNAMICS_H.read_text(encoding="utf-8", errors="replace")
    body = re.search(r"enum class SurfaceClass\s*:\s*\w+\s*\{(.*?)\}", text, re.S)
    assert body is not None, "SurfaceClass enum not found"
    out: dict[int, str] = {}
    nxt = 0
    for name, value in re.findall(r"(\w+)\s*(?:=\s*(\d+))?\s*,", body.group(1)):
        if name == "Count":
            continue
        nxt = int(value) if value else nxt
        out[nxt] = name
        nxt += 1
    return out


def _ini_physical_surfaces() -> dict[int, str]:
    """``SurfaceTypeN=Name`` from ``DefaultEngine.ini``."""
    text = DEFAULT_ENGINE_INI.read_text(encoding="utf-8", errors="replace")
    return {int(n): name for n, name in
            re.findall(r"\+PhysicalSurfaces=\(Type=SurfaceType(\d+),Name=(\w+)\)", text)}


def test_the_engine_config_and_the_tyre_model_agree_about_every_surface():
    """``EPhysicalSurface`` index N must be the surface ``SurfaceClass`` N names.

    ``UNYCVehicleMovementComponent::ToSurfaceClass`` casts the ``EPhysicalSurface`` index straight to
    a ``SurfaceClass`` with a range check and no table.  So the two lists are a single implicit
    contract held in two files, and one insertion in either would silently give every cobblestone
    street steel-plate grip.
    """
    enum = _engine_surface_classes()
    ini = _ini_physical_surfaces()
    assert ini, "DefaultEngine.ini declares no PhysicalSurfaces"
    mismatched = {n: (enum.get(n), name) for n, name in ini.items() if enum.get(n) != name}
    assert not mismatched, (
        f"EPhysicalSurface and SurfaceClass disagree at {sorted(mismatched)}: "
        + ", ".join(f"SurfaceType{n} is {name!r} in {DEFAULT_ENGINE_INI.name} but "
                    f"{have!r} in {DYNAMICS_H.name}" for n, (have, name) in sorted(mismatched.items())))


def test_every_surface_the_pavement_stage_emits_is_a_class_the_tyre_model_knows():
    """A pavement mesh that names a class outside the enum is a wheel contact that falls back to
    ``Default`` -- which is dry asphalt, in the rain, on cobblestones."""
    enum = _engine_surface_classes()
    for kind in pvlib.PAVEMENT_KINDS:
        for surface in pvlib.SURFACE_NAMES:
            cls = pvlib.surface_class(kind, surface)
            assert cls in enum, (
                f"kind {kind} on surface {surface} maps to SurfaceClass {cls}, which "
                f"{DYNAMICS_H.name} does not declare")
            assert pvlib.SURFACE_CLASS_NAMES.get(cls) == enum[cls], (
                f"SurfaceClass {cls} is {enum[cls]!r} in the engine but "
                f"{pvlib.SURFACE_CLASS_NAMES.get(cls)!r} in pvlib")


def test_the_two_kinds_that_override_their_material_do_it_for_a_reason():
    """A sidewalk is not simply concrete and a crosswalk is not simply asphalt."""
    assert pvlib.surface_class(1, 1) == 9, "a concrete sidewalk must resolve to Sidewalk, not Concrete"
    assert pvlib.surface_class(5, 0) == 5, "an asphalt crosswalk must resolve to PaintedMarking"
    assert pvlib.surface_class(0, 1) == 2, "a concrete roadbed is concrete"
    assert pvlib.surface_class(0, 2) == 3, "a cobbled roadbed is cobble"


def test_the_manifest_routes_pavement_to_its_own_import_settings():
    """Without a rule of its own, ``tile_pavement.glb`` would fall into the generic tile rule and
    import as a building shell: no physical materials, so no friction."""
    from nycsim_pipeline.unreal.manifest import GLB_RULES, IMPORT_SETTINGS

    rel = "tiles/t_-4_4/tile_pavement.glb"
    rule = next(((rx, s, tpl, kind) for rx, s, tpl, kind in GLB_RULES if rx.match(rel)), None)
    assert rule is not None, "no import rule matches tile_pavement.glb"
    _rx, settings, tpl, kind = rule
    assert kind == "pavement", f"tile_pavement.glb is imported as {kind!r}"
    assert settings == "pavement_nanite", f"tile_pavement.glb uses the {settings!r} profile"
    profile = IMPORT_SETTINGS[settings]
    assert profile.get("physical_materials") is True, (
        "the pavement profile does not ask for physical materials, so every wheel contact in the "
        "city resolves to SurfaceClass::Default")
    assert profile.get("collision") == "complex_as_simple", (
        "the wheels line-trace against the road triangles; a simplified hull is not a road")
    assert "SM_Pavement" in tpl, f"unexpected content path template {tpl!r}"
