# Brooklyn brownstone block: Park Slope, Seventh Avenue / Garfield Place

`drive_brooklyn_park_slope_7th_ave` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:195 Garfield Place.jpg by Beyond My Ken, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2013, 1920x1887. [Commons page](https://commons.wikimedia.org/wiki/File:195_Garfield_Place.jpg)

**Camera** — 40.672465, -73.977455 (NYC_TM -2321, -3057) at z 29.1 m NAVD88 | azimuth 32.4°, pitch +0.0° | 35 mm on 36 mm (54.4° horizontal) | 1054x1036.

**Sun** — azimuth 85.4°, elevation 32.2° at 2013-06-21T08:30:00-04:00 (photograph year only, 21 June assumed, and 08:30 **chosen**, not measured: of the hours that put the Sun above 20 deg it is the one whose bearing (85 deg) comes closest to the view azimuth (32 deg), 53 deg off, so the Sun is behind the camera and lights what it looks at); 788.3 W/m² direct normal, sky at strength 0.0352, Filmic, +4.12 stops.

**In the scene**, within 756.6 m of the camera and not all of it in frame — 6 building tiles (492,134 tris), 2 landmark models of which **0 can fall inside the 54.4° frame**, 23,064 pavement polygons (9,385 white, 5,341 sidewalk, 4,038 roadbed, 3,131 curb, 541 crosswalk, 291 yellow, 274 median, 44 parking lot, 19 plaza), 5826 props of the 5,930 in range, 3,708 kit pieces, 88 vehicles and 371 people; 4,500,208 triangles. Ground mesh 89,872 triangles, 0 holes. 19 city surfaces are dressed from the shared photographic catalogue.

## Verdict — the same street, not the same view: a shed and a garage wall stand in for a row of Eastlake tenements

**The two halves of this sheet do not face the same way, and the record says so before the reader looks.** The camera stands on the photograph's own EXIF GPS, **36.6 m** from the item's recorded viewpoint at the Seventh Avenue crossing — which, by the photograph's own title, puts it on Garfield Place in front of number 195. The heading is not the photograph's: the item names no subject, the azimuth **32.4°** is Seventh Avenue's own bearing from `meta.json`, and the reference's direction was never derived from the image (confidence **medium**). The pitch is level because there is nothing to aim at. The record's own instruction is to compare street width, storey height and material, not composition.

**What each half shows.** The photograph looks obliquely along the north row of Garfield Place with the camera tilted well up: four storeys of yellow and red brick, oriel windows on carved stone brackets, a conical slate turret over the bay, green-painted pressed-metal cornices with finials, terracotta panels and arched attic windows, air-conditioners in half the openings, two street trees in leaf, and black SUVs parked along the kerb with an arm out of one window. The sky is a blown white haze. The render, level on a 54.4° lens, looks across an asphalt carriageway that takes the lower two-fifths of the frame at a hunter-green sidewalk shed on cross-braced posts, a one-storey brick structure with a parapet and a roof bulkhead to the right, a blank pale flank wall behind the shed in the upper middle, and a four-storey tan-brick block with punched windows and air-conditioners at the top right. A honeylocust stands left of centre — the record's `prop_tree_honeylocust_small_2`, **8.9 m** away at **-18.1°** — and the view axis runs into a dark recess under the shed, clear for **38.7 m**. No car, no person, a sliver of sky at the top right corner.

**What the reader must not take from it.** This sheet is not evidence that 195 Garfield Place is or is not modelled: the render's field holds no row of houses at the photograph's angle, and the record cannot say what stands in the block face it does show. The sidewalk shed is a real object from the permit data the city is built to — **31** scaffold pieces are in the scene — but the photograph is of **2013** and the shed is of the build's own date: a fact of the wrong year, not a modelling fault. The render's brightness is not the light on the street: the scene was developed at **+4.12 stops** where the physical rule alone would have given **+0.42**, and the record itself marks it under-lit (J83). The instant is chosen (J80): 21 June at 08:30, so that the Sun at **85°** falls behind a camera facing 32°. The Commons categories for this file place it on 28 July 2013, a Sunday; the pipeline read the year only, so the crowd was drawn for **a weekday**.

## What matches

* **Storey height and material at the top right.** The four-storey tan-brick block with punched openings and air-conditioners in them (**243** window accessories in the scene) is the photograph's building type, height and brick tone; `tan_brick` is dressed from the `Bricks029` scan and `red_brick` from `Bricks082A`, at their stated albedo.
* **Street trees in leaf at the kerb.** Two young trees in front of the photograph's houses; the honeylocust at **8.9 m** in the render. Trees stand at the census's height: **5,287** instances scaled, mean scale **0.913**, **6** outside the band (J70).
* **Hard sun from behind the camera.** Foliage shadows lie across the shed fascia and the brick wall in the render; the photograph's facades are sunlit too, with tree shadow on the lower left house, under a hazed sky.
* **The camera was not moved.** It stands on the photograph's GPS, in open air at **1.6 m** eye height, view clear for **38.7 m**, no agent within **60 m**.
* **The fabric is of this district**: **3,708** kit pieces including **2,165** windows, **274** storefronts, **247** entry doors, **145** parapets, **112** fire escapes, **106** cornices, **64** string courses and **34** quoins; **23,064** pavement polygons with **0** dropped, **6** of **6** tiles, **0** holes.

## What does not match

* **The block face in the render carries none of the photograph's articulation.** No oriel, no turret, no bracketed cornice, no terracotta, no arched attic window: a shed, a one-storey brick structure and a blank flank, with a flat window grid above. The kit's cornices, quoins and string courses exist in the scene but not on the faces this frame sees.
* **The render is empty of traffic and people.** **88** vehicles and **371** pedestrians are placed and none stands within **60 m**; the photograph's foreground is three parked SUVs and a person. **165** vehicles and **173** pedestrians were dropped for triangle budget, **272** and **413** for radius.
* **A sidewalk shed the photograph cannot contain.** **31** scaffold pieces; the photograph is of 2013 and shows an open row.
* **The photograph is tilted up and the render is level.** The photograph's frame is mostly building, the render's lower two-fifths is asphalt; the item names no subject to tilt at.
* **Lighting as stops.** Development **+4.12 stops** (unclamped **+4.12**, physical rule **+0.42**), linear median **0.010386**; the record calls the scene under-lit. Display statistics: render mean **0.6079** against photograph **0.4799** (**1.267**), p50 **0.4981** against **0.4763** (**1.046**), exposure offset **0.238** against **0.099** stops. The median ratio near unity says both are developed to the same convention; the mean ratio is the render's brighter shadows.
* **The render has no deep shadow.** p05 **0.2725** against **0.0484**, sd **0.2347** against **0.2928** — far above the JPEG floor. A scene lifted four stops has its floor lifted with it, and the frame holds no dark car bodies or canopy shade.
* **Colour is half the photograph's.** Chroma **0.0717** against **0.1478**, ratio **0.485**. The photograph is yellow brick against red brick against green cornices; the render is one tan-pink brick at two tones plus the green shed (J66).
* **Two landmark models, neither in frame**: the Memorial Arch at **641.1 m** and the Central Library at **790.7 m** are behind or aside.
* **Budget and substitution, declared**: kit capped at triangle budget **1,093,076**; **17** impostor cards dropped; **1,857** trees species-substituted; `roof_membrane` and `wood_clapboard` at the albedo cap.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the block face carries none of the photograph's articulation | the azimuth is Seventh Avenue's bearing from `meta.json`, not derived from the image, so the frame looks across the street rather than along the row; oriels, turrets, bracketed cornices and terracotta are not kit categories in any case | reference + geometry |
| no traffic or people in frame | agents are placed city-wide from one simulation frame and none of 88 vehicles or 371 people falls within 60 m of this camera | verification |
| a sidewalk shed the photograph cannot contain | scaffold is built from the permit set current at build time; the photograph is of 2013 | reference |
| photograph tilted up, render level | the item names no subject, so the pitch is 0.0°; the photographer aimed at the houses | stated choice |
| +4.12 stops development, mean 1.267x | metered development: median placed at middle grey (**DEVIATIONS J83**); the instant is chosen, not measured (**DEVIATIONS J80**); the day type is a weekday where the Commons category gives a Sunday | verification |
| no deep shadow, p05 0.2725 against 0.0484 | the four-stop lift raises the floor of a frame that has no dark objects in it; the photograph's floor is car paint and canopy shade | verification |
| chroma 0.485x | `shellmat` varies tone within a facade class and never hue, so a street of individually coloured houses is drawn in one palette (**DEVIATIONS J66**) | material |
| 2 landmarks placed, 0 in frame | both stand behind or beside the camera; a scene count, not a frame count | — (not a gap) |
| kit capped, 17 cards dropped, 1,857 trees substituted | triangle budget 1,093,076; no modelled species matched, the nearest by size and taxon used | performance / data |
