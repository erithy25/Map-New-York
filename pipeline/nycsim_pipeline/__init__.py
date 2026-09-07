"""NYCSim data pipeline.

Stages (see docs/ARCHITECTURE.md §15) are idempotent and manifest-tracked. Run with
``python -m nycsim_pipeline <stage> [options]``.
"""
__version__ = "1.0.0"
SCHEMA_VERSION = 1
