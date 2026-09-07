# Compressed and removed source artefacts

Large source files were compressed, and one large intermediate removed, to make room for the
city-wide build passes. **Nothing was deleted that is not regenerable, and nothing was deleted
without a record.** This file is that record.

It lives here rather than beside the files because `data/` is git-ignored: the notes written next to
the artefacts (`data/raw/nyc_opendata/README_COMPRESSED.md`, `data/processed/terrain/src2m_removed.json`)
are untracked and would vanish with the container. That was an oversight in the recovery discipline and
this file corrects it.

## Compressed sources

Each is recoverable in place, without a network round trip:

```bash
gunzip -k data/raw/nyc_opendata/<name>.gz     # -k keeps the archive
```

Every one is also re-downloadable by its manifest id against the SHA-256 recorded in
`data/manifest/downloads.json`.

| File | Consuming stage (complete) |
|---|---|
| `building_footprints.geojson.gz` | buildings — the 1,083,026-row base table |
| `plan_roadbed.geojson.gz` | roads pavement |
| `plan_pavement_edge.geojson.gz` | roads pavement |
| `plan_sidewalk.geojson.gz` | roads pavement, pedestrian density |
| `plan_curb.geojson.gz` | roads pavement |
| `plan_elevation_points.geojson.gz` | terrain densification |
| `pluto.csv.gz` | buildings — floors, year, class, land use, lot geometry |
| `traffic_volume_auto.csv.gz` | traffic density |
| `street_trees_2015.csv.gz` | street furniture — 650,516 tree positions |
| `centerline.geojson.gz` | roads — the CSCL network |
| `dohmh_restaurants.csv.gz` | facade storefront names — 30,381 real business names |
| `dot_signs.csv.gz` | roads regulatory signage — 633,287 signs |

## Removed intermediate

| Artefact | Bytes | Why | Regenerate with |
|---|---|---|---|
| `data/processed/terrain/src2m` | 1,757,651,688 | the 2,916 published tiles are the product and are complete; the intermediate is regenerable from data/raw/usgs by `python -m nycsim_pipeline terrain --ingest`, and disk was needed for the city-wide building shell run | `python -m nycsim_pipeline terrain --ingest` |

The index of what that mosaic was cut from was deliberately kept behind at
`data/processed/terrain/src2m_index_kept.json` — one record per ingested window with its source id,
kind, byte count and SHA-256 — which is why §3 of the fidelity report can still state the 30 USGS 3DEP
products and 4.50 GB of source data behind a mosaic that no longer exists.

## What was considered and not removed

* `data/raw/character_assets/mh_data` (508 MB) — unpacked from zips that are still present, so it is
  reconstructible, but a character rebuild needs it and the disk pressure never justified the risk.
* `data/raw/doitt_3d/DA_WISE_GML.zip` (874 MB) — the CityGML source. Spent (all 21 delivery-area
  parquet outputs exist) but already compressed, so only deletion would free anything, and it is an
  874 MB download.
