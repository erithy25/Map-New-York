# Stage report — character (player + NPC system)

**Lane:** `blender/character/`, `blender_out/character/`, `docs/verification/character/`, `docs/CHARACTER.md`,
`tests/test_character.py`
**Engine:** Blender 4.5.13 LTS as the `bpy` Python module, CPU only. MPFB2 2.0.17 driven headless.
**Date:** 2026-09-06

---

## 1. What was built

| Artefact | Content |
|---|---|
| `blender_out/character/player.glb` | Nikos Vlahos: 71-bone UE5-Mannequin rig, 16 skinned meshes, 52 ARKit morph targets, 25 glTF animations at 30 fps |
| `docs/verification/character/detail.png` | hand and foot close-ups - added after the orchestrator's review, because the two places a body most obviously fails cannot be judged in a full-figure shot |
| `blender_out/character/player.blend` | the scene the verification renders open (no rebuild) |
| `blender_out/character/catalog/player.json` | bones, per-clip metadata, measurements, asset licences, driver package |
| `blender_out/character/npc/npc_*.glb` | 24 pedestrians, one per base body, same skeleton and same clip set |
| `blender_out/character/npc_variety.json` | the 12-dimensional variety contract, the 40-item wardrobe, the 12 hairstyles, and every generated NPC's vector |
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
blender/character/wardrobe.py         40 NYC garments tailored from the body mesh, plus bags, hats, watch
blender/character/variety.py          the 12-dimensional pedestrian variety vector (contract for core/peds)
blender/character/npc_generator.py    24 base bodies x variety vector
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

## 5. Blendshapes — all 52 ARKit channels exist

The `faceunits01` functional pack contains exactly the ARKit-52 set for the hm08 base mesh, so **all 52** are
realised as glTF morph targets. There is no gap here:

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
`african-male-young` or height targets. `test_blendshapes_actually_move_vertices` asserts every one of the 52
displaces at least one vertex, so an empty channel cannot ship silently.

Caveats, stated plainly:

* the four `eyeLook*` families move the **eyelid and periorbital skin only**; the eyeballs are separate
  objects and are rotated by the runtime, not by a morph;
* `tongueOut` moves the body mesh's mouth region; the tongue is a separate mesh skinned to `head` and does
  not itself morph;
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

**The first pass was wrong and was rebuilt.** Garments were originally generated by offsetting the body mesh
along its normals. The orchestrator's review of `full_body_front.png` called it correctly: the top read as a
balloon that swallowed the torso, the arms fused into the chest volume because two offset shells
interpenetrated at the armpit, the sleeves reached past the wrist and buried the hands, and the shoes were
smoothed foot-shells that read as flippers.

Before rebuilding, the pipeline was diagnosed to make sure the cause was the wardrobe and not a fallback
mesh (`/tmp` diagnostic, output quoted here):

```
basemesh: diag.body 19158 verts, 18486 faces        <- the genuine MakeHuman hm08 base mesh
materials: ['diag.body'] Principled + TEX_IMAGE     <- the real MakeSkin material, not a placeholder
vertex groups: 233
bodyparts: eyes 1064, eyebrows 124, eyelashes 250, teeth 3868, tongue 226, hair 2984
finger bone groups: 30   verts on fingers: 3934     <- the hands do have modelled fingers
hand_l verts: 369  foot_l: 529  ball_l: 990         <- so do the feet
clothes loaded: 37 of 37   MISSING clothes: []      <- every MakeHuman garment fits successfully
```

So the head looked right because it was untouched skin, and the body looked wrong because the procedural
shells were covering it. Nothing had fallen back.

### 7.1 What the wardrobe is now

Every base layer, bottom and shoe is a **real tailored MakeHuman CC0 mesh** with a hem, a collar, sleeve
seams, an armpit and a waistband, fitted by MPFB through the MakeClothes vertex correspondences so it follows
every macro target. Three mechanisms make that usable as a 40-item NYC wardrobe:

* **Suit splitting.** Several `casualsuit`/`elegantsuit` assets are one mesh holding a jacket shell and two
  trouser shells. `split_loose_parts` separates them by connected component and keeps the half the item wants,
  which turns one asset into a real jacket *and* a real pair of trousers (e.g. `male_casualsuit02` →
  1 250-vertex bomber jacket, 886 vertices of trouser removed).
* **Tinting.** The garment's own diffuse map already carries the author's colour, so multiplying the wardrobe
  colour into it gives muddy hues. The map is instead reduced to luminance, normalised by its own mean,
  remapped into a 0.55-1.35 shading band and multiplied by the wardrobe colour - **baked into a new image**,
  in the image's own colour space. Baking rather than shader-nodding matters: glTF carries a base-colour
  texture and a factor, so a Mix/MapRange chain is dropped on export and the garment would arrive in the
  engine in the asset author's colour. The first NPC line-up showed exactly that failure.
* **Layer stand-off.** MakeHuman fits every garment at its own designed stand-off, so a jacket and a sweater
  interpenetrate. Each layer is pushed out along its normals: base 0, mid 4 mm, outer 24 mm.

### 7.2 Weights: taken from the body, not from MPFB's proximity fit

MPFB weights a fitted garment by proximity to the base mesh. That is wrong wherever two body parts are close
together: in the MakeHuman rest pose the hands hang beside the thighs, so trouser vertices picked up `hand_*`
and finger weights, and as soon as the hand moved it **tore a hand-shaped hole through the trouser leg**. The
hole was visible in `detail.png` and was isolated to `jeans_indigo` by rendering each garment separately
against the bare body.

`reweight_from_body` now gives every garment vertex the weights of its nearest *body* vertex through a
KD-tree, so garments use MakeHuman's own anatomically-correct weighting and inherit the 4-influence,
sum-to-one normalisation `convert_to_ue5` has just applied. The same routine weights the procedural garments.

A second, unrelated cause of the same symptom was also fixed: the idle pose hung the hands 55 mm *inboard*,
which pushed them inside the trouser leg. They now hang 16 mm outboard of the thigh.

### 7.3 What is still procedural

The items MakeHuman has none of: three puffers and a long puffer, two long coats, the ANSI hi-vis vest, the
Con-Ed orange vest, the insulated delivery vest, the hijab, the hood on the hoodies, the wristwatch, the two
extra hairstyles, the bags and the caps. These are cut with the original offset technique - but from **the
garment already on the body** (the tee or the sweater), not from the bare skin, so they inherit that
garment's real sleeves, armpit gap and hem instead of fusing the arms to the torso. Vests are torso-only and
so cannot have the problem at all. The hijab leaves the face open by cutting the head region 35 mm in front
of the head joint.

The player wears `tee_white`, `jeans_indigo`, `hoodie_grey` (with a procedural hood), `jacket_bomber` (the
upper shell of `male_casualsuit02`) and `sneakers_black`, plus a procedural steel watch on the left wrist
whose strap radius is measured from his own forearm vertices.

**Gap:** the garments have no zips, buttons, plackets or cloth simulation, and the procedural outerwear still
has no seams. `bmesh.ops.solidify` was tried on the MakeHuman garments to give them fabric thickness and had
to be reverted - the CC0 meshes contain loose edges and coincident vertices that make it fan out spikes at
the shoulder and hip (`thicken()` is kept in the module, unused, with that recorded).

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

## 9. NPC system

* **24 base bodies** (`variety.BODY_PRESETS`) across the MakeHuman macro targets — gender, age (child to
  old), muscle, weight, height, proportions and the three ethnic axes, distributed to match the ACS profile
  of New York City (30.9 % White NH, 28.7 % Hispanic, 20.2 % Black, 15.6 % Asian). Every one of the 24 is
  generated and exported; `test_all_24_base_bodies_are_generated` asserts it.
* **40 wardrobe items** (`wardrobe.WARDROBE`), 29 of them real tailored MakeHuman CC0 meshes and 11
  procedural: 11 tops, 3 mid-layer hoodies, 13 outerwear (3 puffers plus a long puffer, 2 long coats,
  3 tailored jackets, 3 suit jackets, ANSI hi-vis, Con-Ed orange, insulated delivery vest), 8 bottoms
  (jeans x2, chinos, suit trousers, scrubs, joggers, denim shorts, kid's jeans), 4 shoes and the hijab.
  Scrubs, hijab, delivery vest, hi-vis, tourist tee and three children's items are all present;
  `test_wardrobe_has_forty_items` checks the count and the tags.
* **12 hairstyles**: 10 MakeHuman CC0 card-hair meshes (short01-04, bob01/02, long01, ponytail01, braid01,
  afro01) plus 2 procedural (`buzzcut` = a scalp shell, `topknot` = bob01 plus a bun).
* **12-dimensional variety vector** (`variety.py`, published to `blender_out/character/npc_variety.json`):
  `body_preset, skin_tone, hair, top, bottom, shoes, outerwear, bag, hat, glasses, height_scale, walk_style`
  — 12 unsigned bytes, each an index into a named table, 255 = absent. `height_scale` maps 0-255 onto a
  narrow multiplier band. `walk_style` selects one of 8 gaits (relaxed, brisk, hurried, strolling, elderly,
  phone, umbrella, loaded), each with a clip, a playback rate and a stoop offset applied to the whole clip
  set at build time.
  The vector is derived from a spawn seed by `blake2b(seed_le_u64)`; byte *i* is dimension *i* and byte
  *i*+16 is the absence roll, so the runtime can reproduce any pedestrian's appearance from its id alone.

  **`core/peds` was empty when this stage ran** (`core/include/nycsim/peds/` and `core/src/peds/` contain no
  files), so there was no existing vector to match. This lane *defines* it and publishes the machine-readable
  contract; the peds agent should consume `npc_variety.json` rather than invent a second encoding. That is a
  new inter-stage contract and is flagged here for the orchestrator.
* **One skeleton, one clip set.** Every NPC carries the same 71 bones, the same 52 blendshapes and the same
  25 clips including `umbrella_hold` and `phone_walk`;
  `test_npcs_share_one_skeleton_and_the_same_clips` asserts a single distinct clip set across all 24.

---

## 10. Verification renders

Cycles CPU, 64 samples for the mandated stills and 32-48 for the contact sheets, three-point area lighting on
a neutral backdrop (ADR-012). `NYCSIM_RENDER_PREVIEW=1` renders the same compositions at 34 % scale and 10
samples; framing and pose iterations were done there, and only the final pass at full quality.

| file | what it shows |
|---|---|
| `face_closeup.png` | three-quarter portrait: subsurface skin, split eyeball/cornea with the tagged iris, `eyelashes02`, `eyebrow006`, the hair cards |
| `full_body.png` | front and back of the dressed player (the character is turned 180 degrees between the two, so both halves are lit identically) |
| `walk_strip.png` | eight evenly spaced frames of one retargeted walk cycle, side on |
| `bend_test.png` | elbow (top row) and knee (bottom row) at 0/45/90/120 degrees, clay-shaded with the clothing hidden |
| `blendshapes.png` | six ARKit face units at full weight |
| `detail.png` | left hand and left foot at 460 px each: modelled fingers with nails and knuckles, the shoe, and the garment boundaries |
| `npc_lineup.png` | twelve generated pedestrians side by side |

The renders were opened and acted on, not just produced - and after the orchestrator's review, opened again.
Eleven defects were found this way and fixed:

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

---

## 11. Tests

`python3 -m pytest tests/test_character.py -q`

The suite reads the exported artefacts, not the generator: it parses `player.glb`'s JSON and BIN chunks
itself and checks the bone set and hierarchy, the seven IK bones, the full finger chain including
metacarpals, the `asset.extras.nycsim` block required by DATA_CONTRACTS section 13, every required animation
name, 30 fps key spacing, loop closure, the additive flags, the 52 morph target names, that each morph
actually moves vertices, that skin weights sum to 1 with at most four influences and reference valid joints,
the player's measurements, and that his home BIN is residential in `buildings_base.parquet`. The NPC manifest
is checked for the 12 dimensions, 24 bodies, 40 wardrobe items and the single shared clip set. The ASF/AMC
parser has its own unit tests (bone-length invariance under FK, the rest pose being a standing human, the
Euler convention matching Blender's, the Y-up to Z-up swap being a proper rotation) that need neither Blender
nor the exported assets.

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
4. **Garments have no zips, buttons, plackets or cloth simulation**, and the eleven procedural items are
   still offset shells (section 7.3). The 29 MakeHuman items are properly tailored meshes.
5. **No facial rig beyond blendshapes.** There are no jaw or eye bones; the eyes are separate objects the
   runtime must rotate, and jaw motion is the `jawOpen`/`jawLeft`/`jawRight`/`jawForward` morphs only.
6. **No LODs and no cloth/hair physics.** One mesh level per part; the player is about 42 k vertices across
   16 meshes. LOD generation and a UE cloth setup are runtime-side work.
7. **Subsurface skin is authored, not previewable in glTF.** The Principled subsurface weight and radius are
   set for Cycles and written into `extras.nycsim.skin` for the UE material; glTF itself has no SSS, so a
   glTF viewer shows flat diffuse skin.
8. **The `eyeLook*` blendshapes move only the lids** (5).
9. **Character forward is -Y in Blender**, recorded as `extras.nycsim.forward_axis_blender`. That is
   MakeHuman's native orientation, kept because rotating a shape-keyed, skinned, multi-mesh character risks
   more than it gains; the UE import must apply the +X convention. This differs from the vehicles lane, which
   exports +X forward, and the orchestrator should make the import script aware of it.
10. **The car clips assume the exported Fusion Hybrid.** If the vehicles lane re-exports with different
    interior geometry the seated clips need rebuilding; the numbers used are recorded in the catalog so the
    drift is detectable.
11. **Facial identity is MakeHuman's**, driven only by the macro targets — no custom head sculpt, so the
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
* `blender_out/character/npc_variety.json` is the **pedestrian appearance contract for `core/peds`**: 12
  uint8 dimensions, the tables they index, and the seed hash. Consume it; do not define a second encoding.
* Every character is 4-influence skinned with weights summing to exactly 1, so UE's default skinning limit
  needs no re-weighting on import.
* Rebuild commands:
  `python3 blender/character/build_character.py` (about 35 s),
  `python3 blender/character/npc_generator.py --count 24` (about 13 min),
  `python3 blender/character/render_verify.py all` (about 50 min at 64 samples on this contended 4-vCPU box;
  set `NYCSIM_RENDER_PREVIEW=1` for a two-minute pass).
