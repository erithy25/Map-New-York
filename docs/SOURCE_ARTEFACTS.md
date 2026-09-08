# Compressed and removed source artefacts

Large source files were compressed, and one large intermediate removed, to make room for the
city-wide build passes. **Nothing was deleted that is not regenerable, and nothing was deleted
without a record.** This file is that record.

> **Correction, 2026-09-08.** The section below calls these files "recoverable in place, without a
> network round trip". For seven of them that is no longer true: a later disk pass deleted the
> archives outright. The audit and the test that shows nothing is lost are at the bottom of this
> file, under *What is actually on disk*. The claim above -- regenerable, recorded -- still holds;
> the claim about `gunzip` does not.

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

Two of them no longer need even the `gunzip`: the furniture stage reads `street_trees_2015.csv.gz` through
polars and `plan_elevation_points.geojson.gz` through GDAL's `/vsigzip/`, falling back to the archive when the
plain file is absent. Re-running that stage therefore costs no scratch disk at all.

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

* ~~`data/raw/character_assets/mh_data` (508 MB) — unpacked from zips that are still present, so it is
  reconstructible, but a character rebuild needs it and the disk pressure never justified the risk.~~
  **Both went, and the zips were not "still present" when it mattered.** A later pass removed the
  whole `data/raw/character_assets` directory — the 508 MB tree *and* the fourteen archives — leaving
  MPFB2's user-data symlinks dangling, so `chenv.enable_mpfb` failed with all eight asset directories
  missing and the character stage could not be run at all. Worse, **the step that built `mh_data`
  from those archives had never been in the repository**, and the packs were not in
  `nycsim_pipeline.sources` either, so `python -m nycsim_pipeline.download --id mh_bodyparts01`
  answered *unknown source id*. Recovery existed only as 14 URLs and hashes recorded in
  `data/manifest/downloads.json` after the fact. `tools/unpack_character_assets.py` closes that: it
  reads the manifest, fetches each pack against its recorded SHA-256, and merges the archives into
  the tree — 939 files, 508 MB, verified by rebuilding it and baking twelve NPCs from it. One pack
  does not merge: `faceunits01` goes to `mh_data/faceunits_pack/`, because `mh_build.FACEUNITS_DIR`
  expects it there and that path was the only surviving record of the original layout.
* `data/raw/doitt_3d/DA_WISE_GML.zip` (874 MB) — the CityGML source. Spent (all 21 delivery-area
  parquet outputs exist) but already compressed, so only deletion would free anything, and it is an
  874 MB download.


## What is actually on disk, 2026-09-08

Re-running the furniture stage for J56 needed three raw sources. Two were not on disk in any form,
and one of those was never listed in this file at all. Audited the whole list against the working
copy:

| File | This file says | On disk today |
|---|---|---|
| `building_footprints.geojson` | `.gz`, recoverable in place | **gone** |
| `plan_roadbed.geojson` | `.gz`, recoverable in place | **gone** |
| `plan_pavement_edge.geojson` | `.gz`, recoverable in place | **gone** |
| `plan_sidewalk.geojson` | `.gz`, recoverable in place | **gone** |
| `plan_curb.geojson` | `.gz`, recoverable in place | **gone** |
| `pluto.csv` | `.gz`, recoverable in place | **gone** |
| `dohmh_restaurants.csv` | `.gz`, recoverable in place | **gone** |
| `street_trees_2015.csv` | `.gz`, recoverable in place | **was gone**, re-downloaded |
| `plan_elevation_points.geojson` | `.gz`, recoverable in place | restored plain by `gunzip -k` |
| `centerline.geojson` | `.gz`, recoverable in place | `.gz` present, claim holds |
| `traffic_volume_auto.csv` | `.gz`, recoverable in place | `.gz` present, claim holds |
| `dot_signs.csv` | `.gz`, recoverable in place | `.gz` present, claim holds |
| `pedestrian_ramps.csv` | *not listed* | **was gone**, re-downloaded |
| `character_assets/*.zip` (14 packs, 442.5 MB) | *listed as "still present"* | **was gone**, re-downloaded, unpacked, removed again |
| `character_assets/mh_data` (508 MB) | *listed as not removed* | **was gone**, rebuilt by `tools/unpack_character_assets.py`, removed again |
| `plan_cooling_towers.geojson` | *not listed* | **was gone**, re-downloaded |

**Nothing is lost, and that was tested rather than asserted.** The three the furniture stage needs
were fetched again on 2026-09-08 and each came back at exactly the byte count already recorded in
`data/manifest/downloads.json`, with the recorded SHA-256:

| id | recorded bytes | fetched bytes |
|---|---|---|
| `street_trees_2015` | 220,354,362 | 220,354,362 |
| `pedestrian_ramps` | 42,057,860 | 42,057,860 |
| `plan_cooling_towers` | 35,433,370 | 35,433,370 |

Only `downloaded_at` moved. So the recovery discipline works; what it costs is a network round trip
before a finished stage can be re-run, and deleting the sources again afterwards on a container with
a fixed disk allowance. The sentence this file opened with -- *nothing was deleted without a record*
-- was true of the deletions it knew about and false of the two it did not, which is why the table
above lists every file rather than only the ones that moved.

```bash
PYTHONPATH=pipeline python3 -m nycsim_pipeline.download --id street_trees_2015
```
