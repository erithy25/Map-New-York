# Queens residential block: Forest Hills Gardens

`drive_queens_forest_hills` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Homes in Forest Hills Gardens 05.jpg by XanderAi, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2024-09-26 16:04:15, 1920x1081. [Commons page](https://commons.wikimedia.org/wiki/File:Homes_in_Forest_Hills_Gardens_05.jpg)

**Camera** — 40.717607, -73.844883 (NYC_TM 8882, 1961) at z 23.4 m NAVD88 | azimuth 140.0°, pitch +0.0° | 35 mm on 36 mm (54.4° horizontal) | 1280x720.

**Sun** — azimuth 239.6°, elevation 28.3° at 2024-09-26T16:04:15-04:00 (EXIF DateTimeOriginal); 754.0 W/m² direct normal, sky at strength 0.0365, Filmic, +1.45 stops.

**In the scene**, within 900.0 m of the camera and not all of it in frame — 6 building tiles (321,776 tris), 0 landmark models, 27,707 pavement polygons (12,707 white, 4,666 roadbed, 4,562 sidewalk, 3,619 curb, 801 crosswalk, 784 yellow, 459 median, 106 parking lot, 3 plaza), 1259 props of the 5,844 in range, 4,917 kit pieces, 65 vehicles and 407 people; 4,500,045 triangles. Ground mesh 96,800 triangles, 0 holes. 14 city surfaces are dressed from the shared photographic catalogue.

## Verdict — the same spot, not the same picture: a close-up of one clinker-brick house beside a street view of white stucco boxes

**The two halves stand on the same coordinate and do not look at the same thing.** The camera is on the photograph's own EXIF GPS, **221.9 m** from the item's recorded viewpoint at Station Square, and was not moved; the Sun is the photograph's own instant to the second. But the item names no subject, and the azimuth of **140.0°** is the item's street heading, not a direction read out of the picture (confidence **medium**). The photographer tilted up at one house across a garden wall, filling the frame with its brick and tile; the render is a level **35 mm** view along the street at **1.6 m** eye height, with roadway across its lower third, a black sedan in the centre and a bare tree trunk **10.4 m** from the lens. The record says so itself: compare on storey height, street width and material, not on composition. Nothing here tests whether the build places that particular house correctly.

**What the pairing does test is material, and there it fails plainly.** The photograph is a Tudor Revival house in variegated clinker brick — orange, red, purple-brown and tan in one wall — under a terracotta tile roof with copper gutters, half-timbering on the left wing, leaded casements in dark timber frames, an arched attic window with a wrought-iron balcony in the gable, and a brick chimney stack. The render's houses are two-storey white stucco blocks under grey pitched roofs, with dark-framed sash windows in two even rows, a red door under a small hood with iron stoop railings, and a blank red-brick block beside them. The build's class for this district, `queens_tudor_1930`, is described in its own catalogue as *"brick base, stucco and half-timber gables, slate roof, casement windows"* and declares `stucco` and `red_brick` as its materials; the shells take the material list and the roof pitch and none of the ornament. This is the case **DEVIATIONS J66** records under this sheet's own name: one material family per facade class, no source for a per-building hue, and the chroma reads **0.0337** against the photograph's **0.1191**, a ratio of **0.283**.

**The luminance figures must not be read as a fault of the city.** The render is developed at **+1.45 stops** (the physical rule alone would have granted **+0.61**), placing its linear median of **0.065793** at middle grey (J83); the photographer, facing dark brick under a white sky, exposed **-1.101** stops from that convention while the render sits at **0.254**. The render's mean of **0.4499** against **0.3791** and median of **0.5007** against **0.3207** are that exposure choice first. The photograph's p95 of **0.9281** is its overcast sky at clipping; the render's **0.7017** is a blue sky that never clips. The scene evidence is the stops themselves: **+1.45** is a well-lit late-afternoon frame, nowhere near the under-lit mark.

## What matches

* **The typology is right.** Two-storey houses, steeply pitched roofs, gable ends with chimney stacks, ivy at the base of the walls (**67** kit vegetation pieces; the class lists `ivy` and `pitched_roof`). The photograph's house is the same building type.
* **The storey height reads the same**: two rows of openings under the eaves, at a matching proportion to the wall height in both halves.
* **The instant is measured, not chosen.** Sun at **239.6°** and **28.3°** from EXIF `DateTimeOriginal`; the render's shadows fall to the left of the car and under the sills, where a Sun to the right and behind the camera puts them. The photograph's overcast light shows no Sun, so the direction cannot be checked against it.
* **The camera is the photographer's.** GPS-derived, not moved, the view clear for **24.0 m**; the nearest agent is **15.7 m** away and the one figure in the frame stands on the far pavement, not against the lens.
* **The street fabric is complete.** **6** of **6** tiles, **0** pavement polygons dropped, **0** holes; kerb, sidewalk and roadbed run through the frame, and **4,917** kit pieces including **3,386** windows stand in range.
* **The trees are at their measured height**: **511** of **512** instances scaled, mean **0.892**, **1** outside the band (J70).

## What does not match

* **The wall material, and it is the whole gap.** Chroma **0.283** of the photograph's. The photograph's wall is four brick colours at once under a tile roof; the render's is one stucco white (target albedo **0.6667**) beside one red brick under a grey roof. Half-timbering, leaded casements, the arched gable window and its balcony are not in the kit.
* **The framing.** Photograph: pitched up at one house from behind its garden wall, no street, sky only at the top edge. Render: level, along the street, road across the bottom third, two black sedans, and a bare honeylocust trunk left of centre rising through a brick-faced block at the top edge — a chimney of the house behind, or the tree's own missing crown; the record drops **9** impostor cards and does not say which.
* **Luminance, stated as stops**: development **+1.45**; exposure offsets **0.254** (render) against **-1.101** (photograph), **1.355** stops apart. Mean ratio **1.187**, median **1.561**, tonal spread **0.847**. The p05 floor, **0.0583** against **0.0426**, is inside the photographs' JPEG floor and not counted.
* **A quarter of the props in range were placed**: **1259** of **5,844**, capped at a triangle budget of **1,313,553**; the kit was capped too, at **1,357,840**.
* **The crowd is thinned by rule and by budget**: **347** pedestrians dropped for standing in the carriageway without crossing, **179** for not being on a walkable surface, **90** to the budget; **188** vehicles to the budget. Of the **65** vehicles drawn only **6** are LOD1, and the sedan in the centre of the frame is a smooth featureless body.
* **225** of the **512** trees are species-substituted, drawn at their own measured height as the nearest available species.
* **`roof_membrane` still binds the albedo cap** at **4.0**, residual **2.852**; the wrong source material rather than the wrong level (J66). No membrane roof is in this frame.
* **Point props with no asset**: **13** vending machines, **5** miscellaneous structures, **2** swimming pools, **2** payphones, one artwork, one billboard, one memorial (J23).

## Cause of each gap

| gap | cause | class |
|---|---|---|
| chroma 0.283 of the photograph; one stucco white where the photograph is four brick colours and tile | the facade class states two materials for the whole typology and varies tone, not hue, per building; no source records what an individual house is faced with | material — **DEVIATIONS J66** |
| no half-timbering, leaded casements, arched gable window or balcony | the class description names them; the kit carries none and the shell takes only the material list and the roof pitch | geometry |
| the two halves are framed differently | the item names no subject; the azimuth is the item's street heading, not derived from the picture (confidence medium), and the camera is level where the photographer tilted up | reference |
| luminance ratios 1.187 mean, 1.561 median | metered development at +1.45 stops against a photograph exposed -1.101 stops from the same convention; the physical light is the photograph's own instant | — (not a gap) — **DEVIATIONS J83** |
| p05 0.0583 against 0.0426 | the photographs' JPEG floor | — (not a gap) |
| 1259 of 5,844 props placed | triangle budget 1,313,553, declared in the record | performance |
| 347 pedestrians dropped in the carriageway, 188 vehicles to the budget, 6 of 65 at LOD1 | the pedestrian rule refuses a person standing in a live carriageway; the vehicle budget caps and the remainder falls to LOD2 | performance |
| 225 of 512 trees species-substituted | no modelled species matched the census row; the nearest by size and taxon is used at the measured height | data |
| roof_membrane at the albedo cap, residual 2.852 | Rubber004 is black rubber where a membrane roof runs from black EPDM to white TPO; recorded as open | material — **DEVIATIONS J66** |
| unplaced vending machines, structures, pools, payphones, artwork, memorial | datasets with no modelled asset; artworks and memorials are deliberately not stood in for by a generic mesh | geometry — **DEVIATIONS J23** |
