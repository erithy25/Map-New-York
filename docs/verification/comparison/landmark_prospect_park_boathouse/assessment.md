# Prospect Park Boathouse

`landmark_prospect_park_boathouse` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Prospect Park New York May 2015 005.jpg by King of Hearts, CC BY-SA 3.0 (https://creativecommons.org/licenses/by-sa/3.0), taken 2015-05-02, 1920x1272. [Commons page](https://commons.wikimedia.org/wiki/File:Prospect_Park_New_York_May_2015_005.jpg) — the photograph's own view direction is derived from the image at **high** confidence. It is the Lullwater in a dead calm: the water mirror-flat across the lower three fifths, the Lullwater Bridge on the left, the Boathouse's white terracotta facade and **red tile roof** through the trees, and a deep blue sky. The trees are **half bare and half coming into leaf**.

**Camera** — 40.660211, -73.966618 (NYC_TM -1405, -4418) at z 21.0 m NAVD88 | azimuth 58.6°, pitch +2.2° | 35 mm on 36 mm (54.4° horizontal, landscape) | 1280x848. The camera stands on **this photograph's own EXIF GPS**, **185.0 m** from the item's recorded viewpoint, and the heading is the bearing from there to the subject; the item's recorded azimuth is 300.0°, **118.6° away** — the nominal viewpoint stands on the opposite bank. The eye point **stands on `t_-2_-5_park_park_ground_grass`** and the walk left it there, because this position is the photograph's own GPS rather than a nominal viewpoint standing for a deck (J65). The view azimuth is clear for **124.6 m** against a **66.4 m** requirement, **nothing built stands within 60 m of the lens**, and no simulated agent stands within 60 m. The ground under it reads 19.352 m NAVD88 from the 2 m heightmap, 16 samples within 5 m, range 19.11 to 19.91 m.

**Sun** — azimuth 268.8°, elevation 25.7° at 2015-05-02T17:30:00−04:00. The date is the photograph's and the hour is **chosen, not measured** (J80): of the hours putting the Sun above 20° it is the one whose bearing, 269°, comes closest to the item's recorded azimuth of 300°, **31° off**, so the Sun is behind the camera and lights what it looks at. 726.7 W/m² direct normal, sky at strength 0.0377, Filmic, **+1.52 stops** metered and unclamped against a linear median of **0.062905** and a target of **0.18**. The physical rule would have given **0.75 stops**. Per J80 the luminance comparison on this sheet is not evidence about the render, although here the two halves happen to agree closely.

**In the scene** — 2,630,962 triangles: 8 building tiles (546,784 tris, 0 missing, 0 LOD-substituted), 1 landmark model, **0.0° off axis** in the 54.4° frame, 6,369 pavement polygons, **14,482 props**, 100 kit pieces, 34 park-ground meshes over 610 surfaces, 2,472 triangles of structures, 32 vehicles and 11 people.

## Verdict — the best park frame in the pass, and its trees are in the wrong month

**This is the closest thing to a match in the pass so far.** The subject is dead on the axis — the frustum reports the Boathouse **0.0° off axis** at 132.3 m, the only exact zero written so far. The probe found fabric on **43 of 43** rays and measured **11.96 m** above a ground of 20.01 m against a catalogue entry of **11.55 m** whose origin stands **0.4 m** from the coordinate: a landmark whose stored position and stored height are both right, which is rare in this pass. The plan extent is **33.2 m by 16.1 m**, measured off the model. And the picture reads as the place: the Lullwater mirror-flat across the lower half with the bank and its trees reflected in it, the sloping lawns, the arch at the water's edge, and the Boathouse's pale colonnaded block in the middle distance.

**What is wrong is the month, and it is J97's spring case exactly.** The photograph is dated **2 May** and its trees are half bare, half in new leaf — the Brooklyn leaf-out, which is what makes the reference's canopy a pale acid green with dark bare limbs showing through. The render draws **full summer foliage**, because `leaf_off` is a single boolean with a 15 April threshold and 2 May is past it. There is no leafing-out state and no spring colour. Measured over the pass, **25 sheets sit in the 16 April to 15 May leaf-out** and every one of them is drawn this way, none of them wrong by the switch's own rule.

**The canopy itself is the largest in the pass and it is mostly rule-placed, which the sheet says.** **14,043 trees**: 12 drawn from modelled branches within 120 m, 14,031 as six-triangle impostor cards out to 797 m, and **12,827 of those cards are procedural canopy stems** placed by rule inside mapped woodland polygons (Stage 55) — their positions, species and heights inferred, not surveyed. Nothing was capped: **14,482 props placed of 14,518 in range**, **0 dropped for budget**. So the woods in this frame are a plausible woodland rather than a surveyed one, and the record prints the rule that made them.

**Two smaller things the picture shows.** The Boathouse's **red tile roof is absent** — the render's block reads white to its top edge, where the photograph's roof is the one warm mass in the frame. And **eight of thirteen sightline rays are blocked at 74.4 m by `prop_lamp_cobra_davit_157`**, a highway cobra-head lamp standing between the camera and the Boathouse on the Lullwater bank. Prospect Park's own lighting is the cast-iron post-top lantern, and the record shows both kinds placed here — 44 from the 30–40 m rule combined with the park post lamp, 31 from OSM combined with it, and **28 from the plain 30–40 m rule** with no park post. One of those 28 is what is in the way, and it is not an open question: **J56 measures the class** — **10,652 lamps stand on park ground and 7,520 of them are rule-placed cobra heads**, 629 of those in Central Park. So the fixture blocking eight of thirteen rays on the Lullwater bank is one instance of a counted, open fault, and the visible fraction of 0.385 is a cost of it.

## What matches

* **The subject is exactly on axis** — 0.0° off, at 132.3 m.
* **The catalogue is right about both position and height** — origin **0.4 m** from the coordinate, **11.55 m** against a measured **11.96 m**.
* **The water is a mirror and reads as one.** The reflection across the lower half of the render is the strongest single point of resemblance on the sheet, and the terrain carries **9 named water bodies** in range: Ambergill Pond, Binnen Water, Duck and Waterfowl, Prospect Lake, Upper Pool, a lake, a marsh, a pond and a river.
* **The tone and the mean agree** — mean **0.4819** against **0.4602** (**1.047×**), p50 **1.122×**. On a sheet whose instant was chosen rather than measured, that is luck as much as method, and J80 says to read it that way.
* **Nothing was capped, in props or in kit.**
* **The park is furnished as a park** — **170 benches**, 103 street lamps, 95 manholes, 38 Citi Bike units, 10 hydrants, 4 bike racks, 3 waste baskets, 1 subway entrance.
* **The park ground is exact near the camera** — within 150 m, 125 samples, an under-fraction of **0.0**, a median clearance of **0.185 m**, a worst of **+0.04 m**, no z-fighting. **143 faces** were cut for the landmark's own ground.
* **The building tiles are complete** — 8 tiles, 546,784 triangles, **0 missing** and **0 LOD-substituted**, the largest building-tile figure on any sheet written so far.

## What does not match

* **The trees are in full summer leaf and the photograph's are leafing out.** `leaf_off` is binary with a 15 April threshold (J97).
* **The Boathouse's red tile roof is absent.**
* **The woodland is inferred, not surveyed** — 12,827 of the 14,031 impostor cards are procedural canopy stems placed by rule, with inferred species and heights (Stage 55, declared on the sheet).
* **700 of the trees are a substituted species and 26 are scaled outside the allowed band** — the highest out-of-band count on any sheet written so far.
* **Eight of thirteen sightline rays are blocked by a single lamp**, giving a visible fraction of **0.385**; the ray that does reach the subject lands at 124.7 m.
* **The render holds two thirds of the photograph's contrast** — sd **0.1612** against **0.2318**, a ratio of **0.695** — and **0.584** of its colour, chroma **0.1192** against **0.2041**. The reference's deep blue May sky and its acid-green new leaves are most of both.
* **No cloud, and a pale sky.** The photograph's sky is a saturated blue that the render's Nishita sky does not reach at this Sun elevation; nothing in this build reads a historical sky.
* **The bank is a smooth lawn.** The photograph's shoreline is undergrowth, reeds and bare earth; the render's park ground is one flat-coloured grass surface, because the texture catalogue has no photographic set for mown grass, clay, court, pool water, rink ice or bare ground (J40) and the park builder keeps its own colour.
* **Three of five tiles in range have no structures file** — 5 tiles, **3 without a file**, and only **2,472 triangles** of structures.
* **121 kit pieces were suppressed** under landmark shells, leaving **100 drawn of 221 in range** — on a sheet where the landmark is the only building that matters, that is correct behaviour and it leaves the neighbouring fabric bare.
* **25 props across six kinds in range have no asset** — 8 memorials, **6 drinking fountains**, **6 parks buildings**, 2 artworks, 2 parks comfort stations, 1 vending machine. Prospect Park's comfort stations and parks buildings are exactly the structures a reader would look for on its banks.
* **Eleven people in Prospect Park on a May afternoon.** The density table asked 69 and 104 were simulated; **38 were dropped for standing off a walkable surface** and 9 for standing in the carriageway without crossing — the park's paths and lawns are not surfaces the crowd's test can see (J101).
* **Beyond 400 m the park ground reads under the terrain on 0.2645 of 1,244 samples**, worst **−3.884 m**; between 150 and 400 m it is **0.2157** over 51 samples with a z-fighting fraction of **0.0392**. The redrape moved **557,263** vertices, the largest redrape on any sheet written so far, up to 0.696 m up and 0.847 m down.

## Measured for this assessment

| figure | how |
|---|---|
| 10,652 lamps on park ground, 7,520 of them rule-placed cobra heads | quoted from DEVIATIONS J56, which measured the class over the whole city; this sheet's own record shows 28 of its 103 lamps placed by the plain 30–40 m rule with no park post |

## Cause of each gap

| gap | cause | class |
|---|---|---|
| summer leaf against a 2 May leaf-out | `leaf_off` is one boolean with a 15 April threshold and there is no leafing-out state or spring colour; 25 sheets in the pass sit in this window (J97) | **verification — open (J97)** |
| no red tile roof | the model's roof carries no distinct tile material; the facade's terracotta is what the builder addressed | geometry |
| the woodland is inferred | only individually mapped trees exist in the sources, so woodland polygons are filled by rule (Stage 55) — named on the sheet and in the record | data — declared, and the honest form |
| 700 substituted species, 26 out of band | the species lists do not cover this stock and the nearest modelled species is used, counted rather than hidden | data — declared, counted |
| a visible fraction of 0.385 | one rule-placed cobra-head lamp 74.4 m out blocks eight of thirteen rays, and 28 of this frame's 103 lamps come from the plain 30–40 m rule with no park post; J56 measures the class at 7,520 rule-placed cobra heads on park ground out of 10,652 lamps there (J56, J79) | **data — open (J56), with a measured count** |
| sd 0.695, chroma 0.584 | a saturated blue May sky and acid-green new leaves against a clear Nishita sky and summer green; the photograph is developed 0.131 stops below the grey convention and the render 0.227 above (J83) | reference |
| no cloud | nothing in this build reads a historical sky | reference — no source exists |
| the bank is a smooth lawn | the park ground is one flat-coloured grass surface and undergrowth is not a class this build models (J40) | data + geometry |
| three of five tiles without a structures file | those tiles are unbuilt | data — open |
| 121 kit pieces suppressed | the landmark shell replaces the tile's buildings and takes their kit with it | declared decision |
| 25 props across six kinds unmapped | no asset exists for those kinds, parks buildings and comfort stations among them | data |
| eleven people in the park | the crowd's walkable test reads only the road network's sidewalk, median, plaza and crosswalk, so a park path and a lawn are unwalkable (J101) | **verification — open (J101)** |
| under-fraction 0.2645 beyond 400 m | the terrain grid coarsens to 40 m at the scene edge and the park builder drapes on its own heightmap; the redrape closes the near field to 0.0 and leaves this tail (J71) | geometry — open, bounded |
| the hour is chosen, not measured | the photograph carries a date and no time, so the hour was picked to light the recorded view direction, and the record says so (J80) | verification — declared, and the luminance comparison is void |
