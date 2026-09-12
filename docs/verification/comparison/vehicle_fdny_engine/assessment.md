# FDNY engine (pumper)

`vehicle_fdny_engine` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:FDNY Engine 21 2025.jpg by Transpoman, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2025-12-03 10:31:59, 1920x1440. [Commons page](https://commons.wikimedia.org/wiki/File:FDNY_Engine_21_2025.jpg) — the photograph carries no camera GPS and its view direction was not derived from the image, so its viewpoint confidence is **low**. Engine 21's pumper photographed close in December: the red body and gold leaf, the pump panel, the hose bed, the crosslays, the company numerals and the chrome.

**Camera** — 40.755, -73.984 (NYC_TM -2871, 6108) at z 20.4 m NAVD88 | azimuth 0.0°, pitch 0.0° | 35 mm on 36 mm (54.4° horizontal, 54.4° on the long side) | 1208x906. This is one of **ten sheets in the pass rendered from this exact camera** — the same position, the same heading and the same 35 mm lens, each frame shaped to its own reference photograph so the horizontal field runs from 42.0° to 54.4° across the ten — each standing for a different object class and each lit at its own reference photograph's instant. The record is candid about what that means: *"This item names no subject and the reference photograph's own view direction was not derived from the image (confidence: low), so the two halves of this sheet are not guaranteed to face the same way -- compare them on street width, storey height and material, not on composition."* `subject_note` reads *"the item names no point subject"*, so there is no height probe, no sightline and no visible fraction on this record at all. The camera was **not moved**; the nearest built thing in the frame is `lm_c_times_square.0` **21.8 m** away and the view azimuth is clear for **37.2 m**. The ground under the lens reads 18.769 m NAVD88, the 10th percentile of 113 samples within 12.0 m.

**In the frame, in every one of the ten** — 4 building tiles (247,682 tris), 9 landmark models of which 2 fall inside the frame cone, 27,313 pavement polygons with 12,088 white markings and 620 crosswalk, **0 triangles of structures** with 4 tiles having no file, and a great pale north-facing wall filling the upper two thirds of the picture. Because that wall faces away from the Sun at every one of the ten instants, **all ten frames are under-lit**: the metered development runs from **+3.451 stops** on the fire-hydrant sheet to **+6.000**, clamped, on the NYPD sheet, and nine of the ten carry the record's own under-lit note.

**Sun** — azimuth 161.2°, elevation 24.8° at 2025-12-03T10:31:59-05:00, from the photograph’s own EXIF DateTimeOriginal; 716.8 W/m² direct normal, sky at strength 0.0381, Filmic, **+5.18 stops**. Metered: **5.185 stops** on a linear median of **0.004949**, against a physical rule of 0.8, and the record carries its own under-lit note: a scene this far from a photographable level needs more than the 4 stops a photographer recovers hand-held.

## Verdict — no fire engine in the frame, and with 198 engine companies in a city of two million cars there would not normally be one

**There is no FDNY engine in this frame.** The sample is 22 yellow taxis, 13 boro taxis, 7 sedans, 7 black cars, an SUV and a box truck. The sheet exists to compare a pumper against a photograph of a pumper and the pumper is absent.

**The arithmetic makes that the expected outcome, not a failure of the simulation.** The fleet table's basis for this class is **198 engine companies** against about 1.9 million registered private cars, and `TrafficSim::sampleClass` draws a class per vehicle from the density cell's shares with no special handling for emergency vehicles. In a 53-vehicle sample the chance of an engine is small, so a sheet that asks *is the FDNY engine modelled?* cannot be answered by sampling the traffic. It needs the vehicle placed on purpose. Three of the four vehicle sheets in this pass are in that position.

**The engine is modelled and its dimensions are checked.** `blender/verify/agents.py` maps the class to an exported pumper body and carries an explicit note where an exported body differs from the size the fleet table publishes, so the asset exists and is dimension-audited; this frame simply did not draw one.

**This is one of the four leaf-off instants from this camera**, and it fits **1,167 props** of the same budget that fits 876 in the leaf-on frames (J97).

**The frame needed 5.185 stops.** Tone: mean **1.164×**, p50 **1.227×**, contrast **0.49×** — the flattest of the ten — chroma **0.31**, and the render's 95th percentile 0.7062 against 0.8687.

**And the sheet a reader should hold this one beside is J110.** The verification renderer places props through `data/processed/furniture/props_catalog.json`, which has 34 kinds, and it never reads `tiles/{tile}/signs.json`. So none of the **633,287 signs** or **19,814 signalised intersections** in this city's own data appears in this frame, or in any of the other 171, even though the models for fifteen of them sit in `blender_out/props` and 898 tiles carry the export. Only **20 prop kinds** appear anywhere in the pass.

## What matches

* **The body exists and is dimension-audited** against the fleet table's published size.
* **1,167 props placed**, the leaf-off budget advantage (J97).
* **The record states its own limits before the assessment does**: no subject, a low-confidence reference heading, and an instruction to compare street width, storey height and material rather than composition.
* **The block is paved and marked**: 27,313 polygons with 12,088 white markings, 5,788 sidewalk, 4,278 roadbed, 3,372 curb, 751 plaza, 620 crosswalk and 341 median, and **0 dropped**.
* **The camera was not moved**, with 37.2 m of clear view along the azimuth.

## What does not match

* **No FDNY engine in the frame**, on the sheet that exists to show one.
* **Contrast 0.49×**, the flattest of the ten frames from this camera, and chroma 0.31.
* **A close-up reference against a street-scale frame**: pump panel, hose bed, crosslays, numerals and gold leaf are not comparable here.
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
| no FDNY engine in the frame | 198 engine companies against 1.9 million private cars, drawn per vehicle from the density cell with no special handling, so a 53-vehicle sample will usually contain none. A sheet named for a class needs the class placed deliberately | **verification — open; the same repair as the NYPD and MTA sheets** |
| 5.185 stops of development and 0.49 contrast | a 24.8 deg December Sun on the wall this camera points at (J83) | verification — declared |
| no signage of any kind in the frame | the verification renderer never reads the sign or signal export, and its 34-kind props catalogue has no kind for either (J110) | **verification — open** |
| ten sheets are the same picture | these items name a type rather than a place, so they share one representative camera; the set would read better if each stood somewhere its own subject is dense | verification — a design choice worth revisiting |
| no structures on any of the 4 tiles | four tiles in range and none has a structures file; 19 sheets in the pass share it (B13 remainder) | data — open |
| no cloud | nothing in this build reads a historical sky | reference — no source exists |
