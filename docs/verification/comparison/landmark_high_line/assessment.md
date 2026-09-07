# High Line

`landmark_high_line` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:The High Line Hotel 001.jpg by Kidfly182, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2023-01-21 13:36:45, 1920x1440. [Commons page](https://commons.wikimedia.org/wiki/File:The_High_Line_Hotel_001.jpg)

**Camera** — camera 40.74608, -74.00532 (NYC_TM -4672, 5118) z 13.6 m NAVD88 | azimuth 29.0deg pitch +0.0deg | 35 mm on 36 mm (54.4deg horizontal) | 1208x906. View direction: 29.0 deg as recorded in meta.json.  This item names no subject and the reference photograph's own view direction was not derived from the image (confidence: medium), so the two halves of this sheet are not guaranteed to face the same way -- compare them on street width, storey height and material, not on composition. Aim: level optical axis (the reference names no subject to aim at).

**Sun** — azimuth 203.5°, elevation 26.0° at 2023-01-21T13:36:45-05:00 (EXIF DateTimeOriginal).

**In frame** — 6/6 building tiles (160,976 tris), 5 landmark models, 1,661 pavement polygons, 525 props, 5,448 facade-kit pieces; 3,295,802 triangles; ground mesh 211² at 2.0 m near / 40.0 m far.

**Verdict — the camera is at the right height above the right street and there is no High Line under it: no deck, no planting, no rails, no benches — just a Chelsea street seen from 10.7 m up, which is a fair test of the surrounding fabric and no test at all of the park**

## What matches

* The eye height is right and its source is published: the High Line deck at 30 ft (9.1 m) above the street on the West Side Line viaduct plus 1.6 m, giving 13.6 m NAVD88 over a 2.9 m street.
* The camera stands on the photograph's own EXIF GPS, 58 m from the item's nominal viewpoint.
* The Chelsea fabric either side is right in kind: four- and five-storey red-brick blocks with arched window heads, projecting cornices, roof bulkheads and chimneys, at the right heights and the right rhythm — and the reference's own subject, the High Line Hotel's brick and gabled dormers, is the same vocabulary.
* The Hudson Yards towers close the view north at the right distance and the right height, with glass curtain wall legible on them.
* The winter tree state is right for a January photograph: bare canopies with visible branch structure, 24 opaque impostor cards dropped.
* The elevated green structure at the right of the frame is the viaduct's own steel edge, in the right place.

## What does not match

* There is no High Line. The deck the camera stands on, its planting beds, the retained rails, the concrete plank paving, the benches, the railings and the Chelsea Grasslands the viewpoint names are all absent; the eye floats 10.7 m above a street with nothing under it.
* The frames face different ways: the item looks north along the park, the photograph is a courtyard view of the High Line Hotel. The item names no subject and the photograph's direction was assumed.
* No brick texture, no window glazing, no sills, no cornice detail: the blocks are flat colour with openings cut in them.
* No people on a park that is never empty, and no vehicles on the street below.
* The street and sidewalks are flat untextured planes with no markings.
* Props were capped by the triangle budget at 525 placed.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| no High Line deck, planting, rails or benches | the viaduct and its park are neither building footprints nor props, so no stage builds them; the eye height is asserted from the published deck level instead | geometry |
| the two halves face different ways | the item names no subject and the reference stage assigned it the item's own azimuth | reference |
| no brick texture or glazing | shells carry a per-material base colour; the kit supplies openings without glass | material |
| no people or vehicles | no crowd or traffic placement feeds the verification scene | data |
| untextured street | pavement polygons carry a kind but no texture or markings | material |
