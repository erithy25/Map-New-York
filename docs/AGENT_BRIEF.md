# Brief for every NYCSim sub-agent

You are one specialist on a team building a 1:1, photoreal, drivable New York City (Blender assets → Unreal Engine 5.4). The orchestrator integrates your work; other agents run concurrently in the same repository.

## Read first (in this order)
1. `docs/ARCHITECTURE.md` — plan, environment constraints (§0), coordinate systems (§2), tiling (§3).
2. `docs/DATA_CONTRACTS.md` — every schema you produce or consume. Follow it exactly; if you must extend it, append a clearly marked section and say so in your report.
3. `docs/DECISIONS.md` — ADRs. Do not silently contradict one; propose a new ADR in your report instead.
4. Foundation code you must use, not duplicate: `pipeline/nycsim_pipeline/{crs,tiling,manifest,paths,sources,download}.py`, `blender/common/nycsim_bpy.py`.

## Non-negotiable rules
* **No placeholders.** No TODO/FIXME/stub/mock/"would be extended". Every function is complete, with error handling and edge cases. If a fidelity target cannot be reached, implement the best achievable version *and state the exact gap* in your report — never present approximations as real.
* **Real data only.** Real footprints, real attributes, real dimensions (published), real names. Anything inferred is flagged in data (`fidelity` bits / `source` columns) and in your report.
* **Stay in your lane.** Write only in the directories assigned to you (plus `docs/verification/<your-stage>/`). Never edit another agent's files or the foundation files (report needed changes instead).
* **Verify before reporting.** Run your code. Run your tests. Open your outputs (row counts, bounds, sample rows, rendered PNG). Your report must contain the evidence (numbers, file paths, test output summaries).
* **Resource etiquette** (4 vCPU, 15 GB RAM, ~25 GB free disk shared by all agents): one heavy process at a time, `nice -n 10` for jobs > 1 min, never load `data/raw/nyc_opendata/building_footprints.geojson` (use `data/processed/buildings/footprints_raw.parquet`, read only the columns you need), stream large files (CityGML zip: `unzip -p` + iterparse), delete scratch. Develop on a subset (one tile/borough), then run the full pass only if it fits in ~40 CPU-minutes, else provide a `run_full.sh` and say so.
* **Reproducibility.** Every download goes through `nycsim_pipeline.download`/`manifest.record_download` (or, for assets, a JSON licence record next to the file: url, licence, author, sha256). Every processed artefact is recorded via `manifest.record_processed`.
* **Python**: 3.11, type hints, `from __future__ import annotations`, logging not print (CLI entry points may print summaries), pytest tests under `pipeline/tests/` or `tests/`. **C++**: C++17, no exceptions across module boundaries, no UB, `-Wall -Wextra -Werror` clean, tests with doctest (`https://cdn.jsdelivr.net/gh/doctest/doctest@2.4.11/doctest/doctest.h`). **Blender**: `bpy` 4.5.13 headless via `python3` (already installed), Cycles CPU for renders, export via `nycsim_bpy.export_glb`.
* **Network**: HTTPS goes through a proxy with a custom CA; `requests` and `curl` already work. Blocked: github.com downloads, Geofabrik, overpass-api.de (use `https://overpass.kumi.systems/api/interpreter` or `https://overpass.private.coffee/api/interpreter`). `https://cdn.jsdelivr.net/gh/<owner>/<repo>@<tag>/<path>` serves GitHub files. Do not try to route around a 403/407.
* **Do not commit or push.** The orchestrator commits. Do not run `git add/commit/checkout/reset`.
* **Report** at `docs/verification/<stage>/REPORT.md`: What was built (files), how verified (commands + numeric results), fidelity achieved vs. target, gaps with reasons, what the next agent needs to know, licences of anything downloaded. Your final message to the orchestrator is a concise version of that report (facts, numbers, paths). Do not ask the orchestrator questions; make and document decisions.
