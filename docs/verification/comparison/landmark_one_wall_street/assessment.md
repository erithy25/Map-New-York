# One Wall Street (Irving Trust Building)

`landmark_one_wall_street` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Buildings in FiDi, Manhattan.jpg by Emperor of Emperors, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2026-02-27 15:49:02, 1920x2560. [Commons page](https://commons.wikimedia.org/wiki/File:Buildings_in_FiDi,_Manhattan.jpg)

**Camera** — camera 40.70679, -74.01239 (NYC_TM -5283, 764) z 11.3 m NAVD88 | azimuth 52.0deg pitch +0.0deg | 18 mm on 36 mm (73.7deg horizontal, 90.0deg vertical, portrait) | 904x1206. View direction: 52.0 deg, the bearing from this photograph's own GPS position to One Wall Street (Irving Trust Building); heading and position both come from the photograph.  The item's recorded azimuth is 75.0 deg, 23.0 deg away, and belongs to its nominal viewpoint. Aim: level optical axis (One Wall Street (Irving Trust Building) is 78 m away and would need +51 deg of tilt; a real frame would use a wider lens instead, and a tilted axis would stop the render being comparable on proportion).

**Sun** — azimuth 239.6°, elevation 19.8° at 2026-02-27T15:49:02-05:00 (EXIF DateTimeOriginal).

**In frame** — 4/4 building tiles (82,358 tris), 10 landmark models, 1,771 pavement polygons, 651 props, 11,607 facade-kit pieces; 4,500,562 triangles; ground mesh 201² at 2.0 m near / 40.0 m far.

**Camera clearance** — the recorded viewpoint is boxed in: the view azimuth is closed off 25 m ahead, less than the 39 m this frame needs to show its subject; the camera was moved 13 m onto the nearest real sidewalk polygon in data/processed/roads/pavement, keeping the same eye height above the heightmap.  The view azimuth is clear for 60 m from there

**Verdict — the fluted, faceted flank of One Wall Street is genuinely modelled — the vertical pier-and-recess rhythm that makes the building famous is there — and the canyon around it is in shadow with nothing else in it**

## What matches

* One Wall Street's defining facade treatment is present: the continuous vertical piers and deep recesses running the full height, with the faceted, slightly curved wall plane between them. It is the only building in the set whose surface modulation is modelled rather than painted on.
* The canyon is right: Wall Street's narrow roadbed, the sidewalk widths, the kerb line, and the way the towers close overhead.
* A sidewalk shed with green netting runs along the left frontage at the right height, and a bishop's-crook lamp head is visible at the right.
* 1,686 pavement polygons and 649 props are placed, and the clearance report gives 60 m of clear azimuth against the 39 m needed.
* 9 landmark models are in range with their shells suppressed.

## What does not match

* The building's top — the setbacks and the crown that the reference photographs — is out of frame; a level axis at this distance sees only the shaft.
* Mean luminance 0.222: the whole street floor is in shadow.
* The limestone has no texture and the windows have no glass, so the piers read as extruded plastic rather than stone.
* Nothing else is in the frame: no people, no vehicles, no signage, no traffic signals, no entrance.
* The lower 40 % is bare untextured paving and roadbed with no markings.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the crown is out of frame | a level axis at street level in a narrow canyon cannot contain a 200 m tower | camera |
| frame in shadow | a narrow Financial District canyon with two light bounces | lighting |
| no stone texture or glazing | shells carry a per-material base colour; the kit supplies openings without glass | material |
| no people, vehicles or signage | no stage places any of them | data |
| bare paving | pavement polygons carry a kind but no texture or markings | material |
