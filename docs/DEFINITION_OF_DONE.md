# Definition of done

Section 12 of the project brief lists seven conditions. This file maps each one to the concrete
artefact or test that proves it, so "done" is checkable rather than claimed. The orchestrator
updates the Status column only from a verified artefact, never from an agent's assertion.

| # | Brief condition | Proof | Status |
|---|---|---|---|
| 1 | Launch, spawn, drive from any real address to any other on real roads without interruption | `runtime/roadgraph.nycb` (104 MB, 122,235 segments); `test_road_network_is_connected_enough_to_drive_across_the_city`; A* route Fordham Rd to Hylan Blvd 49.38 km across 24 Verrazzano segments; `unreal/README.md` workstation run | **data and routing verified**; the drive itself needs the Unreal pass |
| 2 | Every building present at its real location, and the count is known | `docs/FIDELITY_REPORT.md` §1; `docs/verification/buildings/REPORT.md`; `test_every_building_sits_inside_the_tile_it_is_assigned_to`; `test_fidelity_report_counts_every_bit_from_the_stage_that_sets_it` | **done, with the inference stated** — 1,083,026 buildings, 100 % real footprints, 99.93 % measured height (six tallest match published roof heights to 4 cm or better), 95.42 % measured roof massing. What is *not* measured is now reported rather than implied: 26.60 % of floor counts derived from height, 96.69 % of facades inferred, 52.43 % of roofs inferred |
| 3 | Screenshots from the seven standard viewpoints compared with real photographs | 519 licensed photographs across 172 subjects; 57 comparison sheets with written assessments; `docs/FIDELITY_REPORT.md` §8.2 quotes all nine mandated verdicts verbatim; `test_the_mandated_viewpoints_and_drive_areas_all_have_a_usable_comparison`, `test_verification_renders_can_actually_serve_as_evidence`, `test_no_comparison_camera_is_placed_underground`, `test_no_comparison_sheet_is_older_than_the_content_it_shows` | **coverage done, and the comparison says the world does not yet look like the photographs.** All 57 scenes have a render, a sheet and an assessment, covering the 9 mandated renders and all 10 drive scenes. Of the nine mandated, **one reads as a success** (Top of the Rock: "now a real comparison and a good one"), **two cannot be judged** because their reference photograph faces a different way than the viewpoint it was collected for (I12), and the remaining six are candid that the geometry is in the right place and the surfaces, population and light are not — "Times Square is absent", "a pale grey massing model floating on a mirror", "everything the photograph is actually of is missing". That is the honest state, and B12–B16 and I13 name and size every cause |
| 4 | Traffic behaves as specified across the whole city | `core` traffic and pedestrian suites (11 of 11 core suites pass); `data/processed/traffic/density.parquet`; `docs/verification/performance/REPORT.md` | **behaviour met, performance not** — zero red-light and right-on-red violations by law-abiding drivers, saturation flow 1,708.6 veh/h/lane, zero pedestrian wall crossings, memory flat at 8 KB growth over 895,887 agent lifecycles; but the step costs 14.0 ms synthetic and 777 ms city-scale against an 8 ms budget, and the spawner cannot fill the player's ring on the real graph (ADR-021) |
| 5 | Time and weather match real New York now, verifiably | `docs/verification/live/REPORT.md` live run; `core/tests/{time,astro,weather}`; Manhattanhenge dates | **done** — live observation published, 344 service tests and 9 core suites green, time zone checked against every day 2007 to 2099 |
| 6 | Every subsystem in brief §3–§11 implemented, tested, working | one `REPORT*.md` per stage under `docs/verification/` | **all 21 stage lanes have delivered a report** (22 top-level reports; the landmarks lane split into REPORT_B and REPORT_C, plus 34 per-landmark and 24 per-comparison-scene reports). Audio is covered inside `unreal_gameplay`; its 65 radio tracks were checked here — all 65 present on disk, all 74 payload files licensed, sha256 verified |
| 7 | No placeholder, stub, TODO or mock anywhere; every bug found has a verified fix | `test_no_placeholder_markers_in_shipped_source` | **passing** — the gate is green across pipeline, core, blender, services and the Unreal sources |

## The suite, as of this writing

`PYTHONPATH=pipeline python3 -m pytest tests/ pipeline/tests/` — **3,778 passed, 1 skipped, 0 failed**, in
5 m 38 s. `ctest` in `core/build` — **11 of 11 suites green**. That is the whole repository green at once,
which it has not been before: the gates that were failing were failing for real reasons, and each was
closed by fixing the thing rather than the gate.

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
it. An agent reporting success is not proof — four of the defects found so far were reported as
successes by the stage that produced them: 32.8 million kit placements pointing at assets that did
not exist, a 1,003 km² stretch of New Jersey highland modelled as sea, a packed C++ struct that
made the road graph unreadable to the router, and a character whose garments all carried the
wrong vertex weights because `vertex_groups.new()` does not overwrite.

The same standard applies to this report about itself. It stated for some time that 0 % of facades
and 0 % of roofs were inferred, because the generator counted those bits in a table that does not
set them. The real figures are 96.69 % and 52.43 %. Nothing about the world was wrong; the
accounting of it was, in the one direction the brief says must never happen — claiming inferred
content is real. `test_fidelity_report_counts_every_bit_from_the_stage_that_sets_it` now checks
every reported count against a direct count in the owning artefact.
