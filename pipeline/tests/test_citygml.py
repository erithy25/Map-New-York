"""Tests for the CityGML LOD2 stage (``buildings/citygml*.py``).

Run with::

    PYTHONPATH=pipeline python3 -m pytest pipeline/tests/test_citygml.py -q

Everything up to ``test_real_*`` runs against the committed fixture
``tests/fixtures/citygml_sample.gml`` (regenerate with ``fixtures/make_citygml_sample.py``) and needs no
downloaded data. The fixture deliberately contains gable / hip / shed roofs, which the **real** NYC
delivery does not contain (see ADR-013): that is how these tests prove the classifier works and the flat
result on real data is a property of the source, not a bug.

The ``test_real_*`` tests skip when the corresponding artefact has not been produced yet.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest
import shapely
from shapely import affinity

from nycsim_pipeline.buildings import citygml as C
from nycsim_pipeline.buildings import citygml_geom as G
from nycsim_pipeline.buildings import citygml_join as J
from nycsim_pipeline.buildings import citygml_roof as R
from nycsim_pipeline.paths import PROCESSED, VERIFICATION

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "citygml_sample.gml"
CITYGML_DIR = PROCESSED / "buildings" / "citygml"
INDEX = CITYGML_DIR / "index.parquet"
FOOTPRINTS = PROCESSED / "buildings" / "footprints_raw.parquet"
ROOF_ATTRS = PROCESSED / "buildings" / "roof_attrs.parquet"
FT = 0.3048006096012192          # US survey foot


# --------------------------------------------------------------------------- fixture parse
@pytest.fixture(scope="module")
def fixture_rows(tmp_path_factory) -> pd.DataFrame:
    assert FIXTURE.exists(), f"missing test fixture {FIXTURE}"
    out = tmp_path_factory.mktemp("citygml") / "da0.parquet"
    summary = C.process_gml_file(FIXTURE, da=0, out_path=out)
    assert summary["error"] is None, summary["error"]
    df = pq.read_table(out).to_pandas()
    df.attrs["summary"] = summary
    return df


def _row(df: pd.DataFrame, gml_id: str) -> pd.Series:
    """The single row whose (possibly merged, ';'-joined) gml_id list contains ``gml_id``."""
    sel = df[df.gml_id.map(lambda s: gml_id in s.split(";"))]
    assert len(sel) == 1, f"{gml_id}: expected 1 row, got {len(sel)}"
    return sel.iloc[0]


def test_fixture_parses_every_building(fixture_rows):
    s = fixture_rows.attrs["summary"]
    assert s["buildings"] == 9          # nine bldg:Building elements
    assert s["rows"] == 8               # two of them share BIN 4000001 and are merged
    assert s["duplicate_bins_merged"] == 1
    assert "building_exception" not in s["counters"], "a building raised while parsing the fixture"
    assert "srs_assumed" not in s["counters"], "srsName EPSG:2263 must be read, not assumed"
    assert "srs_unknown_epsg" not in s["counters"]


def test_fixture_roof_types(fixture_rows):
    """The classifier finds gable, hip and shed when the geometry really has them."""
    assert _row(fixture_rows, "b_gable").roof_type == R.ROOF_GABLE
    assert _row(fixture_rows, "b_hip").roof_type == R.ROOF_HIP
    assert _row(fixture_rows, "b_shed").roof_type == R.ROOF_SHED
    assert _row(fixture_rows, "b_two_level").roof_type == R.ROOF_FLAT
    assert _row(fixture_rows, "b_flat").roof_type == R.ROOF_FLAT
    counters = fixture_rows.attrs["summary"]["counters"]
    assert counters["roof_face_sloped"] == 7        # 2 gable + 4 hip + 1 shed
    assert counters["roof_face_horizontal"] == 7


def test_fixture_roof_slope_is_geometrically_correct(fixture_rows):
    """Gable: eaves at 30 ft, ridge at 45 ft, half-span 12 ft -> atan(15/12) = 51.34 deg."""
    g = _row(fixture_rows, "b_gable")
    assert g.roof_slope_deg == pytest.approx(math.degrees(math.atan2(15.0, 12.0)), abs=0.05)
    assert g.n_roof_levels == 0                      # a pure gable has no horizontal face
    assert g.z_roof_max == pytest.approx(45.0 * FT, abs=1e-3)
    assert g.z_ground_min == pytest.approx(10.0 * FT, abs=1e-3)


def test_fixture_roof_levels(fixture_rows):
    t = _row(fixture_rows, "b_two_level")
    assert t.n_roof_levels == 2
    assert sorted(float(z) for z in t.roof_level_z) == pytest.approx([35.0 * FT, 60.0 * FT], abs=1e-3)
    # the lower level is an annulus (60x40 minus 20x20), the upper one the 20x20 cap
    areas = sorted(float(a) for a in t.roof_level_area)
    assert areas[0] == pytest.approx((20.0 * FT) ** 2, rel=0.02)
    assert areas[1] == pytest.approx((60.0 * 40.0 - 20.0 * 20.0) * FT * FT, rel=0.02)


def test_fixture_bin_handling(fixture_rows):
    nobin = _row(fixture_rows, "b_nobin")
    assert nobin.bin == 0 and not nobin.bin_ok and (int(nobin["flags"]) & C.F_BIN_MISSING)
    ph = _row(fixture_rows, "b_placeholder")
    assert ph.bin == 4000000 and not ph.bin_ok and (int(ph["flags"]) & C.F_BIN_PLACEHOLDER)
    merged = _row(fixture_rows, "b_flat_part2")          # merged row keeps both gml_ids
    assert merged.gml_id == "b_flat;b_flat_part2"
    assert merged.bin == 4000001 and merged.bin_ok and (int(merged["flags"]) & C.F_MERGED)
    assert merged.n_ground == 2 and merged.n_roof == 2
    # the merged row is the sum of its parts: 30x50 house + 20x20 garage wing
    assert merged.footprint_area_m2 == pytest.approx((30.0 * 50.0 + 20.0 * 20.0) * FT * FT, rel=1e-3)


def test_fixture_bad_ring_is_dropped_not_fatal(fixture_rows):
    bad = _row(fixture_rows, "b_baddring")
    assert bad.n_dropped == 1 and (int(bad["flags"]) & C.F_DROPPED)
    assert bad.n_roof == 1                                # the good roof polygon survived
    assert fixture_rows.attrs["summary"]["counters"]["ring_not_3d"] == 1


def test_fixture_geometry_is_consistent(fixture_rows):
    """Blob lengths, winding and areas agree with the schema for every row."""
    for _, r in fixture_rows.iterrows():
        xyz = np.frombuffer(r.tri_xyz, dtype="<f4")
        typ = np.frombuffer(r.tri_type, dtype=np.uint8)
        assert xyz.size == r.tri_count * 9
        assert typ.size == r.tri_count
        tris = xyz.reshape(-1, 3, 3).astype(np.float64)
        n = G.cross3(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
        assert (n[typ == G.SURF_ROOF][:, 2] > 0).all(), "roof triangles must face up"
        assert (n[typ == G.SURF_GROUND][:, 2] < 0).all(), "ground triangles must face down"
        v = tris.reshape(-1, 3)
        assert r.xmin == pytest.approx(v[:, 0].min(), abs=1e-3)
        assert r.ymax == pytest.approx(v[:, 1].max(), abs=1e-3)
        assert r.z_roof_max <= v[:, 2].max() + 1e-3
        assert r.vertex_count <= r.tri_count * 3


def test_fixture_footprint_area(fixture_rows):
    assert _row(fixture_rows, "b_hip").footprint_area_m2 == pytest.approx(34.0 * 34.0 * FT * FT, rel=1e-3)
    assert _row(fixture_rows, "b_gable").footprint_area_m2 == pytest.approx(40.0 * 24.0 * FT * FT, rel=1e-3)
    assert _row(fixture_rows, "b_two_level").footprint_area_m2 == pytest.approx(60.0 * 40.0 * FT * FT, rel=1e-3)


def test_fixture_walls_face_outward(fixture_rows):
    c = fixture_rows.attrs["summary"]["counters"]
    assert c.get("wall_ground_inward", 0) == 0
    assert c.get("wall_ground_outward", 0) > 0


def test_index_from_fixture(tmp_path):
    out = tmp_path / "da0.parquet"
    C.process_gml_file(FIXTURE, da=0, out_path=out)
    s = C.build_index(tmp_path, das=(0,), manifest=False)
    assert s["rows"] == 8 and s["bin_ok_rows"] == 6
    t = pq.read_table(tmp_path / "index.parquet")
    assert set(C.INDEX_COLUMNS) <= set(t.schema.names)
    assert t.schema.metadata[b"nycsim.schema"].decode() == C.INDEX_SCHEMA_ID
    assert s["roof_type_hist"]["gable"] == 1 and s["roof_type_hist"]["hip"] == 1


# --------------------------------------------------------------------------- parsing units
@pytest.mark.parametrize("srs,code", [
    ("EPSG:2263", 2263),
    ("urn:ogc:def:crs:EPSG::2263", 2263),
    ("urn:ogc:def:crs:EPSG:6.12:2263", 2263),                              # authority version, not the code
    ("urn:ogc:def:crs,crs:EPSG:6.12:2263,crs:EPSG:6.12:5703", 2263),      # compound: horizontal first
    ("http://www.opengis.net/def/crs/EPSG/0/2263", 2263),
    ("EPSG:4326", 4326), ("", None), (None, None), ("nonsense", None),
])
def test_parse_srs(srs, code):
    assert C.parse_srs(srs) == code


@pytest.mark.parametrize("raw,expect", [
    ("4292359", (4292359, True, 0)),
    (" 1000000 ", (1000000, False, C.F_BIN_PLACEHOLDER)),
    ("999999", (999999, False, C.F_BIN_MISSING)),
    ("6000000", (6000000, False, C.F_BIN_MISSING)),
    ("", (0, False, C.F_BIN_MISSING)),
    (None, (0, False, C.F_BIN_MISSING)),
    ("abc", (0, False, C.F_BIN_MISSING)),
])
def test_parse_bin(raw, expect):
    assert C.parse_bin(raw) == expect


# --------------------------------------------------------------------------- geometry units
def test_newell_normal_and_slope():
    sq = np.array([[0, 0, 0], [10, 0, 0], [10, 10, 0], [0, 10, 0]], dtype=float)
    n = G.newell_normal(sq)
    assert n[2] == pytest.approx(200.0)                      # 2 * area, +z
    assert G.slope_deg(n / np.linalg.norm(n)) == pytest.approx(0.0, abs=1e-9)
    tilt = sq.copy()
    tilt[2:, 2] = 10.0                                       # 45 deg towards -y
    nh = G.newell_normal(tilt)
    nh = nh / np.linalg.norm(nh)
    assert G.slope_deg(nh) == pytest.approx(45.0, abs=1e-6)
    assert G.azimuth_deg(nh) == pytest.approx(270.0, abs=1e-6)


def test_clean_ring_and_collinear():
    pts = np.array([[0, 0, 0], [5, 0, 0], [10, 0, 0], [10, 10, 0], [0, 10, 0], [0, 0, 0]], dtype=float)
    r, removed = G.clean_ring(pts)
    assert removed == 1 and len(r) == 5                       # closing vertex dropped
    r2, dropped = G.remove_collinear(r)
    assert dropped == 1 and len(r2) == 4                      # the midpoint on the bottom edge
    assert G.ring_area_xy(r2) == pytest.approx(100.0)


def test_triangulate_polygon_with_hole():
    ext = np.array([[0, 0, 5], [10, 0, 5], [10, 10, 5], [0, 10, 5]], dtype=float)
    hole = np.array([[4, 4, 5], [4, 6, 5], [6, 6, 5], [6, 4, 5]], dtype=float)
    res, reason = G.triangulate_polygon([ext, hole])
    assert reason == "ok" and res is not None
    assert res.area3d == pytest.approx(96.0)
    assert res.n_holes == 1 and res.max_plane_dev == pytest.approx(0.0, abs=1e-9)
    area = 0.0
    for t in res.tris:
        area += 0.5 * float(np.linalg.norm(np.cross(t[1] - t[0], t[2] - t[0])))
    assert area == pytest.approx(96.0, rel=1e-6)
    assert res.nhat[2] == pytest.approx(1.0)


@pytest.mark.parametrize("rings,reason", [
    ([], "degenerate"),
    ([np.zeros((2, 3))], "degenerate"),
    ([np.array([[0, 0, 0], [1e-4, 0, 0], [0, 1e-4, 0]], dtype=float)], "sliver"),
    ([np.array([[0, 0, 0], [1, 0, np.nan], [0, 1, 0]], dtype=float)], "nonfinite"),
])
def test_triangulate_polygon_rejects_bad_input(rings, reason):
    res, got = G.triangulate_polygon(rings)
    assert res is None and got == reason


def test_finalize_triangles_drops_flipped_slivers():
    tris = np.array([[[0, 0, 0], [1, 0, 0], [0, 1, 0]],
                     [[0, 0, 0], [1e-9, 0, 0], [0, 1e-9, 0]]], dtype=float)
    out, dropped = G.finalize_triangles(tris, np.array([0.0, 0.0, 1.0]))
    assert dropped == 1 and len(out) == 1 and out.dtype == np.dtype("<f4")


def test_cluster_helpers():
    assert [sorted(g.tolist()) for g in G.cluster_1d(np.array([1.0, 1.1, 5.0]), 0.3)] == [[0, 1], [2]]
    groups = G.cluster_circular(np.array([350.0, 5.0, 180.0]), 25.0)
    assert sorted(len(g) for g in groups) == [1, 2]           # 350 and 5 wrap into one cluster
    assert G.circular_mean_deg(np.array([350.0, 10.0])) % 360.0 == pytest.approx(0.0, abs=1e-6)
    assert G.circular_mean_deg(np.array([80.0, 100.0])) == pytest.approx(90.0, abs=1e-6)
    assert G.angular_distance_deg(350.0, 10.0) == pytest.approx(20.0)


def test_weld_vertex_count():
    tris = np.array([[[0, 0, 0], [1, 0, 0], [0, 1, 0]],
                     [[1, 0, 0], [1, 1, 0], [0, 1, 0]]], dtype="<f4")
    assert G.weld_vertex_count(tris) == 4


# --------------------------------------------------------------------------- roof classifier units
def _face(slope, az, area=50.0, z=10.0):
    return R.RoofFace(area3d=area, area_xy=area * math.cos(math.radians(slope)), slope_deg=slope,
                      azimuth_deg=az, z_min=z, z_max=z + 1.0, z_mean=z + 0.5)


@pytest.mark.parametrize("faces,expect", [
    ([_face(0.0, 0.0)], R.ROOF_FLAT),
    ([_face(30.0, 0.0), _face(30.0, 180.0)], R.ROOF_GABLE),
    ([_face(30.0, 0.0), _face(30.0, 90.0), _face(30.0, 180.0), _face(30.0, 270.0)], R.ROOF_HIP),
    ([_face(20.0, 45.0)], R.ROOF_SHED),
    ([_face(0.0, 0.0, area=400.0), _face(35.0, 0.0, area=20.0)], R.ROOF_FLAT),      # small dormer on a flat deck
    ([_face(0.0, 0.0, area=200.0), _face(40.0, 0.0, area=60.0), _face(40.0, 180.0, area=60.0)], R.ROOF_COMPLEX),
])
def test_classify_roof(faces, expect):
    assert R.classify_roof(faces).roof_type == expect


def test_classify_roof_mansard_and_levels():
    faces = [_face(70.0, 0.0, area=40.0), _face(70.0, 90.0, area=40.0), _face(70.0, 180.0, area=40.0),
             _face(70.0, 270.0, area=40.0), _face(0.0, 0.0, area=60.0, z=12.0)]
    rc = R.classify_roof(faces)
    assert rc.roof_type == R.ROOF_MANSARD
    assert rc.n_roof_levels == 1 and rc.level_z[0] == pytest.approx(12.5)


def test_classify_roof_empty_is_flat():
    rc = R.classify_roof([])
    assert rc.roof_type == R.ROOF_FLAT and rc.n_roof_levels == 0


def test_roof_levels_cluster_by_height():
    faces = [_face(0.0, 0.0, z=10.0), _face(0.0, 0.0, z=10.1), _face(0.0, 0.0, z=20.0)]
    zs, areas = R.roof_levels(faces)
    assert len(zs) == 2 and areas[0] == pytest.approx(100.0) and areas[1] == pytest.approx(50.0)


# --------------------------------------------------------------------------- join stage units
def test_rect_features_of_a_rotated_rectangle():
    poly = shapely.Polygon([(0, 0), (20, 0), (20, 8), (0, 8)])
    rot = affinity.rotate(poly, 30.0, origin=(0, 0))
    w, ln, hd = J.rect_features(np.array([poly, rot], dtype=object))
    assert w[0] == pytest.approx(8.0, rel=1e-6) and ln[0] == pytest.approx(20.0, rel=1e-6)
    assert hd[0] == pytest.approx(90.0, abs=1e-6)      # long axis runs east-west
    assert w[1] == pytest.approx(8.0, rel=1e-3) and ln[1] == pytest.approx(20.0, rel=1e-3)


def test_rect_features_survives_degenerate_geometry():
    w, ln, hd = J.rect_features(np.array([shapely.Point(0, 0), shapely.Polygon()], dtype=object))
    assert (w == 0).all() and (ln == 0).all() and np.isnan(hd).all()


def _infer_frame(**over):
    row = {"bin": 1, "bldg_class": "A1", "borough": 4, "floors": 2, "height": 8.0, "ground_z": 3.0,
           "footprint_area": 90.0, "lot_frontage": 12.0, "bldg_frontage": 7.0, "rect_w": 7.0, "rect_l": 13.0,
           "rect_heading": 45.0}
    row.update(over)
    return pd.DataFrame([row])


def test_infer_pitched_accepts_a_detached_queens_house():
    d = J.infer_pitched(_infer_frame())
    assert bool(d.is_pitched.iloc[0])
    # 30 deg over a 7 m span -> rise 2.02 m, split evenly around the LiDAR plane
    assert d.roof_pitch_deg.iloc[0] == pytest.approx(30.0, abs=0.01)
    assert d.roof_ridge_dz_m.iloc[0] == pytest.approx(0.5 * 3.5 * math.tan(math.radians(30.0)), rel=1e-3)
    assert d.roof_eave_dz_m.iloc[0] == pytest.approx(-d.roof_ridge_dz_m.iloc[0])
    assert d.roof_ridge_deg.iloc[0] == pytest.approx(45.0)


@pytest.mark.parametrize("over", [
    {"bldg_class": "C1"},                       # walk-up apartment, not 1-2 family
    {"bldg_frontage": 12.0},                    # building fills the lot width: attached, party walls
    {"lot_frontage": 0.0},                      # no lot frontage published: no evidence
    {"rect_w": 20.0},                           # span too wide for a domestic pitched roof
    {"floors": 6},
    {"footprint_area": 900.0},
])
def test_infer_pitched_rejects(over):
    d = J.infer_pitched(_infer_frame(**over))
    assert not bool(d.is_pitched.iloc[0])
    assert d.roof_pitch_deg.iloc[0] == 0.0 and d.roof_ridge_dz_m.iloc[0] == 0.0


def test_infer_pitched_clamps_the_rise():
    wide = J.infer_pitched(_infer_frame(rect_w=13.0, bldg_frontage=7.0, lot_frontage=15.0))
    assert wide.roof_ridge_dz_m.iloc[0] == pytest.approx(0.5 * J.RISE_MAX_M)
    assert wide.roof_pitch_deg.iloc[0] < J.PITCH_DEG          # clamped: shallower than nominal
    narrow = J.infer_pitched(_infer_frame(rect_w=2.5))
    assert narrow.roof_ridge_dz_m.iloc[0] == pytest.approx(0.5 * J.RISE_MIN_M)
    assert narrow.roof_pitch_deg.iloc[0] > J.PITCH_DEG


def test_osm_roof_shape_mapping_covers_the_contract_enum():
    codes = set(J.OSM_ROOF_SHAPE_TO_TYPE.values())
    assert codes <= set(range(len(R.ROOF_NAMES)))
    assert J.OSM_ROOF_SHAPE_TO_TYPE["gabled"] == R.ROOF_GABLE
    assert J.OSM_ROOF_SHAPE_TO_TYPE["hipped"] == R.ROOF_HIP
    assert J.OSM_ROOF_SHAPE_TO_TYPE["flat"] == R.ROOF_FLAT
    assert J.OSM_ROOF_SHAPE_TO_TYPE["skillion"] == R.ROOF_SHED


def test_roof_attrs_schema_matches_the_contract():
    names = set(J.SCHEMA.names)
    required = {"bin", "roof_type", "n_roof_levels", "z_roof_max", "roof_mesh_ref", "citygml_match",
                "dz_vs_footprint_m"}
    assert required <= names
    assert J.SCHEMA.field("roof_type").type.equals(pa.int8())
    assert J.SCHEMA.field("bin").type.equals(pa.int64())
    assert J.SCHEMA.field("citygml_match").type.equals(pa.bool_())
    assert J.SCHEMA.field("z_roof_max").type.equals(pa.float32())
    assert J.SCHEMA.field("roof_mesh_ref").type.equals(pa.string())


# --------------------------------------------------------------------------- real data (skipped when absent)
def _skip_unless(path: Path):
    if not path.exists():
        pytest.skip(f"{path} not produced yet")


@pytest.fixture(scope="module")
def real_index() -> pd.DataFrame:
    _skip_unless(INDEX)
    return pq.read_table(INDEX).to_pandas()


def test_real_index_bin_match_rate(real_index):
    _skip_unless(FOOTPRINTS)
    fp = pq.read_table(FOOTPRINTS, columns=["bin", "ground_z", "height"]).to_pandas().drop_duplicates("bin")
    ok = real_index[real_index.bin_ok]
    matched = ok.bin.isin(set(fp.bin)).mean()
    assert len(ok) > 0
    assert matched > 0.97, f"BIN match rate {matched:.4f} against footprints_raw is too low"


def test_real_index_roof_height_agrees_with_footprints(real_index):
    _skip_unless(FOOTPRINTS)
    fp = pq.read_table(FOOTPRINTS, columns=["bin", "ground_z", "height"]).to_pandas().drop_duplicates("bin")
    m = real_index[real_index.bin_ok].merge(fp, on="bin")
    dz = (m.z_roof_max - (m.ground_z + m.height)).abs()
    assert float(dz.median()) < 0.10, f"median |dz_roof| {dz.median():.3f} m"
    assert float((dz <= 1.0).mean()) > 0.95


def test_real_index_is_one_row_per_bin(real_index):
    ok = real_index[real_index.bin_ok]
    assert ok.bin.is_unique
    assert (real_index.tri_count > 0).all()


NON_FLAT_MAX_FRAC = 1e-4        # ADR-013: only hand-modelled landmarks carry sloped LOD2 geometry


def test_real_delivery_is_flat_massing(real_index):
    """ADR-013: the NYC 3-D Building Model models flat massing for essentially every building.

    A handful of hand-modelled landmarks (Statue of Liberty, Brooklyn Museum, Barclays Center, ...) do
    carry sloped geometry, so this asserts a fraction rather than zero. If DoITT ever publishes sloped
    LOD2 for the ordinary stock this fails loudly, which is the point: the ``roof_type`` fallback in
    ``citygml_join`` must then be revisited.
    """
    hist = real_index.roof_type.value_counts()
    non_flat = len(real_index) - int(hist.get(R.ROOF_FLAT, 0))
    assert non_flat / len(real_index) < NON_FLAT_MAX_FRAC, \
        f"{non_flat} non-flat CityGML roofs ({hist.to_dict()}) - revisit ADR-013 and citygml_join"


def test_real_progress_counters_show_flat_roof_faces():
    """Every parsed delivery area: the roof faces are horizontal apart from the landmark handful."""
    _skip_unless(CITYGML_DIR / "progress.json")
    doc = json.loads((CITYGML_DIR / "progress.json").read_text())
    done = [v for v in doc["das"].values() if v.get("status") == "done"]
    if not done:
        pytest.skip("no delivery area finished yet")
    horizontal = sum(v["counters"].get("roof_face_horizontal", 0) for v in done)
    sloped = sum(v["counters"].get("roof_face_sloped", 0) for v in done)
    assert horizontal > 0
    assert sloped / (sloped + horizontal) < 1e-2, \
        f"{sloped} of {sloped + horizontal} roof faces are sloped - ADR-013 no longer holds"
    # and they concentrate in a negligible number of buildings
    flat_rows = sum(v["counters"].get("roof_type_flat", 0) for v in done)
    total_rows = sum(v["rows"] or 0 for v in done)
    assert flat_rows >= total_rows * (1.0 - NON_FLAT_MAX_FRAC)


def test_real_roof_evidence_json_is_conclusive():
    p = VERIFICATION / "citygml" / "roof_evidence_da4_queens.json"
    _skip_unless(p)
    ev = json.loads(p.read_text())
    assert ev["roof_faces_scanned"] > 1000
    assert ev["max_slope_deg_seen"] == 0.0
    assert ev["fraction_faces_sloped_ge_1deg"] == 0.0
    assert not ev["buildings_missing"]
    for b in ev["buildings"]:
        assert b["max_slope_deg"] == 0.0
        for f in b["roof_faces"]:
            assert f["z_range_ft"] == 0.0


def test_real_roof_attrs_contract():
    _skip_unless(ROOF_ATTRS)
    t = pq.read_table(ROOF_ATTRS)
    assert t.schema.metadata[b"nycsim.schema"].decode() == J.SCHEMA_ID
    for f in J.SCHEMA:
        assert t.schema.field(f.name).type.equals(f.type), f.name
    d = t.to_pandas()
    assert d.bin.is_unique and (d.bin > 0).all()
    assert d.roof_type.between(0, len(R.ROOF_NAMES) - 1).all()
    assert d.roof_type_source.between(0, len(J.SOURCE_NAMES) - 1).all()
    assert (d.loc[d.citygml_match, "roof_mesh_ref"].str.len() > 0).all()
    assert (d.loc[~d.citygml_match, "roof_mesh_ref"] == "").all()
    assert d.loc[~d.citygml_match, "z_roof_max"].isna().all()
    # inferred pitched roofs carry usable geometry, flats carry none
    pitched = d[d.roof_type_source == J.SRC_INFERRED]
    if len(pitched):
        assert (pitched.roof_pitch_deg > 0).all() and pitched.roof_ridge_deg.notna().all()
        assert (pitched.roof_ridge_dz_m > 0).all()
        assert np.allclose(pitched.roof_eave_dz_m, -pitched.roof_ridge_dz_m, atol=1e-5)
    flat_default = d[d.roof_type_source == J.SRC_DEFAULT]
    assert (flat_default.roof_type == R.ROOF_FLAT).all()
    assert (flat_default.roof_pitch_deg == 0).all()
    assert d.roof_inferred.equals(d.roof_type_source >= J.SRC_INFERRED)


# --------------------------------------------------------------------------- buildings-stage interface
def _fake_roof_attrs(tmp_path: Path, rows: list[dict]) -> Path:
    import pyarrow as pa_
    full = []
    for r in rows:
        d = {"bin": 0, "roof_type": 0, "n_roof_levels": 0, "z_roof_max": float("nan"), "roof_mesh_ref": "",
             "citygml_match": False, "dz_vs_footprint_m": float("nan"), "roof_type_source": J.SRC_DEFAULT,
             "roof_inferred": True, "roof_type_conf": 0.0, "roof_pitch_deg": 0.0, "roof_ridge_deg": float("nan"),
             "roof_eave_dz_m": 0.0, "roof_ridge_dz_m": 0.0, "z_ground_min": float("nan"), "tri_count": 0,
             "citygml_da": 0, "citygml_flags": 0}
        d.update(r)
        full.append(d)
    p = tmp_path / "roof_attrs.parquet"
    pq.write_table(pa_.Table.from_pylist(full, schema=J.SCHEMA), p)
    return p


def test_attach_roof_columns_sets_type_mesh_and_fidelity(tmp_path):
    from nycsim_pipeline.buildings.schema import Fidelity
    ra = _fake_roof_attrs(tmp_path, [
        {"bin": 1, "roof_type": R.ROOF_GABLE, "roof_mesh_ref": "", "citygml_match": False},
        {"bin": 2, "roof_type": R.ROOF_FLAT, "roof_mesh_ref": "t_1_2/roofs.glb#bin_2", "citygml_match": True},
    ])
    df = pd.DataFrame({"bin": [2, 1, 3], "fidelity": np.array([1, 1, 1], dtype=np.uint16)})
    out = J.attach_roof_columns(df, roof_attrs=ra)
    assert list(out.bin) == [2, 1, 3]                              # order preserved
    assert list(out.roof_type) == [R.ROOF_FLAT, R.ROOF_GABLE, R.ROOF_FLAT]
    assert list(out.roof_mesh_ref) == ["t_1_2/roofs.glb#bin_2", "", ""]
    assert out.roof_type.dtype == np.int8 and out.fidelity.dtype == np.uint16
    real = (out.fidelity.to_numpy() & Fidelity.ROOF_REAL.mask) != 0
    assert list(real) == [True, False, False]                      # only the BIN with a mesh
    assert "citygml_match" not in out.columns


def test_attach_roof_columns_without_the_artefact(tmp_path):
    df = pd.DataFrame({"bin": [1, 2], "fidelity": np.array([1, 1], dtype=np.uint16)})
    out = J.attach_roof_columns(df, roof_attrs=tmp_path / "missing.parquet")
    assert (out.roof_type == R.ROOF_FLAT).all() and (out.roof_mesh_ref == "").all()
    assert (out.fidelity == 1).all()
    with pytest.raises(FileNotFoundError):
        J.attach_roof_columns(df, roof_attrs=tmp_path / "missing.parquet", strict=True)


def test_attach_roof_columns_needs_bin_and_fidelity(tmp_path):
    ra = _fake_roof_attrs(tmp_path, [{"bin": 1}])
    with pytest.raises(KeyError):
        J.attach_roof_columns(pd.DataFrame({"b": [1]}), roof_attrs=ra)
    with pytest.raises(KeyError):
        J.attach_roof_columns(pd.DataFrame({"bin": [1]}), roof_attrs=ra)
    out = J.attach_roof_columns(pd.DataFrame({"bin": [1]}), roof_attrs=ra, set_fidelity=False)
    assert out.roof_type.iloc[0] == R.ROOF_FLAT
