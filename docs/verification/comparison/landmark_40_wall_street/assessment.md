# 40 Wall Street (Trump Building)

`landmark_40_wall_street` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:View of Manhattan from Liberty Island ferry, NYC, 20231003 1627 2026.jpg by Jakub Hałun, CC BY 4.0 (https://creativecommons.org/licenses/by/4.0), taken 2023-10-03 16:27:26, 1920x909. [Commons page](https://commons.wikimedia.org/wiki/File:View_of_Manhattan_from_Liberty_Island_ferry,_NYC,_20231003_1627_2026.jpg)

**Camera** — camera 40.70629, -74.01193 (NYC_TM -5180, 698) z 5.7 m NAVD88 | azimuth 70.0deg pitch +0.0deg | 18 mm on 36 mm (90.0deg horizontal) | 1280x606. View direction: 70.0 deg as recorded; it agrees with the bearing from the camera position used to 40 Wall Street (Trump Building) (70.1 deg) to 0.1 deg. Aim: level optical axis (40 Wall Street (Trump Building) is 200 m away and would need +35 deg of tilt; a real frame would use a wider lens instead, and a tilted axis would stop the render being comparable on proportion).

**Sun** — azimuth 242.9°, elevation 22.4° at 2023-10-03T16:27:26-04:00 (EXIF DateTimeOriginal).

**In frame** — 5/5 building tiles (83,670 tris), 13 landmark models, 2,385 pavement polygons, 623 props, 10,650 facade-kit pieces; 4,500,745 triangles; ground mesh 211² at 2.0 m near / 40.0 m far.

**Camera clearance** — the recorded viewpoint is rendered as an unusable frame from this eye point, so it is treated as blocked even though no ray test caught it; the camera was moved 52 m onto the nearest real roadbed polygon in data/processed/roads/pavement, keeping the same eye height above the heightmap.  The view azimuth is clear for 96 m from there

**Verdict — the lens rule now gets the tower's base and Federal Hall's colonnade into shot at 18 mm, and the crown the item exists to test is still above the top of the frame; the pairing is hopeless anyway, because the only photograph collected is a harbour panorama taken 1.5 km away**

## What matches

* The lens rule fired and is stated on the sheet: 35 mm widened to the 18 mm floor because the 282 m tower stands 284 m above the lens only 200 m away, 55 deg above the horizon. That brought the tower's base, the street and Federal Hall into the frame where a 35 mm level axis had shown only a dark corner.
* Federal Hall's Doric colonnade and pediment are recognisable on the left at the right distance and the right scale — a real landmark model doing real work.
* The camera's own guard worked: the first frame from the recorded eye point was unusable, so the clearance correction was forced and the camera moved 52 m onto the nearest real roadbed, with 96 m of clear view.
* The photograph's own EXIF GPS was correctly rejected as mis-tagged at 1,535 m.
* The heading is right: 70.0 deg as recorded, agreeing with the bearing to 40 Wall Street (70.1 deg) to 0.1 deg.
* Street furniture is placed and correct: subway entrance railings, a fire hydrant, cobra-head lamps, street trees, and 2,385 pavement polygons with the kerb line reading clearly across the frame.

## What does not match

* The pyramidal green crown — the whole point of the item — is above the top of the frame even at 18 mm, and the sheet says so. A level axis cannot contain a 282 m tower from 200 m; the alternatives are a tilted camera that skews every vertical, or a viewpoint further away, which the item does not give.
* The reference photograph is of somewhere else entirely: the whole Lower Manhattan skyline from the Liberty Island ferry, 1.5 km out. Nothing in it corresponds to anything in the render.
* The frame is still very dark, mean 0.131. Wall Street at Broad is a 12 m canyon between 60-100 m walls under a 22 deg October Sun; the geometry is right and it genuinely is that dark, but nothing can be judged from it.
* The tower's base has no surface: a flat pale plane with unglazed window dashes where the real building is limestone with deep-set bronze-framed windows and a rusticated base.
* No people, no vehicles, no signage, no road markings.
* The facade kit was capped by the triangle budget at 10,650 of 18,999 records in range.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the crown is still out of frame | even the 18 mm floor gives 51 deg of vertical angle against the 55 deg the subject needs; going wider would distort the comparison | camera |
| the reference is a photograph of somewhere else | no photograph of 40 Wall Street from its own viewpoint was collected | reference |
| frame too dark to read | a 12 m canyon between 60-100 m walls at a 22 deg Sun with two light bounces | lighting |
| no surface on the tower base | shells carry a per-material base colour; the kit supplies openings without glass or mouldings | material |
| no people, vehicles, signage or markings | no stage places any of them | data |
| nearly half the facade kit not drawn | the 4.5 M triangle budget is spent before the kit finishes | geometry |

## Re-render note, 2026-09-07

Re-rendered against the corrected `b_wtc_site` model — the World Trade Center site stood 3.5 m too high, its plaza was an unbroken 520 x 520 m quad over both memorial pools, and its 220 oaks each carried a merged impostor card (`docs/verification/landmarks/REPORT_B.md` §12). Measured against the shipped render, **0.000 %** of pixels differ by more than 8/255 and the largest single difference is **1/255**, which is Cycles sampling noise at 32 samples, not content; frame mean and standard deviation are unchanged (0.131 / 0.084). The camera did not move. Nothing in this assessment changes.
