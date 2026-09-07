# St. Patrick's Cathedral

`landmark_st_patricks_cathedral` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:St Patrick’s Cathedral August 2021 001.jpg by Kidfly182, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2021-08-21 12:42:57, 1920x2560. [Commons page](https://commons.wikimedia.org/wiki/File:St_Patrick%E2%80%99s_Cathedral_August_2021_001.jpg)

**Camera** — camera 40.75881, -73.97759 (NYC_TM -2336, 6516) z 23.3 m NAVD88 | azimuth 106.5deg pitch +0.0deg | 19 mm on 36 mm (71.1deg horizontal, 87.3deg vertical, portrait) | 904x1206. View direction: 106.5 deg, the bearing from this photograph's own GPS position to St. Patrick's Cathedral; heading and position both come from the photograph.  The item's recorded azimuth is 111.2 deg, 4.7 deg away, and belongs to its nominal viewpoint. Aim: level optical axis (St. Patrick's Cathedral is 122 m away and would need +22 deg of tilt; a real frame would use a wider lens instead, and a tilted axis would stop the render being comparable on proportion).

**Sun** — azimuth 171.9°, elevation 60.9° at 2021-08-21T12:42:57-04:00 (EXIF DateTimeOriginal).

**In frame** — 5/5 building tiles (179,070 tris), 9 landmark models, 1,506 pavement polygons, 528 props, 9,477 facade-kit pieces; 4,500,144 triangles; ground mesh 205² at 2.0 m near / 40.0 m far.

**Camera clearance** — the recorded viewpoint is inside t_-3_6_roof_membrane (a ray straight up from the eye point hits its roof); the camera was moved 16 m onto the nearest real sidewalk polygon in data/processed/roads/pavement, keeping the same eye height above the heightmap.  The view azimuth is clear for 73 m from there

**Verdict — raised from black (0.023) to legible (0.222) by moving the camera off a wall it was 1.6 m from, and what is now visible is a Midtown side street with the cathedral's spire just showing between the trees — recognisable but marginal**

## What matches

* The camera was 1.6 m from a building footprint, which is why the frame was near-black; the in-the-lens test caught it and the pavement snap moved it out, giving 73 m of clear azimuth against the 61 m needed.
* The cathedral's spire and the pitched roof behind it are visible between the trees at the right bearing and distance — the Gothic profile is discernible in the mid-distance.
* The street trees are correct London planes in full leaf at the right kerb spacing, and their canopies read as canopies rather than as masses.
* The side-street section is right: roadbed, sidewalks, kerb reveal, sidewalk sheds with lit soffits on the right, and 1,839 pavement polygons.
* 15 landmark models are in range with their shells suppressed.

## What does not match

* The cathedral is a marginal presence rather than the subject. Its Fifth Avenue front, the twin spires, the rose window and the bronze doors — everything the reference is of — are not in the frame.
* Mean luminance 0.222: the street is in shadow.
* What can be seen of the cathedral has no surface: the marble is one flat pale colour with no tracery, no buttresses, no window openings.
* No people, no vehicles, no signage.
* The lower half of the frame is bare roadbed and sidewalk with no texture and no markings.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the cathedral front is not in the frame | the corrected camera looks along a side street rather than at the Fifth Avenue front | camera |
| frame in shadow | a Midtown side street between tall blocks | lighting |
| no tracery, buttresses or openings | the st_patricks_cathedral model carries the massing and spire form with a flat base colour | geometry |
| no people, vehicles or signage | no stage places any of them | data |
| bare roadbed | pavement polygons carry a kind but no texture or markings | material |
