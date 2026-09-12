# Columbus Circle

`landmark_columbus_circle` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:March for our lives march passing Columbus Circle NYC (27123512198).jpg by Paul Wasneski, Public domain (https://commons.wikimedia.org/wiki/Commons:Licensing#Material_in_the_public_domain), taken 2018-03-24 14:26, 1920x1280. [Commons page](https://commons.wikimedia.org/wiki/File:March_for_our_lives_march_passing_Columbus_Circle_NYC_(27123512198).jpg) — the photograph's own view direction is derived from the image at **high** confidence.

**Camera** — 40.76855, -73.98168 (NYC_TM -2675, 7613) at z 25.5 m NAVD88 | azimuth 255.7°, pitch +34.3° | 18 mm on 36 mm (90.0° horizontal, 67° vertical) | 1280x854. Position and heading both come from the photograph: its own EXIF camera GPS, **58.0 m** from the item's recorded viewpoint, and 255.7° is the bearing from there to the subject, 3.1° from the item's own azimuth. The lens was **widened from 35 mm to the 18 mm floor** and the axis tilted **+34.3°**, and the top of the subject is still cut off: `lm_b_columbus_circle_monument.6` stands 235 m above the lens at 115 m, **64° above the horizon**. **The verticals converge, so this frame is not comparable with the photograph on proportion.** The camera was not moved — open air, azimuth clear for **80.8 m** against the 57.3 m needed — and the nearest built thing is `prop_lamp_cobra_davit_0` **10.1 m** away at −45°, with a taxi 11.3 m off at the same bearing. Ground under the camera reads **23.88 m** NAVD88 from 16 heightmap samples within 5.0 m, range 23.73 to 24.0 m.

**Sun** — azimuth 211.3°, elevation 46.5° at 2018-03-24T14:26−04:00, from the photograph's own **EXIF DateTimeOriginal (minutes)**; 873.9 W/m² direct normal, sky at strength 0.0324, Filmic, **+2.15 stops and not clamped**. The linear frame's median is **0.040579** against a middle-grey target of 0.18; the physical rule would have given **0.0 stops** (J83).

**In the scene** — 4,500,178 triangles: 5 building tiles (219,378 tris, none missing, none LOD-substituted), 6 landmark models of which 1 falls inside the 90.0° frame — the Hearst Tower, not the subject — 22,609 pavement polygons with **0 dropped**, 1,216 props, 6,499 kit pieces, 19 park-ground meshes over 270 surfaces with **2,814 faces cut** for landmark ground, 2 structures tiles (33,232 tris), 53 vehicles and 252 people, terrain 83,212 tris at 2.0 m near / 40.0 m far with no holes.

## Verdict — the twin towers are modelled and read correctly from below; the photograph is of a demonstration, with the towers as its backdrop, so the two halves share a subject and nothing else

**The reference is a march.** Sixty per cent of the frame is a crowd with placards, photographed from within it at eye level; the Deutsche Bank Center's twin towers stand behind, in the upper third. Unlike most of the mismatches in this queue the subject *is* in the photograph — this is half a reference rather than the wrong one — but the picture's content, exposure and colour are all the demonstration's, not the building's.

**The render is a good upward view of the towers.** Both shafts rise from a chamfered podium, the setback and the corner cut read correctly, and the probe measures the near tower exactly: **235.64 m** above a ground of 24.56 m over **43 of 43** rays, plan extent **40.3 m by 40.3 m**. The catalogue entry 94.7 m away carries 228.6 m for the whole Columbus Circle composite, and the height came from the geometry rather than that entry (J74).

**The sightline again counts a nearer member of the same composite.** Of 13 rays, 13 clear and **9 on the subject** — but **8 of those 9** land on fabric nearer than the recorded coordinate, `lm_b_columbus_circle_monument.3` at **83.8 m** against the subject's own 114.7 m. Here the two objects are the two halves of the same building complex, so the reading is defensible; on `landmark_central_park_tower`, where the composite spans a whole street corridor, the same rule certifies a wall twenty-two metres from the lens. The fault is the rule, and this sheet is the benign end of it.

**The tonal comparison is dominated by the photograph's own development.** The reference sits **1.291 stops below** the grey convention and the render **0.247 above** it — **1.538 stops** apart, the widest in this queue — which is most of the render's **1.421×** mean and **1.662×** median. Chroma **0.102** against **0.1673** (**0.61×**): a thousand coats and placards against glass and pale plaza.

## What matches

* **The twin towers are right in massing and proportion**, including the chamfered crowns and the podium setback.
* **The probe is exact**: 43 of 43 rays, 235.64 m, extent 40.3 m square, with the composite catalogue entry properly refused (J74).
* **The development is metered and unclamped**, +2.15 stops from a median linear luminance of 0.040579.
* **The car-free rule works here** — **48 vehicles dropped** because the road graph put them on Central Park's East, West, Terrace or Center Drive (the rule whose absence on Governors Island is J95).
* **Near-field ground is sound**: within 150 m, **0.0047** of 213 park-surface samples sit under the terrain, median **+0.199 m**.
* **The landmark-ground rule did real work**: **2,814** park-ground faces cut.
* **The season is right and was read**: bare canopies for 24 March, and the render's street trees are bare.
* **The day type is right**: the crowd clock reads **Saturday** for 2018-03-24, which was a Saturday — and a Saturday is when a march of this kind happens.
* **The pavement is complete**: 22,609 polygons, **0 dropped**, including 8,675 white markings, 5,286 roadbed, 3,965 sidewalk, 2,589 curb, 735 median and 640 plaza.
* **Agents carry mixed detail**: 9 vehicles at LOD1, and of 252 people **51 at LOD1 and 2 at LOD0**.

## What does not match

* **The photograph is a demonstration and the render is an empty plaza.** The crowd that makes the reference what it is has no counterpart: **252** people are drawn where the table asked **2,374** and 3,000 were simulated.
* **Eight of the nine rays that scored 0.692 landed on a nearer member of the same composite**, 83.8 m out rather than 114.7 m.
* **The only landmark the frustum finds is the Hearst Tower**, 274.1 m away and 38.7° off axis; the subject has no separate model to find.
* **The render is far brighter at the midtone**: median **1.662×**, mean **1.421×**, almost all of it the photograph's own 1.291-stop underdevelopment (J83).
* **Chroma is 0.61 of the photograph's** and contrast **0.826×**.
* **The top of the subject is cut off** at the 18 mm floor; the towers need 64° of elevation at 115 m.
* **Fifty-nine per cent of the props are missing**: 1,216 placed of **2,969 in range**, with **1,607 dropped for the triangle budget** of 1,176,964 and 10 impostor cards dropped.
* **6,499 of 15,825 kit records were drawn**, capped at a 1,104,162-triangle budget, with a further 2,500 suppressed under landmark shells.
* **1,435 tree rows did not fit** the props budget, **0** of the 369 impostor cards are procedural canopy stems, and **238 of 457** tree species were substituted.
* **Three of 5 structures tiles in range have no structures file**, under the busiest station complex on the West Side.
* **Beyond 400 m the park surface sits under the terrain on 0.2658 of 1,460 samples**, minimum **−6.386 m**, with a z-fighting fraction of **0.0432**, after a redrape that moved **266,215** vertices (J85).
* **Eighteen props across eight kinds were wanted in range and have no asset**: 6 artwork, 3 drinking fountain, 2 parks building, 2 passenger-information sign, 2 vending machine, 1 misc structure, 1 parks comfort station, 1 swimming pool. The Columbus monument's own statue is in the artwork class.
* **Seven park-ground surface kinds fall back to the builder's flat colour** — infield dirt, sport court, grass field, park grass, recreation grass, rink ice, bare ground (J40).
* **Pedestrians were dropped in two large groups** — **574** in the carriageway without crossing and **377** off a walkable surface — which at Columbus Circle, where the plaza and the circle itself are where people stand, is the geometry of the place disagreeing with the planimetric data.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the photograph is a demonstration | the chooser matched the place and the subject appears in the frame, so this passes its rules while the picture's content is an event (J93's benign end) | **verification — open, J93** |
| 8 of 9 scoring rays on a nearer composite member | the sightline counts a hit on any member of the landmark composite as a hit on the subject; here the members are the two halves of one complex | **verification — open** |
| the frustum finds only the Hearst Tower | the cone test uses landmark composite origins, and the subject's composite centroid falls outside the frame | verification — open |
| p50 1.662×, mean 1.421× | the reference is developed 1.538 stops below the render relative to the grey convention (J83) | **reference** |
| chroma 0.61×, sd 0.826× | a crowd in colour against glass and pale plaza | consequence of the reference |
| the top of the subject is cut off | 18 mm is the widest lens the comparison allows and the towers need 64° at 115 m | **verification — declared limit** |
| 1,216 props of 2,969 in range | the props triangle budget at 1,176,964, which dropped 1,607 | **performance** |
| 6,499 kit pieces of 15,825 in range | the kit triangle budget at 1,104,162, plus 2,500 suppressed under landmark shells | performance + declared rule |
| 1,435 tree rows dropped, 238 species substituted, 0 canopy stems | the props budget, a tree catalogue that does not hold most species surveyed here, and no mapped woodland polygon in this radius | performance + **data** |
| 3 of 5 structures tiles without a file | no structures file was built for those tiles | **data — open, three tiles unbuilt** |
| 0.2658 of far park ground under the terrain, min −6.386 m | the terrain grid coarsens to 40 m beyond the near band across Central Park's south-west corner (J85) | geometry — open, measured |
| 18 props across eight kinds unmapped, the Columbus statue among them | no asset exists for those kinds | **data — open** |
| seven park surface kinds flat-coloured | the texture catalogue has no photographic set for any of them (J40) | **declared decision** |
| 574 plus 377 pedestrians dropped in the carriageway or off the walkable surface | the plaza and circle where people actually stand are not walkable surface in the planimetric data | **data — open, measured** |
| 252 people where the table asked 2,374 | the agent triangle budget plus the placement rules, each with its count | performance + verification |
