# Empire State Building

`landmark_empire_state_building` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Empire State Building August 2021 007.jpg by Kidfly182, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2021-08-19 11:47:25, 1920x1440. [Commons page](https://commons.wikimedia.org/wiki/File:Empire_State_Building_August_2021_007.jpg)

**Camera** — camera 40.74600, -73.98760 (NYC_TM -3254, 5155) z 15.3 m NAVD88 | azimuth 31.1deg pitch +0.0deg | 18 mm on 36 mm (90.0deg horizontal) | 1208x906. View direction: 31.1 deg as recorded; it agrees with the bearing from the camera position used to Empire State Building (31.2 deg) to 0.1 deg. Aim: level optical axis (the subject is 317 m away; anything that far is photographed with a level camera).

**Sun** — azimuth 145.6°, elevation 57.7° at 2021-08-19T11:47:25-04:00 (EXIF DateTimeOriginal).

**In frame** — 7/7 building tiles (293,440 tris), 5 landmark models, 3,543 pavement polygons, 447 props, 11,344 facade-kit pieces; 4,500,081 triangles; ground mesh 221² at 2.0 m near / 40.0 m far.

**Camera clearance** — the recorded viewpoint is boxed in: the view azimuth is closed off 51 m ahead, less than the 80 m this frame needs to show its subject; the camera was moved 90 m onto the nearest real roadbed polygon in data/processed/roads/pavement, keeping the same eye height above the heightmap.  The view azimuth is clear for 96 m from there

**Verdict — the correction that saved the frame from blackness also walked it 90 m up the street, and the Empire State Building is in neither version: the sheet is a Midtown block face against a photograph of 443 m of limestone**

## What matches

* The photograph's own EXIF GPS was rejected as mis-tagged at 357 m and the item's viewpoint used.
* The heading is right: 31.1 deg as recorded, agreeing to 0.1 deg with the bearing from the camera to the tower.
* The lens rule fired and is stated: 35 mm widened to the 18 mm floor because the model's published 443 m height stands 443 m above the lens at 317 m, 54 deg above the horizon, and even 18 mm cuts the top off.
* The camera correction is fully documented: the recorded viewpoint had the view closed off 51 m ahead against the 80 m this subject needs, so the camera was moved 90 m onto the nearest roadbed with 96 m of clear view.
* What the frame shows is a correct Midtown street: red-brick and limestone block faces at the right heights, sidewalk sheds with green netting and lit soffits, a LinkNYC kiosk, cobra-head lamps, street trees, and 3,543 pavement polygons with the kerb reading across the frame.

## What does not match

* The Empire State Building is not in the frame at all, which makes this sheet unusable for the purpose it exists for. The recorded viewpoint has no line of sight to it, and the clearance rule's test — 80 m of clear azimuth — is satisfied by a spot that still has a block between the camera and the tower.
* The 90 m displacement is itself a significant caveat: the render is not taken from the viewpoint the item records, and the sheet says so.
* The reference is a single tower filling the frame in a tight upward perspective with 86 storeys of limestone piers and steel spandrels. There is nothing in the render at that scale to compare it with.
* No facade in the render has glazing, texture or mouldings.
* No people, no vehicles, no signage.
* The facade kit was capped by the triangle budget at 11,344 of 14,550 records in range.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the tower is not in the frame | the recorded viewpoint has no line of sight to the subject, and the clearance test measures free distance along the azimuth rather than visibility of the subject itself | camera |
| camera 90 m from the recorded viewpoint | the search takes the nearest point that satisfies the clear-view test; in a dense block that can be far | camera |
| no glazing, texture or mouldings | shells carry a per-material base colour; the kit supplies openings without glass | material |
| no people, vehicles or signage | no stage places any of them | data |
| a fifth of the facade kit not drawn | the 4.5 M triangle budget is spent before the kit finishes | geometry |
