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
    """The glb must carry exactly the LOD chain its manifest declares.

    A tile may legitimately be built with `--lod 0,1` (the full-city run does, to halve the bytes),
    so the chain is checked against the manifest rather than hard-coded to 0/1/2; a tile built with
    the default settings must still have all three.
    """
    import json

    path, tile = tile_glb
    assert path.stat().st_size > 10_000
    names = [m.name for m in gltf.meshes]
    assert names, "no meshes in the tile glb"
    lods = {_lod_of(n) for n in names}
    declared = {int(k[3:]) for k in json.loads((path.parent / "manifest.json").read_text())["triangles"]}
    assert 0 in declared, "LOD0 is mandatory"
    assert lods == declared, f"glb has LODs {sorted(lods)} but the manifest declares {sorted(declared)}"
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
    present = set()
    for mesh in gltf.meshes:
        lod = _lod_of(mesh.name)
        present.add(lod)
        for prim in mesh.primitives:
            counts[lod] += gltf.accessors[prim.indices].count // 3
    assert counts[0] > 0
    if 1 in present:
        assert counts[1] < counts[0], counts
    if 2 in present:
        assert counts[2] < counts.get(1, counts[0]), counts
        assert counts[2] / counts[0] < 0.45, f"LOD2 is not a massing LOD: {counts}"


def test_full_lod_chain_when_built_with_defaults(tmp_path_factory):
    """A tile built with the default `--lod 0,1,2` carries all three meshes."""
    import build_tile as bt

    out = tmp_path_factory.mktemp("lodchain")
    m = bt.build_tile("t_-6_0", out_root=out, lods=(0, 1, 2))
    g = pygltflib.GLTF2().load(str(out / "t_-6_0" / "tile_buildings.glb"))
    assert {_lod_of(mesh.name) for mesh in g.meshes} == {0, 1, 2}
    assert set(m["triangles"]) == {"lod0", "lod1", "lod2"}


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
    assert "lod0" in m["triangles"]
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


# --------------------------------------------------------------------------- stepped massing
_STEP_CASES = {
    "edge wing": (Polygon([(0, 0), (20, 0), (20, 12), (0, 12)]),
                  [(Polygon([(0, 4), (20, 4), (20, 12), (0, 12)]), 25.0),
                   (Polygon([(0, 0), (20, 0), (20, 4), (0, 4)]), 18.0)]),
    "corner wing": (Polygon([(0, 0), (20, 0), (20, 12), (0, 12)]),
                    [(Polygon([(0, 0), (20, 0), (20, 12), (0, 12)]).difference(
                        Polygon([(0, 0), (6, 0), (6, 5), (0, 5)])), 25.0),
                     (Polygon([(0, 0), (6, 0), (6, 5), (0, 5)]), 18.0)]),
    "central tower": (Polygon([(0, 0), (20, 0), (20, 12), (0, 12)]),
                      [(Polygon([(5, 3), (15, 3), (15, 9), (5, 9)]), 25.0),
                       (Polygon([(0, 0), (20, 0), (20, 12), (0, 12)]).difference(
                           Polygon([(5, 3), (15, 3), (15, 9), (5, 9)])), 16.0)]),
    "three levels": (Polygon([(0, 0), (20, 0), (20, 12), (0, 12)]),
                     [(Polygon([(0, 8), (20, 8), (20, 12), (0, 12)]), 25.0),
                      (Polygon([(0, 4), (20, 4), (20, 8), (0, 8)]), 20.0),
                      (Polygon([(0, 0), (20, 0), (20, 4), (0, 4)]), 15.0)]),
    "courtyard": (Polygon([(0, 0), (20, 0), (20, 12), (0, 12)], [[(8, 5), (8, 8), (12, 8), (12, 5)]]),
                  [(Polygon([(0, 0), (20, 0), (20, 12), (0, 12)],
                            [[(8, 5), (8, 8), (12, 8), (12, 5)]]).difference(
                      Polygon([(0, 0), (20, 0), (20, 3), (0, 3)])), 25.0),
                   (Polygon([(0, 0), (20, 0), (20, 3), (0, 3)]), 17.0)]),
}


@pytest.mark.parametrize("case", sorted(_STEP_CASES))
@pytest.mark.parametrize("kind", [0, 1, 2, 4])
@pytest.mark.parametrize("lod", [0, 1])
def test_stepped_massing_is_a_closed_solid(case, kind, lod):
    """A stepped building is one closed solid spanning exactly [ground_z, roof_z]."""
    base, steps = _STEP_CASES[case]
    spec = sg.BuildingSpec(bin=1, polygon=base, ground_z=10.0, roof_z=25.0,
                           roof=sg.RoofSpec(kind=kind, parapet_h=sg.PARAPET_H_M),
                           mat_wall=0, mat_roof=19, facade_heading=180.0, floors=6,
                           area=base.area, roof_steps=steps)
    buf = sg._build_shell_once(spec, lod)
    pos = np.asarray(buf.pos)
    tris = np.asarray(buf.tris)
    rep = sg.watertight_report(pos, tris, weld=sg.STEP_WELD_M)
    assert rep["closed"], f"{case}/lod{lod}: {rep}"
    assert rep["volume_m3"] > 0
    assert abs(pos[:, 2].max() - 25.0) < 1e-3 and abs(pos[:, 2].min() - 10.0) < 1e-3


def test_stepped_massing_actually_steps():
    """The lower level must really be lower — not silently flattened to the top height."""
    base, steps = _STEP_CASES["edge wing"]
    spec = sg.BuildingSpec(bin=1, polygon=base, ground_z=10.0, roof_z=25.0,
                           roof=sg.RoofSpec(kind=0, parapet_h=0.0), mat_wall=0, mat_roof=19,
                           facade_heading=180.0, floors=6, area=base.area, roof_steps=steps)
    flat = sg.BuildingSpec(bin=1, polygon=base, ground_z=10.0, roof_z=25.0,
                           roof=sg.RoofSpec(kind=0, parapet_h=0.0), mat_wall=0, mat_roof=19,
                           facade_heading=180.0, floors=6, area=base.area)
    v_step = sg.watertight_report(np.asarray(sg._build_shell_once(spec, 0).pos),
                                  np.asarray(sg._build_shell_once(spec, 0).tris),
                                  weld=sg.STEP_WELD_M)["volume_m3"]
    v_flat = sg.watertight_report(np.asarray(sg._build_shell_once(flat, 0).pos),
                                  np.asarray(sg._build_shell_once(flat, 0).tris))["volume_m3"]
    # the wing is 20 x 4 m and 7 m lower, so the stepped solid is 560 m3 smaller
    assert abs((v_flat - v_step) - 560.0) < 1.0, (v_flat, v_step)


def test_roofstep_recovery_rejects_disagreeing_levels():
    """The published-area gate must reject outlines that do not tile the building."""
    import roofsteps as rsx

    good = [(10.0, Polygon([(0, 0), (10, 0), (10, 5), (0, 5)])),
            (14.0, Polygon([(0, 5), (10, 5), (10, 10), (0, 10)]))]
    ok, why, strict = rsx.check_against_published(good, [10.0, 14.0], [50.0, 50.0], 100.0)
    assert ok, why
    assert strict
    bad, why, _ = rsx.check_against_published(good, [10.0, 14.0], [50.0, 50.0], 400.0)
    assert not bad and "footprint" in why


def test_roofstep_partition_tiles_the_footprint():
    import roofsteps as rsx

    fp = Polygon([(0, 0), (20, 0), (20, 12), (0, 12)])
    levels = [(18.0, Polygon([(-0.003, -0.004), (20.006, 0.002), (20.001, 4.003), (0.002, 3.997)])),
              (25.0, Polygon([(0.001, 4.002), (20.004, 3.998), (19.997, 12.005), (-0.002, 11.996)]))]
    regions, why = rsx.partition_footprint(fp, levels)
    assert regions, why
    assert abs(sum(p.area for p, _ in regions) - fp.area) < 0.05
    assert len({round(z, 2) for _, z in regions}) == 2


def test_lod2_is_box_massing():
    poly = _AWKWARD["L"]
    spec = sg.BuildingSpec(bin=1, polygon=poly, ground_z=0.0, roof_z=20.0, roof=sg.RoofSpec(),
                           mat_wall=0, mat_roof=19, floors=6, area=poly.area)
    lod0 = sg.build_shell(spec, 0)
    lod2 = sg.build_shell(spec, 2)
    assert len(lod2.tris) < len(lod0.tris)
    assert len(lod2.pos) <= 16, "LOD2 outline should be a simplified hull"


# --------------------------------------------------------------------------- stepped massing, real data
@pytest.fixture(scope="session")
def step_tile():
    """Real specs for the fixture tile, with the recovered levels beside them."""
    import roofsteps as rsx

    load = td.load_tile(FIXTURE_TILE)
    sets, _ = rsx.load_tile_steps(FIXTURE_TILE)
    return load, sets


@pytest.fixture(scope="session")
def published_levels():
    """``roof_level_z`` / ``z_roof_max`` straight out of the CityGML table, per BIN."""
    import pyarrow.parquet as pq

    import roofsteps as rsx

    tx, ty = (int(v) for v in FIXTURE_TILE[2:].split("_", 1))
    out: dict[int, tuple[np.ndarray, float]] = {}
    for fname in rsx._files_for(tx, ty):
        path = rsx.CITYGML_DIR / fname
        if not path.exists():
            continue
        t = pq.read_table(path, columns=["bin", "roof_level_z", "z_roof_max", "footprint_area_m2"],
                          filters=[("tx", "=", tx), ("ty", "=", ty)])
        for b, lz, zm in zip(t.column("bin").to_pylist(), t.column("roof_level_z").to_pylist(),
                             t.column("z_roof_max").to_pylist()):
            out[int(b)] = (np.asarray(lz or [], dtype=float), float(zm or 0.0))
    return out


def test_recovered_levels_are_disjoint_and_tile_the_plan(step_tile):
    """Each level is a disjoint part of the plan, and together they cover it.

    This is the claim the whole feature rests on: if the levels overlapped, or left the plan
    uncovered, the regions cut from them would put a step on the wrong part of the building.
    """
    _, sets = step_tile
    assert sets, "no CityGML step sets for the fixture tile"
    checked = 0
    for ss in sets.values():
        if not ss.ok:
            continue
        checked += 1
        polys = [p for _, p in ss.levels]
        total = sum(p.area for p in polys)
        overlap = sum(polys[i].intersection(polys[j]).area
                      for i in range(len(polys)) for j in range(i + 1, len(polys)))
        assert overlap <= 1e-6 * max(total, 1.0), f"bin {ss.bin}: levels overlap by {overlap:.3f} m2"
    assert checked > 100, f"only {checked} multi-level buildings recovered"


def test_step_regions_are_inside_the_footprint_and_cover_it(step_tile):
    """The regions the shell is cut into are a partition of the real footprint."""
    load, _ = step_tile
    checked = 0
    for spec in load.specs:
        steps = spec.roof_steps
        if not steps or len(steps) < 2:
            continue
        checked += 1
        fp = spec.polygon
        union = shapely.union_all([p for p, _ in steps])
        outside = union.difference(fp.buffer(sg.SNAP_M * 2)).area
        assert outside < 0.05, f"bin {spec.bin}: {outside:.3f} m2 of level outline outside the footprint"
        assert union.area >= 0.99 * fp.area, f"bin {spec.bin}: levels cover only {union.area / fp.area:.3f}"
        overlap = sum(steps[i][0].intersection(steps[j][0]).area
                      for i in range(len(steps)) for j in range(i + 1, len(steps)))
        assert overlap < 0.5, f"bin {spec.bin}: regions overlap by {overlap:.3f} m2"
    assert checked > 100, f"only {checked} buildings carry steps"


def test_step_heights_come_from_the_published_roof_levels(step_tile, published_levels):
    """Undo the height shift and every step must land on a level the CityGML stage published.

    This is what separates a measured step from an invented one: the shell may move the whole
    profile so its top meets the contract ``roof_z``, but the *depth* of each step has to be one
    the source reports.
    """
    load, _ = step_tile
    errs: list[float] = []
    for spec in load.specs:
        steps = spec.roof_steps
        if not steps or len(steps) < 2:
            continue
        pz, zmax = published_levels.get(spec.bin, (np.array([]), 0.0))
        if not len(pz):
            continue
        dz = spec.roof_z - zmax
        for _, z in steps:
            errs.append(float(np.min(np.abs(pz - (z - dz)))))
    assert len(errs) > 300, f"only {len(errs)} step heights to check"
    e = np.asarray(errs)
    assert np.median(e) < 0.05, f"median step-height error {np.median(e):.3f} m"
    assert (e < 0.5).mean() > 0.99, f"only {(e < 0.5).mean():.3f} of steps within 0.5 m of a published level"


def test_shipped_stepped_shells_close_and_remove_volume(step_tile):
    """A stepped shell must be closed, and must be *smaller* than the slab it replaces."""
    import dataclasses

    load, _ = step_tile
    stepped = [s for s in load.specs if s.roof_steps and len(s.roof_steps) >= 2]
    assert len(stepped) > 100
    sample = stepped[:: max(len(stepped) // 40, 1)]
    shipped = 0
    for spec in sample:
        buf = sg.build_shell(spec, 0)
        rep = sg.watertight_report(np.asarray(buf.pos), np.asarray(buf.tris), weld=sg.STEP_WELD_M)
        assert rep["closed"], f"bin {spec.bin}: open shell {rep}"
        if buf.fallback and not str(buf.fallback).startswith("steps_merged"):
            continue                      # reverted to a flat cap: counted, not shipped as stepped
        shipped += 1
        flat = sg.build_shell(dataclasses.replace(spec, roof_steps=None), 0)
        v_flat = sg.watertight_report(np.asarray(flat.pos), np.asarray(flat.tris))["volume_m3"]
        assert rep["volume_m3"] < v_flat + 1.0, f"bin {spec.bin}: stepped solid is not below the slab"
        assert 12 <= len(buf.tris) <= 4000, f"bin {spec.bin}: {len(buf.tris)} triangles is not a shell"
    assert shipped >= len(sample) // 2, f"only {shipped} of {len(sample)} sampled buildings shipped stepped"


def test_stepped_shells_span_exactly_ground_to_roof(step_tile):
    """A stepped solid must still be exactly as tall as the flat one it replaces.

    The merge fallback absorbs a small level into the neighbour that surrounds it.  If the level it
    absorbed were the *highest* one, the building would stop below its measured ``roof_z`` — the
    steps would have quietly changed the building's height, which is the one thing this stage
    guarantees about every solid.  This checks the built mesh, not the spec.
    """
    load, _ = step_tile
    stepped = [s for s in load.specs if s.roof_steps and len(s.roof_steps) >= 2]
    assert len(stepped) > 100
    worst = 0.0
    for spec in stepped[:: max(len(stepped) // 60, 1)]:
        buf = sg.build_shell(spec, 0)
        z = np.asarray(buf.pos)[:, 2]
        worst = max(worst, abs(float(z.max()) - spec.roof_z),
                    abs(float(z.min()) - spec.ground_z))
    assert worst <= 0.01, f"stepped shell z-extent is off by {worst:.4f} m"


def test_step_merging_never_absorbs_the_top_level():
    """The highest level survives every stage of the merge ladder."""
    base = Polygon([(0, 0), (30, 0), (30, 20), (0, 20)])
    steps = [(Polygon([(0, 0), (30, 0), (30, 18), (0, 18)]), 20.0),
             (Polygon([(0, 18), (28, 18), (28, 20), (0, 20)]), 12.0),
             (Polygon([(28, 18), (30, 18), (30, 20), (28, 20)]), 26.0)]   # a 4 m2 penthouse
    for reduced in (sg._merge_small_steps(steps, 200.0), sg._merge_to_count(steps, 2)):
        assert reduced, "the ladder emptied the step set"
        assert abs(max(z for _, z in reduced) - 26.0) < 1e-9, \
            f"the 26 m penthouse was absorbed: {sorted(z for _, z in reduced)}"


def test_manifest_step_counts_are_consistent():
    """``shipped`` is what closed; it can never exceed what was applied, or applied what was found."""
    import json

    import build_tile as bt

    seen = 0
    for p in sorted(bt.OUT_ROOT.glob("*/manifest.json")):
        m = json.loads(p.read_text())
        rs = m.get("roof_steps") or {}
        if "shipped" not in rs:
            continue
        seen += 1
        assert rs["shipped"] <= rs["applied"] <= rs["recovered"] <= rs["candidates"], (p.name, rs)
        assert rs["shipped"] + rs["lost_would_not_close"] == rs["applied"], (p.name, rs)
        assert rs["applied_exact_z"] + rs["applied_offset_z"] == rs["applied"], (p.name, rs)
        assert rs["shipped_with_levels_merged"] <= rs["shipped"], (p.name, rs)
    assert seen > 0, "no rebuilt tile manifest carries step counts"


def test_step_merging_keeps_the_partition(step_tile):
    """The fallback that merges small levels must still tile the footprint exactly."""
    load, _ = step_tile
    busy = [s for s in load.specs if s.roof_steps and len(s.roof_steps) >= 4]
    assert busy, "no building with four or more regions on the fixture tile"
    for spec in busy[:20]:
        merged = sg._merge_small_steps(spec.roof_steps, 30.0)
        assert len(merged) <= len(spec.roof_steps)
        if len(merged) < 2:
            continue
        before = shapely.union_all([p for p, _ in spec.roof_steps])
        after = shapely.union_all([p for p, _ in merged])
        assert abs(after.area - before.area) < 0.05, f"bin {spec.bin}: merging changed the plan"
        ov = sum(merged[i][0].intersection(merged[j][0]).area
                 for i in range(len(merged)) for j in range(i + 1, len(merged)))
        assert ov < 0.5, f"bin {spec.bin}: merged regions overlap"


# --------------------------------------------------------------------------- shell materials
def test_material_variation_is_deterministic_and_in_range():
    import shellmat as sm

    vals = [sm.variation(h, lo) for h in range(60) for lo in range(60)]
    assert all(-1.0 <= v <= 1.0 for v in vals)
    assert sm.variation(7, 11) == sm.variation(7, 11)
    assert len({round(v, 6) for v in vals}) > 3000, "the per-building tint barely varies"
    assert abs(float(np.mean(vals))) < 0.05, "the tint is biased light or dark"
    for name in sm.MATERIALS:
        for k in (-1.0, 0.0, 1.0):
            col, rough = sm.shaded(name, k)
            assert all(0.0 <= c <= 1.0 for c in col), (name, k, col)
            assert 0.0 < rough <= 1.0, (name, k, rough)


def test_glass_curtain_ships_as_a_dark_reflective_material(tile_glb):
    """The gap this closes: a curtain wall that renders as a pale flat solid."""
    import json

    path, _ = tile_glb
    raw = path.read_bytes()
    n = struct.unpack("<I", raw[12:16])[0]
    doc = json.loads(raw[20:20 + n])
    mats = {m["name"]: m for m in doc.get("materials", [])}
    glass = mats.get("NYCSIM_glass_curtain")
    assert glass is not None, sorted(mats)
    pbr = glass["pbrMetallicRoughness"]
    rgb = pbr["baseColorFactor"][:3]
    lum = 0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]
    assert lum < 0.20, f"glass base colour luminance {lum:.3f} is not dark glass"
    assert pbr["roughnessFactor"] < 0.20, pbr
    assert pbr["metallicFactor"] > 0.2, pbr
    ext = glass.get("extensions", {})
    assert "KHR_materials_ior" in ext, ext
    for name in ("NYCSIM_red_brick", "NYCSIM_brownstone"):
        if name in mats:
            assert mats[name]["pbrMetallicRoughness"]["roughnessFactor"] > 0.5, name


def test_shipped_glb_carries_the_stepped_geometry(gltf, tile_glb):
    """The steps must be in the *file*, not only in the manifest.

    Counts buildings whose LOD0 mesh has two or more up-facing roof plateaus more than 1 m apart.
    That count is a **lower bound** on the stepped buildings — two levels less than a metre apart
    merge into one plateau here — so the check is that the manifest does not claim materially more
    than the file shows.  Measured over five tiles the detector finds 2,395 of 2,414 claimed
    (99.2 %); a manifest counting assignments rather than deliveries would be about 30 % over and
    fails this outright.  The 1 m threshold cannot be lowered: a flat roof's parapet coping sits
    0.60 m above its deck, so every flat building would read as two plateaus.
    """
    import json

    path, tile = tile_glb
    man = json.loads((path.parent / "manifest.json").read_text())
    rs = man.get("roof_steps") or {}
    if "shipped" not in rs:
        pytest.skip("tile predates the stepped-massing build")
    per_bin = _collect(gltf, 0)
    stepped = 0
    for rec in per_bin.values():
        pos = np.asarray(rec["pos"])
        tri = np.asarray(rec["tri"])
        v = pos[tri]
        nrm = np.cross(v[:, 1] - v[:, 0], v[:, 2] - v[:, 0])
        ln = np.linalg.norm(nrm, axis=1)
        ok = ln > 1e-9
        up = ok & (nrm[:, 2] > 0.99 * np.where(ok, ln, 1.0))
        if not up.any():
            continue
        area = 0.5 * ln[up]
        z = v[up][:, :, 2].mean(axis=1)
        order = np.argsort(z)
        z, area = z[order], area[order]
        plateaus = []
        for zz, aa in zip(z, area):
            if plateaus and zz - plateaus[-1][0] < 1.0:
                plateaus[-1] = (zz, plateaus[-1][1] + aa)
            else:
                plateaus.append((zz, aa))
        if len([p for p in plateaus if p[1] >= sg.MIN_PART_AREA_M2]) >= 2:
            stepped += 1
    assert stepped >= 0.97 * rs["shipped"], (
        f"{tile}: manifest claims {rs['shipped']} stepped buildings, the glb shows {stepped}")
