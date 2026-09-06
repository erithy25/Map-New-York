# Stage report — character (player + NPC system)

**Lane:** `blender/character/`, `blender_out/character/`, `docs/verification/character/`, `docs/CHARACTER.md`,
`tests/test_character.py`
**Engine:** Blender 4.5.13 LTS as the `bpy` Python module, CPU only. MPFB2 2.0.17 driven headless.
**Date:** 2026-09-06

---

## 0. Second pass — the body, diagnosed rather than sculpted around

The first pass shipped a head the review accepted and a body it did not: *"the clothing is an inflated shell,
the arms are fused to the torso, the hands are barely formed, the feet read as flippers, and there is broken
geometry at the neck join."* The review also asked, correctly, whether the body proxy, hands, feet and
clothing had come through the MakeHuman pipeline at all or whether this was a fallback mesh. **They had. The
mesh was never the problem.** Rendering the character one layer at a time settled it in four frames:

| layer | verdict |
|---|---|
| bare body | correct — modelled fingers with nails, real feet, clavicles, a shoulder line, an armpit gap |
| `+ tee_white` | a real tee: hem, neckline, sleeve seams, armpits |
| `+ hoodie_grey` | a real knitted pullover: ribbed collar, cuffs and hem |
| `+ jacket_bomber` | **a shapeless sack that swallowed all three** |

Every symptom in the review traced to one of five defects, all of them in the wardrobe and export code, none
in the body. Each is stated below with the evidence that found it and the fix that closed it.

### 0.1 The "bomber jacket" was never a jacket

`jacket_bomber` was the upper shell of `male_casualsuit02`. Splitting that asset by connected component and
rendering the halves shows what they are: a **1 250-vertex crude long-sleeve tee** and a pair of jeans. There
is no jacket in the file. Fitted over a tee and a sweater and pushed out 24 mm it became the balloon in
`full_body_front.png`, and because it reached past the wrist it was also what buried the hands.

To pick a replacement on evidence rather than on the asset's name, all eleven male MakeHuman suit/jacket
assets were fitted to the player's body and rendered side by side (audition sheet, 11 frames). What they
actually contain:

| asset | upper shell really is | vertices |
|---|---|---|
| `male_casualsuit01` | button-down shirt **welded to** jeans (one connected component) | 8 426 |
| `male_casualsuit02` | long-sleeve tee | 1 250 |
| `male_casualsuit03` | striped button shirt | 1 613 |
| `male_casualsuit04` | short-sleeve tee | 810 |
| **`male_casualsuit05`** | **four-pocket field jacket** over a shirt | 1 659 |
| `male_casualsuit06` | plain tee | 2 822 |
| `male_worksuit01` | denim overalls over a tee | 2 497 |
| `male_elegantsuit01` | suit jacket + shirt + tie (one shell) | 6 256 |
| `toigo_male_suit_3` | pinstripe suit jacket + shirt + tie | 4 256 |
| `toigo_male_double-breasted_suit` | double-breasted suit jacket | 1 694 |
| `toigo_male_suit_tie_and_jacket` | suit jacket + tie | — |

MakeHuman's CC0 packs contain **exactly one casual jacket** (`male_casualsuit05`) and four tailored suit
jackets. So `jacket_field`, `jacket_denim` and `jacket_leather` are the same field-jacket mesh in three
fabrics — stated here rather than implied — and `male_casualsuit02/03` became what they are: a long-sleeve tee
and a button shirt in the *tops* slot. A new split mode, `keep="outer"`, takes the outermost shell of a
multi-shell suit by horizontal footprint, which is how the field jacket comes off without the plaid shirt
modelled inside it; the suit jackets keep `keep="upper"`, because their shirt and tie are part of the same
shell and a suit jacket with the shirt cut out of it opens onto nothing. `male_casualsuit01` is unusable: its
shirt and jeans are one welded component, and a height cut through it leaves a raw edge that tears across the
midriff of a short wearer (0.7).

### 0.2 The garment re-weighting was inert — every garment still had MPFB's proximity weights

The first pass reported that `reweight_from_body` had replaced MPFB's proximity fit with the body's own
anatomical weights. It had not. `vertex_groups.new(name=...)` does not overwrite an existing group, it
creates `spine_05.001` beside `spine_05` — and `.001` matches no bone, so the armature modifier ignores it.
Dumping the shipped `player.blend` showed every garment carrying **both** sets:

```
jacket_bomber: 69 vertex groups
  bone-matching (these drove the deformation): calf_l calf_r foot_l foot_r thumb_01_l thumb_02_l
      index_metacarpal_l ... spine_01..05 upperarm_l/r ...          <- MPFB proximity fit: a jacket
                                                                       weighted to the feet and the thumbs
  ignored by the armature: spine_05.001 upperarm_l.001 lowerarm_l.001 ... <- the correct weights
sneakers_black: active groups include neck_01, neck_02, spine_01..spine_05   <- shoes weighted to the neck
```

`_transfer_weights` now removes every existing vertex group before writing, which also drops MakeHuman's
bookkeeping groups (`Delete.*`, `Left`/`Mid`/`Right`, `body`) that were otherwise propagating into every
procedural layer cut from a garment.

### 0.3 The 24 mm normal push tore the collar — that is the "broken geometry at the neck join"

The outer layer was stood off with `vert.co += vert.normal * 0.024`. On an **open boundary** — the neck hole,
the cuffs, the hem — a vertex normal is the average of the faces on one side only, so consecutive boundary
vertices tilt in alternating directions and the edge comes out as a saw-tooth. That is exactly the jagged
fringe the review saw around the collar in `face_closeup.png`.

`wardrobe.push_along_normals` replaces it: raw vertex normals are Laplacian-smoothed over the edge graph, and
the push is tapered to zero across three rings of any open boundary, so the hem, the cuffs and the collar
stay where the tailor put them and only the panels between them stand off. The outer-layer stand-off also
came down from 24 mm to 11 mm, which is a jacket over a sweater rather than an inner tube.

### 0.4 The skin was never removed from under the clothes — that is the "flipper" foot

Every MakeClothes asset ships a *delete group* naming the base-mesh vertices it hides, and MPFB imports it as
`Delete.<asset>` and drives a Mask modifier with it. `strip_helper_geometry` deleted the helper geometry and
then removed **every** Mask modifier — including the one masking the clothes. So the whole foot stayed inside
the sneaker and interpenetrated it, which is why `detail.png` showed a torn black shell with a bare foot
coming out of the back of it.

`mh_build.hide_body_under_clothes` now deletes those vertices, guarded so a suit whose trouser half was split
away cannot delete a leg it no longer covers: a marked vertex goes only if a ray along **its own normal**
hits a worn garment within 60 mm. (A proximity query was tried first and deletes the skin in the gap between
a hem and a waistband, because the nearest garment point there is the hem edge — the gap then shows the
backdrop straight through the body.) On the player that removes 2 819 of 13 380 body vertices (21 %), which
is 21 % less skin to skin and to export.

### 0.5 Nothing resolved one garment against another

Two garments fitted independently to the same body do not know about each other, so a tee's shoulder seam can
sit outside the sweater over it. `wardrobe.resolve_layers` gives the outer layer the last word: for every
vertex of an inner garment it takes the **closest point on the outer garment's surface** (`closest_point_on_
mesh`, against the real triangles and their face normals — a coarse outer mesh has vertices whose normals
point nowhere near the surface being poked through) and, if the inner vertex is outside it, moves it back
until it is 5 mm inside. Three passes. Two orderings had to be got right and both were visible in a render
before they were:

* a base top goes *inside* the waistband and the trousers close over it, while a sweater or jacket hangs
  outside them — with the naive "top over bottom" rule, white scraps of tee stuck through the seat of the
  trousers;
* a trouser leg drapes *over* the shoe, but a shoe is rigid and must not be dented to make room, so for that
  one pair it is the trouser that moves, outward, out of the shoe.

On the player, 2 487 garment vertices move.

### 0.6 Consequences for the review's five points

| review point | cause | state now |
|---|---|---|
| clothing is an inflated shell | 0.1 + 0.3 | real tailored meshes; ribbed collar, cuffs and hem visible in `full_body.png` |
| arms fused to the torso | 0.1 (one shell over tee + sweater + arms) | armpit gap and shoulder line visible front and back |
| hands barely formed | the crude sleeve reached past the wrist | never a mesh problem — see `detail.png`: knuckles, nails, four modelled fingers and a thumb |
| feet read as flippers | 0.4 | `detail.png`: a black sneaker with a sole line, toe cap and stitching, no skin through it |
| broken geometry at the neck join | 0.3 | clean ribbed collar in `face_closeup.png` |

Two further defects were found by the same method and fixed in this pass: the pullover's procedural hood was
a faceted grey sphere stuck to the back (three shapes were built and judged on the render before one read as
a hood — see 7.4), and the player's outfit was cut from three MakeHuman torso layers to two, because
`push_along_normals` can stand one fitted layer off another cleanly but three shells fitted to the same body
cannot all clear each other and the middle one is the one that shows.

### 0.7 The same method, applied to the NPCs

The line-up was then rendered from the *exported glb files* rather than from the build scene, and read the
same way — one pedestrian at a time, at portrait size. Six more defects came out of that, all fixed:

| what the render showed | cause | fix |
|---|---|---|
| the whole line-up washed out and the ends dark | the three-point *portrait* rig lighting a nine-metre line-up: inverse-square falloff blows out the middle | `render_verify.lineup_lighting` — two suns and a lit world, distance-independent, so every pedestrian is lit identically |
| a courier's box clipping out of the front of an eight-year-old | bag sizes and offsets were absolute, so a 0.40 m box on a 1.16 m child reaches out of the chest | every bag dimension and offset scales with the wearer's own stature |
| a shoulder bag floating a hand's width clear of the hip | it was placed at a fixed 170 mm from the spine | placed by ray-casting to the body's actual side surface, falling back from the garment to the skin |
| a tote hanging horizontally off the forearm | built in world axes, and in MakeHuman's rest pose the arm points sideways | hand and forearm bags are built in the *bone's* frame, whose axis is "down" once the arm hangs |
| grey joggers with a floral print | `toigo_harem_pants` carries a large floral map, and the tint keeps luminance as fabric detail | `Garment.flat_colour` drops the map for assets whose pattern is not fabric detail |
| a torn gap across an older woman's midriff | `male_casualsuit01` welds its shirt to its jeans, so the shirt came off by a height cut whose raw edge lands above the waistband on a short wearer | both button shirts come off `male_casualsuit03`, which separates cleanly by connected component; the height-cut split mode is gone |
| skin missing between a polo hem and a waistband | the "is this skin covered?" test was a proximity query, and near a hem the nearest garment point is the hem edge | the test is now a ray along the skin's own normal: no cloth above it, no deletion |
| a "loafer" that is a trainer and "boots" that are a slip-on | the shoe assets were assigned from their file names | all six `shoesNN` assets were fitted and rendered at 300 px, and named for what they are (7.5) |

---

## 1. What was built

| Artefact | Content |
|---|---|
| `blender_out/character/player.glb` | Nikos Vlahos: 71-bone UE5-Mannequin rig, 16 skinned meshes, 52 ARKit morph targets, 25 glTF animations at 30 fps |
| `docs/verification/character/detail.png` | hand and foot close-ups - added after the orchestrator's review, because the two places a body most obviously fails cannot be judged in a full-figure shot |
| `blender_out/character/player.blend` | the scene the verification renders open (no rebuild) |
| `blender_out/character/catalog/player.json` | bones, per-clip metadata, measurements, asset licences, driver package |
| `blender_out/character/npc/npc_*.glb` | 24 pedestrians decoded from the pedestrian simulation's 12-dimensional variety contract, same skeleton and same clip set |
| `blender_out/character/npc_variety.json` | the pedestrian variety contract as this lane consumes it, the 47-item wardrobe, the 12 hairstyles, and every generated NPC's twelve floats |
| `docs/CHARACTER.md` | the person, his verified address, and the build inventory |
| `tests/test_character.py` | acceptance tests over the exported artefacts plus unit tests of the ASF/AMC parser |

Source modules (all new in this lane):

```
blender/character/chenv.py            environment bootstrap; enables MPFB2; the os._exit shutdown workaround
blender/character/ue5_skeleton.py     the 71-bone UE5 set, hierarchy, and the CMU -> UE5 retarget map
blender/character/asf_amc.py          CMU ASF/AMC parser + forward kinematics (pure numpy, no bpy)
blender/character/mh_build.py         MPFB body, ARKit blendshapes, helper strip, eye split, skin/eye materials
blender/character/rig_ue5.py          MPFB game_engine rig -> UE5 mannequin, with weight redistribution
blender/character/pose_solver.py      closed-form pose evaluation + analytic two-bone IK
blender/character/retarget.py         CMU -> UE5 rotation-delta retargeter, gait analysis, speed matching
blender/character/anim_lib.py         F-curve baking, NLA/glTF export, asset.extras patching, glb reader
blender/character/car_ref.py          driver package read out of the vehicles lane's exported Fusion Hybrid
blender/character/anim_procedural.py  every non-mocap clip
blender/character/wardrobe.py         47 NYC garments: MakeHuman tailored meshes, layer stand-off and
                                      layer resolve, plus the vests, hood, bags, hats and watch
blender/character/variety.py          decodes the traffic lane's 12-dimensional pedestrian variety vector
blender/character/npc_generator.py    contract vector -> MakeHuman macros, outfit, tints, gait, glb
blender/character/build_character.py  the player entry point
blender/character/render_verify.py    the Cycles verification renders
```

---

## 2. MPFB2 headless — it works

The brief allowed a fallback to a raw MakeHuman base mesh plus Rigify if MPFB could not be driven headless.
**It could.** MPFB2 2.0.17 is installed as a Blender *extension* (`bl_ext.user_default.mpfb`) and is enabled
from the `bpy` module with `addon_utils.enable("bl_ext.user_default.mpfb")`. Two facts had to be found by
experiment and are recorded in `chenv.py`:

* extensions are **not** auto-enabled when Blender runs as a Python module, so every entry point calls
  `chenv.enable_mpfb()` first;
* the `bpy` module deadlocks in its own atexit handlers (the repo's `hang_repro.py` is the minimal case), so
  every entry point ends with `chenv.hard_exit()` (`os._exit`).

With those two, `HumanService.deserialize_from_dict` builds a fully shaped, rigged, dressed character in
about 4 s. No fallback was needed and none is used.

---

## 3. The player and his address

Name **Nikos "Nick" Vlahos**, 34, **23-22 31st Avenue, Apt 3R, Astoria, Queens, NY 11106**.
The 200-word backstory is in `docs/CHARACTER.md`.

The address was verified twice, against two independent files:

```
data/processed/buildings/buildings_base.parquet, BIN 4006653
  bbl 4005690038  bldg_class C1  land_use 2  floors 4  year_built 1926
  address "23-22 31 AVENUE"  tile t_1_7  nta QN0103
  height 15.33 m (height_source 0 = LiDAR-real)  footprint_area 190.76 m2
data/raw/nyc_opendata/pluto.csv, BBL 4005690038
  postcode 11106  bldgclass C1  landuse 2  numfloors 4  unitsres 12  unitstotal 12
  yearbuilt 1926  zonedist1 R6A  council district 22  community board 401
  latitude 40.7660977  longitude -73.9280196
```

PLUTO class **C1** is "walk-up apartments, six families or more, without stores" and land use **2** is
"multi-family walk-up buildings" — residential on both axes, with 12 residential units. The NYC_TM centroid
(1859.864, 7345.275) round-trips through `pipeline/nycsim_pipeline/crs.py` to 40.766142 N, 73.927972 W, about
5 m from PLUTO's own lat/lon for the lot. `test_catalog_records_the_home_address_and_it_is_residential`
re-reads the parquet and re-checks the class on every test run.

---

## 4. MakeHuman / CMU assets used, with licences

| Pack | Licence | Author / attribution | What it contributed |
|---|---|---|---|
| MPFB2 2.0.17 (`assets/character/downloads/add-on-mpfb-v2.0.17.zip`) | **GPL-3.0-or-later** for the add-on code; the bundled hm08 base mesh, targets, rigs and weights are **CC0-1.0** | Joel Palmius / MakeHuman team | hm08 base mesh (19 158 verts), macro targets, `game_engine` rig definition and its skin weights, joint helper cubes |
| `faceunits01` (functional pack) | CC0-1.0 | Mika Suominen | **all 52 ARKit face-unit targets** |
| `makehuman_system_assets` | CC0-1.0 | MakeHuman team / Data Collection AB | high-poly eyes, `teeth_base`, `tongue01`, 10 hair meshes, 23 skin materials, 7 proxy meshes |
| `eyebrows01` | CC0-1.0 | Mindfront et al. | 26 eyebrow meshes (`eyebrow006` on the player) |
| `eyelashes01` | CC0-1.0 | Mindfront et al. | 9 eyelash meshes (`eyelashes02` on the player) |
| `shirts01`, `pants01`, `suits01`, `suits05` | CC0-1.0 | Joel Palmius, namuhekam, Cortu, MargaretToigo et al. | reference tailoring; the shipped characters use procedural garments instead (section 7) |
| `glasses01`, `hats01`, `hats02` | CC0-1.0 | MakeHuman community | NPC glasses and the fedora |
| `bodyparts01`, `equipment01`, `makehuman_system_poses` | CC0-1.0 | MakeHuman community | available, not used in the shipped assets |
| CMU Graphics Lab Motion Capture Database | "free for all uses ... may be copied, modified, or redistributed without permission" (NSF EIA-0196217) | Carnegie Mellon University Graphics Lab | walk / jog / run retarget sources and the idle base posture |

Every entry above has a SHA-256 and a source URL in `data/manifest/downloads.json`.
MPFB2's GPL code is *used* by this pipeline (a build-time tool); nothing GPL is redistributed inside the
exported `.glb`, whose geometry derives only from the CC0 base mesh and targets.

---

## 5. Blendshapes — all 52 ARKit channels exist, and all 52 now move something

The `faceunits01` functional pack contains exactly the ARKit-52 set for the hm08 base mesh, so all 52 are
realised as glTF morph targets:

```
browDownLeft        browDownRight       browInnerUp         browOuterUpLeft     browOuterUpRight
cheekPuff           cheekSquintLeft     cheekSquintRight    eyeBlinkLeft        eyeBlinkRight
eyeLookDownLeft     eyeLookDownRight    eyeLookInLeft       eyeLookInRight      eyeLookOutLeft
eyeLookOutRight     eyeLookUpLeft       eyeLookUpRight      eyeSquintLeft       eyeSquintRight
eyeWideLeft         eyeWideRight        jawForward          jawLeft             jawOpen
jawRight            mouthClose          mouthDimpleLeft     mouthDimpleRight    mouthFrownLeft
mouthFrownRight     mouthFunnel         mouthLeft           mouthLowerDownLeft  mouthLowerDownRight
mouthPressLeft      mouthPressRight     mouthPucker         mouthRight          mouthRollLower
mouthRollUpper      mouthShrugLower     mouthShrugUpper     mouthSmileLeft      mouthSmileRight
mouthStretchLeft    mouthStretchRight   mouthUpperUpLeft    mouthUpperUpRight   noseSneerLeft
noseSneerRight      tongueOut
```

They are loaded onto the body mesh **after** MPFB's macro targets are baked into it
(`TargetService.bake_targets`), so the exported morph list is these 52 and nothing else — no leaked
`african-male-young` or height targets.

### 5.1 `tongueOut` was a dead channel, and the test could not see it

The first pass claimed `test_blendshapes_actually_move_vertices` proved every channel displaces a vertex. It
proved nothing: it raised `KeyError: 'bufferView'` before reaching the assertion, because **Blender writes
every morph target as a sparse accessor**. A glTF accessor may omit `bufferView` entirely — the base data is
then all zeros and the real values live in a `sparse` block of (indices, values) — and a face blendshape that
moves a few hundred of 14 517 vertices is about fifty times smaller that way. The test's reader now decodes
sparse accessors (`Glb.accessor` / `Glb._read`), which is a fix to the reader, not to the assertion.

With the reader fixed, a real defect surfaced: **`tongueOut` moved nothing.** MakeHuman's `tongueOut.target`
displaces base-mesh vertices 13380-13605 — exactly the 226 vertices of the *helper tongue*, proxy geometry
that only exists so the real `tongue01` mesh can be fitted to it. `strip_helper_geometry` deletes those
vertices and Blender remaps the shape keys with them, so the channel survived by name with every delta zero.

`mh_build.transfer_tongue_morph` now copies the displacement onto the tongue mesh before the strip, each
tongue vertex taking the delta of the nearest helper-tongue vertex (the two meshes carry the same 226-vertex
fitted topology, so "nearest" is exact). **226 of 226 tongue vertices move.** The test now checks the union
over the file's meshes and asserts specifically that the tongue moves by more than a millimetre; a companion
test asserts the body still names all 52 channels in ARKit order.

Caveats, stated plainly:

* the four `eyeLook*` families move the **eyelid and periorbital skin only**; the eyeballs are separate
  objects and are rotated by the runtime, not by a morph;
* `tongueOut` is carried by the tongue mesh, not by the body — the body's channel of that name is a
  zero-delta placeholder that keeps the runtime's morph list a single 52-entry set;
* the targets are Mika Suominen's automatic ARKit derivation on hm08. They are correct in direction and
  usable for lipsync and expression, but they are not a hand-sculpted FACS set and there is no corrective
  shape between combinations.

---

## 6. The skeleton

71 bones, UE5-Mannequin naming, verified against `ue5_skeleton.ue5_parents()` in the exported glb:

```
root
 - pelvis
   - spine_01 -> spine_02 -> spine_03 -> spine_04 -> spine_05
       - neck_01 -> neck_02 -> head
       - clavicle_{l,r} -> upperarm -> lowerarm -> hand
           - thumb_01 -> thumb_02 -> thumb_03
           - {index,middle,ring,pinky}_metacarpal -> _01 -> _02 -> _03
   - thigh_{l,r} -> calf -> foot -> ball
ik_foot_root -> ik_foot_{l,r}                 (non-deforming)
ik_hand_root -> ik_hand_gun -> ik_hand_{l,r}  (non-deforming)
```

MPFB's `game_engine` rig is the UE4 mannequin set (53 bones) fitted to the actual body through the MakeHuman
joint helper cubes, so bone positions follow each character's macro targets. `rig_ue5.convert_to_ue5` then:

1. renames `Root` to `root`;
2. subdivides `spine_01 -> (spine_01, spine_02)`, `spine_02 -> (spine_03, spine_04)`, `spine_03 -> spine_05`,
   and `neck_01 -> (neck_01, neck_02)`, reparenting the children;
3. inserts a metacarpal from the wrist to each non-thumb knuckle;
4. adds the seven IK bones, each initialised on the FK bone it tracks;
5. **redistributes the skin weights**: the weights of a subdivided bone are split across its halves by the
   vertex's projection along the original bone axis through a smoothstep, and 0-60 % of each palm vertex's
   `hand_*` weight is moved to the nearest metacarpal (falloff over a 22 mm radius);
6. caps every vertex at its **4 strongest influences** and renormalises to a sum of exactly 1.

The cap is applied in Blender rather than left to the exporter, so the authored weights and the exported
weights are the same numbers — which is what `test_vertex_weights_sum_to_one` checks against the glb's own
`WEIGHTS_0` accessor, and no `WEIGHTS_1` set is emitted. `convert_to_ue5` reports **0 unweighted vertices**
on every mesh of every character built.

---

## 7. Clothing

Section 0 is the diagnosis; this is what the wardrobe *is* after it.

### 7.1 What the wardrobe is now

47 items in `wardrobe.WARDROBE`. Every top, bottom, jacket and shoe is a **real tailored MakeHuman CC0 mesh**
with a hem, a collar, sleeve seams, an armpit and a waistband, fitted by MPFB through the MakeClothes vertex
correspondences so it follows every macro target. Four mechanisms make those assets usable as an NYC
wardrobe:

* **Shell splitting** (`split_loose_parts`). A MakeHuman "suit" is one mesh holding several shells. Three
  modes: `all`; `upper`/`lower` by connected-component centroid; and `outer`, which keeps only the outermost
  upper shell (largest horizontal footprint, ignoring shells under a tenth the size of the largest so a
  collar scrap cannot win) and is how the field jacket comes off `male_casualsuit05` without the plaid shirt
  inside it. A per-vertex height cut was written for `male_casualsuit01`, whose shirt and jeans are one
  welded component, and then removed with the asset: the raw cut edge lands above the waistband on a short
  wearer and tears a gap across the midriff.
* **Tinting** (`tint`). The garment's own diffuse map carries the author's colour, so multiplying the
  wardrobe colour into it gives muddy hues. The map is reduced to luminance, normalised by its own mean,
  remapped into a 0.55-1.35 shading band and multiplied by the wanted colour — **baked into a new image**, in
  the image's own colour space. Baking rather than shader-nodding matters: glTF carries a base-colour texture
  and a factor, so a Mix/MapRange chain is dropped on export and the garment arrives in the engine in the
  asset author's colour. The first NPC line-up showed exactly that failure. The colour is a parameter, not a
  catalogue constant: the pedestrian variety vector's twelve top colours and twelve bottom colours are passed
  in per build (`finish_makehuman(..., colours=...)`).
* **Layer stand-off** (`push_along_normals`, section 0.3). Base 0, mid 4 mm, outer 11 mm, tapered to zero
  across three rings of every open boundary.
* **Layer resolve** (`resolve_layers`, section 0.5). The outer layer gets the last word, by closest point on
  its real surface.

### 7.2 Weights: taken from the body, not from MPFB's proximity fit

MPFB weights a fitted garment by proximity to the base mesh, which is wrong wherever two body parts are close
together: in the MakeHuman rest pose the hands hang beside the thighs, so trouser vertices pick up `hand_*`
and finger weights and the hand tears a hand-shaped hole through the trouser leg as soon as it moves.
`reweight_from_body` gives every garment vertex the weights of its nearest *body* vertex through a KD-tree,
so garments use MakeHuman's own anatomically-correct weighting and inherit the 4-influence, sum-to-one
normalisation `convert_to_ue5` has just applied.

**In the first pass this ran but did nothing** — section 0.2. It works now, and the proof is in the file: no
`*.001` vertex group survives on any garment, and no garment carries a group for a bone that is nowhere near
it (`sneakers_black` no longer has `neck_01`; `jacket_field` no longer has `foot_l`).

A second, unrelated cause of the same symptom was also fixed: the idle pose hung the hands 55 mm *inboard*,
which pushed them inside the trouser leg. They now hang 16 mm outboard of the thigh.

### 7.3 What is still procedural

The items MakeHuman has none of *and* which an offset shell can honestly stand in for: the ANSI hi-vis vest,
the Con-Ed orange vest, the insulated delivery vest, the hijab, the hood on the pullovers, the wristwatch, the
two extra hairstyles, the bags and the caps. (The puffers and long coats used to be here too; an offset shell
could not carry them and they are now the field-jacket mesh — section 12, gap 5.)

Each is cut as an offset of an existing surface. A vest covers nothing but the torso, so it is cut from **the
garment already on the body** — the outermost top or jacket — and inherits that garment's armpit and hem.
Anything whose region reaches past the torso would be cut from the body instead, because a layer can only be
as long and as sleeved as the surface it comes off; that rule is what the puffers and coats failed, in both
directions, before they became a MakeHuman mesh. The hijab leaves the face open by cutting the head region 35 mm in front of
the head joint.

### 7.4 The hood, and three attempts at it

MakeHuman's CC0 packs contain no hoodie, so the hood on `hoodie_grey`/`hoodie_black`/`kids_hoodie` is
procedural. Three shapes were built and each was judged on a rendered close-up of the character's back before
the next was written:

1. **a half-ellipsoid placed from the neck joint** — the back panel of a fitted sweater is 100-140 mm behind
   the neck joint, and by a distance that depends on the body, so most of the hood ended up *inside* the
   sweater and what showed was a faceted grey ball and a few fragments;
2. **the same ellipsoid projected outwards onto the garment surface** — projecting every vertex flattens the
   volume away and leaves a crumpled skin-tight patch;
3. **a swept collar roll**, which is what ships. The collar line is found by ray-casting horizontally inwards
   at collar height on thirteen directions spanning ±86° from straight back (a *closest point* query from out
   at the side returns the top of the shoulder, and the roll then spans the shoulders like a yoke), and a
   tube of 44 mm radius at the nape tapering to 24 mm at the ends is swept along those points, standing off
   along each point's own surface normal. Its loops take their UVs from the nearest garment vertex, so it is
   shaded by the same knit texture and needs no material of its own, and it is weighted 55/45 to
   `neck_01`/`spine_05`.

**Gap:** the garments have no zips, buttons, plackets or cloth simulation, and the vests have no seams. `bmesh.ops.solidify` was tried on the MakeHuman garments to give them fabric thickness and had
to be reverted — the CC0 meshes contain loose edges and coincident vertices that make it fan out spikes at the
shoulder and hip (`thicken()` is kept in the module, unused, with that recorded).

### 7.5 The shoes are what the render says they are, not what the file is called

`shoes01`-`shoes06` were fitted to the same foot and rendered at 300 px to see what each one *is*, because
the first pass took `shoes03` for boots and `shoes02` for loafers on the strength of nothing. They are:
`01` a slip-on dress shoe, `02` and `06` trainers, `03` a chunky slip-on work shoe, `04` a lace-up oxford,
`05` a trainer. Every one comes with its own sock, which is why a pedestrian in short trousers shows white
socks. The six footwear levels are named accordingly.

**Gap:** MakeHuman's CC0 packs contain **no boots**. There is no work boot, no Chelsea boot and no winter
boot in a city that wears all three; the wardrobe says "slip-on work shoes" rather than pretending.

### 7.6 What the player wears

`tee_white`, `jeans_indigo`, `hoodie_grey` (with the procedural hood down on his back), `sneakers_black`, and
a procedural steel watch on the left wrist whose strap radius is measured from his own forearm vertices. The
build removes 2 819 of his 13 380 body vertices as covered skin and moves 2 487 garment vertices in the layer
resolve.

Two torso layers, not three. `push_along_normals` can stand one fitted layer off another cleanly, but three
MakeHuman torso shells fitted to the same body cannot all clear each other, and the middle one is the one
that then shows through the outer one. The field jacket is in the wardrobe and on NPCs; on the player it
would have been a third shell.

---

## 8. Animations — 25 clips at 30 fps, method per clip

`walk`, `jog` and `run` are retargeted CMU motion capture. Everything else is authored.

### 8.1 Which CMU trial drives what, and why

The nine downloaded AMC files were **measured**, not assumed, by running the forward-kinematics solver over
each and taking the mean horizontal root speed (`asf_amc.root_speed_mps`, 10 % trimmed at each end):

| trial | frames | duration | mean root speed | peak foot lift | used as |
|---|---|---|---|---|---|
| 02_01 | 343 | 2.86 s | 1.18 m/s | 0.140 m | — |
| 02_02 | 298 | 2.48 s | 1.64 m/s | 0.174 m | — |
| 02_03 | 173 | 1.44 s | 2.65 m/s | 0.257 m | — |
| **07_01** | 316 | 2.63 s | **1.38 m/s** | 0.157 m | **walk**, and the idle base posture |
| 07_12 | 245 | 2.04 s | 1.93 m/s | 0.174 m | — |
| **09_01** | 148 | 1.23 s | **3.64 m/s** | 0.423 m | **run** |
| **16_35** | 162 | 1.35 s | **2.82 m/s** | 0.304 m | **jog** |
| 35_01 | 358 | 2.98 s | 1.28 m/s | 0.123 m | — |
| 35_17 | 167 | 1.39 s | 3.16 m/s | 0.236 m | — |

`test_measured_clip_speeds_match_the_documented_assignment` re-measures the three chosen trials on every test
run, so this table cannot drift away from the data.

### 8.2 How the retarget works

Rotation deltas in world space, conjugated by the yaw that aligns the subject's travel direction with the
character's forward axis:

```
delta_i(f) = A . (R_src_i(f) . R_src_i(rest)^-1) . A^-1
R_tgt_i(f) = delta_i(f) . R_tgt_i(rest)
```

Only each skeleton's *change from its own rest pose* is transferred, so the CMU subject's shoulder width,
limb proportions and rest arm angle never leak into the MakeHuman body. On top of that:

* CMU's three spine bones fan out to five (`spine_02` and `spine_04` are slerps of their neighbours' deltas)
  and its `lowerneck`/`upperneck` map to `neck_01`/`neck_02`;
* CMU's single `lfingers`/`rfingers` curl channel drives all twelve finger phalanges, and the two-axis
  `lthumb`/`rthumb` drives the thumb;
* pelvis height above the floor is transferred as a **ratio of leg length** (target 0.879 m against source
  0.809-0.861 m), so the feet neither float nor sink;
* horizontal travel is removed — the clips are in place, with the ground speed recorded in the metadata —
  while the lateral sway and vertical bob are kept and scaled by the same leg ratio;
* the clip is cut at a left heel strike (detected as a local minimum of the foot's height above the floor)
  to the next one, and resampled so the last frame equals the first.
  `test_loop_clips_start_and_end_on_the_same_pose` checks every looping clip's first and last glTF key agree
  to 2e-3.

### 8.3 Speed matching, with the honest numbers

| clip | source | source speed | on a 0.879 m leg | playback rate | delivered | cycle |
|---|---|---|---|---|---|---|
| walk | CMU 07_01 | 1.383 m/s (0.809 m leg) | 1.50 m/s | 1.071x | **1.4 m/s** | 28 frames / 0.93 s |
| jog | CMU 16_35 | 2.820 m/s (0.836 m leg) | 2.96 m/s | 1.056x | **2.8 m/s** | 26 frames / 0.87 s |
| run | CMU 09_01 | 3.636 m/s (0.861 m leg) | 3.70 m/s | **0.740x** | **5.0 m/s** | 17 frames / 0.57 s |

Walk and jog land within 7 % of their source cadence — those are honest retargets.

**`run` is not.** None of the fourteen downloaded CMU files is a 5 m/s sprint; the fastest is a 3.6 m/s run.
Reaching the 5 m/s spec by time compression alone means the clip is played 1.35x faster than it was captured:
stride *length* is that of a 3.6 m/s run, and cadence is therefore 35 % higher than a real 5 m/s runner's
(0.57 s per stride, about 210 steps/min, against roughly 180 for a real 5 m/s run). It reads as a fast run,
not as a sprint. The fix is a genuine sprint capture; the clip metadata carries `time_scale` and
`equivalent_speed_mps` so the runtime can instead play it at its natural 3.70 m/s.

### 8.4 The idle

**There is no idle in the downloaded CMU set.** All nine AMC files are pure locomotion: the minimum 0.25 s
rolling root speed across all of them is 1.03 m/s, and no clip contains a standing window. So the idle is a
**hybrid**, and it is labelled as one in the glb (`method: "hybrid: mocap standing posture + procedural
breathing/weight-shift"`):

* the **posture** is real mocap — the circular quaternion mean of every bone over one whole gait cycle of the
  retargeted 07_01 walk. Averaging a full cycle cancels the forward and backward halves of each swing, so the
  legs come under the hips and the arms hang, while the subject's actual spine, neck and shoulder carriage
  survive. The residual 16.6 degrees of walking head-down pitch is measured against the rest pose and 80 % of
  it is removed across `neck_01`/`neck_02`/`head` in a 25/30/45 split;
* the feet are then planted with analytic IK (flat on the ground, 7 degrees toe-out) and the fingers put in
  a resting curl (17/26/18 degrees per phalanx, curl direction *measured* on the rig, not assumed);
* the **motion** is authored: 45 breaths/min on the spine, a plus/minus 11 mm lateral weight shift, and a
  slow head drift.

### 8.5 Every clip, with its method

| clip | frames | s | loop | method | notes |
|---|---|---|---|---|---|
| `walk` | 28 | 0.93 | yes | **cmu-mocap-retarget** | CMU 07_01 to 1.4 m/s |
| `jog` | 26 | 0.87 | yes | **cmu-mocap-retarget** | CMU 16_35 to 2.8 m/s |
| `run` | 17 | 0.57 | yes | **cmu-mocap-retarget** | CMU 09_01 to 5.0 m/s (time-compressed, 8.3) |
| `idle` | 121 | 4.00 | yes | **hybrid** mocap posture + procedural motion | see 8.4 |
| `idle_phone` | 121 | 4.00 | yes | procedural-keyposed | phone 0.30 m in front of the sternum, head 28 deg down |
| `look_around` | 151 | 5.00 | yes | procedural-keyposed | head yaw -48 to +40 deg, 55/28/17 % across head/neck_02/neck_01 |
| `hail_cab` | 79 | 2.60 | yes | procedural-keyposed | right arm to 86 % of arm length above the shoulder, two waves |
| `lean_on_car` | 121 | 4.00 | yes | procedural-keyposed | hip on the belt line, arms folded, weight on the left leg |
| `umbrella_hold` | 91 | 3.00 | yes | procedural-keyposed | NPC pose; vertical grip 0.18 m above the right shoulder |
| `turn_left_90` | 29 | 0.93 | — | procedural-on-mocap-gait | root yaws +90 deg over one full walk cycle, 16 deg torso lead |
| `turn_right_90` | 29 | 0.93 | — | procedural-on-mocap-gait | as above, -90 deg |
| `stairs_up` | 29 | 0.93 | yes | procedural-on-mocap-gait | 0.18 m riser / 0.28 m tread, torso +9 deg |
| `stairs_down` | 29 | 0.93 | yes | procedural-on-mocap-gait | same geometry, torso -5 deg |
| `phone_walk` | 28 | 0.90 | yes | procedural-on-mocap-gait | `idle_phone` upper body blended 88 % onto the walk |
| `open_car_door` | 53 | 1.73 | — | procedural-keyposed | right hand to the real handle, 0.30 m pull, 0.14 m step back |
| `enter_car` | 79 | 2.60 | — | procedural-keyposed | roof rail, sill, right foot in, hips to the H-point |
| `sit_drive_idle` | 91 | 3.00 | yes | procedural-keyposed | **hands at nine and three** on the real rim, +/-2.2 deg correction |
| `drive_steer_left` | 2 | — | — | procedural-keyposed **(additive)** | frame 0 neutral, frame 1 = +110 deg of rim rotation |
| `drive_steer_right` | 2 | — | — | procedural-keyposed **(additive)** | as above, -110 deg |
| `drive_shift` | 33 | 1.07 | — | procedural-keyposed | right hand to the console knob and back |
| `drive_shoulder_check_left` | 37 | 1.20 | — | procedural-keyposed | head +78 deg, torso +26 deg |
| `drive_shoulder_check_right` | 37 | 1.20 | — | procedural-keyposed | head -78 deg, torso -26 deg |
| `drive_mirror_check` | 31 | 1.00 | — | procedural-keyposed | head -20 deg, torso -5 deg |
| `exit_car` | 69 | 2.27 | — | procedural-keyposed | time-reverse of `enter_car`, 13 % quicker |
| `close_door` | 43 | 1.40 | — | procedural-keyposed | left hand on the inner door edge, 0.30 m swing |

The procedural clips are not hand-typed Euler angles: limb poses are given as **world-space targets** and
solved with the analytic two-bone IK in `pose_solver.py`, and the targets for every car clip are read out of
the vehicles lane's own export (8.6). "Hands at nine and three" is literally a point on the exported rim.

### 8.6 The driver package, read from the sibling lane

`car_ref.py` parses `blender_out/vehicles/fusion_hybrid.glb` (ADR-009's Ford Fusion Hybrid) directly and
converts glTF Y-up back to Blender Z-up. In the car's frame (origin = ground under the rear-axle centre,
+X forward, +Y left):

| point | value | how |
|---|---|---|
| steering-wheel centre | (2.280, 0.375, 0.865) m | `SteeringWheel` node translation |
| steering-wheel rim radius | 0.2015 m (0.403 m diameter) | max radius of the node's own vertices |
| column axis | (-0.906, 0, 0.423), a 25 deg rake | the node's rotation applied to its local +Z |
| shifter knob | (2.200, 0.000, 0.666) m | `Shifter` mesh bounding-box centre |
| driver door handle | (2.100, 0.902, 0.860) m | the front-left cluster of the `Handles` mesh |
| SAE H-point | (1.754, 0.375, 0.800) m | `Seat_FL` bbox: 42 % of cushion depth, 0.10 m above the cushion |
| heel point | (2.840, 0.449, 0.294) m | `Pedals` bbox |

The glb records `extras.nycsim.car_attach.socket_car_local_m = [1.7537, 0.375, 0.0]`: put the character's
origin there, aligned with the car's +X, and the seated clips line up with the real interior. If the vehicle
glb is missing, `car_ref` falls back to published Fusion interior dimensions and stamps
`driver_package.source = "published"` so it is visible in the catalog.

---

## 9. NPC system — built from the pedestrian simulation's variety contract

The traffic lane finished after the first character pass and **fixed the pedestrian variety vector as a
contract** (`docs/verification/traffic/REPORT.md` §7): twelve floats in `[0, 1]`, each with a fixed number of
quantisation levels, in this order.

| # | dimension | levels | # | dimension | levels |
|---|---|---|---|---|---|
| 0 | age band | 4 | 6 | top garment | 10 |
| 1 | stature | 6 | 7 | top colour | 12 |
| 2 | body mass | 6 | 8 | bottom garment | 8 |
| 3 | skin tone | 8 | 9 | bottom colour | 12 |
| 4 | hair style | 10 | 10 | footwear | 6 |
| 5 | hair colour | 8 | 11 | accessory | 10 |

4·6·6·8·10·8·10·12·8·12·6·10 = **63 700 992 000** distinguishable appearances — the figure the traffic report
quotes. `variety.py` was rewritten to consume exactly this; the previous, locally-invented 12-byte encoding
(`body_preset, skin_tone, hair, top, bottom, shoes, outerwear, bag, hat, glasses, height_scale, walk_style`,
12 uint8 indices into locally-defined tables)
is gone, and with it the 24 fixed body presets it depended on. `tests/test_character.py` carries its own copy
of the twelve dimensions and level counts, transcribed from the traffic report, and asserts the module and
the shipped manifest both match it — so neither side can drift silently.

**Decoding.** `level = clamp(floor(v · levels), 0, levels-1)`. That inverts both encodings a producer might
reasonably use, `k/(levels-1)` and the bin centre `(k+0.5)/levels`; the test checks both for every level of
every dimension.

**The two things the vector does not carry, resolved rather than invented.**

* *Sex.* There is no sex dimension. Each of the ten hairstyles carries the sex it is worn by
  (`variety.HAIR_STYLES`); the two unisex styles (short curly, afro) resolve from the parity of the stature
  and body-mass levels, so the result is deterministic in the vector alone and both sexes appear.
* *Gait.* Activity comes from the simulation, so the vector carries no walk style. The playback rate of the
  shared locomotion clips and a spinal lean come from the age band and the body mass (`variety.gait_for`):
  ×1.10 for a child down to ×0.78 for the older band (a healthy adult walks about 1.4 m/s, an over-65 about
  1.1 m/s), further scaled ×1.02 to ×0.88 across the six mass levels, with 1° to 8.5° of forward lean.

**Stature is the simulation's own number, and it is solved for.** `core/include/nycsim/peds/Variety.h`
does not just carry dimension 1 — it *computes a height from it*: `heightMetres() = 1.50 + v[1] · 0.45`,
scaled by 0.72 for the child band, on the raw float rather than the quantised level. That is the number the
simulation steps its agents with, so it is the number the mesh is built to; a pedestrian whose mesh is
1.60 m while the simulation believes it is 1.85 m would be worse than any independent height model.
`variety.contract_height_m` implements exactly that formula and
`test_stature_follows_the_simulations_own_height_formula` pins it against the header.

**Two limitations of the contract's formula are reported, not silently corrected.** It has no sex term (men
and women of the same stature level come out the same height, where the real difference is 12-13 cm) and it
does not shorten the older band (real over-65s are 4-7 cm shorter). `variety.AGE_BANDS[...]["anthropometric_m"]`
carries what real anthropometry would ask for and every NPC's entry in `npc_variety.json` records both
`target_height_m` (built) and `anthropometric_height_m` (reference), so the difference is visible. **Proposed
change for the peds agent:** give `heightMetres()` a sex term and an ageing term; this lane will follow it.

**Getting to that height needed a solver, not a table.** Feeding the stature dimension straight into MakeHuman's `height`
macro produced a **1.71 m "child"** and a **2.05 m pedestrian** in the first generation run. All 4 × 6 × 2 (band × stature × sex) combinations were then built and measured; the MakeHuman
macro-to-stature response is linear per band and sex:

| band | sex | height at macro 0.24 | height at macro 0.90 | slope (m per unit macro) |
|---|---|---|---|---|
| child | M / F | 1.185 / 1.105 m | 1.809 / 1.730 m | 0.945 / 0.947 |
| young adult | M / F | 1.486 / 1.374 m | 2.192 / 2.080 m | 1.070 / 1.070 |
| middle-aged | M / F | 1.543 / 1.428 m | 2.272 / 2.156 m | 1.105 / 1.103 |
| older | M / F | 1.529 / 1.420 m | 2.257 / 2.148 m | 1.103 / 1.103 |

Inverting that table was still not enough: the macro that delivers a given stature also depends on the
**weight, muscle and ethnic macros**, which are three more contract dimensions, and the next generated cast
still spread over 13 cm at a fixed macro — a 1.44 m adult among them. So the macro is **solved for**:
`npc_generator.solve_height_macro` builds a naked probe body (no clothes, hair, teeth or eyes — about 1.5 s),
measures it, and corrects the macro by a secant slope until the measurement is within 8 mm of the target.
`test_npc_statures_hit_the_metres_the_contract_asked_for` re-checks every NPC against its own target from the
shipped manifest, so this cannot drift.

**Wardrobe mapping.** The contract's ten top-garment levels are *looks*, not meshes — a base top plus an
optional layer over it — because that is what an upper body looks like: tee, tank, polo, button-down, scrubs,
long-sleeve, knit, hoodie, field jacket over a tee, and a suit jacket (which carries its own shirt and tie in
the same shell, so no separate top goes under it). Eight bottoms are eight different *cuts* (the colour is a
dimension of its own), six footwear levels are five different shoe meshes (`shoes05` twice, in white and in
black), and the ten accessory levels are
nothing, five carried items, glasses, two hats and the ANSI hi-vis vest. **26 of the 47 wardrobe items are
reachable** from the contract; the other 21 are colourways the colour dimensions make redundant (`tee_black`,
`jeans_black`, `hoodie_black`, the second sneakers) plus the items no dimension has a slot for (the Con-Ed
vest, the insulated delivery vest, the hijab, the tourist tee, the four children's items). They stay in the
catalogue for the simulation to reach if the contract grows, and `npc_variety.json` lists exactly which are
reachable so the two sides can see the difference.

**The generated cast covers the space.** A hash of 24 seeds leaves whole levels unused — with 24 draws the
chance of covering all twelve colours is negligible, and a cast that never wears half the wardrobe is not
evidence the wardrobe works. `variety.spread_vectors` walks each dimension as its own rotated cycle with a
stride coprime to its level count, so every level of every dimension appears within the first `levels` draws.
`test_generated_cast_exercises_every_contract_level` asserts it against the shipped manifest.

**The 24 shipped pedestrians.** 6 per age band, 14 female and 10 male, statures **1.153 m** (an eight-year-old
girl) to **1.903 m** (a middle-aged man), adults 1.511-1.903 m, all ten top looks, all ten accessory levels
and all six footwear levels worn at least once. Every one hits its own stature target: the largest error over
the cast is **8.5 mm**, the mean 3.1 mm, at a mean of 3.0 probe builds. 12-14 meshes and 18 835-30 206
vertices each; 14.4-31.4 MB per glb, **496 MB** for the cast, which is dominated by the 25 shared animations
and the 52 morph targets each file carries its own copy of. Across the cast the contract's height formula and
real anthropometry differ by 64 mm on average and 179 mm at worst, which is the size of the sex and ageing
terms the formula is missing.

**One skeleton, one clip set.** Every NPC carries the same 71 bones, the same 52 blendshapes and the same 25
clips including `umbrella_hold` and `phone_walk`; `test_npcs_share_one_skeleton_and_the_same_clips` asserts a
single distinct clip set across all 24.

**A broken garment can no longer ship.** `wardrobe.verify_outfit` checks every finished garment against the
body's own bounding box grown by 300 mm and rejects non-finite coordinates, and the build raises if anything
fails. This was written because the first run of the new generator produced a **2.51 m pedestrian**:
`bmesh.ops.solidify` on the hi-vis vest, cut from a fitted sweater whose CC0 mesh has coincident vertices and
inconsistent winding, fanned out spikes 2.3 m tall and 4.0 m deep, and the exported bounding box quietly
absorbed them. `build_garment` now cleans the cut (remove doubles, dissolve degenerates, drop loose vertices,
recalculate normals) and compares the bounding box before and after `solidify`; if the mesh grew by more than
eight times the intended thickness it ships the single-sided shell instead and says so in the log.

---

## 10. Verification renders

Cycles CPU, 64 samples for the mandated stills and 20-48 for the contact sheets, three-point area lighting on
a neutral backdrop for the portraits and two suns for the line-up (ADR-012). `NYCSIM_RENDER_PREVIEW=1` renders the same compositions at 34 % scale and 10
samples; framing and pose iterations were done there, and only the final pass at full quality.

| file | what it shows |
|---|---|
| `face_closeup.png` | three-quarter portrait: subsurface skin, split eyeball/cornea with the tagged iris, `eyelashes02`, `eyebrow006`, the hair cards |
| `full_body.png` | front and back of the dressed player (the character is turned 180 degrees between the two, so both halves are lit identically) |
| `walk_strip.png` | eight evenly spaced frames of one retargeted walk cycle, side on |
| `bend_test.png` | elbow (top row) and knee (bottom row) at 0/45/90/120 degrees, the **dressed** character clay-shaded |
| `blendshapes.png` | six ARKit face units at full weight |
| `detail.png` | left hand and left foot at 460 px each: modelled fingers with nails and knuckles, and the sneaker with its sole line, toe cap and stitching |
| `npc_lineup.png` | twelve of the twenty-four generated pedestrians side by side, imported from their exported `.glb` files rather than from the build scene |

The renders were opened and acted on, not just produced - and after each orchestrator review, opened again.
Eleven defects were found in the first pass this way and fixed:

1. the first idle stood in a mid-stride pose with the legs splayed - the standing posture was being averaged
   over double-support frames only; it now averages a whole gait cycle, levels the head and plants the feet
   with IK;
2. the wristwatch was a 0.45 m hoop around the whole body - its strap radius was being measured from *every*
   body vertex in the wrist plane instead of the forearm's;
3. the first bend test rendered black because the camera was on the far side of the body from the left limb,
   and the joints did not flex visibly; the camera is now outboard of the limb, the arm is abducted 55
   degrees, and the flexion direction is *measured* per rig (`_flexion_sign`) rather than assumed;
4. three coincident garment shells read as one shapeless mass, and a ring of bare skin showed at the waist
   where no garment's bone region covered the pelvis;
5. the walk strip and the face close-up were both cropped; the face camera now targets the **nose tip found
   from the mesh** rather than a fixed offset from the head bone;
6. the character walked 3.4 degrees off its own facing, because the forward axis was taken from the left toe
   bone alone; it is now the mean of both toe bones, which is exactly -Y;
7. **the whole clothing approach was wrong** and was rebuilt on the MakeHuman tailored garments (section 7);
8. **the character floated**: transferring pelvis height as a ratio of leg length leaves a constant offset,
   because the CMU subject's ankle-to-sole distance is not this character's. `ground_clip` now measures the
   lowest ankle over the finished cycle and plants it - the correction was 128, 150 and 134 mm for walk, jog
   and run respectively, which is exactly the hover the walk strip showed;
9. the hands were splayed flat, because CMU's single finger-curl channel barely moves the MakeHuman rest
   hand; the resting curl is now composed onto the mocap clips at 60 %;
10. garment colours were correct in Cycles but arrived in the glb as the asset authors' originals, because a
    shader-node tint does not survive glTF export - the tint is now baked into the texture (section 7.1);
11. the card hair, brows and lashes exported as opaque quads - a braid rendered as a white spike in the first
    NPC line-up - because MPFB leaves the texture's alpha unconnected; `setup_alpha_materials` links it and
    sets a clip threshold so the exporter emits `alphaMode: MASK`.

The bend test after the rebuild shows a clean elbow and knee through 0/45/90/120 degrees: no candy-wrapping,
no collapse, and the limb keeps its volume. There is mild volume loss on the inside of the elbow and behind
the knee at 120 degrees, which is what four-influence linear blend skinning does without corrective shapes.

### 10.1 The second review pass

The renders were opened again after the orchestrator's second review, and this time the diagnosis came from
**rendering the character one layer at a time** rather than from staring at the finished frame (section 0).
Six further defects were found on a render and fixed:

12. the "bomber jacket" was a crude long-sleeve tee shell inflated 24 mm — the balloon (0.1);
13. every garment was still deforming with MPFB's proximity weights, because the corrected weights had gone
    into `bone.001` groups the armature ignores (0.2);
14. the 24 mm stand-off saw-toothed every open boundary, which is the jagged collar (0.3);
15. the whole foot stayed inside the sneaker, which is the torn "flipper" (0.4);
16. the hood was a faceted grey sphere on the back; three shapes were built and judged on a close-up before
    one read (7.4);
17. the hi-vis vest blew up to 2.3 m tall under `bmesh.ops.solidify` and produced a 2.51 m pedestrian in the
    first run of the new NPC generator (section 9).

`bend_test.png` now clay-shades the **dressed** character rather than the bare skin: the skin under the
clothes is deleted at build time, so a skin-only render is full of holes, and what has to bend correctly is
the sleeve and the trouser leg that ship. Through 0/45/90/120 degrees the sleeve keeps its cuff and creases
at the elbow and the trouser leg holds volume at the knee with thigh-to-calf contact at 120 degrees; there is
no candy-wrapping and no collapse. Mild volume loss on the inside of the elbow and behind the knee at 120
degrees is what four-influence linear blend skinning does without corrective shapes.

---

## 11. Tests

`python3 -m pytest tests/test_character.py -q`

The suite reads the exported artefacts, not the generator: it parses `player.glb`'s JSON and BIN chunks
itself — including **sparse accessors**, which is what morph targets are written as — and checks the bone set
and hierarchy, the seven IK bones, the full finger chain including metacarpals, the `asset.extras.nycsim`
block required by DATA_CONTRACTS §13, every required animation name, 30 fps key spacing, loop closure, the
additive flags, the 52 morph target names, that every channel actually moves vertices somewhere in the file
and that the tongue really comes out, that skin weights sum to 1 with at most four influences and reference
valid joints, the player's measurements, and that his home BIN is residential in `buildings_base.parquet`.

The pedestrian contract has its own tests that need neither Blender nor the exported assets, because
`variety.py` is plain Python (it imports `wardrobe`, and therefore `bpy`, lazily): the twelve dimensions and
their level counts are transcribed into the test file from `docs/verification/traffic/REPORT.md` §7 and
checked against the module, the appearance-space size is checked to be 63 700 992 000, quantisation is
checked to invert both plausible encodings at every level of every dimension, and every level of every
dimension is decoded and its outfit checked for exactly one bottom, exactly one pair of shoes, no item worn
twice, no colour override for an item not worn and a plausible gait. Against the shipped manifest it then
checks that the published contract matches, that the generated cast exercises every level of every
dimension, that each NPC's twelve floats re-decode to the levels and the outfit that were actually built,
that all 24 share one skeleton and one clip set, and that their statures span a real population.

The ASF/AMC parser keeps its own unit tests (bone-length invariance under FK, the rest pose being a standing
human, the Euler convention matching Blender's, the Y-up to Z-up swap being a proper rotation).

### 11.1 The two failures the review reported, and what was actually wrong

**`test_animations_are_30fps_and_non_trivial`** — every glTF key was 0.041667 s apart, i.e. 1/24. Nothing set
the scene frame rate, so it stayed on Blender's 24 fps default; the clips are baked one key per frame and the
exporter converts a key's frame number to seconds with the *scene* rate, so a "30 fps" clip shipped 25 % slow
and every documented ground speed with it. `anim_lib.set_scene_fps` now sets 30 at build time (so the saved
`.blend` agrees) and again inside `export_character` (so the `.glb` agrees whatever opened the file). Key
spacing is now 1/30 s to within 1e-6.

**`test_blendshapes_actually_move_vertices`** — `KeyError: 'bufferView'`. Section 5.1: the reader could not
decode sparse accessors, and behind that failure sat a genuinely dead `tongueOut` channel. Both are fixed;
neither assertion was relaxed, and the blendshape test is now strictly stronger than before (it additionally
requires the tongue to move more than a millimetre, and a second test pins the body's channel list to the
ARKit set in ARKit order).

---

## 12. Honest gaps

1. **Hair is card/mesh hair, not strands.** The ten MakeHuman styles are alpha-textured polygon cards
   (1 011-5 203 vertices) plus two procedural shells. At a distance and in silhouette they are fine; at
   portrait range they read as cards, with no flyaways, no strand-level shading and no anisotropic highlight.
   Real strand hair (Blender curves to a UE groom) was not attempted: no CC0 groom asset was reachable, and
   an authored groom is a multi-day job. **This is the single biggest fidelity gap in the lane.** The rig and
   the scalp are ready for a groom to be attached later; `wardrobe.build_procedural_hair` shows where a scalp
   shell attaches.
2. **`run` is a time-compressed 3.6 m/s run, not a 5 m/s sprint** (8.3), with the numbers in the metadata.
3. **The idle's motion is authored**, only its posture is mocap (8.4) — there is no idle capture in the
   fourteen downloaded CMU files.
4. **Garments have no zips, buttons, plackets or cloth simulation.** The wardrobe is 43 real tailored
   MakeHuman meshes and 4 procedural items (three work vests and the hijab, all torso-only cuts of the
   garment already on the body).
5. **MakeHuman's CC0 packs contain one casual jacket and no puffer, no long coat and no hoodie.**
   `jacket_field`, `jacket_denim`, `jacket_leather`, `puffer_black`, `puffer_olive`, `puffer_red_long`,
   `coat_wool` and `coat_trench` are therefore all `male_casualsuit05` — a four-pocket field jacket — in
   eight fabrics, at stand-offs from 11 to 22 mm. They read correctly as jackets and coats at street
   distance, but **a "long" coat is hip-length, not knee-length**, and a puffer has no quilting.
   Both alternatives were built and rejected on the render: cut from the tee underneath, a "trench coat"
   comes out as a beige t-shirt; cut from the skin with sleeves and a hem it comes out as a painted-on
   body-suit. The hood is procedural and is a bunched collar roll (section 7.4), not a hood you could put up.
6. **No boots.** MakeHuman's CC0 packs have none, so a city that wears work boots, Chelsea boots and winter
   boots is shod in trainers, oxfords, loafers and one chunky slip-on work shoe. The six footwear levels are
   five distinct meshes: `shoes05` appears twice, in white and in black.
7. **The carried items are bevelled boxes.** A backpack, tote, shoulder bag, courier's box and briefcase are
   each one box, scaled to the wearer and placed against the body surface by ray-cast, weighted rigidly to
   one bone. They read at street distance and are wrong close up: no straps, no handles, no soft shape.
8. **No facial rig beyond blendshapes.** There are no jaw or eye bones; the eyes are separate objects the
   runtime must rotate, and jaw motion is the `jawOpen`/`jawLeft`/`jawRight`/`jawForward` morphs only.
9. **No LODs and no cloth/hair physics.** One mesh level per part; the player is about 38 k vertices across
   15 meshes, an NPC 18-30 k. LOD generation and a UE cloth setup are runtime-side work.
10. **Subsurface skin is authored, not previewable in glTF.** The Principled subsurface weight and radius are
    set for Cycles and written into `extras.nycsim.skin` for the UE material; glTF itself has no SSS, so a
    glTF viewer shows flat diffuse skin.
11. **The `eyeLook*` blendshapes move only the lids, and `tongueOut` is carried by the tongue mesh** (5).
12. **The contract's height formula has no sex term and does not shorten the older band** (9). This lane
    builds to the simulation's number rather than to anthropometry, and reports the difference: 64 mm on
    average and 179 mm at worst across the shipped cast.
13. **Two 5 mm scraps of the tee's hem still show through the seat of the player's trousers** on the back
    view. `resolve_layers` moves 2 487 vertices and leaves those two; a fourth pass clears them but the cast
    would have to be regenerated to keep the code and the shipped assets in step, so it is recorded rather
    than half-applied.
14. **Character forward is -Y in Blender**, recorded as `extras.nycsim.forward_axis_blender`. That is
   MakeHuman's native orientation, kept because rotating a shape-keyed, skinned, multi-mesh character risks
   more than it gains; the UE import must apply the +X convention. This differs from the vehicles lane, which
   exports +X forward, and the orchestrator should make the import script aware of it.
15. **The car clips assume the exported Fusion Hybrid.** If the vehicles lane re-exports with different
    interior geometry the seated clips need rebuilding; the numbers used are recorded in the catalog so the
    drift is detectable.
16. **Facial identity is MakeHuman's**, driven only by the macro targets — no custom head sculpt, so the
    player's face is a plausible 34-year-old rather than a designed, memorable one.

---

## 13. What the next agent needs to know

* The glb is at `blender_out/character/player.glb`, Y-up (glTF), metres, origin on the ground between the
  feet, **facing -Y in Blender space** (`extras.nycsim.forward_axis_blender`).
* Animation names are stable and are the contract: the 25 in 8.5. Two are additive
  (`drive_steer_left/right`): frame 0 is the neutral reference, frame 1 the full-lock pose; the runtime
  should difference them against `sit_drive_idle`.
* The seated clips need the character's origin at `extras.nycsim.car_attach.socket_car_local_m` in the car's
  frame — `[1.7537, 0.375, 0.0]` for the Fusion.
* `blender_out/character/npc_variety.json` publishes the **pedestrian appearance contract as this lane
  consumes it**: the twelve dimensions and their level counts exactly as `docs/verification/traffic/
  REPORT.md` section 7 fixes them, the table each level indexes, which wardrobe items are reachable, and
  every generated NPC's twelve floats with what they decoded to. The simulation produces the vector; this
  lane consumes it. The first pass invented its own 12-byte encoding when `core/peds` was empty - that is
  gone.
* **Two dimensions the vector does not carry are derived here**: sex from the hairstyle table (with the
  two unisex styles resolved from the parity of stature + body mass) and the locomotion playback rate
  from the age band and body mass. If the simulation ever wants to own either, they become dimensions 13
  and 14 and `variety.py` drops its derivation.
* Every character is 4-influence skinned with weights summing to exactly 1, so UE's default skinning limit
  needs no re-weighting on import.
* Rebuild commands:
  `python3 blender/character/build_character.py` (about 20 s),
  `python3 blender/character/npc_generator.py --count 24` (about 12 min; each NPC costs two to four
  extra 1.5 s probe builds while its stature is solved for),
  `python3 blender/character/render_verify.py all` (about 50 min at 64 samples on this contended 4-vCPU box;
  set `NYCSIM_RENDER_PREVIEW=1` for a two-minute pass).
