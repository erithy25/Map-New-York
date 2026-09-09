# Chelsea Market

`landmark_chelsea_market` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Chelsea Market August 2022 003.jpg by Kidfly182, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2022-08-08 13:10:32, 1920x1440. [Commons page](https://commons.wikimedia.org/wiki/File:Chelsea_Market_August_2022_003.jpg)

**Camera** — 40.741975, -74.005836 (NYC_TM -4715, 4661) at z 3.9 m NAVD88 | azimuth 338.3°, pitch +0.4° | 21 mm on 36 mm (81.2° horizontal) | 1208x906.

**Sun** — azimuth 185.1°, elevation 65.2° at 2022-08-08T13:10:32-04:00 (EXIF DateTimeOriginal); 930.0 W/m² direct normal, sky at strength 0.0307, Filmic, +0.63 stops.

**Subject** — Chelsea Market at 64.8 m.

**In the scene**, within 557.5 m of the camera and not all of it in frame — 4 building tiles (143,412 tris), 4 landmark models of which **3 can fall inside the 81.2° frame**, 19,803 pavement polygons (6,852 white, 5,235 sidewalk, 3,659 roadbed, 2,882 curb, 399 crosswalk, 327 median, 284 plaza, 101 parking lot, 64 yellow), 1607 props of the 2,930 in range, 6,951 kit pieces, 85 vehicles and 300 people; 4,500,017 triangles. Ground mesh 81,608 triangles, 0 holes. 18 city surfaces are dressed from the shared photographic catalogue.

## Verdict — the photograph is a painted sign, the render is a slope of the model's own fabric, and nothing in either half can be checked against the other

**This sheet is not a comparison and must not be read as one.** The reference photograph is a hand-painted vendor board -- *LOS TACOS No. 1, TAKEOUT and DELIVERY, LOSTACOS1.com*, a cyclist drawn in black line on white, a red band along the bottom. There is no street in it, no sky, no brick and no building; it is a sign at arm's length. The chooser took it because its EXIF GPS is the nearest of the item's three photographs to the recorded viewpoint -- **57 m** against **110 m** and **100 m** -- and both of the others, `1.jpg` and `2.jpg`, are exteriors of the Chelsea Market brick with its own *CHELSEA MARKET* sign on the wall. This is the shape of **DEVIATIONS J71**: every test the chooser runs is a property of the photograph as a photograph, and none asks what it is a picture of. The row is open; its remedy is this verdict. The "high" direction confidence and the estimated azimuth of **338.4°** are the bearing from the phone's GPS to the subject's coordinate, not anything derived from the image; the two halves do not face the same way in any sense that can be tested.

**The record establishes the model and the instant, and both are sound.** The height probe lands **43 of 43** rays on built fabric at the subject's coordinate and reads **36.66 m** above the ground there, off `lm_c_chelsea_market.7`; the catalogue entry `c_chelsea_market`, **8.7 m** away, publishes **37.7 m**. That object's plan extent is **109.8 m by 98.2 m**: a block-scale building, as the complex is. The Sun is the photograph's own EXIF second, **185.1°** and **65.2°** high -- measured, not chosen -- and the crowd was drawn for a weekday, which a Monday is. The camera is the photograph's own GPS, moved **2 m** backwards because the view azimuth was closed off **27 m** ahead and the frame needs **31 m**.

**The render shows almost none of that building, and the sightline record says why.** `sightline.subject_visible` is `true` at **0.846** -- **11 of 13** rays -- but all eleven are counted under `subject_rays_on_own_fabric_nearer_than_recorded`: they land on `lm_c_chelsea_market.0` at **19.4 m**, not at the subject's **67.4 m**. The clearance probe puts the nearest built thing, `lm_c_chelsea_market.6`, at **18.7 m**, **40.6°** right and **16.4°** up; read off the render at full size, the crest of the pale slope at the right edge sits about **41°** right and **17°** up (my conversion of its pixel position through the field of view), which is that object. So the pale, concrete-textured surface filling the lower two thirds of the frame -- about **68 %** of it by my PIL count of low-chroma pale pixels below the crest -- is the Chelsea Market model's own fabric standing between the lens and the wall, and the "visible" verdict is eleven rays stopping on it. Neither exterior photograph in the folder shows any such surface at the building's foot.

**Not to be read into this sheet:** that the render is under-exposed (it is metered, J83), that the photograph's whiteness is a fault of the city, or that the building is missing from the model -- it is there at its published height.

## What matches

* **The material family.** The wall in the upper right of the render is dark brown-red brick with a regular grid of deep-set openings; the two unused photographs show a brown brick industrial facade with regular openings. `brown_brick` is one of the **18** dressed surfaces and the kit places **5,738 windows** across the scene.
* **The model is present at its published height**: **36.66 m** measured against **37.7 m** catalogued, **43 of 43** probe rays on built fabric, `c_chelsea_market` at LOD 0 with **40,256** triangles, **67.7 m** from the camera.
* **The chroma of the two halves is close** -- **0.0487** against **0.0418** -- by coincidence: black on white paint is nearly grey, and so is a concrete slope under a shaded wall.

## What does not match

* **Neither half's subject is in the other.** There is no common object, edge or horizon to align.
* **Two thirds of the render is a sloped pale surface at 18.7 to 19.4 m.** Its crest runs from a quarter of the way across at **43 %** of the height to the right edge at **24 %**. By my PIL sampling it reads about **54 %** display luminance mid-slope and **69 %** at the sunlit crest; only the crest exceeds 0.7, and about **3 %** of the whole frame does. The record names the object; it does not say what it stands for.
* **The brick wall the Sun should light is in shade.** The Sun stands at **185.1°**, high behind the camera's left shoulder, so a face turned towards the street the camera stands in would be lit; by my PIL sampling the brick in the upper right reads **7 to 8 %** display luminance across its whole extent, against a sky of **38 to 42 %** at the upper left. The sheet does not say what shades it.
* **The lighting, in the record's own units.** The render is developed at **+0.63** stops (metered; the physical rule alone gives +0.00), linear median **0.116251**; its display median **0.5014** sits **0.258** stops above the middle-grey convention. The photograph's median **0.8325** sits **1.875** stops above it, because a white board is white; the **-1.617** stop gap is the photograph's subject matter, not the city's exposure. The p05 gap, **0.0333** against **0.1277**, is the render's shaded brick against a photograph with no shadow in it.
* **The crowd, the lamps and the trees have no counterpart.** At the far left, a fifth to a seventh of the way across and just below mid-height, seven standing figures counted at full size -- blue coveralls, a hi-vis vest, a white shirt with a black pack, four in dark clothing -- and an eighth low pinkish shape cut by the crest; two tree canopies beside them; a cobra-head lamp; a run of about eleven lamp heads receding above a pale column at the left edge. No vehicle is in frame although **85** are placed; `clearance.nearest_agent` is null within the **20 m** probe.
* **The lens and the axis serve a building that is not being compared.** The lens was widened from **35 mm** to **21 mm** and the axis tilted **+0.4°** so that the top of `lm_c_chelsea_market.7`, **29°** above the horizon at **63 m**, sits in a **65°**-tall frame; the photograph has no verticals to compare either way.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the photograph is a painted sign, not the building | the chooser ranks on lighting, EXIF, Sun height, azimuth error and the distance band; this picture wins the band at **57 m** against **110 m** and **100 m**, and nothing tests what a photograph is of | reference; **DEVIATIONS J71** |
| two thirds of the render is a sloped pale surface at 18.7 to 19.4 m | `lm_c_chelsea_market.0` and `.6`, the model's own fabric, stand between lens and wall; the walk scored the position clear for **60 m**, and own-fabric hits nearer than the coordinate count as the subject, so **11 of 13** rays stop on the slab and the verdict reads visible | verification; the count rule of **DEVIATIONS J78** |
| the sunlit brick face is in shade at 7 to 8 % | not established by the record; the Sun is behind the camera at **65.2°** and the shading object is not named | geometry |
| render median a stop and a half under the photograph's | a white board developed **1.875** stops above middle grey against a render metered at **+0.63** stops, **0.258** above the convention | — (not a gap); **DEVIATIONS J83** |
| people, lamps and trees in one half and none in the other | correctly placed simulated content in a frame whose reference contains no street | — (not a gap) |
| lens widened and axis tilted for a subject the photograph does not show | the containment rule serves the subject, not the pairing | stated choice; **I18** |
