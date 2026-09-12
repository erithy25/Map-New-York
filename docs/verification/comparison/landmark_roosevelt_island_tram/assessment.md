# Roosevelt Island Tramway

`landmark_roosevelt_island_tram` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Roosevelt Island cable car (49400617542).jpg by Mig Gilbert from Brighton, CC BY-SA 2.0 (https://creativecommons.org/licenses/by-sa/2.0), taken 2020-01-10 12:58, 1920x2880. [Commons page](https://commons.wikimedia.org/wiki/File:Roosevelt_Island_cable_car_(49400617542).jpg) — the photograph's own view direction is derived from the image at **high** confidence. It is the **island** station house: the red portal frame, two tram cabins parked inside, *Roosevelt Island Tramway* in red across the fascia, blue corrugated cladding, the haul ropes running out over the brick-paved ramp, bare January branches across the top of the frame, and the Ravenswood smokestacks on the Queens shore.

**Camera** — 40.757465, -73.954532 (NYC_TM -383, 6381) at z 7.0 m NAVD88 | azimuth 298.7°, pitch 0.0° | 35 mm on 36 mm (37.8° horizontal, 54.4° vertical, portrait) | 852x1278. The camera stands on **this photograph's own EXIF GPS**, **21.9 m** from the item's recorded viewpoint, and its heading agrees with the item's recorded 300.0° to **1.3°**. The axis was left level because the subject is **911.1 m** away. The walk did not move it: 150.0 m of clear view against an 80.0 m requirement, the nearest built thing `t_-1_6_concrete` **21.6 m** out, no agent within 60 m. The ground reads 5.403 m NAVD88, the 10th percentile of 113 samples within 12 m, range 5.31 to 5.69 m. **The record contradicts itself about where this is**: the viewpoint line reads *Tramway Plaza on Roosevelt Island, about 900 m east-south-east of the Manhattan station*, and the camera's own `eye_source` reads *Tramway Plaza at Second Avenue and 59th Street, street level*. Those are opposite ends of the ride.

**Sun** — azimuth 194.1°, elevation 26.0° at 2020-01-10T12:58:00−05:00, from the photograph's own **EXIF DateTimeOriginal** to the minute; 731.0 W/m² direct normal, sky at strength 0.0375, Filmic, **+3.36 stops** metered and unclamped against a linear median of **0.01751** and a target of **0.18**. The physical rule would have given **0.73 stops**. A 26° January Sun almost due south, into a frame looking west-north-west.

**In the scene** — 3,239,362 triangles: **21 building tiles** (530,712 tris, 0 missing, 0 LOD-substituted), 15 landmark models of which 4 can fall inside the 37.8° frame, 20,157 pavement polygons, 7,238 props, 1,396 kit pieces, 28 park-ground meshes, 69 vehicles and 207 people.

## Verdict — the tramway blocks the view of the tramway, and the probe measured a kilometre-wide brick mesh instead of it

**Zero of thirteen rays are clear.** `subject_visible` is **false**, `subject_visible_fraction` **0.0**, `subject_clear_fraction` **0.0**, and every ray stops at **49.1 m** on `lm_b_roosevelt_island_tram.27` — a member of the tramway's own model. The subject is 911 m away and its own near structure, 49 m from the lens, is what the rays meet. This is one of the 19 sheets in the pass that publish a visible fraction of exactly 0.0 with `frame.usable` true (J100), and it is the clearest case of a subject hiding itself.

**The probe measured a tile mesh, and the record says so.** `probe.object` is **`t_-2_6_tan_brick`** — every tan-brick surface in that tile joined into one object — with an extent of **1035.7 m by 1015.4 m**, and the record refuses to use it: *a tile mesh is every building of one material in the tile, so its extent is not the subject's and is not used* (J94). The **15.85 m** height it reports above a ground of 20.26 m is therefore the height of a brick building somewhere in that kilometre, not of the tramway. The nearest catalogue origin, `b_roosevelt_island_tram`, stands **497.3 m** away, past the 120 m the old rule looked in, so nothing was inherited either (J74). **18 of 43** probe rays found fabric.

**What the render does contain is the Manhattan tower, and it is right.** A white steel lattice tower rises through the frame with the guideway springing off it, pedestrians and cars on the plaza below, a yellow taxi at the kerb — and the tower's proportions and lattice pattern are recognisably the tramway's. What the photograph contains is the **island** station house, 900 m away at the other end. So the two halves show the two ends of one ride, and the sheet's own viewpoint text cannot decide which end it is describing.

**The lower 45 % of the render is one flat plane.** At an eye height of 7.0 m NAVD88 looking west-north-west across the river, the frame's bottom is the East River's flat specular surface and the bare terrain beside it — the record names **three tiles with no park ground** in the 900 m radius (`t_-1_5`, `t_0_5`, `t_0_6`), so that ground carries no surface of its own (J102). Measured: a 5th percentile of **0.4536** against the photograph's **0.0577**, and a standard deviation of **0.1675** against **0.3426** — **0.489**, less than half the range, because nothing in the render is dark and nearly half of it is one tone.

## What matches

* **The Manhattan tower.** Lattice pattern, taper and guideway spring are all recognisably the tramway's.
* **The aim** — the recorded azimuth agrees with the measured bearing to **1.3°** and the axis was correctly left level for a 911 m subject.
* **The trees are bare, from the photograph's own date** — 10 January, inside `leaf_off`'s window, and the reference's branches are leafless (J97's working half).
* **The largest building-tile set in the pass** — **21 tiles**, 530,712 triangles, **0 missing**, **0 LOD-substituted**.
* **The props are dense and mostly real** — **7,238** placed, of which 5,613 come from the street-tree survey and 1,288 from OSM; only **178** of the 7,065 impostor cards are procedural canopy stems (Stage 55).
* **The plaza is furnished** — 40 Citi Bike stations, 61 manholes, 15 street lamps on the 30–40 m rule, 8 cooling towers, 7 hydrants, 3 steam vents, 2 railroad structures.
* **20,157 pavement polygons and none dropped**, including **325 plaza** and 447 crosswalk.

## What does not match

* **The subject is not visible at all** — 0 of 13 rays, blocked by the tramway's own member 49 m from the lens (J100).
* **The probe measured a 1,035 m tile mesh**, so this sheet carries no usable height or plan extent for its subject (J94).
* **The record contradicts itself about the viewpoint** — Roosevelt Island in one line, Second Avenue and 59th Street in another.
* **The island station house is absent** — no portal frame, no cabins, no fascia lettering, no blue cladding. No printed copy is invented anywhere (B5, B15a).
* **Less than half the photograph's contrast** — sd **0.489×** — with a 5th percentile of **0.4536** against **0.0577**: nothing in the render is dark.
* **The render is brighter at the midtone** — p50 **0.4982** against **0.357**, a ratio of **1.396**, mean **1.221×**. The photograph's median sits **0.782 stops below** the grey convention and the render's **0.238 above**, a **+1.02-stop** difference (J83).
* **Nearly twice the photograph's colour** — chroma **0.085** against **0.0472**, a ratio of **1.801**. The reference is a grey-blue January industrial scene; the render has a clear sky, tan brick and a yellow taxi.
* **The water is a flat specular plane** with no wave state and no turbidity, and at this eye height it is most of the lower frame (J103's companion gap).
* **No park ground was built for three tiles in range** — `t_-1_5`, `t_0_5`, `t_0_6` (J102).
* **No haul ropes, no cabins in motion.** The photograph's ropes run across the whole frame; a moving aerial tramway is not something this build simulates.
* **No cloud.** The reference's sky is a flat January overcast; nothing in this build reads a historical sky.
* **Beyond 400 m the terrain reads under the park ground on 26 % of 3,344 samples**, as the pavement does there.
* **2,753 agents were dropped** — **473 pedestrians in the carriageway without crossing**, 221 where the planimetric data has no sidewalk (J101), 4 cyclists and e-bikes the fleet exports without a rider, 2 vehicles where there is no roadway.
* **Only 9 trees are drawn from modelled branches** against **7,065** impostor cards out to 1,500 m.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| 0 of 13 rays clear | the subject is 911 m away and a member of its own model stands 49 m from the lens, so the tramway hides the tramway; the frame gate published it anyway (J100) | **verification — open (J100)** |
| the probe measured a 1,035 m tile mesh | every tan-brick surface in that tile is joined into one object, so the nearest fabric at the coordinate is a kilometre-wide mesh; the record refuses to use its extent and still reports its height (J94) | **geometry — open, the join is the fault** |
| the record names two different viewpoints | the item's viewpoint text and the camera's `eye_source` disagree about which end of the ride the eye is at, and nothing reconciles them | **verification — open, a record inconsistency** |
| the island station house is absent | the frame is at the Manhattan end; the station house is 900 m away and behind the subject's own structure | verification — the pairing |
| no fascia lettering | no printed copy is invented anywhere (B5, B15a) | declared decision |
| sd 0.489, p05 0.4536 | nearly half the frame is one flat water plane and the render holds no dark values; the photograph is a high-contrast winter frame developed 0.782 stops below the grey convention (J83) | geometry + reference |
| chroma 1.801 | a clear sky, tan brick and a taxi against a grey-blue January industrial scene | reference |
| the water is a mirror | open water is a flat specular plane with no wave state and no turbidity | geometry — open |
| no park ground for three tiles | 85 % of the city's mapped open space was never draped (J102) | data — open (J102) |
| no haul ropes, no moving cabins | an aerial tramway's ropes and cabins are not a class this build models or animates | geometry |
| 9 trees from modelled branches against 7,065 cards | the modelled-branch radius is 120 m and the impostor radius 1,500 m, so almost everything in a frame this deep is a card | performance — declared |
| 473 pedestrians in the carriageway, 221 off a walkable surface | the crowd model puts walkers where the placement test reads roadway or cannot read at all (J101) | verification — open (J101) |
| no cloud | nothing in this build reads a historical sky | reference — no source exists |
