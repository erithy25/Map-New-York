# Traffic calibration — verification report

Written by the orchestrator from the calibration agent's delivery after independently verifying the
artefacts. The step-by-step method is in `METHOD.md` in this directory; every number below was
re-read from the files on disk, not taken on trust.

## 1. Artefacts and contract compliance

| Path | Rows | Schema |
|---|---|---|
| `data/processed/traffic/density.parquet` | 18,864 | `traffic/density@1`, DATA_CONTRACTS §10 |
| `data/processed/traffic/density_detail.parquet` | 18,864 | modelled speed, observed speed, flow, lane-km, provenance |
| `data/processed/traffic/fleet_mix.json` | 18 classes × 6 regions × 5 bands | `traffic/fleet_mix@1` |
| `data/processed/runtime/density.nycb` | 18,864 cells, 334 NTA rings | DATA_CONTRACTS §15 |

Verified by the orchestrator: `validate_parquet("density", …)` passes; **262 NTAs × 24 hours × 3 day
types = 18,864 rows** with no gaps; **zero nulls in every column**; every share inside [0, 1] and the
four summing to at most **0.866**; peak density 56.34 veh/km/lane, well under the 130 jam value.

## 2. Sanity, re-measured

| Check | Value | Verdict |
|---|---|---|
| Midtown–Times Square, weekday 17:00 | 56.34 veh/km/lane | busiest cell in the city |
| Midtown–Times Square, weekday 04:00 | 5.94 | 9.5× lower than its own peak |
| Tottenville–Charleston, weekday 17:00 | 4.43 | 12.7× below Midtown at the same hour |
| Pedestrians, Midtown 13:00 vs 04:00 | 0.152 vs 0.012 ped/m² | 13× |
| Pedestrians, Midtown vs Tottenville at 13:00 | 0.152 vs 0.005 | 30× |

## 3. Checks against sources that were **not** used to fit

These are the figures that make the table trustworthy, because nothing in them was tuned.

| Quantity | Model | Published |
|---|---|---|
| Manhattan central business district travel speed, weekday 11:00–17:00 | 10.6–11.2 km/h | NYC DOT Mobility Report, about 7 mph ≈ 11 km/h |
| For-hire share of traffic in the central business district | 28–34 % | TLC and DOT, about 30 % |
| Pedestrian hourly shape vs DOT's permanent counters | correlation 0.953 | counters were not used to build the shape |
| Truck share citywide, weekday | 3.4 %, peaking 6.3 % at 03:00 | matches the overnight freight window |
| Pedestrians on sidewalks, weekday 13:00 | 1.11 million | about 11 % of the daytime population |

## 4. Fitted models

* **Volume by road class** (1,616 count sites): R² 0.271, leave-one-out 0.260.
* **Land-use regression** filling the 31 neighbourhoods without counts (227 neighbourhoods): R² 0.206,
  leave-one-out 0.158. Combined at neighbourhood level, R² rises from 0.303 on road class alone to **0.447**.
* **Pedestrians** (99 DOT count sites): R² 0.694, leave-one-out 0.639, with retail floor area the
  strongest predictor.
* **Bicycles** (29 permanent counters): R² 0.420, leave-one-out 0.162 — spatial pattern only, with the
  citywide level anchored on DOT's published 610,000 trips per day.

Provenance per neighbourhood: 227 of 262 rest on their own counts, **31 (11.8 %, covering 5.9 % of
lane-kilometres) come from the regression**, and 4 have no roads at all.

## 5. Honest gaps

1. **The land-use regression is weak, and the data says it must be.** The median neighbourhood has six
   count sites and the within-neighbourhood residual spread is 0.66 log units, so roughly a third of the
   between-neighbourhood variance is sampling noise. A perfect model could not exceed about R² 0.7 here.
   The 31 affected neighbourhoods are right to about ±45 % on level.
2. **Only 321 of 2,397 count sites were last counted in 2023 or later** — DOT counts roughly 100 to 130
   segments a year. Older sites are down-weighted and their neighbourhoods are tagged, but the post-2019
   mode shift and 2025 congestion pricing are only partly represented.
3. **Weekend modal shares reuse the weekday shares**, because DOT's classification counts are weekday-only
   across the whole 2011–2025 file. Volumes are day-type specific; weekend truck share is an upper bound.
4. **Bicycle shares do not come from the classification counts**, which carry no bicycle class. This is a
   stated deviation from the brief. The 29 permanent counters all sit on cycle routes, so the raw fit was
   scaled by 0.655 to reproduce the published citywide figure.
5. **Citywide vehicle-kilometres land 15–30 % below the published state figure** (91.2 M against 105–130 M).
   Densities are per lane so the spatial pattern is unaffected, but this table must not be used as a
   citywide vehicle-miles estimate.
6. **Emergency-vehicle activity is the least grounded part of the fleet mix.** Fleet sizes are published;
   daily distance per vehicle and duty cycles are assumptions, and each carries a `basis` string saying so.
7. **School buses have no vehicle class.** The bus share includes DOT's school-bus class but the simulation
   has only `MtaBus`, so the bus group resolves entirely to transit buses.
8. **Sidewalk area is mapped polygon area × 0.63**, the Street Design Manual clear-path fraction applied
   uniformly rather than per block.

## 6. Runtime and reproducibility

Full rebuild `python -m nycsim_pipeline.traffic.build` takes 7.8 CPU-minutes at peak 1.52 GB, under the
4 GB budget, using lazy scans over the 234 MB count file, 334 MB lot file and 277 MB of trip records.
Two consecutive builds produce a byte-identical `density.nycb`. The 36-test suite passes.

## 7. Licences

NYC Open Data Terms of Use for every City dataset used, and TLC trip records as public data released by
the New York City Taxi and Limousine Commission with attribution requested. All recorded in
`data/manifest/downloads.json` with URL, licence, attribution and SHA-256.
