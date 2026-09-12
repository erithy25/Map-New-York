# NYC traffic signals and pedestrian signals (close-ups)

`street_nyc_traffic_signals` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Countdown signal NYC walk symbol 1.jpg by Epicgenius, CC BY-SA 3.0 (https://creativecommons.org/licenses/by-sa/3.0), taken 2013-10-25 12:33:12, 1920x2571. [Commons page](https://commons.wikimedia.org/wiki/File:Countdown_signal_NYC_walk_symbol_1.jpg) — the photograph carries no camera GPS and its view direction was not derived from the image, so its viewpoint confidence is **low**. A Midtown corner in late-October light, and the photograph is entirely its subject: a signal standard carrying a three-section mast-arm head, a countdown pedestrian signal showing the walk symbol, a ONE WAY blade beneath it, a plane tree turning, parked cars and a cyclist on a continental crosswalk.

**Camera** — 40.755, -73.984 (NYC_TM -2871, 6108) at z 20.4 m NAVD88 | azimuth 0.0°, pitch 0.0° | 35 mm on 36 mm (42.0° horizontal, 54.4° on the long side, **portrait**) | 904x1210. This is one of **ten sheets in the pass rendered from this exact camera** — the same position, the same heading and the same 35 mm lens, each frame shaped to its own reference photograph so the horizontal field runs from 42.0° to 54.4° across the ten — each standing for a different object class and each lit at its own reference photograph's instant. The record is candid about what that means: *"This item names no subject and the reference photograph's own view direction was not derived from the image (confidence: low), so the two halves of this sheet are not guaranteed to face the same way -- compare them on street width, storey height and material, not on composition."* `subject_note` reads *"the item names no point subject"*, so there is no height probe, no sightline and no visible fraction on this record at all. The camera was **not moved**; the nearest built thing in the frame is `lm_c_times_square.0` **23.7 m** away and the view azimuth is clear for **37.2 m**. The ground under the lens reads 18.769 m NAVD88, the 10th percentile of 113 samples within 12.0 m.

**In the frame, in every one of the ten** — 4 building tiles (247,682 tris), 9 landmark models of which 2 fall inside the frame cone, 27,313 pavement polygons with 12,088 white markings and 620 crosswalk, **0 triangles of structures** with 4 tiles having no file, and a great pale north-facing wall filling the upper two thirds of the picture. Because that wall faces away from the Sun at every one of the ten instants, **all ten frames are under-lit**: the metered development runs from **+3.451 stops** on the fire-hydrant sheet to **+6.000**, clamped, on the NYPD sheet, and nine of the ten carry the record's own under-lit note.

**Sun** — azimuth 177.9°, elevation 36.9° at 2013-10-25T12:33:12-04:00, from the photograph’s own EXIF DateTimeOriginal; 822.8 W/m² direct normal, sky at strength 0.0342, Filmic, **+4.92 stops**. Metered: **4.922 stops** on a linear median of **0.005939**, against a physical rule of 0.22, and the record carries its own under-lit note: a scene this far from a photographable level needs more than the 4 stops a photographer recovers hand-held.

## Verdict — the sheet that exists to show New York's traffic signals contains none, and neither does any other sheet in the pass

**There is no traffic signal in this frame.** The render's `props.per_kind` lists fifteen kinds — 475 trees, 161 Citi Bike dock units, 55 cooling towers, 47 street lamps, 43 manholes, 32 hydrants, 18 vent grates, 13 bike racks, 13 bus-stop signs, 11 subway entrances, 3 steam vents, 2 newsstands, a bus shelter, a LinkNYC kiosk and a mailbox — and **no signal of any kind**, no pedestrian head, no push-button station, no one-way blade. The photograph beside it is a close-up of exactly those objects.

**This is not a gap in the city and it is not a gap in the modelling.** `blender_out/props` holds five signal assemblies built to ITE and MUTCD dimensions — `signal_mastarm_6m`, `signal_mastarm_9m`, `signal_pedestal`, `signal_spanwire` and `signal_ped_countdown`, the twelve-inch three-section head at 0.349 by 0.394 by 0.203 m with a 0.305 m lens and a 0.241 m visor, on a 5.5 m standard carrying 6.1 m and 9.1 m mast arms, in NYC DOT dark green with a louvred backplate and a retroreflective yellow border. `data/processed/roads/signals.parquet` holds **19,814 signalised nodes** with controller, cycle, offset and phase groups (ADR-007). And **`blender/verify/*.py` never reads either of them**: the props catalogue has 34 kinds and `traffic_signal` is not one, so nothing on the renderer's placement path can resolve to those five models. The engine gets the signals; the evidence does not.

**What the frame does show is a shaded wall.** The dominant surface is a pale north-facing shell 23.7 m from the lens, so the scene arrived at a linear median of 0.005939 — one thirtieth of a photographable level — and was lifted **4.922 stops**. The consequence is measurable: the render's contrast is **0.56** of the photograph's and its 95th percentile 0.6965 against 0.9395. The photograph's own exposure sits 1.187 stops below the grey convention and the render is metered to 0.255 above it, a **1.442-stop** gap, so p50 reads **1.608×**.

**One thing in the frame is right and worth naming.** 29 of the 53 vehicles are yellow medallion taxis, with 8 black cars, 7 sedans, 5 boro taxis, 3 SUVs and a box truck — a taxi-heavy mix, which is correct for this block. The crosswalk the photograph stands on is drawn too: 620 crosswalk polygons and 12,088 white markings in this frame, and **0 dropped**.

**And the sheet a reader should hold this one beside is J110.** The verification renderer places props through `data/processed/furniture/props_catalog.json`, which has 34 kinds, and it never reads `tiles/{tile}/signs.json`. So none of the **633,287 signs** or **19,814 signalised intersections** in this city's own data appears in this frame, or in any of the other 171, even though the models for fifteen of them sit in `blender_out/props` and 898 tiles carry the export. Only **20 prop kinds** appear anywhere in the pass.

## What matches

* **29 yellow medallion taxis of 53 vehicles**, which is the right mix for this block.
* **620 crosswalk polygons and 12,088 white markings**, none dropped — the continental crosswalk the photograph stands on is a class this build draws.
* **The record states its own limits before the assessment does**: no subject, a low-confidence reference heading, and an instruction to compare street width, storey height and material rather than composition.
* **The block is paved and marked**: 27,313 polygons with 12,088 white markings, 5,788 sidewalk, 4,278 roadbed, 3,372 curb, 751 plaza, 620 crosswalk and 341 median, and **0 dropped**.
* **The camera was not moved**, with 37.2 m of clear view along the azimuth.

## What does not match

* **No signal, no pedestrian head, no push-button station and no one-way blade**, on the sheet whose whole purpose is to show them.
* **Contrast is 0.56 of the photograph's** and the 95th percentile 0.6965 against 0.9395, both consequences of a 4.922-stop lift.
* **A 1.442-stop exposure gap**, so p50 reads 1.608× (J83).
* **None of the city's 633,287 signs or 19,814 signalised intersections is in this frame**, or in any other frame in the pass (J110).
* **Ten sheets in the pass are this same picture**, lit at ten instants and captioned for ten different subjects, so a reader flipping through the set sees the same Midtown wall ten times.
* **No structures at all**: 0 tiles imported, 4 without a file, 0 triangles.
* **No cloud.** Nothing in this build reads a historical sky, so the only fill on a shaded frame is a procedural Nishita dome.

## Measured for this assessment

| figure | where it comes from |
|---|---|
| ten sheets share this camera | the `camera` block of all ten records at 40.755, -73.984, azimuth 0.0 deg, 35 mm: the six streetscape showcase items and the four vehicle items |
| all ten are under-lit, from 3.451 to 6.000 stops | the `lighting.development.stops` of those ten records; nine of them carry the record's own under-lit note |
| 633,287 signs, 106,622 of them D3-1 street-name blades, and 19,814 signalised nodes | row counts and the `mutcd_code` distribution of `data/processed/roads/signs.parquet`, and the row count of `data/processed/roads/signals.parquet` |
| fifteen signal and sign models exist and none is placed | the `signal_*` and `sign_*` files in `blender_out/props`, against the 34 kinds in `data/processed/furniture/props_catalog.json` and the 20 kinds that appear in any record of the pass |
| 898 tiles carry a signs.json and the verification renderer never reads one | the per-tile export written by `pipeline/nycsim_pipeline/unreal/manifest.py`, and the absence of any reference to it in `blender/verify` |
| the MUTCD signal head at 0.349 by 0.394 by 0.203 m with a 0.305 m lens, a 0.241 m visor, a 5.5 m standard and 6.1 m and 9.1 m mast arms | the dimensions block of `blender/props/p_traffic.py`, which cites the ITE/MUTCD polycarbonate section and NYC DOT practice |
| 314,105 placed objects across the eight prop kinds that collapse to one asset each | DEVIATIONS J58, whose measurement this is |
| about 1,800 LinkNYC kiosks, 9,000 sidewalk sheds, 198 FDNY engine companies, 4,300 MTA buses in weekday peak service and 1.9 million registered private cars | the fleet and inventory bases published in `pipeline/nycsim_pipeline/traffic/fleet_mix.py` for the vehicle classes, and the city programme sizes those entries cite |
| the non-taxi remainder splits 55 per cent sedan, 30 per cent SUV, 10 per cent black car and 5 per cent NYPD | `TrafficSim::sampleClass` in `core/src/traffic/TrafficSim.cpp` |
| the scaffold category places 105 pieces on the City Hall sheet, 87 on the Woolworth and 77 on three Times Square sheets | the `scene.kit.per_category` of those records |
| the leaf-off frames fit 1,167 props against 876 on the same budget, dropping 729 against 1,020 | the `props.placed` and `props.dropped_for_budget` of the ten records against their `capped` budget of 1,065,014 triangles, grouped by whether their instant falls inside the leaf-off window (J97) |


## Cause of each gap

| gap | cause | class |
|---|---|---|
| no traffic signal anywhere in the frame or the pass | the renderer places props through a 34-kind catalogue that has no `traffic_signal` kind and never reads the signal or sign export, while the models and the 19,814 signalised nodes both exist (J110) | **verification — open, and the cheapest large repair on the list** |
| 4.922 stops of development, past the under-lit threshold | a north-facing wall 23.7 m from the lens fills the frame at every one of the ten instants this camera was used for, and the only fill is a procedural sky at strength 0.0342 (J83) | **verification — declared, and the number is published with the frame** |
| no signage of any kind in the frame | the verification renderer never reads the sign or signal export, and its 34-kind props catalogue has no kind for either (J110) | **verification — open** |
| ten sheets are the same picture | these items name a type rather than a place, so they share one representative camera; the set would read better if each stood somewhere its own subject is dense | verification — a design choice worth revisiting |
| no structures on any of the 4 tiles | four tiles in range and none has a structures file; 19 sheets in the pass share it (B13 remainder) | data — open |
| no cloud | nothing in this build reads a historical sky | reference — no source exists |
