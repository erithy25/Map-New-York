# Tenement with fire escapes (East Village / Lower East Side)

`street_tenement_fire_escapes_les` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Lower East Side March 2023 054.jpg by Kidfly182, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2023-03-24 11:49:44, 1920x1440. [Commons page](https://commons.wikimedia.org/wiki/File:Lower_East_Side_March_2023_054.jpg) — camera GPS on the file, viewpoint confidence **low**. A close upward view of a corner tenement's chamfered angle: tan brick with heavy painted stone window surrounds, oval cartouche panels between the upper floors, a bracketed cornice, a wooden water tower on its steel frame against the sky, a window air-conditioner, and paint peeling off the stonework in sheets.

**Camera** — 40.720008, -73.988472 (NYC_TM -3251, 2223) at z 11.782 m NAVD88, a 1.6 m standing eye over terrain read at 10.182 m — the 10th percentile of 113 samples within 12.0 m, whose range is 10.16 to 10.58 | azimuth 29.0°, pitch 0.0° | 35 mm on 36 mm (54.432° horizontal) | 1208x906. The camera stands on *"this photograph's own EXIF camera GPS (40.72001, -73.98847), 19 m from the item's recorded viewpoint -- the position the picture was taken from"*, and it was **not moved**: the view azimuth is clear for **96 m**, the nearest built thing is `t_-4_2_tan_brick` **19.8 m** away, and no simulated agent stands within 60 m. This is one of the small number of sheets in the pass where the camera stands on the photographer's fix and the clearance walk had nothing to correct. The axis is level and there is no probe, no sightline and no visible fraction, because the item names no point subject.

**Sun** — azimuth 152.6°, elevation 47.5° at 2023-03-24T11:49:44-04:00, from the photograph's own EXIF DateTimeOriginal; 878 W/m² direct normal, Nishita sky, Filmic, **+2.40 stops**. Metered: **2.396 stops** on a linear median of **0.034198** against a physical rule of 0.0. 24 March is inside the leaf-off window, and the render's one street tree is bare.

## Verdict — the render has the fire escapes and the photograph does not, and the ornament runs the other way

**The sheet is named for fire escapes and the reference has none in it.** The chooser took a portrait of a corner tenement's chamfered angle — a good photograph of a Lower East Side building, and a photograph of the one elevation on that corner without an escape on it. The render has **153 fire escapes** placed and several of them are the most conspicuous thing in its picture, running in zigzags down the brick flank on the right. On the item's own terms the right-hand half is the better illustration, which happens on perhaps a dozen sheets in this pass and is worth saying when it does.

**What the photograph has and the render cannot is the ornament and the age.** The reference's corner carries moulded stone window heads, oval cartouches between the floors, a bracketed cornice, and paint failing in sheets across the stonework. The render's blocks carry **81 cornices, 74 quoins, 41 string courses and 352 window accessories** across 4,266 kit pieces, and they are clean, flat and repeated: the kit has a cornice but not a cartouche, a string course but not a moulded architrave, and nothing anywhere in this build weathers. That is the honest difference between a kit assembled from facade classes and a building photographed at 130 years old.

**The water tower is modelled and there are eleven of them.** The photograph's most memorable object is the rooftop tank on its frame; the kit places `water_tower` eleven times on this block, so the type is there even where this particular frame does not put one against the sky.

**And the window air-conditioner is modelled too.** The kit carries five of them in its `window_accessory` category — three sizes of sash unit, a bracket and a through-wall sleeve — and **17,858 of this tile's 17,891 window accessories are one of them**. This scene drew **352**. At the 19.8 m the nearest building stands from the lens, `acc_ac_window_medium` is 0.568 m across and subtends **1.644°**, or **37 pixels**, so where they fall in frame they are plainly visible.

**Tone agrees almost exactly and colour does not.** The exposure gap is **-0.061 stops** and the medians are within two per cent (p50 **0.981**), which for a frame developed 2.396 stops is a good result. Contrast is **0.878** and chroma **1.305**: the render carries a third more colour than the photograph, and the reason is in both pictures — the reference is one tan wall against a white sky, and the render has green awnings, red brick, a bare tree, and an apple-green car.

**That car is a boro taxi, and it is in the wrong borough half.** `agents.py` records the substitution honestly — *"the fleet table names a RAV4 for the green Street Hail Livery and the only green SHL body exported is a Camry, so the livery is right and the body is one class larger in plan and one class lower"* — so the colour is correct and the shape is a class out. What is wrong is that a Street Hail Livery cab may not take a street hail below 96th Street in Manhattan, and Orchard at Rivington is a long way below it. Two of this frame's 69 vehicles are boro taxis (J105).

**And the traffic is otherwise one class.** 49 of the 69 vehicles are sedans, with 12 SUVs, 6 yellow cabs and the 2 boro taxis, and **no truck, no van, no bus and no cyclist at all** on a Lower East Side street at 11:49 on a Friday. Six cyclists, e-bikes and pedicabs were dropped because the fleet exports those bodies without a rider.

**The props budget took two thirds of the street.** 1,156 placed against **2,000 dropped**, of which **1,968 are tree rows**, on a 1,183,590-triangle cap. What survives is 377 trees, 272 Citi Bike docks, 137 cooling towers, 137 manholes, 86 hydrants, 84 street lamps, 8 subway entrances, 6 steam vents and 2 vent grates — a fair Lower East Side inventory. The kit was cut harder still: **4,266 pieces of 13,729 in range**, so 9,463 were dropped.

**The pavement is complete and heavily marked**: 33,780 polygons with 17,356 white markings, 5,187 roadbed, 5,035 sidewalk, 3,840 curb, 961 crosswalk and 873 median, **none dropped**, and the continental crosswalk across the near junction is the clearest one read this round.

**The ground is close to right.** Of 157 park-ground samples within 150 m, an under-fraction of **0.0191** puts three below the terrain, with a median of **+0.13 m** and a worst case of **-0.094 m**; beyond 400 m, where the grid coarsens to 40.0 m, 23 per cent of 1,731 sit under it.

## What matches

* **The fire escapes are there** — 153 of them, and prominent in the frame, which is what the item asks for.
* **The camera stands on the photographer's own GPS fix** and needed no correction: 96 m of clear view, nearest building 19.8 m.
* **Tone agrees to 0.061 stops** with medians within two per cent.
* **The building type is right**: four- and five-storey brick tenements with retail at grade, cornices, quoins and string courses over 4 complete building tiles.
* **The water tower type is modelled**, eleven times on this block.
* **352 window air-conditioners placed**, 37 pixels wide at the nearest building.
* **The trees are bare**, correct for 24 March.
* **The pavement is complete**: 33,780 polygons, none dropped, with a full continental crosswalk.
* **Three of 157 near park-ground samples sit under the terrain**, an under-fraction of 0.0191.
* **The boro taxi's livery is right and the substitution is recorded**, body class and all.

## What does not match

* **The reference has no fire escape in it**, on the sheet named for them.
* **No cartouches, no moulded window heads, no bracketed enrichment**: the kit has a cornice and a string course and no ornament between them.
* **Nothing is old.** No peeling paint, no patched brick, no soot, no repair — the reference's subject is largely its own age.
* **Chroma 1.305**: the render carries a third more colour than a photograph of one tan wall.
* **Two boro taxis below 96th Street** (J105), and the greener of them is the brightest object in the frame.
* **No truck, no van, no bus and no cyclist** among 69 vehicles.
* **Two thirds of the props dropped** — 2,000 of them, of which 1,968 are tree rows — and 9,463 of 13,729 kit pieces.
* **No signage of any kind** (J110).
* **No shopfront lettering, no awning text, no address numbers** anywhere.

## Measured for this assessment

| figure | where it comes from |
|---|---|
| the green car is a boro taxi and its substitution is recorded | the `boro_taxi` entry of the class table in `blender/verify/agents.py`, whose note reads "the fleet table names a RAV4 for the green Street Hail Livery and the only green SHL body exported is a Camry" |
| 4,266 kit pieces placed of 13,729 in range leaves 9,463 dropped | the sum of the record's `scene.kit.per_category`, whose `total` is null, against `records_in_range` |
| 1,156 props placed against 2,000 dropped is two thirds of what the scene had in range | the record's `props.placed` and `props.dropped_for_budget` |
| the kit has five window air-conditioner assets and 17,858 of this tile's 17,891 window accessories are one of them | the `window_accessory` entries of `data/processed/kit_catalog.json`, counted against the `kit_id` column of `data/processed/tiles/t_-4_2/kit_placements.bin` |
| `acc_ac_window_medium` is 0.568 m across and subtends 1.644 deg at 19.8 m, 37 pixels on a 1208-pixel frame of 54.432 deg | accessor bounds of `blender_out/kit/facade/acc_ac_window_medium.glb` against the record's own clearance distance and frame |
| 24 March is inside the leaf-off window | the `leaf_off` rule in `blender/verify/render_sheets.py` (J97) |

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the reference has no fire escape | nothing tests what a photograph is a picture of, and this item names no subject (J71); the render happens to answer the brief better than its own reference | **verification — open, and harmless here** |
| no cartouches or moulded heads | the kit is assembled from facade classes and carries a cornice, a string course, a quoin and a window accessory; there is no ornament vocabulary below that | content — declared, and the limit of the kit |
| nothing is weathered | no wear, patina, soot or repair layer exists anywhere in this build | content — open, no source |
| chroma 1.305 | one tan wall under a white sky against a street with awnings, brick and a green cab | reference — the pairing, not the render |
| two boro taxis below 96th Street | `TrafficSim::sampleClass` splits the taxi share 70/30 with no geography (J105) | **runtime — open** |
| no truck, van, bus or cyclist among 69 vehicles | the class sampler's non-taxi remainder is 55 per cent sedan and 30 per cent SUV, so a 69-vehicle draw is mostly those two; cyclists are exported without a rider and dropped | **runtime — open** |
| two thirds of props and two thirds of kit dropped | a 1,183,590-triangle prop cap and a 1,114,905-triangle kit cap against every prop and all 13,729 kit records in range | performance — declared |
| no signage or lettering | the verification renderer never reads the sign or signal export, and no lettering exists on any surface in this build (J110) | **verification — open** |
