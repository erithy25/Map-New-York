"""Map the processed road artefacts onto the NYCB runtime containers of DATA_CONTRACTS §15.

    python -m nycsim_pipeline.runtime.export [--roads-dir DIR] [--out-dir DIR]

Produces ``data/processed/runtime/roadgraph.nycb`` and ``signals.nycb`` plus ``nycb_layout.json`` (the exact
field offsets so ``core/io/NycbReader.h`` can be checked mechanically against this writer).

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

EXPECTED_SIZEOF = {
    "nodes": 24, "segments": 48, "vertices": 12, "lanes": 48, "lane_links": 8,
    "junction_lanes": 48, "yield_links": 8, "controllers": 32, "phases": 28,
}
ROADGRAPH_DTYPES = {"nodes": NODE_DTYPE, "segments": SEGMENT_DTYPE, "vertices": VERTEX_DTYPE, "lanes": LANE_DTYPE,
                    "lane_links": LANE_LINK_DTYPE, "junction_lanes": JUNCTION_DTYPE, "yield_links": YIELD_LINK_DTYPE}
SIGNAL_DTYPES = {"controllers": CONTROLLER_DTYPE, "phases": PHASE_DTYPE}
ALL_DTYPES = {**ROADGRAPH_DTYPES, **SIGNAL_DTYPES}
for _n, _d in ALL_DTYPES.items():
    if _d.itemsize != EXPECTED_SIZEOF[_n]:
        raise AssertionError(f"NYCB section {_n!r}: sizeof {_d.itemsize} != contract {EXPECTED_SIZEOF[_n]}")

SIG_NONE = 255
NO_SIGNAL_GROUP = -1


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


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--roads-dir", type=Path, default=PROCESSED / "roads")
    ap.add_argument("--out-dir", type=Path, default=PROCESSED / "runtime")
    ap.add_argument("-v", "--verbose", action="store_true")
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if a.verbose else logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    a.out_dir.mkdir(parents=True, exist_ok=True)
    from .nycb import write_layout
    st = {"roadgraph": export_roadgraph(a.roads_dir, a.out_dir / "roadgraph.nycb"),
          "signals": export_signals(a.roads_dir, a.out_dir / "signals.nycb")}
    write_layout(a.out_dir / "nycb_layout.json", ALL_DTYPES)
    st["layout"] = str(a.out_dir / "nycb_layout.json")
    print(json.dumps(st, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
