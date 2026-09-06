"""roads/pavement/{tile}.parquet (DATA_CONTRACTS §7): the real paved surfaces of the city, clipped to the
1 km tile grid.

Sources (all DoITT planimetric, EPSG:4326 exports of the 2014-refresh basemap, plus DOT plazas):
  kind 0 roadbed      plan_roadbed        (i36f-5ih7)   asphalt carriageway polygons
  kind 1 sidewalk     plan_sidewalk       (52n9-sdep)
  kind 2 median       plan_median         (ees7-4ufv)
  kind 3 plaza        plan_public_plazas  (ue2e-9jm2) + ped_plazas (k5k6-6jex)
  kind 4 curb         plan_curb           (5xvt-8cbk)   published as lines; stored as the real curb face,
                                                        buffered to CURB_WIDTH_M so the contract's polygon
                                                        type holds (documented in the report)
  kind 5 crosswalk    derived at every controlled intersection from the real leg widths (flagged source=1)
  kind 6 parking lot  plan_parking_lot    (7cgt-uhhz)

Polygons that straddle a tile boundary are clipped, so a tile file contains exactly the pavement inside that
tile and the union over tiles reproduces the source. ``surface`` for roadbeds is taken from the nearest CSCL
segment (so the real cobblestone/steel-plate/concrete streets keep their surface); the other kinds use their
material class. ``roughness_seed`` is a deterministic hash of the source feature id.
"""
from __future__ import annotations

import logging
import time
import zlib
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import pyogrio
import shapely

from ..crs import NYC_TM, TILE_SIZE_M
from . import schema as S

log = logging.getLogger("nycsim.roads.pavement")

CURB_WIDTH_M = 0.30
CROSSWALK_DEPTH_M = 3.66      # NYC standard 12 ft crosswalk
CROSSWALK_SETBACK_M = 1.0
MIN_AREA_M2 = 0.25
PAV_SRC_PLANIMETRIC, PAV_SRC_DERIVED = 0, 1


def _tile_name(tx: int, ty: int) -> str:
    return f"t_{int(tx)}_{int(ty)}"


def _clip_to_tiles(geoms: np.ndarray, attrs: dict[str, np.ndarray]) -> tuple[np.ndarray, dict[str, np.ndarray], np.ndarray, np.ndarray]:
    """Split every geometry at the 1 km grid. Returns (geoms, attrs, tx, ty)."""
    bounds = shapely.bounds(geoms)
    tx0 = np.floor(bounds[:, 0] / TILE_SIZE_M).astype(np.int32)
    ty0 = np.floor(bounds[:, 1] / TILE_SIZE_M).astype(np.int32)
    tx1 = np.floor(np.nextafter(bounds[:, 2], -np.inf) / TILE_SIZE_M).astype(np.int32)
    ty1 = np.floor(np.nextafter(bounds[:, 3], -np.inf) / TILE_SIZE_M).astype(np.int32)
    tx1 = np.maximum(tx1, tx0)
    ty1 = np.maximum(ty1, ty0)
    single = (tx0 == tx1) & (ty0 == ty1)

    out_geom = [geoms[single]]
    out_idx = [np.flatnonzero(single)]
    out_tx = [tx0[single]]
    out_ty = [ty0[single]]

    multi = np.flatnonzero(~single)
    if len(multi):
        boxes: list = []
        srcs: list[int] = []
        bxs: list[int] = []
        bys: list[int] = []
        for i in multi:
            for ty in range(int(ty0[i]), int(ty1[i]) + 1):
                for tx in range(int(tx0[i]), int(tx1[i]) + 1):
                    boxes.append(shapely.box(tx * TILE_SIZE_M, ty * TILE_SIZE_M, (tx + 1) * TILE_SIZE_M, (ty + 1) * TILE_SIZE_M))
                    srcs.append(int(i))
                    bxs.append(tx)
                    bys.append(ty)
        srcs_a = np.asarray(srcs, dtype=np.int64)
        pieces = shapely.intersection(geoms[srcs_a], np.asarray(boxes, dtype=object))
        keep = ~shapely.is_empty(pieces) & shapely.is_valid(pieces)
        out_geom.append(pieces[keep])
        out_idx.append(srcs_a[keep])
        out_tx.append(np.asarray(bxs, dtype=np.int32)[keep])
        out_ty.append(np.asarray(bys, dtype=np.int32)[keep])

    g = np.concatenate(out_geom) if len(out_geom) else np.array([], dtype=object)
    idx = np.concatenate(out_idx) if len(out_idx) else np.array([], dtype=np.int64)
    tx = np.concatenate(out_tx) if len(out_tx) else np.array([], dtype=np.int32)
    ty = np.concatenate(out_ty) if len(out_ty) else np.array([], dtype=np.int32)
    return g, {k: v[idx] for k, v in attrs.items()}, tx, ty


def _explode(gdf: gpd.GeoDataFrame) -> tuple[np.ndarray, np.ndarray]:
    """Explode multi-part geometries; returns (single-part geometries, source row index)."""
    g = gdf.geometry.values
    n = shapely.get_num_geometries(g)
    idx = np.repeat(np.arange(len(g)), n)
    parts = np.concatenate([shapely.get_parts(gi) if ni > 1 else np.array([gi], dtype=object)
                            for gi, ni in zip(g, n)]) if len(g) else np.array([], dtype=object)
    return parts, idx


def _seed(source_id: np.ndarray) -> np.ndarray:
    return np.array([zlib.crc32(str(s).encode()) & 0xFFFFFFFF for s in source_id], dtype=np.uint32)


class Accumulator:
    """Collects clipped pavement rows per tile as WKB, so peak memory stays close to the output size."""

    def __init__(self) -> None:
        self.parts: dict[str, list[pd.DataFrame]] = {}
        self.rows = 0

    def add(self, geoms: np.ndarray, kind: int, surface: np.ndarray, source_id: np.ndarray,
            feat_code: np.ndarray, source: int, tx: np.ndarray, ty: np.ndarray) -> None:
        if len(geoms) == 0:
            return
        area = shapely.area(geoms)
        keep = area >= MIN_AREA_M2
        if not keep.any():
            return
        geoms, surface, source_id, feat_code, tx, ty = geoms[keep], surface[keep], source_id[keep], feat_code[keep], tx[keep], ty[keep]
        df = pd.DataFrame({
            "kind": np.full(len(geoms), kind, dtype=np.int8),
            "surface": surface.astype(np.int8),
            "roughness_seed": _seed(source_id),
            "area_m2": shapely.area(geoms).astype(np.float32),
            "source": np.full(len(geoms), source, dtype=np.int8),
            "source_id": source_id.astype(str),
            "feat_code": feat_code.astype(np.int32),
            "geometry": shapely.to_wkb(geoms),
            "tile": [_tile_name(a, b) for a, b in zip(tx, ty)],
        })
        for tile, grp in df.groupby("tile", sort=False):
            self.parts.setdefault(tile, []).append(grp.drop(columns=["tile"]))
        self.rows += len(df)

    def tiles(self) -> list[str]:
        return sorted(self.parts)


def _read(path: Path, columns: list[str]) -> gpd.GeoDataFrame:
    g = pyogrio.read_dataframe(str(path), columns=columns)
    return g.to_crs(NYC_TM)


def _add_polygon_source(acc: Accumulator, path: Path, kind: int, surface_val: int, columns: list[str],
                        stats: dict, label: str) -> None:
    t0 = time.time()
    gdf = _read(path, columns)
    parts, src = _explode(gdf)
    src_id = (gdf["source_id"].fillna("").astype(str).to_numpy() if "source_id" in gdf.columns
              else np.arange(len(gdf)).astype(str))[src]
    feat = (pd.to_numeric(gdf["feat_code"], errors="coerce").fillna(0).astype(np.int32).to_numpy()
            if "feat_code" in gdf.columns else np.zeros(len(gdf), dtype=np.int32))[src]
    parts = shapely.make_valid(parts)
    poly = shapely.get_type_id(parts)
    ok = np.isin(poly, [shapely.GeometryType.POLYGON, shapely.GeometryType.MULTIPOLYGON])
    parts, src_id, feat = parts[ok], src_id[ok], feat[ok]
    parts2, src2 = _explode(gpd.GeoDataFrame(geometry=parts, crs=NYC_TM))
    src_id, feat = src_id[src2], feat[src2]
    g, at, tx, ty = _clip_to_tiles(parts2, {"src_id": src_id, "feat": feat})
    acc.add(g, kind, np.full(len(g), surface_val, dtype=np.int8), at["src_id"], at["feat"], PAV_SRC_PLANIMETRIC, tx, ty)
    stats[label] = {"features": int(len(gdf)), "parts": int(len(parts2)), "tile_pieces": int(len(g)),
                    "seconds": round(time.time() - t0, 1)}
    log.info("%s: %d features -> %d tile pieces (%.1fs)", label, len(gdf), len(g), time.time() - t0)
    del gdf, parts, parts2, g


def _roadbed_surface(parts: np.ndarray, seg: gpd.GeoDataFrame) -> np.ndarray:
    """Surface of the nearest CSCL segment (asphalt where the nearest segment is farther than 25 m)."""
    tree = shapely.STRtree(seg.geometry.values)
    pts = shapely.point_on_surface(parts)
    idx = np.asarray(tree.nearest(pts), dtype=np.int64)
    d = shapely.distance(pts, seg.geometry.values[idx])
    surf = seg["surface"].to_numpy()[idx].astype(np.int8)
    surf[d > 25.0] = S.SURF_ASPHALT
    return surf


def _crosswalks(nodes: pd.DataFrame, approaches: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """Crosswalk rectangles across every leg of every controlled intersection."""
    ctrl = nodes.set_index("node_id")["control"]
    deg = nodes.set_index("node_id")["degree_drivable"]
    ap = approaches[approaches["drivable"]].reset_index(drop=True)
    by_node: dict[int, list[int]] = {}
    for i, nd in enumerate(ap["node_id"].to_numpy()):
        by_node.setdefault(int(nd), []).append(i)
    x = ap["x"].to_numpy(); y = ap["y"].to_numpy(); h = np.radians(ap["heading_out"].to_numpy()); w = ap["width_m"].to_numpy()
    polys: list = []
    ids: list[str] = []
    for node, idxs in by_node.items():
        c = int(ctrl.get(node, S.CTRL_NONE))
        if c == S.CTRL_NONE or int(deg.get(node, 0)) < 3:
            continue
        widest = float(max(w[i] for i in idxs))
        for i in idxs:
            along = widest / 2.0 + CROSSWALK_SETBACK_M + CROSSWALK_DEPTH_M / 2.0
            tx, ty = np.cos(h[i]), np.sin(h[i])
            rx, ry = ty, -tx
            cx, cy = x[i] + along * tx, y[i] + along * ty
            hw = max(w[i], 6.0) / 2.0
            hd = CROSSWALK_DEPTH_M / 2.0
            ring = [(cx + hw * rx + hd * tx, cy + hw * ry + hd * ty),
                    (cx - hw * rx + hd * tx, cy - hw * ry + hd * ty),
                    (cx - hw * rx - hd * tx, cy - hw * ry - hd * ty),
                    (cx + hw * rx - hd * tx, cy + hw * ry - hd * ty)]
            polys.append(shapely.Polygon(ring))
            ids.append(f"xw:{node}:{int(ap['segment_id'].to_numpy()[i])}")
    return np.asarray(polys, dtype=object), np.asarray(ids, dtype=object)


def build(inputs, seg: gpd.GeoDataFrame, nodes: pd.DataFrame, approaches: pd.DataFrame, out_dir: Path) -> dict:
    """Write ``out_dir/{tile}.parquet`` for every tile with pavement. Returns stats."""
    t0 = time.time()
    stats: dict = {"sources": {}}
    acc = Accumulator()

    # roadbed (surface from the nearest real centreline)
    if inputs.has("plan_roadbed"):
        ts = time.time()
        gdf = _read(inputs["plan_roadbed"], ["feat_code", "source_id"])
        parts, src = _explode(gdf)
        src_id = gdf["source_id"].fillna("").astype(str).to_numpy()[src]
        feat = pd.to_numeric(gdf["feat_code"], errors="coerce").fillna(0).astype(np.int32).to_numpy()[src]
        parts = shapely.make_valid(parts)
        ok = np.isin(shapely.get_type_id(parts), [shapely.GeometryType.POLYGON, shapely.GeometryType.MULTIPOLYGON])
        parts, src_id, feat = parts[ok], src_id[ok], feat[ok]
        parts2, s2 = _explode(gpd.GeoDataFrame(geometry=parts, crs=NYC_TM))
        src_id, feat = src_id[s2], feat[s2]
        surf = _roadbed_surface(parts2, seg)
        g, at, tx, ty = _clip_to_tiles(parts2, {"src_id": src_id, "feat": feat, "surf": surf})
        acc.add(g, S.PAV_ROADBED, at["surf"], at["src_id"], at["feat"], PAV_SRC_PLANIMETRIC, tx, ty)
        stats["sources"]["roadbed"] = {"features": int(len(gdf)), "parts": int(len(parts2)), "tile_pieces": int(len(g)),
                                       "surface_counts": {int(k): int(v) for k, v in zip(*np.unique(at["surf"], return_counts=True))},
                                       "seconds": round(time.time() - ts, 1)}
        log.info("roadbed: %d features -> %d tile pieces (%.1fs)", len(gdf), len(g), time.time() - ts)
        del gdf, parts, parts2, g

    if inputs.has("plan_sidewalk"):
        _add_polygon_source(acc, inputs["plan_sidewalk"], S.PAV_SIDEWALK, S.SURF_CONCRETE, ["feat_code", "source_id"], stats["sources"], "sidewalk")
    if inputs.has("plan_median"):
        _add_polygon_source(acc, inputs["plan_median"], S.PAV_MEDIAN, S.SURF_CONCRETE, ["feat_code", "source_id"], stats["sources"], "median")
    if inputs.has("plan_public_plazas"):
        _add_polygon_source(acc, inputs["plan_public_plazas"], S.PAV_PLAZA, S.SURF_CONCRETE, ["feat_code", "source_id"], stats["sources"], "public_plaza")
    if inputs.has("ped_plazas"):
        _add_polygon_source(acc, inputs["ped_plazas"], S.PAV_PLAZA, S.SURF_CONCRETE, ["objectid", "plazaname"], stats["sources"], "ped_plaza")
    if inputs.has("plan_parking_lot"):
        _add_polygon_source(acc, inputs["plan_parking_lot"], S.PAV_PARKING_LOT, S.SURF_ASPHALT, ["feat_code", "source_id"], stats["sources"], "parking_lot")

    # curb lines -> curb-face polygons
    if inputs.has("plan_curb"):
        ts = time.time()
        gdf = _read(inputs["plan_curb"], ["feat_code", "source_id"])
        parts, src = _explode(gdf)
        src_id = gdf["source_id"].fillna("").astype(str).to_numpy()[src]
        feat = pd.to_numeric(gdf["feat_code"], errors="coerce").fillna(0).astype(np.int32).to_numpy()[src]
        buf = shapely.buffer(parts, CURB_WIDTH_M / 2.0, quad_segs=1, cap_style="flat", join_style="mitre")
        buf = shapely.make_valid(buf)
        g, at, tx, ty = _clip_to_tiles(buf, {"src_id": src_id, "feat": feat})
        acc.add(g, S.PAV_CURB, np.full(len(g), S.SURF_CONCRETE, dtype=np.int8), at["src_id"], at["feat"], PAV_SRC_PLANIMETRIC, tx, ty)
        stats["sources"]["curb"] = {"features": int(len(gdf)), "parts": int(len(parts)), "tile_pieces": int(len(g)),
                                    "buffer_m": CURB_WIDTH_M, "seconds": round(time.time() - ts, 1)}
        log.info("curb: %d features -> %d tile pieces (%.1fs)", len(gdf), len(g), time.time() - ts)
        del gdf, parts, buf, g

    # crosswalks derived from the real controlled intersections
    ts = time.time()
    xw, xw_ids = _crosswalks(nodes, approaches)
    n_xw_pieces = 0
    if len(xw):
        gx, at, tx, ty = _clip_to_tiles(xw, {"src_id": xw_ids, "feat": np.zeros(len(xw), dtype=np.int32)})
        acc.add(gx, S.PAV_CROSSWALK, np.full(len(gx), S.SURF_ASPHALT, dtype=np.int8), at["src_id"], at["feat"], PAV_SRC_DERIVED, tx, ty)
        n_xw_pieces = int(len(gx))
    stats["sources"]["crosswalk"] = {"features": int(len(xw)), "tile_pieces": n_xw_pieces,
                                     "seconds": round(time.time() - ts, 1)}

    # ---- write ----
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.glob("t_*.parquet"):
        old.unlink()
    written: dict[str, int] = {}
    kind_counts: dict[int, int] = {}
    total_area: dict[int, float] = {}
    for tile in acc.tiles():
        df = pd.concat(acc.parts[tile], ignore_index=True)
        g = shapely.from_wkb(df["geometry"].to_numpy())
        gdf = gpd.GeoDataFrame(df.drop(columns=["geometry"]), geometry=g, crs=NYC_TM)
        n = S.write_geoparquet(gdf, out_dir / f"{tile}.parquet", S.SCHEMAS["pavement"], {"nycsim.tile": tile})
        written[tile] = n
        for k, v in gdf["kind"].value_counts().items():
            kind_counts[int(k)] = kind_counts.get(int(k), 0) + int(v)
        for k, v in gdf.groupby("kind")["area_m2"].sum().items():
            total_area[int(k)] = total_area.get(int(k), 0.0) + float(v)
    stats.update({
        "tiles": len(written), "rows": int(sum(written.values())),
        "rows_by_kind": {int(k): int(v) for k, v in sorted(kind_counts.items())},
        "area_km2_by_kind": {int(k): round(v / 1e6, 3) for k, v in sorted(total_area.items())},
        "seconds": round(time.time() - t0, 1),
    })
    log.info("pavement: %d rows across %d tiles in %.1fs", stats["rows"], stats["tiles"], time.time() - t0)
    return stats


def main(argv: list[str] | None = None) -> int:
    """Standalone re-runnable entry point: ``python -m nycsim_pipeline.roads.pavement``.

    Reads the already-written ``segments.parquet``/``nodes.parquet`` so the pavement layer can be rebuilt (or
    built after a ``--no-pavement`` run) without repeating the whole roads stage.
    """
    import argparse
    import json
    import logging as _logging

    import geopandas as _gpd
    import pandas as _pd

    from ..paths import PROCESSED as _PROCESSED
    from . import inputs as inputs_mod
    from .signs import _approach_frames

    ap = argparse.ArgumentParser(description="Build roads/pavement/{tile}.parquet from the planimetric sources")
    ap.add_argument("--roads-dir", type=Path, default=_PROCESSED / "roads")
    ap.add_argument("--out-dir", type=Path, default=None, help="default: <roads-dir>/pavement")
    ap.add_argument("-v", "--verbose", action="store_true")
    a = ap.parse_args(argv)
    _logging.basicConfig(level=_logging.DEBUG if a.verbose else _logging.INFO,
                         format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    out_dir = a.out_dir or (a.roads_dir / "pavement")
    seg = _gpd.read_parquet(a.roads_dir / "segments.parquet")
    nodes = _pd.read_parquet(a.roads_dir / "nodes.parquet")
    approaches = _approach_frames(seg)
    st = build(inputs_mod.resolve(), seg, nodes, approaches, out_dir)
    with open(a.roads_dir / "pavement_summary.json", "w") as f:
        json.dump(st, f, indent=1)
    print(json.dumps(st, indent=1))
    return 0


if __name__ == "__main__":
    import sys as _sys
    _sys.exit(main())
