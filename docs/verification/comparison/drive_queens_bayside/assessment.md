# Queens residential block: Bayside

`drive_queens_bayside` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:2024-06-18 14 45 53 View south along Interstate 295 (Clearview Expressway) from the pedestrian overpass at 42nd Avenue in Queens, New York City, New York.jpg by Famartin, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2024-06-18 14:45:53, 1920x1440. [Commons page](https://commons.wikimedia.org/wiki/File:2024-06-18_14_45_53_View_south_along_Interstate_295_(Clearview_Expressway)_from_the_pedestrian_overpass_at_42nd_Avenue_in_Queens,_New_York_City,_New_York.jpg)

**Camera** — 40.76300, -73.77200 (NYC_TM 15026, 7044) at z 25.2 m NAVD88 | azimuth 0.0°, pitch +0.0° | 35 mm on 36 mm (54.4° horizontal) | 1208x906. The camera stands on **the item's recorded viewpoint** — the photograph's own EXIF GPS is **566.6 m** away, far past the 250 m band, so it was not stood on — and was then **moved 32.2 m onto the nearest sidewalk**, because the recorded viewpoint is hard against `t_15_7_struct_station_house`, 0.1 m ahead along the view azimuth. From the new point the view is clear for 60 m and the nearest built thing in frame is `prop_tree_honeylocust_large_24` 18.6 m away.

**Sun** — azimuth 241.3°, elevation 61.3° at 2024-06-18T14:45:53−04:00, from the photograph's own **EXIF DateTimeOriginal**; 921.7 W/m² direct normal, sky at strength 0.0309, Filmic, +0.00 stops. That date is a **Tuesday** and the crowd was drawn for **a weekday**.

**In the scene**, within 720.0 m of the camera and not all of it in frame — 4/4 building tiles (212,356 tris), 0 landmark models, 21,221 pavement polygons (7,333 white marking, 4,286 sidewalk, 4,237 roadbed, 3,062 curb, 858 parking lot, 622 yellow marking, 446 crosswalk, 376 median, 1 plaza), 453 props of the 639 in range, 2,445 kit pieces, 73 vehicles and 265 people; 3,172,448 triangles. Ground mesh 88,200 triangles, 0 holes. 15 city surfaces are dressed from the shared photographic catalogue.

## Verdict — the reference is a photograph of something else, and it is not the chooser's fault

**The item asked for a residential street and its reference is a six-lane Interstate.** The fetch recorded its own queries — *"Bayside Queens houses residential street"* and *"Bayside, Queens" house* — and the three photographs it kept are **Interstate 295 seen from a pedestrian overpass**, a Flickr picture titled *"Needs Work"*, and *Lawrence Cemetery*. None of them is a residential street. The chooser can only rank what the fetch kept, and it ranked the only one with a real EXIF timestamp and GPS to the top. That the GPS is **566.6 m** away is recorded and the camera was correctly not moved to it (J60); what is not yet caught anywhere is that the photograph is of a different *kind of place* (docs/DEVIATIONS.md J71).

**Nothing below is a comparison of two views.** The photograph is a sunken interstate under a clear sky from 6 m up; the render is a Queens commercial strip at eye level. What the render can be judged on is whether it is a plausible Queens street, and it is.

## What matches

* **It is recognisably outer-borough Queens.** Two- and three-storey brick and stucco taxpayers with continuous shopfronts under awnings, a wide roadway with kerbside parking on both sides, low parapets, and a rooftop plant. **325 storefront and 38 storefront-interior** pieces stand in the scene out of 2,445, with 1,448 windows, 291 window accessories, 131 parapets, 117 entry doors and 89 rooftop cooling towers.
* **The New York City flag is the New York City flag.** A flagpole in the middle of the frame flies the blue-white-orange municipal flag with its seal — the right one of the two variants, which it was not before J58.
* **The clock is the photograph's own.** The Sun is placed from EXIF `DateTimeOriginal` — 18 June 2024 at 14:45:53, a Tuesday, elevation 61.3°, 921.7 W/m² — so the light is not assumed, and it shows: hard shadows under the parked cars, sunlit stucco on the west side, a lit brick elevation on the east.
* **The road is a road with real markings**: 4,237 roadbed, 3,062 curb and 4,286 sidewalk polygons, **858 parking-lot polygons** — the strip-mall aprons Queens is full of — and 7,333 white and 622 yellow marking polygons in range (J52).
* **This is the closest colour match in the set so far**: chroma **0.0517** against the photograph's **0.1111**, a ratio of **0.465**, and mean **0.2944** against **0.5632** (**0.523×**).
* **The trees are at their measured height**: all 196 scaled, mean **0.928**, none outside the declared band (J70).
* **Nothing was capped away except props**: 0 tiles missing, 0 LOD substitutions, 0 pavement polygons dropped, 0 holes, no kit cap, and no pedestrian or vehicle dropped for the triangle budget.

## What does not match

* **The two halves are of different kinds of place**, for the reason the verdict gives. Street width, storey height, material and framing are all incomparable here.
* **The item is named "residential block" and the render is a commercial strip.** The recorded viewpoint is *215th Street near 42nd Avenue, looking north*, and 32.2 m of clearance walking put the camera on a shopfront block. The move is correct behaviour — the viewpoint was 0.1 m from a station house — but the sheet no longer stands where the item's own note says.
* **The frame is about half the photograph's brightness**: mean **0.2944** against **0.5632**, 95th percentile **0.4863** against **0.8745**, 5th percentile **0.0356** against **0.1130**. The photograph is a sunlit open highway with sky filling its upper third; the render is a street with buildings filling its upper half. A camera stops down on the first and this renderer never does.
* **The facades carry no cornice line worth the name** — 11 cornices and 11 string courses across 2,445 pieces. Queens taxpayers carry brick corbel courses and pressed-metal cornices, and the classifier has no source for them.
* **186 props in range were not placed** — triangle budget 1,398,827 — and **24 opaque impostor cards were dropped**.
* **70 of the 196 trees are species-substituted.** They are drawn at the height their own rows record; the species they are drawn *as* is the nearest by size and taxon.
* **Three surfaces sit at the albedo cap with the wrong source material behind them** — `concrete`, `roof_membrane` and `wood_clapboard` (J66).
* **Every one of the 265 people is at LOD2** and every one of the 73 vehicles too; nothing in this frame is at close-up fidelity.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the reference is a photograph of an Interstate | the fetch kept three photographs for a "residential street" query, none of which is one; the chooser ranks what was kept and cannot reject a subject it has no test for | **reference — open, DEVIATIONS J71** |
| the camera stands on a commercial strip, not a residential block | the recorded viewpoint is 0.1 m from `t_15_7_struct_station_house`, so the camera was walked 32.2 m onto the nearest sidewalk | verification |
| mean 0.523× and 95th percentile 0.486 against 0.875 | a sunlit open highway with sky filling its upper third against a street with buildings filling its upper half, plus a renderer that never stops down | reference + stated choice |
| chroma 0.465× | `concrete`, `roof_membrane` and `wood_clapboard` at the albedo cap with the wrong source material (J66) | material |
| no cornice line | 11 cornices and 11 string courses across 2,445 kit pieces; the classifier has no source for a Queens taxpayer's corbel course or pressed-metal cornice | geometry |
| 186 props not placed and 24 impostor cards dropped | triangle budget 1,398,827, declared on the sheet | performance |
| 70 of 196 trees species-substituted | no modelled species matched exactly; the nearest by size and taxon was used | data |
| everything at LOD2 | the LOD selector keys off distance and nothing in this frame is near enough for LOD0 | performance |
