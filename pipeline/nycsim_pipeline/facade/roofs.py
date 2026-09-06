"""Roof shape for the pitched-roof house stock (ADR-013).

The NYC 3-D Building Model is stepped **flat massing**: measured over 395,891 parsed buildings only 28 have any roof
surface sloped more than 2 degrees.  ADR-013 therefore splits the two facts apart:

* ``ROOF_REAL`` (fidelity bit 2) means the LOD2 solid exists — real roof height, real setback levels.  It comes from
  ``buildings/roof_attrs.parquet`` (``citygml_match``) and this module never touches it.
* ``ROOF_INFERRED`` (fidelity bit 13) means the roof **shape** was derived here, from PLUTO building class, footprint
  aspect ratio and era, for the classes that really have pitched roofs: PLUTO A0-A9 (one family), B1-B9 (two family),
  C0 (three-family walk-up) and detached S-class houses, concentrated in Queens, Staten Island and outer Brooklyn.

The measured ``roof_z`` is kept as the **ridge** height, so the building's overall height stays real; the eave drops
below it by the rise implied by the pitch and the footprint's short side.

Which eligible buildings actually get a pitch is decided by the **facade class**: ``facade_classes.json`` states the
roof of every typology (``flat_parapet``, ``flat_cornice``, ``pitched_low``, ``pitched_steep``, ``pitched_tile``,
``pitched_dormer``, ...).  A Park Slope brownstone or a Ridgewood brick two-family is a flat roof behind a cornice or a
parapet and stays flat; the Queens / Staten Island detached house, the Tudor, the garden apartment, the Mediterranean
Revival house and the church are pitched.  That keeps the inference inside the typology the kit already models instead
of putting gables on half of Brooklyn.

Shape decision, among the eligible buildings whose class is pitched (in order):

1. an accessory garage or a one-storey outbuilding under 80 m^2 -> **shed** (feature code 5110 is direct evidence of
   an outbuilding, whatever its lot's class says);
2. an LPC designation naming Second Empire or a mansard -> **mansard**;
3. a class whose roof is ``pitched_tile``, or a free-standing squarish footprint (aspect < 1.4) -> **hip** (the
   interwar and post-war Queens / Staten Island detached house);
4. anything else -> **gable**, ridge along the long axis (the NYC attached and semi-detached house presents a gable
   end to the street).

Pitch is the published norm for the era: 38 deg for pre-1900 and Tudor/Queen Anne/Victorian styles, 30 deg for
1900-1944, 22 deg for 1945 and later (the post-war low-slope ranch and split level), 10 deg for a shed, 65 deg for the
lower slope of a mansard.
"""
from __future__ import annotations

import numpy as np

from . import enums as E

ROOF_SRC_CITYGML = 0
ROOF_SRC_OSM = 1
ROOF_SRC_FACADE_RULE = 2
ROOF_SRC_DEFAULT_FLAT = 3

FIDELITY_ROOF_INFERRED = 1 << 13

#: PLUTO classes whose stock really has a pitched roof (ADR-013).
PITCHED_ONE_FAMILY = ("A0", "A1", "A2", "A3", "A4", "A5", "A6", "A7", "A8", "A9")
PITCHED_TWO_FAMILY = ("B1", "B2", "B3", "B9")
PITCHED_WALKUP = ("C0",)
PITCHED_MIXED = ("S0", "S1", "S2")           # only when free-standing
PITCHED_CONDO_HOUSE = ("R1", "R2", "R3", "R6")

NARROW_SHORT_SIDE_M = 9.0
SQUARE_ASPECT = 1.4
NARROW_ASPECT = 1.8
GARAGE_MAX_AREA_M2 = 80.0
DETACHED_SHORT_SIDE_M = 14.0      # ADR-013's geometric test for the detached house stock
DETACHED_MAX_AREA_M2 = 400.0
MIN_RISE_M = 0.8
MAX_RISE_M = 4.0
MIN_EAVE_ABOVE_GROUND_M = 2.2

PITCH_PREWAR_DEG = 38.0
PITCH_INTERWAR_DEG = 30.0
PITCH_POSTWAR_DEG = 22.0
PITCH_SHED_DEG = 10.0
PITCH_MANSARD_DEG = 65.0


def eligible(bldg_class: np.ndarray, feature_code: np.ndarray, attached: np.ndarray, floors: np.ndarray,
             area: np.ndarray) -> np.ndarray:
    """Buildings whose roof shape this stage owns (ADR-013)."""
    cls = np.asarray(bldg_class)
    house = np.isin(cls, list(PITCHED_ONE_FAMILY + PITCHED_TWO_FAMILY + PITCHED_WALKUP + PITCHED_CONDO_HOUSE))
    mixed_detached = np.isin(cls, list(PITCHED_MIXED)) & (attached == 0)
    outbuilding = (feature_code == 5110) & (area <= GARAGE_MAX_AREA_M2)
    return (house | mixed_detached | outbuilding) & (floors <= 4)


def infer(bldg_class: np.ndarray, feature_code: np.ndarray, year: np.ndarray, floors: np.ndarray, area: np.ndarray,
          attached: np.ndarray, short_m: np.ndarray, long_m: np.ndarray, ridge_heading: np.ndarray,
          lpc_style: np.ndarray, ground_z: np.ndarray, roof_z: np.ndarray, class_roof: np.ndarray, class_is_tile: np.ndarray
          ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """``(roof_type, pitch_deg, ridge_heading, eave_z, applied)`` for the eligible house stock.

    ``class_roof`` is the roof_type the building's facade class declares (``facade_classes.json``); only buildings
    whose class is pitched — or accessory outbuildings — get a pitched roof here.  ``applied`` marks the rows this
    function actually produced a non-flat shape for; those are the ``ROOF_INFERRED`` buildings.
    """
    n = len(bldg_class)
    roof = np.zeros(n, dtype=np.int8)
    pitch = np.zeros(n, dtype=np.float32)
    eave = np.asarray(roof_z, dtype=np.float32).copy()
    ridge = np.zeros(n, dtype=np.float32)
    outbuilding = (feature_code == 5110) & (area <= GARAGE_MAX_AREA_M2)
    style = np.asarray([s.lower() for s in lpc_style], dtype=object)
    # a designation report naming Second Empire or a mansard is direct evidence of a mansard roof, whatever the
    # facade class's default roof is: the mansard *is* the defining feature of the type
    mansard_style = np.asarray([("second empire" in s) or ("mansard" in s) for s in style], dtype=bool)
    victorian = np.asarray([any(k in s for k in ("queen anne", "victorian", "gothic", "stick", "shingle style",
                                                 "tudor", "romanesque")) for s in style], dtype=bool)
    # a free-standing house with a side yard, a rowhouse-width footprint and at most three storeys is the detached
    # house stock: it really has a pitched roof even where its facade class is one of the flat-roofed brick types
    # (the ADR-013 geometric test, measured at precision 0.83 against the OSM ``roof:shape`` ground truth)
    detached_house = ((attached == 0) & (short_m <= DETACHED_SHORT_SIDE_M) & (floors <= 3)
                      & (area <= DETACHED_MAX_AREA_M2))
    ok = (eligible(bldg_class, feature_code, attached, floors, area)
          & ((class_roof != E.ROOF_FLAT) | outbuilding | detached_house | mansard_style))
    if not ok.any():
        return roof, pitch, ridge, eave, ok

    with np.errstate(invalid="ignore", divide="ignore"):
        aspect = np.where(short_m > 0.1, long_m / short_m, 1.0)

    shed = ok & (outbuilding | ((floors <= 1) & (area < 60.0)))
    mansard = ok & mansard_style & ~shed
    square = ok & ((attached == 0) & (aspect < SQUARE_ASPECT) | class_is_tile) & ~shed & ~mansard

    roof = np.where(ok, E.ROOF_GABLE, roof).astype(np.int8)
    roof = np.where(square, E.ROOF_HIP, roof).astype(np.int8)
    roof = np.where(mansard, E.ROOF_MANSARD, roof).astype(np.int8)
    roof = np.where(shed, E.ROOF_SHED, roof).astype(np.int8)

    p = np.where((year > 0) & (year < 1900), PITCH_PREWAR_DEG,
                 np.where(year >= 1945, PITCH_POSTWAR_DEG, PITCH_INTERWAR_DEG))
    p = np.where(victorian, PITCH_PREWAR_DEG, p)
    p = np.where(roof == E.ROOF_SHED, PITCH_SHED_DEG, p)
    p = np.where(roof == E.ROOF_MANSARD, PITCH_MANSARD_DEG, p)
    pitch = np.where(ok, p, 0.0).astype(np.float32)

    half = np.where(roof == E.ROOF_SHED, np.maximum(short_m, 0.5), np.maximum(short_m, 0.5) * 0.5)
    rise = np.clip(half * np.tan(np.deg2rad(np.minimum(pitch, 60.0))), MIN_RISE_M, MAX_RISE_M)
    e = np.asarray(roof_z, dtype=np.float64) - rise
    e = np.maximum(e, np.asarray(ground_z, dtype=np.float64) + MIN_EAVE_ABOVE_GROUND_M)
    e = np.minimum(e, np.asarray(roof_z, dtype=np.float64))
    eave = np.where(ok, e, roof_z).astype(np.float32)
    ridge = np.where(ok, np.asarray(ridge_heading, dtype=np.float32) % 180.0, 0.0).astype(np.float32)
    return roof, pitch, ridge, eave, ok


def mrr_axes(geoms: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Minimum rotated rectangle of each footprint -> (short side m, long side m, long-axis compass heading)."""
    import shapely
    n = len(geoms)
    if n == 0:
        z = np.zeros(0, dtype=np.float32)
        return z, z, z
    mrr = shapely.oriented_envelope(geoms)
    coords, idx = shapely.get_coordinates(mrr, return_index=True)
    short = np.zeros(n, dtype=np.float64)
    long = np.zeros(n, dtype=np.float64)
    head = np.zeros(n, dtype=np.float64)
    # every oriented envelope is a 5-point closed ring; degenerate ones (lines/points) fall back to the bbox
    starts = np.flatnonzero(np.concatenate([[True], idx[1:] != idx[:-1]]))
    counts = np.diff(np.append(starts, len(idx)))
    good = counts >= 4
    gi = idx[starts][good]
    gs = starts[good]
    p0 = coords[gs]
    p1 = coords[gs + 1]
    p2 = coords[gs + 2]
    a = np.hypot(p1[:, 0] - p0[:, 0], p1[:, 1] - p0[:, 1])
    b = np.hypot(p2[:, 0] - p1[:, 0], p2[:, 1] - p1[:, 1])
    long_is_a = a >= b
    short[gi] = np.where(long_is_a, b, a)
    long[gi] = np.where(long_is_a, a, b)
    dx = np.where(long_is_a, p1[:, 0] - p0[:, 0], p2[:, 0] - p1[:, 0])
    dy = np.where(long_is_a, p1[:, 1] - p0[:, 1], p2[:, 1] - p1[:, 1])
    head[gi] = np.degrees(np.arctan2(dx, dy)) % 180.0        # compass heading of the long axis, folded to [0, 180)
    bad = ~np.isin(np.arange(n), gi)
    if bad.any():
        xmin, ymin, xmax, ymax = shapely.bounds(geoms[bad]).T
        w, h = np.maximum(xmax - xmin, 0.1), np.maximum(ymax - ymin, 0.1)
        short[bad] = np.minimum(w, h)
        long[bad] = np.maximum(w, h)
        head[bad] = np.where(w >= h, 90.0, 0.0)
    return short.astype(np.float32), long.astype(np.float32), head.astype(np.float32)
