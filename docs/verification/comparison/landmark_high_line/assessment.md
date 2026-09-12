# High Line

`landmark_high_line` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:The High Line Hotel 001.jpg by Kidfly182, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2023-01-21 13:36:45, 1920x1440. [Commons page](https://commons.wikimedia.org/wiki/File:The_High_Line_Hotel_001.jpg) — the photograph's own view direction **was not** derived from the image; confidence is **medium**.

**Camera** — 40.746078, -74.005317 (NYC_TM -4672, 5118) at z 13.6 m NAVD88 | azimuth 29.0°, pitch 0.0° | 35 mm on 36 mm (54.4° horizontal) | 1208x906. The camera stands on **this photograph's own EXIF GPS**, 57.7 m from the item's recorded viewpoint, and was **not moved**. Its eye sits **10.7 m above the terrain** — the High Line deck, **30 ft (9.1 m)** above the street on the West Side Line viaduct, plus a 1.6 m standing eye. The ground under it reads 2.886 m NAVD88 from **16 samples within 5.0 m**, range 2.75 to 3.09 m: the viewpoint note names the raised surface the photographer stood on, so the heightmap height at the point itself is the ground rather than a percentile of its neighbourhood. The view azimuth is clear for 150 m.

**This sheet carries its own instruction for reading it.** The item names no point subject and the reference's view direction was not derived from the image, so the record states: *"the two halves of this sheet are not guaranteed to face the same way — compare them on street width, storey height and material, not on composition."* The axis is level and the lens is the default 35 mm, because there is nothing to aim at.

**Sun** — azimuth 203.5°, elevation 26.0° at 2023-01-21T13:36:45−05:00, from the photograph's own **EXIF DateTimeOriginal**; 730.3 W/m² direct normal, sky at strength 0.0375, Filmic, **+2.47 stops**, measured from the linear frame's median of **0.032579** (J83). The physical rule would have given **0.73 stops**.

**In the scene** — 4,500,259 triangles: 6 building tiles (211,196 tris), 5 landmark models of which 2 fall inside the 54.4° frame, 24,685 pavement polygons, 1,388 props, 5,386 kit pieces, 20 park-ground meshes, **35,460 triangles of structures**, 71 vehicles and 252 people.

## Verdict — read on street width, storey height and material as the record asks, this is a fair Chelsea; the two halves are not looking at the same thing and the sheet says so first

**The photograph is a close view of the High Line Hotel's red-brick Gothic front**, seen from the deck through a planted arbour of dried vine and string lights, with the hotel's own sign on the trellis, steep slate roofs and dormers above. **The render looks north up Tenth Avenue** from the same deck: a canyon of brick and tan mid-rise walls, a roadway full of traffic, crosswalks and sidewalk crowds, and the Hudson Yards towers closing the distance. Both face 29.0°. They are not of the same object, and the record refuses to claim they are.

**What can be compared, compares well.** Street width, storey height and material are the three the record names, and on all three the render is a credible West Chelsea: four- to six-storey brick and painted-brick walls at the right height either side of a wide avenue, window rhythm at the right pitch, fire escapes on the older fronts, and the glass towers where Hudson Yards actually stands.

**Two things are right here that were not right in earlier passes.** The camera sits on the viaduct at the deck's real height rather than on the street below it, and **35,460 triangles of structures** stand in this frame — the largest structures count on any sheet in the set, which is the elevated viaduct itself being drawn (B13). The High Line is also the nearest landmark in the cone at **237.9 m** and **0.1° off axis**, which is what standing on it and looking along it should produce.

## What matches

* **The deck height is the deck's height.** 30 ft of viaduct plus a 1.6 m eye, and the ground under the camera measured at the point rather than from its neighbourhood, because a terrace metres above a plaza 4 m away would otherwise put the camera underground.
* **The viaduct is built.** 35,460 triangles of structures across 4 imported tiles — the elevated line the photograph is standing on.
* **Street width and storey height are Chelsea's.** Four to six storeys of brick either side of a wide avenue, with the taller blocks set back where the neighbourhood's are.
* **The material palette is the right one.** 237 material slots resolved against the shared photographic catalogue — red brick at 3.24 m, brown brick, brownstone, stucco, tan brick, precast, white glazed brick — and the render's walls read as brick rather than as flat colour.
* **The older fronts carry their ironwork.** 127 fire escapes, 116 scaffold pieces, 58 quoins, 55 cornices and 39 string courses.
* **The traffic is a Tenth Avenue fleet on a Saturday.** 71 vehicles — **26 sedans, 18 yellow taxis, 9 SUVs, 8 black cars, 6 boro taxis, 2 box trucks, a van and an NYPD car** — and the crowd clock reports **Saturday**, the day type for 2023-01-21, which was one.
* **Both halves are leaf-off and the date is why.** The reference is 21 January; **62 trees are drawn from their modelled branches** within 120 m in bare-canopy form, with 346 impostor cards beyond.
* **Citi Bike is a station**: 413 dock units in range (Stage 40).
* **The near park ground sits on the terrain.** Within 150 m the under-fraction is **0.0149**, median clearance **0.202 m**.
* **The Hudson is drawn** — 2,390 quads on the flattened water surface — and Hudson Yards stands at **931.0 m**, 8.7° off axis, where it belongs.

## What does not match

* **Composition, and the record says so before a reader can.** A medium-confidence heading and no named subject mean the frames were never going to line up. This is a pairing limit, not a world gap.
* **The High Line's own planting is absent.** The photograph's foreground is the park: dried perennials, a vine arbour, string lights. On the deck the render has none of that. 408 trees are in range and **1,335 tree rows did not fit the props budget**; the High Line's planted beds are not a class this build carries at all.
* **The brightest gap is the development, not the scene.** Median **0.4973** against **0.2985** (**1.666×**), mean **0.5285** against **0.3804** (**1.389×**). The photograph's own median sits **1.312 stops** below the middle-grey convention and the render's **0.233** above it — a difference of **1.545 stops**, which is most of that ratio before the scene contributes anything (J83).
* **Less contrast, no blown highlight.** Standard deviation **0.2305** against **0.2733** (**0.843×**); the photograph reaches **1.0** at the 95th percentile and the render **0.8706**.
* **Chroma runs the other way here** — **0.0780** against **0.0542**, a ratio of **1.439**. The reference is a flat winter grey over dark brick; the render's tan and brick walls under a clear Nishita sky are more colourful than the day was.
* **No overcast.** The reference's light is flat and sourceless; the render puts a 26.0° January sun at 203.5° into a clear sky. Nothing in this build reads a historical sky.
* **The traffic queues nose to tail across the full width.** Seventy-one vehicles stand in a frame of one avenue block, most of them in two dense ranks. A Saturday afternoon on Tenth Avenue moves; this reads as a signal-held queue in every lane at once.
* **The crowd is thin where the traffic is thick.** 252 people against a density table asking for **3,072** over the simulated ring: **1,285 were dropped at the triangle budget**, 1,166 for being outside the radius, 163 for standing in the carriageway without crossing, 129 for not being on a walkable surface and **4 for being inside a building**.
* **Vehicles were dropped for the same reasons.** 259 outside the radius, **258 at the triangle budget**, 14 not on a carriageway, and **16 bodies with no rider** — bicycles, e-bikes and pedicabs the fleet exports riderless, so they are dropped rather than drawn. The photograph's neighbourhood is full of them.
* **Only 1 vehicle and 1 person are at LOD0.** 67 of 71 vehicles and 197 of 252 people are at LOD2, so most of the crowd and fleet in this frame are their coarsest form.
* **Far park ground sinks into the terrain**: beyond 400 m the under-fraction is **0.2792** over 1,594 samples, minimum clearance **−8.467 m**, z-fighting **0.027**. Within 150 m it is clean.
* **Eight prop kinds were wanted in range and had no asset**: 5 misc structure, 3 drinking fountain, 3 vending machine, 2 artwork, 2 passenger-information sign, 1 parks building, 1 parks comfort station, 1 payphone.
* **2 of the 6 tiles in range have no structures file.**

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the two halves are not of the same thing | the item names no point subject and the reference's heading was not derived from the image (medium confidence); the record directs the comparison to street width, storey height and material instead | **reference — declared, read as instructed** |
| the High Line's planting is absent | the park's perennial beds and vine arbour are not a class this build models; 1,335 tree rows were dropped at the props triangle budget on top of that | **geometry — open, no class for park planting** |
| p50 1.666×, mean 1.389× | the photograph is developed 1.312 stops under the grey convention and the render 0.233 over it, a 1.545-stop difference before the scene (J83) | reference |
| sd 0.843×, no highlight near white | the recovered render has no headroom; the photograph holds a blown sky | reference |
| chroma 1.439× — the render is more colourful than the day | a flat winter grey reference against a clear Nishita sky and brick walls resolved from the photographic catalogue | reference — no source for a historical sky |
| traffic queues nose to tail in every lane | the traffic model's signal state at this instant, at a density the table set for a Saturday | verification |
| 252 people against a table asking 3,072 | the 1,125,000-triangle agent budget dropped 1,285 pedestrians, and the placement rules the rest, each with its count | performance + verification |
| 67 of 71 vehicles at LOD2 | the LOD ladder at this distance and budget | performance |
| 16 riderless bodies dropped | the fleet exports bicycle, e-bike and pedicab bodies without a rider | geometry |
| 0.2792 of far park-ground samples under the terrain, minimum −8.467 m | surfaces draped on the 2 m heightmap against a scene edge coarsened to 40 m | verification |
| eight prop kinds unmapped | no asset exists for those kinds | data |
