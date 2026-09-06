"""Tests for the facade classification and kit placement stage (ADR-004, DATA_CONTRACTS §5 / §5.4 / §6).

Pure-logic tests always run.  Data-dependent tests skip when the stage's outputs are not on disk yet.

    PYTHONPATH=pipeline python3 -m pytest pipeline/tests/test_facade.py -q
"""
from __future__ import annotations

import json
import random
from pathlib import Path

import numpy as np
import polars as pl
import pyarrow as pa
import pyarrow.parquet as pq
import pytest
import shapely

from nycsim_pipeline.contracts import CONTRACTS, validate_parquet
from nycsim_pipeline.facade import derive as D
from nycsim_pipeline.facade import enums as E
from nycsim_pipeline.facade import kit_ids as K
from nycsim_pipeline.facade import roofs as RF
from nycsim_pipeline.facade import rules as R
from nycsim_pipeline.facade import schema as FS
from nycsim_pipeline.facade.placements import PLACEMENT_DTYPE, RECORD_BYTES, read_tile
from nycsim_pipeline.paths import PROCESSED

FACADE_DIR = PROCESSED / "facade"
ATTRS = FACADE_DIR / "facade_attrs.parquet"
GEOM = FACADE_DIR / "geom_attrs.parquet"
SUMMARY = FACADE_DIR / "rules_summary.json"
EMIT_SUMMARY = FACADE_DIR / "emit_summary.json"
TILES = PROCESSED / "tiles"
BASE = PROCESSED / "buildings" / "buildings_base.parquet"

FIDELITY_ROOF_REAL = 1 << 2
FIDELITY_MATERIAL_REAL = 1 << 5
FIDELITY_FACADE_INFERRED = 1 << 10

#: The published range for the number of wooden rooftop water tanks in New York City.
WATER_TANK_LOW, WATER_TANK_HIGH = 10_000, 17_000


# --------------------------------------------------------------------------- fixtures
@pytest.fixture(scope="module")
def attrs() -> pl.DataFrame:
    if not ATTRS.exists():
        pytest.skip(f"{ATTRS} not built")
    return pl.read_parquet(ATTRS)


@pytest.fixture(scope="module")
def base_attrs() -> pl.DataFrame:
    if not BASE.exists():
        pytest.skip(f"{BASE} not built")
    return pl.read_parquet(BASE, columns=["bin", "address", "name", "bldg_class", "year_built", "floors", "borough",
                                          "nta", "hist_district", "footprint_area", "feature_code", "has_storefront"])


@pytest.fixture(scope="module")
def tiles_with_placements() -> list[Path]:
    if not TILES.exists():
        pytest.skip("no tiles built")
    out = sorted(p.parent for p in TILES.glob("*/kit_placements.bin"))
    if not out:
        pytest.skip("kit placements not produced yet")
    return out


def _sample(items: list, n: int, seed: int = 1234) -> list:
    rng = random.Random(seed)
    return items if len(items) <= n else rng.sample(items, n)


# --------------------------------------------------------------------------- enums and the kit registry
def test_material_enum_matches_the_contract():
    """The §5 material enum is duplicated in the contract text, in facade_params and here; all three must agree."""
    assert tuple(E.MATERIALS[: E.N_CONTRACT_MATERIALS]) == E.CONTRACT_MATERIALS
    assert E.RED_BRICK == 0 and E.GLASS_CURTAIN == 8 and E.PRECAST == 16
    assert tuple(E.STOREFRONT_KINDS) == E.CONTRACT_STOREFRONT_KINDS


def test_every_facade_class_has_a_bay_width_and_a_roof():
    classes = E.load_classes()
    assert len(classes) >= 40, "the typology table must cover at least 40 NYC classes"
    for c in classes:
        assert c["window_type"] in E.BAY_WIDTH_M, f"{c['id']}: no bay spacing for {c['window_type']}"
        assert c.get("roof", "flat_parapet") in E.CLASS_ROOF_SHAPE, f"{c['id']}: unknown roof {c.get('roof')}"
        assert 1.5 <= float(c["floor_height_m"]) <= 13.0
        assert 2.0 <= float(c["ground_floor_height_m"]) <= 13.0


def test_kit_ids_come_from_the_exported_catalog():
    """DATA_CONTRACTS §6 ids must name assets that exist: the numbering is derived from the Blender kit catalog."""
    try:
        reg = K.registry()
    except K.KitCatalogMissing:
        pytest.skip("blender_out/kit/catalog not exported yet")
    pieces = reg["pieces"]
    assert pieces, "the registry is empty"
    ids = [p["kit_id"] for p in pieces]
    assert len(set(ids)) == len(ids), "duplicate kit ids"
    assert min(ids) >= K.KIT_ID_STRIDE and max(ids) < K.KIT_ID_MAX
    for p in pieces:
        assert p["catalog_id"], f"kit id {p['kit_id']} has no catalog id"
        assert p["category"] in E.KIT_CATEGORIES
        base = (E.KIT_CATEGORIES.index(p["category"]) + 1) * K.KIT_ID_STRIDE
        assert base <= p["kit_id"] < base + K.KIT_ID_STRIDE, f"{p['catalog_id']} outside its category block"
    # every role the placer can ask for resolves to a piece the kit exports
    assert reg["roles_without_a_kit_piece"] == [], reg["roles_without_a_kit_piece"]


def test_deterministic_hash_is_stable_and_uniform():
    seed = np.arange(100_000, dtype=np.uint32)
    a = E.rand_unit(seed, 7)
    b = E.rand_unit(seed, 7)
    assert np.array_equal(a, b), "the hash is not deterministic"
    assert not np.array_equal(a, E.rand_unit(seed, 8)), "two salts produced the same stream"
    assert 0.0 <= a.min() and a.max() < 1.0
    assert abs(a.mean() - 0.5) < 0.01, f"mean {a.mean()} is not uniform"


# --------------------------------------------------------------------------- the rule table
def test_rule_table_is_well_formed():
    names = [r.name for r in R.RULES]
    assert len(set(names)) == len(names), "duplicate rule names"
    valid = {c["facade_class"] for c in E.load_classes()}
    for r in R.RULES:
        assert r.facade_class in valid, f"{r.name} -> unknown facade_class {r.facade_class}"
        assert r.predicate and r.rationale, f"{r.name} has no predicate or rationale"
        assert len(r.rationale) > 40, f"{r.name}: the rationale must state the typology fact it encodes"
    assert R.RULES[-1].predicate == "always true", "the last rule must be an unconditional fallback"


def _synthetic(n: int = 400) -> pl.DataFrame:
    """A synthetic cross-product of the attributes the rules read, for the exhaustiveness test."""
    rng = np.random.default_rng(7)
    classes = ["A1", "A5", "B1", "B2", "C0", "C1", "C4", "D1", "D4", "O4", "K1", "L1", "F1", "E1", "M1", "W1",
               "I1", "H1", "G1", "Y1", "RM", "R4", "S2", "", "ZZ"]
    return pl.DataFrame({
        "bldg_class": rng.choice(classes, n),
        "year_built": rng.choice([0, 1830, 1880, 1905, 1925, 1935, 1955, 1970, 1985, 2005, 2020], n).astype(np.int16),
        "floors": rng.integers(1, 90, n).astype(np.int16),
        "footprint_area": rng.uniform(20, 5000, n).astype(np.float32),
        "borough": rng.integers(1, 6, n).astype(np.int8),
        "feature_code": rng.choice([2100, 5100, 5110, 1001], n).astype(np.int16),
        "n_bldgs_on_lot": rng.integers(1, 8, n).astype(np.int16),
        "nta": rng.choice(["BK0401", "QN0602", "MN0501", "SI0302", ""], n),
        "hist_district": rng.choice(["", "Park Slope Historic District", "SoHo-Cast Iron Historic District"], n),
        "lpc_style": rng.choice(["", "Italianate", "Art Deco", "Tudor Revival", "Greek Revival"], n),
        "lpc_material": rng.choice(["", "Brick", "Brownstone", "Cast Iron", "Wood Frame"], n),
        "attached": rng.integers(0, 3, n).astype(np.int16),
        "osm_material": np.full(n, -1, dtype=np.int8),
    })


def test_rule_table_is_exhaustive_on_synthetic_input():
    df = _synthetic()
    fc, rid, hits = R.classify(df)
    assert (fc.to_numpy() > 0).all(), "a synthetic building was left unclassified"
    assert sum(hits.values()) == df.height
    assert (rid.to_numpy() >= 0).all()


def test_rules_table_markdown_dumps_every_rule():
    md = R.rules_table_markdown({r.name: 1 for r in R.RULES}, len(R.RULES))
    for r in R.RULES:
        assert f"`{r.name}`" in md
    assert md.count("\n|") >= len(R.RULES)


# --------------------------------------------------------------------------- derived attributes
def test_window_grid_follows_real_geometry():
    fc = np.array([1, 3, 8, 17], dtype=np.int64)          # tenement, brownstone, prewar apartment, curtain wall
    frontage = np.array([7.62, 6.10, 30.0, 70.0])          # 25 ft lot, 20 ft lot, 100 ft, 230 ft
    floors = np.array([5, 4, 12, 40], dtype=np.int32)
    cols, rows, bay = D.window_grid(fc, frontage, floors)
    assert list(cols) == [4, 3, 12, 46], f"bay counts {list(cols)} do not match the real NYC lot modules"
    assert list(rows) == [4, 3, 11, 39], "window rows must be floors - 1"
    assert bay[0] == pytest.approx(1.90) and bay[3] == pytest.approx(1.52)


def test_water_tower_rule_is_physical():
    fc = np.array([2, 2, 2, 2], dtype=np.int64)
    floors = np.array([5, 6, 6, 6], dtype=np.int32)
    year = np.array([1920, 1920, 1965, 2010], dtype=np.int32)
    area = np.array([400.0, 400.0, 400.0, 400.0])
    fcode = np.array([2100, 2100, 2100, 2100], dtype=np.int32)
    has, kind = D.water_towers(fc, floors, year, area, fcode)
    assert list(has) == [False, True, True, False], "the tank rule must key on six floors and the pre-1990 era"
    assert kind[1] == D.TANK_WOOD_10K and kind[2] == D.TANK_STEEL


def test_fire_escape_never_lands_on_a_one_or_two_family_house():
    fc = np.array([1, 1, 1, 27], dtype=np.int64)
    floors = np.array([5, 5, 2, 2], dtype=np.int32)
    year = np.array([1890, 1990, 1890, 1950], dtype=np.int32)
    boro = np.array([1, 1, 1, 4], dtype=np.int8)
    cls1 = np.array([b"C", b"C", b"C", b"B"], dtype="S1")
    free = np.array([2, 2, 2, 4], dtype=np.int32)
    out = D.fire_escapes(fc, floors, year, boro, cls1, free)
    assert list(out) == [True, False, False, False]


def test_material_precedence_follows_adr_004():
    fc = np.array([3, 3, 3, 3], dtype=np.int64)                # brownstone rowhouse: class default is brownstone
    osm_mat = np.array([-1, -1, -1, E.CAST_IRON], dtype=np.int8)
    osm_col = np.array([-1, -1, E.TAN_BRICK, -1], dtype=np.int8)
    lpc = np.array([-1, E.RED_BRICK, E.RED_BRICK, -1], dtype=np.int8)
    prim, sec, src, real = D.resolve_material(fc, osm_mat, osm_col, lpc)
    assert prim[0] == E.BROWNSTONE and src[0] == D.MAT_SRC_RULE and not real[0]
    assert prim[1] == E.RED_BRICK and src[1] == D.MAT_SRC_LPC and real[1]
    assert prim[2] == E.TAN_BRICK and src[2] == D.MAT_SRC_OSM_COLOUR, "a colour refines a masonry shade"
    assert prim[3] == E.CAST_IRON and src[3] == D.MAT_SRC_OSM_MATERIAL
    assert (sec != prim).all(), "the trim material must differ from the wall material"


def test_roof_rule_only_pitches_the_house_stock():
    cls = np.array(["A1", "C1", "A1", "A1"], dtype=object)
    fcode = np.array([2100, 2100, 5110, 2100], dtype=np.int32)
    year = np.array([1950, 1950, 1950, 1875], dtype=np.int32)
    floors = np.array([2, 6, 1, 3], dtype=np.int32)
    area = np.array([120.0, 900.0, 40.0, 120.0])
    attached = np.array([0, 2, 0, 2], dtype=np.int32)
    short = np.array([9.0, 20.0, 6.0, 6.0])
    long = np.array([11.0, 45.0, 6.5, 16.0])
    ridge = np.array([30.0, 0.0, 0.0, 90.0])
    style = ["", "", "", "French Second Empire"]
    gz = np.zeros(4)
    rz = np.array([8.0, 20.0, 3.2, 12.0])
    class_roof = np.array([RF.E.ROOF_GABLE, RF.E.ROOF_FLAT, RF.E.ROOF_FLAT, RF.E.ROOF_FLAT], dtype=np.int8)
    is_tile = np.zeros(4, dtype=bool)
    roof, pitch, rh, eave, ok = RF.infer(cls, fcode, year, floors, area, attached, short, long, ridge, style,
                                         gz, rz, class_roof, is_tile)
    assert ok[0] and roof[0] == RF.E.ROOF_HIP, "a squarish detached house gets a hip roof"
    assert not ok[1], "a six-storey walk-up is not house stock"
    assert ok[2] and roof[2] == RF.E.ROOF_SHED, "an accessory garage gets a shed roof"
    assert ok[3] and roof[3] == RF.E.ROOF_MANSARD, "a Second Empire designation gets a mansard"
    assert (eave[ok] <= rz[ok]).all(), "the eave must sit at or below the measured roof height"
    assert (eave[ok] >= gz[ok]).all()


# --------------------------------------------------------------------------- stage outputs
def test_every_building_has_a_facade_class(attrs: pl.DataFrame):
    assert attrs.height > 0
    valid = {c["facade_class"] for c in E.load_classes()}
    fc = attrs["facade_class"].to_numpy()
    assert (fc > 0).all(), f"{int((fc <= 0).sum())} buildings without a facade class"
    assert set(np.unique(fc)).issubset(valid)
    rid = attrs["facade_rule"].to_numpy()
    assert rid.min() >= 0 and rid.max() < len(R.RULES)
    # the rule that claimed a building must be the rule that names its class
    by_rule = {i: r.facade_class for i, r in enumerate(R.RULES)}
    expect = np.asarray([by_rule[int(i)] for i in rid], dtype=np.int16)
    assert np.array_equal(expect, fc), "facade_rule and facade_class disagree"


def test_facade_attrs_rows_match_buildings_base(attrs: pl.DataFrame):
    n = pq.ParquetFile(BASE).metadata.num_rows if BASE.exists() else None
    if n is None:
        pytest.skip("buildings_base missing")
    assert attrs.height == n, f"facade_attrs has {attrs.height} rows, buildings_base has {n}"


def test_fidelity_bits_follow_the_contract(attrs: pl.DataFrame):
    fid = attrs["fidelity"].to_numpy().astype(np.uint32)
    mat_real = (fid & FIDELITY_MATERIAL_REAL) != 0
    inferred = (fid & FIDELITY_FACADE_INFERRED) != 0
    # DATA_CONTRACTS §5.1: bit 10 is set whenever bit 5 is clear
    assert np.array_equal(inferred, ~mat_real)
    src = attrs["material_source"].to_numpy()
    assert np.array_equal(mat_real, src != D.MAT_SRC_RULE), "MATERIAL_REAL must mean a real material source"
    roof_inferred = (fid & RF.FIDELITY_ROOF_INFERRED) != 0
    assert np.array_equal(roof_inferred, attrs["roof_source"].to_numpy() == RF.ROOF_SRC_FACADE_RULE)
    assert not (roof_inferred & (attrs["roof_type"].to_numpy() == 0)).any(), \
        "ROOF_INFERRED must only mark a building whose shape this stage actually pitched"


def test_material_real_share_is_reported_and_small(attrs: pl.DataFrame):
    """ADR-004's central admission: the overwhelming majority of facades are inferred. The number must be real."""
    fid = attrs["fidelity"].to_numpy().astype(np.uint32)
    share = float(((fid & FIDELITY_MATERIAL_REAL) != 0).mean())
    assert 0.0 < share < 0.25, f"MATERIAL_REAL share {share:.4f} is not plausible for the available evidence"


def test_water_tower_count_is_inside_the_published_range(attrs: pl.DataFrame):
    kinds = attrs["water_tower_kind"].to_numpy()
    wooden = int(((kinds == D.TANK_WOOD_10K) | (kinds == D.TANK_WOOD_20K)).sum())
    assert WATER_TANK_LOW <= wooden <= WATER_TANK_HIGH, (
        f"{wooden:,} wooden rooftop tanks is outside the published 10,000-17,000 range for New York City")
    assert int(attrs["has_water_tower"].sum()) >= wooden


def test_window_counts_are_bounded_by_the_building(tiles_with_placements: list[Path]):
    """``window_rows`` is floors - 1, so it can never exceed the building's own storey count."""
    for d in _sample(tiles_with_placements, 30, seed=17):
        t = pq.read_table(d / "buildings.parquet", columns=["window_cols", "window_rows", "floors", "bay_width_m"])
        rows = t["window_rows"].to_numpy()
        floors = t["floors"].to_numpy()
        cols = t["window_cols"].to_numpy()
        bay = t["bay_width_m"].to_numpy(zero_copy_only=False)
        assert (rows <= floors).all(), f"{d.name}: window_rows exceeds floors"
        assert (rows >= 0).all() and (cols >= 1).all() and (cols <= 200).all()
        assert (bay >= 1.0).all() and (bay <= 4.0).all()


# --------------------------------------------------------------------------- per-tile schema
def test_every_tile_carries_the_complete_contract_schema(tiles_with_placements: list[Path]):
    problems = {}
    for d in _sample(tiles_with_placements, 40):
        p = d / "buildings.parquet"
        probs = validate_parquet("buildings", p, check_nulls=False)
        if probs:
            problems[d.name] = probs
    assert not problems, f"tiles missing DATA_CONTRACTS §5 columns: {list(problems.items())[:3]}"


def test_tile_files_keep_the_buildings_stage_columns_and_metadata(tiles_with_placements: list[Path]):
    from nycsim_pipeline.buildings import schema as BS
    for d in _sample(tiles_with_placements, 10):
        f = pq.ParquetFile(d / "buildings.parquet")
        names = set(f.schema_arrow.names)
        missing = [c for c, _, _ in BS.COLUMNS if c not in names]
        assert not missing, f"{d.name} lost buildings-stage columns {missing}"
        assert set(FS.ADDED_NAMES).issubset(names), f"{d.name} is missing facade columns"
        meta = f.schema_arrow.metadata or {}
        assert meta.get(b"nycsim.schema") == b"buildings/1"
        assert meta.get(b"nycsim.tile", b"").decode() == d.name
        assert meta.get(b"nycsim.facade.schema") == FS.FACADE_SCHEMA_ID.encode()
        assert b"geo" in meta, "the GeoParquet metadata must survive the facade rewrite"


def test_added_columns_have_the_declared_types(tiles_with_placements: list[Path]):
    d = tiles_with_placements[0]
    sch = pq.ParquetFile(d / "buildings.parquet").schema_arrow
    for name, typ in FS.ADDED_COLUMNS:
        assert sch.field(name).type == typ, f"{name}: {sch.field(name).type} != {typ}"
    # and the contract's own type families still hold
    spec = CONTRACTS["buildings"]
    assert set(spec).issubset(set(sch.names))


# --------------------------------------------------------------------------- placements
def test_placement_record_is_forty_bytes():
    assert PLACEMENT_DTYPE.itemsize == RECORD_BYTES == 40
    assert [f for f in PLACEMENT_DTYPE.names] == ["kit_id", "bin", "x", "y", "z", "yaw_deg", "scale",
                                                  "variant_seed", "flags"]
    assert PLACEMENT_DTYPE["kit_id"].str == "<u4" and PLACEMENT_DTYPE["bin"].str == "<i8"


def test_placement_headers_agree_with_their_files(tiles_with_placements: list[Path]):
    import hashlib
    for d in _sample(tiles_with_placements, 30):
        raw = (d / "kit_placements.bin").read_bytes()
        hdr = json.load(open(d / "kit_placements.json"))
        assert hdr["record_bytes"] == RECORD_BYTES
        assert hdr["bytes"] == len(raw)
        assert hdr["count"] * RECORD_BYTES == len(raw)
        assert hdr["sha256"] == hashlib.sha256(raw).hexdigest()
        assert hdr["schema"] == "kit_placements/1"
        assert all(isinstance(k, int) for k in hdr["kit_ids"]), "kit_ids must be a plain list of ids"


def test_placements_sit_on_their_own_building(tiles_with_placements: list[Path]):
    margin = 2.0
    for d in _sample(tiles_with_placements, 12, seed=99):
        rec = read_tile(d)
        if len(rec) == 0:
            continue
        tb = pq.read_table(d / "buildings.parquet",
                           columns=["bin", "footprint", "ground_z", "roof_z", "has_storefront", "n_placements"])
        bins = tb["bin"].to_numpy()
        order = np.argsort(bins, kind="stable")
        sb = bins[order]
        pos = np.searchsorted(sb, rec["bin"])
        ok = (pos < len(sb)) & (sb[np.minimum(pos, len(sb) - 1)] == rec["bin"])
        assert ok.all(), f"{d.name}: {int((~ok).sum())} placements name a bin that is not in the tile"
        idx = order[pos]
        g = shapely.from_wkb(np.asarray(tb["footprint"].to_pylist(), dtype=object))
        xmin, ymin, xmax, ymax = shapely.bounds(g).T
        assert (rec["x"] >= xmin[idx] - margin).all() and (rec["x"] <= xmax[idx] + margin).all(), \
            f"{d.name}: a placement is outside its footprint bounding box + {margin} m"
        assert (rec["y"] >= ymin[idx] - margin).all() and (rec["y"] <= ymax[idx] + margin).all()
        gz = tb["ground_z"].to_numpy(zero_copy_only=False)
        rz = tb["roof_z"].to_numpy(zero_copy_only=False)
        assert (rec["z"] >= gz[idx] - 1.5).all(), f"{d.name}: a placement is below its building's ground"
        assert (rec["z"] <= rz[idx] + 16.0).all(), f"{d.name}: a placement floats above its building's roof"
        assert int(tb["n_placements"].to_numpy().sum()) == len(rec)


def test_storefront_pieces_only_where_the_data_says_there_is_a_storefront(tiles_with_placements: list[Path]):
    try:
        reg = K.registry()
    except K.KitCatalogMissing:
        pytest.skip("kit catalog not exported")
    sf_ids = {p["kit_id"] for p in reg["pieces"]
              if p["category"] in ("storefront", "storefront_interior") and not p["catalog_id"].startswith("entry_")}
    for d in _sample(tiles_with_placements, 12, seed=5):
        rec = read_tile(d)
        if len(rec) == 0:
            continue
        tb = pq.read_table(d / "buildings.parquet", columns=["bin", "has_storefront"])
        has = dict(zip(tb["bin"].to_pylist(), tb["has_storefront"].to_pylist()))
        sel = np.isin(rec["kit_id"], list(sf_ids))
        if not sel.any():
            continue
        bad = [int(b) for b in np.unique(rec["bin"][sel]) if not has.get(int(b), False)]
        assert not bad, f"{d.name}: storefront pieces on buildings without a storefront: {bad[:5]}"


def test_no_placement_on_a_party_wall(tiles_with_placements: list[Path]):
    """A party wall is shared masonry: it can carry no window, stoop, storefront or fire escape."""
    from nycsim_pipeline.facade import edges as EG
    d = tiles_with_placements[len(tiles_with_placements) // 2]
    tb = pq.read_table(d / "buildings.parquet", columns=["bin", "footprint", "attached"])
    if int(np.asarray(tb["attached"].to_numpy()).sum()) == 0:
        pytest.skip("no attached buildings in the sampled tile")
    rec = read_tile(d)
    if len(rec) == 0:
        pytest.skip("no placements in the sampled tile")
    # only facade-mounted pieces are constrained: rooftop equipment stands on the deck and may sit anywhere inside
    # the footprint, including directly behind a party wall
    try:
        roof_ids = {p["kit_id"] for p in K.registry()["pieces"]
                    if p["category"] in ("hvac", "water_tower", "antenna", "bulkhead", "billboard", "vegetation")}
    except K.KitCatalogMissing:
        pytest.skip("kit catalog not exported")
    rec = rec[~np.isin(rec["kit_id"], list(roof_ids))]
    if len(rec) == 0:
        pytest.skip("no facade placements in the sampled tile")
    g = shapely.from_wkb(np.asarray(tb["footprint"].to_pylist(), dtype=object))
    tree = shapely.STRtree(g)
    runs = EG.compute_runs(g, np.zeros(len(g)), tree, np.arange(len(g), dtype=np.int64))
    party = runs.is_party & (runs.length >= EG.MIN_RUN_M)
    if not party.any():
        pytest.skip("no party walls detected in the sampled tile")
    bins = tb["bin"].to_numpy()
    mx = 0.5 * (runs.x0 + runs.x1)[party]
    my = 0.5 * (runs.y0 + runs.y1)[party]
    pb = bins[runs.bidx[party]]
    # for each party-wall midpoint, no placement of that same building may sit within 0.6 m of it
    close = 0
    for b in np.unique(pb)[:400]:
        sel = rec["bin"] == b
        if not sel.any():
            continue
        m = pb == b
        dx = rec["x"][sel][:, None] - mx[m][None, :]
        dy = rec["y"][sel][:, None] - my[m][None, :]
        close += int((np.hypot(dx, dy) < 0.6).any(axis=1).sum())
    assert close == 0, f"{close} placements sit on a party wall in {d.name}"


def test_placements_are_reproducible_byte_for_byte(tiles_with_placements: list[Path]):
    """Determinism: the same inputs must regenerate the same file, byte for byte."""
    from nycsim_pipeline.facade.build import regenerate_tile_placements
    if not ATTRS.exists():
        pytest.skip("facade_attrs not built")
    for d in _sample(tiles_with_placements, 2, seed=31):
        on_disk = (d / "kit_placements.bin").read_bytes()
        if not on_disk:
            continue
        again = regenerate_tile_placements(d.name)
        order = np.lexsort((again["kit_id"], again["bin"]))
        assert again[order].tobytes() == on_disk, f"{d.name} is not reproducible from its inputs"
        twice = regenerate_tile_placements(d.name)
        assert twice.tobytes() == again.tobytes(), f"{d.name} differs between two runs of the generator"


def test_city_wide_placement_volume_is_plausible():
    if not EMIT_SUMMARY.exists():
        pytest.skip("emit summary missing")
    d = json.load(open(EMIT_SUMMARY))
    assert d["problems"] == [], d["problems"][:3]
    assert d["placements"] > 1_000_000, "a city of a million buildings cannot have under a million placements"
    assert d["placements_per_building"] >= 4.0, "the placement generator produced almost nothing"
    assert d["bytes"] == d["placements"] * RECORD_BYTES


# --------------------------------------------------------------------------- typology spot checks
def _lookup(attrs: pl.DataFrame, base: pl.DataFrame) -> pl.DataFrame:
    return attrs.join(base, on="bin", how="inner")


def test_a_park_slope_brownstone_is_classified_as_a_brownstone(attrs, base_attrs):
    j = _lookup(attrs, base_attrs).filter(
        (pl.col("hist_district") == "Park Slope Historic District")
        & pl.col("bldg_class").is_in(["A4", "B1", "B3", "C0"]) & (pl.col("floors").is_between(3, 5)))
    assert j.height > 100, "the Park Slope Historic District rowhouses are missing from the data"
    rowhouse_classes = {3, 4, 5, 7, 6}      # brownstone 1860/1880, limestone 1900, Greek Revival, Federal
    share = float(j["facade_class"].is_in(list(rowhouse_classes)).mean())
    assert share > 0.8, f"only {share:.0%} of Park Slope rowhouses got a rowhouse class"
    masonry = {E.BROWNSTONE, E.LIMESTONE, E.RED_BRICK, E.BROWN_BRICK, E.TAN_BRICK, E.STONE_RUBBLE, E.GRANITE}
    assert float(j["material_primary"].is_in(list(masonry)).mean()) > 0.95
    assert float(j["has_stoop"].mean()) > 0.7, "a Park Slope rowhouse has a stoop"


def test_fifteen_central_park_west_is_not_a_frame_house(attrs, base_attrs):
    j = _lookup(attrs, base_attrs).filter(pl.col("address").str.starts_with("15 CENTRAL PARK WEST"))
    if j.height == 0:
        pytest.skip("15 Central Park West is not in this build")
    for r in j.iter_rows(named=True):
        assert r["material_primary"] not in (E.VINYL_SIDING, E.WOOD_CLAPBOARD), \
            f"a 2005 Central Park West tower was given {E.MATERIALS[r['material_primary']]}"
        assert r["facade_class"] in (15, 17, 18, 50), f"unexpected class {r['facade_class']} for a 2005 CPW tower"
        assert r["window_rows"] >= 20 and r["has_fire_escape"] is False


def test_a_bushwick_warehouse_is_industrial(attrs, base_attrs):
    j = _lookup(attrs, base_attrs).filter(
        pl.col("nta").is_in(["BK0401", "BK0402"]) & pl.col("bldg_class").str.slice(0, 1).is_in(["F", "E", "L"]))
    assert j.height > 50, "no Bushwick industrial buildings in the data"
    industrial = {21, 22, 45, 46}
    assert float(j["facade_class"].is_in(list(industrial)).mean()) > 0.85
    masonry_or_concrete = {E.RED_BRICK, E.CONCRETE, E.METAL_PANEL, E.PRECAST, E.BROWN_BRICK, E.TAN_BRICK}
    assert float(j["material_primary"].is_in(list(masonry_or_concrete)).mean()) > 0.9
    prewar = j.filter(pl.col("year_built").is_between(1880, 1940))
    if prewar.height:
        assert float(prewar["material_primary"].is_in([E.RED_BRICK, E.BROWN_BRICK, E.TAN_BRICK]).mean()) > 0.5, \
            "a pre-1940 Bushwick industrial building is brick, not poured concrete"


def test_the_empire_state_building_is_a_setback_tower(attrs, base_attrs):
    j = _lookup(attrs, base_attrs).filter(pl.col("name") == "Empire State Building")
    if j.height == 0:
        pytest.skip("the Empire State Building is not in this build")
    r = j.row(0, named=True)
    assert r["facade_class"] == 25, "the 1931 Empire State Building must be the Art Deco setback office class"
    assert r["has_water_tower"], "a 1931 tower needs a gravity tank"
    assert r["window_rows"] > 90


def test_soho_cast_iron_district_gets_the_cast_iron_class(attrs, base_attrs):
    j = _lookup(attrs, base_attrs).filter(pl.col("hist_district") == "SoHo-Cast Iron Historic District")
    if j.height < 50:
        pytest.skip("SoHo-Cast Iron Historic District not in this build")
    assert float((j["facade_class"] == 20).mean()) > 0.6
    assert float(j["has_fire_escape"].mean()) > 0.5, "SoHo loft buildings carry fire escapes"


def test_a_queens_single_family_house_never_gets_a_fire_escape(attrs, base_attrs):
    j = _lookup(attrs, base_attrs).filter(
        (pl.col("borough") == 4) & pl.col("bldg_class").str.starts_with("A") & (pl.col("floors") <= 3))
    assert j.height > 1000
    assert int(j["has_fire_escape"].sum()) == 0, "a Queens single-family house never has a fire escape"


def test_class_distribution_covers_the_typology(attrs: pl.DataFrame):
    used = set(attrs["facade_class"].unique().to_list())
    all_classes = {c["facade_class"] for c in E.load_classes()}
    assert len(used) >= 40, f"only {len(used)} of {len(all_classes)} facade classes are used"
    # no single class may swallow the city
    top = attrs.group_by("facade_class").len().sort("len", descending=True).row(0)
    assert top[1] / attrs.height < 0.30, f"class {top[0]} holds {top[1] / attrs.height:.0%} of the city"


def test_borough_material_profiles_are_right(attrs, base_attrs):
    j = _lookup(attrs, base_attrs)
    mn = j.filter(pl.col("borough") == 1)
    si = j.filter(pl.col("borough") == 5)
    assert float(mn["material_primary"].is_in([E.VINYL_SIDING, E.WOOD_CLAPBOARD]).mean()) < 0.10, \
        "Manhattan is not a frame-house borough"
    assert float(si["material_primary"].is_in([E.VINYL_SIDING, E.WOOD_CLAPBOARD]).mean()) > 0.35, \
        "Staten Island is mostly sided frame houses"
    assert float(mn.filter(pl.col("facade_class").is_in([16, 17, 18, 19]))["facade_class"].len()) > 100, \
        "Manhattan must hold curtain-wall towers"
