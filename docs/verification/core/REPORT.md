# Stage report — `core/` (engine-agnostic C++17 library)

**Scope of this report:** `core/` except the `traffic/` and `peds/` behaviour models, which belong to
the traffic/routing/pedestrian agent. `routing/RoadGraph` and `routing/Router` are that agent's code;
they are kept compiling and linking here and their suite is reported, but their content is theirs.

**Starting point (docs/STATE.md):** *"`core/`: never compiled here; no ctest run."* 30 headers and 27
sources existed; `time/`, `astro/`, `weather/` and `vehicle/` were empty directories that
`core/CMakeLists.txt` already referenced.

---

## 1. Build

```
$ cmake -S core -B core/build -DCMAKE_BUILD_TYPE=Release
$ cmake --build core/build -j3
$ ctest --test-dir core/build --output-on-failure
```

GCC 13.3.0, CMake 3.28.3, C++17, Release. Warning set actually applied to every core source and every
test (from `core/CMakeLists.txt`):

```
-Wall -Wextra -Wpedantic -Wshadow -Wconversion -Wsign-conversion -Wdouble-promotion
-Wformat=2 -Wundef -Wcast-align -Werror        plus  -fno-exceptions -fno-rtti
```

The build is **clean: 0 warnings, 0 errors**, in both configurations
(`-DNYCSIM_BUILD_LANES=ON` — the default, everything — and `OFF` — this lane alone).

### 1.1 Compile errors found and fixed in the pre-existing code

The library had never been compiled. Fifteen `-Werror` diagnostics were fixed:

| file | diagnostic | fix |
|---|---|---|
| `src/tiling/TileCatalog.cpp:38` | `-Wredundant-move` | dropped `std::move` on the returned local |
| `src/io/Nycb.cpp` x3 | `-Wredundant-move` | same |
| `src/io/Json.cpp:499` | `-Wredundant-move` | same |
| `src/io/Json.cpp:366` | `json::Value::obj_` private in the parser | added the public `Value::append(key, value)` (RFC 8259 permits duplicate names; `set()` replaces, `append()` does not) and used it |
| `src/io/Json.cpp:398` | `-Wsign-conversion` on `for (unsigned char c : string_view)` | explicit `static_cast<unsigned char>` per character |
| `include/nycsim/routing/RoadGraph.h:330` | `std::sqrt` without `<cmath>` | fixed by the traffic agent concurrently |
| `src/routing/RoadGraph.cpp` x4, `src/routing/Router.cpp` x2 | `-Wsign-conversion` | fixed by the traffic agent concurrently |

### 1.2 Failing tests found and fixed in the pre-existing tests

| test | problem | resolution |
|---|---|---|
| `tests/tiling/test_scheduler.cpp:197` | the transition-ordering assertion was a tautology (`a.tx == a.tx`) and would not compile under doctest ("Expression Too Complex") | replaced with a real check: transitions are emitted in non-decreasing cone-weighted priority, ties broken by `(ty, tx)`, and the first transition is the tile the camera stands in |
| `tests/tiling/test_tile.cpp:56` | expected `tilesInBbox(10, 10, 0, 0) == 0` | the C++ *correctly* mirrors `tiling.tiles_in_bbox`, which clamps with `max(xmax - 1e-9, xmin)` and therefore returns the single tile `(0, 0)`. Verified against Python: `list(tiles_in_bbox(10,10,0,0)) == [Tile(0,0)]`. The test expectation was wrong and was corrected. |

---

## 2. Final ctest result

`ctest --test-dir core/build --output-on-failure` over all 11 registered suites:

```
    Start  1: util
 1/11 Test  #1: util ...........................   Passed    0.04 sec
    Start  2: geo
 2/11 Test  #2: geo ............................   Passed    0.12 sec
    Start  3: tiling
 3/11 Test  #3: tiling .........................   Passed   30.71 sec
    Start  4: io
 4/11 Test  #4: io .............................   Passed    1.65 sec
    Start  5: time
 5/11 Test  #5: time ...........................   Passed    0.04 sec
    Start  6: astro
 6/11 Test  #6: astro ..........................   Passed    0.76 sec
    Start  7: weather
 7/11 Test  #7: weather ........................   Passed    0.05 sec
    Start  8: vehicle
 8/11 Test  #8: vehicle ........................   Passed    0.10 sec
    Start  9: traffic
 9/11 Test  #9: traffic ........................   Failed   (traffic agent's lane, in flight)
    Start 10: routing
10/11 Test #10: routing ........................   Passed    0.03 sec
    Start 11: peds
11/11 Test #11: peds ...........................   Failed   (peds agent's lane, in flight)

82% tests passed, 2 tests failed out of 11
Total Test time (real) = 147.16 sec
```

**Excluding the two suites that are not this lane** (`ctest -E "^(traffic|peds)$"`), which is the
result this report certifies:

```
100% tests passed, 0 tests failed out of 9
Total Test time (real) =  33.52 sec
```

The two failures are in the traffic/pedestrian agent's own files, which were being written while this
build ran (`tests/traffic/test_sim.cpp`, `tests/peds/test_peds.cpp:487` —
`collisions_with_peds == 0` fails with 598). They are reported to the orchestrator, not fixed here:
that lane is not mine.

### 2.1 Per-suite detail (test cases / assertions, all passing)

| suite | test cases | assertions | what it proves |
|---|---:|---:|---|
| `util` | 7 | 65 | `Result`/`Error` value semantics, `Span`, `Arena`, `FixedStepClock`, `Log` |
| `geo` | 9 | 25,753 | NYC_TM and EPSG:2263 against pyproj at 30 points; round trips over the whole scope; ADR-002 distortion bound; UE mapping; units |
| `tiling` | 11 | 3,059 | tile grid vs `tiling.py`; scheduler invariants over five recorded drives |
| `io` | 13 | 624 | NYCB reader/writer, corruption handling, JSON, **and interop with the real exporter output** |
| `time` | 8 | 5,831 | DST for every day 2007-2099 and every hour of every transition day; Julian day; Delta-T |
| `astro` | 14 | 14,910 | NREL SPA reference case; 121 solar and 97 lunar instants vs the Python reference; 15 USNO days; Manhattanhenge |
| `weather` | 26 | 171,038 | METAR grammar, three providers on live fixtures, service state machine, world-effect mapping |
| `vehicle` | 9 | 2,224 | published specification, friction table, 0-60 mph, braking, energy balance |
| `routing` | (traffic agent's) | - | kept compiling and linking; passes |
| **total (this lane)** | **97** | **223,504** | |

---

## 3. Modules completed in this pass

`time/`, `astro/`, `weather/` and `vehicle/` were empty. 5,056 lines of header and source were added,
plus their suites. All four are ports of, or extensions to, an authoritative reference; nothing is
approximated silently.

### 3.1 `time/NyTime.{h,cpp}` — civil time

Port of `services/nycsim_live/timesync.py`. Proleptic-Gregorian calendar arithmetic (Hinnant's
`days_from_civil`/`civil_from_days`, Sakamoto's day-of-week), the US federal DST rule as pure integer
arithmetic for 1967 onwards (2007- second Sunday of March -> first Sunday of November; 1987-2006;
1976-1986; the 1974 and 1975 Emergency Act years; 1967-1973), Julian day (Meeus ch. 7 / SPA eq. 4),
the leap-second table through 2017-01-01 and the Espenak-Meeus Delta-T polynomial, and a per-frame
`SimTime`.

**Verification** — `docs/verification/core/gen_dst.py` generates `core/tests/time/dst_table.h` from
Python `zoneinfo` (the IANA database):

* the exact POSIX instants of **both** offset changes for every year **2007-2099** (93 x 2 = 186
  values, found by an hour-resolution scan): all 186 match `usDstBounds()` exactly;
* one bit per UTC day from 2007-01-01 to 2099-12-31 — **33,968 days**, each checked at 12:00 UTC:
  0 mismatches in offset, DST flag and abbreviation;
* the offset at each of the 24 UTC hours of **both transition days of every year** — 4,464 checks,
  0 mismatches;
* the half-open boundary `[start, end)` and the repeated autumn hour;
* Julian day and Delta-T against 12 instants computed by `timesync.py` (agreement < 1e-9).

Known model seam, asserted so it cannot change silently: at 2038-01-01 Delta-T jumps 69.184 s ->
83.233 s where the exact leap-second relation hands over to the polynomial. Identical in the Python
reference.

### 3.2 `astro/{Spa,Moon}.{h,cpp}` — sun and moon

Complete NREL SPA (Reda & Andreas, NREL/TP-560-34302): Earth heliocentric L0-L5/B0-B1/R0-R4, IAU 1980
nutation (63 terms), true obliquity, aberration, apparent sidereal time, topocentric parallax,
refraction, azimuth/zenith, plus the Appendix A.2 rise/transit/set procedure. Meeus ch. 47 lunar
theory (the full 60 + 60 periodic terms and the additive terms of 47.6/47.7) and ch. 48 illumination.
The long tables are generated mechanically from the Python reference
(`gen_spa_tables.py` -> `src/astro/SpaTables.inc`) so a transcription slip is impossible.

**Verification**

* **NREL reference case** — 2003-10-17 12:30:30 UTC-7, 39.742476 N, 105.1786 W, 1830.14 m, 820 mbar,
  11 C, Delta-T = 67 s:
  **zenith 50.11162 deg, azimuth 194.34024 deg, both within 1e-5 deg** — an order of magnitude better
  than the 0.001 deg requirement. Every intermediate of the paper's table A5.1 is checked as well
  (L, B, R, Theta, dPsi, dEps, eps, lambda, nu, alpha, delta, H, delta', H', e0, de, e, Phi).
* 121 solar instants through 2026 at Central Park vs `astronomy.py`: worst angular difference
  **< 1e-9 deg**, worst radius difference < 1e-12 AU.
* 97 lunar instants vs `astronomy.py`: worst angle **< 1e-9 deg**, distance < 1e-6 km,
  illuminated fraction < 1e-12, phase index identical at every sample.
* Meeus worked examples 47.a (lambda 133.162655, beta -3.229126, Delta 368,409.7 km, pi 0.991990) and
  48.a (i 69.0756, k 0.6786) reproduced.
* **Independent ground truth:** 15 days fetched live from the **U.S. Naval Observatory** one-day API
  (`gen_usno_cases.py`; raw responses archived in `usno_oneday.json`, public domain). Sunrise,
  solar transit, sunset, civil-twilight begin/end all agree **to the minute** (worst error <= 1 min,
  which is USNO's own rounding), and the moon's illuminated fraction at 12:00 local agrees to
  **< 0.6 percentage points** (USNO rounds to whole per cent).
* Twilight thresholds order correctly; a polar June day correctly reports *no* sunrise/sunset rather
  than inventing one.

**Manhattanhenge.** `manhattanhenge(year, observer, ...)` searches 1 May - 15 Aug for evening instants
whose apparent solar azimuth is within 0.5 deg of **299.0 deg** (270 + the 29.0 deg
Commissioners'-Plan grid rotation), for both the "full sun" (disc centre at +0.5 deg) and "half sun"
(centre on the street-end horizon) variants, and flags the best match of each kind either side of the
solstice. 2024-2028 gives **91 events**, every one within 0.5 deg of 299.0 and all in the two expected
windows (late May, mid July); each matches the Python reference date, azimuth and delta to < 1e-6.
The four 2026 best dates are 27 May (half, 299.113), 28 May (full, 299.026), 14 July (full, 298.972)
and 15 July (half, 299.057).
*Stated gap:* these land **within one day** of the dates the American Museum of Natural History
announces. The difference is entirely the assumed street-end horizon elevation — the sensitivity is
about 1 day per 0.2 deg of disc-centre elevation and about 1 day per 0.22 deg of assumed grid azimuth
(documented in `astronomy.py:manhattanhenge_sensitivity`). The **azimuth** criterion the brief
specifies is met exactly; the calendar date is only as good as the horizon assumption, and that is
said here rather than hidden.

### 3.3 `weather/` — live weather

Six headers / six sources: `WeatherState` (DATA_CONTRACTS §12 plus the §12.1 extension, missing
values as NaN, with a `valid()` contract checker), `MetarParser` (full FMH-1 ch. 12 grammar,
hand-rolled matchers — no `std::regex`, no exceptions), `NwsParser` (observations plus the gridpoint
forecast-anchored blend), `OpenMeteoParser` (WMO 4677 table, interval->rate, rain/snow partition,
`minutely_15` visibility), `WeatherService` (ordered providers, circuit breakers, snow model, stale
fallback, `weather.json` read/write), `WorldEffects` (the ARCHITECTURE §11 mapping table).

**Verification against the Python reference on real, live data.** `gen_weather_cases.py` runs
`services/nycsim_live/{metar,weather}.py` over the *same fixture bytes* the C++ test reads and emits
the expected values, so any divergence fails the build. Fixtures fetched live on 2026-09-06 and
archived under `core/tests/data/weather/`:

| fixture | source |
|---|---|
| `nws_KNYC.json`, `nws_KLGA.json`, `nws_KJFK.json` | `api.weather.gov/stations/{id}/observations/latest` |
| `nws_gridpoint.json` (203 KB) | `api.weather.gov/gridpoints/OKX/34,45` |
| `open_meteo.json` | `api.open-meteo.com/v1/forecast` |
| `metar_{KNYC,KLGA,KJFK,KEWR}.txt` | `tgftp.nws.noaa.gov` |
| `awc_metar.json` | `aviationweather.gov/api/data/metar` |

Every parsed field (station, observed_at, temp, dewpoint, RH, wind speed/gust/direction in all three
conventions, precip type, rate, rate basis, cloud cover, visibility, pressure, snow depth and source,
snowfall rate, thunder, obscuration bit set) matches the Python reference to 1e-9 on all three
providers, both with and without the forecast blend applied. Every parsed state also passes
`WeatherState::valid()`.

**METAR grammar coverage.** 20 curated reports exercise the whole grammar — calm/clear, light rain
with mist, heavy thunderstorm with CB, moderate snow with freezing fog and a snow-depth remark,
freezing rain, ice-pellet/snow mix, drizzle with fog and vertical visibility, vicinity thunderstorm,
CAVOK, metric visibility with a trend group, RVR with variable wind and PK WND, mixed-fraction
visibility, missing dew point, haze + smoke, blowing snow with 931/933 groups, hail with a
thunderstorm, Q-code pressure, NIL, `/////KT`, and snow grains at `0000`. All 20 decode
field-for-field identically to `metar.py`, including remarks (SLP, T-group, P, 4/sss, 931, 933, 6, 7,
PK WND) and the derived semantics (precip classification priority, class rates x1.5 for
thunderstorm-driven precipitation, trace, measured, obscuration set, ceiling, cloud fraction).

**Service state machine.** NWS -> Open-Meteo -> METAR -> stale, verified by injection: the primary
succeeding means the others are never called; each failure falls through and counts exactly one
breaker failure; 3 consecutive failures open the breaker for 300 s, a probe half-opens it, a failed
probe re-opens it, a success closes it and clears the counter; an open breaker is *skipped entirely*
(call count asserted); with no provider and nothing known the result is an **empty stale record with
NaN values, never invented weather**; with a last-good state the values are kept and `stale_age_s`
grows; the snow model keeps melting/settling from the last known temperature. Snow model checked term
by term against the documented formula (SLR bands 8/10/13/18 and 3 for sleet, 0.06 cm/h/C melt,
0.02 cm/mm rain-on-snow, 2 %/day settling, 6 h step cap, observed-depth reset, non-negative depth).
`weather.json` round-trips: every §12 key and every §12.1 key present, numbers rounded to 3 decimals
as `to_json_dict` does, unknowns as `null` <-> NaN, malformed documents rejected.

**World-effect mapping** — see §5.1 below; it has no Python counterpart and is specified in
`WorldEffects.h`.

### 3.4 `vehicle/` — the player car

`VehicleSpec.h` carries the 2019 Ford Fusion Hybrid (ADR-009) with **every constant labelled
PUBLISHED, DERIVED or CALIBRATED**. Published: 4,872 x 1,852 x 1,476 mm, 2,850 mm wheelbase, tracks
1,580/1,583 mm, 11.6 m turning circle, curb 1,685 kg, GVWR 2,159 kg, 58/42 distribution, Cd 0.27,
frontal area 2.27 m2, 225/50R17 tyres at 241 kPa, 2.0 L Atkinson (105.1 kW @ 6,000 rpm,
174.9 N.m @ 4,000 rpm), 88 kW / 159 N.m traction motor, 140.2 kW combined system power, 1.4 kWh pack,
115 mph limiter, 85 mph EV ceiling, 53 L tank, 316/302 mm discs, 14.8:1 steering.
Derived (with the formula stated inline): tyre unloaded radius 0.3284 m and rolling radius 0.3176 m
from the size code, CoG height, overhangs, inertias, rotating-inertia factor 1.06, driveline
efficiency 0.92.

`Friction.h/.cpp` implements the **ARCHITECTURE §7 table verbatim** — dry asphalt 1.00, wet asphalt
0.70, wet steel plate 0.55, wet painted marking 0.60, snow 0.30, ice 0.15 — and the four entries whose
name already fixes a condition have identical dry and wet columns so no wetness blend can move them
off the contract (asserted). `frictionFor(surface, wetness, snowCover, iceRisk)` connects the live
weather to the tyre model, and `tractionLimitedAccelMps2` solves the load-transfer equation for a
front-drive car. Seven further surfaces (concrete, Belgian block, steel grate, gravel, boardwalk,
packed snow, slush) are an **appended extension**, marked as such in the table and covering the
DATA_CONTRACTS §7 `surface` enum.

`Powertrain.h`/`LongitudinalSim.h` model the power-split eCVT as constant tractive force below a
corner speed and constant system power above it, with RK4 integration.

**0-60 mph acceptance test: 8.49997 s** (requirement 8.5 +/- 0.8 s). Step-size independent to 0.2 %
between dt = 0.2 ms and 5 ms; distance 118 m; peak acceleration 3.43 m/s2 (0.350 g). Also checked:
0-30 mph is 35-50 % of the 0-60 time; wet asphalt gives the *same* time (the launch is torque-limited,
not traction-limited, at mu = 0.70 — the physically correct answer, asserted rather than assumed);
packed snow is > 1.2x slower; sheet ice takes about 39 s; a 45 % grade correctly returns
`NoConvergence` instead of a fabricated number. Braking 60 mph -> 0: 33-36.7 m dry, 1.30-1.50x on wet
asphalt, 5.5-7.5x on ice, and 30 mph -> 0 is a quarter of the 60 mph distance. Work-energy balance
over a full 0-60 run closes to better than 0.5 %.

---

## 4. Verifications requested by the brief

### 4.1 Geodesy against pyproj (< 2 mm at >= 20 points)

`docs/verification/core/gen_geo.py` regenerates the tables embedded in `tests/geo/test_geo.cpp` with
**pyproj 3.7.2 / PROJ 9.5.1**. The committed tables were regenerated and **compared line by line:
identical**, both the 30 coordinate rows and the 30 `get_factors` rows.

**30 points across all five boroughs and NJ** (7 Manhattan, 5 Bronx, 5 Brooklyn, 6 Queens,
5 Staten Island, 2 New Jersey), from the Empire State Building and One World Trade Center to
Tottenville, City Island, Far Rockaway and the George Washington Bridge. Both directions are checked
to **< 2 mm**, for NYC_TM (`EPSG:4326 -> +proj=tmerc +lat_0=40.7 +lon_0=-73.95 +k=1`) and for
EPSG:2263 (Lambert Conformal Conic from NAD83 geographic, i.e. the pure projection with no datum
shift, matching the C++ implementation), plus the EPSG:2263 -> NYC_TM composition. Point scale and
grid convergence match `Proj.get_factors` at all 30 points, and the ADR-002 claim (<= 1.2 cm/km
distortion anywhere in scope) is checked over the whole scope box.

### 4.2 TileScheduler against ARCHITECTURE §3

Verified over the full 2,916-tile scope catalogue with recorded synthetic drives (a 120 s eastbound
run at 30 m/s, a run along a tile edge, and an 8-segment Manhattan grid path with light stops —
5,550 frames in total):

* **Nothing within 300 m is ever unloaded or downgraded.** Two independent checks: no transition is
  ever emitted for a tile the reference (computed outside the scheduler with `tilesInBbox` +
  `distanceToTile`) says is inside the protect radius, and no such tile is ever at a tier below L0.
  Violations: **0** on every drive.
* **Radii and hysteresis.** With an unlimited budget the tier equals the radii oracle at every frame:
  inside a load radius => at least that tier; loaded => within that tier's unload radius. Violations:
  **0**. Along a straight drive every tile enters L0 exactly once (asserted per tile), the only L0
  exit is to L1 (never straight to Unloaded), and no tile flips L0 -> L1 -> L0 within 10 s.
* **Memory budget.** With the budget set to 55 % of the L0 cost of the nine tiles around the start,
  resident bytes never exceed the budget, budget-limited transitions are flagged, and the grant order
  is nearest-first (no tile is denied L0 while a farther one is granted it). With a 1-byte budget the
  protected tiles still load and `overBudget` is reported rather than the protection being broken.
* **Determinism.** The same camera path replays to a bit-identical transition log; a randomly
  shuffled catalogue produces the identical log; duplicate `(tx, ty)` records are dropped.
* **Cost model** monotone in tier and in the right order of magnitude (a 400-building tile is 2-8 MB
  at L0).

### 4.3 NYCB round trip against the producer's byte layout

The C++ side was **wrong** and is now fixed — see the contract deviation in §5.2. Verification:

* `docs/verification/core/gen_nycb_fixture.py` writes one file per DATA_CONTRACTS §15 container
  (`roadgraph`, `signals`, `tiles`, `transit`, `density`, `pois`) **with the foundation exporter
  itself** (`pipeline/nycsim_pipeline/runtime/nycb.py`) into `core/tests/data/runtime/`, and emits
  `core/tests/io/nycb_expected.h`. The C++ reader reads all six and every field of every record type
  is asserted (ids, floats, enums, string-table offsets, the 24-entry headway array, ...). All 16
  record sizes equal the exporter's numpy `dtype.itemsize`.
* **The real exporter output is loaded.** `data/processed/runtime/roadgraph.nycb` (103,728,864 bytes)
  appeared during this work and is read by the C++ reader in the test. **Section counts equal the
  parquet row counts exactly:**

  | section | nycb records | `data/processed/roads/*.parquet` rows |
  |---|---:|---:|
  | `nodes` | 79,291 | `nodes.parquet` 79,291 |
  | `segments` | 122,235 | `segments.parquet` 122,235 |
  | `lanes` | 384,703 | `lanes.parquet` 384,703 |
  | `junction_lanes` | 466,279 | `junction_lanes.parquet` 466,279 |
  | `controllers` (signals.nycb) | 23,839 | `signals.parquet` 23,839 |

  plus `vertices` 3,901,850, `lane_links` 466,279, `yield_links` 551,241, `strtab` 148,757 bytes;
  `transit.nycb` 345 routes / 13,364 stops / 21,963 route-stops / 137,060 vertices.
  Cross-section integrity over the real file: every `first_vertex + vertex_count`,
  `first_succ + succ_count` and `first_yield + yield_count` is in range and every `name_str` resolves
  — **0 violations**, and **0 degenerate** (single-vertex) segments or lanes.
* Writer/reader round trip, 8-byte section alignment, 24-byte header, and typed rejection of every
  corruption mode (bad magic, wrong version, truncated header, truncated index, index past EOF,
  section past EOF, `element_size x element_count != size`, duplicate name, empty name, unterminated
  strtab, missing file, empty path).

---

## 5. Contract deviations and additions

Five, all necessary and all documented in the code as well.

### 5.1 §12 extension — the weather -> world mapping (**new**, `weather/WorldEffects.h`)

ARCHITECTURE §11 requires a "mapping table weather -> world (wetness, puddles, snow accumulation, fog
density, wind for flags/awnings, umbrellas, plows/salt)" but no such table existed in
`services/nycsim_live/` (that package stops at the observation) and none is in DATA_CONTRACTS.
It is therefore **specified in `core/include/nycsim/weather/WorldEffects.h`, which is now the
authority**, with every threshold named, given a value and a justification, and unit-tested:

wetness (full at 2 mm/h, 45 min drying half-life, 60 s wetting half-life), puddles (onset 1.5 mm/h,
full 8 mm/h, none at or below 0 C), snow cover (full at 2 cm), ice risk (freezing rain, or a wet road
below freezing), fog density (log-linear 10 km -> 200 m, with floors of 0.25 for reported BR and 0.60
for FG), wind and flag sway (full at a 25 m/s gust), umbrella share (onset 0.2 mm/h, full 3 mm/h,
ceiling 0.72), pedestrian density scale (rain, cold, heat, gales, lying snow; floor 0.35),
DSNY plough/salt activity (onset 5 cm, full 15 cm; salt below freezing), wipers (0/1/2/3 at
0.05/1/5 mm/h) and headlights (NY VTL 375(2)(a): continuous wipers, or fog, or visibility < 1 km),
and the `SurfaceClass` handed to the tyre model. A time-stepped variant gives wetness and puddles
memory so a shower leaves the streets wet. **6,480 sampled weather states** (9 temperatures x
6 rates x 5 depths x 4 visibilities x 6 precipitation types) confirm every output stays inside its
documented range and that the resulting friction stays in [0.10, 1.00]; an all-unknown state produces
finite drives and dry asphalt rather than NaN.

### 5.2 §15 — the C++ record layout was packed; the producer is naturally aligned (**fixed**)

`core/include/nycsim/io/NycbRecords.h` used `#pragma pack(push, 1)`. The producer,
`pipeline/nycsim_pipeline/runtime/nycb.py`, builds every dtype with `align=True` (natural C
alignment) and its header carries 4 bytes of padding after `section_count`. The C++ reader would
therefore have read `index_offset` from the wrong bytes and mis-decoded two record types. Confirmed
against the roads stage's own `data/processed/runtime/nycb_layout.json`. Fixed:

| item | was (packed) | is (producer) |
|---|---:|---:|
| header | 20 B, `index_offset` at 12 | **24 B, `index_offset` at 16** |
| `Lane` | 44 B | **48 B** |
| `SignalController` | 28 B | **32 B** |
| section alignment | 16 B | **8 B** |
| section-name limit | 16 bytes | **15 bytes** (the exporter's limit; guarantees NUL termination) |

Every other record already matched. The header now carries an `offsetof` assertion for every field of
every record type, so a future change cannot drift silently. Because the records are no longer
alignment-1, `NycbReader::view<T>()` now validates the mapped pointer's alignment and returns
`ErrorCode::Misaligned` rather than risking UB, and `copyRecords<T>()` was added for callers that
cannot guarantee alignment (e.g. an arbitrary UE bulk-data pointer). Files and `fromBuffer`/`fromFile`
are always sufficiently aligned.

DATA_CONTRACTS §15 also names the reader `core/io/NycbReader.h`; the file is `core/io/Nycb.h` (reader
and writer together). Nothing else consumes that name, so the header was left where it is.

### 5.3 `json::Value::append` (**new public API**, `io/Json.h`)

RFC 8259 permits duplicate object member names and the parser must keep them (the file's own doc
comment says so), but the only public mutator, `set()`, replaces. `append()` was added and the parser
now uses it. `set()`, `find()` and the rest are unchanged.

### 5.4 `core/CMakeLists.txt` — two build options

`NYCSIM_BUILD_LANES` (default `ON`) makes the `src/{traffic,routing,peds}` subdirectories optional, so
this lane can be built and tested while another agent's lane is mid-edit. `traffic_standalone` is now
inside that guard, because its benchmark links the lane sources.

### 5.5 One calibrated vehicle constant, named

`Powertrain::maxWheelForceN = 6424.0` N. There is no published transaxle ratio for the Ford HF35
power-split eCVT, so this single value is fixed by bisection to reproduce the **published measured**
0-60 mph time at the SAE test mass. It is labelled `CALIBRATED` in the header and it is the only such
constant; everything else is `PUBLISHED` or `DERIVED` with the formula stated.

---

## 6. Gaps and what the next agents need to know

1. **`traffic` and `peds` suites are red** at the time of writing — `tests/traffic/test_sim.cpp` and
   `tests/peds/test_peds.cpp:487` (`collisions_with_peds == 0` fails with 598 over 360 samples).
   Those files belong to the traffic/pedestrian agent and were being written during this build. The
   library itself compiles and links cleanly with those lanes enabled; only their assertions fail.
2. **The repository placeholder gate**
   (`tests/test_world_integration.py::test_no_placeholder_markers_in_shipped_source`)
   has **no hits in `core/`**. It still fails on four lines outside this lane, all of which are
   legitimate uses of the *word*: `pipeline/nycsim_pipeline/buildings/citygml_join.py:348,349,353`
   (a variable named `placeholder` for unusable BINs) and `blender/props/_legends.py:3` ("Nothing here
   is a placeholder"). Those need either an `allow` pattern in the gate or a rename by their owners.
3. **Manhattanhenge dates** are within one day of the AMNH announcement; the azimuth criterion is met
   exactly. See §3.2 for why, and for the sensitivity figures.
4. **Weather fixtures are a snapshot** (2026-09-06). They are archived so the tests are hermetic and
   need no network. Re-run `gen_weather_cases.py` after refetching if a provider changes its schema.
   `gen_usno_cases.py --offline` regenerates the astronomy header from the archived USNO responses.
5. **Nothing in core does I/O over the network.** `WeatherService` takes injected fetch functions; the
   UE runtime supplies them.
6. **For the UE agents:** the six entry points, with worked snippets, are in `core/README.md`
   ("How the Unreal module consumes it"). Two rules that matter most: convert coordinates only through
   `geo/UECoords.h`, and install a fatal handler at start-up
   (`nycsim::setFatalHandler`) that routes to `UE_LOG(..., Fatal, ...)` and does not return.
7. **After adding a file to `core/src`**, re-run `unreal/tools/gen_core_unity.py` so UBT picks it up.

---

## 7. Licences of material fetched

| what | source | licence |
|---|---|---|
| `docs/verification/core/usno_oneday.json` | U.S. Naval Observatory Astronomical Applications API v4 | U.S. Government work — public domain |
| `core/tests/data/weather/nws_*.json` | NOAA / National Weather Service `api.weather.gov` | U.S. Government work — public domain |
| `core/tests/data/weather/metar_*.txt`, `awc_metar.json` | NOAA `tgftp.nws.noaa.gov`, `aviationweather.gov` | U.S. Government work — public domain |
| `core/tests/data/weather/open_meteo.json` | Open-Meteo | CC BY 4.0 (attribution recorded here) |

`core/third_party/doctest` was already vendored with its `LICENSE_RECORD.json` (MIT).
