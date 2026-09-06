# Traffic calibration — method

How `data/processed/traffic/density.parquet` (DATA_CONTRACTS §10), `traffic/fleet_mix.json` and
`data/processed/runtime/density.nycb` (§15) are produced, step by step, with the source of every
number and every assumption stated where it is made.

Entry points

```
python -m nycsim_pipeline.traffic.fetch     # download the extra inputs (idempotent, manifest-recorded)
python -m nycsim_pipeline.traffic.build     # the whole stage, ~7.5 min, peak RSS 1.5 GB
python -m nycsim_pipeline.traffic.report    # maps and tables into docs/verification/traffic_density/
PYTHONPATH=pipeline python -m pytest pipeline/tests/test_traffic_density.py
```

Code: `pipeline/nycsim_pipeline/traffic/` — `geo`, `segments`, `counts`, `landuse`, `accessibility`,
`model`, `speed`, `tlc`, `sidewalks`, `pedestrians`, `shares`, `fleet_mix`, `runtime_export`,
`build`, `report`.

---

## 0. Inputs

| id | dataset | used for |
|---|---|---|
| `traffic_volume_auto` | DOT Automated Traffic Volume Counts (`7ym2-wayt`), 1.87 M 15-min directional rows | hourly volume per lane |
| `centerline` | CSCL Street Centerline | lane-km, road class, posted speed, geometry |
| `pluto` | MapPLUTO, 857,347 lots | land-use regression features, pedestrian generators |
| `nta_2020` | 2020 Neighborhood Tabulation Areas, 262 polygons | the output geography |
| `taxi_zones` | TLC taxi zones, 263 polygons | TLC → NTA mapping |
| `subway_entrances` | MTA subway entrances, 2,120 placed | accessibility, pedestrian generators |
| `dot_vehicle_class_counts` | DOT Vehicle Classification Counts (`96ay-ea4r`) | truck and bus shares |
| `dot_ped_counts_biannual` | DOT Bi-Annual Pedestrian Counts (`cqsj-cfgu`), 114 sites | pedestrian calibration |
| `dot_bike_ped_hourly` / `dot_bike_ped_sensors` | DOT Bicycle and Pedestrian Counts (`ct66-47at`, `6up2-gnw8`) | bicycle volumes, pedestrian shape check |
| `plan_sidewalk`, `plan_public_plazas`, `ped_plazas` | CSCL planimetrics | sidewalk area (the pedestrian denominator) |
| `dsny_frequencies` | DSNY collection frequencies (`rv63-53db`) | DSNY truck intensity per borough |
| `tlc_yellow_2025_05`, `tlc_green_2025_05`, `tlc_fhvhv_2025_05` | TLC trip records, May 2025 | for-hire vehicle-km, journey speeds, activity shape |

May 2025 is the reference month: the most recent complete spring month in all three TLC files, and
spring is when DOT takes its own counts. Licences: NYC Open Data Terms of Use for everything from
`data.cityofnewyork.us`; the TLC trip records are published by the NYC Taxi and Limousine Commission
with attribution requested. All of it is recorded in `data/manifest/downloads.json` with SHA-256.

## 1. Geography (`geo.py`)

The 262 NTA-2020 polygons are reprojected to NYC_TM, repaired with `make_valid`, sorted by code and
indexed in an STRtree. 18 are flagged **CBD** (Manhattan, centroid south of the 60th Street line
West End Av/60th → York Av/60th); 65 are flagged **special** (`ntatype != 0`: parks, cemeteries,
airports, Rikers). Taxi zones get area-overlay weights onto NTAs (259 of 263 zones overlap at least
one NTA; EWR and a few water zones do not).

## 2. Road supply (`segments.py`)

CSCL is read with `pyogrio`, reprojected, and filtered to the vehicular types of DATA_CONTRACTS §7
(`rw_type` 1 street, 2 highway, 3 bridge, 4 tunnel, 9 ramp, 10 alley), excluding `trafdir == NV`
and zero-length geometry: **112,395 segments, 11,794 km of road, 21,220 lane-km**. Travel lanes and
posted speed come from CSCL where present and valid (lanes 1-12, speed 5-65 mph); otherwise a class
default is used and `lanes_source` / `speed_source` is set to 1 (1,691 and 12,306 segments). Each
segment is assigned to the NTA containing its midpoint (43 segments, 3.4 km, fall outside every NTA
and are dropped from the NTA aggregates).

## 3. Hourly volume per lane (`counts.py`)

DOT's ATR file holds 15-minute (a few requests: 10-minute) directional counts. Processing:

1. keep 2012-2026, `0 <= Vol <= 3000` per slot, valid `SegmentID` and `HH`;
2. drop US federal holidays (observed dates) plus the day after Thanksgiving, 24 and 31 December;
3. detect the slot length per `RequestID` from the distinct minute marks, require ≥ 75 % of an hour's
   slots to be present, and scale the partial hour up to a full hour;
4. sum over the directions counted in that hour;
5. average over days with recency weights — 2023-2026 × 1.0, 2019-2022 × 0.6, 2015-2018 × 0.4,
   2012-2014 × 0.25;
6. day type: 0 weekday, 1 Saturday, 2 Sunday.

Result: **93,653 segment × hour × day-type flows on 2,397 count sites** (321 last counted in
2023-2026). A site's coordinates come from its `WktGeom` (State Plane ft → NYC_TM).

## 4. Site matching and diurnal profiles (`model.py`)

A site is attached to a CSCL segment by `SegmentID == physicalid` when that segment lies within
150 m of the recorded point; otherwise to the nearest segment within 60 m whose normalised street
name matches; otherwise to the nearest segment within 25 m. **2,394 of 2,397 sites match, median
offset 1 m.** A two-way segment counted in one direction only is doubled (31,484 segment-hours),
which is the standard assumption of directional symmetry and is flagged in the summary.

Each site's **level** is the mean of its weekday hourly flows per travel lane (sites with fewer
than 18 observed weekday hours get no level: 1,616 of 2,394 qualify). The **profile** is a pooled
quantity, not a per-site ratio:

```
profile(h, d) = Σ_sites w · q_site(h, d)  /  Σ_sites w · level_site        (sites observed at h, d)
```

Dividing the sums rather than averaging per-site ratios keeps a single very quiet block from
multiplying an hour it happens to be the only observer of. Profiles are pooled by area cluster —
`cbd` (16 NTAs), `manhattan` (16), `commercial` (46), `industrial`, `residential` (119),
`special` (65) — for surface streets, and city-wide for freeways and ramps, with a documented
fallback chain when a cluster has fewer than 8 sites (`industrial` has none of its own and is
pooled from `residential`). Each profile is renormalised so its weekday daily mean is exactly 1 and
clipped at 4× that mean.

## 5. The level model — two stages, and where the R² comes from

**Stage 1, road class.** `log(level)` at the 1,616 usable sites is regressed (weighted ridge, λ = 2,
weights √(observed weekday hours) × 1.0 recent / 0.6 older) on the segment's own attributes:
`log(travel lanes)`, highway / ramp / bridge-tunnel flags, posted speed, two-way flag, truck-route
flag, `log(kerb-to-kerb width)` and an avenue/boulevard name flag.

> **R² = 0.271, leave-one-out R² = 0.260, n = 1,616, rmse(log) = 0.844.**

**Stage 2, land use.** The stage-1 residuals are averaged per NTA (weighted) into an **NTA effect**,
and that effect is regressed on land use and accessibility. The candidate list is the 19 features in
`model.nta_feature_matrix` — PLUTO floor-area FARs by use, dwellings per km², lot-use shares, lane-km
density, highway / arterial / truck-route lane shares, borough flags, subway-entrance density and
distance, distance to the Manhattan core, expressway lane-km within 3 km, and PLUTO garage area per
dwelling. Six were selected by forward selection on the leave-one-out R² and are fixed in
`model.STAGE2_FEATURES`:

| feature | β (standardised) |
|---|---|
| intercept | −0.011 |
| `log_office_far` | +0.089 |
| `log_garage_per_unit` | +0.126 |
| `truck_route_share` | −0.112 |
| `log_d_cbd_km` | −0.085 |
| `arterial_lane_share` | −0.093 |
| `highway_lane_share` | +0.075 |

> **R² = 0.206, leave-one-out R² = 0.158, n = 227 NTAs, rmse(log) = 0.379, ridge λ = 4.**

**Combined, at NTA level.** Predicting each NTA's observed mean log level from the model:

> **R² = 0.303 with road class alone, R² = 0.447 once the land-use NTA effect is added (227 NTAs).**

The ceiling on that number is set by sampling noise, not by the model: the median within-NTA
residual standard deviation is 0.66 in log units over the NTAs with at least four sites, and the
median NTA has six sites, so roughly a third of the between-NTA variance of the observed mean is
noise in the observation itself. Section "Honest limits" in REPORT.md says what this means.

**Blending.** An NTA with sites uses `(W·effect_obs + k₀·effect_pred) / (W + k₀)` where `W` is the
total site weight and `k₀` the median weight of one site; an NTA with no sites uses the prediction,
clipped to the 2nd-98th percentile of the observed effects. 227 NTAs have their own counts,
**31 are filled from the regression**, 4 have no roads at all.

**Assembly.** Every one of the 112,395 segments gets
`level = exp(stage1(x_segment) + effect(NTA))`, its hourly flow is `level × profile`, and the NTA
value is the lane-km weighted mean over its segments.

## 6. Speed model and the flow → density conversion (`speed.py`)

Density is derived: `k = q / v`, and `v` must be a **space-mean journey speed** including signal,
queue and kerb delay, because the vehicles waiting at a red light are on the lane and count. Per
road class the speed falls linearly from a free-flow anchor to a speed-at-capacity anchor:

```
v_c(q) = v_free_c − (v_free_c − v_cap_c) · min(q / q_cap_c, 1)
k      = min(q / v_c(q), k_jam),      k_jam = 130 veh/km/lane
```

This is the linear (Greenshields) family written with the two anchors that are actually published.
`k_jam` = 130 veh/km/lane is 7.7 m per vehicle at a standstill (4.9 m mean length over the NYC fleet
including vans, trucks and buses, plus a 2.8 m stopped gap).

**Assumed free-flow speeds** (lane-km weighted over the network as built):

| class | segments | lane-km | mean posted | **v_free** | v at capacity | q_cap | k at capacity |
|---|---|---|---|---|---|---|---|
| freeway / expressway | 4,126 | 1,900 | 77.2 km/h | **88.5 km/h** (55 mph) | 46.7 km/h | 2,100 veh/h/ln | 44.9 veh/km/ln |
| ramp | 3,567 | 490 | 49.6 km/h | **48.3 km/h** (30 mph) | 26.6 km/h | 1,800 veh/h/ln | 67.8 veh/km/ln |
| arterial (≥ 3 lanes or truck route) | 23,227 | 5,524 | 43.5 km/h | **27.0 km/h** (0.62 × posted) | 10.9 km/h | 900 veh/h/ln | 84.5 veh/km/ln |
| two-way street | 47,153 | 8,617 | 39.5 km/h | **23.7 km/h** (0.60 × posted) | 9.9 km/h | 750 veh/h/ln | 76.6 veh/km/ln |
| one-way local | 34,322 | 4,688 | 40.2 km/h | **23.3 km/h** (0.58 × posted) | 9.6 km/h | 650 veh/h/ln | 67.6 veh/km/ln |

Sources: HCM 7th ed. basic freeway segment (capacity 2,250 pc/h/ln at 55 mph FFS, 45 pc/km/ln at
capacity — derated to 2,100 veh/h/ln for the NYC fleet); HCM ramp roadways (1,900-2,000 veh/h/ln,
derated); HCM urban street facilities (base saturation flow 1,900 veh/h/ln × a typical NYC through
`g/C` of 0.45-0.50 → 855-950 veh/h/ln). The surface free-flow **travel** speeds are a fraction of the
posted speed because they already contain intersection delay; those fractions are the NYC-specific
part and are re-calibrated per NTA and hour (next paragraph), so the table above is the starting
point, not the answer.

**Calibration against real speeds.** The TLC trip records give an observed door-to-door speed for
every taxi zone, hour and day type. Only trips of at most 3 km are used, so the trip stays on the
surface streets around the pick-up zone instead of an airport run over the expressways inflating it
(Midtown zones, weekday: 22.5 km/h at 00:00 and 12.0 km/h at 16:00 with no cap; 16.4 and 8.9 km/h
with it — the second pair is what the NYC DOT Mobility Report shows for the Midtown core). The
multiplier that brings the modelled lane-km-weighted harmonic-mean surface speed onto the observed
one is applied to the surface classes, clipped to [0.30, 1.60]:

> **15,956 of 18,864 cells calibrated from their own TLC speed, 2,908 from the borough-hour median,
> 0 left uncalibrated. Multiplier p05 / median / p95 = 0.56 / 0.75 / 0.93.**

Freeway, ramp and bridge speeds are *not* multiplied — a taxi journey speed is a surface-street
quantity.

## 7. Pedestrians (`sidewalks.py`, `pedestrians.py`)

The DOT Bi-Annual Pedestrian Counts are reachable, so they are the calibration target, not a
fallback. 114 screenline locations, weekday windows AM 07:00-09:00, MD 12:00-14:00, PM 16:00-19:00;
the 14 East-/Harlem-River bridge sites are excluded (they are not sidewalks), leaving **99 street
sites**. The six most recent seasons are averaged and converted to pedestrians per hour.

1. **Denominator.** 50,865 planimetric sidewalk polygons plus public and DOT pedestrian plazas are
   overlaid on the NTAs: **57.06 km² of mapped sidewalk**, of which **35.95 km² is walkable**. The
   0.63 walkable fraction is the NYC DOT Street Design Manual's pedestrian clear path: the kerbside
   furnishing zone (~1.2 m) and the frontage zone (~0.5 m) of a typical 4.6 m NYC sidewalk carry
   trees, hydrants, racks, bins and shed legs, not walking traffic.
2. **Level (where).** `log(pedestrians/h)` at the 99 sites is regressed on the local land-use
   generators — retail, office, commercial and residential floor area, dwellings and subway
   entrances summed over a 900 m box on a 100 m raster — plus the CBD flag.
   > **R² = 0.694, leave-one-out R² = 0.639, n = 99, rmse(log) = 0.488.**
   > β: retail +0.407, office +0.202, commercial −0.030, residential +0.065, dwellings +0.134,
   > subway entrances +0.195, CBD −0.154.
   The fitted model is evaluated at the midpoint of every CSCL segment, so an NTA's average is an
   average over its quiet blocks as well as its busy ones.
3. **Shape (when).** Three windows are not a 24-hour curve, and the eight permanent DOT pedestrian
   counters are all greenway/bridge sites (Willis Ave, High Bridge, Emmons Ave, Concrete Plant
   Park), so their shape is recreational. The hourly shape is therefore taken from TLC pick-ups per
   zone, hour and day type — a real, citywide, hourly measure of street activity — corrected once,
   city-wide, by the factor that reproduces the AM : MD : PM ratios the DOT counts show (observed
   0.668 : 1.108 : 1.224, TLC 1.022 : 0.868 : 1.110, correction 0.654 : 1.277 : 1.102, interpolated
   periodically between the 08:00 / 13:00 / 17:30 anchors). 758 of 786 NTA × day-type shapes come
   from that NTA's own TLC activity; the rest are pooled by borough.
4. **Density.** Little's law: a screenline flow `F` (ped/h, both directions and both sidewalks) on a
   block of length `L` puts `F·L / v_walk` pedestrians on that block at any instant.
   `v_walk` = 1.34 m/s (Fruin 1971 / HCM free-flow walking speed), inflated by 1.15 for time spent
   standing at kerbs, signals and shopfronts. Summed over the NTA's segments and divided by its
   walkable sidewalk area. Capped at 6 ped/m² (Fruin LOS F).

**Independent check.** The permanent counters were not used to build the shape, so they are a free
validation: the correlation between the modelled citywide hourly shape and the counters' own is
**0.953 on weekdays**, 0.728 Saturday, 0.833 Sunday.

## 8. Modal shares (`shares.py`)

`veh_per_km_lane` counts **motor vehicles** on travel lanes — what the ATR counters measure. The four
shares are fractions of the **road-user stream on those lanes** (motor vehicles + bicycles); the four
categories are disjoint so they sum to at most 1, and the remainder is private cars, SUVs,
motorcycles and emergency vehicles. A cell whose four shares would exceed 0.97 is rescaled (this
never fired in the current build).

**`taxi_share` — TLC trip records.** "Taxi" means the whole population that behaves like a taxi:
yellow medallion + green SHL + high-volume FHV. `fleet_mix.json` splits it into `taxi` / `boro_taxi`
/ `black_car`. Trip kilometres are spread along the **corridor** between the pick-up and drop-off
zone centroids, cut by the NTA boundaries the line crosses, and within a corridor split by
*length × that NTA's own modelled vehicle-km* — a for-hire trip drives where the traffic drives, so
a straight line across a cemetery hands its kilometres to the neighbouring streets. (Splitting half
to each endpoint instead made Greenpoint 72 % for-hire at midnight and put four cemeteries in the
top ten; the corridor allocation removes both artefacts.) Intra-zone trips are spread over the
zone's own NTAs by area. Revenue kilometres are divided by the published occupancy ratio to recover
total for-hire kilometres — yellow/green 0.60, high-volume FHV 0.62 (TLC Factbook, Schaller
Consulting *The New Automobility* 2018, and the TLC's 2019 FHV congestion rulemaking, which measured
41 % of Manhattan-CBD FHV mileage without a passenger). The share is capped at 0.75.

**`truck_share`, `bus_share` — DOT Vehicle Classification Counts.** 1,453 segments in the file,
**851 matched to CSCL** (by `physicalid`, then through the ATR site table, which shares DOT's
`SegmentID` space). Classes are grouped: `Auto(s)` → auto, `Taxi(s)` → taxi, `Commercial`,
`Commercial Vehicle`, `Medium Truck`, `Heavy Truck`, `Trucks` → truck (the simulation's `van`,
`box_truck` and `dsny_truck` bodies), `School Bus`, `Other Bus` → bus. Shares are tabulated by road
class × hour × day type; DOT takes these counts almost exclusively on weekdays (8.36 M vehicles on
weekdays, none on Saturdays or Sundays), so Saturday and Sunday inherit the weekday shares — stated
as a gap. Each NTA gets a multiplier from its own sites when it has at least three (130 NTAs),
shrunk toward its cluster's multiplier; the rest take the cluster multiplier outright.

**`bike_share` — DOT bicycle counters.** The classification counts have no bicycle class. 29
permanent DOT counters with hourly volumes since 2024 are placed on CSCL segments and
`log(bikes/h)` is regressed on protected-bike-lane and bike-lane flags, local commercial floor area,
local dwellings, CBD and Manhattan flags (**R² = 0.420, LOO R² = 0.162, n = 29**). The counters all
sit on cycle routes, so the fitted *level* over-states an ordinary street; the spatial pattern is
kept and the absolute level is anchored on the published citywide volume — NYC DOT *Cycling in the
City*, about 610,000 daily cycling trips, at a 3.0 km mean trip length = 1.83 M bike-km/day, a
scale factor of 0.655. The diurnal shape comes from the counters themselves (weekday peak 2.19× the
daily mean at 17:00).

## 9. `fleet_mix.json` (`fleet_mix.py`)

Every one of the 18 `core/traffic/VehicleClass.h` classes gets a share for each of 6 regions
(Manhattan CBD, Manhattan north of 60th, Bronx, Brooklyn, Queens, Staten Island) × 5 time bands
(night 00-05, am_peak 06-09, midday 10-15, pm_peak 16-19, evening 20-23) — 30 entries.

Each class carries a published fleet figure, an assumed daily distance per vehicle and a duty cycle
per band; the product is a vehicle-km weight. Region scaling: private cars, emergency and cycling
classes are scaled by the region's residential units, DSNY by the region's share of DSNY collection
days (Manhattan 0.138, Bronx 0.113, Brooklyn 0.359, Queens 0.331, Staten Island 0.059, parsed from
the 610 sanitation sections' `freq_refuse`/`freq_recycling`/`freq_organics` day lists), and each
class carries an explicit CBD factor. Legal restrictions are enforced, not assumed away: pedicabs
and horse carriages exist only in Manhattan, and the carriage duty cycle is zero in the night band
(the 21:00 curfew).

Two views are written per entry:

* `within_group` — the split inside each of the five groups (taxi, truck, bus, bike, other). This is
  what a host using `density.parquet` needs: the density cell says what share of the stream is
  for-hire, commercial, bus or bicycle; this says which class inside that group to spawn.
* `share` — the unconditional mix, `within_group` multiplied by the group shares the **density table
  itself** reports for that region and band (vehicle-count weighted over the region's NTAs and the
  band's hours). The two views are consistent by construction.

The taxi group's internal split is not assumed at all: it is measured from the May 2025 TLC records
per region and band (Manhattan CBD midday: 23 % yellow, 0.06 % green, 77 % high-volume FHV; Staten
Island midday: 0.5 % / 0.03 % / 99.5 %).

## 10. Outputs and the runtime binary (`build.py`, `runtime_export.py`)

`density.parquet` carries exactly the DATA_CONTRACTS §10 columns in order —
`nta_code, hour, dow, veh_per_km_lane, ped_per_m2_sidewalk, taxi_share, truck_share, bus_share,
bike_share, source` — with Parquet metadata `nycsim.schema = traffic/density@1`. Everything
diagnostic (flow, speed, vehicle-km, pedestrian counts, TLC speed, calibration factor, lane-km,
site counts, NTA effects, cluster, borough) goes into the sibling `density_detail.parquet` so the
contract file stays exact. `source` per NTA is one of `atr_recent`, `atr_mixed`, `atr_older`,
`landuse_model`, `no_roads`.

Before anything is written, `build._validate` checks: column order, 262 × 24 × 3 = 18,864 rows,
unique keys, the NTA code set, hour and day-type ranges, no non-finite or negative values, every
share ≤ 1, the share sum ≤ 1, `veh_per_km_lane` ≤ `k_jam`, and a non-null `source`.

`runtime/density.nycb` is written through `nycsim_pipeline.runtime.nycb` (foundation code owned by
the roads stage — this stage only lays out the records) in the exact layout
`core/src/traffic/Density.cpp::loadFromNycb` reads: `cells` (32 bytes: `uint32 nta_str`,
`uint8 hour`, `uint8 dow`, `uint16 pad`, six `float`s at offsets 8, 12, 16, 20, 24, 28),
`nta_polys` (12 bytes), `vertices` (12 bytes, `z = 0`) and `strtab`. Exterior rings only, simplified
to 5 m and dropping parts under 2,000 m² — `pointInNta` ray-casts closed rings and would not honour
holes anyway. The file is read back and compared against the dataframe by
`runtime_export.verify_density_nycb` on every build.
