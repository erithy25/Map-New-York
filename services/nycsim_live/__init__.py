"""NYCSim live services — reference implementation mirrored 1:1 in ``core/live`` (C++).

Modules: :mod:`timesync` (civil time/DST/JD/ΔT), :mod:`astronomy` (NREL SPA sun, Meeus moon,
Manhattanhenge), :mod:`metar` (METAR parser), :mod:`weather` (NWS / Open-Meteo / METAR providers and
the WeatherService), :mod:`esb_lights`, :mod:`tides`, :mod:`worldmapping`, :mod:`debug_overlay`.
Snapshot schemas: docs/DATA_CONTRACTS.md §12 (+ §12.1 extension appended by this stage).
"""
from __future__ import annotations

__version__ = "1.0.0"
SCHEMA_VERSION = 1
