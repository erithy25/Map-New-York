"""Sidewalk area per NTA from the CSCL planimetric sidewalk layer (`plan_sidewalk.geojson`).

The pedestrian density in DATA_CONTRACTS §10 is *pedestrians per m² of sidewalk*, so the
denominator has to be the real walkable surface, not a rule of thumb.  The planimetric layer
(NYC OTI / DoITT, 2022 capture) holds 50,865 sidewalk polygons covering the whole city; each is
reprojected to NYC_TM, made valid and split across the NTAs it touches by area overlay.

``effective_width_m`` is the mean sidewalk width implied by that area and the NTA's street length
(two sidewalks per street), used by the pedestrian model to turn a sidewalk *flow* into a density.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

import numpy as np
import polars as pl
import pyogrio
import shapely

from ..crs import NYC_TM
from ..paths import PROCESSED, RAW
from .geo import NtaTable

log = logging.getLogger("nycsim.traffic.sidewalks")

SIDEWALK_PATH = RAW / "nyc_opendata" / "plan_sidewalk.geojson"
PLAZA_PATH = RAW / "nyc_opendata" / "plan_public_plazas.geojson"
PED_PLAZA_PATH = RAW / "nyc_opendata" / "ped_plazas.geojson"
CACHE = PROCESSED / "traffic" / "sidewalk_area.parquet"

# Obstruction factor: NYC DOT Street Design Manual (3rd ed., 2020) reserves the kerbside "furnishing
# zone" (~1.2 m: trees, hydrants, racks, bins, scaffolding legs) and the "frontage zone" (~0.5 m) of
# every sidewalk; only the "pedestrian clear path" carries walking traffic.  On the typical 15 ft
# (4.6 m) NYC sidewalk that leaves ~2.9 m, i.e. 63 % of the mapped polygon area.
WALKABLE_FRACTION = 0.63
CHUNK = 12000


def _read_polygons(path: Path, *, label: str) -> tuple[np.ndarray, np.ndarray]:
    """Read a planimetric polygon layer in chunks and return (geometries in NYC_TM, areas m²)."""
    if not path.exists():
        raise FileNotFoundError(f"{path} missing — run `python -m nycsim_pipeline.download --id {path.stem}`")
    info = pyogrio.read_info(path)
    n = int(info["features"])
    geoms: list[np.ndarray] = []
    for start in range(0, n, CHUNK):
        gdf = pyogrio.read_dataframe(path, columns=[], skip_features=start, max_features=CHUNK)
        if len(gdf) == 0:
            break
        g = gdf.to_crs(NYC_TM).geometry.values
        g = np.asarray(g, dtype=object)
        bad = ~shapely.is_valid(g)
        if bad.any():
            g[bad] = shapely.make_valid(g[bad])
        geoms.append(g)
        del gdf
    arr = np.concatenate(geoms) if geoms else np.array([], dtype=object)
    area = shapely.area(arr)
    log.info("%s: %d polygons, %.2f km² mapped", label, len(arr), area.sum() / 1e6)
    return arr, area


def sidewalk_area_by_nta(nta: NtaTable, *, use_cache: bool = True) -> pl.DataFrame:
    """One row per NTA: ``sidewalk_m2`` (mapped), ``walkable_m2`` (clear path), ``plaza_m2``.

    Cached in ``data/processed/traffic/sidewalk_area.parquet`` because the source is a 530 MB
    GeoJSON; delete that file or pass ``use_cache=False`` to rebuild.
    """
    if use_cache and CACHE.exists():
        df = pl.read_parquet(CACHE)
        if df.height == len(nta) and df["nta_code"].to_list() == nta.codes:
            log.info("sidewalk area from cache %s", CACHE)
            return df
        log.warning("sidewalk cache %s does not match the NTA table — rebuilding", CACHE)

    n = len(nta)
    sw_m2 = np.zeros(n)
    pz_m2 = np.zeros(n)
    for path, out, label in ((SIDEWALK_PATH, sw_m2, "sidewalk"), (PLAZA_PATH, pz_m2, "public plaza"),
                             (PED_PLAZA_PATH, pz_m2, "DOT pedestrian plaza")):
        geoms, area = _read_polygons(path, label=label)
        if len(geoms) == 0:
            continue
        for s, g, frac in nta.overlay_fractions(geoms):
            out[g] += area[s] * frac
        del geoms, area
    df = pl.DataFrame({
        "nta_idx": np.arange(n, dtype=np.int32),
        "nta_code": nta.codes,
        "sidewalk_m2": sw_m2,
        "walkable_m2": sw_m2 * WALKABLE_FRACTION,
        "plaza_m2": pz_m2,
    })
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    df.write_parquet(CACHE)
    log.info("sidewalk area: %.2f km² total, %.2f km² walkable, %.2f km² plazas; %d NTAs with none",
             sw_m2.sum() / 1e6, sw_m2.sum() * WALKABLE_FRACTION / 1e6, pz_m2.sum() / 1e6, int((sw_m2 <= 0).sum()))
    return df


def effective_width_m(sidewalk: pl.DataFrame, roads: pl.DataFrame) -> np.ndarray:
    """Mean walkable sidewalk width per NTA = walkable area / (2 × street length)."""
    a = sidewalk.sort("nta_idx")["walkable_m2"].to_numpy()
    road_m = roads.sort("nta_idx")["road_km"].to_numpy() * 1000.0
    with np.errstate(invalid="ignore", divide="ignore"):
        w = np.where(road_m > 0, a / (2.0 * road_m), 0.0)
    return np.clip(w, 0.6, 12.0)


def _self_test() -> int:  # pragma: no cover - manual invocation
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    from .geo import load_ntas
    nta = load_ntas()
    df = sidewalk_area_by_nta(nta, use_cache=False)
    print(json.dumps({"rows": df.height, "sidewalk_km2": float(df["sidewalk_m2"].sum() / 1e6)}, indent=1))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(_self_test())
