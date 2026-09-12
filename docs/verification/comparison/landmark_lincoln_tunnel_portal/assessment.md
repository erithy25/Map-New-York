# Lincoln Tunnel Manhattan portal

`landmark_lincoln_tunnel_portal` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Lincoln Tunnel Land Ventilation Building.jpg by Kidfly182, CC BY 4.0 (https://creativecommons.org/licenses/by/4.0), taken 2024-08-10 12:57:29, 1920x863. [Commons page](https://commons.wikimedia.org/wiki/File:Lincoln_Tunnel_Land_Ventilation_Building.jpg) — the photograph's own view direction is derived from the image at **high** confidence.

**Camera** — 40.75854, -73.99995 (NYC_TM -4202, 6532) at z 7.7 m NAVD88 | azimuth 358.3°, pitch +3.3° | 35 mm on 36 mm (54.4° horizontal) | 1280x576. Position and heading both come from the photograph: its own EXIF camera GPS, **156.7 m** from the item's recorded viewpoint, and 358.3° is the bearing from there to the subject. The item's recorded azimuth of 297.2° is **61.1° away**. The recorded viewpoint was **boxed in** — the azimuth closed **35 m** ahead against the 64.7 m needed — so the camera was **moved 33.1 m** onto the nearest surveyed crosswalk, scored on the subject's sightline. From there the azimuth is clear for **77.6 m**, the nearest built thing is `lm_b_lincoln_tunnel_portals.31` **16.6 m** away, and **a simulated taxi stands 8.9 m** from the lens. Ground under the camera reads **6.094 m** NAVD88, the 10th percentile of **113** heightmap samples within 12 m, range 6.0 to 6.47 m.

**Sun** — azimuth 177.9°, elevation 64.5° at 2024-08-10T12:57:29−04:00, from the photograph's own **EXIF DateTimeOriginal**; 928.7 W/m² direct normal, sky at strength 0.0307, Filmic, **+2.55 stops and not clamped**. The linear frame's median is **0.030771** against a middle-grey target of 0.18; the physical rule would have given **0.0 stops** (J83).

**In the scene** — 4,500,035 triangles: 6 building tiles (178,338 tris, none missing, none LOD-substituted), **6 landmark models and 0 of them inside the 54.4° frame**, 29,146 pavement polygons with **0 dropped**, 1,435 props, 7,951 kit pieces, 17 park-ground meshes over 175 surfaces, 4 structures tiles (**123,024 tris**) with 2 without a file, 77 vehicles and 259 people, terrain 89,416 tris at 2.0 m near / 40.0 m far with no holes.

## Verdict — the second exact 1.000 in this pass earned from a tile mesh: thirteen of thirteen rays land on `t_-5_6_tan_brick`, a joined surface 959 metres across, and the ventilation building is not identifiable in the frame

**`subject_visible_fraction` is 1.000.** Thirteen rays, **13 clear, 13 on the subject**, nothing blocked, nothing into nothing. And the object every one of them struck is `t_-5_6_tan_brick` — **a tile mesh whose extent is 959.4 m by 735.2 m**: every tan-brick surface in that tile joined into one. The ray that gets nearest lands **80.2 m** out. The record names the object, says a tile mesh's extent is not the subject's, and refuses to use it (J74) — and the sightline still counts hits on it as hits on the Lincoln Tunnel's ventilation building.

**This is the same fault as `landmark_castle_williams`**, where 13 of 13 rays on an island-wide roof-membrane mesh produced 1.000 with no fort in the frame. Two sheets in one pass now carry a perfect score earned from a tile mesh, and a third — Rockefeller Center — carries a 2-of-43 probe for the same reason. The repair is the same: the sightline must not be allowed to aim at, or count, a joined tile surface.

**What the frame shows is a street.** A yellow taxi in the foreground, a brick block with punched windows, a pale grey slab behind it, pedestrians, traffic cones, and the far kerb. The reference is the Land Ventilation Building: a brick Art Deco tower with deep vertical window slots, a stepped crown and sculpted panels at the top. None of that reads in the render, and the frustum agrees — **0 of 6** landmark models fall inside the frame.

**The deepest terrain under-reading in the pass sits on this sheet.** Beyond 400 m the park surface reaches **−10.821 m** with a first percentile of **−7.143 m** and an under-fraction of **0.3217** over 1,669 samples, after a redrape that moved 127,584 vertices (J85). That band is the Hudson Yards platform and the tunnel's own approach cut.

**The tonal pairing is decent and the colour is not.** Mean **0.926×**, median **0.926×**, with the two development offsets **0.239 stops** apart — but chroma **0.0889** against **0.1953**, a ratio of **0.455**, because the reference is warm brick against a deep August blue and the render's frame is grey concrete with one yellow car in it.

## What matches

* **The record names the tile mesh and refuses its extent** (J74), which is the only reason the 1.000 can be read for what it is.
* **The clearance walk worked as designed**: a 35 m closure detected, 33.1 m onto a real surveyed crosswalk, scored on the subject's sightline (J79).
* **The development is metered and unclamped**, +2.55 stops from a median linear luminance of 0.030771.
* **Mean and median are both within 8 per cent**, and the two development offsets are 0.239 stops apart (J83).
* **Structures carry 123,024 triangles** over 4 tiles — the tunnel's approach ramps and the rail-yard structures.
* **The pavement is complete**: 29,146 polygons, **0 dropped**, including 13,842 white markings, 5,098 roadbed, 4,322 sidewalk, 3,275 curb, 1,052 parking lot and 660 crosswalk.
* **The taxi, the cones and the crossing crowd** read as Tenth Avenue at midday, and 58 of 259 people are at LOD1.

## What does not match

* **A visible fraction of 1.000 measured against a tile mesh 959 m across** — the second such false perfect score in the pass (J94).
* **No landmark model falls inside the frame** — 6 placed, **0 in the cone**.
* **The ventilation building's tower, window slots and crown are not identifiable.**
* **Chroma is 0.455 of the photograph's**, 0.0889 against 0.1953.
* **Beyond 400 m the park surface reaches −10.821 m**, under-fraction **0.3217** over 1,669 samples — the deepest under-reading in the pass (J85).
* **Sixty per cent of the props are missing**: 1,435 placed of **3,575 in range**, with **1,807 dropped for the triangle budget** of 1,211,154, **132** dropped on suppressed buildings and 3 cards dropped.
* **1,452 tree rows did not fit** that budget; 52 of the 440 cards are procedural canopy stems and 7 trees are drawn from modelled branches.
* **7,951 of 16,733 kit records were drawn**, capped at a 1,165,161-triangle budget, with 1,075 suppressed.
* **A taxi stands 8.9 m from the lens** (J91).
* **Two of 6 structures tiles have no structures file.**
* **Forty-two props across eight kinds were wanted in range and have no asset**, **32 of them misc structure** — at a tunnel portal, the toll plaza canopies and the vent stacks.
* **Four park-ground surface kinds fall back to the builder's flat colour** (J40).
* **Eighteen vehicles and 5 pedestrians were placed inside buildings** and dropped rather than drawn, along with 377 pedestrians in the roadway while not crossing and 129 with no sidewalk under them.
* **The crowd is an eighth of the ask**: the table wanted 835 vehicles and 1,961 people; 988 and 2,097 were simulated and **2,749** dropped.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| a 1.000 verdict measured on a tile mesh 959 m across | the sightline aims at and counts hits on whichever object stands at the subject's coordinate, and here that object is every tan-brick surface in the tile joined into one; the probe's own note says a tile mesh's extent is not the subject's, and the sightline ignores it (J94) | **verification — open, and the second false 1.000 in the pass** |
| no landmark in the frame | the frustum found 0 of 6 in the cone after the 33.1 m move changed the bearing | verification — open |
| the ventilation building is unidentifiable | the portal structures are modelled as approach ramps and walls; the Art Deco vent tower with its slotted windows and sculpted crown is not authored as a distinct object | geometry — declared scope |
| chroma 0.455× | warm brick against deep August blue in one frame, grey concrete in the other | reference + **J66 remainder** |
| −10.821 m beyond 400 m, 0.3217 under | the terrain grid coarsens to 40 m beyond the near band across the Hudson Yards platform and the tunnel's approach cut (J85) | **geometry — open, deepest in the pass** |
| 1,435 props of 3,575 in range, 1,452 tree rows dropped | the props triangle budget at 1,211,154, which dropped 1,807, plus 132 on suppressed buildings | **performance** |
| 7,951 kit pieces of 16,733 in range | the kit triangle budget at 1,165,161, plus 1,075 suppressed | performance |
| a taxi 8.9 m from the lens | the 8 m nothing-built rule applies to geometry and not to the crowd (J91) | verification — open |
| 2 of 6 structures tiles without a file | no structures file was built for those tiles | **data — open, two tiles unbuilt** |
| 42 props unmapped, 32 of them misc structure | no asset exists for those kinds, and at a tunnel portal that kind is the toll canopies and vent stacks | **data — open** |
| 23 agents dropped inside buildings | the road and sidewalk graph runs through building footprints at the portal approach | **data — open, measured** |
| four park surface kinds flat-coloured | the texture catalogue has no photographic set for any of them (J40) | **declared decision** |
