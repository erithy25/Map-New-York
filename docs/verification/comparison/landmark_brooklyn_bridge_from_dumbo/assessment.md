# Brooklyn Bridge seen from DUMBO / Brooklyn Bridge Park

`landmark_brooklyn_bridge_from_dumbo` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Brooklyn Bridge March 2023 009.jpg by Kidfly182, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2023-03-07 13:20:26, 1920x1440. [Commons page](https://commons.wikimedia.org/wiki/File:Brooklyn_Bridge_March_2023_009.jpg)

**Camera** — camera 40.70400, -73.99200 (NYC_TM -3549, 445) z 3.7 m NAVD88 | azimuth 288.3deg pitch +0.0deg | 35 mm on 36 mm (54.4deg horizontal) | 1208x906. View direction: 288.3 deg as recorded; it agrees with the bearing from the camera position used to Brooklyn Bridge Brooklyn tower (288.2 deg) to 0.1 deg. Aim: level optical axis (the subject is 285 m away; anything that far is photographed with a level camera).

**Sun** — azimuth 204.6°, elevation 41.1° at 2023-03-07T13:20:26-05:00 (EXIF DateTimeOriginal).

**In frame** — 9/9 building tiles (189,682 tris), 3 landmark models, 2,536 pavement polygons, 471 props, 2,193 facade-kit pieces; 2,091,195 triangles; ground mesh 217² at 2.0 m near / 40.0 m far.

**Verdict — the best bridge model in the set: the Brooklyn tower's twin Gothic arches, the main cables, the suspenders and the deck truss are all there in the right proportions — but it is bare grey where the real tower is coursed granite, and the park it stands in is a blank plane**

## Re-rendered 2026-09-07

A winter frame, correctly: the reference photograph's own date puts `leaf_off` on, so all 282 trees
in this scene carry the kit's bare-canopy variants and the long low shadows they cast across the
plaza are the right shape for the season. The Brooklyn Bridge crosses the middle distance with its
suspension cables and deck reading clearly, the DUMBO block faces sit under it, three landmark models
are placed, and 89 vehicles and 427 people are in the scene.

**Two things work against the subject.** The item names the Brooklyn tower at 285.9 m, and the near
field is a stand of bare trunks — the closest of them a couple of metres from the lens — which screen
a good part of the left of the frame where that tower stands. In leaf-on season they would hide it
entirely. And the foreground is roughly the lower third of the image as untextured pale ground: this
is Brooklyn Bridge Park, whose promenade decks and paving are the structures deviation B13 records as
absent, so what should be timber decking, granite setts and planting beds is one flat surface.

Mean luminance **0.483 against the photograph's 0.390** — brighter, like Barclays and Bethesda, and
another instance of I16 running in the opposite direction from the Manhattan canyons.

## What matches

* The Brooklyn tower is recognisably itself: two pointed Gothic arches, the correct pier proportions, the saddle at the top and the main cables running down to the deck on both sides.
* The suspension system is modelled, not implied: main cables, vertical suspenders and the diagonal stays are present at roughly the right spacing.
* The deck truss with its lattice web and the roadway below it is at the right height above the water and the right depth.
* The origin rule chose correctly and says why: this photograph's own EXIF GPS is only 23 m away but the eye point there is inside a building shell, while the item's recorded viewpoint is in open air, so the recorded one was used.
* The heading agrees to 0.1 deg with the bearing from the camera to the tower 286 m away, and the Manhattan skyline behind the bridge is at the right scale and in the right order.
* 2,536 pavement polygons and 471 props are placed, and the water surface reaches the right waterline.

## What does not match

* The tower has no masonry. It is a single pale grey surface where the real tower is coursed limestone and granite with deep joints, a rough face and strong tonal variation — the entire subject of the reference photograph.
* The framing is much wider than the reference. The photograph is taken from directly under the bridge looking up the tower with a long lens; the render's level 35 mm axis puts the tower a third of the way up the frame with half of Brooklyn Bridge Park in shot. That is the level-axis rule working as designed but it means the two frames are not of the same thing.
* Brooklyn Bridge Park is a blank grey plane: no Pebble Beach shingle, no railings, no benches, no planting, no Jane's Carousel, no paths.
* ~~No people anywhere, on a waterfront that is never empty.~~ — **superseded 2026-09-07.** **427 people and 89 vehicles are in this scene** from one frame of the running simulation; what the reference still has and the render does not is recorded in the section above.
* The bridge carries no traffic and no pedestrians on the promenade.
* The buildings across the river are flat pastel solids with no glass.
* The foreground is a large untextured plane with visible triangulation from the graded terrain grid.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| no masonry on the tower | the b_brooklyn_bridge model carries geometry but a flat base colour; there is no stone texture | material |
| framing much wider than the reference | a level optical axis at 35 mm is required to compare proportion; the reference is a tilted long lens from beneath | camera |
| the park is a blank plane | park surfacing, planting, railings and structures are in no dataset the scene reads | geometry |
| ~~no people or traffic~~ superseded | agents are placed now (427 people, 89 vehicles); what remains is framing and occlusion, not absence | reporting |
| flat buildings across the river | shells carry a per-material base colour with no glass | material |
| untextured, faceted foreground | the terrain material is a flat colour and the graded grid is 2 m here | material |
