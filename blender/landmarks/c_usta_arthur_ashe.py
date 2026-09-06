"""Arthur Ashe Stadium — USTA Billie Jean King National Tennis Center, Flushing Meadows (BIN 4467715).
Rossetti Architects, 1997; retractable roof by Rossetti with WSP, 2016.

Dimensions used (source in brackets)
------------------------------------
* Footprint: the real OTI polygon (16,655 m2) — a regular octagon 153.7 m across the flats.
* Height [Rossetti published sections; USTA]: about **150 ft = 46.0 m** to the top of the roof trusses. The OTI
  LiDAR height, 17.7 m, pre-dates the 2016 roof and is not usable; the 46.0 m figure is scaled from Rossetti's
  published section and is flagged **inferred**.
* Retractable roof [Rossetti / WSP / Hardesty & Hanover, 2016]: a 6,500-tonne two-panel roof carried on **eight
  new columns** outside the original bowl, each on its own foundation; the panels are PTFE-coated fibreglass fabric
  and close a 62 x 62 m opening in 5-7 minutes. Modelled **open**, with the two panels parked over the north and
  south sides and the eight columns and the ring truss as separate geometry.
* Bowl [Rossetti]: 23,771 seats in three tiers around a court; the playing surface is DecoTurf, and the ITF court
  is 23.77 x 10.97 m inside a 36.6 x 18.3 m run-off.
* Facade [Rossetti]: precast concrete piers with an open steel-mesh screen between them and ramped entrance towers
  at four of the eight corners.

Fidelity: real octagonal footprint; the eight roof columns, the ring truss, the two parked roof panels over a
62 x 62 m opening, the three-tier bowl and the regulation court are modelled as geometry. Inferred (stated): the
overall 46.0 m height (scaled from a published section, +-2 m, because the LiDAR pre-dates the roof), the tier
rakes and the facade's pier rhythm. NOT modelled: the seats, the roof's drive machinery, the interiors and the
practice courts around the stadium.
"""
from __future__ import annotations

import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import c_common as cc  # noqa: E402
import common as C  # noqa: E402

ID = "c_usta_arthur_ashe"
BIN = 4467715
TOP = 46.0
BOWL_TOP = 33.0
OPENING = 62.0
COLUMNS = 8
COURT = (23.77, 10.97)
RUNOFF = (36.6, 18.3)
CAPACITY = 23771


def build():
    C.reset()
    cc.materials(["concrete", "concrete_dark", "steel_dark", "steel_galvanized" if False else "aluminium",
                  "marble_white", "grass", "asphalt", "roof_dark", "pavement", "glass_dark"])
    g = cc.Group(ID)
    P = g.poly(BIN)
    cx, cy = P.centroid.x, P.centroid.y
    objs: list = []

    objs.append(C.plinth(f"{ID}_base", P, 0.0, 6.0, C.M.concrete, material_top=C.M.pavement))
    # the three-tier bowl
    b = C.MeshBuilder()
    for z0, r0, z1, r1 in ((0.0, 30.0, 9.0, 44.0), (11.0, 46.0, 20.0, 58.0), (22.0, 60.0, BOWL_TOP, 72.0)):
        b.loft([[(cx + r0 * math.cos(2 * math.pi * k / 48), cy + r0 * math.sin(2 * math.pi * k / 48), z0)
                 for k in range(48)],
                [(cx + r1 * math.cos(2 * math.pi * k / 48), cy + r1 * math.sin(2 * math.pi * k / 48), z1)
                 for k in range(48)]], C.M.concrete_dark, cap_top=False, cap_bottom=False)
    objs.append(C.tag(b.build(f"{ID}_bowl"), "mass"))
    # the court
    b = C.MeshBuilder()
    b.prism(C.ring_coords(C.rect(cx, cy, RUNOFF[0], RUNOFF[1])), 0.0, 0.05, C.M.asphalt)
    b.prism(C.ring_coords(C.rect(cx, cy, COURT[0], COURT[1])), 0.05, 0.06, C.M.grass)
    for line in (C.rect(cx, cy, COURT[0], COURT[1]), C.rect(cx, cy, COURT[0], 8.23)):
        b.loft([[(x, y, 0.07) for x, y in C.ring_coords(line)],
                [(x, y, 0.07) for x, y in C.offset_ring(C.ring_coords(line), -0.1)]], C.M.marble_white,
               cap_top=False, cap_bottom=False)
    objs.append(C.tag(b.build(f"{ID}_court"), "field"))

    # ---- the precast facade -------------------------------------------------------------------------------------
    b = C.MeshBuilder()
    for p0, p1, L, t, n in C.edges_of(C.ring_coords(P)):
        npier = max(2, int(round(L / 6.2)))
        for k in range(npier + 1):
            q0 = p0 + t * (min(L, k * (L / npier)) - 0.8)
            q1 = q0 + t * 1.6
            b.box_from_to(q0, q1, n, 1.2, 0.0, BOWL_TOP, C.M.concrete)
        for j in range(6):                                # the open steel-mesh screen between the piers
            z = 6.0 + (BOWL_TOP - 8.0) * j / 6
            b.box_from_to(p0, p1, n, 0.5, z, z + 0.25, C.M.aluminium)
    objs.append(b.build(f"{ID}_facade"))

    # ---- the retractable roof: eight columns, the ring truss and the two parked panels ---------------------------
    b = C.MeshBuilder()
    R = 78.0
    for k in range(COLUMNS):
        a = 2 * math.pi * (k + 0.5) / COLUMNS
        q = (cx + R * math.cos(a), cy + R * math.sin(a))
        b.box((q[0], q[1], TOP / 2), (3.2, 3.2, TOP), C.M.concrete)
        b.box((q[0], q[1], 1.6), (6.0, 6.0, 3.2), C.M.concrete)                       # the separate foundation
    ring = [(cx + R * math.cos(2 * math.pi * k / 48), cy + R * math.sin(2 * math.pi * k / 48)) for k in range(48)]
    cc.band_ring(b, ring, TOP - 6.0, TOP - 1.0, 1.6, C.M.steel_dark)
    for k in range(24):                                                                # the radial roof trusses
        a = 2 * math.pi * k / 24
        q0 = (cx + R * math.cos(a), cy + R * math.sin(a))
        q1 = (cx + (OPENING / 2 + 2.0) * math.cos(a), cy + (OPENING / 2 + 2.0) * math.sin(a))
        b.hull([(q0[0] - 0.5, q0[1] - 0.5, TOP - 6.0), (q0[0] + 0.5, q0[1] + 0.5, TOP - 6.0),
                (q0[0] - 0.5, q0[1] + 0.5, TOP - 6.0), (q0[0] + 0.5, q0[1] - 0.5, TOP - 6.0),
                (q1[0] - 0.5, q1[1] - 0.5, TOP - 2.5), (q1[0] + 0.5, q1[1] + 0.5, TOP - 2.5),
                (q1[0] - 0.5, q1[1] + 0.5, TOP - 2.5), (q1[0] + 0.5, q1[1] - 0.5, TOP - 2.5)], C.M.steel_dark)
    for sgn in (-1.0, 1.0):                              # the two PTFE panels, parked open
        y0 = cy + sgn * (OPENING / 2 + 1.0)
        y1 = cy + sgn * (R - 4.0)
        b.quad((cx - OPENING / 2, y0, TOP - 2.0), (cx + OPENING / 2, y0, TOP - 2.0),
               (cx + OPENING / 2, y1, TOP - 1.0), (cx - OPENING / 2, y1, TOP - 1.0), C.M.marble_white)
        b.quad((cx - OPENING / 2, y1, TOP - 1.0), (cx + OPENING / 2, y1, TOP - 1.0),
               (cx + OPENING / 2, y0, TOP - 2.0), (cx - OPENING / 2, y0, TOP - 2.0), C.M.marble_white)
    objs.append(C.tag(b.build(f"{ID}_roof"), "roof"))
    return objs, g


def main():
    objs, g = build()
    entry = cc.finish(objs, ID, g.frame, real_footprint=g.real_local,
                      fidelity_statement=(
                          "Exact: real octagonal OTI footprint (153.7 m across the flats); the eight roof columns "
                          "on their own foundations, the ring truss and 24 radial trusses, the two PTFE roof panels "
                          "parked open over a 62 x 62 m opening; a three-tier bowl and a regulation 23.77 x 10.97 m "
                          "court in a 36.6 x 18.3 m run-off; precast piers with a steel-mesh screen. INFERRED and "
                          "flagged: the 46.0 m overall height (+-2 m, scaled from Rossetti's published section, "
                          "because the OTI LiDAR height of 17.7 m pre-dates the 2016 roof); the tier rakes and the "
                          "pier rhythm. Not modelled: the 23,771 seats, the roof drive machinery, interiors, and "
                          "the surrounding practice courts."),
                      dimensions={"top_m": TOP, "top_m_source": "inferred from published section, +-2 m",
                                  "bowl_top_m": BOWL_TOP, "roof_opening_m": OPENING, "roof_columns": COLUMNS,
                                  "court_m": list(COURT), "runoff_m": list(RUNOFF), "capacity": CAPACITY})
    cc.render(ID, [
        {"view": "plaza", "azimuth_deg": 200, "elevation_deg": "street", "distance": 190, "fov_deg": 60, "look_up_deg": 16},
        {"view": "aerial", "azimuth_deg": 220, "elevation_deg": 32},
    ])
    return entry


if __name__ == "__main__":
    main()
