# 40 Wall Street (Trump Building)

`landmark_40_wall_street` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:View of Manhattan from Liberty Island ferry, NYC, 20231003 1627 2026.jpg by Jakub Hałun, CC BY 4.0 (https://creativecommons.org/licenses/by/4.0), taken 2023-10-03 16:27:26, 1920x909. [Commons page](https://commons.wikimedia.org/wiki/File:View_of_Manhattan_from_Liberty_Island_ferry,_NYC,_20231003_1627_2026.jpg)

**Camera** — 40.706285, -74.01193 (NYC_TM -5180, 698) at z 5.7 m NAVD88 | azimuth 70.0°, pitch **+30.7°** | **18 mm** on 36 mm (90.0° horizontal) | 1280x606. The camera stands on the item's recorded viewpoint and was then **moved 52.2 m onto the nearest roadbed**, because the recorded viewpoint is boxed in: the view azimuth is closed off 32 m ahead, less than the 80 m this frame needs. From the new point the view is clear for 96 m, nothing built stands within 20 m of the lens, and the nearest simulated agent is `agent_ped_1719.3` 14.6 m away.

**Sun** — from 2023-10-03T16:27:26−04:00, the photograph's own **EXIF DateTimeOriginal**. That date is a **Tuesday** and the crowd was drawn for a weekday.

**In the scene**, within 720.7 m of the camera and not all of it in frame — 5 building tiles (108,550 tris), 13 landmark models of which **5 can fall inside the 90.0° frame**, 26,463 pavement polygons (10,017 white marking, 5,457 roadbed, 5,346 sidewalk, 3,969 curb, 583 crosswalk, 457 plaza, 374 median, 236 yellow marking, 24 parking lot), 725 props of the 925 in range, 5,027 kit pieces, 81 vehicles and 406 people; 4,500,015 triangles. Ground mesh 87,328 triangles, 0 holes. 20 city surfaces are dressed from the shared photographic catalogue.

## Verdict — a broken pairing and a frame that proves little, and the record says both before a reader has to work it out

**The photograph is a skyline from the water and the render is a street canyon looked up.** The reference was taken from the Liberty Island ferry; its own EXIF GPS is **1,534.5 m** from the item's recorded viewpoint, past the 250 m at which it could still be the same view, so the camera was not stood on it. The record states what that means and what it does not: *"a statement about this pairing and not about the photograph: a fix this far out is usually correct and simply of somewhere else"* (docs/DEVIATIONS.md J60). **Nothing below should be read as a comparison of two pictures of 40 Wall Street.**

**The render is also close to unusable on its own terms.** Its mean luminance is **0.1054** — above the 0.06 floor at which the renderer refuses to publish a frame, and not by much — and what it shows is a 90° frame tilted **30.7°** up at a canyon in shadow, with one sunlit tower crown at the top left and most of the rest a dark mass. The tilt and the lens are both stated consequences of one rule: the subject tops out **53° above the horizon** from 200 m away, so the lens was widened to the 18 mm floor and the axis tilted the remainder. A frame that shows its subject with converging verticals beats a frame that does not show it, and the sheet says so — but this one is at the edge of showing anything.

**What is genuinely new here is the height, and it disagrees with the catalogue by 18 m in an instructive way.** The probe casts 17 rays at the subject's coordinate; **all 17 land on built fabric** and the highest is `lm_40_wall_street.2` at **264.55 m** above the ground there. The catalogue entry `40_wall_street` stands **14.4 m** away and publishes **282.5 m**. The difference is not an error in either: the catalogue's figure is the building's published height to the tip of its spire, and the probe measures the highest surface a ray meets at the *subject's own coordinate*, which is the roof below the spire's base. The record publishes both and says which is which (J74).

## What matches

* **The site is the right site.** A narrow Financial District canyon of dark masonry towers rising out of shadow, with a sliver of sky between them — that is Wall Street, and 5,027 kit pieces stand in it including **4,176 windows**, 657 window accessories, 108 storefronts, 18 scaffold pieces and 11 parapets.
* **The subject is where the item says it is.** The recorded azimuth of 70.0° agrees with the bearing from the camera position actually used to 40 Wall Street to **0.1°**, and the building the probe lands on is the building the item names.
* **The camera move is correct behaviour and is declared.** The recorded viewpoint had 32 m of open air against the 80 m a 151 m subject needs, so the camera was walked onto real roadbed rather than left to render a wall.
* **The street is a street**: 5,457 roadbed, 3,969 curb and 5,346 sidewalk polygons with asphalt and concrete from their own material names, **10,017 white and 236 yellow marking polygons** in range, and 81 vehicles and 406 people from the simulation's own Tuesday afternoon.
* Nothing was dropped for being missing: 5 building tiles, 0 LOD substitutions, 0 pavement polygons dropped, 0 holes in the ground.

## What does not match

* **The two halves are pictures of different things from different places**, by the 1,534.5 m the reference's own GPS records. Composition, framing and what fills the frame are not comparable here by construction.
* **The frame is a fifth of the photograph's brightness and carries a seventh of its colour**: mean **0.1054** against **0.5557** (**0.19×**), standard deviation **0.1076** against **0.1746** (**0.616×**), chroma **0.0248** against **0.1763** (**0.141×**), 5th percentile **0.0126** against **0.2531**, 95th percentile **0.3742** against **0.7743**. Almost all of that is the pairing: a skyline over open water in late-afternoon sun against a shadowed canyon looked up at from its floor. The chroma ratio is the lowest so far in the set and this sheet cannot separate how much of it is J66 and how much is the pairing.
* **`sightline.subject_visible` is `false`**, blocked at **37.5 m** by `t_-6_0_limestone` — a building between the camera and the subject. The fan is **264 m** wide, held at the **15° cap**, and 0 of 5 rays reach the tower. A fan sized to a 265 m subject seen from 203 m spans more than the canyon is wide, so the walls take the rays; that is the same fault this pass records at DUMBO (docs/DEVIATIONS.md J78), and it is a statement about the probe rather than about the frame. What the frame actually shows is a dark mass where the tower stands, so on this sheet the boolean is not obviously wrong — only unproven.
* **The verticals converge, by 30.7°.** The sheet says so and says why: past the 18 mm floor a level axis cannot contain a subject 53° above the horizon. This frame is therefore **not comparable with the photograph on proportion**, which is the property the level-axis rule exists to protect.
* **200 props in range were not placed** and part of the kit was capped at 1,147,969 triangles.
* **Pedestrians and vehicles were dropped in their hundreds** — 1,441 people for being outside the radius, 689 for the triangle budget, 298 for standing in the carriageway without crossing and 146 for not being on a walkable surface; 656 vehicles outside the radius and 156 for the budget. Among them, **20 people and 18 vehicles were found inside buildings** and dropped for it. The record names each rule and its count.
* **Only 3 cornices and 3 string courses** stand among 5,027 kit pieces: the Financial District's towers carry setbacks, cornices and crowns, and these are extrusions with windows.
* **40 Wall Street's crown is the thing it is known for** — a green pyramidal spire — and the frame does not show it, because the frame does not reach it.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the two halves are of different places | the photograph's own GPS is 1,534.5 m from the recorded viewpoint, past the 250 m band; the record says so and refuses to stand the camera on it (J60) | **reference — this pairing cannot be fixed by rendering** |
| mean 0.19×, chroma 0.141× | a sunlit skyline over water against a shadowed canyon looked up from its floor; the pairing dominates and this sheet cannot isolate J66's share | reference |
| verticals converge by 30.7° | the subject tops out 53° above the horizon at 200 m; past the 18 mm lens floor the axis must tilt, and the sheet declares it (I18) | stated choice |
| `subject_visible: false`, 0 of 5 rays | the fan is sized to a 265 m subject and spans more than the canyon is wide, so the walls take the rays; a probe fault, not a frame fault (J78) | verification — open |
| measured 264.55 m against a published 282.5 m | the catalogue's figure is the height to the spire's tip; the probe measures the highest surface at the subject's own coordinate, which is the roof below it. Both are published and the record says which is which (J74) | — (not a gap) |
| no crown, no green pyramid | the frame does not reach the top of the building even at 18 mm and 30.7° | verification |
| almost no cornice, setback or crown geometry | the shell is extruded from a footprint; the kit's cornice is a generic profile and the classifier has no source for a modelled crown | geometry |
| 200 props and part of the kit unplaced | triangle budget 1,147,969, declared on the sheet | performance |
| 38 agents found inside buildings | the placement rules caught them and dropped them; the record names the rule and the count | verification |
