"""Flatiron (Fuller) Building — 175 Fifth Avenue (BIN 1016278, LP-00219). D. H. Burnham & Co., 1902.

Dimensions used (source in brackets)
------------------------------------
* Footprint: real OTI polygon, 1,025.2 m2 — the triangular Broadway / Fifth Avenue / East 22nd Street lot; 66.8 m on its
  long axis and 26.7 m across the 22nd Street base in the model's local frame, apex (the "prow") to the north. The
  published lot is 190 ft x 87 ft (57.9 x 26.5 m) [Wikipedia, LPC designation report LP-0219]; the extra length in the
  OTI polygon is the 1902 one-storey "cowcatcher" retail extension at the prow, which the model carries as a real part
  of the ground floor.
* Height [Wikipedia, LPC report LP-0219, Emporis]: 285 ft = 86.9 m to the top of the cornice; 22 storeys (the 1905
  rooftop penthouse, which the LiDAR roof height of 91.5 m includes, is *not* modelled — stated gap).
* Storeys [LPC report]: tripartite Beaux-Arts composition — rusticated limestone base of 4 storeys, terracotta shaft of
  storeys 5-20, two-storey capital and a heavy modillioned cornice. Storey heights derived from those fixed points:
  ground floor 6.0 m, storeys 2-4 at 4.2 m, storeys 5-22 at 3.66 m, cornice 84.5 -> 86.9 m.
* Materials [LPC report]: limestone at the base, glazed architectural terracotta above (Atlantic Terra Cotta), with
  undulating three-sided oriel bays on both long flanks and a rounded prow.

Fidelity: exact — real footprint including the prow extension, 86.9 m cornice height, 22 storeys, the tripartite
base/shaft/capital division, the oriel-bay rhythm on both flanks, the rounded prow. Inferred — per-storey heights
(derived from the two published fixed points, not published individually). Simplified — the terracotta ornament
(medallions, Greek faces, egg-and-dart) is carried as string courses and a modillioned cornice profile, not as modelled
relief; the cowcatcher is a plain glazed one-storey volume. Not modelled — the 1905 rooftop penthouse, interiors.
"""
from __future__ import annotations

import math
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import common as C  # noqa: E402

ID = "flatiron"
BINS = [1016278]
CORNICE_TOP_M = 86.9
GROUND_H = 6.0
BASE_STOREY_H = 4.2
SHAFT_STOREY_H = 3.66
CORNICE_H = 2.4


def storey_z() -> list[float]:
    """Floor lines 0..22 (0 = grade)."""
    z = [0.0, GROUND_H]
    for _ in range(3):
        z.append(z[-1] + BASE_STOREY_H)          # storeys 2-4
    for _ in range(18):
        z.append(z[-1] + SHAFT_STOREY_H)         # storeys 5-22
    return z


def build():
    C.reset()
    fp = C.load_footprint(ID)
    fr = C.local_frame(fp.polygon, fp.ground_z)
    P = fr.local_polygon(fp.polygon)
    minx, miny, maxx, maxy = P.bounds
    Z = storey_z()
    z4, z20, z22 = Z[4], Z[20], Z[22]
    objs = []
    lime, tc, tcr, glass = C.M.limestone_rusticated, C.M.terracotta_cream, C.M.terracotta_red, C.M.glass_dark

    # which end is the prow? compare the cross-axis extent of the two halves
    xm = (minx + maxx) / 2
    ext = {}
    for side, sel in (("lo", C.rect_xy(minx - 1, miny - 1, xm, maxy + 1)), ("hi", C.rect_xy(xm, miny - 1, maxx + 1, maxy + 1))):
        q = P.intersection(sel)
        ext[side] = (q.bounds[3] - q.bounds[1]) if not q.is_empty else 0.0
    prow_hi = ext["hi"] < ext["lo"]
    prow_x = maxx if prow_hi else minx

    # ---- base storeys 1-4 on the real footprint (IoU volume) ---------------------------------------------------
    objs.append(C.plinth(f"{ID}_base", P, 0.0, GROUND_H, lime, material_top=C.M.roof_grey))
    fen_base = C.Fenestration(bay_w=3.1, window_frac=0.5, recess=0.5, spandrel_h=1.1, pier="limestone_rusticated",
                              spandrel="limestone_rusticated", glass="glass_dark", floor_z=Z[1:5], window_h=2.6)
    objs.append(C.facade_grid(f"{ID}_base_skin", P, GROUND_H, z4, fen_base))
    objs.append(C.prism(f"{ID}_base_mass", P, GROUND_H, z4, lime, inset=0.52, material_top=C.M.roof_grey, role="mass"))
    objs.append(C.band(f"{ID}_belt4", P, z4, z4 + 0.55, 0.4, tc))

    # ---- shaft storeys 5-20 with the three-sided oriel bays on the two long flanks ------------------------------
    fen_shaft = C.Fenestration(bay_w=3.1, window_frac=0.52, recess=0.42, spandrel_h=1.0, pier="terracotta_cream",
                               spandrel="terracotta_red", glass="glass_dark", floor_z=Z[4:21], window_h=2.35)
    objs.append(C.facade_grid(f"{ID}_shaft_skin", P, z4, z20, fen_shaft))
    objs.append(C.prism(f"{ID}_shaft_mass", P, z4, z20, tc, inset=0.44, material_top=C.M.roof_grey, role="mass"))
    b = C.MeshBuilder()
    coords = C.ring_coords(P)
    # The OTI polygon states each flank as a run of short edges, so the bays are laid out along the whole wall run.
    runs = C.wall_runs(coords, 90.0, tol_deg=45.0, min_len=25.0) + C.wall_runs(coords, -90.0, tol_deg=45.0, min_len=25.0)
    for pts, L in runs:
        nbay = max(3, int(round(L / 8.4)))
        module = L / nbay
        proj = 1.05
        for k in range(nbay):
            a, t, n = C.polyline_at(pts, module * (k + 0.10))
            c, t2, n2 = C.polyline_at(pts, module * (k + 0.90))
            w = float(np.linalg.norm(c - a))
            am = a + t * w * 0.24 + n * proj
            cm = c - t2 * w * 0.24 + n2 * proj
            b.quad((a[0], a[1], z4), (am[0], am[1], z4), (am[0], am[1], z20), (a[0], a[1], z20), tc)
            b.quad((am[0], am[1], z4), (cm[0], cm[1], z4), (cm[0], cm[1], z20), (am[0], am[1], z20), glass)
            b.quad((cm[0], cm[1], z4), (c[0], c[1], z4), (c[0], c[1], z20), (cm[0], cm[1], z20), tc)
            for zf in Z[4:21]:
                b.box_from_to(am, cm, n, 0.14, zf, zf + 0.9, tcr, top=True, bottom=True)
                b.box_from_to(a, am, n, 0.14, zf, zf + 0.9, tcr, top=True, bottom=True)
                b.box_from_to(cm, c, n, 0.14, zf, zf + 0.9, tcr, top=True, bottom=True)
            b.face([b.vert(a[0], a[1], z20), b.vert(am[0], am[1], z20), b.vert(cm[0], cm[1], z20), b.vert(c[0], c[1], z20)], tc)
            b.face([b.vert(c[0], c[1], z4), b.vert(cm[0], cm[1], z4), b.vert(am[0], am[1], z4), b.vert(a[0], a[1], z4)], tc)
    objs.append(b.build(f"{ID}_oriels"))

    # ---- capital storeys 21-22 and the modillioned cornice -----------------------------------------------------
    fen_cap = C.Fenestration(bay_w=3.1, window_frac=0.46, recess=0.5, spandrel_h=0.9, pier="terracotta_cream",
                             spandrel="terracotta_cream", glass="glass_dark", floor_z=Z[20:23], window_h=2.2)
    objs.append(C.facade_grid(f"{ID}_cap_skin", P, z20, z22, fen_cap))
    objs.append(C.prism(f"{ID}_cap_mass", P, z20, z22, tc, inset=0.52, material_top=C.M.roof_dark, role="mass"))
    objs.append(C.cornice(f"{ID}_cornice", P, z22, [(0.35, 0.0), (1.45, 0.9), (1.75, 1.5), (1.55, CORNICE_H - 0.35),
                                                    (0.55, CORNICE_H)], tc))
    b = C.MeshBuilder()
    for p0, p1, L, t, n in C.edges_of(coords):          # modillion brackets under the corona
        k = max(2, int(round(L / 1.55)))
        for i in range(k):
            q = p0 + t * (L * (i + 0.5) / k)
            b.box((float(q[0] + n[0] * 0.85), float(q[1] + n[1] * 0.85), z22 + 0.55), (0.9, 0.32, 0.75), tc,
                  rot_deg=math.degrees(math.atan2(t[1], t[0])))
    # ---- the prow: a rounded nose and the one-storey "cowcatcher" ----------------------------------------------
    nose = C.rect_xy(prow_x - 6.0, miny - 1, prow_x + 1, maxy + 1).intersection(P)
    if not nose.is_empty and nose.area > 4:
        b.prism(C.ring_coords(nose if nose.geom_type == "Polygon" else max(nose.geoms, key=lambda g: g.area)),
                0.0, 5.4, C.M.glass_clear, cap_bottom=False, material_top=C.M.limestone)
    objs.append(b.build(f"{ID}_cornice_detail"))
    objs.append(C.prism(f"{ID}_roof", P, z22 - 0.3, z22 + 0.7, C.M.roof_dark))
    return objs, fr, fp


def main():
    objs, fr, fp = build()
    C.finish(objs, ID, BINS, fr, height_m=CORNICE_TOP_M, name="Flatiron Building", lp_number="LP-00219",
             height_source="Wikipedia / LPC LP-0219 / Emporis: 285 ft = 86.9 m to the top of the cornice, 22 storeys",
             fidelity_statement=(
                 "Exact: real triangular footprint including the prow extension, 86.9 m cornice height, 22 storeys, the "
                 "tripartite limestone-base / terracotta-shaft / two-storey-capital composition, the oriel-bay rhythm on "
                 "both flanks and the rounded prow. Inferred: per-storey heights (derived from the published overall height "
                 "and storey count). Simplified: terracotta ornament is carried as string courses, a modillioned cornice and "
                 "spandrel bands rather than modelled relief. Not modelled: the 1905 rooftop penthouse (which is why the "
                 "model stops at 86.9 m while the LiDAR roof height is 91.5 m), and all interiors."),
             notes="Height is to the top of the cornice; the LiDAR height_roof (91.5 m) includes the later penthouse",
             dimensions={"cornice_top_m": CORNICE_TOP_M, "storeys": 22, "ground_floor_h_m": GROUND_H,
                         "base_storey_h_m": BASE_STOREY_H, "shaft_storey_h_m": SHAFT_STOREY_H, "cornice_h_m": CORNICE_H,
                         "lot_long_axis_m": 66.8, "lot_base_width_m": 26.7, "published_lot_ft": [190, 87]})
    C.render_check(ID, [
        {"view": "street", "azimuth_deg": 190, "elevation_deg": "street", "distance": 138, "target_z": 38, "fov_deg": 60},
        {"view": "aerial", "azimuth_deg": 205, "elevation_deg": 17, "distance": 230, "fov_deg": 48, "target_z": 50},
    ])


if __name__ == "__main__":
    main()
