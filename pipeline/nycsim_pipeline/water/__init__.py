"""Water stage (DATA_CONTRACTS §4): hydrography, shoreline and hydro-structure GeoParquet + per-tile water summary.

Inside the city boundary the NYC planimetric database (2022 aerials) is authoritative; outside it
(NJ half of the Hudson, Newark Bay, Arthur Kill west bank, Raritan Bay, Long Island Sound off Nassau,
the Atlantic beyond the city line) water polygons come from OpenStreetMap (coastline + water areas),
flagged ``source = 'osm'``. Levels (``tidal``, ``water_z_m``) are set by the terrain stage from the
composed DEM and the planimetric water-elevation points; see ``build.finalize_levels``.
"""
