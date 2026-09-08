# Charging Bull

`landmark_charging_bull` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Bowling Green NYC Feb 2020 15.jpg by Epicgenius, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2020-02-05 09:35:51, 1920x1440. [Commons page](https://commons.wikimedia.org/wiki/File:Bowling_Green_NYC_Feb_2020_15.jpg) — the photograph's own view direction is derived from the image at **high** confidence.

**Camera** — 40.705804, -74.013406 (NYC_TM -5358, 646) at z 9.0 m NAVD88 | azimuth 179.2°, pitch +0.0° | 35 mm on 36 mm (54.4° horizontal) | 1208x906. The camera stands on **this photograph's own EXIF GPS**, 25.9 m from the item's recorded viewpoint, and was **not moved**: the viewpoint is in open air on the ground, the view azimuth is clear for 150 m, the nearest built thing in the frame is `prop_lamp_cobra_davit_6` 3.4 m away, and no simulated agent stands within 60 m of it.

**Sun** — azimuth 139.4°, elevation 23.0° at 2020-02-05T09:35:51−05:00, from the photograph's own **EXIF DateTimeOriginal**; 695.4 W/m² direct normal, sky at strength 0.0389, Filmic, **+0.91 stops**. That date is a **Wednesday** and the crowd was drawn for a weekday. Both the instant and the position are the photograph's own.

**In the scene** — 4,854 kit pieces, 88 vehicles and 309 people; 20 city surfaces are dressed from the shared photographic catalogue.

## Verdict — the sculpture is in the frame and the record says its height is unknown, and both of those are true

**This is one of the closest pairings in the set.** Both halves look south down Broadway from Bowling Green on an overcast winter morning: the same avenue, the same granite barrier blocks along the plaza edge, bare street trees, flags on their poles, a crowd gathered at the same place in the middle distance, and the bull itself standing among them. The camera is on the photograph's own GPS and the Sun on its own EXIF instant, so nothing about the light or the position is assumed.

**The record reports the subject's height as unmeasured, and the sheet has to say why, because the sculpture is plainly there.** The height probe casts 17 rays at the recorded subject coordinate; **only 4 land on built fabric** and the highest is the bull's base plate, reported as **0.6 m below** the street-mode ground sampled 15 m around it. That reads like a buried landmark and is not one. The recorded coordinate is **4.0 m** from the model's origin and **3.2 m** from its nearest vertex, and the probe samples three rings at 0, 3 and 6 m: the centre ray passes clear of a 4.9 m sculpture, the 3 m ring just misses it, and the 6 m ring overshoots onto its base. **The bull's mesh spans its full published height above its own placement level, and it stands on the plaza in the frame** — the figures are in `blender_out/landmarks/catalog/charging_bull.json` and in docs/DEVIATIONS.md J74 rather than in this sheet's record. This is the probe's sampling geometry meeting the only subject in the set smaller than its own ring spacing, and it is recorded as such (docs/DEVIATIONS.md J74, amendment).

## What matches

* **The view is the view.** South down Broadway from Bowling Green, the plaza on the left, the Standard Oil and Cunard fronts on the right, and the avenue narrowing between them — the same composition in both halves, at high confidence, from the photograph's own position.
* **The sculpture is placed and visible**, standing on the plaza at the same point in the frame as the reference's, with a crowd around it.
* **The granite barrier blocks are there**, strung along the plaza edge in the roadway exactly as the photograph shows them — those are security bollards and they are modelled.
* **The trees are bare and the date is why.** The reference is 5 February and the leaf-off variants are selected from the photograph's own date.
* **The flags are on their poles** in the render as in the photograph, on the same frontages.
* **The crowd is the simulation's own** — 309 people on a Wednesday morning, 1 at LOD0, 42 at LOD1 and 266 at LOD2 — and it gathers where the photograph's does.
* **The fleet is a Lower Manhattan fleet**: 56 sedans, 17 SUVs, 7 yellow taxis, 5 boro taxis, a box truck, a black car and an ambulance.
* **The chroma matches the photograph almost exactly** — **0.0433** against **0.0417**, a ratio of **1.038**, the closest colour agreement of any sheet so far. Both halves are a grey winter morning over grey stone, which is the one condition under which this build's per-class materials are not the limiting factor.
* **155 scaffold pieces** stand in the scene: Lower Manhattan is permanently under sidewalk shed and the render shows it.

## What does not match

* **The frame is about half the photograph's brightness**: mean **0.2123** against **0.3922** (**0.541×**), standard deviation **0.1812** against **0.2611** (**0.694×**), 95th percentile **0.6432** against **0.9281**, 5th percentile **0.0597** against **0.0801**. The reference is a flat overcast whose sky is nearly blown; the render puts a 23° February sun at 139.4° into a clear sky, so the render has hard shadows the photograph has none of and a darker sky above them. The instant is the photograph's own — what is not the photograph's own is its **weather**, and nothing in this build reads a historical sky.
* **The bull is a shape rather than a sculpture at this distance.** It is 33.8 m from the lens and reads as a dark bronze mass; the reference at the same distance shows the same, so this is not a gap the sheet can measure — but no claim about the modelling of the sculpture itself is supported by this frame.
* **The traffic signals on their mast arms are the photograph's most conspicuous foreground objects and the render has none in the near frame.** The signal heads are placed city-wide; none falls in this cone at this distance.
* **The red-painted bike lane on the right of the photograph is not painted in the render.** Coloured lane surfacing is not among the marking kinds this build draws (J52 draws white and yellow).
* **`subject_visible` is `null` and no sightline was tested**, because no height was measured. On this sheet that is the correct output and it is also a loss: the one thing a sightline could have confirmed is the thing the sheet exists for.
* **530 pedestrians were dropped for standing in the carriageway without crossing**, 96 for not being on a walkable surface, 787 for the triangle budget, and **17 people and 18 vehicles were found inside buildings** and dropped for it.
* **1 cornice for every 300 windows**: 4,854 kit pieces of which **4,437 are windows** and only 15 cornices, 15 string courses and 8 parapets. Lower Manhattan's Beaux-Arts fronts carry heavy cornices, rustication and columned bases, and these are extrusions with openings.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the subject's height reads as unmeasured, and −0.6 m | the probe samples rings at 0, 3 and 6 m and the recorded coordinate is 4.0 m from a 4.9 m sculpture, so the rays miss it and land on its base plate; the bull itself is correctly placed and visible | **verification — open, DEVIATIONS J74 amendment** |
| mean 0.541×, hard shadows against none | the instant is the photograph's own and its **weather** is not: the reference is a flat overcast and the render puts a clear sky at the same instant. Nothing in this build reads a historical sky | reference — no source exists |
| no traffic signals in the near frame | signal heads are placed city-wide and none falls in this 54.4° cone at this distance | verification |
| no red bike-lane surfacing | coloured lane surfacing is not among the marking kinds the road stage draws (J52) | data |
| no sightline tested | it follows from the unmeasured height; the record says so rather than reporting a verdict it cannot support | verification |
| almost no cornice, rustication or columned base | the shell is extruded from a footprint and the kit's cornice is a generic profile; the classifier has no source for a modelled Beaux-Arts front | geometry |
| pedestrians and vehicles dropped in their hundreds | the placement rules — outside the radius, in the carriageway, not on a walkable surface, inside a building, over the triangle budget — each named with its count in the record | verification + performance |
