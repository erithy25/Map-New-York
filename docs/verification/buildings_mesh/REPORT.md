# Stage report — building shells (`blender/buildings/`)

Agent: Blender building shell. Date: 2026-09-06. Blender 4.5.13 LTS (`bpy`, CPU only), Python 3.11.15.

This stage turns every one of the 1,083,026 real NYC footprints into a closed, watertight `.glb`
building shell with the real footprint ring, the real `ground_z`/`roof_z`, the real roof shape where
the data says there is one, metre UVs for the facade shader, an LOD chain and per-building vertex
attributes. It implements ARCHITECTURE §4.3 and the shell half of ADR-003.

---

## 1. What was built

| File | Purpose |
|---|---|
| `blender/buildings/shellgeom.py` | Pure-geometry layer (no `bpy`): footprint cleaning, wall/roof/cap emission, roof-shape decomposition, LOD simplification, watertightness checks. |
| `blender/buildings/tiledata.py` | Reads `data/processed/tiles/{tile}/buildings.parquet`, resolves roof type, pitch, material and attributes through documented precedence chains, emits `BuildingSpec`s in tile-local metres. |
| `blender/buildings/build_tile.py` | CLI: `--tile t_-4_5`, `--tiles`, `--tile-list`, `--all`, `--workers N` (max 2), `--lod 0,1,2`, `--attrs full\|min`, `--ridge-mode clamp\|adr013`, `--skip-existing`. Assembles the Blender meshes and exports `tile_buildings.glb` + `manifest.json`. |
| `blender/buildings/build_lod_merged.py` | L2 (4 km cells) and L3 (16 km cells, buildings >= 40 m) merged skyline meshes. |
| `blender/buildings/render_verify.py` | Cycles CPU verification renders; re-imports the exported `.glb` so the renders show the shipped file, not a rebuild. |
| `blender/buildings/summary.py` | Aggregates the per-tile manifests and extrapolates the whole-city cost. |
| `blender/buildings/run_all.sh` | Full-city run with the measured cost in its header. |
| `tests/test_building_shells.py` | 148 tests (see §6). |

Outputs: `blender_out/tiles/{tile}/tile_buildings.glb` + `manifest.json`,
`blender_out/tiles/_merged/l{2,3}/L{2,3}_{px}_{py}.glb` + `.manifest.json`,
`docs/verification/buildings_mesh/{summary.json, renders.json, *.png}`.

---

## 2. Geometry: how a shell is built

**Footprint cleaning** (`shellgeom.clean_footprints`, vectorised shapely 2): `force_2d` ->
validity repair -> `set_precision(0.02)` snap-rounding (the 2 cm snap) -> Douglas-Peucker at 0.02 m
(removes collinear runs without moving any vertex more than the snap tolerance) -> parts < 1 m2 and
interior rings < 0.5 m2 dropped -> `orient` so the exterior is CCW and holes CW. Interior rings are
kept as holes and become real courtyard walls. 0 of 66,559 footprints in the verified subset were
dropped.

**Walls** are extruded from `ground_z` to the wall-top height out of the cleaned ring. Every solid
spans exactly `[ground_z, roof_z]`: for a flat roof `roof_z` is the top of the parapet and the deck
sits 0.60 m below it; for a pitched roof `roof_z` is the ridge and the eave is below it. That is the
behaviour the orchestrator asked for — the measured `z_roof_max` is the ridge, so the overall height
stays the measured one (`--ridge-mode clamp`, the default). `--ridge-mode adr013` instead honours
`roof_ridge_dz_m` from `roof_attrs.parquet` literally, which puts the ridge above the LiDAR plane
and makes the mesh taller than the `height` column; it is available but not used.

**Roofs.** `roof_type` is consumed from the tile column when present (it now is, for all 1,083,026
rows) and the roof is generated as a continuous planar height field clipped to the real footprint:

* `flat` — deck at `roof_z - 0.60 m`, 0.30 m parapet ring, coping band, closed deck. The parapet is
  only generated for buildings with >= 2 floors, >= 6 m height and >= 40 m2 footprint, because a
  parapet on a detached garage is wrong.
* `gable` — two planes meeting on the OBB long axis; the wall top follows the roof, so the gable
  ends are real triangular walls rather than a separate object.
* `hip` — four planes falling away from the ridge segment (`z = z_top - k*max(|v|, |u|-(a-b), 0)`).
* `mansard` — flat deck over the inner 35 % of the short half-axis plus four steep slopes.
* `shed` — one plane across the short axis.
* `sawtooth` — north-light teeth: a long monitor slope plus a short 8 %-of-period glazing face
  (modelled at about 80 degrees rather than exactly vertical so the roof stays a continuous height
  field, which is what the wall/cap stitching relies on).
* `barrel` — 8 planar bands across the short axis.
* `dome` — generated as a four-sided faceted pyramid. True domes belong to the hand-scripted
  landmarks of ARCHITECTURE §4.6; this is stated as an approximation, not presented as real.
* `complex` — treated as flat + parapet, because `tiles/{tile}/roofs.glb` (the `roof_mesh_ref`
  target of DATA_CONTRACTS §5) does not exist. 28 buildings city-wide.

The roof pitch uses the measured `roof_ridge_dz_m - roof_eave_dz_m` from `roof_attrs.parquet` when
available (median rise 2.05 m on the Bayside tile), else `roof_pitch_deg`, else a class default.

**Stepped massing** (`blender/buildings/roofsteps.py`, `shellgeom._build_stepped`). A setback tower
is not a slab, and 307,735 buildings — 28 % of the city — carry more than one roof level. The level
*outline* is recovered from the CityGML LOD2 triangle soup rather than guessed: every `tri_type == 2`
roof triangle is exactly horizontal (verified: `1 - |n_z|` is 0.0 over a 400-row sample), so grouping
the roof triangles by z within 0.15 m and unioning each group **is** the outline of that level. The
levels are then made disjoint in plan — about one Midtown building in five has an overhang, and seen
from above the taller surface is the one that is there — and checked against the publishing stage:
their union must reproduce `footprint_area_m2` within 2 %, which it does for 100 % of candidates
(the union of the *ground* surfaces reproduces the same column just as exactly, so the roof levels
really do cover the plan). The real 2026 OTI footprint is then cut into one region per level, the
whole profile is shifted so its top lands on the contract `roof_z`, and `shellgeom` builds one flat
cap per region plus a vertical step face on every shared boundary. Nothing is inferred: a building
whose recovered levels disagree with the published areas, whose plan does not match its footprint,
or whose height cannot be reconciled, keeps its single-height shell and is counted as such.

**Shell materials** (`blender/buildings/shellmat.py`). One analytic PBR set per material class —
base colour, roughness, metallic, specular level and IOR — exported as `KHR_materials_specular` and
`KHR_materials_ior`, so a curtain wall ships as a dark, low-roughness, part-metallic surface whose
brightness comes from what it reflects rather than as a pale flat colour. Per-building variation is
a shader expression over the `_LIT_SEED_HI` / `_LIT_SEED_LO` attributes the shells already carry
(`shellmat.variation`), which costs no bytes and no draw calls; `render_verify.py` evaluates it as
Cycles nodes so the verification renders show what an engine implementing the same expression will
show. These are shading choices, not measurements — no reflectance was measured for any NYC
building, and which class a building is in is governed by ADR-004 and its `MATERIAL_REAL` bit.

**Closure.** Every building is a closed solid: outer walls, courtyard walls, roof surface, parapet
coping and inner face, and a floor slab at `ground_z`. Vertices are welded per building on a 1 mm
grid; the roof regions are snapped to the same grid before use (`shapely.set_precision`), which is
what makes the roof and the wall strips share vertices exactly. A ridge point reached from two
different plane equations can still straddle a grid cell by one ULP, so `TriBuf.vid` falls back to a
26-neighbour probe — used only for the ~0.5 % of buildings whose fast-path build does not close, so
the common path keeps its speed. After that, `build_shell` verifies edge-manifoldness and, if a
pathological footprint still fails, rebuilds the same real footprint and height as a flat-capped
extrusion. In the 66,559-building subset that fallback fired 28 times (0.04 %) and the
massing fallback 11 times; **0 open shells were exported.**

**Wall UVs** are in metres. `u` is arc length along the facade, with `u = 0` at the start of the
edge whose outward normal best matches `primary_facade_heading`, so the window grid phase is stable
between LODs and between runs. `v` is height above the building's own `ground_z` on every vertical
surface, including the inner parapet face. **glTF stores V with a top-left origin, so a
glTF/Unreal consumer reads the height as `1 - V`, not `V`.** Horizontal faces (floor slab, parapet
coping, roof deck) carry planar XY metre UVs instead; branch on the face normal.

---

## 3. Attributes and how the Unreal importer reads them

Blender exports a mesh attribute whose name starts with `_` as a glTF custom vertex attribute with
the name upper-cased, always `componentType 5126` (FLOAT), `type SCALAR` (verified by reading the
exported files back with `pygltflib`).

| glTF attribute | LOD0 | LOD1 | LOD2 | meaning |
|---|:-:|:-:|:-:|---|
| `_BIN` | yes | yes | yes | Building Identification Number. Exact: every NYC BIN < 5,799,524 < 2^24, so float32 is lossless. |
| `_FACADE_CLASS` | yes | | | `facade_classes.json` id; `0` = not classified yet -> use the material fallback. |
| `_FLOORS` | yes | yes | | PLUTO `numfloors` or inferred. |
| `_FLOOR_HEIGHT` | yes | yes | | metres. |
| `_GROUND_FLOOR_HEIGHT` | yes | yes | | metres. |
| `_IS_STOREFRONT` | yes | | | 0/1. |
| `_LIT_SEED_HI`, `_LIT_SEED_LO` | yes | yes | yes | `lit_seed = _LIT_SEED_HI * 65536 + _LIT_SEED_LO`. |

`lit_seed` is a uint32 (max 4,294,963,886) and does **not** fit a float32 exactly, and Blender's
exporter converts every attribute to float32; splitting it into two exact 16-bit halves is the only
lossless path through glTF. This is a deviation from the literal wording of the brief
(`lit_seed` as one attribute) and it round-trips exactly —
`tests/test_building_shells.py::test_attribute_round_trip` asserts equality against the parquet for
a 60-building sample.

In UE 5.4 the Interchange glTF pipeline keeps unknown vertex attributes when
*Interchange -> glTF -> Import Vertex Attributes* is enabled; they arrive as float vertex streams
named exactly as above. LODs are carried both by the mesh/node name (`{tile}_{material}`,
`..._LOD1`, `..._LOD2`) and by each node's `extras = {tile, lod, material, material_index, origin_m}`.
The file-level metadata is on `asset.extras.nycsim` per DATA_CONTRACTS §13 (tile, `origin_m`, CRS,
vertical datum, LOD list, attribute list, attribute notes, git commit, schema version). Blender's
exporter can only put scene custom properties on the scene node and JSON-encodes them as a string,
so `build_tile.stamp_asset_extras` rewrites the GLB JSON chunk after export to satisfy §13.

Meshes are one per (LOD, material class), so the draw calls per tile are bounded by the materials
actually used (7-14 in the verified tiles), not by the building count. Wall triangles carry the
building's `material_primary`; roof decks carry `roof_membrane` (flat) or `tar_roof` (pitched, i.e.
asphalt shingle / rolled roofing) so the roof is not shaded as brick.

---

## 4. Measured results

### 4.1 The five representative tiles

| tile | buildings | LOD0 tris | LOD1 | LOD2 | LOD1/LOD2 ratio | glb | bytes/building | seconds | open shells |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `t_-4_5` Midtown (Empire State Building) | 852 | 38,554 | 16,452 | 12,324 | 0.43 / 0.32 | 4.37 MB | 5,127 | 18.9 | 0 |
| `t_-6_0` Lower Manhattan (Wall Street) | 199 | 14,520 | 5,348 | 3,276 | 0.37 / 0.23 | 1.49 MB | 7,492 | 2.2 | 0 |
| `t_-3_-4` Park Slope brownstones | 2,893 | 158,592 | 57,404 | 45,924 | 0.36 / 0.29 | 16.42 MB | 5,674 | 54.2 | 0 |
| `t_14_6` Bayside one/two-family | 1,888 | 45,786 | 28,476 | 26,956 | 0.62 / 0.59 | 6.64 MB | 3,515 | 42.6 | 0 |
| `t_2_14` Bronx Grand Concourse | 716 | 62,618 | 26,756 | 12,816 | 0.43 / 0.20 | 6.15 MB | 8,584 | 8.9 | 0 |

Seconds are wall clock on a 4 vCPU container shared with seven other agents (load average 20-26
throughout), so they are pessimistic by roughly 2x.

### 4.2 The verified subset (76 tiles)

76 tiles covering Lower and Midtown Manhattan, Brooklyn Heights, Downtown Brooklyn and Park Slope
(`tx` in [-8, -1], `ty` in [-4, 7]) plus the Bayside and Grand Concourse tiles — chosen because they
also supply the merged L2 cells the skyline render needs.

* buildings **66,559** (6.15 % of the city), rows in 66,559, dropped 0
* triangles **3,150,252** LOD0 / **1,342,800** LOD1 / **981,086** LOD2 -> LOD1 **42.6 %**, LOD2 **31.1 %**
* vertices 2,156,947 / 1,206,280 / 935,492 (welded, before the exporter's UV split)
* bytes **350,528,652** -> **5,266 B/building**
* open shells at LOD0: **0**; flat-cap fallbacks 28; massing fallbacks 11; LOD1 shipped as massing
  for 2,849 buildings (see §7)
* roof type source: **column** (the tile `roof_type`) for 100 % of rows; material source: **column**
  (`material_primary`) for 100 % of rows — the facade/CityGML stage's columns landed during this
  run, so nothing in the shipped subset uses this stage's own fallback rules
* generation time 972.9 worker-seconds total (geometry 767.9 s, parquet load 86.5 s, Blender mesh
  assembly 42.7 s, glTF export 71.9 s)

> **Note on `summary.json`.** The figures in §4.2 are the frozen measurement of the 76-tile,
> LOD0+LOD1+LOD2 subset this stage built and verified. `summary.json` is regenerated by whoever
> runs `blender/buildings/summary.py`, so it reflects whatever is on disk at that moment — the
> orchestrator's whole-city run (`--all --workers 2 --lod 0,1`) overwrites it as it progresses.
> With LOD2 omitted the measured cost drops to about 4,089 B/building (about 4.4 GB for the city),
> which is the number to use for a `--lod 0,1` build.

### 4.3 Merged L2 / L3

`blender_out/tiles/_merged/` — 8 L2 cells (4 km) and 3 L3 cells (16 km, buildings >= 40 m only),
70,572 emitted solids, 1,051,466 triangles, 55.9 MB, 277 s. `L3_-1_0` alone carries the
**3,690 Manhattan buildings >= 40 m** that make the skyline complete from Brooklyn Heights, the
Staten Island Ferry and the George Washington Bridge; `L2_-1_-1` (Downtown Brooklyn / Park Slope) is
the largest at 27,375 buildings / 400,430 triangles / 22.2 MB.

### 4.4 Whole-city cost (extrapolated from the measurements above)

| | measured | projected for 1,083,026 buildings / 920 tiles |
|---|---|---|
| triangles LOD0 | 47.33 per building | **51.3 M** |
| storage (LOD0+LOD1+LOD2, full attributes) | 5,266 B/building | **5.70 GB** |
| storage (LOD0 only) | about 2,900 B/building | about 3.2 GB |
| compute | 0.01462 worker-seconds per building | **4.4 worker-hours**, about **2.2 h wall clock with 2 workers** |
| merged L2 + L3 | — | about +12 min, about +0.8 GB |

**The full city was not run here, and the reason is disk, not time.** 2.2 h of wall clock fits the
3-hour budget, but the container had **6.4 GB free** when the subset finished (down from 12 GB at
the start of this session — seven other agents are writing concurrently) and the full run needs
5.7 GB. Filling the disk would break the other stages. `blender/buildings/run_all.sh` performs the
run, checks free space before starting, warns below 8 GB, is resumable (`--skip-existing`) and
prints the same summary; `LODS=0 bash blender/buildings/run_all.sh` produces the 3.2 GB variant.

---

## 5. Verification renders (Cycles CPU, ADR-012)

Every render imports the exported `.glb` back into Blender — what is shown is the shipped file, not
a rebuild. LOD1/LOD2 objects are hidden, the flat shell materials are swapped for the real
AmbientCG CC0 PBR sets by material name via `blender/common/textures.py` (19 of 20 material names
resolve; `glass_curtain` is procedural in the catalogue and renders as flat colour), and a ground
surface is interpolated from the buildings' own LiDAR `ground_z` values (inverse-distance over the
6 nearest footprint centroids on a 12 m grid) so that a building sitting proud of or sunk into grade
shows up immediately. 1280 x 720, 24 samples, OIDN denoised, AgX view transform.

| render | what it shows |
|---|---|
| `docs/verification/buildings_mesh/midtown_aerial.png` | Oblique aerial over `t_-4_5` and neighbours from 640 m. |
| `docs/verification/buildings_mesh/midtown_avenue.png` | Sixth Avenue looking north from West 33rd Street, eye height 1.7 m above real grade. |
| `docs/verification/buildings_mesh/park_slope_block.png` | Park Slope brownstone rows, Carroll Street towards Eighth Avenue, low oblique from 26 m. |
| `docs/verification/buildings_mesh/queens_houses.png` | Bayside one/two-family houses, low oblique from 48 m — the roof-shape check. |
| `docs/verification/buildings_mesh/skyline_brooklyn.png` | Lower Manhattan from the Brooklyn Heights Promenade, built from the merged **L2** cells, over a flat water plane at 0.0 m NAVD88. |
| `docs/verification/buildings_mesh/midtown_setbacks.png` | A setback tower and its neighbours from 240 m, the frame the stepped massing exists for. |

Three of those have a matched **before** frame, rendered from the same camera with the same
materials so the pair isolates one change each:

| pair | what differs | what to look at |
|---|---|---|
| `midtown_setbacks.png` vs `midtown_setbacks_no_steps.png` | stepped massing only (identical materials) | the ziggurat profile: five plateaus against the sky where the "before" is one flat top |
| `midtown_aerial.png` vs `midtown_aerial_no_steps.png` | stepped massing only | roof lines across the whole frame, not just one tower |
| `skyline_brooklyn.png` vs `skyline_brooklyn_before_materials.png` | shell materials only (the merged L2 cells are LOD2 massing, which carries no steps either way) | the towers going from pale flat solids to dark glass with sky in them |

Camera positions, targets, sample counts, source files and render times are in `renders.json`.

### What the renders showed, and what was fixed because of them

The renders were looked at and four real defects were found and fixed before this report:

1. **Cameras underground.** The first street-level renders were solid black or looking at the
   underside of the terrain: the camera z had been written as a height above ground while the world
   is in absolute NAVD88 metres, and Midtown grade is 14-16 m. Fixed by resolving `cam_agl` against
   the nearest real building `ground_z` at render time (`_ground_z_at`).
2. **Cameras inside buildings.** "Sixth Avenue and 33rd Street" typed from latitude/longitude lands
   inside BIN 1083630. Fixed with `_open_point`, which samples a grid and takes the point of maximum
   clearance from any real footprint (STRtree) — i.e. the roadway.
3. **Street-level views in Queens and Park Slope framed rear yards and garages, not roofs.** The
   most-open point in a low-density residential block is the back lot, not the street. Those two
   views were changed to low obliques (48 m and 26 m), which is what actually verifies roof shape.
4. **Overexposure.** Factory colour management blew out the light masonry. Fixed with AgX plus
   -0.6 EV and a sun at 2.6 rather than 3.5.

### What the renders confirm

* Buildings sit on grade — no floating, no sinking — in all five views, including the sloping
  Park Slope and Bayside blocks.
* Normals are outward: sunlit faces are lit, shadowed faces are shadowed, no black or inside-out
  facets anywhere; the signed volume of every sampled building is positive.
* Roofs are closed and correct. `queens_houses.png` shows gable, hip and shed roofs on the
  one/two-family stock next to flat roofs with a raised coping and a recessed grey deck on the
  apartment buildings — exactly the roof mix the `roof_type` column carries for that tile
  (861 gable, 459 shed, 414 flat, 154 hip).
* `park_slope_block.png` shows continuous rowhouse blocks with party walls, real rear extensions,
  and parapets standing above recessed roof membranes — the parapet geometry reads correctly from
  above.
* Heights are right: the Empire State Building is the tall slab in `midtown_aerial.png` at its real
  377.6 m; the skyline silhouette from Brooklyn Heights has the correct Lower Manhattan cluster with
  One World Trade Center (429.3 m in the source data) as its tallest element.
* Wall textures are at real metre scale (the brick courses in `park_slope_block.png` and
  `midtown_avenue.png` are the right size), confirming the metre UVs end to end through the `.glb`.

---

## 6. Tests

`python3 -m pytest tests/test_building_shells.py -q` -> **149 passed** (16.9 s), run against the
shipped `blender_out/tiles/t_-4_5/tile_buildings.glb`.

* `test_glb_loads_and_has_lod_chain` — loads with `pygltflib`; LOD0/LOD1/LOD2 all present; mesh
  names prefixed by the tile; `asset.extras.nycsim` carries tile, CRS, origin, schema version, LODs.
* `test_lod_triangle_budget` — LOD2 < LOD1 < LOD0 and LOD2/LOD0 < 0.45, for whichever LODs the
  file carries.
* `test_full_lod_chain_when_built_with_defaults` — builds `t_-6_0` fresh with the default
  `--lod 0,1,2` and asserts all three meshes are present. The chain assertion on the *shipped* tile
  is manifest-driven rather than hard-coded, because `--lod 0,1` is a legitimate configuration (the
  whole-city run uses it to halve the bytes) and a tile built that way must not fail the suite.
* `test_attributes_present` — all eight LOD0 attributes plus `TEXCOORD_0` on every LOD0 primitive.
* `test_every_source_building_is_present` — all 852 source BINs are in the glb.
* `test_buildings_are_watertight_solids` — 60-building sample, edge-manifold with positive signed
  volume, welding across all material meshes of the building.
* `test_footprint_iou_above_098` — the floor slab recovered from the mesh versus the cleaned source
  polygon, worst-case IoU over the sample must exceed 0.98.
* `test_height_matches_source_within_1cm` — mesh z-extent vs the `height` column, mesh bottom vs
  `ground_z`, mesh top vs `roof_z`, all within 1 cm.
* `test_attribute_round_trip` — `_BIN`, `_FLOORS`, `_FLOOR_HEIGHT`, `_GROUND_FLOOR_HEIGHT`,
  `_IS_STOREFRONT` and the reconstructed `lit_seed` equal the parquet values exactly.
* `test_wall_uvs_are_metres` — on every vertical wall face, `1 - V` equals height above `ground_z`
  to 2 cm, and `U` advances in metres.
* `test_manifest_matches_glb` — manifest byte count matches the file, zero open shells.
* `test_shellgeom_closes_every_roof_type` — 135 parametrised cases: 9 roof types x 3 LODs x 5
  awkward footprints (rectangle, L, courtyard-with-hole, triangle, 3 m sliver); each must be closed,
  outward-oriented and span exactly `[ground_z, roof_z]`.
* Plus footprint-cleaning tests (holes kept, winding, 2 cm snap) and an LOD2 massing test.

---

## 7. Gaps, deviations and decisions

**ADR-003 storage.** ADR-003 estimates "about 1.2 KB/building -> about 1.3 GB for the city". The
measured figure is **5,266 B/building -> 5.70 GB** for LOD0+LOD1+LOD2 with the full attribute set,
or about 2,900 B/building -> 3.2 GB for LOD0 alone. The gap is not extra geometry (47.3 triangles
per building is a minimal shell); it is that the ADR's estimate did not budget for (a) the LOD1/LOD2
chain the brief requires in the same file, which adds about 80 % on top of LOD0, and (b) the
per-building vertex attributes, which cost 32 B per exported vertex at LOD0 — 62 % of the LOD0
payload. Two mitigations are already applied: normals are not exported (glTF clients compute flat
normals from the winding, which is what a faceted shell wants) and the attribute set is reduced per
LOD (8/6/3). Draco was measured and rejected: it does compress a tile 4.7x (4.35 MB -> 0.92 MB,
right at the ADR-003 figure), but on this contended container the encoder needs 65-90 s per tile
(16+ hours for the city) and it makes the geometry unreadable by `pygltflib`, which the brief's test
list depends on. **Proposed ADR amendment:** restate ADR-003's shell budget as about 3 GB (LOD0) /
about 5.7 GB (with the LOD chain), and record Draco as a workstation-side packaging step, not a
build-time one.

**Stepped massing is built, and where it is not, that is counted.** 307,735 buildings (28 % of the
city, in 891 of the 920 tiles) carry more than one CityGML roof level. The recovery and the geometry
are described in §2; what follows is what it costs and what it misses, measured over the whole
rebuild and reported per tile in `manifest.json` under `roof_steps`.

Of the multi-level buildings the recovery is offered, a building drops out at one of five gates, and
each is counted separately per tile:

| gate | what it means | Midtown tile `t_-4_5` |
|---|---|---|
| `candidates` | `n_roof_levels >= 2` in the CityGML table | 623 |
| `rejected_area` | the recovered levels do not tile the CityGML plan | 5 |
| `rejected_plan` | the 2014 solid is not this building (mutual coverage with the footprint below 0.80) | 8 |
| `rejected_dz` | the two sources disagree on height by more than 20 % of it, or 15 m | 39 |
| `rejected_partition` | cutting the real footprint by the levels leaves nothing usable | 9 |
| `lost_would_not_close` | the stepped solid could not be made watertight, so the flat cap was kept | 137 |
| `shipped_with_levels_merged` | shipped, but with its smallest levels absorbed into their neighbour | 46 |
| **`shipped`** | **a real stepped solid is in the file** | **376** |

Two of those gates were widened in this pass, and both were widened for a reason that can be
checked rather than to raise the number:

* **Overlapping levels.** About one Midtown building in five has an overhang, so two level outlines
  overlap in plan and their *areas* sum above the footprint. The gate compared that sum to the
  published `roof_level_area` sum as an equality and rejected 131 of 623. It is now resolved
  top-down first — seen from above the taller surface is the one that is there — and the published
  sum is treated as the upper bound it actually is. **What makes this safe rather than permissive:**
  the union of the recovered levels reproduces `footprint_area_m2` for 100 % of candidates (5th
  percentile 1.000), the union of the CityGML *ground* surfaces reproduces the same column just as
  exactly, and after the change 99.75 % of the shipped step heights still land within 0.5 m of a
  published `roof_level_z` (median error 0.000 m). A building admitted by the change is one whose
  levels tile its plan and whose heights are the published ones.
* **The region cap.** A cap of 8 *plan regions* rejected 74 more on this tile — a level split into
  several disjoint patches counts several times, so the cap was rejecting buildings for having a
  light well rather than for anything about their steps. It is now 24 regions. The buildings this
  admits are checked by the same invariants as every other: regions inside the footprint (0 outside,
  measured), covering it (worst case 0.9958), and pairwise disjoint.

A third gate was **added**, not widened: every stepped building must now agree in plan with its own
footprint (0.80 mutual coverage, 0.95 when the height had to be shifted). Mutual coverage is sharply
bimodal — its 5th percentile is 0.96-0.999 over three tiles and only 1.1-2.3 % of buildings fall
below 0.80 — so this removes the ones where the 2014 solid is a different building, which the old
code would have stepped anyway.

**What is honestly weaker.** `applied_offset_z` counts buildings whose CityGML top and contract
`roof_z` differ by more than 3 m (135 of 513 on the Midtown tile). Their plans match to an IoU of
1.000, so they are the same building measured twice, and the quantity taken from CityGML — the depth
of each step below the top — is unaffected by a height offset. But the *altitude* of such a step
carries that offset, and it is counted separately for exactly that reason.

**The largest remaining defect in this feature: 137 of 513 assigned buildings on the Midtown tile
(27 %) lose their steps because the stepped solid will not close.** They are the busy ones — a
median of 8 plan regions against 2 for those that close. Each candidate fix was measured on its own
rather than assumed, and only three of six moved the number: snapping a region vertex onto a
footprint **corner** before its edges (294 -> 306 closed of 513), keeping two roof samples that
differ in position as well as in height and carrying the wall strip out to both ends of its edge
(306 -> 319), and splitting a step face at every level height present at its corners, which is the
T-junction where three levels meet (319 -> 330). Rebuilding the step faces from the exact shared
boundary of each region pair, filling a footprint edge that lost its wall-top samples, and noding
the regions against each other each closed nothing or one building on their own; they are kept
because they are right by construction, and their docstrings say so. A finer vertex weld (2 cm ->
1 cm, which was collapsing centimetre slivers into degenerate triangles) closes 330 on the *first*
attempt instead of 299. Finally the smallest levels are merged into the level that surrounds them
and the build retried, which recovers a further 46 buildings that would otherwise have lost every
step. The remainder still fail, in the caps and step faces rather than in the walls — attributed by
tagging each triangle with the routine that emitted it — and were not diagnosed further in this
pass. They keep their single-height shell and are counted in
`lost_would_not_close`; **`shipped` is what is in the file, and it is the only number in the
manifest that should be read as a delivery.**

**Stepped massing is LOD0 and LOD1 only.** LOD2 is the convex-hull massing of ARCHITECTURE §4.3 and
the merged L2/L3 skyline cells are built from it, so a setback tower is a single block at distance.
That is a pre-existing LOD decision, not a new one, but it means the *skyline* renders do not show
the setbacks that the street and aerial renders do.

**The shell materials are shading, not measurement.** The reflectance values in `shellmat.py` were
authored to make a curtain wall read as glass; no reflectance was measured for any NYC building, and
which material class a building is in is ADR-004's inference with its own `MATERIAL_REAL` bit. Two
parts of the gap are **not** closed: the spandrel band at each floor line is not in the geometry or
in the shipped material (`shellmat.floor_band_uv` states the expression an engine should use over
the metre UVs the shell already carries), and the per-building variation is a shader expression, so
a consumer that renders the glTF material as authored sees the class average rather than the
variation. Both are stated in DATA_CONTRACTS §13.

**LOD ratios.** The brief asks for about 35 % at LOD1 and about 8 % at LOD2. Measured over the
subset: LOD1 **42.6 %**, LOD2 **31.1 %** (dense masonry tiles reach 0.36/0.20; the Bayside
single-family tile is 0.62/0.59). 8 % is unreachable and the reason is arithmetic: a *closed* box
costs 12 triangles, and the mean LOD0 shell is only 47.3 triangles, so the floor for LOD2 on the
small-house stock — 70 % of the city — is about 25 %, not 8 %. LOD2 is already the minimum: the
convex hull simplified to at most 8 corners, extruded, capped. LOD1 uses a 0.5 m simplification with
no parapet, and where that saves less than 40 % the building ships the massing at LOD1 instead
(2,849 buildings in the subset). The only way to reach 8 % would be to drop the floor slab and ship
open shells, which contradicts the "no open shells" requirement; the requirement was kept.

**Eaves are flush.** Pitched roofs stop at the footprint ring with no overhang, fascia or soffit.
A real 0.3-0.45 m eave overhang is visible on houses at street level. The fix is a positive buffer
of the roof polygon plus a fascia band and soffit, which is closed and about 6 extra triangles per
building; it was left out for the same disk-budget reason as above and because it interacts with the
step work described earlier.

**Dome and complex roofs.** 8 domes are generated as faceted pyramids and 28 `complex` roofs as flat
+ parapet, because `tiles/{tile}/roofs.glb` — the `roof_mesh_ref` target of DATA_CONTRACTS §5 — does
not exist. Both are stated as approximations, not as measured roof shape.

**Fallback chains that are currently inactive but real.** When `roof_type` / `material_primary` /
`facade_class` are absent from a tile file, `tiledata` falls back in this order: `roof_type` column
-> `buildings/roof_attrs.parquet` (ADR-013) -> `facade_class` -> `facade_classes.json` `roof`
-> a PLUTO-class rule that reproduces ADR-013 §3 verbatim (classes A0-A9/B1-B3/B9/R1/R3,
`bldg_frontage / lot_frontage < 0.80`, short side <= 14 m, <= 3 floors, <= 400 m2, always gable) ->
flat. Material falls back through `facade_class` -> a PLUTO class x era x borough table. In the
shipped subset both chains resolved at step 1 for 100 % of rows, so no inferred value is in the
output; the chains exist so a tile written before the facade stage still produces correct-looking
geometry, and every tile manifest counts which source each building used.

**Foundation change requested (`blender/common/nycsim_bpy.py`, kit agent's file — not edited).**
`export_glb` does not pass `export_attributes` to `bpy.ops.export_scene.gltf`, and this stage
requires it, so `build_tile.export_glb` repeats the export call locally with the identical
`asset.extras.nycsim` contract. The requested change is one keyword:
`export_attributes: bool = False` passed through. Two smaller ones would also help every stage: an
`export_normals` passthrough (this stage saves 17 % of its bytes by omitting them) and moving the
metadata from the scene's custom property to `asset.extras` as DATA_CONTRACTS §13 specifies —
`build_tile.stamp_asset_extras` shows the (small) GLB rewrite that does it.

**Not verified here.** UE import of the custom vertex attributes, the LOD-group naming and the
Nanite build are workstation steps (ADR-001); the attribute layout above is what the importer will
see, verified by reading the exported files back, but no UE editor ran.

---

## 8. What the next agent needs to know

* Shell coordinates are **tile-local metres** — add `asset.extras.nycsim.origin_m` (the tile's
  south-west corner in NYC_TM) to get world X/Y. **Z is absolute NAVD88 metres**, not tile-local.
* The facade kit placer can key everything off `_BIN` on the vertices; the shell guarantees
  `1 - V` metres above `ground_z` on vertical faces, so a floor line is at
  `ground_floor_height + n * floor_height`.
* `has_storefront`, `floors`, `floor_height` and `ground_floor_height` are already on the vertices,
  so the ground-floor band can be shaded without a side table.
* The roof deck of a flat building is at `roof_z - 0.60 m` and is inset 0.30 m from the wall face —
  that is where rooftop kit items (water towers, HVAC, bulkheads) must be placed so they do not
  intersect the parapet.
* Merged L2/L3 cells use `pipeline.nycsim_pipeline.tiling.parent_tile`, so the runtime tile
  scheduler and these files agree on cell indices by construction.
* Re-running is cheap and safe: `--skip-existing` leaves finished tiles alone, and every tile writes
  its own manifest, so `blender/buildings/summary.py` reports whatever exists.
