# Lower Manhattan drive-through: Stone Street

`drive_lower_manhattan_stone_st` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Financial District Manhattan April 2022 008.jpg by Kidfly182, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2022-04-19 13:45:47, 1920x1440. [Commons page](https://commons.wikimedia.org/wiki/File:Financial_District_Manhattan_April_2022_008.jpg)

**Camera** — 40.7041, -74.0107 (NYC_TM -5133, 465) at z 4.0 m NAVD88 | azimuth 60.0°, pitch +0.0° | 35 mm on 36 mm (54.4° horizontal) | 1208x906.

**Sun** — azimuth 204.4°, elevation 58.6° at 2022-04-19T13:45:47-04:00 (EXIF DateTimeOriginal); 915.1 W/m² direct normal, sky at strength 0.0311, Filmic, +3.61 stops.

**In the scene**, within 740.2 m of the camera and not all of it in frame — 6 building tiles (86,646 tris), 12 landmark models of which **2 can fall inside the 54.4° frame**, 23,768 pavement polygons (8,502 white, 5,392 roadbed, 4,263 sidewalk, 3,443 curb, 987 plaza, 563 crosswalk, 393 median, 212 yellow, 13 parking lot), 1041 props of the 4,076 in range, 5,343 kit pieces, 89 vehicles and 380 people; 4,500,018 triangles. Ground mesh 88,180 triangles, 0 holes. 20 city surfaces are dressed from the shared photographic catalogue.

## Verdict — the same kind of alley on the same afternoon, but a level camera in a restaurant lane against a photograph aimed at the sky

**This sheet compares a street type, not a composition, and the record says so.** The item names no subject; its azimuth of **60.0°** is the street heading in `meta.json`, not read off the photograph (confidence medium), and the axis is level because there is nothing to aim at. The photograph is tilted steeply upward: its upper third is white overcast sky and no ground is in it — two event canopies, blue and red, cut its bottom edge. The render's top edge is brick and a distant pale facade between the two walls, no sky, and its lower half is floor.

**The place is the right place.** The camera stands on the photograph's own EXIF GPS, **20.2 m** from the item's recorded viewpoint, then walked **7.2 m** onto the nearest sidewalk polygon because that point was closed off 11 m ahead; from there the azimuth is clear for **60 m** and the nearest built thing is `t_-6_0_red_brick` at **11.2 m**, left at **-27.2°**. The Sun is at the photograph's EXIF second, elevation **58.6°** from **204.4°** — high, behind the camera's right shoulder — and the render shows it in one place only: the upper storeys of the right wall at the top right of the frame, hard shadows falling from every sill and reveal and a diagonal shadow line from something behind the camera across them; the near-left brick is a flat sky-lit face with no lit/shade split, and the tan building at the centre stands in shade, darker than the frame's median. The photograph, under overcast, has no shadow.

**The lighting is metered, not dim.** The frame was developed at **+3.61** stops where the physical rule alone would have granted **+0.00**: the linear median **0.014763** was placed at **0.18** (J83). That is under the +4 line at which the record calls a frame under-lit. The photographer's exposure sits **-1.342** stops from the same middle-grey convention, the render's at **0.245**; the median ratio of **1.689** is that exposure difference first, the pitch second, and only then the city.

**What the reader must not take from this sheet:** that the paving is right or wrong against the photograph (it shows none); that the towers over the rooftops are missing (Pier 17 at **789.2 m** and the Brooklyn Bridge at **1,227.8 m** cross the cone and are correctly hidden behind the walls); or that the clearance verdict describes the crowd. The clearance block reports `nearest_agent` null at a **20 m** probe, and three pedestrians stand on the left footway well inside that. J49 gave the record an agent reading; J54 re-took it "after the cull over the observer", the field this sheet carries. `culled_after_camera_move` says **1** pedestrian was removed, and the post-cull reading still reports nobody over a frame that draws three. The picture is right; the number is of a population other than the one drawn.

## What matches

* **The street type is the street type.** A narrow party-wall brick lane, shopfronts under awnings, an unmarked pedestrian surface, no traffic but one vehicle where the lane meets the cross street, a taller building closing the far end. The kit carries **238 storefronts**, **44 storefront interiors**, **56 entry doors**, **4,786 windows** and **93 window accessories** — the last visible as air-conditioner boxes in the upper openings, as in the photograph.
* **The instant is the photograph's own.** EXIF `DateTimeOriginal`, 19 April 2022, a Tuesday, and the crowd is drawn for a weekday. Nothing about the clock is assumed (contrast J80).
* **The colour is a match.** Chroma **0.0493** against **0.0469**, ratio **1.051**: both are grey pictures of brown brick, not J66's desaturated frame.
* **The shadow floor is not the J83 deficit.** p05 **0.1355** against **0.0832**: the render's darkest twentieth is brighter than the photograph's, the reverse of the floor shortfall J83 recorded across the pass; the record offers no cause beyond the two exposure choices.
* **The furniture is the right furniture**: a red hydrant at the left kerb, from **71** hydrants within **270.2 m**; shopfront emissives on under the awnings, per the daylight note.

## What does not match

* **The photograph is aimed up and the render is level.** Reference p95 **1.0**, blown sky, against render **0.6199**, a sunlit wall; standard deviation **0.3019** against **0.1642**, ratio **0.544**. The mean ratio **1.088** is pitch and exposure cancelling.
* **Overcast against clear sky.** The record carries the instant and no weather: a clear-sky Sun at **915.1 W/m²**, sky at **0.0311**, hard-edged on the upper storeys of the right wall, the rest of the lane in shade.
* **The brick is the wrong brick.** The photograph's left building is blackened dark-brown brick with plum-red frames; the render's nearest tile is `t_-6_0_red_brick`, bright orange-red from `Bricks082A` at target albedo **0.2333**, and every building of that class is one scan at different brightnesses (J66, second half); the chromas agree because both are low, the hues do not.
* **The facades are far plainer.** The reference carries iron balconies, fire escapes, a stone pediment over the Dubliner's door, wall lanterns, a slate mansard with a dormer, a red awning, lettered signs and string-light cables across the lane. The render is punched windows in flat brick with grey pilasters: **18** cornices, **20** pilasters and **8** string courses in the whole scene, no fire-escape category in the kit, one green awning material at every bay on both sides.
* **Green slabs on the left shopfront.** The kit places **5** vegetation pieces; those in frame are blocky green panels on the brick at head height, not planters or ivy.
* **The floor is one pale surface with no kerb, and the left building floats above it.** The floor is pavement, not terrain: sidewalk, plaza and curb polygons are all dressed `concrete_sidewalk` (`Concrete036`, target albedo **0.3317**), so footway and lane are one texture and no kerb line can appear. The dark band at the foot of the right wall and two slivers in mid-distance are roadbed asphalt (target albedo **0.056**) or undressed terrain showing where surfaces cross. The pavement is draped on a heightmap that within **12 m** spans **-0.55** to **3.64 m** over **113** samples; the camera was set at the 10th percentile, **2.36 m**, against **3.39 m** at its own point. So the floor falls steeply left of the pedestrians while the near-left shell's base is one flat plane, with a dark void beneath it. This is not J64, which records the coarse-fan burial as fixed and the pavement re-measured above the terrain; no register row covers a shell base held flat over graded ground.
* **The lane is emptier than the photograph's.** The photograph's roadway holds two event canopies; the render's holds nobody. **517** pedestrians were dropped for standing in the carriageway without crossing — on a pedestrianised block, that is where the people are — and **647** pedestrians and **213** vehicles for the triangle budget.
* **Trees and point props.** **137** of **211** trees are species-substituted, **210** scaled at a mean of **0.874**, **1** outside the band (J70); none is in either half. **6** artworks, **5** memorials, **4** miscellaneous structures and **1** vending machine have no asset (J23).

## Cause of each gap

| gap | cause | class |
|---|---|---|
| aimed up against level | no subject, so the axis is level (stated on the sheet); the reference tilts to the towers | reference + stated choice |
| overcast against clear sky | the record takes the instant and models a clear sky; it has no weather field | reference |
| the brick is the wrong brick | one scan per facade class, scaled by one scalar; the class varies in tone, never hue | data — **DEVIATIONS J66** |
| plainer facades | extruded footprint; balconies, fire escapes, pediments, mansards and signs are not in the kit | geometry |
| green slabs on the shopfront | the vegetation kit piece is a box and is placed as one | geometry |
| one pale floor with no kerb; a floating ground floor; slivers on the surface | one `concrete_sidewalk` dressing for sidewalk, plaza and curb; pavement on a heightmap with a four-metre spread inside 12 m under a flat shell base; not J64 (recorded fixed); no register row covers the floating shell | geometry (no J-row) |
| the lane is emptier than the photograph's | the carriageway cull removes the crowd a pedestrianised block holds; the budget takes the rest | stated choice + performance |
| three pedestrians inside the 20 m the probe reports clear | the J54 post-cull re-measurement (1 pedestrian removed) still reports no agent over a frame that draws three | verification — **DEVIATIONS J49**, **J54** |
| trees substituted and scaled; sixteen point props unplaced | no modelled species matched; those four prop kinds have no asset | data — **DEVIATIONS J70**, **J23** |
| the halves are not guaranteed to face the same way | the azimuth is the street heading from `meta.json` | — (not a gap) |
