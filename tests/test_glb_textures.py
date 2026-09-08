"""Moving embedded glTF images out of the binary chunk without touching the geometry.

The measurement that made this necessary: across the 541 non-tile ``.glb`` files this project
exports, 2.950 GB of image data is 2,847 references to 486 distinct images -- 2.610 GB, 88.5 %,
byte-for-byte duplicate.  One 2 K leather normal map is written into forty-one vehicles.

What these tests hold is the part that can go wrong silently.  Deleting an image's buffer view
shifts every later one, so a rewrite that renumbers four of the five places a buffer view can be
referenced produces a file that opens, reports the right node names, and draws nothing.
"""
from __future__ import annotations

import json
import struct
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "blender" / "common"))

import glb_textures as gt  # noqa: E402

JPEG = b"\xff\xd8\xff\xe0" + b"leather-normal-map" * 6
PNG = b"\x89PNG\r\n\x1a\n" + b"roughness" * 5


def _glb(path: Path, doc: dict, binary: bytes) -> Path:
    """Write a GLB by hand, so the reader under test is not checked against its own writer."""
    body = json.dumps(doc, separators=(",", ":")).encode()
    body += b" " * (-len(body) % 4)
    blob = binary + b"\0" * (-len(binary) % 4)
    total = 12 + 8 + len(body) + 8 + len(blob)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        f.write(struct.pack("<III", 0x46546C67, 2, total))
        f.write(struct.pack("<II", len(body), 0x4E4F534A))
        f.write(body)
        f.write(struct.pack("<II", len(blob), 0x004E4942))
        f.write(blob)
    return path


def _car(path: Path, *, extra_view: dict | None = None) -> tuple[Path, bytes]:
    """A file shaped like a vehicle export: positions, indices, two images, one shared payload."""
    positions = struct.pack("<9f", *[float(i) for i in range(9)])
    indices = struct.pack("<3H", 0, 1, 2) + b"\0\0"          # padded to 4
    binary = positions + indices + JPEG + PNG
    off_pos = 0
    off_idx = len(positions)
    off_jpg = off_idx + len(indices)
    off_png = off_jpg + len(JPEG)
    views = [
        {"buffer": 0, "byteOffset": off_pos, "byteLength": len(positions)},
        {"buffer": 0, "byteOffset": off_idx, "byteLength": 6},
        {"buffer": 0, "byteOffset": off_jpg, "byteLength": len(JPEG)},
        {"buffer": 0, "byteOffset": off_png, "byteLength": len(PNG)},
    ]
    doc = {
        "asset": {"version": "2.0"},
        "buffers": [{"byteLength": len(binary)}],
        "bufferViews": views,
        "accessors": [
            {"bufferView": 0, "componentType": 5126, "count": 3, "type": "VEC3"},
            {"bufferView": 1, "componentType": 5123, "count": 3, "type": "SCALAR"},
        ],
        "images": [{"name": "Leather026_2K_normal", "bufferView": 2, "mimeType": "image/jpeg"},
                   {"name": "Leather026_2K_roughness", "bufferView": 3, "mimeType": "image/png"}],
        "meshes": [{"primitives": [{"attributes": {"POSITION": 0}, "indices": 1}]}],
        "nodes": [{"name": "Body", "mesh": 0}],
    }
    if extra_view is not None:
        doc.update(extra_view)
    _glb(path, doc, binary)
    return path, binary


def test_a_rewritten_file_reads_the_same_geometry(tmp_path: Path) -> None:
    path, _ = _car(tmp_path / "fusion_hybrid.glb")
    before = gt.read_glb(path)
    record = gt.rewrite_file(path)
    after = gt.read_glb(path)

    assert record["images"] == 2
    assert record["bytes_after"] < record["bytes_before"]
    # the two image views are gone and the two geometry views renumbered from 0
    assert len(after.json["bufferViews"]) == 2
    assert [a["bufferView"] for a in after.json["accessors"]] == [0, 1]
    assert after.json["buffers"][0]["byteLength"] == len(after.bin)
    for i in range(len(before.json["accessors"])):
        assert gt._accessor_bytes(before, i) == gt._accessor_bytes(after, i), f"accessor {i} moved"
    # and the images now name files that hold exactly the bytes they replaced
    uris = [im["uri"] for im in after.json["images"]]
    assert all(u.startswith("textures/") for u in uris)
    assert (path.parent / uris[0]).read_bytes() == JPEG
    assert (path.parent / uris[1]).read_bytes() == PNG
    assert after.json["asset"]["extras"]["external_images"] == 2


def test_one_image_shared_by_two_files_is_written_once(tmp_path: Path) -> None:
    """The whole point: 41 vehicles, one leather map."""
    a, _ = _car(tmp_path / "camry_taxi_yellow.glb")
    b, _ = _car(tmp_path / "camry_black_car.glb")
    gt.rewrite_file(a)
    second = gt.rewrite_file(b)

    assert second["written"] == [], "the second file rewrote images the first had already written"
    assert sorted(p.name for p in (tmp_path / "textures").iterdir()) == sorted(second["reused"])
    assert len(list((tmp_path / "textures").iterdir())) == 2
    ua = [im["uri"] for im in gt.read_glb(a).json["images"]]
    ub = [im["uri"] for im in gt.read_glb(b).json["images"]]
    assert ua == ub, "two files holding the same image must name the same file"


def test_a_buffer_view_something_else_reads_stays_where_it_is(tmp_path: Path) -> None:
    """Sharing one view between an image and an accessor is legal glTF; dropping it would take
    the accessor's bytes with it, so such an image is left embedded rather than guessed at."""
    path, _ = _car(tmp_path / "odd.glb")
    doc = gt.read_glb(path)
    doc.json["accessors"].append({"bufferView": 2, "componentType": 5121, "count": 4, "type": "SCALAR"})
    gt.write_glb(path, doc)

    gt.rewrite_file(path)
    after = gt.read_glb(path)
    assert after.json["images"][0].get("bufferView") is not None, "the shared view was removed"
    assert after.json["images"][1].get("uri"), "the unshared image should still have moved out"


def test_a_buffer_view_named_by_an_extension_is_renumbered_too(tmp_path: Path) -> None:
    """Renumbering the four places today's exporter puts a buffer view is not the same as
    renumbering every place one can be.  Draco stores its own, on the primitive."""
    path, binary = _car(tmp_path / "draco.glb")
    doc = gt.read_glb(path)
    doc.json["bufferViews"].append({"buffer": 0, "byteOffset": 0, "byteLength": 8})
    draco_index = len(doc.json["bufferViews"]) - 1
    doc.json["meshes"][0]["primitives"][0]["extensions"] = {
        "KHR_draco_mesh_compression": {"bufferView": draco_index, "attributes": {"POSITION": 0}}}
    gt.write_glb(path, doc)

    gt.rewrite_file(path)
    after = gt.read_glb(path)
    got = after.json["meshes"][0]["primitives"][0]["extensions"]["KHR_draco_mesh_compression"]
    assert got["bufferView"] == 2, "the Draco view kept an index that now points at other bytes"
    assert len(after.json["bufferViews"]) == 3


def test_a_file_with_nothing_embedded_is_left_alone(tmp_path: Path) -> None:
    path, _ = _car(tmp_path / "twice.glb")
    gt.rewrite_file(path)
    first = path.read_bytes()
    again = gt.rewrite_file(path)
    assert again["images"] == 0
    assert path.read_bytes() == first, "a second sweep must be a no-op, not a rewrite"


def test_the_chunks_are_padded_the_way_the_container_requires(tmp_path: Path) -> None:
    """glTF 2.0 4.4.2: the JSON chunk is padded with spaces and the binary chunk with zeros.  A
    chunk padded with the wrong filler is a file some readers reject."""
    path, _ = _car(tmp_path / "pad.glb")
    gt.rewrite_file(path)
    data = path.read_bytes()
    total = struct.unpack_from("<I", data, 8)[0]
    assert total == len(data)
    off = 12
    seen = []
    while off < total:
        length, kind = struct.unpack_from("<II", data, off)
        assert length % 4 == 0, "a chunk length must be a multiple of four"
        seen.append(kind)
        if kind == 0x4E4F534A:
            assert data[off + 8:off + 8 + length].rstrip(b" ").decode() == json.dumps(
                gt.read_glb(path).json, separators=(",", ":"), ensure_ascii=False)
        off += 8 + length
    assert seen == [0x4E4F534A, 0x004E4942]


def test_a_rewrite_that_cannot_be_verified_leaves_the_original(tmp_path: Path, monkeypatch) -> None:
    """The original is replaced only after the rewritten bytes have been read back and compared.
    A file this module cannot rewrite correctly is a file it must leave alone."""
    path, _ = _car(tmp_path / "guarded.glb")
    original = path.read_bytes()

    real = gt.externalise

    def broken(glb, directory="textures"):
        out, files = real(glb, directory=directory)
        out.bin = out.bin[:-4]          # geometry silently truncated
        return out, files

    monkeypatch.setattr(gt, "externalise", broken)
    with pytest.raises(gt.GlbError):
        gt.rewrite_file(path)
    assert path.read_bytes() == original


def test_the_package_ships_every_image_its_glbs_name(tmp_path: Path, monkeypatch) -> None:
    """The manifest is the only list of what the import needs.  A package built from the entries'
    ``src`` paths alone would deliver a mesh with nothing on it and no error to say so."""
    sys.path.insert(0, str(REPO_ROOT / "tools"))
    import package_content as pc

    monkeypatch.setattr(pc, "REPO_ROOT", tmp_path)
    glb = tmp_path / "blender_out" / "vehicles" / "camry_taxi_yellow.glb"
    tex = tmp_path / "blender_out" / "vehicles" / "textures" / "Leather026_2K_normal-abc123def456.jpg"
    for p, payload in ((glb, b"glb"), (tex, JPEG)):
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(payload)
    manifest = tmp_path / "data" / "processed" / "unreal_manifest.json"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps({
        "entries": [{"id": "glb:vehicles/camry_taxi_yellow.glb",
                     "src": "blender_out/vehicles/camry_taxi_yellow.glb",
                     "sidecars": ["blender_out/vehicles/textures/Leather026_2K_normal-abc123def456.jpg"]}],
        "tiles": {}}))

    files, note = pc.collect(manifest, None)
    got = {str(p.relative_to(tmp_path)) for p in files}
    assert "blender_out/vehicles/textures/Leather026_2K_normal-abc123def456.jpg" in got
    assert note["sidecar_references"] == 1 and note["sidecar_files"] == 1
    assert note["missing"] == []


def test_every_exported_glb_names_only_images_that_exist() -> None:
    """The state of the tree, not a synthetic one: after the sweep, no ``.glb`` under
    ``blender_out`` may name an image file that is not beside it."""
    blender_out = REPO_ROOT / "blender_out"
    if not blender_out.is_dir():
        pytest.skip("blender_out is not built in this checkout")
    from urllib.parse import unquote

    broken: list[str] = []
    checked = 0
    for path in blender_out.rglob("*.glb"):
        try:
            doc = gt.read_glb_json(path)
        except gt.GlbError as exc:                       # a truncated file is a different fault
            broken.append(f"{path}: {exc}")
            continue
        for image in doc.get("images") or []:
            uri = image.get("uri")
            if not uri or uri.startswith("data:"):
                continue
            checked += 1
            target = (path.parent / unquote(uri)).resolve()
            try:
                target.relative_to(path.parent.resolve())
            except ValueError:
                broken.append(f"{path}: {uri} climbs out of its own directory")
                continue
            if not target.is_file():
                broken.append(f"{path}: {uri} is not on disk")
    assert not broken, "\n".join(broken[:20])
    assert checked > 0, "no glb names an external image; the sweep has not run"
