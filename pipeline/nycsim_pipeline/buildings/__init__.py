"""Buildings stage (ARCHITECTURE §4, DATA_CONTRACTS §5).

``build.py``     — footprints + PLUTO + LPC + DCWP/DOHMH + DOB sheds -> ``buildings_base.parquet`` and per-tile files.
``citygml.py``   — CityGML LOD2 roof matching (separate agent; not imported here).
"""
