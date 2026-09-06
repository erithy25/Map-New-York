# Hudson Yards and the Vessel

`landmark_hudson_yards_vessel` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:The Vessel April 2022 004.jpg by Kidfly182, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2022-04-18 13:02:07, 1920x1440. [Commons page](https://commons.wikimedia.org/wiki/File:The_Vessel_April_2022_004.jpg)

**Camera** — camera 40.75357, -74.00137 (NYC_TM -4364, 5966) z 4.4 m NAVD88 | azimuth 290.1deg pitch +0.0deg | 18 mm on 36 mm (90.0deg horizontal) | 1208x906. View direction: 290.1 deg, the bearing from this photograph's own GPS position to the Vessel; heading and position both come from the photograph.  The item's recorded azimuth is 288.3 deg, 1.8 deg away, and belongs to its nominal viewpoint. Aim: level optical axis (the Vessel is 75 m away and would need +69 deg of tilt; a real frame would use a wider lens instead, and a tilted axis would stop the render being comparable on proportion).

**Sun** — azimuth 183.4°, elevation 60.2° at 2022-04-18T13:02:07-04:00 (EXIF DateTimeOriginal).

**In frame** — 4/4 building tiles (146,604 tris), 5 landmark models, 1,392 pavement polygons, 522 props, 97 facade-kit pieces; 1,454,284 triangles; ground mesh 201² at 2.0 m near / 40.0 m far.

**Camera clearance** — the recorded viewpoint is inside lm_c_hudson_yards.44 (a ray straight up from the eye point hits its roof); the camera was moved 30 m onto the nearest real roadbed polygon in data/processed/roads/pavement, keeping the same eye height above the heightmap.  The view azimuth is clear for 60 m from there

**Verdict — the Vessel's interlocking stair lattice is modelled and unmistakable — the best sculptural landmark in the set — and it hovers on a disc above the plaza with nothing under it, seen from a camera that had to be moved 30 m out of a building shell**

## What matches

* The Vessel is recognisably itself: the honeycomb of interlocking flights, the hexagonal landings stacked in eight tiers, the outward taper and the copper-brown steel colour are all correct and read at a glance.
* The camera stands on the photograph's own EXIF GPS, 32 m from the item's nominal viewpoint, and the heading (290.1 deg) is the bearing from there to the Vessel.
* The lens rule fired and states its own limit honestly: 35 mm widened to the 18 mm floor because the structure tops out 385 m above the lens only 75 m away, and no normal lens contains it.
* The clearance correction is stated: the recorded viewpoint is inside lm_c_hudson_yards.44, and the camera was moved 30 m onto the nearest real roadbed with 60 m of clear view.
* The Hudson Yards towers either side carry glass curtain wall with a legible mullion grid, and 30 Hudson Yards' massing closes the frame at the right height.

## What does not match

* The Vessel floats. Its base is a smooth disc suspended above the plaza with no plinth, no steps up to it, no ground contact and no supporting structure; in the reference it sits on the square.
* The Vessel's underside is a blank dark surface where the real structure is open lattice all the way through.
* The public square is a flat grey plane: no paving pattern, no planting, no benches, no water feature, no barriers.
* The camera ended up under the structure rather than across the square from it, so the render's composition and the reference's are unrelated: the photograph is a flat elevation of the whole Vessel through the Shed's glazing, the render is a worm's-eye view of its base.
* No people, on a plaza whose whole purpose is people.
* Only 97 kit pieces are placed in the entire scene, so the surrounding buildings have almost no facade detail; and the glass has no reflections of the Vessel, which is the reference's dominant effect.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the Vessel floats above the plaza | the c_hudson_yards landmark model's base is not resolved against the terrain surface at this location | geometry |
| blank underside | the model closes the lattice with a solid disc rather than continuing it | geometry |
| bare public square | plaza paving, planting and furniture are in no dataset the scene reads | data |
| worm's-eye composition | the corrected camera is 30 m from the recorded viewpoint and under the structure; the clearance search takes the nearest open point, not the best composition | camera |
| no people | no crowd placement feeds the verification scene | data |
| no glass reflections | the curtain-wall material is not reflective | material |
