# Chrysler Building

`landmark_chrysler_building` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Chrysler Building October 2022 001.jpg by Kidfly182, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2022-10-08 14:36:16, 1920x1440. [Commons page](https://commons.wikimedia.org/wiki/File:Chrysler_Building_October_2022_001.jpg)

**Camera** — camera 40.75000, -73.97670 (NYC_TM -2274, 5564) z 16.5 m NAVD88 | azimuth 29.6deg pitch +0.0deg | 18 mm on 36 mm (90.0deg horizontal) | 1208x906. View direction: 29.6 deg as recorded; it agrees with the bearing from the camera position used to Chrysler Building (29.7 deg) to 0.1 deg. Aim: level optical axis (Chrysler Building is 205 m away and would need +37 deg of tilt; a real frame would use a wider lens instead, and a tilted axis would stop the render being comparable on proportion).

**Sun** — azimuth 215.8°, elevation 36.5° at 2022-10-08T14:36:16-04:00 (EXIF DateTimeOriginal).

**In frame** — 4/4 building tiles (148,546 tris), 6 landmark models, 1,591 pavement polygons, 540 props, 12,474 facade-kit pieces; 4,500,209 triangles; ground mesh 201² at 2.0 m near / 40.0 m far.

**Camera clearance** — the recorded viewpoint is boxed in: the view azimuth is closed off 13 m ahead, less than the 36 m this frame needs to show its subject; the camera was moved 21 m onto the nearest real roadbed polygon in data/processed/roads/pavement, keeping the same eye height above the heightmap.  The view azimuth is clear for 60 m from there

**Verdict — rescued from a black frame to a legible one — the boxed-in test moved the camera off a wall 13 m ahead and the lens rule opened to 18 mm — and the Chrysler Building is still not in it, because from a Lexington Avenue sidewalk the tower is behind the block in front of you**

## What matches

* The camera correction is the story of this sheet and it is fully stated: the recorded viewpoint had the view closed off 13 m ahead against the 36 m this subject needs, so the camera was moved 21 m onto the nearest real roadbed polygon with 60 m of clear view. Before that the frame was mean 0.096, effectively black.
* The lens rule fired too: 35 mm widened to the 18 mm floor because the 319 m tower stands 312 m above the lens at 205 m, 57 deg above the horizon.
* What the frame does show is a correct Midtown canyon: Lexington Avenue's roadbed and sidewalk widths, the setback towers stepping away, a kerb line with the right reveal, and aerial perspective washing the far end out at the right rate.
* The street furniture is right and well modelled: a LinkNYC kiosk with its lit screen at the correct 2.9 m height, a bus shelter, planters with hedging, street trees in full October leaf, a hydrant, cobra-head lamps on davits.
* There are road markings — white directional arrows and lane markings on the roadbed — the only frame in the set that shows any.
* 1,591 pavement polygons and 540 props are placed, with 15 opaque impostor cards dropped.

## What does not match

* The Chrysler Building is not in the frame. The item exists to test its stainless-steel crown and the render shows the street it stands on. From a sidewalk 205 m away on a canyon street the tower is behind the block in front of the camera, and no lens choice can recover it — only a different viewpoint can.
* The frame is still dark, mean 0.222, because Lexington Avenue at 40th at a 36 deg October Sun is in shadow at street level.
* No building has any surface: the near walls are flat grey-blue and pale planes with unglazed openings, where the reference's own foreground buildings carry limestone, deep reveals and bronze spandrels.
* No people, no vehicles, no traffic signals, no signage.
* The reference is a dramatic upward view of the crown against a deep blue sky with the eagle gargoyles and the sunburst spire; there is no counterpart to any of it.
* Both props and kit were capped by the triangle budget (12,474 of 16,473 kit records in range).

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the tower is not in the frame | the recorded viewpoint is on a canyon sidewalk 205 m from the subject with a block in between; the item needs a viewpoint with a line of sight | reference |
| frame still dark | a Midtown canyon at a 36 deg Sun with two light bounces | lighting |
| no surface on any building | shells carry a per-material base colour; the kit supplies openings without glazing | material |
| no people, vehicles, signals or signage | no stage places any of them | data |
| a quarter of the facade kit not drawn | the 4.5 M triangle budget is spent before the kit finishes | geometry |
