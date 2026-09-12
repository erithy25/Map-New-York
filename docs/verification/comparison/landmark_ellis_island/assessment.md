# Ellis Island Main Building

`landmark_ellis_island` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Ellis Island Immigrant Hospital - Tour.jpg by Z22, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2018-01-01 10:51:29, 1920x1440. [Commons page](https://commons.wikimedia.org/wiki/File:Ellis_Island_Immigrant_Hospital_-_Tour.jpg) — the photograph's own view direction is derived from the image at **high** confidence.

**Camera** — 40.70166, -74.04024 (NYC_TM -7626, 188) at z 1.6 m NAVD88 | azimuth 170.0°, pitch +4.1° | 35 mm on 36 mm (54.4° horizontal) | 1208x906. The camera stands on **the item's recorded viewpoint**: this photograph's own EXIF GPS is **369.5 m** away, past the 250 m at which it could still be the same view. The recorded azimuth of 170.0° agrees with the bearing to the subject to **0.0°**. The lens stayed at 35 mm and the axis was tilted **+4.1°** to the subject's mid-height, 33 m above its ground. The camera was not moved — **nothing built stands within 60 m of the lens**, no agent either, and the azimuth is clear for **94.4 m** against the 80.0 m needed. **Ground under the camera reads −0.0 m NAVD88, from 16 heightmap samples within 5.0 m whose range is −0.0 to −0.0 m** — the flattened water surface, because the item's recorded viewpoint is *the ferry basin north of the Main Building*, which is water.

**Sun** — azimuth 162.7°, elevation 24.4° at 2018-01-01T10:51:29−05:00, from the photograph's own **EXIF DateTimeOriginal**; 712.5 W/m² direct normal, sky at strength 0.0383, Filmic, **−0.40 stops**. This is the **second negative development in the pass**: the linear frame's median is **0.236927** against a middle-grey target of 0.18, so the scene arrived brighter than a photographable level and was pulled down rather than lifted. The physical rule would have given **+0.82 stops** (J83). A frame that is two thirds open water on a low winter sun is exactly the case where that happens.

**In the scene** — 187,502 triangles, the second-smallest scene in the pass: 4 building tiles (4,012 tris) with **2 missing**, 2 landmark models, both in the frame, 903 pavement polygons with **0 dropped**, 416 props, **3** kit pieces, **0 park-ground meshes**, 4 structures tiles with **2 missing** (3,080 tris), **0 vehicles and 0 people**, terrain 91,592 tris at 2.0 m near / 40.0 m far with no holes.

## Verdict — the reference is the Immigrant Hospital, the subject is the Main Building, and the Main Building renders as a salmon-coloured box whose four copper towers survive only as green tips

**The reference is the wrong building on the right island.** `File:Ellis Island Immigrant Hospital - Tour.jpg` is a tour group in hard hats standing in front of the abandoned hospital's brick flank — a different complex on the south side of the island from the Main Immigration Building the item names. This is the sharpest instance of **J93** in the pass so far: not a detail, not an interior, not an event, but a neighbouring building with the same place name in its title.

**The Main Building is a box.** The render shows a long pale salmon mass with a flat parapet and a slight setback, and at its right end **two small green points** where the copper cupolas of the eastern towers should stand. The real building's four corner towers with their copper domes and finials, its triple arched entrance, its limestone quoins and window surrounds and its red brick are all absent. The mass is roughly the right footprint — the probe measures **32.97 m** above a ground of 2.81 m over **43 of 43** rays, plan extent **66.6 m by 46.9 m** — against a catalogue entry 27.2 m away carrying **45.3 m**, which is tower height, so this sheet is also in the J94 survey.

**The camera is standing in the harbour.** The item's viewpoint is the ferry basin, so the eye point sits 1.6 m over water at −0.0 m NAVD88 and the lower half of the frame is a flat mirror. That is faithful to the item's own record and it is also why two thirds of the picture carries no information: a mirror of a box.

**The island has three kit pieces.** 3 of 3 in range, nothing capped: two windows and one quoin for the whole of Ellis Island. **Two of the four building tiles have no shell file at all**, and park ground was not built for six tiles, so the island's own lawns and paths are bare terrain.

**The exposure comparison runs the other way from most of this pass.** Mean **1.394×**, median **1.638×** — the render is brighter — but the photograph sits **1.248 stops below** the grey convention against the render's +0.249, a **1.497-stop** difference, and that accounts for nearly all of it (J83). Chroma at **0.812×** is one of the closest in the pass, because a salmon box over grey water and a brick wall under bare trees happen to carry similar saturation.

## What matches

* **The development is metered and negative**, −0.40 stops, and the record reports the minus sign rather than clamping at zero — the correct answer for a winter frame that is mostly lit water (J83).
* **Chroma is 0.812 of the photograph's**, and the two development offsets are 1.497 stops apart, which explains the mean and median ratios without appealing to the scene.
* **The height probe is complete and the extent is the real footprint**: 43 of 43 rays, 32.97 m, 66.6 m by 46.9 m (J74).
* **Both landmark models in range are in the frame**, and the subject is **4.7° off axis** at 230.7 m.
* **The record is honest about an empty simulation**: *the simulation frame is empty here* — correct for an island with no road network.
* **The record names every missing file**: 2 building tiles without a shell, 2 structures tiles without a file, and 6 tiles without park ground, each listed by name.
* **Props were not capped**: 416 placed of 416 in range, and **0** unmapped kinds — the only sheet in this queue with nothing unmapped.
* **The bare canopy is right for 1 January**, and 22 of the 414 cards are procedural canopy stems.

## What does not match

* **The reference is the Immigrant Hospital, not the Main Building** (J93).
* **The Main Building's four towers, domes, arched entrance and limestone trim are absent**, leaving a salmon box with two green tips.
* **The brick is one flat colour.** The real building is red brick with limestone banding; the render carries a single salmon tone (J66 remainder).
* **Two of 4 building tiles have no shell file**, and **2 of 4 structures tiles have none either**, so the island's other buildings — the hospital in the reference among them — are simply not there.
* **Three kit pieces on the whole island**: 2 windows and 1 quoin.
* **No park ground at all** — 0 meshes — with 6 tiles named as unbuilt.
* **The sightline is weak and correctly reported**: 13 rays, **3 clear, 3 on the subject**, all three landing on the subject's own fabric nearer than the recorded coordinate, blocked at **94.4 m** by `t_-8_0_struct_seawall`. Visible fraction **0.231**.
* **The probe's 32.97 m against a 45.3 m catalogue entry 27.2 m away** puts this sheet in the J94 survey: the towers are what the entry measures and the box is what the probe found.
* **Contrast is 0.494 of the photograph's** — the render has a mirror where the reference has bare branches, snow, shadow and five people in dark coats.
* **Not one of 414 trees is drawn from modelled branches**, and **392 of them** had their species substituted.
* **The water is a flat mirror** on a tidal harbour.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the reference is the Immigrant Hospital | the chooser matched "Ellis Island" in the title and cannot tell one building on an island from another (J93) | **verification — open, J93** |
| no towers, domes, arched entrance or limestone trim | the landmark builder models massing; corner towers with domes and finials are not a shape it authors, and there is no per-building trim | geometry — declared scope + **data, open** |
| one flat salmon tone | no per-building facade colour (J66 remainder) | **data — open** |
| 2 of 4 building tiles and 2 of 4 structures tiles without a file | no shell or structures file was built for those tiles; the record names all four | **data — open, measured** |
| 3 kit pieces on the island | the facade classifier found 3 records in range, because the tiles that would carry the rest have no shell file | consequence of the row above |
| no park ground, 6 tiles unbuilt | park ground was not built for those tiles; the record names all six | **data — open, six tiles unbuilt** |
| visible fraction 0.231, blocked at 94.4 m on a seawall | the subject is 249.7 m away across open water and the island's own seawall stands in the fan; the reading is correct | verification — correct as measured |
| probe 32.97 m against a 45.3 m entry | the probe took the object at the coordinate, which is the main block rather than a tower (J94) | verification — open, J94 |
| sd 0.494×, p05 0.3175 against 0.0524 | a mirror and a box against bare branches, snow and dark coats | consequence of the reference and the viewpoint |
| the camera stands on water at −0.0 m | the item's own recorded viewpoint is the ferry basin, which is water; the record states the elevation and its sample range | **data — declared, and faithful to the item** |
| 0 of 414 trees from modelled branches, 392 species substituted | the props budget spends its triangles on cards at this density, and the tree catalogue does not hold most species surveyed here | performance + **data** |
| the water is a flat mirror | water is a flattened surface at a single elevation with no wave or depth model | **declared scope** |
