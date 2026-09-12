# One57 (Billionaires' Row)

`landmark_one57` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:One57 2025 015.jpg by Kidfly182, CC BY 4.0 (https://creativecommons.org/licenses/by/4.0), taken 2025-11-03 12:32:14, 1920x3412. [Commons page](https://commons.wikimedia.org/wiki/File:One57_2025_015.jpg) — the photograph's own view direction is derived from the image at **medium** confidence, the lowest confidence on any sheet written so far, and the sheet bears that out. The photograph is taken from the **pavement at the tower's own base**, looking straight up its glass curtain wall, which fills all 1920x3412 pixels.

**Camera** — 40.7639, -73.9776 (NYC_TM -2298, 7120) at z 18.9 m NAVD88 | azimuth 324.6°, pitch +14.8° | 18 mm on 36 mm (58.7° horizontal, 90.0° vertical, portrait) | 784x1394. The camera stands on **the item's recorded viewpoint**, the south-east corner of West 57th Street and Sixth Avenue, because **this photograph carries no camera GPS** at all. The recorded azimuth of 324.6° agrees with the bearing to the subject to **0.1°**. The walk then **moved the camera 40 m to the right**: the recorded viewpoint is boxed in, closed off **10 m ahead** against the **80.0 m** this frame needs, and 40 m right was the nearest point in open air. From there the view is clear for **87.0 m** and the nearest built thing in the frame is `prop_lamp_cobra_davit_25` **15.5 m** away. The ground under it reads 17.25 m NAVD88, the 10th percentile of 113 samples within 12 m, range 17.16 to 17.79 m.

**Sun** — azimuth 195.1°, elevation 32.6° at 2025-11-03T12:32:14−05:00, from the photograph's own **EXIF DateTimeOriginal**; 792 W/m² direct normal, Filmic, **+4.70 stops** metered and unclamped against a linear median of **0.006937** and a target of **0.18**. The record declares the consequence in its own words: **under-lit** — *the scene needed +4.70 stops to read as a picture, more than the 4 a photographer recovers hand-held; the frame is published and this is the number to read it by*. A 32.6° November Sun almost due south, into a street canyon aligned north-west, puts the whole frame in its own shade.

**In the scene** — 4,500,019 triangles: 6 building tiles (279,446 tris, 0 missing, 0 LOD-substituted), 12 landmark models of which 3 can fall inside the 58.7° frame, 30,447 pavement polygons, 2,675 props, 6,938 kit pieces, 22 park-ground meshes, 21,504 triangles of structures, 50 vehicles and 233 people.

## Verdict — the height is the best thing on this sheet and the two frames are taken 222 m apart

**J74 saved this sheet from being framed for Carnegie Hall.** The probe found fabric on **43 of 43 rays** and measured **301.0 m** above a ground of 23.05 m, topping out at z **324.05 m**, on `lm_c_billionaires_row.49` — a member of the composite, **76.6 m by 73.7 m** in plan, not a tile mesh. The nearest catalogue origin is **`c_carnegie_hall`, 88.3 m away, height 55.2 m**, and the record marks it `within_120_m: true`. Under the rule J74 replaced, that entry would have supplied the subject's height, and this 301 m tower would have been lensed, pitched and ray-fanned as a 55 m concert hall. The composite `c_billionaires_row` has no origin near its own members, so the nearest catalogue row here is a different landmark on a different block.

**The same composite then hides the subject from the frustum.** The in-cone list names Carnegie Hall at 248.8 m, the Columbus Circle monument and Deutsche Bank Center at 593.4 m, and Hearst Tower at 607.9 m. **One57 is not in it** — the subject the sheet is about, 218.2 m away and on the view axis to a tenth of a degree, does not appear in the frustum's own account of what is in the picture, because the test uses the catalogue footprint's centroid and the composite's centroid is somewhere else (J88).

**And the two halves are pictures of different distances.** The reference is a photograph of a curtain wall taken from beneath it; the render is a view down a Midtown block with the tower 222 m off. One57 is in the render — the pale glass shaft behind the near buildings, upper left of centre — and it is a small part of the frame. The sightline says so honestly: **3 of 13 rays clear**, **1 on the subject**, a visible fraction of **0.077**, blocked at **17.4 m** by a street lamp. The walk's own score at its chosen point was the same 0.077, so nothing drifted between the decision and the render; this is simply the best view of One57 available from a surveyed viewpoint on that corner. What the sheet cannot do is compare a facade, and the confidence flag reading **medium** is the record saying so before anyone looks.

**The colour ratio runs backwards here and the reason is instructive.** Chroma **0.09 against the photograph's 0.0468, a ratio of 1.923** — the render carries nearly twice the colour. That is not the render being garish: a glass curtain wall in November haze is almost achromatic, and the render's frame is brick, tan stone, a yellow taxi and a white van. Two frames of different subjects will differ in colour before they differ in fidelity.

## What matches

* **The height, measured off the geometry** — 301.0 m on 43 of 43 rays, against a nearest catalogue row of 55.2 m that the current rule correctly refused (J74).
* **The aim** — the recorded azimuth agrees with the measured bearing to the subject to **0.1°**, from a viewpoint the photograph itself could not supply.
* **The record is honest about the frame it got.** The visible fraction is published as 0.077, the development as under-lit at +4.70 stops, and the reference confidence as medium.
* **Nothing was capped in the props** — **2,675 placed of 2,736 in range**, **0 dropped for budget** — and the count is dominated by **2,077 trees**, which is the south edge of Central Park doing what it should.
* **The park drives are car-free** — **5 vehicles dropped** because the road graph put them on Central Park's East, West, Terrace or Center Drive (J95).
* **2,814 faces were cut** out of the park ground for the landmark's own ground plate.
* **The crowd includes bodies at full detail** — 5 pedestrians at LOD0, 42 at LOD1, 196 at LOD2 — and the fleet is a Midtown fleet: 15 yellow taxis, 8 boro taxis, 12 sedans, 8 black cars, 3 box trucks.
* **30,447 pavement polygons and none dropped**, including 12,395 white markings, 7,740 sidewalk and 636 crosswalk.

## What does not match

* **The two frames are of different distances.** A curtain wall from its own pavement against a tower 222 m down the block.
* **The facade cannot be compared at all**, so nothing can be said here about One57's own glazing, its setbacks or its crown — the parts the photograph is entirely made of.
* **The subject is not in the frustum's in-cone list**, although it is on the view axis (J88).
* **Published under-lit at +4.70 stops.** Per the record's own note this is beyond hand-held recovery, and the luminance comparison should be read as the number the record gives it rather than as a fidelity reading.
* **The render is darker at the midtone and flatter** — p50 **0.4958** against **0.5813**, a ratio of **0.853**, mean **0.95×**, sd **0.1966** against **0.2737** (**0.718×**). The photograph's median sits **0.723 stops** above the grey convention and the render's **0.224**, a **−0.499-stop** difference (J83).
* **The near buildings are shells with drawn-on windows.** Kit was capped to **6,938 of 21,616 in range** at a **1,150,723-triangle** budget, and the openings are not cut (Stage 34 / J51, measured at +48 GB).
* **The canopy is in full summer green on 3 November.** `leaf_off` is a binary switch with a 15 November threshold, so there is no autumn state at all: the New York year has six weeks of turning leaves and this build has bare or green and nothing between (J97).
* **Four of six tiles in range have no structures file** — 2 imported, **4 without a file** — under a block served by three subway lines.
* **1,189 of the 2,077 trees are a substituted species** and **4** are scaled outside the allowed band.
* **10 props across four kinds in range have no asset** — 6 artworks, 2 misc structures, 1 drinking fountain, 1 real-time information sign.
* **The clearance note and the clearance field disagree about the nearest agent, and both are true.** The note reads *the nearest simulated agent is `agent_ped_726.3` 0.6 m away* while the field `nearest_agent` names a taxi at **8.8 m** and marks itself *after the cull over the observer*. The 0.6 m body is one of the **19 pedestrians dropped for standing over the observer** and is not in the frame. A reader of the note alone would conclude the frame has a person at the lens (J91, J98).
* **4,101 agents were dropped** — 1,440 pedestrians at the agent triangle budget, 1,089 outside the radius, 865 vehicles outside the radius, 440 vehicles at the budget, 199 pedestrians in the carriageway without crossing, 23 riderless bodies, 19 over the observer, 15 off a walkable surface, 11 vehicles off the carriageway, 5 on a car-free park drive, **3 pedestrians inside a building**, 2 vehicles over the observer.
* **There is no park ground within 150 m to check** — **0 samples**, although Central Park is a block away. Beyond 400 m the under-fraction is **0.3888** over 751 samples with a worst of **−4.501 m** and a z-fighting fraction of **0.0493**; between 150 and 400 m it is **0.2268** over 269 samples. The redrape moved **235,952** vertices, up to 2.739 m up and 3.331 m down.
* **Six park surface kinds keep the builder's flat colour** — infield clay, hard sport court, park grass, recreation grass, rink ice and bare ground (J40).
* **No cloud.** The reference's sky is a flat November haze behind the tower; nothing in this build reads a historical sky.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the two frames are of different distances | the photograph carries no GPS, so the item's recorded viewpoint was used, and that viewpoint is 222 m from a subject the photographer stood underneath; the reference chooser accepted it at **medium** confidence | **verification — open, and flagged on the sheet** |
| the subject is missing from the in-cone list | the frustum tests the catalogue footprint's centroid and `c_billionaires_row` is a composite whose centroid is not near this member (J88) | verification — cosmetic, and misleading in the record |
| the nearest catalogue row is Carnegie Hall at 55.2 m | the composite has no origin near its own members, so the nearest catalogue origin within 120 m belongs to a different landmark; the probe refused it and measured the geometry (J74) | verification — the rule working, and the catalogue is the weak part |
| published under-lit at +4.70 stops | a 32.6° November Sun almost due south into a north-west canyon; the frame is shade and the development says so (J83) | verification — declared, and correct |
| chroma 1.923 | an achromatic glass wall in haze against a frame of brick, stone and a taxi — a consequence of the pairing, not of the materials | reference |
| p50 0.853, sd 0.718 | the photograph is developed 0.723 stops above the grey convention and the render 0.224 above (J83) | reference |
| windows drawn on the shell | Stage 34 / J51, measured at +48 GB | declared decision — physically impossible here |
| 6,938 kit pieces of 21,616 | the kit triangle budget at 1,150,723 | performance |
| green canopy on 3 November | `leaf_off` is binary with a 15 November threshold and there is no autumn state (J97) | **verification — open, and a new corner of J97** |
| four of six tiles without a structures file | those tiles are unbuilt | data — open |
| 1,189 of 2,077 trees a substituted species | the species lists do not cover this stock and the nearest modelled species is used, counted rather than hidden | data — declared, counted |
| 10 props across four kinds unmapped | no asset exists for those kinds | data |
| the note names a 0.6 m pedestrian that is not in the frame | the note is written before the cull over the observer and the field after it, and nothing says so in the note itself | **verification — open, a record inconsistency (J91, J98)** |
| under-fraction 0.3888 beyond 400 m, z-fighting 0.0493 | the terrain grid coarsens to 40 m at the scene edge and the park builder drapes on its own heightmap; the redrape leaves this tail (J71) | geometry — open, bounded |
| six park surface kinds flat | the texture catalogue has no photographic set for clay, court, grass, ice or bare ground (J40) | data — declared, named on the sheet |
| 233 people of 3,220 asked | the agent triangle budget plus the placement rules, each with its own count | performance + verification |
| no cloud | nothing in this build reads a historical sky | reference — no source exists |
