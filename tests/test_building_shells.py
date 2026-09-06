"""Verification tests for the building-shell stage (`blender/buildings/`).

Checks, on real generated output for a real NYC tile:

* the ``.glb`` loads with ``pygltflib`` and has the LOD0/LOD1/LOD2 mesh chain and a bounded
  material list;
* every sampled building is a closed, outward-oriented solid (edge-manifold, positive volume);
* the footprint recovered from the mesh matches the source polygon in
  ``data/processed/tiles/{tile}/buildings.parquet`` with IoU > 0.98;
* the mesh height equals the ``height`` column within 1 cm, and the mesh sits on ``ground_z``;
* the per-building vertex attributes round-trip exactly (including the split ``lit_seed``);
* the pure-geometry layer closes the solid for every roof type on awkward footprints.

Run: ``python3 -m pytest tests/test_building_shells.py -v``
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

import numpy as np
import pytest
import shapely
from shapely.geometry import Polygon

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "blender" / "buildings"))
sys.path.insert(0, str(REPO_ROOT / "blender" / "common"))

import shellgeom as sg  # noqa: E402
import tiledata as td  # noqa: E402

pygltflib = pytest.importorskip("pygltflib")

FIXTURE_TILE = "t_-4_5"          # Midtown, contains the Empire State Building
SAMPLE_BUILDINGS = 60
IOU_MIN = 0.98
HEIGHT_TOL_M = 0.01

_COMPONENT = {5120: ("b", 1), 5121: ("B", 1), 5122: ("h", 2), 5123: ("H", 2),
              5125: ("I", 4), 5126: ("f", 4)}
_NCOMP = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}


# --------------------------------------------------------------------------- fixtures
@pytest.fixture(scope="session")
def tile_glb(tmp_path_factory) -> tuple[Path, str]:
    """The shipped tile if it exists, else build it into a temporary directory."""
    import build_tile as bt

    shipped = bt.OUT_ROOT / FIXTURE_TILE / "tile_buildings.glb"
    if shipped.exists():
        return shipped, FIXTURE_TILE
    out = tmp_path_factory.mktemp("tiles")
    bt.build_tile(FIXTURE_TILE, out_root=out, lods=(0, 1, 2))
    return out / FIXTURE_TILE / "tile_buildings.glb", FIXTURE_TILE


@pytest.fixture(scope="session")
def gltf(tile_glb):
    path, _ = tile_glb
    return pygltflib.GLTF2().load(str(path))


@pytest.fixture(scope="session")
def source(tile_glb):
    """Source rows of the tile keyed by BIN, with the cleaned polygon in tile-local metres."""
    import pandas as pd

    _, tile = tile_glb
    df = pd.read_parquet(td.tile_path(tile))
    x0, y0 = td.tile_origin(tile)
    geoms = shapely.from_wkb(df["footprint"].to_numpy())
    cleaned = sg.clean_footprints(geoms)
    out = {}
    for i, b in enumerate(df["bin"].to_numpy()):
        parts = cleaned[i]
        if not parts:
            continue
        local = [shapely.transform(p, lambda c: c - np.array([x0, y0])) for p in parts]
        out[int(b)] = {"row": df.iloc[i], "polys": local}
    return out


# --------------------------------------------------------------------------- glTF reading
def _accessor(g, index: int) -> np.ndarray:
    acc = g.accessors[index]
    assert acc.bufferView is not None, "accessor has no bufferView (compressed file?)"
    bv = g.bufferViews[acc.bufferView]
    fmt, size = _COMPONENT[acc.componentType]
    ncomp = _NCOMP[acc.type]
    blob = g.binary_blob()
    base = (bv.byteOffset or 0) + (acc.byteOffset or 0)
    stride = bv.byteStride or (size * ncomp)
    out = np.empty((acc.count, ncomp), dtype=np.float64 if fmt == "f" else np.int64)
    for i in range(acc.count):
        out[i] = struct.unpack_from("<" + fmt * ncomp, blob, base + i * stride)
    return out if ncomp > 1 else out[:, 0]


def _prim_attrs(prim) -> dict[str, int]:
    d = prim.attributes.__dict__ if hasattr(prim.attributes, "__dict__") else dict(prim.attributes)
    return {k: v for k, v in d.items() if v is not None}


def _lod_of(name: str) -> int:
    if name.endswith("_LOD1"):
        return 1
    if name.endswith("_LOD2"):
        return 2
    return 0


def _collect(g, lod: int) -> dict[int, dict]:
    """Triangles and attributes of every building at the given LOD, keyed by BIN.

    glTF is Y-up: (gx, gy, gz) = (bx, bz, -by), so Blender/NYC_TM tile-local coordinates come back
    as x = gx, y = -gz, z = gy.
    """
    per_bin: dict[int, dict] = {}
    for mesh in g.meshes:
        if _lod_of(mesh.name) != lod:
            continue
        for prim in mesh.primitives:
            attrs = _prim_attrs(prim)
            pos = _accessor(g, attrs["POSITION"])
            idx = _accessor(g, prim.indices).astype(np.int64)
            bins = _accessor(g, attrs["_BIN"])
            xyz = np.column_stack([pos[:, 0], -pos[:, 2], pos[:, 1]])
            other = {k: _accessor(g, v) for k, v in attrs.items() if k.startswith("_")}
            tri = idx.reshape(-1, 3)
            tri_bin = np.rint(bins[tri[:, 0]]).astype(np.int64)
            for b in np.unique(tri_bin):
                sel = tri_bin == b
                rec = per_bin.setdefault(int(b), {"pos": [], "tri": [], "attrs": None, "n": 0})
                t = tri[sel]
                uniq, inv = np.unique(t, return_inverse=True)
                rec["pos"].append(xyz[uniq])
                rec["tri"].append(inv.reshape(-1, 3) + rec["n"])
                rec["n"] += len(uniq)
                if rec["attrs"] is None:
                    rec["attrs"] = {k: float(v[t[0, 0]]) for k, v in other.items()}
    for rec in per_bin.values():
        rec["pos"] = np.vstack(rec["pos"])
        rec["tri"] = np.vstack(rec["tri"])
    return per_bin


@pytest.fixture(scope="session")
def lod0(gltf):
    return _collect(gltf, 0)


# --------------------------------------------------------------------------- tests
def test_glb_loads_and_has_lod_chain(gltf, tile_glb):
    path, tile = tile_glb
    assert path.stat().st_size > 10_000
    names = [m.name for m in gltf.meshes]
    assert names, "no meshes in the tile glb"
    lods = {_lod_of(n) for n in names}
    assert lods == {0, 1, 2}, f"LOD chain incomplete: {sorted(lods)}"
    assert all(n.startswith(tile) for n in names), names[:3]
    # one mesh per (LOD, material class) keeps the draw calls bounded
    assert len(names) <= 3 * 25, f"{len(names)} meshes is more than one per LOD per material"
    assert len({m.name for m in gltf.materials}) == len(gltf.materials)
    # DATA_CONTRACTS §13: asset.extras.nycsim
    meta = (gltf.asset.extras or {}).get("nycsim")
    assert isinstance(meta, dict), "asset.extras.nycsim missing"
    assert meta["tile"] == tile and meta["crs"] == "NYC_TM"
    assert meta["origin_m"][:2] == list(td.tile_origin(tile))
    assert meta["schema_version"] == 1 and meta["lods"] == [0, 1, 2]


def test_lod_triangle_budget(gltf):
    counts = {0: 0, 1: 0, 2: 0}
    for mesh in gltf.meshes:
        lod = _lod_of(mesh.name)
        for prim in mesh.primitives:
            counts[lod] += gltf.accessors[prim.indices].count // 3
    assert counts[0] > 0
    assert counts[1] < counts[0], counts
    assert counts[2] < counts[1], counts
    assert counts[2] / counts[0] < 0.45, f"LOD2 is not a massing LOD: {counts}"


def test_attributes_present(gltf):
    want0 = {"_BIN", "_FACADE_CLASS", "_FLOORS", "_FLOOR_HEIGHT", "_GROUND_FLOOR_HEIGHT",
             "_IS_STOREFRONT", "_LIT_SEED_HI", "_LIT_SEED_LO"}
    for mesh in gltf.meshes:
        if _lod_of(mesh.name) != 0:
            continue
        for prim in mesh.primitives:
            attrs = set(_prim_attrs(prim))
            assert want0 <= attrs, f"{mesh.name} missing {sorted(want0 - attrs)}"
            assert "TEXCOORD_0" in attrs, mesh.name


def test_every_source_building_is_present(lod0, source):
    missing = set(source) - set(lod0)
    assert not missing, f"{len(missing)} buildings missing from the glb, e.g. {sorted(missing)[:5]}"


def _sample(keys) -> list[int]:
    keys = sorted(keys)
    if len(keys) <= SAMPLE_BUILDINGS:
        return keys
    step = len(keys) / SAMPLE_BUILDINGS
    return [keys[int(i * step)] for i in range(SAMPLE_BUILDINGS)]


def test_buildings_are_watertight_solids(lod0):
    bad = []
    for b in _sample(lod0):
        rec = lod0[b]
        rep = sg.watertight_report(rec["pos"], rec["tri"], weld=2e-3)
        if not rep["closed"] or rep["volume_m3"] <= 0:
            bad.append((b, rep))
    assert not bad, f"{len(bad)} of {SAMPLE_BUILDINGS} sampled buildings are not closed solids: {bad[:3]}"


def test_height_matches_source_within_1cm(lod0, source):
    errs = []
    for b in _sample(set(lod0) & set(source)):
        z = lod0[b]["pos"][:, 2]
        row = source[b]["row"]
        dz = float(z.max() - z.min())
        errs.append((b, abs(dz - float(row["height"])),
                     abs(float(z.min()) - float(row["ground_z"])),
                     abs(float(z.max()) - float(row["roof_z"]))))
    worst_h = max(e[1] for e in errs)
    worst_g = max(e[2] for e in errs)
    worst_r = max(e[3] for e in errs)
    assert worst_h <= HEIGHT_TOL_M, f"height error {worst_h:.4f} m > {HEIGHT_TOL_M} m"
    assert worst_g <= HEIGHT_TOL_M, f"ground_z error {worst_g:.4f} m"
    assert worst_r <= HEIGHT_TOL_M, f"roof_z error {worst_r:.4f} m"


def test_footprint_iou_above_098(lod0, source):
    """The floor slab of the mesh must reproduce the real footprint polygon."""
    worst = (1.0, None)
    for b in _sample(set(lod0) & set(source)):
        rec = lod0[b]
        z0 = rec["pos"][:, 2].min()
        tri = rec["tri"]
        zt = rec["pos"][tri, 2]
        base = tri[np.all(np.abs(zt - z0) < 2e-3, axis=1)]
        if len(base) == 0:
            pytest.fail(f"building {b} has no floor slab (open shell)")
        polys = [Polygon(rec["pos"][t][:, :2]) for t in base]
        polys = [p for p in polys if p.is_valid and p.area > 0]
        mesh_fp = shapely.union_all(polys).buffer(0)
        src = shapely.union_all(source[b]["polys"]).buffer(0)
        inter = mesh_fp.intersection(src).area
        union = mesh_fp.union(src).area
        iou = inter / union if union > 0 else 0.0
        if iou < worst[0]:
            worst = (iou, b)
    assert worst[0] > IOU_MIN, f"worst footprint IoU {worst[0]:.4f} on BIN {worst[1]}"


def test_attribute_round_trip(lod0, source):
    for b in _sample(set(lod0) & set(source)):
        a = lod0[b]["attrs"]
        row = source[b]["row"]
        assert int(round(a["_BIN"])) == b
        assert int(round(a["_FLOORS"])) == int(row["floors"]), b
        assert abs(a["_FLOOR_HEIGHT"] - float(row["floor_height"])) < 1e-3, b
        assert abs(a["_GROUND_FLOOR_HEIGHT"] - float(row["ground_floor_height"])) < 1e-3, b
        assert int(round(a["_IS_STOREFRONT"])) == int(bool(row["has_storefront"])), b
        seed = int(round(a["_LIT_SEED_HI"])) * 65536 + int(round(a["_LIT_SEED_LO"]))
        assert seed == int(row["lit_seed"]), f"lit_seed round-trip failed for BIN {b}"
        hi, lo = int(round(a["_LIT_SEED_HI"])), int(round(a["_LIT_SEED_LO"]))
        assert 0 <= hi < 65536 and 0 <= lo < 65536, (b, hi, lo)


def test_wall_uvs_are_metres(gltf, source):
    """On every vertical wall face, ``1 - V`` is the height above the building's own ``ground_z`` in metres
    and u is arc length along the facade.  Horizontal faces (bottom slab, parapet coping) carry
    planar metre UVs instead and are excluded by the normal test, exactly as the engine's facade
    shader branches on them."""
    checked = 0
    worst = 0.0
    for mesh in gltf.meshes:
        if _lod_of(mesh.name) != 0:
            continue
        for prim in mesh.primitives:
            attrs = _prim_attrs(prim)
            pos = _accessor(gltf, attrs["POSITION"])
            uv = _accessor(gltf, attrs["TEXCOORD_0"])
            bins = np.rint(_accessor(gltf, attrs["_BIN"])).astype(np.int64)
            tri = _accessor(gltf, prim.indices).astype(np.int64).reshape(-1, 3)
            xyz = np.column_stack([pos[:, 0], -pos[:, 2], pos[:, 1]])
            a, b, c = xyz[tri[:, 0]], xyz[tri[:, 1]], xyz[tri[:, 2]]
            n = np.cross(b - a, c - a)
            ln = np.linalg.norm(n, axis=1)
            keep = ln > 1e-9
            vertical = np.zeros(len(tri), bool)
            vertical[keep] = np.abs(n[keep, 2] / ln[keep]) < 0.05
            for t in tri[vertical][:400]:
                bin_ = int(bins[t[0]])
                row = source.get(bin_)
                if row is None:
                    continue
                g0 = float(row["row"]["ground_z"])
                # glTF stores V with a top-left origin: v_gltf = 1 - v_blender (metres up)
                err = float(np.max(np.abs((1.0 - uv[t, 1]) - (xyz[t, 2] - g0))))
                worst = max(worst, err)
                checked += 1
            # u must advance along the facade, not be a normalised 0..1 coordinate
            if vertical.any():
                assert uv[tri[vertical], 0].max() > 3.0, mesh.name
    assert checked > 200, f"only {checked} wall triangles checked"
    assert worst < 0.02, f"wall v is not height above ground_z (worst error {worst:.3f} m)"


def test_manifest_matches_glb(tile_glb):
    import json

    path, tile = tile_glb
    man = path.parent / "manifest.json"
    assert man.exists()
    m = json.loads(man.read_text())
    assert m["tile"] == tile
    assert m["buildings"]["open_shells_lod0"] == 0
    assert m["glb"]["bytes"] == path.stat().st_size
    assert set(m["triangles"]) == {"lod0", "lod1", "lod2"}
    assert m["materials"], "no material list in the manifest"


# --------------------------------------------------------------------------- pure geometry layer
_AWKWARD = {
    "rect": Polygon([(0, 0), (20, 0), (20, 12), (0, 12)]),
    "L": Polygon([(0, 0), (30, 0), (30, 10), (18, 10), (18, 22), (0, 22)]),
    "courtyard": Polygon([(0, 0), (40, 0), (40, 40), (0, 40)], [[(10, 10), (10, 20), (20, 20), (20, 10)]]),
    "triangle": Polygon([(0, 0), (15, 0), (6, 11)]),
    "sliver": Polygon([(0, 0), (30, 0), (30, 3.2), (0, 3.2)]),
}


@pytest.mark.parametrize("shape", sorted(_AWKWARD))
@pytest.mark.parametrize("kind", list(range(9)))
@pytest.mark.parametrize("lod", [0, 1, 2])
def test_shellgeom_closes_every_roof_type(shape, kind, lod):
    poly = _AWKWARD[shape]
    spec = sg.BuildingSpec(bin=1, polygon=poly, ground_z=10.0, roof_z=28.0,
                           roof=sg.RoofSpec(kind=kind), mat_wall=0, mat_roof=19,
                           facade_heading=90.0, floors=5, area=poly.area)
    buf = sg.build_shell(spec, lod)
    pos = np.asarray(buf.pos)
    tris = np.asarray(buf.tris)
    rep = sg.watertight_report(pos, tris)
    assert rep["closed"], f"{shape}/{sg.ROOF_NAMES[kind]}/lod{lod}: {rep}"
    assert rep["volume_m3"] > 0, "normals are inverted (negative signed volume)"
    assert abs(pos[:, 2].max() - 28.0) < 1e-6 and abs(pos[:, 2].min() - 10.0) < 1e-6


def test_footprint_cleaning_keeps_holes_and_winding():
    p = _AWKWARD["courtyard"]
    out = sg.clean_footprints(np.array([p], dtype=object))[0]
    assert len(out) == 1
    q = out[0]
    assert len(q.interiors) == 1
    assert q.exterior.is_ccw
    assert not q.interiors[0].is_ccw
    assert abs(q.area - p.area) < 0.05


def test_snap_is_two_centimetres():
    ring = [(0, 0), (10.0004, 0), (10.0004, 6.0007), (0, 6.0007)]
    out = sg.clean_footprints(np.array([Polygon(ring)], dtype=object))[0][0]
    coords = np.asarray(out.exterior.coords)
    assert np.allclose(coords / 0.02, np.rint(coords / 0.02), atol=1e-6), coords


def test_lod2_is_box_massing():
    poly = _AWKWARD["L"]
    spec = sg.BuildingSpec(bin=1, polygon=poly, ground_z=0.0, roof_z=20.0, roof=sg.RoofSpec(),
                           mat_wall=0, mat_roof=19, floors=6, area=poly.area)
    lod0 = sg.build_shell(spec, 0)
    lod2 = sg.build_shell(spec, 2)
    assert len(lod2.tris) < len(lod0.tris)
    assert len(lod2.pos) <= 16, "LOD2 outline should be a simplified hull"
