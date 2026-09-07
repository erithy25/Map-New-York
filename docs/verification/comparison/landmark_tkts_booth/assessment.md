# TKTS booth and red steps, Duffy Square

`landmark_tkts_booth` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Times Square, New York City, 20231003 1232 1916.jpg by Jakub Hałun, CC BY 4.0 (https://creativecommons.org/licenses/by/4.0), taken 2023-10-03 12:32:56, 1920x1281. [Commons page](https://commons.wikimedia.org/wiki/File:Times_Square,_New_York_City,_20231003_1232_1916.jpg)

**Camera** — camera 40.75847, -73.98482 (NYC_TM -2960, 6496) z 15.9 m NAVD88 | azimuth 10.0deg pitch +3.3deg | 35 mm on 36 mm (54.4deg horizontal) | 1280x854. View direction: 10.0 deg as recorded; it agrees with the bearing from the camera position used to TKTS booth and red steps, Duffy Square (10.1 deg) to 0.1 deg. Aim: aimed at TKTS booth and red steps, Duffy Square 60 m away, at its mid-height (a nominal 10 m subject); +3.3 deg from horizontal.

**Sun** — azimuth 175.7°, elevation 45.1° at 2023-10-03T12:32:56-04:00 (EXIF DateTimeOriginal).

**In frame** — 4/4 building tiles (188,464 tris), 3 landmark models, 919 pavement polygons, 333 props, 8,673 facade-kit pieces; 3,114,634 triangles; ground mesh 199² at 2.0 m near / 40.0 m far.

**Camera clearance** — the recorded viewpoint is boxed in: the view azimuth is closed off 12 m ahead, less than the 30 m this frame needs to show its subject; the camera was moved 18 m onto the nearest real crosswalk polygon in data/processed/roads/pavement, keeping the same eye height above the heightmap.  The view azimuth is clear for 60 m from there

**Verdict — the red steps are there as a red wedge and nothing else in Duffy Square is: no booth glass, no signage, no people, and the plaza reads as an empty grey field under a row of black cones**

## What matches

* The red glass steps are present and in the right place — the red band left of centre sits over the booth footprint at the north end of Duffy Square, about 60 m from the lens, matching the photograph's position within the frame.
* The plaza is a continuous paved surface rather than a road: 919 pavement polygons are drawn here (368 curb, 171 crosswalk, 164 roadbed, 105 sidewalk, 62 median, 45 plaza), and the pedestrian plaza does read as one flat surface flush with the roadbed, which is what Broadway between 45th and 47th actually is.
* The bowtie geometry is right. The two building walls converging toward the top-centre of the render follow Seventh Avenue on the left and Broadway on the right, and the gap between them opens northward exactly as it does in the photograph.
* Ground height is right to within the step: the camera stands at 14.32 m NAVD88 read as a point sample from the 2 m heightmap (16 samples in 5 m spanned only 14.33-14.57 m), and Duffy Square's published grade is about 14.5 m, so the plaza is not floating or sunk.
* Street furniture density is plausible for this block — 90 street lamps, 12 LinkNYC kiosks, 10 newsstands, 15 benches, 8 subway entrances — and the cobra-head lamp standards visible in the render are at the right spacing and height.

## What does not match

* The photograph's whole subject is illuminated signage and the render has none. Every facade in the frame is an untextured flat colour block: no LED boards, no Marriott Marquis marquee, no American Eagle wrap, no Coca-Cola or YouTube screens. The `c_times_square` landmark model is placed (182,310 triangles, 290 m away) but it contributes no emissive signage at this distance, so the most recognisable streetscape in the world renders as beige and grey masonry. This single gap accounts for most of the visual distance between the two halves of the sheet.
* The TKTS booth itself is missing. The red steps are drawn but the glass-walled ticket booth under them — the object the sheet is named for — is not in the scene at any LOD, so the wedge reads as a bare red ramp with nothing beneath it.
* The steps are a smooth wedge, not steps. There is no tread-and-riser modulation on the red surface, so it catches light as one flat plane instead of the 27-riser stack of ruby glass in the photograph.
* The row of black cones across the middle of the frame is wrong twice over. They are the 28 tree props, and (a) Duffy Square has no such tree line — the photograph shows an open plaza with cafe umbrellas — and (b) their canopy material renders near-black rather than green, so they read as opaque pyramids blocking the plaza.
* No people. The reference frame contains roughly two hundred, sitting on the steps and filling the plaza, and they are the reason the picture is legible as Times Square; the render is empty. Crowd is not in this stage's scope but it is the second-largest perceptual gap after signage.
* No vehicles. The photograph has a fire truck, two red double-decker buses, taxis and a police van on the Seventh Avenue side; the render's roadbed is bare.
* The camera is 18 m from where the photographer stood and one level lower. The recorded viewpoint was boxed in (view closed off 12 m ahead against the 30 m this frame needs), so the placement rule snapped it onto the nearest crosswalk polygon. The photograph is taken from partway up the red steps looking down over the plaza; the render looks across it from ground level, which is why the render's foreground is a large empty grey apron that has no counterpart on the left.
* The plaza surface carries no markings, no paving pattern, no cafe furniture and no barriers. It is one untextured grey sheet from the bottom edge to the steps, where the photograph has granite paving bands, painted crossings, moveable tables and the pink-and-white bollard line.
* Building massing is too low and too plain on the right. The Marriott Marquis and the 1500 Broadway stack in the photograph rise well past the top of a 35 mm frame; in the render the right-hand wall tops out inside the frame with a flat roof and no setbacks.
* The Father Duffy monument and the flagpole at the plaza's south end — the dark granite cross the photographer is standing beside — is not modelled; the two flagpole props present are elsewhere in the square.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| no illuminated signage anywhere in Times Square | the landmark model for Times Square carries geometry but no emissive sign panels, and the facade kit has no billboard or LED-board category; nothing in the pipeline produces the signage layer | data |
| TKTS booth absent under its own steps | the red steps come from the Times Square landmark mesh; the booth structure is not a separate catalogue entry and is not part of that mesh | data |
| red steps are a smooth wedge | the landmark mesh models the ramp as a single plane at LOD0; the riser detail is below the model's resolution | geometry |
| tree canopies render as black cones | the tree asset's canopy material has near-zero albedo in the props catalogue — the same defect seen on every street-tree sheet in this set | material |
| a tree line where the photograph has open plaza | the props table places 28 trees on the Duffy Square block from a source that does not distinguish planted trees from planter-box seasonal plantings | data |
| no people, no vehicles | the verification scene builds static geometry only; agents and traffic are a runtime layer that this stage does not instantiate | data |
| camera 18 m north of the photographer and one level lower | the recorded viewpoint failed the boxed-in test (12 m of view against a 30 m requirement) so the pavement-snap rule moved it; the rule has no notion of standing on the steps themselves | camera |
| featureless grey plaza surface | pavement polygons are extruded flat and shaded with a single untextured material; no paving texture or road-marking layer exists yet | material |
| right-hand buildings too short and unarticulated | tile shells at LOD0 carry footprint-extrusion heights without setbacks, and no landmark model exists for the Marriott Marquis | geometry |
| Father Duffy monument missing | no catalogue entry; the props table classes it under the unmapped kind `memorial` (1 row in range, not instantiated) | data |
