"""OpenStreetMap heights and storey counts joined onto the New Jersey buildings (deviation B11a).

The New Jersey table is built from FEMA/ORNL USA Structures, whose heights are measured off aerial
imagery stamped ``2013-08-15`` on 163,444 of the 231,382 rows.  Measured against the published
architectural heights in ``nj_reference_heights.json``, that source is short by a median **66.41 m
(54.4 %)** on the twenty-five Jersey City towers that already stood when the imagery was flown, and
not one of the thirty-nine reference towers carrying a source height is within 10 % of its published
figure.  The failure is a measurement failure, not only a coverage gap.

The OpenStreetMap extract already in this repository (``data/processed/osm/buildings_nj.parquet``,
ODbL) carries **417 ``height`` tags and 6,199 ``building:levels`` tags** over New Jersey.  This
module joins them onto the USA Structures footprints and uses them where they are better.  What
"better" means is decided by measurement and stated in full below, not by preferring the newer
source on principle.

The three rules, and the evidence for each
------------------------------------------
**1. A matched OSM ``height`` tag replaces the source height, always.**  A tag on a footprint is a
statement somebody made about *that building*; a USA Structures height is a LiDAR return off a
2013 image, which for a tower finished in 2021 is a measurement of whatever stood there before.
On the 41 accepted matches carrying a ``height`` tag the source is short in every height band —
−0.50 m (−5.0 %) below 20 m, −7.14 m (−12.3 %) between 40 and 80 m, −40.44 m (−33.5 %) above 80 m —
so taking the tag costs nothing at low rise and recovers the towers.  The row keeps ``HEIGHT_REAL``:
the tag is a real height, and ``height_source`` says which real source it came from.

**2. A matched ``building:levels`` tag is turned into a height only where the source height cannot
carry the storeys the tag counts** — where the storey count implied by the source height is at least
:data:`LEVELS_SHORTFALL_STOREYS` below the tagged one.  Evidence:

* The source and the tags mostly agree.  Over the 3,084 accepted matches carrying a usable levels
  tag, the storey count implied by the source height equals the tagged one on 1,849 (60.0 %) and is
  within one storey on 2,838 (92.0 %).  Replacing a measurement with an inference across that
  agreement would trade a real number for a derived one and buy nothing.
* Where they disagree, the disagreement is one-sided: 208 rows are short by two storeys or more
  against 38 rows over by two or more, 5.5 : 1.  That asymmetry is the signature of the source
  truncating tall buildings.  It is also why the rule is one-sided: a levels tag *lower* than the
  source height is usually OpenStreetMap describing a podium rather than the tower over it.  The
  outline named "99 Hudson" in this extract carries ``height=27`` and ``levels=7``, where the real
  99 Hudson Street is 76 storeys and 271 m; a symmetric rule would pull that tower *down*.
* Two storeys rather than one, because a one-storey disagreement is inside the rounding band of the
  storey formula itself and inside the spread of real storey heights: on the 28 matched footprints
  carrying both tags the measured storey height ranges 2.48–3.71 m for residential against the 3.0 m
  the occupancy table assumes.  Held out against those 28, "short by ≥ 1" and "short by ≥ 2" score
  identically (median |error| 0.57 m below 20 m and 12.30 m above 40 m for both), while "≥ 1" would
  rewrite 824 heights instead of 189.  Both counts are recomputed on every run and written into the
  summary as ``levels_rule_would_change_at_1_storey`` / ``_at_2_storeys`` / ``_at_3_storeys``.

A height derived this way is **inferred**: the row carries ``HEIGHT_INFERRED`` and loses
``HEIGHT_REAL``, even where the source height it replaces was real.  That is a deliberate trade of
a fidelity bit for accuracy, and it is visible in the bitfield rather than hidden.

**3. Where the source published no height at all** — the 60,835 rows whose height is a
neighbour median — any OSM evidence wins, tag or levels, because there is no measurement to
displace.  A neighbour median is an inference about the block; a levels tag is an observation of the
building.

The storey height
-----------------
A levels tag needs metres per storey.  New Jersey has no PLUTO building class, so this uses
``nj_tiles._OCC_FLOORS`` — the USA Structures occupancy class table the stage already uses to derive
floor counts *from* heights, whose numbers are the same as the New York class table in
``buildings/infer.py``.  Using the same table in both directions makes the two derivations exact
inverses: ``floors_from_height(height_from_levels(L)) == L`` for every L, so a building's published
floor count and its published height never contradict each other.  The alternative — fitting new
storey heights to the 28 footprints that carry both tags — was refused: the sample is 12 residential,
9 unclassified and 4 commercial rows, and its measured medians (2.78, 3.33 and 4.53 m against the
table's 3.0, 3.0 and 3.9) are three numbers from a sample too small to move a table that 231,382
buildings key off.  Those medians are reported in the summary as a check on the table, not folded
into it.

Matching an OSM way to a USA Structures polygon
-----------------------------------------------
They are not the same geometry: one is hand-traced, the other is machine-extracted from imagery, and
the two datasets disagree about where a building ends.  A match is accepted only when the two
polygons cover each other — intersection over union at or above :data:`MATCH_MIN_IOU` — and every
accepted pair is required to be one-to-one.

0.5 is not a tuned number.  If two polygons A and B each reach IoU ≥ 0.5 against the same polygon C
then |A∩C| ≥ 0.5·|A∪C| ≥ 0.5·|C| and likewise for B, so A and B must overlap by at least half of C:
two building outlines that do not overlap cannot both claim one USA Structures polygon.  Measured
over the whole join, the contested count collapses towards that bound — 1,546 New Jersey polygons
are claimed twice at 0.40, 818 at 0.42, 206 at 0.45, 32 at 0.47 and 8 at 0.49 and 0.50.  It does not
reach zero, because the premise fails for the handful of OpenStreetMap outlines that really do
overlap each other; those 16 pairs are **dropped**, not resolved, and counted in the match stats.

Containment is deliberately *not* enough: the Two Gateway Center tower sits wholly inside a USA
Structures polygon covering its whole superblock (97.9 % of the OSM outline covered, IoU 0.079,
centroid 101.5 m away), and accepting that would raise a whole block to 83 m.
"""
from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import polars as pl
import shapely

from ..paths import PROCESSED
from . import schema as S

log = logging.getLogger("nycsim.buildings.nj.osm")

OSM_BUILDINGS_NJ = PROCESSED / "osm" / "buildings_nj.parquet"
OSM_SOURCE_ID = "osm_newyork_pbf"
OSM_LICENSE = "ODbL 1.0, © OpenStreetMap contributors"

MATCH_MIN_IOU = 0.5           # see the module docstring: the point where the assignment is one-to-one
LEVELS_SHORTFALL_STOREYS = 2  # storeys the source must fall short by before a levels tag overrides it
MIN_OSM_LEVELS = 1
MAX_OSM_LEVELS = 200
MIN_OSM_HEIGHT_M = 1.0
MAX_OSM_HEIGHT_M = 600.0      # nj_tiles.MAX_PLAUSIBLE_HEIGHT_M

# ``height_mode`` — which rule set the published height on a row.  Reported per row so a consumer can
# separate a measurement from a tag from a derivation without decoding the fidelity bitfield.
MODE_SOURCE = 0        # the USA Structures height (or its neighbour median) was kept
MODE_OSM_HEIGHT = 1    # replaced by an OSM ``height`` tag on a matched footprint      -> HEIGHT_REAL
MODE_OSM_LEVELS = 2    # derived from an OSM ``building:levels`` tag x the storey table -> HEIGHT_INFERRED


def load_osm_buildings(path: Path | None = None) -> tuple[pl.DataFrame, np.ndarray]:
    """Read the New Jersey OpenStreetMap building extract and return its rows and geometries."""
    p = path or OSM_BUILDINGS_NJ
    if not p.exists():
        raise FileNotFoundError(
            f"{p} is required for the New Jersey height join (deviation B11a); run the osm extract stage")
    df = pl.read_parquet(p, columns=["osm_id", "osm_type", "name", "building", "height", "levels",
                                     "min_height", "geometry"])
    geoms = shapely.from_wkb(df["geometry"].to_numpy())
    return df.drop("geometry"), geoms


def match_footprints(nj_geoms: np.ndarray, osm_geoms: np.ndarray,
                     min_iou: float = MATCH_MIN_IOU) -> tuple[np.ndarray, np.ndarray, dict]:
    """One-to-one footprint match by intersection over union.

    Returns ``(osm_row, iou, stats)``, both arrays indexed by New Jersey row: ``osm_row`` is the index
    into ``osm_geoms`` of the matched outline or ``-1``, and ``iou`` is that pair's overlap or 0.0.

    A pair is accepted when the two polygons cover each other at ``min_iou`` or better.  Where two
    accepted pairs claim the same polygon on either side the *pair* is dropped, not resolved: a
    contested match is one this stage cannot defend, and there are few enough of them that keeping
    them would buy nothing.  The count is returned so the drop is visible.
    """
    n_nj, n_osm = len(nj_geoms), len(osm_geoms)
    nj_area = shapely.area(nj_geoms)
    osm_area = shapely.area(osm_geoms)
    tree = shapely.STRtree(nj_geoms)
    li, ri = tree.query(osm_geoms, predicate="intersects")      # li -> osm row, ri -> nj row
    inter = shapely.area(shapely.intersection(osm_geoms[li], nj_geoms[ri]))
    union = osm_area[li] + nj_area[ri] - inter
    iou = inter / np.maximum(union, 1e-9)

    stats: dict = {
        "nj_footprints": int(n_nj),
        "osm_footprints": int(n_osm),
        "candidate_pairs_intersecting": int(len(li)),
        "min_iou": float(min_iou),
    }
    keep = iou >= min_iou
    li_k, ri_k, iou_k = li[keep], ri[keep], iou[keep]
    stats["pairs_at_or_above_min_iou"] = int(keep.sum())

    # one-to-one: drop any pair whose New Jersey polygon or OpenStreetMap outline is claimed twice
    nj_claims = np.bincount(ri_k, minlength=n_nj)
    osm_claims = np.bincount(li_k, minlength=n_osm)
    contested = (nj_claims[ri_k] > 1) | (osm_claims[li_k] > 1)
    stats["pairs_dropped_contested"] = int(contested.sum())
    stats["nj_footprints_contested"] = int((nj_claims > 1).sum())
    stats["osm_footprints_contested"] = int((osm_claims > 1).sum())
    li_k, ri_k, iou_k = li_k[~contested], ri_k[~contested], iou_k[~contested]

    osm_row = np.full(n_nj, -1, dtype=np.int64)
    out_iou = np.zeros(n_nj, dtype=np.float64)
    osm_row[ri_k] = li_k
    out_iou[ri_k] = iou_k
    stats["matched"] = int(len(ri_k))
    stats["match_rate_pct"] = round(100.0 * len(ri_k) / max(n_nj, 1), 3)
    # how close the runners-up came, so "one-to-one" is not taken on trust
    best = np.zeros(n_nj)
    np.maximum.at(best, ri, iou)
    unmatched_with_a_candidate = (osm_row < 0) & (best > 0)
    stats["nj_unmatched_but_overlapping_an_osm_outline"] = int(unmatched_with_a_candidate.sum())
    if unmatched_with_a_candidate.any():
        stats["best_iou_of_the_unmatched_median"] = round(float(np.median(best[unmatched_with_a_candidate])), 3)
    stats["iou_percentiles_of_accepted"] = (
        {str(q): round(float(v), 3) for q, v in zip((5, 25, 50, 75, 95), np.percentile(iou_k, [5, 25, 50, 75, 95]))}
        if len(iou_k) else {})
    return osm_row, out_iou, stats


def floors_from_height(height: np.ndarray, floor_h: np.ndarray, ground_floor_h: np.ndarray) -> np.ndarray:
    """Storeys implied by a height: the storey rule ``nj_tiles.resolve_attributes`` publishes."""
    fl = np.where(height <= ground_floor_h + 0.5 * floor_h, 1, 1 + np.rint((height - ground_floor_h) / floor_h))
    return np.clip(fl, 1, 200).astype(np.int32)


def height_from_levels(levels: np.ndarray, floor_h: np.ndarray, ground_floor_h: np.ndarray) -> np.ndarray:
    """Height implied by a storey count.  Exact inverse of :func:`floors_from_height`."""
    return ground_floor_h + np.maximum(levels - 1.0, 0.0) * floor_h


def resolve_heights(source_height: np.ndarray, source_is_real: np.ndarray, osm_row: np.ndarray,
                    osm_height: np.ndarray, osm_levels: np.ndarray,
                    floor_h: np.ndarray, ground_floor_h: np.ndarray,
                    shortfall_storeys: int = LEVELS_SHORTFALL_STOREYS,
                    ) -> tuple[np.ndarray, np.ndarray, dict]:
    """Apply the three rules of the module docstring.  Returns ``(height, mode, stats)``.

    ``source_height`` is the height the stage would publish without this join (source value where
    the source has one, neighbour median where it does not); ``source_is_real`` marks the former.
    ``osm_height`` / ``osm_levels`` are indexed like ``osm_row`` — the tag arrays of the OSM table.
    """
    n = len(source_height)
    matched = osm_row >= 0
    height = source_height.astype(np.float64).copy()
    mode = np.full(n, MODE_SOURCE, dtype=np.int8)

    tag_h = np.full(n, np.nan)
    tag_l = np.full(n, np.nan)
    tag_h[matched] = osm_height[osm_row[matched]]
    tag_l[matched] = osm_levels[osm_row[matched]]
    has_tag_h = matched & np.isfinite(tag_h) & (tag_h >= MIN_OSM_HEIGHT_M) & (tag_h < MAX_OSM_HEIGHT_M)
    has_tag_l = matched & np.isfinite(tag_l) & (tag_l >= MIN_OSM_LEVELS) & (tag_l <= MAX_OSM_LEVELS)

    # rule 1 — a real tag on a matched footprint
    height[has_tag_h] = tag_h[has_tag_h]
    mode[has_tag_h] = MODE_OSM_HEIGHT

    # rule 2/3 — a levels derivation, where the source cannot carry the storeys or never measured any
    derived = height_from_levels(np.where(has_tag_l, tag_l, 1.0), floor_h, ground_floor_h)
    implied = floors_from_height(source_height, floor_h, ground_floor_h)
    short = implied - np.where(has_tag_l, tag_l, implied)
    use_levels = (has_tag_l & ~has_tag_h
                  & ((short <= -shortfall_storeys) | ~source_is_real)
                  & np.isfinite(derived) & (derived >= MIN_OSM_HEIGHT_M) & (derived < MAX_OSM_HEIGHT_M))
    height[use_levels] = derived[use_levels]
    mode[use_levels] = MODE_OSM_LEVELS

    changed = mode != MODE_SOURCE
    d = height[changed] - source_height[changed]
    stats = {
        "matched": int(matched.sum()),
        "matched_with_a_height_tag": int(has_tag_h.sum()),
        "matched_with_a_levels_tag": int(has_tag_l.sum()),
        "matched_with_both_tags": int((has_tag_h & has_tag_l).sum()),
        "height_from_osm_tag": int((mode == MODE_OSM_HEIGHT).sum()),
        "height_from_osm_levels": int((mode == MODE_OSM_LEVELS).sum()),
        "height_kept_from_source": int((mode == MODE_SOURCE).sum()),
        "levels_rule_shortfall_storeys": int(shortfall_storeys),
        "levels_overrode_a_real_source_height": int((use_levels & source_is_real).sum()),
        "levels_filled_an_inferred_source_height": int((use_levels & ~source_is_real).sum()),
        "tag_overrode_a_real_source_height": int((has_tag_h & source_is_real).sum()),
        "rows_that_grew": int((d > 0).sum()) if len(d) else 0,
        "rows_that_shrank": int((d < 0).sum()) if len(d) else 0,
        "median_change_m": round(float(np.median(d)), 2) if len(d) else 0.0,
        "largest_increase_m": round(float(d.max()), 2) if len(d) else 0.0,
        "largest_decrease_m": round(float(d.min()), 2) if len(d) else 0.0,
        # what the discarded alternative would have done, so the choice of 2 storeys is auditable
        "levels_rule_would_change_at_1_storey": int((has_tag_l & ~has_tag_h & (short <= -1)).sum()),
        "levels_rule_would_change_at_2_storeys": int((has_tag_l & ~has_tag_h & (short <= -2)).sum()),
        "levels_rule_would_change_at_3_storeys": int((has_tag_l & ~has_tag_h & (short <= -3)).sum()),
        "storey_disagreement_short_by_2_or_more": int((has_tag_l & (short <= -2)).sum()),
        "storey_disagreement_over_by_2_or_more": int((has_tag_l & (short >= 2)).sum()),
        "storey_agreement_exact": int((has_tag_l & (short == 0)).sum()),
        "storey_agreement_within_1": int((has_tag_l & (np.abs(short) <= 1)).sum()),
    }
    return height, mode, stats


def height_sources(mode: np.ndarray, source_is_real: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """``(height_source, height_is_real)`` for the published height, given the rule that set it.

    ``HEIGHT_REAL`` belongs to a measurement or to a tag somebody wrote about the building.  A height
    computed from a storey count is not one, whatever the storey count is worth, so ``MODE_OSM_LEVELS``
    is inferred even where it replaced a real source height.
    """
    src = np.where(mode == MODE_OSM_HEIGHT, S.SRC_OSM_HEIGHT,
                   np.where(mode == MODE_OSM_LEVELS, S.SRC_OSM_LEVELS,
                            np.where(source_is_real, S.SRC_LIDAR, S.SRC_NEIGHBOURS))).astype(np.int8)
    real = np.isin(src, (S.SRC_LIDAR, S.SRC_OSM_HEIGHT))
    return src, real


def storey_height_check(osm_height: np.ndarray, osm_levels: np.ndarray, osm_row: np.ndarray,
                        occ: np.ndarray) -> dict:
    """Metres per storey measured on the footprints that carry both tags, as a check on the table.

    This is a *measurement of the assumption*, not an input to it: nothing here changes the storey
    heights the stage uses.  See the module docstring for why the table is not refitted to it.
    """
    matched = osm_row >= 0
    h = np.full(len(osm_row), np.nan)
    l = np.full(len(osm_row), np.nan)
    h[matched] = osm_height[osm_row[matched]]
    l[matched] = osm_levels[osm_row[matched]]
    both = matched & np.isfinite(h) & np.isfinite(l) & (l >= 1)
    if not both.any():
        return {"n": 0}
    per = h[both] / l[both]
    out = {"n": int(both.sum()), "median_m_per_storey": round(float(np.median(per)), 2),
           "p25": round(float(np.percentile(per, 25)), 2), "p75": round(float(np.percentile(per, 75)), 2),
           "by_occupancy": {}}
    for cls in sorted(set(occ[both].tolist())):
        m = occ[both] == cls
        if m.sum() >= 3:
            out["by_occupancy"][str(cls)] = {"n": int(m.sum()), "median_m_per_storey": round(float(np.median(per[m])), 2),
                                             "min": round(float(per[m].min()), 2), "max": round(float(per[m].max()), 2)}
    return out


def unjoined_tall_tags(nj_geoms: np.ndarray, osm_geoms: np.ndarray, osm_df: pl.DataFrame,
                       osm_row: np.ndarray, min_height_m: float = 40.0) -> dict:
    """The tall OpenStreetMap heights this join could **not** use, and why.

    A published height that exists in the extract and does not reach the table is the residue of
    deviation B11a, so it is counted rather than left implicit.  For each unmatched tagged outline
    this records the best overlap it achieved against any USA Structures polygon and how much of the
    outline that polygon covered: ``covered_high_iou_low`` is the diagnostic shape — the tower sits
    inside a polygon covering its whole block, which is exactly the match that must not be made.
    """
    height = osm_df["height"].to_numpy().astype(np.float64)
    name = osm_df["name"].fill_null("").to_list()
    tall = np.nonzero(np.isfinite(height) & (height >= min_height_m))[0]
    used = set(osm_row[osm_row >= 0].tolist())
    unmatched = [int(i) for i in tall if int(i) not in used]
    if not unmatched:
        return {"min_height_m": min_height_m, "tall_tags": int(len(tall)), "unmatched": 0, "towers": []}
    tree = shapely.STRtree(nj_geoms)
    nj_area = shapely.area(nj_geoms)
    rows = []
    for i in unmatched:
        g = osm_geoms[i]
        oa = float(shapely.area(g))
        hit = tree.query(g, predicate="intersects")
        rec = {"name": name[i], "osm_id": int(osm_df["osm_id"][i]), "osm_height_m": round(float(height[i]), 1),
               "candidates": int(len(hit))}
        if len(hit):
            inter = shapely.area(shapely.intersection(g, nj_geoms[hit]))
            iou = inter / np.maximum(oa + nj_area[hit] - inter, 1e-9)
            k = int(np.argmax(iou))
            rec |= {"best_iou": round(float(iou[k]), 3),
                    "osm_outline_covered": round(float(inter[k] / max(oa, 1e-9)), 3),
                    "usa_polygon_covered": round(float(inter[k] / max(nj_area[hit][k], 1e-9)), 3),
                    "usa_area_m2": round(float(nj_area[hit][k]), 1), "osm_area_m2": round(oa, 1)}
        rows.append(rec)
    rows.sort(key=lambda r: -r["osm_height_m"])
    covered = [r for r in rows if r.get("osm_outline_covered", 0) >= 0.85 and r.get("best_iou", 0) < MATCH_MIN_IOU]
    return {"min_height_m": min_height_m, "tall_tags": int(len(tall)), "unmatched": len(rows),
            "no_overlapping_usa_polygon": int(sum(1 for r in rows if r["candidates"] == 0)),
            "covered_high_iou_low": len(covered),
            "note": ("an outline the USA Structures polygon swallows whole (the tower inside a "
                     "block-sized footprint) is refused on purpose: taking its height would raise "
                     "the whole block"),
            "towers": rows}
