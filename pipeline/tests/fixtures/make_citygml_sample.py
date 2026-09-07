"""Generate pipeline/tests/fixtures/citygml_sample.gml: a small synthetic CityGML 2.0 file.

Coordinates are EPSG:2263 US survey feet near Howard Beach, Queens; z is feet NAVD88, matching the
real DA_WISE delivery. The file deliberately contains shapes the real NYC delivery does NOT contain
(gable, hip, shed) so the roof classifier is exercised end-to-end.
"""
from __future__ import annotations

import math
from pathlib import Path

OUT = Path(__file__).resolve().parent / "citygml_sample.gml"
X0, Y0 = 1032000.0, 180000.0
SRS = "EPSG:2263"


def ring(pts):
    txt = " ".join(f"{v:.4f}" for p in pts for v in p)
    return ('<gml:surfaceMember><gml:Polygon><gml:exterior><gml:LinearRing>'
            f'<gml:posList srsDimension="3">{txt}</gml:posList>'
            '</gml:LinearRing></gml:exterior></gml:Polygon></gml:surfaceMember>')


def ring_with_hole(outer, holes):
    def pl(p):
        return f'<gml:posList srsDimension="3">{" ".join(f"{v:.4f}" for q in p for v in q)}</gml:posList>'
    s = ('<gml:surfaceMember><gml:Polygon><gml:exterior><gml:LinearRing>' + pl(outer) +
         '</gml:LinearRing></gml:exterior>')
    for h in holes:
        s += '<gml:interior><gml:LinearRing>' + pl(h) + '</gml:LinearRing></gml:interior>'
    return s + '</gml:Polygon></gml:surfaceMember>'


def close(p):
    return list(p) + [p[0]]


def surface(kind, members):
    return (f'<bldg:boundedBy><bldg:{kind}><bldg:lod2MultiSurface><gml:MultiSurface srsName="{SRS}">'
            + "".join(members) + '</gml:MultiSurface></bldg:lod2MultiSurface></bldg:' + kind + '></bldg:boundedBy>')


def rect(cx, cy, w, d, rot=0.0):
    """Footprint rectangle, counter-clockwise seen from above."""
    c, s = math.cos(rot), math.sin(rot)
    out = []
    for dx, dy in ((-w / 2, -d / 2), (w / 2, -d / 2), (w / 2, d / 2), (-w / 2, d / 2)):
        out.append((cx + dx * c - dy * s, cy + dx * s + dy * c))
    return out


def walls(plan, z0, z_top):
    """Vertical wall quads for a CCW plan; ``z_top`` is a value or a callable of the vertex index."""
    ms = []
    n = len(plan)
    for i in range(n):
        a, b = plan[i], plan[(i + 1) % n]
        za = z_top(i) if callable(z_top) else z_top
        zb = z_top((i + 1) % n) if callable(z_top) else z_top
        ms.append(ring(close([(a[0], a[1], z0), (b[0], b[1], z0), (b[0], b[1], zb), (a[0], a[1], za)])))
    return ms


def ground(plan, z):
    return [ring(close([(x, y, z) for x, y in reversed(plan)]))]   # CW from above => normal down


def building(gml_id, bin_str, parts, doitt=None):
    attrs = ""
    if bin_str is not None:
        attrs += ('<gen:stringAttribute name="BIN"><gen:value>%s</gen:value></gen:stringAttribute>' % bin_str)
    if doitt is not None:
        attrs += ('<gen:stringAttribute name="DOITT_ID"><gen:value>%s</gen:value></gen:stringAttribute>' % doitt)
    return (f'<cityObjectMember><bldg:Building gml:id="{gml_id}">' + attrs + "".join(parts) + "</bldg:Building></cityObjectMember>")


parts_all = []

# 1. flat box, BIN 4000001 (also appears again below as a duplicate BIN to exercise the merge)
plan = rect(X0, Y0, 30, 50)
parts_all.append(building("b_flat", "4000001", [
    surface("GroundSurface", ground(plan, 10.0)),
    surface("WallSurface", walls(plan, 10.0, 40.0)),
    surface("RoofSurface", [ring(close([(x, y, 40.0) for x, y in plan]))]),
], doitt="900001"))

# 2. gable: ridge along the +x (long) axis, eaves at 30 ft, ridge at 45 ft
w, d = 40.0, 24.0
cx, cy = X0 + 200.0, Y0
plan = rect(cx, cy, w, d)
p00, p10, p11, p01 = plan
r0 = (cx - w / 2, cy, 45.0)
r1 = (cx + w / 2, cy, 45.0)
parts_all.append(building("b_gable", "4000002", [
    surface("GroundSurface", ground(plan, 10.0)),
    surface("WallSurface", [
        ring(close([(p00[0], p00[1], 10.0), (p10[0], p10[1], 10.0), (p10[0], p10[1], 30.0), (p00[0], p00[1], 30.0)])),
        ring(close([(p10[0], p10[1], 10.0), (p11[0], p11[1], 10.0), (p11[0], p11[1], 30.0), r1, (p10[0], p10[1], 30.0)])),
        ring(close([(p11[0], p11[1], 10.0), (p01[0], p01[1], 10.0), (p01[0], p01[1], 30.0), (p11[0], p11[1], 30.0)])),
        ring(close([(p01[0], p01[1], 10.0), (p00[0], p00[1], 10.0), (p00[0], p00[1], 30.0), r0, (p01[0], p01[1], 30.0)])),
    ]),
    surface("RoofSurface", [
        ring(close([(p00[0], p00[1], 30.0), (p10[0], p10[1], 30.0), r1, r0])),
        ring(close([(p11[0], p11[1], 30.0), (p01[0], p01[1], 30.0), r0, r1])),
    ]),
], doitt="900002"))

# 3. hip: square plan, four faces meeting on a short ridge
s = 34.0
cx, cy = X0 + 400.0, Y0
plan = rect(cx, cy, s, s)
p00, p10, p11, p01 = plan
h0 = (cx - 6.0, cy, 46.0)
h1 = (cx + 6.0, cy, 46.0)
parts_all.append(building("b_hip", "4000003", [
    surface("GroundSurface", ground(plan, 10.0)),
    surface("WallSurface", walls(plan, 10.0, 32.0)),
    surface("RoofSurface", [
        ring(close([(p00[0], p00[1], 32.0), (p10[0], p10[1], 32.0), h1, h0])),
        ring(close([(p10[0], p10[1], 32.0), (p11[0], p11[1], 32.0), h1])),
        ring(close([(p11[0], p11[1], 32.0), (p01[0], p01[1], 32.0), h0, h1])),
        ring(close([(p01[0], p01[1], 32.0), (p00[0], p00[1], 32.0), h0])),
    ]),
], doitt="900003"))

# 4. shed: one plane, low on -y, high on +y
cx, cy = X0 + 600.0, Y0
plan = rect(cx, cy, 30.0, 40.0)
p00, p10, p11, p01 = plan
parts_all.append(building("b_shed", "4000004", [
    surface("GroundSurface", ground(plan, 10.0)),
    surface("WallSurface", walls(plan, 10.0, lambda i: (28.0, 28.0, 44.0, 44.0)[i])),
    surface("RoofSurface", [
        ring(close([(p00[0], p00[1], 28.0), (p10[0], p10[1], 28.0), (p11[0], p11[1], 44.0), (p01[0], p01[1], 44.0)])),
    ]),
], doitt="900004"))

# 5. two flat levels (stepped massing, the real NYC pattern)
cx, cy = X0 + 800.0, Y0
big = rect(cx, cy, 60.0, 40.0)
small = rect(cx + 10.0, cy, 20.0, 20.0)
parts_all.append(building("b_two_level", "4000005", [
    surface("GroundSurface", ground(big, 10.0)),
    surface("WallSurface", walls(big, 10.0, 35.0) + walls(small, 35.0, 60.0)),
    surface("RoofSurface", [
        ring_with_hole(close([(x, y, 35.0) for x, y in big]), [close([(x, y, 35.0) for x, y in reversed(small)])]),
        ring(close([(x, y, 60.0) for x, y in small])),
    ]),
], doitt="900005"))

# 6. duplicate BIN 4000001: a second Building element for the same building (garage wing)
cx, cy = X0, Y0 + 80.0
plan = rect(cx, cy, 20.0, 20.0)
parts_all.append(building("b_flat_part2", "4000001", [
    surface("GroundSurface", ground(plan, 10.0)),
    surface("WallSurface", walls(plan, 10.0, 22.0)),
    surface("RoofSurface", [ring(close([(x, y, 22.0) for x, y in plan]))]),
], doitt="900001"))

# 7. no BIN attribute at all
cx, cy = X0 + 1000.0, Y0
plan = rect(cx, cy, 25.0, 25.0)
parts_all.append(building("b_nobin", None, [
    surface("GroundSurface", ground(plan, 10.0)),
    surface("WallSurface", walls(plan, 10.0, 30.0)),
    surface("RoofSurface", [ring(close([(x, y, 30.0) for x, y in plan]))]),
]))

# 8. borough placeholder BIN
cx, cy = X0 + 1100.0, Y0
plan = rect(cx, cy, 25.0, 25.0)
parts_all.append(building("b_placeholder", "4000000", [
    surface("GroundSurface", ground(plan, 10.0)),
    surface("WallSurface", walls(plan, 10.0, 30.0)),
    surface("RoofSurface", [ring(close([(x, y, 30.0) for x, y in plan]))]),
]))

# 9. one unusable (2-D) roof ring plus a good flat roof: exercises the drop path
cx, cy = X0 + 1200.0, Y0
plan = rect(cx, cy, 25.0, 25.0)
bad = ('<gml:surfaceMember><gml:Polygon><gml:exterior><gml:LinearRing>'
       '<gml:posList srsDimension="2">0 0 1 0 1 1 0 0</gml:posList>'
       '</gml:LinearRing></gml:exterior></gml:Polygon></gml:surfaceMember>')
parts_all.append(building("b_baddring", "4000006", [
    surface("GroundSurface", ground(plan, 10.0)),
    surface("WallSurface", walls(plan, 10.0, 30.0)),
    surface("RoofSurface", [ring(close([(x, y, 30.0) for x, y in plan])), bad]),
], doitt="900006"))

doc = ('<?xml version="1.0" encoding="UTF-8"?>\n'
       '<CityModel xmlns="http://www.opengis.net/citygml/2.0" '
       'xmlns:bldg="http://www.opengis.net/citygml/building/2.0" '
       'xmlns:gen="http://www.opengis.net/citygml/generics/2.0" '
       'xmlns:gml="http://www.opengis.net/gml">\n'
       '<gml:name>nycsim citygml test fixture (synthetic, EPSG:2263 ft)</gml:name>\n'
       + "\n".join(parts_all) + "\n</CityModel>\n")
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(doc)
print(OUT, OUT.stat().st_size, "bytes")
