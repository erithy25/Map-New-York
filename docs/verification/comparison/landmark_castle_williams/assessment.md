# Castle Williams (Governors Island)

`landmark_castle_williams` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Castle Williams window.jpg by Nvss132, CC0 (http://creativecommons.org/publicdomain/zero/1.0/deed.en), taken 2022-09-19 12:04:30, 1920x1440. [Commons page](https://commons.wikimedia.org/wiki/File:Castle_Williams_window.jpg) — the photograph's own view direction is derived from the image at **high** confidence.

**Camera** — 40.69299, -74.01968 (NYC_TM -5824, -788) at z 3.9 m NAVD88 | azimuth 118.7°, pitch +4.7° | 35 mm on 36 mm (54.4° horizontal) | 1208x906. Position and heading both come from the photograph: its own EXIF camera GPS, **244.6 m** from the item's recorded viewpoint — inside the 250 m rule by five metres — and 118.7° is the bearing from there to the subject. The item's recorded azimuth of 270.0° is **151.3° away**: the nominal viewpoint faces the fort from the other side. The lens stayed at 35 mm and the axis was tilted **+4.7°** to the subject's mid-height, 11 m above its ground. The recorded viewpoint was **hard against `t_-6_-1_brownstone`, 1.2 m ahead along the view azimuth**, so the camera was **moved 65.8 m** onto the nearest surveyed roadbed polygon, scored on the subject's sightline — which returned **13 of 13 rays on the subject** at the chosen point. From there the azimuth is clear for **60 m** against the 24.5 m needed, the nearest built thing is `prop_tree_honeylocust_small_15` **8.2 m** away at +10.5° pitch, and the nearest simulated agent is a black car **2.3 m** from the lens. Ground under the camera reads **2.29 m** NAVD88 from 16 heightmap samples within 5.0 m, range 2.25 to 2.36 m.

**Sun** — azimuth 162.5°, elevation 49.3° at 2022-09-19T12:04:30−04:00, from the photograph's own **EXIF DateTimeOriginal**; 885.4 W/m² direct normal, sky at strength 0.0321, Filmic, **+1.10 stops and not clamped**. The linear frame's median is **0.084156** against a middle-grey target of 0.18; the physical rule would have given **0.0 stops** (J83).

**In the scene** — 2,605,339 triangles: 3 building tiles (11,054 tris) with **1 tile missing**, 3 landmark models of which 1 falls inside the 54.4° frame, 4,519 pavement polygons with **0 dropped**, 2,475 props, 4,489 kit pieces, 4 park-ground meshes over 15 surfaces, 4 structures tiles with **none missing** (24,504 tris), 86 vehicles and 7 people, terrain 88,200 tris at 2.0 m near / 40.0 m far with no holes.

## Verdict — this sheet reports a visible fraction of 1.000 and the fort is not in the picture; what is in the picture is eighty-six private cars parked along a kerb on an island that has been car-free for twenty years

**The verdict is the most misleading number in the pass.** `subject_visible_fraction` is **1.000**: 13 rays cast, **13 clear, 13 on the subject**, nothing into nothing. And the frame contains no fort. It contains a street: a row of parked sedans and SUVs receding to the right, a four-storey brick barracks block behind them, street trees, a kerb and a broad asphalt roadway.

**The reason is the object the probe found.** `t_-6_-1_roof_membrane` — **a tile mesh**, every roof-membrane surface on Governors Island joined into one object, extent **775.6 m by 268.0 m**. The record knows what it is and says so twice: *a tile mesh is every building of one material in the tile, so its extent is not the subject's and is not used*, and separately that the height came from the geometry because the nearest catalogue origin is 147.4 m away (J74). But the sightline still aims at that object, and because the object spans the whole island, **every ray lands on it**. The ray that gets closest lands on `t_-6_-1_brownstone` at **6.9 m** — a brownstone wall seven metres from the lens. Thirteen of thirteen rays hitting a wall seven metres away is reported as the subject being fully visible.

**This is the compound case for J92 and J94 together.** J94 says the probe takes whatever object stands at the coordinate; here that object is a 775-metre tile mesh. J92 says nothing measures what fills the frame; here what fills the frame is a car park. Put together they produce a certified perfect score on a sheet that contains none of its subject.

**And the cars are their own fault.** Governors Island carries no private traffic. The build already has the rule: the Belvedere Castle sheet records **21 vehicles dropped** with the reason *the road graph put them on Central Park's East, West, Terrace or Center Drive, which have carried no private traffic since 2018*. No equivalent rule exists for Governors Island, so the simulation placed **86 vehicles** — 58 sedans, 26 SUVs, 2 boro taxis, 1 black car and 1 police car — along the esplanade, and the drop list on this sheet contains no car-free-drive reason at all.

**The reference, meanwhile, is a close-up of one barred window.** Red sandstone ashlar, a steel grille, a dark casemate behind it, photographed from about two metres. It is a photograph of masonry detail, not of the fort — the seventh sheet in this queue whose reference is not of its subject (**J93**).

## What matches

* **The development is metered and unclamped**, +1.10 stops from a median linear luminance of 0.084156, against a physical rule that would have given 0.0.
* **The tonal figures are close**: mean **0.935×**, median **0.915×**, chroma **0.805×**, with the two development offsets **0.278 stops** apart (J83). Red sandstone at noon and brick at noon land in the same place.
* **The clearance walk caught a viewpoint 1.2 m from a wall** and moved 65.8 m onto real surveyed roadbed, scoring the destination on the subject's sightline (J79).
* **The record names the tile mesh and refuses its extent** (J74), which is the only reason this sheet's fault is legible at all.
* **Every structures tile in range has a file** — 4 of 4, 24,504 triangles — one of only two sheets in this queue with complete structures coverage.
* **The kit was fully placed**: 4,489 of 4,489 records in range, nothing capped and nothing suppressed — so the barracks blocks carry their full window count, and it shows.
* **The woodland canopy rule contributes**: **826** of the 2,266 impostor cards are procedural canopy stems, and 26 trees are drawn from modelled branches.
* **Ground clearance is the best in this queue**: over all draws the median is **+0.224 m**, the minimum **−0.699 m** and the under-fraction **0.0826**, after a redrape that moved only 10,394 vertices by at most 0.142 m (J85).
* **Props were not capped**: 2,475 placed of 2,502 in range.

## What does not match

* **The fort is not in the frame**, and the sheet reports a visible fraction of **1.000**.
* **The probe's subject is a 775.6 m by 268.0 m tile mesh**, so the sightline cannot distinguish the fort from any roof on the island.
* **Eighty-six private vehicles are parked on a car-free island.** The rule that would have dropped them exists and is applied to Central Park's drives; it is not applied here.
* **The reference is a photograph of one window** (J93).
* **One of 3 building tiles has no shell file** — the record names it, `t_-7_-1` — and park ground was not built for that same tile, so it renders as bare terrain.
* **A simulated car stands 2.3 m from the lens**, well inside the 8 m of nothing-built the walk enforces against geometry and never applies to the crowd (J91). This is the closest agent in this queue.
* **Seven pedestrians.** The table asked for 142 and 207 were simulated; 93 were dropped for standing in the carriageway while not crossing and 46 for standing where the planimetric data has no sidewalk — which on Governors Island, where the esplanade is the pedestrian surface, is most of the island.
* **Only 26 of 2,292 trees are drawn from modelled branches**; **1,466** species were substituted, **7** instances scaled out of band, 3 cards dropped.
* **The vehicle level-of-detail tally reads 88 while the drawn count reads 86** — a two-vehicle disagreement inside the same record.
* **There is no park ground within 150 m to check** — 0 samples — and only 4 park-ground meshes over 15 surfaces exist for the whole island.
* **Nine props across five kinds were wanted in range and have no asset**: 3 drinking fountain, 2 artwork, 2 swimming pool, 1 memorial, 1 vending machine.
* **Two park-ground surface kinds fall back to the builder's flat colour** — recreation grass and bare ground (J40).
* **The render has no deep shadow**: fifth percentile **0.1332** against the photograph's **0.0084**, because the reference contains a black casemate interior and the render contains none.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| visible fraction 1.000 with no fort in the frame | the probe took the object standing at the subject's coordinate and that object is a tile mesh spanning the island, so all 13 rays land on it — the ray that gets nearest lands on a brownstone wall 6.9 m from the lens (J94 compounded with J92) | **verification — open, and the worst instance in the pass** |
| 86 private cars on a car-free island | the fleet placer has a car-free rule and applies it to Central Park's drives, and Governors Island is not in that list | **data — open, one missing rule, with the rule's own precedent named** |
| the reference is a photograph of one window | the chooser cannot tell a building from a detail of it (J93) | **verification — open, J93** |
| 1 of 3 building tiles without a shell file, and no park ground for it | no shell or park-ground file was built for `t_-7_-1`; the record names both | **data — open, one tile unbuilt** |
| a car 2.3 m from the lens | the 8 m nothing-built rule applies to geometry and not to the crowd (J91) | verification — open |
| 7 pedestrians | 93 dropped in the carriageway and 46 off-sidewalk, because the esplanade is not a sidewalk in the planimetric data | **data — open, measured** |
| 26 of 2,292 trees from modelled branches, 1,466 species substituted | the props budget spends its triangles on cards at this density, and the tree catalogue does not hold most species surveyed here | performance + **data** |
| the LOD tally says 88 and the count says 86 | two counters in the same record disagree by two vehicles | **verification — open, small** |
| p05 0.1332 against 0.0084 | no dark interior in the render's frame | consequence of the reference |
| 9 props across five kinds unmapped | no asset exists for those kinds | data |
| two park surface kinds flat-coloured | the texture catalogue has no photographic set for either (J40) | **declared decision** |
