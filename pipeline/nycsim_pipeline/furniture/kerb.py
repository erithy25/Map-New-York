"""A kerb-side prop takes the kerb's heading from the road it stands beside, and the side it stands on from the geometry.

Until this module the loaders of six dataset-placed kinds -- ``bus_shelter`` (2), ``linknyc`` (3), ``newsstand``
(4), ``bike_shelter`` (5), ``bike_rack`` (6) and ``bus_stop_sign`` (24) -- never wrote ``heading``, and both
consumers draw a NaN heading facing north (docs/DEVIATIONS.md J84). :func:`apply` is one post-pass over the
prop columns, run by the build after dedupe beside :func:`citibike.apply`, that fills the NaN headings of those
kinds from two things the sources do hold:

* **the axis** -- the local bearing of the nearest *roadway-class* CSCL centreline within :data:`AXIS_MAX_M`
  (``roads/segments.parquet``), reduced mod 180. :func:`citibike.station_axes` finds it and
  :func:`citibike.local_frame` takes the tangent exactly as :func:`rules._densify` does, so a dock, a shelter and
  a rule lamp on one block agree. Segments of class path, step street, non-physical, U-turn and ferry
  (:data:`NON_ROADWAY_RW_TYPES`) are not candidates: a shelter's nearest line is sometimes a housing-estate
  footpath, and "nearest" then measures something other than the street the shelter serves;
* **the side** -- which side of that centreline the prop stands on, read as the sign of the cross product of the
  segment's local tangent with the vector from the foot of the perpendicular to the prop. That is geometry read
  from two sources, not a rule, and it says where the roadway is: toward the centreline. The Citi Bike stage
  declared it could not know this; it can (:func:`side_of_centreline`).

What the sources do **not** hold is which way each kind's front faces relative to the kerb. Those are rules,
one line per kind in :data:`FACING`, each written out in :data:`RULES` with its physical basis, named in the
build summary (``kerb.rules``) and in every written row's ``attrs`` (``rules``, ``facing``, ``heading_rule``).
No MTA, DOT, LinkNYC or CityRack siting document is held in the repository; a later stage can flip one kind in
:data:`FACING` without touching the geometry.

``heading`` is, as everywhere in ``props.parquet`` (catalog.Kind.heading_meaning), the compass bearing of the
asset's authored front (+Y). ``toward_roadway`` is the perpendicular to the axis that points at the centreline,
``away_from_roadway`` its opposite, ``along_kerb`` the axis itself (the mod-180 representative).

For ``bus_shelter`` and ``bus_stop_sign`` the source names the street the object serves (``On_Street``; the
GTFS stop name ``ON ST/CROSS ST``), and at a corner the nearest centreline is often the cross street. Where a
roadway segment within reach carries that name, the nearest such segment is taken (``attrs.axis_match =
named_street``); the name normalisation is itself a rule and a miss falls back to the nearest (``nearest``).
"""
from __future__ import annotations

import json
import logging
import re
from pathlib import Path

import numpy as np
import shapely

from .catalog import KIND_ID
from .citibike import AXIS_MAX_M, _pct, local_frame, station_axes

log = logging.getLogger("nycsim.furniture.kerb")

#: The kinds this pass writes, in catalogue order.
KINDS: tuple[str, ...] = ("bus_shelter", "linknyc", "newsstand", "bike_shelter", "bike_rack", "bus_stop_sign")

TOWARD_ROADWAY = "toward_roadway"
AWAY_FROM_ROADWAY = "away_from_roadway"
ALONG_KERB = "along_kerb"

#: Which way each kind's authored front (+Y) faces relative to the kerb. A rule per kind -- see :data:`RULES`.
FACING: dict[str, str] = {
    "bus_shelter": AWAY_FROM_ROADWAY,
    "bike_shelter": AWAY_FROM_ROADWAY,
    "newsstand": AWAY_FROM_ROADWAY,
    "linknyc": ALONG_KERB,
    "bus_stop_sign": ALONG_KERB,
    "bike_rack": TOWARD_ROADWAY,
}

#: CSCL roadway classes that are not a kerb a prop stands beside (DATA_CONTRACTS §7 rw_type):
#: 6 path, 7 step street, 12 non-physical, 13 U-turn, 14 ferry.
NON_ROADWAY_RW_TYPES: tuple[int, ...] = (6, 7, 12, 13, 14)

#: A prop closer than this to the centreline was geocoded into the roadbed; its side is real geometry of a
#: point that is not where the object stands, so the toward/away choice is a coin. Counted, never smoothed.
NEAR_CENTRELINE_M = 0.5

#: Kinds whose source names the street the object serves, and where that name is read from.
NAMED_STREET_KINDS: tuple[str, ...] = ("bus_shelter", "bus_stop_sign")

#: Kinds whose loader may already carry a heading from the source itself; that heading wins and is recorded.
SOURCE_HEADING: dict[str, str] = {"bike_rack": "osm_direction"}

RULES_ID = "kerb.RULES"
#: ``attrs.heading_source`` of a row this pass wrote; a row that carries it is left alone by a later pass.
HEADING_SOURCE = "kerb_axis"

#: What this module decides that no source says. Written into the build summary and into every row's attrs.
RULES: tuple[str, ...] = (
    "axis = local bearing of the nearest roadway-class CSCL centreline within 25 m, reduced mod 180 (the "
    "tangent citibike.station_axes and rules._densify take); rw_type 6 path, 7 step street, 12 non-physical, "
    "13 U-turn and 14 ferry are not candidates; no roadway segment within reach -> heading NaN, "
    "axis_source none, and both consumers draw the row facing north",
    "side = sign of the cross product of the segment's local tangent (digitised vertex order) with the vector "
    "from the foot of the perpendicular to the prop -- geometry read from two sources, not a rule; the roadway "
    "is toward the centreline. toward_roadway = the perpendicular to the axis (axis -/+ 90) that points at the "
    "centreline, away_from_roadway = its opposite, along_kerb = the axis. A prop within 0.5 m of the "
    "centreline was geocoded into the roadbed: its perpendicular is still right, the toward/away choice is a "
    "coin (taken as axis - 90 toward), counted as side_from_offset_under_0_5m",
    "bus_shelter: back to the kerb, open front (asset +Y) to the footway -- heading = away_from_roadway. "
    "Physical basis: the 1.52 m deep unit stands in the furnishing zone with its columns and rear glazing on "
    "the kerb line and the roof cantilevering over the footway. No MTA/DOT siting document is held in the "
    "repository, so this is a rule; the dataset's own Corner field is a cross-source check of the side, never "
    "the source of the facing",
    "bike_shelter: same family as the bus shelter (drawn by the same asset), a canopy over CityRacks with its "
    "back to the kerb -- heading = away_from_roadway (a rule)",
    "newsstand: serving window and racks (asset +Y) face the footway where the customers stand, the service "
    "door is kerb-side -- heading = away_from_roadway (a rule; NYC Admin Code 20-231 gives the footprint only)",
    "linknyc: kiosk perpendicular to the kerb, its two screens (asset +/-Y) looking up and down the footway -- "
    "heading = axis (along_kerb); the tablet side is a coin the source does not flip, taken as the axis "
    "direction (a rule; no LinkNYC siting document is held in the repository)",
    "bus_stop_sign: the two-sided blade (asset +Y) is perpendicular to the kerb so it reads from the "
    "approaching bus -- heading = axis (along_kerb); axis and axis + 180 draw the same (a rule; the MUTCD "
    "practice is not held as a document here)",
    "bike_rack: hoop parallel to the kerb in the furnishing zone (asset +X along the kerb, +Y to the roadway) "
    "-- heading = toward_roadway; the hoop is symmetric under a half turn so only the axis is visible (a rule; "
    "no DOT CityRack siting sheet is in the repository). An OSM direction tag, where one exists, is kept as "
    "the heading and recorded as heading_source = osm_direction",
    "bus_shelter and bus_stop_sign: where a roadway segment within 25 m carries the street the source names "
    "(On_Street; the first-named street of the GTFS stop name 'ON ST/CROSS ST'), the nearest such segment is "
    "taken over the nearest of any name (axis_match = named_street), because at a corner the nearest "
    "centreline is often the cross street. The name match is a rule: upper-case, punctuation stripped, "
    "AVENUE/AVE -> AV, STREET -> ST, ROAD -> RD, BOULEVARD -> BLVD, PLACE -> PL, PARKWAY -> PKWY, "
    "EAST/WEST/NORTH/SOUTH -> E/W/N/S, ordinal suffixes dropped; no match -> nearest (axis_match = nearest)",
)


# --------------------------------------------------------------------------------------- street names

_ABBREV = (
    (re.compile(r"\b(AVENUE|AVE)\b"), "AV"), (re.compile(r"\bSTREET\b"), "ST"), (re.compile(r"\bROAD\b"), "RD"),
    (re.compile(r"\bBOULEVARD\b"), "BLVD"), (re.compile(r"\bPLACE\b"), "PL"), (re.compile(r"\bPARKWAY\b"), "PKWY"),
    (re.compile(r"\bEAST\b"), "E"), (re.compile(r"\bWEST\b"), "W"), (re.compile(r"\bNORTH\b"), "N"),
    (re.compile(r"\bSOUTH\b"), "S"), (re.compile(r"\b(\d+)(ST|ND|RD|TH)\b"), r"\1"),
)


def normalise_street(name: str) -> str:
    """The name-match rule of :data:`RULES`: one spelling for 'ATLANTIC AVENUE', 'Atlantic Ave' and 'ATLANTIC AV'."""
    s = re.sub(r"[^A-Z0-9 ]", " ", str(name or "").upper())
    for rx, rep in _ABBREV:
        s = rx.sub(rep, s)
    return " ".join(s.split())


_STOP_NAME_SPLIT = re.compile(r"/| & | AT ")


def named_street(kind_name: str, text: str, attrs: dict) -> str:
    """The street the source says the object serves, normalised; '' where the kind or the row names none."""
    if kind_name == "bus_shelter":
        return normalise_street(attrs.get("on_street", ""))
    if kind_name == "bus_stop_sign":
        parts = [p for p in _STOP_NAME_SPLIT.split(str(text or "").upper()) if p.strip()]
        return normalise_street(parts[0]) if len(parts) >= 2 else ""
    return ""


# --------------------------------------------------------------------------------------- geometry

def roadway_segments(seg: dict | None) -> dict | None:
    """The segments table without :data:`NON_ROADWAY_RW_TYPES`. Every array key is masked alike."""
    if seg is None:
        return None
    keep = ~np.isin(np.asarray(seg["rw_type"]), NON_ROADWAY_RW_TYPES)
    out = {}
    for k, v in seg.items():
        if isinstance(v, np.ndarray) and v.shape[:1] == keep.shape:
            out[k] = v[keep]
        else:
            out[k] = v
    return out


def side_of_centreline(px: np.ndarray, py: np.ndarray, proj: np.ndarray, tangent: np.ndarray) -> dict:
    """Which side of a line a point stands on, from the line's local tangent and the foot of the perpendicular.

    ``cross = t.x * v.y - t.y * v.x`` with ``v = P - proj``; in the NYC_TM x-east / y-north frame ``cross > 0``
    puts the point on the **left** of the tangent's direction of travel (the standard 2-D orientation test;
    :func:`rules.street_lamps` uses the same frame, right of travel = heading + 90). The digitised direction is
    arbitrary with respect to traffic, so ``side`` means something only together with the segment id; the
    facing carries the meaning. Returns ``side`` (list of ``left``/``right``/``on``), ``cross``, ``v`` (n, 2)
    and ``offset_m`` (|v|, the perpendicular distance).
    """
    v = np.column_stack([np.asarray(px, dtype=np.float64), np.asarray(py, dtype=np.float64)]) - proj
    cross = tangent[:, 0] * v[:, 1] - tangent[:, 1] * v[:, 0]
    side = np.where(cross > 0, "left", np.where(cross < 0, "right", "on")).tolist()
    return {"side": side, "cross": cross, "v": v, "offset_m": np.hypot(v[:, 0], v[:, 1])}


def toward_roadway_deg(axis_deg: np.ndarray, v: np.ndarray) -> np.ndarray:
    """The perpendicular to the axis that points at the centreline: ``axis - 90`` or ``axis + 90``.

    Chosen by the sign of its dot product with ``-v`` (foot of the perpendicular minus prop), so the heading
    stays exactly perpendicular to the local axis rather than to the chord to a vertex. A zero offset (the
    prop on the line) is a coin and takes ``axis - 90``.
    """
    a = np.radians(np.asarray(axis_deg, dtype=np.float64) - 90.0)
    dot = np.sin(a) * (-v[:, 0]) + np.cos(a) * (-v[:, 1])
    return np.where(dot >= 0, axis_deg - 90.0, axis_deg + 90.0) % 360.0


def heading_for(facing: str, axis_deg: np.ndarray, toward_deg: np.ndarray) -> np.ndarray:
    """The compass bearing of the asset's +Y front for one of the three facings."""
    axis_deg = np.asarray(axis_deg, dtype=np.float64)
    toward_deg = np.asarray(toward_deg, dtype=np.float64)
    if facing == TOWARD_ROADWAY:
        return toward_deg % 360.0
    if facing == AWAY_FROM_ROADWAY:
        return (toward_deg + 180.0) % 360.0
    if facing == ALONG_KERB:
        return axis_deg % 360.0
    raise ValueError(f"unknown facing {facing!r}")


def kerb_axes(x: np.ndarray, y: np.ndarray, seg: dict | None, names: list[str] | None = None,
              max_dist_m: float = AXIS_MAX_M) -> dict:
    """Axis, chosen segment and side for every point, against a (roadway-masked) segments table.

    ``names`` -- one normalised street name per point ('' for no preference): where a segment within
    ``max_dist_m`` carries that name, the nearest such segment replaces the nearest of any name. Returns
    :func:`citibike.station_axes`' arrays (with ``axis_deg`` etc. recomputed against the chosen segment)
    plus ``axis_match`` (``named_street`` / ``nearest`` / ``none``), ``nearest_segment_id`` /
    ``nearest_distance_m`` / ``nearest_axis_deg`` (the plain nearest, for the report), ``side``, ``cross``,
    ``v``, ``offset_m``, ``toward_deg`` and ``tangent_deg``.
    """
    n = len(x)
    x = np.asarray(x, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    out = station_axes(x, y, seg, max_dist_m)
    out["nearest_segment_id"] = out["segment_id"].copy()
    out["nearest_distance_m"] = out["distance_m"].copy()
    out["nearest_axis_deg"] = out["axis_deg"].copy()
    out["axis_match"] = ["none"] * n
    out["side"] = [""] * n
    out["cross"] = np.full(n, np.nan)
    out["v"] = np.full((n, 2), np.nan)
    out["offset_m"] = np.full(n, np.nan)
    out["toward_deg"] = np.full(n, np.nan)
    out["tangent_deg"] = np.full(n, np.nan)
    out["named_street_in_reach"] = np.zeros(n, dtype=bool)
    if n == 0 or seg is None or out.get("skipped"):
        return out
    geoms = np.asarray(seg["geometry"], dtype=object)
    ok = np.array([g is not None and not g.is_empty for g in geoms], dtype=bool)
    lines = geoms[ok]
    seg_rows = np.flatnonzero(ok)
    sid = np.asarray(seg["segment_id"])[seg_rows]
    accepted = np.flatnonzero(np.isfinite(out["axis_deg"]))
    if accepted.size == 0:
        return out
    row_of_sid = {int(s): i for i, s in enumerate(sid.tolist())}
    chosen = np.array([row_of_sid[int(s)] for s in out["segment_id"][accepted]], dtype=np.int64)
    match = np.array(["nearest"] * accepted.size, dtype=object)
    pts = shapely.points(x, y)

    # ---- name preference: the nearest segment within reach that carries the street the source names
    if names is not None and seg.get("street_name") is not None:
        want = np.array([names[i] for i in accepted], dtype=object)
        has = np.array([bool(w) for w in want], dtype=bool)
        if has.any():
            seg_norm = np.array([normalise_street(s) for s in np.asarray(seg["street_name"], dtype=object)[seg_rows]],
                                dtype=object)
            tree = shapely.STRtree(lines)
            qi, li = tree.query(pts[accepted[has]], predicate="dwithin", distance=float(max_dist_m))
            if qi.size:
                name_ok = seg_norm[li] == want[has][qi]
                qi, li = qi[name_ok], li[name_ok]
            if qi.size:
                cand_pts = pts[accepted[has]][qi]
                dist = shapely.distance(cand_pts, lines[li])
                order = np.lexsort((dist, qi))
                qi, li, dist = qi[order], li[order], dist[order]
                first = np.r_[True, qi[1:] != qi[:-1]]
                local = np.flatnonzero(has)[qi[first]]
                chosen[local] = li[first]
                match[local] = "named_street"
                out["named_street_in_reach"][accepted[local]] = True

    # ---- the frame on the chosen segment: axis, side, toward
    frame = local_frame(lines[chosen], pts[accepted])
    sides = side_of_centreline(x[accepted], y[accepted], frame["proj"], frame["tangent"])
    axis = frame["bearing_deg"] % 180.0
    toward = toward_roadway_deg(axis, sides["v"])
    out["axis_deg"][accepted] = axis
    out["segment_id"][accepted] = sid[chosen]
    out["distance_m"][accepted] = frame["distance_m"]
    out["rw_type"][accepted] = np.asarray(seg["rw_type"])[seg_rows][chosen]
    out["segment_length_m"][accepted] = frame["length_m"]
    out["cross"][accepted] = sides["cross"]
    out["v"][accepted] = sides["v"]
    out["offset_m"][accepted] = sides["offset_m"]
    out["toward_deg"][accepted] = toward
    out["tangent_deg"][accepted] = frame["bearing_deg"]
    for j, i in enumerate(accepted.tolist()):
        out["axis_match"][i] = str(match[j])
        out["side"][i] = sides["side"][j]
    return out


# --------------------------------------------------------------------------------------- cross-source check

def _corner_check(attrs: list[dict], axes: dict, seg_names: dict[int, str]) -> dict:
    """The shelter dataset's Corner (NE/NW/SE/SW quadrant of the intersection) against the derived side.

    Testable where the axis is within 45 deg of east-west (the N/S letter must agree with the sign of the
    prop's northing offset from the centreline) or of north-south (the E/W letter with the easting offset).
    Disagreements are characterised, never corrected: a Corner is a quadrant of the intersection, which on
    Brooklyn's diagonal grid does not separate 'north side' from 'east side'.
    """
    agree = disagree = untestable = 0
    diag = cross_nearest = 0
    rest: list[dict] = []
    ax = axes["axis_deg"]
    v = axes["v"]
    for i, a in enumerate(attrs):
        if not np.isfinite(ax[i]):
            continue
        c = str(a.get("corner", "")).upper()
        ew = abs(((ax[i] + 90.0) % 180.0) - 90.0) > 45.0        # axis within 45 deg of bearing 90: an E-W street
        if ew and c[:1] in ("N", "S"):
            exp = 1.0 if c[0] == "N" else -1.0
            ok_ = np.sign(v[i, 1]) == exp
        elif not ew and len(c) > 1 and c[1] in ("E", "W"):
            exp = 1.0 if c[1] == "E" else -1.0
            ok_ = np.sign(v[i, 0]) == exp
        else:
            untestable += 1
            continue
        if ok_:
            agree += 1
            continue
        disagree += 1
        if min(abs(ax[i] - 45.0), abs(ax[i] - 135.0)) <= 20.0:
            diag += 1
        elif normalise_street(seg_names.get(int(axes["segment_id"][i]), "")) == normalise_street(a.get("cross_street", "")):
            cross_nearest += 1
        else:
            rest.append({"shelter_id": a.get("shelter_id", ""), "corner": c, "on_street": a.get("on_street", ""),
                         "cross_street": a.get("cross_street", ""), "axis_deg": round(float(ax[i]), 1),
                         "axis_segment_id": int(axes["segment_id"][i]),
                         "segment_name": seg_names.get(int(axes["segment_id"][i]), ""), "side": axes["side"][i]})
    testable = agree + disagree
    return {"what": "the dataset's own Corner quadrant against the derived side; a check of the sign, not its source",
            "testable": testable, "agree": agree, "disagree": disagree, "untestable": untestable,
            "agree_fraction": round(agree / testable, 4) if testable else None,
            "disagree_axis_within_20deg_of_diagonal": diag, "disagree_cross_street_is_the_axis_segment": cross_nearest,
            "disagree_other": rest}


# --------------------------------------------------------------------------------------- the pass

def apply(cols: dict, segments_path: Path, seg: dict | None = None) -> tuple[dict, dict]:
    """Fill the NaN headings of :data:`KINDS` from the kerb axis and the side of the centreline. Returns (cols, report).

    Runs after dedupe, so headings are computed for the rows that survive. Only ``heading`` and ``attrs`` of
    those kinds change; every other column and every other kind is untouched to the byte, and a row whose
    loader already carried a heading (an OSM ``direction`` on a bike rack) keeps it. Idempotent: a second call
    finds no NaN among the kinds and writes nothing.
    """
    from .rules import load_segments
    if seg is None:
        seg = load_segments(Path(segments_path))
    road = roadway_segments(seg)
    seg_names: dict[int, str] = {}
    if seg is not None and seg.get("street_name") is not None:
        seg_names = {int(s): str(n) for s, n in zip(np.asarray(seg["segment_id"]).tolist(),
                                                     np.asarray(seg["street_name"], dtype=object).tolist())}

    kind = np.asarray(cols["kind"], dtype=np.int16)
    heading = np.asarray(cols["heading"], dtype=np.float32).copy()
    attrs_out = list(cols["attrs"])
    x = np.asarray(cols["x"], dtype=np.float64)
    y = np.asarray(cols["y"], dtype=np.float64)
    report: dict = {"rules_id": RULES_ID, "rules": list(RULES), "axis_max_m": float(AXIS_MAX_M),
                    "non_roadway_rw_types_excluded": list(NON_ROADWAY_RW_TYPES),
                    "facing": dict(FACING), "near_centreline_m": NEAR_CENTRELINE_M, "kinds": {}}
    if seg is None:
        report["skipped"] = f"{segments_path} absent: no kerb heading for any row"

    kind_of_row: dict[int, str] = {}
    todo: list[int] = []
    kept: dict[str, int] = {}
    carried: dict[str, int] = {}
    for name in KINDS:
        rows = np.flatnonzero(kind == KIND_ID[name])
        nan = rows[~np.isfinite(heading[rows])]
        have = rows[np.isfinite(heading[rows])]
        kept[name] = 0
        carried[name] = 0
        for i in have.tolist():
            a = json.loads(attrs_out[i]) if attrs_out[i] else {}
            if a.get("heading_source") == HEADING_SOURCE:
                carried[name] += 1                  # written by an earlier pass: idempotent, nothing to do
                continue
            kept[name] += 1
            if "heading_source" not in a:
                a.update({"heading_source": SOURCE_HEADING.get(name, "source"), "kept_source_heading": True,
                          "rules": RULES_ID})
                attrs_out[i] = json.dumps(a, separators=(",", ":"))
        for i in nan.tolist():
            kind_of_row[i] = name
        todo.extend(nan.tolist())
    todo_arr = np.asarray(sorted(todo), dtype=np.int64)
    attrs_in = [json.loads(attrs_out[i]) if attrs_out[i] else {} for i in todo_arr.tolist()]
    names = [named_street(kind_of_row[int(i)], cols["text"][int(i)], a) for i, a in zip(todo_arr.tolist(), attrs_in)]
    axes = kerb_axes(x[todo_arr], y[todo_arr], road, names)
    # the same rows against every line, class mask off: what the mask changed, and what it left with nothing
    unmasked = station_axes(x[todo_arr], y[todo_arr], seg) if seg is not None else None

    written = np.zeros(len(todo_arr), dtype=bool)
    new_heading = np.full(len(todo_arr), np.nan)
    for j, i in enumerate(todo_arr.tolist()):
        name = kind_of_row[i]
        a = attrs_in[j]
        a["rules"] = RULES_ID
        if axes["axis_source"][j] == "nearest_segment":
            facing = FACING[name]
            h = float(heading_for(facing, axes["axis_deg"][j], axes["toward_deg"][j]))
            new_heading[j] = h
            written[j] = True
            a.update({"axis_deg": round(float(axes["axis_deg"][j]), 2), "axis_source": "nearest_segment",
                      "axis_segment_id": int(axes["segment_id"][j]),
                      "axis_distance_m": round(float(axes["distance_m"][j]), 2),
                      "axis_rw_type": int(axes["rw_type"][j]), "side": axes["side"][j], "facing": facing,
                      "heading_source": HEADING_SOURCE, "heading_rule": f"{RULES_ID}:{name}:{facing}"})
            if name in NAMED_STREET_KINDS:
                a["axis_match"] = axes["axis_match"][j]
        else:
            a["axis_source"] = "none"
            if np.isfinite(axes["distance_m"][j]):
                a["axis_distance_m"] = round(float(axes["distance_m"][j]), 2)
                a["axis_rw_type"] = int(axes["rw_type"][j])
        attrs_out[i] = json.dumps(a, separators=(",", ":"))
    heading[todo_arr[written]] = new_heading[written].astype(np.float32)

    def dang(a, b):
        return np.abs(((a - b) + 90.0) % 180.0 - 90.0)

    for name in KINDS:
        rows = np.flatnonzero(kind == KIND_ID[name])
        m = np.array([kind_of_row[int(i)] == name for i in todo_arr], dtype=bool) if todo_arr.size else np.zeros(0, bool)
        acc = m & written
        none = m & ~written
        dist_all = axes["distance_m"][m]
        rec: dict = {
            "rows": int(rows.size), "facing": FACING[name],
            "heading_written": int(acc.sum()), "kept_source_heading": kept[name],
            "already_written_by_an_earlier_pass": carried[name], "heading_nan": int(none.sum()),
            "axis_distance_m": _pct(axes["distance_m"][acc]),
            "axis_rw_type": {int(k): int(c) for k, c in zip(*np.unique(axes["rw_type"][acc], return_counts=True))},
            "side": {s: int(sum(1 for j in np.flatnonzero(acc) if axes["side"][j] == s)) for s in ("left", "right", "on")},
            "side_from_offset_under_0_5m": int((axes["offset_m"][acc] < NEAR_CENTRELINE_M).sum()),
        }
        if none.any():
            nd = axes["distance_m"][none]
            no_axis: dict = {
                "count": int(none.sum()),
                "beyond_25m": int(np.isfinite(nd).sum()), "no_roadway_segment_at_all": int((~np.isfinite(nd)).sum()),
                "nearest_roadway_segment_m": _pct(nd),
                "beyond_100m": int((nd > 100.0).sum()),
                "nearest_rw_type": {int(k): int(c) for k, c in zip(*np.unique(axes["rw_type"][none], return_counts=True))},
            }
            if unmasked is not None:
                ud = unmasked["distance_m"][none]
                no_axis["only_a_non_roadway_line_within_25m"] = int((ud <= AXIS_MAX_M).sum())
                no_axis["non_roadway_rw_type_of_that_line"] = {
                    int(k): int(c) for k, c in zip(*np.unique(unmasked["rw_type"][none][ud <= AXIS_MAX_M], return_counts=True))}
            rec["no_axis"] = no_axis
        if unmasked is not None and acc.any():
            both = acc & np.isfinite(unmasked["axis_deg"])
            nearest_any = unmasked["segment_id"]
            chg = both & (axes["nearest_segment_id"] != nearest_any)
            rec["class_mask"] = {
                "nearest_segment_changed": int(chg.sum()),
                "axis_changed_over_30deg": int((chg & (dang(axes["nearest_axis_deg"], unmasked["axis_deg"]) > 30.0)).sum()),
            }
        if name in NAMED_STREET_KINDS:
            named = acc & np.array([s == "named_street" for s in axes["axis_match"]], dtype=bool)
            differs = named & (axes["segment_id"] != axes["nearest_segment_id"])
            rec["named_street"] = {
                "rows_naming_a_street": int(sum(1 for j in np.flatnonzero(m) if names[j])),
                "named_street_matched": int(named.sum()), "fell_back_to_nearest": int((acc & ~named).sum()),
                "differs_from_nearest": int(differs.sum()),
                "axis_changed_over_30deg": int((differs & (dang(axes["axis_deg"], axes["nearest_axis_deg"]) > 30.0)).sum()),
            }
        if name == "bus_shelter" and acc.any():
            sub = {k: (np.asarray(v)[m] if isinstance(v, np.ndarray) and v.shape[:1] == m.shape else
                       [v[j] for j in np.flatnonzero(m)] if isinstance(v, list) and len(v) == m.size else v)
                   for k, v in axes.items()}
            rec["corner_check"] = _corner_check([attrs_in[j] for j in np.flatnonzero(m)], sub, seg_names)
        report["kinds"][name] = rec
    report["heading_written"] = int(written.sum())
    report["heading_nan"] = int((~written).sum())
    report["kept_source_heading"] = int(sum(kept.values()))
    log.info("kerb: %d headings written over %d kinds, %d left NaN (no roadway segment within %.0f m), %d kept from the source",
             report["heading_written"], len(KINDS), report["heading_nan"], AXIS_MAX_M, report["kept_source_heading"])
    cols["heading"] = heading
    cols["attrs"] = attrs_out
    return cols, report
