# Bank of America Tower at One Bryant Park

`landmark_bank_of_america_tower` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:View from Empire State Building, New York City, 20231001 1512 1371.jpg by Jakub Hałun, CC BY 4.0 (https://creativecommons.org/licenses/by/4.0), taken 2023-10-01 15:12:13, 1920x1282. [Commons page](https://commons.wikimedia.org/wiki/File:View_from_Empire_State_Building,_New_York_City,_20231001_1512_1371.jpg)

**Camera** — 40.754845, -73.986671 (NYC_TM -3106, 6088) at z 18.6 m NAVD88 | azimuth 70.0°, pitch +25.1° | 18 mm on 36 mm (90.0° horizontal) | 1280x854.

**Sun** — azimuth 226.5°, elevation 34.7° at 2023-10-01T15:12:13-04:00 (EXIF DateTimeOriginal); 807.6 W/m² direct normal, sky at strength 0.0346, Filmic, +1.62 stops.

**Subject** — Bank of America Tower at One Bryant Park at 210.4 m.

**In the scene**, within 720.6 m of the camera and not all of it in frame — 4 building tiles (247,682 tris), 7 landmark models of which **3 can fall inside the 90.0° frame**, 26,275 pavement polygons (11,776 white, 4,547 sidewalk, 4,247 roadbed, 3,307 curb, 1,346 plaza, 608 crosswalk, 381 median, 46 yellow, 17 parking lot), 2088 props of the 2,203 in range, 6,073 kit pieces, 69 vehicles and 281 people; 4,500,229 triangles. Ground mesh 88,194 triangles, 0 holes. 20 city surfaces are dressed from the shared photographic catalogue.

## Verdict — two different views of the city, and the subject is in only one of them

**This sheet is not a pairing of the same view, and it must not be read as one.** The photograph was taken from the 86th-floor deck of the Empire State Building, looking north over Midtown at an estimated **7.5°**; its EXIF GPS is **655.6 m** from the item's recorded viewpoint, past the **250 m** at which the record would accept it as the same place, so the camera was not stood on it. The render stands instead at the item's own viewpoint, Broadway at West 42nd Street, 1.6 m above the roadway, facing **70.0°** — the recorded heading, not one derived from the photograph, and it agrees with the bearing to the subject to **0.1°**. The two halves face different ways from points **656 m** apart and a skyscraper's height apart in elevation; the building the photographer stood on is in the render's scene at **714.8 m**, behind the camera. This is DEVIATIONS J60: a photograph of somewhere else, chosen because it is captioned with the subject's name.

**The subject is not in the render.** The record says so: `subject_visible` is **false**, **0 of 13** rays land on it, the line is closed at **27.0 m** by `t_-4_6_limestone`, and `subject_clear_fraction` is **0.077** — one ray in thirteen gets past the limestone, and it meets nothing out to **654 m**. The picture agrees. The right half of the frame is the limestone building itself, a tan window grid from the axis to the right edge and from the top edge down to a shopfront band; the left half is a brown-brick tower with a lighter flank; a blue curtain wall occupies the left fifth above the bus. The clearance walk was scored on the subject's sightline (the J79 rule) and its note records the result: no point within **80 m** had the **80 m** of open air the frame needed, the camera was moved **10 m** backwards, and the view is still closed **50 m** ahead. The lens was widened from **35 mm** to the **18 mm** floor and tilted **+25.1°** (I18): the record says the verticals converge, the frame is not comparable on proportion, and it exists to show the subject at all — which it does not.

**One line of the record needs reading against the rest of it.** The sightline note blames the item's coordinate or the model for the open line. The height probe contradicts it: at the subject's coordinate it lands **43 of 43** rays on `lm_c_times_square.6` and reads **284.75 m** above the ground there. Something tall stands where the item says the tower stands; the one clear ray is the top of a fan **284.4 m** tall aimed at mid-height **142.2 m**, grazing the roofline. The fault is a street-level viewpoint boxed in by the block ahead, not the coordinate. The height is read off a part of the *Times Square* catalogue model, origin **196 m** away, published height **365.8 m** (J74): the probe read a roof, not the spire tip.

## What matches

* **The instant and the light are the photograph's own.** Sun at azimuth **226.5°**, elevation **34.7°**, from the EXIF second; **807.6 W/m²** direct normal. This puts the Sun behind the camera's right shoulder, and sampling `render.png` with PIL agrees: the tan limestone face on the right is the lit surface, about two fifths of its upper pixels above the **0.7** threshold, while the brown brick face on the left reads at under half that brightness with no pixel above it — consistent with the nearer limestone block shadowing the building beyond. The photograph's towers are lit from the same quarter, west faces bright, north faces in shade.
* **The crowd is drawn for the right day type.** 2023-10-01 was a Sunday and the Sunday profile was used; **281** people and **69** vehicles were placed; the frame shows 8 pedestrians and 4 vehicles. The nearest simulated agent is `agent_ped_3097.1` at **18.8 m**, **15.0°** right of the axis.
* **The fabric of the block is Midtown fabric**: **6,073** kit pieces including **5,555** windows, **200** storefronts and **106** scaffold pieces; a bus, taxis, a bike rack, a kiosk and a cobra-head lamp on the kerb.

## What does not match

* **Nothing in the two frames is the same object.** The photograph's centre is the tower's faceted glass crown and spire, just right of centre, the H&M signs to its left, the Salesforce sign below, Central Park Tower and the Steinway tower on the skyline, 30 Rockefeller Plaza in the right sixth, the Hudson across the upper left and Central Park at the right edge. The render holds two mid-block facades and a bus. The three landmark models in the cone — the Public Library at **424.0 m** and **45.5°** off axis, One Vanderbilt at **724.7 m**, 30 Rockefeller Plaza at **776.4 m** — are all behind the limestone block.
* **Sky.** By a PIL mask about 3 % of the render is sky, a wedge in the top-left corner; about half of the photograph is sky. This is the chroma gap: render **0.1015** against **0.1584**, ratio **0.641** — blue sky and teal glass against tan stone and brown brick.
* **Lighting, in stops.** The render needed **+1.62** stops of metered development (the physical rule alone would have given **+0.31**), its linear median **0.058441** before development: a street canyon lit from behind the camera, well below the level at which the record calls a frame under-lit. The photographer exposed **0.945** stops above the middle-grey convention, the render sits at **0.224**, a gap of **-0.721** stops; the p50 ratio of **0.795** is that exposure choice first. The p05 gap, **0.1857** against **0.08**, is the scene: the deck view has deep canyon shadows and the street frame has none.
* **The facades are single-material grids.** Each building is one surface — tan limestone, brown brick — with window frames applied to a flat face rather than openings cut into it. The kit places **10** cornices and **7** pilasters in the whole scene; none is on these two faces (J66).
* **A black slot runs along the base of the right-hand building** where the shell meets the pavement, a band at zero luminance below the shopfront glazing; and the shopfront fascia is a blank white emissive strip, the brightest thing in the frame.
* **The bus reads "M14A SELECT"** on Broadway at 42nd Street; the M14A runs on 14th Street. The scene has **1** `mta_bus` and it carries one destination sign wherever it is placed.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| nothing in the two frames is the same object | a deck photograph **656 m** from the item's viewpoint looking **7.5°**; the render faces **70.0°** and is closed at **27.0 m** by `t_-4_6_limestone`, **0 of 13** rays on the subject (**DEVIATIONS J60**, J78, J79) | reference |
| the subject absent from a frame that exists to show it | a street viewpoint boxed in by the block ahead; no open air within **80 m**, lens at the **18 mm** floor, tilt **+25.1°** (I18), still the limestone face | verification |
| the record's note blaming the coordinate | generic text on the one clear ray; **43 of 43** probe rays on `lm_c_times_square.6` at **284.75 m** put the model at the coordinate | verification |
| height read off the *Times Square* model, catalogue **365.8 m** | a grouped catalogue entry with its origin **196 m** away; the probe reads the roof, not the spire (**DEVIATIONS J74**) | data |
| sky 3 % against half; chroma ratio **0.641** | a street canyon tilted up at two facades against a deck panorama | reference |
| **+1.62** stops of development; exposure offset **-0.721** | metered development at middle grey (**DEVIATIONS J83**); the photographer exposed **0.945** stops above the convention | — (not a gap) |
| single-material facades with applied window frames | one material family per facade class (**DEVIATIONS J66**); openings not yet cut into the shells | material |
| black slot along the building base; blank white fascia | the shell and the pavement do not meet at the kerb line; the shopfront emissive is left on in daylight with no sign content | geometry |
| "M14A SELECT" on a Broadway bus | one bus asset with one baked destination sign; route is not read from the network | data |
