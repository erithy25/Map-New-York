# Manhattan Municipal Building

`landmark_municipal_building` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Manhattan Municipal Building April 2022 003.jpg by Kidfly182, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2022-04-16 14:06:42, 1920x1440. [Commons page](https://commons.wikimedia.org/wiki/File:Manhattan_Municipal_Building_April_2022_003.jpg) — the photograph's own view direction is derived from the image at **high** confidence.

**Camera** — 40.712711, -74.004792 (NYC_TM -4630, 1413) at z 13.4 m NAVD88 | azimuth 81.6°, pitch +24.3° | 18 mm on 36 mm (90.0° horizontal) | 1208x906. The camera stands on **this photograph's own EXIF GPS**, 166.6 m from the item's recorded viewpoint, and was **not moved**; the item's recorded azimuth is 131.3°, **49.7° away**. The lens was widened to the **18 mm floor** and the axis tilted **24.3°** for a subject that tops out **57° above the horizon** at 68 m; the top is still cut off and the record declares the verticals converge. The ground under it reads 11.797 m NAVD88, the **10th percentile of 113 samples within 12 m**, range 11.62 to 12.78 m. The nearest built thing in the frame is `prop_lamp_cobra_davit_12` **9.9 m** away at 15° off axis; the nearest simulated agent is 38.5 m away.

**Sun** — azimuth 212.2°, elevation 55.8° at 2022-04-16T14:06:42−04:00, from the photograph's own **EXIF DateTimeOriginal**; 907.3 W/m² direct normal, sky at strength 0.0314, Filmic, **+2.07 stops**, measured from the linear frame's median of **0.042929** (J83). The physical rule would have given **0.0 stops**.

**In the scene** — 4,500,245 triangles: 6 building tiles (253,212 tris), 7 landmark models of which 1 falls inside the 90.0° frame, 34,834 pavement polygons, 733 props, 4,033 kit pieces, 30 park-ground meshes with **53,345 faces cut for landmark ground**, 44,256 triangles of structures, 57 vehicles and 374 people.

## Verdict — the closest tonal agreement in the whole pass, on a frame that measures the base of the building and not the building

**The two halves were developed to within eight hundredths of a stop of each other.** The photograph's median sits **0.300 stops** above the middle-grey convention and the render's **0.218** — a difference of **0.082 stops**, the closest in the pass — and the medians follow: **0.4949** against **0.5081**, a ratio of **0.974**. On the one sheet where the tonal comparison is essentially free of the development choice, what remains is the scene, and the scene disagrees in two specific ways.

**The height measured is the base, not the tower.** The probe casts **43 rays** of which **38 land on built fabric**, and reports **105.82 m** above a ground of 11.14 m on `lm_municipal_building.3`, an object **117.1 m by 99.5 m** in plan. The catalogue's figure for `municipal_building`, whose origin sits **35.9 m** away, is **177.1 m** — the tower with Civic Fame on it. What the coordinate stands on is the great colonnaded base block; the tiered tower above it is a different piece. This is the third sheet in the pass with that distinction, after the Grand Central facade and the New York Stock Exchange, and the sheet reports the measured figure as it should.

**A street lamp nine metres from the lens takes most of the sightline.** `prop_lamp_cobra_davit_12` stands **9.9 m** away and blocks the fan at **10.0 m**: of 13 rays, 9 are clear but only **4 land on the subject**, for a visible fraction of **0.308**, with 3 passing into sky. That is the fourth sheet in this pass whose sightline is spoiled by a cobra-head mast (J88).

**And the building's whole sculptural programme is absent.** No gilded Civic Fame on the crown, no corner cupolas, no tiered setbacks, no deep Beaux-Arts cornice — the render is a tan mass with a regular grid of square windows over a dark base and a colonnade. **24 artwork props** were wanted in range and had no asset, the largest artwork shortfall in the pass, which is what City Hall Park is: the densest monument ground in the city.

## What matches

* **The massing is broadly right**: a very large block with a colonnaded screen at its base, a darker plinth course, and a tower rising off centre — recognisable as the building's silhouette if not its detail.
* **The tonal agreement is the best in the pass** — 0.082 stops of development apart, medians within three per cent.
* **The colonnade is there.** Round columns stand along the right of the render's base where the photograph's screen runs, and **19 pilasters, 30 cornices and 28 string courses** are placed in the scene.
* **The civic plaza is paved as a plaza** — 34,834 pavement polygons including **4,518 plaza** polygons and **285 yellow markings**, and **80 benches**, which is what Foley Square and City Hall Park carry.
* **106 trees are drawn from their modelled branches** within 120 m — the second-highest count in the pass — against 179 impostor cards beyond.
* **The near park ground is clean**: within 150 m the under-fraction is **0.0** over 430 samples, median clearance **0.194 m**, and the landmark's own ground is cut into it (**53,345 faces**).
* **The scaffolding is there.** **158 scaffold pieces** stand in this scene — Lower Manhattan is permanently under sidewalk shed, and this is the second-highest scaffold count in the pass.
* **The kerb-side furniture faces the kerb** (J84): 89 street lamps, **9 subway entrances**, 14 vent grates, 21 waste baskets, 9 flagpoles.
* **111 Citi Bike dock units** are in range (Stage 40).

## What does not match

* **Civic Fame, the cupolas, the tiered crown and the cornice profile are all missing.** The photograph's subject is its ornament; the render's is an extruded mass with openings cut. **3,610 of 4,033 kit pieces are windows**, and kit was capped by a **920,736-triangle** budget with **44,407 pieces in range** — one piece in eleven drawn.
* **The measured height is the base's, 71 m short of the catalogue's tower**, because the recorded coordinate stands on the 117 m-wide block.
* **A cobra-head lamp 9.9 m from the lens cuts the visible fraction to 0.308.**
* **The render is more than half again as colourful as the photograph** — chroma **0.1125** against **0.0651** (**1.728×**). The reference is grey limestone against a blue-grey sky; the render's tan shell, brick base and green trees are far more saturated. This is the per-building facade colour gap (J66) in its clearest form: the shell carries one catalogue course and the real building is pale grey stone.
* **Three-quarters of the photograph's contrast** — standard deviation **0.2044** against **0.2731** (**0.748×**), 95th percentile **0.8468** against **0.9147**.
* **No cloud.** The reference's sky is broken cumulus; nothing in this build reads a historical sky.
* **The monuments are absent.** 24 artwork, 7 memorial, 10 drinking fountain, 9 parks building and 6 misc structure props were wanted and had no asset — 56 objects across five kinds.
* **2,121 tree rows did not fit the props budget**, capped at **1,077,022** triangles.
* **804 pedestrians were dropped for standing in the roadway without crossing** — the highest such count in the pass — along with 179 for no sidewalk, **390 at the agent triangle budget**, 244 vehicles at the same, 26 vehicles for no roadway in the planimetric data, and **24 riderless bodies**. The density table wanted **660 vehicles and 4,775 people**; **768 and 2,997** were simulated and **3,334** dropped.
* **The parked rank along the barrier** reads as a continuous line of dark cars where the photograph shows none — the traffic model's kerb occupancy at this instant.
* **2 of the tiles in range have no structures file.**
* **Far park ground z-fights at 0.0303** beyond 400 m, over 791 samples, though the under-fraction there is a mild **0.1062**.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| no Civic Fame, no cupolas, no tiered crown, no cornice profile | the shell is an extruded footprint with openings cut, kit capped at 920,736 triangles with 44,407 pieces in range, and architectural sculpture is not a class this build models | **geometry + performance** |
| measured height 105.82 m against a catalogue 177.1 m | the recorded coordinate stands on the 117.1 m by 99.5 m base block and the tower is a separate piece; the sheet reports what it measured (J74). Third such case after Grand Central and the NYSE | **verification — open, the item's coordinate** |
| the visible fraction is 0.308 | a cobra-head lamp 9.9 m from the lens blocks the fan at 10.0 m; the walk clears built fabric along the azimuth and does not weigh props (J88) | verification — open |
| chroma 1.728× | the shell carries one catalogue brick course where the real building is pale grey limestone; no per-building facade colour exists (J66) | data — no source exists |
| sd 0.748×, no highlight near white | the photograph holds a bright broken sky beside grey stone in shadow | reference |
| no cloud | nothing in this build reads a historical sky | reference — no source exists |
| 56 monument props across five kinds unmapped | no asset exists for artwork, memorial, drinking fountain, parks building or misc structure, on the city's densest monument ground | data |
| 2,121 tree rows dropped | the props triangle budget at 1,077,022 triangles | performance |
| 804 pedestrians in the roadway without crossing | the crowd model put them there and the placement rule dropped them, each with its count | verification |
| a continuous rank of parked cars | the traffic model's kerb occupancy at this instant | verification |
