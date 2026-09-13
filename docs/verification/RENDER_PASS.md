# The comparison-sheet render pass: where it stands and how it is resumed

One file, kept current, because the pass runs for hours in a container that can be reclaimed and its
resume state lives outside the repository (`blender_out/render_all_state.json`, untracked because it
changes on every sheet). Losing that file would mean re-rendering everything already done.

## v17 — every sheet again, for the eight verification faults the v16 pass found

The v16 pass finished 171 sheets and one declined interior, and reading those 172 records found
**eight faults in the verification itself** (docs/DEVIATIONS.md J111 to J118). Each of them changes
what is rendered -- which photograph, which instant, where the camera stands, or what the record
says -- so fixing them without re-rendering would leave 172 sheets carrying the old answers, and
fixing them *and* re-rendering makes all 172 assessments stale. This pass is the second way.

| fix | what it changes in the render | sheets it is measured to touch |
|---|---|---|
| J112 reference chooser: a coarse distance band on the non-drive groups, aim error ranked above the EXIF clock, an unmeasured heading ranked past the worst measured one | which photograph a sheet is compared against | **27 of 172** change photograph |
| J114 the instant: the photograph's own title, description and categories are read before the solstice fallback; the item's own name may name an hour | the date, so the canopy, the Sun and the crowd | **31 of 172** gain a real date (2 still assumed); the hour window fires on **1** |
| J115 a deck is a street's ceiling, not a room: five named `struct_*` deck parts no longer read as indoors | whether the camera is moved at all | the two elevated-railway sheets |
| J116 a view short of the frame's own `min_view_m` is a fourth trigger for the walk, with the recorded position entered as the baseline it has to beat | where the camera stands | **1 of 171** (the other five below their minimum had already searched) |
| J111 the sidestep ranks candidates on the fan's own hit count and refuses one that ends nearer the prop | where the camera stands, and the published sightline fraction | the two sheets that used the rule, both of which it had failed |
| J113 the fan spans every part of the model, across this camera's bearing | `subject_fan_m`, the half-angle and `subject_visible_fraction` | every sheet naming a landmark subject |
| J117a kit counts as built fabric in the clearance sample, the view distance and the sightline | what the record names at the lens, and where a camera stands when a shed is in front of it | every sheet with kit off the facade in frame |
| J117b the agent half of a clearance note is filled from the record's own fields after the cull | the prose under every picture | **19 of 171** were contradicting themselves |

### Disk, measured before the pass rather than discovered at sheet 59

A full pass rewrites **909.8 MB** of artefacts (`sheet.png` 694.2, `render.png` 209.5, the records
5.9, the frame statistics 0.2), and because PNGs are already deflate-compressed that is what they
cost again as git objects. The container had **630 MB** free against `.git` holding 3.76 GiB of
loose objects beside a 3.40 GiB pack, and a repack cannot help: it writes the new pack before
removing the old, so it needs about 6.8 GB of room to save a few per cent on content that does not
delta-compress.

What made the pass possible instead is `tools/tile_reach.py`, which measures what no catalogued
viewpoint can reach -- **each viewpoint's own radius**, and **each class's own loader radius**, not
one flat number -- and deletes only that, appending every name to a rebuild list. Measured over the
172 viewpoints: **5,677 MB** of tile artefacts are unreachable. Four classes were deleted, the ones
whose source data is present and whose rebuild is a documented stage:

| class | deleted | freed | rebuild list |
|---|---|---|---|
| `tile_pavement.glb` | 137 tiles | 2,193 MB | `pavement_rebuild_needed.txt` (395 tiles) |
| `tile_buildings_nj.glb` | 424 tiles | 777 MB | `buildings_nj_rebuild_needed.txt` |
| `tile_structures.glb` | 612 tiles | 121 MB | `structures_rebuild_needed.txt` |
| `tile_parkground.glb` | 17 tiles | 18 MB | `parkground_rebuild_needed.txt` |

`tile_buildings.glb` was **not** touched, although 626 of its tiles (2,569 MB) are equally
unreachable: the four classes above cleared enough room, and a building shell is the expensive
thing to rebuild. Free after the deletions: **3,598 MB**.

### The 90 pavement tiles that had to come back first

The same measurement found J118: the v16 pass's own housekeeping deleted pavement tiles under the
rule *"further than 3 km from every viewpoint still to be rendered"*, which is a statement about a
queue where a deletion is a statement about a repository. **90 of the pavement tiles a viewpoint's
loader can reach were missing, 71 of them named in a published record's own `tiles_read`** --
`landmark_george_washington_bridge`, `drive_bronx_grand_concourse`, `landmark_kosciuszko_bridge`
and `landmark_bronx_county_courthouse` among the sheets. They are rebuilt before the pass starts,
from the untouched `data/processed/roads/pavement/*.parquet`:

```
python3 tools/tile_reach.py --missing pavement > /tmp/pav.txt
python3 blender/roads/build_pavement.py --tiles $(grep '^t_' /tmp/pav.txt | paste -sd,) --workers 2
```

`tests/test_comparison.py::test_every_tile_a_published_sheet_loaded_is_still_on_disk` is the check
that found it and stays red until the rebuild finishes.

### Running it

```
rm -f blender_out/render_all_state.json                 # all 172, from the start
bash tools/pass_tick.sh                                 # commits what finished, restarts the runner
```

`tools/pass_tick.sh` is the whole loop for a container that does not live eight hours: it commits
and pushes the sheets that finished, refuses to start a second runner, refuses to start at all
below 350 MB, and counts the declined interior so the pass can reach its own target. Run it on
every container start until it says the pass is complete.

Two tests are red between the code changes and the finished pass, both by design:
`test_no_comparison_scene_silently_changed_which_photograph_it_shows` (J112 changed 27 picks) and
`test_no_render_record_contradicts_itself_about_the_nearest_agent` (J117b, 19 records). A third,
`test_every_tile_a_published_sheet_loaded_is_still_on_disk`, is red until the pavement rebuild
lands.

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
| every street sheet with a bus shelter, LinkNYC kiosk, newsstand, bus stop blade or bike rack in frame | — | J84 — the six dataset-placed kerb kinds stood square to north; they now take the kerb's heading and the side of the centreline |
| the seven Hudson Yards sheets | 7 | J85 — the platform is a terrain deck; Tenth Avenue no longer dives 8 m into the rail yard's DEM, and `landmark_15_hudson_yards` stands on the named node |
| the twenty-three park and open-space sheets | 23 | Stage 55 — woodland coverage from the OSM polygons the build already holds, stems declared procedural; the Ramble and every other wood was bare terrain |

Five sheets were rendered under the final code as the A/B before the pass and are already in the
repository (`bethesda_terrace_fountain`, `landmark_flatiron_building`, `landmark_barclays_center`,
`landmark_charging_bull`, `landmark_trinity_church`); they are rendered again in v16 all the same,
because the fan cap and Stage 40 landed after them.

## How to run or resume it

```
rm -f blender_out/render_all_state.json                      # only for a fresh start
setsid nohup python3 tools/render_all_sheets.py --workers 2 --last $(cat docs/verification/render_pass_last.txt) \
    > /tmp/render_all_v16.log 2>&1 &
```

`--last` puts the thirty sheets in `render_pass_last.txt` (the seven Hudson Yards sheets, the
twenty-three park sheets) at the end of the queue: the platform deck (J85) and the canopy stage
(Stage 55) were still being built when the pass started, and a sheet those fixes touch is rendered
once, with them, rather than twice. The kerb headings (J84) touch nearly every street sheet, so the
pass did not start until that rebuild had landed.

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


## Disk: the 259 pavement meshes this pass does not need

The container's writable allowance ran out at sheet 59 and the runner stopped itself at its 700 MB
floor, as it is built to. `blender_out/tiles/*/tile_pavement.glb` is the largest artefact class in
the build -- **7.95 GB over 546 tiles** -- and 259 of those tiles lie further than 3 km from every
viewpoint still to be rendered, so no remaining sheet can load them. They were deleted (**3.20 GB**)
and their names are in `pavement_rebuild_needed.txt`. Nothing measured is lost: they are built from
`data/processed/roads/pavement/*.parquet`, which is untouched, at about 45 s a tile:

```
python3 blender/roads/build_pavement.py --tiles $(paste -sd, docs/verification/pavement_rebuild_needed.txt) --workers 2
```

**They must be rebuilt before any content package is cut for those tiles**, or the package ships a
tile whose roadway is missing. The first-drive region is not among them.
