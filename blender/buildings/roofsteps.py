"""Recover real stepped-roof outlines from the CityGML LOD2 triangles (no ``bpy``).

ADR-013 established that the NYC 3-D Building Model carries **flat multi-level massing**, not roof
pitch: `roof_level_z` / `roof_level_area` in `buildings/roof_attrs.parquet` say *how high* and *how
big* each roof level is, but not *where* it is.  The outlines are recoverable, because
`data/processed/buildings/citygml/da*.parquet` publishes the LOD2 triangle soup per building:

* ``tri_xyz``  — float32, ``(n, 3, 3)``, NYC_TM metres, z in NAVD88 metres.
* ``tri_type`` — uint8 per triangle: **0 = ground, 1 = wall, 2 = roof** (verified against the
  ``n_ground`` / ``n_wall`` / ``n_roof`` counts and the face normals: type 0 and 2 are exactly
  horizontal, type 1 exactly vertical).

Every roof triangle is horizontal, so its 2-D projection *is* the level outline.  Grouping the roof
triangles by height and unioning each group gives the real per-level polygon, which this module then
checks against the published `roof_level_area` before anything is built from it.

Nothing here guesses.  A building whose recovered outlines do not reproduce the published areas, or
whose levels do not tile its footprint, is rejected and falls back to the single-height shell.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import shapely
from shapely.geometry import Polygon

LOG = logging.getLogger("nycsim.buildings.roofsteps")

REPO_ROOT = Path(__file__).resolve().parents[2]
CITYGML_DIR = REPO_ROOT / "data" / "processed" / "buildings" / "citygml"
INDEX_PATH = Path(__file__).resolve().parent / "citygml_tile_index.json"

TRI_GROUND, TRI_WALL, TRI_ROOF = 0, 1, 2

Z_CLUSTER_TOL_M = 0.15        # roof faces within this height belong to one level
MIN_LEVEL_AREA_M2 = 4.0       # a level smaller than this is not a step, it is a bulkhead detail
MIN_STEP_H_M = 1.0            # a step shallower than this is not worth the triangles
AREA_TOL_REL = 0.02           # published vs recovered level area (the 2 % measured in the report)
AREA_TOL_ABS_M2 = 1.5
MAX_LEFTOVER_FRAC = 0.25      # footprint not covered by any recovered level
MAX_LEVELS = 8


@dataclass
class StepSet:
    """Recovered levels for one building, in NYC_TM metres."""

    bin: int
    levels: list[tuple[float, Polygon]]        # (z of the level, outline), ascending z
    z_roof_max: float
    reason: str = "ok"                          # why it was rejected, when levels is empty

    @property
    def ok(self) -> bool:
        return len(self.levels) >= 2


# --------------------------------------------------------------------------- level recovery
def recover_levels(tri_xyz: bytes, tri_type: bytes, *, z_tol: float = Z_CLUSTER_TOL_M,
                   min_area: float = MIN_LEVEL_AREA_M2) -> list[tuple[float, Polygon]]:
    """Group the roof triangles by height and union each group into a level outline."""
    if not tri_xyz or not tri_type:
        return []
    tri = np.frombuffer(tri_xyz, dtype=np.float32).reshape(-1, 3, 3)
    typ = np.frombuffer(tri_type, dtype=np.uint8)
    if len(typ) != len(tri):
        return []
    roof = tri[typ == TRI_ROOF]
    if len(roof) == 0:
        return []
    z = roof[:, :, 2].mean(axis=1).astype(np.float64)
    order = np.argsort(z)
    zs = z[order]
    cuts = np.nonzero(np.diff(zs) > z_tol)[0] + 1
    out: list[tuple[float, Polygon]] = []
    for grp in np.split(order, cuts):
        if len(grp) == 0:
            continue
        polys = []
        for i in grp:
            p = Polygon(roof[i][:, :2].astype(np.float64))
            if p.is_valid and p.area > 1e-9:
                polys.append(p)
        if not polys:
            continue
        try:
            merged = shapely.union_all(polys).buffer(0)
        except Exception:
            continue
        parts = [q for q in _iter_polygons(merged) if q.area >= min_area]
        if not parts:
            continue
        out.append((float(z[grp].mean()), shapely.union_all(parts)))
    out.sort(key=lambda t: t[0])
    return out


def _iter_polygons(geom):
    t = geom.geom_type
    if t == "Polygon":
        if not geom.is_empty:
            yield geom
    elif t in ("MultiPolygon", "GeometryCollection"):
        for sub in geom.geoms:
            yield from _iter_polygons(sub)


def check_against_published(levels: list[tuple[float, Polygon]], pub_z, pub_area,
                            footprint_area: float | None) -> tuple[bool, str, bool]:
    """Validate the recovered outlines against what the CityGML stage published.

    Returns ``(accept, reason, strict_per_level_match)``.

    The gate is that the recovered levels **tile the building**: their areas must sum to the
    CityGML ground footprint area within ``AREA_TOL_REL``.  That is the comparable quantity —
    measured over the 623 multi-level buildings of the Midtown tile, recovered-sum / footprint-area
    has median 1.0000 and recovered-sum / published-sum has median 1.0000, so the totals agree
    exactly, while a *per-level* comparison disagrees for 17 % of buildings purely because the
    height clustering here (0.15 m) splits or merges levels differently from the publishing stage.
    A building whose levels overlap in plan (sum > footprint) or leave a hole (sum < footprint)
    fails and falls back to the flat cap; nothing is guessed.  ``strict_per_level_match`` reports
    whether the stricter level-by-level comparison would also have passed, for the record.
    """
    if len(levels) < 2:
        return False, "fewer than two levels recovered", False
    rec_total = float(sum(p.area for _, p in levels))
    if footprint_area and footprint_area > 0:
        rel = abs(rec_total / float(footprint_area) - 1.0)
        if rel > AREA_TOL_REL and abs(rec_total - float(footprint_area)) > AREA_TOL_ABS_M2:
            return False, f"levels sum to {rec_total:.1f} m2 vs footprint {footprint_area:.1f} m2", False
    if pub_area is not None:
        pa = np.asarray(pub_area, dtype=np.float64)
        pub_total = float(pa.sum())
        if pub_total > 0:
            rel = abs(rec_total / pub_total - 1.0)
            if rel > AREA_TOL_REL and abs(rec_total - pub_total) > AREA_TOL_ABS_M2:
                return False, f"levels sum to {rec_total:.1f} m2 vs published {pub_total:.1f} m2", False

    strict = False
    if pub_z is not None and pub_area is not None:
        pz = np.asarray(pub_z, dtype=np.float64)
        pa = np.asarray(pub_area, dtype=np.float64)
        if len(pz) == len(pa):
            keep = pa >= MIN_LEVEL_AREA_M2
            pz, pa = pz[keep], pa[keep]
            if len(pz) == len(levels):
                idx = np.argsort(pz)
                strict = all(
                    abs(rz - pz[j]) <= 0.5
                    and abs(poly.area - pa[j]) <= max(AREA_TOL_ABS_M2, AREA_TOL_REL * pa[j])
                    for (rz, poly), j in zip(levels, idx))
    return True, "ok", strict


# --------------------------------------------------------------------------- footprint partition
def partition_footprint(footprint: Polygon, levels: list[tuple[float, Polygon]], *,
                        weld: float = 1e-3) -> tuple[list[tuple[Polygon, float]], str]:
    """Cut the *real OTI footprint* into one region per recovered level.

    The shell's plan stays the real 2026 footprint; the 2014 CityGML levels only say which part of
    it is lower.  The largest region is computed last, as ``footprint − union(others)``, so the
    regions tile the footprint exactly and adjacent regions share bit-identical boundaries — which
    is what lets the step faces weld to the level caps.
    """
    if len(levels) < 2:
        return [], "fewer than two levels"
    area = footprint.area
    if area <= 0:
        return [], "empty footprint"
    order = sorted(range(len(levels)), key=lambda i: -levels[i][1].area)
    main = order[0]

    taken = None
    others: list[tuple[Polygon, float]] = []
    for i in sorted(range(len(levels)), key=lambda i: -levels[i][0]):
        if i == main:
            continue
        z, poly = levels[i]
        try:
            r = footprint.intersection(poly)
            if taken is not None:
                r = r.difference(taken)
            r = shapely.set_precision(r, weld, mode="valid_output")
        except Exception:
            continue
        parts = [p for p in _iter_polygons(r) if p.area >= MIN_LEVEL_AREA_M2]
        if not parts:
            continue
        reg = shapely.union_all(parts)
        others.append((reg, z))
        taken = reg if taken is None else shapely.union_all([taken, reg])

    if not others:
        return [], "no secondary level survives the footprint intersection"
    try:
        main_region = footprint.difference(taken)
        main_region = shapely.set_precision(main_region, weld, mode="valid_output")
    except Exception:
        return [], "main region difference failed"
    main_parts = [p for p in _iter_polygons(main_region) if p.area >= MIN_LEVEL_AREA_M2]
    if not main_parts:
        return [], "main region vanished"
    main_poly = shapely.union_all(main_parts)

    regions = [(main_poly, levels[main][0])] + others
    covered = sum(p.area for p, _ in regions)
    if covered < (1.0 - MAX_LEFTOVER_FRAC) * area:
        return [], f"regions cover only {covered / area:.2f} of the footprint"
    zs = [z for _, z in regions]
    if max(zs) - min(zs) < MIN_STEP_H_M:
        return [], f"step of {max(zs) - min(zs):.2f} m is below the {MIN_STEP_H_M} m threshold"
    if len(regions) > MAX_LEVELS:
        return [], f"{len(regions)} levels exceeds the {MAX_LEVELS} cap"
    return regions, "ok"


# --------------------------------------------------------------------------- per-tile source access
def build_tile_index(force: bool = False) -> dict[str, list[list[int]]]:
    """Map each ``da*.parquet`` to the tiles it contains, so a tile opens one file, not twenty."""
    if INDEX_PATH.exists() and not force:
        try:
            return json.loads(INDEX_PATH.read_text())["files"]
        except Exception:
            pass
    import pyarrow.parquet as pq

    files: dict[str, list[list[int]]] = {}
    for p in sorted(CITYGML_DIR.glob("da*.parquet")):
        try:
            t = pq.read_table(p, columns=["tx", "ty"])
        except Exception as exc:
            LOG.warning("cannot index %s: %s", p, exc)
            continue
        tx = np.asarray(t.column("tx"))
        ty = np.asarray(t.column("ty"))
        pairs = np.unique(np.column_stack([tx, ty]), axis=0)
        files[p.name] = [[int(a), int(b)] for a, b in pairs]
    INDEX_PATH.write_text(json.dumps({"schema_version": 1, "files": files}, indent=1, sort_keys=True))
    LOG.info("citygml tile index written: %d files", len(files))
    return files


_INDEX: dict[tuple[int, int], list[str]] | None = None


def _files_for(tx: int, ty: int) -> list[str]:
    global _INDEX
    if _INDEX is None:
        _INDEX = {}
        for fname, pairs in build_tile_index().items():
            for a, b in pairs:
                _INDEX.setdefault((a, b), []).append(fname)
    return _INDEX.get((tx, ty), [])


def load_tile_steps(tile: str, *, min_levels: int = 2) -> tuple[dict[int, StepSet], dict[str, int]]:
    """Recovered level outlines for every multi-level building in a tile, keyed by BIN."""
    import pyarrow.compute as pc
    import pyarrow.parquet as pq

    tx, ty = (int(v) for v in tile[2:].split("_", 1))
    stats = {"rows": 0, "candidates": 0, "recovered": 0, "rejected_area": 0, "rejected_geom": 0,
             "strict_per_level_match": 0}
    out: dict[int, StepSet] = {}
    for fname in _files_for(tx, ty):
        path = CITYGML_DIR / fname
        if not path.exists():
            continue
        cols = ["bin", "tri_xyz", "tri_type", "roof_level_z", "roof_level_area",
                "n_roof_levels", "z_roof_max", "footprint_area_m2"]
        try:
            tb = pq.read_table(path, columns=cols,
                              filters=[("tx", "=", tx), ("ty", "=", ty)])
        except Exception as exc:
            LOG.warning("cannot read %s for %s: %s", path, tile, exc)
            continue
        _ = pc
        stats["rows"] += tb.num_rows
        bins = tb.column("bin").to_pylist()
        nlev = tb.column("n_roof_levels").to_pylist()
        zmax = tb.column("z_roof_max").to_pylist()
        xyz = tb.column("tri_xyz").to_pylist()
        typ = tb.column("tri_type").to_pylist()
        lz = tb.column("roof_level_z").to_pylist()
        la = tb.column("roof_level_area").to_pylist()
        fa = tb.column("footprint_area_m2").to_pylist()
        for i, b in enumerate(bins):
            if (nlev[i] or 0) < min_levels:
                continue
            stats["candidates"] += 1
            levels = recover_levels(xyz[i], typ[i])
            if len(levels) < min_levels:
                stats["rejected_geom"] += 1
                out[int(b)] = StepSet(int(b), [], float(zmax[i] or 0.0), "too few levels recovered")
                continue
            ok, why, strict = check_against_published(levels, lz[i], la[i], fa[i])
            if not ok:
                stats["rejected_area"] += 1
                out[int(b)] = StepSet(int(b), [], float(zmax[i] or 0.0), why)
                continue
            stats["recovered"] += 1
            stats["strict_per_level_match"] += int(strict)
            out[int(b)] = StepSet(int(b), levels, float(zmax[i] or levels[-1][0]), "ok")
    return out, stats
