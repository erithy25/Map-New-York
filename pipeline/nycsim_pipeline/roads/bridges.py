"""bridges_tunnels.json: the named East River / Harlem River / Newtown Creek / Gowanus / Arthur Kill /
Jamaica Bay / Long Island Sound crossings, resolved to the real CSCL segments that form each one.

Matching is by the real CSCL ``full_street_name`` (normalised by ``roads.names``): a segment belongs to a
structure when its normalised name equals one of the structure's patterns or begins with a pattern followed by
a qualifier ("PED PATH", "BIKE PATH", "UPPER RDWY", "EN"/"ET" ramp designators ...). Nothing is matched by
proximity, so a segment is never attributed to a crossing it does not carry a name for. The one exception is
the Greenpoint Avenue (J. J. Byrne Memorial) Bridge, whose deck CSCL names simply "GREENPOINT AVE": it is
resolved by intersecting the named street with the DoITT planimetric transportation-structure polygons
(``plan_transport_structures``), which is still a real geometric source, and is flagged ``matched_by =
"street_in_structure"``.

For each structure the file records the segment ids, the ramp segment ids, the total deck length, the end
nodes (nodes of the structure that are also endpoints of segments outside it) and whether removing the
structure would split the network there — the real test that the crossing is the connection between two
shores, not a stub.
"""
from __future__ import annotations

import logging
import time
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import pyogrio
import shapely
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components

from ..crs import NYC_TM
from . import schema as S

log = logging.getLogger("nycsim.roads.bridges")

QUALIFIERS = ("PED", "BIKE", "PATH", "WALK", "UPPER", "LOWER", "RDWY", "RY", "DECK", "LEVEL", "LVL", "EN", "ET",
              "RP", "APPR", "N", "S", "E", "W", "NB", "SB", "EB", "WB", "AND", "TO", "BUS", "SLIP", "GREENWAY",
              "BRONX", "QUEENS", "MN", "BKLYN", "OPAS", "TURNAROUND")

# name, kind, normalised CSCL name patterns, excluded substrings
STRUCTURES: list[dict] = [
    {"id": "brooklyn_bridge", "name": "Brooklyn Bridge", "kind": "bridge", "patterns": ["BROOKLYN BR"]},
    {"id": "manhattan_bridge", "name": "Manhattan Bridge", "kind": "bridge", "patterns": ["MANHATTAN BR"]},
    {"id": "williamsburg_bridge", "name": "Williamsburg Bridge", "kind": "bridge", "patterns": ["WILLIAMSBURG BR"]},
    {"id": "queensboro_bridge", "name": "Ed Koch Queensboro Bridge", "kind": "bridge",
     "patterns": ["QUEENSBORO BR", "ED KOCH QUEENSBORO BR", "ED KOCH BR"]},
    {"id": "rfk_triborough_bridge", "name": "Robert F. Kennedy (Triborough) Bridge", "kind": "bridge",
     "patterns": ["RFK BR", "TRIBOROUGH BR"]},
    {"id": "george_washington_bridge", "name": "George Washington Bridge", "kind": "bridge", "patterns": ["GEORGE WASHINGTON BR"]},
    {"id": "verrazzano_narrows_bridge", "name": "Verrazzano-Narrows Bridge", "kind": "bridge",
     "patterns": ["VERRAZZANO BR", "VERRAZANO BR", "VERRAZZANO NARROWS BR"]},
    {"id": "throgs_neck_bridge", "name": "Throgs Neck Bridge", "kind": "bridge", "patterns": ["THROGS NECK BR"]},
    {"id": "bronx_whitestone_bridge", "name": "Bronx-Whitestone Bridge", "kind": "bridge",
     "patterns": ["WHITESTONE BR", "BRONX WHITESTONE BR"], "exclude": ["EXPY"]},
    {"id": "pulaski_bridge", "name": "Pulaski Bridge", "kind": "bridge", "patterns": ["PULASKI BR"]},
    {"id": "kosciuszko_bridge", "name": "Kosciuszko Bridge", "kind": "bridge", "patterns": ["KOSCIUSZKO BR"]},
    {"id": "high_bridge", "name": "High Bridge", "kind": "bridge", "patterns": ["HIGH BR"], "exclude": ["PARK"]},
    {"id": "henry_hudson_bridge", "name": "Henry Hudson Bridge", "kind": "bridge", "patterns": ["HENRY HUDSON BR"]},
    {"id": "cross_bay_bridge", "name": "Cross Bay Veterans Memorial Bridge", "kind": "bridge",
     "patterns": ["CROSS BAY VETERANS MEMORIAL BR", "CROSS BAY VET MEMORIAL BR", "CROSS BAY VET MEM BR"]},
    {"id": "marine_parkway_bridge", "name": "Marine Parkway-Gil Hodges Memorial Bridge", "kind": "bridge",
     "patterns": ["MARINE PKWY GIL HODGES MEMORIAL BR", "MARINE PKWY GIL HODGES BR", "MARINE PKWY BR"]},
    {"id": "hell_gate_bridge", "name": "Hell Gate Bridge", "kind": "bridge", "patterns": ["HELL GATE BR"]},
    {"id": "goethals_bridge", "name": "Goethals Bridge", "kind": "bridge", "patterns": ["GOETHALS BR"]},
    {"id": "bayonne_bridge", "name": "Bayonne Bridge", "kind": "bridge", "patterns": ["BAYONNE BR"]},
    {"id": "outerbridge_crossing", "name": "Outerbridge Crossing", "kind": "bridge",
     "patterns": ["OUTERBRIDGE XING", "OUTERBRIDGE CROSSING"]},
    {"id": "willis_avenue_bridge", "name": "Willis Avenue Bridge", "kind": "bridge", "patterns": ["WILLIS AVE BR"]},
    {"id": "third_avenue_bridge", "name": "Third Avenue Bridge", "kind": "bridge", "patterns": ["3 AVE BR"]},
    {"id": "madison_avenue_bridge", "name": "Madison Avenue Bridge", "kind": "bridge", "patterns": ["MADISON AVE BR"]},
    {"id": "145th_street_bridge", "name": "145th Street Bridge", "kind": "bridge", "patterns": ["145 ST BR"]},
    {"id": "macombs_dam_bridge", "name": "Macombs Dam Bridge", "kind": "bridge", "patterns": ["MACOMBS DAM BR"]},
    {"id": "university_heights_bridge", "name": "University Heights Bridge", "kind": "bridge", "patterns": ["UNIVERSITY HTS BR"]},
    {"id": "washington_bridge", "name": "Washington Bridge", "kind": "bridge", "patterns": ["WASHINGTON BR"]},
    {"id": "alexander_hamilton_bridge", "name": "Alexander Hamilton Bridge", "kind": "bridge", "patterns": ["ALEXANDER HAMILTON BR"]},
    {"id": "broadway_bridge", "name": "Broadway Bridge", "kind": "bridge", "patterns": ["BROADWAY BR"]},
    {"id": "roosevelt_island_bridge", "name": "Roosevelt Island Bridge", "kind": "bridge", "patterns": ["ROOSEVELT IS BR"]},
    {"id": "carroll_street_bridge", "name": "Carroll Street Bridge", "kind": "bridge", "patterns": ["CARROLL ST BR"]},
    {"id": "union_street_bridge", "name": "Union Street Bridge", "kind": "bridge", "patterns": ["UNION ST BR"]},
    {"id": "third_street_bridge", "name": "Third Street Bridge", "kind": "bridge", "patterns": ["3 ST BR"]},
    {"id": "ninth_street_bridge", "name": "Ninth Street Bridge", "kind": "bridge", "patterns": ["9 ST BR"]},
    {"id": "hamilton_avenue_bridge", "name": "Hamilton Avenue Bridge", "kind": "bridge", "patterns": ["HAMILTON AVE BR"]},
    {"id": "greenpoint_avenue_bridge", "name": "Greenpoint Avenue Bridge", "kind": "bridge",
     "patterns": ["GREENPOINT AVE BR"], "street_in_structure": "GREENPOINT AVE"},
    {"id": "metropolitan_avenue_bridge", "name": "Metropolitan Avenue Bridge", "kind": "bridge", "patterns": ["METROPOLITAN AVE BR"]},
    {"id": "grand_street_bridge", "name": "Grand Street Bridge", "kind": "bridge", "patterns": ["GRAND ST BR"]},
    {"id": "borden_avenue_bridge", "name": "Borden Avenue Bridge", "kind": "bridge", "patterns": ["BORDEN AVE BR"]},
    {"id": "hunters_point_avenue_bridge", "name": "Hunters Point Avenue Bridge", "kind": "bridge",
     "patterns": ["HUNTERS POINT AVE BR", "HUNTERS POINT BR"]},
    {"id": "roosevelt_avenue_bridge", "name": "Roosevelt Avenue Bridge", "kind": "bridge", "patterns": ["ROOSEVELT AVE BR"]},
    {"id": "mill_basin_bridge", "name": "Mill Basin Bridge", "kind": "bridge", "patterns": ["MILL BASIN BR"]},
    {"id": "cropsey_avenue_bridge", "name": "Cropsey Avenue Bridge", "kind": "bridge", "patterns": ["CROPSEY AVE BR"]},
    {"id": "ocean_avenue_bridge", "name": "Ocean Avenue Bridge", "kind": "bridge",
     "patterns": ["OCEAN AVE BR", "OCEAN AVE PED BR"]},
    {"id": "pelham_bridge", "name": "Pelham Bridge", "kind": "bridge", "patterns": ["PELHAM BR"]},
    {"id": "city_island_bridge", "name": "City Island Bridge", "kind": "bridge", "patterns": ["CITY IS BR"]},
    {"id": "unionport_bridge", "name": "Unionport Bridge", "kind": "bridge", "patterns": ["UNIONPORT BR"]},
    {"id": "eastchester_bridge", "name": "Eastchester Bridge", "kind": "bridge", "patterns": ["EASTCHESTER BR"]},
    {"id": "hutchinson_river_parkway_bridge", "name": "Hutchinson River Parkway Bridge", "kind": "bridge",
     "patterns": ["HUTCHINSON RIVER PKWY BR", "HUTCHINSON RVR PKWY BR"]},
    {"id": "rikers_island_bridge", "name": "Rikers Island Bridge", "kind": "bridge", "patterns": ["RIKERS IS BR"]},
    {"id": "lincoln_tunnel", "name": "Lincoln Tunnel", "kind": "tunnel", "patterns": ["LINCOLN TUNL"]},
    {"id": "holland_tunnel", "name": "Holland Tunnel", "kind": "tunnel", "patterns": ["HOLLAND TUNL"]},
    {"id": "queens_midtown_tunnel", "name": "Queens-Midtown Tunnel", "kind": "tunnel", "patterns": ["QUEENS MIDTOWN TUNL"]},
    {"id": "hugh_l_carey_tunnel", "name": "Hugh L. Carey Tunnel", "kind": "tunnel",
     "patterns": ["HUGH L CAREY TUNL", "BROOKLYN BATTERY TUNL", "BKLYN BTRY TUNL"]},
]


def _matches(name_norm: str, patterns: list[str], exclude: list[str]) -> bool:
    if not name_norm:
        return False
    for e in exclude:
        if e in name_norm:
            return False
    for p in patterns:
        if name_norm == p:
            return True
        if name_norm.startswith(p + " "):
            rest = name_norm[len(p) + 1:].split()
            if rest and all(t in QUALIFIERS or t.isdigit() for t in rest):
                return True
    return False


def _structure_polygons(path: Path) -> np.ndarray:
    g = pyogrio.read_dataframe(str(path), columns=["feat_code"])
    g = g.to_crs(NYC_TM)
    return np.asarray(g.geometry.values)


def build(seg: gpd.GeoDataFrame, nodes: pd.DataFrame, inputs) -> tuple[dict, dict]:
    """Return (bridges_tunnels document, stats)."""
    t0 = time.time()
    name_norm = seg["name_norm"].to_numpy()
    rw = seg["rw_type"].to_numpy()
    sid = seg["segment_id"].to_numpy()
    fn = seg["from_node"].to_numpy()
    tn = seg["to_node"].to_numpy()
    length = seg["length_m"].to_numpy()
    drivable = seg["drivable"].to_numpy()
    boro = seg["borough"].to_numpy()

    node_pos = pd.Series(np.arange(len(nodes)), index=nodes["node_id"].to_numpy())
    nx = nodes["x"].to_numpy()
    ny = nodes["y"].to_numpy()
    n_nodes = len(nodes)
    fpos = node_pos.reindex(fn).to_numpy()
    tpos = node_pos.reindex(tn).to_numpy()

    struct_polys = None
    if any("street_in_structure" in s for s in STRUCTURES) and inputs.has("plan_transport_structures"):
        struct_polys = _structure_polygons(inputs["plan_transport_structures"])
        tree = shapely.STRtree(struct_polys)
    else:
        tree = None

    docs: list[dict] = []
    stats = {"found": 0, "missing": [], "by_kind": {}}
    for spec in STRUCTURES:
        pats = spec["patterns"]
        excl = spec.get("exclude", [])
        hit = np.array([_matches(n, pats, excl) for n in name_norm])
        matched_by = "name"
        if not hit.any() and spec.get("street_in_structure") and tree is not None:
            cand = np.flatnonzero(name_norm == spec["street_in_structure"])
            if len(cand):
                pairs = tree.query(seg.geometry.values[cand], predicate="intersects")
                inside = np.unique(cand[pairs[0]]) if pairs.size else np.array([], dtype=np.int64)
                hit = np.zeros(len(seg), dtype=bool)
                hit[inside] = True
                matched_by = "street_in_structure"
        idx = np.flatnonzero(hit)
        if len(idx) == 0:
            stats["missing"].append(spec["name"])
            docs.append({"id": spec["id"], "name": spec["name"], "kind": spec["kind"], "found": False,
                         "matched_by": "none", "patterns": pats, "segment_ids": [], "ramp_segment_ids": [],
                         "n_segments": 0, "length_m": 0.0, "end_nodes": [], "splits_network": False,
                         "note": "no CSCL segment carries this name"})
            continue
        deck = idx[rw[idx] != S.RW_RAMP]
        ramps = idx[rw[idx] == S.RW_RAMP]
        core = deck if len(deck) else idx

        # nodes of the structure that also carry a segment outside it -> the ends
        in_set = np.zeros(len(seg), dtype=bool)
        in_set[core] = True
        struct_nodes = np.unique(np.concatenate([fpos[core], tpos[core]]))
        outside = ~in_set
        out_nodes = np.unique(np.concatenate([fpos[outside], tpos[outside]]))
        end_pos = np.intersect1d(struct_nodes, out_nodes)
        # a structure node touched by nothing else is a dangling end too
        counts = np.bincount(np.concatenate([fpos[core], tpos[core]]), minlength=n_nodes)
        dangling = struct_nodes[counts[struct_nodes] == 1]
        end_pos = np.union1d(end_pos, dangling)

        # would removing the structure disconnect its ends?
        keep = outside
        rows = np.concatenate([fpos[keep], tpos[keep]])
        cols = np.concatenate([tpos[keep], fpos[keep]])
        adj = coo_matrix((np.ones(len(rows), dtype=np.int8), (rows, cols)), shape=(n_nodes, n_nodes))
        ncomp, labels = connected_components(adj, directed=False)
        end_labels = sorted({int(labels[p]) for p in end_pos})
        splits = len(end_labels) >= 2

        doc = {
            "id": spec["id"], "name": spec["name"], "kind": spec["kind"], "found": True, "matched_by": matched_by,
            "patterns": pats,
            "cscl_names": sorted({str(n) for n in name_norm[idx] if n}),
            "segment_ids": [int(v) for v in np.sort(sid[core])],
            "ramp_segment_ids": [int(v) for v in np.sort(sid[ramps])],
            "n_segments": int(len(core)), "n_ramp_segments": int(len(ramps)),
            "length_m": round(float(length[core].sum()), 1),
            "drivable_segments": int(drivable[core].sum()),
            "boroughs": sorted({int(b) for b in boro[core] if b > 0}),
            "rw_types": sorted({int(r) for r in rw[core]}),
            "end_nodes": [{"node_id": int(nodes["node_id"].to_numpy()[p]), "x": round(float(nx[p]), 2),
                           "y": round(float(ny[p]), 2), "component": int(labels[p])} for p in end_pos],
            "n_end_nodes": int(len(end_pos)),
            "distinct_end_components": len(end_labels),
            "splits_network": bool(splits),
            "connected_both_ends": bool(len(end_pos) >= 2),
        }
        docs.append(doc)
        stats["found"] += 1
        stats["by_kind"][spec["kind"]] = stats["by_kind"].get(spec["kind"], 0) + 1

    out = {
        "schema_version": 1,
        "crs": "NYC_TM",
        "source": "NYC Street Centerline (CSCL, inkn-q76z) names; DoITT planimetric transportation structures (r9cu-9r7b) where noted",
        "n_structures": len(docs),
        "n_found": stats["found"],
        "bridges_tunnels": docs,
    }
    stats["structures"] = len(docs)
    stats["not_connected_both_ends"] = [d["name"] for d in docs if d["found"] and not d["connected_both_ends"]]
    stats["does_not_split_network"] = [d["name"] for d in docs if d["found"] and not d["splits_network"]]
    log.info("bridges/tunnels: %d of %d found in %.1fs (missing: %s)", stats["found"], len(docs), time.time() - t0, stats["missing"])
    return out, stats
