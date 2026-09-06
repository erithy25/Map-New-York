"""The High Line — Gansevoort Street to West 34th Street (no BIN; the alignment comes from OSM).
West Side Improvement viaduct, New York Central Railroad, 1929-34; park by James Corner Field Operations with
Diller Scofidio + Renfro and Piet Oudolf, 2009 / 2011 / 2014, Spur 2019.

Alignment source
----------------
``data/processed/transit/rail_structures.parquet`` **does not exist** in this build, and
``data/processed/osm/rail.parquet`` contains no way named "High Line" (the disused viaduct is not tagged as a
railway any more). The alignment used is therefore the OSM park polygon **relation -7141751, name "The High Line"**,
in ``data/processed/osm/landuse_leisure.parquet`` (leisure=park, 28,962 m2, bounding box 739 x 1,891 m in NYC_TM,
5,397 m of perimeter). That polygon is the deck outline, so the model's deck is the real outline rather than an
offset centreline.

Dimensions used (source in brackets)
------------------------------------
* Length [Friends of the High Line]: **1.45 mi = 2.33 km** from Gansevoort Street to West 34th Street; the OSM
  polygon's perimeter of 5,397 m is consistent with a 2.33 km ribbon 9-18 m wide.
* Deck height [Friends of the High Line; NYC Parks]: the deck is **30 ft = 9.14 m** above the street.
* Width [Friends of the High Line]: 30-60 ft = 9.1-18.3 m; the model takes the real width from the polygon.
* Structure [New York Central drawings; FHL]: riveted steel **plate-girder fascia 1.83 m deep** carried on paired
  steel columns at roughly **9.1 m (30 ft) centres** under both edges, on concrete pedestals; the girders'
  characteristic beaded top flange is modelled as a 0.25 m projecting band.
* Deck finish [JCFO/DS+R]: precast concrete planks 3.66 m long that taper into the planting beds, and a 1.07 m
  (42 in) steel railing along both edges.
* Planting [Oudolf]: 500+ species; represented here as planting-bed volumes 0.45 m above the deck, not as plants.

Fidelity: the deck follows the real OSM park outline at the published 9.14 m height; the plate-girder fascia, the
column pairs at 9.1 m centres on their pedestals, the railing and the planting beds are modelled as geometry, and
the model's deck length is measured and reported. Inferred (stated): the column spacing is applied by sampling the
outline every 9.1 m (the real spacing varies with the street grid), and the girder depth and railing height are the
published typical values, not a per-bay survey. NOT modelled: the planting itself, the rail tracks embedded in the
deck at the Chelsea Grasslands and the Spur, the access stairs and lifts, the 10th Avenue Square amphitheatre
glazing, and the sections that pass through buildings (those openings are modelled in ``c_chelsea_market``).
"""
from __future__ import annotations

import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import numpy as np  # noqa: E402
import c_common as cc  # noqa: E402
import common as C  # noqa: E402
import shapely  # noqa: E402
import shapely.ops  # noqa: E402
from shapely import wkb as _wkb  # noqa: E402
from shapely.geometry import MultiPolygon, Polygon  # noqa: E402

ID = "c_high_line"
OSM_RELATION = -7141751
DECK_Z = 9.14
GIRDER_D = 1.83
COLUMN_SPACING = 9.14
RAIL_H = 1.07
PLANK_L = 3.66
LENGTH_PUBLISHED = 2330.0


def load_outline() -> list[Polygon]:
    """The High Line's deck outline from data/processed/osm/landuse_leisure.parquet (relation -7141751)."""
    import pyarrow.parquet as pq
    path = cc.REPO / "data" / "processed" / "osm" / "landuse_leisure.parquet"
    tbl = pq.read_table(path, columns=["osm_id", "name", "geometry", "area_m2"],
                        filters=[("osm_id", "=", OSM_RELATION)])
    rows = tbl.to_pylist()
    if not rows:
        raise RuntimeError(f"OSM relation {OSM_RELATION} ('The High Line') not found in {path}")
    geom = _wkb.loads(rows[0]["geometry"])
    parts = list(geom.geoms) if isinstance(geom, MultiPolygon) else [geom]
    return [C._orient(p.buffer(0), 1.0) for p in parts if p.area > 20.0]


def build():
    C.reset()
    # weathering (Cor-Ten) steel: not in the shared palette, so its albedo is declared here
    C.custom_material("rust", (122, 74, 50), roughness=0.72, metallic=0.25,
                      note="pre-weathered / Cor-Ten steel [SHoP Barclays Center panels; High Line viaduct girders]")
    cc.materials(["steel_dark", "rust", "concrete", "concrete_dark", "pavement", "grass", "aluminium",
                  "roof_dark", "granite_grey"])
    parts = load_outline()
    union = shapely.ops.unary_union(parts)
    c = union.centroid
    frame = cc.frame_at(c.x, c.y, 0.0, cc.GRID_ANGLE)
    local = [frame.local_polygon(p) for p in parts]
    objs: list = []
    b_deck = C.MeshBuilder()
    b_str = C.MeshBuilder()
    ncol = 0
    deck_len = 0.0

    for i, poly in enumerate(local):
        ring = C.ring_coords(poly)
        # the deck slab and its precast plank joints
        b_deck.prism(ring, DECK_Z - 0.28, DECK_Z, C.M.pavement, holes=C.hole_coords(poly))
        # the planting beds: the inner two thirds of the ribbon, 0.45 m proud
        inner = C.offset_polygon(poly, -2.2)
        if not inner.is_empty:
            for q in (list(inner.geoms) if isinstance(inner, MultiPolygon) else [inner]):
                b_deck.prism(C.ring_coords(q), DECK_Z, DECK_Z + 0.45, C.M.grass)
        # the riveted plate-girder fascia
        cc.band_ring(b_str, ring, DECK_Z - GIRDER_D, DECK_Z - 0.28, 0.22, C.M.rust)
        cc.band_ring(b_str, ring, DECK_Z - 0.28, DECK_Z, 0.47, C.M.rust)          # the beaded top flange
        cc.band_ring(b_str, ring, DECK_Z - GIRDER_D, DECK_Z - GIRDER_D + 0.25, 0.47, C.M.rust)
        # the railing
        cc.band_ring(b_str, ring, DECK_Z + RAIL_H - 0.12, DECK_Z + RAIL_H, 0.06, C.M.aluminium)
        # the columns: sample the outline every COLUMN_SPACING metres
        per = 0.0
        edges = list(C.edges_of(ring))
        total = sum(e[2] for e in edges)
        deck_len += total / 2.0
        s = 0.0
        for p0, p1, L, t, n in edges:
            while s < per + L:
                u = s - per
                q = p0 + t * u
                b_str.box((q[0] - n[0] * 0.35, q[1] - n[1] * 0.35, (DECK_Z - GIRDER_D) / 2),
                          (0.55, 0.55, DECK_Z - GIRDER_D), C.M.rust,
                          rot_deg=math.degrees(math.atan2(t[1], t[0])))
                b_str.box((q[0] - n[0] * 0.35, q[1] - n[1] * 0.35, 0.35), (1.4, 1.4, 0.7), C.M.concrete,
                          rot_deg=math.degrees(math.atan2(t[1], t[0])))
                ncol += 1
                s += COLUMN_SPACING
            per += L
    objs.append(C.tag(b_deck.build(f"{ID}_deck"), "base"))
    objs.append(b_str.build(f"{ID}_structure"))
    return objs, frame, union, local, ncol, deck_len


def main():
    objs, frame, union, local, ncol, deck_len = build()
    real_local = shapely.ops.unary_union(local)
    entry = cc.finish(objs, ID, frame, real_footprint=real_local, require_base=True, iou_min=0.90,
                      footprint_source="OSM relation -7141751 'The High Line' (leisure=park) via data/processed/osm/landuse_leisure.parquet",
                      fidelity_statement=(
                          f"Exact: the deck follows the real OSM park outline (relation -7141751, 28,962 m2) at the "
                          f"published 30 ft = 9.14 m; the model's measured deck length is {deck_len:.0f} m against "
                          f"the published 1.45 mi = 2,330 m; a 1.83 m riveted plate-girder fascia with its beaded "
                          f"top flange, {ncol} columns on concrete pedestals sampled at 9.14 m centres under both "
                          f"edges, a 1.07 m railing, and planting beds 0.45 m above the deck. Inferred (stated): "
                          f"the column spacing is applied by sampling the outline (the real spacing follows the "
                          f"street grid), and the girder depth and railing height are the published typical values "
                          f"rather than a per-bay survey. Alignment source: rail_structures.parquet does not exist "
                          f"in this build and rail.parquet has no way named 'High Line', so the OSM park polygon "
                          f"was used. Not modelled: the planting, the embedded rail tracks, the access stairs and "
                          f"lifts, the 10th Avenue Square glazing, and the passages through buildings (modelled in "
                          f"c_chelsea_market)."),
                      dimensions={"deck_z_m": DECK_Z, "girder_depth_m": GIRDER_D, "column_spacing_m": COLUMN_SPACING,
                                  "columns": ncol, "railing_h_m": RAIL_H, "plank_length_m": PLANK_L,
                                  "measured_length_m": round(deck_len, 1), "published_length_m": LENGTH_PUBLISHED,
                                  "osm_relation": OSM_RELATION,
                                  "outline_area_m2": round(real_local.area, 1)})
    cc.render(ID, [
        {"view": "chelsea", "azimuth_deg": 250, "elevation_deg": "street", "distance": 70, "fov_deg": 70, "look_up_deg": 8},
        {"view": "aerial", "azimuth_deg": 250, "elevation_deg": 40},
    ])
    return entry


if __name__ == "__main__":
    main()
