# Bronx drive-through: Grand Concourse Art Deco apartments

`drive_bronx_grand_concourse` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Dollar Savings Bank of New York headquarters building, Grand Concourse & East Fordham Road, The Bronx, New York.jpg by Deansfa, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2022-10-09 12:16:14, 1920x2560. [Commons page](https://commons.wikimedia.org/wiki/File:Dollar_Savings_Bank_of_New_York_headquarters_building,_Grand_Concourse_%26_East_Fordham_Road,_The_Bronx,_New_York.jpg)

**Camera** — camera 40.83200, -73.91860 (NYC_TM 2644, 14663) z 31.6 m NAVD88 | azimuth 25.0deg pitch +0.0deg | 35 mm on 36 mm (42.2deg horizontal, 54.4deg vertical, portrait) | 904x1206. Moved 4.9 m onto the nearest roadbed polygon because the recorded eye point was inside `t_2_14_roof_membrane`.

**Sun** — azimuth 171.0°, elevation 42.4° at 2022-10-09T12:16:14-04:00 (EXIF DateTimeOriginal).

**In frame** — 6/6 building tiles (323,032 tris), 2 landmarks (Yankee Stadium, Bronx County Courthouse), 2,433 pavement polygons, 407 props, 5,695 kit pieces, 89 vehicles, 307 people; **4,500,226 triangles**, which is the scene's 4.5 M ceiling reached exactly. Props capped at 407 of 872, kit capped at 5,695. Frame mean 0.2395, sd 0.1719.

**Verdict — this sheet compares nothing, for two independent reasons, and the second one is new. Its reference is a building 3.9 km away on a different part of the Concourse, which was already recorded. And the right half of the render is a building face about five metres from the lens, because the clearance probe that declared the view "clear for 60 m" looks at 5 % of the frame**

## Why the render shows a wall

The recorded eye point was inside a roof membrane, so the camera was moved 4.9 m onto the nearest
real roadbed polygon and the axis re-checked: `view_m: 60.0`, `nearest_obstruction_m: 20.0`. Both
numbers are true. Looking up the Concourse on 25°, the axis is clear.

What the caption then says is "the nearest solid thing in the view cone", and the cone is
`_nearest_opaque`'s default **half-angle of 6°**. This frame is 42.2° wide and 54.4° high, so the
probe covers 28 % of its width, 22 % of its height and **5.2 % of its solid angle**. The building
face that fills the right of the picture — close enough to read its air-conditioners, with a
pedestrian's back at about 3.9 m in front of it — lies between +6° and +21° off-axis, which is
exactly where the probe does not look. Recorded as J47.

So the clearance number is not wrong; it answers a narrower question than the caption puts it to.
The camera is standing on a roadbed hard against a block face, and the picture is mostly that face.

## What the left third does show, and it is worth reading

The part of the frame that is not wall is the strongest evidence on this sheet:

* A red-brick block with a continuous green awning band recedes up the left, with street trees in
  full October canopy at the kerb — **208 of the 407 props are trees**, and the props are capped at
  407 of 872 in range by a 1,356,090-triangle budget.
* The street furniture the Concourse actually carries is placed and countable: 63 street lamps,
  61 manholes, 29 hydrants, **27 subway vent grates and 2 subway entrances**, 2 bus shelters,
  3 bus-stop signs, 2 Citi Bike docks, 10 rooftop cooling towers.
* 2,433 pavement polygons — 923 curb, 601 crosswalk, 408 roadbed, 251 sidewalk, 143 median,
  88 parking-lot, 19 plaza. The Concourse's median is in the data and in the frame.
* 5,695 kit pieces including 4,052 windows, 453 window accessories, **213 scaffold pieces**,
  137 quoins, 112 string courses, 83 cornices, 83 parapets and 59 fire escapes. The scaffold count
  is high because this stretch of the Concourse is genuinely sheathed in it.
* Yankee Stadium and the Bronx County Courthouse are both loaded, though neither is in this frame.
* A yellow taxi and a white van stand at the far end of the street; 89 vehicles and 307 people are
  placed — 48 sedans, 18 SUVs, 10 taxis, 4 vans, 3 MTA buses, 3 black cars, 2 box trucks, 1 boro
  taxi.

## What does not match

* **The reference is 3.9 km away.** The photograph is the Dollar Savings Bank at East Fordham Road;
  the viewpoint is the Concourse at East 165th Street. Commons has essentially nothing free looking
  along the boulevard near 165th, and the item names no subject from which a bearing could be taken.
  This is the third fault recorded under I12 and it is unchanged.
* **The frame is half wall** (J47, above).
* **The scene is at its ceiling.** 4,500,226 triangles is the 4.5 M budget reached exactly, with the
  props capped at 407 of 872 and the kit capped as well. What is missing from the far end of the
  street is missing because the budget ran out before it got there, not because the data is absent.
* 825 people and 77 vehicles the simulation had in range were dropped at the 1,125,000-triangle
  agent budget, 705 more people and 190 more vehicles for being outside the radius, 127 for standing
  in the carriageway without crossing, 52 for not being on a walkable surface, 11 vehicles for being
  a body with no rider, 6 for not being on a carriageway.
* The Art Deco the item is named for is not visible: no setbacks, no banding, no brickwork relief,
  no casement rhythm. The blocks in frame are flat planes with window openings and no reveal.
* The roadway is untextured, as everywhere.
* `curb_ramp: 81` still appears under `unmapped_kinds`; those rows are built into the pavement and
  the label is stale by minutes (the resolver learned to say `built_elsewhere` after this render).

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the reference is 3.9 km from the viewpoint | Commons has no free photograph looking along the Concourse near 165th Street, and the item names no subject | reference |
| the right half of the frame is a wall five metres away | the clearance probe is a 6° cone in a 42.2° frame and reports its answer as the frame's (J47) | verification |
| props and kit both capped | 4.5 M triangles reached; 465 props and the far end of the kit never placed | budget |
| no Art Deco relief, setbacks or banding | building shells carry massing and a flat window grid; the kit has no Deco vocabulary | geometry |
| untextured roadway | pavement is a flat colour per kind with no surface texture | material |
| `curb_ramp: 81` shown as unmapped | rendered minutes before the resolver said `built_elsewhere`; the ramps are in the pavement | reporting |
