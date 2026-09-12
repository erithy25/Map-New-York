# Top of the Rock looking south (Empire State Building centred)

`top_of_the_rock_south` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:View-from-Empire-State-Building.jpg by Sebring12Hrs, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2018-10-25 13:05:58, 1920x1440. [Commons page](https://commons.wikimedia.org/wiki/File:View-from-Empire-State-Building.jpg) — the photograph carries no camera GPS, so the view direction is the item's own standard viewpoint at **medium** confidence. Its filename says *view from the Empire State Building*, and the Empire State Building is the tower standing in the middle of it, so the title is wrong about its own subject; what the picture actually is is a south view from a Midtown deck, which is what this item wants. Midtown's roofs in the near field, the Empire State Building centred with its mast, One World Trade Center beyond it, the Bank of America Tower's crystalline crown at the right, and the harbour at the horizon under a clear October sky with one small cloud in it.

**Camera** — 40.7593, -73.9789 (NYC_TM -2440, 6586) at z 280.9 m NAVD88, eye **260.7 m above the terrain** | azimuth 205.2°, pitch 0.0° | 24 mm on 36 mm (73.7° horizontal) | 1208x906. The eye height carries a file reference for its own source: *"Top of the Rock outdoor deck, 70th floor of 30 Rockefeller Plaza: roof/deck level 259.1 m above the plaza (`blender_out/landmarks/catalog/30_rockefeller_plaza.json`, CTBUH 850 ft), plus 1.6 m eye height"* — the deck rule at its best (J65). The camera stands on the item's recorded viewpoint, whose azimuth agrees with the bearing to the subject to **0.2°**, and was **not moved**. The nearest built thing in the frame is `lm_30_rockefeller_plaza.24` **28.5 m** away — the deck's own parapet — and the view azimuth is clear for **150.0 m**. The lens is chosen for the view: *"observation-deck panorama: the reference frames span the whole Midtown-to-Lower-Manhattan skyline, which needs 74 deg horizontal"*. The ground 261 m below reads 20.229 m NAVD88 from 16 samples within 5.0 m.

**Sun** — azimuth 187.9°, elevation **36.7°** at 2018-10-25T13:05:58−04:00, from the photograph's own **EXIF DateTimeOriginal**; 821.2 W/m² direct normal, sky at strength 0.0342, Filmic, **−0.02 stops**. The linear frame's median is **0.1826** against the 0.18 middle-grey target, so the metered development is **−0.021 stops**: this scene arrived at a photographable level on its own and needed nothing. **Of the 169 metered frames in the pass, this is the smallest development of any of them.** The physical rule would have given 0.23.

**In the scene** — 4,489,948 triangles: **83 building tiles (1,574,780 tris), 0 missing, 28 substituted by a lower LOD**, 46 landmark models of which 16 fall inside the 73.7° cone, 36,256 pavement polygons, **0 props, 0 kit pieces, 0 vehicles and 0 people**, 34 park-ground meshes, **53 tiles of structures (415,308 tris) with 30 having no file**, and 19 named water bodies with 21,569 quads on the flattened surface.

## Verdict — the best-behaved frame in the pass on light and sightline, and it has no colour

**Three things on this sheet are the best of their kind.** The development is **−0.021 stops** on a linear median of **0.1826** against a 0.18 target — the smallest metered development of all 169 metered frames, which is to say that a Midtown skyline at 13:05 on a clear October afternoon arrives at exactly the level a photographer would expose for, with no lift and no clamp. The height probe cast 43 rays and **all 43 landed on built fabric**, measuring **431.0 m** on `lm_empire_state.3` against a catalogued **443.2 m** — the difference is the upper mast above the point the ray met. And the sightline reports **12 of 13 rays clear and 12 on the subject**, a visible fraction of **0.923**, with the single failure stopping at 833.3 m on a glass-curtain tile mesh. From this deck the Empire State Building is genuinely visible and the record says so with the right number.

**The massing is right and reads as Midtown.** 83 building tiles at 1,574,780 triangles with **none missing**, 46 landmark models, and the result is a skyline a reader recognises: the Empire State Building with its mast in the centre, 432 Park's white slab and its neighbours at the left, the Bank of America Tower's block at the right, and hundreds of setback roofs stepping away. This is the most complete tile coverage of any sheet read this round.

**And it has almost no colour.** Chroma **0.0641** against the photograph's **0.1992**, a ratio of **0.322** — the render carries under a third of the real view's saturation. Everything in the frame is a tile shell wearing its resolved material colour (J63), and above a certain distance those colours converge on the same cream and grey. The photograph's Midtown is red brick, black glass, green copper, white terracotta and a saturated October sky; the render's is a tonal study. The contrast follows: sd **0.793**, with the render's 95th percentile at 0.6686 against the photograph's 0.8312, because there is no glass in the render bright enough to flare and no shadow deep enough to read as one.

**Everything below the roofline is deliberately absent, and the record says so.** `props not placed: disabled`, `kit not placed: disabled`, and the agents field carries its own reason: *"the eye stands 261 m above the ground, where a person is a fraction of a pixel and a car a few, so the simulation's crowd and traffic are not drawn"*. That is the correct decision for an observation-deck frame and it is the clearest statement of a performance trade in any record read this round. It costs nothing visible: at 261 m nothing in the photograph's streets is legible either.

**Two gaps are real and both are about what is not there.** Thirty of the fifty-three structures tiles have no file, on a view that takes in the whole elevated and cut-and-cover network of Midtown and Lower Manhattan. And the park ground has **no samples closer than 400 m at all**, with 0.2575 of its 3,483 far-field samples under the terrain and a worst case of **−12.094 m** — the deepest single park-ground excursion read this round.

## What matches

* **The development is the smallest of all 169 metered frames**: −0.021 stops on a median of 0.1826 against a 0.18 target, so the frame is published as the scene arrived.
* **43 of 43 probe rays on built fabric**, and 431.0 m measured against a catalogued 443.2 m — the difference is the mast above the ray's landing.
* **12 of 13 sightline rays clear and 12 on the subject**, a fraction of 0.923.
* **The eye height cites its own source file.** 259.1 m of deck from the catalogue entry for 30 Rockefeller Plaza, with CTBUH's 850 ft named, plus a 1.6 m eye (J65).
* **The heading agrees with the bearing to the subject to 0.2°.**
* **The tile coverage is complete**: 83 of 83 building tiles present, **0 missing**, with 28 drawn at a lower LOD than their distance asks — which at this range is the streaming rule working as designed.
* **The median tone agrees to a sixtieth**: p50 1.016×, with an exposure-offset gap of **0.049 stops**.
* **The lens was chosen for the view**, at 24 mm and 73.7°, because a deck panorama needs the whole Midtown-to-Lower-Manhattan span.
* **The absent props, kit and agents are declared with their reason**, and at 261 m of height the decision costs nothing a reader can see.
* **Structures are here in force**: 53 tiles imported for **415,308 triangles**.
* **The water is comprehensive**: 19 named bodies from the Hudson to Turtle Pond, with 21,569 quads on the flattened surface.
* **The pavement is drawn even though nothing stands on it**: 36,256 polygons with **19,989 white markings**, 5,638 sidewalk, 4,287 roadbed, 3,758 curb, 1,423 plaza and 812 crosswalk, and **0 dropped**.

## What does not match

* **The render carries under a third of the photograph's colour**: chroma 0.322×. Above a certain distance every tile shell's resolved material converges on cream and grey, and Midtown's brick, copper, black glass and terracotta go with it.
* **The contrast is four fifths of the photograph's**, sd 0.793×, with the 95th percentile at 0.6686 against 0.8312 — no glass flares and no shadow reads as deep.
* **No cloud.** The photograph's one small cloud sits beside the Empire State Building's mast and is the only thing in its sky; the render's sky is a Nishita gradient at strength 0.0342 that hazes toward the horizon in a way the real air on that day did not.
* **The harbour is not legible at the horizon.** The photograph's far distance carries Upper New York Bay, Staten Island and the Verrazzano; the render's resolves into the same haze as the sky.
* **Thirty of the fifty-three structures tiles have no file**, on a view that contains most of the Midtown and Lower Manhattan rail network.
* **The park ground has no samples inside 400 m** — the mid and near bands are both empty — and 0.2575 of the 3,483 far samples sit under the terrain, worst case **−12.094 m**, the deepest excursion read this round.
* **The reference's own filename is wrong about its subject.** It is titled as a view *from* the Empire State Building and the Empire State Building is in the middle of it. The pairing works because the picture is what the item wants, but a reader should know the title does not describe it (J71's family).
* **The reference has no camera GPS**, so its viewpoint is the item's standard position at **medium** confidence rather than a derived one.
* **No props, no kit, no crowd and no traffic** — correct at this height, and still a statement that this sheet tests massing and light only.

## Measured for this assessment

| figure | where it comes from |
|---|---|
| the smallest metered development of all 169 metered frames | ranked over every record whose `lighting.development.metered` is true, on the absolute value of `stops`; this sheet's -0.021 is the smallest, ahead of the Verrazzano-Narrows Bridge at +0.044 and the Coney Island Cyclone at +0.076 |
| the most complete building-tile coverage and the deepest park-ground excursion read this round | this sheet's 83 of 83 tiles with 0 missing, and its park-ground minimum clearance of -12.094 m, against the forty-three sheets read in the preceding rounds |
| the 443.2 m catalogue figure is the Empire State Building's antenna tip and 431.0 m is the mast below it | the recorded `nearest_catalogue_origin.height_m` of 443.2 against the recorded probe height, the building's published antenna height and its 381 m roof |
| the photograph's own title names the wrong building | the reference filename `View-from-Empire-State-Building.jpg` against the content of the frame, in which the Empire State Building stands at the centre |

## Cause of each gap

| gap | cause | class |
|---|---|---|
| chroma 0.322 and contrast 0.793 | every surface beyond the near field is a tile shell wearing one resolved material colour, and per-building facade colour has no source (J63, J66). At this distance the colours converge | **data — declared, no source** |
| no cloud, and the horizon hazes | nothing in this build reads a historical sky, and the procedural dome's own horizon gradient replaces real October clarity | **reference — no source exists** |
| the harbour is not legible | the same haze, plus the far terrain and water resolving at 40.0 m spacing | performance + reference |
| 30 of 53 structures tiles have no file | those tiles were not built (B13 remainder), on the view that contains the most of them | **data — open** |
| park ground 0.2575 under the terrain, worst -12.094 m, and no samples inside 400 m | the park surfaces were draped on the fine grid and this scene's terrain coarsens to 40.0 m over a 4.5 km radius; nothing park-like stands within 400 m of a rooftop 261 m up (J40, J96) | verification — declared |
| the reference's title names the wrong building | the reference chooser tests licence, resolution, date and whether a view direction can be derived, and nothing tests what a photograph is a picture of (J71). Here the pairing survives it | reference — declared |
| no props, kit, crowd or traffic | disabled on purpose at this eye height, with the reason recorded in the agents field | **declared decision — and the right one** |
| 28 tiles drawn at a lower LOD | the streaming rule working as designed at a 4.5 km radius | performance — declared |
