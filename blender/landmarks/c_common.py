"""Shared helpers for the *C* landmark scripts (Hudson Yards, Billionaires' Row, Times Square, museums, cultural,
stadiums, outer-borough icons).

Written because ``blender/landmarks/common.py`` (agent A) was absent 20 minutes after this lane started; the API is
the one the orchestrator specified for that module (``load_footprint``, ``local_frame``, ``finish``, ``render_check``)
so the scripts can be re-pointed at the shared module by changing one import.

Conventions (docs/DATA_CONTRACTS.md §13, docs/ARCHITECTURE.md §2):
* Model space is metres, Blender Z-up, **X = east, Y = north**, unrotated (buildings on the Manhattan grid therefore
  appear rotated by the real grid angle, ~29°).  ``origin_tm`` in every glb's extras is the NYC_TM / NAVD88 point of
  the model origin, so ``world = origin_tm + local``.  Local z = 0 is the footprint's LiDAR ``ground_z``.
* Every landmark is exported twice: ``blender_out/landmarks/<id>.glb`` (LOD0) and ``<id>_lod1.glb`` (LOD1), plus one
  catalog JSON ``blender_out/landmarks/catalog/<id>.json`` carrying the DATA_CONTRACTS §11 fields
  (id, name, bins, lp_number, script, footprint_source, height_m, height_source, notes, fidelity_statement) and the
  LOD records.  ``blender/common/merge_catalog.py`` merges them into ``landmarks.json``.
* Footprints come from ``data/processed/landmarks/candidate_footprints.parquet`` (BIN-keyed) and, for BINs not in
  that file, from ``data/processed/buildings/footprints_raw.parquet`` read with pyarrow column/row filters only
  (never loaded whole into geopandas).
* Materials: Principled BSDF with documented base colours (``PALETTE``); when ``blender/common/textures.py`` can
  resolve a material name (its catalog present + asset downloadable) the PBR maps are attached at 1K so the glbs
  stay small.  Times Square screens are emissive slots named ``TSQ_SCREEN_<n>`` with UV 0..1 per screen.
"""
from __future__ import annotations

import fcntl
import json
import logging
import math
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Sequence

REPO = Path(os.environ.get("NYCSIM_REPO_ROOT", Path(__file__).resolve().parents[2]))
for _p in (REPO / "blender" / "common", REPO / "pipeline", REPO / "blender" / "landmarks"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import bpy  # noqa: E402
import bmesh  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402

import nycsim_bpy as nb  # noqa: E402
from nycsim_pipeline.crs import lonlat_to_tm, tm_to_lonlat  # noqa: E402,F401

log = logging.getLogger("landmarks.c")
if not log.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

OUT = Path(os.environ.get("NYCSIM_BLENDER_OUT", REPO / "blender_out")) / "landmarks"
CATALOG = OUT / "catalog"
VERIFY = REPO / "docs" / "verification" / "landmarks"
FOOTPRINTS = REPO / "data/processed/landmarks/candidate_footprints.parquet"
FOOTPRINTS_RAW = REPO / "data/processed/buildings/footprints_raw.parquet"
FIDELITY_LANDMARK_MODEL = 1 << 7  # DATA_CONTRACTS §5.1 bit 7
BUDGET_TRIS = 250_000
BUDGET_TRIS_LARGE = 400_000  # Vessel, Guggenheim, High Line (brief)
MANHATTAN_GRID_HEADING = 29.0  # compass heading of the avenues (N 29° E), streets = 119°
AGENT = "C"

# --------------------------------------------------------------------------------------------------------- registry
# Canonical id -> published height (m) + BINs.  Tests read this table (tests/test_landmarks_c.py) and check the
# exported glb bounding-box height against ``height_m`` ±1 %.  ``bins`` are the OTI Building Footprints BINs the
# model replaces; ``height_source`` documents where the height comes from.  Sub-ids of multi-building scripts carry
# ``script`` explicitly.
C_LANDMARKS: dict[str, dict] = {
    # ---- Hudson Yards (script c_hudson_yards.py)
    "c_hy_30_hudson_yards": dict(name="30 Hudson Yards", bins=[1088961], height_m=387.1, script="c_hudson_yards",
                                 height_source="KPF / CTBUH: 1,270 ft (387.1 m) architectural; Edge deck at 1,131 ft (345 m)", budget=BUDGET_TRIS),
    "c_hy_10_hudson_yards": dict(name="10 Hudson Yards", bins=[1088961], height_m=272.8, script="c_hudson_yards",
                                 height_source="KPF / CTBUH: 895 ft (272.8 m); OSM height=272.8", budget=BUDGET_TRIS),
    "c_hy_35_hudson_yards": dict(name="35 Hudson Yards", bins=[1091590], height_m=308.0, script="c_hudson_yards",
                                 height_source="SOM / CTBUH: 1,009 ft (308 m), 72 floors", budget=BUDGET_TRIS),
    "c_hy_55_hudson_yards": dict(name="55 Hudson Yards", bins=[1089412], height_m=237.4, script="c_hudson_yards",
                                 height_source="KPF+Kohn / CTBUH: 780 ft (237.4 m), 51 floors; footprint LiDAR height stale (24 m, 2015 flight)", budget=BUDGET_TRIS),
    "c_hy_15_hudson_yards": dict(name="15 Hudson Yards", bins=[1089411], height_m=278.6, script="c_hudson_yards",
                                 height_source="Diller Scofidio + Renfro / CTBUH: 914 ft (278.6 m), 88 floors", budget=BUDGET_TRIS),
    "c_hy_50_hudson_yards": dict(name="50 Hudson Yards", bins=[1090274], height_m=308.2, script="c_hudson_yards",
                                 height_source="Foster + Partners / CTBUH: 1,011 ft (308.2 m), 58 floors; LiDAR 308.2 m", budget=BUDGET_TRIS),
    "c_hy_the_shed": dict(name="The Shed (Bloomberg Building)", bins=[1089411], height_m=40.0, script="c_hudson_yards",
                          height_source="DS+R: 8-storey base ~120 ft; movable shell 115 ft (35 m) tall; OSM height=40", budget=BUDGET_TRIS),
    "c_hy_vessel": dict(name="Vessel", bins=[1090391], height_m=46.0, script="c_hudson_yards",
                        height_source="Heatherwick Studio: 150 ft (46 m) tall, 50 ft base widening to 150 ft; 154 flights, 2,500 steps, 80 landings", budget=BUDGET_TRIS_LARGE),
    # ---- Billionaires' Row (script c_billionaires_row.py)
    "c_br_432_park_avenue": dict(name="432 Park Avenue", bins=[1088817, 1035787], height_m=425.5, script="c_billionaires_row",
                                 height_source="Rafael Viñoly / CTBUH: 1,396 ft (425.5 m), 85 floors; footprint LiDAR 425.5 m", budget=BUDGET_TRIS),
    "c_br_111_west_57th": dict(name="111 West 57th Street (Steinway Tower) + Steinway Hall", bins=[1023728], height_m=435.3, script="c_billionaires_row",
                               height_source="SHoP / CTBUH: 1,428 ft (435.3 m), 84 floors; footprint LiDAR 435.3 m", budget=BUDGET_TRIS),
    "c_br_central_park_tower": dict(name="Central Park Tower", bins=[1090180], height_m=472.4, script="c_billionaires_row",
                                    height_source="AS+GG / CTBUH: 1,550 ft (472.4 m), 98 floors; cantilever begins at floor 30 (~90 m)", budget=BUDGET_TRIS),
    "c_br_one57": dict(name="One57", bins=[1088565], height_m=306.1, script="c_billionaires_row",
                       height_source="Christian de Portzamparc / CTBUH: 1,004 ft (306 m), 75 floors", budget=BUDGET_TRIS),
    "c_br_220_central_park_south": dict(name="220 Central Park South", bins=[1090184], height_m=290.2, script="c_billionaires_row",
                                        height_source="Robert A.M. Stern / CTBUH: 952 ft (290 m), 70 floors; LiDAR 290.2 m", budget=BUDGET_TRIS),
    "c_br_53w53": dict(name="53 West 53rd (MoMA Expansion Tower)", bins=[1090777], height_m=320.0, script="c_billionaires_row",
                       height_source="Jean Nouvel / CTBUH: 1,050 ft (320 m), 77 floors; LiDAR 320.0 m", budget=BUDGET_TRIS),
    "c_br_trump_tower": dict(name="Trump Tower", bins=[1035794], height_m=202.0, script="c_billionaires_row",
                             height_source="Der Scutt / CTBUH: 664 ft (202 m), 58 floors; LiDAR 202.7 m", budget=BUDGET_TRIS),
    "c_br_solow_building": dict(name="Solow Building (9 West 57th Street)", bins=[1035071], height_m=210.0, script="c_billionaires_row",
                                height_source="SOM (Gordon Bunshaft) / CTBUH: 689 ft (210 m), 50 floors; LiDAR 204.8 m (roof deck)", budget=BUDGET_TRIS),
    # ---- Times Square (script c_times_square.py)
    "c_ts_one_times_square": dict(name="One Times Square", bins=[1022581], height_m=141.0, script="c_times_square",
                                  height_source="Roof 363 ft (111 m) + ball pole to ~463 ft (141 m) incl. flagpole/ball; OSM 'Times Square Ball' height 133.6 m (ball position)", budget=BUDGET_TRIS),
    "c_ts_two_times_square": dict(name="Two Times Square (Renaissance New York Times Square Hotel)", bins=[1024742], height_m=160.6, script="c_times_square",
                                  height_source="Footprint LiDAR 160.6 m (527 ft); Emporis lists 26-floor hotel + sign tower; no published architectural height", budget=BUDGET_TRIS),
    "c_ts_three_times_square": dict(name="3 Times Square (Reuters Building)", bins=[1024686], height_m=169.2, script="c_times_square",
                                    height_source="Fox & Fowle: 30 floors; OSM height=169.2 m; LiDAR main roof 148.9 m (corner tower + mast above)", budget=BUDGET_TRIS),
    "c_ts_four_times_square": dict(name="4 Times Square (Condé Nast Building)", bins=[1085682], height_m=247.0, script="c_times_square",
                                   height_source="Fox & Fowle / CTBUH: 809 ft (247 m) to roof, 48 floors (antenna 1,118 ft not modelled as structure); LiDAR 224.6 m top slab", budget=BUDGET_TRIS),
    "c_ts_tsx_broadway": dict(name="TSX Broadway (1568 Broadway) incl. Palace Theatre", bins=[1085493], height_m=158.0, script="c_times_square",
                              height_source="PBDW / L&L: 46 floors, 518 ft (158 m), completed 2023; footprint LiDAR 146 m is the demolished DoubleTree", budget=BUDGET_TRIS),
    "c_ts_paramount_building": dict(name="Paramount Building (1501 Broadway)", bins=[1024706], height_m=128.3, script="c_times_square",
                                    height_source="Rapp & Rapp 1927: 33 floors, 420 ft (128 m) to top of globe; LiDAR 128.3 m", budget=BUDGET_TRIS),
    "c_ts_tkts_duffy_square": dict(name="TKTS booth, red steps and Duffy Square plaza", bins=[1085637, 1090950], height_m=8.2, script="c_times_square",
                                   height_source="Perkins Eastman/Choi Ropiha 2008: 27 red glass steps rising 16 ft (4.9 m) above plaza; flagpole/Duffy statue plinth to 8.2 m", budget=BUDGET_TRIS),
    "c_ts_times_square_tower": dict(name="Times Square Tower (7 Times Square)", bins=[1086069], height_m=221.0, script="c_times_square",
                                    height_source="SOM / CTBUH: 726 ft (221 m), 47 floors; LiDAR 209.6 m (main roof below crown screen)", budget=BUDGET_TRIS),
    "c_ts_bank_of_america_tower": dict(name="Bank of America Tower (One Bryant Park)", bins=[1087268], height_m=365.8, script="c_times_square",
                                       height_source="Cook+Fox / CTBUH: 1,200 ft (365.8 m) to spire tip, roof 945 ft (288 m), 55 floors; LiDAR 270.6 m", budget=BUDGET_TRIS),
    "c_ts_marriott_marquis": dict(name="New York Marriott Marquis", bins=[1024727], height_m=176.0, script="c_times_square",
                                  height_source="John Portman 1985: 49 floors, 574 ft (175 m); LiDAR 176.0 m", budget=BUDGET_TRIS),
    "c_ts_new_york_times_building": dict(name="The New York Times Building", bins=[1087186], height_m=318.8, script="c_times_square",
                                         height_source="Renzo Piano / CTBUH: 1,046 ft (318.8 m) to mast, roof 748 ft (228 m), 52 floors; LiDAR 230.1 m", budget=BUDGET_TRIS),
    "c_ts_port_authority_bus_terminal": dict(name="Port Authority Bus Terminal", bins=[1083268], height_m=38.6, script="c_times_square",
                                             height_source="1950/1979 structure; OSM height 38.6 m; LiDAR 31.4 m (main roof), truss frame above", budget=BUDGET_TRIS),
    # ---- single-building scripts
    "c_hearst_tower": dict(name="Hearst Tower", bins=[1025451], height_m=182.0, height_source="Foster + Partners / CTBUH: 597 ft (182 m), 46 floors on 1928 Urban base (6 floors, 40 m)", budget=BUDGET_TRIS),
    "c_citigroup_center": dict(name="Citigroup Center (601 Lexington)", bins=[1036474], height_m=278.9, height_source="Hugh Stubbins / CTBUH: 915 ft (278.9 m), 59 floors; 45° roof; 114 ft (35 m) stilts; LiDAR 277.7 m", budget=BUDGET_TRIS),
    "c_metlife_building": dict(name="MetLife Building (200 Park Avenue)", bins=[1085630], height_m=246.3, height_source="Emery Roth / CTBUH: 808 ft (246.3 m), 59 floors; footprint LiDAR 47.9 m is the 10-storey base only", budget=BUDGET_TRIS),
    "c_lipstick_building": dict(name="Lipstick Building (885 Third Avenue)", bins=[1038549], height_m=138.0, height_source="Johnson/Burgee / CTBUH: 453 ft (138 m), 34 floors; LiDAR 141.6 m incl. mechanical", budget=BUDGET_TRIS),
    "c_seagram_building": dict(name="Seagram Building", bins=[1036465], height_m=157.0, height_source="Mies van der Rohe / CTBUH: 515 ft (157 m), 38 floors; LiDAR 161.8 m incl. bulkhead", budget=BUDGET_TRIS),
    "c_lever_house": dict(name="Lever House", bins=[1035732], height_m=94.0, height_source="SOM (Bunshaft) / CTBUH: 307 ft (94 m), 24 floors incl. mechanical; LiDAR 82.1 m main roof", budget=BUDGET_TRIS),
    "c_un_headquarters": dict(name="United Nations Headquarters (Secretariat, General Assembly, Conference Building, Library)", bins=[1083875, 1083872, 1083874],
                              height_m=154.0, height_source="Harrison/Le Corbusier/Niemeyer: Secretariat 505 ft (154 m), 39 floors; LiDAR 156.3 m", budget=BUDGET_TRIS),
    "c_the_dakota": dict(name="The Dakota", bins=[1028637], height_m=50.9, lp_number="LP-0280", height_source="Henry Hardenbergh 1884: 9 storeys + gables; footprint LiDAR 50.9 m to gable ridge", budget=BUDGET_TRIS),
    "c_the_plaza": dict(name="The Plaza Hotel", bins=[1035253], height_m=76.2, lp_number="LP-0629", height_source="Hardenbergh 1907: 19 floors, 250 ft (76.2 m) to roof ridge; LiDAR 85.0 m incl. rooftop bulkheads", budget=BUDGET_TRIS),
    "c_metropolitan_museum": dict(name="The Metropolitan Museum of Art", bins=[1083810], height_m=42.0, lp_number="LP-0955", height_source="Hunt/McKim 1902-26 Fifth Ave facade: attic cornice ~110 ft; central pavilion to 138 ft (42 m); LiDAR 26.8 m (average roof)", budget=BUDGET_TRIS),
    "c_guggenheim": dict(name="Solomon R. Guggenheim Museum", bins=[1046946, 1046964], height_m=41.6, lp_number="LP-1774", height_source="Frank Lloyd Wright 1959: rotunda 92 ft (28 m) + skylight; 1992 annex tower 10 storeys; LiDAR 41.6 m (annex)", budget=BUDGET_TRIS_LARGE),
    "c_american_museum_natural_history": dict(name="American Museum of Natural History (Central Park West facade + Rose Center)", bins=[1083846, 1090575], height_m=44.8,
                                              lp_number="LP-0946", height_source="Trowbridge & Livingston 1936 Roosevelt Memorial: 4 columns 60 ft; Rose Center cube 95 ft (29 m), sphere 87 ft (26.5 m); LiDAR 44.8 m", budget=BUDGET_TRIS),
    "c_lincoln_center": dict(name="Lincoln Center (Metropolitan Opera, Geffen Hall, Koch Theater, plaza)", bins=[1081022, 1081023, 1028831], height_m=37.7,
                             height_source="Wallace Harrison 1966 Met Opera: 5 travertine arches 96 ft (29 m); roof LiDAR 37.7 m", budget=BUDGET_TRIS),
    "c_apollo_theater": dict(name="Apollo Theater", bins=[1058654], height_m=20.0, lp_number="LP-1268", height_source="George Keister 1914: neoclassical facade ~65 ft (20 m); LiDAR 20.0 m; marquee 1940s", budget=BUDGET_TRIS),
    "c_carnegie_hall": dict(name="Carnegie Hall", bins=[1023449], height_m=55.2, lp_number="LP-0278", height_source="William Tuthill 1891: 6 storeys + studio tower; LiDAR 55.2 m", budget=BUDGET_TRIS),
    "c_st_john_the_divine": dict(name="Cathedral of St. John the Divine", bins=[1082706], height_m=71.0, lp_number="LP-2585", height_source="Heins & LaFarge / Cram: nave ridge 177 ft; crossing/central tower base 232 ft (71 m) unfinished; LiDAR 51.4 m (nave roof)", budget=BUDGET_TRIS),
    "c_riverside_church": dict(name="Riverside Church", bins=[1081792, 1081791], height_m=120.1, lp_number="LP-2037", height_source="Allen & Collens 1930: tower 392 ft (119.5 m), 22 storeys; OSM 120.1 m; LiDAR 118.0 m", budget=BUDGET_TRIS),
    "c_yankee_stadium": dict(name="Yankee Stadium (2009)", bins=[2114490], height_m=42.0, height_source="Populous 2009: frieze at top of upper deck ~138 ft (42 m); field 318/408/314 ft; LiDAR 36.6 m (average roof)", budget=BUDGET_TRIS),
    "c_citi_field": dict(name="Citi Field", bins=[4536844], height_m=39.0, height_source="Populous 2009: brick rotunda 60 ft (18 m); upper deck roof ~128 ft (39 m); field 335/408/330 ft; LiDAR 24.3 m (average)", budget=BUDGET_TRIS),
    "c_barclays_center": dict(name="Barclays Center", bins=[3398156], height_m=42.1, height_source="SHoP/Ellerbe Becket 2012: 137 ft (42 m) weathering-steel bands, oculus canopy 117 ft long; LiDAR 42.1 m", budget=BUDGET_TRIS),
    "c_usta_arthur_ashe": dict(name="Arthur Ashe Stadium", bins=[4467715], height_m=46.0, height_source="Rossetti 1997/2016: 23,771 seats; retractable roof on 8 columns; overall height ~150 ft (46 m) estimated from Rossetti sections (footprint LiDAR 17.7 m pre-roof, unreliable)", budget=BUDGET_TRIS),
    "c_domino_sugar_refinery": dict(name="Domino Sugar Refinery + Domino Park", bins=[3335796], height_m=60.0, lp_number="LP-2268", height_source="Havemeyer 1882-84 refinery: brick to 155 ft (47 m); PAU 2023 glass barrel vault to ~200 ft (60 m); OSM 65 m; LiDAR 45.8 m (pre-vault)", budget=BUDGET_TRIS),
    "c_kings_theatre": dict(name="Kings Theatre", bins=[3117845], height_m=25.2, height_source="Rapp & Rapp 1929: 3,000-seat theatre; LiDAR 25.2 m (fly tower)", budget=BUDGET_TRIS),
    "c_brooklyn_museum": dict(name="Brooklyn Museum", bins=[3029667], height_m=50.0, lp_number="LP-0057", height_source="McKim Mead & White 1897-1927: 5 storeys, dome; LiDAR 50.0 m (dome top); OSM 50.0", budget=BUDGET_TRIS),
    "c_brooklyn_public_library": dict(name="Brooklyn Public Library, Central Library", bins=[3029665], height_m=29.3, lp_number="LP-1972", height_source="Githens & Keally 1941: 50 ft gilded portal; LiDAR 29.3 m", budget=BUDGET_TRIS),
    "c_williamsburgh_savings_bank_tower": dict(name="Williamsburgh Savings Bank Tower (One Hanson Place)", bins=[3059183], height_m=156.0, lp_number="LP-0973",
                                                height_source="Halsey, McCormack & Helmer 1929: 512 ft (156 m), 37 floors, four 27-ft clock faces; LiDAR 157.6 m", budget=BUDGET_TRIS),
    "c_pier_17_seaport": dict(name="Pier 17 (South Street Seaport)", bins=[1090548], height_m=20.7, height_source="SHoP 2018: 4 storeys incl. 1.5-acre rooftop; LiDAR 20.7 m", budget=BUDGET_TRIS),
    "c_battery_maritime_and_whitehall_ferry_terminal": dict(name="Whitehall Ferry Terminal + Battery Maritime Building + St. George Ferry Terminal", bins=[1085792, 1000003, 5141706], height_m=27.7,
                                                            lp_number="LP-0102", height_source="Schwartz Architects 2005 Whitehall: 75-ft glass hall; LiDAR 27.7 m; BMB 1909 cast-iron 3 storeys LiDAR 21.6 m; St George 2005 LiDAR 18.5 m", budget=BUDGET_TRIS),
    "c_flushing_meadows": dict(name="New York State Pavilion (Tent of Tomorrow, Observation Towers, Theaterama) + Queens Museum", bins=[4464054, 4541449, 4464056, 4458851], height_m=69.0,
                               lp_number="LP-2318", height_source="Philip Johnson 1964: towers 60/150/226 ft (tallest 69 m); Tent 16 columns 100 ft; LiDAR towers 64.3 m", budget=BUDGET_TRIS),
    "c_bronx_courthouse": dict(name="Bronx County Courthouse (Mario Merola Building)", bins=[2002869], height_m=58.5, lp_number="LP-1027", height_source="Freedlander & Hausle 1933: 9 storeys + 4-storey tower; LiDAR 58.5 m", budget=BUDGET_TRIS),
    "c_bronx_zoo_gate": dict(name="Bronx Zoo Rainey Memorial Gates", bins=[], height_m=11.0, lp_number="LP-0123", height_source="Paul Manship 1934: bronze gates 36 ft (11 m) high, 40 ft wide; no building footprint (placed by WGS84 coordinate)", budget=BUDGET_TRIS),
    "c_high_line": dict(name="The High Line", bins=[], height_m=9.1, height_source="Friends of the High Line: deck ~30 ft (9.1 m) above street, 1.45 mi (2.33 km) Gansevoort-34th; 30-60 ft wide; alignment from OSM ways name='High Line'", budget=BUDGET_TRIS_LARGE),
    "c_little_island": dict(name="Little Island (Pier 55)", bins=[], height_m=18.9, height_source="Heatherwick/MNLA 2021: 2.4 acres, 132 tulip pots, deck 15-62 ft (4.6-18.9 m) above water; outline from OSM way 'Little Island'", budget=BUDGET_TRIS),
    "c_pier_57": dict(name="Pier 57", bins=[1012253], height_m=19.3, height_source="Emil Praeger 1954: 3 storeys on caissons, 850 ft long; LiDAR 19.3 m", budget=BUDGET_TRIS),
    "c_chelsea_market": dict(name="Chelsea Market (National Biscuit Company complex)", bins=[1012541], height_m=37.7, height_source="Nabisco 1890-1934: 11 storeys max; LiDAR 37.7 m", budget=BUDGET_TRIS),
    "c_javits_center": dict(name="Jacob K. Javits Convention Center", bins=[1067973, 1089474], height_m=53.6, height_source="I.M. Pei/James Freed 1986: space-frame crystal palace 150 ft (46 m) hall; LiDAR 53.6 m", budget=BUDGET_TRIS),
    "c_penn_station_moynihan": dict(name="Moynihan Train Hall (James A. Farley Building)", bins=[1084820], height_m=31.2, lp_number="LP-0233", height_source="McKim Mead & White 1913: 8 storeys, 53-ft Corinthian colonnade; SOM 2021 skylight 92 ft above hall floor; LiDAR 31.2 m", budget=BUDGET_TRIS),
}
for _k, _v in C_LANDMARKS.items():
    _v.setdefault("script", _k)
    _v.setdefault("lp_number", "")


# --------------------------------------------------------------------------------------------------------- footprints
@dataclass
class Footprint:
    bin: int
    name: str
    height: float
    ground_z: float
    cx: float
    cy: float
    year: int | None
    area: float
    geometry: object  # shapely (Multi)Polygon in NYC_TM
    source: str

    def polygons(self) -> list:
        g = self.geometry
        return list(getattr(g, "geoms", [g]))

    def polygon(self):
        """Largest polygon of the footprint."""
        return max(self.polygons(), key=lambda p: p.area)

    def rings(self) -> list[list[tuple[float, float]]]:
        """Exterior rings (CCW, closing point removed) of every polygon."""
        from shapely.geometry.polygon import orient
        out = []
        for p in self.polygons():
            p = orient(p, sign=1.0)
            out.append([(float(x), float(y)) for x, y in list(p.exterior.coords)[:-1]])
        return out

    @property
    def bounds(self) -> tuple[float, float, float, float]:
        return tuple(float(v) for v in self.geometry.bounds)


_COLS = ["bin", "name", "height", "ground_z", "cx", "cy", "construction_year", "shape_area", "geometry"]


def _rows_to_footprints(table, source: str) -> list[Footprint]:
    from shapely import wkb
    cols = {c: table.column(c).to_pylist() for c in _COLS}
    out = []
    for i in range(table.num_rows):
        g = wkb.loads(cols["geometry"][i])
        out.append(Footprint(int(cols["bin"][i]), cols["name"][i] or "", float(cols["height"][i] or 0.0), float(cols["ground_z"][i] or 0.0),
                             float(cols["cx"][i]), float(cols["cy"][i]), cols["construction_year"][i], float(cols["shape_area"][i] or g.area), g, source))
    return out


def _query(path: Path, filt, source: str) -> list[Footprint]:
    import pyarrow.dataset as ds
    dset = ds.dataset(str(path), format="parquet")
    return _rows_to_footprints(dset.to_table(columns=_COLS, filter=filt), source)


def load_footprints(bins: Sequence[int]) -> list[Footprint]:
    """Footprints for the given BINs: candidate file first, then the raw city-wide file (pyarrow filters only)."""
    import pyarrow.compute as pc
    bins = [int(b) for b in bins]
    if not bins:
        return []
    found: dict[int, Footprint] = {}
    if FOOTPRINTS.exists():
        for fp in _query(FOOTPRINTS, pc.field("bin").isin(bins), "candidate_footprints"):
            found.setdefault(fp.bin, fp)
    missing = [b for b in bins if b not in found]
    if missing:
        if not FOOTPRINTS_RAW.exists():
            raise FileNotFoundError(f"{FOOTPRINTS_RAW} missing; cannot resolve BINs {missing}")
        for fp in _query(FOOTPRINTS_RAW, pc.field("bin").isin(missing), "footprints_raw"):
            found.setdefault(fp.bin, fp)
    still = [b for b in bins if b not in found]
    if still:
        raise KeyError(f"BIN(s) not in any footprint file: {still}")
    return [found[b] for b in bins]


def load_footprint(key: int | str) -> Footprint:
    """``key``: BIN (int), a landmark id from ``C_LANDMARKS`` (first BIN), or a footprint ``name`` (case-insensitive,
    candidate file only)."""
    import pyarrow.compute as pc
    if isinstance(key, int) or (isinstance(key, str) and key.isdigit()):
        return load_footprints([int(key)])[0]
    if key in C_LANDMARKS:
        bins = C_LANDMARKS[key]["bins"]
        if not bins:
            raise KeyError(f"{key} has no footprint BIN (positioned by coordinate)")
        return load_footprints(bins)[0]
    if not FOOTPRINTS.exists():
        raise FileNotFoundError(FOOTPRINTS)
    rows = _query(FOOTPRINTS, pc.equal(pc.utf8_lower(pc.field("name")), key.lower()), "candidate_footprints")
    if not rows:
        raise KeyError(f"no candidate footprint named {key!r}")
    return max(rows, key=lambda r: r.area)


def footprints_in_bbox(x0: float, y0: float, x1: float, y1: float, *, min_height: float = 0.0, min_area: float = 0.0,
                       exclude_bins: Iterable[int] = ()) -> list[Footprint]:
    """All city footprints whose centroid lies in the NYC_TM box (used for context shells in verification renders)."""
    import pyarrow.compute as pc
    filt = (pc.field("cx") >= x0) & (pc.field("cx") <= x1) & (pc.field("cy") >= y0) & (pc.field("cy") <= y1)
    if min_height > 0:
        filt = filt & (pc.field("height") >= min_height)
    if min_area > 0:
        filt = filt & (pc.field("shape_area") >= min_area)
    ex = set(int(b) for b in exclude_bins)
    return [fp for fp in _query(FOOTPRINTS_RAW, filt, "footprints_raw") if fp.bin not in ex]


def min_rect(polygon) -> tuple[tuple[float, float], float, float, float]:
    """Minimum rotated rectangle of a shapely polygon -> (centre, length, width, math angle deg of the long axis)."""
    r = polygon.minimum_rotated_rectangle
    pts = list(r.exterior.coords)[:-1]
    e0 = math.dist(pts[0], pts[1])
    e1 = math.dist(pts[1], pts[2])
    if e0 >= e1:
        ang = math.degrees(math.atan2(pts[1][1] - pts[0][1], pts[1][0] - pts[0][0]))
        length, width = e0, e1
    else:
        ang = math.degrees(math.atan2(pts[2][1] - pts[1][1], pts[2][0] - pts[1][0]))
        length, width = e1, e0
    c = r.centroid
    return (float(c.x), float(c.y)), float(length), float(width), ang % 180.0


def footprint_heading(fp: Footprint) -> float:
    """Compass heading (0 = north, clockwise) of the footprint's principal (long) axis, in [0, 180)."""
    _, _, _, ang = min_rect(fp.polygon())
    return (90.0 - ang) % 180.0


def grid_heading_near(fp: Footprint) -> float:
    """Snap a footprint's principal axis to the Manhattan grid (29° or 119°) when within 4°, else keep it."""
    h = footprint_heading(fp)
    for g in (MANHATTAN_GRID_HEADING, MANHATTAN_GRID_HEADING + 90.0):
        if abs(h - g) < 4.0:
            return g
    return h


# --------------------------------------------------------------------------------------------------------- frames
@dataclass
class LocalFrame:
    """Model origin in NYC_TM (x, y) / NAVD88 (z).  Model axes are east/north (unrotated); ``heading_deg`` is the
    compass heading of the landmark's principal axis (informational + used by ``grid_matrix``)."""
    x: float
    y: float
    z: float
    heading_deg: float = 0.0

    @property
    def origin_tm(self) -> list[float]:
        return [round(self.x, 3), round(self.y, 3), round(self.z, 3)]

    def to_local(self, X: float, Y: float, Z: float | None = None):
        if Z is None:
            return (X - self.x, Y - self.y)
        return (X - self.x, Y - self.y, Z - self.z)

    def ring_local(self, ring: Sequence[Sequence[float]]) -> list[tuple[float, float]]:
        return [(p[0] - self.x, p[1] - self.y) for p in ring]

    def from_lonlat(self, lon: float, lat: float, z: float = 0.0) -> tuple[float, float, float]:
        X, Y = lonlat_to_tm(lon, lat)
        return (float(X) - self.x, float(Y) - self.y, z)

    def grid_matrix(self, heading_deg: float | None = None, at=(0.0, 0.0, 0.0)) -> Matrix:
        """Matrix that maps grid-local coordinates (u along the axis with compass heading ``heading_deg``, v 90° to
        its left, w up) to model coordinates, translated to ``at``."""
        h = self.heading_deg if heading_deg is None else heading_deg
        return Matrix.Translation(Vector(at)) @ Matrix.Rotation(math.radians(90.0 - h), 4, "Z")


def local_frame(origin: Footprint | Sequence[Footprint] | Sequence[float], z0: float | None = None, heading_deg: float | None = None) -> LocalFrame:
    """Frame at a footprint's centroid (or the joint centroid of several) with z0 = its LiDAR ground_z, heading snapped
    to the Manhattan grid; or at an explicit (x, y)."""
    if isinstance(origin, Footprint):
        c = origin.geometry.centroid
        return LocalFrame(round(float(c.x), 2), round(float(c.y), 2), round(origin.ground_z if z0 is None else z0, 2),
                          grid_heading_near(origin) if heading_deg is None else heading_deg)
    if isinstance(origin, (list, tuple)) and origin and isinstance(origin[0], Footprint):
        from shapely.ops import unary_union
        u = unary_union([f.geometry for f in origin]).centroid
        gz = min(f.ground_z for f in origin) if z0 is None else z0
        return LocalFrame(round(float(u.x), 2), round(float(u.y), 2), round(gz, 2),
                          grid_heading_near(origin[0]) if heading_deg is None else heading_deg)
    x, y = float(origin[0]), float(origin[1])
    return LocalFrame(x, y, 0.0 if z0 is None else z0, heading_deg or 0.0)


def frame_from_lonlat(lon: float, lat: float, z0: float = 0.0, heading_deg: float = 0.0) -> LocalFrame:
    x, y = lonlat_to_tm(lon, lat)
    return LocalFrame(round(float(x), 2), round(float(y), 2), z0, heading_deg)


# --------------------------------------------------------------------------------------------------------- materials
# name -> (base colour RGBA linear, roughness, metallic).  Colours are documented approximations of the real finishes
# (sRGB hex noted) — no texture is claimed unless textures.py supplies one (see ``mat``).
PALETTE: dict[str, tuple[tuple[float, float, float, float], float, float]] = {
    "limestone": ((0.78, 0.74, 0.66, 1.0), 0.80, 0.0),          # Indiana limestone #E3DCCB
    "limestone_warm": ((0.80, 0.72, 0.58, 1.0), 0.80, 0.0),     # buff limestone / Met facade
    "granite_grey": ((0.45, 0.45, 0.46, 1.0), 0.55, 0.0),
    "granite_pink": ((0.62, 0.50, 0.46, 1.0), 0.50, 0.0),       # Seagram plaza / Carnegie
    "granite_dark": ((0.16, 0.16, 0.17, 1.0), 0.35, 0.0),
    "marble_white": ((0.90, 0.89, 0.86, 1.0), 0.40, 0.0),
    "travertine": ((0.86, 0.80, 0.68, 1.0), 0.70, 0.0),         # Lincoln Center
    "brownstone": ((0.42, 0.29, 0.22, 1.0), 0.85, 0.0),
    "red_brick": ((0.50, 0.22, 0.16, 1.0), 0.90, 0.0),          # #8C3A2B
    "brown_brick": ((0.40, 0.27, 0.20, 1.0), 0.90, 0.0),
    "tan_brick": ((0.72, 0.62, 0.48, 1.0), 0.90, 0.0),          # Dakota buff brick
    "yellow_brick": ((0.78, 0.68, 0.46, 1.0), 0.90, 0.0),
    "white_brick": ((0.86, 0.85, 0.80, 1.0), 0.85, 0.0),
    "terracotta": ((0.72, 0.52, 0.42, 1.0), 0.70, 0.0),         # 111 W 57 glazed terracotta (warm bronze-white)
    "terracotta_white": ((0.86, 0.82, 0.74, 1.0), 0.55, 0.0),
    "concrete": ((0.62, 0.61, 0.58, 1.0), 0.90, 0.0),
    "concrete_white": ((0.85, 0.84, 0.80, 1.0), 0.85, 0.0),     # Guggenheim gunite (repainted 2008, warm white)
    "precast": ((0.74, 0.72, 0.68, 1.0), 0.85, 0.0),
    "stucco": ((0.80, 0.77, 0.70, 1.0), 0.90, 0.0),
    "bronze": ((0.35, 0.24, 0.14, 1.0), 0.45, 0.9),             # Seagram bronze mullions
    "bronze_dark": ((0.20, 0.14, 0.09, 1.0), 0.50, 0.9),
    "copper_new": ((0.72, 0.45, 0.20, 1.0), 0.35, 1.0),         # Vessel copper-coloured steel cladding
    "copper_patina": ((0.30, 0.55, 0.50, 1.0), 0.70, 0.3),
    "steel_black": ((0.05, 0.05, 0.05, 1.0), 0.45, 0.8),
    "steel_grey": ((0.45, 0.46, 0.48, 1.0), 0.40, 0.9),
    "steel_white": ((0.85, 0.86, 0.87, 1.0), 0.40, 0.7),
    "steel_galv": ((0.60, 0.62, 0.64, 1.0), 0.50, 0.9),
    "weathering_steel": ((0.40, 0.20, 0.10, 1.0), 0.85, 0.2),   # Barclays Center Cor-ten
    "aluminium": ((0.72, 0.73, 0.75, 1.0), 0.35, 0.9),
    "aluminium_dark": ((0.30, 0.31, 0.33, 1.0), 0.40, 0.9),
    "stainless": ((0.70, 0.71, 0.72, 1.0), 0.25, 1.0),          # Hearst diagrid stainless cladding
    "zinc": ((0.50, 0.52, 0.55, 1.0), 0.55, 0.6),
    "gold_leaf": ((0.85, 0.65, 0.20, 1.0), 0.25, 1.0),          # BPL portal, Met details
    "glass_clear": ((0.62, 0.70, 0.72, 0.35), 0.05, 0.0),
    "glass_blue": ((0.40, 0.55, 0.70, 0.55), 0.05, 0.1),
    "glass_dark": ((0.12, 0.16, 0.20, 0.85), 0.08, 0.1),        # Trump Tower / Solow dark bronze glass
    "glass_bronze": ((0.30, 0.22, 0.15, 0.80), 0.08, 0.2),      # Seagram / Solow
    "glass_green": ((0.45, 0.62, 0.58, 0.55), 0.05, 0.1),       # Lever House / UN Secretariat blue-green
    "glass_grey": ((0.35, 0.40, 0.45, 0.70), 0.06, 0.1),
    "glass_white": ((0.78, 0.82, 0.85, 0.50), 0.06, 0.0),       # frit / low-iron (Shed, Javits, 4TS)
    "glass_lit": ((0.95, 0.85, 0.60, 0.60), 0.10, 0.0),
    "spandrel_dark": ((0.10, 0.11, 0.13, 1.0), 0.35, 0.3),
    "spandrel_grey": ((0.40, 0.42, 0.44, 1.0), 0.40, 0.3),
    "spandrel_white": ((0.86, 0.87, 0.88, 1.0), 0.40, 0.2),
    "spandrel_bronze": ((0.32, 0.24, 0.16, 1.0), 0.40, 0.6),
    "roof_dark": ((0.12, 0.12, 0.12, 1.0), 0.90, 0.0),
    "roof_grey": ((0.45, 0.45, 0.45, 1.0), 0.90, 0.0),
    "roof_green": ((0.25, 0.35, 0.18, 1.0), 0.95, 0.0),
    "roof_copper_green": ((0.32, 0.52, 0.45, 1.0), 0.70, 0.2),
    "roof_slate": ((0.22, 0.24, 0.27, 1.0), 0.80, 0.0),
    "roof_red_tile": ((0.55, 0.25, 0.15, 1.0), 0.80, 0.0),
    "asphalt": ((0.15, 0.15, 0.15, 1.0), 0.95, 0.0),
    "pavers_grey": ((0.55, 0.54, 0.52, 1.0), 0.90, 0.0),
    "pavers_bluestone": ((0.35, 0.38, 0.42, 1.0), 0.85, 0.0),
    "planting": ((0.18, 0.32, 0.12, 1.0), 0.95, 0.0),
    "lawn": ((0.25, 0.42, 0.14, 1.0), 0.95, 0.0),
    "grass_field": ((0.22, 0.45, 0.15, 1.0), 0.95, 0.0),
    "infield_clay": ((0.55, 0.36, 0.22, 1.0), 0.95, 0.0),
    "water": ((0.10, 0.20, 0.25, 1.0), 0.05, 0.0),
    "wood_ipe": ((0.42, 0.28, 0.16, 1.0), 0.75, 0.0),           # High Line / Little Island decking
    "wood_weathered": ((0.55, 0.50, 0.42, 1.0), 0.85, 0.0),
    "seat_blue": ((0.05, 0.15, 0.45, 1.0), 0.70, 0.0),          # Yankee Stadium seats
    "seat_green": ((0.05, 0.30, 0.20, 1.0), 0.70, 0.0),         # Citi Field seats
    "seat_dark": ((0.10, 0.10, 0.12, 1.0), 0.70, 0.0),
    "red_glass": ((0.80, 0.05, 0.05, 0.60), 0.08, 0.0),         # TKTS steps
    "red_paint": ((0.70, 0.08, 0.06, 1.0), 0.50, 0.0),
    "white_paint": ((0.92, 0.92, 0.90, 1.0), 0.50, 0.0),
    "black_paint": ((0.03, 0.03, 0.03, 1.0), 0.50, 0.0),
    "yellow_paint": ((0.90, 0.70, 0.10, 1.0), 0.50, 0.0),
    "blue_paint": ((0.08, 0.20, 0.50, 1.0), 0.50, 0.0),
    "orange_paint": ((0.90, 0.40, 0.05, 1.0), 0.50, 0.0),
    "apple_red": ((0.75, 0.06, 0.04, 1.0), 0.40, 0.0),          # Home Run Apple
    "sign_white_emissive": ((0.95, 0.95, 0.92, 1.0), 0.40, 0.0),
    "shed_ptfe": ((0.92, 0.93, 0.94, 0.85), 0.60, 0.0),         # The Shed ETFE pillows
    "fabric_white": ((0.90, 0.90, 0.90, 1.0), 0.80, 0.0),
    "interior_dark": ((0.05, 0.05, 0.06, 1.0), 0.90, 0.0),
}
# NYCSim material-enum names (DATA_CONTRACTS §5 material_primary) for which textures.py may supply PBR maps.
TEXTURE_NAMES: dict[str, str] = {
    "limestone": "limestone", "limestone_warm": "limestone", "granite_grey": "granite", "granite_pink": "granite", "granite_dark": "granite",
    "brownstone": "brownstone", "red_brick": "red_brick", "brown_brick": "brown_brick", "tan_brick": "tan_brick", "yellow_brick": "tan_brick",
    "white_brick": "white_glazed_brick", "terracotta": "terracotta", "concrete": "concrete", "concrete_white": "concrete", "precast": "precast",
    "stucco": "stucco", "asphalt": "asphalt", "pavers_grey": "concrete", "wood_ipe": "wood_clapboard", "marble_white": "marble", "travertine": "limestone",
}
_TEXTURES_ENABLED = os.environ.get("NYCSIM_LANDMARK_TEXTURES", "1") != "0"
_TEXTURE_RES = os.environ.get("NYCSIM_LANDMARK_TEXTURE_RES", "1K")
_texture_status: dict[str, str] = {}


def _try_textures(pal_name: str) -> dict[str, str] | None:
    """PBR maps for a palette name via blender/common/textures.py, or None (reason logged once per name)."""
    if not _TEXTURES_ENABLED or pal_name not in TEXTURE_NAMES:
        return None
    if pal_name in _texture_status:
        return None
    try:
        import textures  # blender/common/textures.py (facade-kit agent)
        maps = textures.get_texture_set(TEXTURE_NAMES[pal_name], _TEXTURE_RES)
        _texture_status[pal_name] = "ok"
        return {k: v for k, v in maps.items() if k in ("color", "roughness", "normal", "metalness")}
    except Exception as e:  # catalog missing, offline, unknown name -> documented Principled colour instead
        _texture_status[pal_name] = f"fallback: {type(e).__name__}: {str(e)[:120]}"
        log.info("material %s: no texture (%s); using documented Principled colour", pal_name, _texture_status[pal_name])
        return None


def texture_status() -> dict[str, str]:
    return dict(_texture_status)


def mat(name: str) -> bpy.types.Material:
    """Principled material ``NYC_<name>`` from ``PALETTE`` (created once per scene).  Glass names get alpha blending;
    masonry names get PBR maps when textures.py can provide them (UVs are in metres, one tile per
    ``physical_size_m``)."""
    if name not in PALETTE:
        raise KeyError(f"unknown palette material {name!r}")
    mname = f"NYC_{name}"
    m = bpy.data.materials.get(mname)
    if m is not None:
        return m
    color, rough, metal = PALETTE[name]
    maps = _try_textures(name)
    if maps:
        tex = {k: v for k, v in maps.items() if k in ("color", "roughness", "normal")}
        try:
            import textures
            size = float(textures.get_texture_meta(TEXTURE_NAMES[name]).get("physical_size_m", 2.0))
        except Exception:
            size = 2.0
        m = nb.pbr_material(mname, base_color=color, roughness=rough, metallic=metal, textures=tex, uv_scale_m=size)
        m["nycsim_textured"] = True
    else:
        m = nb.pbr_material(mname, base_color=color, roughness=rough, metallic=metal, alpha=color[3])
        m["nycsim_textured"] = False
    m["nycsim_material"] = name
    if color[3] < 1.0:
        bsdf = m.node_tree.nodes["Principled BSDF"]
        bsdf.inputs["Transmission Weight"].default_value = 0.0  # keep glTF simple: alpha-blended tinted glass
        m.blend_method = "BLEND"
        m.use_backface_culling = False
    return m


def screen_material(n: int, color=(0.9, 0.9, 1.0, 1.0), strength: float = 4.0) -> bpy.types.Material:
    """Emissive LED-screen slot ``TSQ_SCREEN_<n>`` (the engine swaps a video texture onto it; UV 0..1 per screen)."""
    mname = f"TSQ_SCREEN_{n}"
    m = bpy.data.materials.get(mname)
    if m is not None:
        return m
    m = nb.pbr_material(mname, base_color=(0.02, 0.02, 0.02, 1.0), roughness=0.3, metallic=0.0, emission=color, emission_strength=strength)
    m["nycsim_material"] = "led_screen"
    m["nycsim_screen_index"] = n
    return m


def emissive_material(name: str, color, strength: float = 3.0) -> bpy.types.Material:
    mname = f"NYC_EMIT_{name}"
    m = bpy.data.materials.get(mname)
    if m is not None:
        return m
    m = nb.pbr_material(mname, base_color=(0.05, 0.05, 0.05, 1.0), roughness=0.4, emission=color, emission_strength=strength)
    m["nycsim_material"] = f"emissive_{name}"
    return m


# --------------------------------------------------------------------------------------------------------- mesh builder
class MB:
    """Accumulates faces (with per-face material and optional per-loop UVs) and builds one Blender mesh object.
    Far faster than one bpy object per architectural element.  Coordinates are model metres."""

    def __init__(self, name: str):
        self.name = name
        self.verts: list[tuple[float, float, float]] = []
        self.faces: list[tuple[int, ...]] = []
        self.face_mat: list[int] = []
        self.face_uv: list[list[tuple[float, float]] | None] = []
        self.mats: list[bpy.types.Material] = []
        self._mi: dict[str, int] = {}
        self.smooth_faces: set[int] = set()

    # -- materials
    def mi(self, material: str | bpy.types.Material) -> int:
        m = mat(material) if isinstance(material, str) else material
        if m.name not in self._mi:
            self._mi[m.name] = len(self.mats)
            self.mats.append(m)
        return self._mi[m.name]

    # -- primitives
    def face(self, pts: Sequence[Sequence[float]], material, uvs: Sequence[Sequence[float]] | None = None, *, smooth: bool = False,
             m: Matrix | None = None) -> int:
        base = len(self.verts)
        if m is not None:
            pts = [tuple((m @ Vector(p))[:]) for p in pts]
        self.verts.extend(tuple(float(c) for c in p) for p in pts)
        self.faces.append(tuple(range(base, base + len(pts))))
        self.face_mat.append(self.mi(material))
        self.face_uv.append([tuple(uv) for uv in uvs] if uvs is not None else None)
        if smooth:
            self.smooth_faces.add(len(self.faces) - 1)
        return len(self.faces) - 1

    def quad(self, a, b, c, d, material, uv_metres: bool = True, uvs=None, **kw) -> int:
        """Quad a-b-c-d (CCW seen from outside).  Default UVs: u along a->b, v along a->d, in metres."""
        if uvs is None and uv_metres:
            w = math.dist(a, b)
            h = math.dist(a, d)
            uvs = [(0, 0), (w, 0), (w, h), (0, h)]
        return self.face([a, b, c, d], material, uvs, **kw)

    def tri(self, a, b, c, material, **kw) -> int:
        return self.face([a, b, c], material, None, **kw)

    def box(self, lo: Sequence[float], hi: Sequence[float], material, *, faces: str = "xyzXYZ", m: Matrix | None = None, **kw) -> None:
        """Axis-aligned box from min corner ``lo`` to max corner ``hi``; ``faces`` selects sides (x=-X, X=+X ...)."""
        x0, y0, z0 = lo
        x1, y1, z1 = hi
        P = lambda x, y, z: (x, y, z)  # noqa: E731
        if "z" in faces:
            self.quad(P(x0, y0, z0), P(x0, y1, z0), P(x1, y1, z0), P(x1, y0, z0), material, m=m, **kw)
        if "Z" in faces:
            self.quad(P(x0, y0, z1), P(x1, y0, z1), P(x1, y1, z1), P(x0, y1, z1), material, m=m, **kw)
        if "y" in faces:
            self.quad(P(x0, y0, z0), P(x1, y0, z0), P(x1, y0, z1), P(x0, y0, z1), material, m=m, **kw)
        if "X" in faces:
            self.quad(P(x1, y0, z0), P(x1, y1, z0), P(x1, y1, z1), P(x1, y0, z1), material, m=m, **kw)
        if "Y" in faces:
            self.quad(P(x1, y1, z0), P(x0, y1, z0), P(x0, y1, z1), P(x1, y1, z1), material, m=m, **kw)
        if "x" in faces:
            self.quad(P(x0, y1, z0), P(x0, y0, z0), P(x0, y0, z1), P(x0, y1, z1), material, m=m, **kw)

    def box_c(self, center: Sequence[float], size: Sequence[float], material, **kw) -> None:
        cx, cy, cz = center
        sx, sy, sz = size
        self.box((cx - sx / 2, cy - sy / 2, cz - sz / 2), (cx + sx / 2, cy + sy / 2, cz + sz / 2), material, **kw)

    def bar(self, p0: Sequence[float], p1: Sequence[float], w: float, h: float, material, *, up=(0, 0, 1), cap: bool = True) -> None:
        """Rectangular bar of cross-section w (across) × h (along ``up``) from p0 to p1 (structural members)."""
        a = Vector(p0)
        b = Vector(p1)
        ax = b - a
        L = ax.length
        if L < 1e-6:
            return
        ax.normalize()
        upv = Vector(up)
        if abs(ax.dot(upv)) > 0.999:
            upv = Vector((1, 0, 0))
        side = ax.cross(upv).normalized()
        upv = side.cross(ax).normalized()
        hw, hh = w / 2, h / 2
        c = [a + side * hw + upv * hh, a - side * hw + upv * hh, a - side * hw - upv * hh, a + side * hw - upv * hh]
        d = [p + ax * L for p in c]
        mi = material
        for i in range(4):
            j = (i + 1) % 4
            self.quad(tuple(c[i]), tuple(d[i]), tuple(d[j]), tuple(c[j]), mi)
        if cap:
            self.face([tuple(p) for p in reversed(c)], mi)
            self.face([tuple(p) for p in d], mi)

    def prism(self, ring: Sequence[Sequence[float]], z0: float, z1: float, wall_material, top_material=None, *, holes: Sequence[Sequence[Sequence[float]]] = (),
              cap_top: bool = True, cap_bottom: bool = False, m: Matrix | None = None, smooth: bool = False, u0: float = 0.0) -> None:
        """Extrude a CCW 2-D ring (with optional CW-or-CCW holes) between z0 and z1; wall UVs in metres."""
        ring = [tuple(p[:2]) for p in ring]
        if _signed_area(ring) < 0:
            ring = ring[::-1]
        holes = [[tuple(p[:2]) for p in h] for h in holes]
        holes = [h[::-1] if _signed_area(h) > 0 else h for h in holes]  # holes CW so their walls face inwards
        u = u0
        for loop in [ring] + holes:
            n = len(loop)
            for i in range(n):
                a = loop[i]
                b = loop[(i + 1) % n]
                seg = math.dist(a, b)
                self.quad((a[0], a[1], z0), (b[0], b[1], z0), (b[0], b[1], z1), (a[0], a[1], z1), wall_material,
                          uvs=[(u, 0), (u + seg, 0), (u + seg, z1 - z0), (u, z1 - z0)], smooth=smooth, m=m)
                u += seg
        if cap_top or cap_bottom:
            tris = nb.triangulate_2d(ring, holes)
            allp = list(ring) + [p for h in holes for p in h]
            tm = top_material if top_material is not None else wall_material
            for a, b, c in tris:
                if cap_top:
                    self.face([(allp[a][0], allp[a][1], z1), (allp[b][0], allp[b][1], z1), (allp[c][0], allp[c][1], z1)], tm,
                              [(allp[a][0], allp[a][1]), (allp[b][0], allp[b][1]), (allp[c][0], allp[c][1])], m=m)
                if cap_bottom:
                    self.face([(allp[c][0], allp[c][1], z0), (allp[b][0], allp[b][1], z0), (allp[a][0], allp[a][1], z0)], tm, m=m)

    def polygon_cap(self, ring: Sequence[Sequence[float]], z: float, material, *, holes=(), flip: bool = False, m: Matrix | None = None) -> None:
        """Flat horizontal polygon at height z (upward-facing unless flip)."""
        ring = [tuple(p[:2]) for p in ring]
        if _signed_area(ring) < 0:
            ring = ring[::-1]
        holes = [[tuple(p[:2]) for p in h] for h in holes]
        holes = [h[::-1] if _signed_area(h) > 0 else h for h in holes]
        tris = nb.triangulate_2d(ring, holes)
        allp = list(ring) + [p for h in holes for p in h]
        for a, b, c in tris:
            pts = [(allp[a][0], allp[a][1], z), (allp[b][0], allp[b][1], z), (allp[c][0], allp[c][1], z)]
            if flip:
                pts.reverse()
            self.face(pts, material, [(p[0], p[1]) for p in pts], m=m)

    def loft(self, rings: Sequence[Sequence[Sequence[float]]], material, *, close: bool = True, smooth: bool = True, cap_end: bool = False,
             cap_start: bool = False, m: Matrix | None = None) -> None:
        """Skin successive 3-D rings with the same vertex count (frustums, domes, tapering shafts)."""
        n = len(rings[0])
        for r in rings:
            if len(r) != n:
                raise ValueError("loft rings must have equal vertex counts")
        for k in range(len(rings) - 1):
            r0, r1 = rings[k], rings[k + 1]
            rng = range(n) if close else range(n - 1)
            for i in rng:
                j = (i + 1) % n
                a, b, c, d = r0[i], r0[j], r1[j], r1[i]
                if math.dist(c, d) < 1e-9:      # apex
                    self.face([a, b, c], material, None, smooth=smooth, m=m)
                elif math.dist(a, b) < 1e-9:
                    self.face([a, c, d], material, None, smooth=smooth, m=m)
                else:
                    self.face([a, b, c, d], material, None, smooth=smooth, m=m)
        if cap_start:
            self.face(list(reversed(rings[0])), material, None, m=m)
        if cap_end:
            self.face(list(rings[-1]), material, None, m=m)

    def cylinder(self, cx: float, cy: float, z0: float, z1: float, r0: float, r1: float | None = None, material="concrete", *, segs: int = 32,
                 cap_top: bool = True, cap_bottom: bool = False, phase: float = 0.0, smooth: bool = True, top_material=None, m: Matrix | None = None) -> None:
        r1 = r0 if r1 is None else r1
        ring0 = circle(cx, cy, r0, segs, z0, phase)
        ring1 = circle(cx, cy, r1, segs, z1, phase)
        self.loft([ring0, ring1], material, smooth=smooth, m=m)
        if cap_top and r1 > 1e-6:
            self.face(list(ring1), top_material or material, None, m=m)
        if cap_bottom and r0 > 1e-6:
            self.face(list(reversed(ring0)), top_material or material, None, m=m)

    def dome(self, cx: float, cy: float, z0: float, r: float, height: float, material, *, segs: int = 32, rows: int = 10, m: Matrix | None = None,
             r_top: float = 0.0, z_top: float | None = None) -> None:
        """Spherical-cap dome (ellipsoidal if height != r); optional flat top opening of radius r_top."""
        rings = []
        for k in range(rows + 1):
            t = k / rows
            ang = t * math.pi / 2
            rr = r * math.cos(ang)
            if rr < r_top:
                rr = r_top
            z = z0 + height * math.sin(ang)
            rings.append(circle(cx, cy, max(rr, 1e-4 if k == rows and r_top == 0 else rr), segs, z))
        if r_top == 0:
            rings[-1] = [(cx, cy, z0 + height)] * segs
        self.loft(rings, material, smooth=True, m=m)
        if r_top > 0:
            self.face(list(rings[-1]), material, None, m=m)

    def sweep(self, profile: Sequence[Sequence[float]], path: Sequence[Sequence[float]], material, *, closed_path: bool = True, smooth: bool = False,
              m: Matrix | None = None) -> None:
        """Sweep a 2-D profile (outward offset ``d``, height ``h`` pairs) along a horizontal polyline path (CCW ring for a
        cornice around a building).  Profile points are (offset outward from the path, z relative to the path z)."""
        n = len(path)
        frames = []
        for i in range(n):
            p = Vector(path[i])
            if closed_path:
                prev = Vector(path[i - 1])
                nxt = Vector(path[(i + 1) % n])
                t = ((nxt - p).normalized() + (p - prev).normalized())
                if t.length < 1e-6:
                    t = (nxt - p)
            else:
                if i == 0:
                    t = Vector(path[1]) - p
                elif i == n - 1:
                    t = p - Vector(path[n - 2])
                else:
                    t = (Vector(path[i + 1]) - p).normalized() + (p - Vector(path[i - 1])).normalized()
            t.z = 0
            t.normalize()
            out = Vector((t.y, -t.x, 0))  # right-hand side of travel = outward for a CCW ring
            # mitre scale at corners
            if closed_path:
                d0 = (p - Vector(path[i - 1])).normalized()
                cosang = max(0.35, abs(out.dot(Vector((d0.y, -d0.x, 0)))))
            else:
                cosang = 1.0
            frames.append((p, out / cosang))
        rings = []
        for (p, out) in frames:
            rings.append([tuple(p + out * d + Vector((0, 0, h))) for d, h in profile])
        # build as quads between successive path stations
        cnt = n if closed_path else n - 1
        for i in range(cnt):
            r0 = rings[i]
            r1 = rings[(i + 1) % n]
            for k in range(len(profile) - 1):
                self.face([r0[k], r1[k], r1[k + 1], r0[k + 1]], material, None, smooth=smooth, m=m)

    def transform(self, mtx: Matrix) -> None:
        self.verts = [tuple((mtx @ Vector(v))[:]) for v in self.verts]

    def tri_count(self) -> int:
        return sum(max(0, len(f) - 2) for f in self.faces)

    def build(self, col: bpy.types.Collection | None = None, *, merge_dist: float = 0.0) -> bpy.types.Object:
        me = bpy.data.meshes.new(self.name)
        me.from_pydata(self.verts, [], self.faces)
        for m in self.mats:
            me.materials.append(m)
        me.polygons.foreach_set("material_index", self.face_mat)
        if self.smooth_faces:
            sm = [i in self.smooth_faces for i in range(len(self.faces))]
            me.polygons.foreach_set("use_smooth", sm)
        uv = me.uv_layers.new(name="UVMap")
        uvdata = uv.data
        li = 0
        for f, uvs in zip(me.polygons, self.face_uv):
            n = f.loop_total
            if uvs is not None and len(uvs) == n:
                for k in range(n):
                    uvdata[li + k].uv = uvs[k]
            else:
                # planar fallback: project on the dominant axis plane, metres
                vs = [self.verts[self.faces[f.index][k]] for k in range(n)]
                nx = abs(sum((vs[(k + 1) % n][1] - vs[k][1]) * (vs[(k + 1) % n][2] + vs[k][2]) for k in range(n)))
                ny = abs(sum((vs[(k + 1) % n][2] - vs[k][2]) * (vs[(k + 1) % n][0] + vs[k][0]) for k in range(n)))
                nz = abs(sum((vs[(k + 1) % n][0] - vs[k][0]) * (vs[(k + 1) % n][1] + vs[k][1]) for k in range(n)))
                for k in range(n):
                    x, y, z = vs[k]
                    if nz >= nx and nz >= ny:
                        uvdata[li + k].uv = (x, y)
                    elif nx >= ny:
                        uvdata[li + k].uv = (y, z)
                    else:
                        uvdata[li + k].uv = (x, z)
            li += n
        me.validate(verbose=False, clean_customdata=False)
        me.update()
        if merge_dist > 0:
            bm = bmesh.new()
            bm.from_mesh(me)
            bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=merge_dist)
            bm.to_mesh(me)
            bm.free()
        ob = bpy.data.objects.new(self.name, me)
        nb.link(ob, col)
        return ob


def _signed_area(ring: Sequence[Sequence[float]]) -> float:
    a = 0.0
    n = len(ring)
    for i in range(n):
        x0, y0 = ring[i][0], ring[i][1]
        x1, y1 = ring[(i + 1) % n][0], ring[(i + 1) % n][1]
        a += x0 * y1 - x1 * y0
    return a / 2.0


def circle(cx: float, cy: float, r: float, segs: int, z: float = 0.0, phase: float = 0.0) -> list[tuple[float, float, float]]:
    return [(cx + r * math.cos(phase + 2 * math.pi * i / segs), cy + r * math.sin(phase + 2 * math.pi * i / segs), z) for i in range(segs)]


def rect(w: float, d: float, cx: float = 0.0, cy: float = 0.0) -> list[tuple[float, float]]:
    return [(cx - w / 2, cy - d / 2), (cx + w / 2, cy - d / 2), (cx + w / 2, cy + d / 2), (cx - w / 2, cy + d / 2)]


def rot2(pts: Sequence[Sequence[float]], deg: float, cx: float = 0.0, cy: float = 0.0) -> list[tuple[float, float]]:
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    return [(cx + (p[0] - cx) * c - (p[1] - cy) * s, cy + (p[0] - cx) * s + (p[1] - cy) * c) for p in pts]


def offset_ring(ring: Sequence[Sequence[float]], d: float) -> list[tuple[float, float]]:
    """Inward (d<0) / outward (d>0) offset of a polygon ring via shapely (keeps the largest result polygon)."""
    from shapely.geometry import Polygon
    p = Polygon(ring).buffer(d, join_style=2, mitre_limit=4.0)
    p = max(getattr(p, "geoms", [p]), key=lambda q: q.area)
    from shapely.geometry.polygon import orient
    p = orient(p, sign=1.0)
    return [(float(x), float(y)) for x, y in list(p.exterior.coords)[:-1]]


def simplify_ring(ring: Sequence[Sequence[float]], tol: float = 0.3) -> list[tuple[float, float]]:
    from shapely.geometry import Polygon
    from shapely.geometry.polygon import orient
    p = orient(Polygon(ring).simplify(tol, preserve_topology=True), sign=1.0)
    return [(float(x), float(y)) for x, y in list(p.exterior.coords)[:-1]]


def tri_count(objects: Iterable[bpy.types.Object]) -> int:
    n = 0
    for o in objects:
        if o.type != "MESH":
            continue
        n += sum(max(0, len(p.vertices) - 2) for p in o.data.polygons)
    return n


def new_scene() -> None:
    nb.reset_scene()


def all_mesh_objects() -> list[bpy.types.Object]:
    return [o for o in bpy.data.objects if o.type == "MESH"]


# --------------------------------------------------------------------------------------------------------- export
def _rel(path: Path) -> str:
    """Repo-relative path when inside the repo (normal case), else the absolute path (tests with NYCSIM_BLENDER_OUT)."""
    try:
        return str(path.relative_to(REPO))
    except ValueError:
        return str(path)


def _record_processed(artifact_id: str, path: Path, sources: list[str], extra: dict) -> None:
    """manifest.record_processed under an advisory lock (the manifest JSON is shared with other agents)."""
    try:
        from nycsim_pipeline import manifest
        lock = manifest.MANIFEST / ".processed.lock"
        lock.parent.mkdir(parents=True, exist_ok=True)
        with open(lock, "w") as lf:
            fcntl.flock(lf, fcntl.LOCK_EX)
            try:
                manifest.record_processed(artifact_id, path, stage="landmarks_c", sources=sources, rows=None, schema="glb", extra=extra)
            finally:
                fcntl.flock(lf, fcntl.LOCK_UN)
    except Exception as e:  # never fail an export because the shared manifest is busy/broken; reported in the log
        log.warning("record_processed(%s) failed: %s", artifact_id, e)


def finish(objects: Sequence[bpy.types.Object], landmark_id: str, bins: Sequence[int], extras: dict, *, lod: int = 0,
           budget_tris: int | None = None, sources: Sequence[str] = ()) -> dict:
    """Export ``objects`` to ``blender_out/landmarks/<id>.glb`` (``<id>_lod1.glb`` for lod=1) and merge the catalog
    entry.  ``extras`` must contain origin_tm, heading_deg, height_m, fidelity_statement; DATA_CONTRACTS §11 fields
    (name, lp_number, footprint_source, height_source, notes) are filled from ``C_LANDMARKS`` when absent."""
    required = ("origin_tm", "heading_deg", "height_m", "fidelity_statement")
    missing = [k for k in required if k not in extras]
    if missing:
        raise ValueError(f"finish({landmark_id}): extras missing {missing}")
    objects = [o for o in objects if o is not None and o.type == "MESH"]
    if not objects:
        raise ValueError(f"finish({landmark_id}): no mesh objects")
    reg = C_LANDMARKS.get(landmark_id, {})
    if budget_tris is None:
        budget_tris = reg.get("budget", BUDGET_TRIS) if lod == 0 else max(20_000, reg.get("budget", BUDGET_TRIS) // 10)
    tris = tri_count(objects)
    if tris > budget_tris:
        raise RuntimeError(f"{landmark_id} LOD{lod}: {tris:,} triangles exceeds budget {budget_tris:,}")
    bounds = nb.bounds_of(objects)
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / (f"{landmark_id}.glb" if lod == 0 else f"{landmark_id}_lod{lod}.glb")
    glb_extras = {"landmark_id": landmark_id, "bins": [int(b) for b in bins], "lod": lod, "triangles": tris, "bounds": bounds,
                  "fidelity_bits": FIDELITY_LANDMARK_MODEL, "agent": AGENT, **extras}
    nb.export_glb(path, objects=objects, extras=glb_extras)
    from nycsim_pipeline.manifest import sha256_of
    mats = sorted({sl.material.name for o in objects for sl in o.material_slots if sl.material})
    rec = {"path": _rel(path), "triangles": tris, "bytes": path.stat().st_size, "bounds": bounds, "sha256": sha256_of(path),
           "objects": len(objects), "materials": mats}
    CATALOG.mkdir(parents=True, exist_ok=True)
    cpath = CATALOG / f"{landmark_id}.json"
    entry = json.load(open(cpath)) if cpath.exists() else {"id": landmark_id, "schema_version": 1}
    entry.update({"id": landmark_id, "bins": [int(b) for b in bins], "script": f"blender/landmarks/{reg.get('script', landmark_id)}.py", "agent": AGENT,
                  "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
    entry.setdefault("name", reg.get("name", landmark_id))
    entry.setdefault("lp_number", reg.get("lp_number", ""))
    entry.setdefault("height_source", reg.get("height_source", ""))
    entry.setdefault("footprint_source", "NYC Building Footprints (OTI, 5zhs-2jue) via data/processed/landmarks/candidate_footprints.parquet / footprints_raw.parquet" if bins
                     else "no building footprint (positioned by WGS84 coordinate / OSM way)")
    entry.setdefault("notes", "")
    for k, v in extras.items():
        entry[k] = v
    entry.setdefault("lods", {})[f"lod{lod}"] = rec
    entry["screens"] = sorted({m for m in mats if m.startswith("TSQ_SCREEN_")})
    entry["textures_used"] = sorted({o.material_slots[i].material["nycsim_material"] for o in objects for i in range(len(o.material_slots))
                                     if o.material_slots[i].material and o.material_slots[i].material.get("nycsim_textured")})
    nb.write_catalog_entry(CATALOG, entry)
    _record_processed(f"landmark_{landmark_id}_lod{lod}", path, list(sources) or ["building_footprints", "osm_bbbike"],
                      {"landmark_id": landmark_id, "lod": lod, "triangles": tris})
    log.info("%s LOD%d: %d tris, %d objects, %.2f MB -> %s", landmark_id, lod, tris, len(objects), path.stat().st_size / 1e6, path)
    return rec


def render_check(landmark_id: str, view: str, camera_location, camera_target, *, fov_deg: float = 50.0, size=(1280, 720), samples: int = 64,
                 sun_azimuth_deg: float = 220.0, sun_elevation_deg: float = 35.0, ground: tuple[str, float, float] | None = ("pavers_grey", 0.0, 400.0)) -> Path:
    """Cycles CPU still into docs/verification/landmarks/<id>/<view>.png.  ``ground`` = (material, z, half-size) adds a
    temporary ground plane."""
    out_dir = VERIFY / landmark_id
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{view}.png"
    tmp = []
    if ground is not None:
        gname, gz, half = ground
        g = MB("_ctx_ground")
        g.quad((-half, -half, gz), (half, -half, gz), (half, half, gz), (-half, half, gz), gname)
        tmp.append(g.build())
    try:
        nb.quick_render(path, camera_location=camera_location, camera_target=camera_target, fov_deg=fov_deg, size=size, samples=samples,
                        sun_azimuth_deg=sun_azimuth_deg, sun_elevation_deg=sun_elevation_deg)
    finally:
        for o in tmp:
            me = o.data
            bpy.data.objects.remove(o)
            bpy.data.meshes.remove(me)
        for name in ("verify_cam", "verify_sun"):
            o = bpy.data.objects.get(name)
            if o is not None:
                bpy.data.objects.remove(o)
    if not path.exists() or path.stat().st_size < 1000:
        raise RuntimeError(f"render failed: {path}")
    log.info("render %s/%s -> %s", landmark_id, view, path)
    return path


def write_report(landmark_id: str, title: str, sections: dict[str, str], lods: dict, renders: Sequence[Path] = ()) -> Path:
    """Per-landmark REPORT.md under docs/verification/landmarks/<id>/ (dimensions + sources, fidelity statement,
    polycounts, renders)."""
    d = VERIFY / landmark_id
    d.mkdir(parents=True, exist_ok=True)
    reg = C_LANDMARKS.get(landmark_id, {})
    lines = [f"# {title}", "",
             f"Script: `blender/landmarks/{reg.get('script', landmark_id)}.py` · agent C · generated {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())}", ""]
    if reg:
        lines += [f"* BIN(s): {', '.join(str(b) for b in reg.get('bins', [])) or 'none (no footprint)'}",
                  f"* Height used: **{reg['height_m']} m** — {reg.get('height_source', '')}",
                  f"* LPC: {reg.get('lp_number') or '—'}", ""]
    for h, body in sections.items():
        lines += [f"## {h}", "", body.strip(), ""]
    lines += ["## Polycounts / outputs", ""]
    for k, v in sorted(lods.items()):
        lines.append(f"* `{v['path']}` — {v['triangles']:,} triangles, {v['bytes'] / 1e6:.2f} MB, bounds min {['%.1f' % c for c in v['bounds']['min']]} "
                     f"max {['%.1f' % c for c in v['bounds']['max']]}; materials: {', '.join(v.get('materials', []))}")
    lines.append("")
    ts = texture_status()
    if ts:
        lines += ["## Textures", ""] + [f"* {k}: {v}" for k, v in sorted(ts.items())] + [""]
    if renders:
        lines += ["## Verification renders (Cycles CPU)", ""]
        for r in renders:
            lines.append(f"![{Path(r).stem}]({Path(r).name})")
        lines.append("")
    p = d / "REPORT.md"
    p.write_text("\n".join(lines))
    return p


def cli_args(argv: Sequence[str] | None = None) -> dict:
    """Common CLI: --no-render, --lod0-only, --samples N, --only <sub-id> (multi-building scripts)."""
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-render", action="store_true")
    ap.add_argument("--lod0-only", action="store_true")
    ap.add_argument("--samples", type=int, default=64)
    ap.add_argument("--only", default=None)
    a, _ = ap.parse_known_args(argv if argv is not None else sys.argv[1:])
    return vars(a)


def context_shells(frame: LocalFrame, radius: float, *, exclude_bins: Iterable[int] = (), min_height: float = 6.0, material: str = "concrete",
                   name: str = "_ctx_shells") -> bpy.types.Object | None:
    """Grey extruded footprints (real polygons, real LiDAR heights) around a frame for verification renders only —
    never exported.  Excludes the landmark's own BINs."""
    fps = footprints_in_bbox(frame.x - radius, frame.y - radius, frame.x + radius, frame.y + radius, min_height=min_height, exclude_bins=exclude_bins)
    if not fps:
        return None
    mb = MB(name)
    for fp in fps:
        for ring in fp.rings():
            if len(ring) < 3:
                continue
            try:
                ring = simplify_ring(frame.ring_local(ring), 0.25)
                z0 = fp.ground_z - frame.z
                mb.prism(ring, z0 - 0.5, z0 + max(fp.height, 3.0), material, "roof_grey")
            except Exception as e:  # a few OTI polygons are self-intersecting; skip those in a render-only helper
                log.debug("context shell %s skipped: %s", fp.bin, e)
    return mb.build()
