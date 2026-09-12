# NYC yellow cab

`vehicle_yellow_cab` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Yellow Taxi Cabs, New York.jpg by Matt Kieffer, CC BY-SA 2.0 (https://creativecommons.org/licenses/by-sa/2.0), taken 2015, 1920x1056. [Commons page](https://commons.wikimedia.org/wiki/File:Yellow_Taxi_Cabs,_New_York.jpg) — the photograph carries no camera GPS and its view direction was not derived from the image, so its viewpoint confidence is **low**. A rank of yellow medallion cabs seen close and low, filling the frame: the roof lights, the medallion numbers on the hood, the TLC decals on the doors, the partition glass.

**Camera** — 40.755, -73.984 (NYC_TM -2871, 6108) at z 20.4 m NAVD88 | azimuth 0.0°, pitch 0.0° | 35 mm on 36 mm (54.4° horizontal, 54.4° on the long side) | 1280x704. This is one of **ten sheets in the pass rendered from this exact camera** — the same position, the same heading and the same 35 mm lens, each frame shaped to its own reference photograph so the horizontal field runs from 42.0° to 54.4° across the ten — each standing for a different object class and each lit at its own reference photograph's instant. The record is candid about what that means: *"This item names no subject and the reference photograph's own view direction was not derived from the image (confidence: low), so the two halves of this sheet are not guaranteed to face the same way -- compare them on street width, storey height and material, not on composition."* `subject_note` reads *"the item names no point subject"*, so there is no height probe, no sightline and no visible fraction on this record at all. The camera was **not moved**; the nearest built thing in the frame is `lm_c_times_square.0` **21.8 m** away and the view azimuth is clear for **37.2 m**. The ground under the lens reads 18.769 m NAVD88, the 10th percentile of 113 samples within 12.0 m.

**In the frame, in every one of the ten** — 4 building tiles (247,682 tris), 9 landmark models of which 2 fall inside the frame cone, 27,313 pavement polygons with 12,088 white markings and 620 crosswalk, **0 triangles of structures** with 4 tiles having no file, and a great pale north-facing wall filling the upper two thirds of the picture. Because that wall faces away from the Sun at every one of the ten instants, **all ten frames are under-lit**: the metered development runs from **+3.451 stops** on the fire-hydrant sheet to **+6.000**, clamped, on the NYPD sheet, and nine of the ten carry the record's own under-lit note.

**Sun** — azimuth 284.1°, elevation 20.1° at 2015-06-21T18:30:00-04:00, from a chosen instant (J80); 654.9 W/m² direct normal, sky at strength 0.0405, Filmic, **+5.77 stops**. Metered: **5.774 stops** on a linear median of **0.00329**, against a physical rule of 1.11, and the record carries its own under-lit note: a scene this far from a photographable level needs more than the 4 stops a photographer recovers hand-held.

## Verdict — twenty-six yellow cabs in the frame, and the one thing this sheet can check it checks

**The subject is present in quantity.** The simulation's sample for this frame is **26 yellow medallion taxis** of 53 vehicles, with 11 boro taxis, 10 black cars, 3 sedans, 2 SUVs and an MTA bus. A yellow cab in Midtown at half past six on a June evening is the most ordinary thing in the city and the fleet mix says so: taxis are half the vehicles in frame, which is right here and would be wrong in most of the five boroughs.

**What the sheet cannot check is the car.** The reference is a close, low rank of cabs — roof light, hood medallion number, door decals, partition — and the render's cabs are street-scale bodies well down the block. `blender/verify/agents.py` names the body it uses and why: a **`camry_taxi_yellow`**, the Toyota Camry XV70 with the TAXI roof light, which is the body the fleet table names. That is the correct car for the period and it is drawn at LOD2 for most of the sample, so its decals and numbers are not in the geometry at all.

**The instant was assumed, and the record says so.** This reference carries only a year, so the sun was placed at a chosen hour rather than read from EXIF (J80) — 21 June at 18:30, which is a defensible pick for a summer street and is not the moment the photograph was taken.

**The frame needed 5.774 stops.** Tone: mean **1.217×**, p50 **1.27×**, contrast **0.616×**, chroma **0.527**, and the render's 95th percentile 0.7292 against 0.879.

**And the sheet a reader should hold this one beside is J110.** The verification renderer places props through `data/processed/furniture/props_catalog.json`, which has 34 kinds, and it never reads `tiles/{tile}/signs.json`. So none of the **633,287 signs** or **19,814 signalised intersections** in this city's own data appears in this frame, or in any of the other 171, even though the models for fifteen of them sit in `blender_out/props` and 898 tiles carry the export. Only **20 prop kinds** appear anywhere in the pass.

## What matches

* **26 yellow medallion taxis of 53 vehicles** — the subject is present, and a taxi-heavy mix is right for this block.
* **The body is the one the fleet table names**: a `camry_taxi_yellow`, the Camry XV70 with the TAXI roof light.
* **The record states its own limits before the assessment does**: no subject, a low-confidence reference heading, and an instruction to compare street width, storey height and material rather than composition.
* **The block is paved and marked**: 27,313 polygons with 12,088 white markings, 5,788 sidewalk, 4,278 roadbed, 3,372 curb, 751 plaza, 620 crosswalk and 341 median, and **0 dropped**.
* **The camera was not moved**, with 37.2 m of clear view along the azimuth.

## What does not match

* **The car cannot be compared.** Roof light, hood medallion number and TLC door decals are not in the geometry, and most of the sample is drawn at LOD2.
* **The sun instant was assumed**, because the reference carries only a year (J80).
* **Contrast 0.616 and chroma 0.527**, from a 5.774-stop lift on a shaded wall.
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
| the car cannot be compared at close range | a close-up reference paired with a street-scale frame, with most bodies at the coarsest LOD and no decal or numbering layer in the fleet assets | **verification — declared, and the honest reading of this sheet** |
| the sun instant was assumed | the reference's `date_taken` is a bare year, so an hour was chosen to light the view rather than read (J80) | declared decision |
| 5.774 stops of development | a 20.1 deg evening Sun on the wall this camera points at (J83) | verification — declared |
| no signage of any kind in the frame | the verification renderer never reads the sign or signal export, and its 34-kind props catalogue has no kind for either (J110) | **verification — open** |
| ten sheets are the same picture | these items name a type rather than a place, so they share one representative camera; the set would read better if each stood somewhere its own subject is dense | verification — a design choice worth revisiting |
| no structures on any of the 4 tiles | four tiles in range and none has a structures file; 19 sheets in the pass share it (B13 remainder) | data — open |
| no cloud | nothing in this build reads a historical sky | reference — no source exists |
