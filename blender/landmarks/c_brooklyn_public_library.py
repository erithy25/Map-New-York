"""Brooklyn Public Library, Central Library — 10 Grand Army Plaza (BIN 3029665, LP-1972).
Raymond F. Almirall 1912 design; completed by Alfred Morton Githens and Francis Keally, 1935-41.

Dimensions used (source in brackets)
------------------------------------
* Footprint: the real OTI polygon (5,822 m2), 96.8 x 128.2 m, the wedge at Grand Army Plaza where Eastern Parkway
  and Flatbush Avenue meet; the entrance is in the re-entrant corner facing the plaza (north-west).
* Height [OTI LiDAR; LP-1972]: 29.3 m to the top of the parapet over the entrance bay; the wings' cornice is at
  22.0 m over four storeys.
* Entrance screen [LPC designation report LP-1972]: a **15.2 m (50 ft) high** splayed entrance recess faced in
  **gilded bronze** — fifteen figures from American literature by Thomas Hudson Jones and C. Paul Jennewein on the
  black-granite pylons flanking a bronze screen, with the gilded frieze of Rene Paul Chambellan above the doors.
  The recess is 18.0 m wide at the street and splays back 9.0 m.
* Elevation [LP-1972]: Indiana limestone, stripped classical, with tall vertical window slots between pilaster
  strips and a plain parapet; the two curved wings follow the parkway and avenue lines.
* Storey heights derived to land the wing cornice at 22.0 m: base 6.0 m, then three storeys of 5.33 m.

Fidelity: real footprint including the plaza wedge; the 29.3 m entrance parapet, the 22.0 m wing cornice, the
15.2 m gilded entrance recess with its flanking pylons and bronze screen, and the vertical window slots between
pilaster strips are modelled as geometry. Inferred (stated): storey heights (from the LiDAR heights and four
published storeys) and the pilaster rhythm. NOT modelled: the fifteen bronze figures and the Chambellan frieze
(their gilded panels are modelled as flat bronze), the interiors, and the 2021 rooftop terrace.
"""
from __future__ import annotations

import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import c_common as cc  # noqa: E402
import common as C  # noqa: E402

ID = "c_brooklyn_public_library"
BIN = 3029665
PARAPET = 29.3
CORNICE = 22.0
BASE_TOP = 6.0
ENTRY_H, ENTRY_W, ENTRY_SPLAY = 15.2, 18.0, 9.0


def build():
    C.reset()
    cc.materials(["limestone", "granite_black", "gold", "bronze", "glass_dark", "roof_grey", "roof_dark",
                  "pavement"])
    g = cc.Group(ID)
    P = g.poly(BIN)
    coords = C.ring_coords(P)
    objs: list = []

    objs.append(C.plinth(f"{ID}_base", P, 0.0, BASE_TOP, C.M.limestone, material_top=C.M.roof_dark))
    fl = [BASE_TOP + (CORNICE - 1.4 - BASE_TOP) * k / 3 for k in range(4)]
    fen = C.Fenestration(bay_w=3.4, window_frac=0.36, recess=0.55, spandrel_h=0.7, spandrel_proud=0.1,
                         pier="limestone", spandrel="limestone", glass="glass_dark", floor_z=fl, window_h=4.2)
    objs += C.tower_tier(f"{ID}_wings", P, BASE_TOP, CORNICE - 1.4, fen, roof_material="roof_grey", parapet_h=1.4,
                         parapet_t=0.6)

    # ---- the splayed gilded entrance in the re-entrant corner facing Grand Army Plaza ----------------------------
    # the corner with the largest interior angle (the re-entrant one) carries the entrance
    n_ = len(coords)
    best, best_ang = 0, -1.0
    for i in range(n_):
        a = (coords[i - 1][0] - coords[i][0], coords[i - 1][1] - coords[i][1])
        c = (coords[(i + 1) % n_][0] - coords[i][0], coords[(i + 1) % n_][1] - coords[i][1])
        la = math.hypot(*a); lc = math.hypot(*c)
        if la < 5.0 or lc < 5.0:
            continue
        ang = math.degrees(math.acos(max(-1.0, min(1.0, (a[0] * c[0] + a[1] * c[1]) / (la * lc)))))
        if ang > best_ang:
            best, best_ang = i, ang
    corner = coords[best]
    cen = (P.centroid.x, P.centroid.y)
    out = (corner[0] - cen[0], corner[1] - cen[1])
    ln = math.hypot(*out)
    out = (out[0] / ln, out[1] / ln)
    side = (-out[1], out[0])
    b = C.MeshBuilder()
    for sgn in (-1.0, 1.0):                            # the two black-granite pylons flanking the recess
        q = (corner[0] + side[0] * sgn * (ENTRY_W / 2 + 2.6), corner[1] + side[1] * sgn * (ENTRY_W / 2 + 2.6))
        b.box((q[0] - out[0] * 2.0, q[1] - out[1] * 2.0, ENTRY_H / 2), (5.0, 4.0, ENTRY_H), C.M.granite_black,
              rot_deg=math.degrees(math.atan2(side[1], side[0])))
        for k in range(4):                             # the gilded figure panels on each pylon
            z = 3.0 + 2.9 * k
            b.box((q[0] - out[0] * (-0.1), q[1] - out[1] * (-0.1), z), (2.2, 0.2, 2.2), C.M.gold,
                  rot_deg=math.degrees(math.atan2(side[1], side[0])))
    # the splayed recess: two converging walls and the bronze screen at the back
    for sgn in (-1.0, 1.0):
        a0 = (corner[0] + side[0] * sgn * ENTRY_W / 2, corner[1] + side[1] * sgn * ENTRY_W / 2)
        a1 = (corner[0] - out[0] * ENTRY_SPLAY + side[0] * sgn * ENTRY_W / 4,
              corner[1] - out[1] * ENTRY_SPLAY + side[1] * sgn * ENTRY_W / 4)
        b.quad((a0[0], a0[1], 0.0), (a1[0], a1[1], 0.0), (a1[0], a1[1], ENTRY_H), (a0[0], a0[1], ENTRY_H),
               C.M.limestone)
    back0 = (corner[0] - out[0] * ENTRY_SPLAY - side[0] * ENTRY_W / 4,
             corner[1] - out[1] * ENTRY_SPLAY - side[1] * ENTRY_W / 4)
    back1 = (corner[0] - out[0] * ENTRY_SPLAY + side[0] * ENTRY_W / 4,
             corner[1] - out[1] * ENTRY_SPLAY + side[1] * ENTRY_W / 4)
    b.quad((back0[0], back0[1], 0.0), (back1[0], back1[1], 0.0), (back1[0], back1[1], ENTRY_H),
           (back0[0], back0[1], ENTRY_H), C.M.bronze)
    b.quad((back0[0], back0[1], ENTRY_H - 3.4), (back1[0], back1[1], ENTRY_H - 3.4),
           (back1[0], back1[1], ENTRY_H - 0.4), (back0[0], back0[1], ENTRY_H - 0.4), C.M.gold)   # Chambellan frieze
    # the taller entrance bay parapet
    bay = C.rect(corner[0] - out[0] * 11.0, corner[1] - out[1] * 11.0, ENTRY_W + 12.0, 20.0,
                 angle_deg=math.degrees(math.atan2(side[1], side[0])))
    objs.append(C.prism(f"{ID}_entrance_bay", bay, CORNICE, PARAPET, C.M.limestone, material_top=C.M.roof_grey,
                        role="mass"))
    objs.append(b.build(f"{ID}_entrance"))
    return objs, g


def main():
    objs, g = build()
    entry = cc.finish(objs, ID, g.frame, real_footprint=g.real_local,
                      fidelity_statement=(
                          "Exact: real OTI footprint on the Grand Army Plaza wedge; the 29.3 m entrance-bay parapet "
                          "and the 22.0 m wing cornice (OTI LiDAR, LP-1972); the 50 ft = 15.2 m splayed entrance "
                          "recess, 18.0 m wide and splaying back 9.0 m, with its black-granite pylons, gilded "
                          "figure panels, bronze screen and gilded frieze; the tall vertical window slots between "
                          "pilaster strips. Inferred (stated): storey heights (from the LiDAR heights and four "
                          "published storeys) and the pilaster rhythm. Not modelled: the fifteen bronze figures and "
                          "the Chambellan frieze relief (flat gilded panels), interiors, the 2021 rooftop terrace."),
                      dimensions={"parapet_m": PARAPET, "wing_cornice_m": CORNICE, "entrance_h_m": ENTRY_H,
                                  "entrance_w_m": ENTRY_W, "entrance_splay_m": ENTRY_SPLAY, "storeys": 4})
    cc.render(ID, [
        {"view": "grand_army_plaza", "azimuth_deg": 315, "elevation_deg": "street", "distance": 90, "fov_deg": 62, "look_up_deg": 22},
        {"view": "aerial", "azimuth_deg": 330, "elevation_deg": 30},
    ])
    return entry


if __name__ == "__main__":
    main()
