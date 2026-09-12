# NYC fire hydrant (close-up)

`street_fire_hydrant` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Fire Hydrant on East 101st Street, Lex Avenue, East Harlem Open Streets, June 15 2024, East Harlem, Manhattan.jpg by Deans Charbal, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2024-06-15 15:28:50, 1920x2560. [Commons page](https://commons.wikimedia.org/wiki/File:Fire_Hydrant_on_East_101st_Street,_Lex_Avenue,_East_Harlem_Open_Streets,_June_15_2024,_East_Harlem,_Manhattan.jpg) — the photograph carries no camera GPS and its view direction was not derived from the image, so its viewpoint confidence is **low**. A hydrant on East 101st Street during an Open Streets afternoon in June, photographed close and from above: the bonnet, the two 2½-inch side outlets with their caps and chains, the pumper nozzle, the operating nut, and the kerb behind it.

**Camera** — 40.755, -73.984 (NYC_TM -2871, 6108) at z 20.4 m NAVD88 | azimuth 0.0°, pitch 0.0° | 35 mm on 36 mm (42.2° horizontal, 54.4° on the long side, **portrait**) | 904x1206. This is one of **ten sheets in the pass rendered from this exact camera** — the same position, the same heading and the same 35 mm lens, each frame shaped to its own reference photograph so the horizontal field runs from 42.0° to 54.4° across the ten — each standing for a different object class and each lit at its own reference photograph's instant. The record is candid about what that means: *"This item names no subject and the reference photograph's own view direction was not derived from the image (confidence: low), so the two halves of this sheet are not guaranteed to face the same way -- compare them on street width, storey height and material, not on composition."* `subject_note` reads *"the item names no point subject"*, so there is no height probe, no sightline and no visible fraction on this record at all. The camera was **not moved**; the nearest built thing in the frame is `lm_c_times_square.0` **23.6 m** away and the view azimuth is clear for **37.2 m**. The ground under the lens reads 18.769 m NAVD88, the 10th percentile of 113 samples within 12.0 m.

**In the frame, in every one of the ten** — 4 building tiles (247,682 tris), 9 landmark models of which 2 fall inside the frame cone, 27,313 pavement polygons with 12,088 white markings and 620 crosswalk, **0 triangles of structures** with 4 tiles having no file, and a great pale north-facing wall filling the upper two thirds of the picture. Because that wall faces away from the Sun at every one of the ten instants, **all ten frames are under-lit**: the metered development runs from **+3.451 stops** on the fire-hydrant sheet to **+6.000**, clamped, on the NYPD sheet, and nine of the ten carry the record's own under-lit note.

**Sun** — azimuth 253.1°, elevation 53.8° at 2024-06-15T15:28:50-04:00, from the photograph’s own EXIF DateTimeOriginal; 901.0 W/m² direct normal, sky at strength 0.0316, Filmic, **+3.45 stops**. Metered: **3.451 stops** on a linear median of **0.016456**, against a physical rule of 0.0 — the only one of the ten sheets from this camera that stays below the +4 at which this build declares a frame under-lit.

## Verdict — the one showcase sheet whose subject is actually in its frame, thirty-two times over

**This sheet can answer its own question, and the answer is yes.** The render places **32 hydrants** within its radius, from a props run of 876 placed. A reader comparing halves can check the object's presence, its height against a kerb and its place in the furniture rhythm of a block. Six of the ten sheets rendered from this camera cannot do that, because their subject is not in the frame at all.

**What cannot be checked is the hydrant itself.** The photograph is a close-up from about two metres: its subject fills the frame and what it shows is the casting — bonnet, outlet caps, chains, pumper nozzle, operating nut, the paint over the flange. The render's nearest hydrant is a small red object at street scale in a 42° frame whose dominant surface is a shell more than twenty metres off. The two halves are not comparable on the thing the photograph is about; they are comparable, as the record says, on street width, storey height and material.

**And the hydrant is one asset for the whole city.** Eight prop kinds collapse to a single model each across 314,105 objects (J58), so every one of these 32 is the same casting at the same size, where the real city carries several generations of Mueller and Kennedy hydrants in at least three paint schemes.

**This is the best-lit of the ten frames and it is still lifted three and a half stops.** A 53.8° June Sun at 15:28 puts light on more of this canyon than any of the other nine instants, and the linear median still arrives at 0.016456. The render comes out **brighter** than the photograph — mean **1.31×**, p50 **1.221×**, 95th percentile 0.9221 against 0.7967 — and holds slightly **more** contrast, sd **1.076×**, which is the pale lifted wall against a photograph made close to a dark kerb. Chroma is **0.382**.

**And the sheet a reader should hold this one beside is J110.** The verification renderer places props through `data/processed/furniture/props_catalog.json`, which has 34 kinds, and it never reads `tiles/{tile}/signs.json`. So none of the **633,287 signs** or **19,814 signalised intersections** in this city's own data appears in this frame, or in any of the other 171, even though the models for fifteen of them sit in `blender_out/props` and 898 tiles carry the export. Only **20 prop kinds** appear anywhere in the pass.

## What matches

* **32 hydrants in the frame** — the subject is present and countable, which six of the ten sheets from this camera cannot say.
* **The best-lit of the ten frames**: 3.451 stops, the only one of them under the +4 under-lit threshold.
* **Slightly more contrast than the photograph**, sd 1.076×.
* **The record states its own limits before the assessment does**: no subject, a low-confidence reference heading, and an instruction to compare street width, storey height and material rather than composition.
* **The block is paved and marked**: 27,313 polygons with 12,088 white markings, 5,788 sidewalk, 4,278 roadbed, 3,372 curb, 751 plaza, 620 crosswalk and 341 median, and **0 dropped**.
* **The camera was not moved**, with 37.2 m of clear view along the azimuth.

## What does not match

* **The casting cannot be compared.** The photograph is a two-metre close-up of a hydrant's bonnet, outlets, chains and nut; the render's hydrants are street-scale objects in a 42° frame.
* **One hydrant model for the whole city** (J58), where the real street carries several generations and paint schemes.
* **Chroma 0.382** and a brighter render than the photograph, mean 1.31×, from a 3.451-stop lift on a shaded wall.
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
| the casting cannot be compared | the item is a close-up reference paired with a street-scale frame; the record says so itself and asks the reader to compare street width, storey height and material instead | **verification — declared, and the honest reading of this sheet** |
| one hydrant model for 314,105 placed objects of eight kinds | eight prop kinds collapse to a single asset each (J58 remainder) | data — open |
| 3.451 stops of development | the shaded north-facing wall this camera points at (J83) | verification — declared |
| no signage of any kind in the frame | the verification renderer never reads the sign or signal export, and its 34-kind props catalogue has no kind for either (J110) | **verification — open** |
| ten sheets are the same picture | these items name a type rather than a place, so they share one representative camera; the set would read better if each stood somewhere its own subject is dense | verification — a design choice worth revisiting |
| no structures on any of the 4 tiles | four tiles in range and none has a structures file; 19 sheets in the pass share it (B13 remainder) | data — open |
| no cloud | nothing in this build reads a historical sky | reference — no source exists |
