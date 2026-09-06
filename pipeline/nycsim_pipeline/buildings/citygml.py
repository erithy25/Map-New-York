"""CityGML LOD2 (NYC 3-D Building Model, 2014 LiDAR) -> per-BIN triangulated solids.

Input : ``data/raw/doitt_3d/DA_WISE_GML.zip`` (20 members ``DA_WISE_GMLs/DA{n}_3D_Buildings_Merged.gml``,
        13.8 GB of CityGML 2.0, EPSG:2263 US-survey-feet, z = feet NAVD88). The zip is never
        extracted: each member is streamed through ``unzip -p`` into ``lxml.etree.iterparse``.
Output: ``data/processed/buildings/citygml/da{n}.parquet`` (schema ``citygml_solids_v1``, one row per
        BIN), ``index.parquet`` (whole city), ``progress.json`` (resumable per DA).

Run:   ``python -m nycsim_pipeline citygml [--da 4 [--limit 2000]] [--build-index] [--validate]``

Row schema (``SCHEMA`` below; Parquet key/value metadata ``nycsim.schema`` = ``citygml_solids_v1``):
  bin int64 (0 when missing), bin_ok bool (False for missing or placeholder x000000 BINs),
  gml_id, doitt_id, source_id, da,
  n_roof / n_wall / n_ground (kept polygons per surface type), n_dropped (rings/polygons dropped),
  z_ground_min, z_roof_max, z_roof_main (metres NAVD88), roof_type (0..8, see citygml_roof),
  n_roof_levels, roof_level_z[], roof_level_area[], roof_slope_deg,
  footprint_area_m2, roof_area_m2, wall_area_m2, cx, cy, xmin..ymax (NYC_TM), tx, ty (1 km tile),
  tri_count, vertex_count, tri_xyz (little-endian float32, tri_count*9 values, x y z per vertex,
  3 vertices per triangle, absolute NYC_TM metres), tri_type (uint8 per triangle: 0 ground, 1 wall,
  2 roof), flags (bitfield ``F_*``).
Triangle winding: roof triangles face up, ground triangles face down (outward), wall triangles keep the
source winding (outward, CCW seen from outside; agreement with a centroid test is counted in the summary).
"""
from __future__ import annotations

import argparse
import fcntl
import json
import logging
import math
import os
import re
import resource
import shutil
import subprocess
import sys
import time
import warnings
import zipfile
from collections import Counter
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
from lxml import etree

from .. import crs as crs_mod
from ..crs import TILE_SIZE_M
from ..manifest import record_processed
from ..paths import PROCESSED, RAW, REPO_ROOT
import shapely

from .citygml_geom import (SURF_GROUND, SURF_ROOF, SURF_WALL, PLANARITY_TOL_M, azimuth_deg, clean_ring, cluster_1d,
                           finalize_triangles, flip_triangles, remove_collinear, slope_deg, triangulate_polygon,
                           weld_vertex_count)
from .citygml_roof import FLAT_SLOPE_DEG, ROOF_COMPLEX, ROOF_NAMES, LEVEL_TOL_M, VERTICAL_SLOPE_DEG, RoofFace, classify_roof

log = logging.getLogger("nycsim.citygml")

# --------------------------------------------------------------------------- constants
ZIP_PATH = RAW / "doitt_3d" / "DA_WISE_GML.zip"
OUT_DIR = PROCESSED / "buildings" / "citygml"
FOOTPRINTS = PROCESSED / "buildings" / "footprints_raw.parquet"
MEMBER_FMT = "DA_WISE_GMLs/DA{n}_3D_Buildings_Merged.gml"
DA_IDS = tuple(range(1, 21))
SCHEMA_ID = "citygml_solids_v1"
INDEX_SCHEMA_ID = "citygml_index_v1"
PROGRESS_FILE = "progress.json"
LOCK_FILE = ".citygml.lock"
FLUSH_ROWS = 4000
DEFAULT_SRS_EPSG = 2263
SOURCE_ID = "doitt_3d_citygml"

NS_GML = "http://www.opengis.net/gml"
NS_GML32 = "http://www.opengis.net/gml/3.2"
NS_BLDG = ("http://www.opengis.net/citygml/building/1.0", "http://www.opengis.net/citygml/building/2.0")
NS_GEN = ("http://www.opengis.net/citygml/generics/1.0", "http://www.opengis.net/citygml/generics/2.0")
TAG_BUILDING = tuple(f"{{{ns}}}Building" for ns in NS_BLDG)
TAG_STRATTR = tuple(f"{{{ns}}}stringAttribute" for ns in NS_GEN) + tuple(f"{{{ns}}}intAttribute" for ns in NS_GEN)
TAG_GENVALUE = tuple(f"{{{ns}}}value" for ns in NS_GEN)
_GMLS = (NS_GML, NS_GML32)
TAG_POLY = tuple(f"{{{ns}}}{t}" for ns in _GMLS for t in ("Polygon", "Triangle", "Rectangle"))
TAG_EXTERIOR = tuple(f"{{{ns}}}exterior" for ns in _GMLS)
TAG_INTERIOR = tuple(f"{{{ns}}}interior" for ns in _GMLS)
TAG_LINEARRING = tuple(f"{{{ns}}}LinearRing" for ns in _GMLS)
TAG_POSLIST = tuple(f"{{{ns}}}posList" for ns in _GMLS)
TAG_POS = tuple(f"{{{ns}}}pos" for ns in _GMLS)
TAG_COORDINATES = tuple(f"{{{ns}}}coordinates" for ns in _GMLS)
GML_ID_ATTRS = (f"{{{NS_GML}}}id", f"{{{NS_GML32}}}id")

# CityGML boundary-surface local names -> triangle surface type
SURFACE_TYPE_BY_NAME = {
    "GroundSurface": SURF_GROUND,
    "WallSurface": SURF_WALL,
    "RoofSurface": SURF_ROOF,
    "ClosureSurface": SURF_WALL,
    "OuterCeilingSurface": SURF_WALL,
    "OuterFloorSurface": SURF_ROOF,
}

# flags bitfield
F_NO_GROUND = 1 << 0        # no GroundSurface: footprint area/centroid from roof faces, z_ground_min from all vertices
F_NO_ROOF = 1 << 1          # no RoofSurface: roof_type defaults to 0, z_roof_max from all vertices
F_NO_WALL = 1 << 2
F_DROPPED = 1 << 3          # at least one ring/polygon of this building was dropped (see n_dropped)
F_BIN_MISSING = 1 << 4      # no numeric BIN attribute -> bin = 0
F_BIN_PLACEHOLDER = 1 << 5  # BIN is a borough placeholder (1000000..5000000)
F_MERGED = 1 << 6           # several Building elements with the same BIN were merged into this row
F_NON_PLANAR = 1 << 7       # a polygon deviated > PLANARITY_TOL_M from its best-fit plane
F_TYPE_BY_NORMAL = 1 << 8   # a polygon outside a known boundary-surface type was typed from its normal
F_SRS_ASSUMED = 1 << 9      # srsName missing/unparseable: EPSG:2263 assumed
F_WALL_INWARD = 1 << 10     # a ground-touching wall's source winding points into the footprint (kept as-is)
FLAG_NAMES = {
    "NO_GROUND": F_NO_GROUND, "NO_ROOF": F_NO_ROOF, "NO_WALL": F_NO_WALL, "DROPPED": F_DROPPED,
    "BIN_MISSING": F_BIN_MISSING, "BIN_PLACEHOLDER": F_BIN_PLACEHOLDER, "MERGED": F_MERGED,
    "NON_PLANAR": F_NON_PLANAR, "TYPE_BY_NORMAL": F_TYPE_BY_NORMAL, "SRS_ASSUMED": F_SRS_ASSUMED,
    "WALL_INWARD": F_WALL_INWARD,
}

SCHEMA_DOC = {
    "schema_version": 1,
    "schema": SCHEMA_ID,
    "crs": "NYC_TM (see crs.json); z metres NAVD88",
    "horizontal_datum": "EPSG:2263 (NAD83) -> WGS84 with the 7-parameter Helmert NAD_1983_To_WGS_1984_5 (position vector) "
                        "unless the foundation transformer already applies a datum shift; see DATUM_* / summary['datum']",
    "tri_xyz": "little-endian float32, tri_count*9 values: [x0 y0 z0 x1 y1 z1 x2 y2 z2] per triangle, absolute NYC_TM metres",
    "tri_type": "uint8 per triangle: 0 ground, 1 wall, 2 roof",
    "winding": "roof up, ground down, walls source winding (outward)",
    "roof_type": dict(enumerate(ROOF_NAMES)),
    "flags": FLAG_NAMES,
    "source": SOURCE_ID,
}

SCHEMA = pa.schema([
    ("bin", pa.int64()), ("bin_ok", pa.bool_()), ("gml_id", pa.string()), ("doitt_id", pa.int64()),
    ("source_id", pa.int64()), ("da", pa.int8()),
    ("n_roof", pa.int32()), ("n_wall", pa.int32()), ("n_ground", pa.int32()), ("n_dropped", pa.int32()),
    ("z_ground_min", pa.float32()), ("z_roof_max", pa.float32()), ("z_roof_main", pa.float32()),
    ("roof_type", pa.int8()), ("n_roof_levels", pa.int16()),
    ("roof_level_z", pa.list_(pa.float32())), ("roof_level_area", pa.list_(pa.float32())),
    ("roof_slope_deg", pa.float32()),
    ("footprint_area_m2", pa.float32()), ("roof_area_m2", pa.float32()), ("wall_area_m2", pa.float32()),
    ("cx", pa.float64()), ("cy", pa.float64()),
    ("xmin", pa.float64()), ("ymin", pa.float64()), ("xmax", pa.float64()), ("ymax", pa.float64()),
    ("tx", pa.int32()), ("ty", pa.int32()),
    ("tri_count", pa.int32()), ("vertex_count", pa.int32()),
    ("tri_xyz", pa.binary()), ("tri_type", pa.binary()), ("flags", pa.uint16()),
], metadata={"nycsim.schema": SCHEMA_ID, "nycsim.citygml": json.dumps(SCHEMA_DOC)})

INDEX_COLUMNS = ["bin", "bin_ok", "da", "doitt_id", "roof_type", "n_roof_levels", "z_ground_min", "z_roof_max",
                 "z_roof_main", "footprint_area_m2", "tri_count", "cx", "cy", "tx", "ty", "flags"]

# numpy.fromstring() only *warns* about trailing unparsable data; make that an exception so malformed
# posLists take the slow, counting code path instead of being silently truncated.
warnings.filterwarnings("error", message="string or file could not be read to its end")

# srsName spellings seen in CityGML: "EPSG:2263" (what the DoITT delivery uses), the OGC urn
# "urn:ogc:def:crs:EPSG::2263" / "urn:ogc:def:crs:EPSG:6.12:2263" (an authority *version* sits between the
# authority and the code and must not be mistaken for it), the compound urn
# "urn:ogc:def:crs,crs:EPSG:6.12:2263,crs:EPSG:6.12:5703" (the first code is the horizontal one) and the
# OGC http form "http://www.opengis.net/def/crs/EPSG/0/2263".
_SRS_RE = re.compile(r"EPSG[:/]{1,2}(?:\d+(?:\.\d+)*[:/])?(\d{3,6})\b", re.IGNORECASE)

# NAD83 -> WGS84 7-parameter Helmert (ESRI "NAD_1983_To_WGS_1984_5" = NAD83(CORS96) -> ITRF00 @ 1997.0, position-vector
# convention). Measured against footprints_raw (Socrata WGS84 export of the same buildings) this reproduces the
# footprint frame to < 1 cm, whereas PROJ's default "NAD83 to WGS 84 (1)" is a null shift that leaves the CityGML
# 0.92 m south / 0.12 m east of every Socrata-derived layer (see docs/verification/citygml/REPORT.md).
DATUM_HELMERT_PIPELINE = (
    "+proj=pipeline +step +proj=unitconvert +xy_in=deg +xy_out=rad +step +proj=cart +ellps=GRS80 "
    "+step +proj=helmert +x=-0.9956 +y=1.9013 +z=0.5215 +rx=0.025915 +ry=0.009426 +rz=0.011599 +s=0.00062 "
    "+convention=position_vector +step +inv +proj=cart +ellps=WGS84 +step +proj=unitconvert +xy_in=rad +xy_out=deg"
)
DATUM_MODES = ("auto", "helmert", "foundation")
DATUM_REF_POINT_FT = (995000.0, 200000.0)   # a point in the East River near the NYC_TM origin
DATUM_DETECT_TOL_M = 0.05
_datum_mode = "auto"


class _Horizontal:
    """Callable (x_ft, y_ft) -> (x_m, y_m) NYC_TM for one source EPSG code, with the chosen datum handling."""

    def __init__(self, epsg: int, mode: str):
        from pyproj import CRS, Transformer
        c = CRS.from_epsg(epsg)
        self.z_factor = float(c.axis_info[0].unit_conversion_factor) if c.axis_info else 1.0
        self.foundation = crs_mod.transformer(epsg, "NYC_TM")
        geog = c.geodetic_crs
        self.to_geog = Transformer.from_crs(c, geog, always_xy=True)     # same datum: pure inverse projection
        self.helmert = Transformer.from_pipeline(DATUM_HELMERT_PIPELINE)
        self.mode = mode
        self.shift_m = (0.0, 0.0)
        if mode == "auto":
            # Does the foundation transformer already move points relative to a same-datum projection?
            x, y = DATUM_REF_POINT_FT
            fx, fy = self.foundation.transform(x, y)
            lon, lat = self.to_geog.transform(x, y)
            nx, ny = crs_mod.lonlat_to_tm(lon, lat)
            self.mode = "foundation" if math.hypot(fx - nx, fy - ny) > DATUM_DETECT_TOL_M else "helmert"
        if self.mode == "helmert":
            x, y = DATUM_REF_POINT_FT
            lon, lat = self.to_geog.transform(x, y)
            x0, y0 = crs_mod.lonlat_to_tm(lon, lat)
            x1, y1 = self(np.array([x]), np.array([y]))
            self.shift_m = (float(x1[0] - x0), float(y1[0] - y0))
        self.description = (f"{self.mode}: " + (f"NAD83->WGS84 Helmert (position vector), shift at reference point "
                                                f"dE={self.shift_m[0]:+.3f} m dN={self.shift_m[1]:+.3f} m"
                                                if self.mode == "helmert" else self.foundation.description))

    def __call__(self, x: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        if self.mode == "foundation":
            return self.foundation.transform(x, y)
        lon, lat = self.to_geog.transform(x, y)
        lon, lat = self.helmert.transform(lon, lat)
        return crs_mod.lonlat_to_tm(lon, lat)


_transformers: dict[tuple[int, str], _Horizontal] = {}


def set_datum_mode(mode: str) -> None:
    """Select how the NAD83 -> WGS84 step is handled: auto (default), helmert, foundation."""
    global _datum_mode
    if mode not in DATUM_MODES:
        raise ValueError(f"datum mode must be one of {DATUM_MODES}")
    _datum_mode = mode
    _transformers.clear()


def datum_info(epsg: int = DEFAULT_SRS_EPSG) -> dict[str, Any]:
    """How EPSG:``epsg`` x/y were brought into NYC_TM (recorded in every summary/progress entry)."""
    h = horizontal_transformer(epsg)
    return {"mode": h.mode, "requested": _datum_mode, "shift_at_ref_m": [round(h.shift_m[0], 4), round(h.shift_m[1], 4)],
            "description": h.description}


def horizontal_transformer(epsg: int = DEFAULT_SRS_EPSG) -> _Horizontal:
    """Cached horizontal transformer for a source EPSG code under the current datum mode."""
    key = (epsg, _datum_mode)
    if key not in _transformers:
        _transformers[key] = _Horizontal(epsg, _datum_mode)
    return _transformers[key]


def parse_srs(srs_name: str | None) -> int | None:
    """EPSG code from an srsName in any common spelling; None if absent/unparseable."""
    if not srs_name:
        return None
    m = _SRS_RE.search(srs_name)
    return int(m.group(1)) if m else None


def parse_bin(raw: str | None) -> tuple[int, bool, int]:
    """(bin, bin_ok, flags) from the raw BIN attribute text."""
    if raw is None:
        return 0, False, F_BIN_MISSING
    s = raw.strip()
    if not s.isdigit():
        return 0, False, F_BIN_MISSING
    b = int(s)
    if b < 1_000_000 or b > 5_999_999:
        return b, False, F_BIN_MISSING
    if b % 1_000_000 == 0:
        return b, False, F_BIN_PLACEHOLDER
    return b, True, 0


def _to_int(raw: str | None) -> int:
    if raw is None:
        return 0
    s = raw.strip()
    if s.lstrip("-").isdigit():
        return int(s)
    try:
        return int(float(s))
    except ValueError:
        return 0


# --------------------------------------------------------------------------- ring parsing
def _slow_parse(text: str, counters: Counter) -> np.ndarray | None:
    vals: list[float] = []
    bad = 0
    for tok in text.replace(",", " ").split():
        try:
            vals.append(float(tok))
        except ValueError:
            bad += 1
    if bad:
        counters["poslist_bad_tokens"] += bad
        return None
    return np.asarray(vals, dtype=np.float64)


def _numbers(text: str | None, counters: Counter) -> np.ndarray | None:
    if not text or not text.strip():
        counters["ring_empty"] += 1
        return None
    try:
        return np.fromstring(text, dtype=np.float64, sep=" ")
    except (DeprecationWarning, ValueError):
        counters["poslist_slow_path"] += 1
        return _slow_parse(text, counters)


def ring_coords(ring_prop: etree._Element, counters: Counter) -> np.ndarray | None:
    """(n, 3) float64 coordinates (source units) of a ``gml:exterior``/``gml:interior`` property, or None.

    Accepts ``posList`` (preferred), a sequence of ``pos`` elements, or legacy ``coordinates``.
    Rings that are not 3-D, have a non-multiple-of-3 ordinate count, contain non-numeric or
    non-finite values, or are empty are dropped and counted.
    """
    lr = None
    for ch in ring_prop.iterchildren():
        if isinstance(ch.tag, str):
            lr = ch
            break
    if lr is None:
        counters["ring_no_linearring"] += 1
        return None
    dim_attr = lr.get("srsDimension")
    arr: np.ndarray | None = None
    pl = None
    for t in TAG_POSLIST:
        pl = lr.find(t)
        if pl is not None:
            break
    if pl is not None:
        dim_attr = pl.get("srsDimension") or dim_attr
        arr = _numbers(pl.text, counters)
        if arr is None:
            return None
    else:
        poss = [p for t in TAG_POS for p in lr.findall(t)]
        if poss:
            parts = []
            for p in poss:
                a = _numbers(p.text, counters)
                if a is None:
                    return None
                parts.append(a)
            if not parts:
                counters["ring_empty"] += 1
                return None
            dims = {p.size for p in parts}
            if len(dims) != 1:
                counters["ring_bad_count"] += 1
                return None
            dim_attr = dim_attr or str(parts[0].size)
            arr = np.concatenate(parts)
        else:
            co = None
            for t in TAG_COORDINATES:
                co = lr.find(t)
                if co is not None:
                    break
            if co is None:
                counters["ring_no_coords"] += 1
                return None
            cs, ts = co.get("cs", ","), co.get("ts", " ")
            txt = (co.text or "").replace(ts, " ").replace(cs, " ")
            arr = _numbers(txt, counters)
            if arr is None:
                return None
    if arr.size == 0:
        counters["ring_empty"] += 1
        return None
    if dim_attr:
        try:
            dim = int(dim_attr)
        except ValueError:
            dim = 0
    else:
        dim = 3 if arr.size % 3 == 0 else (2 if arr.size % 2 == 0 else 0)
    if dim != 3:
        counters["ring_not_3d"] += 1
        return None
    if arr.size % 3 != 0:
        counters["ring_bad_count"] += 1
        return None
    if not np.isfinite(arr).all():
        counters["ring_nonfinite"] += 1
        return None
    return arr.reshape(-1, 3)


def _surface_type_of(poly: etree._Element) -> tuple[int | None, str | None]:
    """Boundary-surface type of a polygon from its ancestors, plus the nearest srsName seen on the way."""
    srs = poly.get("srsName")
    stype: int | None = None
    for anc in poly.iterancestors():
        t = anc.tag
        if not isinstance(t, str):
            continue
        if srs is None:
            srs = anc.get("srsName")
        local = t.rsplit("}", 1)[-1]
        st = SURFACE_TYPE_BY_NAME.get(local)
        if st is not None:
            stype = st
            if srs is not None:
                break
        if t in TAG_BUILDING:
            break
    return stype, srs


# --------------------------------------------------------------------------- building parsing
def parse_building(elem: etree._Element, da: int, counters: Counter) -> dict[str, Any] | None:
    """Convert one ``bldg:Building`` element into a row dict (schema ``SCHEMA``), or None if it has no usable geometry."""
    gml_id = ""
    for a in GML_ID_ATTRS:
        gml_id = elem.get(a) or gml_id
    attrs: dict[str, str | None] = {}
    for child in elem.iterchildren(*TAG_STRATTR):
        name = child.get("name")
        if name is None:
            continue
        val = None
        for vt in TAG_GENVALUE:
            val = child.findtext(vt)
            if val is not None:
                break
        attrs[name] = val
    bin_val, bin_ok, flags = parse_bin(attrs.get("BIN"))
    if flags & F_BIN_MISSING:
        counters["building_no_bin"] += 1
    elif flags & F_BIN_PLACEHOLDER:
        counters["building_placeholder_bin"] += 1
    doitt_id = _to_int(attrs.get("DOITT_ID"))
    source_id = _to_int(attrs.get("SOURCE_ID"))

    # 1. collect rings in source units
    rings_src: list[np.ndarray] = []
    poly_specs: list[tuple[int | None, int]] = []
    n_dropped = 0
    srs_name: str | None = None
    for poly in elem.iter(*TAG_POLY):
        stype, srs = _surface_type_of(poly)
        if srs_name is None:
            srs_name = srs
        if stype is None:
            counters["polygon_unknown_surface_type"] += 1
        ext_el = None
        for t in TAG_EXTERIOR:
            ext_el = poly.find(t)
            if ext_el is not None:
                break
        if ext_el is None:
            counters["polygon_no_exterior"] += 1
            n_dropped += 1
            continue
        ext = ring_coords(ext_el, counters)
        if ext is None:
            counters["polygon_dropped_bad_ring"] += 1
            n_dropped += 1
            continue
        holes: list[np.ndarray] = []
        for int_el in poly.iterchildren(*TAG_INTERIOR):
            h = ring_coords(int_el, counters)
            if h is None:
                counters["hole_dropped_bad_ring"] += 1
                n_dropped += 1
                continue
            holes.append(h)
        if holes:
            counters["polygons_with_holes"] += 1
        poly_specs.append((stype, 1 + len(holes)))
        rings_src.append(ext)
        rings_src.extend(holes)
    if not poly_specs:
        counters["building_no_geometry"] += 1
        return None

    # 2. one CRS transform per building
    epsg = parse_srs(srs_name)
    if epsg is None:
        epsg = DEFAULT_SRS_EPSG
        flags |= F_SRS_ASSUMED
        counters["srs_assumed"] += 1
    try:
        tr = horizontal_transformer(epsg)
    except Exception:  # unknown EPSG code: fall back, flag, count
        counters["srs_unknown_epsg"] += 1
        flags |= F_SRS_ASSUMED
        tr = horizontal_transformer(DEFAULT_SRS_EPSG)
    allpts = np.concatenate(rings_src, axis=0)
    x, y = tr(allpts[:, 0], allpts[:, 1])
    pts_m = np.empty_like(allpts)
    pts_m[:, 0] = x
    pts_m[:, 1] = y
    pts_m[:, 2] = allpts[:, 2] * tr.z_factor
    sizes = np.fromiter((len(r) for r in rings_src), dtype=np.int64, count=len(rings_src))
    offsets = np.concatenate(([0], np.cumsum(sizes)))

    # 3. per polygon: clean, triangulate, orient, collect
    tris_out: list[np.ndarray] = []
    types_out: list[np.ndarray] = []
    roof_faces: list[RoofFace] = []
    ground_area = ground_cx = ground_cy = 0.0
    roof_area = wall_area = 0.0
    roof_xy_area = roof_cx = roof_cy = 0.0
    z_ground: list[float] = []
    z_roof: list[float] = []
    ground_rings: list[np.ndarray] = []
    wall_c: list[np.ndarray] = []
    wall_n: list[np.ndarray] = []
    wall_zmin: list[float] = []
    n_by_type = [0, 0, 0]
    n_tri_dropped = 0
    ri = 0
    for stype, nrings in poly_specs:
        rings_m: list[np.ndarray] = []
        for k in range(nrings):
            r, removed = clean_ring(pts_m[offsets[ri]:offsets[ri + 1]])
            ri += 1
            if removed:
                counters["dup_points_removed"] += removed
            r, removed = remove_collinear(r)
            if removed:
                counters["collinear_points_removed"] += removed
            rings_m.append(r)
        if len(rings_m[0]) < 3:
            counters["polygon_degenerate"] += 1
            n_dropped += 1
            continue
        res, reason = triangulate_polygon(rings_m)
        if res is None:
            counters["polygon_" + reason] += 1
            n_dropped += 1
            continue
        if reason == "ok:holes_dropped":
            counters["hole_dropped_degenerate"] += 1
            n_dropped += 1
        if res.max_plane_dev > PLANARITY_TOL_M:
            counters["polygon_non_planar"] += 1
            flags |= F_NON_PLANAR
        nhat = res.nhat
        tris = res.tris
        if stype is None:
            stype = SURF_ROOF if nhat[2] > 0.5 else (SURF_GROUND if nhat[2] < -0.5 else SURF_WALL)
            flags |= F_TYPE_BY_NORMAL
        if stype == SURF_ROOF:
            if nhat[2] < 0:
                tris = flip_triangles(tris)
                nhat = -nhat
                counters["roof_flipped_up"] += 1
            sl = slope_deg(nhat)
            counters["roof_face_horizontal" if sl < FLAT_SLOPE_DEG else ("roof_face_vertical" if sl > VERTICAL_SLOPE_DEG else "roof_face_sloped")] += 1
            roof_faces.append(RoofFace(res.area3d, res.area_xy, sl, azimuth_deg(nhat), res.z_min, res.z_max, res.z_mean))
            roof_area += res.area3d
            roof_xy_area += res.area_xy
            roof_cx += res.area_xy * res.centroid[0]
            roof_cy += res.area_xy * res.centroid[1]
            z_roof.append(res.z_max)
        elif stype == SURF_GROUND:
            if nhat[2] > 0:
                tris = flip_triangles(tris)
                nhat = -nhat
                counters["ground_flipped_down"] += 1
            ground_area += res.area_xy
            ground_cx += res.area_xy * res.centroid[0]
            ground_cy += res.area_xy * res.centroid[1]
            z_ground.append(res.z_min)
            ground_rings.append(rings_m[0][:, :2])
        else:
            wall_area += res.area3d
            wall_c.append(res.centroid)
            wall_n.append(nhat)
            wall_zmin.append(res.z_min)
        t32, dropped = finalize_triangles(tris, nhat)
        if dropped:
            n_tri_dropped += dropped
            counters["tri_dropped_f32_degenerate"] += dropped
            if len(t32) == 0:
                counters["polygon_all_tris_degenerate"] += 1
                n_dropped += 1
                continue
        n_by_type[stype] += 1
        tris_out.append(t32)
        types_out.append(np.full(len(t32), stype, dtype=np.uint8))
    if not tris_out:
        counters["building_no_geometry"] += 1
        return None
    if n_dropped:
        flags |= F_DROPPED

    xyz32 = np.concatenate(tris_out, axis=0)
    tri_type = np.concatenate(types_out)
    allv = xyz32.reshape(-1, 3).astype(np.float64)
    # footprint & centroid
    if ground_area > 0:
        cx, cy = ground_cx / ground_area, ground_cy / ground_area
        footprint_area = ground_area
    else:
        flags |= F_NO_GROUND
        counters["building_no_ground"] += 1
        if roof_xy_area > 0:
            cx, cy = roof_cx / roof_xy_area, roof_cy / roof_xy_area
        else:
            cx, cy = float(allv[:, 0].mean()), float(allv[:, 1].mean())
        footprint_area = roof_xy_area
    if not roof_faces:
        flags |= F_NO_ROOF
        counters["building_no_roof"] += 1
    if n_by_type[SURF_WALL] == 0:
        flags |= F_NO_WALL
        counters["building_no_wall"] += 1
    z_ground_min = min(z_ground) if z_ground else float(allv[:, 2].min())
    z_roof_max = max(z_roof) if z_roof else float(allv[:, 2].max())
    # Wall winding check (walls keep their source winding): a ground-touching wall faces outward when a point
    # 5 cm in front of its centroid lies outside the footprint. Measured 100 % outward on the real data.
    if wall_c and ground_rings:
        wz = np.asarray(wall_zmin)
        touching = np.abs(wz - z_ground_min) < 0.05
        if touching.any():
            try:
                fp_geom = shapely.union_all([shapely.polygons(r) for r in ground_rings if len(r) >= 3])
                if not fp_geom.is_valid:
                    fp_geom = shapely.make_valid(fp_geom)
                wc = np.asarray(wall_c)[touching]
                wn = np.asarray(wall_n)[touching]
                inside = shapely.contains_xy(fp_geom, wc[:, 0] + 0.05 * wn[:, 0], wc[:, 1] + 0.05 * wn[:, 1])
                n_in = int(inside.sum())
                counters["wall_ground_outward"] += int(touching.sum()) - n_in
                counters["wall_ground_inward"] += n_in
                if n_in:
                    flags |= F_WALL_INWARD
            except Exception:  # shapely failure on a pathological footprint must not stop the building
                counters["wall_check_failed"] += 1
    rc = classify_roof(roof_faces)
    z_roof_main = rc.z_main if roof_faces and math.isfinite(rc.z_main) else z_roof_max
    counters["roof_type_" + ROOF_NAMES[rc.roof_type]] += 1
    if n_tri_dropped:
        counters["buildings_with_tri_dropped"] += 1
    row = {
        "bin": bin_val, "bin_ok": bin_ok, "gml_id": gml_id, "doitt_id": doitt_id, "source_id": source_id, "da": da,
        "n_roof": n_by_type[SURF_ROOF], "n_wall": n_by_type[SURF_WALL], "n_ground": n_by_type[SURF_GROUND], "n_dropped": n_dropped,
        "z_ground_min": z_ground_min, "z_roof_max": z_roof_max, "z_roof_main": z_roof_main,
        "roof_type": rc.roof_type, "n_roof_levels": rc.n_roof_levels,
        "roof_level_z": rc.level_z, "roof_level_area": rc.level_area, "roof_slope_deg": rc.slope_deg,
        "footprint_area_m2": footprint_area, "roof_area_m2": roof_area, "wall_area_m2": wall_area,
        "cx": cx, "cy": cy,
        "xmin": float(allv[:, 0].min()), "ymin": float(allv[:, 1].min()), "xmax": float(allv[:, 0].max()), "ymax": float(allv[:, 1].max()),
        "tx": int(math.floor(cx / TILE_SIZE_M)), "ty": int(math.floor(cy / TILE_SIZE_M)),
        "tri_count": int(len(xyz32)), "vertex_count": weld_vertex_count(xyz32),
        "tri_xyz": xyz32.tobytes(), "tri_type": tri_type.tobytes(), "flags": flags,
    }
    return row


# --------------------------------------------------------------------------- streaming
class _CountingReader:
    """Wraps a binary stream and counts the bytes handed to the XML parser."""

    def __init__(self, f):
        self._f = f
        self.bytes = 0

    def read(self, n: int = -1) -> bytes:
        b = self._f.read(n)
        self.bytes += len(b)
        return b


def iter_buildings(source, counters: Counter | None = None) -> Iterator[etree._Element]:
    """Yield every ``bldg:Building`` element (CityGML 1.0 or 2.0) from a binary stream, freeing memory as it goes.

    The caller must not keep references to yielded elements past the next iteration.
    """
    ctx = etree.iterparse(source, events=("end",), tag=TAG_BUILDING, remove_blank_text=True, huge_tree=True,
                          remove_comments=True, remove_pis=True)
    for _ev, elem in ctx:
        yield elem
        elem.clear()
        parent = elem.getparent()
        if parent is not None:
            while parent.getprevious() is not None:
                del parent.getparent()[0]
        else:
            while elem.getprevious() is not None:
                del elem.getparent()[0]


class _ParquetSink:
    """Buffered row-group writer for ``SCHEMA`` writing to ``<path>.part`` and renaming on close."""

    def __init__(self, path: Path, flush_rows: int = FLUSH_ROWS):
        self.path = Path(path)
        self.tmp = self.path.with_name(self.path.name + ".part")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._writer = pq.ParquetWriter(self.tmp, SCHEMA, compression="snappy")
        self._rows: list[dict[str, Any]] = []
        self._flush_rows = flush_rows
        self.rows_written = 0

    @property
    def pending(self) -> int:
        return len(self._rows)

    def add(self, row: dict[str, Any]) -> None:
        self._rows.append(row)
        if len(self._rows) >= self._flush_rows:
            self.flush()

    def flush(self) -> None:
        if not self._rows:
            return
        table = pa.Table.from_pylist(self._rows, schema=SCHEMA)
        self._writer.write_table(table)
        self.rows_written += len(self._rows)
        self._rows = []

    def close(self, keep: bool = True) -> Path:
        self.flush()
        self._writer.close()
        if keep:
            os.replace(self.tmp, self.path)
            return self.path
        self.tmp.unlink(missing_ok=True)
        return self.path


def _rss_mb() -> float:
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0


def process_stream(source, *, da: int, out_path: Path, limit: int | None = None, log_every: int = 5000,
                   counters: Counter | None = None) -> dict[str, Any]:
    """Parse a CityGML byte stream into ``out_path`` (schema ``SCHEMA``). Never raises on bad content.

    Returns a summary dict: rows, buildings (elements seen), bytes, elapsed_s, counters, error (str or None),
    duplicate real BINs merged.
    """
    counters = counters if counters is not None else Counter()
    reader = _CountingReader(source)
    sink = _ParquetSink(out_path)
    t0 = time.time()
    n_seen = 0
    error: str | None = None
    bin_counts: Counter = Counter()
    exc_logged = 0
    try:
        for elem in iter_buildings(reader, counters):
            n_seen += 1
            try:
                row = parse_building(elem, da, counters)
            except Exception as e:  # a single pathological building must never stop the file
                counters["building_exception"] += 1
                row = None
                if exc_logged < 5:
                    exc_logged += 1
                    log.exception("DA%s building #%d (%s) raised %s", da, n_seen, elem.get(GML_ID_ATTRS[0]), e)
            if row is not None:
                if row["bin_ok"]:
                    bin_counts[row["bin"]] += 1
                sink.add(row)
            if log_every and n_seen % log_every == 0:
                dt = time.time() - t0
                log.info("DA%s %d buildings, %d rows, %.1f MB, %.0f bldg/s, %.1f MB/s, rss %.0f MB", da, n_seen,
                         sink.rows_written + sink.pending, reader.bytes / 1e6, n_seen / max(dt, 1e-9),
                         reader.bytes / 1e6 / max(dt, 1e-9), _rss_mb())
            if limit is not None and n_seen >= limit:
                break
    except etree.XMLSyntaxError as e:
        error = f"XMLSyntaxError after {n_seen} buildings: {e}"
        log.error("DA%s %s", da, error)
    except Exception as e:  # stream/IO failures
        error = f"{type(e).__name__} after {n_seen} buildings: {e}"
        log.exception("DA%s stream failed", da)
    path = sink.close(keep=True)
    dups = {b for b, c in bin_counts.items() if c > 1}
    n_merged = 0
    if dups:
        n_merged = merge_duplicate_bins(path, dups, counters)
    elapsed = time.time() - t0
    summary = {
        "rows": sink.rows_written - n_merged, "buildings": n_seen, "bytes": reader.bytes, "elapsed_s": round(elapsed, 2),
        "buildings_per_s": round(n_seen / max(elapsed, 1e-9), 1), "mb_per_s": round(reader.bytes / 1e6 / max(elapsed, 1e-9), 2),
        "max_rss_mb": round(_rss_mb(), 1), "duplicate_bins_merged": len(dups), "rows_merged_away": n_merged,
        "error": error, "counters": dict(sorted(counters.items())), "parquet": str(path),
        "datum": datum_info(),
    }
    return summary


# --------------------------------------------------------------------------- duplicate-BIN merge
def _merge_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Merge several Building rows with the same BIN into one per-BIN row (documented policy).

    Counts/areas are summed, heights min/max, blobs concatenated, roof levels re-clustered from the parts'
    level lists, roof_type kept when all parts agree else ``complex`` (6), flags OR-ed plus ``MERGED``.
    """
    rows = sorted(rows, key=lambda r: (-r["tri_count"], r["gml_id"]))
    first = rows[0]
    xyz = b"".join(r["tri_xyz"] for r in rows)
    typ = b"".join(r["tri_type"] for r in rows)
    lev_z = np.array([z for r in rows for z in r["roof_level_z"]], dtype=np.float64)
    lev_a = np.array([a for r in rows for a in r["roof_level_area"]], dtype=np.float64)
    level_z: list[float] = []
    level_area: list[float] = []
    for g in cluster_1d(lev_z, LEVEL_TOL_M):
        w = lev_a[g]
        level_z.append(float((lev_z[g] * w).sum() / w.sum()) if w.sum() > 0 else float(lev_z[g].mean()))
        level_area.append(float(w.sum()))
    fp_area = sum(r["footprint_area_m2"] for r in rows)
    roof_area = sum(r["roof_area_m2"] for r in rows)
    types = {r["roof_type"] for r in rows}
    z_roof_max = max(r["z_roof_max"] for r in rows)
    z_main = level_z[int(np.argmax(level_area))] if level_z else z_roof_max
    if fp_area > 0:
        cx = sum(r["cx"] * r["footprint_area_m2"] for r in rows) / fp_area
        cy = sum(r["cy"] * r["footprint_area_m2"] for r in rows) / fp_area
    else:
        cx = float(np.mean([r["cx"] for r in rows]))
        cy = float(np.mean([r["cy"] for r in rows]))
    flags = F_MERGED
    for r in rows:
        flags |= int(r["flags"])
    # a part without ground/roof/wall does not make the merged building lack it
    if any(not (r["flags"] & F_NO_GROUND) for r in rows):
        flags &= ~F_NO_GROUND
    if any(not (r["flags"] & F_NO_ROOF) for r in rows):
        flags &= ~F_NO_ROOF
    if any(not (r["flags"] & F_NO_WALL) for r in rows):
        flags &= ~F_NO_WALL
    xyz32 = np.frombuffer(xyz, dtype="<f4")
    return {
        "bin": first["bin"], "bin_ok": True, "gml_id": ";".join(r["gml_id"] for r in rows), "doitt_id": first["doitt_id"],
        "source_id": first["source_id"], "da": first["da"],
        "n_roof": sum(r["n_roof"] for r in rows), "n_wall": sum(r["n_wall"] for r in rows),
        "n_ground": sum(r["n_ground"] for r in rows), "n_dropped": sum(r["n_dropped"] for r in rows),
        "z_ground_min": min(r["z_ground_min"] for r in rows), "z_roof_max": z_roof_max, "z_roof_main": z_main,
        "roof_type": types.pop() if len(types) == 1 else ROOF_COMPLEX, "n_roof_levels": len(level_z),
        "roof_level_z": level_z, "roof_level_area": level_area,
        "roof_slope_deg": (sum(r["roof_slope_deg"] * r["roof_area_m2"] for r in rows) / roof_area) if roof_area > 0 else 0.0,
        "footprint_area_m2": fp_area, "roof_area_m2": roof_area, "wall_area_m2": sum(r["wall_area_m2"] for r in rows),
        "cx": cx, "cy": cy,
        "xmin": min(r["xmin"] for r in rows), "ymin": min(r["ymin"] for r in rows),
        "xmax": max(r["xmax"] for r in rows), "ymax": max(r["ymax"] for r in rows),
        "tx": int(math.floor(cx / TILE_SIZE_M)), "ty": int(math.floor(cy / TILE_SIZE_M)),
        "tri_count": sum(r["tri_count"] for r in rows), "vertex_count": weld_vertex_count(xyz32),
        "tri_xyz": xyz, "tri_type": typ, "flags": flags,
    }


def merge_duplicate_bins(path: Path, dups: set[int], counters: Counter | None = None) -> int:
    """Rewrite ``path`` so that each BIN in ``dups`` occupies exactly one row. Returns rows removed.

    Streams row groups (memory = one row group) and appends the merged rows at the end.
    """
    counters = counters if counters is not None else Counter()
    path = Path(path)
    tmp = path.with_name(path.name + ".merge")
    pf = pq.ParquetFile(path)
    held: dict[int, list[dict[str, Any]]] = {}
    with pq.ParquetWriter(tmp, SCHEMA, compression="snappy") as w:
        for rg in range(pf.metadata.num_row_groups):
            t = pf.read_row_group(rg)
            bins = t.column("bin").to_numpy()
            ok = t.column("bin_ok").to_numpy(zero_copy_only=False)
            mask = ok & np.isin(bins, np.fromiter(dups, dtype=np.int64, count=len(dups)))
            if mask.any():
                for r in t.filter(pa.array(mask)).to_pylist():
                    held.setdefault(int(r["bin"]), []).append(r)
                t = t.filter(pa.array(~mask))
            if t.num_rows:
                w.write_table(t)
        merged = [_merge_rows(rs) for rs in held.values()]
        if merged:
            w.write_table(pa.Table.from_pylist(merged, schema=SCHEMA))
    os.replace(tmp, path)
    removed = sum(len(rs) - 1 for rs in held.values())
    counters["duplicate_bin_rows_merged"] += removed
    return removed


# --------------------------------------------------------------------------- progress / locking
@contextmanager
def _locked(out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / LOCK_FILE, "w") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(fh, fcntl.LOCK_UN)


def read_progress(out_dir: Path) -> dict[str, Any]:
    p = out_dir / PROGRESS_FILE
    if p.exists():
        try:
            with open(p) as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            log.warning("progress.json unreadable (%s); starting fresh", e)
    return {"schema_version": 1, "zip": str(ZIP_PATH), "das": {}}


def _update_progress(out_dir: Path, da: int, patch: dict[str, Any]) -> dict[str, Any]:
    with _locked(out_dir):
        doc = read_progress(out_dir)
        entry = doc["das"].get(str(da), {})
        entry.update(patch)
        doc["das"][str(da)] = entry
        tmp = out_dir / (PROGRESS_FILE + ".tmp")
        with open(tmp, "w") as f:
            json.dump(doc, f, indent=1, sort_keys=True)
        os.replace(tmp, out_dir / PROGRESS_FILE)
        return entry


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


# --------------------------------------------------------------------------- per-DA driver
def open_member_stream(zip_path: Path, member: str) -> tuple[Any, subprocess.Popen | None]:
    """Binary stream of a zip member without extracting: ``unzip -p`` (fast, separate process) or zipfile fallback."""
    if shutil.which("unzip"):
        proc = subprocess.Popen(["unzip", "-p", str(zip_path), member], stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=1 << 20)
        return proc.stdout, proc
    zf = zipfile.ZipFile(zip_path)
    return zf.open(member), None


def member_size(zip_path: Path, member: str) -> int:
    with zipfile.ZipFile(zip_path) as zf:
        return zf.getinfo(member).file_size


def process_da(da: int, *, zip_path: Path = ZIP_PATH, out_dir: Path = OUT_DIR, limit: int | None = None, force: bool = False,
               log_every: int = 5000, manifest: bool = True) -> dict[str, Any]:
    """Process one delivery area. Resumable: a DA whose progress entry is ``done`` is skipped unless ``force``."""
    out_dir.mkdir(parents=True, exist_ok=True)
    member = MEMBER_FMT.format(n=da)
    full_run = limit is None
    out_path = out_dir / (f"da{da}.parquet" if full_run else f"da{da}_limit{limit}.parquet")
    if full_run and not force:
        entry = read_progress(out_dir)["das"].get(str(da))
        if entry and entry.get("status") == "done" and out_path.exists():
            log.info("DA%s already done (%s rows) - skipping", da, entry.get("rows"))
            return entry
    size = member_size(zip_path, member)
    if full_run:
        _update_progress(out_dir, da, {"status": "running", "started": _now(), "pid": os.getpid(), "member": member,
                                       "member_bytes": size, "rows": None, "error": None})
    log.info("DA%s start: %s (%.0f MB)%s", da, member, size / 1e6, f" limit={limit}" if limit else "")
    stream, proc = open_member_stream(zip_path, member)
    summary: dict[str, Any] | None = None
    unzip_rc: int | None = None
    unzip_err = ""
    try:
        summary = process_stream(stream, da=da, out_path=out_path, limit=limit, log_every=log_every)
    finally:
        if proc is not None:
            if limit is not None or summary is None or summary.get("error"):
                proc.kill()          # we stopped reading; unzip is blocked on a full pipe
                proc.wait()
            else:
                try:
                    unzip_rc = proc.wait(timeout=120)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    unzip_rc = proc.wait()
            if proc.stderr is not None:
                unzip_err = proc.stderr.read().decode(errors="replace").strip()
                proc.stderr.close()
            if proc.stdout is not None:
                proc.stdout.close()
        else:
            stream.close()
        if summary is None and full_run:  # process_stream itself failed (e.g. disk full): leave a trace and re-raise
            _update_progress(out_dir, da, {"status": "error", "finished": _now(), "error": "process_stream raised"})
    assert summary is not None
    if unzip_rc not in (None, 0):
        msg = f"unzip exit {unzip_rc}: {unzip_err[:300]}"
        log.error("DA%s %s", da, msg)
        summary["error"] = f"{summary['error']} | {msg}" if summary["error"] else msg
    if summary["error"] is None and full_run and summary["bytes"] < size:
        summary["error"] = f"stream ended early: {summary['bytes']} of {size} bytes"
    status = "done" if summary["error"] is None else "partial"
    summary.update({"status": status, "da": da, "member": member, "member_bytes": size, "finished": _now(), "limit": limit})
    log.info("DA%s %s: %d buildings -> %d rows in %.1fs (%.0f bldg/s, %.1f MB/s, rss %.0f MB)%s", da, status, summary["buildings"],
             summary["rows"], summary["elapsed_s"], summary["buildings_per_s"], summary["mb_per_s"], summary["max_rss_mb"],
             f"; ERROR {summary['error']}" if summary["error"] else "")
    if full_run:
        _update_progress(out_dir, da, summary)
        if manifest and status == "done":
            with _locked(out_dir):
                record_processed(f"citygml_da{da}", out_path, stage="citygml", sources=[SOURCE_ID], rows=summary["rows"],
                                 schema=SCHEMA_ID, extra={"da": da, "buildings_parsed": summary["buildings"],
                                                         "counters": summary["counters"], "elapsed_s": summary["elapsed_s"]})
    return summary


def process_gml_file(path: Path, *, da: int, out_path: Path, limit: int | None = None, log_every: int = 5000) -> dict[str, Any]:
    """Process a plain (unzipped) .gml file, e.g. the test fixture."""
    with open(path, "rb") as f:
        summary = process_stream(f, da=da, out_path=out_path, limit=limit, log_every=log_every)
    summary.update({"status": "done" if summary["error"] is None else "partial", "da": da, "member": str(path)})
    return summary


# --------------------------------------------------------------------------- index
def build_index(out_dir: Path = OUT_DIR, das: tuple[int, ...] = DA_IDS, manifest: bool = True) -> dict[str, Any]:
    """Concatenate the per-DA parquet files into ``index.parquet`` (one row per BIN city-wide).

    A real BIN present in several DA files (buildings straddling a delivery-area boundary are delivered in
    both) keeps the row with the most triangles; the number of such cross-DA duplicates is reported.
    """
    tables = []
    present = []
    for n in das:
        p = out_dir / f"da{n}.parquet"
        if p.exists():
            tables.append(pq.read_table(p, columns=INDEX_COLUMNS))
            present.append(n)
    if not tables:
        raise FileNotFoundError(f"no da*.parquet in {out_dir}")
    t = pa.concat_tables(tables)
    bins = t.column("bin").to_numpy()
    ok = t.column("bin_ok").to_numpy(zero_copy_only=False)
    tri = t.column("tri_count").to_numpy()
    da_col = t.column("da").to_numpy()
    order = np.lexsort((da_col, -tri, bins))  # by bin, then most triangles, then lowest DA
    keep = np.ones(len(bins), dtype=bool)
    sb = bins[order]
    sok = ok[order]
    dup = np.zeros(len(bins), dtype=bool)
    dup[1:] = (sb[1:] == sb[:-1]) & sok[1:]
    keep[order[dup]] = False
    n_dropped = int(dup.sum())
    t = t.take(pa.array(np.nonzero(keep)[0])).sort_by([("da", "ascending"), ("bin", "ascending")])
    meta = {"nycsim.schema": INDEX_SCHEMA_ID, "nycsim.citygml": json.dumps({
        "schema_version": 1, "schema": INDEX_SCHEMA_ID, "das": present, "cross_da_duplicates_dropped": n_dropped,
        "roof_type": dict(enumerate(ROOF_NAMES)), "flags": FLAG_NAMES})}
    t = t.replace_schema_metadata(meta)
    path = out_dir / "index.parquet"
    tmp = path.with_name(path.name + ".part")
    pq.write_table(t, tmp, compression="snappy")
    os.replace(tmp, path)
    rt = t.column("roof_type").to_numpy()
    hist = {ROOF_NAMES[i]: int((rt == i).sum()) for i in range(len(ROOF_NAMES))}
    okc = t.column("bin_ok").to_numpy(zero_copy_only=False)
    summary = {"path": str(path), "rows": t.num_rows, "bin_ok_rows": int(okc.sum()), "das": present,
               "cross_da_duplicates_dropped": n_dropped, "roof_type_hist": hist}
    log.info("index: %d rows (%d with valid BIN) from DA %s; %d cross-DA duplicates dropped", t.num_rows, int(okc.sum()), present, n_dropped)
    if manifest:
        with _locked(out_dir):
            record_processed("citygml_index", path, stage="citygml", sources=[SOURCE_ID], rows=t.num_rows, schema=INDEX_SCHEMA_ID,
                             extra={"das": present, "cross_da_duplicates_dropped": n_dropped, "roof_type_hist": hist})
    return summary


# --------------------------------------------------------------------------- CLI
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="nycsim_pipeline citygml", description=__doc__.split("\n\n")[0])
    ap.add_argument("--da", type=int, nargs="*", help="delivery areas to process (default: all 20, smallest first)")
    ap.add_argument("--limit", type=int, help="stop after N buildings (dev/test; output goes to da{n}_limit{N}.parquet, no progress/manifest)")
    ap.add_argument("--out", type=Path, default=OUT_DIR, help="output directory")
    ap.add_argument("--zip", type=Path, default=ZIP_PATH, help="DA_WISE_GML.zip path")
    ap.add_argument("--gml", type=Path, help="process a plain .gml file instead of a zip member (tests)")
    ap.add_argument("--label", type=int, default=0, help="DA label used with --gml")
    ap.add_argument("--force", action="store_true", help="re-process DAs already marked done")
    ap.add_argument("--build-index", action="store_true", help="build index.parquet from the per-DA files")
    ap.add_argument("--join", action="store_true",
                    help="build data/processed/buildings/roof_attrs.parquet from index.parquet + buildings_base + OSM roof:shape "
                         "(what buildings/build.py consumes for roof_type/roof_mesh_ref/ROOF_REAL)")
    ap.add_argument("--validate", action="store_true", help="compare against footprints_raw.parquet and write a validation JSON")
    ap.add_argument("--validation-out", type=Path, help="where to write the validation JSON (default docs/verification/citygml/)")
    ap.add_argument("--datum", choices=DATUM_MODES, default="auto",
                    help="NAD83->WGS84 handling for EPSG:2263 x/y: auto (default: Helmert unless crs.transformer already shifts), helmert, foundation")
    ap.add_argument("--log-every", type=int, default=5000)
    ap.add_argument("--no-manifest", action="store_true", help="do not record artefacts in data/manifest/processed.json")
    ap.add_argument("-v", "--verbose", action="store_true")
    a = ap.parse_args(argv)
    if not logging.getLogger().handlers:
        logging.basicConfig(level=logging.DEBUG if a.verbose else logging.INFO, stream=sys.stderr,
                            format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    out_dir: Path = a.out
    out_dir.mkdir(parents=True, exist_ok=True)
    set_datum_mode(a.datum)
    log.info("horizontal datum handling: %s", datum_info()["description"])
    summaries: list[dict[str, Any]] = []
    if a.gml:
        out_path = out_dir / (f"da{a.label}.parquet" if a.limit is None else f"da{a.label}_limit{a.limit}.parquet")
        s = process_gml_file(a.gml, da=a.label, out_path=out_path, limit=a.limit, log_every=a.log_every)
        summaries.append(s)
    elif a.da or (not a.build_index and not a.validate and not a.join):
        if not a.zip.exists():
            log.error("zip not found: %s", a.zip)
            return 2
        das = a.da if a.da else sorted(DA_IDS, key=lambda n: member_size(a.zip, MEMBER_FMT.format(n=n)))
        for n in das:
            if n not in DA_IDS:
                log.error("unknown DA %s (valid: 1..20)", n)
                return 2
            summaries.append(process_da(n, zip_path=a.zip, out_dir=out_dir, limit=a.limit, force=a.force,
                                        log_every=a.log_every, manifest=not a.no_manifest))
    for s in summaries:
        print(json.dumps({k: v for k, v in s.items() if k != "counters"}, default=str))
        print("  counters:", json.dumps(s.get("counters", {}), sort_keys=True))
    rc = 0
    if any(s.get("error") for s in summaries):
        rc = 1
    if a.build_index:
        try:
            print(json.dumps(build_index(out_dir, manifest=not a.no_manifest)))
        except FileNotFoundError as e:
            log.error("%s", e)
            rc = 1
    if a.join:
        from .citygml_join import OUT_PATH as ROOF_ATTRS_PATH, build_roof_attrs
        try:
            print(json.dumps(build_roof_attrs(index_path=out_dir / "index.parquet", out_path=ROOF_ATTRS_PATH,
                                              manifest=not a.no_manifest), indent=1, default=str))
        except FileNotFoundError as e:
            log.error("%s", e)
            rc = 1
    if a.validate:
        from .citygml_validate import validate
        parquets = [Path(s["parquet"]) for s in summaries if s.get("parquet")] or None
        rep = validate(out_dir, parquets=parquets, out_json=a.validation_out)
        print(json.dumps(rep, indent=1, default=str))
    return rc


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
