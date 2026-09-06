# Fidelity Report

Generated 2026-09-06 22:33 UTC from commit `c23a45dbe54e` by `pipeline/nycsim_pipeline/report/fidelity.py`.

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
| character | 11 | 221.4 MB |
| landmarks | 127 | 920.5 MB |
| tiles | 1,010 | 4,624.0 MB |

Catalog entries describing those assets: 386.

## 6. Simulation code and runtime data

- `core/`: 52 headers, 37 sources, 19 test files; registered ctest cases: 11
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

Per-subject reports underneath those: comparison 29, facade 1, landmarks 34, reference 2, traffic_density 2.

What is verified in this environment versus on a workstation is defined in `docs/ARCHITECTURE.md` §14. In short: geodesy, tiling, streaming logic, routing, traffic rules, signal phasing, astronomy, time zone handling, weather parsing, data coverage and asset geometry are verified here by tests and Cycles renders. Unreal Engine compilation, cooking, frame rate, vehicle feel and audio are not — no Unreal editor or GPU exists in this environment, and no claim is made that they were tested.

## 9. Every deviation from the brief, with its reason


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
| B11 | **New Jersey has terrain but no buildings.** 1,104 tiles of New Jersey shoreline carry a heightmap and nothing standing on it, so every view west from Manhattan shows bare ground where Jersey City, Hoboken and Newark stand. The comparison lane found it independently on the Brooklyn Heights Promenade frame. | The brief's scope is the five boroughs *plus* the New Jersey shoreline. 231,336 NJ buildings from FEMA/ORNL USA Structures were downloaded, parsed and written to `data/processed/nj/`, and then never tiled — the tiling stage is NYC-only. | Tile them and build their shells; the data is on disk. **In progress at the time of writing.** Note that the source carries a height for only 73.7 % of them, none of their ground elevations, and no roof geometry at all, so New Jersey will never reach the fidelity of the five boroughs. |

### The photorealism gap, stated as its own item

The comparison assessments are the most direct evidence in the project of the distance between what is built
and a photograph, and three findings recur in almost every frame. They are listed here rather than left in
the individual assessments, because together they are the honest answer to "is it photorealistic".

| # | Deviation | Reason | What would close it |
|---|---|---|---|
| B12 | **Buildings have no facade textures and no glass.** Every shell carries a per-material base colour only — no albedo or normal maps, no glass BSDF, no spandrel banding, no fenestration readable at distance. In the Brooklyn Heights Promenade frame the Lower Manhattan towers are "flat pastel solids: pale pink, pale blue, white" against a photograph whose towers are dark glass with strong vertical banding and a tonal range from near-black to specular white. **The skyline reads as a massing study rather than a city.** | This is the visible consequence of A2: with 96.69 % of facades inferred there is no per-building appearance to texture from, and the facade kit places geometry (windows, cornices, fire escapes) rather than painting surfaces. | The A2 fix — licensed street-level imagery and a vision model — plus an authored material set with a glass BSDF. This is the single largest gap between this build and photorealism, and it is a material and imagery problem, not a geometry one. |
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
| E3 | **Hair is alpha-textured polygon cards, not strands.** At portrait range it reads as cards: no flyaways, no strand shading, no anisotropic highlight. The lane calls this its single biggest fidelity gap. | No CC0 groom asset was reachable and an authored groom is a multi-day job. The rig and scalp are ready for one. | A groom asset. |
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
| I8 | **Six comparison scenes still render near-black and one fails to render**, so 50 of 57 scenes are usable. The render gate fails on exactly those seven and is left failing. | Under investigation at the time of writing; the evidence points at the camera being inside geometry for some and outside the loaded region for others. | Fix the camera placement, or drop the scene and say so — never ship a black frame or widen the gate. |

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

That is **65 deviations**, each with the stage report it is drawn from. The source document is `docs/DEVIATIONS.md`.

