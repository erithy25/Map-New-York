# Fidelity Report

Generated 2026-09-06 11:13 UTC from commit `7d287e091886` by `pipeline/nycsim_pipeline/report/fidelity.py`.

Every figure below is read from an artefact on disk at generation time. Where an artefact does not exist, the row says **not produced** rather than showing a zero. Nothing in this report is an estimate unless it is labelled as one.

## 1. Buildings

Total buildings modelled: **1,083,026** (source of truth: NYC Open Data Building Footprints, `data/processed/buildings/buildings_base.parquet`).

### 1.1 By borough

| Borough | Buildings | Median height (m) | Max height (m) | Height real | Floors real | Roof real | Material real |
|---|---|---|---|---|---|---|---|
| Manhattan | 45,194 | 17.75 | 472.44 | 99.83 % | 84.77 % | 0.00 % | 0.00 % |
| Bronx | 104,278 | 8.43 | 137.16 | 99.82 % | 76.68 % | 0.00 % | 0.00 % |
| Brooklyn | 330,154 | 8.37 | 315.47 | 99.93 % | 77.88 % | 0.00 % | 0.00 % |
| Queens | 460,939 | 7.42 | 242.01 | 99.97 % | 66.42 % | 0.00 % | 0.00 % |
| Staten Island | 142,461 | 7.89 | 64.61 | 99.94 % | 79.63 % | 0.00 % | 0.00 % |

### 1.2 Attribute provenance across the whole city

| Bit | Flag | Meaning | Buildings | Share |
|---|---|---|---|---|
| 0 | `FOOTPRINT_REAL` | footprint from the NYC OTI photogrammetric dataset | 1,083,026 | 100.00 % |
| 1 | `HEIGHT_REAL` | roof height from the LiDAR-derived `height_roof` field | 1,082,290 | 99.93 % |
| 2 | `ROOF_REAL` | roof geometry from the CityGML LOD2 model | 0 | 0.00 % |
| 3 | `FLOORS_REAL` | floor count from PLUTO | 794,995 | 73.40 % |
| 4 | `YEAR_REAL` | year built from PLUTO / footprint dataset | 1,075,197 | 99.28 % |
| 5 | `MATERIAL_REAL` | facade material from an OSM tag or an LPC designation report | 0 | 0.00 % |
| 6 | `SIGNAGE_REAL` | at least one real business name attached to the ground floor | 30,381 | 2.81 % |
| 7 | `LANDMARK_MODEL` | replaced by a hand-scripted landmark model | 0 | 0.00 % |
| 8 | `SCAFFOLD_REAL` | sidewalk shed from an active DOB permit | 6,396 | 0.59 % |
| 9 | `GROUND_REAL` | ground elevation from the LiDAR-derived field | 1,082,833 | 99.98 % |
| 10 | `FACADE_INFERRED` | facade appearance inferred by the rule set (ADR-004) | 0 | 0.00 % |
| 11 | `HEIGHT_INFERRED` | height derived from floor count or neighbours | 736 | 0.07 % |
| 12 | `FLOORS_INFERRED` | floor count derived from height | 288,031 | 26.60 % |

Buildings whose footprint **and** height are both from measurement: 99.93 %.

Per-tile files with the complete §5 schema: 0 of 25 sampled (920 tiles hold buildings).
First schema gap seen: ["missing column 'roof_type'", "missing column 'roof_mesh_ref'", "missing column 'facade_class'", "missing column 'material_primary'", "missing column 'material_secondary'", "missing column 'window_type'"]

### 1.3 Roof geometry (CityGML LOD2)

Delivery areas parsed: **3 of 20**; buildings with parsed LOD2 geometry: **16,665**.

Roof-type distribution: flat 16,665.

## 2. Road network

`roads/segments.parquet` not produced — no road figures available.

## 3. Terrain, water and coastline

- Tiles with a written heightmap: **0**
- USGS 3DEP products ingested: 30 (13, 19, 1m), 4.50 GB

Water layers not produced.

## 4. Street environment, transit and traffic model

- Tiles with props: 0 · total props placed: not produced
- Bus routes not produced · bus stops not produced · subway entrances not produced · rail structures not produced · ferry routes not produced
- Traffic density cells: not produced

## 5. Authored assets (Blender)

| Group | glTF files | Size |
|---|---|---|
| kit | 1 | 0.7 MB |
| props | 1 | 5.5 MB |
| vehicles | 0 | 0.0 MB |
| character | 0 | 0.0 MB |
| landmarks | 0 | 0.0 MB |
| tiles | 0 | 0.0 MB |

Catalog entries describing those assets: 1.

## 6. Simulation code and runtime data

- `core/`: 29 headers, 33 sources, 14 test files; registered ctest cases: 8
- Runtime binaries (`*.nycb`): not produced

## 7. Data sources and licences

144 downloaded sources, 14.8 GB, with SHA-256 recorded in `data/manifest/downloads.json`. Full table: `docs/DATA_SOURCES.md`.

| Licence | Sources |
|---|---|
| NYC Open Data Terms of Use (public domain-equivalent; attribution requested) | 66 |
| USGS public domain | 34 |
| CMU Graphics Lab Motion Capture Database: "free for all uses"; "may be copied, modified, or redistributed without permission"; created with funding from NSF EIA-0196217 | 14 |
| CC0-1.0 | 13 |
| MTA Developer Data Terms | 9 |
| NYC TLC Trip Record Data — public data released by the NYC Taxi & Limousine Commission (no licence restrictions stated; attribution requested) | 3 |
| Citi Bike Data License Agreement | 1 |
| CC0-1.0 (MakeHuman community functional pack; pack json carries per-target licence) | 1 |
| GPL-3.0-or-later (add-on code); bundled base mesh/targets CC0 | 1 |
| ODbL 1.0 | 1 |
| Public domain (US Government work: FEMA / ORNL USA Structures) | 1 |

Authored asset licences (textures, fonts, mocap, audio): `docs/ASSET_LICENSES.md`.

## 8. Verification status

Reference photographs collected for side-by-side comparison: 0 photos across 0 subjects, each with author and licence metadata.

Stage reports present: none.

Stage reports still missing: buildings, buildings_mesh, citygml, core, facade, furniture, kit, landmarks, live, props, reference, roads, terrain, traffic, traffic_density, unreal_world, unreal_gameplay, vehicles, character.

What is verified in this environment versus on a workstation is defined in `docs/ARCHITECTURE.md` §14. In short: geodesy, tiling, streaming logic, routing, traffic rules, signal phasing, astronomy, time zone handling, weather parsing, data coverage and asset geometry are verified here by tests and Cycles renders. Unreal Engine compilation, cooking, frame rate, vehicle feel and audio are not — no Unreal editor or GPU exists in this environment, and no claim is made that they were tested.

## 9. Known gaps against the brief

| # | Gap | Why | What would close it |
|---|---|---|---|
| 1 | Facade appearance is inferred from real attributes, not matched to photographs of each building | No lawful, feasible per-building street-level imagery source for 1.08 M buildings in this environment (ADR-004) | Licensed street-level imagery plus a vision model to classify material, window pattern and storefront per facade |
| 2 | Unreal side is authored but never compiled or run | No Unreal editor, no GPU, no Epic download in this environment (ADR-001) | One workstation pass following `unreal/README.md` |
| 3 | Terrain is LiDAR-derived at 2 m rather than the 1 ft city DEM | The 1 ft DEM is a 26.6 GB download against a ~30 GB disk allowance (ADR-005) | Re-run the same terrain stage against `NYC_DEM_1ft_Float`, no code change |
| 4 | Vehicle and character models are built from published dimensions, not manufacturer CAD or scans | No lawful source for either (ADR-009, ADR-010) | Licensed CAD, or photogrammetry |

Anything else that fell short is stated in the stage reports under `docs/verification/`, and each of those reports is written by the agent that did the work and reviewed by the orchestrator.

