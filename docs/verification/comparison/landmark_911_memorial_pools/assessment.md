# National September 11 Memorial pools

`landmark_911_memorial_pools` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:National September 11 Memorial South Pool - 04.jpg by Oleg Yunakov, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2025-09-11 17:01:35, 1920x2560. [Commons page](https://commons.wikimedia.org/wiki/File:National_September_11_Memorial_South_Pool_-_04.jpg)

**Camera** — 40.711156, -74.012633 (NYC_TM -5293, 1241) at z 5.8 m NAVD88 | azimuth 314.3°, pitch +0.0° | 35 mm on 36 mm (42.2° horizontal, portrait) | 904x1206.

**Sun** — azimuth 254.4°, elevation 23.6° at 2025-09-11T17:01:35-04:00 (EXIF DateTimeOriginal); 702.3 W/m² direct normal, sky at strength 0.0387, Filmic, +4.25 stops.

**In the scene**, within 600.7 m of the camera and not all of it in frame — 4 building tiles (106,490 tris), 10 landmark models of which **1 can fall inside the 42.2° frame**, 22,728 pavement polygons (8,296 white, 3,994 plaza, 3,649 roadbed, 3,192 sidewalk, 2,585 curb, 454 crosswalk, 321 median, 142 yellow, 95 parking lot), 398 props of the 4,244 in range, 1,826 kit pieces, 88 vehicles and 438 people; 3,657,949 triangles. Ground mesh 67,010 triangles, 0 holes. 20 city surfaces are dressed from the shared photographic catalogue.

## Verdict — the camera stands on the right parapet and looks along it, but level, so the pool it names is a hole the frame cannot see into

**Both halves are taken from the same spot, and neither shows the item's subject.** The camera stands on the photograph's own EXIF GPS, **36.9 m** from the item's recorded viewpoint, and was not moved. That spot is on the parapet of the *South* Pool: the photograph's title says South Pool, and the render's foreground is the run of name panels at the pool's edge — the record's nearest built thing, `lm_b_wtc_site.233`, **0.7 m** from the lens at **-14.1°** yaw and **-27.2°** pitch. The item's named subject is the North Pool, **102.4 m** away behind the grove in the render and out of the photograph altogether. The pairing is South Pool parapet against South Pool parapet, and `distance_m 102.4` is not a distance to anything in the picture.

**The heading is the bearing to the North Pool, not a reading of the picture.** `meta.json` gives the photograph's azimuth by `camera_gps_to_subject` at "high" confidence — the confidence is the GPS's, the direction is arithmetic from that GPS to the North Pool's coordinate. So the two halves do not face quite the same way: in the photograph the parapet's far end vanishes a little left of the centre line, in the render it runs out of the left edge half-way down; the render is turned a few degrees right of the photograph. The item's recorded azimuth, **301.3°**, is **13.0°** further left again and belongs to its nominal viewpoint.

**The record declines to give the subject a height, and it is right to.** The 43-ray probe at the North Pool's coordinate lands **41 of 43** rays on built fabric and the highest thing it finds is **0.1 m** above the ground — `highest_built_z_m` **4.4** over `ground_z_m` **4.33**, the plaza deck at the lip of the opening. The nearest catalogue origin, `b_wtc_site` at **39.0 m** with **329.2 m** (3 World Trade Center's height), was correctly not used: J74 working as designed. But a pool is a *depth*, and a probe that measures upward reads a void as nothing. So `subject_visible` is **null** — no sightline was tested — and null means neither seen nor hidden. The consequence is in the picture: with nothing to tilt towards the axis is level, the parapet top stands a little below the eye and hides everything inside it. The photograph tilts steeply down over the same parapet and is made of what the level render cannot show.

**The light is metered, not a fault of the city.** The scene needed **+4.25** stops to read as a picture where the physical rule would have given **+0.88**; the record calls this under-lit and it is the number to read the render by (J83). Against the same middle-grey convention the render sits at **0.232** stops and the photograph at **-0.522**, so the render's median is the brighter: p50 **0.4972** against **0.3891**, ratio **1.278**. The p05 gap (**0.1422** against **0.1088**) is under the JPEG floor.

## What matches

* **The parapet is where the parapet is, and it runs the way it runs.** In both halves the pool's edge enters at the lower left and recedes diagonally into the middle distance, pool to its left, walkway and trees to its right.
* **The plaza is cut open over the pools.** The model's own report (`docs/verification/landmarks/b_wtc_site/REPORT.md`) builds both pool squares, their walls, water and central void, and the ring of name panels; the probe's **0.1 m** is the deck at the lip of an opening, not a filled-in plaza.
* **The grove is a grove of young trees on a grid**, seen in both halves beyond the parapet on the right and along the far side. The record places **282** prop trees, **281** of them a substituted species at mean scale **0.706**, on top of the landmark model's own oaks.
* **The light comes from the left and the shadows fall right** in both halves. Sun at **254.4°**, **23.6°**, camera facing **314.3°**: in the render the parapet tops and open plaza are sunlit (my PIL sample: the front panel's top about 51 per cent display luminance, the plaza at the right about 58) while the panels' front faces, looking back at the camera, are in shade at about 24; tree shadows streak right across the plaza. The photograph's crowd is lit from behind-left, shadows thrown right. About a tenth of the render's pixels exceed 0.7, all sky and glass tower in the top third; below the horizon under one per cent.
* **The furniture is the memorial's**: **54** benches and **37** street lamps in range; six or seven benches stand in a double row at the foot of the grove, centre frame just below the horizon.
* **The instant is the photograph's own**, to the second, on the anniversary — a **Thursday**, so a weekday crowd profile.
* **The World Trade Center site model is the one landmark that can fall inside the frame**, at **63.4 m** and **-0.1°** off axis; the pale wall down the render's right edge is its museum pavilion.

## What does not match

* **The pool itself is not in the render.** The photograph's upper left third is the pool: dark granite walls, water sheeting down them, a tower and the trees reflected. The render has the parapet top and, at the horizon, the far edge of the pool as a thin dark line; everything between is hidden by the near parapet at pitch **+0.0°**.
* **The parapet is a flat tan slab where the photograph is black bronze with incised names.** The model gives the panels a `MEMORIAL_NAMES` slot for the engine to drive; in this render the slot has no texture and the panels read as pale concrete-coloured blocks with dark seams, lit on top. No names, no roses, no flags, no reflections.
* **The crowd is absent.** The photograph has nine figures in its right third at full size and a continuous line of people along the far parapet, on the order of a hundred. The render has none: **438** pedestrians were placed but no simulated agent stands within **60 m** of the camera, and **412** were dropped for not being on a walkable surface. The plaza is the landmark model's own ground, **33,039.3 m²**, and the record does not say whether that counts as walkable.
* **The render is turned right of the photograph**, so the museum pavilion fills its right edge where the photograph's is walkway, people and trees.
* **Chroma is two thirds of the photograph's**: **0.0768** against **0.1162**, ratio **0.661**. The photograph's colour is the yellow and red of the roses, the flags and the bronze; the render's is the green of the canopy against grey.
* **The lighting, as stops**: development **+4.25** (physical rule **+0.88**), exposure offset **0.232** against the photograph's **-0.522**; mean **0.4447** against **0.4068**, ratio **1.093**. The render is developed brighter than the photograph.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the pool itself is not in the render | the subject is a depth; the height probe measures upward, finds the deck at 0.1 m, declares nothing to tilt to and leaves the axis level where the photograph tilts down | verification (the J72/J74 rule applied to a void) |
| a flat tan slab where the photograph is bronze with names | the `MEMORIAL_NAMES` slot is an engine material; the verification renderer has no texture for it | material |
| the crowd is absent | 438 pedestrians placed, none within 60 m; 412 dropped as not on a walkable surface, and the plaza is the landmark's own ground rather than a pavement polygon | verification |
| render turned to the right of the photograph; pavilion at the right edge | the heading is `camera_gps_to_subject` to the North Pool 102.4 m away, not derived from the image; the item names the other pool from the one photographed | reference |
| chroma at 0.661 of the photograph | the photograph's colour is roses, flags and bronze, none of which the model carries; the render is grey plaza, tan slab and green canopy | material |
| development +4.25 stops, exposure offset 0.232 against -0.522 | metered development (**DEVIATIONS J83**); a low Sun behind-left of the axis, sky at strength 0.0387 | — (not a gap) |
