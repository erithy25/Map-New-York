# Bronx drive-through: Arthur Avenue (Belmont)

`drive_bronx_arthur_ave` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Arthur Avenue 09 - M&G Restaurant.jpg by Joe Mabel, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2026, 1920x1440. [Commons page](https://commons.wikimedia.org/wiki/File:Arthur_Avenue_09_-_M%26G_Restaurant.jpg)

**Camera** — camera 40.85325, -73.88915 (NYC_TM 5131, 17020) z 26.6 m NAVD88 | azimuth 190.0deg pitch +0.0deg | 35 mm on 36 mm (54.4deg horizontal) | 1280x854. View direction: 190.0 deg as recorded in meta.json. This item names no subject and the reference photograph's own view direction was not derived from the image (confidence: medium), so the two halves of this sheet are not guaranteed to face the same way — compare them on street width, storey height and material, not on composition. Aim: level optical axis (the reference names no subject to aim at).

**Sun** — azimuth 95.5°, elevation 43.6° at 2026-06-21T09:30:00-04:00 (photograph year only; 21 June 09:30 assumed).

**In frame** — 4/4 building tiles (261,870 tris), 0 landmark models, 2,363 pavement polygons, 393 props, 6,622 facade-kit pieces, 88,200 terrain triangles; **4,475,972 triangles** in 262.6 s. Frame mean 0.2679, sd 0.1878. Props capped by the triangle budget at 393 of the 880 in range.

**Verdict — the strongest street-level frame in the set on everything the street is made of, and the clearest statement of what is still missing from it. Block-face height, storey rhythm, awning band, fire escapes, the kerb reveal and a June canopy are all right. The ground floor is a coloured strip where the photograph has a shopfront, the roadway is an untextured plane, and both kerbs are bare where the real avenue is parked solid**

## What this render is, and what changed under it

Re-rendered 2026-09-08 against the same reference. Three things in the world moved since the last
pass and all three are visible in the numbers rather than in the picture:

* **The surveyed curb ramps are cut into the pavement now.** They are not visible in this frame,
  and that is correct: a ramp is a corner detail and this camera looks down the middle of a block.
  The kerb reveal that *is* visible along the near sidewalk is the 0.15 m the pavement stage draws.
  The render record still lists `curb_ramp: 81` under `unmapped_kinds` because this sheet was
  rendered minutes before the resolver learned to say `built_elsewhere` — those 81 rows are built,
  as pavement, and the count is a stale label rather than a gap.
* **The triangle count rose from 3.56 M to 4.48 M** on the same camera, most of it the ramp
  geometry in the pavement and 38 more props inside the budget (393 against 355).
* **Every vehicle in this frame is at LOD2**, which until this morning meant every one of them
  carried an untextured 2 m sphere at its rear axle — Blender's glTF importer builds one per rigged
  file as a bone display shape and `import_glb` returned it with the car (J44). This is the first
  Arthur Avenue frame without them.

## What matches

* The street trees are right: full June canopies, visible trunk and branch structure, correct 8–12 m
  heights, planted at the kerb where the street-tree census puts them. **200 of the 393 props in
  this frame are trees**, and the budget is reached on trees before it reaches the smaller furniture.
* The block face is right in kind and scale for Arthur Avenue: two- and three-storey brick and stucco
  buildings with flat roofs and parapets, a continuous ground-floor commercial band, and the Arthur
  Avenue Retail Market's shed running along the left.
* The kit that makes the frame read as the Bronx is placed and countable: **147 fire escapes**, 883
  storefront pieces, 3,904 windows, 686 window accessories, 171 parapets, 110 cornices, 109 string
  courses, 114 quoins and 21 scaffold pieces. The green-netted sidewalk sheds on both frontages are
  those 21.
* The street section is right: a wide roadbed, generous sidewalks both sides, a visible kerb reveal,
  and 2,363 pavement polygons — 958 curb, 541 crosswalk, 395 roadbed, 235 sidewalk, 132 parking-lot,
  76 median, 26 plaza — from the DoITT planimetrics.
* A fire hydrant stands at the kerb at the right size and colour, at the position `props.parquet`
  records. 26 hydrants, 61 street lamps, 54 manholes, 48 rooftop cooling towers and 2 Citi Bike
  docks are in frame.
* The traffic is the simulation's own: 89 vehicles within 320 m and 281 people within 200 m, seed
  20260907, after 120 s of simulated time on the shipped road graph — 49 sedans, 18 SUVs, 5 taxis,
  5 black cars, 4 MTA buses, 3 box trucks, 3 vans, 2 boro taxis. A white box truck, a green sedan
  and a dark sedan are visible down the avenue with people on both sidewalks.

## What does not match

* **The frames are at different scales.** The item looks south down Arthur Avenue from the roadway
  centre; the photograph is a frontage at four metres. They agree on what the street is made of and
  cannot be compared on composition. The item names no subject, so no bearing can be derived from it
  (I7).
* **The Sun is a guess.** The file records only the year 2026, so the fallback puts it at 21 June
  09:30, azimuth 95.5° — an east-facing morning light on a street the photograph shows in flat
  shade. Frame mean 0.2679 against a photograph of a sunlit red frontage.
* **Both kerbs are bare.** Arthur Avenue in the photograph's own background is parked solid on both
  sides; the simulation models moving traffic and there is no parked-vehicle layer, so the one thing
  that fills a Bronx kerb is the one thing not in the frame.
* **Few of the placed agents are visible, and the caption's numbers are disc counts.** 89 vehicles
  and 281 people are placed; a 54.4° wedge at 200 m is 206 m wide and most of that width is inside
  the blocks rather than on the street, so a handful reach the picture. Nothing is wrong with the
  placement — 270 people and 109 vehicles are dropped for being outside the radius, 50 more for
  standing in the carriageway without crossing, 22 for not being on a walkable surface, 4 vehicles
  for being a body with no rider — but a reader should not take a disc count for a frame count.
* No market stalls, no shop signs, no menu boards — the things that make Arthur Avenue what it is.
  The awning band *is* there with `RESTAURANT` lettering, which is the one shopfront element the
  facade kit supplies.
* The ground-floor commercial band is a flat coloured strip: no glass, no shopfront lettering beyond
  the awning, no rolling shutters, no produce boxes on the sidewalk.
* The roadway is an untextured plane. The pavement carries a kind and a few markings and no surface
  texture, so the bottom 45 % of the frame is flat grey with the shadows of things above it.
* No landmark models are in range, which is correct here but means the frame rests entirely on
  shells and kit.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the two halves are of different subjects | the item names no subject, so the reference stage assigned it the item's own azimuth and the photograph is a shopfront at four metres | reference |
| the Sun is a guess | the photograph's metadata carries a year and no date, so the stage falls back to 21 June 09:30 | reference |
| no parked cars | the traffic simulation models moving vehicles only; there is no parked-vehicle layer | data |
| few placed agents visible | 89 vehicles and 281 people are a disc count; the block faces occlude nearly all of them | reporting |
| no shopfronts, signs or produce | the facade kit supplies openings without glazing or lettering, and no stage produces shop signage | material |
| untextured roadway | the pavement material is a flat colour per kind with no texture (J40's problem, on asphalt) | material |
| `curb_ramp: 81` shown as unmapped | this sheet predates the resolver saying `built_elsewhere`; the ramps are in the pavement | reporting |
