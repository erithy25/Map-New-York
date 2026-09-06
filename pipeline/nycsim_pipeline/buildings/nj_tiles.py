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
* **Height** — 73.7 % of rows carry a LiDAR-derived ``height_m`` from the source; those get
  ``HEIGHT_REAL``.  The rest get the median of the ten nearest rows that do have one and
  ``HEIGHT_INFERRED``.  The source height is measured but it is **not** New York City quality: see
  ``docs/verification/buildings_nj/`` and :func:`height_report` — the source truncates tall
  buildings badly and its imagery predates the towers built after 2013.
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
from ..paths import PROCESSED
from ..terrain.segment_z import ZSampler
from ..tiling import tile_index_arrays
from . import schema as S
from .footprints import MIN_PART_AREA_M2, _polygonal_parts
from .infer import neighbour_median

log = logging.getLogger("nycsim.buildings.nj")

SOURCE_PARQUET = PROCESSED / "nj" / "buildings_nj_usa_structures.parquet"
SOURCE_ID = "usa_structures_nj_hudson"
SCHEMA_ID = "buildings_nj/1"
SCHEMA_VERSION = 1
TILE_FILENAME = "buildings_nj.parquet"
BOROUGH_NJ = 6              # DATA_CONTRACTS §2: 1 MN 2 BX 3 BK 4 QN 5 SI 6 NJ 0 water
LICENSE = "Public domain (US Government work: FEMA / ORNL USA Structures)"

MIN_HEIGHT_M = 2.0
MAX_PLAUSIBLE_HEIGHT_M = 600.0
GROUND_SAMPLE_MAX_VERTICES = 64     # outline samples per footprint before the ring is decimated
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
    ("osm_id", pa.int64(), True),              # not matched by this stage: 0
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
        b"nycsim.source": SOURCE_ID.encode(),
        b"nycsim.borough": str(BOROUGH_NJ).encode(),
    }
    if extra_meta:
        meta.update({k.encode(): v.encode() for k, v in extra_meta.items()})
    return pa.schema(fields, metadata=meta)


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
def resolve_attributes(df: pl.DataFrame, ground: np.ndarray) -> tuple[pl.DataFrame, dict]:
    """Height, floors, storey heights, material and the fidelity bitfield."""
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
    height = np.where(np.isfinite(height), height, MIN_HEIGHT_M)
    height = np.maximum(height, MIN_HEIGHT_M)
    height_source = np.where(h_ok, S.SRC_LIDAR, S.SRC_NEIGHBOURS).astype(np.int8)
    stats["height_source_lidar"] = int(h_ok.sum())
    stats["height_neighbour_median"] = int(need.sum())
    stats["height_pct_real"] = round(100.0 * float(h_ok.sum()) / max(n, 1), 3)
    stats["height_max_m"] = float(height.max())
    stats["height_median_m"] = float(np.median(height))

    fh = np.array([_OCC_FLOORS.get(str(o), _OCC_FLOORS_DEFAULT)[0] for o in occ])
    gfh_rule = np.array([_OCC_FLOORS.get(str(o), _OCC_FLOORS_DEFAULT)[1] for o in occ])
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
    fid |= np.where(h_ok, S.Fidelity.HEIGHT_REAL.mask, S.Fidelity.HEIGHT_INFERRED.mask).astype(np.uint16)
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
        "osm_id": pa.array(np.zeros(n, np.int64), pa.int64()),
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
    return files


# ---- height investigation ---------------------------------------------------------------------------------------
def height_report(df: pl.DataFrame, geoms: np.ndarray, osm_path: Path | None = None) -> dict:
    """Measure the source's height error against OpenStreetMap's tagged heights.

    OpenStreetMap is used here as an **instrument**, not as an input: nothing it says reaches the
    published table.  It is the only independent height source already ingested in this repository
    (``data/processed/osm/buildings_nj.parquet``, ODbL), and its ``height`` tags on the Hudson County
    towers come from published architectural figures.
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
                      "err_m": float(h[j] - oh[i]), "err_pct": float(100.0 * (h[j] - oh[i]) / oh[i]),
                      "usa_area_m2": float(area[j])})
    if not pairs:
        return {"available": True, "matched": 0}
    p = pl.DataFrame(pairs)
    bands = {}
    for lo, hi in ((0, 20), (20, 40), (40, 80), (80, 400)):
        s = p.filter((pl.col("osm_height_m") >= lo) & (pl.col("osm_height_m") < hi))
        if s.height:
            bands[f"{lo}-{hi}m"] = {"n": s.height,
                                    "median_err_m": round(float(s["err_m"].median()), 2),
                                    "median_err_pct": round(float(s["err_pct"].median()), 1)}
    return {"available": True, "matched": p.height,
            "source": "data/processed/osm/buildings_nj.parquet (ODbL, OpenStreetMap contributors)",
            "by_reference_height_band": bands,
            "worst_20": p.sort("err_m").head(20).to_dicts()}


def summary(table: pa.Table, source_stats: dict, ground_stats: dict, attr_stats: dict) -> dict:
    df = pl.from_arrow(table.select(["borough", "height", "ground_z", "roof_z", "floors", "fidelity",
                                     "county", "city", "occ_class", "tile", "height_source"]))
    fid = df["fidelity"].to_numpy()
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
    ap.add_argument("-v", "--verbose", action="store_true")
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if a.verbose else logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    subset = a.limit is not None
    out_dir = a.out_dir or (PROCESSED / "buildings_nj")
    tiles_root = a.tiles_root or (PROCESSED / "tiles")
    out_dir.mkdir(parents=True, exist_ok=True)
    t0 = time.perf_counter()

    df, geoms, src_stats = load_source(limit=a.limit)
    ground, ground_stats = sample_ground(geoms, df["centroid_x"].to_numpy(), df["centroid_y"].to_numpy())
    df, attr_stats = resolve_attributes(df, ground)

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
    doc["height_investigation"] = height_report(df, geoms)
    doc["tiles_written"] = len(tile_files)
    doc["seconds"] = round(time.perf_counter() - t0, 2)
    with open(out_dir / "buildings_nj_summary.json", "w") as f:
        json.dump(doc, f, indent=1, sort_keys=True, default=str)

    if not subset and not a.no_manifest:
        manifest.record_processed("buildings_nj_base", base_path, stage="buildings_nj", sources=[SOURCE_ID],
                                  rows=table.num_rows, schema=SCHEMA_ID,
                                  extra={"license": LICENSE, "columns": [c for c, _, _ in COLUMNS],
                                         "borough_code": BOROUGH_NJ})
        manifest.record_processed("buildings_nj_summary", out_dir / "buildings_nj_summary.json",
                                  stage="buildings_nj", sources=[SOURCE_ID], schema="buildings_nj_summary/1")
        if tile_files:
            for t, v in tile_files.items():
                v["sha256"] = manifest.sha256_of(tiles_root / t / TILE_FILENAME)
            index_path = out_dir / "tiles_index.json"
            with open(index_path, "w") as f:
                json.dump({"schema_version": 1, "filename": TILE_FILENAME, "tiles": tile_files}, f,
                          indent=1, sort_keys=True)
            manifest.record_processed("buildings_nj_tiles", index_path, stage="buildings_nj", sources=[SOURCE_ID],
                                      rows=int(sum(v["rows"] for v in tile_files.values())), schema=SCHEMA_ID,
                                      extra={"license": LICENSE, "n_tiles": len(tile_files),
                                             "tile_filename": TILE_FILENAME})

    print(json.dumps({k: doc[k] for k in ("buildings", "tiles", "height_median_m", "height_max_m",
                                          "pct_height_real", "pct_height_inferred", "n_roof_real",
                                          "n_floors_real", "n_ground_real", "seconds")}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
