# Stage report — street furniture, vegetation and transit

**Stages:** `furniture` (`pipeline/nycsim_pipeline/furniture/`) and `transit` (`pipeline/nycsim_pipeline/transit/`)
**Run date:** 2026-09-06 · **Environment:** the shared 4 vCPU container (load average 20–28 from concurrent agents)
**Contracts implemented:** DATA_CONTRACTS §8 (Furniture), §9 (Transit), §15 (`runtime/transit.nycb`)

---

## 1. What was built

### 1.1 Code

| File | Purpose |
|---|---|
| `pipeline/nycsim_pipeline/furniture/allometry.py` | (pre-existing) species → tree height curve |
| `pipeline/nycsim_pipeline/furniture/catalog.py` | (pre-existing, **extended**) prop-kind enum; kinds 31–33 and `Z_SOURCE` 3/4 added |
| `pipeline/nycsim_pipeline/furniture/schema.py` | **new** — Arrow schema of `props.parquet` |
| `pipeline/nycsim_pipeline/furniture/trees.py` | **new** — 2015 Street Tree Census loader (alive only) |
| `pipeline/nycsim_pipeline/furniture/datasets.py` | **new** — every other furniture dataset → prop rows |
| `pipeline/nycsim_pipeline/furniture/elevation.py` | **new** — ground model from surveyed elevation points |
| `pipeline/nycsim_pipeline/furniture/dedupe.py` | **new** — cross-dataset 1.5 m de-duplication |
| `pipeline/nycsim_pipeline/furniture/rules.py` | **new** — rule-based lamps / manholes / steam vents |
| `pipeline/nycsim_pipeline/furniture/build.py` | **new** — stage driver (`python -m nycsim_pipeline furniture`) |
| `pipeline/nycsim_pipeline/transit/entrances.py` | (pre-existing) MTA subway entrance normaliser |
| `pipeline/nycsim_pipeline/transit/gtfs.py` | **new** — GTFS reader, service-day resolution, headways |
| `pipeline/nycsim_pipeline/transit/structures.py` | **new** — rail structures with measured deck heights |
| `pipeline/nycsim_pipeline/transit/ferry.py` | **new** — ferry feed sources, download, landing merge |
| `pipeline/nycsim_pipeline/transit/build.py` | **new** — stage driver (`python -m nycsim_pipeline transit`) |
| `pipeline/tests/test_furniture.py` | **new** — 44 tests (unit + contract integration) |

### 1.2 Data artefacts

| Artefact | Rows | Size |
|---|---:|---:|
| `data/processed/tiles/{tile}/props.parquet` (1,576 tiles) | 1,724,589 | 88.7 MB |
| `data/processed/furniture/props_catalog.json` | 34 kinds | — |
| `data/processed/furniture/build_summary.json`, `tiles_index.json` | — | — |
| `data/processed/transit/bus_routes.parquet` | 345 | 5.4 MB |
| `data/processed/transit/bus_stops.parquet` | 13,364 | 0.58 MB |
| `data/processed/transit/subway_entrances.parquet` | 2,120 | 92 kB |
| `data/processed/transit/rail_structures.parquet` | 8,341 | 3.0 MB |
| `data/processed/transit/ferry_routes.parquet` | 6 | 18 kB |
| `data/processed/transit/ferry_terminals.parquet` *(contract extension)* | 27 | 4.2 kB |
| `data/processed/transit/rail_routes.parquet` *(contract extension)* | 47 | 4.4 MB |
| `data/processed/transit/rail_stops.parquet` *(contract extension)* | 1,166 | 40 kB |
| `data/processed/runtime/transit.nycb` + `transit.layout.json` | see §5 | 2.37 MB |

Every artefact is recorded in `data/manifest/processed.json` with SHA-256, row count, stage, git commit and source ids.

---

## 2. Furniture — counts by prop kind

1,724,589 props. `source = 0` (a published dataset record) **1,178,780 (68.4 %)**; `source = 1` (rule placement)
**545,809 (31.6 %)**.

| kind | name | count | source | provenance |
|---:|---|---:|---|---|
| 0 | tree | 650,516 | dataset | 2015 Street Tree Census `uvpi-gqnh` |
| 23 | manhole | 288,174 | 623 OSM + 287,551 rule | OSM `man_made=manhole` + `rule:manhole_40m` |
| 14 | street_lamp | 273,781 | 16,938 OSM + 256,843 rule | OSM `highway=street_lamp` + `rule:lamp_30_40m_alt` |
| 9 | curb_ramp | 216,339 | dataset | DOT Pedestrian Ramps `ufzp-rrqu` |
| 1 | hydrant | 109,724 | dataset | DEP hydrants `5bgh-vtsn` |
| 28 | cooling_tower | 81,684 | dataset | Planimetric Cooling Towers `x748-37q7` |
| 11 | bench | 21,086 | dataset | OSM `amenity=bench` |
| 29 | swimming_pool | 17,989 | dataset | Planimetric Swimming Pools `6uj9-35vn` |
| 24 | bus_stop_sign | 13,341 | dataset | one per GTFS bus stop |
| 6 | bike_rack | 9,864 | dataset | OSM `amenity=bicycle_parking` |
| 31 | subway_vent_grate | 7,448 | dataset | Planimetric Railroad Structure `dwer-xbgx` code 2470 |
| 12 | waste_basket | 5,611 | dataset | OSM `amenity=waste_basket` |
| 30 | misc_structure | 4,335 | dataset | Planimetric Misc Structures `92m5-3pwp` |
| 2 | bus_shelter | 3,380 | dataset | Bus Stop Shelters `t4f2-8md7` |
| 7 | citibike_dock | 2,507 | dataset | Citi Bike GBFS (`capacity` = real dock count) |
| 13 | mailbox | 2,318 | dataset | OSM `amenity=post_box` |
| 3 | linknyc | 2,251 | dataset | LinkNYC `s4kf-3yrf` |
| 8 | subway_entrance | 2,110 | dataset | MTA `i9wp-a4ja` (lines + globe colour) |
| 21 | flagpole | 1,655 | dataset | OSM `man_made=flagpole` |
| 18 | drinking_fountain | 1,645 | dataset | OSM `amenity=drinking_water` |
| 27 | parks_building | 1,487 | dataset | Parks Structures `n8q6-i44s` |
| 33 | steam_vent | 1,402 | **rule** | `rule:steam_vent_400m_manhattan_below_96` |
| 20 | vending_machine | 1,003 | dataset | OSM `amenity=vending_machine` |
| 16 | artwork | 956 | dataset | OSM `tourism=artwork` |
| 22 | utility_pole | 924 | dataset | OSM `man_made=utility_pole` |
| 17 | memorial | 860 | dataset | OSM `historic=memorial` |
| 25 | parks_comfort_station | 715 | dataset | Parks Structures (public restroom) |
| 10 | rtpi_sign | 491 | dataset | RTPI signs `g9jx-npbk` |
| 4 | newsstand | 360 | dataset | Newsstands `w9zq-xm8b` |
| 15 | billboard | 292 | dataset | OSM `advertising=billboard` |
| 32 | subway_emergency_exit | 189 | dataset | Planimetric Railroad Structure code 2480 |
| 19 | payphone | 102 | dataset | OSM `amenity=telephone` + 4 LinkNYC payphone sites |
| 26 | parks_recreation_center | 33 | dataset | Parks Structures (recreation centre) |
| 5 | bike_shelter | 17 | dataset | Bicycle Parking Shelters `dimy-qyej` |

`props_catalog.json` carries all 34 kinds with their category, description, dataset provenance, nominal
dimensions **and the source of those dimensions**, the `variant`/`text`/`heading` meanings and these counts.

### 2.1 Street trees (2015 census)

| | |
|---|---:|
| rows in the census | 683,788 |
| **alive, placed** | 652,173 |
| dead — excluded | 13,961 |
| stumps — excluded | 17,654 |
| other/blank status | 0 |
| alive rows without coordinates (dropped) | 0 |
| alive rows without a species name | 5 |
| alive rows with `tree_dbh = 0` (`dbh_cm = 0`, height uses the 5 cm sapling default) | 222 |
| distinct species/genus labels | 133 |
| duplicate census rows removed by the 1.5 m de-duplication | 1,657 |
| **trees in `props.parquet`** | **650,516** |

Top ten species (living street trees):

| # | Latin | Common | Count | Share |
|---:|---|---|---:|---:|
| 1 | *Platanus × acerifolia* | London planetree | 87,014 | 13.3 % |
| 2 | *Gleditsia triacanthos* var. *inermis* | honeylocust | 64,263 | 9.9 % |
| 3 | *Pyrus calleryana* | Callery pear | 58,931 | 9.0 % |
| 4 | *Quercus palustris* | pin oak | 53,185 | 8.2 % |
| 5 | *Acer platanoides* | Norway maple | 34,189 | 5.2 % |
| 6 | *Tilia cordata* | littleleaf linden | 29,742 | 4.6 % |
| 7 | *Prunus* (genus only in the census) | cherry | 29,279 | 4.5 % |
| 8 | *Zelkova serrata* | Japanese zelkova | 29,258 | 4.5 % |
| 9 | *Ginkgo biloba* | ginkgo | 21,024 | 3.2 % |
| 10 | *Styphnolobium japonicum* | Sophora (pagoda tree) | 19,338 | 3.0 % |

Species and DBH are **measured**; height is **estimated** by `allometry.py`
(`h = 1.37 + H_max(species)·(1 − e^(−k·DBH_cm))`) and every tree row carries `height_source = 1`.
Resulting heights: min 2.35 m, max 31.37 m, mean 12.55 m.

### 2.2 De-duplication across datasets (1.5 m)

`dedupe.py` compares rows only inside a *dedupe group* — the kinds that can describe the same physical object —
so a hydrant 1 m from a tree is never merged. Groups: `bike_parking` = {bike_rack, citibike_dock, bike_shelter},
`phone_kiosk` = {linknyc, payphone}; every other kind is de-duplicated against itself. The authority dataset beats
OpenStreetMap, and OpenStreetMap beats a rule placement.

* 7,897 pairs within 1.5 m · **5,373 rows dropped** · 1,724,589 kept.
* Largest groups of drops: duplicate census trees 1,657; duplicate DOT ramp records 1,340; overlapping cooling-tower
  polygons 638; duplicate OSM benches 388; rule manholes colliding with each other 326; rule lamps 210;
  OSM bike parking merged into another bike-parking row 204.

### 2.3 Rule-based fill (`source = 1`, 545,809 rows)

`data/processed/roads/segments.parquet` **was** available (122,235 CSCL segments, produced by the roads stage
before this run), so the road-derived fill ran. Every rule is deterministic (offsets hashed from `segment_id`) and
is suppressed where a surveyed/mapped object already exists.

| rule | kind | generated | suppressed | kept | spec |
|---|---|---:|---:|---:|---|
| `rule:lamp_30_40m_alt` | street_lamp | 267,162 | 10,109 | **257,053** | every 30–40 m, alternating sides, on `rw_type` ∈ {street, highway, bridge, alley} with `width_m ≥ 9`; offset `width/2 + 0.6 m` from the centreline; suppressed within 25 m of an OSM `highway=street_lamp` |
| `rule:manhole_40m` | manhole | 288,104 | 214 | **287,890** | every 40 m on the centreline of the same classes; suppressed within 15 m of an OSM `man_made=manhole` |
| `rule:steam_vent_400m_manhattan_below_96` | steam_vent | 1,402 | 0 | **1,402** | every 400 m along streets ≥ 9 m wide in Manhattan south of 96th St (`y ≤ 10,438.8 m` NYC_TM), the Con Edison steam district |

Cross-check against reality: NYC DOT maintains on the order of 250,000 street lights; the rule produces 257,053
plus 16,938 mapped ones. The manhole and steam-vent counts are **modelling choices, not measurements** — no
citywide dataset of either exists.

### 2.4 Prop elevation (`z`, `z_source`)

The per-tile terrain rasters did not exist when this stage ran, so props are placed on a ground model built from
**measured** points: 376,133 planimetric spot elevations (`plan_elevation_points`, `sub_code` 300000 — roadbed and
interior-sidewalk survey points, exactly where street furniture stands) plus 1,083,026 LiDAR building grades from
`buildings_base.parquet`. `z` is the inverse-distance-weighted mean of the 4 nearest reference points.

| `z_source` | meaning | rows |
|---:|---|---:|
| 3 | spot elevation / building grade IDW, nearest ≤ 80 m | 1,712,547 (99.30 %) |
| 4 | same, nearest > 80 m (extrapolated: piers, runways, open water) | 10,083 (0.58 %) |
| 1 | elevation published by the dataset itself (Parks structures) | 1,959 (0.11 %) |
| — | missing | **0** |

---

## 3. Transit

### 3.1 Bus (GTFS, service day Wednesday 2026-09-09)

| | |
|---|---:|
| feeds read | NYCT Manhattan / Bronx / Brooklyn / Queens / Staten Island + MTA Bus Company |
| **routes** | **345** (253 MTA NYCT, 92 MTA Bus Company) |
| routes by borough (0 = MTA Bus Company / multi-borough) | 0: 92 · 1 MN: 41 · 2 BX: 46 · 3 BK: 68 · 4 QN: 40 · 5 SI: 58 |
| **stops** | **13,364** |
| stops with a DOT shelter within 15 m | **2,561** (19.2 % — 3,381 shelters exist citywide) |
| route length, longest shape per route, summed | 5,374.5 km |
| weekday route-hours with scheduled service | 6,686 |
| headway across those hours | median 15 min, p10 8 min, p90 40 min |
| stop `z` range (NAVD88) | −1.87 m … 106.96 m |

`headway_min[h] = round(60 · D / T)`, *T* = trips of the route whose **first departure** falls in hour *h*,
*D* = distinct `direction_id` among them. `0` = no scheduled departure in that hour. Spot check: M101 rush hour
4–9 min, B41 3–5 min, B44 SBS 8–10 min — matching the published MTA timetables.

### 3.2 Subway entrances

2,120 entrances from the MTA 2024 dataset (`i9wp-a4ja`), each with its `lines` bullet list and globe colour:

* by kind: **1,990 stair**, 102 elevator, 28 escalator;
* globes: **1,636 green** (entry allowed), **40 red** (exit only), 444 none (elevators, station houses, in-building
  easements);
* 100 % carry at least one line bullet.

Globe rule used: an outdoor stair/escalator opening with "Entry Allowed = YES" gets a green globe, one with entry
refused but exit allowed gets a red globe. The dataset publishes no opening hours, so a *part-time* entrance that
allows entry is shown green — the one place where the globe colour is a rule rather than a record.

### 3.3 Rail structures (elevated km)

8,341 structure segments, **986.2 track-kilometres** (the planimetric layer is per-track, not per-route).

| kind | rows | track-km | deck height measured | median deck height |
|---|---:|---:|---:|---:|
| **elevated** | 3,914 | **492.2** (393.5 planimetric + 98.7 OSM-only) | 2,475 | **6.79 m** |
| **viaduct** | 72 | **12.9** | 70 | **11.72 m** |
| embankment | 2,689 | 314.7 | 1,505 | 5.01 m |
| open cut | 1,666 | 166.5 | n/a (track below grade) | n/a |
| **elevated + viaduct** | 3,986 | **505.0 km** | | |

Deck heights are **measured** where the City surveyed them: planimetric *Bridge Elevation* points
(`sub_code` 300020, 11,433 of them) give the deck elevation and the ground model gives the ground beneath;
4,050 of the 6,675 above-grade structures (60.7 %) got a measured height. 171 measurements were rejected as
implausible for their class (the nearby bridge points belonged to a road structure crossing the track) and
2,625 structures with no usable bridge point fall back to the **median measured height of their own class**
(`deck_height_source = 1`). Open-cut track carries `deck_height_source = 2` and a NaN height.

The measured median of 6.79 m for elevated track matches the real NYC "el" (rail level ~20–22 ft above the street);
the viaduct median of 11.72 m and the Culver Viaduct rows at 20–23 m match the real structure.

### 3.4 Ferries

| route | operator | headway (weekday) | primary shape |
|---|---|---|---:|
| `SIF` Staten Island Ferry | NYC DOT | 30 min overnight, 15–17 min peak | 8.13 km (St George ↔ Whitehall) |
| `AS` Astoria | NYC Ferry | 30–60 min | 14.77 km |
| `ER` East River | NYC Ferry | 12–13 min peak | 9.23 km |
| `RS` Rockaway‑Soundview | NYC Ferry | 30–60 min | 56.11 km |
| `SB` South Brooklyn | NYC Ferry | 30–60 min | 11.60 km |
| `SG` St. George | NYC Ferry | 20–60 min | 28.27 km |

**Both operators come from real GTFS feeds — no terminal coordinate is hand-typed.** 27 landings in
`ferry_terminals.parquet`, including St. George Ferry Terminal, Whitehall Ferry Terminal, Wall St/Pier 11,
Midtown West 39th St‑Pier 79, Hunters Point South, Roosevelt Island, Gov. Island/Yankee Pier, Rockaway, Soundview,
Ferry Point Park and Battery Park City/Vesey St.

The Staten Island Ferry feed leaves `direction_id` empty and separates the two directions by `shape_id`; the reader
detects that and uses `shape_id` as the direction key, which is what makes the SIF headways come out at the real
30 min overnight instead of 15.

### 3.5 Subway / commuter-rail routes (contract extension)

`rail_routes.parquet`: 47 routes — 28 subway services + Staten Island Railway, all 12 LIRR branches that run on a
weekday (Belmont Park runs only on race days), all 6 Metro-North lines — each with its weekday headway array and
its shapes. `rail_stops.parquet`: 1,166 stations. Route lengths cross-check: subway 1 train 23.5 km (real 23.9 km),
LIRR Port Jefferson Branch 95.6 km, MNR Harlem Line 131.9 km.

---

## 4. How it was verified

```
PYTHONPATH=pipeline python3 -m pytest pipeline/tests/test_furniture.py -q
# 44 passed, 1 warning in 20.61s
```

The suite is 38 unit tests on synthetic inputs (allometry monotonicity and saturation, catalog integrity,
de-duplication groups/priority/radius/determinism, every rule's spacing/side/offset/suppression/district,
ground-model IDW, tree status filtering, GTFS calendar + calendar_dates resolution, headway arithmetic, shape
parsing) plus 6 integration tests that open the real artefacts:

* every `tiles/{tile}/props.parquet` validates against `contracts.CONTRACTS["props"]` (DATA_CONTRACTS §8);
* every row's `x, y` really lies inside the tile named in its `tile`/`tx`/`ty` columns, one tile per file;
* `prop_id` is globally unique across all 1,576 files and `prop_id // 10^10 == kind` everywhere;
* the per-kind counts in `props_catalog.json` equal the counts recomputed from the tile files;
* every row has provenance and `source == 1` ⇔ `dataset_id` starts with `rule:`;
* trees: 650,516 rows, every one with a finite allometric height in (1.37 m, 45 m), `height_source = 1`,
  `dbh_cm ≥ 0`, and the row count equals `alive_placed − tree dedupe drops` exactly;
* `bus_routes.parquet` and `bus_stops.parquet` validate against `contracts.CONTRACTS`, headway arrays are 24 long
  with a plausible median, route geometry is inside the NYC_TM scope box and carries GeoParquet `geo` metadata;
* subway entrances have line bullets and legal globe codes;
* rail structures have finite deck heights for every elevated row and at least some measured ones;
* the ferry table contains `SIF` with an 8.1 km alignment and both real terminal names;
* `runtime/transit.nycb` round-trips: sections, per-record sizes, every `first_*`/`*_count` span inside its
  section, every `route_stops` id present in `bus_stops`, every vertex inside the scope box.

Stage runtimes on the loaded container: furniture **164.7 s** (peak RSS ≈ 1.07 GB), transit **139.8 s**
(peak RSS ≈ 0.9 GB) — both well inside the 4 GB budget, both run with `nice -n 10`.

---

## 5. `runtime/transit.nycb` (DATA_CONTRACTS §15)

Written through `nycsim_pipeline.runtime.nycb.NycbWriter` (the writer was ready).

| section | records | `element_size` | C struct |
|---|---:|---:|---|
| `bus_routes` | 345 | 68 | `{uint32 name_str; uint32 first_vertex, vertex_count; uint32 first_stop, stop_count; uint16 headway_min[24]}` |
| `bus_stops` | 13,364 | 24 | `{int64 id; float x, y, z; uint32 name_str}` |
| `route_stops` | 21,963 | 8 | `{int64 stop_id}` |
| `vertices` | 137,060 | 12 | `{float x, y, z}` |
| `strtab` | 205,860 B | 1 | NUL-separated UTF-8 |

`transit.layout.json` next to it records every field offset so the C++ `core/io/NycbReader.h` side can be checked
mechanically. Two conventions the C++ side must know:

* `bus_routes.first_vertex/vertex_count` reference the **longest single shape** of the route (its primary
  alignment). The other shape variants are only in the Parquet `geometry` MultiLineString.
* `bus_stops.id` is the GTFS `stop_id` parsed as an integer when it is numeric (all MTA bus stops are), otherwise
  `1,000,000,000 + row index`. The string id stays in the Parquet table.

---

## 6. Fidelity achieved vs. target, and the gaps

**Real:** every tree position, species and trunk diameter; every hydrant, shelter, kiosk, newsstand, bike shelter,
curb ramp, RTPI sign, Citi Bike dock (with its real capacity), subway entrance (with its real line bullets and
globe state), Parks structure (with its surveyed roof height and grade), planimetric vent grate, emergency exit,
cooling tower, pool and misc structure; every bus route shape, stop, and weekday headway; every rail structure
alignment and class; every ferry route and landing. All ground elevations come from survey/LiDAR points.

**Gaps, each flagged in the data:**

1. **Tree height is estimated, not measured** (the census records no height). `height_source = 1` on all 650,516
   tree rows. The curve is a saturating monomolecular fit whose asymptote is the published mature street-tree
   height of the species; it cannot be validated against per-tree truth because no such data exists.
2. **31.6 % of props are rule placements** (`source = 1`): 256,843 street lamps, 287,551 manholes, 1,402 steam
   vents. The City publishes no citywide location dataset for any of the three. Positions are plausible, not real;
   the *count* of lamps is close to the published fleet size, the manhole and steam-vent counts are modelling
   choices stated as such in `props_catalog.json` and `build_summary.json`.
3. **Prop `z` does not come from the terrain raster** (`tiles/{tile}/terrain.png` did not exist during this run).
   It comes from surveyed spot elevations + LiDAR building grades, which is arguably better on the street but is
   not the same surface the engine will render. `z_source` 3/4 marks every such row; a later pass can resample
   against the finished terrain. 0.58 % of rows (10,083) are extrapolated from a reference point > 80 m away.
4. **GTFS is one representative weekday** (2026-09-09). Saturday/Sunday headways, night service patterns and
   seasonal routes are absent: the Governors Island ferry shuttle, the NYC Ferry Rockaway Rocket, and the LIRR
   Belmont Park branch have no weekday trips and therefore no row. The service date is recorded in
   `transit/build_summary.json`.
5. **Deck heights are 60.7 % measured**; 2,625 above-grade structures use their class median (flagged
   `deck_height_source = 1`) because no *Bridge Elevation* point falls within 25 m. Open-cut depth is not
   produced at all (`deck_height_source = 2`, NaN) — the bridge points around an open cut belong to the road
   bridges crossing it, so measuring from them would be wrong.
6. **Prop dimensions in the catalog are nominal reference sizes**, not per-instance measurements, except where the
   dataset publishes one (Parks roof heights, ramp widths, footprint extents, Citi Bike capacity, OSM `height`).
   `dims_source` names the standard behind each nominal size.
7. **Bike shelters: only 17 exist in `dimy-qyej`.** That is the dataset, not a loss.
8. **Planimetric "transit entrance" polygons (2,005, code 2485) were deliberately not imported** — they are the
   same physical stairs as the MTA `subway_entrances` records, which additionally carry the served lines and the
   globe state. Importing both would double-place every subway stair.
9. **`highway=bus_stop` OSM nodes (15,145) are not turned into props** — bus stops come from GTFS with their real
   route lists (kind 24). This is the only OSM furniture tag in the extract that is intentionally unmapped.

---

## 7. Contract extensions (appended, not silent)

DATA_CONTRACTS §8 and §9 were followed exactly for the columns they name. These additions are documented in
`props_catalog.json` (`extensions_to_data_contracts_s8`) and here, and should be folded into the contract:

* **`props.parquet` extra columns:** `height_source` (0 measured/tagged, 1 allometry, 2 nominal catalog value,
  3 none), `capacity` (docks/stands, 0 = n/a), `z_source` (0 terrain, 1 dataset, 2 none, **3 spot-elevation IDW
  ≤ 80 m, 4 same but > 80 m**), `attrs` (per-instance JSON: native ids, footprint dimensions, routes, ramp width…),
  and the tiling columns `tile, tx, ty` — the same convention the buildings stage uses in §5.2.
* **New prop kinds 31–33:** `subway_vent_grate`, `subway_emergency_exit` (both from the planimetric Railroad
  Structure layer, real), `steam_vent` (rule).
* **`bus_routes`/`rail_routes`/`ferry_routes` extra columns:** `route_uid` (`"{agency}:{route_id}"`),
  `agency`, `route_type`, `color`, `feeds`, `shape_count`, `length_m` (longest shape),
  `total_shape_length_m` (all variants), `trips_weekday`.
  `route_uid` exists because GTFS `route_id` is **not** unique across agencies — subway route `1`, LIRR route `1`
  and Metro-North route `1` are three different routes and collided until the key was made agency-qualified.
* **`bus_stops`/`rail_stops` extra columns:** `z_source`, `shelter_dist_m`, `parent_station`, `feeds`.
* **`subway_entrances` extra columns:** `z_source`, `kind_code`, `entrance_type`, `station_id`, `complex_id`,
  `gtfs_stop_id`, `stop_name`, `division`, `line`, `borough`, `entry_allowed`, `exit_allowed`.
* **New files:** `transit/ferry_terminals.parquet`, `transit/rail_routes.parquet`, `transit/rail_stops.parquet`.
* **Two new download sources** are defined in `transit/ferry.py` rather than in `sources.py` (a foundation file
  this stage must not edit) and are registered through `manifest.record_download` like every other download.
  **Request to the orchestrator: move these two `Source` records into `sources.py`.**

---

## 8. What the next agent needs to know

* **Order matters:** the transit stage must run **before** the furniture stage — `furniture/build.py` reads
  `transit/bus_stops.parquet` to place the bus-stop sign props (kind 24) and fails loudly with an instruction if it
  is missing.
* **Blender props kit:** `props_catalog.json` is the authoritative kind enum with nominal dimensions and the
  meaning of `variant`, `text` and `heading` for each kind; build one mesh per kind (plus its variants) and
  instance it from `tiles/{tile}/props.parquet`. `heading` is a compass bearing (0 = north, clockwise), NaN where
  the source gives no orientation. `height_m` is the object height to scale to; trees additionally carry
  `dbh_cm` (trunk diameter) and `species`.
* **Rooftop props:** the 81,684 cooling towers carry the `bin` of the building underneath in `attrs`, and
  `sub_featur` distinguishes roof level (`212000`) from ground level (`212010`) — this is the real input for the
  buildings contract's `rooftop_units`.
* **Terrain agent:** when `tiles/{tile}/terrain.png` exists, prop `z` can be resampled; the rows to revisit are
  exactly those with `z_source` 3 or 4.
* **Traffic agent:** buses follow `bus_routes.parquet` (`geometry` + `headway_min[24]`) and stop at
  `bus_stops.parquet`; `runtime/transit.nycb` has the same data in the C++ layout. Trains follow
  `rail_routes.parquet`; `rail_structures.parquet` says where the track is above grade and how high the deck is.
* **Pedestrian agent:** `subway_entrances.parquet` (2,120 real entrances with `lines`), `bus_stops.parquet` and
  the storefront/POI layers are the destination set; `curb_ramp` props (216,339) mark every real curb cut.
* **Re-running:** `python -m nycsim_pipeline transit` then `python -m nycsim_pipeline furniture`. Both are
  idempotent and deterministic; both rebuild the same ground model (≈ 30–50 s each). If the roads stage ever
  re-emits `segments.parquet`, re-run `furniture` to refresh the rule-based fill.

---

## 9. Licences of everything used by these two stages

| Source id(s) | Publisher | Licence |
|---|---|---|
| `street_trees_2015`, `hydrants`, `bus_stop_shelters`, `linknyc`, `newsstands`, `bike_shelters`, `pedestrian_ramps`, `rtpi_signs`, `parks_structures`, `plan_railroad_structure`, `plan_railroad_line`, `plan_misc_structures`, `plan_swimming_pools`, `plan_cooling_towers`, `plan_elevation_points` | City of New York (OTI / DOT / DEP / Parks), NYC Open Data | **NYC Open Data Terms of Use** — public-domain-equivalent, attribution requested |
| `gtfs_ferry_staten_island` (dataset `b57i-ri22`) | New York City Department of Transportation, NYC Open Data | **NYC Open Data Terms of Use** |
| `gtfs_bus_manhattan`, `gtfs_bus_bronx`, `gtfs_bus_brooklyn`, `gtfs_bus_queens`, `gtfs_bus_staten_island`, `gtfs_bus_company`, `gtfs_subway`, `gtfs_lirr`, `gtfs_mnr` | Metropolitan Transportation Authority | **MTA Developer Data Terms** |
| `subway_entrances` (`i9wp-a4ja`) | Metropolitan Transportation Authority, data.ny.gov | **NY State Open Data terms** (public domain-equivalent, attribution requested) |
| `gtfs_ferry_nyc` | NYC Ferry (NYCEDC / Hornblower), Connexionz feed | **Public GTFS feed published for consumption by transit applications** |
| `citibike_gbfs_stations` | Lyft Bikes and Scooters, LLC | **Citi Bike Data License Agreement** |
| `osm_newyork_pbf` (street furniture + rail layers) | © OpenStreetMap contributors | **ODbL 1.0** |
| `building_footprints` → `buildings_base.parquet` ground elevations (consumed, not produced here) | City of New York, OTI | NYC Open Data Terms of Use |

Documentation consulted (not redistributed): the NYC Planimetric Database *Capture Rules*
(`github.com/CityOfNewYork/nyc-planimetrics`), which is what establishes that Railroad Line feature codes
2410/2420/2430/2440 mean elevated / embankment / viaduct / open cut and that Railroad Structure codes
2470/2480/2485 mean ventilation grate / emergency exit / transit entrance. Every download in this stage is
recorded in `data/manifest/downloads.json` with its URL, SHA-256, licence and attribution.

One access note for the record: the URL printed in the Staten Island Ferry dataset description
(`https://www.nyc.gov/html/dot/downloads/misc/siferry-gtfs.zip`) is refused with HTTP 403 by nyc.gov's edge from
this network; the Socrata blob endpoint for the identical file was used instead and is the URL recorded in the
manifest.
