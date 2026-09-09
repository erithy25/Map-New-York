# Where the v15 comparison-sheet pass stands

This file exists because the pass runs for hours in a container that can be reclaimed, and its
resume state lives outside the repository (`blender_out/render_all_state.json`, untracked, because
it changes on every sheet). Losing that file would mean re-rendering everything already done. This
is its snapshot, written by hand at the moment below, and it is what a fresh container should be
told.

**Snapshot taken:** 2026-09-09T00:28:30Z ·
**commit:** `68b15f5`

| | count |
|---|---|
| reference slugs with a photograph on disk | **172** |
| rendered in this pass | **29** |
| refused as unusable (`rejected_unusable_frame`) | **2** |
| never rendered in this pass yet | **141** |
| rendered, with an assessment written against **that** render | **19** |
| rendered, assessment missing or older than the render | **10** |
| assessments in the repository in total | **57**, of which **37** are older than their own render |

## How to restart it

```
mkdir -p blender_out
cat > blender_out/render_all_state.json <<'JSON'
{
 "done": [
  "bethesda_terrace_fountain",
  "drive_bronx_arthur_ave",
  "drive_bronx_grand_concourse",
  "drive_brooklyn_bed_stuy_stuyvesant_ave",
  "drive_brooklyn_park_slope_7th_ave",
  "drive_lower_manhattan_broadway_wall_st",
  "drive_lower_manhattan_stone_st",
  "drive_queens_bayside",
  "drive_queens_forest_hills",
  "drive_queens_jackson_heights",
  "dumbo_washington_st_manhattan_bridge",
  "fifth_ave_42nd_north",
  "fifth_ave_42nd_south",
  "landmark_40_wall_street",
  "landmark_911_memorial_pools",
  "landmark_barclays_center",
  "landmark_brooklyn_bridge_from_dumbo",
  "landmark_charging_bull",
  "landmark_chrysler_building",
  "landmark_city_hall",
  "landmark_domino_sugar_refinery",
  "landmark_empire_state_building",
  "landmark_flatiron_building",
  "landmark_grand_central_facade",
  "landmark_high_line",
  "landmark_hudson_yards_vessel",
  "landmark_madison_square_garden",
  "landmark_manhattan_bridge",
  "landmark_metlife_building"
 ],
 "failed": [
  "landmark_equitable_building",
  "landmark_federal_hall"
 ],
 "skipped": []
}
JSON
setsid nohup python3 tools/render_all_sheets.py > /tmp/render_all_v15.log 2>&1 &
```

`render_all_sheets.py` skips everything in `done`, so the run picks up exactly where it stopped.
It stops itself cleanly when free disk falls below its 700 MB floor; if that happens,
`blender_out/tiles/_merged` is reproducible from the tiles and is the thing to delete first.

## Refused, and why that is the right outcome

Both of these were rendered and the frame gate refused to publish them — a frame below mean 0.06 is
not evidence, and publishing one would be worse than publishing nothing.

* `landmark_equitable_building`
* `landmark_federal_hall`

`landmark_equitable_building` has its assessment written against the refusal; it is the sharpest
case in the set for J79. `landmark_federal_hall` is queued for re-render under J80 — its 0.021 mean
is what a 09:30 sun does to Wall Street.

## Rendered and still waiting for an assessment

* `landmark_barclays_center`
* `landmark_city_hall`
* `landmark_domino_sugar_refinery`
* `landmark_empire_state_building`
* `landmark_grand_central_facade`
* `landmark_high_line`
* `landmark_hudson_yards_vessel`
* `landmark_madison_square_garden`
* `landmark_manhattan_bridge`
* `landmark_metlife_building`

## Also queued for re-render

See [`RERENDER_QUEUE.md`](RERENDER_QUEUE.md) — sheets whose frame is a picture of a state the
repository no longer holds.

## The rhythm each assessment is written in

Per finished sheet, in this order — the middle step is the one no tool can do:

```
python3 tools/assessment_header.py <slug>     # the header, generated from the record itself
python3 tools/sheet_brief.py     <slug>       # everything in the record that is quotable
python3 tools/sheet_pair.py      <slug>       # both halves in one image — then look at them
                                              # write docs/verification/comparison/<slug>/assessment.md
python3 tools/assessment_check.py <slug>      # every figure must appear in that sheet's own record
python3 tools/png_decodes.py                  # every changed PNG decodes
                                              # commit, push
```

Two rules this pass paid for:

* **No figure that is not in that sheet's own record.** Historical values, city-wide medians and
  the assessment's own subtractions all fail `assessment_check.py`. Either dissolve them into
  prose or leave them out; a measurement that belongs to the whole set belongs in
  `docs/DEVIATIONS.md`, not on a sheet.
* **Look at both halves.** Four of the deviations found in this pass — J74's Charging Bull
  amendment, J78's "blocked by itself", J81 and J82 — were visible in the picture and invisible in
  the record, and each of them would have been written up backwards from the record alone.

## What is still open when the pass finishes

| | |
|---|---|
| J78 | count a hit on the subject's own model as finding it; size the fan to the subject **and** the frame; report the fraction rather than a majority of five rays |
| J79 | run the sightline probe **inside** `camera._move_clear_of_geometry` and score candidates by it |
| J74 | denser probe rings, so a subject smaller than 6 m cannot fall between them |
| J65 | a viewpoint on Bethesda Terrace's upper deck |
| then | `render_sheets.py --write-index`, regenerate `docs/FIDELITY_REPORT.md`, rebuild `blender_out/tiles/_merged/l2,l3`, re-issue `dist/first-drive`, full suite green except the honest Midtown/J69 red |
