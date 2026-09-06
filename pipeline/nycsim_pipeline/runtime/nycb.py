"""NYCB container format (DATA_CONTRACTS §15) — writer and reader.

Layout (all little-endian, natural C alignment as a C++17 compiler lays the structs out
without ``#pragma pack``; every offset in the index is absolute from the start of the file):

    header  {char magic[4] = "NYCB"; uint32 version = 1; uint32 section_count; uint64 index_offset}
            sizeof == 24 (4 bytes of padding after section_count so index_offset is 8-aligned)
    sections ... each section's data starts on an 8-byte boundary
    index   array[section_count] of {char name[16]; uint64 offset; uint64 size; uint32 element_size; uint32 element_count}
            sizeof == 40, located at header.index_offset

Section names are at most 15 bytes (NUL padded). Element records are numpy structured dtypes
built with ``align=True`` so ``element_size`` equals the C++ ``sizeof`` of the equivalent struct
(including tail padding). Strings live in a section named ``strtab``: a NUL-separated blob of UTF-8
strings, referenced from other sections by ``uint32`` byte offsets into that blob (offset 0 is always
the empty string). ``element_size`` of ``strtab`` is 1 and ``element_count`` is the blob length.

The reader in this module is the reference implementation used by the round-trip tests; the C++
reader (``core/io/NycbReader.h``) must read the same bytes. ``describe_layout`` emits a JSON-able
description of every field offset so the C++ side can be checked against it mechanically.
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping

import numpy as np

log = logging.getLogger("nycsim.runtime.nycb")

MAGIC = b"NYCB"
VERSION = 1
SECTION_NAME_BYTES = 16
ALIGN = 8

HEADER_DTYPE = np.dtype(
    [("magic", "S4"), ("version", "<u4"), ("section_count", "<u4"), ("index_offset", "<u8")], align=True
)
INDEX_DTYPE = np.dtype(
    [("name", f"S{SECTION_NAME_BYTES}"), ("offset", "<u8"), ("size", "<u8"), ("element_size", "<u4"), ("element_count", "<u4")],
    align=True,
)
assert HEADER_DTYPE.itemsize == 24, HEADER_DTYPE.itemsize
assert INDEX_DTYPE.itemsize == 40, INDEX_DTYPE.itemsize


class NycbError(RuntimeError):
    """Malformed container or invalid write request."""


def aligned_dtype(fields: list[tuple[str, str] | tuple[str, str, tuple[int, ...]]]) -> np.dtype:
    """Build a little-endian, naturally aligned structured dtype from ``(name, numpy-type[, shape])`` tuples."""
    return np.dtype(fields, align=True)


class StringTable:
    """Deduplicating NUL-separated string blob. Offset 0 is the empty string."""

    def __init__(self) -> None:
        self._offsets: dict[str, int] = {"": 0}
        self._chunks: list[bytes] = [b"\0"]
        self._size = 1

    def add(self, s: str | None) -> int:
        if s is None:
            s = ""
        s = str(s)
        off = self._offsets.get(s)
        if off is not None:
            return off
        data = s.encode("utf-8") + b"\0"
        off = self._size
        self._offsets[s] = off
        self._chunks.append(data)
        self._size += len(data)
        return off

    def add_many(self, strings: Iterable[str | None]) -> np.ndarray:
        return np.fromiter((self.add(s) for s in strings), dtype="<u4")

    def blob(self) -> bytes:
        return b"".join(self._chunks)

    def __len__(self) -> int:
        return self._size


@dataclass(frozen=True)
class SectionInfo:
    name: str
    offset: int
    size: int
    element_size: int
    element_count: int


def _check_name(name: str) -> bytes:
    b = name.encode("ascii")
    if not b or len(b) >= SECTION_NAME_BYTES:
        raise NycbError(f"section name must be 1..{SECTION_NAME_BYTES - 1} ASCII bytes: {name!r}")
    if b"\0" in b:
        raise NycbError("section name contains NUL")
    return b


class NycbWriter:
    """Collects sections and writes them in one pass. Sections keep insertion order."""

    def __init__(self) -> None:
        self._sections: list[tuple[str, bytes, int, int]] = []
        self._names: set[str] = set()
        self.strings = StringTable()

    def add_array(self, name: str, arr: np.ndarray) -> None:
        """Add a structured (or plain) numpy array; ``element_size`` = ``arr.dtype.itemsize``."""
        _check_name(name)
        if name in self._names:
            raise NycbError(f"duplicate section {name!r}")
        if arr.dtype.byteorder == ">":
            raise NycbError("big-endian arrays are not allowed")
        arr = np.ascontiguousarray(arr)
        if arr.ndim != 1:
            raise NycbError(f"section {name!r}: array must be 1-D, got shape {arr.shape}")
        self._sections.append((name, arr.tobytes(), int(arr.dtype.itemsize), int(arr.shape[0])))
        self._names.add(name)

    def add_bytes(self, name: str, data: bytes, element_size: int = 1) -> None:
        _check_name(name)
        if name in self._names:
            raise NycbError(f"duplicate section {name!r}")
        if element_size <= 0 or len(data) % element_size:
            raise NycbError(f"section {name!r}: size {len(data)} is not a multiple of element_size {element_size}")
        self._sections.append((name, bytes(data), element_size, len(data) // element_size))
        self._names.add(name)

    def add_strtab(self) -> None:
        """Append the string table (call after every ``strings.add``)."""
        self.add_bytes("strtab", self.strings.blob(), 1)

    def write(self, path: str | os.PathLike[str]) -> SectionInfo | None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        index = np.zeros(len(self._sections), dtype=INDEX_DTYPE)
        pos = HEADER_DTYPE.itemsize
        blobs: list[tuple[int, bytes]] = []
        for i, (name, data, esz, cnt) in enumerate(self._sections):
            pad = (-pos) % ALIGN
            pos += pad
            index[i]["name"] = _check_name(name)
            index[i]["offset"] = pos
            index[i]["size"] = len(data)
            index[i]["element_size"] = esz
            index[i]["element_count"] = cnt
            blobs.append((pad, data))
            pos += len(data)
        pad_index = (-pos) % ALIGN
        index_offset = pos + pad_index
        header = np.zeros(1, dtype=HEADER_DTYPE)
        header[0]["magic"] = MAGIC
        header[0]["version"] = VERSION
        header[0]["section_count"] = len(self._sections)
        header[0]["index_offset"] = index_offset
        with open(tmp, "wb") as f:
            f.write(header.tobytes())
            for pad, data in blobs:
                if pad:
                    f.write(b"\0" * pad)
                f.write(data)
            if pad_index:
                f.write(b"\0" * pad_index)
            f.write(index.tobytes())
        os.replace(tmp, path)
        log.info("wrote %s: %d sections, %d bytes", path, len(self._sections), index_offset + index.nbytes)
        return None

    def section_names(self) -> list[str]:
        return [s[0] for s in self._sections]


class NycbReader:
    """Memory-mapped reader. ``read(name, dtype)`` validates ``element_size`` against ``dtype.itemsize``."""

    def __init__(self, path: str | os.PathLike[str]) -> None:
        self.path = Path(path)
        self._mm = np.memmap(self.path, dtype=np.uint8, mode="r")
        if self._mm.size < HEADER_DTYPE.itemsize:
            raise NycbError(f"{self.path}: too small for a header")
        hdr = np.frombuffer(self._mm[: HEADER_DTYPE.itemsize].tobytes(), dtype=HEADER_DTYPE)[0]
        if bytes(hdr["magic"]) != MAGIC:
            raise NycbError(f"{self.path}: bad magic {bytes(hdr['magic'])!r}")
        if int(hdr["version"]) != VERSION:
            raise NycbError(f"{self.path}: unsupported version {int(hdr['version'])}")
        n = int(hdr["section_count"])
        off = int(hdr["index_offset"])
        end = off + n * INDEX_DTYPE.itemsize
        if end > self._mm.size:
            raise NycbError(f"{self.path}: index [{off},{end}) beyond file size {self._mm.size}")
        idx = np.frombuffer(self._mm[off:end].tobytes(), dtype=INDEX_DTYPE)
        self.sections: dict[str, SectionInfo] = {}
        for row in idx:
            name = bytes(row["name"]).split(b"\0", 1)[0].decode("ascii")
            info = SectionInfo(name, int(row["offset"]), int(row["size"]), int(row["element_size"]), int(row["element_count"]))
            if info.offset + info.size > self._mm.size:
                raise NycbError(f"{self.path}: section {name!r} beyond end of file")
            if info.element_size * info.element_count != info.size:
                raise NycbError(f"{self.path}: section {name!r} size mismatch")
            self.sections[name] = info
        self.version = int(hdr["version"])

    def raw(self, name: str) -> bytes:
        info = self._info(name)
        return self._mm[info.offset : info.offset + info.size].tobytes()

    def read(self, name: str, dtype: np.dtype) -> np.ndarray:
        info = self._info(name)
        if dtype.itemsize != info.element_size:
            raise NycbError(f"{self.path}: section {name!r} element_size {info.element_size} != dtype itemsize {dtype.itemsize}")
        return np.frombuffer(self.raw(name), dtype=dtype)

    def strings(self) -> bytes:
        return self.raw("strtab") if "strtab" in self.sections else b"\0"

    def string_at(self, offset: int, blob: bytes | None = None) -> str:
        blob = self.strings() if blob is None else blob
        if offset < 0 or offset >= len(blob):
            raise NycbError(f"string offset {offset} outside strtab of {len(blob)} bytes")
        end = blob.index(b"\0", offset)
        return blob[offset:end].decode("utf-8")

    def _info(self, name: str) -> SectionInfo:
        try:
            return self.sections[name]
        except KeyError:
            raise NycbError(f"{self.path}: no section {name!r}; have {sorted(self.sections)}") from None

    def close(self) -> None:
        del self._mm


def describe_layout(dtypes: Mapping[str, np.dtype]) -> dict:
    """JSON-able description of each section's record layout (field, offset, size, numpy type)."""
    out: dict = {
        "container": {
            "header": _fields(HEADER_DTYPE),
            "index_entry": _fields(INDEX_DTYPE),
            "endianness": "little",
            "alignment": "natural C alignment; sections start on 8-byte boundaries",
        },
        "sections": {},
    }
    for name, dt in dtypes.items():
        out["sections"][name] = _fields(dt)
    return out


def _fields(dt: np.dtype) -> dict:
    fields = []
    for fname in dt.names or ():
        fdt, off = dt.fields[fname][:2]
        fields.append({"name": fname, "offset": int(off), "size": int(fdt.itemsize), "type": str(fdt.base) if fdt.shape else str(fdt), "shape": list(fdt.shape)})
    return {"sizeof": int(dt.itemsize), "fields": fields}


def write_layout(path: str | os.PathLike[str], dtypes: Mapping[str, np.dtype]) -> None:
    with open(path, "w") as f:
        json.dump(describe_layout(dtypes), f, indent=1)
