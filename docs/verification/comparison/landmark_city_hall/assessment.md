# New York City Hall

`landmark_city_hall` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Cherry blossom at City Hall Park, May 1st 2024, Manhattan 03.jpg by Deans Charbal, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2024-05-01 12:33:28, 1920x1440. [Commons page](https://commons.wikimedia.org/wiki/File:Cherry_blossom_at_City_Hall_Park,_May_1st_2024,_Manhattan_03.jpg) — the view direction is derived from the image at **high** confidence. The photograph's own title says what it is of: a cherry in full white flower filling the upper two thirds of the frame, people on the park's cast-iron benches under it, the cast-iron fountain at the left edge, and City Hall itself completely hidden behind the canopy.

**Camera** — 40.711953, -74.007003 (NYC_TM -4817, 1329) at z 13.1 m NAVD88 | azimuth 42.1°, pitch +7.3° | 35 mm on 36 mm (54.4° horizontal) | 1208x906. The camera stands on **this photograph's own EXIF GPS**, **50.5 m** from the item's recorded viewpoint, and was **not moved**: `moved: false`, offset 0.0 m, with the view azimuth clear for **102.7 m** against a 63.3 m requirement and **no simulated agent within 60 m**. The nearest built thing in the frame is `t_-5_1_park_park_ground_grass` **2.7 m** from the lens at −9.1° yaw and −21.1° pitch — a joined park-ground tile mesh under the photographer's feet, which is J91's near-fabric case rather than an obstruction. The heading is the bearing from that GPS to City Hall; the item's own recorded azimuth is 45.9°, 3.8° away. The ground under the lens reads 11.51 m NAVD88, the 10th percentile of 113 samples within 12.0 m, range 11.41 to 12.26 m.

**Sun** — azimuth 169.1°, elevation **64.3°** at 2024-05-01T12:33:28−04:00, from the photograph's own **EXIF DateTimeOriginal**; 928.3 W/m² direct normal, sky at strength 0.0308, Filmic, **+3.00 stops**. Metered: the linear median is **0.022582** against the 0.18 target, so the development is **2.995 stops**, unclamped. The physical rule would have given **0.0**. A near-noon May Sun at 64° over a closed canopy is why: almost every surface the frame contains is in leaf shadow.

**In the scene** — 4,500,131 triangles: 4 building tiles (106,490 tris), 12 landmark models of which 2 fall inside the 54.4° cone, 28,434 pavement polygons, 730 props, 5,636 kit pieces, 19 park-ground meshes, **3 tiles of structures (43,576 tris)**, 69 vehicles and 251 people.

## Verdict — the photograph is a cherry blossom photograph and this build has no blossom, and no cherry

**There is no Prunus model in the asset set and no flowering state on any tree.** Counted in `blender_out/props`, the build ships **10 tree species** — callery pear, ginkgo, honeylocust, littleleaf linden, Norway maple, pin oak, planetree, red maple, sophora and zelkova — each in three sizes and two states, **30 glbs in leaf and 30 bare**, and not one file in the set carries a bloom, flower or blossom variant. The 2015 street tree census the build places from records **132 distinct species over 652,169 trees**; the ten modelled species cover **349,927 of them, 53.66 per cent**. **Prunus is the fourth most common genus in the census at 41,653 trees, 6.39 per cent of the city**, and it has no model, so every cherry and plum in New York is drawn as something else. On this sheet **242 of the 268 trees** drawn had their species substituted, and the tree that blocks the sightline is `prop_tree_honeylocust_large_32` — a honeylocust standing where the photograph has a cherry.

**Measured across the whole pass, 90,815 of 231,720 trees drawn had their species substituted — 39.19 per cent** — and on six sheets it is effectively every tree: 55 Hudson Yards 226 of 226, the Statue of Liberty 277 of 277, the Hugh Carey portal 356 of 357, the 9/11 Memorial pools 281 of 282. The canopy of this city is a ten-species canopy with two appearances, and the reference photograph for City Hall is a picture of the thing it cannot draw. This is recorded as J108.

**Everything else about this sheet is unusually good, and one thing is unexpectedly right.** The probe cast 43 rays and **all 43 landed on built fabric**; the sightline reports **3 of 13 rays clear, 3 on the subject**, a visible fraction of **0.231**, and the blocker is a **tree 34.4 m from the lens**. That is not a defect. It is what the photograph shows: City Hall is behind the trees in both halves. For once the obstruction is the correct answer, and the fraction of 0.231 is an honest account of a view that genuinely is nine tenths foliage.

**The height probe measured the cupola, not the building.** 33.87 m above a ground of 12.83 m on `lm_city_hall.4`, whose plan extent the record gives as **17.3 by 17.3 m** — a square tower a sixth of City Hall's length. The catalogue origin 5.0 m away carries **36.6 m**, which is the building with the statue of Justice on top, so the difference of under three metres is roughly the figure and the lantern above what the ray met. J94 again: the probe measures whichever member stands at the coordinate, and at the centre of City Hall that member is the drum under the dome.

**And the park is empty of people, which is the other half of the photograph.** 78 benches are placed and **251 people are drawn in the whole frame**, with **133 dropped for not standing on a walkable surface** — City Hall Park's paths are not a road-network surface class, so the crowd cannot stand in the park at all (J101). The reference photograph is four people on a bench; the render's park has benches and nobody on them.

## What matches

* **43 of 43 probe rays on built fabric**, and the measured 33.87 m sits under three metres below the catalogue's 36.6 m once the lantern and figure are allowed for.
* **The obstruction is correct.** Ten of thirteen rays stop on a tree 34.4 m away, and in the photograph the tree is exactly where the building should be. This is the only sheet read this round whose low visible fraction is the right answer.
* **The camera is where the photographer stood** — the photograph's own EXIF GPS, not moved, 102.7 m of clear view, nothing within 60 m.
* **The canopy is dense and mostly real branches.** **123 of the 268 trees are drawn from their modelled branches** within 120 m, the highest count read this round, with 145 impostor cards beyond; mean scale 0.909, only 2 outside the band.
* **The park ground is correct where it can be seen.** 235 samples within 150 m, `under_frac` **0.0**, median clearance +0.183 m and a minimum of +0.001 m — the best near-field reading of any sheet read this round, and overall 0.1125 under across 1,983 samples, also the best.
* **The park is furnished as a park**: **78 benches**, 90 street lamps, 64 manholes, 43 Citi Bike dock units, 33 waste baskets, 29 vent grates, 27 hydrants, 21 bike racks, **13 flagpoles**, 13 bus-stop signs, 6 subway entrances and 3 mailboxes.
* **The block is paved and marked**: 28,434 polygons with 11,647 white markings, 5,212 sidewalk, 4,955 roadbed, 3,762 curb, 1,137 plaza, 797 crosswalk, 547 median and 234 yellow markings, and **0 dropped**.
* **Structures are here**: 3 tiles imported for 43,576 triangles, over the City Hall subway loop.
* **The frustum names two real neighbours at real bearings**: City Hall at 121.2 m and 2.0° off axis, the Manhattan Municipal Building at 300.1 m and 24.4°.
* **The Sun is the real minute** of a real Wednesday, from EXIF, and the development is metered: 2.995 stops on a linear median of 0.022582.

## What does not match

* **No cherry, no blossom.** The single most dominant feature of the reference photograph has no representation anywhere in this build: no Prunus asset, and no flowering state on any of the ten species that do exist.
* **242 of the 268 trees drawn are a substituted species**, so the canopy's composition is wrong as well as its phenology.
* **The trees are in full summer leaf.** 1 May falls outside the leaf-off window, so the switch is correct by its own rule and the rule has only two positions (J97); a May canopy in New York is neither bare nor fully out.
* **The render carries more colour than the photograph**, chroma 0.1553 against 0.1181, a ratio of **1.315** — the authored canopy green is more saturated than a real canopy under a 64° Sun with white blossom in it.
* **Three quarters of a stop of the brightness difference is exposure.** The photograph sits **0.514 stops below** the grey convention and the render 0.197 above it, a **0.711-stop** gap, so mean reads 1.335× and p50 1.26× (J83). The render holds less contrast, sd 0.2023 against 0.2295 (0.881×), because a procedural canopy's shadow is softer and flatter than real dappled light.
* **The fountain is absent.** Nineteen props across five kinds had no asset — **9 parks building, 6 memorial, 5 drinking fountain, 4 artwork, 3 misc structure** — and the park's cast-iron fountain at the left edge of the photograph is precisely one of those kinds (J58 remainder).
* **There is nobody in the park.** 251 people in the whole frame with **133 dropped for not being on a walkable surface**, because park paths are not a road-network surface class (J101), so the benches are empty.
* **Nearly four in five props in range were dropped.** 730 drawn of 4,406 at a 1,120,831-triangle budget, **3,464 dropped**, including **2,468 tree rows**; 4 impostor cards dropped as opaque.
* **Nearly four in five kit pieces were withheld.** 5,636 drawn of **26,412** in range against a **999,883**-triangle budget, of which 5,284 are windows against **15 cornices and 15 string courses** — on a block of Federal and Beaux-Arts civic buildings whose interest is entirely in their order. A further 280 were suppressed under the landmark shells.
* **City Hall's own portico and dome are not readable in the frame** because the trees are in front of them, so this sheet tests the canopy rather than the building.
* **53,345 faces were cut for landmark ground**, two orders of magnitude above a typical sheet, because twelve landmark models stand inside this radius.
* **Three green boro taxis** at City Hall, inside the zone where a Street Hail Livery may not take a hail (J105).
* **251 people where the table asked 3,859.** 673 vehicles and 3,859 people were wanted over the simulated ring; 705 and 2,998 were simulated and **3,383 dropped** — 1,227 pedestrians outside the radius, 812 at the 1,125,000-triangle agent budget, **564 in the carriageway without crossing**, 361 vehicles outside the radius, 251 at the budget, 133 not on a walkable surface, 12 riderless bodies, 12 off the carriageway and 11 inside a building.
* **Most agents are at the coarsest LOD**: 64 of 69 vehicles and 193 of 251 people at LOD2.
* **No cloud.** The photograph's sky is a clear May blue behind blossom; the render's is a Nishita dome at strength 0.0308.

## Measured for this assessment

| figure | where it comes from |
|---|---|
| the build ships 10 tree species in 60 glbs, 30 in leaf and 30 bare, with no flowering variant | the file names under `blender_out/props` matching `tree_*`: callery pear, ginkgo, honeylocust, littleleaf linden, Norway maple, pin oak, planetree, red maple, sophora and zelkova, each in small, medium and large, each with and without a `_bare` suffix, and none matching bloom, flower or blossom |
| the census records 132 distinct latin species over 652,169 trees | counted directly over `data/raw/nyc_opendata/street_trees_2015.csv.gz`, on the `spc_latin` column |
| the ten modelled species cover 349,927 of those trees, 53.66 per cent | the same count, summed over the ten species the asset set carries |
| Prunus is the fourth most common genus at 41,653 trees, 6.39 per cent | the same count, summed over every row whose `spc_latin` begins Prunus; the bare genus bucket `Prunus` alone is 29,279 rows |
| 90,815 of 231,720 trees drawn across the pass had their species substituted, 39.19 per cent | summed over every record carrying both `props.tree_species_substituted` and `props.per_kind.tree` -- 170 of them; the six highest shares are 55 Hudson Yards 226 of 226, the Statue of Liberty 277 of 277, the Hugh Carey portal 356 of 357, the 9/11 Memorial pools 281 of 282, and four staged sheets at 462 of 475 |
| the allometry table knows eight Prunus taxa the asset set cannot draw | `pipeline/nycsim_pipeline/furniture/allometry.py`, which carries mature-height entries for Prunus, cerasifera, virginiana, serrulata, sargentii, x yedoensis, subhirtella and serotina |
| the substituted-species count is what the resolver reports | `blender/verify/scene.py`, which increments `species_substituted` whenever `assets_index.resolve_scaled` returns a reason beginning `species_substituted` |
| the best near-field and overall park-ground clearance read this round | this sheet's near-field `under_frac` of 0.0 over 235 samples and overall 0.1125 over 1,983, against the thirty-four sheets read in the preceding rounds |
| 1 May falls outside the leaf-off window | the `leaf_off` rule in `blender/verify/render_sheets.py`, true only for a date on or after 15 November or on or before 15 April (J97) |

## Cause of each gap

| gap | cause | class |
|---|---|---|
| no cherry and no blossom | the asset set has ten species and two states per species, and neither a Prunus model nor a flowering state exists anywhere in it, while the census names 132 species of which the ten cover 53.66 per cent (J108, new) | **data — open; 46 per cent of the city's trees are drawn as another species and 6.39 per cent of them are cherries and plums with no model at all** |
| 242 of 268 trees are a substituted species | the same asset set, resolved per row by `resolve_scaled` | data — open |
| the canopy is in full summer leaf on 1 May | the leaf switch is binary with a 15 November / 15 April threshold, so there is no leaf-out or blossom state to be in (J97) | **declared decision — the rule is stated and it has two positions** |
| chroma 1.315 and sd 0.881x | an authored canopy green and a procedural soft shadow against real dappled light through white flower | data — declared (J66) |
| 0.711 stops of exposure difference | the photograph was developed 0.514 stops under the grey convention and the render is metered to it (J83) | reference — declared, and correct |
| the probe measured the cupola drum, 17.3 m square | the height probe takes the object standing at the subject's coordinate, and at the centre of City Hall that is the drum under the dome rather than the building (J74, J94) | **verification — open** |
| the fountain and the park's monuments are absent | no asset exists for the parks building, memorial, drinking fountain or artwork kinds (J58 remainder) | data — open |
| nobody sits on the benches | the crowd's walkable test reads only road-network sidewalk classes, so a park path is not standable and 133 bodies were dropped for it (J101) | **verification — open** |
| 3,464 props dropped, 2,468 of them trees | the props triangle budget at 1,120,831 triangles | performance |
| the kit withheld — 5,636 drawn of 26,412 in range — and 15 cornices drawn | the kit triangle budget at 999,883 triangles, spent windows-first, on a block of civic classicism | **performance** |
| City Hall is behind the trees | this is the photograph's own composition and the render reproduces it; the sheet therefore tests the canopy | reference — correct, and worth saying |
| 53,345 faces cut for landmark ground | twelve landmark models stand inside this radius, each cutting the terrain under its own footprint (J96) | verification — declared |
| 3 boro taxis inside the exclusion zone | the runtime splits the taxi share 70/30 yellow to green everywhere with no geography (J105) | data — open |
| 251 people where the table asked 3,859 | the 1,125,000-triangle agent budget plus the placement rules | performance + verification |
| no cloud | nothing in this build reads a historical sky | reference — no source exists |
