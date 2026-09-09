"""Prop kinds (``props_catalog.json``) — the int16 ``kind`` enum used by ``tiles/{tile}/props.parquet`` (DATA_CONTRACTS §8).

Dimensions are nominal reference sizes for the Blender kit, taken from published standards where one exists
(``dims_source`` says which); they are not per-instance measurements. Per-instance real values (DBH, capacity,
roof height, ramp width) live in the props table itself.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field

from .dedupe import CROSS_SOURCE_RULES


@dataclass(frozen=True)
class Kind:
    id: int
    name: str
    category: str
    description: str
    datasets: tuple[str, ...]
    dims_m: tuple[float, float, float]   # width (across the front), depth, height
    dims_source: str
    variant_meaning: str = ""
    text_meaning: str = ""
    heading_meaning: str = "compass heading of the object's front (0 = north, clockwise); NaN = not derivable"
    extra: dict = field(default_factory=dict)


KINDS: tuple[Kind, ...] = (
    Kind(0, "tree", "vegetation", "Tree from the 2015 Street Tree Census (alive only; species and DBH real, height estimated) or from "
         "the OSM extract's natural=tree nodes (dataset_id tells them apart; the OSM nodes are the only trees inside parks)",
         ("street_trees_2015", "osm_newyork_pbf"), (0.0, 0.0, 0.0),
         "per-instance: dbh_cm is the measured trunk diameter, 0 where the source records none — true of every OSM tree, since "
         "OSM publishes no trunk diameter in one unit convention. height_m is the OSM height tag where there is one "
         "(height_source=0), the allometry over a measured census DBH (height_source=1), or, where the source gives neither, a "
         "deterministic draw from the census height distribution seeded by the tree's own coordinates (height_source=4)",
         "health: 0 Good, 1 Fair, 2 Poor, 3 unknown (OSM records no condition, so every OSM tree is 3)",
         "spc_common (census) / the OSM name tag where a tree has one",
         extra={"attrs": "census: tree_id, curb_loc, sidewalk, nta — OSM: osm_id, genus, taxon, leaf_type, leaf_cycle, "
                         "denotation, circumference, diameter_crown, diameter (raw tag strings, never converted into dbh_cm)"}),
    Kind(1, "hydrant", "utility", "DEP fire hydrant", ("hydrants",), (0.30, 0.30, 0.75),
         "nominal: NYC DEP hydrant ~0.75 m above grade (typical; DEP does not publish a single standard)", "", "unitid"),
    Kind(2, "bus_shelter", "transit", "DOT/JCDecaux bus stop shelter", ("bus_stop_shelters",), (4.3, 1.6, 2.7),
         "nominal: Grimshaw-designed NYC standard shelter (~14 ft x 5 ft footprint), approximate", "", "On street / cross street"),
    Kind(3, "linknyc", "utility", "LinkNYC kiosk", ("linknyc",), (0.90, 0.30, 2.9),
         "published: Link1.0 kiosk 9 ft 6 in tall; Link5G is a 32 ft (9.75 m) pole", "0 Link1.0, 1 Link5G_Ad, 2 Link5G_NonAd", "site id"),
    Kind(4, "newsstand", "commerce", "Licensed sidewalk newsstand", ("newsstands",), (3.7, 1.8, 2.9),
         "legal maximum 72 sq ft footprint (NYC Admin Code 20-231); Cemusa standard unit ~12 ft x 6 ft (approximate height)", "", "street"),
    Kind(5, "bike_shelter", "transit", "DOT covered bicycle parking shelter", ("bike_shelters",), (4.3, 1.6, 2.7),
         "nominal: same family as the bus shelter (Cemusa), approximate", "", "location"),
    Kind(6, "bike_rack", "transit", "Bicycle parking (OSM amenity=bicycle_parking); capacity where tagged", ("osm",), (0.50, 0.10, 0.86),
         "published: DOT CityRack hoop 34 in tall", "0 unknown type, 1 stands/hoop, 2 wall_loops/rack, 3 shed/lockers", "OSM name"),
    Kind(7, "citibike_dock", "transit",
         "Citi Bike station (GBFS station_information) expanded into its parts: one row per dock unit and one kiosk row "
         "per station; capacity (docks) is carried on the kiosk row, so sum(capacity) over the kind is the dock-row count. "
         "Station identity is attrs.station_id, not prop_id contiguity",
         ("citibike_gbfs_stations", "citibike_gbfs_station_status"), (0.90, 1.8, 2.0),
         "per dock 0.90 m pitch (observed spacing, not a Lyft specification; the asset's tile_pitch_m), kiosk 2.0 m tall "
         "(asset nominal); station run length = capacity x 0.90 m along the nearest CSCL segment's bearing",
         "1 kiosk, 2 dock unit (0.90 m pitch along the kerb axis), 3 docked bicycle -- written only from a GBFS "
         "station_status snapshot (dataset_id citibike_gbfs_station_status, attrs.snapshot_last_updated) and absent "
         "otherwise; 0 is never written",
         "station name",
         extra={"attrs": "station_id, short_name, region_id, name, part (kiosk|dock|bike), dock_index, capacity, "
                         "axis_deg, axis_source (nearest_segment|none), axis_segment_id, axis_distance_m, rules; "
                         "(bike) snapshot_last_updated, num_bikes_available, num_ebikes_available",
                "heading": "axis - 90 so the dock's tileable +X lies along the kerb; NaN where no CSCL segment is "
                           "within 25 m (the run is then east-west, the direction consumers draw a NaN heading in)"}),
    Kind(8, "subway_entrance", "transit", "MTA subway entrance/exit (data.ny.gov 2024)", ("subway_entrances",), (1.5, 3.0, 2.4),
         "nominal stair opening; globe lamps 2.4 m", "0 stair, 1 escalator, 2 elevator, 3 easement/station house (no globe)",
         "Stop name — routes", extra={"attrs": "lines, entrance_type, has_globe (0 none, 1 green, 2 red), entry, exit"}),
    Kind(9, "curb_ramp", "pavement", "DOT pedestrian ramp (curb cut)", ("pedestrian_ramps",), (1.2, 1.5, 0.0),
         "per-instance ramp width in attrs (inches converted to m)", "0 no detectable warning surface, 1 DWS present", "streets"),
    Kind(10, "rtpi_sign", "transit", "Real-time passenger information sign at a bus stop", ("rtpi_signs",), (0.4, 0.1, 3.0),
         "nominal pole-mounted sign", "", "routes"),
    Kind(11, "bench", "seating", "Bench (OSM amenity=bench)", ("osm",), (1.8, 0.6, 0.85),
         "published: DOT CityBench 6 ft backed bench; OSM instances vary", "0 unknown, 1 with backrest, 2 without backrest", "OSM name"),
    Kind(12, "waste_basket", "utility", "Litter basket (OSM amenity=waste_basket)", ("osm",), (0.6, 0.6, 0.9),
         "nominal: DSNY wire mesh basket 24 in dia x 30 in (typical)", "", ""),
    Kind(13, "mailbox", "utility", "USPS collection box (OSM amenity=post_box)", ("osm",), (0.56, 0.60, 1.27),
         "nominal: USPS collection box (approximate)", "", ""),
    Kind(14, "street_lamp", "lighting", "Street light (OSM highway=street_lamp; rule-based fill flagged source=1)", ("osm", "rule:lamp_35m"),
         (0.3, 0.3, 9.1), "published: NYC DOT standard octagonal pole with cobra head, 30 ft mounting height", "0 unknown, 1 cobra, 2 historic/bishop's crook, 3 pedestrian-scale", "lamp_type"),
    Kind(15, "billboard", "advertising", "Billboard (OSM advertising=billboard)", ("osm",), (14.6, 0.5, 4.3),
         "nominal: 48 ft x 14 ft standard bulletin", "", "OSM name"),
    Kind(16, "artwork", "culture", "Public artwork (OSM tourism=artwork)", ("osm",), (1.5, 1.5, 3.0), "nominal", "", "OSM name / artwork_type"),
    Kind(17, "memorial", "culture", "Memorial (OSM historic=memorial)", ("osm",), (1.5, 1.5, 3.0), "nominal", "", "OSM name / memorial type"),
    Kind(18, "drinking_fountain", "utility", "Drinking fountain (OSM amenity=drinking_water)", ("osm",), (0.5, 0.5, 1.0), "nominal", "", ""),
    Kind(19, "payphone", "utility", "Public payphone (OSM amenity=telephone; LinkNYC 'Public Payphones')", ("osm", "linknyc"), (0.6, 0.4, 2.3), "nominal", "", ""),
    Kind(20, "vending_machine", "commerce", "Vending machine (OSM amenity=vending_machine)", ("osm",), (0.9, 0.7, 1.8), "nominal", "", "vending type"),
    Kind(21, "flagpole", "misc", "Flagpole (OSM man_made=flagpole)", ("osm",), (0.2, 0.2, 10.0), "nominal unless OSM height tag", "", ""),
    Kind(22, "utility_pole", "utility", "Utility pole (OSM man_made=utility_pole)", ("osm",), (0.3, 0.3, 11.0), "nominal unless OSM height tag", "", ""),
    Kind(23, "manhole", "utility", "Manhole cover (OSM man_made=manhole; rule-based fill flagged source=1)", ("osm", "rule:manhole_40m"),
         (0.61, 0.61, 0.0), "nominal: 24 in cover", "", "manhole type"),
    Kind(24, "bus_stop_sign", "transit", "MTA bus stop sign pole at every GTFS bus stop", ("gtfs_bus",), (0.45, 0.1, 3.0),
         "nominal pole-mounted MTA bus stop sign", "", "stop name", extra={"attrs": "stop_id, routes"}),
    Kind(25, "parks_comfort_station", "parks", "NYC Parks structure with public restroom", ("parks_structures",), (0.0, 0.0, 0.0),
         "per-instance: footprint dims and roof height from the dataset", "", "DESCRIPTION", extra={"attrs": "bin, footprint_w, footprint_d, area_m2"}),
    Kind(26, "parks_recreation_center", "parks", "NYC Parks recreation center building", ("parks_structures",), (0.0, 0.0, 0.0),
         "per-instance", "", "DESCRIPTION"),
    Kind(27, "parks_building", "parks", "Other NYC Parks structure (maintenance, pavilion, shed, ...)", ("parks_structures",), (0.0, 0.0, 0.0),
         "per-instance", "", "DESCRIPTION"),
    Kind(28, "cooling_tower", "rooftop", "Rooftop cooling tower (planimetric)", ("plan_cooling_towers",), (0.0, 0.0, 3.0),
         "per-instance footprint; nominal 3 m tall", "", ""),
    Kind(29, "swimming_pool", "landscape", "Swimming pool (planimetric)", ("plan_swimming_pools",), (0.0, 0.0, 0.0), "per-instance footprint", "", ""),
    Kind(30, "misc_structure", "misc", "Planimetric miscellaneous structure (feature code in attrs)", ("plan_misc_structures",), (0.0, 0.0, 0.0),
         "per-instance footprint", "", "sub feature code"),
    Kind(31, "subway_vent_grate", "transit", "Subway ventilation grate in the sidewalk (planimetric Railroad Structure, feat_code 2470)",
         ("plan_railroad_structure",), (0.0, 0.0, 0.05),
         "per-instance footprint from the polygon; grate sits ~0.05 m proud of the sidewalk (nominal)", "",
         "", extra={"attrs": "source_id, area_m2, footprint_w, footprint_d"}),
    Kind(32, "subway_emergency_exit", "transit", "Subway emergency exit hatch/grate (planimetric Railroad Structure, feat_code 2480)",
         ("plan_railroad_structure",), (0.0, 0.0, 0.05), "per-instance footprint from the polygon", "",
         "", extra={"attrs": "source_id, area_m2"}),
    Kind(33, "steam_vent", "utility", "Con Edison steam-system vent stack over a manhole (orange/white striped tube) — rule-based, no dataset exists",
         ("rule:steam_vent",), (0.9, 0.9, 3.5),
         "nominal: standard Con Edison vent tube ~3.5 m tall, 0.9 m diameter (approximate)", "", ""),
)
KIND_BY_NAME: dict[str, Kind] = {k.name: k for k in KINDS}
KIND_ID: dict[str, int] = {k.name: k.id for k in KINDS}

SOURCE_DATASET = 0
SOURCE_RULE = 1

HEIGHT_SOURCE = {"measured": 0, "allometry": 1, "nominal": 2, "none": 3, "census_distribution": 4}
# 4 was added for the OSM tree nodes, which give neither a height nor a trunk diameter: it is a deterministic
# draw from the census's own height distribution, seeded by the tree's coordinates (furniture/trees.py
# CensusHeights). It is kept apart from 1 because 1 means "estimated from this row's own measured trunk" and
# 4 means "no per-tree evidence at all; this is the population".
# 0/1/2 are the original values; 3/4 were added by the furniture build because the per-tile terrain rasters
# (DATA_CONTRACTS §3) do not exist yet and props are placed on measured survey points instead (elevation.py).
# 5 is the roof of the building the survey digitised the feature against: the planimetric cooling towers
# stand on roofs, and a ground elevation -- however well surveyed -- puts every one of them inside the
# building it sits on top of. furniture/rooftop.py joins their BIN against buildings_base.roof_z.
Z_SOURCE = {"terrain": 0, "dataset": 1, "none": 2, "spot_elev": 3, "spot_elev_far": 4, "building_roof": 5}


def catalog_json(counts: dict[str, int] | None = None) -> dict:
    counts = counts or {}
    return {
        "schema_version": 1,
        "columns": {
            "prop_id": "int64 deterministic id: kind * 1e10 + rank within kind (sorted by x, y)",
            "kind": "int16 -> kinds[].id",
            "x, y": "NYC_TM metres", "z": "float32 metres NAVD88 (NaN when z_source = 2)",
            "heading": "float32 compass degrees, NaN if unknown", "variant": "int16, see kinds[].variant_meaning",
            "text": "display text (see kinds[].text_meaning)", "source": "int8 0 dataset, 1 rule (inferred placement)",
            "dataset_id": "manifest source id or rule name", "species": "latin name (trees)", "dbh_cm": "float32 trunk diameter (trees)",
            "height_m": "float32 object height",
            "height_source": "int8 0 measured/tagged, 1 allometry over this row's own measured DBH, 2 nominal "
                             "catalog value, 3 none, 4 deterministic draw from the census height distribution "
                             "(no per-tree evidence; seeded by the row's own x/y so a re-run is bit-identical)",
            "capacity": "int16 docks / bike stands (0 = n/a)",
            "z_source": "int8 0 terrain sample, 1 dataset elevation, 2 none, 3 planimetric spot elevation + LiDAR "
                        "building grade (IDW of 4 nearest, nearest <= 80 m), 4 same but nearest > 80 m (extrapolated), "
                        "5 measured roof of the building the survey names in attrs.bin (buildings_base.roof_z)",
            "attrs": "JSON string of per-instance attributes (dataset native ids, footprint dims, routes, ...)",
            "tile": "string t_{tx}_{ty} of the tile file this row lives in", "tx, ty": "int32 tile grid index",
        },
        "extensions_to_data_contracts_s8": ["height_source", "capacity", "z_source", "attrs", "tile", "tx", "ty"],
        "dedupe": {"radius_m": 1.5, "note": "cross-dataset duplicates removed inside a dedupe group; see build.py DEDUPE_GROUPS",
                   "cross_source": [{"group": r.group, "kept_dataset": r.keep_dataset, "dropped_dataset": r.drop_dataset,
                                     "radius_m": r.radius_m, "basis": r.basis} for r in CROSS_SOURCE_RULES]},
        "kinds": [dict(asdict(k), count=counts.get(k.name, 0)) for k in KINDS],
    }
