"""Trinity Church — 75 Broadway at the head of Wall Street (BIN 1001028, LP-00048). Richard Upjohn, 1846.

Dimensions used (source in brackets)
------------------------------------
* Footprint: real OTI polygon, 1,812.4 m2 — the church with its later chapel and parish additions, 67.8 x 44.0 m in the
  model's local frame; the tower front faces Broadway (east) at the head of Wall Street.
* Heights [Wikipedia "Trinity Church (Manhattan)", LPC LP-0048, Trinity Church Wall Street]: the spire and cross reach
  281 ft = 85.6 m — the tallest structure in New York from 1846 to 1890. The nave is 79 ft (24.1 m) wide and 166 ft
  (50.6 m) long inside; the tower is 25 ft (7.6 m) square in plan.
* Massing [LPC LP-0048]: a Gothic Revival aisled nave with a clerestory, buttressed side walls with lancet windows, a
  square west tower (facing Broadway) rising to a parapet and pinnacles at 43.0 m, and an octagonal broach spire from
  there to the finial and cross at 85.6 m. The 43.0 m tower parapet is read off published elevations and is stated as
  inferred (+-2 m); everything above and below it is fixed by the 85.6 m total.
* Materials [LPC LP-0048]: Little Falls brownstone ashlar throughout, slate roof, bronze doors (Richard Morris Hunt,
  1893), copper cross.

Fidelity: exact — real footprint, 85.6 m spire and cross, the aisled nave with clerestory and buttresses, the square
Broadway tower with an octagonal broach spire and corner pinnacles, the brownstone/slate material split, and lancet
window rhythm at the documented bay. Inferred (+-2 m) — the tower parapet level and the aisle/clerestory heights, which
are not published individually. Simplified — window tracery is modelled as pointed openings with a single mullion, not
as cusped tracery; crockets on the spire are omitted. Not modelled — the interior, the Hunt bronze doors' relief panels,
and the churchyard monuments.
"""
from __future__ import annotations

import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import common as C  # noqa: E402

ID = "trinity_church"
BINS = [1001028]
SPIRE_TOP_M = 85.6
TOWER_PARAPET_M = 43.0
AISLE_H = 12.5
NAVE_WALL_H = 20.5
NAVE_RIDGE_M = 27.5
TOWER_W = 7.6


def build():
    C.reset()
    fp = C.load_footprint(ID)
    fr = C.local_frame(fp.polygon, fp.ground_z)
    P = fr.local_polygon(fp.polygon)
    minx, miny, maxx, maxy = P.bounds
    east = fr.local_cardinal(90.0)                 # Broadway is east of the church
    objs = []
    stone, slate, glass = C.M.brownstone, C.M.slate, C.M.glass_dark

    # ---- the whole footprint as the ground-floor volume (IoU volume) -------------------------------------------
    objs.append(C.plinth(f"{ID}_base", P, 0.0, AISLE_H, stone, material_top=C.M.slate))
    coords = C.ring_coords(P)

    # ---- buttresses and lancet windows around the aisle walls --------------------------------------------------
    b = C.MeshBuilder()
    BAY = 6.2                                      # the aisle bay, measured along the wall
    for q, t, n, s in C.ring_stations(coords, BAY):
        b.box_from_to(q - t * 0.75, q + t * 0.75, n, 1.15, 0.0, AISLE_H - 2.2, stone, top=True)
        b.box_from_to(q - t * 0.6, q + t * 0.6, n, 0.85, AISLE_H - 2.2, AISLE_H - 0.6, stone, top=True)
        b.lathe([(0.7, 0.0), (0.7, 1.0), (0.0, 3.2)], 4, stone,
                origin=(float(q[0] + n[0] * 0.4), float(q[1] + n[1] * 0.4), AISLE_H - 0.6), smooth=False, phase_deg=45)
    for q, t, n, s in C.ring_stations(coords, BAY, offset=BAY / 2):
        C.arched_opening(b, q - t * (BAY * 0.28), q + t * (BAY * 0.28), n, 2.6, 6.6, None, 0.8, stone, glass,
                         pointed=True, n=8)
    objs.append(b.build(f"{ID}_aisle_detail"))

    # ---- the nave: clerestory walls and the slate gable roof ---------------------------------------------------
    nave = C.offset_polygon(P, -7.2)
    if nave.geom_type != "Polygon":
        nave = max(nave.geoms, key=lambda g: g.area)
    objs.append(C.prism(f"{ID}_nave", nave, AISLE_H, NAVE_WALL_H, stone, role="mass"))
    b = C.MeshBuilder()
    ncoords = C.ring_coords(nave)
    for q, t, n, s in C.ring_stations(ncoords, BAY, offset=BAY / 2):   # clerestory windows on the same bay
        C.arched_opening(b, q - t * (BAY * 0.22), q + t * (BAY * 0.22), n, AISLE_H + 1.6, NAVE_WALL_H - 2.2, None,
                         0.55, stone, glass, pointed=True, n=6)
    # the frame's +x axis is the footprint's long axis, so the ridge runs along it
    C.gable_roof(b, ncoords, NAVE_WALL_H, NAVE_RIDGE_M - NAVE_WALL_H, slate, ridge_dir_deg=0.0, overhang=0.4)
    # lean-to aisle roofs: outer wall head up to the foot of the clerestory (offset_ring keeps the vertex count)
    inner = C.offset_ring(coords, -7.2)
    b.loft([[(x, y, AISLE_H) for x, y in coords], [(x, y, AISLE_H + 2.4) for x, y in inner]], slate,
           cap_top=False, cap_bottom=False)
    objs.append(b.build(f"{ID}_nave_detail"))

    # ---- the Broadway tower and the octagonal broach spire -----------------------------------------------------
    b = C.MeshBuilder()
    d = math.radians(east)
    u = (math.cos(d), math.sin(d))
    tc = P.centroid
    # tower centre: on the footprint's east edge, half a tower width in
    ex = max((x * u[0] + y * u[1]) for x, y in coords)
    tx = tc.x + u[0] * (ex - (tc.x * u[0] + tc.y * u[1]) - TOWER_W / 2 - 0.6)
    ty = tc.y + u[1] * (ex - (tc.x * u[0] + tc.y * u[1]) - TOWER_W / 2 - 0.6)
    tower = C.rect(tx, ty, TOWER_W, TOWER_W, angle_deg=east)
    tring = C.ring_coords(tower)
    b.prism(tring, 0.0, TOWER_PARAPET_M, stone, cap_top=False, cap_bottom=False)
    for stage, (z0, z1) in enumerate(((0.0, 14.0), (14.0, 27.0), (27.0, TOWER_PARAPET_M - 3.0))):
        for p0, p1, L, t, n in C.edges_of(tring):
            b.box_from_to(p0, p0 + t * 0.9, n, 0.55, z0, z1, stone, top=True)          # corner buttress strips
            b.box_from_to(p1 - t * 0.9, p1, n, 0.55, z0, z1, stone, top=True)
            if stage == 2:                                                              # the belfry louvres
                C.arched_opening(b, p0 + t * 1.6, p1 - t * 1.6, n, z0 + 2.0, z1 - 2.5, None, 0.6, stone,
                                 C.M.wood_dark, pointed=True, n=8)
            elif stage == 1 and abs(((math.degrees(math.atan2(n[1], n[0])) - east + 180) % 360) - 180) < 45:
                C.arched_opening(b, p0 + t * 1.5, p1 - t * 1.5, n, z0 + 1.5, z1 - 1.5, None, 0.7, stone,
                                 glass, pointed=True, n=8)                              # the great east window
    # parapet, corner pinnacles and the broach spire
    b.prism(tring, TOWER_PARAPET_M - 3.0, TOWER_PARAPET_M, stone,
            holes=[C.ring_coords(C.offset_polygon(tower, -0.55))], cap_bottom=False)
    for qx, qy in tring:
        b.lathe([(0.85, 0.0), (0.85, 2.2), (0.62, 2.8), (0.0, 8.6)], 4, stone, origin=(qx, qy, TOWER_PARAPET_M - 3.0),
                smooth=False, phase_deg=45)
    sp_h = SPIRE_TOP_M - 2.4 - TOWER_PARAPET_M
    b.lathe([(TOWER_W / 2 * 1.05, 0.0), (TOWER_W / 2 * 0.99, 3.0), (0.0, sp_h)], 8, slate,
            origin=(tx, ty, TOWER_PARAPET_M), smooth=False, phase_deg=22.5)
    b.lathe([(0.35, 0.0), (0.55, 0.5), (0.2, 1.4), (0.12, 2.4)], 8, C.M.copper_green,
            origin=(tx, ty, SPIRE_TOP_M - 2.4), smooth=True)
    b.box((tx, ty, SPIRE_TOP_M - 1.5), (1.8, 0.16, 0.16), C.M.copper_green, rot_deg=east)      # the cross
    b.box((tx, ty, SPIRE_TOP_M - 1.2), (0.16, 0.16, 2.4), C.M.copper_green)
    objs.append(b.build(f"{ID}_tower"))
    return objs, fr, fp


def main():
    objs, fr, fp = build()
    C.finish(objs, ID, BINS, fr, height_m=SPIRE_TOP_M, name="Trinity Church", lp_number="LP-00048",
             height_source="Wikipedia / LPC LP-0048 / Trinity Church Wall Street: 281 ft = 85.6 m to the top of the cross",
             fidelity_statement=(
                 "Exact: real footprint, 85.6 m to the top of the cross, the aisled nave with clerestory and stepped "
                 "buttresses, the 7.6 m square Broadway tower with an octagonal broach spire, corner pinnacles and belfry "
                 "louvres, the brownstone / slate / copper material split, and the lancet-window bay rhythm. "
                 "Inferred (+-2 m): the tower parapet at 43.0 m and the aisle (12.5 m) and clerestory (20.5 m) heights, "
                 "which are not published individually. Simplified: window tracery is a pointed opening with a single "
                 "reveal, not cusped tracery; spire crockets are omitted. Not modelled: the interior, the relief panels "
                 "of the Hunt bronze doors, and the churchyard monuments."),
             notes="The footprint includes the later chapel and parish additions, which the model carries as aisle-height fabric",
             dimensions={"spire_top_m": SPIRE_TOP_M, "tower_parapet_m": TOWER_PARAPET_M, "aisle_h_m": AISLE_H,
                         "clerestory_h_m": NAVE_WALL_H, "nave_ridge_m": NAVE_RIDGE_M, "tower_plan_m": TOWER_W,
                         "published_nave_m": [50.6, 24.1]})
    C.render_check(ID, [
        {"view": "street", "azimuth_deg": 95, "elevation_deg": "street", "distance": 95, "target_z": 34, "fov_deg": 62},
        {"view": "aerial", "azimuth_deg": 120, "elevation_deg": 22, "distance": 235, "fov_deg": 45, "target_z": 45},
    ])


if __name__ == "__main__":
    main()
