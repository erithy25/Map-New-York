# The player character — Nikos "Nick" Vlahos

| | |
|---|---|
| **Name** | Nikos Vlahos (goes by Nick) |
| **Age** | 34 |
| **Home** | 23-22 31st Avenue, Apt 3R, Astoria, Queens, NY 11106 |
| **Work** | Nights driving a TLC-plated 2019 Ford Fusion Hybrid; days, second-year apprentice at the MTA's Casey Stengel bus depot |
| **Asset** | `blender_out/character/player.glb` (`asset_id: player`) |

## The address is real

Every field below is read out of the project's own processed data, not invented.

| Field | Value | Source |
|---|---|---|
| BIN | 4006653 | `data/processed/buildings/buildings_base.parquet` |
| BBL | 4005690038 (Queens, block 569, lot 38) | PLUTO join, `pluto_joined = true` |
| PLUTO building class | **C1** — walk-up apartments, six families or more, no stores | `data/raw/nyc_opendata/pluto.csv` |
| PLUTO land use | **2** — multi-family walk-up buildings | PLUTO |
| Residential units | 12 (`unitsres = 12`, `unitstotal = 12`) | PLUTO |
| Floors | 4 | PLUTO / footprint join |
| Year built | 1926 | PLUTO |
| Zoning | R6A | PLUTO |
| Postcode | 11106 | PLUTO |
| Council district / community board | 22 / Queens CB 1 | PLUTO |
| Footprint area | 190.76 m² | `buildings_base.parquet` |
| Measured height / roof | 15.33 m / 18.98 m NAVD88, ground 3.66 m | `buildings_base.parquet` (`height_source = 0`, LiDAR-real) |
| Building frontage × depth | 6.71 m × 32.92 m | PLUTO |
| Primary facade heading | 301.6° | `buildings_base.parquet` |
| Centroid (NYC_TM) | x = 1859.864 m, y = 7345.275 m | `buildings_base.parquet` |
| Centroid (WGS84) | 40.766098 N, 73.928020 W | PLUTO latitude/longitude; NYC_TM round-trip agrees to 5 m |
| Tile | `t_1_7` | tiling from `pipeline/nycsim_pipeline/tiling.py` |
| NTA (2020) | QN0103 — Astoria (Central) | `buildings_base.parquet` |
| Landmark / historic district | none | `landmark_id` empty, `hist_district` empty |

The building is a twelve-unit, four-storey 1926 brick walk-up on a 6.7 m-wide lot — the standard Astoria
type. Apt 3R is the rear apartment on the third floor; with twelve units over four floors that is three
apartments per landing, which is what the 6.7 × 32.9 m footprint gives.

## Backstory (200 words)

Nick Vlahos was born in the third-floor rear of 23-22 31st Avenue and has not managed to leave it. His
grandfather came from Kalymnos in 1961 and took the same apartment; his mother still has the lease, and Nick
still has the small back bedroom that looks onto the airshaft and the Astoria Boulevard traffic beyond it.

He learned cars from his uncle's shop on 21st Street, which closed in 2019. Now he is two years into an
apprenticeship at the MTA's Casey Stengel depot, turning wrenches on New Flyer buses on the day shift, and he
drives a for-hire Fusion Hybrid five nights a week to cover his mother's medical bills and the loan on the
car itself. He knows which Queensboro Bridge lane moves at 2 a.m., which Kaufman Astoria security guards will
let him wait, and that the Grand Central Parkway is a lie between six and ten.

He is not romantic about the city. He is precise about it. He notices a scaffold that has been up four years,
a fire escape repainted, a bodega changing hands. He wants a licence, a garage bay of his own, and to stop
driving nights. He is saving 400 dollars a month toward it.

## What was built

* **Body** — MakeHuman hm08 base mesh through MPFB2, macro targets: gender 0.93, age 0.44 (≈ 34 years),
  muscle 0.60, weight 0.52, height 0.60, proportions 0.62, ethnicity 80 % Caucasian / 14 % Asian / 6 %
  African (a Greek-American phenotype in MakeHuman's three-axis model). Measured height 1.79 m.
* **Face** — 52 ARKit blendshapes (the complete set) from the CC0 `faceunits01` pack, shipped as glTF morph
  targets. See `docs/verification/character/REPORT.md` for the exact list.
* **Eyes** — MakeHuman high-poly eyes, split into separate eyeball and cornea meshes; the cornea is a
  refractive shell (IOR 1.376), and the iris faces carry their own material slot so the runtime can drive
  pupil dilation. Lashes (`eyelashes02`) and brows (`eyebrow006`) are separate CC0 meshes.
* **Mouth** — MakeHuman `teeth_base` and `tongue01` as separate skinned meshes.
* **Hair** — MakeHuman `short01` card hair with its alpha diffuse map.
* **Skin** — MakeHuman `middleage_caucasian_male` CC0 diffuse on a Principled BSDF with subsurface weight
  0.18 and a 10/4/2.5 mm RGB scattering radius.
* **Clothing** — white crew tee, indigo jeans, grey pullover hoodie, olive bomber jacket, black sneakers, and
  a steel watch on the left wrist. All tailored procedurally from his own body mesh (see
  `blender/character/wardrobe.py`), so they fit and deform exactly.
* **Rig** — UE5-Mannequin naming, 71 bones: `root`, `pelvis`, `spine_01..05`, `neck_01/02`, `head`,
  `clavicle/upperarm/lowerarm/hand` per side, the full finger chain including metacarpals, `thigh/calf/foot/
  ball`, and `ik_foot_root`, `ik_foot_l/r`, `ik_hand_root`, `ik_hand_gun`, `ik_hand_l/r`.
* **Animations** — 25 glTF animations at 30 fps. Walk, jog and run are retargeted CMU motion capture; the
  rest are authored procedurally. Per-clip method and numbers are in the verification report.

## Coordinates and conventions

* Blender: metres, Z up, origin on the ground between the feet.
* Facing axis is recorded in the glb extras as `forward_axis_blender`; the UE import should rotate to the
  mannequin's +X.
* The seated clips assume the character's origin is placed at the car-local point recorded in
  `extras.nycsim.car_attach.socket_car_local_m` of the glb, aligned with the car's +X. That point is derived
  from the SAE H-point of `blender_out/vehicles/fusion_hybrid.glb` (ADR-009's Ford Fusion Hybrid).
