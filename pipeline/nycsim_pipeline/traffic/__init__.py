"""Traffic calibration stage (ARCHITECTURE §9/§10, DATA_CONTRACTS §10).

Produces ``data/processed/traffic/density.parquet`` (NTA × hour × day-type vehicle density,
pedestrian density and modal shares), ``data/processed/traffic/fleet_mix.json`` and, when the
runtime exporter exists, ``runtime/density.nycb``.

Modules
-------
``sources_extra``  dynamic registration of the extra inputs (TLC, DOT classification / pedestrian /
                   bicycle counts, DSNY frequencies) with the foundation downloader.
``fetch``          downloads those inputs (idempotent, manifest-recorded), including a column
                   subset of the TLC high-volume FHV trip file read through HTTP range requests.
``geo``            NTA-2020 polygons in NYC_TM, point-in-polygon and area-overlay helpers.
``segments``       CSCL centerline -> per-segment lane-km, road class, posted speed, NTA.
``counts``         DOT Automated Traffic Volume Counts -> per-segment hourly flow by day type.
``landuse``        MapPLUTO -> per-NTA floor-area densities (regression features).
``model``          NTA aggregation, land-use regression for uncounted NTAs, Greenshields density.
``pedestrians``    pedestrian density model calibrated to the DOT Bi-Annual Pedestrian Counts.
``shares``         taxi / truck / bus / bike shares.
``fleet_mix``      per-class base shares by borough/CBD and time band.
``build``          CLI entry point (``python -m nycsim_pipeline traffic``).
``report``         maps and tables for docs/verification/traffic_density/REPORT.md.
"""
from __future__ import annotations

SCHEMA_NAME = "traffic/density@1"
N_NTA_EXPECTED = 262
HOURS = 24
DAY_TYPES = 3  # 0 weekday, 1 saturday, 2 sunday
