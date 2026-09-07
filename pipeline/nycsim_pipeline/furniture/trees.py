"""2015 Street Tree Census (``uvpi-gqnh``) -> tree props.

The census is a full field inventory: every row is a real tree at real coordinates with the species identified and
the trunk diameter measured at breast height (``tree_dbh``, inches). It also records ``status`` (Alive / Dead /
Stump), ``health``, stewardship and damage observations.

Dead trees and stumps are **excluded** from the props table (a stump is not a street tree and a standing dead tree
has no canopy); the counts of both are reported by :func:`load_trees` and printed in the build summary.

Height is not in the census and is estimated per species and DBH by :mod:`.allometry` (``height_source = 1``).

:class:`CensusHeights` publishes that estimated population as a distribution, for the one caller that has a real
tree and no evidence of its size at all — the OSM tree nodes, which carry a height on 1.6 % of rows and a trunk
diameter on none. See its docstring for why a draw from it is not the same claim as the census's own fallback.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import polars as pl

from ..crs import transformer
from ..paths import RAW
from . import allometry

log = logging.getLogger("nycsim.furniture.trees")

CSV = RAW / "nyc_opendata" / "street_trees_2015.csv"
SOURCE_ID = "street_trees_2015"

COLUMNS = ["tree_id", "tree_dbh", "stump_diam", "status", "health", "spc_latin", "spc_common",
           "latitude", "longitude", "borocode", "curb_loc", "sidewalk", "nta", "address"]

HEALTH_VARIANT = {"Good": 0, "Fair": 1, "Poor": 2}
HEALTH_UNKNOWN = 3


@dataclass(frozen=True)
class TreeCensus:
    df: pl.DataFrame              # alive trees only, with x/y (NYC_TM), dbh_cm, height_m
    n_total: int
    n_alive: int
    n_dead: int
    n_stump: int
    n_status_blank: int
    n_no_coord: int
    n_no_species: int
    n_no_dbh: int
    species_counts: list[tuple[str, str, int]]   # (latin, common, count) sorted desc


def load_trees(path: Path = CSV) -> TreeCensus:
    if not path.exists():
        # spent sources are gzipped in place to free disk (data/raw/nyc_opendata/README_COMPRESSED.md);
        # polars reads the archive directly, so the stage does not need 330 MB of scratch to re-run.
        gz = path.with_suffix(path.suffix + ".gz")
        if not gz.exists():
            raise FileNotFoundError(f"{path} missing; run: python -m nycsim_pipeline.download --id {SOURCE_ID}")
        log.info("%s is gzipped; reading %s directly", path.name, gz.name)
        path = gz
    df = pl.read_csv(path, columns=COLUMNS, infer_schema_length=0)
    n_total = df.height
    status = df["status"].fill_null("").str.strip_chars()
    n_alive = int((status == "Alive").sum())
    n_dead = int((status == "Dead").sum())
    n_stump = int((status == "Stump").sum())
    n_blank = n_total - n_alive - n_dead - n_stump
    log.info("street trees: %d rows -> alive %d, dead %d, stump %d, other/blank %d", n_total, n_alive, n_dead, n_stump, n_blank)

    alive = df.filter(status == "Alive").with_columns([
        pl.col("latitude").cast(pl.Float64, strict=False),
        pl.col("longitude").cast(pl.Float64, strict=False),
        pl.col("tree_dbh").cast(pl.Float64, strict=False),
        pl.col("tree_id").cast(pl.Int64, strict=False),
        pl.col("spc_latin").fill_null("").str.strip_chars(),
        pl.col("spc_common").fill_null("").str.strip_chars(),
        pl.col("health").fill_null("").str.strip_chars(),
    ])
    good = alive["latitude"].is_finite() & alive["longitude"].is_finite()
    n_no_coord = int((~good).sum())
    if n_no_coord:
        log.warning("%d alive trees without usable coordinates dropped", n_no_coord)
    alive = alive.filter(good)

    lon = alive["longitude"].to_numpy()
    lat = alive["latitude"].to_numpy()
    x, y = transformer("WGS84", "NYC_TM").transform(lon, lat)

    dbh_in = alive["tree_dbh"].fill_null(0.0).to_numpy()
    dbh_cm = allometry.dbh_inches_to_cm(dbh_in)
    n_no_dbh = int((dbh_in <= 0).sum())
    species = alive["spc_latin"].to_list()
    n_no_species = sum(1 for s in species if not s)
    height = allometry.height_array(species, dbh_cm)

    health = alive["health"].to_list()
    variant = np.array([HEALTH_VARIANT.get(h, HEALTH_UNKNOWN) for h in health], dtype=np.int16)

    out = pl.DataFrame({
        "tree_id": alive["tree_id"].fill_null(0).cast(pl.Int64),
        "x": np.asarray(x, dtype=np.float64),
        "y": np.asarray(y, dtype=np.float64),
        "species": species,
        "common": alive["spc_common"].to_list(),
        "dbh_cm": dbh_cm.astype(np.float32),
        "height_m": height.astype(np.float32),
        "variant": variant,
        "borocode": alive["borocode"].fill_null("").to_list(),
        "curb_loc": alive["curb_loc"].fill_null("").to_list(),
        "sidewalk": alive["sidewalk"].fill_null("").to_list(),
        "nta": alive["nta"].fill_null("").to_list(),
    })

    sp = (alive.select([pl.col("spc_latin").alias("latin"), pl.col("spc_common").alias("common")])
          .group_by(["latin", "common"]).len().sort("len", descending=True))
    species_counts = [(r["latin"], r["common"], int(r["len"])) for r in sp.iter_rows(named=True)]

    return TreeCensus(out, n_total, n_alive, n_dead, n_stump, n_blank, n_no_coord, n_no_species, n_no_dbh, species_counts)


# --------------------------------------------------------------------------------------- height distribution

MIN_TAXON_POOL = 30
"""Fewest census trees a species or genus needs before it gets its own height pool.

Below this the pool is a handful of individuals rather than a distribution, and drawing from it would put one
particular street tree's estimated height on an unrelated tree in a park.
"""

_GOLDEN = np.uint64(0x9E3779B97F4A7C15)


def _splitmix64(z: np.ndarray) -> np.ndarray:
    """SplitMix64 finalizer — a fixed, platform-independent integer hash (no RNG state, no Python ``hash()``)."""
    with np.errstate(over="ignore"):
        z = z + _GOLDEN
        z = (z ^ (z >> np.uint64(30))) * np.uint64(0xBF58476D1CE4E5B9)
        z = (z ^ (z >> np.uint64(27))) * np.uint64(0x94D049BB133111EB)
        return z ^ (z >> np.uint64(31))


def coordinate_uniform(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    """A deterministic uniform in [0, 1) per point, seeded only by its own NYC_TM position.

    Seeded by position rather than by row index so the value follows the *tree*: it is unchanged by row order,
    by how many trees the dedupe removed before it, and by re-running the stage. Coordinates are quantised to
    the millimetre so a float round-trip through parquet cannot move a tree into a different draw.
    """
    with np.errstate(over="ignore"):
        xi = np.rint(np.asarray(x, dtype=np.float64) * 1000.0).astype(np.int64).astype(np.uint64)
        yi = np.rint(np.asarray(y, dtype=np.float64) * 1000.0).astype(np.int64).astype(np.uint64)
        h = _splitmix64(_splitmix64(xi) ^ (yi * _GOLDEN))
    return (h >> np.uint64(11)).astype(np.float64) * (2.0 ** -53)


@dataclass(frozen=True)
class CensusHeights:
    """The height distribution of the census trees whose trunk diameter was actually measured.

    **What this is, stated precisely.** These are not measured heights: the census records no height, and every
    value here is :mod:`.allometry` applied to a *measured* DBH and an identified species (DEVIATIONS D2). So the
    pool is one inference deep already, and a draw from it is two. What makes it worth drawing from is that its
    input — 651,951 trunk diameters measured in the field — is real, and its shape is therefore the shape of the
    New York street tree population rather than of an assumption.

    **Why a draw rather than the census's own unknown-DBH fallback.** A census row with no DBH is usually a
    newly planted tree, so reading a missing diameter as a sapling is meaningful *there*. A missing ``height``
    tag in OpenStreetMap means only that no mapper measured one — 98.4 % of tree nodes have none — so carrying
    the sapling fallback across asserts "small" where the source says nothing at all, and asserts it in one
    direction 49,000 times. A draw asserts only what the census observed about the size of New York trees.

    **Why a draw rather than the median.** A single value makes every unknown tree identical, which reads as a
    plantation and is wrong in shape as well as per tree; the draw reproduces the population's spread, so
    aggregates over the world are right and only the per-tree assignment is fiction. Both are inferences and
    both are flagged ``height_source = 4``; the draw is the one whose error is spread rather than repeated.

    The draw is conditioned on the taxon wherever OSM names one, because a cherry is not an oak: a lookup falls
    from the species pool to the genus pool to the whole population, the same order :func:`allometry.params_for`
    uses. Pools below :data:`MIN_TAXON_POOL` trees fall through.
    """

    all_m: np.ndarray                       # sorted heights of every measured-DBH census tree
    by_species: dict[str, np.ndarray]       # sorted, per exact ``spc_latin`` with >= MIN_TAXON_POOL trees
    by_genus: dict[str, np.ndarray]         # sorted, per first word of ``spc_latin``
    n_source: int
    n_excluded_no_dbh: int

    @classmethod
    def from_arrays(cls, height_m, species, dbh_cm, min_pool: int = MIN_TAXON_POOL) -> "CensusHeights":
        h = np.asarray(height_m, dtype=np.float64)
        d = np.asarray(dbh_cm, dtype=np.float64)
        sp = np.asarray(list(species), dtype=object)
        ok = np.isfinite(h) & (h > 0) & np.isfinite(d) & (d > 0)
        if not ok.any():
            raise ValueError("CensusHeights needs at least one census tree with a measured DBH")
        h, sp = h[ok], sp[ok]
        gen = np.array([s.split(" ")[0] if s else "" for s in sp], dtype=object)
        pools: list[dict[str, np.ndarray]] = []
        for key in (sp, gen):
            pool: dict[str, np.ndarray] = {}
            names, inverse = np.unique(key.astype(str), return_inverse=True)
            order = np.argsort(inverse, kind="stable")
            bounds = np.searchsorted(inverse[order], np.arange(len(names) + 1))
            for i, name in enumerate(names):
                if not name:
                    continue
                vals = h[order[bounds[i]:bounds[i + 1]]]
                if vals.size >= min_pool:
                    pool[str(name)] = np.sort(vals)
            pools.append(pool)
        return cls(np.sort(h), pools[0], pools[1], int(h.size), int((~ok).sum()))

    @classmethod
    def from_census(cls, tc: "TreeCensus", min_pool: int = MIN_TAXON_POOL) -> "CensusHeights":
        df = tc.df
        return cls.from_arrays(df["height_m"].to_numpy(), df["species"].to_list(), df["dbh_cm"].to_numpy(), min_pool)

    def pool_for(self, taxon: str) -> np.ndarray:
        """Species pool, then genus pool, then the whole population — the allometry's own lookup order."""
        t = (taxon or "").strip()
        if t in self.by_species:
            return self.by_species[t]
        return self.by_genus.get(t.split(" ")[0], self.all_m)

    def draw(self, x, y, taxon) -> tuple[np.ndarray, np.ndarray]:
        """Return ``(height_m, from_taxon_pool)`` for points at ``x, y`` with the taxon names in ``taxon``.

        The value is the ``u``-th quantile of the chosen pool, where ``u`` comes only from the point's own
        coordinates, so the result is bit-identical across runs and independent of row order.
        """
        x = np.asarray(x, dtype=np.float64)
        u = coordinate_uniform(x, y)
        names = np.asarray(list(taxon), dtype=object)
        out = np.empty(x.size, dtype=np.float64)
        from_taxon = np.zeros(x.size, dtype=bool)
        keys = np.array([self._key(t) for t in names], dtype=object)
        skeys = keys.astype(str)
        for key in np.unique(skeys):
            m = skeys == key
            pool = self.all_m if key == "" else self.by_species.get(key, self.by_genus.get(key, self.all_m))
            idx = np.minimum((u[m] * pool.size).astype(np.int64), pool.size - 1)
            out[m] = pool[idx]
            from_taxon[m] = key != ""
        return out, from_taxon

    def _key(self, taxon: str) -> str:
        t = (taxon or "").strip()
        if t in self.by_species:
            return t
        g = t.split(" ")[0]
        return g if g in self.by_genus else ""

    def report(self) -> dict:
        q = [5, 10, 25, 50, 75, 90, 95]
        return {"source": "2015 Street Tree Census heights (allometry over a measured DBH, DEVIATIONS D2)",
                "trees_in_pool": self.n_source, "excluded_without_a_measured_dbh": self.n_excluded_no_dbh,
                "species_pools": len(self.by_species), "genus_pools": len(self.by_genus),
                "min_pool": MIN_TAXON_POOL,
                "percentiles_m": {str(k): round(float(v), 2) for k, v in zip(q, np.percentile(self.all_m, q))}}
