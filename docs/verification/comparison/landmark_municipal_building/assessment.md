# Manhattan Municipal Building

`landmark_municipal_building` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Manhattan Municipal Building April 2022 003.jpg by Kidfly182, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2022-04-16 14:06:42, 1920x1440. [Commons page](https://commons.wikimedia.org/wiki/File:Manhattan_Municipal_Building_April_2022_003.jpg)

**Camera** — camera 40.71271, -74.00479 (NYC_TM -4630, 1413) z 13.4 m NAVD88 | azimuth 81.6deg pitch +0.0deg | 18 mm on 36 mm (90.0deg horizontal) | 1208x906. View direction: 81.6 deg, the bearing from this photograph's own GPS position to Manhattan Municipal Building; heading and position both come from the photograph.  The item's recorded azimuth is 131.3 deg, 49.7 deg away, and belongs to its nominal viewpoint. Aim: level optical axis (Manhattan Municipal Building is 68 m away and would need +52 deg of tilt; a real frame would use a wider lens instead, and a tilted axis would stop the render being comparable on proportion).

**Sun** — azimuth 212.2°, elevation 55.8° at 2022-04-16T14:06:42-04:00 (EXIF DateTimeOriginal).

**In frame** — 3/3 building tiles (69,562 tris), 5 landmark models, 1,542 pavement polygons, 692 props, 1,358 facade-kit pieces; 2,372,629 triangles; ground mesh 201² at 2.0 m near / 40.0 m far.

**Verdict — the Municipal Building's Corinthian screen and its tower shaft are both modelled and in frame, and everything above the 25th floor — the tiered temple, the colonnaded drum and Civic Fame on top — is cut off by the 18 mm floor**

## What matches

* The building is identifiable: the free-standing Corinthian colonnade at the base with its correct column spacing and entablature, the rusticated podium behind it, and the tower shaft rising with a regular window grid at the published 177 m height.
* The camera stands on the photograph's own EXIF GPS, 167 m from the item's nominal viewpoint, and the heading (81.6 deg) is the bearing from there to the building — 49.7 deg from the recorded azimuth, which was discarded.
* The lens rule widened 35 mm to the 18 mm floor and states the limit: 175 m of building above the lens at 68 m, 69 deg above the horizon, so the top is still cut off.
* The surrounding fabric is right: the Woolworth-era block to the left, the low-rise to the right, cobra-head and bishop's-crook lamps, a Citi Bike at a dock on the sidewalk, and 1,542 pavement polygons with the crossing geometry.

## What does not match

* The top of the building is missing, and with it the whole reason the item exists: the tiered setbacks, the ten-column temple, the drum and the gilded Civic Fame statue. The reference is almost entirely those.
* The stone has no surface — one flat pale colour where the reference is a limestone facade with deep window reveals, string courses, and a hundred years of weathering.
* No glazing anywhere; the windows are dark rectangles.
* No people, no vehicles, no traffic signals, no flag.
* The lower half of the frame is bare untextured paving.
* Props were capped by the triangle budget at 692 placed.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the top of the building is out of frame | a 177 m subject 68 m away needs 69 deg of vertical angle; the 18 mm floor gives 74 deg on the long side but the frame is landscape | camera |
| no stone surface or reveals | landmark models carry a flat base colour per material with no texture | material |
| no glazing | neither the model nor the kit supplies glass | material |
| no people, vehicles or signals | no stage places any of them | data |
| bare paving | pavement polygons carry a kind but no texture | material |
