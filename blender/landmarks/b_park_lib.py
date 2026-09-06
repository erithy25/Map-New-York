"""Masonry, classical and fairground generators for the B landmarks (monuments, forts, park structures, Coney Island).

Everything here is dimension-driven: each generator takes the published measurements of the thing being built and
produces geometry in the landmark's local frame (metres, z up, NAVD88).  Nothing here invents a "typical" size —
callers pass the figures they cite in their docstring.
"""
from __future__ import annotations

import math
from typing import Callable, Sequence

import bmesh
from mathutils import Matrix, Vector

import b_common as bc
import nycsim_bpy as nb


# ================================================================================================ classical orders


def column(name: str, base: Sequence[float], height: float, radius: float, material: str, *, order: str = "doric",
           segments: int = 12, flutes: int = 0, entasis: float = 0.06, lod: int = 0) -> list:
    """A classical column: plinth, base torus, tapered (entasis) shaft, capital.

    ``order``: doric (plain echinus + abacus), ionic (volute block), corinthian (bell + abacus).  ``flutes`` > 0 adds
    that many shallow vertical grooves as thin boxes (LOD0 only).
    """
    b = Vector(base)
    out = []
    plinth_h = radius * 0.35
    cap_h = radius * (0.9 if order == "corinthian" else 0.62)
    shaft_h = height - plinth_h - cap_h
    if shaft_h <= 0:
        raise ValueError(f"column({name}): height {height} too small for radius {radius}")
    out.append(nb.cylinder(f"{name}_plinth", radius * 1.28, plinth_h, segments, b, material=bc.mat(material)))
    # shaft with entasis: swell of `entasis` at 1/3 height
    bm = bmesh.new()
    rings = []
    n_st = 6 if lod == 0 else 2
    for i in range(n_st + 1):
        u = i / n_st
        r = radius * (1.0 + entasis * math.sin(math.pi * min(u * 1.4, 1.0)) - 0.16 * u)
        z = plinth_h + shaft_h * u
        rings.append([bm.verts.new(b + Vector((r * math.cos(2 * math.pi * k / segments),
                                               r * math.sin(2 * math.pi * k / segments), z))) for k in range(segments)])
    for r0, r1 in zip(rings[:-1], rings[1:]):
        for k in range(segments):
            bm.faces.new((r0[k], r0[(k + 1) % segments], r1[(k + 1) % segments], r1[k]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    shaft = nb.bmesh_to_object(f"{name}_shaft", bm, materials=[bc.mat(material)])
    for p in shaft.data.polygons:
        p.use_smooth = True
    out.append(shaft)
    z_cap = plinth_h + shaft_h
    if order == "corinthian":
        out.append(nb.cylinder(f"{name}_bell", radius * 1.05, cap_h * 0.72, segments, b + Vector((0, 0, z_cap)),
                               material=bc.mat(material)))
        out.append(bc.box(f"{name}_abacus", (radius * 2.5, radius * 2.5, cap_h * 0.28),
                          (b.x, b.y, b.z + z_cap + cap_h * 0.72), material))
    elif order == "ionic":
        out.append(bc.box(f"{name}_volute", (radius * 2.5, radius * 1.9, cap_h * 0.6),
                          (b.x, b.y, b.z + z_cap), material))
        out.append(bc.box(f"{name}_abacus", (radius * 2.6, radius * 2.2, cap_h * 0.4),
                          (b.x, b.y, b.z + z_cap + cap_h * 0.6), material))
    else:
        out.append(nb.cylinder(f"{name}_echinus", radius * 1.22, cap_h * 0.55, segments, b + Vector((0, 0, z_cap)),
                               material=bc.mat(material)))
        out.append(bc.box(f"{name}_abacus", (radius * 2.5, radius * 2.5, cap_h * 0.45),
                          (b.x, b.y, b.z + z_cap + cap_h * 0.55), material))
    if flutes and lod == 0:
        for k in range(flutes):
            a = 2 * math.pi * k / flutes
            f = bc.box(f"{name}_flute{k}", (radius * 0.16, radius * 0.16, shaft_h * 0.96),
                       (b.x + (radius * 0.97) * math.cos(a), b.y + (radius * 0.97) * math.sin(a), b.z + plinth_h),
                       material)
            out.append(f)
    return out


def entablature(name: str, ring: Sequence[Sequence[float]], z0: float, material: str, *, architrave: float = 0.9,
                frieze: float = 1.1, cornice: float = 0.8, projection: float = 0.55) -> list:
    """Architrave / frieze / cornice courses over a plan ring (each course steps out by ``projection``/3)."""
    out = []
    z = z0
    for i, (h, grow) in enumerate(((architrave, 0.0), (frieze, projection / 3), (cornice, projection))):
        out.append(bc.prism(f"{name}_c{i}", _offset_ring(ring, grow), z, z + h, material))
        z += h
    return out


def _offset_ring(ring: Sequence[Sequence[float]], d: float) -> list[tuple[float, float]]:
    """Naive outward offset of a convex-ish ring by ``d`` (from its centroid)."""
    cx = sum(p[0] for p in ring) / len(ring)
    cy = sum(p[1] for p in ring) / len(ring)
    out = []
    for x, y in ring:
        dx, dy = x - cx, y - cy
        L = math.hypot(dx, dy) or 1.0
        out.append((x + dx / L * d, y + dy / L * d))
    return out


def balustrade(name: str, ring: Sequence[Sequence[float]], z0: float, height: float, material: str, *,
               spacing: float = 0.55, lod: int = 0, closed: bool = True) -> list:
    """Stone balustrade: bottom rail, turned balusters (octagonal prisms), top rail."""
    out = [bc.prism(f"{name}_rail0", ring, z0, z0 + height * 0.16, material),
           bc.prism(f"{name}_rail1", _offset_ring(ring, 0.06), z0 + height * 0.84, z0 + height, material)]
    if lod > 0:
        return out
    posts = []
    pts = list(ring) + ([ring[0]] if closed else [])
    for a, b in zip(pts[:-1], pts[1:]):
        L = math.dist(a, b)
        n = max(int(L / spacing), 1)
        for k in range(n):
            u = (k + 0.5) / n
            x = a[0] + (b[0] - a[0]) * u
            y = a[1] + (b[1] - a[1]) * u
            posts.append(nb.cylinder(f"{name}_b", height * 0.13, height * 0.68, 6,
                                     (x, y, z0 + height * 0.16), material=bc.mat(material)))
    if posts:
        out.append(bc.join(posts, f"{name}_balusters"))
    return out


def dome(name: str, centre: Sequence[float], radius: float, rise: float, material: str, *, segments: int = 24,
         rings: int = 8, oculus_r: float = 0.0, lantern_h: float = 0.0, lod: int = 0) -> list:
    """Hemispherical/segmental dome of the given radius and rise, with an optional oculus and lantern."""
    c = Vector(centre)
    seg = segments if lod == 0 else max(segments // 2, 8)
    nr = rings if lod == 0 else max(rings // 2, 3)
    bm = bmesh.new()
    a_max = math.asin(max(0.0, min(1.0, oculus_r / radius))) if oculus_r > 0 else 0.0
    prev = None
    for i in range(nr + 1):
        a = (math.pi / 2 - a_max) * (1 - i / nr) if oculus_r > 0 else (math.pi / 2) * (1 - i / nr)
        # parametrise so that i=0 is the springing (a = pi/2 -> top). Use i as latitude from base:
        lat = (math.pi / 2 - a_max) * i / nr
        r = radius * math.cos(lat)
        z = rise * math.sin(lat)
        ring = [bm.verts.new(c + Vector((r * math.cos(2 * math.pi * k / seg), r * math.sin(2 * math.pi * k / seg), z)))
                for k in range(seg)]
        if prev is not None:
            for k in range(seg):
                bm.faces.new((prev[k], prev[(k + 1) % seg], ring[(k + 1) % seg], ring[k]))
        prev = ring
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    ob = nb.bmesh_to_object(f"{name}_shell", bm, materials=[bc.mat(material)])
    for p in ob.data.polygons:
        p.use_smooth = True
    out = [ob]
    if lantern_h > 0:
        top_r = radius * math.cos(math.pi / 2 - a_max) if oculus_r > 0 else radius * 0.14
        z_top = rise * math.sin(math.pi / 2 - a_max) if oculus_r > 0 else rise
        out.append(nb.cylinder(f"{name}_lantern", max(top_r, 0.6), lantern_h, seg // 2,
                               c + Vector((0, 0, z_top)), material=bc.mat(material)))
        out.append(nb.cylinder(f"{name}_finial", max(top_r, 0.6) * 0.35, lantern_h * 0.4, 8,
                               c + Vector((0, 0, z_top + lantern_h)), material=bc.mat(material)))
    return out


def stairs(name: str, p0: Sequence[float], p1: Sequence[float], width: float, n: int, material: str) -> list:
    """A straight run of ``n`` equal risers from p0 (bottom, 3-D) to p1 (top, 3-D)."""
    a, b = Vector(p0), Vector(p1)
    d = Vector((b.x - a.x, b.y - a.y, 0.0))
    run = d.length
    rise = b.z - a.z
    if n < 1 or run < 1e-6:
        raise ValueError(f"stairs({name}): need a positive run and step count")
    d.normalize()
    parts = []
    for k in range(n):
        z = a.z + rise * k / n
        # steps are built along +x at the origin and the whole run is rotated into place afterwards
        parts.append(bc.box(f"{name}_s{k}", (run / n * 1.02, width, rise / n + 0.02),
                            (run * (k + 0.5) / n, 0.0, z), material, anchor="bottom"))
    m = Matrix.Translation(Vector((a.x, a.y, 0.0))) @ Matrix.Rotation(math.atan2(d.y, d.x), 4, "Z")
    for st in parts:
        bc.transform(st, m)
    return [bc.join(parts, name)]


def triumphal_arch(name: str, centre: Sequence[float], heading_deg: float, *, width: float, depth: float,
                   height: float, opening_w: float, opening_h: float, material: str, attic_h: float = 0.0,
                   cornice: float = 0.0, lod: int = 0, spandrel_relief: bool = True) -> list:
    """Single-opening triumphal arch (Washington Square, Grand Army Plaza, Manhattan Bridge type).

    The pier faces carry a shallow pilaster order and the arch has a moulded archivolt; ``attic_h`` adds the plain
    attic storey above the cornice that both New York arches have.
    """
    c = Vector((centre[0], centre[1], 0.0))
    M = bc.rot_z(bc.heading_to_math_deg(heading_deg) - 90.0)
    M.translation = c
    out = []
    prof = [(-width / 2, centre[2]), (width / 2, centre[2]), (width / 2, centre[2] + height),
            (-width / 2, centre[2] + height)]
    hole = bc.round_arch(opening_w, opening_h, 0.0, centre[2])
    body = bc.profile_extrude(f"{name}_body", prof, depth, material, holes=[hole], plane="yz")
    bc.transform(body, M)
    out.append(body)
    if cornice > 0:
        cor = bc.box(f"{name}_cornice", (depth + cornice * 2, width + cornice * 2, cornice * 1.4),
                     (0, 0, centre[2] + height), material)
        bc.transform(cor, M)
        out.append(cor)
    if attic_h > 0:
        at = bc.box(f"{name}_attic", (depth * 0.92, width * 0.94, attic_h),
                    (0, 0, centre[2] + height + (cornice * 1.4 if cornice > 0 else 0.0)), material)
        bc.transform(at, M)
        out.append(at)
        cap = bc.box(f"{name}_atticcap", (depth * 0.98, width + 0.5, 0.7),
                     (0, 0, centre[2] + height + (cornice * 1.4 if cornice > 0 else 0.0) + attic_h), material)
        bc.transform(cap, M)
        out.append(cap)
    if lod == 0:
        # engaged columns on the four pier faces and a shallow spandrel relief
        pier = (width - opening_w) / 2
        for sgn in (-1, 1):
            t = sgn * (opening_w / 2 + pier / 2)
            for ds in (-depth / 2 - 0.35, depth / 2 + 0.35):
                parts = column(f"{name}_col{sgn}{ds:+.0f}", (0, 0, 0), height * 0.78, pier * 0.19, material,
                               order="corinthian", segments=10, lod=lod)
                place = M @ Matrix.Translation(Vector((ds, t, centre[2])))
                for ob in parts:
                    bc.transform(ob, place)
                out += parts
        if spandrel_relief:
            for ds in (-depth / 2 - 0.12, depth / 2 + 0.12):
                for s in (-1, 1):
                    rel = bc.box(f"{name}_spandrel", (0.24, opening_w * 0.3, opening_w * 0.3),
                                 (ds, s * opening_w * 0.32, centre[2] + opening_h - opening_w * 0.16), material,
                                 anchor="center")
                    bc.transform(rel, M)
                    out.append(rel)
    return out


# ================================================================================================ fortification


def star_fort(name: str, ring: Sequence[Sequence[float]], z_ground: float, wall_h: float, wall_t: float,
              material: str, *, parapet_h: float = 1.4, glacis: float = 0.0, lod: int = 0) -> list:
    """Bastioned earth-and-masonry fort from its real plan ring: scarp wall, parapet and (optionally) a glacis slope."""
    inner = _offset_ring(ring, -wall_t)
    out = [nb.extrude_polygon(f"{name}_scarp", list(ring), z_ground - 2.0, z_ground + wall_h, [list(reversed(inner))],
                              material=bc.mat(material))]
    out.append(bc.prism(f"{name}_terreplein", inner, z_ground - 2.0, z_ground + wall_h - parapet_h, "grass"))
    out.append(nb.extrude_polygon(f"{name}_parapet", _offset_ring(ring, 0.2), z_ground + wall_h,
                                  z_ground + wall_h + parapet_h,
                                  [list(reversed(_offset_ring(inner, -0.2)))], material=bc.mat(material)))
    if glacis > 0:
        out.append(nb.extrude_polygon(f"{name}_glacis", _offset_ring(ring, glacis), z_ground - 3.0, z_ground - 0.4,
                                      [list(reversed(list(ring)))], material=bc.mat("grass")))
    _ = lod
    return out


def casemate_tower(name: str, centre: Sequence[float], radius: float, height: float, wall_t: float, material: str, *,
                   tiers: int = 3, ports_per_tier: int = 26, segments: int = 40, lod: int = 0) -> list:
    """Circular casemated battery (Castle Williams): a thick drum wall with tiers of gun ports and an open court."""
    c = Vector(centre)
    outer = bc.regular_polygon(segments, radius, c.x, c.y)
    inner = bc.regular_polygon(segments, radius - wall_t, c.x, c.y)
    out = [nb.extrude_polygon(f"{name}_wall", outer, c.z, c.z + height, [list(reversed(inner))],
                              material=bc.mat(material))]
    out.append(bc.prism(f"{name}_court", inner, c.z - 0.5, c.z + 0.4, "sidewalk"))
    if lod == 0:
        ports = []
        for tier in range(tiers):
            z = c.z + height * (0.16 + 0.26 * tier)
            for k in range(ports_per_tier):
                a = 2 * math.pi * k / ports_per_tier
                px = c.x + (radius - wall_t * 0.42) * math.cos(a)
                py = c.y + (radius - wall_t * 0.42) * math.sin(a)
                port = bc.box(f"{name}_port{tier}_{k}", (wall_t * 1.2, 1.35, 1.9), (px, py, z), "tile_dark",
                              anchor="center")
                m = (Matrix.Translation(Vector((px, py, 0))) @ Matrix.Rotation(a, 4, "Z")
                     @ Matrix.Translation(Vector((-px, -py, 0))))
                bc.transform(port, m)
                ports.append(port)
        out.append(bc.join(ports, f"{name}_gunports"))
    out.append(bc.prism(f"{name}_parapet", bc.regular_polygon(segments, radius + 0.3, c.x, c.y), c.z + height,
                        c.z + height + 1.3, material,
                        holes=[list(reversed(bc.regular_polygon(segments, radius - wall_t - 0.3, c.x, c.y)))]))
    return out


def park_wall(name: str, line: Sequence[Sequence[float]], z_fn: Callable[[float], float] | float, height: float,
              thickness: float, material: str, *, coping: float = 0.12, step: float = 12.0) -> list:
    """Low perimeter wall following a polyline (Central Park's brownstone-and-schist boundary wall)."""
    z0 = (lambda p: z_fn) if isinstance(z_fn, (int, float)) else z_fn
    pts = [Vector((p[0], p[1], 0.0)) for p in line]
    bm = bmesh.new()
    prev = None
    for i, p in enumerate(pts):
        if i == 0:
            t = pts[1] - pts[0]
        elif i == len(pts) - 1:
            t = pts[-1] - pts[-2]
        else:
            t = (pts[i + 1] - pts[i]).normalized() + (pts[i] - pts[i - 1]).normalized()
        t = Vector((t.x, t.y, 0.0))
        t = t.normalized() if t.length > 1e-9 else Vector((1, 0, 0))
        n = Vector((-t.y, t.x, 0.0))
        zb = z0(p) if callable(z0) else z0
        ring = [bm.verts.new(p + n * (thickness / 2) + Vector((0, 0, zb - 0.6))),
                bm.verts.new(p - n * (thickness / 2) + Vector((0, 0, zb - 0.6))),
                bm.verts.new(p - n * (thickness / 2) + Vector((0, 0, zb + height))),
                bm.verts.new(p + n * (thickness / 2) + Vector((0, 0, zb + height)))]
        if prev is not None:
            for k in range(4):
                bm.faces.new((prev[k], prev[(k + 1) % 4], ring[(k + 1) % 4], ring[k]))
        prev = ring
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    _ = step, coping
    return [nb.bmesh_to_object(name, bm, materials=[bc.mat(material)])]


# ================================================================================================ fairground


def ferris_wheel(name: str, centre: Sequence[float], radius: float, n_cars: int, material_frame: str,
                 car_materials: Sequence[str], *, swinging: int = 0, spokes: int = 16, car_size=(2.6, 2.0, 2.4),
                 heading_deg: float = 0.0, lod: int = 0) -> list:
    """Eccentric-wheel type Ferris wheel (Coney Island Wonder Wheel): two rims, radial spokes, A-frame towers and
    ``n_cars`` cars, of which ``swinging`` ride on inner rails rather than the outer rim."""
    c = Vector(centre)
    a0 = math.radians(bc.heading_to_math_deg(heading_deg))
    plane_n = Vector((math.cos(a0 + math.pi / 2), math.sin(a0 + math.pi / 2), 0.0))
    u = Vector((math.cos(a0), math.sin(a0), 0.0))
    out = []

    def P(ang: float, r: float, off: float = 0.0) -> Vector:
        return c + u * (r * math.cos(ang)) + Vector((0, 0, r * math.sin(ang))) + plane_n * off

    for off in (-1.6, 1.6):
        rim = [P(2 * math.pi * k / 72, radius, off) for k in range(72)] + [P(0.0, radius, off)]
        out.append(bc.tube_along(f"{name}_rim{off:+.1f}", rim, 0.22, material_frame, 6 if lod == 0 else 4, cap=False))
        rim2 = [P(2 * math.pi * k / 72, radius * 0.62, off) for k in range(72)] + [P(0.0, radius * 0.62, off)]
        out.append(bc.tube_along(f"{name}_rim2{off:+.1f}", rim2, 0.16, material_frame, 5 if lod == 0 else 4, cap=False))
    hub = bc.cylinder_between(f"{name}_hub", c - plane_n * 2.2, c + plane_n * 2.2, 0.7, material_frame, 12)
    out.append(hub)
    if lod == 0:
        sp = []
        for k in range(spokes):
            ang = 2 * math.pi * k / spokes
            for off in (-1.6, 1.6):
                sp.append(bc.cylinder_between(f"{name}_spoke", c + plane_n * off, P(ang, radius, off), 0.08,
                                              material_frame, 4))
        out.append(bc.join(sp, f"{name}_spokes"))
    # A-frame towers
    for off in (-1.6, 1.6):
        for s in (-1, 1):
            out.append(bc.box_between(f"{name}_leg", c + u * (s * radius * 0.72) + plane_n * off - Vector((0, 0, radius)),
                                      c + plane_n * off, 0.5, 0.5, material_frame))
    cars = []
    for k in range(n_cars):
        ang = 2 * math.pi * k / n_cars
        r = radius * (0.62 if k < swinging else 1.0)
        p = P(ang, r) - Vector((0, 0, car_size[2] / 2 + 0.9))
        m = car_materials[k % len(car_materials)]
        body = bc.box(f"{name}_car{k}", car_size, (p.x, p.y, p.z), m, anchor="center")
        cars.append(body)
        cars.append(bc.box_between(f"{name}_hanger{k}", P(ang, r), p + Vector((0, 0, car_size[2] / 2)), 0.1, 0.1,
                                   material_frame))
    out.append(bc.join(cars, f"{name}_cars"))
    return out


def coaster_track(name: str, path: Sequence[Sequence[float]], material_track: str, material_structure: str, *,
                  gauge: float = 1.1, bent_spacing: float = 6.0, ground_z: float = 0.0, lod: int = 0) -> list:
    """Wooden roller-coaster track: two running rails, cross ties, and timber bents down to the ground."""
    pts = [Vector(p) for p in path]
    out = []
    rails = []
    for s in (-1, 1):
        line = []
        for i, p in enumerate(pts):
            t = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)])
            t = Vector((t.x, t.y, 0.0))
            t = t.normalized() if t.length > 1e-9 else Vector((1, 0, 0))
            n = Vector((-t.y, t.x, 0.0))
            line.append(p + n * (s * gauge / 2))
        rails.append(line)
        out.append(bc.tube_along(f"{name}_rail{s}", line, 0.075, material_track, 5 if lod == 0 else 4, cap=False))
    if lod == 0:
        ties = []
        for i in range(0, len(pts), 2):
            ties.append(bc.box_between(f"{name}_tie{i}", rails[0][i], rails[1][i], 0.16, 0.12, material_structure))
        out.append(bc.join(ties, f"{name}_ties"))
    bents = []
    acc = 0.0
    for i in range(1, len(pts)):
        acc += (pts[i] - pts[i - 1]).length
        if acc < bent_spacing:
            continue
        acc = 0.0
        p = pts[i]
        if p.z - ground_z < 1.2:
            continue
        for s in (-1, 1):
            t = (pts[i] - pts[i - 1])
            t = Vector((t.x, t.y, 0.0)).normalized()
            n = Vector((-t.y, t.x, 0.0))
            top = p + n * (s * gauge / 2)
            foot = Vector((top.x + n.x * s * (p.z - ground_z) * 0.13, top.y + n.y * s * (p.z - ground_z) * 0.13, ground_z))
            bents.append(bc.box_between(f"{name}_post", foot, top, 0.16, 0.16, material_structure))
        if lod == 0:
            a = pts[i] + Vector((0, 0, -(p.z - ground_z) * 0.5))
            bents.append(bc.box_between(f"{name}_brace", a, p, 0.1, 0.1, material_structure))
    if bents:
        out.append(bc.join(bents, f"{name}_bents"))
    return out


def parachute_jump(name: str, centre: Sequence[float], height: float, base_r: float, top_r: float, material: str,
                   *, arms: int = 12, lod: int = 0) -> list:
    """The 1939 Parachute Jump: a six-legged tapering lattice tower with the ring of cantilevered arms at the top."""
    c = Vector(centre)
    out = []
    legs = 6
    for k in range(legs):
        a = 2 * math.pi * k / legs
        base = c + Vector((base_r * math.cos(a), base_r * math.sin(a), 0.0))
        top = c + Vector((top_r * math.cos(a), top_r * math.sin(a), height))
        out.append(bc.box_between(f"{name}_leg{k}", base, top, 0.55, 0.55, material))
    rings = 14 if lod == 0 else 5
    braces = []
    for i in range(1, rings + 1):
        u = i / rings
        r = base_r + (top_r - base_r) * u
        z = height * u
        for k in range(legs):
            a0 = 2 * math.pi * k / legs
            a1 = 2 * math.pi * (k + 1) / legs
            p0 = c + Vector((r * math.cos(a0), r * math.sin(a0), z))
            p1 = c + Vector((r * math.cos(a1), r * math.sin(a1), z))
            braces.append(bc.box_between(f"{name}_ring{i}_{k}", p0, p1, 0.24, 0.24, material))
            if lod == 0 and i < rings:
                u2 = (i + 1) / rings
                r2 = base_r + (top_r - base_r) * u2
                p2 = c + Vector((r2 * math.cos(a1), r2 * math.sin(a1), height * u2))
                braces.append(bc.box_between(f"{name}_x{i}_{k}", p0, p2, 0.16, 0.16, material))
    out.append(bc.join(braces, f"{name}_lattice"))
    for k in range(arms):
        a = 2 * math.pi * k / arms
        p0 = c + Vector((top_r * 0.8 * math.cos(a), top_r * 0.8 * math.sin(a), height))
        p1 = c + Vector((top_r * 3.6 * math.cos(a), top_r * 3.6 * math.sin(a), height + 1.6))
        out.append(bc.box_between(f"{name}_arm{k}", p0, p1, 0.3, 0.3, material))
    out.append(nb.cylinder(f"{name}_cap", top_r * 0.9, 3.2, 12, c + Vector((0, 0, height)), material=bc.mat(material)))
    return out


def boardwalk(name: str, line: Sequence[Sequence[float]], width: float, z: float, material: str, *,
              rail: bool = True, lod: int = 0) -> list:
    """Timber boardwalk deck (Riegelmann Boardwalk) following a real polyline, on piles, with a handrail."""
    pts = [Vector((p[0], p[1], z)) for p in line]
    bm = bmesh.new()
    prev = None
    edges: list[list[Vector]] = [[], []]
    for i, p in enumerate(pts):
        t = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)])
        t = Vector((t.x, t.y, 0.0))
        t = t.normalized() if t.length > 1e-9 else Vector((1, 0, 0))
        n = Vector((-t.y, t.x, 0.0))
        a = p + n * (width / 2)
        b = p - n * (width / 2)
        edges[0].append(a)
        edges[1].append(b)
        ring = [bm.verts.new(a), bm.verts.new(b), bm.verts.new(b - Vector((0, 0, 0.5))),
                bm.verts.new(a - Vector((0, 0, 0.5)))]
        if prev is not None:
            for k in range(4):
                bm.faces.new((prev[k], prev[(k + 1) % 4], ring[(k + 1) % 4], ring[k]))
        prev = ring
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    out = [nb.bmesh_to_object(name, bm, materials=[bc.mat(material)])]
    if rail and lod == 0:
        rails = []
        for side in edges:
            for i in range(0, len(side) - 1, 3):
                j = min(i + 3, len(side) - 1)
                rails.append(bc.railing(f"{name}_rail{i}", side[i], side[j], 1.0, 3.0, "wood_deck", 2))
        out.append(bc.join(rails, f"{name}_railings"))
    return out
