# Facade classification and kit placement — verification report

**Stage** `pipeline/nycsim_pipeline/facade/` · **rules version** `facade-rules/1` · **run** 2026-09-06, full city,
1,083,026 buildings, 920 tiles.

This is the stage that decides how every building in New York looks. **ADR-004 governs it**: appearance is inferred
from real per-building attributes by a versioned, auditable rule set, and every building whose material has no real
source carries `FACADE_INFERRED`. The headline number is in §6: **96.7 % of the city's facades are inferred.** That is
the single largest fidelity gap in the project and it is stated here as such, not smoothed over.

---

## 1. What was built

| file | what it is |
|---|---|
| `facade/rules.py` | the classifier: **101 ordered, named predicates** over real attributes → `facade_class` |
| `facade/enums.py` | bridge to `blender/common/facade_params.py` + `facade_classes.json`; bay spacing; OSM/LPC material mapping; the deterministic hash |
| `facade/edges.py` | merged facade runs, party-wall detection, street-facing classification against CSCL centrelines |
| `facade/derive.py` | window grid, materials, water towers, fire escapes, stoops, rooftop plant, awning text |
| `facade/roofs.py` | roof **shape** for the pitched-roof house stock (ADR-013), fidelity bit 13 |
| `facade/kit_ids.py` | kit id registry **derived from the exported Blender catalog**; semantic role → catalog id |
| `facade/osm_match.py` | OSM ↔ BIN match by largest footprint IoU |
| `facade/placements.py` | the placement generator and the 40-byte DATA_CONTRACTS §6 writer |
| `facade/schema.py` | the §5.4 extension schema (appended to `docs/DATA_CONTRACTS.md`) |
| `facade/build.py` | the three-pass driver (`geom`, `rules`, `emit`, `all`) |
| `facade/apply_roofs.py` | re-runnable merge of `buildings/roof_attrs.parquet` after the fact |
| `facade/validate_placements.py` | structural + geometric validation and the kit-catalog reconciliation |
| `pipeline/tests/test_facade.py` | **36 tests** — schema, coverage, determinism, placement sanity, typology spot checks |
| `docs/verification/facade/rules_table.md` | the full rule table with hit counts, dumped by the stage on every run |
| `docs/verification/facade/placement_validation.json` | the per-tile validation result for all 920 tiles |

Outputs on disk:

| artefact | contents |
|---|---|
| `tiles/{tile}/buildings.parquet` × 920 | complete DATA_CONTRACTS §5 schema + §5.2 + §5.4, 1,083,026 rows total |
| `tiles/{tile}/kit_placements.bin` + `.json` × 920 | **42,068,609 records, 1,682,744,360 bytes (1.68 GB)** |
| `facade/facade_attrs.parquet` | 1,083,026 rows, the whole-city facade attribute table |
| `facade/geom_attrs.parquet` | 1,083,026 rows, footprint geometry summary |
| `facade/kit_ids.json`, `facade/kit_catalog_map.json` | the kit id registry and the `kit_id → catalog_id → .glb` map |
| `facade/{rules_summary,emit_summary,run_summary}.json` | every number this report quotes, machine-readable |

Run with `python -m nycsim_pipeline.facade.build all` (or the three passes separately). Everything is idempotent; the
emit pass rebuilds the edge cache by itself when it needs it.

---

## 2. How the classifier works

**101 ordered rules; the first match wins; the last rule matches unconditionally.** Each rule carries a stable name, a
human-readable predicate, the `facade_class` it assigns and a rationale stating the NYC typology or legal fact it
encodes. The whole table with hit counts is dumped to `rules_table.md` on every run, and the index of the rule that
classified each building is written to the data as `facade_rule` — so **every facade in the city is traceable to a
named predicate**.

The rules read only *real* attributes: MapPLUTO `bldgclass` / `yearbuilt` / `numfloors` / `bldgfront`, the OTI
planimetric `feature_code` and footprint area, the LPC designation-report `STYLE1` and `MATERIAL1`, the LPC historic
district polygon, the NTA 2020 code, the footprint-derived party-wall count and corner flag, and the OSM
`building:material` tag.

The typology and the legal history it encodes:

* **Old Law tenement** (1879 Tenement House Act – 1901): PLUTO class `C4` *is* "old law tenement"; 25 × 100 ft lot,
  dumbbell plan with an air shaft, five to six storeys, red brick, segmental-arched heads, iron fire escape on the
  street face (compulsory for multiple dwellings since the 1867 Act). **6,643 buildings.**
* **New Law tenement** (1901 – 1929): wider lot, interior courts, buff/tan brick with limestone trim, pressed-metal
  dentil cornice. **34,333 buildings** — the largest class in Manhattan at 22.0 % of the borough.
* **Brownstone and limestone rowhouses** (1845 – 1915): high stoop over an English basement, bracketed cornice, 20 ft
  lot; Greek Revival (1830-55) and Federal (1790-1840) predecessors in brick with a dormered pitched roof.
  **23,991 buildings** across classes 3–7.
* **Prewar apartment houses** (1915 – 1940) under the 1916 Zoning Resolution's setback envelope; Beaux-Arts
  (1898-1918) limestone piles; **Art Deco** (1928-42) on the Grand Concourse and the Brooklyn boulevards.
* **Postwar** (1945 – 1975): red-brick six-storey elevator houses, Manhattan white-glazed-brick towers, and **NYCHA**
  campuses recognised by the real superblock signature — six-plus floors, three or more buildings on one very large tax
  lot, 1935-75.
* **1961 Zoning Resolution** plaza-bonus glass towers (1962-88), 1980s brown brick, 2000s+ curtain wall, supertalls.
* **SoHo cast iron** and Tribeca store-and-loft buildings, driven by the LPC historic-district polygon and the
  designation-report material — the most precise evidence anywhere in the table.
* **Industrial lofts, daylight factories, warehouses, self-storage, big-box retail, taxpayers and corner bodegas,
  garages, gas stations, schools, churches, hospitals, firehouses, hotels and elevated transit structures.**
* **Outer-borough house stock**, where PLUTO's own semantics do the work: **`B1` is a two-family *brick* house and
  `B2` is a two-family *frame* house**, `A5` is attached or semi-detached and `A1`/`A2` are detached. The material and
  attachment evidence is therefore real, not guessed.

### Window counts come from real geometry

`window_cols = round(frontage / the bay width of the class's window family)`. The frontage is MapPLUTO's surveyed
`bldgfront` (present for 1,060,009 of 1,083,026 buildings) and falls back to the longest street-facing non-party-wall
footprint run. Bay widths are the published NYC lot modules: a 25 ft (7.62 m) tenement lot carries **4** window bays
(1.90 m), a 20 ft (6.10 m) brownstone lot carries **3** (2.03 m), a 1920s prewar casement bay is 8 ft (2.44 m), a
unitised curtain wall uses the 5 ft (1.52 m) module. `window_rows = floors − 1`: the ground floor is consumed by the
ground-floor treatment (storefront, stoop and entrance, garage or lobby), which is placed separately.

Verified by `test_window_grid_follows_real_geometry`: the four canonical cases produce exactly 4, 3, 12 and 46 bays.

---

## 3. Rule table and hit counts

The complete table — all 101 rules with predicates, rationales and hit counts — is in
[`rules_table.md`](rules_table.md). **Every rule fired at least once; no rule is dead.** The fourteen largest:

| rule | buildings | share |
|---|--:|--:|
| `accessory_garage` | 213,451 | 19.71 % |
| `rowhouse_brick_1920` | 125,942 | 11.63 % |
| `queens_vinyl_2fam` | 122,958 | 11.35 % |
| `brick_house_postwar` | 66,805 | 6.17 % |
| `house_brick_prewar` | 60,554 | 5.59 % |
| `brooklyn_frame_rowhouse` | 51,408 | 4.75 % |
| `house_frame_prewar` | 51,249 | 4.73 % |
| `queens_brick_2fam` | 33,933 | 3.13 % |
| `si_qn_single_family_siding` | 33,520 | 3.10 % |
| `fallback_low_postwar` | 30,984 | 2.86 % |
| `fallback_small_masonry` | 25,553 | 2.36 % |
| `fedders_special` | 19,306 | 1.78 % |
| `fallback_low_prewar_masonry` | 16,762 | 1.55 % |
| `bushwick_frame_3fl` | 16,414 | 1.52 % |

The twelve fallback rules at the end of the table claim **93,538 buildings, 8.64 % of the city** — those are
classified by era, height and borough alone because their PLUTO class carried no more specific signal. The other
91.4 % were claimed by a rule that names a real typology.

---

## 4. Class and material distribution

All **56 of 56** facade classes are used; none is unused.

### Overall class distribution (top 20 of 56; the full list is in `rules_summary.json`)

| # | class | buildings | share |
|--:|---|--:|--:|
| 38 | `parking_garage_concrete` | 215,904 | 19.94 % |
| 34 | `rowhouse_brick_1920_2fl_flat_roof` | 212,049 | 19.58 % |
| 27 | `queens_vinyl_2fam_1950` | 122,958 | 11.35 % |
| 31 | `brooklyn_frame_rowhouse_1900_siding` | 105,349 | 9.73 % |
| 28 | `queens_brick_2fam_1930` | 100,738 | 9.30 % |
| 30 | `staten_island_sf_1970_siding` | 61,263 | 5.66 % |
| 12 | `postwar_red_brick_1950_6fl_elevator` | 39,814 | 3.68 % |
| 2 | `tenement_1905_new_law_6fl` | 34,333 | 3.17 % |
| 33 | `fedders_special_2005` | 22,462 | 2.07 % |
| 37 | `bodega_corner_taxpayer_1_2fl` | 19,261 | 1.78 % |
| 32 | `bushwick_frame_3fl_1900` | 16,414 | 1.52 % |
| 51 | `garden_apt_1940_brick_2fl` | 13,454 | 1.24 % |
| 29 | `queens_tudor_1930` | 12,671 | 1.17 % |
| 5 | `limestone_rowhouse_1900_4fl_bowfront` | 12,523 | 1.16 % |
| 22 | `warehouse_concrete_1950` | 11,732 | 1.08 % |
| 10 | `bronx_art_deco_apt_1935` | 9,603 | 0.89 % |
| 3 | `brownstone_rowhouse_1880_4fl_stoop` | 7,349 | 0.68 % |
| 1 | `tenement_1880_brick_5fl_fire_escape` | 6,643 | 0.61 % |
| 36 | `church_brick_romanesque_1890` | 5,460 | 0.50 % |
| 54 | `brown_brick_office_1985_midrise` | 5,068 | 0.47 % |

**215,904 buildings (19.9 %) carry class 38 — of which 213,451 are one-storey accessory garages** (OTI feature code
5110), not multi-storey parking decks. See gap **G-2**.

### Top classes per borough

* **Manhattan** (45,194): `tenement_1905_new_law_6fl` 22.0 %, `tenement_1880_brick_5fl_fire_escape` 11.0 %,
  `prewar_apt_1925_brick_limestone_6_12fl` 6.9 %, `brownstone_rowhouse_1880_4fl_stoop` 6.0 %,
  `postwar_red_brick_1950_6fl_elevator` 5.8 %.
* **Bronx** (104,278): `rowhouse_brick_1920_2fl_flat_roof` 22.1 %, `parking_garage_concrete` 14.8 %,
  `queens_brick_2fam_1930` 13.1 %, `queens_vinyl_2fam_1950` 9.7 %, `brooklyn_frame_rowhouse_1900_siding` 8.4 %.
* **Brooklyn** (330,154): `rowhouse_brick_1920_2fl_flat_roof` 28.7 %, `parking_garage_concrete` 16.9 %,
  `brooklyn_frame_rowhouse_1900_siding` 10.2 %, `queens_brick_2fam_1930` 7.7 %.
* **Queens** (460,939): `parking_garage_concrete` 27.5 %, `rowhouse_brick_1920_2fl_flat_roof` 18.3 %,
  `queens_vinyl_2fam_1950` 13.5 %, `brooklyn_frame_rowhouse_1900_siding` 10.5 %.
* **Staten Island** (142,461): `queens_vinyl_2fam_1950` 26.6 %, `staten_island_sf_1970_siding` 19.7 %,
  `queens_brick_2fam_1930` 19.0 %, `parking_garage_concrete` 12.1 %.

### Material distribution

| material | buildings | share |
|---|--:|--:|
| vinyl siding | 365,078 | 33.71 % |
| red brick | 338,113 | 31.22 % |
| tan brick | 279,147 | 25.78 % |
| concrete | 36,877 | 3.41 % |
| limestone | 18,636 | 1.72 % |
| stucco | 12,835 | 1.19 % |
| brownstone | 7,840 | 0.72 % |
| glass curtain | 6,582 | 0.61 % |
| brown brick | 5,330 | 0.49 % |
| metal panel | 4,663 | 0.43 % |
| wood clapboard | 2,828 | 0.26 % |
| stone rubble | 2,564 | 0.24 % |
| precast | 1,161 | 0.11 % |
| terracotta | 526 | 0.05 % |
| white glazed brick | 372 | 0.03 % |
| cast iron | 343 | 0.03 % |
| granite | 131 | 0.01 % |

Brick of all shades: **623,335 buildings, 57.6 %** — the right order for New York.

### Material per borough (% of that borough)

| borough | red brick | tan brick | vinyl siding | limestone | brownstone | glass curtain | concrete | stucco |
|---|--:|--:|--:|--:|--:|--:|--:|--:|
| Manhattan | 42.7 | 28.6 | 0.5 | 6.9 | 5.2 | 4.6 | 1.5 | 0.7 |
| Bronx | 33.7 | 34.5 | 22.2 | 2.3 | 0.0 | 1.0 | 3.9 | 0.7 |
| Brooklyn | 30.0 | 37.1 | 23.6 | 3.5 | 1.7 | 0.7 | 1.9 | 0.1 |
| Queens | 31.4 | 21.2 | 38.9 | 0.3 | 0.0 | 0.2 | 4.6 | 2.4 |
| Staten Island | 28.1 | 7.1 | 59.5 | 0.2 | 0.0 | 0.1 | 3.2 | 0.5 |

Manhattan is masonry with a curtain-wall fraction, Staten Island is 60 % sided frame, Brooklyn and the Bronx split
between red and tan brick. That is the real profile of the city.

---

## 5. `MATERIAL_REAL` from OSM and LPC (ADR-004's override sources)

| source | buildings | share of the city |
|---|--:|--:|
| OSM `building:material` tag | 1,717 | 0.159 % |
| OSM `building:colour` (shade refinement of a masonry wall) | 412 | 0.038 % |
| LPC designation-report `MATERIAL1` | 33,689 | 3.110 % |
| **total `MATERIAL_REAL` (fidelity bit 5)** | **35,818** | **3.307 %** |
| rule-derived → `FACADE_INFERRED` (bit 10) | 1,047,208 | 96.693 % |

The OSM **match** is excellent — **1,061,220 of 1,083,026 buildings (98.0 %)** matched an OSM building by largest
footprint IoU (≥ 0.30, one-to-one, greedy by descending IoU with deterministic tie-breaking), and their `osm_id` is now
written into the §5 column the buildings stage left at 0. The problem is the **tags**: of 1,247,724 OSM buildings in
NYC only **1,829 carry `building:material`** and **2,381 carry `building:colour`**. NYC's OSM building layer is a bulk
import of the city footprint file — it has geometry, not cladding.

Precedence (ADR-004, refined and documented in §5.4): an explicit `building:material` tag > an LPC `MATERIAL1` > an
OSM `building:colour`, and a colour only ever refines the *shade* of a masonry wall the rule or the LPC report already
settled on. A colour is a statement about hue, not about material family.

`MATERIAL_REAL` per borough: Manhattan 14,746 (32.6 % of the borough), Brooklyn 15,303 (4.6 %), Queens 4,390 (1.0 %),
Bronx 978 (0.9 %), Staten Island 401 (0.3 %) — it tracks the LPC historic districts exactly, as it must.

---

## 6. The ADR-004 fidelity gap, stated explicitly

> **1,047,208 of 1,083,026 buildings — 96.7 % of New York City — have a facade whose material, window pattern, trim
> and features were produced by the rule table in `rules.py`, not observed.** Every one of them carries fidelity bit 10
> `FACADE_INFERRED`. Only **35,818 buildings (3.3 %)** have a material from a real source, and of those only **2,129
> (0.20 %)** come from OSM tags; the rest come from LPC designation reports, which name one coarse material string per
> building ("Brick", "Brownstone", "Wood Frame").

Per building, what is real and what is not:

| attribute | real | inferred |
|---|---|---|
| footprint, height, ground elevation, floors, year, address | ✔ (buildings stage) | |
| roof massing and setback levels | ✔ 1,033,416 (95.4 %) `ROOF_REAL` | |
| storefront presence and business names | ✔ 80,261 storefronts, 30,381 real names | 49,880 use generic NYC awning wording |
| scaffolding | ✔ 6,396 active DOB sidewalk-shed permits | |
| frontage (window bay count) | ✔ MapPLUTO `bldgfront`, 97.9 % | |
| first-floor offset (stoop evidence) | ✔ 855,643 surveyed | |
| **material** | 35,818 (3.3 %) | **1,047,208 (96.7 %)** |
| **window family, trim, cornice style, features** | — | **1,083,026 (100 %)** |
| **roof shape** | 4,092 (0.4 %) | 567,800 pitched by rule + 511,134 default flat |

The gap cannot be closed in this environment: there is no lawful, feasible source of per-building street-level imagery
for 1.08 M buildings here. Closing it needs street-level imagery plus a vision model classifying material, window
pattern and storefront per facade. The rule table is deliberately shaped so such a source would replace the
`material_source == 3` rows without touching the contract.

**What the inference is worth anyway.** It is not random. It keys on the strongest real signals New York offers —
PLUTO's class letter (which encodes brick vs frame and attached vs detached *by definition*), the year built read
against the tenement acts and the zoning resolutions, the LPC historic-district boundary and designation style, the
NTA, and the footprint's own party walls. The per-borough profiles in §4 and the feature counts in §7 are the profiles
of the real city, and the typology spot checks in §10 land on the right buildings by address.

---

## 7. Features: fire escapes, stoops, cornices, water towers

| feature | buildings | rule |
|---|--:|---|
| fire escapes | **54,900** | class feature ∧ floors ≥ 3 ∧ 1800 < year ≤ 1968 (the 1968 Building Code replaced the fire escape with two enclosed stairs) ∧ ≥ 1 free facade ∧ never a one- or two-family house ∧ never Staten Island below five storeys |
| stoops | **614,527** | class feature ∨ (residential ∧ surveyed first-floor offset ≥ 0.75 m) ∧ not a storefront ∧ ≤ 8 floors |
| cornices | **208,710** | class `cornice` feature ∧ ≥ 1 free facade |
| water towers | **21,233** | see below |
| rooftop units | **473,849** items | bulkheads, HVAC, vents and antennas from class features, floors and roof area |
| corner lots | **108,769** (10.0 %) | two street-facing free runs ≥ 4 m, normals 60–120° apart, nearest centrelines on two *different* CSCL segments |
| attached (party wall) | **647,506** (59.8 %) | real footprint adjacency |

Fire escapes per borough: **Manhattan 18,812 · Brooklyn 23,365 · Queens 6,436 · Bronx 6,274 · Staten Island 13.**
Thirteen in Staten Island, all five-storey-plus multiple dwellings — the borough has essentially no tenement stock —
and a Queens single-family house never gets one (asserted over 130,000+ of them by
`test_a_queens_single_family_house_never_gets_a_fire_escape`).

### Water towers, cross-checked against the published figure

NYC street mains pressurise roughly six storeys; anything taller needs a gravity tank or a booster. The rule is
**floors ≥ 6 ∧ 1850 < year ≤ 1989 ∧ roof area ≥ 150 m² ∧ not a class with no habitable water demand** (glass office
towers, garages, warehouses, big boxes, gas stations, transit structures).

| | count |
|---|--:|
| eligible — physically needs a tank | **21,233** |
| of which **wooden gravity tanks** (year ≤ 1949) | **15,025** (13,037 × 10,000 gal + 1,988 × 20,000 gal) |
| of which steel / enclosed (1950-1989) | 6,208 |

**The wooden-tank count, 15,025, sits inside the widely cited 10,000–17,000 range for New York City**, and
`test_water_tower_count_is_inside_the_published_range` asserts it. The split is physical rather than fitted: wooden
gravity tanks are the pre-1950 norm and the published figure counts the wooden tanks the tank companies maintain,
while 1950-1989 buildings increasingly use an enclosed steel tank in a bulkhead or a basement booster — which is why
they carry a different `water_tower_kind` and a different kit piece. Sensitivity to the roof-area threshold: 21,233 at
150 m², 20,082 at 200 m², 18,059 at 300 m². Per borough: Manhattan 11,529, Brooklyn 3,755, Bronx 3,186, Queens 2,608,
Staten Island 155.

---

## 8. Roof shape (ADR-013, fidelity bit 13)

ADR-013 established that the CityGML LOD2 model is stepped **flat massing** — real roof heights and setback levels, no
roof pitch — and assigned the roof **shape** of the pitched-roof house stock to this stage. Precedence, recorded per
row in `roof_source`:

1. a real source — CityGML (55 hand-modelled landmarks) or an OSM `roof:shape` tag (4,037) — always wins;
2. otherwise, for PLUTO A0–A9 / B1–B9 / C0 / detached S-class / R1–R6 houses of at most four floors whose facade class
   declares a pitched roof, **or** which are free-standing with a side yard, footprint short side ≤ 14 m, ≤ 3 floors
   and ≤ 400 m² (the ADR-013 geometric test), **or** whose LPC designation names Second Empire or a mansard, this
   stage derives the shape — **567,800 buildings, fidelity bit 13 `ROOF_INFERRED`**;
3. otherwise flat — 511,134.

Shape rule: an accessory garage or a one-storey outbuilding under 80 m² → **shed**; an LPC Second Empire / mansard
designation → **mansard**; free-standing and squarish (aspect < 1.4) or a tile-roof class → **hip**; everything else →
**gable with the ridge along the long axis** (the NYC attached and semi-detached house presents a gable end to the
street). Pitch is the era norm: 38° pre-1900 and for Tudor / Queen Anne / Victorian designations, 30° for 1900-1944,
22° post-1945, 10° for a shed, 65° for a mansard's lower slope. **The measured `roof_z` is kept as the ridge height**
and `roof_eave_z` drops below it by the rise the pitch and the footprint's short side imply, so the building's overall
height stays exactly what the LiDAR measured.

| roof type | buildings |
|---|--:|
| 0 flat | 514,751 |
| 1 gable | 309,498 |
| 2 hip | 47,271 |
| 3 mansard | 219 |
| 4 shed | 211,243 |
| 6 complex (CityGML mesh) / 7 dome / 8 barrel | 28 / 8 / 8 |

Pitched share per borough: **Manhattan 1.9 % · Bronx 46.2 % · Brooklyn 32.2 % · Queens 67.0 % · Staten Island 72.9 %.**
ADR-013 predicted the profile (MN 0.5 %, BX 33 %, BK 25 %, QN 58 %, SI 72 %); the curve matches, and this stage's
numbers run higher because they include the 211,243 shed roofs on accessory garages that ADR-013's own inference left
flat. `ROOF_REAL` (bit 2 — the measured LOD2 massing) is set on **1,033,416 buildings, 95.4 %**, straight from
`citygml_match`; this stage never touches that bit's meaning.

`apply_roofs.py` re-derives all of the above from a later `buildings/roof_attrs.parquet` without re-running the
classifier or the placements, so a CityGML re-run is merged with one command.

---

## 9. Kit placements (DATA_CONTRACTS §6)

**42,068,609 records across 920 tiles, 1,682,744,360 bytes, 38.84 placements per building.** Every file is a whole
number of 40-byte little-endian records sorted by `(bin, kit_id)`, with a `.json` header carrying the count, byte
length, SHA-256 of the binary, field layout, the angle and scale conventions and the list of kit ids used.

### Kit ids resolve to real assets

The numbering is derived **from the exported Blender kit catalog**, not from an assumed name list:
`kit_id = (category index in facade_params.KIT_CATEGORIES + 1) × 200 + index of the catalog id inside that category`,
catalog ids sorted lexicographically. All **138 exported catalog entries** are registered in `facade/kit_ids.json`
with their `catalog_id`, `glb` path, nominal size and the placement roles that use them; `kit_catalog_map.json` is the
same map for the UE importer. The placer refers to pieces by **semantic role** — `("door_entry",
"stoop_high_brownstone")` → `entry_stoop_brownstone_10` — so a rename on the kit side is a one-line change; a role the
kit does not export raises rather than emitting an id that resolves to nothing, and `write_tile` bounds-checks every
id against the registry before writing. **85 of the 138 exported pieces are placed**; the other 53 are listed in
`placement_validation.json` — see gap **G-5**. The stage also survives the kit being re-exported mid-run: when
`blender_out/kit/catalog` is temporarily absent it falls back to the registry it last wrote, so ids never drift.

### What is placed, and where

* **Windows** on every non-party-wall facade run ≥ 2.2 m, at the class's real bay spacing and at real floor heights
  (`ground_z + ground_floor_height + (f−1) × floor_height + sill`). A party wall is shared masonry and carries nothing
  — asserted by `test_no_placement_on_a_party_wall`.
* **Window air-conditioners** on 18 % of residential upper-floor windows (deterministic from `lit_seed`), and a
  through-wall sleeve under every window of the classes whose typology has one (the 2000s "Fedders special", the
  post-war slabs, the white-brick towers).
* **Fire escapes** on the street facade only: one balcony per storey, a drop ladder at the lowest, the top balcony
  piece and a roof hook above.
* **Stoops** at the entrance bay — high brownstone, low brick or wooden by material and by the surveyed first-floor
  offset — with the areaway railing of the classes that have one.
* **Cornices** at the roofline of the street facade in the class's cornice style; **parapets** on the other free runs
  of flat-roofed buildings; **string courses**, **quoins**, **pilasters/columns** and **entrance canopies** for the
  classes whose typology declares them.
* **Storefronts** along the ground floor of street-facing commercial frontage: a glazed bay per 4.8 m in the three
  widths the kit exports, a sign band, an awning on 60 % of the bays of the classes that have one, a roll-down gate on
  55 % (flagged animated so the runtime lowers it at night), an entrance door, and one interior shell per shopfront
  chosen from the building's real storefront kind.
* **Water towers, bulkheads, HVAC, vents and cell antennas** on the roof at points tested to lie inside the real
  footprint; **brick chimneys** on the pitched-roof house stock.
* **Sidewalk sheds** on the street facade of the buildings with an active DOB permit, capped at both ends.

Facade classification uses the real street geometry: with `roads/segments.parquet` present (**106,635 street
centrelines**), a run is street-facing when its outward probe point is within 20 m of a street centreline, and the
nearest `physicalid` is written to `street_segment_id`. **2,194,710 of 5,835,555 usable runs are street-facing, and
all 2,194,710 matched a CSCL segment.** Without the roads file the stage falls back to the buildings stage's real
`primary_facade_heading` — implemented, tested and logged as the degraded path.

### Composition of the 42.1 M records

windows 74 % · window accessories (AC units and sleeves) 10 % · parapets 4 % · doors, stoops and garage doors 4 % ·
storefronts and their interiors 2.5 % · cornices 1.2 % · bulkheads 0.9 % · fire escapes 0.7 % · sidewalk sheds 0.5 % ·
railings, string courses, quoins, pilasters, canopies, ivy, chimneys, water towers and antennas the remainder.

### Determinism

Everything is a deterministic function of `lit_seed` and the inputs.
`test_placements_are_reproducible_byte_for_byte` regenerates two whole tiles from `buildings_base.parquet` +
`facade_attrs.parquet` + the road centrelines, with **no cached intermediate**, and asserts the bytes are identical to
the files on disk, and identical between two runs. They are.

---

## 10. Verification

### Commands run and their results

```
python -m nycsim_pipeline.facade.build geom     1,083,026 buildings, 82 blocks, 252 s, peak RSS 942 MB
                                                6,372,757 facade runs; 1,032,018 party walls; 2,194,710 street-facing
                                                647,506 attached buildings; 108,769 corner lots; 160 with no free run
python -m nycsim_pipeline.facade.build rules    1,083,026 classified, 0 unclassified, 101 rules, 56/56 classes,
                                                378 s, peak RSS 1,902 MB, MATERIAL_REAL 35,818
python -m nycsim_pipeline.facade.build emit     920 tiles, 42,068,609 placements, 1,682,744,360 bytes, 452 s,
                                                peak RSS 1,152 MB, 920/920 tiles schema-validated, 0 problems
python -m nycsim_pipeline.facade.validate_placements
                                                920 tiles checked, 0 with problems, 85 distinct kit ids, all registered
PYTHONPATH=pipeline pytest pipeline/tests/test_facade.py -q            36 passed
PYTHONPATH=pipeline pytest tests/test_world_integration.py -k kit_placements   1 passed
```

Total wall time for the full city: **about 18 minutes** on the shared 4-vCPU box, peak RSS 1.9 GB — inside the 5 GB
budget. The stage runs `nice -n 10` and processes the city in 4 × 4 km blocks, so memory does not scale with the city.

### What the tests assert

`pipeline/tests/test_facade.py` — **36 tests, all passing**:

* **Schema** — every sampled tile passes `contracts.validate_parquet("buildings", …)`; the buildings stage's own
  columns and its `geo` / `nycsim.schema` / `nycsim.tile` metadata survive the rewrite; every appended column has the
  declared type.
* **Rule coverage** — no building without a `facade_class`; `facade_rule` and `facade_class` agree on every one of the
  1,083,026 rows; the table is exhaustive on synthetic input; no duplicate names; every rule carries a rationale.
* **Determinism** — two tiles regenerated from scratch are byte-identical to the files on disk and to each other.
* **Placement sanity** — every placement lies inside its own building's footprint bounding box + 2 m and between the
  building's ground − 1.5 m and roof + 16 m; `window_rows ≤ floors`; storefront pieces only where `has_storefront`;
  no facade piece on a party wall; `n_placements` sums to the file's record count; every header's count, byte length
  and SHA-256 match its file.
* **Kit registry** — every id comes from the exported catalog, is unique and sits in its category's block; every
  placement role resolves to a piece that exists.
* **Typology spot checks by address** — Park Slope Historic District rowhouses get a rowhouse class (> 80 %), a
  masonry material (> 95 %) and a stoop (> 70 %); **15 Central Park West** is never given vinyl siding or clapboard;
  a **Bushwick warehouse** gets an industrial class (> 85 %) and a pre-1940 one gets brick, not poured concrete; the
  **Empire State Building** gets `limestone_office_1930_art_deco_setback` and a water tower; the **SoHo-Cast Iron
  Historic District** gets the cast-iron class (> 60 %) with fire escapes; a **Queens single-family house** never gets
  a fire escape; Manhattan is not a frame-house borough and Staten Island is.
* **Physical rules** — the bay counts for the four canonical NYC lot modules; the water-tank floor and era thresholds;
  the wooden-tank count inside the published range; ADR-004's material precedence; the roof rule pitching only the
  house stock and keeping the eave at or below the measured roof.

---

## 11. Gaps and decisions, stated

**G-1 — the ADR-004 gap (the big one).** 96.7 % of facades are inferred. Quantified in §6. Not closable in this
environment.

**G-2 — accessory garages have no class of their own.** 213,451 one-storey backyard garages (OTI feature code 5110,
19.7 % of all footprints) are assigned `facade_class 38 parking_garage_concrete`, the only garage typology in
`facade_classes.json`, because a garage is what they are — but that class describes a multi-storey concrete parking
deck. Their *material* is overridden from the lot's own real evidence (a PLUTO `B2` frame lot or a frame-belt NTA →
vinyl siding; pre-1946 → red brick; otherwise concrete) and their roof is a shed, so the shells read correctly. The
clean fix is a class 57 `accessory_garage_1fl` in `facade_classes.json` — **proposed to the kit agent, not made here**:
`blender/**` is not this lane. Until then the class distribution has a 19.9 % bar that is really two different things,
and it is labelled as such everywhere in this report.

**G-3 — LPC `MATERIAL1` is coarser than the building.** It names one string per building. For the Empire State
Building it says "Brick", where the real cladding is Indiana limestone with granite and aluminium; ADR-004 makes that
string outrank the class default, so the tower comes out brick-toned. This affects a small number of individually
designated landmarks and is the correct behaviour under the ADR — a real source outranks a rule — but the source is
blunt. Landmarks with hand-scripted models (`landmark_model`, fidelity bit 7) bypass the shell and are unaffected.

**G-4 — the kit has no 2000s stone-clad residential tower.** 15 Central Park West and its imitators are limestone;
the nearest class is 50 `condo_midrise_2010_glass_brick`. They get a residential condo class with glass-and-brick
cladding rather than an industrial or frame class (the test asserts they never get siding), but the limestone is not
there. A class 58 `condo_tower_2005_limestone` would fix it.

**G-5 — 54 of the 174 exported kit pieces are never placed.** They are detail pieces the placer does not yet call
for: window guards and blinds, curtains, most trim profiles (keystones, water tables, datestones, corner beads), the
half/closed roll-gate and grille states (the runtime animates the open one instead), `parapet_balustrade`,
`fire_escape_corner_return`, `hvac_condenser_bank`, the antenna variants and one ivy panel. Adding them is placement
policy, not new geometry. One of the 54 is a sign band: `storefront_sign_band_hardware` is unplaced because the string
"HARDWARE" never occurs in `awning_text` anywhere in the city — no facade class lists `hardware` among its typical
storefront kinds and no licence matched one.

*Superseded, 2026-09-07 (§14).* This entry previously read "53 of the 138 exported kit pieces" and said that **both
billboards are deliberately not placed** because "there is no real source of NYC billboard locations in this
environment". The second half of that was too broad and is corrected in §14: the *content* of a bulletin still has no
source and is still left blank, but the *presence* of one is inferred from the `billboard` typology feature of the
building's own `facade_class`, which is the same ADR-004 mechanism every other class feature uses. Both billboards
are now placed, with blank faces.

**G-6 — placements are 1.68 GB, not the "< 1 GB" ADR-003 estimated.** 42,068,609 records × 40 bytes. That estimate
predates the placement policy; 38.8 pieces per building is *modest* for New York (a five-storey tenement with two free
facades carries about 40 windows alone) and 74 % of the volume is windows. If the disk budget binds, the levers in
order of cost are: drop the window AC units (−10 %), place windows only on street-facing facades rather than all free
facades (−35 %, and visibly wrong from a side street), or reduce `MAX_BAYS_PER_RUN`. **Proposed correction to
ADR-003's storage line: "≈ 1.3 GB shells + ≈ 1.7 GB placements".**

**G-7 — awning text is generic where no business name is known.** 30,381 of 80,261 storefronts carry a real DCWP /
DOHMH / OSM business name (those buildings already have `SIGNAGE_REAL`, bit 6). The other 49,880 get the standard NYC
wording for their kind ("DELI GROCERY", "NAILS & SPA", "DRY CLEANERS"); 48,021 of those resolve to one of the fifteen
generic strings and 1,859 are empty (a lobby, a garage door, a vacant unit). The `awning_real` column marks which is
which, per building. As of §14 that text reaches geometry: a generic string is baked on the sign band, and a real name
is **not** — it gets a blank lit panel that the runtime fills from `awning_text` on the same `bin`.

**G-8 — corner and street-facing logic depends on the roads stage.** It ran with `roads/segments.parquet` present, so
both are derived from real CSCL centrelines. A rebuild that ran the facade stage before roads would fall back to
`primary_facade_heading`, and the corner flag would degrade to "two free perpendicular facades", which over-counts
(51 % instead of 10 % on a Brooklyn sample). The fallback is implemented and tested, but the numbers here are the
roads-present ones.

**G-9 — three tests in `pipeline/tests/test_buildings.py` now fail, and none of them is this stage.**
`test_schema_conformance` fails because `buildings_base.parquet` was rewritten at 12:19 by another stage through a
polars round-trip: `bldg_class` became `large_string` and the `nycsim.schema` metadata key was dropped.
`test_fidelity_bits` fails because that same rewrite set `ROOF_REAL` in `buildings_base`, which the buildings stage's
test asserts is owned by a later stage. `test_tile_files` fails on `assert len(idx) > 1000` against a
`tiles_index.json` that holds 920 tiles. The **per-tile** files this stage rewrites keep `bldg_class: string`, keep
`nycsim.schema = buildings/1`, `nycsim.tile` and the GeoParquet `geo` block, and are asserted to do so by
`test_tile_files_keep_the_buildings_stage_columns_and_metadata`. Flagged for the orchestrator, not touched.

---

## 12. What the next agent needs to know

* **Blender shell/kit agent** — `tiles/{tile}/buildings.parquet` carries the complete §5 schema plus §5.4.
  `facade_class` selects the typology from `blender/common/facade_classes.json`; `material_primary` /
  `material_secondary` are the §5 enum; `window_type` is the `facade_params.WINDOW_TYPES` index; `bay_width_m` is the
  spacing the placements actually used. For roofs use `roof_type` with `roof_pitch_deg`, `roof_ridge_heading` and
  `roof_eave_z` — **the ridge is at `roof_z`**, so extruding to `roof_eave_z` and raising the ridge back to `roof_z`
  keeps the measured height. `kit_placements.bin` is the instancing list; resolve `kit_id` through
  `data/processed/facade/kit_catalog_map.json`.
* **Kit agent** — two classes are missing from `facade_classes.json` (G-2, G-4) and 53 exported pieces are unused
  (G-5). The `ROLE_TO_CATALOG` table in `facade/kit_ids.py` is the contact surface: if a catalog id is renamed, that
  one table changes and the numbering follows automatically.
* **UE importer** — `kit_ids.json` / `kit_catalog_map.json` map `kit_id → catalog_id → .glb`; every tile's placement
  header repeats the record layout and the angle and scale conventions.
* **CityGML agent** — `apply_roofs.py` merges a later `roof_attrs.parquet` without re-running the classifier or the
  placements. This stage takes `roof_type` from sources 0 (CityGML) and 1 (OSM) only and owns the house-stock shape
  itself, per ADR-013 and the orchestrator's arbitration; source 2/3 rows are treated as "flat unless my rule fires".
* **Report / fidelity stage** — `facade/rules_summary.json` and `facade/emit_summary.json` hold every number in this
  report machine-readably, including the full per-borough class and material distributions and the per-kit-id counts.
* **`python -m nycsim_pipeline facade` is not registered** in `pipeline/nycsim_pipeline/__main__.py` (not this lane).
  Run the stage as `python -m nycsim_pipeline.facade.build all`, or add
  `"facade": "nycsim_pipeline.facade.build"` to `STAGES`.

## 13. Licences

No new downloads were made. Inputs: NYC Open Data (OTI building footprints, MapPLUTO, the LPC building database and
historic districts, Building Elevation & Subgrade, DCWP, DOHMH, DOB sidewalk sheds, NTA 2020, CSCL) under NYC Open
Data terms, recorded in `data/manifest/downloads.json` by the stages that fetched them; OpenStreetMap
(`osm/buildings.parquet`) — **ODbL 1.0, © OpenStreetMap contributors** — used for `building:material`,
`building:colour`, `roof:shape` and the `osm_id` match. This stage's own artefacts are recorded in
`data/manifest/processed.json` under stage `facade`.

---

## 14. Illuminated signage (2026-09-07)

The comparison lane recorded deviation **B15**: the Times Square daylight frame has "no signage of any kind — not a
screen, not a billboard, not a shopfront sign, not a lit letter", against a photograph that is "60 % illuminated
advertising by area", and the night frame renders "a grey canyon lit by six street lamps" with "the emissive content
of the model city close to zero". This section is what was done about it and, just as importantly, what was not.

### 14.1 What each sign is evidence of

`facade/signage.py` keeps three questions apart, because they have three different sources.

| question | source | is it real? |
|---|---|---|
| does this shopfront have a sign? | `has_storefront` (MapPLUTO `retailarea`/`comarea`, DCWP licences, DOHMH permits, OSM `shop`) and a non-empty `awning_text` | **real** |
| what does it say? | `awning_text` + `awning_real` — a real DCWP/DOHMH/OSM business name for 30,381, the generic NYC trade wording for 48,021, empty for 1,859 | **real name for 30,381; the rest is generic wording, flagged** |
| does this building carry a bulletin? | the `billboard` typology feature of its `facade_class` | **inferred** (ADR-004, `FACADE_INFERRED`) |
| does this frontage carry a screen? | MapPLUTO `zonedist1`..`zonedist4` = **`C6-7T`** — 59 lots in the whole city, all of them in the Times Square bowtie | **real, per lot** |

**`C6-7T` is the find that made an honest Times Square possible.** The `T` suffix in the Special Midtown District is
the Times Square core, where illuminated signage is mandatory rather than merely permitted, and MapPLUTO carries it
per lot. Measured on the shipped extract: 56 lots as `zonedist1`, 3 more as `zonedist2`, and every one of the 59 lies
inside latitude 40.7565–40.7616, longitude −73.9867 to −73.9828 — a 570 × 320 m box on Broadway and Seventh Avenue
between 42nd and 50th Streets. No hand-drawn polygon, no guessed boundary: a published per-lot attribute of a dataset
that was already in this repository.

`test_the_sign_zone_lots_are_all_in_times_square` asserts that every building the zone claims is within 400 m of
Duffy Square, so a future PLUTO refresh that put `C6-7T` somewhere else would fail rather than light the wrong city.

### 14.2 What is placed

**42,546,790 placements** across 920 tiles (1.702 GB), up from 42,068,609 (1.683 GB) — **+478,181 records, +1.1 %**.
920/920 tiles validated, 0 problems, 120 distinct kit ids in use (was 85).

| piece | records | placed where |
|---|--:|---|
| `storefront_sign_band` (blank lit fascia) | **279,624** | shopfront runs of the buildings whose `awning_text` is a **real business name** — the panel is lit and blank, and the runtime binds the name from `awning_text` on the same `bin` |
| `storefront_sign_band_<kind>` (15 of 16 used) | **305,082** | shopfront runs whose `awning_text` is the generic wording for that kind. `storefront_sign_band_hardware` is never placed: "HARDWARE" occurs nowhere in `awning_text` |
| `storefront_sign_projecting` (blade sign) | **56,214** | 35 % of shopfront runs that carry a fascia band |
| `billboard_wall_mounted` (blank vinyl) | **1,161** | street facade of a `billboard`-class building whose primary run is ≥ 13.6 m and whose wall clears 6.75 m above the shopfront storey |
| `billboard_rooftop` (blank vinyl) | **6,269** | roof of a `billboard`-class building of ≤ 4 floors and ≥ 300 m² whose footprint can actually contain the 14.95 m board (both ends tested inside the polygon) |
| `sign_led_panel_wall` / `_blade_tall` / `_ribbon` | **1,036 / 41 / 56** | street-facing frontages of the buildings on a `C6-7T` lot, from the top of the shopfront storey to 30 m, one 6.10 × 3.05 m module at a time |
| `win_<type>_lit` | **9,048,881** of 30,435,823 windows (**29.7 %**) | the windows the existing `lit_seed` draw already flagged `FLAG_LIT` — no extra records at all, the id changes instead |

**34,102 buildings** carry the `billboard` class feature; **7,430 of them (21.8 %)** get a bulletin, because the rest
have no wall long or tall enough and no roof big enough. Two classes carry the feature but never get a *rooftop*
board (`derive.NO_ROOF_BILLBOARD_CLASSES`): a gas-station canopy has no roof deck to stand an 8.6 m steel frame on,
and a one- or two-storey corner taxpayer advertises on its wall and its fascia, not on a rooftop bulletin. Both stay
eligible for the wall board.

**57 buildings** stand on the 59 `C6-7T` lots and carry the 1,133 LED modules between them.

### 14.3 What the night city emits now

`flags` bit 0 already said which windows have their lights on; nothing consumed it, because a glTF instance cannot
switch a material from a flag. The kit now exports a `win_<type>_lit` twin of every window that has an interior card
and the placer names it directly — so **9.05 M windows changed from the unlit interior card (emission 0.85) to the
lit one (1.6) at a cost of zero extra records and zero extra bytes**. Every sign placement carries `FLAG_LIT`, and
the sign faces are emissive in the kit: 2.2 for an internally-lit shopfront box sign, 7.0 for an LED display, 0.55
for floodlit bulletin vinyl.

### 14.4 What was refused

* **No invented advertising copy, anywhere.** ADR-004 and deviation B5 are unchanged in substance: there is still no
  source that says what any New York bulletin or screen carries, so every bulletin face is blank vinyl and every LED
  face carries the pixel matrix of the display hardware and nothing else. `test_every_shipped_sign_legend_is_generic_
  wording_or_blank` is the gate: a kit piece may declare a legend only if that string is one of the fifteen generic
  trade strings the pipeline itself writes into `awning_text`, or the empty string.
* **No real business name is baked into geometry.** The 30,381 shopfronts with a real name get a *blank lit panel*.
  The name is in the data and the contract says where a runtime binds it (DATA_CONTRACTS §6.1.1), but an instanced
  kit carries one texture per piece and the offline verification frames therefore show those fascias unlettered.
  This is a stated gap, not a solved problem: closing it needs per-instance texture binding at runtime.
* **The Times Square screens show nothing.** Placing a screen where the zoning says a screen must be is inference of
  the same kind as every other class feature. Painting an advertisement on it would be fabrication, so the face is
  the LED matrix on its black substrate: unmistakably a display, asserting nothing about content.

### 14.5 Correction to an earlier claim in this report

G-5 said wall billboards were unplaced because "there is no real source of NYC billboard locations in this
environment". That was too broad and is corrected here. Two sources exist and both are now used:

* the `billboard` class feature — inference, flagged, blank-faced;
* **292 OSM `advertising=billboard` nodes** in the city extract, which the *furniture* stage already places as
  free-standing props (`furniture.catalog` kind 15). None of them is within 1 km of Times Square, and this stage
  does not duplicate them.

### 14.6 Verification

```
python -m nycsim_pipeline.facade.build emit      920 tiles, 42,546,790 placements, 1,701,871,600 bytes, 149 s,
                                                 peak RSS 1,182 MB, 920/920 schema-validated, 0 problems
python -m nycsim_pipeline.facade.validate_placements
                                                 920 tiles checked, 0 with problems, 120 distinct kit ids,
                                                 all registered, 54 catalog entries never placed
PYTHONPATH=pipeline pytest pipeline/tests/test_facade.py pipeline/tests/test_facade_signage.py -q   55 passed
python3 -m pytest tests/test_kit_facade.py -q                                                     1462 passed
```

`pipeline/tests/test_facade_signage.py` adds **19 tests**: the two generic-wording tables agree between the kit and
the pipeline; no shipped legend is anything but generic wording or blank; no real business name is baked; the sign
zone is the published district and every one of its lots is in the bowtie; every placed kit id resolves to an
exported `.glb`; signs lie inside their own building's footprint; wall signs sit between pavement and roof and
rooftop bulletins on the roof deck; bands only where `has_storefront`, bulletins only where the class carries the
feature (and at most one per building), LED only on a sign-zone lot; every sign is flagged lit; a `_lit` window piece
appears exactly where `FLAG_LIT` is set; the band a building gets carries that building's own `awning_text`; and the
whole stream regenerates byte-identically.

### 14.7 Measured on the frame

A controlled A/B, both frames rendered from the **same tile shells, same camera, same 32 samples**, through the
shipped `blender/verify/render_sheets.py` path, differing only in the placement stream: "before" is the same stage
with the signage suppressed and every window on its unlit twin. Luminance is Rec. 709 luma on the display-referred
PNG; "> 0.90" is the fraction of the frame's area above that luma — the bright-source area an illuminated sign
occupies. The reference photographs are the licensed Wikimedia Commons frames the comparison lane already uses.

**Night — Duffy Square looking south, 21:00, 3 August**

| | mean | median | p99 | area > 0.70 | **area > 0.90** | area > 0.95 |
|---|--:|--:|--:|--:|--:|--:|
| before (no signage, unlit windows) | 0.463 | 0.480 | 0.785 | 14.40 % | **0.34 %** | 0.27 % |
| after | 0.532 | 0.565 | 0.945 | 23.71 % | **7.02 %** | 0.29 % |
| reference photograph | 0.253 | 0.151 | 1.000 | 9.70 % | **6.17 %** | 5.07 % |

**Day — the same viewpoint**

| | mean | median | p99 | **area > 0.70** | area > 0.90 |
|---|--:|--:|--:|--:|--:|
| before (no signage) | 0.406 | 0.369 | 0.977 | **10.69 %** | 5.64 % |
| after | 0.434 | 0.381 | 0.977 | **16.06 %** | 5.64 % |
| reference photograph | 0.404 | 0.395 | 0.986 | **15.73 %** | 3.29 % |

**The emissive content of the night frame went from 0.34 % of the frame to 7.02 %, against a photograph at 6.17 %.**
In daylight the illuminated-surface fraction went from 10.69 % to 16.06 % against a photograph at 15.73 %, and the
frame's mean luminance moved from 0.406 to 0.434 against the photograph's 0.404. Within the camera's 130 m kit
radius the frame now carries **11,337 m² of emissive sign face** (9,752 m² of LED display, 607 m² of ribbon board,
433 m² of shopfront fascia, 397 m² of blade spectacular, 149 m² of floodlit bulletin) where it carried none, plus
5,355 of 18,932 windows on their lit twin. The render records 15,471 kit instances placed and **0 unresolved kit
ids**.

**What the numbers still say is wrong, and it is not the signage.** The night frame's *base level* is far too high:
median 0.565 against the photograph's 0.151, and only 0.29 % of the frame reaches 0.95 where the photograph clips
over 5 % of its area. The photograph is a dark street with signs that blow out; the render is a lifted grey street
with signs that merely glow. That is the night lighting policy in `blender/verify/render_sheets.py`
(`NIGHT_EXPOSURE_STOPS = 2.0`, `SKY_STRENGTH_NIGHT = 0.5`), not the emissive content, and it is handed to the
comparison lane rather than compensated for here: raising the sign emission until the render clips would have
over-brightened the daylight frame, which is exactly what the 7.0 calibration point did (daylight area > 0.90 rose
to 6.93 % against the photograph's 3.29 %). The shipped LED emission of 3.0 is the value that fits the **daylight**
photograph, measured, and the night frame's remaining deficit is a base-exposure problem for whoever owns that file.
