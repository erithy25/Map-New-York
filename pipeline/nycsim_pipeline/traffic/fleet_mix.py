"""``data/processed/traffic/fleet_mix.json`` — a share for every ``core/traffic/VehicleClass.h`` class
by borough, central-business-district flag and time band.

The density table (DATA_CONTRACTS §10) says *how many* road users are on an NTA's lanes and what
fraction of them are for-hire, commercial, buses or bicycles.  This file says *which* of the 18
simulated vehicle classes those are.  Each class carries the real fleet figure it is derived from,
so the numbers can be audited:

===================  =========================================================================
class                fleet basis
===================  =========================================================================
sedan, suv           NYS DMV passenger-vehicle registrations in the five boroughs, about
                     1.9 M private cars; body split 55 % car / 45 % SUV-crossover.
taxi                 13,587 medallions (TLC).  Yellow taxis may pick up anywhere but work
                     overwhelmingly in Manhattan below 96th St and at the airports.
boro_taxi            green Street-Hail Livery permits, about 6,000 issued and roughly 850
                     active; by rule they may only pick up above West 110th/East 96th St and
                     in the outer boroughs (not the airports except by pre-arrangement).
black_car            about 100,000 licensed for-hire vehicles, of which roughly 78,000 are
                     high-volume (Uber/Lyft) and the rest black car / livery / luxury limousine.
nypd                 about 9,000 NYPD vehicles, distributed over 77 precincts (patrol density
                     roughly follows population, with a Manhattan-CBD surplus).
fdny_engine          198 engine companies.
fdny_ladder          143 ladder companies.
ambulance            about 450 FDNY-EMS and voluntary-hospital ambulances on tour.
mta_bus              5,800 buses in the MTA fleet, about 4,300 in weekday peak service.
box_truck            classification-count "Medium Truck" + "Heavy Truck".
van                  classification-count "Commercial Vehicle" (light commercial).
dsny_truck           about 2,100 DSNY collection trucks; per-borough intensity from the DSNY
                     collection-frequency map, on the day (06-14), evening (16-24) and, in the
                     Manhattan business districts, night (00-08) shifts.
cyclist, ebike       about 610,000 daily cycling trips (NYC DOT "Cycling in the City"); the
                     e-bike share of NYC cycling is taken at 30 %, dominated by delivery riding
                     and therefore weighted toward the evening.
moped                about 34,000 motorcycle/moped registrations in the five boroughs.
pedicab              850 pedicab registrations (DCWP cap); by law they operate in Midtown and
                     around Central Park only.
horse_carriage       68 licensed carriages (DCWP); by law they operate in Central Park and on
                     Central Park South, 10:00-21:00 (curfew, weather rules apply).
===================  =========================================================================

The taxi group's internal split (yellow / green / black car) is **not** assumed: it is measured from
the May 2025 TLC trip records, per borough, CBD flag and time band.
"""
from __future__ import annotations

import datetime as dt
import json
import logging
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import polars as pl

from ..manifest import git_commit
from .geo import BOROUGH_NAMES, NtaTable

log = logging.getLogger("nycsim.traffic.fleet_mix")

SCHEMA_VERSION = 1

CLASSES = ("sedan", "taxi", "boro_taxi", "black_car", "suv", "nypd", "fdny_engine", "fdny_ladder",
           "ambulance", "mta_bus", "box_truck", "dsny_truck", "van", "cyclist", "ebike", "moped",
           "pedicab", "horse_carriage")
GROUP_OF = {
    "sedan": "other", "suv": "other", "nypd": "other", "fdny_engine": "other", "fdny_ladder": "other",
    "ambulance": "other", "moped": "other", "horse_carriage": "other",
    "taxi": "taxi", "boro_taxi": "taxi", "black_car": "taxi",
    "box_truck": "truck", "dsny_truck": "truck", "van": "truck",
    "mta_bus": "bus",
    "cyclist": "bike", "ebike": "bike", "pedicab": "bike",
}
GROUPS = ("taxi", "truck", "bus", "bike", "other")

TIME_BANDS: dict[str, tuple[int, ...]] = {
    "night": (0, 1, 2, 3, 4, 5),
    "am_peak": (6, 7, 8, 9),
    "midday": (10, 11, 12, 13, 14, 15),
    "pm_peak": (16, 17, 18, 19),
    "evening": (20, 21, 22, 23),
}
BAND_OF_HOUR = {h: b for b, hs in TIME_BANDS.items() for h in hs}

REGIONS: tuple[tuple[int, bool, str], ...] = (
    (1, True, "Manhattan CBD (south of 60th St)"),
    (1, False, "Manhattan north of 60th St"),
    (2, False, "Bronx"),
    (3, False, "Brooklyn"),
    (4, False, "Queens"),
    (5, False, "Staten Island"),
)

# Published fleet figures.  ``vmt_km`` is the daily distance one vehicle of the class covers in the
# city; ``duty`` is the relative activity of the class in each time band (weekday).
@dataclass(frozen=True)
class FleetFacts:
    vehicles: float
    vmt_km: float
    duty: dict[str, float]
    basis: str
    boroughs: tuple[int, ...] = (1, 2, 3, 4, 5)
    cbd_only: bool = False
    cbd_factor: float = 1.0


FLEET: dict[str, FleetFacts] = {
    "sedan": FleetFacts(1_045_000, 18.0, {"night": 0.25, "am_peak": 1.20, "midday": 1.00, "pm_peak": 1.35, "evening": 0.60},
                        "NYS DMV: ~1.9 M private passenger vehicles registered in the five boroughs; 55 % car bodies",
                        cbd_factor=0.55),
    "suv": FleetFacts(855_000, 18.0, {"night": 0.25, "am_peak": 1.20, "midday": 1.00, "pm_peak": 1.35, "evening": 0.60},
                      "NYS DMV registrations, 45 % SUV/crossover bodies", cbd_factor=0.55),
    "taxi": FleetFacts(13_587, 180.0, {"night": 0.55, "am_peak": 1.15, "midday": 1.05, "pm_peak": 1.35, "evening": 0.95},
                       "13,587 TLC medallions", cbd_factor=3.2),
    "boro_taxi": FleetFacts(850, 150.0, {"night": 0.45, "am_peak": 1.25, "midday": 1.05, "pm_peak": 1.30, "evening": 0.85},
                            "green Street-Hail Livery: ~6,000 permits issued, ~850 active",
                            boroughs=(1, 2, 3, 4, 5), cbd_factor=0.05),
    "black_car": FleetFacts(100_000, 130.0, {"night": 0.60, "am_peak": 1.10, "midday": 0.95, "pm_peak": 1.30, "evening": 1.05},
                            "~100,000 TLC-licensed for-hire vehicles (~78,000 high-volume)", cbd_factor=1.6),
    "nypd": FleetFacts(9_000, 90.0, {"night": 0.85, "am_peak": 1.05, "midday": 1.10, "pm_peak": 1.05, "evening": 0.95},
                       "~9,000 NYPD vehicles across 77 precincts", cbd_factor=1.8),
    "fdny_engine": FleetFacts(198, 55.0, {"night": 0.70, "am_peak": 1.05, "midday": 1.15, "pm_peak": 1.15, "evening": 0.95},
                              "198 FDNY engine companies", cbd_factor=1.3),
    "fdny_ladder": FleetFacts(143, 50.0, {"night": 0.70, "am_peak": 1.05, "midday": 1.15, "pm_peak": 1.15, "evening": 0.95},
                              "143 FDNY ladder companies", cbd_factor=1.3),
    "ambulance": FleetFacts(450, 120.0, {"night": 0.80, "am_peak": 1.05, "midday": 1.15, "pm_peak": 1.10, "evening": 0.95},
                            "~450 FDNY-EMS and voluntary-hospital ambulances on tour", cbd_factor=1.4),
    "mta_bus": FleetFacts(4_300, 150.0, {"night": 0.30, "am_peak": 1.35, "midday": 1.05, "pm_peak": 1.35, "evening": 0.60},
                          "5,800 MTA buses, ~4,300 in weekday peak service", cbd_factor=1.2),
    "box_truck": FleetFacts(38_000, 60.0, {"night": 0.30, "am_peak": 1.35, "midday": 1.30, "pm_peak": 0.75, "evening": 0.30},
                            "classification counts: Medium + Heavy Truck; NYC commercial registrations", cbd_factor=1.1),
    "van": FleetFacts(115_000, 55.0, {"night": 0.25, "am_peak": 1.30, "midday": 1.35, "pm_peak": 0.85, "evening": 0.35},
                      "classification counts: Commercial Vehicle (light commercial)", cbd_factor=1.2),
    "dsny_truck": FleetFacts(2_100, 45.0, {"night": 0.55, "am_peak": 1.60, "midday": 1.20, "pm_peak": 0.75, "evening": 0.80},
                             "~2,100 DSNY collection trucks on day (06-14), evening (16-24) and Manhattan night shifts",
                             cbd_factor=1.3),
    "cyclist": FleetFacts(427_000, 3.0, {"night": 0.25, "am_peak": 1.35, "midday": 0.95, "pm_peak": 1.50, "evening": 0.70},
                          "NYC DOT: ~610,000 daily cycling trips; 70 % pedal cycles", cbd_factor=1.5),
    "ebike": FleetFacts(183_000, 3.6, {"night": 0.45, "am_peak": 0.95, "midday": 1.00, "pm_peak": 1.45, "evening": 1.35},
                        "NYC DOT: ~610,000 daily cycling trips; 30 % e-bikes, delivery-weighted", cbd_factor=1.8),
    "moped": FleetFacts(34_000, 12.0, {"night": 0.35, "am_peak": 1.00, "midday": 1.10, "pm_peak": 1.35, "evening": 1.05},
                        "~34,000 motorcycle/moped registrations in the five boroughs", cbd_factor=1.4),
    "pedicab": FleetFacts(850, 25.0, {"night": 0.15, "am_peak": 0.35, "midday": 1.30, "pm_peak": 1.60, "evening": 1.10},
                          "850 DCWP pedicab registrations, Midtown and Central Park only",
                          boroughs=(1,), cbd_only=False, cbd_factor=6.0),
    "horse_carriage": FleetFacts(68, 18.0, {"night": 0.00, "am_peak": 0.10, "midday": 1.40, "pm_peak": 1.50, "evening": 0.90},
                                 "68 DCWP-licensed carriages; Central Park and Central Park South, 10:00-21:00",
                                 boroughs=(1,), cbd_factor=4.0),
}

DSNY_PATH = "dsny_frequencies.geojson"
_DAY_TOKENS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")


def dsny_intensity_by_borough(path: Path) -> dict[int, float]:
    """Collection days per week summed over each borough's sanitation sections (relative truck load)."""
    if not path.exists():
        raise FileNotFoundError(f"{path} missing — run `python -m nycsim_pipeline.traffic.fetch`")
    import pyogrio
    gdf = pyogrio.read_dataframe(path, columns=["district", "freq_refuse", "freq_recycling", "freq_organics"],
                                 read_geometry=False)
    # DSNY district codes: MN Manhattan, BX Bronx, BK Brooklyn, QE/QW Queens East/West, SI Staten Island
    boro_of = {"MN": 1, "BX": 2, "BK": 3, "QE": 4, "QW": 4, "QN": 4, "SI": 5}
    out = {b: 0.0 for b in BOROUGH_NAMES}
    n_bad = 0
    for district, *freqs in zip(gdf["district"], gdf["freq_refuse"], gdf["freq_recycling"], gdf["freq_organics"]):
        b = boro_of.get(str(district)[:2].upper()) if district else None
        if b is None:
            n_bad += 1
            continue
        days = 0
        for f in freqs:
            if not f:
                continue
            s = str(f).lower()
            days += sum(1 for t in _DAY_TOKENS if t in s)
        out[b] += float(days)
    tot = sum(out.values())
    if tot <= 0:
        raise ValueError(f"{path}: no collection days parsed")
    log.info("DSNY: %d sections, collection days per week by borough %s (%d unparsed districts)",
             len(gdf), {BOROUGH_NAMES[k]: int(v) for k, v in out.items()}, n_bad)
    return {k: v / tot for k, v in out.items()}


def _population_weight(nta: NtaTable, landuse: pl.DataFrame) -> dict[tuple[int, bool], float]:
    """Residential units per borough × CBD flag — the base for private-vehicle and emergency activity."""
    lu = landuse.sort("nta_idx")["units"].to_numpy()
    out: dict[tuple[int, bool], float] = {}
    for b, cbd, _ in REGIONS:
        m = (nta.borocode == b) & (nta.is_cbd == cbd)
        out[(b, cbd)] = float(lu[m].sum())
    return out


def _taxi_split(tlc_by_service: dict[str, np.ndarray], nta: NtaTable) -> dict[tuple[int, bool, str], dict[str, float]]:
    """Measured yellow / green / high-volume-FHV split of for-hire vehicle-km per region and band."""
    name = {"yellow": "taxi", "green": "boro_taxi", "fhvhv": "black_car"}
    out: dict[tuple[int, bool, str], dict[str, float]] = {}
    for b, cbd, _ in REGIONS:
        m = (nta.borocode == b) & (nta.is_cbd == cbd)
        for band, hours in TIME_BANDS.items():
            vals = {name[s]: float(a[m][:, list(hours), 0].sum()) for s, a in tlc_by_service.items()}
            tot = sum(vals.values())
            out[(b, cbd, band)] = ({k: v / tot for k, v in vals.items()} if tot > 0
                                   else {"taxi": 0.2, "boro_taxi": 0.05, "black_car": 0.75})
    return out


def build_fleet_mix(nta: NtaTable, landuse: pl.DataFrame, tlc_by_service: dict[str, np.ndarray],
                    dsny_path: Path, share_stats: dict) -> dict:
    """Assemble the fleet-mix document (see the module docstring for the sources of every figure)."""
    dsny = dsny_intensity_by_borough(dsny_path)
    pop = _population_weight(nta, landuse)
    pop_tot = sum(pop.values()) or 1.0
    taxi_split = _taxi_split(tlc_by_service, nta)

    entries: list[dict] = []
    for b, cbd, region_name in REGIONS:
        pw = pop[(b, cbd)] / pop_tot
        for band in TIME_BANDS:
            vmt: dict[str, float] = {}
            for cls, f in FLEET.items():
                if b not in f.boroughs:
                    vmt[cls] = 0.0
                    continue
                base = f.vehicles * f.vmt_km * f.duty[band]
                if cls == "dsny_truck":
                    base *= dsny[b] * 5.0
                elif cls in ("sedan", "suv", "nypd", "fdny_engine", "fdny_ladder", "ambulance", "moped"):
                    base *= max(pw, 0.01) * 6.0
                elif cls in ("cyclist", "ebike"):
                    base *= max(pw, 0.01) * 6.0
                if cbd:
                    base *= f.cbd_factor
                elif f.cbd_only:
                    base = 0.0
                vmt[cls] = base
            split = taxi_split[(b, cbd, band)]
            tot_taxi = sum(vmt[c] for c in ("taxi", "boro_taxi", "black_car"))
            for c in ("taxi", "boro_taxi", "black_car"):
                vmt[c] = tot_taxi * split[c]
            total = sum(vmt.values())
            if total <= 0:
                raise ValueError(f"fleet mix: no activity for region {region_name} band {band}")
            share = {c: vmt[c] / total for c in CLASSES}
            within: dict[str, dict[str, float]] = {}
            for g in GROUPS:
                members = [c for c in CLASSES if GROUP_OF[c] == g]
                s = sum(share[c] for c in members)
                within[g] = ({c: share[c] / s for c in members} if s > 0
                             else {c: 1.0 / len(members) for c in members})
            entries.append({
                "borough": b, "borough_name": BOROUGH_NAMES[b], "cbd": bool(cbd), "region": region_name,
                "band": band, "hours": list(TIME_BANDS[band]),
                "share": {c: round(share[c], 6) for c in CLASSES},
                "within_group": {g: {c: round(v, 6) for c, v in within[g].items()} for g in GROUPS},
            })

    doc = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "git_commit": git_commit(),
        "classes": [{"index": i, "name": c, "group": GROUP_OF[c],
                     "fleet_vehicles": FLEET[c].vehicles, "daily_km_per_vehicle": FLEET[c].vmt_km,
                     "boroughs": list(FLEET[c].boroughs), "cbd_factor": FLEET[c].cbd_factor,
                     "basis": FLEET[c].basis}
                    for i, c in enumerate(CLASSES)],
        "groups": {g: [c for c in CLASSES if GROUP_OF[c] == g] for g in GROUPS},
        "time_bands": {b: list(h) for b, h in TIME_BANDS.items()},
        "regions": [{"borough": b, "cbd": bool(c), "name": nm} for b, c, nm in REGIONS],
        "usage": ("density.parquet gives taxi/truck/bus/bike shares per NTA and hour; pick the group from "
                  "those shares (the remainder is the 'other' group) and then the class inside the group "
                  "from within_group for the matching region and time band.  'share' is the standalone "
                  "unconditional mix for hosts that do not use the density table."),
        "dsny_collection_days_share_by_borough": {BOROUGH_NAMES[k]: round(v, 4) for k, v in dsny.items()},
        "taxi_split_source": "TLC yellow/green/high-volume-FHV trip records, May 2025, vehicle-km by region and band",
        "density_share_stats": share_stats,
        "mix": entries,
    }
    log.info("fleet mix: %d region × band entries, %d classes", len(entries), len(CLASSES))
    return doc


def write_fleet_mix(doc: dict, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w") as f:
        json.dump(doc, f, indent=1)
    tmp.replace(path)
    return path


def validate_fleet_mix(doc: dict) -> None:
    """Fail loudly on a malformed document (used by the tests and by the build)."""
    if doc.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"fleet_mix schema_version {doc.get('schema_version')} != {SCHEMA_VERSION}")
    names = [c["name"] for c in doc["classes"]]
    if tuple(names) != CLASSES:
        raise ValueError(f"fleet_mix class list {names} != VehicleClass.h order {list(CLASSES)}")
    if len(doc["mix"]) != len(REGIONS) * len(TIME_BANDS):
        raise ValueError(f"fleet_mix has {len(doc['mix'])} entries, expected {len(REGIONS) * len(TIME_BANDS)}")
    for e in doc["mix"]:
        s = sum(e["share"].values())
        if abs(s - 1.0) > 1e-4:
            raise ValueError(f"fleet_mix shares for {e['region']}/{e['band']} sum to {s}")
        if set(e["share"]) != set(CLASSES):
            raise ValueError(f"fleet_mix shares for {e['region']}/{e['band']} do not cover every class")
        for g, d in e["within_group"].items():
            gs = sum(d.values())
            if abs(gs - 1.0) > 1e-4:
                raise ValueError(f"fleet_mix within_group[{g}] for {e['region']}/{e['band']} sums to {gs}")
