# Sidewalk shed (scaffolding)

`street_sidewalk_shed` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:47 St sidewalk shed work 2020 jeh.jpg by Jim.henderson, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2020-01-21 13:21:19, 1920x1440. [Commons page](https://commons.wikimedia.org/wiki/File:47_St_sidewalk_shed_work_2020_jeh.jpg) — the photograph carries no camera GPS and its view direction was not derived from the image, so its viewpoint confidence is **low**. A sidewalk shed being erected on 47th Street in January: the green-painted plywood parapet, the steel standards and ledgers, the lit underside over the pavement, and the workers on it. Its own 95th percentile is **1.0** — clipped in the source file.

**Camera** — 40.755, -73.984 (NYC_TM -2871, 6108) at z 20.4 m NAVD88 | azimuth 0.0°, pitch 0.0° | 35 mm on 36 mm (54.4° horizontal, 54.4° on the long side) | 1208x906. This is one of **ten sheets in the pass rendered from this exact camera** — the same position, the same heading and the same 35 mm lens, each frame shaped to its own reference photograph so the horizontal field runs from 42.0° to 54.4° across the ten — each standing for a different object class and each lit at its own reference photograph's instant. The record is candid about what that means: *"This item names no subject and the reference photograph's own view direction was not derived from the image (confidence: low), so the two halves of this sheet are not guaranteed to face the same way -- compare them on street width, storey height and material, not on composition."* `subject_note` reads *"the item names no point subject"*, so there is no height probe, no sightline and no visible fraction on this record at all. The camera was **not moved**; the nearest built thing in the frame is `lm_c_times_square.0` **21.8 m** away and the view azimuth is clear for **37.2 m**. The ground under the lens reads 18.769 m NAVD88, the 10th percentile of 113 samples within 12.0 m.

**In the frame, in every one of the ten** — 4 building tiles (247,682 tris), 9 landmark models of which 2 fall inside the frame cone, 27,313 pavement polygons with 12,088 white markings and 620 crosswalk, **0 triangles of structures** with 4 tiles having no file, and a great pale north-facing wall filling the upper two thirds of the picture. Because that wall faces away from the Sun at every one of the ten instants, **all ten frames are under-lit**: the metered development runs from **+3.451 stops** on the fire-hydrant sheet to **+6.000**, clamped, on the NYPD sheet, and nine of the ten carry the record's own under-lit note.

**Sun** — azimuth 199.6°, elevation 27.0° at 2020-01-21T13:21:19-05:00, from the photograph’s own EXIF DateTimeOriginal; 740.9 W/m² direct normal, sky at strength 0.0370, Filmic, **+5.21 stops**. Metered: **5.213 stops** on a linear median of **0.004851**, against a physical rule of 0.68, and the record carries its own under-lit note: a scene this far from a photographable level needs more than the 4 stops a photographer recovers hand-held.

## Verdict — no scaffold piece was drawn in this frame, on the one sheet about scaffolding, and the kit that carries them was capped

**There is no scaffold in this frame.** `scene.kit.per_category` on this record lists no `scaffold` entry at all. The category exists and is placed elsewhere in the pass — 105 pieces on the City Hall sheet, 87 on the Woolworth, 77 on three of the Times Square sheets — so the asset and the placement path both work. Here the kit was capped at **894,534 triangles** and what fitted was windows: the same windows-first spend that leaves one cornice on the Chrysler sheet.

**That is the honest reading and it is a performance result, not a data one.** New York has some 9,000 sidewalk sheds standing at any time and they are a defining feature of its streets; this build models them as a kit category and then spends its kit budget on window pieces, so a sheet named for the shed shows none.

**The reference is a construction photograph rather than a finished shed**, which makes the pairing partly about a state this build has no representation for: there is no scaffolding-under-erection state, no lit underside and no plywood parapet colour in the kit's own vocabulary.

**This is one of the four leaf-off instants from this camera**, and it fits **1,167 props** of the same 1,065,014-triangle budget against 876 on the leaf-on sheets, dropping 729 where the leaf-on frames lose more — a bare canopy is cheaper, so the winter frames carry a third more furniture (J97).

**Under a 27.0° January Sun the frame needed 5.213 stops.** The tone: mean **1.173×**, p50 **1.199×**, contrast **0.516×**, chroma **0.576**, with the render's 95th percentile at 0.7274 against a clipped 1.0.

**And the sheet a reader should hold this one beside is J110.** The verification renderer places props through `data/processed/furniture/props_catalog.json`, which has 34 kinds, and it never reads `tiles/{tile}/signs.json`. So none of the **633,287 signs** or **19,814 signalised intersections** in this city's own data appears in this frame, or in any of the other 171, even though the models for fifteen of them sit in `blender_out/props` and 898 tiles carry the export. Only **20 prop kinds** appear anywhere in the pass.

## What matches

* **The scaffold category exists and works elsewhere** — 105 pieces on the City Hall sheet, 87 on the Woolworth, 77 on three Times Square sheets.
* **1,167 props placed of the budget that fits 876 in leaf-on frames** (J97).
* **The record states its own limits before the assessment does**: no subject, a low-confidence reference heading, and an instruction to compare street width, storey height and material rather than composition.
* **The block is paved and marked**: 27,313 polygons with 12,088 white markings, 5,788 sidewalk, 4,278 roadbed, 3,372 curb, 751 plaza, 620 crosswalk and 341 median, and **0 dropped**.
* **The camera was not moved**, with 37.2 m of clear view along the azimuth.

## What does not match

* **No scaffold piece in this frame at all**, on the one sheet in the pass about sidewalk sheds.
* **The reference's highlights are clipped at 1.0.**
* **Contrast 0.516 and chroma 0.576**, from a 5.213-stop lift on a shaded wall.
* **No under-erection state**: the reference shows a shed being built, and the kit has one finished scaffold vocabulary.
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
| no scaffold in the frame | the kit triangle budget at 894,534 triangles was spent windows-first, and the scaffold category placed nothing here although it places tens of pieces on other sheets | **performance — open; a per-category floor would fix it** |
| no under-erection state | the kit has one finished scaffold vocabulary and no construction-sequence state | geometry — no source |
| 5.213 stops of development | a 27.0 deg January Sun on the north-facing wall this camera points at (J83) | verification — declared |
| no signage of any kind in the frame | the verification renderer never reads the sign or signal export, and its 34-kind props catalogue has no kind for either (J110) | **verification — open** |
| ten sheets are the same picture | these items name a type rather than a place, so they share one representative camera; the set would read better if each stood somewhere its own subject is dense | verification — a design choice worth revisiting |
| no structures on any of the 4 tiles | four tiles in range and none has a structures file; 19 sheets in the pass share it (B13 remainder) | data — open |
| no cloud | nothing in this build reads a historical sky | reference — no source exists |
