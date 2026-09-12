# New York State Pavilion

`landmark_ny_state_pavilion` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:NY State Pavilion.jpg by Mtam93940, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2015-10-18 11:41:23, 1920x2560. [Commons page](https://commons.wikimedia.org/wiki/File:NY_State_Pavilion.jpg) — the photograph's own view direction is derived from the image at **high** confidence. It is taken from inside the Tent of Tomorrow looking up: sixteen concrete columns, the **yellow** ring truss with its sawtooth brackets, the radial cable net, the three observation towers through the ring, and the **red-and-white striped** base wall.

**Camera** — 40.743499, -73.844343 (NYC_TM 8924, 4836) at z 8.1 m NAVD88 | azimuth 353.9°, pitch +0.4° | 32 mm on 36 mm (45.6° horizontal, 58.6° vertical, portrait) | 904x1206. The camera stands on **this photograph's own EXIF GPS**, **100.3 m** from the item's recorded viewpoint; the item's recorded azimuth is 20.0°, **26.1° away**, and belongs to the nominal viewpoint. The eye point **stands on `lm_c_flushing_meadows.6`** — the pavilion's own floor slab — and the walk left it there rather than moving: the record gives the reason, that this position is the photograph's own GPS rather than a nominal viewpoint standing for a whole deck, so there is nothing to walk to (J65). The view azimuth is clear for **51.4 m** against a **29.5 m** requirement, the nearest built thing in the frame is that same slab **1.2 m** away, and no simulated agent stands within 60 m. The ground under it reads 6.454 m NAVD88 from the 2 m heightmap, 16 samples within 5 m, range 6.44 to 6.54 m.

**Sun** — azimuth 161.4°, elevation 37.8° at 2015-10-18T11:41:23−04:00, from the photograph's own **EXIF DateTimeOriginal**; 828.4 W/m² direct normal, sky at strength 0.0340, Filmic, **+0.49 stops** metered and unclamped, against a linear median of **0.127688** and a target of **0.18**. The physical rule would have given **0.19 stops** — the two are within a third of a stop of each other, which happens on very few sheets in this pass.

**In the scene** — 1,685,605 triangles: 4 building tiles (73,862 tris, 0 missing, 0 LOD-substituted), 2 landmark models, both able to fall inside the 45.6° frame, 18,140 pavement polygons, 1,490 props, **0 kit pieces**, 21 park-ground meshes over 498 surfaces, 16,864 triangles of structures, 73 vehicles and **1 person**.

## Verdict — the structure is measured right and rendered entirely grey, and a Sunday in Flushing Meadows renders with one person in it

**The geometry is among the best in the pass.** The probe found fabric on **43 of 43 rays**, measuring **31.6 m** above a ground of 5.45 m on an object **101.6 m by 80.1 m** in plan — the Tent of Tomorrow's elliptical ring, measured off the model itself and not a tile mesh. All **13 of 13** sightline rays are clear, **9 land on the subject** and 4 pass into open sky through the ring, for a visible fraction of **0.692** and a clear fraction of **1.0**. The catalogue's **69.0 m** for `c_flushing_meadows` is the observation tower and this is the tent, which is why the probe took its height from the geometry (J74). The render shows the columns, the ring beam and the base drum in the right places at the right size.

**And it is all grey.** The photograph's subject is colour: a yellow steel ring truss with sawtooth brackets across the whole upper half, and a red-and-white striped base wall across the lower. The builder assigns `concrete` to the columns, the ring beam and the base, and `steel_dark` to the ring's steel members; **no colour is assigned anywhere in the model**. The measured consequence is the lowest chroma ratio on any sheet written so far: **0.0512 against the photograph's 0.1981, a ratio of 0.258** — the render carries a quarter of the reference's colour. The builder's own docstring is careful about the ruin ("the roof's coloured plastic panels are gone; the model shows the ring beam") and says nothing about the paint, which the 2015 restoration put back and which this 2015 photograph shows.

**Three things the photograph has that the render does not**: the radial cable net, which fills the upper half of the reference as a web of hundreds of lines and is not a class this build models; the sawtooth brackets on the ring; and the three observation towers, which the photograph frames inside the ring. The towers **are** built — the model lathes them with their disc platforms — but they are not in this frame, and the record does not say where they went: the frustum reports the composite's centroid **178.4 m away at 30.9° off axis**, which is the frame's left edge and not where the towers stand, so from this eye point they fall behind the tent's own base drum or outside the picture. That is a gap in the record as much as in the render.

**The park is empty, and the same record says why.** The crowd drew **1 pedestrian**. The density table asked for 65 people and 152 were simulated; **84 fell outside the radius, 59 were dropped for standing off a walkable surface** and 8 for being in the carriageway without crossing. The walkable test is `PED_SURFACES = (1, 2, 3, 5)` — sidewalk, median, plaza, crosswalk — read out of the **road** network's pavement export, and this frame's pavement is **7,813 roadbed, 4,602 curb, 2,579 white markings, 2,247 median, 442 sidewalk, 318 parking lot, 73 crosswalk and 2 plaza** polygons. In a 600 m radius of Flushing Meadows Corona Park there are 442 sidewalk polygons and two plaza polygons, and a park path is not a surface class at all: the park-ground builder writes ballfield, cemetery, court, golf, grass field, greenstreet, park ground, pool, recreation and vacant, and **none of them is walkable to the crowd**. So the crowd model puts people in the park, the placement test asks the road network whether they are standing on a sidewalk, and the answer is no (J101).

## What matches

* **The plan.** 101.6 m by 80.1 m, measured off the landmark model, which is the Tent of Tomorrow's ellipse.
* **The height** — 31.6 m on **43 of 43** probe rays, taken from the geometry rather than from a composite catalogue entry of 69.0 m (J74).
* **The sightline is perfect** — **13 of 13** rays clear, 9 on the subject, and the four that pass into nothing go through the open ring, which is what a roofless tent does to a ray.
* **The columns, the ring beam and the base drum** are in the render at the right diameter and the right height.
* **The development is nearly physical** — +0.49 stops metered against 0.19 by the rule.
* **Nothing was capped.** Props **1,490 placed of 1,521 in range**, **0 dropped for budget** — the whole neighbourhood the radius reached is drawn.
* **The park's canopy is dense and partly procedural** — 1,280 trees, **96** of them procedural canopy stems placed by rule inside mapped woodland polygons (Stage 55), and 1,275 drawn as impostor cards out to 600 m.
* **The park ground is exact where it matters** — within 150 m, **363 samples**, an under-fraction of **0.0**, a median clearance of **0.193 m**, a worst of **+0.045 m** and **no** z-fighting. **573 faces** were cut out of it for the landmark's own ground.
* **The crowd clock reads Sunday** for 2015-10-18, which was a Sunday, and the fleet is a Sunday park fleet: 45 sedans, 26 SUVs, 1 boro taxi and 1 police car, with **no** buses and **no** trucks.

## What does not match

* **No colour anywhere.** The yellow ring truss and the red-and-white striped base wall are the photograph's subject; chroma **0.0512** against **0.1981**, a ratio of **0.258**.
* **No cable net.** The radial suspension web fills the reference's upper half; nothing of it is in the render.
* **No sawtooth brackets** on the ring.
* **The three observation towers are not in the frame**, although the model builds them.
* **One person in a park on a Sunday** — 59 of the simulation's pedestrians were dropped for standing off a walkable surface, which in a park means every path and lawn (J101).
* **Not one kit piece was drawn.** **858 in range and 858 suppressed** under landmark shells — the whole facade kit for this frame gave way to the landmark models, which is correct behaviour and leaves the Queens Museum's own elevation bare.
* **1,131 of the 1,280 trees are a substituted species** — the highest substitution share on any sheet written so far — and **1** is scaled outside the allowed band.
* **The render is brighter at the midtone** — p50 **0.4977** against **0.3748**, a ratio of **1.328**, mean **1.07×** — and flatter, sd **0.2141** against **0.2568** (**0.834×**). The photograph's median sits **0.636 stops below** the grey convention, a frame exposed for a bright October sky against dark concrete, and the render's **0.236 above** it, a **+0.872-stop** difference (J83).
* **No cloud.** The reference's sky carries October cumulus behind the ring, and it is a large part of the frame because the roof is open; nothing in this build reads a historical sky.
* **The park ground sinks badly in the distance** — beyond 400 m the under-fraction is **0.418** over 787 samples, the worst far-field reading on any sheet written so far, with a minimum of **−1.868 m**; between 150 and 400 m it is **0.0836** over 359 samples. The redrape moved **346,385** vertices, up to 0.634 m up and 0.803 m down.
* **Ten park surface kinds keep the builder's flat colour** — infield clay, cemetery grass, hard sport court, golf grass, field grass, greenstreet grass, park grass, **pool water**, recreation grass and bare ground, because the texture catalogue holds walls, roofs, roadway and floors and no photographic set for any of them (J40). On a sheet that is almost entirely park, that is most of the ground.
* **One of three tiles in range has no structures file.**
* **23 props across five kinds in range have no asset** — 11 misc structures, 5 drinking fountains, **4 parks buildings**, 2 memorials, 1 artwork.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| no colour on the pavilion | the builder assigns `concrete` to the columns, ring beam and base and `steel_dark` to the ring's steel, and no colour anywhere; the 2015 repaint this photograph shows is not in the model. This is what drives chroma to 0.258 of the photograph's | **geometry — open, and it is one material assignment per member** |
| no cable net, no sawtooth brackets | a radial suspension net and a truss bracket are not classes this build models | geometry |
| the observation towers are not in the frame | they are built, on a separate polygon, and from this eye point they fall behind the tent's base drum or outside the picture; the frustum reports the composite's centroid 178.4 m away at 30.9° off axis rather than the towers' own position (J88) | verification — the record cannot say which |
| 1 pedestrian in a park on a Sunday | the crowd's walkable test reads sidewalk, median, plaza and crosswalk out of the road network's pavement export; a park path is not a surface class and a lawn is not walkable, so 59 of the park's people were dropped where they stood (J101) | **verification — open (J101)** |
| 0 kit pieces drawn | all 858 in range were suppressed under landmark shells | declared decision |
| 1,131 of 1,280 trees a substituted species | the street-tree and OSM species lists do not cover this park's stock and the nearest modelled species is used, counted rather than hidden | data — declared, counted |
| p50 1.328, sd 0.834 | the photograph is developed 0.636 stops **below** the grey convention for a bright October sky and the render 0.236 above it (J83) | reference |
| no cloud | nothing in this build reads a historical sky | reference — no source exists |
| under-fraction 0.418 beyond 400 m | the terrain grid coarsens to 40 m at the edge of the scene and the park builder drapes on its own heightmap; the redrape closes the near field to 0.0 and leaves this tail (J71) | geometry — open, bounded |
| ten park surface kinds flat | the texture catalogue has no photographic set for clay, grass, court, pool water or bare ground (J40) | data — declared, named on the sheet |
| one of three tiles without a structures file | that tile is unbuilt | data — open |
| 23 props across five kinds unmapped | no asset exists for those kinds, parks buildings among them | data |
