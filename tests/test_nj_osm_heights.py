"""Verification tests for the OpenStreetMap height join on the New Jersey table (deviation B11a).

These are written to fail if the join is *wrong*, not to restate that it ran.  Each one is aimed at
a specific way this change could have gone bad:

* a height that moved on a row with no matched footprint under it — the join reaching further than
  its own evidence;
* a match that is not really the same building — the accepted pairs are re-measured from the two
  geometries here, and required to be one-to-one;
* ``HEIGHT_REAL`` on a height nobody measured — a storey count times an assumed storey height is an
  inference and must carry ``HEIGHT_INFERRED``, whatever it replaced;
* a levels derivation firing where the source did not fall short, or a tag value in the table that
  is not the tag value in the extract;
* a corrected height leaving a stale floor count, roof elevation or material behind it;
* the fidelity bits read as masks instead of indices, which has happened in this project before;
* the acceptance test moving the wrong way, or being reported on a different population than the
  one deviation B11a quotes.

Run: ``python3 -m pytest tests/test_nj_osm_heights.py -v``
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import polars as pl
import pyarrow.parquet as pq
import pytest
import shapely

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "pipeline"))

from nycsim_pipeline.buildings import nj_osm_heights as oh  # noqa: E402
from nycsim_pipeline.buildings import nj_tiles as nj  # noqa: E402
from nycsim_pipeline.buildings import schema as S  # noqa: E402
from nycsim_pipeline.paths import PROCESSED  # noqa: E402

BASE = PROCESSED / "buildings_nj" / "buildings_nj_base.parquet"
SUMMARY = PROCESSED / "buildings_nj" / "buildings_nj_summary.json"
OSM = oh.OSM_BUILDINGS_NJ
SOURCE = nj.SOURCE_PARQUET

OSM_SOURCES = (S.SRC_OSM_HEIGHT, S.SRC_OSM_LEVELS)
REAL_SOURCES = (S.SRC_LIDAR, S.SRC_OSM_HEIGHT)


@pytest.fixture(scope="session")
def table() -> pl.DataFrame:
    if not BASE.exists():
        pytest.skip("the New Jersey buildings stage has not been run")
    return pl.read_parquet(BASE)


@pytest.fixture(scope="session")
def summary() -> dict:
    if not SUMMARY.exists():
        pytest.skip("the New Jersey summary has not been written")
    return json.loads(SUMMARY.read_text())


@pytest.fixture(scope="session")
def osm_tags() -> pl.DataFrame:
    if not OSM.exists():
        pytest.skip(f"{OSM} missing")
    return pl.read_parquet(OSM, columns=["osm_id", "height", "levels", "geometry"])


def _occ_storeys(occ: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    fh = np.array([nj._OCC_FLOORS.get(str(o), nj._OCC_FLOORS_DEFAULT)[0] for o in occ])
    gf = np.array([nj._OCC_FLOORS.get(str(o), nj._OCC_FLOORS_DEFAULT)[1] for o in occ])
    return fh, gf


# --------------------------------------------------------------------------- the bits themselves
def test_the_fidelity_bits_are_indices_and_are_used_as_indices():
    """A bit *index* used as a mask sets the wrong bit.  That mistake has been made here before."""
    assert int(S.Fidelity.HEIGHT_REAL) == 1 and S.Fidelity.HEIGHT_REAL.mask == 2
    assert int(S.Fidelity.HEIGHT_INFERRED) == 11 and S.Fidelity.HEIGHT_INFERRED.mask == 2048
    assert int(S.Fidelity.FOOTPRINT_REAL) == 0 and S.Fidelity.FOOTPRINT_REAL.mask == 1
    # every bit the enum names is distinct and no mask collides with another bit's index
    idx = [int(b) for b in S.Fidelity]
    assert len(set(idx)) == len(idx)


def test_no_published_row_sets_a_bit_the_schema_does_not_name(table):
    highest = max(int(b) for b in S.Fidelity)
    fid = table["fidelity"].to_numpy().astype(np.uint32)
    assert int((fid >> (highest + 1)).max()) == 0, "a New Jersey row sets a fidelity bit nothing names"


def test_height_real_and_height_inferred_follow_height_source_row_for_row(table):
    fid = table["fidelity"].to_numpy().astype(np.uint32)
    src = table["height_source"].to_numpy()
    real = ((fid >> int(S.Fidelity.HEIGHT_REAL)) & 1).astype(bool)
    inf = ((fid >> int(S.Fidelity.HEIGHT_INFERRED)) & 1).astype(bool)
    expect_real = np.isin(src, REAL_SOURCES)
    assert np.array_equal(real, expect_real), (
        f"HEIGHT_REAL disagrees with height_source on {int((real != expect_real).sum())} rows")
    assert np.array_equal(inf, ~expect_real)
    assert not (real & inf).any(), "a row claims both a real and an inferred height"
    assert set(np.unique(src).tolist()) <= {S.SRC_LIDAR, S.SRC_NEIGHBOURS, S.SRC_OSM_HEIGHT, S.SRC_OSM_LEVELS}


def test_a_levels_derivation_is_never_flagged_real(table):
    """A storey count times an assumed storey height is an inference, whatever it replaced."""
    fid = table["fidelity"].to_numpy().astype(np.uint32)
    lev = table["height_source"].to_numpy() == S.SRC_OSM_LEVELS
    assert lev.sum() > 0, "no row took a levels derivation: this test would be vacuous"
    assert not ((fid[lev] >> int(S.Fidelity.HEIGHT_REAL)) & 1).any(), (
        "a height derived from building:levels claims HEIGHT_REAL")
    assert ((fid[lev] >> int(S.Fidelity.HEIGHT_INFERRED)) & 1).all()
    # and it really did replace real source heights in some rows -- otherwise the trade is untested
    src_h = table["source_height_m"].to_numpy()
    assert np.isfinite(src_h[lev]).all()


# --------------------------------------------------------------------------- the join's reach
def test_no_height_moved_without_a_matched_footprint_under_it(table):
    """Heights may only improve where a match was made."""
    h = table["height"].to_numpy().astype(np.float64)
    src = table["source_height_m"].to_numpy().astype(np.float64)
    osm_id = table["osm_id"].to_numpy()
    iou = table["osm_match_iou"].to_numpy().astype(np.float64)
    moved = h != src
    assert moved.sum() > 0, "nothing changed: this test would be vacuous"
    assert (osm_id[moved] != 0).all(), (
        f"{int((osm_id[moved] == 0).sum())} rows changed height with no matched OpenStreetMap outline")
    assert (iou[moved] >= oh.MATCH_MIN_IOU - 1e-6).all(), "a height moved on a below-threshold match"
    # ... and the converse: an unmatched row is the source verbatim
    assert np.array_equal(h[osm_id == 0], src[osm_id == 0])


def test_no_building_gained_a_height_it_has_no_evidence_for(table, osm_tags):
    """Every changed row must carry a real tag on the outline it matched, read back from the extract."""
    h = table["height"].to_numpy().astype(np.float64)
    src = table["source_height_m"].to_numpy().astype(np.float64)
    osm_id = table["osm_id"].to_numpy()
    moved = np.nonzero(h != src)[0]
    tag = {int(i): (float(a) if a is not None else np.nan, float(b) if b is not None else np.nan)
           for i, a, b in zip(osm_tags["osm_id"], osm_tags["height"], osm_tags["levels"])}
    for i in moved:
        th, tl = tag.get(int(osm_id[i]), (np.nan, np.nan))
        assert np.isfinite(th) or np.isfinite(tl), (
            f"row {i} changed from {src[i]:.2f} to {h[i]:.2f} m but osm_id {osm_id[i]} carries no tag")


def test_the_tag_columns_are_the_tag_values_in_the_extract(table, osm_tags):
    osm_id = table["osm_id"].to_numpy()
    th = table["osm_height_m"].to_numpy().astype(np.float64)
    tl = table["osm_levels"].to_numpy().astype(np.int64)
    lookup = {int(i): (a, b) for i, a, b in zip(osm_tags["osm_id"], osm_tags["height"], osm_tags["levels"])}
    m = np.nonzero(osm_id != 0)[0]
    rng = np.random.default_rng(11)
    for i in rng.choice(m, size=min(3000, len(m)), replace=False):
        a, b = lookup[int(osm_id[i])]
        if a is None or not np.isfinite(a):
            assert not np.isfinite(th[i]), f"row {i} invented a height tag"
        else:
            assert abs(th[i] - a) < 1e-3, f"row {i} height tag {th[i]} != extract {a}"
        assert tl[i] == (0 if b is None or not np.isfinite(b) else int(min(b, 32767))), f"row {i} levels tag"
    # an unmatched row claims no tag at all
    u = osm_id == 0
    assert not np.isfinite(th[u]).any() and (tl[u] == 0).all()


def test_every_accepted_match_really_covers_both_polygons_and_is_one_to_one(table):
    """Re-measure the accepted pairs from the two geometries; the table must not be taking this on trust."""
    osm_id = table["osm_id"].to_numpy()
    matched = np.nonzero(osm_id != 0)[0]
    assert len(matched) > 10_000
    assert len(set(osm_id[matched].tolist())) == len(matched), "an OpenStreetMap outline was matched twice"

    osm = pl.read_parquet(OSM, columns=["osm_id", "geometry"])
    og = shapely.from_wkb(osm["geometry"].to_numpy())
    by_id = {int(i): k for k, i in enumerate(osm["osm_id"])}
    fp = table["footprint"].to_numpy()
    iou_col = table["osm_match_iou"].to_numpy().astype(np.float64)
    rng = np.random.default_rng(23)
    for i in rng.choice(matched, size=400, replace=False):
        a = shapely.from_wkb(fp[i])
        b = og[by_id[int(osm_id[i])]]
        inter = shapely.area(shapely.intersection(a, b))
        union = shapely.area(a) + shapely.area(b) - inter
        iou = inter / max(union, 1e-9)
        assert iou >= oh.MATCH_MIN_IOU - 1e-6, f"row {i} matched at IoU {iou:.3f}"
        assert abs(iou - iou_col[i]) < 1e-3, f"row {i} publishes IoU {iou_col[i]:.4f}, measured {iou:.4f}"


def test_the_match_rate_in_the_summary_is_the_one_in_the_table(table, summary):
    m = summary["attributes"]["osm_join"]["match"]
    assert m["min_iou"] == oh.MATCH_MIN_IOU
    matched = int((table["osm_id"].to_numpy() != 0).sum())
    assert m["matched"] == matched
    assert abs(m["match_rate_pct"] - 100.0 * matched / table.height) < 0.01
    assert m["osm_footprints_contested"] == 0 and m["nj_footprints_contested"] < 100


# --------------------------------------------------------------------------- the rules
def test_a_kept_row_is_the_source_height_verbatim(table):
    src_tab = pq.read_table(SOURCE, columns=["build_id", "height_m"])
    lookup = {int(b): (float(h) if h is not None else np.nan)
              for b, h in zip(src_tab["build_id"].to_pylist(), src_tab["height_m"].to_pylist())}
    build = table["build_id"].to_numpy()
    h = table["height"].to_numpy().astype(np.float64)
    hs = table["height_source"].to_numpy()
    keep = np.nonzero(hs == S.SRC_LIDAR)[0]
    rng = np.random.default_rng(5)
    for i in rng.choice(keep, size=5000, replace=False):
        assert abs(h[i] - lookup[int(build[i])]) < 1e-3, f"row {i} rescaled a SRC_LIDAR height"


def test_an_osm_tag_row_publishes_the_tag_exactly(table):
    h = table["height"].to_numpy().astype(np.float64)
    th = table["osm_height_m"].to_numpy().astype(np.float64)
    sel = table["height_source"].to_numpy() == S.SRC_OSM_HEIGHT
    assert sel.sum() > 0
    assert np.abs(h[sel] - th[sel]).max() < 1e-3, "a SRC_OSM_HEIGHT row is not the tag it cites"
    assert (th[sel] >= oh.MIN_OSM_HEIGHT_M).all() and (th[sel] < oh.MAX_OSM_HEIGHT_M).all()


def test_a_levels_row_is_exactly_the_storey_derivation_and_round_trips(table):
    occ = table["occ_class"].fill_null("Unclassified").to_numpy().astype(object)
    fh, gf = _occ_storeys(occ)
    h = table["height"].to_numpy().astype(np.float64)
    lv = table["osm_levels"].to_numpy().astype(np.float64)
    floors = table["floors"].to_numpy().astype(np.int64)
    sel = table["height_source"].to_numpy() == S.SRC_OSM_LEVELS
    assert sel.sum() > 0
    assert (lv[sel] >= oh.MIN_OSM_LEVELS).all() and (lv[sel] <= oh.MAX_OSM_LEVELS).all()
    want = oh.height_from_levels(lv[sel], fh[sel], gf[sel])
    assert np.abs(h[sel] - want).max() < 1e-3, "a SRC_OSM_LEVELS height is not the storey derivation"
    # the derivation and the floor rule are inverses, so the published floor count is the tagged one
    assert np.array_equal(floors[sel], lv[sel].astype(np.int64)), (
        "a levels-derived building publishes a floor count that is not the storey count it came from")


def test_the_levels_rule_only_fires_where_the_source_falls_short_or_never_measured(table):
    """The one-sided rule is the point: a levels tag below the source height is usually a podium."""
    occ = table["occ_class"].fill_null("Unclassified").to_numpy().astype(object)
    fh, gf = _occ_storeys(occ)
    src = table["source_height_m"].to_numpy().astype(np.float64)
    lv = table["osm_levels"].to_numpy().astype(np.float64)
    fid = table["fidelity"].to_numpy().astype(np.uint32)
    hs = table["height_source"].to_numpy()
    sel = np.nonzero(hs == S.SRC_OSM_LEVELS)[0]
    implied = oh.floors_from_height(src, fh, gf)
    src_tab = pq.read_table(SOURCE, columns=["build_id", "height_m"])
    lookup = {int(b): (float(x) if x is not None else np.nan)
              for b, x in zip(src_tab["build_id"].to_pylist(), src_tab["height_m"].to_pylist())}
    build = table["build_id"].to_numpy()
    for i in sel:
        raw = lookup[int(build[i])]
        source_measured = np.isfinite(raw) and 0 < raw < nj.MAX_PLAUSIBLE_HEIGHT_M
        short = implied[i] - lv[i]
        assert (short <= -oh.LEVELS_SHORTFALL_STOREYS) or not source_measured, (
            f"row {i}: levels rule fired with the source only {-short:.0f} storeys short "
            f"and a measured height of {raw}")
    # and nowhere did a tagged row with an agreeing source get rewritten
    agreeing = (lv >= 1) & (np.abs(implied - lv) <= 1) & np.isfinite(src)
    assert not (agreeing & (hs == S.SRC_OSM_LEVELS) & ((fid >> int(S.Fidelity.HEIGHT_REAL)) & 1).astype(bool)).any()


def test_the_storey_table_used_here_is_the_one_the_stage_derives_floors_with():
    """The derivation and its inverse must share a table, or a building's height and floor count part."""
    for cls, (fh, gf) in nj._OCC_FLOORS.items():
        levels = np.arange(1, 60, dtype=np.float64)
        f = np.full(len(levels), fh)
        g = np.full(len(levels), gf)
        h = oh.height_from_levels(levels, f, g)
        assert np.array_equal(oh.floors_from_height(h, f, g), levels.astype(np.int32)), cls


# --------------------------------------------------------------------------- consistency downstream
def test_every_height_derived_column_agrees_with_the_published_height(table):
    """A corrected height must not leave a stale floor count, roof elevation or material behind."""
    occ = table["occ_class"].fill_null("Unclassified").to_numpy().astype(object)
    county = table["county"].fill_null("").to_numpy().astype(object)
    area = table["footprint_area"].to_numpy().astype(np.float64)
    h = table["height"].to_numpy().astype(np.float64)
    fh, gf = _occ_storeys(occ)

    floors = np.clip(np.where(h <= gf + 0.5 * fh, 1, 1 + np.rint((h - gf) / fh)), 1, 200).astype(np.int64)
    assert np.array_equal(table["floors"].to_numpy().astype(np.int64), floors), "floors disagree with height"

    gz = table["ground_z"].to_numpy().astype(np.float64)
    rz = table["roof_z"].to_numpy().astype(np.float64)
    assert np.abs(rz - (gz + h)).max() < 5e-3, "roof_z is not ground_z + height"

    mat = nj._material_from_occupancy(occ, county, h, area)
    assert np.array_equal(table["material_primary"].to_numpy(), mat), "material disagrees with height"

    fl = floors.astype(np.float64)
    gfh = np.where(fl <= 1, h, np.clip(gf, 2.2, np.maximum(h - (fl - 1) * 2.2, 2.2)))
    assert np.abs(table["ground_floor_height"].to_numpy().astype(np.float64) - gfh).max() < 5e-3
    fhh = np.where(fl > 1, (h - gfh) / np.maximum(fl - 1, 1), fh)
    assert np.abs(table["floor_height"].to_numpy().astype(np.float64) - fhh).max() < 5e-3


def test_disabling_the_join_reproduces_the_source_only_table(table):
    """``--no-osm`` must give back exactly what this stage published before B11a was closed."""
    sub = table.head(20000)
    ground = sub["ground_z"].to_numpy().astype(np.float64)
    df = sub.rename({"height_m": "h_ignored"}) if "height_m" in sub.columns else sub
    df = df.with_columns(pl.col("source_height_m").cast(pl.Float64).alias("height_m"))
    out, stats = nj.resolve_attributes(df.drop(["height", "roof_z", "floors", "floor_height",
                                                "ground_floor_height", "material_primary",
                                                "height_source", "floors_source", "ground_source",
                                                "fidelity", "osm_id", "osm_match_iou",
                                                "osm_height_m", "osm_levels", "source_height_m"]),
                                       ground, None, use_osm=False)
    assert stats["osm_join"] == {"applied": False}
    assert np.abs(out["height"].to_numpy().astype(np.float64) - sub["source_height_m"].to_numpy()).max() < 1e-3


# --------------------------------------------------------------------------- the acceptance test
def test_the_reference_comparison_still_reproduces_the_error_it_was_written_to_measure(summary):
    """The "before" half must be the population deviation B11a quotes, not a friendlier one."""
    rep = summary["height_investigation"]["against_published_tower_heights"]
    assert rep["available"] and rep["paired_on_the_same_footprints"] is True
    before = rep["before_source_height"]
    assert before["all_towers_with_a_source_height"]["with_a_source_height"] == 39
    assert before["all_towers_with_a_source_height"]["n_within_10_pct"] == 0
    stood = before["already_built_when_the_imagery_was_flown"]
    assert stood["with_a_source_height"] == 25
    assert abs(stood["median_error_m"] - (-66.41)) < 0.01
    assert abs(stood["median_error_pct"] - (-54.4)) < 0.1
    assert stood["n_short_by_over_20m"] == 20


def test_the_reference_comparison_improved_on_the_population_it_is_judged_on(summary):
    """The acceptance test for B11a: the 25 pre-imagery towers, before against after, same footprints."""
    rep = summary["height_investigation"]["against_published_tower_heights"]
    before = rep["before_source_height"]["already_built_when_the_imagery_was_flown"]
    after = rep["after_osm_join"]["already_built_when_the_imagery_was_flown"]
    assert after["with_a_source_height"] == before["with_a_source_height"], "the population moved"
    assert after["median_error_m"] > before["median_error_m"], (
        f"median error on the pre-imagery towers did not improve: {before['median_error_m']} -> "
        f"{after['median_error_m']}")
    assert after["median_error_m"] <= 0.0, "the correction overshot the published heights"
    assert after["n_short_by_over_20m"] < before["n_short_by_over_20m"]
    assert after["n_within_10_pct"] > before["n_within_10_pct"]
    assert rep["towers_improved"] > rep["towers_made_worse"]
    assert rep["towers_made_worse"] <= 2, rep["made_worse"]


def test_the_towers_the_join_could_not_reach_are_counted_not_hidden(summary):
    t = summary["attributes"]["osm_join"]["tall_tags_the_join_could_not_use"]
    assert t["tall_tags"] >= t["unmatched"] > 0
    assert len(t["towers"]) == t["unmatched"]
    for r in t["towers"]:
        assert r["osm_height_m"] >= t["min_height_m"]
        assert r["candidates"] == 0 or r["best_iou"] < oh.MATCH_MIN_IOU, (
            f"{r['name']} is listed as unjoined but reaches IoU {r.get('best_iou')}")


def test_the_tag_reach_is_reported_against_an_honest_denominator(summary):
    """A tag over a part of New Jersey this project does not model is not a failed match."""
    r = summary["attributes"]["osm_join"]["tags_in_the_extract"]
    for kind in ("height_tags", "levels_tags", "tagged_outlines"):
        total, over, matched = r[kind], r[f"{kind}_over_the_table"], r[f"{kind}_matched"]
        assert matched <= over <= total, kind
        assert over > 0 and matched > 0, kind
    # the extract really is wider than the table: most height tags are over ground it does not cover
    assert r["height_tags_over_the_table"] < r["height_tags"]


def test_the_openstreetmap_cross_check_separates_the_rows_it_is_still_independent_on(summary):
    rep = summary["height_investigation"]["against_openstreetmap_height_tags"]
    assert rep["available"] and rep["matched"] > 0
    ind = rep["published_where_the_tag_was_not_used"]
    assert ind["n"] == rep["matched"] - rep["published_where_the_tag_was_used"]
    assert set(ind["source_by_band"]) == set(ind["published_by_band"])
