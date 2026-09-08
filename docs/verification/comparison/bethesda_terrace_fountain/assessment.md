# Bethesda Terrace and Fountain

`bethesda_terrace_fountain` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** - File:Bethesda Fountain and the Lake, Central Park, Manhattan, New York.jpg by Christian David, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2026-04-18 08:04:45, 1920x1280. [Commons page](https://commons.wikimedia.org/wiki/File:Bethesda_Fountain_and_the_Lake,_Central_Park,_Manhattan,_New_York.jpg)

**Camera** - camera 40.77350, -73.97110 (NYC_TM -1778, 8174) z 24.2 m NAVD88, being the 22.622 m heightmap surface plus a 1.6 m standing eye | azimuth 14.2deg pitch -2.5deg | 28 mm on 36 mm (65.5deg horizontal) | 1280x854. It is aimed there because the recorded 14.2 deg agrees with the bearing from this position to the Angel of the Waters to 0.0 deg, the pitch is set on the angel at the model's 8 m mid-height, and the lens widened to 28 mm because "the terrace, fountain and the Lake behind it need a wide frame from the upper level". The camera stands at the item's recorded viewpoint, not the photograph's EXIF GPS 43 m away whose eye point sits under 1.8 m of paving, and was walked 12 m along the azimuth to the parapet.

**Sun** - azimuth 92.9deg, elevation 20.3deg at 2026-04-18T08:04:45-04:00, taken from the photograph's own EXIF DateTimeOriginal rather than assumed.

**In frame** - 4/4 building tiles (231,192 tris), 7 landmark models, 969 pavement polygons (438 curb, 185 crosswalk, 154 roadbed, 124 sidewalk, 60 median, 5 parking_lot, 3 plaza), 165 props of the 195 rows in range, 0 kit pieces, 0 vehicles and 10 people; 1,155,050 triangles total, the ground mesh 84,356 of them across a 209² grid at 2.0 m near and 40.0 m far, 0 holes, 3,737 quads on the flattened water surface. Nothing was capped by a budget: no tile dropped or LOD-substituted, no landmark skipped, no pavement polygon dropped. The 30 props not placed are unmapped kinds - 10 artwork, 7 drinking fountains, 5 memorials, 5 parks buildings, 3 comfort stations.

**Verdict - the aim, the height and the subject model are all right and the frame is still wrong: the terrace's own balustrade crosses the sightline and leaves a thumbnail of verdigris bronze where the fountain should be, so this sheet cannot yet be read as evidence about Bethesda Terrace, and J45's fix to the clearance walk is what would make it one.**

## What matches

* The camera stands on the right structure at the right height: the eye is on the roof of `lm_b_bethesda_terrace.26` at 24.2 m NAVD88 on the recorded 14.2 deg heading. The aim is not what is broken here.
* **The subject is in the picture, and J45 predicted exactly how much of it.** A pale verdigris shape stands clear above the coping rail near the centre of the frame - a narrow upright with a single arm out to the right. J45 measured that about 1.4 deg of the angel, some 26 px of an 854 px frame, would clear the balustrade line, and that is what the render shows: the measurement and the picture agree.
* The balustrade itself is the right object: square balusters with rectangular gaps under a continuous coping, running away from the lens across the whole width, the same lake-edge balustrade that stands behind the fountain in the photograph.
* Bow Bridge is unmistakable at the left: a shallow teal arch with a lattice railing, in the verdigris the real ironwork carries, with a lamp standard at its near abutment. Two park landmarks sitting correctly relative to each other, seen from a third, is a real check on placement and it passes.
* Belvedere Castle reads on its ridge at the centre of the frame, tower, turret and crenellation legible at that distance.
* Museum-scale masses close both edges: at the left a long beige block with a regular window grid over an arcaded ground storey, at the right a plain flat-topped mass in front of grey apartment blocks.
* The Sun is placed from the photograph's own instant rather than assumed, and the scene is complete rather than trimmed: 4 of 4 building tiles, 7 of 7 landmarks, 969 of 969 pavement polygons.

## What does not match

* **The fountain, the basin, the four cherubs, the water and the whole lower plaza are hidden.** The photograph is a fountain filling the centre of the frame, a granite rim people sit on, red brick radiating away from it; the render has a rail and, above it, bare ground. J45 measured why: the balustrade tops out at 24.05 m against a lens at 24.222 m and its far end crosses the sightline at -0.2 deg, so the basin, pedestal and cherubs, spanning -5.9 to -1.8 deg, all sit below the rail line. The model is not at fault - `b_bethesda_terrace.glb` carries the plaza, basin, stem, cherubs and angel in 10,808 triangles.
* **There is no canopy, and the frame shows it plainly:** the photograph's horizon is unbroken foliage with no building of any kind in it, while the render shows two museums, a castle and a skyline over the rail. 43 trees are placed within 300 m and not one is in this 66 deg frame at any radius; D10 records that the citywide tree ingest changed 0.003 % of this frame's pixels.
* The Lake cannot be picked out of the picture. The caption counts 3,737 quads on the flattened water surface and B16 records that the balustrade hides all but 455 pixels of it; nothing in the frame reads as water, where a band of green Lake water crosses the middle of the photograph behind the fountain.
* No people can be identified anywhere in the frame. 10 were placed, 2 at LOD1 and 8 at LOD2, against roughly eighty in the photograph (I13a).
* No vehicles, where the reference has a green Parks utility cart on the plaza. 113 agents were dropped, 47 of them vehicles the road graph put on Central Park's East, West, Terrace or Center Drive, which have carried no private traffic since 2018 (C8).
* The ground is a single pale grey with visible triangulation facets from the graded grid, where the photograph has red brick laid in radial bands with granite kerbs and stair treads cutting across it.
* **The render is far too bright.** Frame mean luminance is 0.7188, standard deviation 0.1648; I16 records this scene as 0.331 brighter than its photograph, the largest positive gap in the re-rendered set, and it shows - the render is high-key and almost shadowless where the photograph is mid-toned with deep shade under the trees.
* What is visible of the angel reads as a blocked-out shape, not a figure - I1's general case arriving at the one landmark whose whole point is a bronze figure.
* Three faults on the sheet's own caption strip. "7 landmarks" under **In frame** counts landmarks placed in the scene: The Dakota is one of the seven and stands on Central Park West, outside a 65.5 deg frame aimed at 14.2 deg. The subject is "27 m from the camera" on the caption's Subject line and "69 m away" on its Aim line five lines below. And the pavement breakdown lists six kinds summing to 966 of the 969 it reports, dropping the 3 plaza polygons.
* Neither of today's two changes can be seen here. 438 curb polygons are in range but no kerb is in the picture, so the surveyed ramps now cut into the pavement mesh (J21, J43) show nothing; and with 0 vehicles placed, the removal of the untextured 2 m sphere at each rigged vehicle's rear axle (J44) has nothing to remove.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| fountain, basin, cherubs and lower plaza hidden | the clearance walk stops at the first gap in the deck, 12 m out, not at the parapet 50 m on that the photographs are taken from; the near balustrade then crosses the sightline at -0.2 deg (J45) | verification |
| the angel reads as a block, not a figure | sculpture is modelled as blocked-out mass throughout (I1) | geometry |
| no trees, and a skyline visible that the photograph does not have | Central Park's canopy is not in any dataset the scene reads; OSM covers where a mapper walked and this sight line crosses none of it (D10) | data |
| the Lake invisible | the water is built and the balustrade occludes it; 455 px survive (B16) | verification |
| no people | the walkable network is offset from road centrelines, so a park terrace has no sidewalk to stand on (I13a) | data |
| no vehicles | CSCL still carries the car-free park drives as ordinary roadway, so the placement lane refuses what the simulation puts there (C8) | data |
| flat grey untextured ground | parks have no ground surface class; lawn, plaza and forest floor are one terrain colour (D10) | material |
| frame 0.331 brighter than the photograph | the render is physically lit at a fixed exposure, the photograph metered (I16) | verification |
| photograph's own vantage unusable | its EXIF GPS eye point sits under 1.8 m of paving, so the render falls back to the recorded viewpoint 43 m away | reference |
| "7 landmarks", "27 m"/"69 m", 966 of 969 | the caption reports scene counts and two subject distances as though they were frame facts | reporting |
| today's curb-ramp and J44 fixes invisible | no kerb and no vehicle is in this frame | verification |
