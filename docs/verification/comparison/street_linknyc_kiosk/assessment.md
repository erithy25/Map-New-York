# LinkNYC kiosk (close-up)

`street_linknyc_kiosk` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Kew Gardens Rd 83rd Av td (2020-10-17) 02 - LinkNYC.jpg by Tdorante10, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2020-10-17 12:07:24, 1920x1280. [Commons page](https://commons.wikimedia.org/wiki/File:Kew_Gardens_Rd_83rd_Av_td_(2020-10-17)_02_-_LinkNYC.jpg) — the photograph carries no camera GPS and its view direction was not derived from the image, so its viewpoint confidence is **low**. A Link kiosk on Kew Gardens Road in Queens, photographed from a few metres: the slab's two advertising faces lit, the tablet and keypad panel, the braille plate, the base bolted to the sidewalk.

**Camera** — 40.755, -73.984 (NYC_TM -2871, 6108) at z 20.4 m NAVD88 | azimuth 0.0°, pitch 0.0° | 35 mm on 36 mm (54.4° horizontal, 54.4° on the long side) | 1280x854. This is one of **ten sheets in the pass rendered from this exact camera** — the same position, the same heading and the same 35 mm lens, each frame shaped to its own reference photograph so the horizontal field runs from 42.0° to 54.4° across the ten — each standing for a different object class and each lit at its own reference photograph's instant. The record is candid about what that means: *"This item names no subject and the reference photograph's own view direction was not derived from the image (confidence: low), so the two halves of this sheet are not guaranteed to face the same way -- compare them on street width, storey height and material, not on composition."* `subject_note` reads *"the item names no point subject"*, so there is no height probe, no sightline and no visible fraction on this record at all. The camera was **not moved**; the nearest built thing in the frame is `lm_c_times_square.0` **21.8 m** away and the view azimuth is clear for **37.2 m**. The ground under the lens reads 18.769 m NAVD88, the 10th percentile of 113 samples within 12.0 m.

**In the frame, in every one of the ten** — 4 building tiles (247,682 tris), 9 landmark models of which 2 fall inside the frame cone, 27,313 pavement polygons with 12,088 white markings and 620 crosswalk, **0 triangles of structures** with 4 tiles having no file, and a great pale north-facing wall filling the upper two thirds of the picture. Because that wall faces away from the Sun at every one of the ten instants, **all ten frames are under-lit**: the metered development runs from **+3.451 stops** on the fire-hydrant sheet to **+6.000**, clamped, on the NYPD sheet, and nine of the ten carry the record's own under-lit note.

**Sun** — azimuth 169.3°, elevation 39.1° at 2020-10-17T12:07:24-04:00, from the photograph’s own EXIF DateTimeOriginal; 836.2 W/m² direct normal, sky at strength 0.0337, Filmic, **+4.91 stops**. Metered: **4.907 stops** on a linear median of **0.006001**, against a physical rule of 0.14, and the record carries its own under-lit note: a scene this far from a photographable level needs more than the 4 stops a photographer recovers hand-held.

## Verdict — one kiosk in the frame, and its two lit faces are the same blank slots as every other sign in this build

**There is exactly one LinkNYC kiosk in this frame.** The render's `props.per_kind` gives `linknyc: 1` among 876 props. So the subject is present, barely, and a reader can confirm that the class is placed from data and stands at the right height beside a kerb. Nothing about the object's proportions at close range can be read from a street-scale frame whose nearest kiosk is a small slab.

**What the photograph is actually about is the two lit advertising faces, and those are blank here.** A Link kiosk is a double-sided 55-inch display; in the reference both faces are carrying a campaign. This build places sign and screen faces with named material slots and an exact 0..1 UV and no content, because no source records what a New York display is showing and no advertising copy was invented anywhere (DEVIATIONS B5, B15, B15a). So the kiosk's defining feature is a grey rectangle, for the same declared reason that leaves Times Square's screens blank.

**One Link kiosk in a Midtown frame is also low.** There are over 1,800 Link kiosks in the city and this camera's radius is dense Midtown sidewalk; the single placement suggests the source rows for this kind are sparse rather than that the block is empty.

**The frame is under-lit by nearly five stops** — 4.907 on a linear median of 0.006001 — and the tone follows: mean **1.105×**, p50 **1.235×**, contrast **0.544×**, chroma **0.308**, with the render's 95th percentile at 0.6994 against the photograph's 0.923.

**And the sheet a reader should hold this one beside is J110.** The verification renderer places props through `data/processed/furniture/props_catalog.json`, which has 34 kinds, and it never reads `tiles/{tile}/signs.json`. So none of the **633,287 signs** or **19,814 signalised intersections** in this city's own data appears in this frame, or in any of the other 171, even though the models for fifteen of them sit in `blender_out/props` and 898 tiles carry the export. Only **20 prop kinds** appear anywhere in the pass.

## What matches

* **One LinkNYC kiosk in the frame**, so the class is placed from data and stands at a plausible height beside the kerb.
* **876 props across fifteen kinds** in a 42° frame, including 475 trees, 161 Citi Bike dock units and 47 street lamps.
* **The record states its own limits before the assessment does**: no subject, a low-confidence reference heading, and an instruction to compare street width, storey height and material rather than composition.
* **The block is paved and marked**: 27,313 polygons with 12,088 white markings, 5,788 sidewalk, 4,278 roadbed, 3,372 curb, 751 plaza, 620 crosswalk and 341 median, and **0 dropped**.
* **The camera was not moved**, with 37.2 m of clear view along the azimuth.

## What does not match

* **Both advertising faces are blank**, which is what the photograph is a picture of (B15a).
* **One kiosk in a dense Midtown radius** against more than 1,800 in the city — the source rows for this kind look sparse.
* **Contrast 0.544 and chroma 0.308**, from a 4.907-stop lift on a shaded wall.
* **The object cannot be compared at close range**; the reference is a few metres from its subject and this frame is not.
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
| the kiosk's advertising faces are blank | sign and screen faces carry named material slots and a defined UV and no content, because no source records what a New York display shows (B15a) | **declared decision — the slots and UVs exist; the content binding is the open half** |
| one kiosk in the frame | the placement comes from the `linknyc` prop rows in range, and only one falls inside this radius | data — worth re-checking against the DoITT kiosk inventory |
| 4.907 stops of development | the shaded north-facing wall this camera points at (J83) | verification — declared |
| no signage of any kind in the frame | the verification renderer never reads the sign or signal export, and its 34-kind props catalogue has no kind for either (J110) | **verification — open** |
| ten sheets are the same picture | these items name a type rather than a place, so they share one representative camera; the set would read better if each stood somewhere its own subject is dense | verification — a design choice worth revisiting |
| no structures on any of the 4 tiles | four tiles in range and none has a structures file; 19 sheets in the pass share it (B13 remainder) | data — open |
| no cloud | nothing in this build reads a historical sky | reference — no source exists |
