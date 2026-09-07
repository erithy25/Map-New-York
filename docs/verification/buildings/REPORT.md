# Stage report — buildings (the 1,083,026-row base table)

**Lane:** `pipeline/nycsim_pipeline/buildings/`, `data/processed/buildings/`, `pipeline/tests/test_buildings.py`
**Output:** `data/processed/buildings/buildings_base.parquet` — 1,083,026 rows, 51 columns
**Date:** 2026-09-06
**Written by:** the orchestrator, from the shipped artefact. Every figure below was read out of the parquet
file at the time of writing, not copied from a build log.

This report covers the base table only: the join, the provenance of each attribute, and what is measured
versus derived. Three lanes downstream of it have their own reports and are not repeated here —
`docs/verification/citygml/REPORT.md` (LOD2 roof geometry), `docs/verification/facade/REPORT.md` (facade
classification and the kit placement), and `docs/verification/buildings_mesh/REPORT.md` (the shell meshes).

---

## 1. What the table is

One row per building in the five boroughs, keyed by BIN, carrying the footprint polygon in NYC_TM metres,
the ground and roof elevation in NAVD88, and the attributes the downstream stages need to build and dress
a shell. Total modelled footprint area is **162.1 km²** — about 21 % of the city's 778 km² land area, which
is the right order for a city of this density.

| | |
|---|---|
| Rows | 1,083,026 |
| Distinct BINs | 1,083,021 |
| Median footprint area | 89.1 m² |
| Largest footprint | 108,872 m² (a single BIN; the table does not split multi-part complexes) |
| Median height | 7.97 m |
| Tallest | 472.44 m |
| Median year built | 1930 (1st–99th percentile 1884–2018) |

The five duplicate BINs are the borough sentinels 2000000, 3000000 and 4000000, which NYC assigns to
footprints that have no BIN of their own. They are kept rather than dropped — they are real buildings — and
every downstream join is positional or BIN-plus-row, never BIN alone. This is stated because a BIN-only join
against this table silently merges those eight rows.

## 2. Sources

| Source | Used for |
|---|---|
| NYC Open Data **Building Footprints** (OTI photogrammetric) | footprint geometry, `height_roof`, `ground_elevation`, construction year |
| **PLUTO** | floor count, year built, land use, building class, lot geometry |
| **Building Elevation and Subgrade** | ground grade where the footprint field is absent |
| **DOB sidewalk sheds** | active scaffold permits |
| **LPC individual landmarks** and **historic districts** | landmark id, style, material, district membership |
| OSM | storefront names and kinds, building names |

All are recorded in `data/manifest/downloads.json` with SHA-256 and licence; the full table is in
`docs/DATA_SOURCES.md`.

## 3. Attribute provenance — measured versus derived

This is the part of the table that matters for the fidelity claim, so it is given in full. The numeric
source codes are `pipeline/nycsim_pipeline/buildings/schema.py` lines 76–82.

### 3.1 Height

| Source | Buildings | Share |
|---|---|---|
| `SRC_LIDAR` — `height_roof` from the OTI LiDAR-derived field | 1,082,290 | 99.93 % |
| `SRC_NEIGHBOURS` — median of the 10 nearest buildings with a real value | 405 | 0.04 % |
| `SRC_PLUTO` — PLUTO floor count × the class floor height | 331 | 0.03 % |

736 buildings (0.07 %) therefore carry an inferred height, and they are flagged `HEIGHT_INFERRED` (bit 11),
not `HEIGHT_REAL`. Height ranges from 1.00 m to 472.44 m; the floor at 1 m is deliberate, because the source
carries zeros and negative values for a few hundred footprints and a building of zero height is not a
building.

**External cross-check.** The six tallest rows in the table, against published roof heights. These were not
tuned to match — `height_roof` is taken from the source untouched, so this is a check on the source and on
the join, and it is the strongest evidence in this report that the height column means what it says:

| Address in the table | Building | Table | Published roof | Δ |
|---|---|---|---|---|
| 217 West 57th Street | Central Park Tower | 472.44 m | 472.4 m | +0.04 m |
| 111 West 57th Street | Steinway Tower | 435.26 m | 435.3 m | −0.04 m |
| 185 Greenwich Street | One World Trade Center | 429.27 m | 417 m roof / 426.2 m parapet | +3.1 m |
| 51 East 42nd Street | One Vanderbilt | 427.03 m | 427 m | +0.03 m |
| 432 Park Avenue | 432 Park Avenue | 425.50 m | 425.5 m | 0.00 m |

`height_roof` is a LiDAR return, so it measures the highest structure over the footprint rather than the
architectural roof line: that is why One World Trade Center reads above its 417 m roof and close to its
parapet, and it is the reason no spire height appears anywhere in this column.

Two honesty notes from the same check. 432 Park Avenue appears **twice**, as two BINs at the same height —
the tower and its podium are separately binned, so a naive count of "buildings over 400 m" over this table
double-counts it. And the tallest row carries the OSM name *B. F. Goodrich Company Building*, which is the
1920s building that stood on that site, not Central Park Tower: the `name` column is an OSM attachment and
is **not** reliable as an identity, which is why nothing downstream keys on it.

### 3.2 Floors

| Source | Buildings | Share |
|---|---|---|
| `SRC_PLUTO` — floor count as published | 794,995 | 73.40 % |
| `SRC_HEIGHT_TO_FLOORS` — height ÷ the class floor height | 288,031 | 26.60 % |

**Over a quarter of the city's floor counts are derived, not published.** They are flagged
`FLOORS_INFERRED` (bit 12). This is the single largest inference in the base table and it is visible in the
build: floor count drives the facade kit's storey division, so a wrong floor count shows up as windows at
the wrong pitch. The derivation is not a guess at random — it divides a measured height by the floor height
for that building class — but it is not a published number and is not reported as one.

### 3.3 Year built

| Source | Buildings | Share |
|---|---|---|
| `SRC_FOOTPRINT_YEAR` — construction year from the footprint dataset | 1,072,951 | 99.07 % |
| `SRC_PLUTO` | 2,246 | 0.21 % |
| `SRC_NONE` — no year in any source | 7,829 | 0.72 % |

The 7,829 with no year are flagged clear of `YEAR_REAL` and the facade rules fall back to the building
class alone for them.

### 3.4 Ground elevation

| Source | Buildings | Share |
|---|---|---|
| `SRC_LIDAR` — `ground_elevation` from the footprint dataset | 1,082,459 | 99.95 % |
| `SRC_BSIN` — `z_grade` from Building Elevation and Subgrade | 374 | 0.03 % |
| `SRC_NEIGHBOURS` | 193 | 0.02 % |

### 3.5 Facade heading

The primary facade heading decides which side of a building the kit dresses as the front. It is derived
geometrically in every case — no source publishes it:

| Method | Buildings | Share |
|---|---|---|
| `HEADING_FREE_EDGE_LOT` — longest non-party-wall edge, tie-broken by lot position | 957,274 | 88.39 % |
| `HEADING_FREE_EDGE` — longest non-party-wall edge, no lot centroid available | 125,540 | 11.59 % |
| `HEADING_LONGEST_EDGE` — no free edge ≥ 2 m, so the longest edge of the ring | 212 | 0.02 % |

The 212 in the last row are buildings entirely enclosed by neighbours; the chosen heading for them is
arbitrary in the sense that no elevation of the building is actually visible from a street.

### 3.6 Joins and attachments

| | Buildings | Share |
|---|---|---|
| Joined to a PLUTO lot | 1,082,623 | 99.96 % |
| Primary building on its lot | 817,171 | 75.45 % |
| Has a subgrade record | 243,278 | 22.46 % |
| Has at least one storefront | 80,261 | 7.41 % |
| Under an active sidewalk shed | 6,396 | 0.59 % |

The PLUTO join at 99.96 % is the load-bearing one: land use, building class and lot geometry all come
through it, and 403 buildings that miss it fall back to class defaults throughout.

Note the difference between `has_storefront` (80,261 buildings, 7.41 %) and the `SIGNAGE_REAL` bit
(30,381 buildings, 2.81 %) reported in the fidelity report. A building has a storefront if the data says a
ground-floor commercial use exists there; it earns `SIGNAGE_REAL` only if a **real business name** was
attached to it. The other 49,880 get a storefront with no real name on it, and that is an inference.

## 4. What is measured about every building

Footprint geometry is real for **100 %** of the table — every polygon is the published photogrammetric
outline, none is a generated rectangle. Together with height that gives:

* footprint and height both from measurement: **99.93 %**
* footprint real, height inferred: 0.07 %

That is the strongest claim this project makes, and it is the one most firmly supported: the mass and
position of the city are measured, not modelled.

## 5. What is not

Stated plainly, because the brief asks for the deviations and not only the achievements:

1. **26.60 % of floor counts are derived from height.** §3.2.
2. **Facade heading is derived for 100 % of buildings.** §3.5. No source publishes which side is the front.
3. **Facade appearance is inferred for 96.69 % of buildings** — see `docs/verification/facade/REPORT.md` and
   ADR-004. Only 3.31 % carry a material from a real source (an OSM tag or an LPC designation report).
4. **52.43 % of roofs are inferred** from building class and footprint rather than taken from LOD2 geometry
   — see `docs/verification/citygml/REPORT.md` and ADR-013.
5. **Multi-part complexes are one row.** A BIN is one row here even where the real structure is several
   connected masses at different heights; the LOD2 stage recovers some of that, the base table does not.
6. **Interiors do not exist.** Every building is a shell. Nothing in this table describes anything inside.

## 6. Verification

`pipeline/tests/test_buildings.py` and the cross-cutting `tests/test_world_integration.py` check this table
directly. The checks that would catch a fabricated table, rather than merely a malformed one:

| Check | What it would catch |
|---|---|
| `test_every_building_sits_inside_the_tile_it_is_assigned_to` | a footprint written to the wrong tile, which would make it unreachable at runtime |
| `test_building_heights_are_physically_plausible` | a height column that is floors, feet, or a placeholder |
| `test_borough_building_counts_match_the_borough_summary` | rows lost or duplicated in the join |
| `test_landmark_footprints_resolve_to_real_buildings` | a landmark id pointing at no building |
| `test_fidelity_report_counts_every_bit_from_the_stage_that_sets_it` | a provenance bit reported from a table that never sets it |

The last of those exists because that failure did occur: the fidelity report counted four bits in this table
that this stage does not set, and reported 0 % inferred facades and 0 % inferred roofs when the real figures
are 96.69 % and 52.43 %. The data was correct; the report was reading the wrong file. Fixed in 9d6e631.
