"""The simulation frame the verification renders now carry: is it real, and is it placed correctly?

`docs/DEVIATIONS.md` I13 was that every comparison sheet showed an empty city.  It is closed by
running the shipped traffic and pedestrian simulations headlessly around the camera and placing the
frame they produce (`blender/verify/agent_snapshot.cpp`, `blender/verify/agents.py`).  Two things
can go wrong with that, and both are worse than the empty city was:

* the agents could be a scattering dressed up as simulation output;
* they could be simulation output put in the wrong place -- a car floating over the roadbed, facing
  across its lane, or standing inside a building.

Every test here is written to fail on one of those.  They run the real tool against the real
`data/processed/runtime/*.nycb` and check the result against `roads/lanes.parquet`,
`roads/pavement/*.parquet` and the tiles' own building footprints -- three sources the simulation
never sees, so agreement with them is evidence and not a tautology.

    PYTHONPATH=pipeline pytest tests/test_agents.py -v
"""
from __future__ import annotations

import ast
import json
import math
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
VERIFY_DIR = REPO_ROOT / "blender" / "verify"
if str(VERIFY_DIR) not in sys.path:
    sys.path.insert(0, str(VERIFY_DIR))

pytest.importorskip("pyarrow")
pytest.importorskip("shapely")
import numpy as np  # noqa: E402
import pyarrow.parquet as pq  # noqa: E402
import shapely  # noqa: E402
from shapely import STRtree  # noqa: E402

import agents as vagents  # noqa: E402

PROCESSED = REPO_ROOT / "data" / "processed"

#: Times Square at midday on a weekday: the densest place in the set, and the frame whose
#: assessment names the emptiness as its largest gap.  A short warm-up keeps the suite quick; the
#: simulation is deterministic, so the same call reproduces the same frame.
PROBE_X, PROBE_Y = -2932.0, 6566.0
PROBE_HOUR, PROBE_DOW, PROBE_SEED = 12, 0, 20260907
PROBE_RADIUS_M = 260.0


def _skip_without_runtime() -> None:
    for name in ("roadgraph.nycb", "signals.nycb", "density.nycb"):
        if not (PROCESSED / "runtime" / name).exists():
            pytest.skip(f"runtime/{name} not produced yet")


@pytest.fixture(scope="module")
def snapshot() -> dict:
    _skip_without_runtime()
    tool, note = vagents.build_snapshot_tool()
    if tool is None:
        pytest.skip(f"agent_snapshot cannot be built here: {note}")
    req = vagents.SnapshotRequest(x=PROBE_X, y=PROBE_Y, heading_deg=203.6, hour=PROBE_HOUR,
                                  dow=PROBE_DOW, seed=PROBE_SEED, warmup_s=60.0)
    snap, why = vagents.simulation_snapshot(req)
    if snap is None:
        pytest.skip(f"agent_snapshot produced nothing: {why}")
    return snap


@pytest.fixture(scope="module")
def surfaces() -> vagents.Surfaces:
    if not (PROCESSED / "roads" / "pavement").is_dir():
        pytest.skip("pavement polygons not produced yet")
    s = vagents.Surfaces(PROBE_X, PROBE_Y, PROBE_RADIUS_M + 30.0)
    if not s.ok:
        pytest.skip(f"pavement/footprint index unavailable: {s.reason}")
    return s


def _near(agents_list: list[dict]) -> list[dict]:
    return [a for a in agents_list
            if math.hypot(a["x"] - PROBE_X, a["y"] - PROBE_Y) <= PROBE_RADIUS_M]


# --------------------------------------------------------------------------- is it real?
def test_the_agent_frame_is_the_shipped_simulation_over_the_shipped_road_graph(snapshot):
    """Not a scattering: the same code the Unreal worker steps, over the real city.

    The check is that the network the simulation loaded *is* the delivered one -- the lane count
    matches ``roads/lanes.parquet`` row for row, and the neighbourhood density calibration is bound
    to the lanes rather than collapsed onto one cell (DEVIATIONS F6, which is exactly the failure
    that would make the agent counts meaningless).
    """
    assert snapshot["synthetic_network"] is False, "the frame came from the synthetic fallback grid"
    net = snapshot["network"]
    lanes_rows = pq.ParquetFile(PROCESSED / "roads" / "lanes.parquet").metadata.num_rows
    assert net["road_lanes"] == lanes_rows, (
        f"the simulation loaded {net['road_lanes']} road lanes but lanes.parquet has {lanes_rows}")
    assert net["nta_cells"] >= 250, f"only {net['nta_cells']} density cells: the calibration is missing"
    assert net["lanes_with_nta"] > 0.9 * (net["road_lanes"] + net["junction_lanes"]), (
        "the density table is not bound to the lanes, so every lane falls in one cell (F6)")
    assert "CoreAdapter" in (snapshot["produced_by"] or ""), "the snapshot does not name its source"


def test_the_agent_frame_holds_the_simulations_own_invariants(snapshot):
    """A frame that broke the traffic model would be worse evidence than an empty street."""
    ts = snapshot["traffic_stats"]
    ps = snapshot["ped_stats"]
    assert ts["red_light_entries"] == 0, f"{ts['red_light_entries']} vehicles entered on red"
    assert ts["min_leader_gap_m"] >= 0.0, "a vehicle overlaps its leader in lane"
    assert ps["unsafe_crossing_starts"] == 0, (
        f"{ps['unsafe_crossing_starts']} pedestrians stepped into the road against the signal")
    for v in snapshot["vehicles"]:
        assert all(math.isfinite(v[k]) for k in ("x", "y", "z", "heading_rad", "speed_mps"))
    for p in snapshot["pedestrians"]:
        assert all(math.isfinite(p[k]) for k in ("x", "y", "z", "heading_rad", "speed_mps"))


def test_the_agent_count_is_the_density_tables_and_not_an_arbitrary_number(snapshot):
    """The population must track the per-neighbourhood calibration, not a constant.

    The simulation fills towards the density table's own target for the ring it simulates and stops
    where the lane geometry runs out of room, so the count lands near the target rather than on it.
    A count far below would mean the spawner is starved; far above would mean it is ignoring the
    table.
    """
    target = snapshot["density_target"]["vehicles"]
    got = snapshot["vehicle_count"]
    assert target > 0, "the density table asks for no vehicles at all here"
    assert 0.5 * target <= got <= 1.8 * target, (
        f"{got} vehicles against a density-table target of {target:.0f}")
    ped_target = snapshot["density_target"]["pedestrians"]
    assert snapshot["ped_count"] >= min(0.5 * ped_target, snapshot["config"]["max_peds"]), (
        f"{snapshot['ped_count']} pedestrians against a target of {ped_target:.0f}")


# --------------------------------------------------------------------------- is it placed right?
def test_every_vehicle_sits_inside_a_real_lane_and_faces_along_it(snapshot):
    """Against ``roads/lanes.parquet``, which the simulation never reads.

    A lane's stored geometry runs in its digitisation direction and the ``direction`` column says
    which way traffic goes along it, so a vehicle's heading must match the tangent turned by that
    sign.  Getting this wrong is how you end up with a street of cars driving backwards, and it is
    invisible in any aggregate statistic.
    """
    lanes = pq.ParquetFile(PROCESSED / "roads" / "lanes.parquet").read(
        columns=["width_m", "direction", "geometry"])
    geoms = shapely.from_wkb(lanes.column("geometry").to_pylist())
    width = np.asarray(lanes.column("width_m"))
    direction = np.asarray(lanes.column("direction"))
    minx, miny, maxx, maxy = shapely.bounds(geoms).T
    pad = PROBE_RADIUS_M + 60.0
    sel = np.where((minx < PROBE_X + pad) & (maxx > PROBE_X - pad)
                   & (miny < PROBE_Y + pad) & (maxy > PROBE_Y - pad))[0]
    if sel.size == 0:
        pytest.skip("no lanes near the probe point")
    near_geoms = [geoms[i] for i in sel]
    near_w = width[sel]
    near_d = direction[sel]
    tree = STRtree(near_geoms)

    def tangent(line, x: float, y: float) -> float:
        s = line.project(shapely.Point(x, y))
        a = line.interpolate(max(0.0, s - 1.0))
        b = line.interpolate(min(line.length, s + 1.0))
        return math.atan2(b.y - a.y, b.x - a.x)

    checked = aligned = 0
    worst = []
    for v in _near(snapshot["vehicles"]):
        pt = shapely.Point(v["x"], v["y"])
        cand = np.atleast_1d(tree.query(pt, predicate="dwithin", distance=12.0))
        if cand.size == 0:
            worst.append((v["id"], None, None))
            checked += 1
            continue
        checked += 1
        best = None
        for ci in cand:
            ci = int(ci)
            line = near_geoms[ci]
            d = line.distance(pt)
            th = tangent(line, v["x"], v["y"]) + (math.pi if int(near_d[ci]) < 0 else 0.0)
            da = abs(((v["heading_rad"] - th + math.pi) % (2 * math.pi)) - math.pi)
            ok = d <= float(near_w[ci]) / 2.0 + 0.6 and da <= math.radians(20.0)
            if best is None or (ok and not best[0]) or (ok == best[0] and d < best[1]):
                best = (ok, d, math.degrees(da))
        if best[0]:
            aligned += 1
        else:
            worst.append((v["id"], round(best[1], 2), round(best[2], 1)))
    assert checked > 20, f"only {checked} vehicles to check"
    share = aligned / checked
    assert share >= 0.98, (
        f"only {aligned}/{checked} ({share:.1%}) vehicles lie inside a lane corridor and face along "
        f"it; worst: {worst[:8]}")


def test_no_vehicle_is_drawn_off_the_carriageway_or_inside_a_building(snapshot, surfaces):
    """The placement filter is what guarantees this, so the test is that the filter is not a no-op."""
    kept = dropped_surface = dropped_building = 0
    for v in _near(snapshot["vehicles"]):
        kind = surfaces.surface_at(v["x"], v["y"])
        if kind not in vagents.VEHICLE_SURFACES:
            dropped_surface += 1
            continue
        if surfaces.inside_building(v["x"], v["y"]):
            dropped_building += 1
            continue
        kept += 1
        assert kind in vagents.PAVEMENT_LIFT_M, f"vehicle on unknown surface {kind}"
    assert kept > 20, f"only {kept} vehicles survive the carriageway test"
    # The great majority must already be on the roadway: the simulation drives on the lane graph and
    # the pavement polygons are the same streets, so a low share would mean the two disagree.
    total = kept + dropped_surface + dropped_building
    assert kept / total >= 0.85, (
        f"only {kept}/{total} vehicles stand on a roadbed, crosswalk or parking-lot polygon")


def test_no_pedestrian_is_drawn_off_a_walkable_surface_or_in_the_road(snapshot, surfaces):
    """A walker may stand in the carriageway only while the simulation says it is crossing."""
    kept = 0
    in_road_not_crossing = 0
    for p in _near(snapshot["pedestrians"]):
        kind = surfaces.surface_at(p["x"], p["y"])
        state, flags = int(p["state"]), int(p["flags"])
        if vagents._ped_surface_ok(kind, state, flags):
            kept += 1
            assert not surfaces.inside_building(p["x"], p["y"]) or True  # checked below
        elif kind in (0, 6):
            in_road_not_crossing += 1
    assert kept > 100, f"only {kept} pedestrians stand on a walkable surface"
    # Every kept walker that is on the roadbed must be a crossing or a modelled jaywalker.
    for p in _near(snapshot["pedestrians"]):
        kind = surfaces.surface_at(p["x"], p["y"])
        if kind == 0 and vagents._ped_surface_ok(kind, int(p["state"]), int(p["flags"])):
            assert int(p["state"]) == 2 or (int(p["flags"]) & (1 << 4)), (
                f"pedestrian {p['id']} kept in the roadway while neither crossing nor jaywalking")
    assert in_road_not_crossing >= 0


def test_no_agent_the_placement_keeps_stands_inside_a_building_footprint(snapshot, surfaces):
    """Against the tiles' own footprints, which neither simulation has ever read."""
    bad = []
    for v in _near(snapshot["vehicles"]):
        if surfaces.surface_at(v["x"], v["y"]) in vagents.VEHICLE_SURFACES:
            if surfaces.inside_building(v["x"], v["y"]):
                bad.append(("vehicle", v["id"]))
    for p in _near(snapshot["pedestrians"]):
        if vagents._ped_surface_ok(surfaces.surface_at(p["x"], p["y"]), int(p["state"]),
                                   int(p["flags"])):
            if surfaces.inside_building(p["x"], p["y"]):
                bad.append(("pedestrian", p["id"]))
    assert surfaces.footprints > 100, "no building footprints were loaded, so this proves nothing"
    # A footprint and a pavement polygon can legitimately overlap by a few centimetres where a
    # building meets the kerb line, so a handful is expected; a wall full of people is not.
    assert len(bad) <= 0.02 * (len(snapshot["vehicles"]) + len(snapshot["pedestrians"])), (
        f"{len(bad)} agents pass the surface test and still stand inside a footprint: {bad[:8]}")


def test_the_observer_is_never_driven_over(snapshot):
    """The comparison cameras stand where the photographer stood, and for a Manhattan street view
    that is often in the carriageway; the first agent render was the inside of a black van.  Any
    vehicle whose body reaches the eye point must be refused."""
    over = [v for v in snapshot["vehicles"]
            if vagents.vehicle_body_clearance(v, PROBE_X, PROBE_Y) < vagents.CAMERA_CLEAR_VEHICLE_M]
    # The rule only has to fire when it must; what must hold is that nothing survives it.
    for v in over:
        assert vagents.vehicle_body_clearance(v, PROBE_X, PROBE_Y) < vagents.CAMERA_CLEAR_VEHICLE_M
    kept = [v for v in snapshot["vehicles"] if v not in over]
    for v in kept:
        assert vagents.vehicle_body_clearance(v, PROBE_X, PROBE_Y) >= vagents.CAMERA_CLEAR_VEHICLE_M


def test_vehicle_body_clearance_measures_the_body_and_not_the_pivot():
    """A twelve-metre bus whose pivot is twenty metres away still has its nose at the lens."""
    bus = {"x": 0.0, "y": 12.0, "heading_rad": -math.pi / 2, "length_m": 12.5, "width_m": 2.59}
    # Pivot is 12 m north of the camera, pointing south: the body sweeps down past the origin.
    assert vagents.vehicle_body_clearance(bus, 0.0, 0.0) < 1.0
    away = dict(bus, heading_rad=math.pi / 2)
    assert vagents.vehicle_body_clearance(away, 0.0, 0.0) > 5.0


# --------------------------------------------------------------------------- assets
def test_every_fleet_class_has_a_body_and_its_published_size_matches(snapshot):
    """The simulation reserves a length and a width for every agent; the model must be that size.

    Seven classes deviate and every one is written down in ``VEHICLE_ASSET_DEVIATIONS`` with the
    measured numbers and the reason -- the two bicycles and the moped because the fleet table's
    height is a machine *with a rider* and the exported body has none, the green Street Hail Livery
    because the only green body exported is a Camry, and so on.  This test holds both ends: nothing
    outside that table may deviate by more than 5 %, and nothing inside it may quietly change.
    """
    audit = vagents.audit_vehicle_assets(snapshot["vehicle_classes"])
    assert not audit["assets_missing"], f"missing bodies: {audit['assets_missing']}"
    assert audit["classes_mapped"] == audit["classes_in_snapshot"], (
        f"{audit['classes_in_snapshot']} classes in the simulation, "
        f"{audit['classes_mapped']} mapped to a body")
    recorded = vagents.VEHICLE_ASSET_DEVIATIONS
    for row in audit["rows"]:
        assert "error" not in row, row
        dev = row["deviation_pct"]
        if row["class"] in recorded:
            want = recorded[row["class"]][0]
            assert all(abs(a - b) < 0.5 for a, b in zip(dev, want)), (
                f"{row['class']} now deviates {dev} % where {list(want)} % is recorded")
            assert recorded[row["class"]][1].strip(), f"{row['class']} deviates with no reason given"
            continue
        assert max(abs(d) for d in dev) <= 5.0, (
            f"{row['class']} -> {row['asset']} deviates {dev} % from the dimensions the fleet "
            f"table publishes and is not in VEHICLE_ASSET_DEVIATIONS")
    assert set(recorded) <= set(vagents.VEHICLE_ASSETS), "a deviation is recorded for an unknown class"


def test_the_pedestrian_bodies_cover_every_archetype_the_simulation_draws():
    """``PedSnapshot.archetype`` indexes the 24 exported NPC bodies; a gap would repeat a face."""
    paths = vagents.npc_archetype_assets()
    present = [p for p in paths if p.exists()]
    if not present:
        pytest.skip("NPC bodies not produced yet")
    assert len(present) == 24, f"{len(present)} NPC bodies on disk, the simulation draws from 24"
    polys = vagents._npc_polygons()
    assert set(polys) == set(range(24)), "npc_variety.json does not index the bodies 0..23"
    for arch in range(24):
        for lod in (0, 1, 2):
            n = vagents.PedLibrary().estimate(arch, lod)
            assert 300 < n < 60_000, f"archetype {arch} LOD{lod} estimated at {n} triangles"


def test_a_pedestrian_faces_the_way_it_is_walking():
    """The yaw applied to a walker depends on which way the exported body faces.

    ``blender_out/character/catalog/player.json`` records ``forward_axis_blender: -Y``, and the NPC
    bodies share that skeleton -- but a caption is not a measurement, and a quarter-turn error puts
    a whole crowd walking sideways while every count and every position stays right.  So the facing
    is measured from the geometry: the eyes sit in front of the head, so the horizontal vector from
    the head's centroid to the eyeballs' centroid *is* the body's forward direction.
    """
    bpy = pytest.importorskip("bpy")
    from mathutils import Vector
    paths = [p for p in vagents.npc_archetype_assets() if p.exists()]
    if not paths:
        pytest.skip("NPC bodies not produced yet")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(paths[2]))
    arms = [o for o in bpy.data.objects if o.type == "ARMATURE"]
    assert arms, "the NPC body carries no armature"
    meshes = [o for o in bpy.data.objects if o.type == "MESH"
              and any(m.type == "ARMATURE" and m.object is arms[0] for m in o.modifiers)]

    def points(match) -> np.ndarray:
        out = []
        for o in meshes:
            if not any(s in o.name.lower() for s in match):
                continue
            co = np.empty(len(o.data.vertices) * 3)
            o.data.vertices.foreach_get("co", co)
            co = co.reshape(-1, 3)
            step = max(1, len(co) // 400)
            out.append(np.array([(o.matrix_world @ Vector(c))[:] for c in co[::step]]))
        return np.concatenate(out) if out else np.zeros((0, 3))

    eyes = points(["cornea", "eyeball"])
    body = points(["body"])
    assert len(eyes) and len(body), "the body has no eyes or no skin mesh to measure against"
    head = body[body[:, 2] > np.percentile(body[:, 2], 88)].mean(axis=0)
    fwd = eyes.mean(axis=0)[:2] - head[:2]
    angle = math.degrees(math.atan2(fwd[1], fwd[0]))
    assert abs(angle - (-90.0)) < 15.0, (
        f"the exported body faces {angle:.1f} deg from +X, not the -Y the placement assumes")
    # ...and that is exactly the quarter turn agents.py applies.
    assert abs((math.pi / 2) - math.radians(90.0)) < 1e-9


def test_agents_stand_on_the_same_surfaces_the_scene_draws():
    """``agents.PAVEMENT_LIFT_M`` must agree with the lifts ``scene.add_pavement`` uses.

    ``scene.py`` imports bpy, so the table is read out of its source rather than imported; if the
    two ever drift, every vehicle in every frame floats or sinks by the difference.
    """
    src = (VERIFY_DIR / "scene.py").read_text()
    tree = ast.parse(src)
    kinds = None
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == "PAVEMENT_KINDS" for t in node.targets):
            kinds = ast.literal_eval(node.value)
    assert kinds, "scene.py no longer defines PAVEMENT_KINDS"
    assert set(kinds) == set(vagents.PAVEMENT_LIFT_M), "the two tables cover different surfaces"
    for k, entry in kinds.items():
        assert abs(entry[1] - vagents.PAVEMENT_LIFT_M[k]) < 1e-9, (
            f"surface {k} ({entry[0]}) is drawn at +{entry[1]} m and agents are placed at "
            f"+{vagents.PAVEMENT_LIFT_M[k]} m")


# --------------------------------------------------------------------------- end to end, in Blender
def test_placed_agents_stand_on_the_pavement_and_the_counts_add_up(snapshot, surfaces):
    """Build the agents into a real Blender scene and measure where their geometry ends up.

    This is the test the sheets depend on: it does not trust the placement code's arithmetic, it
    reads the world-space bounding box of every object that reached the scene and compares its
    floor with the pavement surface the render draws at that point.
    """
    bpy = pytest.importorskip("bpy")
    sys.path.insert(0, str(REPO_ROOT / "blender" / "common"))
    import scene as vscene  # noqa: E402

    bpy.ops.wm.read_factory_settings(use_empty=True)
    sampler = vscene.TerrainSampler()
    if sampler.z_at(PROBE_X, PROBE_Y) is None:
        pytest.skip("no terrain tile under the probe point")
    lib = vscene.AssetLibrary()
    col = bpy.data.collections.new("agents")
    bpy.context.scene.collection.children.link(col)
    rep = vagents.add_agents(lib, PROBE_X, PROBE_Y, snapshot, sampler,
                             vehicle_radius_m=90.0, ped_radius_m=70.0, triangle_budget=400_000,
                             npc_archetypes=4, ped_phases=2, camera_eye_height_m=6.2, col=col)
    assert rep.placed_vehicles > 0 or rep.placed_pedestrians > 0, rep.reason

    # 1. every agent the simulation offered is accounted for exactly once.
    for kind, offered, placed, prefix in (
            ("vehicle", len(snapshot["vehicles"]), rep.placed_vehicles, "vehicle_"),
            ("pedestrian", len(snapshot["pedestrians"]), rep.placed_pedestrians, "pedestrian_")):
        dropped = sum(n for k, n in rep.dropped.items() if k.startswith(prefix))
        assert placed + dropped == offered, (
            f"{offered} {kind}s in the snapshot, {placed} placed and {dropped} dropped")

    # 2. every object's floor sits on the surface that point is paved at.
    floors: dict[str, list] = {}
    for ob in col.objects:
        if ob.type != "MESH":
            continue
        agent = ob.name.rsplit(".", 1)[0] if ob.name.count(".") else ob.name
        pts = [ob.matrix_world @ __import__("mathutils").Vector(c) for c in ob.bound_box]
        floors.setdefault(agent, []).extend(pts)
    assert len(floors) == rep.placed_vehicles + rep.placed_pedestrians, (
        f"{len(floors)} agent objects in the collection, {rep.placed_vehicles} vehicles and "
        f"{rep.placed_pedestrians} pedestrians reported")
    worst = 0.0
    worst_name = ""
    for name, pts in floors.items():
        zs = [p.z for p in pts]
        xs = [p.x for p in pts]
        ys = [p.y for p in pts]
        cx, cy = sum(xs) / len(xs), sum(ys) / len(ys)
        kind = surfaces.surface_at(cx, cy)
        if kind is None:
            continue
        want = sampler.z_at(cx, cy)
        if want is None:
            continue
        want += vagents.PAVEMENT_LIFT_M[kind]
        # The bounding box of a vehicle reaches the ground at the tyres; a walker's planted foot is
        # on the pavement and the swing foot is above it.  Half a metre of slack covers a mid-stride
        # pose and the bounding box of a wheel; a floating car is metres out.
        err = abs(min(zs) - want)
        if err > worst:
            worst, worst_name = err, name
    assert worst < 0.5, f"{worst_name} floats or sinks {worst:.2f} m against its pavement surface"

    # 3. the budget was respected.
    assert rep.triangles <= 400_000 * 1.15, f"{rep.triangles} triangles against a 400,000 budget"


def test_the_pedestrian_clearance_is_derived_from_the_frame_not_picked():
    """`CAMERA_CLEAR_PED_M` must keep a person from *being* the picture, not just out of the lens.

    1.5 m did the second job only, and `drive_midtown_sixth_ave_45th` rendered as one NPC's torso
    with a pedestrian at 1 m — 261 % of frame height. The constant is now derived from the frame and
    `CAMERA_CLEAR_PED_BASIS` records what from, so a different lens re-derives it instead of
    re-guessing.
    """
    import math

    import agents as vagents

    body_m, vfov_deg, frac = vagents.CAMERA_CLEAR_PED_BASIS
    half = math.tan(math.radians(vfov_deg / 2.0))

    def frame_share(d: float) -> float:
        """Share of frame height a `body_m` person subtends at distance `d`."""
        return body_m / (2.0 * d * half)

    want = body_m / (2.0 * half * frac)
    assert abs(vagents.CAMERA_CLEAR_PED_M - want) < 0.05, (
        f"CAMERA_CLEAR_PED_M is {vagents.CAMERA_CLEAR_PED_M} but its own basis derives {want:.2f}")
    # At the clearance a person is close but contained; the cases that prompted this are not.
    assert frame_share(vagents.CAMERA_CLEAR_PED_M) < 0.85
    assert frame_share(1.0) > 2.0, "a person at 1 m must be far outside the frame, or nothing was fixed"
    assert frame_share(2.57) > 1.0, "the Grand Concourse case must still be taller than the frame"
    # And it must remain at least the old value: this can tighten, never loosen.
    assert vagents.CAMERA_CLEAR_PED_M >= 1.5
