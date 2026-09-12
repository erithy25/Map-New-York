# Pier 57 (Hudson River Park)

`landmark_pier_57` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Chelsea Manhattan Apr 2026 105.jpg by Epicgenius, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2026-04-16 18:17:33, 1920x1440. [Commons page](https://commons.wikimedia.org/wiki/File:Chelsea_Manhattan_Apr_2026_105.jpg) — the photograph's own view direction is derived from the image at **high** confidence. It is a straight-on view of the shed's brick elevation, with the incised lettering *MARINE & AVIATION PIER 57* and *DEPARTMENT OF MARINE AND AVIATION NEW YORK*, a flag on a bishop's-crook lamp standard, the market entrance under a *PIER 57* sign, and parked cars along the kerb.

**Camera** — 40.743573, -74.008412 (NYC_TM -4928, 4894) at z 3.9 m NAVD88 | azimuth 262.8°, pitch −0.3° | 35 mm on 36 mm (54.4° horizontal, landscape) | 1208x906. The camera stands on **this photograph's own EXIF GPS**, **83.7 m** from the item's recorded viewpoint; the item's recorded azimuth is 240.0°, **22.8° away**. The walk then **moved the camera 52.7 m** onto the nearest surveyed crosswalk polygon: the recorded viewpoint is boxed in, closed off **48 m ahead** against the **76.1 m** this frame needs. From there the view is clear for **81.5 m**, **nothing built stands within 20 m of the lens**, and the nearest simulated agent is `agent_veh_ambulance_type1_fdny_739` **12.8 m** away, measured after the cull over the observer. The ground under it reads 2.331 m NAVD88 from the 2 m heightmap, 16 samples within 5 m, range 2.3 to 2.4 m.

**Sun** — azimuth 271.8°, elevation **14.0°** at 2026-04-16T18:17:33−04:00, from the photograph's own **EXIF DateTimeOriginal**; **540.5 W/m²** direct normal — the lowest irradiance on any daylight sheet written so far — sky at strength 0.0481, Filmic, **+2.89 stops** metered and unclamped against a linear median of **0.024356** and a target of **0.18**. The physical rule would have given **1.62 stops**, so even the physical rule wanted a lift here: a 14° Sun due west at a quarter past six in April is a low, weak, almost head-on light.

**In the scene** — 4,500,103 triangles: 4 building tiles (143,412 tris, 0 missing, 0 LOD-substituted), 4 landmark models of which 1 can fall inside the 54.4° frame, 19,640 pavement polygons, 2,320 props, 11,345 kit pieces, 13 park-ground meshes, 35,460 triangles of structures over 4 tiles with **none missing**, 54 vehicles and 423 people.

## Verdict — the frame was aimed one metre above the ground 172 m away, so half the sheet is crosswalk paint

**The aim is the whole story.** The object standing at Pier 57's coordinate is `lm_c_pier_57.1`, and the probe measured it at **2.01 m** above a ground of 2.19 m — the pier deck. The catalogue's own entry for `c_pier_57` is **19.3 m** tall and its origin stands **15.2 m** away, so the shed the photograph is a picture of is fifteen metres from the point the item records. The framing then follows the deck: `subject_aimed_at` reads *the subject's mid-height, **1.0 m** above its ground*, the pitch came out at **−0.3°**, and with the subject 172.4 m off, an optical axis pointed one metre above the ground at that range is an axis pointed at the road. The published render is a wide asphalt apron with crosswalk bars running away in perspective across the bottom half, a white box truck at close range, a yellow taxi behind it, and a small glazed building with four people beside it on the left. The brick shed, its lettering and its market entrance are not in the picture.

**The visible fraction is 0.769 and it is a fraction of a slab.** Ten of thirteen rays are clear, **ten land on the subject**, none goes into nothing — and every one of them lands on `lm_c_pier_57.1`, the 2 m deck, the first at **52.3 m**. Nine of the ten meet that fabric nearer than the recorded distance. Because the deck measures 2.0 m, under the pass's 12 m floor, the ray fan was built from the floor rather than from the subject, which the record states. So a reader who sees **0.769** has been told that three quarters of the subject is visible, and what is visible is a pier deck seen edge-on from 52 m (J94, J96).

**Two of the measured ratios run the unusual way, and the crosswalk explains both.** The render has **more** contrast than the photograph — sd **0.2993** against **0.2357**, a ratio of **1.27** — and a brighter midtone, p50 **1.147**, mean **1.323**, with p95 at **0.9882**, all but clipping. White thermoplastic bars on dark asphalt under a low Sun are as much range as a frame can hold, and they fill half of it. Against that, chroma **0.0372** against **0.1462**, a ratio of **0.254**: the photograph's warm brick, its flag, its blue evening sky and its street trees are all absent from a frame of grey asphalt and white paint.

**One unexplained thing in the picture.** There is a small dark blob in the sky above the horizon, upper middle of the render, which nothing in the record accounts for: no emissive, no prop, no landmark member is reported at that bearing. It is named here rather than passed over, because a published comparison frame should not contain a mark whose cause the record cannot state.

## What matches

* **Every tile in range has its structures file** — 4 tiles, **0 without a file**, 35,460 triangles, on a waterfront that is piers and a seawall. The only sheet written so far with no structures shortfall at all.
* **Nothing was capped in the props** — **2,320 placed of 2,489 in range**, **0 dropped for budget** — and the kit came within 12 % of complete, **11,345 of 12,866 in range** against a **1,855,519-triangle** budget, the largest kit budget on any sheet written so far.
* **The pavement is a Chelsea crossing** — 19,640 polygons with **0 dropped**, including 8,043 white markings and **540 crosswalk** polygons, and the markings in the frame are the continental bars J52 built rather than one painted rectangle.
* **The crowd is a Hudson River Park crowd** — **423 people** against 54 vehicles, and an **FDNY ambulance** in the fleet.
* **The trees are real trees** — 1,467 placed, **36** drawn from modelled branches within 120 m, 1,431 as impostor cards out to 727 m, **11** of the cards procedural canopy stems inside mapped woodland (Stage 55).
* **The park ground is exact near the camera** — within 150 m, **408 samples**, an under-fraction of **0.0**, a median clearance of **0.201 m**, a worst of **+0.111 m**, no z-fighting.
* **The development was honest about a hard light** — +2.89 stops metered where the physical rule itself wanted 1.62, on 540.5 W/m² at a 14° Sun.

## What does not match

* **The shed is not in the frame.** No brick elevation, no incised lettering, no flag, no market entrance.
* **The frame was aimed 1.0 m above the ground at 172 m**, because the object at the subject's coordinate is a 2 m deck and the 19.3 m shed is 15.2 m away (J94).
* **The visible fraction of 0.769 is a fraction of that deck**, not of the building the sheet names.
* **Half the render is roadway**, a consequence of the 52.7 m move onto a crosswalk plus the near-level aim.
* **A quarter of the photograph's colour** — chroma **0.254** — and **1.27×** its contrast, both driven by paint on asphalt replacing brick, trees and sky.
* **No cloud, and no contrails.** The reference's sky carries two long contrails across it; nothing in this build reads a historical sky.
* **The render is brighter at the midtone** — p50 **1.147**, mean **1.323**. The photograph's median sits **0.177 stops below** the grey convention and the render's **0.247 above**, a **+0.424-stop** difference (J83).
* **1,131 kit pieces were suppressed** under landmark shells and **59 props were dropped on a suppressed building**.
* **473 of the 1,467 trees are a substituted species** and **2** are scaled outside the allowed band; 8 impostor cards were dropped.
* **17 props across seven kinds in range have no asset** — **7 drinking fountains**, 3 artworks, 2 misc structures, 1 parks comfort station, 1 payphone, 1 real-time information sign, 1 vending machine.
* **Six park surface kinds keep the builder's flat colour** — hard sport court, greenstreet grass, park grass, pool water, recreation grass and bare ground (J40).
* **2,655 agents were dropped** — 834 pedestrians at the agent triangle budget, 705 outside the radius, **425 in the carriageway without crossing**, 368 vehicles outside the radius, 153 vehicles at the budget, **128 off a walkable surface** on a waterfront park (J101), **25 inside a building**, 10 vehicles off the carriageway, 8 pedestrians over the observer, 4 riderless bodies, 3 vehicles over the observer.
* **A dark blob in the sky** that the record does not explain.
* **Beyond 400 m the park ground reads under the terrain on 0.1504 of 1,456 samples**, worst **−3.755 m**, with a z-fighting fraction of **0.0385**; between 150 and 400 m it is **0.1891** over 878 samples. The redrape moved **83,308** vertices, up to 3.288 m up and 3.503 m down.
* **The windows are drawn on the shells, not cut** (Stage 34 / J51).

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the shed is not in the frame | the object at the subject's coordinate is a 2.01 m pier deck, so the aim point is 1.0 m above the ground and a level axis at 172 m looks at the road; the 19.3 m shed stands 15.2 m from that coordinate (J94, J96) | **data — open, the coordinate; verification — open, the aim follows it** |
| the visible fraction reads 0.769 of a slab | the sightline lands on the deck and counts it as the subject, and the fan came from the 12 m floor because the subject measures 2.0 m (J78, J94) | verification — true and misleading |
| half the frame is roadway | the recorded viewpoint was boxed in at 48 m against 76.1 m, so the walk moved 52.7 m onto a crosswalk polygon — the best surveyed surface with a clear view (J79) | verification — the rule working, with a bad result |
| chroma 0.254, sd 1.27, p50 1.147 | white thermoplastic on asphalt under a 14° Sun replacing brick, trees and an evening sky; the photograph is developed 0.177 stops below the grey convention and the render 0.247 above (J83) | reference + verification |
| no cloud, no contrails | nothing in this build reads a historical sky | reference — no source exists |
| 1,131 kit pieces and 59 props suppressed | the landmark shell replaces the tile's buildings and takes their kit and kerb furniture with it | declared decision |
| windows drawn on the shell | Stage 34 / J51, measured at +48 GB | declared decision — physically impossible here |
| 473 of 1,467 trees a substituted species | the species lists do not cover this stock and the nearest modelled species is used, counted rather than hidden | data — declared, counted |
| 17 props across seven kinds unmapped | no asset exists for those kinds | data |
| 128 pedestrians off a walkable surface | the crowd's walkable test reads only the road network's sidewalk, median, plaza and crosswalk; a park esplanade is not a surface class (J101) | verification — open (J101) |
| six park surface kinds flat | the texture catalogue has no photographic set for court, grass, pool water or bare ground (J40) | data — declared, named on the sheet |
| a dark blob in the sky | unexplained; no emissive, prop or landmark member is recorded at that bearing | **verification — open, and unaccounted for** |
| under-fraction 0.1891 mid-range, 0.1504 far | the park builder drapes on its own heightmap and the scene's differs; the redrape closes the near field to 0.0 and leaves this tail (J71) | geometry — open, bounded |
| 423 people of 1,933 asked | the agent triangle budget plus the placement rules, each with its own count | performance + verification |
