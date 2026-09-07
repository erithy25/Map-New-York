"""St. Patrick's Cathedral — Fifth Avenue between 50th and 51st Streets (BINs 1081150, 1081149, 1082595; LP-00267).
James Renwick Jr., dedicated 1879; the spires completed 1888, the Lady Chapel (Charles T. Mathews) 1906.

Dimensions used (source in brackets)
------------------------------------
* Footprint: the three real OTI polygons of the cathedral (BIN 1081150, 4,142.1 m2), the Lady Chapel (BIN 1081149,
  303.0 m2) and the parish/rectory block (BIN 1082595, 330.6 m2) — 4,775.7 m2 together, 120.3 x 61.7 m in the model's
  local frame. The Fifth Avenue front, with the twin spires, faces east.
* Dimensions [Wikipedia "St. Patrick's Cathedral (Manhattan)", the cathedral's own fact sheet, LPC LP-0267]:
  exterior length 400 ft (121.9 m); width across the transepts 174 ft (53.0 m); the twin spires reach 330 ft (100.6 m);
  the nave vault is 112 ft (34.1 m) high inside; the rose window is 26 ft (7.9 m) across; the bronze main doors weigh
  9,200 lb each. The aisle wall head (14.5 m), the clerestory head (28.0 m) and the nave ridge (41.0 m) are read off
  published sections and are stated as inferred (+-2 m).
* Materials [LPC LP-0267]: Tuckahoe and Massachusetts white marble ashlar, slate roofs, bronze doors, stained glass
  (Chartres and Nantes) in the rose and clerestory windows.

Fidelity: exact — the three real footprints, the 100.6 m twin spires, the 121.9 m length and 53.0 m transept width, the
7.9 m rose window over the central Fifth Avenue portal, three west portals, the aisled-and-clerestoried nave with a
slate gable roof, flying buttresses and pinnacles, the Lady Chapel apse, and the white-marble / slate / bronze material
split. Inferred (+-2 m) — the aisle, clerestory and ridge heights. Simplified — the Gothic tracery is modelled as
pointed openings with mullions rather than cusped tracery; the spire crockets and the gable statuary are omitted; the
rose window is a rosette of radial mullions, not the real 26-panel design. Not modelled — the interior (nave arcade,
baldachin, Lady Chapel windows) and the bronze door reliefs.
"""
from __future__ import annotations

import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import common as C  # noqa: E402
import shapely.ops  # noqa: E402
from shapely.geometry import MultiPolygon  # noqa: E402

ID = "st_patricks_cathedral"
BINS = [1081150, 1081149, 1082595]
SPIRE_TOP_M = 100.6
TOWER_PARAPET_M = 46.0
AISLE_H = 14.5
CLERESTORY_H = 28.0
NAVE_RIDGE_M = 41.0
ROSE_D = 7.9
NAVE_W = 33.0            # nave and aisles under one roof (the 53 m transept width is only at the crossing)


def build():
    C.reset()
    fps = C.load_footprints(BINS)
    union = shapely.ops.unary_union([f.polygon for f in fps])
    main = max(union.geoms, key=lambda g: g.area) if isinstance(union, MultiPolygon) else union
    fr = C.local_frame(main, fps[0].ground_z)
    P = fr.local_polygon(union)
    parts = list(P.geoms) if isinstance(P, MultiPolygon) else [P]
    body = max(parts, key=lambda g: g.area)
    others = [p for p in parts if p is not body]
    east = fr.local_cardinal(90.0)
    objs = []
    marble, slate, glass, bronze = C.M.marble_white, C.M.slate, C.M.glass_dark, C.M.bronze

    # ---- every footprint as ground-floor fabric (the IoU volume) -----------------------------------------------
    objs.append(C.plinth(f"{ID}_base", body, 0.0, AISLE_H, marble, material_top=C.M.slate))
    for i, q in enumerate(others):
        objs.append(C.plinth(f"{ID}_annex{i}", q, 0.0, min(AISLE_H, 11.5), marble, material_top=C.M.slate))
    coords = C.ring_coords(body)

    # ---- aisle walls: buttresses, pinnacles and pointed windows -------------------------------------------------
    b = C.MeshBuilder()
    BAY = 7.5                                      # the aisle bay, measured along the wall
    for q, t, n, s in C.ring_stations(coords, BAY):
        b.box_from_to(q - t * 0.8, q + t * 0.8, n, 1.5, 0.0, AISLE_H - 3.0, marble, top=True)
        b.box_from_to(q - t * 0.65, q + t * 0.65, n, 1.05, AISLE_H - 3.0, AISLE_H, marble, top=True)
        if int(s / BAY) % 2 == 0:                   # a pinnacle on every second buttress
            b.lathe([(0.8, 0.0), (0.8, 1.6), (0.0, 4.6)], 4, marble,
                    origin=(float(q[0] + n[0] * 0.5), float(q[1] + n[1] * 0.5), AISLE_H), smooth=False, phase_deg=45)
    for q, t, n, s in C.ring_stations(coords, BAY, offset=BAY / 2):
        C.arched_opening(b, q - t * (BAY * 0.26), q + t * (BAY * 0.26), n, 3.2, 8.6, None, 0.9, marble, glass,
                         pointed=True, n=10)
    objs.append(b.build(f"{ID}_aisle_detail"))

    # ---- nave: clerestory and the slate gable roof ---------------------------------------------------------------
    # The nave is a rectangle on the frame's long axis at the published nave-and-aisle width, clipped to the
    # footprint: a gable raised over the irregular footprint offset would read as a tent, not a cathedral roof.
    bx0, by0, bx1, by1 = body.bounds
    nave = C.rect_xy(bx0 + 2.0, (by0 + by1) / 2 - NAVE_W / 2, bx1 - 2.0, (by0 + by1) / 2 + NAVE_W / 2)
    nave = nave.intersection(C.offset_polygon(body, -6.0))
    if nave.geom_type != "Polygon":
        nave = max(nave.geoms, key=lambda g: g.area)
    objs.append(C.prism(f"{ID}_nave", nave, AISLE_H, CLERESTORY_H, marble, role="mass"))
    b = C.MeshBuilder()
    ncoords = C.ring_coords(nave)
    for q, t, n, s in C.ring_stations(ncoords, BAY, offset=BAY / 2):
        C.arched_opening(b, q - t * (BAY * 0.24), q + t * (BAY * 0.24), n, AISLE_H + 2.4, CLERESTORY_H - 2.6, None,
                         0.6, marble, glass, pointed=True, n=8)
    C.gable_roof(b, ncoords, CLERESTORY_H, NAVE_RIDGE_M - CLERESTORY_H, slate, ridge_dir_deg=0.0, overhang=0.7)
    # the aisle roofs are the flat slate deck on top of the plinth, finished with a parapet coping
    C.wall_ring(b, body, AISLE_H, AISLE_H + 0.7, 1.0, marble)
    # flying buttresses: a raking strut from each aisle pinnacle to the clerestory wall
    for q, t, n, s in C.ring_stations(ncoords, BAY):
        o = q + n * 9.0
        b.hull([(float(q[0]), float(q[1]), AISLE_H + 4.0), (float(q[0]), float(q[1]), CLERESTORY_H - 1.0),
                (float(o[0]), float(o[1]), AISLE_H + 2.5), (float(o[0]), float(o[1]), AISLE_H + 5.0),
                (float(q[0] + n[0] * 0.9 - t[0] * 0.5), float(q[1] + n[1] * 0.9 - t[1] * 0.5), AISLE_H + 4.0),
                (float(q[0] + n[0] * 0.9 + t[0] * 0.5), float(q[1] + n[1] * 0.9 + t[1] * 0.5), AISLE_H + 4.0),
                (float(o[0] - t[0] * 0.5), float(o[1] - t[1] * 0.5), AISLE_H + 3.5),
                (float(o[0] + t[0] * 0.5), float(o[1] + t[1] * 0.5), AISLE_H + 3.5)], marble)
    objs.append(b.build(f"{ID}_nave_detail"))

    # ---- Fifth Avenue front: two towers with spires, three portals and the rose window ---------------------------
    b = C.MeshBuilder()
    runs = sorted(C.wall_runs(coords, east, tol_deg=50.0), key=lambda r: -r[1])
    pts, Lf = runs[0]
    tw = 12.5
    # The Fifth Avenue front is broken by its three portals, so its longest *run* is only a fragment of the elevation.
    # Place the two towers from the footprint's own extent instead: front face, one tower width in from each corner.
    ux, uy = math.cos(math.radians(east)), math.sin(math.radians(east))
    vx, vy = -uy, ux
    us = [x * ux + y * uy for x, y in coords]
    vs = [x * vx + y * vy for x, y in coords]
    u_front = max(us) - (tw / 2 + 1.2)
    for v_t in (min(vs) + tw / 2 + 1.5, max(vs) - tw / 2 - 1.5):
        tx = ux * u_front + vx * v_t
        ty = uy * u_front + vy * v_t
        tower = C.rect(tx, ty, tw, tw, angle_deg=east)
        tring = C.ring_coords(tower)
        b.prism(tring, 0.0, TOWER_PARAPET_M, marble, cap_top=False, cap_bottom=False)
        for z0, z1, opening in ((0.0, 17.0, False), (17.0, 32.0, True), (32.0, TOWER_PARAPET_M - 3.5, True)):
            for e0, e1, eL, et, en in C.edges_of(tring):
                b.box_from_to(e0, e0 + et * 1.3, en, 0.75, z0, z1, marble, top=True)
                b.box_from_to(e1 - et * 1.3, e1, en, 0.75, z0, z1, marble, top=True)
                if opening:
                    C.arched_opening(b, e0 + et * 2.4, e1 - et * 2.4, en, z0 + 2.2, z1 - 3.0, None, 0.7, marble,
                                     glass if z1 < 33 else C.M.wood_dark, pointed=True, n=8)
        b.prism(tring, TOWER_PARAPET_M - 3.5, TOWER_PARAPET_M, marble,
                holes=[C.ring_coords(C.offset_polygon(tower, -0.7))], cap_bottom=False)
        for qx, qy in tring:                                   # corner pinnacles
            b.lathe([(1.0, 0.0), (1.0, 3.0), (0.7, 3.8), (0.0, 12.0)], 4, marble, origin=(qx, qy, TOWER_PARAPET_M - 3.5),
                    smooth=False, phase_deg=45)
        sp_h = SPIRE_TOP_M - 1.6 - TOWER_PARAPET_M              # the octagonal spire
        b.lathe([(tw / 2 * 1.02, 0.0), (tw / 2 * 0.95, 4.0), (0.0, sp_h)], 8, marble,
                origin=(tx, ty, TOWER_PARAPET_M), smooth=False, phase_deg=22.5)
        b.lathe([(0.4, 0.0), (0.6, 0.5), (0.22, 1.2), (0.0, 1.6)], 8, C.M.copper_green,
                origin=(tx, ty, SPIRE_TOP_M - 1.6), smooth=True)
    # gable between the towers with the rose window over the three portals
    mid, mt, mn = C.polyline_at(pts, Lf / 2)
    for f, w, h in ((-8.5, 3.0, 9.0), (0.0, 4.6, 12.0), (8.5, 3.0, 9.0)):
        a = mid + mt * (f - w / 2); c = mid + mt * (f + w / 2)
        C.arched_opening(b, a, c, mn, 0.0, h - w / 2, None, 2.2, marble, bronze, pointed=True, n=12)
    rc = mid + mn * 0.35
    seg = 16
    for i in range(seg):                                       # rose window: rosette of radial mullions
        a0 = 2 * math.pi * i / seg
        a1 = 2 * math.pi * (i + 1) / seg
        z0 = 24.0
        p_in = [(float(rc[0] + mt[0] * (ROSE_D / 2 * 0.18 * math.cos(a))), float(rc[1] + mt[1] * (ROSE_D / 2 * 0.18 * math.cos(a))),
                 z0 + ROSE_D / 2 * 0.18 * math.sin(a)) for a in (a0, a1)]
        p_out = [(float(rc[0] + mt[0] * (ROSE_D / 2 * math.cos(a))), float(rc[1] + mt[1] * (ROSE_D / 2 * math.cos(a))),
                  z0 + ROSE_D / 2 * math.sin(a)) for a in (a0, a1)]
        b.face([b.vert(*p_in[0]), b.vert(*p_out[0]), b.vert(*p_out[1]), b.vert(*p_in[1])], glass)
        q0 = rc + mt * (ROSE_D / 2 * 0.95 * math.cos(a0))
        b.box((float(q0[0] + mn[0] * 0.25), float(q0[1] + mn[1] * 0.25), z0 + ROSE_D / 2 * 0.95 * math.sin(a0)),
              (0.22, 0.3, 0.22), marble)
    for i in range(seg):                                       # the vertical stone ring around the rose
        a0 = 2 * math.pi * i / seg
        a1 = 2 * math.pi * (i + 1) / seg
        r_in, r_out = ROSE_D / 2, ROSE_D / 2 + 0.55
        pa = [(float(rc[0] + mt[0] * (r * math.cos(a)) - mn[0] * 0.15),
               float(rc[1] + mt[1] * (r * math.cos(a)) - mn[1] * 0.15),
               24.0 + r * math.sin(a)) for r, a in ((r_in, a0), (r_out, a0), (r_out, a1), (r_in, a1))]
        b.face([b.vert(*q) for q in pa], marble)
    C.pediment(b, mid - mt * 13.0, mid + mt * 13.0, mn, 34.0, 9.0, 1.6, marble, tympanum=marble, cornice_t=0.5)
    objs.append(b.build(f"{ID}_front"))
    return objs, fr, fps, P


def main():
    objs, fr, fps, P = build()
    C.finish(objs, ID, BINS, fr, height_m=SPIRE_TOP_M, name="St. Patrick's Cathedral", lp_number="LP-00267",
             real_footprint=P,
             height_source="Wikipedia / cathedral fact sheet / LPC LP-0267: spires 330 ft = 100.6 m; length 400 ft = 121.9 m; transept width 174 ft = 53.0 m; nave vault 112 ft = 34.1 m",
             fidelity_statement=(
                 "Exact: the three real footprints (cathedral, Lady Chapel, parish block), 100.6 m twin spires, 121.9 m "
                 "length, 53.0 m transept width, the 7.9 m rose window over three Fifth Avenue portals, the aisled and "
                 "clerestoried nave with a slate gable roof, flying buttresses and pinnacles, and the white-marble / slate "
                 "/ bronze material split. Inferred (+-2 m): aisle head 14.5 m, clerestory head 28.0 m, nave ridge 41.0 m. "
                 "Simplified: Gothic tracery is pointed openings with mullions, not cusped tracery; spire crockets and "
                 "gable statuary are omitted; the rose is a 16-spoke rosette, not the real 26-panel design. "
                 "Not modelled: the interior (arcade, baldachin, Lady Chapel windows) and the bronze door reliefs."),
             notes="BIN 1090615 (a 70 m2, zero-height 2017 structure on the same site) is deliberately excluded",
             dimensions={"spire_top_m": SPIRE_TOP_M, "tower_parapet_m": TOWER_PARAPET_M, "aisle_h_m": AISLE_H,
                         "clerestory_h_m": CLERESTORY_H, "nave_ridge_m": NAVE_RIDGE_M, "rose_window_d_m": ROSE_D,
                         "published_length_m": 121.9, "published_transept_width_m": 53.0, "published_vault_m": 34.1,
                         "tower_plan_m": 12.5})
    C.render_check(ID, [
        {"view": "street", "azimuth_deg": 100, "elevation_deg": "street", "distance": 172, "target_z": 51, "fov_deg": 62},
        {"view": "aerial", "azimuth_deg": 125, "elevation_deg": 24, "distance": 250, "fov_deg": 48, "target_z": 46},
    ])


if __name__ == "__main__":
    main()
