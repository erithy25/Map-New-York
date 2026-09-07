"""Tests for the OSM tree source: the extraction (``osm/trees.parquet``) and its placement as tree props.

The 2015 census is a street inventory, so the parks in this world were empty (DEVIATIONS D10). These tests
guard the second source that fills them and, more importantly, guard the three ways it could quietly lie:
by planting a tree the census already has, by inventing a dimension OSM does not publish, or by losing the
provenance that lets a reader separate the two inventories.

Unit tests run on synthetic inputs and are always executed. The integration tests at the bottom read the real
``tiles/{tile}/props.parquet`` and are skipped until the furniture stage has been re-run with the OSM source;
point ``NYCSIM_TILES_ROOT`` at a subset run to exercise them on a handful of tiles.

Run:  PYTHONPATH=pipeline python3 -m pytest pipeline/tests/test_osm_trees.py -q
"""
from __future__ import annotations

import json
import math
import os
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pytest
import shapely

from nycsim_pipeline.furniture import allometry, catalog, datasets, dedupe
from nycsim_pipeline.osm import trees as osm_trees
from nycsim_pipeline.paths import PROCESSED
from scipy.spatial import cKDTree

TILES = Path(os.environ.get("NYCSIM_TILES_ROOT", PROCESSED / "tiles"))
OSM = PROCESSED / "osm"
TREE_KIND = catalog.KIND_ID["tree"]
CENSUS = "street_trees_2015"
OSM_DATASET = "osm_newyork_pbf"

# The park set DEVIATIONS D10 counts: OSM green polygons of 2 ha or more that are parks or woodland.
# It reproduces D10's figures exactly (1,916 polygons, 1,756 of them without a census tree, 219.3 km²).
PARK_VALUES = ("park", "wood", "recreation_ground", "nature_reserve", "forest")
PARK_MIN_AREA_M2 = 20_000.0
D10_EMPTY_PARKS = 1756          # the baseline this work has to beat


# --------------------------------------------------------------------------------------- fake OSM tags

class _Tag:
    def __init__(self, k: str, v: str) -> None:
        self.k, self.v = k, v


class _Tags:
    """The two things :func:`osm_trees._tag_columns` uses from an osmium tag list: ``get`` and iteration."""

    def __init__(self, d: dict[str, str]) -> None:
        self._d = dict(d)

    def get(self, k: str, default=None):
        return self._d.get(k, default)

    def __iter__(self):
        return iter([_Tag(k, v) for k, v in self._d.items()])


# --------------------------------------------------------------------------------------- extraction

def test_named_columns_and_the_tag_blob_agree():
    tags = _Tags({"natural": "tree", "species": "Quercus bicolor", "genus": "Quercus", "leaf_type": "broadleaved",
                  "leaf_cycle": "deciduous", "denotation": "park", "height": "7", "circumference": "26\"",
                  "diameter_crown": "18.9", "diameter": "10m", "operator": "NYC Parks", "surprise": "kept anyway"})
    row = osm_trees._tag_columns(tags)
    assert row["species"] == "Quercus bicolor" and row["genus"] == "Quercus"
    assert row["leaf_type"] == "broadleaved" and row["denotation"] == "park"
    assert row["height_m"] == pytest.approx(7.0)
    # the dimensions OSM does not state in one unit convention stay raw strings
    assert row["circumference_raw"] == "26\"" and row["diameter_crown_raw"] == "18.9" and row["diameter_raw"] == "10m"
    # nothing is lost: a tag with no column of its own survives in the blob
    assert json.loads(row["tags"])["surprise"] == "kept anyway"
    assert set(json.loads(row["tags"])) == set(tags._d)


def test_absent_tags_stay_absent():
    row = osm_trees._tag_columns(_Tags({"natural": "tree"}))
    assert row["species"] == "" and row["genus"] == "" and row["denotation"] == ""
    assert row["height_raw"] == "" and math.isnan(row["height_m"])
    assert row["circumference_raw"] == "" and row["diameter_raw"] == ""


def test_an_unparsable_height_becomes_no_height_rather_than_a_guess():
    # 6 of the 71,447 nodes carry a species name in the height field
    row = osm_trees._tag_columns(_Tags({"natural": "tree", "height": "Platanus Platanus"}))
    assert row["height_raw"] == "Platanus Platanus"
    assert math.isnan(row["height_m"])


def test_the_schemas_name_every_column_the_placement_reads():
    needed = {"osm_id", "x", "y", "species", "genus", "taxon", "leaf_type", "leaf_cycle", "denotation", "name",
              "ref", "start_date", "operator", "height_m", "height_raw", "circumference_raw",
              "diameter_crown_raw", "diameter_raw"}
    assert needed <= set(osm_trees.TREE_SCHEMA.names)
    assert "tags" in osm_trees.TREE_SCHEMA.names
    assert "geometry" in osm_trees.TREE_ROW_SCHEMA.names and "length_m" in osm_trees.TREE_ROW_SCHEMA.names


# --------------------------------------------------------------------------------------- placement

def _tree_parquet(tmp_path: Path, rows: list[dict]) -> Path:
    """Write a ``trees.parquet`` fixture with the real extraction schema."""
    schema = osm_trees.TREE_SCHEMA
    cols = {}
    for f in schema:
        default = "" if pa.types.is_string(f.type) else (math.nan if pa.types.is_floating(f.type) else 0)
        cols[f.name] = [r.get(f.name, default) for r in rows]
    p = tmp_path / "trees.parquet"
    pq.write_table(pa.table(cols, schema=schema), p)
    return p


def test_osm_trees_carry_their_provenance(tmp_path):
    p = _tree_parquet(tmp_path, [{"osm_id": 1, "osm_type": "node", "x": 10.0, "y": 20.0},
                                 {"osm_id": 2, "osm_type": "node", "x": 40.0, "y": 20.0}])
    cols = datasets.load_osm_trees(p)
    assert list(np.asarray(cols["kind"])) == [TREE_KIND, TREE_KIND]
    assert list(np.asarray(cols["source"])) == [catalog.SOURCE_DATASET, catalog.SOURCE_DATASET]
    assert cols["dataset_id"] == [OSM_DATASET, OSM_DATASET]
    assert cols["dataset_id"][0] != CENSUS, "a reader must be able to separate the two tree inventories"
    assert [json.loads(a)["osm_id"] for a in cols["attrs"]] == [1, 2]


def test_no_dbh_is_invented_from_any_osm_tag(tmp_path):
    """``circumference`` and ``diameter`` are carried raw and never converted into a trunk diameter."""
    p = _tree_parquet(tmp_path, [{"osm_id": 1, "x": 0.0, "y": 0.0, "circumference_raw": "1.91 m"},
                                 {"osm_id": 2, "x": 9.0, "y": 0.0, "diameter_raw": "115\""},
                                 {"osm_id": 3, "x": 18.0, "y": 0.0}])
    cols = datasets.load_osm_trees(p)
    assert np.all(np.asarray(cols["dbh_cm"]) == 0.0), "0 means the source records no trunk diameter"
    attrs = [json.loads(a) for a in cols["attrs"]]
    assert attrs[0]["circumference"] == "1.91 m" and attrs[1]["diameter"] == "115\""


def test_height_comes_from_the_tag_where_there_is_one_and_from_allometry_otherwise(tmp_path):
    p = _tree_parquet(tmp_path, [{"osm_id": 1, "x": 0.0, "y": 0.0, "height_m": 7.0, "height_raw": "7"},
                                 {"osm_id": 2, "x": 9.0, "y": 0.0},
                                 {"osm_id": 3, "x": 18.0, "y": 0.0, "height_raw": "Platanus Platanus",
                                  "height_m": math.nan},
                                 {"osm_id": 4, "x": 27.0, "y": 0.0, "species": "Quercus palustris"}])
    cols = datasets.load_osm_trees(p)
    hs = np.asarray(cols["height_source"])
    h = np.asarray(cols["height_m"])
    assert hs[0] == catalog.HEIGHT_SOURCE["measured"] and h[0] == pytest.approx(7.0)
    assert list(hs[1:]) == [catalog.HEIGHT_SOURCE["allometry"]] * 3
    # the allometric ones are the census's own curve with no DBH to feed it
    assert h[1] == pytest.approx(allometry.height_m("", 0.0))
    assert h[3] == pytest.approx(allometry.height_m("Quercus palustris", 0.0))
    assert h[3] != h[1], "a species OSM does give must reach the height curve"
    # and the unparsable one says so rather than disappearing
    assert json.loads(cols["attrs"][2])["height_tag_unparsed"] == "Platanus Platanus"


def test_species_is_set_only_where_osm_gives_one(tmp_path):
    p = _tree_parquet(tmp_path, [{"osm_id": 1, "x": 0.0, "y": 0.0, "species": "Quercus bicolor"},
                                 {"osm_id": 2, "x": 9.0, "y": 0.0, "genus": "Prunus"},
                                 {"osm_id": 3, "x": 18.0, "y": 0.0, "taxon": "Ginkgo biloba"},
                                 {"osm_id": 4, "x": 27.0, "y": 0.0}])
    cols = datasets.load_osm_trees(p)
    assert cols["species"] == ["Quercus bicolor", "", "Ginkgo biloba", ""], "a genus is not a species"
    # the genus is still recorded, and still reaches the height curve through its own lookup
    assert json.loads(cols["attrs"][1])["genus"] == "Prunus"
    assert np.asarray(cols["height_m"])[1] == pytest.approx(allometry.height_m("Prunus", 0.0))


def test_osm_trees_record_no_health(tmp_path):
    p = _tree_parquet(tmp_path, [{"osm_id": 1, "x": 0.0, "y": 0.0}])
    cols = datasets.load_osm_trees(p)
    assert np.asarray(cols["variant"])[0] == 3, "variant 3 is the catalog's 'health unknown'"


def test_tree_rows_are_never_placed(tmp_path):
    """``natural=tree_row`` is extracted and deliberately not turned into trunks (no count, no spacing)."""
    p = _tree_parquet(tmp_path, [{"osm_id": 1, "x": 0.0, "y": 0.0}, {"osm_id": 2, "x": 9.0, "y": 0.0}])
    pq.write_table(pa.table({f.name: [] for f in osm_trees.TREE_ROW_SCHEMA}, schema=osm_trees.TREE_ROW_SCHEMA),
                   tmp_path / "tree_rows.parquet")
    cols = datasets.load_osm_trees(p)
    assert len(cols["x"]) == 2, "only the node layer becomes props"
    assert datasets.OSM_TREES.name == "trees.parquet"


# --------------------------------------------------------------------------------------- the dedupe rule

def _rule() -> dedupe.CrossSourceRule:
    rules = [r for r in dedupe.CROSS_SOURCE_RULES if r.group == "tree"]
    assert len(rules) == 1, "exactly one cross-source rule governs trees"
    return rules[0]


def _tree_cols(xs, ys, datasets_):
    n = len(xs)
    return {"kind": np.full(n, TREE_KIND, dtype=np.int16), "x": np.asarray(xs, dtype=float),
            "y": np.asarray(ys, dtype=float), "dataset_id": list(datasets_),
            "source": np.zeros(n, dtype=np.int8)}


def test_the_radius_is_recorded_with_how_it_was_measured():
    r = _rule()
    assert r.keep_dataset == CENSUS and r.drop_dataset == OSM_DATASET
    assert 1.5 < r.radius_m <= 10.0
    assert "control" in r.basis, "the radius must carry the measurement it came from, not a round number"
    doc = catalog.catalog_json()
    assert doc["dedupe"]["cross_source"][0]["radius_m"] == r.radius_m


def test_an_osm_tree_inside_the_radius_is_dropped_and_one_outside_is_kept():
    r = _rule()
    eps = 0.01
    # the two OSM trees sit either side of the radius, and far enough apart not to meet each other
    cols = _tree_cols([0.0, r.radius_m - eps, -(r.radius_m + eps)], [0.0, 0.0, 0.0],
                      [CENSUS, OSM_DATASET, OSM_DATASET])
    keep, report = dedupe.dedupe(cols, {TREE_KIND: "tree"})
    assert list(keep) == [True, False, True]
    cross = [c for c in report["cross_source"] if c["group"] == "tree"][0]
    assert cross["rows_dropped"] == 1 and cross["radius_m"] == r.radius_m


def test_the_census_row_is_the_one_that_survives():
    r = _rule()
    cols = _tree_cols([0.0, 1.0], [0.0, 0.0], [OSM_DATASET, CENSUS])
    keep, _ = dedupe.dedupe(cols, {TREE_KIND: "tree"})
    assert list(keep) == [False, True]
    assert r.keep_dataset == CENSUS


def test_the_wider_radius_never_merges_two_rows_of_one_source():
    """A park mapped tree by tree has trees 4 m apart; the radius must not reach them."""
    r = _rule()
    d = r.radius_m - 0.5
    for source in (CENSUS, OSM_DATASET):
        cols = _tree_cols([0.0, d, 2 * d], [0.0, 0.0, 0.0], [source] * 3)
        keep, _ = dedupe.dedupe(cols, {TREE_KIND: "tree"})
        assert list(keep) == [True, True, True], f"{source} rows must survive each other at {d:.1f} m"


def test_the_rule_leaves_other_kinds_alone():
    names = catalog.KIND_ID
    n = 2
    cols = {"kind": np.array([names["hydrant"], names["bench"]], dtype=np.int16),
            "x": np.array([0.0, 2.0]), "y": np.array([0.0, 0.0]),
            "dataset_id": ["hydrants", OSM_DATASET], "source": np.zeros(n, dtype=np.int8)}
    keep, report = dedupe.dedupe(cols, {v: k for k, v in names.items()})
    assert list(keep) == [True, True]
    assert all(c["rows_dropped"] == 0 for c in report["cross_source"])


# --------------------------------------------------------------------------------------- integration

props_files = sorted(TILES.glob("*/props.parquet")) if TILES.exists() else []


def _trees() -> dict[str, np.ndarray]:
    cols = {k: [] for k in ("x", "y", "dataset_id", "source", "height_source", "height_m", "dbh_cm", "species")}
    for p in props_files:
        t = pq.read_table(p, columns=["kind", *cols])
        m = t.column("kind").to_numpy(zero_copy_only=False) == TREE_KIND
        if not m.any():
            continue
        for k in cols:
            col = t.column(k)
            v = np.asarray(col.to_pylist(), dtype=object) if pa.types.is_string(col.type) else col.to_numpy(zero_copy_only=False)
            cols[k].append(v[m])
    return {k: (np.concatenate(v) if v else np.array([])) for k, v in cols.items()}


TREES = _trees() if props_files else {}
HAS_OSM = bool(len(TREES.get("dataset_id", [])) and (TREES["dataset_id"] == OSM_DATASET).any())
needs_osm_trees = pytest.mark.skipif(
    not HAS_OSM, reason=f"no OSM trees in {TILES}; re-run the furniture stage (or set NYCSIM_TILES_ROOT)")


@needs_osm_trees
def test_no_osm_tree_stands_within_the_dedupe_radius_of_a_census_tree():
    r = _rule().radius_m
    osm = TREES["dataset_id"] == OSM_DATASET
    cen = TREES["dataset_id"] == CENSUS
    assert cen.sum() and osm.sum()
    d, _ = cKDTree(np.column_stack([TREES["x"][cen], TREES["y"][cen]])).query(
        np.column_stack([TREES["x"][osm], TREES["y"][osm]]), k=1, workers=1)
    assert d.min() > r, f"{int((d <= r).sum())} OSM trees stand within {r} m of a census tree"


@needs_osm_trees
def test_every_osm_tree_says_which_inventory_it_came_from():
    osm = TREES["dataset_id"] == OSM_DATASET
    assert np.all(TREES["source"][osm] == catalog.SOURCE_DATASET), "these are records, not rule placements"
    assert set(np.unique(TREES["dataset_id"]).tolist()) == {CENSUS, OSM_DATASET}
    assert (TREES["dataset_id"] == CENSUS).sum() > 0


@needs_osm_trees
def test_an_osm_tree_without_a_height_tag_gets_an_allometric_height_and_is_flagged():
    osm = TREES["dataset_id"] == OSM_DATASET
    hs = TREES["height_source"][osm]
    h = TREES["height_m"][osm]
    assert set(np.unique(hs).tolist()) <= {catalog.HEIGHT_SOURCE["measured"], catalog.HEIGHT_SOURCE["allometry"]}
    allom = hs == catalog.HEIGHT_SOURCE["allometry"]
    assert allom.any()
    assert np.all(np.isfinite(h)) and h[allom].min() > allometry.BREAST_HEIGHT_M
    # with no DBH the census curve degenerates to its own unknown-DBH default; the flag pair says so
    assert np.all(TREES["dbh_cm"][osm] == 0.0)
    assert h[allom].max() <= allometry.BREAST_HEIGHT_M + max(p[0] for p in allometry.SPECIES_PARAMS.values())
    tagged = hs == catalog.HEIGHT_SOURCE["measured"]
    if tagged.any():
        assert h[tagged].min() > 0.0, "a tagged height is carried as tagged, never clamped"


@needs_osm_trees
def test_species_is_present_only_where_osm_gives_one():
    osm = TREES["dataset_id"] == OSM_DATASET
    named = TREES["species"][osm] != ""
    # OSM tags a species on well under 1 % of its tree nodes; the column must not be padded out from the
    # genus, the leaf type or the census's own species list
    assert named.mean() < 0.10, f"{named.mean():.3%} of OSM trees carry a species — too many to be real"
    if osm.sum() > 20_000:                      # a whole-city run: some of them really do carry one
        assert named.any()


@pytest.mark.skipif(not (OSM / "landuse_leisure.parquet").exists(), reason="the osm stage has not been run")
@needs_osm_trees
def test_the_park_tree_counts_move():
    """The point of the whole exercise: parks that held no tree now hold the trees OSM records in them."""
    t = pq.read_table(OSM / "landuse_leisure.parquet", columns=["value", "area_m2", "geometry", "name"])
    value = np.asarray(t.column("value").to_pylist(), dtype=object)
    area = t.column("area_m2").to_numpy(zero_copy_only=False)
    sel = np.flatnonzero((area >= PARK_MIN_AREA_M2) & np.isin(value, PARK_VALUES))
    parks = shapely.from_wkb(t.column("geometry").to_pylist())[sel]
    names = np.asarray(t.column("name").to_pylist(), dtype=object)[sel]

    # a subset run only covers some tiles, so score the parks that lie inside the covered ground
    tx = np.floor(TREES["x"] / 1000.0).astype(int)
    ty = np.floor(TREES["y"] / 1000.0).astype(int)
    covered = shapely.box(tx.min() * 1000.0, ty.min() * 1000.0, (tx.max() + 1) * 1000.0, (ty.max() + 1) * 1000.0)
    inside = shapely.contains(covered, parks)
    parks, names = parks[inside], names[inside]
    assert len(parks) > 0

    def counts(mask: np.ndarray) -> np.ndarray:
        pts = shapely.points(TREES["x"][mask], TREES["y"][mask])
        hit = shapely.STRtree(pts).query(parks, predicate="contains")
        out = np.zeros(len(parks), dtype=int)
        np.add.at(out, hit[0], 1)
        return out

    census_only = counts(TREES["dataset_id"] == CENSUS)
    with_osm = census_only + counts(TREES["dataset_id"] == OSM_DATASET)
    gain = with_osm - census_only
    assert gain.min() >= 0
    assert gain.sum() > 0, "no park gained a tree"
    assert gain.max() >= 100, "the parks that gained did so by real numbers of trees"
    empty_before, empty_after = int((census_only == 0).sum()), int((with_osm == 0).sum())
    assert empty_after <= empty_before
    if len(parks) >= 1900:                      # a whole-city run
        assert empty_before >= D10_EMPTY_PARKS - 5, "the D10 baseline should reproduce"
        assert empty_after <= D10_EMPTY_PARKS - 100, "the empty-park count has to fall, not just move"
    named = {str(n): int(c) for n, c in zip(names, with_osm)}
    if "Central Park" in named:
        assert named["Central Park"] > 1000, "Central Park held 70 census trees over 341.6 ha"
