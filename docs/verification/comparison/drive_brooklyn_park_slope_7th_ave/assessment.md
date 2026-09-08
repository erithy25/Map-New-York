# Brooklyn brownstone block: Park Slope, Seventh Avenue / Garfield Place

`drive_brooklyn_park_slope_7th_ave` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** - File:Park Slope - Brooklyn (55268725540).jpg by ajay_suresh, CC BY 4.0 (https://creativecommons.org/licenses/by/4.0), taken 2026-04-23 13:09, 1920x1080. [Commons page](https://commons.wikimedia.org/wiki/File:Park_Slope_-_Brooklyn_(55268725540).jpg)

**Camera** - camera 40.67233, -73.97706 (NYC_TM -2288, -3072) z 29.9 m NAVD88, a 1.6 m eye above a terrain surface measured at 28.309 m NAVD88 from 113 heightmap samples within 12.0 m | azimuth 32.4 deg pitch +0.0 deg | 35 mm on 36 mm (54.4 deg horizontal) | 1280x720. It looks at 32.4 deg because that is Seventh Avenue's own measured bearing, snapped to the street when the viewpoint was corrected today; the axis is level because the item names no subject to tilt towards, and the lens is the default 35 mm equivalent because nothing asked for anything else.

**Sun** - azimuth 187.7 deg, elevation 61.8 deg at 2026-04-23T13:09:00-04:00, from the photograph's own EXIF DateTimeOriginal to the minute, not an assumption.

**In frame** - 6 of 6 building tiles (492,134 triangles, none missing, none LOD-substituted); 2 landmarks, the Soldiers' and Sailors' Memorial Arch and the Central Library, neither visible in this frame; 1,741 pavement polygons within 720 m (701 curb, 406 crosswalk, 322 roadbed, 184 sidewalk, 109 median, 15 parking lot, 4 plaza), none dropped; 273 props of 762 rows in range, among them 167 trees, 39 street lamps and 14 hydrants, plus 28 curb ramps built as pavement rather than props; 3,751 kit pieces, including 2,123 windows, 302 storefronts, 99 fire escapes and 52 lit storefront interiors; 89 vehicles and 281 people; 4,272,206 triangles; ground mesh 211² at 2.0 m near and 40.0 m far, no holes. Two budgets bite: the 1,311,426-triangle prop budget caps the props at 273 of 762 and dropped 23 impostor cards, and the agent budget dropped 517 more people and 117 more vehicles. Frame mean 0.3622, standard deviation 0.1921, passed as usable.

**Verdict - the corrected viewpoint (J48) turns this sheet from a blank wall into a legible Seventh Avenue with awnings, trees, kerbs, ramps and a crowd, and the two things now worth an engineer's morning are the windowless brick above the shopfronts and a carriageway that renders as untextured grey patchwork with one pavement slab floating over it.**

## What matches

* The frame is a street. The viewpoint was corrected today from a point J48 records as 98 m from the crossing its own note names, and the azimuth snapped from 30.0 to the avenue's measured 32.4 deg. The clearance rule did not move the camera: the nearest solid thing in frame is `prop_lamp_cobra_davit_6` at 12.6 m and the axis is clear for 150 m against a 20 m floor.
* This is a shopping street and it looks like one. A continuous run of storefronts, awnings and lit soffits carries the left-hand block face, with fascia signs legible at "OPEN" and "RESTAURANT" - generic wording, as B4 says of 49,880 of them, but the right object in the right place at the right height.
* Street trees line both kerbs and close over the pavement, which is what Seventh Avenue does; 167 are placed within the 250 m prop radius.
* The kerb reads correctly along both sides, and the surveyed ramps are now geometry rather than a uniform lift: on the near left kerb the sidewalk slopes down and the kerb face pinches out to nothing, which is what a cut ramp looks like. 28 are built into this pavement (J21, closed).
* The city is populated. 281 people stand and walk on the pavements in varied clothing at LOD1 48 / LOD2 233, and of the 89 vehicles a rank of sedans, an SUV and a white box truck stands at the far kerb, where the reference also has one.
* J44 is genuinely gone: I looked at the middle-distance vehicles at pixel level and there is no untextured sphere under any of them.
* The roofline behind the trees carries stepped parapets, chimney stacks and cornices, air-conditioners and fire escapes hang at plausible floor levels, and the 61.8 deg midday sun throws short dappled tree shadows across the roadway as the reference's own shadows do.

## What does not match

* The photograph is a different corner. Its street sign reads "8 AV", its own EXIF GPS is 734 m from this camera - past the 250 m at which the sheet will take it as the same view, so it was rejected as mis-tagged - and the file's Commons categories name Eighth Avenue and 9th Street. The halves cannot be compared on composition, only on width, storey height and material, as the caption warns.
* No facade near enough to read carries a single window opening. The left block face above its awnings, the near right building, and the wall carrying two full fire escapes with balconies and ladders are blank brick, with nothing behind the escapes. 2,123 window pieces are placed within the kit's 120 m radius, so they exist in this scene and not on these elevations.
* The carriageway is unfinished. The near half breaks into large light and dark grey regions whose jagged edges follow triangle boundaries rather than any street feature, and one pale pavement slab ends in mid-road with a free edge and a soft dark band beneath it, so it reads as a plate laid on the road rather than a kerbed island.
* The road carries one white bar and nothing else. The reference has a yellow centre line, a ladder crosswalk, stop bars, patched asphalt and a manhole cover; here 406 crosswalk and 322 roadbed polygons produce flat grey with no texture and no markings near the camera.
* The near roadway is empty: no moving traffic and nothing parked at either near kerb, where the reference has cars nose to tail on both sides and two more waiting in the intersection.
* Nothing signals or names the street. No mast-arm signal, no pedestrian countdown, no street-name sign, no newsstand, no fire-alarm box, all of which are in the reference and three of which dominate its right third. No bicycles either: 20 cyclist, e-bike and pedicab bodies were dropped for having no rider.
* The foliage is the wrong season - full dark summer canopies against a reference of the same minute that is half-leafed pale yellow-green with a flowering pink tree behind the corner.
* One pedestrian on the right pavement carries a plain red box that intersects his torso.
* The sky is a clean gradient where the reference has light cloud, and the render's key is far lower: a frame mean of 0.3622 against a photograph bright end to end.
* The item is called a brownstone block and there is not a stoop in the frame. That is the avenue's doing rather than the render's, but a reader comparing name to picture will not know it.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| photograph is a different corner 734 m away | the chooser scored a Park Slope streetscape with no usable heading; the GPS was rejected, the image kept | reference |
| no window openings on any near facade | the facade class places sills, accessories and fire escapes but no window on these elevations; facades are inferred (A2) | geometry |
| fire escapes on blank brick | same class: the escape comes from the kit without the opening it serves | geometry |
| patchwork light and dark carriageway | polygon-boundary shading across the pavement and terrain surfaces; J17 records terrain still rising through the pavement over 0.0-0.15 % of it, the right shape for this but unmeasured on this tile | verification |
| pavement slab floating over the roadbed | a raised pavement polygon ends in a free edge instead of closing to a kerb face | geometry |
| no texture or markings on the road | pavement carries a kind and a base colour, not a texture; crosswalks are derived (C3) and the layer is from an earlier run (C7) | material |
| no signal, countdown, street sign, newsstand, fire-alarm box or bicycle | none of those kinds is placed in this scene, sign legends are MUTCD defaults where they exist (D6), and 20 cyclist bodies were dropped for having no rider | data |
| empty near roadway | 241 vehicles dropped outside 320 m and 117 to the triangle budget; no survivor is parked near the camera | budget |
| props drawn 273 of 762 | the 1,311,426-triangle prop budget, which also dropped 23 impostor cards | budget |
| summer canopies on an April frame | trees are procedural with no seasonal state (D6); 43 species substituted | data |
| red box intersecting a pedestrian | carried items are bevelled boxes (E5), and this one is not attached to its body | geometry |
| clear sky, low key | a Nishita sky with no cloud layer or haze | material |
| "brownstone block" names a retail avenue | the item's name and its viewpoint note describe two different things | reporting |
