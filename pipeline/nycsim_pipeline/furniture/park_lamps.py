"""A lamp standing in a park is not the lamp standing on Third Avenue.

The lamp rule (:mod:`.rules`) walks the *road* network, so every pole it places is the NYC DOT
standard: an octagonal steel pole with a cobra head on a 12 ft davit arm, which is right for a
street and wrong for a park path.  The park drives of Central Park, Prospect Park and Riverside
Park are roads in the CSCL centreline and get lamps from that rule like any other street -- and
Central Park's drives carry the cast-iron post-top lantern, not a cobra head.  Bethesda Terrace
made the fault visible: the verification camera there stands 2.2 m behind
``prop_lamp_cobra_davit_6``, a DOT davit on the terrace of a park whose lighting is a listed part
of the landscape (docs/DEVIATIONS.md J56).

**This module is a rule, not a measurement.**  It says: a lamp whose fixture nothing in the data
identifies, standing on pedestrian park ground, is a post-top park lamp.  Two things it will not
touch:

* a lamp whose fixture *was* read from its own OSM tags (``variant`` already 1, 3 or 4 from
  :func:`.datasets.lamp_variant` on a ``source = 0`` row).  A measurement outranks a rule even when
  the rule would look better;
* a lamp on a road of highway class.  The Belt Parkway, the Grand Central Parkway, the Cross Island
  Parkway and the Richmond Parkway all run through park land and hold 875 of these lamps between
  them; a parkway is lit with cobra heads and high masts, and the surrounding grass does not change
  that.

The polygons that count are the four open-space classes a person walks on -- ``park_ground``,
``grass_field``, ``recreation`` and ``golf``.  Deliberately excluded: ``greenstreet`` (the planted
traffic islands at junctions, lit by the street they sit in), ``ballfield``, ``court``, ``track``
and ``pool`` (sports lighting is a floodlight mast, a fixture this build has no mesh for),
``cemetery``, and ``vacant``.
"""
from __future__ import annotations

import logging

import numpy as np

from ..paths import PROCESSED
from ..roads import schema as S

log = logging.getLogger("nycsim.furniture.park_lamps")

SURFACES = PROCESSED / "parks" / "surfaces.parquet"

#: Rule name written into ``dataset_id`` of every row this module re-fixtures.
RULE_ID = "rule:park_post_lamp"

#: Open-space classes whose lighting is pedestrian-scale.
WALKABLE_KINDS = ("park_ground", "grass_field", "recreation", "golf")

#: Narrowest a polygon may be, across the short side of its own minimum rotated rectangle, and still
#: count as park *interior* rather than a planted street median.
#:
#: NYC Parks owns the avenue malls, so they arrive in this file as ``park_ground`` like any lawn --
#: and a lamp on the Park Avenue mall is a street lamp lighting Park Avenue.  Measured over the
#: named strips: Tudor Malls 2.1 m, Kings Highway Malls 2.7 m, Flatbush Malls 4.3 m, Broadway Malls
#: 6.7 m, Park Avenue Malls 7.2 m, Ocean Parkway Malls 10.1 m -- against Riverside Park 27.4 m,
#: Central Park 34.1 m and Grand Army Plaza 46.4 m.  15 m falls in the empty band between the two
#: groups and is a physical statement: a strip you cannot stand 7.5 m from every edge of is a
#: median.  It keeps the broader linear parks that really are walkable -- Crotona Parkway Malls
#: 17.5 m, Catherine Slip 18.6 m, Mount Eden Malls 24.6 m.
MIN_PARK_WIDTH_M = 15.0

#: ``street_lamp`` variant this rule assigns: the post-top twin park lamp.
PARK_VARIANT = 3

#: Variants a row must be in for the rule to touch it: 0 (nothing known) or 1 (the citywide DOT
#: default the road rule stamps on every pole it places).
OVERRIDABLE = (0, 1)


def park_ground():
    """The walkable open-space polygons as a shapely STRtree, or ``None`` when the file is absent."""
    if not SURFACES.is_file():
        return None
    import pandas as pd
    from shapely import STRtree, wkb

    df = pd.read_parquet(SURFACES, columns=["kind_name", "name", "geometry"])
    df = df[df["kind_name"].isin(WALKABLE_KINDS)]
    if not len(df):
        return None
    geoms = [wkb.loads(b) for b in df["geometry"]]
    names = df["name"].astype(str).to_numpy()
    wide = [i for i, g in enumerate(geoms) if short_side_m(g) >= MIN_PARK_WIDTH_M]
    if not wide:
        return None
    return STRtree([geoms[i] for i in wide]), names[wide]


def short_side_m(geom) -> float:
    """The short side of a polygon's minimum rotated rectangle, in metres.

    The coordinates are NYC_TM, so this is metres without a projection step; a degenerate or empty
    geometry answers 0.0 and is therefore never park interior.
    """
    try:
        rect = geom.minimum_rotated_rectangle
        xs, ys = rect.exterior.coords.xy
    except (AttributeError, ValueError, IndexError):
        return 0.0
    sides = [((xs[i + 1] - xs[i]) ** 2 + (ys[i + 1] - ys[i]) ** 2) ** 0.5 for i in range(4)]
    return float(min(sides[0], sides[1]))


#: CSCL ``rw_type`` codes whose lighting stays a cobra head or a high mast whatever it drives past.
#: The lamp rule only places on :data:`.rules.LIT_RW_TYPES` -- street, highway, bridge and alley --
#: so in practice this excludes the parkways (highway) and the bridges that carry them; tunnel and
#: ramp are named for completeness, not because a pole exists on one today.
HIGHWAY_RW_TYPES = (S.RW_HIGHWAY, S.RW_BRIDGE, S.RW_TUNNEL, S.RW_RAMP)

#: CSCL ``nonped`` value for a segment pedestrians are prohibited from.
#:
#: ``rw_type`` alone lets the parkway mainlines through: measured, **1,384 vehicles-only segments are
#: typed as plain street**, and the ten commonest names among all 10,160 of them are Long Island
#: Expy, Belt Pkwy, Cross Bronx Expy, Grand Central Pkwy, BQE, Van Wyck Expy, Gowanus Expy, FDR
#: Drive, Bruckner Expy and Major Deegan Expy -- 10,159 of the 10,160 drivable.  So this flag is
#: read as the physical question the rule is actually asking: may a person walk here?
#:
#: The other non-empty value, ``D`` (3,983 segments, 2,558 of them not drivable), is the opposite
#: signal and is deliberately *not* excluded: Clove Lakes Park Path, the Hudson River Greenway,
#: the Randalls Island and Bronx River Greenways, the East River Esplanade and Central Park's West
#: Drive are all ``D``.  Neither meaning is taken from a data dictionary this build does not hold --
#: both are read off the segments that carry them.
NONPED_VEHICLES_ONLY = "V"


def highway_mask_from_attrs(attrs) -> tuple[np.ndarray, int]:
    """``(mask, rows with no road class recorded)`` from the ``attrs`` JSON of every row.

    Only :func:`.rules.street_lamps` writes ``rw_type`` -- an OSM lamp node carries no road class at
    all, so its entry is False and it is counted as unknown rather than quietly treated as a street.
    """
    import json as _json

    mask = np.zeros(len(attrs), dtype=bool)
    unknown = 0
    for i, raw in enumerate(attrs):
        try:
            d = _json.loads(raw or "{}")
        except (TypeError, ValueError):
            d = {}
        if not isinstance(d, dict):
            d = {}
        rw = d.get("rw_type")
        if rw is None:
            unknown += 1
            continue
        mask[i] = (int(rw) in HIGHWAY_RW_TYPES
                   or str(d.get("nonped") or "").upper() == NONPED_VEHICLES_ONLY)
    return mask, unknown


def apply(cols: dict, lamp_kind_id: int, *, highway_mask: np.ndarray | None = None) -> dict:
    """Re-fixture the park lamps in ``cols`` in place; returns what it did, for the build summary.

    ``highway_mask`` is a per-row boolean, True where the lamp was placed against a road of highway
    or bridge class, or one pedestrians are prohibited from, and must keep its cobra head.  ``None`` means no road class was carried through,
    in which case nothing is excluded on that ground and the report says so.
    """
    from shapely import points

    kind = np.asarray(cols["kind"], dtype=np.int64)
    variant = np.asarray(cols["variant"], dtype=np.int16).copy()
    rows = np.flatnonzero(kind == lamp_kind_id)
    report: dict = {"rule": RULE_ID, "lamps": int(rows.size), "moved": 0,
                    "walkable_kinds": list(WALKABLE_KINDS), "variant": PARK_VARIANT,
                    "min_park_width_m": MIN_PARK_WIDTH_M,
                    "road_class_excluded": 0,
                    "note": "a rule, not a measurement: an unidentified lamp on walkable park "
                            "ground is a post-top park lamp"}
    if rows.size == 0:
        return report
    built = park_ground()
    if built is None:
        report["skipped"] = f"{SURFACES} absent"
        return report
    tree, names = built
    cand = rows[np.isin(variant[rows], OVERRIDABLE)]
    report["overridable"] = int(cand.size)
    if cand.size == 0:
        return report
    x = np.asarray(cols["x"], dtype=np.float64)[cand]
    y = np.asarray(cols["y"], dtype=np.float64)[cand]
    hit = tree.query(points(x, y), predicate="within")
    if hit.size == 0:
        report["inside_park_ground"] = 0
        return report
    inside = np.unique(hit[0])
    report["inside_park_ground"] = int(inside.size)
    target = cand[inside]
    if highway_mask is not None:
        hw = np.asarray(highway_mask, dtype=bool)[target]
        report["road_class_excluded"] = int(hw.sum())
        target = target[~hw]
    variant[target] = PARK_VARIANT
    cols["variant"] = variant
    ds = list(cols["dataset_id"])
    for i in target:
        ds[int(i)] = f"{ds[int(i)]}+{RULE_ID}"
    cols["dataset_id"] = ds
    report["moved"] = int(target.size)
    # Counted over the rows the rule actually moved, not over the polygon hits: the parkways run
    # through park land and their lamps are inside these polygons but excluded by road class, so a
    # tally taken before the exclusion would name Belt Parkway under a rule that never touched it.
    moved_set = set(int(i) for i in target)
    first: dict[int, int] = {}
    for a, b in zip(hit[0], hit[1]):
        first.setdefault(int(cand[int(a)]), int(b))
    seen: dict[str, int] = {}
    for row, gi in first.items():
        if row not in moved_set:
            continue
        n = str(names[gi]) or "(unnamed)"
        seen[n] = seen.get(n, 0) + 1
    report["by_park"] = dict(sorted(seen.items(), key=lambda kv: -kv[1])[:20])
    report["by_park_note"] = "counted over the lamps this rule moved, after the road-class exclusion"
    log.info("park post lamp rule: %d lamps overridable, %d inside walkable park ground, "
             "%d excluded by road class, %d moved to variant %d",
             cand.size, inside.size, report["road_class_excluded"], report["moved"], PARK_VARIANT)
    return report
