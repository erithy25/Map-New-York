# Visual comparison — renders against licensed photographs

Stage: **comparison** (`blender/verify/`). This is condition 3 of `docs/DEFINITION_OF_DONE.md`:
*"Screenshots from the seven standard viewpoints compared with real photographs."*

Every sheet in this directory puts one licensed photograph beside a Cycles render taken from the
position that photograph was taken at, with a caption strip that states the camera, the Sun, the
licence, and exactly which pieces of world data were in the frame. `INDEX.md` lists every subject
and its status. Each rendered subject has its own `assessment.md` with the judgement written down.

This report is written from the sheets, not from the code. Where the simulation falls short the
gap is named and attributed to one of five causes: **missing data**, **missing geometry**,
**missing material detail**, **lighting**, **camera/reference metadata**.

---

## 1. How a sheet is made

`blender/verify/` is three modules, run as `python3 blender/verify/render_sheets.py --slugs <slug>`.

**`scene.py` — assemble the world around a point.**

| layer | source | how it is placed |
|---|---|---|
| terrain | `data/processed/tiles/{tile}/terrain.png` + `.json` (16-bit, 501x501 at 2 m, `z = z_min_m + v*z_scale_m`), 2,916 tiles on disk | displaced **graded** grid over the scene square — the heightmap's own 2 m spacing within 150 m of the camera, then coarsening geometrically to at most 40 m at the edge of the scene; PNG row 0 is the north edge so the array is flipped before sampling; quads whose four corners sit on a tile's flattened water surface get a separate water material |
| building shells | `blender_out/tiles/{tile}/tile_buildings.glb` — 920 tiles, 1,083,026 buildings, zero open shells | translated by the tile origin (`tx*1000, ty*1000`). Each glb carries LOD0/LOD1/LOD2 as sibling objects; exactly one LOD is kept per tile (LOD0 inside 1.2 km, LOD1 to 2.5 km, LOD2 beyond) and the rest deleted, otherwise every shell would be drawn two or three times over. Not every tile carries every LOD, so a tile with no mesh at the LOD its distance asks for is drawn at the nearest LOD it *does* have, and the substitution is printed on the sheet |
| pavement | `data/processed/roads/pavement/{tile}.parquet` (§7) — **617,518 polygons across 972 tiles**, counted from every file's Parquet metadata | roadbed, sidewalk, median, plaza, curb, crosswalk and parking-lot polygons triangulated in plan, every vertex lifted to the heightmap surface plus that kind's own offset, so the pavement follows the real grade and the curb reveal is the real 0.15 m |
| landmarks | `blender_out/landmarks/catalog/*.json` — 93 entries | translated to `origin_tm`; the model axes are already parallel to NYC_TM ("no rotation to apply on import"). Two catalogue shapes are handled: `glb` + `bounds_local_m` for the towers, and a `lods` map with `path` + `bounds` for the bridges and monuments. A landmark is kept when its model's *bounding box* touches the scene disc, not just its origin, so a bridge that spans kilometres is not dropped for having a distant origin |
| props | `data/processed/tiles/{tile}/props.parquet` (§8) — 1,724,589 rows over 1,576 tiles | instanced against `blender_out/props/props_asset_catalog.json` (122 assets), matched on `kind` → `dataset_kind`; trees matched on the census species (`Styphnolobium japonicum` → `tree_sophora_*`) and size class. Yaw is the negated compass heading, because every prop asset is authored facing +Y. **No scale is ever applied** |
| facade kit | `data/processed/tiles/{tile}/kit_placements.bin` (§6, 40-byte records), 920 tiles | instanced against the tile's own `kit_placements.json` header, which carries the `kit_id → glb` map the placements were written with. Yaw is `yaw_deg + 90` deg (the record holds the wall's outward normal as an angle CCW from east; every kit piece is authored with its wall plane at y=0 and `into_building = +Y`, so its outward direction is local -Y). `scale` is applied to local X only — it is the along-run stretch, not a uniform scale, so a 12x cornice must not become 12x tall |

Instancing shares one mesh datablock across every placement, so 13,000 kit pieces cost 13,000 object
headers and one copy of the geometry. Everything is capped by a triangle budget (4.5 M by default,
allocated buildings → landmarks → props → kit) and every cap is recorded in `render.json` and
printed on the sheet, so a frame never silently omits content.

**`camera.py` — put the camera where the photographer stood.**

* Position: **the chosen photograph's own EXIF camera GPS**, where it exists and sits within 250 m
  of the item's nominal `viewpoint`; otherwise the nominal viewpoint, with the sheet saying the
  photograph's GPS was rejected and by how far. Of the 57 subjects rendered, the photograph's own
  GPS was adopted for **45**, rejected as mis-tagged for **10** (up to 3.6 km away) and absent for
  **2**.
* Heading: the bearing **from the position actually used** to the item's `subject` coordinate.
  When the camera stands on the photograph's own GPS this is used unconditionally — position and
  heading then come from the same measurement. When it stands on the nominal viewpoint the
  recorded `azimuth_deg` is kept unless the subject bearing disagrees with it by more than 20 deg.
  The bearing is never copied from the metadata; it is always recomputed at the camera.
* Height: the heightmap surface plus an eye height read from the viewpoint note — 1.60 m for a
  standing observer, and an explicit entry with its published source where the note names a
  structure (Top of the Rock's 70th-floor deck at 259.1 m, the TKTS steps at 4.6 m, a Staten
  Island Ferry's upper deck at 6.4 m above the waterline).
* The ground under the camera is read from a *neighbourhood*, not one sample: the median inside
  5 m where the note names the raised surface the photographer stood on, and the 10th percentile
  inside 12 m where the note says roadway or sidewalk — the 1 m DEM carries building grades and
  raised plinths that would otherwise lift a street camera onto the terrace beside it.
* Lens: 35 mm on a 36 mm sensor (54.4 deg horizontal) by default; per-slug overrides with a written
  reason where the reference framing needs a wider lens (24 mm for the Top of the Rock panorama
  and the Duffy Square bowtie, 28 mm for the Brooklyn Heights Promenade, the Staten Island Ferry
  deck, Washington Street in DUMBO and Bethesda Terrace). A portrait reference is rendered with the
  lens fitted to the *vertical* axis, because that is where a turned camera's 36 mm dimension lies.
* The optical axis is level. A level axis keeps vertical building edges vertical, which is the
  convention every architectural photograph follows and the only way a render and a photograph
  can be compared on proportion; the one exception is a subject inside 250 m that needs less than
  8 deg of tilt to centre.

**`render_sheets.py` — light it, render it, compose it.**

* The Sun is put where it actually was at the instant the reference photograph was taken: the EXIF
  `DateTimeOriginal`, in America/New_York, through `services/nycsim_live/astronomy.py` — the same
  SPA implementation the live-services stage uses. Where only a date or a year is recorded the
  fallback is 09:30 local and the sheet says so.
* Sun strength follows the direct normal irradiance for that elevation (1361 W/m2 at the top of
  the atmosphere, Kasten-Young air mass, 0.7 transmittance per air mass) scaled by one calibration
  constant, measured with test renders, that puts a 0.26-albedo sunlit ground at about 150/255
  through the Filmic view transform — where a correctly exposed photograph of concrete sits. The
  view exposure then opens by up to three stops as the light falls off, the way a photographer
  would, and never stops down.
* Sky: Nishita at the true Sun elevation and azimuth.
* In a daylight frame the prop kit's modelled light cones are made transparent and the street-lamp
  lenses are switched off (NYC street lighting is dusk-to-dawn); traffic-signal and shopfront
  emissives are left on. In a night frame nothing is touched, so the frame shows exactly how much
  emissive content the world actually has.
* Cycles CPU, 32 samples with adaptive sampling (threshold 0.03) and denoising, 2 light bounces,
  3 threads (the machine is shared with the other stages).
* Composition with Pillow: reference left, render right, caption strip below naming the subject,
  where the camera stands and why, the viewpoint note, the photograph's title/author/licence/date
  and Commons URL, the camera parameters, the Sun, the ground mesh, what was in the frame, and
  every gap and cap.

Sheets that embed a CC BY-SA photograph are derivative works and carry the same licence; the sheet
says so in its own caption.

### Resolution

Renders are 1280 px wide for any reference at 3:2 or wider. A quarter of the reference photographs
(137 of 519) are portrait, some as tall as 1:2.2; at 1280 px wide those cost three times the
samples of a landscape frame for the same content, so their width is reduced to hold every frame to
the same pixel budget as a 1280x853 landscape frame. The angle of view is unchanged — only the
sampling density. Each sheet states its own resolution.

---

## 2. Four faults in the comparison stage itself, found by looking at the sheets

Every one of these was corrupting *every* frame.

**2.1 Position and heading came from different places.** The first version took the heading from
the chosen photograph's own GPS (`camera_gps_to_subject`) while leaving the *position* on the
item's nominal viewpoint. For Washington Street in DUMBO those are 35 m apart, so the camera stood
on Water Street and looked along a bearing that only works from Washington Street: the render was a
brick wall where the photograph is the Manhattan Bridge tower. Both now come from the same source
(§1). Across the 57 subjects the photograph's own GPS is a median **52.5 m** from the item's
recorded viewpoint, so this was not a small correction. Guarded by
`tests/test_comparison.py::test_camera_position_and_heading_come_from_the_same_measurement`.

**2.2 Recorded viewpoints inside buildings.** The reference viewpoints are recorded to five decimal
places of latitude but they are *nominal* positions. Tested against the real footprints in
`data/processed/tiles/{tile}/buildings.parquet`, **52 of 171 (30 %) fall inside a real building
footprint**, up to 52 m from the nearest wall. Left alone this renders a black frame — the first
Brooklyn Heights Promenade render was uniformly black (mean pixel 0.08/255) because the eye point
sat inside `t_-5_-1_roof_membrane`, 14 m below that shell's roof.

`camera.py` detects it (a ray straight up from the eye point that hits a building shell or a
landmark means the eye is inside it) and corrects it in two steps: first **snap to the real
pavement** — `data/processed/roads/pavement` holds the DoITT roadbed, sidewalk, plaza, median and
crosswalk polygons, so the nearest one of those *is* the surface the note names — and only if
nothing paved is in reach, walk radially outward in 2 m rings. A candidate is accepted only if it
is both in open air and *able to see*: nothing opaque within 8 m of the lens in a 12 deg cone, and
a clear view along the azimuth for half the subject distance (capped at 80 m). Without that second
test the camera settles into a light well and renders brickwork. A rooftop viewpoint is instead
walked forward to the parapet, because a deck's viewpoint is recorded as one lat/lon for the whole
slab while the photographs are taken at the edge.

This is a defect in the reference metadata, not in the world. It should be fixed at source by
snapping each viewpoint to the nearest point outside a footprint — preferably to the photograph's
own GPS, which §2.1 shows is usually available and much better.

**2.3 Every street tree rendered as a solid opaque cone.** Each tree glb carries a six-polygon
`<species>_billboard` card with an `IMPOSTOR_*` material intended as a distant stand-in. The
exported material is a flat opaque colour with **no alpha texture** (`base_color 0.8,0.8,0.8`,
`alpha 1.0`), and the card carries no `_LOD1` suffix, so the scene loader drew it *at LOD0 over the
real branches*. Every tree in every street-level frame was therefore a solid cone: the black spikes
down Fifth Avenue and the black mass that filled the DUMBO frame were both this.  `scene.py` now
drops impostor cards and prints how many it dropped on the sheet.
**This is a defect in the props stage, not in the comparison stage** — the exported card should
carry an alpha-masked crown texture and be tagged `_LOD1` so it is only used at distance. Until it
is, no consumer of `blender_out/props/*.glb` can draw those assets at LOD0 as exported. Guarded by
`tests/test_comparison.py::test_tree_impostor_cards_are_not_drawn_over_the_real_branches`.

**2.4 The ground mesh was too coarse to be a street.** The terrain was a uniform grid capped at
300 samples a side, which over a 700 m street scene lands one height every **4.7 m** and over a
5 km skyline scene one every **26 m**. A flat sidewalk 10 m from the lens became a rolling mound
and the East River shoreline a smooth ramp. The grid is now graded: the heightmap's own **2 m**
spacing within 150 m of the camera, coarsening to 40 m at the edge. For the Fifth Avenue scene that
is 209² samples and **86,528 triangles** where the uniform grid cost 180,000 — better resolution
for less than half the geometry. Guarded by
`tests/test_comparison.py::test_the_ground_mesh_resolves_the_near_field_and_still_reaches_the_horizon`.

Two further corrections came out of the same pass:

* **Tiles with no LOD2 were dropped from skylines.** 20 of the 99 tiles in the Brooklyn Heights
  Promenade scene carry LOD0 and LOD1 but no LOD2 mesh, and the loader dropped them rather than
  substituting. That scene now imports **77 of 99** tiles instead of 57. Guarded by
  `tests/test_comparison.py::test_a_tile_without_the_requested_lod_is_drawn_at_the_nearest_lod_it_has`.
* **Long-range scenes had no foreground.** Props and facade kit were switched off entirely for any
  scene over 1.5 km, so the Brooklyn Heights Promenade frame had no railing, no benches and no
  trees where the photograph is half foreground. A ground-level long-range viewpoint now keeps a
  150 m ring of props and a 70 m ring of kit; an observation deck (eye above 20 m) still does not,
  because from 260 m up those props are sub-pixel.

### The prop scale question, answered with numbers

The review reported "two props rendered at roughly a metre across — a red blob and a blue dome".
Both were identified by projecting `props.parquet` through the recorded camera and measured:

* the red object is `hydrant_fdny` at **14.4 m** from the camera, published size 0.36 x 0.36 x
  0.75 m — a correct NYC dry-barrel hydrant;
* the blue object is `mailbox_usps` at **11.3 m**, published size 0.47 x 0.60 x 1.27 m — a correct
  USPS street collection box (50 in tall). At 11.3 m its 0.60 m depth subtends 3.0 deg, which is
  68 px of a 1208 px / 54.4 deg frame; it measures about 75 px on the render. It is the right size.

`python3 blender/verify/scene.py --audit-props` now measures **every** exported prop the way the
scene loads it (LOD0 meshes, the glb's own local matrices) against the size its catalogue entry
publishes. Result: **0 of 122 assets are the wrong size** and 0 fail to load. The only four whose
imported geometry exceeds `nominal_size_m` are the street lamps, whose extra extent is exactly
their `bounds_with_effects` — the modelled light cone, which the daylight pass makes transparent.
Guarded by `tests/test_comparison.py::test_every_prop_asset_matches_the_size_its_catalogue_publishes`.

What made those two props read as oversized is not scale but context: `mailbox_usps` is 484
triangles, so its curved hood is a faceted dome and its body a plain box, and there are **no people
and no vehicles anywhere in any frame** to give the eye a human reference.

---

## 2.5 Six black or featureless frames: which of the three causes it was

The orchestrator's sweep found six unusable renders in the first pass, every one of them a
street-level view: `drive_bronx_arthur_ave` (mean 0.016), `drive_lower_manhattan_broadway_wall_st`
(0.038), `drive_lower_manhattan_stone_st` (0.001), `drive_midtown_sixth_ave_45th` (sd 0.009),
`drive_queens_bayside` (sd 0.012) and `landmark_40_wall_street` (0.006). Three causes were
proposed; here is which one it was.

**Not the datum.** The camera's z is absolute NAVD88, the same datum the shells use: it is the
heightmap value (`z_min_m + v*z_scale_m`, NAVD88) plus an eye height, and it is printed on every
sheet. The proof is the Top of the Rock frame: the camera was placed at 281.0 m and came to rest
1.6 m above the roof of 30 Rockefeller Plaza, whose published deck is 259.1 m above a 20.3 m
plaza — 279.4 m absolute. Had the z been a height *above ground* the camera would have sat at
260.7 m absolute, 19 m inside that building, and every frame in the set would have been black
rather than six.

**It was the camera inside or under geometry.** Every one of the six is a viewpoint that lands
inside a footprint or under a paved surface, and the ray tests in place at the time did not catch
all of them:

* the up-ray only counted building shells and landmark models, so a camera under a *pavement*
  polygon passed. Bethesda Terrace is the extreme case: its plaza polygons bridge the 5.4 m step
  between the lower plaza and the upper terrace, and the photograph's own GPS lands under that
  bridged surface, sealing the eye 1.8 m below the paving. That frame rendered pure black twice
  before the cause was found;
* the forward test was a single level ray 2 m long, which slips between two piers of the terrace
  or past the 0.2 m trunk of the street tree that fills the DUMBO frame.

Both are now covered: a ray straight up that hits terrain or pavement is a block (nothing outdoors
has ground over its head), and a 20-ray fan across 12 deg of bearing and 24 deg of elevation
rejects any eye point with something solid inside a metre of the lens. Where the photograph's own
GPS lands in such a place and the item's nominal viewpoint does not, the nominal viewpoint is used
and the sheet says why. Stone Street went from mean 0.001 to 0.151 and Bethesda Terrace from
0.000 to 0.698 on those corrections alone.

**Lighting is a contributing cause, not the cause.** Stone Street is a 6 m alley between 25 m
walls; even correctly placed, at 32 samples with two light bounces, its floor sits at mean 0.151 —
legitimately dark, and the reference photograph of it is dark too. No exposure change was made to
flatter it.

**The guard.** `render_subject` now measures every frame's mean and standard deviation the moment
it is written, against the same thresholds as
`tests/test_world_integration.py::test_verification_renders_can_actually_serve_as_evidence`
(mean below 0.06; mean above 0.94 with sd below 0.05; sd below 0.025). A frame that fails is not
accepted: the clearance correction is *forced* — the eye point is treated as blocked even though
no ray test caught it, snapped to the nearest real pavement with a clear view, and rendered once
more. If it still fails, `render.png` and any stale `sheet.png` are deleted and a
`render_error.txt` is written naming the metrics, the camera, the clearance decision, the free
distance along the view azimuth, the Sun elevation and the exposure. Nothing that cannot serve as
evidence is left in the directory looking like evidence. The measured mean and standard deviation
of every accepted frame are recorded in its `render.json` under `frame`.

## 2.6 Three more faults, found the same way

**A landmark sheet whose landmark is out of frame.** The rule that keeps the optical axis level is
what makes a render comparable with a photograph on proportion, and it was applied with a fixed
35 mm lens. For 40 Wall Street — a 227 m tower photographed from 200 m — that puts the crown far
above the top of the frame, and the sheet said so honestly while showing a dark corner of a street
instead of the building. The lens is now widened until a *level* axis contains the subject, with
12 % headroom, down to a floor of 18 mm below which the distortion would stop the two frames being
comparable; the sheet prints the focal length it chose, the height of the subject above the lens
and the angle that forced it. Where even 18 mm is not enough, the sheet says the top is still cut
off rather than tilting the camera and skewing the verticals.

**An eye point in open air that can see nothing.** Seventh Avenue at Garfield Place put the camera
in the open with a party wall 8.6 m ahead: not dark, not inside anything, and completely
featureless — the frame passed the luminance gate at sd 0.085. A viewpoint whose azimuth closes off
inside 12 m is now corrected like a blocked one. The threshold is deliberately lower than the 20 m
a *candidate* must satisfy: a camera with 17 m of street in front of it is looking across a road at
the opposite facade, which is a real street-level view and is left alone.

**A camera under a hole in the terrain.** The 9/11 Memorial pools drop 9 m below the plaza and the
1 m DEM records them, so the 10th-percentile street ground rule inside 12 m found the bottom of a
pool and put the eye 1.3 m under the plaza deck. Every candidate within 80 m did the same, so the
frame was rejected outright — correctly, and with a diagnostic. The clearance search now reads the
ground twice at each candidate, the street percentile first and the height at the point itself
second, and takes whichever is not underground.


### The six near-black frames, separated by cause without rendering anything

Testing each camera position against the real footprints in
`data/processed/tiles/{tile}/buildings.parquet` (`footprint`, `ground_z`, `roof_z`) separates them
into three distinct faults, which is why no single fix cleared them:

| subject | mean / sd | camera (NYC_TM, z) | finding | cause |
|---|---|---|---|---|
| `landmark_nyse` | 0.000 / 0.001 | (-5106, 794, 8.9) | **inside** BIN 1001020, ground 8.5 m, roof 27.8 m | eye 0.4 m above that building's floor and 19 m below its roof |
| `landmark_moma` | 0.005 / 0.030 | (-2330, 6804, 21.9) | **inside** BIN 1087646, roof 95.4 m | eye inside the building |
| `landmark_nypl` | 0.021 / 0.043 | (-2582, 5853, 24.4) | **inside** BIN 1035330, roof 84.7 m | eye inside the library itself |
| `landmark_metlife_building` | 0.016 / 0.013 | (-2299, 5636, 17.5) | nearest footprint **0.1 m** | eye hard against a wall |
| `landmark_new_york_times_building` | 0.035 / 0.007 | (-3519, 6181, 12.7) | nearest footprint **0.2 m** | eye hard against a wall |
| `landmark_st_patricks_cathedral` | 0.023 / 0.018 | (-2358, 6545, 23.0) | nearest footprint **1.6 m** | eye hard against a wall |
| `landmark_911_memorial_pools` | 0.000 / 0.001 | (-5293, 1241, 2.9) | nearest footprint 18.1 m, **not** inside anything | eye under the plaza: two separate faults, one in the ground reading and one in the World Trade Center model's own height. Both are in §2.7; the frame now renders at 0.475 / 0.137 |

Every tile these cameras need has its `tile_buildings.glb` on disk (2/2, 1/1 in each case), so none of
them is a loading failure. Three are viewpoints recorded inside a building, three are recorded
against a wall, and one is under the terrain — and all three classes are now caught before the
frame is rendered: the up-ray test for a shell roof or a paved surface overhead, the 20-ray cone
test for anything solid within a metre of the lens, and the requirement that a camera with a named
subject can see roughly as far as its subject. Where a corrected camera still cannot produce a
usable frame the render is refused, the PNG is deleted, and the subject is dropped from the sheet
set with its reason recorded in `render_error.txt`. The gate's thresholds were not touched.

## 2.7 The last black frame: a landmark model standing 3.5 m too high

`landmark_911_memorial_pools` was the only one of the 57 subjects without a usable render, and it
stayed black through two rounds of corrections. Both of the diagnoses written down before this pass
were wrong about the object, so this one was settled by measurement.

**What the camera was actually under.** `lm_b_wtc_site.232` — the object a ray straight up from the
eye point hits — is the World Trade Center model's **plaza**: a two-triangle, four-vertex
520 x 520 m quad on material `b_sidewalk` whose every vertex sits at exactly **7.000 m NAVD88**.
Not a roof, and not (as the second diagnosis claimed) an oak canopy: the nearest of the 220 memorial
oaks is **93.3 m** away and all of them lie between -1.0 deg and +5.7 deg of the horizon from this
camera. The eye stood at 5.795 m, **1.21 m underneath that quad**, with the South Pool's granite
wall 0.15 m ahead; **400 of 400 sampled sky directions were blocked**, 113 by the plaza and 287 by
the pool wall. That is the whole explanation of mean 0.0003.

**Why the plaza is up there.** The 1 m DEM reads **4.26 m NAVD88** at the same point, so the model's
plaza deck floats **2.74 m** above the ground the camera's eye height was measured from. The cause is
in `blender/landmarks/b_wtc_site.py`: `GRND = 3.5` is used both as the model's *local* plaza level
(`bc.ground_plane("plaza", 260.0, GRND, "sidewalk")`, and every tower's `z0`) and as the frame
origin's NAVD88 z (`bc.local_frame(PLAZA_CENTRE_TM, GRND, ...)`). `blender/landmarks/b_common.py`
states the contract — "a world point is `origin_tm + local`" — so the plaza level is added twice and
the **entire World Trade Center site model stands 3.5 m too high**. Checked against the other 92
catalogue entries, the median |origin z - DEM at the origin| is **0.07 m**: this is one model's
fault, not the convention. **It is a defect in the landmarks stage and is left there to be fixed;
nothing in the comparison stage edits the model.** Every scene that contains `b_wtc_site` — 17 of
the 57 — carries the same 3.5 m error, invisible at distance and decisive at 60 m.

**What the comparison stage does about it.** Three changes, all in `blender/verify/camera.py`:

* **`deck_underfoot`** — an eye point put under a *landmark's own* level deck, within one eye height
  of it and clear once stood upon, is raised onto that deck, and the sheet says so. A landmark
  carries ground the heightmap knows nothing about, and where the two disagree the modelled deck is
  the surface a visitor walks on. Terrain and pavement deliberately keep the old treatment: they are
  draped on the same heightmap the eye height came from, so an eye under *them* is a fault in the
  ground reading, which the pavement snap already corrects (Bethesda Terrace). The correction
  applies to the recorded eye point only and not to the candidates the position search tries: a
  candidate that works only after being lifted onto a model's deck is a worse place to stand than
  one on ground the heightmap and the model agree about.
* **Foliage is not a roof.** The up-ray now steps past trees and reports the first *built* thing
  overhead. An upward ray cast cannot tell a ceiling from a canopy, and standing under a tree — or
  an awning, a scaffold shed or a bridge deck — is what a person on a plaza does. Trees are
  identified by material, not by name: every tree asset exports its canopy on `LEAF_<species>`, its
  trunk on `bark_<species>` and its billboard on `IMPOSTOR_<species>`, and scanned across all 122
  prop assets, 127 landmark models, 138 kit pieces and the tile shells those three prefixes appear
  on tree geometry and on nothing else. This matters because the memorial's 220 oaks are objects
  *inside* `lm_b_wtc_site` whose names say nothing about what they are — no name list would have
  caught them. `view_distance` steps past them too, as it already did for `prop_tree_*`.
* **The parapet walk refuses to move a camera whose supporting surface still carries it at the end
  of its probe.** That is ground, not a deck with an edge; walking the memorial plaza's 520 m slab
  to its "edge" would have carried this camera 250 m off the viewpoint.

**And one more impostor card.** §2.3 says the tree impostor cards are dropped. That was true only of
the props library, where the card is its own `<species>_billboard` object. `b_wtc_site.glb` built its
oaks through `bc.prop_template`, which **joins** the card into the tree's own mesh: one mesh with
three material slots (`IMPOSTOR_pin_oak_medium`, `bark_pin_oak`, `LEAF_pin_oak`). Dropping whole
objects cannot reach that, so all 220 memorial oaks were drawn with two canopies. `scene.py` now
strips the faces on any `IMPOSTOR_*` slot of a mesh that also carries real geometry, and counts
them: 12 card faces on 2 template meshes, instanced 220 times.

**Result.** 904x1206 at 64 samples, from the photograph's own GPS at **8.60 m NAVD88**: mean
**0.475**, sd **0.137**, against a gate of 0.06. **57 of 57 subjects now have a usable render.**
The remaining gaps in that frame — the plaza plane drawn across both pool openings, so no camera
anywhere on the plaza can see a pool; the level axis against a photograph tilted 40 deg down the
parapet; the unbound `MEMORIAL_NAMES` texture — are written up in its `assessment.md`.

**Which other scenes moved.** One: `landmark_911_memorial_pools`, from no render to a usable one.
Every other clearance decision in the set was re-measured and is unchanged — `bethesda_terrace_fountain`,
`landmark_moma`, `landmark_hudson_yards_vessel`, `landmark_high_line`, `landmark_oculus`,
`landmark_one_world_trade_center` and `top_of_the_rock_south` were all rebuilt and re-placed with the
new code and come out at the same camera to the metre. Two of them, `landmark_oculus` and
`landmark_one_world_trade_center`, *do* differ from the render.json on disk, but they differed before
this pass as well: the street-percentile void exclusion committed earlier (§2.6) changes the ground
read at their subject points, and their shipped sheets predate it. Measured at the code as it stands,
`landmark_oculus` keeps its camera and moves its pitch from -3.3 deg to -0.3 deg, and
`landmark_one_world_trade_center` moves from (-5193, 1094, 7.2) to (-5205, 1057, 8.5) with its
clearance rule falling from "radial search with a clear view" to "open air only". **Both need
re-rendering and neither has been re-rendered here**; their sheets and assessments are stale by that
much.
