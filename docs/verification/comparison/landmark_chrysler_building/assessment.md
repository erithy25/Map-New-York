# Chrysler Building

`landmark_chrysler_building` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Chrysler Building October 2022 001.jpg by Kidfly182, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2022-10-08 14:36:16, 1920x1440. [Commons page](https://commons.wikimedia.org/wiki/File:Chrysler_Building_October_2022_001.jpg) — the view direction is derived from the image at **high** confidence. It is the crown from Lexington Avenue looking straight up: the stainless sunburst, the triangular windows, the eagles at the 61st-floor corners and the spire, against a deep October blue.

**Camera** — 40.75, -73.9767 (NYC_TM -2242, 5626) at z 14.7 m NAVD88 | azimuth 29.6°, pitch +21.0° | 18 mm on 36 mm (90.0° horizontal, 74° vertical) | 1208x906. The camera stands on **the item's recorded viewpoint** rather than the photograph's own GPS, and the record says why: that position is 137 m away and *"the eye point there is inside `t_-3_5_roof_membrane` (a ray straight up from the eye point hits its roof)"*. From the recorded point the walk then moved **73.8 m** — boxed in with the azimuth closed off **13 m** ahead against the **80.0 m** this frame needs — **onto the nearest crosswalk**, under the rule `open air only, ranked on how much of the subject it sees`. The note is worth quoting whole: *"No point within 80 m had 80 m of open air along the view azimuth with nothing built inside 8 m of the lens, so the frame is closed off 96 m ahead and nothing built stands within 20 m of the lens"*. The nearest simulated body is `agent_ped_2957.5` **11.2 m** away. The lens sits at the **18 mm floor** and the record declares the cost: *"held at the 18 mm floor, so the top of the subject is still cut off"* and *"the verticals converge, so this frame is not comparable with the photograph on proportion"*.

**Sun** — azimuth 215.8°, elevation 36.5° at 2022-10-08T14:36:16−04:00, from the photograph's own **EXIF DateTimeOriginal**; 820.0 W/m² direct normal, sky at strength 0.0343, Filmic, **+4.17 stops**. The record declares it: *"under-lit: the scene needed +4.17 stops to read as a picture, more than the 4 a photographer recovers hand-held"*. The linear median is **0.009966** against the 0.18 target, so the development is **4.175 stops**, unclamped. The physical rule would have given **0.24**.

**In the scene** — 4,500,174 triangles: 4 building tiles (197,492 tris), 7 landmark models of which 3 fall inside the 90.0° cone, 28,913 pavement polygons, 1,575 props, 6,106 kit pieces, 14 park-ground meshes, **2 tiles of structures (2,920 tris)**, 80 vehicles and 405 people.

## Verdict — the frame does not contain the Chrysler Building, and the walk knew that when it chose the spot

**`subject_visible: false`. `subject_visible_fraction: 0.0`. `subject_rays_on_subject: 0`.** Of 13 rays, **1 is clear** and **12 stop at 30.3 m** on `t_-3_5_metal_panel` — a joined tile mesh standing beside the crosswalk the camera was moved to. The one clear ray meets nothing at all out to 593 m. The record's own note is blunt about the shape of the failure: *"nothing stands within 25 m of the subject's recorded coordinate on any clear ray: the clear rays meet nothing at all out to 593 m. The line is open and the subject is not on it, which is a fault in the item's coordinate or in the model, not in the camera."*

**On that last clause the record is wrong, and its own height probe proves it.** The probe cast 43 rays and **all 43 landed on built fabric**, measuring **281.94 m** above a ground of 10.06 m on `lm_chrysler.2`, with a plan extent of 42.4 by 39.3 m and the catalogue's own origin 12.4 m away carrying **318.9 m** — the spire tip. So the Chrysler Building is present, is 282 m to the crown at the item's coordinate, and agrees with its catalogue once the 37 m spire is allowed for. The model is not the fault and the coordinate is not the fault. **The camera is**, and the camera is where the clearance walk put it.

**The walk recorded the zero before it moved.** `clearance.subject_sightline_at_choice` on this record reads `subject_rays: 13, subject_rays_on_subject: 0, subject_visible: false, subject_visible_fraction: 0.0`. The walk scored candidates on the subject's own sightline, as J79 requires, found that its best candidate saw **none** of the subject, and displaced the camera **73.8 m** to it anyway. Measured across the pass, **7 of the 59 records that carry a chosen-candidate sightline chose a candidate already measuring 0.0**, and a further 11 chose one measuring 0.077 — one ray of thirteen. The seven zeros are the Chrysler Building, the **Empire State Building**, the **MetLife Building**, **40 Wall Street**, the **Bank of America Tower**, **111 West 57th Street** and the Holland Tunnel portal, and **six of the seven are blocked by a joined tile mesh**. The walk has no floor: nothing in it says that a displacement which cannot see the subject is worse than not moving.

**So what the right half of this sheet is a picture of is two tile shells.** The left one carries the render's second measured fault, and it is the one a reader will notice first: a regular grid of pale boxes standing **proud** of a flat wall. Those are kit window pieces on a shell with no openings cut into it (J51), and the arithmetic behind them is stark. **80,199 kit pieces stand in range and 6,106 were drawn** against a 1,220,631-triangle budget — seven and a half per cent — of which **6,023 are windows**, 50 storefronts, 8 doors, 8 parapets, 4 items of rooftop plant, 3 pilasters, 3 bulkheads, **1 cornice and 1 string course**. On the sheet for the finest Art Deco ornament in the world the render placed one cornice.

**And the tone is two stops apart before the scene is compared.** The photograph sits **2.054 stops below** the grey convention — a deliberately dark exposure holding that October sky — and the render is metered to **0.234 above** it, a **2.288-stop** gap, the largest read this round. p50 comes out at **2.16×** and mean at 1.571×. Chroma is **0.415**: the photograph's saturated cobalt sky against a procedural Nishita dome at strength 0.0343.

## What matches

* **The model is right and the probe proves it.** 43 of 43 rays on fabric, **281.94 m** above its own ground, against a catalogued 318.9 m to the spire tip — the difference is the spire, and the probe measures the thing rather than the entry (J74).
* **The plan extent is a real object's box**, 42.4 by 39.3 m, `is_tile_mesh: false`.
* **The Sun is the real minute** of a real Saturday afternoon, from EXIF, and the crowd clock agrees: **2022-10-08 was a Saturday** and the simulation used its Saturday density profile.
* **The record declares every one of its own failures** before this assessment does: the lens at its floor, the converging verticals, the under-lit development, the zero fraction, the clear rays meeting nothing, and the walk's own score at the moment of choice. Nothing here had to be discovered by reading the picture.
* **The avenue is paved and marked**: 28,913 polygons with **14,491 white markings**, 4,866 roadbed, 4,504 sidewalk, 3,483 curb, 761 crosswalk, 411 plaza and 104 yellow markings, and **0 dropped**.
* **The block is furnished for Midtown East**: **603 Citi Bike dock units**, 159 cooling towers, 155 street lamps, 137 manholes, 77 hydrants, 29 vent grates, 28 waste baskets, **24 LinkNYC kiosks**, 17 bus-stop signs, 17 subway entrances, 15 flagpoles, 11 bike racks and 9 steam vents.
* **Seventeen trees are drawn from modelled branches** within 120 m, and the October date is correctly outside the leaf-off window, so the canopy is in leaf.
* **The frustum report is right for once**, because all three landmarks it names are real neighbours at real bearings: the Chrysler at 149.1 m and 13.1° off axis, Grand Central at 237.1 m and −43.6°, the MetLife Building at 318.4 m and −30.9°.
* **The frame passes its luminance gate without a retry**: mean 0.5103, sd 0.2273, `usable: true`.

## What does not match

* **The subject is absent.** Zero of thirteen rays reach it; the published fraction is 0.0. There is no comparison to make between the two halves of this sheet.
* **The camera was moved 73.8 m to a point the walk itself scored at 0.0.**
* **Twelve of thirteen rays stop 30.3 m from the lens on a joined tile mesh**, which is also what fills the frame.
* **80,199 kit pieces in range, 6,106 drawn, 1 cornice.** The Chrysler Building's neighbours on Lexington are brick and terracotta with heavy cornices and string courses, and the budget spent everything it had on windows.
* **The windows stand proud of the shells.** No opening is cut into a building shell anywhere in this build (J51), so a window is a box on a wall, and at this focal length and this angle the grid of boxes is the dominant texture of the render's left half.
* **The crown is not modelled in this frame because the building is not in this frame** — the sunburst arches, the triangular windows, the eagles and the spire are in `lm_chrysler` and no ray reached any of them.
* **The verticals converge and the photograph's do not.** 18 mm at +21.0° of pitch against a photograph made to hold a 319 m tower upright. The record says the two frames are not comparable on proportion, and they are not.
* **The development is past the under-lit threshold** at 4.175 stops on a linear median of 0.009966, so the render's tone is amplification rather than scene light.
* **The exposure gap is 2.288 stops**, the largest read this round, giving a p50 ratio of **2.16×** (J83).
* **Chroma 0.415** against a cobalt sky the procedural dome cannot make.
* **Structures are almost absent**: 2 tiles imported for **2,920 triangles** with 2 more having no file, over the Grand Central throat — one of the densest pieces of underground and elevated rail structure in the country.
* **Two thirds of the props in range were dropped.** 1,575 drawn of 3,860 at a 1,241,097-triangle budget, **2,046 dropped**, including **1,404 tree rows**; 5 impostor cards dropped as opaque.
* **Twenty-eight props across five kinds had no asset**: 13 vending machine, 5 artwork, 5 drinking fountain, 3 misc structure, 2 passenger-information sign.
* **Eleven of the eighty vehicles are green boro taxis** at Lexington and 40th, inside the zone where a Street Hail Livery may not take a hail; 16 are yellow (J105).
* **405 people where the table asked 3,986.** 797 vehicles and 3,986 people were wanted over the simulated ring; 905 and 2,999 were simulated and **3,416 dropped** — 1,418 pedestrians outside the radius, 806 at the 1,125,000-triangle agent budget, 508 vehicles outside the radius, 284 at the budget, 232 in the carriageway without crossing, 136 not on a walkable surface, 25 riderless bodies and 7 off the carriageway.
* **Nearly every agent is at the coarsest LOD**: 79 of 80 vehicles and 398 of 405 people at LOD2.
* **The park ground away from the lens sits under the terrain**: 0.2594 of 1,565 samples beyond 400 m, worst case −5.548 m. There are **0 samples within 150 m** and only 17 in the mid band, so the near field is untested.
* **No cloud.** The photograph's sky is a deep unbroken October blue with one small cloud; the render's is a Nishita dome.

## Measured for this assessment

| figure | where it comes from |
|---|---|
| 7 of the 59 records carrying a chosen-candidate sightline chose a candidate already measuring 0.0, and 11 more chose 0.077 | counted over every record carrying `clearance.subject_sightline_at_choice`; the seven zeros are 111 West 57th (moved 76.0 m), this sheet (73.8 m), the MetLife Building (62.2 m), 40 Wall Street (52.2 m), the Holland Tunnel portal (44.6 m), the Empire State Building (16.0 m) and the Bank of America Tower (10.0 m) |
| six of those seven are blocked by a joined tile mesh | the `subject_blocked_by` field of each of those seven chosen-candidate sightlines: five `t_*` material meshes, one park-ground tile mesh, and one tree |
| the 37 m difference between the probe and the catalogue is the spire | the recorded probe height of 281.94 m against the recorded catalogue height of 318.9 m for the `chrysler` entry 12.4 m away |
| 2022-10-08 was a Saturday | the record's own `crowd_clock`, which reports day type Saturday for that date |
| the largest exposure gap read this round | this sheet's 2.288 stops against the thirty-three sheets read in the preceding rounds |
| a window is a box on a wall | no opening is cut into any building shell in this build; the kit places window pieces proud of the shell surface (DEVIATIONS J51, measured at +48 GB to close and therefore open) |

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the subject is absent from the frame | the clearance walk moved the camera 73.8 m to a candidate whose own recorded sightline was already 0.0, because nothing in the walk rejects a displacement that cannot see the subject. The walk's note says no point within 80 m satisfied its clearance test, and its answer to that was to move anyway rather than to hold the recorded viewpoint and say so (J79, J100) | **verification — open, and the same fault puts the Empire State Building, the MetLife Building, 40 Wall Street and the Bank of America Tower in the same condition** |
| twelve rays stop 30.3 m away on a tile mesh | every surface of one material in a tile is joined into one object, so a single mesh can fill the frame and be reported as one blocker (J94) | verification — open |
| the record blames the coordinate and the model | the sightline's own note concludes that the line is open and the subject is not on it; the height probe in the same record found the subject with 43 of 43 rays. The two halves of the record contradict each other and nothing reconciles them | **verification — open; a record that mis-attributes its own failure is worse than one that reports it plainly** |
| the kit withheld — 6,106 drawn of 80,199 in range — and one cornice drawn | the kit triangle budget at 1,220,631 triangles, spent windows-first, on the block whose interest is its ornament | **performance** |
| the windows stand proud of the shells | no window, door or storefront opening is cut into any building shell; cutting them was measured at +48 GB, which this container cannot hold (J51) | **declared decision — recorded with its number** |
| the verticals converge | 18 mm is the widest lens the build will use, and a 319 m tower 137 m away does not fit a level frame; the record declares the two halves incomparable on proportion | verification — declared |
| 4.175 stops, past the under-lit threshold | a Midtown canyon at 36.5 deg of Sun elevation with the beam behind the camera, and a procedural sky at strength 0.0343 as the only fill; there is no measured sky luminance (J83) | **verification — declared, and the number is published with the frame** |
| 2.288 stops of exposure difference, p50 2.16x | the photograph was developed 2.054 stops under the grey convention and the render is metered to it (J83) | reference — declared, and correct |
| chroma 0.415 | a procedural Nishita dome against a saturated October sky, and flat authored surface colours (J66) | data — declared |
| 2,920 triangles of structures over the Grand Central throat | two of the four tiles in range have no structures file, and the two that do carry almost nothing (B13 remainder) | **data — open** |
| 2,046 props dropped, 1,404 of them trees | the props triangle budget at 1,241,097 triangles | performance |
| 28 props across 5 kinds unmapped | no asset exists for those kinds | data |
| 11 boro taxis inside the exclusion zone | the runtime splits the taxi share 70/30 yellow to green everywhere with no geography (J105) | data — open |
| 405 people where the table asked 3,986 | the 1,125,000-triangle agent budget plus the placement rules | performance + verification |
| park ground under the terrain beyond 400 m | the park surfaces were draped on the fine grid and the scene's terrain coarsens to 40.0 m (J40, J96) | verification — declared |
| no cloud | nothing in this build reads a historical sky | reference — no source exists |
