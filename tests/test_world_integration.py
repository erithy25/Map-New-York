"""Cross-cutting integration tests: the checks no single stage can make.

Each test asserts a property that spans two or more subsystems (geodesy vs. data, tiles vs.
buildings, roads vs. terrain, assets vs. placements). Tests skip with an explicit reason when the
artefact they need has not been produced yet, so this file is meaningful at every point in the
build and becomes the definition-of-done gate at the end.

    PYTHONPATH=pipeline pytest tests/test_world_integration.py -v
"""
from __future__ import annotations

import json
import math
import struct
import time
from pathlib import Path

import pytest

pytest.importorskip("pyarrow")
import pyarrow.parquet as pq  # noqa: E402

from nycsim_pipeline import crs, tiling  # noqa: E402
from nycsim_pipeline.paths import BLENDER_OUT, PROCESSED, REPO_ROOT, VERIFICATION  # noqa: E402

TILES = PROCESSED / "tiles"


def _need(p: Path, what: str) -> Path:
    if not p.exists():
        pytest.skip(f"{what} not produced yet ({p.relative_to(REPO_ROOT) if p.is_relative_to(REPO_ROOT) else p})")
    return p


def _tile_files(name: str) -> list[Path]:
    return sorted(TILES.glob(f"*/{name}")) if TILES.exists() else []


# --------------------------------------------------------------------------- geodesy
def test_world_crs_is_one_to_one_across_the_whole_scope():
    """1:1 means 1:1: map scale distortion must stay under 10 mm per km anywhere in the five boroughs."""
    corners = [(-74.2591, 40.4774), (-73.7002, 40.4774), (-73.7002, 40.9176), (-74.2591, 40.9176),
               (-74.0060, 40.7128), (-73.9857, 40.7484), (-74.2513, 40.5051), (-73.8474, 40.9037)]
    worst = max(abs(crs.scale_distortion_ppm(lon, lat)) for lon, lat in corners)
    assert worst < 10.0, f"worst-case scale distortion {worst:.1f} ppm exceeds 10 mm/km"


def test_crs_json_matches_the_code():
    p = _need(PROCESSED / "crs.json", "crs.json")
    d = json.load(open(p))
    assert d["proj4"] == crs.NYC_TM_PROJ4
    assert d["tile_size_m"] == crs.TILE_SIZE_M


def test_known_landmarks_land_in_their_expected_boroughs_and_tiles():
    """A coordinate bug anywhere in the chain shows up here first."""
    known = {"Empire State Building": (-73.9857, 40.7484), "Yankee Stadium": (-73.9262, 40.8296),
             "Coney Island": (-73.9779, 40.5749), "Tottenville": (-74.2513, 40.5051),
             "Flushing Meadows": (-73.8458, 40.7461)}
    for name, (lon, lat) in known.items():
        x, y = crs.lonlat_to_tm(lon, lat)
        t = tiling.tile_of(x, y)
        x0, y0, x1, y1 = t.bounds
        assert x0 <= x < x1 and y0 <= y < y1, f"{name} outside its own tile bounds"
        back = crs.tm_to_lonlat(x, y)
        assert math.isclose(back[0], lon, abs_tol=1e-9) and math.isclose(back[1], lat, abs_tol=1e-9)


# --------------------------------------------------------------------------- buildings
def test_every_building_sits_inside_the_tile_it_is_assigned_to():
    p = _need(PROCESSED / "buildings" / "buildings_base.parquet", "buildings_base")
    t = pq.ParquetFile(p).read(columns=["centroid_x", "centroid_y", "tile"])
    xs, ys, tiles = t.column("centroid_x").to_pylist(), t.column("centroid_y").to_pylist(), t.column("tile").to_pylist()
    step = max(1, len(xs) // 20000)  # sample; a systematic error shows up immediately
    bad = []
    for i in range(0, len(xs), step):
        want = tiling.tile_of(xs[i], ys[i]).name
        if tiles[i] != want:
            bad.append((tiles[i], want))
            if len(bad) > 5:
                break
    assert not bad, f"tile assignment disagrees with the tiling module: {bad[:5]}"


def test_building_heights_are_physically_plausible():
    p = _need(PROCESSED / "buildings" / "buildings_base.parquet", "buildings_base")
    t = pq.ParquetFile(p).read(columns=["height", "roof_z", "ground_z"])
    h = t.column("height").to_numpy(zero_copy_only=False)
    assert h.min() > 0.0, "a building with non-positive height exists"
    # One World Trade Center's roof is 417 m; nothing in NYC exceeds 550 m to the roof.
    assert h.max() < 550.0, f"tallest building {h.max():.1f} m is above any real NYC roof height"
    assert (h > 100.0).sum() > 250, "too few buildings above 100 m for New York City"
    roof = t.column("roof_z").to_numpy(zero_copy_only=False)
    ground = t.column("ground_z").to_numpy(zero_copy_only=False)
    assert (roof >= ground).all(), "a roof sits below its own ground elevation"


def test_borough_building_counts_match_the_borough_summary():
    p = _need(PROCESSED / "buildings" / "borough_summary.json", "borough summary")
    base = _need(PROCESSED / "buildings" / "buildings_base.parquet", "buildings_base")
    d = json.load(open(p))
    total_reported = sum(v["buildings"] for v in d["boroughs"].values())
    assert total_reported == pq.ParquetFile(base).metadata.num_rows


def test_landmark_footprints_resolve_to_real_buildings():
    p = _need(PROCESSED / "buildings" / "landmark_footprints.parquet", "landmark footprints")
    t = pq.ParquetFile(p).read()
    names = [str(n).lower() for n in t.column("name").to_pylist()] if "name" in t.column_names else []
    joined = " ".join(names)
    for must in ("empire state", "chrysler"):
        assert must in joined, f"{must!r} missing from the resolved landmark footprints"


# --------------------------------------------------------------------------- terrain
def test_terrain_tiles_are_readable_and_seams_line_up():
    files = _tile_files("terrain.json")
    if not files:
        pytest.skip("terrain tiles not produced yet")
    png = pytest.importorskip("PIL.Image", reason="Pillow needed to read heightmaps")
    from PIL import Image
    import numpy as np
    checked = 0
    now = time.time()

    def being_written(*paths: Path) -> bool:
        """A tile touched in the last two minutes may be half-written by a concurrent stage."""
        return any(p.exists() and now - p.stat().st_mtime < 120 for p in paths)

    for meta_p in files[:400]:
        img_p = meta_p.parent / "terrain.png"
        if being_written(meta_p, img_p):
            continue
        meta = json.load(open(meta_p))
        assert img_p.exists(), f"{meta_p.parent.name} has terrain.json but no terrain.png"
        try:
            a = np.asarray(Image.open(img_p))
        except OSError as e:
            pytest.fail(f"{meta_p.parent.name}: terrain.png is unreadable and not being written ({e})")
        assert a.shape == (meta["samples"], meta["samples"]), f"{meta_p.parent.name} heightmap shape mismatch"
        t = tiling.Tile.parse(meta_p.parent.name)
        east = TILES / tiling.Tile(t.tx + 1, t.ty).name / "terrain.png"
        if east.exists() and not being_written(east, east.with_suffix(".json")):
            b = np.asarray(Image.open(east))
            east_meta = json.load(open(east.with_suffix(".json")))
            za = meta["z_min_m"] + a[:, -1].astype(float) * meta["z_scale_m"]
            zb = east_meta["z_min_m"] + b[:, 0].astype(float) * east_meta["z_scale_m"]
            assert np.abs(za - zb).max() < 0.05, f"seam mismatch between {meta_p.parent.name} and its eastern neighbour"
            checked += 1
    assert checked or len(files) < 2, "no shared tile edges could be compared"


def test_highest_points_are_todt_hill_in_the_city_and_the_palisades_in_new_jersey():
    """Todt Hill (about 125 m) is the highest natural point in New York City.

    The scope also covers the New Jersey shoreline, whose Palisades ridge is higher, so the
    city-wide maximum is checked inside Staten Island rather than over the whole grid.
    """
    files = _tile_files("terrain.json")
    if not files:
        pytest.skip("terrain tiles not produced yet")
    # Staten Island bounding box in WGS84, converted once to the world CRS.
    sw = crs.lonlat_to_tm(-74.262, 40.491)
    ne = crs.lonlat_to_tm(-74.049, 40.651)
    peaks_si: list[tuple[float, str]] = []
    peaks_all: list[tuple[float, str]] = []
    for f in files:
        name = f.parent.name
        z = json.load(open(f)).get("z_max_m")
        if not isinstance(z, (int, float)):
            continue
        peaks_all.append((z, name))
        t = tiling.Tile.parse(name)
        cx, cy = t.x0 + 500.0, t.y0 + 500.0
        if sw[0] <= cx <= ne[0] and sw[1] <= cy <= ne[1]:
            peaks_si.append((z, name))
    assert peaks_si, "no tiles fall inside the Staten Island bounding box"
    si_peak = max(peaks_si)
    assert 100.0 < si_peak[0] < 145.0, f"Staten Island maximum {si_peak[0]:.1f} m in {si_peak[1]} is not Todt Hill"
    overall = max(peaks_all)
    # The Palisades escarpment opposite Manhattan reaches roughly 150-180 m.
    assert 100.0 < overall[0] < 220.0, f"scope-wide terrain maximum {overall[0]:.1f} m in {overall[1]} is implausible"
    lowest = min((json.load(open(f)).get("z_min_m", 999), f.parent.name) for f in files)
    assert lowest[0] > -12.0, (
        f"lowest terrain sample {lowest[0]:.1f} m in {lowest[1]} — deeper than any real cut in the scope, "
        "which usually means an unfilled DEM void")


# --------------------------------------------------------------------------- roads
def test_road_network_is_connected_enough_to_drive_across_the_city():
    p = _need(PROCESSED / "roads" / "segments.parquet", "road segments")
    nodes_p = _need(PROCESSED / "roads" / "nodes.parquet", "road nodes")
    seg = pq.ParquetFile(p).read(columns=["segment_id", "from_node", "to_node", "rw_type"])
    n_nodes = pq.ParquetFile(nodes_p).metadata.num_rows
    # union-find over the undirected segment graph
    parent: dict[int, int] = {}

    def find(a: int) -> int:
        while parent.setdefault(a, a) != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    fr, to = seg.column("from_node").to_pylist(), seg.column("to_node").to_pylist()
    for a, b in zip(fr, to):
        ra, rb = find(int(a)), find(int(b))
        if ra != rb:
            parent[ra] = rb
    sizes: dict[int, int] = {}
    for n in set(fr) | set(to):
        r = find(int(n))
        sizes[r] = sizes.get(r, 0) + 1
    largest = max(sizes.values())
    assert largest / max(n_nodes, 1) > 0.9, (
        f"the largest connected component holds only {largest:,} of {n_nodes:,} nodes — the city is not drivable end to end")


def test_every_named_bridge_and_tunnel_is_present():
    p = _need(PROCESSED / "roads" / "bridges_tunnels.json", "bridge/tunnel index")
    d = json.load(open(p))
    items = d.get("bridges_tunnels", d) if isinstance(d, dict) else d
    blob = json.dumps(items).lower()
    required = ["brooklyn", "manhattan", "williamsburg", "queensboro", "george washington", "verrazzano",
                "throgs neck", "whitestone", "pulaski", "kosciuszko", "high bridge", "triborough",
                "lincoln", "holland", "queens-midtown", "carey"]
    missing = [r for r in required if r not in blob]
    assert not missing, f"missing from the bridge/tunnel index: {missing}"


def test_lane_geometry_stays_inside_its_segment_corridor():
    lanes_p = _need(PROCESSED / "roads" / "lanes.parquet", "lanes")
    shapely = pytest.importorskip("shapely")
    from shapely import wkb
    lanes = pq.ParquetFile(lanes_p).read(columns=["lane_id", "segment_id", "width_m", "geometry"])
    segs = pq.ParquetFile(_need(PROCESSED / "roads" / "segments.parquet", "segments")).read(
        columns=["segment_id", "geometry", "width_m"])
    seg_geom = {int(s): wkb.loads(bytes(g.as_py())) for s, g in zip(segs.column("segment_id").to_pylist(), segs.column("geometry"))}
    seg_w = {int(s): float(w) for s, w in zip(segs.column("segment_id").to_pylist(), segs.column("width_m").to_pylist())}
    bad = 0
    ids = lanes.column("segment_id").to_pylist()
    step = max(1, len(ids) // 3000)
    for i in range(0, len(ids), step):
        sid = int(ids[i])
        if sid not in seg_geom:
            continue
        g = wkb.loads(bytes(lanes.column("geometry")[i].as_py()))
        allowed = max(seg_w.get(sid, 12.0), 12.0) / 2.0 + 3.0
        if g.distance(seg_geom[sid]) > allowed:
            bad += 1
    assert bad == 0, f"{bad} sampled lanes lie outside their segment corridor"


# --------------------------------------------------------------------------- runtime binaries
def test_runtime_binaries_have_a_valid_container_header():
    d = PROCESSED / "runtime"
    files = sorted(d.glob("*.nycb")) if d.exists() else []
    if not files:
        pytest.skip("runtime .nycb binaries not produced yet")
    for f in files:
        with open(f, "rb") as fh:
            magic, version, section_count, _pad, index_offset = struct.unpack("<4sIIIQ", fh.read(24))
        assert magic == b"NYCB", f"{f.name} is not a NYCB container"
        assert version == 1, f"{f.name} has unexpected version {version}"
        assert 0 < section_count < 4096, f"{f.name} declares {section_count} sections"
        assert 24 <= index_offset <= f.stat().st_size, f"{f.name} index offset out of range"


def test_roadgraph_binary_agrees_with_the_parquet_it_came_from():
    b = PROCESSED / "runtime" / "roadgraph.nycb"
    segs = PROCESSED / "roads" / "segments.parquet"
    if not b.exists() or not segs.exists():
        pytest.skip("roadgraph.nycb or segments.parquet not produced yet")
    with open(b, "rb") as fh:
        _, _, section_count, _pad, index_offset = struct.unpack("<4sIIIQ", fh.read(24))
        fh.seek(index_offset)
        counts = {}
        for _ in range(section_count):
            name, offset, size, esize, ecount = struct.unpack("<16sQQII", fh.read(40))
            counts[name.rstrip(b"\0").decode()] = ecount
    assert counts.get("segments") == pq.ParquetFile(segs).metadata.num_rows, (
        f"roadgraph.nycb holds {counts.get('segments')} segments but the parquet holds "
        f"{pq.ParquetFile(segs).metadata.num_rows}")


# --------------------------------------------------------------------------- assets vs. data
def test_kit_placements_are_populated_and_reference_real_kit_pieces():
    """A tile full of buildings must carry facade kit placements.

    The emit stage once wrote 920 well-formed headers with `count: 0` and reported no problems,
    because it validated structure and not content. Zero placements means no windows, no fire
    escapes and no storefronts anywhere in the city, so emptiness is a failure, not a pass.
    """
    headers = _tile_files("kit_placements.json")
    if not headers:
        pytest.skip("kit placements not produced yet")
    catalog_dir = BLENDER_OUT / "kit" / "catalog"
    known: set = set()
    if catalog_dir.exists():
        for p in catalog_dir.glob("*.json"):
            d = json.load(open(p))
            for key in ("kit_id", "id"):
                if key in d:
                    known.add(d[key])

    populated = 0
    total_records = 0
    used_ids: set = set()
    for h in headers:
        d = json.load(open(h))
        blob = h.parent / "kit_placements.bin"
        assert blob.exists(), f"{h.parent.name}: header without a .bin"
        size = blob.stat().st_size
        assert size == d.get("bytes", size), f"{h.parent.name}: header says {d.get('bytes')} bytes, file has {size}"
        assert size % 40 == 0, f"{h.parent.name}: {size} bytes is not a whole number of 40-byte records"
        if size:
            populated += 1
            total_records += size // 40
        for kid in d.get("kit_ids", []):
            used_ids.add(kid)

    # Every tile that holds buildings should hold placements: a building needs windows.
    with_buildings = sum(1 for h in headers if (h.parent / "buildings.parquet").exists())
    assert populated > 0, (
        f"all {len(headers)} kit placement files are empty — the emit stage produced no placements at all")
    assert populated >= 0.9 * with_buildings, (
        f"only {populated} of {with_buildings} tiles with buildings carry placements")
    assert total_records > 1_000_000, (
        f"only {total_records:,} placements city-wide for over a million buildings — far too few to be windows")

    # Every numeric kit id a placement uses must resolve, through the registry, to an asset that
    # exists on disk. The registry and the Blender kit catalog are written by different stages, so
    # this is the check that catches them drifting apart.
    registry_path = PROCESSED / "facade" / "kit_ids.json"
    if not registry_path.exists():
        pytest.skip("kit id registry not produced yet")
    registry = json.load(open(registry_path))
    by_id = {int(p["kit_id"]): p for p in registry.get("pieces", [])}
    assert by_id, "the kit id registry lists no pieces"
    unregistered = sorted(k for k in used_ids if int(k) not in by_id)
    assert not unregistered, f"placements use kit ids missing from the registry: {unregistered[:8]}"

    catalog_ids = {json.load(open(p))["id"] for p in (BLENDER_OUT / "kit" / "catalog").glob("*.json")} \
        if (BLENDER_OUT / "kit" / "catalog").exists() else set()
    if catalog_ids:
        unresolved = sorted(
            f'{k}:{by_id[int(k)].get("category")}/{by_id[int(k)].get("name")}'
            for k in used_ids
            if by_id[int(k)].get("catalog_id") not in catalog_ids)
        assert not unresolved, (
            f"{len(unresolved)} kit ids used by placements do not resolve to an exported asset — the registry "
            f"must carry the exporting catalog's own id in `catalog_id`. Examples: {unresolved[:6]}")


def test_every_exported_asset_has_a_catalog_entry():
    import re
    if not BLENDER_OUT.exists():
        pytest.skip("no Blender output yet")
    for group in ("kit", "props", "vehicles", "landmarks"):
        d = BLENDER_OUT / group
        # files whose name starts with "_" are scratch output from an agent's own smoke runs
        globs = [g for g in d.rglob("*.glb") if not g.stem.startswith("_")] if d.exists() else []
        if not globs:
            continue
        cat = {p.stem for p in (d / "catalog").glob("*.json")} if (d / "catalog").exists() else set()
        # An asset may ship its LOD meshes either inside the parent .glb or as sibling
        # "<id>_LOD1.glb" files; both are covered by the parent's catalog entry.
        base = lambda stem: re.sub(r"_lod\d+$", "", stem, flags=re.I)
        missing = sorted({base(g.stem) for g in globs} - cat)
        assert not missing, f"{group}: {len(missing)} exported assets without a catalog entry, e.g. {missing[:5]}"


def test_landmark_models_match_their_published_heights():
    """Every landmark catalog entry is checked against the published height it cites.

    Heights are compared to the tip (spire and mast included) because that is what the catalog
    records — the Empire State Building is 443.2 m to the tip and 380.6 m to the roof, and both
    numbers appear in its `height_source` string.
    """
    catalog = BLENDER_OUT / "landmarks" / "catalog"
    if not catalog.exists() or not any(catalog.glob("*.json")):
        pytest.skip("no landmark catalog yet")
    published_tip_m = {
        "empire_state": 443.2, "chrysler": 318.9, "flatiron": 86.9, "one_vanderbilt": 427.0,
        "woolworth": 241.4, "40_wall_street": 282.5, "30_rockefeller_plaza": 259.1,
        "one_world_trade_center": 541.3, "george_washington_bridge": 184.0,
        "verrazzano_narrows": 211.0, "brooklyn_bridge": 84.3, "hearst_tower": 182.0,
        "metlife_building": 246.0, "seagram_building": 157.0, "un_headquarters": 154.0,
        "central_park_tower": 472.4, "432_park": 425.5, "111_west_57": 435.0, "one57": 306.1,
        "bank_of_america_tower": 365.8, "citigroup_center": 279.0, "statue_of_liberty": 93.0,
    }
    checked, problems = 0, []
    for f in sorted(catalog.glob("*.json")):
        d = json.load(open(f))
        ident = str(d.get("id", f.stem))
        height = d.get("height_m") or d.get("model_height_m")
        assert height, f"{ident}: catalog entry carries no height"
        assert d.get("height_source"), f"{ident}: height has no cited source"
        stripped = ident[2:] if ident[:2] in ("b_", "c_") else ident
        for key, real in published_tip_m.items():
            if key == stripped or key in stripped:
                checked += 1
                if abs(height - real) / real > 0.02:
                    problems.append(f"{ident}: model {height:.1f} m vs published {real:.1f} m")
                break
    assert checked >= 10, f"only {checked} landmarks could be compared against published heights"
    assert not problems, "landmark heights disagree with their cited sources: " + "; ".join(problems)


def test_verification_renders_can_actually_serve_as_evidence():
    """A render that is black, blown out or featureless proves nothing.

    The point of the verification renders is that a person looks at them and judges whether the
    geometry is right. An image with no visible content cannot support that judgement, so it fails
    here rather than sitting in a directory looking like evidence.

    Thresholds are set to pass legitimately low-contrast output — a city-wide hillshade over mostly
    flat terrain, or a chart on a white ground — while catching a camera inside geometry or an
    exposure set for a different scene.
    """
    Image = pytest.importorskip("PIL.Image", reason="Pillow needed to inspect renders")
    import numpy as np
    from PIL import Image as PILImage

    renders = sorted((VERIFICATION).rglob("*.png")) if VERIFICATION.exists() else []
    if not renders:
        pytest.skip("no verification renders yet")
    unusable: list[str] = []
    for r in renders:
        try:
            a = np.asarray(PILImage.open(r).convert("L"), dtype=np.float32) / 255.0
        except Exception as e:  # noqa: BLE001 — an unreadable render is itself the failure
            unusable.append(f"{r.relative_to(VERIFICATION)}: unreadable ({e})")
            continue
        mean, sd = float(a.mean()), float(a.std())
        if mean < 0.06:
            unusable.append(f"{r.relative_to(VERIFICATION)}: near-black (mean {mean:.3f})")
        elif mean > 0.94 and sd < 0.05:
            unusable.append(f"{r.relative_to(VERIFICATION)}: blown out (mean {mean:.3f}, sd {sd:.3f})")
        elif sd < 0.025:
            unusable.append(f"{r.relative_to(VERIFICATION)}: featureless (sd {sd:.3f})")
    assert not unusable, (
        f"{len(unusable)} of {len(renders)} verification renders cannot serve as evidence:\n  "
        + "\n  ".join(unusable))


def test_the_world_has_no_orphan_or_missing_content_layers():
    """Every layer must agree about which tiles hold content.

    A building without a mesh is invisible; a mesh without buildings is geometry nobody can query;
    a content tile without terrain is a building floating over nothing. None of these show up in a
    per-stage test, because each stage only sees its own output.
    """
    def tiles_with(pattern: str, depth: str = "parent") -> set:
        if depth == "parent":
            return {p.parent.name for p in Path(".").glob(pattern)}
        return {p.stem for p in Path(".").glob(pattern)}

    terrain = tiles_with("data/processed/tiles/*/terrain.json")
    buildings = tiles_with("data/processed/tiles/*/buildings.parquet")
    shells = tiles_with("blender_out/tiles/*/tile_buildings.glb")
    props = tiles_with("data/processed/tiles/*/props.parquet")
    kit = tiles_with("data/processed/tiles/*/kit_placements.bin")
    if not buildings:
        pytest.skip("no per-tile building data yet")

    problems = []
    if shells:
        missing_mesh = sorted(buildings - shells)
        assert not missing_mesh, f"{len(missing_mesh)} tiles hold buildings but no shell mesh, e.g. {missing_mesh[:5]}"
        orphan_mesh = sorted(shells - buildings)
        assert not orphan_mesh, f"{len(orphan_mesh)} shell meshes have no building data, e.g. {orphan_mesh[:5]}"
    if kit:
        no_kit = sorted(buildings - kit)
        assert not no_kit, f"{len(no_kit)} tiles hold buildings but no kit placements, e.g. {no_kit[:5]}"
    if terrain:
        floating = sorted((buildings | props) - terrain)
        assert not floating, f"{len(floating)} content tiles have no terrain beneath them, e.g. {floating[:5]}"
    assert not problems


# --------------------------------------------------------------------------- honesty gate
def test_no_placeholder_markers_in_shipped_source():
    """The brief forbids placeholders. This test is the gate that keeps them out.

    It is expected to fail while a stage is mid-flight and its scaffolding files are still empty.
    It must pass before the build is called done — that is the whole point of having it.
    """
    import re
    roots = [REPO_ROOT / "pipeline", REPO_ROOT / "blender", REPO_ROOT / "core", REPO_ROOT / "services",
             REPO_ROOT / "unreal" / "NYCSim" / "Source", REPO_ROOT / "tests"]
    # Markers are matched case-sensitively: conventional markers are upper case, whereas "todo" as a
    # lower-case identifier (a work queue, a boolean mask) is ordinary code.
    marker = re.compile(r"\b(TODO|FIXME|XXX|HACK)\b")
    # "Placeholder" and "stub" are ordinary domain words in this project — the NYC footprint data has
    # placeholder BINs, and a test may assert that a smoke file was deleted. What the brief forbids is
    # unfinished work, so the word only counts when the same line also signals incompleteness.
    incomplete = re.compile(r"pending|to be implemented|implement later|for now|temporar|will be replaced"
                            r"|not implemented|NotImplementedError|dummy|fake data|TBD|coming soon", re.I)
    suspicious = re.compile(r"placeholder|stub(bed)? out", re.I)
    negated = re.compile(r"not a placeholder|nothing here is a placeholder|no placeholder|forbids placeholder"
                         r"|must be deleted|keeps them out|banned|for banned in|forbidden", re.I)

    hits: list[str] = []
    for root in roots:
        if not root.exists():
            continue
        for p in root.rglob("*"):
            if p.suffix.lower() not in {".py", ".h", ".hpp", ".cpp", ".cs", ".ini"} or not p.is_file():
                continue
            if "third_party" in p.parts or "__pycache__" in p.parts:
                continue
            if p.name == "test_world_integration.py":
                continue  # this file necessarily contains the words it forbids
            for i, line in enumerate(p.read_text(errors="replace").splitlines(), 1):
                unfinished = incomplete.search(line) and suspicious.search(line)
                bare_incomplete = re.search(r"not implemented|NotImplementedError|stub(bed)? out", line, re.I)
                if (marker.search(line) or unfinished or bare_incomplete) and not negated.search(line):
                    hits.append(f"{p.relative_to(REPO_ROOT)}:{i}: {line.strip()[:100]}")
    assert not hits, "placeholder markers found in shipped source:\n" + "\n".join(hits[:40])


def test_fidelity_report_counts_every_bit_from_the_stage_that_sets_it():
    """The report must not read a fidelity bit from a table that never writes it.

    DATA_CONTRACTS §5.1 gives bits 2, 5, 10 and 13 to the facade stage, which writes
    `facade/facade_attrs.parquet` and does not write back into `buildings_base.parquet`. Counting them in
    the base table returns 0 for each, and the report then states that 0 % of facades are inferred and
    0 % of roofs are inferred when the real figures are 96.69 % and 52.43 %. That is not a rounding error
    in a table — it is the report claiming inferred content is real, which the brief names as the worst
    failure available to this project. This test fails if any bit is counted from a table that does not
    set it, by checking the count the report produces against a direct count in the owning table.
    """
    import numpy as np

    from nycsim_pipeline.report.fidelity import FIDELITY_BITS, FIDELITY_TABLES, probe_buildings

    b = probe_buildings()
    if b is None:
        pytest.skip("buildings_base.parquet not produced")

    direct: dict[str, int] = {}
    for owner, rel in FIDELITY_TABLES.items():
        path = PROCESSED / rel
        if not path.exists():
            continue
        pf = pq.ParquetFile(path)
        if "fidelity" not in pf.schema_arrow.names:
            continue
        fid = np.asarray(pf.read(columns=["fidelity"]).column("fidelity")).astype(np.uint32)
        for bit, name, _desc, o in FIDELITY_BITS:
            if o == owner:
                direct[name] = int(((fid >> bit) & 1).sum())

    assert direct, "no owning table carried a fidelity column — the probe cannot be checked"
    wrong = {name: (b["bits"].get(name), n) for name, n in direct.items() if b["bits"].get(name) != n}
    assert not wrong, ("the report's count disagrees with a direct count in the owning table "
                       f"(reported, actual): {wrong}")

    # The two bits that record inference must be non-zero: every building's facade appearance is inferred
    # unless a real material was found (ADR-004), and every roof without LOD2 geometry is inferred
    # (ADR-013). A zero in either would mean the report is reading the wrong table again.
    for name in ("FACADE_INFERRED", "ROOF_INFERRED"):
        n = b["bits"].get(name)
        assert n, f"{name} is {n!r}; inferred content exists and must be reported as inferred"
        assert n < b["total"], f"{name} covers every building, which no rule set should produce"

    # A bit whose owning artefact is absent must read None ("not produced"), never 0.
    for _bit, name, _desc, owner in FIDELITY_BITS:
        if owner in FIDELITY_TABLES and not (PROCESSED / FIDELITY_TABLES[owner]).exists():
            assert b["bits"].get(name) is None, f"{name} has no owning table but was reported as a number"


def test_landmark_models_are_flagged_on_the_buildings_they_replace():
    """Bit 7 must count the landmark models that exist, not zero.

    No stage writes a landmark column into the buildings table, so the landmark catalog is the authority.
    If the catalog names BINs and the report still says none are flagged, the report is under-claiming the
    hand-built work; if it names BINs that no building has, the catalog and the buildings table disagree.
    """
    from nycsim_pipeline.report.fidelity import _landmark_model_bins, probe_buildings

    lm = _landmark_model_bins()
    if lm is None:
        pytest.skip("landmark catalog not produced")
    b = probe_buildings()
    if b is None:
        pytest.skip("buildings_base.parquet not produced")
    if not lm:
        pytest.skip("no landmark entry names a BIN")

    base = pq.read_table(PROCESSED / "buildings" / "buildings_base.parquet", columns=["bin"])
    known = set(base.column("bin").to_pylist())
    missing = sorted(b for b in lm if b not in known)
    assert not missing, f"the landmark catalog names {len(missing)} BINs no building has: {missing[:10]}"
    assert b["bits"].get("LANDMARK_MODEL") == len(lm), (
        f"catalog names {len(lm)} BINs but the report flags {b['bits'].get('LANDMARK_MODEL')!r}")


# The nine renders that brief §12 condition 3 actually names: seven standard viewpoints, two of which
# are required in two states (Duffy Square day and night, Fifth Avenue north and south).
MANDATED_VIEWPOINTS = {
    "promenade_lower_manhattan": "Brooklyn Heights Promenade looking at Lower Manhattan",
    "top_of_the_rock_south": "Top of the Rock looking south",
    "times_square_duffy_south_day": "Duffy Square looking south, day",
    "times_square_duffy_south_night": "Duffy Square looking south, night",
    "fifth_ave_42nd_north": "Fifth Avenue at 42nd Street looking north",
    "fifth_ave_42nd_south": "Fifth Avenue at 42nd Street looking south",
    "bethesda_terrace_fountain": "Bethesda Terrace and Fountain",
    "staten_island_ferry_lower_manhattan": "Staten Island Ferry deck looking at Lower Manhattan",
    "dumbo_washington_st_manhattan_bridge": "Washington Street in DUMBO with the Manhattan Bridge",
}

# The five drive-through areas the brief names, as the scenes that stand for them.
DRIVE_AREAS = {
    "Midtown": ["drive_midtown_sixth_ave_45th"],
    "Lower Manhattan": ["drive_lower_manhattan_broadway_wall_st", "drive_lower_manhattan_stone_st"],
    "Brooklyn brownstone block": ["drive_brooklyn_park_slope_7th_ave", "drive_brooklyn_bed_stuy_stuyvesant_ave"],
    "Queens two-family street": ["drive_queens_forest_hills", "drive_queens_jackson_heights", "drive_queens_bayside"],
    "Bronx Grand Concourse": ["drive_bronx_grand_concourse", "drive_bronx_arthur_ave"],
}


def _comparison_scene_state(name: str) -> tuple[str, float, float]:
    """('missing' | 'no render' | 'black' | 'blown' | 'ok', mean, sd) for one comparison scene."""
    import numpy as np
    from PIL import Image

    d = VERIFICATION / "comparison" / name
    if not d.is_dir():
        return "missing", 0.0, 0.0
    render = d / "render.png"
    if not render.exists():
        return "no render", 0.0, 0.0
    a = np.asarray(Image.open(render).convert("L"), dtype=np.float32) / 255.0
    mean, sd = float(a.mean()), float(a.std())
    if mean < 0.06:
        return "black", mean, sd
    if mean > 0.94 and sd < 0.05:
        return "blown", mean, sd
    return "ok", mean, sd


def test_the_mandated_viewpoints_and_drive_areas_all_have_a_usable_comparison():
    """Brief §12 condition 3 names seven viewpoints and five drive-through areas specifically.

    The comparison lane renders more scenes than the brief asks for, so a count of usable scenes does
    not answer whether the *mandated* set is covered — a build could lose Bethesda Terrace and still
    report fifty-something scenes working. This test asks the question the brief actually asks. It
    checks that each named scene has a render that is neither black nor blown out, and a sheet and an
    assessment beside it, because a render nobody compared to the photograph is not a comparison.

    It deliberately does not judge how *well* the render matches: that is what the written assessments
    are for, and they are candid (the promenade assessment calls its own skyline "a massing study
    rather than a city"). This test guards coverage, not quality.
    """
    problems: list[str] = []
    for scene, label in MANDATED_VIEWPOINTS.items():
        state, mean, sd = _comparison_scene_state(scene)
        if state != "ok":
            problems.append(f"{label} ({scene}): {state} (mean {mean:.3f}, sd {sd:.3f})")
            continue
        for artefact in ("sheet.png", "assessment.md"):
            if not (VERIFICATION / "comparison" / scene / artefact).exists():
                problems.append(f"{label} ({scene}): renders but has no {artefact}")
    assert not problems, "mandated viewpoints without a usable comparison:\n  " + "\n  ".join(problems)

    missing_areas: list[str] = []
    for area, scenes in DRIVE_AREAS.items():
        usable = [s for s in scenes if _comparison_scene_state(s)[0] == "ok"]
        if not usable:
            states = ", ".join(f"{s}={_comparison_scene_state(s)[0]}" for s in scenes)
            missing_areas.append(f"{area}: no usable scene ({states})")
    assert not missing_areas, ("drive-through areas with no usable comparison scene:\n  "
                              + "\n  ".join(missing_areas))


def test_no_comparison_camera_is_placed_underground():
    """A verification camera below the surface it stands on renders a black frame from inside the shell.

    Two scenes failed this way. Bethesda Terrace was fixed by giving raised viewpoints `mode="local"`,
    and the 9/11 Memorial Pools by bounding how far the street percentile may reach below the point the
    camera actually stands on: the two pools are 9 m voids a few metres from the viewpoint, so the 10th
    percentile inside 10 m came out at 1.17 m against a plaza at 4.31 m and sealed the eye 1.4 m under
    the paving. This test reads each render record's own camera position back against the terrain and
    fails if any eye point is at or below the ground, which is the condition that produces the black
    frame, whatever its cause.
    """
    import numpy as np

    from nycsim_pipeline.terrain.segment_z import ZSampler

    records = sorted((VERIFICATION / "comparison").glob("*/render.json"))
    if not records:
        pytest.skip("no comparison render records")

    xs, ys, zs, slugs = [], [], [], []
    for r in records:
        try:
            rec = json.loads(r.read_text())
        except json.JSONDecodeError:
            continue
        cam = rec.get("camera") or {}
        x, y, z = cam.get("x"), cam.get("y"), cam.get("z")
        if x is None or y is None or z is None:
            continue
        xs.append(float(x)); ys.append(float(y)); zs.append(float(z)); slugs.append(r.parent.name)
    if not xs:
        pytest.skip("no render record carries a camera position")

    ground = ZSampler().sample(np.asarray(xs), np.asarray(ys))
    clearance = np.asarray(zs) - ground
    # A camera on a bridge deck, an observation floor or a terrace is legitimately far above the terrain,
    # so only the lower bound is asserted. 0.5 m is below any real eye height and well clear of the
    # sampler's own 0.384 m RMS.
    underground = [(s, float(c), float(g)) for s, c, g in zip(slugs, clearance, ground)
                   if np.isfinite(c) and c < 0.5]
    assert not underground, ("comparison cameras at or below the ground (slug, clearance m, terrain m): "
                             + ", ".join(f"{s} {c:+.2f} over {g:.2f}" for s, c, g in underground))


def test_no_comparison_sheet_is_older_than_the_content_it_shows():
    """A sheet must not predate geometry that would appear in its own frame.

    Content lands in this world in waves — New Jersey's 231,382 shells arrived long after most sheets
    were rendered — and a sheet rendered before the geometry it should show is evidence for a world that
    no longer exists. The check is deliberately narrow: a tile only counts if it is inside the frame's
    scene radius **and** within 45 degrees of the view axis, because a tile behind the camera is listed
    in the scene report but changes no pixel. That distinction matters: 26 sheets predate the New Jersey
    build and not one of them can see New Jersey, so none of them is stale.
    """
    import math

    root = VERIFICATION / "comparison"
    if not root.is_dir():
        pytest.skip("no comparison sheets")

    # Two kinds of geometry can go stale under a sheet, and both must be checked: the tile shells, and
    # the hand-built landmark models. The WTC site and the Oculus were both rebuilt after most sheets
    # were rendered, and a test that looked only at tiles would have called those sheets current.
    content: dict[str, tuple[float, float, float]] = {}   # key -> (x, y, mtime)
    for pat in ("*/tile_buildings.glb", "*/tile_buildings_nj.glb"):
        for p in (BLENDER_OUT / "tiles").glob(pat):
            t = p.parent.name
            try:
                _, tx, ty = t.split("_")
                x, y = int(tx) * 1000 + 500, int(ty) * 1000 + 500
            except ValueError:
                continue
            prev = content.get(t)
            m = p.stat().st_mtime
            content[t] = (x, y, max(prev[2], m) if prev else m)

    cat = BLENDER_OUT / "landmarks" / "catalog"
    if cat.is_dir():
        for f in sorted(cat.glob("*.json")):
            try:
                entry = json.loads(f.read_text())
            except (OSError, json.JSONDecodeError):
                continue
            origin = entry.get("origin_tm")
            glb = BLENDER_OUT / "landmarks" / f"{f.stem}.glb"
            if not origin or len(origin) < 2 or not glb.exists():
                continue
            content[f"landmark:{f.stem}"] = (float(origin[0]), float(origin[1]), glb.stat().st_mtime)

    if not content:
        pytest.skip("no tile shells or landmark models on disk")

    centres = {k: (v[0], v[1]) for k, v in content.items()}
    shells = {k: v[2] for k, v in content.items()}

    stale: list[str] = []
    for d in sorted(root.iterdir()):
        render, rec_path = d / "render.png", d / "render.json"
        if not (d.is_dir() and render.exists() and rec_path.exists()):
            continue
        try:
            rec = json.loads(rec_path.read_text())
        except json.JSONDecodeError:
            continue
        cam = rec.get("camera") or {}
        x, y = cam.get("x"), cam.get("y")
        az = cam.get("azimuth_deg", cam.get("azimuth"))
        if x is None or y is None or az is None:
            continue
        radius = rec.get("radius_m") or (rec.get("scene") or {}).get("radius_m") or 5000.0
        t_render = render.stat().st_mtime
        for tile, (cx, cy) in centres.items():
            if shells[tile] <= t_render:
                continue
            dist = math.hypot(cx - x, cy - y)
            if dist > float(radius):
                continue
            bearing = math.degrees(math.atan2(cx - x, cy - y)) % 360.0
            if abs((bearing - float(az) + 180.0) % 360.0 - 180.0) > 45.0:
                continue
            stale.append(f"{d.name}: {tile} rebuilt after the render, {dist:.0f} m away in frame")
            break
    assert not stale, "comparison sheets older than geometry in their own frame:\n  " + "\n  ".join(stale)


def test_every_deviation_reference_in_the_delivered_documents_resolves():
    """A fidelity report that cites a deviation which does not exist is not evidence, it is a footnote
    to nothing.

    The report, the definition of done and the deviations list cross-reference each other by id (A1,
    B11a, I13). Those ids are written by hand, the list is edited constantly as lanes close things, and
    a renumbering or a deletion would leave a citation pointing nowhere — in the one document whose whole
    purpose is that every claim is traceable to the thing that established it.
    """
    import re as _re

    dev_path = REPO_ROOT / "docs" / "DEVIATIONS.md"
    if not dev_path.exists():
        pytest.skip("docs/DEVIATIONS.md not produced")
    dev = dev_path.read_text()
    defined = set(_re.findall(r"^\| ([A-Z]\d+[a-z]?) \|", dev, _re.M))
    assert defined, "no deviation ids found; the table's shape must have changed"

    # An id-shaped token, but not one inside a word, a path or a hyphenated name (ADR-021, LOD2, t_-4_10).
    token = _re.compile(r"(?<![A-Za-z0-9_/-])([A-I]\d{1,2}[a-d]?)(?![A-Za-z0-9_-])")
    problems: list[str] = []
    for rel in ("docs/FIDELITY_REPORT.md", "docs/DEFINITION_OF_DONE.md", "docs/DEVIATIONS.md"):
        p = REPO_ROOT / rel
        if not p.exists():
            continue
        text = p.read_text()
        # Blank the deviations table's own id column so a definition is not read as a reference.
        body = _re.sub(r"^\| [A-Z]\d+[a-z]? \|", "| |", text, flags=_re.M)
        for ref in sorted(set(token.findall(body))):
            if ref not in defined:
                problems.append(f"{rel} cites {ref}, which no deviation defines")
    assert not problems, "dangling deviation references:\n  " + "\n  ".join(problems)


# --------------------------------------------------------------------------- orphaned data gate
#: Processed tables that no code outside their own producing module reads, each with the deviation
#: that records why. Four of these were found in one afternoon by looking, not by any test, and the
#: shape was identical every time: a stage gathered real data, wrote it, and nothing ever consumed
#: it — so nothing failed and the gap stayed invisible until someone opened a render.
#:
#: An entry here is a statement that the gap is *known and recorded*, not that it is acceptable.
#: Adding a row costs a deviation entry; that is the point.
KNOWN_ORPHANED_TABLES = {
    # Recorded as deviations. An entry here says the gap is known, not that it is acceptable.
    "transit/rail_routes.parquet": "D11 — 47 rail routes; transit.nycb has no rail section",
    "transit/rail_stops.parquet": "D11 — 1,166 rail stops, likewise",

    "osm/water_nj.parquet": "D11 — New Jersey water areas; the water stage never reads them",
    "osm/signals_stops.parquet": "D11 — duplicate of roads/cache/osm_nodes.parquet, which is what the "
                                 "signal stage actually uses",
}

#: Tables whose only reader is inside their own stage package, legitimately: a cache the stage reads
#: back, or a lookup exposed through a function rather than a path. Each entry names the function, and
#: the test checks that function still exists — so this cannot become a place to hide a real orphan.
CONSUMED_WITHIN_STAGE = {
    "traffic/sidewalk_area.parquet": ("pipeline/nycsim_pipeline/traffic/sidewalks.py",
                                      "sidewalk_area_by_nta"),
    "facade/sign_zones.parquet": ("pipeline/nycsim_pipeline/facade/signage.py", "sign_zone_bbls"),
}


def test_no_processed_table_is_written_and_never_read():
    """Data gathered, written, and consumed by nobody is the failure shape this build hit four times.

    `roofs.glb` (B6) had 1,033,416 rows pointing into a file that was never written; 986 km of rail
    structure (B13) had one consumer in the whole repository; three contracted runtime files (H6)
    were never produced at all; and the subway (D11) is 2,120 doorways to nothing. None of them made
    a test go red, because a table nobody reads cannot fail.

    This test cannot prove a table reaches the shipped world — that needs tracing, not grep. What it
    can do is force a decision: every table whose name appears nowhere outside its own stage is
    either recorded as a deviation or listed with the in-stage function that reads it. A new one
    cannot appear silently, which is the only property that was actually missing.
    """
    import subprocess

    if not PROCESSED.exists():
        pytest.skip("data/processed has not been produced")
    src_roots = [str(REPO_ROOT / d) for d in ("pipeline", "blender", "core", "services", "unreal", "tests")
                 if (REPO_ROOT / d).exists()]
    if not src_roots:
        pytest.skip("no source trees to search")

    # Top-level stage tables only: per-tile files are opened through a glob on the directory, so a
    # filename search would report every one of them as an orphan and mean nothing.
    tables: list[str] = []
    for stage_dir in sorted(p for p in PROCESSED.iterdir() if p.is_dir()):
        for f in sorted(stage_dir.iterdir()):
            if f.is_file() and f.suffix == ".parquet":
                tables.append(f"{stage_dir.name}/{f.name}")

    orphans: list[str] = []
    for rel in tables:
        stage, name = rel.split("/", 1)
        out = subprocess.run(
            ["grep", "-rl", "--include=*.py", "--include=*.cpp", "--include=*.h", "--", name, *src_roots],
            capture_output=True, text=True)
        readers = {f for f in out.stdout.split() if f and "__pycache__" not in f}
        # This file names every table it exempts, so it would otherwise count as their consumer and
        # the act of recording an orphan would hide it.
        outside = {f for f in readers
                   if f"/nycsim_pipeline/{stage}/" not in f and not f.endswith(Path(__file__).name)}
        if not outside:
            orphans.append(rel)

    accounted = set(KNOWN_ORPHANED_TABLES) | set(CONSUMED_WITHIN_STAGE)
    unrecorded = sorted(set(orphans) - accounted)
    assert not unrecorded, (
        "processed tables whose name appears nowhere outside their own stage, and which are neither "
        "recorded as a deviation nor listed with an in-stage reader:\n  " + "\n  ".join(unrecorded) +
        "\nGive the table a consumer, or record it in docs/DEVIATIONS.md and add it to "
        "KNOWN_ORPHANED_TABLES, or add it to CONSUMED_WITHIN_STAGE naming the function that reads it.")

    # The in-stage exemptions must stay true: the named function has to still exist.
    for rel, (mod, fn) in sorted(CONSUMED_WITHIN_STAGE.items()):
        src = REPO_ROOT / mod
        if not src.exists():
            continue
        assert f"def {fn}(" in src.read_text(), (
            f"{rel} is exempted because {mod}:{fn}() reads it, and that function no longer exists")

    # And the deviation list must not rot: an entry that has since gained a consumer should go, so
    # the list stays a list of real gaps rather than a graveyard.
    stale = sorted(t for t in KNOWN_ORPHANED_TABLES
                   if (PROCESSED / t).exists() and t not in orphans)
    assert not stale, (
        "KNOWN_ORPHANED_TABLES lists tables that now have a consumer; remove them:\n  " +
        "\n  ".join(stale))


def test_every_roof_mesh_reference_points_at_a_file_that_exists():
    """``roof_mesh_ref`` named ``tiles/{tile}/roofs.glb``, which no stage writes and none will (B6).

    1,033,416 buildings carried one. This was an xfail for as long as the reference was broken: the
    column's own test asserts its *format* -- non-empty exactly when ``citygml_match`` -- and a
    format test on a pointer says nothing about the pointer.

    The contract is now amended and the reference names the CityGML shard that really holds the
    building's LOD2 triangles, which is the file ``roofsteps.py`` opens, so this resolves them and
    asserts. Every CityGML roof triangle is horizontal -- the model is flat multi-level massing, not
    roof pitch -- so a ``roofs.glb`` would have carried the level outlines ``roofsteps.py`` already
    recovers and builds into the tile shells. The roof shape was never missing.
    """
    base = PROCESSED / "buildings" / "buildings_base.parquet"
    if not base.exists():
        pytest.skip("the buildings table has not been produced")
    refs = pq.read_table(base, columns=["roof_mesh_ref"])["roof_mesh_ref"].to_pylist()
    wanted = {r.split("#", 1)[0] for r in refs if r}
    n_rows = sum(1 for r in refs if r)
    assert wanted, "no building carries a roof reference at all"
    assert not any("roofs.glb" in t for t in wanted), (
        "the withdrawn tiles/{tile}/roofs.glb reference is back; DATA_CONTRACTS §5 says why it is not written")
    missing = sorted(t for t in wanted if not (BLENDER_OUT / t).exists() and not (PROCESSED / t).exists())
    assert not missing, (
        f"{n_rows} buildings reference {len(wanted)} files and {len(missing)} do not exist: {missing[:4]}")


def test_the_tile_index_content_counts_are_filled_and_agree_with_the_artefacts():
    """`index.parquet`'s four content columns were declared and never written (D12).

    They now are, and the check is against the artefacts themselves rather than against the writer:
    a count column is only worth having if it says what a tile actually holds. `n_buildings` counts
    both populations because a tile load instantiates both, which is the definition
    `runtime/export.py::_tile_row_counts` already uses — so `tiles.nycb` and `index.parquet` cannot
    drift apart.
    """
    idx = PROCESSED / "tiles" / "index.parquet"
    if not idx.exists():
        pytest.skip("the tile index has not been produced")
    t = pq.read_table(idx, columns=["tile", "n_buildings", "n_road_segments", "n_props", "n_trees"])
    by = {r["tile"]: r for r in t.to_pylist()}
    for col in ("n_buildings", "n_road_segments", "n_props", "n_trees"):
        assert sum(r[col] for r in by.values()) > 0, f"{col} is zero for every tile; it was never filled"

    # Sample rather than sweep 2,916 tiles: the point is that the number matches the file.
    import numpy as np
    rng = np.random.default_rng(11)
    have = sorted(n for n, r in by.items() if r["n_props"] or r["n_buildings"])
    for name in rng.choice(have, size=min(8, len(have)), replace=False):
        d = TILES / str(name)
        want_b = 0
        for stem in ("buildings.parquet", "buildings_nj.parquet"):
            if (d / stem).exists():
                want_b += pq.ParquetFile(d / stem).metadata.num_rows
        assert by[str(name)]["n_buildings"] == want_b, f"{name}: n_buildings disagrees with its parquet"
        pf = d / "props.parquet"
        if pf.exists():
            assert by[str(name)]["n_props"] == pq.ParquetFile(pf).metadata.num_rows, f"{name}: n_props"
            kinds = pq.read_table(pf, columns=["kind"])["kind"].to_numpy(zero_copy_only=False)
            assert by[str(name)]["n_trees"] == int((kinds == 0).sum()), f"{name}: n_trees"
        else:
            assert by[str(name)]["n_props"] == 0 and by[str(name)]["n_trees"] == 0

    # A segment can cross a tile boundary and is counted in every tile it touches, so the column
    # sums to more than the segment table holds. Stated as an assertion so the definition is pinned.
    seg = PROCESSED / "roads" / "segments.parquet"
    if seg.exists():
        total = sum(r["n_road_segments"] for r in by.values())
        assert total >= pq.ParquetFile(seg).metadata.num_rows, (
            "n_road_segments sums below the segment table, so segments crossing a tile edge are being lost")


#: Share of drivable lanes that must sit in one strongly connected component. The brief's first
#: condition is "drive from any real address to any other without interruption", and that is a
#: *directed* question: a one-way pocket you can enter and not leave breaks it while leaving the
#: undirected graph fully connected. Measured at 93.71 % when this was written; the threshold sits
#: just under so a regression fails and an improvement does not.
MIN_DRIVABLE_SCC_SHARE = 0.93


def test_the_drivable_lane_graph_is_strongly_connected_not_merely_connected():
    """`test_road_network_is_connected_enough_to_drive_across_the_city` is an *undirected* union-find.

    It passes on a graph where every street is one-way into a cul-de-sac, because ignoring direction
    makes the city look connected when no car could leave. This measures what the condition actually
    claims: over travel, bus and turn lanes, how many sit in a single strongly connected component —
    the set of lanes from which every other is reachable *and* which is reachable from every other.
    """
    p = _need(PROCESSED / "roads" / "lanes.parquet", "lane graph")
    import collections

    import numpy as np

    t = pq.read_table(p, columns=["lane_id", "kind", "successors"])
    lid = np.asarray(t["lane_id"])
    kind = np.asarray(t["kind"])
    succ = t["successors"].to_pylist()
    # DATA_CONTRACTS §7: kind 0 travel, 1 parking, 2 bike, 3 bus, 4 turn, 5 shoulder. A parking lane
    # is not a route and each one is its own component, so including them measures nothing.
    sel = np.nonzero(np.isin(kind, [0, 3, 4]))[0]
    remap = {int(lid[i]): k for k, i in enumerate(sel)}
    n = sel.size
    assert n > 0, "no drivable lanes"
    adj: list[list[int]] = [[] for _ in range(n)]
    for k, i in enumerate(sel):
        for s in (succ[i] or ()):
            j = remap.get(int(s))
            if j is not None:
                adj[k].append(j)

    # Tarjan, iterative: the recursive form overflows the stack on a 221k-node graph.
    idx = [0] * n
    low = [0] * n
    on = bytearray(n)
    comp = [-1] * n
    stack: list[int] = []
    counter = 1
    ncomp = 0
    for root in range(n):
        if idx[root]:
            continue
        work = [(root, 0)]
        while work:
            v, pi = work[-1]
            if pi == 0:
                idx[v] = low[v] = counter
                counter += 1
                stack.append(v)
                on[v] = 1
            recurse = False
            for k in range(pi, len(adj[v])):
                w = adj[v][k]
                if not idx[w]:
                    work[-1] = (v, k + 1)
                    work.append((w, 0))
                    recurse = True
                    break
                if on[w]:
                    low[v] = min(low[v], idx[w])
            if recurse:
                continue
            if low[v] == idx[v]:
                while True:
                    w = stack.pop()
                    on[w] = 0
                    comp[w] = ncomp
                    low[w] = min(low[w], low[v])
                    if w == v:
                        break
                ncomp += 1
            work.pop()
            if work:
                low[work[-1][0]] = min(low[work[-1][0]], low[v])

    sizes = collections.Counter(comp)
    largest = max(sizes.values())
    share = largest / n
    assert share >= MIN_DRIVABLE_SCC_SHARE, (
        f"only {largest:,} of {n:,} drivable lanes ({100*share:.2f} %) are mutually reachable; "
        f"a car on the other {n - largest:,} cannot drive to the rest of the city, or cannot be "
        f"reached from it")
