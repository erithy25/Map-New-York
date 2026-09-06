"""Charging Bull — Bowling Green, Broadway at Morris Street. Arturo Di Modica, 1989.

This is a sculpture, not a building: it has **no building footprint** in the NYC Building Footprints dataset, so it is
placed by coordinates and the footprint-IoU check does not apply (``require_base=False``, ``bins=[]``).

Dimensions used (source in brackets)
------------------------------------
* Position: 40.70552 N, 74.01344 W [OpenStreetMap node / Wikipedia "Charging Bull"], which is NYC_TM
  (-5361, 615). The bull faces north up Broadway, head towards the Bowling Green fountain.
* Dimensions [Wikipedia "Charging Bull", Di Modica's own description]: 11 ft (3.4 m) tall, 16 ft (4.9 m) long, and
  7,100 lb (3,200 kg) of cast bronze — one of the largest bronzes cast in one piece in the United States.
* Ground: 5.49 m NAVD88, the LiDAR ground elevation of the nearest building footprint (BIN 1000811, 47 m away).
* Materials: cast bronze, patinated dark but rubbed to a polish on the horns, nose and rear by visitors — the model
  uses the ``bronze_patina`` palette entry for the body and ``bronze`` for the rubbed areas.

Fidelity: exact — position, orientation (facing north up Broadway), the published 3.4 m height and 4.9 m length, the
bronze material and the granite setts it stands on. Simplified — **the bull is a massing sculpture, not a scan**: the
body, neck, head, horns, four legs and tail are built from convex hulls fitted to the published overall dimensions and
to reference photographs, so the silhouette and stance (head lowered and turned left, tail whipped up to the right) are
right but the modelled musculature is not the cast surface. This is the largest single fidelity gap in agent A's set,
and it cannot be closed without a photogrammetric scan, which no open licence provides.
"""
from __future__ import annotations

import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import common as C  # noqa: E402

ID = "charging_bull"
BINS: list[int] = []
TM_X, TM_Y = -5361.2, 614.9
GROUND_Z = 5.486411          # LiDAR ground elevation of BIN 1000811, 47 m away
HEIGHT_M = 3.4               # 11 ft
LENGTH_M = 4.9               # 16 ft
HEADING_DEG = 29.0           # Broadway's compass heading here; the bull charges north


def _blob(b: C.MeshBuilder, sections, material) -> None:
    """Convex hull through a list of elliptical cross-sections ``(x, y, z, half_width, half_height)``."""
    pts = []
    for x, y, z, hw, hh in sections:
        for k in range(16):
            a = 2 * math.pi * k / 16
            pts.append((x, y + hw * math.cos(a), z + hh * math.sin(a)))
    b.hull(pts, material, smooth=True)


def build():
    C.reset()
    # No footprint: the frame is anchored on the published coordinates, +x along Broadway (the direction of the charge).
    fr = C.local_frame(C.rect(TM_X, TM_Y, 6.0, 6.0), GROUND_Z, angle_deg=90.0 - HEADING_DEG,
                       origin_xy=(TM_X, TM_Y))
    objs = []
    body_m, polish = C.M.bronze_patina, C.M.bronze
    b = C.MeshBuilder()

    # granite setts under the sculpture (Bowling Green paving), 7 x 5 m
    b.box((0.0, 0.0, -0.06), (7.0, 5.0, 0.12), C.M.granite_dark)

    bull = C.MeshBuilder()          # the animal itself, scaled to the published height once it is complete
    L = LENGTH_M
    # barrel of the body: shoulders forward (+x), haunches aft; the back line is 2.05 m above grade
    _blob(bull, [(-L * 0.42, 0.0, 1.42, 0.52, 0.42),      # rump
              (-L * 0.22, 0.0, 1.50, 0.72, 0.56),      # haunch
              (0.02, 0.0, 1.50, 0.78, 0.60),           # barrel
              (L * 0.22, 0.0, 1.52, 0.80, 0.62),       # chest/shoulder, the deepest section
              (L * 0.36, 0.0, 1.42, 0.62, 0.52)], body_m)
    # neck and lowered head, turned to the bull's left (+y)
    _blob(bull, [(L * 0.36, 0.05, 1.45, 0.55, 0.48),
              (L * 0.46, 0.16, 1.30, 0.46, 0.40),
              (L * 0.55, 0.26, 1.12, 0.38, 0.34)], body_m)
    _blob(bull, [(L * 0.55, 0.26, 1.10, 0.36, 0.32),
              (L * 0.66, 0.34, 1.02, 0.30, 0.30),
              (L * 0.76, 0.38, 0.92, 0.22, 0.22),
              (L * 0.82, 0.40, 0.84, 0.14, 0.14)], polish)          # muzzle (rubbed to a polish)
    # horns: swept up and out from the poll
    for sgn in (-1, 1):
        pts = []
        for f, r in ((0.0, 0.11), (0.35, 0.09), (0.7, 0.06), (1.0, 0.03)):
            hx = L * 0.66 + f * 0.30
            hy = 0.34 + sgn * (0.22 + f * 0.44)
            hz = 1.16 + f * 0.52 - f * f * 0.18
            for k in range(10):
                a = 2 * math.pi * k / 10
                pts.append((hx + r * math.cos(a), hy, hz + r * math.sin(a)))
        bull.hull(pts, polish, smooth=True)
    # four legs: front pair braced forward, hind pair gathered under the body (the charging stance)
    for lx, ly, foot_dx, top_r, bot_r in ((L * 0.30, 0.42, 0.16, 0.20, 0.12), (L * 0.30, -0.42, 0.16, 0.20, 0.12),
                                          (-L * 0.30, 0.40, -0.22, 0.24, 0.13), (-L * 0.30, -0.40, -0.22, 0.24, 0.13)):
        _blob(bull, [(lx, ly, 1.30, top_r * 1.4, top_r * 1.4),
                  (lx + foot_dx * 0.4, ly, 0.80, top_r, top_r),
                  (lx + foot_dx * 0.8, ly, 0.36, bot_r, bot_r),
                  (lx + foot_dx, ly, 0.10, bot_r * 1.5, 0.10)], body_m)
    # tail: whipped up and over to the bull's right
    pts = []
    for f, r in ((0.0, 0.13), (0.3, 0.10), (0.6, 0.07), (0.85, 0.05), (1.0, 0.07)):
        tx = -L * 0.44 - f * 0.28
        ty = -0.10 - f * 0.62
        tz = 1.55 + f * 1.20 - f * f * 0.35
        for k in range(10):
            a = 2 * math.pi * k / 10
            pts.append((tx + r * math.cos(a), ty, tz + r * math.sin(a)))
    bull.hull(pts, body_m, smooth=True)
    # the section radii come from reference photographs, so the modelled animal is scaled once, about the ground plane,
    # to the published 3.4 m height; its 4.9 m length is set directly by LENGTH_M above.
    zmax = max(v[2] for v in bull.v)
    k = HEIGHT_M / zmax
    bull.transform(C.Matrix.Diagonal((1.0, 1.0, k, 1.0)))
    b.merge(bull)
    objs.append(C.tag(b.build(f"{ID}_bronze"), "mass"))
    return objs, fr


def main():
    objs, fr = build()
    C.finish(objs, ID, BINS, fr, height_m=HEIGHT_M, name="Charging Bull",
             require_base=False,
             height_source="Wikipedia / Di Modica: 11 ft = 3.4 m tall, 16 ft = 4.9 m long, 7,100 lb = 3,200 kg cast bronze",
             footprint_source="none — a sculpture with no building footprint; placed at 40.70552 N, 74.01344 W (OpenStreetMap / Wikipedia) = NYC_TM (-5361, 615)",
             fidelity_statement=(
                 "This landmark has no building footprint (it is a sculpture), so no footprint IoU is computed. "
                 "Exact: position at Bowling Green, orientation charging north up Broadway, the published 3.4 m height "
                 "and 4.9 m length, and the patinated/rubbed bronze material split. Simplified — and this is the largest "
                 "single fidelity gap in agent A's set: the bull is a massing sculpture built from convex hulls fitted to "
                 "the published dimensions and to reference photographs, so the stance (head lowered and turned left, "
                 "horns swept up, tail whipped to the right, hind legs gathered) reads correctly but the modelled surface "
                 "is not the cast musculature. Closing it needs a photogrammetric scan, which no open licence provides."),
             notes="Ground elevation taken from the nearest footprint (BIN 1000811, 47 m away): 5.486 m NAVD88",
             dimensions={"height_m": HEIGHT_M, "length_m": LENGTH_M, "mass_kg": 3200, "heading_deg": HEADING_DEG,
                         "position_tm": [TM_X, TM_Y], "position_lonlat": [-74.01344, 40.70552],
                         "ground_z_navd88_m": GROUND_Z})
    C.render_check(ID, [
        {"view": "street", "azimuth_deg": 200, "elevation_deg": "street", "distance": 9.0, "eye_z": 1.65,
         "target_z": 1.7, "fov_deg": 55},
        {"view": "aerial", "azimuth_deg": 240, "elevation_deg": 30, "distance": 14.0, "fov_deg": 50, "target_z": 1.6},
    ])


if __name__ == "__main__":
    main()
