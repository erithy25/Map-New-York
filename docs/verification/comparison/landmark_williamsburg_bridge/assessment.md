# Williamsburg Bridge

`landmark_williamsburg_bridge` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Williamsburg Bridge June 2022 003.jpg by Kidfly182, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2022-06-28 13:38:05, 1920x1440. [Commons page](https://commons.wikimedia.org/wiki/File:Williamsburg_Bridge_June_2022_003.jpg) — the view direction is derived from the image at **high** confidence. It is taken from Domino Park's Grand Street pier looking up at the Brooklyn tower: the steel lattice rising through the frame, the deck truss overhead, the main cables sweeping down, the approach's great steel arch at the right, a brick warehouse wall at the left, and half the picture is a June sky full of cumulus.

**Camera** — 40.713178, -73.968269 (NYC_TM -1544, 1464) at z 5.3 m NAVD88 | azimuth 241.7°, pitch +8.1° | 18 mm on 36 mm (90.0° horizontal, 74° vertical) | 1208x906. The camera stands on **this photograph's own EXIF GPS**, **389.2 m** from the item's recorded viewpoint, and the record makes the override explicit and argues it: *"It is past the 250 m sanity radius, but this item is a view of Williamsburg Bridge Brooklyn tower and the photograph stands 114 m from it against the recorded viewpoint's 479 m, on the same side to 33.7 deg, so the measurement is kept and the estimate is not."* It was **not moved**: `moved: false`, offset 0.0 m, view azimuth clear for **107.2 m** against a 57.2 m requirement, **no simulated agent within 60 m**. The nearest built thing in the frame is `prop_lamp_cobra_davit_1` **13.5 m** away, **dead ahead at 0.0° yaw and 0.0° pitch**. The lens is at the **18 mm floor** and the record declares the cost: the tower's top is still cut off and *"the verticals converge, so this frame is not comparable with the photograph on proportion"*. The ground under the lens reads 3.722 m NAVD88 from 16 samples within 5.0 m, range 3.44 to 4.32 m.

**Sun** — azimuth 208.0°, elevation **70.7°** at 2022-06-28T13:38:05−04:00, from the photograph's own **EXIF DateTimeOriginal**; 939.4 W/m² direct normal, sky at strength 0.0304, Filmic, **+1.27 stops**. Metered: the linear median is **0.074454** — already four tenths of the way to the 0.18 target — so the development is only **1.274 stops**, unclamped. The physical rule would have given **0.0**. A 70.7° near-solstice Sun is the brightest scene light on any sheet read this round.

**In the scene** — 4,500,068 triangles: 9 building tiles (278,754 tris), 2 landmark models of which 1 falls inside the 90.0° cone, 21,656 pavement polygons, 1,049 props, 7,190 kit pieces, 36 park-ground meshes, **9 tiles of structures (60,480 tris)**, 89 vehicles and 430 people. The water table holds the East River, the Navy Yard Basin and the Wallabout Channel, with 19,459 quads on the flattened water surface.

## Verdict — the best height measurement in the pass, on a frame that shows the bridge from underneath instead of the tower from in front

**Everything the instrument did here was right.** The height probe cast 43 rays and **all 43 landed on built fabric**. The catalogue origin is **246.9 m** away, past the 120 m the rule looks in, so J74 fired and the height came from the geometry: **103.19 m** above a ground of 0.0 m on `lm_b_williamsburg_bridge.196`, an object whose plan extent is **11.0 by 11.0 m**. That is one leg of the Brooklyn tower, an eleven-metre square steel box, and its top is the tower's top. The catalogue's own figure is **102.11 m**, so the measured and catalogued heights agree to **just over a metre** — from two independent routes, with the object that was measured being the right object for once. After the Brooklyn Bridge cable and Trinity's nave, this is what J94's repair is supposed to produce.

**The model earns it.** Measured off `blender_out/landmarks/b_williamsburg_bridge.glb`, the bridge is **216 mesh nodes and 84,236 triangles**: sixteen truss-bay nodes at 10,752 triangles, four main cables at 11,344, the suspenders at 2,656, the deck and approach railings at 20,064, the deck markings at 11,136 — and `deck_track_bed` and `deck_track_rail`, so **the J, M and Z subway tracks are on the bridge as geometry**. Eleven materials, from granite through four steels to lane paint. The towers read as lattice in the render, which is the thing the photograph is about.

**What the frame does not do is look at the tower.** The tower rises 98 m above a lens 114 m from it — 41° above the horizon — and 18 mm is the widest lens this build will use, so at +8.1° of pitch the picture is the **deck soffit** running the width of the frame with its lamp standards hanging under it, the approach viaduct's blank flank beneath that, and the towers reduced to two lattice fragments at the frame's top edge and right margin. The record says all of this in its own lens note before the assessment does. **And six of thirteen sightline rays stop 13.5 m from the lens on a cobra-head street lamp standing dead ahead** — J88's exact shape — so the published fraction of **0.385** is a lamp mast as much as a bridge.

**The deck's underside is a plane.** In the photograph the soffit is a lattice of floor beams, stringers and lateral bracing, deep enough to read as a space; in the render it is one flat surface with lamps on it. The truss is modelled in sixteen bays and the render shows it in silhouette above the deck, but what a viewer standing under this bridge actually sees — the ironwork overhead — is not there.

**And the sky is half the photograph.** A June afternoon of scattered cumulus, with shadow moving across the tower's steel. Nothing in this build reads a historical sky, so the render's is an unbroken Nishita dome at strength 0.0304, and the difference shows in the numbers as much as in the picture: the render's contrast is **0.763** of the photograph's, its chroma **0.438**.

## What matches

* **The height agrees to just over a metre from two independent routes**: 103.19 m measured from 43 of 43 rays against a catalogued 102.11 m, on the correct object — an 11.0 m square tower leg.
* **J74's origin rule fired correctly**: the catalogue entry at 246.9 m was past the 120 m reach, so the figure was measured rather than copied, and the measurement turned out to confirm the entry.
* **The reference chooser overrode its own sanity radius and said why.** 389.2 m from the nominal viewpoint is outside the 250 m band, and the record argues the case on the distance to the actual subject — 114 m against 479 m — rather than silently accepting or silently rejecting it. This is the clearest reasoning in any camera block read this round.
* **The bridge is one of the most heavily modelled things in this build**: 216 mesh nodes, 84,236 triangles, sixteen truss bays, four main cables, suspenders, railings, deck markings, a walkway, and the subway track bed and rails.
* **Every tile in range has its structures file.** 9 imported, **0 without a file**, 60,480 triangles — the only sheet read this round with no structures gap at all.
* **The park ground is correct where the camera can see it**: 166 samples within 150 m, `under_frac` **0.0**, median clearance +0.205 m.
* **The scene arrived bright and needed almost nothing.** 1.274 stops on a linear median of 0.074454, the least development of any sheet read this round.
* **The fleet is a Williamsburg fleet**: 41 sedans, 22 SUVs, 12 yellow taxis, 4 boro taxis, 4 vans, 3 black cars and 3 box trucks — and four green Street Hail Liveries in Brooklyn is where they are legally allowed to work (J105).
* **The crowd was barely capped**: only 17 vehicles and 331 pedestrians lost to the agent triangle budget, the smallest budget loss read this round.
* **The street is marked**: 21,656 pavement polygons with 11,610 white markings, 2,842 curb, 2,632 sidewalk, 2,516 roadbed, 861 median and 671 crosswalk, and **0 dropped**.

## What does not match

* **The frame is the bridge from underneath, not the tower from in front.** A 103 m tower 114 m away needs 41° of elevation and the lens is held at 18 mm; the record declares the two halves incomparable on proportion.
* **Six of thirteen rays stop on a cobra lamp 13.5 m from the lens**, dead ahead, so the 0.385 fraction is partly a measurement of a lamp mast (J88).
* **The deck soffit is a plane.** The floor beams, stringers and lateral bracing that fill the photograph's overhead are not modelled; the flat underside with lamp standards is what a driver under this bridge would see.
* **The approach viaduct's flank is blank.** In the photograph the Brooklyn approach is a steel arch over a masonry pier; in the render it is an unrelieved pale wall across the frame.
* **No cloud, and the sky is half the reference.** The render's is an unbroken Nishita dome, so the moving shadow that models the tower's steel in the photograph is absent (chroma 0.438, sd 0.763×).
* **The subject's ground is 0.0 m NAVD88** — the tidal datum, because every tidal water body in this build is flattened to it (J103). The tower's pier stands in the river.
* **A stop and a fifth of the brightness difference is exposure.** The photograph sits **0.96 stops below** the grey convention and the render 0.227 above it, a **1.187-stop** gap, so p50 reads **1.476×** and mean 1.133× (J83).
* **Two thirds of the props in range were dropped.** 1,049 drawn of 4,578 at a 1,209,428-triangle budget, **3,083 dropped**, including **1,697 tree rows**, and only **5 trees are drawn from modelled branches** against 229 cards — in Domino Park, which is a planted park.
* **Nearly nine in ten kit pieces were withheld.** 7,190 drawn of **58,341** in range against a 1,164,307-triangle budget, of which 6,363 are windows against **15 cornices and 15 string courses** — Williamsburg's warehouse and tenement cornices are the street's whole character. A further 711 were suppressed under the landmark shells.
* **Three tiles in the 900 m ground radius have no park ground built at all**, so the terrain is bare there (J102).
* **Agents were placed where they could not stand**: **273 dropped for not being on a walkable surface** and **41 inside buildings** — Domino Park's own paths and the pier are not road-network sidewalk classes (J101).
* **430 people and 89 vehicles** where the density table asked for 268 vehicles and 1,634 people; 345 and 2,207 were simulated and **2,033 dropped** — 831 pedestrians outside the radius, 331 at the agent budget, 299 in the carriageway without crossing, 273 not on a walkable surface, 227 vehicles outside the radius, 41 inside buildings, 17 vehicles at the budget, 9 riderless bodies and 3 off the carriageway.
* **Every vehicle is at the coarsest LOD** — all 89 at LOD2.
* **Twenty props across four kinds had no asset**: **10 drinking fountain**, 6 misc structure, 3 artwork, 1 parks comfort station. Domino Park's own fixtures are among them.
* **The frustum reports the composite's centroid.** It names Williamsburg Bridge at 330.0 m and 36.0° off axis while the tower it is measuring stands 114.3 m away on the axis (J99).
* **One World Trade Center is at the photograph's horizon** and is not readable in the render's far distance, which resolves to pale boxes.

## Measured for this assessment

| figure | where it comes from |
|---|---|
| the bridge is 216 mesh nodes and 84,236 triangles | the accessor `count` of every primitive of every mesh node of `blender_out/landmarks/b_williamsburg_bridge.glb`, read from the binary glTF header |
| sixteen truss-bay nodes at 10,752 triangles, four main cables at 11,344, suspenders 2,656, deck and approach railings 20,064, deck markings 11,136 | the same counts grouped by node name in that file: `deck_truss*`, `cable_cable_t*`, `cable_suspenders`, `deck_railing` with `ap_mn_deck_railing` and `ap_bk_deck_railing`, and `deck_markings` with the two approach marking nodes |
| the subway track bed and rails are modelled | the `deck_track_bed` and `deck_track_rail` nodes of the same file |
| eleven materials, from granite through four steels to lane paint | the `materials` array of the same file: dark and grey granite, grey, black and silver steel, asphalt, sidewalk, dark concrete, warm light, white and yellow lane paint |
| the least development, the smallest agent-budget loss and the only sheet with no structures gap, read this round | this sheet's 1.274 stops, its 17 vehicles and 331 pedestrians lost to the agent budget, and its `tiles_without_a_file` of 0, against the thirty-seven sheets read in the preceding rounds |

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the frame shows the deck soffit rather than the tower | a 103 m subject 114 m away subtends 41 deg and the lens is held at the 18 mm floor, because wider would stop the two frames being comparable at all. The record declares it | **verification — declared; the honest alternative is a second frame at a greater distance** |
| six rays stop on a lamp 13.5 m away | the walk's clearance probe tests built fabric and a lamp mast is a prop, so the candidate scored as clear (J88) | **verification — open** |
| the deck soffit and the approach flank are planes | the bridge's ironwork is modelled above the deck and not beneath it; a floor-beam lattice is another order of geometry on a model already at 84,236 triangles | geometry — declared by what is and is not in the node list |
| the subject's ground is the tidal datum | every tidal water body is flattened to 0.0 m NAVD88 (J103) | declared decision |
| no cloud, chroma 0.438, sd 0.763x | nothing in this build reads a historical sky, so an unbroken procedural dome replaces a sky that is half the reference | **reference — no source exists** |
| 1.187 stops of exposure difference | the photograph was developed 0.96 stops under the grey convention and the render is metered to it (J83) | reference — declared, and correct |
| 3,083 props dropped, 1,697 of them trees, 5 modelled canopies | the props triangle budget at 1,209,428 triangles, on a frame whose foreground is a planted waterfront park | **performance** |
| 51,151 kit pieces withheld, 15 cornices drawn | the kit triangle budget at 1,164,307 triangles, spent windows-first, in a district of cornice-heavy warehouses | **performance** |
| 3 tiles with no park ground built | 85 per cent of the city's mapped open space has no ground geometry (J102) | data — open |
| agents placed where they could not stand, 273 plus 41 | the crowd's walkable test reads only road-network sidewalk classes, so a waterfront park and a pier are not standable (J101) | **verification — open** |
| 20 props across 4 kinds unmapped | no asset exists for those kinds (J58 remainder) | data |
| the frustum names the composite's centroid | a composite landmark is tested by its centroid rather than by the member at the subject's coordinate (J99) | verification — open |
