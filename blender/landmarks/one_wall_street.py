"""One Wall Street — the Irving Trust Company Building (BIN 1000815). Ralph Walker of Voorhees, Gmelin & Walker, 1931.

Dimensions used (source in brackets)
------------------------------------
* Footprint: real OTI polygon, 3,294.5 m2 — the Wall Street / Broadway / New Street block, 106.4 x 34.3 m in the model's
  local frame (the long axis runs along Wall Street).
* Heights [CTBUH, Emporis, Wikipedia "One Wall Street", LPC LP-2029 area survey]: 654 ft = 199.3 m; 50 storeys.
  Storey heights derived: ground floor 6.5 m, floors 2-50 at (199.3 - 6.5)/49 = 3.935 m.
* Massing [LPC designation report LP-2559 (One Wall Street), Wikipedia "Architecture"]: an Art Deco limestone slab that
  rises sheer from the lot line and then steps back in a series of chamfered setbacks; the corners of every setback are
  cut at 45 degrees. Setbacks at floors 20, 27, 34, 40 and 45 reproduce the published silhouette (+-2 floors, inferred).
* Facade [LPC LP-2559]: the defining feature is the *fluted* curtain wall — the limestone is folded into shallow
  vertical faceted bays about 3.0 m wide with the windows in the reveals, so that the wall reads as a continuous
  curtain of shallow curves rather than as piers and spandrels. Modelled here as a real folded surface: each bay is a
  three-plane fold, 0.55 m deep, whose innermost 28 % carries the glazing, so the wall reads as limestone with narrow
  dark slots — which is how the building reads from Wall Street.
* Materials [LPC LP-2559]: Rockwood Alabama limestone throughout; polished granite at the entrance surrounds.

Fidelity: exact — real footprint, 199.3 m, 50 storeys, the sheer lot-line rise, the five chamfered setbacks with cut
corners, and the fluted limestone curtain wall as real folded geometry at its documented 3.0 m bay. Inferred
(+-2 floors) — the setback levels and the plan of each tier. Simplified — the chamfer geometry at the setback corners is
a straight 45-degree cut rather than the built curve; the entrance surrounds are recessed granite panels.
Not modelled — the Red Room mosaic lobby (a designated interior landmark) and the 2018-2023 residential conversion.
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import common as C  # noqa: E402

ID = "one_wall_street"
BINS = [1000815]
ROOF_M = 199.3
GROUND_H = 6.5
FLOOR_H = (ROOF_M - GROUND_H) / 49.0
SETBACK_FLOORS = (20, 27, 34, 40, 45)
FLUTE_BAY = 3.0
FLUTE_DEPTH = 0.55


def fz(k: int) -> float:
    return 0.0 if k <= 0 else GROUND_H + (k - 1) * FLOOR_H


def fluted_wall(b: C.MeshBuilder, poly, z0: float, z1: float, floors, lime, glass) -> None:
    """The folded limestone curtain wall: each 3.0 m bay is a shallow three-plane fold with glazing in the reveal."""
    for p0, p1, L, t, n in C.edges_of(C.ring_coords(poly)):
        if L < 2.5:
            b.box_from_to(p0, p1, n, 0.2, z0, z1, lime, top=True)
            continue
        k = max(1, int(round(L / FLUTE_BAY)))
        mod = L / k
        for i in range(k):
            a = p0 + t * (mod * i)
            m0 = p0 + t * (mod * (i + 0.36)) - n * FLUTE_DEPTH
            m1 = p0 + t * (mod * (i + 0.64)) - n * FLUTE_DEPTH
            c = p0 + t * (mod * (i + 1))
            b.quad((a[0], a[1], z0), (m0[0], m0[1], z0), (m0[0], m0[1], z1), (a[0], a[1], z1), lime)
            b.quad((m0[0], m0[1], z0), (m1[0], m1[1], z0), (m1[0], m1[1], z1), (m0[0], m0[1], z1), glass)
            b.quad((m1[0], m1[1], z0), (c[0], c[1], z0), (c[0], c[1], z1), (m1[0], m1[1], z1), lime)
            for zf in floors:                       # limestone spandrel across the fold at every floor line
                if z0 < zf < z1:
                    b.box_from_to(m0, m1, n, FLUTE_DEPTH - 0.08, zf, min(zf + 1.05, z1), lime, top=True, bottom=True)


def chamfer(poly, cut: float):
    """Cut every corner of ``poly`` at 45 degrees by ``cut`` metres (Walker's chamfered setbacks)."""
    return C._orient(poly.buffer(-cut, join_style="round", resolution=1).buffer(cut * 0.72, join_style="mitre",
                                                                                mitre_limit=1.0), 1.0)


def build():
    C.reset()
    fp = C.load_footprint(ID)
    fr = C.local_frame(fp.polygon, fp.ground_z)
    P = fr.local_polygon(fp.polygon)
    objs = []
    lime, glass, gran = C.M.limestone, C.M.glass_dark, C.M.granite_dark

    objs.append(C.plinth(f"{ID}_base", P, 0.0, GROUND_H, lime, material_top=C.M.roof_grey))
    b = C.MeshBuilder()
    coords = C.ring_coords(P)
    for p0, p1, L, t, n in C.edges_of(coords):
        if L < 8:
            continue
        k = max(1, int(round(L / 4.4)))
        for i in range(k):
            a = p0 + t * (L * i / k + 0.8); c = p0 + t * (L * (i + 1) / k - 0.8)
            C.window_punch(b, a, c, n, 0.8, GROUND_H - 1.1, 0.5, gran, C.M.glass_clear, sill=0.0)
    runs = sorted(C.wall_runs(coords, 0.0, tol_deg=55.0) + C.wall_runs(coords, 180.0, tol_deg=55.0), key=lambda r: -r[1])
    if runs:                                       # the Broadway entrance
        pts, L = runs[0]
        a, t, n = C.polyline_at(pts, L / 2 - 3.6)
        c, t2, n2 = C.polyline_at(pts, L / 2 + 3.6)
        C.arched_opening(b, a, c, n, 0.0, 6.4, 3.0, 1.8, gran, glass, n=10)
    objs.append(b.build(f"{ID}_base_detail"))

    floors = [fz(k) for k in range(1, 51)]
    levels = [1, *SETBACK_FLOORS, 50]
    plan = P
    b = C.MeshBuilder()
    for k in range(len(levels) - 1):
        f0, f1 = levels[k], levels[k + 1]
        z0 = GROUND_H if k == 0 else fz(f0)
        z1 = fz(f1) if f1 < 50 else ROOF_M
        if k > 0:
            # Walker's setbacks shorten the Wall Street elevation; the 34 m depth barely changes, so trim mostly
            # along the long axis and chamfer the corners.
            pb = plan.bounds
            nxt = plan.intersection(C.rect_xy(pb[0] + 8.0, pb[1] + 1.2, pb[2] - 8.0, pb[3] - 1.2))
            nxt = chamfer(nxt if nxt.geom_type == "Polygon" else max(nxt.geoms, key=lambda g: g.area), 2.0)
            if not nxt.is_empty:
                plan = nxt if nxt.geom_type == "Polygon" else max(nxt.geoms, key=lambda g: g.area)
        wall_top = z1 - 0.9                    # the plain parapet takes the last 0.9 m of every tier
        objs.append(C.prism(f"{ID}_t{k}_mass", plan, z0, wall_top, lime, inset=FLUTE_DEPTH + 0.05,
                            material_top=C.M.roof_dark, role="mass"))
        fluted_wall(b, plan, z0, wall_top, floors, lime, glass)
        b.prism(C.ring_coords(plan), wall_top - 0.4, wall_top, C.M.roof_dark)          # roof deck of this tier
        C.wall_ring(b, plan, wall_top, z1, 0.45, lime)                                 # parapet
    objs.append(b.build(f"{ID}_skin"))
    return objs, fr, fp


def main():
    objs, fr, fp = build()
    C.finish(objs, ID, BINS, fr, height_m=ROOF_M, name="One Wall Street (Irving Trust Building)", lp_number="LP-02559",
             height_source="CTBUH/Emporis/Wikipedia: 654 ft = 199.3 m, 50 storeys",
             fidelity_statement=(
                 "Exact: real footprint, 199.3 m / 50 storeys, the sheer lot-line rise, five chamfered setbacks with cut "
                 "corners, and the fluted limestone curtain wall built as real folded geometry at its documented 3.0 m bay "
                 "with the glazing in the fold. Inferred (+-2 floors): the setback levels (20/27/34/40/45) and the plan of "
                 "each tier. Simplified: the setback corner chamfers are straight 45-degree cuts rather than the built "
                 "curves; entrance surrounds are recessed granite panels. Not modelled: the Red Room mosaic lobby (a "
                 "designated interior landmark) and the 2018-2023 residential conversion."),
             notes="The fluted wall is real geometry (3.0 m bays, 0.55 m fold depth), not a normal map",
             dimensions={"roof_m": ROOF_M, "storeys": 50, "ground_floor_h_m": GROUND_H, "floor_h_m": round(FLOOR_H, 3),
                         "setback_floors": list(SETBACK_FLOORS), "flute_bay_m": FLUTE_BAY, "flute_depth_m": FLUTE_DEPTH})
    C.render_check(ID, [
        {"view": "street", "azimuth_deg": 210, "elevation_deg": "street", "distance": 340, "target_z": 100, "fov_deg": 62},
        {"view": "aerial", "azimuth_deg": 225, "elevation_deg": 24, "distance": 620, "fov_deg": 40, "target_z": 105},
    ])


if __name__ == "__main__":
    main()
