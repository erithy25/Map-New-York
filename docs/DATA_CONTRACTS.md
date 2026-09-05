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
`kit_catalog.json` maps `kit_id` → glb path, category, bounds. flags bit0 = lit at night, bit1 = animated, bit2 = interior-visible.

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
Each `.glb` carries `asset.extras.nycsim = {"generator_script": ..., "git_commit": ..., "schema_version": 1}`.

## 14. UE import manifest — `unreal_manifest.json`
Lists every glb/png/parquet with target content path `Game/NYCSim/...`, import settings id and dependency order. Consumed by `unreal/NYCSim/Content/Python/import_world.py`.

## 15. Runtime binaries for `core/` (consumed by C++ without Arrow)
Container format `NYCB`: little-endian; header `{char magic[4]="NYCB"; uint32 version=1; uint32 section_count; uint64 index_offset}`; index = array of `{char name[16]; uint64 offset; uint64 size; uint32 element_size; uint32 element_count}`. Strings are stored in a per-file string table section `"strtab"` (uint32 offsets into a NUL-separated blob). Produced by `pipeline/nycsim_pipeline/runtime/export.py`, read by `core/io/NycbReader.h`. Floats are float32 unless noted; coordinates are NYC_TM metres.

* `runtime/roadgraph.nycb`: sections `nodes` {int64 id; float x,y,z; uint8 control; uint8 signal_source; uint16 pad}, `segments` {int64 id; int64 from_node,to_node; uint32 first_vertex,vertex_count; uint8 rw_type,traffic_dir,travel_lanes,park_lanes; float width_m; uint8 speed_mph,bike_lane,surface,borough; uint32 name_str}, `vertices` {float x,y,z}, `lanes` {int64 id; int64 segment_id; int8 index_from_center,direction,kind,pad; float width_m,speed_mps; uint32 first_vertex,vertex_count; uint32 first_succ,succ_count}, `lane_links` {int64 lane_id}, `junction_lanes` {int64 id; int64 from_lane,to_lane; uint8 turn; uint8 pad[3]; int32 signal_group; uint32 first_vertex,vertex_count; uint32 first_yield,yield_count}, `yield_links` {int64 lane_id}, `strtab`.
* `runtime/signals.nycb`: `controllers` {int64 node_id; int32 controller_id; float cycle_s,offset_s; uint32 first_phase,phase_count}, `phases` {int32 group; float green_s,yellow_s,allred_s,ped_walk_s,ped_flash_s,lpi_s}.
* `runtime/tiles.nycb`: `tiles` {int32 tx,ty; float z_min,z_max; uint32 n_buildings,n_props; uint8 flags(has_terrain=1,has_water=2,has_land=4); uint8 borough_mask; uint16 pad}.
* `runtime/transit.nycb`: `bus_routes` {uint32 name_str; uint32 first_vertex,vertex_count; uint32 first_stop,stop_count; uint16 headway_min[24]}, `bus_stops` {int64 id; float x,y,z; uint32 name_str}, `route_stops` {int64 stop_id}, `vertices`, `strtab`.
* `runtime/density.nycb`: `cells` {uint32 nta_str; uint8 hour,dow; uint16 pad; float veh_per_km_lane,ped_per_m2,taxi_share,truck_share,bus_share,bike_share}, `nta_polys` (`{uint32 nta_str; uint32 first_vertex,vertex_count}` + `vertices`), `strtab`.
* `runtime/landmarks.nycb`, `runtime/pois.nycb` (addresses for GPS: `{float x,y; uint32 addr_str}` over PLUTO/PAD addresses).
