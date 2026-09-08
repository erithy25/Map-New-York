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


# --------------------------------------------------------------------------- triangulation quality


def test_the_grid_triangulation_produces_usable_triangles_and_not_slivers():
    """The measurement that replaced ear clipping.

    Ear clipping a planimetric road polygon is correct and fast and gives long thin triangles that no
    subsequent refinement repairs. On the largest roadbed polygon of one Lower Manhattan tile --
    11,446 m2, 2,195 m of perimeter -- it produced 133,004 triangles of which 97.4 % had a shape
    quality below 0.1, a median quality of 0.001 and a smallest edge of 0.0000 m. Cutting on a grid
    gives 5,050 triangles at a median quality of 0.866.

    Quality here is ``4*sqrt(3)*area / sum(edge^2)``: 1 for an equilateral triangle, 0 for a sliver.
    """
    import shapely

    # A ribbon 8 m wide and 600 m long with a kink: the shape that breaks ear clipping.
    line = shapely.LineString([(0.0, 0.0), (300.0, 12.0), (600.0, 0.0)])
    poly = line.buffer(4.0, cap_style="flat")
    verts, tris = pvlib.grid_triangulate(poly, 2.5)
    assert len(tris) > 0

    a = np.abs(np.cross(verts[tris[:, 1]] - verts[tris[:, 0]],
                        verts[tris[:, 2]] - verts[tris[:, 0]])) / 2.0
    e = np.stack([np.linalg.norm(verts[tris[:, 1]] - verts[tris[:, 0]], axis=1),
                  np.linalg.norm(verts[tris[:, 2]] - verts[tris[:, 1]], axis=1),
                  np.linalg.norm(verts[tris[:, 0]] - verts[tris[:, 2]], axis=1)], axis=1)
    quality = 4.0 * np.sqrt(3.0) * a / np.maximum((e ** 2).sum(axis=1), 1e-12)

    assert a.sum() == pytest.approx(poly.area, rel=1e-6), "the grid cut lost or added surface"
    assert np.median(quality) > 0.5, (
        f"median triangle quality {np.median(quality):.3f}; the grid cut is producing slivers")
    assert float((quality < 0.1).mean()) < 0.25, (
        f"{100 * float((quality < 0.1).mean()):.0f}% of the triangles are slivers")
    # Roughly area / cell^2 triangles, not the ear-clipper's arbitrary count.
    assert len(tris) < 6.0 * poly.area / (2.5 ** 2), f"{len(tris)} triangles for {poly.area:.0f} m2"


def test_the_grid_cut_keeps_the_polygon_boundary_exactly():
    """Every piece is an intersection with the original, so the union is the original."""
    import shapely

    poly = shapely.Polygon([(0.0, 0.0), (37.3, 0.0), (37.3, 19.1), (18.0, 26.0), (0.0, 19.1)],
                           [[(8.0, 6.0), (14.0, 6.0), (14.0, 12.0), (8.0, 12.0)]])
    verts, tris = pvlib.grid_triangulate(poly, 4.0)
    area = np.abs(np.cross(verts[tris[:, 1]] - verts[tris[:, 0]],
                           verts[tris[:, 2]] - verts[tris[:, 0]])).sum() / 2.0
    assert area == pytest.approx(poly.area, rel=1e-9), "the hole or the outline was not preserved"


def test_the_carriageway_takes_its_height_from_the_road_and_not_from_the_ground_under_it():
    """A planimetric roadbed polygon has no elevation, and the ground under a viaduct is not it.

    Over the paved area of one Lower Manhattan tile, 48.2 % sits on polygons spanning more than two
    metres of terrain -- against 3.0 % in Midtown -- with a maximum span of 12.6 m: the FDR Drive,
    the Battery Tunnel portals and the Brooklyn Bridge approaches drawn on the street below. The road
    network already carries a 3D centreline per segment and a z_source saying whether its elevation
    came from the terrain (0) or from a level or a ramp (1, 2).
    """
    segments = REPO_ROOT / "data" / "processed" / "roads" / "segments.parquet"
    if not segments.is_file():
        pytest.skip("no road segments in this checkout")
    surface = pvlib.RoadSurface(segments, (-4000.0, 0.0, -3000.0, 1000.0))
    if not surface.ok:
        pytest.skip(surface.reason)
    assert surface.lines, "no 3D centrelines were loaded"
    assert any(z != 0 for z in surface.z_source), (
        "no grade-separated segment near Lower Manhattan; the level information is missing")

    # The rule is narrow on purpose: an at-grade segment's z came from the terrain in the first
    # place, so using it there could only introduce a way to be wrong.
    import shapely

    at_grade = next((i for i, z in enumerate(surface.z_source) if z == 0), None)
    if at_grade is not None:
        poly = surface.lines[at_grade].buffer(3.0)
        assert surface.line_for(poly) is None, (
            "an at-grade road was treated as elevated; its height would move off the terrain that "
            "produced it")


def test_one_polygon_gets_one_centreline():
    """A per-point lookup tears the surface where two decks pass at different heights."""
    segments = REPO_ROOT / "data" / "processed" / "roads" / "segments.parquet"
    if not segments.is_file():
        pytest.skip("no road segments in this checkout")
    surface = pvlib.RoadSurface(segments, (-4000.0, 0.0, -3000.0, 1000.0))
    if not surface.ok:
        pytest.skip(surface.reason)
    elevated = next((i for i, z in enumerate(surface.z_source) if z != 0), None)
    if elevated is None:
        pytest.skip("no grade-separated segment here")
    height = surface.height_on(elevated)
    line = surface.lines[elevated]
    xs = np.linspace(line.coords[0][0], line.coords[-1][0], 40)
    ys = np.linspace(line.coords[0][1], line.coords[-1][1], 40)
    z = height(xs, ys)
    assert np.isfinite(z).all(), "the bound height function has holes; it must be defined everywhere"
    # Continuity: a carriageway does not step. Consecutive samples a few metres apart stay close.
    step = np.abs(np.diff(z))
    assert step.max() < 3.0, f"the bound surface steps by {step.max():.2f} m along one centreline"


# --------------------------------------------------------------------------------- curb ramps (J21)


def test_a_ramps_run_comes_from_its_measured_slope():
    """The DOT inventory publishes each ramp's running slope; the run is the kerb over the slope."""
    import pvlib

    assert pvlib.RAMP_DROP_M == pytest.approx(0.15), "the kerb reveal is the sidewalk lift minus the roadbed's"
    assert pvlib.ramp_run_m(8.33) == pytest.approx(0.15 / 0.0833, rel=1e-6), "the ADA maximum"
    assert pvlib.ramp_run_m(11.6) < pvlib.ramp_run_m(5.5), "a steeper ramp is a shorter one"
    # The file's slopes reach under 1 % and over 20 %; both ends are clamped rather than believed.
    assert pvlib.ramp_run_m(0.4) == pytest.approx(pvlib.RAMP_RUN_M[1])
    assert pvlib.ramp_run_m(40.0) == pytest.approx(pvlib.RAMP_RUN_M[0])
    assert pvlib.ramp_run_m(None) == pytest.approx(pvlib.ramp_run_m(pvlib.RAMP_DEFAULT_SLOPE_PCT))


def test_a_ramp_descends_from_the_sidewalk_to_the_roadbed():
    import numpy as np
    import pvlib

    run, width = 2.73, 1.24
    ring, (dx, dy) = pvlib.ramp_rect(0.0, 0.0, 1.0, 0.0, width, run)
    assert ring is not None and (dx, dy) == (1.0, 0.0)
    lift = pvlib.ramp_lift(np.asarray(ring), 0.0, 0.0, dx, dy, run)
    assert lift[0] == pytest.approx(pvlib.PAVEMENT_KINDS[1][1]), "the uphill end is the sidewalk"
    assert lift[2] == pytest.approx(pvlib.PAVEMENT_KINDS[0][1]), "the kerb end is the roadbed"
    # and it is a plane, not a step: halfway along, halfway down
    mid = pvlib.ramp_lift(np.array([[0.0, 0.0]]), 0.0, 0.0, dx, dy, run)
    assert mid[0] == pytest.approx((pvlib.PAVEMENT_KINDS[0][1] + pvlib.PAVEMENT_KINDS[1][1]) / 2.0)


def test_a_ramp_is_the_right_size_and_squared_to_its_own_direction():
    import numpy as np
    import pvlib

    ring, _ = pvlib.ramp_rect(10.0, 20.0, 0.0, 1.0, 1.5, 2.0)
    r = np.asarray(ring)
    assert r[:, 0].max() - r[:, 0].min() == pytest.approx(1.5), "width is across the descent"
    assert r[:, 1].max() - r[:, 1].min() == pytest.approx(2.0), "run is along it"


def test_a_ramp_walks_on_the_sidewalk_not_on_the_road():
    """`SurfaceClass::Sidewalk`, like the sidewalk it is cut into, not the asphalt it descends to."""
    import pvlib

    assert pvlib.surface_class(8, 1) == 9
    assert pvlib.material_name(8, 1) == "pave_curb_ramp_concrete"


def test_the_ramps_reached_the_built_tiles():
    """Every ramp in a built tile is built, or the manifest says which and why not."""
    import json

    manifests = sorted((REPO_ROOT / "blender_out" / "tiles").glob("*/pavement_manifest.json"))
    with_ramps = []
    for p in manifests:
        d = json.loads(p.read_text())
        r = d.get("curb_ramps")
        if r and r.get("ramps"):
            with_ramps.append((p.parent.name, r))
    if not with_ramps:
        pytest.skip("no tile has been built since the ramps were added")
    total = sum(r["ramps"] for _t, r in with_ramps)
    built = sum(r["built"] for _t, r in with_ramps)
    assert built / total > 0.9, f"only {built} of {total} surveyed ramps were built"
    for tile, r in with_ramps:
        assert r["built"] + r["no_roadbed"] + r["no_triangulation"] + r["no_terrain"] == r["ramps"], (
            f"{tile}: the ramp counts do not add up: {r}")


def test_the_ramp_is_left_out_of_the_draping_residual_and_says_so():
    """Its lift is not a constant, so a metric that subtracts one lift per object cannot read it."""
    import json

    for p in sorted((REPO_ROOT / "blender_out" / "tiles").glob("*/pavement_manifest.json")):
        d = json.loads(p.read_text())
        if not (d.get("curb_ramps") or {}).get("built"):
            continue
        res = d.get("draping_residual_m") or {}
        assert any("curb_ramp" in n for n in res.get("excluded_variable_lift", [])), (
            f"{p.parent.name}: the ramp mesh is in the residual, which reads its slope as error")
        return
    pytest.skip("no tile with ramps has been built")
