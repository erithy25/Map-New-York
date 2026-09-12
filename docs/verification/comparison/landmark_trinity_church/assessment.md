# Trinity Church

`landmark_trinity_church` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Trinity Church Wall St (6217334552).jpg by Tony Hisgett from Birmingham, UK, CC BY 2.0 (https://creativecommons.org/licenses/by/2.0), taken 2011-09-16 14:43, 1920x3089. [Commons page](https://commons.wikimedia.org/wiki/File:Trinity_Church_Wall_St_(6217334552).jpg) — the view direction is derived from the image at **high** confidence. It is the classic portrait frame: Wall Street's canyon closing on the spire, the cross at the top of it, the great west window and portal below, and several hundred people filling the pavement in the foreground.

**Camera** — 40.706573, -74.009812 (NYC_TM -5054, 733) at z 9.4 m NAVD88 | azimuth 311.3°, pitch 0.0° | 35 mm on 36 mm (35.4° horizontal, 54.4° vertical, **portrait**) | 824x1326. The camera stands on **this photograph's own EXIF GPS**, **27.6 m** from the item's recorded viewpoint, and was moved **1.5 m to the right** under the rule `sidestep around a prop at the lens`, because *"the recorded viewpoint has `prop_lamp_cobra_davit_0` 4.1 m from the lens on the line to the subject, which a photographer steps around"*. The walk scored candidates on the subject's own sightline and improved it from **0.154** at the recorded point to **0.231** — and the same lamp still stands **3.3 m** from the lens. The view azimuth is then clear for **150.0 m** and no simulated agent stands within 60 m. The axis is level: *"the subject is 257 m away; anything that far is photographed with a level camera"*. The ground under the lens reads 7.817 m NAVD88, the 10th percentile of 113 samples within 12.0 m, range 7.71 to 8.22 m.

**Sun** — azimuth 220.9°, elevation 44.3° at 2011-09-16T14:43:00−04:00, from the photograph's own **EXIF DateTimeOriginal**; 863.6 W/m² direct normal, sky at strength 0.0327, Filmic, **+6.00 stops**. The record declares the clamp: *"the frame wanted +7.11 stops and was held at +6.00: a scene this far from a photographable level is not developed into a picture of one"*. The linear median is **0.001302** against the 0.18 target — about one part in a hundred and forty — and `stops_unclamped` is **7.111**. The physical rule would have given **0.0**. A 44° Sun at azimuth 220.9° behind a camera looking at 311.3° puts the whole of Wall Street's canyon in shade.

**In the scene** — 4,500,233 triangles: 6 building tiles (112,630 tris), 16 landmark models of which 6 fall inside the 35.4° cone, 28,499 pavement polygons, 957 props, 3,547 kit pieces, 24 park-ground meshes, **5 tiles of structures (112,968 tris)**, 58 vehicles and 297 people.

## Verdict — the spire is in the model at 85.60 m and the probe measured 25.16 m of nave, so the sightline fan is 2.71 degrees tall and never looks at it

**Both halves of this sheet are about a spire, and the instrument that decides what this sheet measures never pointed at one.** The height probe cast 43 rays, 32 landed on fabric, and the answer was **25.16 m** above a ground of 11.28 m on `lm_trinity_church.3`, whose plan extent the record gives as **69.2 by 58.8 m** — the whole churchyard block. The catalogue entry 12.6 m away carries **85.6 m**, and J74's rule preferred the measurement over the entry, as it is written to.

**Here that rule gave the worse answer, and the file shows why.** Measured off `blender_out/landmarks/trinity_church.glb`, the church is six objects: `base` 116 triangles on 69.2 by 58.8 m up to 12.50 m, `aisle_detail` 2,646 triangles to 15.10 m, `nave` 28 triangles to 20.50 m, `nave_detail` 575 triangles on the same 69.2 by 58.8 m box to 27.50 m, and **`tower` — 619 triangles, 12.1 m square, rising to 85.60 m**. The spire is modelled, to the published height, as its own object. The ray at the item's coordinate met the nave instead, and the catalogue's 85.6 m turns out to be the tower's own figure to the decimetre. So the entry was right, the measurement was wrong, and the rule that exists to stop a catalogue inventing a height has here thrown away the only correct number in the record.

**The consequence runs straight into the sightline.** `subject_fan_tall_m` is **24.4 m** and `subject_fan_v_half_angle_deg` is **2.71°**. At 257 m a 2.71° half-angle reaches 12 m above and below the aim point, which sits **12.2 m** above the church's ground. So the fan tests a band from the pavement to roughly the aisle roof and stops there. Trinity's tower rises to 85.60 m, which at 257 m subtends about 17° — six times the fan's half-angle. **The published visible fraction of 0.231 is a measurement of the church's lower walls.** J94's proposed repair — take the tallest member whose footprint contains the coordinate — would have found the tower, because its 12.1 m square footprint contains that coordinate and its top is the 85.60 m the catalogue already knew.

**The frame is the deepest under-exposure in the pass, and the clamp accidentally matched the photograph.** A linear median of **0.001302** wanted **7.111 stops** and was held at 6.00, so the render is published **0.803 stops below** the grey convention — one of the few frames in the pass that sits under it rather than on it. The reference photograph, a dark canyon shot, sits **0.589 stops below**. The gap is therefore **−0.214 stops**, and the measured agreement is close across the board: mean **1.075×**, p50 **0.931×**, chroma **0.966×**. That is not the development succeeding. It is a clamp landing near a dark photograph by coincidence, and the record says so in its own note.

**And a street lamp 3.3 m from the lens still takes eight of thirteen rays.** The walk saw the lamp, sidestepped 1.5 m, and doubled the fraction from 0.154 to 0.231. It could not do better, because `prop_lamp_cobra_davit_0` stands on the Wall Street kerb between the lens and the church and the walk's clearance probe does not weigh props at all (J88).

## What matches

* **The spire is modelled to its published height** — 85.60 m in a 619-triangle tower object 12.1 m square — and it is visible in the render as a pale tapering spire closing the canyon, which is the photograph's composition.
* **The lens is in portrait**, 35.4° by 54.4°, matching a 1920 by 3089 reference: the one sheet read this round whose frame shape follows its photograph's.
* **The frustum report is genuinely useful here**, naming six real Wall Street neighbours at real bearings: 40 Wall Street at 50.4 m, Federal Hall at 91.8 m, the New York Stock Exchange at 129.7 m, One Wall Street at 180.6 m, the Equitable Building at 192.9 m and Trinity Church at 262.0 m, **2.4° off axis**.
* **The tonal agreement is the closest read this round** on three of four measures: mean 1.075×, p50 0.931×, chroma 0.966×, with a 0.214-stop exposure gap.
* **The walk did the right thing and recorded it.** It detected a prop on the sight line, moved across the axis rather than away, scored the result, and published both the before and after fractions.
* **Structures are substantial**: 5 tiles imported for **112,968 triangles** under the densest subway junction in Lower Manhattan.
* **The street is paved and marked**: 28,499 polygons with **13,660 white markings**, 4,842 sidewalk, 4,071 roadbed, 4,021 curb, 778 crosswalk, 625 plaza and 324 yellow markings, and **0 dropped**.
* **The block is furnished**: 291 Citi Bike dock units, 105 manholes, 101 street lamps, 87 cooling towers, 70 hydrants, 53 benches, 32 waste baskets, 23 subway entrances, 23 vent grates, 17 bike racks, 6 newsstands and 3 flagpoles.
* **The Sun is the real minute** of a real Friday, from EXIF, and the crowd clock's weekday profile is right for 16 September 2011.
* **The frame passes its gate** at mean 0.4145, sd 0.1971, `usable: true` — even after a 6-stop lift.

## What does not match

* **The measured height is 25.16 m for an 85.60 m subject**, and the fan built from it is 2.71° tall, so this sheet's headline number describes the church's lower walls.
* **Eight of thirteen rays stop 3.4 m from the lens on a street lamp**, after the walk had already moved to get around it.
* **The development was clamped** at 6.00 stops against a wanted 7.111 — the record's own words are that a scene this far from a photographable level is not developed into a picture of one. The close tonal agreement that follows is coincidence, not fidelity.
* **The church's Gothic is a massing.** 3,984 triangles for the whole building: 619 of them the tower and spire, 2,646 the aisle detail, 575 the nave detail. There is no tracery in the west window, no crockets on the spire, no pinnacles, no cross.
* **Nine in ten kit pieces were withheld.** 3,547 drawn of **32,261** in range against a **810,375**-triangle budget — the smallest kit budget read this round — of which 3,256 are windows and 191 window accessories against **1 cornice and 1 string course**. Wall Street's canyon is cornices.
* **Five in six props in range were dropped.** 957 drawn of 5,828 at a 1,020,484-triangle budget, **4,666 dropped**, including **4,320 tree rows**; only **12 trees are drawn from modelled branches** and 129 are cards, 114 of the 141 a substituted species (J108).
* **The George Washington statue is absent**, and so is every other monument here: 23 props across four kinds had no asset — **10 artwork, 8 memorial**, 3 drinking fountain, 2 vending machine. The photograph's right foreground is that statue on its plinth at Federal Hall.
* **The crowd is not there.** The photograph's foreground is several hundred people on the pavement; the render's is an empty carriageway with one car. **297 people** are drawn where the density table asked for **5,044** — the largest ask on any sheet read this round — with 750 vehicles and 3,000 people simulated and **3,394 dropped**: 1,447 pedestrians outside the radius, 585 at the 1,125,000-triangle agent budget, 436 vehicles outside the radius, **395 in the carriageway without crossing**, **246 not on a walkable surface**, 231 vehicles at the budget, **27 inside buildings**, 15 riderless bodies, 7 off the carriageway and 6 above the observer.
* **Only four yellow cabs, and four green boro taxis, on Wall Street** at 14:43 on a Friday — inside the zone where a Street Hail Livery may not take a hail (J105).
* **Nearly half the park ground in the middle distance sits under the terrain**: 0.4877 of 365 samples in the 150 to 400 m band, worst case −1.667 m. There are **0 samples within 150 m**, so the near field is untested.
* **53,345 faces were cut for landmark ground**, because sixteen landmark models stand inside this radius.
* **The flags are absent.** Three flagpoles are placed; the photograph's blue NYSC banner, the Stars and Stripes and the church's own flag are not a class this build models.
* **No cloud.** The photograph's strip of sky is a hazy September white; the render's is a Nishita dome at strength 0.0327.

## Measured for this assessment

| figure | where it comes from |
|---|---|
| the church is six objects totalling 3,984 triangles: base 116 to 12.50 m, aisle_detail 2,646 to 15.10 m, nave 28 to 20.50 m, nave_detail 575 to 27.50 m, tower 619 to 85.60 m, and an LOD1 of 144 | the accessor `count` and `min`/`max` of every primitive of every node of `blender_out/landmarks/trinity_church.glb`, read from the binary glTF header |
| the tower is 12.1 m square and its footprint contains the item's coordinate | the same accessor bounds for `trinity_church_tower`, against the recorded subject distance and the 69.2 by 58.8 m extent the probe reported |
| the catalogue's 85.6 m is the tower's own height to the decimetre | the recorded `nearest_catalogue_origin.height_m` of 85.6 against the measured tower top of 85.60 m |
| the spire subtends about 17 degrees at this distance, against the fan's 2.71 | the tower's 85.60 m at the recorded subject distance of 257.2 m |
| a linear median of 0.001302 is about one part in a hundred and forty of the target | the recorded `median_linear` against the recorded `target_linear` of 0.18 |
| the closest tonal agreement and the smallest kit budget read this round | this sheet's four `render_over_reference` ratios and its 810,375-triangle kit budget, against the thirty-five sheets read in the preceding rounds |
| the materials are brownstone, slate, dark glass, dark wood and green copper | the `materials` array of the same glb |

## Cause of each gap

| gap | cause | class |
|---|---|---|
| 25.16 m measured for an 85.60 m subject | the height probe takes the object standing at the coordinate, and at the centre of Trinity's churchyard that is the nave, whose bounding box is the whole 69.2 by 58.8 m block. The tower is a separate object and was never measured, so J74's rule -- prefer the measurement to the entry -- discarded the only correct figure in the record (J74, J94) | **verification — open, and this is the clearest case in the pass for J94's tallest-member repair: the tower's own footprint contains the coordinate** |
| the fan is 2.71 degrees tall | it is sized from that 24.4 m measurement rather than from the subject's real 85.60 m, so the published 0.231 describes the lower walls (J78, J94) | **verification — open** |
| eight rays stop 3.4 m away on a lamp | the walk's clearance probe tests built fabric and a lamp mast is a prop, so it cannot be scored around; the sidestep rule moved 1.5 m and could do no better (J88) | verification — open |
| the development was clamped at 6.00 stops | a canyon in full shade at a linear median of 0.001302, with a procedural sky at strength 0.0327 as the only fill and no measured sky luminance or indirect bounce budget (J83) | **verification — declared, and the clamp is published with the frame** |
| no tracery, crockets, pinnacles or cross | the church is a massing of six objects; Gothic ornament at this scale is not derivable from a footprint and a height, and no scan exists under an open licence | **geometry — declared by its triangle count** |
| the kit withheld — 3,547 drawn of 32,261 in range — and one cornice drawn | the kit triangle budget at 810,375 triangles, spent windows-first, in the district whose canyon is made of cornices | **performance** |
| 4,666 props dropped, 4,320 of them trees | the props triangle budget at 1,020,484 triangles | performance |
| 114 of 141 trees are a substituted species | the asset set is ten species with two states (J108) | data — open |
| the George Washington statue and every monument absent | no asset exists for the artwork or memorial kinds (J58 remainder) | data — open |
| 297 people where the table asked 5,044 | the 1,125,000-triangle agent budget plus the placement rules; 246 bodies were dropped for not being on a road-network sidewalk and 27 were placed inside buildings (J101) | performance + verification |
| 4 boro taxis on Wall Street, 4 yellow cabs | the runtime splits the taxi share 70/30 yellow to green everywhere with no geography (J105) | data — open |
| park ground 0.4877 under the terrain in the middle distance | the park surfaces were draped on the fine grid and this scene's terrain coarsens away from the lens (J40, J96) | verification — declared |
| no flags | flags on buildings are not a class this build models | geometry — no source |
| 53,345 faces cut for landmark ground | sixteen landmark models stand inside this radius, each cutting the terrain under its own footprint (J96) | verification — declared |
| no cloud | nothing in this build reads a historical sky | reference — no source exists |
