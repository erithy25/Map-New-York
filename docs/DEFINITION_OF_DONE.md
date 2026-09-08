# Definition of done

Section 12 of the project brief lists seven conditions. This file maps each one to the concrete
artefact or test that proves it, so "done" is checkable rather than claimed. The orchestrator
updates the Status column only from a verified artefact, never from an agent's assertion.

**All seven rows were audited on 2026-09-07 against the question "does the cited proof actually
measure the claim?", and four did not.** The failure was the same each time — a real measurement of
something adjacent to the condition, which therefore had no failing case:

| # | what the proof measured instead | outcome |
|---|---|---|
| 1 | *undirected* connectivity, for a question about driving, which is directed | **fixed** — 93.71 % of drivable lanes are strongly connected; 6.29 % are not (C8) |
| 4 | a red-light count that included the deliberately modelled runners | **fixed** — 0 law-abiding violations, measured on the real city graph (F7) |
| 6 | that one `REPORT.md` exists per stage, for a claim that subsystems are *tested* | **fixed** — 4,561 Python tests and 149 C++ cases, collected |
| 7 | a search for the word `TODO`, for "every bug found has a verified fix" | **recorded** — the per-bug record is what stands behind it, and the row now says so |

Conditions 2, 3 and 5 hold up as written: the building count is 1,083,026 rows in and out with the
per-tile tables summing to exactly that; the seven mandated viewpoints are covered 7 of 7 and their
verdicts are quoted verbatim rather than summarised; and the time and weather claim rests on tests
that do bear on it, including the time zone checked against every day from 2007 to 2099.

| # | Brief condition | Proof | Status |
|---|---|---|---|
| 1 | Launch, spawn, drive from any real address to any other on real roads without interruption | `runtime/roadgraph.nycb` (104 MB, 122,235 segments); `test_road_network_is_connected_enough_to_drive_across_the_city` (undirected, and see C8 for why that is the weaker claim) plus `test_the_drivable_lane_graph_is_strongly_connected_not_merely_connected` (**93.71 % of drivable lanes mutually reachable; 6.29 % are not**); A* route Fordham Rd to Hylan Blvd 49.38 km across 24 Verrazzano segments; `runtime/pois.nycb` (1,082,160 addresses) and the §15 completeness test in `pipeline/tests/test_roads.py`; `unreal/README.md` workstation run | **data, addressing and routing verified**; the drive itself needs the Unreal pass. **The addressing half was missing until today and nothing said so**: `pois.nycb` had no producer, so the GPS index could offer a street name and a bus stop but not a house number — "any real address" was not reachable. It ships now, and the check is through the consumer rather than the writer: `RoadNetwork::load()` on the real directory returns 1,082,160 addresses, 13,364 bus stops, 65 landmarks and 1,106,225 index entries with no absence notes, and an address search and a landmark search resolve to the same point for the same building |
| 2 | Every building present at its real location, and the count is known | `docs/FIDELITY_REPORT.md` §1; `docs/verification/buildings/REPORT.md`; `test_every_building_sits_inside_the_tile_it_is_assigned_to`; `test_fidelity_report_counts_every_bit_from_the_stage_that_sets_it` | **done, with the inference stated** — 1,083,026 buildings, 100 % real footprints, 99.93 % measured height (six tallest match published roof heights to 4 cm or better), 95.42 % measured roof massing. What is *not* measured is now reported rather than implied: 26.60 % of floor counts derived from height, 96.69 % of facades inferred, 52.43 % of roofs inferred |
| 3 | Screenshots from the seven standard viewpoints compared with real photographs | 519 licensed photographs across 172 subjects; 57 comparison sheets with written assessments; `docs/FIDELITY_REPORT.md` §8.2 quotes all nine mandated verdicts verbatim; `test_the_mandated_viewpoints_and_drive_areas_all_have_a_usable_comparison`, `test_verification_renders_can_actually_serve_as_evidence`, `test_no_comparison_camera_is_placed_underground`, `test_no_comparison_sheet_is_older_than_the_content_it_shows` | **coverage done, and the comparison says the world does not yet look like the photographs.** All 57 scenes have a render, a sheet and an assessment, covering the 9 mandated renders and all 10 drive scenes. Of the nine mandated, **one reads as a success** (Top of the Rock: "now a real comparison and a good one"), **two cannot be judged** because their reference photograph faces a different way than the viewpoint it was collected for (I12), and the remaining six are candid that the geometry is in the right place and the surfaces, population and light are not — "Times Square is absent", "a pale grey massing model floating on a mirror", "everything the photograph is actually of is missing". That is the honest state, and B12–B16 and I13 name and size every cause |
| 4 | Traffic behaves as specified across the whole city | `core` traffic and pedestrian suites (11 of 11 green) **plus the compliance invariant measured on the real city graph — 0 law-abiding red-light entries of 8 total over 5,000 vehicles (F7); until today the city-scale number counted the modelled runners too and could not fail**; `docs/verification/performance/REPORT.md`; ADR-021 addendum in `docs/DECISIONS.md` | **behaviour met; performance transformed but still short of 8 ms.** ADR-021 is implemented and measured: the city-scale step went **665.3 ms → 38.3 ms** on the same machine, same seed and same command, with path finding falling from 96 % of the step to 9.6 % and a vehicle route query from 49.8 ms to 0.46 ms. The ring can now be populated — a prefill went from 604,604 ms to 512 ms and fills 1,021 vehicles against the density table's own target of 1,066 for that ring, where it managed 19 before. Every behaviour invariant was re-confirmed rather than assumed: saturation flow 1,708.61 veh/h/lane, zero red-light entries by a law-abiding driver, zero right-on-red, zero pedestrian wall crossings, zero spawns inside the protected region. **8 ms is not reached and 38.3 ms is what it reaches**; F1 lists what stands between them. The first item on that list has since been taken and was worth less than F1 claimed: the signal cache now follows the streamed region from inside `step()` rather than waiting for a host to ask, measured at 433 of 19,814 plans refreshed a step and a combined step of **37.32 → 35.59 ms** on the city benchmark — **1.73 ms, not the 2.7 that was published** — with both trajectory hashes bit-identical across the A/B, so the saving is provably free of any behaviour change |
| 5 | Time and weather match real New York now, verifiably | `docs/verification/live/REPORT.md` live run; `core/tests/{time,astro,weather}`; Manhattanhenge dates | **done** — live observation published, 344 service tests and 9 core suites green, time zone checked against every day 2007 to 2099 |
| 6 | Every subsystem in brief §3–§11 implemented, tested, working | one `REPORT*.md` per stage under `docs/verification/` — **which proves reports exist, not that subsystems are tested**, so the test counts are the evidence for the middle word: **4,561 Python tests** (3,835 cross-cutting in `tests/`, 382 pipeline, 344 services) and **149 C++ cases** carrying 249,249 assertions in `core` | **all 21 stage lanes have delivered a report** (22 top-level reports; the landmarks lane split into REPORT_B and REPORT_C, plus 34 per-landmark and 24 per-comparison-scene reports). Audio is covered inside `unreal_gameplay`; its 65 radio tracks were checked here — all 65 present on disk, all 74 payload files licensed, sha256 verified |
| 7 | No placeholder, stub, TODO or mock anywhere; every bug found has a verified fix | `test_no_placeholder_markers_in_shipped_source`; and, for the second half, the fix and its verification named per bug in `docs/DEVIATIONS.md` and the stage reports | **first half passing** — the marker gate is green across pipeline, core, blender, services and the Unreal sources. **The second half is not something that gate tests, and saying so is the point**: it checks for the *word* TODO, not for whether a bug was fixed. What stands behind it is the per-bug record. Today's, as the pattern: the daylight light cones rendered opaque — ray-cast to `LIGHT_CONE`, fixed by deleting the faces, verified by re-rendering the frame that exposed it and by `cone_faces_deleted` in every `render.json`; the pedestrian clearance let a body at 1 m fill 261 % of frame height — re-derived from the frame, verified by `test_the_pedestrian_clearance_is_derived_from_the_frame_not_picked`, which also forbids it loosening; the OSM park trees were placed at a sapling default below the 10th percentile of the real population — replaced by a seeded draw, verified reproducible from scratch at `sha256 5df79f612578fc44`; the signal cache refreshed all 19,814 plans every step — fixed in `step()` so no host can forget, verified by bit-identical trajectory hashes across the A/B. Five bugs of a different kind — data written and never read — are recorded rather than fixed, and `test_no_processed_table_is_written_and_never_read` now forces the next one to be recorded before it can be tolerated. |

## What changed after the first delivery

This document was written when the world was a set of tables and a `unreal/` tree nobody had
compiled. Two things have happened since, and both belong here because they change what "done"
means.

**The first drivable region is delivered.** 48 parts, 2.15 GB packed and 4.09 GB unpacked, 1,041
files across 47 tiles of Manhattan, on the branch `dist/first-drive` with an `index.json` naming
every file and its SHA-256. `unreal/README.md` §9b has the five commands that put it on a
workstation. Until it is compiled and driven there, the brief's first condition remains unproven —
that has not changed — but the content half of it is no longer a thing the reader has to build.

**A defect shape was found twelve times and closed eleven.** A stage gathers real data, writes it,
and nothing ever consumes it. Nothing fails, no test goes red, and the gap is invisible until
somebody opens a render or follows a reference. The largest of them was **5,713,269 facade kit
instances and 129,828 props in the first-drive region alone resolving to no asset at all** — every
window, cornice, storefront, fire escape, water tower and street tree, with the import reporting no
error because there was no error to report. The others are in `docs/DEVIATIONS.md` §J: 986 km of
rail structure with one consumer, 1,285 surveyed stations in the survey and in nothing else, 81,684
rooftop cooling towers standing at street level inside the buildings they sit on, 1,033,416
buildings pointing at a `roofs.glb` nobody wrote, 13,851 surveyed curb ramps that the pavement had
no kind for, and every vehicle in the city with untextured tyres and seats.

**What that says about the standard below.** "A condition is marked done only when its proof
artefact exists and the orchestrator has opened it" was the right rule and it was not enough: each
of these had a proof artefact that existed and was correct. The kit *was* exported. The rail
structures *were* measured. The tests that passed were testing the producer. What none of them
tested was whether anything downstream could resolve what the producer wrote — so the rule now has a
second half, and the tests that enforce it are named in each entry: **a producer is not done until
something consumes its output and a test fails when the join breaks.**

## The suite, as of this writing

`PYTHONPATH=pipeline python3 -m pytest tests/ pipeline/tests/` was measured on 2026-09-08 at
**4,386 passed, 1 skipped, 2 failed** in 12 m 43 s, and `ctest` in `core/build` re-run the same day
is **11 of 11 suites green** in 76.6 s. The suite has grown as the vehicle rig, the structures, the
park ground, the curb ramps, the road markings, the cold-weather cast and the prop audits added
their own; a handful more have been added since that run and the figure is due to be re-measured
when the comparison pass finishes.

**Both failures in that run were reporting something real, and neither was a false alarm.**
`test_the_pedestrian_bodies_cover_every_archetype_the_simulation_draws` asserted `len(present) == 24`
with the 24 written into the test, and the cast had grown to 36 — the same fault
`PedSim::kArchetypeCount` had, and the reason J53 says a count that must be hand-edited to follow the
cast is a count that will not. It now reads `kPedWardrobeArchetypes` out of the generated header, so
the test follows the cast by construction. `test_no_comparison_sheet_is_older_than_the_content_it_shows`
is **deliberately red** and stays red until the 172-sheet pass finishes: the sheets on disk predate
the markings, the lamps and the cold cast, and the test exists to say so.

**Two tests were red on the way here and both were reporting something real.**

`test_nycb_layout_json_documents_the_cpp_structs` failed on a missing `places` key. The GPS learned
to search 85,023 named places and the section that carries them was added to the export, but the
layout document that tells `core/io/NycbReader.h` where every field sits had not been regenerated,
so the C++ side was being checked against a description of the file that predated a section of it.

`test_placed_agents_stand_on_the_pavement_and_the_counts_add_up` failed with a taxi 1.15 m off its
pavement against a 0.5 m tolerance, and the cause was not the taxi. Blender's glTF importer builds a
mesh object called `Icosphere` for any rigged file and hands it to every bone as a display shape;
`import_glb` returned it with the car, and every rigged vehicle in every verification render had
been carrying an untextured 2 m sphere at its rear axle. Nothing had failed over it for as long as
the fleet had been rigged, because the sphere has no material and renders as grey rather than as an
error. It is J44, and the test that caught it is the one that measures where geometry *ends up*
rather than where the placement code says it was put.

## What "verified" means in this build

`docs/ARCHITECTURE.md` §14 draws the line. Everything that can be executed here is executed here:
data coverage, geodesy, tiling and streaming logic, routing, traffic rules, signal phasing,
astronomy, time-zone handling, weather parsing, asset geometry, and Cycles renders compared against
licensed photographs. Unreal Engine compilation, cooking, frame rate, vehicle feel and audio cannot
be executed here — there is no Unreal editor and no GPU in this environment — and no claim is made
that they were.

**That was said of the whole plugin, and it is only true of part of it.** Measured on 2026-09-08:
of the **101 translation units** in `unreal/NYCSim/Source`, **41 are plain C++ that the system
compiler builds with `-Wall -Wextra` and no Unreal present** — the `nycsim_gameplay` adapter layer
and the generated `CoreUnity` stubs that wrap `core/src`. All 41 compile clean; **0 fail**.
`unreal/tools/syntax_check.py` runs them, `test_the_plugin_source_that_can_be_compiled_here_is_compiled_here`
holds the floor at 41, and a review record is weaker evidence than a compiler wherever the compiler
can run. It is what turned J53's 64-bit archetype mask from an argument into a compile.

The remaining **60 reach `CoreMinimal.h`** — directly or through their own headers, which is how a
first version of that checker called 58 files broken when most were simply not ours to build — and
those are what is authored as complete source with a per-file review record in
`unreal/COMPILE_CHECKLIST.md` and `unreal/COMPILE_CHECKLIST_GAMEPLAY.md`. The workstation steps are
in `unreal/README.md`.

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
