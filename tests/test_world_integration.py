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
import sys
import re
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

    "osm/water_nj.parquet": "D11 — New Jersey water areas; the water stage never reads them, and "
                            "7.812 km2 of what they hold is dry land in the built tiles "
                            "(test_the_new_jersey_water_gap_is_the_size_it_is_recorded_as)",
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


def test_the_new_jersey_water_gap_is_the_size_it_is_recorded_as():
    """D11 says the New Jersey water extract is wasted, not a gap.  It is a gap; this is its size.

    The claim was asserted for weeks and never measured.  Measured: the water model covers 93.46 %
    of the 130.21 km2 in ``osm/water_nj.parquet`` -- every large body, Upper New York Bay, Newark
    Bay and the Kill Van Kull among them -- and **7.812 km2 in 607 polygons falls inside tiles this
    build has generated and is dry land there**: Cedar Grove Reservoir, Packanack Lake, Orange
    Reservoir, Great Notch Reservoir, Lincoln Park Lake and 602 more.

    The test does not require the gap to be closed -- closing it needs a 4.67 GB re-download of the
    USGS products before the water stage can compute a level for each new body.  It requires the
    number in DEVIATIONS to keep matching the artefacts, in both directions: a gap that grows
    silently and a gap that is quietly closed without the entry being corrected are the same fault.
    """
    import numpy as np
    import pandas as pd
    from shapely import STRtree, wkb

    nj_path = PROCESSED / "osm" / "water_nj.parquet"
    hyd_path = PROCESSED / "water" / "hydrography.parquet"
    if not nj_path.is_file() or not hyd_path.is_file():
        pytest.skip("the osm and water stages have not both been run in this working copy")
    tiles = {p.name for p in (PROCESSED / "tiles").glob("t_*")} if (PROCESSED / "tiles").is_dir() else set()
    if not tiles:
        pytest.skip("no tiles on disk")

    hyd = pd.read_parquet(hyd_path, columns=["geometry"])
    tree = STRtree([wkb.loads(b) if isinstance(b, (bytes, bytearray)) else b for b in hyd["geometry"]])
    nj = pd.read_parquet(nj_path, columns=["area_m2", "geometry"])
    from nycsim_pipeline.tiling import TILE_SIZE_M

    covered = inside = 0.0
    n_inside = 0
    for a, blob in zip(nj["area_m2"].astype(float), nj["geometry"]):
        g = wkb.loads(blob) if isinstance(blob, (bytes, bytearray)) else blob
        c = g.representative_point()
        if len(tree.query(c, predicate="within")):
            covered += a
            continue
        tx, ty = int(np.floor(c.x / TILE_SIZE_M)), int(np.floor(c.y / TILE_SIZE_M))
        if f"t_{tx}_{ty}" in tiles:
            inside += a
            n_inside += 1
    total = float(nj["area_m2"].astype(float).sum())
    share = 100.0 * covered / total
    print(f"\nNJ water: {total / 1e6:.2f} km2 extracted, {covered / 1e6:.2f} km2 ({share:.2f} %) in the "
          f"water model, {inside / 1e6:.3f} km2 in {n_inside} polygons dry inside a built tile")
    assert 92.0 < share < 95.0, f"the covered share moved to {share:.2f} %; DEVIATIONS D11 says 93.46 %"
    assert 7.0e6 < inside < 8.6e6, \
        f"the dry-inside-a-tile area moved to {inside / 1e6:.3f} km2; DEVIATIONS D11 says 7.812"
    assert 550 <= n_inside <= 660, f"{n_inside} polygons; DEVIATIONS D11 says 607"


def test_the_architecture_does_not_claim_a_train_that_does_not_run():
    """ARCHITECTURE.md said "trains run on GTFS schedules".  Nothing runs on rails in this build.

    A gap in a document is one thing; a false statement in it is another, and this was the second.
    The test holds the correction against the artefact rather than against the prose: if a rail
    section ever appears in ``transit.nycb``, this fails and the architecture has to be rewritten to
    match -- which is the right way round.
    """
    from nycsim_pipeline.runtime.nycb import NycbReader

    arch = (Path(__file__).resolve().parents[1] / "docs" / "ARCHITECTURE.md").read_text()
    assert "trains run on GTFS schedules" not in arch or "~~Trains run on GTFS schedules.~~" in arch, \
        "ARCHITECTURE.md claims trains run; measure transit.nycb before saying so"
    assert "rail in this build is surface features only" in arch.lower() or \
           "rail in this build is surface features only" in arch, \
        "the architecture must state the rail scope rather than leave it implied"

    p = PROCESSED / "runtime" / "transit.nycb"
    if not p.is_file():
        pytest.skip("the transit runtime has not been built in this working copy")
    sections = set(NycbReader(p).sections)
    assert sections == {"bus_routes", "bus_stops", "route_stops", "vertices", "strtab"}, \
        (f"transit.nycb sections changed to {sorted(sections)}; if rail is now simulated, "
         "ARCHITECTURE.md and DEVIATIONS D11 both have to say so")


#: Prop kinds that place exactly one of their several assets, and why that is where it stands today.
#: An entry says the collapse is known and priced, not that it is right (docs/DEVIATIONS.md J58).
#: The number is the placements the single asset receives, so a silent change fails either way.
COLLAPSED_PROP_KINDS = {
    "manhole": (288_174, "no source in this build says which cover belongs to which utility; the "
                         "rows are rule-placed, so a DEP/Con Edison split would be invented"),
    "waste_basket": (5_611, "all Better Bin; DSNY replaced only part of the wire-basket stock"),
    "steam_vent": (1_402, "all the 3 m stack; the 6 m is used where the plume must clear traffic"),
    # Left this register on 2026-09-08 and each says how:
    #   bus_stop_sign  13,341  now sign_mta_bus_stop, its own asset (J58)
    #   flagpole        1,655  now 812 US and 843 city poles, split on the OSM subtype (J58)
    #   utility_pole      924  now unplaced; an 11 m pole has no asset and a sign post is not one
    #   rtpi_sign         491  now unplaced, likewise
    # and on 2026-09-09:
    #   citibike_dock   2,507  one row per station, drawn as a bicycle -> one row per part: 2,507
    #                          kiosks, 74,189 dock units and the bikes of one station_status snapshot
    #                          (Stage 40, J58; test_a_citibike_station_is_its_kiosk_and_every_one_of_its_docks)
}


def test_no_prop_kind_quietly_collapses_onto_one_of_its_assets():
    """Which asset a prop resolves to, not merely whether it resolves to one.

    ``prop_kinds_without_an_asset`` is 0 for all eight kinds below, because one asset always
    resolves -- and an id-sorted candidate list makes "wrong" look like "chosen".  That is how
    288,174 manholes became Con Edison covers and 13,832 bus stop signs became parking plates
    (docs/DEVIATIONS.md J56, J58).

    The test fails in both directions.  A kind that starts collapsing is new damage; a kind that
    stops has been fixed and its entry has to go, so the deviation record cannot drift away from
    the artefacts.
    """
    import collections

    cat_path = BLENDER_OUT / "props" / "props_asset_catalog.json"
    tiles = sorted((PROCESSED / "tiles").glob("*/props.json")) if (PROCESSED / "tiles").is_dir() else []
    if not cat_path.is_file() or not tiles:
        pytest.skip("the prop catalogue or the tile manifests have not been built")

    from nycsim_pipeline.furniture import assets as A
    from nycsim_pipeline.furniture.catalog import KINDS

    by_dk = collections.defaultdict(list)
    for e in json.loads(cat_path.read_text())["entries"]:
        by_dk[str(e.get("dataset_kind") or "")].append(e["id"])

    placed = collections.Counter()
    for f in tiles:
        d = json.loads(f.read_text())
        names = d.get("assets") or []
        key = d.get("asset_key", "a")
        for i, n in collections.Counter(r.get(key) for r in d.get("rows") or []).items():
            if isinstance(i, int) and 0 <= i < len(names):
                placed[str(names[i]).split("/")[-1].removeprefix("SM_")] += n

    # Counted per *kind*, from its own rows -- not per asset.  bus_stop_sign and rtpi_sign both
    # alias to road_sign and therefore share one asset, so an asset-side tally attributes all
    # 13,832 placements to each of them and neither number means anything.
    rows = collections.Counter()
    for f in sorted(TILES.glob("*/props.parquet")):
        t = pq.read_table(f, columns=["kind"])
        for k in t.column("kind").to_pylist():
            rows[int(k)] += 1

    found, wrong = {}, []
    for kind in KINDS:
        dk = A.PROP_KIND_ALIASES.get(kind.name, kind.name)
        ids = by_dk.get(dk or "", [])
        # Trees are chosen by species and height, not by variant, and there are 60 of them.
        if dk == "tree" or len(ids) < 2:
            continue
        used = {i for i in ids if placed.get(i, 0)}
        if len(used) == 1 and rows.get(kind.id, 0):
            found[kind.name] = rows[kind.id]
    for name, n in sorted(found.items()):
        if name not in COLLAPSED_PROP_KINDS:
            wrong.append(f"{name}: {n:,} placements now collapse onto one asset and J58 does not list it")
        elif COLLAPSED_PROP_KINDS[name][0] != n:
            wrong.append(f"{name}: {n:,} placements, J58 records {COLLAPSED_PROP_KINDS[name][0]:,}")
    for name in COLLAPSED_PROP_KINDS:
        if name not in found:
            wrong.append(f"{name}: no longer collapsed -- remove it from COLLAPSED_PROP_KINDS and J58")
    # 314,105 when J58 was written; 297,694 after 2026-09-08 took bus_stop_sign (13,341),
    # flagpole (1,655), utility_pole (924) and rtpi_sign (491) out of it; 295,187 after 2026-09-09
    # took citibike_dock (2,507) out of it.  The figure is asserted so that the register and the
    # deviation cannot drift apart in either direction.
    total = sum(n for n, _ in COLLAPSED_PROP_KINDS.values())
    assert total == 295_187, f"the recorded total moved to {total:,}; J58 says 295,187"
    assert not wrong, "prop asset selection moved:\n   " + "\n   ".join(wrong)


#: Kinds whose chosen asset is more than twice or less than half the height the kind declares, and
#: why (docs/DEVIATIONS.md J58). The catalogue states each kind's real dimensions and each asset's
#: measured ones, so this was checkable from the day both existed and nothing compared them.
#: Empty since 2026-09-08.  All three entries left it on the same day: ``bus_stop_sign`` got its own
#: 3.05 m asset, and ``utility_pole`` and ``rtpi_sign`` are unplaced rather than drawn as a 0.46 m
#: parking plate and a 2.44 m sign post (docs/DEVIATIONS.md J58).  Kept as an empty register rather
#: than deleted: the test below is what refuses the next one.
WRONG_SIZED_PROP_ASSETS: dict[str, tuple[float, float, str]] = {}


def test_no_prop_kind_is_drawn_by_an_asset_of_the_wrong_size():
    """The kind declares its dimensions and the asset carries its measured ones. Compare them.

    Nothing did, and the result is 924 eleven-metre utility poles drawn as 2.44 m sign posts and
    13,832 bus stop signs drawn as a 0.46 m parking plate. A height ratio is a blunt instrument and
    it is enough: it separates "a slightly different bench" from "a different object".
    """
    import collections

    cat_path = BLENDER_OUT / "props" / "props_asset_catalog.json"
    if not cat_path.is_file():
        pytest.skip("the prop catalogue has not been built")
    from nycsim_pipeline.furniture import assets as A
    from nycsim_pipeline.furniture.catalog import KINDS

    by_dk = collections.defaultdict(list)
    for e in json.loads(cat_path.read_text())["entries"]:
        by_dk[str(e.get("dataset_kind") or "")].append(e)

    found, wrong = {}, []
    for kind in KINDS:
        dk = A.PROP_KIND_ALIASES.get(kind.name, kind.name)
        if dk is None or dk == "tree":
            continue
        ents = sorted(by_dk.get(dk, []), key=lambda e: e["id"])
        if not ents or not kind.dims_m or not kind.dims_m[2]:
            continue
        dims = ents[0].get("dims_m") or ents[0].get("size_m")
        if not dims:
            continue
        kh, ah = float(kind.dims_m[2]), float(dims[2])
        if not kh:
            continue
        ratio = ah / kh
        if ratio < 0.5 or ratio > 2.0:
            found[kind.name] = (kh, ah)
    for name, (kh, ah) in sorted(found.items()):
        if name not in WRONG_SIZED_PROP_ASSETS:
            wrong.append(f"{name}: declares {kh:.2f} m and is drawn by a {ah:.2f} m asset, unrecorded")
        else:
            want_k, want_a, _why = WRONG_SIZED_PROP_ASSETS[name]
            if abs(want_k - kh) > 0.01 or abs(want_a - ah) > 0.01:
                wrong.append(f"{name}: {kh:.2f} m vs {ah:.2f} m, J58 records {want_k:.2f} vs {want_a:.2f}")
    for name in WRONG_SIZED_PROP_ASSETS:
        if name not in found:
            wrong.append(f"{name}: now within size -- remove it from WRONG_SIZED_PROP_ASSETS and J58")
    assert not wrong, "prop asset sizes moved:\n   " + "\n   ".join(wrong)


def test_the_plugin_source_that_can_be_compiled_here_is_compiled_here():
    """A review record is weaker evidence than a compiler, and the compiler can run on much of this.

    DEFINITION_OF_DONE says Unreal compilation cannot be executed in this container and the plugin
    is therefore "authored as complete source with a per-file review record".  That is true of the
    code that includes ``CoreMinimal.h``; it was being said of all of it.  Measured, 41 of the 101
    translation units are plain C++ -- the ``nycsim_gameplay`` adapter layer and the generated
    ``CoreUnity`` stubs that wrap ``core/src`` -- and a system compiler builds every one of them
    with ``-Wall -Wextra`` and no Unreal present.  ``GameplayPedSim.cpp`` is among them, which is
    what turned J53's 64-bit archetype mask from an argument into a compile.
    """
    import shutil
    import subprocess

    tool = REPO_ROOT / "unreal" / "tools" / "syntax_check.py"
    if not tool.is_file():
        pytest.skip("the syntax checker is absent")
    if shutil.which("g++") is None:
        pytest.skip("no C++ compiler in this environment")
    r = subprocess.run([sys.executable, str(tool)], capture_output=True, text=True, timeout=900)
    tail = (r.stdout or "").strip().splitlines()[-1:] or [""]
    assert r.returncode == 0, f"plugin source failed to compile:\n{r.stdout[-3000:]}"
    m = re.search(r"(\d+) translation units: (\d+) compile clean here, (\d+) fail, (\d+) need Unreal",
                  r.stdout)
    assert m, f"the checker's summary line changed: {tail[0]!r}"
    total, ok, failed, unreal = (int(g) for g in m.groups())
    assert failed == 0
    # A floor, not an equality: new plain-C++ files should raise it and new Unreal files should not
    # lower it.  If this fails downward, something that used to compile here has stopped.
    assert ok >= 41, f"only {ok} of {total} translation units compile here; it was 41"
    assert total == ok + failed + unreal


def test_no_prop_kind_is_drawn_by_an_object_of_a_different_kind():
    """A prop must resolve to an asset of its own kind, or to nothing at all.

    J58 found eight kinds collapsed onto one asset each, and two of those were not monotony but
    the wrong object: 13,341 MTA bus stop signs and 491 real-time passenger information signs were
    drawn as an 18 in parking regulation plate (0.23 m tall, no post), and 924 eleven-metre wooden
    utility poles as a 2.44 m galvanised U-channel sign post. The rule this enforces is the one
    ``billboard`` and ``curb_ramp`` already followed: where the kit has no asset for a kind, the
    rows stay unplaced and the sheet reports them, rather than becoming something else.
    """
    import sys
    sys.path.insert(0, str(REPO_ROOT / "pipeline"))
    from nycsim_pipeline.furniture import assets as A

    cat_path = BLENDER_OUT / "props" / "props_asset_catalog.json"
    kinds_path = REPO_ROOT / "data" / "processed" / "furniture" / "props_catalog.json"
    if not cat_path.is_file() or not kinds_path.is_file():
        pytest.skip("no built prop catalogue in this checkout")

    #: kind -> the ``dataset_kind`` its assets must carry, where the two names differ for a reason
    #: that is about vocabulary rather than about the object.
    SAME_OBJECT = {
        "bike_shelter": "bus_shelter",           # a sheltered bike corral is the same CEMUSA shell
        "subway_emergency_exit": "subway_vent_grate",   # both are the same sidewalk grating
    }
    pa = A.load(REPO_ROOT / "data" / "processed", BLENDER_OUT)
    kinds = json.loads(kinds_path.read_text())
    rows = kinds["kinds"] if isinstance(kinds, dict) and "kinds" in kinds else kinds
    wrong = []
    for k in (rows if isinstance(rows, list) else rows.values()):
        if not isinstance(k, dict) or k.get("id") is None:
            continue
        name = k["name"]
        entry, why = pa.resolve(int(k["id"]))
        if entry is None:
            continue                              # unplaced is always allowed; that is the point
        want = SAME_OBJECT.get(name, name)
        got = entry.get("dataset_kind")
        if got != want and A.KIND_TO_KIT_PIECE.get(name) is None and name != "tree":
            wrong.append(f"{name}: drawn by {entry['id']!r}, whose kind is {got!r}, not {want!r}")
    assert not wrong, "prop kinds drawn by an object of another kind:\n  " + "\n  ".join(wrong)


def test_the_flag_a_pole_flies_is_the_flag_its_row_says():
    """1,655 flagpoles all flew the city flag because the resolver took the first asset by id.

    OSM's ``subtype`` on a ``man_made=flagpole`` node says which flag is flown and is populated on
    931 of them: ``national`` 798, then regional, municipal, advertising and religious. The kit has
    a US flag and a city flag and nothing else, so ``national`` maps to the US pole and everything
    else stays on the city pole -- a state or a corporate flag drawn as either would be a
    substitution (docs/DEVIATIONS.md J58).
    """
    import sys
    sys.path.insert(0, str(REPO_ROOT / "pipeline"))
    from nycsim_pipeline.furniture import assets as A
    from nycsim_pipeline.furniture import datasets as D

    if not (BLENDER_OUT / "props" / "props_asset_catalog.json").is_file():
        pytest.skip("no built prop catalogue in this checkout")
    assert D.FLAG_VARIANT == {"national": 1}
    pa = A.load(REPO_ROOT / "data" / "processed", BLENDER_OUT)
    declared = pa.variants_by_kind.get("flagpole")
    assert declared == {0: "flag_nyc_pole", 1: "flag_us_pole"}, declared


def _kind7_rows():
    """Every kind-7 row of every tile, with its parsed attrs. Skips when the tiles are not built."""
    import sys
    sys.path.insert(0, str(REPO_ROOT / "pipeline"))
    files = sorted(TILES.glob("*/props.parquet"))
    if not files:
        pytest.skip("no built tiles in this checkout")
    cols = ["kind", "x", "y", "heading", "variant", "capacity", "attrs", "dataset_id"]
    out = {c: [] for c in cols if c != "kind"}
    out["tile"] = []
    for f in files:
        t = pq.read_table(f, columns=cols)
        k = t.column("kind").to_numpy(zero_copy_only=False)
        idx = [i for i, v in enumerate(k.tolist()) if v == 7]
        if not idx:
            continue
        sub = t.take(idx)
        for c in out:
            if c == "tile":
                out[c].extend([f.parent.name] * len(idx))
            else:
                out[c].extend(sub.column(c).to_pylist())
    out["attrs"] = [json.loads(a) if a else {} for a in out["attrs"]]
    return out


def test_a_citibike_station_is_its_kiosk_and_every_one_of_its_docks():
    """One GBFS station is one kiosk row, ``capacity`` dock rows 0.90 m apart, and bikes only from a
    ``station_status`` snapshot -- read back from the written tiles, not recomputed (DATA_CONTRACTS
    §8.1, docs/DEVIATIONS.md J58 closure, Stage 40).

    2,507 stations stood as 2,507 single bicycles before; the identity held here is
    ``rows(kind 7) == kiosks + docks + bikes`` with ``kiosks == stations``, ``docks == sum(capacity)``
    and ``bikes == sum(min(num_bikes_available, capacity))`` over the snapshot, or 0 without one.
    """
    import collections
    import math

    info_path = REPO_ROOT / "data" / "raw" / "furniture" / "citibike_gbfs_stations.json"
    status_path = REPO_ROOT / "data" / "raw" / "furniture" / "citibike_gbfs_station_status.json"
    if not info_path.is_file():
        pytest.skip("no GBFS station_information snapshot in this checkout")
    stations = json.loads(info_path.read_text())["data"]["stations"]
    cap_by_id = {str(s["station_id"]): int(s.get("capacity", 0) or 0) for s in stations
                 if s.get("lon") is not None and s.get("lat") is not None}
    n_stations, sum_cap = len(cap_by_id), sum(cap_by_id.values())
    expected_bikes, snapshot_ts = 0, None
    if status_path.is_file():
        st = json.loads(status_path.read_text())
        snapshot_ts = int(st["last_updated"])
        for s in st["data"]["stations"]:
            sid = str(s["station_id"])
            if sid in cap_by_id:
                expected_bikes += min(int(s.get("num_bikes_available", 0) or 0), cap_by_id[sid])

    rows = _kind7_rows()
    var = collections.Counter(rows["variant"])
    assert var.get(0, 0) == 0, f"{var.get(0)} kind-7 rows carry variant 0, which is never written after Stage 40"
    assert var.get(1, 0) == n_stations, f"kiosks {var.get(1, 0):,} != stations {n_stations:,}"
    assert var.get(2, 0) == sum_cap, f"dock rows {var.get(2, 0):,} != sum(capacity) {sum_cap:,}"
    assert sum(rows["capacity"]) == var[2], "capacity lives on the kiosk row: sum(capacity) over kind 7 == dock rows"
    assert var.get(3, 0) == expected_bikes, (
        f"bike rows {var.get(3, 0):,}; the station_status snapshot allows exactly {expected_bikes:,} "
        f"({'no snapshot: no bikes' if snapshot_ts is None else snapshot_ts})")
    by_station = collections.defaultdict(lambda: collections.defaultdict(list))
    for i, a in enumerate(rows["attrs"]):
        assert a.get("part") in ("kiosk", "dock", "bike"), a
        by_station[a["station_id"]][a["part"]].append(i)
        if a["part"] == "bike":
            assert a.get("snapshot_last_updated") == snapshot_ts, a
            assert rows["dataset_id"][i] == "citibike_gbfs_station_status"
        else:
            assert rows["dataset_id"][i] == "citibike_gbfs_stations"
        if a.get("axis_source") == "none":
            assert math.isnan(rows["heading"][i]), "no kerb axis -> heading NaN, by contract"
        else:
            assert a.get("axis_source") == "nearest_segment" and not math.isnan(rows["heading"][i])
    assert set(by_station) == set(cap_by_id), "station identity is attrs.station_id"
    # geometry read from the file: neighbouring docks 0.90 m apart, the kiosk one pitch past the end
    off = []
    for sid, parts in by_station.items():
        assert len(parts["kiosk"]) == 1, sid
        docks = sorted(parts["dock"], key=lambda i: rows["attrs"][i]["dock_index"])
        assert len(docks) == cap_by_id[sid], sid
        pts = [(rows["x"][i], rows["y"][i]) for i in docks]
        for (ax, ay), (bx, by) in zip(pts, pts[1:]):
            d = math.hypot(bx - ax, by - ay)
            if abs(d - 0.90) > 0.01:
                off.append((sid, d))
        if docks:
            k = parts["kiosk"][0]
            d = math.hypot(rows["x"][docks[0]] - rows["x"][k], rows["y"][docks[0]] - rows["y"][k])
            if abs(d - 0.90) > 0.01:
                off.append((sid, "kiosk", d))
        assert len(parts["bike"]) <= len(docks), sid
    assert not off, f"{len(off)} dock pitches off 0.90 m: {off[:5]}"

    # and the engine sees the same parts: every props.json placement of the three assets
    placed = collections.Counter()
    bad_reasons = collections.Counter()
    manifests = sorted(TILES.glob("*/props.json"))
    if manifests:
        for f in manifests:
            d = json.loads(f.read_text())
            names = d.get("assets") or []
            key = d.get("asset_key", "a")
            for i, n in collections.Counter(r.get(key) for r in d.get("rows") or []).items():
                if isinstance(i, int) and 0 <= i < len(names):
                    placed[str(names[i]).split("/")[-1]] += n
            for reason, n in (d.get("unresolved") or {}).items():
                if reason.startswith(("variant_unmapped", "variant_out_of_range")):
                    bad_reasons[reason] += n
        assert placed.get("SM_citibike_kiosk", 0) == n_stations, placed
        assert placed.get("SM_citibike_dock_unit", 0) == sum_cap, placed
        assert placed.get("SM_citibike_bike", 0) == expected_bikes, placed
        assert not bad_reasons, f"prop rows fell off the declared variant maps: {dict(bad_reasons)}"


#: The six dataset-placed kerb-side kinds and the facing each takes (docs/DEVIATIONS.md J84, closed):
#: heading = the compass bearing of the asset's +Y front, derived from the kerb axis (the nearest
#: roadway-class CSCL centreline within 25 m) and the side of the centreline the prop stands on.
#: ``nan_ceiling`` is the number of rows the rebuild left with no roadway segment in reach (the build
#: summary's kerb.<kind>.heading_nan), pinned as a ceiling so a regression to "all NaN" fails here.
KERB_KINDS_FACING = {
    "bus_shelter": ("away_from_roadway", 4), "bike_shelter": ("away_from_roadway", 0),
    "newsstand": ("away_from_roadway", 19), "linknyc": ("along_kerb", 0),
    "bus_stop_sign": ("along_kerb", 123), "bike_rack": ("toward_roadway", 1_141),
}
KERB_KIND_ROWS = {"bus_shelter": 3_380, "bike_rack": 9_864, "linknyc": 2_251, "newsstand": 360,
                  "bus_stop_sign": 13_341, "bike_shelter": 17}


def _kerb_rows():
    """Every row of the six kerb kinds over every tile, with parsed attrs. Skips when the tiles are not built."""
    import sys
    sys.path.insert(0, str(REPO_ROOT / "pipeline"))
    from nycsim_pipeline.furniture.catalog import KIND_ID

    files = sorted(TILES.glob("*/props.parquet"))
    if not files:
        pytest.skip("no built tiles in this checkout")
    want = {KIND_ID[n]: n for n in KERB_KINDS_FACING}
    out = {"kind": [], "x": [], "y": [], "heading": [], "attrs": []}
    for f in files:
        t = pq.read_table(f, columns=["kind", "x", "y", "heading", "attrs"])
        k = t.column("kind").to_numpy(zero_copy_only=False)
        idx = [i for i, v in enumerate(k.tolist()) if v in want]
        if not idx:
            continue
        sub = t.take(idx)
        out["kind"].extend(want[v] for v in sub.column("kind").to_pylist())
        for c in ("x", "y", "heading", "attrs"):
            out[c].extend(sub.column(c).to_pylist())
    out["attrs"] = [json.loads(a) if a else {} for a in out["attrs"]]
    return out


def _angle_diff(a: float, b: float) -> float:
    return abs((a - b + 180.0) % 360.0 - 180.0)


def test_kerb_kinds_carry_the_kerbs_heading():
    """J84's closure: every shelter, kiosk, newsstand, rack and bus stop blade with a roadway centreline
    within 25 m carries the kerb's heading and the side of the centreline it stands on; the rest are NaN
    with ``axis_source = none`` and their count is at most what the rebuild measured.

    The contract identity is checked row by row: ``heading`` is finite iff ``attrs.axis_source`` is
    ``nearest_segment`` (or the loader's own heading was kept), and then it is ``axis_deg`` itself
    (along_kerb) or one of the two perpendiculars (toward / away), with ``attrs.facing`` the kind's rule.
    """
    import collections
    import math

    rows = _kerb_rows()
    n = collections.Counter(rows["kind"])
    for name, want in KERB_KIND_ROWS.items():
        assert n[name] == want, f"{name}: {n[name]:,} rows, the catalogue count is {want:,}"
    nan = collections.Counter()
    bad = []
    for i, name in enumerate(rows["kind"]):
        a = rows["attrs"][i]
        h = rows["heading"][i]
        facing, _ceiling = KERB_KINDS_FACING[name]
        if h is None or math.isnan(h):
            nan[name] += 1
            if a.get("axis_source") != "none" or "facing" in a:
                bad.append((name, "NaN heading without axis_source none", a))
            continue
        if a.get("kept_source_heading"):
            assert a.get("heading_source"), a
            continue
        if a.get("axis_source") != "nearest_segment" or a.get("side") not in ("left", "right", "on") \
                or a.get("facing") != facing or a.get("rules") != "kerb.RULES":
            bad.append((name, "finite heading without the kerb attrs", a))
            continue
        axis = float(a["axis_deg"])
        if facing == "along_kerb":
            ok = _angle_diff(h, axis) < 0.011                      # attrs round axis_deg to 0.01
        else:
            ok = min(_angle_diff(h, axis - 90.0), _angle_diff(h, axis + 90.0)) < 0.011
        if not ok:
            bad.append((name, f"heading {h} is not {facing} of axis {axis}", a))
    assert not bad, f"{len(bad)} rows break the kerb contract; first: {bad[:3]}"
    over = {k: (nan[k], v[1]) for k, v in KERB_KINDS_FACING.items() if nan[k] > v[1]}
    assert not over, f"more NaN headings than the rebuild measured (kind: (now, ceiling)): {over}"
    assert sum(nan.values()) < 0.05 * len(rows["kind"]), "the pass wrote almost nothing"


def test_kerb_side_is_geometry_read_back_from_the_segments():
    """Recompute the side of the centreline for 500 random rows from ``roads/segments.parquet`` and the
    segment each row names in ``attrs.axis_segment_id``, and check the sign; then check that the facing
    points the way the side says (a shelter's front away from the foot of the perpendicular, a rack's
    toward it, a blade and a Link along the tangent)."""
    import math
    import random
    import sys
    sys.path.insert(0, str(REPO_ROOT / "pipeline"))
    import numpy as np
    import shapely
    from nycsim_pipeline.furniture.citibike import local_frame
    from nycsim_pipeline.furniture.kerb import side_of_centreline

    seg_path = _need(PROCESSED / "roads" / "segments.parquet", "roads/segments.parquet")
    rows = _kerb_rows()
    idx = [i for i, a in enumerate(rows["attrs"]) if a.get("axis_source") == "nearest_segment"]
    random.Random(84).shuffle(idx)
    idx = idx[:500]
    t = pq.read_table(seg_path, columns=["segment_id", "geometry"])
    want = {rows["attrs"][i]["axis_segment_id"] for i in idx}
    geom = {}
    for sid, wkb in zip(t.column("segment_id").to_pylist(), t.column("geometry").to_pylist()):
        if sid in want:
            geom[sid] = shapely.from_wkb(wkb)
    lines = np.array([geom[rows["attrs"][i]["axis_segment_id"]] for i in idx], dtype=object)
    pts = shapely.points([rows["x"][i] for i in idx], [rows["y"][i] for i in idx])
    frame = local_frame(lines, pts)
    sides = side_of_centreline(np.array([rows["x"][i] for i in idx]), np.array([rows["y"][i] for i in idx]),
                               frame["proj"], frame["tangent"])
    wrong = []
    for j, i in enumerate(idx):
        a = rows["attrs"][i]
        if sides["side"][j] != a["side"]:
            wrong.append((a, sides["side"][j]))
            continue
        h = math.radians(rows["heading"][i])
        fx, fy = math.sin(h), math.cos(h)                        # the +Y front the consumers rotate to
        vx, vy = sides["v"][j]                                   # foot of the perpendicular -> prop
        off = math.hypot(vx, vy)
        if off < 0.5:
            continue                                             # geocoded into the roadbed: a coin, counted in the summary
        dot = (fx * vx + fy * vy) / off
        tx, ty = frame["tangent"][j]
        along = abs(fx * tx + fy * ty)
        # the contract: the front is exactly perpendicular to the local axis (or exactly along it) and
        # points into the half-plane the side says. The offset vector itself is not always the
        # perpendicular -- a prop past the end of its segment projects onto the endpoint -- so only
        # its sign is tested (33 of 27,926 rows measured so, all with the right sign).
        expect = {"away_from_roadway": along < 0.011 and dot > 0, "toward_roadway": along < 0.011 and dot < 0,
                  "along_kerb": along > 0.99}[a["facing"]]
        if not expect:
            wrong.append((a, f"dot {dot:.3f} along {along:.3f}"))
    assert not wrong, f"{len(wrong)} of {len(idx)} rows disagree with the geometry: {wrong[:3]}"


def test_citibike_parts_face_away_from_the_centreline():
    """Every kiosk and dock with an axis faces the footway: its +Y front has a positive dot with the
    vector from the foot of the perpendicular on its own segment to the station point (read back from
    ``roads/segments.parquet`` for a sample), and ``attrs.side`` is what the geometry says."""
    import math
    import random
    import sys
    sys.path.insert(0, str(REPO_ROOT / "pipeline"))
    import numpy as np
    import shapely
    from nycsim_pipeline.furniture.citibike import local_frame
    from nycsim_pipeline.furniture.kerb import side_of_centreline

    seg_path = _need(PROCESSED / "roads" / "segments.parquet", "roads/segments.parquet")
    rows = _kind7_rows()
    kiosks = [i for i, a in enumerate(rows["attrs"]) if a.get("part") == "kiosk" and a.get("axis_source") == "nearest_segment"]
    assert kiosks, "no kiosk with an axis"
    assert all(rows["attrs"][i].get("facing") == "away_from_roadway" and rows["attrs"][i].get("side") in ("left", "right", "on")
               for i in kiosks), "a kiosk with an axis lacks side/facing"
    random.Random(58).shuffle(kiosks)
    sample = kiosks[:300]
    # the station point is the centre of the dock run; the kiosk stands one pitch past its end, so use the
    # docks' mean where there are docks and the kiosk itself for a capacity-0 station
    by_station = {}
    for i, a in enumerate(rows["attrs"]):
        if a.get("part") == "dock":
            by_station.setdefault(a["station_id"], []).append(i)
    px, py = [], []
    for i in sample:
        d = by_station.get(rows["attrs"][i]["station_id"], [])
        px.append(sum(rows["x"][j] for j in d) / len(d) if d else rows["x"][i])
        py.append(sum(rows["y"][j] for j in d) / len(d) if d else rows["y"][i])
    t = pq.read_table(seg_path, columns=["segment_id", "geometry"])
    want = {rows["attrs"][i]["axis_segment_id"] for i in sample}
    geom = {sid: shapely.from_wkb(w) for sid, w in zip(t.column("segment_id").to_pylist(), t.column("geometry").to_pylist()) if sid in want}
    lines = np.array([geom[rows["attrs"][i]["axis_segment_id"]] for i in sample], dtype=object)
    frame = local_frame(lines, shapely.points(px, py))
    sides = side_of_centreline(np.array(px), np.array(py), frame["proj"], frame["tangent"])
    wrong = []
    for j, i in enumerate(sample):
        a = rows["attrs"][i]
        vx, vy = sides["v"][j]
        off = math.hypot(vx, vy)
        if sides["side"][j] != a["side"]:
            wrong.append((a["station_id"], "side", a["side"], sides["side"][j]))
        if off < 0.5:
            continue
        h = math.radians(rows["heading"][i])
        dot = (math.sin(h) * vx + math.cos(h) * vy) / off
        tx, ty = frame["tangent"][j]
        along = abs(math.sin(h) * tx + math.cos(h) * ty)
        if along > 0.011 or dot <= 0:                         # perpendicular to the axis, into the footway half-plane
            wrong.append((a["station_id"], "front", round(dot, 3), round(along, 3)))
    assert not wrong, f"{len(wrong)} of {len(sample)} stations do not face away from their centreline: {wrong[:5]}"


def test_unreal_yaw_puts_the_front_at_the_compass_heading():
    """``build_levels.heading_to_yaw`` under the project's frame (X east, Y = -north, yaw clockwise from
    +X): the forward vector must be the unit vector of the compass heading for the four cardinal cases,
    which is the same picture ``blender/verify/scene.py`` draws with ``yaw = -heading``. Read from the
    source with ast so the ``unreal`` import is not needed."""
    import ast
    import math

    src = (REPO_ROOT / "unreal" / "NYCSim" / "Content" / "Python" / "build_levels.py").read_text()
    tree = ast.parse(src)
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "heading_to_yaw")
    ns: dict = {}
    exec(compile(ast.Module(body=[fn], type_ignores=[]), "build_levels.heading_to_yaw", "exec"), ns)
    heading_to_yaw = ns["heading_to_yaw"]
    for heading, (east, north) in {0.0: (0, 1), 90.0: (1, 0), 180.0: (0, -1), 270.0: (-1, 0)}.items():
        yaw = math.radians(heading_to_yaw(heading))
        ue_x, ue_y = math.cos(yaw), math.sin(yaw)          # UE forward in the X-east / Y-south plane
        assert abs(ue_x - east) < 1e-9 and abs(-ue_y - north) < 1e-9, (heading, ue_x, ue_y)
        # Blender: rotate +Y by -heading about +Z
        b = math.radians(-heading)
        bx, by = -math.sin(b), math.cos(b)
        assert abs(bx - east) < 1e-9 and abs(by - north) < 1e-9, (heading, bx, by)


def test_the_engines_prop_manifest_is_not_older_than_the_props_it_lists():
    """There are two prop artefacts per tile and only one stage writes each.

    ``props.parquet`` is the furniture stage's output and what the Blender comparison renderer
    reads. ``props.json`` is the Unreal manifest stage's output and what the engine reads and the
    content package ships. A furniture rebuild refreshes the first and not the second, so on
    2026-09-08 the renders carried the J58 fixes and a player would not: the manifests still named
    13,832 parking plates where the bus stops are and 924 sign posts where the utility poles were,
    and no US flag anywhere.

    Nothing failed over it -- both files were internally valid and both counts were right about
    their own contents. Only their *dates* disagreed, which is what this checks.
    """
    tiles = sorted((PROCESSED / "tiles").glob("*/props.parquet"))
    if not tiles:
        pytest.skip("no built tiles in this checkout")
    #: A manifest written in the same run may finish a little before or after the parquet it
    #: describes; a stage that was not re-run at all is hours behind.
    SLACK_S = 20 * 60
    stale = []
    checked = 0
    for pq_path in tiles:
        js = pq_path.with_name("props.json")
        if not js.is_file():
            continue                     # a tile with no manifest is a different question
        checked += 1
        behind = pq_path.stat().st_mtime - js.stat().st_mtime
        if behind > SLACK_S:
            stale.append(f"{pq_path.parent.name}: props.json is {behind / 3600:.1f} h older "
                         f"than props.parquet")
    assert checked, "no tile carries both a props.parquet and a props.json"
    assert not stale, (
        f"{len(stale)} of {checked} tiles have an engine manifest older than their prop data; "
        f"re-run `python3 -m nycsim_pipeline.unreal.manifest` after any furniture rebuild:\n  "
        + "\n  ".join(stale[:8]))


def test_no_elevation_carries_more_tiers_of_windows_than_its_own_typology_allows():
    """A spire's height must not reach the published facade as rows of windows.

    `buildings_base.floors` is a real PLUTO count for some buildings and, for the rest, the derivation
    `height / class storey height`, published honestly as `floors_source = SRC_HEIGHT_TO_FLOORS`. The
    derivation is sound wherever the height belongs to a stack of storeys. It is a category error where the
    height belongs to something else, and the facade stage then draws that many rows of windows: Old First
    Reformed Church (BIN 3020373, 63.07 m to the top of its steeple) came out of it with 16 floors and
    15 x 14 = 210 window bays, a wooden gravity tank and two rooftop bulkheads. City-wide that put 91,217
    window openings on elevations that are not storey stacks — churches, elevated stations, big-box walls
    and fuel canopies (docs/DEVIATIONS.md J68).

    This test reads the published table, not the code that wrote it: for the five classes named in
    `derive.NOT_A_STOREY_STACK` no row may carry more `window_rows` than the class's own `floors_typical`
    maximum allows, and neither church class may carry a rooftop tank.
    """
    import numpy as np

    from nycsim_pipeline.facade import derive as D
    from nycsim_pipeline.facade import enums as E

    attrs = _need(PROCESSED / "facade" / "facade_attrs.parquet", "facade attributes")
    t = pq.read_table(attrs, columns=["bin", "facade_class", "window_rows", "window_cols", "has_water_tower"])
    fc = np.asarray(t["facade_class"]).astype(np.int64)
    rows = np.asarray(t["window_rows"]).astype(np.int64)
    cols = np.asarray(t["window_cols"]).astype(np.int64)
    tank = np.asarray(t["has_water_tower"].to_pylist(), dtype=bool)
    bins = np.asarray(t["bin"]).astype(np.int64)
    ids = {c["facade_class"]: c["id"] for c in E.load_classes()}

    bad: list[str] = []
    for k in sorted(D.NOT_A_STOREY_STACK):
        allowed = max(int(D.CLASS.max_storeys[k]) - 1, 0)
        over = np.where((fc == k) & (rows > allowed))[0]
        if len(over):
            worst = over[int(np.argmax(rows[over] * cols[over]))]
            bad.append(f"{ids.get(k, k)} (class {k}): {len(over)} buildings above {allowed} tier(s); "
                       f"worst BIN {int(bins[worst])} with {int(rows[worst])} x {int(cols[worst])} "
                       f"= {int(rows[worst] * cols[worst])} openings")
    assert not bad, "windows drawn on an elevation that is not a storey stack:\n  " + "\n  ".join(bad)

    church = np.isin(fc, [35, 36]) & tank
    assert not church.any(), (
        f"{int(church.sum())} churches carry a rooftop gravity tank; the storey count that made them "
        f"eligible is a spire height divided by a storey height")


def test_the_citys_canopy_stands_at_the_height_the_tree_census_measured():
    """2,248 km of surplus canopy, and every street frame in the project was drawn under it.

    A street tree row carries `species` and `dbh_cm` from the 2015 census, and
    `furniture/allometry.py` turns the trunk diameter into a height by a published species curve.
    Until J70 that height only chose one of three exported sizes -- on bin edges of 7 m and 12 m --
    and the instance was then drawn at whatever height the kit had exported, because
    `scene.add_props` places a prop by translation and yaw alone. A pin oak's three assets stand at
    11.8, 18.3 and 22.6 m and a plane tree's at 20.7, 24.0 and 27.7 m, so a tree measured at 8 m
    stood 18.3 or 24.0 m over the pavement. Across the 651,023 trees that carry both a species and
    a height the median asset was **1.26x** the measured height, **185,837 (28.5 %)** were 1.5x or
    more and **62,997 (9.7 %)** were at least twice it (docs/DEVIATIONS.md J70).

    The fix uses the number that was already there: the nearest exported size is chosen by its own
    height and the remainder is taken up by a uniform instance scale. This test reads the published
    rows and the published catalogue and checks the tree that *would be drawn*, so it fails if the
    resolver, the catalogue or the census move apart again.
    """
    import numpy as np

    from nycsim_pipeline.furniture import assets as A

    idx = A.load(PROCESSED, BLENDER_OUT)
    if not idx.asset_height_m or not idx.kind_names:
        pytest.skip("prop catalogues not produced yet")
    files = sorted(TILES.glob("*/props.parquet"))
    if not files:
        pytest.skip("tile props not produced yet")

    ratios: list[float] = []
    out_of_band = 0
    for path in files[::7]:                       # every seventh tile: 235 of 1,648, ~90k trees
        t = pq.read_table(path, columns=["species", "height_m"])
        species = t["species"].to_pylist()
        heights = np.asarray(t["height_m"])
        for i, sp in enumerate(species):
            h = heights[i]
            if not sp or h is None or not np.isfinite(h) or h <= 0:
                continue
            entry, why, scale = idx.tree_asset(sp, float(h))
            if entry is None:
                continue
            asset_h = idx.asset_height_m.get(entry["id"])
            if not asset_h:
                continue
            if why.endswith(":scale_out_of_band"):
                out_of_band += 1
                continue
            ratios.append(asset_h * scale / float(h))

    assert len(ratios) > 10_000, f"only {len(ratios)} trees sampled; the check is not meaningful"
    r = np.asarray(ratios)
    worst = float(np.abs(r - 1.0).max())
    assert worst < 0.02, (
        f"a tree is drawn {r[np.argmax(np.abs(r - 1.0))]:.2f}x its measured height; "
        f"the census height must reach the frame, not just choose a bin")
    # The band is a declared limit, not a silent one: it may not swallow a large share of the city.
    share = out_of_band / max(len(ratios) + out_of_band, 1)
    assert share < 0.01, (
        f"{share:.2%} of trees fall outside the {A.TREE_SCALE_MIN}-{A.TREE_SCALE_MAX} scale band "
        f"and keep the asset's own size; the band or the kit's sizes need revisiting")
