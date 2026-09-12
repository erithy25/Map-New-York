# MTA New York City Bus

`vehicle_mta_bus` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Feb 23 2026 Blizzard in Manhattan, MTA M103 bus on 3rd Avenue at 94th Street, Yorkville, Upper East Side, New York 06.jpg by Deans Charbal, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2026-02-23 09:46:41, 1920x1440. [Commons page](https://commons.wikimedia.org/wiki/File:Feb_23_2026_Blizzard_in_Manhattan,_MTA_M103_bus_on_3rd_Avenue_at_94th_Street,_Yorkville,_Upper_East_Side,_New_York_06.jpg) — the photograph carries no camera GPS and its view direction was not derived from the image, so its viewpoint confidence is **low**. An M103 bus on Third Avenue at 94th Street **in a blizzard**: snow on the roadway, snow on the bus's roof and skirts, snow falling across the frame, and the route sign lit in the murk.

**Camera** — 40.755, -73.984 (NYC_TM -2871, 6108) at z 20.4 m NAVD88 | azimuth 0.0°, pitch 0.0° | 35 mm on 36 mm (54.4° horizontal, 54.4° on the long side) | 1208x906. This is one of **ten sheets in the pass rendered from this exact camera** — the same position, the same heading and the same 35 mm lens, each frame shaped to its own reference photograph so the horizontal field runs from 42.0° to 54.4° across the ten — each standing for a different object class and each lit at its own reference photograph's instant. The record is candid about what that means: *"This item names no subject and the reference photograph's own view direction was not derived from the image (confidence: low), so the two halves of this sheet are not guaranteed to face the same way -- compare them on street width, storey height and material, not on composition."* `subject_note` reads *"the item names no point subject"*, so there is no height probe, no sightline and no visible fraction on this record at all. The camera was **not moved**; the nearest built thing in the frame is `lm_c_times_square.0` **21.8 m** away and the view azimuth is clear for **37.2 m**. The ground under the lens reads 18.769 m NAVD88, the 10th percentile of 113 samples within 12.0 m.

**In the frame, in every one of the ten** — 4 building tiles (247,682 tris), 9 landmark models of which 2 fall inside the frame cone, 27,313 pavement polygons with 12,088 white markings and 620 crosswalk, **0 triangles of structures** with 4 tiles having no file, and a great pale north-facing wall filling the upper two thirds of the picture. Because that wall faces away from the Sun at every one of the ten instants, **all ten frames are under-lit**: the metered development runs from **+3.451 stops** on the fire-hydrant sheet to **+6.000**, clamped, on the NYPD sheet, and nine of the ten carry the record's own under-lit note.

**Sun** — azimuth 138.6°, elevation 29.8° at 2026-02-23T09:46:41-05:00, from the photograph’s own EXIF DateTimeOriginal; 768.6 W/m² direct normal, sky at strength 0.0358, Filmic, **+5.30 stops**. Metered: **5.303 stops** on a linear median of **0.00456**, against a physical rule of 0.53, and the record carries its own under-lit note: a scene this far from a photographable level needs more than the 4 stops a photographer recovers hand-held.

## Verdict — no bus in the frame and no snow on a blizzard reference, so this sheet is missing both of its subjects

**There is no MTA bus in this frame.** The sample is 18 yellow taxis, 13 boro taxis, 12 sedans, 7 black cars, 2 vans and an SUV. The sheet exists to compare a New York City Bus against a photograph of one, and the bus is absent — the same draw problem as the NYPD and FDNY sheets, from a fleet basis of about 4,300 buses in weekday peak service against 1.9 million private cars.

**And the other half of this reference is weather this build cannot render.** The photograph is titled for what it is: a **blizzard** on Third Avenue. Snow is lying on the roadway, on the bus's roof and skirts, and falling across the frame. The render has none of it, and the reason is measured in J97: `render_sheets.py` builds its snapshot request with only x, y, heading, hour, day type, seed and headlights, so **`rain_mm_h` stays 0.00, `temperature_c` 15.0 and `snow_cover` 0.00 on all 172 sheets**, whatever the reference photograph's date says. The date reaches the trees through the leaf switch and never reaches the weather. So this sheet's reference is a February blizzard and its render is a dry summer-temperature Midtown morning with bare trees — the trees are right and nothing else about the season is.

**The bus is modelled and named.** `blender/verify/agents.py` maps the class to a **`nova_lfs_mta`** — a 40-foot MTA local bus, a Nova LFS where the fleet table names a New Flyer, with the substitution recorded rather than hidden. So the asset exists and was not drawn.

**This is one of the four leaf-off instants from this camera** and fits **1,167 props** of the same budget that fits 876 in the leaf-on frames (J97).

**Tone**: the photograph's own median sits above the grey convention — snow does that — so the gap is **−0.596 stops** and the render is the darker half: mean **0.893×**, p50 **0.828×**, contrast **0.59×**, chroma **0.764**.

**And the sheet a reader should hold this one beside is J110.** The verification renderer places props through `data/processed/furniture/props_catalog.json`, which has 34 kinds, and it never reads `tiles/{tile}/signs.json`. So none of the **633,287 signs** or **19,814 signalised intersections** in this city's own data appears in this frame, or in any of the other 171, even though the models for fifteen of them sit in `blender_out/props` and 898 tiles carry the export. Only **20 prop kinds** appear anywhere in the pass.

## What matches

* **The bus body exists and its substitution is recorded**: a `nova_lfs_mta`, a Nova LFS where the fleet table names a New Flyer.
* **The trees are bare**, which is right for 23 February (J97).
* **1,167 props placed**, the leaf-off budget advantage.
* **The record states its own limits before the assessment does**: no subject, a low-confidence reference heading, and an instruction to compare street width, storey height and material rather than composition.
* **The block is paved and marked**: 27,313 polygons with 12,088 white markings, 5,788 sidewalk, 4,278 roadbed, 3,372 curb, 751 plaza, 620 crosswalk and 341 median, and **0 dropped**.
* **The camera was not moved**, with 37.2 m of clear view along the azimuth.

## What does not match

* **No MTA bus in the frame**, on the sheet that exists to show one.
* **No snow, on a reference titled for a blizzard.** `rain_mm_h` is 0.00, `temperature_c` 15.0 and `snow_cover` 0.00 on all 172 sheets (J97).
* **The render is the darker half**: a −0.596-stop gap, mean 0.893× and p50 0.828×, because snow puts a photograph's median above the grey convention.
* **Contrast 0.59 and chroma 0.764**, from a 5.303-stop lift on a shaded wall.
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
| no MTA bus in the frame | about 4,300 buses in weekday peak service against 1.9 million private cars, drawn per vehicle from the density cell, so a 53-vehicle sample will usually contain none. A sheet named for a class needs the class placed deliberately | **verification — open; the same repair as the NYPD and FDNY sheets** |
| no snow on a blizzard reference | the render's snapshot request carries x, y, heading, hour, day type, seed and headlights and no weather at all, so rain, temperature and snow cover are the defaults on every one of the 172 sheets (J97) | **verification — open, and this sheet is the clearest case for it in the pass** |
| 5.303 stops of development | a 29.8 deg February Sun on the wall this camera points at (J83) | verification — declared |
| no signage of any kind in the frame | the verification renderer never reads the sign or signal export, and its 34-kind props catalogue has no kind for either (J110) | **verification — open** |
| ten sheets are the same picture | these items name a type rather than a place, so they share one representative camera; the set would read better if each stood somewhere its own subject is dense | verification — a design choice worth revisiting |
| no structures on any of the 4 tiles | four tiles in range and none has a structures file; 19 sheets in the pass share it (B13 remainder) | data — open |
| no cloud | nothing in this build reads a historical sky | reference — no source exists |
