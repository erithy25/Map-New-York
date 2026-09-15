# The whole thing started, headless — 15 September 2026

This is the record of starting **everything in this build that can start in this container**: the
world, the live services, the simulation on the real city, a 49 km drive across it, the signal table,
the synthetic baseline, the engine's own test suite, a 35-minute soak, and one rendered frame out of
the running world. Every number below was produced by the runs listed here, on this machine, in one
sitting. Where something is degraded, the degradation is named and measured rather than described.

## 1. What cannot run here — and it is not a matter of effort

The Unreal client is not startable in this container. Checked, read-only:

| checked | result |
|---|---|
| Unreal Engine installed | **no** — no `UnrealEditor` on the path, no `/opt/UnrealEngine` |
| GPU | **no** — `/dev/dri` absent, no Vulkan, no GL |
| display | **no** — `DISPLAY` unset |
| built game binary | **no** — no `NYCSim` executable, no `Binaries/` |

`unreal/NYCSim/NYCSim.uproject` is the project, and it needs an engine, a GPU and a screen. A window
with a drivable New York cannot be opened here, and this document does not pretend otherwise.

**What did start is the substance rather than a stand-in**: the simulation, the world data and the
live services all run headless, and the C++ binaries are built and current.

## 2. Conditions, so the numbers mean something

4 vCPUs, 16 GB RAM, load average **0.04** at the start — the v17 render pass was not running, so the
benchmark's own caveat (*"four vCPUs are shared with other agents and a wall-clock number without it is
not a measurement"*) is satisfied for the timed runs. Runs 3–7 below were measured on the idle machine.
The experiments in §10 ran **beside the soak** and are labelled as such; in each of them both arms
shared the same load, so the comparison inside a pair is fair even where its absolute level is not.

There is no `/usr/bin/time` in this container, so peak RSS is read from the kernel's own `VmHWM`
high-water mark just before the process is reaped.

## 3. The world — 24,042,069 records on disk

`data/processed/runtime`, 134 MB, read directly from the container index rather than from a manifest:

| container | sections | the counts that matter |
|---|---|---|
| `roadgraph.nycb` | 8 | **79,291 nodes, 122,235 segments, 381,971 lanes, 469,754 junction lanes**, 3,910,302 vertices, 588,201 yield links |
| `pois.nycb` | 3 | **1,082,160 POIs**, 85,023 places, 16.2 MB string table |
| `signals.nycb` | 2 | **19,814 controllers, 39,649 phases** |
| `density.nycb` | 4 | 18,864 cells, 334 NTA polygons |
| `transit.nycb` | 5 | **345 bus routes, 13,364 bus stops**, 21,963 route-stops |
| `tiles.nycb` | 1 | 2,916 tiles |
| `landmarks.nycb` | 2 | 65 landmark points |

The simulation re-derives more on load: **452,024 sidewalk nodes, 677,799 sidewalk edges,
104,456,504 m² of walkable surface and 226,012 walls**, in 1,267 ms.

## 4. The live services — every provider answered, nothing fell back

    PYTHONPATH=services python3 -m nycsim_live --once

| subsystem | provider | what came back |
|---|---|---|
| weather | **NWS**, station **KLGA** | 21.4 °C, dewpoint 11.6 °C, RH 53 %, wind 3.6 m/s from 170°, cloud 21 %, visibility 16,093 m, 1027.4 hPa, observation age **24 m 11 s** |
| sun | NREL SPA | azimuth 255.776°, elevation +20.006°, sunrise 06:36:35, sunset 19:04:46 |
| moon | Meeus 47/48 | azimuth 193.537°, elevation +24.499°, waxing crescent, **23.0 % illuminated** |
| ESB tower lights | live | **Red, White, Green — "In Honor of Mexico Independence Day"**, sunset to 02:00, `fallback: no` |
| tides and currents | NOAA **8518750** / **NYH1924** | −0.388 m NAVD88, current **2.211 m/s WSW ebb**, next low 22:13, next high 04:19 |
| world mapping | derived | wetness 0.000 (dry, τ 1,653 s), road ice no, fog 0.000, extinction 0.000243 1/m |

`missing fields: none`. **No subsystem entered its documented fallback** — this is a fully live boot,
not a degraded one. Written to `data/processed/live/`: `weather.json`, `world_state.json`,
`esb_lights.json`, `tides.json`, `snow_state.json`, `overlay.txt`.

## 5. The simulation on the real city — it runs, and it misses its budget by 3.6×

    ./core/build/bench/nycsim_bench city --steps 120 --warmup 30

| | |
|---|---|
| load | read 73 ms, graph 605 ms, signals 2 ms, density 341 ms, transit 181 ms; **287.5 MB** resident |
| router | attached in 2,360 ms |
| fleet | **4,549 vehicles, 21,239 pedestrians** |
| traffic step | mean **17.002 ms**, p50 16.785, p95 19.281, p99 19.965, max 22.043 |
| pedestrian step | mean **11.933 ms**, p50 11.819, p95 13.517, p99 15.231, max 17.601 |
| combined | mean **28.936 ms** wall, 28.933 ms CPU |
| contention | **0.0 %** of wall time off-CPU — the step is not being descheduled |
| budget | 8.000 ms at 20 Hz → **FAIL, 361.7 % of budget** |
| invariant | red-light entries by a law-abiding driver: **0** |
| peak RSS | **600.0 MB** |
| trajectory hash | traffic `7cc15acf170cd26a`, peds `54ce1e8bcd95e17d` |

A second run of the identical command gave 27.107 ms and a third 30.105 ms — a **10.6 % spread**,
which is why the deltas in §10 are argued from the trajectory hash and the counters rather than from
wall clock alone.

## 6. Driving across the city — 49.59 km, Fordham Road to Hylan Boulevard

    ./core/build/bench/nycsim_bench stream

| | |
|---|---|
| catalogue | **2,917 tiles** in 3,716 ms: 2,916 with terrain, 841 with buildings, **846,234 buildings** |
| route | 500 lanes, 499 segments, **49.43 km**, free flow 46.9 min, **32 Verrazzano segments** |
| drive | **49.59 km at 100 km/h, 35,706 scheduler updates over 29.8 simulated minutes** |
| update cost | mean **0.253 ms**, p50 0.249, p95 0.284, p99 0.334, max 0.543 |
| transitions | 2,917 loads, 428 unloads, 4,456 upgrades, 1,932 downgrades |
| tiers at peak | L0 9, L1 24, L2 507, L3 2,377, **unloaded 0** |
| protection ring | **0** transitions coarsened a tile within 300 m of the camera — as required |
| budget | 8.0 GB, **0** tile-updates coarsened, over-budget flag clear |

The drive completes and the protection ring holds. What the budget line means is **J124** below.

## 7. The signal table at scale — the window is transparent

    ./core/build/bench/nycsim_bench signals --steps 400

**19,814 plans** bound to 79,291 graph nodes, spanning 46 × 45 km; the densest 1 km cell holds 123
plans. Refreshing the whole table costs **0.647 ms** CPU per step; restricted to a 3,000 m window it
refreshes **978 plans (4.9 %)** at **0.020 ms** — **32.9× faster, 0.6271 ms saved per step, 7.84 % of
an 8 ms budget**. And it is not an approximation: **0 of 39,628 plan states differ** between the two
modes. (The published figure is 28.9×; this idle-machine run gives 32.9×. Same mechanism, less load.)

## 8. The synthetic baseline

    ./core/build/bench/nycsim_bench synthetic --steps 1200

14 avenues × 28 streets, 5,000 vehicles and 20,001 pedestrians: traffic **5.183 ms**, pedestrians
**6.980 ms**, combined **12.163 ms** mean (p95 13.940, p99 15.277), 0.0 % off-CPU, 19.1 MB resident.
Against the 8 ms budget: **FAIL, 152.0 %**. The published honest baseline is 14.6 ms; this run is
12.163 ms on an idle machine, and the report's own point stands — the wall clock is the weather.

## 9. The engine's own tests

    ./core/build/nycsim_core_tests

**145 test cases, 249,268 assertions, 0 failed, 0 skipped.** 58.2 s, 492.2 MB peak. Among what it
asserts on the way past: 0-60 mph measured at **8.49997 s** against the published 8.5 ± 0.8 s, and
6 of 6 cyclists reaching a bike lane.

## 10. The soak — 35 simulated minutes of churn

    ./core/build/bench/nycsim_bench soak --minutes 35 --vehicles 3000 --peds 12000 --city

**41,999 steps at 20 Hz, 693.7 s wall**, on the real city. It completed without a crash, a stall or a
dropped invariant:

| | |
|---|---|
| churn | **19,246 vehicle spawns / 17,821 despawns; 420,798 pedestrian spawns / 406,798 despawns** |
| population at the end | 1,425 vehicles, 14,000 pedestrians |
| RSS | 204 samples after the first simulated minute, **579.9 – 591.7 MB**, spread **11.74 MB** |
| **RSS slope** | **+0.3387 MB per simulated minute (+20.32 MB per simulated hour)** |
| peak RSS | 599.1 MB |

The slope is small in absolute terms and it is **not zero**, and it is 20× the bound this project sets
for itself. That is **J126** below.

## 11. A frame out of the running world

All twelve `drive_*` viewpoints were already rendered in the current v17 pass, carrying the current
`record_shape` 2, so an image of the running world exists without spending twenty minutes of contended
CPU to make another. `docs/verification/comparison/drive_midtown_sixth_ave_45th/sheet.png` — Sixth
Avenue at West 45th Street, looking uptown — reports what the renderer put in front of the lens:

| | |
|---|---|
| geometry | **4,500,100 triangles**: 7 building tiles (315,514), 245 park-ground surfaces on 7 tiles (275,593), 29,405 pavement polygons, 4,480 kit pieces, 9 landmark models |
| pavement breakdown | 13,095 `marking_white`, 6,020 sidewalk, 4,753 roadbed, 3,549 curb, 967 plaza, 652 crosswalk |
| agents | **53 vehicles and 242 people** from one frame of the traffic and pedestrian simulations, seed 20260907, after 120 s of simulated time |
| vehicle classes | 18 taxi, 9 sedan, 8 boro_taxi, 7 black_car, 5 SUV, 3 van, 1 box truck, 1 DSNY truck, 1 MTA bus |
| pedestrian LODs | LOD0 4, LOD1 45, LOD2 193 |
| instant | 2018-03-22T09:30−04:00, sun azimuth 115.5°, elevation 27.6° |

**What the frame does not show, from its own accounting — 3,241 agents dropped:**

| reason | count |
|---|---|
| vehicle outside radius | 977 |
| **pedestrian triangle budget** | **892** |
| pedestrian outside radius | 749 |
| **vehicle triangle budget** | **335** |
| pedestrian in the carriageway, not crossing | 153 |
| pedestrian not on a walkable surface | 76 |
| vehicle body has no rider (cyclists, e-bikes, pedicabs) | 22 |
| vehicle not on the carriageway | 18 |
| pedestrian over the observer | 17 |
| vehicle over the observer | 2 |

Plus **1,267 tree rows that did not fit the props budget**, props capped at 982,596 triangles and kit
capped at 741,974. The triangle budget is the binding constraint on the crowd, not the simulation:
**1,227 of 1,520 agents in range were dropped for triangles alone**.

Looking at the two halves side by side, the honest reading is that this frame is **massing and
population, not photorealism**: the near-field is a large featureless pale plane where the photograph
has a kerb, a hydrant and a 20-bike Citi Bike dock; the left-hand shells are blank pale masses with no
storefronts resolved, which is **J51** — 33 million window, door and storefront pieces render as
nothing behind unbroken walls; the trees are bare because the photograph's own date is 22 March, which
is **J114** working as designed. This frame's crowd was read back from a cached snapshot
(`snapshot_note: cached -2748_6306_9_0_78f919145bb1bdee_1788868452.json`), which is exactly the case
**J121** qualifies: a crowd read back from a snapshot is not bit-for-bit the crowd that was written.

## 12. J124 — the streaming budget cannot see 62.3 % of the bytes it is supposed to cap

The `stream` run reports `budget 8.0 GB; 0 tile-updates coarsened by the budget, over budget flag
clear`. That verdict is drawn over a catalogue that counts, per tile, only `terrain.png`,
`props.parquet` and `tile_buildings.glb` (`core/bench/bench_stream.cpp:97` and `:128`). Everything else
the engine streams per tile is absent. Measured across `blender_out/tiles`:

| per-tile asset | tiles | MiB | in the budget? | the engine asset it becomes |
|---|---|---|---|---|
| `tile_buildings.glb` | 841 | **3,157.1** | **yes** | `SM_Shells` (`manifest.py:108`) |
| `tile_pavement.glb` | 256 | **4,818.0** | **no** | `SM_Pavement` (`manifest.py:109`) |
| `tile_parkground.glb` | 120 | 190.2 | **no** | `SM_ParkGround` (`manifest.py:112`) |
| `tile_structures.glb` | 250 | 78.7 | **no** | `SM_Structures` (`manifest.py:110`) |
| `tile_buildings_nj.glb` | 64 | 124.2 | **no** | `SM_tile_buildings_nj`, via the catch-all at `manifest.py:113` |
| **total per-tile glTF** | | **8,368.1** | 3,157.1 counted | |

**5,211.0 MiB — 62.3 % of the per-tile bytes — is invisible to the cap**, and the single largest
streamed asset class, the pavement at 4,818.0 MiB, is bigger than all the buildings the budget does
count. The consequence is not academic, because the cap is 8 GB = **8,192 MiB** and the per-tile glTF
alone is **8,368.1 MiB — 176.1 MiB over the cap before a single mesh is decoded**, while the cost model
at peak reported **384.0 MiB**. That is **21.8× optimistic**, against the **9.1×** already recorded in
`performance/REPORT.md` §7 — the recorded figure is right about the model and measured it against the
counted subset only. Combined with the same section's finding that the most distant tier loads at 40 km
against a 46 × 45 km city, so the streamer holds the whole catalogue from anywhere on the route, the
honest statement is that **the budget is exceeded by the catalogue on disk and the model that decides
the budget cannot notice**. `nProps = 0` is set explicitly with a comment, so props contribute nothing
to the estimate either.

The same gap explains the run's other warning, `721 tile(s) with unreadable metadata`. It decomposes
exactly: **653 tile directories are empty** (one of them, `t_-3_16`, timestamped 13 September 12:27,
when the render pass's disk housekeeping ran) and **68 hold real content the catalogue cannot read** —
`manifest_nj.json` with `tile_buildings_nj.glb`, or `structures_manifest.json` with
`tile_structures.glb`. So 68 tiles carrying **28,096 New Jersey building solids** are counted by the
catalogue as having zero buildings and zero bytes; the catalogue's `846,234 buildings` is the New York
figure, and the true total is **874,330**.

**Open, not fixed here.** Fixing it is a change to what the budget measures, which would re-date every
streaming figure in `performance/REPORT.md`; and this boot was asked to start the game, not to re-price
it. What it costs to leave: the streamer's over-budget flag is not a safety net on the target machine.

## 13. J125 — 19,878 of 20,010 pedestrians are created without a route, and the published city step is measured on that crowd

The `city` run reports `1590 paths built, 20106 path failures` — read plainly, 92.7 % of pedestrian
routing failing. It is not that, and it is not harmless either. Four runs settle what it is:

| run | spawned | paths built | path failures |
|---|---|---|---|
| `--steps 1 --warmup 0` | 20,010 | **106** | **19,878** |
| `--peds 200 --steps 120` | 1,700 | 1,593 | **382** |
| `--peds 20000 --steps 120` | 21,500 | 1,590 | **20,106** |
| `--peds 20000 --steps 400` | 22,547 | 2,632 | **20,287** |

**Tripling the steps moves the failures by 0.9 %; cutting the crowd 100× cuts them 52.6×.** After a
single step 19,878 failures already exist, so they are produced by the **fill**, not by the simulation.

The cause is one line of harness. `PedSim::prefill()` lifts the per-step path budget with the comment
*"load time: no per-step budget"* (`core/src/peds/PedSim.cpp:904`) — it exists for precisely this
moment. The `city` benchmark's default path does not use it: `seedPedsNear()` calls `spawn()` in a
loop (`core/bench/bench_step.cpp:572`), `spawn()` calls `chooseGoal()` → `pathTo()`, and there
`max_paths_per_step = 96` is in force while `paths_this_step_` is only ever reset inside `step()`
(`PedSim.cpp:712`) — which does not run during a fill. So the first ~96 pedestrians get a route and the
rest are refused one, permanently: a refused pedestrian does not queue, it loses the goal and takes
*"a random continuation"* at each node until its next activity (`PedSim.cpp:611-613`, and the comment
at `:190` states it). The behaviour is deliberate and documented; being applied to 99.5 % of the crowd
at load is not.

**What it costs, matched fleet, only the budget changed** (identical 4,549 vehicles and 21,239
pedestrians, both arms at the same load):

| | `--max-paths 96` (default) | `--max-paths 1000000` |
|---|---|---|
| fill | 41 ms | 209 ms |
| paths built | 1,590 | **21,446** |
| path failures | 20,106 | **4,416** |
| pedestrian step | 11.324 ms | **13.611 ms** (+20.2 %) |
| combined step | 27.107 ms | 30.926 ms |
| kerb waits | 571 | **1,430** |
| jaywalking | 3 | **75** |
| pedestrian trajectory hash | `54ce1e8bcd95e17d` | `7fb2a42ba8c248c2` |

The hash changes, so this is behaviour and not noise — and the behaviour that appears is the behaviour
the city is supposed to have: pedestrians that wait at kerbs and cross streets. Two further numbers
fall out. **The real path-failure rate, once the deferrals are gone, is 4,416 of 21,446 searches =
20.6 %** — a genuine figure that the deferral count was hiding. And **routing the crowd costs
+2.287 ms on the pedestrian side**, which is where this touches the published record: `DEVIATIONS.md`
F1 quotes *"19.1 ms traffic and 15.5 ms pedestrians at 4,549 vehicles and 21,239 pedestrians"*, and
that fleet is the fingerprint of the default seeding — `--use-spawner` gives 2,396 vehicles and 17,785
pedestrians instead. So the published city-scale step is measured on the **cheaper, unrouted** crowd,
in the same entry whose prose says *"pedestrians now reach their goals instead of wandering"*.

To be fair to the record: `performance/REPORT.md` §5a calls this path *"the benchmark's seeding hack"*
in so many words and passes `--use-spawner` for its population figures, which is why its ring numbers
(1,021 vehicles in the ring) reproduced here exactly. The fault is not concealment; it is that the
**step-time** figures were taken on the hack and the fleet counts prove it.

**Open, not fixed here.** The one-line fix — have `seedPedsNear` lift and restore the budget the way
`prefill()` does — is not the whole job, because the published step times then need re-measuring and
F1's 38.3 ms becomes a figure for a crowd that does not commute. That is a measurement pass, not an
edit, and it is named here with both numbers rather than quietly corrected.
