# Build state (verified by the orchestrator, 2026-09-06)

Wave 1 of the sub-agents was cut off mid-run by a session rate limit. This file records what is **verified on disk**, so that resumed agents continue instead of redoing. Verified means: the orchestrator opened the artefact and read its row counts / summaries.

## Done and verified

| Artefact | State |
|---|---|
| `data/raw/**` (144 sources, 14.8 GB) | downloaded, manifest with SHA-256 in `data/manifest/downloads.json` |
| `data/processed/buildings/footprints_raw.parquet` | 1,083,026 rows, NYC_TM, ground_z/height in metres |
| `data/processed/buildings/buildings_base.parquet` | 1,083,026 rows × 50 cols; PLUTO join 99.96 %, height real 99.8 %, ground real 99.97 %; scaffolds from 8,479 active DOB permits; 3,689 footprints with LPC landmark id; 31,442 in historic districts |
| `data/processed/tiles/{tile}/buildings.parquet` | 920 tiles written |
| `data/processed/buildings/borough_summary.json`, `build_summary.json` | per-borough counts and join rates |
| `data/processed/buildings/landmark_footprints.parquet` | 65 landmark footprints resolved |
| `data/processed/buildings/citygml/da4.parquet` | 16,665 buildings, LOD2 triangles; throughput 455 buildings/s, 6 MB/s, peak RSS 189 MB; NAD83→WGS84 Helmert applied |
| `data/processed/osm/*.parquet` | buildings 1,247,724 · NJ buildings 302,989 · POIs 117,930 · signals/stops 213,897 · restrictions 12,445 · rail 14,306 · landuse 116,616 · street furniture 80,145 |
| `data/processed/nj/buildings_nj_usa_structures.parquet` | 231,336 NJ structures (USA Structures) |
| `data/processed/terrain/src2m/` | **gone** — the 2 m working mosaic (1.76 GB) was deleted for disk after the 2,916 tiles were published (`src2m_removed.json`; regenerable with `terrain --ingest`, ~525 MB per 1 m product through the proxy). Until it is re-ingested, `terrain --only tiles` cannot run; the published tiles are the product, and a terrain edit goes through a published-tile mode (`terrain.platforms apply-to-published`, ADR-022) |
| `data/processed/terrain/platform_decks.parquet` | 2 platform decks (Hudson Yards ERY platform + Tenth Avenue, Eleventh Avenue bridge over the yard) burned into `t_-5_5` / `t_-5_6` on 2026-09-09 (J85). Order after a terrain edit: `terrain --only index` → `--only verify` → `blender/landmarks/export_ground_outlines.py` (whole catalogue) → `roads.apply_terrain_z` → `runtime.export` → `build_pavement` / `build_structures` / `build_parkground` for the tiles → `unreal.manifest` (full) → the sheets |
| `data/processed/osm/extract_summary.json` | geometry_errors 0; NJ/NY state-line validation passed |
| `core/` | 30 headers + 27 sources: geo (TM, LCC, State Plane, UE coords), tiling (Tile, Catalog, Scheduler), io (Nycb, Json), routing (RoadGraph, Router), traffic (Density, Signals, VehicleClass, SpatialHash, Random, SyntheticGrid), util (Result, Arena, Span, Log, FixedStepClock); doctest vendored |
| `services/nycsim_live/` | timesync, astronomy, weather, metar, esb_lights, tides, net |
| `unreal/NYCSim/` | uproject, 3 configs, 3 modules (Core/Runtime/Editor), CoreAdapter (geo, nycb, tile scheduler), World subsystem/GameMode/GameInstance |
| `blender/` | common (nycsim_bpy, textures, facade_params, merge_catalog), kit/facade/kitlib, props/_core+_palette, vehicles/vlib, landmarks/common+b_common+c_common+bridge_lib+empire_state |
| `assets/textures/` | 937 MB CC0 PBR sets from AmbientCG with per-asset LICENSE.json (git-ignored, re-fetchable) |
| `assets/character/cmu_mocap/` | CMU mocap ASF/AMC clips (free for all uses), tracked |
| `assets/fonts/Overpass` | SIL OFL font for signage |

## Not done yet (wave 2 targets)

* CityGML: 19 of 20 delivery areas unparsed (`run_citygml_full.sh` not started).
* Roads: modules written, **no** `segments/nodes/lanes/junctions/signals/signs` parquet produced yet.
* Terrain: source grid ingested, **no** per-tile `terrain.png` / `terrain.json` written; water not built.
* `core/`: never compiled here; no ctest run.
* Blender: exactly one smoke `.glb` exists. No kit, props, vehicles, character or landmark assets.
* Traffic/peds C++ behaviour models: headers only, no IDM/MOBIL/social-force implementation.
* Live services: no `weather.json` written, no test run recorded.
* Unreal: only world/streaming skeleton; no sky/weather/vehicle/character/traffic/UI/audio.
* No `REPORT.md` in any `docs/verification/*` directory.
