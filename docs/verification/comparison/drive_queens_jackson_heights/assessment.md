# Queens residential block: Jackson Heights side street with two-family homes

`drive_queens_jackson_heights` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:78-12 35th Avenue (entrance), between 78th and 79th Street, Jackson Heights, Queens, New York.jpg by Deans Charbal, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2022-09-11 11:57:15, 1920x1440. [Commons page](https://commons.wikimedia.org/wiki/File:78-12_35th_Avenue_(entrance),_between_78th_and_79th_Street,_Jackson_Heights,_Queens,_New_York.jpg)

**Camera** — camera 40.75200, -73.88300 (NYC_TM 5677, 5783) z 20.3 m NAVD88 | azimuth 165.0deg pitch +0.0deg | 35 mm on 36 mm (54.4deg horizontal) | 1208x906. View direction: 165.0 deg as recorded in meta.json.  This item names no subject and the reference photograph's own view direction was not derived from the image (confidence: medium), so the two halves of this sheet are not guaranteed to face the same way -- compare them on street width, storey height and material, not on composition. Aim: level optical axis (the reference names no subject to aim at).

**Sun** — azimuth 157.6°, elevation 51.6° at 2022-09-11T11:57:15-04:00 (EXIF DateTimeOriginal).

**In frame** — 6/6 building tiles (469,002 tris), 0 landmark models, 2,099 pavement polygons, 314 props, 6,514 facade-kit pieces; 3,720,621 triangles; ground mesh 211² at 2.0 m near / 40.0 m far.

**Camera clearance** — the recorded viewpoint is hard against prop_lamp_cobra_davit_1 (0.25 m from the lens in the view cone); the camera was moved 19 m onto the nearest real sidewalk polygon in data/processed/roads/pavement, keeping the same eye height above the heightmap.  The view azimuth is clear for 28 m from there

**Verdict — the closest material match in the drive-through set — red brick garden-apartment blocks with window air-conditioners under mature street trees, which is exactly what Jackson Heights is — undone by having no windows, no planting and no ground detail**

## Re-rendered 2026-09-07 — the crowd frame that works, and the first vehicle cull

This is the strongest evidence in the set that the pedestrian simulation produces a plausible
street. 288 people are placed and they are *distributed*: two in the near foreground on the
crosswalk, a group on the left pavement at 20-40 m, more on the right, a scatter thinning into the
distance down a tree-lined block. Nobody is standing on the lens and nobody is clumped. 76 vehicles,
173 street trees, 50 lamps, 60 manholes, five bus-stop signs.

**The vehicle cull fired here for the first time**: `culled_after_camera_move` reports
`vehicle_over_the_observer: 1`. A car was inside the 6 m vehicle clearance of the *final* camera
position and outside it from the scene centre the placement measured against — the same fault the
pedestrian side showed on Grand Concourse, on the other agent class. The agents lane's own note
records that the first agent render was "the inside of a black van"; this is that failure mode
recurring through a different route and being caught.

The drop record is worth reading beside the 288: **988 pedestrians outside the radius, 367 cut by the
triangle budget, 312 on no walkable surface and 91 standing in the carriageway while not crossing**.
The crowd in the frame is roughly a sixth of what the simulation had within reach.

**The buildings are the weak half, and it is the facade-class case again** — 4,003 window pieces
rendering as thin dark dashes on flat red-brown planes, against Jackson Heights' real brick with deep
reveals, sills and casements. Recorded on the Bed-Stuy sheet and qualified on the Wall Street one,
where the same kit produces real recessed openings.

## What matches

* The camera correction fired on the new in-the-lens test: the recorded viewpoint stands 0.25 m from a cobra-head lamp standard, and the camera was moved 19 m onto the nearest real sidewalk polygon with 28 m of clear view.
* The photograph's own EXIF GPS was rejected as mis-tagged at 419 m; the item's viewpoint was used and the sheet says so.
* The building material is right: a continuous run of red-brown brick garden-apartment blocks at five or six storeys with flat roofs and parapets, which is the Jackson Heights historic-district vocabulary and matches the reference's own block.
* Window air-conditioner units project from the facade at the right rhythm and the right height — a small detail that is genuinely characteristic and genuinely present.
* The street trees are mature and in full September leaf with correct canopies and trunks; 20 impostor cards were dropped.
* 2,099 pavement polygons place the roadway, both sidewalks, 475 crosswalk and 30 parking-lot polygons at the right widths, and a manhole cover sits proud in the roadway.

## What does not match

* There is not one window opening on the near block face. The wall is a flat brick-coloured plane with air-conditioners and string courses on it but no fenestration at all, where the reference's block face is 40 % window by area.
* No entrance. The reference's subject is a stone-framed doorway with a moulded architrave and a glazed door; the render's ground floor is blank.
* No planting. Jackson Heights garden apartments are named for their planted forecourts; the reference foreground is entirely hydrangea, hosta and a brick path, and the render has bare grey ground up to the wall.
* ~~No cars, no people, no rubbish bins.~~ — **partly superseded 2026-09-07.** The people and vehicles are placed now; the rest of this bullet — traffic signals, street signs, wayfinding kiosks and the like — is **still true**, and those are street furniture rather than agents.
* The roadway and sidewalks are flat untextured planes with no markings and no joint pattern.
* The pairing is again unrelated in direction: the item looks south along 84th Street, the photograph is a courtyard entrance study.
* Props were capped by the triangle budget at 314 placed.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| no windows on the near facade | the facade kit placed 6,514 pieces but this facade class carries no window piece on the visible run; the kit's residential vocabulary is the thinnest part of it | geometry |
| no entrance or door surround | the kit has a door_entry piece but none was placed on this frontage | geometry |
| no planting or forecourt | no dataset the scene reads carries residential planting | data |
| ~~no cars, people or bins~~ superseded | agents are placed now (288 people, 76 vehicles); what remains is framing and occlusion, not absence | reporting |
| untextured ground | flat colour per pavement kind, no texture, no markings | material |
| the two halves face different ways | the item names no subject and the reference stage assigned it the item's own azimuth | reference |
