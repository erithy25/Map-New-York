"""Roosevelt Island Tramway — aerial tramway over the East River between Second Avenue at 59th-60th Streets
(Manhattan) and 300 Main Street (Roosevelt Island).  Opened 17 May 1976; rebuilt March-November 2010 with two
independently operating cabins (Poma/Leitner).  The only aerial commuter tram in the United States until 2006.

Dimensions used (source in brackets)
------------------------------------
* Route length **3,140 ft = 957.1 m**; the East River span is **1,184 ft = 360.9 m**; **three steel support towers**,
  the tallest **250 ft = 76.20 m** above ground at York Avenue; the Manhattan terminal is elevated **18 ft = 5.49 m**;
  the Roosevelt Island terminal is at grade; each cabin carries **110 passengers**, weighs 22,125 lb empty and runs at
  **17 mph = 7.6 m/s**; the crossing takes 3-4 minutes [Wikipedia "Roosevelt Island Tramway", RIOC].

Placement: the whole line comes from OSM way ``22886820`` (``aerialway=cable_car``, name "Roosevelt Island Tramway"),
whose five vertices are, in NYC_TM metres, the Manhattan terminal (-1192.4, 6793.4), tower 1 (-1037.7, 6715.5),
tower 2 (-754.5, 6564.6, York Avenue), tower 3 (-429.2, 6407.5) and the Roosevelt Island terminal (-358.0, 6371.0).
The four measured segment lengths are 173.2 / 320.9 / 361.3 / 80.0 m — the third of which is **0.1 %** from the
published 1,184 ft river span — and they sum to 935.4 m against the published 957.1 m (the difference is the length
of the two station platforms, which the OSM way does not include).  The line is therefore modelled *exactly on its
real polyline*, not straightened.

Tower heights other than York Avenue's 250 ft are **inferred** (tower 1 = 46 m, tower 3 = 31 m, +-6 m) from the
requirement that the track ropes clear the Queensboro Bridge approach and the island; no published figures were found.

Not modelled: the haul-rope grips and bogies in detail, the drive and tension machinery inside the terminals, the
station canopies' glazing pattern, the rescue-cabin rail, and the tower maintenance ladders.
"""
from __future__ import annotations

import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import b_align as ba  # noqa: E402
import b_bridge_lib as bl  # noqa: E402
import b_common as bc  # noqa: E402
from mathutils import Vector  # noqa: E402

ID = "b_roosevelt_island_tram"
TITLE = "Roosevelt Island Tramway"

# OSM way 22886820 vertices in NYC_TM (metres), Manhattan -> Roosevelt Island
LINE_TM = [(-1192.4, 6793.4), (-1037.7, 6715.5), (-754.5, 6564.6), (-429.2, 6407.5), (-358.0, 6371.0)]
TOWER_H = [None, 46.0, 76.20, 31.0, None]      # above ground; index 2 = York Avenue, the published 250 ft
TERMINAL_MN_DZ = 5.49                          # 18 ft
RIVER_SPAN = 360.9                             # 1,184 ft
ROUTE_LEN = 957.1                              # 3,140 ft
CABIN_CAP = 110
GROUND = 4.0
ROPE_GAUGE = 2.6                               # track-rope spacing across the cabin (inferred)
CABIN_L, CABIN_W, CABIN_H = 5.2, 3.4, 3.1      # inferred from the 110-passenger capacity


def _local(frame, p):
    x, y, _ = frame.to_local(p[0], p[1])
    return Vector((x, y, 0.0))


def _rope(pts, sag_frac, z_at, step: float = 12.0):
    """Catenary polyline through consecutive tower sheaves (one list of 3-D points per span, joined)."""
    out = []
    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]
        span = (b - a).length
        sag = max(span * sag_frac, 0.4)
        prof = bc.catenary_points(0.0, z_at[i], span, z_at[i + 1], sag, n=max(int(span / step), 4))
        d = (b - a).normalized()
        for k, (s, z) in enumerate(prof):
            if i > 0 and k == 0:
                continue
            out.append(a + d * s + Vector((0, 0, z - a.z)))
    return out


def build(lod: int = 0):
    frame = ba.frame_at(*LINE_TM[2], 0.0,
                        math.degrees(math.atan2(LINE_TM[4][0] - LINE_TM[0][0], LINE_TM[4][1] - LINE_TM[0][1])) % 360.0)
    P = [_local(frame, p) for p in LINE_TM]
    objs: list = []
    # sheave elevations (NAVD88): terminals carry their sheaves just above the platform, towers at their published /
    # inferred heights
    z_sheave = [GROUND + TERMINAL_MN_DZ + 8.0, GROUND + TOWER_H[1], GROUND + TOWER_H[2], GROUND + TOWER_H[3],
                GROUND + 9.0]

    # ---- towers ---------------------------------------------------------------------------------------------------
    for i in (1, 2, 3):
        base = P[i] + Vector((0, 0, GROUND - 3.0))
        top = P[i] + Vector((0, 0, z_sheave[i]))
        # the published tower height is to the top of the sheave head, so the lattice stops 1.6 m short of it and the
        # head occupies that band -- the rope then rides over the sheaves at exactly the published elevation
        top = P[i] + Vector((0, 0, z_sheave[i] - 1.6))
        objs.append(bc.lattice_column(f"tower{i}", base, top, 7.5, 3.4, "steel_gray",
                                      panels=max(int(TOWER_H[i] / 9), 4), member=0.5 if lod == 0 else 0.8,
                                      x_brace=(lod == 0)))
        head = bc.box(f"tower{i}_head", (4.0, ROPE_GAUGE + 3.2, 1.6), (P[i].x, P[i].y, z_sheave[i] - 1.6), "steel_gray")
        objs.append(head)
        if lod == 0:
            for dt in (-ROPE_GAUGE / 2, ROPE_GAUGE / 2):
                d = (P[min(i + 1, 4)] - P[max(i - 1, 0)]).normalized()
                n = Vector((-d.y, d.x, 0.0))
                objs.append(bc.cylinder_between(f"tower{i}_sheave{dt:+.1f}",
                                                P[i] + n * dt + Vector((0, 0, z_sheave[i] + 1.0)) - d * 1.2,
                                                P[i] + n * dt + Vector((0, 0, z_sheave[i] + 1.0)) + d * 1.2,
                                                0.55, "steel_black", 12, cap=True))

    # ---- track ropes and haul rope --------------------------------------------------------------------------------
    for side in (-1, 1):
        pts = []
        for i, p in enumerate(P):
            d = (P[min(i + 1, 4)] - P[max(i - 1, 0)]).normalized()
            n = Vector((-d.y, d.x, 0.0))
            pts.append(p + n * (side * ROPE_GAUGE / 2))
        rope = _rope(pts, 0.012, z_sheave, 12.0 if lod == 0 else 60.0)
        objs.append(bc.tube_along(f"track_rope{side}", rope, 0.032, "steel_silver", 6 if lod == 0 else 4, cap=False))
    haul = _rope(P, 0.016, [z - 1.6 for z in z_sheave], 12.0 if lod == 0 else 60.0)
    objs.append(bc.tube_along("haul_rope", haul, 0.022, "steel_silver", 5 if lod == 0 else 4, cap=False))

    # ---- terminals ------------------------------------------------------------------------------------------------
    mn = P[0]
    d0 = (P[1] - P[0]).normalized()
    a0 = math.degrees(math.atan2(d0.y, d0.x))
    plat = bc.box("mn_platform", (26.0, 15.0, 1.2), (mn.x, mn.y, GROUND + TERMINAL_MN_DZ - 1.2), "concrete")
    bc.transform(plat, bc.Matrix.Translation(-Vector((mn.x, mn.y, 0))) )
    bc.transform(plat, bc.rot_z(0.0))
    bc.transform(plat, bc.Matrix.Translation(Vector((mn.x, mn.y, 0))))
    objs.append(plat)
    for i, (dx, dy) in enumerate(((-11.0, -6.0), (11.0, -6.0), (-11.0, 6.0), (11.0, 6.0))):
        objs.append(bc.box(f"mn_col{i}", (1.2, 1.2, TERMINAL_MN_DZ), (mn.x + dx, mn.y + dy, GROUND), "concrete"))
    objs.append(bc.box("mn_house", (18.0, 12.0, 9.0), (mn.x, mn.y, GROUND + TERMINAL_MN_DZ), "steel_gray"))
    if lod == 0:
        objs.append(bc.box("mn_glazing", (16.0, 10.0, 4.0), (mn.x, mn.y, GROUND + TERMINAL_MN_DZ + 2.0), "glass_clear"))
    ri = P[4]
    objs.append(bc.box("ri_platform", (24.0, 14.0, 1.0), (ri.x, ri.y, GROUND - 1.0), "concrete"))
    objs.append(bc.box("ri_house", (18.0, 12.0, 10.0), (ri.x, ri.y, GROUND), "steel_gray"))
    if lod == 0:
        objs.append(bc.box("ri_glazing", (16.0, 10.0, 4.5), (ri.x, ri.y, GROUND + 2.0), "glass_clear"))
    _ = a0

    # ---- the two cabins -------------------------------------------------------------------------------------------
    rope_ref = _rope(P, 0.016, [z - 1.6 for z in z_sheave], 12.0)
    for k, frac in ((0, 0.42), (1, 0.72)):
        idx = int(frac * (len(rope_ref) - 1))
        c = rope_ref[idx]
        nxt = rope_ref[min(idx + 1, len(rope_ref) - 1)]
        d = (nxt - c).normalized() if (nxt - c).length > 1e-6 else Vector((1, 0, 0))
        ang = math.degrees(math.atan2(d.y, d.x))
        body = bc.box(f"cabin{k}_body", (CABIN_L, CABIN_W, CABIN_H), (0, 0, -CABIN_H - 2.2), "cabin_red", anchor="bottom")
        glass = bc.box(f"cabin{k}_glass", (CABIN_L - 0.5, CABIN_W + 0.06, CABIN_H - 1.4), (0, 0, -CABIN_H - 1.5),
                       "glass_clear", anchor="bottom") if lod == 0 else None
        hang = bc.box(f"cabin{k}_hanger", (0.5, 0.5, 2.2), (0, 0, -2.2), "steel_gray", anchor="bottom")
        bogie = bc.box(f"cabin{k}_bogie", (2.6, ROPE_GAUGE + 0.6, 0.6), (0, 0, -0.3), "steel_black", anchor="center")
        for ob in [o for o in (body, glass, hang, bogie) if o is not None]:
            bc.transform(ob, bc.rot_z(90.0 - ang))
            bc.transform(ob, bc.Matrix.Translation(c))
            objs.append(ob)

    extras = {
        "origin_tm": frame.origin_tm, "heading_deg": frame.heading_deg, "height_m": TOWER_H[2], "name": TITLE,
        "route_length_published_m": ROUTE_LEN, "route_length_modelled_m": sum((P[i + 1] - P[i]).length for i in range(4)),
        "river_span_m": RIVER_SPAN, "towers": 3, "tallest_tower_m": TOWER_H[2],
        "manhattan_terminal_height_m": TERMINAL_MN_DZ, "cabin_capacity": CABIN_CAP, "cabins": 2,
        "alignment_source": "OSM way 22886820 (aerialway=cable_car) vertices, used verbatim",
        "height_source": "Wikipedia/RIOC: 3,140 ft route, 1,184 ft river span, tallest tower 250 ft at York Avenue",
        "sources_ids": ["osm_bbbike", "published_ri_tram"],
        "fidelity_statement": (
            "Exact: the line follows the real OSM polyline vertex for vertex (four spans of 173.2 / 320.9 / 361.3 / "
            "80.0 m, the river span 0.1 % from the published 1,184 ft); York Avenue tower 76.20 m (250 ft); "
            "Manhattan terminal elevated 5.49 m (18 ft); Roosevelt Island terminal at grade; two cabins on the line. "
            "Inferred: tower 1 and tower 3 heights (46 m / 31 m, +-6 m — no published figures), 2.6 m track-rope "
            "gauge, 1.2 %/1.6 % rope sag, cabin dimensions from the 110-passenger capacity, terminal building sizes. "
            "Not modelled: haul-rope grips and bogies in detail, drive and tension machinery, station glazing "
            "pattern, rescue-cabin rail, tower ladders."),
    }
    return objs, extras


def main() -> None:
    frame = ba.frame_at(*LINE_TM[2], 0.0,
                        math.degrees(math.atan2(LINE_TM[4][0] - LINE_TM[0][0], LINE_TM[4][1] - LINE_TM[0][1])) % 360.0)
    P = [_local(frame, p) for p in LINE_TM]
    mid = (P[2] + P[3]) / 2
    ctx = (("water_dark", 0.35, 700.0, (mid.x, mid.y)),
           ("ground_urban", GROUND, 260.0, (P[0].x - 60.0, P[0].y + 60.0)),
           ("grass", GROUND, 200.0, (P[4].x + 60.0, P[4].y - 60.0)))
    ba.run_landmark(
        ID, TITLE, build, budget_lod0=250_000, budget_lod1=50_000,
        renders=[
            # the comparison agent's recorded photographic viewpoint, used verbatim
            ba.reference_render("landmark_roosevelt_island_tram", frame, view="tram_reference",
                                ground_z=GROUND, target_z=60.0, fov_deg=58.0, size=(1280, 720), context=ctx,
                                sun_azimuth_deg=215.0, sun_elevation_deg=35.0),
            dict(view="from_the_island", cam=(P[4].x + 90.0, P[4].y - 40.0, GROUND + 2.0),
                 target=(P[2].x, P[2].y, 55.0), fov_deg=58.0, context=ctx, sun_azimuth_deg=250.0, sun_elevation_deg=34.0),
            dict(view="york_avenue_tower", cam=(P[2].x + 110.0, P[2].y + 90.0, GROUND + 2.0),
                 target=(P[2].x, P[2].y, 60.0), fov_deg=64.0, context=ctx, sun_azimuth_deg=150.0, sun_elevation_deg=40.0),
        ],
        sections={"Placement": "line from OSM way 22886820, used vertex for vertex; frame origin at the York Avenue "
                               "tower, NYC_TM (%.1f, %.1f)." % (LINE_TM[2][0], LINE_TM[2][1]),
                  "Published dimensions": __doc__.split("------------------------------------\n")[1].split("\nPlacement:")[0].strip(),
                  "Not modelled": __doc__.split("Not modelled:")[1].strip()},
    )


if __name__ == "__main__":
    main()
