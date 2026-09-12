# Yankee Stadium

`landmark_yankee_stadium` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:161st St River Av td (2019-01-24) 26 - IND Vent Grates.jpg by Tdorante10, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2019-01-24 15:42:23, 1920x1280. [Commons page](https://commons.wikimedia.org/wiki/File:161st_St_River_Av_td_(2019-01-24)_26_-_IND_Vent_Grates.jpg) — camera GPS on the file, viewpoint confidence **high**, and the photograph's own description says what it is of: *"Looking at vent grates for the IND subway in median of East 161st Street, at 161st Street and River Avenue in Concourse"*. A wet January afternoon: standing water on the roadway, the long IND vent grate running down the middle of the sidewalk, litter on the concrete, bare plane trees along the kerb, the Deegan approach cut away on the left, an NYPD supervisor-parking sign, one parked Nissan, and the stadium's limestone wall filling the right third with the blue **GATE** lettering at the frame edge.

**Camera** — 40.827996, -73.926199 (NYC_TM 1995, 14179) at z 10.193 m NAVD88, a 1.6 m standing eye over terrain read at 8.593 m — the 10th percentile of 113 samples within 12.0 m, whose median is 8.88 and whose range runs 8.33 to 9.35 | azimuth 354.5°, pitch +2.1° | 35 mm on 36 mm (54.432° horizontal) | 1280x854. **This is the best-founded camera in the pass.** Its position is the photograph's own EXIF GPS, *"34 m from the item's recorded viewpoint -- the position the picture was taken from"*, and its heading is the bearing from that GPS to the stadium, **354.5°**, against the photograph's own estimated view direction of **354.6°** — a tenth of a degree apart. The clearance walk agrees: it found the recorded viewpoint *"boxed in: the view azimuth is closed off 46 m ahead, less than the 80 m this frame needs to show its subject"*, moved **35.7 m** onto the nearest real sidewalk polygon, and reports 88.4 m of clear view from there. Nearest built thing in frame: `prop_lamp_cobra_davit_17` at **9.2 m**, 27.2° off the axis. No simulated agent within 20 m.

**Sun** — azimuth 231.1°, elevation 12.2° at 2019-01-24T15:42:23-05:00, from the photograph's own EXIF DateTimeOriginal; 496 W/m² direct normal, Nishita sky, Filmic, **+4.27 stops**. Metered: **4.272 stops** on a linear median of **0.009318**, against a physical rule of 1.81, and the record publishes its own warning: *"under-lit: the scene needed +4.27 stops to read as a picture, more than the 4 a photographer recovers hand-held; the frame is published and this is the number to read it by."* A 12.2° January Sun in the south-west against a wall that faces east is exactly the case that rule exists for.

## Verdict — the camera is right, the wall is the right kind of wall, and the reference is a photograph of the drain covers

**The chooser had this photographer's picture of Yankee Stadium and took his picture of the vent grates instead.** Candidate 1 in the same folder is `File:161st St River Av td (2019-01-24) 34 - Yankee Stadium.jpg`, from the **same walk, the same day, and the identical GPS fix** — 40.827996, -73.926199, the same coordinate this camera stands on, **0.0 m** apart. It carries the same fetch score of **12.6**, the same estimated azimuth, the same author and the same licence. Its own description reads *"Looking at the exterior of Yankee Stadium at Gate 6, at the northwest corner of 161st Street and River Avenue"*. It lost on one term and one only: its `date_taken` is `2019` and the vent-grate frame's is `2019-01-24 15:42:23`, so only the latter satisfies `has_time`. **This is the only sheet in the pass where a photograph tied on every geometric term and lost purely to the clock** — and where the passed-over file is titled for the subject and the chosen one is titled for the drain covers (J112).

**The wall the render draws is the right kind of wall.** The Indiana-limestone arcade is there: round-arched openings 5.5 m wide, one per 8.2 m of the real OTI footprint, springing at 2.75 m and heading at 12.0 m; a pier 1.8 m wide between each pair standing 1.4 m proud; the name band at 14.5 to 17.0 m; the cornice at 24.0 to 26.5 m. Beside a photograph of that same wall the family resemblance is unmistakable, and it is the model's own 6,062 triangles of exterior doing the work, not a texture.

**Above the arch heads there is nothing between the piers.** The exterior builds arches to 12.0 m, piers to 24.0 m and a cornice above — and no wall between the piers over that 12 m band. So the render shows a colonnade you can see through to the concourse behind, where the photograph shows a solid limestone screen with tall arched window bays and slender mullions. That band is the most conspicuous part of the elevation in the reference and it is absent as a surface here.

**And the name band carries no name.** It is `box_from_to(p0, p1, n, 1.1, 14.5, 17.0, limestone)`: 2.5 m of stone standing 1.1 m proud, all the way round. The catalogue's fidelity statement says *"the name band"* and that is precisely what is modelled — a band. The word **YANKEE STADIUM**, the blue **GATE** numerals, the club marks, the banners, the entrance signage: none of it exists, here or anywhere in this build (J110).

**The height probe measured the inside of the bowl.** 43 of 43 rays landed on built fabric and read **24.96 m** above a ground of 4.41 m, on `lm_c_yankee_stadium.2` — the seating bowl, 252.1 by 241.1 m in plan. The catalogue entry sits **9.0 m** from the coordinate, inside the 120 m radius, and carries **42.0 m**, cited to Populous as the top of the upper deck and its frieze. J74 prefers a measurement to a catalogue figure, so the record publishes 24.96 m for a stadium whose published height is 42.0 m — because a vertical ray at the centre of a stadium comes down on the raked deck, not on the rim. The same shape as Trinity Church, where the catalogue's figure was the tower's own and the probe measured the nave.

**The fan was then built to the wrong shape, and the visible fabric is 125 m nearer than the coordinate.** With 24.96 m for height and 252.1 m for width the fan came out **252.1 m across and 24.6 m tall** — half-angles of **27.22°** and **3.3°** — aimed at *"the subject's mid-height, 12.3 m above its ground"* at a range of **213.1 m**, which is out over the infield. But the stadium's own fabric stands **87.9 m** from the lens: the record names `lm_c_yankee_stadium.3` as both what the rays land on and the nearest own fabric. Two rays reach within the 25.0 m reach of the coordinate and two more strike the building nearer than the coordinate and are counted apart from them, so **four of thirteen rays are on the stadium and the published fraction is 0.154**. A 252 m building whose coordinate is its centroid cannot pass a 25 m on-subject test from its own kerb.

**The elevated 4 train is built, loaded, and 3.3 degrees outside the right edge of the frame.** The item's viewpoint note says *"under the elevated 4 train"*. Three of the four structures tiles carry **15,936 triangles of elevated steel**, its nearest vertex **16.7 m** from the lens, and **none of 912 sampled vertices falls inside the frame cone** — the frame runs 327.3° to 21.7° in yaw and the el's closest approach is 30.5° off the axis. It is not missing; the azimuth, set by the bearing to the stadium's centroid, simply points away from it. Structures here are complete: **4 tiles, 0 without a file, 24,688 triangles.**

**The two frames agree on tone and disagree on colour and weather.** The exposure gap is **0.186 stops** and the medians are within 6 per cent (1.061×), which for a frame that needed 4.272 stops of development is a good result. But contrast is **0.651×** and chroma **2.378×** — the largest colour excess read this round. The photograph is a wet, flat, sunless January dusk with standing water and grey sky; the render is a dry matte street under a clear Nishita dome with a warm limestone wall. `rain_mm_h` is 0.00 and `snow_cover` 0.00 on every sheet in this pass (J97), so the wet roadway that makes half of the reference's picture cannot appear.

**And the near-field terrain is as good as this build gets.** Of **568** park-ground samples within 150 m, **none** sits below the terrain, and the tightest clears by **0.023 m**.

## What matches

* **The camera stands where the photographer stood** and looks where the photograph looks, to a tenth of a degree.
* **The limestone arcade is modelled as geometry** and reads as the same wall: round arches, piers, name band, cornice.
* **The frieze exists** — 2,560 triangles from 39.0 to 42.0 m, the 3.0 m band the 1923 stadium's copper original is replicated from.
* **43 of 43 probe rays found built fabric.**
* **Structures are complete**: 4 tiles, none without a file, 24,688 triangles, including the elevated the frame happens to miss.
* **Building tiles are complete**: 4 of 4, 162,882 triangles, none missing and none LOD-substituted.
* **The trees are bare**, right for 24 January, and 1,792 of the 2,223 props are trees.
* **The exposure agrees**: a 0.186-stop gap and medians within 6 per cent.
* **Nothing under the terrain in the near field**: 0 of 568 samples, minimum clearance +0.023 m.
* **The under-lit warning is published, not smoothed.**
* **Two MTA buses** on a Bronx sheet, where the fleet belongs.

## What does not match

* **The reference is a photograph of subway vent grates**, chosen over the same photographer's photograph of Yankee Stadium from the identical GPS fix and the identical score (J112).
* **The wall above the arch heads is open between the piers** where the photograph has a solid screen of tall arched windows.
* **The name band has no name on it**, and the GATE lettering, the club marks and every other sign are absent (J110).
* **The record publishes 24.96 m for a stadium published at 42.0 m**, because the probe measured the raked deck at the centre (J74).
* **The sightline reads 0.154** on a frame filled by the building, because the coordinate is the centroid of a 252.1 m plan and the visible fabric stands 87.9 m out against a 25.0 m reach (J113's family).
* **No wet ground, no reflections, no standing water**, on a reference whose roadway is a mirror (J97).
* **Chroma 2.378 and contrast 0.651**: too much colour and too little range against a flat grey afternoon.
* **No vent grates in the sidewalk**, on the sheet whose reference is named for them; the scene holds 22 of the prop, none of them here.
* **No litter, no kerb barrier, no perimeter globe lamps** — the photograph's street furniture is a low concrete wall and a row of the stadium's own lamp standards; the render has two DOT cobra heads.
* **The trees are mature broad canopies** where the photograph has slim young plane trees, and 607 of them had their species substituted.
* **One yellow cab and no boro taxi in the Bronx**, which is the borough the green cab was licensed for (J105).
* **383 kit pieces suppressed** under the landmark shell, so the blocks the stadium replaces carry none of their own detail.

## Measured for this assessment

| figure | where it comes from |
|---|---|
| the model is 12,387 triangles over 7 mesh nodes: exterior 6,062 to z 26.5 m, frieze 2,560 from 39.0 to 42.0 m, bowl 1,008 to 39.0 m, LOD1 1,783, base core and plinth 408 each, field 158 | node-by-node accessor bounds of `blender_out/landmarks/c_yankee_stadium.glb`, honouring each node's translation; the record's own in-scene figure is 10,604 |
| the arcade is one 5.5 m round-arched opening per 8.2 m of footprint edge, springing 2.75 m and heading 12.0 m, with a 1.8 m pier between standing 1.4 m proud to 24.0 m | the exterior loop of `blender/landmarks/c_yankee_stadium.py` |
| nothing is built between the piers above the arch heads | the same loop: it emits arched openings, piers, the name band and the cornice, and no wall surface over the 12.0 to 24.0 m band |
| the name band is a plain limestone box from 14.5 to 17.0 m standing 1.1 m proud, with no lettering | `box_from_to(p0, p1, n, 1.1, 14.5, 17.0, C.M.limestone)` in the same file, annotated "the name band" |
| the frieze's arched motif is 160 rectangular posts of 0.5 by 0.5 by 1.8 m on a three-ring loft | the frieze block of the same file, which resamples the bowl ring to 160 segments and puts one box on each |
| 15,936 triangles of elevated steel are loaded across three of the four structures tiles, the nearest vertex 16.7 m from the lens, and 0 of 912 sampled vertices fall inside the frame cone, the closest passing 30.5 deg off the axis and so 3.31 deg outside the right edge | the `el_steel` nodes of `blender_out/tiles/t_1_13`, `t_1_14` and `t_2_14` `tile_structures.glb`, placed by adding the tile origin, against the record's camera position, azimuth and field of view |
| the frame cone runs 327.3 to 21.7 deg in yaw and -16.9 to +21.0 deg in pitch | the record's `camera` block: azimuth 354.5 deg, pitch +2.1 deg, 54.432 deg horizontal on a 1280 by 854 frame |
| the passed-over candidate shares this camera's GPS to 0.0 m, its fetch score of 12.6 and its estimated azimuth, and its description names the stadium | the three kept candidates in `docs/verification/reference/landmark_yankee_stadium/meta.json` |
| this is the only sheet in the pass whose chosen photograph was tied from the same spot by an unchosen one of equal or better score and won only on the clock | every reference `meta.json` against the `reference_photo.file` its render used, comparing GPS offsets within 5 m, fetch scores and `date_taken` lengths |
| the fetch stores no EXIF focal length for any photograph, so every sheet's lens is a default or a widening | the per-photo keys in the reference `meta.json` files, none of which carries a focal length; this record's `lens_reason` reads "default 35 mm full-frame equivalent" |
| 2,017 kit pieces | the sum of the record's `scene.kit.per_category`, whose `total` is null |
| 24 January is inside the leaf-off window | the `leaf_off` rule in `blender/verify/render_sheets.py` (J97) |

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the reference is a photograph of vent grates | `pick_reference_photo` breaks a tie on every geometric term with `has_time`, and the photographer's stadium frame kept only the year (J112, and J71 for what nothing tests) | **verification — open, and the cheapest fix in the pass: the file is already on disk** |
| the wall above the arch heads is open | the exterior loop builds openings, piers and bands and never a wall plane between them | **content — open** |
| the name band has no name | no lettering exists anywhere in this build; every sign, band and marquee is blank geometry (J110) | **content — open** |
| 24.96 m published for a 42.0 m stadium | a vertical probe at a stadium's centroid lands on the raked deck; J74 prefers the measurement to the catalogue and has no notion of a subject with a hole in the middle | **verification — open** |
| the sightline reads 0.154 | the subject's coordinate is the centroid of a 252.1 m plan and the fabric that fills the frame is 87.9 m away, against a fixed 25.0 m reach (J109's tolerance and J113's fan, together) | **verification — open** |
| the elevated is not in the picture | the azimuth is the bearing to the subject's centroid, not the photograph's composition; the el is built and loaded and passes 3.31 deg outside the right edge | verification — declared, and not a data gap |
| no wet ground on a wet reference | the snapshot request carries no weather at all, so rain, temperature and snow cover are the defaults on every sheet (J97) | **verification — open** |
| chroma 2.378 | a clear procedural sky and a warm limestone tint against a desaturated overcast dusk | reference — no source exists |
| 4.272 stops of development | a 12.2 deg January Sun in the south-west on an east-facing wall (J83) | verification — declared |
| one yellow cab and no boro taxi in the Bronx | `TrafficSim::sampleClass` splits the taxi share with no geography (J105) | **runtime — open** |
| 383 kit pieces suppressed | kit is suppressed wherever a landmark shell replaces the tiled buildings, which is correct here and costs the surrounding blocks their detail | performance — declared |
