# 53W53 (MoMA Tower)

`landmark_53w53` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:53W53 February 2023 001.jpg by Kidfly182, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2023-02-23 12:49:28, 1280x1707. [Commons page](https://commons.wikimedia.org/wiki/File:53W53_February_2023_001.jpg)

**Camera** — 40.761214, -73.977981 (NYC_TM -2363, 6798) at z 21.7 m NAVD88 | azimuth 329.4°, pitch +39.9° | 18 mm on 36 mm (73.7° horizontal, portrait) | 904x1206.

**Sun** — azimuth 192.7°, elevation 38.7° at 2023-02-23T12:49:28-05:00 (EXIF DateTimeOriginal); 833.7 W/m² direct normal, sky at strength 0.0338, Filmic, +6.00 stops.

**Subject** — 53W53 (MoMA Tower) at 58.4 m.

**In the scene**, within 597.2 m of the camera and not all of it in frame — 4 building tiles (222,112 tris), 10 landmark models of which **2 can fall inside the 73.7° frame**, 23,668 pavement polygons (8,698 white, 5,828 sidewalk, 4,074 roadbed, 3,151 curb, 1,012 plaza, 434 crosswalk, 432 median, 22 yellow, 17 parking lot), 1165 props of the 2,456 in range, 5,916 kit pieces, 73 vehicles and 347 people; 4,500,120 triangles. Ground mesh 83,126 triangles, 0 holes. 19 city surfaces are dressed from the shared photographic catalogue.


## Verdict — the tower is in the frame, measured and recognisable; the frame is a tilted wide-angle that the photograph is not, and the exposure was held at its clamp

**This is the same building from close to the same spot, and the two frames are not the same picture.** The photograph is a phone held almost vertical at the foot of 53W53: the tower fills it top to bottom, a glass prism tapering to a point with the diagrid's diagonals crossing a fine mullion grid, a plume of steam drifting across its lower half, a slice of a neighbouring glass facade in the bottom right corner, and no street at all. The render stands on the photograph's own EXIF GPS, **58.4 m** from the subject, on the traffic surface of West 53rd Street, and to get a **318 m** tower into a frame from that distance it went to the **18 mm** floor and then tilted **+39.9°**. The record says so itself: *the verticals converge, so this frame is not comparable with the photograph on proportion — it is here to show the subject at all*. That is the I18 case with the tilt applied and declared: the tower stands centred between a red-brick block on the left and a dark curtain wall on the right, with bare trees, taxis and pedestrians along the bottom and a wedge of clear sky the photograph has no counterpart for. The instant is the photograph's own, to the second; the heading is the bearing from the photograph's GPS to the subject.

**The building the record measured is the building.** The height probe lands **43 of 43** rays on built fabric at the subject's coordinate and reads **318.34 m** above the ground there, off `lm_c_billionaires_row.33` — a piece of the West 57th Street corridor model that happens to stand on West 53rd. That is within a couple of metres of the tower's published height, which the record does not carry, so the agreement is not this sheet's to claim. The nearest *catalogue* origin is `moma` at **62.8 m**, publishing **74.7 m**: the museum, not the tower, and a J74 measurement off the fabric rather than off that origin is what kept the probe honest. The sightline puts **6 of 13** rays on the subject, **3** on the subject's own fabric nearer than the coordinate (`lm_c_billionaires_row.35` at **52.1 m**), **3** into nothing, and names `t_-3_6_red_brick` at **8.0 m** as the blocker — the red-brick block filling the left of the frame. `subject_visible: true` on the J78 rule, fraction **0.462**; the picture agrees with the fraction rather than the boolean — half of a fan **318 m** tall aimed from **58 m** away is bound to leave the frame or meet the neighbours.

**The lighting is the clamp, not the city.** The metered development wanted **+7.53** stops and was held at **+6.00**; the physical rule alone would have given **+0.16**. The linear median is **0.000974** against a target of **0.18**. The record's own note reads: *a scene this far from a photographable level is not developed into a picture of one*. In frame_stats the render's median sits **-1.229** stops below the middle-grey convention and the photograph's **+0.742** above it, a difference of **-1.971** stops. A frame that needs more than six stops to read at all is short of light at the source (J83); the Sun is behind the camera at **38.7°** elevation with **833.7 W/m²** direct normal, and the shade is the canyon — three tall walls and a lens pointed up the gap between them. Do not read the render's darker street as a fact about West 53rd Street.

## What matches
* **The massing and the diagrid.** A single slender tower tapering to a point, with structural diagonals crossing a rectangular glazing grid on the face that turns toward the camera; the crossing pattern in the render reads as the same family of structure as the photograph's, at a comparable angle of taper. The probe's **38.0 m** by **31.4 m** plan extent is a tower footprint, not a corridor block.
* **The height.** **318.34 m** above ground at the coordinate, all **43** rays on fabric. The tower is present and it is the tallest thing in either frame.
* **The neighbour in the bottom right.** The photograph's corner shows a glass facade with horizontal floor bands; the render's right third is a dark curtain wall with the same emphatic horizontal spandrels, at a similar close range.
* **The bright end of the histogram.** Render p95 **0.92** against the photograph's **0.9116**: the sky in the render and the overcast sky in the photograph both reach the top of the scale.
* **Season.** The **213** trees are scaled and the callery pear **6.6 m** from the lens is bare, as a February street should be.

## What does not match
* **The framing.** Photograph: near-vertical, tower only. Render: **73.7°** horizontal, **90°** vertical at **18 mm**, tilted **+39.9°**, with a street, **73** vehicles and **347** people in the scene and a foreground of taxis, a black car, a green boro taxi and a pedestrian at the frame's foot (the nearest agent the record names is **17.1 m** away). Both sets of verticals converge, from different angles and lenses, and no proportion can be compared between them.
* **The crown is an open lattice.** Above roughly the upper third the render's tower turns into a white unglazed frame — a scaffold-like cage with sky through it — where the photograph's glass runs unbroken to the apex.
* **The weather.** The photograph is overcast: white sky, no cast shadows, flat blue-grey glass, a steam plume. The render is a clear day at **833.7 W/m²** direct normal, with the sunlit south flank of the tower and hard shadows across the neighbours. The scene places **2** steam vents; no plume.
* **The tone level.** Render p50 **0.3071** against **0.5847**, mean **0.3952** against **0.6112**, ratio **0.525** at the median: the render's development was held at **+6.00** stops of a needed **+7.53**. Render p05 **0.0389** against the photograph's **0.1933** is well above the JPEG floor and is the render's shadow depth, the deep shade of the canyon at the clamp.
* **Chroma.** **0.0554** against **0.0778**, ratio **0.712**: the render is greyer than a photograph that is itself close to monochrome.
* **The left-hand block.** A red-brick wall with window boxes projecting from it like air-conditioning cabinets fills the left of the render; nothing in the photograph corresponds, because the photograph does not look there.
* **The tower's base.** The render's tower stands on a tan brick plinth with a dark band; the real building meets the street in glass.
* **A cluster of four dark squares hangs in open sky** to the left of the tower at mid-height, with no pole, arm or facade behind it.

## Cause of each gap
| gap | cause | class |
|---|---|---|
| the framing: wide, tilted, street in frame | a **318 m** subject **58 m** away cannot be contained by any level lens; the rule widens to the **18 mm** floor and then tilts, and declares the tilt (**I18**, tilt now applied) | stated choice |
| the crown drawn as an open lattice | the corridor model's upper section carries the diagrid members without glazing panels, or its glazing material renders as open; the record has no per-part material entry to say which | geometry |
| clear sky and hard shadows against an overcast photograph | the simulation has one sky, driven by the Sun's position and irradiance; there is no cloud-cover input, and the steam-vent props place a grate, not a plume | data |
| tone level: median ratio **0.525**, development held at **+6.00** of **+7.53** stops | metered development at the clamp (**DEVIATIONS J83**); the frame's linear median is **0.000974** because the lens looks up a canyon of three tall walls with the Sun behind the camera | verification |
| chroma ratio **0.712** | one material family per facade class and the clamp's compression of the little colour there is (**DEVIATIONS J66**) | material |
| the red-brick block with projecting window boxes | tile mesh `t_-3_6_red_brick` at **8.0 m**, dressed with kit windows whose geometry stands proud of the wall | material |
| a brick plinth under a glass tower | the model's base is not the building's glass base; nothing in the record describes the ground floor | geometry |
| four dark squares floating in the sky | not identifiable from the record; a kit or prop piece with no visible support | verification |
