"""Traffic calibration stage — CLI entry point.

    python -m nycsim_pipeline.traffic.build [--no-runtime] [--rebuild-sidewalks]

Produces
  ``data/processed/traffic/density.parquet``   DATA_CONTRACTS §10, 262 NTAs × 24 h × 3 day types
  ``data/processed/traffic/density_detail.parquet``  the same cells with the diagnostic columns
  ``data/processed/traffic/fleet_mix.json``    per-class shares by borough / CBD / time band
  ``data/processed/traffic/build_summary.json``  every number quoted in the verification report
  ``data/processed/runtime/density.nycb``      DATA_CONTRACTS §15 runtime binary

Runtime on the 4-vCPU build box: about 4 minutes end to end (7 minutes on the first run, which also
builds the sidewalk-area cache from the 530 MB planimetric layer).  Peak RSS stays below 1.6 GB.
"""
from __future__ import annotations

import argparse
import json
import logging
import resource
import sys
import time
from pathlib import Path

import numpy as np
import polars as pl
import pyarrow.parquet as pq

from ..manifest import git_commit, record_processed
from ..paths import PROCESSED, RAW
from . import accessibility, counts, fleet_mix, geo, landuse, model, pedestrians, segments
from . import runtime_export, shares, sidewalks, speed, tlc
from . import DAY_TYPES, HOURS, N_NTA_EXPECTED, SCHEMA_NAME

log = logging.getLogger("nycsim.traffic.build")

OUT_DIR = PROCESSED / "traffic"
RUNTIME_DIR = PROCESSED / "runtime"
DENSITY_PATH = OUT_DIR / "density.parquet"
DETAIL_PATH = OUT_DIR / "density_detail.parquet"
FLEET_PATH = OUT_DIR / "fleet_mix.json"
SUMMARY_PATH = OUT_DIR / "build_summary.json"
NYCB_PATH = RUNTIME_DIR / "density.nycb"

CONTRACT_COLUMNS = ["nta_code", "hour", "dow", "veh_per_km_lane", "ped_per_m2_sidewalk",
                    "taxi_share", "truck_share", "bus_share", "bike_share", "source"]
SOURCE_IDS = ["traffic_volume_auto", "dot_vehicle_class_counts", "dot_ped_counts_biannual",
              "dot_bike_ped_hourly", "dot_bike_ped_sensors", "centerline", "pluto", "nta_2020",
              "taxi_zones", "subway_entrances", "plan_sidewalk", "plan_public_plazas", "ped_plazas",
              "dsny_frequencies", "tlc_yellow_2025_05", "tlc_green_2025_05", "tlc_fhvhv_2025_05"]


def _peak_rss_mb() -> float:
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0


def _flatten(nta: geo.NtaTable, arrays: dict[str, np.ndarray]) -> pl.DataFrame:
    """(n_nta, 24, 3) arrays → a long frame ordered by nta_code, dow, hour."""
    n = len(nta)
    codes = np.repeat(np.array(nta.codes, dtype=object), HOURS * DAY_TYPES)
    dow = np.tile(np.repeat(np.arange(DAY_TYPES, dtype=np.int8), HOURS), n)
    hour = np.tile(np.arange(HOURS, dtype=np.int8), n * DAY_TYPES)
    out = {"nta_code": codes.tolist(), "hour": hour, "dow": dow}
    for k, a in arrays.items():
        if a.shape != (n, HOURS, DAY_TYPES):
            raise ValueError(f"{k}: shape {a.shape} != {(n, HOURS, DAY_TYPES)}")
        out[k] = np.ascontiguousarray(np.transpose(a, (0, 2, 1))).reshape(-1)
    return pl.DataFrame(out)


def _write_parquet(df: pl.DataFrame, path: Path, schema_id: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tbl = df.to_arrow()
    meta = dict(tbl.schema.metadata or {})
    meta[b"nycsim.schema"] = schema_id.encode()
    meta[b"nycsim.schema_version"] = b"1"
    meta[b"nycsim.git_commit"] = git_commit().encode()
    tbl = tbl.replace_schema_metadata(meta)
    tmp = path.with_suffix(path.suffix + ".tmp")
    pq.write_table(tbl, tmp, compression="snappy")
    tmp.replace(path)


def run(*, write_runtime: bool = True, rebuild_sidewalks: bool = False) -> dict:
    t_start = time.time()
    stamps: dict[str, float] = {}

    def mark(name: str) -> None:
        stamps[name] = round(time.time() - t_start, 1)

    nta = geo.load_ntas()
    if len(nta) != N_NTA_EXPECTED:
        raise ValueError(f"{len(nta)} NTAs loaded, expected {N_NTA_EXPECTED}")
    zones = geo.load_taxi_zones()
    zone_weights = geo.taxi_zone_to_nta_weights(zones, nta)
    mark("geo")

    seg = segments.load_segments(nta)
    roads = segments.nta_road_summary(seg, nta)
    mark("segments")

    lots = landuse.load_lots(nta)
    lu = landuse.load_landuse(nta, lots=lots)
    access = accessibility.load_accessibility(nta, seg, lu)
    clusters = model.cluster_of(nta, lu)
    mark("landuse")

    cd = counts.load_counts()
    ms = model.match_sites(cd, seg)
    sm = model.build_site_model(cd, ms, clusters)
    lm = model.fit_level_model(sm, nta, lu, roads, access)
    mark("counts")

    agg = tlc.aggregate()
    corridors = tlc.corridor_weights(zones, nta, tlc.pair_list(agg.vkm), zone_weights)
    tlc_speed, tlc_trip_km = tlc.zone_speed_to_nta(agg.speed, zone_weights, len(nta))
    mark("tlc")

    vol = model.assemble(nta, seg, sm, lm, clusters, tlc_speed, tlc_trip_km)
    mark("volumes")

    # for-hire kilometres follow the traffic, so the corridor split is weighted by each NTA's own
    # modelled vehicle-km (see tlc.zone_to_nta)
    tlc_vkm = tlc.zone_to_nta(agg.vkm, corridors, len(nta), vol.veh_km_h.mean(axis=(1, 2)))
    mark("tlc_allocation")

    sw = sidewalks.sidewalk_area_by_nta(nta, use_cache=not rebuild_sidewalks)
    sub_xy = accessibility._subway_points()
    raster = pedestrians.build_generator_raster(lots, sub_xy)
    ped_sites = pedestrians.load_ped_count_sites(nta)
    ped_reg = pedestrians.fit_ped_level_model(ped_sites, raster, nta)
    trips = tlc.trips_by_zone_hour(agg.vkm)
    ped = pedestrians.pedestrian_density(nta, seg, raster, ped_sites, ped_reg, trips, zone_weights, sw)
    mark("pedestrians")

    cls_counts = shares.load_class_counts(seg, nta, ms.df.select(["segment_id", "seg_row"]))
    cs = shares.class_shares(cls_counts, nta, clusters)
    bike_lvl, bike_prof = shares.load_bike_counters(seg)
    bike = shares.fit_bike_model(bike_lvl, bike_prof, seg, nta, raster.sample)
    sh = shares.build_shares(nta, seg, vol, tlc_vkm, cs, bike)
    mark("shares")

    density = _flatten(nta, {
        "veh_per_km_lane": vol.density,
        "ped_per_m2_sidewalk": ped.density,
        "taxi_share": sh.taxi,
        "truck_share": sh.truck,
        "bus_share": sh.bus,
        "bike_share": sh.bike,
    })
    src_map = {c: s for c, s in zip(nta.codes, vol.source.tolist())}
    density = density.with_columns(
        pl.col("nta_code").replace_strict(src_map, return_dtype=pl.Utf8).alias("source")
    ).select(CONTRACT_COLUMNS)
    _validate(density, nta)
    _write_parquet(density, DENSITY_PATH, SCHEMA_NAME)

    detail = _flatten(nta, {
        "veh_per_km_lane": vol.density,
        "flow_veh_h_lane": vol.q_lane,
        "speed_kmh": vol.speed_kmh,
        "veh_km_h": vol.veh_km_h,
        "ped_per_m2_sidewalk": ped.density,
        "ped_present": ped.present,
        "ped_flow_per_h": ped.flow_mean,
        "taxi_share": sh.taxi,
        "truck_share": sh.truck,
        "bus_share": sh.bus,
        "bike_share": sh.bike,
        "taxi_vkm_h": sh.taxi_vkm,
        "bike_veh_km_h": sh.bike_flow_nta,
        "tlc_speed_kmh": np.nan_to_num(tlc_speed, nan=-1.0),
        "speed_calibration": vol.calibration.factor,
    })
    per_nta = pl.DataFrame({
        "nta_code": nta.codes, "nta_name": nta.names, "borough": nta.borocode,
        "is_cbd": nta.is_cbd, "is_special": nta.is_special, "area_km2": nta.area_km2,
        "cluster": clusters.tolist(), "lane_km": vol.lane_km,
        "walkable_sidewalk_m2": sw.sort("nta_idx")["walkable_m2"].to_numpy(),
        "n_atr_sites": lm.n_sites, "n_atr_sites_recent": lm.n_sites_recent,
        "nta_effect": lm.effect, "nta_effect_obs": lm.effect_obs, "nta_effect_pred": lm.effect_pred,
        "source": vol.source.tolist(),
    })
    detail = detail.join(per_nta, on="nta_code", how="left")
    _write_parquet(detail, DETAIL_PATH, "traffic/density_detail@1")

    veh_count = vol.density * vol.lane_km[:, None, None]
    group_shares = fleet_mix.region_group_shares(
        nta, {"taxi": sh.taxi, "truck": sh.truck, "bus": sh.bus, "bike": sh.bike}, veh_count)
    fm = fleet_mix.build_fleet_mix(nta, lu, tlc_vkm, RAW / "nyc_opendata" / fleet_mix.DSNY_PATH,
                                   sh.stats, group_shares)
    fleet_mix.validate_fleet_mix(fm)
    fleet_mix.write_fleet_mix(fm, FLEET_PATH)
    mark("outputs")

    nycb_info: dict = {"written": False}
    if write_runtime:
        runtime_export.write_density_nycb(NYCB_PATH, nta, density)
        nycb_info = runtime_export.verify_density_nycb(NYCB_PATH, density)
        nycb_info["written"] = True
        mark("runtime")

    summary = _summary(nta, seg, roads, sw, cd, ms, sm, lm, vol, ped, sh, cs, bike, agg, density,
                       nycb_info, stamps, t_start)
    SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(SUMMARY_PATH, "w") as f:
        json.dump(summary, f, indent=1, default=float)

    record_processed("traffic_density", DENSITY_PATH, stage="traffic", sources=SOURCE_IDS,
                     rows=density.height, schema=SCHEMA_NAME,
                     extra={"ntas": len(nta), "hours": HOURS, "day_types": DAY_TYPES})
    record_processed("traffic_density_detail", DETAIL_PATH, stage="traffic", sources=SOURCE_IDS,
                     rows=detail.height, schema="traffic/density_detail@1")
    record_processed("traffic_fleet_mix", FLEET_PATH, stage="traffic", sources=SOURCE_IDS,
                     rows=len(fm["mix"]), schema="traffic/fleet_mix@1")
    if nycb_info.get("written"):
        record_processed("runtime_density_nycb", NYCB_PATH, stage="traffic", sources=["traffic_density"],
                         rows=nycb_info["cells"], schema="runtime/density.nycb@1", extra=nycb_info)
    log.info("traffic stage complete in %.1f s, peak RSS %.0f MB", time.time() - t_start, _peak_rss_mb())
    return summary


def _validate(df: pl.DataFrame, nta: geo.NtaTable) -> None:
    """Every contract invariant, checked before anything is written."""
    if list(df.columns) != CONTRACT_COLUMNS:
        raise ValueError(f"column order {df.columns} != {CONTRACT_COLUMNS}")
    expect = len(nta) * HOURS * DAY_TYPES
    if df.height != expect:
        raise ValueError(f"{df.height} rows, expected {expect}")
    if df.select(pl.struct(["nta_code", "hour", "dow"]).n_unique()).item() != expect:
        raise ValueError("duplicate (nta_code, hour, dow) keys")
    if sorted(df["nta_code"].unique().to_list()) != sorted(nta.codes):
        raise ValueError("NTA code set does not match nta_2020")
    if df["hour"].min() != 0 or df["hour"].max() != HOURS - 1:
        raise ValueError("hour out of range")
    if df["dow"].min() != 0 or df["dow"].max() != DAY_TYPES - 1:
        raise ValueError("dow out of range")
    share_cols = ["taxi_share", "truck_share", "bus_share", "bike_share"]
    for c in ["veh_per_km_lane", "ped_per_m2_sidewalk", *share_cols]:
        v = df[c].to_numpy()
        if not np.isfinite(v).all():
            raise ValueError(f"{c} has {int((~np.isfinite(v)).sum())} non-finite values")
        if v.min() < 0:
            raise ValueError(f"{c} has negative values (min {v.min()})")
    for c in share_cols:
        if df[c].max() > 1.0:
            raise ValueError(f"{c} exceeds 1 (max {df[c].max()})")
    tot = sum(df[c].to_numpy() for c in share_cols)
    if tot.max() > 1.0 + 1e-9:
        raise ValueError(f"shares sum above 1 (max {tot.max()})")
    if df["veh_per_km_lane"].max() > speed.K_JAM + 1e-6:
        raise ValueError(f"veh_per_km_lane above jam density ({df['veh_per_km_lane'].max()})")
    if df["source"].null_count():
        raise ValueError("null source")
    log.info("contract check passed: %d rows, %d NTAs, shares in [0,1] summing to <= %.4f, "
             "veh/km/lane in [%.3f, %.1f], ped/m² in [%.5f, %.4f]",
             df.height, df["nta_code"].n_unique(), float(tot.max()),
             df["veh_per_km_lane"].min(), df["veh_per_km_lane"].max(),
             df["ped_per_m2_sidewalk"].min(), df["ped_per_m2_sidewalk"].max())


def _top_bottom(nta: geo.NtaTable, values: np.ndarray, k: int = 10) -> dict:
    order = np.argsort(-values)
    def rows(idx):
        return [{"nta": nta.codes[i], "name": nta.names[i], "borough": int(nta.borocode[i]),
                 "value": float(values[i])} for i in idx]
    return {"top": rows(order[:k]), "bottom": rows(order[::-1][:k])}


def _summary(nta, seg, roads, sw, cd, ms, sm, lm, vol, ped, sh, cs, bike, agg, density, nycb_info,
             stamps, t_start) -> dict:
    d17 = vol.density[:, 17, 0]
    ped13 = ped.density[:, 13, 0]
    cls_summary = speed.free_flow_summary(seg, vol.road_class)
    return {
        "schema_version": 1,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "git_commit": git_commit(),
        "runtime_s": round(time.time() - t_start, 1),
        "stage_seconds": stamps,
        "peak_rss_mb": round(_peak_rss_mb(), 1),
        "ntas": len(nta),
        "rows": density.height,
        "segments": {"vehicular": seg.df.height, "lane_km": float(seg.df["lane_km"].sum()),
                     "road_km": float(seg.df["length_m"].sum() / 1000.0),
                     "lanes_inferred": int(seg.df["lanes_source"].sum()),
                     "speed_inferred": int(seg.df["speed_source"].sum())},
        "counts": {"flows": cd.flows.height, "sites": cd.sites.height,
                   "sites_recent": int((cd.sites["tier"] == "recent").sum()),
                   "matched": ms.n_by_match, "sites_with_level": int(sm.sites["level"].is_not_null().sum()),
                   "direction_doubled_hours": sm.dir_doubled, "profile_sites": sm.profile_n},
        "level_model": {
            "stage1_road_class": lm.stage1.as_dict(),
            "stage2_land_use": lm.stage2.as_dict(),
            "stage2_features": list(lm.stage2_selected),
            "nta_r2_road_class_only": lm.nta_r2_class_only,
            "nta_r2_with_land_use": lm.nta_r2_with_landuse,
            "nta_n": lm.nta_n,
            "within_nta_residual_sd": lm.within_nta_sd,
            "ntas_with_sites": int((lm.n_sites > 0).sum()),
            "ntas_from_regression": int((lm.n_sites == 0).sum()),
        },
        "speed_model": {
            "k_jam_veh_km_lane": speed.K_JAM,
            "classes": cls_summary.to_dicts(),
            "calibration": {"cells_from_tlc": vol.calibration.n_direct,
                            "cells_from_borough_median": vol.calibration.n_borough,
                            "cells_uncalibrated": vol.calibration.n_default,
                            "factor_p05_p50_p95": [float(x) for x in np.percentile(vol.calibration.factor, [5, 50, 95])]},
            "tlc": {"trips_read": agg.n_trips_read, "trips_used": agg.n_trips_used,
                    "day_counts": agg.day_counts},
        },
        "density": {
            "min": float(vol.density.min()), "p50": float(np.percentile(vol.density, 50)),
            "p95": float(np.percentile(vol.density, 95)), "max": float(vol.density.max()),
            "citywide_veh_km_per_weekday": float(vol.veh_km_h[:, :, 0].sum()),
            "weekday_17h": _top_bottom(nta, d17),
        },
        "pedestrians": {
            "regression": ped.regression.as_dict(), "sites": ped.n_sites,
            "walkable_sidewalk_km2": float(sw["walkable_m2"].sum() / 1e6),
            "mapped_sidewalk_km2": float(sw["sidewalk_m2"].sum() / 1e6),
            "walk_speed_mps": pedestrians.WALK_SPEED_MPS,
            "stationary_factor": pedestrians.STATIONARY_FACTOR,
            "p50": float(np.percentile(ped.density, 50)), "p95": float(np.percentile(ped.density, 95)),
            "max": float(ped.density.max()),
            "citywide_present_13h_weekday": float(ped.present[:, 13, 0].sum()),
            "weekday_13h": _top_bottom(nta, ped13),
            "counter_check": ped.counter_check,
            "period_correction": [float(x) for x in ped.correction],
        },
        "shares": {
            "stats": sh.stats,
            "class_count_segments": cs.n_sites,
            "ntas_with_class_sites": cs.n_nta_with_sites,
            "citywide_truck_share_by_hour_weekday": [float(x) for x in cs.citywide[:, 0, 0]],
            "citywide_bus_share_by_hour_weekday": [float(x) for x in cs.citywide[:, 0, 1]],
            "bike_model": bike.regression.as_dict(),
            "bike_sensors": bike.n_sensors,
            "bike_trips_per_day_anchor": bike.trips_per_day_implied,
            "bike_level_scale": bike.level_scale,
            "for_hire_occupancy": shares.OCCUPANCY,
        },
        "monotonic_checks": _monotonic_checks(nta, vol.density),
        "runtime_nycb": nycb_info,
    }


def _monotonic_checks(nta: geo.NtaTable, density: np.ndarray) -> dict:
    def val(code: str, hour: int, dow: int = 0) -> float:
        return float(density[nta.index[code], hour, dow])
    mid = "MN0502"      # Midtown-Times Square
    tot = "SI0305"      # Tottenville-Charleston
    out = {
        "midtown_code": mid, "midtown_name": nta.names[nta.index[mid]],
        "tottenville_code": tot, "tottenville_name": nta.names[nta.index[tot]],
        "midtown_17": val(mid, 17), "midtown_04": val(mid, 4), "tottenville_17": val(tot, 17),
    }
    out["midtown_17_gt_midtown_04"] = out["midtown_17"] > out["midtown_04"]
    out["midtown_17_gt_tottenville_17"] = out["midtown_17"] > out["tottenville_17"]
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--no-runtime", action="store_true", help="skip data/processed/runtime/density.nycb")
    ap.add_argument("--rebuild-sidewalks", action="store_true", help="re-read the 530 MB sidewalk layer")
    ap.add_argument("-v", "--verbose", action="store_true")
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if a.verbose else logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s %(message)s")
    s = run(write_runtime=not a.no_runtime, rebuild_sidewalks=a.rebuild_sidewalks)
    print(json.dumps({k: s[k] for k in ("rows", "ntas", "runtime_s", "peak_rss_mb", "monotonic_checks")},
                     indent=1, default=float))
    return 0


if __name__ == "__main__":
    sys.exit(main())
