"""Woodland canopy rule (``source = 1``, ``dataset_id`` ``rule:woodland_canopy``): stems under the wood polygons.

**What the sources hold and what they do not.** The build's two tree inventories are point lists: the 2015
Street Tree Census (a street inventory; zero rows inside Central Park) and the ``natural=tree`` nodes of the OSM
extract (D10: the trees a mapper happened to walk past). The *extent* of the city's woodland is a third, real
source that nothing read: ``osm/landuse_leisure.parquet`` holds the ``natural=wood`` / ``landuse=forest`` /
``natural=scrub`` polygons -- 5,557 ha inside the five boroughs, 41.9 ha of it in Central Park -- and 94.5 % of
those polygons hold no tree at all. No canopy raster, LiDAR point cloud or per-tree inventory of any NYC
woodland is held or registered (``sources.py``), so the polygon is the only measured claim about the wood.

**What this rule asserts, and how each part is flagged.** A ``natural=wood`` polygon is a mapper's statement
that the ground inside it is covered by tree crowns. This module takes that statement literally and nothing
more: it places stems inside the polygon until the projected crown area of the placed trees, plus that of every
dataset tree already standing inside it, reaches the plantable area (closed canopy). Every stem position, the
count that results, the species (unless drawn from a mapped neighbour's tag) and the height are inferred, and
every row says so: ``source = 1``, ``dataset_id = rule:woodland_canopy``, and ``attrs`` carrying the rule name,
the polygon it was placed in, where its species came from and where its height came from. The **stems per
hectare are a consequence of crown closure over the asset catalogue's own crown widths -- never a measurement**;
the build summary reports them under that name.

Conventions shared with the lamp / manhole rules (:mod:`.rules`): a stem is generated only where no mapped tree
stands -- suppressed within :data:`SUPPRESS_M` of any census or OSM tree (the measured 5.0 m cross-source
dedupe radius of :mod:`.dedupe` plus one metre) -- so every mapped tree keeps its place and the rule fills gaps;
placement is a deterministic blue-noise (Poisson-disc) sample seeded from ``(wood osm_id, cell index, round)``
through SplitMix64 in the style of :func:`.trees.coordinate_uniform`, so a re-run is bit-identical and the
result does not depend on row order; and :mod:`.dedupe` makes a rule stem lose to any dataset tree within the
same radius as a second line of defence.
"""
from __future__ import annotations

import json
import logging
import math
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq
import shapely
from scipy.spatial import cKDTree

from ..crs import SCOPE_XMAX, SCOPE_XMIN, SCOPE_YMAX, SCOPE_YMIN, transformer
from ..paths import PROCESSED, RAW
from ..tiling import tiles_in_bbox
from . import assets as A
from .catalog import HEIGHT_SOURCE, KIND_ID, SOURCE_RULE
from .dedupe import CROSS_SOURCE_RULES, TREE_RULE_DATASET, TREE_RULE_MARGIN_M
from .schema import empty_columns
from .trees import CensusHeights, _splitmix64, coordinate_uniform

log = logging.getLogger("nycsim.furniture.canopy")

#: The ``dataset_id`` every stem carries; :mod:`.dedupe` names the same string in its cross-source rules.
RULE_ID = TREE_RULE_DATASET
RULE_NAME = "woodland_canopy"

LANDUSE = PROCESSED / "osm" / "landuse_leisure.parquet"
BOROUGHS = RAW / "nyc_opendata" / "borough_boundaries.geojson"
PARKS_PROPERTIES = RAW / "nyc_opendata" / "parks_properties.geojson"
SURFACES = PROCESSED / "parks" / "surfaces.parquet"
PAVEMENT_DIR = PROCESSED / "roads" / "pavement"
HYDROGRAPHY = PROCESSED / "water" / "hydrography.parquet"
ASSET_CATALOG = Path(__file__).resolve().parents[3] / "blender_out" / "props" / "props_asset_catalog.json"

#: OSM values this rule reads as "ground covered by tree crowns" (``natural=wood``, ``landuse=forest``) or by
#: shrub crowns (``natural=scrub``).
WOOD_VALUES = ("wood", "forest", "scrub")
#: Health/condition ``variant`` for a tree nothing was observed about: the catalogue's 3 = unknown, as D10 does.
TREE_HEALTH_UNKNOWN = 3

EDGE_INSET_M = 2.0
#: A generated stem is dropped within this distance of any census or OSM tree: the measured 5.0 m cross-source
#: radius of :data:`.dedupe.CROSS_SOURCE_RULES` (nearest-census-tree distance of every OSM node against a
#: 20 m-displaced control) plus one metre, so the rule never stands closer to a mapped tree than the two
#: inventories are allowed to stand to each other.
SUPPRESS_M = float(CROSS_SOURCE_RULES[0].radius_m) + float(TREE_RULE_MARGIN_M)
MIN_SPACING_M = 4.0
SPACING_CROWN_FRACTION = 0.6
SCRUB_SPACING_M = 3.0
#: Scrub draws only the catalogue's small size band: heights below the scene's small/medium edge
#: (:data:`.assets.TREE_SIZE_EDGES` [0]) and no lower than :data:`SCRUB_MIN_HEIGHT_M`, and only species whose
#: small exported asset stands under :data:`SCRUB_SMALL_ASSET_MAX_M`, so the consumer's uniform scale
#: (:data:`.assets.TREE_SCALE_MIN`) stays in band and the shrub drawn is the shrub placed.
SCRUB_MIN_HEIGHT_M = 3.0
SCRUB_SMALL_ASSET_MAX_M = 10.0
#: ``parks/surfaces.parquet`` kinds that are built surfaces (hard court, ball diamond, pool, running track,
#: rink) -- no crown stands on them even where a wood polygon overlaps.
PAVED_SURFACE_KINDS = ("court", "ballfield", "pool", "track", "skating_rink")

#: Candidate lattice: one candidate per :data:`CELL_M` cell per round; a cell's candidates from different
#: rounds are different draws. Rounds stop when every polygon has closed or has gone :data:`JAM_ROUNDS` rounds
#: without accepting a stem.
CELL_M = 5.0
MAX_ROUNDS = 16
JAM_ROUNDS = 3

#: The scoping agent's bounding box of the Ramble in NYC_TM metres (no OSM polygon inside Central Park is named
#: "The Ramble"; the two rows with that name are in New Jersey), kept for the summary's window count only.
RAMBLE_BBOX_TM = (-1984.0, 8384.0, -1519.0, 8829.0)

#: The rule, in the words the build summary, the catalogue and every row's attrs carry.
RULES: tuple[str, ...] = (
    "woodland_canopy: inside every natural=wood, landuse=forest and natural=scrub polygon of the OSM extract "
    "(osm/landuse_leisure.parquet) clipped to the five boroughs and the scope box, minus a 2 m edge inset, "
    "minus the built park surfaces (court, ballfield, pool, track, skating_rink), the roads-stage pavement "
    "polygons and the open-water polygons, tree stems are placed by a deterministic Poisson-disc sample "
    "seeded from (wood osm_id, 5 m cell index, round) through SplitMix64.",
    "density is a modelling consequence of what the tag asserts (ground covered by tree crowns), not a "
    "measurement: no stem inventory of any NYC woodland is held, so stems are placed until the projected "
    "crown area (pi/4 x crown^2, the asset's nominal_size_m[0] at the uniform scale the consumer draws it at) "
    "of the placed stems plus the dataset trees already inside the polygon reaches the plantable area, with a "
    "minimum spacing of max(4 m, 0.6 x crown); scrub draws only the small size band at 3 m spacing -- and there "
    "the target is unreachable by construction: small assets carry crowns of 2.3-4.1 m, closure at 3 m spacing "
    "needs a 3.15 m crown even at hexagonal packing, so the scrub fill jams at about 640 stems/ha with the "
    "crowns covering about half the ground; the scrub density is the jam density of the 3 m spacing constant, "
    "not crown closure, and the summary reports it under that name.",
    f"a stem is suppressed within {SUPPRESS_M:.1f} m of any census or OSM tree (the measured 5.0 m cross-source "
    "dedupe radius plus one metre), so every mapped tree keeps its place and the rule fills gaps only.",
    "species: from the species/genus tags of the OSM trees mapped inside the same polygon where any carry one "
    "(species_from=neighbour); otherwise, for broadleaved, mixed and untagged polygons, the catalogue's ten "
    "species weighted by the 2015 Street Tree Census counts of the same borough, a street-population proxy "
    "(species_from=census_pool); needleleaved polygons have no conifer asset, so the broadleaf fallback is "
    "placed with species empty and species_substituted=true (species_from=fallback).",
    "height: a deterministic draw from the census height distribution conditioned on the taxon, seeded by the "
    "stem's own coordinates -- the OSM-tree path, height_source 4; variant 3 (condition unknown); dbh_cm 0.",
)


# --------------------------------------------------------------------------------------- hashing

_C1 = np.uint64(0x9E3779B97F4A7C15)
_C2 = np.uint64(0xD1B54A32D192ED03)
_C3 = np.uint64(0x8CB92BA72F3D8DD7)
_S_X = np.uint64(0x2545F4914F6CDD1D)
_S_Y = np.uint64(0x5851F42D4C957F2D)
_S_SPECIES = np.uint64(0x14057B7EF767814F)


def _u01(h: np.ndarray) -> np.ndarray:
    return (h >> np.uint64(11)).astype(np.float64) * (2.0 ** -53)


def cell_uniforms(osm_id: np.ndarray, ix: np.ndarray, iy: np.ndarray, rnd: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Three deterministic uniforms in [0, 1) per candidate, seeded only by ``(wood osm_id, cell, round)``.

    Same construction as :func:`.trees.coordinate_uniform` (SplitMix64 finaliser, no RNG state): the draw
    follows the polygon and the cell, so it is unchanged by row order, by which other polygons are present and
    by re-running the stage.
    """
    with np.errstate(over="ignore"):
        o = np.asarray(osm_id, dtype=np.int64).astype(np.uint64)
        a = np.asarray(ix, dtype=np.int64).astype(np.uint64)
        b = np.asarray(iy, dtype=np.int64).astype(np.uint64)
        r = np.uint64(int(rnd) & 0xFFFFFFFFFFFFFFFF)
        k = _splitmix64(_splitmix64(_splitmix64(o * _C1) ^ (a * _C2)) ^ (b * _C3)) ^ _splitmix64(r * _C1)
        return _u01(_splitmix64(k ^ _S_X)), _u01(_splitmix64(k ^ _S_Y)), _u01(_splitmix64(k ^ _S_SPECIES))


# --------------------------------------------------------------------------------------- crown widths

@dataclass(frozen=True)
class CrownTable:
    """Crown width of the asset a stem will be drawn with, read from ``props_asset_catalog.json``.

    Mirrors :meth:`.assets.PropAssets.tree_asset`: the exported size nearest the row's height is drawn at a
    uniform scale ``height / asset height`` inside :data:`.assets.TREE_SCALE_MIN` .. ``MAX`` (else at 1.0), and
    the projected crown is the asset's ``nominal_size_m[0]`` at that scale -- the crown the consumer shows.
    """
    keys: tuple[str, ...]
    heights: dict[str, np.ndarray]        # key -> exported heights (small, medium, large order)
    crowns: dict[str, np.ndarray]         # key -> nominal_size_m[0] in the same order
    ids: dict[str, list[str]]             # key -> asset ids in the same order
    fallback: str = A.TREE_FALLBACK_KEY

    @classmethod
    def load(cls, catalog_path: Path = ASSET_CATALOG) -> "CrownTable":
        if not catalog_path.exists():
            raise FileNotFoundError(f"{catalog_path} missing: the canopy rule reads crown widths from the exported "
                                    "prop asset catalogue (blender/props/build_props.py)")
        doc = json.loads(catalog_path.read_text())
        heights: dict[str, list[float]] = {}
        crowns: dict[str, list[float]] = {}
        ids: dict[str, list[str]] = {}
        for e in doc.get("entries", []):
            if e.get("dataset_kind") != "tree" or e["id"].endswith("_bare"):
                continue
            key, size = e["id"][len("tree_"):].rsplit("_", 1)
            b = e["bounds"]
            heights.setdefault(key, []).append(float(b["max"][2]) - float(b["min"][2]))
            crowns.setdefault(key, []).append(float(e["nominal_size_m"][0]))
            ids.setdefault(key, []).append(str(e["id"]))
        if not heights:
            raise ValueError(f"{catalog_path} carries no tree assets")
        if A.TREE_FALLBACK_KEY not in heights:
            raise ValueError(f"the fallback species {A.TREE_FALLBACK_KEY!r} has no exported asset")
        return cls(tuple(sorted(heights)), {k: np.asarray(v) for k, v in heights.items()},
                   {k: np.asarray(v) for k, v in crowns.items()}, ids)

    def key_of(self, species: str) -> str:
        return A.TREE_SPECIES_KEYS.get((species or "").strip().lower(), self.fallback)

    def small_asset_height(self, key: str) -> float:
        return float(self.heights[key].min())

    def lookup(self, species: list[str], height_m: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, list[str]]:
        """``(crown_m, scale, asset_index_within_key, asset_id)`` per stem, vectorised per species key."""
        h = np.asarray(height_m, dtype=np.float64)
        keys = np.array([self.key_of(s) for s in species], dtype=object)
        crown = np.empty(h.size)
        scale = np.ones(h.size)
        which = np.zeros(h.size, dtype=np.int64)
        for key in np.unique(keys.astype(str)) if h.size else []:
            m = keys == key
            hs = self.heights[key]
            want = np.where(np.isfinite(h[m]) & (h[m] > 0), h[m], A.TREE_DEFAULT_HEIGHT_M)
            j = np.argmin(np.abs(hs[None, :] - want[:, None]), axis=1)
            sc = want / hs[j]
            sc = np.where((sc < A.TREE_SCALE_MIN) | (sc > A.TREE_SCALE_MAX), 1.0, sc)
            crown[m] = self.crowns[key][j] * sc
            scale[m] = sc
            which[m] = j
        ids = [self.ids[k][int(j)] for k, j in zip(keys, which)]
        return crown, scale, which, ids

    def max_spacing(self, height_pool_max: float) -> float:
        """Largest ``max(4, 0.6 x crown)`` any stem can ask for, given the tallest height the pool can draw."""
        worst = MIN_SPACING_M
        for key in self.keys:
            for hh, cc in zip(self.heights[key], self.crowns[key]):
                sc = min(A.TREE_SCALE_MAX, max(1.0, height_pool_max / hh))
                worst = max(worst, SPACING_CROWN_FRACTION * cc * sc)
        return worst


# --------------------------------------------------------------------------------------- inputs

@dataclass
class WoodPolygons:
    osm_id: np.ndarray
    value: np.ndarray            # wood | forest | scrub
    leaf_type: np.ndarray
    name: np.ndarray
    borough: np.ndarray          # 1..5 (borough_boundaries borocode)
    geometry: np.ndarray         # clipped to the boroughs and the scope box
    area_m2: np.ndarray          # of the clipped polygon
    inset: np.ndarray = field(default_factory=lambda: np.empty(0, dtype=object))
    plantable: np.ndarray = field(default_factory=lambda: np.empty(0, dtype=object))
    plantable_m2: np.ndarray = field(default_factory=lambda: np.empty(0))
    has_exclusion: np.ndarray = field(default_factory=lambda: np.empty(0, dtype=bool))

    def __len__(self) -> int:
        return int(self.osm_id.size)


def load_boroughs(path: Path = BOROUGHS) -> tuple[np.ndarray, np.ndarray]:
    """``(borocode int array, NYC_TM geometries)`` of the five boroughs' land boundaries."""
    doc = json.loads(path.read_text())
    tr = transformer("WGS84", "NYC_TM")
    codes, geoms = [], []
    for f in doc["features"]:
        g = shapely.geometry.shape(f["geometry"])
        g = shapely.transform(g, lambda c: np.column_stack(tr.transform(c[:, 0], c[:, 1])))
        codes.append(int(f["properties"]["borocode"]))
        geoms.append(shapely.make_valid(g))
    return np.asarray(codes, dtype=np.int8), np.asarray(geoms, dtype=object)


def load_wood_polygons(path: Path = LANDUSE, boroughs_path: Path = BOROUGHS,
                       scope: tuple[float, float, float, float] = (SCOPE_XMIN, SCOPE_YMIN, SCOPE_XMAX, SCOPE_YMAX)) -> tuple[WoodPolygons, dict]:
    """The wood / forest / scrub polygons of the extract, clipped to the five boroughs and the scope box."""
    if not path.exists():
        raise FileNotFoundError(f"{path} missing; run: python -m nycsim_pipeline osm")
    t = pq.read_table(path, columns=["osm_id", "geometry", "value", "name", "leaf_type", "area_m2"])
    value = np.asarray(t.column("value").to_pylist(), dtype=object)
    keep = np.isin(value, np.asarray(WOOD_VALUES, dtype=object))
    idx = np.flatnonzero(keep)
    geoms = shapely.from_wkb([t.column("geometry")[int(i)].as_py() for i in idx])
    geoms = shapely.make_valid(geoms)
    osm_id = t.column("osm_id").to_numpy(zero_copy_only=False)[idx].astype(np.int64)
    value = value[idx]
    leaf = np.asarray([(v or "") for v in t.column("leaf_type").to_pylist()], dtype=object)[idx]
    name = np.asarray([(v or "") for v in t.column("name").to_pylist()], dtype=object)[idx]
    n_extract = int(idx.size)
    extract_ha = float(np.nansum(t.column("area_m2").to_numpy(zero_copy_only=False)[idx]) / 1e4)

    codes, bgeoms = load_boroughs(boroughs_path)
    land = shapely.union_all(bgeoms)
    box = shapely.box(*scope)
    clip_to = land.intersection(box)
    btree = shapely.STRtree(bgeoms)
    hit = btree.query(geoms, predicate="intersects")
    touched = np.unique(hit[0])
    within = np.zeros(len(geoms), dtype=bool)
    w = btree.query(geoms, predicate="within")
    within[np.unique(w[0])] = True
    out_geoms = np.empty(len(geoms), dtype=object)
    for i in touched:
        g = geoms[i]
        if not within[i] or not box.contains(g):
            g = g.intersection(clip_to)
        out_geoms[i] = g
    touched_set = set(touched.tolist())
    ok = np.array([i in touched_set and out_geoms[i] is not None and not out_geoms[i].is_empty
                   and out_geoms[i].area > 0 for i in range(len(geoms))], dtype=bool)
    sel = np.flatnonzero(ok)
    rep = shapely.point_on_surface(out_geoms[sel])
    bh = btree.query(rep, predicate="within")
    borough = np.zeros(sel.size, dtype=np.int8)
    borough[bh[0]] = codes[bh[1]]
    # a representative point on a shared boundary can miss "within"; nearest borough then
    miss = np.flatnonzero(borough == 0)
    if miss.size:
        near = btree.nearest(rep[miss])
        borough[miss] = codes[near]
    wp = WoodPolygons(osm_id[sel], value[sel], leaf[sel], name[sel], borough, out_geoms[sel],
                      shapely.area(out_geoms[sel]))
    rep_doc = {"polygons_in_extract": n_extract, "extract_area_ha": round(extract_ha, 2),
               "polygons_in_boroughs": int(sel.size), "clipped_area_ha": round(float(wp.area_m2.sum()) / 1e4, 2),
               "dropped_outside_boroughs": int(n_extract - sel.size)}
    log.info("canopy: %d wood/forest/scrub polygons in the extract, %d inside the five boroughs (%.1f ha)",
             n_extract, sel.size, wp.area_m2.sum() / 1e4)
    return wp, rep_doc


def load_exclusions(wood: WoodPolygons, surfaces_path: Path = SURFACES, pavement_dir: Path = PAVEMENT_DIR,
                    hydro_path: Path = HYDROGRAPHY) -> tuple[np.ndarray, np.ndarray, dict]:
    """``(geometries, source labels, report)`` of the ground no crown stands on, near the wood polygons."""
    geoms: list = []
    labels: list[str] = []
    rep: dict = {}
    if surfaces_path.exists():
        t = pq.read_table(surfaces_path, columns=["kind_name", "geometry"])
        kn = np.asarray(t.column("kind_name").to_pylist(), dtype=object)
        m = np.isin(kn, np.asarray(PAVED_SURFACE_KINDS, dtype=object))
        g = shapely.from_wkb([t.column("geometry")[int(i)].as_py() for i in np.flatnonzero(m)])
        geoms.extend(g.tolist())
        labels.extend(f"surfaces:{k}" for k in kn[m])
        rep["surfaces_paved_polygons"] = int(m.sum())
    else:
        rep["surfaces_paved_polygons"] = f"skipped: {surfaces_path} missing"
    tiles: set[str] = set()
    for b in shapely.bounds(wood.geometry):
        for tl in tiles_in_bbox(b[0] - EDGE_INSET_M, b[1] - EDGE_INSET_M, b[2] + EDGE_INSET_M, b[3] + EDGE_INSET_M):
            tiles.add(tl.name)
    n_pav = 0
    n_tiles = 0
    if pavement_dir.exists():
        for name in sorted(tiles):
            p = pavement_dir / f"{name}.parquet"
            if not p.exists():
                continue
            n_tiles += 1
            g = shapely.from_wkb(pq.read_table(p, columns=["geometry"]).column("geometry").to_pylist())
            geoms.extend(g.tolist())
            labels.extend(["pavement"] * len(g))
            n_pav += len(g)
    rep["pavement_tiles_read"] = n_tiles
    rep["pavement_polygons"] = n_pav
    if hydro_path.exists():
        t = pq.read_table(hydro_path, columns=["is_open_water", "geometry"])
        ow = np.asarray(t.column("is_open_water").to_pylist(), dtype=bool)
        g = shapely.from_wkb([t.column("geometry")[int(i)].as_py() for i in np.flatnonzero(ow)])
        geoms.extend(g.tolist())
        labels.extend(["water"] * len(g))
        rep["open_water_polygons"] = int(ow.sum())
    else:
        rep["open_water_polygons"] = f"skipped: {hydro_path} missing"
    return np.asarray(geoms, dtype=object), np.asarray(labels, dtype=object), rep


def plantable_regions(wood: WoodPolygons, excl_geoms: np.ndarray, excl_labels: np.ndarray) -> dict:
    """Fill ``wood.inset`` / ``wood.plantable``: the polygon minus the edge inset minus the exclusions."""
    n = len(wood)
    inset = shapely.buffer(wood.geometry, -EDGE_INSET_M)
    plantable = np.empty(n, dtype=object)
    has_excl = np.zeros(n, dtype=bool)
    removed_by: Counter = Counter()
    removed_ha: Counter = Counter()
    tree = shapely.STRtree(excl_geoms) if len(excl_geoms) else None
    src_names = np.array([s.split(":")[0] for s in excl_labels], dtype=object)
    for i in range(n):
        g = inset[i]
        if g is None or g.is_empty:
            plantable[i] = shapely.Polygon()
            continue
        hits = tree.query(g, predicate="intersects") if tree is not None else np.zeros(0, dtype=np.int64)
        if hits.size == 0:
            plantable[i] = g
            continue
        has_excl[i] = True
        cut = g
        for src in np.unique(src_names[hits].astype(str)):
            part = shapely.union_all(excl_geoms[hits[src_names[hits] == src]])
            before = cut.area
            cut = cut.difference(part)
            removed_by[src] += 1
            removed_ha[src] += (before - cut.area) / 1e4
        plantable[i] = cut
    wood.inset = inset
    wood.plantable = plantable
    wood.plantable_m2 = shapely.area(plantable)
    wood.has_exclusion = has_excl
    shapely.prepare(plantable)
    return {"polygons_with_an_exclusion": int(has_excl.sum()),
            "polygons_removed_by_exclusion": {k: int(v) for k, v in sorted(removed_by.items())},
            "area_removed_ha": {k: round(float(v), 3) for k, v in sorted(removed_ha.items())},
            "polygons_too_thin_for_the_inset": int(sum(1 for g in plantable if g.is_empty)),
            "inset_area_ha": round(float(np.nansum(shapely.area(inset))) / 1e4, 2),
            "plantable_area_ha": round(float(wood.plantable_m2.sum()) / 1e4, 2)}


# --------------------------------------------------------------------------------------- species pools

@dataclass(frozen=True)
class SpeciesPool:
    taxa: tuple[str, ...]
    cum: np.ndarray                  # cumulative weights normalised to 1
    origin: str                      # neighbour | census_pool | fallback
    note: str = ""


def census_pools(census_by_borough: dict[int, dict[str, int]], crowns: CrownTable) -> dict[int, SpeciesPool]:
    """Per borough: the catalogue's species weighted by the census counts of that borough (a street proxy)."""
    pools: dict[int, SpeciesPool] = {}
    for boro, counts in census_by_borough.items():
        by_key: dict[str, tuple[str, int]] = {}
        for latin, c in counts.items():
            key = A.TREE_SPECIES_KEYS.get((latin or "").strip().lower())
            if key is None or key not in crowns.heights:
                continue
            if key not in by_key or c > by_key[key][1]:
                # one census spelling per asset species: the commonest one, so the species column reads as
                # the census writes it
                by_key[key] = (latin, c)
        if not by_key:
            continue
        keys = sorted(by_key)
        total_by_key = {}
        for latin, c in counts.items():
            key = A.TREE_SPECIES_KEYS.get((latin or "").strip().lower())
            if key in by_key:
                total_by_key[key] = total_by_key.get(key, 0) + int(c)
        w = np.array([total_by_key[k] for k in keys], dtype=np.float64)
        pools[int(boro)] = SpeciesPool(tuple(by_key[k][0] for k in keys), np.cumsum(w) / w.sum(), "census_pool",
                                       f"2015 census counts of the catalogue's species in borough {boro}")
    return pools


def scrub_pool(pool: SpeciesPool, crowns: CrownTable) -> SpeciesPool:
    """The same weights, restricted to species whose small exported asset stands under the scrub limit."""
    w = np.diff(np.concatenate([[0.0], pool.cum]))
    keep = [i for i, tx in enumerate(pool.taxa) if crowns.small_asset_height(crowns.key_of(tx)) <= SCRUB_SMALL_ASSET_MAX_M]
    if not keep:
        keep = list(range(len(pool.taxa)))
    ww = w[keep]
    return SpeciesPool(tuple(pool.taxa[i] for i in keep), np.cumsum(ww) / ww.sum(), pool.origin, pool.note + "; scrub band")


def draw_species(pool: SpeciesPool, u: np.ndarray) -> list[str]:
    j = np.minimum(np.searchsorted(pool.cum, u, side="right"), len(pool.taxa) - 1)
    return [pool.taxa[int(k)] for k in j]


# --------------------------------------------------------------------------------------- heights

def draw_heights(heights: CensusHeights, x: np.ndarray, y: np.ndarray, taxon: list[str], scrub: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """``(height_m, from_taxon_pool)``: the OSM-tree draw, and for scrub the same draw over the pool's small band."""
    h, from_taxon = heights.draw(x, y, taxon)
    if scrub.any():
        u = coordinate_uniform(x[scrub], y[scrub])
        names = np.asarray(taxon, dtype=object)[scrub]
        hi = float(A.TREE_SIZE_EDGES[0])
        out = np.empty(int(scrub.sum()))
        for tx in np.unique(names.astype(str)):
            m = names == tx
            pool = heights.pool_for(tx)
            lo_i, hi_i = np.searchsorted(pool, SCRUB_MIN_HEIGHT_M, side="left"), np.searchsorted(pool, hi, side="left")
            band = pool[lo_i:hi_i] if hi_i > lo_i else pool[:max(1, hi_i)]
            idx = np.minimum((u[m] * band.size).astype(np.int64), band.size - 1)
            out[m] = band[idx]
        h[scrub] = out
    return h, from_taxon


# --------------------------------------------------------------------------------------- placement

def _crown_area(crown_m: np.ndarray) -> np.ndarray:
    return math.pi / 4.0 * np.asarray(crown_m, dtype=np.float64) ** 2


@dataclass
class DatasetTrees:
    """The census and OSM trees already in the build: positions, and what they carry that the rule reads."""
    x: np.ndarray
    y: np.ndarray
    is_osm: np.ndarray
    species: np.ndarray            # species column
    taxon: np.ndarray              # species, or the OSM genus where the species column is empty
    height_m: np.ndarray

    @classmethod
    def from_cols(cls, cols: dict, tree_kind: int = KIND_ID["tree"]) -> "DatasetTrees":
        kind = np.asarray(cols["kind"], dtype=np.int16)
        m = np.flatnonzero(kind == tree_kind)
        ds = np.asarray(cols["dataset_id"], dtype=object)[m]
        species = np.asarray(cols["species"], dtype=object)[m]
        is_osm = ds == "osm_newyork_pbf"
        taxon = species.copy()
        attrs = cols["attrs"]
        for j in np.flatnonzero(is_osm & (species == "")):
            a = attrs[int(m[j])]
            if a and '"genus"' in a:
                try:
                    taxon[j] = str(json.loads(a).get("genus") or "")
                except ValueError:
                    pass
        return cls(np.asarray(cols["x"], dtype=np.float64)[m], np.asarray(cols["y"], dtype=np.float64)[m],
                   is_osm, species, taxon, np.asarray(cols["height_m"], dtype=np.float64)[m])


def _polygon_pools(wood: WoodPolygons, trees: DatasetTrees, boro_pools: dict[int, SpeciesPool],
                   crowns: CrownTable) -> tuple[list[SpeciesPool], np.ndarray, np.ndarray, dict]:
    """One species pool per polygon, plus the crown area the dataset trees inside it already cover."""
    n = len(wood)
    pts = shapely.points(trees.x, trees.y)
    hit = shapely.STRtree(pts).query(wood.plantable, predicate="contains") if trees.x.size else np.zeros((2, 0), dtype=np.int64)
    inside_poly, inside_tree = hit[0], hit[1]
    crown, _sc, _w, _ids = crowns.lookup(list(trees.species[inside_tree]), trees.height_m[inside_tree])
    credited = np.zeros(n)
    np.add.at(credited, inside_poly, _crown_area(crown))
    n_inside = np.zeros(n, dtype=np.int64)
    np.add.at(n_inside, inside_poly, 1)
    tagged = inside_tree[trees.is_osm[inside_tree] & (trees.taxon[inside_tree] != "")]
    tagged_poly = inside_poly[trees.is_osm[inside_tree] & (trees.taxon[inside_tree] != "")]
    per_poly: dict[int, Counter] = {}
    for p, t in zip(tagged_poly.tolist(), tagged.tolist()):
        per_poly.setdefault(int(p), Counter())[str(trees.taxon[t])] += 1
    fallback = SpeciesPool(("",), np.array([1.0]), "fallback", "no conifer asset; broadleaf fallback, species_substituted")
    pools: list[SpeciesPool] = []
    origin = Counter()
    for i in range(n):
        if i in per_poly:
            c = per_poly[i]
            taxa = tuple(sorted(c))
            w = np.array([c[t] for t in taxa], dtype=np.float64)
            pool = SpeciesPool(taxa, np.cumsum(w) / w.sum(), "neighbour", f"{int(w.sum())} tagged OSM trees inside the polygon")
        elif wood.leaf_type[i] == "needleleaved":
            pool = fallback
        else:
            pool = boro_pools.get(int(wood.borough[i]))
            if pool is None:
                pool = fallback
        if wood.value[i] == "scrub" and pool.origin == "census_pool":
            pool = scrub_pool(pool, crowns)
        pools.append(pool)
        origin[pool.origin] += 1
    return pools, credited, n_inside, {"polygons_by_species_origin": dict(origin),
                                       "dataset_trees_inside_polygons": int(inside_tree.size),
                                       "dataset_crown_credited_ha": round(float(credited.sum()) / 1e4, 3)}


def place(wood: WoodPolygons, trees: DatasetTrees, heights: CensusHeights, crowns: CrownTable,
          pools: list[SpeciesPool], credited: np.ndarray, *, max_rounds: int = MAX_ROUNDS) -> tuple[dict, dict]:
    """The Poisson-disc fill. Returns ``(stem arrays, report)``.

    Every round puts one candidate in every :data:`CELL_M` cell of every open polygon at a position drawn from
    ``(osm_id, cell, round)``; candidates outside the plantable region, within :data:`SUPPRESS_M` of a dataset
    tree, or closer than the pair's spacing to an accepted stem are dropped; the rest are accepted in cell order
    until the polygon's crown area closes. Candidates of one *phase group* (cell indices congruent mod ``k``)
    are at least ``(k - 1) x CELL_M`` >= the largest spacing apart, so a group is checked against the accepted
    stems in one vectorised pass and never against itself, and the outcome is a fixed function of the inputs.
    """
    n = len(wood)
    target = wood.plantable_m2.copy()
    s = CELL_M
    sp_max = crowns.max_spacing(float(heights.all_m.max()))
    k = int(math.ceil(sp_max / s)) + 1
    # candidate lattice: every cell of every polygon's plantable bbox, ordered (polygon, iy, ix)
    cp, cix, ciy = [], [], []
    for i in range(n):
        g = wood.plantable[i]
        if g.is_empty or target[i] <= 0:
            continue
        x0, y0, x1, y1 = g.bounds
        ix = np.arange(math.floor(x0 / s), math.floor(x1 / s) + 1, dtype=np.int64)
        iy = np.arange(math.floor(y0 / s), math.floor(y1 / s) + 1, dtype=np.int64)
        gx, gy = np.meshgrid(ix, iy)
        cp.append(np.full(gx.size, i, dtype=np.int64))
        cix.append(gx.ravel())
        ciy.append(gy.ravel())
    if not cp:
        return _stem_arrays([], [], [], [], [], [], [], [], [], [], []), {"candidates": 0, "rounds": 0}
    cell_poly, cell_ix, cell_iy = np.concatenate(cp), np.concatenate(cix), np.concatenate(ciy)
    del cp, cix, ciy
    poly_osm = wood.osm_id[cell_poly]
    is_scrub_poly = wood.value == "scrub"

    dtree = cKDTree(np.column_stack([trees.x, trees.y])) if trees.x.size else None
    open_ = target > 0
    open_ &= np.array([not g.is_empty for g in wood.plantable])
    empty_rounds = np.zeros(n, dtype=np.int64)
    acc_x: list[np.ndarray] = []
    acc_y: list[np.ndarray] = []
    acc_sp: list[np.ndarray] = []
    acc_poly: list[np.ndarray] = []
    acc_species: list[list[str]] = []
    acc_h: list[np.ndarray] = []
    acc_from_taxon: list[np.ndarray] = []
    acc_crown: list[np.ndarray] = []
    acc_scale: list[np.ndarray] = []
    acc_asset: list[list[str]] = []
    acc_round: list[np.ndarray] = []
    acc_xy_tree: cKDTree | None = None
    acc_xy: np.ndarray = np.empty((0, 2))
    acc_sp_all: np.ndarray = np.empty(0)
    counts = Counter()
    rounds_run = 0
    for rnd in range(max_rounds):
        live = open_[cell_poly]
        if not live.any():
            break
        rounds_run = rnd + 1
        idx = np.flatnonzero(live)
        u, v, w = cell_uniforms(poly_osm[idx], cell_ix[idx], cell_iy[idx], rnd)
        x = (cell_ix[idx] + u) * s
        y = (cell_iy[idx] + v) * s
        p = cell_poly[idx]
        counts["candidates"] += idx.size
        # inside the plantable region: cells are ordered by polygon, so each polygon is one slice
        inside = np.zeros(idx.size, dtype=bool)
        excluded = 0
        bounds = np.flatnonzero(np.diff(p, prepend=-1) != 0)
        ends = np.append(bounds[1:], idx.size)
        for b, e in zip(bounds, ends):
            i = int(p[b])
            inside[b:e] = shapely.contains_xy(wood.plantable[i], x[b:e], y[b:e])
            if wood.has_exclusion[i]:
                out = ~inside[b:e]
                if out.any():
                    excluded += int(shapely.contains_xy(wood.inset[i], x[b:e][out], y[b:e][out]).sum())
        counts["outside_plantable"] += int((~inside).sum())
        counts["excluded_paved_or_water"] += excluded
        keep = np.flatnonzero(inside)
        if keep.size == 0:
            empty_rounds[open_] += 1
            open_ &= empty_rounds < JAM_ROUNDS
            continue
        x, y, p, w = x[keep], y[keep], p[keep], w[keep]
        ix_k, iy_k = cell_ix[idx][keep], cell_iy[idx][keep]
        if dtree is not None:
            d, _ = dtree.query(np.column_stack([x, y]), k=1, distance_upper_bound=SUPPRESS_M, workers=1)
            near = np.isfinite(d)
            counts["suppressed_near_dataset_tree"] += int(near.sum())
            sel = np.flatnonzero(~near)
            x, y, p, w, ix_k, iy_k = x[sel], y[sel], p[sel], w[sel], ix_k[sel], iy_k[sel]
        if x.size == 0:
            empty_rounds[open_] += 1
            open_ &= empty_rounds < JAM_ROUNDS
            continue
        # species, height, crown and spacing of every surviving candidate
        species = [""] * x.size
        bounds = np.flatnonzero(np.diff(p, prepend=-1) != 0)
        ends = np.append(bounds[1:], x.size)
        for b, e in zip(bounds, ends):
            species[b:e] = draw_species(pools[int(p[b])], w[b:e])
        scrub = is_scrub_poly[p]
        h, from_taxon = draw_heights(heights, x, y, species, scrub)
        crown, scale, _which, asset = crowns.lookup(species, h)
        spacing = np.where(scrub, SCRUB_SPACING_M, np.maximum(MIN_SPACING_M, SPACING_CROWN_FRACTION * crown))
        area = _crown_area(crown)
        accepted_round = np.zeros(n, dtype=np.int64)
        gx_all, gy_all = ix_k % k, iy_k % k
        for gx in range(k):
            for gy in range(k):
                sel = np.flatnonzero((gx_all == gx) & (gy_all == gy) & open_[p])
                if sel.size == 0:
                    continue
                bt = cKDTree(np.column_stack([x[sel], y[sel]]))
                # two polygons whose bboxes overlap share global cells, so one group can hold two
                # candidates of one cell: the later one (cell order) yields to the earlier
                pairs = bt.query_pairs(sp_max, output_type="ndarray")
                if pairs.size:
                    dd = np.hypot(x[sel][pairs[:, 0]] - x[sel][pairs[:, 1]], y[sel][pairs[:, 0]] - y[sel][pairs[:, 1]])
                    clash = dd < np.maximum(spacing[sel][pairs[:, 0]], spacing[sel][pairs[:, 1]])
                    if clash.any():
                        bad = np.zeros(sel.size, dtype=bool)
                        bad[np.maximum(pairs[clash, 0], pairs[clash, 1])] = True
                        counts["rejected_by_spacing"] += int(bad.sum())
                        sel = sel[~bad]
                        if sel.size == 0:
                            continue
                        bt = cKDTree(np.column_stack([x[sel], y[sel]]))
                if acc_xy.shape[0]:
                    coo = bt.sparse_distance_matrix(acc_xy_tree, sp_max, output_type="coo_matrix")
                    if coo.nnz:
                        clash = coo.data < np.maximum(spacing[sel][coo.row], acc_sp_all[coo.col])
                        bad = np.zeros(sel.size, dtype=bool)
                        bad[coo.row[clash]] = True
                        counts["rejected_by_spacing"] += int(bad.sum())
                        sel = sel[~bad]
                if sel.size == 0:
                    continue
                # closure: in cell order per polygon, accept while the crown area credited so far is short
                ps = p[sel]
                prior = np.zeros(sel.size)
                order_b = np.flatnonzero(np.diff(ps, prepend=-1) != 0)
                order_e = np.append(order_b[1:], sel.size)
                for b, e in zip(order_b, order_e):
                    cs = np.cumsum(area[sel[b:e]])
                    prior[b:e] = credited[int(ps[b])] + cs - area[sel[b:e]]
                take = prior < target[ps]
                counts["rejected_by_closure"] += int((~take).sum())
                sel = sel[take]
                if sel.size == 0:
                    continue
                np.add.at(credited, p[sel], area[sel])
                np.add.at(accepted_round, p[sel], 1)
                acc_x.append(x[sel]); acc_y.append(y[sel]); acc_sp.append(spacing[sel]); acc_poly.append(p[sel])
                acc_species.append([species[int(j)] for j in sel]); acc_h.append(h[sel])
                acc_from_taxon.append(from_taxon[sel]); acc_crown.append(crown[sel]); acc_scale.append(scale[sel])
                acc_asset.append([asset[int(j)] for j in sel]); acc_round.append(np.full(sel.size, rnd, dtype=np.int16))
                acc_xy = np.concatenate([acc_xy, np.column_stack([x[sel], y[sel]])])
                acc_sp_all = np.concatenate([acc_sp_all, spacing[sel]])
                acc_xy_tree = cKDTree(acc_xy)
                open_ &= credited < target
        empty_rounds = np.where(accepted_round > 0, 0, empty_rounds + 1)
        open_ &= empty_rounds < JAM_ROUNDS
        log.info("canopy round %d: %d candidates live, %d stems so far, %d polygons still open",
                 rnd, idx.size, acc_xy.shape[0], int(open_.sum()))
    stems = _stem_arrays(acc_x, acc_y, acc_sp, acc_poly, acc_species, acc_h, acc_from_taxon, acc_crown, acc_scale,
                         acc_asset, acc_round)
    rep = {k_: int(v) for k_, v in counts.items()}
    rep.update({"rounds": rounds_run, "max_rounds": max_rounds, "cell_m": s, "phase_stride": k,
                "max_spacing_m": round(sp_max, 2), "polygons_closed": int((credited >= target)[target > 0].sum()),
                "polygons_jammed_open": int((open_ == False)[(credited < target) & (target > 0)].sum()),
                "polygons_still_open_at_max_rounds": int(open_.sum()),
                # by wood value, because the three outcomes mean different things for scrub: a scrub
                # polygon cannot close (see RULES[1]), so "jammed" and "still open" are its normal end
                "by_value": {v: {"polygons": int((wood.value == v).sum()),
                                 "closed": int(((credited >= target) & (target > 0) & (wood.value == v)).sum()),
                                 "jammed_open": int(((open_ == False) & (credited < target) & (target > 0)
                                                     & (wood.value == v)).sum()),
                                 "still_open_at_max_rounds": int((open_ & (wood.value == v)).sum()),
                                 "crown_over_plantable_area_weighted": (round(float(credited[wood.value == v].sum()
                                                                               / target[wood.value == v].sum()), 3)
                                                                         if target[wood.value == v].sum() > 0 else None)}
                             for v in WOOD_VALUES}})
    return stems, rep


def _stem_arrays(xs, ys, sps, polys, species, hs, fts, crowns, scales, assets_, rounds) -> dict:
    if not xs:
        return {"x": np.empty(0), "y": np.empty(0), "spacing": np.empty(0), "poly": np.empty(0, dtype=np.int64),
                "species": [], "height_m": np.empty(0), "from_taxon": np.empty(0, dtype=bool), "crown_m": np.empty(0),
                "scale": np.empty(0), "asset": [], "round": np.empty(0, dtype=np.int16)}
    return {"x": np.concatenate(xs), "y": np.concatenate(ys), "spacing": np.concatenate(sps),
            "poly": np.concatenate(polys), "species": [s for part in species for s in part],
            "height_m": np.concatenate(hs), "from_taxon": np.concatenate(fts), "crown_m": np.concatenate(crowns),
            "scale": np.concatenate(scales), "asset": [a for part in assets_ for a in part],
            "round": np.concatenate(rounds)}


# --------------------------------------------------------------------------------------- rows

def stem_rows(stems: dict, wood: WoodPolygons, pools: list[SpeciesPool]) -> dict:
    """Prop columns (``schema.FIELDS``) for the placed stems: kind 0, source 1, the rule as dataset_id."""
    n = int(stems["x"].size)
    cols = empty_columns(n)
    cols["kind"] = np.full(n, KIND_ID["tree"], dtype=np.int16)
    cols["source"] = np.full(n, SOURCE_RULE, dtype=np.int8)
    cols["dataset_id"] = [RULE_ID] * n
    cols["x"] = np.asarray(stems["x"], dtype=np.float64)
    cols["y"] = np.asarray(stems["y"], dtype=np.float64)
    cols["variant"] = np.full(n, TREE_HEALTH_UNKNOWN, dtype=np.int16)
    cols["dbh_cm"] = np.zeros(n, dtype=np.float32)
    cols["height_m"] = np.asarray(stems["height_m"], dtype=np.float32)
    cols["height_source"] = np.full(n, HEIGHT_SOURCE["census_distribution"], dtype=np.int8)
    poly = np.asarray(stems["poly"], dtype=np.int64)
    # a taxon that names a species (a binomial) is a species; a genus alone goes to attrs, as the OSM loader does
    taxa = list(stems["species"])
    cols["species"] = [t if " " in t else "" for t in taxa]
    attrs = []
    for j in range(n):
        i = int(poly[j])
        pool = pools[i]
        a = {"rule": RULE_NAME, "wood_osm_id": int(wood.osm_id[i]), "wood_value": str(wood.value[i]),
             "leaf_type": str(wood.leaf_type[i]), "species_from": pool.origin,
             "height_source": "census_distribution" + ("_taxon" if stems["from_taxon"][j] else "_population"),
             "crown_m": round(float(stems["crown_m"][j]), 2), "asset": stems["asset"][j]}
        if " " not in taxa[j] and taxa[j]:
            a["genus"] = taxa[j]
        if pool.origin == "fallback":
            a["species_substituted"] = True
        if stems["scale"][j] != 1.0:
            a["scale"] = round(float(stems["scale"][j]), 3)
        attrs.append(json.dumps({k_: v for k_, v in a.items() if v not in ("", None)}, separators=(",", ":")))
    cols["attrs"] = attrs
    return cols


# --------------------------------------------------------------------------------------- windows

def load_park_windows(path: Path = PARKS_PROPERTIES, names: tuple[str, ...] = ("Central Park", "Prospect Park")) -> dict[str, shapely.Geometry]:
    """NYC_TM polygons of the named parks (``parks_properties`` ``signname``), for the summary's counts."""
    if not path.exists():
        return {}
    doc = json.loads(path.read_text())
    tr = transformer("WGS84", "NYC_TM")
    out: dict[str, list] = {}
    for f in doc["features"]:
        nm = f["properties"].get("signname")
        if nm in names and f.get("geometry"):
            g = shapely.geometry.shape(f["geometry"])
            out.setdefault(nm, []).append(shapely.transform(g, lambda c: np.column_stack(tr.transform(c[:, 0], c[:, 1]))))
    return {k_: shapely.union_all(v) for k_, v in out.items()}


def window_counts(x: np.ndarray, y: np.ndarray, parks: dict[str, shapely.Geometry] | None = None) -> dict:
    """Stems inside Central Park, Prospect Park (``parks_properties`` polygons) and the Ramble bbox."""
    x = np.asarray(x, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    if parks is None:
        parks = load_park_windows()
    out = {}
    for nm, g in parks.items():
        out[nm.lower().replace(" ", "_")] = int(shapely.contains_xy(g, x, y).sum()) if x.size else 0
    x0, y0, x1, y1 = RAMBLE_BBOX_TM
    out["ramble_bbox"] = int(((x >= x0) & (x <= x1) & (y >= y0) & (y <= y1)).sum())
    return out


# --------------------------------------------------------------------------------------- after dedupe

def _wood_value_of(attrs: str) -> str:
    """The ``wood_value`` of one stem's attrs without a JSON parse (the key is written by :func:`stem_rows`)."""
    i = attrs.find('"wood_value":"')
    if i < 0:
        return ""
    j = i + len('"wood_value":"')
    return attrs[j:attrs.find('"', j)]


def after_dedupe(cols: dict, placed: int, parks: dict[str, shapely.Geometry] | None = None) -> dict:
    """What the dedupe left of the placed stems: count, by wood value, the window counts, and how many it dropped.

    The placement already keeps every stem :data:`SUPPRESS_M` from any dataset tree, so ``dropped_by_dedupe``
    should be 0; a non-zero value is a placement fault the summary would otherwise hide.
    """
    ds = np.asarray(cols["dataset_id"], dtype=object)
    m = np.flatnonzero(ds == RULE_ID)
    x = np.asarray(cols["x"], dtype=np.float64)[m]
    y = np.asarray(cols["y"], dtype=np.float64)[m]
    attrs = cols["attrs"]
    by_value = Counter(_wood_value_of(attrs[int(i)]) for i in m)
    return {"stems": int(m.size), "dropped_by_dedupe": int(placed - m.size),
            "stems_by_value": {v: int(by_value.get(v, 0)) for v in WOOD_VALUES},
            "windows": window_counts(x, y, parks)}


# --------------------------------------------------------------------------------------- entry point

def census_species_by_borough(df) -> dict[int, dict[str, int]]:
    """``{borocode: {spc_latin: alive count}}`` from the census frame (:class:`.trees.TreeCensus` ``df``)."""
    import polars as pl

    g = df.select([pl.col("borocode"), pl.col("species")]).group_by(["borocode", "species"]).len()
    out: dict[int, dict[str, int]] = {}
    for r in g.iter_rows(named=True):
        try:
            b = int(r["borocode"])
        except (TypeError, ValueError):
            continue
        if not r["species"]:
            continue
        out.setdefault(b, {})[str(r["species"])] = int(r["len"])
    return out


def build_canopy(cols: dict, heights: CensusHeights, census_by_borough: dict[int, dict[str, int]], *,
                 landuse_path: Path = LANDUSE, boroughs_path: Path = BOROUGHS, surfaces_path: Path = SURFACES,
                 pavement_dir: Path = PAVEMENT_DIR, hydro_path: Path = HYDROGRAPHY,
                 catalog_path: Path = ASSET_CATALOG, max_rounds: int = MAX_ROUNDS,
                 scope: tuple[float, float, float, float] | None = None) -> tuple[dict, dict]:
    """Place the canopy stems against the tree rows already in ``cols``. Returns ``(columns, report)``.

    ``cols`` is the concatenated dataset table (census + OSM trees among it): every kind-0 row in it suppresses
    stems within :data:`SUPPRESS_M` and credits its crown to the polygon it stands in. ``scope`` (NYC_TM
    x0 y0 x1 y1) clips the wood polygons to a development box (``--bbox``); the polygons cut by the box are
    inset from the cut edge as well, so a subset run is not the city run restricted to the box.
    """
    import time

    t0 = time.perf_counter()
    crowns = CrownTable.load(catalog_path)
    wood, rep_wood = (load_wood_polygons(landuse_path, boroughs_path) if scope is None
                      else load_wood_polygons(landuse_path, boroughs_path, scope=tuple(scope)))
    if scope is not None:
        rep_wood["scope_bbox_tm"] = list(scope)
    excl_g, excl_l, rep_excl = load_exclusions(wood, surfaces_path, pavement_dir, hydro_path)
    rep_plant = plantable_regions(wood, excl_g, excl_l)
    del excl_g, excl_l
    trees = DatasetTrees.from_cols(cols)
    boro_pools = census_pools(census_by_borough, crowns)
    pools, credited, n_inside, rep_pools = _polygon_pools(wood, trees, boro_pools, crowns)
    t1 = time.perf_counter()
    stems, rep_place = place(wood, trees, heights, crowns, pools, credited, max_rounds=max_rounds)
    t2 = time.perf_counter()
    rows = stem_rows(stems, wood, pools)
    n = len(rows["x"])
    poly = np.asarray(stems["poly"], dtype=np.int64)
    by_value = Counter(str(v) for v in wood.value[poly]) if n else Counter()
    by_borough = Counter(int(b) for b in wood.borough[poly]) if n else Counter()
    plant_ha_by_value = {v: float(wood.plantable_m2[wood.value == v].sum()) / 1e4 for v in WOOD_VALUES}
    gross_ha_by_value = {v: float(wood.area_m2[wood.value == v].sum()) / 1e4 for v in WOOD_VALUES}
    per_ha = {}
    for grp, vals in (("wood_forest", ("wood", "forest")), ("scrub", ("scrub",))):
        cnt = sum(by_value.get(v, 0) for v in vals)
        pl_ha = sum(plant_ha_by_value[v] for v in vals)
        gr_ha = sum(gross_ha_by_value[v] for v in vals)
        per_ha[grp] = {"stems": int(cnt), "plantable_ha": round(pl_ha, 2), "polygon_ha": round(gr_ha, 2),
                       "stems_per_plantable_ha": round(cnt / pl_ha, 1) if pl_ha > 0 else None,
                       "stems_per_polygon_ha": round(cnt / gr_ha, 1) if gr_ha > 0 else None,
                       "mechanism": ("crown closure over the catalogue's crown widths (stems are placed until the "
                                     "projected crown area reaches the plantable area)" if grp == "wood_forest" else
                                     "the jam density of the 3 m spacing constant: small assets carry 2.3-4.1 m "
                                     "crowns, closure at 3 m spacing needs 3.15 m even at hexagonal packing, so the "
                                     "fill stops when no cell can take another stem, at about half crown cover")}
    boro_names = {1: "manhattan", 2: "bronx", 3: "brooklyn", 4: "queens", 5: "staten_island"}
    origin = Counter(pools[int(i)].origin for i in poly) if n else Counter()
    h = np.asarray(rows["height_m"], dtype=np.float64)
    report = {
        "rule": RULE_ID,
        "kind": "tree",
        "stems": int(n),
        "stems_by_value": {v: int(by_value.get(v, 0)) for v in WOOD_VALUES},
        "stems_by_borough": {boro_names.get(b, str(b)): int(c) for b, c in sorted(by_borough.items())},
        "windows_before_dedupe": window_counts(rows["x"], rows["y"]),
        "species_from": {k_: int(v) for k_, v in origin.items()},
        "species_substituted_needleleaved": int(origin.get("fallback", 0)),
        "height_from_taxon_pool": int(np.asarray(stems["from_taxon"], dtype=bool).sum()) if n else 0,
        "height_m_percentiles": ({str(q): round(float(np.percentile(h, q)), 2) for q in (5, 25, 50, 75, 95)} if n else {}),
        "crown_m_percentiles": ({str(q): round(float(np.percentile(stems["crown_m"], q)), 2) for q in (5, 25, 50, 75, 95)} if n else {}),
        "stems_per_ha_consequence": per_ha,
        "consequence_not_measurement": "stems/ha are a consequence of the rule, not a measurement: crown closure "
                                       "over the asset catalogue's crown widths for wood and forest, the jam "
                                       "density of the 3 m spacing constant for scrub (whose small crowns cannot "
                                       "close at that spacing); the repository holds no stem inventory of any NYC "
                                       "woodland",
        "polygons": rep_wood,
        "exclusions": {**rep_excl, **rep_plant},
        "dataset_trees": rep_pools,
        "placement": rep_place,
        "constants": {"edge_inset_m": EDGE_INSET_M, "suppress_m": SUPPRESS_M,
                      "suppress_basis": "dedupe.CROSS_SOURCE_RULES tree radius 5.0 m (measured) + 1 m",
                      "min_spacing_m": MIN_SPACING_M, "spacing_crown_fraction": SPACING_CROWN_FRACTION,
                      "scrub_spacing_m": SCRUB_SPACING_M, "scrub_height_band_m": [SCRUB_MIN_HEIGHT_M, float(A.TREE_SIZE_EDGES[0])],
                      "scrub_small_asset_max_m": SCRUB_SMALL_ASSET_MAX_M, "paved_surface_kinds": list(PAVED_SURFACE_KINDS),
                      "crown_source": str(catalog_path), "cell_m": CELL_M},
        "rules": list(RULES),
        "seconds": {"inputs": round(t1 - t0, 1), "placement": round(t2 - t1, 1), "rows": round(time.perf_counter() - t2, 1)},
    }
    log.info("canopy rule: %d stems in %d polygons (%s) in %.1f s", n, int(np.unique(poly).size) if n else 0,
             ", ".join(f"{k_} {v}" for k_, v in report["stems_by_value"].items()), time.perf_counter() - t0)
    return rows, report
