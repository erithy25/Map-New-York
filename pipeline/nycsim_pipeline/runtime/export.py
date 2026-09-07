"""Map the processed road, building and tile artefacts onto the NYCB runtime containers of DATA_CONTRACTS §15.

    python -m nycsim_pipeline.runtime.export [--roads-dir DIR] [--buildings-dir DIR] [--tiles-dir DIR] [--out-dir DIR]

Produces ``data/processed/runtime/roadgraph.nycb``, ``signals.nycb``, ``pois.nycb``, ``tiles.nycb`` and
``landmarks.nycb`` plus ``nycb_layout.json`` (the exact field offsets so ``core/io/NycbReader.h`` can be checked
mechanically against this writer). ``transit.nycb`` and ``density.nycb`` are the transit and traffic stages' own
outputs; between the seven that is all of §15.

Section record layouts are declared as naturally aligned numpy dtypes, which reproduce byte for byte what a
C++17 compiler lays out for the structs in §15 on any LP64 little-endian target. Every field order, type and
name below is taken verbatim from §15; the module asserts the resulting ``sizeof`` at import time, so a typo
fails loudly instead of silently shifting the C++ side.

Shared indices
* ``vertices`` holds segment polylines first, then lane polylines, then junction-lane polylines. Every record
  that carries ``first_vertex``/``vertex_count`` indexes into that one array.
* ``lane_links`` is the concatenation of the lanes' successor lists; ``lanes.first_succ``/``succ_count`` index
  into it. ``yield_links`` does the same for ``junction_lanes.yield_to``.
* ``strtab`` is the NUL-separated UTF-8 blob; ``segments.name_str`` is a byte offset into it.

Point sections (``pois``, ``points``)
* The point is the **footprint centroid** already carried by the buildings tables as ``centroid_x``/``centroid_y``
  (§5.2), not a recomputed one: it is the same point the buildings stage assigns the tile from, so a searched address
  and its building agree on which tile they belong to by construction. Storing it as float32 costs at most 1 mm over
  the NYC_TM extent (|x|,|y| < 26 km), far below the precision of the source geometry.
* A row with no name/address is not emitted. Nothing is synthesised to fill one: ``RoadNetwork::loadPois`` and
  ``loadLandmarks`` skip an empty label anyway, so an invented string would be the only way such a row could ever
  reach a player.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq
import shapely

from ..paths import PROCESSED
from .nycb import NycbReader, NycbWriter, aligned_dtype

log = logging.getLogger("nycsim.runtime.export")

NODE_DTYPE = aligned_dtype([
    ("id", "<i8"), ("x", "<f4"), ("y", "<f4"), ("z", "<f4"),
    ("control", "u1"), ("signal_source", "u1"), ("pad", "<u2"),
])
SEGMENT_DTYPE = aligned_dtype([
    ("id", "<i8"), ("from_node", "<i8"), ("to_node", "<i8"),
    ("first_vertex", "<u4"), ("vertex_count", "<u4"),
    ("rw_type", "u1"), ("traffic_dir", "u1"), ("travel_lanes", "u1"), ("park_lanes", "u1"),
    ("width_m", "<f4"),
    ("speed_mph", "u1"), ("bike_lane", "u1"), ("surface", "u1"), ("borough", "u1"),
    ("name_str", "<u4"),
])
VERTEX_DTYPE = aligned_dtype([("x", "<f4"), ("y", "<f4"), ("z", "<f4")])
LANE_DTYPE = aligned_dtype([
    ("id", "<i8"), ("segment_id", "<i8"),
    ("index_from_center", "i1"), ("direction", "i1"), ("kind", "i1"), ("pad", "i1"),
    ("width_m", "<f4"), ("speed_mps", "<f4"),
    ("first_vertex", "<u4"), ("vertex_count", "<u4"),
    ("first_succ", "<u4"), ("succ_count", "<u4"),
])
LANE_LINK_DTYPE = aligned_dtype([("lane_id", "<i8")])
JUNCTION_DTYPE = aligned_dtype([
    ("id", "<i8"), ("from_lane", "<i8"), ("to_lane", "<i8"),
    ("turn", "u1"), ("pad", "u1", (3,)),
    ("signal_group", "<i4"),
    ("first_vertex", "<u4"), ("vertex_count", "<u4"),
    ("first_yield", "<u4"), ("yield_count", "<u4"),
])
YIELD_LINK_DTYPE = aligned_dtype([("lane_id", "<i8")])
CONTROLLER_DTYPE = aligned_dtype([
    ("node_id", "<i8"), ("controller_id", "<i4"),
    ("cycle_s", "<f4"), ("offset_s", "<f4"),
    ("first_phase", "<u4"), ("phase_count", "<u4"),
])
PHASE_DTYPE = aligned_dtype([
    ("group", "<i4"), ("green_s", "<f4"), ("yellow_s", "<f4"), ("allred_s", "<f4"),
    ("ped_walk_s", "<f4"), ("ped_flash_s", "<f4"), ("lpi_s", "<f4"),
])
POI_DTYPE = aligned_dtype([("x", "<f4"), ("y", "<f4"), ("addr_str", "<u4")])
TILE_DTYPE = aligned_dtype([
    ("tx", "<i4"), ("ty", "<i4"), ("z_min", "<f4"), ("z_max", "<f4"),
    ("n_buildings", "<u4"), ("n_props", "<u4"),
    ("flags", "u1"), ("borough_mask", "u1"), ("pad", "<u2"),
])
# landmarks.nycb `points`: the same record as `pois` under the name RoadNetwork::loadLandmarks() looks for.
LANDMARK_DTYPE = aligned_dtype([("x", "<f4"), ("y", "<f4"), ("name_str", "<u4")])

EXPECTED_SIZEOF = {
    "nodes": 24, "segments": 48, "vertices": 12, "lanes": 48, "lane_links": 8,
    "junction_lanes": 48, "yield_links": 8, "controllers": 32, "phases": 28,
    "pois": 12, "tiles": 28, "points": 12,
}
ROADGRAPH_DTYPES = {"nodes": NODE_DTYPE, "segments": SEGMENT_DTYPE, "vertices": VERTEX_DTYPE, "lanes": LANE_DTYPE,
                    "lane_links": LANE_LINK_DTYPE, "junction_lanes": JUNCTION_DTYPE, "yield_links": YIELD_LINK_DTYPE}
SIGNAL_DTYPES = {"controllers": CONTROLLER_DTYPE, "phases": PHASE_DTYPE}
POI_DTYPES = {"pois": POI_DTYPE}
TILE_DTYPES = {"tiles": TILE_DTYPE}
LANDMARK_DTYPES = {"points": LANDMARK_DTYPE}
ALL_DTYPES = {**ROADGRAPH_DTYPES, **SIGNAL_DTYPES, **POI_DTYPES, **TILE_DTYPES, **LANDMARK_DTYPES}
for _n, _d in ALL_DTYPES.items():
    if _d.itemsize != EXPECTED_SIZEOF[_n]:
        raise AssertionError(f"NYCB section {_n!r}: sizeof {_d.itemsize} != contract {EXPECTED_SIZEOF[_n]}")

SIG_NONE = 255
NO_SIGNAL_GROUP = -1
# tiles.flags, per §15 and FNYCTileRecord in unreal/.../CoreAdapter/NYCNycb.h.
FLAG_HAS_TERRAIN = 1
FLAG_HAS_WATER = 2
FLAG_HAS_LAND = 4


def _flatten(geoms: np.ndarray, base: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """3-D coordinates of a geometry array plus (first_vertex, vertex_count) offset by ``base``."""
    if len(geoms) == 0:
        return np.zeros((0, 3), dtype=np.float32), np.zeros(0, dtype=np.uint32), np.zeros(0, dtype=np.uint32)
    coords = shapely.get_coordinates(geoms, include_z=True)
    counts = shapely.get_num_coordinates(geoms).astype(np.uint32)
    firsts = (np.concatenate([[0], np.cumsum(counts, dtype=np.int64)[:-1]]) + base).astype(np.uint32)
    xyz = np.nan_to_num(coords, nan=0.0).astype(np.float32)
    return xyz, firsts, counts


def _u8(v: np.ndarray) -> np.ndarray:
    return np.clip(np.nan_to_num(np.asarray(v, dtype=np.float64), nan=0.0), 0, 255).astype(np.uint8)


def export_roadgraph(roads_dir: Path, out_path: Path) -> dict:
    t0 = time.time()
    seg_t = pq.read_table(roads_dir / "segments.parquet",
                          columns=["segment_id", "from_node", "to_node", "geometry", "street_name", "rw_type",
                                   "traffic_dir", "travel_lanes", "park_lanes", "width_m", "posted_speed_mph",
                                   "bike_lane", "surface", "borough"])
    node_t = pq.read_table(roads_dir / "nodes.parquet", columns=["node_id", "x", "y", "z", "control", "signal_source"])
    lane_t = pq.read_table(roads_dir / "lanes.parquet",
                           columns=["lane_id", "segment_id", "index_from_center", "direction", "kind", "width_m",
                                    "speed_mps", "geometry", "successors"])
    jl_t = pq.read_table(roads_dir / "junction_lanes.parquet",
                         columns=["junction_lane_id", "from_lane", "to_lane", "turn", "signal_group", "yield_to", "geometry"])

    w = NycbWriter()

    nodes = np.zeros(node_t.num_rows, dtype=NODE_DTYPE)
    nodes["id"] = node_t.column("node_id").to_numpy(zero_copy_only=False).astype(np.int64)
    nodes["x"] = node_t.column("x").to_numpy(zero_copy_only=False).astype(np.float32)
    nodes["y"] = node_t.column("y").to_numpy(zero_copy_only=False).astype(np.float32)
    nodes["z"] = np.nan_to_num(node_t.column("z").to_numpy(zero_copy_only=False).astype(np.float32), nan=0.0)
    nodes["control"] = _u8(node_t.column("control").to_numpy(zero_copy_only=False))
    nodes["signal_source"] = _u8(node_t.column("signal_source").to_numpy(zero_copy_only=False))

    seg_geom = shapely.from_wkb(seg_t.column("geometry").to_numpy(zero_copy_only=False))
    seg_xyz, seg_first, seg_count = _flatten(seg_geom, 0)
    lane_geom = shapely.from_wkb(lane_t.column("geometry").to_numpy(zero_copy_only=False))
    lane_xyz, lane_first, lane_count = _flatten(lane_geom, len(seg_xyz))
    jl_geom = shapely.from_wkb(jl_t.column("geometry").to_numpy(zero_copy_only=False))
    jl_xyz, jl_first, jl_count = _flatten(jl_geom, len(seg_xyz) + len(lane_xyz))
    verts = np.zeros(len(seg_xyz) + len(lane_xyz) + len(jl_xyz), dtype=VERTEX_DTYPE)
    allxyz = np.concatenate([seg_xyz, lane_xyz, jl_xyz]) if len(verts) else np.zeros((0, 3), dtype=np.float32)
    verts["x"] = allxyz[:, 0]
    verts["y"] = allxyz[:, 1]
    verts["z"] = allxyz[:, 2]

    segments = np.zeros(seg_t.num_rows, dtype=SEGMENT_DTYPE)
    segments["id"] = seg_t.column("segment_id").to_numpy(zero_copy_only=False).astype(np.int64)
    segments["from_node"] = seg_t.column("from_node").to_numpy(zero_copy_only=False).astype(np.int64)
    segments["to_node"] = seg_t.column("to_node").to_numpy(zero_copy_only=False).astype(np.int64)
    segments["first_vertex"] = seg_first
    segments["vertex_count"] = seg_count
    for dst, src in (("rw_type", "rw_type"), ("traffic_dir", "traffic_dir"), ("travel_lanes", "travel_lanes"),
                     ("park_lanes", "park_lanes"), ("speed_mph", "posted_speed_mph"), ("bike_lane", "bike_lane"),
                     ("surface", "surface"), ("borough", "borough")):
        segments[dst] = _u8(seg_t.column(src).to_numpy(zero_copy_only=False))
    segments["width_m"] = np.nan_to_num(seg_t.column("width_m").to_numpy(zero_copy_only=False).astype(np.float32), nan=0.0)
    segments["name_str"] = w.strings.add_many(seg_t.column("street_name").to_pylist())

    succ_lists = lane_t.column("successors").to_pylist()
    succ_counts = np.array([len(v) if v is not None else 0 for v in succ_lists], dtype=np.uint32)
    succ_first = np.concatenate([[0], np.cumsum(succ_counts, dtype=np.int64)[:-1]]).astype(np.uint32) if len(succ_counts) else np.zeros(0, dtype=np.uint32)
    flat_succ = np.fromiter((int(x) for v in succ_lists if v for x in v), dtype=np.int64,
                            count=int(succ_counts.sum()))
    lane_links = np.zeros(len(flat_succ), dtype=LANE_LINK_DTYPE)
    lane_links["lane_id"] = flat_succ

    lanes = np.zeros(lane_t.num_rows, dtype=LANE_DTYPE)
    lanes["id"] = lane_t.column("lane_id").to_numpy(zero_copy_only=False).astype(np.int64)
    lanes["segment_id"] = lane_t.column("segment_id").to_numpy(zero_copy_only=False).astype(np.int64)
    lanes["index_from_center"] = lane_t.column("index_from_center").to_numpy(zero_copy_only=False).astype(np.int8)
    lanes["direction"] = lane_t.column("direction").to_numpy(zero_copy_only=False).astype(np.int8)
    lanes["kind"] = lane_t.column("kind").to_numpy(zero_copy_only=False).astype(np.int8)
    lanes["width_m"] = lane_t.column("width_m").to_numpy(zero_copy_only=False).astype(np.float32)
    lanes["speed_mps"] = lane_t.column("speed_mps").to_numpy(zero_copy_only=False).astype(np.float32)
    lanes["first_vertex"] = lane_first
    lanes["vertex_count"] = lane_count
    lanes["first_succ"] = succ_first
    lanes["succ_count"] = succ_counts

    yield_lists = jl_t.column("yield_to").to_pylist()
    y_counts = np.array([len(v) if v is not None else 0 for v in yield_lists], dtype=np.uint32)
    y_first = np.concatenate([[0], np.cumsum(y_counts, dtype=np.int64)[:-1]]).astype(np.uint32) if len(y_counts) else np.zeros(0, dtype=np.uint32)
    flat_yield = np.fromiter((int(x) for v in yield_lists if v for x in v), dtype=np.int64, count=int(y_counts.sum()))
    yield_links = np.zeros(len(flat_yield), dtype=YIELD_LINK_DTYPE)
    yield_links["lane_id"] = flat_yield

    jl = np.zeros(jl_t.num_rows, dtype=JUNCTION_DTYPE)
    jl["id"] = jl_t.column("junction_lane_id").to_numpy(zero_copy_only=False).astype(np.int64)
    jl["from_lane"] = jl_t.column("from_lane").to_numpy(zero_copy_only=False).astype(np.int64)
    jl["to_lane"] = jl_t.column("to_lane").to_numpy(zero_copy_only=False).astype(np.int64)
    jl["turn"] = _u8(jl_t.column("turn").to_numpy(zero_copy_only=False))
    jl["signal_group"] = jl_t.column("signal_group").to_numpy(zero_copy_only=False).astype(np.int32)
    jl["first_vertex"] = jl_first
    jl["vertex_count"] = jl_count
    jl["first_yield"] = y_first
    jl["yield_count"] = y_counts

    w.add_array("nodes", nodes)
    w.add_array("segments", segments)
    w.add_array("vertices", verts)
    w.add_array("lanes", lanes)
    w.add_array("lane_links", lane_links)
    w.add_array("junction_lanes", jl)
    w.add_array("yield_links", yield_links)
    w.add_strtab()
    w.write(out_path)
    st = {"path": str(out_path), "bytes": out_path.stat().st_size, "sections": w.section_names(),
          "counts": {"nodes": len(nodes), "segments": len(segments), "vertices": len(verts), "lanes": len(lanes),
                     "lane_links": len(lane_links), "junction_lanes": len(jl), "yield_links": len(yield_links),
                     "strtab_bytes": len(w.strings)},
          "seconds": round(time.time() - t0, 2)}
    log.info("roadgraph.nycb: %s", st["counts"])
    return st


def export_signals(roads_dir: Path, out_path: Path) -> dict:
    t0 = time.time()
    t = pq.read_table(roads_dir / "signals.parquet", columns=["node_id", "controller_id", "cycle_s", "offset_s", "phases"])
    phases_col = t.column("phases").to_pylist()
    counts = np.array([len(p) if p is not None else 0 for p in phases_col], dtype=np.uint32)
    first = np.concatenate([[0], np.cumsum(counts, dtype=np.int64)[:-1]]).astype(np.uint32) if len(counts) else np.zeros(0, dtype=np.uint32)
    total = int(counts.sum())
    phases = np.zeros(total, dtype=PHASE_DTYPE)
    k = 0
    for plist in phases_col:
        for p in (plist or []):
            phases[k]["group"] = int(p["group"])
            phases[k]["green_s"] = float(p["green_s"])
            phases[k]["yellow_s"] = float(p["yellow_s"])
            phases[k]["allred_s"] = float(p["allred_s"])
            phases[k]["ped_walk_s"] = float(p["ped_walk_s"])
            phases[k]["ped_flash_s"] = float(p["ped_flash_s"])
            phases[k]["lpi_s"] = float(p["lpi_s"])
            k += 1
    ctrl = np.zeros(t.num_rows, dtype=CONTROLLER_DTYPE)
    ctrl["node_id"] = t.column("node_id").to_numpy(zero_copy_only=False).astype(np.int64)
    ctrl["controller_id"] = t.column("controller_id").to_numpy(zero_copy_only=False).astype(np.int32)
    ctrl["cycle_s"] = t.column("cycle_s").to_numpy(zero_copy_only=False).astype(np.float32)
    ctrl["offset_s"] = t.column("offset_s").to_numpy(zero_copy_only=False).astype(np.float32)
    ctrl["first_phase"] = first
    ctrl["phase_count"] = counts

    w = NycbWriter()
    w.add_array("controllers", ctrl)
    w.add_array("phases", phases)
    w.write(out_path)
    st = {"path": str(out_path), "bytes": out_path.stat().st_size, "sections": w.section_names(),
          "counts": {"controllers": len(ctrl), "phases": len(phases)}, "seconds": round(time.time() - t0, 2)}
    log.info("signals.nycb: %s", st["counts"])
    return st


def _point_section(x: np.ndarray, y: np.ndarray, labels: list, dtype: np.dtype, str_field: str,
                   w: NycbWriter) -> tuple[np.ndarray, dict]:
    """Build a ``{float x, float y, uint32 <str_field>}`` array, dropping unlabelled rows and exact duplicates.

    A duplicate is an identical ``(label, x, y)`` triple *after* the float32 narrowing that the record stores, so
    two rows that only the parquet's float64 can tell apart are still one point on disk and are collapsed to one
    record. Distinct positions sharing a label are kept: they are different buildings that really do carry the same
    address or name, and dropping them would delete real geometry from the index.
    """
    total = len(labels)
    has_label = np.array([bool(s) for s in labels], dtype=bool)
    x32 = np.nan_to_num(np.asarray(x, dtype=np.float64), nan=0.0).astype(np.float32)
    y32 = np.nan_to_num(np.asarray(y, dtype=np.float64), nan=0.0).astype(np.float32)
    finite = np.isfinite(np.asarray(x, dtype=np.float64)) & np.isfinite(np.asarray(y, dtype=np.float64))
    keep = has_label & finite
    idx = np.flatnonzero(keep)
    seen: set[tuple] = set()
    rows: list[int] = []
    dup = 0
    for i in idx.tolist():
        key = (labels[i], float(x32[i]), float(y32[i]))
        if key in seen:
            dup += 1
            continue
        seen.add(key)
        rows.append(i)
    sel = np.asarray(rows, dtype=np.int64)
    out = np.zeros(len(sel), dtype=dtype)
    if len(sel):
        out["x"] = x32[sel]
        out["y"] = y32[sel]
        out[str_field] = w.strings.add_many(labels[i] for i in sel.tolist())
    dropped = {"no_label": int(total - int(has_label.sum())),
               "non_finite_point": int(np.count_nonzero(has_label & ~finite)),
               "duplicate_label_and_point": dup}
    return out, dropped


def export_pois(buildings_dir: Path, out_path: Path) -> dict:
    """§15 ``runtime/pois.nycb``: one address point per building that has an address.

    Source is ``buildings/buildings_base.parquet`` — the PLUTO/PAD address the buildings stage joined onto each
    footprint (§5.2) — at the footprint centroid the same table carries. Buildings with ``address == ""`` (unknown,
    per §5.2) are simply absent; there is no address to write for them and none is made up.
    """
    t0 = time.time()
    t = pq.read_table(buildings_dir / "buildings_base.parquet", columns=["address", "centroid_x", "centroid_y"])
    addrs = t.column("address").to_pylist()
    w = NycbWriter()
    pois, dropped = _point_section(t.column("centroid_x").to_numpy(zero_copy_only=False),
                                   t.column("centroid_y").to_numpy(zero_copy_only=False),
                                   addrs, POI_DTYPE, "addr_str", w)
    w.add_array("pois", pois)
    w.add_strtab()
    w.write(out_path)
    st = {"path": str(out_path), "bytes": out_path.stat().st_size, "sections": w.section_names(),
          "counts": {"pois": len(pois), "strtab_bytes": len(w.strings)},
          "source_rows": t.num_rows, "dropped": dropped, "seconds": round(time.time() - t0, 2)}
    log.info("pois.nycb: %d of %d buildings, dropped %s", len(pois), t.num_rows, dropped)
    return st


def _tile_row_counts(tiles_dir: Path, name: str) -> tuple[int, int]:
    """(buildings, props) actually present for one tile, from the parquet footers of its own artefacts.

    ``tiles/index.parquet`` declares ``n_buildings``/``n_props`` columns (§2) but the terrain stage that writes the
    index does not own them (its ``nycsim.terrain_columns`` metadata lists the eleven columns it does own) and they
    are zero for every tile, so the counts are taken from the per-tile artefacts instead. ``buildings.parquet`` is
    the NYC footprint set and ``buildings_nj.parquet`` the New Jersey one; a tile's building count is what a tile
    load would actually instantiate, which is both.
    """
    d = tiles_dir / name
    n_b = 0
    for stem in ("buildings.parquet", "buildings_nj.parquet"):
        p = d / stem
        if p.exists():
            n_b += pq.ParquetFile(p).metadata.num_rows
    p = d / "props.parquet"
    n_p = pq.ParquetFile(p).metadata.num_rows if p.exists() else 0
    return n_b, n_p


def export_tiles(tiles_dir: Path, out_path: Path) -> dict:
    """§15 ``runtime/tiles.nycb``: the streaming subsystem's tile table, one record per row of ``tiles/index.parquet``.

    Every tile in the index is written, New Jersey included. The tile table is what
    ``NYCTileStreamingSubsystem`` uses to decide a tile exists at all ("not present in tiles.nycb" = never streamed),
    ``FNYCTilesTable`` reserves a ``borough_mask`` bit for NJ (code 6), and the NJ tiles carry real content: terrain
    for all of them, props, and the ``buildings_nj.parquet`` footprints that are visible across the Hudson from
    Manhattan's west side. Excluding them would make real, shipped geometry unloadable.
    """
    t0 = time.time()
    t = pq.read_table(tiles_dir / "index.parquet",
                      columns=["tile", "tx", "ty", "z_min", "z_max", "has_terrain", "has_water", "has_land",
                               "borough_codes"])
    names = t.column("tile").to_pylist()
    rec = np.zeros(t.num_rows, dtype=TILE_DTYPE)
    rec["tx"] = t.column("tx").to_numpy(zero_copy_only=False).astype(np.int32)
    rec["ty"] = t.column("ty").to_numpy(zero_copy_only=False).astype(np.int32)
    rec["z_min"] = np.nan_to_num(t.column("z_min").to_numpy(zero_copy_only=False).astype(np.float32), nan=0.0)
    rec["z_max"] = np.nan_to_num(t.column("z_max").to_numpy(zero_copy_only=False).astype(np.float32), nan=0.0)

    ter = t.column("has_terrain").to_numpy(zero_copy_only=False).astype(bool)
    wat = t.column("has_water").to_numpy(zero_copy_only=False).astype(bool)
    lnd = t.column("has_land").to_numpy(zero_copy_only=False).astype(bool)
    rec["flags"] = (ter * FLAG_HAS_TERRAIN + wat * FLAG_HAS_WATER + lnd * FLAG_HAS_LAND).astype(np.uint8)

    codes = t.column("borough_codes").to_pylist()
    mask = np.zeros(t.num_rows, dtype=np.uint8)
    for i, cl in enumerate(codes):
        m = 0
        for c in (cl or []):
            c = int(c)
            if not 0 <= c <= 7:
                raise ValueError(f"tile {names[i]}: borough code {c} does not fit the uint8 borough_mask")
            m |= 1 << c
        mask[i] = m
    rec["borough_mask"] = mask

    n_b = np.zeros(t.num_rows, dtype=np.uint32)
    n_p = np.zeros(t.num_rows, dtype=np.uint32)
    for i, name in enumerate(names):
        b, p = _tile_row_counts(tiles_dir, name)
        n_b[i] = b
        n_p[i] = p
    rec["n_buildings"] = n_b
    rec["n_props"] = n_p

    w = NycbWriter()
    w.add_array("tiles", rec)
    w.write(out_path)
    st = {"path": str(out_path), "bytes": out_path.stat().st_size, "sections": w.section_names(),
          "counts": {"tiles": len(rec)},
          "totals": {"buildings": int(n_b.sum()), "props": int(n_p.sum()),
                     "tiles_with_buildings": int((n_b > 0).sum()), "tiles_with_props": int((n_p > 0).sum()),
                     "tiles_with_nj": int(((mask & (1 << 6)) != 0).sum())},
          "seconds": round(time.time() - t0, 2)}
    log.info("tiles.nycb: %s %s", st["counts"], st["totals"])
    return st


def export_landmarks(buildings_dir: Path, out_path: Path) -> dict:
    """§15 ``runtime/landmarks.nycb``: the named-landmark point set for the GPS index.

    Layout is not a choice: ``RoadNetwork::loadLandmarks()`` reads a section named ``points`` (falling back to
    ``landmarks``) of ``{float x, float y, uint32 name_str}`` and requires a ``strtab``, and says exactly that in the
    note it logs when it cannot. Source is ``buildings/landmark_footprints.parquet`` — the landmark stage's matched
    footprints, which carry the canonical designation name, the LPC ``lp_number`` and a centroid (§11's shape).
    """
    t0 = time.time()
    t = pq.read_table(buildings_dir / "landmark_footprints.parquet", columns=["name", "centroid_x", "centroid_y"])
    w = NycbWriter()
    pts, dropped = _point_section(t.column("centroid_x").to_numpy(zero_copy_only=False),
                                  t.column("centroid_y").to_numpy(zero_copy_only=False),
                                  t.column("name").to_pylist(), LANDMARK_DTYPE, "name_str", w)
    w.add_array("points", pts)
    w.add_strtab()
    w.write(out_path)
    st = {"path": str(out_path), "bytes": out_path.stat().st_size, "sections": w.section_names(),
          "counts": {"points": len(pts), "strtab_bytes": len(w.strings)},
          "source_rows": t.num_rows, "dropped": dropped, "seconds": round(time.time() - t0, 2)}
    log.info("landmarks.nycb: %d of %d landmarks, dropped %s", len(pts), t.num_rows, dropped)
    return st


# --------------------------------------------------------------------------- readers (round-trip tests)
def read_roadgraph(path: Path) -> dict:
    """Read ``roadgraph.nycb`` back into numpy arrays plus the decoded segment names."""
    r = NycbReader(path)
    out = {name: r.read(name, dt) for name, dt in ROADGRAPH_DTYPES.items()}
    blob = r.strings()
    out["strtab"] = blob
    out["segment_names"] = [r.string_at(int(o), blob) for o in out["segments"]["name_str"]]
    out["reader"] = r
    return out


def read_signals(path: Path) -> dict:
    r = NycbReader(path)
    return {"controllers": r.read("controllers", CONTROLLER_DTYPE), "phases": r.read("phases", PHASE_DTYPE), "reader": r}


def read_pois(path: Path) -> dict:
    """Read ``pois.nycb`` back, decoding every address the way ``RoadNetwork::loadPois`` does."""
    r = NycbReader(path)
    pois = r.read("pois", POI_DTYPE)
    blob = r.strings()
    return {"pois": pois, "strtab": blob,
            "addresses": [r.string_at(int(o), blob) for o in pois["addr_str"]], "reader": r}


def read_tiles(path: Path) -> dict:
    r = NycbReader(path)
    return {"tiles": r.read("tiles", TILE_DTYPE), "reader": r}


def read_landmarks(path: Path) -> dict:
    r = NycbReader(path)
    pts = r.read("points", LANDMARK_DTYPE)
    blob = r.strings()
    return {"points": pts, "strtab": blob,
            "names": [r.string_at(int(o), blob) for o in pts["name_str"]], "reader": r}


def segment_polyline(rg: dict, i: int) -> np.ndarray:
    s = rg["segments"][i]
    v = rg["vertices"][int(s["first_vertex"]): int(s["first_vertex"]) + int(s["vertex_count"])]
    return np.column_stack([v["x"], v["y"], v["z"]])


def lane_successors(rg: dict, i: int) -> np.ndarray:
    l = rg["lanes"][i]
    return rg["lane_links"]["lane_id"][int(l["first_succ"]): int(l["first_succ"]) + int(l["succ_count"])]


def junction_yields(rg: dict, i: int) -> np.ndarray:
    j = rg["junction_lanes"][i]
    return rg["yield_links"]["lane_id"][int(j["first_yield"]): int(j["first_yield"]) + int(j["yield_count"])]


# --------------------------------------------------------------------------- manifest
# artefact id -> (file, manifest sources, key in `st` holding the row count, schema). Every §15 file this module
# writes is listed; ``record_manifest`` records the ones actually exported in this run.
MANIFEST_ENTRIES = {
    "roadgraph": ("runtime_roadgraph", "roadgraph.nycb",
                  ["roads_segments", "roads_nodes", "roads_lanes", "roads_junction_lanes"],
                  "segments", "nycb.roadgraph/1"),
    "signals": ("runtime_signals", "signals.nycb", ["roads_signals"], "controllers", "nycb.signals/1"),
    "pois": ("runtime_pois", "pois.nycb", ["buildings_base"], "pois", "nycb.pois/1"),
    "tiles": ("runtime_tiles", "tiles.nycb", ["tiles_index"], "tiles", "nycb.tiles/1"),
    "landmarks": ("runtime_landmarks", "landmarks.nycb", ["landmark_footprints"], "points", "nycb.landmarks/1"),
}


def record_manifest(out_dir: Path, st: dict) -> list[str]:
    """Record every exported artefact in ``data/manifest/processed.json``. Returns the artefact ids written."""
    from .. import manifest
    written = []
    for key, (artifact_id, filename, sources, count_key, schema) in MANIFEST_ENTRIES.items():
        if key not in st:
            continue
        s = st[key]
        extra = {k: s[k] for k in ("counts", "totals", "dropped", "source_rows") if k in s}
        manifest.record_processed(artifact_id, out_dir / filename, stage="runtime.export", sources=sources,
                                  rows=s["counts"][count_key], schema=schema, extra=extra)
        written.append(artifact_id)
    manifest.record_processed("runtime_nycb_layout", out_dir / "nycb_layout.json", stage="runtime.export",
                              sources=[], schema="nycb.layout/1")
    written.append("runtime_nycb_layout")
    return written


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--roads-dir", type=Path, default=PROCESSED / "roads")
    ap.add_argument("--buildings-dir", type=Path, default=PROCESSED / "buildings")
    ap.add_argument("--tiles-dir", type=Path, default=PROCESSED / "tiles")
    ap.add_argument("--out-dir", type=Path, default=PROCESSED / "runtime")
    ap.add_argument("--no-manifest", action="store_true", help="do not record the artefacts in data/manifest/processed.json")
    ap.add_argument("-v", "--verbose", action="store_true")
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if a.verbose else logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    a.out_dir.mkdir(parents=True, exist_ok=True)
    from .nycb import write_layout
    st = {"roadgraph": export_roadgraph(a.roads_dir, a.out_dir / "roadgraph.nycb"),
          "signals": export_signals(a.roads_dir, a.out_dir / "signals.nycb"),
          "pois": export_pois(a.buildings_dir, a.out_dir / "pois.nycb"),
          "tiles": export_tiles(a.tiles_dir, a.out_dir / "tiles.nycb"),
          "landmarks": export_landmarks(a.buildings_dir, a.out_dir / "landmarks.nycb")}
    write_layout(a.out_dir / "nycb_layout.json", ALL_DTYPES)
    st["layout"] = str(a.out_dir / "nycb_layout.json")
    if not a.no_manifest and a.out_dir == PROCESSED / "runtime":
        record_manifest(a.out_dir, st)
    print(json.dumps(st, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
