"""New Jersey buildings tiling stage: FEMA/ORNL USA Structures -> ``tiles/{tile}/buildings_nj.parquet``.

    python -m nycsim_pipeline.buildings.nj_tiles [--out-dir DIR] [--no-tiles] [--limit N]

ARCHITECTURE §3 puts the New Jersey shoreline inside the project scope and §5 says the NJ side is a
skyline, not a drivable borough.  The terrain stage already covers it (1,104 NJ tiles); this stage
gives those tiles their buildings.

Why a **separate file** from ``buildings.parquet``
--------------------------------------------------
``tiles/{tile}/buildings.parquet`` is the New York City table: a real BIN per row, PLUTO attributes,
CityGML roof massing, LPC landmark status.  New Jersey has none of that.  Nine tiles carry both a
New York City and a New Jersey footprint (Bayonne against Staten Island, Weehawken against the
Hudson bulkhead), so the two cannot share one file without either losing the distinction or
inventing New York attributes for New Jersey rows.  They are therefore written side by side, with
``nycsim.schema = buildings_nj/1``, and every consumer that wants one gets exactly that one.

What is real here and what is not
---------------------------------
* **Footprint** — real, FEMA/ORNL USA Structures, public domain.  ``FOOTPRINT_REAL`` is set on every
  row.
* **Height** — three provenances, recorded per row in ``height_source`` and in the fidelity
  bitfield.  73.7 % of rows carry a LiDAR-derived ``height_m`` from the source; the rest get the
  median of the ten nearest rows that do have one.  The source height is measured but it is **not**
  New York City quality — it is a return off 2013 imagery and it truncates the Jersey City towers by
  a median 66.41 m — so where an OpenStreetMap footprint matches at IoU >= 0.5 its ``height`` tag
  replaces the source value (``HEIGHT_REAL``, ``SRC_OSM_HEIGHT``) and its ``building:levels`` tag
  replaces it where the source height cannot carry the storeys the tag counts
  (``HEIGHT_INFERRED``, ``SRC_OSM_LEVELS`` — a derivation, never presented as measured).  The rules
  and the measurements behind them are in :mod:`nj_osm_heights`; :func:`height_report` and
  :func:`published_height_report` measure the result against the independent heights already in this
  repository, before and after, and write both into ``buildings_nj_summary.json``.  Nothing is
  rescaled: a height either comes from a source that states it or is derived from a storey count
  that a source states.
* **Ground elevation** — the source column is null on all 231,336 rows, so ground comes from this
  project's own terrain (``terrain/segment_z.sample_z``, seam-continuous, bilinear on the published
  2 m heightmaps), sampled over the footprint outline and taken at its minimum, which is the grade a
  building sits on.  ``GROUND_REAL`` means "from a per-building LiDAR ground field" (DATA_CONTRACTS
  §5.1 bit 9) and is therefore **never** set here; ``ground_source`` records ``SRC_TERRAIN``.
* **Roof shape** — there is no LOD2 model for New Jersey.  Every row is emitted flat with a parapet
  and ``ROOF_REAL`` is never set.
* **Floors** — no source; derived from the height with an occupancy-class storey table.
  ``FLOORS_REAL`` is never set, ``FLOORS_INFERRED`` always is.
* **Year, materials, landmark status, storefronts** — no source.  ``YEAR_REAL``, ``MATERIAL_REAL``,
  ``SIGNAGE_REAL``, ``SCAFFOLD_REAL`` and ``LANDMARK_MODEL`` are never set.  ``material_primary``
  comes from an occupancy × height rule (below) and carries ``FACADE_INFERRED``, exactly as ADR-004
  requires of an inferred facade.

So a New Jersey row is distinguishable from a New York City row four ways over: a different file, a
different ``nycsim.schema``, ``borough = 6`` (the New Jersey code of DATA_CONTRACTS §2, which the
terrain stage already uses), and a fidelity bitfield that never claims a roof, a floor count, a year
or a material.

The city boundary wins inside the city
--------------------------------------
USA Structures covers Ellis Island and Liberty Island — filled land New Jersey won sovereignty over
in 1998 — and the New York footprint table already carries those buildings, several of them
hand-modelled landmarks.  Following ADR-019, which cuts OpenStreetMap water against the city's own
land boundary, every structure whose centroid falls inside the five boroughs is dropped here and
counted, so no building is modelled twice.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import logging
import sys
import time
from pathlib import Path

import numpy as np
import polars as pl
import pyarrow as pa
import pyarrow.parquet as pq
import shapely

from .. import manifest
from ..crs import NYC_TM
from ..paths import PROCESSED, RAW
from ..terrain.segment_z import ZSampler
from ..tiling import tile_index_arrays
from . import schema as S
from .footprints import MIN_PART_AREA_M2, _polygonal_parts
from .infer import neighbour_median
from . import nj_osm_heights as osmh

log = logging.getLogger("nycsim.buildings.nj")

SOURCE_PARQUET = PROCESSED / "nj" / "buildings_nj_usa_structures.parquet"
BOROUGH_BOUNDARIES = RAW / "nyc_opendata" / "borough_boundaries.geojson"
SOURCE_ID = "usa_structures_nj_hudson"
SCHEMA_ID = "buildings_nj/2"     # /2 adds the OpenStreetMap height-join columns (deviation B11a)
SCHEMA_VERSION = 2
TILE_FILENAME = "buildings_nj.parquet"
BOROUGH_NJ = 6              # DATA_CONTRACTS §2: 1 MN 2 BX 3 BK 4 QN 5 SI 6 NJ 0 water
# The licence of the footprints and of every USA Structures attribute.  Since deviation B11a was
# closed the ``height`` column can also carry an OpenStreetMap tag or a value derived from one, which
# is ODbL and carries an attribution and share-alike obligation of its own: that licence travels
# beside this one in ``nycsim.license.osm`` on every file, and ``height_source`` says per row which
# of the two a height came from.
LICENSE = "Public domain (US Government work: FEMA / ORNL USA Structures)"
OSM_LICENSE = osmh.OSM_LICENSE
OSM_SOURCE_ID = osmh.OSM_SOURCE_ID

MIN_INFERRED_HEIGHT_M = 2.0   # floor for a height this stage had to infer; a measured one is published verbatim
MAX_PLAUSIBLE_HEIGHT_M = 600.0
GROUND_SAMPLE_MAX_VERTICES = 64     # outline samples per footprint before the ring is decimated
NYC_OVERLAP_MAX_M2 = 1.0            # footprint area inside the city boundary before the row is the city's
ROOF_TYPE_FLAT = 0                  # DATA_CONTRACTS §5 roof_type enum

# ---- occupancy typology -------------------------------------------------------------------------------------------
# USA Structures publishes OCC_CLS (occupancy class) and PRIM_OCC (primary occupancy).  These are the
# only typological attributes the source has, and they are the New Jersey analogue of the PLUTO
# building class the New York rules use.  The storey heights below are the same numbers as
# ``buildings/infer.py`` uses for the equivalent New York class, so a Hoboken walk-up and a Brooklyn
# walk-up get the same floor count from the same height.
#                          floor_h, ground_floor_h
_OCC_FLOORS: dict[str, tuple[float, float]] = {
    "Residential": (3.0, 3.3),
    "Commercial": (3.9, 4.5),
    "Industrial": (4.5, 4.5),
    "Education": (3.9, 4.5),
    "Government": (3.9, 4.5),
    "Assembly": (3.9, 4.5),
    "Utility and Misc": (4.5, 4.5),
    "Agriculture": (4.5, 4.5),
    "Unclassified": (3.0, 3.3),
}
_OCC_FLOORS_DEFAULT = (3.0, 3.3)

# Primary facade material by occupancy and size (ADR-004: inferred from real attributes, flagged
# FACADE_INFERRED, never presented as measured).  The enum is DATA_CONTRACTS §5 ``material_primary``.
MAT_RED_BRICK, MAT_BROWN_BRICK, MAT_TAN_BRICK = 0, 1, 2
MAT_LIMESTONE, MAT_GLASS_CURTAIN, MAT_CONCRETE = 5, 8, 9
MAT_VINYL_SIDING, MAT_WOOD_CLAPBOARD, MAT_METAL_PANEL = 11, 12, 14

# Hudson County — Jersey City, Hoboken, Union City, West New York, Weehawken, Bayonne — is a dense
# attached-masonry city built out before 1930: brick and brownstone row houses, with the post-1990
# glass towers on the waterfront.  The Bergen / Passaic / Essex / Union suburbs behind the Palisades
# ridge (Clifton, Nutley, Belleville, Bloomfield, Teaneck) are detached frame housing with clapboard
# and, post-war, vinyl siding.  County is a real source column, so this split is drawn from data.
MASONRY_COUNTIES = ("Hudson",)
GLASS_MIN_HEIGHT_M = 45.0
BRICK_MIN_HEIGHT_M = 12.0
LARGE_HOUSE_AREA_M2 = 200.0
LARGE_SHED_AREA_M2 = 2000.0


def _material_from_occupancy(occ: np.ndarray, county: np.ndarray, height: np.ndarray,
                             area: np.ndarray) -> np.ndarray:
    """Occupancy class × county × height × footprint area → ``material_primary`` (inferred, ADR-004)."""
    m = np.full(len(occ), MAT_RED_BRICK, dtype=np.int8)
    res = occ == "Residential"
    com = occ == "Commercial"
    ind = occ == "Industrial"
    masonry = np.isin(county, MASONRY_COUNTIES)
    m[res] = MAT_WOOD_CLAPBOARD
    m[res & (area >= LARGE_HOUSE_AREA_M2)] = MAT_VINYL_SIDING
    m[res & masonry] = MAT_RED_BRICK
    m[res & (height >= BRICK_MIN_HEIGHT_M)] = MAT_RED_BRICK
    m[res & (height >= 25.0)] = MAT_BROWN_BRICK
    m[com] = MAT_TAN_BRICK
    m[com & (height >= 25.0)] = MAT_LIMESTONE
    m[ind] = MAT_METAL_PANEL
    m[ind & (area >= LARGE_SHED_AREA_M2)] = MAT_CONCRETE
    m[np.isin(occ, ("Education", "Government", "Assembly"))] = MAT_TAN_BRICK
    m[np.isin(occ, ("Utility and Misc", "Agriculture"))] = MAT_CONCRETE
    m[height >= GLASS_MIN_HEIGHT_M] = MAT_GLASS_CURTAIN
    return m


# ---- Arrow schema -------------------------------------------------------------------------------------------------
# Contract-shaped columns keep the DATA_CONTRACTS §5 names and types so ``blender/buildings`` reads a
# New Jersey tile with the same loader it uses for a New York one.  The §5 columns New Jersey has no
# source for are still present and explicitly empty (year 0, class "", no landmark) rather than
# absent, so a consumer sees "known to be nothing" instead of "column missing".
COLUMNS: list[tuple[str, pa.DataType, bool]] = [
    ("bin", pa.int64(), True),                 # USA Structures BUILD_ID — NOT a New York City BIN
    ("bbl", pa.int64(), True),                 # no tax lot in New Jersey: 0
    ("borough", pa.int8(), True),              # always 6 (New Jersey)
    ("footprint", pa.binary(), True),
    ("ground_z", pa.float32(), True),
    ("roof_z", pa.float32(), True),
    ("roof_type", pa.int8(), True),            # always 0 (flat): no LOD2 roof source for New Jersey
    ("height", pa.float32(), True),
    ("floors", pa.int16(), True),
    ("floor_height", pa.float32(), True),
    ("ground_floor_height", pa.float32(), True),
    ("year_built", pa.int16(), True),          # no source: 0
    ("bldg_class", pa.string(), True),         # no PLUTO in New Jersey: ""
    ("land_use", pa.int8(), True),             # no PLUTO land use: 0
    ("material_primary", pa.int8(), True),     # inferred from occupancy (FACADE_INFERRED)
    ("has_storefront", pa.bool_(), True),      # no source: False
    ("has_scaffold", pa.bool_(), True),        # no source: False
    ("landmark_id", pa.string(), True),        # no LPC jurisdiction in New Jersey: ""
    ("osm_id", pa.int64(), True),              # the matched OpenStreetMap outline, or 0
    ("name", pa.string(), True),               # USA Structures carries no building name: ""
    ("lit_seed", pa.uint32(), True),
    ("fidelity", pa.uint16(), True),
    ("primary_facade_heading", pa.float32(), True),
    ("address", pa.string(), True),            # real: USA Structures PROP_ADDR
    ("tile", pa.string(), True),
    ("tx", pa.int32(), True),
    ("ty", pa.int32(), True),
    # ---- New Jersey extension columns ----
    ("build_id", pa.int64(), False),
    ("part_index", pa.int16(), False),
    ("footprint_area", pa.float32(), False),
    ("centroid_x", pa.float64(), False),
    ("centroid_y", pa.float64(), False),
    ("occ_class", pa.string(), False),
    ("prim_occ", pa.string(), False),
    ("sec_occ", pa.string(), False),
    ("city", pa.string(), False),
    ("county", pa.string(), False),
    ("state", pa.string(), False),
    ("src_source", pa.string(), False),        # USA Structures SOURCE (the contributing programme)
    ("val_method", pa.string(), False),
    ("image_date", pa.string(), False),        # the imagery the structure was digitised from
    ("fips", pa.string(), False),
    ("height_source", pa.int8(), False),
    ("floors_source", pa.int8(), False),
    ("ground_source", pa.int8(), False),
    ("facade_heading_method", pa.int8(), False),
    # ---- the OpenStreetMap height join (nj_osm_heights, deviation B11a) ----
    # The evidence behind ``height`` on this row, kept beside it so a consumer can audit the join
    # without redoing the geometry.  ``osm_match_iou`` is 0 and the tag columns NaN / 0 where no
    # OpenStreetMap outline matched; a tag present here was not necessarily used (see the rules).
    ("osm_match_iou", pa.float32(), False),
    ("osm_height_m", pa.float32(), False),      # NaN where the matched outline carries no height tag
    ("osm_levels", pa.int16(), False),          # 0 where it carries no building:levels tag
    # What this stage would have published without the join: the USA Structures height, or the
    # neighbour median where the source has none.  Kept so the correction is auditable per row and
    # so no source value is lost, the convention ADR-018 set for the terrain repairs.
    ("source_height_m", pa.float32(), False),
]
CONTRACT_COLUMNS = [c for c, _, k in COLUMNS if k]
EXTENSION_COLUMNS = [c for c, _, k in COLUMNS if not k]

# Bits this stage may set. Everything else stays clear because New Jersey has no source for it.
ALLOWED_BITS = (S.Fidelity.FOOTPRINT_REAL, S.Fidelity.HEIGHT_REAL, S.Fidelity.HEIGHT_INFERRED,
                S.Fidelity.FLOORS_INFERRED, S.Fidelity.FACADE_INFERRED)
NEVER_SET_BITS = (S.Fidelity.ROOF_REAL, S.Fidelity.FLOORS_REAL, S.Fidelity.YEAR_REAL,
                  S.Fidelity.MATERIAL_REAL, S.Fidelity.SIGNAGE_REAL, S.Fidelity.LANDMARK_MODEL,
                  S.Fidelity.SCAFFOLD_REAL, S.Fidelity.GROUND_REAL)


def arrow_schema(bbox=None, extra_meta: dict[str, str] | None = None) -> pa.Schema:
    """Arrow schema with the GeoParquet 1.1 ``geo`` block and the ``nycsim.*`` keys of the New York tiles."""
    fields = [pa.field(n, t, nullable=False) for n, t, _ in COLUMNS]
    meta = {
        b"geo": json.dumps(S.geo_metadata(bbox)).encode(),
        b"nycsim.schema": SCHEMA_ID.encode(),
        b"nycsim.schema_version": str(SCHEMA_VERSION).encode(),
        b"nycsim.license": LICENSE.encode(),
        b"nycsim.license.osm": OSM_LICENSE.encode(),
        b"nycsim.source": SOURCE_ID.encode(),
        b"nycsim.source.osm": OSM_SOURCE_ID.encode(),
        b"nycsim.borough": str(BOROUGH_NJ).encode(),
    }
    if extra_meta:
        meta.update({k.encode(): v.encode() for k, v in extra_meta.items()})
    return pa.schema(fields, metadata=meta)


# ---- the city boundary ----------------------------------------------------------------------------------------------
def _nyc_land() -> object:
    """Union of the five borough polygons in NYC_TM (the city's own land boundary)."""
    if not BOROUGH_BOUNDARIES.exists():
        raise FileNotFoundError(
            f"{BOROUGH_BOUNDARIES} is required: the New Jersey table is clipped against the city "
            "boundary so Ellis Island and Liberty Island are not modelled twice")
    import pyogrio

    gdf = pyogrio.read_dataframe(BOROUGH_BOUNDARIES).to_crs(NYC_TM)
    return shapely.union_all(np.asarray(gdf.geometry.values, dtype=object))


# ---- loading ------------------------------------------------------------------------------------------------------
def load_source(path: Path = SOURCE_PARQUET, limit: int | None = None) -> tuple[pl.DataFrame, np.ndarray, dict]:
    """Read the ingest output, explode multipolygons, drop degenerate parts, recompute tile keys.

    The ingest already reprojected to ``NYC_TM``; this re-verifies the declared CRS rather than
    trusting it, because everything downstream is metres in that frame.
    """
    if not path.exists() or path.stat().st_size == 0:
        raise FileNotFoundError(f"New Jersey buildings parquet missing or empty: {path}")
    pf = pq.ParquetFile(path)
    meta = {k.decode(): v.decode() for k, v in (pf.metadata.metadata or {}).items()}
    geo = json.loads(meta.get("geo", "{}"))
    crs = (geo.get("columns", {}).get("geometry", {}) or {}).get("crs")
    if crs is None or not NYC_TM.equals(crs):
        raise ValueError(f"{path}: geometry CRS is not NYC_TM (GeoParquet metadata says {crs!r})")
    table = pq.read_table(path)
    df = pl.from_arrow(table.drop(["geometry"]))
    wkb = table["geometry"].to_numpy(zero_copy_only=False)
    if limit:
        df, wkb = df.head(limit), wkb[:limit]
    del table
    stats: dict = {"rows_in": df.height, "crs_verified": "NYC_TM"}
    geoms = shapely.from_wkb(wkb)
    del wkb

    invalid = ~shapely.is_valid(geoms)
    stats["invalid_fixed"] = int(invalid.sum())
    if invalid.any():
        geoms[invalid] = shapely.make_valid(geoms[invalid])

    type_id = shapely.get_type_id(geoms)
    is_poly = type_id == 3
    stats["multipart_rows"] = int((~is_poly).sum())
    part_index = np.zeros(len(geoms), dtype=np.int16)
    if not is_poly.all():
        keep_rows: list[int] = []
        new_geoms: list = []
        new_parts: list[int] = []
        for i in np.nonzero(~is_poly)[0]:
            for k, p in enumerate(_polygonal_parts(geoms[i])):
                keep_rows.append(int(i))
                new_geoms.append(p)
                new_parts.append(k)
        stats["multipart_parts"] = len(new_geoms)
        single = np.nonzero(is_poly)[0]
        order = np.concatenate([single, np.asarray(keep_rows, dtype=np.int64)])
        geoms = np.concatenate([geoms[single], np.asarray(new_geoms, dtype=object)])
        part_index = np.concatenate([np.zeros(len(single), dtype=np.int16),
                                     np.asarray(new_parts, dtype=np.int16)])
        df = df[pl.Series(order)]
    else:
        stats["multipart_parts"] = 0

    area = shapely.area(geoms)
    tiny = area < MIN_PART_AREA_M2
    stats["dropped_degenerate_lt_1m2"] = int(tiny.sum())
    if tiny.any():
        keep = ~tiny
        geoms, area, part_index = geoms[keep], area[keep], part_index[keep]
        df = df.filter(pl.Series(keep))

    cent = shapely.centroid(geoms)
    cx, cy = shapely.get_x(cent), shapely.get_y(cent)

    # ADR-019 applied to buildings: New York City's own datasets are the authority inside the city
    # boundary.  USA Structures covers Ellis Island and Liberty Island — filled land New Jersey won
    # sovereignty over in 1998 — and the New York footprint table already carries those same
    # buildings, hand-modelled as landmarks.  Keeping both would put two shells on one hospital, so
    # every row whose centroid falls inside the city is dropped here and counted.
    nyc = _nyc_land()
    inside = shapely.contains(nyc, shapely.points(cx, cy))
    # ... and a structure that only straddles the line counts too: two of the Liberty Island and
    # Ellis Island buildings sit with their centroid a few metres on the New Jersey side.
    tree = shapely.STRtree(geoms)
    for i in tree.query(nyc, predicate="intersects"):
        if shapely.area(shapely.intersection(geoms[i], nyc)) >= NYC_OVERLAP_MAX_M2:
            inside[i] = True
    stats["dropped_inside_nyc_boundary"] = int(inside.sum())
    if inside.any():
        log.info("dropping %d structures inside the New York City boundary (Ellis / Liberty Island): "
                 "the city's own footprint table already models them", int(inside.sum()))
        keep = ~inside
        geoms, area, part_index = geoms[keep], area[keep], part_index[keep]
        cx, cy = cx[keep], cy[keep]
        df = df.filter(pl.Series(keep))

    tx, ty = tile_index_arrays(cx, cy)
    tile = np.char.add(np.char.add(np.char.add("t_", tx.astype(str)), "_"), ty.astype(str))
    df = df.with_columns([
        pl.Series("part_index", part_index),
        pl.Series("footprint_area", area.astype(np.float32)),
        pl.Series("centroid_x", cx),
        pl.Series("centroid_y", cy),
        pl.Series("tx", tx),
        pl.Series("ty", ty),
        pl.Series("tile", tile),
    ])
    stats["rows_out"] = df.height
    stats["tiles"] = int(len(np.unique(tile)))
    log.info("New Jersey source: %d rows -> %d parts over %d tiles", stats["rows_in"], df.height, stats["tiles"])
    return df, geoms, stats


# ---- ground from the project's own terrain --------------------------------------------------------------------------
def sample_ground(geoms: np.ndarray, cx: np.ndarray, cy: np.ndarray,
                  sampler: ZSampler | None = None) -> tuple[np.ndarray, dict]:
    """Ground elevation per footprint: the minimum of the published terrain over its outline.

    The source's own ``ground_elev_m`` is null on every row, so the grade comes from this project's
    terrain — the same surface the engine loads, sampled through ``terrain.segment_z``, which is
    bilinear and seam-continuous.  Taking the **minimum** over the outline (plus the centroid) is the
    "lowest adjacent grade" convention: on the Palisades and the Weehawken bluff a footprint can span
    six metres of fall, and a building keyed to the mean would float on its downhill side.
    """
    zs = sampler if sampler is not None else ZSampler(missing="nearest")
    rings = shapely.get_exterior_ring(geoms)
    coords, idx = shapely.get_coordinates(rings, return_index=True)
    # decimate very long rings so the sample count stays bounded (the ring is closed, so the last
    # vertex repeats the first and is dropped with it)
    counts = np.bincount(idx, minlength=len(geoms))
    keep = np.ones(len(coords), dtype=bool)
    long_rings = np.nonzero(counts > GROUND_SAMPLE_MAX_VERTICES)[0]
    stats = {"footprints": int(len(geoms)), "rings_decimated": int(len(long_rings))}
    if len(long_rings):
        starts = np.concatenate([[0], np.cumsum(counts)[:-1]])
        for r in long_rings:
            s, n = int(starts[r]), int(counts[r])
            step = int(np.ceil(n / GROUND_SAMPLE_MAX_VERTICES))
            block = np.zeros(n, dtype=bool)
            block[::step] = True
            keep[s:s + n] = block
    coords, idx = coords[keep], idx[keep]
    xs = np.concatenate([coords[:, 0], cx])
    ys = np.concatenate([coords[:, 1], cy])
    owner = np.concatenate([idx, np.arange(len(geoms))])
    stats["samples"] = int(len(xs))
    z = np.asarray(zs.sample(xs, ys), dtype=np.float64)
    finite = np.isfinite(z)
    stats["samples_without_terrain"] = int((~finite).sum())
    ground = np.full(len(geoms), np.inf)
    np.minimum.at(ground, owner[finite], z[finite])
    missing = ~np.isfinite(ground)
    stats["footprints_without_terrain"] = int(missing.sum())
    if missing.any():
        # no published terrain under this footprint at all: fall back to the nearest neighbour that
        # does have one, so the row is still keyed to the real surface rather than to zero
        ground[missing] = neighbour_median(cx, cy, ground, ~missing, missing, k=1)
    stats["z_min_m"] = float(np.nanmin(ground))
    stats["z_max_m"] = float(np.nanmax(ground))
    stats["z_median_m"] = float(np.nanmedian(ground))
    stats["sampler"] = zs.stats
    return ground, stats


# ---- attributes ---------------------------------------------------------------------------------------------------
def _osm_tag_reach(o_height: np.ndarray, o_levels: np.ndarray, osm_row: np.ndarray,
                   nj_geoms: np.ndarray, osm_geoms: np.ndarray) -> dict:
    """How much of the OpenStreetMap tag stock the footprint match actually reaches.

    The OpenStreetMap extract covers a wider slice of New Jersey than the USA Structures table does
    — Newark, the Bergen suburbs, the Passaic valley — so a tag that never reaches the table is
    usually not a failed match at all: it is a tag on a building this project does not model.  The
    two are separated here rather than folded into one comforting number: ``*_over_the_table`` is
    the honest denominator, the tags that overlap a USA Structures polygon at all.
    """
    used = np.zeros(len(o_height), dtype=bool)
    used[osm_row[osm_row >= 0]] = True
    h, l = np.isfinite(o_height), np.isfinite(o_levels)
    tree = shapely.STRtree(nj_geoms)
    over = np.zeros(len(o_height), dtype=bool)
    idx = np.nonzero(h | l)[0]
    li, _ = tree.query(osm_geoms[idx], predicate="intersects")
    over[idx[np.unique(li)]] = True
    return {"height_tags": int(h.sum()), "height_tags_over_the_table": int((h & over).sum()),
            "height_tags_matched": int((h & used).sum()),
            "levels_tags": int(l.sum()), "levels_tags_over_the_table": int((l & over).sum()),
            "levels_tags_matched": int((l & used).sum()),
            "tagged_outlines": int((h | l).sum()),
            "tagged_outlines_over_the_table": int(((h | l) & over).sum()),
            "tagged_outlines_matched": int(((h | l) & used).sum())}


def resolve_attributes(df: pl.DataFrame, ground: np.ndarray, geoms: np.ndarray | None = None,
                       osm_path: Path | None = None, *, use_osm: bool = True,
                       ) -> tuple[pl.DataFrame, dict]:
    """Height, floors, storey heights, material and the fidelity bitfield.

    ``geoms`` (the footprints, in row order) enables the OpenStreetMap height join of
    :mod:`nj_osm_heights` — deviation B11a, the reason this stage no longer ships the source height
    verbatim on every row.  Every attribute derived from height (floors, storey heights, material,
    ``roof_z``) is computed *after* the join, from the height that is actually published, so the
    table cannot hold a floor count that disagrees with its own height.  Passing ``use_osm=False``
    or no geometry reproduces the source-only table exactly.
    """
    n = df.height
    cx, cy = df["centroid_x"].to_numpy(), df["centroid_y"].to_numpy()
    occ = df["occ_class"].fill_null("Unclassified").to_numpy().astype(object)
    county = df["county"].fill_null("").to_numpy().astype(object)
    area = df["footprint_area"].to_numpy().astype(np.float64)
    stats: dict = {}

    h_src = df["height_m"].to_numpy().astype(np.float64)
    h_ok = np.isfinite(h_src) & (h_src > 0) & (h_src < MAX_PLAUSIBLE_HEIGHT_M)
    height = np.where(h_ok, h_src, np.nan)
    need = ~h_ok
    if need.any():
        height[need] = neighbour_median(cx, cy, h_src, h_ok, need)
    # A measured height is published exactly as the source states it, however small: 48 rows are
    # under 2 m and 1 is 0.4 m, and rounding those up would make HEIGHT_REAL a lie.  Only an
    # inferred height gets a floor, because a neighbour median can come back empty.
    inferred = np.where(np.isfinite(height), height, MIN_INFERRED_HEIGHT_M)
    inferred = np.maximum(inferred, MIN_INFERRED_HEIGHT_M)
    source_height = np.where(h_ok, h_src, inferred)
    stats["height_source_lidar"] = int(h_ok.sum())
    stats["height_neighbour_median"] = int(need.sum())
    stats["source_height_pct_real"] = round(100.0 * float(h_ok.sum()) / max(n, 1), 3)
    stats["source_height_max_m"] = float(source_height.max())
    stats["source_height_median_m"] = float(np.median(source_height))

    fh = np.array([_OCC_FLOORS.get(str(o), _OCC_FLOORS_DEFAULT)[0] for o in occ])
    gfh_rule = np.array([_OCC_FLOORS.get(str(o), _OCC_FLOORS_DEFAULT)[1] for o in occ])

    # ---- the OpenStreetMap height join (deviation B11a) ----------------------------------------
    osm_row = np.full(n, -1, dtype=np.int64)
    osm_iou = np.zeros(n)
    osm_id = np.zeros(n, dtype=np.int64)
    tag_h = np.full(n, np.nan)
    tag_l = np.zeros(n, dtype=np.int16)
    if use_osm and geoms is not None:
        odf, ogeom = osmh.load_osm_buildings(osm_path)
        o_height = odf["height"].to_numpy().astype(np.float64)
        o_levels = odf["levels"].to_numpy().astype(np.float64)
        o_id = odf["osm_id"].to_numpy().astype(np.int64)
        o_min_h = odf["min_height"].to_numpy().astype(np.float64)
        osm_row, osm_iou, match_stats = osmh.match_footprints(geoms, ogeom)
        height, mode, join_stats = osmh.resolve_heights(source_height, h_ok, osm_row,
                                                        o_height, o_levels, fh, gfh_rule,
                                                        osm_min_height=o_min_h)
        m = osm_row >= 0
        osm_id[m] = o_id[osm_row[m]]
        tag_h[m] = o_height[osm_row[m]]
        lv = np.where(np.isfinite(o_levels), np.clip(o_levels, 0, 32767), 0).astype(np.int16)
        tag_l[m] = lv[osm_row[m]]
        stats["osm_join"] = {"source": str(osmh.OSM_BUILDINGS_NJ), "license": osmh.OSM_LICENSE,
                             "match": match_stats, "heights": join_stats,
                             "storey_height_check": osmh.storey_height_check(o_height, o_levels, osm_row, occ),
                             "tall_tags_the_join_could_not_use":
                                 osmh.unjoined_tall_tags(geoms, ogeom, odf, osm_row),
                             "tags_in_the_extract": _osm_tag_reach(o_height, o_levels, osm_row, geoms, ogeom)}
        log.info("OpenStreetMap height join: %d of %d footprints matched (%.2f %%); "
                 "%d heights from a tag, %d derived from levels",
                 match_stats["matched"], n, match_stats["match_rate_pct"],
                 join_stats["height_from_osm_tag"], join_stats["height_from_osm_levels"])
    else:
        height = source_height.copy()
        mode = np.full(n, osmh.MODE_SOURCE, dtype=np.int8)
        stats["osm_join"] = {"applied": False}

    # Everything below is derived from the height that is actually *published*, not from the float64
    # working value: the column is float32, and rounding it afterwards left 185 buildings whose
    # published floor count could not be recomputed from their published height.
    height = np.asarray(height, dtype=np.float32).astype(np.float64)

    height_source, h_real = osmh.height_sources(mode, h_ok)
    stats["height_source_osm_tag"] = int((height_source == S.SRC_OSM_HEIGHT).sum())
    stats["height_source_osm_levels"] = int((height_source == S.SRC_OSM_LEVELS).sum())
    stats["height_pct_real"] = round(100.0 * float(h_real.sum()) / max(n, 1), 3)
    stats["height_max_m"] = float(height.max())
    stats["height_median_m"] = float(np.median(height))

    floors = np.where(height <= gfh_rule + 0.5 * fh, 1, 1 + np.rint((height - gfh_rule) / fh))
    floors = np.clip(floors, 1, 200).astype(np.int16)
    fl = floors.astype(np.float64)
    gfh = np.where(fl <= 1, height, np.clip(gfh_rule, 2.2, np.maximum(height - (fl - 1) * 2.2, 2.2)))
    floor_height = np.where(fl > 1, (height - gfh) / np.maximum(fl - 1, 1), fh)
    stats["floors_median"] = float(np.median(floors))
    stats["floors_max"] = int(floors.max())

    material = _material_from_occupancy(occ, county, height, area)
    stats["material_histogram"] = {int(k): int(v) for k, v in zip(*np.unique(material, return_counts=True))}

    fid = np.full(n, S.Fidelity.FOOTPRINT_REAL.mask, dtype=np.uint16)
    fid |= np.where(h_real, S.Fidelity.HEIGHT_REAL.mask, S.Fidelity.HEIGHT_INFERRED.mask).astype(np.uint16)
    fid |= np.uint16(S.Fidelity.FLOORS_INFERRED.mask)      # no floor count in the source, ever
    fid |= np.uint16(S.Fidelity.FACADE_INFERRED.mask)      # no material in the source, ever (ADR-004)
    stats["fidelity_histogram"] = {int(k): int(v) for k, v in zip(*np.unique(fid, return_counts=True))}

    out = df.with_columns([
        pl.Series("ground_z", ground.astype(np.float32)),
        pl.Series("height", height.astype(np.float32)),
        pl.Series("roof_z", (ground + height).astype(np.float32)),
        pl.Series("floors", floors),
        pl.Series("floor_height", floor_height.astype(np.float32)),
        pl.Series("ground_floor_height", gfh.astype(np.float32)),
        pl.Series("material_primary", material),
        pl.Series("height_source", height_source),
        pl.Series("floors_source", np.full(n, S.SRC_HEIGHT_TO_FLOORS, dtype=np.int8)),
        pl.Series("ground_source", np.full(n, S.SRC_TERRAIN, dtype=np.int8)),
        pl.Series("fidelity", fid),
        pl.Series("osm_id", osm_id),
        pl.Series("osm_match_iou", osm_iou.astype(np.float32)),
        pl.Series("osm_height_m", tag_h.astype(np.float32)),
        pl.Series("osm_levels", tag_l),
        pl.Series("source_height_m", source_height.astype(np.float64)),
    ])
    return out, stats


def assemble_table(df: pl.DataFrame, geoms: np.ndarray, heading: np.ndarray, method: np.ndarray) -> tuple[pa.Table, np.ndarray]:
    """Sort by (tile, build_id, part) and build the Arrow table in schema order."""
    df = df.with_columns([pl.Series("primary_facade_heading", heading),
                          pl.Series("facade_heading_method", method)])
    order = df.with_row_index("_i").sort(["tile", "build_id", "part_index"])["_i"].to_numpy()
    a = df[order]
    g = geoms[order]
    n = a.height
    build_id = a["build_id"].to_numpy().astype(np.int64)
    const = {
        "bin": pa.array(build_id, pa.int64()),
        "bbl": pa.array(np.zeros(n, np.int64), pa.int64()),
        "borough": pa.array(np.full(n, BOROUGH_NJ, np.int8), pa.int8()),
        "footprint": pa.array(shapely.to_wkb(g), pa.binary()),
        "roof_type": pa.array(np.full(n, ROOF_TYPE_FLAT, np.int8), pa.int8()),
        "year_built": pa.array(np.zeros(n, np.int16), pa.int16()),
        "bldg_class": pa.array([""] * n, pa.string()),
        "land_use": pa.array(np.zeros(n, np.int8), pa.int8()),
        "has_storefront": pa.array(np.zeros(n, bool), pa.bool_()),
        "has_scaffold": pa.array(np.zeros(n, bool), pa.bool_()),
        "landmark_id": pa.array([""] * n, pa.string()),
        "name": pa.array([""] * n, pa.string()),
        "lit_seed": pa.array(S.lit_seed(build_id, build_id), pa.uint32()),
    }
    rename = {"src_source": "source"}
    cols: dict[str, pa.Array] = {}
    for name, typ, _ in COLUMNS:
        if name in const:
            cols[name] = const[name]
            continue
        src = rename.get(name, name)
        arr = a[src].to_arrow()
        if arr.null_count:
            if pa.types.is_string(typ):
                arr = a[src].fill_null("").to_arrow()
            else:
                raise ValueError(f"column {name} has {arr.null_count} nulls")
        cols[name] = arr.cast(typ)
    schema = arrow_schema(shapely.total_bounds(g), {"nycsim.stage": "buildings_nj", "nycsim.rows": str(n)})
    return pa.Table.from_arrays([cols[f.name] for f in schema], schema=schema), g


def write_tiles(table: pa.Table, geoms: np.ndarray, tiles_root: Path) -> dict:
    """One ``buildings_nj.parquet`` per tile, beside (never merged into) the New York ``buildings.parquet``."""
    tiles = table["tile"].to_numpy()
    uniq, starts = np.unique(tiles, return_index=True)
    order = np.argsort(starts)
    uniq, starts = uniq[order], starts[order]
    ends = np.append(starts[1:], len(tiles))
    base_meta = dict(table.schema.metadata)
    files: dict[str, dict] = {}
    for t, s, e in zip(uniq, starts, ends):
        sl = table.slice(int(s), int(e - s))
        meta = dict(base_meta)
        meta[b"geo"] = json.dumps(S.geo_metadata(shapely.total_bounds(geoms[s:e]))).encode()
        meta[b"nycsim.rows"] = str(sl.num_rows).encode()
        meta[b"nycsim.tile"] = str(t).encode()
        sl = sl.replace_schema_metadata(meta)
        d = tiles_root / str(t)
        d.mkdir(parents=True, exist_ok=True)
        p = d / TILE_FILENAME
        pq.write_table(sl, p, compression="snappy")
        files[str(t)] = {"rows": int(sl.num_rows), "bytes": p.stat().st_size}
    # A re-run that drops rows must not leave the previous run's file behind claiming buildings that
    # are no longer published (the Liberty Island clip empties a tile outright).
    stale = [q for q in tiles_root.glob(f"*/{TILE_FILENAME}") if q.parent.name not in files]
    for q in stale:
        log.info("removing %s: this run publishes no buildings for that tile", q)
        q.unlink()
    return files


# ---- height investigation ---------------------------------------------------------------------------------------
REFERENCE_HEIGHTS = Path(__file__).with_name("nj_reference_heights.json")
REFERENCE_MATCH_RADIUS_M = 45.0


def published_height_report(df: pl.DataFrame, geoms: np.ndarray,
                            reference: Path | None = None) -> dict:
    """Compare the published height against published architectural heights, tower by tower.

    ``nj_reference_heights.json`` carries the 63 tallest buildings of Jersey City with the
    coordinates and heights the Council on Tall Buildings publishes, retrieved once and recorded
    with its source.  For each of them the tallest USA Structures footprint within
    ``REFERENCE_MATCH_RADIUS_M`` of the published point is taken, and the two heights are compared.

    This is the acceptance test for deviation B11a, so it is **paired**: the footprint is chosen
    once, by the rule the source-only report used — the tallest polygon within the radius that
    carries a source height — and both the source height and the published height are then read off
    that same polygon.  A rule that changed the polygon between the two runs could show an
    improvement that is only a different choice of building.  ``reselected_by_published_height``
    repeats the "after" figures with the polygon re-chosen by the published height, because that is
    what a consumer reading the table actually sees.

    The split that matters is the source's own ``image_date``: a tower finished after the imagery
    was flown cannot be in it at all, and is a *coverage* gap, not a measurement error.  A tower
    that already stood is a measurement error, and those are reported separately.
    """
    ref_path = reference or REFERENCE_HEIGHTS
    if not ref_path.exists():
        return {"available": False, "reason": f"{ref_path} not present"}
    from ..crs import lonlat_to_tm

    doc = json.loads(ref_path.read_text())
    cx, cy = df["centroid_x"].to_numpy(), df["centroid_y"].to_numpy()
    src_h = df["height_m"].to_numpy().astype(np.float64)          # the raw USA Structures column
    area = df["footprint_area"].to_numpy().astype(np.float64)
    img = df["image_date"].fill_null("").to_numpy().astype(object)
    pub_h = df["height"].to_numpy().astype(np.float64) if "height" in df.columns else src_h
    h_src_code = df["height_source"].to_numpy() if "height_source" in df.columns else np.zeros(df.height, np.int8)
    osm_h = df["osm_height_m"].to_numpy().astype(np.float64) if "osm_height_m" in df.columns else np.full(df.height, np.nan)
    osm_l = df["osm_levels"].to_numpy() if "osm_levels" in df.columns else np.zeros(df.height, np.int16)
    tree = shapely.STRtree(shapely.points(cx, cy))
    rows = []
    for b in doc["buildings"]:
        x, y = lonlat_to_tm(b["lon"], b["lat"])
        hit = tree.query(shapely.buffer(shapely.points(x, y), REFERENCE_MATCH_RADIUS_M),
                         predicate="contains")
        rec = {"rank": b["rank"], "name": b["name"], "published_height_m": b["height_m"],
               "published_floors": b["floors"], "completed": b["year"],
               "candidates_within_45m": int(len(hit))}
        if len(hit) == 0:
            rec["matched"] = False
            rows.append(rec)
            continue
        with_h = hit[np.isfinite(src_h[hit])]
        j = int(with_h[np.argmax(src_h[with_h])]) if len(with_h) else int(hit[np.argmax(area[hit])])
        rec.update({"matched": True, "build_id": int(df["build_id"][j]),
                    "source_height_m": None if not np.isfinite(src_h[j]) else round(float(src_h[j]), 2),
                    "published_table_height_m": round(float(pub_h[j]), 2),
                    "height_source": int(h_src_code[j]),
                    "osm_height_tag_m": None if not np.isfinite(osm_h[j]) else round(float(osm_h[j]), 2),
                    "osm_levels_tag": int(osm_l[j]) or None,
                    "source_area_m2": round(float(area[j]), 1),
                    "source_image_date": str(img[j])})
        if np.isfinite(src_h[j]):
            rec["error_m"] = round(float(src_h[j]) - b["height_m"], 2)
            rec["error_pct"] = round(100.0 * (float(src_h[j]) - b["height_m"]) / b["height_m"], 1)
            rec["error_after_m"] = round(float(pub_h[j]) - b["height_m"], 2)
            rec["error_after_pct"] = round(100.0 * (float(pub_h[j]) - b["height_m"]) / b["height_m"], 1)
        # what a consumer sees: the tallest published footprint near the point, whichever it is
        k = int(hit[np.argmax(pub_h[hit])])
        rec["reselected_height_m"] = round(float(pub_h[k]), 2)
        rec["reselected_error_m"] = round(float(pub_h[k]) - b["height_m"], 2)
        rec["reselected_error_pct"] = round(100.0 * (float(pub_h[k]) - b["height_m"]) / b["height_m"], 1)
        rows.append(rec)

    def _stats(sub: list[dict], key_m: str = "error_m", key_pct: str = "error_pct") -> dict:
        e = np.array([r[key_m] for r in sub if key_m in r])
        p = np.array([r[key_pct] for r in sub if key_pct in r])
        if not len(e):
            return {"n": len(sub), "with_a_source_height": 0}
        return {"n": len(sub), "with_a_source_height": int(len(e)),
                "median_error_m": round(float(np.median(e)), 2),
                "median_error_pct": round(float(np.median(p)), 1),
                "worst_error_m": round(float(e.min()), 2),
                "n_short_by_over_20m": int((e < -20).sum()),
                "n_within_10_pct": int((np.abs(p) <= 10).sum())}

    imagery_year = 2013     # the Hudson County imagery date the source stamps on these rows
    stood = [r for r in rows if r["completed"] <= imagery_year]
    later = [r for r in rows if r["completed"] > imagery_year]
    paired = [r for r in rows if "error_m" in r]
    improved = [r for r in paired if abs(r["error_after_m"]) < abs(r["error_m"]) - 1e-9]
    worsened = [r for r in paired if abs(r["error_after_m"]) > abs(r["error_m"]) + 1e-9]
    return {
        "available": True,
        "reference": {"source": doc["source"], "url": doc["source_url"], "retrieved": doc["retrieved"],
                      "buildings": len(doc["buildings"])},
        "match_radius_m": REFERENCE_MATCH_RADIUS_M,
        "paired_on_the_same_footprints": True,
        "before_source_height": {
            "already_built_when_the_imagery_was_flown": _stats(stood),
            "built_after_the_imagery_was_flown": _stats(later),
            "all_towers_with_a_source_height": _stats(paired),
        },
        "after_osm_join": {
            "already_built_when_the_imagery_was_flown": _stats(stood, "error_after_m", "error_after_pct"),
            "built_after_the_imagery_was_flown": _stats(later, "error_after_m", "error_after_pct"),
            "all_towers_with_a_source_height": _stats(paired, "error_after_m", "error_after_pct"),
        },
        "reselected_by_published_height": {
            "already_built_when_the_imagery_was_flown": _stats(stood, "reselected_error_m", "reselected_error_pct"),
            "built_after_the_imagery_was_flown": _stats(later, "reselected_error_m", "reselected_error_pct"),
        },
        "towers_improved": len(improved),
        "towers_unchanged": len(paired) - len(improved) - len(worsened),
        "towers_made_worse": len(worsened),
        "made_worse": [{"name": r["name"], "published_height_m": r["published_height_m"],
                        "before_m": r["source_height_m"], "after_m": r["published_table_height_m"],
                        "height_source": r["height_source"]} for r in worsened],
        "towers": rows,
    }


def height_report(df: pl.DataFrame, geoms: np.ndarray, osm_path: Path | None = None) -> dict:
    """Measure the height error against OpenStreetMap's tagged heights, before and after the join.

    Before the join OpenStreetMap was an **instrument** here and nothing it said reached the table;
    that is no longer true (deviation B11a), so this report is careful about which half of it is
    still independent:

    * ``source`` — the USA Structures column against the tags.  Unchanged, and still the diagnosis:
      the source runs 4.7 % short below 20 m and 37.5 % short above 80 m.
    * ``published_where_the_tag_was_not_used`` — the shipped height against the tags on the rows
      whose height did **not** come from a tag (no accepted footprint match, or the levels rule).
      This is the part that is still an independent check, and it is the one that matters: it says
      what is left of the error after the join, on the buildings the join could not reach.

    The pairing here is looser than the acceptance test's: a New Jersey centroid inside the
    OpenStreetMap outline, largest footprint wins.  It is a population-level cross-check, not the
    one-to-one match the join itself requires.
    """
    osm_path = osm_path or (PROCESSED / "osm" / "buildings_nj.parquet")
    if not osm_path.exists():
        return {"available": False, "reason": f"{osm_path} not present"}
    osm = pl.read_parquet(osm_path, columns=["osm_id", "name", "height", "levels", "geometry"])
    osm = osm.filter(pl.col("height").is_not_null() & (pl.col("height") > 0))
    og = shapely.from_wkb(osm["geometry"].to_numpy())
    cx, cy = df["centroid_x"].to_numpy(), df["centroid_y"].to_numpy()
    area = df["footprint_area"].to_numpy()
    h = df["height_m"].to_numpy().astype(np.float64)
    pub = df["height"].to_numpy().astype(np.float64) if "height" in df.columns else h
    hs = df["height_source"].to_numpy() if "height_source" in df.columns else np.zeros(df.height, np.int8)
    names = osm["name"].fill_null("").to_list()
    oh = osm["height"].to_numpy().astype(np.float64)
    tree = shapely.STRtree(shapely.points(cx, cy))
    pairs = []
    for i, g in enumerate(og):
        hit = tree.query(g, predicate="contains")
        if len(hit) == 0:
            continue
        j = int(hit[np.argmax(area[hit])])          # the main structure inside the OSM outline
        if not np.isfinite(h[j]):
            continue
        pairs.append({"name": names[i], "osm_height_m": float(oh[i]), "usa_height_m": float(h[j]),
                      "published_height_m": float(pub[j]), "height_source": int(hs[j]),
                      "err_m": float(h[j] - oh[i]), "err_pct": float(100.0 * (h[j] - oh[i]) / oh[i]),
                      "err_after_m": float(pub[j] - oh[i]),
                      "err_after_pct": float(100.0 * (pub[j] - oh[i]) / oh[i]),
                      "usa_area_m2": float(area[j])})
    if not pairs:
        return {"available": True, "matched": 0}
    p = pl.DataFrame(pairs)

    def _bands(frame: pl.DataFrame, col_m: str, col_pct: str) -> dict:
        bands = {}
        for lo, hi in ((0, 20), (20, 40), (40, 80), (80, 400)):
            sub = frame.filter((pl.col("osm_height_m") >= lo) & (pl.col("osm_height_m") < hi))
            if sub.height:
                bands[f"{lo}-{hi}m"] = {"n": sub.height,
                                        "median_err_m": round(float(sub[col_m].median()), 2),
                                        "median_err_pct": round(float(sub[col_pct].median()), 1)}
        return bands

    independent = p.filter(pl.col("height_source") != S.SRC_OSM_HEIGHT)
    return {"available": True, "matched": p.height,
            "source": "data/processed/osm/buildings_nj.parquet (ODbL, OpenStreetMap contributors)",
            "note": ("the tags are an input to the published height since deviation B11a was closed; "
                     "only the rows whose height did not come from a tag are an independent check"),
            "source_by_reference_height_band": _bands(p, "err_m", "err_pct"),
            "published_where_the_tag_was_used": int(p.height - independent.height),
            "published_where_the_tag_was_not_used": {
                "n": independent.height,
                "source_by_band": _bands(independent, "err_m", "err_pct"),
                "published_by_band": _bands(independent, "err_after_m", "err_after_pct")},
            "worst_20": p.sort("err_after_m").head(20).to_dicts()}


# ---- shell meshes ---------------------------------------------------------------------------------------------------
SHELL_MANIFEST = "manifest_nj.json"
SHELL_GLB = "tile_buildings_nj.glb"


def shells_index(blender_tiles: Path, out_dir: Path, *, record: bool = True) -> dict:
    """Aggregate the per-tile ``manifest_nj.json`` files written by ``build_tile.py --source nj``.

    The shell meshes live under ``blender_out/`` (git-ignored, like every other generated mesh), so
    this index is what makes them auditable: one row per tile with the glb's size, SHA-256, triangle
    counts per LOD and building count, registered in ``data/manifest/processed.json`` like every
    other artefact.
    """
    mans = sorted(Path(blender_tiles).glob(f"*/{SHELL_MANIFEST}"))
    tiles: dict[str, dict] = {}
    tot = {"tiles": 0, "buildings": 0, "bytes": 0, "lod0": 0, "lod1": 0, "lod2": 0,
           "open_shells_lod0": 0, "dropped_empty_footprint": 0, "seconds": 0.0}
    for m in mans:
        doc = json.loads(m.read_text())
        glb = m.parent / SHELL_GLB
        if not glb.exists():
            continue
        tile = doc["tile"]
        tiles[tile] = {"buildings": doc["buildings"]["solids"], "bytes": doc["glb"]["bytes"],
                       "sha256": doc["glb"]["sha256"],
                       "triangles": {k: int(v) for k, v in doc["triangles"].items()},
                       "bounds_world_m": doc["bounds_world_m"], "seconds": doc["seconds"]["total"]}
        tot["tiles"] += 1
        tot["buildings"] += doc["buildings"]["solids"]
        tot["bytes"] += doc["glb"]["bytes"]
        for k in ("lod0", "lod1", "lod2"):
            tot[k] += int(doc["triangles"].get(k, 0))
        tot["open_shells_lod0"] += doc["buildings"].get("open_shells_lod0", 0)
        tot["dropped_empty_footprint"] += doc["buildings"].get("dropped_empty_footprint", 0)
        tot["seconds"] += doc["seconds"]["total"]
    doc = {"schema_version": SCHEMA_VERSION, "stage": "buildings_nj_mesh", "glb": SHELL_GLB,
           "generated_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "totals": {**tot, "seconds": round(tot["seconds"], 1),
                      "bytes_per_building": round(tot["bytes"] / max(tot["buildings"], 1), 1)},
           "tiles": tiles}
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "shells_index.json"
    with open(path, "w") as f:
        json.dump(doc, f, indent=1, sort_keys=True)
    if record:
        manifest.record_processed("buildings_nj_shells", path, stage="buildings_nj_mesh", sources=[SOURCE_ID],
                                  rows=tot["buildings"], schema="buildings_nj_shells/1",
                                  extra={"license": LICENSE, "n_tiles": tot["tiles"],
                                         "glb_bytes_total": tot["bytes"], "glb": SHELL_GLB,
                                         "glb_root": "blender_out/tiles/{tile}/" + SHELL_GLB})
    return doc


def summary(table: pa.Table, source_stats: dict, ground_stats: dict, attr_stats: dict) -> dict:
    df = pl.from_arrow(table.select(["borough", "height", "ground_z", "roof_z", "floors", "fidelity",
                                     "county", "city", "occ_class", "tile", "height_source"]))
    fid = df["fidelity"].to_numpy()
    hsrc = df["height_source"].to_numpy()
    n = df.height
    pct = lambda x: round(100.0 * float(x) / max(n, 1), 3)  # noqa: E731
    by_county = {r["county"]: r["len"] for r in df.group_by("county").len().sort("len", descending=True).to_dicts()}
    top_cities = {r["city"]: r["len"] for r in
                  df.group_by("city").len().sort("len", descending=True).head(10).to_dicts()}
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "buildings": n,
        "tiles": int(df["tile"].n_unique()),
        "borough_code": BOROUGH_NJ,
        "height_median_m": round(float(df["height"].median()), 2),
        "height_p90_m": round(float(df["height"].quantile(0.9)), 2),
        "height_max_m": round(float(df["height"].max()), 2),
        "ground_z_min_m": round(float(df["ground_z"].min()), 2),
        "ground_z_max_m": round(float(df["ground_z"].max()), 2),
        "roof_z_max_m": round(float(df["roof_z"].max()), 2),
        "floors_median": float(df["floors"].median()),
        "pct_footprint_real": pct(int(((fid >> int(S.Fidelity.FOOTPRINT_REAL)) & 1).sum())),
        "pct_height_real": pct(int(((fid >> int(S.Fidelity.HEIGHT_REAL)) & 1).sum())),
        "pct_height_inferred": pct(int(((fid >> int(S.Fidelity.HEIGHT_INFERRED)) & 1).sum())),
        "height_by_source": {name: int((hsrc == code).sum()) for name, code in
                             (("usa_structures_lidar", S.SRC_LIDAR), ("neighbour_median", S.SRC_NEIGHBOURS),
                              ("osm_height_tag", S.SRC_OSM_HEIGHT), ("osm_levels_derived", S.SRC_OSM_LEVELS))},
        "n_roof_real": int(((fid >> int(S.Fidelity.ROOF_REAL)) & 1).sum()),
        "n_floors_real": int(((fid >> int(S.Fidelity.FLOORS_REAL)) & 1).sum()),
        "n_year_real": int(((fid >> int(S.Fidelity.YEAR_REAL)) & 1).sum()),
        "n_ground_real": int(((fid >> int(S.Fidelity.GROUND_REAL)) & 1).sum()),
        "by_county": by_county,
        "top_cities": top_cities,
        "source": source_stats,
        "ground": ground_stats,
        "attributes": attr_stats,
    }


# ---- driver -------------------------------------------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out-dir", type=Path, default=None, help="summary directory (default data/processed/buildings_nj)")
    ap.add_argument("--tiles-root", type=Path, default=None, help="tile root (default data/processed/tiles)")
    ap.add_argument("--limit", type=int, default=None, help="first N source rows (development subset, never recorded)")
    ap.add_argument("--no-tiles", action="store_true", help="compute everything but write no per-tile files")
    ap.add_argument("--no-manifest", action="store_true", help="skip the manifest write")
    ap.add_argument("--no-osm", action="store_true",
                    help="skip the OpenStreetMap height join (deviation B11a) and publish the "
                         "USA Structures height on every row, as this stage did before it was closed")
    ap.add_argument("--shells-index", action="store_true",
                    help="only aggregate and register the shell meshes built by "
                         "blender/buildings/build_tile.py --source nj, then exit")
    ap.add_argument("--blender-tiles", type=Path, default=None,
                    help="shell mesh root (default blender_out/tiles)")
    ap.add_argument("-v", "--verbose", action="store_true")
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if a.verbose else logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    subset = a.limit is not None
    out_dir = a.out_dir or (PROCESSED / "buildings_nj")
    tiles_root = a.tiles_root or (PROCESSED / "tiles")
    out_dir.mkdir(parents=True, exist_ok=True)
    t0 = time.perf_counter()

    if a.shells_index:
        from ..paths import BLENDER_OUT

        doc = shells_index(a.blender_tiles or (BLENDER_OUT / "tiles"), out_dir, record=not a.no_manifest)
        print(json.dumps(doc["totals"], indent=1))
        return 0

    df, geoms, src_stats = load_source(limit=a.limit)
    ground, ground_stats = sample_ground(geoms, df["centroid_x"].to_numpy(), df["centroid_y"].to_numpy())
    df, attr_stats = resolve_attributes(df, ground, geoms, use_osm=not a.no_osm)

    from .facade_heading import facade_headings
    nan = np.full(df.height, np.nan)
    heading, method, heading_stats = facade_headings(
        geoms, df["centroid_x"].to_numpy(), df["centroid_y"].to_numpy(), nan, nan, shapely.STRtree(geoms))
    attr_stats["facade_heading"] = heading_stats

    table, geoms_sorted = assemble_table(df, geoms, heading, method)
    base_path = out_dir / "buildings_nj_base.parquet"
    pq.write_table(table, base_path, compression="snappy", row_group_size=131072)

    tile_files: dict = {}
    if not a.no_tiles:
        tile_files = write_tiles(table, geoms_sorted, tiles_root)

    doc = summary(table, src_stats, ground_stats, attr_stats)
    doc["height_investigation"] = {
        "against_openstreetmap_height_tags": height_report(df, geoms),
        "against_published_tower_heights": published_height_report(df, geoms),
    }
    doc["tiles_written"] = len(tile_files)
    doc["seconds"] = round(time.perf_counter() - t0, 2)
    with open(out_dir / "buildings_nj_summary.json", "w") as f:
        json.dump(doc, f, indent=1, sort_keys=True, default=str)

    if not subset and not a.no_manifest:
        manifest.record_processed("buildings_nj_base", base_path, stage="buildings_nj", sources=[SOURCE_ID, OSM_SOURCE_ID],
                                  rows=table.num_rows, schema=SCHEMA_ID,
                                  extra={"license": LICENSE, "license_osm": OSM_LICENSE,
                                         "columns": [c for c, _, _ in COLUMNS], "borough_code": BOROUGH_NJ})
        manifest.record_processed("buildings_nj_summary", out_dir / "buildings_nj_summary.json",
                                  stage="buildings_nj", sources=[SOURCE_ID, OSM_SOURCE_ID],
                                  schema="buildings_nj_summary/2",
                                  extra={"license": LICENSE, "license_osm": OSM_LICENSE})
        if tile_files:
            for t, v in tile_files.items():
                v["sha256"] = manifest.sha256_of(tiles_root / t / TILE_FILENAME)
            index_path = out_dir / "tiles_index.json"
            with open(index_path, "w") as f:
                json.dump({"schema_version": SCHEMA_VERSION, "filename": TILE_FILENAME, "tiles": tile_files}, f,
                          indent=1, sort_keys=True)
            manifest.record_processed("buildings_nj_tiles", index_path, stage="buildings_nj", sources=[SOURCE_ID, OSM_SOURCE_ID],
                                      rows=int(sum(v["rows"] for v in tile_files.values())), schema=SCHEMA_ID,
                                      extra={"license": LICENSE, "license_osm": OSM_LICENSE,
                                             "n_tiles": len(tile_files), "tile_filename": TILE_FILENAME})

    print(json.dumps({k: doc[k] for k in ("buildings", "tiles", "height_median_m", "height_max_m",
                                          "pct_height_real", "pct_height_inferred", "height_by_source",
                                          "n_roof_real", "n_floors_real", "n_ground_real", "seconds")}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
