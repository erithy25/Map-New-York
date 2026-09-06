# Terrain & Water — stage report

**Stage:** terrain & coastline (ARCHITECTURE §5) and water (DATA_CONTRACTS §4).
**Contracts produced:** §2 `tiles/index.parquet` (terrain columns), §3 `tiles/{tile}/terrain.png` +
`terrain.json`, §4 `water/hydrography.parquet`, `water/shoreline.parquet`, `water/structures.parquet`,
`water/water_tiles.parquet`.
**Run date:** 2026-09-06. Every number below is quoted from an artefact on disk; the command that
produced it is named next to it.

---

## 1. What was built

| File | Role |
|---|---|
| `terrain/grid.py` | global 2 m lattice, tile transforms, 16-bit encoding (unchanged) |
| `terrain/sources_3dep.py`, `terrain/ingest.py` | TNM product discovery + warp to the lattice (unchanged) |
| `terrain/compose.py` | priority composition 1 m > 1/9" > 1/3" (open-dataset cap raised to 160) |
| `terrain/coverage.py` | **new** — scope/borough coverage audit → `terrain/coverage.json` |
| `terrain/points.py` | **new** — survey-point cache + global point-vs-DEM accuracy audit |
| `terrain/hydro.py` | **new** — per-tile water / pier deck / seawall / shoreline rasters |
| `terrain/tiles.py` | **new** — the tile pass: compose → densify → hydro-flatten → sub-datum repair → PNG |
| `terrain/index.py` | **new** — `tiles/index.parquet` written under `flock` |
| `terrain/segment_z.py` | **new** — cached `sample_z(x, y)` / `segment_z(line)` for the other stages |
| `terrain/verify.py` | **new** — extremes, voids, seams, known elevations, water datum, overview, hillshades |
| `terrain/build.py` | **new** — stage driver (`python -m nycsim_pipeline terrain`) |
| `terrain/manifest_safe.py` | **new** — locked, retrying wrapper around the shared manifest |
| `water/names.py` | **new** — a real name for every water body |
| `water/build.py` | tidal classification corrected, DEM sampling bounded, plain-string columns |
| `water/classify.py` | `clean_name` now drops NaN placeholders |
| `pipeline/tests/test_terrain.py` | **new** — 39 tests |

Data on disk: `terrain/coverage.json`, `terrain/ground_points.parquet` (1,458,592 rows),
`terrain/point_audit.json`, `terrain/tile_summary.json`, `terrain/overview_16m.tif`,
`tiles/{tile}/terrain.png` + `terrain.json` (2,916 × 2 files, 525 MB), `tiles/index.parquet`,
`water/*.parquet`, `water/water_summary.json`, and this directory's verification products.

## 2. Sources and licences

| Source | Product used | Licence |
|---|---|---|
| USGS 3DEP **1 m** DEM, project `NY_CMPG_2013` — 21 tiles, 3.24 GB raw | bare-earth LiDAR DEM, UTM 18N NAD83, metres NAVD88 | USGS, public domain |
| USGS NED **1/9"** — 7 products, 0.57 GB (NJ, Nassau) | LiDAR DEM | USGS, public domain |
| USGS 3DEP **1/3"** `n41w074`, `n41w075` — 0.67 GB | seamless 10 m DEM | USGS, public domain |
| NYC planimetric Elevation points (`szwg-xci6`) | feature code 3000 / sub code 300000 (ground spot elevations, ft) | NYC Open Data terms |
| NYC Building Footprints (`5zhs-2jue`) via `buildings/footprints_raw.parquet` | `cx, cy, ground_z` — LiDAR ground per footprint | NYC Open Data terms |
| NYC planimetric Hydrography (`pjs3-c3z5`), Hydro Structures (`6hbv-tek4`), Shoreline (`59xk-wagz`) | water polygons, piers/jetties/seawalls with surveyed deck elevation, shoreline lines | NYC Open Data terms |
| NYC Borough Boundaries (land, and with-water) | borough masks, NY/NJ state line | NYC Open Data terms |
| OpenStreetMap BBBike New York extract | coastline-derived sea outside the city line, water names | ODbL 1.0, © OpenStreetMap contributors |
| `CityOfNewYork/nyc-planimetrics` Capture_Rules.md (via jsDelivr) | authoritative feature-code semantics quoted below | NYC Open Data / MIT repo |

Downloads are recorded with URL + SHA-256 in `data/manifest/downloads.json`; processed artefacts in
`data/manifest/processed.json`.

## 3. Method

**Source grid.** Every DEM is warped once onto the global 2 m NYC_TM lattice (sample centres at even
metre coordinates); finer-than-2 m sources are box-averaged, coarser ones bilinear. `compose.DemStack`
then fills any window from the best source per sample — 1 m LiDAR > 1/9" > 1/3" — as a pure pixel copy,
so a sample has one value no matter which tile asks for it.

**Densification (ARCHITECTURE §5).** `points.py` caches the real survey points in one globally sorted
array: planimetric **spot elevations** (feature code 3000 / sub code 300000 — points on the centre of
every roadbed and on interior sidewalks, at intersections and every 200 ft along a block) and the
**building ground elevations** of all 1.08 M footprints. The planimetric *bridge* subtype (300020) and
the *building* elevation code (3020, a roof height) are excluded — both would lift the ground surface.
For each point, `dz = z_point − z_dem` at its nearest lattice sample; `|dz| ≥ 3 m` is rejected as an
outlier and counted. Accepted corrections are spread by inverse distance with a Franke–Little taper
`w = ((R−d)/(R·d))²` (R = 15 m) and blended into the DEM by `alpha = min(1, Σ (1 − d/R)²)` — alpha is 1
at a survey point (the surface passes exactly through it) and 0 at 15 m from every point, so there is no
step at the search radius.

**Hydro-flattening.** Everything tidal is flattened to **0.0 m NAVD88**; a non-tidal body is flattened to
its own real level (the surveyed planimetric water-elevation point where one exists, else the DEM median
where the pool is flat, else it keeps the DEM). Marshes are never flattened. Pier and jetty decks
(2800/2810) replace the water plane with their surveyed deck elevation; seawalls (2820) raise samples the
water mask would otherwise flood. The planimetric shoreline is burned as a hard edge: a shoreline sample
standing 0.1–6 m above the water plane keeps its ground elevation, so the land/water transition is exactly
one 2 m sample wide instead of a ramp.

**Encoding.** Elevations are quantised to a global 2.5 mm grid, cropped to 501 × 501 (inclusive edges) and
written as a 16-bit grayscale PNG, north row first, with `terrain.json` giving `z_min_m` and
`z_scale_m = 0.0025`. The encoder refuses a tile that would need a coarser quantum, because tiles encoded
at different quanta could not share bit-identical edges.

**Determinism.** Each sample depends only on data within 15 m of it, the tile window is padded by 32 m,
and point contributions are summed in ascending *global* point order, so two tiles sharing an edge compute
it from the same numbers in the same order. Verified below: 0 seam violations over 5,724 tile pairs.

---

## 4. Coverage of the source grid

`python -m nycsim_pipeline.terrain.coverage` → `data/processed/terrain/coverage.json` (2,916 tiles,
284 s). Land masks from the borough boundaries (land-only file); "water" from the water stage's
open-water union.

| Borough | Land in scope | DEM coverage | from 1 m LiDAR | from 1/3" | Land voids |
|---|---|---|---|---|---|
| Manhattan | 59.38 km² | **100.000 %** | 100.000 % | 0 % | 0 |
| Bronx | 110.74 km² | **100.000 %** | 99.975 % | 0.025 % | 0 |
| Brooklyn | 180.44 km² | **100.000 %** | 99.9999 % | 0.0001 % | 0 |
| Queens | 283.68 km² | **100.000 %** | 100.000 % | 0 % | 0 |
| Staten Island | 151.44 km² | **100.000 %** | 100.000 % | 0 % | 0 |

Scope totals: 731,918,916 samples, 695,853,080 with a DEM value. The 36,065,836 void samples are
36,063,946 inside water polygons and **1,890 outside them** — all of them in the open Atlantic at the
south-east corner of the scope box (tiles `t_5_-23` … `t_8_-21`, beyond the last 3DEP tile), i.e. no land
gap anywhere. Nothing had to be re-fetched: the 1 m mosaic already covers all five boroughs, the 1/9"
products cover the New Jersey and Nassau strips, and the two 1/3" tiles cover the remainder.
130 tiles had no DEM sample at all and 27 were partially covered — every one of them open ocean.

**Consequence for ADR-005:** the DEM is 3DEP **1 m** (project `NY_CMPG_2013`, the same 2013–14 post-Sandy
LiDAR that produced the NYC 1-ft DEM and the 2014 CityGML model) over 100 % of the five boroughs, not the
1/9" (≈3.4 m) product the ADR assumed. I propose **ADR-005a**: "Terrain base is 3DEP 1 m where it exists
(the whole city), 1/9" for New Jersey/Nassau, 1/3" elsewhere in the scope box; the working grid stays
2 m." The gap versus the 26.6 GB NYC 1-ft DEM is unchanged and still stated in ARCHITECTURE §0.

## 5. Densification and the accuracy statement

`python -m nycsim_pipeline.terrain.points --audit` → `data/processed/terrain/point_audit.json` (30.9 s).
Every one of the 1,458,592 survey points was compared with the composed 3DEP surface at its nearest
lattice sample; each point is counted exactly once (unlike the per-tile counters, whose padded windows
overlap).

| Point set | n | median dz | p05 … p95 | RMS | RMS after outlier rejection | rejected \|dz\| ≥ 3 m |
|---|---|---|---|---|---|---|
| Planimetric spot elevations | 376,133 | −0.106 m | −0.506 … +0.278 m | 2.385 m | **0.291 m** | 5,888 (1.57 %) |
| Building LiDAR ground | 1,082,459 | −0.015 m | −0.745 … +0.488 m | 0.735 m | **0.411 m** | 1,720 (0.16 %) |
| All | 1,458,592 | −0.037 m | −0.691 … +0.411 m | 1.367 m | **0.384 m** | **7,608 (0.52 %)** |

Reading: before densification the 1 m LiDAR surface already agrees with survey-grade ground points to
**0.38 m RMS** with a −0.04 m median bias; after densification the published surface passes through every
accepted point exactly and relaxes back to the LiDAR surface within 15 m. The 7,608 rejected points are
the outliers the brief asked to be counted — they sit on bridge decks and viaduct approaches that the
sub-code filter did not catch, on retaining walls and areaways, and on the ~1,700 footprints whose LiDAR
"ground" fell on a roof or a neighbouring structure. No point was rejected for lack of a DEM value
(`no_dem = 0`).

## 6. Water (DATA_CONTRACTS §4)

`python -m nycsim_pipeline.water.build` → `data/processed/water/` and `water_summary.json`.

* `hydrography.parquet` — **2,235 polygons, 1,226.6 km²**. Kinds: pond 992, marsh 744, river 281,
  bay 129, lake 61, basin 20, ocean 6, canal 2. **481 bodies (1,209.8 km²) are tidal and sit at
  0.000 m NAVD88**; 946 have a constant non-tidal level and 808 (744 of them marsh) follow the DEM.
  Level provenance: 878 from surveyed planimetric water-elevation points, 469 tidal by connectivity to
  the harbour, 12 tidal by name, 68 from the DEM median, 64 left sloped, 744 marsh.
* `shoreline.parquet` — 413 parts, **809.0 km**: bulkhead 214, natural 181, pier 18. 72 parts classified
  from the structure layer, 252 from the DEM slope (26,300 probe points), 89 as marsh edge.
* `structures.parquet` — 2,536 polygons: 1,332 piers, 1,018 seawalls, 186 jetties, each with its
  surveyed deck elevation (`deck_z_m`); 24 "piers" whose deck is above 15 m are bridge decks and are
  excluded from the terrain (counted, not silently dropped).
* `water_tiles.parquet` — one row per scope tile (2,916), 1,752 with open water.

**Names.** 180 distinct real names over 332 polygons covering 873.5 km²: 135 from the planimetric `name` field, 97 adopted
from an OpenStreetMap water polygon that covers a planimetric polygon (this is what supplies the Central
Park bodies and the New Jersey ones), and 100 pieces of the coastline-derived sea named by nearest named
body (flagged `name_source = 'nearest_named_body'`, never presented as surveyed). Every body the brief
named is present and tidal at 0.0 m: Hudson River (68.5 km²), East River (58.3), Harlem River (2.3),
Upper New York Bay (52.6), Lower New York Bay (85.3), Jamaica Bay (20.5), Newtown Creek (0.44),
Gowanus Canal (0.09), Bronx River (0.44), Kill Van Kull (7.5), Arthur Kill (30.6), Long Island Sound
(87.8), Atlantic Ocean (158.5), plus Raritan Bay, Newark Bay, Rockaway Inlet, The Narrows, Buttermilk
Channel, Flushing Bay, Gravesend Bay, Eastchester Bay, Little Neck Bay, Great Kills Harbor and others.
Central Park's water is named and **not** flattened to sea level: the Jacqueline Kennedy Onassis
Reservoir stands at **34.52 m**, The Lake at 16.55 m, Harlem Meer at 3.56 m — all from surveyed
planimetric water-elevation points.

**Two corrections made here** (both were silently wrong before and are the reason the water stage was
re-run): the tidal test used to require the DEM median inside a body to be within ±1 m of zero, but the
2013 1 m LiDAR reports a *nominal water surface near −1.6 m*, so the Hudson, the East River and most of
the harbour failed the test and were left following that −1.6 m artefact. Tidal status is now decided by
connectivity to the harbour (25 m), vetoed only where the DEM p10 or a surveyed pool puts the body clearly
above the datum, and propagated across the pieces of a named body. Second, `clean_name` treated a missing
name read back as the string `"nan"`, which left 361 polygons "named" nan.

## 7. Tiles and the tile index

`python -m nycsim_pipeline.terrain.tiles --workers 2` → **2,916 tiles written, 0 failed**, 1,817 s wall
(2 workers, `nice -n 10`, peak RSS 0.72 GB per worker; the box was carrying 5 other agents at load
average ≈ 33, so this is ~10 CPU-minutes of real work). `data/processed/terrain/tile_summary.json`.

* Every tile in the scope grid has `terrain.png` (16-bit, 501 × 501, 2 m, inclusive edges, north row
  first) and `terrain.json` — **including the 622 tiles that are pure water**. Total PNG payload 525 MB.
* Sample provenance over the whole scope: 253,630,295 from 1 m LiDAR, 226,144,629 from 1/9",
  216,078,156 from 1/3", 249,356,124 flattened to a water surface, 330,322 pier/jetty deck,
  107,548 shoreline hard edge, 1,384 seawall crest, 4,341 filled from the tidal datum (open Atlantic
  beyond the last 3DEP tile).
* Sub-datum repair (samples the LiDAR put below the land floor, mostly its nominal water return):
  16,243 samples in 42 tiles — 1,454 kept because a survey point corroborates them, 1,024 resolved to the
  water plane, 13,765 filled from the neighbouring surface. The deepest raw source value was −26.97 m
  (`t_-5_6`, the Hudson Line portal).
* `tiles/index.parquet`: 2,916 rows, `has_terrain` true for all, 2,294 with land, 1,743 with water,
  `z_min`/`z_max` per tile, content counts left at 0 for the buildings/roads/furniture stages (the writer
  never overwrites a non-zero count another stage has already put there and carries unknown columns
  across). Written under `data/processed/tiles/index.parquet.lock` (`fcntl.flock`) because agents run
  concurrently. `borough_codes` per tile: water 1,743, Manhattan 105, Bronx 162, Brooklyn 243,
  Queens 372, Staten Island 192, New Jersey 1,022, and **7 = New York State outside NYC** 362 — code 7 is
  an appended extension to the §2 enumeration (Nassau County and lower Westchester are clipped by the
  scope box and are neither a borough nor New Jersey); the enumeration is stored in the parquet metadata
  key `nycsim.borough_codes`.

## 8. `segment_z.sample_z` — the elevation service for the other stages

`pipeline/nycsim_pipeline/terrain/segment_z.py` reads the **published** tiles (not the intermediates), so
a consumer gets exactly the surface the engine will load. It decodes a tile once and keeps it in an LRU
cache (one tile = 501 × 501 float32 = 1.0 MB; 64 tiles by default), and interpolates bilinearly on the
2 m lattice. Scalars or numpy arrays; `missing="raise" | "nan" | "nearest"` decides what happens outside
the built area.

```python
from nycsim_pipeline.terrain.segment_z import sample_z, segment_z
z  = sample_z(-3015.0, 5375.4)      # 15.15 m — Fifth Avenue at 34th Street
zs = sample_z(xs, ys)               # vectorised
zs = segment_z(linestring)          # elevation per vertex, what the roads stage needs
```

Continuity across a seam is exact: `sample_z` 1 mm either side of a tile boundary returns the same value
(test `test_sample_z_matches_the_stored_grid_and_is_continuous_across_a_seam`).

## 9. Verification

`python -m nycsim_pipeline.terrain.verify` → `docs/verification/terrain/verification.json` plus the
rendered products in this directory.

**9.1 Known elevations** (sampled through `sample_z`; the check passes when the published figure
intersects the terrain's range over the probe radius).

| Place | probe | terrain range over radius | published | |
|---|---|---|---|---|
| Todt Hill summit, Staten Island | 125.59 m | 116.34 – 125.59 m (60 m) | 409.8 ft = 124.9 m | **OK** |
| Battery Park, Manhattan | 2.52 m | 1.57 – 3.18 m (40 m) | 2–3 m | **OK** |
| Fort Tryon Park, Linden Terrace | 77.32 m | 59.30 – 77.32 m (60 m) | ~250 ft = 76.2 m | **OK** |
| Bennett Park (Manhattan high point) | 81.07 m | 75.50 – 81.07 m (60 m) | 265 ft = 80.8 m | **OK** |
| Brooklyn Heights Promenade | 17.05 m | 3.71 – 17.71 m (30 m) | ~50–65 ft above the river | **OK** |
| Flushing Meadows Corona Park | 1.53 m | 0.59 – 3.70 m (120 m) | 3–5 m (marsh fill) | **OK** |
| Central Park reservoir pool | 34.52 m | 34.52 – 34.52 m (100 m) | surveyed pool | **OK** |
| Coney Island beach | 2.99 m | 0.00 – 3.95 m (50 m) | ocean beach | **OK** |

**Todt Hill is the maximum of Staten Island and of the whole city.** Per-borough extremes read back from
`tiles/index.parquet` + the per-tile `z_max`:

| Borough | min | max | max tile |
|---|---|---|---|
| Manhattan | −5.18 m | **81.09 m** (Bennett Park; published 80.8 m) | `t_0_16` |
| Bronx | −1.93 m | 89.39 m (Riverdale ridge) | `t_6_22` |
| Brooklyn | −4.00 m | 71.40 m (Green-Wood / Ocean Hill ridge) | `t_5_-2` |
| Queens | −3.29 m | 80.64 m (Forest Park ridge) | `t_19_6` |
| Staten Island | −2.00 m | **125.59 m** (Todt Hill; published 124.9 m) | `t_-14_-12` |
| New Jersey (in scope) | −2.00 m | 210.28 m (Watchung ridge, `t_-26_15`) | — |
| NY State outside NYC | −2.00 m | 99.50 m | `t_6_26` |

**9.2 No NaN / no void.** All 2,916 tiles present, all decode to finite elevations, 731,918,916 samples,
0 non-finite, 0 missing tiles. The only synthetic samples in the whole city are the 4,341 open-Atlantic
samples set to the tidal datum at the scope's south-east corner (0.0006 % of the scope).

**9.3 Tile-seam continuity.** 5,724 adjacent tile pairs compared on their shared edge row/column:
**maximum difference 2.8 × 10⁻¹⁴ m** (float64 decode noise), 0 violations against the 1 mm tolerance.

**9.4 Water datum.** 358 random points inside tidal bodies: **357 decode to exactly 0.000 m**; the
remaining one is 0.167 m — a sample that falls on the shoreline hard edge.

**9.5 Rendered products** (this directory):

| File | What |
|---|---|
| `hillshade_city.png` | whole scope, 20 m cells, 2,700 × 2,700, azimuth 315° / altitude 45° |
| `relief_city.png` | same with a hypsometric tint |
| `hillshade_manhattan.png` | Manhattan window (−8/−4 km to +3/+18 km), 4 m cells, 2,750 × 5,500 |
| `relief_manhattan.png` | same with a hypsometric tint |
| `verification.json` | every number quoted above |
| `data/processed/terrain/overview_16m.tif` | the whole scope at 16 m, a strict decimation of the tiles (3,376 × 3,375, no voids) |

**9.6 Tests.** `python -m pytest pipeline/tests/test_terrain.py -q` → **39 passed**. They cover the
lattice algebra and inclusive edges, the 16-bit encoding round-trip, the IDW taper and the outlier
rejection, the water classification and name cleaning, the index merge and its lock, borough coverage,
the per-tile contract fields, seam identity, `sample_z` against the stored grid, the hydrography contract
and the named bodies, tidal levels vs reservoirs, shoreline/structure kinds, the extremes envelope, the
sub-datum accounting and the overview decimation.

The city relief shows Manhattan, the Hudson and East Rivers, the Palisades and Watchung ridges on the New
Jersey side, the Bronx ridges, the Harlem River, Newtown Creek, the Gowanus and Erie Basin, Jamaica Bay
with its marsh islands, the Rockaway barrier, Coney Island and the Staten Island spine — read as a map,
it is New York. The Manhattan hillshade (bare earth, no buildings, which is what a DTM must look like)
shows the Palisades cliff line, the Washington Heights / Inwood ridges, the Central Park depression, the
Harlem valley at 125th Street and every finger pier along both waterfronts.

## 10. Timings and resources (this container, 4 vCPU shared with 5 other agents)

| Step | Command | Wall time | Peak RSS |
|---|---|---|---|
| Coverage audit | `terrain.coverage` | 284 s | 0.4 GB |
| Ground-point cache | `terrain.points` | 25 s | 0.6 GB |
| Point-vs-DEM audit | `terrain.points --audit` | 31 s | 0.6 GB |
| Water (geometry + names + levels + shoreline) | `water.build` | ~230 s | 1.4 GB |
| **Tile pass, 2,916 tiles** | `terrain.tiles --workers 2` | **1,817 s** | 0.72 GB per worker |
| Tile index | `terrain.index` | 20 s | 0.5 GB |
| Verification + hillshades + overview | `terrain.verify` | 320 s | 1.3 GB |
| Tests | `pytest pipeline/tests/test_terrain.py` | 11 s | — |

Everything ran at `nice -n 10` with at most two worker processes, well inside the 5 GB RAM budget. The
tile pass is ~10 CPU-minutes of real work; it took 30 minutes of wall clock because the machine was at
load average ≈ 33. Disk: 1.7 GB of lattice-aligned DEM intermediates, 525 MB of tile PNGs, 20 MB overview,
28 MB of verification renders.

## 11. Fidelity achieved vs. target, and the gaps

| Target (brief / ARCHITECTURE §5) | Achieved | Evidence |
|---|---|---|
| Terrain over all five boroughs | 100.00 % of every borough, all of it from 1 m LiDAR | §4 |
| Horizontal resolution 2 m | 2 m lattice, 501 × 501 per km tile, inclusive edges | §3, §7 |
| Vertical accuracy ≈ 0.15 m | **0.38 m RMS** agreement between the 1 m LiDAR surface and 1.46 M survey points before densification; the published surface passes exactly through the accepted points | §5 |
| Densify with spot elevations + 1.08 M building grounds within 15 m, reject \|Δz\| ≥ 3 m | done; 7,608 outliers rejected (0.52 %), counted by source | §5 |
| Hydro-flatten to 0.0 m NAVD88 | 481 tidal bodies, 1,209.8 km², all at exactly 0.000 m | §6, §9.4 |
| Shoreline as a hard edge | 107,548 shoreline samples keep their ground elevation against the water plane | §7 |
| Pier / bulkhead decks | 330,322 deck samples from 1,518 surveyed pier/jetty polygons; 1,384 seawall crest samples | §7 |
| A tile for every tile in scope incl. water-only | 2,916 / 2,916 | §7 |
| `tiles/index.parquet` per §2, counts left to other stages, lock | done | §7 |
| `sample_z` for other stages | `terrain/segment_z.py`, cached, seam-continuous | §8 |
| Named water bodies | 180 distinct real names; every body the brief listed | §6 |
| Zero NaN / void | 0 non-finite samples; 4,341 synthetic samples in the open Atlantic | §9.2 |
| Seam continuity within 1 mm | max 2.8 × 10⁻¹⁴ m over 5,724 pairs | §9.3 |

**Gaps, stated plainly.**

1. **Vertical accuracy is 0.38 m RMS against survey points, not 0.15 m.** ARCHITECTURE §5 estimated
   ≈ 0.15 m. The measured spread is dominated by the *time difference* between the sources (2013–14 LiDAR
   vs 2022 planimetrics) and by real change (regrading, new construction), not by noise: the median offset
   is −0.04 m and the interquartile spread is well under 0.5 m. Where a survey point exists the published
   surface is exact; between points, on a 1 m LiDAR base, the surface is the LiDAR surface.
2. **1,890 samples of the scope box (0.0003 %) had no elevation source at all** — open Atlantic beyond
   the last 3DEP tile at the south-east corner — and 4,341 published samples were set to the tidal datum
   there. No land sample anywhere is synthetic.
3. **The outer sea is only partly named.** 332 polygons carrying 873.5 km² have a real name; the
   remaining 1,903 polygons (353.1 km²) do not — 340.0 km² of coastline-derived sea more than 5 km from
   any named body, plus 736 unnamed marshes (11.8 km²) and 928 unnamed ponds (1.3 km²) that the
   planimetric database itself does not name. Names were never invented: `name_source` says exactly where
   each one came from (`planimetric` 135, `osm` 97, `nearest_named_body` 100).
4. **`marsh` is an added `kind`** beyond the seven in §4 (river, bay, ocean, lake, pond, canal, basin) and
   744 marsh polygons follow the DEM rather than a water plane — a tidal wetland surface is not a flat
   pool. Extension columns on `hydrography.parquet` (`name_source`, `level_mode`, `water_z_m`,
   `level_source`, `z_dem_*`, `n_dem_samples`, `is_open_water`, `source`, `feat_code`, `osm_id`,
   `plan_source_id`, `area_m2`) and `borough_codes = 7` on `tiles/index.parquet` are the only contract
   extensions; both are recorded in the parquet metadata.
5. **Bridge and viaduct decks are not terrain.** Planimetric bridge elevations (sub code 300020) and 24
   pier polygons with decks above 15 m are excluded, so the ground under an elevated structure stays the
   ground. The road stage must place bridge decks itself from the CSCL level codes — `sample_z` returns
   the *terrain*, not the roadway, under a bridge.
6. **A second terrain agent was running in the same lane during this session** (the orchestrator resumed
   two). The code in `pipeline/nycsim_pipeline/terrain/` is the merge of both: this report's author
   contributed `coverage.py`, `points.py`, `hydro.py`, `index.py`, `segment_z.py`, `water/names.py`, the
   tidal-classification and name fixes in `water/build.py`, the seam-exact encoding path and most of the
   test module; the other contributed `build.py`, `manifest_safe.py`, the sub-datum repair and the 16 m
   overview. All artefacts on disk were produced by the final pass over the merged code and verified
   together. `data/manifest/processed.json` was found corrupted by two agents writing it at once (one
   stray `}`); it was repaired in place under `data/manifest/.processed.lock` with all 258 entries kept.

## 12. What the next agent needs to know

* **Use `nycsim_pipeline.terrain.segment_z.sample_z(x, y)`** for any elevation. It is cached, vectorised
  and seam-continuous, and it reads the same PNGs the engine will. Do not re-open the intermediates.
* **`sample_z` is the ground.** Bridges, viaducts and elevated rail are *not* in it by design; add the
  structure height on top.
* **Water level:** everything tidal is exactly `0.0` m. `water/hydrography.parquet` carries
  `tidal`, `level_mode` (`tidal` | `constant` | `dem`) and `water_z_m` per body — use `water_z_m` for a
  non-tidal pool (Central Park reservoir 34.52 m, The Lake 16.55 m, Meadow Lake, Silver Lake, Jerome Park
  …), and expect `NaN` where `level_mode == "dem"` (marshes and sloped streams follow the terrain).
* **`tiles/index.parquet` is shared.** Fill only your own columns and take
  `nycsim_pipeline.terrain.index.index_lock()` around the read-modify-write; the terrain writer preserves
  any non-zero count and any extra column it does not own.
* **Tile geometry:** 501 × 501 samples at 2 m with **inclusive edges** — the last row/column of a tile is
  the first row/column of its neighbour, bit-identical. A consumer that treats a tile as 500 × 500 will
  drop a sample line; a consumer that stitches without dropping the duplicate will double one.
* **Elevation decode:** `z = z_min_m + png_value × z_scale_m`, `z_scale_m` is 0.0025 m for every tile.
* Reproduce the whole stage with `python -m nycsim_pipeline terrain` (idempotent, `--from`/`--only`
  select steps), or step by step: `terrain.ingest` → `terrain.points` → `water.build` →
  `terrain.coverage` → `terrain.tiles --workers 2` → `terrain.index` → `terrain.verify`.
