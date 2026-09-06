"""Water-body ``kind`` classification (DATA_CONTRACTS §4) from planimetric feature codes, names and OSM tags.

Contract kinds: river, bay, ocean, lake, pond, canal, basin. Extension (documented in the terrain report):
``marsh`` for planimetric Wetland/Marsh (2640) — a tidal wetland surface that must *not* be flattened to
the water plane, and which is excluded from ``has_open_water``.
"""
from __future__ import annotations

import re

# NYC planimetric HYDROGRAPHY feature codes (CityOfNewYork/nyc-planimetrics Capture_Rules.md, section HYDROGRAPHY)
FEAT_CODE_KIND = {2600: "lake", 2610: "pond", 2620: "river", 2630: "river", 2640: "marsh", 2650: "beach", 2660: "bay"}
FEAT_CODE_LABEL = {2600: "Lake/Reservoir", 2610: "Pond", 2620: "River", 2630: "Stream", 2640: "Wetland/Marsh", 2650: "Beach/Shoreline", 2660: "Bay/Ocean"}
# HYDRO STRUCTURE feature codes (same document, section HYDRO STRUCTURE)
STRUCT_CODE_KIND = {2800: "pier", 2810: "jetty", 2820: "seawall"}

_NAME_RULES: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bOCEAN\b", re.I), "ocean"),
    (re.compile(r"\bCANAL\b", re.I), "canal"),
    (re.compile(r"\bBASIN\b", re.I), "basin"),
    (re.compile(r"\b(BAY|SOUND|INLET|CHANNEL|HARBOR|HARBOUR|COVE|NARROWS)\b", re.I), "bay"),
    (re.compile(r"\b(RIVER|KILL|KILLS|CREEK|STRAIT|BROOK|RUN)\b", re.I), "river"),
    (re.compile(r"\b(RESERVOIR|LAKE|MEER)\b", re.I), "lake"),
    (re.compile(r"\b(POND|POOL|WATER)\b", re.I), "pond"),
)
_UNNAMED = {"", "unset", "no name", "<null>", "null", "none", "marsh", "pond"}


def clean_name(name: str | None) -> str:
    """Normalise a planimetric name: placeholders become '', real names are title-cased per NYC usage."""
    if name is None:
        return ""
    n = str(name).strip()
    if n.lower() in _UNNAMED:
        return ""
    return n


def kind_from_planimetric(feat_code: int, name: str) -> str:
    """Kind from the feature code, refined by the name where the name is more specific (e.g. Gowanus CANAL is 2630)."""
    base = FEAT_CODE_KIND.get(int(feat_code), "")
    if not base:
        raise ValueError(f"unknown hydrography feature code {feat_code}")
    if base in ("marsh", "beach"):
        return base
    for pat, kind in _NAME_RULES:
        if pat.search(name or ""):
            # a name never turns open water into a lake/pond or vice versa
            if kind in ("lake", "pond") and base in ("river", "bay"):
                continue
            if kind in ("river", "bay", "ocean", "canal", "basin") and base in ("lake", "pond") and kind not in ("canal", "basin"):
                continue
            return kind
    return base


def kind_from_osm(tags: dict[str, str]) -> str:
    natural, water, waterway, landuse = tags.get("natural", ""), tags.get("water", ""), tags.get("waterway", ""), tags.get("landuse", "")
    name = tags.get("name", "")
    for pat, kind in _NAME_RULES:
        if pat.search(name):
            return kind
    if natural == "bay" or water in ("bay", "lagoon"):
        return "bay"
    if natural == "strait" or water in ("river", "stream", "canal", "strait", "oxbow"):
        return "canal" if water == "canal" else "river"
    if water in ("lake", "reservoir") or landuse == "reservoir":
        return "lake"
    if water in ("basin", "wastewater", "harbour", "lock") or landuse == "basin" or waterway == "dock":
        return "basin"
    if water in ("pond", "pool", "reflecting_pool", "fountain", "moat"):
        return "pond"
    if natural == "wetland":
        return "marsh"
    return "pond" if natural == "water" else "bay"


def is_open_water(kind: str) -> bool:
    return kind in ("river", "bay", "ocean", "lake", "pond", "canal", "basin")
