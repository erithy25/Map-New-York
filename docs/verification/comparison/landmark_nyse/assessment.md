# New York Stock Exchange

`landmark_nyse` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:New York Stock Exchange August 2017 02.jpg by Arild Vågen, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2017, 1920x1282. [Commons page](https://commons.wikimedia.org/wiki/File:New_York_Stock_Exchange_August_2017_02.jpg)

**Camera** — camera 40.70716, -74.01053 (NYC_TM -5119, 790) z 8.2 m NAVD88 | azimuth 243.1deg pitch +0.0deg | 18 mm on 36 mm (90.0deg horizontal) | 1280x854. View direction: 243.1 deg, the bearing from this photograph's own GPS position to New York Stock Exchange (11 Broad Street); heading and position both come from the photograph.  The item's recorded azimuth is 251.7 deg, 8.6 deg away, and belongs to its nominal viewpoint. Aim: level optical axis (New York Stock Exchange (11 Broad Street) is 63 m away and would need +37 deg of tilt; a real frame would use a wider lens instead, and a tilted axis would stop the render being comparable on proportion).

**Sun** — azimuth 95.3°, elevation 43.5° at 2017-06-21T09:30:00-04:00 (photograph year only; 21 June 09:30 assumed).

**In frame** — 4/4 building tiles (82,358 tris), 10 landmark models, 1,813 pavement polygons, 543 props, 11,194 facade-kit pieces; 4,500,220 triangles; ground mesh 199² at 2.0 m near / 40.0 m far.

**Camera clearance** — the recorded viewpoint is under verify_terrain (0.2 m of ground or paving directly overhead, so the eye point is beneath the walking surface); the camera was moved 7 m onto the nearest real roadbed polygon in data/processed/roads/pavement, keeping the same eye height above the heightmap.  The view azimuth is clear for 37 m from there

**Verdict — the clearest recovery in the set: from a pure black frame (mean 0.000) with the camera standing inside a building to a frame in which the Exchange's Corinthian portico and pediment are actually visible — and it is still so dark that only the silhouette can be judged**

## What matches

* The camera was inside BIN 1001020 — ground 8.5 m, roof 27.8 m, eye at 8.9 m — which is why the first frame rendered at mean 0.000, sd 0.001. The up-ray test caught it and the pavement snap moved it out; the sheet states the correction.
* The New York Stock Exchange's own facade is now in the frame and identifiable: the six Corinthian columns of the Broad Street portico, the pediment above them and the deep entrance recess behind, at the right scale and the right place on the corner.
* The Wall Street corner reads correctly: 40 Wall's base on the right with its window grid, the Broad Street canyon opening to the left, and the towers stepping away up Broadway.
* Street furniture is placed and correct: a subway entrance with its railings and sign, a bench, a bishop's-crook lamp with a lit globe, a fire hydrant, a street tree.
* 1,863 pavement polygons carry the pedestrianised Wall Street geometry, and 10 landmark models are in range with their shells suppressed.

## What does not match

* Mean luminance 0.104: the Exchange faces east into a canyon and the Sun is behind the towers, so the portico is a silhouette. Nothing about its stone, its sculpture or its famous flag can be judged.
* The pediment is a plain triangle: the reference's 'Integrity Protecting the Works of Man' sculptural group is not modelled.
* There is no flag, no banner, no barrier, no security bollard, no signage — the things that fill the real corner.
* No people, no vehicles.
* Nothing in the frame has any surface texture or glazing.
* The lower half of the frame is bare untextured paving.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| frame far too dark | an east-facing facade in a canyon of 100-280 m towers, with two light bounces | lighting |
| plain pediment | the nyse landmark model carries the portico's columns and pediment form without its sculpture | geometry |
| no flag, barriers or signage | no stage produces them | data |
| no people or vehicles | no crowd or traffic placement feeds the verification scene | data |
| no texture or glazing | shells and models carry a flat base colour per material | material |

## Re-render note, 2026-09-07

Re-rendered against the corrected `b_wtc_site` model — the World Trade Center site stood 3.5 m too high, its plaza was an unbroken 520 x 520 m quad over both memorial pools, and its 220 oaks each carried a merged impostor card (`docs/verification/landmarks/REPORT_B.md` §12). Measured against the shipped render, **0.000 %** of pixels differ by more than 8/255 and the largest single difference is **1/255**, which is Cycles sampling noise at 32 samples, not content; frame mean and standard deviation are unchanged (0.104 / 0.069). The camera did not move. Nothing in this assessment changes.
