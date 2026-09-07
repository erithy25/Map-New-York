"""Domino Sugar Refinery and Domino Park — 292-314 Kent Avenue, Williamsburg (BIN 3335796, LP-2268 for the Filter,
Pan and Finishing House). Havemeyers & Elder, 1881-84 (Theodore A. Havemeyer); adaptive reuse by Practice for
Architecture and Urbanism (PAU) with Ennead, 2023; Domino Park by James Corner Field Operations, 2018.

Dimensions used (source in brackets)
------------------------------------
* Footprint: the real OTI polygon (3,051 m2) of the landmarked Filter/Pan/Finishing House, 63.8 x 85.2 m, on the
  East River waterfront; Kent Avenue is east (local +x), the river west.
* Heights [LP-2268; PAU]: the 1884 brick shell rises to **155 ft = 47.2 m** at its parapet (OTI LiDAR gives 45.8 m
  for the pre-2023 roof); PAU's 2023 barrel-vaulted glass "building within a building" rises above it to
  **~200 ft = 60.0 m**, which is the model's height.
* Brick shell [LP-2268]: Romanesque Revival red brick with round-arched window bays on a 4.9 m module, corbelled
  brick cornices at each floor line, and segmental relieving arches; the shell was retained and the interior removed.
* Glass insert [PAU 2023]: a glass-and-steel volume set 3.0 m inside the brick walls with a barrel vault springing
  from the old parapet, so a light-filled void separates the two.
* Domino Park [JCFO 2018]: a **5-acre (2.0 ha), 450 ft = 137 m** waterfront park; its **Artifact Walk** is an
  elevated walkway 9.1 m above grade carrying four salvaged **syrup tanks** (each 6.0 m in diameter and 12.0 m
  tall) and 21 salvaged columns and crane tracks. The park lies west of the footprint and is tagged ``role="park"``.
* The four rooftop letters of the "Domino Sugar" sign are 5.5 m tall on a steel frame on the north elevation.

Fidelity: real footprint; the 47.2 m brick shell with its arched bays and corbelled cornices, the 60.0 m glass
barrel vault set 3.0 m inside it, the Artifact Walk at 9.1 m with its four syrup tanks and column line, and the
rooftop sign frame are modelled as geometry. Inferred (stated): the park's extent (the real park is outside the
footprint; its western edge is placed 60 m from the building line), the bay module (measured from the polygon), and
the position of the salvaged tanks. NOT modelled: the "Domino Sugar" letters themselves (their steel frame is), the
interiors, the adjacent new towers, and the park's planting.
"""
from __future__ import annotations

import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import c_common as cc  # noqa: E402
import common as C  # noqa: E402

ID = "c_domino_sugar_refinery"
BIN = 3335796
BRICK_TOP = 47.2
VAULT_TOP = 60.0
WALK_Z = 9.1
TANK_D, TANK_H, TANKS = 6.0, 12.0, 4
SIGN_LETTER_H = 5.5


def build():
    C.reset()
    # weathering (Cor-Ten) steel: not in the shared palette, so its albedo is declared here
    C.custom_material("rust", (122, 74, 50), roughness=0.72, metallic=0.25,
                      note="pre-weathered / Cor-Ten steel [SHoP Barclays Center panels; High Line viaduct girders]")
    cc.materials(["brick_red", "brick_buff", "glass_clear", "glass_dark", "steel_dark", "rust", "concrete",
                  "roof_dark", "pavement", "grass", "wood_dark"])
    g = cc.Group(ID)
    P = g.poly(BIN)
    coords = C.ring_coords(P)
    objs: list = []

    # ---- the 1884 brick shell (IoU volume) -----------------------------------------------------------------------
    objs.append(C.plinth(f"{ID}_shell_base", P, 0.0, 6.0, C.M.brick_red, material_top=C.M.roof_dark))
    b = C.MeshBuilder()
    floors = [6.0 + (BRICK_TOP - 2.0 - 6.0) * k / 7 for k in range(8)]
    for p0, p1, L, t, n in C.edges_of(coords):
        nbay = max(1, int(round(L / 4.9)))
        mod = L / nbay
        for k in range(nbay):
            a = p0 + t * (k * mod + 1.15)
            c = p0 + t * ((k + 1) * mod - 1.15)
            for fi in range(len(floors) - 1):
                z0 = floors[fi] + 0.9
                z1 = floors[fi + 1] - 0.9
                C.arched_opening(b, a, c, n, z0, z1 - (float(((c - a) ** 2).sum()) ** 0.5) / 2, None, 0.55,
                                 C.M.brick_red, C.M.glass_dark)
            b.box_from_to(p0 + t * (k * mod - 0.55), p0 + t * (k * mod + 0.55), n, 0.55, 0.0, BRICK_TOP - 2.0,
                          C.M.brick_red)
        for z in floors[1:]:                                    # corbelled brick cornices at each floor line
            b.box_from_to(p0, p1, n, 0.35, z - 0.5, z, C.M.brick_red)
        b.box_from_to(p0, p1, n, 0.7, BRICK_TOP - 2.0, BRICK_TOP, C.M.brick_red)      # the parapet
    objs.append(b.build(f"{ID}_brick_shell"))

    # ---- PAU's glass barrel vault, set 3.0 m inside the brick walls ----------------------------------------------
    inner = C.offset_polygon(P, -3.0)
    ix0, iy0, ix1, iy1 = inner.bounds
    b = C.MeshBuilder()
    b.prism(C.ring_coords(inner), 6.0, BRICK_TOP, C.M.glass_clear, cap_top=False, cap_bottom=False)
    nrib = 14
    for k in range(nrib + 1):
        u = k / nrib
        x = ix0 + (ix1 - ix0) * u
        prof = []
        for j in range(13):
            v = j / 12.0
            y = iy0 + (iy1 - iy0) * v
            z = BRICK_TOP + (VAULT_TOP - BRICK_TOP) * math.sin(math.pi * v)
            prof.append((y, z))
        for j in range(12):
            (ya, za), (yb, zb) = prof[j], prof[j + 1]
            b.hull([(x - 0.22, ya, za), (x + 0.22, ya, za), (x - 0.22, yb, zb), (x + 0.22, yb, zb),
                    (x - 0.22, ya, za - 0.55), (x + 0.22, ya, za - 0.55),
                    (x - 0.22, yb, zb - 0.55), (x + 0.22, yb, zb - 0.55)], C.M.steel_dark)
        if k < nrib:
            xn = ix0 + (ix1 - ix0) * (k + 1) / nrib
            for j in range(12):
                (ya, za), (yb, zb) = prof[j], prof[j + 1]
                b.quad((x, ya, za), (xn, ya, za), (xn, yb, zb), (x, yb, zb), C.M.glass_clear)
    objs.append(C.tag(b.build(f"{ID}_glass_vault"), "mass"))

    # ---- the rooftop sign frame on the north elevation -------------------------------------------------------------
    b = C.MeshBuilder()
    p0, p1, L, t, n = C.edge_facing(coords, 90.0)
    for k in range(9):
        q = p0 + t * (L * (k + 0.5) / 9)
        b.box((q[0] + n[0] * 1.2, q[1] + n[1] * 1.2, BRICK_TOP + SIGN_LETTER_H / 2 + 0.6),
              (0.3, 0.3, SIGN_LETTER_H + 1.2), C.M.steel_dark)
    b.box_from_to(p0, p1, n, 1.35, BRICK_TOP + 0.4, BRICK_TOP + 0.8, C.M.steel_dark)
    b.box_from_to(p0, p1, n, 1.35, BRICK_TOP + SIGN_LETTER_H + 0.6, BRICK_TOP + SIGN_LETTER_H + 1.0, C.M.steel_dark)
    objs.append(b.build(f"{ID}_sign_frame"))

    # ---- Domino Park: the Artifact Walk, the salvaged syrup tanks and the column line -----------------------------
    b = C.MeshBuilder()
    px0, py0, px1, py1 = P.bounds
    walk_x = px0 - 22.0
    b.box((walk_x, (py0 + py1) / 2, WALK_Z), (7.0, 137.0, 0.6), C.M.wood_dark)
    for k in range(21):                                        # the 21 salvaged columns and crane track
        y = (py0 + py1) / 2 - 137.0 / 2 + 137.0 * k / 20
        b.lathe([(0.45, 0.0), (0.45, WALK_Z), (0.7, WALK_Z + 0.4)], 10, C.M.rust, origin=(walk_x - 3.2, y, 0.0))
        b.lathe([(0.45, 0.0), (0.45, WALK_Z), (0.7, WALK_Z + 0.4)], 10, C.M.rust, origin=(walk_x + 3.2, y, 0.0))
    for k in range(TANKS):
        y = (py0 + py1) / 2 - 40.0 + 26.0 * k
        b.lathe([(TANK_D / 2, 0.0), (TANK_D / 2, TANK_H), (TANK_D / 2 * 0.7, TANK_H + 1.4), (0.0, TANK_H + 2.0)], 20,
                C.M.rust, origin=(walk_x - 12.0, y, 0.0), smooth=True)
    b.prism(C.ring_coords(C.rect_xy(px0 - 60.0, py0 - 20.0, px0 - 2.0, py1 + 20.0)), -0.02, 0.3, C.M.pavement)
    b.prism(C.ring_coords(C.rect_xy(px0 - 55.0, py0 - 10.0, px0 - 30.0, py1 + 10.0)), 0.3, 0.4, C.M.grass)
    objs.append(C.tag(b.build(f"{ID}_domino_park"), "park"))
    return objs, g


def main():
    objs, g = build()
    entry = cc.finish(objs, ID, g.frame, real_footprint=g.real_local,
                      fidelity_statement=(
                          "Exact: real OTI footprint of the landmarked Filter/Pan/Finishing House; the 155 ft = "
                          "47.2 m brick shell with round-arched bays on a 4.9 m module and corbelled floor "
                          "cornices; PAU's 2023 glass barrel vault set 3.0 m inside the shell and rising to "
                          "~200 ft = 60.0 m; the rooftop sign's steel frame; Domino Park's Artifact Walk at "
                          "9.1 m over 137 m with 21 salvaged columns and four 6.0 x 12.0 m syrup tanks. Inferred "
                          "(stated): the park's western extent (it lies outside the footprint; placed 60 m from the "
                          "building line), the bay module (measured from the polygon), and the tank positions. Not "
                          "modelled: the 'Domino Sugar' letters (frame only), interiors, the adjacent new towers, "
                          "the park planting."),
                      dimensions={"brick_top_m": BRICK_TOP, "vault_top_m": VAULT_TOP, "artifact_walk_z_m": WALK_Z,
                                  "syrup_tank_m": [TANK_D, TANK_H], "syrup_tanks": TANKS,
                                  "park_length_m": 137.0, "sign_letter_h_m": SIGN_LETTER_H})
    cc.render(ID, [
        {"view": "east_river", "azimuth_deg": 270, "elevation_deg": "street", "fov_deg": 55, "look_up_deg": 18},
        {"view": "aerial", "azimuth_deg": 250, "elevation_deg": 28},
    ])
    return entry


if __name__ == "__main__":
    main()
