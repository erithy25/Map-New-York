# Roads stage — verification report

Stage: `pipeline/nycsim_pipeline/roads/` (+ `runtime/`). Contracts: `DATA_CONTRACTS.md` §7 and §15, ADR-006/007.
Full pass run on 2026-09-06 in this container (4 vCPU shared, `nice -n 10`).

```
PYTHONPATH=pipeline python -m nycsim_pipeline roads              # everything below
PYTHONPATH=pipeline python -m nycsim_pipeline.roads.apply_terrain_z   # lift onto the real terrain
PYTHONPATH=pipeline python -m nycsim_pipeline.runtime.export          # re-export the §15 binaries
PYTHONPATH=pipeline python -m pytest pipeline/tests/test_roads.py -q  # 55 passed
PYTHONPATH=pipeline python -m pytest tests/test_world_integration.py -q  # 18 passed
```

---

## 1. What was built

| File | Purpose |
|---|---|
| `roads/build.py` | stage entry point (`python -m nycsim_pipeline roads`), orchestration, contract validation, manifest |
| `roads/cscl.py`, `roads/lion.py` | CSCL geometry/attributes; LION node topology, datum shift, node positions |
| `roads/osm.py` | OSM caches (signal/stop nodes, vehicular ways, turn-restriction relations) |
| `roads/segments.py` | §7 `segments.parquet` + the node table |
| `roads/signals.py` | signal provenance union (ADR-007), stop/yield control, DOT-standard phasing, progression offsets |
| `roads/lanes.py` | §7 `lanes.parquet` — real cross-sections with offset geometry |
| `roads/junctions.py` | §7 `junction_lanes.parquet` — lane-to-lane connectors, turns, yields, OSM restrictions |
| `roads/signs.py` | §7 `signs.parquet` — 402,774 real DOT signs + the regulatory/name signs DOT does not publish |
| `roads/pavement.py` | §7 `roads/pavement/{tile}.parquet` — planimetric roadbed/sidewalk/median/plaza/curb/parking + derived crosswalks |
| `roads/bridges.py` | `roads/bridges_tunnels.json` — the 53 named crossings, their segment ids and end nodes |
| `roads/graph.py` | directed lane-network graph, A* router, component analysis, one-way and dead-end audits |
| `roads/apply_terrain_z.py` | re-runnable stage that lifts the network onto `tiles/{tile}/terrain.png` |
| `runtime/export.py` | §15 `runtime/roadgraph.nycb`, `runtime/signals.nycb`, `nycb_layout.json` + the Python reader |
| `pipeline/tests/test_roads.py` | 55 tests (unit + artefact + binary round-trip) |

Outputs (`data/processed/`):

| Artefact | Rows | Size |
|---|---|---|
| `roads/segments.parquet` | 122,235 | 13.7 MB |
| `roads/nodes.parquet` | 79,291 | 4.2 MB |
| `roads/lanes.parquet` | 381,971 | 36.8 MB |
| `roads/junction_lanes.parquet` | 469,754 | 59.6 MB |
| `roads/signals.parquet` | 19,814 | 0.5 MB |
| `roads/signs.parquet` | 633,287 | 33.7 MB |
| `roads/pavement/*.parquet` | 617,518 in 972 tiles | 864 MB |
| `roads/bridges_tunnels.json` | 53 structures | 173 KB |
| `roads/connectivity.json`, `roads/build_summary.json`, `roads/terrain_z_summary.json` | — | — |
| `runtime/roadgraph.nycb` | 8 sections | 104.2 MB |
| `runtime/signals.nycb` | 2 sections | 1.74 MB |

`nycsim_pipeline.contracts.validate_parquet` returns `[]` for all six tabular artefacts
(`road_segments`, `road_nodes`, `lanes`, `junction_lanes`, `signals`, `signs`); the stage aborts if it does not.

---

## 2. Inputs and topology

CSCL (`inkn-q76z`): 122,269 features read → 122,235 segments (5,377 multipart arcs line-merged, 0 disjoint,
57 duplicate `physicalid` rows dropped keeping the longest). LION (`2v4z-66xt`): 139,674 nodes, 188,829 segment
rows covering 122,212 physical ids, 129,750 nodes with real street names.

Node assignment (244,470 segment ends): **243,626 (99.65 %)** matched a LION node of the same `physicalid`,
470 (0.19 %) the nearest LION node within 3 m, 374 (0.15 %) needed a synthetic node (152 synthetic nodes in total).

CSCL reaches NYC_TM through Socrata's WGS84 export and LION/DOT/planimetric data through EPSG:2263; the measured
offset between the two realisations is **dx = −0.108 m, dy = +0.915 m** with a residual RMS of **0.079 m** over
121,864 matched ends. Every EPSG:2263-sourced coordinate (DOT signs, permit pavement records) is shifted by it,
so all layers share one frame.

OSM caches: 218,205 tagged nodes, 260,544 vehicular ways, 12,378 turn-restriction relations.

---

## 3. Segments — 12,997.3 km

| rw_type | segments | km |
|---|---:|---:|
| 1 street | 99,346 | 10,359.7 |
| 2 highway | 4,125 | 653.2 |
| 3 bridge | 3,364 | 203.3 |
| 4 tunnel | 171 | 15.0 |
| 5 boardwalk | 101 | 21.4 |
| 6 path | 5,953 | 650.5 |
| 7 step street | 245 | 7.7 |
| 8 driveway | 799 | 93.8 |
| 9 ramp | 3,570 | 372.3 |
| 10 alley | 3,824 | 308.8 |
| 12 non-physical | 8 | 0.3 |
| 13 U-turn | 304 | 4.7 |
| 14 ferry | 425 | 306.6 |
| **total** | **122,235** | **12,997.3** |

Drivable (motor-vehicle rw_type, `trafdir != NV`, status 2): **113,445 segments, 11,886.9 km**.

| borough | segments | km | drivable km |
|---|---:|---:|---:|
| Manhattan | 14,066 | 1,435.9 | 1,086.4 |
| Bronx | 18,574 | 1,861.5 | 1,675.6 |
| Brooklyn | 27,677 | 3,111.4 | 2,896.3 |
| Queens | 45,219 | 4,680.2 | 4,492.3 |
| Staten Island | 16,699 | 1,908.3 | 1,736.3 |

Attribute provenance (`*_source = 0` real, `1` inferred): width real for 113,249 / 122,235 (92.6 %), lane counts
real for 113,526 (92.9 %), posted speed real for 100,949 (82.6 %). 188 further speeds came from the Vision Zero
speed-limit layer (`5mad-ntua`) before the rw_type default was used. Bus lanes: 2,295 segments (`ycrg-ses3`).
Truck routes: 7,710 through + 39 local resolved from `truck_routes`, 15,466 flagged in CSCL without a resolvable
type. Bike lanes: 5,889 protected, 7,471 standard, 3,991 sharrow, 268 greenway (CSCL `bike_lane` + `mzxg-pwib`).
Surface: 119,437 asphalt, 1,734 concrete, **864 cobble/Belgian block** (2,500 from OSM `surface=*`, 613 from
cobblestone entries in the DOT street-construction permit pavement records), 10 steel grate, 89 gravel,
101 boardwalk.

Grade separation: 114,273 segments at grade, 5,278 at a constant level code, 2,684 ramping between two codes.

---

## 4. Elevation

`z` is produced in two stages so the roads stage never blocks on terrain.

1. **In `build.py`** — from the CSCL/LION level codes: 4 codes = one grade level = 5.5 m, interpolated along the
   segment for the 2,684 ramping records. That alone gives correct *relative* geometry on a flat city.
2. **In `apply_terrain_z.py`** (re-runnable, run after the terrain stage) — samples
   `tiles/{tile}/terrain.png` (§3: 16-bit, 501 × 501, 2 m, north row first, `z = z_min_m + v·z_scale_m`)
   bilinearly and rewrites the absolute heights: at-grade vertices follow the terrain, decks stay straight
   between `terrain(end) + level offset` so a bridge does not follow the riverbed; nodes, lanes, junction lanes
   and sign mounting heights are lifted consistently.

Result of the final run, against the 2,916 terrain tiles the terrain stage had written (last tile written 13:30):

| layer | rows | vertices | vertices with terrain | at-grade lifted | structures lifted |
|---|---:|---:|---:|---:|---:|
| segments | 122,235 | 434,961 | 434,961 (100 %) | 396,305 | 7,962 / 7,962 |
| lanes | 381,971 | 1,121,513 | 1,121,513 (100 %) | 1,045,670 | 16,530 / 16,530 |
| junction lanes | 469,754 | 2,353,828 | 2,353,828 (100 %) | 2,228,124 | 26,736 / 26,736 |
| nodes | 79,291 | — | 79,291 | — | — |
| signs | 633,287 | — | 633,287 | — | — |

Ground heights under the network: mean **16.06 m**, min **−5.12 m**, max **121.29 m** (Todt Hill, Staten Island —
the published summit is 124.9 m, and the road does not reach the summit). Runtime 108 s, 3,717 tile loads
through a 256-tile LRU (~130 MB ceiling).

The stage is **idempotent**: the grade-separation offset is recomputed from the immutable `level_from`/`level_to`
codes and the sign mounting height from `z − ground_z`, never read back out of the geometry. This is proved by
`test_apply_terrain_z_lifts_the_network_and_is_idempotent`, which lifts a synthetic network twice and asserts the
z arrays are bit-identical. Re-run the stage (and then `runtime.export`) whenever the terrain tiles change.

---

## 5. Nodes, control and signals

79,291 nodes (152 synthetic). Control:

| control | nodes |
|---|---:|
| 0 none | 38,319 |
| 1 signal | 19,814 |
| 2 stop | 19,838 |
| 3 all-way stop | 1,063 |
| 4 yield | 257 |

**Signals by source** (ADR-007 priority LPI > Barnes > OSM > retiming > inferred; every source that hit a node is
also kept in the `signal_sources_mask` extension column):

| source | nodes | input |
|---|---:|---|
| 1 DOT LPI (`xc4v-ntf4`) | 6,741 | 6,791 rows, 6,777 snapped, 6,320 (93 %) confirmed by matching both street names |
| 2 DOT Barnes Dance (`8kuj-2n3u`) | 578 | 737 rows, 610 snapped, 134 with an exclusive pedestrian phase |
| 0 OSM `highway=traffic_signals` | 9,547 | 24,760 nodes, 18,144 snapped |
| 3 DOT retiming corridors (`d8dp-wfee`) | 1,282 | 444 corridors, 15,078 nodes on a corridor, 9,403 dropped as not a through crossing |
| 4 inferred (ADR-007) | 1,666 | multi-lane arterial × multi-lane arterial with no source and no stop sign |
| **total** | **19,814** | |

19,814 signal *nodes* collapse to **14,466 intersection clusters** at a 40 m single-link radius; NYC DOT publishes
about 13,700 signalised intersections, so the union is ~5 % above the published count — the residual is mostly
divided roadways whose two carriageways are separate nodes further than 40 m apart. This is the honest position
of ADR-007: DOT does not publish an all-signals dataset, so the union is the best available and every node carries
its provenance. A retiming corridor names the corridor, not its individual signals, so a retiming-only node is
kept only where the crossing street is a real through street (its name is on ≥ 2 legs and it carries ≥ 2 travel
lanes); that rule removed 9,403 of the 15,078 candidates.

Stop/yield control comes from OSM: 35,494 `highway=stop` nodes (26,924 snapped) and 889 `give_way` (429 snapped),
attributed to the nearest incident drivable approach; 1,063 nodes are all-way stops (`stop=all` or every approach
signed).

**Phasing** (DOT standard): 2 vehicle groups (3 at nodes with ≥ 5 legs), yellow 3 s, all-red 2 s, WALK 7 s,
pedestrian flashing = crossing width / 1.1 m/s, LPI 7 s where DOT lists one, an exclusive pedestrian phase where
DOT lists a Barnes Dance. Cycle 90 s in the Manhattan CBD (south of the *real* 60th Street line fitted from the
CSCL segments — 1,864 signals), 60 s elsewhere, escalated only when the pedestrian minimums do not fit:
14,282 × 60 s, 5,438 × 90 s, 94 × 120 s; 3,679 controllers were escalated or had their pedestrian intervals scaled.
Every controller's phase durations sum to its cycle exactly (asserted for 500 sampled controllers and in the
binary round-trip test). 14,303 controllers carry a progression offset computed along their one-way corridor at
25 mph.

---

## 6. Lanes and junction lanes

**381,971 lanes**: 220,329 travel, 686 centre-turn, 146,768 parking, 14,188 bike. Travel + turn lane length
**22,182 km**. Mean travel-lane width 3.29 m, minimum 0.907 m (a bike lane; see below).

A stack that does not fit the published curb-to-curb width is made to fit the way a narrow NYC street really is:
optional lanes go first — parking from the kerb inwards, then the bike lane — and only the survivors are narrowed,
never below a physical minimum (travel/bus/turn 2.43 m = the widest fleet body plus clearance, parking 1.80 m,
bike 0.90 m). 1,812 optional lanes were dropped this way. 3,234 stacks are still wider than the published
`streetwidth`, i.e. CSCL itself lists more lanes than its own width field allows; those keep the minimum widths and
are flagged. 9,688 two-way segments carry a single published travel lane and are modelled as one lane each way.

**469,754 junction lanes**: 207,838 straight, 113,720 left, 115,515 right, 32,681 U-turn (21,156 legal U-turns
plus 9,459 cul-de-sac turnarounds; a U-turn connector exists only at an unsignalised node with ≥ 3 legs on a
two-way street at least 11.6 m wide — the real curb-to-curb turning circle of the ADR-009 player car).
588,201 yield relations. OSM restrictions: 12,378 relations, 10,833 with a via node, 3,892 snapped to a node,
**3,529 mapped** onto (node, from-segment, to-segment) pairs — 2,212 `no_*` pairs removed and 612 pairs removed by
`only_*` rules; 449 conditional and 1,483 via-way restrictions were skipped and counted. 167 street↔highway pairs
were blocked at nodes where a ramp provides the legal movement.

Dead ends (a lane with no successor once the connectors are attached): **1,834 of 221,015 travel lanes (0.83 %)**
have no successor, 741 no predecessor, 50 are isolated; 1,051 bike lanes end without a successor. Mean 2.05
successors per travel lane. The residual dead ends are real: kerbed cul-de-sac stubs, service roads that CSCL ends
at a property line, and segments that leave the five boroughs.

---

## 7. Signs — 633,287

| source | count |
|---|---:|
| 0 DOT current sign records (`nfid-uabd`) | 402,774 |
| 1 generated street-name blades | 106,622 |
| 2 generated regulatory (position derived, control real) | 123,891 |

**By MUTCD family**

| family | count | origin |
|---|---:|---|
| R7 parking/standing/stopping | 339,880 | DOT |
| D3-1 street name | 106,622 | generated from the two real LION names |
| I information / guide (NYC `SI-`) | 49,579 | DOT |
| R5-1 do not enter | 42,020 | generated at the closed end of a one-way street |
| R6-1 one way | 41,994 | generated at the open end of a one-way street |
| R1-1/R1-2 stop / yield | 26,055 | generated at the 25,743 stop-controlled and 312 yield-controlled approaches |
| R2-1 speed limit | 13,825 | 3 DOT + 13,822 generated where the *real* posted limit changes at a node |
| R8 bus stop | 12,425 | DOT |
| B, M, W, R3, R4, other | 887 | DOT |

The DOT dataset is a **parking-regulation** dataset: 0 of its 440,540 rows are ONE WAY, DO NOT ENTER or YIELD
signs and its 21,467 rows matching "STOP" are all "NO STOPPING"/"BUS STOP". Those four regulatory families
therefore have no published point source and are generated from the network and the OSM control nodes; they carry
`source = 2` and their *positions* are derived while their *control* is real.

Of the 440,540 DOT rows, 403,703 are current with usable State Plane coordinates; 402,774 snapped to a centreline
within 40 m (median snap distance **0.43 m**) and 929 were dropped as unplaceable (private roads, marinas, airport
aprons). 345,637 snapped to an intersection node within 60 m. 269,191 distinct poles; signs sharing a pole are
stacked upward from the MUTCD urban minimum mounting height of 2.13 m. Sheet size comes from the real
`sign_size` string (HEIGHT × WIDTH inches, or "NN DIAMETER"); 755 blanks fell back to the NYC standard 12″ × 18″.
Arrows: 231,891 double, 49,587 left, 47,015 right, 74,281 none. Supports: 332,718 pole, 65,365 lamp post,
4,177 signal mast, 514 wall. Facing headings put the face parallel to the kerb with its normal pointing into the
roadway, which is how NYC mounts parking signs.

---

## 8. Pavement — 617,518 polygons in 972 tiles

Recomputed from the produced tile files:

| kind | polygons | area km² | source |
|---|---:|---:|---|
| 0 roadbed | 121,324 | 135.81 | `plan_roadbed` (i36f-5ih7), 104,961 features |
| 1 sidewalk | 63,427 | 57.25 | `plan_sidewalk` (52n9-sdep), 50,865 features |
| 2 median | 21,442 | 4.88 | `plan_median` (ees7-4ufv), 19,346 features |
| 3 plaza | 2,149 | 1.65 | `plan_public_plazas` (ue2e-9jm2) + DOT `ped_plazas` (k5k6-6jex) |
| 4 curb | 237,790 | 5.73 | `plan_curb` (5xvt-8cbk), 217,662 lines buffered to the real 0.30 m curb face |
| 5 crosswalk | 148,674 | 5.94 | derived at every controlled intersection from the real leg widths (`source = 1`) |
| 6 parking lot | 22,712 | 34.89 | `plan_parking_lot` (7cgt-uhhz), 20,429 features |

468,844 rows are planimetric (`source = 0`) and 148,674 are the derived crosswalks (`source = 1`). Polygons that
straddle a tile boundary are clipped, so the union over tiles reproduces the source exactly and every polygon lies
inside its own tile (asserted on 12 random tiles). Roadbed `surface` is taken from the nearest CSCL segment, so the
1,136 cobble and 109 gravel roadbeds are the real ones. Runtime of the pavement pass: 367 s.

Two notes on this layer, stated plainly:

* The contract types pavement as polygons; the DoITT curb layer is published as lines, so the curb *face* is stored
  buffered to 0.30 m. That is a representation choice, not invented geometry.
* Crosswalks (kind 5) are **derived**, not published: NYC does not publish crosswalk polygons in the datasets used
  here. They are 3.66 m (12 ft) deep, as wide as the real leg roadway, set back past the widest crossing leg, and
  placed only at nodes that actually carry a signal or stop/yield control. They are flagged `source = 1`.
* `driveway` (kind 7) has no published source in this dataset set and is not produced.

---

## 9. Bridges and tunnels — 53 of 53 found

`roads/bridges_tunnels.json` lists every named crossing with its CSCL names, the segment ids of the deck, the ramp
segment ids, deck length, the end nodes (with coordinates), and whether removing the structure would split the
network there. Matching is by the real CSCL `full_street_name` normalised by `roads/names.py`; the only exception
is the Greenpoint Avenue Bridge, whose deck CSCL names simply "GREENPOINT AVE" — it is resolved by intersecting
that street with the DoITT planimetric transportation-structure polygons and flagged `matched_by =
"street_in_structure"`. **Nothing is matched by proximity.**

**Every one of the 53 is connected at both ends** (≥ 2 end nodes joining segments outside the structure).

| structure | kind | deck segs | ramp segs | length m | end nodes | sole link |
|---|---|---:|---:|---:|---:|:--:|
| Brooklyn Bridge | bridge | 119 | 15 | 7,632 | 92 | yes |
| Manhattan Bridge | bridge | 164 | 5 | 11,037 | 143 | yes |
| Williamsburg Bridge | bridge | 154 | 0 | 10,977 | 114 | yes |
| Ed Koch Queensboro Bridge | bridge | 192 | 12 | 13,499 | 86 | yes |
| Robert F. Kennedy (Triborough) Bridge | bridge | 155 | 32 | 14,067 | 125 | yes |
| George Washington Bridge | bridge | 58 | 8 | 5,549 | 34 | yes |
| Verrazzano-Narrows Bridge | bridge | 94 | 21 | 9,562 | 38 | yes |
| Throgs Neck Bridge | bridge | 26 | 0 | 6,370 | 19 | yes |
| Bronx-Whitestone Bridge | bridge | 13 | 0 | 4,148 | 8 | yes |
| Pulaski Bridge | bridge | 69 | 1 | 3,605 | 47 | no |
| Kosciuszko Bridge | bridge | 35 | 0 | 3,260 | 26 | no |
| High Bridge | bridge | 18 | 0 | 1,212 | 15 | no |
| Henry Hudson Bridge | bridge | 17 | 0 | 1,230 | 12 | no |
| Cross Bay Veterans Memorial Bridge | bridge | 6 | 30 | 2,193 | 7 | no |
| Marine Parkway-Gil Hodges Memorial Bridge | bridge | 14 | 9 | 3,580 | 9 | no |
| Hell Gate Bridge | bridge | 3 | 0 | 270 | 3 | yes |
| Goethals Bridge | bridge | 7 | 0 | 1,550 | 7 | yes |
| Bayonne Bridge | bridge | 19 | 1 | 3,356 | 16 | yes |
| Outerbridge Crossing | bridge | 10 | 0 | 2,401 | 8 | yes |
| Willis Avenue Bridge | bridge | 36 | 1 | 2,107 | 29 | yes |
| Third Avenue Bridge | bridge | 39 | 3 | 1,751 | 31 | no |
| Madison Avenue Bridge | bridge | 46 | 0 | 2,202 | 31 | no |
| 145th Street Bridge | bridge | 26 | 0 | 1,334 | 15 | no |
| Macombs Dam Bridge | bridge | 74 | 0 | 2,915 | 50 | no |
| University Heights Bridge | bridge | 6 | 0 | 351 | 2 | no |
| Washington Bridge | bridge | 72 | 5 | 2,836 | 63 | no |
| Alexander Hamilton Bridge | bridge | 40 | 0 | 1,091 | 33 | no |
| Broadway Bridge | bridge | 4 | 0 | 247 | 4 | no |
| Roosevelt Island Bridge | bridge | 15 | 4 | 965 | 10 | no |
| Carroll Street Bridge | bridge | 1 | 0 | 30 | 2 | no |
| Union Street Bridge | bridge | 1 | 0 | 29 | 2 | no |
| Third Street Bridge | bridge | 1 | 0 | 30 | 2 | no |
| Ninth Street Bridge | bridge | 1 | 0 | 31 | 2 | no |
| Hamilton Avenue Bridge | bridge | 2 | 0 | 75 | 4 | no |
| Greenpoint Avenue Bridge | bridge | 8 | 0 | 271 | 10 | yes |
| Metropolitan Avenue Bridge | bridge | 2 | 0 | 48 | 2 | no |
| Grand Street Bridge | bridge | 2 | 0 | 67 | 2 | no |
| Borden Avenue Bridge | bridge | 1 | 0 | 21 | 2 | no |
| Hunters Point Avenue Bridge | bridge | 1 | 0 | 45 | 2 | no |
| Roosevelt Avenue Bridge | bridge | 3 | 0 | 91 | 4 | no |
| Mill Basin Bridge | bridge | 2 | 0 | 427 | 4 | no |
| Cropsey Avenue Bridge | bridge | 2 | 0 | 125 | 4 | no |
| Ocean Avenue Bridge | bridge | 3 | 0 | 191 | 2 | no |
| Pelham Bridge | bridge | 1 | 0 | 236 | 2 | no |
| City Island Bridge | bridge | 3 | 0 | 856 | 2 | yes |
| Unionport Bridge | bridge | 5 | 0 | 76 | 4 | no |
| Eastchester Bridge | bridge | 2 | 0 | 72 | 4 | yes |
| Hutchinson River Parkway Bridge | bridge | 8 | 0 | 271 | 6 | no |
| Rikers Island Bridge | bridge | 6 | 0 | 1,391 | 3 | yes |
| Lincoln Tunnel | tunnel | 51 | 27 | 4,121 | 27 | yes |
| Holland Tunnel | tunnel | 26 | 30 | 1,823 | 8 | yes |
| Queens-Midtown Tunnel | tunnel | 42 | 29 | 4,141 | 8 | no |
| Hugh L. Carey Tunnel | tunnel | 91 | 9 | 7,269 | 30 | yes |

"sole link = no" means the crossing's two ends stay connected when the structure is removed, because a parallel
crossing exists (the four Harlem River bridges within 1 km of each other, Pulaski next to Kosciuszko, the Gowanus
Canal bascule bridges, and the Queens-Midtown Tunnel next to the Queensboro Bridge). It is a property of the city,
not a defect: 21 structures *are* the only link between their two shores and are reported as such.

Two entries need a word. **Hell Gate Bridge** is a rail bridge; CSCL carries 3 short segments for it (270 m), which
is all the road centreline dataset knows about it. **Ocean Avenue Bridge** over Sheepshead Bay is a footbridge, and
CSCL names it "OCEAN AVE PED BR" — 3 segments, 191 m, correctly non-drivable.

---

## 10. Connectivity and driving validation

Undirected segment graph: 2,247 components, largest **72,997 of 79,291 nodes = 92.06 %** (the integration gate
requires > 90 %). Directed drivable graph: 79,291 nodes, 172,552 arcs, 74,787 nodes with an outgoing arc; the
largest strongly connected component holds **68,271 = 91.29 % of the drivable nodes**, i.e. from 91 % of the
network you can drive to 91 % of the network and back. The remainder is genuine: gated Rikers Island roads,
private-campus loops, park paths, boardwalks, ferry routes and beach-club drives that CSCL records but that do not
join the public network.

**A\* routes** (free-flow travel time, admissible straight-line heuristic):

| route | segments | km | min | nodes expanded | search s |
|---|---:|---:|---:|---:|---:|
| **Fordham Rd & Grand Concourse (BX) → Hylan Blvd & Richmond Ave (SI)** | 487 | **49.38** | 46.7 | 42,977 | 0.27 |
| 5 Ave & E 42 St (MN) → Flatbush Ave & Atlantic Ave (BK) | 111 | 9.85 | 11.4 | 4,986 | 0.04 |
| Queens Blvd & Woodhaven Blvd (QN) → Broadway & W 72 St (MN) | 130 | 13.15 | 14.3 | 9,657 | 0.10 |
| Fordham Rd & Grand Concourse (BX) → Northern Blvd & Junction Blvd (QN) | 176 | 17.94 | 16.7 | 11,634 | 0.15 |

The Bronx → Staten Island route **uses 24 Verrazzano-Narrows Bridge segments** (asserted in
`test_connectivity_report_shows_a_drivable_city`). Its street sequence is
E/W Fordham Rd → Major Deegan Expy → 3 Ave → Bruckner Blvd → Third Avenue Bridge → Harlem River Dr → FDR Dr →
Manhattan Bridge → Adams/Water/Washington St → BQE → Gowanus Expy → Verrazzano-Narrows Bridge → Staten Island Expy
→ Fingerboard Rd → Hylan Blvd — a route a New York driver would recognise.

**One-way sanity** (length-weighted compass bearing of legal travel; 7 of 7 pass). The Manhattan grid is rotated
~29° from true north, which is exactly what the measured bearings show:

| street | one-way km | mean travel bearing | expected | share within 60° |
|---|---:|---:|---:|---:|
| Fifth Avenue | 10.15 | 208.8° | 180° (south) | 99.8 % |
| Madison Avenue | 9.28 | 29.0° | 0° (north) | 97.4 % |
| First Avenue | 12.64 | 29.2° | 0° | 98.2 % |
| Second Avenue | 10.65 | 209.0° | 180° | 100 % |
| Lexington Avenue | 8.88 | 209.0° | 180° | 100 % |
| Third Avenue | 8.59 | 29.1° | 0° | 100 % |
| Broadway south of W 59th St | 7.85 | 203.1° | 180° | 93.5 % |

**Divided highways** (opposing one-way carriageways on a north–south axis; 4 of 4 pass):

| highway | one-way km | northbound km | southbound km | N–S share |
|---|---:|---:|---:|---:|
| FDR Drive | 34.49 | 11.77 | 14.09 | 75.0 % |
| West Street (West Side Hwy south) | 8.56 | 4.30 | 4.26 | 100 % |
| Twelfth Avenue (West Side Hwy north) | 9.81 | 4.75 | 4.79 | 97.3 % |
| Henry Hudson Parkway | 24.89 | 11.96 | 12.76 | 99.3 % |

---

## 11. Runtime binaries (§15)

`runtime/roadgraph.nycb` — 104.19 MB, 8 sections: nodes 79,291 · segments 122,235 · vertices 3,910,302 ·
lanes 381,971 · lane_links 469,754 · junction_lanes 469,754 · yield_links 588,201 · strtab 148,757 bytes.
`runtime/signals.nycb` — 1.74 MB: controllers 19,814 · phases 39,649.

Every record layout is declared as a naturally aligned numpy dtype in the field order of §15 and its `sizeof` is
asserted at import time; the measured offsets are exactly the C++17 struct layout:

| section | sizeof | field offsets |
|---|---:|---|
| nodes | 24 | id 0, x 8, y 12, z 16, control 20, signal_source 21, pad 22 |
| segments | 48 | id 0, from_node 8, to_node 16, first_vertex 24, vertex_count 28, rw_type 32, traffic_dir 33, travel_lanes 34, park_lanes 35, width_m 36, speed_mph 40, bike_lane 41, surface 42, borough 43, name_str 44 |
| vertices | 12 | x 0, y 4, z 8 |
| lanes | 48 | id 0, segment_id 8, index_from_center 16, direction 17, kind 18, pad 19, width_m 20, speed_mps 24, first_vertex 28, vertex_count 32, first_succ 36, succ_count 40 |
| lane_links | 8 | lane_id 0 |
| junction_lanes | 48 | id 0, from_lane 8, to_lane 16, turn 24, pad 25, signal_group 28, first_vertex 32, vertex_count 36, first_yield 40, yield_count 44 |
| yield_links | 8 | lane_id 0 |
| controllers | 32 | node_id 0, controller_id 8, cycle_s 12, offset_s 16, first_phase 20, phase_count 24 |
| phases | 28 | group 0, green_s 4, yellow_s 8, allred_s 12, ped_walk_s 16, ped_flash_s 20, lpi_s 24 |

The same table is written machine-readably to `runtime/nycb_layout.json` (with the 24-byte header and 40-byte
index-entry layouts) so `core/io/NycbReader.h` can be checked against this writer mechanically.

`runtime/export.py` also provides the reference **Python reader** (`read_roadgraph`, `read_signals`,
`segment_polyline`, `lane_successors`, `junction_yields`). `test_roadgraph_binary_matches_the_parquet` and
`test_signals_binary_matches_the_parquet` read the produced binaries back and assert, against the parquet:
all 122,235 segment ids/end nodes/widths, decoded street names, sampled polylines to 2 cm, all 79,291 node ids and
control bytes, sampled lane successor lists, sampled junction yield lists, that
Σ`vertex_count` over segments + lanes + junction lanes equals the `vertices` section length, and that every
controller's phase slice matches the parquet phase list.

---

## 12. Tests

`pipeline/tests/test_roads.py` — **55 passed** in 26 s. `tests/test_world_integration.py` — **18 passed**.

Unit (no data): name normalisation across CSCL/LION/DOT/OSM spellings; level-code → height; offset polylines
(exact 3 m offset, mitre limit at corners); Bézier connector tangents; heading conventions; lane cross-sections
over the width × lane-count × direction grid, including the guarantee that no lane is ever emitted below its
physical minimum and that a narrow street loses parking before travel lanes; signal group assignment and exact
cycle closure with/without LPI and Barnes; DOT sheet-size parsing; MUTCD family classification; sign stacking
heights; bridge name matching (accepts "BROOKLYN BR PED PATH", rejects "FDR DR NB EN BROOKLYN BR", "BROADWAY",
"GEORGE WASHINGTON BR" for "WASHINGTON BR", "HIGH BR PARK PATH"); tile clipping conserves area exactly; A* on a
synthetic grid finds the 800 m shortest path, detours around a one-way column, and reports failure for a
disconnected pair; one-way audit; component counting; NYCB container round-trip and error handling; terrain
sampling including the tile-boundary fallback; and the terrain-lift idempotency proof.

Artefact tests: contract validation of all six tables, exact §7 column types, 3-D geometry inside the project
scope, enum ranges, node/segment referential integrity, lanes inside their segment corridor and never below the
per-kind minimum width, lane successors referencing real lanes (parking lanes never connect), junction lanes
referencing real lanes, signal coverage and per-controller cycle closure, sign ranges and family coverage
(only real DOT records may exceed a 2.5 m panel), all 53 crossings present and connected, the connectivity report,
per-tile pavement bounds, and the two binary round-trips.

---

## 13. Gaps and decisions, stated plainly

1. **Signals are a union, not a published dataset** (ADR-007). 19,814 signal nodes = 14,466 clusters against DOT's
   published ~13,700 signalised intersections. 1,666 (8.4 %) are inferred and flagged `signal_source = 4`;
   1,282 rest on a retiming corridor plus a through-crossing test. Phasing is the DOT *standard*, not per-controller
   timing plans, which DOT does not publish.
2. **Regulatory signs are generated.** DOT publishes parking regulation signs only; ONE WAY, DO NOT ENTER, STOP,
   YIELD and most SPEED LIMIT signs (123,891 rows, 19.6 % of the layer) have derived positions and carry
   `source = 2`. Their existence and control are real; the exact pole positions are not.
3. **Crosswalk polygons are derived** (148,674 rows, `source = 1`); no published crosswalk geometry was available.
   Pavement kind 7 (driveway) is not produced at all.
4. **Curb is stored as a 0.30 m buffered line**, because the contract types pavement as polygons and DoITT
   publishes the curb as a line layer.
5. **Attribute inference**: 7.4 % of widths, 7.1 % of lane counts and 17.4 % of posted speeds are inferred and
   flagged in `width_source` / `lanes_source` / `speed_source`. 3,234 lane stacks are wider than the published
   `streetwidth` because CSCL's own lane counts do not fit its own width field.
6. **8 % of the drivable network is outside the largest strongly connected component** — gated, private and park
   roads that CSCL records but that do not join the public network. 0.83 % of travel lanes end without a successor.
7. **Bike lanes on one-way streets are placed on the right of travel**; NYC also uses left-side lanes (e.g. on
   avenues with a left-side protected lane). CSCL's `bike_trafdir` does not say which side, so this is a documented
   simplification affecting the side, never the presence, of 14,188 bike lanes.
8. **The pavement layer was produced by the 12:11 run of this same code**; between that run and the final rebuild,
   another stage deleted `plan_roadbed`, `plan_curb`, `plan_sidewalk` and `plan_pavement_edge` from `data/raw`
   (2.1 GB) to free disk. The final rebuild therefore ran with `--no-pavement` and the 972 tile files are
   unchanged; the numbers in §8 were recomputed by reading those files back, not copied from a log. Re-running
   `python -m nycsim_pipeline.roads.pavement` after re-downloading those four sources reproduces them.
9. **Hell Gate Bridge** is a rail structure and CSCL only carries 270 m of it; **Ocean Avenue Bridge** is a
   footbridge. Both are in the index, correctly typed, and neither is drivable.

---

## 14. For the next agent

* Road z is now **absolute NAVD88 metres**. If the terrain stage rewrites `tiles/*/terrain.png`, re-run
  `python -m nycsim_pipeline.roads.apply_terrain_z` and then `python -m nycsim_pipeline.runtime.export`; both are
  idempotent and take ~2.5 minutes together.
* Extension columns beyond §7 that consumers may rely on: `segments.{drivable, length_m, name_norm, z_source,
  z_from, z_to, width_source, status, nonped, bike_trafdir, node_source, terrain_applied}`,
  `nodes.{degree, degree_drivable, names, names_norm, synthetic, vintersect, signal_sources_mask, barnes_exclusive,
  lpi, cbd, borough}`, `lanes.offset_m`, `junction_lanes.{junction_lane_id, node_id, from_segment, to_segment}`,
  `signs.{ground_z, mutcd_family, on_street, side_of_street, dot_order_number, dot_distance_ft, design_voided}`,
  `pavement.{area_m2, source, source_id, feat_code}`. `nodes.signal_source = 255` means "not signalised".
* `roads/graph.py` is reusable: `RoadGraph(seg, nodes).astar(a, b)`, `find_intersection("5 AVE", "E 42 ST", 1)`,
  `one_way_audit`, `dead_end_lanes`, `undirected_components`.
* The C++ side should validate `core/io/NycbReader.h` against `data/processed/runtime/nycb_layout.json`.
* Licences of everything read: NYC Open Data (CSCL, LION, DOT signs/LPI/Barnes/retiming/speed limits, bike routes,
  bus lanes, truck routes, pedestrian plazas, street-construction permits, DoITT planimetrics) — public domain /
  NYC Open Data Terms of Use; OpenStreetMap — ODbL 1.0, © OpenStreetMap contributors. All are recorded with URL
  and SHA-256 in `data/manifest/downloads.json`; every artefact above is recorded in `data/manifest/processed.json`.

---

## 15. Runtimes (this container, 4 vCPU shared with five other agents, load average ~35)

| step | s |
|---|---:|
| CSCL load + type | 44.0 |
| LION load | 46.2 |
| node assignment + datum shift | 12.1 |
| OSM caches (reused) | 5.5 |
| segments | 75.1 |
| signals | 88.5 |
| lanes | 37.9 |
| junction lanes | 190.7 |
| signs | 136.7 |
| write + contract validation | 12.9 |
| bridges/tunnels | 8.2 |
| connectivity + A* | 3.1 |
| runtime binaries | 10.6 |
| manifest | 2.0 |
| **total (without pavement)** | **673.4** |
| pavement (earlier pass, same code) | 366.3 |
| `apply_terrain_z` | 107.9 |
| `runtime.export` (standalone) | 10.0 |

Peak RSS observed during the full pass: 2.5 GB.
