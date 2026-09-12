# Bethesda Terrace and Fountain

`bethesda_terrace_fountain` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Bethesda Fountain and the Lake, Central Park, Manhattan, New York.jpg by Christian David, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2026-04-18 08:04:45, 1920x1280. [Commons page](https://commons.wikimedia.org/wiki/File:Bethesda_Fountain_and_the_Lake,_Central_Park,_Manhattan,_New_York.jpg) — the photograph's own view direction is derived from the image at **high** confidence.

**Camera** — 40.773882, -73.971046 (NYC_TM -1777, 8205) at z 22.8 m NAVD88 | azimuth 20.4°, pitch +2.4° | 28 mm on 36 mm (65.5° horizontal) | 1280x854. The camera stands on **this photograph's own EXIF GPS**, 42.7 m from the item's recorded viewpoint, and was **not moved**. It was, however, **raised onto the terrace's upper deck**: the eye point first sat **1.83 m under** `verify_pavement`, the paved upper level the viewpoint note names at 21.19 m NAVD88, so it was lifted to stand on the surface actually drawn under it at **22.79 m NAVD88**. The view azimuth is clear for 50 m, the nearest built thing in the frame is `lm_b_bethesda_terrace.16` 25.3 m away, and no simulated agent stands within 60 m.

**Sun** — azimuth 92.9°, elevation 20.3° at 2026-04-18T08:04:45−04:00, from the photograph's own **EXIF DateTimeOriginal**; 657.2 W/m² direct normal, sky at strength 0.0404, Filmic, **+0.83 stops** — and those stops are **measured**, not assumed: the linear frame's median luminance of 0.10121 placed at middle grey (J83). The physical rule would have given 1.1 stops. Both the instant and the position are the photograph's own.

**In the scene** — 1,990,716 triangles: 4 building tiles, 8 landmark models of which 5 fall inside the 65.5° frame, 14,791 pavement polygons, 5,642 props, 100 kit pieces, 16 park-ground meshes, 0 vehicles and 11 people.

## Verdict — the subject is visible, the sightline is honest about it, and what is visible is a 3.3 m slab standing in for a bronze sculpture group

**The hard parts of this sheet are right and the easy part is wrong.** The camera is on the photograph's own GPS, the instant is its own EXIF, the exposure is metered off the frame rather than assumed, and the viewpoint is correctly lifted onto the terrace's paved upper level instead of being rejected as "under pavement" — the four things that took the most work to get right. The composition follows: both halves look north-north-east from the upper terrace across the fountain plaza to the Lake and the wall of the Ramble behind it.

**And the Angel of the Waters is not in the render.** The height probe casts **43 rays, all 43 landing on built fabric**, and measures the subject at **8.64 m** above a ground of 17.16 m. The object it measured is `lm_b_bethesda_terrace.2`, whose plan extent is **3.3 m by 0.3 m** — a thin upright slab. The sightline then casts 13 rays, **13 clear**, **8 of them on the subject**, for a visible fraction of **0.615**, and reports `subject_visible: true`. Every one of those numbers is correct, and together they certify that a stepped base carrying a 3.3 m by 0.3 m slab is visible where the photograph shows a tiered bronze fountain with a winged figure on top. **The verification passed on a stand-in.** The record is not lying; it is measuring the thing that is there.

The cause is in the record two lines further down: among the props the scene wanted and could not draw are **11 artwork, 9 drinking fountain and 5 memorial** entries, unmapped because no asset exists for those kinds. The Angel of the Waters is an artwork. The terrace's landmark model carries its architecture — the stairs, the balustrade masses, the plaza — and the sculpture on top of the fountain is a class this build does not model.

## What matches

* **The view is the photograph's view.** Azimuth **20.4°** is the bearing from the photograph's own GPS to the fountain; the item's nominal azimuth is 13.9°, **6.5° away**, and was not used. Looking north-north-east from the upper terrace, the plaza in the near field, the Lake behind it, the Ramble closing the horizon — the same composition in both halves.
* **The viewpoint stands on the deck it is supposed to stand on.** This is the J65 repair working on the sheet it was written for: the eye was 1.83 m below the drawn paving and is now on it at 22.79 m NAVD88.
* **The plaza, the basin ring and the terrace stairs are all in place** and at the same points in the frame as the photograph's — the circular paved disc with the fountain at its centre, the steps rising on the right.
* **The Lake is drawn**, a flattened water surface of **3,737 quads**, filling the middle distance where the photograph's water sits, with the far shore in the same place.
* **The canopy closes the horizon.** 5,494 trees are in range, of which **3,542 are procedural canopy stems placed by rule inside mapped woodland polygons** — the Stage 55 repair. Before it the Ramble rendered as bare terrain; here it is a wall of foliage across the same span of the frame as the photograph's.
* **The trees are leaf-on and the date is why.** The reference is 18 April and the foliage variants are selected from the photograph's own date.
* **The exposure is measured.** The render develops its own median to middle grey at +0.83 stops; the photograph's median sits **1.009 stops** from that same convention. A brightness ratio on this sheet is first that difference in development and only then the scene (J83).
* **No traffic, and the record says why.** 0 vehicles is correct here: **46 were dropped for standing on Central Park's East, West, Terrace or Center Drive**, which the drop reason records as having carried no private traffic since 2018, the year the ban took effect.

## What does not match

* **The fountain is massing, not sculpture.** No winged figure, no tiered bowls, no bronze: a stepped block and a 3.3 m by 0.3 m upright. The photograph's subject is the most detailed object in its frame and the render's is among its least.
* **Every surface in the near field is flat colour.** The photograph's plaza is patterned red and brown brick in a radial layout; the render's is an even pale grey. Six park-ground kinds are recorded as deliberately flat — grass, infield clay, hard court, rink ice, bare ground, recreation grass — because **the shared photographic catalogue has no set for any of them** (J40); its entries are walls, roofs, roadway, floors and vehicle interiors. `glass_curtain` is flat for the same reason.
* **The colour is a little over half the photograph's.** Chroma **0.0828** against **0.1435**, a ratio of **0.577**. A spring morning over red brick and new foliage is the worst case for a build whose ground materials are authored base colours.
* **Less contrast, and brighter in the midtones.** Standard deviation **0.1474** against **0.2089** (**0.706×**), median **0.498** against **0.3583** (**1.39×**), mean **0.4655** against **0.391** (**1.191×**), 5th percentile **0.1827** against **0.0933**. The render has no deep shadow: an 08:04 sun at 20.3° elevation and 92.9° azimuth rakes almost straight down the view axis, so the frame is front-lit and the photograph's shadowed foreground is not reproduced.
* **The Lake reads as a pale sheet rather than green reflective water.** The surface is there and flattened correctly; what is missing is its material.
* **The crowd is 11 people against the photograph's several dozen**, 3 at LOD1 and 8 at LOD2. 10 more were outside the radius, 4 were not on a walkable surface and 2 stood in the carriageway without crossing. The photograph's plaza on a April morning is busy in a way 11 figures cannot be.
* **The balustrade's carved posts, the ornate lamp standard on the right edge, the dogs and the parks utility cart are all absent.** 60 street lamps are in range and none is the photograph's cast-iron standard; carts, dogs and stone balusters are not classes this build carries.
* **The tree positions, species and heights are inferred, not surveyed**, for the 3,542 canopy stems — declared procedural under §12 rather than claimed as the Ramble's actual trees. 1,052 species were substituted and 5,485 instances scaled, mean scale 0.937, 9 out of band.
* **Far park ground sinks into the terrain.** Beyond 400 m, **0.2852 of 1,301 samples sit under it** and 0.0346 z-fight; within 150 m the under-fraction is 0.0024 and nothing z-fights. The horizon is where the coarsened 40 m terrain grid and the draped park surfaces disagree.
* **3 of the 4 tiles in range have no structures file at all**, so 48 triangles of structures stand in this frame.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the Angel of the Waters is absent; the subject is a 3.3 m by 0.3 m slab on a stepped base | the sculpture's class is unmapped — 11 artwork, 9 drinking fountain and 5 memorial props had no asset to draw. The terrace's architecture is modelled; its sculpture is not | **geometry — open, no asset for the class** |
| the sightline certifies a stand-in as visible | the probe and the fan measure the built thing standing at the subject's coordinate, which is the slab. Every figure is correct and the verdict is still about the wrong object | **verification — open** |
| plaza, grass, court, clay, ice and bare ground are flat colours | the CC0 texture catalogue has no photographic set for any of them; the builder's authored base colour is kept rather than the nearest wrong material (J40) | data — no source exists |
| chroma 0.577× | follows from the flat ground materials against a spring reference | data |
| sd 0.706×, p50 1.39× | an 08:04 sun at 20.3° almost along the view axis front-lights the frame; the photograph's foreground shadow has no counterpart | reference — the instant is the photograph's own, the shadow geometry follows from it |
| the Lake has no water material | water is not among the 21 city surfaces the catalogue resolves | data |
| 11 people where the photograph has dozens | the density table asked for 13 people over the simulated ring and the placement rules dropped 16 more; this is the simulation's own crowd for that hour, not the photograph's | verification |
| no balusters, no cast-iron lamp standard, no cart, no dogs | none is a class this build models; the 60 lamps in range are the generic fixtures | geometry |
| tree positions, species and heights inferred | no survey exists for the Ramble's canopy; declared procedural (§12, Stage 55) | data — declared |
| 0.2852 of far park-ground samples under the terrain | the 40 m coarsened grid at the scene edge against surfaces draped on the 2 m heightmap | verification |
