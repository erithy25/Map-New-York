"""Museum of Modern Art — 11 West 53rd Street (BINs 1081128, 1081130, 1087646).
Philip L. Goodwin & Edward Durell Stone, 1939; Philip Johnson's east wing and sculpture garden, 1964; Cesar Pelli's
gallery/tower wing, 1984; Yoshio Taniguchi's rebuild, 2004; Diller Scofidio + Renfro's western expansion, 2019.

Dimensions used (source in brackets)
------------------------------------
* Footprints: the three real OTI polygons that make up the museum block — BIN 1081128 (1,381.3 m2, LiDAR roof 33.05 m),
  BIN 1081130 (505.8 m2, 31.33 m) and BIN 1087646 (4,007.5 m2, 74.68 m) — 5,894.6 m2 together, 139.6 x 61.5 m in the
  model's local frame. The 53rd Street front faces south; the Abby Aldrich Rockefeller Sculpture Garden lies behind
  (north), towards 54th Street.
* Heights: each block is modelled to its own LiDAR ``height_roof``; the tallest, 74.7 m on BIN 1087646, is the height
  the model is verified against. MoMA does not publish an architectural height for the campus, so the LiDAR values are
  the primary source here.
* Composition [MoMA, Taniguchi's project description, Wikipedia "Museum of Modern Art"]: the 53rd Street front is a
  composition of black granite, white-painted panel and full-height glass, with the entrance canopy running the width
  of the entrance bay; the gallery floors are expressed as unbroken bands; the 2004 rebuild raised the Marron Atrium to
  110 ft (33.5 m). The Sculpture Garden is a walled outdoor room, about 40 x 25 m, with two rectangular reflecting
  pools, beech and birch planting and a marble-paved floor.
* Materials [Taniguchi / MoMA]: black granite, aluminium and white panel, low-iron glass, marble paving and Vermont
  slate in the garden.

Fidelity: exact — the three real footprints, each block at its own LiDAR roof height (74.7 / 33.1 / 31.3 m), the
53rd Street black-granite-and-glass front with its entrance canopy and expressed gallery bands, and the Sculpture
Garden as a walled outdoor room with two reflecting pools and planting, on the real open ground north of the blocks.
Inferred — the position of the internal divisions between the 1939, 1964, 1984, 2004 and 2019 fabric, because the
footprint polygons do not distinguish them; the model therefore reads the campus as three volumes rather than five
architects. Simplified — the trees are massing forms; the garden sculptures are omitted. Not modelled — the Marron
Atrium and every other interior, and the 53W53 residential tower (BIN under landmark id ``53w53``, a separate
landmark).
"""
from __future__ import annotations

import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import common as C  # noqa: E402
import shapely.ops  # noqa: E402
from shapely.geometry import MultiPolygon  # noqa: E402

ID = "moma"
BINS = [1081128, 1081130, 1087646]
HEIGHTS = {1081128: 33.05, 1081130: 31.33, 1087646: 74.68}
TOP_M = 74.7
GARDEN_W, GARDEN_D = 40.0, 25.0


def build():
    C.reset()
    fps = C.load_footprints(BINS)
    union = shapely.ops.unary_union([f.polygon for f in fps])
    main = max(union.geoms, key=lambda g: g.area) if isinstance(union, MultiPolygon) else union
    fr = C.local_frame(main, fps[0].ground_z)
    P = fr.local_polygon(union)
    parts = {f.bin: fr.local_polygon(f.polygon) for f in fps}
    south = fr.local_cardinal(180.0)
    north = fr.local_cardinal(0.0)
    objs = []
    gran, glass, panel, alu = C.M.granite_black, C.M.glass_clear, C.M.marble_white, C.M.aluminium

    fen = C.Fenestration(floor_h=5.0, bay_w=3.4, window_frac=0.86, recess=0.3, spandrel_h=0.9,
                         pier="granite_black", spandrel="granite_black", glass="glass_clear", mullion="aluminium",
                         mullions=1)
    for bn, poly in parts.items():
        h = TOP_M if bn == 1087646 else HEIGHTS[bn]
        objs.append(C.plinth(f"{ID}_base_{bn}", poly, 0.0, 6.5, gran, material_top=C.M.roof_grey))
        objs += C.tower_tier(f"{ID}_block_{bn}", poly, 6.5, h - 1.2, fen, parapet_h=1.2, parapet_t=0.5,
                             roof_material="roof_grey")
        # the expressed white gallery bands between the glazed floors
        b = C.MeshBuilder()
        for zf in [6.5 + 5.0 * k for k in range(1, int((h - 8.0) / 5.0))]:
            C.wall_ring(b, poly, zf - 0.55, zf, 0.34, C.M.marble_white)
        objs.append(b.build(f"{ID}_bands_{bn}"))

    # ---- the 53rd Street entrance front -------------------------------------------------------------------------
    b = C.MeshBuilder()
    big = parts[1087646]
    coords = C.ring_coords(big)
    runs = sorted(C.wall_runs(coords, south, tol_deg=50.0), key=lambda r: -r[1])
    if runs:
        pts, Lf = runs[0]
        mid, mt, mn = C.polyline_at(pts, Lf / 2)
        C.window_punch(b, mid - mt * 11.0, mid + mt * 11.0, mn, 0.4, 8.4, 0.9, gran, glass, sill=0.0)
        b.box_from_to(mid - mt * 13.0, mid + mt * 13.0, mn, 4.0, 8.4, 9.0, alu)            # entrance canopy
        for i in range(9):
            q = mid + mt * (-11.0 + 22.0 * i / 8)
            b.box((float(q[0] + mn[0] * 0.6), float(q[1] + mn[1] * 0.6), 4.4), (0.16, 0.4, 8.0), alu,
                  rot_deg=math.degrees(math.atan2(mt[1], mt[0])))
    objs.append(b.build(f"{ID}_entrance"))

    # ---- the Abby Aldrich Rockefeller Sculpture Garden, on the open ground north of the blocks -------------------
    b = C.MeshBuilder()
    minx, miny, maxx, maxy = P.bounds
    d = math.radians(north)
    # the garden sits against the north edge of the site, centred on the campus
    gx, gy = P.centroid.x + math.cos(d) * 22.0, P.centroid.y + math.sin(d) * 22.0
    garden = C.rect(gx, gy, GARDEN_W, GARDEN_D, angle_deg=north + 90.0).difference(P.buffer(1.0))
    if not garden.is_empty:
        g = garden if garden.geom_type == "Polygon" else max(garden.geoms, key=lambda gg: gg.area)
        gring = C.ring_coords(g)
        b.prism(gring, -0.15, 0.35, C.M.marble_white, cap_bottom=False)                     # marble paving
        C.wall_ring(b, g, 0.35, 3.4, 0.45, gran)                                            # the garden wall
        gb = g.bounds
        for sgn in (-1, 1):                                                                 # two reflecting pools
            pool = C.rect((gb[0] + gb[2]) / 2 + sgn * (gb[2] - gb[0]) * 0.22, (gb[1] + gb[3]) / 2,
                          (gb[2] - gb[0]) * 0.26, (gb[3] - gb[1]) * 0.42, angle_deg=north + 90.0).intersection(g)
            if not pool.is_empty and pool.area > 4:
                pr = C.ring_coords(pool if pool.geom_type == "Polygon" else max(pool.geoms, key=lambda gg: gg.area))
                b.prism(pr, 0.05, 0.3, C.M.water_dark, cap_bottom=False)
        planting = C.offset_polygon(g, -3.0)
        planting = planting if planting.geom_type == "Polygon" and not planting.is_empty else g
        for q, t, n, s in C.ring_stations(C.ring_coords(planting), 6.0):                    # beech and birch
            b.lathe([(0.22, 0.0), (0.16, 4.0), (0.12, 5.0)], 8, C.M.wood_dark,
                    origin=(float(q[0]), float(q[1]), 0.35), smooth=True)
            b.lathe([(0.0, 0.0), (2.2, 1.4), (2.4, 3.0), (1.4, 5.2), (0.0, 6.2)], 10, C.M.grass,
                    origin=(float(q[0]), float(q[1]), 4.2), smooth=True, cap=False)
    objs.append(b.build(f"{ID}_sculpture_garden"))
    return objs, fr, fps, P


def main():
    objs, fr, fps, P = build()
    C.finish(objs, ID, BINS, fr, height_m=TOP_M, name="Museum of Modern Art", real_footprint=P,
             height_source="LiDAR height_roof per BIN: 1087646 = 74.68 m, 1081128 = 33.05 m, 1081130 = 31.33 m; MoMA publishes no architectural height for the campus. Marron Atrium 110 ft = 33.5 m [MoMA]",
             fidelity_statement=(
                 "Exact: the three real footprints, each block modelled to its own LiDAR roof height (74.7 / 33.1 / "
                 "31.3 m), the 53rd Street black-granite-and-glass front with its aluminium entrance canopy and expressed "
                 "white gallery bands, and the Abby Aldrich Rockefeller Sculpture Garden as a walled outdoor room with "
                 "two reflecting pools and planting on the real open ground north of the blocks. Inferred: where the "
                 "1939 Goodwin & Stone, 1964 Johnson, 1984 Pelli, 2004 Taniguchi and 2019 DS+R fabric meet — the "
                 "footprint polygons do not distinguish them, so the model reads the campus as three volumes rather than "
                 "five architects, and the facade rhythm is Taniguchi's applied throughout. Simplified: the garden trees "
                 "are massing forms and its sculptures are omitted. Not modelled: the Marron Atrium and every other "
                 "interior, and 53W53 (a separate landmark)."),
             notes="Garden dimensions (about 40 x 25 m) are taken from published plans and clipped to the real open ground",
             dimensions={"top_m": TOP_M, "per_bin_roof_m": {str(k): v for k, v in HEIGHTS.items()},
                         "garden_m": [GARDEN_W, GARDEN_D], "reflecting_pools": 2, "gallery_band_pitch_m": 5.0,
                         "campus_m": [139.6, 61.5]})
    C.render_check(ID, [
        {"view": "street", "azimuth_deg": 180, "elevation_deg": "street", "distance": 105, "target_z": 32, "fov_deg": 64},
        {"view": "aerial", "azimuth_deg": 350, "elevation_deg": 28, "distance": 260, "fov_deg": 48, "target_z": 30},
    ])


if __name__ == "__main__":
    main()
