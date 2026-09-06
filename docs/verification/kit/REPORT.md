# Facade kit — verification report

Stage: **Blender facade kit** (`blender/kit/facade/`, `blender_out/kit/`, `docs/verification/kit/`,
`tests/test_kit_facade.py`, plus the shared `blender/common/{textures.py, texture_catalog.json, facade_params.py,
facade_classes.json}`).

## 1. What was built

**138 production kit pieces** (brief asked for ≥ 120), each exported as
`blender_out/kit/facade/<id>.glb` with a per-piece catalog entry written through
`nycsim_bpy.write_catalog_entry` to `blender_out/kit/catalog/<id>.json`, plus the machine-readable enum contract
`blender_out/kit/facade_params.json`.

| file | role |
|---|---|
| `blender/kit/facade/kitlib.py` | geometry accumulator (metre UVs, named material slots), PBR materials from `textures.py`, LOD1 generation, glb export, catalog entries, triangle accounting |
| `blender/kit/facade/pieces_common.py` | shared sub-builders (masonry reveals, lintels, sills, segmental arches, sashes, railings, ladders, stairs, gratings, brackets, dentils) and the generated textures (interior cards, ivy sheet, sign strips) |
| `blender/kit/facade/pieces_windows.py` | 18 windows — one per `facade_params.WINDOW_TYPES` entry |
| `blender/kit/facade/pieces_accessories.py` | 15 window accessories |
| `blender/kit/facade/pieces_entries.py` | 13 stoops, doors, canopies, gates, hatches |
| `blender/kit/facade/pieces_trim.py` | 23 cornices, string courses, quoins, pilasters and loose trim |
| `blender/kit/facade/pieces_storefront.py` | 19 storefront bays, roll gates, scissor grilles, awnings, projecting sign |
| `blender/kit/facade/pieces_interiors.py` | 11 storefront interior shells (2.50 m deep) |
| `blender/kit/facade/pieces_roof.py` | 24 fire escapes, parapets, bulkheads, water towers, HVAC, antennas, billboards |
| `blender/kit/facade/pieces_street.py` | 9 sidewalk sheds, pipe scaffold, fences, ivy, roof weeds |
| `blender/kit/facade/build_kit.py` | driver — `python3 blender/kit/facade/build_kit.py [--only PREFIX] [--slice I/N] [--dry-run]` |
| `blender/kit/facade/render_sheets.py` | Cycles contact sheets and the assembled tenement test |
| `blender/kit/facade/render_all.sh` | runs every verification render, one Blender process at a time |
| `tests/test_kit_facade.py` | 973 acceptance tests against the exported artefacts |

### Coverage against the brief

* **Windows (18)** — double-hung 1/1 plain, 1/1 with stone lintel + sill, 1/1 with brick soldier lintel, 2/2, 6/6,
  casement pair, steel industrial 4 × 5, punched office, curtain-wall module (1.50 × 3.90 m with mullions, vision
  glass and a shadow-box spandrel), three-sided bay, segmental-arched tenement, gable dormer, aluminium slider,
  1950s picture window, Gothic traceried church window, ribbon strip, Chicago tripartite, through-wall AC sleeve.
* **Window accessories (15)** — window air conditioners in three real BTU sizes with their steel brackets, the
  bracket on its own, the outdoor half of a through-wall unit, HPD child window guard, welded security grille,
  flower box, curtains open and closed, half-drop venetian blind, roller shade, lit and unlit interior cards,
  wall satellite dish.
* **Entrances (13)** — 4-riser tenement stoop, 10-riser brownstone stoop with cheek walls, newels and areaway
  railing, areaway railing on its own, apartment lobby canopy, residential double doors, single panelled door,
  glazed lobby entrance, loft roll gate, sectional garage door, Gothic church portal, hollow-metal service door,
  sidewalk cellar hatch, Italianate brownstone door surround.
* **Trim (23)** — three pressed-metal cornice profiles + a single console bracket + a mitred return end, brick
  corbel cornice, limestone modillion cornice; four string courses; three quoin stacks; four pilasters; water
  table, loose lintel, loose sill, keystone, datestone, brick corner return.
* **Storefronts (19 + 11 interiors)** — bays at 3.6 / 4.8 / 6.0 m with bulkhead, plate glass, recessed entrance,
  transom, sign fascia and gooseneck lights; roll-down gate at each width in three states (closed / half /
  rolled-up); scissor security grille and canvas box awning at each width; projecting sign; and a 4.80 × 2.50 ×
  3.40 m interior shell for each of `facade_params.STOREFRONT_INTERIOR_KINDS` — bodega, deli, pharmacy,
  restaurant, bar, nail/hair, laundromat, bank (the eight trades the brief names) plus the three fallback shells
  the enum requires (generic retail, lobby, vacant).
* **Fire escapes (6)** — per-storey party-balcony unit (standard and wide), top balcony without a stair, L-shaped
  corner return, stowed drop ladder, gooseneck roof hook.
* **Roof (16)** — brick parapet wall, three parapet copings, cast-stone balustrade; brick / metal stair bulkheads
  and an elevator machine room; 10 000 and 20 000 gal cedar water towers; packaged RTUs (small and large),
  condenser bank, mushroom exhaust fan, cooling tower, vent-pipe cluster, brick chimney; cell sector array, whip
  mast, roof satellite dish, TV Yagi; 14.63 × 4.88 m rooftop bulletin and a 12.19 × 6.10 m wall bulletin.
* **Street (9)** — sidewalk-shed bay and corner bay, tube-and-clamp pipe scaffold bay, hunter-green plywood
  construction fence, chain-link panel, wrought-iron areaway fence, dense and sparse ivy panels, roof weed patch.

## 2. Conventions the next agent needs

* Blender Z-up metres; glTF exported Y-up by `nycsim_bpy.export_glb` with `asset.extras` → the glTF **scene**
  extras carry the `nycsim` JSON blob (schema_version, git commit, bounds, anchor, nominal size).
* The wall plane is `y = 0`; **+Y points into the building**, −Y is the street.
* Every glb contains exactly two meshes: `<id>` (LOD0) and `<id>_LOD1`.
* UVs are in metres; each material tiles through a Mapping node at its catalogued `physical_size_m`, which the
  exporter writes as `KHR_texture_transform`. Textures are embedded (1024 px JPEG colour / normal / ORM).
* `anchor.origin` names the datum the origin sits on, and the assembler places **that datum**:

| anchor | datum | used by |
|---|---|---|
| `wall_bottom_centre` | bottom-centre of the masonry opening / base of the piece on the wall plane (sills and aprons may hang up to 0.5 m below) | 75 pieces |
| `wall_sill_centre` | the sill line — AC units and flower boxes, whose brackets hang below | 5 |
| `wall_head_centre` | the head line — blinds and roller shades hang below | 2 |
| `wall_platform_centre` | the fire-escape platform deck (its stair descends to −3.05 m) | 4 |
| `wall_corner_bottom` | the building's outside corner at the base of the piece | 5 |
| `wall_corner_platform` | the outside corner at platform level | 1 |
| `wall_bay_frame` | the same origin as the storefront bay it belongs to (pavement level, bay centre) | 15 |
| `ground_bottom_centre` | bottom-centre of the footprint on the roof deck or pavement | 30 |
| `ground_corner_bottom` | outside corner of the footprint at pavement level | 1 |

* Every horizontal trim run (cornices, string courses, parapets, water table) is exactly **1.000 m long in X** so
  it repeats along a wall; quoins and pilasters are one unit / one storey tall instead.
* Storefront bays are **hollow** — pair each with a `storefront_interior_*` shell placed at the same origin
  (the bay's catalog entry carries `interior_depth_m = 2.5` and `glass_line_y_m = 0.25`). `facade_params.STOREFRONT_INTERIOR_FOR_KIND`
  maps all 20 storefront kinds onto the 11 shells; each shell's catalog entry lists the kinds it serves in
  `serves_storefront_kinds`.
* Gates, grilles and awnings carry `bay_width_m` (and gates `gate_state`) so they drop straight onto the
  matching bay. Per-piece extras are merged into the top level of the catalog entry.

## 3. Polycounts

| category | pieces | LOD0 tris | largest | budget (brief / kit) | LOD1 share | glb MB |
|---|---:|---:|---:|---:|---:|---:|
| `antenna` | 4 | 978 | 306 | - / 900 | 21 % | 4.6 |
| `billboard` | 2 | 1,904 | 1,528 | - / 2500 | 18 % | 2.6 |
| `bulkhead` | 3 | 420 | 260 | - / 900 | 18 % | 9.1 |
| `cornice` | 7 | 1,206 | 304 | - / 400/1000/1400 | 17 % | 2.0 |
| `door_entry` | 13 | 5,138 | 1,720 | - / 400/500/900/1200/1400/1600/1800/2000/2200/2600/3000 | 17 % | 13.6 |
| `fence` | 3 | 1,201 | 561 | - / 800 | 19 % | 2.9 |
| `fire_escape` | 6 | 4,198 | 1,260 | 3 000 / 3000 | 9 % | 2.9 |
| `hvac` | 7 | 2,072 | 516 | - / 1200 | 20 % | 10.5 |
| `parapet` | 5 | 804 | 708 | - / 300/900 | 22 % | 2.1 |
| `pilaster` | 4 | 622 | 228 | - / 400/900 | 21 % | 1.8 |
| `quoin` | 3 | 288 | 144 | - / 400/500 | 4 % | 1.0 |
| `scaffold` | 3 | 1,752 | 1,092 | - / 3000 | 22 % | 4.0 |
| `storefront` | 19 | 9,600 | 1,676 | 6 000 / 800/6000 | 10 % | 24.5 |
| `storefront_interior` | 11 | 9,831 | 1,642 | - / 6000 | 20 % | 16.3 |
| `string_course` | 4 | 300 | 144 | - / 200/400/500 | 17 % | 1.5 |
| `trim` | 6 | 139 | 48 | - / 200/300 | 14 % | 3.4 |
| `vegetation` | 3 | 824 | 440 | - / 1500 | 23 % | 0.2 |
| `water_tower` | 2 | 2,372 | 1,234 | 4 000 / 4000 | 18 % | 4.1 |
| `window` | 18 | 3,398 | 318 | 400 / 250/400/500/550/700/900/1000 | 5 % | 25.6 |
| `window_accessory` | 15 | 2,236 | 312 | - / 8/400 | 18 % | 7.4 |
| **total** | **138** | **49,283** | | | **15 %** | **140.1** |

`budget` is the per-piece cap recorded in the catalog; the brief's caps (window ≤ 400, storefront bay ≤ 6 000,
fire escape ≤ 3 000, water tower ≤ 4 000) are all met with margin — the largest window is 318 triangles, the
largest storefront piece 1 676, the largest fire escape 1 260, the largest water tower 1 234.

LOD1 is capped at 25 % of LOD0. Where collapse decimation cannot reach that (a mesh of separate closed bars —
fire escapes, scissor grilles, storefront bays — cannot go below four triangles per box), an explicit low-poly
builder is supplied instead (`_fe_lod`, `_grille_lod`, `_bay_lod`). Two pieces are so small that 25 % is below the
two-triangle floor of a triangle mesh (`acc_interior_card_lit` / `_unlit`, 4 triangles each); the enforced rule is
therefore `lod1 ≤ max(2, ceil(0.25 · lod0))`, which is binding for every piece above 8 triangles.

## 4. Verification

### 4.1 Build

```
$ nice -n 12 python3 blender/kit/facade/build_kit.py
138 pieces in 16 s
  triangles LOD0 total 49 283
  over budget : []
  LOD1 > 25 % : []
  size dev>5 %: []
```

Peak RSS of the build process ≈ 0.9 GB (all 46 catalogue materials and their embedded 1 K maps stay resident for
the whole run); 140.1 MB of glb written.

### 4.2 Tests

```
$ python3 -m pytest tests/test_kit_facade.py -q
973 passed in 15.15s
```

The suite opens every glb with `pygltflib` and checks, per piece: the file exists and loads; meshes `<id>` and
`<id>_LOD1` are both present; LOD1 ≤ max(2, 25 % of LOD0); LOD0 within its own budget *and* within the brief's
budget for its category; the POSITION accessor bounds converted back to Blender Z-up agree with the catalog and
sit within ±5 % of `nominal_size_m` on all three axes; the origin lies on the datum its anchor names; every glTF
image is embedded (no external URI) with a jpeg/png mime type and any piece listing texture assets has a material
with a base-colour texture; and every referenced texture asset has a CC0 `LICENSE.json` on disk. Kit-wide it
checks the ≥ 120 piece count, id/file agreement both ways, valid categories and anchors, the `nycsim` extras
round-trip, the written `facade_params.json` contract, and that the kit covers every `WINDOW_TYPES` entry, every
storefront bay width × gate state, every interior kind and the pieces the brief names individually.

### 4.3 Renders

Cycles CPU, 64 samples, adaptive sampling at 0.03, bounces limited to 4 (2 diffuse / 2 glossy / 4 transmission),
`nice -n 10`, one Blender process at a time:

| file | contents | resolution | render |
|---|---|---|---|
| `docs/verification/kit/tenement_test.png` | assembled 25 ft × 18 m five-storey New Law tenement | 800 × 1296 | RENDER_TENEMENT |
| `docs/verification/kit/facade_sheet_windows.png` | 18 windows | 1000 × H | RENDER_windows |
| `docs/verification/kit/facade_sheet_accessories.png` | 15 window accessories | 1000 × H | RENDER_accessories |
| `docs/verification/kit/facade_sheet_entries.png` | 13 entrances | 1000 × H | RENDER_entries |
| `docs/verification/kit/facade_sheet_trim.png` | 23 cornices / string courses / quoins / pilasters / trim | 1000 × H | RENDER_trim |
| `docs/verification/kit/facade_sheet_storefront.png` | 19 storefront pieces | 1000 × H | RENDER_storefront |
| `docs/verification/kit/facade_sheet_interiors.png` | 11 interior shells | 1000 × H | RENDER_interiors |
| `docs/verification/kit/facade_sheet_roof.png` | 6 fire escapes, 5 parapets, 3 bulkheads, 2 water towers | 1000 × H | RENDER_roof |
| `docs/verification/kit/facade_sheet_rooftop_equipment.png` | 7 HVAC, 4 antennas, 2 billboards | 1000 × H | RENDER_rooftop_equipment |
| `docs/verification/kit/facade_sheet_street.png` | 3 scaffold, 3 fence, 3 vegetation | 1000 × H | RENDER_street |

Each sheet is a near-orthographic elevation (camera pulled back 240 m with a matching narrow FOV) with every
piece labelled with its id, triangle count and measured size, so the sheet doubles as the visual index of the kit.
Free-standing pieces are turned 28° so their depth reads; wall pieces face the camera square-on.

The assembled test is a 7.62 m (25 ft) wide, five-storey, 18.07 m New Law tenement built **only** from kit pieces
plus a brick wall generated around the openings: a 4.20 m commercial ground storey with a 3.6 m storefront bay
(bodega interior, awning, gate rolled up in its hood) and a 4-riser stoop with a green panelled door; four
residential storeys at 3.20 m with three 1/1 soldier-lintel windows each, window ACs, a child window guard and a
flower box; a stone belt course; the standard party-balcony fire escape (three storey units, a top balcony, a
drop ladder and a gooseneck roof hook) on the centre bay; a pressed-metal cornice with mitred returns and a brick
parapet behind it; and on the roof a 10 000 gal cedar water tower, a stair bulkhead, an RTU, a vent-pipe cluster
and a TV aerial.

### 4.4 What the renders were used to fix

The renders were inspected and the following were corrected before this report:

1. **Contact-sheet backdrop.** The first sheets put a brick wall on the wall plane (`y = 0`); the kit's windows
   put their sashes, reveals and interior cards at positive y, so the backdrop hid exactly what the sheet exists
   to show. The backdrop is now a neutral plane *behind* the deepest piece.
2. **`Mesh.merge` / `Mesh.mirror_x` collapsed everything to one vertex** — a freshly created `BMVert` carries
   index −1 until `verts.index_update()` is called, so the remap dict had a single key. Fixed in `kitlib.py`.
3. **`win_dormer` had a solid front wall** with the sash buried behind it; the front skin is now built as a frame
   around the opening.
4. **`win_gothic_arched` had its two arch centres swapped**, which produced a dip at the crown instead of a
   point; the arch head is now glazed as well.
5. **`win_bay_window` had inward-facing facet normals** (the outward normal of a plan segment is `(uy, −ux)`, not
   `(−uy, ux)`), so the bay rendered inside-out and nearly empty; it is now a solid three-sided projection with
   apron, sill and head bands, piers, reveals, sashes and a lead-clad roof.
6. **Hunter green was fluorescent.** `plywood_green` (sidewalk sheds, construction fences) and
   `painted_metal_green` (shed frames, fire escapes) were far too bright and read as grass; both were re-tinted
   in `blender/common/texture_catalog.json` to sRGB ≈ #26523A / #2C4B38, and the generated ivy leaf sheet was
   desaturated and given veins.
7. **Portrait framing was cropping the water tower** — Blender's AUTO sensor fit applies `camera.angle` to the
   *larger* image dimension, so the FOV has to be derived from the matching half-extent. Fixed in
   `render_sheets.py` for both the sheets and the tenement.
8. **Catalog polycounts disagreed with the exported glb.** The exporter drops degenerate faces and merges
   coincident ones, so a decimated LOD1 of 30 Blender triangles could export as 22. `build_piece` now reads the
   triangle counts back out of the finished glb (stdlib GLB/JSON parse, `kitlib.glb_mesh_triangles`), and
   `evaluated_tris` ignores zero-area polygons; the catalog and the artefact now agree by construction, which the
   tests assert.
9. **Decimation fell back to a single bounding quad too eagerly.** `make_lod1` now retries with a tightening
   ratio and rejects a decimated result that has collapsed below four triangles, so the flat-quad proxy is a last
   resort rather than the common case.

## 5. Fidelity: what is real and what is not

Every dimension in the kit is a published or measured New York construction dimension, recorded in the source
next to the number it drives (`pieces_common.py` holds the shared ones): 67.5 mm brick course and 194 mm soldier
course; 150 mm stone lintels bearing 115 mm each side and projecting 40 mm; 100 mm sills with a 20 mm wash and
65 mm projection; 45 mm sash stiles, 40 mm meeting rails, 22 mm true-divided-light muntins; 3.05 m tenement and
3.20 m New Law floor-to-floor with a 4.20 m commercial ground storey; 0.55 m bulkhead / 2.35 m plate glass /
transom bar at 2.90 m / 0.80 m sign fascia; 0.95 m deep fire-escape platforms with 0.86 m (34 in) railings,
0.406 m (16 in) drop ladders at 305 mm rung pitch; 1.07 m (42 in) parapets; 2.44 m (8 ft) sidewalk-shed clear
height with a 1.07 m green plywood parapet and 2.44 m construction fences; 3.35 m × 3.66 m and 4.27 m × 4.88 m
cedar water tanks (10 000 / 20 000 US gal); 14.63 × 4.88 m (48 × 16 ft) rooftop bulletins; 5 000 / 8 000 /
18 000 BTU window AC cabinets; 0.915 × 2.13 m door leaves.

**Gaps, stated plainly:**

* The pieces are *typologies*, not surveys of named buildings. Each is the standard New York detail for its era
  and class, not a measured drawing of one address. Nothing in the kit is presented as a specific building.
* Ornament is modelled at kit-piece resolution: cornice brackets are swept S-curve profiles rather than
  cast foliate scrolls, the Ionic pilaster capital is a simplified volute, and terracotta rosettes are stepped
  blocks. At the triangle budgets the brief sets (a window is 400 triangles) that is the achievable fidelity;
  finer ornament belongs in normal maps, which the kit does not bake.
* Storefront sign bands are a plain painted panel with no lettering. The fascia geometry and its metre UVs are
  there for the signage/props agent to map real signs onto; inventing shop names here would be fabricated data.
* The interior shells are lit by emissive ceiling planes and flat-coloured stock, not by real fixtures; they are
  built to read correctly through 6 mm of glass from the sidewalk, which is all they are for.
* Only 30 of the 46 catalogued materials are used by kit pieces. The other 16 (asphalt, tar roof, brown/orange
  brick, rubble, siding variants, the Poly Haven stone walls) are in the shared catalog for the props, vehicle
  and landmark agents.
* The kit's own `billboard` budget was raised from 1 500 to 2 500 triangles: a 48 × 16 ft bulletin with a real
  lattice back-frame, catwalk and floodlights does not fit in 1 500. The brief fixes no budget for billboards.
* `blender/common/texture_catalog.json` was edited (two green tints) and `blender/common/textures.py` was not.
  `blender/common/nycsim_bpy.py` (foundation) was **not** modified; `render_sheets.py` works around its fixed
  camera setup by pre-setting the Cycles bounce limits and by pulling the camera back for a near-orthographic
  frame.

## 6. Texture licences

All embedded textures are CC0 1.0. 1024 px JPEG copies (colour with half-strength AO baked in, OpenGL normal, and
an ORM pack with roughness in G and metalness in B) are generated under
`assets/textures/<AssetID>/kit1024/` and embedded in every glb.

| asset | provider | author | licence | source | sha-256 (colour map archive) |
|---|---|---|---|---|---|
| `Bricks029` | ambientcg | ambientCG (Lennart Demes) | CC0 1.0 | https://ambientcg.com/view?id=Bricks029 | `27a436cd92128645...` |
| `Bricks058` | ambientcg | ambientCG (Lennart Demes) | CC0 1.0 | https://ambientcg.com/view?id=Bricks058 | `503c5bd37eb396a5...` |
| `Bricks060` | ambientcg | ambientCG (Lennart Demes) | CC0 1.0 | https://ambientcg.com/view?id=Bricks060 | `e8dce6fd843fce86...` |
| `Bricks082A` | ambientcg | ambientCG (Lennart Demes) | CC0 1.0 | https://ambientcg.com/view?id=Bricks082A | `ed11c95962a77ec9...` |
| `Concrete030` | ambientcg | ambientCG (Lennart Demes) | CC0 1.0 | https://ambientcg.com/view?id=Concrete030 | `cf129c209f714650...` |
| `Concrete034` | ambientcg | ambientCG (Lennart Demes) | CC0 1.0 | https://ambientcg.com/view?id=Concrete034 | `5839d284d94ffb8d...` |
| `CorrugatedSteel005` | ambientcg | ambientCG (Lennart Demes) | CC0 1.0 | https://ambientcg.com/view?id=CorrugatedSteel005 | `9bec057d9db923cd...` |
| `Fabric037` | ambientcg | ambientCG (Lennart Demes) | CC0 1.0 | https://ambientcg.com/view?id=Fabric037 | `156feaf51ea56993...` |
| `Fabric071` | ambientcg | ambientCG (Lennart Demes) | CC0 1.0 | https://ambientcg.com/view?id=Fabric071 | `c163b7d6af77293f...` |
| `Granite002A` | ambientcg | ambientCG (Lennart Demes) | CC0 1.0 | https://ambientcg.com/view?id=Granite002A | `551e8b2a0fac2b41...` |
| `Marble026` | ambientcg | ambientCG (Lennart Demes) | CC0 1.0 | https://ambientcg.com/view?id=Marble026 | `3fe558b15c3fd0e7...` |
| `Metal032` | ambientcg | ambientCG (Lennart Demes) | CC0 1.0 | https://ambientcg.com/view?id=Metal032 | `9e4f363905a64795...` |
| `Metal036` | ambientcg | ambientCG (Lennart Demes) | CC0 1.0 | https://ambientcg.com/view?id=Metal036 | `0629b2e8380e65ab...` |
| `Metal039` | ambientcg | ambientCG (Lennart Demes) | CC0 1.0 | https://ambientcg.com/view?id=Metal039 | `99b529f52030ca4d...` |
| `Metal055A` | ambientcg | ambientCG (Lennart Demes) | CC0 1.0 | https://ambientcg.com/view?id=Metal055A | `cb15430e4177d8d7...` |
| `Paint005` | ambientcg | ambientCG (Lennart Demes) | CC0 1.0 | https://ambientcg.com/view?id=Paint005 | `18ae3c5780119752...` |
| `PaintedWood002` | ambientcg | ambientCG (Lennart Demes) | CC0 1.0 | https://ambientcg.com/view?id=PaintedWood002 | `b136189aed23a855...` |
| `PaintedWood007C` | ambientcg | ambientCG (Lennart Demes) | CC0 1.0 | https://ambientcg.com/view?id=PaintedWood007C | `5f8235413ec48eab...` |
| `Planks023B` | ambientcg | ambientCG (Lennart Demes) | CC0 1.0 | https://ambientcg.com/view?id=Planks023B | `f483234085b5e351...` |
| `Plaster001` | ambientcg | ambientCG (Lennart Demes) | CC0 1.0 | https://ambientcg.com/view?id=Plaster001 | `944b4831016e42ac...` |
| `Rubber004` | ambientcg | ambientCG (Lennart Demes) | CC0 1.0 | https://ambientcg.com/view?id=Rubber004 | `d8933e73c3b98389...` |
| `Rust005` | ambientcg | ambientCG (Lennart Demes) | CC0 1.0 | https://ambientcg.com/view?id=Rust005 | `25c8b4b8a3488b78...` |
| `Tiles012` | ambientcg | ambientCG (Lennart Demes) | CC0 1.0 | https://ambientcg.com/view?id=Tiles012 | `fefd6079969309d2...` |
| `Tiles133A` | ambientcg | ambientCG (Lennart Demes) | CC0 1.0 | https://ambientcg.com/view?id=Tiles133A | `6aeec8cbd589cbed...` |
| `Travertine005` | ambientcg | ambientCG (Lennart Demes) | CC0 1.0 | https://ambientcg.com/view?id=Travertine005 | `cf10df1546e7b6b2...` |
| `Travertine009` | ambientcg | ambientCG (Lennart Demes) | CC0 1.0 | https://ambientcg.com/view?id=Travertine009 | `927ca19b99e32ed6...` |
| `WoodFloor051` | ambientcg | ambientCG (Lennart Demes) | CC0 1.0 | https://ambientcg.com/view?id=WoodFloor051 | `eb7d1cee763bb17a...` |
| `WoodSiding009` | ambientcg | ambientCG (Lennart Demes) | CC0 1.0 | https://ambientcg.com/view?id=WoodSiding009 | `5e55bdc169c4b3e3...` |
| `long_white_tiles` | polyhaven | Jenelle van Heerden, Sergej Majboroda | CC0 1.0 | https://polyhaven.com/a/long_white_tiles | `476ccb9f93aa78db...` |
| `terrazzo_tiles` | polyhaven | Amal Kumar | CC0 1.0 | https://polyhaven.com/a/terrazzo_tiles | `462e3e719cda0472...` |

Fonts: `assets/fonts/Overpass` (SIL Open Font License 1.1) is used for the contact-sheet labels only.

## 7. Reproducing

```sh
python3 blender/common/textures.py --fetch-all          # CC0 sources + LICENSE.json (already on disk)
python3 blender/kit/facade/build_kit.py                 # 138 glb + catalog, ~16 s
python3 -m pytest tests/test_kit_facade.py -q           # 973 assertions
sh blender/kit/facade/render_all.sh 64 1000             # every verification render, sequentially
```

## 8. Full piece list

| id | category | LOD0 | LOD1 | budget | size W x D x H (m) | anchor | materials |
|---|---|---:|---:|---:|---|---|---|
| `acc_ac_bracket` | window_accessory | 72 | 12 | 400 | 0.51 x 0.40 x 0.35 | wall_sill_centre | steel_galvanized |
| `acc_ac_window_large` | window_accessory | 276 | 49 | 400 | 0.67 x 0.66 x 0.80 | wall_sill_centre | aluminum_anodized, painted_metal_black, steel_galvanized |
| `acc_ac_window_medium` | window_accessory | 276 | 49 | 400 | 0.57 x 0.55 x 0.77 | wall_sill_centre | aluminum_anodized, painted_metal_black, steel_galvanized |
| `acc_ac_window_small` | window_accessory | 276 | 49 | 400 | 0.48 x 0.42 x 0.73 | wall_sill_centre | aluminum_anodized, painted_metal_black, steel_galvanized |
| `acc_blinds_half` | window_accessory | 312 | 59 | 400 | 0.89 x 0.04 x 0.73 | wall_head_centre | aluminum_anodized, paint_cream |
| `acc_curtains_closed` | window_accessory | 56 | 12 | 400 | 0.96 x 0.04 x 1.54 | wall_bottom_centre | aluminum_anodized, paint_cream |
| `acc_curtains_open` | window_accessory | 28 | 5 | 400 | 0.96 x 0.04 x 1.54 | wall_bottom_centre | aluminum_anodized, paint_cream |
| `acc_flower_box` | window_accessory | 148 | 32 | 400 | 1.00 x 0.37 x 0.59 | wall_sill_centre | painted_wood_white, soil, painted_metal_black, paint_red, foliage_green |
| `acc_interior_card_lit` | window_accessory | 4 | 2 | 8 | 1.30 x 0.01 x 2.00 | wall_bottom_centre | interior_lit, paint_black |
| `acc_interior_card_unlit` | window_accessory | 4 | 2 | 8 | 1.30 x 0.01 x 2.00 | wall_bottom_centre | interior_unlit, paint_black |
| `acc_roller_shade` | window_accessory | 56 | 10 | 400 | 0.92 x 0.06 x 1.00 | wall_head_centre | paint_cream |
| `acc_satellite_dish` | window_accessory | 172 | 39 | 400 | 0.46 x 0.59 x 0.85 | wall_bottom_centre | aluminum_anodized, painted_metal_black |
| `acc_through_wall_ac_unit` | window_accessory | 120 | 19 | 400 | 0.65 x 0.31 x 0.42 | wall_bottom_centre | aluminum_anodized, painted_metal_black |
| `acc_window_guard_child` | window_accessory | 156 | 4 | 400 | 1.03 x 0.08 x 0.66 | wall_bottom_centre | painted_metal_black |
| `acc_window_guard_security` | window_accessory | 280 | 50 | 400 | 1.01 x 0.04 x 1.76 | wall_bottom_centre | painted_metal_black |
| `antenna_cell_panel_array` | antenna | 306 | 64 | 900 | 1.92 x 2.17 x 3.85 | ground_bottom_centre | steel_galvanized, metal_panel, paint_grey, concrete |
| `antenna_satellite_dish_roof` | antenna | 302 | 71 | 900 | 1.24 x 1.17 x 1.61 | ground_bottom_centre | metal_panel, steel_galvanized, concrete |
| `antenna_tv_yagi` | antenna | 208 | 36 | 900 | 0.90 x 1.10 x 2.81 | ground_bottom_centre | steel_galvanized |
| `antenna_whip_mast` | antenna | 162 | 34 | 900 | 0.79 x 0.89 x 6.10 | ground_bottom_centre | steel_galvanized, neon_red, concrete |
| `billboard_rooftop` | billboard | 1528 | 263 | 2500 | 14.95 x 1.65 x 8.62 | ground_bottom_centre | metal_panel, steel_galvanized, concrete, fluoro_white |
| `billboard_wall_mounted` | billboard | 376 | 73 | 2500 | 12.39 x 1.13 x 6.75 | wall_bottom_centre | metal_panel, steel_galvanized, painted_metal_black, fluoro_white |
| `bulkhead_elevator_machine` | bulkhead | 260 | 46 | 900 | 3.70 x 4.30 x 4.02 | ground_bottom_centre | tan_brick, precast, roof_membrane, paint_grey, steel_galvanized, painted_metal_black |
| `bulkhead_stair_brick` | bulkhead | 92 | 19 | 900 | 2.90 x 3.50 x 2.71 | ground_bottom_centre | red_brick, precast, roof_membrane, paint_grey, steel_galvanized, chrome, fluoro_white |
| `bulkhead_stair_metal` | bulkhead | 68 | 11 | 900 | 2.30 x 2.75 x 2.44 | ground_bottom_centre | corrugated_metal, steel_galvanized, roof_membrane, paint_grey, painted_metal_black |
| `construction_fence_chainlink` | fence | 508 | 90 | 800 | 3.31 x 0.60 x 1.86 | ground_bottom_centre | steel_galvanized, plywood_green, concrete |
| `construction_fence_plywood` | fence | 132 | 22 | 800 | 2.44 x 0.14 x 2.48 | ground_bottom_centre | plywood_green, interior_wood_floor, glass_clear, paint_grey, paint_white |
| `cornice_bracket` | cornice | 56 | 10 | 400 | 0.15 x 0.40 x 0.60 | wall_bottom_centre | metal_panel |
| `cornice_brick_corbel` | cornice | 204 | 37 | 1400 | 1.01 x 0.34 x 0.54 | wall_bottom_centre | red_brick, precast |
| `cornice_pressed_metal_a` | cornice | 208 | 39 | 1400 | 1.00 x 0.54 x 0.92 | wall_bottom_centre | metal_panel |
| `cornice_pressed_metal_b` | cornice | 304 | 61 | 1400 | 1.00 x 0.66 x 1.15 | wall_bottom_centre | metal_panel |
| `cornice_pressed_metal_c` | cornice | 252 | 48 | 1400 | 1.00 x 0.44 x 0.62 | wall_bottom_centre | metal_panel |
| `cornice_return_end` | cornice | 86 | 4 | 1000 | 0.86 x 0.54 x 0.92 | wall_corner_bottom | metal_panel |
| `cornice_stone` | cornice | 96 | 4 | 1400 | 1.00 x 0.50 x 0.78 | wall_bottom_centre | limestone |
| `entry_apartment_lobby_glass` | door_entry | 278 | 4 | 1600 | 2.54 x 0.57 x 3.05 | wall_bottom_centre | granite, aluminum_anodized, glass_clear, chrome, interior_lit |
| `entry_areaway_railing` | door_entry | 372 | 61 | 900 | 3.20 x 0.15 x 1.05 | wall_bottom_centre | cast_iron |
| `entry_brownstone_door_surround` | door_entry | 188 | 35 | 1800 | 2.32 x 0.76 x 3.58 | wall_bottom_centre | brownstone |
| `entry_cellar_hatch` | door_entry | 104 | 24 | 400 | 1.52 x 1.22 x 0.12 | ground_bottom_centre | steel_galvanized, painted_metal_black |
| `entry_church_doors` | door_entry | 530 | 104 | 2600 | 2.84 x 0.97 x 4.40 | wall_bottom_centre | limestone, paint_darkgreen, interior_wood_floor, painted_metal_black, granite |
| `entry_door_single_panel` | door_entry | 196 | 38 | 900 | 1.17 x 0.39 x 2.57 | wall_bottom_centre | red_brick, paint_maroon, chrome, glass_clear, precast |
| `entry_double_doors` | door_entry | 224 | 42 | 1600 | 2.01 x 0.40 x 3.05 | wall_bottom_centre | red_brick, paint_darkgreen, glass_clear, interior_unlit, chrome, limestone |
| `entry_garage_door` | door_entry | 216 | 35 | 1200 | 2.90 x 0.30 x 2.28 | wall_bottom_centre | concrete, metal_panel, glass_clear, paint_grey |
| `entry_lobby_canopy` | door_entry | 200 | 45 | 2000 | 2.50 x 3.70 x 3.20 | wall_bottom_centre | canvas_striped, paint_white, aluminum_anodized, fluoro_white |
| `entry_loft_roll_gate` | door_entry | 308 | 50 | 1400 | 2.25 x 0.35 x 3.35 | wall_bottom_centre | red_brick, corrugated_metal, steel_galvanized, painted_metal_black |
| `entry_service_door_steel` | door_entry | 168 | 31 | 500 | 0.96 x 0.29 x 2.18 | wall_bottom_centre | red_brick, paint_grey, steel_galvanized, chrome |
| `entry_stoop_brownstone_10` | door_entry | 1720 | 309 | 3000 | 4.03 x 4.68 x 4.79 | wall_bottom_centre | brownstone, cast_iron, paint_darkgreen, glass_clear, interior_unlit, chrome |
| `entry_stoop_tenement_4` | door_entry | 634 | 113 | 2200 | 1.52 x 2.14 x 3.15 | wall_bottom_centre | granite, painted_metal_black, red_brick, paint_darkgreen, glass_clear, interior_unlit, chrome, limestone |
| `fence_iron_areaway` | fence | 561 | 113 | 800 | 2.49 x 0.05 x 1.20 | ground_bottom_centre | cast_iron |
| `fire_escape_balcony_top` | fire_escape | 576 | 40 | 3000 | 2.23 x 0.99 x 1.57 | wall_platform_centre | painted_metal_black |
| `fire_escape_corner_return` | fire_escape | 646 | 118 | 3000 | 1.56 x 1.56 x 1.53 | wall_corner_platform | painted_metal_black |
| `fire_escape_drop_ladder` | fire_escape | 204 | 36 | 3000 | 0.57 x 0.12 x 3.30 | wall_platform_centre | painted_metal_black |
| `fire_escape_floor_unit` | fire_escape | 1188 | 56 | 3000 | 2.23 x 1.01 x 3.90 | wall_platform_centre | painted_metal_black |
| `fire_escape_floor_unit_wide` | fire_escape | 1260 | 60 | 3000 | 3.08 x 1.01 x 3.90 | wall_platform_centre | painted_metal_black |
| `fire_escape_top_hook` | fire_escape | 324 | 56 | 3000 | 0.48 x 1.08 x 2.16 | wall_bottom_centre | painted_metal_black |
| `hvac_chimney_brick` | hvac | 90 | 19 | 1200 | 1.20 x 1.14 x 2.77 | ground_bottom_centre | red_brick, precast, terracotta, rust |
| `hvac_condenser_bank` | hvac | 450 | 78 | 1200 | 2.60 x 0.93 x 1.25 | ground_bottom_centre | steel_galvanized, painted_metal_black |
| `hvac_cooling_tower` | hvac | 444 | 80 | 1200 | 3.05 x 2.33 x 3.22 | ground_bottom_centre | metal_panel, painted_metal_black, steel_galvanized, rust |
| `hvac_exhaust_fan` | hvac | 174 | 37 | 1200 | 0.92 x 0.90 x 0.86 | ground_bottom_centre | interior_wood_floor, steel_galvanized |
| `hvac_rooftop_unit_large` | hvac | 204 | 35 | 1200 | 3.33 x 2.79 x 1.84 | ground_bottom_centre | interior_wood_floor, metal_panel, steel_galvanized, painted_metal_black, paint_grey |
| `hvac_rooftop_unit_small` | hvac | 194 | 33 | 1200 | 1.33 x 1.03 x 1.12 | ground_bottom_centre | interior_wood_floor, steel_galvanized, painted_metal_black, metal_panel |
| `hvac_vent_pipe_cluster` | hvac | 516 | 127 | 1200 | 1.14 x 0.74 x 1.52 | ground_bottom_centre | rust, steel_galvanized |
| `ivy_panel_dense` | vegetation | 440 | 100 | 1500 | 1.95 x 0.18 x 1.99 | wall_bottom_centre | ivy_leaf, soil |
| `ivy_panel_sparse` | vegetation | 200 | 43 | 1500 | 1.95 x 0.14 x 1.99 | wall_bottom_centre | ivy_leaf, soil |
| `parapet_balustrade` | parapet | 708 | 168 | 900 | 1.01 x 0.32 x 0.98 | ground_bottom_centre | limestone |
| `parapet_cap_metal_coping` | parapet | 24 | 4 | 300 | 1.00 x 0.40 x 0.14 | ground_bottom_centre | metal_panel |
| `parapet_cap_stone` | parapet | 24 | 2 | 300 | 1.00 x 0.42 x 0.12 | ground_bottom_centre | limestone |
| `parapet_cap_terracotta` | parapet | 24 | 4 | 300 | 1.00 x 0.40 x 0.19 | ground_bottom_centre | terracotta |
| `parapet_wall_brick` | parapet | 24 | 2 | 300 | 1.00 x 0.39 x 1.07 | ground_bottom_centre | red_brick, precast |
| `pilaster_brick` | pilaster | 24 | 2 | 400 | 0.49 x 0.23 x 3.05 | wall_bottom_centre | red_brick, precast |
| `pilaster_cast_iron` | pilaster | 156 | 28 | 900 | 0.36 x 0.32 x 3.90 | wall_bottom_centre | cast_iron |
| `pilaster_stone_fluted` | pilaster | 228 | 47 | 900 | 0.55 x 0.27 x 4.20 | wall_bottom_centre | limestone |
| `pilaster_storefront_column` | pilaster | 214 | 51 | 900 | 0.24 x 0.24 x 4.20 | ground_bottom_centre | cast_iron |
| `quoin_brick_rusticated` | quoin | 144 | 4 | 500 | 0.57 x 0.22 x 1.44 | wall_corner_bottom | precast |
| `quoin_brownstone` | quoin | 72 | 4 | 400 | 0.53 x 0.19 x 1.35 | wall_corner_bottom | brownstone |
| `quoin_limestone` | quoin | 72 | 4 | 400 | 0.60 x 0.19 x 1.35 | wall_corner_bottom | limestone |
| `roof_weeds_patch` | vegetation | 184 | 44 | 1500 | 1.56 x 1.56 x 0.54 | ground_bottom_centre | soil, foliage_green, foliage_green_dry |
| `scaffold_pipe_bay` | scaffold | 1092 | 255 | 3000 | 2.28 x 1.06 x 7.00 | ground_bottom_centre | steel_galvanized, interior_wood_floor |
| `sidewalk_shed_corner` | scaffold | 324 | 60 | 3000 | 4.33 x 4.33 x 3.81 | ground_corner_bottom | painted_metal_green, steel_galvanized, interior_wood_floor, plywood_green, fluoro_white |
| `sidewalk_shed_module` | scaffold | 336 | 64 | 3000 | 3.08 x 4.33 x 3.81 | ground_bottom_centre | painted_metal_green, steel_galvanized, interior_wood_floor, plywood_green, fluoro_white |
| `storefront_awning_36` | storefront | 180 | 37 | 6000 | 3.64 x 1.28 x 0.96 | wall_bay_frame | fabric_awning, aluminum_anodized |
| `storefront_awning_48` | storefront | 204 | 42 | 6000 | 4.84 x 1.28 x 0.96 | wall_bay_frame | fabric_awning, aluminum_anodized |
| `storefront_awning_60` | storefront | 228 | 47 | 6000 | 6.04 x 1.28 x 0.96 | wall_bay_frame | fabric_awning, aluminum_anodized |
| `storefront_bay_36` | storefront | 418 | 32 | 6000 | 3.66 x 1.07 x 4.34 | wall_bottom_centre | cast_iron, granite, aluminum_anodized, glass_clear, chrome, interior_wood_floor, metal_panel, paint_darkgreen, painted_metal_black, steel_galvanized |
| `storefront_bay_48` | storefront | 484 | 32 | 6000 | 4.86 x 1.07 x 4.34 | wall_bottom_centre | cast_iron, granite, aluminum_anodized, glass_clear, chrome, interior_wood_floor, metal_panel, paint_darkgreen, painted_metal_black, steel_galvanized |
| `storefront_bay_60` | storefront | 550 | 32 | 6000 | 6.06 x 1.07 x 4.34 | wall_bottom_centre | cast_iron, granite, aluminum_anodized, glass_clear, chrome, interior_wood_floor, metal_panel, paint_darkgreen, painted_metal_black, steel_galvanized |
| `storefront_gate_36_closed` | storefront | 660 | 113 | 6000 | 3.66 x 0.35 x 3.80 | wall_bay_frame | steel_galvanized, corrugated_metal, painted_metal_black |
| `storefront_gate_36_half` | storefront | 372 | 65 | 6000 | 3.66 x 0.35 x 3.80 | wall_bay_frame | steel_galvanized, corrugated_metal, painted_metal_black |
| `storefront_gate_36_open` | storefront | 72 | 14 | 6000 | 3.66 x 0.45 x 3.81 | wall_bay_frame | steel_galvanized |
| `storefront_gate_48_closed` | storefront | 660 | 113 | 6000 | 4.86 x 0.35 x 3.80 | wall_bay_frame | steel_galvanized, corrugated_metal, painted_metal_black |
| `storefront_gate_48_half` | storefront | 372 | 65 | 6000 | 4.86 x 0.35 x 3.80 | wall_bay_frame | steel_galvanized, corrugated_metal, painted_metal_black |
| `storefront_gate_48_open` | storefront | 72 | 14 | 6000 | 4.86 x 0.45 x 3.81 | wall_bay_frame | steel_galvanized |
| `storefront_gate_60_closed` | storefront | 660 | 113 | 6000 | 6.06 x 0.35 x 3.80 | wall_bay_frame | steel_galvanized, corrugated_metal, painted_metal_black |
| `storefront_gate_60_half` | storefront | 372 | 65 | 6000 | 6.06 x 0.35 x 3.80 | wall_bay_frame | steel_galvanized, corrugated_metal, painted_metal_black |
| `storefront_gate_60_open` | storefront | 72 | 14 | 6000 | 6.06 x 0.45 x 3.81 | wall_bay_frame | steel_galvanized |
| `storefront_grille_36` | storefront | 1096 | 42 | 6000 | 3.63 x 0.06 x 2.94 | wall_bay_frame | steel_galvanized, painted_metal_black |
| `storefront_grille_48` | storefront | 1328 | 62 | 6000 | 4.83 x 0.06 x 2.94 | wall_bay_frame | steel_galvanized, painted_metal_black |
| `storefront_grille_60` | storefront | 1676 | 72 | 6000 | 6.03 x 0.06 x 2.94 | wall_bay_frame | steel_galvanized, painted_metal_black |
| `storefront_interior_bank` | storefront_interior | 434 | 96 | 6000 | 4.80 x 2.50 x 3.40 | wall_bottom_centre | terrazzo, limestone, paint_white, fluoro_white, interior_wood_floor, granite, glass_clear, metal_panel, paint_black, chrome, painted_metal_black, paint_blue |
| `storefront_interior_bar` | storefront_interior | 1322 | 309 | 6000 | 4.80 x 2.50 x 3.40 | wall_bottom_centre | interior_wood_floor, dark_brick, paint_black, lamp_warm, metal_panel, steel_galvanized, paint_maroon, paint_green, paint_yellow, painted_metal_black |
| `storefront_interior_bodega` | storefront_interior | 1024 | 177 | 6000 | 4.80 x 2.50 x 3.40 | wall_bottom_centre | checker_tile, interior_tile, paint_white, fluoro_white, metal_panel, paint_red, paint_blue, paint_yellow, paint_cream, glass_clear, interior_wood_floor |
| `storefront_interior_deli` | storefront_interior | 396 | 72 | 6000 | 4.80 x 2.50 x 3.40 | wall_bottom_centre | checker_tile, subway_tile, paint_white, fluoro_white, metal_panel, glass_clear, paint_red, paint_cream, paint_yellow |
| `storefront_interior_generic_retail` | storefront_interior | 1090 | 193 | 6000 | 4.80 x 2.50 x 3.40 | wall_bottom_centre | interior_wood_floor, paint_white, fluoro_white, metal_panel, paint_red, paint_blue, paint_yellow, paint_cream, paint_black |
| `storefront_interior_laundromat` | storefront_interior | 1306 | 279 | 6000 | 4.80 x 2.50 x 3.40 | wall_bottom_centre | interior_tile, paint_white, fluoro_white, metal_panel, glass_clear, steel_galvanized, paint_blue, paint_yellow |
| `storefront_interior_lobby` | storefront_interior | 589 | 106 | 6000 | 4.80 x 2.50 x 3.40 | wall_bottom_centre | terrazzo, limestone, paint_white, lamp_warm, bronze_anodized, metal_panel, paint_black, paint_maroon, interior_wood_floor, foliage_green, painted_metal_black |
| `storefront_interior_nail_hair` | storefront_interior | 1018 | 197 | 6000 | 4.80 x 2.50 x 3.40 | wall_bottom_centre | interior_tile, paint_white, fluoro_white, paint_blue, steel_galvanized, chrome, paint_black, paint_red |
| `storefront_interior_pharmacy` | storefront_interior | 1642 | 310 | 6000 | 4.80 x 2.50 x 3.40 | wall_bottom_centre | interior_tile, paint_white, fluoro_white, metal_panel, paint_red, paint_blue, paint_yellow, paint_cream |
| `storefront_interior_restaurant` | storefront_interior | 616 | 121 | 6000 | 4.80 x 2.50 x 3.40 | wall_bottom_centre | interior_wood_floor, paint_maroon, paint_white, lamp_warm, steel_galvanized, granite, metal_panel, paint_black, painted_metal_black |
| `storefront_interior_vacant` | storefront_interior | 394 | 72 | 6000 | 4.80 x 2.50 x 3.40 | wall_bottom_centre | concrete, stucco, fluoro_white, plywood_green, metal_panel, interior_wood_floor, paint_grey |
| `storefront_sign_projecting` | storefront | 124 | 24 | 800 | 0.11 x 1.16 x 0.95 | wall_bottom_centre | paint_darkgreen, metal_panel, painted_metal_black, fluoro_white |
| `string_course_brick_soldier` | string_course | 12 | 2 | 200 | 1.00 x 0.13 x 0.19 | wall_bottom_centre | red_brick |
| `string_course_dentil` | string_course | 144 | 27 | 400 | 1.00 x 0.29 x 0.24 | wall_bottom_centre | terracotta |
| `string_course_stone_belt` | string_course | 24 | 2 | 200 | 1.00 x 0.18 x 0.25 | wall_bottom_centre | limestone |
| `string_course_terracotta_band` | string_course | 120 | 20 | 500 | 1.00 x 0.16 x 0.36 | wall_bottom_centre | terracotta |
| `trim_corner_bead_brick` | trim | 37 | 5 | 300 | 0.34 x 0.34 x 3.05 | wall_corner_bottom | red_brick, granite, precast |
| `trim_datestone_plaque` | trim | 48 | 7 | 300 | 0.72 x 0.16 x 0.48 | wall_bottom_centre | limestone |
| `trim_keystone` | trim | 12 | 2 | 200 | 0.26 x 0.19 x 0.44 | wall_bottom_centre | limestone |
| `trim_lintel_stone` | trim | 12 | 2 | 200 | 1.18 x 0.14 x 0.15 | wall_bottom_centre | limestone |
| `trim_sill_cast_stone` | trim | 12 | 2 | 200 | 1.10 x 0.17 x 0.10 | wall_bottom_centre | precast |
| `trim_water_table` | trim | 18 | 2 | 300 | 1.00 x 0.22 x 0.42 | wall_bottom_centre | granite |
| `water_tower_large` | water_tower | 1234 | 229 | 4000 | 4.45 x 4.60 x 13.08 | ground_bottom_centre | cedar_wood, steel_galvanized, rust |
| `water_tower_small` | water_tower | 1138 | 209 | 4000 | 3.53 x 3.68 x 10.40 | ground_bottom_centre | cedar_wood, steel_galvanized, rust |
| `win_aluminum_slider` | window | 174 | 4 | 400 | 1.31 x 0.32 x 1.48 | wall_bottom_centre | white_glazed_brick, aluminum_anodized, glass_clear, interior_unlit, precast |
| `win_arched_tenement` | window | 246 | 4 | 400 | 1.13 x 0.34 x 2.36 | wall_bottom_centre | red_brick, painted_wood_white, glass_clear, interior_unlit, granite |
| `win_bay_window` | window | 124 | 29 | 900 | 2.49 x 0.68 x 2.62 | wall_bottom_centre | brownstone, glass_clear, interior_unlit, painted_wood_white, metal_panel |
| `win_casement_pair` | window | 234 | 4 | 400 | 1.21 x 0.34 x 1.70 | wall_bottom_centre | tan_brick, painted_metal_black, glass_clear, interior_unlit, precast |
| `win_chicago_tripartite` | window | 318 | 4 | 550 | 2.60 x 0.34 x 2.49 | wall_bottom_centre | red_brick, painted_wood_white, glass_clear, interior_unlit, precast |
| `win_curtain_wall_module` | window | 134 | 22 | 500 | 1.50 x 0.29 x 3.90 | wall_bottom_centre | aluminum_anodized, glass_curtain, metal_panel, concrete, interior_unlit |
| `win_dormer` | window | 268 | 4 | 700 | 1.64 x 1.09 x 2.25 | wall_bottom_centre | painted_wood_white, metal_panel, glass_clear, interior_unlit |
| `win_double_hung_1_1` | window | 174 | 4 | 400 | 0.99 x 0.29 x 1.75 | wall_bottom_centre | red_brick, painted_wood_white, glass_clear, interior_unlit, precast |
| `win_double_hung_1_1_soldier` | window | 186 | 4 | 400 | 1.06 x 0.32 x 1.99 | wall_bottom_centre | red_brick, painted_wood_white, glass_clear, interior_unlit, precast |
| `win_double_hung_1_1_stone` | window | 186 | 4 | 400 | 1.18 x 0.34 x 1.95 | wall_bottom_centre | red_brick, painted_wood_white, glass_clear, interior_unlit, limestone |
| `win_double_hung_2_2` | window | 210 | 4 | 400 | 1.18 x 0.34 x 2.05 | wall_bottom_centre | brownstone, painted_wood_white, glass_clear, interior_unlit |
| `win_double_hung_6_6` | window | 258 | 4 | 400 | 1.01 x 0.34 x 1.89 | wall_bottom_centre | red_brick, painted_wood_white, glass_clear, interior_unlit, brownstone |
| `win_gothic_arched` | window | 160 | 32 | 1000 | 1.35 x 0.27 x 3.67 | wall_bottom_centre | limestone, glass_curtain, painted_metal_black |
| `win_picture_window` | window | 202 | 4 | 400 | 1.92 x 0.33 x 1.46 | wall_bottom_centre | vinyl_siding, painted_wood_white, glass_clear, interior_unlit, aluminum_anodized |
| `win_punched_office` | window | 102 | 4 | 400 | 1.62 x 0.33 x 2.29 | wall_bottom_centre | precast, aluminum_anodized, glass_curtain, interior_unlit |
| `win_ribbon_strip` | window | 126 | 4 | 400 | 3.10 x 0.33 x 1.60 | wall_bottom_centre | concrete, aluminum_anodized, glass_curtain, interior_unlit, precast |
| `win_steel_industrial_4x5` | window | 170 | 4 | 400 | 1.62 x 0.32 x 2.44 | wall_bottom_centre | red_brick, painted_metal_black, glass_clear, interior_unlit, steel_galvanized, precast |
| `win_through_wall_ac_sleeve` | window | 126 | 22 | 250 | 0.81 x 0.34 x 0.59 | wall_bottom_centre | tan_brick, steel_galvanized, aluminum_anodized, precast |
