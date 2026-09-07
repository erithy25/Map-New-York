# Fidelity Report

Generated 2026-09-07 06:52 UTC from commit `552cc1108360` by `pipeline/nycsim_pipeline/report/fidelity.py`.

Every figure below is read from an artefact on disk at generation time. Where an artefact does not exist, the row says **not produced** rather than showing a zero. Nothing in this report is an estimate unless it is labelled as one.

## 1. Buildings

Total buildings modelled: **1,083,026** (source of truth: NYC Open Data Building Footprints, `data/processed/buildings/buildings_base.parquet`).

### 1.1 By borough

| Borough | Buildings | Median height (m) | Max height (m) | Height real | Floors real | Roof real | Material real |
|---|---|---|---|---|---|---|---|
| Manhattan | 45,194 | 17.75 | 472.44 | 99.83 % | 84.77 % | 96.58 % | 32.63 % |
| Bronx | 104,278 | 8.43 | 137.16 | 99.82 % | 76.68 % | 95.93 % | 0.94 % |
| Brooklyn | 330,154 | 8.37 | 315.47 | 99.93 % | 77.88 % | 97.06 % | 4.64 % |
| Queens | 460,939 | 7.42 | 242.01 | 99.97 % | 66.42 % | 94.50 % | 0.95 % |
| Staten Island | 142,461 | 7.89 | 64.61 | 99.94 % | 79.63 % | 93.86 % | 0.28 % |

### 1.2 Attribute provenance across the whole city

| Bit | Flag | Meaning | Counted from | Buildings | Share |
|---|---|---|---|---|---|
| 0 | `FOOTPRINT_REAL` | footprint from the NYC OTI photogrammetric dataset | `buildings/buildings_base.parquet` | 1,083,026 | 100.00 % |
| 1 | `HEIGHT_REAL` | roof height from the LiDAR-derived `height_roof` field | `buildings/buildings_base.parquet` | 1,082,290 | 99.93 % |
| 2 | `ROOF_REAL` | roof geometry from the CityGML LOD2 model | `facade/facade_attrs.parquet` | 1,033,416 | 95.42 % |
| 3 | `FLOORS_REAL` | floor count from PLUTO | `buildings/buildings_base.parquet` | 794,995 | 73.40 % |
| 4 | `YEAR_REAL` | year built from PLUTO / footprint dataset | `buildings/buildings_base.parquet` | 1,075,197 | 99.28 % |
| 5 | `MATERIAL_REAL` | facade material from an OSM tag or an LPC designation report | `facade/facade_attrs.parquet` | 35,818 | 3.31 % |
| 6 | `SIGNAGE_REAL` | at least one real business name attached to the ground floor | `buildings/buildings_base.parquet` | 30,381 | 2.81 % |
| 7 | `LANDMARK_MODEL` | replaced by a hand-scripted landmark model | `blender_out/landmarks/catalog` | 121 | 0.01 % |
| 8 | `SCAFFOLD_REAL` | sidewalk shed from an active DOB permit | `buildings/buildings_base.parquet` | 6,396 | 0.59 % |
| 9 | `GROUND_REAL` | ground elevation from the LiDAR-derived field | `buildings/buildings_base.parquet` | 1,082,833 | 99.98 % |
| 10 | `FACADE_INFERRED` | facade appearance inferred by the rule set (ADR-004) | `facade/facade_attrs.parquet` | 1,047,208 | 96.69 % |
| 13 | `ROOF_INFERRED` | roof shape derived from building class and footprint (ADR-013) | `facade/facade_attrs.parquet` | 567,800 | 52.43 % |
| 11 | `HEIGHT_INFERRED` | height derived from floor count or neighbours | `buildings/buildings_base.parquet` | 736 | 0.07 % |
| 12 | `FLOORS_INFERRED` | floor count derived from height | `buildings/buildings_base.parquet` | 288,031 | 26.60 % |

Each bit is counted from the table of the stage that sets it. DATA_CONTRACTS §5.1 gives bits 2, 5, 10 and 13 to the facade stage, which writes its own table and does not write back into the base table, and bit 7 to the landmark scripts, whose catalog is the authority on which models exist. A bit whose owning artefact is missing reads **not produced**, never zero — a zero here would claim that nothing is inferred, which is the one thing this report must not get wrong.
* 121 BINs are named by the landmark catalog; 121 of them exist in the buildings table

Buildings whose footprint **and** height are both from measurement: 99.93 %.

Per-tile files with the complete §5 schema: 25 of 25 sampled (920 tiles hold buildings).

### 1.2a New Jersey — a second population, at a lower fidelity

The brief's scope is the five boroughs **plus the New Jersey shoreline**. New Jersey carries **231,382** further buildings across 486 tiles, from FEMA/ORNL USA Structures. They are **not** added to the count above and never should be: that count is the five boroughs, and these buildings are a different source at a different fidelity.

| Flag | New Jersey buildings | Share |
|---|---|---|
| `FOOTPRINT_REAL` | 231,382 | 100.00 % |
| `HEIGHT_REAL` | 170,547 | 73.71 % |
| `ROOF_REAL` | 0 | 0.00 % |
| `FLOORS_REAL` | 0 | 0.00 % |
| `YEAR_REAL` | 0 | 0.00 % |
| `MATERIAL_REAL` | 0 | 0.00 % |
| `SIGNAGE_REAL` | 0 | 0.00 % |
| `LANDMARK_MODEL` | 0 | 0.00 % |
| `SCAFFOLD_REAL` | 0 | 0.00 % |
| `GROUND_REAL` | 0 | 0.00 % |
| `FACADE_INFERRED` | 231,382 | 100.00 % |
| `ROOF_INFERRED` | 0 | 0.00 % |
| `HEIGHT_INFERRED` | 60,835 | 26.29 % |
| `FLOORS_INFERRED` | 231,382 | 100.00 % |

Median height 6.62 m, maximum 107.48 m. The whole table holds **2 distinct fidelity values**, which is the shape of a population where only the footprint and sometimes the height are measured. The maximum matters: the tallest building in Jersey City is really 271 m, and the source's error on towers is quantified in deviation B11a. Nothing was scaled to hide it.

By county: Bergen 93,901, Hudson 64,066, Essex 42,838, Passaic 29,053, Union 1,524.

### 1.3 Roof geometry (CityGML LOD2)

Delivery areas parsed: **20 of 20**; buildings with parsed LOD2 geometry: **1,083,281**.

Roof-type distribution: flat 1,083,377, complex 27, hip 12, mansard 8, dome 5, gable 4, barrel 2, shed 2.

## 2. Road network

Source of truth: NYC Street Centerline (CSCL) and LION, per ADR-006.

- Segments: **122,235**
- Total centreline length: **12,997.29 km**
- Nodes: 79,291 · lanes: 381,971 · junction lanes: 469,754
- Signalised intersections: 19,814 · signs: 633,287
- Named bridges and tunnels resolved: 53
- Posted speed from data (not inferred): 82.6 % of segments
- Lane count from data (not inferred): 92.9 % of segments

| Road class | Centreline km |
|---|---|
| street | 10,360 |
| highway | 653 |
| path | 651 |
| ramp | 372 |
| alley | 309 |
| ferry route | 307 |
| bridge | 203 |
| driveway | 94 |
| boardwalk | 21 |
| tunnel | 15 |
| step street | 8 |
| U-turn | 5 |
| non-physical | 0 |

**External cross-check.** New York City's published mapped street mileage is about 6,000 centreline miles, roughly 9,650 km. This build carries **10,360 km** classified as street, about +7 % against that figure — the difference is the service roads, marginal streets and private roads that CSCL carries and the published mileage excludes. The drivable network (street, highway, bridge, tunnel, ramp, alley) totals 11,912 km; ferry routes are listed above for completeness but are not road.

| Borough | Centreline km |
|---|---|
| Queens | 4,680.2 |
| Brooklyn | 3,111.4 |
| Staten Island | 1,908.3 |
| Bronx | 1,861.5 |
| Manhattan | 1,435.9 |

## 3. Terrain, water and coastline

- Tiles with a written heightmap: **2,916**
- USGS 3DEP products ingested: **30** (1/13 arc-second, 1/19 arc-second, 1m) cut into 117 windows, 4.50 GB of source data
  - The 2 m working mosaic those were cut into was deleted to free disk for the city-wide shell run; the figures above come from the index kept behind for exactly this purpose (`terrain/src2m_index_kept.json`, one record per window with its source SHA-256). The removal, its reason and the command that regenerates it are in `terrain/src2m_removed.json`. The 2,916 published tiles are the product and are complete.
- Elevation range across written tiles: -5.18 m to 210.28 m (NAVD88)
- Vertical accuracy **0.384 m RMS**, measured against 1,458,592 independent survey and LiDAR ground points (0.291 m against planimetric spot elevations, 0.411 m against building ground grades), median bias −0.037 m after rejecting 0.52 % outliers. The plan assumed 0.15 m; this is the measured figure.
- Land coverage is 100.000 % in every borough, with 99.97 % or better taken from the 3DEP 1 m product (ADR-017). Tile seams match to 2.8 × 10⁻¹⁴ m across 5,724 adjacent pairs.

Water: hydrography polygons 2,235 · shoreline lines 413 · structures 2,536 · water tiles 2,916.

## 4. Street environment, transit and traffic model

- Tiles with props: 1,576 · total props placed: 1,724,589
- Bus routes 345 · bus stops 13,364 · subway entrances 2,120 · rail structures 8,341 · ferry routes 6
- Traffic density cells: 18,864

## 5. Authored assets (Blender)

| Group | glTF files | Size |
|---|---|---|
| kit | 138 | 140.3 MB |
| props | 122 | 79.2 MB |
| vehicles | 93 | 100.2 MB |
| character | 25 | 512.5 MB |
| landmarks | 127 | 920.2 MB |
| tiles | 1,496 | 5,523.1 MB |

Catalog entries describing those assets: 386.

## 6. Simulation code and runtime data

- `core/`: 53 headers, 37 sources, 19 test files; registered ctest cases: 11
- Runtime binaries: `density.nycb` 0.9 MB, `roadgraph.nycb` 104.2 MB, `signals.nycb` 1.7 MB, `transit.nycb` 2.4 MB

### 6.1 Unreal project

- 112 C++ files, 27,909 lines, 3 editor automation scripts, checklists: `COMPILE_CHECKLIST.md`, `COMPILE_CHECKLIST_GAMEPLAY.md`

The project cannot be compiled in this environment (ADR-001), so it is verified by static analysis that the orchestrator re-ran rather than took on trust:

| Check | Exit | Result |
|---|---|---|
| `check_gameplay_sources.py` | 0 | files checked: 72 (64 Unreal, 8 adapter), reflected public headers: 29, plain structs holding UObject pointers: 2 |
| `check_math.py` | 0 | ALL CHECKS PASSED |
| `check_sources.py` | 0 | ALL 523 CHECKS PASSED |
| `check_terrain_data.py` | 0 | ALL CHECKS PASSED |

These confirm the reflection macros, module dependencies, include resolution, garbage-collection ownership, declaration-to-definition pairing, console command documentation and the landscape and water mathematics. They do **not** confirm that the project compiles, cooks or runs — that needs a workstation pass following `unreal/README.md`, and no claim is made here that it was done.

## 7. Data sources and licences

146 downloaded sources, 14.8 GB, with SHA-256 recorded in `data/manifest/downloads.json`. Full table: `docs/DATA_SOURCES.md`.

| Licence | Sources |
|---|---|
| NYC Open Data Terms of Use (public domain-equivalent; attribution requested) | 67 |
| USGS public domain | 34 |
| CMU Graphics Lab Motion Capture Database: "free for all uses"; "may be copied, modified, or redistributed without permission"; created with funding from NSF EIA-0196217 | 14 |
| CC0-1.0 | 13 |
| MTA Developer Data Terms | 9 |
| NYC TLC Trip Record Data — public data released by the NYC Taxi & Limousine Commission (no licence restrictions stated; attribution requested) | 3 |
| Citi Bike Data License Agreement | 1 |
| NYC Ferry / Hornblower public GTFS feed (published for consumption by transit applications) | 1 |
| CC0-1.0 (MakeHuman community functional pack; pack json carries per-target licence) | 1 |
| GPL-3.0-or-later (add-on code); bundled base mesh/targets CC0 | 1 |
| ODbL 1.0 | 1 |
| Public domain (US Government work: FEMA / ORNL USA Structures) | 1 |

Authored asset licences (textures, fonts, mocap, audio): `docs/ASSET_LICENSES.md`.

## 8. Verification status

Reference photographs collected for side-by-side comparison: 519 photos across 172 subjects, each with author and licence metadata.

### 8.1 World coherence

| Layer | Tiles |
|---|---|
| terrain heightmaps | 2,916 |
| tiles with buildings | 920 |
| tiles with a shell mesh | 920 |
| tiles with kit placements | 920 |
| tiles with props | 1,576 |
| tiles with pavement | 972 |

Checked by `tests/test_world_integration.py::test_the_world_has_no_orphan_or_missing_content_layers`: every tile holding buildings also holds a shell mesh and kit placements, every shell mesh has building data behind it, and every content tile has terrain beneath it. Zero exceptions in any direction.

Stage reports present: buildings, buildings_mesh, character, citygml, comparison, core, facade, furniture, kit, landmarks, live, performance, props, reference, roads, terrain, traffic, traffic_density, unreal_gameplay, unreal_world, vehicles.

Lanes that split their work wrote more than one: `landmarks` (REPORT_B.md, REPORT_C.md).

Per-subject reports underneath those: comparison 58, facade 1, landmarks 34, reference 2, traffic_density 2.

What is verified in this environment versus on a workstation is defined in `docs/ARCHITECTURE.md` §14. In short: geodesy, tiling, streaming logic, routing, traffic rules, signal phasing, astronomy, time zone handling, weather parsing, data coverage and asset geometry are verified here by tests and Cycles renders. Unreal Engine compilation, cooking, frame rate, vehicle feel and audio are not — no Unreal editor or GPU exists in this environment, and no claim is made that they were tested.

## 9. Low-fidelity regions — where the data is thinnest

A citywide percentage hides where the weakness is. Below, the 194 neighbourhood tabulation areas holding at least 500 buildings, ranked by the mean of the three provenance shares this report can measure per neighbourhood. That mean is a ranking aid, not a score with units.

**The ten thinnest.** These are the places where a rebuild of this world should start.

| Neighbourhood | Buildings | Roof measured | Floors published | Material from a real source |
|---|---|---|---|---|
| Co-op City (Bronx) | 536 | 75.4 % | 29.9 % | 0.0 % |
| Spring Creek-Starrett City (Brooklyn) | 752 | 64.0 % | 64.6 % | 0.0 % |
| Breezy Point-Belle Harbor-Rockaway Park-Broad Channel (Queens) | 9,409 | 91.5 % | 44.8 % | 0.0 % |
| Bay Terrace-Clearview (Queens) | 4,965 | 89.0 % | 51.6 % | 0.0 % |
| Oakland Gardens-Hollis Hills (Queens) | 6,356 | 96.2 % | 47.9 % | 0.0 % |
| Glen Oaks-Floral Park-New Hyde Park (Queens) | 8,037 | 97.4 % | 50.6 % | 0.0 % |
| Fresh Meadows-Utopia (Queens) | 6,435 | 93.0 % | 56.8 % | 0.0 % |
| Bellerose (Queens) | 10,107 | 95.0 % | 55.2 % | 0.0 % |
| South Ozone Park (Queens) | 23,684 | 91.3 % | 59.9 % | 0.0 % |
| Laurelton (Queens) | 10,709 | 92.6 % | 59.0 % | 0.0 % |

**The five best, for contrast.**

| Neighbourhood | Buildings | Roof measured | Floors published | Material from a real source |
|---|---|---|---|---|
| Brooklyn Heights (Brooklyn) | 1,490 | 98.1 % | 88.8 % | 86.1 % |
| Upper West Side-Lincoln Square (Manhattan) | 962 | 98.4 % | 88.5 % | 83.1 % |
| Upper West Side (Central) (Manhattan) | 2,757 | 99.0 % | 90.4 % | 79.4 % |
| West Village (Manhattan) | 2,289 | 98.0 % | 82.7 % | 84.8 % |
| Greenwich Village (Manhattan) | 1,224 | 98.1 % | 82.8 % | 75.2 % |

Two things in that contrast are worth stating plainly, because they shape what this world looks like and neither is visible in a citywide average:

* **Facade material fidelity is a map of the LPC historic districts.** The best-documented neighbourhoods are the landmarked ones — Brooklyn Heights and the Upper West Side reach 79–86 % real material because designation reports name a material per building — and the outer-borough neighbourhoods sit at 0.0 %. The rule table (ADR-004) fills the rest, and it is the *only* thing describing those facades.
* **The post-war tower estates and the Rockaways are the thinnest.** Co-op City has published floor counts for under a third of its buildings, and Breezy Point and the Rockaway peninsula for under half. In the Rockaways part of that is real change: the 2014 LiDAR predates the post-Sandy rebuilding, so a house that was replaced is measured as the house that stood before it.

Two whole regions sit below every row of that table and are not in it, because they are not neighbourhoods of the city:

* **New Jersey** (§1.2a) — footprints and 73.7 % of heights, and nothing else measured at all.
* **The outer sea and the marshes** — 1,903 water polygons covering 353.1 km² carry no real name, against 332 polygons over 873.5 km² that do. Names were never invented; `name_source` records where each one came from.

## 10. Every deviation from the brief, with its reason


### A. Structural — these four constrain the whole build

| # | Deviation | Reason | What would close it |
|---|---|---|---|
| A1 | **The Unreal project is authored but never compiled, cooked or run.** 112 C++ files, 27,909 lines, verified only by static analysis. | No Unreal editor, no GPU and no Epic download in this environment (ADR-001). | One workstation pass following `unreal/README.md`. Nothing is known to be missing; nothing is proven to build. |
| A2 | **96.69 % of facades are inferred** — material, window pattern, trim and features come from a rule table keyed on PLUTO class, year built, LPC district and party walls, not from observation. Only 3.31 % carry a material from a real source, and only 0.20 % from OSM tags. | No lawful, feasible source of per-building street-level imagery for 1.08 M buildings here (ADR-004). | Licensed street-level imagery plus a vision model classifying material, window pattern and storefront per facade. The rule table is shaped so such a source replaces the `material_source == 3` rows without a contract change. |
| A3 | **52.43 % of roofs are inferred** from building class and footprint rather than measured, and gable-versus-hip is undetermined — every inferred pitched roof ships as a gable, of which about 36 % are really hips. Measured precision against the OSM sample is 0.805 and recall 0.456: roughly 1 in 5 inferred pitched roofs is wrong, and more than half of the genuinely pitched roofs are missed and stay flat. | The 2014 CityGML LOD2 model covers 95.42 % of footprints; the rest, and all roof *pitch*, is not published. ADR-013 records that the city model carries roof massing, not roof pitch. | A roof-plane classifier on the raw LiDAR point cloud, or an aerial photogrammetric mesh. |
| A4 | **Terrain is 0.384 m RMS vertical accuracy, not the 0.15 m the plan assumed**, and is built from the 3DEP 1 m product rather than the city's 1 ft DEM. | The measured spread is dominated by the time difference between sources (2013–14 LiDAR against 2022 planimetrics) and by real change, not noise — median offset −0.037 m. The 1 ft DEM is a 26.6 GB download against a ~30 GB disk allowance (ADR-005, ADR-017). | Re-run the same terrain stage against `NYC_DEM_1ft_Float`. No code change. |

---

### B. Buildings and facades — `docs/verification/{buildings,citygml,facade,buildings_mesh}/REPORT.md`

| # | Deviation | Reason | What would close it |
|---|---|---|---|
| B1 | **26.60 % of floor counts are derived from height**, not published. | PLUTO does not carry a floor count for those lots. The derivation divides a measured height by the class floor height. | Nothing available; PLUTO is the source of record. |
| B2 | **Facade heading is derived for 100 % of buildings.** No source publishes which side of a building is the front; 88.4 % use the longest non-party-wall edge tie-broken by lot position, and 212 buildings are fully enclosed by neighbours so their heading is arbitrary. | No published attribute exists. | Street-level imagery, as A2. |
| B3 | **Stepped massing is not built.** 28 % of the city (301,311–307,735 buildings) has two or more roof levels with a median 4.44 m step, and setback towers ship as single slabs. | The tables publish level height and level *area* but not the level *outline*. Splitting a footprint by area alone means guessing which limb is the low one, and a 4.4 m step on the wrong side of a house is a visible error dressed as measured data. | Group the CityGML `RoofSurface` rings by z and union them — the triangles are already in `citygml/da*.parquet`. Estimated half a day. |
| B4 | **49,880 storefronts carry generic wording** ("DELI GROCERY", "NAILS & SPA") rather than a real business name; 30,381 of 80,261 have a real name. | DCWP/DOHMH/OSM cover only part of the ground-floor stock. The `awning_real` column marks which is which. | A fuller business licence join. |
| B5 | **Wall billboards are deliberately not placed**, and 53 of 138 kit pieces are never placed. | There is no real source of NYC billboard locations here, and inventing advertising copy would be exactly the fabrication the brief forbids. The other 52 are detail pieces awaiting placement policy, not missing geometry. | A billboard location source; placement policy for the rest. |
| B6 | **Eaves are flush** — pitched roofs stop at the footprint ring with no overhang, fascia or soffit, which is visible on houses at street level. **8 domes are faceted pyramids and 28 complex roofs are flat-plus-parapet.** | Disk budget, and the dome/complex cases need `roofs.glb`, which does not exist yet. | About 6 extra triangles per building for eaves; a Blender stage for `roofs.glb`. |
| B7 | **LOD ratios miss the brief's targets** — LOD1 42.6 % against ~35 %, LOD2 31.1 % against ~8 %. | Arithmetic, not laziness: a closed box costs 12 triangles and the mean LOD0 shell is 47.3, so the LOD2 floor on the small-house stock (70 % of the city) is about 25 %. Reaching 8 % needs open shells, which the brief forbids. | Nothing, without contradicting the no-open-shells requirement. |
| B8 | **213,451 accessory garages (19.7 % of footprints) share a class with multi-storey parking decks.** | `facade_classes.json` has one garage typology. Their material and roof are overridden from real lot evidence so the shells read correctly. | A class 57 `accessory_garage_1fl`, proposed to the kit lane. |
| B9 | **Shell storage is 5.70 GB, not ADR-003's ~1.3 GB estimate; placements are 1.68 GB, not "< 1 GB".** | The estimate did not budget for the LOD chain (+80 %) or per-building vertex attributes (62 % of the LOD0 payload). Draco compresses 4.7× but needs 16+ hours for the city here and makes the geometry unreadable to `pygltflib`. | Amend ADR-003 to ≈3 GB LOD0 / ≈5.7 GB with the chain, and treat Draco as a workstation packaging step. |
| B10 | **Multi-part complexes are one row per BIN, and interiors do not exist.** Every building is a shell. | The base table is keyed by BIN; the brief asks for a drivable exterior city. | Out of scope. |
| B11 | **New Jersey is built, but to a different standard than New York.** 231,382 shells across 486 tiles now stand on the New Jersey shoreline, from FEMA/ORNL USA Structures. Of them: footprints 100 % real, heights real for **73.7 %** and inferred from the ten nearest neighbours for the rest, ground sampled from this project's own terrain surface, and **nothing else measured at all** — no roof shape, no building class, no year built, no floor count, no material. `ROOF_REAL`, `FLOORS_REAL`, `YEAR_REAL`, `MATERIAL_REAL`, `SIGNAGE_REAL`, `SCAFFOLD_REAL`, `LANDMARK_MODEL` and `GROUND_REAL` are zero on every New Jersey row; the whole table holds just two distinct fidelity values. | There is no PLUTO analogue for New Jersey and no LOD2 city model. Floors come from height through an occupancy-class storey table and material from an occupancy × county × height rule; both carry `FLOORS_INFERRED` and `FACADE_INFERRED`. | New Jersey parcel data, if it can be licensed. |
| B11a | **The New Jersey tower heights are badly wrong, and they ship wrong.** Of 39 Jersey City reference towers with a USA Structures height, **not one is within 10 % of its published height**; median error −83.0 m (−60.9 %). Restricted to the 25 towers that already stood when the imagery was flown the median error is still **−66.4 m (−54.4 %)** and 20 of 25 are short by more than 20 m, so this is a measurement failure and not merely a coverage gap. Goldman Sachs Tower is published at 238.1 m and measured at 96.34 m. The tallest building in the whole New Jersey table is 107.48 m; the real tallest is 271 m. | `image_date` is 2013-08-15 on 163,444 of the rows and most of the Jersey City waterfront post-dates it; the source also truncates the towers that did exist. An independent cross-check against OpenStreetMap's own height tags agrees on the shape of the error: −4.7 % below 20 m, **−37.5 % above 80 m**. | The OSM extract already in this repository carries 417 `height` tags and 6,199 `levels` for New Jersey. That is the identified upgrade path; it was not taken, because the instruction was to ship the source as-is and report the error rather than scale anything. **Nothing was scaled or patched.** |
| B11b | **Jersey City still cannot be seen from the Brooklyn Heights Promenade**, the frame that prompted this work. With the shells as built, 13 of the frame's 1,208 columns show a New Jersey roof clearing the New York skyline, by at most 5.6 px. | Geometry, not a missing shell: from that camera the Jersey City waterfront lies *behind* Lower Manhattan, which is half the distance and therefore angularly taller. At the towers' published heights it would be 17 columns and up to 27.8 px — a sliver either way. | Correct heights would make it a visible sliver, not a cluster. The earlier assessment's claim that the photograph shows the *Newport* towers there is wrong: Newport is at bearing 316.9°, 4.68 km out and 1.72° tall against an 8.09° Manhattan skyline. What is visible at the far left is the southern Jersey City / Paulus Hook cluster. |
| B11c | **17 structures on Ellis Island and Liberty Island were dropped** from the New Jersey table, and one LOD0 shell in tile `t_-12_20` is open. | Both islands are covered by USA Structures *and* by the NYC footprint table, several as hand-modelled landmarks; shipping both would have put two shells on one hospital. Dropped by centroid-inside or ≥1 m² overlap with the city boundary, following ADR-019's precedent. The open shell is the same defect class the NYC run reports. | — |

### The photorealism gap, stated as its own item

The comparison assessments are the most direct evidence in the project of the distance between what is built
and a photograph, and three findings recur in almost every frame. They are listed here rather than left in
the individual assessments, because together they are the honest answer to "is it photorealistic".

| # | Deviation | Reason | What would close it |
|---|---|---|---|
| B12 | **Buildings have no glass, no per-building variation and no spandrel banding**, and no texture maps at all. The consequence is measured: the Brooklyn Heights Promenade assessment records the Lower Manhattan towers rendering as "flat pastel solids: pale pink, pale blue, white" against a photograph whose towers are dark glass with strong vertical banding and a tonal range from near-black to specular white, and concludes that **"the skyline reads as a massing study rather than a city"**. | This is the visible consequence of A2: with 96.69 % of facades inferred there is no per-building appearance to key a texture to, and the facade kit places geometry — windows, cornices, fire escapes — rather than painting surfaces. **Correction, recorded rather than quietly amended:** this entry previously said the shells carry "a per-material base colour only", which repeated the comparison assessment's wording and is wrong. `blender/buildings/build_tile.py` sets per-class roughness and metallic (glass_curtain 0.12/0.0, cast_iron 0.45/0.85, limestone 0.65, default 0.72). What is genuinely absent is transmission, IOR and specular — so a curtain wall is a smooth opaque surface rather than glass — plus any variation between two buildings of the same class, and the spandrel band at each floor line. A fidelity report that overstates a gap is as inaccurate as one that hides it. | Authoring, not acquisition: a glass BSDF, per-building variation keyed on the `_LIT_SEED_HI`/`_LIT_SEED_LO` attributes already exported, and banding keyed on the metre UV against the exported `_FLOOR_HEIGHT`. All of it is in the data already. **In progress at the time of writing**, folded into the stepped-massing rebuild so the shells are re-exported once rather than twice. |
| B13 | **Non-building structures at ground level do not exist.** The Brooklyn Heights Promenade deck itself, Brooklyn Bridge Park, the East River piers and the Squibb bridge are all absent, so a camera standing on the promenade stands on bare terrain and its own railing, benches and lamps sit below the parapet line where the deck should be. | No stage produces structures that are neither buildings, roads, nor props. The terrain heightmap flattens them into ground. | A structures stage consuming the planimetric deck and pier polygons, which are already downloaded. |
| B14 | **Water is a mirror.** Roughness 0.06 with no wave normal map makes the East River a perfect reflector of sky and towers; the real surface at that distance is dark, broken and largely non-reflective. The mirrored towers below the waterline are the most conspicuously unreal thing in the frame. | The water normal map is not in the repository (see H3). It is bound by material parameter, so no graph editing is needed. | One texture. |

---

### C. Roads, signals and signs — `docs/verification/roads/REPORT.md`

| # | Deviation | Reason | What would close it |
|---|---|---|---|
| C1 | **Signals are a union of sources, not a published dataset.** 14,466 clusters against DOT's published ~13,700; 1,666 (8.4 %) are inferred and flagged. **Phasing is the DOT standard, not per-controller timing plans.** | DOT does not publish per-controller timing (ADR-007). | A DOT timing-plan release. |
| C2 | **123,891 regulatory signs (19.6 % of the layer) have derived positions.** ONE WAY, DO NOT ENTER, STOP, YIELD and most SPEED LIMIT signs. Their existence and control are real; their exact pole positions are not. | DOT publishes parking regulation signs only. | A sign inventory. |
| C3 | **148,674 crosswalk polygons are derived**, and driveway pavement is not produced at all. | No published crosswalk geometry was available. | A planimetric crosswalk layer. |
| C4 | **7.4 % of widths, 7.1 % of lane counts and 17.4 % of posted speeds are inferred**, all flagged. 3,234 lane stacks are wider than CSCL's own `streetwidth` because its lane counts do not fit its width field. | The source is internally inconsistent for those rows. | — |
| C5 | **8 % of the drivable network is outside the largest strongly connected component** — gated, private and park roads CSCL records that do not join the public network. 0.83 % of travel lanes end without a successor. | Real property of the source. | — |
| C6 | **Bike lanes on one-way streets are always placed on the right of travel**; NYC also uses left-side protected lanes. Affects the side, never the presence, of 14,188 bike lanes. | `bike_trafdir` does not say which side. | A side attribute. |
| C7 | **The pavement layer is from an earlier run of the same code.** Its four planimetric sources were deleted mid-build to free disk, so the final rebuild ran `--no-pavement` and the 972 tile files are unchanged. | Disk exhaustion. The §8 numbers were recomputed by reading those files back, not copied from a log. | Re-download the four sources and re-run `nycsim_pipeline.roads.pavement`. |

---

### D. Street furniture, transit and traffic data — `docs/verification/{furniture,props,traffic_density}/REPORT.md`

| # | Deviation | Reason | What would close it |
|---|---|---|---|
| D1 | **31.6 % of props are rule placements** — 256,843 street lamps, 287,551 manholes, 1,402 steam vents, all flagged `source = 1`. Positions are plausible, not real. | The City publishes no citywide location dataset for any of the three. The lamp *count* is close to the published fleet size; the manhole and steam-vent counts are stated modelling choices. | A utility asset inventory. |
| D2 | **Tree height is estimated for all 650,516 trees.** | The census records species and trunk diameter but no height. The curve is a saturating fit to published mature heights; no per-tree truth exists to validate against. | — |
| D3 | **Prop z comes from survey points, not the terrain raster** the engine will render. | `tiles/{tile}/terrain.png` did not exist during that run. Flagged `z_source` 3/4; 0.58 % extrapolated from over 80 m away. | A resample pass against the finished terrain. |
| D4 | **GTFS is one representative weekday** (2026-09-09). Weekend, night and seasonal services are absent entirely. | The feed snapshot. | A multi-day GTFS ingest. |
| D5 | **Deck heights are 60.7 % measured**; 2,625 above-grade structures use their class median. Open-cut depth is not produced at all. | No *Bridge Elevation* point within 25 m. Measuring open cuts from surrounding bridge points would be wrong. | Denser elevation points. |
| D6 | **Manufacturer geometry is not reproduced** for the Better Bin, LinkNYC kiosk, Cemusa shelter and newsstand, Muni-Meter, Citi Bike bicycle and food carts — published dimensions and a recognisable silhouette, not part-for-part models. **Trees are procedural, not scanned. Sign legends are MUTCD defaults, not per-instance text.** | No licensed CAD (same statement as ADR-009 for vehicles). Real per-instance sign text arrives at runtime through the `SIGN_FACE` slot. | Licensed CAD; the `roads/signs.parquet` wiring. |
| D7 | **Citywide vehicle-kilometres land 15–30 % below the published state figure** (91.2 M against 105–130 M). **Weekend modal shares reuse weekday shares. Bicycle shares are not from the classification counts.** | DOT's classification counts are weekday-only and carry no bicycle class; the bicycle fit was scaled by 0.655 to reproduce the published citywide figure. Densities are per lane so the spatial pattern is unaffected, but the table must not be used as a citywide VMT estimate. | Weekend classification counts. |
| D8 | **Emergency-vehicle activity is the least grounded part of the fleet mix**, and **school buses have no vehicle class** — the bus share resolves entirely to transit buses. | Fleet sizes are published; daily distance and duty cycles are assumptions, each carrying a `basis` string. | Fleet telematics. |

---

### E. Vehicles and character — `docs/verification/{vehicles,character}/REPORT.md`

| # | Deviation | Reason | What would close it |
|---|---|---|---|
| E1 | **Vehicles are dimensionally exact but not photoreal.** Surfaces are lofted from station tables, so panel creases, shut lines, grille meshes and badge relief are approximate; `fusion_exterior.png` reads as *a* mid-size sedan of the right size, not as a recognisable 2019 Fusion. **No PBR texture maps at all** — materials are analytic, with no albedo, normal, ORM, dirt or wear layers. | No licensed CAD or scan data (ADR-009). Worst dimensional deviation is 1.85 %, most are 0.00 %. | Reference-photo modelling or scan data; an authored texture set. |
| E2 | **The player car's greenhouse is packaged too far forward.** The windscreen header sits 0.35 m ahead of the driver's eye where a real Fusion has ≈0.75 m; the interior render needed an 80° lens to get the A-pillars in shot. | A blueprint error in the fore-and-aft split between bonnet, screen and roof. Overall height, length and H-point are right. | Re-cut the `X_ROOF_F`/`X_COWL` stations, which moves every panel on the flagship model. |
| E3 | **Hair is a solid shell, not cards and not strands.** At portrait range it reads as a helmet: no flyaways, no strand shading, no anisotropic highlight, and no card silhouette either. Measured open-edge ratios across all ten MakeHuman CC0 hair assets: `short02` and `short03` are 0.05, which is a closed cap; `braid01` is 0.46 and still renders as a smooth helmet with no visible braid; only `afro01` (0.51) genuinely clumps. Alpha is wired on all ten — the meshes simply are not card-built. The lane calls this its single biggest fidelity gap and it is right. | Those ten assets are the entire MakeHuman CC0 hair library, so there is nothing better to switch to. No CC0 groom asset was reachable and an authored groom is a multi-day job. The rig and scalp are ready for one. | A groom asset, or authored hair cards. |
| E4 | **MakeHuman's CC0 packs contain exactly one casual jacket and no boots.** `jacket_field`, `jacket_denim`, `jacket_leather`, three puffers and two coats are all `male_casualsuit05` in eight fabrics, so a "long" coat is hip-length and a puffer has no quilting; a city that wears work boots is shod in trainers and loafers. | The asset library. Both alternatives were built and rejected on the render: cut from the tee it comes out a beige t-shirt, cut from the skin a painted-on bodysuit. | Licensed or authored garments. |
| E5 | **Carried items are bevelled boxes** — a backpack, tote, shoulder bag, courier's box and briefcase are each one box with no straps, handles or soft shape. **Garments have no zips, buttons, plackets or cloth simulation.** | Authoring cost. They read at street distance and are wrong close up. | Authored props and a cloth setup. |
| E6 | **No facial rig beyond blendshapes, no LODs, no cloth or hair physics**, and subsurface skin is authored for Cycles but invisible in glTF, which has no SSS. | Runtime-side work. Jaw motion is morphs only; the eyes are separate objects the runtime rotates. | An engine pass. |
| E7 | **`run` is a time-compressed 3.6 m/s run, not a 5 m/s sprint, and the idle's motion is authored** — only its posture is mocap. | No idle capture exists in the fourteen downloaded CMU files. | More mocap. |
| E8 | **Millimetre slivers of the base top still show through the knit at the shoulder and chest**, and the orchestrator's review of 2026-09-06 additionally found the trouser hem passing through the sneaker heel, fingertips buried in the trousers in the rest pose, and carried props floating unattached to the hand. | Linear blend skinning moves two fitted meshes slightly differently; the clearance that would close the first starts to flatten the knit. The other three were open at the time of writing and are being worked. | Garment-versus-garment resolution extended to the bottoms/feet pair and to the rest pose. |

---

### F. Traffic, pedestrians and performance — `docs/verification/{traffic,performance}/REPORT.md`

| # | Deviation | Reason | What would close it |
|---|---|---|---|
| F1 | **The 8 ms step budget is not met. Synthetic 14.0 ms; city-scale 777 ms.** | At city scale about 709 ms of the 777 is destination selection over the whole graph rather than the streamed region (ADR-021); the rest is the lane array growing from 470 KB to 85 MB. Synthetically the remaining time is spread thin — nothing left is worth more than about 5 %. | ADR-021's streamed-region fix, then multithreading across tiles, which is the only change reaching 8 ms without touching the models. |
| F2 | **The jaywalking share (0.30) and box-blocking probability (0.02–0.35) are modelling targets, not measurements.** | No New York field count of signal non-compliance exists here. 0.30 sits inside the 20–50 % range in the literature and is a single exposed constant. | A pedestrian-count stage. |
| F3 | **Jaywalking is modelled as crossing against the signal at a crosswalk**, not as mid-block crossing with its own geometry. | Modelling choice. | Mid-block crossing geometry. |
| F4 | **22 of 3,000 sampled frames catch one vehicle pair mid-separation** at a junction entry, each clearing within two or three frames. | The impenetrability projection runs at the end of each step. The two tests that cannot assert an exact zero carry the measured value and the reason in the assertion. | A continuous-collision formulation. |
| F5 | **A published traffic figure of 35.57 ms was not reproducible** and is corrected in place to 14.6 ms. | Contention with five other agents on four cores. Every behaviour counter was identical; only the machine differed. | — (recorded so the wrong figure is not quoted again). |

---

### G. Time, weather and audio — `docs/verification/{live,unreal_gameplay}/REPORT.md`

| # | Deviation | Reason | What would close it |
|---|---|---|---|
| G1 | **Wetness, puddles, umbrella probability, snow thresholds and road-clearing rates are modelled, not measured**, and one city-wide clearing rate is applied to every street class. | NYC publishes no per-street wetness or umbrella telemetry. Each is a documented closed-form rule with a named, sourced constant. | Telemetry that does not exist. |
| G2 | **The snow-depth model has never been exercised against a real snow event** (it is September), and the forecast blend is unvalidated beyond a single adverse sample. | Season. Its terms are unit-tested individually and its constants sourced. | A winter run. |
| G3 | **Manhattanhenge disagrees with the published dates** by 1 day in May and 3 in July. | The published dates are internally inconsistent; the azimuth criterion is met exactly and the sensitivity table ships. | — |
| G4 | **No New York field recording is used for ambience.** The one Commons candidate for "city traffic ambience" turned out to be a railway-station tunnel recorded in Tampere; it is licensed and kept with its record but no zone plays it. The traffic bed is synthesised from the vehicles actually around the listener. | No lawful NYC field recording was reachable. | A licensed NYC ambience set. |
| G5 | **MetaSound graphs are not authored**; the five documented sources are C++ DSP with an identical parameter contract. | The MetaSound builder API is experimental in 5.4 and cannot be exercised here. `UNYCVehicleAudioComponent` prefers a MetaSound asset the moment one exists. | A workstation pass; no engine work needed to adopt them. |
| G6 | **Pedestrian↔vehicle coupling lags one step** — a driver reacts to a pedestrian 50 ms late. | The obstacle set handed to the traffic simulation is the previous step's. Core's `traffic/Interop.h` is designed to remove exactly this. | Adopt `Interop.h` with the traffic-simulation merge. |

---

### H. Unreal world assembly — `docs/verification/unreal_world/REPORT.md`

| # | Deviation | Reason | What would close it |
|---|---|---|---|
| H1 | **Landscape sample spacing is 1.98413 m, not 2.00 m.** | UE requires `SubsectionSizeQuads` in {7,15,31,63,127,255} and 500 quads is divisible by none of them. The importer resamples bilinearly to 504 quads and keeps the tile exactly 1 km wide; measured cost 0.002 m, and exactly zero at tile borders. The vertical data is untouched. | Export 505-sample heightmaps directly and set `component_size_quads: 63`. |
| H2 | **The four Niagara weather systems cannot be authored here**, so rain, snow, spray and fog particles are absent until a workstation pass. | UE 5.4 exposes no Python API for Niagara graphs. The subsystem logs one warning per missing system and every other weather effect stays live. | `unreal/README.md` §6 — the single manual step, with the exact user-parameter contract. |
| H3 | **The star texture and the water normal map are not in the repository**, so the star sphere is skipped and water uses a flat normal with flow-driven roughness. | No suitable licensed texture was fetched. Both are bound by material *parameter*, so dropping a texture in needs no graph editing. | Two textures. |
| H4 | **Sidewalk geometry is derived**, offsetting each centreline by `width/2 + 1.9 m`, not planimetric. | The planimetric sidewalk polygons were among the four sources deleted for disk (C7). | `GameplayPedSim::buildSidewalks()` is the one function to change. |
| H5 | **`landmarks.nycb` has no layout in DATA_CONTRACTS §15**, so landmark search is unavailable. | Unspecified contract. The reader reports its absence in the load notes rather than guessing. | Specify the section. |

---

### I. Landmarks and verification — `docs/verification/{landmarks,reference,comparison}/REPORT*.md`

| # | Deviation | Reason | What would close it |
|---|---|---|---|
| I1 | **Sculpture is modelled as blocked-out mass, never as figures** — the Bronx County Courthouse's sculpture groups, the Brooklyn Museum's 30 allegorical figures, the AMNH equestrian statue and the Brooklyn Public Library's fifteen bronzes are plinths and blocks. | Deliberate: inventing figure geometry would be worse than the honest gap. | The props/character competence, not the landmarks lane. |
| I2 | **Detail screens are built at reduced density.** The New York Times Building's ceramic rods are one in five (0.60 m centres against the real 0.127 m); the Javits Center's space frame follows the 90 ft structural grid, not the 5 ft module. | 186,000 rods at ~12 triangles each is ~2.2 M triangles for one facade, five times the whole group's budget. Both are stated in the catalog `dimensions`. | A triangle budget that does not exist. |
| I3 | **Two landmark heights are inferred** — Arthur Ashe Stadium (46.0 m, scaled from the published section, ±2 m, because the LiDAR predates the 2016 roof) and Two Times Square (the LiDAR roof including its sign tower). Both flagged in the catalog. | No architectural height is published for either. | A published figure. |
| I4 | **Three footprint polygons had to be divided** because one BIN covers two buildings (Shops at Hudson Yards / 30 Hudson Yards; 15 Hudson Yards / The Shed; 111 West 57th / Steinway Hall). Each cut uses a vertex already in the polygon and each is named as an inference. | The source keys by BIN. | — |
| I5 | **No interiors anywhere**, except volumes visible from the street through glass. | Scope. | — |
| I6 | **One reference subject has a single photograph** (Staten Island ranch houses) and seven have 2–3 instead of 3–4. | Commons has essentially no freely licensed street photography of ordinary Staten Island tract housing; the candidate pool was exhausted after licence, date and content filtering, and each `meta.json` records `"exhausted": true` with its rejection histogram. Padding the subject with photographs of something else was rejected. | A different photo corpus. |
| I7 | **Street-axis subjects carry the subject's azimuth, not the photograph's.** | Nothing in the file metadata gives a camera heading; every such explanation says exactly that. | EXIF that does not exist. |
| I8 | ~~Six comparison scenes render near-black and one not at all~~ — **closed. All 57 scenes now have a usable render, a sheet and a written assessment.** The last of them, the 9/11 Memorial Pools, was black for two independent reasons, and both were camera-placement faults rather than anything wrong with the world. | The first: `ground_z(mode="street")` took a low percentile of the terrain in a radius and found the bottom of a memorial pool — a 9 m void a few metres away — putting the eye 1.4 m under the paving. The second: the WTC site model's own plaza slab (I11) covered the camera. Four landmark-stage renders were red for the same class of reason and are also fixed: a camera 7.9 m underground, one inside a terrace prism, one under a boardwalk aimed 19° off, and two wall views too small to read. | — |
| I9 | **The "is this eye point indoors" test was an upward ray cast**, which cannot tell a ceiling from foliage, an awning, a scaffold shed or a bridge deck — all of which exist in this world and all of which a person stands under. | An upward hit was taken as proof of being inside a shell. | Fixed: the ray now steps past trees and reports the first *built* thing overhead, identifying foliage by material after checking those materials appear on tree geometry and nothing else across 122 props, 127 landmarks, 138 kit pieces and the tile shells. |
| I10 | **Two comparison sheets are stale.** `landmark_oculus` (pitch −3.3° → −0.3°) and `landmark_one_world_trade_center` (camera moved 39 m and its clearance rule fell to "open air only") were placed under the pre-fix camera code and not re-rendered. | 1WTC's new placement is worse by the search's own criteria, so re-rendering risked replacing a working sheet with a poorer one. Measured and recorded rather than silently left. | Re-render once the placement search is improved, or accept the older, better frame and say which code produced it. |
| I11 | ~~The WTC site model stands about 2.6 m too high and its plaza has no pool openings~~ — **closed and verified.** `origin_tm` z is now 4.40 m and the plaza measures 4.10–4.40 m NAVD88 (it was exactly 7.000 m); the plaza is 116 triangles with the two 61 m pool openings cut and not one triangle inside either, against the 2-triangle unbroken quad it was; the impostor card is gone from the oak mesh; the model's maximum z is 330.60 m, which is 3 WTC's published 329.2 m plus its 1.4 m mast exactly. | `GRND` served as both the local datum and the frame origin's NAVD88 z, so plaza level was counted twice. It is now two constants. The 4.40 m was chosen on evidence, not assumed: the published terrain reads 4.405 m at the frame origin, the median over the plaza deck is 4.341 m, and the choice puts this entry 0.005 m from the convention the other 92 catalogue entries follow. The plaza is also clipped to the real OSM outline (33,039 m² against a published 8 acres = 32,375 m²) instead of a 520 × 520 m quad. | — |
| I11a | **The two pool centres were derived and wrong, and are now measured.** They were **31.8 m** and **30.1 m** out of position with the squares **41.4° mis-rotated**. | The script recorded that no polygon existed for the individual pools. OpenStreetMap carries both, as ways 697722178 and 697722181, in the extract already in this repository. The corrected 29.25° edge heading agrees with the real 3 WTC (26.5°) and 4 WTC (29.4°) footprints. | — (closed; recorded because a derived value was presented as the best available when a real one was on disk). |
| I11b | **No water is visible in the memorial-pools comparison frame**, even with the plaza cut open. | Two measured reasons, neither a modelling fault. Optics: from a 1.6 m eye at the 1.07 m coping the sight line falls 0.137 m/m and needs 74.6 m of run to reach water 10.19 m down, but the basin is 56.6 m across — a person standing there cannot see the water either, and the reference photograph tilts about 40° down, which the level-axis rule forbids. And the scene draws terrain straight through the pool: nothing cuts terrain under a landmark's own ground, so the heightmap inside the pool square reads a median 1.86 m against a modelled basin reaching −4.74 m. | Cut terrain and pavement under a landmark's own ground plane. The landmark render `b_wtc_site/memorial_plaza.png` does show the opening, the basin and the central void. |
| I11c | **The Oculus is 32° off its own footprint** — `PLAZA_AXIS_DEG` is 160.6° against the real BIN 1089309 long axis at 128.2°, and its east end crosses into 3 WTC's footprint. | Found while fixing the plaza; it belongs to the Oculus sheets, not this pass. Measured and recorded in the model's fidelity statement and both reports rather than moved, because moving it changes scenes in another lane. | Re-derive the Oculus axis from BIN 1089309. |
| I11d | **`b_wtc_site` had no verification renders on disk at all.** | `b_common.prop_template` kept a template cache across `new_scene()`, and touching `ob.name` on a removed StructRNA raises, so the render pass crashed before writing anything. Fixed; it has six renders now. | — |
| B16 | **Inland water renders dry.** Central Park's Lake, its ponds, the Staten Island reservoirs and the Bronx and Queens lakes are all absent from the verification renders: the Bethesda Terrace sheet, one of the nine the brief mandates, shows the terrace balustrade correctly and then bare grey ground where the photograph has the Lake filling its upper third. Measured: **121 of the 1,743 water-bearing tiles carry a water plane below their own lowest ground** — median 8.01 m below, worst 58.34 m — so no water surface can be produced there at all. | Not a data gap: `hydrography.parquet` holds all 2,235 bodies and **946 non-tidal ones carry a real surface level** from −0.55 m to 118.65 m, with exactly one sitting at 0.0. The loss is at the tile boundary — `terrain/tiles.py` writes `"water_level_m": 0.0` as a hard-coded constant, and the scene builder then masks water as `z <= water_level + 0.05`, which on an inland tile selects nothing. | **Not by patching the constant**, which I tried and rejected on measurement: setting each of the 121 tiles to its dominant body's level leaves only 30 safe, and on the other 91 the threshold mask would flood up to **76 m of real relief**, turning hillsides into lakes. One scalar plus a height threshold cannot describe a tile holding a pond at 118 m over ground at 52 m, nor a coastal tile holding both the sea and a pond. The fix is a per-polygon water mask in the scene builder, using each body's own `water_z_m`. Handed to the verification lane, which is already in that file. |
| I13 | **Every comparison sheet shows an empty city.** 51 of the 57 written assessments record that there are no people in the frame and 37 that there are no vehicles. The verification scene places neither: `blender/verify/scene.py` loads terrain, buildings, shells, kit, props and landmarks, and no agent of any kind. | This is a limitation of the *verification* path, not of the world: the traffic and pedestrian simulations exist, are tested, and hold their invariants (zero red-light entries, zero wall crossings, saturation flow 1,708.6 veh/h/lane) — they simply do not feed the still renderer. It matters because it is systematic: a reader going through 57 sheets would reasonably conclude the city is unpopulated, and every sheet in this report understates the world in the same direction. | Place a simulation frame's agents into the verification scene. The snapshot format already exists for the Unreal runtime. |
| B15 | **No commercial signage geometry exists anywhere** — not a billboard, not a screen, not an illuminated shopfront sign. The Times Square assessment puts it plainly: *"This single absence is the difference between 'a Midtown avenue' and 'Times Square', and it is the largest gap in the whole comparison set."* The reference photograph there is roughly 60 % illuminated advertising by area. | The *data* is computed and shipped — the facade stage produces `awning_text` for 80,261 storefronts and a `has_billboard` flag per building — but no stage turns either into geometry, and the facade kit's two billboard pieces are among the 53 that are never placed. Deliberately so for wall billboards (B5): there is no real source of NYC billboard locations here and inventing advertising copy would be exactly the fabrication the brief forbids. That reasoning covers *content*; it does not explain the absence of a lit surface. | Place the kit's billboard and screen pieces on the buildings whose `has_billboard` flag is set, lit and blank or carrying the generic wording the awning system already uses, rather than leaving the surface absent altogether. Real copy still needs a source. |
| I12 | **The reference metadata has two faults that produce misleading sheets.** The Washington Square Arch sheet compares two different views — its photograph is of skateboarders at the fountain and does not contain the Arch — because the heading came from a camera-GPS-to-subject bearing that assumes a photograph taken *at* a viewpoint is a photograph *of* it. The Williamsburg Bridge camera sits 500 m too far back because a 250 m rule rejected a photograph's own GPS, which was correct at 117 m, in favour of a nominal viewpoint that was not, at 506 m. | Both are in the reference chooser and its distance rule, not in the comparison lane. The chooser also scored one photograph 14.2 on a subject it does not show. | Fix the chooser's subject test and the distance rule; both would move scenes across lanes, so they are documented rather than changed in place. |

---

### What is *not* on this list

Two things, stated so their absence is not mistaken for an oversight:

* **Nothing was found where a procedural or approximated result is presented as real.** Every inference in
  this build carries a flag in the data (`*_source` columns, the fidelity bitfield) and a sentence in its
  stage report. The one time that failed it was in the *accounting* rather than the world: the fidelity
  report itself reported 0 % inferred facades and 0 % inferred roofs for a period, because its generator
  counted those bits in a table that does not set them. That is recorded in `docs/DEFINITION_OF_DONE.md`
  and is now guarded by a test.
* **No deviation here was discovered by an agent's self-report alone.** Each was either declared by the
  lane that made it or found by the orchestrator opening the artefact. Four defects were reported as
  successes by the stage that produced them and found only by inspection: 32.8 M kit placements pointing
  at assets that did not exist, a 1,003 km² stretch of New Jersey highland modelled as sea, a packed C++
  struct that made the road graph unreadable to the router, and a character whose garments all carried
  the wrong vertex weights.

That is **79 deviations**, each with the stage report it is drawn from. The source document is `docs/DEVIATIONS.md`.

## 11. Next steps, in the order I would do them

Ordered by what each one buys against what it costs, not by how hard it is. Every one of these is traceable to a numbered deviation in §10, where the measurement behind it is stated.

1. **Compile, cook and run the Unreal project on a workstation** (A1). Everything downstream of it is unknown until it is done: frame rate, vehicle feel, audio, streaming under a real GPU, and the brief's first condition — driving from any address to any other. 112 C++ files and 27,909 lines are authored and statically checked, and nothing is known to be missing, but nothing is proven to build. `unreal/README.md` has the steps; §6.1 lists the four static checks that pass and what they do *not* cover.
2. **Put a real material set on the building shells** (B12). This is the largest single gain in visual fidelity available without new data: shells carry a per-material base colour and nothing else, so the Lower Manhattan skyline renders as flat pastel solids against a photograph of dark banded glass. A glass BSDF, spandrel banding and an albedo/roughness set keyed on the `facade_class` and `material_primary` already in the data would change every comparison sheet in this report. It needs authoring, not acquisition.
3. **Licensed street-level imagery and a vision model** (A2). The single largest *data* gap: 96.69 % of facades are inferred from real attributes rather than observed. The rule table is deliberately shaped so a real source replaces its rows without a contract change, so this is an ingest, not a rewrite.
4. **A roof-plane classifier on the raw LiDAR** (A3). 52.43 % of roofs are inferred, gable-versus-hip is undetermined, and about 1 in 5 inferred pitched roofs is wrong. This is the second-largest data gap and the point cloud it needs is public.
5. **Re-run the terrain stage against the 1 ft city DEM** (A4). No code change: the stage already consumes it, and it was skipped only because 26.6 GB did not fit the disk allowance here. Would take vertical accuracy from a measured 0.384 m RMS toward the 0.15 m the plan assumed.
6. **A structures stage for what is neither building, road, nor prop** (B13). Promenade decks, park terraces, piers and pedestrian bridges are absent, so a camera standing on the Brooklyn Heights Promenade stands on bare terrain. The planimetric polygons are already downloaded.
7. **New Jersey heights from OSM** (B11a). The shipped source understates Jersey City's towers by a median 66 m; the OSM extract already in this repository carries 417 `height` tags and 6,199 `levels` for New Jersey. A bounded ingest against data on disk.

Everything above is work this project identified by measuring its own output. None of it is a reconsideration of the plan; the plan is in `docs/ARCHITECTURE.md` and it held.

