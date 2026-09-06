"""The Plaza Hotel — 768 Fifth Avenue at Grand Army Plaza (BIN 1035253, LP-0629, NHL). Henry J. Hardenbergh, 1907;
Warren & Wetmore 1921 Fifth Avenue addition.

Dimensions used (source in brackets)
------------------------------------
* Footprint [NYC Building Footprints, OTI 5zhs-2jue]: the real OTI polygon (5,444 m2), 90.8 m east-west by
  66.5 m north-south, with the light court notched out of the south-west corner.
* Height [LPC designation report LP-0629; AIA Guide]: 19 storeys, 250 ft = 76.2 m to the ridge of the mansard.
  Storey heights derived so the main cornice lands at 56.0 m: a three-storey rusticated marble base to 15.0 m, then
  13 storeys of 3.15 m; the mansard roof occupies the top three storeys, 20.2 m from cornice to ridge.
* Elevation [LP-0629]: white glazed brick above a Vermont-marble base, a French Renaissance chateau composition with
  a heavy modillioned copper cornice, balustraded balconies, and a green copper mansard with two orders of dormers,
  corner turrets and iron cresting.
* Frontages [AIA Guide to New York City]: Fifth Avenue is east (local +x) and Central Park South north (+y); the
  Grand Army Plaza corner carries the porte-cochere.

Fidelity: real footprint; 19 storeys, the 56.0 m cornice, the 76.2 m ridge, the marble base, the glazed-brick shaft
with punched windows, the copper cornice and the two-order dormered mansard with corner turrets are modelled as
geometry. Inferred (stated): the storey heights (derived from the published total and storey count) and the dormer
rhythm (regular, not measured). NOT modelled: the interiors (Palm Court, Grand Ballroom), the balcony ironwork
pattern, the Pulitzer Fountain and the plaza in front (other stages), and the roof plant.
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import c_common as cc  # noqa: E402
import common as C  # noqa: E402

ID = "c_the_plaza"
BIN = 1035253
RIDGE = 76.2
CORNICE = 56.0
BASE_TOP = 15.0


def build():
    C.reset()
    cc.materials(["white_brick", "marble_white", "copper_green", "glass_dark", "slate", "roof_dark", "granite_grey",
                  "cast_iron", "gold"])
    g = cc.Group(ID, angle_deg=cc.GRID_ANGLE)
    P = g.poly(BIN)
    objs: list = []
    coords = C.ring_coords(P)

    objs += cc.base_and_wall(f"{ID}_base", P, BASE_TOP, C.M.marble_white, recess=0.7, material_top=C.M.roof_dark)
    fl = [BASE_TOP + (CORNICE - BASE_TOP) * k / 13 for k in range(14)]
    fen = C.Fenestration(bay_w=3.2, window_frac=0.48, recess=0.42, spandrel_h=0.85, spandrel_proud=0.12,
                         pier="white_brick", spandrel="white_brick", glass="glass_dark", floor_z=fl, window_h=2.3)
    objs += C.tower_tier(f"{ID}_shaft", P, BASE_TOP, CORNICE, fen, roof_material="roof_dark", parapet_h=0.0)

    b = C.MeshBuilder()
    for p0, p1, L, t, n in C.edges_of(coords):
        if L < 6.0:
            continue
        nbay = max(2, int(round(L / 4.6)))
        mod = L / nbay
        for k in range(nbay):                       # marble base: arched ground floor, square 2nd/3rd floor windows
            a = p0 + t * (k * mod + 1.0)
            c = p0 + t * ((k + 1) * mod - 1.0)
            C.arched_opening(b, a, c, n, 1.7, 5.4, None, 0.6, C.M.marble_white, C.M.glass_dark)
            C.window_punch(b, a, c, n, 8.6, 11.4, 0.5, C.M.marble_white, C.M.glass_dark)
            C.window_punch(b, a, c, n, 12.2, 14.4, 0.5, C.M.marble_white, C.M.glass_dark)
        for z in (BASE_TOP, 27.0, 40.0):            # marble band courses in the brick shaft
            b.box_from_to(p0, p1, n, 0.3, z - 0.4, z, C.M.marble_white)
    e0, e1, L, t, n = C.edge_facing(coords, 0.0)    # Fifth Avenue porte-cochere
    mid = (e0 + e1) / 2
    b.box_from_to(mid - t * 7.0, mid + t * 7.0, n, 4.4, 5.6, 6.4, C.M.copper_green)
    for k in (-1, 1):
        q = mid + t * (k * 6.0)
        b.lathe([(0.3, 0.0), (0.24, 5.6)], 12, C.M.cast_iron, origin=(q[0] + n[0] * 4.0, q[1] + n[1] * 4.0, 0.0))
    objs.append(b.build(f"{ID}_base_detail"))
    objs.append(C.cornice(f"{ID}_cornice", P, CORNICE - 2.4,
                          [(0.5, 0.0), (2.0, 1.2), (2.0, 2.0), (0.6, 2.8)], C.M.copper_green))

    # ---- the copper mansard: two orders of dormers and corner turrets ---------------------------------------------
    b = C.MeshBuilder()
    ring = C.ring_coords(P)
    b.loft([[(x, y, CORNICE + 0.4) for x, y in ring],
            [(x, y, CORNICE + 15.0) for x, y in C.offset_ring(ring, -8.0)],
            [(x, y, RIDGE - 0.4) for x, y in C.offset_ring(ring, -22.0)],
            [(x, y, RIDGE) for x, y in C.offset_ring(ring, -23.0)]], C.M.copper_green,
           cap_top=True, cap_bottom=False, material_top=C.M.roof_grey)
    for p0, p1, L, t, n in C.edges_of(ring):
        for order, (z0, z1, w) in enumerate(((CORNICE + 1.2, CORNICE + 6.2, 2.0), (CORNICE + 7.4, CORNICE + 11.4, 1.6))):
            ndorm = max(1, int(round(L / (6.0 + 2.0 * order))))
            for k in range(ndorm):
                q = p0 + t * (L * (k + 0.5) / ndorm)
                inset = 0.0 if order == 0 else 2.6
                a = q - t * w - n * inset
                c = q + t * w - n * inset
                b.box_from_to(a, c, n, 1.1, z0, z1, C.M.copper_green, top=False)
                C.window_punch(b, a + t * 0.3, c - t * 0.3, n + n * 0.0, z0 + 0.6, z1 - 0.6, 0.3, C.M.copper_green,
                               C.M.glass_dark)
                b.hull([(a[0], a[1], z1), (c[0], c[1], z1),
                        (a[0] + n[0] * 1.1, a[1] + n[1] * 1.1, z1), (c[0] + n[0] * 1.1, c[1] + n[1] * 1.1, z1),
                        (q[0] - n[0] * inset, q[1] - n[1] * inset, z1 + 1.5)], C.M.copper_green)
    x0, y0, x1, y1 = P.bounds
    for cxy in ((x0 + 6.5, y1 - 6.5), (x1 - 6.5, y1 - 6.5), (x1 - 6.5, y0 + 6.5)):
        b.lathe([(4.6, 0.0), (4.6, 6.0), (4.2, 8.0), (2.6, 13.0), (1.0, 16.6), (0.0, 18.6)], 20,
                C.M.copper_green, origin=(cxy[0], cxy[1], CORNICE), smooth=True)
        b.lathe([(0.0, 0.0), (0.5, 0.5), (0.0, 1.6)], 10, C.M.gold, origin=(cxy[0], cxy[1], CORNICE + 18.6))
    objs.append(C.tag(b.build(f"{ID}_mansard"), "mass"))
    return objs, g


def main():
    objs, g = build()
    entry = cc.finish(objs, ID, g.frame, real_footprint=g.real_local,
                      fidelity_statement=(
                          "Exact: real OTI footprint; 19 storeys with the cornice at 56.0 m and the mansard ridge at "
                          "250 ft = 76.2 m (LP-0629); three-storey Vermont-marble base with arched ground-floor "
                          "openings; white glazed-brick shaft with punched windows and marble band courses; "
                          "modillioned copper cornice; two orders of dormers in a copper mansard with three corner "
                          "turrets; Fifth Avenue porte-cochere. Inferred (stated): storey heights derived from the "
                          "published total and storey count, and a regular dormer rhythm. Not modelled: interiors "
                          "(Palm Court, Grand Ballroom), balcony ironwork pattern, the Pulitzer Fountain and plaza, "
                          "roof plant."),
                      dimensions={"ridge_m": RIDGE, "cornice_m": CORNICE, "base_top_m": BASE_TOP, "floors": 19})
    cc.render(ID, [
        {"view": "grand_army_plaza", "azimuth_deg": 60, "elevation_deg": "street", "distance": 175, "fov_deg": 50, "look_up_deg": 20},
        {"view": "aerial", "azimuth_deg": 60, "elevation_deg": 28},
    ])
    return entry


if __name__ == "__main__":
    main()
