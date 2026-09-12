# Brooklyn Museum

`landmark_brooklyn_museum` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:NYC Architectural Artifacts from the Brooklyn Museum.jpg by Kidfly182, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2021-08-05 15:07:32, 1920x1440. [Commons page](https://commons.wikimedia.org/wiki/File:NYC_Architectural_Artifacts_from_the_Brooklyn_Museum.jpg) — the photograph's own view direction is derived from the image at **high** confidence.

**Camera** — 40.67207, -73.96419 (NYC_TM -1200, -3102) at z 51.2 m NAVD88 | azimuth 156.1°, pitch +5.2° | 35 mm on 36 mm (54.4° horizontal) | 1208x906. Position and heading both come from the photograph: its own EXIF camera GPS, **140.5 m** from the item's recorded viewpoint, and 156.1° is the bearing from there to the subject. The item's recorded azimuth of 80.0° is **76.1° away**. The lens stayed at 35 mm and the axis was tilted **+5.2°** to the subject's mid-height, 22 m above its ground. The camera was not moved — the viewpoint is in open air, **nothing built stands within 60 m of the lens**, the azimuth is clear for **83.0 m** against the 46.3 m needed, and the nearest simulated agent is a black car **9.3 m** away at 27.2°. Ground under the camera reads **49.586 m** NAVD88, the 10th percentile of **113** heightmap samples within 12 m, range 49.42 to 50.24 m.

**Sun** — azimuth 237.8°, elevation 53.9° at 2021-08-05T15:07:32−04:00, from the photograph's own **EXIF DateTimeOriginal**; 901.4 W/m² direct normal, sky at strength 0.0316, Filmic, **+1.19 stops and not clamped**. The linear frame's median is **0.079151** against a middle-grey target of 0.18; the physical rule would have given **0.0 stops** (J83).

**In the scene** — 4,500,171 triangles: 4 building tiles (360,902 tris, none missing, none LOD-substituted), 3 landmark models of which 1 falls inside the 54.4° frame, 19,348 pavement polygons with **0 dropped**, 5,072 props, 5,033 kit pieces, 16 park-ground meshes over 321 surfaces, 2 structures tiles (1,672 tris), 70 vehicles and 402 people, terrain 86,512 tris at 2.0 m near / 40.0 m far with no holes.

## Verdict — a good exterior render of the museum paired with a photograph of five carved heads on a blue mosaic wall, which is the third sheet in this queue whose reference is not of its subject

**The reference is a set of objects from the collection.** Five architectural fragments — carved stone masks and a lion's head — mounted in gold-lined panels on a blue mosaic ground, photographed indoors from about two metres. The Commons title says it exactly: *Architectural Artifacts **from** the Brooklyn Museum*. The chooser read the museum's name and took the file; it has no evidence of whether a photograph shows a building or something that building contains (**J93**).

**The render is a reasonable Beaux-Arts front.** The colonnade stands on the right with its entablature and pediment, the long facade runs back to the left with four storeys of window openings, and the copper dome behind reads green at the correct hue. The camera is where the photographer stood, the sightline is **13 of 13 rays clear with 11 on the subject** — visible fraction **0.846** — and the height probe is **43 of 43** rays giving **22.01 m** above a ground of 48.81 m, against a catalogue entry 48.7 m away carrying 50.0 m for the whole composite. The plan extent measured off the object is **158.1 m by 115.9 m**, which is the museum's actual footprint.

**What the render does not have is the front of the building as it now stands.** The viewpoint note names *the glass entrance and Beaux-Arts front*. The glass entrance pavilion and its stepped plaza and fountains — the 2004 front — are not in the model; the render meets the ground with a plain plinth. Nor is there any of the facade's sculpture: the pediment figures, the allegorical statues along the attic and the inscribed frieze are all absent, and those are the things the reference photograph is a fragment of.

**The tonal figures are ordinary and readable.** Median **1.125×**, mean **0.868×**, contrast **0.701×**, chroma **0.496×**, with the two development offsets **0.365 stops** apart (J83). The colour gap is a blue mosaic and gilding against grey limestone; the contrast gap is that the render's facade is evenly lit where the photograph has a dark interior ceiling in it.

## What matches

* **The sightline is strong and honest**: 13 of 13 rays clear, 11 on the subject, 1 into nothing, clear fraction **1.0**.
* **The height probe is complete and the extent is the real footprint**: 43 of 43 rays, 22.01 m, 158.1 m by 115.9 m (J74).
* **The colonnade, the entablature and the pediment are modelled** and read at 92.7 m, and the copper dome is the right colour.
* **The development is metered and unclamped**, +1.19 stops from a median linear luminance of 0.079151.
* **The camera needed no intervention**: open air, nothing built within 60 m, azimuth clear for 83 m.
* **The woodland canopy rule carries the greenery**: **2,503** of the 4,407 impostor cards are procedural canopy stems, and 48 more trees are drawn from modelled branches.
* **Near-field ground is perfect**: within 150 m, **0.0** of 260 park-surface samples sit under the terrain, median **+0.19 m**.
* **The pavement is complete**: 19,348 polygons, **0 dropped**, including 5,654 white markings, 3,983 roadbed, 2,571 sidewalk, 2,481 curb, 2,172 parking lot and 753 plaza — and Eastern Parkway's double yellow centre line is drawn correctly in the foreground.
* **Props were not capped**: 5,072 placed of 5,231 in range.
* **The crowd is close to the ask for once**: the table wanted 987 people and **1,253** were simulated, of which 402 are drawn — the best ratio in this queue.

## What does not match

* **The reference is five objects from the collection**, photographed indoors. No render of the building can match it.
* **The glass entrance pavilion and its plaza are not modelled**, and the viewpoint note names them as the subject.
* **No facade sculpture at all**: no pediment figures, no attic statues, no inscribed frieze. The reference is a photograph of exactly this class of thing, one storey down.
* **Chroma is 0.496 of the photograph's**, 0.0695 against 0.1401.
* **Contrast is 0.701 of the photograph's** and the render's fifth percentile is **0.1048** against **0.2091** — the two frames are dark and light in opposite places.
* **5,033 of 21,998 kit records were drawn**, capped at a 1,369,129-triangle budget, with a further 1,140 suppressed under the landmark shell — so the blocks along Eastern Parkway carry a quarter of their window openings.
* **Only 48 of 4,455 trees are drawn from modelled branches**; **1,382** species were substituted, **12** instances scaled out of band and 12 cards dropped.
* **Both structures tiles in range have no structures file**, and the 2 that are imported contribute **1,672 triangles** in total, over the Eastern Parkway IRT line and the museum's own subway entrance.
* **Beyond 400 m the park surface sits under the terrain on 0.3639 of 1,003 samples**, minimum **−3.389 m**, after a redrape that moved **241,684** vertices — the worst far-band figure in this queue, and that band is Prospect Park and the Botanic Garden (J85).
* **Thirteen props across seven kinds were wanted in range and have no asset**: 3 memorial, 2 drinking fountain, 2 misc structure, 2 parks building, 2 parks comfort station, 1 artwork, 1 payphone.
* **Seven park-ground surface kinds fall back to the builder's flat colour** — infield dirt, sport court, greenstreet grass, park grass, pool water, recreation grass, bare ground (J40).
* **A simulated car stands 9.3 m from the lens**, outside the 8 m rule but close, and the rule still does not apply to the crowd (J91).

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the reference is objects from the collection | the chooser matches the institution's name in a title and cannot tell a building from its contents (J93) | **verification — open, J93** |
| no glass entrance pavilion or plaza | the landmark model carries the Beaux-Arts massing and not the 2004 front; the item's own viewpoint note names a feature the model does not have | **geometry — open, measured against the item's own note** |
| no facade sculpture | sculpture is not a class this build authors | geometry — declared scope |
| chroma 0.496×, sd 0.701×, p05 0.1048 against 0.2091 | grey limestone against blue mosaic and gilding, and an evenly lit facade against a dark interior | consequence of the reference |
| 5,033 kit pieces of 21,998 in range | the kit triangle budget at 1,369,129, plus 1,140 suppressed under the landmark shell | performance + declared rule |
| 48 of 4,455 trees from modelled branches, 1,382 species substituted | the props budget spends its triangles on cards at this density, and the tree catalogue does not hold most species surveyed here | performance + **data** |
| 2 of 2 structures tiles without a file, 1,672 triangles from the rest | no structures file was built for either tile in range, over the Eastern Parkway IRT | **data — open, two tiles unbuilt** |
| 0.3639 of far park ground under the terrain, min −3.389 m | the terrain grid coarsens to 40 m beyond the near band across Prospect Park and the Botanic Garden (J85) | geometry — open, measured |
| 13 props across seven kinds unmapped | no asset exists for those kinds | data |
| seven park surface kinds flat-coloured | the texture catalogue has no photographic set for any of them (J40) | **declared decision** |
| a car 9.3 m from the lens | the 8 m nothing-built rule applies to geometry and not to the crowd (J91) | verification — open |
