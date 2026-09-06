# Definition of done

Section 12 of the project brief lists seven conditions. This file maps each one to the concrete
artefact or test that proves it, so "done" is checkable rather than claimed. The orchestrator
updates the Status column only from a verified artefact, never from an agent's assertion.

| # | Brief condition | Proof | Status |
|---|---|---|---|
| 1 | Launch, spawn, drive from any real address to any other on real roads without interruption | `runtime/roadgraph.nycb` (104 MB, 122,235 segments); `test_road_network_is_connected_enough_to_drive_across_the_city`; A* route Fordham Rd to Hylan Blvd 49.38 km across 24 Verrazzano segments; `unreal/README.md` workstation run | **data and routing verified**; the drive itself needs the Unreal pass |
| 2 | Every building present at its real location, and the count is known | `docs/FIDELITY_REPORT.md` §1; `test_every_building_sits_inside_the_tile_it_is_assigned_to` | **done** — 1,083,026 buildings, 99.93 % measured height, 95.42 % measured roof massing; shell meshes building city-wide |
| 3 | Screenshots from the seven standard viewpoints compared with real photographs | 265 licensed photographs in `docs/verification/reference/` with viewpoint and azimuth; comparison sheets in `docs/verification/comparison/` | **in progress** — reference set complete, sheets being rendered |
| 4 | Traffic behaves as specified across the whole city | `core` traffic and pedestrian suites (all 11 core suites pass); `data/processed/traffic/density.parquet` 18,864 calibrated cells | **behaviour met, performance not** — zero red-light and right-on-red violations by law-abiding drivers, saturation flow 1,708.6 veh/h/lane inside the Highway Capacity Manual band, zero wall crossings by pedestrians; but the step costs 35.6 ms against an 8 ms budget |
| 5 | Time and weather match real New York now, verifiably | `docs/verification/live/REPORT.md` live run; `core/tests/{time,astro,weather}`; Manhattanhenge dates | **done** — live observation published, 344 service tests and 9 core suites green, time zone checked against every day 2007 to 2099 |
| 6 | Every subsystem in brief §3–§11 implemented, tested, working | one `REPORT.md` per stage under `docs/verification/` | **13 of 19 stage reports delivered**; traffic, character, vehicles, landmarks A and B, comparison sheets outstanding |
| 7 | No placeholder, stub, TODO or mock anywhere; every bug found has a verified fix | `test_no_placeholder_markers_in_shipped_source` | **passing** — the gate is green across pipeline, core, blender, services and the Unreal sources |

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
it. An agent reporting success is not proof — three of the defects found so far were reported as
successes by the stage that produced them: 32.8 million kit placements pointing at assets that did
not exist, a 1,003 km² stretch of New Jersey highland modelled as sea, and a packed C++ struct that
made the road graph unreadable to the router.
