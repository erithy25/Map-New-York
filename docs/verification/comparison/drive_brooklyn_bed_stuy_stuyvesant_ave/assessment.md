# Brooklyn brownstone block: Bed-Stuy, Stuyvesant Avenue

`drive_brooklyn_bed_stuy_stuyvesant_ave` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Utica Avenue Station September 2022 003.jpg by Kidfly182, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2022-09-27 14:38:22, 1920x1440. [Commons page](https://commons.wikimedia.org/wiki/File:Utica_Avenue_Station_September_2022_003.jpg)

**Camera** — camera 40.68170, -73.93300 (NYC_TM 1438, -2050) z 19.3 m NAVD88 | azimuth 13.0deg pitch +0.0deg | 35 mm on 36 mm (54.4deg horizontal) | 1208x906. View direction: 13.0 deg as recorded in meta.json.  This item names no subject and the reference photograph's own view direction was not derived from the image (confidence: medium), so the two halves of this sheet are not guaranteed to face the same way -- compare them on street width, storey height and material, not on composition. Aim: level optical axis (the reference names no subject to aim at).

**Sun** — azimuth 218.0°, elevation 40.5° at 2022-09-27T14:38:22-04:00 (EXIF DateTimeOriginal).

**In frame** — 6/6 building tiles (633,718 tris), 0 landmark models, 1,138 pavement polygons, 266 props, 3,537 facade-kit pieces; 3,299,284 triangles; ground mesh 211² at 2.0 m near / 40.0 m far.

**Camera clearance** — the recorded viewpoint is inside t_1_-3_roof_membrane (a ray straight up from the eye point hits its roof); the camera was moved 17 m onto the nearest real roadbed polygon in data/processed/roads/pavement, keeping the same eye height above the heightmap.  The view azimuth is clear for 60 m from there

**Verdict — the first frame in the set with real brownstone architecture in it — arched window heads, stoops, railings, a continuous brick party wall — seen from five metres away, filling the frame, and paired with a photograph of a subway platform**

## What matches

* The brownstone block face is genuinely right in kind. The render carries a continuous three-storey brick wall with round-arched window heads, projecting stone lintels and a run of raised stoops with metal railings, which is exactly the Stuyvesant Heights vocabulary and the reason this drive-through area is in the brief.
* The stoops are correctly proportioned: about ten risers to a raised parlour floor, flanking railings, and a basement entry beneath, repeated at the block's own rhythm.
* The photograph's own EXIF GPS was rejected as mis-tagged (256 m away, past the 250 m gate) and the item's viewpoint used instead; the sheet states it.
* The camera was corrected out of a shell: the recorded viewpoint sits inside t_1_-3_roof_membrane and was snapped 17 m onto the nearest real roadbed polygon, with 60 m of clear view along the azimuth.
* 1,138 pavement polygons are placed with the correct kinds for a residential block: 328 roadbed, 172 sidewalk, 384 crosswalk, 50 parking-lot.

## What does not match

* The frames have nothing in common. The item is a residential street looking north; the photograph is the platform of Utica Avenue subway station, underground. No comparison of any kind is possible on this pairing, and the sheet says so.
* The camera is far too close to the block face. Standing 5 m off the wall, the frame is entirely facade with no street, no sky and no depth, so the streetscape the item exists to test is not visible.
* There is no glass in any opening, no window frames, no sashes, no doors in the stoop entries; the openings are recessed rectangles under their arches.
* There is no cornice line, no brownstone banding, no water table, no areaway railing, and no colour variation between adjacent houses — a Bed-Stuy block is a run of individually coloured houses, not one continuous plane.
* No street trees are visible in frame, though 266 props were placed; no parked cars; no people; no rubbish bins on the kerb.
* The roadway and sidewalk are flat untextured planes.
* Props were capped by the triangle budget at 266 placed.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the two halves have nothing in common | the reference stage paired a residential-street item with a subway-platform photograph and assigned it the item's azimuth | reference |
| camera 5 m from a wall | the clearance rule tests the view azimuth and a narrow cone, not the frame as a whole; the nearest roadbed polygon put the camera against the block face | camera |
| no glass, frames or doors | the facade kit's window and door pieces carry openings and reveals but no glazing or joinery | material |
| no cornice, banding or per-house colour | shells carry one material per class over a whole run; the kit has no cornice or string course for this facade class here | geometry |
| no cars, people or bins | no traffic, crowd or refuse placement feeds the verification scene | data |
| untextured ground | flat colour per pavement kind, no texture | material |
