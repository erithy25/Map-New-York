"""Horizontal and vertical facade trim: pressed-metal, brick-corbel and stone cornices; string courses; quoins;
pilasters; water tables, lintels, sills, keystones and datestones (23 pieces).

All runs are modelled **1.00 m long in X** so the assembler can repeat them along a wall (the quoins and pilasters
are one unit tall / one storey tall instead). Origin: bottom-centre on the wall plane, y = 0 = the brick face,
+Y into the building.
"""
from __future__ import annotations

import kitlib as K
import pieces_common as P

RUN = 1.000            # every horizontal trim piece is exactly 1 m of wall
HALF = RUN / 2


# --------------------------------------------------------------------------- pressed-metal cornices
def _metal_cornice(m: K.Mesh, profile, mat: str, bracket_pitch: float, bracket_proj: float, bracket_h: float,
                   *, dentil: bool = False, frieze_z: float = 0.0) -> None:
    """Sheet-metal cornice run of 1 m: swept crown profile, brackets and an optional dentil course."""
    m.extrude_profile(profile, -HALF, HALF, mat, closed=True, caps=True, flip=True)
    n = max(1, int(round(RUN / bracket_pitch)))
    for k in range(n):
        cx = -HALF + RUN * (k + 0.5) / n
        P.corbel_bracket(m, cx, 0.0, frieze_z, frieze_z + bracket_h, bracket_proj, mat, width=0.085)
    if dentil:
        P.dentils(m, -HALF, HALF, frieze_z + bracket_h + 0.02, frieze_z + bracket_h + 0.11, -0.055, 0.075, mat, pitch=0.105)


@K.register("cornice_pressed_metal_a", "cornice", nominal_size=(1.0, 0.542, 0.92),
            description="Pressed galvanised-iron tenement cornice, profile A: 0.46 m projection, cyma crown over a dentil course "
                        "and scrolled brackets at 0.50 m (1880-1900 Old Law tenement).",
            features=["cornice"], budget=1400)
def _cornice_a():
    m = K.Mesh()
    prof = [(0.0, 0.30), (-0.10, 0.34), (-0.20, 0.46), (-0.34, 0.56), (-0.44, 0.70), (-0.40, 0.82),
            (-0.28, 0.90), (0.0, 0.92), (0.0, 0.30)]
    _metal_cornice(m, prof, "metal_panel", 0.50, 0.16, 0.30, dentil=False, frieze_z=0.0)
    m.box((-HALF, -0.055, 0.0), (HALF, P.WYTHE, 0.30), "metal_panel")                    # frieze board
    P.dentils(m, -HALF, HALF, 0.30, 0.39, -0.055, 0.075, "metal_panel", pitch=0.105)
    m.box((-HALF, -0.075, 0.39), (HALF, P.WYTHE, 0.44), "metal_panel")                   # bed mould
    return m


@K.register("cornice_pressed_metal_b", "cornice", nominal_size=(1.0, 0.662, 1.15),
            description="Pressed-metal cornice, profile B: deep 0.56 m modillion cornice with a panelled frieze and paired "
                        "console brackets at 0.62 m (1890-1910 New Law tenement / flats).",
            features=["cornice"], budget=1400)
def _cornice_b():
    m = K.Mesh()
    prof = [(0.0, 0.46), (-0.14, 0.50), (-0.30, 0.62), (-0.46, 0.76), (-0.56, 0.94), (-0.50, 1.08),
            (-0.30, 1.14), (0.0, 1.15), (0.0, 0.46)]
    m.extrude_profile(prof, -HALF, HALF, "metal_panel", closed=True, caps=True, flip=True)
    m.box((-HALF, -0.075, 0.0), (HALF, P.WYTHE, 0.46), "metal_panel")                    # panelled frieze
    for k in range(3):
        cx = -HALF + RUN * (k + 0.5) / 3
        m.box((cx - 0.135, -0.095, 0.06), (cx + 0.135, -0.075, 0.40), "metal_panel")     # sunk frieze panel
    for k in (0, 1):
        for d in (-0.055, 0.055):
            P.corbel_bracket(m, -HALF + RUN * (k + 0.5) / 2 + d, 0.0, 0.46, 0.80, 0.22, "metal_panel", width=0.075)
    P.dentils(m, -HALF, HALF, 0.46, 0.55, -0.075, 0.085, "metal_panel", pitch=0.09)
    return m


@K.register("cornice_pressed_metal_c", "cornice", nominal_size=(1.0, 0.442, 0.62),
            description="Pressed-metal cornice, profile C: shallow 0.34 m ogee crown with a bead-and-reel band and small brackets "
                        "at 0.33 m (narrow rowhouse / rear cornice).",
            features=["cornice"], budget=1400)
def _cornice_c():
    m = K.Mesh()
    prof = [(0.0, 0.20), (-0.09, 0.24), (-0.20, 0.34), (-0.34, 0.46), (-0.28, 0.56), (-0.12, 0.61),
            (0.0, 0.62), (0.0, 0.20)]
    _metal_cornice(m, prof, "metal_panel", 0.333, 0.11, 0.20, frieze_z=0.0)
    m.box((-HALF, -0.045, 0.0), (HALF, P.WYTHE, 0.20), "metal_panel")
    P.dentils(m, -HALF, HALF, 0.20, 0.26, -0.045, 0.055, "metal_panel", pitch=0.083)
    return m


@K.register("cornice_bracket", "cornice", nominal_size=(0.15, 0.402, 0.6),
            description="Single scrolled pressed-metal console bracket, 0.60 m high with a 0.28 m scroll, for spacing under any "
                        "cornice or hood.",
            features=["cornice"], budget=400)
def _cornice_bracket():
    m = K.Mesh()
    P.corbel_bracket(m, 0.0, 0.0, 0.0, 0.60, 0.28, "metal_panel", width=0.115, scroll=7)
    m.box((-0.075, -0.03, 0.0), (0.075, P.WYTHE, 0.055), "metal_panel")
    m.box((-0.075, -0.30, 0.545), (0.075, P.WYTHE, 0.60), "metal_panel")
    return m


@K.register("cornice_brick_corbel", "cornice", nominal_size=(1.005, 0.342, 0.539),
            description="Corbelled brick cornice: three stepped courses plus a saw-tooth (dogtooth) course, 0.24 m total "
                        "projection, over a soldier band (1900-1930 brick tenement / warehouse).",
            features=["cornice"], budget=1400)
def _cornice_corbel():
    m = K.Mesh()
    z = 0.0
    m.box((-HALF, -0.02, z), (HALF, P.WYTHE, z + P.BRICK_LEN), "red_brick")               # soldier band
    z += P.BRICK_LEN
    for k, proj in enumerate((0.055, 0.110, 0.165)):                                      # corbelled courses
        m.box((-HALF, -proj, z), (HALF, P.WYTHE, z + P.BRICK_COURSE), "red_brick")
        z += P.BRICK_COURSE
    n = 11                                                                                # dogtooth course
    for k in range(n):
        cx = -HALF + RUN * (k + 0.5) / n
        m.box((cx - 0.048, -0.235, z), (cx + 0.048, -0.055, z + P.BRICK_COURSE), "red_brick")
    m.box((-HALF, -0.055, z), (HALF, P.WYTHE, z + P.BRICK_COURSE), "red_brick")
    z += P.BRICK_COURSE
    m.box((-HALF, -0.240, z), (HALF, P.WYTHE, z + 0.075), "precast")                      # coping
    return m


@K.register("cornice_stone", "cornice", nominal_size=(1.0, 0.497, 0.78),
            description="Limestone modillion cornice: architrave, plain frieze, egg-and-dart bed mould, modillions at 0.33 m and "
                        "a cyma crown (bank / institutional / apartment house).",
            features=["cornice"], budget=1400)
def _cornice_stone():
    m = K.Mesh()
    m.box((-HALF, -0.075, 0.0), (HALF, P.WYTHE, 0.10), "limestone")                        # architrave
    m.box((-HALF, -0.055, 0.10), (HALF, P.WYTHE, 0.32), "limestone")                       # frieze
    m.box((-HALF, -0.135, 0.32), (HALF, P.WYTHE, 0.40), "limestone")                       # bed mould
    for k in range(3):                                                                     # modillions
        cx = -HALF + RUN * (k + 0.5) / 3
        m.box((cx - 0.070, -0.330, 0.40), (cx + 0.070, -0.135, 0.50), "limestone")
    prof = [(-0.135, 0.40), (-0.395, 0.50), (-0.395, 0.62), (-0.30, 0.72), (-0.16, 0.78), (0.0, 0.78), (0.0, 0.40)]
    m.extrude_profile(prof, -HALF, HALF, "limestone", closed=True, caps=True, flip=True)
    return m


@K.register("cornice_return_end", "cornice", nominal_size=(0.86, 0.542, 0.92),
            description="End return for the pressed-metal cornice profile A: the crown mitred round the corner and closed with a "
                        "return panel (used at party walls and building corners).",
            features=["cornice"], budget=1000)
def _cornice_return():
    m = K.Mesh()
    prof = [(0.0, 0.30), (-0.10, 0.34), (-0.20, 0.46), (-0.34, 0.56), (-0.44, 0.70), (-0.40, 0.82),
            (-0.28, 0.90), (0.0, 0.92), (0.0, 0.30)]
    m.extrude_profile(prof, -0.21, 0.21, "metal_panel", closed=True, caps=True, flip=True)
    m.box((-0.21, -0.055, 0.0), (0.21, P.WYTHE, 0.30), "metal_panel")
    P.corbel_bracket(m, 0.0, 0.0, 0.0, 0.30, 0.16, "metal_panel", width=0.085)
    # mitred return: the same profile swept in Y at the +X end
    for i in range(len(prof) - 1):
        (ya, za), (yb, zb) = prof[i], prof[i + 1]
        m.face([(0.21, ya, za), (0.21 - ya, ya, za), (0.21 - yb, yb, zb), (0.21, yb, zb)], "metal_panel", flip=True)
    m.box((0.21, -0.055, 0.0), (0.21 + 0.055, P.WYTHE, 0.30), "metal_panel")
    return m


# --------------------------------------------------------------------------- string courses
@K.register("string_course_brick_soldier", "string_course", nominal_size=(1.0, 0.127, 0.194),
            description="Brick soldier-course string course, 1 m run, projecting 25 mm from the wall face.",
            features=["string_course"])
def _sc_soldier():
    m = K.Mesh()
    m.box((-HALF, -0.025, 0.0), (HALF, P.WYTHE, P.BRICK_LEN), "red_brick")
    return m


@K.register("string_course_stone_belt", "string_course", nominal_size=(1.0, 0.177, 0.25),
            description="Limestone belt course, 1 m run, 0.25 m deep with a 65 mm projection and a drip on the underside.",
            features=["string_course"])
def _sc_belt():
    m = K.Mesh()
    m.box((-HALF, -0.065, 0.0), (HALF, P.WYTHE, 0.250), "limestone")
    m.box((-HALF, -0.075, 0.205), (HALF, -0.055, 0.250), "limestone")            # projecting cap fillet
    return m


@K.register("string_course_dentil", "string_course", nominal_size=(1.0, 0.292, 0.24),
            description="Dentilled string course: a 90 mm dentil band between two fillets, 1 m run (terracotta / limestone).",
            features=["string_course"], budget=400)
def _sc_dentil():
    m = K.Mesh()
    m.box((-HALF, -0.045, 0.0), (HALF, P.WYTHE, 0.045), "terracotta")
    P.dentils(m, -HALF, HALF, 0.045, 0.150, -0.095, 0.095, "terracotta", pitch=0.10)
    m.box((-HALF, -0.095, 0.150), (HALF, P.WYTHE, 0.240), "terracotta")
    return m


@K.register("string_course_terracotta_band", "string_course", nominal_size=(1.0, 0.164, 0.36),
            description="Ornamented terracotta band course, 1 m run with a repeating rosette panel every 0.25 m.",
            features=["string_course"], budget=500)
def _sc_terracotta():
    m = K.Mesh()
    m.box((-HALF, -0.030, 0.0), (HALF, P.WYTHE, 0.360), "terracotta")
    for k in range(4):
        cx = -HALF + RUN * (k + 0.5) / 4
        m.box((cx - 0.085, -0.050, 0.055), (cx + 0.085, -0.030, 0.305), "terracotta")
        m.box((cx - 0.048, -0.062, 0.115), (cx + 0.048, -0.050, 0.245), "terracotta")
    m.box((-HALF, -0.048, 0.325), (HALF, P.WYTHE, 0.360), "terracotta")
    return m


# --------------------------------------------------------------------------- quoins
def _quoin(m: K.Mesh, mat: str, big: float, small: float, proj: float, courses: int, chamfer: bool) -> None:
    """Alternating long / short corner blocks stacked over ``courses`` (origin at the corner, block runs into +X)."""
    z = 0.0
    for i in range(courses):
        w = big if i % 2 == 0 else small
        h = 0.225 if not chamfer else 0.240
        m.box((0.0, -proj, z), (w, P.WYTHE, z + h), mat)
        if chamfer:
            m.box((0.0, -proj - 0.018, z + 0.022), (w - 0.022, -proj, z + h - 0.022), mat)   # rusticated face
        z += h


@K.register("quoin_limestone", "quoin", nominal_size=(0.6, 0.187, 1.35),
            description="Limestone quoin stack: six courses of alternating 0.60 / 0.40 m blocks, 225 mm high, projecting 85 mm "
                        "(Renaissance-revival apartment house corner).",
            features=["quoins"], budget=400)
def _quoin_lime():
    m = K.Mesh()
    _quoin(m, "limestone", 0.600, 0.400, 0.085, 6, False)
    return m


@K.register("quoin_brownstone", "quoin", nominal_size=(0.53, 0.187, 1.35),
            description="Brownstone quoin stack: six courses of alternating 0.53 / 0.36 m blocks with a tooled margin.",
            features=["quoins"], budget=400)
def _quoin_brown():
    m = K.Mesh()
    _quoin(m, "brownstone", 0.530, 0.360, 0.085, 6, False)
    return m


@K.register("quoin_brick_rusticated", "quoin", nominal_size=(0.575, 0.22, 1.44),
            description="Rusticated cast-stone quoin stack: six chamfered blocks, 240 mm courses, 0.10 m projection "
                        "(1920s apartment / bank corner).",
            features=["quoins", "rustication"], budget=500)
def _quoin_rust():
    m = K.Mesh()
    _quoin(m, "precast", 0.575, 0.385, 0.100, 6, True)
    return m


# --------------------------------------------------------------------------- pilasters
@K.register("pilaster_cast_iron", "pilaster", nominal_size=(0.36, 0.317, 3.9),
            description="Cast-iron storefront pilaster: fluted shaft with a moulded plinth, astragal and foliate capital, "
                        "3.90 m tall (SoHo / Tribeca cast-iron front).",
            features=["pilasters", "columns"], budget=900)
def _pil_iron():
    m = K.Mesh()
    h = 3.900
    m.box((-0.18, -0.20, 0.0), (0.18, P.WYTHE, 0.30), P.IRON)                                # plinth
    m.box((-0.155, -0.175, 0.30), (0.155, P.WYTHE, 0.38), P.IRON)                            # base torus
    for k in range(5):                                                                        # flutes
        cx = -0.11 + 0.055 * k
        m.box((cx - 0.018, -0.176, 0.40), (cx + 0.018, -0.150, h - 0.52), P.IRON)
    m.box((-0.140, -0.150, 0.38), (0.140, P.WYTHE, h - 0.52), P.IRON)                         # shaft
    m.box((-0.150, -0.165, h - 0.52), (0.150, P.WYTHE, h - 0.46), P.IRON)                     # astragal
    m.box((-0.175, -0.195, h - 0.46), (0.175, P.WYTHE, h - 0.12), P.IRON)                     # capital bell
    m.box((-0.180, -0.215, h - 0.12), (0.180, P.WYTHE, h), P.IRON)                            # abacus
    for s in (-1, 1):                                                                          # corner volutes
        m.box((s * 0.105, -0.215, h - 0.30), (s * 0.165, -0.150, h - 0.14), P.IRON)
    return m


@K.register("pilaster_brick", "pilaster", nominal_size=(0.49, 0.227, 3.05),
            description="Brick pilaster strip, one storey (3.05 m) tall, 0.44 m wide with a 0.10 m projection and a cast-stone cap.",
            features=["pilasters"], budget=400)
def _pil_brick():
    m = K.Mesh()
    m.box((-0.22, -0.100, 0.0), (0.22, P.WYTHE, 2.900), "red_brick")
    m.box((-0.245, -0.125, 2.900), (0.245, P.WYTHE, 3.050), "precast")
    return m


@K.register("pilaster_stone_fluted", "pilaster", nominal_size=(0.55, 0.272, 4.2),
            description="Fluted limestone pilaster, 4.20 m tall: moulded base, seven flutes and a simplified Ionic capital "
                        "(bank / institutional front).",
            features=["pilasters", "columns"], budget=900)
def _pil_stone():
    m = K.Mesh()
    h = 4.200
    m.box((-0.26, -0.135, 0.0), (0.26, P.WYTHE, 0.220), "limestone")
    m.box((-0.235, -0.115, 0.220), (0.235, P.WYTHE, 0.320), "limestone")
    m.box((-0.215, -0.100, 0.320), (0.215, P.WYTHE, h - 0.480), "limestone")
    for k in range(7):
        cx = -0.168 + 0.056 * k
        m.box((cx - 0.020, -0.104, 0.360), (cx + 0.020, -0.086, h - 0.520), "limestone")
    m.box((-0.235, -0.125, h - 0.480), (0.235, P.WYTHE, h - 0.380), "limestone")               # necking
    m.box((-0.260, -0.155, h - 0.380), (0.260, P.WYTHE, h - 0.120), "limestone")               # capital
    for s in (-1, 1):
        m.cylinder((s * 0.185, -0.155, h - 0.310), (s * 0.185, P.WYTHE, h - 0.310), 0.070, "limestone", segments=10)  # volute
    m.box((-0.275, -0.170, h - 0.120), (0.275, P.WYTHE, h), "limestone")                       # abacus
    return m


@K.register("pilaster_storefront_column", "pilaster", nominal_size=(0.24, 0.24, 4.2), anchor="ground_bottom_centre",
            description="Free-standing cast-iron storefront column, 0.20 m diameter and 4.20 m tall, with base, astragals and "
                        "capital (between storefront bays).",
            features=["columns"], budget=900)
def _pil_column():
    m = K.Mesh()
    h = 4.200
    m.lathe([(0.115, 0.0), (0.115, 0.10), (0.095, 0.16), (0.100, 0.22)], 12, P.IRON, caps=(True, False))
    m.cylinder((0.0, 0.0, 0.22), (0.0, 0.0, h - 0.34), 0.096, P.IRON, segments=12, caps=False)
    m.lathe([(0.096, h - 0.34), (0.118, h - 0.30), (0.100, h - 0.26), (0.120, h - 0.14), (0.118, h - 0.06)], 12, P.IRON)
    m.box((-0.120, -0.120, h - 0.06), (0.120, 0.120, h), P.IRON)
    return m


# --------------------------------------------------------------------------- misc trim
@K.register("trim_water_table", "trim", nominal_size=(1.0, 0.217, 0.42),
            description="Granite water table: the projecting base course between the sidewalk and the brick, 1 m run, "
                        "0.42 m high with a sloped wash.",
            features=[], budget=300)
def _water_table():
    m = K.Mesh()
    m.box((-HALF, -0.115, 0.0), (HALF, P.WYTHE, 0.360), "granite")
    m.face([(-HALF, -0.115, 0.360), (HALF, -0.115, 0.360), (HALF, P.WYTHE, 0.420), (-HALF, P.WYTHE, 0.420)], "granite")
    m.face([(-HALF, P.WYTHE, 0.360), (-HALF, P.WYTHE, 0.420), (HALF, P.WYTHE, 0.420), (HALF, P.WYTHE, 0.360)], "granite")
    m.face([(-HALF, -0.115, 0.360), (-HALF, P.WYTHE, 0.420), (-HALF, P.WYTHE, 0.360)], "granite")
    m.face([(HALF, P.WYTHE, 0.360), (HALF, P.WYTHE, 0.420), (HALF, -0.115, 0.360)], "granite")
    return m


@K.register("trim_lintel_stone", "trim", nominal_size=(1.18, 0.142, 0.15),
            description="Loose limestone lintel, 1.18 m long x 150 mm deep, 40 mm projection — drops over any 0.95 m opening.",
            features=["lintels"], budget=200)
def _lintel():
    m = K.Mesh()
    P.stone_lintel(m, -0.475, 0.475, 0.0, "limestone")
    return m


@K.register("trim_sill_cast_stone", "trim", nominal_size=(1.1, 0.167, 0.1),
            description="Loose cast-stone sill, 1.10 m long with a 20 mm wash and 65 mm projection — drops under any 0.95 m opening.",
            features=["sills"], budget=200)
def _sill():
    m = K.Mesh()
    P.stone_sill(m, -0.475, 0.475, 0.0, "precast")
    return m


@K.register("trim_keystone", "trim", nominal_size=(0.26, 0.192, 0.44),
            description="Limestone keystone, 0.23 m wide at the head and 0.44 m tall, projecting 90 mm — for arched and "
                        "flat-arched openings.",
            features=["lintels"], budget=200)
def _keystone():
    m = K.Mesh()
    top, bot = 0.130, 0.090
    zt, zb = 0.440, 0.0
    for (ya, yb) in ((-0.090, -0.060), (-0.060, P.WYTHE)):
        m.face([(-bot, ya, zb), (bot, ya, zb), (top, ya, zt), (-top, ya, zt)], "limestone", flip=(ya < -0.06))
    m.face([(-bot, -0.090, zb), (-top, -0.090, zt), (-top, P.WYTHE, zt), (-bot, P.WYTHE, zb)], "limestone")
    m.face([(bot, P.WYTHE, zb), (top, P.WYTHE, zt), (top, -0.090, zt), (bot, -0.090, zb)], "limestone")
    m.face([(-top, -0.090, zt), (top, -0.090, zt), (top, P.WYTHE, zt), (-top, P.WYTHE, zt)], "limestone")
    m.face([(-bot, P.WYTHE, zb), (bot, P.WYTHE, zb), (bot, -0.090, zb), (-bot, -0.090, zb)], "limestone")
    return m


@K.register("trim_datestone_plaque", "trim", nominal_size=(0.72, 0.162, 0.48),
            description="Carved limestone datestone / name plaque, 0.66 x 0.42 m with a moulded surround and a sunk field "
                        "(tenement builder's plaque).",
            features=[], budget=300)
def _datestone():
    m = K.Mesh()
    m.box((-0.330, -0.045, 0.0), (0.330, P.WYTHE, 0.420), "limestone")
    m.box((-0.360, -0.060, -0.030), (0.360, P.WYTHE, 0.030), "limestone")
    m.box((-0.360, -0.060, 0.390), (0.360, P.WYTHE, 0.450), "limestone")
    m.box((-0.270, -0.060, 0.060), (0.270, -0.045, 0.360), "limestone")
    return m


@K.register("trim_corner_bead_brick", "trim", nominal_size=(0.24, 0.24, 3.05),
            description="Brick outside-corner return, one storey tall: two 0.115 m wythes mitred at 90 deg, for wrapping the "
                        "kit round a building corner.",
            features=[], budget=200)
def _corner_bead():
    m = K.Mesh()
    m.box((-0.120, -0.120, 0.0), (0.120, 0.120, 3.050), "red_brick", faces="yxZ")
    return m
