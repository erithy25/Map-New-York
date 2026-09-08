"""Write core/tests/data/runtime/*.nycb with the *foundation* exporter and record the expected values.

The C++ reader (core/io/Nycb.h) must read the bytes that pipeline/nycsim_pipeline/runtime/nycb.py
produces. Rather than describe that format twice, this script builds one file of every
DATA_CONTRACTS §15 section type with the exporter itself and writes a JSON of the values the C++
test asserts. Regenerate whenever the exporter or the contract changes.

Run: python3 docs/verification/core/gen_nycb_fixture.py
"""
from __future__ import annotations

import json
import pathlib
import sys

import numpy as np

sys.path.insert(0, "pipeline")

from nycsim_pipeline.runtime.nycb import NycbWriter, aligned_dtype, describe_layout  # noqa: E402

OUT = pathlib.Path("core/tests/data/runtime")

NODE_DT = aligned_dtype([("id", "<i8"), ("x", "<f4"), ("y", "<f4"), ("z", "<f4"),
                         ("control", "u1"), ("signal_source", "u1"), ("pad", "<u2")])
SEG_DT = aligned_dtype([("id", "<i8"), ("from_node", "<i8"), ("to_node", "<i8"),
                        ("first_vertex", "<u4"), ("vertex_count", "<u4"),
                        ("rw_type", "u1"), ("traffic_dir", "u1"), ("travel_lanes", "u1"), ("park_lanes", "u1"),
                        ("width_m", "<f4"), ("speed_mph", "u1"), ("bike_lane", "u1"), ("surface", "u1"),
                        ("borough", "u1"), ("name_str", "<u4")])
VTX_DT = aligned_dtype([("x", "<f4"), ("y", "<f4"), ("z", "<f4")])
LANE_DT = aligned_dtype([("id", "<i8"), ("segment_id", "<i8"), ("index_from_center", "i1"),
                         ("direction", "i1"), ("kind", "i1"), ("pad", "i1"), ("width_m", "<f4"),
                         ("speed_mps", "<f4"), ("first_vertex", "<u4"), ("vertex_count", "<u4"),
                         ("first_succ", "<u4"), ("succ_count", "<u4")])
LINK_DT = aligned_dtype([("lane_id", "<i8")])
JUNC_DT = aligned_dtype([("id", "<i8"), ("from_lane", "<i8"), ("to_lane", "<i8"), ("turn", "u1"),
                         ("pad", "u1", (3,)), ("signal_group", "<i4"), ("first_vertex", "<u4"),
                         ("vertex_count", "<u4"), ("first_yield", "<u4"), ("yield_count", "<u4")])
CTRL_DT = aligned_dtype([("node_id", "<i8"), ("controller_id", "<i4"), ("cycle_s", "<f4"),
                         ("offset_s", "<f4"), ("first_phase", "<u4"), ("phase_count", "<u4")])
PHASE_DT = aligned_dtype([("group", "<i4"), ("green_s", "<f4"), ("yellow_s", "<f4"), ("allred_s", "<f4"),
                          ("ped_walk_s", "<f4"), ("ped_flash_s", "<f4"), ("lpi_s", "<f4")])
TILE_DT = aligned_dtype([("tx", "<i4"), ("ty", "<i4"), ("z_min", "<f4"), ("z_max", "<f4"),
                         ("n_buildings", "<u4"), ("n_props", "<u4"), ("flags", "u1"),
                         ("borough_mask", "u1"), ("pad", "<u2")])
ROUTE_DT = aligned_dtype([("name_str", "<u4"), ("first_vertex", "<u4"), ("vertex_count", "<u4"),
                          ("first_stop", "<u4"), ("stop_count", "<u4"), ("headway_min", "<u2", (24,))])
STOP_DT = aligned_dtype([("id", "<i8"), ("x", "<f4"), ("y", "<f4"), ("z", "<f4"), ("name_str", "<u4")])
RSTOP_DT = aligned_dtype([("stop_id", "<i8")])
CELL_DT = aligned_dtype([("nta_str", "<u4"), ("hour", "u1"), ("dow", "u1"), ("pad", "<u2"),
                         ("veh_per_km_lane", "<f4"), ("ped_per_m2", "<f4"), ("taxi_share", "<f4"),
                         ("truck_share", "<f4"), ("bus_share", "<f4"), ("bike_share", "<f4")])
NTA_DT = aligned_dtype([("nta_str", "<u4"), ("first_vertex", "<u4"), ("vertex_count", "<u4")])
POI_DT = aligned_dtype([("x", "<f4"), ("y", "<f4"), ("addr_str", "<u4")])


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    expected: dict = {"sizeof": {}, "sections": {}, "strings": {}}

    w = NycbWriter()
    nodes = np.zeros(3, dtype=NODE_DT)
    nodes["id"] = [1000, 2000, 3000]
    nodes["x"] = [-3011.9766, 0.0, 1234.5]
    nodes["y"] = [5379.805, -1.5, 6789.0]
    nodes["z"] = [10.25, 0.0, -2.5]
    nodes["control"] = [1, 0, 2]
    nodes["signal_source"] = [1, 4, 0]
    w.add_array("nodes", nodes)

    segs = np.zeros(2, dtype=SEG_DT)
    segs["id"] = [50, 51]
    segs["from_node"] = [1000, 2000]
    segs["to_node"] = [2000, 3000]
    segs["first_vertex"] = [0, 2]
    segs["vertex_count"] = [2, 3]
    segs["rw_type"] = [1, 3]
    segs["traffic_dir"] = [0, 1]
    segs["travel_lanes"] = [2, 4]
    segs["park_lanes"] = [1, 0]
    segs["width_m"] = [12.8, 24.4]
    segs["speed_mph"] = [25, 45]
    segs["bike_lane"] = [2, 0]
    segs["surface"] = [0, 1]
    segs["borough"] = [1, 3]
    segs["name_str"] = [w.strings.add("BROADWAY"), w.strings.add("BROOKLYN BRIDGE")]
    w.add_array("segments", segs)

    vtx = np.zeros(5, dtype=VTX_DT)
    vtx["x"] = [0.0, 100.0, 100.0, 200.0, 300.0]
    vtx["y"] = [0.0, 0.0, 50.0, 60.0, 70.0]
    vtx["z"] = [1.0, 1.5, 2.0, 2.5, 3.0]
    w.add_array("vertices", vtx)

    lanes = np.zeros(2, dtype=LANE_DT)
    lanes["id"] = [900, 901]
    lanes["segment_id"] = [50, 51]
    lanes["index_from_center"] = [1, -2]
    lanes["direction"] = [1, -1]
    lanes["kind"] = [0, 3]
    lanes["width_m"] = [3.2, 3.5]
    lanes["speed_mps"] = [11.176, 20.1168]
    lanes["first_vertex"] = [0, 2]
    lanes["vertex_count"] = [2, 3]
    lanes["first_succ"] = [0, 1]
    lanes["succ_count"] = [1, 1]
    w.add_array("lanes", lanes)

    links = np.zeros(2, dtype=LINK_DT)
    links["lane_id"] = [901, 900]
    w.add_array("lane_links", links)

    junc = np.zeros(1, dtype=JUNC_DT)
    junc["id"] = [7000]
    junc["from_lane"] = [900]
    junc["to_lane"] = [901]
    junc["turn"] = [1]
    junc["signal_group"] = [2]
    junc["first_vertex"] = [1]
    junc["vertex_count"] = [3]
    junc["first_yield"] = [0]
    junc["yield_count"] = [1]
    w.add_array("junction_lanes", junc)

    yields = np.zeros(1, dtype=LINK_DT)
    yields["lane_id"] = [901]
    w.add_array("yield_links", yields)
    w.add_strtab()
    w.write(OUT / "roadgraph.nycb")

    expected["sections"]["roadgraph.nycb"] = {
        "nodes": 3, "segments": 2, "vertices": 5, "lanes": 2, "lane_links": 2,
        "junction_lanes": 1, "yield_links": 1, "strtab": len(w.strings),
    }
    expected["strings"]["BROADWAY"] = int(segs["name_str"][0])
    expected["strings"]["BROOKLYN BRIDGE"] = int(segs["name_str"][1])

    w2 = NycbWriter()
    ctrl = np.zeros(2, dtype=CTRL_DT)
    ctrl["node_id"] = [1000, 3000]
    ctrl["controller_id"] = [11, 22]
    ctrl["cycle_s"] = [90.0, 60.0]
    ctrl["offset_s"] = [0.0, 12.5]
    ctrl["first_phase"] = [0, 2]
    ctrl["phase_count"] = [2, 1]
    w2.add_array("controllers", ctrl)
    ph = np.zeros(3, dtype=PHASE_DT)
    ph["group"] = [0, 1, 0]
    ph["green_s"] = [45.0, 35.0, 30.0]
    ph["yellow_s"] = [3.0, 3.0, 3.0]
    ph["allred_s"] = [2.0, 2.0, 2.0]
    ph["ped_walk_s"] = [7.0, 7.0, 7.0]
    ph["ped_flash_s"] = [11.0, 11.0, 11.0]
    ph["lpi_s"] = [7.0, 0.0, 0.0]
    w2.add_array("phases", ph)
    w2.write(OUT / "signals.nycb")
    expected["sections"]["signals.nycb"] = {"controllers": 2, "phases": 3}

    w3 = NycbWriter()
    tiles = np.zeros(2, dtype=TILE_DT)
    tiles["tx"] = [-3, 4]
    tiles["ty"] = [5, -7]
    tiles["z_min"] = [0.0, -2.1]
    tiles["z_max"] = [40.0, 12.0]
    tiles["n_buildings"] = [412, 0]
    tiles["n_props"] = [180, 3]
    tiles["flags"] = [5, 2]
    tiles["borough_mask"] = [1, 8]
    w3.add_array("tiles", tiles)
    w3.write(OUT / "tiles.nycb")
    expected["sections"]["tiles.nycb"] = {"tiles": 2}

    w4 = NycbWriter()
    routes = np.zeros(1, dtype=ROUTE_DT)
    routes["name_str"] = [w4.strings.add("M15-SBS")]
    routes["first_vertex"] = [0]
    routes["vertex_count"] = [3]
    routes["first_stop"] = [0]
    routes["stop_count"] = [2]
    routes["headway_min"][0] = list(range(24))
    w4.add_array("bus_routes", routes)
    stops = np.zeros(2, dtype=STOP_DT)
    stops["id"] = [400001, 400002]
    stops["x"] = [1.0, 2.0]
    stops["y"] = [3.0, 4.0]
    stops["z"] = [5.0, 6.0]
    stops["name_str"] = [w4.strings.add("1 AV/E 14 ST"), w4.strings.add("1 AV/E 23 ST")]
    w4.add_array("bus_stops", stops)
    rstops = np.zeros(2, dtype=RSTOP_DT)
    rstops["stop_id"] = [400001, 400002]
    w4.add_array("route_stops", rstops)
    w4.add_array("vertices", vtx[:3])
    w4.add_strtab()
    w4.write(OUT / "transit.nycb")
    expected["sections"]["transit.nycb"] = {
        "bus_routes": 1, "bus_stops": 2, "route_stops": 2, "vertices": 3, "strtab": len(w4.strings),
    }

    w5 = NycbWriter()
    cells = np.zeros(2, dtype=CELL_DT)
    cells["nta_str"] = [w5.strings.add("MN17"), w5.strings.add("BK09")]
    cells["hour"] = [8, 20]
    cells["dow"] = [0, 2]
    cells["veh_per_km_lane"] = [55.0, 12.0]
    cells["ped_per_m2"] = [0.35, 0.02]
    cells["taxi_share"] = [0.28, 0.03]
    cells["truck_share"] = [0.06, 0.02]
    cells["bus_share"] = [0.04, 0.01]
    cells["bike_share"] = [0.05, 0.01]
    w5.add_array("cells", cells)
    ntas = np.zeros(1, dtype=NTA_DT)
    ntas["nta_str"] = [w5.strings.add("MN17")]
    ntas["first_vertex"] = [0]
    ntas["vertex_count"] = [4]
    w5.add_array("nta_polys", ntas)
    w5.add_array("vertices", vtx[:4])
    w5.add_strtab()
    w5.write(OUT / "density.nycb")
    expected["sections"]["density.nycb"] = {
        "cells": 2, "nta_polys": 1, "vertices": 4, "strtab": len(w5.strings),
    }

    w6 = NycbWriter()
    pois = np.zeros(2, dtype=POI_DT)
    pois["x"] = [-3011.9766, 100.0]
    pois["y"] = [5379.805, 200.0]
    pois["addr_str"] = [w6.strings.add("350 5 AVENUE"), w6.strings.add("1 CENTRE STREET")]
    w6.add_array("pois", pois)
    # The named places the GPS searches, in the same record and the same string table as the
    # addresses. The fixture carried none, so the only thing exercising the section was the real
    # container -- and the C++ reader is allowed to shrug at a real file that predates it ("an
    # older container"). A deterministic fixture with two places is what makes that path a test
    # rather than a courtesy.
    places = np.zeros(2, dtype=POI_DT)
    places["x"] = [-1758.7964, 980.0]
    places["y"] = [8252.8652, -420.0]
    places["addr_str"] = [w6.strings.add("Bethesda Terrace"), w6.strings.add("Red Hook")]
    w6.add_array("places", places)
    w6.add_strtab()
    w6.write(OUT / "pois.nycb")
    expected["sections"]["pois.nycb"] = {"pois": 2, "places": 2, "strtab": len(w6.strings)}

    layout = describe_layout({
        "nodes": NODE_DT, "segments": SEG_DT, "vertices": VTX_DT, "lanes": LANE_DT,
        "lane_links": LINK_DT, "junction_lanes": JUNC_DT, "controllers": CTRL_DT,
        "phases": PHASE_DT, "tiles": TILE_DT, "bus_routes": ROUTE_DT, "bus_stops": STOP_DT,
        "cells": CELL_DT, "nta_polys": NTA_DT, "pois": POI_DT, "places": POI_DT,
    })
    expected["sizeof"] = {k: v["sizeof"] for k, v in layout["sections"].items()}
    expected["sizeof"]["header"] = layout["container"]["header"]["sizeof"]
    expected["sizeof"]["index_entry"] = layout["container"]["index_entry"]["sizeof"]
    (OUT / "expected.json").write_text(json.dumps(expected, indent=1, sort_keys=True))
    write_cpp_header(expected)
    write_real_counts()
    print(json.dumps(expected["sizeof"], sort_keys=True))
    for f in sorted(OUT.glob("*.nycb")):
        print(f, f.stat().st_size, "bytes")
    return 0


def write_real_counts() -> None:
    """Record the real exporter output under data/processed/runtime/ for the C++ interop test.

    The C++ test reads this JSON at run time (with nycsim::json), so refreshing it after the roads
    stage re-runs needs no recompilation. Each file records its byte size: the test compares counts
    only while the recorded size still describes the file on disk, and says so loudly otherwise,
    because a changed size means the data was regenerated and this file is stale.

    `parquet_rows` is the cross-check that matters: the exporter must emit exactly one record per
    parquet row. It is computed here because C++ cannot read parquet.
    """
    processed = pathlib.Path("data/processed")
    from nycsim_pipeline.runtime.nycb import NycbReader  # local import: only needed here

    parquet_maps = {
        "roadgraph": {"nodes": "roads/nodes", "segments": "roads/segments",
                      "lanes": "roads/lanes", "junction_lanes": "roads/junction_lanes"},
        "signals": {"controllers": "roads/signals"},
        "transit": {},
        "density": {},
        # `tiles` is one record per row of the tile index, so it cross-checks against the parquet. `pois` and
        # `points` deliberately do not: a building with no address and a landmark with no name have no record
        # (§15), so their counts are below the parquet's and are checked by the exporter's own tests instead.
        "tiles": {"tiles": "tiles/index"},
        "pois": {},
        "landmarks": {},
    }
    out: dict = {"schema_version": 1, "files": {}}
    for stem, parquet_map in parquet_maps.items():
        path = processed / "runtime" / f"{stem}.nycb"
        if not path.exists():
            continue
        reader = NycbReader(path)
        entry = {
            "bytes": path.stat().st_size,
            "sections": {k: {"count": v.element_count, "element_size": v.element_size}
                         for k, v in reader.sections.items()},
            "parquet_rows": {},
        }
        for section, parquet in parquet_map.items():
            pfile = processed / f"{parquet}.parquet"
            if not pfile.exists():
                continue
            import pyarrow.parquet as pq
            rows = pq.ParquetFile(pfile).metadata.num_rows
            entry["parquet_rows"][section] = rows
            got = reader.sections[section].element_count if section in reader.sections else None
            status = "OK" if got == rows else "MISMATCH"
            print(f"  {stem}.nycb/{section}: nycb {got} vs {parquet}.parquet {rows}  [{status}]")
        out["files"][f"{stem}.nycb"] = entry
    (OUT / "real_counts.json").write_text(json.dumps(out, indent=1, sort_keys=True))
    print(f"wrote {OUT / 'real_counts.json'} for {len(out['files'])} real files")


def write_cpp_header(expected: dict) -> None:
    """Emit core/tests/io/nycb_expected.h with everything the C++ test asserts."""
    h = pathlib.Path("core/tests/io/nycb_expected.h")
    lines = [
        "// GENERATED by docs/verification/core/gen_nycb_fixture.py. DO NOT EDIT BY HAND.",
        "// Expected sizes and section counts of the NYCB files written by the *foundation*",
        "// exporter pipeline/nycsim_pipeline/runtime/nycb.py.",
        "#pragma once", "", "#include <cstdint>", "", "namespace nycsim_test_nycb {", "",
        "struct SectionCount { const char* file; const char* section; uint32_t count; };",
        "inline constexpr SectionCount kFixtureCounts[] = {",
    ]
    for f in sorted(expected["sections"]):
        for sec in sorted(expected["sections"][f]):
            lines.append(f'    {{"{f}", "{sec}", {expected["sections"][f][sec]}}},')
    lines += ["};", f"inline constexpr int kFixtureCountN = "
              f"{sum(len(v) for v in expected['sections'].values())};", ""]
    lines += ["struct RecordSize { const char* name; uint32_t bytes; };",
              "inline constexpr RecordSize kRecordSizes[] = {"]
    for k in sorted(expected["sizeof"]):
        lines.append(f'    {{"{k}", {expected["sizeof"][k]}}},')
    lines += ["};", f"inline constexpr int kRecordSizeN = {len(expected['sizeof'])};", ""]
    lines += ["struct StringOffset { const char* text; uint32_t offset; };",
              "inline constexpr StringOffset kStringOffsets[] = {"]
    for k in sorted(expected["strings"]):
        lines.append(f'    {{"{k}", {expected["strings"][k]}}},')
    lines += ["};", f"inline constexpr int kStringOffsetN = {len(expected['strings'])};", ""]
    lines += ["// The real exporter output under data/processed/runtime/ is NOT snapshotted here:",
              "// the test reads core/tests/data/runtime/real_counts.json at run time so the roads",
              "// stage can regenerate its data without a recompilation.", "",
              "}  // namespace nycsim_test_nycb"]
    h.write_text("\n".join(lines) + "\n")
    print(f"wrote {h}")


if __name__ == "__main__":
    raise SystemExit(main())
