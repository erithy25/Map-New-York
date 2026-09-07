# Live services — exact algorithms, constants and mappings

Reference specification for `services/nycsim_live/*.py` and its C++ port in `core/astro` and
`core/weather`. Every constant, formula, branch order and rounding rule below is normative: a C++
implementation that follows this document reproduces the Python number for number (the tolerances the
Python test-suite asserts are given per section, and `services/tests` is the executable form of this
document — 342 tests, all offline).

Conventions used throughout:

* **Angles** in degrees. `*_dir_deg` is *mathematical* (0 = east, counter-clockwise); `*_heading` is
  *compass* (0 = north, clockwise). Conversion both ways: `compass = (90 − math) mod 360`.
* **Time** is POSIX seconds (no leap seconds; a UTC day is exactly 86 400 s).
* **Vectors** are ENU metres (x = east, y = north, z = up). The UE mapping is `UE.x = east`,
  `UE.y = −north`, `UE.z = up` (`core/geo/UECoords.h`).
* `clamp(x, lo, hi)` returns `lo` if `x < lo`, `hi` if `x > hi`, else `x`.
* Values that are unknown are `null`/`std::optional` **empty** — never 0, never a default.

---

## 1. Civil time (`timesync.py` → `core/astro/TimeSync`)

### 1.1 Calendar arithmetic

* `days_from_civil(y, m, d)` / `civil_from_days(n)` — Howard Hinnant's proleptic-Gregorian algorithms,
  exact for every representable year. `days_from_civil(1970,1,1) = 0`, `days_from_civil(2000,1,1) = 10957`.
* `day_of_week(y, m, d)` — Sakamoto's table `t = {0,3,2,5,0,3,5,1,4,6,2,4}`, `0 = Sunday`.
* `is_leap_year(y) = y%4==0 && (y%100!=0 || y%400==0)`.
* `nth_weekday_of_month(y, m, w, n)`: `first = 1 + (w − day_of_week(y,m,1)) mod 7`, result `first + 7(n−1)`.
* `last_weekday_of_month(y, m, w)`: `dim − (day_of_week(y,m,dim) − w) mod 7`.

### 1.2 US daylight-saving rule for America/New_York (arithmetic, no tz database)

DST is in effect for `start ≤ t < end`, with the local rule dates:

| years | start | end |
|---|---|---|
| ≥ 2007 | 2nd Sunday of March | 1st Sunday of November |
| 1987–2006 | 1st Sunday of April | last Sunday of October |
| 1976–1986 | last Sunday of April | last Sunday of October |
| 1975 | 23 February | last Sunday of October |
| 1974 | 6 January | last Sunday of October |
| 1967–1973 | last Sunday of April | last Sunday of October |
| < 1967 | **error** — use the IANA database |

The instants: `start = unix_utc(y, sm, sd, 02:00) − (−5 h)` (02:00 EST) and
`end = unix_utc(y, em, ed, 02:00) − (−4 h)` (02:00 EDT). Offsets: `EST = −18000 s`, `EDT = −14400 s`.

*Verification.* `test_timesync.py` compares this rule with `zoneinfo("America/New_York")` at 12:00 UTC on
**every one of the 36 890 days from 2000-01-01 to 2100-12-31** (exact match), at **every hour of both
transition days of every year 1967–2100**, and one second either side of every boundary for 2007, 2026,
2050 and 2099.

### 1.3 Julian day

`julian_day(utc)` — Meeus ch. 7 with the Gregorian correction `B = 2 − A + floor(A/4)`, `A = floor(y/100)`:

```
d  = day + (hour + (minute + (second + µs/1e6)/60)/60)/24
if month <= 2: year -= 1; month += 12
JD = floor(365.25(year+4716)) + floor(30.6001(month+1)) + d + B − 1524.5
```

Checks: 2000-01-01T12:00Z → 2451545.0; 1957-10-04T19:26:24Z → 2436116.31;
2003-10-17T19:30:30Z → 2452930.312847. Equivalently `JD = unix/86400 + 2440587.5`
(round-trip through POSIX seconds is exact to 4·10⁻⁵ s — one float64 ulp of a JD near 2.46·10⁶).

### 1.4 ΔT = TT − UT1

For 1972-01-01 ≤ t and year ≤ (last leap second's year + 20): `ΔT = 32.184 + (TAI−UTC)(t) − DUT1`, with
`DUT1 = 0` by default (|DUT1| < 0.9 s by definition, i.e. < 0.004° of hour angle). The `TAI−UTC` step table
is complete to 2026-09 and ends at **37 s from 2017-01-01**; before 1972 the value 10 is used.
So **ΔT = 69.184 s for any date in 2026**, and 64.184 s in 2003.

Outside that span the Espenak–Meeus (2006) piecewise polynomial is used, with the published breakpoints
−500/500/1600/1700/1800/1860/1900/1920/1941/1961/1986/2005/2050/2150 (coefficients in
`timesync.delta_t_polynomial`; for 2005–2050 `ΔT = 62.92 + 0.32217 t + 0.005589 t²`, `t = y − 2000`).

### 1.5 `SimTime`

One UTC instant → `{utc, unix_s, jd, jde = jd + ΔT/86400, delta_t_s, local, utc_offset_s, is_dst,
tz_abbreviation ("EST"|"EDT"), local_date, seconds_since_local_midnight, day_of_year, dst_start_unix,
dst_end_unix}`. The offset comes from `zoneinfo` when a tz database is present (it also covers pre-1967),
otherwise from §1.2.

---

## 2. Astronomy (`astronomy.py` → `core/astro`)

### 2.1 Sun — NREL SPA (Reda & Andreas, NREL/TP-560-34302 rev. 2008)

The full algorithm, not a truncation: Earth heliocentric longitude/latitude/radius from the complete
L0–L5, B0–B1 and R0–R4 tables (Table A4.2), nutation from all 63 rows of Table A4.3, then §3.5–3.14 of the
paper. Constants: `SUN_RADIUS_DEG = 0.26667`, `ATMOS_REFRACT_HORIZON_DEG = 0.5667`, Earth radius
6 378 140 m for the topocentric correction, flattening factor `0.99664719`.

Refraction (eq. 42), applied **only** when `e0 ≥ −(body_radius + atmos_refract)`:

```
Δe = (P/1010)·(283/(273+T))·1.02 / (60·tan((e0 + 10.3/(e0 + 5.11))·π/180))     [degrees]
```

At `e0 = 0`, P = 1013.25 mbar, T = 15 °C this is **0.476173°**. Azimuth is computed astronomically
(from south, westward, eq. 44) and converted to compass by `+180 mod 360`.

**Reference case (must match exactly).** 2003-10-17 12:30:30 at UTC−7 (= 19:30:30 UTC),
39.742476° N, 105.1786° W, 1830.14 m, 820 mbar, 11 °C, ΔT = 67 s:

| quantity | value | tolerance |
|---|---|---|
| JD | 2452930.312847 | 1e−6 |
| L (heliocentric longitude) | 24.0182616° | 1e−6 |
| B | −0.0001011219° | 1e−9 |
| R | 0.9965422974 AU | 1e−9 |
| Δψ | −0.00399840° | 1e−8 |
| Δε | 0.00166657° | 1e−8 |
| ε | 23.440465° | 1e−6 |
| λ (apparent) | 204.0085519° | 1e−6 |
| ν (apparent sidereal time) | 318.5119° | 1e−4 |
| α | 202.22741° | 1e−5 |
| δ | −9.31434° | 1e−5 |
| H | 11.105900° | 1e−5 |
| e (topocentric, refracted) | 39.888378° | 1e−6 |
| **θ (zenith)** | **50.111622°** | 1e−6 |
| **Φ (azimuth)** | **194.340241°** | 1e−6 |

Independently cross-checked against the **USNO celestial-navigation API** at five instants (NYC and the
Colorado site): azimuth agrees to **0.0001°**, geometric altitude to **0.0025°**.

### 2.2 Sunrise, transit, sunset

SPA Appendix A.2 produces the initial estimate (three-day α/δ interpolation with `ΔT = 0` at 0 h TT,
`h0 = −0.8333°`, `m0 = ((α − λ − ν)/360) mod 1`). **A.2 is only a single Newton step and is wrong by up to
~30 s, so the estimate is refined:** bisect the *geometric* altitude

```
geometric_altitude(t) = asin(sin φ sin δ + cos φ cos δ cos H)     (geocentric δ, no refraction, no parallax)
```

onto `h0` within ±1800 s to a tolerance of 0.05 s; transit is bisected onto `local_hour_angle(t) = 0`
(hour angle in (−180, 180]). If the window does not bracket a crossing the A.2 estimate is kept.

A.2 yields events of a **UT** day. `sun_events_at_offset(local_date, observer, utc_offset_s)` evaluates the
UT days `local_date` and `local_date + 1` and keeps each event whose local date matches — west of Greenwich
the evening sunset is usually just after 00 UT of the next UT day. `sun_events_local` is that with New
York's own offset.

Verification: SPA A.5 reference site/date gives sunrise **06:12:43**, transit **11:46:04**, sunset
**17:18:51** local (UTC−7); against the USNO `rstt/oneday` API for Central Park on nine dates every event
agrees to within the ±1 minute of USNO's own rounding.

### 2.3 Moon — Meeus ch. 47/48

Full Tables 47.A (60 terms, Σl and Σr) and 47.B (60 terms, Σb) with the eccentricity factor
`E = 1 − 0.002516 T − 0.0000074 T²` applied as `E^|m|`, plus the additive terms

```
Σl += 3958 sin A1 + 1962 sin(L' − F) + 318 sin A2
Σb += −2235 sin L' + 382 sin A3 + 175 sin(A1 − F) + 175 sin(A1 + F) + 127 sin(L' − M') − 115 sin(L' + M')
A1 = 119.75 + 131.849 T,  A2 = 53.09 + 479264.290 T,  A3 = 313.45 + 481266.484 T
```

`λ = L' + Σl/10⁶`, `β = Σb/10⁶`, `Δ = 385000.56 + Σr/1000` km, `π = asin(6378.14/Δ)`. Apparent longitude
adds the SPA nutation Δψ; α/δ use the true obliquity. Topocentric position uses the same SPA parallax
correction with `π` in place of the solar `ξ`, and the refraction of §2.1 with
`body_radius = semidiameter = asin(0.272481 sin π)` (Meeus 55.1).

Illumination (Meeus 48.1–48.3), from the **geocentric** positions:

```
cos ψ = sin δ☉ sin δ☾ + cos δ☉ cos δ☾ cos(α☉ − α☾)
i     = atan2(R sin ψ, Δ − R cos ψ)          R = solar distance in km
k     = (1 + cos i)/2
elongation = (λ☾,app − λ☉,app) mod 360        (< 180° ⇒ waxing)
```

Phase name: eight equal 45° octants, `idx = floor(((elongation + 22.5) mod 360)/45)` over
`("New Moon", "Waxing Crescent", "First Quarter", "Waxing Gibbous", "Full Moon", "Waning Gibbous",
"Last Quarter", "Waning Crescent")`. (USNO's `curphase` uses a different convention — principal phases
only at their exact instants — so the two disagree for about a day either side of each principal phase.)

Verification: Meeus example 47.a (1992-04-12 00:00 TD) — L' 134.290182°, D 113.842304°, M 97.643514°,
M' 5.150833°, F 219.889721°, λ 133.162655°, β −3.229126°, Δ 368409.7 km, π 0.991990° (all to 1e−5);
example 48.a — `i = 69.0756°`, `k = 0.6786`. Illuminated fraction against the USNO `fracillum` on nine
dates lies inside the day's range each time.

### 2.4 `geometric_altitude` / `local_hour_angle`

Exported because both the rise/set refinement and the C++ port's own solvers need them; see §2.2.

### 2.5 Manhattan grid azimuth — derived, not assumed

`MANHATTAN_STREET_SUNSET_AZIMUTH_DEG = 299.00°`, derived from the **NYC DCP LION street centrelines**
(`data/raw/lion/lion/lion.gdb`, layer `lion`) by `nycsim_live/grid_azimuth.py`:

1. `LBoro = '1'` (Manhattan) and `FeatureTyp = '0'` (real street centreline) → 28 048 segments;
2. names matching `(WEST|EAST) n STREET` with 14 ≤ n ≤ 96 (the regular Commissioners'-Plan grid);
3. end points reprojected EPSG:2263 → WGS84 and the **geodesic** forward azimuth taken west-end → east-end
   (working in the projected plane would carry the ≈0.013° State-Plane meridian convergence into the answer);
4. segments shorter than 60 m or more than 12° from 119° discarded (kerb stubs, ramps, diagonals).

Result over **1 812 segments / 292.9 km**: length-weighted mean **118.9997°**, median **118.9955°**,
quartiles 118.938–119.069°, 5–95 % 118.702–119.297°, circular σ 0.319°. Per street:
14th 118.966°, 23rd 119.013°, 34th 118.966°, 42nd 118.988°, 57th 118.975°, 79th 119.014°.
⇒ grid rotated **28.996° east of north**, sunset azimuth **298.996° ≈ 299.00°**.
Recorded in `docs/verification/live/manhattan_grid_azimuth.json`.

### 2.6 Manhattanhenge

Definitions used (both refer to the **apparent, refracted, topocentric elevation of the disc centre**):

* **full sun** — `FULL_SUN_ELEVATION_DEG = 0.50°`: the whole disc is above a street-end horizon that sits
  `0.50 − 0.26667 = 0.2333°` above the astronomical horizon (the New Jersey shoreline from mid-Manhattan
  street level);
* **half sun** — `HALF_SUN_ELEVATION_DEG = 0.2333°`: the disc centre on that same horizon, one solar radius
  lower.

For each local date, `time_of_evening_elevation` bisects the apparent elevation onto the target between
solar transit and sunset + 90 min (elevation is strictly decreasing there at NYC latitude), tolerance
0.05 s, then **validates** that the solution really sits on the target (|Δ| ≤ 1e−3°): apparent elevations
between about −0.83° and −0.22° do not exist, because the SPA switches refraction off at
`−(SUN_RADIUS_DEG + atmos_refract)` and the apparent elevation jumps there.

An event is reported when `|azimuth − 299.00| ≤ 0.5°` between 1 May and 15 August; the closest of each kind
before and after the June solstice is flagged `best_in_season`. Observer: 42nd Street at Tudor City Place,
40.7489° N, 73.9711° W, 20 m, 1013.25 mbar, 15 °C.

Sensitivity (2026, in `docs/verification/live/manhattanhenge_2026.json`): the best date moves by **one day
per ≈0.22° of assumed disc-centre elevation** and by **one day per ≈0.22° of assumed grid azimuth**; the
sunset azimuth changes 0.22°/day in late May and −0.21°/day in mid-July.

Because the criterion at a fixed elevation depends only on the solar declination, the May and July events
of the same kind **must** occur at the same declination. That is the invariant the C++ port should assert
(the Python suite does: the two 2026 full-sun events differ by 0.04° of declination, well inside one day's
0.16°).

---

## 3. Weather (`metar.py`, `weather.py` → `core/weather`)

### 3.1 Unit constants

`KT_TO_MPS = 0.514444` (1852/3600), `KMH_TO_MPS = 1/3.6`, `STATUTE_MILE_M = 1609.344`, `FOOT_M = 0.3048`,
`INHG_TO_HPA = 33.86389`, `HUNDREDTH_INCH_MM = 0.254`, `INCH_CM = 2.54`,
`VIS_UNLIMITED_M = 16093.44` (10 SM; also the cap for `9999` and CAVOK).

### 3.2 METAR parser

Token grammar (regexes in `metar.py`), in body order: optional `METAR`/`SPECI`, optional `COR`, station
(`[A-Z][A-Z0-9]{3}`, **required**), time `ddhhmmZ` (**required unless the report is `NIL`**; `dd` must be
1–31, `hh` ≤ 24, `mm` ≤ 59), then `AUTO`/`COR`/`NIL`/`RTD`/`CCx`, then in any order: wind
`(ddd|VRB|///)(ff|//)(Gff)?(KT|MPS|KMH)`, variable range `dddVddd`, visibility (`[MP]?n n/dSM`, `dddd` with
optional direction, `CAVOK`), RVR `Rxx/…` (kept in `rvr`), present weather
`([+-])?(VC)?(descriptor)?(phenomena…)`, sky `(FEW|SCT|BKN|OVC|VV)(hhh|///)(CB|TCU|///)?`, temperature
`(M?dd)/(M?dd)?`, altimeter `Adddd` (inHg/100) or `Qdddd` (hPa). Everything after `NOSIG|TEMPO|BECMG|NSW|FMhhmm`
is the trend; everything after ` RMK ` is remarks. Unrecognised tokens go to `unparsed` (never silently dropped).

Remarks decoded: `SLPppp` → `ppp/10 + (1000 if ppp ≥ 500 else 1100)` hPa; `Tsnnnsnnn` → temperature and
dew point to 0.1 °C (sign digit 1 = negative), which **overrides** the whole-degree body group;
`Pnnnn` → hundredths of an inch in the last hour (`P0000` = trace); `6nnnn`/`7nnnn` → 3/6-hourly and
24-hourly totals; `4/sss` → snow depth in whole inches → cm; `931sss` → 6-hourly snowfall (tenths of an
inch); `933sss` → snow water equivalent (tenths of an inch); `PK WND dddff/(hh)mm`; `$` → maintenance flag.

Observation time (`resolve_observation_time`): the day-of-month from the report is placed on the most
recent month that yields an instant ≤ reference + 15 min, wrapping back across a month boundary when needed.

Cloud cover — okta midpoints, and METAR layer amounts are cumulative so the **maximum** layer wins:

| code | fraction |
|---|---|
| SKC / CLR / NSC / NCD | 0.0 |
| FEW (1–2/8) | 0.1875 |
| SCT (3–4/8) | 0.4375 |
| BKN (5–7/8) | 0.75 |
| OVC, VV | 1.0 |
| *no sky group at all* | **null** |

### 3.3 Precipitation classification and rate

`classify_precipitation(groups, temp_c)` → (`precip_type`, intensity code). Vicinity (`VC`) groups never
count. Per group, in this order: `FZ` with `RA|DZ` → `freezing_rain`; `PL|GS|GR`, or `SN` together with
`RA|DZ` → `sleet`; `SN|SG|IC` → `snow`; `RA` → `rain`; `UP` → `rain` if `T > 1 °C` else `snow`;
`DZ` → `drizzle`. Across groups the highest rank wins
(`none < drizzle < rain < snow < sleet < freezing_rain`), ties broken by intensity (`−` < `` < `+`).

Rate (`precip_rate_mmph`) and its `precip_rate_basis`:

1. `none` ⇒ `0.0`, basis `none`;
2. a measured hourly amount > 0 ⇒ that value (mm), basis `measured`;
3. a measured amount of exactly 0 with precipitation falling ⇒ `TRACE_RATE_MMPH = 0.1`, basis `trace`;
4. otherwise the class representative below, ×`THUNDERSTORM_RATE_FACTOR = 1.5` if any precipitating group
   carries the `TS` descriptor, basis `class`.

Liquid-equivalent class representatives (mm/h), from the FMH-1 §8.5 intensity bands:

| type | light `−` | moderate `` | heavy `+` |
|---|---|---|---|
| rain | 1.0 | 4.0 | 10.0 |
| drizzle | 0.2 | 0.5 | 1.0 |
| snow | 0.5 | 1.5 | 3.0 |
| sleet | 1.0 | 3.0 | 6.0 |
| freezing rain | 0.5 | 2.0 | 4.0 |

`obscuration(groups)` = the phenomena in `{BR FG FU VA DU SA HZ PY}` ∪ `{PO SQ FC SS DS}` of non-vicinity
groups. `thunder_present(groups)` = any group with descriptor `TS`, **including `VCTS`** (thunder is
audible from the vicinity).

### 3.4 Providers, in order (ADR-011)

Every provider yields the same `WeatherObservation`. An observation older than
`MAX_OBSERVATION_AGE_S = 9000 s` (2.5 h) is a provider failure, not a value.

**(1) NWS** — `https://api.weather.gov/stations/{KNYC,KLGA,KJFK}/observations/latest`
(`Accept: application/geo+json`, a `User-Agent` identifying the application is mandatory). Stations are
tried in order until one parses. Values are read through a quality-control gate: a field whose
`qualityControl` is `X`, `Q` or `B` (MADIS rejected / questioned / subjective-bad) is treated as absent.
`windSpeed`/`windGust` are km/h → m/s; pressure is Pa → hPa (`seaLevelPressure`, else `barometricPressure`);
a wind direction of 0 with speed 0 is *calm* (direction null). RH is taken from the API, else derived from
T/Td; the dew point is derived from RH when absent. `presentWeather[].rawString` is parsed by §3.2 (as
`XXXX 010000Z <raw>` — a valid dummy time group); when a decoded entry has no raw string, an equivalent
group is synthesised from `weather` + `intensity` (`light → "−"`, `moderate → ""`, `heavy → "+"`) with the
mapping `rain/rain_showers→RA, drizzle→DZ, snow/snow_showers/snow_grains/ice_crystals→SN,
sleet/ice_pellets/hail/snow_pellets→PL, freezing_rain/freezing_drizzle→FZ+RA,
unknown_precipitation→RA; thunderstorms→thunder; fog_mist→BR, fog/freezing_fog→FG, haze→HZ, smoke→FU,
dust→DU, sand→SA, volcanic_ash→VA, squalls→SQ, funnel_cloud→FC, dust_whirls→PO, sandstorm→SS,
duststorm→DS`. If `precipitationLastHour > 0` while no present-weather group was reported (an ASOS between
showers), the type is `rain` above 1 °C and `snow` at or below it, with basis `measured`. `rawMessage`, when
present, is parsed as a METAR to recover the `4/sss` snow depth and an SLP if the API omitted the pressure.

*Forecast-anchored interpolation.* Because those stations report hourly, the observation is carried along
the NWS gridpoint forecast trend between reports:

```
value(now) = value(t_obs) + clamp(F(now) − F(t_obs), −L, +L)
```

`F` is the gridpoint layer for the same quantity from
`https://api.weather.gov/gridpoints/OKX/34,45` (the Central Park grid cell, from
`/points/40.7831,-73.9712`), refetched at most every `NWS_GRIDPOINT_TTL_S = 1800 s` and discarded after 6 h
without a refresh. Layers are sampled as step functions: each `validTime = start/duration` entry
contributes `(start, v)` and `(start + duration − 1, v)`, with linear interpolation between samples, and
`null` outside the covered range (then no correction is applied). Limits `L`: temperature 5 °C, dew point
5 °C, wind 5 m/s, gust 6 m/s, sky cover 0.40, RH 25 %, visibility 8000 m. Sky cover is scaled 0.01 and wind
km/h → m/s. The correction is applied only when the observation is older than
`BLEND_MIN_AGE_S = 600 s`; afterwards `dewpoint = min(dewpoint, temperature)` and RH is recomputed from the
adjusted pair. **Wind direction and precipitation are never interpolated.** The flag `interpolated` records
that this happened; the observation itself is never replaced.

**(2) Open-Meteo** — `https://api.open-meteo.com/v1/forecast?latitude=40.7831&longitude=-73.9712&current=…
&minutely_15=…&forecast_minutely_15=12&timezone=UTC&wind_speed_unit=ms`. `precipitation` and `snowfall` are
amounts *per interval*, so both are multiplied by `3600/interval` to get mm/h and cm/h. Visibility comes
from the `minutely_15` sample nearest the current time, accepted only within 15 min. WMO 4677 mapping:

| code(s) | type | intensity | thunder | obscuration |
|---|---|---|---|---|
| 0,1,2,3 | none | | no | — |
| 45,48 | none | | no | FG |
| 51 / 53 / 55 | drizzle | − / (mod) / + | no | — |
| 56 / 57 | freezing_rain | − / + | no | — |
| 61 / 63 / 65 | rain | − / (mod) / + | no | — |
| 66 / 67 | freezing_rain | − / + | no | — |
| 71 / 73 / 75 | snow | − / (mod) / + | no | — |
| 77 | snow | − | no | — |
| 80 / 81 / 82 | rain | − / (mod) / + | no | — |
| 85 / 86 | snow | − / + | no | — |
| 95 | rain | (mod) | **yes** | — |
| 96 / 99 | sleet | (mod) / + | **yes** | — |

If the code says dry but `precipitation > 0`, the type is taken from the model's own partition:
`rain + showers > 0` and `snowfall > 0` → `sleet`, `snowfall > 0` → `snow`, otherwise `rain`. The rate is
the measured amount when > 0 (basis `measured`), else the class representative of §3.3 (basis `class`).

**(3) METAR** — `https://aviationweather.gov/api/data/metar?ids=KLGA,KJFK,KNYC,KEWR&format=json` first
(stations tried in the order KNYC, KLGA, KJFK, KEWR; `obsTime` from the JSON is preferred over the parsed
time), then, station by station,
`https://tgftp.nws.noaa.gov/data/observations/metar/stations/{station}.TXT`.
**`api.aviationweather.gov` is blocked by this environment's egress policy; the host without the `api.`
prefix is the working endpoint** (see `docs/verification/live/REPORT.md`).

**(4) stale** — no provider answered: the last good observation is re-emitted with `source = "stale"`, a
fresh `fetched_at`, a recomputed `stale_age_s`, `interpolated = false`, and the snow model still stepped
(so lying snow keeps melting). With no history at all, every value is `null` and `precip_type = "none"` —
**never a synthetic value**.

### 3.5 Circuit breakers

One per provider, `CLOSED → OPEN → HALF_OPEN → CLOSED`:

* `record_failure`: `consecutive_failures += 1`; open when the count reaches
  `failure_threshold = 3`, **or** immediately if the state was `HALF_OPEN`;
* `allow(now)`: `false` while `OPEN` and `now − opened_at < open_seconds = 300`; at 300 s the state becomes
  `HALF_OPEN` and one probe is allowed;
* `record_success`: `CLOSED`, counter 0, last error cleared.

`status(now)` renders `"closed"`, `"half_open"` or `"open(<remaining>s)"`, and lands in
`weather.json:provider_status`. A provider raising *any* exception (not just `ProviderError`) counts as one
failure and never stops the loop.

### 3.5a Provider selection (ADR-011 and its proposed amendment)

Default (**ADR-011, unchanged**): the first provider whose breaker is closed and whose fetch succeeds wins;
the rest are not contacted. `WeatherService(prefer_freshest_age_s=S)` optionally relaxes that: when the
answer that arrived is older than `S` seconds, the remaining closed-breaker providers are queried as well
and the observation with the newest `observed_at` wins. It is **off by default** because enabling it
changes ADR-011; the measurement that motivates it is in `docs/verification/live/REPORT.md` (api.weather.gov
served KNYC's 10:51Z observation until at least 12:01Z while aviationweather.gov already had KNYC's 11:51Z
METAR). With the option off, behaviour is byte-identical to strict ordering.

### 3.6 Poll loop

`POLL_INTERVAL_S = 60`. Per-request timeouts: 10 s for NWS and METAR, **25 s for Open-Meteo**
(`OPEN_METEO_TIMEOUT_S` — the shared egress proxy here needs up to ~10 s to open a cold TLS session to
api.open-meteo.com, measured 0.3–30 s). Each poll: try providers in order, skipping open breakers; stamp `fetched_at` and
`stale_age_s = max(0, now − observed_at)`; step the snow model; write `weather.json` **atomically**
(temp file + `rename`), so a reader never sees a partial document. Floats in the JSON are rounded to
3 decimals. On start-up the previous `weather.json` is reloaded as the stale fallback.

### 3.7 Snow-depth model

Used when no station reports a `4/sss` group (NYC stations only emit it during snow events). Per update
with `Δt` hours capped at `MAX_STEP_H = 6`:

```
if snow_depth_source == "observed":  depth = observed;  source = "observed"
else:
    rate_cmph = snowfall_rate (Open-Meteo) if > 0
                else precip_rate_mmph · SLR(T, type)/10        for type in {snow, sleet}
    depth += rate_cmph · Δt
    depth -= 0.06 · max(0, T − 1 °C) · Δt                       [MELT_CM_PER_H_PER_C]
    depth -= 0.02 · rain_rate_mmph · Δt                         [RAIN_MELT_CM_PER_MM, liquid precipitation]
    depth *= max(0, 1 − 0.02·Δt/24)                             [SETTLE_PER_DAY = 2 %/day compaction]
    depth  = max(0, depth);  source = "model" if depth > 0 else "none"
```

Snow-to-liquid ratio `SLR` (Roebber et al. 2003 climatology bands): sleet 3; snow 8 for `T ≥ 0 °C`,
10 for `−5 ≤ T < 0`, 13 for `−10 ≤ T < −5`, 18 for `T < −10`; 8 when the temperature is unknown.
The melt coefficient 0.06 cm/h per °C is ≈ 4 mm SWE per °C·day at a snow density of 0.3.
State persists in `live/snow_state.json`.

---

## 4. World mapping (`worldmapping.py` → `core/weather/WorldMapping`)

Persistent state (`live/world_state.json`): `wetness`, `puddle_level`, `snow_cover`, `snow_cover_road`,
`updated_at_unix`. `Δt = clamp(now − last_update, 0, 6 h)`; the very first update only seeds the clock.
Integrators are the **exact** solutions, so results do not depend on the poll cadence:

```
lag(x, x*, Δt, τ) = x* + (x − x*)·exp(−Δt/τ)            (τ ≤ 0 ⇒ jump to x*; Δt ≤ 0 ⇒ unchanged)
```

### 4.1 Surface wetness (0 = dry, 1 = mirror-wet)

Target = max of three independent sources:

```
precipitation: w = 0.25 + 0.75·min(1, R/2.5)                       R = precip_rate_mmph  [WET_ONSET, WET_SATURATION_MMPH]
               snow/sleet:  0            if T ≤ 0 °C or T unknown
                            w · 0.5      otherwise                 [SNOW_WET_FRACTION]
fog:           0.15  if visibility < 1000 m and obscuration ∩ {FG, BR} ≠ ∅   [FOG_WETNESS]
dew:           0.10  if RH ≥ 97 %                                            [DEW_WETNESS]
```

Rise (`target > wetness`): `τ = max(30, 240/(1 + R/2))` s. Dry-out otherwise:

```
E   = 2 · deficit · (1 + u/3) · 2^((T − 20)/10) · (1 + 1.5·S)
τ   = clamp(5400/E, 300, 86400) s,  ×4 when T < 0 °C            [FREEZE_DRY_FACTOR]
deficit = max(0.02, 1 − RH/100)   (0.5 when RH is unknown)
u = wind m/s (0 if unknown),  T = 20 °C if unknown
S = max(0, sin(solar elevation))·(1 − 0.7·cloud_cover)          [0 at night, 0 when the Sun is unknown]
```

The factor 2 normalises the reference state (20 °C, RH 50 %, calm, dark) to exactly
`TAU_DRY_BASE_S = 5400 s`. Physical basis: bulk-aerodynamic evaporation ∝ moisture deficit × transfer
coefficient (linear in wind) × saturation vapour pressure (Clausius–Clapeyron ⇒ ×2 per 10 K over 0–30 °C)
× available energy.

`road_ice = (T ≤ 0 °C) and (wetness > 0.2)`.

### 4.2 Puddles

Linear reservoir over `PUDDLE_FULL_MM = 8 mm` of accumulated excess, with `DRAIN_MMPH = 1.5` for the NYC
catch-basin + infiltration capacity:

```
R_liquid = precip_rate_mmph  for rain/drizzle/freezing_rain,  plus the same for snow/sleet when T > 1 °C
if wetness ≥ 0.85 and R_liquid > 1.5:      P += (R_liquid − 1.5)·Δt_h / 8
else:                                      P -= 1.5·Δt_h/8 + P·(1 − exp(−Δt/(τ_dry/0.35)))
P = clamp(P, 0, 1);   puddle_depth_mm = 8·P
```

The second term is evaporation at 35 % of the film's rate (`PUDDLE_EVAP_FACTOR`, a puddle holds much more
water than the film).

### 4.3 Snow cover

`SNOW_FULL_COVER_CM = 2.0` (pavement texture fully hidden). Per update, in cover units:

```
accretion = snowfall_rate_cmph·Δt_h / 2.0
melt      = 0.06·max(0, T − 1)·Δt_h / 2.0  +  0.02·rain_rate_mmph·Δt_h / 2.0
supported = clamp(snow_depth_cm / 2.0, 0, 1)                    (the depth model of §3.7 is authoritative)

snow_cover      = supported                                              if snow_depth_source == "observed"
                = min(clamp(snow_cover + accretion − melt, 0, 1), supported)  otherwise
clear           = 0.15 + (0.60 if plow_active) + (0.25 if salt_active)   per hour
snow_cover_road = clamp(snow_cover_road + accretion − melt − clear·Δt_h, 0, snow_cover)
```

With both plows and spreaders out the three clearing terms sum to 1.0/h — a fully covered carriageway is
bare one hour into a full response (DSNY's arterial clearance target). The same rate is applied to every
street class: the model has no per-street plow routing.

**DSNY dispatch flags** (`plow_and_salt(depth_cm, T, precip_type)`), `T` treated as 0 when unknown:

```
frozen = precip_type ∈ {snow, sleet, freezing_rain}
salt   = (T ≤ 1 °C and (frozen or depth > 0))  or  precip_type == freezing_rain
plow   = depth ≥ 5.08 cm (2.00 in)  and  (T ≤ 1 °C or frozen)
```

### 4.4 Fog and visibility

Koschmieder with a 2 % contrast threshold: the extinction coefficient the engine's exponential height fog
needs is `β = 3.912 / V` per metre (0 when `V` is unknown or ≤ 0).

```
density(V) = 0                                     V ≥ 10000 m      [FOG_VIS_CLEAR_M]
           = 1                                     V ≤ 50 m         [FOG_VIS_DENSE_M]
           = ln(10000/V) / ln(10000/50)            otherwise        (0.5 at 707 m)
```

The density is attributed to **dry aerosol** (`haze_density`) only when an aerosol group
(`HZ FU DU SA VA PY`) is reported *and* no droplet group (`FG`, `BR`) and RH < 95 %; otherwise it is
`fog_density` — which therefore also covers heavy precipitation reported without any obscuration group.

### 4.5 Wind vector

From the meteorological "from" heading θ (compass), the air moves towards θ + 180:

```
east  = −sin θ · U      north = −cos θ · U      up = 0
UE    = (east, −north, 0)
```

Both vectors are `[0,0,0]` when the speed or the direction is unknown (calm or variable wind).

### 4.6 Umbrella probability

Fraction of pedestrians carrying an open umbrella:

```
p = 0.85 · f(type) · (1 − exp(−R/0.8))      R = precip_rate_mmph, 0 when R ≤ 0 or f = 0
f: rain 1.0, freezing_rain 0.9, drizzle 0.7, sleet 0.6, snow 0.35, none 0.0
wind: ×1                                                for u ≤ 8 m/s
      ×max(0.10, 1 − (u − 8)/9 · 0.9)                   for u > 8 m/s   (umbrellas invert and are abandoned)
p = clamp(p, 0, 0.85)
```

### 4.7 Window condensation

Steady-state pane surface temperatures with ISO 6946 surface resistances
(`R_si = 0.13`, `R_se = 0.04` m²K/W) and glazing resistance 0.004 (4 mm single glass, `R_tot = 0.174`,
U = 5.75 W/m²K) or 0.19 (sealed double unit, `R_tot = 0.360`, U = 2.78 W/m²K):

```
T_si = T_in  − (R_si/R_tot)·(T_in − T_out)          T_in = 21 °C, RH_in = 40 %  ⇒ Td_in = 6.90 °C
interior = clamp((Td_in − T_si)/3.0, 0, 1)                                   [CONDENSATION_FULL_C]

if T_out > 26 °C:                                   T_in,cooled = 23 °C
    T_so = T_out − (R_se/R_tot)·(T_out − T_in,cooled)
    exterior = clamp((Td_out − T_so)/3.0, 0, 1)
else exterior = 0
```

Both glazing types are reported: `window_condensation_interior/_exterior` are the single-glazed values (the
visible city-wide effect in NYC's pre-war stock), `window_condensation_double` the sealed-unit value,
`window_condensation = max(interior, exterior)`. With T and Td unknown both are 0.

### 4.8 Missing data

`missing[]` lists which of `temp_c, dewpoint_c, rh, wind_mps, wind_dir_deg, cloud_cover, visibility_m` were
`null` in the observation that drove the update. The derived value then uses the documented neutral value
(dry, calm, clear, no fog) — it is never fabricated, and the consumer can see exactly why.

---

## 5. Empire State Building tower lights (`esb_lights.py`)

Sources: `https://www.esbnyc.com/about/tower-lights` (the three-day block: yesterday / today / tomorrow,
`div.three-days-lights-wrapper`, the current day marked `is-today`, `h2` carrying `Today, <Month> <d>, <yyyy>`,
`h3` the colour text, `.field_description` the reason, `.field_hours` the hours) and
`https://www.esbnyc.com/about/tower-lights/calendar/<yyyymm>` (`article.lse[data-date=YYYY-MM-DD]` inside
`.lights-calendar-view`). Both are parsed with a stdlib `HTMLParser` tree — no third-party dependency. A
markup change raises `ESBParseError` rather than returning something wrong.

Colour text is split on `,`, `/`, `&`, `+`, `and`, `with`, the words *colors/colours/lights* stripped, then each
name is title-cased and mapped to RGB by exact match, else by its last word (`"Giants Blue"` → blue).
`Rainbow`/`Pride` expands to the six-colour sequence red (230,20,20), orange (255,110,0), yellow (255,230,0),
green (0,200,60), blue (0,70,255), purple (140,30,220). A name with no mapping is **not guessed**: it is
listed in `unknown_colors`; if *nothing* resolved, the record still lights with signature white
(255,228,206) so the tower is never dark, and the published names remain in `colors`.

Resolution order for a date: the three-day block, then the month calendar (a disagreement is logged and the
three-day block wins). If both pages parse and neither lists the date, that is **not** a failure — it means
the standard schedule, i.e. Signature White, `fallback = true`. If a page fetch or parse fails and no cached
entry exists for the date, signature white is used with the error in `reason`. Refreshed at most hourly
(`refresh_s = 3600`), and always refreshed while the current record is a fallback.

## 6. Tides and currents (`tides.py`)

NOAA CO-OPS, `application=NYCSim`, `units=metric`, `time_zone=gmt`, `format=json`.

* Water level: `datagetter?product=water_level&date=latest&datum=MLLW&station=8518750` (The Battery), every
  poll; rejected when older than `MAX_WATER_LEVEL_AGE_S = 7200 s` (then the snapshot is `stale`).
* Datums: `mdapi/prod/webapi/stations/8518750/datums.json`, at most daily.
  `navd88_minus_mllw_m = NAVD88 − MLLW`; when unavailable the published Battery value **0.846 m**
  (epoch 1983–2001) is used and the failure is listed in `errors`. World vertical datum is NAVD88, so
  `water_level_m = level_MLLW − navd88_minus_mllw_m`.
* High/low predictions: `product=predictions&interval=hilo&datum=MLLW`, cached per UTC day; the next four
  are published in `next_tides`.
* Currents: `product=currents_predictions&interval=30` for `NYH1924` Hell Gate (East River, primary),
  `NYH1920` Brooklyn Bridge (East River), `NYH1927` Hudson River entrance and `n03020` The Narrows, cached
  per UTC day. `Velocity_Major` is cm/s along the principal axis, **positive = flood**. The value at the
  poll instant is linearly interpolated between predictions (`null` outside the predicted span);
  `speed = |v|/100` m/s, `phase = slack` for `|v| < 5 cm/s`, else `flood`/`ebb`, and the compass heading is
  the station's own `meanFloodDir` / `meanEbbDir`.

Each failure is recorded in `errors[]` and sets `stale`; nothing is invented.

## 7. Debug overlay (`debug_overlay.py`)

Fixed section order: `TIME`, `SUN (NREL SPA)`, `MOON (Meeus 47/48)`, `WEATHER`, `WORLD MAPPING`,
`PROVIDERS`, `ESB TOWER LIGHTS`, `TIDES / CURRENTS`, closed by a full-width `=` rule. Headers are
`"== <TITLE> "` left-padded with `=` to `WIDTH = 62`. Every field line is
`<mark><label padded to LABEL_W = 22>": "<value>`, where `mark` is `!` for stale weather, an open breaker or
a stale tide snapshot, and a space otherwise. A missing value renders as `—` (U+2014) — never `0`. Durations
render as `1h 04m 09s` / `4m 09s` / `9s`. The header line of the weather block carries the provider name,
the observation age, and `** STALE **` when the source is `stale` or the age exceeds
`MAX_OBSERVATION_AGE_S` (9000 s — a smaller limit would flag KNYC every hour, since a station reporting
hourly at :51 legitimately serves a 59-minute-old observation). Compass points use the 16-point rose with
22.5° sectors. Written atomically to `live/overlay.txt`.

## 8. CLI

```
python -m nycsim_live [--once] [--polls N] [--interval S] [--print-overlay] [--record]
python -m nycsim_live manhattanhenge YEAR [--out FILE]
python -m nycsim_live spa-check          # prints the NREL SPA reference case with pass/fail per quantity
python -m nycsim_live overlay            # re-renders the overlay from the snapshots on disk
python -m nycsim_live.grid_azimuth [--gdb PATH] [--json OUT]   # LION grid-azimuth derivation (§2.5)
```

Each subsystem fails independently: an outage degrades that snapshot to its documented stale/fallback state
and never stops the loop.
