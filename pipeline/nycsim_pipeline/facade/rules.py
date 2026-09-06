"""The facade classifier: an ordered, versioned, auditable rule table (ADR-004).

Every rule is a named predicate over *real* per-building attributes — MapPLUTO ``bldgclass``/``yearbuilt``/
``numfloors``/``bldgfront``, the OTI footprint ``feature_code`` and area, the LPC designation-report ``STYLE1``/
``MATERIAL1``, the LPC historic-district name, the NTA 2020 code, the footprint-derived attachment count, and the OSM
``building:material`` tag — and maps it to one ``facade_class`` of ``blender/common/facade_classes.json``.

Rules are applied **in order**; the first matching rule wins and its hit count is recorded, so the table is auditable
(``rules_table.md``) and every reclassification is traceable to a named rule.  The last rules are exhaustive fallbacks,
so no building can leave the classifier without a class.

The typology and its legal history encoded here:

* **Old Law tenement** (Tenement House Act 1879 – New Law 1901): 25 x 100 ft lot, dumbbell plan with an air shaft,
  5-6 storeys, red brick, segmental-arched openings, iron fire escape on the street face — required for multiple
  dwellings since the 1867 Tenement House Act.  PLUTO class C4 is literally "old law tenement".
* **New Law tenement** (1901 Tenement House Act – 1929): wider lot, interior courts, 5-7 storeys, buff/tan brick with
  limestone trim.
* **Brownstone rowhouse** (1840-1900): Triassic sandstone facing over brick, high stoop over an English basement,
  bracketed pressed-metal or wood cornice, 20 ft lot.  Greek Revival (1830-55) and Federal (1790-1840) predecessors are
  brick with a dormered pitched roof.
* **Prewar apartment house** (1915-1940): the 1916 Zoning Resolution's setback envelope; brick over a limestone base.
* **Art Deco** (1928-1942): Bronx Grand Concourse and Brooklyn corridors, corner windows, brick polychromy.
* **Postwar** (1945-1975): white glazed and tan brick, aluminium sliders, through-wall AC; NYCHA campuses (1935-1975)
  are red-brick towers grouped several to a superblock lot.
* **1961 Zoning Resolution** plaza-bonus glass towers (1962-1988), 1980s brown brick, 2000s+ curtain wall, supertalls.
* **SoHo cast iron** (1855-1890) and Tribeca store-and-loft buildings; industrial lofts and daylight factories.
* **Outer-borough house stock**: PLUTO separates B1 (two-family *brick*) from B2 (two-family *frame*), and A5
  (attached / semi-detached one family) from A1/A2 (detached) — the material and attachment evidence is therefore real,
  not guessed.
* **Taxpayers and corner bodegas** (K1/K2/S1/S9, 1-2 storeys), garages, schools, churches, hospitals, firehouses.

``FACADE_INFERRED`` (fidelity bit 10) is set for every building classified here.  Bit 5 ``MATERIAL_REAL`` is set
separately in :mod:`nycsim_pipeline.facade.derive` when OSM or LPC evidence fixes the material.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Callable

import polars as pl

log = logging.getLogger("nycsim.facade.rules")

RULES_VERSION = "facade-rules/1"

# --------------------------------------------------------------------------------------------------------------------
# Column contract expected by the rule expressions (all real, all present in buildings_base.parquet unless noted).
#   bldg_class, year_built, floors, height, footprint_area, land_use, borough, feature_code, n_bldgs_on_lot,
#   is_primary_on_lot, bldg_frontage, bldg_depth, lot_frontage, nta, hist_district, landmark_id, lpc_style,
#   lpc_material, has_storefront, name
#   attached           int16   footprints sharing a wall (facade `geom` pass, real geometry)
#   is_corner          bool    two free facades ~perpendicular (facade `geom` pass, real geometry)
#   osm_material       int8    §5 material enum from the OSM building:material tag, -1 when absent
# --------------------------------------------------------------------------------------------------------------------

MN, BX, BK, QN, SI = 1, 2, 3, 4, 5

#: NTA 2020 codes where the pre-1930 house stock is overwhelmingly balloon-frame with clapboard/shingle siding
#: (Brooklyn's and Queens' wood-frame belt: Greenpoint, Williamsburg, Bushwick, Ridgewood, Bed-Stuy fringes,
#: Sunset Park, Flatbush, Astoria, Woodside, Richmond Hill, Ozone Park, plus all of Staten Island's north shore).
FRAME_BELT_NTA: tuple[str, ...] = (
    "BK0101", "BK0102", "BK0103", "BK0104", "BK0401", "BK0402", "BK0501", "BK0502", "BK0503", "BK0505",
    "BK1401", "BK1402", "BK1701", "BK1702", "BK1703", "BK1704", "BK1602", "BK0702", "BK0703",
    "QN0101", "QN0102", "QN0103", "QN0104", "QN0203", "QN0502", "QN0501", "QN0902", "QN0903", "QN0904",
    "QN1001", "QN1002", "QN1201", "QN1202", "QN1401", "QN1402", "QN1403",
    "SI0101", "SI0102", "SI0106",
)

#: NTA 2020 codes of the planned Tudor-revival / garden-suburb enclaves (Forest Hills Gardens, Jackson Heights,
#: Jamaica Estates, Douglaston, Riverdale, Fieldston, Todt Hill).
TUDOR_BELT_NTA: tuple[str, ...] = (
    "QN0602", "QN0601", "QN0301", "QN0804", "QN0805", "QN1103", "QN1102", "BX0803", "SI0203",
)

#: NTA 2020 codes of the Manhattan office core, where an O-class building of any era is a real high-rise.
MIDTOWN_DOWNTOWN_NTA: tuple[str, ...] = (
    "MN0101", "MN0102", "MN0401", "MN0501", "MN0502", "MN0601", "MN0602", "MN0603", "MN0604",
)


# --------------------------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Rule:
    """One ordered classifier rule.

    ``expr`` builds the polars boolean expression; ``predicate`` is its human-readable form for the audit table;
    ``rationale`` states the NYC typology / legal fact the rule encodes.
    """
    name: str
    facade_class: int
    predicate: str
    rationale: str
    expr: Callable[[], pl.Expr] = field(repr=False)


# --- expression helpers ------------------------------------------------------------------------------------------------
def _cls() -> pl.Expr:
    return pl.col("bldg_class")


def _c1() -> pl.Expr:
    """First letter of the MapPLUTO building class."""
    return pl.col("bldg_class").str.slice(0, 1)


def isin(*classes: str) -> pl.Expr:
    return _cls().is_in(list(classes))


def letter(*letters: str) -> pl.Expr:
    return _c1().is_in(list(letters))


def yr_between(a: int, b: int) -> pl.Expr:
    """Year in [a, b]; year_built == 0 means unknown and never matches an era test."""
    return (pl.col("year_built") >= a) & (pl.col("year_built") <= b)


def yr_le(b: int) -> pl.Expr:
    return (pl.col("year_built") > 0) & (pl.col("year_built") <= b)


def yr_ge(a: int) -> pl.Expr:
    return pl.col("year_built") >= a


def fl_between(a: int, b: int) -> pl.Expr:
    return (pl.col("floors") >= a) & (pl.col("floors") <= b)


def boro(*codes: int) -> pl.Expr:
    return pl.col("borough").is_in(list(codes))


def hist_like(*fragments: str) -> pl.Expr:
    e = pl.lit(False)
    for f in fragments:
        e = e | pl.col("hist_district").str.contains(f, literal=True)
    return e


def style_like(*fragments: str) -> pl.Expr:
    e = pl.lit(False)
    for f in fragments:
        e = e | pl.col("lpc_style").str.to_lowercase().str.contains(f.lower(), literal=True)
    return e


def lpc_mat_like(*fragments: str) -> pl.Expr:
    e = pl.lit(False)
    for f in fragments:
        e = e | pl.col("lpc_material").str.to_lowercase().str.contains(f.lower(), literal=True)
    return e


def nta_in(codes: tuple[str, ...]) -> pl.Expr:
    return pl.col("nta").is_in(list(codes))


def attached() -> pl.Expr:
    return pl.col("attached") > 0


def detached() -> pl.Expr:
    return pl.col("attached") == 0


def osm_mat(*materials: int) -> pl.Expr:
    return pl.col("osm_material").is_in(list(materials))


# Class groups used repeatedly.
WALKUP_APT = ("C0", "C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8", "C9")
ELEV_APT = ("D0", "D1", "D2", "D3", "D4", "D5", "D6", "D7", "D8", "D9")
CONDO_RES = ("R1", "R2", "R3", "R4", "R6", "R9", "RR")
MIXED_RES = ("S0", "S1", "S2", "S3", "S4", "S5", "S9", "RM", "RX")
OFFICE = ("O1", "O2", "O3", "O4", "O5", "O6", "O7", "O8", "O9", "RB")
LOFT = ("L1", "L2", "L3", "L8", "L9")
FACTORY = ("F1", "F2", "F4", "F5", "F8", "F9")
WAREHOUSE = ("E1", "E3", "E4", "E9")
STORE = ("K1", "K2", "K3", "K4", "K5", "K6", "K7", "K8", "K9")
ONE_FAM = ("A0", "A1", "A2", "A3", "A4", "A5", "A6", "A7", "A8", "A9")
TWO_FAM = ("B1", "B2", "B3", "B9")


# --------------------------------------------------------------------------------------------------------------------
def build_rules() -> list[Rule]:
    """The ordered rule table. First match wins."""
    R: list[Rule] = []

    def add(name: str, fc: int, predicate: str, rationale: str, expr: Callable[[], pl.Expr]) -> None:
        R.append(Rule(name=name, facade_class=fc, predicate=predicate, rationale=rationale, expr=expr))

    # ================================================================================================ tier A: structures
    # The OTI planimetric feature code is a direct observation of what the structure *is* and outranks every attribute
    # inherited from the tax lot, so it is tested first.
    add("accessory_garage", 38,
        "feature_code == 5110",
        "OTI planimetric feature code 5110 is a detached (accessory) garage: a one-storey box with a vehicle door and "
        "no windows. 19.7 % of all NYC footprints. No dedicated kit class exists yet — see REPORT gap G-2.",
        lambda: pl.col("feature_code") == 5110)
    add("transit_structure", 55,
        "bldg_class in U2,U6,U7,T2,T9 or feature_code in 1000..1006",
        "Elevated subway stations, train sheds, piers and other transportation structures (PLUTO U/T classes and the "
        "OTI 'other structure' feature codes) are steel-and-canopy structures, not masonry shells.",
        lambda: isin("U2", "U6", "U7", "T2", "T9") | pl.col("feature_code").is_between(1000, 1006))
    add("gas_station", 48,
        "bldg_class in G3,G4,G5",
        "PLUTO G3/G4/G5 are gasoline stations with/without retail or service: a small kiosk under a steel canopy.",
        lambda: isin("G3", "G4", "G5"))
    add("parking_garage", 38,
        "bldg_class in G0,G1,G6,G7,G9",
        "Multi-storey and licensed parking garages: cast-in-place or precast concrete decks with open spandrels.",
        lambda: isin("G0", "G1", "G6", "G7", "G9"))
    add("auto_shop", 22,
        "bldg_class in G2,G8",
        "Auto-body shops and car dealerships are single-storey masonry/concrete boxes with roll-down vehicle doors.",
        lambda: isin("G2", "G8"))
    add("firehouse", 44,
        "bldg_class == Y1",
        "FDNY firehouses: 2-3 storey brick with limestone trim, a bracketed cornice and an apparatus door at grade. "
        "The 1880-1930 municipal type is still the dominant stock.",
        lambda: _cls() == "Y1")

    # ================================================================================================ tier B: LPC evidence
    # LPC designation reports are real per-building typology; the historic-district polygons are real boundaries.
    add("cast_iron_lpc_material", 20,
        "lpc_material contains 'cast iron' and floors >= 4",
        "A designation report naming cast iron as the primary material is direct evidence of a cast-iron front "
        "(SoHo / Ladies' Mile / Tribeca store-and-loft buildings, 1855-1890).",
        lambda: lpc_mat_like("cast iron", "cast-iron") & (pl.col("floors") >= 4))
    add("soho_cast_iron_district", 20,
        "hist_district contains 'SoHo-Cast Iron' and floors >= 4 and year <= 1900",
        "The SoHo-Cast Iron Historic District is by designation the largest concentration of cast-iron facades in the "
        "world; its 1855-1890 store-and-loft buildings are 5-6 storeys over a full-width cast-iron ground floor.",
        lambda: hist_like("SoHo-Cast Iron") & (pl.col("floors") >= 4) & yr_le(1900))
    add("tribeca_store_loft", 56,
        "hist_district contains 'Tribeca' and floors 3..7 and year <= 1900",
        "Tribeca's designated store-and-loft blocks (1850-1875) are marble/limestone-fronted with cast-iron piers at "
        "the ground floor — the Washington Market dry-goods type.",
        lambda: hist_like("Tribeca") & fl_between(3, 7) & yr_le(1900))
    add("ladies_mile_terracotta", 23,
        "hist_district contains 'Ladies' Mile' and floors >= 6",
        "The Ladies' Mile Historic District is the 1880-1915 cast-iron/terracotta emporium and loft belt; its tall "
        "buildings are Chicago-tripartite terracotta piles.",
        lambda: hist_like("Ladies' Mile") & (pl.col("floors") >= 6))
    add("lpc_brownstone_rowhouse", 3,
        "lpc_material contains 'brownstone'/'sandstone' and floors 3..5 and class in rowhouse set",
        "A designation report naming brownstone/sandstone on a 3-5 storey rowhouse is direct material evidence of the "
        "Italianate/neo-Grec brownstone type (1855-1895).",
        lambda: lpc_mat_like("brownstone", "brown stone", "sandstone") & fl_between(3, 5)
                & (isin("A4", "A9", "B1", "B3", "C0", "C1", "C2", "C3", "S2", "S3") | letter("A", "B", "C", "S")))
    add("lpc_brownstone_low", 4,
        "lpc_material contains 'brownstone'/'sandstone' and floors <= 3",
        "Pre-1875 brownstones are three storeys over a basement; the 1845-1875 Anglo-Italianate type.",
        lambda: lpc_mat_like("brownstone", "brown stone", "sandstone") & (pl.col("floors") <= 3))
    add("lpc_wood_frame_house", 31,
        "lpc_material contains 'wood frame'/'clapboard'/'shingle' and floors <= 3",
        "A designation report naming a wood frame is direct evidence of the balloon-frame house type; today almost all "
        "carry vinyl or aluminium siding over the original clapboard.",
        lambda: lpc_mat_like("wood frame", "clapboard", "shingle", "wood") & (pl.col("floors") <= 3))
    add("lpc_tudor_revival", 29,
        "lpc_style contains 'Tudor'",
        "Tudor Revival: stucco-and-half-timber gables over a brick base, steeply pitched roof — the Jackson Heights / "
        "Forest Hills Gardens / Riverdale garden-suburb type.",
        lambda: style_like("tudor"))
    add("lpc_greek_revival", 7,
        "lpc_style contains 'Greek Revival' and floors <= 4 and year <= 1860",
        "Greek Revival rowhouses (1830-1855): red brick, brownstone trim, low stoop, dentilled wood cornice, 6/6 sash.",
        lambda: style_like("greek revival") & (pl.col("floors") <= 4) & yr_le(1860))
    add("lpc_federal", 6,
        "lpc_style contains 'Federal' and floors <= 3",
        "Federal rowhouses (1790-1840): 2.5 storeys, Flemish-bond brick, dormered pitched roof, 6/6 sash.",
        lambda: style_like("federal") & (pl.col("floors") <= 3))
    add("lpc_beaux_arts_apt", 9,
        "lpc_style contains 'Beaux-Arts'/'neo-Renaissance' and floors >= 8 and class in apartment set",
        "Beaux-Arts apartment houses (1898-1918) are limestone-faced with rusticated bases and heavy modillion "
        "cornices — Riverside Drive, Central Park West, Broadway.",
        lambda: style_like("beaux-arts", "neo-renaissance", "renaissance revival") & (pl.col("floors") >= 8)
                & (isin(*ELEV_APT) | isin(*WALKUP_APT) | isin("H1", "H2", "H6")))
    add("lpc_art_deco", 10,
        "lpc_style contains 'Art Deco' and floors 4..12",
        "Art Deco apartment houses (1928-1942): polychrome brick, corner casement windows, stepped parapets — the "
        "Grand Concourse and the Brooklyn/Queens boulevards.",
        lambda: style_like("art deco") & fl_between(4, 12))
    add("lpc_gothic_church", 35,
        "lpc_style contains 'Gothic' and class in M1,M9",
        "Gothic Revival churches: rock-faced ashlar or brownstone, pointed-arch traceried windows, a tower or spire.",
        lambda: style_like("gothic") & isin("M1", "M9"))
    add("lpc_queen_anne_frame", 31,
        "lpc_style contains 'Queen Anne' and floors <= 3 and borough in BK,QN,SI",
        "Queen Anne frame houses of the 1880-1900 streetcar suburbs (Ditmas Park, Prospect Park South, Douglaston).",
        lambda: style_like("queen anne") & (pl.col("floors") <= 3) & boro(BK, QN, SI))

    # ================================================================================================ tier C: institutions
    add("church_gothic_stone", 35,
        "class in M1,M9 and year <= 1920 and footprint_area >= 250",
        "Large 19th-century churches are stone (rock-faced ashlar, brownstone or granite) with a steeply pitched nave "
        "roof and a spire.",
        lambda: isin("M1", "M9") & yr_le(1920) & (pl.col("footprint_area") >= 250.0))
    add("church_brick", 36,
        "class in M1,M2,M3,M4,M9",
        "Smaller and later churches, missions, rectories and convents are brick Romanesque or vernacular with "
        "round-arched openings.",
        lambda: letter("M"))
    add("school_prewar", 39,
        "class in W1,W2,W3,W4,W5,W7,W8,W9 and year <= 1945",
        "The C.B.J. Snyder-era public-school type (1895-1940): red brick with limestone trim, quoins, a heavy cornice, "
        "large 6/6 sash and a flat parapet roof.",
        lambda: letter("W") & (~isin("W6")) & yr_le(1945))
    add("school_postwar", 40,
        "class in W1..W9 except W6",
        "Post-1950 schools: tan brick, ribbon windows, low parapet, rooftop mechanical.",
        lambda: letter("W") & (~isin("W6")))
    add("university_modern", 54,
        "class == W6",
        "College and university buildings outside a designated campus core are 1960-1995 brown-brick/precast midrise.",
        lambda: _cls() == "W6")
    add("hospital_modern", 41,
        "class in I1..I9 and (year >= 1985 or floors >= 8)",
        "Modern hospital and clinic buildings: curtain wall or metal panel over a masonry podium, large rooftop plant.",
        lambda: letter("I") & (yr_ge(1985) | (pl.col("floors") >= 8)))
    add("hospital_prewar", 39,
        "class in I1..I9 and year <= 1945",
        "Prewar hospitals and dispensaries share the institutional masonry type with the Snyder schools.",
        lambda: letter("I") & yr_le(1945))
    add("hospital_postwar", 54,
        "class in I1..I9",
        "1945-1985 hospitals and nursing homes: brown brick / precast midrise slabs.",
        lambda: letter("I"))
    add("civic_prewar", 39,
        "class in N,P,J,Y,Z (except Y1) and year <= 1945",
        "Prewar civic buildings — libraries, museums, lodges, theatres, courthouses, police stations, asylums — are "
        "masonry with a cornice and monumental openings.",
        lambda: (letter("N", "P", "J", "Y", "Z") & (~isin("Y1"))) & yr_le(1945))
    add("civic_postwar", 40,
        "class in N,P,J,Y,Z (except Y1)",
        "Postwar civic buildings: tan brick / precast with ribbon glazing and rooftop plant.",
        lambda: letter("N", "P", "J", "Y", "Z") & (~isin("Y1")))

    # ================================================================================================ tier D: industrial
    add("self_storage", 46,
        "class == E7 or (class in E* and year >= 1990)",
        "Self-storage conversions and new-builds: corrugated/ribbed metal panel over a concrete frame, minimal glazing.",
        lambda: (_cls() == "E7") | (letter("E") & yr_ge(1990)))
    add("daylight_factory", 45,
        "class in F*,L1,L2,L3 and year 1900..1935 and floors >= 4",
        "The reinforced-concrete daylight factory (Kahn system, 1908-1935): concrete frame with wide steel-sash "
        "industrial windows filling the bays — Long Island City, Bush Terminal, the Bronx industrial belt.",
        lambda: (letter("F") | isin("L1", "L2", "L3")) & yr_between(1900, 1935) & (pl.col("floors") >= 4))
    add("industrial_loft_brick", 21,
        "class in L*,F*,RM,RW,O5 and year <= 1930 and floors >= 4",
        "The 1895-1930 masonry loft: load-bearing red brick with brick-pier bays, corbelled cornice, water tower, "
        "fire escapes and a loading dock — DUMBO, the Garment District, Long Island City.",
        lambda: (isin(*LOFT) | letter("F") | isin("RM", "RW")) & yr_le(1930) & (pl.col("floors") >= 4))
    add("warehouse_low", 22,
        "class in E*,F*,L*,RW and floors <= 3",
        "Single- and two-storey warehouses and light-manufacturing sheds: concrete or brick walls, roll-down loading "
        "doors, parapet roof.",
        lambda: (letter("E", "F") | isin(*LOFT) | isin("RW")) & (pl.col("floors") <= 3))
    add("loft_converted", 21,
        "class in L*,F*,E*,RW,RM",
        "Remaining loft / factory / warehouse stock keeps the masonry loft treatment.",
        lambda: letter("L", "F", "E") | isin("RW", "RM"))

    # ================================================================================================ tier E: retail
    add("big_box_retail", 47,
        "class in K3,K5,K6,K8 or (class in K* and footprint_area >= 1800 and floors <= 2 and year >= 1975)",
        "Department stores, franchise/shopping-centre retail and big boxes: precast tilt-up panels, a tall parapet "
        "sign band, a canopy over the entrance and a rooftop mechanical field.",
        lambda: isin("K3", "K5", "K6", "K8")
                | (letter("K") & (pl.col("footprint_area") >= 1800.0) & (pl.col("floors") <= 2) & yr_ge(1975)))
    add("limestone_bank", 24,
        "class in K4,O7,O9,K1 and year 1900..1940 and floors <= 6 and footprint_area >= 200",
        "The 1900-1935 neighbourhood bank: limestone or granite temple front, engaged columns or pilasters, a single "
        "very tall banking-hall storey.",
        lambda: isin("K4", "O7", "O9", "K1") & yr_between(1900, 1940) & (pl.col("floors") <= 6)
                & (pl.col("footprint_area") >= 200.0))
    add("taxpayer_corner", 37,
        "class in K1,K2,K9,S1,S9,RS and floors <= 2",
        "The 'taxpayer': a one- or two-storey brick store row built to carry the taxes on a lot held for later "
        "development, and the corner bodega/deli type it produced across the outer boroughs.",
        lambda: isin("K1", "K2", "K9", "S1", "S9", "RS") & (pl.col("floors") <= 2))
    add("retail_mixed_prewar", 37,
        "class in K* and floors <= 3 and year <= 1975",
        "Remaining low-rise store buildings keep the taxpayer treatment.",
        lambda: letter("K") & (pl.col("floors") <= 3) & yr_le(1975))
    add("retail_midrise", 54,
        "class in K*",
        "Taller and later retail buildings: brown brick / precast with a glazed retail base.",
        lambda: letter("K"))

    # ================================================================================================ tier F: hotels
    add("hotel_prewar", 43,
        "class in H* and year <= 1940",
        "The 1905-1935 masonry hotel: brick over a limestone base, setbacks above the 1916 street wall, a marquee "
        "canopy and a heavy cornice.",
        lambda: letter("H") & yr_le(1940))
    add("hotel_modern", 42,
        "class in H*",
        "Post-1990 hotels: curtain wall or metal panel with a canopy and a glazed lobby/bar at grade.",
        lambda: letter("H"))

    # ================================================================================================ tier G: offices
    add("supertall_office", 18,
        "class in O*,RB and floors >= 55 and year >= 2005",
        "Post-2005 supertalls: full unitised curtain wall, slender setback profile, mechanical crowns.",
        lambda: isin(*OFFICE) & (pl.col("floors") >= 55) & yr_ge(2005))
    add("office_curtain_2010", 17,
        "class in O*,RB and year >= 2000 and floors >= 10",
        "Post-2000 office towers: unitised curtain wall on a 4.2 m floor-to-floor module with a glazed lobby and a "
        "mechanical crown (Hudson Yards, the far West Side, Downtown Brooklyn, Long Island City).",
        lambda: isin(*OFFICE) & yr_ge(2000) & (pl.col("floors") >= 10))
    add("office_curtain_1970", 16,
        "class in O*,RB and year 1962..1988 and floors >= 15",
        "The 1961 Zoning Resolution's plaza bonus produced the 1962-1988 glass-and-aluminium slab set back behind an "
        "open plaza — Sixth Avenue, Water Street, Third Avenue.",
        lambda: isin(*OFFICE) & yr_between(1962, 1988) & (pl.col("floors") >= 15))
    add("office_international_1960", 19,
        "class in O*,RB and year 1950..1968 and floors >= 10",
        "International Style curtain-wall offices (Lever House 1952, Seagram 1958 and their imitators): green or grey "
        "glass in a bronze/aluminium grid on a travertine podium.",
        lambda: isin(*OFFICE) & yr_between(1950, 1968) & (pl.col("floors") >= 10))
    add("office_art_deco_setback", 25,
        "class in O*,RB and year 1926..1945 and floors >= 18",
        "The 1916 Zoning Resolution's setback envelope plus the Art Deco vocabulary produced the 1926-1940 limestone "
        "and brick ziggurat with a crown — Wall Street, Midtown, Court Square.",
        lambda: isin(*OFFICE) & yr_between(1926, 1945) & (pl.col("floors") >= 18))
    add("office_masonry_setback", 26,
        "class in O*,RB and year 1916..1935 and floors >= 9",
        "1916-1935 masonry office buildings below tower height: tan brick over a limestone base, setbacks, a "
        "modillion cornice and a retail base.",
        lambda: isin(*OFFICE) & yr_between(1916, 1935) & (pl.col("floors") >= 9))
    add("office_terracotta_1905", 23,
        "class in O*,RB and year <= 1925 and floors >= 7",
        "The 1895-1925 skeleton-frame office: terracotta and limestone cladding in a Chicago-tripartite base/shaft/"
        "capital composition with a projecting cornice.",
        lambda: isin(*OFFICE) & yr_le(1925) & (pl.col("floors") >= 7))
    add("office_brown_brick_1985", 54,
        "class in O*,RB and year 1969..1999",
        "The 1970-1999 brown-brick and precast midrise office — the dominant outer-borough and secondary-Manhattan "
        "office stock.",
        lambda: isin(*OFFICE) & yr_between(1969, 1999))
    add("office_lowrise_prewar", 26,
        "class in O*,RB and year <= 1945",
        "Remaining prewar office buildings keep the masonry setback treatment.",
        lambda: isin(*OFFICE) & yr_le(1945))
    add("office_generic", 54,
        "class in O*,RB",
        "Remaining office buildings: brown brick / precast midrise.",
        lambda: isin(*OFFICE))

    # ================================================================================================ tier H: apartments
    add("supertall_residential", 18,
        "class in D*,R4,RR and floors >= 50 and year >= 2005",
        "Post-2005 supertall residential (Billionaires' Row, 57th Street, Downtown Brooklyn): curtain wall with "
        "limestone or metal spandrels, 3.4 m floor-to-floor.",
        lambda: (isin(*ELEV_APT) | isin("R4", "RR")) & (pl.col("floors") >= 50) & yr_ge(2005))
    add("nycha_campus_tower", 13,
        "floors >= 6 and year 1935..1975 and n_bldgs_on_lot >= 3 and footprint_area >= 400 and class in C/D/R/S",
        "NYCHA and Mitchell-Lama campuses are superblocks: several identical red-brick towers on one very large tax "
        "lot, cross-shaped or slab plan, no cornice, no storefront, aluminium sliders.",
        lambda: (pl.col("floors") >= 6) & yr_between(1935, 1975) & (pl.col("n_bldgs_on_lot") >= 3)
                & (pl.col("footprint_area") >= 400.0) & letter("C", "D", "R", "S"))
    add("condo_midrise_2010", 50,
        "class in D*,R4,RR,RM and year >= 2000 and floors 6..24",
        "The 2000s+ condo midrise: glass-and-brick or glass-and-metal facade, balconies, a canopy and a retail or "
        "lobby base.",
        lambda: (isin(*ELEV_APT) | isin("R4", "RR", "RM")) & yr_ge(2000) & fl_between(6, 24))
    add("condo_tower_2010", 17,
        "class in D*,R4,RR and year >= 2000 and floors >= 25",
        "Post-2000 residential towers above 25 storeys are curtain-walled.",
        lambda: (isin(*ELEV_APT) | isin("R4", "RR")) & yr_ge(2000) & (pl.col("floors") >= 25))
    add("brown_brick_condo_1985", 15,
        "class in D*,R4,RR and year 1976..1999 and floors >= 10",
        "The 1980s-90s brown-brick condo tower with punched windows, balconies and setbacks — the Upper East Side, "
        "Battery Park City, Downtown Brooklyn.",
        lambda: (isin(*ELEV_APT) | isin("R4", "RR")) & yr_between(1976, 1999) & (pl.col("floors") >= 10))
    add("mitchell_lama_slab", 14,
        "class in D*,R4 and year 1962..1980 and floors >= 14",
        "Mitchell-Lama and urban-renewal slabs (1962-1980): exposed concrete frame with brick infill, balconies, "
        "through-wall AC sleeves.",
        lambda: (isin(*ELEV_APT) | isin("R4")) & yr_between(1962, 1980) & (pl.col("floors") >= 14))
    add("postwar_white_brick", 11,
        "class in D*,R4 and year 1955..1975 and floors >= 11 and borough == MN",
        "The Manhattan white-glazed-brick tower (1955-1975): white or ivory glazed brick, aluminium sliders, "
        "balconies, a canopy — Second and Third Avenue, the Upper East Side.",
        lambda: (isin(*ELEV_APT) | isin("R4")) & yr_between(1955, 1975) & (pl.col("floors") >= 11) & boro(MN))
    add("postwar_red_brick_elevator", 12,
        "class in D*,R4 and year 1945..1975",
        "The postwar six-storey red-brick elevator apartment house — the dominant 1945-1975 outer-borough type.",
        lambda: (isin(*ELEV_APT) | isin("R4")) & yr_between(1945, 1975))
    add("prewar_beaux_arts_apt", 9,
        "class in D*,C6 and year 1898..1918 and floors >= 9 and borough == MN",
        "Beaux-Arts apartment houses (1898-1918): limestone base and upper facade, rusticated ground floor, balconies "
        "and a heavy modillion cornice.",
        lambda: (isin(*ELEV_APT) | isin("C6")) & yr_between(1898, 1918) & (pl.col("floors") >= 9) & boro(MN))
    add("art_deco_apt", 10,
        "class in D*,C* and year 1928..1942 and floors 4..12",
        "Art Deco apartment houses (1928-1942): brick polychromy, corner casement windows, stepped parapet — the "
        "Grand Concourse, Ocean Parkway, Jackson Heights.",
        lambda: (isin(*ELEV_APT) | isin(*WALKUP_APT)) & yr_between(1928, 1942) & fl_between(4, 12))
    add("prewar_apt_1925", 8,
        "class in D*,C6,C1,C7,R4 and year 1915..1940 and floors >= 6",
        "The prewar apartment house (1915-1940): red brick over a limestone base, setbacks above the 1916 street "
        "wall, casement pairs, a canopy and a modillion cornice.",
        lambda: (isin(*ELEV_APT) | isin("C6", "C1", "C7", "R4")) & yr_between(1915, 1940) & (pl.col("floors") >= 6))
    add("garden_apt", 51,
        "class in C9,C6,D1,C1,R2 and floors <= 4 and n_bldgs_on_lot >= 2 and year 1925..1965",
        "Garden apartments (1925-1965): two- and three-storey red-brick blocks set in landscaped superblocks — "
        "Jackson Heights, Sunnyside Gardens, Parkchester, Bay Terrace.",
        lambda: isin("C9", "C6", "D1", "C1", "R2") & (pl.col("floors") <= 4) & (pl.col("n_bldgs_on_lot") >= 2)
                & yr_between(1925, 1965))

    # ================================================================================================ tier I: tenements
    add("old_law_tenement_class", 1,
        "class == C4",
        "MapPLUTO class C4 is literally 'old law tenement': the 1879-1901 dumbbell plan on a 25 x 100 ft lot, "
        "red brick, segmental-arched openings, iron fire escape.",
        lambda: _cls() == "C4")
    add("old_law_tenement_era", 1,
        "class in C1,C2,C7,S3,S4,S5,C0 and year 1879..1901 and floors 4..7 and borough in MN,BX,BK,QN",
        "Multiple dwellings built between the 1879 Tenement House Act and the 1901 New Law are Old Law tenements: "
        "5-6 storeys, 25 ft frontage, four windows across, fire escape on the street face.",
        lambda: isin("C1", "C2", "C7", "S3", "S4", "S5", "C0") & yr_between(1879, 1901) & fl_between(4, 7)
                & boro(MN, BX, BK, QN))
    add("new_law_tenement", 2,
        "class in C1,C2,C7,C5,S5,S4,D1 and year 1902..1929 and floors 4..8",
        "New Law tenements (1901 Tenement House Act - 1929): wider lot, interior courts, 5-7 storeys, buff/tan brick "
        "with limestone trim and a pressed-metal dentil cornice.",
        lambda: isin("C1", "C2", "C7", "C5", "S5", "S4", "D1") & yr_between(1902, 1929) & fl_between(4, 8))
    add("bushwick_frame_3fl", 32,
        "class in C0,C2,C3,S3,B* and year 1885..1925 and floors == 3 and borough in BK,QN and (frame belt NTA or "
        "class B2)",
        "The three-storey Brooklyn/Queens frame tenement (Bushwick, Ridgewood, Greenpoint, Astoria): balloon frame "
        "with a pressed-metal cornice, now sided in vinyl or aluminium; a store often occupies the corner ground floor.",
        lambda: (isin("C0", "C2", "C3", "S3", "S2", "B2", "B9") ) & yr_between(1885, 1925) & (pl.col("floors") == 3)
                & boro(BK, QN) & (nta_in(FRAME_BELT_NTA) | (_cls() == "B2")))
    add("fedders_special", 33,
        "class in C0,C1,C2,C3,B2,D1,RM and year >= 1998 and floors 3..6",
        "The 2000s infill multiple dwelling ('Fedders special'): tan or beige brick with through-wall AC sleeves "
        "punched under every window, a token balcony and a garage at grade.",
        lambda: (isin("C0", "C1", "C2", "C3", "B2", "D1", "RM") | isin(*CONDO_RES)) & yr_ge(1998) & fl_between(3, 6))
    add("townhouse_modern", 49,
        "class in C0,C1,C7,D0,D1,RM,R* and year >= 2005 and floors 3..8",
        "The 2005+ boutique townhouse/condo: metal panel and glass with full-height windows, balconies and a "
        "storefront or lobby base — Williamsburg, Long Island City, Chelsea.",
        lambda: (isin("C0", "C1", "C7", "D0", "D1", "RM") | isin(*CONDO_RES)) & yr_ge(2005) & fl_between(3, 8))
    add("walkup_prewar_tenement", 2,
        "class in C* and year <= 1945 and floors 4..7",
        "Remaining prewar 4-7 storey walk-up apartment houses take the New Law tenement treatment.",
        lambda: isin(*WALKUP_APT) & yr_le(1945) & fl_between(4, 7))
    add("walkup_postwar", 12,
        "class in C*,S* and floors 4..7",
        "Postwar 4-7 storey walk-ups: red brick, aluminium sliders, parapet roof.",
        lambda: (isin(*WALKUP_APT) | isin(*MIXED_RES)) & fl_between(4, 7))

    # ================================================================================================ tier J: rowhouses
    add("federal_rowhouse", 6,
        "class in A4,B1,C0,S2 and year <= 1840 and floors <= 3",
        "Federal rowhouses (1790-1840): 2.5 storeys, Flemish-bond red brick, brownstone lintels, dormered pitched "
        "roof — Greenwich Village, the Lower East Side, Vinegar Hill.",
        lambda: isin("A4", "B1", "B3", "C0", "S2", "A9") & yr_le(1840) & (pl.col("floors") <= 3))
    add("greek_revival_rowhouse", 7,
        "class in A4,B1,B3,C0,S2 and year 1830..1858 and floors 3..4",
        "Greek Revival rowhouses (1830-1855): red brick with brownstone trim, a low stoop, pilastered doorway and a "
        "dentilled wood cornice.",
        lambda: isin("A4", "B1", "B3", "C0", "S2", "A9") & yr_between(1830, 1858) & fl_between(3, 4))
    add("brownstone_rowhouse_1860", 4,
        "class in A4,B1,B3,C0,S2 and year 1845..1875 and floors <= 3 and borough in MN,BK and attached",
        "The pre-1875 Italianate brownstone: three storeys over an English basement, a high stoop, bracketed cornice, "
        "2/2 sash — Brooklyn Heights, Cobble Hill, the Village.",
        lambda: isin("A4", "A9", "B1", "B3", "C0", "S2") & yr_between(1845, 1875) & (pl.col("floors") <= 3)
                & boro(MN, BK) & attached())
    add("brownstone_rowhouse_1880", 3,
        "class in A4,A9,B1,B3,C0,C1,S2 and year 1855..1895 and floors 3..5 and borough in MN,BK,BX and attached",
        "The neo-Grec / Renaissance Revival brownstone (1875-1895): four storeys over a basement, high stoop, "
        "pressed-metal bracketed cornice — Park Slope, Bed-Stuy, Harlem, Clinton Hill.",
        lambda: isin("A4", "A9", "B1", "B3", "C0", "C1", "C2", "S2", "S3") & yr_between(1855, 1895) & fl_between(3, 5)
                & boro(MN, BK, BX) & attached())
    add("limestone_rowhouse_1900", 5,
        "class in A4,A9,B1,B3,C0,S2 and year 1890..1915 and floors 3..4 and borough in MN,BK,BX and attached",
        "The turn-of-the-century limestone rowhouse: a bow or swell front in Indiana limestone with a stone modillion "
        "cornice — Park Slope, Crown Heights, Sunset Park, the Grand Concourse.",
        lambda: isin("A4", "A9", "B1", "B3", "C0", "C1", "S2") & yr_between(1890, 1915) & fl_between(3, 4)
                & boro(MN, BK, BX) & attached())
    add("brooklyn_frame_rowhouse", 31,
        "class in B2,B9,A9,C0,S2 and year 1880..1925 and floors 2..3 and borough in BK,QN,SI and (frame belt or B2)",
        "The two- and three-storey frame rowhouse of the 1880-1925 streetcar belt: clapboard or shingle (now vinyl) "
        "over a balloon frame, a pressed-metal cornice and a wooden stoop.",
        lambda: isin("B2", "B9", "A9", "A1", "C0", "S2") & yr_between(1880, 1925) & fl_between(2, 3)
                & boro(BK, QN, SI) & (nta_in(FRAME_BELT_NTA) | (_cls() == "B2")))
    add("rowhouse_brick_1920", 34,
        "class in A5,B1,B2,B3,S2 and year 1900..1945 and floors 2..3 and attached",
        "The 1900-1945 attached brick rowhouse: two storeys, flat roof behind a corbelled parapet, a projecting "
        "brick or wood bay over a low stoop — Ridgewood, Bay Ridge, Bensonhurst, Astoria, Woodhaven.",
        lambda: isin("A5", "A1", "A9", "B1", "B2", "B3", "S2") & yr_between(1900, 1945) & fl_between(2, 3) & attached())

    # ================================================================================================ tier K: houses
    add("tudor_belt_house", 29,
        "class in A*,B* and year 1918..1945 and NTA in the Tudor belt",
        "The planned garden-suburb Tudor of 1918-1940 (Forest Hills Gardens, Jackson Heights, Jamaica Estates, "
        "Riverdale/Fieldston, Todt Hill): stucco with half-timbering over brick, steep slate/tile roof.",
        lambda: (isin(*ONE_FAM) | isin(*TWO_FAM)) & yr_between(1918, 1945) & nta_in(TUDOR_BELT_NTA))
    add("stucco_mediterranean", 52,
        "class in A*,B* and year 1915..1940 and (lpc_material stucco or osm material stucco)",
        "The 1920s Mediterranean / Spanish Colonial Revival house: stucco walls, clay-tile hipped roof, arched "
        "openings — Jackson Heights, Forest Hills, Ditmas Park, Staten Island's south shore.",
        lambda: (isin(*ONE_FAM) | isin(*TWO_FAM)) & yr_between(1915, 1940)
                & (lpc_mat_like("stucco") | osm_mat(10)))
    add("mansion_stone", 53,
        "class in A3,A7,W3,N9,M9 and footprint_area >= 300 and floors >= 2 and year <= 1940",
        "Free-standing stone mansions and institutional houses (Riverdale, Todt Hill, Prospect Park South, Fort "
        "Greene): rock-faced stone with a steep slate roof and dormers.",
        lambda: isin("A3", "A7", "W3", "N9", "M9", "A6") & (pl.col("footprint_area") >= 300.0)
                & (pl.col("floors") >= 2) & yr_le(1940))
    add("queens_brick_2fam", 28,
        "class in B1,A5,B3 and year 1918..1948 and borough in QN,BX,BK,SI",
        "The interwar brick two-family: PLUTO class B1 is by definition *brick*; a projecting brick or wood bay, "
        "soldier-course lintels, a corbelled parapet and a garage under the stoop.",
        lambda: isin("B1", "A5", "B3") & yr_between(1918, 1948) & boro(QN, BX, BK, SI))
    add("queens_vinyl_2fam", 27,
        "class in B2,B3,B9,A2,A5,A1,A9 and year 1945..1979",
        "The postwar detached/semi-detached two-family: PLUTO class B2 is by definition *frame*; vinyl or aluminium "
        "siding over the frame, a low-pitched roof, a picture window and an attached garage.",
        lambda: isin("B2", "B3", "B9", "A2", "A5", "A1", "A9", "A0") & yr_between(1945, 1979))
    add("brick_house_postwar", 28,
        "class in B1,A5 attached and year >= 1946 and borough in QN,BX,BK,SI",
        "MapPLUTO class B1 is by definition a *brick* two-family: the post-war outer-borough B1 stock is the same "
        "brick box as the interwar type, so it must never fall through to a sided-frame class.",
        lambda: (isin("B1") | (isin("A5") & attached())) & yr_ge(1946) & boro(QN, BX, BK, SI))
    add("si_qn_single_family_siding", 30,
        "class in A*,B* and year >= 1960 and borough in SI,QN,BX",
        "The post-1960 Staten Island / eastern Queens single family: vinyl siding with a brick veneer water table, "
        "a low-pitched roof, an attached garage.",
        lambda: (isin(*ONE_FAM) | isin(*TWO_FAM)) & yr_ge(1960) & boro(SI, QN, BX))
    add("house_modern_generic", 30,
        "class in A*,B*,R1,R2,R3,R6 and year >= 1960",
        "Post-1960 one- and two-family houses elsewhere in the city take the same sided-frame treatment.",
        lambda: (isin(*ONE_FAM) | isin(*TWO_FAM) | isin("R1", "R2", "R3", "R6")) & yr_ge(1960))
    add("house_frame_prewar", 31,
        "class in A*,B* and year <= 1925 and detached",
        "Detached pre-1925 frame houses across Brooklyn, Queens and Staten Island: clapboard/shingle (now vinyl) with "
        "a wood cornice and a porch.",
        lambda: (isin(*ONE_FAM) | isin(*TWO_FAM)) & (~isin("B1")) & yr_le(1925) & detached())
    add("house_brick_prewar", 34,
        "class in A*,B*",
        "Remaining one- and two-family houses: the interwar brick type.",
        lambda: isin(*ONE_FAM) | isin(*TWO_FAM))

    # ================================================================================================ tier L: fallbacks
    add("fallback_supertall", 18,
        "floors >= 50 and year >= 2005",
        "Any remaining post-2005 building above 50 storeys is a curtain-walled supertall.",
        lambda: (pl.col("floors") >= 50) & yr_ge(2005))
    add("fallback_tower_modern", 17,
        "floors >= 20 and year >= 1990",
        "Any remaining post-1990 tower is curtain-walled.",
        lambda: (pl.col("floors") >= 20) & yr_ge(1990))
    add("fallback_tower_postwar", 13,
        "floors >= 12 and year 1940..1989",
        "Remaining 1940-1989 towers take the postwar brick tower treatment.",
        lambda: (pl.col("floors") >= 12) & yr_between(1940, 1989))
    add("fallback_tower_prewar", 26,
        "floors >= 10",
        "Remaining tall buildings take the prewar masonry setback treatment.",
        lambda: pl.col("floors") >= 10)
    add("fallback_mid_modern", 50,
        "floors >= 6 and year >= 1990",
        "Remaining post-1990 midrise: glass-and-brick condo treatment.",
        lambda: (pl.col("floors") >= 6) & yr_ge(1990))
    add("fallback_mid_postwar", 12,
        "floors >= 6 and year >= 1945",
        "Remaining postwar midrise: red-brick elevator apartment treatment.",
        lambda: (pl.col("floors") >= 6) & yr_ge(1945))
    add("fallback_mid_prewar", 8,
        "floors >= 6",
        "Remaining prewar and unknown-year midrise: prewar apartment treatment.",
        lambda: pl.col("floors") >= 6)
    add("fallback_low_prewar_masonry", 2,
        "floors 3..5 and year <= 1929",
        "Remaining prewar 3-5 storey buildings: New Law tenement treatment.",
        lambda: fl_between(3, 5) & yr_le(1929))
    add("fallback_low_modern", 33,
        "floors 3..5 and year >= 1990",
        "Remaining post-1990 3-5 storey buildings: the 2000s infill type.",
        lambda: fl_between(3, 5) & yr_ge(1990))
    add("fallback_low_postwar", 12,
        "floors 3..5",
        "Remaining 3-5 storey buildings: postwar brick treatment.",
        lambda: fl_between(3, 5))
    add("fallback_small_suburban", 30,
        "floors <= 2 and borough in QN,SI",
        "Remaining Queens / Staten Island low structures: sided frame treatment.",
        lambda: (pl.col("floors") <= 2) & boro(QN, SI))
    add("fallback_small_masonry", 34,
        "always true",
        "Exhaustive fallback: a low masonry structure. Guarantees that no building leaves the classifier unclassified.",
        lambda: pl.lit(True))

    return R


RULES: list[Rule] = build_rules()
RULE_INDEX: dict[str, int] = {r.name: i for i, r in enumerate(RULES)}


def classify(df: pl.DataFrame) -> tuple[pl.Series, pl.Series, dict[str, int]]:
    """Apply the ordered rule table.

    Returns ``(facade_class int16, rule_id int16, hits)`` where ``rule_id`` is the 0-based index into :data:`RULES`
    and ``hits`` maps rule name -> number of buildings it claimed.
    """
    n = df.height
    required = {"bldg_class", "year_built", "floors", "footprint_area", "borough", "feature_code", "n_bldgs_on_lot",
                "nta", "hist_district", "lpc_style", "lpc_material", "attached", "osm_material"}
    missing = required - set(df.columns)
    if missing:
        raise KeyError(f"classify(): missing columns {sorted(missing)}")

    import numpy as np
    fc = np.zeros(n, dtype=np.int16)
    rid = np.full(n, -1, dtype=np.int16)
    hits: dict[str, int] = {}
    remaining = np.ones(n, dtype=bool)
    for i, rule in enumerate(RULES):
        if not remaining.any():
            hits[rule.name] = 0
            continue
        m = df.select(rule.expr().alias("m"))["m"].fill_null(False).to_numpy()
        if m.dtype != bool:
            m = m.astype(bool)
        take = remaining & m
        k = int(take.sum())
        hits[rule.name] = k
        if k:
            fc[take] = np.int16(rule.facade_class)
            rid[take] = np.int16(i)
            remaining &= ~take
    unclassified = int(remaining.sum())
    if unclassified:
        raise RuntimeError(f"rule table is not exhaustive: {unclassified} buildings unclassified")
    log.info("classified %d buildings with %d rules", n, len(RULES))
    return pl.Series("facade_class", fc), pl.Series("facade_rule", rid), hits


def rules_table_markdown(hits: dict[str, int] | None = None, total: int | None = None) -> str:
    """Dump the full ordered rule table (optionally with hit counts) as markdown."""
    from .enums import load_classes
    class_name = {c["facade_class"]: c["id"] for c in load_classes()}
    out = [
        f"# Facade classifier rule table (`{RULES_VERSION}`)", "",
        f"{len(RULES)} ordered rules over real per-building attributes (ADR-004). The **first matching rule wins**; "
        "the last rule matches unconditionally so the table is exhaustive.", "",
        "Columns: `#` order, `rule` stable rule name, `class` the `facade_class` written to "
        "`buildings.parquet`, `predicate` the condition, `hits` buildings claimed by the rule in the recorded run, "
        "`share` hits / total buildings.", "",
        "| # | rule | class | facade_class id | predicate | hits | share |",
        "|--:|---|--:|---|---|--:|--:|",
    ]
    for i, r in enumerate(RULES):
        h = hits.get(r.name, 0) if hits else 0
        share = (100.0 * h / total) if (hits and total) else 0.0
        out.append(f"| {i} | `{r.name}` | {r.facade_class} | `{class_name.get(r.facade_class, '?')}` | "
                   f"{r.predicate} | {h:,} | {share:.3f} % |")
    out += ["", "## Rationale per rule", ""]
    for i, r in enumerate(RULES):
        out.append(f"**{i}. `{r.name}` -> {r.facade_class} `{class_name.get(r.facade_class, '?')}`**  ")
        out.append(f"*predicate:* `{r.predicate}`  ")
        out.append(f"{r.rationale}")
        out.append("")
    return "\n".join(out)
