"""Facade classification and kit placement (ADR-004, DATA_CONTRACTS §5 / §6).

Three passes, each idempotent and separately runnable (``python -m nycsim_pipeline facade <pass>``):

* ``geom``  — footprint edge runs, party-wall detection, street-facing classification -> ``facade/edges/*.parquet``
  and the per-building summary ``facade/geom_attrs.parquet``;
* ``rules`` — the versioned rule table (``rules.py``) plus OSM/LPC material evidence -> ``facade/facade_attrs.parquet``;
* ``emit``  — extends every ``tiles/{tile}/buildings.parquet`` to the complete DATA_CONTRACTS §5 schema and writes
  ``tiles/{tile}/kit_placements.bin`` + ``.json``.

Every building classified by the rule table carries fidelity bit 10 ``FACADE_INFERRED``; bit 5 ``MATERIAL_REAL`` is set
only where an OSM ``building:material`` / ``building:colour`` tag or an LPC designation-report material applies
(ADR-004).
"""
from __future__ import annotations

SCHEMA_VERSION = 1
RULES_VERSION = "facade-rules/1"
