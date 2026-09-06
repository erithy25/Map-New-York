"""USGS 3DEP DEM source discovery via The National Map (TNM) products API.

Findings that shaped this module (2026-09-05, see docs/verification/terrain/REPORT.md):

* The NED **1/9 arc-second** dataset has *no product covering the five boroughs*. The 18 products whose
  0.25 deg cells intersect the scope carry data only for New Jersey (``nj_northeast_2007``,
  ``nj_3coastalcounties_2011``, ``nj_mercerco_2008``), Nassau County NY (``ny_nassauco_2010``),
  Fairfield CT and a 0.3 MB Westchester sliver (``ny_hudsonbay_2011``).
* 3DEP **1 m** DEMs exist for the whole city: project ``NY_CMPG_2013`` (2013-14 post-Sandy LiDAR, the
  same acquisition behind the NYC 1-ft DEM and the 2014 CityGML model), 21 tiles / 3.43 GB. They are
  UTM 18N NAD83, Float32, metres NAVD88 (stated in the product description).
* The **1/3 arc-second** seamless tiles ``n41w074``/``n41w075`` (10 m, metres NAVD88) cover everything.

Priority stack used by ``ingest``: 1 m (priority 0) > 1/9" (1) > 1/3" (2). Every product is a regular
``Source`` registered dynamically in ``nycsim_pipeline.sources.SOURCES`` so that the foundation
downloader/manifest handle it exactly like a static source.
"""
from __future__ import annotations

import json
import logging
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .. import download as dl
from ..crs import SCOPE_XMAX, SCOPE_XMIN, SCOPE_YMAX, SCOPE_YMIN, tm_to_lonlat
from ..sources import SOURCES, Source

log = logging.getLogger("nycsim.terrain.sources")

TNM_API = "https://tnmaccess.nationalmap.gov/api/v1/products"
TNM_DATASETS = {
    "19": "National Elevation Dataset (NED) 1/9 arc-second",
    "1m": "Digital Elevation Model (DEM) 1 meter",
}
TNM_BBOX = "-74.30,40.45,-73.65,40.95"  # matches the static usgs_3dep_19_index source
USGS_LICENSE = "USGS public domain"
USGS_ATTR = "U.S. Geological Survey, 3D Elevation Program"

# 1 m projects accepted for the five boroughs. One LiDAR epoch (2013-14) keeps the surface seamless and
# consistent with the 2014 CityGML roofs and the footprint ground elevations.
DEM_1M_PROJECTS = ("NY_CMPG_2013",)
# 1/9" products are only worth their bytes where they add resolution inside the world: skip products whose
# 0.25 deg cell overlaps the scope by less than this fraction (NJ interior west of -74.25, Raritan Bay strip).
MIN_OVERLAP_19 = 0.25
RAW_BUDGET_BYTES = 3 * 1024 ** 3

_PROJECT_RE = re.compile(r"/Projects/([^/]+)/TIFF/")
_CELL_RE = re.compile(r"_(x\d+y\d+)_")


@dataclass(frozen=True)
class DemSource:
    source: Source
    kind: str          # '1m' | '19' | '13'
    priority: int      # 0 = best
    bbox: tuple[float, float, float, float]  # lon/lat minx, miny, maxx, maxy (product cell)
    purge_after_ingest: bool
    title: str
    size_bytes: int

    @property
    def id(self) -> str:
        return self.source.id

    def raster_uri(self, path: Path) -> str:
        """rasterio-openable URI: the GeoTIFF itself, or the .img inside a NED19 zip."""
        if path.suffix.lower() == ".zip":
            with zipfile.ZipFile(path) as zf:
                imgs = [n for n in zf.namelist() if n.lower().endswith(".img")]
            if not imgs:
                raise FileNotFoundError(f"no .img inside {path}")
            return f"/vsizip/{path}/{imgs[0]}"
        return str(path)


def scope_bbox_lonlat(margin_m: float = 500.0) -> tuple[float, float, float, float]:
    """Lon/lat bbox of the (densified) scope rectangle plus a margin."""
    xs = np.linspace(SCOPE_XMIN - margin_m, SCOPE_XMAX + margin_m, 50)
    ys = np.linspace(SCOPE_YMIN - margin_m, SCOPE_YMAX + margin_m, 50)
    bx = np.concatenate([xs, xs, np.full(50, xs[0]), np.full(50, xs[-1])])
    by = np.concatenate([np.full(50, ys[0]), np.full(50, ys[-1]), ys, ys])
    lon, lat = tm_to_lonlat(bx, by)
    return (float(np.min(lon)), float(np.min(lat)), float(np.max(lon)), float(np.max(lat)))


def register(source: Source) -> Source:
    """Idempotently add a dynamic source to the registry (same id -> same definition)."""
    existing = SOURCES.get(source.id)
    if existing is not None and existing.url != source.url:
        raise ValueError(f"source id {source.id} already registered with a different URL")
    SOURCES[source.id] = source
    return source


def index_source(kind: str) -> Source:
    if kind == "19":
        return SOURCES["usgs_3dep_19_index"]
    if kind == "1m":
        ds = TNM_DATASETS["1m"].replace(" ", "%20")
        return register(Source(
            "usgs_3dep_1m_index",
            f"{TNM_API}?bbox={TNM_BBOX}&datasets={ds}&max=200&outputFormat=JSON",
            "json", USGS_LICENSE, USGS_ATTR,
            "Product index of 3DEP 1 m LiDAR-derived DEM tiles intersecting the scope", tags=("terrain",)))
    raise ValueError(kind)


def load_index(kind: str) -> list[dict]:
    """Download (once) and parse a TNM product index; re-fetch if the cached file is not valid JSON."""
    src = index_source(kind)
    path = dl.download(src)
    try:
        with open(path) as f:
            doc = json.load(f)
        items = doc["items"]
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        log.warning("index %s unreadable (%s); re-downloading", src.id, e)
        path = dl.download(src, force=True)
        with open(path) as f:
            doc = json.load(f)
        items = doc["items"]
    if doc.get("total", len(items)) > len(items):
        raise dl.DownloadError(f"TNM index {src.id} truncated: {len(items)} of {doc.get('total')} items")
    return items


def _overlap_fraction(bb: dict, scope: tuple[float, float, float, float]) -> float:
    w = max(0.0, min(bb["maxX"], scope[2]) - max(bb["minX"], scope[0]))
    h = max(0.0, min(bb["maxY"], scope[3]) - max(bb["minY"], scope[1]))
    area = max(1e-12, (bb["maxX"] - bb["minX"]) * (bb["maxY"] - bb["minY"]))
    return w * h / area


def discover(kinds: tuple[str, ...] = ("1m", "19", "13")) -> list[DemSource]:
    """Build the prioritised list of DEM sources that intersect the scope, registering each in SOURCES."""
    scope = scope_bbox_lonlat()
    out: list[DemSource] = []
    if "1m" in kinds:
        for it in load_index("1m"):
            url = it["downloadURL"]
            m = _PROJECT_RE.search(url)
            project = m.group(1) if m else ""
            if project not in DEM_1M_PROJECTS:
                continue
            bb = it["boundingBox"]
            if _overlap_fraction(bb, scope) <= 0.0:
                continue
            cell = _CELL_RE.search(Path(url).name)
            sid = f"usgs_3dep_1m_{cell.group(1) if cell else Path(url).stem}_{project}"
            src = register(Source(sid, url, "tif", USGS_LICENSE, USGS_ATTR,
                                  f"3DEP 1 m DEM {it['title']} (UTM 18N NAD83, metres NAVD88)",
                                  filename=Path(url).name, tags=("terrain", "3dep_1m")))
            out.append(DemSource(src, "1m", 0, (bb["minX"], bb["minY"], bb["maxX"], bb["maxY"]), True, it["title"], int(it.get("sizeInBytes") or 0)))
    if "19" in kinds:
        for it in load_index("19"):
            bb = it["boundingBox"]
            frac = _overlap_fraction(bb, scope)
            if frac < MIN_OVERLAP_19:
                log.info("skip 1/9\" %s: overlap %.0f%% < %.0f%%", it["title"], frac * 100, MIN_OVERLAP_19 * 100)
                continue
            url = it["downloadURL"]
            name = Path(url).stem
            src = register(Source(f"usgs_3dep_19_{name}", url, "img.zip", USGS_LICENSE, USGS_ATTR,
                                  f"NED 1/9 arc-second DEM {it['title']} (NAD83 geographic, metres NAVD88)",
                                  filename=Path(url).name, tags=("terrain", "3dep_19")))
            out.append(DemSource(src, "19", 1, (bb["minX"], bb["minY"], bb["maxX"], bb["maxY"]), False, it["title"], int(it.get("sizeInBytes") or 0)))
    if "13" in kinds:
        for sid, bb in (("usgs_3dep_13_n41w074", (-74.0006, 39.9994, -72.9994, 41.0006)),
                        ("usgs_3dep_13_n41w075", (-75.0006, 39.9994, -73.9994, 41.0006))):
            out.append(DemSource(SOURCES[sid], "13", 2, bb, False, sid, 0))
    out.sort(key=lambda d: (d.priority, d.id))
    return out


def fetch(dem: DemSource, force: bool = False) -> Path:
    """Download through the foundation downloader (idempotent, manifest-recorded)."""
    return dl.download(dem.source, force=force)


def local_path(dem: DemSource) -> Path:
    return dl._target(dem.source)  # noqa: SLF001 — single source of truth for raw locations
