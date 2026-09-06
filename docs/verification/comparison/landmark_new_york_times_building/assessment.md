# The New York Times Building (620 Eighth Avenue)

`landmark_new_york_times_building` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:2024-06-17 10 01 23 The front of the New York Times Building along 8th Avenue in Manhattan, New York City, New York.jpg by Famartin, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2024-06-17 10:01:23, 1920x1440. [Commons page](https://commons.wikimedia.org/wiki/File:2024-06-17_10_01_23_The_front_of_the_New_York_Times_Building_along_8th_Avenue_in_Manhattan,_New_York_City,_New_York.jpg)

**Camera** — camera 40.75632, -73.99057 (NYC_TM -3426, 6255) z 14.3 m NAVD88 | azimuth 115.5deg pitch +3.9deg | 35 mm on 36 mm (54.4deg horizontal) | 1208x906. View direction: 115.5 deg, the bearing from this photograph's own GPS position to The New York Times Building (620 Eighth Avenue); heading and position both come from the photograph.  The item's recorded azimuth is 70.0 deg, 45.5 deg away, and belongs to its nominal viewpoint. Aim: aimed at The New York Times Building (620 Eighth Avenue) 53 m away, at its mid-height (a nominal 10 m subject); +3.9 deg from horizontal.

**Sun** — azimuth 101.6°, elevation 49.5° at 2024-06-17T10:01:23-04:00 (EXIF DateTimeOriginal).

**In frame** — 4/4 building tiles (188,464 tris), 2 landmark models, 1,402 pavement polygons, 340 props, 7,659 facade-kit pieces; 2,476,653 triangles; ground mesh 199² at 2.0 m near / 40.0 m far.

**Verdict — raised from a uniform dark grey (sd 0.007) to a legible one (sd 0.125) and still almost empty: the camera stands against the tower's own base and the frame is a flat wall, a sidewalk and a fire hydrant**

## What matches

* The camera correction fired: the recorded viewpoint stood 0.2 m from a building footprint, and the clearance rule moved it onto a pavement polygon with 150 m of clear azimuth. The orchestrator's sweep had this frame at mean 0.035, sd 0.007 — near-uniform dark grey.
* The eye height and ground are correctly measured from the 2 m heightmap, and the sheet states both.
* The hydrant, the kerb line and the sidewalk reveal are correctly placed and sized, and 2,397 pavement polygons carry the Eighth Avenue geometry.
* 4 landmark models are in range with their shells suppressed.

## What does not match

* The New York Times Building is not identifiable. Its ceramic-rod screen, the mast, the setback and the glazed base — the whole subject — are not visible; the top half of the frame is one flat plane of its wall seen from a few metres away.
* There is no texture, no glazing, no rod screen and no reflectance on that wall, so it reads as painted card.
* The frame remains close to featureless: standard deviation 0.125 is above the 0.025 floor only because the sidewalk and the sky-lit upper wall differ in tone.
* No people, no vehicles, no signage, no entrance.
* The reference's whole content has no counterpart.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the tower is not identifiable | the camera is a few metres from its base and a level axis at this distance sees only wall | camera |
| no rod screen, glazing or texture | the landmark model carries the massing only, with a flat base colour | material |
| no people, vehicles or signage | no stage places any of them | data |
