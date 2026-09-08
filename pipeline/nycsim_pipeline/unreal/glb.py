"""Minimal glTF-binary (.glb) header/JSON reader (no dependencies) used to record asset metadata in the manifest."""
from __future__ import annotations

import json
import struct
from pathlib import Path
from typing import Any

GLB_MAGIC = 0x46546C67  # 'glTF'
CHUNK_JSON = 0x4E4F534A


class GlbError(ValueError):
    pass


def read_glb_json(path: Path) -> dict[str, Any]:
    """Return the JSON chunk of a .glb as a dict. Raises GlbError on a malformed container."""
    with open(path, "rb") as f:
        head = f.read(12)
        if len(head) < 12:
            raise GlbError(f"{path}: file shorter than a glb header")
        magic, version, length = struct.unpack("<III", head)
        if magic != GLB_MAGIC:
            raise GlbError(f"{path}: bad magic 0x{magic:08x}")
        if version != 2:
            raise GlbError(f"{path}: unsupported glTF version {version}")
        chunk_head = f.read(8)
        if len(chunk_head) < 8:
            raise GlbError(f"{path}: truncated first chunk header")
        chunk_len, chunk_type = struct.unpack("<II", chunk_head)
        if chunk_type != CHUNK_JSON:
            raise GlbError(f"{path}: first chunk is not JSON (0x{chunk_type:08x})")
        if chunk_len > length:
            raise GlbError(f"{path}: JSON chunk length {chunk_len} exceeds file length {length}")
        data = f.read(chunk_len)
        if len(data) < chunk_len:
            raise GlbError(f"{path}: truncated JSON chunk")
    try:
        return json.loads(data.decode("utf-8").rstrip("\x00 "))
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        raise GlbError(f"{path}: JSON chunk is not valid JSON: {e}") from e


def nycsim_extras(doc: dict[str, Any]) -> dict[str, Any]:
    """``asset.extras.nycsim`` (DATA_CONTRACTS §13); the Blender exporter stores it as a JSON string or dict."""
    extras = (doc.get("asset") or {}).get("extras") or {}
    v = extras.get("nycsim")
    if v is None:
        # the scene custom property path used by nycsim_bpy.export_glb (scene["nycsim"]) lands in scenes[].extras
        for sc in doc.get("scenes") or []:
            v = (sc.get("extras") or {}).get("nycsim")
            if v is not None:
                break
    if v is None:
        return {}
    if isinstance(v, str):
        try:
            v = json.loads(v)
        except json.JSONDecodeError:
            return {"raw": v}
    return v if isinstance(v, dict) else {"raw": v}


def glb_summary(path: Path) -> dict[str, Any]:
    """Counts + extras + node names that the UE import uses (LOD detection by ``_LOD1`` suffix)."""
    doc = read_glb_json(path)
    nodes = doc.get("nodes") or []
    meshes = doc.get("meshes") or []
    names = [n.get("name", "") for n in nodes]
    lod_names = sorted({n for n in names if "_LOD" in n})
    tri_estimate = 0
    accessors = doc.get("accessors") or []
    for m in meshes:
        for prim in m.get("primitives") or []:
            idx = prim.get("indices")
            if idx is not None and idx < len(accessors):
                tri_estimate += int(accessors[idx].get("count", 0)) // 3
            else:
                pos = (prim.get("attributes") or {}).get("POSITION")
                if pos is not None and pos < len(accessors):
                    tri_estimate += int(accessors[pos].get("count", 0)) // 3
    return {
        "nodes": len(nodes),
        "meshes": len(meshes),
        "materials": len(doc.get("materials") or []),
        "textures": len(doc.get("textures") or []),
        "animations": len(doc.get("animations") or []),
        "skins": len(doc.get("skins") or []),
        "triangles": tri_estimate,
        "lod_nodes": lod_names,
        "has_lod1": any(n.endswith("_LOD1") or "_LOD1" in n for n in names),
        "extras": nycsim_extras(doc),
    }


def _node_matrix(node: dict[str, Any]):
    """A node's local transform as a 4x4, from ``matrix`` or from TRS."""
    import numpy as np

    m = node.get("matrix")
    if m is not None and len(m) == 16:
        return np.asarray(m, dtype=np.float64).reshape(4, 4).T   # glTF stores column-major
    out = np.eye(4)
    s = node.get("scale")
    if s:
        out[:3, :3] = np.diag(np.asarray(s, dtype=np.float64))
    r = node.get("rotation")
    if r:
        x, y, z, w = (float(v) for v in r)
        rot = np.array([
            [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
            [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
            [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
        ])
        out[:3, :3] = rot @ out[:3, :3]
    t = node.get("translation")
    if t:
        out[:3, 3] = np.asarray(t, dtype=np.float64)
    return out


def glb_bounds(path: Path, *, skip_lods: bool = True) -> dict[str, list[float]] | None:
    """The model's axis-aligned bounds in **NYC_TM local metres**, or ``None`` if it has no geometry.

    Read from the ``POSITION`` accessors' own ``min``/``max``, which glTF requires, so no binary
    chunk has to be decoded: the 8 corners of each primitive's box are pushed through its node's
    accumulated transform and unioned. The result is converted out of glTF's Y-up frame back into
    the project's Z-up NYC_TM axes (``x_tm = x_gltf``, ``y_tm = -z_gltf``, ``z_tm = y_gltf``), which
    is the inverse of what the Blender exporter applied.

    ``skip_lods`` leaves out nodes whose name marks them as a lower level of detail, so a model's
    bounds are the bounds of the thing itself.
    """
    import numpy as np

    doc = read_glb_json(path)
    nodes = doc.get("nodes") or []
    meshes = doc.get("meshes") or []
    accessors = doc.get("accessors") or []
    if not nodes or not meshes:
        return None

    mesh_boxes: dict[int, tuple[np.ndarray, np.ndarray]] = {}
    for i, m in enumerate(meshes):
        lo = np.full(3, np.inf)
        hi = np.full(3, -np.inf)
        for prim in m.get("primitives") or []:
            a = (prim.get("attributes") or {}).get("POSITION")
            if a is None or a >= len(accessors):
                continue
            acc = accessors[a]
            amin, amax = acc.get("min"), acc.get("max")
            if not (amin and amax and len(amin) >= 3):
                continue
            lo = np.minimum(lo, np.asarray(amin[:3], dtype=np.float64))
            hi = np.maximum(hi, np.asarray(amax[:3], dtype=np.float64))
        if np.isfinite(lo).all():
            mesh_boxes[i] = (lo, hi)

    scenes = doc.get("scenes") or []
    scene = doc.get("scene", 0)
    roots = scenes[scene].get("nodes", []) if scene < len(scenes) else list(range(len(nodes)))

    lo = np.full(3, np.inf)
    hi = np.full(3, -np.inf)
    seen: set[int] = set()

    def walk(index: int, parent) -> None:
        import numpy as np

        nonlocal lo, hi
        if index in seen or index >= len(nodes):
            return
        seen.add(index)
        node = nodes[index]
        world = parent @ _node_matrix(node)
        mesh = node.get("mesh")
        name = str(node.get("name", ""))
        skip = skip_lods and ("_LOD" in name and not name.endswith("_LOD0"))
        if mesh is not None and mesh in mesh_boxes and not skip:
            b0, b1 = mesh_boxes[mesh]
            corners = np.array([[x, y, z] for x in (b0[0], b1[0]) for y in (b0[1], b1[1])
                                for z in (b0[2], b1[2])])
            pts = (world[:3, :3] @ corners.T).T + world[:3, 3]
            lo = np.minimum(lo, pts.min(axis=0))
            hi = np.maximum(hi, pts.max(axis=0))
        for child in node.get("children") or []:
            walk(int(child), world)

    eye = __import__("numpy").eye(4)
    for r in roots:
        walk(int(r), eye)
    if not np.isfinite(lo).all():
        return None
    # glTF Y-up -> NYC_TM Z-up
    tm_lo = np.array([lo[0], -hi[2], lo[1]])
    tm_hi = np.array([hi[0], -lo[2], hi[1]])
    return {"min": [round(float(v), 4) for v in tm_lo], "max": [round(float(v), 4) for v in tm_hi]}
