# Brooklyn brownstone block: Park Slope, Seventh Avenue / Garfield Place

`drive_brooklyn_park_slope_7th_ave` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:195 Garfield Place.jpg by Beyond My Ken, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), 2013, 1920x1887. [Commons page](https://commons.wikimedia.org/wiki/File:195_Garfield_Place.jpg)

**Camera** — 40.67247, -73.97746 (NYC_TM -2321, -3057) at z 29.1 m NAVD88 | azimuth 32.4°, pitch +0.0° | 35 mm on 36 mm (54.4° horizontal) | 1054x1036. The camera stands on **this photograph's own EXIF GPS**, 36.6 m from the item's recorded viewpoint, and was **not moved**: the viewpoint is in open air on the ground, the view azimuth is clear for 38.7 m, the nearest built thing in the frame is `prop_tree_honeylocust_small_2` 8.4 m away, and no simulated agent stands within 60 m of it.

**Sun** — azimuth 95.3°, elevation 43.5° at 2013-06-21T09:30−04:00; 860.0 W/m² direct normal, sky at strength 0.0328, Filmic, +0.00 stops. The photograph carries a **year only**, so 21 June 09:30 is assumed. That date is a **Friday** and the crowd was drawn for **a weekday**.

**In the scene**, within 756.6 m of the camera and not all of it in frame — 6/6 building tiles (492,134 tris), 2 landmark models of which **0 can fall inside the 54.4° frame**, 23,064 pavement polygons (9,385 white marking, 5,341 sidewalk, 4,038 roadbed, 3,131 curb, 541 crosswalk, 291 yellow marking, 274 median, 44 parking lot, 19 plaza), 343 props of the 1,010 in range, 4,393 kit pieces, 88 vehicles and 364 people; 4,500,137 triangles. Ground mesh 89,872 triangles, 0 holes. 19 city surfaces are dressed from the shared photographic catalogue.

## Verdict

**This sheet is the one that found J68 and J70, and what it shows now is a different picture of the same disagreement.** The two halves are still not of the same thing: the camera stands on the photograph's own GPS at the corner of Seventh Avenue and Garfield Place and looks **up Seventh Avenue**, while the photograph looks along **Garfield Place** at a row of Romanesque Revival houses. The item names no subject and the photograph's own view direction was never derived from the image (confidence **medium**), so the sheet's own caption forbids reading the two as one view.

**What is in the render's frame is a green sidewalk shed, a brick service wall and a roof bulkhead.** The shed is not an error: it is a DOB-permitted sidewalk shed on a real building on this block, from the permit set active on **2026-09-05**, and the photograph is from **2013**. It is a real object of the wrong decade standing exactly where the record says it stands.

**Two things in this frame were wrong on the last render of it and are not now.** The large mass in the upper centre is Old First Reformed Church, and until J68 it was drawn as a sixteen-storey apartment slab carrying a grid of window bays, a wooden gravity tank and two rooftop bulkheads — the counts are in that entry rather than here — while it is now a mass with almost no glazing, which is a plain statement rather than a fabricated apartment house. And the street trees now stand at the height the tree census measured them — **204 of them at a mean scale of 0.933**, none outside the scale band (J70). The frame's mean rose to **0.2244** and its standard deviation to **0.1588** on those two changes; the dappled shadow across the carriageway and the sunlit brick above the shed are what they bought.

## What matches

* **The street fabric is right for this corner.** 2,580 windows, 298 storefront and 52 storefront-interior pieces, 295 entry doors, 280 window accessories, 153 parapets, 148 bulkheads, **147 fire escapes**, 129 cornices, 89 fence pieces, 82 string courses, 44 quoins and 12 pilasters stand in the scene out of 4,393 kit pieces. Four-storey party-wall brick with fire escapes, punched openings and a shopfront band is what Seventh Avenue is.
* **The sidewalk shed is real and it is the right shed.** 56 scaffold pieces are in the scene, drawn from DOB NOW sidewalk-shed permits joined by BIN — not decoration, and not a generic prop. It is painted the hunter green the city requires.
* **The light is directional and the shadows are hard.** A tree casts dappled shade across the footway and out onto the carriageway, the shed's fascia takes grazing morning light, and the brick above it is sunlit. The sky is open above the roofline.
* **The camera was not moved.** The photograph's own GPS was usable, the clearance probe found 38.7 m of open air along the view azimuth, and the render stands where the picture was taken. That is the best case this pipeline has.
* **The road is a road**: 4,038 roadbed, 3,131 curb and 5,341 sidewalk polygons carrying asphalt and concrete from their own material names, with the kerb reading by its reveal and a crosswalk at the corner.
* **The crowd and the fleet are the simulation's own** — 364 people and 88 vehicles at 09:30 on a weekday, 1 at LOD0, 23 at LOD1 and 340 at LOD2. The fleet is 52 sedans, 16 SUVs, 11 yellow taxis, 3 boro taxis, 2 black cars, 2 vans, 1 MTA bus and **1 ambulance**.
* Nothing was dropped for being missing: 6 of 6 building tiles, 0 LOD substitutions, 0 pavement polygons dropped, 0 holes, and **no prop kind unplaced**.

## What does not match

* **The two halves face different ways.** The photograph's subject is a row of individually articulated houses on Garfield Place — bay windows, conical turret roofs, deep bracketed cornices, four different brick and brownstone colours in adjacent houses. The render looks up Seventh Avenue at a shed and a service wall. The item names no subject and the direction was never derived from the image, so this is a property of the pairing, not of the render.
* **The photograph's block face has no individual houses in the model.** Its five or six distinct houses are carried by two large footprints in the source, one of them classed as an elevator apartment building; there is no row of separate shells to give separate colours to. That is a footprint-data fact, not a rendering one.
* **The frame is less than half as bright as the photograph and carries about a third of its colour**: mean **0.2244** against **0.4799** (**0.468×**), standard deviation **0.1588** against **0.2928** (**0.542×**), 95th percentile **0.5221** against **0.9644**, 5th percentile **0.0140** against **0.0484**. Part of that is a difference of weather and exposure — the photograph is a bright overcast with a blown white sky, the render a clear sky at an assumed instant, and a camera stops down where this renderer never does. **The chroma gap is not**: **0.0534** against **0.1478**, a ratio of **0.361**, with `concrete`, `roof_membrane` and `wood_clapboard` at the albedo cap with the wrong source material behind them and `brownstone` drawn from a travertine scan (J66).
* **The church has almost no windows where a Romanesque church has two tiers of tall round-arched ones.** Capping its elevation at the storey count its own facade class publishes stopped it being a sixteen-storey apartment house; it did not give it the glazing a church actually carries. That is stated as a rule in J68 and it is the honest half of a fix, not the whole of one.
* **Both landmark models in the scene are behind or beside the camera** — the Soldiers' and Sailors' Memorial Arch and the Brooklyn Public Library — so 2 placed is not 2 in frame.
* **No vehicle is in frame** although 88 are placed and all 88 are at LOD2. The photograph has cars parked along the kerb, which is what that street looks like at any hour.
* **667 props in range were not placed** — triangle budget 1,291,418 — along with part of the kit (cap 1,316,574) and **27 opaque impostor cards**.
* **204 trees stand within 286.6 m and 48 are species-substituted.** They are drawn at the height their own row records; the species they are drawn *as* is the nearest by size and taxon.
* The Sun is on an assumed instant; the photograph carries a year and nothing finer.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the two halves face different ways | the item names no subject and the photograph's direction was never derived from the image (confidence medium); the camera looks up Seventh Avenue and the photograph along Garfield Place | reference |
| the photograph's houses have no individual shells | the block face is two large footprints in the source, one classed as an elevator apartment building; no source records an individual house's colour | data |
| mean 0.468×, 95th percentile 0.522 against 0.964 | a bright overcast with a blown white sky against a clear sky at an assumed instant, plus a camera's automatic exposure against a renderer that never stops down | reference + stated choice |
| chroma 0.361× | `concrete`, `roof_membrane` and `wood_clapboard` at the albedo cap with the wrong source material, and `brownstone` drawn from a travertine scan (J66) | material |
| a church with almost no glazing | its elevation is capped at the storey count its facade class publishes, which stops the sixteen-storey grid and does not supply the two tiers of arched windows a church carries; stated as a rule (J68) | geometry — open |
| a sidewalk shed of the wrong decade | the shed source is DOB permits active on 2026-09-05 and the photograph is from 2013; the city is built to today's permits | reference |
| 2 landmarks placed, 0 in frame | both stand behind or beside the camera; the count is a scene count and the caption says which is which (J61) | — (not a gap) |
| no vehicle in frame | placement is city-wide and the frame is not; none of the 88 falls inside this 54.4° cone | verification |
| 667 props and part of the kit dropped | triangle budgets 1,291,418 and 1,316,574, declared on the sheet | performance |
| 48 of 204 trees species-substituted | no modelled species matched exactly; the nearest by size and taxon was used | data |
| Sun on an assumed instant | the photograph carries a year and nothing finer | reference |
