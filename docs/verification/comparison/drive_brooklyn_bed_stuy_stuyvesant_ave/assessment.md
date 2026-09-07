# Brooklyn brownstone block: Bed-Stuy, Stuyvesant Avenue

`drive_brooklyn_bed_stuy_stuyvesant_ave` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Bed-Stuy 20191130 - 27 - Nostrand @ Greene.jpg by Andre Carrotflower, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2019-11-30 10:22:34, 1920x1440. [Commons page](https://commons.wikimedia.org/wiki/File:Bed-Stuy_20191130_-_27_-_Nostrand_@_Greene.jpg)

**Camera** — camera 40.68170, -73.93300 (NYC_TM 1438, -2050) z 19.3 m NAVD88 | azimuth 13.0deg pitch +0.0deg | 35 mm on 36 mm (54.4deg horizontal) | 1208x906. View direction: 13.0 deg as recorded in meta.json.  This item names no subject and the reference photograph's own view direction was not derived from the image (confidence: medium), so the two halves of this sheet are not guaranteed to face the same way -- compare them on street width, storey height and material, not on composition. Aim: level optical axis (the reference names no subject to aim at).

**Sun** — azimuth 159.0°, elevation 24.9° at 2019-11-30T10:22:34-05:00 (EXIF DateTimeOriginal).

**In frame** — 6/6 building tiles (669,448 tris), 0 landmark models, 1,138 pavement polygons, 361 props, 3,563 facade-kit pieces; 3,320,072 triangles; ground mesh 211² at 2.0 m near / 40.0 m far; props capped by the triangle budget. Frame mean 0.408, sd 0.133.

**Camera clearance** — the recorded viewpoint is inside t_1_-3_roof_membrane (a ray straight up from the eye point hits its roof); the camera was moved 17 m onto the nearest real roadbed polygon in data/processed/roads/pavement, keeping the same eye height above the heightmap.  The view azimuth is clear for 60 m from there

**Verdict — re-rendered 2026-09-07 against a Bed-Stuy brownstone row instead of a subway platform. Both halves are now the same building type: a continuous brownstone terrace with arched window heads, stoops with iron rails and a sidewalk shed. They are not the same block — the photograph is at Nostrand and Greene, 1,712 m from the item's viewpoint, so its GPS is rejected and the camera stays at Stuyvesant and Decatur — and the render is still a party wall five metres from the lens rather than a street. What the pairing can now test, it passes: storey height, stoop rise, arch springing, cornice depth, brownstone colour**

## What changed, and why

Two of this item's three photographs were of the **Utica Avenue subway platform** — a kilometre away
and underground. They passed because the item's only keyword group was `["stuyvesant", "bedford"]`
and `"stuyvesant"` matches inside the category "Bedford-Stuyvesant, Brooklyn", which every photograph
taken in the neighbourhood carries. The subject test now reads the photograph's own title and
description rather than its categories, and this item requires one of `"stuyvesant avenue"`,
`"stuyvesant heights"`, `"decatur street"`, `"macdonough"`, `"bedford-stuyvesant"` or `"bed-stuy"`; its
exclusions also now name the subway, the platform and Utica Avenue directly
(`docs/verification/comparison/REPORT.md` §2.11).

## What matches

* The brownstone block face is genuinely right in kind. The render carries a continuous three-storey brick wall with round-arched window heads, projecting stone lintels and a run of raised stoops with metal railings, which is exactly the Stuyvesant Heights vocabulary and the reason this drive-through area is in the brief.
* The stoops are correctly proportioned: about ten risers to a raised parlour floor, flanking railings, and a basement entry beneath, repeated at the block's own rhythm.
* **The photograph is of the same thing the render is of**, which it was not before: a brownstone
  terrace with arched heads, stoops, iron rails and a green sidewalk shed. The render has all four.
* The photograph's own EXIF GPS was rejected as mis-tagged (1,712 m away) and the item's viewpoint used instead; the sheet states it.
* The camera was corrected out of a shell: the recorded viewpoint sits inside t_1_-3_roof_membrane and was snapped 17 m onto the nearest real roadbed polygon, with 60 m of clear view along the azimuth.
* 1,138 pavement polygons are placed with the correct kinds for a residential block: 328 roadbed, 172 sidewalk, 384 crosswalk, 50 parking-lot.

## What does not match

* **The photograph is 1,712 m from the render.** Same building type, different block — Nostrand at
  Greene rather than Stuyvesant at Decatur — because its GPS is past the sanity radius and this item is
  a view *from* a named block rather than *of* a subject, so the radius stands. The two halves compare
  on typology and not on place.
* The camera is far too close to the block face. Standing 5 m off the wall, the frame is entirely facade with no street, no sky and no depth, so the streetscape the item exists to test is not visible.
* There is no glass in any opening, no window frames, no sashes, no doors in the stoop entries; the openings are recessed rectangles under their arches.
* There is no cornice line, no brownstone banding, no water table, no areaway railing, and no colour variation between adjacent houses — a Bed-Stuy block is a run of individually coloured houses, not one continuous plane.
* No street trees are visible in frame, though 361 props were placed; no parked cars; no people; no rubbish bins on the kerb.
* The roadway and sidewalk are flat untextured planes.
* Props were capped by the triangle budget at 361 placed.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| ~~the two halves have nothing in common~~ | **fixed**: the subject test reads the photograph's own title and description rather than its categories, so "Bedford-Stuyvesant, Brooklyn" on a subway platform no longer qualifies | reference |
| the photograph is of a different block 1.7 km away | its GPS is past the sanity radius, which stands for an item that is a view from a named block | reference |
| camera 5 m from a wall | the clearance rule tests the view azimuth and a narrow cone, not the frame as a whole; the nearest roadbed polygon put the camera against the block face | camera |
| no glass, frames or doors | the facade kit's window and door pieces carry openings and reveals but no glazing or joinery | material |
| no cornice, banding or per-house colour | shells carry one material per class over a whole run; the kit has no cornice or string course for this facade class here | geometry |
| no cars, people or bins | no traffic, crowd or refuse placement feeds the verification scene | data |
| untextured ground | flat colour per pavement kind, no texture | material |
