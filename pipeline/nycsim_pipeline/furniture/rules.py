"""Rule-based props for objects the City publishes no location dataset for (``source = 1``).

Three objects are placed by rule against the **real** road geometry of ``roads/segments.parquet``
(DATA_CONTRACTS §7 — real CSCL centrelines, real curb-to-curb widths, real functional class):

======================  =========================================================================================
``street_lamp`` (14)    Every 30–40 m, alternating sides, on carriageways at least ``MIN_LAMP_WIDTH_M`` wide.
                        Spacing follows the NYC DOT street-lighting standard for arterial and local streets
                        (30–40 m staggered); the pole is offset ``width/2 + LAMP_CURB_OFFSET_M`` from the
                        centreline, i.e. just behind the curb. Suppressed within ``LAMP_COVER_M`` of a real
                        OSM ``highway=street_lamp`` node, so the rule only fills gaps.
``manhole`` (23)        Every ``MANHOLE_SPACING_M`` along the roadbed centreline of streets and alleys.
                        Suppressed within ``MANHOLE_COVER_M`` of a real OSM ``man_made=manhole`` node.
``steam_vent`` (33)     Con Edison's steam distribution system serves Manhattan from the Battery to 96th Street;
                        a vent stack is placed every ``STEAM_SPACING_M`` along the *wide* streets inside that
                        area (>= ``MIN_LAMP_WIDTH_M``, the avenues and major cross streets the mains follow).
                        Con Edison publishes no dataset of vent locations — the visible orange-and-white stacks
                        are temporary equipment over steam manholes — so every one of these is inferred, is
                        flagged ``source = 1``, and its count is a modelling choice, not a measurement.
======================  =========================================================================================

Everything here is deterministic: offsets along a segment are derived from a hash of ``segment_id`` only, so a
re-run produces byte-identical output, and no lamp/manhole is ever placed where a surveyed one already exists.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq
import shapely
from scipy.spatial import cKDTree

from ..crs import transformer
from ..paths import PROCESSED
from .catalog import HEIGHT_SOURCE, KIND_BY_NAME, KIND_ID, SOURCE_RULE
from .schema import empty_columns

log = logging.getLogger("nycsim.furniture.rules")

SEGMENTS = PROCESSED / "roads" / "segments.parquet"

# roadway classes that carry street lighting / utilities (DATA_CONTRACTS §7 rw_type)
RW_STREET = 1
RW_HIGHWAY = 2
RW_BRIDGE = 3
RW_ALLEY = 10
LIT_RW_TYPES = (RW_STREET, RW_HIGHWAY, RW_BRIDGE, RW_ALLEY)

MIN_LAMP_WIDTH_M = 9.0
LAMP_SPACING_MIN_M = 30.0
LAMP_SPACING_MAX_M = 40.0
LAMP_CURB_OFFSET_M = 0.6
LAMP_COVER_M = 25.0

MANHOLE_SPACING_M = 40.0
MANHOLE_COVER_M = 15.0

STEAM_SPACING_M = 400.0
# Con Edison steam service area: Manhattan (borough 1) south of West/East 96th Street.
STEAM_BOROUGH = 1
STEAM_NORTH_LIMIT_LAT = 40.7940   # W 96 St / Broadway


def steam_north_limit_y() -> float:
    """North edge of the Con Edison steam district in NYC_TM metres."""
    _x, y = transformer("WGS84", "NYC_TM").transform(-73.9712, STEAM_NORTH_LIMIT_LAT)
    return float(y)


def _hash01(v: np.ndarray, salt: int = 0) -> np.ndarray:
    """Deterministic uniform [0,1) from an integer key (splitmix64 finaliser)."""
    z = (v.astype(np.uint64, copy=True) + np.uint64(salt & 0xFFFFFFFFFFFFFFFF))
    z ^= z >> np.uint64(30)
    z *= np.uint64(0xBF58476D1CE4E5B9)
    z ^= z >> np.uint64(27)
    z *= np.uint64(0x94D049BB133111EB)
    z ^= z >> np.uint64(31)
    return (z >> np.uint64(11)).astype(np.float64) / float(1 << 53)


def _densify(line: shapely.Geometry, spacing: float, start: float) -> tuple[np.ndarray, np.ndarray]:
    """Points every ``spacing`` metres along a line from offset ``start``, with the local heading in degrees."""
    length = float(shapely.length(line))
    if length <= 0 or start >= length:
        return np.empty((0, 2)), np.empty(0)
    d = np.arange(start, length, spacing)
    if d.size == 0:
        return np.empty((0, 2)), np.empty(0)
    eps = min(1.0, max(length * 1e-3, 0.05))
    p0 = shapely.get_coordinates(shapely.line_interpolate_point(line, np.maximum(d - eps, 0.0)))[:, :2]
    p1 = shapely.get_coordinates(shapely.line_interpolate_point(line, np.minimum(d + eps, length)))[:, :2]
    p = shapely.get_coordinates(shapely.line_interpolate_point(line, d))[:, :2]
    t = p1 - p0
    n = np.hypot(t[:, 0], t[:, 1])
    n[n == 0] = 1.0
    heading = np.degrees(np.arctan2(t[:, 0] / n, t[:, 1] / n)) % 360.0
    return p, heading


def load_segments(path: Path = SEGMENTS):
    """Read the road segments the rules need. Returns ``None`` when the roads stage has not produced them."""
    if not path.exists():
        return None
    t = pq.read_table(path, columns=["segment_id", "geometry", "rw_type", "width_m", "borough"])
    geoms = shapely.from_wkb(t.column("geometry").to_pylist())
    return {
        "segment_id": t.column("segment_id").to_numpy(zero_copy_only=False).astype(np.int64),
        "geometry": geoms,
        "rw_type": t.column("rw_type").to_numpy(zero_copy_only=False).astype(np.int8),
        "width_m": t.column("width_m").to_numpy(zero_copy_only=False).astype(np.float64),
        "borough": t.column("borough").to_numpy(zero_copy_only=False).astype(np.int8),
    }


def _rows(kind_name: str, x: np.ndarray, y: np.ndarray, heading: np.ndarray, rule_id: str,
          variant: np.ndarray | None = None) -> dict:
    n = len(x)
    cols = empty_columns(n)
    cols["kind"] = np.full(n, KIND_ID[kind_name], dtype=np.int16)
    cols["source"] = np.full(n, SOURCE_RULE, dtype=np.int8)
    cols["dataset_id"] = [rule_id] * n
    cols["x"] = np.asarray(x, dtype=np.float64)
    cols["y"] = np.asarray(y, dtype=np.float64)
    cols["heading"] = np.asarray(heading, dtype=np.float32)
    if variant is not None:
        cols["variant"] = np.asarray(variant, dtype=np.int16)
    k = KIND_BY_NAME[kind_name]
    if k.dims_m[2] > 0:
        cols["height_m"] = np.full(n, k.dims_m[2], dtype=np.float32)
        cols["height_source"] = np.full(n, HEIGHT_SOURCE["nominal"], dtype=np.int8)
    else:
        cols["height_source"] = np.full(n, HEIGHT_SOURCE["none"], dtype=np.int8)
    return cols


def _suppress(x: np.ndarray, y: np.ndarray, existing_xy: np.ndarray, radius: float) -> np.ndarray:
    """Keep-mask: drop generated points within ``radius`` of an existing surveyed/mapped object."""
    if len(x) == 0:
        return np.zeros(0, dtype=bool)
    if existing_xy.size == 0:
        return np.ones(len(x), dtype=bool)
    d, _ = cKDTree(existing_xy).query(np.column_stack([x, y]), k=1, workers=1)
    return d > radius


def street_lamps(seg: dict, existing_lamp_xy: np.ndarray) -> dict:
    keep = np.isin(seg["rw_type"], LIT_RW_TYPES) & np.isfinite(seg["width_m"]) & (seg["width_m"] >= MIN_LAMP_WIDTH_M)
    idx = np.flatnonzero(keep)
    log.info("street lamp rule: %d of %d segments are >= %.1f m wide and lit classes", idx.size, len(seg["rw_type"]), MIN_LAMP_WIDTH_M)
    xs: list[np.ndarray] = []
    ys: list[np.ndarray] = []
    hs: list[np.ndarray] = []
    # The road class each pole was placed against, carried into ``attrs`` so a later rule can tell a
    # park drive from the parkway that runs through the same grass (:mod:`.park_lamps`).  Asking
    # "which segment is nearest this pole" afterwards would answer a different question.
    rws: list[np.ndarray] = []
    r = _hash01(seg["segment_id"])
    for i in idx:
        line = seg["geometry"][i]
        if line is None or line.is_empty:
            continue
        spacing = LAMP_SPACING_MIN_M + (LAMP_SPACING_MAX_M - LAMP_SPACING_MIN_M) * r[i]
        start = spacing * (0.25 + 0.5 * r[i])
        p, head = _densify(line, spacing, start)
        if len(p) == 0:
            continue
        off = seg["width_m"][i] * 0.5 + LAMP_CURB_OFFSET_M
        side = np.where(np.arange(len(p)) % 2 == 0, 1.0, -1.0)
        # unit vector 90 deg clockwise from the compass heading, i.e. to the right of travel
        right = np.radians(head + 90.0)
        nx = np.sin(right)
        ny = np.cos(right)
        xs.append(p[:, 0] + side * off * nx)
        ys.append(p[:, 1] + side * off * ny)
        # the lamp head overhangs the roadway: it faces the centreline, i.e. opposite the offset direction
        hs.append((head + np.where(side > 0, 270.0, 90.0)) % 360.0)
        rws.append(np.full(len(p), int(seg["rw_type"][i]), dtype=np.int16))
    if not xs:
        return _rows("street_lamp", np.empty(0), np.empty(0), np.empty(0), "rule:lamp_30_40m_alt")
    x, y, h = np.concatenate(xs), np.concatenate(ys), np.concatenate(hs)
    rw = np.concatenate(rws)
    m = _suppress(x, y, existing_lamp_xy, LAMP_COVER_M)
    log.info("street lamp rule: %d generated, %d suppressed near a mapped lamp, %d kept",
             len(x), int((~m).sum()), int(m.sum()))
    # variant 1 = cobra head (the NYC DOT standard pole this rule represents)
    cols = _rows("street_lamp", x[m], y[m], h[m], "rule:lamp_30_40m_alt", np.ones(int(m.sum()), dtype=np.int16))
    cols["attrs"] = [json.dumps({"rw_type": int(v)}, separators=(",", ":")) for v in rw[m]]
    return cols


def manholes_and_steam(seg: dict, existing_manhole_xy: np.ndarray) -> tuple[dict, dict]:
    keep = np.isin(seg["rw_type"], LIT_RW_TYPES)
    idx = np.flatnonzero(keep)
    r = _hash01(seg["segment_id"], salt=0x9E3779B97F4A7C15)
    y_limit = steam_north_limit_y()
    mx: list[np.ndarray] = []
    my: list[np.ndarray] = []
    mh: list[np.ndarray] = []
    sx: list[np.ndarray] = []
    sy: list[np.ndarray] = []
    sh: list[np.ndarray] = []
    for i in idx:
        line = seg["geometry"][i]
        if line is None or line.is_empty:
            continue
        p, head = _densify(line, MANHOLE_SPACING_M, MANHOLE_SPACING_M * r[i])
        if len(p) == 0:
            continue
        mx.append(p[:, 0])
        my.append(p[:, 1])
        mh.append(head)
        if seg["borough"][i] == STEAM_BOROUGH and seg["width_m"][i] >= MIN_LAMP_WIDTH_M:
            q, qh = _densify(line, STEAM_SPACING_M, STEAM_SPACING_M * r[i])
            if len(q):
                inside = q[:, 1] <= y_limit
                if inside.any():
                    sx.append(q[inside, 0])
                    sy.append(q[inside, 1])
                    sh.append(qh[inside])
    if mx:
        x, y, h = np.concatenate(mx), np.concatenate(my), np.concatenate(mh)
        m = _suppress(x, y, existing_manhole_xy, MANHOLE_COVER_M)
        log.info("manhole rule: %d generated, %d suppressed near a mapped manhole, %d kept",
                 len(x), int((~m).sum()), int(m.sum()))
        manholes = _rows("manhole", x[m], y[m], h[m], "rule:manhole_40m")
    else:
        manholes = _rows("manhole", np.empty(0), np.empty(0), np.empty(0), "rule:manhole_40m")
    if sx:
        x, y, h = np.concatenate(sx), np.concatenate(sy), np.concatenate(sh)
        log.info("steam vent rule: %d placed inside the Con Edison steam district", len(x))
        steam = _rows("steam_vent", x, y, h, "rule:steam_vent_400m_manhattan_below_96")
    else:
        steam = _rows("steam_vent", np.empty(0), np.empty(0), np.empty(0), "rule:steam_vent_400m_manhattan_below_96")
    return manholes, steam


def build_rule_props(existing: dict, segments_path: Path = SEGMENTS) -> tuple[list[dict], dict]:
    """Generate every rule-based prop. ``existing`` maps a kind name to the (N,2) array of surveyed positions.

    Returns ``([column dicts], report)``. When ``roads/segments.parquet`` is absent nothing is generated and the
    report says so — the road-derived fill is skipped rather than faked.
    """
    seg = load_segments(segments_path)
    if seg is None:
        log.warning("roads/segments.parquet absent — street lamp / manhole / steam vent fill skipped")
        return [], {"skipped": True, "reason": f"{segments_path} does not exist (roads stage has not produced it)",
                    "rules": []}
    lamps = street_lamps(seg, existing.get("street_lamp", np.empty((0, 2))))
    manholes, steam = manholes_and_steam(seg, existing.get("manhole", np.empty((0, 2))))
    parts = [p for p in (lamps, manholes, steam) if len(p["x"])]
    report = {
        "skipped": False,
        "segments_read": int(len(seg["rw_type"])),
        "rules": [
            {"rule": "rule:lamp_30_40m_alt", "kind": "street_lamp", "count": int(len(lamps["x"])),
             "spec": f"every {LAMP_SPACING_MIN_M:.0f}-{LAMP_SPACING_MAX_M:.0f} m alternating sides on rw_type "
                     f"{LIT_RW_TYPES} with width_m >= {MIN_LAMP_WIDTH_M}, offset width/2 + {LAMP_CURB_OFFSET_M} m, "
                     f"suppressed within {LAMP_COVER_M} m of an OSM street_lamp"},
            {"rule": "rule:manhole_40m", "kind": "manhole", "count": int(len(manholes["x"])),
             "spec": f"every {MANHOLE_SPACING_M:.0f} m on the centreline of rw_type {LIT_RW_TYPES}, suppressed "
                     f"within {MANHOLE_COVER_M} m of an OSM manhole"},
            {"rule": "rule:steam_vent_400m_manhattan_below_96", "kind": "steam_vent", "count": int(len(steam["x"])),
             "spec": f"every {STEAM_SPACING_M:.0f} m along streets at least {MIN_LAMP_WIDTH_M} m wide in Manhattan "
                     f"south of 96th Street (y <= {steam_north_limit_y():.1f} m NYC_TM), the Con Edison steam "
                     f"district; no dataset of vent locations exists, so the count is a modelling choice"},
        ],
    }
    return parts, report
