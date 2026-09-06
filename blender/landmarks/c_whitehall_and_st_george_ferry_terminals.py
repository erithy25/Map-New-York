"""The two ends of the Staten Island Ferry, plus the Battery Maritime Building.
BINs 1085792 (Whitehall Terminal, Manhattan), 1000003 (Battery Maritime Building, LP-0102), 5141706 (St. George
Terminal, Staten Island). Frederic Schwartz Architects 2005 (Whitehall); Walker & Morris 1906-09 (Battery
Maritime); HOK 2005 (St. George).

Note on extent: the three buildings are the two ends of one ferry route, 6.0 km apart across Upper New York Bay.
They are exported in a single glb whose origin is the Whitehall Terminal; St. George therefore sits about 5.9 km
away in the model's local frame. This is deliberate (the brief groups them), and the ``origin_tm`` extras let the
engine place the whole node correctly.

Dimensions used (source in brackets)
------------------------------------
* Footprints: the three real OTI polygons (28,071 m2).
* Whitehall Terminal [Frederic Schwartz Architects; NYC DOT]: the waiting room's north wall is a **75 ft = 22.9 m**
  high glass wall facing the skyline; the OTI LiDAR height is **27.7 m** at the roof over the waiting room. The
  terminal handles 70,000 passengers a day through 4 slips.
* Battery Maritime Building [LPC designation report LP-0102]: a three-storey Beaux-Arts structure of **structural
  steel with a riveted cast- and sheet-metal facade painted green**, 21.6 m to the parapet (OTI LiDAR), with three
  ferry slips whose arched gantries stand 12.0 m above the water, giant Guastavino-tiled arches at the ground
  floor, and paired Corinthian colonnettes on the upper storeys.
* St. George Terminal [HOK 2005; NYC DOT]: 18.5 m (OTI LiDAR); a long glazed hall over the bus and rail concourse
  with a curved standing-seam roof and a 12.0 m high harbour-facing glass wall.
* Slips [NYC DOT]: the ferry slips are timber-pile racks 30 m long and 4.5 m above the water, three at Whitehall
  and three at Battery Maritime.

Fidelity: three real footprints; the 22.9 m Whitehall glass wall and its 27.7 m roof, the Battery Maritime
Building's painted-metal facade with its arched ground floor and paired colonnettes at 21.6 m, and the St. George
Terminal's 18.5 m curved-roofed glazed hall are modelled as geometry, together with the ferry slips' pile racks.
Inferred (stated): the storey heights, the slip positions (placed on the water-facing edges of each polygon) and
the roof curvature of St. George (from photographs). NOT modelled: the interiors, the ferry boats, the elevated
FDR Drive ramp over Whitehall, and the Battery Maritime Building's Guastavino tile pattern.
"""
from __future__ import annotations

import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import c_common as cc  # noqa: E402
import common as C  # noqa: E402

ID = "c_whitehall_and_st_george_ferry_terminals"
B_WHITEHALL, B_BMB, B_ST_GEORGE = 1085792, 1000003, 5141706
WHITEHALL_TOP, WHITEHALL_GLASS = 27.7, 22.9
BMB_TOP = 21.6
ST_GEORGE_TOP = 18.5
SLIP_L, SLIP_Z = 30.0, 4.5


def build():
    C.reset()
    cc.materials(["glass_clear", "glass_blue", "steel_dark", "steel_nirosta", "concrete", "concrete_dark",
                  "copper_green", "granite_grey", "roof_grey", "roof_dark",
                  "wood_dark", "aluminium", "limestone"])
    g = cc.Group(ID, angle_deg=cc.GRID_ANGLE, origin_bin=B_WHITEHALL)
    Pw, Pb, Ps = g.poly(B_WHITEHALL), g.poly(B_BMB), g.poly(B_ST_GEORGE)
    objs: list = []

    # ---- Whitehall Terminal ---------------------------------------------------------------------------------------
    objs.append(C.plinth(f"{ID}_whitehall_base", Pw, 0.0, 6.5, C.M.concrete, material_top=C.M.roof_dark))
    objs.append(C.tag(C.prism(f"{ID}_whitehall_hall", C.offset_polygon(Pw, -1.0), 6.5, WHITEHALL_TOP - 1.2,
                              C.M.glass_blue, material_top=C.M.roof_grey), "mass"))
    b = C.MeshBuilder()
    coords = C.ring_coords(Pw)
    p0, p1, L, t, n = C.edge_facing(coords, 90.0)                 # the north (skyline) glass wall
    b.box_from_to(p0, p1, n, 0.5, 0.0, WHITEHALL_GLASS, C.M.glass_clear)
    ncol = max(2, int(round(L / 4.2)))
    for k in range(ncol + 1):
        q = p0 + t * min(L, k * (L / ncol))
        b.box((q[0] + n[0] * 0.6, q[1] + n[1] * 0.6, WHITEHALL_GLASS / 2), (0.3, 0.7, WHITEHALL_GLASS),
              C.M.steel_nirosta, rot_deg=math.degrees(math.atan2(t[1], t[0])))
    for pa, pb, LL, tt, nn in C.edges_of(coords):                 # the roof fascia
        b.box_from_to(pa, pb, nn, 1.4, WHITEHALL_TOP - 1.2, WHITEHALL_TOP, C.M.aluminium)
    p0s, p1s, Ls, ts, ns = C.edge_facing(coords, -90.0)           # the three slips on the harbour side
    for k in range(3):
        q = p0s + ts * (Ls * (k + 0.5) / 3)
        for du in (-6.0, 6.0):
            r = q + ts * du
            b.box((r[0] + ns[0] * SLIP_L / 2, r[1] + ns[1] * SLIP_L / 2, SLIP_Z / 2), (2.0, SLIP_L, SLIP_Z),
                  C.M.wood_dark, rot_deg=math.degrees(math.atan2(ts[1], ts[0])))
    objs.append(b.build(f"{ID}_whitehall"))

    # ---- Battery Maritime Building --------------------------------------------------------------------------------
    objs.append(C.plinth(f"{ID}_bmb_base", Pb, 0.0, 8.0, C.M.copper_green, material_top=C.M.roof_dark))
    fen = C.Fenestration(floor_h=(BMB_TOP - 2.0 - 8.0) / 2, bay_w=4.0, window_frac=0.6, recess=0.45,
                         spandrel_h=1.0, spandrel_proud=0.14, pier="copper_green", spandrel="copper_green",
                         glass="glass_dark", window_h=3.4)
    objs += C.tower_tier(f"{ID}_bmb", Pb, 8.0, BMB_TOP - 2.0, fen, roof_material="roof_dark", parapet_h=2.0,
                         parapet_t=0.5)
    b = C.MeshBuilder()
    bc = C.ring_coords(Pb)
    for pa, pb_, LL, tt, nn in C.edges_of(bc):
        if LL < 8.0:
            continue
        nbay = max(1, int(round(LL / 8.0)))
        for k in range(nbay):                                     # the giant arched ground floor
            a = pa + tt * (k * (LL / nbay) + 1.2)
            c = pa + tt * ((k + 1) * (LL / nbay) - 1.2)
            C.arched_opening(b, a, c, nn, 1.0, 5.0, None, 0.8, C.M.copper_green, C.M.glass_dark)
        for k in range(nbay + 1):                                 # paired Corinthian colonnettes above
            for dd in (-0.6, 0.6):
                q = pa + tt * (min(LL, k * (LL / nbay)) + dd) + nn * 0.5
                C.column(b, q[0], q[1], 8.0, BMB_TOP - 4.5 - 8.0, 0.30, C.M.copper_green, order="corinthian",
                         segments=10, abacus=False)
    p0b, p1b, Lb, tb, nb_ = C.edge_facing(bc, -90.0)              # the three slips and their arched gantries
    for k in range(3):
        q = p0b + tb * (Lb * (k + 0.5) / 3)
        for du in (-7.0, 7.0):
            r = q + tb * du
            b.box((r[0] + nb_[0] * SLIP_L / 2, r[1] + nb_[1] * SLIP_L / 2, SLIP_Z / 2), (2.2, SLIP_L, SLIP_Z),
                  C.M.wood_dark, rot_deg=math.degrees(math.atan2(tb[1], tb[0])))
        C.arched_opening(b, q - tb * 7.0, q + tb * 7.0, nb_, 4.0, 12.0 - 7.0, 7.0, 1.2, C.M.copper_green,
                         C.M.glass_dark)
    objs.append(b.build(f"{ID}_bmb_detail"))

    # ---- St. George Terminal ---------------------------------------------------------------------------------------
    objs.append(C.plinth(f"{ID}_st_george_base", Ps, 0.0, 6.0, C.M.concrete, material_top=C.M.roof_dark))
    b = C.MeshBuilder()
    sx0, sy0, sx1, sy1 = Ps.bounds
    ring = C.ring_coords(Ps)
    b.prism(ring, 6.0, 12.0, C.M.glass_clear, cap_top=False, cap_bottom=False)
    nrib = 18
    for k in range(nrib + 1):
        x = sx0 + (sx1 - sx0) * k / nrib
        prof = [(sy0 + (sy1 - sy0) * j / 10,
                 12.0 + (ST_GEORGE_TOP - 12.0) * math.sin(math.pi * (j / 10)) ** 0.8) for j in range(11)]
        for j in range(10):
            (ya, za), (yb, zb) = prof[j], prof[j + 1]
            b.hull([(x - 0.2, ya, za), (x + 0.2, ya, za), (x - 0.2, yb, zb), (x + 0.2, yb, zb),
                    (x - 0.2, ya, za - 0.5), (x + 0.2, yb, zb - 0.5)], C.M.steel_nirosta)
        if k < nrib:
            xn = sx0 + (sx1 - sx0) * (k + 1) / nrib
            for j in range(10):
                (ya, za), (yb, zb) = prof[j], prof[j + 1]
                b.quad((x, ya, za), (xn, ya, za), (xn, yb, zb), (x, yb, zb), C.M.aluminium)
    p0g, p1g, Lg, tg, ng = C.edge_facing(ring, 0.0)
    b.box_from_to(p0g, p1g, ng, 0.5, 6.0, 12.0, C.M.glass_clear)
    objs.append(C.tag(b.build(f"{ID}_st_george"), "mass"))
    return objs, g, {
        "manhattan": [o for o in objs if o is not None and ("whitehall" in o.name or "bmb" in o.name)],
        "st_george": [o for o in objs if o is not None and "st_george" in o.name],
    }


def main():
    objs, g, groups = build()
    entry = cc.finish(objs, ID, g.frame, real_footprint=g.real_local,
                      fidelity_statement=(
                          "Exact: three real OTI footprints; Whitehall Terminal's 75 ft = 22.9 m north glass wall "
                          "and 27.7 m roof (OTI LiDAR); the Battery Maritime Building's painted-metal Beaux-Arts "
                          "facade at 21.6 m with giant arched ground-floor openings, paired Corinthian colonnettes "
                          "and three arched slip gantries at 12.0 m; St. George Terminal's 18.5 m curved "
                          "standing-seam roof over a glazed hall; the timber slip racks. Inferred (stated): the "
                          "storey heights, the slip positions (on the water-facing edge of each polygon) and the "
                          "St. George roof curvature (from photographs). Not modelled: interiors, the ferries, the "
                          "FDR Drive ramp over Whitehall, the Guastavino tile pattern. Extent note: the three "
                          "buildings are 6.0 km apart across Upper New York Bay and share one glb whose origin is "
                          "the Whitehall Terminal."),
                      dimensions={"whitehall_top_m": WHITEHALL_TOP, "whitehall_glass_wall_m": WHITEHALL_GLASS,
                                  "battery_maritime_top_m": BMB_TOP, "st_george_top_m": ST_GEORGE_TOP,
                                  "slip_length_m": SLIP_L, "slip_deck_z_m": SLIP_Z})
    # The two ends of the route are 6.0 km apart, so framing on the whole group put the camera 13 km out and both
    # terminals became sub-pixel — a uniform grey frame. Each end is now framed on its own objects, and each frame
    # is aimed at the thing it has to prove: Whitehall's 22.9 m north glass hall, the Battery Maritime Building's
    # arched slip gantries, and St. George's curved standing-seam roof.
    cc.render(ID, [{"view": "whitehall_glass_hall", "azimuth_deg": 15, "elevation_deg": 16, "distance": 210,
                    "fov_deg": 48, "target_z": 15.0},
                   {"view": "whitehall_slips", "azimuth_deg": 190, "elevation_deg": 12, "distance": 260,
                    "fov_deg": 48, "target_z": 12.0}],
              objects=groups["manhattan"])
    cc.render(ID, [{"view": "st_george_harbour", "azimuth_deg": 200, "elevation_deg": 14, "distance": 300,
                    "fov_deg": 48, "target_z": 11.0},
                   {"view": "st_george_aerial", "azimuth_deg": 230, "elevation_deg": 30}],
              objects=groups["st_george"])
    return entry


if __name__ == "__main__":
    main()
