"""Tests for landmark agent A's hand-scripted models (blender/landmarks/*.py, agent A set).

For each landmark: the .glb exists and parses; it carries the NYCSim asset extras; a node named ``<id>_LOD1`` exists with
<= 20 % of the LOD0 triangles; the model height matches the documented height within 1 %; the horizontal section of the
base-tagged nodes at z = 1.5 m has IoU > 0.9 with the real footprint(s) (from the landmark footprint parquet).

Runs without bpy: the glb is decoded with pygltflib + numpy. Skips (does not fail) when the outputs have not been built.
"""
from __future__ import annotations

import json
import math
import struct
from pathlib import Path

import numpy as np
import pytest

REPO = Path(__file__).resolve().parents[1]
GLB_DIR = REPO / "blender_out" / "landmarks"
CATALOG = GLB_DIR / "catalog"
CANDIDATES = REPO / "data" / "processed" / "landmarks" / "candidate_footprints.parquet"
RAW = REPO / "data" / "processed" / "buildings" / "footprints_raw.parquet"

LANDMARKS_A = [
    "empire_state", "chrysler", "flatiron", "one_vanderbilt", "30_rockefeller_plaza", "st_patricks_cathedral",
    "grand_central_terminal", "new_york_public_library", "madison_square_garden", "woolworth", "municipal_building",
    "city_hall", "trinity_church", "nyse", "charging_bull", "federal_hall", "40_wall_street", "one_wall_street",
    "equitable_building", "moma",
]
NO_FOOTPRINT = {"charging_bull"}   # sculpture: placed by coordinates, no building footprint

pygltflib = pytest.importorskip("pygltflib")

_COMPONENT = {5120: ("b", 1), 5121: ("B", 1), 5122: ("h", 2), 5123: ("H", 2), 5125: ("I", 4), 5126: ("f", 4)}
_COUNT = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}


class Glb:
    """Minimal glTF 2.0 binary decoder (positions + indices + node graph)."""

    def __init__(self, path: Path):
        self.g = pygltflib.GLTF2().load(str(path))
        self.blob = self.g.binary_blob()

    def accessor(self, idx: int) -> np.ndarray:
        acc = self.g.accessors[idx]
        bv = self.g.bufferViews[acc.bufferView]
        fmt, size = _COMPONENT[acc.componentType]
        n = _COUNT[acc.type]
        start = (bv.byteOffset or 0) + (acc.byteOffset or 0)
        stride = bv.byteStride or size * n
        out = np.empty((acc.count, n), dtype=np.dtype(fmt))
        for i in range(acc.count):
            off = start + i * stride
            out[i] = struct.unpack_from("<" + fmt * n, self.blob, off)
        return out

    def node_world_matrices(self) -> dict[int, np.ndarray]:
        parents = {}
        for i, n in enumerate(self.g.nodes):
            for c in n.children or []:
                parents[c] = i

        def local(n):
            if n.matrix:
                return np.array(n.matrix, dtype=np.float64).reshape(4, 4).T
            m = np.eye(4)
            t = np.array(n.translation or [0, 0, 0]); q = np.array(n.rotation or [0, 0, 0, 1]); s = np.array(n.scale or [1, 1, 1])
            x, y, z, w = q
            R = np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                          [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                          [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])
            m[:3, :3] = R @ np.diag(s); m[:3, 3] = t
            return m
        cache: dict[int, np.ndarray] = {}

        def world(i):
            if i in cache:
                return cache[i]
            m = local(self.g.nodes[i])
            if i in parents:
                m = world(parents[i]) @ m
            cache[i] = m
            return m
        return {i: world(i) for i in range(len(self.g.nodes))}

    def triangles(self, node_filter=None):
        """(N,3,3) triangles in *Blender* coordinates (x east, y north, z up) for nodes passing node_filter(node)."""
        mats = self.node_world_matrices()
        tris = []
        for i, n in enumerate(self.g.nodes):
            if n.mesh is None or (node_filter and not node_filter(n)):
                continue
            m = mats[i]
            for prim in self.g.meshes[n.mesh].primitives:
                pos = self.accessor(prim.attributes.POSITION).astype(np.float64)
                pos = (m[:3, :3] @ pos.T).T + m[:3, 3]
                # glTF Y-up -> Blender Z-up: (x, y, z)_gltf = (x, z, -y)_blender  =>  blender = (x, -z, y)
                pos = np.stack([pos[:, 0], -pos[:, 2], pos[:, 1]], axis=1)
                if prim.indices is not None:
                    idx = self.accessor(prim.indices).reshape(-1).astype(np.int64)
                else:
                    idx = np.arange(len(pos))
                tris.append(pos[idx.reshape(-1, 3)])
        return np.concatenate(tris) if tris else np.zeros((0, 3, 3))


def _section(tris: np.ndarray, z: float):
    import shapely
    import shapely.ops
    from shapely.geometry import MultiLineString, Polygon
    import functools
    zmin = tris[:, :, 2].min(axis=1); zmax = tris[:, :, 2].max(axis=1)
    segs = []
    for a, b, c in tris[(zmin < z) & (zmax > z)]:
        pts = []
        for u, v in ((a, b), (b, c), (c, a)):
            if (u[2] - z) * (v[2] - z) < 0:
                s = (z - u[2]) / (v[2] - u[2])
                pts.append((round(float(u[0] + s * (v[0] - u[0])), 4), round(float(u[1] + s * (v[1] - u[1])), 4)))
        if len(pts) == 2 and pts[0] != pts[1]:
            segs.append(pts)
    if not segs:
        return Polygon()
    merged = shapely.ops.linemerge(shapely.ops.unary_union(MultiLineString(segs)))
    lines = list(merged.geoms) if hasattr(merged, "geoms") else [merged]
    polys = []
    for ln in lines:
        cs = list(ln.coords)
        if len(cs) < 4:
            continue
        if cs[0] != cs[-1]:
            if math.dist(cs[0], cs[-1]) < 0.02:
                cs.append(cs[0])
            else:
                continue
        pg = Polygon(cs)
        if not pg.is_valid:
            pg = pg.buffer(0)
        if pg.area > 1e-6:
            polys.append(pg)
    if not polys:
        return Polygon()
    return functools.reduce(lambda a, b: a.symmetric_difference(b), polys)


def _real_footprint_local(bins, origin_xy):
    import pyarrow.parquet as pq
    import shapely
    import shapely.ops
    from shapely import wkb
    from shapely.geometry import Polygon
    polys = []
    for path in (CANDIDATES, RAW):
        if not path.exists():
            continue
        t = pq.read_table(path, columns=["bin", "geometry"], filters=[("bin", "in", [int(b) for b in bins])])
        for r in t.to_pylist():
            g = wkb.loads(r["geometry"])
            if not g.is_valid:
                g = g.buffer(0)
            polys.append((int(r["bin"]), g))
        if {b for b, _ in polys} >= set(int(b) for b in bins):
            break
    assert {b for b, _ in polys} >= set(int(b) for b in bins), f"footprints missing for {bins}"
    u = shapely.ops.unary_union([g for _, g in polys])
    return shapely.affinity.translate(u, -origin_xy[0], -origin_xy[1])


@pytest.fixture(scope="module")
def built_ids():
    ids = [i for i in LANDMARKS_A if (GLB_DIR / f"{i}.glb").exists() and (CATALOG / f"{i}.json").exists()]
    if not ids:
        pytest.skip("landmark glbs not built (run blender/landmarks/*.py)")
    return ids


def _load(lid):
    glb = Glb(GLB_DIR / f"{lid}.glb")
    cat = json.loads((CATALOG / f"{lid}.json").read_text())
    return glb, cat


@pytest.mark.parametrize("lid", LANDMARKS_A)
def test_glb_exists_and_loads(lid, built_ids):
    if lid not in built_ids:
        pytest.skip(f"{lid} not built")
    glb, cat = _load(lid)
    # nycsim_bpy.export_glb stores the metadata as a scene custom property -> glTF scenes[0].extras.nycsim (JSON string)
    ex = glb.g.asset.extras or {}
    if "nycsim" not in ex and glb.g.scenes and glb.g.scenes[0].extras and "nycsim" in glb.g.scenes[0].extras:
        ex = glb.g.scenes[0].extras["nycsim"]
        ex = json.loads(ex) if isinstance(ex, str) else ex
    elif "nycsim" in ex:
        ex = ex["nycsim"]
        ex = json.loads(ex) if isinstance(ex, str) else ex
    assert ex.get("schema_version") == 1
    assert ex.get("landmark_id") == lid
    assert len(ex.get("origin_tm", [])) == 3
    assert ex.get("fidelity_statement")
    assert cat["id"] == lid and cat["glb"].endswith(f"{lid}.glb")
    assert glb.triangles().shape[0] > 0


@pytest.mark.parametrize("lid", LANDMARKS_A)
def test_lod1_present_and_within_budget(lid, built_ids):
    if lid not in built_ids:
        pytest.skip(f"{lid} not built")
    glb, cat = _load(lid)
    names = [n.name for n in glb.g.nodes]
    assert f"{lid}_LOD1" in names, names
    lod1 = glb.triangles(lambda n: n.name == f"{lid}_LOD1")
    lod0 = glb.triangles(lambda n: n.name != f"{lid}_LOD1" and n.mesh is not None)
    assert lod1.shape[0] > 0
    assert lod1.shape[0] <= 0.2 * lod0.shape[0], (lod1.shape[0], lod0.shape[0])
    budget = 600_000 if lid in ("empire_state", "chrysler", "grand_central_terminal") else 250_000
    assert lod0.shape[0] <= budget


@pytest.mark.parametrize("lid", LANDMARKS_A)
def test_height_within_one_percent(lid, built_ids):
    if lid not in built_ids:
        pytest.skip(f"{lid} not built")
    glb, cat = _load(lid)
    lod0 = glb.triangles(lambda n: n.name != f"{lid}_LOD1" and n.mesh is not None)
    top = float(lod0[:, :, 2].max())
    assert abs(top - cat["height_m"]) <= 0.01 * cat["height_m"], (top, cat["height_m"])
    assert lod0[:, :, 2].min() > -80.0  # nothing absurdly below grade (GCT/MSG have real sub-grade levels)


@pytest.mark.parametrize("lid", LANDMARKS_A)
def test_footprint_iou(lid, built_ids):
    if lid not in built_ids:
        pytest.skip(f"{lid} not built")
    glb, cat = _load(lid)
    if lid in NO_FOOTPRINT:
        assert not cat["bins"]
        assert "no building footprint" in cat["fidelity_statement"].lower() or cat.get("footprint_iou") is None
        return
    base = glb.triangles(lambda n: (n.extras or {}).get("nycsim_role") == "base")
    assert base.shape[0] > 0, "no base-tagged nodes in glb"
    sec = _section(base, 1.5)
    real = _real_footprint_local(cat["bins"], cat["origin_tm"][:2])
    inter = sec.intersection(real).area
    union = sec.union(real).area
    iou = inter / union if union else 0.0
    assert iou > 0.9, f"IoU {iou:.3f} (section {sec.area:.0f} m2 vs real {real.area:.0f} m2)"
    assert abs(iou - cat["footprint_iou"]) < 0.05
