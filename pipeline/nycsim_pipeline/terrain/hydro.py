"""Hydro-flattening layers for one tile window (ARCHITECTURE §5, DATA_CONTRACTS §3/§4).

Turns the water stage's vector output into per-sample rasters on the 2 m lattice:

* ``water_z``   — the water surface inside every open-water polygon. Tidal bodies (everything connected to
  the ocean: Hudson, East River, Harlem River, Upper/Lower Bay, Jamaica Bay, Newtown Creek, Gowanus Canal,
  Kill Van Kull, Arthur Kill, Long Island Sound, the Atlantic …) are flattened to **0.0 m NAVD88**, the
  tidal datum the whole world uses. A non-tidal body (Central Park reservoir at ~ 40 m, Silver Lake,
  Jerome Park Reservoir, Meadow Lake …) is flattened to its own real level, taken from the planimetric
  water-elevation points where they exist and from the DEM median otherwise (``water.build.finalize_levels``).
  Marshes are *not* flattened: their surface is the DEM.
* ``deck_z``    — pier and jetty decks (planimetric HYDRO STRUCTURE 2800/2810) carry a surveyed deck
  elevation and are drivable/walkable surfaces standing over water, so they replace the water plane.
  Seawalls (2820) only raise samples that the water mask would otherwise flatten — that is the bulkhead
  crest, the hard edge between the harbour and the land behind it.
* ``shore_edge`` — the planimetric shoreline burned as a 1-sample-wide line. Nothing is interpolated
  across it: void filling is not allowed to cross a shoreline sample, so a hole in the DEM on the land
  side is never filled with a water elevation and vice versa.

All rasterisation uses the pixel-centre rule (``all_touched=False``) except the shoreline, so that a
sample belongs to water iff its lattice point lies inside a water polygon — the same test whichever tile
asks, which is what keeps tile seams identical.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np
import shapely
from rasterio.features import rasterize
from rasterio.transform import Affine

from ..water.build import HYDRO_PATH, SCHEMAS, SHORE_PATH, STRUCT_PATH, read_geoparquet

log = logging.getLogger("nycsim.terrain.hydro")

MAX_DECK_Z_M = 15.0   # above this a "pier" polygon is a bridge/viaduct deck, not a terrain surface
TIDAL_Z_M = 0.0


@dataclass
class TileHydro:
    water_z: np.ndarray      # float32, NaN outside open water
    deck_z: np.ndarray       # float32, NaN outside pier/jetty decks
    seawall_z: np.ndarray    # float32, NaN outside seawalls
    shore_edge: np.ndarray   # bool
    n_water: int
    n_deck: int
    n_seawall: int


class HydroLayers:
    """Loaded once per worker; serves per-tile rasters."""

    def __init__(self) -> None:
        h = read_geoparquet(HYDRO_PATH, SCHEMAS["hydrography"])
        flat = h[h["is_open_water"].values & (h["level_mode"].values != "dem")].copy()
        z = np.where(flat["level_mode"].values == "tidal", TIDAL_Z_M, flat["water_z_m"].values.astype(np.float64))
        bad = ~np.isfinite(z)
        if bad.any():
            log.warning("%d water bodies with a non-finite level are left to the DEM", int(bad.sum()))
        flat = flat[~bad]
        self.water_geom = flat.geometry.values
        self.water_z = z[~bad]
        # smallest last so that a pond inside a bay wins the pixel
        order = np.argsort(-shapely.area(self.water_geom), kind="stable")
        self.water_geom = self.water_geom[order]
        self.water_z = self.water_z[order]
        self.water_tree = shapely.STRtree(self.water_geom)

        s = read_geoparquet(STRUCT_PATH, SCHEMAS["structures"])
        deck = s[np.isin(s["kind"].values, ("pier", "jetty")) & np.isfinite(s["deck_z_m"].values) & (s["deck_z_m"].values <= MAX_DECK_Z_M)]
        self.n_deck_skipped_high = int((np.isin(s["kind"].values, ("pier", "jetty")) & (s["deck_z_m"].values > MAX_DECK_Z_M)).sum())
        self.deck_geom = deck.geometry.values
        self.deck_z = deck["deck_z_m"].values.astype(np.float64)
        dorder = np.argsort(-shapely.area(self.deck_geom), kind="stable")
        self.deck_geom, self.deck_z = self.deck_geom[dorder], self.deck_z[dorder]
        self.deck_tree = shapely.STRtree(self.deck_geom) if len(self.deck_geom) else None

        wall = s[(s["kind"].values == "seawall") & np.isfinite(s["deck_z_m"].values) & (s["deck_z_m"].values <= MAX_DECK_Z_M)]
        self.wall_geom = wall.geometry.values
        self.wall_z = wall["deck_z_m"].values.astype(np.float64)
        worder = np.argsort(-shapely.area(self.wall_geom), kind="stable")
        self.wall_geom, self.wall_z = self.wall_geom[worder], self.wall_z[worder]
        self.wall_tree = shapely.STRtree(self.wall_geom) if len(self.wall_geom) else None

        sl = read_geoparquet(SHORE_PATH, SCHEMAS["shoreline"])
        self.shore_geom = sl.geometry.values
        self.shore_tree = shapely.STRtree(self.shore_geom)
        log.info("hydro layers: %d flattened bodies, %d decks (%d high decks skipped), %d seawalls, %d shoreline parts",
                 len(self.water_geom), len(self.deck_geom), self.n_deck_skipped_high, len(self.wall_geom), len(self.shore_geom))

    @staticmethod
    def _burn(geoms, values, tree, transform: Affine, shape: tuple[int, int], win) -> np.ndarray:
        out = np.full(shape, np.nan, dtype=np.float32)
        if tree is None or len(geoms) == 0:
            return out
        idx = tree.query(win, predicate="intersects")
        if idx.size == 0:
            return out
        idx = np.sort(idx)  # keep the area order established in __init__ (large first, small last wins)
        rasterize(((geoms[i], float(values[i])) for i in idx), out=out, transform=transform, all_touched=False)
        return out

    def tile(self, transform: Affine, shape: tuple[int, int], bounds: tuple[float, float, float, float]) -> TileHydro:
        win = shapely.box(*bounds)
        water = self._burn(self.water_geom, self.water_z, self.water_tree, transform, shape, win)
        deck = self._burn(self.deck_geom, self.deck_z, self.deck_tree, transform, shape, win)
        wall = self._burn(self.wall_geom, self.wall_z, self.wall_tree, transform, shape, win)
        shore = np.zeros(shape, dtype=np.uint8)
        sidx = self.shore_tree.query(win, predicate="intersects")
        if sidx.size:
            rasterize(((self.shore_geom[i], 1) for i in np.sort(sidx)), out=shore, transform=transform, all_touched=True)
        return TileHydro(water, deck, wall, shore.astype(bool),
                         int(np.isfinite(water).sum()), int(np.isfinite(deck).sum()), int(np.isfinite(wall).sum()))
