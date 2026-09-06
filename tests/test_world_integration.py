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
from nycsim_pipeline.paths import BLENDER_OUT, PROCESSED, REPO_ROOT  # noqa: E402

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
        if known and d.get("kit_ids"):
            unknown = [k for k in d["kit_ids"] if k not in known]
            assert not unknown, f"{h.parent.name} references kit ids absent from the catalog: {unknown[:5]}"

    # Every tile that holds buildings should hold placements: a building needs windows.
    with_buildings = sum(1 for h in headers if (h.parent / "buildings.parquet").exists())
    assert populated > 0, (
        f"all {len(headers)} kit placement files are empty — the emit stage produced no placements at all")
    assert populated >= 0.9 * with_buildings, (
        f"only {populated} of {with_buildings} tiles with buildings carry placements")
    assert total_records > 1_000_000, (
        f"only {total_records:,} placements city-wide for over a million buildings — far too few to be windows")


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
                         r"|must be deleted|keeps them out", re.I)

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
