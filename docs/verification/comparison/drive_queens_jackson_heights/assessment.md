# Queens residential block: Jackson Heights side street with two-family homes

`drive_queens_jackson_heights` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Salvation Army Jax Hts jeh.jpg by Jim.henderson, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2018-08-19 19:02:46, 1920x1280. [Commons page](https://commons.wikimedia.org/wiki/File:Salvation_Army_Jax_Hts_jeh.jpg)

**Camera** — 40.75229, -73.88055 (NYC_TM 5865, 5809) at z 20.9 m NAVD88 | azimuth 165.0°, pitch +0.0° | 35 mm on 36 mm (54.4° horizontal) | 1280x854. The camera stands on **this photograph's own EXIF GPS**, 209.3 m from the item's recorded viewpoint, and was **not moved**: the viewpoint is in open air on the ground, the view azimuth is clear for 29.6 m, and the nearest built thing in the frame is `t_5_5_red_brick` 20.5 m away. The nearest simulated agent is **`agent_veh_rav4_fhv_157.47` 8.1 m away, dead ahead**.

**Sun** — azimuth 280.2°, elevation **7.6°** at 2018-08-19T19:02:46−04:00, from the photograph's own **EXIF DateTimeOriginal**; 348.9 W/m² direct normal, sky at strength 0.0655, Filmic, **+2.32 stops**. That is the lowest Sun and the largest exposure correction of any sheet in the set. That date is a **Sunday** and the crowd was drawn for one.

**In the scene**, within 900.0 m of the camera and not all of it in frame — 8/8 building tiles (546,910 tris), 0 landmark models, 27,433 pavement polygons (14,278 white marking, 4,154 roadbed, 3,994 sidewalk, 3,306 curb, 827 crosswalk, 538 yellow marking, 177 parking lot, 90 median, 69 plaza), 317 props of the 2,470 in range, 5,278 kit pieces, 69 vehicles and 361 people; 4,500,055 triangles. Ground mesh 96,800 triangles, 0 holes. 16 city surfaces are dressed from the shared photographic catalogue.

## Verdict — a photograph of a 1932 citadel for an item that asked for a side street, and a parked car filling the frame

**Two things make this sheet unreadable as a comparison, and both are stated rather than hidden.**

**First, the reference is of a different kind of thing.** The item is *"Jackson Heights side street with two-family homes"*; the photograph is **The Salvation Army's 1932 Art Moderne citadel** — limestone ashlar, curved glass-block bays, a bronze crest and lettering — seen head-on from its own forecourt. It is a Jackson Heights building and it is not a side street of houses. This is the same class of fault as `drive_queens_bayside`: the fetch screens on keywords and a geosearch radius, the chooser ranks on light, EXIF, Sun height, azimuth error and distance band, and **nothing in either asks what the photograph is a picture of** (docs/DEVIATIONS.md J71).

**Second, an SUV stands 8.1 m from the lens, dead ahead, and fills about a third of the frame.** That is the cost of a rule the project holds deliberately: a viewpoint must never move because a simulated agent happened to be there on this seed, or the same slug would render from a different place on every run and the sheet would stop being a comparison of one view (J49). The record names the vehicle and its distance so a reader knows what they are looking at.

**What can still be read is the fabric behind it**, and it is right: four-storey red brick with punched openings, projecting sills, window air-conditioners and a yellow centre line down the carriageway. That is a Jackson Heights street.

## What matches

* **The building stock is the right stock.** 3,913 windows, **723 window accessories** — the window air-conditioners that decide whether a Queens street reads as one — 298 parapets, 134 entry doors, 52 bulkheads, 37 string courses and 31 fence pieces stand in the scene out of 5,278.
* **The clock is the photograph's own**, and it is the hardest clock in the set: 19:02:46 on 19 August 2018, a Sunday, with the Sun at **7.6°** and only **348.9 W/m²** of direct normal irradiance. The renderer opened **+2.32 stops** for it, the largest correction on any sheet, and the frame still reads.
* **This is the only sheet in the set that carries more colour than its photograph**: chroma **0.0457** against **0.0329**, a ratio of **1.389**. The photograph is limestone under a flat white overcast; the render is red brick in the last of a low Sun.
* **The road is a road with real markings**: 4,154 roadbed, 3,306 curb and 3,994 sidewalk polygons, with **14,278 white and 538 yellow marking polygons** and 827 crosswalk polygons in range — the highest marking count in the set (J52).
* **The crowd and the fleet are the simulation's own**: 361 people and 69 vehicles at 19:02 on a Sunday, 1 at LOD0, 22 at LOD1 and 338 at LOD2, drawn from all **36** baked bodies with none folded (J62). The fleet is 32 sedans, 14 SUVs, 9 yellow taxis, **8 boro taxis**, 3 black cars, 1 box truck, 1 van and 1 MTA bus — a plausible outer-Queens mix.
* Nothing was dropped for being missing: 8 of 8 building tiles, 0 LOD substitutions, 0 pavement polygons dropped, 0 holes in the ground, and **no prop kind unplaced**.

## What does not match

* **The reference is a photograph of a single institutional building** and the render is a street. Composition, framing, storey height, material and street width are all incomparable here by construction.
* **A parked SUV occupies the middle of the frame** from 8.1 m. Correct behaviour under J49 and a real cost to this sheet.
* **The frame is well under half the photograph's brightness and under a third of its contrast**: mean **0.1998** against **0.5224** (**0.382×**), standard deviation **0.0867** against **0.2958** (**0.293×**), 95th percentile **0.3447** against **0.9950**, 5th percentile **0.0493** against **0.0476**. The photograph is a pale limestone elevation under a blown-out white overcast — its 95th percentile is 0.995 — and the render is red brick at a 7.6° Sun. The two are lit by different weather at the same instant.
* **There is no cornice line at all.** **2 cornices** across 5,278 kit pieces. Jackson Heights' brick blocks carry corbelled brick cornices and terracotta banding, and the classifier has no source for either.
* **Of the 2,470 props in range only 317 were placed** — the largest shortfall in the set — at a triangle budget of 1,242,963, along with part of the kit (cap 1,226,602) and 22 opaque impostor cards.
* **422 pedestrians were dropped for not being on a walkable surface**, the highest such count in the set, along with 174 to the triangle budget and 100 for standing in the carriageway without crossing.
* **179 trees stand within 459.3 m and 65 are species-substituted**; 177 are drawn at the height their own rows record, at a mean scale of **0.929**, and **two fell outside the declared scale band** and keep their assets' own size (J70).
* **Two surfaces still sit at the albedo cap** — `roof_membrane` and `wood_clapboard` (J66). `concrete` was moved to a scan that does not bind it, and **this frame's statistics did not change when it was**; the frame in the set that did move is Broadway at Wall Street, which is the only one made mostly of stone and concrete.
* **50 sidewalk-shed pieces are in the scene**, from DOB permits active on 2026-09-05, against a photograph from 2018.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the reference is a 1932 citadel and the item asked for a side street of houses | the fetch screens on keywords and a geosearch radius, the chooser ranks on properties of the photograph as a photograph; neither tests what it is a picture of | **reference — open, DEVIATIONS J71** |
| an SUV 8.1 m from the lens fills a third of the frame | a simulated agent must never move a viewpoint, or the sheet stops being a comparison of one view (J49); the record names the vehicle and its distance instead | stated choice |
| mean 0.382× and 95th percentile 0.345 against 0.995 | a pale limestone elevation under a blown-out white overcast against red brick at a 7.6° Sun; the same instant, different weather | reference |
| standard deviation 0.293× | a 7.6° Sun puts almost nothing in this frame in direct light, and +2.32 stops of exposure lifts the whole frame rather than separating it | stated choice |
| no cornice line | 2 cornices across 5,278 kit pieces; the classifier has no source for a Queens brick block's corbel course or terracotta banding | geometry |
| 317 of 2,470 props placed | triangle budget 1,242,963, declared on the sheet; the largest prop shortfall in the set | performance |
| 422 pedestrians dropped as not on a walkable surface | the crowd is placed city-wide and this frame's radius reaches 900 m of rooftops, rail and water that carry no walkable surface | verification |
| 65 of 179 trees species-substituted | no modelled species matched exactly; the nearest by size and taxon was used | data |
| two trees outside the scale band | their measured heights are further from the nearest exported size than the declared band allows, so they keep their assets' own size and are counted (J70) | data |
| sidewalk sheds of the wrong year | the shed source is DOB permits active on 2026-09-05 and the photograph is from 2018 | reference |
