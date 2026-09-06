"""Vehicular-tunnel generators for the B landmarks: drivable tube interiors, portal buildings and ventilation towers.

The four NYC vehicular river tunnels in this lane (Holland, Lincoln, Queens-Midtown, Hugh L. Carey) are all
**twin-shield tunnels with transverse ventilation**: a circular cast-iron/steel lining about 9.5 m in diameter, a
roadway slab across it that leaves a fresh-air duct below and an exhaust plenum above the ceiling, glazed tile on the
walls, a raised catwalk on each side, and luminaires in two rows along the ceiling coves.  This module builds that
section along a real centreline so the tube can be driven end to end.

Geometry conventions
--------------------
* A tunnel is built along a **3-D centreline polyline** in the landmark's local frame — taken from the real OSM
  ``highway=motorway``+``tunnel=yes`` ways, resampled and extended to the published portal-to-portal length, with the
  vertical profile a parabola from the portal elevations down to the published low point under the river.
* The interior lining is a set of **open ribbons** with inward-facing normals (floor, catwalks, tiled lower walls,
  dark upper walls, ceiling), so the tube is correct seen from inside; the outer shell is built only for the length
  that is visible at each portal.  ``build_tube`` states this in every model's fidelity statement.
* ``t`` is metres left of the direction of travel, ``dz`` metres above the roadway surface.
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Callable, Sequence

import bmesh
from mathutils import Matrix, Vector

import b_align as ba
import b_common as bc
import nycsim_bpy as nb

log = logging.getLogger("landmarks.b.tunnel")


# ================================================================================================ centrelines


def osm_way_local(way_id: int, frame: bc.LocalFrame) -> list[Vector] | None:
    """A real OSM LineString way as a list of local-frame points (z = 0)."""
    f = ba._ways().get(int(way_id))
    if f is None or f["geometry"]["type"] != "LineString":
        return None
    out = []
    for lon, lat in f["geometry"]["coordinates"]:
        x, y, _ = frame.from_lonlat(lon, lat)
        out.append(Vector((x, y, 0.0)))
    return out


def chain(frame: bc.LocalFrame, way_ids: Sequence[int], start_xy: tuple[float, float],
          fallback: Sequence[tuple[float, float]]) -> list[Vector]:
    """Join several OSM ways into one centreline running away from ``start_xy`` (NYC_TM).

    Each way is reversed if that brings its first point closer to the growing chain's end.  If any way is missing from
    the extract the whole chain falls back to the recorded ``fallback`` polyline (NYC_TM points), so a model can
    always be rebuilt.
    """
    parts: list[list[Vector]] = []
    for wid in way_ids:
        p = osm_way_local(wid, frame)
        if p is None or len(p) < 2:
            log.warning("OSM way %s missing from the extract; using the recorded fallback centreline", wid)
            return [Vector((x - frame.x0, y - frame.y0, 0.0)) for x, y in fallback]
        parts.append(p)
    sx, sy, _ = frame.to_local(*start_xy)
    start = Vector((sx, sy, 0.0))
    remaining = list(range(len(parts)))
    # start with the way that has an endpoint nearest the given start point, oriented away from it
    i0 = min(remaining, key=lambda i: min((parts[i][0] - start).length, (parts[i][-1] - start).length))
    chained = list(parts[i0]) if (parts[i0][0] - start).length <= (parts[i0][-1] - start).length else list(reversed(parts[i0]))
    remaining.remove(i0)
    while remaining:
        end = chained[-1]
        best, rev, dist = None, False, 1e18
        for i in remaining:
            d0 = (parts[i][0] - end).length
            d1 = (parts[i][-1] - end).length
            if d0 < dist:
                best, rev, dist = i, False, d0
            if d1 < dist:
                best, rev, dist = i, True, d1
        if best is None or dist > 150.0:
            log.warning("chain: next way is %.0f m from the chain end; stopping the chain here", dist)
            break
        seg = list(reversed(parts[best])) if rev else list(parts[best])
        chained += seg[1:]
        remaining.remove(best)
    return chained


def polyline_length(pts: Sequence[Vector]) -> float:
    return sum((pts[i + 1] - pts[i]).length for i in range(len(pts) - 1))


def resample(pts: Sequence[Vector], step: float) -> list[Vector]:
    """Even arc-length resampling of a polyline (keeps the two end points)."""
    if len(pts) < 2:
        raise ValueError("resample: need >= 2 points")
    total = polyline_length(pts)
    n = max(int(round(total / step)), 2)
    out = [Vector(pts[0])]
    target = total / n
    acc = 0.0
    i = 0
    cur = Vector(pts[0])
    while len(out) <= n and i < len(pts) - 1:
        seg = pts[i + 1] - cur
        L = seg.length
        if L < 1e-9:
            i += 1
            cur = Vector(pts[i])
            continue
        if acc + L >= target - 1e-9:
            cur = cur + seg.normalized() * (target - acc)
            out.append(Vector(cur))
            acc = 0.0
        else:
            acc += L
            i += 1
            cur = Vector(pts[i])
    if len(out) < n + 1:
        out.append(Vector(pts[-1]))
    return out


def extend_to_length(pts: Sequence[Vector], target: float) -> list[Vector]:
    """Extend (or trim) a polyline symmetrically along its end tangents so its length equals ``target``."""
    pts = [Vector(p) for p in pts]
    have = polyline_length(pts)
    delta = (target - have) / 2.0
    if abs(delta) < 0.05:
        return pts
    if delta > 0:
        d0 = (pts[0] - pts[1]).normalized()
        d1 = (pts[-1] - pts[-2]).normalized()
        return [pts[0] + d0 * delta] + pts + [pts[-1] + d1 * delta]
    # trim: walk in from both ends
    cut = -delta
    while cut > 0 and len(pts) > 3:
        L = (pts[1] - pts[0]).length
        if L > cut:
            pts[0] = pts[0] + (pts[1] - pts[0]).normalized() * cut
            break
        pts.pop(0)
        cut -= L
    cut = -delta
    while cut > 0 and len(pts) > 3:
        L = (pts[-1] - pts[-2]).length
        if L > cut:
            pts[-1] = pts[-1] + (pts[-2] - pts[-1]).normalized() * cut
            break
        pts.pop()
        cut -= L
    return pts


def profile_z(pts: Sequence[Vector], z_a: float, z_b: float, z_low: float) -> list[Vector]:
    """Apply the vertical profile: a parabola from ``z_a`` at the first point through ``z_low`` at mid-length to
    ``z_b`` at the last, i.e. the real descend-level-climb shape of a river tunnel."""
    total = polyline_length(pts)
    out = []
    s = 0.0
    for i, p in enumerate(pts):
        if i:
            s += (pts[i] - pts[i - 1]).length
        u = s / total
        lin = z_a + (z_b - z_a) * u
        dip = (z_low - 0.5 * (z_a + z_b)) * 4.0 * u * (1.0 - u)
        out.append(Vector((p.x, p.y, lin + dip)))
    return out


# ================================================================================================ ribbon sweeps


def _frames(path: Sequence[Vector]) -> list[tuple[Vector, Vector]]:
    """(point, horizontal left-normal) at every station of a 3-D path."""
    out = []
    n = len(path)
    for i, p in enumerate(path):
        if i == 0:
            t = path[1] - path[0]
        elif i == n - 1:
            t = path[-1] - path[-2]
        else:
            t = (path[i + 1] - path[i]).normalized() + (path[i] - path[i - 1]).normalized()
        t = Vector((t.x, t.y, 0.0))
        if t.length < 1e-9:
            t = Vector((1.0, 0.0, 0.0))
        t.normalize()
        out.append((Vector(p), Vector((-t.y, t.x, 0.0))))
    return out


def ribbon(name: str, path: Sequence[Vector], profile: Sequence[tuple[float, float]], material: str,
           flip: bool = False, smooth: bool = False, uv_scale: float = 1.0) -> bc.bpy.types.Object:
    """Open surface: an *open* 2-D profile (t, dz) swept along a 3-D path.  ``flip`` reverses the normals so the
    surface is seen from inside the tube."""
    fr = _frames(path)
    if len(fr) < 2 or len(profile) < 2:
        raise ValueError(f"ribbon({name}): need >= 2 stations and >= 2 profile points")
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    rings = []
    s_acc = [0.0]
    for i in range(1, len(path)):
        s_acc.append(s_acc[-1] + (path[i] - path[i - 1]).length)
    v_acc = [0.0]
    for k in range(1, len(profile)):
        v_acc.append(v_acc[-1] + math.dist(profile[k - 1], profile[k]))
    for (p, nvec) in fr:
        rings.append([bm.verts.new(p + nvec * t + Vector((0, 0, dz))) for t, dz in profile])
    for i in range(len(rings) - 1):
        for k in range(len(profile) - 1):
            a, b, c, d = rings[i][k], rings[i][k + 1], rings[i + 1][k + 1], rings[i + 1][k]
            f = bm.faces.new((a, b, c, d) if not flip else (d, c, b, a))
            us = (s_acc[i] * uv_scale, s_acc[i + 1] * uv_scale)
            vs = (v_acc[k] * uv_scale, v_acc[k + 1] * uv_scale)
            quad = ((us[0], vs[0]), (us[0], vs[1]), (us[1], vs[1]), (us[1], vs[0]))
            for loop, coord in zip(f.loops, quad if not flip else tuple(reversed(quad))):
                loop[uv].uv = coord
    ob = nb.bmesh_to_object(name, bm, materials=[bc.mat(material)])
    if smooth:
        for poly in ob.data.polygons:
            poly.use_smooth = True
    return ob


def arc_profile(cz: float, r: float, a0_deg: float, a1_deg: float, n: int) -> list[tuple[float, float]]:
    """Points on the tube circle: centre at (0, cz), angle measured from +t towards +dz."""
    return [(r * math.cos(math.radians(a0_deg + (a1_deg - a0_deg) * i / n)),
             cz + r * math.sin(math.radians(a0_deg + (a1_deg - a0_deg) * i / n))) for i in range(n + 1)]


# ================================================================================================ tube


@dataclass
class TubeSpec:
    diameter: float = 9.5          # lining internal diameter
    road_w: float = 6.6            # carriageway width
    lanes: int = 2
    catwalk_w: float = 0.75
    catwalk_h: float = 0.35
    ceiling_h: float = 4.11        # 13 ft 6 in above the roadway (Holland's clearance is 12 ft 6 in under the signs)
    ceiling_half: float = 3.55
    tile_top: float = 2.40         # top of the glazed white tile band
    axis_dz: float = 1.60          # tube centre above the roadway surface
    light_every: float = 10.0      # brief: a luminaire every 10 m
    exit_every: float = 150.0
    station: float = 12.0          # centreline resampling step
    material_wall: str = "tile_white"
    material_upper: str = "tile_dark"
    material_road: str = "asphalt"
    material_ceiling: str = "tile_dark"
    portal_shell_m: float = 70.0   # length of outer shell built at each portal


def tube_interior_profile(spec: TubeSpec) -> dict[str, list[tuple[float, float]]]:
    """The five ribbons of the interior lining, each an open (t, dz) polyline from left to right / bottom to top."""
    r = spec.diameter / 2
    cz = spec.axis_dz
    t_floor = math.sqrt(max(r * r - cz * cz, 0.01))
    a_low = math.degrees(math.asin(max(-1.0, min(1.0, (spec.catwalk_h - cz) / r))))
    a_tile = math.degrees(math.asin(max(-1.0, min(1.0, (spec.tile_top - cz) / r))))
    a_ceil = math.degrees(math.asin(max(-1.0, min(1.0, (spec.ceiling_h - cz) / r))))
    return {
        "floor": [(-t_floor, 0.0), (t_floor, 0.0)],
        "wall_lo_r": arc_profile(cz, r, a_low, a_tile, 3),
        "wall_hi_r": arc_profile(cz, r, a_tile, a_ceil, 3),
        "wall_lo_l": arc_profile(cz, r, 180.0 - a_low, 180.0 - a_tile, 3),
        "wall_hi_l": arc_profile(cz, r, 180.0 - a_tile, 180.0 - a_ceil, 3),
        "ceiling": [(-spec.ceiling_half, spec.ceiling_h), (spec.ceiling_half, spec.ceiling_h)],
        "shell": arc_profile(cz, r + 0.55, -180.0, 180.0, 24),
    }


def build_tube(name: str, path: Sequence[Vector], spec: TubeSpec, lod: int = 0) -> list:
    """One drivable tube: lining, roadway, lane markings, catwalks and handrails, luminaires every ``light_every``
    metres, recessed emergency-exit niches, and the outer shell for ``portal_shell_m`` at each end."""
    pts = resample(path, spec.station)
    prof = tube_interior_profile(spec)
    r = spec.diameter / 2
    out: list = []
    # ---- lining ---------------------------------------------------------------------------------------------------
    out.append(ribbon(f"{name}_floor", pts, prof["floor"], "concrete_dark", flip=True))
    out.append(ribbon(f"{name}_road", pts, [(-spec.road_w / 2, 0.03), (spec.road_w / 2, 0.03)], spec.material_road, flip=True))
    for side in ("l", "r"):
        out.append(ribbon(f"{name}_wall_lo_{side}", pts, prof[f"wall_lo_{side}"], spec.material_wall, flip=True, smooth=(lod == 0)))
        out.append(ribbon(f"{name}_wall_hi_{side}", pts, prof[f"wall_hi_{side}"], spec.material_upper, flip=True, smooth=(lod == 0)))
    out.append(ribbon(f"{name}_ceiling", pts, prof["ceiling"], spec.material_ceiling, flip=True))
    # ---- catwalks and handrails -----------------------------------------------------------------------------------
    t_floor = math.sqrt(max(r * r - spec.axis_dz ** 2, 0.01))
    for s in (-1, 1):
        t_in = s * spec.road_w / 2
        t_out = s * t_floor
        cw = [(t_in, 0.0), (t_in, spec.catwalk_h), (t_out, spec.catwalk_h)]
        out.append(ribbon(f"{name}_catwalk{s}", pts, cw if s > 0 else list(reversed(cw)), "concrete", flip=(s > 0)))
        if lod == 0:
            out.append(ribbon(f"{name}_rail{s}", pts, [(t_in + s * 0.06, spec.catwalk_h + 0.95),
                                                       (t_in - s * 0.06, spec.catwalk_h + 0.95)], "steel_black"))
    # ---- lane markings --------------------------------------------------------------------------------------------
    if lod == 0:
        for i in range(1, spec.lanes):
            t = -spec.road_w / 2 + i * spec.road_w / spec.lanes
            dashes = []
            total = polyline_length(pts)
            k = 0
            s = 0.0
            fr = _frames(pts)
            acc = [0.0]
            for j in range(1, len(pts)):
                acc.append(acc[-1] + (pts[j] - pts[j - 1]).length)
            while s < total - 3.0:
                j = max(0, min(len(pts) - 2, next((q for q in range(len(acc) - 1) if acc[q + 1] > s), 0)))
                p0, n0 = fr[j]
                p1, _ = fr[j + 1]
                d = (p1 - p0)
                if d.length < 1e-6:
                    s += 12.0
                    continue
                d.normalize()
                a = p0 + d * (s - acc[j]) + n0 * t + Vector((0, 0, 0.05))
                b = a + d * 3.0
                dashes.append(bc.box_between(f"{name}_dash{k}", a, b, 0.12, 0.01, "lane_white"))
                s += 12.0
                k += 1
            if dashes:
                out.append(bc.join(dashes, f"{name}_lane_dashes{i}"))
        for s_ in (-1, 1):
            out.append(ribbon(f"{name}_edge{s_}", pts, [(s_ * (spec.road_w / 2 - 0.22), 0.05),
                                                        (s_ * (spec.road_w / 2 - 0.10), 0.05)], "lane_white"))
    # ---- luminaires (two rows in the ceiling coves) and emergency niches -------------------------------------------
    fr = _frames(pts)
    acc = [0.0]
    for j in range(1, len(pts)):
        acc.append(acc[-1] + (pts[j] - pts[j - 1]).length)
    total = acc[-1]

    def at(s: float) -> tuple[Vector, Vector, Vector]:
        j = max(0, min(len(pts) - 2, next((q for q in range(len(acc) - 1) if acc[q + 1] > s), len(pts) - 2)))
        p0, n0 = fr[j]
        d = (pts[j + 1] - pts[j])
        d = d.normalized() if d.length > 1e-6 else Vector((1, 0, 0))
        return p0 + d * (s - acc[j]), n0, d

    lights = []
    s = spec.light_every / 2
    while s < total:
        p, n0, d = at(s)
        for side in (-1, 1):
            c = p + n0 * (side * (spec.ceiling_half - 0.18)) + Vector((0, 0, spec.ceiling_h - 0.14))
            lights.append(bc.box_between(f"{name}_lamp", c - d * 0.7, c + d * 0.7, 0.26, 0.12, "light_cool"))
        s += spec.light_every
    if lights:
        out.append(bc.join(lights, f"{name}_luminaires"))
    if lod == 0:
        niches = []
        s = spec.exit_every
        k = 0
        while s < total - 20.0:
            p, n0, d = at(s)
            side = 1 if k % 2 == 0 else -1
            c = p + n0 * (side * (t_floor - 0.12)) + Vector((0, 0, spec.catwalk_h))
            door = bc.box_between(f"{name}_exit{k}", c - d * 0.55, c + d * 0.55, 0.12, 2.05, "steel_green")
            bc.transform(door, Matrix.Translation(Vector((0, 0, 1.02))))
            niches.append(door)
            sign = bc.box_between(f"{name}_exitsign{k}", c - d * 0.4, c + d * 0.4, 0.06, 0.28, "light_cool")
            bc.transform(sign, Matrix.Translation(Vector((0, 0, 2.35))))
            niches.append(sign)
            s += spec.exit_every
            k += 1
        if niches:
            out.append(bc.join(niches, f"{name}_emergency_exits"))
    # ---- outer shell at the portals --------------------------------------------------------------------------------
    if spec.portal_shell_m > 0:
        n_end = max(int(spec.portal_shell_m / spec.station), 2)
        for tag, seg in (("a", pts[:n_end + 1]), ("b", pts[-n_end - 1:])):
            out.append(ribbon(f"{name}_shell_{tag}", seg, prof["shell"], "concrete_dark", smooth=(lod == 0)))
    return out


# ================================================================================================ portals & vent


def build_portal(name: str, p: Vector, direction: Vector, spec: TubeSpec, *, width: float, height: float,
                 depth: float, ground_z: float, material: str = "granite_gray", lod: int = 0) -> list:
    """Portal head-wall with the tunnel mouth cut through it, plus wing walls and the approach cut.

    ``p`` is the tube centreline point at the portal, ``direction`` the unit vector pointing *into* the tunnel.
    """
    d = Vector((direction.x, direction.y, 0.0)).normalized()
    n = Vector((-d.y, d.x, 0.0))
    axisM = Matrix(((d.x, n.x, 0.0, 0.0), (d.y, n.y, 0.0, 0.0), (0.0, 0.0, 1.0, 0.0), (0.0, 0.0, 0.0, 1.0)))
    axisM.translation = Vector((p.x, p.y, 0.0))
    z0 = p.z
    out = []
    prof = [(-width / 2, ground_z - 6.0), (width / 2, ground_z - 6.0), (width / 2, z0 + height), (-width / 2, z0 + height)]
    mouth = bc.round_arch(spec.diameter + 1.1, spec.diameter * 0.62 + spec.axis_dz + 1.0, 0.0, z0 - 0.1)
    wall = bc.profile_extrude(f"{name}_headwall", prof, depth, material, holes=[mouth], plane="yz")
    bc.transform(wall, axisM)
    out.append(wall)
    cornice = bc.box(f"{name}_cornice", (depth + 1.2, width + 1.2, 1.1), (0, 0, z0 + height), material)
    bc.transform(cornice, axisM)
    out.append(cornice)
    for side in (-1, 1):
        wing = bc.box(f"{name}_wing", (26.0, 1.2, z0 + 3.6 - (ground_z - 5.0)),
                      (-13.0 - depth / 2, side * (width / 2 - 0.6), ground_z - 5.0), material)
        bc.transform(wing, axisM)
        out.append(wing)
    if lod == 0:
        for side in (-1, 1):
            lamp = bc.lamp_post(f"{name}_lamp", Vector((0, 0, 0)), 7.0, 1.4, 0.0)
            bc.transform(lamp, Matrix.Translation(Vector((-depth / 2 - 8.0, side * (width / 2 - 2.0), ground_z))))
            bc.transform(lamp, axisM)
            out.append(lamp)
    return out


def build_vent_building(name: str, centre: Vector, size: tuple[float, float], height: float, heading_deg: float,
                        *, material: str = "brick_red", trim: str = "limestone", louvre_rows: int = 3,
                        lod: int = 0, ring: Sequence[Sequence[float]] | None = None) -> list:
    """Transverse-ventilation building: a banded block with louvre openings and a stepped Art Deco cap.

    ``ring`` is the real OSM footprint in local coordinates (preferred); when it is None the block falls back to a
    ``size`` = (along-heading, across) rectangle.  ``height`` is metres above the block's base.
    """
    w, dp = size
    out = []
    M = bc.rot_z(bc.heading_to_math_deg(heading_deg) - 90.0)
    M.translation = Vector((centre.x, centre.y, 0.0))
    if ring is not None and len(ring) >= 3:
        out.append(bc.prism(f"{name}_body", ring, centre.z, centre.z + height, material))
    else:
        body = bc.box(f"{name}_body", (w, dp, height), (0, 0, centre.z), material)
        bc.transform(body, M)
        out.append(body)
    for k in range(1, 4):
        band = bc.box(f"{name}_band{k}", (w + 0.5, dp + 0.5, 0.6), (0, 0, centre.z + height * k / 4.5), trim)
        bc.transform(band, M)
        out.append(band)
    cap = bc.box(f"{name}_cap", (w - 2.0, dp - 2.0, 3.2), (0, 0, centre.z + height), material)
    bc.transform(cap, M)
    out.append(cap)
    cap2 = bc.box(f"{name}_cap2", (w - 6.0, dp - 6.0, 2.2), (0, 0, centre.z + height + 3.2), trim)
    bc.transform(cap2, M)
    out.append(cap2)
    if lod == 0:
        louvres = []
        for row in range(louvre_rows):
            z = centre.z + height * (0.42 + 0.16 * row)
            for sx, sy, ww, dd in ((0, dp / 2, w - 4.0, 0.3), (0, -dp / 2, w - 4.0, 0.3),
                                   (w / 2, 0, 0.3, dp - 4.0), (-w / 2, 0, 0.3, dp - 4.0)):
                lv = bc.box(f"{name}_louvre{row}", (max(ww, 0.3), max(dd, 0.3), 2.6), (sx, sy, z), "steel_black")
                bc.transform(lv, M)
                louvres.append(lv)
        out.append(bc.join(louvres, f"{name}_louvres"))
    return out


def build_toll_plaza(name: str, centre: Vector, heading_deg: float, lanes: int, *, lod: int = 0) -> list:
    """Open-road tolling gantry over a paved plaza (the modern NYC arrangement: no booths)."""
    out = []
    M = bc.rot_z(bc.heading_to_math_deg(heading_deg) - 90.0)
    M.translation = Vector((centre.x, centre.y, 0.0))
    w = lanes * 3.66 + 6.0
    slab = bc.box(f"{name}_slab", (70.0, w, 0.25), (0, 0, centre.z - 0.25), "asphalt_light")
    bc.transform(slab, M)
    out.append(slab)
    for side in (-1, 1):
        leg = bc.box(f"{name}_leg", (1.0, 1.0, 7.4), (0, side * (w / 2 - 0.8), centre.z), "steel_gray")
        bc.transform(leg, M)
        out.append(leg)
    gantry = bc.box(f"{name}_gantry", (1.6, w, 1.3), (0, 0, centre.z + 7.4), "steel_gray")
    bc.transform(gantry, M)
    out.append(gantry)
    if lod == 0:
        for i in range(lanes):
            t = -w / 2 + 3.0 + (i + 0.5) * 3.66
            head = bc.box(f"{name}_reader{i}", (0.9, 1.2, 0.5), (0, t, centre.z + 6.8), "steel_black")
            bc.transform(head, M)
            out.append(head)
    return out


# ================================================================================================ whole-tunnel assembly


@dataclass
class TubeCfg:
    """One bore: the OSM ways that trace it, the end it starts from, a recorded fallback centreline and its length."""
    name: str
    ways: Sequence[int]
    start_tm: tuple[float, float]
    fallback: Sequence[tuple[float, float]]
    length_m: float
    lanes: int = 2
    direction: str = ""


@dataclass
class VentCfg:
    """One ventilation building: OSM way (0 = none), NYC_TM centroid, published/OSM height, base elevation."""
    name: str
    way: int
    xy: tuple[float, float]
    height: float
    heading_deg: float = 0.0
    size: tuple[float, float] = (30.0, 22.0)
    base_z: float = 0.0
    material: str = "brick_red"
    trim: str = "limestone"
    measured: bool = True


@dataclass
class TunnelCfg:
    portal_a_tm: tuple[float, float]
    portal_b_tm: tuple[float, float]
    ground_a: float
    ground_b: float
    z_low: float
    tubes: Sequence[TubeCfg]
    vents: Sequence[VentCfg] = field(default_factory=list)
    spec: TubeSpec = field(default_factory=TubeSpec)
    portal_width: float = 22.0
    portal_height: float = 9.0
    portal_depth: float = 7.0
    portal_material: str = "granite_gray"
    toll_lanes: int = 0
    toll_xy: tuple[float, float] | None = None


def assemble(cfg: TunnelCfg, frame: bc.LocalFrame, lod: int = 0) -> tuple[list, dict]:
    """Build every tube, both portal head-walls and all ventilation buildings of one vehicular tunnel.

    Returns the object list and a dict of measured-vs-published tube lengths for the model's report.
    """
    objs: list = []
    stats: dict[str, dict] = {}
    for tube in cfg.tubes:
        raw = chain(frame, tube.ways, tube.start_tm, tube.fallback)
        measured = polyline_length(raw)
        line = extend_to_length(raw, tube.length_m)
        # which portal is which end?
        pa = Vector(frame.to_local(*cfg.portal_a_tm)[:2] + (0.0,))
        za = cfg.ground_a - 4.0 if (line[0] - pa).length < (line[-1] - pa).length else cfg.ground_b - 4.0
        zb = cfg.ground_b - 4.0 if (line[0] - pa).length < (line[-1] - pa).length else cfg.ground_a - 4.0
        line = profile_z(line, za, zb, cfg.z_low)
        spec = TubeSpec(**{**cfg.spec.__dict__, "lanes": tube.lanes})
        objs += build_tube(tube.name, line, spec, lod)
        stats[tube.name] = {"osm_measured_m": round(measured, 1), "published_m": tube.length_m,
                            "modelled_m": round(polyline_length(line), 1),
                            "error_pct": round(100.0 * (measured - tube.length_m) / tube.length_m, 2),
                            "lanes": tube.lanes, "direction": tube.direction}
        log.info("tube %s: OSM %.1f m, published %.1f m (%+.2f %%)", tube.name, measured, tube.length_m,
                 100.0 * (measured - tube.length_m) / tube.length_m)
    # ---- portal head-walls: one per portal, spanning all the bores that end there --------------------------------
    for tag, xy, ground in (("a", cfg.portal_a_tm, cfg.ground_a), ("b", cfg.portal_b_tm, cfg.ground_b)):
        px, py, _ = frame.to_local(*xy)
        p0 = Vector((px, py, ground - 4.0))
        # direction into the tunnel = towards the other portal
        ox, oy, _ = frame.to_local(*(cfg.portal_b_tm if tag == "a" else cfg.portal_a_tm))
        d = Vector((ox - px, oy - py, 0.0)).normalized()
        for k, tube in enumerate(cfg.tubes):
            raw = chain(frame, tube.ways, tube.start_tm, tube.fallback)
            end = raw[0] if (raw[0] - p0).length < (raw[-1] - p0).length else raw[-1]
            objs += build_portal(f"portal_{tag}_{tube.name}", Vector((end.x, end.y, ground - 4.0)), d, cfg.spec,
                                 width=cfg.portal_width, height=cfg.portal_height, depth=cfg.portal_depth,
                                 ground_z=ground, material=cfg.portal_material, lod=lod)
    # ---- ventilation buildings ------------------------------------------------------------------------------------
    for v in cfg.vents:
        vx, vy, _ = frame.to_local(*v.xy)
        ring = ba.osm_polygon_local(v.way, frame) if v.way else None
        objs += build_vent_building(v.name, Vector((vx, vy, v.base_z)), v.size, v.height, v.heading_deg,
                                    material=v.material, trim=v.trim, lod=lod, ring=ring)
    if cfg.toll_lanes and cfg.toll_xy:
        tx, ty, _ = frame.to_local(*cfg.toll_xy)
        objs += build_toll_plaza("toll", Vector((tx, ty, cfg.ground_b)), frame.heading_deg, cfg.toll_lanes, lod=lod)
    return objs, stats
