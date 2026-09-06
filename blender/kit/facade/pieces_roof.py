"""Fire escapes, parapets, roof bulkheads, cedar water towers, rooftop HVAC, antennas and billboards (24 pieces).

Fire-escape geometry follows the New York Multiple Dwelling Law party-balcony standard: 0.95 m deep platforms,
0.86 m (34 in) railings, 45 deg stairs with 9 flat-bar treads, a 0.406 m (16 in) wide drop ladder and a gooseneck
roof ladder. Floor-to-floor is 3.05 m (10 ft).

Roof pieces use ``ground_bottom_centre``: origin at the bottom-centre of the footprint on the roof deck.
"""
from __future__ import annotations

import math

import kitlib as K
import pieces_common as P

FLOOR = 3.050          # tenement floor-to-floor
PLAT_D = 0.950         # platform depth from the wall
PLAT_W = 2.200         # platform width (covers two windows of a 7.6 m tenement bay)
STAIR_W = 0.560


# --------------------------------------------------------------------------- fire escapes
def _fe_unit(width: float, *, stair: bool = True) -> K.Mesh:
    """One storey of party-balcony fire escape: platform, railings, wall brackets and the stair down to the next."""
    m = K.Mesh()
    x0, x1 = -width / 2, width / 2
    y0, y1 = -PLAT_D, -0.030
    P.grating(m, x0, x1, y0, y1, 0.0, P.BLACK)
    # stair well opening at the +X end
    well_x0 = x1 - STAIR_W - 0.060
    P.railing(m, [(x0, y0, 0.0), (x1, y0, 0.0)], P.RAIL_H, P.BLACK, pitch=0.135, rails=2)          # street rail
    P.railing(m, [(x0, y0, 0.0), (x0, y1, 0.0)], P.RAIL_H, P.BLACK, pitch=0.135, rails=2)          # -X return
    P.railing(m, [(x1, y0, 0.0), (x1, y1, 0.0)], P.RAIL_H, P.BLACK, pitch=0.135, rails=2)          # +X return
    if stair:
        P.railing(m, [(well_x0, y0 + 0.10, 0.0), (well_x0, y1, 0.0)], P.RAIL_H, P.BLACK, pitch=0.145, rails=2)
    for s in (-1, 1):                                                                               # wall brackets
        x = s * (width / 2 - 0.16)
        P._bar(m, K.Vector((x, -0.030, -0.045)), K.Vector((x, -PLAT_D + 0.10, -0.045)), K.Vector((0.0, 0.0, 1.0)), 0.075, 0.020, P.BLACK)
        P._bar(m, K.Vector((x, -PLAT_D + 0.12, -0.055)), K.Vector((x, -0.020, -0.62)), K.Vector((1.0, 0.0, 0.0)), 0.055, 0.016, P.BLACK)
        m.box((x - 0.055, -0.030, -0.68), (x + 0.055, 0.030, -0.56), P.BLACK)                      # wall plate
    if stair:
        sx0, sx1 = well_x0 + 0.055, x1 - 0.055
        P.stair_flight(m, sx0, sx1, -0.030, -0.09, -PLAT_D + 0.06, -FLOOR + 0.06, P.BLACK, treads=9)
        for xx in (sx0 - 0.03, sx1 + 0.03):                                                        # stair handrails
            P.railing(m, [(xx, -0.030, -0.09), (xx, -PLAT_D + 0.06, -FLOOR + 0.06)], 0.760, P.BLACK, pitch=0.30, rails=2)
    return m


def _fe_lod(width: float, *, stair: bool = True) -> K.Mesh:
    """Explicit LOD1: flat-quad deck, rails, every third picket and the stair as a ribbed ramp. Collapse decimation
    cannot reduce a mesh made of separate closed bars below four triangles each, so the LOD is modelled."""
    m = K.Mesh()
    x0, x1 = -width / 2, width / 2
    y0, y1 = -PLAT_D, -0.030
    m.box((x0, y0, -0.030), (x1, y1, 0.0), P.BLACK, faces="yYZ")                                   # deck
    for z in (P.RAIL_H, P.RAIL_H * 0.45):                                                          # two rails, street side
        m.box((x0, y0 - 0.008, z - 0.014), (x1, y0 + 0.008, z + 0.014), P.BLACK, faces="yY")
    npick = max(3, int(width / 0.40))
    for k in range(npick + 1):                                                                     # thinned pickets
        xx = x0 + (x1 - x0) * k / npick
        m.face([(xx - 0.010, y0, 0.0), (xx + 0.010, y0, 0.0), (xx + 0.010, y0, P.RAIL_H), (xx - 0.010, y0, P.RAIL_H)], P.BLACK)
    for xx in (x0, x1):                                                                            # end returns
        m.box((xx - 0.015, y0, 0.0), (xx + 0.015, y1, P.RAIL_H), P.BLACK, faces="yY")
        m.face([(xx, y0, 0.0), (xx, y1, 0.0), (xx, y1, P.RAIL_H * 0.45 + 0.014), (xx, y0, P.RAIL_H * 0.45 + 0.014)], P.BLACK)
    for s in (-1, 1):                                                                              # wall brackets
        x = s * (width / 2 - 0.16)
        m.face([(x, -0.030, -0.045), (x, y0 + 0.10, -0.045), (x, -0.020, -0.62)], P.BLACK)
    if stair:
        sx0, sx1 = x1 - STAIR_W - 0.005, x1 - 0.055
        m.face([(sx0, -0.030, -0.09), (sx1, -0.030, -0.09),
                (sx1, y0 + 0.06, -FLOOR + 0.06), (sx0, y0 + 0.06, -FLOOR + 0.06)], P.BLACK)
        for k in range(5):                                                                          # tread ribs
            t = (k + 0.5) / 5
            y = -0.030 + (y0 + 0.09) * t
            z = -0.09 + (-FLOOR + 0.15) * t
            m.box((sx0, y - 0.10, z - 0.010), (sx1, y + 0.10, z + 0.010), P.BLACK, faces="Z")
        for xx in (sx0, sx1):                                                                       # stringers + handrail
            m.face([(xx, -0.030, -0.09), (xx, y0 + 0.06, -FLOOR + 0.06),
                    (xx, y0 + 0.06, -FLOOR + 0.82), (xx, -0.030, 0.67)], P.BLACK)
    return m


@K.register("fire_escape_floor_unit", "fire_escape", nominal_size=(2.23, 1.007, 3.901),
            description="One storey of standard NYC party-balcony fire escape: 2.20 x 0.95 m perforated platform, 0.86 m railings, "
                        "wall brackets and a 45 deg stair with nine flat-bar treads down to the storey below.",
            features=["fire_escape"], budget=3000, lod1=lambda: _fe_lod(PLAT_W))
def _fe_floor():
    return _fe_unit(PLAT_W)


@K.register("fire_escape_floor_unit_wide", "fire_escape", nominal_size=(3.08, 1.007, 3.901),
            description="Wide (3.05 m) fire-escape storey unit for three-window bays, otherwise identical to the standard unit.",
            features=["fire_escape"], budget=3000, lod1=lambda: _fe_lod(3.050))
def _fe_wide():
    return _fe_unit(3.050)


@K.register("fire_escape_balcony_top", "fire_escape", nominal_size=(2.23, 0.995, 1.57),
            description="Top-storey fire-escape balcony with no descending stair (the run starts at the storey below).",
            features=["fire_escape"], budget=3000, lod1=lambda: _fe_lod(PLAT_W, stair=False))
def _fe_top():
    return _fe_unit(PLAT_W, stair=False)


@K.register("fire_escape_corner_return", "fire_escape", nominal_size=(1.56, 1.56, 1.533), anchor="wall_corner_bottom",
            description="Fire-escape corner return: an L-shaped platform wrapping an outside building corner, with railings on "
                        "both open sides and brackets on both walls.",
            features=["fire_escape"], budget=3000)
def _fe_corner():
    m = K.Mesh()
    a = 1.550
    # L platform: leg along -X wall (y = 0 plane) and leg along the +X return wall (x = 0 plane)
    P.grating(m, -a, -0.030, -PLAT_D, -0.030, 0.0, P.BLACK)
    P.grating(m, -PLAT_D, -0.030, -a, -PLAT_D, 0.0, P.BLACK)
    P.railing(m, [(-a, -PLAT_D, 0.0), (-0.030, -PLAT_D, 0.0), (-0.030, -a, 0.0)], P.RAIL_H, P.BLACK, pitch=0.135, rails=2)
    P.railing(m, [(-a, -PLAT_D, 0.0), (-a, -0.030, 0.0)], P.RAIL_H, P.BLACK, pitch=0.135, rails=2)
    P.railing(m, [(-PLAT_D, -a, 0.0), (-0.030, -a, 0.0)], P.RAIL_H, P.BLACK, pitch=0.135, rails=2)
    for x in (-a + 0.16, -0.20):
        P._bar(m, K.Vector((x, -0.030, -0.045)), K.Vector((x, -PLAT_D + 0.08, -0.045)), K.Vector((0.0, 0.0, 1.0)), 0.075, 0.020, P.BLACK)
        P._bar(m, K.Vector((x, -PLAT_D + 0.10, -0.055)), K.Vector((x, -0.020, -0.62)), K.Vector((1.0, 0.0, 0.0)), 0.055, 0.016, P.BLACK)
    for y in (-a + 0.16, -0.20):
        P._bar(m, K.Vector((-0.030, y, -0.045)), K.Vector((-PLAT_D + 0.08, y, -0.045)), K.Vector((0.0, 0.0, 1.0)), 0.075, 0.020, P.BLACK)
        P._bar(m, K.Vector((-PLAT_D + 0.10, y, -0.055)), K.Vector((-0.020, y, -0.62)), K.Vector((0.0, 1.0, 0.0)), 0.055, 0.016, P.BLACK)
    return m


@K.register("fire_escape_drop_ladder", "fire_escape", nominal_size=(0.57, 0.12, 3.3),
            description="Counterweighted drop ladder in its stowed position: 0.406 m wide, 3.05 m long with 305 mm rungs, guides "
                        "and the release catch at the lowest balcony.",
            features=["fire_escape"], budget=3000)
def _fe_drop():
    m = K.Mesh()
    P.ladder(m, 0.0, -0.60, 0.10, 3.15, 0.406, P.BLACK)
    for s in (-1, 1):                                                        # slide guides on the balcony
        x = s * 0.265
        m.box((x - 0.020, -0.66, 3.05), (x + 0.020, -0.54, 3.30), P.BLACK)
        m.box((x - 0.020, -0.66, 0.05), (x + 0.020, -0.54, 0.30), P.BLACK)
    m.box((-0.075, -0.66, 3.15), (0.075, -0.54, 3.35), P.BLACK)              # release catch
    return m


@K.register("fire_escape_top_hook", "fire_escape", nominal_size=(0.48, 1.078, 2.16),
            description="Gooseneck roof ladder: the fire escape's top run hooked over the parapet, with two curved stringers and "
                        "eight rungs (MDL requirement above the top balcony).",
            features=["fire_escape"], budget=3000)
def _fe_hook():
    m = K.Mesh()
    seg = 7
    for s in (-1, 1):
        x = s * 0.203
        pts = [(x, -0.60, 0.0)]
        for i in range(seg + 1):
            t = i / seg
            pts.append((x, -0.60 + 0.60 * (1 - math.cos(t * math.pi / 2)), 1.55 + 0.55 * math.sin(t * math.pi / 2)))
        pts.append((x, 0.42, 2.10))
        pts.insert(1, (x, -0.60, 1.55))
        for i in range(len(pts) - 1):
            P._bar(m, K.Vector(pts[i]), K.Vector(pts[i + 1]), K.Vector((1.0, 0.0, 0.0)), 0.036, 0.026, P.BLACK)
    for k in range(5):
        z = 0.22 + k * 0.305
        m.box((-0.203, -0.615, z - 0.011), (0.203, -0.585, z + 0.011), P.BLACK)
    for k in range(3):
        t = (k + 1) / 4
        y = -0.60 + 0.60 * (1 - math.cos(t * math.pi / 2))
        z = 1.55 + 0.55 * math.sin(t * math.pi / 2)
        m.box((-0.203, y - 0.015, z - 0.011), (0.203, y + 0.015, z + 0.011), P.BLACK)
    m.box((-0.24, 0.36, 2.06), (0.24, 0.46, 2.16), P.BLACK)                  # parapet hook plate
    return m


# --------------------------------------------------------------------------- parapets
@K.register("parapet_wall_brick", "parapet", anchor="ground_bottom_centre", nominal_size=(1.0, 0.39, 1.07),
            description="Brick parapet wall, 1 m run x 0.34 m thick x 1.07 m (42 in) high with a cast-stone coping — the standard "
                        "NYC roof-edge parapet.",
            features=["parapet"], budget=300)
def _parapet_brick():
    m = K.Mesh()
    m.box((-0.5, -0.170, 0.0), (0.5, 0.170, 0.980), "red_brick")
    m.box((-0.5, -0.195, 0.980), (0.5, 0.195, 1.070), "precast")
    return m


@K.register("parapet_cap_stone", "parapet", anchor="ground_bottom_centre", nominal_size=(1.0, 0.42, 0.118),
            description="Limestone parapet coping, 1 m run x 0.42 m wide with a 12 mm drip on both edges.",
            features=["parapet"], budget=300)
def _parapet_cap_stone():
    m = K.Mesh()
    m.box((-0.5, -0.210, 0.0), (0.5, 0.210, 0.100), "limestone")
    m.box((-0.5, -0.185, -0.018), (0.5, 0.185, 0.0), "limestone")
    return m


@K.register("parapet_cap_terracotta", "parapet", anchor="ground_bottom_centre", nominal_size=(1.0, 0.4, 0.19),
            description="Glazed terracotta parapet coping with a rounded top, 1 m run x 0.40 m wide (1920s apartment houses).",
            features=["parapet"], budget=300)
def _parapet_cap_tc():
    m = K.Mesh()
    prof = [(-0.200, 0.0), (-0.200, 0.090), (-0.150, 0.165), (0.0, 0.190), (0.150, 0.165), (0.200, 0.090), (0.200, 0.0)]
    m.extrude_profile(prof, -0.5, 0.5, "terracotta", closed=True, caps=True, flip=True)
    return m


@K.register("parapet_cap_metal_coping", "parapet", anchor="ground_bottom_centre", nominal_size=(1.0, 0.4, 0.135),
            description="Aluminium snap-on parapet coping with cleats and drip edges, 1 m run x 0.40 m wide (modern re-roofing).",
            features=["parapet"], budget=300)
def _parapet_cap_metal():
    m = K.Mesh()
    prof = [(-0.200, 0.0), (-0.200, 0.080), (-0.190, 0.110), (0.0, 0.135), (0.190, 0.110), (0.200, 0.080), (0.200, 0.0)]
    m.extrude_profile(prof, -0.5, 0.5, "metal_panel", closed=True, caps=True, flip=True)
    return m


@K.register("parapet_balustrade", "parapet", anchor="ground_bottom_centre", nominal_size=(1.007, 0.32, 0.98),
            description="Cast-stone roof balustrade, 1 m run: moulded base rail, seven turned balusters and a moulded cap "
                        "(Beaux-Arts apartment house / bank).",
            features=["parapet"], budget=900)
def _parapet_balustrade():
    m = K.Mesh()
    m.box((-0.5, -0.150, 0.0), (0.5, 0.150, 0.150), "limestone")
    for k in range(7):
        cx = -0.5 + 1.0 * (k + 0.5) / 7
        m.lathe([(0.052, 0.150), (0.070, 0.200), (0.048, 0.330), (0.075, 0.470), (0.058, 0.620), (0.070, 0.700), (0.052, 0.760)],
                8, "limestone", center=(cx, 0.0))
    m.box((-0.5, -0.135, 0.760), (0.5, 0.135, 0.880), "limestone")
    m.box((-0.5, -0.160, 0.880), (0.5, 0.160, 0.980), "limestone")
    return m


# --------------------------------------------------------------------------- bulkheads
@K.register("bulkhead_stair_brick", "bulkhead", anchor="ground_bottom_centre", nominal_size=(2.9, 3.5, 2.71),
            description="Brick roof stair bulkhead, 2.75 x 3.35 m x 2.60 m with a steel door, a sloped membrane roof and a "
                        "cast-stone coping.",
            features=["bulkhead"], budget=900)
def _bulkhead_brick():
    m = K.Mesh()
    w, d, h = 2.750, 3.350, 2.600
    m.box((-w / 2, -d / 2, 0.0), (w / 2, d / 2, h), "red_brick", faces="yYxX")
    m.box((-w / 2 - 0.075, -d / 2 - 0.075, h), (w / 2 + 0.075, d / 2 + 0.075, h + 0.11), "precast")
    m.box((-w / 2 + 0.06, -d / 2 + 0.06, h - 0.14), (w / 2 - 0.06, d / 2 - 0.06, h), "roof_membrane")
    m.box((-0.52, -d / 2 - 0.020, 0.0), (0.52, -d / 2 + 0.06, 2.130), "paint_grey")            # steel door
    m.box((-0.56, -d / 2 - 0.030, 0.0), (0.56, -d / 2 + 0.02, 2.200), P.GALV, faces="yxXZ")
    m.cylinder((0.40, -d / 2 - 0.075, 1.05), (0.40, -d / 2 + 0.02, 1.05), 0.020, "chrome", segments=8)
    m.box((-0.30, -d / 2 - 0.045, 2.28), (0.30, -d / 2 - 0.015, 2.44), "fluoro_white")          # door light
    return m


@K.register("bulkhead_stair_metal", "bulkhead", anchor="ground_bottom_centre", nominal_size=(2.3, 2.75, 2.44),
            description="Corrugated-metal roof stair bulkhead, 2.15 x 2.60 m x 2.35 m with a hinged hatch panel and a "
                        "galvanised drip edge (later addition on tenement roofs).",
            features=["bulkhead"], budget=900)
def _bulkhead_metal():
    m = K.Mesh()
    w, d, h = 2.150, 2.600, 2.350
    m.box((-w / 2, -d / 2, 0.0), (w / 2, d / 2, h), "corrugated_metal", faces="yYxX")
    m.box((-w / 2 - 0.075, -d / 2 - 0.075, h), (w / 2 + 0.075, d / 2 + 0.075, h + 0.09), P.GALV)
    m.box((-w / 2 + 0.05, -d / 2 + 0.05, h - 0.10), (w / 2 - 0.05, d / 2 - 0.05, h), "roof_membrane")
    m.box((-0.46, -d / 2 - 0.030, 0.0), (0.46, -d / 2 + 0.05, 2.050), "paint_grey")
    for zz in (0.35, 1.70):
        m.box((-0.50, -d / 2 - 0.045, zz - 0.030), (0.10, -d / 2 - 0.020, zz + 0.030), P.BLACK)
    return m


@K.register("bulkhead_elevator_machine", "bulkhead", anchor="ground_bottom_centre", nominal_size=(3.7, 4.3, 4.02),
            description="Elevator machine-room bulkhead, 3.55 x 4.15 m x 3.90 m: brick walls, louvred vents, a service door and "
                        "a coped parapet.",
            features=["bulkhead"], budget=900)
def _bulkhead_elev():
    m = K.Mesh()
    w, d, h = 3.550, 4.150, 3.900
    m.box((-w / 2, -d / 2, 0.0), (w / 2, d / 2, h), "tan_brick", faces="yYxX")
    m.box((-w / 2 - 0.075, -d / 2 - 0.075, h), (w / 2 + 0.075, d / 2 + 0.075, h + 0.12), "precast")
    m.box((-w / 2 + 0.06, -d / 2 + 0.06, h - 0.15), (w / 2 - 0.06, d / 2 - 0.06, h), "roof_membrane")
    m.box((-0.52, -d / 2 - 0.020, 0.0), (0.52, -d / 2 + 0.06, 2.130), "paint_grey")
    for s in (-1, 1):                                                                            # louvred vents
        m.box((s * 1.05 - 0.45, -d / 2 - 0.030, 2.45), (s * 1.05 + 0.45, -d / 2 + 0.02, 3.35), P.GALV)
        for k in range(8):
            m.box((s * 1.05 - 0.42, -d / 2 - 0.045, 2.50 + k * 0.105), (s * 1.05 + 0.42, -d / 2 - 0.026, 2.56 + k * 0.105), P.BLACK)
    return m


# --------------------------------------------------------------------------- cedar water towers
def _water_tower(tank_d: float, staves: float, frame_h: float, legs: int = 4) -> K.Mesh:
    """Rosenwach-type cedar water tank on a steel dunnage frame: staves, hoops, conical roof, finial and access ladder."""
    m = K.Mesh()
    r = tank_d / 2
    z0 = frame_h
    z1 = z0 + staves
    seg = 20
    m.lathe([(r, z0), (r, z1)], seg, "cedar_wood", smooth=False)                                   # staves
    m.lathe([(0.0, z0 - 0.06), (r, z0 - 0.06), (r, z0)], seg, "cedar_wood", smooth=False)          # tank bottom
    roof_h = tank_d * 0.28
    m.lathe([(r + 0.09, z1), (r * 0.55, z1 + roof_h * 0.62), (0.0, z1 + roof_h)], seg, "cedar_wood", smooth=False)
    for k in range(4):                                                                              # steel hoops
        z = z0 + staves * (k + 0.5) / 4
        m.lathe([(r + 0.012, z - 0.020), (r + 0.012, z + 0.020)], seg, P.GALV, smooth=True)
    m.cylinder((0.0, 0.0, z1 + roof_h), (0.0, 0.0, z1 + roof_h + 0.30), 0.055, P.GALV, segments=8)  # finial vent
    m.lathe([(0.0, z1 + roof_h + 0.30), (0.16, z1 + roof_h + 0.24)], 8, P.GALV, caps=(False, True))
    # steel dunnage frame
    a = r * 0.80
    corners = [(a, a), (-a, a), (-a, -a), (a, -a)][:legs]
    for (cx, cy) in corners:
        m.box((cx - 0.055, cy - 0.055, 0.0), (cx + 0.055, cy + 0.055, z0), "rust")
        m.box((cx - 0.13, cy - 0.13, 0.0), (cx + 0.13, cy + 0.13, 0.10), "rust")                    # base plate
    for i in range(len(corners)):
        (ax, ay) = corners[i]
        (bx, by) = corners[(i + 1) % len(corners)]
        for zz in (z0 * 0.42, z0 - 0.10):                                                            # horizontal braces
            P._bar(m, K.Vector((ax, ay, zz)), K.Vector((bx, by, zz)), K.Vector((0.0, 0.0, 1.0)), 0.075, 0.020, "rust")
        n = K.Vector((0.0, 0.0, 1.0))
        P._bar(m, K.Vector((ax, ay, 0.10)), K.Vector((bx, by, z0 * 0.42)), n, 0.055, 0.014, "rust")  # diagonals
        P._bar(m, K.Vector((bx, by, 0.10)), K.Vector((ax, ay, z0 * 0.42)), n, 0.055, 0.014, "rust")
    for i in range(len(corners)):                                                                     # tank cradle beams
        (ax, ay) = corners[i]
        (bx, by) = corners[(i + 1) % len(corners)]
        P._bar(m, K.Vector((ax, ay, z0 - 0.05)), K.Vector((bx, by, z0 - 0.05)), K.Vector((0.0, 0.0, 1.0)), 0.150, 0.030, "rust")
    P.ladder(m, 0.0, -(r + 0.22), 0.20, z1 + 0.30, 0.406, "rust")
    m.cylinder((0.0, 0.0, 0.0), (0.0, 0.0, z0 - 0.05), 0.075, "rust", segments=8)                     # riser pipe
    m.cylinder((r * 0.35, r * 0.35, 0.0), (r * 0.35, r * 0.35, z0 + 0.40), 0.055, "rust", segments=8)  # overflow
    return m


@K.register("water_tower_small", "water_tower", anchor="ground_bottom_centre", nominal_size=(3.53, 3.676, 10.398),
            description="10 000 US gallon cedar water tank (3.35 m diameter x 3.66 m staves) on a 5.5 m steel dunnage frame, with "
                        "four hoops, a conical roof, finial vent, access ladder and riser (Rosenwach type).",
            features=["water_tower"], budget=4000)
def _wt_small():
    return _water_tower(3.350, 3.660, 5.500)


@K.register("water_tower_large", "water_tower", anchor="ground_bottom_centre", nominal_size=(4.45, 4.596, 13.076),
            description="20 000 US gallon cedar water tank (4.27 m diameter x 4.88 m staves) on a 6.7 m steel dunnage frame — the "
                        "tall tank seen on 1920s loft and apartment roofs.",
            features=["water_tower"], budget=4000)
def _wt_large():
    return _water_tower(4.270, 4.880, 6.700)


# --------------------------------------------------------------------------- rooftop HVAC
@K.register("hvac_rooftop_unit_small", "hvac", anchor="ground_bottom_centre", nominal_size=(1.33, 1.03, 1.118),
            description="Packaged rooftop air-conditioning unit, 1.22 x 0.92 x 0.85 m on a 0.25 m timber curb, with a condenser "
                        "fan grille, side louvres and a service panel.",
            features=["rooftop_hvac"], budget=1200)
def _rtu_small():
    m = K.Mesh()
    w, d, h, curb = 1.220, 0.920, 0.850, 0.250
    m.box((-w / 2 - 0.055, -d / 2 - 0.055, 0.0), (w / 2 + 0.055, d / 2 + 0.055, curb), "interior_wood_floor")
    m.box((-w / 2, -d / 2, curb), (w / 2, d / 2, curb + h), P.GALV)
    m.lathe([(0.0, curb + h), (0.30, curb + h)], 12, P.GALV, center=(0.22, 0.0))
    for k in range(6):                                                          # fan guard bars
        a = math.pi * k / 6
        m.box((0.22 - 0.30 * math.cos(a) - 0.010, -0.30 * math.sin(a), curb + h),
              (0.22 + 0.30 * math.cos(a) + 0.010, 0.30 * math.sin(a), curb + h + 0.018), P.BLACK) if k == 0 else \
            P._bar(m, K.Vector((0.22 - 0.30 * math.cos(a), -0.30 * math.sin(a), curb + h + 0.010)),
                   K.Vector((0.22 + 0.30 * math.cos(a), 0.30 * math.sin(a), curb + h + 0.010)), K.Vector((0.0, 0.0, 1.0)), 0.014, 0.010, P.BLACK)
    for k in range(7):                                                          # condenser louvres
        m.box((-w / 2 - 0.008, -d / 2 + 0.06 + k * 0.11, curb + 0.10), (-w / 2 + 0.004, -d / 2 + 0.14 + k * 0.11, curb + h - 0.10), P.BLACK)
    m.box((-0.30, -d / 2 - 0.010, curb + 0.12), (0.42, -d / 2 + 0.004, curb + h - 0.12), "metal_panel")
    return m


@K.register("hvac_rooftop_unit_large", "hvac", anchor="ground_bottom_centre", nominal_size=(3.33, 2.79, 1.838),
            description="Large packaged rooftop unit, 3.05 x 1.83 x 1.50 m on a 0.30 m curb, with twin condenser fans, an economiser "
                        "hood, a disconnect switch and a supply/return duct drop.",
            features=["rooftop_hvac"], budget=1200)
def _rtu_large():
    m = K.Mesh()
    w, d, h, curb = 3.050, 1.830, 1.500, 0.300
    m.box((-w / 2 - 0.06, -d / 2 - 0.06, 0.0), (w / 2 + 0.06, d / 2 + 0.06, curb), "interior_wood_floor")
    m.box((-w / 2, -d / 2, curb), (w / 2, d / 2, curb + h), "metal_panel")
    for s in (-1, 1):
        m.lathe([(0.0, curb + h), (0.42, curb + h)], 12, P.GALV, center=(s * 0.72, 0.0))
        for k in range(5):
            a = math.pi * k / 5
            P._bar(m, K.Vector((s * 0.72 - 0.42 * math.cos(a), -0.42 * math.sin(a), curb + h + 0.012)),
                   K.Vector((s * 0.72 + 0.42 * math.cos(a), 0.42 * math.sin(a), curb + h + 0.012)), K.Vector((0.0, 0.0, 1.0)), 0.016, 0.012, P.BLACK)
    m.box((w / 2 - 0.90, -d / 2 - 0.34, curb + 0.20), (w / 2 - 0.10, -d / 2, curb + h - 0.15), P.GALV)     # economiser hood
    m.box((-w / 2 - 0.22, -0.22, curb + 0.45), (-w / 2, 0.22, curb + 1.05), "paint_grey")                  # disconnect
    m.box((-0.62, d / 2 - 0.02, -0.02), (0.62, d / 2 + 0.62, curb + 0.34), P.GALV)                          # duct drop
    return m


@K.register("hvac_condenser_bank", "hvac", anchor="ground_bottom_centre", nominal_size=(2.6, 0.93, 1.25),
            description="Bank of three split-system condensers, 0.80 x 0.32 m each, on a galvanised dunnage rack 0.35 m above "
                        "the roof deck.",
            features=["rooftop_hvac"], budget=1200)
def _cond_bank():
    m = K.Mesh()
    rack = 0.350
    for k in range(3):
        x = -0.85 + k * 0.85
        m.box((x - 0.40, -0.16, rack), (x + 0.40, 0.16, rack + 0.90), P.GALV)
        m.lathe([(0.0, rack + 0.90), (0.30, rack + 0.90)], 10, P.BLACK, center=(x, 0.0))
        for i in range(9):
            m.box((x - 0.38, -0.175, rack + 0.06 + i * 0.09), (x + 0.38, -0.162, rack + 0.11 + i * 0.09), P.BLACK)
    for s in (-1, 1):
        m.box((-1.30, s * 0.42 - 0.045, 0.0), (1.30, s * 0.42 + 0.045, rack), P.GALV)
    for x in (-1.20, 0.0, 1.20):
        m.box((x - 0.045, -0.46, 0.0), (x + 0.045, 0.46, 0.09), P.GALV)
    return m


@K.register("hvac_exhaust_fan", "hvac", anchor="ground_bottom_centre", nominal_size=(0.92, 0.897, 0.86),
            description="Mushroom (upblast) roof exhaust fan, 0.86 m diameter hood on a 0.30 m curb — kitchen and toilet exhausts.",
            features=["rooftop_hvac"], budget=1200)
def _exhaust_fan():
    m = K.Mesh()
    curb = 0.300
    m.box((-0.34, -0.34, 0.0), (0.34, 0.34, curb), "interior_wood_floor")
    m.lathe([(0.30, curb), (0.30, curb + 0.10)], 14, P.GALV)
    m.lathe([(0.43, curb + 0.20), (0.46, curb + 0.36), (0.40, curb + 0.50), (0.20, curb + 0.56), (0.0, curb + 0.56)], 14, P.GALV, smooth=True)
    for k in range(3):
        a = 2 * math.pi * k / 3
        m.box((0.30 * math.cos(a) - 0.020, 0.30 * math.sin(a) - 0.020, curb + 0.10),
              (0.30 * math.cos(a) + 0.020, 0.30 * math.sin(a) + 0.020, curb + 0.26), P.GALV)
    return m


@K.register("hvac_cooling_tower", "hvac", anchor="ground_bottom_centre", nominal_size=(3.05, 2.327, 3.22),
            description="Induced-draught cooling tower, 3.05 x 2.13 x 2.90 m on a steel dunnage frame: louvred air inlets, fan "
                        "cowl and a sump connection.",
            features=["rooftop_hvac"], budget=1200)
def _cooling_tower():
    m = K.Mesh()
    w, d, h, base = 3.050, 2.130, 2.400, 0.400
    m.box((-w / 2, -d / 2, base), (w / 2, d / 2, base + h), "metal_panel")
    for s in (-1, 1):                                                       # louvred inlets on the long sides
        for k in range(10):
            z = base + 0.18 + k * 0.19
            m.box((-w / 2 + 0.10, s * (d / 2) - s * 0.012, z), (w / 2 - 0.10, s * (d / 2) + s * 0.012, z + 0.12), P.BLACK)
    m.lathe([(0.85, base + h), (0.88, base + h + 0.30), (0.80, base + h + 0.42)], 14, P.GALV)
    for k in range(4):
        a = math.pi * k / 4
        P._bar(m, K.Vector((-0.85 * math.cos(a), -0.85 * math.sin(a), base + h + 0.40)),
               K.Vector((0.85 * math.cos(a), 0.85 * math.sin(a), base + h + 0.40)), K.Vector((0.0, 0.0, 1.0)), 0.030, 0.018, P.BLACK)
    for (cx, cy) in ((w / 2 - 0.22, d / 2 - 0.22), (-w / 2 + 0.22, d / 2 - 0.22), (w / 2 - 0.22, -d / 2 + 0.22), (-w / 2 + 0.22, -d / 2 + 0.22)):
        m.box((cx - 0.055, cy - 0.055, 0.0), (cx + 0.055, cy + 0.055, base), P.GALV)
    m.box((-w / 2, -0.12, 0.0), (w / 2, 0.12, 0.08), P.GALV)
    m.cylinder((-w / 2 + 0.35, -d / 2 - 0.10, 0.0), (-w / 2 + 0.35, -d / 2 - 0.10, base + 0.55), 0.085, "rust", segments=8)
    return m


@K.register("hvac_vent_pipe_cluster", "hvac", anchor="ground_bottom_centre", nominal_size=(1.14, 0.745, 1.521),
            description="Cluster of five cast-iron soil vent pipes and a gooseneck vent through the roof membrane, with lead "
                        "flashings — the commonest object on a NYC roof.",
            features=["rooftop_hvac"], budget=1200)
def _vent_cluster():
    m = K.Mesh()
    pipes = [(-0.42, -0.20, 0.86), (-0.10, 0.14, 1.15), (0.18, -0.24, 0.70), (0.44, 0.10, 0.95)]
    for (x, y, h) in pipes:
        m.lathe([(0.14, 0.0), (0.13, 0.045), (0.075, 0.075)], 10, "rust", center=(x, y))          # lead flashing
        m.cylinder((x, y, 0.0), (x, y, h), 0.062, "rust", segments=10)
        m.lathe([(0.062, h), (0.078, h + 0.035)], 10, "rust", center=(x, y), caps=(False, True))
    m.cylinder((0.05, 0.30, 0.0), (0.05, 0.30, 1.45), 0.075, P.GALV, segments=10)                 # gooseneck
    m.cylinder((0.05, 0.30, 1.45), (0.05, 0.30 - 0.30, 1.45), 0.075, P.GALV, segments=10)
    m.lathe([(0.075, 1.30), (0.115, 1.36)], 10, P.GALV, center=(0.05, 0.0), caps=(False, True))
    return m


@K.register("hvac_chimney_brick", "hvac", anchor="ground_bottom_centre", nominal_size=(1.2, 1.141, 2.765),
            description="Brick boiler chimney above the roof: 0.90 x 0.65 m shaft, corbelled cap and two clay flue liners.",
            features=["rooftop_hvac"], budget=1200)
def _chimney():
    m = K.Mesh()
    w, d, h = 0.900, 0.650, 2.300
    m.box((-w / 2, -d / 2, 0.0), (w / 2, d / 2, h), "red_brick")
    m.box((-w / 2 - 0.075, -d / 2 - 0.075, h), (w / 2 + 0.075, d / 2 + 0.075, h + 0.135), "red_brick")
    m.box((-w / 2 - 0.045, -d / 2 - 0.045, h + 0.135), (w / 2 + 0.045, d / 2 + 0.045, h + 0.185), "precast")
    for s in (-1, 1):
        m.box((s * 0.20 - 0.115, -0.115, h + 0.185), (s * 0.20 + 0.115, 0.115, h + 0.465), "terracotta")
    m.lathe([(0.0, 0.0), (0.60, 0.0), (0.60, 0.055)], 10, "rust", center=(0.0, 0.0))              # base flashing
    return m


# --------------------------------------------------------------------------- antennas
@K.register("antenna_cell_panel_array", "antenna", anchor="ground_bottom_centre", nominal_size=(1.919, 2.169, 3.85),
            description="Cellular sector array: three pairs of 1.30 m panel antennas on a 2.1 m triangular head frame above a "
                        "4 m monopole, with remote radio units and cable trays.",
            features=["cell_antennas"], budget=900)
def _cell_array():
    m = K.Mesh()
    pole_h = 3.100
    m.cylinder((0.0, 0.0, 0.0), (0.0, 0.0, pole_h), 0.110, P.GALV, segments=10)
    m.lathe([(0.0, 0.0), (0.42, 0.0), (0.42, 0.06)], 10, P.GALV)
    for k in range(3):
        a = 2 * math.pi * k / 3
        ux, uy = math.cos(a), math.sin(a)
        m.box((-0.055, -0.055, pole_h), (0.055, 0.055, pole_h + 0.10), P.GALV)
        P._bar(m, K.Vector((0.0, 0.0, pole_h + 0.05)), K.Vector((ux * 0.95, uy * 0.95, pole_h + 0.05)), K.Vector((0.0, 0.0, 1.0)), 0.060, 0.045, P.GALV)
        for s in (-1, 1):
            cx = ux * 0.95 - uy * s * 0.28
            cy = uy * 0.95 + ux * s * 0.28
            for i, (pa, pb) in enumerate(((-0.075, 0.075),)):
                m.box((cx - 0.14 * abs(uy) - 0.06 * abs(ux), cy - 0.14 * abs(ux) - 0.06 * abs(uy), pole_h - 0.55),
                      (cx + 0.14 * abs(uy) + 0.06 * abs(ux), cy + 0.14 * abs(ux) + 0.06 * abs(uy), pole_h + 0.75), "metal_panel")
            m.box((cx - 0.10, cy - 0.10, pole_h - 0.80), (cx + 0.10, cy + 0.10, pole_h - 0.58), "paint_grey")   # RRU
        P._bar(m, K.Vector((0.0, 0.0, pole_h - 0.60)), K.Vector((ux * 0.95, uy * 0.95, pole_h + 0.02)), K.Vector((0.0, 0.0, 1.0)), 0.045, 0.030, P.GALV)
    m.box((-0.30, -0.30, 0.0), (0.30, 0.30, 0.16), "concrete")
    return m


@K.register("antenna_whip_mast", "antenna", anchor="ground_bottom_centre", nominal_size=(0.785, 0.889, 6.1),
            description="Guyed whip antenna mast: 6 m galvanised pole with three guy wires, an aviation obstruction light and a "
                        "roof-mounted base plate.",
            features=["cell_antennas"], budget=900)
def _whip():
    m = K.Mesh()
    h = 5.700
    m.cylinder((0.0, 0.0, 0.0), (0.0, 0.0, h), 0.045, P.GALV, segments=8)
    m.cylinder((0.0, 0.0, h), (0.0, 0.0, h + 0.28), 0.012, P.GALV, segments=6)
    m.lathe([(0.0, h + 0.40), (0.075, h + 0.32), (0.075, h + 0.28)], 8, "neon_red", caps=(False, True))
    for k in range(3):
        a = 2 * math.pi * k / 3
        P._bar(m, K.Vector((0.0, 0.0, h * 0.72)), K.Vector((0.45 * math.cos(a), 0.45 * math.sin(a), 0.10)),
               K.Vector((0.0, 0.0, 1.0)), 0.012, 0.012, P.GALV)
        m.box((0.45 * math.cos(a) - 0.055, 0.45 * math.sin(a) - 0.055, 0.0), (0.45 * math.cos(a) + 0.055, 0.45 * math.sin(a) + 0.055, 0.10), P.GALV)
    m.box((-0.22, -0.22, 0.0), (0.22, 0.22, 0.11), "concrete")
    return m


@K.register("antenna_satellite_dish_roof", "antenna", anchor="ground_bottom_centre", nominal_size=(1.24, 1.17, 1.61),
            description="1.2 m roof satellite dish on a non-penetrating ballasted frame with concrete blocks and a feed arm.",
            features=["cell_antennas"], budget=900)
def _roof_dish():
    m = K.Mesh()
    R, depth, cz = 0.600, 0.200, 1.000
    rings, spokes = 4, 14
    tilt = math.radians(28.0)

    def pt(ir, ia):
        r = R * ir / rings
        a = 2 * math.pi * ia / spokes
        u, v = r * math.cos(a), r * math.sin(a)
        dy = depth * (r / R) ** 2
        return (u, dy * math.cos(tilt) - v * math.sin(tilt), cz + v * math.cos(tilt) + dy * math.sin(tilt))

    for ir in range(rings):
        for ia in range(spokes):
            a0, a1 = ia, (ia + 1) % spokes
            if ir == 0:
                m.face([pt(0, 0), pt(1, a1), pt(1, a0)], "metal_panel", smooth=True)
            else:
                m.face([pt(ir, a0), pt(ir, a1), pt(ir + 1, a1), pt(ir + 1, a0)], "metal_panel", smooth=True)
    m.cylinder((0.0, 0.10, cz), (0.0, 0.42, cz - 0.16), 0.055, P.GALV, segments=8)
    m.cylinder((0.0, 0.42, cz - 0.16), (0.0, 0.42, 0.12), 0.048, P.GALV, segments=8)
    m.cylinder((0.0, -0.42, cz - 0.42), (0.0, -0.12, cz - 0.18), 0.032, "metal_panel", segments=8)
    m.box((-0.055, -0.48, cz - 0.53), (0.055, -0.36, cz - 0.40), "metal_panel")
    for s in (-1, 1):                                                          # ballast frame
        m.box((s * 0.42 - 0.045, -0.55, 0.0), (s * 0.42 + 0.045, 0.62, 0.09), P.GALV)
        for k in range(3):
            m.box((s * 0.42 - 0.20, -0.48 + k * 0.40, 0.09), (s * 0.42 + 0.20, -0.28 + k * 0.40, 0.20), "concrete")
    m.box((-0.46, 0.30, 0.09), (0.46, 0.50, 0.14), P.GALV)
    return m


@K.register("antenna_tv_yagi", "antenna", anchor="ground_bottom_centre", nominal_size=(0.9, 1.1, 2.812),
            description="Roof TV aerial: a Yagi array of eleven elements on a 2.6 m mast with a chimney-strap bracket "
                        "(the classic tenement rooftop silhouette).",
            features=["cell_antennas"], budget=900)
def _yagi():
    m = K.Mesh()
    mast = 2.600
    m.cylinder((0.0, 0.0, 0.0), (0.0, 0.0, mast), 0.020, P.GALV, segments=6)
    m.cylinder((0.0, -0.55, mast + 0.20), (0.0, 0.55, mast + 0.20), 0.014, P.GALV, segments=6)    # boom
    lens = [0.90, 0.86, 0.82, 0.78, 0.74, 0.70, 0.66, 0.62, 0.58, 0.54, 0.50]
    for k, L in enumerate(lens):
        y = -0.52 + k * 0.104
        m.cylinder((-L / 2, y, mast + 0.20), (L / 2, y, mast + 0.20), 0.008, P.GALV, segments=4)
    m.box((-0.075, -0.075, 0.0), (0.075, 0.075, 0.16), P.GALV)
    for s in (-1, 1):
        P._bar(m, K.Vector((0.0, 0.0, 0.70)), K.Vector((s * 0.30, 0.0, 0.05)), K.Vector((0.0, 1.0, 0.0)), 0.030, 0.010, P.GALV)
    return m


# --------------------------------------------------------------------------- billboards
@K.register("billboard_rooftop", "billboard", anchor="ground_bottom_centre", nominal_size=(14.95, 1.65, 8.62),
            description="Rooftop bulletin billboard: a 14.63 x 4.88 m (48 x 16 ft) vinyl face on a galvanised lattice frame, with "
                        "a service catwalk, ladder and eight top-mounted floodlights.",
            features=["billboard"], budget=2500)
def _billboard_roof():
    m = K.Mesh()
    W, H = 14.630, 4.880
    z0 = 3.000                       # bottom of the face above the roof deck
    z1 = z0 + H
    x0, x1 = -W / 2, W / 2
    m.box((x0, -0.030, z0), (x1, 0.030, z1), "metal_panel", faces="yY")                       # face
    m.box((x0 - 0.16, -0.09, z0 - 0.16), (x1 + 0.16, 0.09, z0), "metal_panel")                # bottom moulding
    m.box((x0 - 0.16, -0.09, z1), (x1 + 0.16, 0.09, z1 + 0.16), "metal_panel")
    for s in (-1, 1):
        m.box((s * (W / 2) - 0.08 * s, -0.09, z0 - 0.16), (s * (W / 2) + 0.08 * s, 0.09, z1 + 0.16), "metal_panel")
    posts = 6
    for k in range(posts):                                                                     # lattice legs
        x = x0 + W * (k + 0.5) / posts
        for dy in (-0.55, 0.55):
            m.box((x - 0.055, dy - 0.055, 0.0), (x + 0.055, dy + 0.055, z1), P.GALV)
        for zz in (0.9, 2.8, 4.8, 6.8):
            P._bar(m, K.Vector((x, -0.55, zz)), K.Vector((x, 0.55, zz)), K.Vector((1.0, 0.0, 0.0)), 0.050, 0.016, P.GALV)
        m.box((x - 0.20, -0.75, 0.0), (x + 0.20, 0.75, 0.10), "concrete")                      # ballast pad
    for k in range(posts - 1):                                                                  # horizontal bracing
        xa = x0 + W * (k + 0.5) / posts
        xb = x0 + W * (k + 1.5) / posts
        for zz in (1.6, 5.4):
            P._bar(m, K.Vector((xa, 0.55, zz)), K.Vector((xb, 0.55, zz)), K.Vector((0.0, 0.0, 1.0)), 0.050, 0.016, P.GALV)
        P._bar(m, K.Vector((xa, 0.55, 0.30)), K.Vector((xb, 0.55, 3.60)), K.Vector((0.0, 0.0, 1.0)), 0.045, 0.014, P.GALV)
        P._bar(m, K.Vector((xb, 0.55, 0.30)), K.Vector((xa, 0.55, 3.60)), K.Vector((0.0, 0.0, 1.0)), 0.045, 0.014, P.GALV)
    m.box((x0, 0.09, z0 - 0.90), (x1, 0.75, z0 - 0.84), P.GALV)                                 # catwalk deck
    P.railing(m, [(x0, 0.72, z0 - 0.84), (x1, 0.72, z0 - 0.84)], 1.05, P.GALV, pitch=0.55, rails=2)
    P.ladder(m, x1 - 0.9, 0.80, 0.0, z0 - 0.84, 0.406, P.GALV)
    for k in range(8):                                                                           # floodlights
        x = x0 + W * (k + 0.5) / 8
        m.cylinder((x, 0.06, z1 + 0.16), (x, 0.70, z1 + 0.60), 0.030, P.GALV, segments=6)
        m.lathe([(0.0, z1 + 0.60), (0.20, z1 + 0.74)], 8, "fluoro_white", center=(x, 0.70), caps=(False, True))
    return m


@K.register("billboard_wall_mounted", "billboard", nominal_size=(12.39, 1.13, 6.75),
            description="Wall-mounted bulletin: a 12.19 x 6.10 m (40 x 20 ft) face on standoff steel, with six gooseneck lights "
                        "(blank party wall advertising).",
            features=["billboard"], budget=2500)
def _billboard_wall():
    m = K.Mesh()
    W, H = 12.190, 6.100
    x0, x1 = -W / 2, W / 2
    m.box((x0, -0.42, 0.0), (x1, -0.36, H), "metal_panel", faces="yY")
    for e, (a, b) in enumerate(((x0 - 0.10, x0), (x1, x1 + 0.10))):
        m.box((a, -0.46, -0.10), (b, -0.32, H + 0.10), "metal_panel")
    m.box((x0 - 0.10, -0.46, H), (x1 + 0.10, -0.32, H + 0.10), "metal_panel")
    m.box((x0 - 0.10, -0.46, -0.10), (x1 + 0.10, -0.32, 0.0), "metal_panel")
    for k in range(7):                                                                            # standoff frame
        x = x0 + W * k / 6
        m.box((x - 0.045, -0.36, 0.10), (x + 0.045, 0.0, H - 0.10), P.GALV)
    for zz in (0.5, H / 2, H - 0.5):
        m.box((x0, -0.34, zz - 0.045), (x1, -0.24, zz + 0.045), P.GALV)
    for k in range(6):
        x = x0 + W * (k + 0.5) / 6
        m.cylinder((x, -0.42, H + 0.10), (x, -0.95, H + 0.42), 0.028, P.BLACK, segments=6)
        m.lathe([(0.0, H + 0.42), (0.18, H + 0.55)], 8, "fluoro_white", center=(x, -0.95), caps=(False, True))
    return m
