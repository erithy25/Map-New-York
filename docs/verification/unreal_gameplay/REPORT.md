# Stage report — Unreal gameplay (player vehicle, character, cameras, traffic, pedestrians, GPS, audio)

**Agent:** Unreal agent 2 · **Date:** 2026-09-06 · **Engine target:** UE 5.4 · **Compiled here:** no engine in the
container (ADR-001), so nothing Unreal-facing was compiled; everything core-facing *was* compiled and run.

| | |
|---|---|
| Files written | **72** (64 Unreal, 8 core-facing adapter), 20,024 lines |
| Executable verification | `unreal/tools/gameplay_selftest.cpp` — **74 checks, 0 failures**; `docs/verification/unreal_gameplay/check_gameplay_sources.py` — **1,037 checks, 0 failures** |
| Self-review record | `unreal/COMPILE_CHECKLIST_GAMEPLAY.md` |
| Audio shipped | 7 stations, **65 tracks** (368 min, 247 MB) + **8 SFX**, every file with a machine-checked licence record |
| Build.cs | untouched — every module needed was already listed |

---

## 1. What was built

**The player's car.** A Chaos-based `ANYCPlayerVehicle` bound to the Blender mesh naming contract: `Body`,
`Wheel_*`, `Door_*`, `SteeringWheel`, `Wiper_*`, `Window_*`, `Mirror_*` with the `MIRROR_GLASS*` slots, the
`LIGHT_*` emissive slots, `GAUGE_SPEED` / `GAUGE_RPM` / `SCREEN_CENTER`, `PLATE_FACE`, the `DMG_*` morph regions
and the `UCX_*` collision convention. Tyre friction is driven per wheel by the traced physical surface and by
`MPC_Weather`'s wetness, snow and ice. Working dashboard (damped needles, odometer, trip, instant MPG, warning
lamps, a centre screen that hosts the GPS widget), scene-capture mirrors, FMVSS-108 light timing (85 flashes/min,
hyperflash on a failed bulb, 180/250 ms halogen vs 20/25 ms LED response), rain-rate-driven wipers with five
intermittent detents and an AUTO mode, power windows, horn, and five damage regions with lamp breakage and glass
cracking.

**Cameras.** Chase, hood, bumper, interior (head look, lateral lean under cornering load, steering glance, road
shake), cinematic (five shots on a timer) and photo mode (free-fly cine camera with focal length, aperture, focus
distance and a time pause).

**The player on foot.** `ANYCPlayerCharacter` on the UE5-Mannequin skeleton with the 40-clip animation set, a full
locomotion state machine evaluated in an `FAnimInstanceProxy`, the five-beat enter/exit-vehicle sequence with the
possession swap, and a runtime navmesh over sidewalks, plazas, parks and bridge walkways with real area costs.

**The simulated city.** `UNYCTrafficSubsystem` steps the traffic and pedestrian simulations at a fixed 20 Hz on a
worker thread, double-buffers the result, and drives pooled vehicle and pedestrian actors: bus destination signs,
taxi roof lights, sirens, umbrellas in the rain, four LOD bands by distance.

**GPS and minimap.** Built entirely in C++ (no .uasset needed): the road graph comes from `runtime/roadgraph.nycb`,
routes from the core router, turn-by-turn text from real street names, address / street / bus-stop / landmark
search, ETA, and a Slate minimap with zoom detents.

**Audio.** A procedural source set (engine, tyres, wind, rain, wipers, horn, steam, subway rumble) that a MetaSound
asset transparently replaces when one exists, spatial ambience emitters driven by the live simulation and by an
actor-tag contract, Doppler on moving sirens, the on-foot weather bed, six mix buses, and the car radio.

## 2. Files

| Area | Files | Lines | What |
|---|---|---|---|
| `Public/Vehicle` + `Private/Vehicle` | 20 | 4,865 | contract, wheels, movement, anim proxy, lights, dashboard, body (wipers/windows/doors/horn), mirrors, damage, the pawn |
| `Public/Character` + `Private/Character` | 10 | 2,379 | contract, anim proxy + locomotion state machine, the character, enter/exit, navigation subsystem |
| `Public/Traffic` + `Private/Traffic` | 8 | 2,001 | road-network subsystem, 20 Hz worker, traffic subsystem, pooled traffic vehicle |
| `Public/Peds` + `Private/Peds` | 2 | 312 | pooled pedestrian actor |
| `Public/UI` + `Private/UI` | 8 | 1,603 | GPS subsystem, Slate minimap, UMG minimap, GPS/HUD widget |
| `Public/Audio` + `Private/Audio` | 10 | 3,416 | procedural sources, vehicle audio, audio subsystem, ambience emitter, radio |
| `Public/Player` + `Private/Player` | 6 | 1,158 | settings, input config, camera rig |
| `Private/CoreAdapter/Gameplay*` | 8 | 4,290 | road network, traffic sim, ped sim, vehicle dynamics — the only files that touch `core` |
| `unreal/tools/gameplay_selftest.cpp` | 1 | 471 | the standalone harness |
| `unreal/tools/fetch_radio.py` | 1 | 1,337 (+337 / -14 this stage) | Internet Archive + Wikimedia Commons audio fetcher with licence recording |

Full per-file line counts and the review note for each are in `unreal/COMPILE_CHECKLIST_GAMEPLAY.md` §2.

## 3. Contracts consumed

### 3.1 `core/` — read from the real headers, used only through the adapter

| Header | What this lane uses |
|---|---|
| `nycsim/routing/RoadGraph.h` | the unified lane index space, `poseAt`, `lanesNear`, `successors`, `yieldTo`, segment/lane geometry, street names |
| `nycsim/routing/Router.h` | `Router`, `RouteResult` (`instructions`, `polyline`, `length_m`, `eta_s`) for the GPS |
| `nycsim/routing/NycbLite.h` | reading `runtime/*.nycb` sections |
| `nycsim/traffic/Signals.h` | `SignalTable`, `VehSignal`, `PedSignal`, `addDefaultPlans` — signals are pure functions of time, so both threads read them freely |
| `nycsim/traffic/Density.h` | `DensityTable` / `DensityCell` for spawn targets |
| `nycsim/traffic/Idm.h` | the Treiber longitudinal model |
| `nycsim/traffic/VehicleClass.h` | the 18-class fleet table (dimensions, mass, colours, shares) |
| `nycsim/traffic/SyntheticGrid.h` | the fallback grid when `runtime/` is absent |
| `nycsim/traffic/SpatialHash.h`, `Random.h` | neighbour queries, SplitMix64 |
| `nycsim/vehicle/VehicleSpec.h` | **authoritative** player-car specification (new this afternoon) |
| `nycsim/vehicle/Friction.h` | **authoritative** tyre/surface friction table |

The four `Private/CoreAdapter/Gameplay*` files are the only place any of this appears. They contain no Unreal API
at all, which is asserted by the source checker and proved by the fact that `g++` compiles them against the real
core sources and runs them.

### 3.2 Cross-checks against core's authoritative numbers (new)

`core/include/nycsim/vehicle/` landed while this lane was being written. The gameplay spec is now a *translation*
of it, and the self-test asserts it field by field — a divergence fails the test instead of reaching the car:

* dimensions, mass, front weight fraction, cg height, Cd, frontal area, tyre size code, rolling radius, fuel tank,
  battery capacity — all equal to `nycsim::vehicle::fusionHybrid2019()` (19 assertions);
* the six ARCHITECTURE §7 friction coefficients plus the five surfaces both tables carry (concrete, Belgian block,
  gravel, boardwalk, steel grate) — equal to `nycsim::vehicle::frictionTable()` (16 assertions).

Six values changed as a result of adopting core's figures: front weight fraction 0.57 → **0.58**, cg height
0.53 → **0.548 m**, Cd 0.277 → **0.27**, frontal area 2.28 → **2.27 m²**, front/rear track (they were swapped)
→ **1.580 / 1.583 m**, and the rolling radius 0.3235 → **0.3176 m** (core uses the SAE J1270 0.967 factor rather
than a 1.5 % deflection allowance). Five friction extension values were aligned to core as well (Belgian block
0.85/0.55 → 0.75/0.50, gravel 0.62/0.55 → 0.55/0.45, boardwalk 0.80/0.50 → 0.70/0.45, concrete wet 0.68 → 0.65,
steel grate 0.72/0.50 → 0.75/0.55).

### 3.3 Data contracts

* `runtime/roadgraph.nycb` (mandatory), `signals.nycb`, `density.nycb`, `pois.nycb`, `transit.nycb`,
  `landmarks.nycb` (all optional; each absence is reported, never guessed).
* `Config/DefaultEngine.ini` `PhysicalSurfaces` — `SurfaceType1..13` in the order asphalt, concrete, cobble, steel
  plate, painted marking, gravel, boardwalk, grass, sidewalk, water, metal, snow, ice.
* `MPC_Weather` scalar parameters: `Wetness`, `SnowCover`, `IceCover`, `WaterDepthMm`, `RainRateMmH`,
  `WindSpeedMps`, `TemperatureC`, `NightFactor` (owned by agent 1; read-only here, and every read is guarded by a
  parameter-presence check made once at startup).
* Blender → Unreal mesh naming contract (`Public/Vehicle/NYCVehicleContract.h`, `Public/Character/NYCCharacterContract.h`).
* Actor-tag contracts this lane consumes: navigation (`NYCSidewalk`, `NYCPlaza`, `NYCPark`, `NYCBridgeWalkway`,
  `NYCRoadbed`, `NYCNotWalkable`) and ambience (`NYCAmbienceTraffic`, `NYCSubwayGrate`, `NYCSteamVent`, `NYCPark`,
  `NYCWaterfront`, `NYCConstruction`, `NYCCrowd`, `NYCHelicopterCorridor`).
* `assets/audio/radio/stations.json` schema 1, written by `unreal/tools/fetch_radio.py`.

## 4. Verification

### 4.1 `unreal/tools/gameplay_selftest.cpp` — the adapter, compiled and run

```
g++ -std=c++17 -O2 -Wall -Wextra -o gameplay_selftest \
    -Icore/include -Iunreal/NYCSim/Source/NYCSimRuntime/Private \
    unreal/tools/gameplay_selftest.cpp \
    unreal/NYCSim/Source/NYCSimRuntime/Private/CoreAdapter/Gameplay*.cpp \
    core/src/routing/*.cpp core/src/traffic/*.cpp core/src/vehicle/*.cpp
```

```
NYCSim gameplay self-test (traffic / pedestrians / vehicle dynamics)
--------------------------------------------------------------------
[1] player vehicle specification and tyre friction
      wheel radius 0.3176 m, top speed 44.3 m/s, peak power 140.4 kW
[2] road network (synthetic Manhattan grid)
      160 nodes, 292 segments, 945 road lanes, 897 junction lanes, 156 signal plans, 28 index entries
      search("ave") -> "1st Ave" (0, 796)
      route: 2257 m, ETA 519 s, 35 lanes, 6 instructions, first = "Head west on W 39th St"
[3] traffic + pedestrians, 60 simulated seconds
  traffic: 398 live, 638 spawned, 240 despawned, 272 lane changes, 5 honks, 2 double-parked, 0 bus dwells, 1.265 ms/step
  peds:    497 live, 1947 spawned, 1449 despawned, 32488 crossing samples, 4786 jaywalk samples, 0.654 ms/step
      invariants: red-light entries 0, min leader gap 0.050 m, protected spawn/despawn 0, unsafe crossings 0
[4] determinism
      hash(seed 20260906) = 0x07c93eac049cc781, hash(seed 20260907) = 0xabd7b4ae07e813a2
--------------------------------------------------------------------
74 checks, 0 failures
```

What those invariants mean:

* **red-light entries 0** — no vehicle crosses a stop line while its signal group is red. Getting this to zero
  took three fixes: a `committed` flag set only inside the dilemma zone, a re-check of junction clearance at the
  moment of transition, and an emergency hold that brakes at `max_decel` rather than teleporting. Legal
  dilemma-zone entries are counted separately (`dilemmaZoneEntries`), because suppressing them would be wrong.
* **min leader gap 0.050 m ≥ 0** — no vehicle overlaps its leader. Three real bugs were found and fixed here: the
  lane-entry test read stale per-lane buckets, `applyLaneChange` evaluated gaps at the wrong arc length, and a
  sudden double-park could appear in front of a close follower. A post-step `resolveOverlaps()` clamp guarantees
  the invariant even if a future model change reintroduces one.
* **protected spawn/despawn 0** — ARCHITECTURE §9's rule that nothing pops in or out inside the ring around the
  player. This is checked *externally* by diffing consecutive snapshots for ids appearing or disappearing inside
  the radius, not by a counter the spawner increments (an earlier version of that counter was tautological and was
  removed).
* **unsafe crossings 0** — a pedestrian steps into the roadway only on WALK, at an unsignalised crossing, or as a
  modelled jaywalker with an accepted gap.
* **determinism** — the same seed and observer path reproduce the same FNV-1a trajectory hash; a different seed
  does not. The hash is only comparable within one build: `core/src/traffic/*` is being edited by another agent
  right now (`TrafficSim.cpp` changed at 13:45:44 while this report was being written), and the fleet table
  changing moves the trajectories.

Step cost at ~400 vehicles and ~500 pedestrians: **1.27 ms + 0.65 ms per 20 Hz step**, i.e. under 4 % of one core
at the simulation rate.

### 4.2 `check_gameplay_sources.py` — the static self-review

```
1037 checks, 0 failures
files checked: 72 (64 Unreal, 8 adapter), reflected public headers: 29, plain structs holding UObject pointers: 2
```

It asserts the UHT rules (`.generated.h` last, `GENERATED_BODY()`, `UENUM(BlueprintType) : uint8`), that every
`TObjectPtr` is either a `UPROPERTY` or belongs to a plain struct whose GC owner is written down, that every
in-module include resolves, that **every method declared in a lane header has a definition** (the check that
catches a subsystem being called before it is written), that the adapter contains no Unreal API, that every
engine call on the risk list is documented, and that every audio file referenced has a licence record. Details in
`unreal/COMPILE_CHECKLIST_GAMEPLAY.md` §9.

### 4.3 Probe: can this lane delegate to core's new `traffic::TrafficSim`?

Written and run today (`core_probe.cpp`, scratch): core's simulation configures on the synthetic grid, prefills
**907 vehicles** and steps 1,200 times (60 s) to **908 vehicles** with a stable trajectory hash. Two findings for
the core traffic agent and for whoever does the integration:

1. **`TrafficSim` spawns nothing without a `DensityTable`.** `prefill()` returned 0 until `setDensityTable()` was
   given a table. Worth either a warning in `lastError()` or a documented default.
2. `DensityTable::assignLaneNtas()` returns 0 on a synthetic grid (no polygons) and the sim still fills
   correctly — the fallback path works.

## 5. Audio: what was fetched and under which licence

Everything was fetched by `unreal/tools/fetch_radio.py`, run here. Every file carries a
`<file>.ogg.license.json` next to it *and* is listed in its directory's `LICENSE.json`;
`pipeline/nycsim_pipeline/report/asset_licenses.py` sees **9 audio records** out of 72 repository-wide, and the
only directory it still reports as missing a record is `assets/textures/_generated_kit`, which belongs to another
agent. (One cosmetic artefact of that scanner, not of the records: it counts each directory's files recursively,
so `assets/audio` appears in `docs/ASSET_LICENSES.md` as 503.7 MB — the radio index record's subtree is counted
once for the index and again for each station directory. On disk the tree is 254 MB.)

| Station | Dial | Genre | Tracks | Duration | MB | Licences |
|---|---|---|---|---|---|---|
| Hudson Jazz | 89.3 FM | jazz / ragtime / swing | 12 | 37 min | 26 | Public Domain ×12 |
| Lincoln Center Classical | 91.5 FM | classical / opera | 10 | 37 min | 32 | Public Domain ×10 |
| Bleecker Street Folk | 93.7 FM | folk / country / blues | 10 | 31 min | 25 | Public Domain ×10 |
| Boogie Down FM | 97.1 FM | hip hop | 8 | 35 min | 32 | CC-BY-3.0 ×5, CC-BY-3.0-US ×1, CC-BY-4.0 ×2 |
| Bowery Rock | 102.7 FM | rock / punk | 8 | 40 min | 33 | CC-BY-2.5 ×1, CC-BY-3.0 ×3, CC-BY-3.0-US ×1, CC-BY-4.0 ×3 |
| Pulse Brooklyn | 105.9 FM | electronic | 9 | 48 min | 38 | CC-BY-2.0-FR ×1, CC-BY-2.0-UK ×3, CC-BY-2.5 ×1, CC-BY-3.0 ×1, CC-BY-3.0-US ×1, CC-BY-4.0 ×2 |
| Gotham Readings | 820 AM | public-domain readings set in New York | 8 | 139 min | 61 | Public Domain (LibriVox; CC PDM / CC0) ×8 |
| **Total** | | | **65** | **368 min** | **247** | 40 public domain, 25 CC BY |

All 65 radio tracks come from the Internet Archive, whose per-item `licenseurl` field is machine-checkable — the
fetcher refuses anything whose licence it cannot read, and records the URL it read. The talk station is LibriVox
readings of New York books (*The Four Million*, *Bartleby, the Scrivener*, *How the Other Half Lives*,
*Washington Square*, *The Great Gatsby*, *The Age of Innocence*, *Maggie*, *Leaves of Grass*).

| SFX | Licence | Source | Used by |
|---|---|---|---|
| `glass_break_1.ogg` | CC0-1.0 | opengameart.org | vehicle damage (glass) |
| `radio_static_1.ogg` | CC0-1.0 | opengameart.org | radio tuning burst |
| `radio_jingle_1/2/3.ogg` | CC0-1.0 | opengameart.org | station idents |
| `siren_sample_1.ogg` | Public Domain | commons.wikimedia.org | emergency vehicles (with Doppler) |
| `siren_sample_2.ogg` | Public Domain | commons.wikimedia.org | emergency vehicles |
| `traffic_bed_1.ogg` | CC-BY-4.0 | commons.wikimedia.org | **nothing** — see gap 6 |

Attribution text for the CC-BY tracks is generated at runtime by `UNYCRadioSubsystem::GetAttributionText()` from
the licence records, and the whole set is listed in `docs/ASSET_LICENSES.md`, regenerated by the fetcher.

### What could not be licensed, and what was done instead

* **No car horn.** The OpenGameArt search for a CC0 car horn returned nothing usable. The horn is therefore a
  procedural dual-tone (E4 329.63 Hz + G4 392.00 Hz, a minor third — the interval production US horns use), with
  a 25 ms attack and 60 ms release. Nothing was invented and passed off as a recording.
* **No collision recording.** Same story for "car crash" (0 of 2 found). Impacts are silent until one is licensed;
  the code logs it once and the damage model is unaffected.
* **No subway, helicopter, park, crowd or construction recording.** The Commons searches returned nothing whose
  licence could be machine-checked. The subway grate and the steam vent are synthesised (they are physically
  simple — a low-frequency swell under concrete and a band-limited jet); park, waterfront, crowd, construction and
  helicopter zones stay **silent** and are counted in `GetStats().SilentZones` until a licensed recording is
  imported as `amb_park`, `amb_waterfront`, `amb_crowd`, `amb_construction`, `amb_helicopter`.
* **Wikimedia Commons rate limit.** `upload.wikimedia.org` answered HTTP 429 with `Retry-After: 600` — about one
  file per ten minutes. The fetcher honours it (no work-around, per the network rule), which is why Commons is
  only a top-up and the Internet Archive carries the dial.

## 6. Gaps, risks and hand-offs

1. **Two traffic simulations now exist.** `core/include/nycsim/traffic/TrafficSim.h` and
   `core/include/nycsim/peds/PedSim.h` landed *after* this lane's adapter was written (the adapter was built on
   the core primitives that existed: RoadGraph, Router, SignalTable, DensityTable, Idm, VehicleClass, Rng,
   SpatialHash). Core's version is authoritative and, as §4.3 shows, works. The delegation is deliberately
   contained: `nycsim_gameplay::TrafficSim`'s public API — `configure`, `setConfig`/`config`, `step`,
   `writeSnapshot`, `drainEvents`, `setObserver` — stays exactly as it is and its body becomes a translation of
   `nycsim::traffic::TrafficSim`. The field mapping is direct: `Vehicle::{id, cls, pos, heading_rad, speed, lane,
   s, flags, lc_dir, state, bus_route, bus_stop_ix}` → the snapshot's per-agent record, `HonkEvent` → the honk
   event, `TrafficStats::red_light_entries` → the invariant counter. **No Unreal file changes**; the acceptance
   gate is the existing self-test. This was not done in this stage because `core/src/traffic/TrafficSim.cpp` was
   being edited minute by minute (last write 13:45:44 today) and delegating to a moving target would have
   replaced a green, tested subsystem with an unverifiable one.
2. **Two longitudinal vehicle models.** Core models the powertrain as a calibrated wheel-force ceiling
   (`maxWheelForceN = 6424 N`, fixed from the published 0–60 mph time of 8.50 s); this lane keeps a sampled engine
   torque curve because Chaos needs one and the audio synthesiser needs an engine speed. Every *specification*
   value is now shared and asserted (§3.2), but the two models will not agree exactly on acceleration. Reconcile
   on hardware, with core's published 0–60 as the target.
3. **`landmarks.nycb` layout is unspecified** in DATA_CONTRACTS §15. The reader accepts a `points` section of
   `{float x, float y, uint32 name_str}` plus a `strtab`, and reports its absence in the load notes rather than
   guessing. Landmark search is otherwise unavailable.
4. **Sidewalk geometry is derived, not planimetric.** The pedestrian network offsets each segment centreline by
   `width/2 + 1.9 m`. When the planimetric sidewalk polygons land, `GameplayPedSim::buildSidewalks()` is the one
   function to change.
5. **MetaSound graphs are not authored.** The builder API is experimental in 5.4 and cannot be exercised here, so
   the five documented sources are C++ DSP with an identical parameter contract; `UNYCVehicleAudioComponent`
   prefers a MetaSound asset the moment one exists at the configured path. No engine work is needed to adopt them.
6. **`traffic_bed_1.ogg` is mislabelled by its search.** The Commons query "city traffic ambience" returned a
   railway-station tunnel recorded in Tampere. It is properly licensed (CC-BY-4.0) and kept with its record, but
   it is not a New York street, so no ambience zone plays it; the traffic bed is synthesised from the vehicles the
   simulation actually has around the listener instead. Delete it or re-purpose it deliberately — do not wire it
   to the traffic bed.
7. **Ped ↔ vehicle coupling lags one step.** The pedestrian obstacle set handed to the traffic simulation is the
   previous step's, so a driver reacts to a pedestrian 50 ms late. Core's `traffic/Interop.h` (`PedProbe` /
   `VehicleProbe`) is designed to remove exactly this lag and should be adopted with gap 1.
8. **`assets/textures/_generated_kit` has no licence record.** Not this lane's directory; flagged for whoever owns
   the texture kit, because it is the only thing keeping `asset_licenses.py` from a clean run.
9. **A GCC `-Warray-bounds` warning in core.** `core/src/traffic/Signals.cpp:157` — `std::sort` over
   `int32_t groups[kMaxCachedGroups]` (size 8) can be indexed at offset 64 / element 16 according to the compiler.
   For the core traffic agent.
10. **`UNYCAudioSubsystem` rescans actors for ambience zones.** The scan is a full `TActorIterator` pass, throttled
    to at most one per 10 s and only after the listener has moved 400 m. On a fully streamed city this is the one
    place in the lane with an O(actors) cost; if it shows up in a profile, the fix is for the world builder to
    call `RegisterAmbienceZone()` at spawn time and for the scan to be dropped to a first-load-only pass.
