"""Tile input loading and attribute resolution for the building-shell stage (no ``bpy``).

Reads ``data/processed/tiles/{tile}/buildings.parquet`` (DATA_CONTRACTS §5 + §5.2), resolves the
columns that later stages own but may not have written yet, and hands ``shellgeom`` a list of
``BuildingSpec``.  Every fallback is deterministic and its provenance is counted so the tile
manifest and the stage report can state exactly how much of the output is real.

Resolution chains
-----------------
``roof_type``   column in the tile file  →  ``buildings/roof_attrs.parquet`` (ADR-013, joined on
                ``bin``)  →  ``facade_class`` → ``facade_classes.json`` ``roof``  →  PLUTO
                ``bldg_class`` rule  →  flat.
``material``    ``material_primary`` column  →  ``facade_class`` → ``facade_classes.json``
                ``materials[0]``  →  PLUTO ``bldg_class`` × ``year_built`` × borough rule.
``facade_class`` column if present, else 0 ("unclassified": the engine falls back to the
                material-driven shader defaults).

The PLUTO-class rules below are the codification of NYC building typology used everywhere in this
project (ARCHITECTURE §4.5 / ADR-004).  They are inferred, never presented as measured; the
per-tile manifest counts how many buildings used each source.
"""
from __future__ import annotations

import json
import logging
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import shapely

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "blender" / "common"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import facade_params as fp  # noqa: E402  (blender/common, read-only foundation)
import shellgeom as sg  # noqa: E402

LOG = logging.getLogger("nycsim.buildings")

TILES_DIR = REPO_ROOT / "data" / "processed" / "tiles"
ROOF_ATTRS_PATH = REPO_ROOT / "data" / "processed" / "buildings" / "roof_attrs.parquet"
CITYGML_DIR = REPO_ROOT / "data" / "processed" / "buildings" / "citygml"

MAT = fp.MATERIAL_INDEX
MAT_ROOF_FLAT = MAT["roof_membrane"]
MAT_ROOF_TAR = MAT["tar_roof"]
MAT_ROOF_PITCHED = MAT["tar_roof"]          # asphalt shingle / rolled roofing on pitched stock
MAT_ROOF_METAL = MAT["corrugated_metal"]

# roof strings used by blender/common/facade_classes.json -> shellgeom roof kind
_FACADE_ROOF_KIND = {
    "flat_parapet": sg.ROOF_FLAT,
    "flat_cornice": sg.ROOF_FLAT,
    "flat_mechanical": sg.ROOF_FLAT,
    "flat_deck": sg.ROOF_FLAT,
    "setback_crown": sg.ROOF_FLAT,
    "pitched_low": sg.ROOF_GABLE,
    "pitched_steep": sg.ROOF_GABLE,
    "pitched_tile": sg.ROOF_HIP,
    "pitched_dormer": sg.ROOF_GABLE,
    "mansard": sg.ROOF_MANSARD,
}
_ROOF_NAME_KIND = {n: i for i, n in enumerate(sg.ROOF_NAMES)}

# feature codes of the OTI footprint dataset (DATA_CONTRACTS §5.2)
FC_GARAGE = 5110
FC_UNDER_CONSTRUCTION = 5100


@dataclass
class TileLoad:
    """Result of loading one tile."""

    tile: str
    x0: float
    y0: float
    specs: list[sg.BuildingSpec]
    rows_in: int
    dropped: int
    sources: dict[str, dict[str, int]]
    materials_used: dict[int, int]
    df_index: list[int]          # index into the source dataframe, parallel to ``specs``


# --------------------------------------------------------------------------- material rules
def _material_from_class(bldg_class: str, year: int, borough: int, floors: int, height: float) -> int:
    """PLUTO building class × era × borough → primary facade material (inferred, ADR-004)."""
    c = (bldg_class or "").upper()
    k = c[:1]
    y = int(year) if year and year > 1600 else 0
    if k == "O" or c[:2] in ("RB", "RC"):                       # office
        if y >= 1995:
            return MAT["glass_curtain"]
        if y >= 1958:
            return MAT["glass_curtain"] if floors >= 12 else MAT["brown_brick"]
        if y >= 1930:
            return MAT["limestone"]
        return MAT["terracotta"] if floors >= 8 else MAT["red_brick"]
    if k in ("D", "R"):                                          # elevator apartments / condo
        if y >= 2000:
            return MAT["glass_curtain"] if floors >= 15 else MAT["tan_brick"]
        if y >= 1975:
            return MAT["brown_brick"]
        if y >= 1950:
            return MAT["white_glazed_brick"]
        if y >= 1920:
            return MAT["red_brick"]
        return MAT["limestone"] if floors >= 10 else MAT["red_brick"]
    if k == "C":                                                 # walk-up apartments / tenements
        if c[:2] in ("C0", "C1", "C2", "C3", "C4", "C5", "C7") and y and y < 1901:
            return MAT["red_brick"]
        if y >= 1990:
            return MAT["tan_brick"]
        if y >= 1945:
            return MAT["red_brick"]
        return MAT["red_brick"]
    if k in ("A", "B"):                                          # one- and two-family houses
        if borough == 1:
            return MAT["brownstone"]
        if y >= 1945:
            return MAT["vinyl_siding"] if borough in (4, 5) else MAT["red_brick"]
        if y >= 1900:
            return MAT["red_brick"] if borough in (2, 3) else MAT["wood_clapboard"]
        return MAT["wood_clapboard"]
    if k == "S":                                                 # mixed residential / commercial
        return MAT["red_brick"]
    if k == "K":                                                 # store buildings / taxpayers
        return MAT["red_brick"] if (not y or y < 1970) else MAT["precast"]
    if k in ("E", "F"):                                          # warehouse / factory
        if y >= 1960:
            return MAT["concrete"] if height >= 8 else MAT["metal_panel"]
        return MAT["red_brick"]
    if k == "G":                                                 # garages / gas stations
        return MAT["concrete"]
    if k == "W":                                                 # educational
        return MAT["red_brick"] if (not y or y < 1950) else MAT["tan_brick"]
    if k == "M":                                                 # churches / synagogues
        return MAT["stone_rubble"]
    if k == "H":                                                 # hotels
        return MAT["glass_curtain"] if y >= 2000 else MAT["tan_brick"]
    if k == "I":                                                 # hospitals / health
        return MAT["glass_curtain"] if y >= 2000 else MAT["tan_brick"]
    if k in ("N", "P", "Q", "J"):                                # asylums, public assembly, outdoor rec, theatres
        return MAT["limestone"] if (y and y < 1940) else MAT["concrete"]
    if k in ("T", "U", "V", "Y", "Z"):                           # transport, utility, vacant, city, misc
        return MAT["concrete"]
    if k == "L":                                                 # lofts
        return MAT["red_brick"] if (not y or y < 1940) else MAT["concrete"]
    return MAT["red_brick"]


def _material_from_facade_class(classes_by_id: dict[int, dict[str, Any]], fc: int) -> int | None:
    rec = classes_by_id.get(int(fc))
    if not rec:
        return None
    mats = rec.get("materials") or []
    if not mats:
        return None
    return MAT.get(mats[0])


# --------------------------------------------------------------------------- roof rules
# ADR-013 §3: the roof-shape inference fires only for detached one/two-family stock.  Reproduced
# here verbatim so a tile still gets the right roofs before buildings/roof_attrs.parquet lands, and
# so the two stages cannot drift apart.
ADR013_CLASSES = tuple(f"A{d}" for d in range(10)) + ("B1", "B2", "B3", "B9", "R1", "R3")
ADR013_MAX_FRONTAGE_RATIO = 0.80
ADR013_MAX_SHORT_SIDE_M = 14.0
ADR013_MAX_FLOORS = 3
ADR013_MAX_AREA_M2 = 400.0
ADR013_PITCH_DEG = 30.0


def _roof_from_class(bldg_class: str, feature_code: int, floors: int, area: float,
                     short_side: float, bldg_frontage: float, lot_frontage: float) -> tuple[int, float]:
    """PLUTO class → roof kind when no roof source exists (ADR-013 §3/§4 reproduced).

    Only detached one/two-family stock with a side yard gets a pitch, and it is always a gable with
    the ridge on the long axis, because gable-vs-hip is not decidable from these attributes.
    """
    c = (bldg_class or "").upper()
    if feature_code == FC_GARAGE:
        return sg.ROOF_FLAT, 0.0
    if c[:1] == "M":                                    # houses of worship: pitched by typology
        return sg.ROOF_GABLE, sg.STEEP_SLOPE_DEG
    if c[:2] not in ADR013_CLASSES:
        return sg.ROOF_FLAT, 0.0
    if floors > ADR013_MAX_FLOORS or area > ADR013_MAX_AREA_M2 or short_side > ADR013_MAX_SHORT_SIDE_M:
        return sg.ROOF_FLAT, 0.0
    if not (math.isfinite(bldg_frontage) and math.isfinite(lot_frontage) and lot_frontage > 0.0):
        return sg.ROOF_FLAT, 0.0                        # no frontage evidence -> stay flat
    if bldg_frontage / lot_frontage >= ADR013_MAX_FRONTAGE_RATIO:
        return sg.ROOF_FLAT, 0.0                        # party walls: attached rowhouse, flat roof
    return sg.ROOF_GABLE, ADR013_PITCH_DEG


# --------------------------------------------------------------------------- roof_attrs side-load
_ROOF_ATTRS_CACHE: dict[str, pd.DataFrame | None] = {}


def load_roof_attrs(path: Path | str = ROOF_ATTRS_PATH) -> pd.DataFrame | None:
    """Load ``buildings/roof_attrs.parquet`` (ADR-013) once per process; ``None`` if absent."""
    key = str(path)
    if key in _ROOF_ATTRS_CACHE:
        return _ROOF_ATTRS_CACHE[key]
    p = Path(path)
    df = None
    if p.exists():
        try:
            import pyarrow.parquet as pq

            cols = set(pq.ParquetFile(p).schema_arrow.names)
            want = [c for c in ("bin", "roof_type", "roof_type_source", "roof_inferred",
                                "roof_eave_dz_m", "roof_ridge_dz_m", "roof_slope_deg",
                                "roof_pitch_deg", "roof_type_conf", "roof_mesh_ref") if c in cols]
            if "bin" in want and "roof_type" in want:
                df = pd.read_parquet(p, columns=want).drop_duplicates("bin").set_index("bin")
                LOG.info("roof_attrs: %d rows from %s", len(df), p)
        except Exception as exc:  # pragma: no cover - defensive, reported not swallowed
            LOG.warning("roof_attrs unreadable (%s): %s", p, exc)
            df = None
    _ROOF_ATTRS_CACHE[key] = df
    return df


_FACADE_CLASSES_BY_ID: dict[int, dict[str, Any]] | None = None


def facade_classes_by_id() -> dict[int, dict[str, Any]]:
    global _FACADE_CLASSES_BY_ID
    if _FACADE_CLASSES_BY_ID is None:
        _FACADE_CLASSES_BY_ID = {int(c["facade_class"]): c for c in fp.load_facade_classes()}
    return _FACADE_CLASSES_BY_ID


# --------------------------------------------------------------------------- tile loading
def tile_origin(tile: str) -> tuple[float, float]:
    tx, ty = tile[2:].split("_", 1) if tile.startswith("t_") else (0, 0)
    return float(int(tx)) * 1000.0, float(int(ty)) * 1000.0


def tile_path(tile: str) -> Path:
    return TILES_DIR / tile / "buildings.parquet"


def available_tiles() -> list[str]:
    return sorted(p.parent.name for p in TILES_DIR.glob("*/buildings.parquet"))


def load_tile(tile: str, *, roof_attrs: pd.DataFrame | None = None, ridge_mode: str = "clamp",
              min_height: float = 1.0) -> TileLoad:
    """Load one tile and resolve every geometry input.  ``ridge_mode``:

    ``clamp``   (default) the pitched ridge sits at ``roof_z`` and the eave below it, so the mesh
                spans exactly ``[ground_z, roof_z]`` and matches the ``height`` column.
    ``adr013``  honour ``roof_ridge_dz_m`` / ``roof_eave_dz_m`` from ``roof_attrs.parquet``: the
                ridge rises above the LiDAR plane, so the mesh is taller than ``height``.
    """
    path = tile_path(tile)
    if not path.exists():
        raise FileNotFoundError(path)
    df = pd.read_parquet(path)
    if len(df) == 0:
        x0, y0 = tile_origin(tile)
        return TileLoad(tile, x0, y0, specs=[], rows_in=0, dropped=0,
                        sources={"roof": {}, "material": {}}, materials_used={}, df_index=[])
    x0, y0 = tile_origin(tile)

    geoms = shapely.from_wkb(df["footprint"].to_numpy())
    cleaned = sg.clean_footprints(geoms)

    have = set(df.columns)
    classes = facade_classes_by_id()
    if roof_attrs is None:
        roof_attrs = load_roof_attrs()

    col_roof = df["roof_type"].to_numpy() if "roof_type" in have else None
    col_mat = df["material_primary"].to_numpy() if "material_primary" in have else None
    col_fc = df["facade_class"].to_numpy() if "facade_class" in have else None
    col_slope = df["roof_slope_deg"].to_numpy() if "roof_slope_deg" in have else None

    ra_type = ra_eave = ra_ridge = ra_slope = ra_src = None
    if roof_attrs is not None:
        idx = roof_attrs.reindex(df["bin"].to_numpy())
        ra_type = idx["roof_type"].to_numpy() if "roof_type" in roof_attrs.columns else None
        ra_eave = idx["roof_eave_dz_m"].to_numpy() if "roof_eave_dz_m" in roof_attrs.columns else None
        ra_ridge = idx["roof_ridge_dz_m"].to_numpy() if "roof_ridge_dz_m" in roof_attrs.columns else None
        ra_slope = (idx["roof_pitch_deg"].to_numpy() if "roof_pitch_deg" in roof_attrs.columns
                    else (idx["roof_slope_deg"].to_numpy() if "roof_slope_deg" in roof_attrs.columns else None))
        ra_src = idx["roof_type_source"].to_numpy() if "roof_type_source" in roof_attrs.columns else None

    bins = df["bin"].to_numpy()
    ground = df["ground_z"].to_numpy(dtype=np.float64)
    roofz = df["roof_z"].to_numpy(dtype=np.float64)
    floors = df["floors"].to_numpy(dtype=np.int32)
    fh = df["floor_height"].to_numpy(dtype=np.float64)
    gfh = df["ground_floor_height"].to_numpy(dtype=np.float64)
    year = df["year_built"].to_numpy(dtype=np.int32)
    cls = df["bldg_class"].to_numpy()
    boro = df["borough"].to_numpy(dtype=np.int32)
    store = df["has_storefront"].to_numpy()
    seed = df["lit_seed"].to_numpy(dtype=np.uint32)
    head = df["primary_facade_heading"].to_numpy(dtype=np.float64)
    fcode = df["feature_code"].to_numpy(dtype=np.int32) if "feature_code" in have else np.full(len(df), 2100)
    area_col = df["footprint_area"].to_numpy(dtype=np.float64) if "footprint_area" in have else None
    bfront = df["bldg_frontage"].to_numpy(dtype=np.float64) if "bldg_frontage" in have else None
    lfront = df["lot_frontage"].to_numpy(dtype=np.float64) if "lot_frontage" in have else None

    specs: list[sg.BuildingSpec] = []
    df_index: list[int] = []
    dropped = 0
    src_roof: dict[str, int] = {}
    src_mat: dict[str, int] = {}
    mats_used: dict[int, int] = {}

    for i in range(len(df)):
        parts = cleaned[i]
        if not parts:
            dropped += 1
            continue
        z0 = float(ground[i])
        z1 = float(roofz[i])
        if not (math.isfinite(z0) and math.isfinite(z1)) or z1 - z0 < min_height * 0.5:
            z1 = z0 + max(min_height, 1.0)
        # ---- roof
        kind, slope, rsource = _resolve_roof(i, col_roof, col_slope, ra_type, ra_slope, ra_src,
                                             col_fc, classes, cls[i], int(fcode[i]),
                                             int(floors[i]), parts[0],
                                             _f(bfront, i), _f(lfront, i))
        # ADR-013 §5 publishes the eave and ridge offsets it measured; prefer them over the pitch.
        rise = 0.0
        if kind != sg.ROOF_FLAT and ra_ridge is not None and ra_eave is not None:
            dr, de = _f(ra_ridge, i), _f(ra_eave, i)
            if math.isfinite(dr) and math.isfinite(de) and dr - de > 0.05:
                rise = float(dr - de)
        # ---- material
        mat_wall, msource = _resolve_material(i, col_mat, col_fc, classes, cls[i], int(year[i]),
                                              int(boro[i]), int(floors[i]), z1 - z0)
        mat_roof = MAT_ROOF_FLAT if kind in (sg.ROOF_FLAT, sg.ROOF_COMPLEX) else MAT_ROOF_PITCHED
        if int(fcode[i]) == FC_GARAGE and kind == sg.ROOF_FLAT:
            mat_roof = MAT_ROOF_TAR
        src_roof[rsource] = src_roof.get(rsource, 0) + 1
        src_mat[msource] = src_mat.get(msource, 0) + 1
        mats_used[mat_wall] = mats_used.get(mat_wall, 0) + 1
        mats_used[mat_roof] = mats_used.get(mat_roof, 0) + 1

        z_top = z1
        if ridge_mode == "adr013" and kind != sg.ROOF_FLAT and ra_ridge is not None:
            dz = ra_ridge[i]
            if dz is not None and isinstance(dz, (int, float, np.floating)) and math.isfinite(float(dz)):
                z_top = z1 + float(dz)

        fcv = float(col_fc[i]) if col_fc is not None else 0.0
        attrs = {
            "bin": float(bins[i]),
            "facade_class": fcv,
            "floors": float(floors[i]),
            "floor_height": float(fh[i]),
            "ground_floor_height": float(gfh[i]),
            "is_storefront": 1.0 if bool(store[i]) else 0.0,
            "lit_seed_hi": float(int(seed[i]) >> 16),
            "lit_seed_lo": float(int(seed[i]) & 0xFFFF),
        }
        for part in parts:
            local = shapely.transform(part, lambda c: c - np.array([x0, y0]))
            area = float(area_col[i]) if area_col is not None else float(part.area)
            specs.append(sg.BuildingSpec(
                bin=int(bins[i]), polygon=local, ground_z=z0, roof_z=z_top,
                roof=sg.RoofSpec(kind=kind, slope_deg=slope, rise_m=rise,
                                 parapet_h=sg.PARAPET_H_M if kind == sg.ROOF_FLAT else 0.0,
                                 source=rsource),
                mat_wall=mat_wall, mat_roof=mat_roof,
                facade_heading=float(head[i]) if math.isfinite(head[i]) else 0.0,
                attrs=attrs, floors=max(int(floors[i]), 1), area=area))
            df_index.append(i)

    return TileLoad(tile, x0, y0, specs, len(df), dropped,
                    {"roof": src_roof, "material": src_mat}, mats_used, df_index)


def _f(arr, i) -> float:
    if arr is None:
        return float("nan")
    try:
        return float(arr[i])
    except (TypeError, ValueError):
        return float("nan")


def _resolve_roof(i, col_roof, col_slope, ra_type, ra_slope, ra_src, col_fc, classes,
                  bldg_class, feature_code, floors, poly, bldg_frontage, lot_frontage) -> tuple[int, float, str]:
    slope = sg.GABLE_SLOPE_DEG
    if col_roof is not None:
        v = col_roof[i]
        if v is not None and not (isinstance(v, float) and math.isnan(v)):
            kind = int(v)
            if 0 <= kind < len(sg.ROOF_NAMES):
                if col_slope is not None and math.isfinite(float(col_slope[i])) and float(col_slope[i]) > 1.0:
                    slope = float(col_slope[i])
                return kind, slope, "column"
    if ra_type is not None:
        v = ra_type[i]
        kind = _coerce_roof_kind(v)
        if kind is not None:
            if ra_slope is not None:
                s = ra_slope[i]
                try:
                    if s is not None and math.isfinite(float(s)) and float(s) > 1.0:
                        slope = float(s)
                except (TypeError, ValueError):
                    pass
            tag = "roof_attrs"
            if ra_src is not None and isinstance(ra_src[i], str):
                tag = f"roof_attrs:{ra_src[i]}"
            return kind, slope, tag
    if col_fc is not None:
        rec = classes.get(int(col_fc[i]) if col_fc[i] == col_fc[i] else 0)
        if rec:
            kind = _FACADE_ROOF_KIND.get(str(rec.get("roof", "")), None)
            if kind is not None:
                if str(rec.get("roof")) == "pitched_steep":
                    slope = sg.STEEP_SLOPE_DEG
                return kind, slope, "facade_class"
    short = _short_side(poly)
    kind, s = _roof_from_class(bldg_class, feature_code, floors, float(poly.area), short,
                               bldg_frontage, lot_frontage)
    return kind, (s or slope), ("bldg_class" if kind != sg.ROOF_FLAT else "default_flat")


def _coerce_roof_kind(v) -> int | None:
    if v is None:
        return None
    if isinstance(v, str):
        return _ROOF_NAME_KIND.get(v.strip().lower())
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(f):
        return None
    k = int(f)
    return k if 0 <= k < len(sg.ROOF_NAMES) else None


def _short_side(poly) -> float:
    try:
        _, _, _, _, b = sg.obb_frame(poly)
        return 2.0 * b
    except Exception:
        xmin, ymin, xmax, ymax = poly.bounds
        return min(xmax - xmin, ymax - ymin)


def _resolve_material(i, col_mat, col_fc, classes, bldg_class, year, boro, floors, height) -> tuple[int, str]:
    if col_mat is not None:
        v = col_mat[i]
        try:
            m = int(v)
        except (TypeError, ValueError):
            m = -1
        if 0 <= m < fp.CONTRACT_MATERIAL_COUNT:
            return m, "column"
    if col_fc is not None:
        try:
            fc = int(col_fc[i])
        except (TypeError, ValueError):
            fc = 0
        m = _material_from_facade_class(classes, fc)
        if m is not None:
            return m, "facade_class"
    return _material_from_class(bldg_class, year, boro, floors, height), "bldg_class"


def material_name(idx: int) -> str:
    return fp.MATERIALS[idx] if 0 <= idx < len(fp.MATERIALS) else f"mat{idx}"


def write_json(path: Path, doc: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(doc, f, indent=1, sort_keys=True)
    return path
