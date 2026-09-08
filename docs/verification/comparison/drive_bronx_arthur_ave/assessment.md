# Bronx drive-through: Arthur Avenue (Belmont)

`drive_bronx_arthur_ave` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** - File:Arthur Avenue 09 - M&G Restaurant.jpg by Joe Mabel, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2026 - a year, with no day and no instant - 1920x1280. [Commons page](https://commons.wikimedia.org/wiki/File:Arthur_Avenue_09_-_M%26G_Restaurant.jpg)

**Camera** - camera 40.85524, -73.88776 (NYC_TM 5255, 17278) z 25.9 m NAVD88 | azimuth 190.0 deg pitch +0.0 deg | 35 mm on 36 mm (54.4 deg horizontal) | 1280x854, eye 1.6 m above a terrain surface of 24.30 m taken as the 10th percentile of 113 heightmap samples within 12 m, so the camera stands on the street rather than on a raised building grade. The lens is the default and the axis level because "the reference names no subject to aim at"; the bearing is the item's recorded 190 deg, the heading of Arthur Avenue rather than anything derived from the photograph. The stand point is the photograph's own EXIF GPS, 15.9 m from the item's recorded viewpoint, and the clearance rule then moved the camera 35.7 m onto the nearest real crosswalk polygon because the axis was closed off 10 m ahead; from there it runs clear for 45.4 m.

**Sun** - azimuth 95.5 deg, elevation 43.6 deg at 2026-06-21T09:30:00-04:00. Assumed, not measured: the file carries only the year, so the fallback puts it at 21 June, 09:30.

**In frame** - 4 of 4 building tiles carrying 261,870 triangles, 0 landmarks, 2,363 pavement polygons (958 curb, 541 crosswalk, 395 roadbed, 235 sidewalk, 132 parking-lot, 76 median, 26 plaza, none dropped), 393 props, 6,622 facade-kit pieces, 88,200 terrain triangles, 89 vehicles and 281 people; **4,475,972 triangles** in 268.5 s at 64 samples. Two budgets bite: props are cut to 393 of the 880 in range by a 1,386,876-triangle budget, and 4 vehicles fall to the agent budget. 21 opaque impostor cards were dropped; 62 of the 200 trees are a substituted species. Frame mean 0.3085, sd 0.2071.

**Verdict - the street is right and the picture is not: block-face scale, kerb line, June canopy, the facade kit and the newly cut curb ramp all hold, but two pedestrians stand at the lens over a carriageway with no vehicle anywhere on it, and every shopfront and window in the frame is a blank panel where the reference is glass, goods and raised black lettering.**

## What matches

* **The section of the street is right.** Two facing block faces whose frontages run off the top edge of the frame, a continuous ground-floor commercial band on both sides, sidewalks raised on a visible kerb face, and a roadbed wide enough for two lanes and kerbside parking. Behind it: 2,363 planimetric pavement polygons, none dropped, and 4 of 4 building tiles with nothing missing or substituted at a lower LOD.
* **A surveyed curb ramp is visible, and this is the first Arthur Avenue sheet in which it is.** In the near right foreground the sidewalk drops to the roadbed as a wedge with side flares cut into the pavement mesh, not as a kerb that simply stops. The 81 `curb_ramp` rows now report as `built_elsewhere` rather than `unmapped`, retiring the stale-label caveat the previous assessment carried.
* **The trees are the strongest thing in the frame.** 200 of the 393 props are trees; full June canopies close over the roadway from both kerbs, with trunk and branch structure that reads as a tree rather than a billboard, and leaf shadows across the facades and the asphalt.
* **The kit is placed and legible.** Of 6,622 pieces I can pick out black zigzag fire escapes on the right-hand frontage (147 in scene), a wall-mounted air-conditioning box (13 HVAC), and lintels and sills on the openings (3,904 windows, 686 accessories).
* **The signage geometry exists.** Lit white fascia bands run the length of both frontages, each with a small dark blade sign on a bracket in front of it, and a scalloped green awning covers a shopfront down the block - B15's stock, visible in daylight.
* **The street furniture is where it should be**: a red hydrant at the right kerb at the right size, a manhole disc in the asphalt at the left, and a lamp column carrying a mast arm out over the roadway - 26 hydrants, 54 manholes and 61 street lamps in scene.

## What does not match

* **The two halves are not the same kind of picture, and the sheet says so.** The reference is the M&G Restaurant frontage from a few metres across the sidewalk; the render looks down the middle of the avenue. The item names no subject, so the azimuth is the street heading and no bearing can be recovered from the image (I7). Street width, storey height and material are comparable; composition is not.
* **Two pedestrians own the foreground.** One in a dark top and shorts stands on the pale crosswalk slab in the centre of the frame, one in a purple top and white trousers on the right sidewalk; both are drawn whole - the near one's white trainers end a few pixels above the bottom edge, the woman's black shoes some 320 px above it - and between them they hold the middle of the picture. The clearance record says "the nearest solid thing anywhere in the frame is prop_tree_sophora_small_9 18.8 m away" - a true measurement of the built scene, taken before any agent was placed and silent about the two people the render then put at the lens. The shape of J47 and I17: a real number that cannot fail the way the thing it stands for can.
* **No vehicle appears anywhere in the frame.** 89 are placed within 320 m in eight classes led by 49 sedans, and the roadway runs empty asphalt from the lens to the vanishing point. Nothing stands at either kerb: the record's fleet is the traffic simulation's moving vehicles and carries no parked category.
* **This sheet therefore cannot confirm the J44 fix.** The bone display sphere that rode at every rigged vehicle's rear axle is gone from the importer and all 89 vehicles here are LOD2 - but no car is in this picture, so the claim rests on the test, not on this frame.
* **The shopfronts are blank.** Below the fascia the frontage is a flat panel with vertical mullion strips: no glass, no visible interior, no lettering, no goods. 883 storefront pieces and 122 storefront interiors are placed and none of it reads as a shop - where the reference's whole subject is a red shopfront with raised black letters, a valance of meal services and a telephone number, a neon Coffee sign and plants in the window.
* **The windows have no glass.** Each upper-storey opening is a lintel and sill with two thin jamb lines and a panel exactly the colour of the wall behind it. The reference's are dark glazing with white sashes, blinds and a window air-conditioner.
* **No fascia carries a business name.** The bands are blank white; one further down the block reads OPEN in grey. That is B15a exactly.
* **The roadway is untextured and unmarked.** Plain dark grey with no lane or centre line, and the crosswalk polygon the camera stands on is a pale grey slab with no bar markings.
* **The light is a guess and the guess is visible.** A 43.6 deg east sun at 09:30 on 21 June throws hard leaf shadows across the facades; the reference is flat light under a blown-out white sky, its brick and painted stucco frontage carrying almost no shadow (I16).
* Smaller absences: the reference's traffic cones, wheelie bin, iron area railing, glazed vestibule and yellow kerb paint. One `parks_comfort_station` is unmapped and not drawn.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the two halves are of different subjects | the item names no subject, so the stage assigns the street heading; the photograph is a frontage at a few metres (I7) | reference |
| the Sun is assumed | the file carries a year and no instant, so the stage falls back to 21 June 09:30; a physically lit render against a metered photograph (I16) | reference |
| two pedestrians at the lens | the clearance probe runs before agents are placed and constrains a narrow cone, not the frame (J47, I17) | verification |
| no vehicle visible | 89 is a disc count within 320 m, not a frame count; none falls in the 54.4 deg wedge on this block | reporting |
| nothing parked at either kerb | the traffic simulation models moving vehicles; no parked-vehicle layer exists | data |
| J44 cannot be verified here | the frame contains no vehicle to inspect | verification |
| blank shopfronts | the facade kit supplies openings and fascias with no glazing, dressing or goods | material |
| windows without glass or reveal | the window piece is a lintel, sill and jambs on the shell surface; 96.69 % of facades are rule-inferred (A2) | material |
| no business name on any fascia | an instanced kit piece carries one texture, so the name stays in `awning_text` (B15a, B4) | data |
| untextured roadway, unmarked crosswalk | pavement carries a kind and a flat measured colour, no texture - J40's gap, on asphalt | material |
| 393 props of 880 in range | the 1,386,876-triangle prop budget, spent on trees first | budget |
| 62 trees are a substituted species | trees are procedural and the library carries a subset of the census species (D6) | data |
| comfort station not drawn | `parks_comfort_station` has no asset in the props catalogue | data |
