# New York Public Library (Stephen A. Schwarzman Building)

`landmark_nypl` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:New York Public Library - Main Branch (51396225599).jpg by ajay_suresh, CC BY 2.0 (https://creativecommons.org/licenses/by/2.0), taken 2021-08-21 15:52, 1920x1080. [Commons page](https://commons.wikimedia.org/wiki/File:New_York_Public_Library_-_Main_Branch_(51396225599).jpg)

**Camera** — camera 40.75335, -73.98085 (NYC_TM -2605, 5925) z 23.4 m NAVD88 | azimuth 261.7deg pitch +0.0deg | 27 mm on 36 mm (67.1deg horizontal) | 1280x720. View direction: 261.7 deg, the bearing from this photograph's own GPS position to New York Public Library main entrance; heading and position both come from the photograph.  The item's recorded azimuth is 292.4 deg, 30.7 deg away, and belongs to its nominal viewpoint. Aim: level optical axis (New York Public Library main entrance is 115 m away and would need +9 deg of tilt; a real frame would use a wider lens instead, and a tilted axis would stop the render being comparable on proportion).

**Sun** — azimuth 245.2°, elevation 42.4° at 2021-08-21T15:52:00-04:00 (EXIF DateTimeOriginal (minutes)).

**In frame** — 4/4 building tiles (188,464 tris), 7 landmark models, 1,567 pavement polygons, 389 props, 13,608 facade-kit pieces; 4,500,010 triangles; ground mesh 203² at 2.0 m near / 40.0 m far.

**Verdict — raised from black (0.021) to legible (0.235) by the camera corrections, and the library is still not in the frame: the photograph's own GPS puts the camera 75 m up Fifth Avenue with a block between it and the portico**

## What matches

* The camera stands on the photograph's own EXIF GPS, 75 m from the item's nominal viewpoint, and the heading (261.7 deg) is the bearing from that same point to the library's main entrance — heading and position from one measurement. The item's recorded azimuth is 30.7 deg away and was discarded.
* The lens rule fired precisely rather than at its floor: 35 mm widened to 27 mm so a level axis contains a 38 m subject 115 m away, 18 deg above the horizon.
* The library model is placed 118.7 m away with 30 landmark BINs and 4,060 faces of duplicate shell suppressed, and 725 kit placements belonging to those buildings suppressed with them — the first frame in the set where that machinery is visibly exercised.
* The block face that is in frame is correct in kind: a limestone office building with a regular window grid, a projecting cornice and a scaffold bay, at the right height for East 41st Street.
* 1,567 pavement polygons, 389 props and 13,608 kit pieces are placed.

## What does not match

* The New York Public Library is not in the frame. The item exists to test the Fifth Avenue portico, the lions and the terrace, and the render shows the block on the north side of 42nd Street instead.
* The frame is in full shadow at mean 0.235 where the reference is a bright August afternoon on a south-facing facade.
* The reference's content — the six Corinthian columns, the pediment sculpture, the carved frieze, Patience and Fortitude on their plinths, the banners, the traffic signals, the Fifth Ave street sign, the bus and about sixty people — has no counterpart.
* The wall that is in frame has no stone texture and no glazing.
* No people, no vehicles, no signage.
* The facade kit was capped by the triangle budget at 13,608 of 15,783 records in range.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the library is not in the frame | the photograph's own GPS is 75 m from the item's viewpoint and has a block in the way; position and heading are consistent but the sightline is not | reference |
| frame in shadow | a Midtown side street at a 42 deg Sun with the tall side to the south | lighting |
| no portico, lions, banners or people | the subject is out of frame, and no crowd or signage placement feeds the scene | data |
| no stone texture or glazing | shells carry a per-material base colour; the kit supplies openings without glass | material |
