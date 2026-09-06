"""Verification tests for the vehicle lane (``blender_out/vehicles/``).

The tests read the **exported glb files**, not the Blender scene, so they check exactly what the engine will
import: node names, material-slot names, geometry extents, wheel pivots, LOD files and the convexity of the
``UCX_`` collision proxies.  A tiny self-contained glTF reader is used (no trimesh/pygltflib dependency).

Run: ``pytest -q tests/test_vehicles.py``
"""
from __future__ import annotations

import json
import math
import struct
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pytest

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "blender_out" / "vehicles"
CATALOG = OUT / "catalog"

#: dimension tolerance required by the brief
DIM_TOL_PCT = 2.0
#: how far a wheel pivot may sit from the published hub centre
PIVOT_TOL_M = 0.002
#: convexity tolerance for a UCX proxy, in metres
CONVEX_TOL_M = 2e-3

COMPONENT = {5120: ("b", 1), 5121: ("B", 1), 5122: ("h", 2), 5123: ("H", 2), 5125: ("I", 4), 5126: ("f", 4)}
NCOMP = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}


# --------------------------------------------------------------------------- minimal glTF reader
@dataclass
class Glb:
    path: Path
    json: dict
    bin: bytes

    @classmethod
    def load(cls, path: Path) -> "Glb":
        data = path.read_bytes()
        magic, version, _length = struct.unpack("<4sII", data[:12])
        assert magic == b"glTF", f"{path} is not a glb"
        assert version == 2, f"{path} is glTF {version}, expected 2"
        off, js, bn = 12, None, b""
        while off < len(data):
            clen, ctype = struct.unpack("<I4s", data[off:off + 8])
            chunk = data[off + 8:off + 8 + clen]
            if ctype == b"JSON":
                js = json.loads(chunk)
            elif ctype == b"BIN\x00":
                bn = chunk
            off += 8 + clen + (-(clen) % 4)
        assert js is not None, f"{path} has no JSON chunk"
        return cls(path=path, json=js, bin=bn)

    # -- accessors
    def accessor(self, idx: int) -> np.ndarray:
        acc = self.json["accessors"][idx]
        n = acc["count"]
        ncomp = NCOMP[acc["type"]]
        fmt, size = COMPONENT[acc["componentType"]]
        bv = self.json["bufferViews"][acc["bufferView"]]
        start = bv.get("byteOffset", 0) + acc.get("byteOffset", 0)
        stride = bv.get("byteStride") or ncomp * size
        raw = self.bin
        out = np.empty((n, ncomp), dtype=np.float64 if fmt == "f" else np.int64)
        for i in range(n):
            o = start + i * stride
            out[i] = struct.unpack_from("<" + fmt * ncomp, raw, o)
        return out

    # -- scene graph
    def nodes(self) -> list[dict]:
        return self.json.get("nodes", [])

    def node_names(self) -> set[str]:
        return {n.get("name", "") for n in self.nodes()}

    def material_names(self) -> set[str]:
        return {m.get("name", "") for m in self.json.get("materials", [])}

    def node_matrix(self, node: dict) -> np.ndarray:
        if "matrix" in node:
            return np.asarray(node["matrix"], dtype=np.float64).reshape(4, 4).T
        m = np.eye(4)
        s = node.get("scale", [1, 1, 1])
        r = node.get("rotation", [0, 0, 0, 1])
        t = node.get("translation", [0, 0, 0])
        x, y, z, w = r
        rot = np.array([
            [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
            [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
            [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
        ])
        m[:3, :3] = rot @ np.diag(s)
        m[:3, 3] = t
        return m

    def world_matrices(self) -> dict[int, np.ndarray]:
        nodes = self.nodes()
        parent = {}
        for i, n in enumerate(nodes):
            for c in n.get("children", []):
                parent[c] = i
        out: dict[int, np.ndarray] = {}

        def world(i: int) -> np.ndarray:
            if i in out:
                return out[i]
            m = self.node_matrix(nodes[i])
            if i in parent:
                m = world(parent[i]) @ m
            out[i] = m
            return m

        for i in range(len(nodes)):
            world(i)
        return out

    def mesh_bounds_local(self, mesh_idx: int) -> tuple[np.ndarray, np.ndarray]:
        lo = np.full(3, np.inf)
        hi = np.full(3, -np.inf)
        for prim in self.json["meshes"][mesh_idx]["primitives"]:
            acc = self.json["accessors"][prim["attributes"]["POSITION"]]
            lo = np.minimum(lo, np.asarray(acc["min"], dtype=np.float64))
            hi = np.maximum(hi, np.asarray(acc["max"], dtype=np.float64))
        return lo, hi

    def node_world_bounds(self, skip=()) -> dict[str, tuple[np.ndarray, np.ndarray]]:
        wm = self.world_matrices()
        out = {}
        for i, n in enumerate(self.nodes()):
            if "mesh" not in n:
                continue
            name = n.get("name", f"node{i}")
            if name.startswith(tuple(skip)):
                continue
            lo, hi = self.mesh_bounds_local(n["mesh"])
            corners = np.array([[lo[0] if a else hi[0], lo[1] if b else hi[1], lo[2] if c else hi[2]]
                                for a in (0, 1) for b in (0, 1) for c in (0, 1)])
            w = (wm[i][:3, :3] @ corners.T).T + wm[i][:3, 3]
            out[name] = (w.min(axis=0), w.max(axis=0))
        return out

    def triangles(self, skip=("UCX_",)) -> int:
        """Rendered triangles: mesh nodes whose name does not start with one of ``skip`` (the ``UCX_``
        collision proxies are not drawn and do not count against a LOD budget)."""
        total = 0
        for n in self.nodes():
            if "mesh" not in n or n.get("name", "").startswith(tuple(skip)):
                continue
            for p in self.json["meshes"][n["mesh"]]["primitives"]:
                if "indices" in p:
                    total += self.json["accessors"][p["indices"]]["count"] // 3
                else:
                    total += self.json["accessors"][p["attributes"]["POSITION"]]["count"] // 3
        return total

    def mesh_positions_indices(self, mesh_idx: int) -> tuple[np.ndarray, np.ndarray]:
        pos, idx, base = [], [], 0
        for prim in self.json["meshes"][mesh_idx]["primitives"]:
            p = self.accessor(prim["attributes"]["POSITION"])
            i = self.accessor(prim["indices"]).reshape(-1, 3)
            pos.append(p)
            idx.append(i + base)
            base += len(p)
        return np.concatenate(pos), np.concatenate(idx)


# --------------------------------------------------------------------------- fixtures
def _entries() -> list[dict]:
    if not CATALOG.exists():
        return []
    out = []
    for p in sorted(CATALOG.glob("*.json")):
        if p.name.startswith("_"):          # _build_summary.json is a run log, not a vehicle
            continue
        out.append(json.loads(p.read_text()))
    return out


ENTRIES = _entries()
IDS = [e["id"] for e in ENTRIES]

pytestmark = pytest.mark.skipif(not ENTRIES,
                                reason="no vehicle catalog entries; run blender/vehicles/build_all.py first")


@pytest.fixture(scope="module")
def glbs() -> dict[str, Glb]:
    return {e["id"]: Glb.load(REPO / e["glb"]) for e in ENTRIES}


def _entry(vid: str) -> dict:
    return next(e for e in ENTRIES if e["id"] == vid)


# --------------------------------------------------------------------------- the catalog itself
def test_catalog_is_complete():
    assert ENTRIES, "no catalog entries"
    required = {"id", "name", "class", "glb", "lods", "triangles", "published_dimensions_mm", "measured_m",
                "dimension_deviation_pct", "wheel_pivots", "nodes", "materials", "collision_proxies",
                "damage_regions", "contract_profile", "pivot"}
    for e in ENTRIES:
        missing = required - set(e)
        assert not missing, f"{e['id']} catalog entry missing {sorted(missing)}"
        assert (REPO / e["glb"]).exists(), f"{e['id']}: {e['glb']} does not exist"
        assert e["missing_nodes"] == [], f"{e['id']} reports missing nodes {e['missing_nodes']}"
        assert e["missing_material_slots"] == [], f"{e['id']} reports missing slots {e['missing_material_slots']}"


def test_catalog_ids_unique():
    assert len(IDS) == len(set(IDS))


# --------------------------------------------------------------------------- node contract
@pytest.mark.parametrize("vid", IDS)
def test_required_nodes_present(vid, glbs):
    e, glb = _entry(vid), glbs[vid]
    names = glb.node_names()
    waived = set(e.get("contract_waivers", {}))
    profile = e["contract_profile"]
    if profile == "full":
        required = set(e["nodes"]) & set(_full_contract())
        expect = set(_full_contract()) - waived
    else:
        expect = {n for n in e["nodes"] if n.startswith(("Body", "Wheel_"))}
    missing = expect - names
    assert not missing, f"{vid}: nodes missing from the glb: {sorted(missing)}"


def _full_contract() -> tuple[str, ...]:
    return (
        "Body", "Wheel_FL", "Wheel_FR", "Wheel_RL", "Wheel_RR",
        "Door_FL", "Door_FR", "Door_RL", "Door_RR",
        "SteeringWheel", "Hood", "Trunk", "Wiper_L", "Wiper_R",
        "Window_WS", "Window_BACK", "Window_FL", "Window_FR", "Window_RL", "Window_RR",
        "Mirror_L", "Mirror_R", "Interior_Dash", "Shifter", "Pedals", "Plate_F", "Plate_R",
        "LIGHT_HEAD_L", "LIGHT_HEAD_R", "LIGHT_LOW", "LIGHT_HIGH", "LIGHT_TAIL_L", "LIGHT_TAIL_R",
        "LIGHT_BRAKE_L", "LIGHT_BRAKE_R", "LIGHT_TURN_FL", "LIGHT_TURN_FR", "LIGHT_TURN_RL", "LIGHT_TURN_RR",
        "LIGHT_REVERSE_L", "LIGHT_REVERSE_R", "LIGHT_PLATE", "LIGHT_DRL",
    )


@pytest.mark.parametrize("vid", IDS)
def test_required_material_slots_present(vid, glbs):
    e, glb = _entry(vid), glbs[vid]
    have = glb.material_names()
    waived = set(e.get("contract_waivers", {}))
    if e["contract_profile"] == "full":
        expect = {s for s in ("MIRROR_GLASS", "GAUGE_SPEED", "GAUGE_RPM", "SCREEN_CENTER", "PLATE_FACE")
                  if s not in waived}
        expect |= {s for s in _full_contract() if s.startswith("LIGHT_")} - waived
    else:
        expect = {"LIGHT_HEAD_L", "LIGHT_TAIL_L"} - waived
    missing = expect - have
    assert not missing, f"{vid}: material slots missing from the glb: {sorted(missing)}"


@pytest.mark.parametrize("vid", IDS)
def test_light_slots_are_emissive(vid, glbs):
    glb = glbs[vid]
    for m in glb.json.get("materials", []):
        if not m.get("name", "").startswith("LIGHT_"):
            continue
        assert "emissiveFactor" in m or "extensions" in m, \
            f"{vid}: light slot {m['name']} carries no emissive factor"


# --------------------------------------------------------------------------- dimensions
@pytest.mark.parametrize("vid", IDS)
def test_dimensions_within_two_percent(vid, glbs):
    e, glb = _entry(vid), glbs[vid]
    skip = tuple(["UCX_"] + [n for n in e["measured_m"].get("envelope_excludes", [])])
    bounds = glb.node_world_bounds(skip=skip)
    assert bounds, f"{vid}: no mesh nodes"
    lo = np.min([b[0] for b in bounds.values()], axis=0)
    hi = np.max([b[1] for b in bounds.values()], axis=0)
    # glTF is Y-up: X = vehicle +X, Y = vehicle +Z, Z = -vehicle +Y
    size = hi - lo
    got = {"length_mm": size[0] * 1000.0, "height_mm": size[1] * 1000.0, "width_mm": size[2] * 1000.0}
    pub = e["published_dimensions_mm"]
    for k in ("length_mm", "width_mm", "height_mm"):
        dev = 100.0 * (got[k] - pub[k]) / pub[k]
        assert abs(dev) <= DIM_TOL_PCT, \
            f"{vid}: {k} {got[k]:.0f} mm vs published {pub[k]:.0f} mm ({dev:+.2f} %, tolerance ±{DIM_TOL_PCT} %)"


@pytest.mark.parametrize("vid", IDS)
def test_origin_is_ground_under_rear_axle(vid, glbs):
    """The lowest point of the vehicle must sit on z = 0 and the rear axle must be at x = 0."""
    e, glb = _entry(vid), glbs[vid]
    bounds = glb.node_world_bounds(skip=("UCX_",))
    lo = np.min([b[0] for b in bounds.values()], axis=0)
    assert abs(lo[1]) < 0.01, f"{vid}: lowest point is {lo[1] * 1000:.1f} mm off the ground plane"
    rear = [p for n, p in e["wheel_pivots"].items() if n in ("Wheel_RL", "Wheel_RR", "Wheel_R")]
    assert rear, f"{vid}: no rear wheel pivot recorded"
    for p in rear:
        assert abs(p[0]) < PIVOT_TOL_M, f"{vid}: rear axle is at x = {p[0]:.4f} m, must be 0 (DATA_CONTRACTS §13)"


# --------------------------------------------------------------------------- wheels
@pytest.mark.parametrize("vid", IDS)
def test_wheel_pivots_at_hub_centres(vid, glbs):
    e, glb = _entry(vid), glbs[vid]
    wm = glb.world_matrices()
    by_name = {n.get("name", ""): i for i, n in enumerate(glb.nodes())}
    diam = e.get("wheel_diameters_mm", {})
    checked = 0
    for name, pivot in e["wheel_pivots"].items():
        # a carriage has smaller front wheels than rear, so the catalog records each wheel's own diameter
        r = diam.get(name, e["published_dimensions_mm"]["wheel_diameter_mm"]) / 2000.0
        assert name in by_name, f"{vid}: {name} not in the glb"
        i = by_name[name]
        t = wm[i][:3, 3]
        # glTF Y-up: (x, z, -y) of the Blender/vehicle frame
        got = np.array([t[0], -t[2], t[1]])
        want = np.asarray(pivot, dtype=np.float64)
        assert np.allclose(got, want, atol=PIVOT_TOL_M), \
            f"{vid}: {name} node translation {got} != catalog pivot {want}"
        assert abs(got[2] - r) < max(PIVOT_TOL_M, 0.02 * r), \
            f"{vid}: {name} hub is {got[2]:.4f} m above the ground, tyre radius is {r:.4f} m"
        node = glb.nodes()[i]
        lo, hi = glb.mesh_bounds_local(node["mesh"])
        # the wheel geometry must be centred on its own origin and have the published diameter
        centre = 0.5 * (lo + hi)
        assert np.max(np.abs(centre)) < max(0.01, 0.05 * r), \
            f"{vid}: {name} geometry is not centred on its pivot (centre {centre})"
        dia = max(hi[0] - lo[0], hi[1] - lo[1])
        assert abs(dia - 2 * r) <= 0.02 * 2 * r, \
            f"{vid}: {name} diameter {dia * 1000:.0f} mm vs published {2 * r * 1000:.0f} mm"
        checked += 1
    assert checked >= 2, f"{vid}: only {checked} wheels checked"


# --------------------------------------------------------------------------- LODs
@pytest.mark.parametrize("vid", IDS)
def test_lods_present_and_within_budget(vid):
    e = _entry(vid)
    lods = e["lods"]
    assert len(lods) == 3, f"{vid}: expected LOD0/1/2, got {len(lods)}"
    prev = None
    for lod in lods:
        p = REPO / lod["path"]
        assert p.exists(), f"{vid}: LOD{lod['level']} file missing: {p}"
        glb = Glb.load(p)
        tris = glb.triangles()
        assert abs(tris - lod["triangles"]) <= max(4, lod["triangles"] * 0.02), \
            f"{vid}: LOD{lod['level']} has {tris} triangles, catalog says {lod['triangles']}"
        if lod["budget"]:
            assert tris <= lod["budget"], \
                f"{vid}: LOD{lod['level']} {tris} triangles over budget {lod['budget']}"
        if prev is not None:
            assert tris < prev, f"{vid}: LOD{lod['level']} is not coarser than LOD{lod['level'] - 1}"
        prev = tris


def test_player_car_lod_budgets():
    e = _entry("fusion_hybrid")
    assert e["triangles"] <= 350_000, f"player car LOD0 {e['triangles']} > 350000"
    assert e["lods"][1]["triangles"] <= 60_000
    assert e["lods"][2]["triangles"] <= 8_000


def test_fleet_lod0_budget():
    for e in ENTRIES:
        if e["id"].startswith("fusion"):
            continue
        assert e["triangles"] <= 120_000, f"{e['id']} LOD0 {e['triangles']} > 120000"


# --------------------------------------------------------------------------- collision proxies
def _is_convex(pos: np.ndarray, idx: np.ndarray, tol: float) -> tuple[bool, float]:
    """Every vertex must lie on the inner side of every face plane.  Face normals are oriented away from the
    hull centroid rather than from the winding, so the test measures convexity itself and not the exporter's
    triangle order (which a separate manifold check covers)."""
    centre = pos.mean(axis=0)
    worst = 0.0
    for tri in idx:
        a, b, c = pos[tri[0]], pos[tri[1]], pos[tri[2]]
        n = np.cross(b - a, c - a)
        ln = np.linalg.norm(n)
        if ln < 1e-12:
            continue
        n = n / ln
        if np.dot(a - centre, n) < 0:
            n = -n
        d = float(np.dot(a, n))
        worst = max(worst, float((pos @ n - d).max()))
    return worst <= tol, worst


@pytest.mark.parametrize("vid", IDS)
def test_ucx_proxies_convex(vid, glbs):
    e, glb = _entry(vid), glbs[vid]
    proxies = [n for n in glb.nodes() if n.get("name", "").startswith("UCX_") and "mesh" in n]
    assert proxies, f"{vid}: no UCX_ collision proxies in the glb"
    assert sorted(n["name"] for n in proxies) == sorted(e["collision_proxies"]), \
        f"{vid}: catalog collision_proxies do not match the glb"
    for n in proxies:
        pos, idx = glb.mesh_positions_indices(n["mesh"])
        assert len(idx) >= 4, f"{vid}: {n['name']} has {len(idx)} triangles"
        ok, worst = _is_convex(pos, idx, CONVEX_TOL_M)
        assert ok, f"{vid}: {n['name']} is not convex (worst outside distance {worst * 1000:.2f} mm)"
        # glTF splits vertices per normal/UV, so weld by position before testing the edge manifold
        key = np.round(pos, 5)
        _, first, inv = np.unique(key, axis=0, return_index=True, return_inverse=True)
        w = inv[idx]
        edges: dict[tuple[int, int], int] = {}
        for tri in w:
            for k in range(3):
                e = (int(min(tri[k], tri[(k + 1) % 3])), int(max(tri[k], tri[(k + 1) % 3])))
                edges[e] = edges.get(e, 0) + 1
        open_edges = [e for e, cnt in edges.items() if cnt != 2]
        assert not open_edges, f"{vid}: {n['name']} is not a closed hull ({len(open_edges)} open edges)"


@pytest.mark.parametrize("vid", IDS)
def test_ucx_proxies_cover_the_body(vid, glbs):
    """The union of the proxies must enclose the vehicle's footprint to within 12 cm on every side."""
    e, glb = _entry(vid), glbs[vid]
    # the hull covers the collidable exterior; cabin furniture sits inside it by construction
    b = glb.node_world_bounds(skip=("UCX_", "Interior_", "Seat_", "Pedals", "Shifter", "SteeringWheel"))
    lo = np.min([v[0] for v in b.values()], axis=0)
    hi = np.max([v[1] for v in b.values()], axis=0)
    u = glb.node_world_bounds(skip=tuple(n for n in glb.node_names() if not n.startswith("UCX_")))
    ulo = np.min([v[0] for v in u.values()], axis=0)
    uhi = np.max([v[1] for v in u.values()], axis=0)
    slack = 0.12
    assert (ulo <= lo + slack).all() and (uhi >= hi - slack).all(), \
        f"{vid}: UCX bounds {ulo}..{uhi} do not cover the body {lo}..{hi}"


# --------------------------------------------------------------------------- damage regions
@pytest.mark.parametrize("vid", IDS)
def test_damage_region_attributes(vid, glbs):
    """``Body`` must carry the five ``_DMG_*`` custom vertex attributes."""
    glb = glbs[vid]
    by_name = {n.get("name", ""): n for n in glb.nodes()}
    assert "Body" in by_name, f"{vid}: no Body node"
    mesh = glb.json["meshes"][by_name["Body"]["mesh"]]
    attrs = set()
    for p in mesh["primitives"]:
        attrs |= set(p["attributes"])
    for region in ("FRONT", "REAR", "LEFT", "RIGHT", "ROOF"):
        assert f"_DMG_{region}" in attrs, f"{vid}: Body has no _DMG_{region} attribute (has {sorted(attrs)})"


@pytest.mark.parametrize("vid", IDS)
def test_damage_weights_in_range(vid, glbs):
    glb = glbs[vid]
    by_name = {n.get("name", ""): n for n in glb.nodes()}
    mesh = glb.json["meshes"][by_name["Body"]["mesh"]]
    for region in ("FRONT", "REAR", "LEFT", "RIGHT", "ROOF"):
        lo, hi = 1.0, 0.0
        for prim in mesh["primitives"]:          # one primitive per material; the region spans the whole panel
            vals = glb.accessor(prim["attributes"][f"_DMG_{region}"]).ravel()
            lo, hi = min(lo, float(vals.min())), max(hi, float(vals.max()))
        assert lo >= -1e-5 and hi <= 1 + 1e-5, f"{vid}: _DMG_{region} weights outside 0..1 ({lo}..{hi})"
        assert hi > 0.5, f"{vid}: _DMG_{region} never reaches the region (max {hi:.3f})"


# --------------------------------------------------------------------------- interior slots
@pytest.mark.parametrize("vid", [i for i in IDS if _entry(i)["contract_profile"] == "full"])
def test_gauge_and_screen_uvs_are_unit(vid, glbs):
    """``GAUGE_SPEED``, ``GAUGE_RPM`` and ``SCREEN_CENTER`` faces must have UVs spanning exactly 0..1."""
    e, glb = _entry(vid), glbs[vid]
    if "Interior_Dash" in e.get("contract_waivers", {}):
        pytest.skip("Interior_Dash waived for this vehicle class")
    by_name = {n.get("name", ""): n for n in glb.nodes()}
    assert "Interior_Dash" in by_name
    mesh = glb.json["meshes"][by_name["Interior_Dash"]["mesh"]]
    mats = glb.json["materials"]
    seen = {}
    for prim in mesh["primitives"]:
        name = mats[prim["material"]].get("name", "") if "material" in prim else ""
        if name not in ("GAUGE_SPEED", "GAUGE_RPM", "SCREEN_CENTER"):
            continue
        uv = glb.accessor(prim["attributes"]["TEXCOORD_0"])
        seen[name] = (uv.min(axis=0), uv.max(axis=0))
    for slot in ("GAUGE_SPEED", "GAUGE_RPM", "SCREEN_CENTER"):
        assert slot in seen, f"{vid}: Interior_Dash has no {slot} primitive"
        lo, hi = seen[slot]
        assert np.allclose(lo, 0.0, atol=1e-4) and np.allclose(hi, 1.0, atol=1e-4), \
            f"{vid}: {slot} UVs span {lo}..{hi}, must be exactly 0..1"


@pytest.mark.parametrize("vid", [i for i in IDS if _entry(i)["contract_profile"] == "full"])
def test_plate_face_uvs_are_unit(vid, glbs):
    e, glb = _entry(vid), glbs[vid]
    if "Plate_R" in e.get("contract_waivers", {}):
        pytest.skip("Plate_R waived")
    by_name = {n.get("name", ""): n for n in glb.nodes()}
    mesh = glb.json["meshes"][by_name["Plate_R"]["mesh"]]
    mats = glb.json["materials"]
    found = False
    for prim in mesh["primitives"]:
        if "material" not in prim or mats[prim["material"]].get("name") != "PLATE_FACE":
            continue
        uv = glb.accessor(prim["attributes"]["TEXCOORD_0"])
        assert np.allclose(uv.min(axis=0), 0.0, atol=1e-4) and np.allclose(uv.max(axis=0), 1.0, atol=1e-4), \
            f"{vid}: PLATE_FACE UVs span {uv.min(axis=0)}..{uv.max(axis=0)}"
        found = True
    assert found, f"{vid}: Plate_R has no PLATE_FACE primitive"


# --------------------------------------------------------------------------- pivots of opening panels
@pytest.mark.parametrize("vid", [i for i in IDS if _entry(i)["contract_profile"] == "full"])
def test_door_pivots_on_the_hinge_edge(vid, glbs):
    """Each door's origin must lie on its own leading (hinge) edge, not at the vehicle origin."""
    e, glb = _entry(vid), glbs[vid]
    wm = glb.world_matrices()
    waived = set(e.get("contract_waivers", {}))
    checked = 0
    for i, n in enumerate(glb.nodes()):
        name = n.get("name", "")
        if not name.startswith("Door_") or "mesh" not in n or name in waived:
            continue
        t = wm[i][:3, 3]
        pivot = np.array([t[0], -t[2], t[1]])
        lo, hi = glb.mesh_bounds_local(n["mesh"])
        # the hinge is the panel's forward edge: local x_max must be ~0 (origin on the leading edge)
        assert abs(hi[0]) < 0.06, f"{vid}: {name} origin is {hi[0]:.3f} m from its leading edge"
        assert abs(pivot[1]) > 0.2, f"{vid}: {name} hinge is on the centreline (y = {pivot[1]:.3f})"
        checked += 1
    assert checked >= 2, f"{vid}: only {checked} doors checked"


@pytest.mark.parametrize("vid", [i for i in IDS if _entry(i)["contract_profile"] == "full"])
def test_steering_wheel_axis(vid, glbs):
    e, glb = _entry(vid), glbs[vid]
    if "SteeringWheel" in e.get("contract_waivers", {}):
        pytest.skip("SteeringWheel waived")
    wm = glb.world_matrices()
    by_name = {n.get("name", ""): i for i, n in enumerate(glb.nodes())}
    i = by_name["SteeringWheel"]
    m = wm[i]
    # export_yup rewrites every local frame by C = [[1,0,0],[0,0,1],[0,-1,0]], so the object's Blender-local
    # +Z (the column axis) becomes the glTF node's local +Y, i.e. column 1 of its world matrix.
    axis = m[:3, 1] / np.linalg.norm(m[:3, 1])
    # the column must point forward and downward: +X and -Y in glTF (Y-up)
    assert axis[0] > 0.1, f"{vid}: steering column axis {axis} does not point forward"
    assert axis[1] < -0.1, f"{vid}: steering column axis {axis} does not tilt downward"
    tilt = math.degrees(math.atan2(-axis[1], axis[0]))
    # a car's column is ~20-25 deg below horizontal, a bus or a cab-over truck 55-70 deg
    assert 12.0 <= tilt <= 80.0, f"{vid}: steering column is {tilt:.1f} deg below horizontal"
    lo, hi = glb.mesh_bounds_local(glb.nodes()[i]["mesh"])
    dia = max(hi[0] - lo[0], hi[1] - lo[1])
    assert 0.30 <= dia <= 0.52, f"{vid}: steering wheel diameter {dia * 1000:.0f} mm is not road-car sized"


# --------------------------------------------------------------------------- fleet completeness
def test_fleet_covers_adr009():
    """Every body ADR-009 lists must be present in the catalog."""
    want = {
        "fusion_hybrid": "player car",
        "camry_taxi_yellow": "Toyota Camry cab",
        "rav4_fhv": "Toyota RAV4 FHV",
        "nv200_taxi": "Nissan NV200 taxi",
        "explorer_nypd": "Ford Explorer NYPD",
        "suburban_black_car": "Chevrolet Suburban black car",
        "nova_lfs_mta": "Nova Bus LFS",
        "xd60_sbs": "New Flyer XD60 articulated",
        "mci_j4500_coach": "MCI coach",
        "seagrave_engine_fdny": "Seagrave FDNY engine",
        "seagrave_tower_fdny": "Seagrave FDNY tower ladder",
        "ambulance_type1_fdny": "Type I ambulance",
        "isuzu_npr_box": "Isuzu NPR box truck",
        "mack_lr_dsny": "Mack LR sanitation truck",
        "sprinter_van": "Sprinter van",
        "transit_van": "Transit van",
        "freightliner_stepvan": "Freightliner step van",
        "usps_llv": "USPS LLV",
        "coned_utility_truck": "Con Edison utility truck",
        "school_bus_bluebird": "Blue Bird school bus",
        "dollar_van": "dollar van",
        "citibike_cruiser": "Citi Bike",
        "arrow_ebike": "Arrow delivery e-bike",
        "moped_scooter": "moped",
        "pedicab": "pedicab",
        "horse_carriage": "horse carriage",
    }
    missing = {k: v for k, v in want.items() if k not in IDS}
    assert not missing, f"fleet missing: {missing}"


def test_player_car_liveries():
    liveries = {e["livery"] for e in ENTRIES if e["id"].startswith("fusion")}
    assert {"player_grey", "yellow_taxi", "black_car", "green_boro_taxi"} <= liveries, \
        f"player-car liveries present: {sorted(liveries)}"


def test_taxi_roof_slot_on_medallion_liveries(glbs):
    for vid in IDS:
        e = _entry(vid)
        if e["livery"] not in ("yellow_taxi", "green_boro_taxi"):
            continue
        assert "TAXI_ROOF" in glbs[vid].material_names(), f"{vid}: no TAXI_ROOF medallion slot"
        assert "TAXI_ROOF" in glbs[vid].node_names(), f"{vid}: no TAXI_ROOF node"


def test_emergency_light_slots(glbs):
    for vid in ("explorer_nypd", "seagrave_engine_fdny", "seagrave_tower_fdny"):
        if vid not in IDS:
            continue
        mats = glbs[vid].material_names()
        assert {"LIGHT_EMERGENCY_R", "LIGHT_EMERGENCY_B"} <= mats, \
            f"{vid}: emergency light slots missing ({sorted(m for m in mats if 'EMERG' in m)})"


def test_bus_destination_sign_slots(glbs):
    for vid in ("nova_lfs_mta", "xd60_sbs"):
        if vid not in IDS:
            continue
        names = glbs[vid].node_names()
        assert {"SIGN_FRONT", "SIGN_SIDE", "SIGN_REAR"} <= names, \
            f"{vid}: destination sign slots missing"


def test_waivers_have_reasons():
    for e in ENTRIES:
        for name, reason in e.get("contract_waivers", {}).items():
            assert isinstance(reason, str) and len(reason) > 10, \
                f"{e['id']}: waiver for {name} has no explanation"


def test_asset_extras_present(glbs):
    for vid, glb in glbs.items():
        extras = glb.json.get("asset", {}).get("extras", {})
        payload = extras.get("nycsim")
        if isinstance(payload, str):
            payload = json.loads(payload)
        assert payload, f"{vid}: no asset.extras.nycsim (DATA_CONTRACTS §13)"
        assert payload.get("schema_version") == 1
        assert payload.get("units") == "metres"
