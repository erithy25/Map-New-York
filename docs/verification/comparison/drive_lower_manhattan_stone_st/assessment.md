# Lower Manhattan drive-through: Stone Street

`drive_lower_manhattan_stone_st` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** - File:Financial District Manhattan April 2022 008.jpg by Kidfly182, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2022-04-19 13:45:47, 1920x1440. [Commons page](https://commons.wikimedia.org/wiki/File:Financial_District_Manhattan_April_2022_008.jpg)

**Camera** - camera 40.70410, -74.01070 (NYC_TM -5133, 465) z 4.0 m NAVD88, eye 1.6 m above the terrain surface | azimuth 60.0 deg pitch +0.0 deg | 35 mm on 36 mm (54.4 deg horizontal) | 1208x906. It is aimed here for the weakest of the available reasons and the record says so: 60.0 deg is the azimuth recorded in meta.json, the block's own heading rather than a bearing read out of the photograph (confidence medium); the lens is the default 35 mm full-frame equivalent; the axis is level because this item names no subject to aim at. The clearance rule then moved the camera 7.2 m onto the nearest real sidewalk polygon, because the recorded viewpoint is closed off 11 m ahead against the 12 m this frame needs. From where it now stands the azimuth is clear for 60 m and the nearest solid thing recorded is `t_-6_0_red_brick`, 11.2 m away at -27 deg yaw.

**Sun** - azimuth 204.4 deg, elevation 58.6 deg at 2022-04-19T13:45:47-04:00, from EXIF DateTimeOriginal rather than an assumption.

**In frame** - 6/6 building tiles (86,646 triangles, none missing, none LOD-substituted); 12 landmark models; 2,005 pavement polygons (928 curb, 441 crosswalk, 343 roadbed, 179 sidewalk, 56 median, 51 plaza, 7 parking lot, none dropped); 586 props of 1,069 in range; 6,309 facade-kit pieces of 13,894 in range; 89 vehicles and 377 people; 4,500,162 triangles; ground mesh 211² at 2.0 m near and 40.0 m far, no holes; frame mean 0.2486, sd 0.1501; rendered 2026-09-08T07:15:13Z in 394.7 s. Three budgets bind this frame: props capped at 1,253,543 triangles, kit at 1,239,325, and the agent budget at 1,125,000, which dropped a further 630 people and 212 vehicles the simulation had in range. 90 curb ramps inside the prop radius are recorded as built elsewhere, cut into the pavement mesh rather than placed as props (J21).

**Verdict - the canyon reads as a Lower Manhattan alley and the exposure is honest, but the shopfronts are the thing to fix first: a single self-lit white fascia band runs the whole length of both walls at a quarter to two on an April afternoon, carrying the identical black arrow glyph on every panel, and it is the brightest thing in the picture.**

## What matches

* Both halves are a brick canyon seen along its length: masonry closing on both sides and rising past the eye, red-brown brick on the right-hand side in each, the view running away between them. Nothing in the render contradicts the photograph on the scale of the block.
* All six building tiles that touch this frame are present, with no missing shell and no LOD substitution, and the pavement layer dropped none of its 2,005 polygons.
* The camera stands on the photograph's own EXIF GPS, 20 m from the item's recorded viewpoint, so both halves start from the same place even though the heading does not come from the image.
* The crowd is simulation output rather than dressing. Three pedestrians stand together at the left wall in the middle distance at credible height and spacing, out of 377 people and 89 vehicles taken from one frame of the running simulation.
* A red hydrant sits on the paving at the right size and colour, one of 53 within the 250 m prop radius, and the scaffold shed spanning the street in the middle distance has its soffit strip lights modelled.
* Both of today's changes hold up under inspection. The saloon standing up the block has nothing beneath its rear axle: the imported bone display sphere of J44 is gone. The 90 surveyed curb ramps here are in the pavement mesh rather than the prop table (J21) - though none of them is in this view, which is a kerbless stretch, so what this sheet shows is the counter and not the geometry.
* The exposure is not flattered. The alley is in shade under a 58.6 deg sun, the transform is Filmic at +0.00 stops, and a frame mean of 0.2486 with sd 0.1501 is what that actually looks like. The photograph's camera metered this alley and opened up for it; the render answers a different question and does not pretend otherwise.

## What does not match

* **The two frames are not aimed the same way, and the sheet warns of it before you look.** The photograph is tilted steeply up: its verticals converge and most of its area is upper storeys and blown-white sky. The render's axis is level by rule, so most of its area is ground. These halves can be compared on street width, storey height and material, and not on composition (I7).
* The render's paved space is visibly wider than the reference's alley, with a grey kerb and a dark asphalt carriageway running away on the right. The reference block is kerbless and filled edge to edge with market tents. The 7.2 m the clearance rule moved the camera is part of this: that rule constrains a narrow cone about the axis, not the frame (J47).
* A dark saloon stands in the middle of the block. The reference has no traffic in it at all.
* The lit shopfront fascia is one unbroken white band on grey pilasters, running the full length of both walls at a single height, with the same black arrow glyph on every panel. The reference's shopfronts are individually dark, with a red awning, a projecting bracket lamp, "The DUBLINER" in gold on black and a red neon telephone number.
* There is no glass and no door anywhere in view. Under the fascia the right-hand wall is blank brick panel between pilasters, although the kit counts 289 storefronts, 66 door entries and 53 storefront interiors within its radius - and only 6,309 of the 13,894 kit pieces in range were drawn before the triangle budget ran out, which is part of why those walls are blank.
* The tall right-hand facade carries its windows as flat dark dashes with no frame, no sill, no reveal and no depth. The reference's blocks carry framed sash windows with maroon joinery, stone sills, iron balconies, a full-height fire escape and a slated mansard with dormers under a copper cornice. Six fire-escape kit pieces are counted in range and neither wall in view has one (A2).
* Irregular green blocks are stuck flat to the left wall at first-floor level - five vegetation kit pieces, reading at this range as pixelated moss, and answering to nothing in the photograph.
* Stone Street's defining surface, its Belgian block paving, is a flat untextured grey plane, and the near foreground shows that plane's triangulation as broad facets.
* The street's other defining feature is absent: the tables, chairs, umbrellas and heaters, and here the market tents that fill the reference's lower edge.
* The photograph is overcast, its sky clipped to featureless white with no shadow anywhere in it; the render is a clear Nishita sky with a hard high sun. EXIF gives the instant, not the weather.
* The corridor closes. The reference sees down the canyon to a white classical tower, a glass slab and a peach brick tower; the render's only sky is a narrow neutral slot at the top centre, and none of the 12 landmark models the caption counts is identifiable anywhere in the picture. There are also no bicycles: the 21 cyclists, e-bikes and pedicabs in range were dropped because the fleet exports those bodies without a rider.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the photograph is tilted up, the render is level | the pitch rule keeps the optical axis level so proportion stays comparable; the photographer's own tilt is not reproduced | reference |
| heading is the block's axis, not the photograph's | nothing in the file metadata gives a camera heading (I7) | reference |
| camera 7.2 m off the recorded viewpoint, into a wider kerbed space | the clearance rule moved it because the recorded azimuth was closed off 11 m ahead; the rule measures a cone, not the frame (J47) | verification |
| a saloon standing in a pedestrian block | vehicles are placed on whatever the planimetric data calls carriageway; 13 were dropped for not being on one | data |
| unbroken lit fascia in daylight | the emissive fascia band was calibrated on the Times Square night and day frames and applied unchanged to a shaded alley (B15) | material |
| the same arrow glyph on every fascia panel | no real business name exists for these lots, so the band carries generic content (B4) | data |
| no glass, no doors on the near runs | the kit's storefront and window pieces carry no glazing material, and the pieces on the near wall were not drawn | material |
| windows as flat dashes; no sills, balconies or fire escape | facade pattern, material and trim are inferred from a rule table rather than observed (A2) | geometry |
| green blocks on the left wall | the vegetation kit piece resolves at this range as a flat blocky panel | geometry |
| no cobbles, faceted grey ground | pavement polygons carry a kind and a base colour with no texture map, the same omission J40 records for the open-space surfaces | material |
| no tables, chairs, umbrellas or market tents | no dataset carries outdoor restaurant furniture or temporary stalls | data |
| no bicycles | the fleet exports cyclist, e-bike and pedicab bodies without a rider, so the 21 in range were dropped rather than drawn | data |
| clear sky against an overcast photograph | the sun is placed from the EXIF instant; nothing joins weather to that instant and the Nishita sky has no cloud layer | data |
| nearly half the kit in range not drawn | the 4.5 M triangle budget is spent before the kit finishes; the cap is recorded on the sheet | budget |
| 630 people and 212 vehicles dropped | the 1,125,000-triangle agent budget | budget |
| "12 landmarks" counted where none is visible | a true count of the scene offered where a reader reads the picture, the same shape as I17 and J49 | reporting |
