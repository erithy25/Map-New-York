# One Times Square

`landmark_one_times_square` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Paramount Building via One Times Square.jpg by Scu ba, CC0 (http://creativecommons.org/publicdomain/zero/1.0/deed.en), taken 2024-06-27 15:26:26, 1920x2560. [Commons page](https://commons.wikimedia.org/wiki/File:Paramount_Building_via_One_Times_Square.jpg)

**Camera** — camera 40.75601, -73.98659 (NYC_TM -3082, 6220) z 18.4 m NAVD88 | azimuth 10.6deg pitch +0.0deg | 18 mm on 36 mm (73.7deg horizontal, 90.0deg vertical, portrait) | 904x1206. View direction: 10.6 deg, the bearing from this photograph's own GPS position to One Times Square; heading and position both come from the photograph.  The item's recorded azimuth is 200.0 deg, 170.6 deg away, and belongs to its nominal viewpoint. Aim: level optical axis (One Times Square is 47 m away and would need +76 deg of tilt; a real frame would use a wider lens instead, and a tilted axis would stop the render being comparable on proportion).

**Sun** — azimuth 251.8°, elevation 54.6° at 2024-06-27T15:26:26-04:00 (EXIF DateTimeOriginal).

**In frame** — 4/4 building tiles (188,464 tris), 2 landmark models, 964 pavement polygons, 369 props, 7,739 facade-kit pieces; 2,580,789 triangles; ground mesh 199² at 2.0 m near / 40.0 m far.

**Camera clearance** — the recorded viewpoint is boxed in: the view azimuth is closed off 3 m ahead, less than the 23 m this frame needs to show its subject; the camera was moved 8 m onto the nearest real sidewalk polygon in data/processed/roads/pavement, keeping the same eye height above the heightmap.  The view azimuth is clear for 38 m from there

**Verdict — One Times Square's dark wedge is in the frame and its whole reason for existing is not: the building is a blank grey mass where the real one is a floor-to-roof stack of screens, and the square around it is empty pavement**

## What matches

* The building is in the right place with the right footprint: the narrow wedge closing the bowtie, its long flank running away to the left, at the right height against the towers behind.
* The camera stands on the photograph's own EXIF GPS and the heading is the bearing from there to the building; the boxed-in test accepted the position with 38 m of clear azimuth against the 23 m needed.
* The bowtie geometry reads correctly: Broadway and Seventh Avenue splitting either side of the wedge, the pedestrian plaza between them, a subway entrance with its railings and sign, and a traffic signal head on its pole.
* The towers up the avenue are at the right heights with glazing legible on the landmark models, and 1,848 pavement polygons carry the plaza and crossing geometry.

## What does not match

* One Times Square is a blank dark mass. The real building is almost entirely advertising: the New Year's Eve ball and pole, the Coca-Cola sign, the full-height LED wrap on the south face and the smaller boards below. None of it is modelled, and without it the building has no identity at all.
* The plaza is empty pavement — no cafe tables, no chairs, no planters, no bollards, no barriers.
* No people and no vehicles in Times Square.
* The facades carry no glass, no mullions and no signage anywhere in the frame.
* The lower half of the frame is a large untextured pale plane with visible facets from the graded terrain grid.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the building is blank where it should be all signage | no stage produces sign, screen or billboard geometry | geometry |
| empty plaza | plaza furniture is in no dataset the scene reads | data |
| no people or vehicles | no crowd or traffic placement feeds the verification scene | data |
| no glass or mullions | shells carry a per-material base colour; the kit supplies openings without glazing | material |
| untextured, faceted pavement | the pavement material is a flat colour per kind | material |
