# Definition of done

Section 12 of the project brief lists seven conditions. This file maps each one to the concrete
artefact or test that proves it, so "done" is checkable rather than claimed. The orchestrator
updates the Status column only from a verified artefact, never from an agent's assertion.

| # | Brief condition | Proof | Status |
|---|---|---|---|
| 1 | Launch, spawn, drive from any real address to any other on real roads without interruption | `runtime/roadgraph.nycb` (104 MB, 122,235 segments); `test_road_network_is_connected_enough_to_drive_across_the_city` (undirected, and see C8 for why that is the weaker claim) plus `test_the_drivable_lane_graph_is_strongly_connected_not_merely_connected` (**93.71 % of drivable lanes mutually reachable; 6.29 % are not**); A* route Fordham Rd to Hylan Blvd 49.38 km across 24 Verrazzano segments; `runtime/pois.nycb` (1,082,160 addresses) and the §15 completeness test in `pipeline/tests/test_roads.py`; `unreal/README.md` workstation run | **data, addressing and routing verified**; the drive itself needs the Unreal pass. **The addressing half was missing until today and nothing said so**: `pois.nycb` had no producer, so the GPS index could offer a street name and a bus stop but not a house number — "any real address" was not reachable. It ships now, and the check is through the consumer rather than the writer: `RoadNetwork::load()` on the real directory returns 1,082,160 addresses, 13,364 bus stops, 65 landmarks and 1,106,225 index entries with no absence notes, and an address search and a landmark search resolve to the same point for the same building |
| 2 | Every building present at its real location, and the count is known | `docs/FIDELITY_REPORT.md` §1; `docs/verification/buildings/REPORT.md`; `test_every_building_sits_inside_the_tile_it_is_assigned_to`; `test_fidelity_report_counts_every_bit_from_the_stage_that_sets_it` | **done, with the inference stated** — 1,083,026 buildings, 100 % real footprints, 99.93 % measured height (six tallest match published roof heights to 4 cm or better), 95.42 % measured roof massing. What is *not* measured is now reported rather than implied: 26.60 % of floor counts derived from height, 96.69 % of facades inferred, 52.43 % of roofs inferred |
| 3 | Screenshots from the seven standard viewpoints compared with real photographs | 519 licensed photographs across 172 subjects; 57 comparison sheets with written assessments; `docs/FIDELITY_REPORT.md` §8.2 quotes all nine mandated verdicts verbatim; `test_the_mandated_viewpoints_and_drive_areas_all_have_a_usable_comparison`, `test_verification_renders_can_actually_serve_as_evidence`, `test_no_comparison_camera_is_placed_underground`, `test_no_comparison_sheet_is_older_than_the_content_it_shows` | **coverage done, and the comparison says the world does not yet look like the photographs.** All 57 scenes have a render, a sheet and an assessment, covering the 9 mandated renders and all 10 drive scenes. Of the nine mandated, **one reads as a success** (Top of the Rock: "now a real comparison and a good one"), **two cannot be judged** because their reference photograph faces a different way than the viewpoint it was collected for (I12), and the remaining six are candid that the geometry is in the right place and the surfaces, population and light are not — "Times Square is absent", "a pale grey massing model floating on a mirror", "everything the photograph is actually of is missing". That is the honest state, and B12–B16 and I13 name and size every cause |
| 4 | Traffic behaves as specified across the whole city | `core` traffic and pedestrian suites (11 of 11 green) **plus the compliance invariant measured on the real city graph — 0 law-abiding red-light entries of 8 total over 5,000 vehicles (F7); until today the city-scale number counted the modelled runners too and could not fail**; `docs/verification/performance/REPORT.md`; ADR-021 addendum in `docs/DECISIONS.md` | **behaviour met; performance transformed but still short of 8 ms.** ADR-021 is implemented and measured: the city-scale step went **665.3 ms → 38.3 ms** on the same machine, same seed and same command, with path finding falling from 96 % of the step to 9.6 % and a vehicle route query from 49.8 ms to 0.46 ms. The ring can now be populated — a prefill went from 604,604 ms to 512 ms and fills 1,021 vehicles against the density table's own target of 1,066 for that ring, where it managed 19 before. Every behaviour invariant was re-confirmed rather than assumed: saturation flow 1,708.61 veh/h/lane, zero red-light entries by a law-abiding driver, zero right-on-red, zero pedestrian wall crossings, zero spawns inside the protected region. **8 ms is not reached and 38.3 ms is what it reaches**; F1 lists what stands between them. The first item on that list has since been taken and was worth less than F1 claimed: the signal cache now follows the streamed region from inside `step()` rather than waiting for a host to ask, measured at 433 of 19,814 plans refreshed a step and a combined step of **37.32 → 35.59 ms** on the city benchmark — **1.73 ms, not the 2.7 that was published** — with both trajectory hashes bit-identical across the A/B, so the saving is provably free of any behaviour change |
| 5 | Time and weather match real New York now, verifiably | `docs/verification/live/REPORT.md` live run; `core/tests/{time,astro,weather}`; Manhattanhenge dates | **done** — live observation published, 344 service tests and 9 core suites green, time zone checked against every day 2007 to 2099 |
| 6 | Every subsystem in brief §3–§11 implemented, tested, working | one `REPORT*.md` per stage under `docs/verification/` — **which proves reports exist, not that subsystems are tested**, so the test counts are the evidence for the middle word: **4,561 Python tests** (3,835 cross-cutting in `tests/`, 382 pipeline, 344 services) and **149 C++ cases** carrying 249,249 assertions in `core` | **all 21 stage lanes have delivered a report** (22 top-level reports; the landmarks lane split into REPORT_B and REPORT_C, plus 34 per-landmark and 24 per-comparison-scene reports). Audio is covered inside `unreal_gameplay`; its 65 radio tracks were checked here — all 65 present on disk, all 74 payload files licensed, sha256 verified |
| 7 | No placeholder, stub, TODO or mock anywhere; every bug found has a verified fix | `test_no_placeholder_markers_in_shipped_source`; and, for the second half, the fix and its verification named per bug in `docs/DEVIATIONS.md` and the stage reports | **first half passing** — the marker gate is green across pipeline, core, blender, services and the Unreal sources. **The second half is not something that gate tests, and saying so is the point**: it checks for the *word* TODO, not for whether a bug was fixed. What stands behind it is the per-bug record. Today's, as the pattern: the daylight light cones rendered opaque — ray-cast to `LIGHT_CONE`, fixed by deleting the faces, verified by re-rendering the frame that exposed it and by `cone_faces_deleted` in every `render.json`; the pedestrian clearance let a body at 1 m fill 261 % of frame height — re-derived from the frame, verified by `test_the_pedestrian_clearance_is_derived_from_the_frame_not_picked`, which also forbids it loosening; the OSM park trees were placed at a sapling default below the 10th percentile of the real population — replaced by a seeded draw, verified reproducible from scratch at `sha256 5df79f612578fc44`; the signal cache refreshed all 19,814 plans every step — fixed in `step()` so no host can forget, verified by bit-identical trajectory hashes across the A/B. Five bugs of a different kind — data written and never read — are recorded rather than fixed, and `test_no_processed_table_is_written_and_never_read` now forces the next one to be recorded before it can be tolerated. |

## The suite, as of this writing

`PYTHONPATH=pipeline python3 -m pytest tests/ pipeline/tests/` stands at **4,135 passed, 1 skipped, 1
failed** in 11 m 32 s — the suite has grown by 357 tests as the closing lanes added their own — and
`ctest` in `core/build` is **11 of 11 suites green** — the whole repository green
at once, which it had not been before. Every gate that was red got there by catching something real, and
each was closed by fixing the thing rather than the gate.

**One test is red as this is written, and it should be.**
`test_no_comparison_sheet_is_older_than_the_content_it_shows` flags 29 of the 57 comparison sheets,
because a rebuild of the tile shells — stepped roof massing and a real material set — is in progress and
those frames now show geometry that has been replaced. The sheets are genuinely stale; the test is
reporting the truth, and it clears when the rebuild finishes and the affected scenes are re-rendered.
A green suite that hid this would be worth less than a red one that names it.

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
