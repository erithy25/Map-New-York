# 4 Times Square (Condé Nast Building)

`landmark_four_times_square` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Condé Nast Building Times Square.jpg by Kidfly182, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2021-08-25 12:34:41, 1920x1440. [Commons page](https://commons.wikimedia.org/wiki/File:Cond%C3%A9_Nast_Building_Times_Square.jpg) — the photograph's own view direction is derived from the image at **high** confidence.

**Camera** — 40.75642, -73.98656 (NYC_TM -3067, 6299) at z 17.4 m NAVD88 | azimuth 119.0°, pitch +41.4° | 18 mm on 36 mm (90.0° horizontal, 74° vertical) | 1208x906. Position and heading both come from the photograph: its own EXIF camera GPS, **155.5 m** from the item's recorded viewpoint, and 119.0° is the bearing from there to the subject. The item's recorded azimuth of 200.0° is **81.0° away**. The lens was **widened from 35 mm to the 18 mm floor** and the axis tilted **+41.4°**, and the top of the subject is still cut off: `lm_c_times_square.11` stands 244 m above the lens at 71 m, **74° above the horizon**. **The verticals converge, so this frame is not comparable with the photograph on proportion.** The recorded viewpoint was **boxed in** — the azimuth closed **7 m** ahead against the 35.3 m needed — so the camera was **moved 37.8 m** onto the nearest surveyed plaza polygon, scored on the subject's sightline (11 of 13 rays at the point chosen). From there the azimuth is clear for **60 m** and the nearest built thing is `prop_lamp_cobra_davit_16` **14.8 m** away. The record also states that **a simulated pedestrian stood 0.1 m from the lens** and was culled for being over the observer; the nearest surviving agent is 9.2 m away. Ground under the camera reads **15.789 m** NAVD88, the 10th percentile of **113** heightmap samples within 12 m, range 15.7 to 16.09 m.

**Sun** — azimuth 168.8°, elevation 59.3° at 2021-08-25T12:34:41−04:00, from the photograph's own **EXIF DateTimeOriginal**; 917.0 W/m² direct normal, sky at strength 0.0311, Filmic, **+1.07 stops and not clamped**. The linear frame's median is **0.08577** against a middle-grey target of 0.18 (J83); the physical rule would have given 0.0.

**In the scene** — 4,500,038 triangles: 4 building tiles (247,682 tris, none missing, none LOD-substituted), 4 landmark models of which 2 fall inside the 90.0° frame — **neither is the subject** — 26,252 pavement polygons with **0 dropped**, 1,426 props, 6,211 kit pieces, 13 park-ground meshes over 75 surfaces, **0 triangles of structures**, 50 vehicles and 239 people, terrain 86,520 tris at 2.0 m near / 40.0 m far with no holes.

## Verdict — the towers are the right shape from the right place and they carry no signs at all, on the one block in the city where the signs are the architecture, and 78,921 kit records were in range against a budget that drew 6,211

**This is a good upward frame.** The camera was boxed in at 7 m, moved 37.8 m to a surveyed plaza, and scored **11 of 13 rays on the subject** — visible fraction **0.846**. The probe measured **245.56 m** over **43 of 43** rays with a plan extent of **45.7 m by 45.3 m**, correctly refusing the 365.8 m the Times Square composite entry carries 61.0 m away (J74). And the render shows what the photograph shows in kind: two glass towers converging upward, a curved corner mass on the right with a stone base, a window grid running up both.

**What it does not show is a single sign.** The reference's crown carries a billboard, its shaft carries a vertical H&M sign, and a signal mast with five heads crosses the foreground. The render's towers are blank glass from base to cut-off. There are **39 billboard kit pieces** in this scene, so the class is placed somewhere in range — just not on these faces.

**The kit shortfall here is the largest in the pass.** **78,921** kit records were in range and **6,211** were drawn, capped at a 1,121,688-triangle budget, with a further **10,951 suppressed** where landmark shells stand in place of the tile's buildings. One piece in thirteen of what the classifier found. On a block of curtain-walled towers seen from below, that is why the glass reads as a flat grid rather than as mullions, spandrels and reveals.

**A pedestrian stood a tenth of a metre from the lens.** The record says so, and says it was culled for being over the observer — so the drawn frame is clean, and the 8 m nothing-built rule still does not apply to the crowd (J91). This is the closest agent recorded anywhere in the pass.

**The colour and contrast gap is signage and sky.** Chroma **0.0635** against **0.1503** (**0.422×**), contrast **0.736×**, and the render is brighter — mean **1.227×**, median **1.236×** — with the two development offsets **0.655 stops** apart (J83).

## What matches

* **The massing and the view are right**: two converging glass towers and a curved corner with a stone base, from the photograph's own position.
* **The sightline is strong**: 13 of 13 rays clear, **11 on the subject**, visible fraction 0.846.
* **The probe is exact and the catalogue correctly refused**: 43 of 43 rays, 245.56 m, extent 45.7 m by 45.3 m (J74).
* **The clearance walk worked as designed**: a 7 m closure detected, 37.8 m onto real surveyed plaza, scored on the subject's sightline (J79).
* **The development is metered and unclamped**, +1.07 stops from a median linear luminance of 0.08577.
* **The record names the 0.1 m agent and the cull that removed it**, rather than reporting a clear frame.
* **The pavement is complete**: 26,252 polygons, **0 dropped**, including 9,929 white markings, 6,015 sidewalk, 4,607 roadbed, 3,243 curb, 1,610 plaza and 553 crosswalk.
* **Near-field ground is perfect**: within 150 m, **0.0** of 39 park-surface samples sit under the terrain.
* **Agents carry mixed detail**: 10 vehicles at LOD1, and of 239 people **55 at LOD1 and 1 at LOD0**.

## What does not match

* **No signage at all** on the subject or its neighbours, on the block where signage is the architecture.
* **6,211 kit pieces of 78,921 in range** — the largest shortfall in the pass — capped at 1,121,688 triangles with 10,951 more suppressed.
* **The top of the subject is cut off** at the 18 mm floor; the tower needs 74° of elevation at 71 m.
* **Neither landmark in the frustum is the subject** — the New York Public Library at 523.1 m and 30 Rockefeller Plaza at 633.1 m.
* **Eight of the 11 rays that scored 0.846 landed on fabric nearer than the recorded coordinate**, 51.5 m out against the subject's 79.3 m, because the Times Square composite contains both (the counting fault recorded on `landmark_central_park_tower`).
* **Chroma is 0.422 of the photograph's** and contrast **0.736×**.
* **No structures at all**: **0 tiles imported, 4 without a file, 0 triangles** — under the Times Square interchange.
* **Fifty-seven per cent of the props are missing**: 1,426 placed of **3,350 in range**, with **1,659 dropped for the triangle budget** of 1,188,675 and 22 on a suppressed building.
* **Not one of 169 trees is drawn from modelled branches**; **1,052 tree rows** did not fit the props budget, **0** of the cards are procedural canopy stems and **138** species were substituted.
* **Forty-one props across six kinds were wanted in range and have no asset**: 19 misc structure, 9 artwork, 4 drinking fountain, 4 memorial, 3 parks building, 2 passenger-information sign.
* **The crowd is a thirteenth of the ask**: the table wanted 1,305 vehicles and 3,211 people; 1,443 and 3,000 were simulated and **4,138** dropped — **1,393** pedestrians and 666 vehicles at the agent triangle budget, 1,056 pedestrians and 661 vehicles outside the radius, 243 pedestrians in the carriageway without crossing, 47 not on a walkable surface, 32 vehicles not on a carriageway, 22 pedestrians and 4 vehicles above the observer, and **30 riderless bodies**.
* **Four park-ground surface kinds fall back to the builder's flat colour** (J40).
* **Beyond 400 m the park surface sits under the terrain on 0.215 of 1,051 samples**, minimum −1.467 m (J85).

## Cause of each gap

| gap | cause | class |
|---|---|---|
| no signage on any face | signage on a landmark shell is not placed from any source, and the honesty rule forbids inventing copy (the data contract for the sign-face slots, DEVIATIONS B15a); 39 billboard pieces exist in range and none lands on these faces | **declared decision + geometry, open** |
| 6,211 kit pieces of 78,921 in range | the kit triangle budget at 1,121,688, plus 10,951 suppressed under landmark shells — the largest shortfall in the pass | **performance** |
| the top of the subject is cut off | 18 mm is the widest lens the comparison allows and the subject needs 74° at 71 m | **verification — declared limit** |
| 8 of 11 scoring rays on nearer composite fabric | the sightline counts a hit on any member of the Times Square composite as a hit on the subject | **verification — open** |
| chroma 0.422×, sd 0.736×, mean 1.227× | no signs, no sky and no painted metal in the render's frame, and 0.655 stops of development between the halves (J83) | consequence + reference |
| no structures on any tile | 4 tiles in range and none has a structures file | **data — open, four tiles unbuilt** |
| 1,426 props of 3,350 in range, 1,052 tree rows dropped | the props triangle budget at 1,188,675 | **performance** |
| 41 props across six kinds unmapped | no asset exists for those kinds | data |
| a pedestrian 0.1 m from the lens | the 8 m nothing-built rule applies to geometry and not to the crowd; the over-the-observer cull removed this one and the rule is still missing (J91) | verification — open |
| 239 people where the table asked 3,211 | the agent triangle budget plus the placement rules, each with its count | performance + verification |
| four park surface kinds flat-coloured | the texture catalogue has no photographic set for any of them (J40) | **declared decision** |
| 0.215 of far park ground under the terrain | the terrain grid coarsens to 40 m beyond the near band (J85) | geometry — open, measured |
