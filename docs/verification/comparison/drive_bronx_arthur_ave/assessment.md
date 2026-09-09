# Bronx drive-through: Arthur Avenue (Belmont)

`drive_bronx_arthur_ave` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Arthur Avenue 09 - M&G Restaurant.jpg by Joe Mabel, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2026, 1920x1280. [Commons page](https://commons.wikimedia.org/wiki/File:Arthur_Avenue_09_-_M%26G_Restaurant.jpg)

**Camera** — 40.85524, -73.88776 (NYC_TM 5255, 17278) at z 25.9 m NAVD88 | azimuth 190.0°, pitch +0.0° | 35 mm on 36 mm (54.4° horizontal) | 1280x854.

**Sun** — azimuth 203.9°, elevation 71.3° at 2026-06-21T13:30:00-04:00 (photograph year only, 21 June assumed, and 13:30 **chosen**, not measured: of the hours that put the Sun above 20 deg it is the one whose bearing (204 deg) comes closest to the view azimuth (190 deg), 14 deg off, so the Sun is behind the camera and lights what it looks at); 940.2 W/m² direct normal, sky at strength 0.0304, Filmic, +1.29 stops.

**In the scene**, within 735.9 m of the camera and not all of it in frame — 4 building tiles (261,870 tris), 0 landmark models, 25,829 pavement polygons (11,437 white, 5,027 sidewalk, 4,117 roadbed, 3,331 curb, 670 crosswalk, 656 parking lot, 403 yellow, 148 median, 40 plaza), 3623 props of the 3,790 in range, 6,802 kit pieces, 89 vehicles and 393 people; 4,500,027 triangles. Ground mesh 88,200 triangles, 0 holes. 14 city surfaces are dressed from the shared photographic catalogue.

## Verdict — the same street from two places facing two ways; the sheet compares a street type, not a picture

**The photograph is a close oblique view of one restaurant frontage from the pavement in front of it; the render is a level view down the avenue from a crosswalk at the corner.** The left half is a dark-red painted shopfront with an enclosed glazed vestibule and black lettering on a cream stucco fascia, red brick with a pale quoined corner above, a grey vinyl-sided two-storey house with a scalloped porch awning and iron railings beside it, two traffic cones and a bin on the pavement, a yellow-painted kerb, a tree crown at top right and a white overcast sky. The right half is a three-storey tan-brick block with a continuous green-fascia shopfront band, street trees down both kerbs, a cobra-head lamp, a red hydrant, a continental crosswalk in the foreground, a woman in a red shirt walking a child up the right-hand pavement, an empty carriageway to the vanishing point and a clear blue sky. Nothing in the render is the thing in the photograph, and the record says so: the item names no subject, the photograph's direction was not derived from the image (confidence **medium**), the **190.0°** heading is the item's street heading, and the two halves are "not guaranteed to face the same way -- compare them on street width, storey height and material, not on composition".

**The camera is where the photograph was taken and then somewhere else.** It began on the photograph's own EXIF GPS, **15.9 m** from the item's recorded viewpoint, and was moved **35.7 m** onto the nearest real crosswalk polygon because the recorded azimuth was closed off **10 m** ahead, less than the **12 m** the frame needs. From the new point the azimuth is clear for **45.4 m** and nothing built stands within **20 m**. This is not J60: the GPS is on this street within a block of the item. But the render stands at a corner where the photographer stood mid-block, looking along the avenue where the photographer looked across the pavement at a frontage; the corner's kerb radius fills the lower right of the frame as blank concrete for the same reason. The walk was "pavement snap with a clear frame", not scored on a subject sightline because there is no subject, so J79 does not apply. The reader must not take the tan block on the left of the render for the red-brick restaurant building in the photograph; the sheet cannot say whether it is the same block seen along its flank or a different one.

**The instant is chosen and the photograph is overcast, so the light is not evidence either way (J80, J83).** The record has the year only and picks 13:30 on 21 June to put the Sun **14** degrees off the view azimuth at **71.3°** elevation; the photograph has no visible shadow, a white sky and flat light. The development is metered: **+1.29 stops** above the physical rule's **+0.00** placed the linear median (**0.073481**) at middle grey, far short of the level the record treats as under-lit. The photographer exposed **-0.733** stops from that convention and the render sits at **0.252**, so the halves are developed nearly a stop apart before anything in the city is compared.

## What matches

* **The street type.** Party-wall blocks of two and three storeys, a continuous glazed shopfront under a fascia or awning line, regular windows above, trees at the kerb — what the photograph shows at close range and the render at length.
* **The shopfront band is built, not painted on**: **907 storefront** and **125 storefront_interior** pieces, 195 entry doors, **147 fire escapes**, 180 parapets, 120 quoins, 119 cornices, 111 string courses and 77 pilasters among **6,802** kit pieces, with 3,974 windows.
* **The photograph's three materials are in the dressed set.** Red brick with pale stone trim, grey vinyl siding and plain brick are `red_brick`, `limestone`/`tan_brick` and `vinyl_siding`, among the **14** surfaces dressed from the catalogue.
* **The trees stand at census height.** **3136** trees are in range; **3125** are scaled to the height their trunk diameter gives, mean scale **0.826**, **11** out of band. The canopy is a line of crowns with sky and cornice line visible between them, not a tunnel.
* **Kerb furniture is the right furniture**: **134** cobra-head street lamps, **56** hydrants, **120** manholes placed; the hydrant and lamp in frame stand at the kerb, where the photograph's yellow hydrant-zone kerb says one belongs.
* **The road is drawn as a road**: 4,117 roadbed and 3,331 curb polygons, 11,437 white and 403 yellow markings, 670 crosswalks; the foreground crosswalk is separate white bars with asphalt between them.
* **The crowd is the simulation's own**, drawn for a **Sunday** at 13:30: **393** pedestrians and **89** vehicles; the nearest agent, `agent_ped_362.2`, is **8.4 m** away at **18.1°** right — the woman in the red shirt.
* **Nothing is missing from the fabric**: 4 building tiles, 0 LOD substitutions, 0 pavement polygons dropped, 0 holes in the ground.

## What does not match

* **The frontage in the photograph is not in the render, and the kit could not make it.** Lettering on a fascia, an enclosed vestibule, dark-red painted framing, a fringed awning, a scalloped porch awning, railings, cones and a bin are what the photograph is made of. The render's shopfronts are one green fascia over dark glazing between beige piers, repeated along the block, under a regular grid of identical openings in tan brick.
* **The nearest building is a different building.** Two storeys of red brick and stucco with a quoined stone corner in the photograph; three storeys of tan brick in the render, seen from **35.7 m** away.
* **The carriageway is empty.** **89** vehicles were placed; none is in the frame. **83** were dropped to the triangle budget and **201** left outside the radius. The photograph shows no vehicle either, only a yellow no-parking kerb, so the sheet does not measure this gap; it shows a retail avenue at half past one with no traffic on it.
* **Sky and light**: clear blue with hard foliage shadows against white overcast with none. Mean **0.4508** against **0.392** (**1.15**), median **0.5003** against **0.3628** (**1.379**), p95 **0.7879** against **0.875**, standard deviation **0.2272** against **0.2686** (**0.846**). The p05 pair, **0.1061** against **0.0519**, is a gap of about a twentieth, the photographs' JPEG floor.
* **Chroma 0.0703 against 0.0921 (0.763).** The photograph's colour is dark-red paint, orange cones and a yellow kerb; the render's is the green fascia and foliage. Each facade class carries one photographic family varied per building only by seed (J66), and shopfront paint is not a thing the kit has.
* **The child eight metres from the lens wears a black cut-out bodysuit.** A correctly placed pedestrian at the right scale; the archetype's wardrobe is what draws the eye.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the photographed frontage is not in the render | the halves face different ways from points 35.7 m apart; the item names no subject and the photograph's direction was never derived from the image, as the record's azimuth line states | reference |
| signage, vestibule, painted framing, awnings, railings absent | the storefront kit has 907 glazed fronts with a fascia and no lettering, enclosures, paint or awning types; the classifier has no source for them | geometry |
| the nearest building is a different building | the camera was moved 35.7 m onto a crosswalk under the "pavement snap with a clear frame" rule; no subject sightline exists to score against | verification |
| empty carriageway | 89 vehicles placed, 83 dropped to the triangle budget, 201 outside the radius, none in the frame; the sheet cannot say whether kerbside parking is modelled | performance |
| clear sky and hard shadows against overcast | the instant is chosen, not measured (**DEVIATIONS J80**); the photograph's weather is not in its record and the sky model is clear | stated choice |
| luminance ratios away from unity | metered development at +1.29 stops against a photographer at -0.733 (**DEVIATIONS J83**); a development difference, not a fault of the city | — (not a gap) |
| chroma 0.763 | one photographic family per facade class, varied by seed (**DEVIATIONS J66**); shopfront paint and street colour are not in the kit | material |
| child in a cut-out bodysuit | pedestrian archetype wardrobe, drawn from the 36 bodies available | data |
