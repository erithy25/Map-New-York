# Stage report — live services (`services/nycsim_live`)

Author: live-services agent. Run date **2026-09-06**, all live values fetched between 11:16 and 12:04 UTC
(07:16–08:04 EDT) from this container. Lane: `services/nycsim_live/`, `services/tests/`,
`docs/verification/live/`, `docs/LIVE_ALGORITHMS.md` (plus the appended §12.1 of `docs/DATA_CONTRACTS.md`).

---

## 1. What was built

| File | Lines | Purpose |
|---|---|---|
| `services/nycsim_live/timesync.py` | 378 | civil time, US DST arithmetic, Julian day, ΔT, `SimTime` |
| `services/nycsim_live/astronomy.py` | 974 | full NREL SPA sun, Meeus 47/48 moon, rise/transit/set, Manhattanhenge |
| `services/nycsim_live/metar.py` | 497 | METAR/SPECI parser incl. a real present-weather and remark decoder |
| `services/nycsim_live/weather.py` | 822 | NWS / Open-Meteo / METAR providers, circuit breakers, snow model, `WeatherService` |
| `services/nycsim_live/worldmapping.py` | 461 | weather → wetness, puddles, snow cover, fog, wind, umbrellas, plow/salt, condensation |
| `services/nycsim_live/debug_overlay.py` | 287 | the exact monospace text block the Unreal overlay draws |
| `services/nycsim_live/grid_azimuth.py` | 157 | offline derivation of the Manhattan grid azimuth from LION |
| `services/nycsim_live/__main__.py` | 172 | CLI: poll loop, `manhattanhenge`, `spa-check`, `overlay` |
| `services/nycsim_live/{net,paths,__init__}.py` | 176 | one-request HTTP layer, output paths + manifest hooks |
| `services/tests/*` | 7 files | 344 offline tests against 36 recorded provider fixtures |
| `docs/LIVE_ALGORITHMS.md` | — | normative spec for the `core/weather` + `core/astro` C++ port |
| `docs/DATA_CONTRACTS.md` §12.1 | — | appended extension of the `live/*.json` schemas |

New in this session: `worldmapping.py`, `debug_overlay.py`, `grid_azimuth.py`, `__main__.py`, the whole test
suite, `LIVE_ALGORITHMS.md`, this report, `manhattan_grid_azimuth.json`, and the regenerated
`manhattanhenge_2026.json`. Fixes made to the pre-existing modules are listed in §7.

Outputs written: `data/processed/live/{weather,esb_lights,tides,world_state,snow_state}.json` and
`overlay.txt`, all recorded in `data/manifest/processed.json` under stage `live`
(`live/weather`, `live/esb_lights`, `live/tides`, with SHA-256).

---

## 2. Live run — the actual New York weather at run time

`PYTHONPATH=services python3 -m nycsim_live --once --print-overlay --record`, last run
**2026-09-06 12:03:20 UTC** (08:03:20 EDT).

### 2.1 The observation that was served (`data/processed/live/weather.json`)

```
source            nws          station KNYC (Central Park)
observed_at       2026-09-06T10:51:00Z      fetched_at 2026-09-06T12:03:20Z   stale_age_s 4340.3
raw_text          KNYC 061051Z 00000KT 10SM CLR 18/16 A2996 RMK AO2 SLP138 T01780156
temp_c 18.356   dewpoint_c 15.6   rh 83.98   wind_mps 0.0 (calm, wind_dir_deg null)
precip_type "none"  precip_rate_mmph 0.0  precip_rate_basis "none"  thunder false  obscuration []
cloud_cover 0.02   visibility_m 16090   pressure_hpa 1013.8   snow_depth_cm 0.0 (source "none")
interpolated true   provider_status {nws: closed, open_meteo: closed, metar: closed}
```

Decoding the raw report by hand: **KNYC, 6th at 10:51 UTC, calm wind, 10 statute miles visibility, sky
clear, 18/16 °C, altimeter 29.96 inHg; remarks: automated station type 2, sea-level pressure 1013.8 hPa,
precise temperature 17.8 °C / dew point 15.6 °C.** That is a warm, humid, calm, cloudless early-September
morning in Central Park — which is what New York had.

Each provider was also exercised individually at 11:57–12:02 UTC:

| provider | station / point | observation | values |
|---|---|---|---|
| NWS | KNYC | 2026-09-06T10:51:00Z | T 17.8 °C, Td 15.6, RH 87 %, calm, CLR, 16 090 m, 1013.8 hPa |
| METAR (aviationweather.gov) | KNYC | 2026-09-06T11:51:00Z | `METAR KNYC 061151Z 06004KT 10SM BKN024 18/16 A2999 RMK AO2 SLP146 T01830156 10206 20178 51023` → T 18.3, Td 15.6, RH 84.3 %, wind 060° 2.06 m/s, cover 0.75, 16 093 m, 1014.6 hPa |
| Open-Meteo | 40.789, −73.966 | 2026-09-06T12:00:00Z | T 19.0, Td 15.6, RH 81 %, wind 1.66 m/s from 025°, cover 0.77, vis 18 000 m, 1014.3 hPa, WMO code 2 |

Three independent sources agree on the dew point to 0.0 °C, on temperature within 1.2 °C and on pressure
within 0.8 hPa — the spread is the real spatial/temporal spread between Central Park, the model grid and the
observation times, not a parsing error.

### 2.2 `esb_lights.json` (live from esbnyc.com, 12:03:21 UTC)

```
date 2026-09-06   colors ["Red","White","Blue"]   rgb [[230,20,20],[255,255,255],[0,70,255]]
reason "In Honor of Labor Day"   hours "sunset to 02:00"   fallback false   unknown_colors []
source_url https://www.esbnyc.com/about/tower-lights
```

Red/white/blue for Labor Day weekend (Labor Day 2026 is Monday 7 September) — read from the tower-lights
three-day block, cross-checked against the September 2026 calendar page.

### 2.3 `tides.json` (live from NOAA CO-OPS, 12:03:22 UTC)

```
The Battery (8518750)  water level  0.884 m MLLW  =  0.038 m NAVD88   observed 2026-09-06T11:54:00Z  quality p
NAVD88 − MLLW = 0.846 m  (from the station datums API, epoch 1983–2001)
next L 2026-09-06T14:38Z  0.238 m MLLW (−0.608 m NAVD88)
next H 2026-09-06T20:44Z  1.622 m MLLW ( 0.776 m NAVD88)
currents (all ebbing, mid-ebb):
  NYH1924 Hell Gate, East River            1.701 m/s toward 241° (WSW)
  NYH1920 Brooklyn Bridge, East River      1.136 m/s toward 234°
  n03020  The Narrows                      0.939 m/s toward 144°
  NYH1927 Hudson River entrance            0.469 m/s toward 183°
stale false   errors []
```

Consistent with the tide table: falling water between the 08:44 EDT high and the 10:38 EDT low, so a strong
ebb through Hell Gate. Hell Gate ebbing at 1.7 m/s (3.3 kn) is the expected mid-ebb peak there.

### 2.4 `overlay.txt` and `world_state.json`

The complete overlay for that instant is in `data/processed/live/overlay.txt` (88 lines, 8 sections, longest line 63 characters). The
derived world state for a dry, calm, clear morning is all zeros except `extinction_per_m = 0.000243`
(= 3.912 / 16 090 m) and `cloud_cover = 0.02`, with `missing: ["wind_dir_deg"]` because the wind was calm —
the field is `null`, not `0`, exactly as the contract requires.

---

## 3. Test suite

`python3 -m pytest services/tests -q` → **344 passed in 15.9 s**, entirely offline (36 recorded fixtures in
`services/tests/fixtures/`, no network).

| file | tests | what it pins down |
|---|---|---|
| `test_timesync.py` | 27 | calendar arithmetic; the DST rule against `zoneinfo` for **all 36 890 days 2000-01-01…2100-12-31** and **every hour of both transition days of every year 1967–2100**; Julian day against Meeus/SPA check points; ΔT |
| `test_astronomy.py` | 62 | the NREL SPA reference case (19 quantities incl. all intermediates); rise/transit/set against SPA A.5 **and** the USNO `rstt/oneday` API on 9 dates; Meeus examples 47.a and 48.a; moon illumination vs USNO; Manhattanhenge determinism, the declination-symmetry invariant, and the refraction-discontinuity guard |
| `test_metar.py` | 66 | every recorded report parses with **zero unparsed tokens** and matches the AWC's own decoded fields; each wind/visibility/weather/sky/remark group form; malformed input raises |
| `test_weather.py` | 70 | all three parsers against fixtures; QC-flag rejection; the gridpoint blend and its clamps; circuit-breaker state machine incl. half-open probe; stale fallback and "no history ⇒ all null"; snow model term by term; contract validation |
| `test_worldmapping.py` | 46 | every formula and constant, cadence-independence of the integrators, state persistence and corrupt-state recovery |
| `test_debug_overlay.py` | 38 | formatting primitives, that **every** weather field appears, that nulls render as `—` and never `0`, and the stale/open-breaker markers |
| `test_esb_and_tides.py` | 35 | the recorded ESB pages, colour splitting/mapping, the fallbacks; CO-OPS water level/datum/currents/hi-lo parsing, interpolation, and every degraded path |

Fixtures (captured live from the real endpoints on 2026-09-05 and 2026-09-06): 6 × `nws_obs_*.json`,
`nws_gridpoints.json` (208 KB), `nws_points.json`, `nws_station_knyc.json`, `openmeteo_current.json`,
`metar_awc_nyc.json`, `metar_awc_weather_samples.json` (11 reports chosen for thunderstorms, fog, snow and
freezing precipitation), 2 × `metar_tgftp_*.txt`, 9 × `coops_*.json`, 2 × `esb_*.html`, 9 × `usno/*.json`.

---

## 4. Manhattanhenge 2026

### 4.1 Grid azimuth — derived from LION, not assumed

`python3 -m nycsim_live.grid_azimuth` over `data/raw/lion/lion/lion.gdb`: Manhattan centrelines
(`LBoro='1'`, `FeatureTyp='0'`) named `(WEST|EAST) n STREET` with 14 ≤ n ≤ 96, end points reprojected
EPSG:2263 → WGS84, **geodesic** forward azimuth west-end → east-end, segments < 60 m or > 12° off 119°
dropped. Result over **1 812 segments / 292.9 km** (`docs/verification/live/manhattan_grid_azimuth.json`):

| statistic | value |
|---|---|
| length-weighted mean bearing | 118.9997° true |
| length-weighted median | 118.9955° |
| quartiles | 118.9383° – 119.0692° |
| 5–95 % | 118.7018° – 119.2997° |
| circular σ | 0.319° |
| per street (median) | 14th 118.966°, 23rd 119.013°, 34th 118.966°, 42nd 118.988°, 57th 118.975°, 79th 119.014° |

⇒ the grid is rotated **28.996° east of true north**, so the sunset azimuth aligned with the cross-streets
is **298.996° ≈ 299.00°** — the constant the code uses, now with a data provenance.

### 4.2 Computed events (observer: 42nd St at Tudor City Place, 40.7489 N, 73.9711 W, 20 m)

Criteria: apparent (refracted, topocentric) elevation of the disc centre **+0.500°** for *full sun*
(whole disc above a street-end horizon at +0.2333°) and **+0.2333°** for *half sun* (disc centre on that
horizon, one solar radius lower).

| kind | date | local time (EDT) | azimuth | Δ from 299.00° |
|---|---|---|---|---|
| **half sun** | **2026-05-27** | **20:13:52** | 299.1125° | +0.1125° |
| **full sun** | **2026-05-28** | **20:12:46** | 299.0263° | +0.0263° |
| **full sun** | **2026-07-14** | **20:21:14** | 298.9718° | −0.0282° |
| **half sun** | **2026-07-15** | **20:22:33** | 299.0565° | +0.0565° |

Full list of the 19 evenings within ±0.5° is in `docs/verification/live/manhattanhenge_2026.json`.
Self-consistency: the two full-sun events occur at solar declinations 21.588° and 21.549° (0.04° apart, well
inside one day's 0.16°), as they must for a criterion that depends only on declination.

### 4.3 Cross-check against the published dates — and a real discrepancy

NYC Parks (dates from the AMNH Hayden Planetarium) publishes for 2026: **half sun Thu 28 May 20:14 and
Sun 12 July 20:21; full sun Fri 29 May 20:13 and Sat 11 July 20:20**
(<https://www.nycgovparks.org/highlights/manhattanhenge>). So my May pair is **one day earlier** and my July
pair **three days later** than the published one.

Evaluating the four *published date + time* pairs with the same SPA:

| published event | azimuth | Δ from 299.00° | apparent elevation | declination |
|---|---|---|---|---|
| half, 2026-05-28 20:14 | 299.225° | +0.225° | +0.328° | 21.588° |
| full, 2026-05-29 20:13 | 299.149° | +0.149° | +0.580° | 21.741° |
| full, 2026-07-11 20:20 | 299.144° | +0.144° | +0.896° | 21.991° |
| half, 2026-07-12 20:21 | 299.185° | +0.185° | +0.683° | 21.850° |

Two things follow, and neither is an error in the astronomy:

1. **The published alignment azimuth is ≈ 299.18°, not 299.00°** — 0.18° north of the bearing the LION
   centrelines actually have. All four published date/time pairs land in 299.14–299.23°, so they are
   internally consistent about *azimuth*.
2. **The published May and July events are not the same alignment.** A criterion at a fixed elevation
   depends only on the solar declination, so the May and July events of one kind must share a declination.
   The published full-sun pair differs by **0.25° of declination** (21.741° vs 21.991°) and the half-sun pair
   by 0.26° — about 1.7 days. Equivalently: 29 May is 22.9 days before the 2026 June solstice while 11 July
   is only 20.1 days after it. **No single (grid azimuth, disc-centre elevation) pair reproduces all four
   published dates.** The sensitivity table in `manhattanhenge_2026.json` shows it directly: with the grid at
   299.00° the best full-sun date is 27 May / 15 July at elevation 0.25°, 28 May / 14 July at 0.50°,
   29 May / 13 July at 0.75° and 31 May / 11 July at 1.00° — the published 29 May needs 0.75° while the
   published 11 July needs 1.00°.

The astronomy behind this was verified independently, so the discrepancy is in the published dates, not in
the code: the SPA azimuth matches the **USNO celestial-navigation API** to **0.0001°** at five test instants
(including 2026-05-30 00:14 UT and 2026-07-12 00:23 UT, i.e. the two published evenings), and the geometric
altitude to 0.0025°. Sunrise/sunset match USNO's `rstt/oneday` to within its own ±1-minute rounding on nine
dates, and the SPA A.5 reference case reproduces to 1e−6°.

**Decision:** the simulation uses the LION-derived 299.00° and the stated elevation criteria, i.e. the four
dates in §4.2. The sensitivity table (≈ **1 day per 0.22° of grid azimuth** and ≈ **1 day per 0.22° of
assumed disc-centre elevation**) is shipped so that anyone who prefers the published dates can see exactly
which assumption produces them.

---

## 5. Reachability of every endpoint from this environment

Probed 2026-09-06 11:16–12:04 UTC (`curl` and the service itself):

| endpoint | result |
|---|---|
| `https://api.weather.gov/stations/{KNYC,KLGA,KJFK}/observations/latest` | **200**, ~0.5 s. Requires a `User-Agent`; set `NYCSIM_CONTACT` to add an operator address |
| `https://api.weather.gov/gridpoints/OKX/34,45` | **200**, 208 KB |
| `https://api.weather.gov/points/40.7831,-73.9712` | **200** (used once to derive the gridpoint URL) |
| `https://aviationweather.gov/api/data/metar?...` | **200**, ~0.25 s — **this is the working METAR endpoint** |
| `https://api.aviationweather.gov/api/data/metar?...` | **BLOCKED** — `ProxyError: Unable to connect to proxy … Tunnel connection failed`. Confirmed; the code never uses this host |
| `https://tgftp.nws.noaa.gov/data/observations/metar/stations/{station}.TXT` | **200** (secondary METAR path) |
| `https://api.open-meteo.com/v1/forecast?...` | **200 but intermittent**: measured 0.28 s, 0.43 s, 6.1 s, 9.2 s, one 503 and two 30 s timeouts within a few minutes. A cold TLS session through the shared egress proxy can take ~10–30 s |
| `https://api.tidesandcurrents.noaa.gov/api/prod/datagetter` and `/mdapi/prod/webapi` | **200**, ~0.9 s |
| `https://www.esbnyc.com/about/tower-lights` and `/calendar/<yyyymm>` | **200**, 77 KB / 67 KB |
| `https://aa.usno.navy.mil/api/{rstt/oneday,celnav}` | **200** (verification only, not a runtime dependency) |
| `https://www.amnh.org/...` , `https://www.timeanddate.com/...` | **403** to this container; NYC Parks served the same AMNH dates and was used instead |

Because of the Open-Meteo latency, the Open-Meteo provider's per-request timeout is **25 s**
(`OPEN_METEO_TIMEOUT_S`); NWS and METAR keep the 10 s default. Before that change the provider timed out on
2 of 3 attempts and the circuit breaker (correctly) counted the failures; after it, the provider returned a
valid observation.

---

## 6. Live findings worth passing on

* **api.weather.gov lags.** At 12:01 UTC the API still served KNYC's **10:51Z** observation while
  aviationweather.gov already had KNYC's **11:51Z** METAR. The strict ADR-011 order therefore publishes a
  70-minute-old observation while a 10-minute-old one is available.
* **The forecast blend was measurably wrong on this sample.** Carrying the 10:51Z observation (17.8 °C)
  along the gridpoint trend to 11:51Z gave **17.24 °C**, while the independent 11:51Z METAR measured
  **18.30 °C** — the blend's error (−1.06 °C) was *larger* than simply keeping the stale observation
  (−0.50 °C), because the gridpoint forecast had the morning minimum an hour late. Cloud cover: observation
  CLR 0.00 → blended 0.04, actual BKN024 0.75 (the clamped +0.04 correction was in the right direction but
  far too small). One sample is not a statistic, so nothing was tuned on it — but the number is recorded, the
  blend stays clamped (±5 °C, ±0.40 cover) and every blended record is flagged `interpolated: true`, so a
  consumer can always reject it.
* **Proposed ADR-013 (not applied).** *"When the leading provider's observation is older than N minutes,
  query the remaining closed-breaker providers and publish the freshest observation."* This is implemented
  and tested as `WeatherService(prefer_freshest_age_s=N)` but is **off by default**, because switching it on
  would contradict ADR-011's strict ordering. With it off, behaviour is identical to ADR-011. Evidence for
  adopting it is the two bullets above; the cost is one extra request per poll only while the leader is
  stale.

---

## 7. Corrections made to the modules written in the previous (interrupted) session

All found by the new tests or by the live/USNO cross-checks:

1. **`astronomy.sun_rise_transit_set` was wrong by up to ~30 s.** SPA A.2 is a single Newton step from an
   approximate start; the SPA A.5 sunset came out as 17:20:19 instead of 17:18:51 local. Added
   `geometric_altitude` / `local_hour_angle` and an exact bisection refinement (±30 min window, 0.05 s
   tolerance). The reference case now reproduces exactly and the USNO comparison over nine dates is within
   USNO's own rounding.
2. **Rise/set were returned on the wrong absolute day** for observers west of Greenwich whose sunset falls
   after 00 UT. Added `sun_events_at_offset(local_date, observer, utc_offset_s)`; `sun_events_local` now
   delegates to it. (NYC was already handled correctly by the local wrapper; the SPA reference site was not.)
3. **`time_of_evening_elevation` could return a bogus solution.** The SPA switches refraction off at
   `−(SUN_RADIUS + atmos_refract)`, so apparent elevations between about −0.83° and −0.22° do not exist and
   the bisection converged on the discontinuity. It now validates the solution and returns `None`.
4. **NWS `presentWeather[].rawString` was never parsed.** The code built `"XXXX 000000Z <raw>"`, and day
   `00` is rejected by the time-group validator, so every raw present-weather group was silently discarded.
   Fixed to a valid dummy time group (`010000Z`).
5. **`metar.parse_metar` accepted a report with no time group at all** (e.g. `"KNYC"`). It now raises unless
   the report is explicitly `NIL`.
6. **ESB records could be published with an empty `rgb` list** when no colour name resolved, leaving the
   tower unlit. `_make` now falls back to signature white while keeping the published names and listing them
   in `unknown_colors`.
7. **The Manhattan grid azimuth was an assumed literature value.** Replaced by the LION derivation of §4.1
   (same number, 299.00°, now with provenance and a reproducible script).
8. **Open-Meteo timed out** at the shared 10 s budget; per-provider timeouts added (§5).
9. **The overlay flagged good data as STALE.** The 1 h threshold tripped every hour on KNYC, which reports
   hourly at :51. It is now `weather.MAX_OBSERVATION_AGE_S` (2.5 h) — the age past which a provider
   observation is rejected anyway.

---

## 8. Fidelity achieved vs. target, and the gaps

**Achieved.**

* Sun: full NREL SPA, reference case exact to 1e−6°, independently confirmed against USNO to 1e−4°.
* Moon: full Meeus 47.A/47.B with the additive terms, Meeus examples 47.a/48.a reproduced.
* DST: pure integer arithmetic, identical to the IANA database on every day 2000–2100 and every hour of
  every transition day 1967–2100.
* Weather: three real providers with real parsers (the METAR parser leaves **zero** unparsed tokens on every
  recorded report), per-provider circuit breakers (3 failures → 5 min open → half-open probe), 60 s poll,
  explicit `source: "stale"` with an age in seconds, and **never** a synthetic value — with no history at
  all every field is `null`.
* World mapping and the overlay: complete, with every constant documented and unit-tested.

**Gaps, stated plainly.**

* **Wetness, puddles, umbrella probability, road-clearing rates and the snow-cover thresholds are modelled,
  not measured.** Each is a documented closed-form rule with a physical justification and a named constant
  (§4 of `LIVE_ALGORITHMS.md`), but NYC publishes no per-street wetness or umbrella telemetry to calibrate
  against. They are flagged as derived (`world_state.json` is a separate document from `weather.json`) and
  the model has no per-street plow routing — one city-wide clearing rate is applied to every street class.
* **The snow-depth model has not been exercised against a real snow event** — September. Its terms are
  unit-tested individually and its constants are sourced (Roebber SLR bands; DSNY's 2-inch plow threshold),
  but no end-to-end validation against a real storm was possible in this run.
* **`window_condensation` is computed for two standard glazing assemblies**, not per building: the buildings
  data has no glazing attribute, so the renderer gets both the single- and double-glazed value and must
  choose per material.
* **The forecast blend is unvalidated** beyond the single adverse sample of §6.
* **Manhattanhenge disagrees with the published dates** by 1 day (May) and 3 days (July); §4.3 shows the
  discrepancy is in the published dates' internal inconsistency, and ships the sensitivity table.
* **`grid_azimuth.py` needs `pyogrio`/`pyproj`/`shapely`**; they are imported lazily so the runtime service
  has no geo dependency, and the derived constant is baked in.

---

## 9. What the next agent needs to know

* **The C++ port**: `docs/LIVE_ALGORITHMS.md` is normative and complete — every constant, branch order and
  rounding rule. Port targets: `core/astro` (§1–2) and `core/weather` (§3–4, 7). The SPA reference case
  (§2.1), the DST cross-check (§1.2) and the Manhattanhenge declination invariant (§2.6) are the three
  assertions worth having in doctest.
* **Schemas**: `docs/DATA_CONTRACTS.md` §12 is unchanged; §12.1 (appended by this stage, clearly marked)
  documents the added keys and the two new documents `world_state.json` and `snow_state.json`, plus
  `overlay.txt`.
* **Angles**: `*_dir_deg` mathematical, `*_heading` compass. `world_state.wind_vector_ue` is already in UE
  axes (x = east, y = −north, z = up) in **m/s** — multiply by 100 for centimetres.
* **Unreal**: draw `overlay.txt` verbatim with a monospace font; it is 62-column headers, ≤ 110 characters
  per line, and uses `—` (U+2014) for every missing value.
* **Running it**: `PYTHONPATH=services python3 -m nycsim_live` (60 s loop), `--once` for a single poll,
  `--print-overlay` to see the block, `--record` to write manifest entries. `spa-check` self-verifies the
  astronomy in one second with no network.
* **Do not** point the METAR provider at `api.aviationweather.gov` — that host is blocked here.

---

## 10. Licences of everything fetched

All runtime sources are US federal government works or open data, used through their public APIs with no key:
NWS / api.weather.gov and tgftp.nws.noaa.gov (US Government, public domain), aviationweather.gov (NOAA/FAA,
public domain), NOAA CO-OPS tidesandcurrents.noaa.gov (public domain), USNO aa.usno.navy.mil (public domain,
verification only), Open-Meteo (CC-BY 4.0, attribution "Weather data by Open-Meteo.com" — carried in
`weather.json` via `station: "open-meteo:<lat>,<lon>"` and required in any UI that shows Open-Meteo-sourced
weather), esbnyc.com tower-lights schedule (published schedule, used as factual data with `source_url`
recorded in every record). NYC DCP LION (§4.1) is NYC Open Data, already in `data/manifest/downloads.json`.
No credential, API key or personal data is used anywhere in this stage.
