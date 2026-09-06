"""Bronx County Courthouse (Mario Merola Building) — 851 Grand Concourse (BIN 2002869, LP-1027).
Joseph H. Freedlander and Max Hausle, 1931-34.

Dimensions used (source in brackets)
------------------------------------
* Footprint: the real OTI polygon (5,477 m2), a 92.6 x 96.7 m near-square block bounded by the Grand Concourse
  (west), East 161st Street (south), Walton Avenue (east) and East 158th Street.
* Height [LPC designation report LP-1027; OTI LiDAR]: nine storeys with a four-storey central tower; the tower's
  parapet is at 58.5 m and the main cornice at 40.0 m.
* Elevation [LP-1027]: a stripped-classical block faced in **Mohegan granite** over a two-storey rusticated base,
  with giant square piers, deeply recessed window bays and **four monumental limestone sculpture groups by Adolph
  A. Weinman, Edward Field Sanford Jr., George Snowden and Charles Keck** set on the setback above the eighth floor;
  a continuous limestone frieze runs above the second storey.
* Entrance [LP-1027]: the Grand Concourse and 161st Street fronts each have a portico of **four square granite piers
  17.0 m tall** over a broad flight of granite steps.
* Storey heights derived so the cornice lands at 40.0 m: base 10.0 m for two storeys, then seven storeys of 4.29 m.

Fidelity: real footprint; the 58.5 m tower, the 40.0 m cornice, the two-storey rusticated granite base, the giant
piers and recessed bays, the limestone frieze, the two four-pier porticoes and the four sculpture-group plinths are
modelled as geometry. Inferred (stated): the storey heights (derived from the LiDAR heights and the published nine
storeys) and the bay rhythm. NOT modelled: the sculpture groups themselves (their granite plinths are modelled as
blocks), the frieze's carved relief, the interiors and the courtrooms.
"""
from __future__ import annotations

import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import c_common as cc  # noqa: E402
import common as C  # noqa: E402

ID = "c_bronx_county_courthouse"
BIN = 2002869
TOWER_TOP = 58.5
CORNICE = 40.0
BASE_TOP = 10.0
PORTICO_H = 17.0


def build():
    C.reset()
    cc.materials(["granite_grey", "granite_dark", "limestone", "glass_dark", "roof_grey", "roof_dark", "bronze"])
    g = cc.Group(ID, angle_deg=cc.GRID_ANGLE)
    P = g.poly(BIN)
    coords = C.ring_coords(P)
    objs: list = []

    objs.append(C.plinth(f"{ID}_base", P, 0.0, BASE_TOP, C.M.granite_dark, material_top=C.M.roof_dark))
    fl = [BASE_TOP + (CORNICE - 2.0 - BASE_TOP) * k / 7 for k in range(8)]
    fen = C.Fenestration(bay_w=4.3, window_frac=0.56, recess=1.1, spandrel_h=1.1, spandrel_proud=0.2,
                         pier="granite_grey", spandrel="granite_grey", glass="glass_dark", floor_z=fl, window_h=3.0)
    objs += C.tower_tier(f"{ID}_body", P, BASE_TOP, CORNICE - 2.0, fen, roof_material="roof_grey", parapet_h=0.0)
    b = C.MeshBuilder()
    for p0, p1, L, t, n in C.edges_of(coords):
        for z in (2.6, 5.2, 7.8):                                   # rusticated courses in the base
            b.box_from_to(p0, p1, n, 0.22, z - 0.16, z, C.M.granite_dark)
        b.box_from_to(p0, p1, n, 0.45, BASE_TOP, BASE_TOP + 1.6, C.M.limestone)     # the limestone frieze
    objs.append(b.build(f"{ID}_base_detail"))
    objs.append(C.cornice(f"{ID}_cornice", P, CORNICE - 2.0,
                          [(0.6, 0.0), (1.8, 1.1), (1.8, 1.7), (0.6, 2.0)], C.M.limestone))

    # ---- the two porticoes ---------------------------------------------------------------------------------------
    b = C.MeshBuilder()
    for ang in (180.0, -90.0):                                     # Grand Concourse (west) and 161st Street (south)
        p0, p1, L, t, n = C.edge_facing(coords, ang)
        mid = (p0 + p1) / 2
        for k in range(4):
            u = -9.0 + 6.0 * k
            q = mid + t * u + n * 2.4
            b.box((q[0], q[1], BASE_TOP - 3.0 + PORTICO_H / 2), (2.1, 2.1, PORTICO_H), C.M.granite_grey,
                  rot_deg=math.degrees(math.atan2(t[1], t[0])))
        b.box_from_to(mid - t * 11.5, mid + t * 11.5, n, 3.8, BASE_TOP - 3.0 + PORTICO_H,
                      BASE_TOP - 3.0 + PORTICO_H + 2.2, C.M.granite_grey)
        for k in range(14):                                        # the granite steps
            z = 3.4 * (k + 1) / 14
            d = 0.5 * (14 - k)
            b.box_from_to(mid - t * 13.0, mid + t * 13.0, n, 2.4 + d, 0.0, z, C.M.granite_grey)
    objs.append(b.build(f"{ID}_porticoes"))

    # ---- the setback tower and the four sculpture plinths --------------------------------------------------------
    tower = C.offset_polygon(P, -14.0)
    fen_t = C.Fenestration(floor_h=(TOWER_TOP - 3.0 - CORNICE) / 4, bay_w=4.3, window_frac=0.5, recess=0.8,
                           spandrel_h=1.0, spandrel_proud=0.18, pier="granite_grey", spandrel="granite_grey",
                           glass="glass_dark")
    objs += C.tower_tier(f"{ID}_tower", tower, CORNICE, TOWER_TOP - 3.0, fen_t, roof_material="roof_grey",
                         parapet_h=3.0, parapet_t=0.8)
    b = C.MeshBuilder()
    for ang in (0.0, 90.0, 180.0, -90.0):                          # the four Weinman/Sanford/Snowden/Keck groups
        p0, p1, L, t, n = C.edge_facing(coords, ang)
        mid = (p0 + p1) / 2 - n * 8.0
        b.box((mid[0], mid[1], CORNICE + 2.2), (9.0, 4.0, 4.4), C.M.limestone,
              rot_deg=math.degrees(math.atan2(t[1], t[0])))
    objs.append(b.build(f"{ID}_sculpture_plinths"))
    return objs, g


def main():
    objs, g = build()
    entry = cc.finish(objs, ID, g.frame, real_footprint=g.real_local,
                      fidelity_statement=(
                          "Exact: real OTI footprint; the 58.5 m setback tower and the 40.0 m cornice (OTI LiDAR, "
                          "LP-1027); the two-storey rusticated Mohegan-granite base with its limestone frieze; the "
                          "giant piers and deeply recessed bays; the two porticoes of four 17.0 m square granite "
                          "piers over granite steps; the four sculpture-group plinths on the eighth-floor setback. "
                          "Inferred (stated): the storey heights (derived from the LiDAR heights and nine published "
                          "storeys) and the bay rhythm. Not modelled: the four sculpture groups themselves (their "
                          "plinths only), the carved relief of the frieze, the interiors and courtrooms."),
                      dimensions={"tower_top_m": TOWER_TOP, "cornice_m": CORNICE, "base_top_m": BASE_TOP,
                                  "portico_pier_h_m": PORTICO_H, "storeys": 9})
    cc.render(ID, [
        {"view": "grand_concourse", "azimuth_deg": 250, "elevation_deg": "street", "distance": 110, "fov_deg": 60, "look_up_deg": 22},
        {"view": "aerial", "azimuth_deg": 230, "elevation_deg": 30},
    ])
    return entry


if __name__ == "__main__":
    main()
