"""Hearst Tower — 300 West 57th Street (BIN 1025451, base LP-1974). Joseph Urban & George B. Post 1928 base;
Foster + Partners tower, 2006.

Dimensions used (source in brackets)
------------------------------------
* Footprint: the real OTI polygon (3,542 m2), the whole Eighth Avenue block front between West 56th and 57th Streets
  with its two cut corners.
* Height [CTBUH]: 597 ft = 182.0 m, 46 floors.
* Base [LPC designation report LP-1974]: the 1928 International Magazine Building, 6 storeys, 40.0 m to the top of
  its cast-stone parapet; giant fluted piers with allegorical figure groups over the Eighth Avenue entrance and at
  the corners; the interior was demolished in 2004 and the base is now a shell around the atrium.
* Diagrid tower [Foster + Partners; WSP Cantor Seinuk structural papers]: the triangulated frame is built from
  four-storey, 40 ft = 12.19 m wide modules, so each triangle is 12.19 m wide and (4 x 3.55 =) 14.20 m tall. The
  corners "bird's-mouth": the plan alternates between a full corner at one module line and a 4.0 m chamfer at the
  next, which is what makes the faceted corner notches. 40 tower floors of 3.55 m carry 40.0 m -> 182.0 m.
* Elevation [Foster + Partners]: the diagonals are stainless-clad steel, ~0.9 m deep, standing 0.55 m proud of a
  low-iron glass curtain wall with a horizontal transom at every floor line.

Fidelity: real footprint; published height, floor count, 12.19 m x 4-storey diagrid module and the alternating
bird's-mouth corners modelled as geometry, on the real 6-storey cast-stone base with its giant piers. Inferred
(stated): the 4.0 m corner chamfer and the diagonal member size (from photographs, +-0.5 m); the Urban base's
sculpture groups are represented as blocked-out masses, not modelled figures. NOT modelled: the atrium, the
"Icefall" water sculpture, the roof plant, and the sculptural detail of the 1928 allegorical figures.
"""
from __future__ import annotations

import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import c_common as cc  # noqa: E402
import common as C  # noqa: E402
from shapely.geometry import Polygon  # noqa: E402

ID = "c_hearst_tower"
BIN = 1025451
ROOF_M = 182.0
BASE_TOP = 40.0
FLOOR_H = 3.55
MODULE_W = 12.19          # 40 ft
MODULE_H = 4 * FLOOR_H    # 14.20 m
CHAMFER = 4.0


def corner_ring(cx, cy, w, d, ch):
    """8-vertex ring: each corner split into two points ``ch`` apart along the edges (ch = 0 -> a sharp corner)."""
    hw, hd = w / 2, d / 2
    return [(cx - hw + ch, cy - hd), (cx + hw - ch, cy - hd), (cx + hw, cy - hd + ch), (cx + hw, cy + hd - ch),
            (cx + hw - ch, cy + hd), (cx - hw + ch, cy + hd), (cx - hw, cy + hd - ch), (cx - hw, cy - hd + ch)]


def build():
    C.reset()
    cc.materials(["limestone", "concrete", "glass_blue", "steel_nirosta", "roof_dark", "granite_grey", "bronze"])
    g = cc.Group(ID, angle_deg=cc.GRID_ANGLE)
    P = g.poly(BIN)
    cx = (P.bounds[0] + P.bounds[2]) / 2
    cy = (P.bounds[1] + P.bounds[3]) / 2
    objs: list = []

    # ---- 1928 cast-stone base (IoU volume) --------------------------------------------------------------------
    objs += cc.base_and_wall(f"{ID}_base", P, BASE_TOP - 2.2, C.M.limestone, recess=0.75, material_top=C.M.roof_dark)
    b = C.MeshBuilder()
    coords = C.ring_coords(P)
    for p0, p1, L, t, n in C.edges_of(coords):
        if L < 6.0:
            continue
        npier = max(2, int(round(L / 7.4)))
        mod = L / npier
        for k in range(npier + 1):
            u = min(L, k * mod)
            q0 = p0 + t * max(0.0, u - 1.35); q1 = p0 + t * min(L, u + 1.35)
            b.box_from_to(q0, q1, n, 0.9, 0.0, BASE_TOP - 4.0, C.M.limestone)       # giant fluted pier
            for f in range(3):                                                       # three flutes per pier
                fq0 = q0 + t * (0.55 + f * 0.75); fq1 = fq0 + t * 0.35
                b.box_from_to(fq0, fq1, n, 1.02, 6.0, BASE_TOP - 5.6, C.M.limestone)
            if k in (0, npier):                                                      # corner sculpture group mass
                b.box((q0[0] + n[0] * 1.3, q0[1] + n[1] * 1.3, BASE_TOP - 3.0), (2.6, 2.6, 4.2), C.M.limestone,
                      rot_deg=math.degrees(math.atan2(t[1], t[0])))
        # recessed bays: ground-floor glazing and the punched windows of floors 2-6
        for k in range(npier):
            a = p0 + t * (k * mod + 1.35); c = p0 + t * ((k + 1) * mod - 1.35)
            if float(((c - a) ** 2).sum()) ** 0.5 < 1.2:
                continue
            C.window_punch(b, a, c, n, 1.7, 7.4, 0.9, C.M.limestone, C.M.glass_clear, sill=0.0)
            C.punched_wall(b, a, c, n, 7.4, BASE_TOP - 4.0, [7.4 + i * 5.3 for i in range(1, 6)], C.M.limestone,
                           C.M.glass_dark, bays=2, window_w=1.9, window_h=3.1, sill_h=0.9, depth=0.6)
    objs.append(b.build(f"{ID}_base_order"))
    objs.append(C.cornice(f"{ID}_base_cornice", P, BASE_TOP - 2.2, [(0.35, 0.0), (0.9, 0.7), (0.9, 1.4), (0.4, 2.2)],
                          C.M.limestone))

    # ---- the diagrid tower ----------------------------------------------------------------------------------------
    plan_w = (P.bounds[2] - P.bounds[0]) - 4.2
    plan_d = (P.bounds[3] - P.bounds[1]) - 4.2
    sharp = corner_ring(cx, cy, plan_w, plan_d, 0.0)
    cut = corner_ring(cx, cy, plan_w, plan_d, CHAMFER)
    nlevel = int(round((ROOF_M - BASE_TOP) / MODULE_H))
    rings = []
    for k in range(nlevel + 1):
        z = BASE_TOP + k * (ROOF_M - BASE_TOP) / nlevel
        src = sharp if k % 2 == 0 else cut
        rings.append([(x, y, z) for x, y in src])
    objs.append(C.tag(C.loft(f"{ID}_tower_glass", rings, C.M.glass_blue, material_top=C.M.roof_dark), "mass"))
    # horizontal transom at every floor line
    b = C.MeshBuilder()
    for k in range(nlevel):
        r0, r1 = rings[k], rings[k + 1]
        for f in range(1, 4):
            s = f / 4.0
            ring = [(a[0] + (bq[0] - a[0]) * s, a[1] + (bq[1] - a[1]) * s, a[2] + (bq[2] - a[2]) * s)
                    for a, bq in zip(r0, r1)]
            out = [(x, y, z) for (x, y, z) in ring]
            b.loft([out, [(x, y, z + 0.16) for x, y, z in out]], C.M.steel_nirosta, cap_top=False, cap_bottom=False)
    objs.append(b.build(f"{ID}_transoms"))

    # ---- the diagonals -------------------------------------------------------------------------------------------
    b = C.MeshBuilder()
    import numpy as np
    for k in range(nlevel):
        r0 = rings[k]; r1 = rings[k + 1]
        for i in range(len(r0)):
            j = (i + 1) % len(r0)
            a0 = np.array(r0[i][:2]); a1 = np.array(r0[j][:2])
            b0 = np.array(r1[i][:2]); b1 = np.array(r1[j][:2])
            L = float(np.linalg.norm(a1 - a0))
            if L < 2.0:
                continue
            nmod = max(1, int(round(L / MODULE_W)))
            z0, z1 = r0[i][2], r1[i][2]
            nrm = np.array([(a1 - a0)[1], -(a1 - a0)[0]]) / L
            for m in range(nmod):
                for u0f, u1f in ((m / nmod, (m + 0.5) / nmod), ((m + 1) / nmod, (m + 0.5) / nmod)):
                    p = a0 + (a1 - a0) * u0f + nrm * 0.30
                    q = b0 + (b1 - b0) * u1f + nrm * 0.30
                    pts = []
                    for (X, Y, Z) in ((p[0], p[1], z0), (q[0], q[1], z1)):
                        for dn in (0.0, 0.55):
                            for dz in (-0.45, 0.45):
                                pts.append((X + nrm[0] * dn, Y + nrm[1] * dn, Z + dz))
                    b.hull(pts, C.M.steel_nirosta)
    objs.append(b.build(f"{ID}_diagrid"))
    objs.append(C.prism(f"{ID}_roof_plant", C.rect(cx, cy, plan_w - 22, plan_d - 22), ROOF_M - 3.0, ROOF_M,
                        C.M.steel_nirosta, material_top=C.M.roof_dark, role="mass"))
    return objs, g


def main():
    objs, g = build()
    entry = cc.finish(objs, ID, g.frame, real_footprint=g.real_local,
                      fidelity_statement=(
                          "Exact: real OTI footprint, 182.0 m / 46 floors (CTBUH), the 1928 six-storey cast-stone "
                          "base at 40.0 m with its giant fluted piers, and a diagrid of 12.19 m x four-storey "
                          "(14.20 m) modules with alternating bird's-mouth corners. Inferred (stated, from "
                          "photographs): the 4.0 m corner chamfer and the 0.9 m diagonal depth. Not modelled: the "
                          "atrium and Icefall, roof plant detail, and the sculptural modelling of the 1928 "
                          "allegorical figure groups (blocked-out masses only)."),
                      dimensions={"roof_m": ROOF_M, "floors": 46, "base_top_m": BASE_TOP, "floor_h_m": FLOOR_H,
                                  "diagrid_module_w_m": MODULE_W, "diagrid_module_h_m": MODULE_H,
                                  "corner_chamfer_m": CHAMFER})
    cc.render(ID, [
        {"view": "eighth_ave", "azimuth_deg": 260, "elevation_deg": "street", "distance": 230, "fov_deg": 48, "look_up_deg": 38},
        {"view": "aerial", "azimuth_deg": 230, "elevation_deg": 26},
    ])
    return entry


if __name__ == "__main__":
    main()
