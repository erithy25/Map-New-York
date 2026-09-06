# NYCSim — Architecture Plan

**Project:** 1:1 free-roam drivable simulation of New York City (five boroughs, surrounding waters, NJ shoreline skyline).
**Runtime target:** Unreal Engine 5.4 (World Partition, Chaos Vehicles, Lumen, Nanite, Niagara, MetaSounds).
**Content authoring:** Blender 4.5 LTS, driven headless through the `bpy` Python module.
**Data processing:** Python 3.11 pipeline (`pipeline/`), engine-agnostic C++17 core (`core/`).
**Ground truth:** NYC Open Data (OTI/DCP/DOT/DPR/LPC), USGS 3DEP, OpenStreetMap, MTA GTFS, NWS/Open-Meteo/NOAA.

This document is written before any code. It is the contract every subsystem and every sub-agent works against.
Data schemas shared between subsystems are specified in `DATA_CONTRACTS.md`. Every decision with a trade-off is
recorded in `DECISIONS.md` (ADR format). The honest, quantified result is `FIDELITY_REPORT.md`.

---

## 0. Build environment and its consequences (read first)

The build ran in a headless Linux container (4 vCPU, 15 GB RAM, ~30 GB writable disk, no GPU, no display,
egress through a policy proxy). These facts shape what can be *produced and verified here* versus what can only be
*authored here and verified on a workstation*:

| Capability | Available here | Consequence |
|---|---|---|
| Blender 4.5 (`bpy` module) | Yes (CPU only) | Every mesh, material, rig and animation is generated, exported (glTF/FBX) and test-rendered (Cycles CPU) in this environment. |
| Unreal Engine 5 editor / UBT | **No** (no Epic download, no GPU) | The UE project is authored as complete C++ source, config, Python editor automation and content manifests. It is compiled and cooked on a workstation following `unreal/README.md`. Anything UE-only is verified by static review, not by execution, here. |
| Google Street View / per-building imagery | **No** (ToS + key + 1.08 M buildings) | Facade appearance is *inferred* from real per-building attributes (year built, building class, floors, landmark status, historic district, neighbourhood, OSM tags). It is never presented as photo-matched. See §4.5. |
| Overpass main API, Geofabrik, GitHub releases | Blocked | OSM comes from the BBBike New York extract (`.osm.pbf`, 152 MB) plus Overpass mirrors for spot queries. |
| NYC 1-ft DEM (26.6 GB zip) | Too large for disk | Terrain is built from USGS 3DEP 1/9 arc-second (~3.4 m) LiDAR-derived DEM, densified with 1.08 M building ground elevations (LiDAR) and NYC planimetric spot elevations (survey grade). Effective horizontal resolution 2 m, vertical measured at 0.384 m RMS (see ADR-017). |
| Disk for 1.08 M high-detail facade meshes | No (would be > 50 GB) | Building *shells* (real footprint + real roof) are generated for every building; facade *detail* is delivered as an instanced kit (windows, cornices, fire escapes, storefronts, stoops, rooftop equipment) with per-building placement data computed deterministically in the pipeline and instantiated by the engine. This is also the only architecture that streams 1 M buildings at 60 fps. |

Nothing in the list above is a shortcut hidden as fidelity. Each is a documented, measured gap in `FIDELITY_REPORT.md`.

---

## 1. Repository layout

```
docs/                 ARCHITECTURE.md, DATA_CONTRACTS.md, DECISIONS.md, DATA_SOURCES.md, ASSET_LICENSES.md, FIDELITY_REPORT.md
pipeline/             Python package `nycsim_pipeline` — download, ingest, process, tile, classify, export
  nycsim_pipeline/    sources.py, crs.py, tiling.py, terrain/, roads/, buildings/, furniture/, transit/, water/, live/
  cli.py              `python -m nycsim_pipeline <stage>` — idempotent, manifest-driven
blender/              bpy scripts: kit/, buildings/, landmarks/, props/, vehicles/, character/, render/, common/
core/                 C++17 engine-agnostic library `nycsim_core` + tests (CMake). Compiled into UE module and standalone.
unreal/NYCSim/        UE 5.4 project: NYCSim.uproject, Source/{NYCSimCore,NYCSimRuntime,NYCSimEditor}, Config/, Content/Python/
services/             Live-data adapters reference implementation (Python) mirrored in core/live (C++)
tests/                Cross-cutting integration tests (pipeline outputs, contracts, drive-through)
data/raw/             Downloaded sources (git-ignored, manifest-tracked with SHA-256)
data/processed/       Pipeline outputs (git-ignored, contracts in DATA_CONTRACTS.md)
data/manifest/        JSON manifests of every download and every generated artifact (committed)
```

---

## 2. Coordinate systems and units

* **World CRS (`NYC_TM`)**: custom Transverse Mercator, WGS84, `+proj=tmerc +lat_0=40.7 +lon_0=-73.95 +k=1 +x_0=0 +y_0=0 +units=m`.
  Scale distortion ≤ 1.2 cm/km anywhere in scope (max 30 km from the central meridian). This *is* 1:1.
  Origin (0,0) lies in the East River off Roosevelt Island; all five boroughs fit in x ∈ [−28 km, +22 km], y ∈ [−25 km, +25 km].
* **Vertical**: metres above NAVD88. Sources in US survey feet (NYC DEM, footprints, CityGML, State Plane) are converted with 0.3048006096.
* **Source CRSs**: EPSG:4326 (Socrata GeoJSON), EPSG:2263 (NY Long Island State Plane, ft: signs, LION, planimetrics, CityGML), EPSG:4269/NAD83 (3DEP). All handled by `pipeline/nycsim_pipeline/crs.py` using pyproj with explicit datum transformations.
* **Blender**: right-handed Z-up, metres. X = east, Y = north, Z = up. Tile meshes are authored in tile-local coordinates (tile origin at the tile's south-west corner) to keep float32 precision at the millimetre level.
* **glTF**: Y-up right-handed; the Blender exporter performs (X, Y, Z) → (X, Z, −Y). The UE glTF importer reverses it. No hand conversions anywhere.
* **Unreal**: left-handed Z-up, centimetres. `UE.X = east_m × 100`, `UE.Y = −north_m × 100` (south), `UE.Z = up_m × 100`. Implemented once in `core/geo/UECoords.h`. UE 5 Large World Coordinates (double precision) hold a 50 km world without rebasing.

## 3. Tiling and streaming

* **Tile grid**: 1000 m × 1000 m cells indexed `(tx, ty) = (floor(x/1000), floor(y/1000))`, named `t_{tx}_{ty}` with sign, e.g. `t_-3_7`. ~2,500 cells cover the extent, ~1,480 contain land content.
* **Level-of-detail tiers**
  * **L0 (0–600 m)**: building shells + full instanced facade kit + all props, signs, trees, pavement detail, interior storefront shells, traffic and pedestrians simulated.
  * **L1 (600–2,500 m)**: building shells with facade shader (window grid, materials, lit windows) but no 3D kit except cornices/water towers ≥ 2 m; trees as impostors; traffic simulated coarsely (no pedestrians).
  * **L2 (2.5–12 km)**: merged per-4-km-tile shell meshes (HLOD), skyline correct, lit-window texture.
  * **L3 (12–40 km)**: merged per-16-km-tile meshes; only buildings ≥ 40 m plus terrain and water. Guarantees the Manhattan skyline is complete from Brooklyn Heights, the ferry and the George Washington Bridge.
* **Never dropping buildings in sightline**: every building is present in exactly one tier at every distance; tiers overlap by 20 % with cross-fade dithering; no building < 300 m from the camera is ever loaded/unloaded (loading radius 900 m, unload radius 1,300 m, hysteresis prevents thrash).
* **Streaming**: engine-agnostic `core/streaming/TileScheduler` decides tile tiers from camera position, velocity and heading (predictive: at 30 m/s it pre-loads 1.5 s ahead); UE side uses World Partition runtime cells (1 km) plus custom HLOD layers for L2/L3, async mesh loading on worker threads only. Memory budget: hard cap 6 GB GPU / 8 GB CPU resident, enforced by evicting farthest L0 first.
* **Determinism**: the same camera path produces the same load/unload sequence; the scheduler is unit-tested with recorded drives.

## 4. Buildings (1,083,026 footprints)

### 4.1 Sources
| Attribute | Source (real) | Fallback (inferred, flagged) |
|---|---|---|
| Footprint polygon | NYC Building Footprints (`5zhs-2jue`, OTI, photogrammetric, updated 2026-08) | none (every footprint is real) |
| Roof height | `height_roof` (LiDAR-derived, ft) | PLUTO `numfloors` × class-specific floor height; else neighbours' median |
| Ground elevation | `ground_elevation` (LiDAR, ft) | terrain sample |
| Roof shape | NYC 3-D Building Model CityGML LOD2 (2014 LiDAR, `tnru-abg2`) matched by BIN | flat roof with parapet if built after 2014 or no match |
| Floors, year, class, land use, lot, owner type | MapPLUTO (`64uk-42ks`) by BBL | floors from height; year = footprint `construction_year` |
| Landmark / historic district | LPC individual landmarks (`buis-pvji`), LPC building DB (`gpmc-yuvp`), historic districts (`skyk-mpzq`) | — |
| Names, materials, levels, shops | OSM (BBBike NYC extract: `building`, `building:material`, `building:levels`, `name`, `shop`, `amenity`) | — |
| Storefront business names | OSM `shop/amenity name`; DCWP Issued Licenses (`w7w3-xahh`); DOHMH restaurants (`43nn-pn8j`) geocoded by BBL/BIN | generic unbranded storefront (flagged) |
| Scaffolding / sidewalk sheds | DOB NOW approved permits, work type Sidewalk Shed, active | none |
| Elevation & subgrade (stoops, below-grade) | Building Elevation & Subgrade (`bsin-59hv`) | class-based rule |

### 4.2 Fidelity flags
Every building record carries a bitfield `fidelity`: `FOOTPRINT_REAL, HEIGHT_REAL, ROOF_REAL, FLOORS_REAL, YEAR_REAL, FACADE_INFERRED, SIGNAGE_REAL, LANDMARK_MODEL`. Counts by flag and borough are the backbone of the fidelity report.

### 4.3 Geometry (Blender, per tile)
`blender/buildings/build_tile.py` reads `data/processed/tiles/{tile}/buildings.parquet` and emits `tile_buildings.glb`:
* Footprint ring(s) cleaned (snap 2 cm, orientation fixed, holes kept), triangulated (mapbox_earcut), walls extruded from `ground_elevation` to `roof_base`.
* Roof from CityGML surfaces when matched (gable, hip, mansard, sawtooth, flat with bulkhead as-modelled) else flat + parapet (0.6 m) generated.
* Wall UVs in metres (u along facade, v height) so facade shaders align windows to real floor heights.
* Per-building vertex attributes: `bin`, `facade_class`, `floors`, `floor_height`, `ground_floor_height`, `is_storefront`, `lit_seed`.
* One mesh per (tile, material class) to keep draw calls bounded; shells ≈ 1.2 KB/building → ≈ 1.3 GB for the city.

### 4.4 Facade kit (Blender, once)
`blender/kit/` produces ~260 instanced meshes with PBR materials: window types (double-hung 1-over-1, 6-over-6, casement, steel industrial, curtain-wall module, punched-window office, storefront bay), lintels/sills (brownstone, limestone, cast stone), cornices (pressed metal 3 profiles, brick corbel, stone), fire escapes (drop-ladder, straight, with balconies), stoops (brownstone 8–12 steps, rowhouse 4 steps), areaway railings, entrance canopies, awnings (fabric, aluminium; text generated from real names), roll-down shutters, security grilles, AC window units (3 sizes), water towers (2 sizes, cedar), HVAC (RTU 3 sizes), bulkheads, antennas, parapet caps, billboards, scaffolding/sidewalk shed modules (green plywood, NYC standard), storefront interior shells (bodega, deli, pharmacy, nail salon, laundromat, restaurant, bank, chain generic), roof membranes.

### 4.5 Facade classification (pipeline, deterministic, documented)
`pipeline/nycsim_pipeline/buildings/facade_rules.py` maps (year, PLUTO `bldgclass`, floors, height, lot frontage, borough, NTA, landmark flag, historic district, OSM material) → `facade_class` and kit parameters. The rules are the codification of NYC building typology (tenement laws of 1879/1901, 1916/1961 zoning setbacks, post-war white-brick, 1980s brown-brick, 2000s glass) and are versioned; the classifier is auditable and its rule hit-rates are reported. Where OSM gives `building:material` it overrides the rule (flagged `MATERIAL_REAL`).

### 4.6 Landmarks (hand-scripted parametric models in Blender)
Each landmark in `blender/landmarks/` is its own script with real published dimensions, keyed to its real footprint BIN(s), replacing the generated shell. Target list in `docs/LANDMARKS.md` (60+). Fidelity is stated per landmark (massing + ornament + materials; sculptural elements are the weakest and are said so).

## 5. Terrain, water, coastline
* 3DEP 1/9″ tiles mosaicked → reprojected to `NYC_TM` at 2 m; spot elevations (planimetric `szwg-xci6`) and building `ground_elevation` merged via inverse-distance blending within 15 m of each point; hydro-flattened to 0.0 m NAVD88 inside hydrography polygons (`pjs3-c3z5`), shoreline from planimetric shoreline (`59xk-wagz`) as hard edge; piers/bulkheads from hydrography structures (`6hbv-tek4`).
* Output: per-tile 16-bit heightmap PNG (501 × 501 samples, 2 m) + `terrain.json` (min/max) → UE Landscape import; water plane per tile with flow direction from tidal current tables (NOAA CO-OPS, The Battery/Hell Gate stations).
* NJ side: 3DEP + NJGIN building footprints (Hudson County) with heights from OSM/NJ parcels → L2/L3 skyline meshes only; drivable roads end at the Hudson tunnel/bridge portals (documented scope edge).

## 6. Roads and street environment
* **Centerline/LION** (`inkn-q76z`, `2v4z-66xt`): 122,269 segments; fields used: `trafdir` (FT/TF/TW/NV), `number_travel_lanes`, `number_park_lanes`, `streetwidth`, `posted_speed`, `rw_type` (street/highway/bridge/tunnel/ramp/…), `from/to_level_code` (grade separation), `bike_lane`, `truck_route_type`, `segment_type`, `full_street_name`, `l/r_low/high_hn`.
* **Lane model** (`core/roads`): lanes generated from centreline + width + counts + parking lanes; junction lanes built from node topology; turn restrictions from OSM `restriction` relations + one-way topology; NYC default *no right on red* everywhere (exception list for signed intersections is empty by law except where posted; none posted in data).
* **Pavement geometry**: planimetric Roadbed (`i36f-5ih7`), Curb (`5xvt-8cbk`), Sidewalk (dataset behind `vfx9-tbb6`), Median (`ees7-4ufv`), Pavement Edge (`vs44-rznx`) → exact asphalt/curb/sidewalk polygons per tile (real widths, real corner radii, real medians). Markings from lane model + bike routes (`mzxg-pwib`) + bus lanes (`ycrg-ses3`) + pedestrian plazas (`k5k6-6jex`).
* **Signals**: OSM `highway=traffic_signals` ∪ DOT LPI (`xc4v-ntf4`) ∪ Barnes Dance (`8kuj-2n3u`) ∪ signal retiming (`d8dp-wfee`) ∪ speed-limit dataset (`5mad-ntua`); phasing model per DOT standard (90 s cycle Midtown, 60 s elsewhere, LPI 7 s where flagged, pedestrian countdown). Locations without any source are inferred at intersections of two ≥ 2-lane streets and flagged.
* **Signs**: DOT Parking Regulation Locations and Signs (`nfid-uabd`, 440,540 current signs with MUTCD code, description text, arrow, facing, side, distance from intersection, State Plane x/y) → every real parking, one-way, stop, speed limit sign as an instanced sign mesh with its real text rendered to texture. Street name signs generated at every intersection from the two real names (green, Highway Gothic, NYC standard).
* **Street-level clutter datasets**: trees (2015 census `uvpi-gqnh`, species, DBH), hydrants (`5bgh-vtsn`), bus shelters (`t4f2-8md7`), LinkNYC (`s4kf-3yrf`), newsstands (`w9zq-xm8b`), bike shelters, Citi Bike (GBFS), subway entrances (data.ny.gov `i9wp-a4ja`), bus stops (GTFS), parks (`enfh-gkve` + planimetric open space), truck routes. Items with no dataset (manholes, steam vents, standpipes, bollards, trash cans, mailboxes) are placed by rule against real curb geometry and flagged inferred with the rule named.
* **Transit structures**: elevated subway and Metro-North viaducts from OSM (`railway=subway|rail` with `bridge=yes` / `layer`) + planimetric transportation structures; trains run on GTFS schedules.

## 7. Vehicles and driving
* **Player car**: 2019 Ford Fusion Hybrid dimensions (4,872 × 1,852 × 1,476 mm; 2,850 mm wheelbase) — chosen because it is the most common NYC livery-compatible sedan in the hire fleet, so the same body doubles as a yellow-cab variant. Full exterior/interior in Blender, functional dash (speed, RPM, fuel, turn signals), mirrors (UE scene-capture), lights, wipers, windows, horn, radio.
* **Physics**: UE Chaos Vehicle with parameters from `core/vehicle/VehicleSpec` (mass 1,685 kg, torque curve, gear ratios, tyre friction curves per surface class: dry asphalt 1.0, wet 0.7, steel plate 0.55 wet, painted marking 0.6 wet, snow 0.3, ice 0.15). Suspension responds to a per-tile pavement roughness texture (patches, plates, potholes).
* **Damage**: per-region deformation (UE mesh morph), light breakage states, glass cracking decal.
* **Cameras**: chase, hood, interior with head look, cinematic orbit.
* **GPS**: routing from `core/routing` (contraction hierarchies over the lane graph), turn-by-turn text with real street names, minimap from processed road geometry.

## 8. Character
Rigged human generated with MakeHuman (MPFB) assets in headless Blender, custom face/skin/clothing, ARKit-compatible blendshapes, eye tracking, hands. Animation set authored procedurally + CMU mocap retargeting where reachable (license logged). Name, home address (a real address; the building record is checked to be residential), and backstory in `docs/CHARACTER.md`.

## 9. Traffic AI (core/traffic, deterministic fixed step 20 Hz)
Lane graph; agents with destinations chosen from an origin–destination model weighted by land use and time-of-day (calibrated against DOT Automated Traffic Volume Counts and TLC taxi zone trip counts); IDM longitudinal + MOBIL lateral; signal compliance; NYC behaviours (double parking on commercial blocks with parking lanes, box blocking probability calibrated, honking events); reaction to player (TTC-based braking, swerve, honk); fleet mix per area/time; buses follow GTFS routes and stop at real stops; emergency vehicles with priority behaviour; cyclists/e-bikes on bike lanes. No agent is created or destroyed within 250 m of the player's view frustum (spawn ring with occlusion test).

## 10. Pedestrians (core/peds)
Sidewalk navigation mesh from planimetric sidewalks and plazas; crosswalk gating by signal phase with NYC jaywalking model; density by NTA × hour from a calibrated table (Midtown peak 0.35 ped/m² sidewalk); activities and destinations (subway entrances, bus stops, storefronts, parks); variety via body/clothing parameter space seeded per agent (no duplicates within 60 m).

## 11. Time and weather (core/live, services/)
* Real time from system clock → America/New_York with full IANA rule handling (DST transitions), sun/moon via NREL SPA-equivalent algorithm (± 0.0003°), moon phase; Manhattanhenge verified by test (sunset azimuth 299.0° ± 0.2° on the real dates).
* Weather: NWS (`api.weather.gov` observations from KNYC Central Park, forecast gridpoints) primary; Open-Meteo secondary; METAR (KLGA/KJFK/KEWR) tertiary. Poll 60 s, exponential back-off, last-known-state fallback shown in debug overlay with age. Mapping table weather → world (wetness, puddles, snow accumulation, fog density, wind for flags/awnings, umbrellas, plows/salt).
* Empire State Building crown colours from the ESB tower-lights calendar (scraped daily, cached, fallback: white).
* Tides/currents from NOAA CO-OPS for river flow direction and speed.

## 12. Audio
MetaSounds graphs for engine (RPM/load), tyres per surface, wind, rain on roof, wipers; ambience zones (traffic density-driven, subway grates, steam vents, parks, waterfront, helicopter corridors); sirens with Doppler; radio stations (CC-licensed music/talk beds, logged). All sound sources CC0/CC-BY, listed in `ASSET_LICENSES.md`.

## 13. Performance & robustness
Frame budget 16.6 ms at 1440p on RTX 4070-class: Nanite for shells and kit, Lumen GI, virtual shadow maps; L0 instancing via ISM/HISM per kit type per tile; traffic and peds on worker threads through `core`; memory hard caps; no allocation in per-frame hot paths (arena allocators); every external call has timeouts and typed errors; no exceptions across the engine boundary.

## 14. Verification strategy (what is verified where)
| Check | Where | How |
|---|---|---|
| Geodesy, tiling, scheduler, routing, traffic rules, signal phasing, astronomy, tz, weather parsing | here | `core` unit tests (ctest), Python pipeline tests (pytest) |
| Road connectivity (Bronx → Staten Island over Verrazzano; every bridge/tunnel present and connected) | here | graph tests over processed data |
| Building counts, coverage, no gaps, roof match rate | here | pipeline integrity tests, per-borough reports |
| Visual fidelity at standard viewpoints | here | Blender Cycles CPU renders of generated tiles vs Wikimedia Commons photographs (side-by-side sheets in `docs/verification/`) |
| Drive-through inspection of five areas | here | headless drive along real routes: tile scheduler log, memory bound, gap detection; Cycles stills from car camera |
| UE compile, cook, frame rate, physics feel, audio | **workstation only** | steps in `unreal/README.md`; not claimed as verified here |

## 15. Build order and gating (Section 13 of the brief)
terrain & coastline → roads → buildings → **transit → furniture/vegetation** → vehicle → character → traffic → pedestrians → time/weather → audio → performance → tests → fidelity report. (Transit runs before furniture: the furniture stage reads `transit/bus_stops.parquet` to place bus-stop signs and shelters.) Each stage ends with its verification artefacts committed under `docs/verification/<stage>/` before the next begins.

## 16. Sub-agent organisation
Work is fanned out to specialised agents (data-ingest, Blender kit, Blender landmarks, Blender vehicles, Blender character, core C++, UE C++, UE Python automation, verification). Agents communicate only through the repository: `DATA_CONTRACTS.md` schemas, `data/manifest/*.json`, and stage reports in `docs/verification/`. An orchestrator (this session) reviews every report, re-runs any failed agent with the failure attached, and never accepts a report that claims fidelity it cannot show.
