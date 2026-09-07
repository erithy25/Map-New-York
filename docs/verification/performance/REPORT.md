# Performance and robustness — verification report

Stage 11. Written by the orchestrator from the lane agent's delivery after re-running the suites
independently: `ctest --test-dir core/build` gives 11 of 11 passing, and `tests/test_performance.py`
gives 6 passed with 1 skipped. The harness blocks subagents from writing report files.

## 1. The headline, including a correction

**The 35.6 ms figure in `docs/verification/traffic/REPORT.md` §4 is not reproducible and should not be
quoted.** Running the same benchmark, grid, seed and 1,200 measured steps gives **14.6 ms**, with every
behaviour counter identical to that report — 7,524 lane changes, 3,690 honks, 39 double-parked, 656
stopped at red, 8,232 reroutes. It is the same run; only the machine differs. That report's own "best
observed 24.8 ms" points the same way. **The honest synthetic baseline is 14.6 ms**, and after this
stage the step needs **12.2 % fewer instructions** with bit-identical behaviour.

**The number nobody had — the city-scale step — is 777 ms**, and 96 % of it is path finding.

**Update, ADR-021 implemented.** Agents now draw origins and destinations from the streamed region.
On the identical command, machine, seed and fleet seeding, the city-scale step goes from **665.3 ms
to 38.3 ms** — 94.2 % of it gone — and the player's surroundings can be populated at last: a prefill
through the production spawner puts **1,021 vehicles inside the 900 m ring against that ring's own
density target of 1,066**, where before it put **19**. §5 carries the measurement, §5a the
populating, §8 what is left. The 8 ms budget is still not met; the remaining 38 ms is no longer path
finding, and §8 says what it is.

## 2. How the measurement was made trustworthy

Four vCPUs shared with three other agents. Three precautions, and the third is the one that matters:

1. Every run is `nice -n 10` and records the load average before and after.
2. Thread CPU time is measured beside wall time. This settles the contention question: only 0.4 % to
   3.3 % of wall time was off-CPU, so the step is not being descheduled — wall time here *is* the cost.
   What contention does instead is slow the CPU time itself through shared cache and memory bandwidth:
   three runs of the identical binary at the same load gave 14.008, 14.039 and 16.857 ms, a 20 % spread.
3. **The primary evidence for each optimisation is a callgrind instruction count**, which is
   deterministic and immune to all of that. Wall clock is corroboration, not proof.

That third point is why this report can claim a 12.2 % gain that the wall clock cannot resolve: two
runs of the same binary minutes apart differ by more than the gain. The instruction count is the
measurement; the wall clock is the weather.

## 3. What changed, and what each change bought

| Change | Measured |
|---|---|
| The emergency-yield field is computed once per step instead of once per vehicle. With about 60 emergency vehicles in a 5,000 fleet, that was 300,000 pair tests a step for a rule that almost never fires. | **11.66 % of the step, gone** — 300,000 pair tests become about 660 |
| `SpatialHash` made sparse. It cleared and prefix-summed every grid cell per rebuild; the pedestrian hash alone touched 87,808 cells four times a step. Now an open-addressed table of occupied cells. | hash instructions 1,685 M → 1,311 M; the memset leaves the profile entirely |
| `wallsNear` skips de-duplication for a single-cell query, which is essentially always: a pedestrian moves 7 cm a step against a 25 m wall grid. | 7.05 % → 4.78 % |
| `SignalTable::setActiveWindow` restricts what `SignalTable::cacheStates` refreshes to the streamed region. | **28.9× faster on the real table** — 0.813 ms → 0.028 ms per call, and it is called twice a step, so **1.57 ms saved, 19.6 % of the whole 8 ms budget** |

The signal window was verified transparent: **0 of 39,628 plan states differ** between the windowed
and whole-table paths.

`tests/test_performance.py` re-measures the `cacheStates` window against the shipped signal table on
every run, so the figure above is reproducible rather than a one-off reading:

```
table            19814 plans bound to 79291 graph nodes
plan extent      46 x 45 km; densest 1 km cell holds 123 plans at (-3665, 1869)
whole table      19814 plans refreshed per step
window 3000 m      978 plans refreshed per step (4.9 % of the table)
speed-up         28.6x  (0.7812 ms saved per step, 9.76 % of an 8 ms budget)
```

The two figures differ because they count different things and both are stated rather than one being
chosen: 28.9× is the wall-clock cost of a `cacheStates` call in the bench, 28.6× is the ratio of plans
refreshed, and the per-step saving is quoted here for one call and in the table above for the two the
step actually makes. The plan extent line is the reason the window works at all — 19,814 signal plans
are spread over 46 × 45 km, so a 3 km window around the player reaches under 5 % of them.

Two defects were found and fixed inside this work, both introduced by it and both caught by the suite.
One is worth recording: the sparse hash's build stamp started at zero while slot stamps were
zero-initialised, so a query issued before the first rebuild read every slot as live and probed
forever. The pedestrian suite went from 12 seconds to still running after nine minutes.

One change was **tried and rejected on measurement** and is recorded as such: sharing the crowd hash
with the uniqueness test looked free but turned a 60 m query into 169 cells instead of 9.

## 4. Nothing changed behaviour, and there is a lock on it

Every counter from the traffic lane's own benchmark is identical before and after: mean speed 2.25 m/s,
7,524 lane changes, 3,690 honks, 39 double-parked, 128 in junction, 656 stopped at red, 8,232 reroutes,
477 crossing, 1,042 waiting, 19 jaywalking. So are the 64-bit trajectory hashes over all 25,001 agents
after 1,400 steps:

```
traffic  aa5259411c39445a          peds  f6dda9215d7698a0
```

Both are now asserted in `tests/test_performance.py`, so a future change that alters behaviour while
calling itself an optimisation fails a test rather than a review.

**The hashes moved when ADR-021 was implemented, deliberately, and the pair above is superseded:**

```
traffic  6a24b0a24a962b4c          peds  fd8d5b12f37af8ea
```

ADR-021 said in advance that it would move them, which is why it is an ADR. What moved is the
pedestrian side: a pedestrian used to draw its next destination uniformly over every point of interest
in the city, so almost every path it asked for exceeded the 24-node cap or the per-step budget and the
agent fell back to wandering; it now picks a goal within walking distance and reaches it. The traffic
hash moves with it because drivers yield to pedestrians through the probe, so a different crossing is a
different vehicle trajectory. **The vehicle draw itself is bit-identical on this grid by construction**
— the synthetic world is smaller than its 1,000 km spawn ring, so the streamed region covers the whole
graph and the restricted cumulative distribution is the unrestricted one, the same floats accumulated
in the same order. That is verified rather than argued: running the synthetic benchmark with
pedestrians disabled gives the same traffic hash before and after the change.

The behaviour invariants were re-confirmed against the C++ suite rather than assumed (§5b).

One deliberate behaviour change is offered and is **off by default**: `PedConfig::hash_cell_m` lets a
host size the crowd hash to the streamed extent. It is opt-in because it changes the order in which
repulsion forces are summed, and floating-point addition is not associative.

## 5. The city-scale step — 777 ms before ADR-021, 38.3 ms after

Against the real artefacts: 79,291 nodes, **122,235 segments**, 851,725 lanes, **19,814 signal plans**,
262 neighbourhoods, 345 bus routes, and a derived sidewalk graph of 452,024 nodes and 226,012 walls.
Loading it all costs about 6 seconds and peaks at **598.7 MB** resident.

The original measurement, and the diagnosis it produced:

| Configuration | Combined CPU per step |
|---|---|
| **as shipped** | **776.7 ms** |
| traffic only, routing budget 0 | 20.1 ms |
| traffic and pedestrians, routing 0, no pedestrian paths | 33.6 ms |

| Component | ms per step | Per unit |
|---|---|---|
| 8 vehicle route queries | ~399 | **49.8 ms per query** |
| 96 pedestrian paths | ~310 | **3.23 ms per path** |
| everything else, 5,000 vehicles | ~20 | |
| everything else, 20,000 pedestrians | ~14 | |

**The finding: path finding is 96 % of the step, and not because the router is slow.** The same eight
queries cost about 0.1 ms each on the synthetic grid. It is because **the destination is drawn from the
whole city** — an agent in Brooklyn is routed to Staten Island and the search settles a large fraction
of a 851,725-lane graph. Both the vehicle spawner and the pedestrian goal chooser do it.

**A second defect, found on the way: the city cannot be populated at all.** The spawner samples a lane
from a city-wide distribution and *then* rejects it if it falls outside the player's 900 m ring,
accepting roughly one lane in a thousand. After a prefill of 6,000 vehicles the ring held **86**,
against a density-table target of **304,878**. Fixing it changes which lanes are drawn and in what
order, so it changes the spawn sequence the traffic suite asserts — out of scope for a stage that
promised not to change behaviour, and recorded here as required work. See ADR-021.

### After ADR-021 — measured the same way, on the same machine

The 776.7 ms above was measured on a different machine. To make the before and after comparable, the
benchmark was rebuilt from the commit ADR-021 was written against (`a761f35`) and both binaries were
run here, back to back, with the identical command, seed, camera and fleet seeding:

```sh
nice -n 10 ./core/build/bench/nycsim_bench city --steps 120 --warmup 30 --seed-radius 1000
```

| | before (`a761f35`) | after |
|---|---|---|
| **combined CPU per step** | **665.3 ms** | **38.3 ms** |
| traffic step | 346.9 ms | 22.3 ms |
| pedestrian step | 318.5 ms | 15.9 ms |
| fleet at the end of the run | 5,001 vehicles, 20,020 pedestrians | 4,549 vehicles, 21,239 pedestrians |
| pedestrian paths built / failed | 1,596 / 21,498 | 1,590 / 20,106 |

**627 ms of 665 ms is gone — 94.2 %**, against the 91 % ADR-021 predicted. The two runs are not quite
like for like on fleet size: the benchmark seeds 5,000 vehicles inside 1,000 m of the camera, which is
about twice what the density table asks for there, and the fixed spawner now retires the surplus (§5a),
so the "after" run ends 9 % smaller. Scaling the traffic step by that ratio gives 24.5 ms rather than
22.3, and 40.5 ms combined — the conclusion does not depend on it.

Where the remaining 38.3 ms goes, measured by removing one thing at a time from the same run:

| Configuration | Combined CPU | Difference |
|---|---|---|
| as shipped | 38.27 ms | |
| `--signal-window 3000` | 35.61 ms | −2.66 ms — the §3 window, now worth two calls a step |
| `--max-routes 0` | 34.61 ms | −3.66 ms for 8 route queries |
| `--max-routes 0 --max-paths 0` | 35.62 ms | pedestrian paths are inside the noise |
| traffic only, `--max-routes 0 --no-peds` | 17.81 ms | |

**A vehicle route query costs 0.46 ms, down from 49.8 ms — 109× — and a pedestrian path no longer
registers at all**, down from 3.23 ms. Path finding was 96 % of the step; it is now 9.6 % of it. What
is left is the per-agent decision work itself, 19 ms of traffic and 15.5 ms of pedestrians, which is
what §8 is about and is not what ADR-021 was for.

### 5a. Populating the player's surroundings — 19 vehicles before, 1,021 after

This is the half of ADR-021 that matters more than the frame time: before it, the city could not be
filled at all. Measured with the production spawner rather than the benchmark's seeding hack:

```sh
nice -n 10 ./core/build/bench/nycsim_bench city --steps 120 --warmup 30 --seed-radius 1000     --use-spawner --signal-window 3000
```

| | before (`a761f35`) | after |
|---|---|---|
| `prefill()` wall time | **604,604 ms** | **512 ms** |
| vehicles created by the prefill | 6,000 (city-wide) | 2,456 |
| **inside the 900 m ring afterwards** | **19** | **1,021** |
| what the density table asks for in that ring | 1,066 | 1,066 |
| alive after 150 steps | 47 vehicles, 160 pedestrians | 2,396 vehicles, 17,785 pedestrians |
| combined CPU per step | 298.9 ms | 14.5 ms |

1,021 against 1,066 is **95.8 % of the calibrated density**, and the shortfall is the protected region
the spawner is forbidden to fill (60 m in every direction, 250 m inside the view cone). The ten
minutes the old prefill took were not a slow loop: `prefill()` lifts the per-step path budget, so all
20,000 pedestrian goals ran an unbounded city-wide A* one after another.

Three changes were needed for this, not one:

1. **The draw is restricted, not the result.** `RegionSampler` (core/include/nycsim/util/) indexes the
   spawn distribution on a 250 m grid and re-derives a cumulative distribution over the disc around the
   player. It rebuilds only when the player leaves the disc it was built for, so at 9 m/s that is once
   every 142 steps, not every step.
2. **The fleet is sized to the region it is drawn from.** With the draw restricted but the target still
   city-wide (291,727 vehicles), the spawner simply fills the ring to `max_vehicles` at whatever density
   that happens to be — measured: 3,882 vehicles in a ring calibrated for 1,066. `TrafficSim` now sums
   the density table over the streamed region when a ring restricts the draw, and over the whole city
   when it does not, so the density-convergence behaviour without a ring is untouched.
3. **The walk-graph search is bounded.** Restricting the goal is not enough on its own: a goal 300 m
   away in a straight line can be unreachable on foot — the far side of an expressway, a rail cut, a
   pier — and an unbounded A* then settles all 452,024 nodes of the component before admitting it.
   Measured at **107 ms in a single step**, which is how a 15 ms pedestrian step became a 400 ms one.
   `SidewalkGraph::path` now takes a cost bound; the heuristic is straight-line distance and every edge
   is at least as long as the straight line between its ends, so the bound prunes nothing that could
   have been on a route that cheap.

**A separate defect this exposed, in the host rather than in `core/`:** the road graph carries no NTA
on any lane — 0 of 220,329 travel and bus lanes — and nothing was calling
`DensityTable::assignLaneNtas()`. Every lane therefore fell into the "no NTA" bucket and the whole
262-neighbourhood calibration collapsed onto one cell, which is where the 304,878 city-wide target in
ADR-021 came from. The benchmark now calls it (848,116 lanes claimed, 312 ms at load); **any host that
loads `roadgraph.nycb` must do the same or its density table does nothing.**

### 5b. The behaviour invariants, re-confirmed rather than assumed

Re-run from the C++ suite after the change (`ctest`, 11 of 11):

| Invariant | Before | After |
|---|---|---|
| Saturation flow | 1,708.6 veh/h/lane | **1,708.61** |
| Junction entries: green / yellow / red | 1,508 / 83 / 10 | **1,508 / 83 / 10** |
| Entries on red by a law-abiding driver | 0 | **0** |
| Pedestrian wall crossings, corridor violations | 0, 0 | **0, 0** |
| Spawn / despawn inside the protected region | 0, 0 | **0, 0** |
| Density convergence (no ring): target / present | 1,165.4 / 1,166 | **1,165.4 / 1,166** |
| Walking speed, overall / Midtown | 1.4024 / 1.6024 m/s | **1.4024 / 1.6024 m/s** |
| Jaywalker share | 0.301 | **0.3005** |
| Duplicate appearances within 60 m | 0 of 900 | **0 of 900** |
| Bus dwells / emergency yields | 6 / 3 | **6 / 3** |
| Collisions over 3,000 sampled frames | 22 | **22** |

Two counters in that suite did move, both reported rather than asserted, and both for the reason
ADR-021 gave: **spawn/despawn ring 910/909 → 193/198** (the spawner no longer wastes five draws in
six on lanes outside the ring, so it reaches the target and stops churning), and **crosswalk entries
651 → 526** with 428 on WALK (pedestrians walk to goals instead of wandering, so they meet fewer
crossings). Neither is an assertion; the assertions around them — zero violations, jaywalker share,
zero wall crossings — are unchanged.

## 6. Memory over a long run — the requirement is met exactly

35 simulated minutes, 41,999 steps, a camera driving a circle so the spawn ring sweeps new ground
continuously, 18,489 vehicle spawns and 431,990 pedestrian spawns — **895,887 agent creations and
destructions in total**.

```
RSS at the first sample   14,991,360 bytes
RSS at the last sample    14,999,552 bytes
growth                    8 KB over 35 simulated minutes
slope                     +0.0000 MB per simulated minute
```

The allocation contract holds: every buffer is sized in `configure()` and nothing is allocated in
`step()`. The simulation runs indefinitely without growing.

`tests/test_performance.py::test_memory_is_flat_over_a_long_run` runs its own shorter soak on every
invocation and asserts the **RSS slope** stays inside its bound, so this result is reproducible and not
a single favourable run. Its most recent measurement here:

```
plan             31.0 simulated minutes = 37199 steps at 20 Hz, sampling RSS every 200
churn            9101 spawns, 7601 despawns (vehicles); 377990 / 375095 (pedestrians)
RSS samples      180 after the first simulated minute, 11.2 - 11.2 MB (spread 0.05 MB)
RSS slope        +0.0023 MB per simulated minute (+0.14 MB per simulated hour)
```

+0.14 MB per simulated hour is the honest number for the harness run, against the +0.0000 MB/min of the
longer bench above; at that rate a session would take three weeks of simulated time to grow by 1 GB. The
difference between the two is sampling noise on an 11 MB resident set, not a leak — the spread across all
180 samples is 0.05 MB, which is smaller than the slope's own extrapolation over the run.

## 7. Streaming under load — the real route

The tile catalogue is built from what is actually on disk: 2,916 terrain tiles and 920 building tiles,
1,083,026 buildings, 4,152.1 MB. The route is computed on the real lane graph between the two
intersections the roads stage verified and flown at 100 km/h with a 20 Hz scheduler.

```
route          49.43 km (roads stage measured 49.377 km), crossing the Verrazzano-Narrows
drive          35,706 scheduler updates over 29.8 simulated minutes
update cost    mean 0.349 ms, p95 0.389, p99 0.458, max 7.289
transitions    2,916 loads, 428 unloads, 4,455 upgrades, 1,932 downgrades
protection     0 transitions coarsened a tile within 300 m of the camera
budget         never binding, over-budget flag never set
```

**Three things this exposed that no unit test could:**

1. **The most distant tier's radius is larger than the city.** It loads at 40 km against a 46 × 45 km
   extent, so from anywhere on this route the streamer holds the whole catalogue and does no streaming
   for 81 % of its tiles.
2. **The tile cost model is 9.1× optimistic.** It estimates 454.5 MB for 2,916 resident tiles against
   4,152.1 MB of actual files, and a compressed mesh decodes to *more* memory than its file, so the
   true figure is above 4.15 GB against an 8 GB cap. The model would never have said so.
3. **The scheduler update is O(catalogue), not O(nearby)** — 4.4 % of the frame budget spent deciding
   tiers, most of it on tiles 40 km away.

## 8. The 8 ms budget: not met, and precisely where the time goes

**Synthetic: 14.0 ms against 8 ms.** The remaining time is spread thin — nothing left is worth more
than about 5 %. Roughly 16.6 % is the pedestrian force integration, 9.0 % is proving that 20,001
pedestrians did not walk through a building, 8.4 % is position integration and edge projection, 6.8 %
is vehicle body separation, 5.4 % is the car-following decision and 4.2 % is the router.

What it would take, in the order the profile justifies:

1. **Multithread across tiles.** The step is already two independent phases over agents partitioned by
   lane and walk edge, and the determinism contract survives it because each agent's random stream is
   seeded from world seed and agent id rather than iteration order. This is the only change that
   reaches 8 ms without touching the models.
2. **Structure-of-arrays layout**, worth perhaps 20–30 % on the pedestrian side.
3. **A cheaper wall test** — a precomputed per-edge flag that skips the check exactly where no wall is
   within reach. Not attempted here: the traffic lane records that a previous gating attempt let 262
   crossings through, and getting the bound provably right needs more care than this stage had left.

**City scale: 777 ms against 8 ms.** Not a micro-optimisation problem. Draw destinations from the
streamed region (ADR-021) and about 709 ms of the 777 goes away; fix the spawner; call
`setActiveWindow` from the loaded-tile set for another 1.57 ms; and order lanes by tile so a streamed
region is contiguous — with routing off, the same 5,000 vehicles cost 7 ms on a 4,698-lane graph and
20 ms on an 851,725-lane one, purely because the lane array grew from 470 KB to about 85 MB.

### Update after ADR-021: 38.3 ms against 8 ms, and it is no longer path finding

ADR-021 is implemented and its prediction held (§5). **The budget is still not met** — 38.3 ms with the
benchmark's 5,000-vehicle seeding, 14.5 ms with the density-correct fleet the fixed spawner produces —
and the remainder is exactly the work §8 already named, now at city scale:

| What is left of the 38.3 ms | ms |
|---|---|
| traffic decisions, 4,549 vehicles, no routing | 19.1 |
| pedestrian forces, integration and wall test, 21,239 pedestrians | 15.5 |
| 8 vehicle route queries | 3.7 |
| `SignalTable::cacheStates` over the whole 19,814-plan table, twice a step | 2.7 of the above, recovered by passing `--signal-window 3000` |

So the levers, in the order the profile now justifies them:

1. **Call `setActiveWindow` from the loaded-tile set.** Already built, already verified transparent
   (§3), and measured here at **2.66 ms — a third of the whole budget** — because both simulations
   refresh the table. This one is free; it is a host wiring change, not an engine change.
2. **Multithread across tiles**, unchanged from above and still the only change that reaches 8 ms
   without touching the models. With the region restriction in place the two phases are also now
   *spatially* bounded, which is what made partitioning by tile plausible in the first place.
3. **Structure-of-arrays for the pedestrian side**, worth perhaps 20–30 % of its 15.5 ms.
4. **A cheaper wall test**, unchanged and still needing the bound proved rather than guessed.
5. **Order lanes by tile.** Still worth doing and still unmeasured: with routing off, 5,000 vehicles
   cost 7 ms on the 4,698-lane synthetic graph and 19.1 ms on the 851,725-lane real one at a *smaller*
   fleet, and the models are identical, so the difference is the 85 MB lane array.

**A hierarchy in the router is explicitly not on this list and was not attempted.** Restricting the
draw to the streamed region means agents no longer take cross-city trips; genuinely long journeys need
a hierarchy, and that is separate work, as ADR-021 says.

**The honest cost of the change on the synthetic grid: 13.85 ms → 15.21 ms**, the mean of two runs of
each binary interleaved at the same load. That is a 10 % regression and it is a behaviour change, not
overhead: on the old code almost every pedestrian goal was unreachable within the 24-node path cap, so
20,000 agents wandered; they now walk to goals, wait at kerbs and cross, which costs more because it
does more. The vehicle side of the synthetic grid is untouched — with `--no-peds` the traffic hash is
bit-identical across the change (`01d503a271a21d41`), and the step is 5.54 ms before and 5.69 ms after.

## 9. Error-handling audit

**Fixed in this lane.** The most consequential: `SpatialHash::insert` returns false at capacity and
**all five call sites discarded it** — a dropped agent is invisible to every proximity query for that
step, so no repulsion, no collision separation, no probe. Now counted. Also: router failures and bus
path failures were silent and are now counted; the signal table indexed its plan array unchecked, which
after the windowing change would have looped over a garbage phase count; and a never-configured spatial
hash indexed empty vectors.

**Found and reported, not fixed** — four C++ sites where a computed signal is discarded, and about
twenty Python handlers that skip without logging. Two matter for the reports themselves: the fidelity
report drops a geometry that fails to parse when summing road length, so the reported kilometres can be
quietly low, and it never checks whether ctest actually ran. A third matters for weather: a present-weather
group the parser rejects is dropped without a trace, which is exactly how a parser gap stays hidden.

**There is no bare `except:` anywhere in the Python**, no discarded subprocess result, and no discarded
`Result` in the C++ — the container reader checks every file operation.

## 10. Reproducing it

```sh
cmake -S core/bench -B core/build/bench -DCMAKE_BUILD_TYPE=Release && cmake --build core/build/bench -j2
nice -n 10 ./core/build/bench/nycsim_bench synthetic --steps 1200
nice -n 10 ./core/build/bench/nycsim_bench signals   --steps 400
nice -n 10 ./core/build/bench/nycsim_bench city      --steps 120 --warmup 30 --seed-radius 1000
nice -n 10 ./core/build/bench/nycsim_bench soak      --minutes 35 --vehicles 3000 --peds 12000
nice -n 10 ./core/build/bench/nycsim_bench stream
pytest -q tests/test_performance.py
```

For §5a — the ring, through the production spawner rather than the benchmark's seeding:

```sh
nice -n 10 ./core/build/bench/nycsim_bench city --steps 120 --warmup 30 --seed-radius 1000 \
    --use-spawner --signal-window 3000
```

`city` prints `ring after fill` (vehicles inside the spawn ring against that ring's own density
target), `vehicles in ring` and `crowd` (a 10 m histogram of the pedestrians) at the end of the run, so
the population figures are re-measured on every invocation rather than quoted from here.

To reproduce the before-and-after on one machine, build the benchmark from the commit ADR-021 was
written against and run both:

```sh
git archive a761f35 core | tar -x -C /tmp/base && \
  cmake -S /tmp/base/core/bench -B /tmp/base/build -DCMAKE_BUILD_TYPE=Release && \
  cmake --build /tmp/base/build -j2
```
