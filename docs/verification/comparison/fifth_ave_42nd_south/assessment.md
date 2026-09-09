# Fifth Avenue at 42nd Street (NYPL), street view looking south

`fifth_ave_42nd_south` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:01-21-2017 - Women's March on NYC looking up 5th Ave (10796).jpg by Rhododendrites, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2017-01-21 13:41:25, 1920x1440. [Commons page](https://commons.wikimedia.org/wiki/File:01-21-2017_-_Women%27s_March_on_NYC_looking_up_5th_Ave_(10796).jpg)

**Camera** — 40.753505, -73.980874 (NYC_TM -2607, 5942) at z 23.4 m NAVD88 | azimuth 209.0°, pitch +0.0° | 35 mm on 36 mm (54.4° horizontal) | 1208x906.

**Sun** — azimuth 204.6°, elevation 25.7° at 2017-01-21T13:41:25-05:00 (EXIF DateTimeOriginal); 727.4 W/m² direct normal, sky at strength 0.0376, Filmic, +2.65 stops.

**In the scene**, within 740.1 m of the camera and not all of it in frame — 6 building tiles (300,026 tris), 9 landmark models of which **2 can fall inside the 54.4° frame**, 28,814 pavement polygons (14,594 white, 5,267 sidewalk, 4,173 roadbed, 3,464 curb, 717 crosswalk, 269 median, 231 plaza, 88 yellow, 11 parking lot), 2472 props of the 2,574 in range, 4,629 kit pieces, 53 vehicles and 258 people; 4,500,133 triangles. Ground mesh 88,186 triangles, 0 holes. 20 city surfaces are dressed from the shared photographic catalogue.

## Verdict — the same crossing, photographed in the opposite direction, on a day the avenue was closed

**The two halves stand in the same place and look opposite ways.** The camera is the photograph's own EXIF GPS, **40.1 m** from the item's recorded viewpoint, and the road network puts that point in the carriageway of Fifth Avenue at its crossing with 42nd Street. The render looks down the avenue at **209.0°**, south-south-west, with the New York Public Library's model on the right (**122.0 m** away, **43.3°** off axis, half-width **32.5°**). The photograph's own Commons description says *"Looking up 5th Ave. from its intersection with 42nd St."* — up the avenue, towards the march's destination — and the picture agrees: no library terrace on either side, a right-hand wall of ornate pre-war commercial fronts with flags and twin-globe lamp posts, and an avenue closing on a light stepped-crown tower and a dark glass slab that are not the skyline the render faces. The record warns of this in its own words: the azimuth is *"the street heading of the reference view, not derived from the photo"*, at confidence **medium**. It is the residual fault I12 records — the chooser establishes no view direction, so *"a photograph looking the wrong way along the right street still passes"* — and I7 is its root: a street-axis item carries the item's azimuth, not the photographer's.

**What can be compared is the avenue as a type of street, and it compares well; what cannot be compared is the composition.** Both halves show a five-lane Manhattan avenue between continuous walls, mid-century slabs beside pre-war masonry, bare January trees, taxis and pedestrians at a marked crossing. Storey heights and the canyon's proportion agree; the individual buildings do not correspond and must not be matched.

**The photograph is the Women's March, and the simulation has no notion of it.** Fifth Avenue on 21 January 2017 is filled kerb to kerb with people and placards; the render carries an ordinary Saturday afternoon — **53 vehicles** and **258 people**, drawn for the Saturday that date is. The record shows the simulation generated the photograph's condition and removed it by rule: **168** pedestrians were dropped as *"pedestrian_in_the_carriageway_not_crossing"*, which is what a march is. The open roadway must not be read as the model being empty.

**The light is the photograph's own instant on a sky the photograph does not have.** The Sun is set from EXIF to the second, at **204.6°** and **25.7°** — almost straight down the render's **209.0°** axis and just above the top edge of a level 35 mm frame, which is why the render's sky burns white and its cars throw short shadows towards the lens. The photograph was taken under an overcast: flat light, no cast shadow anywhere. The development is metered (J83) at **+2.65** stops against a physical rule of **+0.75**, well below the under-lit threshold; no luminance ratio here is a fault of the city.

## What matches

* **The camera is on the avenue, in open air, unmoved**: eye height **1.6 m** on the roadbed, the view azimuth clear for **150 m**, the nearest built thing `prop_lamp_cobra_davit_2` at **8.3 m** and the nearest agent `agent_ped_1105.9` at **12.1 m** — nothing fills the frame.
* **The library is where the library is.** Its model — limestone, arched openings, a raised terrace with bare trees — occupies the right edge of the render, on the west side of Fifth south of 42nd, where the record's cone puts it.
* **The canyon is the right kind of canyon**: a wide two-way avenue between walls of the same order of height as the photograph's, glass slabs beside masonry, with a continental crossing and a dashed lane line drawn from **717** crosswalk and **14,594** white-marking polygons in range.
* **The trees are bare and the date is why**: **1,573** trees within range, leaf-off for 21 January at a mean scale of **0.927**; the photograph's own street trees, above the placards on the left, are bare in the same way.
* **The traffic is a Fifth Avenue fleet**: **22** yellow taxis, **13** boro taxis, **9** black cars, **5** sedans, **2** vans, an SUV and a DSNY truck; a green boro taxi, a yellow taxi, a grey SUV and a black SUV are in the frame, and the left-hand fascia carries a lettered bank name from **88** storefront pieces.

## What does not match

* **The photograph faces north and the render faces south-south-west.** The same intersection in opposite directions; no building in one half is a building in the other. The record's azimuth is the item's, not the photograph's, at confidence **medium** (I7; I12 remainder).
* **A demonstration in one half, a carriageway in the other.** The photograph's lower two thirds are heads, hats and placards; the render's are asphalt, a crossing and five figures; **168** simulated pedestrians in the carriageway were removed by rule.
* **Clear sky against overcast.** The render is lit by **727.4 W/m²** of direct Sun with the disc just out of frame; the photograph has no shadow at all. The render's sky is blown out — p95 **0.9086** against **0.8681** — and the facade tops facing the lens are veiled by it.
* **Exposure and colour.** Mean **0.4701** against **0.434** (**1.083×**), median **0.4993** against **0.416** (**1.2×**): the render's offset is **0.245** stops, the photographer's **-0.318** — about half a stop apart, the way a crowd of dark coats pushes a meter. Chroma **0.0613** against **0.086** (**0.713×**): the photograph's colour is pink hats, painted placards and flags, none of which the render has, with J66's one family per facade class as the remainder on the walls. The 5th-percentile gap (**0.1047** against **0.0566**) sits at the photographs' JPEG floor and is not evidence.
* **The lamp posts are the wrong fixture.** The photograph's kerbs carry Fifth Avenue's ornate twin-globe posts; the render's nearest obstruction is a cobra-head davit.
* **The facades are extrusions with openings.** **4,468** of **4,629** kit pieces are windows; **5** cornices, **8** pilasters, **5** string courses and **1** quoin serve the whole scene, so pre-war fronts read as flat walls with a window grid.
* **A figure mid-carriageway in a bent, unnatural pose** stands in front of the grey SUV at the crossing.
* **806** of the **1,573** trees are species-substituted; 7 artworks, 6 memorials and 9 vending machines among the props have no asset; the kit was capped at triangle budget **972,559**.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the halves face opposite ways along the same avenue | the item names no subject, so the camera takes the item's heading (**209.0°**) and the chooser never tests a photograph's direction | reference — **DEVIATIONS I7, I12 remainder** |
| a march in the photograph, an open carriageway in the render | no source of scheduled events or street closures exists in the build; the crowd model draws a day type's pedestrians and the carriageway rule removed the **168** that stood where the march stands | data |
| clear-sky Sun against an overcast photograph | the Sun is the EXIF instant; the record carries no sky-state term and the reference metadata no weather | data |
| mean 1.083×, median 1.2×, offsets 0.245 against -0.318 | metered development at middle grey (**DEVIATIONS J83**) against a photographer's exposure of a crowd of dark coats; a convention difference | — (not a gap) |
| chroma 0.713× | placards, hats and flags absent from the scene; on the walls, one material family per facade class (**DEVIATIONS J66**) | reference + material |
| p95 0.9086 against 0.8681, blown sky | the Sun sits just above the top of a level frame aimed within a few degrees of it | stated choice (level axis, item azimuth) |
| cobra-head davit where the avenue has twin-globe posts | the placed fixture is the mapped lamp's asset; the Fifth Avenue ornamental post is not among them | geometry |
| flat window-grid facades | shells are extruded from footprints; the kit's mouldings are generic profiles placed sparsely | geometry |
| a figure in an unnatural bent pose at the crossing | animation blend on an LOD body; placement correct, pose not | verification |
| 806 trees species-substituted, props unmapped, kit capped | nearest species by size and taxon; unmapped prop kinds stay unplaced rather than become the wrong object; triangle budget 972,559 | data / performance |
