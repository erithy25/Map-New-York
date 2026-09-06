"""MetLife Building (Pan Am Building) — 200 Park Avenue (BIN 1085630). Emery Roth & Sons with Walter Gropius and
Pietro Belluschi, 1963.

Dimensions used (source in brackets)
------------------------------------
* Footprint: the real OTI polygon (10,073 m2) — the base straddles the Grand Central train shed between East 44th
  and 45th Streets; 91.0 m east-west by 113.5 m north-south in the local frame.
* Height [CTBUH]: 808 ft = 246.3 m, 59 floors. Storeys derived to land the roof on 246.3 m: a 9-storey base of
  4.90 m (top 44.1 m) and 50 tower floors of 4.044 m.
* Tower plan [Emery Roth & Sons; Gropius/Belluschi published plans]: an elongated octagon — a 78 x 40 m rectangle
  with 12 m corner chamfers — set with its broad faces north and south so the Park Avenue view up the axis sees the
  wide elevation. The chamfer dimension is measured from photographs (stated inference, +-1.5 m).
* Elevation [AIA Guide; LPC Grand Central area studies]: precast concrete panels with narrow vertical windows on a
  1.60 m module; the concrete piers read as continuous vertical ribs the full height of the shaft.
* Base [AIA Guide]: nine storeys wrapping over the Grand Central concourse, with the Park Avenue viaduct passing
  through it at 44th Street; the roof of the base carried the 1965-77 heliport.

Fidelity: real footprint; published height, floor count, octagonal tower plan and precast rib elevation modelled as
geometry. Inferred (stated): the corner chamfer dimension and the 9/50 floor split between base and tower. NOT
modelled: the Grand Central concourse below, the Park Avenue viaduct roadway through the base (it belongs to the
roads stage), the rooftop MetLife sign lettering, and the interiors.
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import c_common as cc  # noqa: E402
import common as C  # noqa: E402
from shapely.geometry import Polygon  # noqa: E402

ID = "c_metlife_building"
BIN = 1085630
ROOF_M = 246.3
BASE_FLOORS, BASE_FLOOR_H = 9, 4.90
BASE_TOP = BASE_FLOORS * BASE_FLOOR_H
TOWER_FLOORS = 50
FLOOR_H = (ROOF_M - BASE_TOP) / TOWER_FLOORS
PLAN_W, PLAN_D, CHAMFER = 78.0, 40.0, 12.0


def octagon(cx: float, cy: float, w: float, d: float, ch: float) -> Polygon:
    hw, hd = w / 2, d / 2
    return Polygon([(cx - hw + ch, cy - hd), (cx + hw - ch, cy - hd), (cx + hw, cy - hd + ch), (cx + hw, cy + hd - ch),
                    (cx + hw - ch, cy + hd), (cx - hw + ch, cy + hd), (cx - hw, cy + hd - ch), (cx - hw, cy - hd + ch)])


def build():
    C.reset()
    cc.materials(["concrete_dark", "concrete", "glass_dark", "roof_dark", "aluminium", "granite_dark"])
    g = cc.Group(ID, angle_deg=cc.GRID_ANGLE)
    P = g.poly(BIN)
    cx = (P.bounds[0] + P.bounds[2]) / 2
    cy = (P.bounds[1] + P.bounds[3]) / 2
    objs: list = []

    # ---- nine-storey base on the real footprint (IoU volume) ------------------------------------------------------
    fen_base = C.Fenestration(floor_h=BASE_FLOOR_H, bay_w=1.60, window_frac=0.44, recess=0.35, spandrel_h=1.20,
                              spandrel_proud=0.10, pier="concrete_dark", spandrel="concrete_dark", glass="glass_dark")
    objs.append(C.plinth(f"{ID}_ground", P, 0.0, 7.5, C.M.granite_dark, material_top=C.M.roof_dark))
    objs += C.tower_tier(f"{ID}_base", P, 7.5, BASE_TOP, fen_base, roof_material="roof_grey", parapet_h=1.4,
                         parapet_t=0.6)

    # ---- the octagonal tower ---------------------------------------------------------------------------------------
    tower = octagon(cx, cy, PLAN_W, PLAN_D, CHAMFER)
    fen = C.Fenestration(floor_h=FLOOR_H, bay_w=1.60, window_frac=0.42, recess=0.42, spandrel_h=1.25,
                         spandrel_proud=0.10, pier="concrete_dark", spandrel="concrete_dark", glass="glass_dark")
    objs += C.tower_tier(f"{ID}_tower", tower, BASE_TOP, ROOF_M - 5.2, fen, roof_material="roof_dark", parapet_h=0.0)
    # mechanical crown: two stepped precast bands
    objs.append(C.prism(f"{ID}_crown1", C.offset_polygon(tower, -1.2), ROOF_M - 5.2, ROOF_M - 1.8, C.M.concrete_dark,
                        material_top=C.M.roof_dark, role="mass"))
    objs.append(C.prism(f"{ID}_crown2", C.offset_polygon(tower, -8.0), ROOF_M - 1.8, ROOF_M, C.M.concrete_dark,
                        material_top=C.M.roof_dark, role="mass"))
    # the continuous vertical precast ribs
    b = C.MeshBuilder()
    for p0, p1, L, t, n in C.edges_of(C.ring_coords(tower)):
        nrib = max(1, int(round(L / 1.60)))
        for k in range(nrib + 1):
            q0 = p0 + t * min(L, k * (L / nrib)) - t * 0.16
            q1 = q0 + t * 0.32
            b.box_from_to(q0, q1, n, 0.30, BASE_TOP, ROOF_M - 5.2, C.M.concrete_dark)
    objs.append(b.build(f"{ID}_ribs"))
    return objs, g


def main():
    objs, g = build()
    entry = cc.finish(objs, ID, g.frame, real_footprint=g.real_local,
                      fidelity_statement=(
                          "Exact: real OTI footprint over the Grand Central train shed, 246.3 m / 59 floors (CTBUH), "
                          "elongated-octagon tower plan with the broad faces on the Park Avenue axis, precast "
                          "concrete rib elevation on a 1.60 m module. Inferred (stated): the 12 m corner chamfer "
                          "(+-1.5 m, from photographs) and the 9-storey base / 50-storey tower split. Not modelled: "
                          "the Grand Central concourse, the Park Avenue viaduct roadway through the base (roads "
                          "stage), the rooftop sign lettering, interiors."),
                      dimensions={"roof_m": ROOF_M, "floors": 59, "base_floors": BASE_FLOORS, "base_top_m": BASE_TOP,
                                  "tower_floors": TOWER_FLOORS, "floor_h_m": round(FLOOR_H, 3),
                                  "tower_plan_m": [PLAN_W, PLAN_D], "corner_chamfer_m": CHAMFER,
                                  "window_module_m": 1.60})
    cc.render(ID, [
        {"view": "park_ave_axis", "azimuth_deg": 209, "elevation_deg": "street", "distance": 260, "fov_deg": 45, "look_up_deg": 28},
        {"view": "aerial", "azimuth_deg": 200, "elevation_deg": 26},
    ])
    return entry


if __name__ == "__main__":
    main()
