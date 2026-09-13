# Elevated subway street: Broadway (Brooklyn) under the J

`street_elevated_broadway_bushwick_j` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Myrtle Avenue Jamaica Line 003.jpg by Kidfly182, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2021-08-09 16:25:45, 1920x1440. [Commons page](https://commons.wikimedia.org/wiki/File:Myrtle_Avenue_Jamaica_Line_003.jpg) — camera GPS on the file, viewpoint confidence **medium**, and its stored description is four words: *"View from the Myrtle Avenue Station."* The photograph is taken **on the elevated**, from a station platform: the yellow platform edge strip runs across the bottom left, then the running rails and the red-and-white striped third-rail cover boards, and above them the grey-green steel plate girders of the Myrtle Avenue Line crossing the Jamaica Line, three large graffiti pieces on the web plates, rust bleeding through the paint at every rivet line, and a Popeyes sign on a roof below.

**Camera** — 40.697147, -73.935722 (NYC_TM 1212, -333) at z 22.496 m NAVD88, a 1.6 m standing eye over terrain read at 20.896 m — the 10th percentile of 113 samples within 12.0 m | azimuth 127.0°, pitch 0.0° | 35 mm on 36 mm (54.432° horizontal) | 1208x906. The position is *"this photograph's own EXIF camera GPS (40.69715, -73.93572), 75 m from the item's recorded viewpoint -- the position the picture was taken from"*, and the eye datum is **terrain**: a standing observer 1.6 m above the pavement. The heading is the item's recorded 127.0°; the photograph's own was not derived from the image, and the record says what follows: *"the two halves of this sheet are not guaranteed to face the same way -- compare them on street width, storey height and material, not on composition."* The axis is level because the item names no subject, so there is no probe, no sightline and no visible fraction.

**Sun** — azimuth 255.8°, elevation 39.3° at 2021-08-09T16:25:45-04:00, from the photograph's own EXIF DateTimeOriginal; 838 W/m² direct normal, Nishita sky, Filmic, **+1.57 stops**. Metered: **1.574 stops** on a linear median of **0.060442** against a physical rule of 0.13. A bright August afternoon, and one of the least developed frames in the pass.

## Verdict — the photograph was taken on the elevated and the render was moved out from under it

**The reference is a view from the platform, and all three kept candidates say so.** The item asks for *"Broadway at Myrtle Avenue, Bushwick, roadway centre under the J/M/Z structure, looking south-east"* — a street. The fetch's own queries asked for *"Broadway Bushwick elevated J train street"* and *"Broadway Brooklyn elevated BMT Jamaica Line street level"*. What came back, and what it kept, is three photographs of the station: two described *"View from the Myrtle Avenue Station"* and one *"Bushwick 13 Myrtle Avenue station"*. There is no street-level candidate to choose. This is not the chooser's failure — the two 14.9-scoring candidates both carry full timestamps — it is J71's: nothing in the pipeline tests what a photograph is a picture of.

**The camera then answered a view from seven metres up with a view from the pavement.** The origin logic did the right thing and stood the camera on the photographer's own GPS fix. But `eye_datum` is `terrain` and `eye_source` is *"standing observer, 1.6 m eye height above the terrain surface"*, so a photograph taken from a platform deck is rendered from the roadway directly beneath it. J65 gives a viewpoint its landmark's upper deck when the item names one; nothing reads a *photograph's* elevation, and nothing in the fetch records one.

**And then the clearance walk moved the camera out from under the elevated, on the sheet whose title is "under the J".** The record's reason is exact: *"inside `t_1_-1_struct_el_steel` (a ray straight up from the eye point hits its roof)"*, so the recorded viewpoint failed the indoors test and the camera was moved **17.1 m** onto the nearest roadbed polygon. The rule that keeps a camera out of a building's interior cannot tell a building from a railway on legs, and the one item in the set that is *supposed* to stand under a roof is the one it evicted. `scored_on_subject_sightline` is **false** — there is no subject to score the move against, so the walk had only the indoors test to satisfy and satisfied it by leaving.

**The elevated is still in the picture, at the edge.** After the move the nearest built thing in frame is `t_1_-1_struct_el_steel` at **11.8 m**, **27° off the axis** — the left frame edge, which is where the pale grey-green station structure with its canopy and its SUBWAY entrance stands in the render. The structures are substantial: **5 tiles, 2 without a file, 52,824 triangles**, of which the Myrtle Avenue tile alone carries **17,496 of elevated steel, 3,208 of platform and 3,208 of canopy**. The colour is right too — the builder paints el steel `painted_metal_green` because *"the IRT/BMT els are a grey-green"*, and the photograph's girders are exactly that.

**What the elevated is not is a girder structure.** `stlib` describes the real thing in its own docstring — *"the running rails sit on longitudinal stringers carried by transverse floor beams over the bent caps"* — and then builds a **solid slab 1.2 m thick on square columns 0.45 m across at 13.72 m centres, inset 1.3 m, with a 0.9 m cap girder**. So there are no web plates, no rivets, no floor beams, no stringers, no ties, no running rails and no third rail: the underside of the el is a flat plate. The photograph is a close portrait of precisely those members. Nothing above the deck exists either — no track, and no train.

**And there is no graffiti anywhere in this build.** The word does not appear in a single Python file in the repository. Three of the photograph's largest shapes are throw-ups on the girder webs; the render's el steel is clean paint.

**The street fabric, where it can be compared, is fair.** 7 of 7 building tiles built with none missing and none LOD-substituted, 407,906 triangles, and **8,518 kit pieces of 11,632 in range** — 5,584 windows, 976 window accessories, 711 storefronts, 329 parapets, 321 entrance doors, 122 bulkheads, 83 cornices, 70 string courses, 64 fire escapes, 37 scaffolds and **2 billboards**. The brick corner buildings with continuous ground-floor storefronts under a green fascia are the right kind of Broadway.

**The tone gap is the shadow the render does not have.** The photograph's median sits **0.664 stops below** the grey convention because most of its picture is steel in its own shade, with bright August sky through the gap; the render is metered to 0.25 above. That is a **0.914-stop** gap with the render brighter, and the render carries **0.595×** the photograph's range and **0.709×** its chroma. The p95 tells the same story: 0.6577 against 0.8979. There is no deep shadow in the render because there is no structure over the camera any more.

**The crowd and the traffic.** 88 vehicles and 336 people; **9 yellow medallion cabs to 4 boro taxis** in Bushwick, which is outside the street-hail exclusion zone and where the green cab is the licensed fleet — the inversion J105 measures, and the opposite of what the Park Slope sheet drew. Every one of the 88 vehicles is at LOD2. Two DSNY trucks and two MTA buses are right for this corner. 2,767 props with **none dropped**, but **897 of the 2,182 trees had their species substituted** — 41 per cent, above the pass-wide 39.19 per cent of J108.

**No park ground at all.** 0 meshes and 0 surfaces, with 7 tiles in the 795 m radius carrying no park-ground file, so every open surface in this frame is bare terrain.

## What matches

* **The elevated is built, loaded and in frame**: 52,824 triangles of structures over 5 tiles, the Myrtle Avenue tile carrying 17,496 of el steel.
* **The colour of the steel is right**, and chosen for the reason the photograph shows: the els are painted a grey-green.
* **The station is there** with its platform, its canopy, its street entrance and a crowd at the stair head.
* **The camera stands on the photographer's own GPS fix.**
* **The street is the right kind of street**: brick, continuous storefronts at grade, 8,518 kit pieces over 7 complete building tiles.
* **The record declares its own limits** — no subject, a heading not derived from the image, and an instruction to compare fabric rather than composition.
* **Nothing dropped from the props budget**, 2,767 placed.
* **Two DSNY trucks and two MTA buses** on a Bushwick arterial.
* **The frame is well lit**: 1.574 stops of development, one of the smallest in the pass.

## What does not match

* **The photograph is taken on the elevated and the render from the pavement**, because the eye datum is terrain and nothing reads a photograph's height.
* **The clearance walk evicted the camera from under the elevated** — 17.1 m, on the sheet titled "under the J" — because a railway on legs failed the indoors test.
* **The elevated has no girders, rivets, floor beams, stringers, ties, running rails or third rail**: it is a 1.2 m slab on 0.45 m columns at 13.72 m centres.
* **No train**, on a photograph taken from a platform beside a running track.
* **No graffiti**, which is three of the reference's largest shapes; the word appears in no Python file in this repository.
* **No rust, no paint failure, no age of any kind** on steel the photograph shows bleeding at every rivet line.
* **The render is 0.914 stops brighter, with 0.595× the range**, because the deep shade under the structure is gone with the structure.
* **41 per cent of the trees are the wrong species** (J108).
* **No park ground**: 0 meshes and 0 surfaces over 7 tiles with no file.
* **No signage**: no traffic signal, no street-name blade, no station sign beyond the one SUBWAY entrance marker (J110), against a photograph whose readable content is a Popeyes fascia and three tags.
* **Nine yellow cabs to four boro taxis in Bushwick** (J105).

## Measured for this assessment

| figure | where it comes from |
|---|---|
| the Myrtle Avenue tile carries 17,496 triangles of elevated steel, 3,208 of platform and 3,208 of canopy | node-by-node accessor counts of `blender_out/tiles/t_1_-1/tile_structures.glb`, against the five tiles the record lists as imported |
| the elevated is a 1.2 m slab on 0.45 m square columns at 13.72 m centres, inset 1.3 m, with a 0.9 m cap girder, and no member above the deck | `DECK_THICKNESS_M`, `BENT_SPACING_M`, `COLUMN_SIDE_M`, `COLUMN_INSET_M` and `CAP_DEPTH_M` in `blender/structures/stlib.py`, and the rail loop of `build_structures.py`, which emits a deck and bents and nothing else |
| the builder's own docstring describes the members it does not build | the `DECK_THICKNESS_M` comment in `stlib.py`: "the running rails sit on longitudinal stringers carried by transverse floor beams over the bent caps" |
| el steel is painted a grey-green on purpose | the material map in `stlib.py`, whose comment reads "NYC elevated steel is painted; the IRT/BMT els are a grey-green" |
| the word graffiti appears in no Python file in the repository | a case-insensitive search of every `.py` file under the repository root |
| all three kept candidates describe a station rather than a street | the `description` fields in `docs/verification/reference/street_elevated_broadway_bushwick_j/meta.json`, against the item's own viewpoint note and the two fetch queries recorded beside them |
| 8,518 kit pieces | the sum of the record's `scene.kit.per_category`, whose `total` is null |
| 897 of 2,182 trees substituted is 41 per cent, above the pass-wide figure | the record's `props.tree_species_substituted` against its tree count, and DEVIATIONS J108 for the 39.19 per cent |

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the reference is a view from the platform | the fetch returned three station photographs for two street-level queries and nothing tests what a photograph is a picture of (J71) | **verification — open** |
| the render answers it from the pavement | the eye datum is terrain and 1.6 m for every streetscape item; J65 raises an eye only when the *item* names a deck, never when the photograph was taken from one, and the fetch stores no photograph elevation | **verification — open** |
| the camera was moved out from under the elevated | the indoors test is a ray straight up from the eye, which cannot distinguish a building's ceiling from a railway deck; `scored_on_subject_sightline` is false, so nothing weighed the move against what the sheet is for | **verification — open, and specific to the two elevated-street items** |
| the elevated has no girders, rails or train | the structures builder makes a deck and bents from the surveyed centreline, width and deck elevation, which is what `rail_structures.parquet` carries; nothing in the source table describes the steelwork | data — declared, and the limit of the source |
| no graffiti, no rust, no wear | no weathering or decal layer exists anywhere in this build | content — open, no source |
| 0.914 stops brighter with 0.595× the range | the camera left the shade it was standing in | verification — consequent on the move |
| 41 per cent of trees the wrong species | ten species with two appearances each against the census's 132 (J108) | content — open |
| no park ground | 7 tiles in range carry no park-ground file | data — open |
| no signage of any kind | the verification renderer never reads the sign or signal export (J110) | **verification — open** |
| nine yellow cabs to four boro taxis | `TrafficSim::sampleClass` splits the taxi share with no geography (J105) | **runtime — open** |
