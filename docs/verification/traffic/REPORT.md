# Traffic, routing and pedestrian models — verification report

Written by the orchestrator from the lane agent's delivery, after re-running the suite independently.
The harness blocks subagents from writing report files, so the agent supplied the content and the
orchestrator verified it before committing.

## 1. Result

```
$ ctest --test-dir core/build
100% tests passed, 0 tests failed out of 11
Total Test time (real) = 186.02 s
```

Re-run by the orchestrator. All eleven suites pass — util, geo, tiling, io, time, astro, weather,
vehicle, routing, traffic, peds — and the library builds with zero warnings under `-Wall -Wextra
-Wpedantic -Wshadow -Wconversion -Wsign-conversion -Wdouble-promotion -Wformat=2 -Wundef
-Wcast-align -Werror -fno-exceptions -fno-rtti`.

## 2. Four pre-existing defects found and fixed

These had never been exercised because the code had never been compiled or run against real data.

| Defect | Effect |
|---|---|
| `routing/NycbLite.h` read `index_offset` at byte 12 | The header is 24 bytes with natural alignment, so the field is at byte 16. Every real `.nycb` file was rejected — the router could not load the road graph at all. |
| `traffic/Signals.cpp` expected 28-byte controllers | The writer emits 32. Every real `signals.nycb` was rejected. After the fix it loads **19,814 signal plans** and the density table loads **262 neighbourhoods with 334 polygons**. |
| Synthetic grid ran segments node to node | Every straight junction connector was 0.05 m long, so intersections had no physical extent. |
| Right-turn rule said "rightmost travel *or bike* lane" | On any avenue with a bike lane, no motor lane could turn right: **21 of 158 travel lanes were reachable**. After the fix, 157 of 158. |

## 3. Behaviour, measured

| Check | Result |
|---|---|
| Deterministic replay | identical trajectory hashes at 13 checkpoints over 1,200 steps; a different seed diverges |
| Red-light compliance | 1,601 junction entries — 1,508 green, 83 yellow, 10 red, **none by a law-abiding driver** |
| No right on red | **zero**, including a control run where all 600 drivers were red-light runners |
| Collisions, 1,869 vehicles over 10 minutes | one overlapping pair in **22 of 3,000 sampled frames**, down from 77,407 overlaps before this session |
| Saturation flow | **1,708.6 veh/h/lane**, inside the 1,700–1,900 target from the Highway Capacity Manual |
| Bus dwell | 6 dwells, every one inside 15–45 s, over 8.3 km of route |
| Emergency yielding | 3 vehicles pulled right by 1.4 m |
| Spawn and despawn ring | 910 spawns, 909 despawns, **none inside the protected region around the player** |
| Player reaction | stops 6.83 m short of a stalled player car, 10.69 m short of a person on foot |
| Pedestrian wall containment | **zero** corridor violations and zero wall crossings over 1,500 pedestrians × 1,200 steps |
| Crossing compliance | 651 entries, 515 on the walk phase, **zero law-abiding violations**; jaywalker share 0.301 |
| Appearance uniqueness | **zero** duplicates among 900 pedestrians within 60 m, checked by brute force |
| Walking speed | 1.4024 m/s overall, 1.6024 m/s in Midtown |
| Density convergence | target 1,165.4 vehicles, 1,166 present; halving the calibration table gives 486 |

## 4. Performance — the one target not met

> **Correction, added by the orchestrator after stage 11.** The 35.57 ms figure below is **not
> reproducible**. The performance stage ran the same benchmark, grid, seed and 1,200 steps and measured
> **14.6 ms**, with every behaviour counter identical — same lane changes, honks, double-parked, reroutes.
> Only the machine differed. Do not quote 35.6 ms; the honest synthetic baseline is 14.6 ms, and the
> city-scale figure, which nobody had when this was written, is 777 ms. See
> `docs/verification/performance/REPORT.md`.

5,000 vehicles and 20,001 pedestrians, both wired to each other's probes, 1,200 measured steps:

| | mean | p50 | p95 | p99 |
|---|---|---|---|---|
| traffic step | 18.07 ms | 18.53 | 26.88 | 34.18 |
| pedestrian step | 17.50 ms | 18.31 | 26.15 | 32.02 |
| **combined** | **35.57 ms** | 34.54 | 47.70 | 55.99 |

The brief set an 8 ms budget; this is 4.4× over, and the agent says so plainly rather than
re-describing the target. Two things are worth separating:

* **The model keeps up with its own clock.** A 20 Hz fixed step is 50 ms, so at 35.6 ms mean the
  worker thread stays ahead with about 29 % headroom — but the 95th percentile at 47.7 ms and the
  99th at 56.0 ms mean it does *not* stay ahead in the worst frames. It is not comfortable, and on a
  quiet machine the best observed figure was 24.8 ms, so a good part of the spread is contention with
  the five other agents sharing four cores.
* **The 8 ms target was for a worker thread beside a 60 fps renderer**, where a spike must not steal
  a frame. That margin does not exist today.

Already applied: adaptive spatial-hash cell sizing (the pedestrian hash was clearing 2.2 million cells
a step, worth about 8 ms on its own), lane-change evaluation staggered to 4 Hz, pedestrian probes at
5 Hz, budgeted routing at 8 queries a step, and segment-level route relinking instead of full
re-routes. What remains is the per-agent decision work itself; reaching 8 ms needs a structure-of-arrays
layout and multithreading across tiles, which is a separate piece of work.

One related item for the city-scale run: `SignalTable::cacheStates` is O(plans × 8) per step, which is
3,000 operations on the synthetic grid but **158,000 on the real 19,814-plan table**. It should be
restricted to loaded tiles before the city is stepped.

## 5. Calibration constants and their sources

Car-following is the Intelligent Driver Model with δ = 4 (Treiber, Hennecke and Helbing, 2000), car
b = 2.0 and s₀ = 2.0, truck a = 0.8, b = 1.5, T = 1.6, s₀ = 2.5 (Treiber and Kesting, 2013,
tables 11.2 and 11.3). **Two deliberate departures, both commented in the code**: passenger-car
acceleration raised to 1.7–2.0 m/s² because table 11.2 is a motorway calibration while urban queue
discharge is 1.5–2.0 m/s², and car headway T = 1.0 s, which with s₀ = 2 m and a 4.885 m body
reproduces the Highway Capacity Manual's saturation headway of about 1.9 s.

Lane changing is MOBIL with politeness 0.2, threshold 0.2 and safe braking 4.0 (Kesting and others,
2007). Signals use 90 s cycles in the central business district and 60 s elsewhere, 3.0 s yellow,
2.0 s all-red and a 7 s leading pedestrian interval, per NYC DOT standards; the flashing don't-walk
interval is the crossing distance divided by 1.07 m/s, the 3.5 ft/s of MUTCD §4E.06. **No right on
red is absolute**, per NYC Traffic Rules §4-03(a)(2). Unsignalized gap acceptance uses critical
headways of 4.1, 6.2, 6.5 and 7.1 s with a 3.3 s follow-up (Highway Capacity Manual, 6th edition,
exhibit 20-14); a full stop is 0.35 m/s held for a second, per NY Vehicle and Traffic Law §1172, with
right of way from §1141 and §1142, emergency pull-right from §1144 and the red-light exemption from
§1104(b)(2). Pedestrian desired speed is N(1.40, 0.20) m/s clipped to [0.6, 2.2] — Weidmann (1993)
gives 1.34 ± 0.26 — and N(1.60, 0.20) in Midtown, with social-force parameters τ = 0.5 s, A = 2.1 m/s²,
B = 0.3 m (Helbing and Molnár, 1995) and the contact term from Helbing, Farkas and Vicsek (2000).

## 6. Stated gaps

1. **The 8 ms performance target is not met** (§4).
2. **The jaywalking share of 0.30 is a modelling target, not a measurement.** No New York field count
   of signal non-compliance exists in this repository. The figure sits inside the 20–50 % range in the
   literature and is a single exposed constant for a future pedestrian-count stage to replace.
3. **Box-blocking probability** (0.02 free-flowing rising to 0.35 in a jam) is a calibration handle,
   not a measurement.
4. **Residual overlaps.** Vehicle bodies are separated by an impenetrability projection at the end of
   every step, and 22 of 3,000 sampled frames still catch one pair mid-separation at a junction entry,
   each clearing within two or three frames. The two tests that cannot assert an exact zero carry the
   measured value and the reason in the assertion itself.
5. **Jaywalking is modelled as crossing against the signal at a crosswalk**, not as mid-block crossing
   with its own geometry.

## 7. Interface for the Unreal agents

The simulation exposes no engine types, throws nothing, and allocates nothing after `configure()`.
Vehicles read back as position, heading, speed, acceleration, lateral offset, state (driving, stopped
at line, waiting for right of way, double parked, dwelling at a bus stop, taxi pickup) and flags for
brake lights, siren, taxi roof light, yielding to an emergency vehicle, law-abiding, blocking the box
and having a route. Honking events drain per step with position, class and reason. Pedestrians read
back as position, velocity, activity (walk, wait at kerb, cross, browse, sit, jog, photograph, hail a
cab, ride away, enter the subway), flags and a twelve-dimensional variety vector.

**The variety vector is the contract with the Blender NPC generator**: age band (4 levels), stature
(6), body mass (6), skin tone (8), hair style (10), hair colour (8), top garment (10), top colour (12),
bottom garment (8), bottom colour (12), footwear (6), accessory (10) — 63,700,992,000 distinguishable
appearances, packed mixed-radix into a 64-bit signature, with no two agents inside 60 m sharing one.
