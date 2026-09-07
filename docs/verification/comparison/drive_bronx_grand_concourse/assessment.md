# Bronx drive-through: Grand Concourse Art Deco apartments

`drive_bronx_grand_concourse` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Dollar Savings Bank of New York headquarters building, Grand Concourse & East Fordham Road, The Bronx, New York.jpg by Deansfa, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2022-10-09 12:16:14, 1920x2560. [Commons page](https://commons.wikimedia.org/wiki/File:Dollar_Savings_Bank_of_New_York_headquarters_building,_Grand_Concourse_%26_East_Fordham_Road,_The_Bronx,_New_York.jpg)

**Camera** — camera 40.83200, -73.91860 (NYC_TM 2644, 14663) z 31.6 m NAVD88 | azimuth 25.0deg pitch +0.0deg | 35 mm on 36 mm (42.2deg horizontal, 54.4deg vertical, portrait) | 904x1206. The camera stands on the item's recorded viewpoint: this photograph's own EXIF GPS is 3,854 m away, past the 250 m at which it could still be the same view, so it was rejected as mis-tagged. View direction: 25.0 deg as recorded in meta.json; the item names no subject and the photograph's own view direction was not derived from the image.

**Sun** — azimuth 171.0°, elevation 42.4° at 2022-10-09T12:16:14-04:00 (EXIF DateTimeOriginal).

**In frame** — 6/6 building tiles (319,132 tris), 2 landmark models, 2,433 pavement polygons, 398 props, 6,754 facade-kit pieces; 3,686,473 triangles; ground mesh 211² at 2.0 m near / 40.0 m far; props capped by the triangle budget. Frame mean 0.254, sd 0.172.

**Camera clearance** — the recorded viewpoint is inside `t_2_14_roof_membrane` (a ray straight up from the eye point hits its roof); the camera was moved 5 m onto the nearest real roadbed polygon, keeping the same eye height above the heightmap. The view azimuth is clear for 60 m from there.

**Verdict — the reference improved and the render did not. The photograph is now a Grand Concourse view: the boulevard's balustraded median wall in the foreground, the service road and main roadway receding, the Dollar Savings Bank tower above — which is the section this drive-through exists to test. The render is still a building wall two metres from the lens with air-conditioner units on it, because the camera search moved the recorded viewpoint 5 m and stopped there. This is the weakest sheet of the seven the reference pass touched**

## What changed, and why

The three photographs this item shipped with were the Bronx County Courthouse, an expressway
interchange and Loew's Paradise Theatre — every one a *building on* the Grand Concourse rather than
the boulevard, admitted because `"grand concourse"` is the category on all of them. The subject test
now reads the photograph's own title and description rather than its categories, and `not_of` rejects
a title naming a courthouse, a theatre, an expressway or a fallout shelter
(`docs/verification/comparison/REPORT.md` §2.11): 21 candidates were rejected on keywords, 20 on the
exclusions, 5 on the title test and 3 on the subject test.

What came back is better and still not right. The chosen photograph does show the Concourse's own
section — its median balustrade, service road and main roadway — but it was taken at **East Fordham
Road, 3,854 m north** of the item's viewpoint at East 165th Street, so its GPS is rejected and the
camera stays where the item puts it. **Commons has very few free photographs looking along this
boulevard**, and none that this item's rules admit near 165th Street. Choosing between a photograph
of the right street in the wrong place and a photograph of a building on it is a choice between two
kinds of wrong; the first at least shows the roadway section the drive-through is about.

## What matches

* The photograph's own EXIF GPS was correctly rejected: it is 3,604 m from the item's viewpoint, so the item's recorded position was used and the sheet says so. This is the largest GPS disagreement in the whole set and the sanity gate caught it.
* The camera was corrected out of a building: the recorded viewpoint sits inside t_2_14_roof_membrane and was snapped 5 m onto the nearest real roadbed polygon, with 60 m of clear view along the azimuth from there.
* The street trees are correct for late April: full canopies, right heights, planted at the kerb, with 16 opaque impostor cards dropped.
* The street section is right for the Grand Concourse's side streets: roadbed, both sidewalks, kerb reveal, and 2,433 pavement polygons including 601 crosswalk and 88 parking-lot polygons.
* Sidewalk sheds with green netting run along the west frontage, and the building masses behind them are the right height for the Concourse's six-storey Art Deco apartment blocks.
* The Sun is from the photograph's own EXIF instant (2022-10-09 12:16:14 EDT, elevation 42.4 deg, azimuth 171.0 deg) — a midday October sun, which is what both frames show.

## What does not match

* The composition is spoiled by proximity. A street-lamp column stands about 2 m from the lens and a building wall about 5 m to the right, so half the frame is a featureless plane. The clearance rule checks the view azimuth, not the whole cone, so a camera can be accepted with a wall beside it.
* **The photograph is of the Grand Concourse 3.9 km north of the render.** Its own GPS is 3,854 m from
  the item's viewpoint, so it is rejected and the camera stays at East 165th Street while the
  photograph is at East Fordham Road. The two halves are of the same boulevard and not of the same
  place on it.
* **The render does not show the boulevard at all.** The photograph's whole subject is the Concourse's
  section — median balustrade, service road, main roadway — and the render is a wall two metres away.
  The camera search moved the recorded viewpoint 5 m onto the nearest roadbed and stopped; the
  clearance rule tests the view azimuth and a 12 deg cone, so a wall beside the lens passes.
* Nothing in the render is Art Deco. The blocks are plain masses with no string courses, no polychrome brick, no corner windows, no rounded balconies and no cornice — the features the item exists to test.
* No signage, no shopfront glass, no lettering, no marquee anywhere.
* No parked cars on a street that in reality is parked solid on both sides, and no people.
* The roadway has no markings and no texture.
* Props were capped by the triangle budget at 400 placed.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| a lamp column and a wall inside 5 m of the lens | the clearance rule tests the view azimuth and a 12 deg cone, not the whole frame; a camera snapped to the nearest roadbed can end up beside a wall | camera |
| the photograph is of the right boulevard 3.9 km away | Commons has very few free photographs looking along the Grand Concourse and none this item's rules admit near East 165th Street | reference |
| no Art Deco detail | shells are extruded footprints with a per-material colour; the facade kit has no Art Deco vocabulary | geometry |
| no signage or shopfront glass | no stage produces signage; kit storefronts carry no glazing | material |
| no parked cars, no people | no traffic or crowd placement feeds the verification scene | data |
| featureless roadway | flat colour per pavement kind, no texture, no markings | material |
