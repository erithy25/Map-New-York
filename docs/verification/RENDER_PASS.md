# The comparison-sheet render pass: where it stands and how it is resumed

One file, kept current, because the pass runs for hours in a container that can be reclaimed and its
resume state lives outside the repository (`blender_out/render_all_state.json`, untracked because it
changes on every sheet). Losing that file would mean re-rendering everything already done.

## v16 — every sheet, once more, under the probes and the development that the v15 pass measured

The v15 pass rendered all 172 items (166 sheets, 6 refused) and the measurements over that finished
set are the reason for v16. **Every sheet is re-rendered**, for one or more of these:

| class | sheets | why |
|---|---|---|
| every daylight sheet | 170 | J83 — the development is metered on the frame; the old fixed calibration sat ~0.55× under the photographs at every quantile |
| every sheet that names a subject | 138 | J78 (the sightline finds the subject's own fabric, fraction of 13 rays, width × height fan), J79 (the walk scores on the subject), J74 (43-ray probe) |
| the six on the old 09:30 constant | 6 | J80 — `drive_bronx_arthur_ave`, `drive_bronx_grand_concourse`, `drive_brooklyn_bed_stuy_stuyvesant_ave`, `drive_brooklyn_park_slope_7th_ave`, `fifth_ave_42nd_north`, `landmark_federal_hall` |
| the night sheet with a year-only photograph | 1 | J80 amendment — `street_times_square_wet_night` had been given an 08:30 Sun |
| the interior item | 1 | declined by the runner from `meta.json`, before Blender starts; `landmark_grand_central_concourse` gets a `not_renderable_interior` record and no frame |
| Bethesda Terrace | 1 | J65 — the photograph's GPS on the upper deck is usable |
| the Barclays Center | 1 | J81 — the oculus canopy on the Atlantic/Flatbush corner |
| every sheet whose frame holds a Citi Bike station | — | Stage 40 — a kiosk and the real number of dock units instead of one bicycle |

Five sheets were rendered under the final code as the A/B before the pass and are already in the
repository (`bethesda_terrace_fountain`, `landmark_flatiron_building`, `landmark_barclays_center`,
`landmark_charging_bull`, `landmark_trinity_church`); they are rendered again in v16 all the same,
because the fan cap and Stage 40 landed after them.

## How to run or resume it

```
rm -f blender_out/render_all_state.json                      # only for a fresh start
setsid nohup python3 tools/render_all_sheets.py --workers 2 > /tmp/render_all_v16.log 2>&1 &
```

`render_all_sheets.py` skips everything in the state file's `done` and `declined`, so a restart picks
up where it stopped. Two workers: a sheet spends 73 % of its time in a single-threaded scene build and
27 % in a Cycles render that uses every core; the renders take an inter-process lock so only one runs
at a time, and a render peaks near 7.7 GB resident inside a 14.3 GB memory cgroup — three concurrent
renders were killed by the kernel, two workers with the lock fit. A kernel-killed sheet is requeued
once. The run stops itself when free disk falls below 700 MB; `blender_out/tiles/_merged` is
reproducible from the tiles and is the thing to delete first.

Roughly 4.7 minutes per sheet single-file; about 8–9 hours for the set with two workers.

## What is written for every sheet

`render.json` (the record: camera, clearance walk, subject height probe with 43 rays, sightline with
its fraction, `lighting.development` with the metered stops and the linear median), `render.png`
(developed from a linear EXR that is deleted once the PNG exists), `sheet.png`, `frame_stats.json`
(both halves' luminance statistics, their medians and their offset from the metering convention),
and — after the pass — `assessment.md`, written against that record by
`tools/workflows/assess_sheets.js` and checked by `tools/assessment_check.py`.

## After the pass

`render_sheets.py --write-index`; regenerate `docs/FIDELITY_REPORT.md`; the two record tests that are
red until every sheet is re-rendered (`test_every_daylight_render_publishes_the_exposure_it_was_metered_at`,
`test_every_subject_sightline_publishes_its_fraction_and_its_rule`) go green; `blender_out/tiles/_merged`
and `dist/first-drive` are rebuilt.
