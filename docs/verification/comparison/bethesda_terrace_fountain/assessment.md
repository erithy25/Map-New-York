# Bethesda Terrace and Fountain

`bethesda_terrace_fountain` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Bethesda Fountain and the Lake, Central Park, Manhattan, New York.jpg by Christian David, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2026-04-18 08:04:45, 1920x1280. [Commons page](https://commons.wikimedia.org/wiki/File:Bethesda_Fountain_and_the_Lake,_Central_Park,_Manhattan,_New_York.jpg)

**Camera** — 40.77350, -73.97110 (NYC_TM −1778, 8174) at z 24.2 m NAVD88, the 22.622 m heightmap surface plus a 1.6 m standing eye | azimuth 13.9°, pitch −1.9° | 28 mm on 36 mm (65.5° horizontal) | 1280x854. The azimuth is the item's recorded 13.9°, which agrees with the bearing from this position to the Angel of the Waters to **0.0°**. The camera stands at the item's recorded viewpoint rather than the photograph's own EXIF GPS 42.7 m away, because the eye point there is under `verify_pavement` — 1.8 m of paving directly overhead — and was then walked 12 m along the azimuth to the parapet.

**Sun** — azimuth 92.9°, elevation 20.3° at 2026-04-18T08:04:45−04:00, taken from the photograph's own EXIF DateTimeOriginal rather than assumed.

**Subject** — Bethesda Fountain (Angel of the Waters). **81.4 m** from the placed camera; 93.4 m from the origin the aim was decided at; the 51.4 m that this sheet printed until J59 was the distance from the *photograph's* GPS, a position this render had already rejected.

**In frame** — 4/4 building tiles (231,192 tris), 8 landmark models, 7,004 pavement polygons (**5,686 white marking, 164 yellow marking**, 522 curb, 229 crosswalk, 181 roadbed, 143 sidewalk, 68 median, 7 parking lot, 4 plaza), 224 props of the 258 rows in range, 0 kit pieces, 0 vehicles and 11 people; 1,685,121 triangles, the ground mesh 86,028 of them at 2.0 m near and 40.0 m far, 0 holes. Nothing was capped: no tile dropped or LOD-substituted, no landmark skipped, no pavement polygon dropped. The 34 props not placed are unmapped kinds — 11 artworks, 9 drinking fountains, 6 parks buildings, 5 memorials, 3 comfort stations.

**Verdict — the aim is exact, the subject is in the scene and the probe finds it, and the sheet is still not a like-for-like comparison: the camera stands on the upper terrace and every one of the four reference photographs was taken from the lower plaza, so the terrace's own balustrade crosses the sightline and leaves about twenty pixels of verdigris bronze where the photograph has a fountain filling the frame.**

## What matches

* **The aim is exact and it is measured, not asserted.** The recorded 13.9° agrees with the bearing to the Angel of the Waters to 0.0°, and the camera stands on the roof of `lm_b_bethesda_terrace.26` at the height the heightmap gives that deck.
* **The subject is there and the probe finds it.** `subject_sightline` lands a ray on `lm_b_bethesda_terrace.1` at **80.8 m**, 0.6 m short of the subject coordinate, and the render shows it: a small verdigris upright at frame centre, just clear of the coping. Until J57 this same probe reported the fountain *visible* with 5 rays of 5 over a frame that shows almost none of it, and until J55 nothing asked the question at all.
* **Road markings reach a comparison frame for the first time.** A band of grey asphalt crosses the lower third of the picture with a **continuous yellow marking** running its full width — 164 yellow and 5,686 white marking polygons are in range, all derived from measured lane geometry rather than painted by eye (J52). Which line it is cannot be read from this angle: the band is seen almost edge-on from 24 m above it and only one stripe is visible, so this says the paint is there and drawn, not that it is a centre line rather than a lane line.
* **The lamp beside the camera is the right fixture.** The nearest built thing in the frame is `prop_lamp_park_twin_6` at 3.3 m — a cast-iron post-top park lamp. It was a DOT cobra-head davit on a 12 ft davit arm until J56, standing on the terrace of an Olmsted landscape, and it was that pole that blocked this sheet's sightline probe.
* The balustrade is the right object: square balusters with rectangular gaps under a continuous coping in red sandstone, running the full width, which is the lake-side balustrade the photograph shows behind the fountain.
* Belvedere Castle reads on its ridge at the centre, tower and turret legible at that distance, and museum-scale masses close both edges.
* The Sun is placed from the photograph's own instant, and the scene is complete rather than trimmed: 4 of 4 tiles, 8 of 8 landmarks, 7,004 of 7,004 pavement polygons, 0 holes in the ground.

## What does not match

* **The fountain, the basin, the four cherubs, the water and the whole lower plaza are hidden, and the record now says exactly what hides them.** Of five rays cast across a 12 m fan at the subject, **three are stopped by `lm_b_bethesda_terrace.20` at 14.7 m** — the terrace's own lower balustrade — one flies past into nothing, and **one reaches the fountain**. `subject_visible` is false on that majority, and the counts beside it are what make "false" mean *mostly hidden* rather than *absent*.
* **The viewpoint and the photographs are not the same place, and that is the root of the frame.** The item's viewpoint is on the upper terrace, 93.4 m from the fountain. The four reference photographs' own EXIF GPS, taken from `meta.json` and measured against OSM way 958635828 (the fountain footprint the landmark model was built on), puts their cameras **50.5, 51.4, 63.5 and 75.5 m** from it — on the lower plaza and the stairs. No amount of correcting the aim closes a difference in where the photographer stood.
* **No canopy.** The photograph's horizon is unbroken foliage with no building in it; the render shows two museum masses, a castle and a skyline over the rail. 76 trees are placed within 342 m and not one is in this 65.5° frame (D10).
* The Lake cannot be picked out. The terrain carries THE LAKE, Turtle Pond and the Boat Basin as water bodies and the balustrade hides the surface; nothing in the frame reads as water where the photograph has a band of green across the middle.
* No people can be identified. 11 were placed, 3 at LOD1 and 8 at LOD2, against roughly eighty in the photograph.
* No vehicles, where the reference has a green Parks utility cart on the plaza. **46 vehicles were dropped for being on Central Park's East, West, Terrace or Center Drive**, which have carried no private traffic since 2018 (C8).
* The ground is a single pale grey with visible triangulation facets, where the photograph has red brick in radial bands with granite kerbs and stair treads (J40 — the open-space surfaces are honest measured colours, not textures).
* **The render is too bright.** Frame mean luminance 0.7228, sd 0.1663: high-key and almost shadowless where the photograph is mid-toned with deep shade under the trees.
* What is visible of the angel is a blocked-out shape, not a figure — the general case at the one landmark whose whole point is a bronze figure.
* One fault remains on the caption strip: **"8 landmarks" counts landmarks placed in the scene, not landmarks inside the frame.** The Dakota and Billionaires' Row are among the eight and stand behind or beside a 65.5° frame aimed at 13.9°.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| fountain, basin, cherubs and lower plaza hidden | the camera is on the upper terrace and the photographs are on the lower plaza; the terrace's own balustrade then crosses the sightline, stopping 3 of 5 rays at 14.7 m | reference |
| the angel reads as a block, not a figure | sculpture is modelled as blocked-out mass throughout (I1) | geometry |
| no trees, and a skyline the photograph does not have | Central Park's canopy is in no dataset this scene reads (D10) | data |
| the Lake invisible | the water is built and the balustrade occludes it | verification |
| no people | the walkable network is offset from road centrelines, so a park terrace has no sidewalk to stand on (I13a) | data |
| no vehicles | CSCL carries the car-free park drives as ordinary roadway, so 46 placements were refused (C8) | data |
| flat grey untextured ground | parks have no ground surface class; lawn, plaza and forest floor are one terrain colour (J40) | material |
| frame 0.72 mean against a mid-toned photograph | the render is physically lit at a fixed exposure, the photograph metered (I16) | verification |
| the photograph's own vantage unusable | its EXIF GPS eye point sits under 1.8 m of paving, so the render falls back to the recorded viewpoint 42.7 m away | data |
| "8 landmarks" on the caption | the caption reports a scene count as though it were a frame fact | reporting |
