# Statue of Liberty

`landmark_statue_of_liberty` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Statue of Liberty, New York City, 20231003 1511 1972.jpg by Jakub Hałun, CC BY 4.0 (https://creativecommons.org/licenses/by/4.0), taken 2023-10-03 15:11:01, 1920x2876. [Commons page](https://commons.wikimedia.org/wiki/File:Statue_of_Liberty,_New_York_City,_20231003_1511_1972.jpg)

**Camera** — camera 40.68840, -74.04340 (NYC_TM -7895, -1284) z 1.6 m NAVD88 | azimuth 315.5deg pitch +0.0deg | 21 mm on 36 mm (58.9deg horizontal, 80.5deg vertical, portrait) | 854x1280. View direction: 315.5 deg as recorded; it agrees with the bearing from the camera position used to Statue of Liberty (315.5 deg) to 0.0 deg. Aim: level optical axis (Statue of Liberty is 132 m away and would need +21 deg of tilt; a real frame would use a wider lens instead, and a tilted axis would stop the render being comparable on proportion).

**Sun** — azimuth 225.8°, elevation 34.2° at 2023-10-03T15:11:01-04:00 (EXIF DateTimeOriginal).

**In frame** — 3/4 building tiles (3,332 tris), 2 landmark models, 8 pavement polygons, 49 props, 1,053 facade-kit pieces; 590,836 triangles; ground mesh 201² at 2.0 m near / 40.0 m far.

**Verdict — the statue is modelled, correctly coloured and correctly placed on Fort Wood — and it stands on an island that is a bare disc awash to the waterline, at about half the apparent size the pedestal implies**

## What matches

* The Statue of Liberty is recognisably itself: the raised torch arm, the crowned head with its rays, the tablet in the left arm and the draped robe, all in the right weathered-copper green.
* The colour is right, and it is one of very few surfaces in the whole comparison set whose material reads correctly at a glance.
* Fort Wood's eleven-point star pedestal base is modelled with the right plan and the right stepped profile, and the statue sits centred on it.
* The origin rule chose correctly and says why: this photograph's own GPS is 53 m away but the eye point there is under verify_pavement, while the item's recorded viewpoint is in open air.
* The lens rule widened 35 mm to 21 mm so that a level axis contains the statue: 96 m above the lens at 132 m, 36 deg above the horizon.
* The heading agrees exactly with the bearing to the statue (315.5 deg both).

## What does not match

* The statue is much too small for its pedestal. The published 93 m model height is the statue *plus* pedestal; on screen the figure reads at perhaps half the proportion the reference shows against the same base.
* Liberty Island is a bare disc awash to the waterline: no lawn, no paths, no trees, no flagpole plaza, no seawall, and the water comes straight up to the fort's foot.
* The pedestal has no surface: the reference's granite is rusticated with deep courses, string moulding, columns and openings, and the render's is a plain pale block with a few dashes.
* The statue's own surface has no folds, no rivets, no plate seams — only the silhouette is right.
* The mirror-flat water reflects the whole thing, which no photograph of the island ever shows.
* No people at all, on an island whose scale is always read from the visitors on the pedestal balcony.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| statue too small for its pedestal | the b_statue_of_liberty model's proportion between figure and base does not match the published 46 m figure on a 47 m pedestal | geometry |
| island awash, no lawn or paths | Liberty Island's landscaping and seawall are in no dataset the scene reads, and the terrain heightmap flattens it to the waterline | data |
| no granite courses or plate seams | landmark models carry a flat base colour per material with no texture | material |
| mirror water | the water material is roughness 0.06 with no wave normal | material |
| no people | no crowd placement feeds the verification scene | data |
