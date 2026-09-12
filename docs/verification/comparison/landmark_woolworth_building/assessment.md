# Woolworth Building

`landmark_woolworth_building` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Woolworth Building April 2022 007.jpg by Kidfly182, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2022-04-30 13:17:00, 1920x2560. [Commons page](https://commons.wikimedia.org/wiki/File:Woolworth_Building_April_2022_007.jpg) — the view direction is derived from the image at **high** confidence. The tower fills the portrait frame from City Hall Park: terracotta piers running the full height, the setbacks, the flying buttresses and pinnacles of the crown, and blossom branches at the frame's edges against a deep April blue.

**Camera** — 40.712333, -74.006797 (NYC_TM -4799, 1371) at z 13.7 m NAVD88 | azimuth 273.2°, pitch +20.2° | 18 mm on 36 mm (73.7° horizontal, 90.0° vertical, **portrait**) | 904x1206. The camera stands on **this photograph's own EXIF GPS**, **44.0 m** from the item's recorded viewpoint, and was **not moved**: `moved: false`, offset 0.0 m, view azimuth clear for **101.4 m** against a 67.8 m requirement, **no simulated agent within 60 m**. The nearest built thing in the frame is `t_-5_1_park_park_ground_grass` **3.9 m** from the lens — a joined park-ground tile mesh under the photographer's feet. The heading is the bearing from that GPS to the subject; the item's own recorded azimuth is 257.6°, **15.6° away**. The lens is at the **18 mm floor** and the record declares the cost: the top is still cut off and *"the verticals converge, so this frame is not comparable with the photograph on proportion"*. The ground under the lens reads 12.129 m NAVD88 from 16 samples within 5.0 m, range 12.06 to 12.2 m, and the record notes that **no surface was named** in the viewpoint note, so the heightmap median within 5 m was used rather than the tenth percentile.

**Sun** — azimuth 193.0°, elevation **63.7°** at 2022-04-30T13:17:00−04:00, from the photograph's own **EXIF DateTimeOriginal**; 927.1 W/m² direct normal, sky at strength 0.0308, Filmic, **+1.51 stops**. Metered, unclamped. The physical rule would have given **0.0**.

**In the scene** — 4,500,189 triangles: 6 building tiles (197,132 tris), 12 landmark models of which 3 fall inside the 73.7° cone, 28,256 pavement polygons, 607 props, 5,394 kit pieces, 26 park-ground meshes, **4 tiles of structures (63,424 tris)**, 88 vehicles and 437 people.

## Verdict — the best-behaved height probe in the pass, and a honeylocust fourteen metres from the lens takes ten of the thirteen rays

**The probe found the right object and measured it almost exactly.** 43 rays cast, **40 on built fabric**, and the answer is **236.75 m** above a ground of 9.99 m on `lm_woolworth.3`, whose plan extent the record gives as **32.8 by 32.8 m**. Measured off `blender_out/landmarks/woolworth.glb`, that is `woolworth_crown` — 632 triangles, 32.8 m square, running from 203.31 m to **241.40 m**. The catalogue entry 8.7 m away carries **241.4 m**. So the probe aimed at the crown, hit its roof, read 236.75 m, and the **4.65 m** it is short of the catalogue is the finial above the point the ray met. Three independent things agree here — the catalogue, the geometry and the measurement — and the object measured is the object a reader would name. Nothing else read this round does all three.

**Then a tree takes the sheet away.** The sightline reports 13 rays, **3 clear**, **1 on the subject**, a visible fraction of **0.077** — one ray in thirteen — and ten of them stop at **14.6 m** on `prop_tree_honeylocust_large_7`. The render shows exactly that: a single honeylocust in full leaf occupies the centre and right of the frame, and the Woolworth's crown is legible above and to the left of it, small. The camera was not moved, because from its own point the view azimuth is clear for 101.4 m — the walk's clearance probe tests built fabric and a tree is a prop (J88), so the one thing standing between the lens and a 241 m tower is invisible to the rule that chose the spot.

**The tree should not be in full leaf.** The photograph was taken on **30 April** and shows blossom and new foliage, sparse enough to see through at the frame's edges. The build's leaf switch is binary with a 15 April threshold, so every tree in this scene is drawn in full summer canopy (J97), and 233 of the 253 trees are a substituted species (J108). The difference is not cosmetic on this sheet: it is the difference between a canopy you can see a tower through and one you cannot.

**The tower itself is the best-modelled landmark read this round.** 18 mesh nodes and **47,991 triangles**, of which **30,696** are the main shaft's skin over 73.0 by 67.9 m from 15.27 m to 118.89 m, then 5,288, 3,960 and 1,960 for the three setback tiers, 1,723 of base detail and 632 for the crown, and seven materials including a named `terracotta_cream`. That is why the render's tower reads as the Woolworth at 136 m even at a small size in the frame.

**And the exposure runs the other way here.** The photograph's own median sits **0.679 stops above** the grey convention — an open, bright frame — while the render is metered to **0.218 above**, so the gap is **−0.461 stops** and the render is the *darker* half: mean **0.971×**, p50 **0.864×**. The render also holds **more** contrast, sd **1.223×**, because a sunlit terracotta tower against a Nishita sky is a harder edge than the same tower in the real haze of a Lower Manhattan afternoon. Chroma is **0.567**.

## What matches

* **The height, the object and the catalogue all agree.** 236.75 m measured from 40 of 43 rays on the crown, against a catalogued 241.4 m which is the crown's own modelled top, the 4.65 m difference being the finial.
* **The model carries the building's character.** 47,991 triangles in 18 nodes, with the shaft's fenestration at 30,696 and three setback tiers, base detail, a 632-triangle crown and a `terracotta_cream` material — and the render's tower is recognisable as the Woolworth.
* **The camera is where the photographer stood**, on the photograph's own GPS, not moved, 101.4 m of clear view, nothing within 60 m.
* **The lens is in portrait**, 73.7° by 90.0°, matching a 1920 by 2560 reference.
* **139 of the 253 trees are drawn from modelled branches**, not cards — among the highest counts in the pass.
* **The park ground is correct where the camera can see it**: 265 samples within 150 m, `under_frac` **0.0**, median clearance +0.193 m.
* **The frustum names three real neighbours at real bearings**: the Woolworth at 131.0 m and 3.1° off axis, One World Trade Center at 544.0 m and 4.8°, the World Trade Center site at 545.5 m and −12.3°.
* **The block is paved and marked**: 28,256 polygons with 11,786 white markings, 5,283 sidewalk, 4,725 roadbed, 3,626 curb, 1,125 plaza, 750 crosswalk, 430 median and 228 yellow markings, and **0 dropped**.
* **The park is furnished**: 67 benches, 65 street lamps, 49 manholes, 40 Citi Bike dock units, 26 waste baskets, 21 vent grates, 20 bike racks, 17 hydrants, **13 flagpoles**, 12 bus-stop signs, 6 subway entrances and 3 mailboxes.
* **Structures are here**: 4 tiles imported for 63,424 triangles.
* **The Sun and the day type are both right**: the real minute from EXIF, and 30 April 2022 was a **Saturday**, which is the density profile the simulation used.

## What does not match

* **One ray of thirteen reaches the subject.** The published fraction is 0.077 and ten rays stop 14.6 m from the lens on a single honeylocust.
* **The frame's subject is a tree.** In the photograph the tower fills the picture; in the render it is a small crown above a canopy that occupies half the frame.
* **The canopy is in full summer leaf on 30 April**, where the photograph shows blossom and new foliage you can see through (J97), and 233 of 253 trees are a substituted species (J108).
* **The verticals converge and the photograph's do not.** 18 mm at +20.2° of pitch against a photograph made to hold a 241 m tower; the record declares the two halves incomparable on proportion.
* **The terracotta Gothic is a skin, not relief.** 30,696 triangles carry the shaft's window grid; the piers, spandrel panels, gargoyles and the crown's flying buttresses are not separately modelled, and at 136 m in this frame none of them would read anyway.
* **The render is darker than the photograph and harder.** The photograph sits 0.679 stops **above** the grey convention and the render 0.218 above it, a **−0.461-stop** gap, so mean reads 0.971× and p50 0.864×; sd reads **1.223×** because a procedural sky gives a harder shadow edge than a real hazy afternoon (J83).
* **Chroma is 0.567** against a terracotta tower in a deep April blue.
* **Four in five props in range were dropped.** 607 drawn of 4,458 at a 1,073,968-triangle budget, **3,652 dropped**, including **2,625 tree rows**, with 3 impostor cards dropped as opaque and 4 lost on a suppressed building.
* **Three quarters of the kit was withheld.** 5,394 drawn of **21,456** in range against a **915,423**-triangle budget, of which 5,102 are windows against **12 cornices and 12 string courses** — and a further 1,172 pieces were suppressed under the landmark shells.
* **Twenty-seven props across five kinds had no asset**: 8 parks building, 6 memorial, 5 artwork, 5 drinking fountain, 3 misc structure. The item's own viewpoint is *"City Hall Park by the fountain"*, and the fountain is one of those kinds.
* **437 people where the table asked 5,035** — the joint largest ask read this round. 580 vehicles and 5,035 people were wanted over the simulated ring; 621 and 3,000 were simulated and **3,096 dropped** — 1,211 pedestrians outside the radius, **617 in the carriageway without crossing**, 589 at the 1,125,000-triangle agent budget, 362 vehicles outside the radius, 142 vehicles at the budget, 138 not on a walkable surface, 18 riderless bodies, 11 off the carriageway and 8 inside buildings.
* **Every agent is at the coarsest LOD**: all 88 vehicles and all 437 people at LOD2.
* **Nine of the eighty-eight vehicles are green boro taxis** in Lower Manhattan, inside the zone where a Street Hail Livery may not take a hail (J105).
* **Two of the six tiles have no structures file.**
* **The park ground sinks in the far field**: 0.2798 of 840 samples beyond 400 m, worst case −1.653 m; and 53,345 faces were cut for landmark ground, because twelve landmark models stand inside this radius.
* **No cloud.** The photograph's sky is a clear deep blue that the Nishita dome at strength 0.0308 renders paler and flatter.

## Measured for this assessment

| figure | where it comes from |
|---|---|
| the model is 18 mesh nodes and 47,991 triangles: shaft skin 30,696 over 73.0 by 67.9 m from 15.27 to 118.89 m, setback tiers 5,288, 3,960 and 1,960, base detail 1,723 and crown 632 from 203.31 to 241.40 m, LOD1 120 | the accessor `count` and `min`/`max` of every primitive of every node of `blender_out/landmarks/woolworth.glb`, read from the binary glTF header |
| the object the probe measured is the crown | that node's plan extent of 32.8 by 32.8 m matches the record's `plan_extent` exactly, and its modelled top of 241.40 m matches the catalogue's 241.4 m |
| the 4.65 m the probe is short is the finial | the recorded probe height of 236.75 m against the crown's own modelled top of 241.40 m |
| seven materials including a named terracotta | the `materials` array of the same file: limestone, grey and dark roof, `terracotta_cream`, clear and dark glass, green copper |
| 30 April is past the leaf-off threshold | the `leaf_off` rule in `blender/verify/render_sheets.py`, true only for a date on or after 15 November or on or before 15 April (J97) |
| the best agreement between catalogue, geometry and measurement read this round | this sheet's three figures — 241.4 m catalogued, 241.40 m modelled, 236.75 m measured on the same object — against the thirty-eight sheets read in the preceding rounds |

## Cause of each gap

| gap | cause | class |
|---|---|---|
| one ray of thirteen reaches the subject | a honeylocust stands 14.6 m from the lens and the walk's clearance probe tests built fabric only, so a tree cannot be scored around and the camera was never moved (J88) | **verification — open** |
| the canopy is full summer on 30 April | the leaf switch is binary with a 15 April threshold, so there is no leaf-out state; on this sheet that is the difference between a canopy you can see through and one you cannot (J97) | **declared decision — the rule is stated and it has two positions** |
| 233 of 253 trees are a substituted species | the asset set is ten species with two states (J108) | data — open |
| the verticals converge | 18 mm is the widest the build will use and a 241 m tower 136 m away needs 60 deg of elevation; the record declares it | verification — declared |
| no terracotta relief | the shaft is a 30,696-triangle skin; piers, spandrels and the crown's buttresses are not separately modelled, and no per-building ornament source exists (J66) | geometry — declared, no source |
| the render is darker and harder than the photograph | the photograph was developed 0.679 stops above the grey convention and the render is metered to 0.218 above it; the procedural sky gives a harder shadow edge than real haze (J83) | reference — declared, and correct |
| chroma 0.567 | flat authored surface colours and a procedural sky against terracotta in deep April blue (J66) | data — declared |
| 3,652 props dropped, 2,625 of them trees | the props triangle budget at 1,073,968 triangles | performance |
| the kit withheld — 5,394 drawn of 21,456 in range — and 12 cornices drawn | the kit triangle budget at 915,423 triangles, spent windows-first | **performance** |
| the fountain and the park's monuments absent | no asset exists for the parks building, memorial, artwork or drinking fountain kinds (J58 remainder) | data — open |
| 437 people where the table asked 5,035 | the 1,125,000-triangle agent budget plus the placement rules; 138 bodies were dropped for not being on a road-network sidewalk (J101) | performance + verification |
| 9 boro taxis in Lower Manhattan | the runtime splits the taxi share 70/30 yellow to green everywhere with no geography (J105) | data — open |
| 2 tiles with no structures file | those tiles were not built (B13 remainder) | data — open |
| park ground under the terrain beyond 400 m, 53,345 faces cut | the park surfaces were draped on the fine grid and the terrain coarsens to 40.0 m; twelve landmark models each cut the terrain under their footprint (J40, J96) | verification — declared |
| no cloud | nothing in this build reads a historical sky | reference — no source exists |
