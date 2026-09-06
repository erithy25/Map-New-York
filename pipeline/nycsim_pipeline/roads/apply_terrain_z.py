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

Rows whose position falls on a tile with no terrain file, or on a NODATA sample, keep the level-code height and
are counted in the summary. The stage is idempotent: it stores the ground height it applied in the
``ground_z`` columns, so running it again after the terrain stage is re-run simply re-lifts from the new
terrain rather than accumulating offsets.
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
from PIL import Image

from .. import manifest
from ..crs import TILE_SIZE_M
from ..paths import PROCESSED
from . import schema as S

log = logging.getLogger("nycsim.roads.apply_terrain_z")

SAMPLES = 501
SPACING_M = 2.0


class TerrainSampler:
    """Bilinear sampler over the per-tile 16-bit terrain rasters, loaded lazily and cached."""

    def __init__(self, tiles_dir: Path) -> None:
        self.tiles_dir = Path(tiles_dir)
        self._cache: dict[str, tuple[np.ndarray, float, float, float, float] | None] = {}
        self.available: set[str] = set()
        if self.tiles_dir.exists():
            self.available = {p.parent.name for p in self.tiles_dir.glob("t_*/terrain.png")}

    def _tile(self, name: str):
        if name in self._cache:
            return self._cache[name]
        png = self.tiles_dir / name / "terrain.png"
        js = self.tiles_dir / name / "terrain.json"
        if not png.exists() or not js.exists():
            self._cache[name] = None
            return None
        doc = json.loads(js.read_text())
        arr = np.asarray(Image.open(png)).astype(np.float64)
        if arr.shape != (int(doc.get("samples", SAMPLES)), int(doc.get("samples", SAMPLES))):
            log.warning("%s: terrain.png is %s, expected %d square — skipped", name, arr.shape, doc.get("samples", SAMPLES))
            self._cache[name] = None
            return None
        z = float(doc["z_min_m"]) + arr * float(doc["z_scale_m"])
        entry = (z, float(doc.get("x0", 0.0)), float(doc.get("y0", 0.0)), float(doc.get("spacing_m", SPACING_M)),
                 float(doc.get("samples", SAMPLES)))
        self._cache[name] = entry
        return entry

    def sample(self, x: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Return (z, ok). ``ok`` is False where the tile has no terrain file."""
        x = np.asarray(x, dtype=np.float64)
        y = np.asarray(y, dtype=np.float64)
        z = np.zeros(len(x))
        ok = np.zeros(len(x), dtype=bool)
        tx = np.floor(x / TILE_SIZE_M).astype(np.int64)
        ty = np.floor(y / TILE_SIZE_M).astype(np.int64)
        key = tx.astype(np.int64) * 100_000 + ty
        for k in np.unique(key):
            sel = np.flatnonzero(key == k)
            name = f"t_{int(tx[sel[0]])}_{int(ty[sel[0]])}"
            entry = self._tile(name)
            if entry is None:
                continue
            grid, x0, y0, spacing, samples = entry
            n = int(samples)
            cx = (x[sel] - x0) / spacing
            cy = (y0 + TILE_SIZE_M - y[sel]) / spacing
            cx = np.clip(cx, 0.0, n - 1.0000001)
            cy = np.clip(cy, 0.0, n - 1.0000001)
            i0 = cx.astype(np.int64)
            j0 = cy.astype(np.int64)
            fx = cx - i0
            fy = cy - j0
            i1 = np.minimum(i0 + 1, n - 1)
            j1 = np.minimum(j0 + 1, n - 1)
            v = (grid[j0, i0] * (1 - fx) * (1 - fy) + grid[j0, i1] * fx * (1 - fy)
                 + grid[j1, i0] * (1 - fx) * fy + grid[j1, i1] * fx * fy)
            z[sel] = v
            ok[sel] = True
        return z, ok


def _lift_lines(geoms: np.ndarray, z_source: np.ndarray, sampler: TerrainSampler) -> tuple[np.ndarray, dict]:
    """Rewrite the z of every vertex. Returns (new geometries, stats)."""
    coords = shapely.get_coordinates(geoms, include_z=True)
    n_per = shapely.get_num_coordinates(geoms)
    starts = np.concatenate([[0], np.cumsum(n_per)[:-1]])
    row_of = np.repeat(np.arange(len(geoms)), n_per)
    ground, ok = sampler.sample(coords[:, 0], coords[:, 1])

    at_grade = z_source[row_of] == S.Z_AT_GRADE
    offset = coords[:, 2]                       # level-code height above nominal ground
    new_z = coords[:, 2].copy()

    # at grade: follow the terrain exactly
    m = at_grade & ok
    new_z[m] = ground[m]

    # elevated/depressed: straight deck between lifted ends
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
            z_a = ground[a] + offset[a]
            z_b = ground[b] + offset[b]
            new_z[seg] = z_a * (1 - frac) + z_b * frac
            n_struct_lifted += 1

    out = shapely.linestrings(np.column_stack([coords[:, 0], coords[:, 1], new_z]), indices=row_of)
    stats = {
        "vertices": int(len(coords)),
        "vertices_with_terrain": int(ok.sum()),
        "at_grade_vertices_lifted": int(m.sum()),
        "structure_rows_lifted": int(n_struct_lifted),
        "structure_rows": int(len(struct_rows)),
        "mean_ground_z_m": round(float(ground[ok].mean()), 3) if ok.any() else 0.0,
        "max_ground_z_m": round(float(ground[ok].max()), 3) if ok.any() else 0.0,
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
    geoms, st = _lift_lines(seg.geometry.values, seg["z_source"].to_numpy(), sampler)
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
    lane_geoms, lst = _lift_lines(lanes.geometry.values, lane_zsrc, sampler)
    lanes = lanes.set_geometry(gpd.GeoSeries(lane_geoms, index=lanes.index, crs=lanes.crs))
    summary["lanes"] = lst

    jl_path = roads_dir / "junction_lanes.parquet"
    jl = gpd.read_parquet(jl_path)
    jl_zsrc = seg_zsrc.reindex(jl["from_segment"].to_numpy()).fillna(S.Z_AT_GRADE).to_numpy() if "from_segment" in jl.columns \
        else np.zeros(len(jl))
    jl_geoms, jst = _lift_lines(jl.geometry.values, jl_zsrc, sampler)
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
