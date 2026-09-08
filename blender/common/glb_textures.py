"""Move embedded glTF images out of ``.glb`` files into a sibling ``textures/`` directory.

Blender's GLB exporter has no choice about embedding: a ``.glb`` carries exactly one binary
chunk, so every image a material references is written into that chunk in full.  When forty-one
vehicles share one 2 K leather normal map, that one file is written forty-one times.  Measured
across the 541 non-tile ``.glb`` files this project exports, 2.61 GB of 2.95 GB of image data is
a byte-for-byte duplicate of another file's -- 88.5 %.  The duplication does not stop at the disk
either: Unreal's glTF importer creates one ``UTexture2D`` per *reference*, so the cooked build
would carry 2,847 texture assets where 486 distinct images exist, and the streaming pool on an
8 GB card pays for every copy.

glTF 2.0 §3.10 lets an image name a file instead: ``images[i].uri`` replaces
``images[i].bufferView``.  This module rewrites an exported ``.glb`` that way -- it writes each
distinct image once, named ``<image name>-<first 12 hex of its sha256>.<ext>``, into a
``textures/`` directory beside the ``.glb``, and points the file's ``images`` at it.

The URIs are deliberately *relative and descending* (``textures/Leather026_2K_normal-….jpg``,
never ``../textures/…``).  A single shared directory at ``blender_out/textures`` would save a
further 10 MB across the six directories that hold these files -- and would require every
consumer to resolve a URI that climbs out of the ``.glb``'s own directory.  The spec permits it;
whether Unreal's Interchange translator permits it is not something this container can test, and
an untestable assumption is not worth 10 MB.

What the rewrite must not do is change a single byte of geometry.  Removing an image's buffer
view shifts the offset of every later one, so the module renumbers *every* ``"bufferView"`` key
in the whole JSON tree -- accessors, sparse accessor indices and values, Draco-compressed
primitives, any extension that follows the same key convention -- rather than the four sites that
happen to occur in today's files.  A buffer view that anything other than an externalised image
also reads is kept where it is.  ``verify()`` re-reads both files and compares the bytes of every
accessor and every image; ``rewrite_file`` calls it before it replaces the original.
"""

from __future__ import annotations

import hashlib
import json
import re
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

GLB_MAGIC = 0x46546C67
GLB_VERSION = 2
CHUNK_JSON = 0x4E4F534A
CHUNK_BIN = 0x004E4942

#: glTF 2.0 allows ``image/jpeg`` and ``image/png``; the KHR/EXT texture extensions add the rest.
EXTENSION_OF_MIME = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/ktx2": ".ktx2",
    "image/vnd-ms.dds": ".dds",
}

_SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")


class GlbError(RuntimeError):
    """A .glb this module cannot rewrite without risking the geometry in it."""


@dataclass
class Glb:
    """A parsed GLB: its JSON chunk and its binary chunk, nothing else."""

    json: dict
    bin: bytes

    def copy(self) -> "Glb":
        return Glb(json=json.loads(json.dumps(self.json)), bin=self.bin)


def read_glb(path: str | Path) -> Glb:
    data = Path(path).read_bytes()
    if len(data) < 12:
        raise GlbError(f"{path}: shorter than a GLB header")
    magic, version, total = struct.unpack_from("<III", data, 0)
    if magic != GLB_MAGIC:
        raise GlbError(f"{path}: not a GLB (magic {magic:#x})")
    if version != GLB_VERSION:
        raise GlbError(f"{path}: GLB version {version}, expected {GLB_VERSION}")
    if total != len(data):
        raise GlbError(f"{path}: header says {total} bytes, file is {len(data)}")
    js: dict | None = None
    binary = b""
    off = 12
    while off < total:
        if off + 8 > total:
            raise GlbError(f"{path}: truncated chunk header at {off}")
        length, kind = struct.unpack_from("<II", data, off)
        body = data[off + 8:off + 8 + length]
        if len(body) != length:
            raise GlbError(f"{path}: chunk at {off} claims {length} bytes, {len(body)} present")
        if kind == CHUNK_JSON and js is None:
            js = json.loads(body.decode("utf-8"))
        elif kind == CHUNK_BIN and not binary:
            binary = bytes(body)
        off += 8 + length + (-length % 4)
    if js is None:
        raise GlbError(f"{path}: no JSON chunk")
    return Glb(json=js, bin=binary)


def read_glb_json(path: str | Path) -> dict:
    """Just the JSON chunk.  A sweep over 2,839 tile files that only needs the ``images`` array
    has no business reading 13 GB of geometry to get at it."""
    with open(path, "rb") as f:
        head = f.read(12)
        if len(head) < 12:
            raise GlbError(f"{path}: shorter than a GLB header")
        magic, version, _total = struct.unpack("<III", head)
        if magic != GLB_MAGIC:
            raise GlbError(f"{path}: not a GLB (magic {magic:#x})")
        if version != GLB_VERSION:
            raise GlbError(f"{path}: GLB version {version}, expected {GLB_VERSION}")
        header = f.read(8)
        if len(header) < 8:
            raise GlbError(f"{path}: no JSON chunk")
        length, kind = struct.unpack("<II", header)
        if kind != CHUNK_JSON:
            raise GlbError(f"{path}: first chunk is {kind:#x}, not JSON")
        body = f.read(length)
    if len(body) != length:
        raise GlbError(f"{path}: JSON chunk claims {length} bytes, {len(body)} present")
    return json.loads(body.decode("utf-8"))


def write_glb(path: str | Path, glb: Glb) -> Path:
    """Write ``glb`` as a GLB.  The JSON chunk is padded with spaces and the binary chunk with
    zeros, which is what glTF 2.0 §4.4.2 requires -- a chunk padded with the wrong filler is a
    file some readers reject."""
    body = json.dumps(glb.json, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    body += b" " * (-len(body) % 4)
    chunks = [(CHUNK_JSON, body)]
    if glb.bin:
        binary = glb.bin + b"\0" * (-len(glb.bin) % 4)
        chunks.append((CHUNK_BIN, binary))
    total = 12 + sum(8 + len(c) for _, c in chunks)
    out = bytearray(struct.pack("<III", GLB_MAGIC, GLB_VERSION, total))
    for kind, chunk in chunks:
        out += struct.pack("<II", len(chunk), kind)
        out += chunk
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(bytes(out))
    return path


def _bufferview_sites(node, path: tuple = ()) -> Iterator[tuple[list, tuple]]:
    """Yield ``(container, path)`` for every ``"bufferView": <int>`` anywhere in the JSON tree.

    Walking the tree rather than naming the four places today's exporter puts them is the whole
    point: an extension that stores its own buffer view -- Draco, meshopt, structural metadata --
    uses the same key, and a renumbering that missed one would corrupt the file silently.
    """
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "bufferView" and isinstance(value, int):
                yield node, path + (key,)
            else:
                yield from _bufferview_sites(value, path + (key,))
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from _bufferview_sites(value, path + (index,))


def _is_image_site(path: tuple) -> bool:
    return len(path) == 3 and path[0] == "images" and isinstance(path[1], int)


def slug_for(name: str | None, digest: str, mime: str | None) -> str:
    """A file name that is stable across runs, unique per distinct image, and legible."""
    stem = _SAFE_NAME.sub("_", (name or "image").strip()) or "image"
    return f"{stem[:80]}-{digest[:12]}{EXTENSION_OF_MIME.get(mime or '', '.bin')}"


def embedded_images(glb: Glb) -> list[tuple[int, bytes, str | None, str | None]]:
    """``(image index, bytes, name, mimeType)`` for every image stored in the binary chunk."""
    views = glb.json.get("bufferViews", [])
    out = []
    for index, image in enumerate(glb.json.get("images", [])):
        view_index = image.get("bufferView")
        if view_index is None:
            continue
        view = views[view_index]
        start = view.get("byteOffset", 0)
        out.append((index, glb.bin[start:start + view["byteLength"]],
                    image.get("name"), image.get("mimeType")))
    return out


def externalise(glb: Glb, *, directory: str = "textures") -> tuple[Glb, dict[str, bytes]]:
    """Return a copy of ``glb`` whose images name files, plus the files to write.

    Images whose buffer view something else also reads are left embedded: sharing one view
    between an image and an accessor is legal, and dropping it would take the accessor's bytes
    with it.  Blender never emits that, which is exactly why it has to be checked rather than
    assumed.
    """
    out = glb.copy()
    images = out.json.get("images", [])
    if not images:
        return out, {}

    sites = list(_bufferview_sites(out.json))
    used_elsewhere: set[int] = set()
    image_views: dict[int, list[int]] = {}
    for container, path in sites:
        view_index = container["bufferView"]
        if _is_image_site(path):
            image_views.setdefault(view_index, []).append(path[1])
        else:
            used_elsewhere.add(view_index)

    views = out.json.get("bufferViews", [])
    if any(b.get("uri") for b in out.json.get("buffers", [])):
        raise GlbError("buffer with a uri: this is not a self-contained GLB")

    files: dict[str, bytes] = {}
    dropped: set[int] = set()
    for view_index, owners in image_views.items():
        if view_index in used_elsewhere:
            continue
        view = views[view_index]
        start = view.get("byteOffset", 0)
        payload = glb.bin[start:start + view["byteLength"]]
        if len(payload) != view["byteLength"]:
            raise GlbError(f"buffer view {view_index} runs past the binary chunk")
        digest = hashlib.sha256(payload).hexdigest()
        for image_index in owners:
            image = images[image_index]
            name = slug_for(image.get("name"), digest, image.get("mimeType"))
            files[name] = payload
            image.pop("bufferView", None)
            image.pop("mimeType", None)
            image["uri"] = f"{directory}/{name}" if directory else name
        dropped.add(view_index)

    if not dropped:
        return out, {}

    kept = [i for i in range(len(views)) if i not in dropped]
    remap = {old: new for new, old in enumerate(kept)}
    binary = bytearray()
    new_views = []
    for old in kept:
        view = dict(views[old])
        start = view.get("byteOffset", 0)
        payload = glb.bin[start:start + view["byteLength"]]
        if len(payload) != view["byteLength"]:
            raise GlbError(f"buffer view {old} runs past the binary chunk")
        binary += b"\0" * (-len(binary) % 4)   # every view stays 4-aligned, so every accessor does
        view["byteOffset"] = len(binary)
        binary += payload
        new_views.append(view)
    binary += b"\0" * (-len(binary) % 4)   # the container pads the chunk anyway; owning the
    out.json["bufferViews"] = new_views    # padding keeps buffer.byteLength exactly the chunk length
    out.bin = bytes(binary)
    buffers = out.json.get("buffers") or [{}]
    buffers[0]["byteLength"] = len(out.bin)
    out.json["buffers"] = buffers

    for container, path in _bufferview_sites(out.json):
        old = container["bufferView"]
        if old not in remap:
            raise GlbError(f"buffer view {old} still referenced at {path} after removal")
        container["bufferView"] = remap[old]

    extras = out.json.setdefault("asset", {}).setdefault("extras", {})
    extras["external_images"] = len(files)
    extras["external_image_dir"] = directory
    return out, files


def _accessor_bytes(glb: Glb, index: int) -> bytes:
    accessor = glb.json["accessors"][index]
    view_index = accessor.get("bufferView")
    if view_index is None:
        return b""
    view = glb.json["bufferViews"][view_index]
    start = view.get("byteOffset", 0) + accessor.get("byteOffset", 0)
    return glb.bin[start:start + view["byteLength"] - accessor.get("byteOffset", 0)]


def verify(before: Glb, after: Glb, files: dict[str, bytes]) -> None:
    """Raise unless ``after`` carries the same geometry and the same image bytes as ``before``."""
    if len(before.json.get("accessors", [])) != len(after.json.get("accessors", [])):
        raise GlbError("accessor count changed")
    for index in range(len(before.json.get("accessors", []))):
        old, new = _accessor_bytes(before, index), _accessor_bytes(after, index)
        if old != new:
            raise GlbError(f"accessor {index} reads {len(new)} bytes, was {len(old)}")
    before_images = {i: payload for i, payload, _, _ in embedded_images(before)}
    after_images = {i: payload for i, payload, _, _ in embedded_images(after)}
    for index, image in enumerate(after.json.get("images", [])):
        if index not in before_images:
            continue
        if index in after_images:
            # Left embedded on purpose -- something other than an image reads its buffer view --
            # so what has to hold is that its bytes did not move.
            if after_images[index] != before_images[index]:
                raise GlbError(f"image {index} stayed embedded and its bytes changed")
            continue
        uri = image.get("uri")
        if not uri:
            raise GlbError(f"image {index} lost its bufferView without gaining a uri")
        name = uri.rsplit("/", 1)[-1]
        if files.get(name) != before_images[index]:
            raise GlbError(f"image {index} ({uri}) does not match the bytes it replaced")


def rewrite_file(path: str | Path, *, directory: str = "textures") -> dict:
    """Externalise one ``.glb`` in place.  Returns a record of what moved.

    The original is only replaced once ``verify`` has re-read the rewritten bytes, so a file this
    module cannot rewrite correctly is a file it leaves alone.
    """
    path = Path(path)
    before = read_glb(path)
    after, files = externalise(before, directory=directory)
    record = {"path": str(path), "images": 0, "bytes_before": path.stat().st_size,
              "bytes_after": path.stat().st_size, "written": [], "reused": []}
    if not files:
        return record
    verify(before, after, files)
    target = path.parent / directory if directory else path.parent
    target.mkdir(parents=True, exist_ok=True)
    for name, payload in sorted(files.items()):
        destination = target / name
        if destination.exists() and destination.read_bytes() == payload:
            record["reused"].append(name)
            continue
        destination.write_bytes(payload)
        record["written"].append(name)
    tmp = path.with_suffix(path.suffix + ".rewrite")
    write_glb(tmp, after)
    reread = read_glb(tmp)
    verify(before, reread, files)
    tmp.replace(path)
    record["images"] = len(files)
    record["bytes_after"] = path.stat().st_size
    return record


def sweep(root: str | Path, *, directory: str = "textures", pattern: str = "**/*.glb") -> dict:
    """Externalise every ``.glb`` under ``root``.  Returns totals and the per-file records.

    Written to be re-runnable: a file whose images already name their own directory is untouched,
    and an image another file has already written is reused rather than rewritten, so a sweep that
    stops half way can simply be run again.
    """
    root = Path(root)
    records, before, after = [], 0, 0
    for path in sorted(root.glob(pattern)):
        try:
            record = rewrite_file(path, directory=directory)
        except GlbError as exc:
            records.append({"path": str(path), "error": str(exc)})
            continue
        before += record["bytes_before"]
        after += record["bytes_after"]
        if record["images"]:
            records.append(record)
    written = sorted({name for r in records for name in r.get("written", ())})
    return {"root": str(root), "files": len(records), "images_written": len(written),
            "bytes_before": before, "bytes_after": after, "records": records,
            "errors": [r for r in records if "error" in r]}


def main(argv: list[str] | None = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("root", help="directory to sweep, e.g. blender_out/vehicles")
    ap.add_argument("--pattern", default="**/*.glb")
    ap.add_argument("--directory", default="textures",
                    help="name of the sibling directory the images are written to")
    ap.add_argument("--report", type=Path, default=None, help="write the full record here as JSON")
    a = ap.parse_args(argv)
    out = sweep(a.root, directory=a.directory, pattern=a.pattern)
    if a.report:
        a.report.parent.mkdir(parents=True, exist_ok=True)
        a.report.write_text(json.dumps(out, indent=1))
    print(f"{out['files']} file(s) rewritten, {out['images_written']} image(s) written, "
          f"{out['bytes_before'] / 1e9:.2f} GB -> {out['bytes_after'] / 1e9:.2f} GB")
    for bad in out["errors"]:
        print(f"  ! {bad['path']}: {bad['error']}")
    return 1 if out["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
