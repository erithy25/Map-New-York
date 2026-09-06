# Definition of done

Section 12 of the project brief lists seven conditions. This file maps each one to the concrete
artefact or test that proves it, so "done" is checkable rather than claimed. The orchestrator
updates the Status column only from a verified artefact, never from an agent's assertion.

| # | Brief condition | Proof | Status |
|---|---|---|---|
| 1 | Launch, spawn, drive from any real address to any other on real roads without interruption | `data/processed/runtime/roadgraph.nycb` loaded by `core/routing`; `tests/test_world_integration.py::test_road_network_is_connected_enough_to_drive_across_the_city`; `core` routing tests for the Bronx → Staten Island route; `unreal/README.md` workstation run | pending |
| 2 | Every building present at its real location, and the count is known | `docs/FIDELITY_REPORT.md` §1 (read from `buildings_base.parquet`); `tests/test_world_integration.py::test_every_building_sits_inside_the_tile_it_is_assigned_to` | count verified: 1,083,026; meshes pending |
| 3 | Screenshots from the seven standard viewpoints compared with real photographs | `docs/verification/reference/` (licensed photographs) beside Cycles renders in `docs/verification/{buildings_mesh,kit,landmarks}/`; comparison sheets in `docs/verification/comparison/` | pending |
| 4 | Traffic behaves as specified across the whole city | `core` traffic tests (red-light compliance, no collisions, saturation throughput, no right on red) and the 20 Hz benchmark; `data/processed/traffic/density.parquet` coverage test | pending |
| 5 | Time and weather match real New York now, verifiably | `services/nycsim_live` live run recorded in `docs/verification/live/REPORT.md`; `core/tests/{time,astro,weather}`; Manhattanhenge date check | pending |
| 6 | Every subsystem in brief §3–§11 implemented, tested, working | one `REPORT.md` per stage under `docs/verification/`, each with its own test output; `docs/FIDELITY_REPORT.md` §8 lists which are present | pending |
| 7 | No placeholder, stub, TODO or mock anywhere; every bug found has a verified fix | `tests/test_world_integration.py::test_no_placeholder_markers_in_shipped_source` (repository-wide gate) | failing — 17 core scaffolding files still empty, reported to the owning agent |

## What "verified" means in this build

`docs/ARCHITECTURE.md` §14 draws the line. Everything that can be executed here is executed here:
data coverage, geodesy, tiling and streaming logic, routing, traffic rules, signal phasing,
astronomy, time-zone handling, weather parsing, asset geometry, and Cycles renders compared against
licensed photographs. Unreal Engine compilation, cooking, frame rate, vehicle feel and audio cannot
be executed here — there is no Unreal editor and no GPU in this environment — and no claim is made
that they were. They are authored as complete source with a per-file review record in
`unreal/COMPILE_CHECKLIST.md` and `unreal/COMPILE_CHECKLIST_GAMEPLAY.md`, and the workstation steps
are in `unreal/README.md`.

A condition is marked done only when its proof artefact exists **and** the orchestrator has opened
it. An agent reporting success is not proof.
