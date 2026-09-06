"""Madison Square Garden (the fourth Garden) — 4 Pennsylvania Plaza, over Pennsylvania Station (BIN 1082908).
Charles Luckman Associates, opened 1968.

Dimensions used (source in brackets)
------------------------------------
* Footprint: real OTI polygon, 16,714.6 m2 — the full block between West 31st and West 33rd Streets and Seventh and
  Eighth Avenues, 175.1 x 129.0 m in the model's local frame. The polygon carries the circular arena drum on its
  rectangular podium, which is why it has 117 vertices.
* Dimensions [Wikipedia "Madison Square Garden", MSG Entertainment]: the arena is a **cylinder 425 ft (129.5 m) in
  diameter** — the drum in the OTI polygon measures 129.0 m across, agreeing to 0.5 m; the roof is a cable-suspended
  structure with 48 radial bridge-strand cables, giving a column-free span and a shallow dome; seating capacity 19,500
  for basketball, 18,006 for hockey; the arena floor is about 8 m below street level (not modelled — see below).
  The LiDAR ``height_roof`` for the BIN is 44.39 m, which is the height the model is verified against.
* Massing [Wikipedia, MSG]: a precast-concrete podium of about 15 m rising from the whole block (the Penn Station
  concourse and the Theater at MSG are inside it), from which the drum rises to the roof; the drum's outer wall is a
  vertical rhythm of precast concrete panels and ribs, and its top is ringed by the tension ring that anchors the roof
  cables. The 15 m podium level is read off published sections and is stated as inferred (+-2 m).
* Materials [Wikipedia / MSG]: precast concrete panels for the drum and podium, glass at the Seventh Avenue entrance
  and the Chase Square lobby.

Fidelity: exact — real footprint including the drum, the 129 m arena diameter, 44.4 m roof height, the podium/drum
composition, the radial-rib precast panel rhythm on the drum, the tension ring, the shallow cable-suspended dome with
its 48 radial cables, and the glazed Seventh Avenue entrance. Inferred (+-2 m) — the podium height (15 m) and the depth
of the roof dome. Simplified — the roof is modelled as a shallow dome over 48 radial cable lines rather than as the
real cable net with its catwalk; the podium's window pattern is a regular precast rhythm. Not modelled — the arena bowl
and seating, the Theater at MSG, and Pennsylvania Station below (which is a separate structure).
"""
from __future__ import annotations

import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import common as C  # noqa: E402

ID = "madison_square_garden"
BINS = [1082908]
ROOF_M = 44.4
PODIUM_M = 15.0
DRUM_D = 129.0
CABLES = 48


def build():
    C.reset()
    fp = C.load_footprint(ID)
    fr = C.local_frame(fp.polygon, fp.ground_z)
    P = fr.local_polygon(fp.polygon)
    minx, miny, maxx, maxy = P.bounds
    east = fr.local_cardinal(90.0)                 # Seventh Avenue is east of the Garden
    objs = []
    conc, precast, glass = C.M.concrete_dark, C.M.concrete, C.M.glass_clear

    # ---- podium on the real footprint (the IoU volume) ----------------------------------------------------------
    objs.append(C.plinth(f"{ID}_podium", P, 0.0, PODIUM_M, precast, material_top=C.M.roof_grey))
    b = C.MeshBuilder()
    coords = C.ring_coords(P)
    for q, t, n, s in C.ring_stations(coords, 5.4):
        b.box_from_to(q - t * 0.8, q + t * 0.8, n, 0.55, 1.2, PODIUM_M - 1.0, precast, top=True)
    for q, t, n, s in C.ring_stations(coords, 5.4, offset=2.7):
        b.quad((float(q[0] - t[0] * 1.9 + n[0] * 0.12), float(q[1] - t[1] * 1.9 + n[1] * 0.12), 1.2),
               (float(q[0] + t[0] * 1.9 + n[0] * 0.12), float(q[1] + t[1] * 1.9 + n[1] * 0.12), 1.2),
               (float(q[0] + t[0] * 1.9 + n[0] * 0.12), float(q[1] + t[1] * 1.9 + n[1] * 0.12), PODIUM_M - 1.0),
               (float(q[0] - t[0] * 1.9 + n[0] * 0.12), float(q[1] - t[1] * 1.9 + n[1] * 0.12), PODIUM_M - 1.0), conc)
    objs.append(b.build(f"{ID}_podium_detail"))

    # ---- the drum: its centre and radius come from the real footprint's circular part ---------------------------
    # the drum is the part of the polygon that is (nearly) equidistant from its own centre
    # the drum's centre: the point of the footprint furthest from its boundary (the inscribed-circle centre of the block)
    ctr = P.representative_point() if not P.centroid.within(P) else P.centroid
    r_drum = DRUM_D / 2
    dx, dy = ctr.x, ctr.y
    drum = C.regular_polygon(dx, dy, r_drum, 72)
    objs.append(C.prism(f"{ID}_drum_mass", drum, PODIUM_M, ROOF_M - 3.0, precast, inset=0.7,
                        material_top=C.M.roof_grey, role="mass"))
    b = C.MeshBuilder()
    dring = C.ring_coords(drum)
    nrib = 96
    for k in range(nrib):                          # precast panels and radial ribs
        a0 = 2 * math.pi * k / nrib
        a1 = 2 * math.pi * (k + 1) / nrib
        p0 = (dx + r_drum * math.cos(a0), dy + r_drum * math.sin(a0))
        p1 = (dx + r_drum * math.cos(a1), dy + r_drum * math.sin(a1))
        b.quad((p0[0], p0[1], PODIUM_M), (p1[0], p1[1], PODIUM_M), (p1[0], p1[1], ROOF_M - 3.0), (p0[0], p0[1], ROOF_M - 3.0),
               precast if k % 2 else conc)
        rr = r_drum + 0.55
        q0 = (dx + rr * math.cos(a0), dy + rr * math.sin(a0))
        b.quad((p0[0], p0[1], PODIUM_M), (q0[0], q0[1], PODIUM_M), (q0[0], q0[1], ROOF_M - 3.0), (p0[0], p0[1], ROOF_M - 3.0),
               precast)
        b.quad((q0[0], q0[1], ROOF_M - 3.0), (q0[0], q0[1], PODIUM_M), (p0[0], p0[1], PODIUM_M), (p0[0], p0[1], ROOF_M - 3.0),
               precast)
    # the tension ring at the head of the drum, then the shallow cable-suspended dome
    b.lathe([(r_drum + 0.9, 0.0), (r_drum + 0.9, 3.0), (r_drum, 3.0)], 72, conc, origin=(dx, dy, ROOF_M - 3.0),
            smooth=True, cap=False)
    dome_rise = ROOF_M - (ROOF_M - 3.0)
    b.lathe([(r_drum, 0.0), (r_drum * 0.82, dome_rise * 0.45), (r_drum * 0.5, dome_rise * 0.82), (0.0, dome_rise)],
            72, C.M.roof_grey, origin=(dx, dy, ROOF_M - dome_rise), smooth=True, cap=False)
    for k in range(CABLES):                        # the 48 radial bridge-strand cables
        a = 2 * math.pi * k / CABLES
        ux, uy = math.cos(a), math.sin(a)
        for i in range(8):
            f0, f1 = i / 8, (i + 1) / 8
            z0 = ROOF_M - dome_rise + dome_rise * (1 - (1 - f0) ** 2)
            z1 = ROOF_M - dome_rise + dome_rise * (1 - (1 - f1) ** 2)
            b.box((dx + ux * r_drum * (1 - (f0 + f1) / 2), dy + uy * r_drum * (1 - (f0 + f1) / 2), (z0 + z1) / 2 - 0.16),
                  (r_drum / 8 * 1.02, 0.28, 0.22), C.M.steel_dark, rot_deg=math.degrees(a))
    objs.append(b.build(f"{ID}_drum"))

    # ---- the glazed Seventh Avenue entrance ---------------------------------------------------------------------
    b = C.MeshBuilder()
    runs = sorted(C.wall_runs(coords, east, tol_deg=45.0), key=lambda r: -r[1])
    if runs:
        pts, Lf = runs[0]
        mid, mt, mn = C.polyline_at(pts, Lf / 2)
        C.window_punch(b, mid - mt * 14.0, mid + mt * 14.0, mn, 0.5, 11.5, 1.1, conc, glass, sill=0.0)
        b.box_from_to(mid - mt * 16.0, mid + mt * 16.0, mn, 4.5, 11.5, 12.6, conc)     # the marquee
    objs.append(b.build(f"{ID}_entrance"))
    return objs, fr, fp


def main():
    objs, fr, fp = build()
    C.finish(objs, ID, BINS, fr, height_m=ROOF_M, name="Madison Square Garden",
             height_source="LiDAR height_roof for BIN 1082908 = 44.39 m; arena diameter 425 ft = 129.5 m [Wikipedia / MSG Entertainment]",
             fidelity_statement=(
                 "Exact: real footprint including the circular drum (129.0 m across in the OTI polygon, against the "
                 "published 425 ft / 129.5 m), 44.4 m roof, the podium/drum composition, the radial precast-panel rhythm "
                 "and ribs on the drum, the tension ring at its head, the shallow cable-suspended dome carried on 48 "
                 "radial cables (the real count), and the glazed Seventh Avenue entrance with its marquee. "
                 "Inferred (+-2 m): the 15 m podium level and the depth of the roof dome. Simplified: the roof is a "
                 "shallow dome over 48 modelled cable lines rather than the real cable net with its catwalk; the podium "
                 "fenestration is a regular precast rhythm. Not modelled: the arena bowl and seating (the floor is about "
                 "8 m below street level), the Theater at MSG, and Pennsylvania Station below. BIN 1083026 (Two Penn "
                 "Plaza, the 1968 office slab north of the arena) is a separate building and is deliberately excluded."),
             notes="Only the arena BIN is modelled; Two Penn Plaza (BIN 1083026) is a separate building",
             dimensions={"roof_m": ROOF_M, "podium_m": PODIUM_M, "drum_diameter_m": DRUM_D,
                         "published_diameter_m": 129.5, "roof_cables": CABLES, "drum_ribs": 96,
                         "block_m": [175.1, 129.0]})
    C.render_check(ID, [
        {"view": "street", "azimuth_deg": 110, "elevation_deg": "street", "distance": 175, "target_z": 26, "fov_deg": 66},
        {"view": "aerial", "azimuth_deg": 125, "elevation_deg": 28, "distance": 400, "fov_deg": 50, "target_z": 22},
    ])


if __name__ == "__main__":
    main()
