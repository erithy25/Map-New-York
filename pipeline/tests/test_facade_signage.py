"""Tests for illuminated signage: fascia sign bands, bulletin billboards, Times Square LED displays, lit windows.

Two kinds of assertion live here.

**Placement correctness** — a sign that floats off its building, or that names a kit id which resolves to nothing,
is a defect this project has shipped before (32.8 M placements once pointed at assets that did not exist).  Every
sign is checked against its own building's footprint, its own facade run and the exported kit catalog.

**Honesty** — deviation B5 forbids invented advertising copy, and these tests are the gate that keeps it out.  The
only words that may appear on a shipped sign face are the generic New York trade wording the pipeline already
writes into ``awning_text``; every other face must be blank or the LED pixel matrix.  A real business name is never
baked into geometry, and the legend on the placed band must equal the legend in the building's own row.

    PYTHONPATH=pipeline python3 -m pytest pipeline/tests/test_facade_signage.py -q
"""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

import numpy as np
import polars as pl
import pyarrow.parquet as pq
import pytest
import shapely

from nycsim_pipeline.facade import build as B
from nycsim_pipeline.facade import derive as D
from nycsim_pipeline.facade import enums as E
from nycsim_pipeline.facade import kit_ids as K
from nycsim_pipeline.facade import placements as P
from nycsim_pipeline.facade import signage as SG
from nycsim_pipeline.paths import BLENDER_OUT, PROCESSED, REPO_ROOT

TILES = PROCESSED / "tiles"
ATTRS = PROCESSED / "facade" / "facade_attrs.parquet"
CATALOG_DIR = BLENDER_OUT / "kit" / "catalog"

#: Tiles that hold the Times Square bowtie, where the C6-7T lots are.
TIMES_SQUARE_TILES = ("t_-3_6", "t_-4_6", "t_-3_5", "t_-4_5")


def _kit_sign_tables() -> dict:
    """The kit's literal signage tables, read without importing it (the kit module needs ``bpy``)."""
    import ast
    src = (REPO_ROOT / "blender" / "kit" / "facade" / "pieces_signage.py").read_text()
    out: dict = {}
    for node in ast.parse(src).body:
        target = None
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            target, value = node.target.id, node.value
        elif isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            target, value = node.targets[0].id, node.value
        if target and value is not None:
            try:
                out[target] = ast.literal_eval(value)
            except ValueError:
                continue
    return out


@pytest.fixture(scope="module")
def catalog() -> dict:
    if not CATALOG_DIR.is_dir():
        pytest.skip(f"kit catalog not built: {CATALOG_DIR}")
    entries = {}
    for p in sorted(CATALOG_DIR.glob("*.json")):
        d = json.loads(p.read_text())
        entries[d["id"]] = d
    if not entries:
        pytest.skip("kit catalog empty")
    return entries


@pytest.fixture(scope="module")
def tiles_with_placements() -> list[Path]:
    if not TILES.exists():
        pytest.skip("no tiles built")
    out = sorted(p.parent for p in TILES.glob("*/kit_placements.bin"))
    if not out:
        pytest.skip("kit placements not produced yet")
    return out


def _sample(items: list, n: int, seed: int = 99) -> list:
    rng = random.Random(seed)
    return items if len(items) <= n else rng.sample(items, n)


def _sign_kit_ids() -> dict[str, set[int]]:
    """The kit ids of each signage family, from the registry the stage writes."""
    out: dict[str, set[int]] = {"band": set(), "band_blank": set(), "projecting": set(), "led": set(),
                                "bulletin": set(), "window_lit": set(), "window_unlit": set()}
    for p in K.registry()["pieces"]:
        cid = p["catalog_id"]
        kid = int(p["kit_id"])
        if cid == "storefront_sign_band":
            out["band"].add(kid)
            out["band_blank"].add(kid)
        elif cid.startswith("storefront_sign_band_"):
            out["band"].add(kid)
        elif cid == "storefront_sign_projecting":
            out["projecting"].add(kid)
        elif cid.startswith("sign_led_"):
            out["led"].add(kid)
        elif cid.startswith("billboard_"):
            out["bulletin"].add(kid)
        elif cid.startswith("win_"):
            (out["window_lit"] if cid.endswith("_lit") else out["window_unlit"]).add(kid)
    return out


# --------------------------------------------------------------------------- honesty
def test_the_kit_and_the_pipeline_agree_on_the_generic_wording():
    """The legend baked on a sign band and the legend written into ``awning_text`` are the same table.

    They live in two lanes (the pipeline writes the text, the kit paints it), so a divergence would put one word on
    the geometry and another in the data.  The pipeline's table is the authority.
    """
    kit = _kit_sign_tables()["GENERIC_SIGN_TEXT"]
    pipeline = {E.STOREFRONT_KINDS[k]: v for k, v in D.GENERIC_AWNING.items()}
    assert kit == pipeline, "blender/kit/facade/pieces_signage.py has drifted from facade.derive.GENERIC_AWNING"


def test_every_shipped_sign_legend_is_generic_wording_or_blank(catalog):
    """No invented advertising copy anywhere in the kit.

    A sign face may carry the generic trade wording the data already ships, or nothing at all.  A brand, a product
    or a slogan would be fabrication (deviation B5), and this is the gate.
    """
    allowed = set(D.GENERIC_AWNING.values()) | {""}
    seen = []
    for cid, e in catalog.items():
        if "legend" not in e:
            continue
        seen.append(cid)
        assert e["legend"] in allowed, f"{cid}: sign legend {e['legend']!r} is not generic NYC trade wording"
    assert seen, "no kit piece declares a sign legend"


def test_no_kit_sign_face_carries_content_it_cannot_source(catalog):
    """An LED display face declares that it carries no content at all: it models the hardware, not an advertisement."""
    led = [e for cid, e in catalog.items() if cid.startswith("sign_led_")]
    assert led, "the kit exports no LED display piece"
    for e in led:
        assert e.get("content", "").startswith("none"), f"{e['id']}: LED face claims content"
        assert e.get("sign_face_slot", "").startswith("SIGN_FACE"), f"{e['id']}: no SIGN_FACE slot"
        assert e["sign_face_slot"] in e["materials"], f"{e['id']}: the declared sign face slot is not a material"


def test_a_real_business_name_is_never_baked_into_a_kit_piece(catalog):
    """The 30,381 real names stay in the data; the geometry they get is a blank runtime-swappable panel."""
    blank = catalog.get("storefront_sign_band")
    assert blank is not None, "the kit exports no blank sign band"
    assert blank["legend"] == "", "the blank band must carry no legend"
    assert "SIGN_FACE" in blank["materials"]


def test_sign_zone_comes_only_from_the_published_zoning_district():
    """The Times Square sign zone is MapPLUTO's own C6-7T district, not a hand-drawn box."""
    assert SG.TIMES_SQUARE_ZONING == ("C6-7T",)
    bbls = SG.sign_zone_bbls()
    assert 30 <= len(bbls) <= 120, f"{len(bbls)} C6-7T lots is not the Times Square core"


def test_the_sign_zone_lots_are_all_in_times_square():
    """Every lot the sign zone claims must actually be in the bowtie; a leak elsewhere would light the wrong city."""
    if not ATTRS.exists():
        pytest.skip("facade_attrs not built")
    bbls = set(SG.sign_zone_bbls().tolist())
    found = 0
    for tile in TIMES_SQUARE_TILES + ("t_0_0", "t_-5_10", "t_5_-5"):
        p = TILES / tile / "buildings.parquet"
        if not p.exists():
            continue
        tb = pq.read_table(p, columns=["bbl", "centroid_x", "centroid_y"])
        m = np.isin(tb["bbl"].to_numpy(zero_copy_only=False), list(bbls))
        if not m.any():
            continue
        x = tb["centroid_x"].to_numpy(zero_copy_only=False)[m]
        y = tb["centroid_y"].to_numpy(zero_copy_only=False)[m]
        found += int(m.sum())
        # Duffy Square is NYC_TM (-2930, 6575); the whole C6-7T district sits inside 400 m of it
        d = np.hypot(x - (-2930.0), y - 6575.0)
        assert d.max() <= 400.0, f"{tile}: a sign-zone lot is {d.max():.0f} m from Times Square"
    assert found > 0, "no building was found on a C6-7T lot"


# --------------------------------------------------------------------------- placement correctness
def test_every_placed_kit_id_resolves_to_an_exported_asset(tiles_with_placements):
    """The failure this project has shipped before: 32.8 M placements pointing at assets that did not exist."""
    registered = {int(p["kit_id"]): p for p in K.registry()["pieces"]}
    for d in _sample(tiles_with_placements, 40):
        rec = P.read_tile(d)
        if not len(rec):
            continue
        for kid in np.unique(rec["kit_id"]):
            p = registered.get(int(kid))
            assert p is not None, f"{d.name}: kit id {int(kid)} is not in the catalog-derived registry"
            glb = BLENDER_OUT / p["glb"]
            assert glb.is_file(), f"{d.name}: kit id {int(kid)} ({p['catalog_id']}) has no exported {glb}"


def test_signs_sit_inside_their_own_buildings_footprint(tiles_with_placements):
    """A sign is fixed to a building. Its contact point must lie on that building, not in the street or on a
    neighbour: inside the footprint bounding box, within the wall thickness the placer works to."""
    ids = _sign_kit_ids()
    sign_ids = ids["band"] | ids["projecting"] | ids["led"] | ids["bulletin"]
    checked = 0
    for d in _sample(tiles_with_placements, 30):
        rec = P.read_tile(d)
        m = np.isin(rec["kit_id"], list(sign_ids))
        if not m.any():
            continue
        rec = rec[m]
        tb = pq.read_table(d / "buildings.parquet", columns=["bin", "footprint", "ground_z", "roof_z"])
        bins = tb["bin"].to_numpy()
        order = np.argsort(bins, kind="stable")
        sb = bins[order]
        pos = np.searchsorted(sb, rec["bin"])
        ok = (pos < len(sb)) & (sb[np.minimum(pos, len(sb) - 1)] == rec["bin"])
        assert ok.all(), f"{d.name}: a sign references a bin that is not in the tile"
        idx = order[pos]
        g = shapely.from_wkb(np.asarray(tb["footprint"].to_pylist(), dtype=object))
        xmin, ymin, xmax, ymax = shapely.bounds(g).T
        # 2 m covers the wall face offset and the footprint's own quantisation, the same margin the validator uses
        assert (rec["x"] >= xmin[idx] - 2.0).all() and (rec["x"] <= xmax[idx] + 2.0).all(), f"{d.name}: sign off in x"
        assert (rec["y"] >= ymin[idx] - 2.0).all() and (rec["y"] <= ymax[idx] + 2.0).all(), f"{d.name}: sign off in y"
        checked += len(rec)
    assert checked > 0, "no signs were placed anywhere"


def test_signs_are_attached_to_a_facade_and_not_floating(tiles_with_placements):
    """Every wall-mounted sign sits between the pavement and the roof of the building it is fixed to, and every
    rooftop bulletin sits on the roof deck."""
    ids = _sign_kit_ids()
    wall = ids["band"] | ids["projecting"] | ids["led"] | {K.kit_id("billboard", "billboard_wall")}
    roof = {K.kit_id("billboard", "billboard_roof")}
    checked = 0
    for d in _sample(tiles_with_placements, 30):
        rec = P.read_tile(d)
        if not len(rec):
            continue
        tb = pq.read_table(d / "buildings.parquet", columns=["bin", "ground_z", "roof_z"])
        bins = tb["bin"].to_numpy()
        order = np.argsort(bins, kind="stable")
        sb = bins[order]
        gz = tb["ground_z"].to_numpy(zero_copy_only=False)
        rz = tb["roof_z"].to_numpy(zero_copy_only=False)
        for kind, kids, lo_off, hi_off in (("wall", wall, -0.5, 0.5), ("roof", roof, -0.5, 0.5)):
            m = np.isin(rec["kit_id"], list(kids))
            if not m.any():
                continue
            r = rec[m]
            idx = order[np.clip(np.searchsorted(sb, r["bin"]), 0, len(sb) - 1)]
            if kind == "wall":
                assert (r["z"] >= gz[idx] + lo_off - 1.0).all(), f"{d.name}: a wall sign is below the pavement"
                assert (r["z"] <= rz[idx] + hi_off).all(), f"{d.name}: a wall sign is above the roof"
            else:
                assert np.abs(r["z"] - rz[idx]).max() <= 0.5, f"{d.name}: a rooftop bulletin is not on the roof deck"
            checked += len(r)
    assert checked > 0, "no wall or roof signs were placed"


def test_sign_bands_only_where_the_data_says_there_is_a_storefront(tiles_with_placements):
    """Row for row: a fascia band, a blade sign and a shopfront interior only ever appear on a building whose
    ``has_storefront`` is set."""
    ids = _sign_kit_ids()
    kids = list(ids["band"] | ids["projecting"])
    for d in _sample(tiles_with_placements, 30):
        rec = P.read_tile(d)
        m = np.isin(rec["kit_id"], kids)
        if not m.any():
            continue
        tb = pq.read_table(d / "buildings.parquet", columns=["bin", "has_storefront"])
        bins = tb["bin"].to_numpy()
        order = np.argsort(bins, kind="stable")
        sb = bins[order]
        idx = order[np.clip(np.searchsorted(sb, rec["bin"][m]), 0, len(sb) - 1)]
        has_sf = tb["has_storefront"].to_numpy(zero_copy_only=False)[idx]
        assert has_sf.all(), f"{d.name}: {int((~has_sf).sum())} sign bands on buildings with no storefront"


def test_bulletins_only_where_the_facade_class_carries_the_billboard_feature(tiles_with_placements):
    """Row for row: a bulletin billboard only on a building whose class declares the ``billboard`` typology."""
    bulletin = [K.kit_id("billboard", "billboard_wall"), K.kit_id("billboard", "billboard_roof")]
    total = 0
    for d in _sample(tiles_with_placements, 40):
        rec = P.read_tile(d)
        m = np.isin(rec["kit_id"], bulletin)
        if not m.any():
            continue
        tb = pq.read_table(d / "buildings.parquet", columns=["bin", "facade_class"])
        bins = tb["bin"].to_numpy()
        order = np.argsort(bins, kind="stable")
        sb = bins[order]
        idx = order[np.clip(np.searchsorted(sb, rec["bin"][m]), 0, len(sb) - 1)]
        flag = SG.has_billboard(tb["facade_class"].to_numpy(zero_copy_only=False)[idx])
        assert flag.all(), f"{d.name}: {int((~flag).sum())} bulletins on a class with no billboard feature"
        # at most one bulletin per building: a lot carries a bulletin, not a wall of them
        b, c = np.unique(rec["bin"][m], return_counts=True)
        assert c.max() <= 1, f"{d.name}: bin {int(b[c.argmax()])} carries {int(c.max())} bulletins"
        total += int(m.sum())
    assert total > 0, "no bulletin billboards were placed anywhere"


def test_led_displays_only_on_the_times_square_sign_zone(tiles_with_placements):
    """An LED display appears only where MapPLUTO's C6-7T district says illuminated signage is mandatory."""
    led = [K.kit_id("billboard", r) for r in ("led_panel", "led_blade", "led_ribbon")]
    zone_bbls = set(SG.sign_zone_bbls().tolist())
    total = 0
    # the sign zone is 56 lots in one square, so a random sample of 920 tiles would usually miss it entirely
    must = [TILES / t for t in TIMES_SQUARE_TILES if (TILES / t / "kit_placements.bin").exists()]
    for d in must + _sample(tiles_with_placements, 60):
        rec = P.read_tile(d)
        m = np.isin(rec["kit_id"], led)
        if not m.any():
            continue
        tb = pq.read_table(d / "buildings.parquet", columns=["bin", "bbl"])
        bins = tb["bin"].to_numpy()
        order = np.argsort(bins, kind="stable")
        sb = bins[order]
        idx = order[np.clip(np.searchsorted(sb, rec["bin"][m]), 0, len(sb) - 1)]
        bbl = tb["bbl"].to_numpy(zero_copy_only=False)[idx]
        bad = [int(v) for v in np.unique(bbl) if int(v) not in zone_bbls]
        assert not bad, f"{d.name}: LED displays on lots outside the sign zone: {bad[:5]}"
        total += int(m.sum())
    assert total > 0, "no LED displays were placed: the Times Square frontages carry no screens"


def test_every_sign_is_flagged_lit_at_night(tiles_with_placements):
    """A sign the model places is a light source; the contract's flags bit 0 has to say so or the runtime will
    leave the city dark."""
    ids = _sign_kit_ids()
    kids = list(ids["band"] | ids["projecting"] | ids["led"] | ids["bulletin"])
    checked = 0
    for d in _sample(tiles_with_placements, 20):
        rec = P.read_tile(d)
        m = np.isin(rec["kit_id"], kids)
        if not m.any():
            continue
        assert (rec["flags"][m] & P.FLAG_LIT).all(), f"{d.name}: a sign is not flagged lit"
        checked += int(m.sum())
    assert checked > 0


def test_a_lit_window_piece_is_placed_exactly_where_the_lit_flag_is_set(tiles_with_placements):
    """The night city is lit windows. ``flags`` bit 0 and the ``_lit`` kit piece must agree on every record, or the
    render and the contract disagree about which units have their lights on."""
    ids = _sign_kit_ids()
    lit_ids, unlit_ids = list(ids["window_lit"]), list(ids["window_unlit"])
    # the two window families with no interior card have no lit twin, so they keep the plain id when flagged lit
    no_twin = {K.kit_id("window", n) for n in ("gothic_arched", "through_wall_ac_sleeve")}
    n_lit = 0
    for d in _sample(tiles_with_placements, 20):
        rec = P.read_tile(d)
        if not len(rec):
            continue
        is_lit_piece = np.isin(rec["kit_id"], lit_ids)
        flagged = (rec["flags"] & P.FLAG_LIT) != 0
        assert (is_lit_piece <= flagged).all(), f"{d.name}: a lit window piece is not flagged lit"
        unlit_but_flagged = np.isin(rec["kit_id"], unlit_ids) & flagged & ~np.isin(rec["kit_id"], list(no_twin))
        assert not unlit_but_flagged.any(), (
            f"{d.name}: {int(unlit_but_flagged.sum())} windows are flagged lit but carry the unlit piece")
        n_lit += int(is_lit_piece.sum())
    assert n_lit > 0, "no window anywhere in the city has its lights on"


def test_the_lit_window_share_is_the_share_the_policy_states(tiles_with_placements):
    """The lit share is a stated policy constant, not an accident: residential 32 %, office 18 %."""
    ids = _sign_kit_ids()
    lit_ids, unlit_ids = list(ids["window_lit"]), list(ids["window_unlit"])
    lit = unlit = 0
    for d in _sample(tiles_with_placements, 25):
        rec = P.read_tile(d)
        if not len(rec):
            continue
        lit += int(np.isin(rec["kit_id"], lit_ids).sum())
        unlit += int(np.isin(rec["kit_id"], unlit_ids).sum())
    assert lit + unlit > 0
    share = lit / (lit + unlit)
    assert P.LIT_SHARE_OFFICE * 0.5 <= share <= P.LIT_SHARE_RESIDENTIAL * 1.25, f"lit window share {share:.3f}"


# --------------------------------------------------------------------------- the legend follows the data
def test_the_band_a_building_gets_carries_that_buildings_own_awning_text():
    """The strongest honesty check available: for every storefront on a sampled tile, the legend baked on the sign
    band the placer chose is exactly the ``awning_text`` the building's own row carries - or a blank panel where
    that text is a real business name the kit cannot bake."""
    if not ATTRS.exists():
        pytest.skip("facade_attrs not built")
    cat = {}
    if not CATALOG_DIR.is_dir():
        pytest.skip("kit catalog not built")
    for p in CATALOG_DIR.glob("storefront_sign_band*.json"):
        d = json.loads(p.read_text())
        cat[int(K.kit_id_of_catalog(d["id"]))] = d.get("legend", "")
    assert cat, "no sign band pieces in the catalog"
    tile = next((t for t in TIMES_SQUARE_TILES if (TILES / t / "kit_placements.bin").exists()), None)
    if tile is None:
        pytest.skip("no Times Square tile built")
    rec = P.read_tile(TILES / tile)
    m = np.isin(rec["kit_id"], list(cat))
    if not m.any():
        pytest.skip("no sign bands on this tile yet")
    rec = rec[m]
    tb = pq.read_table(TILES / tile / "buildings.parquet", columns=["bin", "awning_text", "awning_real"])
    text = dict(zip(tb["bin"].to_pylist(), tb["awning_text"].to_pylist()))
    real = dict(zip(tb["bin"].to_pylist(), tb["awning_real"].to_pylist()))
    for kid, b in zip(rec["kit_id"].tolist(), rec["bin"].tolist()):
        legend = cat[int(kid)]
        if real.get(b):
            assert legend == "", f"bin {b} has the real name {text.get(b)!r} but got a band reading {legend!r}"
        else:
            assert legend == (text.get(b) or ""), f"bin {b}: band reads {legend!r}, awning_text is {text.get(b)!r}"


def test_a_storefront_with_no_wording_gets_no_sign_band():
    """A lobby, a garage door and a vacant unit carry an empty ``awning_text``; none of them gets a lit fascia."""
    for kind in ("office_lobby", "residential_lobby", "garage_door", "vacant"):
        idx = E.STOREFRONT_KIND_INDEX[kind]
        assert D.GENERIC_AWNING[idx] == ""
        assert SG.band_kind_for_text(D.GENERIC_AWNING[idx], False) == SG.BAND_NONE


def test_band_kind_for_text_maps_every_generic_wording_back_to_its_kind():
    for idx, wording in D.GENERIC_AWNING.items():
        if not wording:
            continue
        assert SG.band_kind_for_text(wording, False) == idx
    assert SG.band_kind_for_text("HURLEY'S SALOON", True) == SG.BAND_BLANK
    # a real name that somehow lost its flag is not silently turned into a generic trade
    assert SG.band_kind_for_text("HURLEY'S SALOON", False) == SG.BAND_NONE


# --------------------------------------------------------------------------- determinism
def test_signage_placements_are_reproducible():
    """The whole placement stream is a deterministic function of the inputs, signage included."""
    tile = next((t for t in TIMES_SQUARE_TILES if (TILES / t / "buildings.parquet").exists()), None)
    if tile is None or not ATTRS.exists():
        pytest.skip("Times Square tiles not built")
    a = B.regenerate_tile_placements(tile)
    b = B.regenerate_tile_placements(tile)
    assert a.tobytes() == b.tobytes()
    ids = _sign_kit_ids()
    kids = list(ids["band"] | ids["led"] | ids["bulletin"])
    assert int(np.isin(a["kit_id"], kids).sum()) > 0, f"{tile} regenerates with no signage at all"
