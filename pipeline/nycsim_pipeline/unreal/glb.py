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
