"""Shared helpers for the *C* landmark scripts (Hudson Yards, Billionaires' Row, Times Square, museums, cultural
buildings, stadiums, outer-borough icons).

**Adopted module:** every C script builds with ``blender/landmarks/common.py`` (agent A) — its ``MeshBuilder``,
``Fenestration``/``tower_tier``/``facade_grid``/``cornice``/``lathe``/``loft``/``column`` builders, its documented
``PALETTE``, and its ``finish``/``render_check`` verification path (footprint IoU > 0.9 at z = 1.5 m on objects tagged
``role="base"``, model height within 1 % of the published height, LOD0 triangle budget, ``<id>_LOD1`` <= 20 % of LOD0).
This module adds only what is specific to lane C and does **not** duplicate any of it:

* :data:`SCRIPTS` — the registry of C landmarks: BINs, published heights and the source of each height. The tests read it.
* :func:`load_bins` / :func:`group` — a working footprint reader.  ``common.load_footprints`` cannot be used as of
  commit-time: it reads ``data/processed/buildings/landmark_footprints.parquet`` first and filters on a ``bin`` column,
  but that file is keyed ``landmark_id``/``bins`` (list) and has no ``bin`` column, so pyarrow raises
  ``ArrowInvalid: No match for FieldRef.Name(bin)`` for *every* key.  Reported to the orchestrator; until it is fixed
  the C scripts read ``candidate_footprints.parquet`` (BIN-keyed, 2,705 rows) and fall back to a pyarrow row-filtered
  read of ``footprints_raw.parquet`` — never a whole-file geopandas load.  ``common.finish`` is therefore always
  called with an explicit ``real_footprint=``.
* :func:`materials` — names the palette materials a script uses in one place and reports where each one's PBR maps
  came from.  Texture resolution itself is agent A's: ``common.mat`` looks the name up in ``common.TEXTURE_NAMES``,
  asks ``blender/common/textures.py`` for the CC0 set, tiles it in metres over the box-projected UVs that
  ``MeshBuilder.build`` writes, and tints the colour map back to the documented ``PALETTE`` albedo.
* :func:`curtain` / :func:`band_ring` — an economical modern curtain wall (glass volume, a protruding spandrel band
  at every floor line, vertical mullions on a module) for the towers whose facades would otherwise cost >100k
  triangles as modelled openings, and :func:`base_and_wall` — a ground-floor volume built so that recessed openings
  are not buried inside a flush solid.
* :func:`screen` — Times Square video slots: emissive materials named ``TSQ_SCREEN_<n>`` on quads with 0..1 UVs, one
  UV island per screen, so the engine can bind a video texture per slot.
* :func:`finish` / :func:`render` — thin wrappers that fill in the lane-C defaults and the registry metadata.
"""
from __future__ import annotations

import logging
import math
import os
import sys
from pathlib import Path
from typing import Iterable, Sequence

_HERE = Path(__file__).resolve()
sys.path.insert(0, str(_HERE.parent))
sys.path.insert(0, str(_HERE.parents[1] / "common"))

import numpy as np  # noqa: E402
import bpy  # noqa: E402
import shapely  # noqa: E402
import shapely.ops  # noqa: E402
from shapely import wkb as _wkb  # noqa: E402
from shapely.geometry import MultiPolygon, Polygon  # noqa: E402
from shapely.geometry.polygon import orient as _orient  # noqa: E402

import common as C  # noqa: E402  (agent A — adopted)
import nycsim_bpy as nb  # noqa: E402

log = logging.getLogger("nycsim.landmarks.c")

REPO = C.REPO_ROOT
CANDIDATES = C.CANDIDATES_PARQUET
RAW = C.FOOTPRINTS_RAW_PARQUET
OUT = C.OUT_DIR
VERIFY = C.VERIFY_DIR
BUDGET = C.TRI_BUDGET_LOD0                 # 250 000 (brief)
BUDGET_LARGE = 400_000                     # Vessel, Guggenheim, High Line (brief)
AGENT = "C"

# Manhattan commissioners' grid: the avenues run N 28.9 deg E, so the cross-streets run at compass 118.9 deg, i.e.
# -28.9 deg from east in the math convention used by ``common.LocalFrame.angle_deg``.
GRID_ANGLE = -28.9

# ------------------------------------------------------------------------------------------------------- registry
# id -> {name, bins, height_m (published architectural height the model must reach), height_source, lp_number,
#        budget, parts: [{name, bins, height_m, height_source}, ...]}.  ``tests/test_landmarks_c.py`` checks the
# exported glb bounding box against ``height_m`` (+-1 %) and the catalog entry against these fields.
SCRIPTS: dict[str, dict] = {
    "c_hudson_yards": dict(
        name="Hudson Yards (Eastern Yard)", height_m=387.1,
        height_source="30 Hudson Yards, KPF/CTBUH: 1,270 ft = 387.1 m architectural (tallest of the group)",
        bins=[1088961, 1089323, 1091590, 1089412, 1089411, 1090274, 1090391],
        parts=[
            dict(id="30_hudson_yards", name="30 Hudson Yards", bins=[1088961], height_m=387.1,
                 height_source="KPF / CTBUH: 1,270 ft (387.1 m) architectural; Edge observation deck 1,131 ft (345 m), cantilever 65 ft (20 m)"),
            dict(id="35_hudson_yards", name="35 Hudson Yards", bins=[1091590], height_m=308.0,
                 height_source="SOM / CTBUH: 1,009 ft (308.0 m), 72 floors"),
            dict(id="10_hudson_yards", name="10 Hudson Yards", bins=[1089323], height_m=272.8,
                 height_source="KPF / CTBUH: 895 ft (272.8 m), 52 floors"),
            dict(id="55_hudson_yards", name="55 Hudson Yards", bins=[1089412], height_m=237.4,
                 height_source="KPF + Kohn Pedersen Fox / CTBUH: 780 ft (237.4 m), 51 floors (LiDAR 24.4 m = 2015 flight, pre-construction)"),
            dict(id="15_hudson_yards", name="15 Hudson Yards", bins=[1089411], height_m=278.6,
                 height_source="Diller Scofidio + Renfro / Rockwell / CTBUH: 914 ft (278.6 m), 88 floors"),
            dict(id="50_hudson_yards", name="50 Hudson Yards", bins=[1090274], height_m=308.2,
                 height_source="Foster + Partners / CTBUH: 1,011 ft (308.2 m), 58 floors"),
            dict(id="the_shed", name="The Shed (Bloomberg Building)", bins=[1089411], height_m=36.6,
                 height_source="Diller Scofidio + Renfro: fixed building 8 storeys; movable ETFE shell 120 ft (36.6 m) tall, 120 ft span, 273 ft travel on 8 double-wheel bogies"),
            dict(id="vessel", name="Vessel", bins=[1090391], height_m=46.0,
                 height_source="Heatherwick Studio: 150 ft (46 m) tall, 50 ft base widening to 150 ft at the top; 154 flights, 2,500 steps, 80 landings"),
        ]),
    "c_billionaires_row": dict(
        name="Billionaires' Row (West 57th Street corridor)", height_m=472.4,
        height_source="Central Park Tower, AS+GG/CTBUH: 1,550 ft = 472.4 m (tallest of the group)",
        bins=[1088817, 1035787, 1023728, 1090180, 1088565, 1090184, 1090777, 1035794, 1035071],
        parts=[
            dict(id="432_park_avenue", name="432 Park Avenue", bins=[1088817, 1035787], height_m=425.5,
                 height_source="Rafael Vinoly / CTBUH: 1,396 ft (425.5 m), 85 floors; 93.5 ft (28.5 m) square tube, 6x6 grid of 10 ft (3.05 m) square windows; open double-height mechanical floors at 12/13, 30/31, 48/49, 66/67, 84/85"),
            dict(id="111_west_57th", name="111 West 57th Street (Steinway Tower) + Steinway Hall", bins=[1023728], height_m=435.3,
                 height_source="SHoP / CTBUH: 1,428 ft (435.3 m), 84 floors; 60 ft (18.3 m) wide east-west, 24:1 slenderness; feathered terracotta setbacks on the east face; Steinway Hall (Warren & Wetmore 1925, LP-2100) 16 storeys"),
            dict(id="central_park_tower", name="Central Park Tower", bins=[1090180], height_m=472.4,
                 height_source="Adrian Smith + Gordon Gill / CTBUH: 1,550 ft (472.4 m), 98 floors; cantilevers 28 ft (8.5 m) east over Art Students League from floor 30 (~91 m)"),
            dict(id="one57", name="One57", bins=[1088565], height_m=306.1,
                 height_source="Christian de Portzamparc / CTBUH: 1,004 ft (306.1 m), 75 floors"),
            dict(id="220_central_park_south", name="220 Central Park South", bins=[1090184], height_m=290.2,
                 height_source="Robert A.M. Stern / CTBUH: 952 ft (290.2 m), 70 floors; Alabama limestone cladding, 18-storey 'Villa' on the CPS frontage"),
            dict(id="53w53", name="53 West 53rd (MoMA Expansion Tower)", bins=[1090777], height_m=320.0,
                 height_source="Jean Nouvel / CTBUH: 1,050 ft (320.0 m), 77 floors; exposed diagonal concrete exoskeleton"),
            dict(id="trump_tower", name="Trump Tower", bins=[1035794], height_m=202.0,
                 height_source="Der Scutt / Swanke Hayden Connell / CTBUH: 664 ft (202.0 m), 58 storeys marketed (68 numbered); 28 sawtooth bay setbacks"),
            dict(id="solow_building", name="Solow Building (9 West 57th Street)", bins=[1035071], height_m=210.0,
                 height_source="SOM (Gordon Bunshaft) / CTBUH: 689 ft (210.0 m), 50 floors; swooping concave north and south facades"),
        ]),
    "c_times_square": dict(
        name="Times Square", height_m=365.8,
        height_source="Bank of America Tower, Cook+Fox/CTBUH: 1,200 ft = 365.8 m to spire (tallest of the group)",
        bins=[1022581, 1024742, 1024686, 1085682, 1085493, 1024706, 1085637, 1090950, 1086069, 1087268, 1024727,
              1087186, 1083268],
        parts=[
            dict(id="one_times_square", name="One Times Square", bins=[1022581], height_m=141.0,
                 height_source="Cyrus Eidlitz 1904: roof 363 ft (110.7 m); the 1999 flagpole/ball mast reaches ~463 ft (141 m). The 12 ft (3.66 m) geodesic ball travels 141 ft (43 m) down the pole in 60 s"),
            dict(id="two_times_square", name="Two Times Square", bins=[1024742], height_m=160.6,
                 height_source="No published architectural height; LiDAR roof (incl. the sign tower) 160.6 m — flagged inferred"),
            dict(id="three_times_square", name="3 Times Square (Thomson Reuters Building)", bins=[1024686], height_m=169.2,
                 height_source="Fox & Fowle 2001: 30 floors; OSM height 169.2 m to the top of the mast (LiDAR main roof 148.9 m)"),
            dict(id="four_times_square", name="4 Times Square (Conde Nast Building)", bins=[1085682], height_m=247.0,
                 height_source="Fox & Fowle / CTBUH: 809 ft (247.0 m) to roof, 48 floors (the 1,118 ft broadcast antenna is not structure)"),
            dict(id="tsx_broadway", name="TSX Broadway (1568 Broadway) + Palace Theatre", bins=[1085493], height_m=158.0,
                 height_source="PBDW / Perkins Eastman 2023: 46 floors, 518 ft (158.0 m); the 1913 Palace Theatre was lifted 30 ft (9.1 m) in 2022"),
            dict(id="paramount_building", name="Paramount Building (1501 Broadway)", bins=[1024706], height_m=128.3,
                 height_source="Rapp & Rapp 1927: 33 floors, 420 ft (128.0 m) to the top of the glass globe; LiDAR 128.3 m; four 25 ft (7.6 m) clock faces"),
            dict(id="tkts_duffy_square", name="TKTS booth and red steps, Father Duffy Square", bins=[1085637, 1090950], height_m=8.2,
                 height_source="Choi Ropiha / Perkins Eastman 2008: 27 red laminated-glass steps rising 16 ft (4.9 m); Father Duffy memorial cross/flagpole to 8.2 m"),
            dict(id="times_square_tower", name="Times Square Tower (7 Times Square)", bins=[1086069], height_m=221.0,
                 height_source="SOM / CTBUH: 726 ft (221.0 m), 47 floors"),
            dict(id="bank_of_america_tower", name="Bank of America Tower (One Bryant Park)", bins=[1087268], height_m=365.8,
                 height_source="Cook+Fox / CTBUH: 1,200 ft (365.8 m) to spire tip, roof 945 ft (288.0 m), 55 floors"),
            dict(id="marriott_marquis", name="New York Marriott Marquis", bins=[1024727], height_m=176.0,
                 height_source="John Portman 1985: 49 floors, 574 ft (175.0 m); LiDAR 176.0 m; 37-storey atrium"),
            dict(id="new_york_times_building", name="The New York Times Building", bins=[1087186], height_m=318.8,
                 height_source="Renzo Piano / FXFOWLE / CTBUH: 1,046 ft (318.8 m) to mast, roof 748 ft (228.0 m), 52 floors; 186,000 white ceramic rods on 5 in (127 mm) centres screening the curtain wall"),
            dict(id="port_authority_bus_terminal", name="Port Authority Bus Terminal", bins=[1083268], height_m=38.6,
                 height_source="1950 / 1979 north wing; OSM height 38.6 m (LiDAR main roof 31.4 m, ramp helix above)"),
        ]),
    "c_hearst_tower": dict(name="Hearst Tower", bins=[1025451], height_m=182.0, lp_number="LP-1974",
                           height_source="Foster + Partners 2006 / CTBUH: 597 ft (182.0 m), 46 floors; diagrid on a 4-storey triangular module; 1928 Joseph Urban base 6 storeys, 40 m"),
    "c_citigroup_center": dict(name="Citigroup Center (601 Lexington Avenue)", bins=[1036474], height_m=278.9,
                               height_source="Hugh Stubbins & Emery Roth 1977 / CTBUH: 915 ft (278.9 m), 59 floors; 45 deg roof; four 114 ft (34.7 m) mid-face stilts"),
    "c_metlife_building": dict(name="MetLife Building (200 Park Avenue)", bins=[1085630], height_m=246.3,
                               height_source="Emery Roth & Sons / Gropius / Belluschi 1963 / CTBUH: 808 ft (246.3 m), 59 floors; precast concrete facade"),
    "c_lipstick_building": dict(name="Lipstick Building (885 Third Avenue)", bins=[1038549], height_m=138.0,
                                height_source="Philip Johnson & John Burgee 1986 / CTBUH: 453 ft (138.0 m), 34 floors; three elliptical telescoping tiers"),
    "c_seagram_building": dict(name="Seagram Building", bins=[1036465], height_m=157.0, lp_number="LP-1664",
                               height_source="Mies van der Rohe & Philip Johnson 1958 / CTBUH: 515 ft (157.0 m), 38 floors; 90 ft (27.4 m) deep granite plaza"),
    "c_lever_house": dict(name="Lever House", bins=[1035732], height_m=94.0, lp_number="LP-1277",
                          height_source="SOM (Gordon Bunshaft) 1952 / CTBUH: 307 ft (94.0 m), 24 floors; 21-storey slab on a one-storey podium raised on columns"),
    "c_un_headquarters": dict(name="United Nations Headquarters", bins=[1083875, 1083872, 1083874], height_m=154.0,
                              height_source="Harrison/Niemeyer/Le Corbusier 1952: Secretariat 505 ft (154.0 m), 39 floors, 287 x 72 ft slab"),
    "c_the_dakota": dict(name="The Dakota", bins=[1028637], height_m=50.9, lp_number="LP-0280",
                         height_source="Henry J. Hardenbergh 1884: 9 storeys with gables and dormers; LiDAR ridge 50.9 m"),
    "c_the_plaza": dict(name="The Plaza Hotel", bins=[1035253], height_m=76.2, lp_number="LP-0629",
                        height_source="Henry J. Hardenbergh 1907: 19 floors, 250 ft (76.2 m) to the roof ridge; mansard roof"),
    "c_metropolitan_museum": dict(name="The Metropolitan Museum of Art", bins=[1083810], height_m=42.0, lp_number="LP-0955",
                                  height_source="Richard Morris Hunt / McKim Mead & White Fifth Avenue facade 1902-26: central pavilion 138 ft (42.0 m); wings' attic cornice ~33 m"),
    "c_guggenheim": dict(name="Solomon R. Guggenheim Museum", bins=[1046946, 1046964], height_m=41.6, lp_number="LP-1774",
                         height_source="Frank Lloyd Wright 1959: rotunda 92 ft (28.0 m) to the skylight oculus; Gwathmey Siegel 1992 annex 10 storeys, LiDAR 41.6 m"),
    "c_american_museum_natural_history": dict(name="American Museum of Natural History + Rose Center", bins=[1083846, 1090575],
                                              height_m=44.8, lp_number="LP-0946",
                                              height_source="Trowbridge & Livingston 1936 Roosevelt Memorial: 4 Ionic columns 60 ft; Polshek 2000 Rose Center cube 95 ft (29.0 m) glass, Hayden Sphere 87 ft (26.5 m) diameter; LiDAR 44.8 m"),
    "c_lincoln_center": dict(name="Lincoln Center for the Performing Arts", bins=[1081022, 1081023, 1028831], height_m=37.7,
                             height_source="Wallace Harrison 1966 Metropolitan Opera House: five travertine arches 96 ft (29.3 m); LiDAR fly-tower roof 37.7 m"),
    "c_apollo_theater": dict(name="Apollo Theater", bins=[1058654], height_m=20.0, lp_number="LP-1268",
                             height_source="George Keister 1914 (Hurtig & Seamon's New Burlesque Theater): neo-classical facade ~65 ft (20.0 m); 1940 vertical blade sign"),
    "c_carnegie_hall": dict(name="Carnegie Hall", bins=[1023449], height_m=55.2, lp_number="LP-0278",
                            height_source="William Burnet Tuthill 1891: 6-storey Roman-brick block plus the 1894/1897 studio tower; LiDAR 55.2 m"),
    "c_st_john_the_divine": dict(name="Cathedral Church of St. John the Divine", bins=[1082706], height_m=71.0, lp_number="LP-2585",
                                 height_source="Heins & LaFarge / Cram & Ferguson: nave vault 124 ft, ridge 177 ft (54.0 m); unfinished crossing tower 232 ft (70.7 m); 601 ft (183 m) long"),
    "c_riverside_church": dict(name="Riverside Church", bins=[1081792, 1081791], height_m=120.1, lp_number="LP-2037",
                               height_source="Allen & Collens / Henry C. Pelton 1930: tower 392 ft (119.5 m), 24 storeys; Laura Spelman Rockefeller Carillon (74 bells); OSM 120.1 m"),
    "c_yankee_stadium": dict(name="Yankee Stadium", bins=[2114490], height_m=42.0,
                             height_source="Populous 2009: limestone/granite exterior, frieze at the top of the upper deck ~138 ft (42.0 m); field 318 ft LF / 408 ft CF / 314 ft RF; 47,309 seats"),
    "c_citi_field": dict(name="Citi Field", bins=[4536844], height_m=39.0,
                         height_source="Populous 2009: Jackie Robinson Rotunda 60 ft (18.3 m) brick-and-limestone arcade; upper-deck roof ~128 ft (39.0 m); field 335 ft LF / 408 ft CF / 330 ft RF; 41,922 seats"),
    "c_barclays_center": dict(name="Barclays Center", bins=[3398156], height_m=42.1,
                              height_source="SHoP / Ellerbe Becket 2012: 137 ft (41.8 m); 12,000 weathering-steel panels in three bands; 30 ft (9.1 m) oculus canopy cantilevering 82 ft over the plaza; LiDAR 42.1 m"),
    "c_usta_arthur_ashe": dict(name="Arthur Ashe Stadium", bins=[4467715], height_m=46.0,
                               height_source="Rossetti 1997, retractable roof 2016: 23,771 seats, 8 exterior columns carrying a 6,500 t roof; overall ~150 ft (46.0 m) — scaled from Rossetti published sections, flagged inferred"),
    "c_domino_sugar_refinery": dict(name="Domino Sugar Refinery and Domino Park", bins=[3335796], height_m=60.0, lp_number="LP-2268",
                                    height_source="Havemeyers & Elder 1882-84 Filter/Pan/Finishing House: brick to 155 ft (47.2 m); PAU 2023 glass barrel vault to ~200 ft (60.0 m); Domino Park (JCFO 2018) 5 acres, 450 ft syrup-tank walk"),
    "c_kings_theatre": dict(name="Kings Theatre (Loew's Kings)", bins=[3117845], height_m=25.2, lp_number="LP-2213",
                            height_source="Rapp & Rapp 1929: 3,200-seat French Baroque movie palace; LiDAR fly tower 25.2 m"),
    "c_brooklyn_museum": dict(name="Brooklyn Museum", bins=[3029667], height_m=50.0, lp_number="LP-0057",
                              height_source="McKim, Mead & White 1897-1927 Beaux-Arts block: 5 storeys, Ionic portico, dome; LiDAR/OSM 50.0 m"),
    "c_brooklyn_public_library": dict(name="Brooklyn Public Library, Central Library", bins=[3029665], height_m=29.3, lp_number="LP-1972",
                                      height_source="Githens & Keally 1941: 50 ft (15.2 m) gilded bronze entrance screen; LiDAR 29.3 m"),
    "c_williamsburgh_savings_bank_tower": dict(name="Williamsburgh Savings Bank Tower (One Hanson Place)", bins=[3059183],
                                               height_m=156.0, lp_number="LP-0973",
                                               height_source="Halsey, McCormack & Helmer 1929: 512 ft (156.0 m), 37 floors; four 27 ft (8.2 m) clock faces; gilded dome"),
    "c_pier_17_seaport": dict(name="Pier 17, South Street Seaport", bins=[1090548], height_m=20.7,
                              height_source="SHoP 2018: 4 storeys, 1.5-acre rooftop; LiDAR 20.7 m"),
    "c_whitehall_and_st_george_ferry_terminals": dict(name="Whitehall, Battery Maritime and St. George ferry terminals",
                                                      bins=[1085792, 1000003, 5141706], height_m=27.7, lp_number="LP-0102",
                                                      height_source="Frederic Schwartz 2005 Whitehall Terminal: 75 ft (22.9 m) glass wall, LiDAR 27.7 m; Battery Maritime Building (Walker & Morris 1909, LP-0102) cast-iron Beaux-Arts, LiDAR 21.6 m; HOK 2005 St. George Terminal, LiDAR 18.5 m"),
    "c_flushing_meadows": dict(name="New York State Pavilion and Queens Museum", bins=[4464054, 4541449, 4464056, 4458851],
                               height_m=69.0, lp_number="LP-2318",
                               height_source="Philip Johnson & Lev Zetlin 1964: three observation towers 60 / 150 / 226 ft (18.3 / 45.7 / 68.9 m); Tent of Tomorrow 16 columns 100 ft (30.5 m), 350 x 250 ft cable roof; Queens Museum (1939 NYC Building) 2013 Grimshaw"),
    "c_bronx_county_courthouse": dict(name="Bronx County Courthouse (Mario Merola Building)", bins=[2002869], height_m=58.5,
                                      lp_number="LP-1027",
                                      height_source="Joseph H. Freedlander & Max Hausle 1934: 9 storeys of Mohegan granite on a full-block base, limestone friezes; LiDAR 58.5 m"),
    "c_high_line": dict(name="The High Line", bins=[], height_m=10.21,
                        height_source="Friends of the High Line: 1.45 mi (2.33 km) Gansevoort St to W 34th St; deck 30 ft (9.14 m) above the street, 30-60 ft (9-18 m) wide, built 1929-34 for the West Side Improvement. The model's highest point is the top of the code-required 42 in (1.07 m) railing on that deck: 9.14 + 1.07 = 10.21 m"),
    "c_little_island": dict(name="Little Island (Pier 55)", bins=[], height_m=18.9,
                            height_source="Heatherwick Studio / MNLA 2021: 2.4 acres on 132 precast 'tulip' pots on 267 piles; deck 15-62 ft (4.6-18.9 m) above the Hudson"),
    "c_pier_57": dict(name="Pier 57", bins=[1012253], height_m=19.3,
                      height_source="Emil H. Praeger 1954 (LP-2450): 3 storeys on three floating concrete caissons, 850 x 165 ft; 2022 rooftop park; LiDAR 19.3 m"),
    "c_chelsea_market": dict(name="Chelsea Market (National Biscuit Company complex)", bins=[1012541], height_m=37.7,
                             height_source="Romeyn & Stever / Nabisco 1890-1932: up to 11 storeys of red brick over a full block; LiDAR 37.7 m"),
    "c_javits_center": dict(name="Jacob K. Javits Convention Center", bins=[1067973, 1089474], height_m=53.6,
                            height_source="I. M. Pei / James Ingo Freed 1986: space-frame 'crystal palace' on a 90 ft (27.4 m) grid, Crystal Palace lobby 150 ft (45.7 m); 2021 Tod Williams Billie Tsien expansion; LiDAR 53.6 m"),
    "c_moynihan_train_hall": dict(name="Moynihan Train Hall (James A. Farley Building)", bins=[1084820], height_m=31.2,
                                  lp_number="LP-0233",
                                  height_source="McKim, Mead & White 1913: 8th Avenue colonnade of 20 Corinthian columns 53 ft (16.2 m); SOM 2021 train hall skylight 92 ft (28.0 m) above the floor; LiDAR cornice/attic 31.2 m"),
}
for _k, _v in SCRIPTS.items():
    _v.setdefault("lp_number", "")
    _v.setdefault("parts", [])
    _v.setdefault("budget", BUDGET_LARGE if _k in ("c_high_line", "c_guggenheim") else BUDGET)
SCRIPTS["c_hudson_yards"]["budget"] = BUDGET_LARGE          # the Vessel's 154 flights (brief)


# ------------------------------------------------------------------------------------------------------ footprints
_FP_COLS = ["bin", "name", "height", "ground_z", "cx", "cy", "geometry", "construction_year", "shape_area"]


def load_bins(bins: Sequence[int]) -> dict[int, C.Footprint]:
    """``{BIN: common.Footprint}`` read from candidate_footprints.parquet, then footprints_raw.parquet (row-filtered)."""
    import pyarrow.parquet as pq
    want = [int(b) for b in bins]
    found: dict[int, C.Footprint] = {}
    for path in (CANDIDATES, RAW):
        missing = [b for b in want if b not in found]
        if not missing or not path.exists():
            continue
        tbl = pq.read_table(path, columns=_FP_COLS, filters=[("bin", "in", missing)])
        for r in tbl.to_pylist():
            b = int(r["bin"])
            if b in found:
                continue
            geom = _wkb.loads(r["geometry"]) if isinstance(r["geometry"], (bytes, bytearray)) else shapely.from_wkb(r["geometry"])
            poly = C._clean_polygon(geom)
            gz = r.get("ground_z")
            gz = float(gz) if gz is not None and not (isinstance(gz, float) and math.isnan(gz)) else math.nan
            h = r.get("height")
            h = float(h) if h is not None and not (isinstance(h, float) and math.isnan(h)) else 0.0
            cx, cy = r.get("cx"), r.get("cy")
            if cx is None or cy is None:
                cx, cy = poly.centroid.x, poly.centroid.y
            yr = r.get("construction_year")
            found[b] = C.Footprint(poly, gz, h, (float(cx), float(cy)), b, str(r.get("name") or ""), path.name,
                                   int(yr) if yr not in (None, 0) else None)
    missing = [b for b in want if b not in found]
    if missing:
        raise KeyError(f"BIN(s) {missing} not in {CANDIDATES.name} or {RAW.name}")
    return found


def ground_of(fps: Iterable[C.Footprint]) -> float:
    """Mean LiDAR ground elevation of the given footprints (NaN entries dropped; 0.0 if all are NaN)."""
    zs = [f.ground_z for f in fps if not math.isnan(f.ground_z)]
    return float(sum(zs) / len(zs)) if zs else 0.0


class Group:
    """The footprints of one script, plus the local frame and the local polygons the IoU check uses."""

    def __init__(self, script_id: str, *, angle_deg: float | None = None, origin_bin: int | None = None,
                 ground_z: float | None = None, extra_bins: Sequence[int] = ()):
        self.id = script_id
        self.meta = SCRIPTS[script_id]
        self.bins = [int(b) for b in self.meta["bins"]] + [int(b) for b in extra_bins]
        self.fp = load_bins(self.bins) if self.bins else {}
        fps = list(self.fp.values())
        self.ground_z = ground_of(fps) if ground_z is None else float(ground_z)
        if fps:
            union = shapely.ops.unary_union([f.polygon for f in fps])
            c = (self.fp[origin_bin].polygon if origin_bin else union).centroid
            base_poly = self.fp[origin_bin].polygon if origin_bin else union
            ang = C.principal_angle_deg(base_poly) if angle_deg is None else float(angle_deg)
            self.frame = C.LocalFrame((float(round(c.x)), float(round(c.y)), self.ground_z), ang)
            self.real_local = shapely.ops.unary_union([self.frame.local_polygon(f.polygon) for f in fps])
        else:
            self.frame = None
            self.real_local = None

    def poly(self, b: int) -> Polygon:
        """Local-frame polygon of one BIN."""
        return self.frame.local_polygon(self.fp[int(b)].polygon)

    def z0(self, b: int) -> float:
        """Local z of that BIN's own LiDAR ground (0 = the group's mean ground)."""
        g = self.fp[int(b)].ground_z
        return 0.0 if math.isnan(g) else float(g) - self.ground_z


def frame_at(x: float, y: float, ground_z: float = 0.0, angle_deg: float = 0.0) -> C.LocalFrame:
    return C.LocalFrame((float(round(x)), float(round(y)), float(ground_z)), float(angle_deg))


# ------------------------------------------------------------------------------------------------------- materials
def materials(names: Sequence[str]) -> dict[str, str]:
    """Instantiate the palette materials this script uses and report where each one's PBR maps came from.

    Texture resolution is agent A's: ``common.mat`` looks the name up in ``common.TEXTURE_NAMES`` and asks
    ``blender/common/textures.py`` for the CC0 set, tiling it in metres over the box-projected UVs that
    ``MeshBuilder.build`` writes, and tinting the colour map back to the documented ``PALETTE`` albedo. This wrapper
    exists so each C script names its materials in one place and the catalog records the outcome."""
    for n in names:
        C.mat(n)
    return {n: C.texture_status().get(n, "flat Principled albedo (no texture set mapped)") for n in names}


def texture_status() -> dict[str, str]:
    return dict(C.texture_status())


# ------------------------------------------------------------------------------------------------- ground floor
def base_and_wall(name: str, poly, z_top: float, material, *, recess: float = 0.6, plinth_h: float = 1.6,
                  material_top=None, role: str = "base") -> list[bpy.types.Object]:
    """The ground-floor volume of a masonry building, built so that recessed openings actually read.

    ``common.arched_opening`` / ``window_punch`` draw a *reveal* set back from the wall line; if the wall behind is a
    solid prism flush with the footprint, that reveal is inside solid geometry and the elevation renders blank. This
    builds instead:

    * a flush plinth on the real footprint from ``z0`` to ``plinth_h`` (1.6 m) — the base course, and the volume the
      IoU check slices at 1.5 m, so the footprint agreement is unaffected;
    * the wall core above it, inset by ``recess``, so every opening drawn on the footprint line between ``plinth_h``
      and ``z_top`` is a real recess against a wall that is genuinely behind it.

    Openings on such a wall must therefore start at or above ``plinth_h``."""
    objs = [C.tag(C.prism(f"{name}_plinth", poly, 0.0, plinth_h, material), role)]
    inner = C.offset_polygon(poly, -recess)
    if inner.is_empty:
        inner = poly
    objs.append(C.tag(C.prism(f"{name}_core", inner, 0.0, z_top, material, material_top=material_top), "mass"))
    return objs


# ----------------------------------------------------------------------------------------------------- curtain wall
def band_ring(b: C.MeshBuilder, ring: Sequence[Sequence[float]], z0: float, z1: float, proud: float, material) -> None:
    """A protruding horizontal band around ``ring`` between z0 and z1 as four lofted rings (in-out-out-in).

    12 triangles per ring vertex per band, which is what keeps a 90-storey curtain wall inside the triangle budget."""
    outer = C.offset_ring(ring, proud)
    b.loft([[(x, y, z0) for x, y in ring], [(x, y, z0) for x, y in outer],
            [(x, y, z1) for x, y in outer], [(x, y, z1) for x, y in ring]],
           material, cap_top=False, cap_bottom=False)


def curtain(name: str, poly, z0: float, z1: float, *, floor_h: float, module: float = 3.0, glass: str = "glass_blue",
            mullion: str = "aluminium", spandrel: str | None = None, spandrel_h: float = 0.95, proud: float = 0.18,
            mullion_w: float = 0.20, mullion_d: float = 0.28, recess: float = 0.06, roof_material: str = "roof_dark",
            role: str = "mass", parapet_h: float = 0.0, first_floor_h: float | None = None,
            edges: Sequence[int] | None = None) -> list[bpy.types.Object]:
    """A modern glass curtain wall: a glass volume, a protruding spandrel band at every floor line and vertical
    mullions on a ``module`` grid.

    This is the economical counterpart of ``common.tower_tier``/``Fenestration`` (which models every window opening as
    solid geometry and costs ~20 triangles per window). At 90 storeys and a 220 m perimeter that would be >100k
    triangles for one tower; this builds the same read — floor lines, mullion rhythm, recessed glass — for ~3k."""
    objs: list[bpy.types.Object] = []
    core = C.prism(f"{name}_mass", poly, z0, z1, C.mat(glass), inset=recess,
                   material_top=C.mat(roof_material), role=role)
    objs.append(core)
    ring = C.ring_coords(poly)
    sp = C.mat(spandrel or mullion)
    mu = C.mat(mullion)
    b = C.MeshBuilder()
    z = z0 if first_floor_h is None else z0 + first_floor_h - floor_h
    n = 0
    while z + floor_h <= z1 + 1e-6:
        zf = z + floor_h
        band_ring(b, ring, zf - spandrel_h, zf, proud, sp)
        z = zf
        n += 1
    band_ring(b, ring, z0, z0 + min(0.7, spandrel_h), proud, sp)
    sel = set(edges) if edges is not None else None
    for i, (p0, p1, L, t, nrm) in enumerate(C.edges_of(ring)):
        if sel is not None and i not in sel:
            continue
        k = max(1, int(round(L / module)))
        for j in range(k + 1):
            q0 = p0 + t * (min(L, j * (L / k)) - mullion_w / 2)
            q1 = q0 + t * mullion_w
            b.box_from_to(q0, q1, nrm, mullion_d, z0, z1, mu, top=False, bottom=False)
    objs.append(b.build(f"{name}_skin"))
    if parapet_h > 0:
        inner = C.offset_polygon(poly, -0.35)
        pb = C.MeshBuilder()
        pb.prism(ring, z1, z1 + parapet_h, mu, holes=[C.ring_coords(inner)] if not inner.is_empty else [],
                 cap_bottom=False)
        objs.append(pb.build(f"{name}_parapet"))
    return objs


_SCREENS: dict[int, bpy.types.Material] = {}


def screen(n: int, *, color=(1.0, 1.0, 1.0), strength: float = 6.0) -> bpy.types.Material:
    """Emissive material slot ``TSQ_SCREEN_<n>`` for one Times Square video screen (engine binds a video per slot)."""
    name = f"TSQ_SCREEN_{n}"
    m = bpy.data.materials.get(name)
    if m is None:
        m = nb.pbr_material(name, base_color=(color[0], color[1], color[2], 1.0), roughness=0.35, metallic=0.0,
                            emission=(color[0], color[1], color[2], 1.0), emission_strength=strength)
        C.PALETTE.setdefault(name, ((230, 230, 235), 0.35, 0.0, color, strength, "Times Square video screen slot (emissive; UE binds a video texture, UV 0..1 per screen)"))
    _SCREENS[int(n)] = m
    return m


def screen_quad(b: C.MeshBuilder, p0, p1, normal, z0: float, z1: float, n: int, *, proud: float = 0.25,
                bezel: float = 0.25, bezel_material=None) -> None:
    """One LED screen on the wall segment p0->p1 between z0 and z1 with its own 0..1 UV island and a bezel frame.

    The face is emitted as a single quad in the order (bottom-left, bottom-right, top-right, top-left) so that the
    default glTF UV unwrap gives a rectangular island; :func:`assign_screen_uvs` then overwrites it with exact 0..1
    coordinates in that order."""
    p0 = np.asarray(p0, dtype=np.float64); p1 = np.asarray(p1, dtype=np.float64)
    nrm = np.asarray(normal, dtype=np.float64)
    q0 = p0 + nrm * proud; q1 = p1 + nrm * proud
    m = screen(n)
    b.quad((q0[0], q0[1], z0), (q1[0], q1[1], z0), (q1[0], q1[1], z1), (q0[0], q0[1], z1), m)
    if bezel > 0:
        bm = bezel_material if bezel_material is not None else C.mat("steel_dark")
        t = (p1 - p0) / max(1e-9, float(np.linalg.norm(p1 - p0)))
        b.box_from_to(p0 - t * bezel, p1 + t * bezel, nrm, proud, z0 - bezel, z0, bm)
        b.box_from_to(p0 - t * bezel, p1 + t * bezel, nrm, proud, z1, z1 + bezel, bm)
        b.box_from_to(p0 - t * bezel, p0, nrm, proud, z0, z1, bm)
        b.box_from_to(p1, p1 + t * bezel, nrm, proud, z0, z1, bm)


def assign_screen_uvs(objects: Sequence[bpy.types.Object]) -> int:
    """Give every ``TSQ_SCREEN_<n>`` face exact 0..1 UVs (u along the wall, v up). Returns the number of faces fixed."""
    fixed = 0
    for ob in objects:
        if ob is None or ob.type != "MESH":
            continue
        me = ob.data
        slots = {i: m.name for i, m in enumerate(me.materials) if m is not None and m.name.startswith("TSQ_SCREEN_")}
        if not slots:
            continue
        uv = me.uv_layers.get("UVMap") or me.uv_layers.new(name="UVMap")
        for p in me.polygons:
            if p.material_index not in slots or p.loop_total != 4:
                continue
            for k, li in enumerate(p.loop_indices):
                uv.data[li].uv = ((0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0))[k]
            fixed += 1
    return fixed


def screen_slots() -> dict[str, str]:
    return {f"TSQ_SCREEN_{n}": "Times Square LED screen — emissive slot, UV 0..1, engine binds a video texture"
            for n in sorted(_SCREENS)}


# ---------------------------------------------------------------------------------------------------------- finish
def finish(objects: Sequence[bpy.types.Object], script_id: str, frame: C.LocalFrame, *, real_footprint,
           fidelity_statement: str, dimensions: dict, notes: str = "", material_slots: dict | None = None,
           lod1_objects: Sequence[bpy.types.Object] | None = None, height_m: float | None = None,
           require_base: bool = True, iou_min: float = C.IOU_MIN, footprint_source: str | None = None,
           plan_polygon=None, plan_polygon_note: str = "", iou_z: float | None = None) -> dict:
    """``common.finish`` with the lane-C registry metadata filled in (and an explicit ``real_footprint``, because
    ``common.load_footprints`` cannot read landmark_footprints.parquet — see the module docstring).

    For an **elevated** structure the 1.5 m slice that ``common.footprint_iou`` takes cuts only the columns, so that
    check is meaningless. Two alternatives are provided and both are labelled in the catalog with
    ``footprint_iou_method`` so nobody mistakes them for the standard figure:

    * ``iou_z`` — take the same section-based measurement at a different height (the High Line's deck at 9.0 m).
    * ``plan_polygon`` — compare the polygon the model's deck was built from against ``real_footprint`` in plan
      (Little Island's deck undulates 4.6-18.9 m, so no single horizontal section can measure it)."""
    meta = SCRIPTS[script_id]
    assign_screen_uvs([o for o in objects if o is not None])
    slots = dict(material_slots or {})
    slots.update(screen_slots())
    parts = meta.get("parts") or []
    dims = dict(dimensions)
    if parts:
        dims["parts"] = {p["id"]: {"name": p["name"], "height_m": p["height_m"], "bins": p["bins"],
                                   "height_source": p["height_source"]} for p in parts}
    tex = texture_status()
    if tex:
        dims["textures"] = tex
    plan_iou = None
    method = plan_polygon_note
    if iou_z is not None:
        meshes = C.all_mesh_objects([o for o in objects if o is not None])
        plan_iou, _sec = C.footprint_iou(meshes, real_footprint, z_cut=float(iou_z))
        if plan_iou < iou_min:
            raise C.FidelityError(f"{script_id}: footprint IoU {plan_iou:.3f} at z = {iou_z} m < {iou_min}")
        method = method or f"model section at z = {iou_z} m (the structure is elevated, so the standard 1.5 m slice would cut only its columns)"
        require_base = False
    elif plan_polygon is not None:
        plan_iou = C.iou(plan_polygon, real_footprint)
        if plan_iou < iou_min:
            raise C.FidelityError(f"{script_id}: plan IoU {plan_iou:.3f} < {iou_min} against the source outline")
        require_base = False
    entry = C.finish(objects, script_id, meta["bins"], frame,
                    height_m=float(meta["height_m"] if height_m is None else height_m),
                    name=meta["name"], fidelity_statement=fidelity_statement, real_footprint=real_footprint,
                    lp_number=meta.get("lp_number", ""), height_source=meta["height_source"],
                    footprint_source=(footprint_source or "NYC Building Footprints (OTI 5zhs-2jue) via data/processed/landmarks/candidate_footprints.parquet"),
                    notes=notes, dimensions=dims, lod1_objects=lod1_objects, tri_budget=int(meta["budget"]),
                    iou_min=iou_min, require_base=require_base, material_slots=slots,
                    extras={"agent": AGENT, "group_parts": [p["id"] for p in parts]})
    if plan_iou is not None:
        entry["footprint_iou"] = round(float(plan_iou), 4)
        entry["footprint_iou_method"] = (method or
                                         "plan IoU of the model's deck outline against the source outline; the "
                                         "structure is elevated, so a 1.5 m section would cut only its columns")
        nb.write_catalog_entry(C.CATALOG_DIR, entry)
    return entry


def render(script_id: str, presets: Sequence[dict] | None = None, **kw):
    return C.render_check(script_id, presets, **kw)


def main_guard(fn):
    """Run ``fn`` and log the catalog line (each C script's ``main`` is wrapped in this)."""
    def wrapper():
        entry = fn()
        if isinstance(entry, dict):
            log.info("%s: %s tris LOD0 / %s LOD1 (%.1f %%), IoU %s, height %.1f m",
                     entry["id"], entry["tris_lod0"], entry["tris_lod1"], 100 * entry["lod1_ratio"],
                     entry["footprint_iou"], entry["model_height_m"])
        return entry
    return wrapper


__all__ = [n for n in dir() if not n.startswith("_")]
