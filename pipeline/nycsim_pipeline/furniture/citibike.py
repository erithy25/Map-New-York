"""A Citi Bike station is a kiosk, a run of dock units and the bikes that happen to be in it -- not one row.

The GBFS ``station_information`` snapshot gives one point and one ``capacity`` per station. Until this module
every station was one ``props.parquet`` row and was drawn as a single bicycle (docs/DEVIATIONS.md J58).
:func:`expand` turns the row into its parts, each a row of the same kind (7, ``citibike_dock``) that the
consumers already resolve through the assets' ``variant:N`` tags:

* ``variant`` 1 -- one kiosk per station (``citibike_kiosk``); the station's record (``capacity``, the GBFS
  attributes) lives on this row, so ``sum(capacity)`` over kind 7 is the number of dock rows;
* ``variant`` 2 -- ``capacity`` dock units (``citibike_dock_unit``) at :data:`PITCH_M` along the kerb axis,
  centred on the GBFS point;
* ``variant`` 3 -- a docked bicycle (``citibike_bike``), written **only** from a GBFS ``station_status``
  snapshot (:func:`load_status`), never from a guess: the snapshot says how many bikes stood in the station at
  one instant, and every bike row carries that instant in ``attrs.snapshot_last_updated``.

Everything below that the sources do not say is a rule, named in :data:`RULES`, in every part's
``attrs.rules`` and in the build summary.  The kerb axis is the local bearing of the nearest CSCL centreline
(:func:`station_axes`, the same tangent :func:`rules._densify` uses) reduced to an undirected line; where no
segment lies within :data:`AXIS_MAX_M` the run is laid east--west with ``heading`` NaN, which is the direction
both consumers draw a NaN heading in (yaw 0, asset +X = east), so the file says what the picture shows.
"""
from __future__ import annotations

import datetime as _dt
import json
import logging
from pathlib import Path

import numpy as np
import shapely

from ..paths import RAW
from .catalog import HEIGHT_SOURCE, KIND_BY_NAME, SOURCE_DATASET
from .schema import empty_columns

log = logging.getLogger("nycsim.furniture.citibike")

#: Dock pitch along the run. The catalogue's "observed spacing" (catalog.py Kind 7) and the asset's
#: ``tile_pitch_m`` (blender/props/p_transit.py build_citibike_dock). An observation, not a Lyft specification.
PITCH_M = 0.90
#: A station takes its axis from the nearest CSCL segment only when that segment is within this distance.
#: Measured before the value was chosen: the nearest-segment distance of the 2,507 stations has p95 17.8 m,
#: and the 113 beyond 25 m are 106 Jersey City / Hoboken stations (segments.parquet is NYC-only) plus 7 with
#: no road within reach; 25 m separates the two populations.
AXIS_MAX_M = 25.0
#: A docked bike's origin sits this far behind the dock's origin, along the dock's front: the dock's fork
#: centre is at y = +0.06 in its frame and the bike's front wheel at y = +0.565 in its own (p_transit.py).
BIKE_SETBACK_M = 0.505
KIOSK_HEIGHT_M = 2.00     # citibike_kiosk nominal (p_transit.py)
DOCK_HEIGHT_M = 0.53      # citibike_dock_unit nominal
BIKE_HEIGHT_M = 1.15      # citibike_bike nominal
VARIANT_KIOSK, VARIANT_DOCK, VARIANT_BIKE = 1, 2, 3

STATIONS_ID = "citibike_gbfs_stations"
STATUS_ID = "citibike_gbfs_station_status"
STATUS = RAW / "furniture" / f"{STATUS_ID}.json"
FETCH_STATUS = f"python -m nycsim_pipeline.download --id {STATUS_ID}"

#: What this module decides that no source says. Written into the build summary and into every part's attrs.
RULES: tuple[str, ...] = (
    "single straight run of capacity dock units at 0.90 m pitch, centred on the GBFS point (GBFS documents "
    "lat/lon as the station location, not as the run's centre)",
    "axis = local bearing of the nearest CSCL centreline within 25 m, reduced mod 180; no segment within reach "
    "-> east-west with heading NaN (the consumers' NaN convention)",
    "the kiosk stands one pitch (0.90 m) beyond the last dock at the axis+180 end of the run (south / west)",
    "docks and kiosk face the same side of the kerb (heading = axis - 90); which side is the sidewalk is not in "
    "any source of this build",
    "a station of capacity 0 is its kiosk alone",
    "bikes are written only from a station_status snapshot; num_bikes_available is capped at capacity and the "
    "bikes fill the docks from the kiosk end (the snapshot says how many, never which)",
    "classic and electric bikes are drawn by the one bicycle asset",
)


# --------------------------------------------------------------------------------------- station axis

def station_axes(x: np.ndarray, y: np.ndarray, seg: dict | None, max_dist_m: float = AXIS_MAX_M) -> dict:
    """Kerb-parallel axis of every point from the nearest CSCL segment.

    ``seg`` is :func:`rules.load_segments`' dict (``None`` when the roads stage has not run). Returns arrays
    ``axis_deg`` (compass bearing mod 180, NaN where none), ``segment_id`` (-1), ``distance_m`` (NaN),
    ``rw_type`` (-1), ``segment_length_m`` (NaN) and a list ``axis_source`` of ``"nearest_segment"`` /
    ``"none"``. The tangent is taken exactly as :func:`rules._densify` takes it -- the chord between the
    points ``eps`` before and after the projection -- so a rule lamp and a dock on the same block agree.
    """
    n = len(x)
    out = {
        "axis_deg": np.full(n, np.nan, dtype=np.float64),
        "segment_id": np.full(n, -1, dtype=np.int64),
        "distance_m": np.full(n, np.nan, dtype=np.float64),
        "rw_type": np.full(n, -1, dtype=np.int16),
        "segment_length_m": np.full(n, np.nan, dtype=np.float64),
        "axis_source": ["none"] * n,
        "max_dist_m": float(max_dist_m),
    }
    if n == 0:
        return out
    if seg is None:
        out["skipped"] = "roads/segments.parquet absent: no kerb axis for any station"
        return out
    geoms = np.asarray(seg["geometry"], dtype=object)
    ok = np.array([g is not None and not g.is_empty for g in geoms], dtype=bool)
    if not ok.any():
        out["skipped"] = "segments table holds no geometry"
        return out
    lines = geoms[ok]
    tree = shapely.STRtree(lines)
    pts = shapely.points(np.asarray(x, dtype=np.float64), np.asarray(y, dtype=np.float64))
    qi, li = tree.query_nearest(pts, return_distance=False, all_matches=False)
    near = lines[li]
    dist = shapely.distance(pts[qi], near)
    length = shapely.length(near)
    d = shapely.line_locate_point(near, pts[qi])
    eps = np.minimum(1.0, np.maximum(length * 1e-3, 0.05))
    p0 = shapely.get_coordinates(shapely.line_interpolate_point(near, np.maximum(d - eps, 0.0)))[:, :2]
    p1 = shapely.get_coordinates(shapely.line_interpolate_point(near, np.minimum(d + eps, length)))[:, :2]
    t = p1 - p0
    nrm = np.hypot(t[:, 0], t[:, 1])
    nrm[nrm == 0] = 1.0
    bearing = np.degrees(np.arctan2(t[:, 0] / nrm, t[:, 1] / nrm)) % 360.0
    seg_rows = np.flatnonzero(ok)[li]
    out["distance_m"][qi] = dist
    out["segment_id"][qi] = np.asarray(seg["segment_id"])[seg_rows]
    out["rw_type"][qi] = np.asarray(seg["rw_type"])[seg_rows]
    out["segment_length_m"][qi] = length
    accept = dist <= max_dist_m
    out["axis_deg"][qi[accept]] = bearing[accept] % 180.0
    for i in qi[accept].tolist():
        out["axis_source"][i] = "nearest_segment"
    return out


# --------------------------------------------------------------------------------------- station status

def load_status(path: Path = STATUS) -> dict | None:
    """The GBFS ``station_status`` snapshot, keyed by station_id; ``None`` when it was never fetched.

    What it measures: the bikes and docks available at one instant (``ttl`` 60 s) -- an occupancy, not a
    property of the station. Every consumer of it must carry ``last_updated`` along.
    """
    path = Path(path)
    if not path.is_file():
        return None
    doc = json.loads(path.read_text())
    by_station = {}
    for s in doc.get("data", {}).get("stations", []):
        sid = str(s.get("station_id", ""))
        if not sid:
            continue
        by_station[sid] = {
            "num_bikes_available": int(s.get("num_bikes_available", 0) or 0),
            "num_ebikes_available": int(s.get("num_ebikes_available", 0) or 0),
            "num_docks_available": int(s.get("num_docks_available", 0) or 0),
            "is_installed": int(s.get("is_installed", 1) if s.get("is_installed") is not None else 1),
            "is_renting": int(s.get("is_renting", 1) if s.get("is_renting") is not None else 1),
            "last_reported": int(s.get("last_reported", 0) or 0),
        }
    last = int(doc.get("last_updated", 0) or 0)
    return {"source_id": STATUS_ID, "path": str(path), "last_updated": last,
            "last_updated_iso": _dt.datetime.fromtimestamp(last, _dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") if last else "",
            "ttl_s": int(doc.get("ttl", 0) or 0), "version": str(doc.get("version", "")), "by_station": by_station}


# --------------------------------------------------------------------------------------- expansion

def _pct(v: np.ndarray, qs=(5, 25, 50, 75, 90, 95, 99)) -> dict:
    v = np.asarray(v, dtype=np.float64)
    v = v[np.isfinite(v)]
    if v.size == 0:
        return {}
    d = {f"p{q}": round(float(np.percentile(v, q)), 2) for q in qs}
    d["max"] = round(float(v.max()), 2)
    d["n"] = int(v.size)
    return d


def _unit(axis_deg: float) -> tuple[float, float, float, float]:
    """``(ux, uy, fx, fy)``: the run direction and the front (facing) direction for a compass axis.

    The dock asset tiles along its +X and faces +Y; a row with ``heading = axis - 90`` is rotated so that its
    +X lies along the compass direction ``axis`` and its +Y along ``axis - 90``. A NaN axis is drawn at yaw 0
    by every consumer, so its run direction is east and its front is north.
    """
    if not np.isfinite(axis_deg):
        return 1.0, 0.0, 0.0, 1.0
    a = np.radians(axis_deg)
    ux, uy = float(np.sin(a)), float(np.cos(a))
    return ux, uy, -uy, ux


def expand(cols: dict, kind_id: int, axes: dict, status: dict | None = None) -> tuple[dict, dict]:
    """Replace every kind-``kind_id`` station row of ``cols`` by its kiosk, its dock units and its bikes.

    ``axes`` is :func:`station_axes` over the station rows, in their order. Raises if any station row already
    carries ``attrs.part`` -- the expansion is not idempotent (a second pass would tile the tiles) and dedupe
    would delete every other dock, so the build calls it exactly once, after dedupe.
    """
    kind = np.asarray(cols["kind"], dtype=np.int16)
    rows = np.flatnonzero(kind == kind_id)
    others = np.flatnonzero(kind != kind_id)
    n_st = int(rows.size)
    if len(axes["axis_deg"]) != n_st:
        raise ValueError(f"axes cover {len(axes['axis_deg'])} stations, cols hold {n_st}")
    x = np.asarray(cols["x"], dtype=np.float64)[rows]
    y = np.asarray(cols["y"], dtype=np.float64)[rows]
    cap = np.asarray(cols["capacity"], dtype=np.int64)[rows]
    names = [cols["text"][i] for i in rows]
    dataset = [cols["dataset_id"][i] for i in rows]
    attrs_in = []
    for i in rows:
        a = json.loads(cols["attrs"][i]) if cols["attrs"][i] else {}
        if "part" in a:
            raise ValueError(f"station row already expanded (attrs.part={a['part']!r}); expand() runs once, after dedupe")
        attrs_in.append(a)

    report: dict = {"stations": n_st, "kiosks": 0, "docks": 0, "bikes": 0, "pitch_m": PITCH_M,
                    "axis_max_m": float(axes.get("max_dist_m", AXIS_MAX_M)), "rules": list(RULES)}
    if axes.get("skipped"):
        report["axis_skipped"] = axes["skipped"]

    # ---- per-station geometry
    ax = np.asarray(axes["axis_deg"], dtype=np.float64)
    src = list(axes["axis_source"])
    heading = np.where(np.isfinite(ax), (ax - 90.0) % 360.0, np.nan).astype(np.float32)
    run_len = cap.astype(np.float64) * PITCH_M
    seg_len = np.asarray(axes.get("segment_length_m", np.full(n_st, np.nan)), dtype=np.float64)

    st_bikes = np.zeros(n_st, dtype=np.int64)
    bikes_rep: dict
    if status is None:
        bikes_rep = {"absent": "no station_status snapshot in this build", "fetch": FETCH_STATUS, "placed": 0}
    else:
        by = status["by_station"]
        matched = 0
        avail = np.zeros(n_st, dtype=np.int64)
        ebikes = np.zeros(n_st, dtype=np.int64)
        not_installed = not_renting = 0
        for i, a in enumerate(attrs_in):
            s = by.get(str(a.get("station_id", "")))
            if s is None:
                continue
            matched += 1
            avail[i] = s["num_bikes_available"]
            ebikes[i] = s["num_ebikes_available"]
            not_installed += int(s["is_installed"] == 0)
            not_renting += int(s["is_renting"] == 0)
        st_bikes = np.minimum(avail, cap)
        over = np.flatnonzero(avail > cap)
        bikes_rep = {
            "source_id": status["source_id"], "path": status["path"],
            "snapshot_last_updated": status["last_updated"], "snapshot_last_updated_iso": status["last_updated_iso"],
            "ttl_s": status["ttl_s"], "gbfs_version": status["version"],
            "what_it_measures": "bikes available at that one instant; an occupancy frozen into the world, not a typical state",
            "stations_joined": matched, "stations_unmatched": n_st - matched,
            "num_bikes_available_sum": int(avail.sum()), "num_ebikes_available_sum": int(ebikes.sum()),
            "ebikes_note": "classic and electric bikes are drawn by the one bicycle asset",
            "placed": int(st_bikes.sum()), "capped_by_capacity": int((avail - st_bikes).sum()),
            "stations_reporting_more_bikes_than_capacity": [
                {"station_id": attrs_in[i].get("station_id", ""), "name": names[i], "capacity": int(cap[i]),
                 "num_bikes_available": int(avail[i])} for i in over.tolist()],
            "stations_not_installed_in_snapshot": not_installed, "stations_not_renting_in_snapshot": not_renting,
            "note_not_installed": "placed anyway: station_information lists them and the parts follow that list (a rule)",
            "fill_rule": "docks 0..n-1 from the kiosk end",
        }

    # ---- emit the parts
    n_docks = int(cap.clip(min=0).sum())
    n_bikes = int(st_bikes.sum())
    n_out = n_st + n_docks + n_bikes
    out = empty_columns(n_out)
    out["kind"] = np.full(n_out, kind_id, dtype=np.int16)
    out["source"] = np.full(n_out, SOURCE_DATASET, dtype=np.int8)
    out["height_source"] = np.full(n_out, HEIGHT_SOURCE["nominal"], dtype=np.int8)
    ox = np.empty(n_out); oy = np.empty(n_out)
    ohead = np.empty(n_out, dtype=np.float32)
    ovar = np.empty(n_out, dtype=np.int16)
    ocap = np.zeros(n_out, dtype=np.int16)
    oh = np.empty(n_out, dtype=np.float32)
    otext: list[str] = [""] * n_out
    ods: list[str] = [""] * n_out
    oattrs: list[str] = [""] * n_out
    zero_capacity: list[dict] = []
    k = 0
    for i in range(n_st):
        N = int(max(cap[i], 0))
        ux, uy, fx, fy = _unit(ax[i])
        base = {"station_id": attrs_in[i].get("station_id", ""), "short_name": attrs_in[i].get("short_name", ""),
                "region_id": attrs_in[i].get("region_id", ""), "name": names[i], "capacity": N,
                "axis_source": src[i], "rules": "citibike.RULES"}
        if src[i] != "none":
            base.update({"axis_deg": round(float(ax[i]), 2), "axis_segment_id": int(axes["segment_id"][i]),
                         "axis_distance_m": round(float(axes["distance_m"][i]), 2)})
        # dock i at c + (i - (N-1)/2) * pitch * u, i = 0 .. N-1; the kiosk one pitch past dock 0
        for j in range(N):
            s = (j - (N - 1) / 2.0) * PITCH_M
            ox[k], oy[k] = x[i] + s * ux, y[i] + s * uy
            ohead[k] = heading[i]; ovar[k] = VARIANT_DOCK; oh[k] = DOCK_HEIGHT_M
            otext[k] = names[i]; ods[k] = dataset[i]
            oattrs[k] = json.dumps(dict(base, part="dock", dock_index=j), separators=(",", ":"))
            k += 1
        s = -((N - 1) / 2.0 + 1.0) * PITCH_M if N > 0 else 0.0
        ox[k], oy[k] = x[i] + s * ux, y[i] + s * uy
        ohead[k] = heading[i]; ovar[k] = VARIANT_KIOSK; oh[k] = KIOSK_HEIGHT_M; ocap[k] = N
        otext[k] = names[i]; ods[k] = dataset[i]
        oattrs[k] = json.dumps(dict(base, part="kiosk"), separators=(",", ":"))
        k += 1
        if N == 0:
            zero_capacity.append({"station_id": base["station_id"], "name": names[i]})
        nb = int(st_bikes[i])
        if nb:
            sid = str(base["station_id"])
            st = status["by_station"][sid]
            for j in range(nb):
                s = (j - (N - 1) / 2.0) * PITCH_M
                ox[k] = x[i] + s * ux - BIKE_SETBACK_M * fx
                oy[k] = y[i] + s * uy - BIKE_SETBACK_M * fy
                ohead[k] = heading[i]; ovar[k] = VARIANT_BIKE; oh[k] = BIKE_HEIGHT_M
                otext[k] = names[i]; ods[k] = STATUS_ID
                oattrs[k] = json.dumps(dict(base, part="bike", dock_index=j,
                                            snapshot_last_updated=status["last_updated"],
                                            num_bikes_available=st["num_bikes_available"],
                                            num_ebikes_available=st["num_ebikes_available"]),
                                       separators=(",", ":"))
                k += 1
    assert k == n_out
    out["x"], out["y"] = ox, oy
    out["heading"] = ohead
    out["variant"] = ovar
    out["capacity"] = ocap
    out["height_m"] = oh
    out["text"], out["dataset_id"], out["attrs"] = otext, ods, oattrs

    report.update({
        "kiosks": n_st, "docks": n_docks, "bikes": n_bikes, "rows_out": n_out,
        "zero_capacity": zero_capacity,
        "axis_source": {s: int(src.count(s)) for s in sorted(set(src))},
        "axis_distance_m": _pct(np.asarray(axes["distance_m"], dtype=np.float64)),
        "stations_with_no_axis": [
            {"station_id": attrs_in[i].get("station_id", ""), "name": names[i], "region_id": attrs_in[i].get("region_id", ""),
             "nearest_segment_m": (round(float(axes["distance_m"][i]), 1) if np.isfinite(axes["distance_m"][i]) else None)}
            for i in range(n_st) if src[i] == "none"],
        "run_length_m": _pct(run_len),
        "runs_over_30m": int((run_len > 30.0).sum()),
        "runs_longer_than_half_nearest_segment": int(np.nansum(run_len > 0.5 * seg_len)),
        "runs_longer_than_nearest_segment": int(np.nansum(run_len > seg_len)),
        "bikes_detail": bikes_rep,
    })
    log.info("citi bike: %d stations -> %d kiosks + %d docks + %d bikes (axis: %s)",
             n_st, n_st, n_docks, n_bikes, report["axis_source"])

    keep = {k_: (np.asarray(v)[others] if not isinstance(v, list) else [v[i] for i in others]) for k_, v in cols.items()}
    from .datasets import concat
    return concat([keep, out]), report


def apply(cols: dict, segments_path: Path, status_path: Path = STATUS) -> tuple[dict, dict]:
    """The build's entry point: axes from the segments table, status from disk, then :func:`expand`."""
    from .rules import load_segments
    kind_id = KIND_BY_NAME["citibike_dock"].id
    kind = np.asarray(cols["kind"], dtype=np.int16)
    rows = np.flatnonzero(kind == kind_id)
    seg = load_segments(Path(segments_path))
    axes = station_axes(np.asarray(cols["x"], dtype=np.float64)[rows], np.asarray(cols["y"], dtype=np.float64)[rows], seg)
    status = load_status(status_path)
    cols, report = expand(cols, kind_id, axes, status)
    report["status_snapshot_used"] = status is not None
    return cols, report
