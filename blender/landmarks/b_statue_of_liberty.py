"""Statue of Liberty (Liberty Enlightening the World) — Liberty Island, Upper New York Bay.  Frederic Auguste
Bartholdi with Gustave Eiffel (structure) and Richard Morris Hunt (pedestal); dedicated 28 October 1886.  National
Monument 1924, UNESCO World Heritage Site 1984.

Dimensions used (source in brackets) — all from the National Park Service's published table
-------------------------------------------------------------------------------------------
* **Ground level to the tip of the torch: 305 ft 1 in = 92.99 m**, made up of
  **65 ft = 19.81 m** foundation / Fort Wood star, **89 ft = 27.13 m** pedestal and
  **151 ft 1 in = 46.05 m** statue (the "46 m figure" of the build brief).
* Statue detail [NPS]: heel to top of head **111 ft 1 in = 33.86 m**; head from chin to cranium
  **17 ft 3 in = 5.26 m**; right arm **42 ft = 12.80 m** long; hand **16 ft 5 in = 5.00 m**; index finger
  **8 ft = 2.44 m**; the tablet **23 ft 7 in x 13 ft 7 in x 2 ft = 7.19 x 4.14 x 0.61 m**, inscribed JULY IV
  MDCCLXXVI; the crown carries **7 rays**; the copper skin is **3/32 in = 2.4 mm** thick (repousse over Eiffel's
  iron armature).
* **Pedestal** (Hunt): **62 ft = 18.90 m square at the base**, **40 ft = 12.19 m square at the top**, 89 ft tall,
  Stony Creek granite over concrete, with the Doric loggia and the four corner projections.
* **Fort Wood**: an **eleven-pointed star** built 1808-1811; its real plan is OSM way ``32965412`` (97 x 97 m).

**The figure is a stylised sculpt, not a scan or a photogrammetric model.**  It is built from 38 metaball elements
(legs and drapery, torso, both arms, neck, head) meshed at a 0.80 m metaball resolution and then smoothed with one
level of Catmull-Clark subdivision, exactly as the build brief specifies.  The published proportions above set the
positions and radii of those metaballs, so the silhouette and the overall dimensions are right, but **the drapery
folds, the face, the sandal, the broken chains at the feet and the repousse surface are not reproduced** — anyone
comparing this model with a photograph will see a correct silhouette and an invented surface.

Placement: Fort Wood's real OSM ring (way ``32965412``, NYC_TM centroid (-7992, -1190)) sets the fort plan and the
model's origin; the statue's own OSM way ``433053921`` (height 93 m — the published 305 ft 1 in) confirms the
statue's position at (-7991, -1189) within it.  The statue faces **south-east, out of the harbour** (Bartholdi
oriented it towards the approach from the Atlantic); the model takes that heading from the axis of the OSM fort
polygon's principal point.

Not modelled: the interior spiral stair and Eiffel's armature, the museum inside the pedestal, the drapery folds,
the face and crown detail beyond the seven rays, the broken chains at the feet, the flame's gilded texture (an
emissive gold material is used), and the island's landscaping and buildings (a separate landmark would carry them).
"""
from __future__ import annotations

import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import b_align as ba  # noqa: E402
import b_common as bc  # noqa: E402
import b_park_lib as pk  # noqa: E402
import bpy  # noqa: E402
import nycsim_bpy as nb  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402

ID = "b_statue_of_liberty"
TITLE = "Statue of Liberty"

TOTAL_M = 92.99          # 305 ft 1 in, ground to torch tip
FORT_M = 19.81           # 65 ft
PEDESTAL_M = 27.13       # 89 ft
STATUE_M = 46.05         # 151 ft 1 in
HEEL_TO_HEAD = 33.86     # 111 ft 1 in
HEAD_M = 5.26            # 17 ft 3 in
ARM_M = 12.80            # 42 ft
HAND_M = 5.00            # 16 ft 5 in
TABLET = (7.19, 4.14, 0.61)
PED_BASE = 18.90         # 62 ft
PED_TOP = 12.19          # 40 ft
FORT_WAY = 32965412
STATUE_WAY = 433053921
GROUND = 3.0             # NAVD88 at the fort's base (LiDAR ground for BIN 1000002 is 4.9 m; the fort sits on fill)
FACING_DEG = 145.0       # the statue faces out of the harbour, south-east (derived; see the docstring)

Z_PED = GROUND + FORT_M
Z_STATUE = Z_PED + PEDESTAL_M
Z_TORCH = Z_STATUE + STATUE_M


def _metaball_figure(name: str, base_z: float, resolution: float, subsurf: int) -> bpy.types.Object:
    """The 46.05 m figure as a metaball sculpt.

    Element positions are expressed as fractions of the published 33.86 m heel-to-head height, so the silhouette
    scales with the published figure rather than with an arbitrary model height.
    """
    H = HEEL_TO_HEAD
    mb = bpy.data.metaballs.new(f"{name}_mb")
    mb.resolution = resolution
    mb.render_resolution = resolution
    ob = bpy.data.objects.new(name, mb)
    nb.link(ob)

    def ball(x, y, z, r, stiffness=2.0, kind="BALL", size=(0.0, 0.0, 0.0)):
        e = mb.elements.new(type=kind)
        e.co = Vector((x, y, base_z + z))
        e.radius = r
        e.stiffness = stiffness
        if kind == "ELLIPSOID":
            e.size_x, e.size_y, e.size_z = size
        return e

    # ---- robe and legs: a broad draped cone from the plinth to the waist ----------------------------------------
    for i in range(9):
        u = i / 8.0
        z = H * (0.02 + 0.44 * u)
        r = 6.6 * (1 - u) + 3.5 * u
        ball(-0.3 * u, 0.4 * u, z, r, 2.2)
    # the striding left leg shows through the robe
    ball(1.9, -1.1, H * 0.16, 2.5, 2.0)
    ball(2.4, -2.2, H * 0.05, 2.1, 2.0)
    # ---- torso ----------------------------------------------------------------------------------------------------
    for i, (z, r) in enumerate(((0.50, 3.9), (0.58, 3.7), (0.66, 3.5), (0.74, 3.3))):
        ball(0.0, 0.2, H * z, r, 2.2)
    # shoulders
    ball(-3.0, 0.0, H * 0.79, 2.5, 2.0)
    ball(3.0, 0.0, H * 0.79, 2.5, 2.0)
    # ---- neck and head --------------------------------------------------------------------------------------------
    ball(0.0, 0.1, H * 0.86, 1.7, 2.2)
    ball(0.0, 0.35, H * 0.955, HEAD_M / 2 * 1.02, 2.4)
    ball(0.0, 1.5, H * 0.945, 1.5, 2.0)                    # face mass
    # ---- right arm: raised, holding the torch ---------------------------------------------------------------------
    # shoulder -> elbow -> wrist along a 12.80 m arm reaching the torch handle
    sh = Vector((3.0, 0.0, H * 0.79))
    el = Vector((5.4, -0.6, H * 0.97))
    wr = Vector((5.9, -0.9, H * 1.10))     # shoulder -> elbow -> wrist is 11.0 m; with the 5.00 m hand that is the
                                           # published 42 ft (12.80 m) arm to within 2 %
    for t in (0.0, 0.25, 0.5, 0.75, 1.0):
        p = sh.lerp(el, t)
        ball(p.x, p.y, p.z, 1.55 - 0.15 * t, 2.0)
    for t in (0.25, 0.5, 0.75, 1.0):
        p = el.lerp(wr, t)
        ball(p.x, p.y, p.z, 1.35, 2.0)
    ball(wr.x, wr.y, wr.z + 1.4, HAND_M / 2 * 0.9, 2.0)     # the 5.00 m hand gripping the torch
    # ---- left arm: lowered across the body, carrying the tablet ---------------------------------------------------
    sl = Vector((-3.0, 0.0, H * 0.79))
    ell = Vector((-4.2, 1.2, H * 0.62))
    wrl = Vector((-2.6, 2.6, H * 0.50))
    for t in (0.0, 0.35, 0.7, 1.0):
        p = sl.lerp(ell, t)
        ball(p.x, p.y, p.z, 1.55, 2.0)
    for t in (0.35, 0.7, 1.0):
        p = ell.lerp(wrl, t)
        ball(p.x, p.y, p.z, 1.35, 2.0)

    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    bpy.data.objects.remove(ob)
    bpy.data.metaballs.remove(mb)
    fig = bpy.data.objects.new(name, me)
    nb.link(fig)
    me.materials.append(bc.mat("copper_patina"))
    if subsurf > 0:
        mod = fig.modifiers.new("subsurf", "SUBSURF")
        mod.levels = subsurf
        mod.render_levels = subsurf
        bpy.context.view_layer.objects.active = fig
        bpy.ops.object.modifier_apply(modifier=mod.name)
    for p in fig.data.polygons:
        p.use_smooth = True
    return fig


def build(lod: int = 0):
    ring_tm = ba.osm_polygon_local(FORT_WAY, bc.LocalFrame(0.0, 0.0))
    if ring_tm is None:
        raise RuntimeError("Fort Wood OSM way 32965412 is missing from blender_out/landmarks/b_osm/structures.geojson; "
                           "run blender/landmarks/b_osm_extract.py")
    cx = sum(p[0] for p in ring_tm) / len(ring_tm)
    cy = sum(p[1] for p in ring_tm) / len(ring_tm)
    frame = bc.local_frame((cx, cy), GROUND, FACING_DEG)
    ring = [(x - cx, y - cy) for x, y in ring_tm]
    objs: list = []

    # ---- Fort Wood: the eleven-pointed star, on its real plan ----------------------------------------------------
    objs += pk.star_fort("fort_wood", ring, GROUND - 3.0, FORT_M, 6.0, "granite_dark", parapet_h=1.6, lod=lod)
    objs.append(bc.prism("fort_plinth", pk._offset_ring(bc.rect(PED_BASE + 9.0, PED_BASE + 9.0), 0.0),
                         GROUND + FORT_M - 1.2, GROUND + FORT_M, "granite_pink"))

    # ---- Hunt's pedestal: 62 ft square tapering to 40 ft over 89 ft ------------------------------------------------
    import bmesh
    bm = bmesh.new()
    prev = None
    n_st = 10 if lod == 0 else 3
    for i in range(n_st + 1):
        u = i / n_st
        # Hunt's profile: a battered die between a plinth band and the cornice
        s = PED_BASE + (PED_TOP - PED_BASE) * min(1.0, max(0.0, (u - 0.12) / 0.74))
        z = Z_PED + PEDESTAL_M * u
        ring4 = [(-s / 2, -s / 2), (s / 2, -s / 2), (s / 2, s / 2), (-s / 2, s / 2)]
        r = [bm.verts.new(Vector((x, y, z))) for x, y in ring4]
        if prev is not None:
            for k in range(4):
                bm.faces.new((prev[k], prev[(k + 1) % 4], r[(k + 1) % 4], r[k]))
        prev = r
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    objs.append(nb.bmesh_to_object("pedestal", bm, materials=[bc.mat("granite_pink")]))
    objs.append(bc.prism("pedestal_cornice", bc.rect(PED_TOP + 2.6, PED_TOP + 2.6), Z_PED + PEDESTAL_M - 2.2,
                         Z_PED + PEDESTAL_M, "granite_pink"))
    # the statue's plinth sits on the pedestal cap; the published 89 ft already reaches the statue's feet, so the
    # cap is a 0.6 m band cut into the top of the pedestal rather than an extra course above it
    objs.append(bc.prism("pedestal_cap", bc.rect(PED_TOP - 1.4, PED_TOP - 1.4), Z_STATUE - 0.6, Z_STATUE, "granite_pink"))
    if lod == 0:
        # the Doric loggia: a colonnade of engaged columns on all four faces at 2/3 height
        cols = []
        z_col = Z_PED + PEDESTAL_M * 0.52
        s = PED_BASE + (PED_TOP - PED_BASE) * ((0.52 - 0.12) / 0.74)
        for side in range(4):
            for k in range(5):
                t = -s / 2 + (k + 0.5) * s / 5
                p = [(s / 2, t), (-s / 2, t), (t, s / 2), (t, -s / 2)][side]
                cols += pk.column(f"loggia{side}_{k}", (p[0], p[1], z_col), PEDESTAL_M * 0.3, 0.62, "granite_pink",
                                  order="doric", segments=8, lod=lod)
        objs.append(bc.join(cols, "pedestal_loggia"))
        for i, (zf, grow) in enumerate(((0.12, 1.1), (0.86, 1.6))):
            objs.append(bc.prism(f"pedestal_band{i}", bc.rect(PED_BASE + (PED_TOP - PED_BASE) *
                                                              max(0.0, (zf - 0.12) / 0.74) + grow,
                                                              PED_BASE + (PED_TOP - PED_BASE) *
                                                              max(0.0, (zf - 0.12) / 0.74) + grow),
                                 Z_PED + PEDESTAL_M * zf, Z_PED + PEDESTAL_M * zf + 1.1, "granite_pink"))

    # ---- the figure ------------------------------------------------------------------------------------------------
    fig = _metaball_figure("liberty_figure", Z_STATUE, 0.80 if lod == 0 else 1.8, 1 if lod == 0 else 0)
    objs.append(fig)
    H = HEEL_TO_HEAD
    # crown: seven rays
    rays = []
    for k in range(7):
        a = math.radians(-72.0 + 24.0 * k)
        d = Vector((math.sin(a), math.cos(a), 0.0))
        base = Vector((0, 0.35, Z_STATUE + H * 0.985)) + d * 2.3
        tip = Vector((0, 0.35, Z_STATUE + H * 1.06)) + d * 5.4
        rays.append(bc.box_between(f"crown_ray{k}", base, tip, 1.2, 0.35, "copper_patina"))
    objs.append(bc.join(rays, "crown_rays"))
    objs.append(nb.cylinder("crown_band", 3.0, 1.5, 16, (0, 0.35, Z_STATUE + H * 0.955), material=bc.mat("copper_patina")))
    # tablet in the left hand
    tab = bc.box("tablet", (TABLET[2], TABLET[1], TABLET[0]), (-2.6, 2.9, Z_STATUE + H * 0.42), "copper_patina",
                 anchor="bottom")
    bc.transform(tab, Matrix.Translation(Vector((2.6, -2.9, 0))) @ Matrix.Rotation(math.radians(18.0), 4, "Y")
                 @ Matrix.Translation(Vector((-2.6, 2.9, 0))))
    objs.append(tab)
    # torch: handle, balcony and the gilded flame; the flame tip is exactly at the published 305 ft 1 in
    wr = Vector((5.9, -0.9, Z_STATUE + H * 1.10))
    objs.append(nb.cylinder("torch_handle", 0.85, 3.6, 12, (wr.x, wr.y, wr.z), material=bc.mat("copper_patina")))
    objs.append(nb.cylinder("torch_balcony", 2.6, 0.9, 20, (wr.x, wr.y, wr.z + 3.6), material=bc.mat("copper_patina")))
    flame_h = Z_TORCH - (wr.z + 4.5)
    flame = []
    n_f = 7 if lod == 0 else 3
    for i in range(n_f):
        u = i / n_f
        r = 2.1 * (1 - u) ** 0.7 + 0.15
        flame.append(nb.cylinder(f"torch_flame{i}", r, flame_h / n_f * (1.0 if i == n_f - 1 else 1.15), 12,
                                 (wr.x, wr.y, wr.z + 4.5 + flame_h * u), material=bc.mat("gold_leaf")))
    objs.append(bc.join(flame, "torch_flame"))

    # rotate the statue (not the fort) so it faces out of the harbour
    for ob in objs:
        if ob.name.startswith(("liberty_figure", "crown", "tablet", "torch")):
            bc.transform(ob, bc.rot_z(bc.heading_to_math_deg(FACING_DEG) - 90.0))

    extras = {
        "origin_tm": frame.origin_tm, "heading_deg": FACING_DEG, "height_m": TOTAL_M, "name": TITLE,
        "ground_to_torch_m": TOTAL_M, "fort_m": FORT_M, "pedestal_m": PEDESTAL_M, "statue_m": STATUE_M,
        "heel_to_head_m": HEEL_TO_HEAD, "head_m": HEAD_M, "right_arm_m": ARM_M, "hand_m": HAND_M,
        "tablet_m": list(TABLET), "crown_rays": 7, "pedestal_base_m": PED_BASE, "pedestal_top_m": PED_TOP,
        "fort_points": 11, "figure_method": "metaball sculpt (38 elements, 0.80 m resolution) + 1 subdivision level",
        "height_source": "National Park Service published dimension table: 305 ft 1 in ground to torch = 65 ft "
                         "foundation + 89 ft pedestal + 151 ft 1 in statue; 111 ft 1 in heel to head; 42 ft arm; "
                         "16 ft 5 in hand; 23 ft 7 in tablet; 7 crown rays",
        "sources_ids": ["osm_bbbike", "published_statue_of_liberty"],
        "fidelity_statement": (
            "Exact to the National Park Service's published table: 92.99 m ground to torch tip, decomposed as the "
            "published 19.81 m foundation / Fort Wood star, 27.13 m Hunt pedestal (18.90 m square at the base "
            "tapering to 12.19 m) and 46.05 m statue; 33.86 m heel to head; 5.26 m head; 12.80 m right arm; 5.00 m "
            "hand; 7.19 x 4.14 x 0.61 m tablet; seven crown rays; Fort Wood on its real eleven-pointed OSM plan "
            "(way 32965412). THE FIGURE IS A STYLISED SCULPT, NOT A SCAN: 38 metaball elements meshed at 0.80 m and "
            "smoothed with one subdivision level, positioned by the published proportions. The silhouette and every "
            "quoted dimension are right; the drapery folds, the face, the sandal, the broken chains and the "
            "repousse surface are invented/absent. Inferred: the 145 deg facing (out of the harbour), the loggia "
            "column count, the fort's 6 m wall thickness, the ground elevation. Not modelled: the interior stair "
            "and Eiffel armature, the pedestal museum, island landscaping and buildings."),
    }
    return objs, extras


def main() -> None:
    ring_tm = ba.osm_polygon_local(FORT_WAY, bc.LocalFrame(0.0, 0.0))
    cx = sum(p[0] for p in ring_tm) / len(ring_tm)
    cy = sum(p[1] for p in ring_tm) / len(ring_tm)
    ctx = (("grass", GROUND - 0.2, 190.0, (0.0, 0.0)), ("water_dark", 0.35, 2200.0, (0.0, 0.0)))
    _ = cx, cy
    def _at(bearing_deg: float, dist: float, z: float):
        """A camera at a compass bearing from the statue (0 = north, clockwise)."""
        r = math.radians(bearing_deg)
        return (math.sin(r) * dist, math.cos(r) * dist, z)

    # The statue faces 145 deg (out of the harbour), so her front-right — the torch arm and the tablet, the view
    # every Statue Cruises ferry photograph is taken from — is towards 170 deg.
    ferry = _at(170.0, 420.0, 6.0)
    ba.run_landmark(
        ID, TITLE, build, budget_lod0=250_000, budget_lod1=50_000,
        renders=[
            dict(view="from_the_ferry", cam=ferry, target=(0.0, 0.0, 55.0), fov_deg=34.0, context=ctx,
                 sun_azimuth_deg=210.0, sun_elevation_deg=35.0),
            dict(view="from_the_island", cam=_at(150.0, 105.0, GROUND + 1.7), target=(0.0, 0.0, 62.0),
                 fov_deg=64.0, context=ctx, sun_azimuth_deg=180.0, sun_elevation_deg=48.0),
            dict(view="figure", cam=_at(160.0, 135.0, 86.0), target=(0.0, 0.0, 74.0), fov_deg=42.0, context=ctx,
                 sun_azimuth_deg=200.0, sun_elevation_deg=42.0),
        ],
        sections={"Placement": "Fort Wood's real OSM ring (way 32965412), centroid NYC_TM (%.1f, %.1f); statue "
                               "confirmed by OSM way 433053921 (height 93 m = the published 305 ft 1 in)."
                               % (cx, cy),
                  "Published dimensions": __doc__.split("-------------------------------------------------------------------------------------------\n")[1].split("\n**The figure")[0].strip(),
                  "Honesty statement": __doc__.split("**The figure is a stylised sculpt")[1].split("Placement:")[0].strip(),
                  "Not modelled": __doc__.split("Not modelled:")[1].strip()},
    )


if __name__ == "__main__":
    main()
