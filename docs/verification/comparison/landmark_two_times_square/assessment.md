# Two Times Square (714 Seventh Avenue)

`landmark_two_times_square` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Times Square - panoramio (14).jpg by TomasEE, CC BY 3.0 (https://creativecommons.org/licenses/by/3.0), taken 2012, 1920x1278. [Commons page](https://commons.wikimedia.org/wiki/File:Times_Square_-_panoramio_(14).jpg) — the view direction is derived from the image. It is the canonical shot down Seventh Avenue: both walls of the bowtie carrying a continuous field of lit advertising, buses and taxis in the carriageway, planters along the median, and the wedge of Two Times Square closing the left side.

**Camera** — 40.758692, -73.985089 (NYC_TM -2975, 6526) at z 16.3 m NAVD88 | azimuth 12.3°, pitch +4.2° | 18 mm on 36 mm (90.0° horizontal) | 1280x852. The camera stands on **this photograph's own EXIF GPS**, **22.6 m** from the item's recorded viewpoint, and the heading is the bearing from that GPS to the subject — **7.7°** off the item's recorded 20.0°. It was then moved **13.9 m** onto the nearest plaza polygon: *"boxed in: the view azimuth is closed off 44 m ahead, less than the 57 m this frame needs to show its subject"*. The walk scored on the subject's own sightline and its chosen point measured **0.462**, which is what the sheet published. From there the view is clear for **68.7 m** and **nothing built stands within 20 m of the lens**. The ground under the lens reads 14.661 m NAVD88 from 16 samples within 5.0 m, and the record notes that **no surface was named** in the viewpoint note, so the heightmap median within 5 m was used. The lens is at the **18 mm floor** and the record declares the verticals incomparable with the photograph on proportion.

**Sun** — azimuth 85.5°, elevation 32.1° at 2012-06-21T08:30:00−04:00, and the instant is **chosen, not measured**. The record spells out the rule in full: *"photograph year only, 21 June assumed, and 08:30 **chosen**, not measured: of the hours that put the Sun above 20 deg it is the one whose bearing (85 deg) comes closest to the view azimuth (20 deg), 65 deg off, so the Sun is behind the camera and lights what it looks at"* (J80). 788.2 W/m² direct normal, sky at strength 0.0352, Filmic, **+0.99 stops** — metered on a linear median of **0.090541**, half the 0.18 target, because putting the Sun behind the camera is what keeps this frame out of the under-lit band. The physical rule would have given 0.42.

**In the scene** — 4,500,095 triangles: 6 building tiles (332,446 tris), 4 landmark models, 24,014 pavement polygons, 1,763 props with **nothing dropped for budget**, 6,659 kit pieces, 22 park-ground meshes, **1 tile of structures (21,408 tris) with 5 having no file**, 58 vehicles and 294 people.

## Verdict — the subject is built to 160.6 m and the sheet measured a tile roof membrane at 78.0 m, a kilometre wide

**This is the clearest single case of J94 in the pass.** `subject.height_probe.object` is **`t_-3_6_roof_membrane`** — not a landmark object at all, but the joined mesh holding every roof-membrane surface in one tile. Its recorded plan extent is **1,074.9 by 1,069.5 m** with `is_tile_mesh: true`, and the height it reports is **78.0 m**. Only **8 of 43** probe rays found fabric.

**Two Times Square is modelled, to a height the builder derived and declared.** `blender/landmarks/c_times_square.py` builds it from the real footprint of BIN 1024742 with `H_TWO` = **160.6 m**, and its dimensions block says where that came from: *"Two Times Square [1,542 m2 site]: 160.6 m — no published architectural height exists, so the OTI LiDAR roof"* is used, with the inference stated again in the fidelity note. So the sheet published **less than half** its subject's modelled height, measured off a tile-wide roof plane.

**And the record is inconsistent about the same object in the same breath.** The sightline's horizontal fan is **12.0 m** — the floor — because something in the fan builder refuses a tile mesh's plan extent as a width. Its vertical fan is **77.9 m**, taken straight from that same tile mesh's 78.0 m height. One object, refused across and accepted up. If the width is untrustworthy the height is too, and J94's repair needs to apply to both.

**What the frame shows is a plaza.** After the 13.9 m move the camera stands on Duffy Square's paving, and the lower two thirds of the render is that surface. Above it: blank white panels on the buildings left and right, the Duffy plinth, three flagpoles, a low green kiosk, the red wedge of the TKTS steps at the right, and a handful of pedestrians. The photograph's Seventh Avenue, its buses, its planters and its taxis are all out of frame, and its advertising — which is the whole content of the left half — is on this sheet as **296 blank billboard faces**, the second-largest billboard count in the pass. Chroma **0.478**, a stop and three eighths of exposure difference, p50 **1.572×**.

**Two things here are better than most of the pass.** Nothing was dropped for the props budget: **1,763 props placed** across seventeen kinds. And **5,718 kit pieces were suppressed under the landmark shells** — the highest such figure on any Times Square sheet — which is the composite doing its job rather than a fault, though it means the detail of those blocks is whatever the composite's own builder authored.

## What matches

* **Nothing was dropped for the props budget**: 1,763 placed across seventeen kinds, including 1,074 trees, 181 Citi Bike dock units, 137 cooling towers, 108 street lamps, 94 manholes, 65 hydrants, **19 LinkNYC kiosks** and **12 newsstands**.
* **The bowtie is paved as the bowtie**: 24,014 polygons with 7,502 white markings, 6,238 sidewalk, 4,703 roadbed, 3,466 curb, **1,423 plaza** and 428 crosswalk.
* **The chosen instant is chosen for a reason, and the reason is recorded.** The Sun is put behind the camera so the frame lights what it looks at, and the consequence is measurable: this frame needed only **0.991 stops**, where the other Times Square sheets needed three to five (J80, J83).
* **The walk scored on the subject's sightline** and its chosen point's measured fraction, 0.462, is exactly what the sheet published — no discrepancy between the score and the render (J79, J100).
* **Twelve of thirteen rays are clear**, a clear fraction of **0.923**, and six land on the subject.
* **The camera is the photograph's own GPS**, and nothing built stands within 20 m of the lens.
* **The fleet is a Times Square fleet**: 17 yellow taxis of 58 vehicles, with 12 sedans, 11 boro taxis, 9 SUVs, 5 black cars, 3 vans and a box truck.
* **The subject's own modelled height is derived and declared**: 160.6 m from the OTI LiDAR roof, because no published architectural height exists.

## What does not match

* **78.0 m published for a 160.6 m subject**, measured off a joined tile roof membrane **1,074.9 m** wide (J94).
* **The same object is refused across and accepted up**: a 12.0 m fan width against a 77.9 m fan height, both from that tile mesh.
* **Only 8 of 43 probe rays found fabric.**
* **296 blank billboard faces**, the second-largest count in the pass, where the photograph's content is the advertising itself (B15a).
* **Chroma 0.478** on the most colourful block in the city.
* **A 1.375-stop exposure gap**: the photograph sits 1.128 stops below the grey convention and the render is metered to 0.247 above it, so mean reads 1.31× and p50 **1.572×** (J83). The render holds slightly more contrast, sd 1.138×.
* **The frame is a plaza, not the avenue.** The 13.9 m move put the camera on Duffy Square's paving and the lower two thirds of the picture is that surface; the photograph's carriageway, buses, planters and taxis are out of frame.
* **The verticals converge** at 18 mm, and the record declares the two halves incomparable on proportion.
* **The heading is 7.7° off the item's own recorded azimuth**, because it is the bearing to a subject coordinate rather than the direction the item describes.
* **Structures are almost absent**: 1 tile imported for 21,408 triangles with **5 having no file**, over the busiest interchange in the system.
* **The kit was capped at 1,292,392 triangles** and spent on windows: 5,893 of them against **26 cornices**; a further **5,718** pieces were suppressed under the landmark shells.
* **508 of the 1,074 trees are a substituted species** (J108), and only 3 are drawn from modelled branches.
* **294 people where the density table asked 1,333.** 967 vehicles and 1,333 people were wanted; 1,168 and 1,884 were simulated and **2,696 dropped** — 742 pedestrians outside the radius, 561 at the agent budget, 538 vehicles at the budget, 513 outside the radius, 182 in the carriageway without crossing, **98 not on a walkable surface** (J101), 36 riderless bodies, 23 off the carriageway and 7 above the observer.
* **The park ground has no samples inside 150 m** and 0.254 of 815 samples beyond 400 m sit under the terrain, worst case −2.056 m.
* **No cloud, and no lit signage.** The photograph's sky is a bright 2012 summer sky above a wall of light; the render's is a Nishita dome at strength 0.0352.

## Measured for this assessment

| figure | where it comes from |
|---|---|
| Two Times Square is built from BIN 1024742 to 160.6 m, and that height is the OTI LiDAR roof because no published architectural height exists | the `B_TWO` and `H_TWO` constants of `blender/landmarks/c_times_square.py`, its dimensions block — *"Two Times Square [1,542 m2 site]: 160.6 m"* — and its fidelity note, which states the inference again |
| the probe's object is the tile's joined roof-membrane mesh | the record's own `probe.object` of `t_-3_6_roof_membrane` with `plan_extent.is_tile_mesh` true and an extent of 1,074.9 by 1,069.5 m (J94) |
| the fan refuses that extent across and accepts it up | the recorded `subject_fan_m` of 12.0 — the floor — against the recorded `subject_fan_tall_m` of 77.9, both derived from the same object |
| the second-largest billboard count in the pass | counted over every record's `scene.kit.per_category`: the TKTS booth sheet carries 331 and this one 296 |
| the highest kit suppression of any Times Square sheet | this sheet's 5,718 against the TKTS booth's 4,454, One Times Square's 9,468 being a different composite radius |

## Cause of each gap

| gap | cause | class |
|---|---|---|
| 78.0 m published for a 160.6 m subject | the height probe measures the object standing at the subject's coordinate, and here that is the tile's joined roof-membrane mesh rather than the landmark shell built at the same place (J94) | **verification — open, and this is the clearest case of it in the pass** |
| the fan width is refused and the fan height is not | the fan builder falls back to a 12 m floor when the plan extent is a tile mesh, and takes the same object's height without the same test (J78, J94) | **verification — open** |
| 296 blank billboard faces | the faces carry named material slots and a defined UV and no content, because no advertising copy was invented anywhere (B5, B15, B15a) | **declared decision** |
| chroma 0.478 | the same blank faces, on the most colourful block in the city | declared decision |
| the frame is a plaza | the recorded viewpoint was boxed in at 44 m against the 57.3 m the frame needs, so the walk moved 13.9 m onto plaza paving (J79) | verification — declared |
| the heading is 7.7 deg off the item's azimuth | the heading is the bearing from the photograph's GPS to the subject's coordinate rather than the direction the item records | verification — open |
| 1.375 stops of exposure difference | the photograph was developed 1.128 stops under the grey convention and the render is metered to it (J83) | reference — declared, and correct |
| the sun instant is assumed | the reference carries only a year, so an hour was chosen to light the view, and the choice is recorded with its reasoning (J80) | **declared decision — and the right one** |
| 21,408 triangles of structures | five of the six tiles in range have no structures file (B13 remainder) | data — open |
| 26 cornices drawn | the kit triangle budget at 1,292,392 triangles, spent windows-first | performance |
| 508 substituted tree species, 3 modelled canopies | the asset set is ten species with two states, and only 3 rows fall inside the 120 m branch band (J108) | data + performance |
| 294 people where the table asked 1,333 | the 1,125,000-triangle agent budget plus the placement rules (J101) | performance + verification |
| no park-ground samples inside 150 m | nothing park-like stands within 150 m of this lens | verification — not a fault |
| no cloud | nothing in this build reads a historical sky | reference — no source exists |
