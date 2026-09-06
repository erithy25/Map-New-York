# Top of the Rock looking south (Empire State Building centred)

`top_of_the_rock_south` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:View-from-Empire-State-Building.jpg by Sebring12Hrs, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2018-10-25 13:05:58, 1920x1440. [Commons page](https://commons.wikimedia.org/wiki/File:View-from-Empire-State-Building.jpg)

**Camera** — camera 40.75930, -73.97890 (NYC_TM -2440, 6586) z 280.9 m NAVD88 | azimuth 205.2deg pitch +0.0deg | 24 mm on 36 mm (73.7deg horizontal) | 1208x906. View direction: 205.2 deg as recorded; it agrees with the bearing from the camera position used to Empire State Building (205.4 deg) to 0.2 deg. Aim: level optical axis (the subject is 1334 m away; anything that far is photographed with a level camera).

**Sun** — azimuth 187.9°, elevation 36.7° at 2018-10-25T13:05:58-04:00 (EXIF DateTimeOriginal).

**In frame** — 65/83 building tiles (1,168,378 tris), 46 landmark models, 3,371 pavement polygons, 0 props, 0 facade-kit pieces; 3,591,476 triangles; ground mesh 381² at 2.0 m near / 40.0 m far.

**Verdict — now a real comparison and a good one: the Empire State Building is centred where the photograph puts it, the Midtown carpet below has the right grain and the right relative heights, and 46 landmark models sit in the right places. What is missing is every surface — glass, stone, roof plant, the deck the photographer is standing on — and the far half of the view**

## What matches

* The Empire State Building is centred, at the right apparent size for 1,334 m, with its stepped setbacks, mooring mast and antenna all present and correctly proportioned. It is the single strongest match in the whole comparison set.
* The heading is right (205.2 deg recorded, 205.4 deg to the subject) and the 24 mm lens gives the same 73.7 deg span as the reference frame.
* The eye height is right and published: 259.1 m deck level from the 30 Rockefeller Plaza catalogue entry (CTBUH 850 ft) plus 1.6 m, over a 20.3 m plaza.
* The carpet of Midtown between the camera and the Empire State Building has the right grain: block sizes, street rhythm, the rise of the mid-block towers and the drop into the side streets all read like the photograph.
* Relative heights are right across the frame. The Billionaires' Row slab on the left rises well above everything near it, the Rockefeller Center block on the right cuts the frame at the correct height, and the low-rise between them sits at the right level.
* 46 landmark models are in the frame, including 30 Rockefeller Plaza, St Patrick's, MoMA, Lever House, the Seagram Building, Carnegie Hall and the MetLife Building. Their shells are suppressed so nothing is drawn twice: 72 BINs and 6,248 faces removed in this scene.
* 65 of the 83 tiles import, 28 of them by falling back from LOD2 to LOD1 — before that fallback only 37 came in and half the skyline was missing.

## What does not match

* There is no observation deck. The camera stands in mid-air above the 30 Rockefeller Plaza model, which stops at the roof slab: no deck floor, no glass screens, no parapet, no radio masts. The photograph's foreground furniture has no counterpart, and nothing supports the camera.
* No building has any surface. Every tower is a flat pastel solid; the two towers with visible fenestration owe it to the landmark models, not to the shells. There is no glass, no reflection, no spandrel banding, no stone.
* No roof carries plant. The reference is full of cooling towers, water tanks, bulkheads, skylights and terraces on every roof in the middle distance; the render's roofs are blank slabs. props.parquet has 120 cooling towers in a comparable Midtown frame and none of them has an exported asset.
* The far half of the view is gone. The Hudson, the harbour, Lower Manhattan and the New Jersey bank — all present in the reference — wash out into haze because 18 of the 83 tiles have no shell and the rest are LOD1 boxes.
* The colour palette is wrong in a specific way: too much pale blue and salmon, too little grey and black. Midtown from above is mostly dark glass, grey stone and black tar roofs; the render's per-material base colours read as a pastel massing model.
* No people, no vehicles on the avenues, no water towers, no antennae, no flags.
* Props and facade kit are switched off for this scene (eye height above 20 m), which is the right call at 260 m but means the streets below are geometrically bare.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| no observation deck, screens or masts | no stage models the deck; the landmark model ends at the roof slab | geometry |
| flat pastel towers, no glass | shells carry a per-material base colour with no facade texture and no glass BSDF | material |
| blank roofs | roof plant exists in props.parquet as kinds (cooling_tower, misc_structure) with no exported asset | data |
| the far half of the view is empty | 18 tiles have no tile_buildings.glb (water, parkland and New Jersey) and the rest are LOD1 | data |
| pastel palette | the per-material base colours are lighter and more saturated than the real Midtown mix | material |
| no people or vehicles | no crowd or traffic placement feeds the verification scene | data |
