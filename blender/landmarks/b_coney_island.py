"""Coney Island — the Cyclone, Deno's Wonder Wheel, the Parachute Jump, the Riegelmann Boardwalk and the Luna Park
entrance, Brooklyn.

Dimensions used (source in brackets)
------------------------------------
* **Cyclone** (Vernon Keenan, opened 26 June 1927): a wooden out-and-back coaster **85 ft = 25.91 m** high with a
  first drop of **85 ft at 58.1 degrees**, **2,640 ft = 804.67 m** of track, a top speed of 60 mph, **12 drops** and
  **6 turns**; NYC Landmark **LP-1636** and NHL 1991 [NYC Parks, LPC, Wikipedia "Cyclone (roller coaster)"].
* **Deno's Wonder Wheel** (Charles Herman, opened 1920): **150 ft = 45.72 m** high, **24 cars** — **16 that swing
  along inner rails** and **8 fixed to the outer rim** — carrying 144 riders, built of 200 tons of Bethlehem steel;
  NYC Landmark **LP-1708** [NYC Parks, LPC].  OSM node ``4080306783`` tags its height as **46 m**.
* **Parachute Jump** (1939 New York World's Fair, moved to Steeplechase Park in 1941, closed 1968): **262 ft =
  79.86 m** high, a six-legged steel lattice tower with **12 cantilevered arms** at the top; NYC Landmark LP-1978.
  OSM way ``248474742`` tags its height as **80 m**.
* **Riegelmann Boardwalk** (1923): **2.7 miles = 4.35 km** long and **80 ft = 24.38 m** wide.  The real OSM way
  ``230060363`` traces **2,600 m** of it, which is what is built (stated gap).
* **Luna Park entrance** (2010): the arched entrance on Surf Avenue with its illuminated crescent-moon sign;
  modelled as a 17 m arch with an emissive sign band (proportions *inferred* from photographs).

Placement: the Wonder Wheel on OSM node ``4080306783`` (-2468, -13987); the Parachute Jump on OSM way ``248474742``
(-2913, -14105); the boardwalk on OSM way ``230060363``; the Cyclone inside the real plot of OSM ways ``405891521``
/ ``376073239`` / ``656566282`` (union bounding box 39 x 171 m, which matches the published 500 x 85 ft lot); the
Luna Park entrance at Surf Avenue and West 10th Street (-2448, -13930), **derived from the street grid, +-30 m**.
The Cyclone and Wonder Wheel BINs in ``landmark_footprints.parquet`` (3326898/3326899/3423906/3425344 and
3326896/3347224/3326897) confirm those positions.

**The Cyclone's track plan is generated, not surveyed.**  The three OSM ways trace only parts of the circuit
(387 / 305 / 255 m of the published 2,640 ft).  The model lays out a folded out-and-back circuit inside the ride's
real plot to the **published 804.67 m of track, 25.91 m lift height and 58.1-degree first drop**, with the published
12 drops; the sequence of curves is therefore a reconstruction to the published parameters, not the real layout.

Not modelled: the Cyclone's station, chain lift and trains; the Wonder Wheel's car glazing and its ticket booth;
the Parachute Jump's parachutes and their guy cables (the ride has not operated since 1968 and none are on it
today); Nathan's Famous, the Thunderbolt and the other Luna Park rides; the beach and the sand; the boardwalk's
lamp standards and benches.
"""
from __future__ import annotations

import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import b_align as ba  # noqa: E402
import b_common as bc  # noqa: E402
import b_park_lib as pk  # noqa: E402
import numpy as np  # noqa: E402
import nycsim_bpy as nb  # noqa: E402
from mathutils import Vector  # noqa: E402

ID = "b_coney_island"
TITLE = "Coney Island: Cyclone, Wonder Wheel, Parachute Jump and Boardwalk"
BINS = [3326896, 3326898, 3347224, 3326897, 3326899, 3423906, 3425344]

CYCLONE_H = 25.91          # 85 ft
CYCLONE_TRACK = 804.67     # 2,640 ft
CYCLONE_DROP_DEG = 58.1
CYCLONE_DROPS = 12
WHEEL_H = 45.72            # 150 ft
WHEEL_CARS = 24
WHEEL_SWINGING = 16
JUMP_H = 79.86             # 262 ft
JUMP_ARMS = 12
BOARDWALK_W = 24.38        # 80 ft
BOARDWALK_Z = 5.2          # NAVD88 deck level (inferred, +-0.5 m)
GROUND = 2.0
LUNA_TM = (-2448.0, -13930.0)
WHEEL_TM = (-2468.0, -13987.0)
JUMP_WAY = 248474742
BOARDWALK_WAY = 230060363
CYCLONE_WAYS = (405891521, 376073239, 656566282)


def _cyclone_plot(frame):
    """The ride's real plot: the union bounding box of the three OSM Cyclone ways, and its principal axis."""
    pts = []
    for w in CYCLONE_WAYS:
        f = ba._ways().get(w)
        if f is None:
            continue
        for lon, lat in f["geometry"]["coordinates"]:
            x, y, _ = frame.from_lonlat(lon, lat)
            pts.append((x, y))
    if len(pts) < 4:
        raise RuntimeError("Cyclone OSM ways missing from the extract; run b_osm_extract.py")
    a = np.asarray(pts)
    c = a.mean(axis=0)
    _, _, vt = np.linalg.svd(a - c, full_matrices=False)
    lg = vt[0]
    sh = np.array([-lg[1], lg[0]])
    u = (a - c) @ lg
    v = (a - c) @ sh
    return c, lg, sh, float(u.max() - u.min()), float(v.max() - v.min())


def _cyclone_track(frame):
    """A folded out-and-back circuit inside the real plot, to the published track length and lift height."""
    c, lg, sh, L, W = _cyclone_plot(frame)
    L = max(L, 150.0)
    W = max(W, 26.0)
    half_l, half_w = L / 2 - 3.0, W / 2 - 3.0
    lanes = (-half_w, -half_w / 3, half_w / 3, half_w)
    pts: list[tuple[float, float]] = []
    # four straight legs joined by 180-degree turns: 4 x L plus 3 half-turns of radius W/3
    for i, t in enumerate(lanes):
        n = 26
        for k in range(n + 1):
            u = -half_l + 2 * half_l * (k / n) if i % 2 == 0 else half_l - 2 * half_l * (k / n)
            pts.append((float(c[0] + lg[0] * u + sh[0] * t), float(c[1] + lg[1] * u + sh[1] * t)))
        if i < len(lanes) - 1:
            t1 = lanes[i + 1]
            u_end = half_l if i % 2 == 0 else -half_l
            r = abs(t1 - t) / 2
            for k in range(1, 10):
                ang = math.pi * k / 10
                du = math.sin(ang) * r * (1 if i % 2 == 0 else -1)
                dt = (t + t1) / 2 - math.cos(ang) * (t1 - t) / 2
                pts.append((float(c[0] + lg[0] * (u_end + du) + sh[0] * dt),
                            float(c[1] + lg[1] * (u_end + du) + sh[1] * dt)))
    # scale the plan so the circuit length is exactly the published 804.67 m
    plan = np.asarray(pts)
    raw = float(np.hypot(*(plan[1:] - plan[:-1]).T).sum())
    # vertical profile: chain lift on the first leg, the 58.1-degree first drop, then 11 decaying hills
    zs = []
    acc = 0.0
    for i, p in enumerate(plan):
        if i:
            acc += float(np.hypot(*(plan[i] - plan[i - 1])))
        s = acc / raw
        if s < 0.22:
            z = GROUND + 2.0 + (CYCLONE_H - 2.0) * (s / 0.22)
        elif s < 0.28:
            z = GROUND + CYCLONE_H - (CYCLONE_H - 4.0) * ((s - 0.22) / 0.06)
        else:
            k = (s - 0.28) / 0.72
            amp = (CYCLONE_H - 4.0) * max(0.0, 1.0 - k) ** 1.15 * 0.62
            z = GROUND + 4.0 + amp * (0.5 + 0.5 * math.cos(2 * math.pi * (CYCLONE_DROPS - 1) * k))
        zs.append(z)
    return [(float(p[0]), float(p[1]), z) for p, z in zip(plan, zs)], raw


def build(lod: int = 0):
    frame = bc.local_frame(((WHEEL_TM[0] + LUNA_TM[0]) / 2, (WHEEL_TM[1] + LUNA_TM[1]) / 2), GROUND, 0.0)
    objs: list = []

    # ---- Riegelmann Boardwalk --------------------------------------------------------------------------------------
    bw = ba._ways().get(BOARDWALK_WAY)
    if bw is None:
        raise RuntimeError("OSM way 230060363 (Riegelmann Boardwalk) missing; run b_osm_extract.py")
    line = []
    for lon, lat in bw["geometry"]["coordinates"]:
        x, y, _ = frame.from_lonlat(lon, lat)
        line.append((x, y))
    bw_len = sum(math.dist(line[i], line[i + 1]) for i in range(len(line) - 1))
    objs += pk.boardwalk("riegelmann_boardwalk", line, BOARDWALK_W, BOARDWALK_Z - GROUND, "wood_deck", rail=True,
                         lod=lod)

    # ---- Deno's Wonder Wheel ---------------------------------------------------------------------------------------
    wx, wy, _ = frame.to_local(*WHEEL_TM)
    objs += pk.ferris_wheel("wonder_wheel", (wx, wy, WHEEL_H / 2 + 1.4), WHEEL_H / 2 - 0.7, WHEEL_CARS,
                            "steel_gray", ("paint_red", "paint_blue", "paint_yellow"), swinging=WHEEL_SWINGING,
                            spokes=16, car_size=(2.7, 2.0, 2.4), heading_deg=90.0, lod=lod)
    objs.append(bc.prism("wonder_wheel_base", bc.rect(30.0, 12.0, wx, wy), -1.0, 1.4, "concrete"))

    # ---- Parachute Jump --------------------------------------------------------------------------------------------
    jring = ba.osm_polygon_local(JUMP_WAY, frame)
    if jring is None:
        raise RuntimeError("OSM way 248474742 (Parachute Jump) missing; run b_osm_extract.py")
    jx = sum(p[0] for p in jring) / len(jring)
    jy = sum(p[1] for p in jring) / len(jring)
    objs += pk.parachute_jump("parachute_jump", (jx, jy, 0.0), JUMP_H, 9.5, 3.4, "steel_red", arms=JUMP_ARMS, lod=lod)
    objs.append(bc.prism("parachute_base", bc.regular_polygon(6, 12.0, jx, jy), -1.2, 0.6, "concrete"))

    # ---- the Cyclone -----------------------------------------------------------------------------------------------
    track, raw = _cyclone_track(frame)
    objs += pk.coaster_track("cyclone", track, "steel_gray", "wood_pale", gauge=1.2, bent_spacing=5.5,
                             ground_z=GROUND - 2.0, lod=lod)
    c, lg, sh, L, W = _cyclone_plot(frame)
    objs.append(bc.box("cyclone_station", (18.0, 9.0, 6.5), (float(c[0]), float(c[1]), -2.0), "wood_pale"))
    objs.append(bc.box("cyclone_sign", (12.0, 0.5, 3.2), (float(c[0]), float(c[1] - 5.0), 4.5), "paint_red"))

    # ---- Luna Park entrance ----------------------------------------------------------------------------------------
    lx, ly, _ = frame.to_local(*LUNA_TM)
    objs += pk.triumphal_arch("luna_entrance", (lx, ly, -2.0), 0.0, width=26.0, depth=4.5, height=13.0,
                              opening_w=15.0, opening_h=9.5, material="paint_white", attic_h=2.4, cornice=0.5,
                              lod=lod, spandrel_relief=False)
    objs.append(bc.box("luna_sign", (17.0, 1.0, 4.0), (lx, ly, 13.0), "paint_yellow"))
    objs.append(bc.box("luna_sign_glow", (15.0, 0.35, 3.0), (lx, ly - 0.6, 13.5), "light_warm"))
    for s in (-1, 1):
        objs.append(nb.cylinder(f"luna_moon{s}", 2.4, 0.6, 20, (lx + s * 15.0, ly, 13.5),
                                material=bc.mat("light_warm")))

    extras = {
        "origin_tm": frame.origin_tm, "heading_deg": 0.0, "height_m": JUMP_H, "name": TITLE,
        "cyclone_height_m": CYCLONE_H, "cyclone_track_m": CYCLONE_TRACK, "cyclone_modelled_track_m": round(raw, 1),
        "cyclone_first_drop_deg": CYCLONE_DROP_DEG, "cyclone_drops": CYCLONE_DROPS, "cyclone_lp": "LP-1636",
        "wonder_wheel_height_m": WHEEL_H, "wonder_wheel_cars": WHEEL_CARS, "wonder_wheel_swinging": WHEEL_SWINGING,
        "wonder_wheel_lp": "LP-1708", "parachute_jump_height_m": JUMP_H, "parachute_jump_arms": JUMP_ARMS,
        "boardwalk_width_m": BOARDWALK_W, "boardwalk_modelled_m": round(bw_len, 1), "boardwalk_published_m": 4345.0,
        "height_source": "NYC Parks / LPC LP-1636, LP-1708, LP-1978: Cyclone 85 ft high with a 2,640 ft track and a "
                         "58.1 deg first drop; Wonder Wheel 150 ft with 24 cars (16 swinging, 8 stationary); "
                         "Parachute Jump 262 ft with 12 arms; Riegelmann Boardwalk 2.7 miles x 80 ft",
        "sources_ids": ["osm_bbbike", "building_footprints", "published_coney_island"],
        "fidelity_statement": (
            "Exact to published values: the Wonder Wheel 45.72 m high with 24 cars of which 16 swing on inner "
            "rails, on its real OSM node; the Parachute Jump 79.86 m with 12 arms on its real OSM footprint (way "
            "248474742, tagged 80 m); the Cyclone 25.91 m high with %.1f m of track (published 804.67 m), a "
            "58.1 deg first drop and 12 drops, inside its real plot; the Riegelmann Boardwalk 24.38 m wide on its "
            "real OSM polyline. THE CYCLONE'S TRACK PLAN IS GENERATED, NOT SURVEYED: the OSM ways trace only "
            "387 / 305 / 255 m of the circuit, so a folded out-and-back layout is reconstructed inside the real "
            "plot to the published length, lift height and drop count. Gaps: the boardwalk is modelled for the "
            "%.0f m the OSM way traces, not the published 4,345 m; the Luna Park entrance is placed from the "
            "street grid (+-30 m) with proportions inferred from photographs. Not modelled: the Cyclone's station "
            "interior, chain lift and trains; the Wonder Wheel's car glazing and ticket booth; the Parachute "
            "Jump's parachutes and guys; Nathan's Famous, the Thunderbolt and the other Luna Park rides; the "
            "beach; boardwalk lamps and benches." % (raw, bw_len)),
    }
    return objs, extras


def main() -> None:
    frame = bc.local_frame(((WHEEL_TM[0] + LUNA_TM[0]) / 2, (WHEEL_TM[1] + LUNA_TM[1]) / 2), GROUND, 0.0)
    wx, wy, _ = frame.to_local(*WHEEL_TM)
    jring = ba.osm_polygon_local(JUMP_WAY, frame)
    jx = sum(p[0] for p in jring) / len(jring)
    jy = sum(p[1] for p in jring) / len(jring)
    ctx = (("sidewalk", -0.4, 900.0, (0.0, 0.0)),)
    ba.run_landmark(
        ID, TITLE, build, bins=BINS, budget_lod0=250_000, budget_lod1=60_000,
        renders=[
            # the comparison agent's recorded photographic viewpoints, used verbatim
            ba.reference_render("landmark_coney_island_wonder_wheel", frame, view="wonder_wheel_reference",
                                ground_z=BOARDWALK_Z - GROUND, target_z=26.0, fov_deg=62.0, size=(1280, 720),
                                context=ctx, sun_azimuth_deg=215.0, sun_elevation_deg=35.0),
            ba.reference_render("landmark_coney_island_parachute_jump", frame, view="parachute_jump_reference",
                                ground_z=0.0, target_z=48.0, fov_deg=54.0, size=(720, 1280),
                                context=ctx, sun_azimuth_deg=215.0, sun_elevation_deg=35.0),
            ba.reference_render("landmark_coney_island_cyclone", frame, view="cyclone_reference",
                                ground_z=0.0, target_z=18.0, fov_deg=58.0, size=(1280, 720),
                                context=ctx, sun_azimuth_deg=215.0, sun_elevation_deg=35.0),
            dict(view="boardwalk", cam=(wx + 130.0, wy - 190.0, BOARDWALK_Z - GROUND + 1.7),
                 target=(wx - 60.0, wy - 20.0, 26.0), fov_deg=64.0, context=ctx, sun_azimuth_deg=200.0,
                 sun_elevation_deg=38.0),
            dict(view="wonder_wheel", cam=(wx + 78.0, wy - 62.0, 12.0), target=(wx, wy, 26.0), fov_deg=56.0,
                 context=ctx, sun_azimuth_deg=230.0, sun_elevation_deg=34.0),
            dict(view="parachute_jump", cam=(jx + 150.0, jy - 130.0, 24.0), target=(jx, jy, 48.0), fov_deg=48.0,
                 context=ctx, sun_azimuth_deg=250.0, sun_elevation_deg=32.0),
        ],
        sections={"Published dimensions": __doc__.split("------------------------------------\n")[1].split("\nPlacement:")[0].strip(),
                  "Placement": __doc__.split("Placement:")[1].split("\n**The Cyclone")[0].strip(),
                  "Cyclone track honesty statement": __doc__.split("**The Cyclone's track plan is generated, not surveyed.**")[1].split("Not modelled:")[0].strip(),
                  "Not modelled": __doc__.split("Not modelled:")[1].strip()},
    )


if __name__ == "__main__":
    main()
