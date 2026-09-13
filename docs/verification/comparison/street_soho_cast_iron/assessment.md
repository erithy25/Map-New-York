# SoHo cast-iron block

`street_soho_cast_iron` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:SoHo, Manhattan (6).jpg, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2026-04-20 10:49:21, 1920x2560. [Commons page](https://commons.wikimedia.org/wiki/File:SoHo,_Manhattan_(6).jpg) — viewpoint confidence **low**, and the author field is the uploader's own credit line, *"This magnificent photo was taken by His Imperial Majesty, an Emperor of Emperors Feel free to use my photos, but please mention me as the author"*, which the sheet reproduces verbatim as the attribution because that is what the file says. A portrait close-up of a brick party wall at the end of a building: wheatpasted posters over a red ground, an ADHD throw-up in orange bubble letters, a flyer reading WHAT THE FUCK IS MATCHA, an Alexander Romero print, white tags across the stone base, a stencilled dog at pavement level, a downpipe, and a barred window at the top left. **There is no cast iron in it.**

**Camera** — 40.7218, -74.002 (NYC_TM -4393, 2422) at z 5.921 m NAVD88, a 1.6 m standing eye over terrain read at 4.321 m — the 10th percentile of 113 samples within 12.0 m, whose range is 3.7 to 4.94 | azimuth 29.0°, pitch 0.0° | 35 mm on 36 mm, **portrait**, 42.163° horizontal by 54.432° on the long side | 904x1206, shaped to the reference's own 3:4. The camera is on the item's recorded viewpoint, Greene Street at Grand Street, because *"this photograph's own EXIF GPS is 57 m away, but the eye point there is inside `t_-5_2_roof_membrane` (a ray straight up from the eye point hits its roof), while the recorded viewpoint is in open air"* — the third sheet in the pass whose origin was decided by that test (J115). The camera was **not moved**, and the record's account of what is around it is the thing to read twice, below.

**Sun** — azimuth 127.6°, elevation 50.0° at 2026-04-20T10:49:21-04:00, from the photograph's own EXIF DateTimeOriginal; 888 W/m² direct normal, Nishita sky, Filmic, **+6.00 stops**, clamped. The record says so: *"the frame wanted +6.28 stops and was held at +6.00: a scene this far from a photographable level is not developed into a picture of one."* The physical rule asks for **0.0** — a 50° April Sun needs no correction at all — and the frame still needed six stops, because the camera is standing under something.

## Verdict — neither half shows a cast-iron facade, and the record says the frame is clear when scaffolding fills it

**The reference is a photograph of paste-ups on a brick wall.** SoHo's cast-iron district is the largest concentration of cast-iron architecture in the world and the item asks for a block of it: Corinthian columns in painted iron, arched bays, bracketed cornices, vault lights in the sidewalk. What the fetch kept and the chooser took is a portrait study of a graffitied brick flank, with no column, no cornice and no iron in the frame. The item names no subject, so nothing in the pipeline can notice (J71).

**The render does not show one either, because pipe scaffolding fills it.** The frame is a colonnade of steel standards with a boarded deck overhead, running away up the street: **27 bays of `scaffold_pipe_bay`**, each 2.28 by 1.06 m in plan and **7.01 m tall** in galvanised steel and timber. Whatever cast iron stands on Greene Street is behind it.

**And the clearance record does not mention any of that.** Its note reads *"the viewpoint is in open air on the ground and the camera was not moved; the nearest built thing in the frame is `t_-5_2_stone_rubble` 11.2 m away … and the view azimuth is clear for 150 m."* Across all 171 records the clearance test names a **prop 68 times, a tile shell 43 times and a landmark 32 times, and a kit piece not once** — so the several thousand kit objects a scene places are invisible to the check that decides whether a camera can see. Here the consequence is total: the sheet reports 150 m of clear view through a scaffold two metres from the lens, and the six stops of development it needed are the measure of the shade that scaffold casts.

**The same clearance block contradicts itself about the crowd.** Its note says *"the nearest simulated agent is `agent_ped_1912.0` 1.2 m away"*; its own fields say `nearest_agent: agent_ped_1152.0` at **36.3 m**, annotated `nearest_agent_measured: "after the cull over the observer"`. Two different pedestrians, thirty-five metres apart, in one record — and it is the note that the sheet prints under the picture. **Nine records in the pass disagree with themselves this way**, the note always naming something nearer, between 0.1 and 4.7 m, than the field.

**What the two halves do share is their tone, almost exactly.** The exposure gap is **0.051 stops** — the **seventh closest of the 171 measured sheets** — with a p50 ratio of **1.017** and a mean ratio of 1.121. Both halves are a shaded surface a metre or two from the lens on a bright spring morning, so both meter the same way, and the six-stop lift lands the render on the photograph's own median almost precisely. The two ratios that separate them are contrast, **1.158×**, and chroma, **0.318**: the photograph is red poster, orange letters, blue print and brown brick, and the render is grey steel and pale concrete.

**Two things this sheet gets right about SoHo.** The street-furniture reads correctly for the district — **9 steam vents, 51 subway vent grates, 9 subway entrances, 2 subway emergency exits, 301 Citi Bike docks and 302 cooling towers** — and the pavement is the most heavily marked of any sheet read this round: **35,381 polygons with 20,228 white markings, 1,132 crosswalk and 3,934 curb, none dropped**. **Only 122 trees**, which is right: Greene Street has almost none.

**The kit that would have made the block is mostly not there.** 3,237 pieces were placed of **15,103 in range**, capped at 931,019 triangles — so **11,866 were dropped**, four in five. Among those that survived are **156 pilasters**, which is the nearest thing this build has to a cast-iron column, and **235 fire escapes**, which SoHo does have. Props fared no better: 1,202 placed and **2,216 dropped**, including 2,013 tree rows.

**The camera never had a subject to protect it.** No probe, no sightline, no visible fraction, and a level axis, because the item names no point subject. Two landmark models are in the scene and both are more than 1.8 km away, neither inside the 42.2° frame.

## What matches

* **The tone agrees to 0.051 stops**, the seventh closest of the 171 measured sheets, with a p50 ratio of 1.017.
* **The street-furniture vocabulary is SoHo's**: steam vents, vent grates, subway entrances and emergency exits, Citi Bike docks and roof cooling towers.
* **The pavement is fully marked**: 35,381 polygons, 20,228 of them white markings, none dropped.
* **122 trees**, which is the right order for Greene Street.
* **235 fire escapes and 156 pilasters** on the surrounding blocks.
* **Building tiles complete**: 8 of 8, 477,838 triangles, none missing, none LOD-substituted.
* **The clamp is declared**, with the number it was held back from.
* **The frame is portrait**, shaped to the reference's own 3:4.

## What does not match

* **Neither half shows a cast-iron facade**, on the sheet named for one.
* **The reference is a wall of paste-ups and tags**; the render has no poster, no sticker, no tag and no graffiti anywhere in this build.
* **Pipe scaffolding fills the render**: 27 bays, 7.01 m tall, between the lens and the block.
* **The clearance record calls that open air** and reports 150 m of clear view; kit is named as the nearest built thing on none of the 171 records.
* **The clearance note and its own fields name different nearest agents**, 1.2 m against 36.3 m, and the note is what the sheet prints.
* **Six stops of development, clamped from 6.28**, on a scene the physical rule says needs none.
* **Chroma 0.318**: the photograph is a poster wall and the render is grey steel.
* **Four in five kit pieces dropped** — 11,866 of 15,103 — and two in three props, so the block's own detail is mostly absent behind the scaffold.
* **No signage of any kind** (J110).
* **Five boro taxis in SoHo**, inside the street-hail exclusion zone (J105).
* **No park-ground samples within 150 m**, so nothing local was measured.

## Measured for this assessment

| figure | where it comes from |
|---|---|
| the scaffold bay is 2.28 by 1.06 m in plan and 7.01 m tall, 1,347 triangles, in galvanised steel and timber | accessor bounds of `blender_out/kit/facade/scaffold_pipe_bay.glb`, the only asset in the `scaffold` category of `data/processed/kit_catalog.json`, against the record's own count of 27 placed |
| the clearance test names a prop 68 times, a tile shell 43 times and a landmark 32 times across the pass, and a kit piece not once | the `clearance.nearest_obstruction` of every record in the pass, grouped by the object's name prefix |
| the structures and landmarks in this scene are all more than 800 m away, so the frame's colonnade can only be kit | the nearest edge of every node in the three imported `tile_structures.glb` files against the camera coordinate, and the record's own two landmark distances |
| nine records disagree with themselves about the nearest agent, the note always naming something between 0.1 and 4.7 m and the field something further | parsing the `clearance.note` of every record against its `nearest_agent` and `nearest_agent_m` fields |
| the exposure gap of 0.051 stops is the seventh closest of the 171 measured sheets | the absolute `render_over_reference.exposure_offset_stops` of every `frame_stats.json` in the pass, ranked |
| 3,237 kit pieces placed of 15,103 in range leaves 11,866 dropped | the record's `scene.kit.placed` and `records_in_range` |
| 20 April is outside the leaf-off window | the `leaf_off` rule in `blender/verify/render_sheets.py` (J97) |

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the reference has no cast iron in it | nothing tests what a photograph is a picture of, and this item names no subject to test against (J71) | **verification — open** |
| no graffiti, posters, stickers or tags | no decal, poster or weathering layer exists anywhere in this build; the word graffiti appears in no Python file in the repository | content — open, no source |
| scaffolding fills the frame | the kit places sidewalk scaffolding from the facade data, correctly, and the camera stands under it | not a fault in itself |
| the record calls the frame clear | `clear_of_geometry` samples tile shells, landmark models, props and agents, and not kit; a scene may place thousands of kit objects and none of them can be the nearest built thing | **verification — open** |
| the note and the fields name different agents | the fields are measured after the cull of agents standing over the observer and the note is written before it; only the note reaches the sheet | **verification — open, and a one-line fix** |
| six stops of development on a 50 deg Sun | the camera stands in the shade of the scaffolding the clearance test cannot see (J83) | verification — consequent on the above |
| four in five kit pieces dropped | a 931,019-triangle cap against 15,103 records in a 177.2 m radius, which is what a SoHo block costs | performance — declared |
| no signage of any kind | the verification renderer never reads the sign or signal export (J110) | **verification — open** |
| five boro taxis in the exclusion zone | `TrafficSim::sampleClass` splits the taxi share with no geography (J105) | **runtime — open** |
| five of eight structures tiles have no file | the B13 remainder | data — open |
