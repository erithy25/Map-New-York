# Brooklyn Bridge from the pedestrian walkway

`landmark_brooklyn_bridge_walkway` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:2024-06-15 09 53 30 View from the middle of the Brooklyn Bridge looking northwest along the pedestrian walkway in Manhattan, New York City, New York.jpg by Famartin, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2024-06-15 09:53:30, 1920x1440. [Commons page](https://commons.wikimedia.org/wiki/File:2024-06-15_09_53_30_View_from_the_middle_of_the_Brooklyn_Bridge_looking_northwest_along_the_pedestrian_walkway_in_Manhattan,_New_York_City,_New_York.jpg)

**Camera** — 40.705771, -73.996343 (NYC_TM -3911, 647) at z 16.0 m NAVD88 | azimuth 316.8°, pitch +0.0° | 35 mm on 36 mm (54.4° horizontal) | 1208x906.

**Sun** — azimuth 100.1°, elevation 48.1° at 2024-06-15T09:53:30-04:00 (EXIF DateTimeOriginal); 880.4 W/m² direct normal, sky at strength 0.0322, Filmic, +1.86 stops.

**Subject** — Brooklyn Bridge Manhattan tower at 340.0 m.

**In the scene**, within 900.0 m of the camera and not all of it in frame — 8 building tiles (206,546 tris), 5 landmark models of which **1 can fall inside the 54.4° frame**, 21,495 pavement polygons (13,791 white, 2,638 roadbed, 2,265 curb, 1,263 sidewalk, 674 crosswalk, 372 yellow, 292 median, 140 parking lot, 60 plaza), 4538 props of the 4,539 in range, 0 kit pieces ("no kit_placements.bin in range"), 34 vehicles and 139 people; 1,950,107 triangles. Ground mesh 100,352 triangles, 0 holes. 20 city surfaces are dressed from the shared photographic catalogue.

| | render | photograph | ratio |
|---|---|---|---|
| mean | **0.5035** | **0.457** | **1.102** |
| sd | **0.1533** | **0.2068** | **0.741** |
| p05 | **0.2508** | **0.0779** | — |
| p50 | **0.4987** | **0.4634** | **1.076** |
| p95 | **0.7244** | **0.7926** | — |
| chroma | **0.0895** | **0.2127** | **0.421** |
| exposure_offset_stops | **0.242** | **0.014** | **0.228** |

## Verdict — the camera stands under the deck, not on the promenade; the tower is in the frame as a plain grey block, and the record scores that block as the thing blocking the view of it

**The two halves face the same way from the same place, and they are not the same view.** The camera is on the photograph's EXIF GPS, **46.2 m** from the item's recorded viewpoint, aimed on the bearing from that GPS to the subject coordinate (**316.8°**; the recorded **318.9°** is 2.1° away), at the EXIF instant. The photograph is the promenade: a timber boardwalk to the vanishing point, brown lattice railings both sides, cable stays fanning up to the Manhattan tower at half the width with its two Gothic arches and a flag, six walkers ahead (counted at full size, just past half the width and half the height), Lower Manhattan behind with One World Trade Center's spire at about a quarter of the width. The render looks along the *underside* of the bridge. Its eye is **16.0 m** above the water, from an `eye_source` reading "deck about 14.4 m above the water at that chainage" — the Brooklyn tower *approach* — while the GPS puts the camera on the main span; the record says so itself: the recorded viewpoint is "inside lm_b_brooklyn_bridge.45 (a ray straight up from the eye point hits its roof)", and the camera was walked **8.0 m** to the right into the air beneath the deck. So a flat grey slab enters at the top at about half the width, its underside running down to the left edge a quarter of the way down, and ends at a plain grey block spanning a third to a half of the width between four-tenths and six-tenths of the height, its foot in the river; above the slab's right edge a narrow, lighter, stepped column climbs to a tenth of the height. That block and column are the Manhattan tower's model: the record's own sightline closes at **229.6 m** on `lm_b_brooklyn_bridge.97`, and that is where the tower is, because the subject coordinate is a point on the roadway a hundred metres or so short of it (**DEVIATIONS J82**). The thing named at **340.0 m** is deck.

**The record's verdict is a measurement of the deck seen from below.** `subject_visible` is true at **0.538**, 7 of 13 rays — and `subject_rays_on_own_fabric_nearer_than_recorded` is also 7, the aimed ray landing at **213.6 m** on `lm_b_brooklyn_bridge.45`, the object the camera was moved out of. The rule is "at least one ray lands on the subject" (J78), and the subject is any part of a model whose plan extent is **761.6** by **728.2 m** — the whole bridge. The height probe is the same shape (J74): **51.28 m** off `lm_b_brooklyn_bridge.34`, 36 of 43 rays on built fabric, is bridge fabric at a point on the span, and the fan was sized to it (aimed **25.6 m** up). No tower height is in this record. The clearance walk was scored on this sightline (J79), so a position under the bridge passed as one that sees the subject.

**What the reader must not take from this sheet.** Nothing in the render is the walkway, the cables, the railings or the lamps. The grey carriageway in the lower left with a raised pale strip is the road network's surface for the bridge drawn at the heightmap, which under the span is the river (`terrain_z_m` **0.0**); the **26** figures on that strip and the single yellow taxi at its far end (counted at full size, of **139** people and **34** vehicles placed) are the Saturday crowd on a pavement polygon lying on the East River. The building stock either side is real and the exposure is metered. The fault is the viewpoint's height and the subject's coordinate, not the city.

## What matches
* **The frame is the photograph's frame**: its GPS, the bearing derived from it, a 35 mm lens, a level axis and its EXIF instant — a Saturday, and the crowd is drawn for Saturday.
* **The skyline's massing is where the photograph has it.** Dark glass towers in the left fifth where the photograph has the Financial District; a pale slab-sided tower right of the block at about six-tenths of the width, where the photograph has the Verizon building's blank flank right of the tower; tan and brown blocks along the far shore under **4,404** trees.
* **The Sun is right and the shadows fall the right way.** Azimuth 100.1°, elevation 48.1°, behind the camera to the right: the walkers' shadows in the photograph and the deck's shadow in the render both run forward-left. Sampled with PIL: the raised strip is the only render surface with pixels above 0.7 (nine in ten of them); the block's face toward the camera sits in the deck's shadow and reads under 0.4; the slab's underside about a half.
* **The development is not the gap.** Metered at **+1.86** stops (the physical rule alone gives 0.0), far under the +4 at which the record calls a scene under-lit; exposure offset **0.242** stops against the photograph's **0.014**; mean 0.5035 against 0.457, p95 0.7244 against 0.7926.

## What does not match
* **The eye is under the deck.** 16.0 m from an approach-chainage 14.4 m plus 1.6 m; the clearance walk moves it 8.0 m sideways rather than up. The photograph's eye is on the boardwalk (J65).
* **The tower is a block.** Granite, two pointed arches and a flag in the photograph; a flat-faced block with a stepped column in the render, which the record names a *blocker* (`lm_b_brooklyn_bridge.97` at 229.6 m).
* **The subject is not the tower.** Named at 340.0 m; the height 51.28 m and plan extent 761.6 × 728.2 m are the bridge's, measured on the span (J82, J74). The 0.538 fraction is 7 rays on the deck at 213.6 m.
* **The bridge's road runs on the water.** Roadbed, white lane markings and a sidewalk strip (from the 2,638 roadbed, 13,791 marking and 1,263 sidewalk polygons) lie at 0.0 m with 26 people and one taxi on them while the deck passes overhead. The photograph's walkers are six, on timber.
* **No promenade fabric.** Kit pieces **0** ("no kit_placements.bin in range"); the lattice railings, lamp standards and the wire waste basket at the photograph's lower left have no counterpart.
* **Chroma 0.0895 against 0.2127** (ratio 0.421): grey slab, grey block, grey road and grey-blue water against brown-painted steel, weathered timber and blue glass (J66).
* **p05 0.2508 against 0.0779**: deep shadow under the railings and in the glass in the photograph; nothing darker than a quarter-tone in the render (sd 0.1533 against 0.2068). Far above the JPEG floor, and not the development.

## Cause of each gap
| gap | cause | class |
|---|---|---|
| the eye is under the deck | 16.0 m is the tower approach's "deck about 14.4 m above the water", applied on the main span; the walk resolved "inside the deck" by moving 8.0 m sideways above a heightmap that is the river | verification, **DEVIATIONS J65** |
| the tower is a block | the bridge model's tower carries no arches, saddles or masonry detail, and the record treats the tower geometry as a blocker | geometry, **DEVIATIONS J82** |
| the subject is not the tower | the coordinate stands on the roadway a hundred-odd metres from the tower; height, fan and sightline follow the fabric there, and any part of the model counts | data, **DEVIATIONS J82 / J74 / J78 / J79** |
| the bridge's road runs on the water | the road network's carriageway polygons are drawn at the heightmap, 0.0 m under the span; the deck is a separate landmark mesh above them | geometry |
| no promenade fabric | no kit placements exist in range; railings, lamp standards and the boardwalk are not props the placer knows | data |
| chroma 0.0895 against 0.2127 | one material family per facade class and untextured landmark grey; the bridge's painted steel and timber are not dressed | material, **DEVIATIONS J66** |
| p05 0.2508 against 0.0779 | no railing lattice, cable shadows or dark glass reveals in the frame; the development is metered (J83) and is not the cause | geometry |
