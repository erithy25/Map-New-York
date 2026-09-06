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
| `SignalTable::setActiveWindow` restricts the phase refresh to the streamed region. | **28.9× faster on the real table** — 0.813 ms → 0.028 ms per call, and it is called twice a step, so **1.57 ms saved, 19.6 % of the whole 8 ms budget** |

The signal window was verified transparent: **0 of 39,628 plan states differ** between the windowed
and whole-table paths.

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

One deliberate behaviour change is offered and is **off by default**: `PedConfig::hash_cell_m` lets a
host size the crowd hash to the streamed extent. It is opt-in because it changes the order in which
repulsion forces are summed, and floating-point addition is not associative.

## 5. The city-scale step — 777 ms, and why

Against the real artefacts: 79,291 nodes, **122,235 segments**, 851,725 lanes, **19,814 signal plans**,
262 neighbourhoods, 345 bus routes, and a derived sidewalk graph of 452,024 nodes and 226,012 walls.
Loading it all costs about 6 seconds and peaks at **598.7 MB** resident.

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
