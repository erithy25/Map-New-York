"""Transit and street-furniture-franchise props: Cemusa bus shelter and newsstand, DOT CityRack, the Citi Bike
station parts (kiosk, tileable dock, docked bicycle) and the subway entrance kit (railing, globes, SUBWAY sign,
MTA route bullets in the official line colours).
"""
from __future__ import annotations

import math

import _core as C
import _legends as L
import _palette as P

# Order the bullets are laid out in; grouped by trunk line as the MTA brand guide groups them.
MTA_LINES = ("1", "2", "3", "4", "5", "6", "7", "A", "C", "E", "B", "D", "F", "M", "G", "J", "Z", "L", "N", "Q", "R", "W", "S")
BULLET_DIA = 0.300


def _ad_panel_material():
    return C.mat_image("AD_PANEL", L.newsstand_ad(), emission_strength=2.2, roughness=0.25)


def build_bus_shelter() -> C.Built:
    """NYC coordinated street furniture bus shelter (Grimshaw design for Cemusa): 14 ft x 5 ft footprint, 2.7 m
    high cantilevered roof on two rear columns, tempered glass panels, perforated bench, backlit ad panel end."""
    steel = P.dark_grey()
    glass = P.glass()
    seat = P.brushed()
    L_, D, H = 4.27, 1.52, 2.70
    roof = C.box("roof", (L_ + 0.16, D + 0.28, 0.075), origin=(0.0, 0.06, H - 0.075), material=steel, anchor="bottom")
    fascia = C.box("roof_fascia", (L_ + 0.16, 0.05, 0.16), origin=(0.0, 0.06 + (D + 0.28) / 2, H - 0.19), material=steel, anchor="bottom")
    parts = [roof, fascia]
    for sgn in (-1.0, 1.0):
        parts.append(C.box(f"column{int(sgn)}", (0.09, 0.14, H - 0.075), origin=(sgn * (L_ / 2 - 0.10), -D / 2 + 0.09, 0.0),
                           material=steel, anchor="bottom"))
    for i, x in enumerate((-L_ * 0.30, 0.0, L_ * 0.30)):     # rear glazing, three panels
        parts.append(C.box(f"rear_glass{i}", (L_ * 0.285, 0.012, 1.95), origin=(x, -D / 2 + 0.09, 0.62), material=glass, anchor="bottom"))
        parts.append(C.box(f"rear_mullion{i}", (0.035, 0.045, 2.05), origin=(x - L_ * 0.15, -D / 2 + 0.09, 0.58), material=steel, anchor="bottom"))
    parts.append(C.box("rear_mullion_end", (0.035, 0.045, 2.05), origin=(L_ * 0.45, -D / 2 + 0.09, 0.58), material=steel, anchor="bottom"))
    parts.append(C.box("side_glass", (0.012, D - 0.20, 1.95), origin=(-L_ / 2 + 0.05, 0.0, 0.62), material=glass, anchor="bottom"))
    # ad panel end: a backlit 1.2 x 1.8 m case
    parts.append(C.box("ad_case", (0.12, 1.30, 2.10), origin=(L_ / 2 - 0.06, 0.0, 0.0), material=steel, anchor="bottom"))
    for sgn in (-1.0, 1.0):
        parts.append(C.sign_blank(f"ad_face{int(sgn)}", "rect", 1.19, 1.79, thickness=0.006,
                                  face_material=_ad_panel_material(), back_material=steel,
                                  center=(L_ / 2 - 0.06 + sgn * 0.065, 0.0, 1.13), facing="+Y"))
        C.rotate(parts[-1], 90.0 * sgn, "Z", pivot=(L_ / 2 - 0.06 + sgn * 0.065, 0.0, 1.13))
    bench = C.box("bench_seat", (2.55, 0.42, 0.045), origin=(-L_ * 0.10, -D / 2 + 0.34, 0.435), material=seat, anchor="bottom")
    back = C.box("bench_back", (2.55, 0.035, 0.24), origin=(-L_ * 0.10, -D / 2 + 0.14, 0.60), material=seat, anchor="bottom")
    legs = [C.box(f"bench_leg{i}", (0.05, 0.36, 0.435), origin=(-L_ * 0.10 + x, -D / 2 + 0.34, 0.0), material=steel, anchor="bottom")
            for i, x in enumerate((-1.15, 0.0, 1.15))]
    lamp = C.box("roof_lamp", (L_ * 0.7, 0.14, 0.03), origin=(0.0, 0.0, H - 0.085), material=P.lamp(), anchor="center")
    return C.Built(lod0=parts + [bench, back, lamp] + legs,
                   extra={"key_dims_m": {"length": L_, "depth": D, "height": H, "ad_panel": [1.19, 1.79]},
                          "screen_slots": ["AD_PANEL"]})


def build_newsstand() -> C.Built:
    """Licensed sidewalk newsstand (Cemusa standard unit): stainless kiosk within the 72 sq ft legal footprint
    (NYC Admin Code 20-231), serving window, magazine racks, lit header and an end ad panel."""
    steel = P.brushed()
    dark = P.dark_grey()
    glass = P.glass()
    L_, D, H = 3.66, 1.83, 2.90
    body = C.box("body", (L_, D, H - 0.12), origin=(0, 0, 0.0), material=steel, anchor="bottom", bevel=0.02)
    roof = C.box("roof", (L_ + 0.18, D + 0.18, 0.12), origin=(0.0, 0.0, H - 0.12), material=dark, anchor="bottom")
    header = C.box("header_sign", (L_ * 0.86, 0.05, 0.34), origin=(0.0, D / 2 + 0.02, H - 0.62), material=P.lamp_warm(), anchor="bottom")
    window = C.box("serving_window", (1.25, 0.06, 1.05), origin=(-L_ * 0.16, D / 2 - 0.01, 1.05), material=glass, anchor="bottom")
    shelf = C.box("counter_shelf", (1.35, 0.28, 0.05), origin=(-L_ * 0.16, D / 2 + 0.12, 1.00), material=steel, anchor="bottom")
    parts = [body, roof, header, window, shelf]
    for i in range(3):                                   # magazine display racks beside the window
        parts.append(C.box(f"rack{i}", (0.62, 0.16, 0.06), origin=(L_ * 0.24, D / 2 + 0.08, 1.30 - 0.32 * i), material=steel, anchor="bottom"))
        parts.append(C.box(f"rack_back{i}", (0.62, 0.02, 0.28), origin=(L_ * 0.24, D / 2 + 0.01, 1.34 - 0.32 * i), material=dark, anchor="bottom"))
    for sgn in (-1.0, 1.0):
        panel = C.sign_blank(f"ad{int(sgn)}", "rect", 0.92, 1.83, thickness=0.006, face_material=_ad_panel_material(),
                             back_material=steel, center=(sgn * (L_ / 2 + 0.012), 0.0, 1.35))
        C.rotate(panel, 90.0 * sgn, "Z", pivot=(sgn * (L_ / 2 + 0.012), 0.0, 1.35))
        parts.append(panel)
    door = C.box("service_door", (0.80, 0.04, 2.00), origin=(L_ * 0.30, -D / 2 - 0.005, 0.0), material=dark, anchor="bottom")
    parts.append(door)
    return C.Built(lod0=parts, extra={"key_dims_m": {"length": L_, "depth": D, "height": H,
                                                     "footprint_sqft": round(L_ * D * 10.7639, 1)},
                                      "screen_slots": ["AD_PANEL"]})


def build_cityrack() -> C.Built:
    """DOT CityRack bicycle hoop: 1.9 in (48 mm) OD galvanised pipe, 34 in (0.86 m) tall, 30 in (0.76 m) wide."""
    steel = P.galv()
    w, h, r = 0.760, 0.864, 0.024
    pts = ([(-w / 2, 0.0, 0.0), (-w / 2, 0.0, h - 0.22)] +
           C.bezier_points([(-w / 2, 0.0, h - 0.22), (-w / 2, 0.0, h + 0.041), (w / 2, 0.0, h + 0.041), (w / 2, 0.0, h - 0.22)], 9) +
           [(w / 2, 0.0, 0.0)])
    hoop = C.tube("hoop", pts, r, 12, material=steel)
    flanges = [C.lathe(f"flange{int(sgn)}", [(0.075, 0.0), (0.075, 0.012), (0.040, 0.030)], 12, material=steel,
                       origin=(sgn * w / 2, 0.0, 0.0)) for sgn in (-1.0, 1.0)]
    return C.Built(lod0=[hoop] + flanges, extra={"key_dims_m": {"width": w, "height": h, "pipe_od": 0.048}})


def build_citibike_kiosk() -> C.Built:
    """Citi Bike station kiosk: solar-powered payment terminal with the station map panel, ~1.9 m tall."""
    dark = C.mat_solid("citibike_housing", "#20262B", 0.45, 0.3)
    blue = P.citibike_blue()
    steel = P.brushed()
    base = C.box("base", (0.62, 0.34, 0.08), material=dark, anchor="bottom", bevel=0.012)
    column = C.box("column", (0.34, 0.24, 0.98), origin=(0, 0, 0.08), material=dark, anchor="bottom", bevel=0.015)
    head = C.box("terminal", (0.44, 0.30, 0.42), origin=(0, 0, 1.06), material=dark, anchor="bottom", bevel=0.02)
    screen = C.box("terminal_screen", (0.28, 0.010, 0.22), origin=(0.0, 0.152, 1.30),
                   material=C.mat_emissive("SCREEN_CITIBIKE", "#8FC7F0", 2.0, base="#0E1418"), anchor="center")
    keys = [C.box(f"key{i}", (0.032, 0.010, 0.026), origin=(-0.09 + 0.06 * (i % 4), 0.152, 1.14 - 0.04 * (i // 4)),
                  material=P.dark_grey(), anchor="center") for i in range(8)]
    mast = C.cyl("map_mast", 0.026, 0.30, 10, origin=(0.0, -0.06, 1.30), material=steel)
    board = C.box("map_board", (0.66, 0.045, 0.70), origin=(0.0, -0.06, 1.30), material=dark, anchor="bottom", bevel=0.010)
    map_face = C.sign_blank("map_face", "rect", 0.60, 0.64, thickness=0.004,
                            face_material=C.mat_solid("citibike_map", "#1B4FA0", 0.4), back_material=dark,
                            center=(0.0, -0.06 + 0.026, 1.65))
    band = C.box("brand_band", (0.34, 0.006, 0.09), origin=(0.0, 0.122, 0.72), material=blue, anchor="center")
    return C.Built(lod0=[base, column, head, screen, mast, board, map_face, band] + keys,
                   extra={"key_dims_m": {"height": 2.00, "terminal_height": 1.48, "map_board": [0.66, 0.70]}})


def build_citibike_dock() -> C.Built:
    """One Citi Bike dock point, tileable along X at the observed 0.90 m station pitch: base pan, wheel fork,
    locking head and status LED."""
    dark = C.mat_solid("citibike_dock_grey", "#2B3238", 0.5, 0.3)
    steel = P.brushed()
    pitch = 0.90
    pan = C.box("dock_pan", (pitch, 0.42, 0.075), material=dark, anchor="bottom", bevel=0.010)
    rail = C.box("dock_rail", (pitch, 0.10, 0.055), origin=(0.0, -0.14, 0.075), material=dark, anchor="bottom")
    fork_l = C.box("fork_l", (0.028, 0.30, 0.44), origin=(-0.045, 0.06, 0.075), material=steel, anchor="bottom")
    fork_r = C.box("fork_r", (0.028, 0.30, 0.44), origin=(0.045, 0.06, 0.075), material=steel, anchor="bottom")
    for f in (fork_l, fork_r):
        C.rotate(f, -8.0, "X", pivot=(0.0, 0.06, 0.075))
    head = C.box("lock_head", (0.145, 0.115, 0.185), origin=(0.0, -0.055, 0.13), material=dark, anchor="bottom", bevel=0.010)
    led = C.box("status_led", (0.030, 0.010, 0.012), origin=(0.0, -0.002, 0.275),
                material=C.mat_emissive("LED_DOCK", "#3FD46A", 4.0), anchor="center")
    plate = C.box("dock_number", (0.055, 0.008, 0.040), origin=(0.055, -0.004, 0.235), material=P.white_paint(), anchor="center")
    return C.Built(lod0=[pan, rail, fork_l, fork_r, head, led, plate],
                   extra={"key_dims_m": {"pitch": pitch, "depth": 0.42, "height": 0.52},
                          "tileable_axis": "X", "tile_pitch_m": pitch})


def build_citibike_bike() -> C.Built:
    """Citi Bike (Bixi-derived) bicycle as parked in a dock: 1.80 m long, 26 in wheels, step-through frame,
    front basket, full fenders, chain guard, three-speed hub. Nose (forward direction) along +Y."""
    blue = P.citibike_blue()
    dark = P.black_matte()
    tyre = P.rubber()
    steel = P.brushed()
    r_w = 0.330                              # 26 in wheel
    y_f, y_r = 0.565, -0.565                 # 1.13 m wheelbase
    parts = []
    for tag, y in (("front", y_f), ("rear", y_r)):
        parts.append(C.torus(f"tyre_{tag}", r_w - 0.024, 0.024, 20, 8, origin=(0.0, y, r_w), material=tyre, axis="X"))
        parts.append(C.torus(f"rim_{tag}", r_w - 0.035, 0.014, 20, 6, origin=(0.0, y, r_w), material=steel, axis="X"))
        parts.append(C.cyl(f"hub_{tag}", 0.032, 0.09, 10, origin=(-0.045, y, r_w), material=steel, axis="X"))
        for k in range(8):                    # spoke pairs, enough to read as a wheel
            a = math.pi * k / 8
            parts.append(C.tube(f"spoke_{tag}_{k}", [(0.0, y - (r_w - 0.04) * math.cos(a), r_w - (r_w - 0.04) * math.sin(a)),
                                                     (0.0, y + (r_w - 0.04) * math.cos(a), r_w + (r_w - 0.04) * math.sin(a))],
                                0.0035, 4, material=steel))
        parts.append(C.tube(f"fender_{tag}", [(0.0, y + (r_w + 0.03) * math.cos(a), r_w + (r_w + 0.03) * math.sin(a))
                                              for a in [math.radians(v) for v in range(20, 165, 18)]], 0.028, 4, material=blue))
    # step-through frame
    head_top = C.Vector((0.0, 0.455, 1.010))
    bb = C.Vector((0.0, -0.075, 0.285))
    seat_top = C.Vector((0.0, -0.335, 0.905))
    parts.append(C.tube("down_tube", C.bezier_points([tuple(head_top), (0.0, 0.30, 0.60), (0.0, 0.05, 0.36), tuple(bb)], 10),
                        0.033, 10, material=blue))
    parts.append(C.tube("top_tube", C.bezier_points([tuple(head_top), (0.0, 0.15, 0.86), (0.0, -0.16, 0.90), tuple(seat_top)], 10),
                        0.030, 10, material=blue))
    parts.append(C.tube("seat_tube", [tuple(seat_top), tuple(bb)], 0.028, 10, material=blue))
    for sgn in (-1.0, 1.0):
        parts.append(C.tube(f"chain_stay{int(sgn)}", [(sgn * 0.05, -0.10, 0.285), (sgn * 0.045, y_r, r_w)], 0.016, 6, material=blue))
        parts.append(C.tube(f"seat_stay{int(sgn)}", [(sgn * 0.03, -0.30, 0.855), (sgn * 0.045, y_r, r_w)], 0.014, 6, material=blue))
        parts.append(C.tube(f"fork{int(sgn)}", [(sgn * 0.035, 0.455, 0.995), (sgn * 0.042, y_f, r_w)], 0.018, 6, material=blue))
    parts.append(C.tube("steerer", [(0.0, 0.455, 0.980), (0.0, 0.412, 1.115)], 0.020, 8, material=steel))
    parts.append(C.tube("handlebar", C.bezier_points([(-0.275, 0.335, 1.115), (-0.10, 0.412, 1.125), (0.10, 0.412, 1.125),
                                                      (0.275, 0.335, 1.115)], 9), 0.016, 8, material=steel))
    for sgn in (-1.0, 1.0):
        parts.append(C.cyl(f"grip{int(sgn)}", 0.019, 0.11, 8, origin=(sgn * 0.275, 0.335, 1.115), material=dark, axis="X"))
    saddle = C.lathe("saddle", [(0.0, 0.0), (0.055, 0.012), (0.075, 0.030), (0.055, 0.048), (0.0, 0.055)], 12,
                     material=dark, origin=(0.0, -0.335, 0.905), smooth=True)
    saddle.data.transform(C.Matrix.Diagonal((1.0, 2.4, 1.0, 1.0)))
    C.move(saddle, 0.0, -0.335 * -1.4, 0.0)
    parts.append(saddle)
    parts.append(C.tube("seat_post", [(0.0, -0.335, 0.820), (0.0, -0.335, 0.905)], 0.017, 8, material=steel))
    basket = C.box("basket", (0.34, 0.28, 0.22), origin=(0.0, 0.53, 0.86), material=steel, anchor="bottom", bevel=0.012)
    basket_front = C.box("basket_face", (0.32, 0.02, 0.20), origin=(0.0, 0.665, 0.87), material=P.silver_paint(), anchor="bottom")
    chain_guard = C.box("chain_guard", (0.020, 0.42, 0.13), origin=(0.055, 0.06, 0.245), material=blue, anchor="center")
    crank = C.cyl("crank", 0.055, 0.02, 12, origin=(0.055, -0.075, 0.285), material=steel, axis="X")
    pedal = C.box("pedal", (0.075, 0.085, 0.020), origin=(0.115, -0.075, 0.225), material=dark, anchor="center")
    lamp = C.lathe("headlamp", [(0.0, 0.0), (0.030, 0.008), (0.034, 0.030)], 10, material=P.lamp(), axis="Y",
                   origin=(0.0, 0.60, 0.98))
    return C.Built(lod0=parts + [basket, basket_front, chain_guard, crank, pedal, lamp], lod1_kind="decimated",
                   extra={"key_dims_m": {"length": 1.80, "wheelbase": 1.13, "wheel_dia": 0.66, "handlebar_height": 1.13},
                          "facing_blender": "+Y (bike nose)"})


def _globe_post(color: str, name: str) -> C.Built:
    """MTA subway entrance globe on its post: green = entrance open at all times, red = exit only / limited hours."""
    green_paint = P.mta_green()
    mat = P.globe_green() if color == "green" else P.globe_red()
    base = C.lathe("base", [(0.115, 0.0), (0.115, 0.055), (0.090, 0.09), (0.070, 0.16)], 16, material=green_paint)
    post = C.lathe("post", [(0.055, 0.14), (0.048, 2.42)], 16, material=green_paint, smooth=True)
    collar = C.lathe("collar", [(0.048, 2.40), (0.070, 2.44), (0.062, 2.50)], 16, material=green_paint)
    globe = C.lathe("globe", [(0.0, 0.0), (0.075, 0.030), (0.135, 0.100), (0.168, 0.190), (0.135, 0.280),
                              (0.075, 0.350), (0.0, 0.380)], 20, material=mat, origin=(0.0, 0.0, 2.50), smooth=True)
    finial = C.lathe("finial", [(0.030, 0.0), (0.040, 0.02), (0.020, 0.055), (0.0, 0.070)], 10, material=green_paint,
                     origin=(0.0, 0.0, 2.875))
    del name
    return C.Built(lod0=[base, post, collar, globe, finial],
                   extra={"key_dims_m": {"globe_dia": 0.336, "globe_centre_height": 2.69, "overall_height": 2.945},
                          "globe_meaning": "green = entrance always open; red = exit only or part-time entrance",
                          "emissive_material": f"LAMP_GLOBE_{color.upper()}"})


def build_globe_green() -> C.Built:
    return _globe_post("green", "green")


def build_globe_red() -> C.Built:
    return _globe_post("red", "red")


def build_subway_entrance() -> C.Built:
    """Subway stair entrance: green painted steel railing around a 3.05 x 1.83 m stair opening, descending treads
    and the black-and-white SUBWAY sign in its frame on the railing head."""
    green = P.mta_green()
    dark = P.black_matte()
    conc = P.concrete()
    W, Ly = 1.83, 3.05                        # opening width (X) and length (Y, the descent direction is -Y)
    rail_h, pipe = 1.07, 0.024
    parts = []
    steps = 9
    for i in range(steps):
        z = -0.18 * (i + 1)
        y = Ly / 2 - 0.30 * (i + 1)
        parts.append(C.box(f"tread{i}", (W, 0.30, 0.05), origin=(0.0, y, z), material=conc, anchor="bottom"))
        parts.append(C.box(f"riser{i}", (W, 0.04, 0.18), origin=(0.0, y + 0.15, z), material=conc, anchor="bottom"))
    parts.append(C.box("shaft_wall_l", (0.14, Ly, 2.4), origin=(-(W / 2 + 0.07), 0.0, -2.4), material=dark, anchor="bottom"))
    parts.append(C.box("shaft_wall_r", (0.14, Ly, 2.4), origin=(W / 2 + 0.07, 0.0, -2.4), material=dark, anchor="bottom"))
    parts.append(C.box("shaft_back", (W + 0.28, 0.14, 2.4), origin=(0.0, -Ly / 2 - 0.07, -2.4), material=dark, anchor="bottom"))
    # railing: both long sides plus the head, with newel posts and two horizontal rails
    posts_xy = []
    for sgn in (-1.0, 1.0):
        for k in range(5):
            posts_xy.append((sgn * (W / 2 + 0.10), Ly / 2 - Ly * k / 4))
    posts_xy += [(-W / 2 * 0.5, Ly / 2 + 0.10), (W / 2 * 0.5, Ly / 2 + 0.10)]
    for i, (px, py) in enumerate(posts_xy):
        parts.append(C.cyl(f"newel{i}", 0.030, rail_h, 10, origin=(px, py, 0.0), material=green))
        parts.append(C.lathe(f"newel_cap{i}", [(0.036, 0.0), (0.030, 0.020), (0.0, 0.042)], 10, material=green,
                             origin=(px, py, rail_h)))
    for sgn in (-1.0, 1.0):
        for z in (rail_h - 0.03, rail_h * 0.55):
            parts.append(C.tube(f"rail{int(sgn)}{int(z * 100)}", [(sgn * (W / 2 + 0.10), Ly / 2, z),
                                                                  (sgn * (W / 2 + 0.10), -Ly / 2, z)], pipe, 8, material=green))
    for z in (rail_h - 0.03, rail_h * 0.55):
        parts.append(C.tube(f"head_rail{int(z * 100)}", [(-(W / 2 + 0.10), Ly / 2 + 0.10, z), (-W / 2 * 0.5, Ly / 2 + 0.10, z)],
                            pipe, 8, material=green))
        parts.append(C.tube(f"head_rail2{int(z * 100)}", [(W / 2 * 0.5, Ly / 2 + 0.10, z), (W / 2 + 0.10, Ly / 2 + 0.10, z)],
                            pipe, 8, material=green))
    # SUBWAY sign frame over the head rail
    frame = C.box("sign_frame", (1.04, 0.06, 0.34), origin=(0.0, Ly / 2 + 0.10, 1.32), material=green, anchor="center")
    for sgn in (-1.0, 1.0):
        plate = C.sign_blank(f"subway_plate{int(sgn)}", "rect", 0.96, 0.26, thickness=0.004,
                             face_material=C.mat_image("SUBWAY_SIGN", L.subway_wordmark(), roughness=0.4),
                             back_material=dark, center=(0.0, Ly / 2 + 0.10 + sgn * 0.034, 1.32),
                             facing="+Y" if sgn > 0 else "-Y")
        parts.append(plate)
    for sgn in (-1.0, 1.0):
        parts.append(C.cyl(f"sign_post{int(sgn)}", 0.024, 1.20, 8, origin=(sgn * 0.46, Ly / 2 + 0.10, 0.0), material=green))
    parts.append(frame)
    return C.Built(lod0=parts,
                   extra={"key_dims_m": {"opening_w": W, "opening_l": Ly, "railing_height": rail_h,
                                         "tread_rise": 0.18, "tread_run": 0.30, "modelled_depth": 2.4},
                          "descent_direction_blender": "-Y",
                          "globe_assets": ["subway_globe_green", "subway_globe_red"]})


def build_mta_bullets() -> C.Built:
    """The 23 MTA route bullets as separate meshes, each with its own ``MTA_<line>`` material in the official
    line colour. Node translation carries only the layout offset — zero it to place a bullet."""
    objs = []
    colors = {}
    for i, line in enumerate(MTA_LINES):
        hexc = C.MTA_LINE_COLORS[line]
        colors[line] = hexc
        mat = C.mat_solid(f"MTA_{line}", hexc, 0.35)
        mat["nycsim_mta_line"] = line
        mat["nycsim_mta_hex"] = hexc
        disc = C.lathe(f"bullet_{line}_disc", [(0.0, 0.0), (BULLET_DIA / 2 * 0.94, 0.0), (BULLET_DIA / 2, 0.006),
                                               (BULLET_DIA / 2, 0.014), (BULLET_DIA / 2 * 0.94, 0.020), (0.0, 0.020)],
                       28, material=mat, axis="Y", origin=(0.0, -0.010, 0.0))
        glyph_hex = "#111111" if line in C.MTA_DARK_TEXT_LINES else "#FFFFFF"
        glyph_mat = C.mat_solid(f"MTA_GLYPH_{'DARK' if line in C.MTA_DARK_TEXT_LINES else 'LIGHT'}", glyph_hex, 0.4)
        glyph = C.text_mesh(f"bullet_{line}_glyph", line, BULLET_DIA * 0.62, material=glyph_mat, depth=0.004,
                            center=(0.0, 0.011, 0.0))
        ob = C.join([disc, glyph], f"bullet_{line}")
        ob.location = ((i % 8) * 0.38 - 1.33, 0.0, 1.30 - 0.38 * (i // 8))
        objs.append(ob)
    lods = [C.decimated_copy(o, 0.35, o.name + "_LOD1") for o in objs]
    return C.Built(lod0=objs, lod1=lods, keep_separate=True,
                   extra={"anchor": {"origin": "bullet_center", "up_blender": "+Z", "facing_blender": "+Y",
                                     "up_gltf": "+Y", "facing_gltf": "-Z"},
                          "mta_colors": colors, "bullet_diameter_m": BULLET_DIA,
                          "node_names": [f"bullet_{n}" for n in MTA_LINES],
                          "key_dims_m": {"diameter": BULLET_DIA, "thickness": 0.020}})


SPECS = [
    C.PropSpec("bus_shelter_cemusa", "furniture", "bus_shelter", build_bus_shelter, (4.43, 1.80, 2.70),
               "NYC coordinated street furniture bus shelter (Grimshaw design, Cemusa/JCDecaux franchise): 14 ft x 5 ft "
               "footprint, 2.7 m cantilevered roof on two rear columns, tempered glass rear and side glazing, "
               "perforated steel bench and a backlit 1.2 x 1.8 m ad case at one end.",
               tags=["dot", "franchise"], tolerance=0.10),
    C.PropSpec("newsstand_stainless", "furniture", "newsstand", build_newsstand, (3.84, 2.18, 2.90),
               "Licensed sidewalk newsstand, Cemusa standard unit: stainless kiosk 12 x 6 ft (within the 72 sq ft legal "
               "maximum of NYC Admin Code 20-231), serving window with counter shelf, magazine racks, lit header and "
               "end ad panels.", tags=["dcwp", "franchise"], tolerance=0.10),
    C.PropSpec("bike_rack_cityrack", "furniture", "bike_rack", build_cityrack, (0.91, 0.15, 0.864),
               "NYC DOT CityRack: inverted-U bicycle hoop in 1.9 in galvanised pipe, 34 in tall and 30 in wide, on two "
               "floor flanges.", tags=["dot"], tolerance=0.10),
    C.PropSpec("citibike_kiosk", "furniture", "citibike_dock", build_citibike_kiosk, (0.66, 0.34, 2.00),
               "Citi Bike station kiosk: solar payment terminal with a touchscreen and keypad under the station map "
               "board, 2.0 m tall. Placed once per station; the dock run is citibike_dock_unit.",
               variants=["citibike_dock_unit", "citibike_bike"], tags=["citibike", "variant:1"], tolerance=0.10),
    C.PropSpec("citibike_dock_unit", "furniture", "citibike_dock", build_citibike_dock, (0.90, 0.48, 0.53),
               "One Citi Bike dock point — tileable along X at the 0.90 m station pitch used by the props table, so a "
               "station of capacity N is N instances end to end. Base pan, wheel fork, locking head, status LED.",
               variants=["citibike_kiosk", "citibike_bike"], tags=["citibike", "tileable", "variant:2"], tolerance=0.08),
    C.PropSpec("citibike_bike", "furniture", "citibike_dock", build_citibike_bike, (0.60, 1.80, 1.15),
               "Citi Bike bicycle as parked in a dock: Bixi-derived step-through frame, 26 in wheels on a 1.13 m "
               "wheelbase, front basket, full fenders, chain guard; nose along +Y.",
               variants=["citibike_kiosk", "citibike_dock_unit"], tags=["citibike", "variant:3"], tolerance=0.12),
    C.PropSpec("subway_entrance", "furniture", "subway_entrance", build_subway_entrance, (2.11, 3.33, 3.89),
               "MTA subway stair entrance: green painted steel railing (42 in) around a 3.05 x 1.83 m stair opening "
               "with concrete treads at 7 in rise / 12 in run descending 2.4 m, and the double-sided SUBWAY plate in "
               "its frame over the head rail. Globes are separate assets keyed to the has_globe attribute. The bounding box spans "
               "1.49 m above grade and 2.40 m below it (the modelled stair shaft).",
               variants=["subway_globe_green", "subway_globe_red", "mta_line_bullets"], tags=["mta"], tolerance=0.10,
               lod1_ratio=0.2),
    C.PropSpec("subway_globe_green", "furniture", "subway_entrance", build_globe_green, (0.34, 0.34, 2.95),
               "MTA entrance globe, green (entrance open at all times): 0.34 m glass globe on a green painted post, "
               "globe centre at 2.69 m. Emissive material LAMP_GLOBE_GREEN.",
               variants=["subway_globe_red", "subway_entrance"], tags=["mta"], tolerance=0.08),
    C.PropSpec("subway_globe_red", "furniture", "subway_entrance", build_globe_red, (0.34, 0.34, 2.95),
               "MTA entrance globe, red (exit only or part-time entrance). Emissive material LAMP_GLOBE_RED.",
               variants=["subway_globe_green", "subway_entrance"], tags=["mta"], tolerance=0.08),
    C.PropSpec("mta_line_bullets", "furniture", "mta_bullet", build_mta_bullets, (2.96, 0.024, 1.06),
               "The 23 MTA route bullets (1 2 3 4 5 6 7 A C E B D F M G J Z L N Q R W S) as separate 0.30 m meshes, "
               "each with its own MTA_<line> material in the official line colour from the MTA brand guidelines; "
               "yellow bullets carry black glyphs, all others white. Laid out in a grid for inspection — the node "
               "translation is layout only.", tags=["mta", "decal"], tolerance=0.15),
]
