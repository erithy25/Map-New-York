"""Traffic calibration stage (ARCHITECTURE §9/§10, DATA_CONTRACTS §10 and §15).

Produces ``data/processed/traffic/density.parquet`` (2020 NTA × hour × day-type vehicle density,
pedestrian density and modal shares), ``data/processed/traffic/fleet_mix.json`` and
``data/processed/runtime/density.nycb``.

Modules
-------
``sources_extra``  dynamic registration of the extra inputs (TLC, DOT classification / pedestrian /
                   bicycle counts, DSNY frequencies) with the foundation downloader.
``fetch``          downloads those inputs (idempotent, manifest-recorded), including a column
                   subset of the TLC high-volume FHV trip file read through HTTP range requests.
``geo``            NTA-2020 and taxi-zone polygons in NYC_TM, point-in-polygon and area overlay.
``segments``       CSCL centerline -> per-segment lane-km, road class, posted speed, NTA.
``counts``         DOT Automated Traffic Volume Counts -> per-segment hourly flow by day type.
``landuse``        MapPLUTO -> lot points and per-NTA floor-area / lot-use features.
``accessibility``  subway entrances, distance to the Manhattan core, expressway proximity, PLUTO
                   garage area per dwelling.
``model``          site matching, diurnal profiles, the two-stage level regression and the per
                   segment assembly into NTA × hour × day-type flow and density.
``speed``          road-class speed-flow curves, calibrated per NTA and hour against TLC journey
                   speeds; converts flow into vehicles per km of lane.
``tlc``            TLC trip records -> for-hire vehicle-km per corridor and local journey speeds.
``sidewalks``      planimetric sidewalk polygons -> walkable sidewalk area per NTA.
``pedestrians``    pedestrian density calibrated to the DOT Bi-Annual Pedestrian Counts.
``shares``         taxi / truck / bus / bike shares of the road-user stream.
``fleet_mix``      per-VehicleClass shares by borough, CBD flag and time band.
``runtime_export`` ``runtime/density.nycb`` in the DATA_CONTRACTS §15 layout.
``build``          CLI entry point (``python -m nycsim_pipeline.traffic.build``).
``report``         maps and tables for docs/verification/traffic_density/.
"""
from __future__ import annotations

SCHEMA_NAME = "traffic/density@1"
N_NTA_EXPECTED = 262
HOURS = 24
DAY_TYPES = 3  # 0 weekday, 1 saturday, 2 sunday
