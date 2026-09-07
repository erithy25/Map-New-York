"""Signage evidence: which buildings carry an illuminated sign, and what a sign is allowed to say.

Three separate questions, three separate sources, kept apart on purpose:

**1. Does this shopfront have a sign?**  ``has_storefront`` is real (MapPLUTO ``retailarea`` / ``comarea``, DCWP
licences, DOHMH permits, OSM ``shop``), and the facade stage already writes ``awning_text`` for every one of the
80,261 storefronts.  A shopfront with wording in ``awning_text`` gets a lit fascia band; one with an empty
``awning_text`` (a lobby, a garage door, a vacant unit) gets none.  Nothing new is asserted here.

**2. What does it say?**  ``awning_real`` splits the 80,261: 30,381 carry a **real** business name and 49,880 carry
the generic New York trade wording for their kind.  The kit exports one lit band per generic wording plus a blank
one, so a real-name shopfront gets the blank ``SIGN_FACE`` panel and the runtime binds its name from
``awning_text`` on the same ``bin``.  :func:`band_kind_for_text` is the exact map, driven by the text the data
already ships, so the legend on the geometry can never disagree with the legend in the table.

**3. Does this building carry a billboard or a screen?**  Two real sources, and no third:

* ``facade_class`` carries the ``billboard`` feature for the seven typologies that really carry bulletins in New
  York (industrial lofts, warehouses, daylight factories, corner taxpayers, self-storage, hotels, gas-station
  canopies).  That is inference under ADR-004, flagged ``FACADE_INFERRED`` like every other class feature, and the
  bulletin face placed on it is **blank vinyl**: the model says a bulletin is mounted here, never what it advertises.
* MapPLUTO ``zonedist1``-``zonedist4`` carry the zoning district of every lot.  **``C6-7T`` exists on exactly 59
  lots in the whole city** (56 as ``zonedist1``, 3 as ``zonedist2``), every one of them inside a 570 x 320 m box on
  Broadway and Seventh Avenue between 42nd and 50th Streets - latitude 40.7565 to 40.7616, longitude -73.9867 to
  -73.9828.  The ``T`` suffix in the Special Midtown District is the Times Square core, where illuminated signs are
  not merely permitted but required.  That is a real, published, per-lot attribute of a dataset already in this
  repository, and it is the only source in this environment that says "there is a screen on this frontage".  The
  screens placed from it carry the LED pixel matrix and no content whatsoever.

The 292 OSM ``advertising=billboard`` nodes in the city are real too, and are already placed by the furniture stage
as free-standing props (``furniture.catalog`` kind 15); none of them is in Times Square, and this module does not
duplicate them.
"""
from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import polars as pl

from ..paths import PROCESSED, RAW
from . import enums as E
from .derive import CLASS, GENERIC_AWNING

log = logging.getLogger("nycsim.facade.signage")

PLUTO_CSV = RAW / "nyc_opendata" / "pluto.csv.gz"
PLUTO_CSV_PLAIN = RAW / "nyc_opendata" / "pluto.csv"
SIGN_ZONES = PROCESSED / "facade" / "sign_zones.parquet"

#: ``sign_zone`` values written per building.
SIGN_ZONE_NONE = 0
SIGN_ZONE_TIMES_SQUARE = 1

#: MapPLUTO zoning districts whose lots carry mandatory illuminated signage.  ``C6-7T`` is the Times Square core of
#: the Special Midtown District; the ``T`` suffix is what distinguishes it from the plain ``C6-7`` next to it.
#: Verified against the shipped PLUTO extract: 59 lots city-wide, every one of them in the Times Square bowtie.
TIMES_SQUARE_ZONING: tuple[str, ...] = ("C6-7T",)
ZONE_COLUMNS: tuple[str, ...] = ("zonedist1", "zonedist2", "zonedist3", "zonedist4")

#: Reverse of :data:`nycsim_pipeline.facade.derive.GENERIC_AWNING`: generic wording -> storefront kind index.
#: Only the kinds whose wording is non-empty appear, so a lobby or a vacant unit maps to nothing and gets no sign.
GENERIC_TEXT_TO_KIND: dict[str, int] = {v: k for k, v in GENERIC_AWNING.items() if v}

#: Sentinels used by the placement code in place of a storefront kind index.
BAND_NONE = -1        # no fascia band on this building at all
BAND_BLANK = -2       # a lit band with a blank face: the building has a real business name the runtime binds


def band_kind_for_text(text: str, awning_real: bool) -> int:
    """Which fascia sign band a storefront gets, from the ``awning_text`` the data already carries.

    A real business name gets the blank runtime-swappable panel (the kit cannot bake 30,381 legends); the generic
    NYC wording gets the band that carries exactly that wording; an empty ``awning_text`` gets no band.
    """
    t = (text or "").strip()
    if not t:
        return BAND_NONE
    if awning_real:
        return BAND_BLANK
    k = GENERIC_TEXT_TO_KIND.get(t)
    return BAND_NONE if k is None else int(k)


def band_kinds(texts, awning_real: np.ndarray) -> np.ndarray:
    """Vectorised :func:`band_kind_for_text` over a tile's ``awning_text`` column."""
    real = np.asarray(awning_real, dtype=bool)
    return np.asarray([band_kind_for_text(t, bool(r)) for t, r in zip(texts, real)], dtype=np.int8)


def has_billboard(facade_class: np.ndarray) -> np.ndarray:
    """Per building: does its facade class carry the ``billboard`` typology feature (``facade_classes.json``)?"""
    return CLASS.has_billboard[np.asarray(facade_class, dtype=np.int64)]


# ----------------------------------------------------------------------------------------------------------------------
def _pluto_path() -> Path:
    for p in (PLUTO_CSV_PLAIN, PLUTO_CSV):
        if p.exists() and p.stat().st_size > 0:
            return p
    raise FileNotFoundError(f"MapPLUTO csv missing: looked for {PLUTO_CSV_PLAIN} and {PLUTO_CSV}")


def build_sign_zones(out: Path = SIGN_ZONES) -> dict:
    """Derive ``bbl -> sign_zone`` from MapPLUTO's zoning districts and cache it as a small parquet."""
    path = _pluto_path()
    df = pl.read_csv(path, infer_schema_length=0, columns=["BBL", *ZONE_COLUMNS])
    zone = pl.lit(False)
    for c in ZONE_COLUMNS:
        zone = zone | pl.col(c).fill_null("").str.strip_chars().is_in(list(TIMES_SQUARE_ZONING))
    df = (df.with_columns([pl.col("BBL").cast(pl.Int64, strict=False).alias("bbl"),
                           zone.alias("_ts")])
            .filter(pl.col("bbl").is_not_null() & pl.col("_ts"))
            .select([pl.col("bbl"),
                     pl.lit(SIGN_ZONE_TIMES_SQUARE, dtype=pl.Int8).alias("sign_zone")])
            .unique(subset=["bbl"], keep="first")
            .sort("bbl"))
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(".tmp")
    df.write_parquet(tmp, compression="snappy")
    tmp.replace(out)
    summary = {"source": str(path.relative_to(path.parents[3])), "districts": list(TIMES_SQUARE_ZONING),
               "columns": list(ZONE_COLUMNS), "lots": int(df.height)}
    log.info("sign zones: %d lots in %s", df.height, ", ".join(TIMES_SQUARE_ZONING))
    return summary


_ZONE_CACHE: dict[str, np.ndarray] = {}


def sign_zone_bbls(path: Path = SIGN_ZONES) -> np.ndarray:
    """Sorted array of the BBLs whose lot carries mandatory illuminated signage; built on first use."""
    key = str(path)
    if key not in _ZONE_CACHE:
        if not path.exists():
            build_sign_zones(path)
        _ZONE_CACHE[key] = np.sort(pl.read_parquet(path)["bbl"].to_numpy().astype(np.int64))
    return _ZONE_CACHE[key]


def sign_zone_of(bbl: np.ndarray, path: Path = SIGN_ZONES) -> np.ndarray:
    """``sign_zone`` per building, from its lot's BBL."""
    keys = sign_zone_bbls(path)
    b = np.asarray(bbl, dtype=np.int64)
    out = np.zeros(len(b), dtype=np.int8)
    if len(keys) == 0 or len(b) == 0:
        return out
    pos = np.searchsorted(keys, b)
    hit = (pos < len(keys)) & (keys[np.minimum(pos, len(keys) - 1)] == b)
    out[hit] = SIGN_ZONE_TIMES_SQUARE
    return out


def refresh() -> None:
    """Drop the cached zone table (the tests rebuild it against a fixture)."""
    _ZONE_CACHE.clear()


def storefront_kind_name(idx: int) -> str:
    return E.STOREFRONT_KINDS[int(idx)]
