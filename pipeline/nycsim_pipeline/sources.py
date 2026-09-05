"""Registry of every external data source (docs/DATA_SOURCES.md is generated from this file).

Each entry: id -> Source(url, fmt, license, attribution, description, kind). ``kind`` drives the downloader:
  'file'      plain HTTP GET
  'socrata_geojson' Socrata geospatial export (GeoJSON, WGS84)
  'socrata_csv'     Socrata full CSV export
  'soda'            Socrata SODA query (url carries $where/$select), paged automatically
"""
from __future__ import annotations

from dataclasses import dataclass, field

SOCRATA_NYC = "https://data.cityofnewyork.us"
SOCRATA_NYS = "https://data.ny.gov"
NYC_OPEN_DATA_LICENSE = "NYC Open Data Terms of Use (public domain-equivalent; attribution requested)"
NYC_ATTR = "City of New York, NYC Open Data"


@dataclass(frozen=True)
class Source:
    id: str
    url: str
    fmt: str
    license: str
    attribution: str
    description: str
    kind: str = "file"
    filename: str = ""
    tags: tuple[str, ...] = field(default_factory=tuple)

    @property
    def local_name(self) -> str:
        if self.filename:
            return self.filename
        ext = {"geojson": "geojson", "csv": "csv", "zip": "zip", "pbf": "osm.pbf", "json": "json", "tif": "tif", "gdb.zip": "zip", "img.zip": "zip"}[self.fmt]
        return f"{self.id}.{ext}"


def _geo(id_: str, ds: str, desc: str, *tags: str, domain: str = SOCRATA_NYC, attribution: str = NYC_ATTR) -> Source:
    return Source(id_, f"{domain}/api/geospatial/{ds}?method=export&format=GeoJSON", "geojson", NYC_OPEN_DATA_LICENSE, attribution, desc, "socrata_geojson", tags=tags + (ds,))


def _csv(id_: str, ds: str, desc: str, *tags: str, domain: str = SOCRATA_NYC, attribution: str = NYC_ATTR) -> Source:
    return Source(id_, f"{domain}/api/views/{ds}/rows.csv?accessType=DOWNLOAD", "csv", NYC_OPEN_DATA_LICENSE, attribution, desc, "socrata_csv", tags=tags + (ds,))


def _soda(id_: str, ds: str, query: str, desc: str, *tags: str, domain: str = SOCRATA_NYC) -> Source:
    return Source(id_, f"{domain}/resource/{ds}.csv?{query}", "csv", NYC_OPEN_DATA_LICENSE, NYC_ATTR, desc, "soda", tags=tags + (ds,))


SOURCES: dict[str, Source] = {s.id: s for s in [
    # ---- Buildings ----
    _geo("building_footprints", "5zhs-2jue", "NYC Building Footprints (OTI): 1,083,026 polygons, BIN, BBL, LiDAR roof height (ft), ground elevation (ft), construction year", "buildings"),
    _csv("pluto", "64uk-42ks", "MapPLUTO tax lot attributes: numfloors, yearbuilt, bldgclass, landuse, lot/bldg area, landmark, histdist, address", "buildings"),
    Source("doitt_3d_citygml", "https://s-media.nyc.gov/agencies/oti/DA_WISE_GML.zip", "zip", NYC_OPEN_DATA_LICENSE, "NYC OTI 3-D Building Model (2014 LiDAR), CityGML LOD2, EPSG:2263", "NYC 3-D Building Model, CityGML LOD2 roofs/walls for every building existing in 2014, keyed by BIN", filename="DA_WISE_GML.zip", tags=("buildings", "tnru-abg2")),
    _csv("building_elevation_subgrade", "bsin-59hv", "Building Elevation and Subgrade: first-floor elevation, stoop, subgrade presence", "buildings"),
    _geo("lpc_individual_landmarks", "buis-pvji", "LPC Individual Landmark Sites (polygons)", "landmarks"),
    _csv("lpc_building_db", "gpmc-yuvp", "LPC Individual Landmark and Historic District Building Database (BIN, BBL, style, material, architect, date)", "landmarks"),
    _geo("lpc_historic_districts", "skyk-mpzq", "LPC Historic Districts polygons", "landmarks"),
    _soda("dob_sidewalk_sheds", "rbx6-tga4", "$select=job_filing_number,work_type,permit_status,issued_date,expired_date,bin,house_no,street_name,borough,block,lot&$where=work_type%3D%27Sidewalk%20Shed%27&$limit=500000", "DOB NOW approved permits for sidewalk sheds (scaffolding)", "buildings"),
    _csv("dcwp_licenses", "w7w3-xahh", "DCWP Issued Licenses: business names with addresses and coordinates", "signage"),
    _csv("dohmh_restaurants", "43nn-pn8j", "DOHMH restaurant inspections: restaurant names, addresses, BIN/BBL, coordinates", "signage"),
    # ---- Roads ----
    _geo("centerline", "inkn-q76z", "NYC Street Centerline (CSCL): 122,269 segments with lanes, width, traffic direction, posted speed, level codes", "roads"),
    Source("lion", f"{SOCRATA_NYC}/download/2v4z-66xt/application%2Fzip", "gdb.zip", NYC_OPEN_DATA_LICENSE, "NYC Department of City Planning", "LION single-line street base map (file geodatabase) with nodes, node levels, segment types", filename="nyclion.zip", tags=("roads", "2v4z-66xt")),
    _csv("dot_signs", "nfid-uabd", "DOT Parking Regulation Locations and Signs: 440,540 current signs with MUTCD code, text, arrow, facing, State Plane x/y", "roads", "signs"),
    _csv("vzv_speed_limits", "5mad-ntua", "Vision Zero View posted speed limits by street segment", "roads"),
    _csv("vzv_lpi_signals", "xc4v-ntf4", "Leading Pedestrian Interval signalized intersections", "roads", "signals"),
    _csv("barnes_dance", "8kuj-2n3u", "Exclusive pedestrian phase (Barnes Dance) intersections", "roads", "signals"),
    _csv("signal_retiming", "d8dp-wfee", "25 MPH signal retiming corridors (signalized intersections)", "roads", "signals"),
    _geo("bike_routes", "mzxg-pwib", "NYC bike routes (protected/standard/sharrow/greenway)", "roads"),
    Source("bus_lanes", f"{SOCRATA_NYC}/resource/ycrg-ses3.geojson?$limit=50000", "geojson", NYC_OPEN_DATA_LICENSE, NYC_ATTR, "Bus lanes on local streets (SODA GeoJSON; the geospatial export endpoint returns an empty collection for this dataset)", "file", tags=("roads", "ycrg-ses3")),
    _geo("truck_routes", "jjja-shxy", "Truck routes (local/through)", "roads"),
    _geo("ped_plazas", "k5k6-6jex", "DOT pedestrian plazas polygons", "roads"),
    _csv("traffic_volume_auto", "7ym2-wayt", "Automated Traffic Volume Counts (ATR) 15-min counts by segment", "traffic"),
    _geo("taxi_zones", "8meu-9t5y", "TLC taxi zones polygons", "traffic"),
    _csv("street_construction_permits", "tqtj-sjs8", "Street construction permits 2022-present (steel plates, cuts)", "roads"),
    # ---- Planimetrics (OTI, 2022 aerial) ----
    _geo("plan_roadbed", "i36f-5ih7", "Planimetric roadbed polygons", "planimetric"),
    _geo("plan_sidewalk", "52n9-sdep", "Planimetric sidewalk polygons", "planimetric"),
    _geo("plan_curb", "5xvt-8cbk", "Planimetric curb lines", "planimetric"),
    _geo("plan_median", "ees7-4ufv", "Planimetric median polygons", "planimetric"),
    _geo("plan_pavement_edge", "vs44-rznx", "Planimetric pavement edge lines", "planimetric"),
    _geo("plan_shoreline", "59xk-wagz", "Planimetric shoreline lines", "planimetric", "water"),
    _geo("plan_hydrography", "pjs3-c3z5", "Planimetric hydrography polygons", "planimetric", "water"),
    _geo("plan_hydro_structures", "6hbv-tek4", "Planimetric hydrography structures (piers, docks, seawalls)", "planimetric", "water"),
    _geo("plan_public_plazas", "ue2e-9jm2", "Planimetric public plazas", "planimetric"),
    _geo("plan_elevation_points", "9uxf-ng6q", "Planimetric spot elevations (survey grade, ft)", "planimetric", "terrain"),
    _geo("plan_transport_structures", "r9cu-9r7b", "Planimetric transportation structures (bridges, elevated roads, tunnels portals)", "planimetric", "roads"),
    _geo("plan_railroad_structure", "dwer-xbgx", "Planimetric railroad structures (elevated, embankment, station)", "planimetric", "transit"),
    _geo("plan_railroad_line", "anc7-97cy", "Planimetric railroad track lines", "planimetric", "transit"),
    _geo("plan_open_space_parks", "y6ja-fw4f", "Planimetric open space (parks) polygons", "planimetric", "parks"),
    _geo("plan_open_space_other", "b7j8-z8a7", "Planimetric open space (other) polygons", "planimetric", "parks"),
    _geo("plan_parking_lot", "7cgt-uhhz", "Planimetric parking lots", "planimetric"),
    _geo("plan_boardwalk", "p9cw-7gsv", "Planimetric boardwalks", "planimetric"),
    _geo("plan_retaining_wall", "s2pi-ccum", "Planimetric retaining walls", "planimetric"),
    _geo("plan_misc_structures", "92m5-3pwp", "Planimetric miscellaneous structures", "planimetric"),
    _geo("plan_cooling_towers", "x748-37q7", "Planimetric cooling towers (rooftop)", "planimetric", "buildings"),
    _geo("plan_swimming_pools", "6uj9-35vn", "Planimetric swimming pools", "planimetric"),
    # ---- Street furniture / vegetation ----
    _csv("street_trees_2015", "uvpi-gqnh", "2015 Street Tree Census: 683,788 trees with species, DBH, coordinates", "furniture", "trees"),
    _geo("hydrants", "5bgh-vtsn", "DEP citywide fire hydrants", "furniture"),
    _csv("bus_stop_shelters", "t4f2-8md7", "Bus stop shelters", "furniture", "transit"),
    _csv("linknyc", "s4kf-3yrf", "LinkNYC kiosk locations", "furniture"),
    _csv("newsstands", "w9zq-xm8b", "Newsstands", "furniture"),
    _csv("bike_shelters", "dimy-qyej", "Bicycle parking shelters", "furniture"),
    _csv("pedestrian_ramps", "ufzp-rrqu", "Pedestrian ramp (curb cut) locations", "furniture"),
    _csv("rtpi_signs", "g9jx-npbk", "Real-time passenger information sign locations (bus)", "furniture", "transit"),
    _csv("subway_entrances", "i9wp-a4ja", "MTA subway entrances and exits (2024) with routes and entrance type", "transit", domain=SOCRATA_NYS, attribution="Metropolitan Transportation Authority, data.ny.gov"),
    _geo("parks_properties", "enfh-gkve", "NYC Parks properties with names and types", "parks"),
    _csv("parks_structures", "n8q6-i44s", "NYC Parks structures (comfort stations, playgrounds equipment, monuments)", "parks"),
    # ---- Boundaries ----
    _geo("borough_boundaries_water", "wh2p-dxnf", "Borough boundaries incl. water", "boundaries"),
    _geo("borough_boundaries", "gthc-hcne", "Borough boundaries (land)", "boundaries"),
    _geo("nta_2020", "9nt8-h7nd", "2020 Neighborhood Tabulation Areas", "boundaries"),
    _geo("community_districts", "5crt-au7u", "Community districts", "boundaries"),
    # ---- Terrain ----
    Source("usgs_3dep_19_index", "https://tnmaccess.nationalmap.gov/api/v1/products?bbox=-74.30,40.45,-73.65,40.95&datasets=National%20Elevation%20Dataset%20(NED)%201/9%20arc-second&max=200&outputFormat=JSON", "json", "USGS public domain", "U.S. Geological Survey, 3D Elevation Program", "Product index of 1/9 arc-second (~3.4 m) LiDAR-derived DEM tiles covering the scope", tags=("terrain",)),
    Source("usgs_3dep_13_n41w074", "https://prd-tnm.s3.amazonaws.com/StagedProducts/Elevation/13/TIFF/historical/n41w074/USGS_13_n41w074_20260820.tif", "tif", "USGS public domain", "U.S. Geological Survey, 3D Elevation Program", "1/3 arc-second DEM n41w074 (fallback base under 1/9\" gaps, NJ shoreline)", tags=("terrain",)),
    Source("usgs_3dep_13_n41w075", "https://prd-tnm.s3.amazonaws.com/StagedProducts/Elevation/13/TIFF/historical/n41w075/USGS_13_n41w075_20201208.tif", "tif", "USGS public domain", "U.S. Geological Survey, 3D Elevation Program", "1/3 arc-second DEM n41w075 (west of -74°: Staten Island west shore, NJ)", tags=("terrain",)),
    # ---- OSM ----
    Source("osm_newyork_pbf", "https://download.bbbike.org/osm/bbbike/NewYork/NewYork.osm.pbf", "pbf", "ODbL 1.0", "© OpenStreetMap contributors", "OpenStreetMap extract, New York City + NJ Hudson waterfront (BBBike)", filename="NewYork.osm.pbf", tags=("osm",)),
    # ---- Transit ----
    Source("gtfs_bus_manhattan", "http://web.mta.info/developers/data/nyct/bus/google_transit_manhattan.zip", "zip", "MTA Developer Data Terms", "Metropolitan Transportation Authority", "NYCT bus GTFS Manhattan", tags=("transit",)),
    Source("gtfs_bus_brooklyn", "http://web.mta.info/developers/data/nyct/bus/google_transit_brooklyn.zip", "zip", "MTA Developer Data Terms", "Metropolitan Transportation Authority", "NYCT bus GTFS Brooklyn", tags=("transit",)),
    Source("gtfs_bus_bronx", "http://web.mta.info/developers/data/nyct/bus/google_transit_bronx.zip", "zip", "MTA Developer Data Terms", "Metropolitan Transportation Authority", "NYCT bus GTFS Bronx", tags=("transit",)),
    Source("gtfs_bus_queens", "http://web.mta.info/developers/data/nyct/bus/google_transit_queens.zip", "zip", "MTA Developer Data Terms", "Metropolitan Transportation Authority", "NYCT bus GTFS Queens", tags=("transit",)),
    Source("gtfs_bus_staten_island", "http://web.mta.info/developers/data/nyct/bus/google_transit_staten_island.zip", "zip", "MTA Developer Data Terms", "Metropolitan Transportation Authority", "NYCT bus GTFS Staten Island", tags=("transit",)),
    Source("gtfs_bus_company", "http://web.mta.info/developers/data/busco/google_transit.zip", "zip", "MTA Developer Data Terms", "Metropolitan Transportation Authority", "MTA Bus Company GTFS (express and former private lines)", tags=("transit",)),
    Source("gtfs_subway", "http://web.mta.info/developers/data/nyct/subway/google_transit.zip", "zip", "MTA Developer Data Terms", "Metropolitan Transportation Authority", "NYCT subway GTFS (routes, stops, schedules)", tags=("transit",)),
    Source("gtfs_lirr", "http://web.mta.info/developers/data/lirr/google_transit.zip", "zip", "MTA Developer Data Terms", "Metropolitan Transportation Authority", "LIRR GTFS", tags=("transit",)),
    Source("gtfs_mnr", "http://web.mta.info/developers/data/mnr/google_transit.zip", "zip", "MTA Developer Data Terms", "Metropolitan Transportation Authority", "Metro-North GTFS (Park Avenue viaduct trains)", tags=("transit",)),
    Source("citibike_gbfs_stations", "https://gbfs.citibikenyc.com/gbfs/2.3/en/station_information.json", "json", "Citi Bike Data License Agreement", "Lyft Bikes and Scooters, LLC", "Citi Bike station information (GBFS)", tags=("furniture", "transit")),
]}


def by_tag(tag: str) -> list[Source]:
    return [s for s in SOURCES.values() if tag in s.tags]
