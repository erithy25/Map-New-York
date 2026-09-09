"""Platform decks: streets and plazas that stand on structure over ground the bare-earth DEM still shows.

The 1 m 3DEP product (NY_CMPG_2013) is a *bare-earth* surface: bridge and viaduct decks are classified out
of it, and anything built after the 2013-14 flight is not in it at all.  Where a street or a plaza is carried
on structure, the DEM therefore holds whatever was under the structure when the aircraft flew -- a rail
yard's floor, an open cut, a construction pit -- and every consumer of ``terrain.png`` puts the street down
there.  The road stage cannot catch it either: CSCL codes these streets **at grade** (level 13), so
``roads/apply_terrain_z.py`` drapes their vertices onto the pit (Tenth Avenue across the West Side Yard:
segment 1267 vertices 5.15, 0.60, -0.65, 9.39 m before this stage existed; DEVIATIONS.md J85).

``repair_sub_datum`` (ADR-018) does not reach these: it repairs land below ``LAND_FLOOR_M`` (-2 m), and a
yard floor at +2.8 m or a cut at -0.9 m is above it.  Nor does ``densify``: the real street-level spot
elevations along the avenue are 5-10 m above the DEM and are rejected as outliers by ``IDW_MAX_DZ_M``.

This module is the register of such **platform decks** and the code that puts them into the terrain
through the same deck path the pier and jetty decks already use (``hydro.TileHydro.deck_z`` ->
``tiles.build_tile``), so that other epoch artefacts can join the table later without a new special case.

The rules, each with its reason
-------------------------------
* **Extent comes from real polygons only.** Every register row names the dataset and the source id of each
  polygon it is built from (DoITT planimetric roadbeds, the road network's own intersection nodes).  No
  extent is drawn by hand and none is taken from a landmark model.
* **Elevation comes from the survey, never from a constant.** Inside the extent the deck surface is an
  inverse-distance-squared interpolation of the **eight nearest survey points within 240 m** -- the points,
  the weights and the reach of ``tiles.survey_fill``, which closes the tunnel portals (ADR-018) -- over the
  planimetric spot elevations and footprint grounds *except* the points the register excludes.  A flat deck
  at one number would be a correct measurement of something other than the road: Tenth Avenue's own seven
  spot elevations grade from 5.17 m at W 30th to 9.20 m at W 33rd, so a constant would step it 2.5 m at
  W 31st.  ``survey_fill``'s growing-radius rule (use only the points inside the smallest of 30/60/120/240 m
  that holds any) is **not** used: on a road surveyed at one spot every 25-55 m it degenerates to nearest-
  neighbour plateaus -- measured on the first attempt, Tenth Avenue came out as 5.62 m flat, then 7.22 m
  flat, then 8.82 m flat, with 1.6 m risers at the midpoints between spots.  Eight points without that rule
  give a monotone grade that passes through every spot (measured |dz| <= 0.03 m at the twelve control spots
  and 6.6 m at the pit sample, which is the linear grade between its two neighbours).
* **Points inside a deck's extent are excluded unless they are planimetric spot elevations.** A footprint's
  LiDAR ground inside the extent is of the excavation's epoch or of an unknown one (the Vessel's OTI ground
  is 2.74 m, the yard floor; 15 Hudson Yards' is 9.14 m), so none is used.  Spot elevations inside the
  extent are the survey of the street on the deck and are the control; a row may list individual spots to
  exclude, with the reason.
* **A deck is burned where it stands above the ground beneath it, and nowhere else** (``z = max(z, deck)``
  inside the extent).  A platform spans a hole; where the bare-earth surface already reaches the deck --
  the corner of the block that was never excavated, the end of a viaduct where it meets the street -- the
  DEM is a real measurement and is kept.  ``max`` is continuous, so there is no step at that boundary, and
  every sample that was replaced is counted per deck in ``terrain.json`` (``platform``).
* **Every input is global**, so two tiles sharing a sample burn it to the same value: the polygons are the
  same for every tile and the survey interpolation reads only the global point index (``points.py``), as
  ``verify.check_seams`` requires.

Two ways to apply the same function
-----------------------------------
``tiles.build_tile`` applies it in the tile pass, between the pier/jetty deck burn and the sub-datum
repair.  ``apply_to_published`` applies it to a tile that is already on disk (decode ``terrain.png`` ->
burn -> re-quantise -> write), for when the 2 m source mosaic is not available to rebuild from
(``data/processed/terrain/src2m_removed.json``).  The deck surface is window-independent and the burn is a
``max`` against values that are already on the 2.5 mm grid, so the two agree to one quantum at every
sample inside an extent; outside, a sub-datum sample within ``FILL_RADIUS_M`` of an extent would have been
rim-filled from deck values in a rebuild and was rim-filled from pit values in the published tile -- that
count is measured and reported per tile in ``platform.rebuild_may_differ_px``.

    python -m nycsim_pipeline.terrain.platforms build
    python -m nycsim_pipeline.terrain.platforms apply-to-published --tiles t_-5_5,t_-5_6
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import shapely
import shapely.geometry
from rasterio.features import rasterize
from rasterio.transform import Affine
from shapely.ops import unary_union

from ..paths import PROCESSED, tile_dir
from ..tiling import Tile
from .grid import SAMPLES, SPACING_M, Z_SCALE_M, bounds_of, encode_png_values, quantize, tile_transform
from .points import KIND_BUILDING, KIND_SPOT, PointIndex, load_index

log = logging.getLogger("nycsim.terrain.platforms")

DECKS_PATH = PROCESSED / "terrain" / "platform_decks.parquet"
DECKS_JSON = PROCESSED / "terrain" / "platform_decks.json"
APPLIED_JSON = PROCESSED / "terrain" / "platform_decks_applied.json"
SCHEMA = "terrain.platform_decks/1"
PAVEMENT_DIR = PROCESSED / "roads" / "pavement"
NODES_PATH = PROCESSED / "roads" / "nodes.parquet"
ROADBED_FEAT_CODE = 3500          # DoITT planimetric roadbed (roads/pavement.py)
SURVEY_REACH_M = 240.0                        # = the widest of tiles.survey_fill's radii
SURVEY_K = 8                                  # = tiles.survey_fill's eight nearest points
IDW_MIN_D_M = 0.25                            # = tiles.IDW_MIN_D_M
NO_DECK = -1


class PlatformError(RuntimeError):
    pass


# ----------------------------------------------------------------------------- the register
# One row per structure.  Every number here is a *reference* to a record in a dataset, not a value the
# terrain takes: the elevations are read from the survey points at build time and the polygons from the
# processed tables.  The ``evidence`` blocks are the measurements that put the row here, taken from the
# published tiles before this stage ran (2026-09-09, DEVIATIONS.md J85), and are kept so the row can be
# audited without re-measuring.
REGISTER: list[dict] = [
    {
        "deck_id": "hudson_yards_ery_platform",
        "name": "Hudson Yards platform over the Eastern Rail Yard, with Tenth Avenue's carriageway across the yard",
        "kind": "platform",
        "status": "applied",
        "structure": ("The Eastern Rail Yard platform (built 2014-16 over the LIRR West Side Yard, W 30th-W 33rd, "
                      "Tenth-Eleventh Avenues; the Hudson Yards public square, the Shops podium, 10/15/30/35 Hudson "
                      "Yards, The Shed and the Vessel stand on it) and Tenth Avenue where it crosses the yard's east "
                      "throat on structure between W 30th and W 33rd Streets."),
        "what_the_dem_holds": ("The 2013-14 bare-earth flight: the open yard floor at about 2.2-4.5 m NAVD88 and the "
                               "east throat's cut under Tenth Avenue down to -1.8 m, where the survey puts the "
                               "avenue at 5.17-9.20 m and the square at 10.0-12.3 m."),
        "extent": [
            {"part": "block",
             "what": "the block bounded by the four streets' centrelines, minus the carriageways of the three "
                     "streets that are on the ground (W 30th, Eleventh Avenue, W 33rd) -- every DoITT roadbed "
                     "polygon that crosses the block's boundary except the one named in keep_roadbeds",
             "dataset": "roads/nodes.parquet (road-network intersection nodes) + DoITT planimetric roadbeds "
                        "(feat_code 3500) in roads/pavement/{tile}.parquet",
             "corner_nodes": [21145, 21201, 21146, 21143],
             "corner_names": ["10 AVE & W 30 ST", "10 AVE & W 33 ST", "11 AVE & W 33 ST", "11 AVE & W 30 ST"],
             "corner_note": "nodes.parquet names them 10 AVE & HIGH LINE (21145) and 11 AVE & AMTRAK-NORTHEAST LINE (21146); "
                            "W 30 ST and W 33 ST are in each node's names list",
             "keep_roadbeds": ["12350003663", "12350003662"],
             "keep_note": "12350003662 is the roadbed stub that enters the block from Eleventh Avenue between W 31st and "
                          "W 32nd (heightmap 1.2-3.8 m, the yard floor); no survey point stands on it, so the deck rule "
                          "puts it at the interpolated street level -- if it is a ramp down to the loading dock, that "
                          "is not in any source this pass has",
             "tiles": ["t_-5_5", "t_-5_6"]},
            {"part": "roadbed",
             "what": "Tenth Avenue's carriageway across the yard, W 30th to W 33rd (both parts of the polygon)",
             "dataset": "DoITT planimetric roadbed (feat_code 3500) in roads/pavement/{tile}.parquet",
             "source_id": "12350003663",
             "tiles": ["t_-5_5", "t_-5_6"]},
            {"part": "frontage",
             "what": "Tenth Avenue's east sidewalk, W 30th to W 33rd: the yard's cut continues under it to the building "
                     "line (heightmap -1.99..0.32 m within 12 m of the carriageway).  The DoITT polygon is one piece "
                     "that also rings the block east of the avenue as far as Ninth Avenue, where the ground is real "
                     "(0.8-15 m) and where a first attempt burned 155 samples by up to 11 m and reached the tile's "
                     "east edge; so only the carriageway's own frontage is taken -- the part of the sidewalk polygon "
                     "nearer to this roadbed than to any other DoITT roadbed",
             "dataset": "DoITT planimetric sidewalk (feat_code 3800) in roads/pavement/{tile}.parquet, cut against "
                        "the roadbeds (feat_code 3500) of the same tiles",
             "feat_code": 3800, "source_ids": ["12380000504"], "roadbed": "12350003663",
             "tiles": ["t_-5_5", "t_-5_6"]},
            {"part": "pavement",
             "what": "the curb strips between that carriageway and sidewalk (heightmap -1.5..1.5 m)",
             "dataset": "DoITT planimetric curb (feat_code 2250) in roads/pavement/{tile}.parquet",
             "feat_code": 2250, "source_ids": ["12225000915", "12225003524", "12225008879", "12225003377"],
             "tiles": ["t_-5_5", "t_-5_6"]},
        ],
        "control": {
            "rule": "planimetric spot elevations (feat 3000 / sub 300000) inside the extent are the control; every "
                    "footprint LiDAR ground inside it is excluded; nothing outside the extent is excluded",
            "spot_elevations_inside": [
                # source_id, ft, m, x, y (NYC_TM), status -- plan_elevation_points.geojson; the survey assigns
                # source_id 0 to every point of status "New" (14 of 14 in the Hudson Yards box), so "0" is the
                # record's own id for those, not a placeholder
                {"source_id": "12300022305", "elevation_ft": 16.0, "z_m": 4.877, "x": -4298.13, "y": 5794.33, "status": "Unchanged", "where": "10 AVE 11 m north of W 30 ST"},
                {"source_id": "12300022329", "elevation_ft": 16.9639, "z_m": 5.171, "x": -4294.89, "y": 5799.88, "status": "Unchanged", "where": "10 AVE"},
                {"source_id": "12300022431", "elevation_ft": 17.0, "z_m": 5.182, "x": -4282.92, "y": 5823.48, "status": "Unchanged", "where": "10 AVE"},
                {"source_id": "12300022533", "elevation_ft": 17.43, "z_m": 5.313, "x": -4266.77, "y": 5852.23, "status": "Unchanged", "where": "10 AVE & W 31 ST"},
                {"source_id": "12300022580", "elevation_ft": 18.4305, "z_m": 5.618, "x": -4258.50, "y": 5867.12, "status": "Unchanged", "where": "10 AVE"},
                {"source_id": "12300022773", "elevation_ft": 23.6859, "z_m": 7.219, "x": -4229.03, "y": 5920.47, "status": "Unchanged", "where": "10 AVE (heightmap -0.23 m before)"},
                {"source_id": "12300022985", "elevation_ft": 28.9412, "z_m": 8.821, "x": -4199.57, "y": 5973.81, "status": "Unchanged", "where": "10 AVE"},
                {"source_id": "0", "elevation_ft": 40.1687, "z_m": 12.243, "x": -4399.93, "y": 5937.80, "status": "New", "where": "public square (heightmap 1.57 m before)"},
                {"source_id": "0", "elevation_ft": 32.9684, "z_m": 10.049, "x": -4444.79, "y": 5955.55, "status": "New", "where": "public square (heightmap 0.87 m before)"},
                {"source_id": "0", "elevation_ft": 40.4852, "z_m": 12.340, "x": -4360.13, "y": 5977.35, "status": "New", "where": "public square (heightmap 2.77 m before)"},
                {"source_id": "0", "elevation_ft": 37.5081, "z_m": 11.432, "x": -4338.60, "y": 6012.67, "status": "New", "where": "public square (heightmap 2.78 m before)"},
                {"source_id": "0", "elevation_ft": 40.3775, "z_m": 12.307, "x": -4401.67, "y": 6025.89, "status": "New", "where": "public square (heightmap 2.90 m before)"},
            ],
            "excluded_spot_elevations": [],
            "excluded_footprint_grounds": [
                # OTI Building Footprints, ground_elevation (ft) -> ground_z (m); all inside the extent
                {"bin": 1089323, "name": "10 Hudson Yards", "ground_z_m": 4.877, "note": "agrees with 10 AVE & W 30 ST; excluded by the rule, not for being wrong"},
                {"bin": 1089411, "name": "15 Hudson Yards / The Shed", "ground_z_m": 9.144},
                {"bin": 1091590, "name": "35 Hudson Yards", "ground_z_m": 8.534},
                {"bin": 1090391, "name": "Vessel", "ground_z_m": 2.743, "note": "the yard floor of the 2013 flight"},
                {"bin": 1088961, "name": "the Shops / 30 Hudson Yards podium", "ground_z_m": None, "note": "NaN in the source; never in the point index"},
                {"bin": 1090967, "ground_z_m": 2.743, "note": "at (-4405.0, 5962.4): the yard floor of the 2013 flight"},
                {"bin": 1090871, "ground_z_m": 2.743, "note": "at (-4356.9, 6007.5): the yard floor of the 2013 flight"},
                {"bin": 1090809, "ground_z_m": 16.764, "note": "at (-4459.9, 6011.6): a value 14 m above the yard floor, a roof fall in the footprint join"},
            ],
        },
        "evidence": {
            "heightmap_before": {"pit_sample": {"x": -4245.81, "y": 5899.01, "z_m": -0.90},
                                 "roadbed_12350003663": {"n": 1149, "min": -2.0, "median": 3.41, "max": 9.64,
                                                         "note": "pixel centres inside the two roadbed parts on the t_-5_5 lattice"},
                                 "podium_bin_1088961": {"n": 4525, "min": -1.89, "median": 2.37, "max": 8.53},
                                 "extent": {"n": 16876, "min": -2.0, "median": 2.83, "max": 9.71,
                                            "note": "pixel centres inside the resolved extents on both tiles' lattices, 12,262 on t_-5_5 and 4,614 on t_-5_6; the min/median/max are the implementer's pre-application measurement"}},
            "roads_before": {"segment_1267_10_AVE_z": [5.15, 0.60, -0.65, 9.39], "node_21199_z": 5.15, "node_21145_z": 6.92},
            "why_not_the_catalogue_datum": ("blender_out/landmarks/catalog/c_hudson_yards.json origin_tm z = 7.8232 m is the mean of the OTI "
                                            "ground elevations of six footprints (16, 28, 30, 31, 40 and 9 ft) across two epochs "
                                            "(c_common.py ground_of), not a survey of the deck; it is not used here."),
        },
    },
    {
        "deck_id": "eleventh_ave_west_side_yard_viaduct",
        "name": "Eleventh Avenue on structure across the West Side Yard, W 30th to W 33rd",
        "kind": "platform",
        "status": "applied",
        "structure": ("Eleventh Avenue between W 30th and W 33rd Streets, carried over the tracks that join the "
                      "Eastern and Western Rail Yards.  CSCL codes it at grade (segments 172352 and 193965, level 13)."),
        "what_the_dem_holds": ("The yard beneath the avenue at 1.2-2.9 m NAVD88 (bridge decks are classified out of "
                               "a bare-earth product), where the avenue's own 'Unchanged' spot elevations read 7.67, "
                               "8.54 and 9.42 m; south of the bridge polygon the DEM and the spots agree (5.15-6.34 m)."),
        "extent": [
            {"part": "structure",
             "what": "the bridge polygon DoITT maps for Eleventh Avenue over the yard (carriageway and both sidewalks, "
                     "5,236 m2, about W 31st to W 33rd); the avenue's roadbed south of it is on the ground and is not "
                     "in the extent",
             "dataset": "DoITT planimetric transportation structures, feat_code 2300 (bridge), "
                        "data/raw/nyc_opendata/plan_transport_structures.geojson",
             "feat_code": 2300, "source_id": "12230000085"},
        ],
        "control": {
            "rule": "as above",
            "spot_elevations_inside": [
                {"source_id": "12300023000", "z_m": 7.666, "x": -4512.02, "y": 5976.33, "status": "Unchanged", "where": "heightmap 2.86 m before"},
                {"source_id": "0", "z_m": 8.487, "x": -4504.61, "y": 5989.29, "status": "New", "where": "heightmap 2.22 m before"},
                {"source_id": "12300023229", "z_m": 8.542, "x": -4482.39, "y": 6029.59, "status": "Unchanged", "where": "heightmap 2.79 m before"},
                {"source_id": "0", "z_m": 10.090, "x": -4468.11, "y": 6054.87, "status": "New", "where": "heightmap 2.89 m before"},
                {"source_id": "12300023519", "z_m": 9.418, "x": -4452.75, "y": 6082.86, "status": "Unchanged", "where": "heightmap 2.66 m before"},
            ],
            "excluded_spot_elevations": [],
            "excluded_footprint_grounds": [],
        },
        "evidence": {
            "heightmap_before": {"bridge_12230000085": {"n": 1310, "min": 1.16, "median": 2.78, "max": 9.58},
                                 "roadbed_12350004092_north_part": {"n": 702, "min": 2.62, "median": 2.79, "max": 9.7}},
            "roads_before": {"segments_172352_193965_11_AVE": "level 13 (at grade) between nodes 21143 (5.71 m) and 21146 (8.64 m)"},
            "found_while": "measuring the west edge of hudson_yards_ery_platform: the same excavation continues under the avenue",
        },
    },
]

#: Measured on the same pass and **not** applied: each needs its own extent polygon research before it can be a
#: row.  Kept here so the register says what it knows it has not done.
CANDIDATES_NOT_APPLIED: list[dict] = [
    {"name": "Manhattan West platform (Ninth-Tenth Avenues, W 31st-W 33rd), built 2014-16 over the Penn Station approach cut",
     "evidence": "spot 12300022542 7.91 m at (-4150.7, 5853.6) reads 3.59 m in the heightmap; spot 12300022706 7.49 m at "
                 "(-4122.3, 5904.5) reads 0.95 m; DoITT roadbeds 12350003654 and 12350003658 east of Tenth Avenue read "
                 "min -1.8 m under a median of 7.3 m",
     "why_not": "the platform's extent has no polygon in the processed tables that this pass verified"},
]


# ----------------------------------------------------------------------------- extent resolution
def _norm_id(v) -> str:
    s = str(v)
    return s[:-2] if s.endswith(".0") else s


def _read_pavement(tiles: list[str]):
    import pandas as pd
    import geopandas as gpd

    frames = []
    for t in tiles:
        p = PAVEMENT_DIR / f"{t}.parquet"
        if not p.exists():
            raise PlatformError(f"missing {p}")
        frames.append(gpd.read_parquet(p))
    pv = pd.concat(frames, ignore_index=True)
    pv["_sid"] = [_norm_id(v) for v in pv["source_id"].values]
    return pv


def _roadbed_rows(pv, source_id: str):
    return pv[(pv["feat_code"].values == ROADBED_FEAT_CODE) & (pv["_sid"].values == source_id)]


def resolve_part(part: dict) -> tuple[shapely.Geometry, dict]:
    """The polygon of one extent part, from the datasets it names, plus what was read to make it."""
    from shapely.ops import unary_union

    kind = part["part"]
    if kind == "structure":
        import pyogrio

        from ..crs import NYC_TM
        from ..paths import RAW
        path = RAW / "nyc_opendata" / "plan_transport_structures.geojson"
        if not path.exists():
            raise PlatformError(f"missing {path}")
        # source_id is numeric in the GeoJSON (12230000085.0): read the feature code's rows, match the id as text
        g = pyogrio.read_dataframe(path, where=f"feat_code = '{int(part['feat_code'])}'").to_crs(NYC_TM)
        g = g[[_norm_id(v) == str(part["source_id"]) for v in g["source_id"].values]]
        if len(g) == 0:
            raise PlatformError(f"structure source_id {part['source_id']} feat_code {part['feat_code']} not in {path.name}")
        geom = unary_union(g.geometry.values)
        return geom, {"part": kind, "source_id": part["source_id"], "feat_code": int(part["feat_code"]),
                      "polygons": int(len(g)), "area_m2": round(float(geom.area), 1)}
    pv = _read_pavement(list(part["tiles"]))
    if kind == "frontage":
        rows = pv[(pv["feat_code"].values == int(part["feat_code"])) & pv["_sid"].isin(list(part["source_ids"])).values]
        if len(rows) == 0:
            raise PlatformError(f"frontage polygons {part['source_ids']} not in {part['tiles']}")
        walk = unary_union(rows.geometry.values)
        mine = unary_union(_roadbed_rows(pv, part["roadbed"]).geometry.values)
        if mine.is_empty:
            raise PlatformError(f"frontage roadbed {part['roadbed']} not in {part['tiles']}")
        others = pv[(pv["feat_code"].values == ROADBED_FEAT_CODE) & (pv["_sid"].values != part["roadbed"])]
        geom = frontage_of(walk, mine, unary_union(others.geometry.values))
        return geom, {"part": kind, "feat_code": int(part["feat_code"]), "source_ids": list(part["source_ids"]),
                      "roadbed": part["roadbed"], "polygon_area_m2": round(float(walk.area), 1),
                      "area_m2": round(float(geom.area), 1)}
    if kind == "pavement":
        rows = pv[(pv["feat_code"].values == int(part["feat_code"])) & pv["_sid"].isin(list(part["source_ids"])).values]
        missing = sorted(set(part["source_ids"]) - set(rows["_sid"].values))
        if missing:
            raise PlatformError(f"pavement feat_code {part['feat_code']} source_ids {missing} not in {part['tiles']}")
        geom = unary_union(rows.geometry.values)
        return geom, {"part": kind, "feat_code": int(part["feat_code"]), "source_ids": list(part["source_ids"]),
                      "polygons": int(len(rows)), "area_m2": round(float(geom.area), 1)}
    if kind == "roadbed":
        rows = _roadbed_rows(pv, part["source_id"])
        if len(rows) == 0:
            raise PlatformError(f"roadbed source_id {part['source_id']} not in {part['tiles']}")
        geom = unary_union(rows.geometry.values)
        return geom, {"part": kind, "source_id": part["source_id"], "polygons": int(len(rows)),
                      "area_m2": round(float(geom.area), 1)}
    if kind == "block":
        import pandas as pd
        nodes = pd.read_parquet(NODES_PATH, columns=["node_id", "x", "y", "intersection_name"]).set_index("node_id")
        corners = []
        for nid, name in zip(part["corner_nodes"], part["corner_names"]):
            if nid not in nodes.index:
                raise PlatformError(f"node {nid} ({name}) not in {NODES_PATH}")
            corners.append((float(nodes.loc[nid, "x"]), float(nodes.loc[nid, "y"])))
        quad = shapely.Polygon(corners)
        if not quad.is_valid:
            raise PlatformError("corner nodes do not form a simple polygon")
        rb = pv[(pv["feat_code"].values == ROADBED_FEAT_CODE) & shapely.intersects(pv.geometry.values, quad)]
        crosses = shapely.intersects(rb.geometry.values, quad.exterior)
        keep = set(part.get("keep_roadbeds", []))
        bounding = rb[crosses & ~rb["_sid"].isin(keep).values]
        inner = rb[~crosses]
        block = quad.difference(unary_union(bounding.geometry.values)) if len(bounding) else quad
        return block, {"part": kind, "corner_nodes": list(part["corner_nodes"]),
                       "corners_tm": [(round(x, 2), round(y, 2)) for x, y in corners],
                       "quad_area_m2": round(float(quad.area), 1),
                       "roadbeds_subtracted": sorted({s for s in bounding["_sid"].values}),
                       "roadbeds_subtracted_area_m2": round(float(bounding.geometry.area.sum()), 1),
                       "roadbeds_inside_kept": sorted({s for s in inner["_sid"].values}),
                       "area_m2": round(float(block.area), 1)}
    raise PlatformError(f"unknown extent part kind {kind!r}")


FRONTAGE_CELL_M = 0.5   # raster cell of the nearer-to test; the 2 m terrain lattice cannot see anything finer


def frontage_of(walk: shapely.Geometry, mine: shapely.Geometry, others: shapely.Geometry) -> shapely.Geometry:
    """The part of ``walk`` nearer to ``mine`` than to ``others`` -- a sidewalk polygon's frontage on one carriageway.

    Decided on a ``FRONTAGE_CELL_M`` raster of the polygon (a Voronoi split between polygons has no closed form
    in shapely) and returned as the union of the winning cells, so the answer is the same for every tile.
    """
    from rasterio.features import shapes

    b = walk.bounds
    x0, y0 = np.floor(b[0] / FRONTAGE_CELL_M) * FRONTAGE_CELL_M, np.floor(b[1] / FRONTAGE_CELL_M) * FRONTAGE_CELL_M
    w = int(np.ceil((b[2] - x0) / FRONTAGE_CELL_M)) + 1
    h = int(np.ceil((b[3] - y0) / FRONTAGE_CELL_M)) + 1
    tr = Affine(FRONTAGE_CELL_M, 0.0, x0, 0.0, -FRONTAGE_CELL_M, y0 + h * FRONTAGE_CELL_M)
    inside = rasterize([(walk, 1)], out_shape=(h, w), transform=tr, all_touched=False, dtype=np.uint8).astype(bool)
    rows, cols = np.nonzero(inside)
    if rows.size == 0:
        return shapely.Polygon()
    xs = tr.c + FRONTAGE_CELL_M / 2.0 + FRONTAGE_CELL_M * cols
    ys = tr.f - FRONTAGE_CELL_M / 2.0 - FRONTAGE_CELL_M * rows
    pts = shapely.points(np.c_[xs, ys])
    win = shapely.distance(pts, mine) < shapely.distance(pts, others)
    mask = np.zeros((h, w), dtype=np.uint8)
    mask[rows[win], cols[win]] = 1
    polys = [shapely.geometry.shape(g) for g, v in shapes(mask, mask=mask.astype(bool), transform=tr) if v == 1]
    return unary_union(polys) if polys else shapely.Polygon()


def resolve_extent(row: dict) -> tuple[shapely.Geometry, list[dict]]:
    from shapely.ops import unary_union

    geoms, details = [], []
    for part in row["extent"]:
        g, d = resolve_part(part)
        geoms.append(g)
        details.append(d)
    geom = unary_union(geoms)
    geom = shapely.make_valid(geom)
    if geom.geom_type == "GeometryCollection":
        geom = unary_union([p for p in geom.geoms if p.geom_type in ("Polygon", "MultiPolygon")])
    if geom.is_empty:
        raise PlatformError(f"{row['deck_id']}: empty extent")
    return geom, details


# ----------------------------------------------------------------------------- the built table
def build(out: Path = DECKS_PATH) -> dict:
    """Resolve every applied register row to a polygon and write ``platform_decks.parquet`` (+ ``.json``)."""
    t0 = time.time()
    pts = load_index()
    rows_out, summary_rows = [], []
    for row in REGISTER:
        if row.get("status") != "applied":
            continue
        geom, details = resolve_extent(row)
        b = geom.bounds
        sel = pts.query_bbox(b[0], b[1], b[2], b[3])
        inside = sel[shapely.contains_xy(geom, pts.x[sel], pts.y[sel])]
        spots = inside[pts.kind[inside] == KIND_SPOT]
        bldg = inside[pts.kind[inside] == KIND_BUILDING]
        excluded = _excluded_spots(row, pts, spots)
        control = spots[~excluded]
        cz = pts.z[control].astype(np.float64)
        listed = len(row["control"]["spot_elevations_inside"])
        if listed != int(control.size):
            log.warning("%s: the register lists %d control spots, the index holds %d inside the extent",
                        row["deck_id"], listed, int(control.size))
        rec = {
            "deck_id": row["deck_id"], "name": row["name"], "kind": row["kind"], "status": row["status"],
            "area_m2": float(geom.area), "n_control_spots": int(control.size),
            "n_excluded_spots": int(excluded.sum()), "n_excluded_footprint_grounds": int(bldg.size),
            "control_z_min_m": float(cz.min()) if cz.size else float("nan"),
            "control_z_median_m": float(np.median(cz)) if cz.size else float("nan"),
            "control_z_max_m": float(cz.max()) if cz.size else float("nan"),
            "register": json.dumps(row, sort_keys=True),
            "geometry": shapely.to_wkb(geom),
        }
        rows_out.append(rec)
        summary_rows.append({k: v for k, v in rec.items() if k not in ("geometry", "register")}
                            | {"bounds_tm": [round(v, 1) for v in b], "extent_parts": details,
                               "control_spots_listed": listed,
                               "control_spots_in_index": [{"x": round(float(pts.x[i]), 2), "y": round(float(pts.y[i]), 2),
                                                           "z_m": round(float(pts.z[i]), 3)} for i in control],
                               "excluded_footprint_grounds_in_index": [{"x": round(float(pts.x[i]), 2), "y": round(float(pts.y[i]), 2),
                                                                        "z_m": round(float(pts.z[i]), 3)} for i in bldg]})
    if not rows_out:
        raise PlatformError("no applied rows in the register")
    tbl = pa.table({
        "deck_id": pa.array([r["deck_id"] for r in rows_out], pa.string()),
        "name": pa.array([r["name"] for r in rows_out], pa.string()),
        "kind": pa.array([r["kind"] for r in rows_out], pa.string()),
        "status": pa.array([r["status"] for r in rows_out], pa.string()),
        "area_m2": pa.array([r["area_m2"] for r in rows_out], pa.float64()),
        "n_control_spots": pa.array([r["n_control_spots"] for r in rows_out], pa.int32()),
        "n_excluded_spots": pa.array([r["n_excluded_spots"] for r in rows_out], pa.int32()),
        "n_excluded_footprint_grounds": pa.array([r["n_excluded_footprint_grounds"] for r in rows_out], pa.int32()),
        "control_z_min_m": pa.array([r["control_z_min_m"] for r in rows_out], pa.float64()),
        "control_z_median_m": pa.array([r["control_z_median_m"] for r in rows_out], pa.float64()),
        "control_z_max_m": pa.array([r["control_z_max_m"] for r in rows_out], pa.float64()),
        "register": pa.array([r["register"] for r in rows_out], pa.string()),
        "geometry": pa.array([r["geometry"] for r in rows_out], pa.binary()),
    }, metadata={b"nycsim.schema": SCHEMA.encode(), b"nycsim.crs": b"NYC_TM"})
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(f".{os.getpid()}.tmp.parquet")
    pq.write_table(tbl, tmp, compression="zstd")
    os.replace(tmp, out)
    summary = {"schema": SCHEMA, "path": str(out), "rows": len(rows_out), "decks": summary_rows,
               "candidates_not_applied": CANDIDATES_NOT_APPLIED,
               "rules": ["extent from real polygons only", "elevation from the survey (eight nearest points, 30-240 m)",
                         "footprint grounds inside an extent excluded", "burned where deck > ground (max), ground kept elsewhere"],
               "seconds": round(time.time() - t0, 1)}
    with open(DECKS_JSON, "w") as f:
        json.dump(summary, f, indent=1)
    from . import manifest_safe as manifest
    manifest.record_processed("terrain_platform_decks", out, stage="terrain",
                              sources=["plan_roadbed", "road_network_nodes", "plan_elevation_points", "building_footprints"],
                              rows=len(rows_out), schema=SCHEMA,
                              extra={"deck_ids": [r["deck_id"] for r in rows_out],
                                     "area_m2": round(sum(r["area_m2"] for r in rows_out), 1)})
    return summary


def _excluded_spots(row: dict, pts: PointIndex, spots: np.ndarray) -> np.ndarray:
    """Boolean over ``spots``: the ones the row lists under ``excluded_spot_elevations`` (matched by x, y, z)."""
    out = np.zeros(spots.size, dtype=bool)
    for ex in row["control"].get("excluded_spot_elevations", []):
        d = np.hypot(pts.x[spots] - ex["x"], pts.y[spots] - ex["y"])
        hit = (d < 1.0) & (np.abs(pts.z[spots] - ex["z_m"]) < 0.02)
        if not hit.any():
            raise PlatformError(f"{row['deck_id']}: excluded spot {ex} is not in the point index inside the extent")
        out |= hit
    return out


# ----------------------------------------------------------------------------- per-tile use
@dataclass
class PlatformDecks:
    """The built table, loaded once per worker."""
    deck_id: list[str]
    geoms: np.ndarray
    rows: list[dict]
    tree: shapely.STRtree = field(repr=False)
    union: shapely.Geometry = field(repr=False)

    @classmethod
    def load(cls, path: Path = DECKS_PATH) -> "PlatformDecks":
        meta = pq.read_schema(path).metadata or {}
        got = meta.get(b"nycsim.schema", b"").decode()
        if got != SCHEMA:
            raise PlatformError(f"{path}: schema {got!r} != {SCHEMA!r}")
        t = pq.read_table(path)
        geoms = np.array([shapely.from_wkb(b) for b in t.column("geometry").to_pylist()], dtype=object)
        rows = [json.loads(s) for s in t.column("register").to_pylist()]
        from shapely.ops import unary_union
        return cls(t.column("deck_id").to_pylist(), geoms, rows, shapely.STRtree(geoms), unary_union(list(geoms)))

    @classmethod
    def load_or_none(cls, path: Path = DECKS_PATH) -> "PlatformDecks | None":
        return cls.load(path) if path.exists() else None

    def __len__(self) -> int:
        return len(self.deck_id)

    def tile_mask(self, transform: Affine, shape: tuple[int, int], bounds: tuple[float, float, float, float]) -> np.ndarray:
        """int16 raster: index of the deck whose polygon contains the sample centre, ``NO_DECK`` elsewhere.

        Pixel-centre rule (``all_touched=False``), like every hydro layer, so the same sample gets the same
        answer whichever tile asks.
        """
        out = np.full(shape, NO_DECK, dtype=np.int16)
        idx = self.tree.query(shapely.box(*bounds), predicate="intersects")
        if idx.size == 0:
            return out
        rasterize(((self.geoms[i], int(i)) for i in np.sort(idx)), out=out, transform=transform, all_touched=False)
        return out

    def excluded_points(self, pts: PointIndex, bounds: tuple[float, float, float, float]) -> np.ndarray:
        """Indices (global order) of the survey points the register excludes within ``bounds``."""
        sel = pts.query_bbox(*bounds)
        if sel.size == 0:
            return sel
        inside = shapely.contains_xy(self.union, pts.x[sel], pts.y[sel])
        drop = inside & (pts.kind[sel] == KIND_BUILDING)
        for i, row in enumerate(self.rows):
            for ex in row["control"].get("excluded_spot_elevations", []):
                d = np.hypot(pts.x[sel] - ex["x"], pts.y[sel] - ex["y"])
                drop |= (d < 1.0) & (np.abs(pts.z[sel] - ex["z_m"]) < 0.02)
        return sel[drop]

    def deck_surface(self, mask: np.ndarray, transform: Affine, pts: PointIndex) -> np.ndarray:
        """The survey-controlled deck elevation at every masked sample (NaN elsewhere and where no survey point
        lies within ``SURVEY_REACH_M``).

        The eight nearest survey points within 240 m, inverse distance squared, distances floored at
        ``IDW_MIN_D_M`` -- ``tiles.survey_fill``'s points, weights and reach, without its growing-radius rule
        (the module docstring says why, with the measurement) -- over the global point index minus the excluded
        points, evaluated with a k-d tree so a whole tile costs milliseconds instead of a Python loop per
        sample.  Depends only on the sample coordinate and the global points, never on the tile window.
        """
        from scipy.spatial import cKDTree

        out = np.full(mask.shape, np.nan, dtype=np.float64)
        rows, cols = np.nonzero(mask != NO_DECK)
        if rows.size == 0:
            return out
        xs = transform.c + SPACING_M / 2.0 + SPACING_M * cols
        ys = transform.f - SPACING_M / 2.0 - SPACING_M * rows
        r_max = SURVEY_REACH_M
        bounds = (xs.min() - r_max, ys.min() - r_max, xs.max() + r_max, ys.max() + r_max)
        sel = pts.query_bbox(*bounds)
        if sel.size == 0:
            return out
        drop = self.excluded_points(pts, bounds)
        allowed = sel[~np.isin(sel, drop)]
        if allowed.size == 0:
            return out
        tree = cKDTree(np.c_[pts.x[allowed], pts.y[allowed]])
        k = min(SURVEY_K, allowed.size)
        d, j = tree.query(np.c_[xs, ys], k=k, distance_upper_bound=r_max)
        d = np.atleast_2d(d.reshape(rows.size, k))
        j = np.atleast_2d(j.reshape(rows.size, k))
        ok = np.isfinite(d) & (d <= r_max)
        w = np.where(ok, 1.0 / np.maximum(d, IDW_MIN_D_M) ** 2, 0.0)
        jz = np.where(ok, j, 0)
        z = pts.z[allowed[jz]].astype(np.float64)
        wsum = w.sum(axis=1)
        got = wsum > 0
        vals = np.full(rows.size, np.nan)
        vals[got] = (w * z).sum(axis=1)[got] / wsum[got]
        out[rows, cols] = vals
        return out


def burn(z: np.ndarray, valid: np.ndarray, mask: np.ndarray, deck_z: np.ndarray,
         deck_ids: list[str] | None = None) -> tuple[np.ndarray, np.ndarray, dict]:
    """``z = max(z, deck)`` inside every deck's extent.  Returns ``(z, covered, stats)``.

    ``covered`` marks the samples that now carry a deck decision (burned or kept-with-control): the caller
    excludes them from the sub-datum repair, exactly as it excludes pier decks.  A void sample (``~valid``)
    inside an extent takes the deck outright.
    """
    inside = (mask != NO_DECK) & np.isfinite(deck_z)
    no_control = (mask != NO_DECK) & ~np.isfinite(deck_z)
    rise = np.where(inside, deck_z - z, 0.0)
    burned = inside & ((rise > 0.0) | ~valid)
    out = z.copy()
    out[burned] = deck_z[burned]
    stats = {"px_in_extent": int((mask != NO_DECK).sum()), "px_burned": int(burned.sum()),
             "px_ground_kept": int((inside & ~burned).sum()), "px_no_control": int(no_control.sum()), "decks": []}
    for i in np.unique(mask[mask != NO_DECK]):
        m = mask == i
        b = burned & m
        rec = {"deck_id": deck_ids[i] if deck_ids else int(i), "px_in_extent": int(m.sum()), "px_burned": int(b.sum()),
               "px_ground_kept": int((inside & m & ~b).sum()), "px_no_control": int((no_control & m).sum())}
        if b.any():
            dz = deck_z[b]
            rr = rise[b]
            rec.update({"deck_z_min_m": round(float(dz.min()), 3), "deck_z_median_m": round(float(np.median(dz)), 3),
                        "deck_z_max_m": round(float(dz.max()), 3), "rise_median_m": round(float(np.median(rr)), 3),
                        "rise_p95_m": round(float(np.percentile(rr, 95)), 3), "rise_max_m": round(float(rr.max()), 3)})
        stats["decks"].append(rec)
    return out, inside, stats


# ----------------------------------------------------------------------------- published-tile mode
def apply_to_published(tile_names: list[str], decks: PlatformDecks | None = None, pts: PointIndex | None = None,
                       dry_run: bool = False) -> dict:
    """Burn the register's decks into tiles that are already on disk; rewrite PNG + JSON in place."""
    from PIL import Image

    from .tiles import LAND_FLOOR_M, FILL_RADIUS_M, write_png

    decks = decks or PlatformDecks.load()
    pts = pts or load_index()
    t0 = time.time()
    results = []
    for name in tile_names:
        tile = Tile.parse(name)
        d = tile_dir(name, create=False)
        png_path, json_path = d / "terrain.png", d / "terrain.json"
        if not png_path.exists() or not json_path.exists():
            results.append({"tile": name, "skipped": "no published tile"})
            continue
        with open(json_path) as f:
            doc = json.load(f)
        vals = np.asarray(Image.open(png_path)).astype(np.uint16)
        z = vals.astype(np.float64) * float(doc["z_scale_m"]) + float(doc["z_min_m"])
        tr = tile_transform(tile, 0)
        shape = (SAMPLES, SAMPLES)
        bounds = bounds_of(tr, SAMPLES, SAMPLES)
        mask = decks.tile_mask(tr, shape, bounds)
        if not (mask != NO_DECK).any():
            results.append({"tile": name, "skipped": "no deck in this tile"})
            continue
        deck_z = decks.deck_surface(mask, tr, pts)
        valid = np.ones(shape, dtype=bool)
        z2, covered, st = burn(z, valid, mask, deck_z, decks.deck_id)
        changed = z2 != z
        if (changed & (mask == NO_DECK)).any():
            raise PlatformError(f"{name}: a sample outside every extent changed")
        # a sub-datum sample outside the extents but within the rim radius of one was rim-filled from pit
        # values here and would be filled from deck values in a rebuild: count it, do not guess it
        low = (z <= LAND_FLOOR_M + Z_SCALE_M) & (mask == NO_DECK)
        may_differ = 0
        if low.any():
            ly, lx = np.nonzero(low)
            px_ = tr.c + SPACING_M / 2.0 + SPACING_M * lx
            py_ = tr.f - SPACING_M / 2.0 - SPACING_M * ly
            may_differ = int(shapely.dwithin(decks.union, shapely.points(np.c_[px_, py_]), FILL_RADIUS_M).sum())
        zq = quantize(z2)
        newvals, z_min, z_scale = encode_png_values(zq)
        if z_scale != Z_SCALE_M:
            raise PlatformError(f"{name}: z_scale {z_scale} != {Z_SCALE_M}")
        # The decision is taken in the PNG's own quantised space.  On a tile that already carries the
        # deck, the float surface exceeds the quantised sample by under one quantum on about half the
        # samples, so ``burned`` above would recount them and, written back, overwrite the provenance of
        # an application that changed nothing.  A sample counts as burned here only if its published
        # value rises; a tile with no rising sample is left exactly as it is, JSON included.
        changed_q = newvals != vals
        if (changed_q & (mask == NO_DECK)).any():
            raise PlatformError(f"{name}: a published sample outside every extent would change")
        if not changed_q.any():
            results.append({"tile": name, "skipped": "already applied: no published sample rises",
                            "px_in_extent": st["px_in_extent"]})
            log.info("%s: already applied, nothing rises", name)
            continue
        burned_q = changed_q & (mask != NO_DECK)
        st = dict(st, px_burned=int(burned_q.sum()),
                  px_ground_kept=int(((mask != NO_DECK) & np.isfinite(deck_z) & ~burned_q).sum()))
        for drec in st["decks"]:
            i = decks.deck_id.index(drec["deck_id"]) if isinstance(drec["deck_id"], str) else drec["deck_id"]
            m = mask == i
            drec["px_burned"] = int((burned_q & m).sum())
            drec["px_ground_kept"] = int((m & np.isfinite(deck_z) & ~burned_q).sum())
        rec = {"tile": name, "px_changed": int(changed_q.sum()), "z_min_m_before": doc["z_min_m"], "z_min_m_after": float(z_min),
               "z_max_m_before": doc["z_max_m"], "z_max_m_after": float(z_min + float(newvals.max()) * z_scale),
               "rebuild_may_differ_px": may_differ, **st}
        if not dry_run:
            png_bytes = write_png(png_path, newvals)
            px = dict(doc.get("px", {}))
            px["platform_deck"] = int(st["px_burned"])
            doc["px"] = px
            sources = [s for s in doc.get("sources", []) if s != "platform_deck"]
            if st["px_burned"]:
                sources.append("platform_deck")
            doc["sources"] = sources
            doc["z_min_m"] = float(z_min)
            doc["z_max_m"] = rec["z_max_m_after"]
            doc["platform"] = {"applied_by": "published_tile", "px_in_extent": st["px_in_extent"], "px_burned": st["px_burned"],
                               "px_ground_kept": st["px_ground_kept"], "px_no_control": st["px_no_control"],
                               "rebuild_may_differ_px": may_differ, "decks": st["decks"]}
            tmp = json_path.with_suffix(f".{os.getpid()}.tmp.json")
            with open(tmp, "w") as f:
                json.dump(doc, f, indent=1, sort_keys=True)
            os.replace(tmp, json_path)
            rec["png_bytes"] = png_bytes
        results.append(rec)
        log.info("%s: %s", name, {k: v for k, v in rec.items() if k != "decks"})
    summary = {"schema_version": 1, "mode": "published_tile", "dry_run": dry_run, "tiles": results,
               "decks": decks.deck_id, "seconds": round(time.time() - t0, 1),
               "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    if not dry_run:
        APPLIED_JSON.parent.mkdir(parents=True, exist_ok=True)
        with open(APPLIED_JSON, "w") as f:
            json.dump(summary, f, indent=1)
        from . import manifest_safe as manifest
        manifest.record_processed("terrain_platform_decks_applied", APPLIED_JSON, stage="terrain",
                                  sources=["terrain_platform_decks", "plan_elevation_points", "building_footprints"],
                                  rows=len([r for r in results if "px_changed" in r]), schema="terrain.platform_decks_applied/1",
                                  extra={"tiles": [r["tile"] for r in results if "px_changed" in r]})
    return summary


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=("build", "apply-to-published"))
    ap.add_argument("--tiles", help="comma separated tile names (apply-to-published)")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    if a.command == "build":
        s = build()
    else:
        if not a.tiles:
            ap.error("--tiles is required for apply-to-published")
        s = apply_to_published([t.strip() for t in a.tiles.split(",") if t.strip()], dry_run=a.dry_run)
    print(json.dumps(s, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
