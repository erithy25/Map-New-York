# NYC newsstand (close-up)

`street_newsstand` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:MTA Queens Center 13.jpg by Tdorante10, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2017-11-01 15:07:14, 1920x1440. [Commons page](https://commons.wikimedia.org/wiki/File:MTA_Queens_Center_13.jpg) — the photograph carries no camera GPS and its view direction was not derived from the image, so its viewpoint confidence is **low**. A photograph filed as *MTA Queens Center*, showing a bus terminal frontage rather than a newsstand as its principal subject. Its own 95th percentile is **1.0** — the highlights are clipped in the source file.

**Camera** — 40.755, -73.984 (NYC_TM -2871, 6108) at z 20.4 m NAVD88 | azimuth 0.0°, pitch 0.0° | 35 mm on 36 mm (54.4° horizontal, 54.4° on the long side) | 1208x906. This is one of **ten sheets in the pass rendered from this exact camera** — the same position, the same heading and the same 35 mm lens, each frame shaped to its own reference photograph so the horizontal field runs from 42.0° to 54.4° across the ten — each standing for a different object class and each lit at its own reference photograph's instant. The record is candid about what that means: *"This item names no subject and the reference photograph's own view direction was not derived from the image (confidence: low), so the two halves of this sheet are not guaranteed to face the same way -- compare them on street width, storey height and material, not on composition."* `subject_note` reads *"the item names no point subject"*, so there is no height probe, no sightline and no visible fraction on this record at all. The camera was **not moved**; the nearest built thing in the frame is `lm_c_times_square.0` **21.8 m** away and the view azimuth is clear for **37.2 m**. The ground under the lens reads 18.769 m NAVD88, the 10th percentile of 113 samples within 12.0 m.

**In the frame, in every one of the ten** — 4 building tiles (247,682 tris), 9 landmark models of which 2 fall inside the frame cone, 27,313 pavement polygons with 12,088 white markings and 620 crosswalk, **0 triangles of structures** with 4 tiles having no file, and a great pale north-facing wall filling the upper two thirds of the picture. Because that wall faces away from the Sun at every one of the ten instants, **all ten frames are under-lit**: the metered development runs from **+3.451 stops** on the fire-hydrant sheet to **+6.000**, clamped, on the NYPD sheet, and nine of the ten carry the record's own under-lit note.

**Sun** — azimuth 219.8°, elevation 24.9° at 2017-11-01T15:07:14-04:00, from the photograph’s own EXIF DateTimeOriginal; 718.1 W/m² direct normal, sky at strength 0.0380, Filmic, **+5.41 stops**. Metered: **5.412 stops** on a linear median of **0.004229**, against a physical rule of 0.8, and the record carries its own under-lit note: a scene this far from a photographable level needs more than the 4 stops a photographer recovers hand-held.

## Verdict — the reference is a Queens bus terminal and the render has two newsstands, so neither half is really about the subject

**The pairing is wrong before the render is looked at.** The item asks for a New York newsstand and the photograph the chooser kept is filed as *MTA Queens Center* — a bus terminal frontage. J71 already records this item by name as one of six whose kept photographs answer none of its own recorded queries, and this is that failure in the published sheet: *"street_newsstand kept two street corners"*. Nothing in `pick_reference_photo` tests what a photograph is a picture of, only whether it has a licence, a size, a date and a derivable heading.

**The render's side of the pairing is thin too.** `props.per_kind` gives `newsstand: 2` among 876 props, so the class is placed and two of them stand in a dense Midtown radius. That is enough to confirm the kind exists and not enough to compare a newsstand's proportions, its magazine racks, its awning or its glazing — all of which is what a close-up reference would have been for.

**Newsstands are also one of the eight kinds that collapse to a single asset** across 314,105 placed objects (J58), so both of these are the same box at the same size, where the real city's stands are a DOT standard unit and a long tail of older ones.

**The photograph's highlights are clipped at 1.0**, so the two halves cannot be compared at the top end at all. Below that the agreement is unusually close: mean **0.942×**, p50 **1.023×**, an exposure gap of only **0.072 stops** — and chroma runs the other way, **1.844×**, the render carrying nearly twice the photograph's saturation, because 5.412 stops of lift on authored surface colours beats a clipped, flat source.

**And the sheet a reader should hold this one beside is J110.** The verification renderer places props through `data/processed/furniture/props_catalog.json`, which has 34 kinds, and it never reads `tiles/{tile}/signs.json`. So none of the **633,287 signs** or **19,814 signalised intersections** in this city's own data appears in this frame, or in any of the other 171, even though the models for fifteen of them sit in `blender_out/props` and 898 tiles carry the export. Only **20 prop kinds** appear anywhere in the pass.

## What matches

* **Two newsstands in the frame**, so the class is placed from data.
* **The median tone agrees to a fortieth**: p50 1.023× with a 0.072-stop exposure gap.
* **The record states its own limits before the assessment does**: no subject, a low-confidence reference heading, and an instruction to compare street width, storey height and material rather than composition.
* **The block is paved and marked**: 27,313 polygons with 12,088 white markings, 5,788 sidewalk, 4,278 roadbed, 3,372 curb, 751 plaza, 620 crosswalk and 341 median, and **0 dropped**.
* **The camera was not moved**, with 37.2 m of clear view along the azimuth.

## What does not match

* **The reference is a Queens bus terminal, not a newsstand** — J71 names this item by name.
* **The photograph's highlights are clipped at 1.0**, so the top end of the two halves cannot be compared.
* **Chroma 1.844×** — the render is nearly twice as saturated, which is the 5.412-stop lift, not a match.
* **One newsstand model for the whole city** (J58).
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
| the reference is not a photograph of the subject | `pick_reference_photo` ranks licence, size, date, sun height and derivable heading, and nothing tests what a photograph is a picture of (J71, which names this item) | **verification — open** |
| the newsstand cannot be compared at close range | a close-up reference paired with a street-scale frame, and one asset for the kind (J58) | verification + data — declared |
| chroma 1.844 and 5.412 stops of development | a shaded wall lifted five and a half stops against a clipped source (J83) | verification — declared |
| no signage of any kind in the frame | the verification renderer never reads the sign or signal export, and its 34-kind props catalogue has no kind for either (J110) | **verification — open** |
| ten sheets are the same picture | these items name a type rather than a place, so they share one representative camera; the set would read better if each stood somewhere its own subject is dense | verification — a design choice worth revisiting |
| no structures on any of the 4 tiles | four tiles in range and none has a structures file; 19 sheets in the pass share it (B13 remainder) | data — open |
| no cloud | nothing in this build reads a historical sky | reference — no source exists |
