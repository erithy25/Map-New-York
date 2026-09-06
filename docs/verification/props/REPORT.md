# Stage 4 — Street props and vegetation

Owner lane: `blender/props/`, `blender_out/props/`, `docs/verification/props/`, `tests/test_props.py`.
Nothing outside that lane was modified.

---

## 1. What was built

**122 assets**, one `blender_out/props/<id>.glb` each, plus one catalog JSON each in
`blender_out/props/catalog/` (merged for convenience into `blender_out/props/props_asset_catalog.json`).
Zero failures; `blender_out/props/_smoke.glb` (the placeholder from wave 1) is deleted.

| category | assets | LOD0 triangles | mean | glb bytes |
|---|---:|---:|---:|---:|
| lighting | 4 | 6,240 | 1,560 | 0.8 MB |
| traffic | 6 | 9,958 | 1,659 | 0.9 MB |
| signs | 9 | 1,024 | 113 | 0.3 MB |
| furniture | 35 | 42,414 | 1,211 | 4.2 MB |
| construction | 8 | 2,568 | 321 | 0.8 MB |
| vegetation | 60 | 295,200 | 4,920 | 72.1 MB |
| **total** | **122** | **357,404** | 2,930 | **79.2 MB** |

LOD1 across the whole library is **17,608 triangles** (4.9 % of LOD0).

### Lighting (`blender/props/p_lighting.py`)
`lamp_cobra_davit` (NYC DOT standard: octagonal tapered pole, 30 ft / 9.14 m mounting height, 12 ft / 3.66 m
davit arm, LED cobra head), `lamp_bishops_crook` (1892 replica, fluted cast iron, scrolled crook, pendant
teardrop at 24 ft / 7.32 m), `lamp_park_twin` (NYC Parks twin-lamp post, two six-sided lanterns on scrolled
arms 0.62 m either side), `lamp_highmast` (100 ft / 30.5 m tapered shaft, six luminaires on a 1.7 m ring).
Each carries an emissive lens material (`LAMP_EMISSIVE` / `LAMP_GLOBE_*`) and a `LIGHT_CONE` pair of crossed
alpha planes for the night light pool. The light-cone planes are excluded from the recorded bounds — they are
an effect volume, not the object's size — and the catalog keeps both (`bounds` and `bounds_with_effects`).

### Traffic control (`blender/props/p_traffic.py`)
Three-section 12-inch head to the ITE/MUTCD polycarbonate section (13.75 x 15.5 x 8 in body, 12 in lens,
9.5 in tunnel visor) in NYC dark-green housings with a black backplate and a retroreflective yellow border,
mounted four ways: `signal_mastarm_6m` (20 ft arm, 2 heads), `signal_mastarm_9m` (30 ft arm, 3 heads),
`signal_pedestal` (4.5 in pipe, head bottom at the 8 ft sidewalk clearance) and `signal_spanwire` (8.2 m pole,
catenary + tether, one suspended head, 6.5 m wire stubs so the engine can chain assemblies pole to pole).
`signal_ped_countdown` is the NYC one-section 16 x 18 in countdown head with two independent runtime slots —
`PED_SYMBOL` (upraised hand / walking person) and `PED_COUNTDOWN` (two seven-segment digits) — both emissive
and both UV 0..1. `ped_pushbutton` is the APS station: 2 in button and locator LED at the PROWAG 42 in height
under the MUTCD R10-3e sign.

Both mast arms keep the MUTCD 15 ft (4.57 m) minimum clearance under the lowest head: 4.73 m on the 6.1 m arm,
4.57 m on the 9.14 m arm. This is asserted by the test suite.

### Signs (`blender/props/p_signs.py`)
Seven blanks, each with the front face carrying the `SIGN_FACE` material and that face's UV spanning **exactly**
(0,0)-(1,1) over its bounding box, u to the reader's right and v up:

| id | MUTCD / NYC code | face size |
|---|---|---|
| `sign_r6_1_oneway` | R6-1 | 0.914 x 0.305 m |
| `sign_r1_1_stop` | R1-1 | 0.762 m octagon |
| `sign_r1_2_yield` | R1-2 | 0.914 x 0.792 m triangle |
| `sign_r2_1_speed` | R2-1 | 0.610 x 0.762 m |
| `sign_nyc_parking_18` | NYC DOT parking | 0.305 x 0.457 m |
| `sign_nyc_parking_24` | NYC DOT parking | 0.305 x 0.610 m |
| `sign_street_name_blade` | NYC street name | 0.152 x 0.762 m, double sided, with pole bracket |

plus `post_u_channel_3m` and `post_u_channel_2m` (galvanised 3 lb/ft U-channel, 10 ft and 8 ft). The
warning-sign blank `sign_roadwork_w20_1` (48 in W20-1 diamond on a folding stand) is in the construction module
and carries the same slot.

The default legends are drawn procedurally at build time by `blender/props/_legends.py` to the published layout
of each sign, in the SIL-OFL Overpass typeface (an open Highway Gothic derivative already in `assets/fonts/`).
The engine replaces the texture per instance from `roads/signs.parquet` (`mutcd_code`, `text`, `arrow`).

### Street furniture (`p_furniture.py`, `p_transit.py`)
`hydrant_fdny`, `litter_basket_wire` (DSNY 24 in x 31 in wire mesh), `litter_basket_betterbin`, `mailbox_usps`,
`standpipe_siamese`, `linknyc_kiosk` (2.90 m, two portrait 55 in `SCREEN_EMISSIVE` displays), `bus_shelter_cemusa`,
`newsstand_stainless`, `bike_rack_cityrack`, `citibike_kiosk` + `citibike_dock_unit` (tileable along X at the
0.90 m station pitch) + `citibike_bike`, `subway_entrance` (green railing, concrete treads, double-sided SUBWAY
plate) with `subway_globe_green` / `subway_globe_red` as separate assets keyed to the dataset's `has_globe`,
`mta_line_bullets`, `vent_grate_sidewalk`, `manhole_coned`, `manhole_dep`, `steam_stack_3m` / `_6m`,
`bollard_steel`, `planter_concrete`, `bench_worlds_fair`, `tree_guard`, `tree_grate`, `trash_bags_small` /
`_large`, `cart_halal`, `cart_hotdog`, `cart_coffee`, `muni_meter`, `fire_alarm_box`, `pigeon`, `rat`.

`mta_line_bullets` holds the 23 route bullets as separate 0.30 m meshes, each with its own `MTA_<line>` material
in the official colour; the node translation is layout only (zero it to place a bullet). Yellow bullets carry
black glyphs, all others white.

### Construction / work zone (`p_construction.py`)
`jersey_barrier` (FHWA F-shape, 10 ft, tileable), `barrel_orange` (MUTCD 36 in drum), `traffic_cone` (28 in),
`roadway_plate` (8 x 12 ft x 1 in steel with cold-patch ramps), `sign_roadwork_w20_1`, `construction_fence`
(8 ft painted plywood, tileable at 2.438 m), `flag_us_pole`, `flag_nyc_pole`.

### Vegetation (`p_vegetation.py`, `_leaves.py`, `census_dbh.py`)
Ten species x three DBH classes x {in leaf, bare winter} = **60 assets**.

The species and the sizes are **derived from the census, not chosen**: `blender/props/census_dbh.py` reads
`data/raw/nyc_opendata/street_trees_2015.csv` (683,788 rows, 652,173 alive), takes the ten commonest identified
species among living trees (the genus-only bucket `Prunus` is excluded — it is not a species) and, for each, the
25th / 50th / 90th percentile of measured trunk diameter. Height and crown spread come from
`pipeline/nycsim_pipeline/furniture/allometry.py` — the same curve the props table uses, `height_source = 1`.
The result is cached in `blender/props/dbh_classes.json`:

| species (census `spc_latin`) | alive | DBH small / medium / large (cm) | height (m) |
|---|---:|---|---|
| Platanus x acerifolia (London planetree) | 87,014 | 40.6 / 55.9 / 81.3 | 20.50 / 23.95 / 27.44 |
| Gleditsia triacanthos var. inermis (honeylocust) | 64,263 | 15.2 / 25.4 / 43.2 | 9.43 / 13.10 / 17.35 |
| Pyrus calleryana (Callery pear) | 58,931 | 15.2 / 20.3 / 35.6 | 7.81 / 9.16 / 11.75 |
| Quercus palustris (pin oak) | 53,185 | 20.3 / 43.2 / 76.2 | 11.78 / 18.21 / 22.53 |
| Acer platanoides (Norway maple) | 34,189 | 25.4 / 35.6 / 55.9 | 12.04 / 14.50 / 17.63 |
| Tilia cordata (littleleaf linden) | 29,742 | 12.7 / 22.9 / 45.7 | 7.71 / 11.31 / 16.29 |
| Zelkova serrata (Japanese zelkova) | 29,258 | 10.2 / 15.2 / 38.1 | 7.17 / 9.43 / 16.36 |
| Ginkgo biloba (ginkgo) | 21,024 | 10.2 / 20.3 / 40.6 | 6.77 / 10.92 / 16.67 |
| Styphnolobium japonicum (Sophora) | 19,338 | 12.7 / 20.3 / 43.2 | 7.07 / 9.58 / 14.44 |
| Acer rubrum (red maple) | 17,246 | 12.7 / 25.4 / 50.8 | 8.34 / 13.10 / 18.58 |

That list is exactly the ten species the brief named, which is a useful cross-check: the brief's list and the
census agree.

Each tree is a recursive branch skeleton (tapered swept tubes, species-specific clear-trunk fraction, scaffold
count, divergence angle, upward bias and droop) carrying alpha leaf cards. The centrelines — never the radii —
are scaled at the end so the finished mesh has exactly the allometric height and crown spread while the trunk
radius stays exactly `dbh_cm / 200`. A leafed tree is fitted to its foliage envelope, a bare one to its branch
envelope, which is the botanically correct measurement in each state.

Leaf atlases are drawn procedurally per species in `_leaves.py` from the species' botanical leaf form (palmate
for the maples and planetree, pinnately compound for honeylocust and Sophora, pinnately lobed for pin oak,
cordate for linden, obovate for Callery pear, elliptic-serrate for zelkova, flabellate for ginkgo), composited
into a 2 x 2 cluster atlas with straight alpha. Bark is a CC0 AmbientCG set per species, tinted per species.

LOD1 is three crossed billboards (6 triangles) carrying an impostor drawn from **the same skeleton the LOD0 was
built from** — the branch polyline and the leaf-card centres projected orthographically — so the silhouette
matches the mesh it replaces rather than being an unrelated picture.

LOD0 triangle budget: **max 9,564** (`tree_pin_oak_large`), mean 4,920, ceiling 12,000. Asserted by the tests.

---

## 2. Conventions honoured

* Metres, Z-up in Blender; glTF exported Y-up (`(X, Y, Z) -> (X, Z, -Y)`).
* Origin at **ground contact**, **+Y = facing** (the side a pedestrian sees; lenses, sign faces and screens have
  their normals along +Y). Recorded in every catalog entry and in `asset.extras.nycsim.anchor`.
* Three documented anchor exceptions, all recorded in the entry and enforced by the tests:
  `sign_face_center` (the seven flat blanks — a blank has no ground contact), `bracket_pole_axis`
  (the street-name blade clamps to a pole) and `bullet_center` (the MTA bullets are decals).
  `manhole_*` (frame 0.06 m below grade) and `subway_entrance` (stair shaft 2.40 m below grade) are genuinely
  ground-contact assets whose geometry extends below z = 0; the tests allow exactly those.
* `LOD0` and `LOD1` nodes per file, wired with `MSFT_lod` (`extensionsUsed` declares it, LOD1 is removed from the
  scene root list so viewers without the extension show only LOD0).
* `asset.extras.nycsim` per DATA_CONTRACTS §13. Blender's exporter can only write **scene** extras, so
  `_core.set_asset_extras()` post-processes the GLB and copies the same dict onto `asset.extras` — the file now
  carries it in both places.
* Runtime material-slot contract: `SIGN_FACE`, `LAMP_EMISSIVE`, `LAMP_GLOBE_GREEN/RED`, `LIGHT_CONE`,
  `SCREEN_EMISSIVE`, `AD_PANEL`, `PED_SYMBOL`, `PED_COUNTDOWN`, `FLAG_FACE`, `LED_RED/YELLOW/GREEN`,
  `MTA_<line>`. Every one is present in at least one exported file and checked by the tests.

---

## 3. How it was verified

### Tests — `tests/test_props.py`, 869 passed

```
$ python3 -m pytest tests/test_props.py -q
869 passed in 2.53s
```

The tests parse the exported `.glb` with `blender/props/glb_reader.py` (a dependency-free GLB/accessor reader,
no bpy, no pygltflib) and assert on the file, not on the generator's intentions:

| test | what it proves |
|---|---|
| `test_library_is_complete_and_unique` | glb set == catalog set; `_smoke.glb` gone |
| `test_every_family_is_represented` | per-category minimum counts |
| `test_variants_and_kinds_resolve` | every `variants` id exists, no self-reference, every prop has a `dataset_kind` and real notes |
| `test_glb_loads` (x122) | GLB2 container, header length, JSON chunk, `asset.extras.nycsim` with the right `prop_id`, units and facing |
| `test_lod1_present_and_wired` (x122) | `LOD0`/`LOD1` nodes, `MSFT_lod` link, `extensionsUsed`, LOD1 not a scene root, LOD1 has geometry |
| `test_lod1_is_cheaper_than_lod0` (x122) | LOD1 <= 62 % of LOD0 (flat blanks excepted, where LOD1 is an exact copy) |
| `test_bounds_match_nominal` (x122) | measured glTF bounds (light cones excluded, node transforms honoured) against the published nominal, per axis, within the prop's own tolerance |
| `test_anchor_is_ground_contact` (x122) | base at z = 0 within 12 mm, or a declared anchor exception |
| `test_sign_face_slot` (x122) | `SIGN_FACE` present where required and **UV range exactly (0,0)-(1,1)** on every primitive that uses it |
| `test_sign_blanks_cover_the_required_mutcd_set` | all seven blanks present at their published face sizes |
| `test_lighting_has_emissive_lamp_and_light_cone` (x4) | emissive lamp material with a non-zero `emissiveFactor`, plus a `LIGHT_CONE` |
| `test_signal_heads_are_nyc_green_with_backplates` | dark-green housing, black backplate, retro yellow border, three LED lenses, and the MUTCD 4.57 m clearance |
| `test_pedestrian_signal_has_runtime_slots` | `PED_SYMBOL` + `PED_COUNTDOWN`, head bottom at 2.44 m |
| `test_mta_bullet_colours_are_exact` | every `MTA_<line>` `baseColorFactor` converted linear -> sRGB equals the official hex, for all 23 routes |
| `test_mta_bullet_glyph_contrast` | yellow bullets black glyphs, all others white |
| `test_subway_globes_are_the_right_colours` | both globe materials present and emissive |
| `test_tree_budget_and_billboard` (x60) | LOD0 <= 12,000 triangles; LOD1 is exactly 6 triangles (three crossed billboards) |
| `test_tree_library_covers_the_census_top_ten` | the 10 species x 3 classes x 2 states matrix is complete and matches `dbh_classes.json` |
| `test_tree_dimensions_follow_the_census_and_allometry` (x60) | DBH, height, crown and trunk radius equal the census/allometry values |
| `test_bare_and_leafed_trees_share_a_skeleton` | a winter tree is the same tree without leaves (same branch count, height, crown) |
| `test_textures_are_licensed` | every embedded texture set is CC0 with a source URL |
| `test_polycounts_are_recorded_and_sane` | non-empty LOD0, plausible file size, finite bounds |

The MTA colour test deliberately re-states the brand-guideline table instead of importing the generator's
constants, so a drift in `_core.MTA_LINE_COLORS` fails the test rather than being copied into it.

### Renders — `docs/verification/props/`

Contact sheets (`sheet_*.png`) and the composed curb scene (`curb_test.png`), Cycles CPU, 20 samples,
1200 px wide, **orthographic** camera. Orthographic is deliberate: every prop on a sheet is at the same
metres-per-pixel, so a wrong size cannot hide behind perspective. Each prop stands beside a 1.75 m
human-height reference rod with a white band at 1.00 m, and is captioned with its id and its measured
bounding box. The camera stands on the +Y side so every prop presents its facing side.

`curb_test.png` is 30 m of Manhattan curb: roadway, curb stone, a sidewalk slab with the subway stair opening
actually cut out of it, and a blank building wall, carrying the cobra-head lamp post, the 6.1 m signal mast arm,
a countdown pedestrian signal, hydrant, wire litter basket, a planetree in a pit with grate and guard, LinkNYC,
a NYC parking sign on its U-channel post, the subway entrance with a green globe, USPS box, bollard, bench,
refuse bags, a Con Edison manhole in the roadway, a traffic cone and a pigeon.

---

## 4. Scale and proportion errors found in the renders and fixed

Every item below was found by opening a render, not by inspecting code.

| # | found in | error | fix |
|---|---|---|---|
| 1 | first furniture sheet | The camera stood on the **-Y** side, so every prop presented its back: the mailbox hopper, the Better Bin opening and the hydrant steamer all faced away. | `render_still()` now places the camera on the +Y side (the documented facing direction) and the sun azimuth was mirrored with it. |
| 2 | first furniture sheet | Perspective row layout made a 0.75 m hydrant ~30 px tall next to a 12 m row; relative size was unreadable. | Switched the sheets to an orthographic camera with the ortho scale set from the row length, and split the big sheets into groups of <= 6. |
| 3 | `furniture_a` | The Better Bin's throw opening was modelled as a box **protruding** from the body instead of a recess. | Opening moved inside the shell (y 0.11-0.25 against a 0.30 m body radius) and the lip pulled in with it. |
| 4 | `furniture_a` | The siamese standpipe's inlets splayed too wide and too high — it read as a "Y" rather than an FDC wye. | Inlet angle and rise reduced (caps now at 0.95 m, 0.13 m off the axis); nominal updated to the measured 0.36 x 0.33 x 1.02 m. |
| 5 | `traffic_signals` | Heads hung 4.13 m over the roadway — **below** the MUTCD 15 ft (4.57 m) minimum. | Arm attachment raised to 5.45 m with a 6.30 m rise and the head hanger shortened from 0.22 m to 0.07 m: clearance now 4.73 m (6.1 m arm) and 4.57 m (9.14 m arm). A test now asserts it. |
| 6 | `trees_medium` | Crowns were far too sparse — the trees read as saplings, not street trees. | Leaf placement re-budgeted: cards are distributed over the tips the skeleton actually produced against a per-class total (520 / 820 / 1120) and the card size raised from 0.115 to 0.140 x crown. Mean vegetation LOD0 went 3.0k -> 4.9k triangles, still under the 12k ceiling. |
| 7 | `trees_medium` | The ground pad was centred on the origin while the row ran to +75 m, so the pad edge cut across the frame; later, the rotated orthographic frame still caught a pad corner. | The pad is sized and centred on the row and runs 400 m past it in both directions. |
| 8 | `trees_medium` | Ten long ids in one caption strip overlapped into unreadable text. | Captions staggered over bands with a tick line to the prop. |
| 9 | bounds check | Bare-winter trees came out up to 22 % narrower than their leafed twins: the crown scaling was fitted to the (absent) foliage envelope. | Bare trees are fitted to the branch envelope; both states now land on the allometric spread. |
| 10 | bounds check | The Citi Bike tyre torus had its **major** radius at the wheel radius, so the bike sat 24 mm below grade. | Major radius reduced by the tube radius; the bike now stands exactly on z = 0. |
| 11 | bounds check | Tilted refuse bags and the roadwork sign's splayed legs dipped 15-80 mm below grade. | Added `_core.settle_to_ground()` and applied it to the refuse piles, the roadwork sign and the trees (whose trunk-foot ring could tilt a few mm below zero). |
| 12 | bounds check | Mast-arm/span-wire nominal depth was 0.66 m against a measured 0.59 m, and the U-channel post's bolt-hole plugs stuck 5 mm out of the 38 mm section. | Nominals corrected to the reference-derived bounding box; hole plugs sunk inside the web. |
| 13 | `signs_nyc`, `signs_regulatory` | **The sign blanks rendered as blank dark plates.** `sign_blank()` put the `SIGN_FACE` polygon on the *far* side of the 2 mm blank and then reversed every normal in the prism to satisfy a facing check — so the viewer saw the aluminium back — and the face UV ran mirrored (u increasing to the reader's *left*). | `sign_blank()` rewritten: the face sits on the facing side, `recalc_face_normals` leaves the prism outward-facing, and u increases to the reader's right. Verified by decoding the exported accessor: on a +Y blank, u = 1.0 at the -X extreme and 0.0 at +X, and the face normal is glTF -Z (Blender +Y). |
| 14 | `lighting` | **All four lamps vanished from the sheet.** The sheet dropped any imported object carrying a `LIGHT_CONE` material — but a prop is exported as one joined mesh, so the whole lamp went with the cone. | The daylight sheets delete the light-cone *polygons*, not the object; caption bounds skip the same polygons. |
| 15 | `mta_bullets` | Measured height 1.60 m against a nominal 1.06 m. Blender's glTF importer instantiates nodes that **no scene references**, so the `MSFT_lod` LOD1 subtree was imported and rendered on top of LOD0 — on every sheet. | The sheet drops objects whose `nycsim_lod` extra is 1. The exported files are unchanged and spec-correct; this is an importer-liberality note the engine integrator should know about (see §6). |
| 16 | `curb_test` | The lamp post was missing (bug 14) and props were rotated with `Euler.rotate_axis("Z")` applied to the importer's X+90 conversion root — i.e. in local space, not world. | Placement now composes a world-space `Matrix.Rotation(heading, "Z")`. The 24 m planetree also put its canopy far above a 1.7 m eye-level frame, so the pit tree became a Callery pear. |
| 17 | `lighting` | The davit and crook arms reach along +Y, straight at the sheet camera, so they were foreshortened off the top of the frame. | The lighting sheets are shot nearly side-on (`azimuth` 78 deg / 66 deg / 40 deg) so the arm profile reads. |
| 18 | `lighting_night` | The light cones rendered as solid white cones that swallowed the lamps. | Cone gradient alpha reduced 0.55 -> 0.20 and its emission 3.0 -> 1.1; the cones now read as a light shaft. |
| 19 | `trees_large` | Two long captions collided and one measurement silently lost its leading digit ("16.862" printed as "6.862"). | Captions now use up to three bands, each drawn on its own dark plate so any residual collision is visible rather than silent. |

Remaining, deliberately accepted deviations from nominal (all inside the per-prop tolerance):
`trash_bags_small` 14.0 % on one axis (a random pile has no exact size — tolerance 20 %),
`tree_pin_oak_large` 12.4 % and eight other trees 10-12 % on one horizontal axis (tolerance 18 %; a procedural
crown is fitted to the target on both horizontal axes, and the leaf cards on the outermost twigs overshoot),
`citibike_bike` 10.9 % on width (handlebar + pedal envelope against a nominal quoted for the frame).

---

## 5. Fidelity achieved vs. target, and the gaps

**Achieved.** Every object in the brief exists as a real, complete mesh at its published dimension, with the
material slots the runtime needs, LOD1, and a catalog entry naming the reference. Dimensions come from published
standards wherever one exists (MUTCD/ITE for signals and signs, FHWA for the barrier, PROWAG for the push
button, Executive Order 10834 for the US flag, NYC DOT street-lighting and parking-sign practice, DSNY, USPS,
NYC Admin Code 20-231 for the newsstand footprint, MTA brand guidelines for the bullet colours) and from the
2015 Street Tree Census plus the project's own allometry for the trees.

**Gaps, stated plainly:**

1. **Manufacturer-exact geometry is not reproduced.** No licensed CAD was used. The Better Bin, the LinkNYC
   kiosk, the Cemusa shelter and newsstand, the Parkeon Muni-Meter, the Citi Bike bicycle and the food carts are
   built to their published overall dimensions and to a recognisable silhouette from public photographs — they
   are not part-for-part models. This is the same fidelity statement ADR-009 makes for the vehicle fleet.
2. **The New York City flag's seal is simplified.** `flag_nyc_pole` draws the seal's principal charges (the
   windmill-sail saltire, the two beavers, the two flour barrels and the date 1625) rather than the full engraved
   arms. The material is the runtime-swappable `FLAG_FACE` slot with UV 0..1, so an exact seal image drops in
   without touching geometry.
3. **Trees are procedural, not scanned.** Species identity comes through crown habit, bark set and leaf form,
   not through a botanically exact branch architecture. Autumn/spring foliage colour is not baked — only the
   summer atlas and the bare-winter state exist; the engine is expected to drive seasonal colour from the
   season, and a third (autumn) atlas per species is a one-function addition to `_leaves.py`.
4. **Hydrant paint.** Modelled in FDNY red. DEP also paints hydrants silver with a colour-coded bonnet; that is
   a runtime tint variant, noted in the catalog entry, not a second asset.
5. **Sign legends are defaults, not per-instance truth.** The baked legends are correct MUTCD/NYC layouts
   (STOP, YIELD, ONE WAY, SPEED LIMIT 25 — the NYC citywide default, NO STANDING ANYTIME, an alternate-side
   street-cleaning regulation, and a street-name blade reading "500 W 42 ST"). Real per-instance text arrives
   from `roads/signs.parquet` at runtime through the `SIGN_FACE` slot. That parquet does not exist yet.
6. **No night render.** The light cones and emissive materials are authored and exported but the verification
   renders are daylight; a night pass belongs with the engine's lighting rig, which cannot run here.
7. **Vegetation dominates the disk budget** — 72 MB of the 79 MB, almost all of it the 1024 px bark colour and
   normal maps embedded once per glb. If the engine shares materials across assets on import, stripping the
   embedded textures from the 60 tree files would cut the library to roughly 12 MB.

---

## 6. What the next agent needs to know

### Placement contract
* Origin = ground contact, +Y = facing, metres. Rotate about Z by the props table's `heading` (compass degrees,
  clockwise from north) after mapping heading -> Blender yaw.
* `signal_mastarm_*`: the **arm runs along +X** and the heads face +Y, so the asset must be yawed so that +Y
  points at the oncoming traffic; the arm then automatically reaches across that approach. Recorded per asset as
  `arm_direction_blender`.
* `signal_spanwire`: the wire runs along +X with 6.5 m stubs — chain instances pole to pole.
* Tileable assets carry `tileable_axis` and `tile_pitch_m`: `citibike_dock_unit` (0.90 m),
  `jersey_barrier` (3.05 m), `construction_fence` (2.438 m). A Citi Bike station of capacity *N* is *N* dock
  units end to end plus one `citibike_kiosk`.
* `subway_entrance` descends along **-Y** and its geometry goes 2.40 m below grade; the sidewalk mesh must have
  the opening cut out of it (the curb render shows how). Globes are separate assets chosen by the dataset's
  `has_globe` (0 none, 1 green, 2 red).
* `mta_line_bullets`: 23 nodes named `bullet_<line>`; the node translation is a display layout — zero it.
* Sign blanks are anchored at the **centre of the sign face**, not the ground. Bolt them to
  `post_u_channel_3m` / `_2m` or to a pole/mast at the height `roads/signs.parquet` gives.

### glTF LOD1 caveat for whoever writes the UE importer
`MSFT_lod` is wired the documented way: `LOD0` references `LOD1` through the extension and `LOD1` is removed
from the scene's root node list, so a viewer that ignores the extension sees only LOD0. **Blender's own glTF
importer instantiates unreferenced nodes anyway**, which silently doubles the geometry unless you filter it.
Every exported object carries a `nycsim_lod` extra (0 or 1) precisely so an importer can tell them apart;
`contact_sheets.import_prop()` shows the two-line filter.

### Kind enum
34 `dataset_kind` values are used. **16 already exist** in `pipeline/nycsim_pipeline/furniture/catalog.py`
(the furniture stage's §8 enum): `tree, hydrant, bus_shelter, linknyc, newsstand, bike_rack, citibike_dock,
subway_entrance, bench, waste_basket, mailbox, street_lamp, flagpole, manhole, subway_vent_grate, steam_vent`.

**18 are proposed additions to DATA_CONTRACTS §8** — this stage needed a kind name and there was none. They are
listed with descriptions in `blender_out/props/build_summary.json` under `extension_kinds` and in
`blender/props/build_props.py::EXTENSION_KINDS`:

`traffic_signal`, `pedestrian_signal`, `ped_pushbutton`, `road_sign`, `sign_post`, `street_name_sign`,
`standpipe`, `bollard`, `planter`, `tree_guard`, `tree_grate`, `trash_pile`, `food_cart`, `work_zone_device`,
`muni_meter`, `fire_alarm_box`, `fauna`, `mta_bullet`.

Note that `traffic_signal`, `pedestrian_signal`, `road_sign`, `sign_post` and `street_name_sign` are really the
**roads** stage's territory (DATA_CONTRACTS §7 `roads/signals.parquet` and `roads/signs.parquet` already carry
the per-instance data), so the cleanest resolution is for the roads stage to place them from §7 and for §8 to
gain only the street-furniture names. **The furniture stage owns that file; this stage did not edit it.**

### Rebuilding
```
python3 blender/props/census_dbh.py                       # refresh dbh_classes.json from the census
nice -n 10 python3 blender/props/build_props.py           # all 122 assets, ~90 s
nice -n 10 python3 blender/props/build_props.py --module p_vegetation --only tree_ginkgo_large
python3 blender/props/build_props.py --list               # registry without bpy
nice -n 10 python3 blender/props/contact_sheets.py --sheets --curb
python3 -m pytest tests/test_props.py -q
python3 blender/common/merge_catalog.py blender_out/props/catalog blender_out/props/props_asset_catalog.json
```

Texture resolution is tunable without code changes: `NYCSIM_PROPS_TEX_PX` (default 512) and
`NYCSIM_BARK_TEX_PX` (default 1024) set the pixel size the PBR maps are re-encoded to before embedding.

### Foundation code touched
None. `blender/common/nycsim_bpy.py`, `blender/common/textures.py` and `blender/common/texture_catalog.json`
were used as-is; the shared texture helper served every request (`build_summary.json` records
`"texture_source": "blender/common/textures.py"`). `pipeline/nycsim_pipeline/furniture/{catalog,allometry}.py`
were read, never written.

---

## 7. Licences of everything embedded

| asset | source | licence |
|---|---|---|
| Bark002, Bark003, Bark004, Bark005, Bark006, Bark007, Bark010, Bark012, Bark014 | ambientCG (Lennart Demes) | CC0 1.0 |
| Metal009, Metal027, Metal032, Metal038, Metal041B, PaintedMetal006 | ambientCG | CC0 1.0 |
| Concrete034, Concrete037, Asphalt033, Planks021 | ambientCG | CC0 1.0 |
| Overpass typeface (sign legends, cast lettering) | Delve Withrington / Red Hat, `assets/fonts/Overpass` | SIL OFL 1.1 |
| Every leaf atlas, impostor, sign legend, flag, ped-signal face, screen image | generated by `_legends.py` / `_leaves.py` in this repository | project-owned |

No texture, mesh or font was downloaded outside the existing `assets/` tree; each AmbientCG set already had its
`LICENSE.json` with a SHA-256 from wave 1, and the catalog entry for every prop repeats the asset id, licence,
source URL and hash of each set it embeds.
