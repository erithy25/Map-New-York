"""``data/processed/runtime/density.nycb`` — the §15 runtime binary read by ``core/traffic/Density.cpp``.

Sections and record layouts are fixed by ``DensityTable::loadFromNycb``:

* ``cells``      32 bytes: ``uint32 nta_str; uint8 hour, dow; uint16 pad; float veh_per_km_lane,
  ped_per_m2, taxi_share, truck_share, bus_share, bike_share``
* ``nta_polys``  12 bytes: ``uint32 nta_str; uint32 first_vertex, vertex_count``
* ``vertices``   12 bytes: ``float x, y, z`` (NYC_TM metres, z = 0 — the table is planar)
* ``strtab``     the NTA codes

The container itself is written by :mod:`nycsim_pipeline.runtime.nycb`, which is foundation code owned
by the roads stage; this module only lays the traffic records out for it.  Exterior rings only:
``DensityTable::pointInNta`` runs a ray cast over closed rings, so an NTA's holes (none of the 2020
NTAs has one that matters for lane assignment) would not be honoured anyway.
"""
from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import polars as pl
import shapely

from ..runtime.nycb import NycbReader, NycbWriter, aligned_dtype, write_layout
from .geo import NtaTable

log = logging.getLogger("nycsim.traffic.runtime_export")

CELL_DTYPE = aligned_dtype([
    ("nta_str", "<u4"), ("hour", "u1"), ("dow", "u1"), ("pad", "<u2"),
    ("veh_per_km_lane", "<f4"), ("ped_per_m2", "<f4"), ("taxi_share", "<f4"),
    ("truck_share", "<f4"), ("bus_share", "<f4"), ("bike_share", "<f4"),
])
POLY_DTYPE = aligned_dtype([("nta_str", "<u4"), ("first_vertex", "<u4"), ("vertex_count", "<u4")])
VERTEX_DTYPE = aligned_dtype([("x", "<f4"), ("y", "<f4"), ("z", "<f4")])
assert CELL_DTYPE.itemsize == 32, CELL_DTYPE.itemsize
assert POLY_DTYPE.itemsize == 12 and VERTEX_DTYPE.itemsize == 12

SIMPLIFY_M = 5.0            # ring simplification tolerance; keeps the polygon section small
MIN_RING_AREA_M2 = 2000.0   # drop slivers (pier tips, bridge approaches) that cannot hold a lane


def _rings(geom: shapely.Geometry) -> list[np.ndarray]:
    g = shapely.simplify(geom, SIMPLIFY_M, preserve_topology=True)
    if g.is_empty:
        g = geom
    parts = shapely.get_parts(g) if g.geom_type.startswith("Multi") else [g]
    out: list[np.ndarray] = []
    for p in parts:
        if p.is_empty or p.geom_type != "Polygon" or p.area < MIN_RING_AREA_M2:
            continue
        coords = np.asarray(shapely.get_coordinates(shapely.get_exterior_ring(p)), dtype=np.float64)
        if len(coords) < 4:
            continue
        out.append(coords)
    return out


def write_density_nycb(path: Path, nta: NtaTable, density: pl.DataFrame) -> Path:
    """Write ``density.nycb`` from the §10 dataframe and the NTA polygons."""
    required = ["nta_code", "hour", "dow", "veh_per_km_lane", "ped_per_m2_sidewalk",
                "taxi_share", "truck_share", "bus_share", "bike_share"]
    missing = [c for c in required if c not in density.columns]
    if missing:
        raise ValueError(f"density frame is missing {missing}")
    df = density.sort(["nta_code", "dow", "hour"])
    w = NycbWriter()
    codes = df["nta_code"].to_list()
    cells = np.zeros(df.height, dtype=CELL_DTYPE)
    cells["nta_str"] = w.strings.add_many(codes)
    cells["hour"] = df["hour"].to_numpy().astype(np.uint8)
    cells["dow"] = df["dow"].to_numpy().astype(np.uint8)
    for src, dst in (("veh_per_km_lane", "veh_per_km_lane"), ("ped_per_m2_sidewalk", "ped_per_m2"),
                     ("taxi_share", "taxi_share"), ("truck_share", "truck_share"),
                     ("bus_share", "bus_share"), ("bike_share", "bike_share")):
        v = df[src].to_numpy().astype(np.float32)
        if not np.isfinite(v).all():
            raise ValueError(f"{src} contains non-finite values")
        cells[dst] = v
    w.add_array("cells", cells)

    polys: list[tuple[int, int, int]] = []
    verts: list[np.ndarray] = []
    n_v = 0
    for i, code in enumerate(nta.codes):
        sid = w.strings.add(code)
        for ring in _rings(nta.geoms[i]):
            polys.append((sid, n_v, len(ring)))
            verts.append(ring)
            n_v += len(ring)
    if not polys:
        raise ValueError("no NTA rings survived simplification")
    parr = np.zeros(len(polys), dtype=POLY_DTYPE)
    parr["nta_str"] = [p[0] for p in polys]
    parr["first_vertex"] = [p[1] for p in polys]
    parr["vertex_count"] = [p[2] for p in polys]
    vall = np.concatenate(verts)
    varr = np.zeros(len(vall), dtype=VERTEX_DTYPE)
    varr["x"] = vall[:, 0].astype(np.float32)
    varr["y"] = vall[:, 1].astype(np.float32)
    varr["z"] = 0.0
    w.add_array("nta_polys", parr)
    w.add_array("vertices", varr)
    w.add_strtab()
    w.write(path)
    # The field offsets the C++ reader has to agree with, beside the file. ``roadgraph.nycb`` and
    # ``transit.nycb`` have always written theirs; ``density.nycb`` did not, so ``cells`` and
    # ``nta_polys`` were read by ``core/src/traffic/Density.cpp`` against a layout described
    # nowhere -- and a description that does not exist cannot be compared with anything.
    layout_path = path.with_suffix(".layout.json")
    write_layout(layout_path, {"cells": CELL_DTYPE, "nta_polys": POLY_DTYPE,
                               "vertices": VERTEX_DTYPE})
    log.info("wrote %s: %d cells, %d rings, %d vertices, %d bytes (layout %s)", path, len(cells),
             len(parr), len(varr), path.stat().st_size, layout_path.name)
    return path


def verify_density_nycb(path: Path, density: pl.DataFrame) -> dict:
    """Read the file back and check it against the dataframe (round-trip evidence for the report)."""
    r = NycbReader(path)
    cells = r.read("cells", CELL_DTYPE)
    polys = r.read("nta_polys", POLY_DTYPE)
    verts = r.read("vertices", VERTEX_DTYPE)
    blob = r.strings()
    if len(cells) != density.height:
        raise ValueError(f"{path}: {len(cells)} cells != {density.height} rows")
    df = density.sort(["nta_code", "dow", "hour"])
    codes = [r.string_at(int(o), blob) for o in cells["nta_str"]]
    if codes != df["nta_code"].to_list():
        raise ValueError(f"{path}: NTA codes do not round-trip")
    for src, dst in (("veh_per_km_lane", "veh_per_km_lane"), ("ped_per_m2_sidewalk", "ped_per_m2"),
                     ("taxi_share", "taxi_share"), ("truck_share", "truck_share"),
                     ("bus_share", "bus_share"), ("bike_share", "bike_share")):
        a = df[src].to_numpy().astype(np.float32)
        b = cells[dst]
        if not np.allclose(a, b, rtol=0, atol=0):
            raise ValueError(f"{path}: {src} does not round-trip")
    if int(polys["first_vertex"][-1]) + int(polys["vertex_count"][-1]) != len(verts):
        raise ValueError(f"{path}: polygon vertex ranges do not cover the vertex section")
    out = {"cells": int(len(cells)), "rings": int(len(polys)), "vertices": int(len(verts)),
           "bytes": int(path.stat().st_size), "sections": sorted(r.sections),
           "cell_element_size": int(r.sections["cells"].element_size)}
    r.close()
    return out
