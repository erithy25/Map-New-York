# Bronx drive-through: Grand Concourse Art Deco apartments

`drive_bronx_grand_concourse` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Lowes Paradise Theater, The Bronx.jpg by Paul Lowry, CC BY 2.0 (https://creativecommons.org/licenses/by/2.0), taken 2025-04-29 19:05:26, 1920x1171. [Commons page](https://commons.wikimedia.org/wiki/File:Lowes_Paradise_Theater,_The_Bronx.jpg)

**Camera** — camera 40.83200, -73.91860 (NYC_TM 2644, 14663) z 31.6 m NAVD88 | azimuth 25.0deg pitch +0.0deg | 35 mm on 36 mm (54.4deg horizontal) | 1280x780. View direction: 25.0 deg as recorded in meta.json.  This item names no subject and the reference photograph's own view direction was not derived from the image (confidence: medium), so the two halves of this sheet are not guaranteed to face the same way -- compare them on street width, storey height and material, not on composition. Aim: level optical axis (the reference names no subject to aim at).

**Sun** — azimuth 283.3°, elevation 7.4° at 2025-04-29T19:05:26-04:00 (EXIF DateTimeOriginal).

**In frame** — 6/6 building tiles (293,580 tris), 2 landmark models, 2,433 pavement polygons, 400 props, 6,596 facade-kit pieces; 3,667,273 triangles; ground mesh 211² at 2.0 m near / 40.0 m far.

**Camera clearance** — the recorded viewpoint is inside t_2_14_roof_membrane (a ray straight up from the eye point hits its roof); the camera was moved 5 m onto the nearest real roadbed polygon in data/processed/roads/pavement, keeping the same eye height above the heightmap.  The view azimuth is clear for 60 m from there

**Verdict — a plausible evening Bronx street with real street trees and real sheds, framed badly — a lamp column and a building wall five metres from the lens fill the right half — and paired with a photograph of a theatre marquee it has no way to match**

## What matches

* The photograph's own EXIF GPS was correctly rejected: it is 3,604 m from the item's viewpoint, so the item's recorded position was used and the sheet says so. This is the largest GPS disagreement in the whole set and the sanity gate caught it.
* The camera was corrected out of a building: the recorded viewpoint sits inside t_2_14_roof_membrane and was snapped 5 m onto the nearest real roadbed polygon, with 60 m of clear view along the azimuth from there.
* The street trees are correct for late April: full canopies, right heights, planted at the kerb, with 16 opaque impostor cards dropped.
* The street section is right for the Grand Concourse's side streets: roadbed, both sidewalks, kerb reveal, and 2,433 pavement polygons including 601 crosswalk and 88 parking-lot polygons.
* Sidewalk sheds with green netting run along the west frontage, and the building masses behind them are the right height for the Concourse's six-storey Art Deco apartment blocks.
* The Sun is from the photograph's own EXIF instant (2025-04-29 19:05:26 EDT, elevation 7.4 deg) and the long low evening light and deep shadow in the street are what that elevation gives.

## What does not match

* The composition is spoiled by proximity. A street-lamp column stands about 2 m from the lens and a building wall about 5 m to the right, so half the frame is a featureless plane. The clearance rule checks the view azimuth, not the whole cone, so a camera can be accepted with a wall beside it.
* The frames are of different things: the item looks north up the Concourse, the photograph is a tight study of the Loew's Paradise Theatre marquee. The item names no subject and the photograph's direction was assumed.
* Nothing in the render is Art Deco. The blocks are plain masses with no string courses, no polychrome brick, no corner windows, no rounded balconies and no cornice — the features the item exists to test.
* No signage, no shopfront glass, no lettering, no marquee anywhere.
* No parked cars on a street that in reality is parked solid on both sides, and no people.
* The roadway has no markings and no texture.
* Props were capped by the triangle budget at 400 placed.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| a lamp column and a wall inside 5 m of the lens | the clearance rule tests the view azimuth and a 12 deg cone, not the whole frame; a camera snapped to the nearest roadbed can end up beside a wall | camera |
| the two halves are of different subjects | the item names no subject and the reference stage assigned it the item's own azimuth | reference |
| no Art Deco detail | shells are extruded footprints with a per-material colour; the facade kit has no Art Deco vocabulary | geometry |
| no signage or shopfront glass | no stage produces signage; kit storefronts carry no glazing | material |
| no parked cars, no people | no traffic or crowd placement feeds the verification scene | data |
| featureless roadway | flat colour per pavement kind, no texture, no markings | material |
