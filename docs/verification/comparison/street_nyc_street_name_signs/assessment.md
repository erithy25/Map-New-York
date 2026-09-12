# NYC street name signs (close-ups)

`street_nyc_street_name_signs` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Christopher Street Sign 003.jpg by Kidfly182, CC BY 4.0 (https://creativecommons.org/licenses/by/4.0), taken 2025-02-11 13:11:21, 1920x863. [Commons page](https://commons.wikimedia.org/wiki/File:Christopher_Street_Sign_003.jpg) — the photograph carries no camera GPS and its view direction was not derived from the image, so its viewpoint confidence is **low**. A Village corner in February: the green D3-1 blade reading CHRISTOPHER ST in Highway Gothic with its white border, bracketed to a signal pole, against bare branches and a winter sky. The photograph is the sign and nothing else.

**Camera** — 40.755, -73.984 (NYC_TM -2871, 6108) at z 20.4 m NAVD88 | azimuth 0.0°, pitch 0.0° | 35 mm on 36 mm (54.4° horizontal, 54.4° on the long side) | 1280x576. This is one of **ten sheets in the pass rendered from this exact camera** — the same position, the same heading and the same 35 mm lens, each frame shaped to its own reference photograph so the horizontal field runs from 42.0° to 54.4° across the ten — each standing for a different object class and each lit at its own reference photograph's instant. The record is candid about what that means: *"This item names no subject and the reference photograph's own view direction was not derived from the image (confidence: low), so the two halves of this sheet are not guaranteed to face the same way -- compare them on street width, storey height and material, not on composition."* `subject_note` reads *"the item names no point subject"*, so there is no height probe, no sightline and no visible fraction on this record at all. The camera was **not moved**; the nearest built thing in the frame is `prop_lamp_cobra_davit_2` **10.4 m** away and the view azimuth is clear for **37.2 m**. The ground under the lens reads 18.769 m NAVD88, the 10th percentile of 113 samples within 12.0 m.

**In the frame, in every one of the ten** — 4 building tiles (247,682 tris), 9 landmark models of which 2 fall inside the frame cone, 27,313 pavement polygons with 12,088 white markings and 620 crosswalk, **0 triangles of structures** with 4 tiles having no file, and a great pale north-facing wall filling the upper two thirds of the picture. Because that wall faces away from the Sun at every one of the ten instants, **all ten frames are under-lit**: the metered development runs from **+3.451 stops** on the fire-hydrant sheet to **+6.000**, clamped, on the NYPD sheet, and nine of the ten carry the record's own under-lit note.

**Sun** — azimuth 197.9°, elevation 33.7° at 2025-02-11T13:11:21-05:00, from the photograph’s own EXIF DateTimeOriginal; 800.2 W/m² direct normal, sky at strength 0.0349, Filmic, **+5.08 stops**. Metered: **5.075 stops** on a linear median of **0.005339**, against a physical rule of 0.35, and the record carries its own under-lit note: a scene this far from a photographable level needs more than the 4 stops a photographer recovers hand-held.

## Verdict — the city's data holds 106,622 street-name blades and not one of them is in this frame

**There is no street-name sign in this frame.** The render's seventeen prop kinds run from 544 trees and 259 Citi Bike dock units down to a single subway emergency exit, and **not one of them is a sign blade**. The photograph beside it is a single green D3-1 blade filling the frame.

**The data for it is the largest single class in the road tables.** `data/processed/roads/signs.parquet` holds **633,287 signs**, of which **106,622 are D3-1** — the street-name blade — each with its own x, y, z, ground elevation, `facing_heading`, legend `text`, arrow code, width, height and support type. The model exists as `sign_street_name_blade`, and `blender/props/p_signs.py` describes what it carries: a runtime-swappable `SIGN_FACE` material on the front face only, with *"the UV of that face spanning exactly (0,0)-(1,1) over the face's bounding box, u to the reader's right and v upwards, so the engine can render the real legend from `roads/signs.parquet` straight onto it"*, and a default baked texture that is the published NYC DOT layout. The export exists: **898 tiles carry a `signs.json`**, and tile `t_0_0` alone holds **1,918** of them in tile-local coordinates. **The verification renderer reads none of it** (J110). So the evidence for this build shows a New York with no street names on its corners, and the build itself does not have that fault.

**A second, smaller thing is visible in this frame and it is a real observation.** This is one of the four of the ten sheets whose instant falls in the leaf-off window, and it fits **1,167 props of the same 1,065,014-triangle budget against 876** on the six leaf-on sheets, dropping **729** where the leaf-on frames lose more. A bare tree is cheaper than a leafy one, so the binary leaf switch of J97 has a performance consequence as well as an appearance one: the same camera on the same budget draws a third more street furniture in winter.

**The tone runs the other way from the rest of the ten.** The photograph's own median sits **above** the grey convention and the render's below it, so the gap is **−1.373 stops** and the render is the darker half: mean **0.784×**, p50 **0.649×**. Chroma is **0.467** and contrast **0.661**.

**And the sheet a reader should hold this one beside is J110.** The verification renderer places props through `data/processed/furniture/props_catalog.json`, which has 34 kinds, and it never reads `tiles/{tile}/signs.json`. So none of the **633,287 signs** or **19,814 signalised intersections** in this city's own data appears in this frame, or in any of the other 171, even though the models for fifteen of them sit in `blender_out/props` and 898 tiles carry the export. Only **20 prop kinds** appear anywhere in the pass.

## What matches

* **1,167 props placed of the same budget that fits 876 on the leaf-on sheets** — a bare canopy is cheaper, so the winter frames are better furnished.
* **Seventeen prop kinds in the frame**, including 544 trees, 259 Citi Bike dock units, 85 cooling towers, 70 street lamps, 64 manholes, 48 hydrants, 30 vent grates and 21 bike racks.
* **The record states its own limits before the assessment does**: no subject, a low-confidence reference heading, and an instruction to compare street width, storey height and material rather than composition.
* **The block is paved and marked**: 27,313 polygons with 12,088 white markings, 5,788 sidewalk, 4,278 roadbed, 3,372 curb, 751 plaza, 620 crosswalk and 341 median, and **0 dropped**.
* **The camera was not moved**, with 37.2 m of clear view along the azimuth.

## What does not match

* **No street-name blade**, against 106,622 of them in the city's own sign table.
* **The render is the darker half here**: a −1.373-stop exposure gap, mean 0.784× and p50 0.649× (J83).
* **Chroma 0.467 and contrast 0.661**, both consequences of a 5.075-stop lift on a shaded wall.
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
| no street-name blade in the frame | 106,622 D3-1 rows and a `sign_street_name_blade` model with a runtime `SIGN_FACE` and an exact 0..1 UV both exist, and the verification renderer reads neither the table nor the per-tile export (J110) | **verification — open** |
| 5.075 stops of development | the shaded north-facing wall this camera points at, at all ten of its instants (J83) | verification — declared |
| the winter frames fit more props than the summer ones | the leaf switch is binary, and a bare-canopy tree asset costs fewer triangles than a leafy one, so the same props budget reaches further (J97) | performance — a consequence worth knowing |
| no signage of any kind in the frame | the verification renderer never reads the sign or signal export, and its 34-kind props catalogue has no kind for either (J110) | **verification — open** |
| ten sheets are the same picture | these items name a type rather than a place, so they share one representative camera; the set would read better if each stood somewhere its own subject is dense | verification — a design choice worth revisiting |
| no structures on any of the 4 tiles | four tiles in range and none has a structures file; 19 sheets in the pass share it (B13 remainder) | data — open |
| no cloud | nothing in this build reads a historical sky | reference — no source exists |
