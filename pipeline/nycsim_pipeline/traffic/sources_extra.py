"""Extra data sources for the traffic stage, registered dynamically with the foundation registry.

``sources.py`` is foundation code and is not edited; :func:`register_source` inserts additional
:class:`~nycsim_pipeline.sources.Source` records into ``SOURCES`` at import time so that the
standard downloader (``nycsim_pipeline.download.download``) fetches and manifest-records them.

Sources
-------
* ``tlc_zone_monthly``            TLC "Pickups and Drop-offs by Taxi Zone and Industry" (c5iv-bn4s)
* ``dot_vehicle_class_counts``    DOT Vehicle Classification Counts 2011-2025 (96ay-ea4r)
* ``dot_ped_counts_biannual``     DOT Bi-Annual Pedestrian Counts, tabular (cqsj-cfgu)
* ``dot_bike_ped_sensors``        DOT Bicycle and Pedestrian Count Sensors (6up2-gnw8)
* ``dot_bike_ped_hourly``         DOT Bicycle and Pedestrian Counts (ct66-47at) aggregated server-side
                                   to sensor × travel mode × hour × day-of-week for 2024-01-01 onwards
* ``dsny_frequencies``            DSNY collection frequencies by section (rv63-53db)
* ``tlc_yellow_2025_05``          TLC yellow taxi trip records, May 2025 (parquet, CloudFront)
* ``tlc_green_2025_05``           TLC green (boro) taxi trip records, May 2025
* ``tlc_fhvhv_2025_05``           TLC high-volume FHV trip records, May 2025 — 517 MB; only the
                                   columns needed are read through HTTP range requests (see fetch.py)

May 2025 was chosen as the reference month because it is the most recent full spring month
(DOT's own counts are taken in spring/autumn) available in every TLC file at build time.
"""
from __future__ import annotations

import logging

from ..sources import NYC_ATTR, NYC_OPEN_DATA_LICENSE, SOCRATA_NYC, SOURCES, Source

log = logging.getLogger("nycsim.traffic.sources")

TLC_CLOUDFRONT = "https://d37ci6vzurychx.cloudfront.net/trip-data"
TLC_LICENSE = "NYC TLC Trip Record Data — public data released by the NYC Taxi & Limousine Commission (no licence restrictions stated; attribution requested)"
TLC_ATTR = "NYC Taxi and Limousine Commission"
REFERENCE_MONTH = "2025-05"

# SODA server-side aggregation: sensor × mode × hour × dow, from 2024-01-01 (recent counter set).
_SENSOR_AGG_QUERY = (
    "$select=sensor_id,travelmode,date_extract_hh(timestamp)%20AS%20hh,date_extract_dow(timestamp)%20AS%20dow,"
    "sum(counts)%20AS%20counts,count(*)%20AS%20n"
    "&$where=timestamp%20%3E%3D%20%272024-01-01T00:00:00%27%20AND%20status%20!%3D%20%27deleted%27"
    "&$group=sensor_id,travelmode,hh,dow&$limit=200000"
)


def _extra_sources() -> list[Source]:
    return [
        Source("tlc_zone_monthly", f"{SOCRATA_NYC}/api/views/c5iv-bn4s/rows.csv?accessType=DOWNLOAD", "csv",
               NYC_OPEN_DATA_LICENSE, NYC_ATTR,
               "TLC monthly pickups and drop-offs by taxi zone and industry (Yellow, Green, FHV-High Volume, FHV-Other)",
               "socrata_csv", tags=("traffic", "c5iv-bn4s")),
        Source("dot_vehicle_class_counts", f"{SOCRATA_NYC}/api/views/96ay-ea4r/rows.csv?accessType=DOWNLOAD", "csv",
               NYC_OPEN_DATA_LICENSE, NYC_ATTR,
               "DOT Vehicle Classification Counts 2011-2025: hourly volumes per segment/direction/date by class (auto, taxi, truck, bus, ...)",
               "socrata_csv", tags=("traffic", "96ay-ea4r")),
        Source("dot_ped_counts_biannual", f"{SOCRATA_NYC}/api/views/cqsj-cfgu/rows.csv?accessType=DOWNLOAD", "csv",
               NYC_OPEN_DATA_LICENSE, NYC_ATTR,
               "DOT Bi-Annual Pedestrian Counts: 114 locations, weekday AM (7-9), midday (12-14), PM (16-19) totals, May/Sept-Oct 2007-2026",
               "socrata_csv", tags=("traffic", "pedestrians", "cqsj-cfgu")),
        Source("dot_bike_ped_sensors", f"{SOCRATA_NYC}/api/views/6up2-gnw8/rows.csv?accessType=DOWNLOAD", "csv",
               NYC_OPEN_DATA_LICENSE, NYC_ATTR,
               "DOT Bicycle and Pedestrian Count Sensors: permanent counter sites with coordinates and travel modes",
               "socrata_csv", tags=("traffic", "6up2-gnw8")),
        Source("dot_bike_ped_hourly", f"{SOCRATA_NYC}/resource/ct66-47at.csv?{_SENSOR_AGG_QUERY}", "csv",
               NYC_OPEN_DATA_LICENSE, NYC_ATTR,
               "DOT Bicycle and Pedestrian Counts (15-min) aggregated server-side to sensor × mode × hour × day-of-week, 2024-01-01 onwards",
               "file", filename="dot_bike_ped_hourly.csv", tags=("traffic", "ct66-47at")),
        Source("dsny_frequencies", f"{SOCRATA_NYC}/api/geospatial/rv63-53db?method=export&format=GeoJSON", "geojson",
               NYC_OPEN_DATA_LICENSE, NYC_ATTR,
               "DSNY collection frequencies by sanitation section (refuse/recycling/organics/bulk collection days)",
               "socrata_geojson", tags=("traffic", "sanitation", "rv63-53db")),
        Source("tlc_yellow_2025_05", f"{TLC_CLOUDFRONT}/yellow_tripdata_{REFERENCE_MONTH}.parquet", "parquet",
               TLC_LICENSE, TLC_ATTR, "TLC yellow taxi trip records, May 2025 (pickup/dropoff time and taxi zone)",
               "file", filename=f"yellow_tripdata_{REFERENCE_MONTH}.parquet", tags=("tlc", "traffic")),
        Source("tlc_green_2025_05", f"{TLC_CLOUDFRONT}/green_tripdata_{REFERENCE_MONTH}.parquet", "parquet",
               TLC_LICENSE, TLC_ATTR, "TLC green (street-hail livery) taxi trip records, May 2025",
               "file", filename=f"green_tripdata_{REFERENCE_MONTH}.parquet", tags=("tlc", "traffic")),
        Source("tlc_fhvhv_2025_05", f"{TLC_CLOUDFRONT}/fhvhv_tripdata_{REFERENCE_MONTH}.parquet", "parquet",
               TLC_LICENSE, TLC_ATTR,
               "TLC high-volume for-hire vehicle (Uber/Lyft) trip records, May 2025 — column subset read by HTTP range requests",
               "file", filename=f"fhvhv_tripdata_{REFERENCE_MONTH}.cols.parquet", tags=("tlc", "traffic")),
    ]


def register_source(src: Source, *, replace: bool = False) -> Source:
    """Insert ``src`` into the foundation ``SOURCES`` registry.

    Idempotent for identical re-registration; a different definition under an existing id raises
    unless ``replace`` is set (never silently shadow a foundation source).
    """
    existing = SOURCES.get(src.id)
    if existing is not None:
        if existing == src:
            return existing
        if not replace:
            raise ValueError(f"source id {src.id!r} already registered with a different definition")
        log.warning("replacing source definition %s", src.id)
    SOURCES[src.id] = src
    return src


def register_all() -> list[Source]:
    """Register every extra traffic source; returns the registered records."""
    out = []
    for s in _extra_sources():
        out.append(register_source(s))
    return out


EXTRA_SOURCES: dict[str, Source] = {s.id: s for s in register_all()}
