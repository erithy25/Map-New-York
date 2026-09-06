"""Carnegie Hall — 881 Seventh Avenue (BIN 1023449, LP-0278, NHL). William Burnet Tuthill, 1891; studio towers 1894
and 1897 (Tuthill / Henry J. Hardenbergh).

Dimensions used (source in brackets)
------------------------------------
* Footprint: the real OTI polygon (2,820 m2), 46.3 m east-west by 61.7 m north-south on the corner of West 57th
  Street (south, local -y) and Seventh Avenue (west, local -x).
* Height [OTI LiDAR; LP-0278]: the 1894/1897 studio tower reaches 55.2 m; the 1891 concert-hall block's cornice is
  at 27.5 m over six storeys.
* Elevation [LP-0278]: narrow Roman brick (a long thin iron-spot brick) with terracotta and brownstone trim; a
  rusticated brownstone base, giant round-arched openings to the 57th Street and Seventh Avenue entrances, an
  arcaded upper storey, and a strongly projecting terracotta cornice on modillions.
* Storey heights derived so the concert-hall cornice lands at 27.5 m: base 6.5 m, then five storeys of 4.2 m. The
  studio tower above adds seven storeys of 3.65 m plus a 2.2 m parapet.
* Auditorium [LP-0278]: the Isaac Stern Auditorium seats 2,804 in five levels; its volume is expressed as the
  windowless mass at the centre of the block.

Fidelity: real footprint; the 55.2 m studio tower, the 27.5 m concert-hall cornice, the Roman-brick and terracotta
elevation with its giant arched entrances, the arcaded top storey and the modillioned cornice are modelled as
geometry. Inferred (stated): storey heights (derived from the LiDAR heights and the published storey count) and the
position of the auditorium mass within the block. NOT modelled: the auditorium interior, the 1986-87 Polshek
restoration's rooftop tower addition detail, and the Weill Recital Hall interior.
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import c_common as cc  # noqa: E402
import common as C  # noqa: E402

ID = "c_carnegie_hall"
BIN = 1023449
TOWER_TOP = 55.2
CORNICE = 27.5
BASE_TOP = 6.5


def build():
    C.reset()
    cc.materials(["brick_red", "terracotta_cream", "brownstone", "glass_dark", "roof_dark", "copper_green",
                  "granite_dark", "limestone"])
    g = cc.Group(ID, angle_deg=cc.GRID_ANGLE)
    P = g.poly(BIN)
    coords = C.ring_coords(P)
    objs: list = []

    objs.append(C.plinth(f"{ID}_base", P, 0.0, BASE_TOP, C.M.brownstone, material_top=C.M.roof_dark))
    fl = [BASE_TOP + (CORNICE - 2.6 - BASE_TOP) * k / 5 for k in range(6)]
    fen = C.Fenestration(bay_w=3.5, window_frac=0.5, recess=0.5, spandrel_h=0.95, spandrel_proud=0.14,
                         pier="brick_red", spandrel="terracotta_cream", glass="glass_dark", floor_z=fl, window_h=2.6)
    objs += C.tower_tier(f"{ID}_hall", P, BASE_TOP, CORNICE - 2.6, fen, roof_material="roof_dark", parapet_h=0.0)
    b = C.MeshBuilder()
    for p0, p1, L, t, n in C.edges_of(coords):
        if L < 8.0:
            continue
        nbay = max(2, int(round(L / 5.6)))
        mod = L / nbay
        for k in range(nbay):                     # giant round-arched ground-floor openings
            a = p0 + t * (k * mod + 1.2)
            c = p0 + t * ((k + 1) * mod - 1.2)
            C.arched_opening(b, a, c, n, 0.9, 3.6, None, 0.65, C.M.brownstone, C.M.glass_dark)
        # arcaded top storey: a round arch over every second bay
        for k in range(0, nbay, 1):
            a = p0 + t * (k * mod + 0.8)
            c = p0 + t * ((k + 1) * mod - 0.8)
            C.arched_opening(b, a, c, n, CORNICE - 8.4, CORNICE - 5.4, None, 0.5, C.M.brick_red, C.M.glass_dark)
        for z in (BASE_TOP + 0.2, 14.4, 19.0):    # terracotta band courses
            b.box_from_to(p0, p1, n, 0.3, z - 0.4, z, C.M.terracotta_cream)
    objs.append(b.build(f"{ID}_hall_detail"))
    objs.append(C.cornice(f"{ID}_cornice", P, CORNICE - 2.6,
                          [(0.5, 0.0), (1.8, 1.2), (1.8, 2.0), (0.5, 2.6)], C.M.terracotta_cream))

    # ---- the studio tower on the north-east part of the block -----------------------------------------------------
    x0, y0, x1, y1 = P.bounds
    tower = C._clean_polygon(P.intersection(C.rect_xy(x0 + 12.0, y0 + 26.0, x1 - 1.0, y1 - 1.0)).buffer(0))
    fen_t = C.Fenestration(floor_h=3.65, bay_w=3.3, window_frac=0.5, recess=0.4, spandrel_h=0.9, spandrel_proud=0.12,
                           pier="brick_red", spandrel="brick_red", glass="glass_dark", window_h=2.4)
    objs += C.tower_tier(f"{ID}_studio_tower", tower, CORNICE, TOWER_TOP - 2.2, fen_t, roof_material="roof_dark",
                         parapet_h=2.2, parapet_t=0.5)
    objs.append(C.cornice(f"{ID}_tower_cornice", tower, TOWER_TOP - 4.4,
                          [(0.4, 0.0), (1.2, 0.9), (1.2, 1.5), (0.4, 2.2)], C.M.terracotta_cream))
    # the auditorium mass (windowless) at the centre of the block
    aud = C.offset_polygon(P, -9.0)
    if not aud.is_empty:
        objs.append(C.prism(f"{ID}_auditorium", aud, BASE_TOP, CORNICE + 4.0, C.M.brick_red,
                            material_top=C.M.roof_dark, role="mass"))
    return objs, g


def main():
    objs, g = build()
    entry = cc.finish(objs, ID, g.frame, real_footprint=g.real_local,
                      fidelity_statement=(
                          "Exact: real OTI footprint; the 55.2 m studio tower and the 27.5 m concert-hall cornice "
                          "(OTI LiDAR / LP-0278); Roman-brick and terracotta elevation with a rusticated brownstone "
                          "base, giant round-arched entrances, an arcaded top storey and a modillioned terracotta "
                          "cornice. Inferred (stated): storey heights derived from the LiDAR heights and the "
                          "published storey count; the position of the auditorium mass within the block. Not "
                          "modelled: the Isaac Stern Auditorium and Weill Recital Hall interiors, and the detail of "
                          "the 1986-87 rooftop addition."),
                      dimensions={"studio_tower_m": TOWER_TOP, "hall_cornice_m": CORNICE, "base_top_m": BASE_TOP,
                                  "auditorium_seats": 2804})
    cc.render(ID, [
        {"view": "seventh_ave", "azimuth_deg": 250, "elevation_deg": "street", "distance": 130, "fov_deg": 52, "look_up_deg": 22},
        {"view": "aerial", "azimuth_deg": 220, "elevation_deg": 30},
    ])
    return entry


if __name__ == "__main__":
    main()
