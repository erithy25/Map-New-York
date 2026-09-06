# Landmarks, agent C — verification report

**Lane:** Hudson Yards, Billionaires' Row, Times Square, the midtown modernists, the museums and cultural buildings,
the stadiums and the outer-borough icons — 39 landmark ids, `blender/landmarks/c_*.py`,
`blender_out/landmarks/`, `docs/verification/landmarks/`, `tests/test_landmarks_c.py`.

**Shared module used:** `blender/landmarks/common.py` (agent A). Every C script builds with A's `MeshBuilder`,
`Fenestration`/`tower_tier`/`facade_grid`/`cornice`/`column`/`pediment`/`arched_opening`/`punched_wall` builders, its
documented `PALETTE` (which now resolves CC0 PBR maps through `blender/common/textures.py` itself), and its
`finish`/`render_check` verification path. `blender/landmarks/c_common.py` was rewritten from a self-contained
duplicate into a thin layer over that module and now contains **only** what is specific to lane C: the registry, a
working footprint reader, the `curtain` helper, the Times Square screen slots and thin `finish`/`render` wrappers.


## 1. What was built

### 1.1 Scripts (`blender/landmarks/`)

| file | what it exports |
|---|---|
| `c_common.py` | lane-C layer over agent A's `common.py`: the 39-entry `SCRIPTS` registry (BINs, published heights, the source of each height, per-part data for the three group scripts), a working footprint reader, `Group`, the `curtain` curtain-wall helper, `band_ring`, the `TSQ_SCREEN_<n>` slot machinery (`screen`, `screen_quad`, `assign_screen_uvs`), and `finish`/`render` wrappers |
| `c_renders.py` | the four canonical viewpoint renders, built by **importing the exported glbs** and placing them at their catalog `origin_tm` — nothing is re-modelled |
| 39 × `c_<id>.py` | one landmark or landmark group each; every one exports `blender_out/landmarks/<id>.glb` (LOD0 + `<id>_LOD1`) and `blender_out/landmarks/catalog/<id>.json` |

The three group scripts each export a single glb containing the whole group, with every building's published height,
BINs and height source recorded per part in the catalog entry's `dimensions.parts`:

* **`c_hudson_yards`** — 30 HY (387.1 m, with the **Edge** deck at 345.0 m cantilevering 20.0 m, glass floor and
  leaning parapet), 35 HY (308.0 m), 10 HY (272.8 m), 55 HY (237.4 m), 15 HY (278.6 m, square base morphing into the
  four-lobed pleated top), 50 HY (308.2 m), **The Shed** (the 36.6 m movable ETFE shell modelled deployed, on its two
  83.2 m rails, with the bogies and the shell as separate nodes so the engine can slide it) and the **Vessel**
  (all **154 flights** and **80 landings** as real stepped geometry, flaring 15.2 → 45.7 m over 46.0 m).
* **`c_billionaires_row`** — 432 Park (425.5 m, the 28.5 m square tube with **six 3.05 m square windows per facade
  per floor** and the **five double-height open mechanical voids** at floors 12/13, 30/31, 48/49, 66/67, 84/85 cut
  right through the tube), 111 West 57th (435.3 m, nine **feathered terracotta setbacks** stepping the plan depth
  24.0 → 11.0 m, over Steinway Hall's 16-storey limestone front), Central Park Tower (472.4 m with the **floor-30
  cantilever**, 8.5 m east from 91.0 m, its soffit and brackets modelled), One57 (306.1 m), 220 Central Park South
  (290.2 m), 53W53 (320.0 m with its diagonal exoskeleton), Trump Tower (202.0 m) and the Solow Building (210.0 m).
* **`c_times_square`** — One Times Square (roof 110.7 m, pole 141.0 m, the 3.66 m ball and its 43.0 m descent track),
  Two/Three/Four Times Square, TSX Broadway (with the Palace Theatre at its lifted 9.1 m level), the Paramount
  Building (four 7.6 m clock faces and the glass globe), the **27 red TKTS steps** and the Duffy memorial, Times
  Square Tower, the Bank of America Tower (365.8 m to the spire), the Marriott Marquis, the New York Times Building
  (318.8 m with the ceramic-rod screen) and the Port Authority Bus Terminal — plus **32 emissive `TSQ_SCREEN_<n>`
  slots**, each a quad with exact 0..1 UVs in the order bottom-left, bottom-right, top-right, top-left.

### 1.2 Outputs

* `blender_out/landmarks/<id>.glb` — 39 files, each containing the LOD0 meshes parented to a root empty plus the
  `<id>_LOD1` massing mesh (DATA_CONTRACTS §13 "extra meshes named `<id>_LOD1` inside the parent file").
* `blender_out/landmarks/catalog/<id>.json` — 39 catalog entries with every DATA_CONTRACTS §11 field
  (`id, name, bins[], lp_number, script, footprint_source, height_m, height_source, notes, fidelity_statement`)
  plus `origin_tm`, `heading_deg`, `tris_lod0`, `tris_lod1`, `lod1_ratio`, `footprint_iou`, `model_height_m`,
  `bounds_local_m`, `dimensions` (every published figure the script used), `material_slots` and `renders`.
  `blender/common/merge_catalog.py` merges these into `landmarks.json`.
* `docs/verification/landmarks/<id>_<view>.png` — two to four verification stills per landmark.
* `docs/verification/landmarks/canonical_*.png` — the four canonical viewpoints.
No other files are written: lane C's own 1 K texture cache was deleted when material handling moved onto agent A's
`common.mat`, which resolves textures straight out of `assets/textures/`.

## 2. How it was verified

Every check below is enforced in code, not by eye: `common.finish` raises `FidelityError` and the script exits
non-zero if any of them fails, so **an exported glb is by construction one that passed**.

| check | rule | where |
|---|---|---|
| real footprint | model section at z = 1.5 m over objects tagged `role="base"` vs the real OTI polygon, **IoU ≥ 0.90** | `common.footprint_iou` via `common.finish` |
| height | model bounding-box height within **1 %** of the published height in `c_common.SCRIPTS` | `common.finish` |
| LOD0 budget | ≤ 250 000 triangles (400 000 for `c_hudson_yards`, `c_guggenheim`, `c_high_line`) | `common.finish` |
| LOD1 | `<id>_LOD1` built from the base/mass volumes, ≤ 20 % of LOD0 | `common.make_lod1` |
| screens | every `TSQ_SCREEN_<n>` face carries exactly (0,0) (1,0) (1,1) (0,1) UVs | `c_common.assign_screen_uvs` + test |
| contract | catalog has every §11 field; glb has `<id>_LOD1` and `asset.extras.nycsim` | `tests/test_landmarks_c.py` |

### 2.1 Commands run

```
# one landmark (the pattern used for all 39; NYCSIM_RENDER_FAST=1 renders the iteration stills at 16 spp / 640x360)
NYCSIM_RENDER_FAST=1 nice -n 10 python3 blender/landmarks/<id>.py

# the four canonical viewpoints, 64 samples at 1280x720, built from the exported glbs
nice -n 10 python3 blender/landmarks/c_renders.py

# the test suite
python3 -m pytest tests/test_landmarks_c.py -q
```

### 2.2 Footprint sources actually read

* **76 BINs** in total across the 39 landmarks. 53 of them are in
  `data/processed/landmarks/candidate_footprints.parquet` (2,705 BIN-keyed rows); the other 23 come from
  `data/processed/buildings/footprints_raw.parquet`, read with **pyarrow column + row filters only**
  (`filters=[("bin", "in", [...])]`) — that 204 MB file is never loaded whole.
* One BIN in the brief's starting registry was wrong and was corrected against the data: 10 Hudson Yards was listed
  under BIN 1088961 (which is actually the Shops podium plus 30 Hudson Yards); its own footprint is **BIN 1089323**
  (4,127 m2, OTI LiDAR height 45.4 m from the 2015 flight, i.e. mid-construction), found by a bbox query on
  `footprints_raw.parquet` and cross-checked against the OSM outline named "10 Hudson Yards".
* `data/processed/osm/landuse_leisure.parquet` for the two landmarks with no building footprint:
  the High Line (relation `-7141751`) and Little Island (way `833335529`).

**A bug in agent A's `common.load_footprints`, reported here rather than patched (not my lane):** it reads
`data/processed/buildings/landmark_footprints.parquet` first and filters on a `bin` column, but that file is keyed
`landmark_id` / `bins` (a list) and has no `bin` column, so pyarrow raises
`ArrowInvalid: No match for FieldRef.Name(bin)` for **every** key, including agent A's own ids. Reproduce with
`python3 -c "import sys;sys.path.insert(0,'blender/landmarks');import common;common.load_footprint(1015862)"`.
Lane C therefore has its own `c_common.load_bins` and always passes `real_footprint=` explicitly to
`common.finish`; nothing in lane C depends on the broken path. The fix is a one-line special case for that file's
schema in `_read_rows`.

### 1.3 Every export

| id | name | published h (m) | model h (m) | IoU | LOD0 tris | LOD1 tris | LOD1 % | glb MB | BINs | renders |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `c_american_museum_natural_history` | American Museum of Natural History + Rose Center | 44.8 | 44.8 | 1.000 | 57606 | 4174 | 7.2 | 13.2 | 2 | 2 |
| `c_apollo_theater` | Apollo Theater | 20.0 | 19.9 | 1.000 | 7029 | 72 | 1.0 | 14.8 | 1 | 2 |
| `c_billionaires_row` | Billionaires' Row (West 57th Street corridor) | 472.4 | 472.4 | 1.000 | 220910 | 37774 | 17.1 | 36.6 | 9 | 2 |
| `c_bronx_county_courthouse` | Bronx County Courthouse (Mario Merola Building) | 58.5 | 58.5 | 1.000 | 11360 | 164 | 1.4 | 14.6 | 1 | 2 |
| `c_brooklyn_museum` | Brooklyn Museum | 50.0 | 50.0 | 1.000 | 22569 | 1520 | 6.7 | 15.2 | 1 | 2 |
| `c_brooklyn_public_library` | Brooklyn Public Library, Central Library | 29.3 | 29.3 | 1.000 | 8556 | 828 | 9.7 | 14.4 | 1 | 2 |
| `c_carnegie_hall` | Carnegie Hall | 55.2 | 55.2 | 1.000 | 19102 | 72 | 0.4 | 15.8 | 1 | 2 |
| `c_chelsea_market` | Chelsea Market (National Biscuit Company complex) | 37.7 | 37.7 | 1.000 | 40256 | 48 | 0.1 | 14.0 | 1 | 2 |
| `c_citi_field` | Citi Field | 39.0 | 39.0 | 1.000 | 8606 | 1532 | 17.8 | 20.3 | 1 | 2 |
| `c_citigroup_center` | Citigroup Center (601 Lexington Avenue) | 278.9 | 278.9 | 1.000 | 76574 | 288 | 0.4 | 20.1 | 1 | 2 |
| `c_domino_sugar_refinery` | Domino Sugar Refinery and Domino Park | 60.0 | 60.0 | 1.000 | 20932 | 2534 | 12.1 | 13.8 | 1 | 2 |
| `c_guggenheim` | Solomon R. Guggenheim Museum | 41.6 | 41.6 | 1.000 | 9352 | 308 | 3.3 | 7.1 | 2 | 2 |
| `c_hearst_tower` | Hearst Tower | 182.0 | 182.4 | 1.000 | 13790 | 204 | 1.5 | 9.2 | 1 | 2 |
| `c_hudson_yards` | Hudson Yards (Eastern Yard) | 387.1 | 387.1 | 0.921 | 103450 | 1026 | 1.0 | 21.4 | 7 | 4 |
| `c_javits_center` | Jacob K. Javits Convention Center | 53.6 | 53.6 | 1.000 | 2268 | 232 | 10.2 | 6.2 | 2 | 2 |
| `c_kings_theatre` | Kings Theatre (Loew's Kings) | 25.2 | 25.2 | 1.000 | 581 | 98 | 16.9 | 14.2 | 1 | 2 |
| `c_lever_house` | Lever House | 94.0 | 94.0 | 0.961 | 31044 | 104 | 0.3 | 7.0 | 1 | 2 |
| `c_lincoln_center` | Lincoln Center for the Performing Arts | 37.7 | 37.7 | 1.000 | 4145 | 156 | 3.8 | 14.1 | 3 | 2 |
| `c_lipstick_building` | Lipstick Building (885 Third Avenue) | 138.0 | 138.0 | 1.000 | 26780 | 1120 | 4.2 | 11.1 | 1 | 2 |
| `c_little_island` | Little Island (Pier 55) | 18.9 | 18.8 | 1.000 | 9350 | 1774 | 19.0 | 5.9 | 0 | 2 |
| `c_metlife_building` | MetLife Building (200 Park Avenue) | 246.3 | 246.3 | 1.000 | 105284 | 188 | 0.2 | 19.4 | 1 | 2 |
| `c_metropolitan_museum` | The Metropolitan Museum of Art | 42.0 | 42.0 | 1.000 | 84303 | 760 | 0.9 | 12.3 | 1 | 2 |
| `c_moynihan_train_hall` | Moynihan Train Hall (James A. Farley Building) | 31.2 | 31.2 | 1.000 | 29032 | 4110 | 14.2 | 15.5 | 1 | 2 |
| `c_riverside_church` | Riverside Church | 120.1 | 120.1 | 1.000 | 18746 | 3204 | 17.1 | 5.2 | 2 | 2 |
| `c_seagram_building` | Seagram Building | 157.0 | 158.1 | 1.000 | 34356 | 140 | 0.4 | 9.0 | 1 | 2 |
| `c_st_john_the_divine` | Cathedral Church of St. John the Divine | 71.0 | 70.7 | 1.000 | 4329 | 576 | 13.3 | 6.6 | 1 | 2 |
| `c_the_dakota` | The Dakota | 50.9 | 50.9 | 1.000 | 20708 | 1642 | 7.9 | 18.8 | 1 | 2 |
| `c_the_plaza` | The Plaza Hotel | 76.2 | 76.2 | 1.000 | 26425 | 4094 | 15.5 | 16.7 | 1 | 2 |
| `c_times_square` | Times Square | 365.8 | 365.8 | 0.999 | 182310 | 3562 | 1.9 | 32.1 | 13 | 2 |
| `c_un_headquarters` | United Nations Headquarters | 154.0 | 154.0 | 1.000 | 12338 | 706 | 5.7 | 15.5 | 3 | 2 |
| `c_usta_arthur_ashe` | Arthur Ashe Stadium | 46.0 | 46.0 | 1.000 | 2452 | 316 | 12.9 | 13.0 | 1 | 2 |
| `c_whitehall_and_st_george_ferry_terminals` | Whitehall, Battery Maritime and St. George ferry terminals | 27.7 | 27.7 | 1.000 | 77605 | 3774 | 4.9 | 14.3 | 3 | 2 |
| `c_williamsburgh_savings_bank_tower` | Williamsburgh Savings Bank Tower (One Hanson Place) | 156.0 | 156.0 | 1.000 | 40902 | 888 | 2.2 | 18.6 | 1 | 2 |
| `c_yankee_stadium` | Yankee Stadium | 42.0 | 42.0 | 1.000 | 10196 | 1742 | 17.1 | 13.6 | 1 | 2 |
## 3. What looking at the renders changed

Every landmark was rendered and inspected; the renders below are the ones that were wrong the first time and what
was changed. This is the "iterate until the proportions read correctly" pass the brief asks for.

| render | what it showed | fix |
|---|---|---|
| `c_hudson_yards_vessel` | the Vessel was a tangle of flights all winding the same way — no honeycomb, no basket | rebuilt as a diagrid of staircases: 8 landings per level, flights from landing (j,k) to (j±1,k+1) so they cross, giving the real triangular-opening honeycomb; 128 crossing flights + 26 entry flights = the published 154, asserted in the build |
| `c_hudson_yards_shed` | the movable shell was a thin barrel vault | the real shell is a rectangular ETFE-clad crate: rebuilt as six box portal frames with a 2.2 m cambered roof, longitudinal ties, cushion panels and eight double-wheel bogies on the rails |
| `c_un_headquarters_aerial` | the General Assembly's concave walls were inverted — low at the ends, high in the middle | corrected to 34.0 m at both ends sweeping down to a 16.0 m waist, with the 23 m dome over the waist and the north glass wall full height |
| `c_american_museum_natural_history_aerial` | the Rose Center's glass cube and Hayden Sphere were invisible — buried inside the north range's solid mass; a corner turret floated off the building | the cube is now cut out of the north range as a real void; turrets moved from bounding-box corners to actual polygon vertices |
| `c_citi_field_rotunda` | the seating bowl's outer ring overhung the exterior wall as a huge dark cantilevered plane | every bowl ring is now clipped to the real footprint (`bowl_ring`), in both stadiums |
| `c_lipstick_building_third_ave` | punched windows instead of ribbon glazing, and the polished red granite read grey | switched the tiers to `cc.curtain` (continuous ribbon glass between deep spandrel bands) and declared the real red Imperial granite albedo with `common.custom_material`, because the CC0 granite scan is grey |
| `c_the_plaza_aerial` | the copper mansard read as a shallow wedge with an oversized flat deck | steeper mansard, deck inset from −9.5 m to −23 m, roof deck material corrected |
| `c_seagram_building_aerial` (first pass) | the bronze I-beams and the plaza pools read, but the whole building was grey | material handling moved off lane C's own texture path onto agent A's `common.mat`, which tints the CC0 colour map back to the documented palette albedo |
| ~19 street views | far too close — the camera stood inside the colonnade of the Met, under the Apollo's marquee, between the Hudson Yards towers | distances recomputed from each model's real size (and the very large models now use `render_check`'s own `2.2 × radius + 45` default) |
| `c_apollo_theater`, `c_the_plaza` (height failures) | `common.finish` rejected both: 21.15 m vs 20.0 m and 77.8 m vs 76.2 m | `common.column`'s `h` argument is the column's own height, not its top z (the Apollo's giant order overshot by 1.15 m); the Plaza's turret finials were lowered so the ridge is the highest point |

## 4. Fidelity achieved against the brief

| brief requirement | status |
|---|---|
| real footprint base, IoU > 0.9 | met for all 39 (see the table; the lowest is `c_hudson_yards`, whose Vessel footprint is the roof projection of a structure that is only ~15 m across at z = 1.5 m, so the group loses ~4 points of IoU there — stated in that script) |
| docstring citing each dimension | met; enforced by `test_script_docstring_cites_sources_and_states_gaps`, which requires ≥ 3 bracketed citations and an explicit "NOT modelled" statement in every script |
| `<id>_LOD1` at ≤ 20 % of the triangles | met for all 39 |
| 250 k triangles (400 k for the Vessel, Guggenheim and High Line) | met for all 39 |
| materials from `blender/common/textures.py` | met, through agent A's `common.mat`, which resolves the CC0 AmbientCG/Poly Haven sets for masonry, paving and metal palette names and tints the colour map back to the documented albedo. Two colours the CC0 catalogue cannot supply (the Lipstick Building's polished red Imperial granite) are declared with `common.custom_material` and documented in the script |
| Times Square screens as emissive `TSQ_SCREEN_<n>` with 0..1 UVs | met: 32 slots, each an emissive material on a quad whose four UVs are exactly (0,0) (1,0) (1,1) (0,1); enforced by `test_times_square_screen_slots_are_emissive_with_0_1_uvs`, which reads the UV accessor out of the glb binary chunk |
| the Vessel's 154 flights | met: 154 flights and 80 landings are built as stepped geometry and asserted in the build (`assert flights == 154 and landings == 80`) and in the tests |
| 432 Park's six-by-six grid and mechanical voids at the real floors | met: six 3.05 m windows and seven 1.46 m piers per facade sum to exactly 28.5 m, and floors 12/13, 30/31, 48/49, 66/67, 84/85 are open through the tube |
| Central Park Tower's floor-30 cantilever | met: 8.5 m east from 91.0 m, with the exposed soffit and six brackets |
| The Shed's movable shell on rails | met: the shell is its own node, `c_hudson_yards_shed_shell`, with two 83.2 m rails and eight double-wheel bogies; the catalog documents the translation that retracts it |
| the High Line as 2.3 km of viaduct | met from OSM (see §2.2 and §5) |
| render from the canonical viewpoints and iterate | met; §3 lists what each pass changed |

## 5. Gaps, with reasons

1. **`c_usta_arthur_ashe` height is inferred.** The OTI LiDAR height for Arthur Ashe Stadium (17.7 m) pre-dates the
   2016 retractable roof, and no architectural height is published. The model uses 46.0 m scaled from Rossetti's
   published section, flagged in the catalog as
   `"top_m_source": "inferred from published section, +-2 m"`. Everything else about that stadium (the eight roof
   columns, the 62 x 62 m opening, the court) is from published figures.
2. **`c_ts_two_times_square` height is the LiDAR roof.** Two Times Square has no published architectural height;
   160.6 m (which includes its sign tower) is used and flagged inferred in the docstring and the fidelity statement.
3. **The New York Times Building's ceramic rods are built at every fifth rod.** The real screen is 186,000 rods on
   127 mm centres; at ~12 triangles each that is ~2.2 M triangles for one facade, five times the whole group's
   budget. The model uses 0.60 m centres (one rod in five) and says so in the catalog `dimensions`
   (`nyt_rod_spacing_m` 0.127 vs `nyt_rod_modelled_spacing_m` 0.60).
4. **The Javits Center's space frame is built on the 90 ft structural grid, not the 5 ft module.** The real frame has
   roughly 76,000 members; one diagonal per 90 ft bay reproduces the reading at 1/300 of the cost. Stated in the
   docstring and the fidelity statement.
5. **Two shared footprint polygons had to be divided.** BIN 1088961 covers the Shops at Hudson Yards *and* 30 Hudson
   Yards, and BIN 1089411 covers 15 Hudson Yards *and* The Shed; BIN 1023728 covers 111 West 57th *and* Steinway
   Hall. Each division is cut at a vertex that already exists in the polygon, and each is named as an inference in
   the script and the catalog.
6. **`c_hudson_yards` IoU is the lowest in the lane.** The Vessel's OTI polygon is the roof projection of a structure
   that is only ~15 m across at the 1.5 m slice height, so the group's section is genuinely smaller than the summed
   footprints there. Building a 46 m-wide solid at ground level to raise the number would be a lie; the loss is
   accepted and stated.
7. **Sculpture is modelled as blocked-out mass, never as figures.** The Bronx County Courthouse's four sculpture
   groups, the Brooklyn Museum's 30 allegorical figures, the AMNH equestrian statue and the Brooklyn Public
   Library's fifteen bronze figures are plinths and blocks. This is deliberate: inventing figure geometry would be
   worse than the honest gap, and figure sculpture is the props/character stage's competence, not this one.
8. **No interiors anywhere.** Every script says so. The one exception is that volumes visible from outside through
   glass (the Shed's fixed building, the Rose Center's sphere, the Palace Theatre inside TSX Broadway, Little
   Island's Amph) are modelled because they read from the street.
9. **`c_whitehall_and_st_george_ferry_terminals` spans 6 km.** The two ends of the Staten Island Ferry are one glb
   whose origin is the Whitehall Terminal, so St. George sits ~5.9 km away in the model's local frame. This is
   correct but unusual; the engine should either accept the large bounding box or split the node.
10. **Agent A's `common.py` is a live dependency.** It changed twice during this run (the `MeshBuilder.box_from_to`
    signature lost a parameter, and `mat()` gained texture resolution). Lane C tracked both. If it changes again,
    re-run the 39 scripts; each takes 10-40 s to build plus its renders.

## 6. What the next agent needs to know

* **Placement.** Every glb's axes are already parallel to NYC_TM (x east, y north, z up before the glTF Y-up
  conversion) and its origin is at ground level; `extras.nycsim.origin_tm` is the NYC_TM position of that origin.
  There is **no rotation to apply on import** — set the node's world translation to `origin_tm` and you are done.
  `heading_deg` is recorded for reference (it is the compass heading of the *build* frame's +x axis, before
  `common.finish` rotated the meshes back).
* **LOD.** Each file carries `<id>_LOD1`, a joined and decimated copy of the base/mass volumes, at ≤ 20 % of LOD0.
  It is a sibling mesh in the same file, so hide it at LOD0 range and swap at distance; it is not parented under the
  root empty (`common.finish` parents only the LOD0 meshes), so a naive "show everything" import will show both.
* **Times Square video.** `TSQ_SCREEN_1` … `TSQ_SCREEN_32` are emissive materials on single quads with exact 0..1
  UVs. Bind one video texture per slot to the emissive channel; the base colour is a neutral grey so an unbound
  slot reads as a dark screen rather than a hole. The catalog's `material_slots` names every slot.
* **The Shed's shell moves.** `c_hudson_yards_shed_shell` is its own node with `nycsim_role = "shell"`. Translating
  it by −83.2 m along the model's local +x (which in the exported file is the direction from the fixed building
  towards the plaza) retracts it over the fixed building. Its bogies and the two rails are in
  `c_hudson_yards_shed_rails`.
* **Roles.** Objects carry `nycsim_role` in their glTF node extras: `base` (the volume the IoU check slices),
  `mass` (LOD1 massing), and lane-C additions `plaza`, `park`, `pier`, `field`, `roof`, `shell`, `theatre`,
  `detail`, `pots`. Plazas, parks, piers and fields lie **outside** the building footprint and can be dropped if the
  terrain/roads stages own that ground.
* **Overlap with other stages.** The buildings-mesh stage must **not** also emit generic buildings for the 75 BINs
  listed in `c_common.SCRIPTS` (the ids and BINs are in each catalog entry's `bins`), or landmarks will z-fight with
  their generic replacements. The High Line and Little Island have no BIN; suppress them by OSM id
  (`-7141751`, `833335529`) instead.
* **Ground.** Local z = 0 is the mean LiDAR `ground_z` of the landmark's footprints (in `origin_tm[2]`). Where a
  group spans different ground levels (Hudson Yards, the UN, Lincoln Center) the individual buildings are offset
  from that mean, so the terrain stage should not re-level them.

## 7. Licences

Nothing was downloaded for this lane. The only external assets used are the CC0 1.0 PBR texture sets that
`blender/common/textures.py` had already fetched into `assets/textures/` (AmbientCG and Poly Haven, each with a
`LICENSE.json` recording url, licence, author and sha256). The footprints come from the NYC Building Footprints
dataset (NYC Open Data `5zhs-2jue`, public domain) already in `data/processed/`, and the two OSM outlines from
`data/processed/osm/landuse_leisure.parquet` (OpenStreetMap contributors, ODbL) — already recorded by the OSM
ingest stage's manifest entry.
