# Vehicle lane — verification report

Stage: `blender/vehicles/` → `blender_out/vehicles/`
Suite: `tests/test_vehicles.py`
Last full build: `2026-09-06T19:32:11Z`, 31 assets in **65.2 s**, 0 failures.

```
PYTHONPATH=pipeline python3 -m pytest tests/test_vehicles.py -q
456 passed in 2.97s
```

---

## 1. What is built

| artefact | count | path |
|---|---|---|
| LOD0 vehicle glb | 31 | `blender_out/vehicles/<id>.glb` |
| LOD1 / LOD2 glb | 62 | `blender_out/vehicles/<id>_LOD{1,2}.glb` |
| catalog entry per asset | 31 | `blender_out/vehicles/catalog/<id>.json` |
| build log | 1 | `blender_out/vehicles/catalog/_build_summary.json` |
| processed-manifest entries | 31 | `data/manifest/processed.json`, ids `vehicles/<id>` |

31 assets = **28 distinct bodies** (every body ADR-009 lists) plus 3 extra player-car liveries
(`fusion_yellow_taxi`, `fusion_black_car`, `fusion_green_boro_taxi`, which share `fusion_hybrid`'s geometry and
carry `base_id`). Total on disk 101 MB.

Source layout:

* `blender/vehicles/build_all.py` — builds the fleet in one Blender process, sequentially (`--only`, `--skip`,
  `--list`, `--keep-going`).
* `blender/vehicles/build_fusion.py` — the player car (Ford Fusion), the highest-detail model and the reference
  for the shared library.
* `blender/vehicles/fleet_cars.py`, `fleet_big.py`, `fleet_small.py` — the 27 fleet bodies as `FleetSpec`s.
* `blender/vehicles/vlib/` — the shared library: `blueprint.py` (station-table body surfaces), `geom.py`,
  `parts.py` (wheels, lamps, mirrors, wipers, handles), `interior.py`, `materials.py`, `textures.py`,
  `rig.py` (contract, pivots, damage weights, collision proxies, LODs, export, catalog), `fleetlib.py`,
  `env.py`.
* `blender/vehicles/render_verify.py` — the verification renders.

Everything is generated procedurally from published dimensions; **nothing was downloaded**, so this lane has
no licence records to add. Textures (plates, wordmarks, gauges, tyre lettering) are generated in
`vlib/textures.py`, not traced from artwork.

## 2. Per-vehicle dimensions, sources and polycounts

Deviation is measured **on the exported glb**, not in the Blender scene: the test rebuilds the world-space
envelope from the node transforms and the accessor `min`/`max` of every mesh node except the `UCX_` proxies and
each vehicle's declared `envelope_excludes` (mirrors, light bars and destination signs, which are not part of a
published body dimension). Tolerance ±2.00 %.

| id | class | published L×W×H (mm) | wheelbase (mm) | dev L/W/H (%) | LOD0 | LOD1 | LOD2 | UCX | published source |
|---|---|---|---|---|---|---|---|---|---|
| `arrow_ebike` | bicycle | 1850 × 660 × 1100 | 1190 | +1.62 / +1.15 / −0.18 | 5,212 | 4,448 | 1,938 | 4 | Arrow class-2 delivery e-bike published specification |
| `citibike_cruiser` | bicycle | 1900 × 660 × 1120 | 1200 | −0.53 / +1.15 / −0.00 | 4,950 | 4,220 | 1,940 | 4 | Citi Bike (Lyft) classic bike published dimensions |
| `mci_j4500_coach` | bus | 13716 × 2591 × 3594 | 9400 | +0.03 / +1.35 / +0.00 | 45,244 | 34,874 | 5,667 | 11 | MCI J4500 published dimensions |
| `nova_lfs_mta` | bus | 12192 × 2591 × 3200 | 7100 | +0.11 / +0.12 / +0.31 | 39,830 | 28,912 | 5,721 | 10 | Nova Bus LFS published dimensions; MTA NYCT 40-foot fleet |
| `school_bus_bluebird` | bus | 12192 × 2440 × 3100 | 6934 | −0.00 / +0.16 / +0.00 | 38,052 | 28,576 | 5,722 | 10 | Blue Bird Vision published dimensions; NY State Type C configuration |
| `xd60_sbs` | bus | 18593 × 2591 × 3200 | 13691 | +0.23 / +0.12 / +0.31 | 50,746 | 38,845 | 5,606 | 14 | New Flyer Xcelsior XD60 published dimensions; MTA SBS livery |
| `horse_carriage` | carriage | 3600 × 1650 × 2200 | 1900 | +0.22 / −0.00 / −0.00 | 11,340 | 9,668 | 2,910 | 4 | NYC DCWP horse-drawn cab rules; vis-à-vis carriage dimensions |
| `ambulance_type1_fdny` | emergency | 7160 × 2440 × 2900 | 4240 | +0.35 / +0.16 / +0.00 | 36,322 | 27,363 | 5,721 | 6 | Ford F-450 chassis cab; Type I module 96 in wide |
| `explorer_nypd` | emergency | 5049 × 2004 × 1775 | 3025 | +0.00 / +0.04 / +0.00 | 39,264 | 28,057 | 5,722 | 5 | Ford Explorer / Police Interceptor Utility 2020 |
| `seagrave_engine_fdny` | emergency | 9750 × 2591 × 3100 | 4674 | +0.17 / +1.85 / +0.00 | 37,936 | 28,733 | 5,721 | 8 | Seagrave Marauder II; FDNY engine company configuration |
| `seagrave_tower_fdny` | emergency | 12500 × 2591 × 3350 | 6350 | +0.10 / +0.04 / +0.00 | 44,384 | 34,039 | 5,665 | 10 | Seagrave Aerialscope 75 ft; FDNY ladder company configuration |
| `moped_scooter` | moped | 1860 × 735 × 1140 | 1340 | −0.84 / +0.91 / −0.17 | 5,780 | 4,966 | 1,940 | 4 | Piaggio Vespa Primavera 150 published dimensions |
| `pedicab` | pedicab | 2900 × 1250 × 1750 | 1850 | +1.55 / −0.46 / −0.29 | 7,090 | 6,048 | 2,132 | 4 | NYC Admin. Code §20-250 pedicab dimensions |
| `camry_taxi_yellow` | sedan | 4885 × 1840 × 1445 | 2825 | −0.00 / +0.00 / +0.00 | 38,652 | 27,571 | 5,722 | 5 | Toyota Camry XV70 published dimensions |
| `camry_boro_taxi` | sedan | 4885 × 1840 × 1445 | 2825 | −0.00 / +0.00 / +0.00 | 38,652 | 27,571 | 5,722 | 5 | Toyota Camry XV70 published dimensions |
| `camry_black_car` | sedan | 4885 × 1840 × 1445 | 2825 | −0.00 / +0.00 / +0.00 | 38,540 | 27,477 | 5,722 | 5 | Toyota Camry XV70 published dimensions |
| `fusion_hybrid` | sedan | 4872 × 1852 × 1476 | 2850 | −0.00 / +0.00 / −0.00 | 84,786 | 58,280 | 7,659 | 7 | Ford 2019 Fusion published dimensions (ADR-009) |
| `fusion_yellow_taxi` | sedan | 4872 × 1852 × 1476 | 2850 | −0.00 / +0.00 / −0.00 | 84,898 | 58,275 | 7,659 | 7 | Ford 2019 Fusion published dimensions (ADR-009) |
| `fusion_black_car` | sedan | 4872 × 1852 × 1476 | 2850 | −0.00 / +0.00 / −0.00 | 84,786 | 58,280 | 7,659 | 7 | Ford 2019 Fusion published dimensions (ADR-009) |
| `fusion_green_boro_taxi` | sedan | 4872 × 1852 × 1476 | 2850 | −0.00 / +0.00 / −0.00 | 84,898 | 58,275 | 7,659 | 7 | Ford 2019 Fusion published dimensions (ADR-009) |
| `rav4_fhv` | suv | 4600 × 1855 × 1685 | 2690 | +0.00 / +0.03 / +0.00 | 38,876 | 27,763 | 5,722 | 5 | Toyota RAV4 XA50 published dimensions |
| `suburban_black_car` | suv | 5733 × 2059 × 1933 | 3407 | +0.00 / +0.00 / +0.00 | 40,612 | 28,863 | 5,721 | 5 | Chevrolet Suburban 2021 published dimensions |
| `coned_utility_truck` | truck | 7340 × 2440 × 2900 | 4320 | +0.00 / +0.98 / −0.00 | 37,740 | 26,989 | 5,237 | 6 | Ford F-550 chassis cab; 11 ft utility body |
| `freightliner_stepvan` | truck | 7620 × 2440 × 3050 | 4140 | +0.12 / +0.16 / +0.00 | 35,296 | 26,499 | 5,237 | 6 | Freightliner MT55; 25 ft walk-in body |
| `isuzu_npr_box` | truck | 7240 × 2130 × 3200 | 3810 | +0.02 / +0.19 / +0.00 | 35,308 | 26,489 | 4,751 | 6 | Isuzu NPR-HD; 16 ft dry-freight body |
| `mack_lr_dsny` | truck | 10060 × 2591 × 3450 | 5120 | +0.13 / +0.12 / +0.00 | 36,816 | 27,695 | 5,721 | 8 | Mack LR; DSNY rear-loader configuration |
| `dollar_van` | van | 6706 × 2059 × 2750 | 3750 | +0.00 / +0.53 / +0.00 | 39,714 | 27,729 | 5,236 | 6 | Ford Transit 350 XLT 15-passenger |
| `nv200_taxi` | van | 4760 × 1730 × 1872 | 2725 | −0.00 / +0.01 / +0.00 | 38,430 | 27,379 | 5,721 | 5 | Nissan NV200 Taxi (NYC TLC Taxi of Tomorrow) |
| `sprinter_van` | van | 5932 × 2020 × 2820 | 3665 | +0.00 / +0.49 / −0.00 | 37,972 | 27,825 | 5,236 | 5 | Mercedes-Benz Sprinter 2500 published dimensions |
| `transit_van` | van | 5981 × 2059 × 2540 | 3750 | +0.00 / +0.53 / +0.00 | 38,504 | 27,824 | 5,237 | 5 | Ford Transit 250 published dimensions |
| `usps_llv` | van | 4440 × 1870 × 2440 | 2690 | +0.00 / +0.21 / +0.00 | 36,060 | 26,196 | 4,752 | 5 | Grumman LLV published dimensions |

**Totals** — LOD0 1,236,690 tris, LOD1 895,729, LOD2 162,778.
**Worst deviation in the fleet: +1.85 %** (`seagrave_engine_fdny` width, the pump-panel handrails on a
102 in body). Everything else is inside ±1.62 %, and 19 of the 31 are inside ±0.35 % on all three axes.

Budgets (`test_player_car_lod_budgets`, `test_fleet_lod0_budget`): player car LOD0 84,786 ≤ 350,000;
LOD1 58,280 ≤ 60,000; LOD2 7,659 ≤ 8,000. Largest non-player LOD0 is `xd60_sbs` at 50,746 ≤ 120,000.
LOD1/LOD2 budgets per class are in each catalog entry (`lods[n].budget`) and every level is strictly coarser
than the one above it.

## 3. Engine contract

Per DATA_CONTRACTS §13: Y-up metres on export, file origin on the ground under the rear-axle centre, +X
forward / +Y left / +Z up in Blender before the export flip. `asset.extras.nycsim` carries
`schema_version`, `generator_script`, `git_commit`, `exported_at`, `units`, `up_axis_blender`, `pivot`,
`vehicle_id`, `vehicle_class`, `livery`, `contract_profile` (and `lod` on the LOD files).

* 1,817 named nodes across the fleet; the player car alone has 77 nodes, 52 material slots, 17 `LIGHT_*` slots.
* Contract profiles: `full` (enclosed cabin), `two_wheel`, `trike`, `open`. Anything a body genuinely does not
  have is listed in `contract_waivers` **with a reason** and is checked by `test_waivers_have_reasons`; nothing
  is faked to satisfy a name list.
* Damage: `Body` carries `_DMG_FRONT/REAR/LEFT/RIGHT/ROOF` float vertex attributes (0..1, each region reaching
  1.0 somewhere on the panel) plus vertex groups of the same name without the underscore, so the data survives
  both the glb and a `.blend` round trip.
* Collision: 199 `UCX_` proxies over the fleet, 25,010 triangles in total.

### Collision proxies — the two bugs that were open, and the numbers now

*Open hulls.* `arrow_ebike UCX_Body_00` had 2 open edges and `moped_scooter` 2; a proxy with a boundary edge is
not a hull and a physics engine handed one does something undefined rather than failing cleanly. Every proxy is
now built as a closed convex hull and welded by position before export.

*Missing upper body.* The e-bike, Citi Bike, pedicab, carriage and moped hulls stopped at the frame and left the
top ~30 cm (handlebars, canopies) with no collision: the e-bike topped out at 0.760 m against a 1.098 m body.

Measured over all 31 assets after the fix:

| check | result |
|---|---|
| open edges, all 199 proxies | **0** |
| worst non-convexity | **0.0003 mm** (tolerance 2 mm) |
| worst under-coverage of the body on any axis | **0.0002 m** (allowance 0.12 m), on `ambulance_type1_fdny` |

e.g. `arrow_ebike` body z 0.000..1.098 m, UCX z 0.000..1.098 m; `citibike_cruiser` 0.000..1.120 against
0.000..1.120.

### Door pivots, including doors that are not side-hinged

The suite requires each `Door_*` origin to sit on the leaf's own leading vertical edge (local `x_max ≈ 0`, so
the leaf extends rearward in −X) and off the centreline. That is well defined for a side-hinged car door. It was
raised as possibly meaningless for the coach and the school bus, which have **bifold** service doors.

The convention that fits both, now implemented and documented in `vlib/rig.py`:

> A `Door_*` node's origin sits on the **forward vertical edge of its own aperture**, and its local +X points
> rearward along the leaf. For a conventional side-hinged door that edge *is* the hinge. A bifold or
> outward-swinging plug leaf is exported as **one node covering the whole doorway** whose origin is on the same
> forward frame edge — which is the outer leaf's hinge — so the rotation axis is well defined either way. The
> mechanism the engine must animate is named per panel in `catalog["door_kind"]`:
> `hinged` / `sliding` / `bifold` / `rear cargo door` / `boot lid / tailgate` / `front-hinged bonnet`.
> Rotate about the origin's local Z for `hinged` and `bifold`; translate along −X for `sliding`.

Measured: `mci_j4500_coach Door_FR` origin (10.200, −1.192, 1.290) with local x −1.095..−0.005;
`school_bus_bluebird Door_FR` origin (6.950, −1.122, 1.128), local x −0.895..−0.005. Both pass the geometric
test *and* declare `door_kind = bifold`, so no waiver was needed and the engine is not left guessing.

`door_kind` is now written for **every** body that has an opening panel (it previously covered only the
`FleetSpec` bodies, not the player car), and it lists only panels the vehicle actually has — a waived door no
longer appears in it.

**Proposed contract addendum (§13a) — for the orchestrator to accept or reject.** DATA_CONTRACTS §13 fixes the
file origin but says nothing about opening panels. The paragraph above is the convention this lane ships and the
importer should rely on; it is machine-readable today as `catalog["door_kind"]` and
`asset.extras.nycsim.pivot`. No shared document was edited.

## 4. Verification

```
PYTHONPATH=pipeline python3 -m pytest tests/test_vehicles.py -q     →  456 passed in 2.97s
nice -n 10 python3 blender/vehicles/build_all.py                    →  31 vehicles, 1,236,690 LOD0 tris, 65.2 s, 0 failures
```

The suite reads the exported `.glb` files with its own minimal glTF reader — no trimesh/pygltflib — so it checks
exactly what Unreal will import: node names, material-slot names, world-space extents, wheel-pivot positions and
tyre radii, damage attributes and their range, gauge/plate UV spans (exactly 0..1), the LOD chain and its
budgets, the convexity **and edge-manifoldness** of every `UCX_` proxy, the coverage of the body by the proxy
union, door and steering-column axes, and `asset.extras.nycsim`.

## 5. Renders

Cycles CPU, AgX view transform, `nice -n 10`, one process at a time (ADR-012). Wall clock measured on the shared
4-vCPU box while other agents were running, so these are upper bounds.

| image | camera | resolution | samples | wall clock |
|---|---|---|---|---|
| `docs/verification/vehicles/fusion_exterior.png` | 3/4 front, 30° FOV | 960 × 540 | 64 | 299 s for both fusion views |
| `docs/verification/vehicles/fusion_interior_driver_pov.png` | driver eyepoint, 80° FOV, 4:3 | 960 × 720 | 64 | (same run) |
| `docs/verification/vehicles/fusion_ortho_side.png` | orthographic side elevation, scale 5.6 m | 1200 × 528 | 24 | 26 s |
| `docs/verification/vehicles/fleet_lineup.png` | orthographic, elevated 3/4 over the yard | 1800 × 1099 | 40 | 187 s |
| `docs/verification/vehicles/fleet_lineup_order.json` | row/placement key for the lineup | — | — | — |

Reproduce:

```
nice -n 10 python3 blender/vehicles/render_verify.py fusion --width 960  --samples 64
nice -n 10 python3 blender/vehicles/render_verify.py ortho  --width 1200 --samples 48
nice -n 10 python3 blender/vehicles/render_verify.py fleet  --width 1100 --samples 40
```

`fleet_lineup.png` shows all 28 bodies (liveries excluded) parked in rows of at most 24 m, sorted by class then
length; `fleet_lineup_order.json` gives each vehicle's row and (x, y) so any body in the frame can be identified.

Two render-harness bugs were found and fixed while producing these:

* the fleet lineup loaded `_build_summary.json` as if it were a vehicle (`KeyError: 'class'`);
* it imported the `UCX_` proxies along with the bodies, and the shared `UCX_COLLISION` material is translucent
  green — every vehicle in the first lineup was wrapped in a green shell. The proxies are now stripped on import
  (the fusion renders already did this).

## 6. Fidelity achieved vs. target

**Target**: photoreal, 1:1, drivable. **Achieved**: dimensionally exact and engine-complete; *not* photoreal.

What is real:

* Every body is driven by published dimensions (length, width, height, wheelbase, track, tyre size, overhangs,
  ground clearance) with the deviations tabulated above — worst 1.85 %, most at 0.00 %.
* Tyre diameters come from the published tyre code, wheel pivots sit at the hub centres (`test_wheel_pivots_at_hub_centres`
  checks the pivot, the hub height against the tyre radius, the centring of the geometry on its own origin and
  the rendered diameter), and the rear axle is at x = 0 on every asset.
* Names, liveries and equipment are the real ones (medallion roof lights on the yellow/green taxis, MTA
  destination signs, FDNY/NYPD emergency slots, USPS wordmark, DSNY rear loader, LLV right-hand drive).

What is **not** photoreal, stated plainly:

1. **Surfaces are procedural, not scanned or photographed.** Bodies are lofted from station tables, so panel
   character (creases, DLO trim, grille meshes, badge relief, shut lines) is approximate. `fusion_exterior.png`
   reads as *a* mid-size sedan of the right size, not as a recognisable 2019 Fusion. Closing this needs
   reference-photo modelling or scan data, which this lane has no source for.
2. **No PBR texture maps.** Materials are analytic (base colour + roughness + clearcoat, generated decals and
   gauge/plate images). There are no albedo/normal/ORM maps, no dirt, wear or edge-grime layers.
3. **The player car's greenhouse is packaged too far forward.** The windscreen header sits at x = 2.00 m and the
   driver's eye at x = 1.65 m, i.e. the header is 0.35 m ahead of the eye where a real Fusion has ≈ 0.75 m; the
   dash top pad (1.140 m) clears the eye (1.245 m) by only 0.105 m. The visible consequence is in
   `fusion_interior_driver_pov.png`: the frame needed a 4:3 aspect and an 80° lens to get the header and
   A-pillars in shot at all. Overall height, length and the H-point are right; the *fore-and-aft* split between
   bonnet, screen and roof is not. Fixing it means re-cutting the Fusion blueprint's `X_ROOF_F` / `X_COWL`
   stations and re-tuning the roofline, which would move every panel on the flagship model.
4. **Interiors are cabin-grade, not trim-grade.** Dash, binnacle, centre stack, console, seats, belts,
   headliner, visors, mirror, door cards and pedals are all present and correctly placed, with unit-UV
   `GAUGE_SPEED` / `GAUGE_RPM` / `SCREEN_CENTER` faces for engine-driven instruments — but no stitching, grain,
   switchgear detail or rear-seat furniture beyond the bench.
5. **Small-vehicle deviations are the largest in the fleet** (e-bike +1.62 % length, pedicab +1.55 %) because a
   published figure for these is a category figure, not a single manufacturer's spec sheet. They are inside the
   ±2 % contract but they are the softest numbers in the table, and the source column says so.

## 7. Defects found and fixed in this pass

Beyond the nine reported failures, verifying the numbers turned up five real modelling bugs:

1. **Wipers parked halfway up the windscreen.** The park position reached equally rearward and inboard, so on
   the player car the blades covered 59 % of the 0.385 m-tall screen and sat *in the driver's line of sight*
   (measured z 1.106..1.332 m against an eye at 1.245 m). Parked blades now follow the bottom edge of the glass
   (reach 0.40 rearward / 0.72 inboard of the arm length); the player car's now occupy z 0.933..1.084 m.
2. **The rearward reach was multiplied by the windscreen slope.** On a near-vertical cab-over screen that lifted
   the arms to roof height — `usps_llv`, `transit_van` and `sprinter_van` had their *published height* set by a
   wiper rather than by the roof. The rise is now taken along the glass surface, so it is bounded by the arm
   length.
3. **The spindle was placed from a blueprint curve that means different things on different bodies.** It used the
   body-top line at the cowl station, which is the cowl on a raked sedan but the *roof* on a van. Spindles are
   now measured off the `Window_WS` glazing that was actually built (`P.windscreen_frame`), which is correct for
   both families.
4. **`nv200_taxi` had no windscreen.** With no explicit glass band, the shell put the `Window_WS` region between
   `x_roof_front` and `x_cowl` — on this stubby-bonnet body that is a flat patch of *roof* (measured
   z 1.824..1.864 m, 0.5 m long). The taxi now declares `front_glass=(2.42, 1.28, 1.84)` and has a real raked
   screen (x 1.856..3.149, z 1.223..1.865) with its wipers at the base of it.
5. **Eleven bodies were built short of their published height** by 20–80 mm (`z_top` in the station table was
   left below `dims.height`); the mis-parked wipers had been masking part of it in the envelope measurement.
   Heights are now exact for all of them — `school_bus_bluebird` went from −2.58 % to 0.00 %, `usps_llv` from
   −2.46 % to 0.00 %, `transit_van` −2.36 % → 0.00 %, `dollar_van` −2.18 % → 0.00 %, `sprinter_van` −2.13 % →
   0.00 %, and `mci_j4500_coach`, `ambulance_type1_fdny`, `mack_lr_dsny`, `freightliner_stepvan`,
   `isuzu_npr_box`, `seagrave_tower_fdny`, `seagrave_engine_fdny` likewise. The tower ladder's stowed bucket and
   the engine's hose rolls, which set those two travelling heights, were raised to match.

## 8. Foundation and housekeeping

* **The local export workaround is gone.** `vlib/rig.export_glb` now calls `nycsim_bpy.export_glb` with
  `export_attributes=True` / `export_normals=True` and lets the foundation stamp `asset.extras`; the lane's own
  copy of the glb JSON-chunk patcher (`_inject_asset_extras`) and its own metadata builder were deleted.
  The only lane-specific addition is the `pivot` string, passed through `extras`. Verified: a full rebuild after
  the swap produced byte-for-byte the same triangle totals (1,236,690) and `test_asset_extras_present` passes on
  all 31 files.
* **The lane now records into the shared processed manifest.** `env.record_processed` writes one
  `vehicles/<id>` entry per asset into `data/manifest/processed.json` (path, size, sha256, git commit, LOD paths
  and triangle counts, published dimensions, deviations, catalog path). Failures to write the shared manifest are
  logged and tolerated rather than allowed to kill a build that has already produced valid geometry.
* No foundation file was modified. No shared document was edited.

## 9. What the next agent needs to know

* **Read the catalog, not the geometry.** `blender_out/vehicles/catalog/<id>.json` has everything an importer or
  a traffic spawner needs: class, livery, `base_id`, glb + LOD paths and triangle counts, published and measured
  dimensions, `wheel_pivots` and per-wheel `wheel_diameters_mm`, node and material lists, `light_slots`,
  `collision_proxies`, `damage_regions`, `door_kind`, `contract_profile`, `contract_waivers` and `sources`.
* **Liveries share geometry.** Filter on `base_id` when you want one asset per body (28 of the 31).
* **LODs are sibling files**, `<id>_LOD1.glb` / `<id>_LOD2.glb`, as §13 permits; the parent catalog entry owns
  them. LOD1 keeps the exterior node names; LOD2 is a single merged `Body`.
* **`UCX_` nodes are collision proxies, not geometry.** Strip them on import (Unreal picks them up by name) and
  never count them against a triangle budget or include them in a render — the shared `UCX_COLLISION` material is
  translucent green and will tint anything you forget to remove.
* **Emissive slots** are the `LIGHT_*` material names; every one carries an `emissiveFactor`. Emergency vehicles
  add `LIGHT_EMERGENCY_R` / `LIGHT_EMERGENCY_B`, medallion taxis add a `TAXI_ROOF` node and slot, MTA buses add
  `SIGN_FRONT` / `SIGN_SIDE` / `SIGN_REAR`.
* **Damage weights** are `_DMG_*` float vertex attributes on `Body` only, 0..1, one per region.
* **Rebuild cost** is 65 s for the whole fleet in one Blender process; `--only <ids>` rebuilds a subset in
  seconds. The renders are the expensive part (≈ 8 minutes for all four).
