# Queens residential block: Bayside

`drive_queens_bayside` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:2024-06-18 14 45 53 View south along Interstate 295 (Clearview Expressway) from the pedestrian overpass at 42nd Avenue in Queens, New York City, New York.jpg by Famartin, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2024-06-18 14:45:53, 1920x1440. [Commons page](https://commons.wikimedia.org/wiki/File:2024-06-18_14_45_53_View_south_along_Interstate_295_(Clearview_Expressway)_from_the_pedestrian_overpass_at_42nd_Avenue_in_Queens,_New_York_City,_New_York.jpg)

**Camera** — 40.763, -73.772 (NYC_TM 15026, 7044) at z 25.2 m NAVD88 | azimuth 0.0°, pitch +0.0° | 35 mm on 36 mm (54.4° horizontal) | 1208x906.

**Sun** — azimuth 241.3°, elevation 61.3° at 2024-06-18T14:45:53-04:00 (EXIF DateTimeOriginal); 921.7 W/m² direct normal, sky at strength 0.0309, Filmic, +1.21 stops.

**In the scene**, within 720.0 m of the camera and not all of it in frame — 4 building tiles (212,356 tris), 0 landmark models, 21,221 pavement polygons (7,333 white, 4,286 sidewalk, 4,237 roadbed, 3,062 curb, 858 parking lot, 622 yellow, 446 crosswalk, 376 median, 1 plaza), 2941 props of the 3,021 in range, 2,445 kit pieces, 73 vehicles and 265 people; 2,585,734 triangles. Ground mesh 88,200 triangles, 0 holes. 15 city surfaces are dressed from the shared photographic catalogue.

## Verdict — the reference is a photograph of a different kind of place, and no sentence below compares two views of one street

**The item asked for a residential street and its reference is a sunken six-lane Interstate.** The fetch recorded its queries — *"Bayside Queens houses residential street"* and *"Bayside, Queens" house* — and kept Interstate 295 from the 42nd Avenue footbridge, a Flickr picture titled *"Needs Work"* and *Lawrence Cemetery*; none is a residential block. This is the sheet docs/DEVIATIONS.md **J71** was written from, and the row is open: the chooser ranks on lighting, distance band, timestamp and azimuth error, and has no test of what a photograph is a picture *of*. All three carry a GPS fix; the Interstate won because it alone carries a full date and time, where the cemetery photograph in the same distance band carries only a year and the Flickr house sits a band further out. Its fix is **566.6 m** from the recorded viewpoint, past the 250 m band, so the camera was correctly not stood on it (the J60 shape: the photograph is where its title says, the pairing is wrong).

**The two halves share nothing but the Sun.** The photograph looks south from a footbridge a storey above the Clearview Expressway: three lanes each way, a median carrying cobra-head lamps on a Y-pole, yellow edge lines and dashed white lane lines, tan retaining walls with railings, trees over the walls, a red saloon in the near lane, a dozen-odd vehicles receding to an EXIT 5 sign, a pale clear sky over the top third. The render stands at eye level on a broad grey apron beside a wide street running north: two- and three-storey red- and tan-brick taxpayers with green shopfront frames, a brick house with a stoop at the far left, a City flag on a pole mid-frame, a cobra-head lamp, three dark vehicles at the kerb and a fourth partly behind, four pedestrians -- two beside the middle vehicle, one on the far right-hand sidewalk in a white top, one small yellow figure far down the cross street at the left --, honey locust crowns at both upper corners, a deep blue sky. Street width, storey height, framing and material cannot be compared across that gap; the render's failure to resemble the photograph is not a fault of the model.

**Where the camera stands is its own small gap.** The item's viewpoint, *215th Street near 42nd Avenue, looking north*, is **0.1 m** from `t_15_7_struct_station_house`, so the camera was walked **32.2 m** onto the nearest sidewalk polygon. The view azimuth is clear for **60 m** and the nearest built thing in frame is `prop_tree_honeylocust_large_22` at **19.4 m** (**-27.2°** yaw, **+21.1°** pitch). The move is correct, and it leaves the frame on a shopfront strip rather than the residential block the item is named for. No subject is named, so `sightline.subject_visible` is null and no J74, J78 or J79 question arises. What can be judged is whether the render is a plausible Bayside commercial street on a June afternoon, and on that narrow question it holds.

## What matches

* **The instant is the photograph's own and the light agrees with it.** The Sun is placed from EXIF `DateTimeOriginal`, **2024-06-18 14:45:53**, azimuth **241.3°**, elevation **61.3°**, **921.7 W/m²** direct normal. Both halves show a high afternoon sun under a clear sky: the photograph's carriageways and walls are fully sunlit with only short shadows tucked under the vehicles; the render's cars and flagpole throw theirs right and toward the far kerb, where a Sun behind the left shoulder of a north-facing camera puts them. The crowd was drawn for **a weekday**, which the Tuesday is.
* **The street furniture is the right family.** The render's cobra-head davit is the fixture on the photograph's median and verges; **88** street lamps stand in range, **82** of them from `rule:lamp_30_40m_alt`, a spacing rule.
* **The trees are the census's, at the census height.** **2,620** trees in range, **2,579** from `street_trees_2015`; **2,614** carry a scale, mean **0.933**, **6** outside the declared band (J70).
* **It is recognisably outer-borough Queens.** Brick taxpayers with continuous shopfronts, kerbside parking, low parapets and rooftop plant: **325** storefronts among **2,445** kit pieces, **1,448** windows, **131** parapets, **117** entry doors, **105** cooling towers.
* **Nothing was cut for budget.** **4** of **4** tiles, 0 missing, 0 LOD-substituted, 0 holes, no kit cap; the **80** unplaced prop rows are curb ramps built into the pavement.
* **The traffic is the simulation's**: **73** vehicles and **265** people from seed **20260907**; the cars and walkers in frame are that density, not the photograph's.

## What does not match

* **The two halves are of different kinds of place** (**J71**), and the eye is at street level where the photograph's is on a footbridge: **1.6 m** over terrain at **23.606 m** (`ground_mode: street`).
* **The item says "residential block" and the frame is a shopfront strip**, where the 32.2 m walk landed.
* **The lower two-fifths of the render is a blank grey plane, and it is pavement, not road.** The record holds **7,333** white and **622** yellow marking polygons in range (J52 done), and the sliver of carriageway that is visible carries a few fragments of them: two yellow dashes at the far kerb, one left of the flagpole and one right of the middle vehicle, a crosswalk's white continental bars between the two nearest cars, and white lines on the cross street ahead.
* **The development is metered, not under-lit.** The frame needed **+1.21** stops to bring its median to middle grey (unclamped **+1.21**; the physical rule alone would give **+0.00**), well under the +4 at which the record calls a scene under-lit (J83). The photographer exposed brighter against the same convention: `exposure_offset_stops` **0.528** against the render's **0.242**, recorded as **-0.286**. The mean ratio **0.749** (**0.4221** against **0.5632**) and median ratio **0.913** (**0.4988** against **0.5465**) are first that choice; the p05 pair, **0.1145** against **0.113**, is not a gap.
* **The highlights differ because the subjects do**: p95 **0.6482** against **0.8745**; sky and sunlit wall against a pavement apron and one stucco face.
* **Chroma is about six-tenths of the photograph's**: **0.0646** against **0.1111**, ratio **0.581**. A red Civic, foliage and blue sky on one side; grey pavement, black cars and two brick tones on the other. `roof_membrane` and `wood_clapboard` sit at the albedo cap, neither in frame; each building class is one hue at different brightnesses (J66).
* **No cornice line worth the name**: **11** cornices, **11** string courses, **12** pilasters across **2,445** pieces; the parapets are flat bands.
* **1,174 of the 2,620 trees are species-substituted** and **15** impostor cards were dropped.
* **The flag is an asset, not a record.** One flagpole in range flies the municipal flag because that is the kit's flagpole (J58).
* **Every agent is at LOD2**; the pedestrian beside the middle vehicle is a low-detail body.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| an Interstate for a residential street, footbridge eye against street eye | the fetch kept nothing answering its houses query and the chooser has no test of subject; the overpass 566.6 m away is refused as a camera position | **reference — open, DEVIATIONS J71**, J60 |
| a commercial strip where the item says residential block | the recorded viewpoint is 0.1 m from `t_15_7_struct_station_house`; the camera was walked 32.2 m onto the nearest sidewalk polygon | verification |
| a blank pavement plane across the lower two-fifths | the walk put the camera on a wide sidewalk polygon and the level axis puts the road high in the frame; the markings are there and mostly out of it | verification |
| mean 0.749 and median 0.913 of the photograph's | metered development at +1.21 stops; the photographer's offset 0.528 against the render's 0.242 is exposure, not the city | — (not a gap), **DEVIATIONS J83** |
| p95 0.6482 against 0.8745 | sky and sunlit wall fill half the photograph; pavement and one stucco face are the render's brightest | reference |
| chroma 0.581 of the photograph's | red car, foliage and sky against grey pavement and dark cars; `shellmat` scales all channels by one factor, so a class varies in tone, never hue | reference + **data — DEVIATIONS J66** |
| no cornice line | 11 cornices across 2,445 pieces; the classifier has no source for a taxpayer's corbel course or pressed-metal cornice | geometry |
| 1,174 trees species-substituted, 15 impostor cards dropped | no modelled species matched; the nearest by size and taxon stands in | data |
| the flag is the kit's flag | one flagpole; the asset is chosen by rule because no source says what flies there | data, **DEVIATIONS J58** |
| every agent at LOD2 | the LOD selector keys off distance and nothing in frame is near enough for LOD0 | performance |
