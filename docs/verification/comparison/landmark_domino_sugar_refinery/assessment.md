# Domino Sugar Refinery

`landmark_domino_sugar_refinery` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Domino Sugar Refinery June 2022.jpg by Kidfly182, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2022-06-28 13:43:57, 1920x1440. [Commons page](https://commons.wikimedia.org/wiki/File:Domino_Sugar_Refinery_June_2022.jpg)

**Camera** — camera 40.71318, -73.96774 (NYC_TM -1473, 1454) z 7.4 m NAVD88 | azimuth 9.4deg pitch +0.0deg | 26 mm on 36 mm (69.9deg horizontal) | 1208x906. View direction: 9.4 deg, the bearing from this photograph's own GPS position to Domino Sugar Refinery; heading and position both come from the photograph.  The item's recorded azimuth is 198.0 deg, 171.4 deg away, and belongs to its nominal viewpoint. Aim: level optical axis (Domino Sugar Refinery is 126 m away and would need +12 deg of tilt; a real frame would use a wider lens instead, and a tilted axis would stop the render being comparable on proportion).

**Sun** — azimuth 211.7°, elevation 70.2° at 2022-06-28T13:43:57-04:00 (EXIF DateTimeOriginal).

**In frame** — 5/5 building tiles (134,182 tris), 2 landmark models, 1,045 pavement polygons, 498 props, 5,229 facade-kit pieces; 2,451,466 triangles; ground mesh 205² at 2.0 m near / 40.0 m far.

**Camera clearance** — the recorded viewpoint is inside t_-2_1_roof_membrane (a ray straight up from the eye point hits its roof); the camera was moved 28 m onto the nearest real sidewalk polygon in data/processed/roads/pavement, keeping the same eye height above the heightmap.  The view azimuth is clear for 75 m from there

**Verdict — the refinery is the best brick landmark in the set — round-arched window grid, correct red brick, the barrel-vaulted glass roof of the 2023 conversion, and the raw-sugar tanks beside it — but it has no chimney, no steel bracing and no surface, and the esplanade it stands on is a bare plane**

## What matches

* The Refinery building is recognisably itself: a rectangular brick block with a regular grid of tall round-arched windows over six storeys, at the right footprint and the right height 82 m from the camera.
* The brick colour is right — the deep red-brown of the real Havemeyers & Elder building — and it is one of the very few surfaces in the whole set that reads as the right material.
* The barrel-vaulted glass roof added in the 2023 conversion is modelled and sits correctly above the retained brick shell, which is what the building looks like now rather than in the reference's 2022 state.
* The cylindrical raw-sugar tanks stand beside it at the right diameter and height.
* The heading is measured: 9.3 deg, the bearing from this photograph's own GPS to the refinery, against a recorded azimuth of 198.0 deg — 171 deg out, and the sheet says the recorded value was discarded.
* The esplanade's lamps, railings and the Williamsburg block faces on the right are all placed, with 785 pavement polygons and 415 props.

## What does not match

* The chimney is missing. The reference's most prominent element is the tall brick stack with 'HAVEMEYERS & ELDER' on it, and the render has nothing in that position.
* The external steel bracing frame that wraps the reference's facade — the most striking thing about the building in its stripped state — is absent.
* The brick has no texture: no courses, no mortar, no weathering, no blocked-up openings. The reference is 150 years of soot and repair.
* No glass in the arched openings: they are dark recesses.
* Domino Park is a flat grey plane. The reference's foreground is mature planting, a lawn and the park's own steel structures; the render has bare ground and a handful of trees rendered as dark silhouettes because they are backlit at a 70 deg June Sun.
* No people on an esplanade that is never empty, and no vehicles.
* The pitch rule kept the axis level and stated why: the subject is 82 m away and would need +19 deg of tilt, so the render frames more foreground and less building than the reference does.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| no chimney | the refinery's stack is a separate structure with no footprint of its own and is not in the landmark model | geometry |
| no external steel bracing | the bracing is temporary works, not in any dataset | geometry |
| no brick texture | shells and landmark models carry a flat base colour per material | material |
| no glass in the arches | the kit supplies openings without glazing | material |
| no park, no planting | park surfacing and planting are in no dataset the scene reads | data |
| no people or vehicles | no crowd or traffic placement feeds the verification scene | data |
| backlit trees read as silhouettes | the canopy is untextured geometry with no translucency | material |
