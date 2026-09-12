# The New York Times Building (620 Eighth Avenue)

`landmark_new_york_times_building` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:2024-06-17 10_01_23 The front of the New York Times Building along 8th Avenue in Manhattan, New York City, New York.jpg by Famartin, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2024-06-17 10:01:23, 1920x1440. [Commons page](https://commons.wikimedia.org/wiki/File:2024-06-17_10_01_23_The_front_of_the_New_York_Times_Building_along_8th_Avenue_in_Manhattan,_New_York_City,_New_York.jpg) — the photograph's own view direction is derived from the image at **high** confidence.

**Camera** — 40.756316, -73.990567 (NYC_TM -3426, 6255) at z 14.3 m NAVD88 | azimuth 115.5°, pitch **+44.5°** | 18 mm on 36 mm (90.0° horizontal) | 1208x906. The camera stands on **this photograph's own EXIF GPS**, 119.1 m from the item's recorded viewpoint, and was **not moved**; the view azimuth is clear for 150 m and the item's recorded azimuth is 70.0°, **45.5° away**. The lens was widened to the **18 mm floor** and the axis tilted **44.5°** — the steepest tilt in the pass — for a subject that tops out **77° above the horizon** at 53 m; the top is still cut off and the record declares the verticals converge. The ground under it reads 12.708 m NAVD88, the **10th percentile of 113 samples within 12 m**, range 12.6 to 13.15 m.

**Sun** — azimuth 101.6°, elevation 49.5° at 2024-06-17T10:01:23−04:00, from the photograph's own **EXIF DateTimeOriginal**; 886.0 W/m² direct normal, sky at strength 0.0321, Filmic, **+0.67 stops** — **the least development of any sheet in the pass**. The linear frame's median is **0.113478** against a middle-grey target of 0.18, so this scene arrived within two-thirds of a stop of a photographable level on its own. The physical rule would have given **0.0 stops**.

**In the scene** — 4,500,299 triangles: 5 building tiles (255,234 tris), 4 landmark models of which 1 falls inside the 90.0° frame, 27,761 pavement polygons, 2,324 props, **8,251 kit pieces** — the most of any sheet in the pass — 14 park-ground meshes, 38,252 triangles of structures, 89 vehicles and 250 people.

## Verdict — the one sheet whose light needed almost no recovery, and the logo the photograph exists for is not on it

**+0.67 stops.** Every other daylight sheet in this pass needed between two and six stops of development to read as a picture, and several were published under-lit or clamped. This one metered at **0.113478** against a 0.18 target and needed two-thirds of a stop. A glass tower at ten in the morning with a 49.5° June sun on it is the one condition in which this build's light arrives already photographable, and the record shows it.

**The height is measured off the geometry and lands on the roof.** The nearest landmark model origin is `c_times_square`, **292.0 m** away with a catalogue height of **365.8 m** that belongs to the composite rather than to this tower, so the probe fell back to measuring: **43 rays, all 43 on built fabric**, **230.0 m** above a ground of 12.98 m. The New York Times Building's roof is at that height; its mast is not, and a downward probe does not land on a mast. J74 is why this sheet does not publish 365.8 m over a photograph of a different height.

**The sightline is the cleanest in the pass.** 13 rays, **all 13 clear**, **11 on the subject**, fraction **0.846**, with 9 landing on the tower's own nearer fabric and 2 passing into sky. Nothing blocks it — no lamp mast, no neighbour, no agent.

**And what the photograph is about is absent.** The reference is the Eighth Avenue front: a ceramic-rod screen wall carrying `The New York Times` in its own gothic type, five metres tall, across the whole facade, with the glazed lobby beneath it. **The render has a glass mullion grid.** No rods, no logo, no lobby, no street — a 44.5° tilt puts the frame entirely into facade and sky.

## What matches

* **The light, almost exactly.** 0.67 stops of development against a photograph developed **0.457 stops** below the grey convention — a difference of **0.635 stops**, and the only sheet in the pass where the render's own scene luminance was already close to right.
* **The height, from geometry** — 230.0 m measured, with the catalogue's 365.8 m correctly refused as belonging to a composite 292 m away (J74).
* **The sightline is unobstructed** — 13 of 13 rays clear, 11 on the subject.
* **The curtain wall reads as a curtain wall.** The mullion grid runs at the right pitch and the corner turns correctly, and 237 material slots resolved against the shared photographic catalogue.
* **This is the most heavily kitted frame in the pass** — 8,251 pieces, of which 222 storefronts, 55 scaffold pieces, 41 fire escapes, 39 parapets and 39 window accessories.
* **The block is furnished as the Port Authority block is**: 202 street lamps, 179 manholes, **125 hydrants**, **26 subway entrances**, 62 vent grates, 20 LinkNYC kiosks, 19 bus-stop signs, 13 newsstands, and 371 Citi Bike dock units (Stage 40).
* **The fleet is an Eighth Avenue weekday fleet**: **32 sedans, 22 yellow taxis, 13 SUVs, 8 boro taxis, 6 black cars, 5 box trucks**, a Sanitation truck, an MTA bus and a van, with the crowd clock reporting **a weekday** for 2024-06-17, which was a Monday.
* **The near park ground is clean** — under-fraction **0.0** over 72 samples within 150 m.

## What does not match

* **The logo and the ceramic-rod screen are absent**, and they are the whole reason this photograph was taken. Applied lettering at architectural scale and a rod brise-soleil are not classes this build models.
* **The lobby, the sidewalk and the street are out of frame.** At a 44.5° tilt from 53 m there is no room for them; the record says the frame is here to show the subject at all.
* **The render is twice as colourful as the photograph** — chroma **0.0814** against **0.0406** (**2.005×**). The reference is a near-monochrome of grey ceramic and grey glass; the render's sky and brick neighbour are more saturated.
* **Seventy per cent of the photograph's contrast** — standard deviation **0.1793** against **0.2521** (**0.711×**), 95th percentile **0.7369** against **0.8269**. The photograph holds a bright sky beside a dark lobby recess; the render has neither.
* **A brighter midtone** — median **0.4887** against **0.3975** (**1.229×**), mean **0.4481** against **0.4115** (**1.089×**) — most of which is the 0.635-stop development difference (J83).
* **7,717 of 8,251 kit pieces are windows**, against **10 cornices, 13 pilasters, 7 string courses and 4 quoins**, and kit was still capped by a **1,338,624-triangle** budget with **45,560 pieces in range**.
* **Only 5 trees are drawn from modelled branches** within 120 m, against **990 impostor cards** out to 619 m — the lowest modelled-to-card ratio in the pass.
* **Twenty-nine props across five kinds were wanted in range and had no asset**: 21 misc structure, 3 artwork, 3 passenger-information sign, 1 drinking fountain, 1 parks comfort station.
* **Every one of the 89 vehicles is at LOD2.** Three people are at LOD0.
* **The crowd is a fraction of the ask.** The density table wanted **1,217 vehicles and 2,174 people**; **1,321 and 2,173** were simulated and **3,155** dropped — 1,033 pedestrians and 862 vehicles outside the radius, **693 pedestrians and 335 vehicles at the agent triangle budget**, 138 in the carriageway without crossing, 54 not on a walkable surface, 2 pedestrians and 2 vehicles inside buildings, and **20 riderless bodies**.
* **Far park ground sinks hard**: beyond 400 m the under-fraction is **0.3064** over 1,126 samples with a minimum clearance of **−9.438 m**.
* **4 of the 5 tiles in range have no structures file.**
* **The Times Square landmark is reported 59.2° off axis** at 198.3 m — the frustum test uses the composite's centroid, and this tower is one piece of it.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| no logo, no ceramic-rod screen | architectural-scale lettering and a rod brise-soleil are not classes this build models | **geometry — open, no class** |
| no lobby, no sidewalk, no street in frame | a 44.5° tilt is what it takes to contain a subject 77° above the horizon at 53 m; declared in the record | verification — declared |
| chroma 2.005×, sd 0.711× | a near-monochrome reference of grey ceramic and glass against a Nishita sky and a brick neighbour | reference |
| p50 1.229× | the photograph is developed 0.457 stops under the grey convention and the render 0.178 over it (J83) | reference |
| 7,717 windows against 10 cornices | shells are extruded footprints with openings cut, and kit was capped at 1,338,624 triangles with 45,560 pieces in range | geometry + performance |
| 5 modelled trees against 990 cards | the props triangle budget puts almost everything on impostor cards at this radius | performance |
| 29 props across five kinds unmapped | no asset exists for those kinds | data |
| every vehicle at LOD2 | the LOD ladder at this distance under the agent budget | performance |
| 250 people against a table asking 2,174 | the agent triangle budget plus the placement rules, each with its count | performance + verification |
| 0.3064 of far park-ground samples under the terrain, minimum −9.438 m | surfaces draped on the 2 m heightmap against a scene edge coarsened to 40 m | verification |
| the frustum reports Times Square 59.2° off axis | the test uses the composite model's centroid and this tower is one piece of it | verification — a known limit of the test |
