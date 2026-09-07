# CityGML LOD2 stage — verification report

Stage owner: CityGML agent. Date: 2026-09-06. Source: **NYC 3-D Building Model** (DoITT/DCP, CityGML 2.0
generated from the 2014 LiDAR flight), `data/raw/doitt_3d/DA_WISE_GML.zip`, 916 MB compressed / **13.78 GB**
of GML in 20 delivery-area members. Licence: NYC Open Data, public domain (recorded in
`data/manifest/downloads.json`).

## 1. What was built

| file | what |
|---|---|
| `pipeline/nycsim_pipeline/buildings/citygml.py` | streaming CityGML parser -> per-BIN triangulated solids, resumable per delivery area, city-wide index builder, CLI |
| `pipeline/nycsim_pipeline/buildings/citygml_geom.py` | pure-numpy planar geometry: ring cleaning, earcut triangulation with holes, winding, float32 finalisation, clustering |
| `pipeline/nycsim_pipeline/buildings/citygml_roof.py` | roof-form classifier (flat/gable/hip/mansard/shed/sawtooth/complex/dome/barrel) + roof-level extraction |
| `pipeline/nycsim_pipeline/buildings/citygml_join.py` | **new** — builds `buildings/roof_attrs.parquet` and exposes `attach_roof_columns()`, the one call `buildings/build.py` needs |
| `pipeline/nycsim_pipeline/buildings/citygml_validate.py` | validation against `footprints_raw.parquet`, raw-GML roof-slope evidence, sloped-roof census, roof-inference calibration |
| `pipeline/tests/test_citygml.py` + `tests/fixtures/citygml_sample.gml` (+ `make_citygml_sample.py`) | 67 tests, fixture-driven and data-driven |
| `data/processed/buildings/citygml/da{1..20}.parquet` | 518 MB, schema `citygml_solids_v1`, one row per building with the triangle blob |
| `data/processed/buildings/citygml/index.parquet` | 66 MB, schema `citygml_index_v1`, 1,083,255 rows, one per BIN city-wide |
| `data/processed/buildings/roof_attrs.parquet` | 42 MB, schema `buildings_roof_attrs_v1`, 1,083,016 rows — **the buildings stage consumes this** (contract §5.3) |
| `docs/verification/citygml/*.json` | `validation_all.json`, `roof_evidence_da4_queens.json`, `roof_sloped_buildings.json`, `roof_inference_calibration.json`, `roof_attrs_summary.json` |

Run commands (exactly what was executed):

```sh
# full pass, 2 workers, nice'd, resumable per DA via progress.json
printf "%s\n" 19 20 18 15 16 17 6 7 8 9 11 13 12 10 14 5 3 2 1 4 \
  | xargs -P 2 -n 1 sh -c 'nice -n 10 python3 -m nycsim_pipeline citygml --da "$0" --log-every 20000' \
  > data/processed/buildings/citygml/full_run.log 2>&1
python3 -m nycsim_pipeline citygml --build-index      # index.parquet
python3 -m nycsim_pipeline citygml --join             # roof_attrs.parquet
PYTHONPATH=pipeline python3 -m pytest pipeline/tests/test_citygml.py -q
```

## 2. Throughput, volume, memory

All 20 delivery areas completed, **no errors, no partial files** (`progress.json`: every DA `status: done`,
`error: null`, every stream read to its full member length).

| metric | value |
|---|---|
| wall clock, 2 concurrent workers | 11:09:30Z -> 12:07:13Z = **57 min 43 s** |
| GML streamed | 13,782,389,916 B (13.78 GB) — the zip is never extracted (`unzip -p` -> `lxml.iterparse`) |
| buildings parsed | **1,083,437** `bldg:Building` elements |
| rows written | **1,083,281** (156 rows merged away: 138 BINs appear as several Building elements) |
| throughput, wall clock | 313 buildings/s, 3.98 MB/s |
| throughput, per worker | 159 buildings/s, 2.02 MB/s (a single worker alone reached 455 buildings/s and 6.0 MB/s on DA4; the drop is contention — 2 workers + 2 `unzip` on 4 vCPU shared with other agents) |
| peak RSS per worker | **366 MB** (streaming: memory is one XML element + one 4,000-row parquet buffer, independent of the 1.4 GB member size) |
| output | 518 MB per-DA parquet + 66 MB index + 42 MB roof_attrs |
| triangles | **30,723,703** total; median 20 per building, p90 48, p99 153 |

Per-DA rows and timings are in `data/processed/buildings/citygml/progress.json`; the log is
`data/processed/buildings/citygml/full_run.log`.

## 3. BIN match rate and geometric validation (`validation_all.json`)

| check | result |
|---|---|
| rows with a real BIN | 1,052,344 of 1,083,281 (30,937 carry a borough placeholder `x000000`, 19 carry none) |
| **BIN match rate against `footprints_raw.parquet`** | **1,033,440 / 1,052,344 = 98.20 %** (per-DA 95.0 % … 99.66 %) |
| DOITT_ID present | 99.21 % of rows; 98.20 % hit a footprint DOITT_ID; 99.59 % agree with the BIN match |
| vertical datum (`z_ground_min` minus footprint `ground_z`) | median -0.199 m, mean -0.287 m, 75.6 % within 0.5 m -> CityGML z is feet NAVD88, as assumed (x 0.3048006) |
| **roof height** (`z_roof_max` minus (`ground_z` + `height`)) | **median exactly 0.000000 m**; 91.2 % within 0.5 m, 94.6 % within 1 m, 99.3 % within 5 m |
| horizontal offset vs footprint centroid | median 2.6e-5 m, 99.18 % within 1 m (NAD83->WGS84 Helmert `NAD_1983_To_WGS_1984_5`, position-vector; PROJ's default null shift would leave a 0.92 m north offset) |
| footprint area ratio (CityGML ground / footprint polygon) | median 1.0000000000, p10 0.999997, p90 1.000003 |
| winding | 9,280,743 ground-touching walls outward vs 12,736 inward (0.14 %); roof triangles all face up, ground all face down (asserted per row in the tests) |

**The 5.4 % of buildings whose roof height differs by more than 1 m are a data-vintage difference, not a
parser error**: 55,049 of those 55,450 buildings have a footprint record edited after 2014, i.e. the
published `heightroof` was revised after the LiDAR flight that produced the CityGML. CityGML is the taller
of the two in 83 % of them, median absolute difference 2.82 m. Both fields come from the same 2014 survey
where the footprint has not been touched since, which is why the median is exactly zero.

Parser robustness over 1.08 M buildings: 4 buildings with no ground surface, 4 with no roof surface, 54
degenerate polygons, 1,675 polygons flagged non-planar (> 5 cm from their best-fit plane), 12,213 float32
slivers dropped, **0 exceptions**. 12.97 M duplicate and 5.13 M collinear vertices removed.

## 4. The flat-roof finding (ADR-013)

**Roof *shape* is not available from this source. Roof *massing* is.**

Measured on the **raw source rings, before any unit or datum transform** (`roof_evidence_da4_queens.json`,
reproduce with `citygml_validate.roof_evidence`): in DA4 (Queens, 16,665 buildings) all **21,956**
`bldg:RoofSurface` polygons have unit normal exactly (0, 0, 1) and z-range exactly 0.0 ft. Maximum slope
**0.000000 degrees**. Nothing at 1 degree, nothing at 0.01. Re-sampled in Staten Island (DA17) and
Manhattan (DA12): identical. Twenty **named** one-family houses on 87 Street, Howard Beach
(BINs 4292333 … 4594319, PLUTO class A1, built 1920–2007) — gabled and hipped in reality — are modelled as
one to four stacked horizontal slabs; several are a bare 12-triangle box.

City-wide over all 1,083,281 buildings:

| | count | share |
|---|---|---|
| roof faces horizontal (< 8 deg from level) | 1,575,141 | 99.60 % |
| roof faces sloped | 6,345 | 0.40 % |
| roof faces near-vertical (parapet sides tagged as roof) | 612 | 0.04 % |
| **buildings with *any* sloped roof face** | **110** | **0.0102 %** |
| buildings the classifier calls non-flat | 60 | 0.0055 % |

The 110 are the hand-modelled landmarks, and only those: Statue of Liberty (3,131 roof faces, 9,404
triangles), Cathedral of St. John the Divine, the Metropolitan Museum, Empire State Building, Chrysler
Building, U.N. Headquarters, Waldorf Astoria, the Ansonia, The Cloisters, City Hall, Low Memorial Library,
Madison Square Garden, Citi Field, Barclays Center, Brooklyn Museum, Litchfield Villa, Williamsburgh
Savings Bank Tower… 102 of the 110 carry a building name and 56 an LPC landmark id. Full list with slopes
and triangle counts: `roof_sloped_buildings.json`. Every one of them exceeds 5 degrees — these are
deliberate detailed models, not numerical noise.

This matches the orchestrator's independent measurement (28 buildings, 0.007 %, over 395,891 buildings at a
2-degree threshold) and is recorded as **ADR-013** with an implementation addendum in `docs/DECISIONS.md`.

**The classifier is not broken.** The committed fixture `pipeline/tests/fixtures/citygml_sample.gml`
contains a synthetic gable (eaves 30 ft, ridge 45 ft, half-span 12 ft), a hip, a shed and a two-level flat
building in the same CityGML dialect at the same NYC coordinates; the pipeline classifies them
`gable` / `hip` / `shed` / `flat` and recovers the gable slope as 51.34 deg = atan(15/12) to within 0.05
(`test_fixture_roof_types`, `test_fixture_roof_slope_is_geometrically_correct`). It also finds hip, barrel,
mansard, dome and complex on the real landmark buildings. The flat result is a true statement about the
source.

### What the source *does* give, and it is worth having

`n_roof_levels`, `roof_level_z` and `roof_level_area` are real measurements of stepped massing — setbacks,
bulkheads, penthouses, mechanical floors — and they are first-class columns in both `index.parquet` and
`roof_attrs.parquet`:

* **301,311 buildings (27.8 %) have >= 2 distinct roof levels**; the maximum is **38**.
* Manhattan: 59.2 % of buildings have >= 2 levels — that is the setback profile of the tower stock.
* Distribution: 1 level 732,105 - 2 levels 246,796 - 3 levels 40,602 - 4 levels 6,538 - >= 5 levels 7,270.

Together with the real roof outline and the real roof height this is what `ROOF_REAL` now means.

## 5. Roof-type distribution after the fix

`roof_attrs.parquet`, 1,083,016 rows (one per distinct real BIN):

| roof_type | rows | share | |
|---|---|---|---|
| flat | 564,975 | 52.17 % | |
| gable | 517,809 | 47.81 % | 517,566 inferred + 240 from OSM tags + 3 from CityGML |
| hip | 159 | 0.015 % | 147 OSM, 12 CityGML |
| complex | 28 | 0.003 % | CityGML landmark meshes |
| mansard | 17 | 0.002 % | |
| shed | 12 | 0.001 % | |
| dome | 8 | 0.001 % | |
| barrel | 8 | 0.001 % | |
| sawtooth | 0 | — | |

| `roof_type_source` | rows | meaning |
|---|---|---|
| 0 `citygml` | 55 | the hand-modelled landmarks — measured shape |
| 1 `osm` | 4,037 | a real OSM `roof:shape` tag matched to the footprint (<= 6 m centroid distance) |
| 2 `inferred` | 517,566 | PLUTO class + footprint/lot shape (flagged `roof_inferred`) |
| 3 `default` | 561,358 | no evidence -> flat |

Borough profile — the sanity check that the inference is not nonsense:

| borough | buildings | CityGML mesh | pitched | >= 2 roof levels |
|---|---|---|---|---|
| Manhattan | 45,193 | 96.6 % | **0.7 %** | 59.2 % |
| Bronx | 104,276 | 95.9 % | 38.1 % | 28.1 % |
| Brooklyn | 330,150 | 97.1 % | 28.2 % | 27.7 % |
| Queens | 460,937 | 94.5 % | **61.0 %** | 27.2 % |
| Staten Island | 142,460 | 93.9 % | **73.0 %** | 19.9 % |
| **city** | **1,083,016** | **95.42 %** | **47.83 %** | **27.8 %** |

### The inference rule and its measured accuracy

Fires only for detached one/two-family stock:
`bldg_class` in {A0–A9, B1–B9, C0, S0–S2, S9, R1, R3} **and** `bldg_frontage / lot_frontage < 0.80` (a side
yard exists -> no party wall; this is what separates a gabled Queens house from a flat-roofed Brooklyn row
house) **and** minimum-rotated-rectangle short side <= 14 m **and** <= 3 floors **and** footprint <= 400 m2.

Scored against the only real roof-shape evidence available for NYC — the 4,038 OSM buildings carrying a
`roof:shape` tag that match a footprint centroid within 6 m (`roof_inference_calibration.json`, reproduce
with `citygml_validate.roof_inference_calibration`):

| | value |
|---|---|
| precision | **0.805** (tp 190, fp 46) |
| recall | 0.456 (fn 227) |
| accuracy | 0.932 |
| precision, Queens | 1.00 (n = 28) |
| precision, Brooklyn | 0.789 (n = 204) |
| Manhattan | rule fired 3 times, all 3 wrong |

Geometry of an inferred roof (ADR-013): the measured `z_roof_max` is kept as the **ridge**, so overall
building height stays exactly the published LiDAR height; the eave drops one full rise below it
(`roof_eave_dz_m` <= 0, `roof_ridge_dz_m` = 0). Nominal pitch 30 degrees (7:12), rise clamped to
[0.9, 3.0] m with the pitch recomputed when the clamp bites — realised mean 29.87 deg, range 23.2–51.6.
Sample: 156-46 87 Street (A1, 2 floors, LiDAR roof 5.76 m AGL) -> eave 4.38 m, ridge 7.38 m, ridge
bearing 169 deg.

## 6. Gaps, stated plainly

1. **Roof shape is not measured.** 47.8 % of NYC buildings carry a *typologically* inferred gable, not a
   surveyed one. Measured precision 0.805 on the OSM sample means roughly **1 in 5 of those 518 k pitched
   roofs is wrong** (a flat roof turned pitched), and recall 0.456 means **more than half of the genuinely
   pitched roofs are missed** and stay flat. Every inferred row is flagged (`roof_inferred`,
   `roof_type_source = 2`, `roof_type_conf = 0.805`) and `roof_shape_measured` is False for 1,082,913 of
   1,083,016 rows.
2. **Gable vs hip is undetermined.** On the 347 buildings OSM tags `gabled` or `hipped`, the best
   footprint-aspect threshold scores 0.617 accuracy against a 0.637 majority-class baseline — worse than
   always saying gable. Every inferred pitched roof is therefore emitted as `gable` with its ridge along
   the long axis of the minimum rotated rectangle. About 36 % of them are hips in reality.
3. **The OSM calibration sample is mapper-selected** (4,038 of 1.08 M buildings, 71 % of them in Brooklyn
   and Manhattan) and skews to buildings someone chose to survey. Treat 0.805 / 0.456 as an
   order-of-magnitude check, not an unbiased estimate. Closing this needs a roof-plane classifier on the
   raw LiDAR point cloud or an aerial photogrammetric mesh.
4. **4.58 % of footprints (49,600) have no CityGML solid** — mostly buildings constructed after the 2014
   flight, plus the 30,937 CityGML rows whose BIN is a borough placeholder and cannot be joined. Those get
   `citygml_match = False`, empty `roof_mesh_ref`, `ROOF_REAL` clear, `n_roof_levels = 0`.
5. **`roofs.glb` does not exist yet.** `roof_mesh_ref` is the forward reference
   `t_{tx}_{ty}/roofs.glb#bin_{bin}`; the triangles are in `citygml/da{n}.parquet` (`tri_xyz` float32 blob
   plus `tri_type`). A Blender stage still has to write the glb files. The reference uses the **footprint**
   tile so the mesh lands in the same tile file as the building row (120 buildings sit on a tile boundary
   where the CityGML centroid would have chosen the neighbouring tile).
6. **Two placeholder-BIN footprints per borough are dropped** from `roof_attrs.parquet` (10 rows) because a
   placeholder BIN cannot key a join.

## 7. What the buildings agent must do — exact instructions

`buildings/build.py` was **not** edited (it belongs to the buildings agent). The join stage is
self-contained; add **one line** to `build.py`, immediately before it writes `buildings_base.parquet` and
the per-tile files, when `df` already has `bin` and `fidelity`:

```python
from .citygml_join import attach_roof_columns

df = attach_roof_columns(df)     # adds roof_type (int8) + roof_mesh_ref (string), ORs ROOF_REAL into fidelity
```

That call:

* left-joins `data/processed/buildings/roof_attrs.parquet` on `bin` (one row per BIN — it cannot fan out;
  the row count and row order of `df` are preserved and asserted);
* sets `roof_type` (DATA_CONTRACTS §5 enum, `flat` where there is no evidence) and `roof_mesh_ref`
  (`""` where there is no CityGML solid) — both are in `schema.DEFERRED_CONTRACT_COLUMNS` today;
* ORs `Fidelity.ROOF_REAL` into `fidelity` for the 1,033,416 buildings that have a measured LOD2 massing
  solid, and leaves it clear for the rest;
* degrades gracefully: if `roof_attrs.parquet` has not been built, the columns are still added with
  `flat` / `""` and `ROOF_REAL` stays clear (pass `strict=True` to make that an error instead).

`STAGE_BITS` in `buildings/schema.py` deliberately excludes `ROOF_REAL`; if that tuple is used to validate
which bits the buildings stage may set, `ROOF_REAL` must be allowed once this call is in place — that is
the only change needed outside the one line, and it is the buildings agent's decision.

Anything that needs more than `roof_type` / `roof_mesh_ref` — the facade-rules stage and the Blender shell
stage — should read `roof_attrs.parquet` directly (contract §5.3). The columns that matter to them:

* `roof_shape_measured` — **False for 99.99 % of buildings**. When it is False the roof silhouette must be
  generated from typology, never taken as measured.
* `n_roof_levels`, `roof_level_z`, `roof_level_area` — real setbacks; build the shell as a stack of
  prisms, not a single extrusion, for the 301,311 buildings with >= 2 levels.
* `roof_pitch_deg`, `roof_ridge_deg`, `roof_eave_dz_m`, `roof_ridge_dz_m` — everything needed to build the
  inferred gable, with `z_roof_max` as the ridge.
* `roof_type_source` / `roof_type_conf` — provenance, for the fidelity report.

The LOD2 triangles for the Blender stage are in `citygml/da{n}.parquet`: `tri_xyz` is little-endian
float32, `tri_count x 9` values (`x y z` per vertex, 3 vertices per triangle, absolute NYC_TM metres),
`tri_type` is one uint8 per triangle (0 ground, 1 wall, 2 roof). Roof triangles face up, ground triangles
face down, walls keep their outward source winding.

## 8. Tests

```
PYTHONPATH=pipeline python3 -m pytest pipeline/tests/test_citygml.py -q
67 passed in 28.78s
```

* **Fixture-driven (no data needed)** — `tests/fixtures/citygml_sample.gml`, regenerate with
  `fixtures/make_citygml_sample.py`: nine `bldg:Building` elements at real Queens EPSG:2263 coordinates
  covering a flat box, a gable, a hip, a shed, a two-level building with a hole in the lower roof, a
  duplicate BIN (merge), a missing BIN, a borough-placeholder BIN and a malformed 2-D ring. Asserts row
  counts, the merge, flag bits, dropped-ring handling, roof types, roof levels and their areas, the gable
  slope against atan(15/12), footprint areas against the source rectangles, triangle-blob lengths,
  triangle winding per surface type and bounding boxes.
* **Units** — `parse_srs` across five srsName spellings including the compound OGC urn (`EPSG:6.12:2263`,
  where the authority *version* must not be read as the code — a bug found and fixed while writing these
  tests), `parse_bin`, Newell normals, slope/azimuth, ring cleaning, collinear removal, earcut with holes
  and its area, rejection paths, float32 sliver dropping, circular clustering, vertex welding, nine roof
  classifier cases, the inference rule and its rejections, the rise clamp, the OSM shape mapping.
* **Buildings interface** — `attach_roof_columns` preserves order, sets the right bit, handles a missing
  artefact and missing columns.
* **Real data (skip when absent)** — BIN uniqueness and match rate >= 97 %, roof-height agreement, the
  flat-massing invariant (non-flat share < 1e-4, sloped-face share < 1 %), the roof-evidence JSON, and the
  full `roof_attrs.parquet` contract: every field type, `roof_mesh_ref` set exactly where
  `citygml_match`, `z_roof_max` NaN where not, pitched rows carrying valid geometry, `roof_inferred`
  consistent with `roof_type_source`.

The flat-massing tests are written to **fail loudly** if DoITT ever publishes sloped LOD2 for the ordinary
stock, because the `roof_type` fallback would then have to be revisited.

## 9. Contract changes made

* `docs/DATA_CONTRACTS.md` **§5.3 appended** — `buildings/roof_attrs.parquet`, schema
  `buildings_roof_attrs_v1`, every column documented.
* `docs/DECISIONS.md` — **ADR-013 addendum** with the measurement and the implementation. The duplicate
  ADR-013 this stage had proposed before the orchestrator's own measurement landed was removed; the
  orchestrator's ADR-013 stands and the code follows it (measured `z_roof_max` kept as the ridge; separate
  `roof_shape_measured` flag; `n_roof_levels` / `roof_level_z` / `roof_level_area` first-class).
* No foundation file and no other agent's file was modified.
