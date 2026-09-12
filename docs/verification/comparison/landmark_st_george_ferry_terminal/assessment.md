# St. George Ferry Terminal

`landmark_st_george_ferry_terminal` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:St George Terminal 3 vc.jpg by Tom Page from London, UK, CC BY-SA 2.0 (https://creativecommons.org/licenses/by-sa/2.0), taken 2022-03-18 14:45, 1920x1280. [Commons page](https://commons.wikimedia.org/wiki/File:St_George_Terminal_3_vc.jpg) — the photograph's own view direction is derived from the image at **high** confidence. **It is the Staten Island Railway platform under the terminal**: an R44 car standing at the platform with its number on the destination sign, the yellow tactile edge strip, fluorescent fittings on a riveted steel roof structure, ballast and rail. It is an interior of a train shed, not the terminal's front.

**Camera** — 40.643755, -74.075356 (NYC_TM -10603, -6238) at z 4.7 m NAVD88 | azimuth 115.1°, pitch 0.0° | 35 mm on 36 mm (54.4° horizontal, landscape) | 1280x854. The camera stands on **this photograph's own EXIF GPS**, **232.0 m** from the item's recorded viewpoint; the item's recorded azimuth is 350.0°, **125.1° away** — the nominal view looks almost the opposite way. The lens was **not widened** and the axis left **level**, because nothing built stands within 6 m of the subject's coordinate. The walk did not move it: 150.0 m of clear view against a 55.5 m requirement, and the nearest built thing in the frame is **`t_-11_-7_precast` 8.3 m** away, one tile's precast surfaces joined into a single object (J94). The ground reads 3.076 m NAVD88, the 10th percentile of 113 samples within 12 m, range 3.02 to 3.38 m.

**Sun** — azimuth 215.4°, elevation 42.7° at 2022-03-18T14:45:00−04:00, from the photograph's own **EXIF DateTimeOriginal** to the minute; 856.1 W/m² direct normal, sky at strength 0.0330, Filmic, **+1.19 stops** metered and unclamped against a linear median of **0.078892** and a target of **0.18**. The physical rule would have given **0.02 stops**.

**In the scene** — 4,500,052 triangles: 5 building tiles (111,778 tris, **2 missing**, 0 LOD-substituted), 1 landmark model and **none in the 54.4° cone**, 16,213 pavement polygons, 2,466 props, 10,251 kit pieces, **0 park-ground meshes**, 34,560 triangles of structures, 89 vehicles and 227 people.

## Verdict — nothing is measurable, the nearest catalogued landmark is 4,773.4 m away, and the published frame is a stack of grey bands

**The probe cast 43 rays and found fabric on none.** *Nothing built stands within 6 m of the subject's coordinate; the nearest built thing is `t_-11_-7_struct_station_house`, **70.8 m** away at bearing 22.5°.* So there is no height, no plan extent and **no sightline** — one of J96's thirteen, which names this sheet by that figure. And the catalogue has nothing nearby either: the nearest origin is **`b_verrazzano_narrows` at 4,773.4 m**, 4,773.4 m away across the island, which is the sharpest illustration in the pass of how thin the landmark catalogue is outside Manhattan. The frustum lists **0 of 1** placed landmarks in the cone.

**The published frame is not a picture of anything.** A textured white band across the top, a dark grey band under it, a thin strip carrying a line of tiny pedestrians and vehicles, then more grey bands and a large pale field below. The camera sits 4.7 m above the datum with a joined precast mesh 8.3 m ahead, so the frame is that mesh, the bay beyond it and the terminal's platform level in between. Measured, it is very nearly colourless: chroma **0.013** against the photograph's **0.0611**, a ratio of **0.213**.

**The reference cannot be compared either.** It is a photograph taken under the terminal on a railway platform, and this build declares no interiors anywhere except volumes visible from the street through glass (B10, I5). Its own median sits **1.879 stops below** the grey convention — a dim train shed exposed for its fluorescent fittings — against the render's **0.26 above**, a **+2.139-stop** difference and a p50 ratio of **2.047** (J83).

**Two build gaps this sheet exposes that most sheets do not.** **Building shells were not built for two tiles** in range — `t_-10_-6` and `t_-10_-7` — so the record reports `missing 2` on the buildings block, the first non-zero shell count on any sheet written so far. And **no park ground was built for seven tiles** in the 810 m radius: `t_-10_-6`, `t_-10_-7`, `t_-11_-6`, `t_-11_-7`, `t_-11_-8`, `t_-12_-6`, `t_-12_-7` — so the frame's ground carries no surface of its own (J102). Staten Island's north shore is, in this build, the thinnest ground in the pass.

## What matches

* **The refusals are correct and complete** — no fabric at the coordinate, so no height, no extent, no sightline, no lens widening and no tilt, with the distance and bearing to the nearest built thing published instead (J96).
* **The kit was almost complete** — **10,251 pieces of 14,854 in range** against a **2,238,327-triangle** budget, the largest kit budget on any sheet written so far, and the most varied inventory: 8,249 windows, 533 storefronts, 374 window accessories, 247 parapets, 144 quoins, 128 cornices, 122 entry doors, 121 string courses, 84 HVAC units, 68 scaffold pieces, 58 pilasters, 46 bulkheads, 15 fire escapes.
* **Nothing was capped in the props** — **2,466 placed of 2,627 in range**, **0 dropped for budget**.
* **The north shore is furnished** — 197 manholes, 191 street lamps, 87 cooling towers, 86 hydrants, **45 benches**, **37 bus-stop signs** on the new MTA blade (J58), 2 bus shelters, 2 subway entrances, 2 LinkNYC kiosks.
* **16,213 pavement polygons and none dropped**, including **688 parking-lot** and **576 plaza** polygons, which is what a ferry terminal's forecourt is.
* **The trees are bare, from the photograph's own date** — 18 March, inside `leaf_off`'s window (J97's working half).

## What does not match

* **Nothing about the terminal is measurable** — the item's coordinate stands 70.8 m from the nearest built thing (J96).
* **The nearest catalogued landmark is 4,773.4 m away.**
* **The reference is a railway platform under the terminal**, and this build has no interiors (B10, I5).
* **The frame is a stack of grey bands**, chroma **0.213** of the photograph's, with a joined precast tile mesh 8.3 m from the lens (J94).
* **The camera looks 125.1° away from the item's recorded azimuth.**
* **Building shells were not built for two tiles** — `t_-10_-6`, `t_-10_-7`.
* **No park ground was built for seven tiles** in range, and the scene carries **0 park-ground meshes** (J102).
* **Three of four tiles with structures have no file** — 4 tiles, **3 without a file**.
* **p50 2.047, mean 1.367** — the photograph is developed **1.879 stops below** the grey convention for a dim train shed and the render **0.26 above** it, a **+2.139-stop** difference (J83).
* **33 props across eight kinds in range have no asset** — 11 vending machines, 8 memorials, 4 misc structures, **3 swimming pools**, 2 artworks, 2 drinking fountains, 2 parks buildings, 1 real-time information sign.
* **487 of the 1,790 trees are a substituted species**, 3 are scaled outside the allowed band, and **662** of the 1,776 impostor cards are procedural canopy stems placed by rule (Stage 55).
* **647 agents were dropped** — **258 pedestrians in the carriageway without crossing**, 78 where the planimetric data has no sidewalk (J101), 8 vehicles at the agent triangle budget, 8 vehicles where there is no roadway, 3 cyclists the fleet exports without a rider.
* **No cloud.** Nothing in this build reads a historical sky; the reference has no sky in it either.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| nothing is measurable | the item's recorded coordinate stands 70.8 m from the nearest built thing, so the probe found no fabric and no sightline was tested (J96) | **data — open (J96), the coordinate** |
| the nearest catalogued landmark is 4,773.4 m away | the landmark catalogue is thin outside Manhattan, so a Staten Island subject has no neighbour to fall back on | **data — open, and the clearest instance in the pass** |
| the reference is a train shed interior | the chooser paired an interior photograph with an exterior-only build (B10, I5, J100) | verification — open (J100) |
| the frame is grey bands | the camera sits 4.7 m above the datum with a joined precast tile mesh 8.3 m ahead, and the axis is level because there is nothing to tilt toward (J94, J96) | geometry + verification |
| the camera looks 125.1° from the recorded azimuth | the heading is the bearing from the photograph's own GPS to the subject, and that GPS is 232 m from the nominal viewpoint on the other side of the terminal | verification — the pairing |
| two tiles have no building shells | those tiles are unbuilt | **data — open** |
| no park ground for seven tiles, 0 meshes in the scene | 85 % of the city's mapped open space was never draped, and Staten Island's north shore is in the unbuilt part (J102) | **data — open (J102)** |
| three of four tiles without a structures file | those tiles are unbuilt, under a ferry terminal and a railway | data — open |
| p50 2.047, chroma 0.213 | a dim train shed developed 1.879 stops below the grey convention against a colourless band of grey surfaces (J83) | reference + geometry |
| 33 props across eight kinds unmapped | no asset exists for those kinds, swimming pools among them | data |
| 487 substituted species, 662 procedural stems | the species lists do not cover this stock, and woodland polygons are filled by rule (Stage 55) | data — declared, counted |
| 258 pedestrians in the carriageway, 78 off a walkable surface | the crowd model puts walkers where the placement test reads roadway or cannot read at all (J101) | verification — open (J101) |
