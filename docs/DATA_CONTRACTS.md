# Data Contracts

All processed artefacts live under `data/processed/`. Formats: Apache Parquet (tabular, snappy), GeoParquet (geometry as WKB in `geometry` column, CRS `NYC_TM` unless stated), 16-bit PNG (heightmaps), glTF 2.0 binary `.glb` (meshes), JSON (small metadata). Every file has a sibling entry in `data/manifest/processed.json` with SHA-256, row count, producer stage, producer git commit and source manifest ids. Consumers must fail loudly on a schema mismatch (`schema_version` field on every JSON, Parquet metadata key `nycsim.schema`).

Length unit everywhere: metres. Angles: degrees, 0 = east, counter-clockwise (mathematical) unless the field name ends in `_heading` (0 = north, clockwise, compass). Time: ISO-8601 UTC.

## 1. `crs.json`
```json
{"schema_version": 1, "name": "NYC_TM", "proj4": "+proj=tmerc +lat_0=40.7 +lon_0=-73.95 +k=1 +x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs",
 "vertical_datum": "NAVD88 metres", "tile_size_m": 1000, "tile_name_format": "t_{tx}_{ty}"}
```

## 2. `tiles/index.parquet`
| column | type | meaning |
|---|---|---|
| tile | string | `t_{tx}_{ty}` |
| tx, ty | int32 | grid index (floor(x/1000), floor(y/1000)) |
| x0, y0 | float64 | south-west corner in NYC_TM |
| borough_codes | list<int8> | 1 MN 2 BX 3 BK 4 QN 5 SI 6 NJ 0 water |
| n_buildings, n_road_segments, n_props, n_trees | int32 | content counts |
| has_terrain, has_water, has_land | bool | |
| z_min, z_max | float32 | terrain range |

## 3. Terrain — `tiles/{tile}/terrain.png` + `terrain.json`
* PNG: 16-bit grayscale, 501 × 501 samples (2 m spacing, inclusive edges, north row first).
* `terrain.json`: `{"schema_version":1,"tile":"t_-3_7","z_min_m":-2.1,"z_scale_m":0.0025,"samples":501,"spacing_m":2.0,"sources":["3dep_19","spot_elev","bldg_ground"],"water_level_m":0.0}`
* Elevation `z = z_min_m + value × z_scale_m`.

## 4. Water — `water/hydrography.parquet` (GeoParquet, polygons)
| column | type |
|---|---|
| water_id | int64 |
| kind | string: river, bay, ocean, lake, pond, canal, basin |
| name | string |
| tidal | bool |
| geometry | polygon |
`water/shoreline.parquet` (lines, `kind`: natural, bulkhead, pier, riprap), `water/structures.parquet` (polygons: pier, dock, wharf, jetty, seawall).

## 5. Buildings — `tiles/{tile}/buildings.parquet`
| column | type | source / notes |
|---|---|---|
| bin | int64 | Building Identification Number (primary key) |
| bbl | int64 | tax lot |
| borough | int8 | 1–5 (6 = NJ) |
| footprint | polygon WKB (NYC_TM) | real, cleaned |
| ground_z | float32 | metres NAVD88 |
| roof_z | float32 | metres NAVD88 (top of roof, ex bulkhead) |
| height | float32 | roof_z − ground_z |
| floors | int16 | PLUTO numfloors or inferred |
| floor_height | float32 | (height − ground_floor_height) / (floors − 1) |
| ground_floor_height | float32 | |
| year_built | int16 | |
| bldg_class | string(2) | PLUTO `bldgclass` e.g. `C1`, `D4`, `O4`, `A1` |
| land_use | int8 | PLUTO landuse 1–11 |
| roof_type | int8 | 0 flat, 1 gable, 2 hip, 3 mansard, 4 shed, 5 sawtooth, 6 complex(CityGML mesh), 7 dome, 8 barrel |
| roof_mesh_ref | string | CityGML-derived roof mesh id in `tiles/{tile}/roofs.glb` or empty |
| facade_class | int16 | see `facade_classes.json` |
| material_primary | int8 | 0 red brick 1 brown brick 2 tan brick 3 white glazed brick 4 brownstone 5 limestone 6 terracotta 7 cast iron 8 glass curtain 9 concrete 10 stucco 11 vinyl siding 12 wood clapboard 13 stone rubble 14 metal panel 15 granite 16 precast |
| material_secondary | int8 | same enum, trim |
| window_type | int8 | kit enum |
| window_cols | int16 | windows across primary facade |
| window_rows | int16 | usually floors − 1 |
| has_fire_escape | bool | |
| has_stoop | bool | |
| has_cornice | bool | |
| has_storefront | bool | ground floor commercial |
| storefront_names | list<string> | real business names (OSM/DCWP/DOHMH) |
| storefront_kinds | list<int8> | 0 bodega 1 deli 2 pharmacy 3 restaurant 4 bar 5 nail/hair 6 laundromat 7 bank 8 clothing 9 electronics 10 grocery 11 hardware 12 coffee 13 pizza 14 dry cleaner 15 generic retail 16 office lobby 17 residential lobby 18 garage door 19 vacant |
| has_water_tower | bool | |
| rooftop_units | int8 | count of HVAC/bulkhead kit items |
| has_scaffold | bool | active DOB sidewalk shed permit |
| awning_text | string | |
| landmark_id | string | LPC LP-number or empty |
| landmark_model | string | script id in `blender/landmarks/` if hand-modelled |
| osm_id | int64 | matched OSM way/relation or 0 |
| name | string | building name (footprint `name` / OSM / LPC) |
| lit_seed | uint32 | deterministic window-lighting seed |
| fidelity | uint16 | bitfield, see §5.1 |
| primary_facade_heading | float32 | compass heading of street-facing facade |
| street_segment_id | int64 | nearest centerline `physicalid` |
| address | string | house number + street from PLUTO/PAD |

### 5.1 `fidelity` bitfield
| bit | name | meaning when set |
|---|---|---|
| 0 | FOOTPRINT_REAL | footprint from OTI dataset (always set) |
| 1 | HEIGHT_REAL | height from LiDAR `height_roof` |
| 2 | ROOF_REAL | roof geometry from CityGML LOD2 |
| 3 | FLOORS_REAL | floors from PLUTO |
| 4 | YEAR_REAL | year built from PLUTO/footprint |
| 5 | MATERIAL_REAL | material from OSM tag or LPC designation report class |
| 6 | SIGNAGE_REAL | at least one real business name attached |
| 7 | LANDMARK_MODEL | hand-scripted model replaces shell |
| 8 | SCAFFOLD_REAL | scaffold from active permit |
| 9 | GROUND_REAL | ground elevation from LiDAR field |
| 10 | FACADE_INFERRED | facade class from rules (set whenever bit 5 is clear) |
| 11 | HEIGHT_INFERRED | height derived from floors or neighbours |
| 12 | FLOORS_INFERRED | floors derived from height |

## 6. Kit placements — `tiles/{tile}/kit_placements.bin` (+ `.json` header)
Little-endian records, 40 bytes each:
```
uint32 kit_id; int64 bin; float32 x, y, z; float32 yaw_deg; float32 scale; uint32 variant_seed; uint32 flags
```
`kit_catalog.json` maps `kit_id` → glb path, category, bounds.

**Who owns the id space.** The exported Blender catalog (`blender_out/kit/catalog/*.json`) is the authority on which pieces exist. The numeric registry `data/processed/facade/kit_ids.json` is *generated from it*: pieces are grouped by the catalog's own `category`, sorted by catalog `id` within each group, and numbered `kit_id = (category_index + 1) × 200 + index_within_category`. Every registry entry carries `catalog_id` (the exporting catalog's `id`, verbatim) and `glb` (its path), so a numeric id in a placement record always resolves to a file that exists. A rule that needs a piece the kit does not export must leave it out of the registry and report the gap — never emit an id that resolves to nothing. Enforced by `tests/test_world_integration.py::test_kit_placements_are_populated_and_reference_real_kit_pieces`. flags bit0 = lit at night, bit1 = animated, bit2 = interior-visible.

## 7. Roads — `roads/segments.parquet` (GeoParquet, lines)
| column | type | notes |
|---|---|---|
| segment_id | int64 | CSCL `physicalid` |
| from_node, to_node | int64 | LION node ids |
| geometry | linestring 3D | z from level code + terrain, ramps interpolated |
| street_name | string | `full_street_name` |
| rw_type | int8 | 1 street 2 highway 3 bridge 4 tunnel 5 boardwalk 6 path 7 step street 8 driveway 9 ramp 10 alley 11 unknown 12 non-physical 13 U-turn 14 ferry |
| traffic_dir | int8 | 0 two-way 1 forward(FT) 2 backward(TF) 3 none |
| travel_lanes, park_lanes, total_lanes | int8 | |
| width_m | float32 | curb-to-curb |
| posted_speed_mph | int8 | |
| bike_lane | int8 | 0 none 1 protected 2 standard 3 sharrow 4 greenway |
| bus_lane | bool | |
| truck_route | int8 | |
| level_from, level_to | int8 | grade separation code |
| surface | int8 | 0 asphalt 1 concrete 2 cobble/belgian block 3 steel grate 4 gravel 5 boardwalk |
| borough | int8 | |
| speed_source, lanes_source | int8 | 0 real 1 inferred |

`roads/nodes.parquet`: `node_id, x, y, z, is_signalized, signal_source(0 osm,1 dot_lpi,2 dot_barnes,3 dot_retiming,4 inferred), has_stop_sign, has_all_way_stop, intersection_name, control(0 none,1 signal,2 stop,3 all-way,4 yield)`

`roads/lanes.parquet`: `lane_id, segment_id, index_from_center, direction(±1), width_m, kind(0 travel,1 parking,2 bike,3 bus,4 turn,5 shoulder), geometry(linestring 3D), speed_mps, successors(list<int64>), predecessors(list<int64>)`

`roads/junction_lanes.parquet`: connector lanes through intersections with `from_lane, to_lane, turn(0 straight,1 left,2 right,3 uturn), signal_group, yield_to(list<int64>), geometry`

`roads/signals.parquet`: `node_id, controller_id, cycle_s, offset_s, phases(list<struct{group,green_s,yellow_s,allred_s,ped_walk_s,ped_flash_s,lpi_s}>)`

`roads/signs.parquet`: `sign_id, node_id, segment_id, x, y, z, facing_heading, mutcd_code, text, arrow(0 none,1 left,2 right,3 both), sign_w_m, sign_h_m, support(0 pole,1 lamp post,2 signal mast,3 wall), source(0 DOT current,1 generated street name,2 inferred)`

`roads/pavement/{tile}.parquet`: polygons `kind(0 roadbed,1 sidewalk,2 median,3 plaza,4 curb,5 crosswalk,6 parking lot,7 driveway)`, `surface`, `roughness_seed`.

## 8. Furniture — `tiles/{tile}/props.parquet`
`prop_id, kind(int16 enum in props_catalog.json), x, y, z, heading, variant, text, source(0 dataset,1 rule), dataset_id, species(for trees), dbh_cm, height_m`

Trees (`kind` 0) come from **two** inventories and `dataset_id` is what separates them: `street_trees_2015` (the
census — species and DBH real, height allometric) and `osm_newyork_pbf` (the extract's `natural=tree` nodes, the
only trees inside parks — height from the OSM `height` tag where there is one, `dbh_cm` always 0 because OSM
publishes no trunk diameter in one unit convention). An OSM tree is never placed within the measured cross-source
radius of a census tree; the radius and how it was measured are in `props_catalog.json` under `dedupe.cross_source`.
The point layer behind the second source is `osm/trees.parquet` and the unplaced `natural=tree_row` lines are
`osm/tree_rows.parquet`, both written by `python -m nycsim_pipeline osm_trees`.

## 9. Transit
`transit/bus_routes.parquet` (route_id, short_name, long_name, borough, shape geometry, headway by hour list<int16>), `transit/bus_stops.parquet` (stop_id, x, y, z, name, routes list, has_shelter), `transit/rail_structures.parquet` (elevated/embankment/open-cut segments with track geometry and deck height), `transit/ferry_routes.parquet`, `transit/subway_entrances.parquet` (entrance_id, x, y, z, lines list<string>, kind(stair, escalator, elevator), has_globe(0 none,1 green,2 red)).

## 10. Traffic calibration — `traffic/density.parquet`
`nta_code, hour(0–23), dow(0 weekday,1 sat,2 sun), veh_per_km_lane, ped_per_m2_sidewalk, taxi_share, truck_share, bus_share, bike_share, source`

## 11. Landmarks — `landmarks/landmarks.json`
Array of `{id, name, bins[], lp_number, script, footprint_source, height_m, height_source, notes, fidelity_statement}`.

## 12. Live data snapshots — `live/*.json` (schema shared with `core/live` C++ structs)
`weather.json`: `{schema_version, observed_at, station, source("nws"|"open_meteo"|"metar"|"stale"), temp_c, dewpoint_c, rh, wind_mps, wind_gust_mps, wind_dir_deg, precip_type("none"|"rain"|"snow"|"sleet"|"freezing_rain"|"drizzle"), precip_rate_mmph, cloud_cover(0..1), visibility_m, pressure_hpa, snow_depth_cm, thunder(bool), fetched_at, stale_age_s}`
`esb_lights.json`: `{date, colors[], reason, source_url}`
`tides.json`: `{station, current_speed_mps, current_dir_deg, water_level_m, predicted_at}`

## 13. Blender exports — `blender_out/`
`kit/{kit_id}.glb` (Y-up, metres, origin at ground contact / wall contact point, `extras.nycsim = {kit_id, category, bounds}`), `landmarks/{id}.glb` (tile-local origin recorded in extras), `vehicles/{id}.glb` (origin at ground under rear-axle centre, +X forward in Blender before export), `character/{id}.glb` (rig + animations as glTF animations), `tiles/{tile}/tile_buildings.glb`, `tiles/{tile}/roofs.glb`.
**Door pivots and mechanisms (§13a).** A `Door_*` node's origin sits on the **forward vertical edge of its aperture**, with local +X running rearward along the leaf. This holds for a bifold or plug door too: it is one node on that same edge, at the outer leaf's hinge, and both the coach and the school bus satisfy it geometrically without a waiver. The mechanism itself is named per panel in the catalog under `door_kind`, one of `hinged`, `sliding`, `bifold`, `rear cargo door`, `boot lid` or `front-hinged bonnet`, so the engine knows whether to rotate, translate or fold about that edge.

**Per-vertex custom attributes.** glTF names application-specific attributes with a leading underscore, and Blender's exporter drops any that do not follow it, so a building shell ships `_BIN`, `_FACADE_CLASS`, `_FLOORS`, `_FLOOR_HEIGHT`, `_GROUND_FLOOR_HEIGHT`, `_IS_STOREFRONT` and the lighting seed split as `_LIT_SEED_HI`/`_LIT_SEED_LO` (value = `hi × 65536 + lo`, because glTF stores attributes as float32 and a uint32 seed cannot round-trip). Note also that glTF flips V, so height above grade in a wall UV is `1 − V`, not `V`.

Level-of-detail meshes may be shipped either as extra meshes named `<id>_LOD1` inside the parent file or as sibling files `<id>_LOD1.glb`, `<id>_LOD2.glb`; both forms are covered by the parent's single catalog entry, which lists the LODs it owns. Importers resolve a sibling by stripping the `_LOD<n>` suffix, matched case-insensitively (`_LOD1` is the canonical spelling; `_lod1` is accepted).

**Building-shell materials.** One glTF material per material class, named `NYCSIM_<class>` for the 20 classes
of §5.1 — one mesh per (tile, LOD, material class), as ARCHITECTURE §4.3 requires. Each carries the analytic
PBR set authored in `blender/buildings/shellmat.py`: `baseColorFactor`, `metallicFactor`, `roughnessFactor`
plus `KHR_materials_specular` and `KHR_materials_ior`. No textures and no `COLOR_0`. **Per-building variation
lives in the shader, not in the file**: `k = fract(sin(_LIT_SEED_HI·12.9898 + _LIT_SEED_LO·78.233)·43758.5453)·2 − 1`
scales the base colour by `1 + tone_amp·k` and offsets roughness by `rough_amp·k`, with the two amplitudes
per class in `shellmat.MATERIALS`. An engine master material that ignores it gets the class average, which is
what a plain glTF viewer shows. The spandrel band a curtain wall needs is **not** in the geometry either;
`shellmat.floor_band_uv` states the expression an engine should use over the metre UV `v` (height above
`ground_z`) with `_FLOOR_HEIGHT` / `_GROUND_FLOOR_HEIGHT`.

Each `.glb` carries `asset.extras.nycsim = {"generator_script": ..., "git_commit": ..., "schema_version": 1}`.

## 14. UE import manifest — `unreal_manifest.json`
Lists every glb/png/parquet with target content path `Game/NYCSim/...`, import settings id and dependency order. Consumed by `unreal/NYCSim/Content/Python/import_world.py`.

## 15. Runtime binaries for `core/` (consumed by C++ without Arrow)
Container format `NYCB`: little-endian, **naturally aligned C structs** (not packed). Header is 24 bytes: `{char magic[4]="NYCB"; uint32 version=1; uint32 section_count; /* 4 bytes padding */ uint64 index_offset}` — `index_offset` sits at byte 16 because a `uint64` aligns to 8. Sections start on 8-byte boundaries. The authoritative field-by-field layout is emitted next to the data as `data/processed/runtime/nycb_layout.json`; a reader must agree with that file, and the C++ side maps these structs directly. index = array of `{char name[16]; uint64 offset; uint64 size; uint32 element_size; uint32 element_count}`. Strings are stored in a per-file string table section `"strtab"` (uint32 offsets into a NUL-separated blob). Produced by `pipeline/nycsim_pipeline/runtime/export.py`, read by `core/io/NycbReader.h`. Floats are float32 unless noted; coordinates are NYC_TM metres.

* `runtime/roadgraph.nycb`: sections `nodes` {int64 id; float x,y,z; uint8 control; uint8 signal_source; uint16 pad}, `segments` {int64 id; int64 from_node,to_node; uint32 first_vertex,vertex_count; uint8 rw_type,traffic_dir,travel_lanes,park_lanes; float width_m; uint8 speed_mph,bike_lane,surface,borough; uint32 name_str}, `vertices` {float x,y,z}, `lanes` {int64 id; int64 segment_id; int8 index_from_center,direction,kind,pad; float width_m,speed_mps; uint32 first_vertex,vertex_count; uint32 first_succ,succ_count}, `lane_links` {int64 lane_id}, `junction_lanes` {int64 id; int64 from_lane,to_lane; uint8 turn; uint8 pad[3]; int32 signal_group; uint32 first_vertex,vertex_count; uint32 first_yield,yield_count}, `yield_links` {int64 lane_id}, `strtab`.
* `runtime/signals.nycb`: `controllers` {int64 node_id; int32 controller_id; float cycle_s,offset_s; uint32 first_phase,phase_count}, `phases` {int32 group; float green_s,yellow_s,allred_s,ped_walk_s,ped_flash_s,lpi_s}.
* `runtime/tiles.nycb`: `tiles` {int32 tx,ty; float z_min,z_max; uint32 n_buildings,n_props; uint8 flags(has_terrain=1,has_water=2,has_land=4); uint8 borough_mask; uint16 pad}. One record per row of `tiles/index.parquet`, New Jersey included; `borough_mask` sets bit *b* for each borough code *b* the tile carries (§2, plus code 7 "New York State outside NYC"), so a water-only tile has bit 0 set. `n_buildings` and `n_props` are the rows actually present in the tile's own artefacts — `tiles/{tile}/buildings.parquet` plus `buildings_nj.parquet`, and `props.parquet` — not the same-named columns of `tiles/index.parquet`, which the terrain stage that writes the index does not own and leaves at zero.
* `runtime/transit.nycb`: `bus_routes` {uint32 name_str; uint32 first_vertex,vertex_count; uint32 first_stop,stop_count; uint16 headway_min[24]}, `bus_stops` {int64 id; float x,y,z; uint32 name_str}, `route_stops` {int64 stop_id}, `vertices`, `strtab`.
* `runtime/density.nycb`: `cells` {uint32 nta_str; uint8 hour,dow; uint16 pad; float veh_per_km_lane,ped_per_m2,taxi_share,truck_share,bus_share,bike_share}, `nta_polys` (`{uint32 nta_str; uint32 first_vertex,vertex_count}` + `vertices`), `strtab`.
* `runtime/pois.nycb`: `pois` {float x,y; uint32 addr_str}, `strtab` — addresses for GPS, over the PLUTO/PAD `address` the buildings stage joined onto each footprint (`buildings/buildings_base.parquet`, §5.2). The point is that table's `centroid_x`/`centroid_y`, the footprint centroid the tile is assigned from. A building whose `address` is `""` (unknown, §5.2) has no record; identical (address, position) pairs are written once.
* `runtime/landmarks.nycb`: `points` {float x,y; uint32 name_str}, `strtab` — named landmarks for GPS, over `buildings/landmark_footprints.parquet` (the §11 landmark set matched to footprints), positioned at its `centroid_x`/`centroid_y`. The section name and record are fixed by the reader, `RoadNetwork::loadLandmarks()` in `unreal/NYCSim/Source/NYCSimRuntime/Private/CoreAdapter/GameplayRoadNetwork.cpp`: it looks for `points`, falls back to a section named `landmarks`, requires `element_size` ≥ 12 and a present `strtab`, and reads x, y, name_str at offsets 0, 4, 8. A landmark with an empty name has no record — the reader skips an empty label anyway.

---

## 5.2 Buildings ingest extension columns — APPENDED by the buildings stage (stage 3 data part)

*Appended section. These columns are written by `pipeline/nycsim_pipeline/buildings/build.py` into
`buildings/buildings_base.parquet` and every `tiles/{tile}/buildings.parquet` in addition to the §5 columns it derives
(`bin, bbl, borough, footprint, ground_z, roof_z, height, floors, floor_height, ground_floor_height, year_built,
bldg_class, land_use, has_storefront, storefront_names, storefront_kinds, has_scaffold, landmark_id, osm_id (0 until the
OSM stage), name, lit_seed, fidelity, primary_facade_heading, address, tile, tx, ty`). The §5 columns owned by later
stages (`roof_type, roof_mesh_ref, facade_class, material_*, window_*, has_fire_escape, has_stoop, has_cornice,
has_water_tower, rooftop_units, awning_text, landmark_model, street_segment_id`) are **absent** from these files and are
added by the citygml / facade-rules / roads stages. Parquet metadata: `nycsim.schema = "buildings/1"`, GeoParquet 1.1
`geo` metadata with `primary_column = "footprint"` (CRS NYC_TM as PROJJSON). Rows are sorted by `(tile, bin)`.*

| column | type | meaning |
|---|---|---|
| feature_code | int16 | OTI footprint feature code: 2100 building, 5100 building under construction, 5110 garage, 1000–1006 other structure codes as published |
| footprint_area | float32 | polygon area, m² |
| centroid_x, centroid_y | float64 | footprint centroid, NYC_TM m (the tile is assigned from this point) |
| pluto_joined | bool | a MapPLUTO lot record was joined (by `mappluto_bbl`, else `base_bbl`) |
| n_bldgs_on_lot | int16 | footprints sharing this `bbl` |
| is_primary_on_lot | bool | largest non-garage footprint on the lot; lot-level PLUTO attributes (`numfloors`, `yearbuilt` fallback, retail evidence) are applied only to it |
| height_source | int8 | 0 LiDAR `height_roof`, 1 PLUTO floors × class storey height, 2 median of 10 nearest LiDAR heights |
| floors_source | int8 | 1 PLUTO `numfloors` (consistent with height), 2 derived from height |
| year_source | int8 | 0 footprint `construction_year`, 1 PLUTO `yearbuilt`, −1 unknown (`year_built` = 0) |
| ground_source | int8 | 0 LiDAR `ground_elevation`, 3 Building Elevation & Subgrade `z_grade`, 2 median of 10 nearest LiDAR grounds |
| facade_heading_method | int8 | 0 free (non party-wall) merged edge chosen with lot-position bias, 1 longest free edge (no lot centroid), 2 longest edge (no free edge ≥ 2 m) |
| first_floor_offset | float32, nullable | first-floor elevation minus grade, m (bsin-59hv `z_floor − z_grade`); NaN unknown |
| has_subgrade | int8 | bsin-59hv subgrade space flag: 1 yes, 0 no, −1 unknown |
| lot_frontage, bldg_frontage, bldg_depth | float32, nullable | PLUTO `lotfront/bldgfront/bldgdepth` in metres; NaN unknown |
| nta | string | NTA 2020 code (bsin-59hv per BIN, else centroid-in-polygon of 9nt8-h7nd); empty if outside all NTAs |
| hist_district, hist_district_id | string | LPC historic district name and LP number containing the centroid; empty if none |
| lpc_style, lpc_material | string | LPC building database `STYLE1` / `MATERIAL1` for the BIN (real designation-report typology; input for `MATERIAL_REAL`) |
| storefront_sources | list<int8> | per `storefront_names` entry: 1 DCWP licence, 2 DOHMH restaurant |

Conventions used for §5 columns in these files: `floor_height` for single-storey buildings is the class storey height
(the contract formula divides by `floors − 1`); `ground_floor_height` = `height` when `floors` = 1; `year_built` = 0 and
`bldg_class` = "" / `land_use` = 0 / `address` = "" / `landmark_id` = "" mean unknown; `has_storefront` is set by PLUTO
class/land-use/retail-area evidence on the primary building or by an attached real business name.

## 5.3 Roof attributes — `buildings/roof_attrs.parquet` — APPENDED by the CityGML stage

*Appended section. Written by `pipeline/nycsim_pipeline/buildings/citygml_join.py`
(`python -m nycsim_pipeline citygml --join`). One row per distinct real BIN in `buildings_base.parquet`
(borough-placeholder BINs `x000000` are excluded because they cannot key a join). Parquet metadata
`nycsim.schema = "buildings_roof_attrs_v1"`, plus `nycsim.roof_attrs` with the enums, the inference rule and the
build summary. This is the table that fills the §5 columns `roof_type` and `roof_mesh_ref` and sets the §5.1
`ROOF_REAL` bit — see ADR-013 for why `roof_type` is not read straight out of CityGML. The buildings stage
applies it with one call: `df = citygml_join.attach_roof_columns(df)`.*

| column | type | meaning |
|---|---|---|
| bin | int64 | join key, unique |
| roof_type | int8 | §5 enum, resolved by the `roof_type_source` precedence below |
| roof_shape_measured | bool | the source really carries sloped roof geometry for this BIN. **False almost everywhere** (ADR-013): the model is a stack of horizontal plates, so the shape must come from typology. The facade and Blender shell stages read this to decide when to generate a gable/hip |
| n_roof_levels | int16 | distinct horizontal roof levels in the LOD2 solid — the genuinely measured signal (real setbacks, bulkheads, penthouses); 0 when no CityGML match |
| roof_level_z | list&lt;float32&gt; | height of each level, m NAVD88, ascending |
| roof_level_area | list&lt;float32&gt; | horizontal area of each level, m² |
| roof_slope_deg | float32 | area-weighted mean slope of the sloped roof faces (0 where the roof is all plates); NaN when no match |
| z_roof_max | float32 | highest CityGML roof vertex, m NAVD88; NaN when no match |
| roof_mesh_ref | string | `t_{tx}_{ty}/roofs.glb#bin_{bin}` when a LOD2 solid exists, else `""` (tile = the footprint tile from `buildings_base`) |
| citygml_match | bool | a CityGML LOD2 solid exists for this BIN — **this is the `ROOF_REAL` bit** |
| dz_vs_footprint_m | float32 | `z_roof_max − (ground_z + height)`; NaN when no match |
| roof_type_source | int8 | 0 citygml, 1 osm `roof:shape`, 2 inferred (PLUTO class + footprint/lot shape), 3 default flat |
| roof_inferred | bool | `roof_type_source >= 2` |
| roof_type_conf | float32 | measured precision of the source (1.0 real, 0.805 inferred, 0.0 default) |
| roof_pitch_deg | float32 | inferred pitch, 0 when not an inferred pitched roof |
| roof_ridge_deg | float32 | compass heading of the ridge line (0 = north), NaN when not pitched |
| roof_eave_dz_m | float32 | eave offset from `z_roof_max`, one full rise below it (≤ 0) |
| roof_ridge_dz_m | float32 | ridge offset from `z_roof_max`; always 0 — ADR-013 keeps the measured height as the ridge so overall building height stays real |
| z_ground_min | float32 | lowest CityGML ground vertex, m NAVD88; NaN when no match |
| tri_count | int32 | triangles in the LOD2 solid |
| citygml_da | int8 | delivery area the solid came from, 0 when no match |
| citygml_flags | uint16 | CityGML parser flag bitfield (`nycsim.citygml` metadata in `citygml/index.parquet`) |

The LOD2 solids themselves stay in `buildings/citygml/da{n}.parquet` (schema `citygml_solids_v1`: per-BIN
`tri_xyz` float32 blob + `tri_type`), with `buildings/citygml/index.parquet` (`citygml_index_v1`) as the
city-wide per-BIN index. A later Blender stage turns the solids into `tiles/{tile}/roofs.glb`.

**Per-level roof outlines are derived, not stored (consumer note).** `n_roof_levels`, `roof_level_z` and
`roof_level_area` say how high and how big each roof level is but not *where* it is, and the outline is what
stepped massing needs. It is recovered directly from `da{n}.parquet`: every `tri_type == 2` (roof) triangle is
exactly horizontal, so grouping the roof triangles by z and unioning each group **is** the level outline.
`blender/buildings/roofsteps.py` does this at build time — the outlines are **not** materialised into
`roof_attrs.parquet`, because they are ~10× the size of the table that would carry them, they are cheap to
recompute (about 2 s per tile), and the triangles they come from are already a published contract. The only
new file is `blender/buildings/citygml_tile_index.json`, a derived `da*.parquet → [tx, ty]` index so a tile
opens one delivery-area file instead of twenty; it is rebuilt by `roofsteps.build_tile_index(force=True)`.
Consumers that need the outlines should call `roofsteps.load_tile_steps(tile)` rather than re-deriving them.

---

## 12.1 Live snapshot extension — APPENDED by the live-services stage

*The keys of §12 are unchanged and remain the contract every consumer may rely on. The live services add
the fields below to the same documents (a superset, so a §12 reader is unaffected) plus two new documents.
Angles: `*_dir_deg` is mathematical (0 = east, counter-clockwise), `*_heading` is compass (0 = north,
clockwise). Times are ISO-8601 UTC with a trailing `Z`. Produced by `services/nycsim_live`, mirrored by
`core/weather` and `core/astro`; the exact formulas are in `docs/LIVE_ALGORITHMS.md`.*

`live/weather.json` additional keys:

| key | type | meaning |
|---|---|---|
| wind_from_heading | float, nullable | compass heading the wind blows **from**; null when calm or variable |
| wind_to_heading | float, nullable | compass heading of the air motion (= `wind_from_heading` + 180°) |
| snow_depth_source | "observed" \| "model" \| "none" | 4/sss group from a station, the snow-depth model, or no snow |
| snowfall_rate_cmph | float, nullable | fresh-snow accumulation rate |
| precip_rate_basis | "measured" \| "class" \| "trace" \| "model" \| "none" | provenance of `precip_rate_mmph` |
| obscuration | list of METAR codes | e.g. `["FG"]`, `["BR"]`, `["HZ"]`; empty when the air is clear |
| interpolated | bool | the NWS gridpoint forecast trend was applied between hourly observations |
| raw_text | string, nullable | the provider's own report (METAR string, NWS `textDescription`, `WMO <code>`) |
| provider_status | object | per provider: `"closed"`, `"half_open"` or `"open(<seconds>s)"` |

`live/esb_lights.json` additional keys: `schema_version`, `rgb` (list of `[r,g,b]`, one per resolved colour
name), `unknown_colors` (published names with no RGB mapping — never guessed), `hours` (as published, e.g.
`"sunset to 02:00"`), `fallback` (bool, signature white substituted), `fetched_at`.

`live/tides.json` additional keys: `schema_version`, `current_station`, `current_heading`, `current_phase`
(`flood` | `ebb` | `slack`), `water_level_datum` (`"NAVD88"`), `water_level_mllw_m`,
`water_level_observed_at`, `water_level_quality` (`p`/`v`), `navd88_minus_mllw_m`, `currents` (per station:
`id, name, water_body, lat, lon, speed_mps, heading, dir_deg, phase, velocity_cms, flood_heading,
ebb_heading, depth_m`), `next_tides` (`utc, kind(H|L), level_mllw_m, level_m`), `fetched_at`, `stale`,
`errors`.

`live/world_state.json` (new — derived render/behaviour parameters, `WorldMapper` → `core/weather`):
`{schema_version, updated_at_unix, source, observation_age_s, wetness(0..1), wetness_target, tau_used_s,
drying(bool), puddle_level(0..1), puddle_depth_mm, road_ice(bool), snow_depth_cm, snow_cover(0..1),
snow_cover_road(0..1), snow_melting(bool), plow_active(bool), salt_active(bool), fog_density(0..1),
haze_density(0..1), extinction_per_m, visibility_m, cloud_cover, wind_speed_mps, wind_gust_mps,
wind_from_heading, wind_to_heading, wind_vector_enu[3] (m/s, x=east y=north z=up),
wind_vector_ue[3] (m/s in UE axes: x=east, y=−north, z=up), umbrella_probability(0..1),
window_condensation(0..1), window_condensation_interior, window_condensation_exterior,
window_condensation_double, missing[] (observation fields that were null)}`.

`live/snow_state.json` (new — persistence for the snow-depth model):
`{schema_version, depth_cm, last_update_unix, source}`.

`live/overlay.txt` (new — the exact monospace text block the in-game debug overlay draws; produced by
`nycsim_live.debug_overlay`, 62-column headers, one field per line, `—` for every null).

## 5.4 Facade columns — APPENDED by the facade stage (ADR-004)

*Appended section. Written by `pipeline/nycsim_pipeline/facade/` (`python -m nycsim_pipeline.facade.build all`) into
`facade/facade_attrs.parquet` and into every `tiles/{tile}/buildings.parquet`. The stage **fills** the sixteen §5
columns the buildings stage deferred (`roof_type, roof_mesh_ref, facade_class, material_primary, material_secondary,
window_type, window_cols, window_rows, has_fire_escape, has_stoop, has_cornice, has_water_tower, rooftop_units,
awning_text, landmark_model, street_segment_id`), **overwrites** `osm_id` (from the footprint-overlap match against
`osm/buildings.parquet`) and `fidelity` (bits 2, 5, 10 and 13), and **appends** the provenance columns below. Every
buildings-stage column and the GeoParquet `geo` metadata are preserved unchanged; `nycsim.schema` stays `buildings/1`
and the stage adds `nycsim.facade.schema = "facade/1"` and `nycsim.facade.rules_version`.*

| column | type | meaning |
|---|---|---|
| facade_rule | int16 | 0-based index into `facade.rules.RULES` of the rule that classified the building — every class is traceable to a named, documented predicate |
| material_source | int8 | 0 OSM `building:material`, 1 OSM `building:colour` (shade refinement of a masonry wall only), 2 LPC `MATERIAL1`, 3 rule |
| frontage_source | int8 | 0 primary footprint run, 1 PLUTO `bldgfront`, 2 PLUTO `lotfront`, 3 sqrt(footprint area) |
| facade_frontage_m | float32 | frontage `window_cols` was computed from |
| bay_width_m | float32 | centre-to-centre window bay spacing of the class's window family |
| water_tower_kind | int8 | 0 none, 1 wooden 10,000 gal, 2 wooden 20,000 gal, 3 steel/enclosed |
| attached | int16 | party-wall facade runs (0 = free-standing); real footprint adjacency |
| n_free_runs | int16 | non-party-wall facade runs at least 1.2 m long |
| is_corner | bool | two street-facing free runs ≥ 4 m, normals 60–120° apart, nearest centrelines on two different streets |
| free_perimeter_m | float32 | total length of non-party-wall facade |
| street_frontage_m | float32 | total length of street-facing facade |
| storefront_kind_primary | int8 | storefront kind used for the ground-floor treatment (§5 `storefront_kinds` enum) |
| awning_real | bool | `awning_text` is a real business name; false means the generic wording for the kind |
| osm_iou | float32 | intersection-over-union of the matched OSM building, 0 when unmatched |
| n_placements | int32 | kit placement records this building owns in `kit_placements.bin` |
| roof_source | int8 | 0 CityGML, 1 OSM `roof:shape`, 2 facade rule (ADR-013), 3 default flat |
| roof_pitch_deg | float32 | roof pitch, 0 when flat |
| roof_ridge_heading | float32 | compass heading of the ridge line folded to [0, 180); 0 when flat |
| roof_eave_z | float32 | eave elevation, m NAVD88 — the ridge stays at the measured `roof_z` so the building's height is unchanged |

`fidelity` bit 13 `ROOF_INFERRED` (ADR-013) is set exactly where `roof_source == 2`.

## 6.1 Kit placement conventions — APPENDED by the facade stage

*Appended section; the record layout in §6 is unchanged. Each tile's `kit_placements.json` header repeats all of this
so a consumer never has to guess.*

* `kit_id` is derived **from the exported Blender kit catalog**: `kit_id = (index of the piece's category in
  `facade_params.KIT_CATEGORIES` + 1) × 200 + index of the catalog id inside that category, catalog ids sorted
  lexicographically`. `data/processed/facade/kit_ids.json` is the registry (`kit_id`, `category`, `catalog_id`, `glb`,
  `nominal_size_m`, the placement roles that use it); `data/processed/facade/kit_catalog_map.json` is the same map for
  the UE importer. Every id in a placement file names an asset that exists.
* `x, y` NYC_TM metres of the piece's contact point — the wall face for facade pieces, the roof deck for roof pieces,
  the sidewalk for stoops, storefronts and sheds.
* `z` NAVD88 metres, absolute, consistent with `ground_z` / `roof_z`.
* `yaw_deg` uses the contract's default angle convention (0 = east, counter-clockwise); it is the outward normal of the
  wall run for a facade piece.
* `scale` is a uniform scale for point pieces. For **run pieces** (cornice, parapet, string course, sign band,
  storefront bay, roll gate, awning, sidewalk shed) it is the along-run stretch factor relative to the piece's nominal
  width; runs longer than 12 nominal widths are split into several records so no instance is stretched further.
* `variant_seed` is derived from the building's `lit_seed` and the piece's address on the building (run, bay, floor);
  the kit picks weathering, glass tint and gate state from it. The whole file is a deterministic function of the
  inputs — the same inputs regenerate the same bytes.
* Records are sorted by `(bin, kit_id)`.

### 6.1.1 Sign faces — where the words come from

*Appended by the facade stage.* A kit piece whose catalog entry declares a `sign_face_slot` carries a
**runtime-swappable face**: one material slot whose name begins with `SIGN_FACE`, with UV 0..1 covering the visible
panel exactly (u to the reader's right, v upwards). The placement record carries the surface; the **text is never in
the placement stream**. Each family binds differently, and every tile's `kit_placements.json` header repeats this in
its `sign_face_binding` block:

| piece family | what its face carries |
|---|---|
| `storefront_sign_band` | blank. The legend for an instance is `awning_text` of the **same `bin`** in `tiles/{tile}/buildings.parquet`; `awning_real` says whether that string is a real business name (DCWP / DOHMH / OSM) or the generic New York trade wording for the storefront kind. Placed on the buildings whose `awning_text` is a real business name. |
| `storefront_sign_band_<kind>` | the generic trade wording for that storefront kind, baked. Placed only where `awning_real` is false and `awning_text` is exactly that wording. |
| `sign_led_*` | the LED pixel matrix and **no content at all**: the face models the display hardware. Placed only where the lot's MapPLUTO `zonedist1`..`zonedist4` is `C6-7T` (the Times Square core of the Special Midtown District, 59 lots city-wide). |
| `billboard_wall_mounted`, `billboard_rooftop` | blank floodlit vinyl. No source in this environment records what any New York bulletin carries, so the model states that a bulletin is mounted, never what it advertises. |

`flags` bit 0 (lit at night) is set on every sign placement and on the windows whose `lit_seed` draw put their lights
on. Because a glTF instance cannot switch a material from a flag, the kit exports a `win_<type>_lit` twin of every
window that has an interior card, and a lit window is placed as that piece; the two window types with no interior
card (`gothic_arched`, `through_wall_ac_sleeve`) keep the plain id.
