"""Roof-form classifier for CityGML LOD2 buildings (docs/DATA_CONTRACTS.md §5 ``roof_type`` enum).

Input: the planar roof faces of one building (area, unit normal, heights). Output: the
``roof_type`` code, the number of distinct horizontal roof levels and a few summary numbers.

Codes
-----
0 flat, 1 gable, 2 hip, 3 mansard, 4 shed, 5 sawtooth, 6 complex, 7 dome, 8 barrel

Definitions
-----------
* A face is *horizontal* when its slope (angle between the normal and the vertical) is below
  ``FLAT_SLOPE_DEG`` (8°: covers drainage pitch and LiDAR fitting noise; real pitched roofs in
  NYC start at ~15°).
* A face is *vertical-ish* when its slope exceeds ``VERTICAL_SLOPE_DEG`` (85°); those are
  parapet/step sides that the modeller tagged as roof and are ignored by the shape rules.
* *Sloped* faces are the rest. Faces smaller than ``max(SMALL_FACE_M2, SMALL_FACE_FRAC * total)``
  are ignored for the shape rules (dormers, chimneys, LiDAR crumbs) but still count in areas.
* Sloped faces are grouped by *azimuth* (the compass direction they face) with a gap tolerance
  of ``AZ_TOL_DEG`` (25°). Two clusters are *opposite* when their mean azimuths differ by
  180° ± ``OPPOSITE_TOL_DEG``.

Decision order (first match wins)
---------------------------------
1. No usable roof face                                    → 0 flat (caller flags NO_ROOF)
2. horizontal area ≥ 75 % of total, or sloped area < 10 % → 0 FLAT
3. sloped area < 50 % of total (mixed massing)            → 6 COMPLEX
4. MANSARD: steep faces (≥ 55°) hold ≥ 25 % of the sloped area, come from ≥ 2 azimuth
   clusters, and the roof also has a flat deck (≥ 10 % horizontal) or shallow (< 35°) upper faces
5. DOME: ≥ 6 sloped faces in ≥ 4 azimuth clusters none holding > 40 % of the sloped area,
   slopes spanning ≥ 25°
6. BARREL: ≥ 5 sloped faces, two opposite clusters ≥ 85 % of sloped area, slopes inside each
   cluster spanning ≥ 25° (the progressive facets of a vault)
7. SAWTOOTH: (a) one azimuth cluster ≥ 85 % with ≥ 3 faces of similar size (max/min ≤ 4) and
   similar ridge heights (std of z_max ≤ 1.5 m) — parallel shed-lets whose steep glazed sides are
   modelled as walls; or (b) two opposite clusters with ≥ 2 faces each where one side is ≥ 1.5×
   steeper than the other (alternating steep/shallow profile)
8. GABLE: exactly two opposite clusters covering ≥ 85 % of the sloped area, each ≥ 20 %
   (a gambrel — two pitches per side — also lands here; there is no gambrel code)
9. HIP: ≥ 3 clusters covering ≥ 85 %, pairwise ≥ 60° apart, cluster slopes all < 55° with
   max/min ≤ 1.8 (a cross-gable has the same signature and is reported as hip)
10. SHED: one cluster ≥ 85 % of the sloped area with ≤ 2 faces (a single plane)
11. otherwise                                             → 6 COMPLEX

``n_roof_levels`` is the number of clusters of horizontal-face heights with a gap tolerance of
``LEVEL_TOL_M`` (0.3 m). Buildings whose roof has no horizontal face report 0 levels.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .citygml_geom import angular_distance_deg, circular_mean_deg, cluster_1d, cluster_circular

ROOF_FLAT, ROOF_GABLE, ROOF_HIP, ROOF_MANSARD, ROOF_SHED, ROOF_SAWTOOTH, ROOF_COMPLEX, ROOF_DOME, ROOF_BARREL = range(9)
ROOF_NAMES = ("flat", "gable", "hip", "mansard", "shed", "sawtooth", "complex", "dome", "barrel")

FLAT_SLOPE_DEG = 8.0
VERTICAL_SLOPE_DEG = 85.0
STEEP_SLOPE_DEG = 55.0
SHALLOW_SLOPE_DEG = 35.0
AZ_TOL_DEG = 25.0
OPPOSITE_TOL_DEG = 30.0
SMALL_FACE_M2 = 0.5
SMALL_FACE_FRAC = 0.01
LEVEL_TOL_M = 0.3
COVERAGE = 0.85


@dataclass
class RoofFace:
    area3d: float
    area_xy: float
    slope_deg: float
    azimuth_deg: float
    z_min: float
    z_max: float
    z_mean: float


@dataclass
class RoofClass:
    roof_type: int
    n_roof_levels: int
    level_z: list[float] = field(default_factory=list)       # ascending distinct horizontal roof heights
    level_area: list[float] = field(default_factory=list)    # horizontal area (m^2) per level
    z_main: float = float("nan")                              # height of the largest horizontal level, else roof z_max
    slope_deg: float = 0.0                                    # area-weighted mean slope of sloped faces
    flat_frac: float = 1.0
    sloped_frac: float = 0.0


@dataclass
class _Cluster:
    idx: np.ndarray
    area: float
    az: float
    n: int
    slope: float
    slope_min: float
    slope_max: float
    zmax_std: float
    area_ratio: float


def _clusters(az: np.ndarray, area: np.ndarray, slope: np.ndarray, zmax: np.ndarray) -> list[_Cluster]:
    out: list[_Cluster] = []
    for g in cluster_circular(az, AZ_TOL_DEG):
        a = area[g]
        out.append(_Cluster(
            idx=g, area=float(a.sum()), az=circular_mean_deg(az[g], a), n=int(g.size),
            slope=float((slope[g] * a).sum() / a.sum()), slope_min=float(slope[g].min()), slope_max=float(slope[g].max()),
            zmax_std=float(zmax[g].std()) if g.size > 1 else 0.0,
            area_ratio=float(a.max() / max(a.min(), 1e-9)),
        ))
    out.sort(key=lambda c: -c.area)
    return out


def _opposite(c1: _Cluster, c2: _Cluster) -> bool:
    return abs(angular_distance_deg(c1.az, c2.az) - 180.0) <= OPPOSITE_TOL_DEG


def roof_levels(faces: list[RoofFace]) -> tuple[list[float], list[float]]:
    """Distinct heights of horizontal roof faces (ascending) and the horizontal area of each level."""
    flat = [f for f in faces if f.slope_deg < FLAT_SLOPE_DEG]
    if not flat:
        return [], []
    z = np.array([f.z_mean for f in flat])
    a = np.array([f.area_xy for f in flat])
    zs: list[float] = []
    ar: list[float] = []
    for g in cluster_1d(z, LEVEL_TOL_M):
        w = a[g]
        zs.append(float((z[g] * w).sum() / w.sum()) if w.sum() > 0 else float(z[g].mean()))
        ar.append(float(w.sum()))
    return zs, ar


def classify_roof(faces: list[RoofFace]) -> RoofClass:
    """Classify the roof form of one building; see the module docstring for the rules."""
    faces = [f for f in faces if f.area3d > 0]
    if not faces:
        return RoofClass(ROOF_FLAT, 0)
    level_z, level_area = roof_levels(faces)
    zmax_all = max(f.z_max for f in faces)
    z_main = level_z[int(np.argmax(level_area))] if level_z else zmax_all

    area = np.array([f.area3d for f in faces])
    slope = np.array([f.slope_deg for f in faces])
    az = np.array([f.azimuth_deg for f in faces])
    zmax = np.array([f.z_max for f in faces])
    total = float(area.sum())
    horiz = slope < FLAT_SLOPE_DEG
    vertical = slope > VERTICAL_SLOPE_DEG
    sloped = ~horiz & ~vertical
    flat_frac = float(area[horiz].sum() / total)
    sloped_frac = float(area[sloped].sum() / total)
    small = area < max(SMALL_FACE_M2, SMALL_FACE_FRAC * total)
    sig = sloped & ~small
    mean_slope = float((slope[sloped] * area[sloped]).sum() / area[sloped].sum()) if sloped.any() else 0.0

    def result(code: int) -> RoofClass:
        return RoofClass(code, len(level_z), level_z, level_area, z_main, mean_slope, flat_frac, sloped_frac)

    if flat_frac >= 0.75 or sloped_frac < 0.10 or not sig.any():
        return result(ROOF_FLAT)
    if sloped_frac < 0.50:
        return result(ROOF_COMPLEX)

    s_idx = np.nonzero(sig)[0]
    s_area = area[s_idx]
    s_slope = slope[s_idx]
    s_total = float(s_area.sum())
    cl = _clusters(az[s_idx], s_area, s_slope, zmax[s_idx])
    n_faces = int(s_idx.size)

    # 4. mansard
    steep = s_slope >= STEEP_SLOPE_DEG
    steep_area = float(s_area[steep].sum())
    if steep_area >= 0.25 * s_total:
        steep_clusters = len(cluster_circular(az[s_idx][steep], AZ_TOL_DEG))
        shallow_area = float(s_area[s_slope < SHALLOW_SLOPE_DEG].sum())
        if steep_clusters >= 2 and (flat_frac >= 0.10 or shallow_area >= 0.10 * total):
            return result(ROOF_MANSARD)

    top1 = cl[0].area / s_total
    top2 = (cl[0].area + cl[1].area) / s_total if len(cl) > 1 else top1
    slope_span = float(s_slope.max() - s_slope.min())

    # 5. dome
    if n_faces >= 6 and len(cl) >= 4 and top1 <= 0.40 and slope_span >= 25.0:
        return result(ROOF_DOME)
    # 6. barrel
    if n_faces >= 5 and len(cl) >= 2 and top2 >= COVERAGE and _opposite(cl[0], cl[1]) \
            and (cl[0].slope_max - cl[0].slope_min) >= 25.0 and (cl[1].slope_max - cl[1].slope_min) >= 25.0:
        return result(ROOF_BARREL)
    # 7. sawtooth
    if top1 >= COVERAGE and cl[0].n >= 3 and cl[0].area_ratio <= 4.0 and cl[0].zmax_std <= 1.5:
        return result(ROOF_SAWTOOTH)
    if len(cl) >= 2 and top2 >= COVERAGE and _opposite(cl[0], cl[1]) and cl[0].n >= 2 and cl[1].n >= 2:
        hi, lo = max(cl[0].slope, cl[1].slope), max(min(cl[0].slope, cl[1].slope), 1e-6)
        if hi / lo >= 1.5:
            return result(ROOF_SAWTOOTH)
    # 8. gable
    if len(cl) >= 2 and top2 >= COVERAGE and _opposite(cl[0], cl[1]) and cl[1].area >= 0.20 * s_total:
        return result(ROOF_GABLE)
    # 9. hip
    if len(cl) >= 3:
        k = 0
        cov = 0.0
        while k < len(cl) and cov < COVERAGE:
            cov += cl[k].area / s_total
            k += 1
        main = cl[:k]
        if len(main) >= 3 and cov >= COVERAGE:
            sep_ok = all(angular_distance_deg(a.az, b.az) >= 60.0 for i, a in enumerate(main) for b in main[i + 1:])
            slopes = [c.slope for c in main]
            if sep_ok and max(slopes) < STEEP_SLOPE_DEG and max(slopes) / max(min(slopes), 1e-6) <= 1.8:
                return result(ROOF_HIP)
    # 10. shed
    if top1 >= COVERAGE and cl[0].n <= 2:
        return result(ROOF_SHED)
    return result(ROOF_COMPLEX)
