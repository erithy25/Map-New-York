# Queens-Midtown Tunnel Manhattan portal

`landmark_queens_midtown_tunnel_portal` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Saint Vartan Park, July, Morning (19391466048).jpg by Jeffrey Zeldman from Manhattan, USA, CC BY 2.0 (https://creativecommons.org/licenses/by/2.0), taken 2015-07-10 09:04, 1920x1080. [Commons page](https://commons.wikimedia.org/wiki/File:Saint_Vartan_Park,_July,_Morning_(19391466048).jpg) — the photograph's own view direction is derived from the image at **high** confidence. **Its filename says what it is: St Vartan Park on a July morning.** The frame is a London plane trunk, a chain-link fence smothered in ivy, deep shade, and the park's own regulations sign reading *ST. VARTAN PARK*. There is no tunnel portal in it.

**Camera** — 40.745029, -73.973457 (NYC_TM -1981, 5001) at z 5.7 m NAVD88 | azimuth 48.8°, pitch 0.0° | 35 mm on 36 mm (54.4° horizontal, landscape) | 1280x720. The camera stands on **this photograph's own EXIF GPS**, **195.1 m** from the item's recorded viewpoint; the item's recorded azimuth is 120.0°, **71.2° away**. The lens was **not widened** and the axis was left **level**, because the highest built thing at the subject's coordinate stands **−4.8 m** below the ground there — below the 2 m at which the probe will aim or frame. The eye point **stands on `t_-2_5_park_skating_rink_ice`** and the walk left it there, this being the photograph's own GPS rather than a nominal viewpoint standing for a deck (J65). The view azimuth is clear for **104.2 m** against an **80.0 m** requirement, the nearest built thing in the frame is `t_-2_5_park_park_ground_grass` **3.2 m** away, and no simulated agent stands within 60 m. The ground under it reads 4.122 m NAVD88, the 10th percentile of 113 samples within 12 m, range 4.08 to 4.74 m.

**Sun** — azimuth 91.6°, elevation 37.2° at 2015-07-10T09:04:00−04:00, from the photograph's own **EXIF DateTimeOriginal** to the minute; 824.8 W/m² direct normal, sky at strength 0.0341, Filmic, **+0.11 stops** metered and unclamped against a linear median of **0.166848** and a target of **0.18**. The physical rule would have given **0.21 stops**. The scene arrived essentially at a photographable level on its own — the smallest development on any sheet written so far, and the figure matters for what follows.

**In the scene** — 4,500,127 triangles: 4 building tiles (164,834 tris, 0 missing, 0 LOD-substituted), 5 landmark models of which 1 can fall inside the 54.4° frame, 35,703 pavement polygons, 921 props, 6,435 kit pieces, 16 park-ground meshes, 5,108 triangles of structures, 89 vehicles and 433 people.

## Verdict — a tunnel portal that is 4.8 m below its own ground, a photograph of a fence in deep shade, and a three-stop exposure gap that belongs entirely to the photograph

**The probe is right and it has nothing to work with.** The highest built thing at the portal's coordinate is `lm_b_queens_midtown_portals.44` at **−4.8 m** relative to the ground — the portal really is below grade, which is what a tunnel mouth is. So the record refused to aim or frame by it, left the axis level, and **tested no sightline at all**: this sheet carries no `subject_visible_fraction`. It is one of the seven sheets in that state (J96), and unlike most of them the reason is correct rather than a bad coordinate. **36 of 43** probe rays found fabric. The nearest catalogue origin is `c_un_headquarters` at **429.2 m**, far past the 120 m the old rule looked in, so nothing was inherited.

**The reference is a picture of a fence.** The photograph is of St Vartan Park, 195 m from the portal, looking at a plane trunk and an ivy-covered chain-link fence in the shade. The render, from that same spot looking at the portal's bearing, is a competent park frame: plane trees, benches, lamp standards, a lawn, brick apartment blocks, a street with taxis, and the **United Nations Secretariat slab** 696.8 m off at 7.9° off axis, which the frustum names and which is in the picture. Two true views from one spot, of two different things.

**The sheet's largest number is an exposure gap, and it is the photograph's choice.** The reference's own median sits **2.859 stops below** the grey convention — the deepest under-exposure of any reference in the pass — because the photographer exposed for a bright July sky and let the shade under the plane go almost black. The render's median sits **0.233 above** it. The difference is **+3.092 stops**, the largest gap in that direction anywhere in the pass, and it produces a p50 ratio of **2.906**: the render reads nearly three times brighter at the midtone. **The development is not the cause.** It contributed **+0.11 stops**, less than any other sheet written so far, and the physical rule wanted *more* than the meter gave. This is the cleanest demonstration in the pass of what J83 exists to say: a mean or median ratio is an exposure comparison first, and here it is nothing else.

**And the render draws ice in July.** The eye point stands on a surface the planimetric survey codes as a skating rink — checked in the parks source: one such surface in that tile, named **St. Vartan Park**, **323.2 m²** — and the park-ground builder keeps its own flat colour for rink ice because the texture catalogue has no photographic set for it (J40). So the pale off-white plane across the render's lower left is a 323.2 m² ice surface on 10 July. The surface class carries no season, and nothing in the build makes a rink read as anything else in summer.

## Measured for this assessment

| figure | how |
|---|---|
| one skating-rink surface in tile `t_-2_5`, named St. Vartan Park, 323.2 m² | read from `data/processed/parks/surfaces.parquet` by its `tile`, `kind_name`, `name` and `area_m2` columns — so the record's `standing_on` is correct and the ice is a real surface class, not a joined-mesh artefact |
| the largest positive exposure gap in the pass | ranked `frame_stats.json` `render_over_reference.exposure_offset_stops` over every record carrying `scene.structures`; the two larger gaps in absolute terms run the other way (The Shed at −5.180, 30 Hudson Yards at −4.303) |

## What matches

* **The probe's refusal is correct.** A tunnel mouth is below grade, the record measured **−4.8 m**, and it declined to frame by it rather than inventing a height (J96).
* **The instant is the photograph's own, to the minute**, and the development is the smallest in the pass at **+0.11 stops** against a physical rule of 0.21.
* **The UN Secretariat is in the frame where the frustum says it is** — 696.8 m, 7.9° off axis.
* **The park is furnished as a Murray Hill park** — **284 Citi Bike units**, 92 street lamps, **63 benches**, 72 manholes, 44 hydrants, 21 waste baskets, 3 bus shelters, 2 LinkNYC kiosks, and **72 lamps on the park post** rather than a cobra head.
* **Murray Hill is paved as Murray Hill** — 35,703 pavement polygons with **0 dropped**, including **17,413 white markings**, 4,291 sidewalk, 914 crosswalk and 478 plaza.
* **The crowd is a weekday morning crowd** — 433 people and 89 vehicles, with **21 yellow taxis and 15 boro taxis** in the fleet on a Friday in July.
* **Only 9 of the 278 trees are a substituted species** and **0** are out of band — the lowest substitution share on any sheet written so far, because Murray Hill's street trees are surveyed rather than inferred: **0** procedural canopy stems in this frame.

## What does not match

* **The reference is a photograph of a park fence, not of the tunnel portal.** No comparison of the subject is possible.
* **No sightline exists on this sheet** (J96).
* **A p50 ratio of 2.906 and a mean ratio of 1.487**, both of which are the photograph's own **−2.859-stop** exposure against the render's **+0.233** (J83).
* **A 323.2 m² skating rink is drawn as ice on 10 July.** The surface class has no season and the catalogue has no rink texture (J40).
* **Props were capped to one in five** — **921 placed of 4,475 in range** at a **1,265,172-triangle** budget, **3,262 dropped for budget**, **2,237** of them tree rows, and 12 impostor cards dropped. Murray Hill's street trees are surveyed and most of them were not drawn.
* **Kit was capped to one piece in eight** — **6,435 of 52,952 in range** at a **1,264,606-triangle** budget, 5,647 of them windows; the openings are not cut (Stage 34 / J51).
* **One of three tiles in range has no structures file**, and the scene carries only **5,108 triangles** of structures — over a river tunnel, the Park Avenue tunnel and the Lexington Avenue line.
* **16 props across eight kinds in range have no asset** — 4 misc structures, 4 vending machines, 3 drinking fountains, 1 artwork, 1 billboard, 1 memorial, 1 parks comfort station, 1 real-time information sign.
* **The park ground reads under the terrain even near the camera** — within 150 m, an under-fraction of **0.0556** over **1,942 samples** with a worst of **−0.682 m**, the first non-zero near-field reading on any sheet written so far. Between 150 and 400 m it is **0.3741** over 572 samples, worst **−3.659 m**, the worst mid-field reading written so far; beyond 400 m **0.2539** over 1,276 samples, worst **−4.769 m**. The redrape moved **80,439** vertices, up to 0.871 m up and 1.028 m down.
* **Six park surface kinds keep the builder's flat colour** — hard sport court, park grass, recreation grass, pool water, **rink ice** and bare ground (J40).
* **2,738 agents were dropped** — 954 pedestrians outside the radius, 564 at the agent triangle budget, 435 vehicles outside the radius, 344 vehicles at the budget, **280 pedestrians in the carriageway without crossing**, **125 off a walkable surface** in a park (J101), 29 riderless bodies, 7 vehicles off the carriageway.
* **No cloud**, although the reference's sky is barely visible through the canopy.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the reference is a photograph of a fence | the chooser accepted a photograph whose own filename names a park rather than the subject; it is a true photograph from the recorded neighbourhood and not a photograph of the item | **verification — open, the pairing is the fault** |
| no sightline was tested | the portal stands 4.8 m below its own ground, under the 2 m at which the probe will aim or frame, and a tunnel mouth genuinely is below grade (J96) | verification — declared, and correct |
| p50 2.906, mean 1.487 | the photograph is developed 2.859 stops below the grey convention for a bright July sky and the render 0.233 above it; the metered development contributed +0.11 stops, less than any other sheet (J83) | reference — and the cleanest instance of it in the pass |
| ice on a July morning | the park surface class carries no season, and the catalogue has no photographic set for rink ice so the builder's flat colour stands (J40) | **data — open, and the class needs a season** |
| 921 props of 4,475, 2,237 tree rows dropped | the props triangle budget at 1,265,172 | performance |
| 6,435 kit pieces of 52,952 | the kit triangle budget at 1,264,606 | performance |
| windows drawn on the shell | Stage 34 / J51, measured at +48 GB | declared decision — physically impossible here |
| 5,108 triangles of structures, one tile without a file | that tile is unbuilt, over a river tunnel and two rail lines | **data — open** |
| 16 props across eight kinds unmapped | no asset exists for those kinds | data |
| an under-fraction of 0.0556 within 150 m | the park builder drapes on its own heightmap and the scene's differs; this is the first sheet where the redrape does not close the near field, and the mid-field tail reaches −3.659 m (J71) | **geometry — open, and worse here than anywhere written so far** |
| six park surface kinds flat | the texture catalogue has no photographic set for court, grass, pool water, rink ice or bare ground (J40) | data — declared, named on the sheet |
| 433 people of 1,793 asked, 125 off a walkable surface | the agent triangle budget plus the crowd's walkable test, which reads only the road network's surfaces (J101) | performance + verification |
