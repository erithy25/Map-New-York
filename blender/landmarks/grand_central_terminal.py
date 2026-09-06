"""Grand Central Terminal — 89 East 42nd Street (BIN 1035381, LP-00266). Reed & Stem with Warren & Wetmore, 1913.
Exterior **and** the Main Concourse interior.

Dimensions used (source in brackets)
------------------------------------
* Footprint: real OTI polygon of the head house, 7,828.6 m2, 91.3 x 86.9 m in the model's local frame; the 42nd Street
  front faces south.
* Exterior [LPC LP-0266, Wikipedia "Grand Central Terminal", MTA]: the 42nd Street facade is a triumphal-arch
  composition — three round-arched windows about 18 m (60 ft) high springing from a colonnade of paired Corinthian
  columns, a cornice, and above it Jules-Felix Coutan's 1914 sculptural group *Glory of Commerce* (Mercury, Hercules,
  Minerva), 48 ft (14.6 m) wide and 15 m high, around the Tiffany clock, which is 13 ft (4.0 m) in diameter — the
  largest example of Tiffany glass in the world. The LiDAR roof height for the BIN is 45.84 m, which is the height used
  here for the top of the sculptural group; no single architectural height is published for the terminal.
* Main Concourse [MTA, Wikipedia "Grand Central Terminal", LPC interior designation LP-1099]: 275 x 120 ft
  (84 x 37 m) in plan and 125 ft (38 m) from floor to the crown of the barrel vault; the vault carries Paul Helleu's
  celestial ceiling — a cerulean sky with 2,500 stars, 59 of them illuminated, painted (and famously reversed) in
  gold. The information booth at the centre carries the four-faced brass clock, about 4 ft (1.2 m) per face, valued in
  the tens of millions. Ticket windows line the west side; the west and east marble staircases (added 1998 on the east)
  are modelled at their real 12 m width. The concourse floor is Tennessee pink marble.
* Modelling decision (stated, not hidden): the concourse floor is placed at +2.0 m above the footprint's ground datum
  and the vault crown therefore at 40.0 m. The real floor sits a few metres *below* 42nd Street; putting it there would
  make the terminal's street-level volume a void, which would no longer match the real building footprint. The 38 m
  floor-to-crown dimension, the 84 x 37 m plan and the 45.8 m exterior height are all exact.
* Materials [LPC LP-0266 / LP-1099]: Stony Creek granite base, Bedford limestone above, Tennessee pink marble and
  Botticino marble inside, brass fittings, the cerulean-and-gold celestial ceiling (material slot ``GCT_CEILING``,
  emissive so the vault reads lit).

Fidelity: exact — real footprint, 45.8 m to the top of the sculptural group, the three 18 m arched windows of the
42nd Street front with their paired-column order and the clock at 4.0 m diameter, and inside: an 84 x 37 m concourse
under a 38 m barrel vault with the emissive celestial ceiling, the four-faced brass clock on the information booth,
a ticket-window range and the two 12 m marble staircases. Inferred — the storey heights of the flanking office wings
and the exact position of the ticket range along the west wall. Simplified — *Glory of Commerce* is a massing group,
not sculpted figures; the ceiling's 2,500 stars are a texture-free emissive surface (the engine can drive it from the
``GCT_CEILING`` slot); the Corinthian capitals use the shared lathe profile. Not modelled — the lower (suburban) level,
the ramps, Vanderbilt Hall, the Oyster Bar and the Whispering Gallery.
"""
from __future__ import annotations

import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import common as C  # noqa: E402

ID = "grand_central_terminal"
BINS = [1035381]
ROOF_M = 45.8              # top of the Coutan sculptural group (LiDAR height_roof 45.84 m)
CORNICE_M = 32.0
FLOOR_M = 2.0              # Main Concourse floor (see the modelling decision in the docstring)
CONC_L, CONC_W, CONC_H = 84.0, 37.0, 38.0
SPRING_H = 18.3            # springing of the vault above the concourse floor (60 ft)
ARCH_H = 18.0              # the three great 42nd Street windows
CLOCK_D = 4.0


def build():
    C.reset()
    fp = C.load_footprint(ID)
    fr = C.local_frame(fp.polygon, fp.ground_z)
    P = fr.local_polygon(fp.polygon)
    minx, miny, maxx, maxy = P.bounds
    cx, cy = P.centroid.x, P.centroid.y
    south = fr.local_cardinal(180.0)
    objs = []
    lime, gran, marble, brass = C.M.limestone_warm, C.M.granite_grey, C.M.marble_tennessee, C.M.brass
    glass, ceil = C.M.glass_dark, C.M.GCT_CEILING

    # ---- street-level volume on the real footprint (the IoU volume; the concourse floor is its top) -------------
    objs.append(C.plinth(f"{ID}_ground", P, 0.0, FLOOR_M, gran, material_top=marble))

    # ---- the concourse void, cut out of the block above the ground level ---------------------------------------
    conc = C.rect(cx, cy, CONC_L, CONC_W)
    shell = P.difference(conc)
    if shell.geom_type != "Polygon":
        shell = max(shell.geoms, key=lambda g: g.area)
    objs.append(C.prism(f"{ID}_block", shell, FLOOR_M, CORNICE_M, lime, material_top=C.M.roof_grey, role="mass"))

    # ---- exterior: rusticated granite base, colonnade order and the three great arched windows ------------------
    b = C.MeshBuilder()
    coords = C.ring_coords(P)
    b.prism(coords, FLOOR_M, 9.0, gran, cap_top=False, cap_bottom=False)
    for q, t, n, s in C.ring_stations(coords, 6.5):                # ground-floor openings all round
        C.arched_opening(b, q - t * 1.8, q + t * 1.8, n, 1.0, 5.4, None, 0.9, gran, glass, n=10)
    # the office-wing fenestration above the base
    fen = C.Fenestration(floor_h=4.2, bay_w=3.3, window_frac=0.5, recess=0.45, spandrel_h=1.0,
                         pier="limestone_warm", spandrel="limestone_warm", glass="glass_dark", window_h=2.8)
    objs.append(C.facade_grid(f"{ID}_skin", P, 9.0, CORNICE_M, fen))
    objs.append(C.cornice(f"{ID}_cornice", P, CORNICE_M, [(0.4, 0.0), (1.6, 1.0), (1.9, 1.7), (1.5, 2.6), (0.5, 3.0)], lime))

    runs = sorted(C.wall_runs(coords, south, tol_deg=50.0), key=lambda r: -r[1])
    pts, Lf = runs[0]
    b2 = C.MeshBuilder()
    for k in range(3):                                             # three arched windows, 18 m high
        cs = Lf * (k + 0.5) / 3
        a, t, n = C.polyline_at(pts, cs - 8.5)
        c, t2, n2 = C.polyline_at(pts, cs + 8.5)
        C.arched_opening(b2, a, c, n, 9.5, 9.5 + ARCH_H - 8.5, None, 2.6, lime, glass, n=16)
        for f in (-8.5, 8.5):                                      # paired Corinthian columns between the bays
            q, qt, qn = C.polyline_at(pts, cs + f)
            for dd in (-1.6, 1.6):
                C.column(b2, float(q[0] + qt[0] * dd + qn[0] * 1.3), float(q[1] + qt[1] * dd + qn[1] * 1.3),
                         9.0, 15.5, 0.95, lime, order="corinthian", segments=14)
    # the Coutan sculptural group and the Tiffany clock over the central bay
    mid, mt, mn = C.polyline_at(pts, Lf / 2)
    b2.box_from_to(mid - mt * 9.0, mid + mt * 9.0, mn, 2.4, CORNICE_M + 3.0, CORNICE_M + 4.2, lime)   # the plinth
    zc = CORNICE_M + 4.2
    C.clock_face(b2, float(mid[0] + mn[0] * 2.2), float(mid[1] + mn[1] * 2.2), zc + 4.0, mn, CLOCK_D / 2,
                 C.M.emissive_warm, brass, bezel_material=lime)
    for dx, w, h in ((-5.4, 3.2, ROOF_M - zc), (0.0, 3.6, ROOF_M - zc - 1.5), (5.4, 3.2, ROOF_M - zc - 2.5)):
        q = mid + mt * dx
        b2.hull([(float(q[0] - mt[0] * w / 2 + mn[0] * 0.6), float(q[1] - mt[1] * w / 2 + mn[1] * 0.6), zc),
                 (float(q[0] + mt[0] * w / 2 + mn[0] * 0.6), float(q[1] + mt[1] * w / 2 + mn[1] * 0.6), zc),
                 (float(q[0] - mt[0] * w / 2 + mn[0] * 2.6), float(q[1] - mt[1] * w / 2 + mn[1] * 2.6), zc),
                 (float(q[0] + mt[0] * w / 2 + mn[0] * 2.6), float(q[1] + mt[1] * w / 2 + mn[1] * 2.6), zc),
                 (float(q[0] - mt[0] * w * 0.28 + mn[0] * 1.6), float(q[1] - mt[1] * w * 0.28 + mn[1] * 1.6), zc + h),
                 (float(q[0] + mt[0] * w * 0.28 + mn[0] * 1.6), float(q[1] + mt[1] * w * 0.28 + mn[1] * 1.6), zc + h)],
                lime)
    objs.append(b.build(f"{ID}_base_detail"))
    objs.append(b2.build(f"{ID}_south_front"))

    # ---- the Main Concourse interior ---------------------------------------------------------------------------
    b = C.MeshBuilder()
    cring = C.ring_coords(conc)
    b.prism(cring, FLOOR_M - 0.25, FLOOR_M, marble, cap_bottom=False)                          # the marble floor
    wall_top = FLOOR_M + SPRING_H
    for p0, p1, L, t, n in C.edges_of(cring):
        b.box_from_to(p0, p1, -n, 0.6, FLOOR_M, wall_top, marble, top=False, bottom=False)     # concourse walls
    # the barrel vault with the emissive celestial ceiling, running along the concourse's long axis
    barrel_rise = FLOOR_M + CONC_H - wall_top
    C.barrel_vault(b, (cx - CONC_L / 2, cy), (cx + CONC_L / 2, cy), CONC_W, wall_top, barrel_rise, ceil,
                   segments=28, thickness=0.5, lunette_material=marble, closed_ends=True)
    # the great lunette windows at both ends and the half-round windows over the east and west balconies
    for sx in (-1, 1):
        x = cx + sx * (CONC_L / 2 - 0.4)
        for i in range(3):
            w = CONC_W / 3.4
            y0 = cy + (i - 1) * (CONC_W / 3.2) - w / 2 + w * 0.12
            y1 = y0 + w * 0.76
            b.quad((x, y0, wall_top - 12.0), (x, y1, wall_top - 12.0), (x, y1, wall_top + 8.0), (x, y0, wall_top + 8.0),
                   C.M.glass_clear)
    # ticket windows along the west wall, with brass grilles and warm lit counters
    for i in range(9):
        y = cy - CONC_W / 2 + 3.0 + i * ((CONC_W - 6.0) / 8)
        x = cx - CONC_L / 2 + 0.65
        b.box((x, y, FLOOR_M + 2.3), (0.35, 1.9, 3.4), brass)
        b.box((x + 0.28, y, FLOOR_M + 2.3), (0.12, 1.55, 2.9), C.M.emissive_warm)
        b.box((x + 0.5, y, FLOOR_M + 1.05), (0.7, 2.1, 0.12), marble)
    # the information booth and its four-faced brass clock
    b.lathe([(4.2, 0.0), (4.2, 3.2), (3.6, 3.6)], 16, marble, origin=(cx, cy, FLOOR_M), smooth=True)
    b.lathe([(0.55, 0.0), (0.5, 2.6), (0.9, 2.9)], 12, brass, origin=(cx, cy, FLOOR_M + 3.6), smooth=True)
    for k in range(4):
        a = math.pi / 2 * k
        nn = (math.cos(a), math.sin(a))
        C.clock_face(b, cx + nn[0] * 0.95, cy + nn[1] * 0.95, FLOOR_M + 5.4, nn, 0.6, C.M.emissive_warm, brass,
                     bezel_material=brass, depth=0.08)
    b.lathe([(0.9, 0.0), (0.55, 0.9), (0.0, 1.5)], 12, brass, origin=(cx, cy, FLOOR_M + 6.5), smooth=True)
    # west and east marble staircases, 12 m wide
    for sx in (-1, 1):
        x = cx + sx * (CONC_L / 2 - 1.0)
        p0 = (x, cy - 6.0); p1 = (x, cy + 6.0)
        C.steps(b, p0, p1, (-sx, 0.0), FLOOR_M + 7.2, 24, 0.30, 0.34, marble, z_bottom=FLOOR_M)
        for dy in (-6.4, 6.4):                                                         # balustrades
            b.box((x - sx * 4.2, cy + dy, FLOOR_M + 4.6), (8.6, 0.5, 1.0), marble, rot_deg=0.0)
    objs.append(b.build(f"{ID}_concourse"))
    concourse_cam = {"eye": fr.to_export(cx + CONC_L / 2 - 6.0, cy + CONC_W / 2 - 5.0, FLOOR_M + 8.0),
                     "target": fr.to_export(cx - CONC_L / 4, cy, FLOOR_M + 17.0)}
    return objs, fr, fp, concourse_cam


def main():
    objs, fr, fp, cam = build()
    C.finish(objs, ID, BINS, fr, height_m=ROOF_M, name="Grand Central Terminal", lp_number="LP-00266",
             height_source="LiDAR height_roof for BIN 1035381 = 45.84 m (top of the Coutan sculptural group); no single architectural height is published. Main Concourse 275 x 120 ft x 125 ft (84 x 37 x 38 m) [MTA / LPC LP-1099]",
             fidelity_statement=(
                 "Exact: real footprint, 45.8 m to the top of the sculptural group, the three 18 m round-arched windows of "
                 "the 42nd Street front with paired Corinthian columns and the 4.0 m Tiffany clock, and the Main Concourse "
                 "interior at its published 84 x 37 x 38 m with an emissive celestial barrel vault (slot GCT_CEILING), the "
                 "four-faced brass clock on the information booth, a ticket-window range and two 12 m marble staircases. "
                 "Stated modelling decision: the concourse floor is at +2.0 m above the footprint ground datum (the real "
                 "floor is a few metres below 42nd Street) so that the street-level volume still matches the real "
                 "footprint; the 38 m floor-to-crown dimension is exact. Inferred: office-wing storey heights and the "
                 "exact position of the ticket range. Simplified: Glory of Commerce is a massing group, not sculpted "
                 "figures; the ceiling's 2,500 stars are an emissive surface for the engine to drive. Not modelled: the "
                 "lower suburban level, the ramps, Vanderbilt Hall, the Oyster Bar and the Whispering Gallery."),
             notes="Material slot GCT_CEILING (emissive) on the concourse vault",
             dimensions={"roof_m": ROOF_M, "cornice_m": CORNICE_M, "concourse_m": [CONC_L, CONC_W, CONC_H],
                         "concourse_floor_z_m": FLOOR_M, "vault_springing_above_floor_m": SPRING_H,
                         "arched_window_h_m": ARCH_H, "clock_d_m": CLOCK_D, "staircase_w_m": 12.0,
                         "ticket_windows": 9},
             tri_budget=C.TRI_BUDGET_LOD0_LARGE,
             material_slots={"GCT_CEILING": "emissive celestial ceiling of the Main Concourse barrel vault"})
    C.render_check(ID, [
        {"view": "street", "azimuth_deg": 180, "elevation_deg": "street", "distance": 125, "target_z": 30, "fov_deg": 64},
        {"view": "aerial", "azimuth_deg": 200, "elevation_deg": 26, "distance": 300, "fov_deg": 46, "target_z": 25},
        {"view": "concourse", "fov_deg": 72, "no_ground": True, **cam},
    ])


if __name__ == "__main__":
    main()
