"""Cross-dataset de-duplication of props within 1.5 m.

The same physical object is published by more than one agency: a Citi Bike station is also an OSM
``amenity=bicycle_parking``; a LinkNYC kiosk stands where OSM still records the payphone it replaced; a
sheltered bike parking site appears in both the DOT shelter list and OSM. Two rows within
:data:`RADIUS_M` that belong to the same *dedupe group* are one object, and only the row from the more
authoritative source is kept.

Grouping, not blanket proximity, is what makes this safe: a hydrant 1 m from a tree is two real objects, so
hydrants and trees are never compared. Only the kinds listed in :data:`GROUPS` are compared across kinds;
every other kind is de-duplicated against itself (repeated rows for one object inside a single dataset,
e.g. two OSM nodes for the same lamp).

Authority order (:data:`PRIORITY`): the agency that owns the asset (DOT, DEP, MTA, Parks, Lyft/Citi Bike,
OTI planimetrics) beats OpenStreetMap, and OpenStreetMap beats a rule-generated placement.

:data:`CROSS_SOURCE_RULES` adds a second, narrower pass for the one case where 1.5 m is too tight: two
*inventories* of the same objects, taken years apart by different methods, whose positions disagree by more
than the width of the object. It is deliberately restricted to a named pair of datasets so that widening a
radius can never merge two rows of the *same* source — a park mapped tree by tree has trees 4 m apart
(15.2 % of the OSM nodes have another OSM node within 5 m) and the census has 7.9 % of its own trees within
5 m of the next one, so a blanket 5 m radius on the tree group would delete about 51,000 real census trees.
"""
from __future__ import annotations

import logging
from collections import Counter
from dataclasses import dataclass

import numpy as np
from scipy.spatial import cKDTree

log = logging.getLogger("nycsim.furniture.dedupe")

RADIUS_M = 1.5

# kind name -> dedupe group. Kinds absent from this map form a group of their own.
GROUPS: dict[str, str] = {
    "bike_rack": "bike_parking",
    "citibike_dock": "bike_parking",
    "bike_shelter": "bike_parking",
    "linknyc": "phone_kiosk",
    "payphone": "phone_kiosk",
}

# dataset_id -> priority (lower wins). Anything not listed is treated as an authority dataset.
PRIORITY: dict[str, int] = {
    "osm_newyork_pbf": 50,
}
RULE_PRIORITY = 100
AUTHORITY_PRIORITY = 10


@dataclass(frozen=True)
class CrossSourceRule:
    """Drop rows of ``drop_dataset`` within ``radius_m`` of a row of ``keep_dataset``, inside one dedupe group.

    Only those two datasets are compared, so the radius says nothing about how close two rows of the same
    source may stand. ``basis`` records how the radius was measured, because a round number chosen by eye is
    exactly what this project does not ship.
    """
    group: str
    keep_dataset: str
    drop_dataset: str
    radius_m: float
    basis: str


# The 2015 census and the OSM extract both record street trees, so a tree mapped in both would otherwise be
# planted twice. The radius is measured, not chosen: for every OSM tree node the distance to the nearest
# census tree was computed, and compared against a control of the same points displaced 20 m in a random
# direction (same local census density, no true correspondence). The shell 4.5–5.0 m still captures 9.6 %
# more pairs than chance; the shell 5.0–5.5 m captures 24 % *fewer*, and the excess over chance peaks at
# exactly 5.0 m (15,319 pairs). 5 m is also below the 10th percentile of the census's own tree-to-tree
# spacing (5.37 m), so the radius cannot reach past one census tree to the next.
CROSS_SOURCE_RULES: tuple[CrossSourceRule, ...] = (
    CrossSourceRule(group="tree", keep_dataset="street_trees_2015", drop_dataset="osm_newyork_pbf", radius_m=5.0,
                    basis="nearest-census-tree distance of every OSM tree node against a 20 m-displaced control; "
                          "excess over chance peaks at 5.0 m and the marginal shell turns negative above it"),
)


def priority_of(dataset_ids: list[str], source: np.ndarray) -> np.ndarray:
    p = np.full(len(dataset_ids), AUTHORITY_PRIORITY, dtype=np.int32)
    for i, d in enumerate(dataset_ids):
        if source[i] == 1 or d.startswith("rule:"):
            p[i] = RULE_PRIORITY
        else:
            p[i] = PRIORITY.get(d, AUTHORITY_PRIORITY)
    return p


def _apply_cross_source(rule: CrossSourceRule, group: np.ndarray, dataset_id: list[str], x: np.ndarray,
                        y: np.ndarray, keep: np.ndarray) -> dict:
    """Apply one :class:`CrossSourceRule` to the rows still kept; returns the rule's report."""
    ds = np.asarray(dataset_id, dtype=object)
    in_group = (group == rule.group) & keep
    a = np.flatnonzero(in_group & (ds == rule.keep_dataset))
    b = np.flatnonzero(in_group & (ds == rule.drop_dataset))
    rep = {"group": rule.group, "kept_dataset": rule.keep_dataset, "dropped_dataset": rule.drop_dataset,
           "radius_m": rule.radius_m, "basis": rule.basis, "candidates": int(b.size),
           "against": int(a.size), "rows_dropped": 0}
    if a.size == 0 or b.size == 0:
        return rep
    tree = cKDTree(np.column_stack([x[a], y[a]]))
    d, _ = tree.query(np.column_stack([x[b], y[b]]), k=1, distance_upper_bound=rule.radius_m, workers=1)
    hit = np.isfinite(d)
    keep[b[hit]] = False
    rep["rows_dropped"] = int(hit.sum())
    log.info("cross-source dedupe %s: dropped %d of %d %s rows within %.2f m of a %s row",
             rule.group, rep["rows_dropped"], b.size, rule.drop_dataset, rule.radius_m, rule.keep_dataset)
    return rep


def dedupe(cols: dict, kind_names: dict[int, str], radius_m: float = RADIUS_M,
           cross_source_rules: tuple[CrossSourceRule, ...] = CROSS_SOURCE_RULES) -> tuple[np.ndarray, dict]:
    """Return a boolean keep-mask over the prop rows and a report of what was dropped.

    Rows are compared only inside their dedupe group; within a group the row with the lower priority value
    (more authoritative source) survives, ties broken by kind id then row order, so the result is deterministic.
    :data:`CROSS_SOURCE_RULES` then runs over the survivors, comparing one named pair of datasets at its own
    measured radius.
    """
    kind = np.asarray(cols["kind"], dtype=np.int32)
    x = np.asarray(cols["x"], dtype=np.float64)
    y = np.asarray(cols["y"], dtype=np.float64)
    dataset_id = list(cols["dataset_id"])
    prio = priority_of(dataset_id, np.asarray(cols["source"], dtype=np.int8))

    group = np.array([GROUPS.get(kind_names.get(int(k), str(k)), kind_names.get(int(k), str(k))) for k in kind], dtype=object)
    keep = np.ones(len(x), dtype=bool)
    dropped: Counter = Counter()
    pairs_total = 0

    for g in sorted(set(group.tolist())):
        idx = np.flatnonzero(group == g)
        if idx.size < 2:
            continue
        tree = cKDTree(np.column_stack([x[idx], y[idx]]))
        pairs = tree.query_pairs(radius_m, output_type="ndarray")
        if pairs.size == 0:
            continue
        pairs_total += len(pairs)
        gi = idx[pairs[:, 0]]
        gj = idx[pairs[:, 1]]
        # rank: (priority, kind, row index) — the smaller rank survives
        rank_i = np.column_stack([prio[gi], kind[gi], gi])
        rank_j = np.column_stack([prio[gj], kind[gj], gj])
        j_worse = np.zeros(len(gi), dtype=bool)
        decided = np.zeros(len(gi), dtype=bool)
        for c in range(3):
            new = (rank_i[:, c] != rank_j[:, c]) & ~decided
            j_worse |= new & (rank_j[:, c] > rank_i[:, c])
            decided |= new
        loser = np.where(j_worse, gj, gi)
        winner = np.where(j_worse, gi, gj)
        # process pairs in a stable order so an already-dropped row cannot drop anyone else
        order = np.lexsort((loser, winner))
        for w, l in zip(winner[order], loser[order]):
            if keep[w] and keep[l]:
                keep[l] = False
                dropped[(g, kind_names.get(int(kind[w]), "?"), dataset_id[w],
                         kind_names.get(int(kind[l]), "?"), dataset_id[l])] += 1

    n_generic = int((~keep).sum())
    cross = [_apply_cross_source(r, group, dataset_id, x, y, keep) for r in cross_source_rules]

    n_drop = int((~keep).sum())
    report = {
        "radius_m": radius_m,
        "pairs_within_radius": int(pairs_total),
        "rows_dropped": n_drop,
        "rows_dropped_generic": n_generic,
        "rows_dropped_cross_source": n_drop - n_generic,
        "rows_kept": int(keep.sum()),
        "by_pair": [{"group": g, "kept_kind": kk, "kept_dataset": kd, "dropped_kind": dk, "dropped_dataset": dd,
                     "count": int(c)} for (g, kk, kd, dk, dd), c in sorted(dropped.items(), key=lambda kv: -kv[1])],
        "cross_source": cross,
    }
    log.info("dedupe: %d rows dropped of %d (%d generic within %.2f m, %d cross-source)",
             n_drop, len(x), n_generic, radius_m, n_drop - n_generic)
    return keep, report
