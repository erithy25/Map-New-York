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
"""
from __future__ import annotations

import logging
from collections import Counter

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


def priority_of(dataset_ids: list[str], source: np.ndarray) -> np.ndarray:
    p = np.full(len(dataset_ids), AUTHORITY_PRIORITY, dtype=np.int32)
    for i, d in enumerate(dataset_ids):
        if source[i] == 1 or d.startswith("rule:"):
            p[i] = RULE_PRIORITY
        else:
            p[i] = PRIORITY.get(d, AUTHORITY_PRIORITY)
    return p


def dedupe(cols: dict, kind_names: dict[int, str], radius_m: float = RADIUS_M) -> tuple[np.ndarray, dict]:
    """Return a boolean keep-mask over the prop rows and a report of what was dropped.

    Rows are compared only inside their dedupe group; within a group the row with the lower priority value
    (more authoritative source) survives, ties broken by kind id then row order, so the result is deterministic.
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

    n_drop = int((~keep).sum())
    report = {
        "radius_m": radius_m,
        "pairs_within_radius": int(pairs_total),
        "rows_dropped": n_drop,
        "rows_kept": int(keep.sum()),
        "by_pair": [{"group": g, "kept_kind": kk, "kept_dataset": kd, "dropped_kind": dk, "dropped_dataset": dd,
                     "count": int(c)} for (g, kk, kd, dk, dd), c in sorted(dropped.items(), key=lambda kv: -kv[1])],
    }
    log.info("dedupe: %d rows dropped of %d (%d pairs within %.2f m)", n_drop, len(x), pairs_total, radius_m)
    return keep, report
