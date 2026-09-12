# Lincoln Center

`landmark_lincoln_center` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Lincoln Center grassy plaza 2021 (1) jeh.jpg by Jim.henderson, CC BY 4.0 (https://creativecommons.org/licenses/by/4.0), taken 2021-05-10 11:35:19, 1920x1280. [Commons page](https://commons.wikimedia.org/wiki/File:Lincoln_Center_grassy_plaza_2021_(1)_jeh.jpg) — the photograph's own view direction is derived from the image at **high** confidence.

**Camera** — 40.77220, -73.98310 (NYC_TM -2794, 8018) at z 26.3 m NAVD88 | azimuth 303.4°, pitch +7.2° | 35 mm on 36 mm (54.4° horizontal) | 1280x854. Position and heading both come from the photograph: its own EXIF camera GPS, **33.7 m** from the item's recorded viewpoint, and 303.4° is the bearing from there to the subject — **1.8°** from the item's own azimuth. The camera was not moved — open air, azimuth clear for **84.0 m** against the 60.6 m needed — and the nearest built thing is `lm_c_lincoln_center.0` **47.3 m** away, with no simulated agent within 60 m. Ground under the camera reads **24.734 m** NAVD88 from 16 heightmap samples within 5.0 m, range 24.68 to 24.79 m.

**Sun** — azimuth 138.6°, elevation 61.7° at 2021-05-10T11:35:19−04:00, from the photograph's own **EXIF DateTimeOriginal**; 922.7 W/m² direct normal, sky at strength 0.0309, Filmic, **+3.13 stops and not clamped**. The linear frame's median is **0.020513** against a middle-grey target of 0.18; the physical rule would have given **0.0 stops** (J83).

**In the scene** — 4,500,110 triangles: 4 building tiles (187,402 tris, none missing, none LOD-substituted), 5 landmark models of which 1 falls inside the 54.4° frame, 21,855 pavement polygons with **0 dropped**, 2,661 props, 7,805 kit pieces, 17 park-ground meshes over 254 surfaces, 88 vehicles and 435 people, terrain 207² at 2.0 m near / 40.0 m far.

## Verdict — the Metropolitan Opera House's five arches are modelled as blind recesses instead of glazed openings, and the photograph's plaza is a temporary lawn installation that no build could carry

**The massing is right and immediately recognisable.** The render shows the Met's front as five tall arched bays under a flat entablature, flanked by the colonnades of Avery Fisher and the David H. Koch theatre — the correct rhythm, the correct proportion, the correct grey travertine tone. At 121 m it reads as the same building.

**The arches are blind.** In the photograph each of the five arches is a full-height glass wall with the lobby, the balconies and the two Chagall murals behind it. In the render each is a solid recess: the arch profile is modelled, the opening is not. That is the same class of gap as the uncut window openings recorded in J51 — an arch is drawn as relief rather than as a hole — and here it removes the building's interior and its two most famous paintings in one step.

**The photograph's plaza is a temporary installation.** In May 2021 Josie Robertson Plaza was laid with an artificial-turf lawn for the season, which is why the reference's lower two thirds is bright green with people sitting on it. The render's plaza is the permanent paving, in concrete grey. **No build reading surveyed data can have this**, and it is the main reason chroma comes out at **0.0502** against **0.1619**, a ratio of **0.31**. Recording it here as a date-and-condition mismatch rather than a fidelity gap.

**The fountain is absent.** The Revson Fountain fills the centre of the reference; nothing in the render's plaza stands in its place. Fountains are not a class this build models.

**The sightline reads 0.846 and ten of its eleven hits are on nearer fabric of the same composite.** `lm_c_lincoln_center.7` at **80.1 m** against the subject's own coordinate at 121.3 m — so what the rays confirm is that some part of Lincoln Center is visible, not that the Opera House is. The composite here is one campus of adjoining buildings, so the reading is defensible, and it is the same rule that certifies a wall 22 m away on `landmark_central_park_tower`.

## What matches

* **The five arched bays, the entablature and the flanking colonnades** all read correctly at 121 m, in the right stone tone.
* **The camera stands 33.7 m from the item's own viewpoint** with a bearing 1.8° from its recorded azimuth, and needed no walk.
* **The probe is complete**: 43 of 43 rays, 32.91 m above a ground of 25.28 m, plan extent **143.7 m by 110.2 m** — the campus block's real footprint (J74).
* **The development is metered and unclamped**, +3.13 stops from a median linear luminance of 0.020513.
* **Near-field ground is perfect**: within 150 m, **0.0** of 500 park-surface samples sit under the terrain, median **+0.20 m**.
* **The pavement is complete**: 21,855 polygons, **0 dropped**, including 8,774 white markings, 4,571 sidewalk, 3,985 roadbed, 2,853 curb and 467 plaza.
* **The median tone is within a tenth** — 1.102× — with the two development offsets **0.301 stops** apart (J83).
* **51 of 2,038 trees are drawn from modelled branches.**

## What does not match

* **The five arches are blind recesses**, so the glazed lobby, the balconies and the two Chagall murals are absent (J51's family).
* **The plaza's temporary lawn cannot be reproduced**, and it is two thirds of the reference.
* **The Revson Fountain is absent.**
* **Chroma is 0.31 of the photograph's**, 0.0502 against 0.1619.
* **The render is brighter and harsher**: mean **1.3×**, standard deviation **1.099×**, ninety-fifth percentile **0.9375** — a travertine wall in direct 62° sun against a photograph with cloud in it.
* **No people in the frame.** 435 are drawn in the scene and none is on the plaza the camera is looking at; the reference has some thirty visible.
* **No cloud.** The reference's May sky carries cumulus.
* **Ten of the eleven rays scoring 0.846 landed on nearer fabric of the same composite**, 80.1 m out against the subject's 121.3 m.
* **7,805 of 9,601 kit records were drawn**, capped at a 1,377,228-triangle budget.
* **1,987 of 2,038 trees are impostor cards**, **0** of them procedural canopy stems, and 9 cards were dropped.
* **Beyond 400 m the park surface sits under the terrain on 0.19 of 905 samples** (J85).
* **Seven park-ground surface kinds fall back to the builder's flat colour** (J40).
* **The crowd is a quarter of the ask**: the table wanted 449 vehicles and 1,840 people; 536 and 2,191 were simulated and **2,204** dropped — 551 people and 180 vehicles at the agent triangle budget, **317** pedestrians in the roadway while not crossing, 55 with no sidewalk under them, and **21 riderless bodies**.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the five arches are blind recesses | the arch profile is modelled as relief and the opening is not cut, the same class as the uncut window openings recorded in J51; behind it there is also no interior to see | **geometry — open, J51's family** |
| the plaza's temporary lawn | the reference records a seasonal installation; no build reading surveyed data can carry it, and the chooser tests nothing about a photograph's date or conditions (J93) | **reference — no source exists** |
| no fountain | a fountain is not a class this build models | geometry — declared scope |
| chroma 0.31×, mean 1.3×, sd 1.099× | the reference's saturated content is the lawn, and the render's frame is travertine in direct sun | consequence of the two rows above |
| no people on the plaza | 435 agents are drawn and the placement rules put none on this plaza, because it is not a walkable surface in the planimetric data — 55 were dropped for exactly that | **data — open, measured** |
| no cloud | nothing in this build reads a historical sky | reference — no source exists |
| 10 of 11 scoring rays on nearer composite fabric | the sightline counts a hit on any member of the landmark composite as a hit on the subject; here the members are one campus of adjoining buildings | verification — open |
| 7,805 kit pieces of 9,601 in range | the kit triangle budget at 1,377,228 | performance |
| 1,987 of 2,038 trees as cards, 0 canopy stems | the props budget spends its triangles on cards at this density, and no mapped woodland polygon lies in this radius | performance + declared rule |
| 0.19 of far park ground under the terrain | the terrain grid coarsens to 40 m beyond the near band (J85) | geometry — open, measured |
| seven park surface kinds flat-coloured | the texture catalogue has no photographic set for any of them (J40) | **declared decision** |
