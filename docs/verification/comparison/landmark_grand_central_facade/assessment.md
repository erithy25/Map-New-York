# Grand Central Terminal facade

`landmark_grand_central_facade` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Grand Central Terminal December 2022 004.jpg by Kidfly182, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2022-12-12 11:51:16, 1920x1440. [Commons page](https://commons.wikimedia.org/wiki/File:Grand_Central_Terminal_December_2022_004.jpg)

**Camera** — camera 40.75212, -73.97778 (NYC_TM -2346, 5788) z 18.1 m NAVD88 | azimuth 67.6deg pitch +0.0deg | 18 mm on 36 mm (90.0deg horizontal) | 1208x906. View direction: 67.6 deg, the bearing from this photograph's own GPS position to Grand Central Terminal 42nd Street facade; heading and position both come from the photograph.  The item's recorded azimuth is 30.5 deg, 37.1 deg away, and belongs to its nominal viewpoint. Aim: level optical axis (Grand Central Terminal 42nd Street facade is 53 m away and would need +21 deg of tilt; a real frame would use a wider lens instead, and a tilted axis would stop the render being comparable on proportion).

**Sun** — azimuth 180.4°, elevation 26.2° at 2022-12-12T11:51:16-05:00 (EXIF DateTimeOriginal).

**In frame** — 4/4 building tiles (148,546 tris), 5 landmark models, 1,337 pavement polygons, 509 props, 11,324 facade-kit pieces; 4,012,649 triangles; ground mesh 199² at 2.0 m near / 40.0 m far.

**Verdict — the terminal's colonnade and cornice are in the frame, unlit and cropped, with two thirds of the picture given to bare roadway; the sculptural group, the clock, the arched windows and the lettering that make the facade what it is are all absent**

## What matches

* The 42nd Street facade is modelled and identifiable: engaged columns with capitals, the entablature and cornice above them, and the wall stepping back to the viaduct — the right composition at the right 46 m height.
* The camera stands on the photograph's own EXIF GPS, 80 m from the item's nominal viewpoint, and the heading (67.6 deg) is the bearing from there to the facade; the item's recorded azimuth is 37.1 deg away and was discarded.
* The lens rule widened 35 mm to the 18 mm floor and states that even so the top is cut off: the facade stands 44 m above the lens at 53 m, 39 deg above the horizon.
* Bishop's-crook lamps line the viaduct at the right spacing, a manhole cover sits proud in the roadway, and 1,337 pavement polygons carry the Pershing Square geometry.

## What does not match

* The whole subject of the reference is missing: the Mercury, Hercules and Minerva sculptural group, the Tiffany clock, the three great arched windows with their steel tracery, and the carved 'GRAND CENTRAL TERMINAL' lettering.
* The stone has no surface: one flat dark grey where the reference is warm Stony Creek granite and Bedford limestone with deep carving and strong tonal range.
* Mean luminance 0.232 with the facade in full shadow: the Sun is at 26 deg in December and the terminal faces south, so the render is dark where the photograph is bright.
* Two thirds of the frame is bare roadway and viaduct deck with no texture and no markings.
* No people, no vehicles, no taxis on the viaduct, no Christmas wreath, no signage.
* The facade kit was capped by the triangle budget at 11,324 pieces.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| no sculpture, clock, tracery or lettering | the grand_central_terminal landmark model carries the massing and the colonnade only | geometry |
| no stone surface | landmark models carry a flat base colour per material with no texture | material |
| facade in shadow, frame dark | a south-facing facade at a 26 deg December Sun in a canyon | lighting |
| bare roadway | pavement polygons carry a kind but no texture or markings | material |
| no people, vehicles or signage | no stage places any of them | data |
