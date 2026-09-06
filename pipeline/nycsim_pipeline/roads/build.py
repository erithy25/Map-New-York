"""Roads stage: CSCL + LION + OSM + DOT datasets + DoITT planimetrics -> the §7 road artefacts.

    python -m nycsim_pipeline roads [--borough N ...] [--out-dir DIR] [--no-pavement] [--no-runtime]

Outputs (full run):
    data/processed/roads/segments.parquet        §7 segments (3-D lines, NYC_TM)
    data/processed/roads/nodes.parquet           §7 nodes with control and signal provenance
    data/processed/roads/lanes.parquet           §7 lanes with successors/predecessors
    data/processed/roads/junction_lanes.parquet  §7 lane-to-lane connectors with turn, group and yield sets
    data/processed/roads/signals.parquet         §7 controllers with DOT-standard phasing
    data/processed/roads/signs.parquet           §7 signs (real DOT signs + generated regulatory/name signs)
    data/processed/roads/pavement/{tile}.parquet §7 per-tile pavement polygons
    data/processed/roads/bridges_tunnels.json    named crossings -> segment ids and end nodes
    data/processed/roads/connectivity.json       A* routes, component analysis, one-way and dead-end audits
    data/processed/roads/build_summary.json      every count in this run
    data/processed/runtime/{roadgraph,signals}.nycb  §15 runtime binaries

``--borough`` restricts CSCL to those boroughs for a fast development pass; subset runs require ``--out-dir``
and are never recorded in the manifest.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely

from .. import manifest
from ..contracts import validate_parquet
from ..paths import PROCESSED
from . import bridges as bridges_mod
from . import cscl as cscl_mod
from . import graph as graph_mod
from . import inputs as inputs_mod
from . import junctions as junctions_mod
from . import lanes as lanes_mod
from . import lion as lion_mod
from . import osm as osm_mod
from . import pavement as pavement_mod
from . import schema as S
from . import segments as segments_mod
from . import signals as signals_mod
from . import signs as signs_mod

log = logging.getLogger("nycsim.roads.build")

SOURCE_IDS = ["centerline", "lion", "osm_newyork_pbf", "dot_signs", "vzv_speed_limits", "vzv_lpi_signals",
              "barnes_dance", "signal_retiming", "bike_routes", "bus_lanes", "truck_routes", "ped_plazas",
              "street_construction_permits", "plan_roadbed", "plan_curb", "plan_sidewalk", "plan_median",
              "plan_pavement_edge", "plan_transport_structures", "plan_parking_lot", "plan_public_plazas"]

# name_norm, borough, expected compass bearing of legal travel (None = report only)
ONE_WAY_CHECKS = [
    ("5 AVE", 1, 180.0, "Fifth Avenue runs one-way southbound"),
    ("MADISON AVE", 1, 0.0, "Madison Avenue runs one-way northbound"),
    ("1 AVE", 1, 0.0, "First Avenue runs one-way northbound"),
    ("2 AVE", 1, 180.0, "Second Avenue runs one-way southbound"),
    ("LEXINGTON AVE", 1, 180.0, "Lexington Avenue runs one-way southbound"),
    ("3 AVE", 1, 0.0, "Third Avenue runs one-way northbound in Manhattan"),
]
DIVIDED_CHECKS = [
    ("FRANKLIN D ROOSEVELT DR", 1, "FDR Drive: opposing one-way carriageways on a north-south axis"),
    ("W ST", 1, "West Street (West Side Highway, Route 9A south): opposing carriageways, north-south axis"),
    ("12 AVE", 1, "Twelfth Avenue (West Side Highway north): opposing carriageways, north-south axis"),
    ("HENRY HUDSON PKWY", 1, "Henry Hudson Parkway: opposing carriageways, north-south axis"),
]
ROUTE_CHECKS = [
    {"id": "bronx_to_staten_island", "from": ("E FORDHAM RD", "GRAND CONC", 2), "to": ("HYLAN BLVD", "RICHMOND AVE", 5),
     "must_use": "verrazzano_narrows_bridge",
     "note": "Fordham Rd & Grand Concourse (Bronx) -> Hylan Blvd & Richmond Ave (Staten Island)"},
    {"id": "manhattan_to_brooklyn", "from": ("5 AVE", "E 42 ST", 1), "to": ("FLATBUSH AVE", "ATLANTIC AVE", 3),
     "must_use": None, "note": "Midtown -> Barclays Center (crosses the East River)"},
    {"id": "queens_to_manhattan", "from": ("QUEENS BLVD", "82 ST", 4), "to": ("BROADWAY", "W 72 ST", 1),
     "must_use": None, "note": "Jackson Heights -> Upper West Side"},
]


class Timer:
    def __init__(self) -> None:
        self.t0 = time.perf_counter()
        self.last = self.t0
        self.steps: dict[str, float] = {}

    def lap(self, name: str) -> None:
        now = time.perf_counter()
        self.steps[name] = round(now - self.last, 2)
        self.last = now
        log.info("[%s] %.1fs (total %.1fs)", name, self.steps[name], now - self.t0)

    @property
    def total(self) -> float:
        return round(time.perf_counter() - self.t0, 2)


def _y_of_street(seg: gpd.GeoDataFrame, name_norm: str, borough: int) -> float | None:
    m = (seg["name_norm"].to_numpy() == name_norm) & (seg["borough"].to_numpy() == borough)
    if not m.any():
        return None
    return float(np.median(shapely.get_coordinates(seg.geometry.values[m])[:, 1]))


def connectivity_report(seg: gpd.GeoDataFrame, nodes: pd.DataFrame, lanes: gpd.GeoDataFrame,
                        bridges_doc: dict) -> dict:
    out: dict = {}
    t0 = time.time()
    g = graph_mod.RoadGraph(seg, nodes)
    out["graph"] = {"nodes": g.n, "directed_arcs": g.n_arcs, "max_speed_mps": round(g.max_speed_mps, 2)}
    comp_all = graph_mod.undirected_components(seg, nodes, drivable_only=False)
    comp_drv = graph_mod.undirected_components(seg, nodes, drivable_only=True)
    strong = g.components("strong")
    weak = g.components("weak")
    for d in (comp_all, comp_drv, strong, weak):
        d.pop("labels", None)
    out["undirected_all_segments"] = comp_all
    out["undirected_drivable_only"] = comp_drv
    out["directed_strongly_connected"] = strong
    out["directed_weakly_connected"] = weak

    # ---- A* routes ----
    bridge_segments = {b["id"]: set(b["segment_ids"]) for b in bridges_doc["bridges_tunnels"]}
    routes = []
    for spec in ROUTE_CHECKS:
        a_name, b_name, a_boro = spec["from"]
        c_name, d_name, c_boro = spec["to"]
        na = g.find_intersection(a_name, b_name, a_boro)
        nb = g.find_intersection(c_name, d_name, c_boro)
        rec = {"id": spec["id"], "note": spec["note"], "from_intersection": f"{a_name} & {b_name}",
               "to_intersection": f"{c_name} & {d_name}", "from_node": na, "to_node": nb}
        if na < 0 or nb < 0:
            rec["found"] = False
            rec["reason"] = "endpoint intersection not found in the node table"
            routes.append(rec)
            continue
        r = g.astar(na, nb)
        rec.update(r.summary())
        if spec["must_use"]:
            used = bridge_segments.get(spec["must_use"], set()) & set(r.segments)
            rec["uses_" + spec["must_use"]] = sorted(int(v) for v in used)
            rec["crosses_required_structure"] = bool(used)
        routes.append(rec)
    out["routes"] = routes

    # ---- every named crossing connected at both ends ----
    struct = []
    for b in bridges_doc["bridges_tunnels"]:
        struct.append({"name": b["name"], "found": b["found"], "n_segments": b["n_segments"],
                       "n_end_nodes": b.get("n_end_nodes", 0), "connected_both_ends": b.get("connected_both_ends", False),
                       "splits_network": b.get("splits_network", False), "length_m": b.get("length_m", 0.0)})
    out["structures"] = struct
    out["structures_found"] = int(sum(1 for s in struct if s["found"]))
    out["structures_connected_both_ends"] = int(sum(1 for s in struct if s["connected_both_ends"]))

    # ---- one-way sanity ----
    checks = []
    for name, boro, expected, note in ONE_WAY_CHECKS:
        a = graph_mod.one_way_audit(seg, name, boro, expected)
        a["note"] = note
        checks.append(a)
    y59 = _y_of_street(seg, "W 59 ST", 1)
    if y59 is not None:
        a = graph_mod.one_way_audit(seg, "BROADWAY", 1, 180.0, y_max=y59)
        a["note"] = f"Broadway south of West 59th Street (y <= {y59:.1f} m) runs one-way southbound"
        a["cut_y_m"] = round(y59, 1)
        checks.append(a)
    out["one_way_checks"] = checks
    out["one_way_checks_passed"] = int(sum(1 for c in checks if c.get("pass")))
    out["one_way_checks_total"] = len(checks)

    divided = []
    for name, boro, note in DIVIDED_CHECKS:
        a = graph_mod.one_way_audit(seg, name, boro, None)
        a["note"] = note
        a["pass"] = bool(a.get("km_northbound", 0) > 0.2 and a.get("km_southbound", 0) > 0.2
                         and (a.get("north_south_share") or 0) >= 0.7)
        divided.append(a)
    out["divided_highway_checks"] = divided
    out["divided_highway_checks_passed"] = int(sum(1 for c in divided if c["pass"]))

    out["dead_ends"] = graph_mod.dead_end_lanes(lanes)
    out["seconds"] = round(time.time() - t0, 1)
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--borough", type=int, action="append", default=[], help="restrict CSCL to borough code(s) 1-5 (dev subset)")
    ap.add_argument("--out-dir", type=Path, default=None, help="output directory (required for subset runs)")
    ap.add_argument("--no-pavement", action="store_true", help="skip the per-tile pavement polygons")
    ap.add_argument("--no-signs", action="store_true", help="skip the sign layer")
    ap.add_argument("--no-runtime", action="store_true", help="skip the §15 runtime binaries")
    ap.add_argument("--force-osm", action="store_true", help="rebuild the OSM caches even if present")
    ap.add_argument("-v", "--verbose", action="store_true")
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if a.verbose else logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    subset = bool(a.borough)
    if subset and a.out_dir is None:
        ap.error("--out-dir is required for subset runs (--borough)")
    out_dir = a.out_dir or (PROCESSED / "roads")
    out_dir.mkdir(parents=True, exist_ok=True)
    cache_dir = PROCESSED / "roads" / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    T = Timer()
    stats: dict = {"subset": subset, "boroughs": a.borough or [1, 2, 3, 4, 5], "out_dir": str(out_dir)}
    inputs = inputs_mod.resolve()
    stats["inputs"] = {k: str(v) for k, v in sorted(inputs.paths.items())}
    stats["inputs_missing"] = inputs.missing

    # ---------------------------------------------------------------- geometry + topology
    boro = a.borough[0] if len(a.borough) == 1 else None
    cscl = cscl_mod.load_cscl(inputs["centerline"], boro)
    if len(a.borough) > 1:
        cscl = cscl[cscl["borough"].isin(a.borough)].reset_index(drop=True)
    stats["cscl"] = {"segments": int(len(cscl)), **{k: int(v) for k, v in cscl.attrs.items()}}
    T.lap("cscl")

    gdb = lion_mod.ensure_extracted(inputs["lion"])
    lion_nodes = lion_mod.load_lion_nodes(gdb)
    lion_segs = lion_mod.load_lion_segments(gdb)
    node_names = lion_mod.load_node_names(gdb)
    stats["lion"] = {"nodes": int(len(lion_nodes)), "segment_rows": int(len(lion_segs)),
                     "physical_ids": int(lion_segs["PhysicalID"].nunique()), "named_nodes": int(len(node_names))}
    T.lap("lion")

    assignment, nodes_raw = lion_mod.assign_nodes(cscl, lion_segs, lion_nodes)
    sx, sy, resid = lion_mod.compute_datum_shift(cscl, assignment, nodes_raw)
    shift = (sx, sy)
    nodes_pos = lion_mod.node_positions_from_cscl(cscl, assignment, nodes_raw, shift)
    stats["topology"] = {
        "ends_by_physicalid": int((assignment["from_source"] == 0).sum() + (assignment["to_source"] == 0).sum()),
        "ends_by_nearest_node": int((assignment["from_source"] == 1).sum() + (assignment["to_source"] == 1).sum()),
        "ends_synthetic": int((assignment["from_source"] == 2).sum() + (assignment["to_source"] == 2).sum()),
        "datum_shift_dx_m": round(sx, 4), "datum_shift_dy_m": round(sy, 4), "datum_shift_residual_rms_m": round(resid, 4),
    }
    T.lap("node_assignment")

    # ---------------------------------------------------------------- OSM
    osm_paths = osm_mod.extract(inputs["osm_newyork_pbf"], cache_dir, force=a.force_osm)
    osm_nodes, osm_ways, osm_rest = osm_mod.load(cache_dir)
    stats["osm"] = {"tagged_nodes": int(len(osm_nodes)), "ways": int(len(osm_ways)), "restrictions": int(len(osm_rest)),
                    "caches": {k: str(v) for k, v in osm_paths.items()}}
    T.lap("osm")

    # ---------------------------------------------------------------- segments
    seg, nd, seg_stats = segments_mod.build(cscl, assignment, nodes_pos, lion_segs, node_names, inputs,
                                            osm_ways, shift, cache_dir)
    stats["segments"] = seg_stats
    del cscl, nodes_raw
    T.lap("segments")

    # ---------------------------------------------------------------- signals and control
    sig = signals_mod.build(seg, nd, inputs, osm_nodes)
    nodes = sig.nodes
    stats["signals"] = sig.stats
    T.lap("signals")

    # ---------------------------------------------------------------- lanes and junctions
    lanes, lane_stats = lanes_mod.build(seg)
    stats["lanes"] = lane_stats
    T.lap("lanes")

    jl, lanes, jl_stats = junctions_mod.build(seg, nodes, lanes, sig.node_groups, sig.stop_approaches,
                                              sig.yield_approaches, osm_rest, osm_ways)
    stats["junction_lanes"] = jl_stats
    del osm_ways, osm_rest
    T.lap("junction_lanes")

    # ---------------------------------------------------------------- signs
    approaches = signs_mod._approach_frames(seg)
    if a.no_signs:
        signs = pd.DataFrame()
        stats["signs"] = {"skipped": True}
    else:
        signs, sign_stats = signs_mod.build(seg, nodes, inputs, shift, sig.stop_approaches, sig.yield_approaches)
        stats["signs"] = sign_stats
    T.lap("signs")

    # ---------------------------------------------------------------- write the tabular artefacts
    seg_out = seg.copy()
    n_seg = S.write_geoparquet(seg_out, out_dir / "segments.parquet", S.SCHEMAS["segments"])
    node_out = nodes.copy()
    node_out["z"] = node_out["z"].astype(np.float32)
    n_nodes = S.write_parquet(node_out, out_dir / "nodes.parquet", S.SCHEMAS["nodes"])
    n_lanes = S.write_geoparquet(lanes, out_dir / "lanes.parquet", S.SCHEMAS["lanes"])
    n_jl = S.write_geoparquet(jl, out_dir / "junction_lanes.parquet", S.SCHEMAS["junction_lanes"])
    n_sig = S.write_parquet(sig.signals, out_dir / "signals.parquet", S.SCHEMAS["signals"])
    n_signs = S.write_parquet(signs, out_dir / "signs.parquet", S.SCHEMAS["signs"]) if len(signs) else 0
    stats["outputs"] = {"segments": n_seg, "nodes": n_nodes, "lanes": n_lanes, "junction_lanes": n_jl,
                        "signals": n_sig, "signs": n_signs}
    T.lap("write_tables")

    problems = {
        "road_segments": validate_parquet("road_segments", out_dir / "segments.parquet"),
        "road_nodes": validate_parquet("road_nodes", out_dir / "nodes.parquet"),
        "lanes": validate_parquet("lanes", out_dir / "lanes.parquet"),
        "junction_lanes": validate_parquet("junction_lanes", out_dir / "junction_lanes.parquet"),
        "signals": validate_parquet("signals", out_dir / "signals.parquet"),
    }
    if n_signs:
        problems["signs"] = validate_parquet("signs", out_dir / "signs.parquet")
    stats["contract_validation"] = problems
    bad = {k: v for k, v in problems.items() if v}
    if bad:
        log.error("contract validation failed: %s", json.dumps(bad, indent=1))
        raise SystemExit(f"DATA_CONTRACTS validation failed: {bad}")
    T.lap("validate")

    # ---------------------------------------------------------------- bridges, tunnels, connectivity
    bridges_doc, bridge_stats = bridges_mod.build(seg, nodes, inputs)
    stats["bridges"] = bridge_stats
    with open(out_dir / "bridges_tunnels.json", "w") as f:
        json.dump(bridges_doc, f, indent=1)
    T.lap("bridges")

    conn = connectivity_report(seg, nodes, lanes, bridges_doc)
    with open(out_dir / "connectivity.json", "w") as f:
        json.dump(conn, f, indent=1)
    stats["connectivity"] = {k: v for k, v in conn.items() if k != "structures"}
    T.lap("connectivity")

    # ---------------------------------------------------------------- pavement
    if a.no_pavement:
        stats["pavement"] = {"skipped": True}
    else:
        stats["pavement"] = pavement_mod.build(inputs, seg, nodes, approaches, out_dir / "pavement")
    T.lap("pavement")

    # ---------------------------------------------------------------- runtime binaries
    if a.no_runtime:
        stats["runtime"] = {"skipped": True}
    else:
        from ..runtime import export as rt_export
        from ..runtime.nycb import write_layout
        rt_dir = (out_dir.parent / "runtime") if subset else (PROCESSED / "runtime")
        rt_dir.mkdir(parents=True, exist_ok=True)
        stats["runtime"] = {
            "roadgraph": rt_export.export_roadgraph(out_dir, rt_dir / "roadgraph.nycb"),
            "signals": rt_export.export_signals(out_dir, rt_dir / "signals.nycb"),
        }
        write_layout(rt_dir / "nycb_layout.json", rt_export.ALL_DTYPES)
    T.lap("runtime")

    stats["timings_s"] = {**T.steps, "total": T.total}
    with open(out_dir / "build_summary.json", "w") as f:
        json.dump(stats, f, indent=1, default=str)

    if not subset:
        srcs = [s for s in SOURCE_IDS if manifest.get_download(s) is not None]
        for aid, path, rows, schema in (
                ("roads_segments", out_dir / "segments.parquet", n_seg, S.SCHEMAS["segments"]),
                ("roads_nodes", out_dir / "nodes.parquet", n_nodes, S.SCHEMAS["nodes"]),
                ("roads_lanes", out_dir / "lanes.parquet", n_lanes, S.SCHEMAS["lanes"]),
                ("roads_junction_lanes", out_dir / "junction_lanes.parquet", n_jl, S.SCHEMAS["junction_lanes"]),
                ("roads_signals", out_dir / "signals.parquet", n_sig, S.SCHEMAS["signals"]),
                ("roads_signs", out_dir / "signs.parquet", n_signs, S.SCHEMAS["signs"]),
                ("roads_bridges_tunnels", out_dir / "bridges_tunnels.json", bridges_doc["n_found"], "roads.bridges/1"),
                ("roads_connectivity", out_dir / "connectivity.json", None, "roads.connectivity/1"),
                ("roads_build_summary", out_dir / "build_summary.json", None, "roads.build_summary/1")):
            if path.exists():
                manifest.record_processed(aid, path, stage="roads", sources=srcs, rows=rows, schema=schema)
        if not a.no_runtime:
            for aid, name in (("runtime_roadgraph", "roadgraph.nycb"), ("runtime_signals", "signals.nycb")):
                p = PROCESSED / "runtime" / name
                if p.exists():
                    manifest.record_processed(aid, p, stage="roads", sources=srcs, schema="nycb/1")
        if not a.no_pavement:
            pav_index = {p.name: p.stat().st_size for p in sorted((out_dir / "pavement").glob("t_*.parquet"))}
            with open(out_dir / "pavement_index.json", "w") as f:
                json.dump({"schema_version": 1, "tiles": pav_index}, f, indent=1)
            manifest.record_processed("roads_pavement", out_dir / "pavement_index.json", stage="roads", sources=srcs,
                                      rows=stats["pavement"].get("rows"), schema=S.SCHEMAS["pavement"],
                                      extra={"n_tiles": len(pav_index)})
        T.lap("manifest")
        stats["timings_s"] = {**T.steps, "total": T.total}
        with open(out_dir / "build_summary.json", "w") as f:
            json.dump(stats, f, indent=1, default=str)

    print(json.dumps({
        "segments": n_seg, "nodes": n_nodes, "lanes": n_lanes, "junction_lanes": n_jl, "signals": n_sig, "signs": n_signs,
        "km_total": round(sum(seg_stats["km_by_rw_type"].values()), 1),
        "signalized_nodes": sig.stats["signalized_nodes"],
        "bridges_found": bridge_stats["found"], "bridges_missing": bridge_stats["missing"],
        "largest_component_share": conn["undirected_all_segments"]["share"],
        "routes": [{r["id"]: r.get("found")} for r in conn["routes"]],
        "one_way_checks_passed": f'{conn["one_way_checks_passed"]}/{conn["one_way_checks_total"]}',
        "pavement_tiles": stats["pavement"].get("tiles"),
        "timings_s": stats["timings_s"],
    }, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
