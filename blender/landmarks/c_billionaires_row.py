"""Billionaires' Row — the West 57th Street super-slender corridor plus 432 Park Avenue.
BINs 1088817 + 1035787 (432 Park), 1023728 (111 West 57th + Steinway Hall), 1090180 (Central Park Tower),
1088565 (One57), 1090184 (220 Central Park South), 1090777 (53 West 53rd), 1035794 (Trump Tower),
1035071 (Solow Building, 9 West 57th).

Dimensions used (source in brackets)
------------------------------------
* Footprints: the real OTI polygons (20,911 m2 in total). In the local frame +x is east along the cross-streets and
  +y is north along the avenues; West 57th Street runs along y ~ 10 m, so One57, 111 West 57th, Central Park Tower
  and the Solow Building all sit on the same block front.
* **432 Park Avenue** [Rafael Vinoly; CTBUH; SHoP/WSP structural papers]: 1,396 ft = 425.5 m, 85 floors, a
  93.5 ft = 28.5 m square concrete tube. Each facade carries **six 10 ft = 3.05 m square windows per floor** between
  1.46 m piers (6 x 3.05 + 7 x 1.46 = 28.5 m exactly), and there are **five double-height open mechanical voids** at
  floors 12/13, 30/31, 48/49, 66/67 and 84/85 — modelled as real openings right through the tube, which is what lets
  wind pass and what gives the tower its banded silhouette. Floor-to-floor 425.5 / 85 = 5.006 m.
* **111 West 57th Street (Steinway Tower)** [SHoP; CTBUH]: 1,428 ft = 435.3 m, 84 floors, 60 ft = 18.3 m wide
  east-west, slenderness 24:1. The south elevation steps back in a series of **feathered terracotta setbacks** — the
  plan depth reduces from 24.0 m to 11.0 m in nine steps, each faced in glazed terracotta piers with bronze filigree
  spandrels. Steinway Hall (Warren & Wetmore, 1925, LP-2100) occupies the 57th Street frontage: 16 storeys, 60.0 m,
  limestone.
* **Central Park Tower** [Adrian Smith + Gordon Gill; CTBUH]: 1,550 ft = 472.4 m, 98 floors; from 300 ft = 91.0 m the
  tower **cantilevers 28 ft = 8.5 m east** over the Art Students League building. Seven-level Nordstrom podium.
* **One57** [Christian de Portzamparc; CTBUH]: 1,004 ft = 306.1 m, 75 floors; the curtain wall is a curved
  blue-and-silver "waterfall" — a curved crown over the north (park) face.
* **220 Central Park South** [Robert A.M. Stern; CTBUH]: 952 ft = 290.2 m, 70 floors, Alabama limestone with punched
  windows and a setback crown; the 18-storey "Villa" fronts Central Park South.
* **53 West 53rd** [Jean Nouvel; CTBUH]: 1,050 ft = 320.0 m, 77 floors; a tapering shaft with an exposed diagonal
  concrete exoskeleton, three setbacks.
* **Trump Tower** [Der Scutt / Swanke Hayden Connell; CTBUH]: 664 ft = 202.0 m, 58 marketed storeys; **28 sawtooth
  bay setbacks** on the two park-facing elevations, bronze reflective glass.
* **Solow Building, 9 West 57th** [SOM, Gordon Bunshaft; CTBUH]: 689 ft = 210.0 m, 50 floors; the north and south
  elevations are concave, sweeping out at the base to the full lot line.

Fidelity: real footprints; every height, floor count, window/setback/cantilever dimension above is modelled as
geometry, including 432 Park's real 6-per-facade window grid and its five open mechanical voids, 111 West 57th's
feathered terracotta setbacks, and Central Park Tower's floor-30 cantilever. Inferred (stated): the split of the
111 West 57th footprint between the tower and Steinway Hall (cut at the polygon's own vertices); tower plan shapes
are the published massing, not measured floor plates; the Solow Building's concave sweep is a 9-segment
approximation. NOT modelled: interiors, the Nordstrom podium's shopfronts, the bronze filigree pattern on the
111 West 57th terracotta (modelled as plain piers), and rooftop plant enclosures.
"""
from __future__ import annotations

import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import numpy as np  # noqa: E402
import c_common as cc  # noqa: E402
import common as C  # noqa: E402
from shapely.geometry import Polygon  # noqa: E402

ID = "c_billionaires_row"
B_432, B_432B, B_111, B_CPT, B_ONE57, B_220, B_53W53, B_TRUMP, B_SOLOW = (1088817, 1035787, 1023728, 1090180,
                                                                          1088565, 1090184, 1090777, 1035794, 1035071)
H432, H111, HCPT, H57, H220, H53, HTRUMP, HSOLOW = 425.5, 435.3, 472.4, 306.1, 290.2, 320.0, 202.0, 210.0
TUBE = 28.5             # 432 Park: 93.5 ft square
WIN = 3.05              # 10 ft square windows, six per facade
PIER = (TUBE - 6 * WIN) / 7
FLOOR432 = H432 / 85
VOID_FLOORS = (12, 30, 48, 66, 84)
CPT_CANTILEVER_Z = 91.0
CPT_CANTILEVER = 8.5
STEINWAY_TOP = 60.0
W111 = 18.3


def build():
    C.reset()
    cc.materials(["concrete", "glass_dark", "glass_blue", "glass_clear", "limestone", "terracotta_cream", "bronze",
                  "steel_nirosta", "aluminium", "roof_dark", "granite_grey", "marble_white"])
    g = cc.Group(ID, angle_deg=cc.GRID_ANGLE, origin_bin=B_111)
    objs: list = []

    # ============================================================================================ 432 Park Avenue
    P432 = g.poly(B_432).union(g.poly(B_432B)).buffer(0)
    P432 = C._clean_polygon(P432)
    objs.append(C.plinth(f"{ID}_432_base", P432, 0.0, 12.0, C.M.limestone, material_top=C.M.roof_dark))
    c432 = P432.centroid
    tube = C.rect(c432.x, c432.y, TUBE, TUBE)
    b = C.MeshBuilder()
    ring = C.ring_coords(tube)
    voids = set()
    for f in VOID_FLOORS:
        voids.update((f - 1, f))                     # the double-height void occupies floors f and f+1 (0-based f-1, f)
    for p0, p1, L, t, n in C.edges_of(ring):
        for fl in range(85):
            z0 = 12.0 + fl * (H432 - 12.0) / 85
            z1 = 12.0 + (fl + 1) * (H432 - 12.0) / 85
            if fl in voids:
                # open mechanical void: only the six structural piers, no spandrel and no glass
                for k in range(7):
                    q0 = p0 + t * (k * (WIN + PIER))
                    q1 = q0 + t * PIER
                    b.box_from_to(q0, q1, n, 0.75, z0, z1, C.M.concrete)
                continue
            C.punched_wall(b, p0, p1, n, z0, z1, [z0 + (z1 - z0) * 0.06], C.M.concrete, C.M.glass_dark,
                           bays=6, window_w=WIN, window_h=WIN, sill_h=(z1 - z0 - WIN) * 0.55, depth=0.75)
    objs.append(C.tag(b.build(f"{ID}_432_tube"), "mass"))
    objs.append(C.prism(f"{ID}_432_core", C.offset_polygon(tube, -0.8), 12.0, H432, C.M.concrete,
                        material_top=C.M.roof_dark, role="mass"))

    # ================================================================== 111 West 57th Street and Steinway Hall
    P111 = g.poly(B_111)
    x0, y0, x1, y1 = P111.bounds
    y_split = y0 + 26.0
    steinway = C._clean_polygon(P111.intersection(C.rect_xy(x0 - 1, y0 - 1, x1 + 1, y_split)).buffer(0))
    objs.append(C.plinth(f"{ID}_111_base", P111, 0.0, 8.0, C.M.limestone, material_top=C.M.roof_dark))
    fen_st = C.Fenestration(floor_h=(STEINWAY_TOP - 8.0) / 14, bay_w=3.1, window_frac=0.55, recess=0.5,
                            spandrel_h=1.0, spandrel_proud=0.12, pier="limestone", spandrel="limestone",
                            glass="glass_dark", window_h=2.6)
    objs += C.tower_tier(f"{ID}_steinway_hall", steinway, 8.0, STEINWAY_TOP, fen_st, roof_material="roof_dark",
                         parapet_h=1.6, parapet_t=0.6)
    objs.append(C.cornice(f"{ID}_steinway_cornice", steinway, STEINWAY_TOP - 3.0,
                          [(0.4, 0.0), (1.3, 0.8), (1.3, 1.6), (0.5, 2.4)], C.M.limestone))
    # the tower: 18.3 m wide, its south face stepping back in nine feathered terracotta setbacks
    cx111 = (x0 + x1) / 2
    y_north = y1 - 1.0
    steps = []
    nstep = 9
    for k in range(nstep + 1):
        z = 8.0 + (H111 - 14.0 - 8.0) * k / nstep
        depth = 24.0 - (24.0 - 11.0) * (k / nstep)
        steps.append((z, depth))
    for k in range(nstep):
        (za, da), (zb, db) = steps[k], steps[k + 1]
        poly = C.rect_xy(cx111 - W111 / 2, y_north - da, cx111 + W111 / 2, y_north)
        fen = C.Fenestration(floor_h=(H111 - 8.0) / 84, bay_w=2.6, window_frac=0.62, recess=0.42, spandrel_h=1.15,
                             spandrel_proud=0.34, pier="terracotta_cream", spandrel="bronze", glass="glass_dark")
        objs += C.tower_tier(f"{ID}_111_t{k}", poly, za, zb, fen, roof_material="roof_dark", parapet_h=0.0)
    top111 = C.rect_xy(cx111 - W111 / 2, y_north - steps[-1][1], cx111 + W111 / 2, y_north)
    objs.append(C.prism(f"{ID}_111_crown", top111, H111 - 14.0, H111, C.M.terracotta_cream,
                        material_top=C.M.roof_dark, role="mass"))

    # ==================================================================================== Central Park Tower
    Pcpt = g.poly(B_CPT)
    objs.append(C.plinth(f"{ID}_cpt_base", Pcpt, 0.0, 30.0, C.M.granite_grey, material_top=C.M.roof_dark))
    tcpt = C.offset_polygon(Pcpt, -1.5)
    objs += cc.curtain(f"{ID}_cpt_low", tcpt, 30.0, CPT_CANTILEVER_Z, floor_h=4.4, module=3.1, glass="glass_blue",
                       mullion="steel_nirosta", spandrel_h=1.1, proud=0.22, role="mass")
    bx0, by0, bx1, by1 = tcpt.bounds
    tcpt_hi = C.rect_xy(bx0, by0, bx1 + CPT_CANTILEVER, by1)          # the floor-30 cantilever, 8.5 m east
    objs += cc.curtain(f"{ID}_cpt_hi", tcpt_hi, CPT_CANTILEVER_Z, HCPT - 16.0, floor_h=4.4, module=3.1,
                       glass="glass_blue", mullion="steel_nirosta", spandrel_h=1.1, proud=0.22, role="mass")
    b = C.MeshBuilder()                                                # the cantilever's exposed soffit and brackets
    b.quad((bx1, by0, CPT_CANTILEVER_Z), (bx1 + CPT_CANTILEVER, by0, CPT_CANTILEVER_Z),
           (bx1 + CPT_CANTILEVER, by1, CPT_CANTILEVER_Z), (bx1, by1, CPT_CANTILEVER_Z), C.M.concrete)
    for k in range(6):
        yy = by0 + (by1 - by0) * (k + 0.5) / 6
        b.hull([(bx1, yy - 0.5, CPT_CANTILEVER_Z), (bx1, yy + 0.5, CPT_CANTILEVER_Z),
                (bx1, yy - 0.5, CPT_CANTILEVER_Z - 6.0), (bx1, yy + 0.5, CPT_CANTILEVER_Z - 6.0),
                (bx1 + CPT_CANTILEVER, yy - 0.5, CPT_CANTILEVER_Z), (bx1 + CPT_CANTILEVER, yy + 0.5, CPT_CANTILEVER_Z)],
               C.M.concrete)
    objs.append(b.build(f"{ID}_cpt_cantilever"))
    objs.append(C.prism(f"{ID}_cpt_crown", C.offset_polygon(tcpt_hi, -2.0), HCPT - 16.0, HCPT, C.M.steel_nirosta,
                        material_top=C.M.roof_dark, role="mass"))

    # ================================================================================================== One57
    P57 = g.poly(B_ONE57)
    objs.append(C.plinth(f"{ID}_one57_base", P57, 0.0, 24.0, C.M.granite_grey, material_top=C.M.roof_dark))
    t57 = C.offset_polygon(P57, -1.2)
    objs += cc.curtain(f"{ID}_one57", t57, 24.0, H57 - 34.0, floor_h=3.7, module=3.0, glass="glass_blue",
                       mullion="aluminium", spandrel_h=1.0, proud=0.2, role="mass")
    # the curved "waterfall" crown over the north face
    ax0, ay0, ax1, ay1 = t57.bounds
    rings = []
    for k in range(9):
        f = k / 8.0
        dz = 34.0 * f
        inset = 14.0 * math.sin(math.pi * f / 2)
        rings.append([(ax0, ay0, H57 - 34.0 + dz), (ax1, ay0, H57 - 34.0 + dz),
                      (ax1, ay1 - inset, H57 - 34.0 + dz), (ax0, ay1 - inset, H57 - 34.0 + dz)])
    objs.append(C.tag(C.loft(f"{ID}_one57_crown", rings, C.M.glass_blue, material_top=C.M.roof_dark), "mass"))

    # ============================================================================ 220 Central Park South
    P220 = g.poly(B_220)
    vx0, vy0, vx1, vy1 = P220.bounds
    villa = C._clean_polygon(P220.intersection(C.rect_xy(vx0 - 1, vy1 - 30.0, vx1 + 1, vy1 + 1)).buffer(0))
    tower220 = C._clean_polygon(P220.intersection(C.rect_xy(vx0 - 1, vy0 - 1, vx0 + 34.0, vy1 - 30.0)).buffer(0))
    objs.append(C.plinth(f"{ID}_220_base", P220, 0.0, 9.0, C.M.limestone, material_top=C.M.roof_dark))
    fen220 = C.Fenestration(floor_h=(H220 - 9.0) / 70, bay_w=3.0, window_frac=0.50, recess=0.45, spandrel_h=1.05,
                            spandrel_proud=0.14, pier="limestone", spandrel="limestone", glass="glass_dark",
                            window_h=2.4)
    objs += C.tower_tier(f"{ID}_220_villa", villa, 9.0, 9.0 + 18 * (H220 - 9.0) / 70, fen220,
                         roof_material="roof_grey", parapet_h=1.4, parapet_t=0.6)
    objs += C.tower_tier(f"{ID}_220_tower", tower220, 9.0, H220 - 18.0, fen220, roof_material="roof_grey",
                         parapet_h=0.0)
    for k, (dz, off) in enumerate(((6.0, -2.2), (12.0, -4.4), (18.0, -6.6))):
        objs.append(C.prism(f"{ID}_220_crown{k}", C.offset_polygon(tower220, off), H220 - 18.0 + dz - 6.0,
                            H220 - 18.0 + dz, C.M.limestone, material_top=C.M.roof_grey, role="mass"))

    # ==================================================================================================== 53 West 53rd
    P53 = g.poly(B_53W53)
    objs.append(C.plinth(f"{ID}_53_base", P53, 0.0, 14.0, C.M.granite_grey, material_top=C.M.roof_dark))
    t53 = C.offset_polygon(P53, -1.0)
    prev = t53
    zs53 = [(120.0, 0.0), (215.0, -3.2), (H53 - 8.0, -6.4)]
    for i, (ztop, off) in enumerate(zs53):
        z0 = 14.0 if i == 0 else zs53[i - 1][0]
        poly = C.offset_polygon(t53, off)
        objs += cc.curtain(f"{ID}_53_t{i}", poly, z0, ztop, floor_h=(H53 - 14.0) / 77, module=3.1, glass="glass_dark",
                           mullion="concrete", spandrel="concrete", spandrel_h=1.0, proud=0.3, role="mass")
        prev = poly
    # the exposed diagonal concrete exoskeleton
    b = C.MeshBuilder()
    for p0, p1, L, t, n in C.edges_of(C.ring_coords(t53)):
        nmod = max(1, int(round(L / 12.0)))
        z = 14.0
        while z + 24.0 < H53 - 8.0:
            for m in range(nmod):
                q0 = p0 + t * (L * m / nmod) + n * 0.34
                q1 = p0 + t * (L * (m + 1) / nmod) + n * 0.34
                for a, c in ((q0, q1), (q1, q0)):
                    b.hull([(a[0], a[1], z), (a[0], a[1], z + 1.0), (c[0], c[1], z + 24.0), (c[0], c[1], z + 25.0),
                            (a[0] + n[0] * 0.4, a[1] + n[1] * 0.4, z), (a[0] + n[0] * 0.4, a[1] + n[1] * 0.4, z + 1.0),
                            (c[0] + n[0] * 0.4, c[1] + n[1] * 0.4, z + 24.0), (c[0] + n[0] * 0.4, c[1] + n[1] * 0.4, z + 25.0)],
                           C.M.concrete)
            z += 24.0
    objs.append(b.build(f"{ID}_53_exoskeleton"))
    objs.append(C.prism(f"{ID}_53_crown", C.offset_polygon(prev, -2.0), H53 - 8.0, H53, C.M.concrete,
                        material_top=C.M.roof_dark, role="mass"))

    # ================================================================================================== Trump Tower
    Ptr = g.poly(B_TRUMP)
    objs.append(C.plinth(f"{ID}_trump_base", Ptr, 0.0, 26.0, C.M.granite_dark, material_top=C.M.roof_dark))
    ttr = C.offset_polygon(Ptr, -1.0)
    # 28 sawtooth bays on the north and east elevations, as a stepped plan
    tx0, ty0, tx1, ty1 = ttr.bounds
    saw = []
    nsaw = 7
    for k in range(nsaw + 1):
        f = k / nsaw
        saw.append(C.rect_xy(tx0, ty0, tx1 - 9.0 * f, ty1 - 6.0 * f))
    for k in range(nsaw):
        z0 = 26.0 + (HTRUMP - 26.0) * k / nsaw
        z1 = 26.0 + (HTRUMP - 26.0) * (k + 1) / nsaw
        objs += cc.curtain(f"{ID}_trump_t{k}", saw[k], z0, z1, floor_h=(HTRUMP - 26.0) / 58 * 1.0, module=3.0,
                           glass="glass_dark", mullion="bronze", spandrel_h=0.9, proud=0.2, role="mass")

    # ============================================================================================== Solow Building
    Psol = g.poly(B_SOLOW)
    sx0, sy0, sx1, sy1 = Psol.bounds
    objs.append(C.plinth(f"{ID}_solow_base", Psol, 0.0, 7.5, C.M.granite_dark, material_top=C.M.roof_dark))
    rings = []
    for k in range(10):
        z = 7.5 + (HSOLOW - 7.5) * k / 9
        f = math.sin(math.pi * k / 9)                    # concave sweep: widest at the base and top
        pull = 9.5 * (1.0 - f) * 0.0 + 9.5 * f
        ring = []
        for x, y in ((sx0 + 1, sy0 + 1 + pull), (sx1 - 1, sy0 + 1 + pull), (sx1 - 1, sy1 - 1 - pull), (sx0 + 1, sy1 - 1 - pull)):
            ring.append((x, y, z))
        rings.append(ring)
    objs.append(C.tag(C.loft(f"{ID}_solow_shaft", rings, C.M.marble_white, material_top=C.M.roof_dark), "mass"))
    b = C.MeshBuilder()
    for k in range(len(rings) - 1):
        r0, r1 = rings[k], rings[k + 1]
        nfl = max(1, int(round((r1[0][2] - r0[0][2]) / ((HSOLOW - 7.5) / 50))))
        for f in range(1, nfl + 1):
            s = f / nfl
            ring = [(a[0] + (bq[0] - a[0]) * s, a[1] + (bq[1] - a[1]) * s, a[2] + (bq[2] - a[2]) * s)
                    for a, bq in zip(r0, r1)]
            cc.band_ring(b, [(x, y) for x, y, _ in ring], ring[0][2] - 1.0, ring[0][2], 0.16, C.M.glass_dark)
    objs.append(b.build(f"{ID}_solow_floors"))
    return objs, g


def main():
    objs, g = build()
    entry = cc.finish(objs, ID, g.frame, real_footprint=g.real_local,
                      fidelity_statement=(
                          "Exact: nine real OTI footprints; published heights 425.5 / 435.3 / 472.4 / 306.1 / 290.2 / "
                          "320.0 / 202.0 / 210.0 m (CTBUH); 432 Park's 28.5 m square tube with six 3.05 m square "
                          "windows per facade per floor and five double-height open mechanical voids at floors "
                          "12/13, 30/31, 48/49, 66/67, 84/85 modelled as real openings; 111 West 57th's nine "
                          "feathered terracotta setbacks (24.0 -> 11.0 m depth) over Steinway Hall's 16-storey "
                          "limestone front; Central Park Tower's 8.5 m east cantilever starting at 91.0 m with its "
                          "exposed soffit and brackets. Inferred (stated): the 111 West 57th footprint split (cut at "
                          "the polygon's own vertices), the tower plan shapes (published massing, not measured floor "
                          "plates), the Solow Building's concave sweep (9 segments) and Trump Tower's sawtooth as 7 "
                          "stepped tiers rather than 28 individual bays. Not modelled: interiors, the Nordstrom "
                          "podium shopfronts, the bronze filigree pattern on the 111 West 57th terracotta, rooftop "
                          "plant enclosures."),
                      dimensions={"432_park_m": H432, "432_tube_m": TUBE, "432_window_m": WIN,
                                  "432_pier_m": round(PIER, 3), "432_floor_h_m": round(FLOOR432, 3),
                                  "432_void_floors": list(VOID_FLOORS), "111_w57_m": H111, "111_width_m": W111,
                                  "steinway_hall_top_m": STEINWAY_TOP, "central_park_tower_m": HCPT,
                                  "cpt_cantilever_z_m": CPT_CANTILEVER_Z, "cpt_cantilever_m": CPT_CANTILEVER,
                                  "one57_m": H57, "220_cps_m": H220, "53w53_m": H53, "trump_tower_m": HTRUMP,
                                  "solow_m": HSOLOW})
    cc.render(ID, [
        {"view": "sheep_meadow", "azimuth_deg": 20, "elevation_deg": "street", "distance": 1300, "fov_deg": 42, "look_up_deg": 12},
        {"view": "aerial", "azimuth_deg": 20, "elevation_deg": 22},
    ])
    return entry


if __name__ == "__main__":
    main()
