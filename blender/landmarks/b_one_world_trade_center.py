"""One World Trade Center — 285 Fulton Street, Manhattan (BIN 1088469).  David Childs / SOM with Daniel Libeskind's
master plan; topped out 10 May 2013, opened 3 November 2014.  The tallest building in the Western Hemisphere.

Dimensions used (source in brackets)
------------------------------------
* **541.3 m (1,776 ft) to the tip of the spire**, **417.0 m (1,368 ft) to the roof/parapet** — the roof height is
  deliberately that of the original North Tower.  The spire is therefore **124.3 m** tall.  104 storeys
  [CTBUH, SOM, PANYNJ; both figures are named in the build brief].
* **Base: a 200 ft = 61.0 m square**, the same plan as the original North Tower.  The real OTI footprint (BIN
  1088469) measures **3,858 m2**, against 3,721 m2 for a true 61.0 m square — 3.7 % larger because the footprint
  includes the podium's entrance canopies; the podium is built on the **real footprint** and the tower shaft on the
  published square (stated).
* **Form: a chamfered square that becomes a regular octagon at mid-height and a 145 ft = 44.2 m square rotated 45
  degrees at the roof.**  The shaft is therefore eight flat isosceles triangles.  Interpolating the two plans
  linearly puts the perfect octagon at **58 % of the shaft height** — the published "midpoint" of the tower.
* **Podium**: 185 ft = **56.4 m** tall, a windowless reinforced-concrete cube clad (in the 2011 redesign) in
  vertical **prismatic glass fins** rather than the cancelled prismatic-glass panels.  This model builds 4 x 46 = 184
  fins at a 1.32 m pitch, each 0.55 m deep (fin count and pitch *inferred* from the 61 m face; the published figure
  is "about 4,000 prismatic glass panels" over the whole podium).
* **Spire**: a 124.3 m communications mast on a circular platform, with the cable-stayed ring at its base and a
  beacon at the tip.
* Curtain wall: about 13,000 panes of low-iron glass; modelled as a floor-band rhythm of 3.7 m storeys with a
  spandrel band, not as individual panes (stated gap).

Placement: the real OTI footprint for BIN **1088469** (centroid NYC_TM (-5338.11, 1446.55), LiDAR ground 1.524 m
NAVD88, LiDAR roof 430.80 m) from ``data/processed/buildings/landmark_footprints.parquet``.  The tower's principal
axis is taken from that footprint's minimum rotated rectangle, which is the World Trade Center site grid.

Not modelled: the individual curtain-wall panes and their mullion detail, the sky lobby and observatory interiors,
the 2 World Trade Center site to the north-east (a separate landmark), the below-grade PATH and retail concourses,
the spire's radome (removed from the design in 2012 — correctly absent), the window-washing rig, and the plaza
paving and bollards.
"""
from __future__ import annotations

import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import b_align as ba  # noqa: E402
import b_common as bc  # noqa: E402
import b_park_lib as pk  # noqa: E402
import nycsim_bpy as nb  # noqa: E402
from mathutils import Vector  # noqa: E402

ID = "b_one_world_trade_center"
TITLE = "One World Trade Center"
BINS = [1088469]

SPIRE_M = 541.3
ROOF_M = 417.0
BASE_SQ = 61.0            # 200 ft
TOP_SQ = 44.2             # 145 ft, rotated 45 degrees
PODIUM_M = 56.4           # 185 ft
FIN_PITCH = 1.32
FIN_DEPTH = 0.55
STOREY = 3.72             # (417.0 - 56.4) / 97 shaft storeys


def _plan(u: float, ground: float) -> list[tuple[float, float]]:
    """The eight-vertex plan at fraction ``u`` of the shaft height (0 = podium top, 1 = roof).

    Four vertices sit above the base square's corners and shrink to the top square's edge midpoints; the other four
    sit above the base square's edge midpoints and grow to the top square's corners.  At u = 0.58 the two radii are
    equal and the plan is a regular octagon.
    """
    r_corner = (BASE_SQ / 2) * math.sqrt(2.0)      # 43.13 m
    r_edge = BASE_SQ / 2                            # 30.50 m
    r_corner_top = TOP_SQ / 2                       # 22.10 m (top square's edge midpoint)
    r_edge_top = (TOP_SQ / 2) * math.sqrt(2.0)      # 31.25 m (top square's corner)
    rc = r_corner + (r_corner_top - r_corner) * u
    re = r_edge + (r_edge_top - r_edge) * u
    pts = []
    for k in range(8):
        a = math.pi / 4 * k
        r = rc if k % 2 == 1 else re
        pts.append((r * math.cos(a), r * math.sin(a)))
    _ = ground
    return pts


def build(lod: int = 0):
    fp = bc.load_footprint(BINS[0])
    heading = bc.footprint_heading(fp)
    frame = bc.local_frame(fp, fp.ground_z, heading)
    g = 0.0                                   # local z of the ground (frame z0 == LiDAR ground)
    ring_real = [(x - frame.x0, y - frame.y0) for x, y in fp.ring]
    rot = bc.rot_z(bc.heading_to_math_deg(heading) - 45.0)
    objs: list = []

    # ---- podium on the real footprint, with the prismatic glass fins ---------------------------------------------
    objs.append(bc.prism("podium", ring_real, g - 6.0, g + PODIUM_M, "concrete"))
    if lod == 0:
        fins = []
        half = BASE_SQ / 2
        n = int(BASE_SQ / FIN_PITCH)
        for side in range(4):
            for k in range(n):
                t = -half + (k + 0.5) * BASE_SQ / n
                p = [Vector((half + FIN_DEPTH / 2, t, 0)), Vector((-half - FIN_DEPTH / 2, t, 0)),
                     Vector((t, half + FIN_DEPTH / 2, 0)), Vector((t, -half - FIN_DEPTH / 2, 0))][side]
                fin = bc.box(f"fin{side}_{k}", (FIN_DEPTH, 0.30, PODIUM_M - 2.0), (p.x, p.y, g + 1.0), "glass_clear")
                bc.transform(fin, rot)
                fins.append(fin)
        objs.append(bc.join(fins, "podium_prismatic_fins"))
    objs.append(bc.prism("podium_cap", pk._offset_ring(_plan(0.0, g), 1.2), g + PODIUM_M, g + PODIUM_M + 1.4,
                         "steel_gray"))

    # ---- tower shaft: eight flat triangular facets ----------------------------------------------------------------
    n_st = 40 if lod == 0 else 8
    import bmesh
    bm = bmesh.new()
    prev = None
    shaft_h = ROOF_M - PODIUM_M
    for i in range(n_st + 1):
        u = i / n_st
        ring = [bm.verts.new(Vector((x, y, g + PODIUM_M + shaft_h * u))) for x, y in _plan(u, g)]
        if prev is not None:
            for k in range(8):
                bm.faces.new((prev[k], prev[(k + 1) % 8], ring[(k + 1) % 8], ring[k]))
        prev = ring
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    shaft = nb.bmesh_to_object("shaft", bm, materials=[bc.mat("glass")])
    bc.transform(shaft, rot)
    objs.append(shaft)
    # roof slab and parapet
    top = pk._offset_ring(_plan(1.0, g), 0.0)
    roof = bc.prism("roof", top, g + ROOF_M - 1.2, g + ROOF_M, "concrete_dark")
    bc.transform(roof, rot)
    objs.append(roof)
    par = nb.extrude_polygon("parapet", pk._offset_ring(top, 0.4), g + ROOF_M, g + ROOF_M + 1.5,
                             [list(reversed(pk._offset_ring(top, -0.2)))], material=bc.mat("steel_gray"))
    bc.transform(par, rot)
    objs.append(par)

    # ---- storey bands (spandrels) --------------------------------------------------------------------------------
    if lod == 0:
        bands = []
        n_floors = int(shaft_h / STOREY)
        for k in range(1, n_floors):
            u = k * STOREY / shaft_h
            ring = pk._offset_ring(_plan(u, g), 0.12)
            bands.append(bc.prism(f"band{k}", ring, g + PODIUM_M + k * STOREY - 0.55, g + PODIUM_M + k * STOREY,
                                  "steel_gray"))
        band = bc.join(bands, "spandrel_bands")
        bc.transform(band, rot)
        objs.append(band)

    # ---- spire ----------------------------------------------------------------------------------------------------
    spire_h = SPIRE_M - ROOF_M
    z0 = g + ROOF_M + 1.5
    objs.append(nb.cylinder("spire_platform", 9.0, 2.6, 16, (0, 0, z0), material=bc.mat("steel_gray")))
    objs.append(nb.cylinder("spire_ring", 6.4, 9.0, 16, (0, 0, z0 + 2.6), material=bc.mat("stainless")))
    mast = []
    n_seg = 8 if lod == 0 else 3
    for k in range(n_seg):
        u0, u1 = k / n_seg, (k + 1) / n_seg
        r0 = 1.55 * (1 - u0) + 0.32 * u0
        r1 = 1.55 * (1 - u1) + 0.32 * u1
        mast.append(bc.cylinder_between(f"spire_seg{k}", Vector((0, 0, z0 + 11.6 + (spire_h - 11.6) * u0)),
                                        Vector((0, 0, z0 + 11.6 + (spire_h - 11.6) * u1)), (r0 + r1) / 2,
                                        "stainless", 12 if lod == 0 else 6))
    objs.append(bc.join(mast, "spire_mast"))
    if lod == 0:
        stays = []
        for k in range(8):
            a = 2 * math.pi * k / 8
            stays.append(bc.cylinder_between(f"spire_stay{k}", Vector((6.2 * math.cos(a), 6.2 * math.sin(a), z0 + 2.6)),
                                             Vector((0.9 * math.cos(a), 0.9 * math.sin(a), z0 + 38.0)), 0.06,
                                             "stainless", 4))
        objs.append(bc.join(stays, "spire_stays"))
    objs.append(nb.cylinder("spire_beacon", 0.55, 2.2, 8, (0, 0, g + SPIRE_M - 2.2), material=bc.mat("light_warm")))

    extras = {
        "origin_tm": frame.origin_tm, "heading_deg": heading, "height_m": SPIRE_M, "name": TITLE,
        "roof_m": ROOF_M, "spire_m": SPIRE_M, "spire_length_m": SPIRE_M - ROOF_M, "podium_m": PODIUM_M,
        "base_square_m": BASE_SQ, "top_square_m": TOP_SQ, "octagon_at_fraction": 0.58, "storeys": 104,
        "footprint_area_m2": round(fp.geometry.area, 1), "footprint_source": fp.source,
        "height_source": "CTBUH/SOM/PANYNJ: 1,776 ft to the spire tip, 1,368 ft to the roof, 200 ft square base, "
                         "145 ft square top rotated 45 degrees, 185 ft podium",
        "sources_ids": ["building_footprints", "published_one_wtc"],
        "fidelity_statement": (
            "Exact to published values: 541.3 m to the spire tip, 417.0 m roof, 124.3 m spire, 56.4 m podium, a "
            "61.0 m square base chamfering into a regular octagon at 58 % of the shaft and a 44.2 m square rotated "
            "45 degrees at the roof (eight flat triangular facets, the real geometry), 104 storeys at 3.72 m, the "
            "podium on the real OTI footprint of BIN 1088469. Inferred: the podium fin count and 1.32 m pitch "
            "(published only as 'about 4,000 prismatic glass panels'), spire platform and stay-ring dimensions, "
            "spandrel band depth. Stated difference: the real footprint is 3,858 m2 against 3,721 m2 for a true "
            "61.0 m square, so the podium (real footprint) is 3.7 % larger in plan than the shaft (published "
            "square). Not modelled: individual curtain-wall panes and mullions, interiors, 2 WTC, the below-grade "
            "concourses, the cancelled spire radome, the window-washing rig, plaza paving."),
    }
    return objs, extras


def main() -> None:
    fp = bc.load_footprint(BINS[0])
    frame = bc.local_frame(fp, fp.ground_z, bc.footprint_heading(fp))
    ctx = (("ground_urban", 0.0, 900.0, (0.0, 0.0)),)
    ba.run_landmark(
        ID, TITLE, build, bins=BINS, budget_lod0=250_000, budget_lod1=50_000,
        renders=[
            # the comparison agent's recorded photographic viewpoint, used verbatim
            ba.reference_render("landmark_one_world_trade_center", frame, view="one_wtc_reference",
                                ground_z=0.0, target_z=280.0, fov_deg=62.0, size=(720, 1280), context=ctx,
                                sun_azimuth_deg=215.0, sun_elevation_deg=35.0),
            dict(view="west_street", cam=(-150.0, -40.0, 1.7), target=(0.0, 0.0, 210.0), fov_deg=70.0, context=ctx,
                 sun_azimuth_deg=200.0, sun_elevation_deg=45.0),
            dict(view="harbour", cam=(-1500.0, -2100.0, 60.0), target=(0.0, 0.0, 300.0), fov_deg=26.0, context=ctx,
                 sun_azimuth_deg=160.0, sun_elevation_deg=30.0),
            dict(view="podium", cam=(-95.0, -95.0, 12.0), target=(0.0, 0.0, 60.0), fov_deg=60.0, context=ctx,
                 sun_azimuth_deg=225.0, sun_elevation_deg=42.0),
        ],
        sections={"Placement": "real OTI footprint BIN 1088469, centroid NYC_TM (%.2f, %.2f), LiDAR ground %.3f m "
                               "NAVD88; principal axis %.2f deg (the World Trade Center site grid)."
                               % (frame.x0, frame.y0, fp.ground_z, bc.footprint_heading(fp)),
                  "Published dimensions": __doc__.split("------------------------------------\n")[1].split("\nPlacement:")[0].strip(),
                  "Not modelled": __doc__.split("Not modelled:")[1].strip()},
    )


if __name__ == "__main__":
    main()
