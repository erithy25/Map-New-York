"""Tests for landmark agent B's models (bridges, tunnels, the World Trade Center, the harbour, parks, Coney Island).

For every landmark in the B set:

* ``blender_out/landmarks/<id>.glb`` exists and parses as glTF 2.0;
* it carries the NYCSim asset extras (DATA_CONTRACTS §13): ``landmark_id``, ``origin_tm`` inside the project scope,
  ``heading_deg``, ``height_m`` and a non-empty ``fidelity_statement``;
* a LOD1 export ``<id>_lod1.glb`` exists, parses, and has at most 45 % of the LOD0 triangle count;
* the model's triangle count is inside the budget the build brief sets (900k for the Brooklyn Bridge, 400k for the
  other bridges, 250k for everything else);
* and the **measured geometry** matches the published dimension **within 1 %**: the model's overall height, and —
  for every bridge with named towers or piers — the distance between those support nodes' vertex centroids.

The measurements are taken from the exported glb, not from the build scripts, so they check what was actually
written.  glTF is exported Y-up (``export_yup=True``), so a glTF position (X, Y, Z) maps back to the model's
(east, north, up) = (X, -Z, Y).

Runs without bpy: the glb is decoded with pygltflib + numpy.  Skips (does not fail) when the outputs have not been
built yet.
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
SCOPE = (-30000.0, -27000.0, 24000.0, 27000.0)      # nycsim_pipeline.crs SCOPE_* bbox
MHW = 0.70                                          # b_common.MHW_ABOVE_NAVD88_M

pygltflib = pytest.importorskip("pygltflib")

_COMPONENT = {5120: ("b", 1), 5121: ("B", 1), 5122: ("h", 2), 5123: ("H", 2), 5125: ("I", 4), 5126: ("f", 4)}
_COUNT = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}

# ---------------------------------------------------------------------------------------------- expectations
#
# max_z   : (expected height above the frame origin, tolerance %) or (expected, tolerance %, node-name prefix).
#           With a prefix only that node's vertices are measured, which is how a landmark whose published figure
#           belongs to one element (the High Bridge's deck, Bethesda's angel, Central Park's wall) is checked
#           without the model's tallest piece of furniture — a lamp standard, a railing — standing in for it.
# span    : (node-name prefix A, node-name prefix B, expected separation in metres, tolerance %)
# budget  : maximum LOD0 triangles
#
# For bridges the frame origin is at NAVD88 0.0, so a tower quoted "above mean high water" reaches
# published_height + 0.70 m in model coordinates.  For buildings the origin is the LiDAR ground.

BUDGET_BRIDGE = 400_000
BUDGET_OTHER = 250_000

LANDMARKS: dict[str, dict] = {
    "b_brooklyn_bridge": dict(budget=900_000, max_z=(84.3 + MHW, 1.0),
                              spans=[("tower_bk", "tower_mn", 486.3, 1.0)]),
    "b_manhattan_bridge": dict(budget=BUDGET_BRIDGE, max_z=(106.68 + MHW, 1.0),
                               spans=[("tower_bk", "tower_mn", 451.1, 1.0)]),
    "b_williamsburg_bridge": dict(budget=BUDGET_BRIDGE, max_z=(102.11 + MHW, 1.0),
                                  spans=[("tower_mn", "tower_bk", 487.68, 1.0)]),
    "b_queensboro_bridge": dict(budget=BUDGET_BRIDGE, max_z=(106.68 + MHW, 1.5),
                                spans=[("qb_pier2", "qb_pier3", 192.0, 1.0),
                                       ("qb_pier1", "qb_pier2", 360.3, 1.0),
                                       ("qb_pier3", "qb_pier4", 300.0, 1.0)]),
    "b_george_washington_bridge": dict(budget=BUDGET_BRIDGE, max_z=(184.1 + MHW, 1.0),
                                       spans=[("tower_nj", "tower_ny", 1066.8, 1.0)]),
    "b_verrazzano_narrows": dict(budget=BUDGET_BRIDGE, max_z=(211.2 + MHW, 1.0),
                                 spans=[("tower_si", "tower_bk", 1298.4, 1.0)]),
    "b_rfk_triborough": dict(budget=BUDGET_BRIDGE, max_z=(96.01 + MHW, 1.5),
                             spans=[("sus_tower_qn", "sus_tower_wi", 420.62, 1.0)]),
    "b_throgs_neck": dict(budget=BUDGET_BRIDGE, max_z=(105.5 + MHW, 1.0),
                          spans=[("tower_qn", "tower_bx", 548.64, 1.0)]),
    "b_bronx_whitestone": dict(budget=BUDGET_BRIDGE, max_z=(114.9 + MHW, 1.0),
                               spans=[("tower_bx", "tower_qn", 701.04, 1.0)]),
    "b_hell_gate": dict(budget=BUDGET_BRIDGE, max_z=(92.96 + MHW, 1.0, "arch_rib"),
                        spans=[("tower_qn", "tower_wi", 329.47, 1.0)]),
    "b_high_bridge": dict(budget=BUDGET_OTHER, max_z=(42.06 + MHW, 1.0, "deck"), spans=[]),
    "b_pulaski": dict(budget=BUDGET_OTHER, max_z=(11.89 + MHW + 2.4, 1.0, "deck_slab"), spans=[]),
    "b_kosciuszko": dict(budget=BUDGET_OTHER, max_z=(27.43 + MHW + 3.0 + 91.4, 2.0), spans=[]),
    "b_roosevelt_island_tram": dict(budget=BUDGET_OTHER, max_z=(4.0 + 76.20, 1.0, "tower2_head"), spans=[]),
    "b_lincoln_tunnel_portals": dict(budget=BUDGET_OTHER, max_z=(5.0 + 44.2 + 5.4, 6.0), spans=[]),
    "b_holland_tunnel_portals": dict(budget=BUDGET_OTHER, max_z=(-2.0 + 39.3 + 5.4, 8.0), spans=[]),
    "b_queens_midtown_portals": dict(budget=BUDGET_OTHER, max_z=(3.0 + 33.3 + 5.4, 8.0), spans=[]),
    "b_hugh_carey_portals": dict(budget=BUDGET_OTHER, max_z=(3.0 + 32.8 + 5.4, 8.0), spans=[]),
    "b_one_world_trade_center": dict(budget=BUDGET_OTHER, max_z=(541.3, 1.0), spans=[]),
    "b_wtc_site": dict(budget=BUDGET_OTHER, max_z=(3.5 + 329.2 + 1.4, 1.0), spans=[]),
    "b_statue_of_liberty": dict(budget=BUDGET_OTHER, max_z=(3.0 + 92.99, 1.0), spans=[]),
    "b_ellis_island_main": dict(budget=BUDGET_OTHER, max_z=(30.5, 1.0, "tower0_cornice"), spans=[]),
    "b_governors_island": dict(budget=BUDGET_OTHER, max_z=(12.19, 1.0, "castle_williams_wall"), spans=[]),
    "b_washington_square_arch": dict(budget=BUDGET_OTHER, max_z=(23.47, 3.0, "wsa_atticcap"), spans=[]),
    "b_bethesda_terrace": dict(budget=BUDGET_OTHER, max_z=(7.92, 1.0, "angel_body"), spans=[]),
    "b_bow_bridge": dict(budget=BUDGET_OTHER, max_z=(20.9 + 2.3 + 1.5, 1.0, "deck"), spans=[]),
    "b_belvedere_castle": dict(budget=BUDGET_OTHER, max_z=(16.5, 1.0, "tower_belvedere"), spans=[]),
    "b_central_park_walls_gates": dict(budget=BUDGET_OTHER, max_z=(1.22, 1.0, "perimeter_wall"), spans=[]),
    "b_unisphere": dict(budget=BUDGET_OTHER, max_z=(42.67, 1.0, "globe_grid"), spans=[]),
    "b_grants_tomb": dict(budget=BUDGET_OTHER, max_z=(45.72, 2.0), spans=[]),
    "b_columbus_circle_monument": dict(budget=BUDGET_OTHER, max_z=(228.60 + 6.0, 1.0), spans=[]),
    "b_soldiers_sailors_arch": dict(budget=BUDGET_OTHER, max_z=(24.38, 3.0, "ssa_atticcap"), spans=[]),
    "b_prospect_park_boathouse": dict(budget=BUDGET_OTHER, max_z=(1.6 + 6.4 + 2.3 + 1.25, 2.0, "roof_bal"), spans=[]),
    "b_coney_island": dict(budget=BUDGET_OTHER, max_z=(79.86, 1.0, "parachute_jump_lattice"), spans=[]),
}

REQUIRED_EXTRAS = ("landmark_id", "origin_tm", "heading_deg", "height_m", "fidelity_statement")


class Glb:
    """Minimal glTF 2.0 binary reader: node graph, world matrices, positions and triangle counts."""

    def __init__(self, path: Path):
        self.path = path
        self.g = pygltflib.GLTF2().load(str(path))
        self.blob = self.g.binary_blob()

    # -------------------------------------------------------------- accessors
    def accessor(self, idx: int) -> np.ndarray:
        acc = self.g.accessors[idx]
        bv = self.g.bufferViews[acc.bufferView]
        fmt, size = _COMPONENT[acc.componentType]
        n = _COUNT[acc.type]
        start = (bv.byteOffset or 0) + (acc.byteOffset or 0)
        stride = bv.byteStride or size * n
        out = np.empty((acc.count, n), dtype=np.dtype(fmt))
        for i in range(acc.count):
            out[i] = struct.unpack_from("<" + fmt * n, self.blob, start + i * stride)
        return out

    # -------------------------------------------------------------- node graph
    def _node_matrix(self, node) -> np.ndarray:
        if node.matrix:
            return np.asarray(node.matrix, dtype=np.float64).reshape(4, 4).T
        m = np.eye(4)
        if node.scale:
            m[:3, :3] = m[:3, :3] @ np.diag(node.scale)
        if node.rotation:
            x, y, z, w = node.rotation
            r = np.array([
                [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])
            m[:3, :3] = r @ m[:3, :3]
        if node.translation:
            m[:3, 3] = node.translation
        return m

    def world_matrices(self) -> dict[int, np.ndarray]:
        out: dict[int, np.ndarray] = {}

        def walk(i: int, parent: np.ndarray) -> None:
            node = self.g.nodes[i]
            m = parent @ self._node_matrix(node)
            out[i] = m
            for c in node.children or []:
                walk(c, m)

        scene = self.g.scenes[self.g.scene or 0]
        for root in scene.nodes:
            walk(root, np.eye(4))
        return out

    def node_positions(self) -> dict[str, np.ndarray]:
        """Model-space (east, north, up) vertex arrays keyed by node name (glTF is Y-up)."""
        mats = self.world_matrices()
        out: dict[str, np.ndarray] = {}
        for i, node in enumerate(self.g.nodes):
            if node.mesh is None:
                continue
            pts = []
            for prim in self.g.meshes[node.mesh].primitives:
                p = self.accessor(prim.attributes.POSITION).astype(np.float64)
                h = np.column_stack([p, np.ones(len(p))])
                pts.append((mats[i] @ h.T).T[:, :3])
            if not pts:
                continue
            a = np.vstack(pts)
            model = np.column_stack([a[:, 0], -a[:, 2], a[:, 1]])
            name = node.name or f"node{i}"
            out[name] = np.vstack([out[name], model]) if name in out else model
        return out

    def triangles(self) -> int:
        n = 0
        for mesh in self.g.meshes:
            for prim in mesh.primitives:
                if prim.indices is not None:
                    n += self.g.accessors[prim.indices].count // 3
                else:
                    n += self.g.accessors[prim.attributes.POSITION].count // 3
        return n

    def extras(self) -> dict:
        raw = (self.g.scenes[self.g.scene or 0].extras or {}).get("nycsim")
        if raw is None:
            for node in self.g.nodes:
                if node.extras and "nycsim" in node.extras:
                    raw = node.extras["nycsim"]
                    break
        if raw is None and self.g.extras:
            raw = self.g.extras.get("nycsim")
        if isinstance(raw, str):
            return json.loads(raw)
        return raw or {}


def _glb(landmark_id: str, lod: int = 0) -> Glb:
    path = GLB_DIR / (f"{landmark_id}.glb" if lod == 0 else f"{landmark_id}_lod{lod}.glb")
    if not path.exists():
        pytest.skip(f"{path.relative_to(REPO)} not built")
    return Glb(path)


def _centroid(nodes: dict[str, np.ndarray], prefix: str) -> np.ndarray:
    hits = [v for k, v in nodes.items() if k.startswith(prefix)]
    assert hits, f"no node whose name starts with {prefix!r} (have: {sorted(nodes)[:12]} ...)"
    a = np.vstack(hits)
    return a.mean(axis=0)


IDS = sorted(LANDMARKS)


@pytest.mark.parametrize("landmark_id", IDS)
def test_glb_loads_and_carries_extras(landmark_id: str) -> None:
    g = _glb(landmark_id)
    assert g.g.asset.version == "2.0"
    assert g.triangles() > 0
    ex = g.extras()
    missing = [k for k in REQUIRED_EXTRAS if k not in ex]
    assert not missing, f"{landmark_id}: extras missing {missing}"
    assert ex["landmark_id"] == landmark_id
    x, y = ex["origin_tm"][0], ex["origin_tm"][1]
    assert SCOPE[0] <= x <= SCOPE[2] and SCOPE[1] <= y <= SCOPE[3], \
        f"{landmark_id}: origin_tm ({x:.1f}, {y:.1f}) outside the NYC_TM project scope"
    assert 0.0 <= float(ex["heading_deg"]) < 360.0
    assert len(ex["fidelity_statement"]) > 120, f"{landmark_id}: fidelity_statement is too short to be meaningful"
    assert float(ex["height_m"]) > 0.0


@pytest.mark.parametrize("landmark_id", IDS)
def test_triangle_budget(landmark_id: str) -> None:
    g = _glb(landmark_id)
    budget = LANDMARKS[landmark_id]["budget"]
    n = g.triangles()
    assert n <= budget, f"{landmark_id}: {n:,} triangles exceeds the {budget:,} budget"


@pytest.mark.parametrize("landmark_id", IDS)
def test_lod1_present_and_lighter(landmark_id: str) -> None:
    g0 = _glb(landmark_id)
    g1 = _glb(landmark_id, 1)
    n0, n1 = g0.triangles(), g1.triangles()
    assert n1 > 0
    assert n1 <= 0.45 * n0, f"{landmark_id}: LOD1 has {n1:,} triangles, more than 45 % of LOD0's {n0:,}"


@pytest.mark.parametrize("landmark_id", IDS)
def test_height_within_1_percent(landmark_id: str) -> None:
    """The model's highest point matches the published height (per-landmark tolerance; 1 % for the primary set)."""
    spec = LANDMARKS[landmark_id]["max_z"]
    expected, tol = spec[0], spec[1]
    prefix = spec[2] if len(spec) > 2 else None
    g = _glb(landmark_id)
    nodes = g.node_positions()
    assert nodes, f"{landmark_id}: no mesh nodes"
    if prefix:
        sel = [v for k, v in nodes.items() if k.startswith(prefix)]
        assert sel, f"{landmark_id}: no node whose name starts with {prefix!r} (have {sorted(nodes)[:12]} ...)"
        top = max(float(v[:, 2].max()) for v in sel)
        what = f"top of {prefix!r}"
    else:
        top = max(float(v[:, 2].max()) for v in nodes.values())
        what = "highest point"
    err = abs(top - expected) / expected * 100.0
    assert err <= tol, f"{landmark_id}: {what} {top:.2f} m vs expected {expected:.2f} m ({err:.2f} % > {tol} %)"


@pytest.mark.parametrize("landmark_id", [k for k in IDS if LANDMARKS[k]["spans"]])
def test_spans_within_1_percent(landmark_id: str) -> None:
    """Measured centre-to-centre distance between the named support nodes vs the published span."""
    g = _glb(landmark_id)
    nodes = g.node_positions()
    for a, b, expected, tol in LANDMARKS[landmark_id]["spans"]:
        ca = _centroid(nodes, a)
        cb = _centroid(nodes, b)
        d = float(math.hypot(cb[0] - ca[0], cb[1] - ca[1]))
        err = abs(d - expected) / expected * 100.0
        assert err <= tol, (f"{landmark_id}: {a} to {b} measures {d:.2f} m, published {expected:.2f} m "
                            f"({err:.2f} % > {tol} %)")


@pytest.mark.parametrize("landmark_id", IDS)
def test_catalog_entry(landmark_id: str) -> None:
    path = CATALOG / f"{landmark_id}.json"
    if not path.exists():
        pytest.skip(f"{path.relative_to(REPO)} not written")
    entry = json.load(open(path))
    assert entry["id"] == landmark_id
    assert entry["agent"] == "B"
    assert "lod0" in entry.get("lods", {})
    rec = entry["lods"]["lod0"]
    for k in ("path", "triangles", "bytes", "bounds", "sha256"):
        assert k in rec, f"{landmark_id}: catalog lod0 record missing {k}"
    assert (REPO / rec["path"]).exists()
    assert entry.get("fidelity_statement")


def test_every_b_script_has_a_landmark_entry() -> None:
    """Every ``blender/landmarks/b_<name>.py`` that is a landmark script is covered by this test module."""
    lib = {"b_common", "b_bridge_lib", "b_tunnel_lib", "b_park_lib", "b_align", "b_osm_extract", "b_build_all"}
    scripts = {p.stem for p in (REPO / "blender" / "landmarks").glob("b_*.py")} - lib
    assert scripts == set(LANDMARKS), (f"landmark scripts not covered: {sorted(scripts - set(LANDMARKS))}; "
                                       f"tested but missing: {sorted(set(LANDMARKS) - scripts)}")
