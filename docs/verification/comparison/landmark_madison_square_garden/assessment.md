# Madison Square Garden

`landmark_madison_square_garden` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Madison Square Garden 112.jpg by Zakarie Faibis, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2018-08-06 17:20:06, 1920x1440. [Commons page](https://commons.wikimedia.org/wiki/File:Madison_Square_Garden_112.jpg)

**Camera** — camera 40.75027, -73.99148 (NYC_TM -3491, 5607) z 13.2 m NAVD88 | azimuth 278.9deg pitch +6.2deg | 35 mm on 36 mm (54.4deg horizontal) | 1208x906. View direction: 278.9 deg, the bearing from this photograph's own GPS position to Madison Square Garden; heading and position both come from the photograph.  The item's recorded azimuth is 299.1 deg, 20.2 deg away, and belongs to its nominal viewpoint. Aim: aimed at Madison Square Garden 164 m away, at its mid-height (the madison_square_garden model's 44 m height); +6.2 deg from horizontal.

**Sun** — azimuth 266.5°, elevation 29.9° at 2018-08-06T17:20:06-04:00 (EXIF DateTimeOriginal).

**In frame** — 7/7 building tiles (266,748 tris), 4 landmark models, 1,901 pavement polygons, 342 props, 5,435 facade-kit pieces; 2,644,070 triangles; ground mesh 207² at 2.0 m near / 40.0 m far.

**Camera clearance** — the recorded viewpoint is boxed in: the view azimuth is closed off 62 m ahead, less than the 80 m this frame needs to show its subject; the camera was moved 25 m onto the nearest real sidewalk polygon in data/processed/roads/pavement, keeping the same eye height above the heightmap.  The view azimuth is clear for 96 m from there

**Verdict — the arena drum is right — the correct cylinder at the correct diameter and height on the correct block, with the Farley block beside it — and it is a blank dark drum where the reference is a wall of illuminated signage and a lit entrance canopy**

## What matches

* Madison Square Garden reads correctly as a drum: a cylinder of the right diameter and 44 m height sitting on a rectangular podium at the right place on Seventh Avenue, with the vertical rib pattern of its cladding.
* The camera stands on the photograph's own EXIF GPS, 64 m from the item's nominal viewpoint, and the heading (278.9 deg) is the bearing from there to the arena — 20.2 deg from the recorded azimuth, which was discarded.
* The boxed-in test fired and is stated: the view azimuth was closed off 62 m ahead against the 80 m this subject needs, so the camera was moved 25 m onto the nearest real sidewalk polygon with 96 m of clear view.
* The aim rule tilted +6.2 deg to centre the drum at its mid-height, inside the 8 deg limit.
* Street furniture is placed and correct: cobra-head lamps on davits with lit heads, a fire hydrant at the kerb at the right size and colour, manhole covers proud of the roadway, and 1,901 pavement polygons carrying the crossing geometry.

## What does not match

* No signage of any kind. The reference is dominated by 'MADISON SQUARE GARDEN' in illuminated letters along the canopy fascia, the MSG Networks sign, and a full-height advertising wall — perhaps half the frame by area. The render's drum is blank.
* No entrance canopy, no lit soffit, no marquee, no doors: the arena meets the sidewalk as a plain wall.
* The block to the left is a flat pale plane where the reference is a 1920s brick-and-terracotta office building with several hundred windows.
* No people, no vehicles, no traffic signals.
* The sidewalk and roadway are flat untextured planes.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| no signage, canopy or marquee | no stage produces sign geometry, and the madison_square_garden model stops at the drum and podium | geometry |
| blank neighbouring block | shells carry a per-material base colour and the kit did not reach this frontage | material |
| no people, vehicles or signals | no stage places any of them | data |
| untextured ground | pavement polygons carry a kind but no texture or markings | material |
