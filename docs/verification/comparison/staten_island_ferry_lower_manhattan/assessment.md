# Staten Island Ferry deck view of Lower Manhattan

`staten_island_ferry_lower_manhattan` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Lower Manhattan from Staten Island Ferry February 2015 002.jpg by King of Hearts, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2015-02-15 13:51, 1920x840. [Commons page](https://commons.wikimedia.org/wiki/File:Lower_Manhattan_from_Staten_Island_Ferry_February_2015_002.jpg)

**Camera** — camera 40.69100, -74.02150 (NYC_TM -6044, -997) z 8.0 m NAVD88 | azimuth 15.8deg pitch +0.0deg | 28 mm on 36 mm (65.5deg horizontal) | 1280x560. View direction: 15.8 deg as recorded; it agrees with the bearing from the camera position used to One World Trade Center (15.9 deg) to 0.1 deg. Aim: level optical axis (the subject is 2510 m away; anything that far is photographed with a level camera).

**Sun** — azimuth 209.3°, elevation 31.9° at 2015-02-15T13:51:00-05:00 (EXIF DateTimeOriginal (minutes)).

**In frame** — 68/120 building tiles (1,116,856 tris), 30 landmark models, 496 pavement polygons, 36 props, 236 facade-kit pieces; 2,596,398 triangles; ground mesh 373² at 3.125 m near / 40.0 m far.

**Verdict — the island is in the right place, the right order and the right proportion, and it is a pale grey massing model floating on a mirror; below the skyline the frame has nothing in it at all**

## What matches

* The skyline profile is right: One World Trade Center with its spire at the centre where the subject bearing puts it, the Financial District ridge stepping down to its right, the low Battery buildings closing the run, and the Trinity Church spire visible as a small green mark against them.
* The heading is measured and agrees with the metadata: 15.8 deg as recorded, 15.9 deg from the camera to One World Trade Center.
* The camera is at the eye height the viewpoint note gives, with its source stated: 8.0 m above sea level, being a Molinari-class ferry's promenade deck at 6.4 m plus 1.6 m.
* The photograph's own EXIF GPS was rejected as mis-tagged at 699 m and the item's viewpoint used. That was the right call and it is worth recording why: with the photograph's fix the camera lands in the Hudson west of Battery Park City and the whole island falls to the right of the frame; from the item's point, 1 nautical mile south of Whitehall, the island sits across the axis as it does in the reference.
* 67 of the 119 tiles import, 11 by LOD fallback; 34 landmark models are placed and their shells suppressed, so nothing is drawn twice.
* The Sun is from the photograph's own EXIF instant (2015-02-15 13:51 EST, elevation 31.8 deg) and the towers are lit from the same side.

## What does not match

* The render is taken from further out than the photograph — 2,510 m against the photographer's own position — so the island spans about 60 % of the frame where the reference fills it. The item's viewpoint is a route description, not a position, and no position on that route reproduces the reference exactly.
* The water is a mirror. Roughness 0.06 with no wave normal makes the Upper Bay a perfect reflector, and the inverted skyline under the waterline is the least believable thing in the frame. The reference is February pack ice: broken, matte, almost white.
* Nothing is on the water: no ferries, no tugs, no barges, no buoys, no wake.
* The Whitehall ferry terminal, the Battery Maritime Building, Pier A, the Battery's seawall and the Staten Island Ferry's own slips are all absent; the shoreline is a bare terrain edge with pavement draped over it.
* Every tower is a flat pastel solid. At 2.5 km the reference still shows glass, vertical banding and window grids on 200 Vesey, 17 State Street and the Blue Tower; the render shows none, so the skyline reads as a study model.
* The frame is washed out: mean luminance 0.764 against a February photograph with a deep blue sky and strong contrast. The Nishita sky plus the exposure rule opens the shadows further than the reference's.
* 52 of the 119 tiles had no shell, so the New Jersey bank behind the island was empty. **Superseded by the 2026-09-07 re-render below**: 103 of 120 tiles now import, 37 of them carrying New Jersey shells, and the left third of the skyline is built up.
* There is no ferry under the camera: the boat is not modelled and the eye floats free at 8 m over the water. The sheet states this.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| taken from further out than the photograph | the item's viewpoint describes a route, not a position, and the photograph's own EXIF fix is off that route | reference |
| mirror-flat water | the water material is roughness 0.06 with no normal map and no wave displacement | material |
| no ice | no seasonal water state exists in any dataset | data |
| no vessels | no stage places boats | data |
| no terminal, piers, slips or seawall | waterfront structures are neither building footprints nor props, so no stage builds them | geometry |
| flat pastel towers | shells carry a per-material base colour with no facade texture or glass | material |
| washed-out sky and shadows | a clear-sky Nishita atmosphere with an exposure that only opens; the reference's winter contrast is not reproduced | lighting |
| ~~empty New Jersey bank~~ | was: no `tile_buildings.glb` outside the five boroughs. The New Jersey stage has since produced them and the 2026-09-07 re-render draws 37 tiles of them | data |
| no ferry under the camera | no vessel geometry exists; the sheet states the camera floats | geometry |

## Re-render note, 2026-09-07

Re-rendered against the corrected `b_wtc_site` model — the World Trade Center site stood 3.5 m too high, its plaza was an unbroken 520 x 520 m quad over both memorial pools, and its 220 oaks each carried a merged impostor card (`docs/verification/landmarks/REPORT_B.md` §12). **1.30 % of the frame changed, and almost none of it is the World Trade Center.** The whole left third of the skyline — empty water with two pier stubs in the shipped sheet — is now built up: the scene imported **103** building tiles against 68, **37** of them carrying `tile_buildings_nj.glb`, because the New Jersey building stage landed on disk after this sheet was first rendered. That is a data change, not a consequence of the World Trade Center fix. The World Trade Center's own contribution is the 3.5 m the model dropped, which at 2,389 m subtends 0.084 deg — about 1.6 px at this focal length. The verdict above is unchanged; the New Jersey shoreline it says is missing is now partly there and should be re-judged by whoever owns that stage.
