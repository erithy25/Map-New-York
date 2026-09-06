# `nycsim_core` — the engine-agnostic C++17 library

Everything in NYCSim that can be *computed and tested without an engine* lives here: geodesy, the
tile grid and its streaming scheduler, the NYCB runtime binary format, JSON, civil time and DST,
solar/lunar astronomy, live-weather decoding and its mapping to the world, the player car's
specification and longitudinal model, and the traffic / routing / pedestrian lanes.

The same sources compile twice:

* **standalone** with CMake (this directory) — that is where the test suite runs;
* **inside Unreal** as the `NYCSimCore` module, which wraps each `core/src/**/*.cpp` in a generated
  translation unit (`unreal/tools/gen_core_unity.py`). No UE header is ever included by core code.

C++17, no exceptions, no RTTI, no `std::filesystem`, no static initialisers with side effects, no
allocation in per-frame hot paths. Warnings are errors:
`-Wall -Wextra -Wpedantic -Wshadow -Wconversion -Wsign-conversion -Wdouble-promotion -Wformat=2
-Wundef -Wcast-align -Werror`.

---

## Build and test

```sh
cmake -S core -B core/build -DCMAKE_BUILD_TYPE=Release
cmake --build core/build -j3
ctest --test-dir core/build --output-on-failure
```

Options (all default `ON`):

| option | effect |
|---|---|
| `NYCSIM_BUILD_TESTS` | build `nycsim_core_tests` and register the ctest suites |
| `NYCSIM_NO_EXCEPTIONS` | compile with `-fno-exceptions -fno-rtti`, mirroring Unreal |
| `NYCSIM_WERROR` | treat warnings as errors |
| `NYCSIM_BUILD_LANES` | build the optional `src/{traffic,routing,peds}` lanes and the standalone benchmark |

One executable holds every suite; each suite is a separate ctest so a failure is attributable:

```sh
ctest --test-dir core/build -R weather --output-on-failure   # one suite
./core/build/nycsim_core_tests --test-suite=astro            # or run doctest directly
./core/build/nycsim_core_tests --list-test-cases
```

The traffic/routing/pedestrian lane can also be built on its own:

```sh
cmake -S core/traffic_standalone -B build/traffic && cmake --build build/traffic
```

### Regenerating test data

Several suites are checked against ground truth produced outside C++. The generators live in
`docs/verification/core/` and are re-runnable:

| generator | writes | ground truth |
|---|---|---|
| `gen_geo.py` | the tables inside `tests/geo/test_geo.cpp` | pyproj 3.7.2 / PROJ 9.5.1 |
| `gen_dst.py` | `tests/time/dst_table.h` | Python `zoneinfo` (IANA tz database) |
| `gen_spa_tables.py` | `src/astro/SpaTables.inc` | `services/nycsim_live/astronomy.py` |
| `gen_astro_cases.py` | `tests/astro/astro_cases.h` | `services/nycsim_live/astronomy.py` |
| `gen_usno_cases.py` | `tests/astro/usno_cases.h` | US Naval Observatory API (archived JSON) |
| `gen_weather_cases.py` | `tests/weather/weather_cases.h` | `services/nycsim_live/{metar,weather}.py` |
| `gen_nycb_fixture.py` | `tests/data/runtime/*.nycb`, `tests/io/nycb_expected.h` | `pipeline/nycsim_pipeline/runtime/nycb.py` |

---

## Layout

```
core/
  include/nycsim/       public headers (the only thing other modules include)
    Config.h            export macro, version, fatal-error hook
    geo/                Ellipsoid, TransverseMercator, LambertConformalConic, NycTm,
                        StatePlaneLI, UECoords, Units
    tiling/             Tile (1 km grid), TileCatalog, TileScheduler (LOD + streaming)
    io/                 Nycb (runtime container), NycbRecords (§15 layouts), Json
    time/               NyTime      — UTC <-> America/New_York, DST, Julian day, Delta-T
    astro/              Spa, Moon   — NREL SPA, Meeus lunar theory, Manhattanhenge
    weather/            WeatherState, MetarParser, NwsParser, OpenMeteoParser,
                        WeatherService, WorldEffects
    vehicle/            VehicleSpec, Friction, Powertrain, LongitudinalSim
    routing/            RoadGraph, Router, NycbLite      (traffic agent's lane)
    traffic/, peds/     fleet, signals, density, IDM/MOBIL, social force
    util/               Result, Error, Span, Arena, Log, FixedStepClock
  src/                  one .cpp per header that needs one; per-lane CMakeLists for the lanes
  tests/                doctest suites, one directory per module; tests/data/ holds fixtures
  third_party/doctest/  vendored, with LICENSE_RECORD.json
  traffic_standalone/   lane-only build + benchmark
```

### Error handling

There are no exceptions. Fallible calls return `Result<T>` (`util/Result.h`), which holds either a
value or an `Error{code, static message, int64 detail}`:

```cpp
const nycsim::Result<nycsim::io::NycbReader> r = nycsim::io::NycbReader::fromFile(path);
if (!r) { UE_LOG(LogNYCSim, Error, TEXT("%hs"), r.error().message); return; }
const auto nodes = r->view<nycsim::io::RoadNode>("nodes");
```

`NYCSIM_TRY(var, expr)` propagates an error out of a function returning a `Result`. `Result::value()`
on an error is a *programmer* error and calls the fatal handler, which Unreal should redirect at
start-up:

```cpp
nycsim::setFatalHandler([](const char* msg, const char* file, int line) {
    UE_LOG(LogNYCSim, Fatal, TEXT("%hs (%hs:%d)"), msg, file, line);
    for (;;) {}   // the handler must not return
});
```

---

## How the Unreal module consumes it

`unreal/NYCSim/Source/NYCSimCore` compiles these sources directly with UBT (`bUseUnity = false`,
`bEnableExceptions = false`, `bUseRTTI = false`, `CppStandard = Cpp17`) and re-exports
`core/include` as a public include path. `NYCSimRuntime/CoreAdapter/*` is the only place that
converts between core types and UE types. Add a file to `core/src` → re-run
`unreal/tools/gen_core_unity.py`.

The five entry points the UE agents need:

**1. Coordinates** — `geo/NycTm.h`, `geo/UECoords.h`

```cpp
using namespace nycsim::geo;
const Result<XY> tm = lonLatToTm(-73.985664, 40.748440);   // WGS84 -> NYC_TM metres
const FVector ue = FVector(tm->x * 100.0, -tm->y * 100.0, z_m * 100.0);  // UECoords.h does this
```

`UE.X = east_m × 100`, `UE.Y = −north_m × 100`, `UE.Z = up_m × 100` (ARCHITECTURE §2). Never
hand-convert anywhere else.

**2. Streaming** — `tiling/Tile.h`, `tiling/TileScheduler.h`

```cpp
TileScheduler sched(Span<const TileInfo>(tiles.data(), tiles.size()));   // from runtime/tiles.nycb
CameraState cam{x_m, y_m, vx, vy, headingDeg, timeS};
for (const Transition& t : sched.update(cam)) {
    // t.from -> t.to for tile (t.tx, t.ty); nearest-first; t.budgetLimited when memory forced it
}
const SchedulerStats& st = sched.stats();   // residentBytes, countByTier, overBudget
```

Deterministic: the same camera path yields the same transition sequence regardless of catalogue
order. Nothing within 300 m of the camera is ever downgraded or evicted.

**3. Runtime data** — `io/Nycb.h`, `io/NycbRecords.h`

```cpp
NYCSIM_TRY(reader, io::NycbReader::fromFile("data/processed/runtime/roadgraph.nycb"));
NYCSIM_TRY(segments, reader.view<io::RoadSegment>("segments"));   // zero-copy
NYCSIM_TRY(name, reader.string(segments[0].nameStr));
```

Byte-compatible with `pipeline/nycsim_pipeline/runtime/nycb.py`: natural C alignment, 24-byte
header, 8-byte section alignment. Use `copyRecords<T>()` instead of `view<T>()` when the buffer's
alignment cannot be guaranteed (e.g. an arbitrary UE bulk-data pointer).

**4. Sky and clock** — `time/NyTime.h`, `astro/Spa.h`, `astro/Moon.h`

```cpp
NYCSIM_TRY(now, nytime::simTime(unixSeconds));            // local time, DST, JD, Delta-T
const astro::SolarPosition sun = astro::solarPositionUnix(unixSeconds, astro::kCentralPark);
const astro::MoonPosition moon = astro::moonPositionUnix(unixSeconds, astro::kCentralPark);
// sun.azimuth / sun.elevation are compass degrees -> directional light rotation
// moon.illuminatedFraction, moon.phase -> moon card material
```

**5. Weather** — `weather/WeatherService.h`, `weather/WorldEffects.h`

Core does no networking. The engine supplies `Provider::fetch` functions; core owns the ordering,
the circuit breakers, the stale fallback and the snow model.

```cpp
std::vector<weather::Provider> providers = { nwsProvider(), openMeteoProvider(), metarProvider() };
weather::WeatherService service(std::move(providers));
const weather::WeatherState& s = service.poll(nowUnix);          // every 60 s
static weather::WorldEffectsState memory;
const weather::WorldEffects w = weather::worldEffectsStep(s, memory, deltaSeconds);
// w.wetness, w.puddles, w.snowCover, w.fogDensity, w.windGustMps, w.umbrellaShare,
// w.plowActivity, w.headlights, w.wiperSpeed, w.surface
```

**6. The player car** — `vehicle/VehicleSpec.h`, `vehicle/Friction.h`

```cpp
const VehicleSpec& car = vehicle::fusionHybrid2019();   // mass, Cd, tyre, powertrain, brakes
const double mu = vehicle::frictionFor(w.surface, w.wetness, w.snowCover, w.iceRisk);
```

Feed `car` into the Chaos Vehicle setup and `mu` into the tyre friction multiplier.

---

Verification results, gaps and contract deviations: `docs/verification/core/REPORT.md`.
