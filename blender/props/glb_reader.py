"""Dependency-free GLB reader used by ``tests/test_props.py`` (no bpy, no pygltflib).

Reads the JSON and BIN chunks of a binary glTF 2.0 file and decodes accessors, so the tests can assert on what
was actually exported — node graph and MSFT_lod links, material slots and factors, UV ranges, triangle counts —
rather than on what the generator believed it wrote.
"""
from __future__ import annotations

import json
import struct
from pathlib import Path

GLB_MAGIC = 0x46546C67
CHUNK_JSON = 0x4E4F534A
CHUNK_BIN = 0x004E4942

COMPONENT = {5120: ("b", 1), 5121: ("B", 1), 5122: ("h", 2), 5123: ("H", 2), 5125: ("I", 4), 5126: ("f", 4)}
NCOMP = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT2": 4, "MAT3": 9, "MAT4": 16}


class GlbError(RuntimeError):
    pass


class Glb:
    """One parsed .glb: ``.json`` is the glTF document, ``.bin`` the binary buffer."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        data = self.path.read_bytes()
        if len(data) < 20:
            raise GlbError(f"{self.path}: too short to be a GLB ({len(data)} bytes)")
        magic, version, length = struct.unpack_from("<III", data, 0)
        if magic != GLB_MAGIC:
            raise GlbError(f"{self.path}: not a GLB (magic {magic:#x})")
        if version != 2:
            raise GlbError(f"{self.path}: GLB version {version}, expected 2")
        if length != len(data):
            raise GlbError(f"{self.path}: header length {length} != file size {len(data)}")
        off, js, binc = 12, None, b""
        while off + 8 <= length:
            clen, ctype = struct.unpack_from("<II", data, off)
            chunk = data[off + 8: off + 8 + clen]
            if ctype == CHUNK_JSON:
                js = json.loads(chunk.decode("utf-8"))
            elif ctype == CHUNK_BIN:
                binc = chunk
            off += 8 + clen
        if js is None:
            raise GlbError(f"{self.path}: no JSON chunk")
        self.json = js
        self.bin = binc

    # ---------------------------------------------------------------- accessors
    def accessor(self, index: int) -> list[tuple]:
        acc = self.json["accessors"][index]
        fmt, size = COMPONENT[acc["componentType"]]
        n = NCOMP[acc["type"]]
        count = acc["count"]
        if "bufferView" not in acc:
            return [tuple([0] * n)] * count
        bv = self.json["bufferViews"][acc["bufferView"]]
        base = bv.get("byteOffset", 0) + acc.get("byteOffset", 0)
        stride = bv.get("byteStride") or n * size
        out = []
        for i in range(count):
            o = base + i * stride
            out.append(struct.unpack_from("<" + fmt * n, self.bin, o))
        return out

    # ---------------------------------------------------------------- graph
    def nodes_by_name(self) -> dict[str, int]:
        return {n.get("name"): i for i, n in enumerate(self.json.get("nodes", [])) if n.get("name")}

    def scene_roots(self) -> list[int]:
        sc = self.json.get("scenes", [])
        if not sc:
            return []
        return list(sc[self.json.get("scene", 0)].get("nodes", []))

    def descendants(self, node_index: int) -> list[int]:
        out, stack = [], [node_index]
        while stack:
            i = stack.pop()
            out.append(i)
            stack.extend(self.json["nodes"][i].get("children", []))
        return out

    def meshes_under(self, node_index: int) -> list[int]:
        return [self.json["nodes"][i]["mesh"] for i in self.descendants(node_index) if "mesh" in self.json["nodes"][i]]

    def material_names(self) -> list[str]:
        return [m.get("name", "") for m in self.json.get("materials", [])]

    def material_by_name(self, name: str) -> dict | None:
        for m in self.json.get("materials", []):
            if m.get("name") == name:
                return m
        return None

    # ---------------------------------------------------------------- geometry
    def triangle_count(self, mesh_indices) -> int:
        total = 0
        for mi in mesh_indices:
            for prim in self.json["meshes"][mi]["primitives"]:
                mode = prim.get("mode", 4)
                if mode != 4:
                    continue
                if "indices" in prim:
                    total += self.json["accessors"][prim["indices"]]["count"] // 3
                else:
                    total += self.json["accessors"][prim["attributes"]["POSITION"]]["count"] // 3
        return total

    def bounds(self, mesh_indices) -> tuple[list[float], list[float]]:
        lo = [float("inf")] * 3
        hi = [float("-inf")] * 3
        for mi in mesh_indices:
            for prim in self.json["meshes"][mi]["primitives"]:
                acc = self.json["accessors"][prim["attributes"]["POSITION"]]
                if "min" in acc and "max" in acc:
                    mn, mx = acc["min"], acc["max"]
                else:
                    pts = self.accessor(prim["attributes"]["POSITION"])
                    mn = [min(p[k] for p in pts) for k in range(3)]
                    mx = [max(p[k] for p in pts) for k in range(3)]
                lo = [min(lo[k], mn[k]) for k in range(3)]
                hi = [max(hi[k], mx[k]) for k in range(3)]
        return lo, hi

    def primitives_with_material(self, name: str) -> list[dict]:
        mats = [i for i, m in enumerate(self.json.get("materials", [])) if m.get("name") == name]
        out = []
        for mesh in self.json.get("meshes", []):
            for prim in mesh["primitives"]:
                if prim.get("material") in mats:
                    out.append(prim)
        return out

    def uv_range(self, prim: dict) -> tuple[tuple[float, float], tuple[float, float]]:
        uvs = self.accessor(prim["attributes"]["TEXCOORD_0"])
        return ((min(u for u, _ in uvs), min(v for _, v in uvs)),
                (max(u for u, _ in uvs), max(v for _, v in uvs)))

    def asset_extras(self) -> dict:
        extras = self.json.get("asset", {}).get("extras", {})
        raw = extras.get("nycsim")
        if isinstance(raw, str):
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                return {}
        return raw or {}


def linear_to_srgb_hex(rgb) -> str:
    """glTF baseColorFactor (linear) -> '#RRGGBB' in sRGB, the space the palette constants are written in."""
    out = []
    for c in rgb[:3]:
        c = max(0.0, min(1.0, float(c)))
        s = 12.92 * c if c <= 0.0031308 else 1.055 * (c ** (1 / 2.4)) - 0.055
        out.append(int(round(s * 255.0)))
    return "#{:02X}{:02X}{:02X}".format(*out)
