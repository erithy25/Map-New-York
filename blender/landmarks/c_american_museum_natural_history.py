"""American Museum of Natural History and the Rose Center for Earth and Space — Central Park West at 79th Street
(BINs 1083846 main museum, 1090575 north range and Rose Center; LP-0946 for the Theodore Roosevelt Memorial).
Calvert Vaux & J. Wrey Mould 1877; Cady, Berg & See 1892 (77th Street); Trowbridge & Livingston 1936 (Roosevelt
Memorial); Polshek Partnership 2000 (Rose Center).

Dimensions used (source in brackets)
------------------------------------
* Footprints: the two real OTI polygons (32,268 m2). Central Park West is east (local +x); West 77th Street is south
  and West 81st Street north.
* Theodore Roosevelt Memorial [LPC designation report LP-0946]: a triumphal arch on Central Park West carried by
  **four Ionic columns 60 ft = 18.3 m tall**, flanked by two statue pylons, with a barrel-vaulted portico behind and
  a bronze equestrian statue of Roosevelt (1940, James Earle Fraser) on a granite plinth before it. The memorial's
  attic reaches 44.8 m, the highest point of the museum (OTI LiDAR).
* Rose Center for Earth and Space [Polshek Partnership 2000; AMNH]: a **glass cube 95 ft = 29.0 m on each side**
  (a suspended white-steel space frame with 736 panes of water-white glass) containing the **Hayden Sphere,
  87 ft = 26.5 m in diameter**, carried clear of the floor on three steel trusses; the sphere's equator is at
  16.0 m. The cube stands at the north-east corner of the north range.
* 77th Street range [Cady, Berg & See 1892]: pink Vermont granite, Richardsonian Romanesque, a 5-storey range with
  round-arched openings and corner turrets, cornice at 30.0 m.
* Materials [LP-0946]: Milford pink granite (1892 range), Indiana limestone (1936 memorial), white-painted steel and
  low-iron glass (Rose Center).

Fidelity: two real footprints; the 18.3 m Ionic columns and the memorial arch, the 29.0 m glass cube with its
26.5 m sphere on three supports, the 1892 granite range with its arched openings and turrets are modelled as
geometry. Inferred (stated): the position of the Rose Center cube inside the north-range polygon (its north-east
corner) and the storey heights of the 1892 range. NOT modelled: the interiors and the halls, the equestrian statue's
figures (a blocked-out mass on its plinth), the sculptural frieze and inscriptions of the memorial, and the
2023 Gilder Center on Columbus Avenue (built after the footprint capture).
"""
from __future__ import annotations

import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import c_common as cc  # noqa: E402
import common as C  # noqa: E402

ID = "c_american_museum_natural_history"
B_MAIN, B_NORTH = 1083846, 1090575
MEMORIAL_TOP = 44.8
COLUMN_H = 18.3
CUBE = 29.0
SPHERE_D = 26.5
SPHERE_Z = 16.0
RANGE_CORNICE = 30.0
BASE_TOP = 7.0


def build():
    C.reset()
    cc.materials(["granite_pink", "limestone", "glass_clear", "glass_dark", "steel_nirosta", "roof_grey",
                  "roof_dark", "bronze", "granite_grey", "aluminium"])
    g = cc.Group(ID, angle_deg=cc.GRID_ANGLE, origin_bin=B_MAIN)
    Pm = g.poly(B_MAIN)
    Pn = g.poly(B_NORTH)
    objs: list = []

    objs += cc.base_and_wall(f"{ID}_main_base", Pm, BASE_TOP, C.M.granite_pink, recess=0.75, material_top=C.M.roof_grey)
    objs += cc.base_and_wall(f"{ID}_north_base", Pn, BASE_TOP, C.M.granite_pink, recess=0.75, material_top=C.M.roof_grey)
    fen = C.Fenestration(bay_w=4.2, window_frac=0.55, recess=0.55, spandrel_h=1.0, spandrel_proud=0.14,
                         pier="granite_pink", spandrel="granite_pink", glass="glass_dark",
                         floor_z=[BASE_TOP + (RANGE_CORNICE - 2.0 - BASE_TOP) * k / 4 for k in range(5)],
                         window_h=3.4)
    objs += C.tower_tier(f"{ID}_main", Pm, BASE_TOP, RANGE_CORNICE - 2.0, fen, roof_material="roof_grey",
                         parapet_h=1.2, parapet_t=0.6)
    nx0, ny0, nx1, ny1 = Pn.bounds
    ccx, ccy = nx1 - CUBE / 2 - 1.0, ny1 - CUBE / 2 - 1.0
    cube = C.rect(ccx, ccy, CUBE, CUBE)
    Pn_body = C._clean_polygon(Pn.difference(cube.buffer(0.6)).buffer(0))     # the cube is a void in the block
    objs += C.tower_tier(f"{ID}_north", Pn_body, BASE_TOP, RANGE_CORNICE - 6.0, fen, roof_material="roof_grey",
                         parapet_h=1.2, parapet_t=0.6)
    b = C.MeshBuilder()
    for P in (Pm, Pn):                                     # Richardsonian round-arched ground floor
        for p0, p1, L, t, n in C.edges_of(C.ring_coords(P)):
            if L < 12.0:
                continue
            nbay = max(2, int(round(L / 6.0)))
            mod = L / nbay
            for k in range(nbay):
                a = p0 + t * (k * mod + 1.3)
                c = p0 + t * ((k + 1) * mod - 1.3)
                C.arched_opening(b, a, c, n, 1.7, 4.6, None, 0.6, C.M.granite_pink, C.M.glass_dark)
    objs.append(b.build(f"{ID}_arcade"))
    # corner turrets on the 1892 range
    b = C.MeshBuilder()
    mx0, my0, mx1, my1 = Pm.bounds
    mring = C.ring_coords(Pm)
    corners = sorted(mring, key=lambda q: (q[0] - mx0) ** 2 + min((q[1] - my0) ** 2, (q[1] - my1) ** 2))[:2]
    for cxy in [(q[0] + 5.0, q[1] + (5.0 if q[1] < (my0 + my1) / 2 else -5.0)) for q in corners]:
        b.lathe([(4.4, 0.0), (4.4, RANGE_CORNICE - BASE_TOP), (5.0, RANGE_CORNICE - BASE_TOP + 0.6),
                 (5.0, RANGE_CORNICE - BASE_TOP + 1.4), (0.0, RANGE_CORNICE - BASE_TOP + 9.0)], 16,
                C.M.granite_pink, origin=(cxy[0], cxy[1], BASE_TOP), smooth=False)
    objs.append(C.tag(b.build(f"{ID}_turrets"), "mass"))

    # ---- the Theodore Roosevelt Memorial on Central Park West ------------------------------------------------------
    coords = C.ring_coords(Pm)
    p0, p1, L, t, n = C.edge_facing(coords, 0.0)            # the east (Central Park West) elevation
    mid = (p0 + p1) / 2
    b = C.MeshBuilder()
    portico = C.rect_xy(mid[0] - 4.0, mid[1] - 24.0, mid[0] + 14.0, mid[1] + 24.0)
    b.prism(C.ring_coords(portico), BASE_TOP, MEMORIAL_TOP - 6.0, C.M.limestone, material_top=C.M.roof_grey)
    for k in range(4):                                      # the four 60 ft Ionic columns
        u = -12.0 + 8.0 * k
        q = mid + t * u + n * 8.5
        C.column(b, q[0], q[1], BASE_TOP - 3.0, COLUMN_H, 0.95, C.M.limestone, order="ionic", segments=18)
    z_ent = BASE_TOP - 3.0 + COLUMN_H
    b.box_from_to(mid - t * 17.0, mid + t * 17.0, n, 10.5, z_ent, z_ent + 3.6, C.M.limestone)      # entablature
    b.box_from_to(mid - t * 17.0, mid + t * 17.0, n, 9.0, z_ent + 3.6, MEMORIAL_TOP - 0.6, C.M.limestone)  # attic
    b.box_from_to(mid - t * 18.0, mid + t * 18.0, n, 9.8, MEMORIAL_TOP - 0.6, MEMORIAL_TOP, C.M.limestone)
    for du in (-21.0, 21.0):                                # the two flanking statue pylons
        q = mid + t * du + n * 6.0
        b.box((q[0], q[1], BASE_TOP + 9.0), (7.0, 7.0, 22.0), C.M.limestone)
    # the barrel-vaulted arch behind the columns
    C.arched_opening(b, mid - t * 6.0, mid + t * 6.0, n + n * 0.0, BASE_TOP - 3.0, 12.0, 6.0, 4.4, C.M.limestone,
                     C.M.glass_dark)
    # the equestrian statue on its granite plinth (blocked-out mass)
    q = mid + n * 16.0
    b.box((q[0], q[1], 1.9), (5.0, 2.6, 3.8), C.M.granite_grey)
    b.box((q[0], q[1], 3.8 + 1.7), (3.6, 1.3, 3.4), C.M.bronze)
    for k in range(24):                                     # the memorial steps
        z = 3.0 * (k + 1) / 24
        d = 0.45 * (24 - k)
        b.box_from_to(mid - t * 20.0, mid + t * 20.0, n, 19.0 + d, 0.0, z, C.M.granite_grey)
    objs.append(b.build(f"{ID}_roosevelt_memorial"))

    # ---- the Rose Center: the glass cube and the Hayden Sphere -----------------------------------------------------
    b = C.MeshBuilder()
    ring = C.ring_coords(cube)
    b.prism(ring, 0.4, CUBE, C.M.glass_clear, cap_top=True, cap_bottom=False, material_top=C.M.glass_clear)
    for p0, p1, L, t, n in C.edges_of(ring):                # the white space-frame grid, 736 panes
        nmul = 8
        for k in range(nmul + 1):
            q = p0 + t * (L * k / nmul)
            b.box((q[0], q[1], CUBE / 2 + 0.2), (0.22, 0.22, CUBE - 0.4), C.M.steel_nirosta, top=False, bottom=False,
                  rot_deg=math.degrees(math.atan2(t[1], t[0])))
        for j in range(1, nmul):
            z = CUBE * j / nmul
            b.box_from_to(p0, p1, n, 0.18, z - 0.11, z + 0.11, C.M.steel_nirosta)
    sphere_prof = [(SPHERE_D / 2 * math.sin(math.pi * k / 16), SPHERE_D / 2 * (1 - math.cos(math.pi * k / 16)))
                   for k in range(17)]
    b.lathe(sphere_prof, 32, C.M.aluminium, origin=(ccx, ccy, SPHERE_Z - SPHERE_D / 2), smooth=True)
    for k in range(3):                                      # the three steel trusses carrying the sphere
        a = 2 * math.pi * k / 3 + 0.5
        q = (ccx + (SPHERE_D / 2 + 1.0) * math.cos(a), ccy + (SPHERE_D / 2 + 1.0) * math.sin(a))
        b.hull([(q[0] - 0.3, q[1] - 0.3, 0.4), (q[0] + 0.3, q[1] + 0.3, 0.4),
                (ccx + SPHERE_D / 2 * 0.75 * math.cos(a) - 0.3, ccy + SPHERE_D / 2 * 0.75 * math.sin(a) - 0.3, SPHERE_Z),
                (ccx + SPHERE_D / 2 * 0.75 * math.cos(a) + 0.3, ccy + SPHERE_D / 2 * 0.75 * math.sin(a) + 0.3, SPHERE_Z),
                (q[0] - 0.3, q[1] + 0.3, 0.4), (q[0] + 0.3, q[1] - 0.3, 0.4)], C.M.steel_nirosta)
    objs.append(C.tag(b.build(f"{ID}_rose_center"), "mass"))
    return objs, g


def main():
    objs, g = build()
    entry = cc.finish(objs, ID, g.frame, real_footprint=g.real_local,
                      fidelity_statement=(
                          "Exact: two real OTI footprints; the Roosevelt Memorial's four 60 ft = 18.3 m Ionic "
                          "columns, arch, flanking pylons and 44.8 m attic (LP-0946, OTI LiDAR); the Rose Center's "
                          "95 ft = 29.0 m glass cube with its white space frame and the 87 ft = 26.5 m Hayden "
                          "Sphere carried on three trusses with its equator at 16.0 m; the 1892 pink-granite range "
                          "with round-arched openings, a 30.0 m cornice and corner turrets. Inferred (stated): the "
                          "cube's position within the north-range polygon and the 1892 range's storey heights. Not "
                          "modelled: interiors and halls, the equestrian statue's figures (blocked-out mass), the "
                          "memorial's carved frieze and inscriptions, and the 2023 Gilder Center (post-dates the "
                          "footprint capture)."),
                      dimensions={"memorial_top_m": MEMORIAL_TOP, "ionic_column_m": COLUMN_H, "rose_cube_m": CUBE,
                                  "hayden_sphere_m": SPHERE_D, "sphere_centre_z_m": SPHERE_Z,
                                  "range_cornice_m": RANGE_CORNICE})
    cc.render(ID, [
        {"view": "central_park_west", "azimuth_deg": 90, "elevation_deg": "street", "fov_deg": 55, "look_up_deg": 12},
        {"view": "aerial", "azimuth_deg": 60, "elevation_deg": 28},
    ])
    return entry


if __name__ == "__main__":
    main()
