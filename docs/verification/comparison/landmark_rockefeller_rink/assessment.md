# Rockefeller Center Lower Plaza and rink (Prometheus)

`landmark_rockefeller_rink` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Renovating Rockefeller rink 2021 jeh.jpg by Jim.henderson, CC BY 4.0 (https://creativecommons.org/licenses/by/4.0), taken 2021-04-30 11:25:53, 1920x1080. [Commons page](https://commons.wikimedia.org/wiki/File:Renovating_Rockefeller_rink_2021_jeh.jpg) — the photograph's own view direction is derived from the image at **high** confidence. **Its filename says what state it caught**: the rink under renovation. Prometheus stands gilded against the Channel Gardens wall; the rink floor itself is a building site of plywood, scaffold frames, sheeting and stacked debris, and *THE CONCOURSE ROCKEFELLER CENTER* is cut into the wall behind. A railing crosses the foreground because the photographer is on the promenade looking **down** into the plaza.

**Camera** — 40.7586, -73.9782 (NYC_TM -2381, 6508) at z 21.2 m NAVD88 | azimuth 290.8°, pitch −1.2° | 35 mm on 36 mm (54.4° horizontal, landscape) | 1280x720. The camera stands on **this photograph's own EXIF GPS**, **40.9 m** from the item's recorded viewpoint; the item's recorded azimuth is 260.0°, **30.8° away**. The lens was **not widened** — the highest built thing at the subject's coordinate stands **−7.0 m** relative to the ground there, under the 2 m at which the probe will frame — and the pitch was set from the subject's **own ground**, the record's words being *nothing stands at its coordinate, so it is a surface, looked down into as the photograph does*. The walk did not move it: the view azimuth is clear for **57.1 m** against a **20.3 m** requirement, the nearest built thing in the frame is `lm_30_rockefeller_plaza.2` **22.7 m** away, no agent within 60 m. The ground under it reads 19.603 m NAVD88 from the 2 m heightmap, 16 samples within 5 m, range 18.75 to 19.76 m.

**Sun** — azimuth 137.4°, elevation 58.0° at 2021-04-30T11:25:53−04:00, from the photograph's own **EXIF DateTimeOriginal**; 913.6 W/m² direct normal, sky at strength 0.0312, Filmic, **+4.20 stops** metered and unclamped against a linear median of **0.009827** and a target of **0.18**. The record declares the consequence: **under-lit** — *the scene needed +4.20 stops to read as a picture, more than the 4 a photographer recovers hand-held; the frame is published and this is the number to read it by*. The physical rule would have given **0.0 stops**. A courtyard between two towers at 58° is a shaft of shade.

**In the scene** — 4,500,190 triangles: 4 building tiles (206,734 tris, 0 missing, 0 LOD-substituted), 8 landmark models of which 2 can fall inside the 54.4° frame, 21,045 pavement polygons, 927 props, 3,955 kit pieces, 14 park-ground meshes over 163 surfaces, **96 triangles of structures**, 88 vehicles and 430 people.

## Verdict — the sunken plaza is modelled seven metres down and the ground is laid flat over the top of it

**The excavation exists.** The probe reports the highest built thing at the subject's coordinate at z **13.41 m** against a ground of **20.37 m** — **6.96 m below it**. So the Lower Plaza's floor is in the model, at the right depth, and the record knew what to do with it: no lens widening, no tilt toward a height, and the pitch aimed at the subject's own **surface** rather than at a mid-height. Two sheets in the pass have a subject whose fabric lies below its own ground, and both are correct about it (J96).

**And the ground covers it.** `terrain.quads_cut_for_landmark_ground` reads **401** — the terrain was opened for the landmark's own ground plate — and that plate is a **single flat surface at the surrounding grade**, so the 6.96 m well it should be opening is filled in. The published render is the result: a continuous tan ground surface across the whole lower half of the frame, where the photograph has a railing, a drop, and a plaza floor seven metres down. **`parkground.faces_cut_for_landmark_ground` is 0**, so nothing else cut it either. The Lower Plaza is two levels and the ground plate is one.

**What the render gets right is the flags, and it gets them properly right.** The row of poles along the plaza's edge is there — **86 flagpoles** placed — and they carry flags rather than bare poles, on the split J58 built from the OSM `subtype` tag. In the photograph the same row flies above the construction hoarding. On a sheet with this much wrong, that row is the one thing a New Yorker would recognise instantly.

**And the colour ratio inverts, for an honest reason.** Chroma **0.0793** against the photograph's **0.0423** — the render carries **1.875×** the reference's colour. That is not the render being garish: the photograph is a grey building site under grey sheeting, and the render is a row of coloured flags over tan stone. Two states of one place, and the flags are the difference.

## Measured for this assessment

| figure | how |
|---|---|
| the plaza floor sits 6.96 m below its own ground | the record's own `highest_built_z_m` of 13.41 m against its `ground_z_m` of 20.37 m, both quoted above |
| only two sheets in the pass have a subject whose fabric lies below its own ground | compared those two fields across every record carrying `scene.structures`: this sheet and the Queens-Midtown tunnel portal, at 4.83 m below |

## What matches

* **The plaza floor's depth is modelled** — 13.41 m against a surrounding ground of 20.37 m, and the framing rule handled a sunken subject correctly (J96).
* **The flag row.** 86 flagpoles with flags, which is the plaza's own signature and is placed from the dataset rather than by rule.
* **The wall behind is right in kind** — a regular grid of windows on limestone, which is what the Channel Gardens elevation is.
* **The aim** — the camera stands on the photograph's own GPS, 40.9 m from the recorded viewpoint, and looks down at **−1.2°**, as the photograph does.
* **The block is furnished for Rockefeller Center** — **307 Citi Bike units**, 93 cooling towers, 74 street lamps, 63 manholes, 45 hydrants, **4 subway entrances**, 5 bus shelters, 3 LinkNYC kiosks, 1 newsstand.
* **21,045 pavement polygons and none dropped**, including **1,404 plaza** polygons and 5,518 sidewalk.
* **The mean and the midtone are close** — mean **1.076×**, p50 **1.132×**.

## What does not match

* **The Lower Plaza is not sunken in the picture.** 401 terrain quads were cut and replaced by a flat plate at grade, so the render shows continuous ground where the photograph shows a seven-metre drop.
* **Prometheus is not identifiable in the frame.** The gilded figure is the photograph's subject and the item's own name.
* **The rink is not there**, in either state — no ice, no renovation hoarding, no *THE CONCOURSE* lettering.
* **The reference caught the plaza mid-renovation**, so even a correct render would differ: the sheet compares a finished plaza with a building site.
* **Published under-lit at +4.20 stops**, beyond hand-held recovery; the luminance comparison should be read as that number (J83).
* **Two thirds of the photograph's contrast** — sd **0.1439** against **0.2288**, a ratio of **0.629**.
* **Almost no structures** — **1 tile imported, 3 without a file, 96 triangles** — over the Rockefeller Center concourse and the Sixth Avenue lines, which is the largest privately built underground complex in the city.
* **Props were capped to half** — **927 placed of 1,834 in range** at a **1,110,758-triangle** budget, **771 dropped for budget**, **405** of them tree rows, 3 dropped on a suppressed building.
* **Kit was capped to one piece in five** — **3,955 of 18,787 in range** at a **982,575-triangle** budget, 3,705 of them windows; the openings are drawn rather than cut (Stage 34 / J51).
* **12 props across four kinds in range have no asset** — **8 artworks**, 2 memorials, 1 drinking fountain, 1 real-time information sign. On this block the artworks are the point: Prometheus is one of them.
* **The park ground is only sampled beyond 400 m** — all **414 samples** fall in that band, with an under-fraction of **0.2609**, a worst of **−0.928 m** and a z-fighting fraction of **0.0242**.
* **4,006 agents were dropped** — 1,504 pedestrians outside the radius, 899 at the agent triangle budget, 833 vehicles outside the radius, 568 vehicles at the budget, **145 in the carriageway without crossing**, 33 riderless bodies, **22 off a walkable surface** on a plaza (J101), 2 vehicles off the carriageway.
* **No cloud**, and the reference's sky is barely in frame.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the plaza is not sunken in the picture | the landmark ground plate that replaced 401 cut terrain quads is one flat surface at the surrounding grade, so the 6.96 m well the model carries is covered; `parkground.faces_cut_for_landmark_ground` is 0 as well | **geometry — open, the ground plate is single-level and the subject is not (J96, amended)** |
| Prometheus is absent | the gilded figure is an artwork, and **8 artworks in range have no asset** — the kind is unmapped | **data — open, and it is the item's own name** |
| no rink, no hoarding, no lettering | neither the finished rink surface nor the renovation state is modelled, and no printed copy is invented anywhere (B5, B15a) | geometry + declared decision |
| the reference caught a building site | the chooser accepted a photograph of the plaza mid-renovation; it is a true photograph of the place and not of its ordinary state | verification — the pairing |
| published under-lit at +4.20 stops | a courtyard between towers at a 58° Sun is a shaft of shade, and the development is metered on the frame (J83) | verification — declared, and correct |
| chroma 1.875 | coloured flags over tan stone against a grey building site under sheeting — the inversion is the reference's state, not the render's saturation | reference |
| sd 0.629 | a flat ground plate and an evenly lit wall hold less range than a construction site in hard sun | geometry |
| 96 triangles of structures, three tiles without a file | those tiles are unbuilt, over the Rockefeller Center concourse and the Sixth Avenue lines | **data — open** |
| 927 props of 1,834, 405 tree rows dropped | the props triangle budget at 1,110,758 | performance |
| 3,955 kit pieces of 18,787 | the kit triangle budget at 982,575 | performance |
| openings drawn on the shell | Stage 34 / J51, measured at +48 GB | declared decision — physically impossible here |
| 12 props across four kinds unmapped | no asset exists for those kinds | data |
| under-fraction 0.2609 beyond 400 m | the park builder drapes on its own heightmap and the scene's differs; no sample falls nearer than 400 m on this sheet (J71) | geometry — open, bounded |
| 430 people of 2,783 asked | the agent triangle budget plus the placement rules, each with its own count | performance + verification |
