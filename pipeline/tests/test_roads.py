"""Tests for the roads stage (DATA_CONTRACTS §7 and §15).

Unit tests run anywhere. The tests that read ``data/processed/roads/*`` skip when the stage has not been run.
"""
from __future__ import annotations

import json
import math
import struct
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest
import shapely
from PIL import Image

from nycsim_pipeline.contracts import validate_parquet
from nycsim_pipeline.crs import NYC_TM, SCOPE_XMAX, SCOPE_XMIN, SCOPE_YMAX, SCOPE_YMIN
from nycsim_pipeline.paths import PROCESSED
from nycsim_pipeline.roads import bridges as B
from nycsim_pipeline.roads import geom as G
from nycsim_pipeline.roads import graph as GR
from nycsim_pipeline.roads import lanes as L
from nycsim_pipeline.roads import pavement as PV
from nycsim_pipeline.roads import schema as S
from nycsim_pipeline.roads import signals as SIG
from nycsim_pipeline.roads import signs as SN
from nycsim_pipeline.roads.apply_terrain_z import TerrainSampler
from nycsim_pipeline.roads.names import core_tokens, display, normalize
from nycsim_pipeline.runtime import export as E
from nycsim_pipeline.runtime.nycb import NycbError, NycbReader, NycbWriter, aligned_dtype
from nycsim_pipeline.tiling import Tile

ROADS = PROCESSED / "roads"
RUNTIME = PROCESSED / "runtime"
SEGMENTS = ROADS / "segments.parquet"
NODES = ROADS / "nodes.parquet"
LANES = ROADS / "lanes.parquet"
JUNCTION_LANES = ROADS / "junction_lanes.parquet"
SIGNALS = ROADS / "signals.parquet"
SIGNS = ROADS / "signs.parquet"
BRIDGES = ROADS / "bridges_tunnels.json"
CONNECTIVITY = ROADS / "connectivity.json"

# DATA_CONTRACTS §7 storage types, spelled out here so a drift in schema.py is caught by this file.
SEGMENT_TYPES: dict[str, pa.DataType] = {
    "segment_id": pa.int64(), "from_node": pa.int64(), "to_node": pa.int64(), "street_name": pa.string(),
    "rw_type": pa.int8(), "traffic_dir": pa.int8(), "travel_lanes": pa.int8(), "park_lanes": pa.int8(),
    "total_lanes": pa.int8(), "width_m": pa.float32(), "posted_speed_mph": pa.int8(), "bike_lane": pa.int8(),
    "bus_lane": pa.bool_(), "truck_route": pa.int8(), "level_from": pa.int8(), "level_to": pa.int8(),
    "surface": pa.int8(), "borough": pa.int8(), "speed_source": pa.int8(), "lanes_source": pa.int8(),
}


def _need(p: Path):
    if not p.exists():
        pytest.skip(f"{p} not built yet")
    return p


# --------------------------------------------------------------------------- names
def test_name_normalisation_unifies_the_source_spellings():
    assert normalize("East 168 Street") == normalize("EAST 168 STREET") == normalize("E  168 ST") == "E 168 ST"
    assert normalize("East 168th Street") == "E 168 ST"
    assert normalize("Avenue of the Americas") == "6 AVE"
    assert normalize("Fifth Avenue") == "5 AVE"
    assert normalize("Pelham Pkwy") == normalize("PELHAM PARKWAY") == "PELHAM PKWY"
    assert normalize("Brooklyn-Battery Tunnel") == "HUGH L CAREY TUNL"
    assert normalize("Ed Koch Queensboro Bridge") == "QUEENSBORO BR"
    assert normalize(None) == "" and normalize("nan") == ""
    assert core_tokens("E 60 ST") == "60 ST"
    assert core_tokens("GRAND CONC NB") == "GRAND CONC"
    assert display("  west   60  street ") == "WEST 60 STREET"


# --------------------------------------------------------------------------- schema helpers
def test_level_code_to_height():
    assert S.level_to_z(S.LEVEL_AT_GRADE) == pytest.approx(0.0)
    assert float(S.level_to_z(17)) == pytest.approx(S.Z_PER_LEVEL_M)
    assert float(S.level_to_z(9)) == pytest.approx(-S.Z_PER_LEVEL_M)
    # out-of-domain codes fall back to grade rather than producing a wild height
    assert float(S.level_to_z(0)) == pytest.approx(0.0)
    assert float(S.level_to_z(99)) == pytest.approx(0.0)


def test_string_type_normalisation_matches_the_contract_validator(tmp_path):
    df = pd.DataFrame({"a": pd.array(["x", "y"], dtype="str"), "b": [[1, 2], [3]], "c": [1.0, 2.0]})
    t = S.normalize_string_types(pa.Table.from_pandas(df, preserve_index=False))
    assert pa.types.is_string(t.schema.field("a").type)
    assert pa.types.is_list(t.schema.field("b").type)


# --------------------------------------------------------------------------- geometry
def test_offset_polyline_is_exactly_d_metres_to_the_right():
    c = np.array([[0.0, 0.0, 0.0], [100.0, 0.0, 0.0], [200.0, 0.0, 0.0]])
    right = G.offset_polyline(c, 3.0)
    assert np.allclose(right[:, 1], -3.0)            # +x heading -> right is -y
    left = G.offset_polyline(c, -3.0)
    assert np.allclose(left[:, 1], 3.0)
    line = shapely.LineString(c[:, :2])
    assert shapely.LineString(right[:, :2]).distance(line) == pytest.approx(3.0, abs=1e-6)


def test_offset_polyline_miters_a_corner_without_blowing_up():
    c = np.array([[0.0, 0.0, 0.0], [50.0, 0.0, 0.0], [50.0, 50.0, 0.0]])
    off = G.offset_polyline(c, 3.0)
    d = np.hypot(off[1, 0] - c[1, 0], off[1, 1] - c[1, 1])
    assert 3.0 <= d <= 3.0 * G.MITER_LIMIT + 1e-9


def test_bezier_connector_leaves_and_arrives_on_the_given_headings():
    p0, p3 = np.array([0.0, 0.0, 0.0]), np.array([30.0, 30.0, 3.0])
    g = G.bezier_connector(p0, 0.0, p3, 90.0, n=501)
    assert np.allclose(g[0], p0) and np.allclose(g[-1], p3)
    # the first/last chord of a finely sampled curve approaches the requested tangent
    assert G.heading_math(*(g[1, :2] - g[0, :2])) == pytest.approx(0.0, abs=0.5)
    assert G.heading_math(*(g[-1, :2] - g[-2, :2])) == pytest.approx(90.0, abs=0.5)
    assert g[0, 2] == pytest.approx(0.0) and g[-1, 2] == pytest.approx(3.0)
    # a straight connector between aligned headings stays straight
    straight = G.bezier_connector(np.array([0.0, 0.0, 0.0]), 0.0, np.array([20.0, 0.0, 0.0]), 0.0, n=5)
    assert np.allclose(straight[:, 1], 0.0)


def test_heading_conventions_round_trip():
    for d in (0.0, 45.0, 90.0, 180.0, 275.0):
        assert G.math_to_compass(G.compass_to_math(d)) == pytest.approx(d)
    assert G.math_to_compass(0.0) == pytest.approx(90.0)      # east
    assert G.math_to_compass(90.0) == pytest.approx(0.0)      # north
    assert G.angle_diff(350.0, 10.0) == pytest.approx(20.0)
    assert G.angle_diff(10.0, 350.0) == pytest.approx(-20.0)


# --------------------------------------------------------------------------- lane cross-sections
@pytest.mark.parametrize("width,travel,park,tdir", [
    (18.0, 4, 2, S.DIR_TWO_WAY), (9.144, 2, 2, S.DIR_TWO_WAY), (12.0, 3, 1, S.DIR_FORWARD),
    (7.0, 1, 0, S.DIR_BACKWARD), (30.0, 6, 2, S.DIR_TWO_WAY), (6.0, 2, 2, S.DIR_TWO_WAY),
])
def test_cross_section_fits_the_real_curb_to_curb_width(width, travel, park, tdir):
    stack = L.cross_section(width, travel, park, tdir, S.BIKE_NONE, "")
    assert stack
    total = sum(x["width"] for x in stack)
    assert total <= width + 1e-6
    offs = [x["offset"] for x in stack]
    assert min(offs) - stack[int(np.argmin(offs))]["width"] / 2 >= -width / 2 - 1e-6
    assert max(offs) + stack[int(np.argmax(offs))]["width"] / 2 <= width / 2 + 1e-6
    assert offs == sorted(offs)                       # ordered left curb -> right curb
    if tdir == S.DIR_FORWARD:
        assert all(x["direction"] == 1 for x in stack)
    if tdir == S.DIR_BACKWARD:
        assert all(x["direction"] == -1 for x in stack)
    if tdir == S.DIR_TWO_WAY:
        assert {x["direction"] for x in stack if x["kind"] == S.LANE_TRAVEL} == {-1, 1}


def test_cross_section_places_a_protected_bike_lane_at_the_curb():
    stack = L.cross_section(15.0, 2, 2, S.DIR_TWO_WAY, S.BIKE_PROTECTED, "TW")
    kinds = [x["kind"] for x in stack]
    assert kinds[0] == S.LANE_BIKE and kinds[-1] == S.LANE_BIKE
    standard = L.cross_section(15.0, 2, 2, S.DIR_TWO_WAY, S.BIKE_STANDARD, "TW")
    ks = [x["kind"] for x in standard]
    assert ks[0] == S.LANE_PARKING and ks[1] == S.LANE_BIKE       # standard lane sits inside the parked cars


def test_cross_section_never_emits_an_unusable_lane():
    for width in np.arange(2.0, 20.0, 0.25):
        for travel, park, bike in ((1, 0, S.BIKE_NONE), (2, 2, S.BIKE_NONE), (4, 2, S.BIKE_PROTECTED), (3, 1, S.BIKE_STANDARD)):
            stack = L.cross_section(float(width), travel, park, S.DIR_TWO_WAY, bike, "TW")
            for lane in stack:
                assert lane["width"] >= L.MIN_W[lane["kind"]] - 1e-9, (width, travel, park, lane)
            assert any(l["kind"] in (S.LANE_TRAVEL, S.LANE_TURN) for l in stack), (width, travel)


def test_narrow_street_loses_its_parking_before_its_travel_lanes():
    wide = L.cross_section(15.0, 2, 2, S.DIR_TWO_WAY, S.BIKE_NONE, "")
    assert sum(1 for l in wide if l["kind"] == S.LANE_PARKING) == 2
    narrow = L.cross_section(6.0, 2, 2, S.DIR_TWO_WAY, S.BIKE_NONE, "")
    assert sum(1 for l in narrow if l["kind"] == S.LANE_PARKING) == 0
    assert sum(1 for l in narrow if l["kind"] == S.LANE_TRAVEL) == 2
    assert sum(l["width"] for l in narrow) <= 6.0 + 1e-9
    assert L.expected_lanes(2, 2, S.DIR_TWO_WAY, S.BIKE_NONE, "") == 4


def test_cross_section_is_empty_where_no_vehicle_may_go():
    assert L.cross_section(9.0, 2, 0, S.DIR_NONE, S.BIKE_NONE, "") == []
    assert L.cross_section(9.0, 0, 0, S.DIR_TWO_WAY, S.BIKE_NONE, "") == []


def test_lane_ids_are_unique_per_segment():
    ids = {L.lane_id(1234, i) for i in range(-15, 16)}
    assert len(ids) == 31
    assert L.lane_id(1234, 0) != L.lane_id(1235, 0)


# --------------------------------------------------------------------------- signals
def test_signal_phases_close_the_cycle_exactly():
    legs = [SIG.Leg(1, "A ST", 0.0, 2, 2, 12.0, S.RW_STREET, S.DIR_TWO_WAY),
            SIG.Leg(2, "A ST", 180.0, 2, 2, 12.0, S.RW_STREET, S.DIR_TWO_WAY),
            SIG.Leg(3, "B AVE", 90.0, 2, 2, 18.0, S.RW_STREET, S.DIR_TWO_WAY),
            SIG.Leg(4, "B AVE", 270.0, 2, 2, 18.0, S.RW_STREET, S.DIR_TWO_WAY)]
    groups = SIG._group_legs(legs)
    assert set(groups.values()) == {0, 1}
    for cycle, lpi, barnes in ((60.0, False, False), (90.0, True, False), (60.0, True, True)):
        c, phases, _ = SIG._phases(legs, groups, cycle, lpi, barnes)
        total = sum(p["lpi_s"] + p["green_s"] + p["yellow_s"] + p["allred_s"] for p in phases if p["group"] >= 0)
        if barnes:
            total += phases[-1]["ped_walk_s"] + phases[-1]["ped_flash_s"]
        assert total == pytest.approx(c, abs=0.02)
        for p in phases:
            assert p["green_s"] >= 0.0 and p["ped_walk_s"] > 0.0
        if lpi:
            assert all(p["lpi_s"] == SIG.LPI_S for p in phases if p["group"] >= 0)


def test_signal_group_assignment_puts_the_heavier_street_first():
    legs = [SIG.Leg(1, "SMALL ST", 0.0, 1, 1, 8.0, S.RW_STREET, S.DIR_TWO_WAY),
            SIG.Leg(2, "SMALL ST", 180.0, 1, 1, 8.0, S.RW_STREET, S.DIR_TWO_WAY),
            SIG.Leg(3, "BIG AVE", 90.0, 3, 3, 20.0, S.RW_STREET, S.DIR_TWO_WAY),
            SIG.Leg(4, "BIG AVE", 270.0, 3, 3, 20.0, S.RW_STREET, S.DIR_TWO_WAY)]
    groups = SIG._group_legs(legs)
    assert groups[3] == groups[4] == 0 and groups[1] == groups[2] == 1


# --------------------------------------------------------------------------- signs
def test_sign_sheet_size_parsing():
    assert SN.parse_size("018 X 012") == pytest.approx((12 * 0.0254, 18 * 0.0254))
    assert SN.parse_size("020 DIAMETER") == pytest.approx((20 * 0.0254, 20 * 0.0254))
    assert SN.parse_size("14.12 X 6") == pytest.approx((6 * 0.0254, 14.12 * 0.0254))
    assert SN.parse_size("") == (0.0, 0.0)
    assert SN.parse_size("garbage") == (0.0, 0.0)


def test_mutcd_family_classification():
    assert SN.mutcd_family("PS-1G", "NO STANDING ANYTIME <->") == "R7"
    assert SN.mutcd_family("SP-477B", "BUS STOP SIGN (BUS & HANDICAP SYMBOLS) NO STANDING") == "R8"
    assert SN.mutcd_family("SI-1878G", "LOCAL MTA BUS ROUTE PANEL") == "I"
    assert SN.mutcd_family("R7-1", "NO PARKING") == "R7"
    assert SN.mutcd_family("W14-1", "DEAD END") == "W"
    assert SN.mutcd_family("R1-1", "STOP") == "R1"


def test_stack_z_puts_the_lowest_sign_at_the_mutcd_minimum():
    base = np.zeros(3)
    h = np.array([0.457, 0.457, 0.152])
    group = np.array([0, 0, 0])
    z = SN._stack_z(base, h, group)
    assert z[0] == pytest.approx(SN.POLE_BOTTOM_M + h[0] / 2)
    assert z[1] > z[0] and z[2] > z[1]
    assert z.max() <= SN.MAX_MOUNT_M + 1e-9


# --------------------------------------------------------------------------- bridges
def test_bridge_name_matcher_accepts_qualifiers_and_rejects_neighbours():
    assert B._matches("BROOKLYN BR", ["BROOKLYN BR"], [])
    assert B._matches("BROOKLYN BR PED PATH", ["BROOKLYN BR"], [])
    assert not B._matches("FDR DR NB EN BROOKLYN BR", ["BROOKLYN BR"], [])
    assert not B._matches("BROADWAY", ["BROADWAY BR"], [])
    assert B._matches("WASHINGTON BR BIKE PATH", ["WASHINGTON BR"], [])
    assert not B._matches("GEORGE WASHINGTON BR", ["WASHINGTON BR"], [])
    assert not B._matches("HIGH BR PARK PATH", ["HIGH BR"], ["PARK"])
    assert B._matches("HIGH BR", ["HIGH BR"], ["PARK"])
    assert not B._matches("WHITESTONE EXPY", ["WHITESTONE BR"], ["EXPY"])


def test_every_required_crossing_has_a_pattern():
    names = {s["name"].lower() for s in B.STRUCTURES}
    blob = " | ".join(names)
    for required in ("brooklyn", "manhattan", "williamsburg", "queensboro", "triborough", "george washington",
                     "verrazzano", "throgs neck", "whitestone", "pulaski", "kosciuszko", "high bridge",
                     "lincoln", "holland", "queens-midtown", "carey"):
        assert required in blob, required
    assert len({s["id"] for s in B.STRUCTURES}) == len(B.STRUCTURES)


# --------------------------------------------------------------------------- pavement
def test_clip_to_tiles_splits_and_conserves_area():
    poly = shapely.box(-10.0, -10.0, 1500.0, 900.0)          # spans t_-1_-1, t_0_-1, t_-1_0, t_0_0, t_1_0
    g, attrs, tx, ty = PV._clip_to_tiles(np.array([poly], dtype=object), {"src": np.array(["a"])})
    assert len(g) >= 4
    assert sum(shapely.area(g)) == pytest.approx(poly.area, rel=1e-9)
    for gi, x, y in zip(g, tx, ty):
        b = shapely.bounds(gi)
        assert b[0] >= x * 1000 - 1e-6 and b[2] <= (x + 1) * 1000 + 1e-6
        assert b[1] >= y * 1000 - 1e-6 and b[3] <= (y + 1) * 1000 + 1e-6
    assert set(attrs["src"]) == {"a"}


def test_clip_to_tiles_leaves_a_single_tile_polygon_untouched():
    poly = shapely.box(100.0, 100.0, 200.0, 200.0)
    g, _, tx, ty = PV._clip_to_tiles(np.array([poly], dtype=object), {"src": np.array(["a"])})
    assert len(g) == 1 and int(tx[0]) == 0 and int(ty[0]) == 0
    assert g[0].equals(poly)


# --------------------------------------------------------------------------- A*
def _grid_network(one_way_col: int | None = None) -> tuple[gpd.GeoDataFrame, pd.DataFrame]:
    """5x5 grid, 100 m spacing. Node id = row * 10 + col."""
    rows: list[dict] = []
    geoms: list = []
    sid = 1
    for r in range(5):
        for c in range(5):
            if c < 4:
                rows.append({"segment_id": sid, "from_node": r * 10 + c, "to_node": r * 10 + c + 1, "traffic_dir": S.DIR_TWO_WAY})
                geoms.append(shapely.LineString([(c * 100, r * 100, 0), ((c + 1) * 100, r * 100, 0)]))
                sid += 1
            if r < 4:
                td = S.DIR_FORWARD if (one_way_col is not None and c == one_way_col) else S.DIR_TWO_WAY
                rows.append({"segment_id": sid, "from_node": r * 10 + c, "to_node": (r + 1) * 10 + c, "traffic_dir": td})
                geoms.append(shapely.LineString([(c * 100, r * 100, 0), (c * 100, (r + 1) * 100, 0)]))
                sid += 1
    seg = gpd.GeoDataFrame(rows, geometry=geoms, crs=NYC_TM)
    seg["drivable"] = True
    seg["length_m"] = seg.geometry.length.astype(np.float32)
    seg["posted_speed_mph"] = np.int8(25)
    seg["street_name"] = "GRID ST"
    seg["name_norm"] = "GRID ST"
    seg["borough"] = np.int8(1)
    seg["rw_type"] = np.int8(S.RW_STREET)
    ids = sorted({*seg["from_node"], *seg["to_node"]})
    nodes = pd.DataFrame({"node_id": ids, "x": [float((i % 10) * 100) for i in ids],
                          "y": [float((i // 10) * 100) for i in ids]})
    nodes["names_norm"] = [["GRID ST"] for _ in ids]
    nodes["degree_drivable"] = 4
    nodes["borough"] = np.int8(1)
    return seg, nodes


def test_astar_finds_the_shortest_grid_route():
    seg, nodes = _grid_network()
    g = GR.RoadGraph(seg, nodes)
    r = g.astar(0, 44)
    assert r.found
    assert r.distance_m == pytest.approx(800.0)      # 4 east + 4 north, 100 m each
    assert len(r.segments) == 8
    assert r.nodes[0] == 0 and r.nodes[-1] == 44


def test_astar_respects_one_way_arcs():
    seg, nodes = _grid_network()
    g = GR.RoadGraph(seg, nodes)
    down = g.astar(44, 4)
    assert down.found and down.distance_m == pytest.approx(400.0)
    # now make every north-south segment of column 4 one-way northbound: going south must detour
    seg2, nodes2 = _grid_network(one_way_col=4)
    g2 = GR.RoadGraph(seg2, nodes2)
    r = g2.astar(44, 4)
    assert r.found and r.distance_m > 400.0


def test_astar_reports_failure_for_a_disconnected_pair():
    seg, nodes = _grid_network()
    nodes = pd.concat([nodes, pd.DataFrame({"node_id": [99], "x": [9999.0], "y": [9999.0],
                                            "names_norm": [["ISLAND ST"]], "degree_drivable": [0], "borough": [np.int8(1)]})],
                      ignore_index=True)
    g = GR.RoadGraph(seg, nodes)
    assert not g.astar(0, 99).found


def test_one_way_audit_measures_the_travel_bearing():
    seg, nodes = _grid_network(one_way_col=0)
    a = GR.one_way_audit(seg, "GRID ST", 1, 0.0)
    assert a["one_way_segments"] == 4
    assert a["mean_travel_bearing"] == pytest.approx(0.0, abs=1.0)     # digitised south -> north, FT
    assert a["pass"] is True
    b = GR.one_way_audit(seg, "GRID ST", 1, 180.0)
    assert b["pass"] is False


def test_undirected_components_counts_islands():
    seg, nodes = _grid_network()
    nodes = pd.concat([nodes, pd.DataFrame({"node_id": [99], "x": [9999.0], "y": [9999.0],
                                            "names_norm": [[]], "degree_drivable": [0], "borough": [np.int8(1)]})],
                      ignore_index=True)
    c = GR.undirected_components(seg, nodes)
    assert c["n_components"] == 2 and c["largest"] == 25


# --------------------------------------------------------------------------- NYCB container
def test_nycb_section_layouts_match_data_contracts_15():
    assert E.NODE_DTYPE.itemsize == 24
    assert [E.NODE_DTYPE.fields[f][1] for f in ("id", "x", "y", "z", "control", "signal_source")] == [0, 8, 12, 16, 20, 21]
    assert E.SEGMENT_DTYPE.itemsize == 48
    assert [E.SEGMENT_DTYPE.fields[f][1] for f in ("id", "from_node", "to_node", "first_vertex", "vertex_count",
                                                   "rw_type", "width_m", "speed_mph", "name_str")] == [0, 8, 16, 24, 28, 32, 36, 40, 44]
    assert E.VERTEX_DTYPE.itemsize == 12
    assert E.LANE_DTYPE.itemsize == 48
    assert [E.LANE_DTYPE.fields[f][1] for f in ("id", "segment_id", "index_from_center", "width_m", "speed_mps",
                                                "first_vertex", "vertex_count", "first_succ", "succ_count")] == [0, 8, 16, 20, 24, 28, 32, 36, 40]
    assert E.JUNCTION_DTYPE.itemsize == 48
    assert [E.JUNCTION_DTYPE.fields[f][1] for f in ("id", "from_lane", "to_lane", "turn", "pad", "signal_group",
                                                    "first_vertex", "vertex_count", "first_yield", "yield_count")] == [0, 8, 16, 24, 25, 28, 32, 36, 40, 44]
    assert E.CONTROLLER_DTYPE.itemsize == 32
    assert E.PHASE_DTYPE.itemsize == 28
    assert all(E.ALL_DTYPES[k].itemsize == v for k, v in E.EXPECTED_SIZEOF.items())


def test_nycb_container_round_trip(tmp_path):
    w = NycbWriter()
    nodes = np.zeros(3, dtype=E.NODE_DTYPE)
    nodes["id"] = [10, 20, 30]
    nodes["x"] = [1.5, 2.5, 3.5]
    nodes["control"] = [0, 1, 2]
    w.add_array("nodes", nodes)
    offs = w.strings.add_many(["", "BROADWAY", "5 AVE", "BROADWAY"])
    assert list(offs) == [0, 1, 10, 1]
    w.add_strtab()
    p = tmp_path / "t.nycb"
    w.write(p)
    with open(p, "rb") as fh:
        magic, version, count, index_offset = struct.unpack("<4sIIQ", fh.read(20))
    assert magic == b"NYCB" and version == 1 and count == 2
    r = NycbReader(p)
    back = r.read("nodes", E.NODE_DTYPE)
    assert list(back["id"]) == [10, 20, 30]
    assert r.string_at(1) == "BROADWAY" and r.string_at(10) == "5 AVE" and r.string_at(0) == ""
    with pytest.raises(NycbError):
        r.read("nodes", aligned_dtype([("id", "<i8")]))
    with pytest.raises(NycbError):
        r.read("missing", E.NODE_DTYPE)


def test_nycb_rejects_bad_sections():
    w = NycbWriter()
    w.add_array("nodes", np.zeros(1, dtype=E.NODE_DTYPE))
    with pytest.raises(NycbError):
        w.add_array("nodes", np.zeros(1, dtype=E.NODE_DTYPE))
    with pytest.raises(NycbError):
        w.add_array("a_very_long_section_name", np.zeros(1, dtype=E.NODE_DTYPE))
    with pytest.raises(NycbError):
        w.add_array("two_d", np.zeros((2, 2), dtype=np.float32))


# --------------------------------------------------------------------------- terrain sampler
def test_terrain_sampler_reads_the_contract_png(tmp_path):
    tile = Tile(3, -2)
    d = tmp_path / tile.name
    d.mkdir(parents=True)
    n = 501
    # ramp from 0 m in the north row to 5 m in the south row
    vals = np.tile((np.arange(n) * 4).astype(np.uint16)[:, None], (1, n))
    Image.frombytes("I;16", (n, n), vals.tobytes()).save(d / "terrain.png")
    (d / "terrain.json").write_text(json.dumps({"schema_version": 1, "tile": tile.name, "x0": tile.x0, "y0": tile.y0,
                                                "z_min_m": -1.0, "z_scale_m": 0.0025, "samples": n, "spacing_m": 2.0}))
    s = TerrainSampler(tmp_path)
    assert tile.name in s.available
    z, ok = s.sample(np.array([tile.x0 + 500.0, tile.x0 + 10.0, tile.x0 + 500.0]),
                     np.array([tile.y0 + 999.0, tile.y0, tile.y0 + 500.0]))
    assert ok.all()
    assert z[0] == pytest.approx(-1.0 + 0.5 * 4 * 0.0025, abs=1e-4)     # half a sample below the north edge
    assert z[1] == pytest.approx(-1.0 + 500 * 4 * 0.0025, abs=1e-3)     # south edge, row 500 (boundary fallback)
    assert z[2] == pytest.approx(-1.0 + 250 * 4 * 0.0025, abs=1e-3)     # middle of the tile
    z2, ok2 = s.sample(np.array([tile.x0 + 5000.0]), np.array([tile.y0]))
    assert not ok2.any()


def _tiny_roads_dir(tmp_path: Path) -> Path:
    """A minimal but contract-shaped roads directory plus one terrain tile, for the terrain-lift test."""
    d = tmp_path / "roads"
    d.mkdir()
    line = shapely.LineString([(10.0, 10.0, 0.0), (500.0, 10.0, 0.0), (900.0, 10.0, 0.0)])
    deck = shapely.LineString([(10.0, 500.0, 5.5), (900.0, 500.0, 5.5)])          # level code 17 = +5.5 m
    seg = gpd.GeoDataFrame({
        "segment_id": np.array([1, 2], dtype=np.int64),
        "from_node": np.array([10, 30], dtype=np.int64), "to_node": np.array([20, 40], dtype=np.int64),
        "z_source": np.array([S.Z_AT_GRADE, S.Z_LEVEL_CONST], dtype=np.int8),
        "level_from": np.array([S.LEVEL_AT_GRADE, 17], dtype=np.int8),
        "level_to": np.array([S.LEVEL_AT_GRADE, 17], dtype=np.int8),
        "z_from": np.float32([0.0, 5.5]), "z_to": np.float32([0.0, 5.5]),
    }, geometry=[line, deck], crs=NYC_TM)
    S.write_geoparquet(seg, d / "segments.parquet", S.SCHEMAS["segments"])
    S.write_parquet(pd.DataFrame({"node_id": np.array([10, 20, 30, 40], dtype=np.int64),
                                  "z": np.float32([0, 0, 5.5, 5.5])}), d / "nodes.parquet", S.SCHEMAS["nodes"])
    S.write_geoparquet(gpd.GeoDataFrame({"lane_id": np.array([1], dtype=np.int64),
                                         "segment_id": np.array([1], dtype=np.int64)},
                                        geometry=[shapely.LineString([(10.0, 12.0, 0.0), (900.0, 12.0, 0.0)])], crs=NYC_TM),
                      d / "lanes.parquet", S.SCHEMAS["lanes"])
    S.write_geoparquet(gpd.GeoDataFrame({"junction_lane_id": np.array([1], dtype=np.int64),
                                         "from_segment": np.array([2], dtype=np.int64)},
                                        geometry=[shapely.LineString([(880.0, 500.0, 5.5), (900.0, 505.0, 5.5)])], crs=NYC_TM),
                      d / "junction_lanes.parquet", S.SCHEMAS["junction_lanes"])
    S.write_parquet(pd.DataFrame({"sign_id": np.array([1], dtype=np.int64), "x": [400.0], "y": [12.0],
                                  "z": np.float32([2.5]), "ground_z": np.float32([0.0])}),
                    d / "signs.parquet", S.SCHEMAS["signs"])

    tiles = tmp_path / "tiles" / "t_0_0"
    tiles.mkdir(parents=True)
    n = 501
    vals = np.tile((np.arange(n) * 8).astype(np.uint16)[:, None], (1, n))
    Image.frombytes("I;16", (n, n), vals.tobytes()).save(tiles / "terrain.png")
    (tiles / "terrain.json").write_text(json.dumps({"schema_version": 1, "tile": "t_0_0", "x0": 0.0, "y0": 0.0,
                                                    "z_min_m": 2.0, "z_scale_m": 0.0025, "samples": n, "spacing_m": 2.0}))
    return d


def _seg_z(d: Path) -> np.ndarray:
    g = gpd.read_parquet(d / "segments.parquet")
    return shapely.get_coordinates(g.geometry.values, include_z=True)[:, 2]


def test_apply_terrain_z_lifts_the_network_and_is_idempotent(tmp_path):
    from nycsim_pipeline.roads import apply_terrain_z as A
    d = _tiny_roads_dir(tmp_path)
    r1 = A.apply(d, tmp_path / "tiles")
    assert r1["applied"] and r1["tiles_with_terrain"] == 1
    z1 = _seg_z(d)
    # at-grade line at y = 10 m -> raster row (1000-10)/2 = 495 -> 2.0 + 495*8*0.0025 = 11.9 m
    assert np.allclose(z1[:3], 2.0 + 495 * 8 * 0.0025, atol=1e-3)
    # the deck at y = 500 m keeps its 5.5 m level offset above the ground there
    ground_500 = 2.0 + 250 * 8 * 0.0025
    assert np.allclose(z1[3:], ground_500 + 5.5, atol=1e-3)
    assert r1["signs"]["z_updated"] == 1
    signs = pd.read_parquet(d / "signs.parquet")
    assert float(signs["ground_z"].iloc[0]) == pytest.approx(2.0 + 494 * 8 * 0.0025, abs=1e-2)
    assert float(signs["z"].iloc[0]) - float(signs["ground_z"].iloc[0]) == pytest.approx(2.5, abs=1e-3)
    nodes = pd.read_parquet(d / "nodes.parquet")
    assert float(nodes.loc[nodes["node_id"] == 30, "z"].iloc[0]) == pytest.approx(ground_500 + 5.5, abs=1e-2)

    r2 = A.apply(d, tmp_path / "tiles")
    z2 = _seg_z(d)
    assert np.array_equal(z1, z2), "re-running the stage must not accumulate offsets"
    signs2 = pd.read_parquet(d / "signs.parquet")
    assert float(signs2["z"].iloc[0]) == pytest.approx(float(signs["z"].iloc[0]))
    assert r2["segments"]["at_grade_vertices_lifted"] == r1["segments"]["at_grade_vertices_lifted"]


def test_apply_terrain_z_reports_when_there_is_no_terrain_yet(tmp_path):
    from nycsim_pipeline.roads import apply_terrain_z as A
    d = _tiny_roads_dir(tmp_path)
    out = A.apply(d, tmp_path / "no_tiles_here")
    assert out["applied"] is False and out["tiles_with_terrain"] == 0
    assert "terrain" in out["note"]


# --------------------------------------------------------------------------- produced artefacts
@pytest.fixture(scope="module")
def segments() -> gpd.GeoDataFrame:
    _need(SEGMENTS)
    return gpd.read_parquet(SEGMENTS)


@pytest.fixture(scope="module")
def road_nodes() -> pd.DataFrame:
    _need(NODES)
    return pd.read_parquet(NODES)


def test_artefacts_satisfy_the_contracts():
    for name, path in (("road_segments", SEGMENTS), ("road_nodes", NODES), ("lanes", LANES),
                       ("junction_lanes", JUNCTION_LANES), ("signals", SIGNALS), ("signs", SIGNS)):
        _need(path)
        assert validate_parquet(name, path) == [], name


def test_segment_column_types_are_the_contract_types():
    _need(SEGMENTS)
    sch = pq.ParquetFile(SEGMENTS).schema_arrow
    for col, typ in SEGMENT_TYPES.items():
        assert sch.field(col).type == typ, f"{col}: {sch.field(col).type} != {typ}"
    assert S.read_schema_tag(SEGMENTS) == S.SCHEMAS["segments"]
    assert S.read_schema_tag(NODES) == S.SCHEMAS["nodes"]


def test_segments_are_three_dimensional_and_inside_the_scope(segments: gpd.GeoDataFrame):
    assert segments.crs is not None and segments.crs.equals(NYC_TM)
    assert shapely.has_z(segments.geometry.values).all()
    assert (shapely.get_type_id(segments.geometry.values) == shapely.GeometryType.LINESTRING).all()
    b = segments.total_bounds
    assert SCOPE_XMIN <= b[0] and b[2] <= SCOPE_XMAX and SCOPE_YMIN <= b[1] and b[3] <= SCOPE_YMAX
    assert segments["segment_id"].is_unique
    assert (segments["width_m"] > 0).sum() >= len(segments) - segments["rw_type"].isin([S.RW_NONPHYSICAL, S.RW_FERRY]).sum()


def test_segment_enums_are_in_range(segments: gpd.GeoDataFrame):
    assert segments["rw_type"].between(1, 14).all()
    assert segments["traffic_dir"].between(0, 3).all()
    assert segments["bike_lane"].between(0, 4).all()
    assert segments["surface"].between(0, 5).all()
    assert segments["borough"].between(0, 5).all()
    assert segments["speed_source"].isin([0, 1]).all()
    assert segments["lanes_source"].isin([0, 1]).all()
    drivable = segments["drivable"].to_numpy()
    assert (segments.loc[drivable, "travel_lanes"] >= 1).all()
    assert (segments.loc[drivable, "posted_speed_mph"] > 0).all()
    assert (segments["total_lanes"] >= segments["travel_lanes"] + segments["park_lanes"]).all()


def test_nodes_carry_control_and_provenance(road_nodes: pd.DataFrame):
    assert road_nodes["node_id"].is_unique
    assert road_nodes["control"].between(0, 4).all()
    assert road_nodes["is_signalized"].equals(road_nodes["control"].eq(S.CTRL_SIGNAL))
    sig = road_nodes["is_signalized"].to_numpy()
    assert road_nodes.loc[sig, "signal_source"].between(0, 4).all()
    assert (road_nodes.loc[~sig, "signal_source"] == S.SIG_NONE).all()
    assert road_nodes.loc[road_nodes["has_all_way_stop"], "has_stop_sign"].all()


def test_every_segment_end_is_a_real_node(segments: gpd.GeoDataFrame, road_nodes: pd.DataFrame):
    ids = set(road_nodes["node_id"].to_numpy().tolist())
    assert set(segments["from_node"].to_numpy().tolist()) <= ids
    assert set(segments["to_node"].to_numpy().tolist()) <= ids


def test_lanes_belong_to_their_segment_and_stay_in_the_corridor(segments: gpd.GeoDataFrame):
    _need(LANES)
    lanes = gpd.read_parquet(LANES)
    assert lanes["lane_id"].is_unique
    seg_index = segments.set_index("segment_id")
    assert set(lanes["segment_id"]) <= set(seg_index.index)
    assert lanes["kind"].between(0, 5).all()
    assert lanes["direction"].isin([-1, 1]).all()
    assert (lanes["width_m"] >= min(L.MIN_W.values()) - 1e-3).all()
    for kind, w in L.MIN_W.items():
        sub = lanes.loc[lanes["kind"] == kind, "width_m"]
        assert sub.empty or sub.min() >= w - 1e-3, f"kind {kind}: min width {sub.min()}"
    assert shapely.has_z(lanes.geometry.values).all()
    rng = np.random.default_rng(7)
    sample = rng.choice(len(lanes), size=min(4000, len(lanes)), replace=False)
    geoms = seg_index.loc[lanes["segment_id"].to_numpy()[sample], "geometry"].to_numpy()
    d = shapely.distance(lanes.geometry.values[sample], geoms)
    allowed = np.maximum(seg_index.loc[lanes["segment_id"].to_numpy()[sample], "width_m"].to_numpy(), 6.0) / 2.0 + 0.5
    assert (d <= allowed).all(), f"{int((d > allowed).sum())} sampled lanes leave their corridor"


def test_lane_successors_reference_real_lanes():
    _need(LANES)
    lanes = pq.read_table(LANES, columns=["lane_id", "successors", "predecessors", "kind"])
    ids = set(lanes.column("lane_id").to_pylist())
    succ = lanes.column("successors").to_pylist()
    rng = np.random.default_rng(11)
    for i in rng.choice(len(succ), size=min(5000, len(succ)), replace=False):
        for s in (succ[i] or []):
            assert s in ids
    kinds = np.array(lanes.column("kind").to_pylist())
    n_succ = np.array([len(s or []) for s in succ])
    travel = np.isin(kinds, [S.LANE_TRAVEL, S.LANE_TURN])
    assert (n_succ[kinds == S.LANE_PARKING] == 0).all()          # parking lanes never connect
    assert n_succ[travel].mean() > 1.0


def test_junction_lanes_connect_existing_lanes():
    _need(JUNCTION_LANES)
    jl = pq.read_table(JUNCTION_LANES, columns=["junction_lane_id", "from_lane", "to_lane", "turn", "signal_group", "yield_to"])
    lane_ids = set(pq.read_table(LANES, columns=["lane_id"]).column("lane_id").to_pylist())
    fl = jl.column("from_lane").to_pylist()
    tl = jl.column("to_lane").to_pylist()
    rng = np.random.default_rng(13)
    for i in rng.choice(len(fl), size=min(5000, len(fl)), replace=False):
        assert fl[i] in lane_ids and tl[i] in lane_ids
    turns = np.array(jl.column("turn").to_pylist())
    assert set(np.unique(turns)) <= {0, 1, 2, 3}
    assert len(set(jl.column("junction_lane_id").to_pylist())) == jl.num_rows


def test_signal_controllers_cover_every_signalised_node(road_nodes: pd.DataFrame):
    _need(SIGNALS)
    sig = pq.read_table(SIGNALS).to_pandas()
    signalised = set(road_nodes.loc[road_nodes["is_signalized"], "node_id"].to_numpy().tolist())
    assert set(sig["node_id"].to_numpy().tolist()) <= signalised
    assert len(sig) >= 0.98 * len(signalised)
    assert sig["controller_id"].is_unique
    assert sig["cycle_s"].between(30.0, 180.0).all()
    assert (sig["offset_s"] < sig["cycle_s"]).all()
    for row in sig.head(500).itertuples():
        total = sum(float(p["lpi_s"]) + float(p["green_s"]) + float(p["yellow_s"]) + float(p["allred_s"])
                    for p in row.phases if int(p["group"]) >= 0)
        total += sum(float(p["ped_walk_s"]) + float(p["ped_flash_s"]) for p in row.phases if int(p["group"]) < 0)
        assert total == pytest.approx(float(row.cycle_s), abs=0.05)


def test_signs_are_real_and_placed():
    _need(SIGNS)
    signs = pq.read_table(SIGNS).to_pandas()
    assert signs["sign_id"].is_unique
    assert signs["source"].isin([0, 1, 2]).all()
    assert signs["arrow"].between(0, 3).all()
    assert signs["support"].between(0, 3).all()
    assert (signs["sign_w_m"] > 0).all() and (signs["sign_h_m"] > 0).all()
    # DOT overhead guide panels really are metres across; nothing may exceed a full sign gantry
    assert (signs["sign_w_m"] < 8.0).all() and (signs["sign_h_m"] < 8.0).all()
    oversize = signs[(signs["sign_w_m"] > 2.5) | (signs["sign_h_m"] > 2.5)]
    assert (oversize["source"] == 0).all(), "only real DOT records may be larger than a 2.5 m panel"
    assert signs["facing_heading"].between(0.0, 360.0).all()
    assert signs["x"].between(SCOPE_XMIN, SCOPE_XMAX).all() and signs["y"].between(SCOPE_YMIN, SCOPE_YMAX).all()
    assert (signs["z"] >= signs["ground_z"]).all()
    dot = signs[signs["source"] == 0]
    assert len(dot) > 300_000, "the DOT sign dataset should dominate the layer"
    assert (dot["mutcd_code"].str.len() > 0).all()
    fams = set(signs["mutcd_family"])
    assert {"R1", "R2", "R5", "R6", "R7", "D3"} <= fams
    named = signs[signs["mutcd_code"] == "D3-1"]
    assert len(named) > 10_000 and (named["text"].str.len() > 0).all()


def test_bridges_and_tunnels_are_all_present_and_connected():
    _need(BRIDGES)
    doc = json.load(open(BRIDGES))
    items = {b["name"]: b for b in doc["bridges_tunnels"]}
    assert doc["n_found"] == doc["n_structures"], [n for n, b in items.items() if not b["found"]]
    blob = json.dumps(doc).lower()
    for required in ("brooklyn", "manhattan", "williamsburg", "queensboro", "george washington", "verrazzano",
                     "throgs neck", "whitestone", "pulaski", "kosciuszko", "high bridge", "triborough",
                     "lincoln", "holland", "queens-midtown", "carey"):
        assert required in blob, required
    for name, b in items.items():
        assert b["n_segments"] > 0, name
        assert b["length_m"] > 0, name
        assert len(b["end_nodes"]) >= 2, f"{name} is not connected at both ends"
        assert b["connected_both_ends"], name


def test_connectivity_report_shows_a_drivable_city():
    _need(CONNECTIVITY)
    c = json.load(open(CONNECTIVITY))
    assert c["undirected_all_segments"]["share"] > 0.9
    assert c["directed_strongly_connected"]["largest_share_of_drivable_nodes"] > 0.9
    routes = {r["id"]: r for r in c["routes"]}
    bx_si = routes["bronx_to_staten_island"]
    assert bx_si["found"], bx_si
    assert bx_si["crosses_required_structure"], "the Bronx -> Staten Island route must use the Verrazzano-Narrows Bridge"
    assert 40.0 < bx_si["distance_km"] < 90.0, bx_si["distance_km"]
    for r in c["routes"]:
        assert r["found"], r["id"]
    assert c["one_way_checks_passed"] == c["one_way_checks_total"], c["one_way_checks"]
    assert c["divided_highway_checks_passed"] == len(c["divided_highway_checks"]), c["divided_highway_checks"]
    d = c["dead_ends"]
    assert d["travel_lanes_without_successor"] / d["travel_lanes"] < 0.02


def test_pavement_tiles_hold_polygons_inside_their_tile():
    d = ROADS / "pavement"
    files = sorted(d.glob("t_*.parquet")) if d.exists() else []
    if not files:
        pytest.skip("pavement not produced yet")
    assert len(files) > 500
    rng = np.random.default_rng(5)
    for p in [files[i] for i in rng.choice(len(files), size=min(12, len(files)), replace=False)]:
        t = Tile.parse(p.stem)
        g = gpd.read_parquet(p)
        assert S.read_schema_tag(p) == S.SCHEMAS["pavement"]
        assert g["kind"].between(0, 7).all()
        assert g["surface"].between(0, 5).all()
        b = g.total_bounds
        assert b[0] >= t.x0 - 1e-6 and b[2] <= t.x0 + 1000 + 1e-6
        assert b[1] >= t.y0 - 1e-6 and b[3] <= t.y0 + 1000 + 1e-6
        assert (shapely.area(g.geometry.values) > 0).all()


# --------------------------------------------------------------------------- runtime binaries
def test_roadgraph_binary_matches_the_parquet():
    p = RUNTIME / "roadgraph.nycb"
    if not p.exists() or not SEGMENTS.exists():
        pytest.skip("roadgraph.nycb not produced yet")
    rg = E.read_roadgraph(p)
    seg = gpd.read_parquet(SEGMENTS, columns=["segment_id", "from_node", "to_node", "street_name", "width_m", "geometry"])
    assert len(rg["segments"]) == len(seg)
    assert (rg["segments"]["id"] == seg["segment_id"].to_numpy()).all()
    assert (rg["segments"]["from_node"] == seg["from_node"].to_numpy()).all()
    assert (rg["segments"]["to_node"] == seg["to_node"].to_numpy()).all()
    assert np.allclose(rg["segments"]["width_m"], seg["width_m"].to_numpy(), atol=1e-3)
    names = seg["street_name"].to_numpy()
    for i in (0, len(seg) // 3, len(seg) - 1):
        assert rg["segment_names"][i] == names[i]
        poly = E.segment_polyline(rg, i)
        ref = shapely.get_coordinates(seg.geometry.values[i], include_z=True)
        assert poly.shape == ref.shape
        assert np.allclose(poly, ref, atol=0.02)
    nodes = pd.read_parquet(NODES, columns=["node_id", "control", "signal_source"])
    assert (rg["nodes"]["id"] == nodes["node_id"].to_numpy()).all()
    assert (rg["nodes"]["control"] == nodes["control"].to_numpy()).all()
    lanes = pq.read_table(LANES, columns=["lane_id", "successors"])
    assert len(rg["lanes"]) == lanes.num_rows
    succ = lanes.column("successors").to_pylist()
    for i in (0, lanes.num_rows // 2, lanes.num_rows - 1):
        assert list(E.lane_successors(rg, i)) == list(succ[i] or [])
    jl = pq.read_table(JUNCTION_LANES, columns=["junction_lane_id", "yield_to"])
    assert len(rg["junction_lanes"]) == jl.num_rows
    y = jl.column("yield_to").to_pylist()
    for i in (0, jl.num_rows // 2, jl.num_rows - 1):
        assert list(E.junction_yields(rg, i)) == list(y[i] or [])
    total_vertices = (int(rg["segments"]["vertex_count"].sum()) + int(rg["lanes"]["vertex_count"].sum())
                      + int(rg["junction_lanes"]["vertex_count"].sum()))
    assert total_vertices == len(rg["vertices"])


def test_signals_binary_matches_the_parquet():
    p = RUNTIME / "signals.nycb"
    if not p.exists() or not SIGNALS.exists():
        pytest.skip("signals.nycb not produced yet")
    sg = E.read_signals(p)
    sig = pq.read_table(SIGNALS).to_pandas()
    assert len(sg["controllers"]) == len(sig)
    assert (sg["controllers"]["node_id"] == sig["node_id"].to_numpy()).all()
    assert int(sg["controllers"]["phase_count"].sum()) == len(sg["phases"])
    i = len(sig) // 2
    c = sg["controllers"][i]
    ph = sg["phases"][int(c["first_phase"]): int(c["first_phase"]) + int(c["phase_count"])]
    ref = sig["phases"].iloc[i]
    assert len(ph) == len(ref)
    for a, b in zip(ph, ref):
        assert int(a["group"]) == int(b["group"])
        assert float(a["green_s"]) == pytest.approx(float(b["green_s"]), abs=1e-2)
        assert float(a["ped_flash_s"]) == pytest.approx(float(b["ped_flash_s"]), abs=1e-2)


def test_nycb_layout_json_documents_the_cpp_structs():
    p = RUNTIME / "nycb_layout.json"
    if not p.exists():
        pytest.skip("nycb_layout.json not produced yet")
    doc = json.load(open(p))
    assert doc["container"]["header"]["sizeof"] == 24
    assert doc["container"]["index_entry"]["sizeof"] == 40
    for name, size in E.EXPECTED_SIZEOF.items():
        assert doc["sections"][name]["sizeof"] == size
