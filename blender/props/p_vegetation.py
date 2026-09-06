"""Street trees: the ten commonest species of the 2015 Street Tree Census, three census DBH classes each,
in leaf and bare.

Species and sizes are **data, not invention**: ``blender/props/dbh_classes.json`` is produced by
``blender/props/census_dbh.py`` from ``data/raw/nyc_opendata/street_trees_2015.csv`` — the ten commonest
identified species among living trees, and for each the 25th / 50th / 90th percentile of measured trunk
diameter. Height and crown spread come from ``pipeline/nycsim_pipeline/furniture/allometry.py``, the same
saturating curve the props table uses (``height_source = 1``).

Each tree is a procedural branch skeleton (recursive tapered tubes with species-specific crown habit) carrying
alpha leaf cards from the atlases in ``_leaves``. The skeleton's centrelines are scaled — radii untouched — so
the finished mesh matches the allometric height and crown spread exactly. LOD1 is three crossed billboards
textured with an impostor drawn from that same skeleton.
"""
from __future__ import annotations

import json
import math
import random
from dataclasses import dataclass, field
from pathlib import Path

import _core as C
import _leaves as LF
import _palette as P

DBH_CLASSES = Path(__file__).resolve().parent / "dbh_classes.json"
MAX_LOD0_TRIS = 12000


@dataclass
class Habit:
    """Crown habit of one species (the shape a mature open-grown street tree of it takes)."""
    key: str
    bark: str                 # friendly texture name in _textures_fallback.PROPS_TEXTURE_NAMES
    bark_tint: str
    clear_frac: float         # clear trunk height / total height (street trees are limbed up)
    scaffolds: int            # primary branches leaving the trunk
    angle1: float             # divergence of the primaries from vertical (deg)
    angle_n: float            # divergence of higher-order branches (deg)
    len_ratio: float          # child length / parent length
    up_bias: float            # 0 spreading, 1 strongly upright
    droop: float              # downward curvature of the lower branches (pin oak, linden)
    crown_note: str
    bark_uv_m: float = 0.55


HABITS: dict[str, Habit] = {
    "planetree": Habit("planetree", "bark_planetree", "#C6BEAC", 0.34, 4, 44.0, 40.0, 0.72, 0.28, 0.06,
                       "wide spreading crown on heavy limbs; mottled exfoliating bark"),
    "honeylocust": Habit("honeylocust", "bark_honeylocust", "#9C8468", 0.38, 4, 40.0, 42.0, 0.70, 0.42, 0.05,
                         "open, airy, vase-to-spreading crown that casts light shade"),
    "callery_pear": Habit("callery_pear", "bark_callery_pear", "#7E6E5E", 0.26, 6, 26.0, 24.0, 0.72, 0.78, 0.0,
                          "tight upswept oval — the narrow habit that makes it a sidewalk staple"),
    "pin_oak": Habit("pin_oak", "bark_pin_oak", "#8C8378", 0.24, 6, 52.0, 34.0, 0.70, 0.46, 0.34,
                     "pyramidal with a strong central leader; lower branches droop, upper ascend"),
    "norway_maple": Habit("norway_maple", "bark_norway_maple", "#7C6E60", 0.32, 5, 42.0, 38.0, 0.71, 0.40, 0.04,
                          "dense rounded crown casting heavy shade"),
    "littleleaf_linden": Habit("littleleaf_linden", "bark_linden", "#8A8074", 0.28, 6, 40.0, 32.0, 0.71, 0.58, 0.14,
                               "dense pyramidal-oval crown, branches to low on the trunk"),
    "ginkgo": Habit("ginkgo", "bark_ginkgo", "#A09380", 0.34, 4, 38.0, 30.0, 0.70, 0.62, 0.0,
                    "irregular, upright and open when young, broadening with age"),
    "zelkova": Habit("zelkova", "bark_zelkova", "#B4AC9C", 0.36, 4, 30.0, 40.0, 0.74, 0.55, 0.0,
                     "classic vase — upright limbs fanning into a broad flat-topped crown"),
    "sophora": Habit("sophora", "bark_sophora", "#8E7D66", 0.34, 4, 46.0, 40.0, 0.71, 0.34, 0.10,
                     "broad rounded open crown on spreading limbs"),
    "red_maple": Habit("red_maple", "bark_red_maple", "#8E8C88", 0.30, 5, 40.0, 34.0, 0.71, 0.52, 0.06,
                       "oval to rounded, ascending branches"),
}

# census latin name -> our species key (the ten species census_dbh.py resolves)
LATIN_TO_KEY = {
    "Platanus x acerifolia": "planetree",
    "Gleditsia triacanthos var. inermis": "honeylocust",
    "Pyrus calleryana": "callery_pear",
    "Quercus palustris": "pin_oak",
    "Acer platanoides": "norway_maple",
    "Tilia cordata": "littleleaf_linden",
    "Ginkgo biloba": "ginkgo",
    "Zelkova serrata": "zelkova",
    "Styphnolobium japonicum": "sophora",
    "Acer rubrum": "red_maple",
}
CLASS_ORDER = ("small", "medium", "large")
# Total leaf cards per tree, distributed over the tips the skeleton actually produced. Budgeting the total
# (rather than a fixed count per tip) keeps a 6-scaffold species like pin oak inside the 12k triangle ceiling
# while still filling a 14 m crown.
CARD_BUDGET = {"small": 520, "medium": 820, "large": 1120}
MAX_ORDER = {"small": 4, "medium": 4, "large": 5}


@dataclass
class Skeleton:
    branches: list[tuple[list[list[float]], list[float], int]] = field(default_factory=list)
    leaves: list[tuple[list[float], float]] = field(default_factory=list)
    tips: list[list[list[float]]] = field(default_factory=list)


def _grow(sk: Skeleton, rng: random.Random, habit: Habit, start, direction, length: float, radius: float,
          order: int, max_order: int) -> None:
    """Recursively add one branch and its children. ``direction`` is a unit Vector."""
    n_pts = 5 if order <= 1 else (4 if order == 2 else 3)
    pts, radii = [list(start)], [radius]
    pos = C.Vector(start)
    d = C.Vector(direction).normalized()
    for i in range(1, n_pts):
        step = length / (n_pts - 1)
        # habit: gentle upward (or, low in the crown, downward) curvature plus a little wander
        up = C.Vector((0.0, 0.0, 1.0))
        bias = habit.up_bias * 0.22 - (habit.droop * 0.30 if order <= 2 else 0.0)
        d = (d + up * bias + C.Vector((rng.gauss(0, 0.09), rng.gauss(0, 0.09), rng.gauss(0, 0.05)))).normalized()
        pos = pos + d * step
        pts.append([pos.x, pos.y, pos.z])
        radii.append(radius * (1.0 - 0.55 * i / (n_pts - 1)))
    sk.branches.append((pts, radii, order))
    if order >= max_order or radius < 0.006:
        sk.tips.append(pts)
        return
    n_children = 3 if order <= 2 else 2
    tip = C.Vector(pts[-1])
    ref = C.Vector((1.0, 0.0, 0.0)) if abs(d.z) > 0.9 else C.Vector((0.0, 0.0, 1.0))
    side = d.cross(ref).normalized()
    side2 = d.cross(side).normalized()
    ang = math.radians(habit.angle_n if order else habit.angle1)
    for c in range(n_children):
        az = C.TAU * ((c + rng.uniform(-0.12, 0.12)) / n_children) + order * 2.399963
        a = ang * rng.uniform(0.78, 1.22)
        nd = (d * math.cos(a) + (side * math.cos(az) + side2 * math.sin(az)) * math.sin(a)).normalized()
        # a sub-branch part way along the parent keeps the crown from being hollow
        base = tip if c == 0 else C.Vector([pts[-2][j] * 0.5 + pts[-1][j] * 0.5 for j in range(3)])
        _grow(sk, rng, habit, base, nd, length * habit.len_ratio * rng.uniform(0.85, 1.12),
              radius * rng.uniform(0.56, 0.70), order + 1, max_order)


def build_skeleton(species: str, height: float, dbh_cm: float, crown_m: float, size_class: str, seed: int,
                   bare: bool = False) -> Skeleton:
    """Trunk + recursive crown, then scale the centrelines (not the radii) to the allometric height and spread."""
    habit = HABITS[species]
    rng = random.Random(seed)
    sk = Skeleton()
    r_trunk = max(0.025, dbh_cm / 200.0)
    clear = max(2.2, height * habit.clear_frac)
    trunk_pts, trunk_r = [], []
    n = 6
    for i in range(n):
        t = i / (n - 1)
        trunk_pts.append([rng.gauss(0, 0.012) * t * t * clear, rng.gauss(0, 0.012) * t * t * clear, t * clear])
        trunk_r.append(r_trunk * (1.30 if i == 0 else 1.0) * (1.0 - 0.28 * t))
    sk.branches.append((trunk_pts, trunk_r, 0))
    card = max(0.40, min(1.70, crown_m * 0.140))
    top = C.Vector(trunk_pts[-1])
    ang = math.radians(habit.angle1)
    for c in range(habit.scaffolds):
        az = C.TAU * (c + rng.uniform(-0.15, 0.15)) / habit.scaffolds
        a = ang * rng.uniform(0.8, 1.2)
        nd = C.Vector((math.sin(a) * math.cos(az), math.sin(a) * math.sin(az), math.cos(a)))
        base = C.Vector((top.x, top.y, top.z - clear * rng.uniform(0.0, 0.16)))
        _grow(sk, rng, habit, base, nd, (height - clear) * 0.52 * rng.uniform(0.9, 1.1),
              r_trunk * 0.62 * rng.uniform(0.85, 1.05), 1, MAX_ORDER[size_class])
    per_tip = max(2, min(12, round(CARD_BUDGET[size_class] / max(1, len(sk.tips)))))
    for pts in sk.tips:
        for k in range(per_tip):
            t = 0.30 + 0.70 * (k + 0.5) / per_tip
            i = min(len(pts) - 2, int(t * (len(pts) - 1)))
            f = t * (len(pts) - 1) - i
            q = [pts[i][j] * (1 - f) + pts[i + 1][j] * f for j in range(3)]
            jitter = card * 0.30
            sk.leaves.append(([q[0] + rng.gauss(0, jitter), q[1] + rng.gauss(0, jitter), q[2] + rng.gauss(0, jitter * 0.7)],
                              card * rng.uniform(0.80, 1.28)))
    # scale centrelines so the finished tree has exactly the allometric height and crown spread
    # A leafed tree's crown spread is its foliage envelope; a bare winter tree's is its branch envelope, so the
    # measurement the scaling is fitted to changes with the state (and both end up at the allometric spread).
    env = [p for b, _, _ in sk.branches for p in b] + ([] if bare else [p for p, _ in sk.leaves])
    xs = [p[0] for p in env]
    ys = [p[1] for p in env]
    zs = [p[2] for p in env]
    # A procedural crown is never symmetric, so each horizontal axis is brought to the allometric spread
    # independently; the trunk radii are untouched, so DBH stays exactly the census value.
    z_max = max(zs)
    margin = 0.0 if bare else card
    wx = (max(xs) - min(xs)) + margin
    wy = (max(ys) - min(ys)) + margin
    sx = crown_m / wx if wx > 1e-6 else 1.0
    sy = crown_m / wy if wy > 1e-6 else 1.0
    sz = height / (z_max + margin * 0.5) if z_max > 1e-6 else 1.0
    cx, cy = (max(xs) + min(xs)) / 2.0, (max(ys) + min(ys)) / 2.0
    for pts, _, _ in sk.branches:
        for p in pts:
            lean = p[2] / z_max                      # keep the trunk foot on the origin, shift only the crown
            p[0] = (p[0] - cx * lean) * sx
            p[1] = (p[1] - cy * lean) * sy
            p[2] = p[2] * sz
    for p, _ in sk.leaves:
        p[0] = (p[0] - cx) * sx
        p[1] = (p[1] - cy) * sy
        p[2] = p[2] * sz
    return sk


def _wood_object(sk: Skeleton, bark, name: str):
    bm, uv = C._new_bm()
    for pts, radii, order in sk.branches:
        segs = 10 if order == 0 else (8 if order == 1 else (6 if order == 2 else (5 if order == 3 else 4)))
        C.tube_into_bm(bm, uv, pts, radii, segs, 0, uv_tile_m=0.55, cap_start=(order == 0), cap_end=False)
    C.bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return C.bm_object(name, bm, [bark], smooth=True)


def _leaf_object(sk: Skeleton, mat, name: str, rng: random.Random):
    bm, uv = C._new_bm()
    for idx, (p, size) in enumerate(sk.leaves):
        u0, v0, u1, v1 = LF.leaf_card_uv(idx)
        n = C.Vector((rng.gauss(0, 1), rng.gauss(0, 1), rng.gauss(0, 0.55)))
        if n.length < 1e-4:
            n = C.Vector((1.0, 0.0, 0.3))
        n.normalize()
        ref = C.Vector((0.0, 0.0, 1.0)) if abs(n.z) < 0.92 else C.Vector((1.0, 0.0, 0.0))
        a = n.cross(ref).normalized() * (size / 2.0)
        b = n.cross(a).normalized() * (size / 2.0)
        o = C.Vector(p)
        vs = [bm.verts.new(o - a - b), bm.verts.new(o + a - b), bm.verts.new(o + a + b), bm.verts.new(o - a + b)]
        f = bm.faces.new(vs)
        f.smooth = True
        for loop, t in zip(f.loops, ((u0, v0), (u1, v0), (u1, v1), (u0, v1))):
            loop[uv].uv = t
    bm.normal_update()
    ob = C.bm_object(name, bm, [mat])
    return ob


def _billboards(name: str, image, height: float, half_width: float, mat_name: str):
    """LOD1: three crossed vertical quads carrying the impostor, sharing one alpha-clipped material."""
    mat = C.mat_image(mat_name, image, alpha_clip=True, roughness=0.8, backface=True)
    mat.use_backface_culling = False
    bm, uv = C._new_bm()
    for k in range(3):
        a = math.pi * k / 3.0
        dx, dy = math.cos(a) * half_width, math.sin(a) * half_width
        vs = [bm.verts.new((-dx, -dy, 0.0)), bm.verts.new((dx, dy, 0.0)),
              bm.verts.new((dx, dy, height)), bm.verts.new((-dx, -dy, height))]
        f = bm.faces.new(vs)
        for loop, t in zip(f.loops, ((0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0))):
            loop[uv].uv = t
    bm.normal_update()
    return C.bm_object(name, bm, [mat])


def load_classes() -> dict:
    if not DBH_CLASSES.exists():
        raise FileNotFoundError(f"{DBH_CLASSES} missing — run: python3 blender/props/census_dbh.py")
    return json.loads(DBH_CLASSES.read_text())


def _tree_builder(species: str, latin: str, common: str, cls: dict, size_class: str, bare: bool, seed: int):
    habit = HABITS[species]

    def build() -> C.Built:
        height, dbh, crown = cls["height_m"], cls["dbh_cm"], cls["crown_m"]
        sk = build_skeleton(species, height, dbh, crown, size_class, seed, bare=bare)
        bark = C.mat_textured(f"bark_{species}", habit.bark, habit.bark_uv_m, tint=habit.bark_tint,
                              roughness=0.85, resolution=C.BARK_TEX_RES, max_px=C.BARK_TEX_PX, normal_strength=1.2)
        wood = _wood_object(sk, bark, f"{species}_wood")
        parts = [wood]
        if not bare:
            leaf_mat = C.mat_image(f"LEAF_{species}", LF.leaf_atlas(species), alpha_clip=True, roughness=0.78, backface=True)
            leaf_mat.use_backface_culling = False
            parts.append(_leaf_object(sk, leaf_mat, f"{species}_leaves", random.Random(seed ^ 0x5EED)))
        C.settle_to_ground(parts)
        segs = []
        for pts, radii, _ in sk.branches:
            for i in range(len(pts) - 1):
                segs.append(((pts[i][0], pts[i][2]), (pts[i + 1][0], pts[i + 1][2]), radii[i]))
        leaf_pts = [(p[0], p[2], s) for p, s in sk.leaves]
        half = crown / 2.0
        img = LF.impostor(f"{species}_{size_class}{'_bare' if bare else ''}", segs, leaf_pts, height, half, species, bare)
        lod1 = _billboards(f"{species}_billboard", img, height, half,
                           f"IMPOSTOR_{species}_{size_class}{'_bare' if bare else ''}")
        return C.Built(lod0=parts, lod1=[lod1], lod1_kind="crossed_billboards",
                       extra={"species_latin": latin, "species_common": common, "size_class": size_class,
                              "dbh_cm": dbh, "height_m": height, "crown_m": crown, "bare_winter": bare,
                              "census_source": "street_trees_2015 (25th/50th/90th percentile DBH of living trees)",
                              "height_source": "allometry (height_source=1)",
                              "crown_habit": habit.crown_note,
                              "key_dims_m": {"height": height, "crown_spread": crown, "dbh_cm": dbh,
                                             "trunk_radius": round(dbh / 200.0, 4)},
                              "leaf_cards": 0 if bare else len(sk.leaves), "branches": len(sk.branches)})

    return build


def specs() -> list:
    doc = load_classes()
    out = []
    ids_by_species: dict[str, list[str]] = {}
    entries = []
    for sp in doc["species"]:
        key = LATIN_TO_KEY.get(sp["latin"])
        if key is None:
            raise KeyError(f"census species {sp['latin']!r} has no crown habit in HABITS")
        for cls in sp["classes"]:
            for bare in (False, True):
                pid = f"tree_{key}_{cls['class']}" + ("_bare" if bare else "")
                ids_by_species.setdefault(key, []).append(pid)
                entries.append((pid, key, sp, cls, bare))
    for pid, key, sp, cls, bare in entries:
        habit = HABITS[key]
        seed = abs(hash((key, cls["class"], bare))) % (2 ** 31)
        note = (f"{sp['common'].title()} ({sp['latin']}), {cls['class']} census class: DBH {cls['dbh_cm']} cm is the "
                f"{'25th' if cls['class'] == 'small' else ('50th' if cls['class'] == 'medium' else '90th')} percentile "
                f"of the {sp['census_count']:,} living trees of this species in the 2015 Street Tree Census; height "
                f"{cls['height_m']} m and crown {cls['crown_m']} m from nycsim_pipeline.furniture.allometry. "
                f"Habit: {habit.crown_note}." + (" Bare winter state (no leaf cards)." if bare else ""))
        out.append(C.PropSpec(
            pid, "vegetation", "tree", _tree_builder(key, sp["latin"], sp["common"], cls, cls["class"], bare, seed),
            (cls["crown_m"], cls["crown_m"], cls["height_m"]), note,
            variants=[i for i in ids_by_species[key] if i != pid],
            tags=[f"species:{key}", f"class:{cls['class']}", "winter" if bare else "summer"],
            tolerance=0.18, lod1_ratio=0.05))
    return out
