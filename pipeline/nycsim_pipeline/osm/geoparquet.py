"""Streaming (Geo)Parquet writer shared by the osm / furniture / transit stages.

Writes GeoParquet 1.0 metadata (``geo`` key, WKB geometry, NYC_TM PROJJSON CRS) plus the
``nycsim.schema`` key required by docs/DATA_CONTRACTS.md. Rows are appended in batches so a
1.5 M-polygon layer never has to be held in memory at once.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import shapely

from ..crs import NYC_TM


def nyc_tm_projjson() -> dict:
    return NYC_TM.to_json_dict()


def geo_metadata(geometry_column: str, geometry_types: Sequence[str], bbox: Sequence[float] | None) -> bytes:
    meta = {
        "version": "1.0.0",
        "primary_column": geometry_column,
        "columns": {
            geometry_column: {
                "encoding": "WKB",
                "geometry_types": sorted(set(geometry_types)),
                "crs": nyc_tm_projjson(),
            }
        },
    }
    if bbox is not None and np.all(np.isfinite(bbox)):
        meta["columns"][geometry_column]["bbox"] = [float(v) for v in bbox]
    return json.dumps(meta).encode()


class ParquetBatchWriter:
    """Append-only Parquet writer with optional GeoParquet metadata.

    ``schema`` is a pyarrow schema. Call :meth:`write` with a dict of equal-length columns
    (lists / numpy arrays; the geometry column as WKB ``bytes``), then :meth:`close`.
    """

    def __init__(self, path: Path, schema: pa.Schema, *, schema_name: str, geometry_column: str | None = "geometry",
                 extra_metadata: dict[str, str] | None = None, compression: str = "snappy") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.schema_name = schema_name
        self.geometry_column = geometry_column if (geometry_column and geometry_column in schema.names) else None
        self.extra_metadata = dict(extra_metadata or {})
        self._schema = schema
        self._writer: pq.ParquetWriter | None = None
        self._compression = compression
        self.rows = 0
        self.geometry_types: set[str] = set()
        self.bbox = np.array([np.inf, np.inf, -np.inf, -np.inf])
        self._tmp = self.path.with_suffix(self.path.suffix + ".tmp")

    def _open(self) -> pq.ParquetWriter:
        if self._writer is None:
            self._writer = pq.ParquetWriter(str(self._tmp), self._schema, compression=self._compression)
        return self._writer

    def write(self, columns: dict[str, Any]) -> int:
        n = None
        for k in self._schema.names:
            if k not in columns:
                raise KeyError(f"missing column {k!r} for {self.path.name}")
            m = len(columns[k])
            if n is None:
                n = m
            elif m != n:
                raise ValueError(f"column {k!r} has {m} rows, expected {n} ({self.path.name})")
        if not n:
            return 0
        if self.geometry_column is not None:
            wkb = columns[self.geometry_column]
            geoms = shapely.from_wkb(list(wkb))
            b = shapely.bounds(geoms)
            ok = np.isfinite(b).all(axis=1)
            if ok.any():
                self.bbox[0] = min(self.bbox[0], b[ok, 0].min())
                self.bbox[1] = min(self.bbox[1], b[ok, 1].min())
                self.bbox[2] = max(self.bbox[2], b[ok, 2].max())
                self.bbox[3] = max(self.bbox[3], b[ok, 3].max())
            for t in np.unique(shapely.get_type_id(geoms)):
                self.geometry_types.add(_GEOM_TYPE_NAMES.get(int(t), "Geometry"))
        table = pa.table({k: _to_arrow(columns[k], self._schema.field(k).type) for k in self._schema.names}, schema=self._schema)
        self._open().write_table(table)
        self.rows += n
        return n

    def close(self) -> Path:
        if self._writer is None:
            # produce an empty but valid file with the schema
            self._open()
        meta = dict(self._schema.metadata or {})
        meta[b"nycsim.schema"] = self.schema_name.encode()
        for k, v in self.extra_metadata.items():
            meta[k.encode()] = str(v).encode()
        if self.geometry_column is not None:
            meta[b"geo"] = geo_metadata(self.geometry_column, sorted(self.geometry_types) or ["Geometry"],
                                        self.bbox if self.rows else None)
        self._writer.add_key_value_metadata({k.decode(): v.decode() for k, v in meta.items()})
        self._writer.close()
        self._writer = None
        self._tmp.replace(self.path)
        return self.path


_GEOM_TYPE_NAMES = {0: "Point", 1: "LineString", 2: "LinearRing", 3: "Polygon", 4: "MultiPoint", 5: "MultiLineString",
                    6: "MultiPolygon", 7: "GeometryCollection"}


def _to_arrow(values: Any, typ: pa.DataType) -> pa.Array:
    if isinstance(values, pa.Array):
        return values.cast(typ) if values.type != typ else values
    if isinstance(values, np.ndarray) and not pa.types.is_list(typ) and not pa.types.is_binary(typ) and not pa.types.is_string(typ) and not pa.types.is_large_string(typ):
        return pa.array(values, type=typ, from_pandas=True)
    return pa.array(list(values), type=typ, from_pandas=True)


def write_table(path: Path, table: pa.Table, *, schema_name: str, geometry_column: str | None = "geometry",
                extra_metadata: dict[str, str] | None = None) -> Path:
    """Write a whole pyarrow table in one go with the same metadata conventions."""
    w = ParquetBatchWriter(path, table.schema, schema_name=schema_name, geometry_column=geometry_column, extra_metadata=extra_metadata)
    w.write({k: table.column(k) for k in table.schema.names})
    return w.close()


def read_geo_bbox(path: Path) -> list[float] | None:
    md = pq.read_schema(str(path)).metadata or {}
    geo = md.get(b"geo")
    if not geo:
        return None
    g = json.loads(geo)
    col = g["columns"][g["primary_column"]]
    return col.get("bbox")
