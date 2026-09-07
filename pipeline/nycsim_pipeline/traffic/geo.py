"""NTA-2020 and taxi-zone geometry in NYC_TM plus point-in-polygon / overlay helpers."""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import shapely
from shapely.geometry import shape
from shapely.strtree import STRtree

from ..crs import lonlat_to_tm
from ..paths import RAW

log = logging.getLogger("nycsim.traffic.geo")

NTA_PATH = RAW / "nyc_opendata" / "nta_2020.geojson"
TAXI_ZONES_PATH = RAW / "nyc_opendata" / "taxi_zones.geojson"
BOROUGH_PATH = RAW / "nyc_opendata" / "borough_boundaries.geojson"

BOROUGH_NAMES = {1: "Manhattan", 2: "Bronx", 3: "Brooklyn", 4: "Queens", 5: "Staten Island"}
BOROUGH_CODES = {v: k for k, v in BOROUGH_NAMES.items()}
# NTA type codes (DCP): 0 residential, 5 rikers island, 6 other special areas, 7 cemeteries, 8 airports, 9 parks
NTA_TYPE_RESIDENTIAL = 0

# 60th Street in WGS84 (West End Ave/60th -> York Ave/60th): the customary northern edge of the Manhattan CBD.
_CBD_LINE_LONLAT = ((-73.9955, 40.7743), (-73.9598, 40.7594))


def to_nyc_tm(geom: shapely.Geometry) -> shapely.Geometry:
    """Reproject a WGS84 shapely geometry to NYC_TM (vectorised over all coordinates)."""
    def _f(coords: np.ndarray) -> np.ndarray:
        x, y = lonlat_to_tm(coords[:, 0], coords[:, 1])
        return np.column_stack([x, y])
    return shapely.transform(geom, _f)


def cbd_line_tm() -> tuple[tuple[float, float], tuple[float, float]]:
    (ax, ay), (bx, by) = _CBD_LINE_LONLAT
    x, y = lonlat_to_tm(np.array([ax, bx]), np.array([ay, by]))
    return (float(x[0]), float(y[0])), (float(x[1]), float(y[1]))


def south_of_cbd_line(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    """True where points lie south (right-hand side) of the 60th Street line."""
    (ax, ay), (bx, by) = cbd_line_tm()
    cross = (bx - ax) * (np.asarray(y) - ay) - (by - ay) * (np.asarray(x) - ax)
    return cross < 0


@dataclass
class NtaTable:
    codes: list[str]
    names: list[str]
    borocode: np.ndarray          # int8 1..5
    ntatype: np.ndarray           # int8
    geoms: np.ndarray             # shapely (Multi)Polygons in NYC_TM
    area_km2: np.ndarray
    cx: np.ndarray
    cy: np.ndarray
    is_cbd: np.ndarray            # Manhattan south of 60th St
    index: dict[str, int]
    tree: STRtree

    def __len__(self) -> int:
        return len(self.codes)

    @property
    def is_special(self) -> np.ndarray:
        """Parks, cemeteries, airports, Rikers, other special areas (no resident population)."""
        return self.ntatype != NTA_TYPE_RESIDENTIAL

    def assign_points(self, x: np.ndarray, y: np.ndarray, *, snap_m: float = 250.0) -> np.ndarray:
        """NTA index for each point (-1 if outside every polygon and farther than ``snap_m`` from all)."""
        x = np.asarray(x, dtype=np.float64)
        y = np.asarray(y, dtype=np.float64)
        out = np.full(len(x), -1, dtype=np.int32)
        if len(x) == 0:
            return out
        pts = shapely.points(x, y)
        pi, gi = self.tree.query(pts, predicate="within")
        out[pi] = gi
        missing = np.flatnonzero(out < 0)
        if len(missing):
            mi, mg = self.tree.query_nearest(pts[missing], max_distance=snap_m, return_distance=False, all_matches=False)
            out[missing[mi]] = mg
        return out

    def overlay_fractions(self, geoms: np.ndarray | list) -> list[tuple[int, int, float]]:
        """For each source polygon: (src_i, nta_i, fraction of the *source* area inside the NTA)."""
        geoms = np.asarray(geoms, dtype=object)
        out: list[tuple[int, int, float]] = []
        si, gi = self.tree.query(geoms, predicate="intersects")
        for s, g in zip(si.tolist(), gi.tolist()):
            a = geoms[s].area
            if a <= 0:
                continue
            inter = shapely.intersection(geoms[s], self.geoms[g]).area
            if inter > 0:
                out.append((s, g, float(inter / a)))
        return out


def load_ntas(path: Path = NTA_PATH) -> NtaTable:
    if not path.exists():
        raise FileNotFoundError(f"{path} missing — run `python -m nycsim_pipeline.download --id nta_2020`")
    with open(path) as f:
        doc = json.load(f)
    feats = doc["features"]
    codes, names, boro, ntype, geoms = [], [], [], [], []
    for ft in feats:
        p = ft["properties"]
        g = shape(ft["geometry"])
        if g.is_empty:
            raise ValueError(f"empty NTA geometry {p.get('nta2020')}")
        g = to_nyc_tm(g)
        if not g.is_valid:
            g = shapely.make_valid(g)
        codes.append(str(p["nta2020"]))
        names.append(str(p["ntaname"]))
        boro.append(int(p["borocode"]))
        ntype.append(int(p["ntatype"]))
        geoms.append(g)
    geoms_arr = np.array(geoms, dtype=object)
    order = np.argsort(np.array(codes))
    codes = [codes[i] for i in order]
    names = [names[i] for i in order]
    geoms_arr = geoms_arr[order]
    borocode = np.array(boro, dtype=np.int8)[order]
    ntatype = np.array(ntype, dtype=np.int8)[order]
    if len(set(codes)) != len(codes):
        raise ValueError("duplicate NTA codes in nta_2020.geojson")
    area = shapely.area(geoms_arr) / 1e6
    cent = shapely.centroid(geoms_arr)
    cx, cy = shapely.get_x(cent), shapely.get_y(cent)
    is_cbd = (borocode == 1) & south_of_cbd_line(cx, cy)
    # Governors/Liberty/Ellis islands + Battery are south of 60th but not CBD traffic-wise only if not connected; keep Battery (MN0191 has FDR/West St).
    tbl = NtaTable(codes, names, borocode, ntatype, geoms_arr, area, cx, cy, is_cbd, {c: i for i, c in enumerate(codes)}, STRtree(geoms_arr))
    log.info("loaded %d NTAs (%d CBD, %d special)", len(tbl), int(is_cbd.sum()), int(tbl.is_special.sum()))
    return tbl


@dataclass
class TaxiZones:
    location_ids: np.ndarray      # int32
    names: list[str]
    boroughs: list[str]
    geoms: np.ndarray
    area_km2: np.ndarray

    def __len__(self) -> int:
        return len(self.location_ids)


def load_taxi_zones(path: Path = TAXI_ZONES_PATH) -> TaxiZones:
    if not path.exists():
        raise FileNotFoundError(f"{path} missing — run `python -m nycsim_pipeline.download --id taxi_zones`")
    with open(path) as f:
        doc = json.load(f)
    ids, names, boros, geoms = [], [], [], []
    for ft in doc["features"]:
        p = ft["properties"]
        g = to_nyc_tm(shape(ft["geometry"]))
        if not g.is_valid:
            g = shapely.make_valid(g)
        ids.append(int(p["locationid"]))
        names.append(str(p.get("zone") or ""))
        boros.append(str(p.get("borough") or ""))
        geoms.append(g)
    garr = np.array(geoms, dtype=object)
    tz = TaxiZones(np.array(ids, dtype=np.int32), names, boros, garr, shapely.area(garr) / 1e6)
    log.info("loaded %d taxi zones", len(tz))
    return tz


def taxi_zone_to_nta_weights(tz: TaxiZones, nta: NtaTable) -> dict[int, list[tuple[int, float]]]:
    """locationid -> [(nta_idx, fraction of zone area)], fractions renormalised to sum to 1 per zone
    (zones partly over water lose the water part). Zones with no NTA overlap (EWR, Newark) are absent."""
    frac = nta.overlay_fractions(tz.geoms)
    per_zone: dict[int, list[tuple[int, float]]] = {}
    for s, g, f in frac:
        per_zone.setdefault(int(tz.location_ids[s]), []).append((g, f))
    out: dict[int, list[tuple[int, float]]] = {}
    for lid, lst in per_zone.items():
        tot = sum(f for _, f in lst)
        if tot <= 0:
            continue
        out[lid] = [(g, f / tot) for g, f in lst if f / tot >= 0.005]
        s = sum(f for _, f in out[lid])
        out[lid] = [(g, f / s) for g, f in out[lid]]
    return out
