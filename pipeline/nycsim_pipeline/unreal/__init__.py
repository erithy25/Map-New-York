"""Unreal Engine hand-off: ``unreal_manifest.json`` generator (DATA_CONTRACTS §14) and UE-readable exports.

UE's embedded Python has no pyarrow, so everything the editor scripts need is exported here as JSON, PNG or raw
little-endian binary. Run with ``python -m nycsim_pipeline.unreal.manifest``.
"""
