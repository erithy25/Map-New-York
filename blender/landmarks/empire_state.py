"""Empire State Building — 350 Fifth Avenue (BIN 1015862, LP-2000). Shreve, Lamb & Harmon, 1931.

Dimensions used (source in brackets)
------------------------------------
* Footprint: real OTI polygon (7,943 m2, 149 x 58 m incl. the narrower western 6-storey wing). The original Waldorf-Astoria
  lot was 197 ft 6 in on Fifth Avenue x 425 ft (60.2 x 129.5 m) [Wikipedia, LPC designation report LP-2000]; the tower is
  centred on that lot; the extra 19.5 m at the west is base only.
* Heights [CTBUH/Emporis/Wikipedia]: roof (top of 102nd-floor structure) 380.6 m (1,250 ft); tip with antenna 443.2 m (1,454 ft);
  86th-floor observatory deck 320.0 m (1,050 ft); 102nd floor 373.1 m (1,224 ft); 102 floors.
* Setback floors 6 / 21 / 25 / 30 / 72 / 81 / 85 [LPC report, Wikipedia "Architecture"]. Storey heights derived so that the
  86th-floor deck lands at 320.0 m: base floors 1-5 top at 21.0 m (three-storey lobby + 2 floors), floors 6-30 at 3.75 m,
  floors 31-85 at 3.732 m. Floor plates from the published figures (base ~7,900 m2 = lot; tower shaft ~2,100 m2; upper
  tiers ~1,400 / ~840 m2) — tier plan dimensions below are inferred from those areas +-10 % (stated uncertainty).
* Materials [LPC report]: Indiana limestone with granite base (floors 1-2), chrome-nickel steel and aluminium spandrels
  forming continuous vertical window strips between limestone piers, aluminium-framed windows (6,514 windows in the
  real building; this model has the same strip rhythm: 1.35 m windows / 1.30 m piers), Art Deco stainless-steel mooring mast.
* Crown lighting: material slot ``ESB_CROWN`` (emissive) on the 72nd-85th floor spandrels, the setback floodlight panels
  and the mast bands; the engine recolours that slot from ``live/esb_lights.json``.

Fidelity: massing/setback rhythm/heights exact to the published values; strip fenestration modelled as geometry; the
5th Avenue entrance recess, canopies and storefront bays are modelled; the aluminium relief panels, eagles and interior
lobby are NOT modelled (stated gap). Tier plan dimensions are inferred from floor-area figures (+-10 %).
"""
from __future__ import annotations

import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import common as C  # noqa: E402
from shapely.geometry import Polygon  # noqa: E402
from shapely.ops import unary_union  # noqa: E402

ID = "empire_state"
BINS = [1015862]
ROOF_M = 380.6
TIP_M = 443.2
DECK86_M = 320.0
FLOOR102_M = 373.1
LOT_DEPTH = 129.5      # 425 ft
LOT_WIDTH = 60.2       # 197.5 ft


def floor_tops() -> list[float]:
    """z of the top of floor k (index k), k = 0..86 (floor 0 = ground)."""
    z = [0.0]
    for k in range(1, 6):
        z.append(21.0 * k / 5)            # ground/lobby storeys average 4.2 m
    for k in range(6, 31):
        z.append(21.0 + (k - 5) * 3.75)
    for k in range(31, 86):
        z.append(z[30] + (k - 30) * 3.732)
    return z


def cruciform(cx: float, cy: float, w: float, d: float, wing_w: float, wing_d: float, end_w: float, end_d: float) -> Polygon:
    """Rectangle w x d (x by y) with central projections: N/S wings (width wing_w along x, depth wing_d) and E/W ends."""
    core = C.rect(cx, cy, w, d)
    ns = C.rect(cx, cy, wing_w, d + 2 * wing_d)
    ew = C.rect(cx, cy, w + 2 * end_d, end_w)
    return C._orient(unary_union([core, ns, ew]), 1.0)


def build():
    C.reset()
    fp = C.load_footprint(ID)
    fr = C.local_frame(fp.polygon, fp.ground_z)          # +x -> Fifth Avenue (ESE), +y -> 34th Street side
    P = fr.local_polygon(fp.polygon)
    minx, miny, maxx, maxy = P.bounds
    x_east = maxx                                        # Fifth Avenue building line
    x_west_lot = x_east - LOT_DEPTH                      # west edge of the original lot
    cy = (miny + maxy) / 2
    cx = (x_east + x_west_lot) / 2                       # tower centred on the original lot
    Z = floor_tops()
    objs = []
    lime, gran, chrome, glass = C.M.limestone, C.M.granite_dark, C.M.steel_chrome, C.M.glass_dark

    # ---- Tier 0: five-storey base on the real footprint (flush; IoU volume) --------------------------------------
    z5 = Z[5]
    objs.append(C.plinth(f"{ID}_base", P, 0.0, z5, lime, material_top=C.M.roof_grey))
    # granite two-storey base course and storefront/entrance bays on the street edges (E, N, S)
    b = C.MeshBuilder()
    coords = C.ring_coords(P)
    for p0, p1, L, t, n in C.edges_of(coords):
        if L < 12:
            continue
        # granite piers with recessed storefront glazing, ground floor 0-6.0 m
        bays = max(1, int(round(L / 6.2)))
        mod = L / bays
        for k in range(bays):
            a = p0 + t * (k * mod); c = p0 + t * ((k + 1) * mod)
            pier_w = 1.6
            b.box_from_to(a, a + t * pier_w, n, 0, 0.45, 0.0, 6.0, gran)
            g0 = a + t * pier_w; g1 = c
            if k == bays - 1:
                b.box_from_to(c - t * pier_w, c, n, 0, 0.45, 0.0, 6.0, gran); g1 = c - t * pier_w
            b.quad((g0[0] + n[0] * 0.05, g0[1] + n[1] * 0.05, 0.0), (g1[0] + n[0] * 0.05, g1[1] + n[1] * 0.05, 0.0),
                   (g1[0] + n[0] * 0.05, g1[1] + n[1] * 0.05, 4.6), (g0[0] + n[0] * 0.05, g0[1] + n[1] * 0.05, 4.6), C.M.glass_clear)
            b.box_from_to(g0, g1, n, 0, 0.25, 4.6, 6.0, gran)        # storefront head / transom band
        # floors 2-5 punched windows in the limestone (window strips start at floor 2)
        fl = [Z[1], Z[2], Z[3], Z[4]]
        C.punched_wall(b, p0, p1, n, 6.0, z5, fl, lime, glass, bays=max(2, int(round(L / 2.7))), window_w=1.35, window_h=2.5,
                       sill_h=0.9, depth=0.45)
    # Fifth Avenue entrance: 3-storey recess with stainless surround (centre of the east edge), 15 m wide, 13 m high
    e0, e1, L, t, n = C.edge_facing(coords, 0.0)
    mid = (e0 + e1) / 2
    for dx, w, h, depth, m_ in ((0.0, 15.0, 13.0, 3.0, C.M.steel_nirosta), (0.0, 12.0, 11.0, 3.0, C.M.glass_dark)):
        a = mid - t * (w / 2); c = mid + t * (w / 2)
        C.window_punch(b, a, c, n, 0.0, h, depth, m_ if m_ is not C.M.glass_dark else C.M.steel_nirosta, C.M.glass_dark, sill=0.0)
    b.box_from_to(mid - t * 9.0, mid + t * 9.0, n, 0, 3.2, 6.0, 6.5, C.M.steel_nirosta)   # canopy
    # 33rd / 34th Street entrances (centre of the long edges, 8 m wide, 8 m high)
    for ang in (90.0, -90.0):
        s0, s1, L2, t2, n2 = C.edge_facing(coords, ang)
        m2 = (s0 + s1) / 2
        C.window_punch(b, m2 - t2 * 4.0, m2 + t2 * 4.0, n2, 0.0, 8.0, 2.5, C.M.steel_nirosta, C.M.glass_dark, sill=0.0)
        b.box_from_to(m2 - t2 * 5.0, m2 + t2 * 5.0, n2, 0, 2.6, 5.5, 6.0, C.M.steel_nirosta)
    objs.append(b.build(f"{ID}_base_detail"))
    objs.append(C.cornice(f"{ID}_base_cornice", P, z5, [(0.25, 0.0), (0.6, 0.5), (0.6, 0.8), (0.3, 1.0)], lime))

    # ---- Tiers 1-3 (floors 6-29): block with the small documented setbacks ---------------------------------------
    main = P.intersection(C.rect_xy(x_west_lot - 0.5, miny - 1, x_east + 1, maxy + 1))
    main = C._orient(main.buffer(0), 1.0)
    fen_lo = C.Fenestration(bay_w=2.65, window_frac=0.51, recess=0.45, spandrel_h=1.05, strip=True, pier="limestone",
                            spandrel="steel_chrome", glass="glass_dark", floor_z=Z)
    t1 = C.offset_polygon(main, -3.5)
    objs += C.tower_tier(f"{ID}_t1", t1, z5, Z[20], fen_lo, parapet_h=1.2)
    t2 = C.offset_polygon(t1, -2.6)
    objs += C.tower_tier(f"{ID}_t2", t2, Z[20], Z[24], fen_lo, parapet_h=1.2)
    t3 = C.offset_polygon(t2, -2.6)
    objs += C.tower_tier(f"{ID}_t3", t3, Z[24], Z[29], fen_lo, parapet_h=1.2)

    # ---- Tier 4: tower shaft floors 30-71, cruciform (inferred 34 x 62 m core + projections) ------------------
    fen_hi = C.Fenestration(bay_w=2.65, window_frac=0.51, recess=0.45, spandrel_h=1.05, strip=True, pier="limestone",
                            spandrel="steel_chrome", glass="glass_dark", floor_z=Z)
    shaft = cruciform(cx, cy, 62.0, 34.0, 36.0, 3.5, 20.0, 2.5)
    objs += C.tower_tier(f"{ID}_t4", shaft, Z[29], Z[71], fen_hi, parapet_h=1.3)
    # ---- Tier 5: floors 72-80 -------------------------------------------------------------------------------------
    fen_crown = C.Fenestration(bay_w=2.65, window_frac=0.51, recess=0.45, spandrel_h=1.05, strip=True, pier="limestone",
                               spandrel="ESB_CROWN", glass="glass_dark", floor_z=Z)
    t5 = cruciform(cx, cy, 50.0, 28.0, 30.0, 3.0, 16.0, 2.0)
    objs += C.tower_tier(f"{ID}_t5", t5, Z[71], Z[80], fen_crown, parapet_h=1.3)
    # floodlight panels on the 72nd floor setback (emissive slot)
    b = C.MeshBuilder()
    for ring, zz in ((C.ring_coords(shaft), Z[71] + 1.35), (C.ring_coords(t5), Z[80] + 1.35)):
        for p0, p1, L, t, n in C.edges_of(ring):
            if L < 8:
                continue
            for k in range(int(L // 6)):
                q = p0 + t * (3 + 6 * k) - n * 0.9
                b.box((q[0], q[1], zz + 0.3), (1.0, 1.0, 0.6), C.M.ESB_CROWN, rot_deg=math.degrees(math.atan2(t[1], t[0])))
    objs.append(b.build(f"{ID}_floodlights"))
    # ---- Tier 6: floors 81-85 ------------------------------------------------------------------------------------
    t6 = cruciform(cx, cy, 38.0, 22.0, 22.0, 2.5, 12.0, 1.5)
    objs += C.tower_tier(f"{ID}_t6", t6, Z[80], Z[85], fen_crown, parapet_h=1.3)

    # ---- 86th floor observatory (deck at 320.0 m) and mooring mast ------------------------------------------------
    b = C.MeshBuilder()
    obs = C.rect(cx, cy, 30.0, 16.0)
    b.prism(C.ring_coords(obs), Z[85], Z[85] + 5.5, lime, material_top=C.M.roof_grey)
    for p0, p1, L, t, n in C.edges_of(C.ring_coords(obs)):
        bays = max(1, int(round(L / 2.65)))
        for k in range(bays):
            mod = L / bays
            a = p0 + t * (k * mod + 0.65); c = p0 + t * ((k + 1) * mod - 0.65)
            C.window_punch(b, a, c, n, Z[85] + 1.0, Z[85] + 4.2, 0.35, lime, glass)
    # mast base block floors 87-90 (stepped), then the fluted stainless tower to the 102nd floor and the cap at 380.6 m
    z87 = Z[85] + 5.5
    b.prism(C.ring_coords(C.rect(cx, cy, 20.0, 14.0)), z87, z87 + 6.0, lime, material_top=C.M.roof_grey)
    b.prism(C.ring_coords(C.rect(cx, cy, 16.0, 12.0)), z87 + 6.0, z87 + 12.0, lime, material_top=C.M.roof_grey)
    z_cyl0 = z87 + 12.0                                   # ~343.5 m
    # fluted shaft: 16 vertical stainless fins around a glass-and-steel core, tapering 6.5 -> 4.6 m radius
    steel = C.M.steel_nirosta
    b.lathe([(6.5, 0.0), (6.4, 4.0), (5.6, 18.0), (4.8, FLOOR102_M - z_cyl0 - 3.0), (4.6, FLOOR102_M - z_cyl0 - 3.0)], 32, C.M.ESB_CROWN, origin=(cx, cy, z_cyl0))
    for k in range(16):
        a = 2 * math.pi * k / 16
        fx, fy = math.cos(a), math.sin(a)
        for r0, r1, zz0, zz1 in ((6.9, 5.0, 0.0, FLOOR102_M - z_cyl0 - 3.0),):
            pts = []
            for rr, zz in ((r0, zz0), (r0 + 0.5, zz0), (r1 + 0.5, zz1), (r1, zz1)):
                for side in (-0.35, 0.35):
                    pts.append((cx + fx * rr - fy * side, cy + fy * rr + fx * side, z_cyl0 + zz))
            b.hull(pts, steel)
    # 102nd floor: glazed observation ring and conical cap up to the roof height
    z102 = FLOOR102_M
    b.lathe([(4.6, 0.0), (4.9, 0.6), (4.9, 1.0), (3.6, 1.0), (3.6, 4.2), (4.2, 4.6), (4.2, 5.2), (2.2, 6.4), (1.2, ROOF_M - z102 - 0.6), (0.9, ROOF_M - z102)], 32, steel, origin=(cx, cy, z102))
    b.lathe([(3.55, 1.0), (3.55, 4.2)], 32, C.M.glass_dark, origin=(cx, cy, z102), cap=False)
    # antenna mast 380.6 -> 443.2 m with three platforms
    b.lathe([(0.9, 0.0), (0.7, 20.0), (0.45, 45.0), (0.3, TIP_M - ROOF_M - 1.0), (0.0, TIP_M - ROOF_M)], 12, C.M.steel_dark, origin=(cx, cy, ROOF_M))
    for dz, r in ((8.0, 2.2), (22.0, 1.8), (40.0, 1.4)):
        b.lathe([(0.0, 0.0), (r, 0.0), (r, 0.5), (0.0, 0.5)], 12, C.M.steel_dark, origin=(cx, cy, ROOF_M + dz))
    objs.append(b.build(f"{ID}_crown"))
    return objs, fr, fp


def main():
    objs, fr, fp = build()
    C.finish(objs, ID, BINS, fr, height_m=TIP_M, name="Empire State Building", lp_number="LP-02000",
             height_source="CTBUH/Emporis: roof 380.6 m, tip 443.2 m; 86th-floor deck 320.0 m; 102nd floor 373.1 m",
             fidelity_statement=("Exact: real footprint, 102-floor setback sequence (6/21/25/30/72/81/85), roof 380.6 m, tip 443.2 m, "
                                 "86th-floor deck 320 m, limestone/granite/chrome-nickel materials, continuous window-strip rhythm. "
                                 "Inferred (+-10 %): tier plan dimensions from published floor-plate areas. Simplified: mooring mast "
                                 "fluting (16 fins), antenna platforms. Not modelled: lobby interior, aluminium relief panels, eagles."),
             notes="Crown lighting slot ESB_CROWN (emissive) — engine drives colour from live/esb_lights.json",
             dimensions={"roof_m": ROOF_M, "tip_m": TIP_M, "deck86_m": DECK86_M, "floor102_m": FLOOR102_M, "lot_m": [LOT_DEPTH, LOT_WIDTH],
                         "base_top_m": 21.0, "floor_h_6_30_m": 3.75, "floor_h_31_85_m": 3.732, "shaft_plan_m": [62, 34], "t5_plan_m": [50, 28], "t6_plan_m": [38, 22],
                         "window_module_m": 2.65, "window_w_m": 1.35},
             tri_budget=C.TRI_BUDGET_LOD0_LARGE,
             material_slots={"ESB_CROWN": "emissive crown lighting (72nd-85th floor spandrels, setback floodlights, mast bands)"})
    C.render_check(ID, [
        {"view": "street", "azimuth_deg": 150, "elevation_deg": "street", "distance": 95, "target_z": 24, "fov_deg": 65},
        {"view": "aerial", "azimuth_deg": 215, "elevation_deg": 22},
        {"view": "skyline", "azimuth_deg": 160, "elevation_deg": 6, "distance": 1400, "fov_deg": 30, "target_z": 200},
    ])


if __name__ == "__main__":
    main()
