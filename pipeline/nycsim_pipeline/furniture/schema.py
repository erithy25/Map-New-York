"""Schema of ``tiles/{tile}/props.parquet`` (DATA_CONTRACTS §8 + the catalog's documented extension columns).

§8 names ``prop_id, kind, x, y, z, heading, variant, text, source, dataset_id, species, dbh_cm, height_m``.
``catalog.catalog_json()["extensions_to_data_contracts_s8"]`` adds ``height_source, capacity, z_source, attrs``
and the tiling columns ``tile, tx, ty`` (the same convention the buildings stage uses in §5.2).
"""
from __future__ import annotations

import numpy as np
import pyarrow as pa

SCHEMA_ID = "props/1"
SCHEMA_VERSION = 1

FIELDS: tuple[tuple[str, pa.DataType], ...] = (
    ("prop_id", pa.int64()),
    ("kind", pa.int16()),
    ("x", pa.float64()),
    ("y", pa.float64()),
    ("z", pa.float32()),
    ("heading", pa.float32()),
    ("variant", pa.int16()),
    ("text", pa.string()),
    ("source", pa.int8()),
    ("dataset_id", pa.string()),
    ("species", pa.string()),
    ("dbh_cm", pa.float32()),
    ("height_m", pa.float32()),
    ("height_source", pa.int8()),
    ("capacity", pa.int16()),
    ("z_source", pa.int8()),
    ("attrs", pa.string()),
    ("tile", pa.string()),
    ("tx", pa.int32()),
    ("ty", pa.int32()),
)

NUMPY_DTYPE: dict[str, str] = {
    "prop_id": "int64", "kind": "int16", "x": "float64", "y": "float64", "z": "float32", "heading": "float32",
    "variant": "int16", "source": "int8", "dbh_cm": "float32", "height_m": "float32", "height_source": "int8",
    "capacity": "int16", "z_source": "int8", "tx": "int32", "ty": "int32",
}
STRING_COLUMNS = ("text", "dataset_id", "species", "attrs", "tile")


def arrow_schema(extra_meta: dict[str, str] | None = None) -> pa.Schema:
    meta = {b"nycsim.schema": SCHEMA_ID.encode(), b"nycsim.schema_version": str(SCHEMA_VERSION).encode()}
    if extra_meta:
        meta.update({k.encode(): v.encode() for k, v in extra_meta.items()})
    return pa.schema([pa.field(n, t, nullable=n in STRING_COLUMNS) for n, t in FIELDS], metadata=meta)


def empty_columns(n: int) -> dict[str, np.ndarray | list]:
    """Column dict with the neutral value of every field, ready to be filled by a dataset loader."""
    cols: dict[str, np.ndarray | list] = {}
    for name, _t in FIELDS:
        if name in STRING_COLUMNS:
            cols[name] = [""] * n
        elif name in ("z", "height_m", "dbh_cm"):
            cols[name] = np.full(n, np.nan, dtype=np.float32)
        elif name == "heading":
            cols[name] = np.full(n, np.nan, dtype=np.float32)
        else:
            cols[name] = np.zeros(n, dtype=NUMPY_DTYPE[name])
    return cols
