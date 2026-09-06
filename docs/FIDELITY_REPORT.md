# Fidelity Report

Generated 2026-09-06 12:25 UTC from commit `7681d64744ab` by `pipeline/nycsim_pipeline/report/fidelity.py`.

Every figure below is read from an artefact on disk at generation time. Where an artefact does not exist, the row says **not produced** rather than showing a zero. Nothing in this report is an estimate unless it is labelled as one.

## 1. Buildings

Total buildings modelled: **1,083,026** (source of truth: NYC Open Data Building Footprints, `data/processed/buildings/buildings_base.parquet`).

### 1.1 By borough

| Borough | Buildings | Median height (m) | Max height (m) | Height real | Floors real | Roof real | Material real |
|---|---|---|---|---|---|---|---|
| Manhattan | 45,194 | 17.75 | 472.44 | 99.83 % | 84.77 % | 96.58 % | 0.00 % |
| Bronx | 104,278 | 8.43 | 137.16 | 99.82 % | 76.68 % | 95.93 % | 0.00 % |
| Brooklyn | 330,154 | 8.37 | 315.47 | 99.93 % | 77.88 % | 97.06 % | 0.00 % |
| Queens | 460,939 | 7.42 | 242.01 | 99.97 % | 66.42 % | 94.50 % | 0.00 % |
| Staten Island | 142,461 | 7.89 | 64.61 | 99.94 % | 79.63 % | 93.86 % | 0.00 % |

### 1.2 Attribute provenance across the whole city

| Bit | Flag | Meaning | Buildings | Share |
|---|---|---|---|---|
| 0 | `FOOTPRINT_REAL` | footprint from the NYC OTI photogrammetric dataset | 1,083,026 | 100.00 % |
| 1 | `HEIGHT_REAL` | roof height from the LiDAR-derived `height_roof` field | 1,082,290 | 99.93 % |
| 2 | `ROOF_REAL` | roof geometry from the CityGML LOD2 model | 1,033,416 | 95.42 % |
| 3 | `FLOORS_REAL` | floor count from PLUTO | 794,995 | 73.40 % |
| 4 | `YEAR_REAL` | year built from PLUTO / footprint dataset | 1,075,197 | 99.28 % |
| 5 | `MATERIAL_REAL` | facade material from an OSM tag or an LPC designation report | 0 | 0.00 % |
| 6 | `SIGNAGE_REAL` | at least one real business name attached to the ground floor | 30,381 | 2.81 % |
| 7 | `LANDMARK_MODEL` | replaced by a hand-scripted landmark model | 0 | 0.00 % |
| 8 | `SCAFFOLD_REAL` | sidewalk shed from an active DOB permit | 6,396 | 0.59 % |
| 9 | `GROUND_REAL` | ground elevation from the LiDAR-derived field | 1,082,833 | 99.98 % |
| 10 | `FACADE_INFERRED` | facade appearance inferred by the rule set (ADR-004) | 0 | 0.00 % |
| 13 | `ROOF_INFERRED` | roof shape derived from building class and footprint (ADR-013) | 0 | 0.00 % |
| 11 | `HEIGHT_INFERRED` | height derived from floor count or neighbours | 736 | 0.07 % |
| 12 | `FLOORS_INFERRED` | floor count derived from height | 288,031 | 26.60 % |

Buildings whose footprint **and** height are both from measurement: 99.93 %.

Per-tile files with the complete §5 schema: 0 of 25 sampled (920 tiles hold buildings).
First schema gap seen: ["missing column 'roof_type'", "missing column 'roof_mesh_ref'", "missing column 'facade_class'", "missing column 'material_primary'", "missing column 'material_secondary'", "missing column 'window_type'"]

### 1.3 Roof geometry (CityGML LOD2)

Delivery areas parsed: **20 of 20**; buildings with parsed LOD2 geometry: **1,083,281**.

Roof-type distribution: flat 1,083,377, complex 27, hip 12, mansard 8, dome 5, gable 4, barrel 2, shed 2.

## 2. Road network

Source of truth: NYC Street Centerline (CSCL) and LION, per ADR-006.

- Segments: **122,235**
- Total centreline length: **12,997.29 km**
- Nodes: 79,291 · lanes: 384,703 · junction lanes: 470,016
- Signalised intersections: 19,814 · signs: 633,287
- Named bridges and tunnels resolved: 53
- Posted speed from data (not inferred): 82.6 % of segments
- Lane count from data (not inferred): 92.9 % of segments

| Borough | Centreline km |
|---|---|
| Queens | 4,680.2 |
| Brooklyn | 3,111.4 |
| Staten Island | 1,908.3 |
| Bronx | 1,861.5 |
| Manhattan | 1,435.9 |

## 3. Terrain, water and coastline

- Tiles with a written heightmap: **2,338**
- USGS 3DEP products ingested: 30 (13, 19, 1m), 4.50 GB
- Elevation range across written tiles: -5.18 m to 196.68 m (NAVD88)

Water: hydrography polygons 2,253 · shoreline lines 413 · structures 2,536 · water tiles 2,916.

## 4. Street environment, transit and traffic model

- Tiles with props: 1,576 · total props placed: 1,724,589
- Bus routes 345 · bus stops 13,364 · subway entrances 2,120 · rail structures 8,341 · ferry routes 6
- Traffic density cells: 18,864

## 5. Authored assets (Blender)

| Group | glTF files | Size |
|---|---|---|
| kit | 138 | 140.1 MB |
| props | 122 | 78.1 MB |
| vehicles | 24 | 29.2 MB |
| character | 1 | 15.1 MB |
| landmarks | 47 | 497.3 MB |
| tiles | 42 | 244.0 MB |

Catalog entries describing those assets: 315.

## 6. Simulation code and runtime data

- `core/`: 52 headers, 37 sources, 19 test files; registered ctest cases: 11
- Runtime binaries: `density.nycb` 0.9 MB, `roadgraph.nycb` 104.5 MB, `signals.nycb` 1.7 MB, `transit.nycb` 2.4 MB

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

Reference photographs collected for side-by-side comparison: 123 photos across 40 subjects, each with author and licence metadata.

Stage reports present: citygml, core, furniture, live, unreal_world.

Stage reports still missing: buildings, buildings_mesh, facade, kit, landmarks, props, reference, roads, terrain, traffic, traffic_density, unreal_gameplay, vehicles, character.

What is verified in this environment versus on a workstation is defined in `docs/ARCHITECTURE.md` §14. In short: geodesy, tiling, streaming logic, routing, traffic rules, signal phasing, astronomy, time zone handling, weather parsing, data coverage and asset geometry are verified here by tests and Cycles renders. Unreal Engine compilation, cooking, frame rate, vehicle feel and audio are not — no Unreal editor or GPU exists in this environment, and no claim is made that they were tested.

## 9. Known gaps against the brief

| # | Gap | Why | What would close it |
|---|---|---|---|
| 1 | Facade appearance is inferred from real attributes, not matched to photographs of each building | No lawful, feasible per-building street-level imagery source for 1.08 M buildings in this environment (ADR-004) | Licensed street-level imagery plus a vision model to classify material, window pattern and storefront per facade |
| 2 | Unreal side is authored but never compiled or run | No Unreal editor, no GPU, no Epic download in this environment (ADR-001) | One workstation pass following `unreal/README.md` |
| 3 | Terrain is LiDAR-derived at 2 m rather than the 1 ft city DEM | The 1 ft DEM is a 26.6 GB download against a ~30 GB disk allowance (ADR-005) | Re-run the same terrain stage against `NYC_DEM_1ft_Float`, no code change |
| 4 | Vehicle and character models are built from published dimensions, not manufacturer CAD or scans | No lawful source for either (ADR-009, ADR-010) | Licensed CAD, or photogrammetry |

Anything else that fell short is stated in the stage reports under `docs/verification/`, and each of those reports is written by the agent that did the work and reviewed by the orchestrator.

