# Central Park perimeter wall and gates

`landmark_central_park_wall_gates` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Central Park td (2019-07-11) 064 - Wien Walk, Central Park Zoo.jpg by Tdorante10, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2019-07-11 17:41:51, 1920x1280. [Commons page](https://commons.wikimedia.org/wiki/File:Central_Park_td_(2019-07-11)_064_-_Wien_Walk,_Central_Park_Zoo.jpg)

**Camera** — 40.765984, -73.97233 (NYC_TM -1885, 7328) at z 16.2 m NAVD88 | azimuth 211.0°, pitch +0.0° | 35 mm on 36 mm (54.4° horizontal) | 1280x854.

**Sun** — azimuth 275.1°, elevation 29.0° at 2019-07-11T17:41:51-04:00 (EXIF DateTimeOriginal); 760.7 W/m² direct normal, sky at strength 0.0361, Filmic, +3.25 stops.

**Subject** — Central Park perimeter wall and gates at 192.1 m.

**In the scene**, within 887.1 m of the camera and not all of it in frame — 7 building tiles (309,168 tris), 14 landmark models of which **6 can fall inside the 54.4° frame**, 33,638 pavement polygons (17,200 white, 8,271 sidewalk, 3,375 curb, 3,284 roadbed, 770 crosswalk, 450 median, 126 plaza, 120 yellow, 42 parking lot), 271 props of the 5,326 in range, 2,501 kit pieces, 88 vehicles and 441 people; 4,500,213 triangles. Ground mesh 94,952 triangles, 0 holes. 20 city surfaces are dressed from the shared photographic catalogue.

## Verdict — neither half shows the perimeter wall: the photograph is the Zoo's gate, the render is a lawn in front of the Plaza

**This sheet does not compare its subject with anything.** The photograph is the brick gate of the Central Park Zoo at the head of Wien Walk, inside the park: brick piers with iron gates, a gatehouse with a bell-shaped black roof on the left, a brick lodge with a round window on the right, wet hexagonal pavers, benches down both sides and a white overcast sky. The render, from the photograph's own GPS and on the bearing to the item's subject coordinate, is an open lawn, a broad grey path curving away to the left, a dozen or so tall tree trunks, and beyond them the Plaza Hotel's white flank and green roof, taxis on the avenue and a knot of people by a subway entrance at the left edge. No wall, gate or pier is in either picture, and the record says why.

**The subject's coordinate is off the thing it names, and the record measured that.** The height probe cast **43** rays at the coordinate and **0** landed on built fabric; nothing built stands within **6 m** of it, and the nearest built thing is `lm_c_the_plaza.6`, **30 m** away at bearing **270°**. The nearest catalogue origin is `c_the_plaza` at **80 m**, so the wall model the catalogue holds (one of the **14** landmarks placed, listed as behind or aside) is not what the probe found: J74's shape, a long model whose origin is nowhere near the part the item points at. With no height the axis was left level and the lens not widened (J72's rule, applied correctly), and no sightline was tested: `subject_visible` is **null**, not false, so J78's fraction does not exist here and the pairing is not a visibility verdict either way. The coordinate itself is the J57/J82 fault, a subject placed on open ground beside the thing it stands for.

**The photograph is the wrong photograph, and its GPS is right.** The camera stands **179.6 m** from the item's recorded viewpoint at Grand Army Plaza, inside J60's threshold, so the distance gate passed it; its title, description and categories all say Central Park Zoo and Wien Walk, and that is what it shows. The chooser matched the query "Central Park entrance gate" and took a gate not on the perimeter. Its direction estimate, **210.8°** at high confidence, agrees with the rendered azimuth of **211.0°** to a fraction of a degree, so the two halves do face the same way; the item's own recorded azimuth is **280.0°**, **69.0°** off, and belongs to a viewpoint the camera does not use. The instant is the photograph's own EXIF; the Sun at **275.1°**, elevation **29.0°**, is over the camera's right shoulder.

**What this sheet is evidence of** is the park's south-east corner at that bearing, not the wall: read it for the Plaza, the lawn and the avenue, and for nothing in its title.

## What matches

* **The direction of view.** The record's estimate from the photograph, **210.8°**, and the render's bearing, **211.0°**, are the same heading; the camera stands on the photograph's own GPS, moved **0.0 m** by the clearance walk.
* **A park with mature trees on both sides.** The photograph's canopy closes over the walk; the render has **148** trees placed and a dozen or so trunks in frame, their crowns hiding the Plaza's upper storeys as the photograph's hide the sky.
* **The Plaza's presence and scale where the record puts it.** `The Plaza Hotel` is in the cone at **248.0 m**, off-axis **16.1°**, and in the render it is the white block with the green mansard filling the right third of the frame, its roof above the top edge, consistent with the catalogue's **76.2 m** for `c_the_plaza`.
* **A weekday late afternoon.** The snapshot is drawn for **17:00** on a weekday from the density table, and the render shows a working avenue: taxis and boro taxis nose-to-tail along the far kerb (**19** and **12** placed), and a cluster of about twenty figures at the subway entrance out of **441** people in the ring. The photograph, the same Thursday evening, has about ten people and a food cart.
* **Sun direction and the shadows it makes.** With the Sun at **275.1°** and the axis at **211.0°**, cast shadows fall leftward and toward the camera; I sampled the lawn: a flat half-tone across almost the whole lower frame, sunlit dapples only in the right quarter between the trunks, and nothing in the bottom third above 0.7. The surfaces above 0.7 are the Plaza's white spandrels, the cream tower at the top left and the sky gap at the centre: a lawn in the long shadow of the trees and the 57th Street towers, as it would be at that hour.

## What does not match

* **The subject.** The photograph's gate, gatehouse and lodge are absent from the render, and the perimeter wall is in neither. The build has **22** `parks_building`, **10** `artwork` and **2** `memorial` props in range with no asset mapped, the classes a zoo lodge would fall under if it is in the dataset at all.
* **The ground.** The photograph's walk is hexagonal asphalt pavers, wet, with puddles reflecting the sky; the render's path is a featureless grey plane, dry and unreflecting, and it is a third of the frame.
* **The furniture.** About a dozen benches line the photograph's walk; the render places **11** in the whole scene and one is visible, on the Plaza's sidewalk at the right, none along the path.
* **The sky and the weather.** The photograph is overcast after rain, the sky a white field at p95 **0.9527**; the render is a clear day at **760.7 W/m²** direct normal with blue sky at the centre top. The record has no weather field; the instant is the photograph's, the weather is not.
* **Development and floor.** The frame is metered at **+3.25** stops (the physical rule alone would have given **+0.57**): the lawn and path sit in shade and the metering lifted the frame to put the median at middle grey. The photograph is exposed **-1.197** stops below that convention and the render **0.23** above it, which is the whole of the p50 ratio of **1.6**. The p05 gap, render **0.1594** against the photograph's **0.0448**, is real and not JPEG floor: the wet pavers and the shadowed foliage go near-black in the photograph and nothing in the render does.
* **Chroma.** Render **0.0821** against **0.0668**: the flat green lawn and green roof carry more colour than a grey wet afternoon; the clear-sky instant, not the materials.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the subject in neither half | the item's coordinate stands on open ground with nothing built within 6 m; the wall model's origin is outside the 120 m search and the nearest built thing is the Plaza; no height, no tilt, no sightline (**DEVIATIONS J57/J82**, J74, J72) | data |
| the photograph is the Zoo gate, not the perimeter wall | the chooser matched on keywords and the photograph's GPS is 179.6 m from the viewpoint, inside the distance gate (J60's shape, below its threshold) | reference |
| featureless grey path where the photograph has wet hexagonal pavers | park paths are drawn as one sidewalk surface; no paver unit and no wet-surface state exist in the material set | material |
| no benches along the walk | 11 benches placed in the whole scene under the prop triangle cap; the Zoo's furniture is not in the placed set | data |
| clear sky against an overcast, wet afternoon | the Sun instant is the photograph's EXIF but no weather state is recorded or rendered; direct normal 760.7 W/m² is a clear-sky value | stated choice |
| +3.25 stops of development and a p05 of 0.1594 against 0.0448 | metered development (**DEVIATIONS J83**) lifts a shaded lawn to middle grey and with it the floor; the photograph was exposed a stop and more below that convention | verification |
| chroma 1.229 of the photograph's | the flat lawn green and the green mansard under a clear sky against a grey wet scene; the instant, not the palette | — (not a gap) |
