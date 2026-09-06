"""Re-runnable stage that lifts the road network onto the real terrain.

    python -m nycsim_pipeline.roads.apply_terrain_z [--roads-dir DIR] [--tiles-dir DIR] [--dry-run]

The roads stage produces z from the CSCL/LION grade-separation level codes alone: an at-grade segment gets
z = 0 and an elevated one gets its level offset above *nominal* ground. That is correct relative geometry but
sits on a flat city. This stage samples ``data/processed/tiles/{tile}/terrain.png`` (DATA_CONTRACTS §3:
16-bit, 501x501, 2 m spacing, north row first, ``z = z_min_m + value * z_scale_m``) and rewrites the absolute
heights:

* at-grade segments (``z_source = 0``): every vertex is set to the bilinearly interpolated terrain height;
* elevated / depressed segments (level codes, ``z_source = 1|2``): the deck is kept straight — the two end
  heights become terrain(end) + level offset and the interior is interpolated along chainage, so a bridge
  stays flat over the water instead of following the riverbed;
* nodes, lanes and junction lanes are lifted the same way, keeping lane geometry consistent with its segment;
* signs keep their mounting height above the new ground (``sign.z - sign.ground_z`` is preserved).

Rows whose position falls on a tile with no terrain file keep the level-code height and are counted in the
summary. The stage is idempotent: the grade-separation offset is recomputed from the immutable ``level_from`` /
``level_to`` codes (and, for signs, the mounting height from ``z - ground_z``) rather than read back out of the
geometry, so running it again after the terrain stage is re-run re-lifts from the new terrain instead of
accumulating offsets.

Re-export the §15 runtime binaries afterwards (``python -m nycsim_pipeline.runtime.export``): they carry a copy
of the vertex heights.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path

from collections import OrderedDict

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely
from PIL import Image

from .. import manifest
from ..crs import TILE_SIZE_M
from ..paths import PROCESSED
from . import schema as S

log = logging.getLogger("nycsim.roads.apply_terrain_z")

SAMPLES = 501
SPACING_M = 2.0
MAX_CACHED_TILES = 256          # ~0.5 MB per uint16 raster -> ~130 MB ceiling


class TerrainSampler:
    """Bilinear sampler over the per-tile 16-bit terrain rasters.

    Rasters are held as their published ``uint16`` codes (0.5 MB per tile) and converted to metres only for the
    four corners a sample actually touches, and the cache is capped at ``MAX_CACHED_TILES`` with FIFO eviction,
    so sampling the whole city (2,300+ tiles) costs ~130 MB rather than several gigabytes.
    """

    def __init__(self, tiles_dir: Path, max_cached: int = MAX_CACHED_TILES) -> None:
        self.tiles_dir = Path(tiles_dir)
        self._cache: "OrderedDict[str, tuple | None]" = OrderedDict()
        self._max_cached = max_cached
        self.tiles_loaded = 0
        self.available: set[str] = set()
        if self.tiles_dir.exists():
            self.available = {p.parent.name for p in self.tiles_dir.glob("t_*/terrain.png")}

    def _tile(self, name: str):
        if name in self._cache:
            self._cache.move_to_end(name)
            return self._cache[name]
        png = self.tiles_dir / name / "terrain.png"
        js = self.tiles_dir / name / "terrain.json"
        entry = None
        if png.exists() and js.exists():
            doc = json.loads(js.read_text())
            n = int(doc.get("samples", SAMPLES))
            arr = np.asarray(Image.open(png))
            if arr.shape != (n, n):
                log.warning("%s: terrain.png is %s, expected %d square - skipped", name, arr.shape, n)
            else:
                entry = (arr, float(doc["z_min_m"]), float(doc["z_scale_m"]), float(doc.get("x0", 0.0)),
                         float(doc.get("y0", 0.0)), float(doc.get("spacing_m", SPACING_M)), n)
                self.tiles_loaded += 1
        self._cache[name] = entry
        while len(self._cache) > self._max_cached:
            self._cache.popitem(last=False)
        return entry

    def sample(self, x: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Return (z, ok). ``ok`` is False where no tile raster covers the point.

        The rasters include both edges of their tile, so a point exactly on a tile's south or west boundary is
        also covered by the neighbour below/left; that fallback is used when the owning tile has no terrain file
        yet, which keeps the seams continuous while the terrain stage is still filling in.
        """
        x = np.asarray(x, dtype=np.float64)
        y = np.asarray(y, dtype=np.float64)
        z = np.zeros(len(x))
        ok = np.zeros(len(x), dtype=bool)
        tx = np.floor(x / TILE_SIZE_M).astype(np.int64)
        ty = np.floor(y / TILE_SIZE_M).astype(np.int64)
        self._sample_into(x, y, tx, ty, z, ok, np.arange(len(x)))
        # boundary fallback for the points the owning tile could not answer
        miss = np.flatnonzero(~ok)
        if len(miss):
            eps = 1e-6
            on_west = (x[miss] / TILE_SIZE_M - tx[miss]) < eps
            on_south = (y[miss] / TILE_SIZE_M - ty[miss]) < eps
            for dx, dy in ((-1, 0), (0, -1), (-1, -1)):
                sel = miss[(on_west if dx else True) & (on_south if dy else True)] if (dx or dy) else miss
                sel = sel[~ok[sel]]
                if len(sel) == 0:
                    continue
                self._sample_into(x, y, tx + dx, ty + dy, z, ok, sel)
        return z, ok

    def _sample_into(self, x: np.ndarray, y: np.ndarray, tx: np.ndarray, ty: np.ndarray,
                     z: np.ndarray, ok: np.ndarray, rows: np.ndarray) -> None:
        key = tx[rows].astype(np.int64) * 100_000 + ty[rows]
        for k in np.unique(key):
            sel = rows[key == k]
            entry = self._tile(f"t_{int(tx[sel[0]])}_{int(ty[sel[0]])}")
            if entry is None:
                continue
            grid, z_min, z_scale, x0, y0, spacing, n = entry
            cx = np.clip((x[sel] - x0) / spacing, 0.0, n - 1.0000001)
            cy = np.clip((y0 + TILE_SIZE_M - y[sel]) / spacing, 0.0, n - 1.0000001)
            i0 = cx.astype(np.int64)
            j0 = cy.astype(np.int64)
            fx = cx - i0
            fy = cy - j0
            i1 = np.minimum(i0 + 1, n - 1)
            j1 = np.minimum(j0 + 1, n - 1)
            v = (grid[j0, i0].astype(np.float64) * (1 - fx) * (1 - fy)
                 + grid[j0, i1].astype(np.float64) * fx * (1 - fy)
                 + grid[j1, i0].astype(np.float64) * (1 - fx) * fy
                 + grid[j1, i1].astype(np.float64) * fx * fy)
            z[sel] = z_min + v * z_scale
            ok[sel] = True


def _lift_lines(geoms: np.ndarray, z_source: np.ndarray, off_a: np.ndarray, off_b: np.ndarray,
                sampler: TerrainSampler) -> tuple[np.ndarray, dict]:
    """Rewrite the z of every vertex from the terrain plus the row's level-code offsets.

    ``off_a``/``off_b`` are the grade-separation offsets (metres above nominal ground) at the first and last
    vertex, recomputed from the immutable ``level_from``/``level_to`` codes rather than read back out of the
    geometry, which is what makes the stage idempotent: running it twice gives the same absolute heights.
    """
    coords = shapely.get_coordinates(geoms, include_z=True)
    n_per = shapely.get_num_coordinates(geoms)
    starts = np.concatenate([[0], np.cumsum(n_per)[:-1]])
    row_of = np.repeat(np.arange(len(geoms)), n_per)
    ground, ok = sampler.sample(coords[:, 0], coords[:, 1])

    new_z = coords[:, 2].copy()
    at_grade = z_source[row_of] == S.Z_AT_GRADE
    m = at_grade & ok
    new_z[m] = ground[m]

    struct_rows = np.flatnonzero(z_source != S.Z_AT_GRADE)
    n_struct_lifted = 0
    if len(struct_rows):
        head = starts[struct_rows]
        tail = starts[struct_rows] + n_per[struct_rows] - 1
        both_ok = ok[head] & ok[tail]
        for r, h, t, good in zip(struct_rows, head, tail, both_ok):
            if not good:
                continue
            a, b = int(h), int(t)
            seg = slice(a, b + 1)
            xy = coords[seg, :2]
            d = np.concatenate([[0.0], np.cumsum(np.hypot(np.diff(xy[:, 0]), np.diff(xy[:, 1])))])
            frac = d / d[-1] if d[-1] > 0 else np.zeros(len(d))
            z_a = ground[a] + float(off_a[r])
            z_b = ground[b] + float(off_b[r])
            new_z[seg] = z_a * (1 - frac) + z_b * frac
            n_struct_lifted += 1

    out = shapely.linestrings(np.column_stack([coords[:, 0], coords[:, 1], new_z]), indices=row_of)
    stats = {
        "rows": int(len(geoms)),
        "vertices": int(len(coords)),
        "vertices_with_terrain": int(ok.sum()),
        "at_grade_vertices_lifted": int(m.sum()),
        "structure_rows": int(len(struct_rows)),
        "structure_rows_lifted": int(n_struct_lifted),
        "mean_ground_z_m": round(float(ground[ok].mean()), 3) if ok.any() else 0.0,
        "max_ground_z_m": round(float(ground[ok].max()), 3) if ok.any() else 0.0,
        "min_ground_z_m": round(float(ground[ok].min()), 3) if ok.any() else 0.0,
    }
    return out, stats


def apply(roads_dir: Path, tiles_dir: Path, dry_run: bool = False) -> dict:
    t0 = time.time()
    sampler = TerrainSampler(tiles_dir)
    summary: dict = {"tiles_with_terrain": len(sampler.available), "tiles_dir": str(tiles_dir),
                     "roads_dir": str(roads_dir), "dry_run": dry_run, "applied": False}
    if not sampler.available:
        summary["note"] = ("no data/processed/tiles/*/terrain.png exists yet; the road network keeps the "
                           "level-code heights. Re-run this stage after the terrain stage.")
        log.warning("%s", summary["note"])
        return summary

    seg_path = roads_dir / "segments.parquet"
    if not seg_path.exists():
        raise FileNotFoundError(seg_path)
    seg = gpd.read_parquet(seg_path)
    seg_off_a = np.asarray(S.level_to_z(seg["level_from"].to_numpy()), dtype=np.float64)
    seg_off_b = np.asarray(S.level_to_z(seg["level_to"].to_numpy()), dtype=np.float64)
    geoms, st = _lift_lines(seg.geometry.values, seg["z_source"].to_numpy(), seg_off_a, seg_off_b, sampler)
    summary["segments"] = st
    ends = shapely.get_coordinates(geoms, include_z=True)
    n_per = shapely.get_num_coordinates(geoms)
    starts = np.concatenate([[0], np.cumsum(n_per)[:-1]])
    seg_z_from = ends[starts, 2]
    seg_z_to = ends[starts + n_per - 1, 2]
    seg = seg.set_geometry(gpd.GeoSeries(geoms, index=seg.index, crs=seg.crs))
    seg["z_from"] = seg_z_from.astype(np.float32)
    seg["z_to"] = seg_z_to.astype(np.float32)
    seg["terrain_applied"] = True

    nodes = pd.read_parquet(roads_dir / "nodes.parquet")
    ends_df = pd.DataFrame({"node_id": np.concatenate([seg["from_node"].to_numpy(), seg["to_node"].to_numpy()]),
                            "z": np.concatenate([seg_z_from, seg_z_to])})
    mean_z = ends_df.groupby("node_id")["z"].mean()
    new_node_z = mean_z.reindex(nodes["node_id"].to_numpy()).to_numpy()
    have = np.isfinite(new_node_z)
    nz = nodes["z"].to_numpy().astype(np.float64).copy()
    nz[have] = new_node_z[have]
    nodes["z"] = nz.astype(np.float32)
    summary["nodes"] = {"nodes": int(len(nodes)), "z_updated": int(have.sum())}

    lanes = gpd.read_parquet(roads_dir / "lanes.parquet")
    seg_zsrc = pd.Series(seg["z_source"].to_numpy(), index=seg["segment_id"].to_numpy())
    lane_zsrc = seg_zsrc.reindex(lanes["segment_id"].to_numpy()).fillna(S.Z_AT_GRADE).to_numpy()
    off_a_by_seg = pd.Series(seg_off_a, index=seg["segment_id"].to_numpy())
    off_b_by_seg = pd.Series(seg_off_b, index=seg["segment_id"].to_numpy())
    lane_off_a = off_a_by_seg.reindex(lanes["segment_id"].to_numpy()).fillna(0.0).to_numpy()
    lane_off_b = off_b_by_seg.reindex(lanes["segment_id"].to_numpy()).fillna(0.0).to_numpy()
    lane_geoms, lst = _lift_lines(lanes.geometry.values, lane_zsrc, lane_off_a, lane_off_b, sampler)
    lanes = lanes.set_geometry(gpd.GeoSeries(lane_geoms, index=lanes.index, crs=lanes.crs))
    summary["lanes"] = lst

    jl_path = roads_dir / "junction_lanes.parquet"
    jl = gpd.read_parquet(jl_path)
    if "from_segment" in jl.columns:
        jl_zsrc = seg_zsrc.reindex(jl["from_segment"].to_numpy()).fillna(S.Z_AT_GRADE).to_numpy()
        # a connector is short: give it one constant deck offset, the mean of its approach segment's two ends
        jl_off = ((off_a_by_seg.reindex(jl["from_segment"].to_numpy()).fillna(0.0).to_numpy()
                   + off_b_by_seg.reindex(jl["from_segment"].to_numpy()).fillna(0.0).to_numpy()) / 2.0)
    else:
        jl_zsrc = np.zeros(len(jl))
        jl_off = np.zeros(len(jl))
    jl_geoms, jst = _lift_lines(jl.geometry.values, jl_zsrc, jl_off, jl_off, sampler)
    jl = jl.set_geometry(gpd.GeoSeries(jl_geoms, index=jl.index, crs=jl.crs))
    summary["junction_lanes"] = jst

    signs = pd.read_parquet(roads_dir / "signs.parquet")
    g_new, s_ok = sampler.sample(signs["x"].to_numpy(), signs["y"].to_numpy())
    mount = signs["z"].to_numpy().astype(np.float64) - signs["ground_z"].to_numpy().astype(np.float64)
    sz = signs["z"].to_numpy().astype(np.float64).copy()
    gz = signs["ground_z"].to_numpy().astype(np.float64).copy()
    sz[s_ok] = g_new[s_ok] + mount[s_ok]
    gz[s_ok] = g_new[s_ok]
    signs["z"] = sz.astype(np.float32)
    signs["ground_z"] = gz.astype(np.float32)
    summary["signs"] = {"signs": int(len(signs)), "z_updated": int(s_ok.sum())}
    summary["terrain_tiles_loaded"] = int(sampler.tiles_loaded)

    if dry_run:
        summary["applied"] = False
        summary["seconds"] = round(time.time() - t0, 1)
        return summary

    S.write_geoparquet(seg, seg_path, S.SCHEMAS["segments"], {"nycsim.terrain_z": "1"})
    S.write_parquet(nodes, roads_dir / "nodes.parquet", S.SCHEMAS["nodes"], {"nycsim.terrain_z": "1"})
    S.write_geoparquet(lanes, roads_dir / "lanes.parquet", S.SCHEMAS["lanes"], {"nycsim.terrain_z": "1"})
    S.write_geoparquet(jl, jl_path, S.SCHEMAS["junction_lanes"], {"nycsim.terrain_z": "1"})
    S.write_parquet(signs, roads_dir / "signs.parquet", S.SCHEMAS["signs"], {"nycsim.terrain_z": "1"})
    summary["applied"] = True
    summary["seconds"] = round(time.time() - t0, 1)
    with open(roads_dir / "terrain_z_summary.json", "w") as f:
        json.dump(summary, f, indent=1)
    if roads_dir == PROCESSED / "roads":
        manifest.record_processed("roads_terrain_z", roads_dir / "terrain_z_summary.json", stage="roads.apply_terrain_z",
                                  sources=["terrain_tiles"], schema="roads.terrain_z/1")
        # the five rewritten artefacts have new checksums
        for aid, name, key in (("roads_segments", "segments.parquet", "segments"), ("roads_nodes", "nodes.parquet", "nodes"),
                               ("roads_lanes", "lanes.parquet", "lanes"), ("roads_junction_lanes", "junction_lanes.parquet", "junction_lanes"),
                               ("roads_signs", "signs.parquet", "signs")):
            manifest.record_processed(aid, roads_dir / name, stage="roads.apply_terrain_z", sources=["terrain_tiles"],
                                      schema=S.SCHEMAS[key], extra={"terrain_z": True})
    log.info("terrain z applied in %.1fs", time.time() - t0)
    return summary


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--roads-dir", type=Path, default=PROCESSED / "roads")
    ap.add_argument("--tiles-dir", type=Path, default=PROCESSED / "tiles")
    ap.add_argument("--dry-run", action="store_true", help="compute and report without rewriting the parquet files")
    ap.add_argument("-v", "--verbose", action="store_true")
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if a.verbose else logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    out = apply(a.roads_dir, a.tiles_dir, a.dry_run)
    print(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
