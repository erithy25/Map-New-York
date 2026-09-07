# Rockefeller Center (30 Rockefeller Plaza)

`landmark_rockefeller_center` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Rockefeller Center British Empire Building Gold-Leaf-Figures 2021-05-13 17-37.jpg by Axel Tschentscher, Public domain (https://commons.wikimedia.org/wiki/Commons:Licensing#Material_in_the_public_domain), taken 2021-05-13 17:37:41, 1920x2909. [Commons page](https://commons.wikimedia.org/wiki/File:Rockefeller_Center_British_Empire_Building_Gold-Leaf-Figures_2021-05-13_17-37.jpg)

**Camera** — camera 40.75880, -73.97760 (NYC_TM -2331, 6530) z 23.4 m NAVD88 | azimuth 296.9deg pitch +0.0deg | 18 mm on 36 mm (66.9deg horizontal, 90.0deg vertical, portrait) | 848x1284. View direction: 296.9 deg as recorded; it agrees with the bearing from the camera position used to 30 Rockefeller Plaza (296.8 deg) to 0.1 deg. Aim: level optical axis (30 Rockefeller Plaza is 123 m away and would need +46 deg of tilt; a real frame would use a wider lens instead, and a tilted axis would stop the render being comparable on proportion).

**Sun** — azimuth 272.8°, elevation 26.0° at 2021-05-13T17:37:41-04:00 (EXIF DateTimeOriginal).

**In frame** — 6/6 building tiles (186,270 tris), 12 landmark models, 1,741 pavement polygons, 512 props, 8,539 facade-kit pieces; 4,500,123 triangles; ground mesh 207² at 2.0 m near / 40.0 m far.

**Verdict — a dark side street with a row of London planes along a blank wall: 30 Rockefeller Plaza, the Channel Gardens, the sunken plaza and Prometheus are all outside the frame, and what is in it has no surface at all**

## What matches

* The street trees are the best thing here: a correct row of mature planes at the right spacing along the kerb, in full leaf, with visible trunk and branch structure.
* The street section is right — roadbed, both sidewalks, kerb reveal — and 1,513 pavement polygons carry it.
* The clearance report gives 150 m of clear azimuth against the 75 m the subject needs, so the camera is correctly placed on a real surface with a real sightline.
* 9 landmark models are in range with their shells suppressed, and the block faces down the street step correctly.

## What does not match

* None of Rockefeller Center is identifiable. 30 Rockefeller Plaza's limestone slab, the Channel Gardens, the sunken plaza, the gilded Prometheus and the flag row — the whole reason for the item — are not in the frame.
* The wall on the right fills half the picture and is a single flat cream plane with no openings, no joints and no detail whatever.
* Mean luminance 0.169: the street is in deep shadow at a low Sun.
* No people, no vehicles, no signage, no flags.
* The lower half of the frame is bare untextured pavement.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| Rockefeller Center is not in the frame | the recorded viewpoint looks along a side street rather than into the plaza; the clearance rule can correct a blocked camera but cannot choose a better viewpoint | reference |
| blank wall filling half the frame | shells carry a per-material base colour, and the facade kit placed nothing on this frontage | geometry |
| frame in deep shadow | a Midtown side street at a low Sun with two light bounces | lighting |
| no people, vehicles, signage or flags | no stage places any of them | data |
| bare pavement | pavement polygons carry a kind but no texture | material |
