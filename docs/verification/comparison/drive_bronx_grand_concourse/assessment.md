# Bronx drive-through: Grand Concourse Art Deco apartments

`drive_bronx_grand_concourse` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** - `2.jpg`, File:Dollar Savings Bank of New York headquarters building, Grand Concourse & East Fordham Road, The Bronx, New York.jpg by Deansfa, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2022-10-09 12:16:14, 1920x2560. [Commons page](https://commons.wikimedia.org/wiki/File:Dollar_Savings_Bank_of_New_York_headquarters_building,_Grand_Concourse_%26_East_Fordham_Road,_The_Bronx,_New_York.jpg)

**Camera** - 40.83200, -73.91860 (NYC_TM 2644, 14663) z 31.6 m NAVD88, eye 1.6 m above a terrain surface read at 29.985 m; azimuth 25.0 deg, pitch +0.0 deg; 35 mm on 36 mm (42.2 deg horizontal, 54.4 deg vertical, portrait) at 904x1206; moved 4.9 m onto the nearest roadbed polygon because the recorded eye point sat inside `t_2_14_roof_membrane`. It is aimed at 25.0 deg because that is the street heading recorded in `meta.json` and for no better reason: the item names no subject, so the lens stays at the default 35 mm and the axis stays level.

**Sun** - azimuth 171.0 deg, elevation 42.4 deg at 2022-10-09T12:16:14-04:00, from the photograph's EXIF DateTimeOriginal rather than an assumption; direct normal irradiance 854 W/m2, Nishita sky, Filmic at +0.03 stops, 64 Cycles samples.

**In frame** - 6 of 6 building tiles, 323,032 triangles against a 3,510,000-triangle budget; 2 landmarks loaded (Yankee Stadium, Bronx County Courthouse), neither in the picture; 2,433 pavement polygons, none dropped (923 curb, 601 crosswalk, 408 roadbed, 251 sidewalk, 143 median, 88 parking lot, 19 plaza); 407 props of 872 in range, capped at a 1,356,090-triangle budget - 208 trees with 78 species substituted, 63 street lamps, 61 manholes, 29 hydrants, 27 subway vent grates, 10 cooling towers - plus 16 opaque impostor cards dropped and 81 curb ramps built into the pavement rather than as props; 5,695 kit pieces of 6,754 in range, capped at a 1,429,814-triangle budget, including 4,052 windows, 329 storefronts, 213 scaffold pieces and 83 cornices; 89 vehicles, all LOD2, and 307 people (7 LOD0, 11 LOD1, 295 LOD2); terrain 88,200 triangles, no holes. **4,500,226 triangles** in total, which is the sum of those parts and not a ceiling - the budgets that bind are the prop, kit and 1,125,000-triangle agent ones.

**Verdict - a convincing, well-populated Bronx kerbside under a green sidewalk shed, and no evidence whatever about the Grand Concourse: the reference is the right avenue 3.9 km north (I12), and the frame-wide clearance probe passes a picture whose right half is a canopy and its post, because the probe counts building shells and a shed is kit.**

## What matches

* The left of the frame is a continuous green sidewalk shed on posts, its deck lit from underneath in daylight, running the length of a red-brick block and on past a cream one; 213 scaffold pieces are placed. The reference photograph's block is wrapped in exactly that, a long scaffold over the pavement with netting on it. It is the strongest correspondence on the sheet and it is a coincidence, since the two halves stand 3.9 km apart.
* The far corner is a shopfront row on green columns under a green awning band with a white top edge, people standing beneath it - 329 storefronts and 56 storefront interiors. The photograph carries the same green band along the base of its block.
* Street trees are in full leaf on both sides of the render and in the photograph; the date is 9 October in both halves. 208 of the 407 props are trees, 78 with a substituted species.
* The traffic and crowd are of the right kinds: a yellow taxi and a white box truck at the far junction, a dark car beyond, six or seven people under the far shed, one walking figure near the lens. The sheet is explicit that this is the simulation's own traffic for that hour and neighbourhood, not the photograph's.
* **J44 is closed and this sheet is where you can see it**: the taxi's rear wheel and the truck's rear axle are clean, with no untextured grey sphere under either, on any of the 89 vehicles.
* Two other repairs show. 6 pedestrians were culled over the observer after the camera moved (I15), leaving one figure near the lens where the previous render had four backs; and `curb_ramp: 81` now sits under `built_elsewhere` with the unmapped list empty, so the ramps read as pavement geometry (J21).
* The pavement stack reads correctly where visible - concrete footway, a raised kerb catching the sun, a dark gutter line, asphalt - with a red hydrant at a tree pit and base plates under the shed posts. Both halves share their weather and light: clear sky, high sun behind the lens, hard shadows thrown back at the viewer.

## What does not match

* **The reference is 3,854 m from the camera.** The photograph is the Dollar Savings Bank at East Fordham Road; the viewpoint is the Concourse at East 165th Street. The sheet says so, and says why the photograph's own GPS was rejected as mis-tagged: it is past the 250 m at which it could still be the same view. This is remainder (2) named under I12, unchanged.
* The sheet also warns that the two halves may not face the same way - the item names no subject and the photograph's view direction was never derived from the image. It offers street width, storey height and material as the comparison instead, and the render then declines to show a storey.
* **The right half of the picture is not street.** An overhead canopy on a post stands immediately right of the lens, a lit panel under its deck, a beige wall behind it with two bracket-mounted air conditioners and a door. The clearance record says the nearest obstruction is 20.0 m, at 0.0, 0.0 deg, and since J47 the probe sweeps the whole frame rather than a 6 deg cone. Both are true. But it counts building shells and landmark models (I17), and what closes half of this frame is kit, so the number is not about the picture the reader sees.
* One pedestrian's back still takes most of the near right. I15's raised radius and post-camera cull are why this is one figure and not four, but at 54.4 deg vertical a body just outside that radius is still a large share of the picture. The camera is also standing in the carriageway at 1.6 m with 89 vehicles in the scene, the clearance move having gone "onto the nearest roadbed" - I14, still open.
* **Nothing in the frame is Art Deco**, which is what the item is named for: no setbacks, no brick banding, no casement rhythm, no relief, and a near red-brick face with a few small openings and no window rhythm. The slab that closes the view is a blank cream wall - the kit was read from one tile, `t_2_14`, within a 120 m radius, so shells past it get no windows.
* The roadway carries no markings anywhere in frame, though 601 crosswalk polygons are in the scene, and the photograph's roadway has a painted yellow centre line. Its fascias have signs and a billboard where the render's green panels are blank (B15a).
* The Concourse is not legible as the Concourse: one carriageway between two block faces, no central mall, service road or planted median in view. 143 median polygons are in the scene and the record says nothing about where they fall relative to the frame, so this sheet cannot tell an absent mall from an out-of-view one. Today's curb ramps are as unverifiable - the near kerb runs unbroken and no crossing is in view.
* A pale sliver of the base body shows between the near figure's jumper hem and waistband, the E8 family. And the sheet contradicts itself by six people: the "In frame" line says 307, the agents line 313.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the reference stands 3.9 km from the viewpoint | Commons has nothing free looking along the Concourse near East 165th Street; remainder (2) of I12 | reference |
| the two halves may not face the same way | the chooser establishes a place, never a view direction | reference |
| a canopy and its post fill the right half | the widened probe (J47) counts only building shells and landmarks (I17); a shed is kit | verification |
| the camera stands in live traffic | the clearance move snaps to the nearest roadbed (I14) | verification |
| one pedestrian dominates the near right | I15's clearance is a radius, not a share of this lens's frame | verification |
| median and curb ramps unaccounted for | the record counts them in the scene and not in the view | verification |
| no Art Deco relief, setbacks or banding | facades inferred from a rule table (A2); no Deco vocabulary in the kit | geometry |
| skin showing at the figure's waist | garment fitting between top and trousers, the E8 family | geometry |
| the far slab is a blank wall | kit read from one tile within 120 m, so shells beyond it carry no openings | budget |
| props and kit capped, 825 people and 77 vehicles dropped | their triangle budgets, the agent one 1,125,000 | budget |
| no lane, centre or crosswalk markings | pavement is a flat colour per kind, no texture and no paint | material |
| blank shopfront fascias | one instanced fascia mesh cannot carry 30,381 business names (B15a) | material |
| 307 people in one caption line, 313 in another | the agents caption predates the cull of 6, the placed count follows it | reporting |
