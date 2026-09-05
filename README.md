# NYCSim — 1:1 drivable New York City

Free-roam driving simulation of the five boroughs at 1:1 scale. Every building footprint, height and (for buildings existing in 2014) real LiDAR roof/massing geometry comes from NYC Open Data; roads with real lanes, one-ways, speeds and signs from NYC DOT/DCP; terrain from USGS 3DEP LiDAR; time and weather live from NWS. Assets are authored in Blender 4.5 (headless `bpy`), assembled in Unreal Engine 5.4.

Read in this order:
1. `docs/ARCHITECTURE.md` — the plan and the environment constraints (what was verified where).
2. `docs/DATA_CONTRACTS.md` — schemas between pipeline, Blender, core and Unreal.
3. `docs/DECISIONS.md` — every trade-off, as ADRs.
4. `docs/FIDELITY_REPORT.md` — honest, quantitative account of what is real, what is inferred, and what is missing.

## Layout
`pipeline/` Python data pipeline · `blender/` bpy asset generators · `core/` engine-agnostic C++17 simulation library with tests · `unreal/NYCSim/` UE 5.4 project · `services/` live-data reference implementation · `tests/` integration tests · `docs/verification/` renders and comparison sheets.

## Quick start (data + assets, Linux, no GPU needed)
```bash
python3 -m pip install -e ".[test]" bpy==4.5.13
PYTHONPATH=pipeline python3 -m nycsim_pipeline download --all
PYTHONPATH=pipeline python3 -m nycsim_pipeline terrain && python3 -m nycsim_pipeline roads && python3 -m nycsim_pipeline citygml && python3 -m nycsim_pipeline buildings && python3 -m nycsim_pipeline furniture && python3 -m nycsim_pipeline transit && python3 -m nycsim_pipeline traffic && python3 -m nycsim_pipeline tiles
python3 blender/run_all.py            # kit, props, vehicles, character, landmarks, tiles -> blender_out/
cmake -S core -B core/build && cmake --build core/build -j && ctest --test-dir core/build
pytest
```
Unreal: see `unreal/README.md` (requires UE 5.4 on a workstation with a GPU).
