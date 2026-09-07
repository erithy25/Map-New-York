"""Terrain stage (ARCHITECTURE §5, DATA_CONTRACTS §3).

Pipeline: ``sources_3dep`` discovers/downloads USGS 3DEP DEMs -> ``ingest`` warps each one onto the
global 2 m NYC_TM sample lattice -> ``water`` (sibling package) classifies hydrography ->
``tiles`` composes, densifies, hydro-flattens and writes ``tiles/{tile}/terrain.png`` ->
``build.main`` drives everything, ``segment_z.sample_z`` serves elevations to other stages.
"""
