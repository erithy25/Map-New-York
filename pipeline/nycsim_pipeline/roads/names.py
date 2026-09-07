"""Street-name normalisation so DOT CSVs ("East 99 Street", "1 Avenue", "Pelham Pkwy"), LION
("EAST 168 STREET"), CSCL ("E  168 ST") and OSM ("East 168th Street") compare equal."""
from __future__ import annotations

import re

_ORDINAL = re.compile(r"\b(\d+)(ST|ND|RD|TH)\b")
_PUNCT = re.compile(r"[.,'’`\"()/\-&]+")
_SPACES = re.compile(r"\s+")

_NUMBER_WORDS = {
    "FIRST": "1", "SECOND": "2", "THIRD": "3", "FOURTH": "4", "FIFTH": "5", "SIXTH": "6", "SEVENTH": "7",
    "EIGHTH": "8", "NINTH": "9", "TENTH": "10", "ELEVENTH": "11", "TWELFTH": "12",
}

# token -> canonical token
_ABBR = {
    "AVENUE": "AVE", "AV": "AVE", "AVE": "AVE", "AVEN": "AVE",
    "STREET": "ST", "STR": "ST", "ST": "ST",
    "ROAD": "RD", "RD": "RD",
    "BOULEVARD": "BLVD", "BLV": "BLVD", "BL": "BLVD", "BLVD": "BLVD", "BOUL": "BLVD",
    "PLACE": "PL", "PL": "PL",
    "PARKWAY": "PKWY", "PKWY": "PKWY", "PY": "PKWY", "PKY": "PKWY", "PARKWY": "PKWY",
    "EXPRESSWAY": "EXPY", "EXPWY": "EXPY", "EXPY": "EXPY", "EP": "EXPY", "EXWY": "EXPY", "EXPRESSWY": "EXPY", "EXPW": "EXPY",
    "DRIVE": "DR", "DRV": "DR", "DR": "DR",
    "LANE": "LN", "LN": "LN",
    "COURT": "CT", "CT": "CT",
    "TERRACE": "TER", "TER": "TER", "TERR": "TER",
    "HIGHWAY": "HWY", "HWY": "HWY",
    "BRIDGE": "BR", "BRDG": "BR", "BRG": "BR", "BR": "BR",
    "TUNNEL": "TUNL", "TUNL": "TUNL", "TNL": "TUNL", "TNNL": "TUNL",
    "CONCOURSE": "CONC", "CNCRSE": "CONC", "CONC": "CONC",
    "SQUARE": "SQ", "SQ": "SQ",
    "CIRCLE": "CIR", "CIR": "CIR",
    "HEIGHTS": "HTS", "HTS": "HTS",
    "PLAZA": "PLZ", "PLZ": "PLZ", "PZ": "PLZ",
    "TURNPIKE": "TPKE", "TPKE": "TPKE", "TPK": "TPKE",
    "ISLAND": "IS", "IS": "IS",
    "PARK": "PARK", "PK": "PARK",
    "NORTH": "N", "SOUTH": "S", "EAST": "E", "WEST": "W",
    "NORTHBOUND": "NB", "SOUTHBOUND": "SB", "EASTBOUND": "EB", "WESTBOUND": "WB",
    "MOUNT": "MT", "MT": "MT",
    "SAINT": "ST",
    "FORT": "FT", "FT": "FT",
    "ROUTE": "RTE", "RTE": "RTE",
    "JUNIOR": "JR", "JR": "JR",
    "BEACH": "BCH", "BCH": "BCH",
    "CENTER": "CTR", "CENTRE": "CTR", "CTR": "CTR",
    "EXTENSION": "EXT", "EXT": "EXT",
    "SERVICE": "SR", "SR": "SR",
    "APPROACH": "APPR", "APPR": "APPR",
    "ENTRANCE": "EN", "EN": "EN", "ENT": "EN",
    "EXIT": "ET", "ET": "ET",
    "RAMP": "RP", "RP": "RP",
    "PEDESTRIAN": "PED", "PED": "PED",
}

_ALIASES = {
    "AVE OF THE AMERICAS": "6 AVE",
    "AMERICAS AVE": "6 AVE",
    "ADAM CLAYTON POWELL JR BLVD": "7 AVE",
    "ADAM CLAYTON POWELL BLVD": "7 AVE",
    "ADAM C POWELL BLVD": "7 AVE",
    "FREDERICK DOUGLASS BLVD": "8 AVE",
    "MALCOLM X BLVD": "LENOX AVE",
    "PARK AVE S": "PARK AVE",
    "GRAND CONC": "GRAND CONC",
    "FASHION AVE": "7 AVE",
    "CENTRAL PARK W": "CENTRAL PARK W",
    "COLUMBUS AVE": "COLUMBUS AVE",
    "AMSTERDAM AVE": "AMSTERDAM AVE",
    "ROBERT F KENNEDY BR": "RFK BR",
    "TRIBOROUGH BR": "RFK BR",
    "ED KOCH QUEENSBORO BR": "QUEENSBORO BR",
    "HUGH L CAREY TUNL": "HUGH L CAREY TUNL",
    "BROOKLYN BATTERY TUNL": "HUGH L CAREY TUNL",
    "BKLYN BTRY TUNL": "HUGH L CAREY TUNL",
    "GW BR": "GEORGE WASHINGTON BR",
}


def normalize(name: str | None) -> str:
    """Canonical upper-case token string; empty string for None/blank."""
    if name is None:
        return ""
    s = str(name).upper().strip()
    if not s or s == "NAN":
        return ""
    s = _PUNCT.sub(" ", s)
    s = _ORDINAL.sub(r"\1", s)
    toks = []
    for t in _SPACES.split(s):
        if not t:
            continue
        t = _NUMBER_WORDS.get(t, t)
        t = _ABBR.get(t, t)
        toks.append(t)
    if toks and toks[0] == "THE":
        toks = toks[1:]
    out = " ".join(toks)
    return _ALIASES.get(out, out)


def display(name: str | None) -> str:
    """CSCL-style display text for signs: upper case, single spaces (e.g. 'W 60 ST')."""
    if name is None:
        return ""
    s = str(name).strip()
    if not s or s.upper() == "NAN":
        return ""
    return _SPACES.sub(" ", s.upper())


def core_tokens(norm: str) -> str:
    """Drop leading directionals and trailing bound suffixes for looser comparisons: 'E 60 ST' -> '60 ST'."""
    toks = norm.split()
    while toks and toks[0] in ("E", "W", "N", "S"):
        toks = toks[1:]
    while toks and toks[-1] in ("NB", "SB", "EB", "WB"):
        toks = toks[:-1]
    return " ".join(toks)
