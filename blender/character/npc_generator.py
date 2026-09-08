"""NYCSim pedestrian generator: the traffic lane's 12-dimensional variety vector, built into glTF NPCs.

Run headless::

    nice -n 10 python3 blender/character/npc_generator.py --count 24            # one glb per pedestrian
    nice -n 10 python3 blender/character/npc_generator.py --count 24 --no-glb   # catalogue only

Design
------
The pedestrian simulation owns the appearance contract (``docs/verification/traffic/REPORT.md`` §7) and this
module consumes it: twelve floats in ``[0, 1]`` - age band, stature, body mass, skin tone, hair style, hair
colour, top garment, top colour, bottom garment, bottom colour, footwear, accessory - decoded by
:mod:`variety` into MakeHuman macro targets, a wardrobe outfit, two garment tints, a hair colour and a gait.
Nothing else is invented: sex comes from the hairstyle table and the gait from the age band and body mass,
both documented in :mod:`variety`.

Every NPC shares **one skeleton** (the same 71-bone UE5 mannequin the player uses) and **the same animation
set**, so the runtime can instance thousands of pedestrians against a single animation blueprint.  The clips
are stored as per-bone ``matrix_basis`` maps, which are skeleton-proportion independent, so the same
rotations drive a 1.25 m child and a 1.95 m adult correctly.  The two NPC-only poses (``umbrella_hold`` and
``phone_walk``) are in that set.
"""
from __future__ import annotations

import argparse
import json
import logging
import math
import sys
import time
from dataclasses import dataclass, field, replace
from pathlib import Path

import chenv

chenv.setup_logging()

import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

import anim_lib  # noqa: E402
import anim_procedural  # noqa: E402
import build_character  # noqa: E402
import car_ref  # noqa: E402
import mh_build  # noqa: E402
import nycsim_bpy as nb  # noqa: E402
import pose_solver  # noqa: E402
import retarget  # noqa: E402
import rig_ue5  # noqa: E402
import variety  # noqa: E402
import wardrobe  # noqa: E402

log = logging.getLogger("nycsim.character.npc")

NPC_DIR = chenv.OUT_DIR / "npc"

@dataclass
class NpcBuild:
    """One generated pedestrian."""

    index: int
    vector: tuple[float, ...]
    appearance: variety.PedAppearance
    spec: mh_build.HumanSpec
    built: mh_build.BuiltHuman
    resolved: dict
    stature: dict = field(default_factory=dict)


def spec_from_appearance(appearance: variety.PedAppearance, name: str) -> mh_build.HumanSpec:
    """Turn one decoded contract vector into the MPFB macro targets and body-part choices."""
    macros = appearance.macros()
    hair = appearance.hair
    accessory = appearance.entry("accessory")
    extra_clothes = [accessory["ref"]] if accessory["kind"] == "mhclo" else []
    male = appearance.is_male
    # Brows and lashes are not contract dimensions; they follow the hair colour and the sex, which is what
    # they do on a real face, and are picked deterministically so a vector always rebuilds identically.
    brow_index = appearance.level("hair_colour") % len(mh_build.EYEBROW_ASSETS)
    lash_index = appearance.level("hair_style") % len(mh_build.EYELASH_ASSETS)
    return mh_build.HumanSpec(
        name=name,
        gender=macros["gender"], age=macros["age"], muscle=macros["muscle"], weight=macros["weight"],
        height=macros["height"], proportions=macros["proportions"],
        cupsize=macros["cupsize"], firmness=macros["firmness"],
        african=macros["african"], asian=macros["asian"], caucasian=macros["caucasian"],
        skin=appearance.skin_material(),
        eyes_material=("brown", "brown", "blue", "green", "grey")[appearance.level("skin_tone") % 5],
        hair=None if hair["procedural"] else hair["asset"],
        eyebrows=mh_build.EYEBROW_ASSETS[brow_index],
        eyelashes=None if male else mh_build.EYELASH_ASSETS[lash_index],
        clothes=tuple(extra_clothes),
    )


def solve_height_macro(appearance: variety.PedAppearance, spec: mh_build.HumanSpec, *,
                       tolerance: float = 0.008, max_iterations: int = 5) -> tuple[float, float, int]:
    """Find the MakeHuman `height` macro that delivers this appearance's stature. Returns (macro, m, iters).

    The contract specifies stature in metres (``variety.AGE_BANDS[...]["height_m"]``), and the macro that
    produces a given stature depends not only on the age band and sex but on the weight, muscle and ethnic
    macros - three more contract dimensions.  A fixed macro-to-metre table is therefore wrong by up to 13 cm,
    which is how a 1.44 m adult and a 2.05 m pedestrian got generated.  So the macro is *solved for*: a naked
    probe body (no clothes, no hair, no teeth, no eyes - about 1.5 s) is built, measured, and the macro
    corrected by the locally estimated slope until the measurement is within ``tolerance`` of the target.
    Two samples give a secant slope; before that the sweep's 1.05 m per unit of macro is used.

    The caller owns the scene: this resets it on every iteration and leaves the last probe in it, so the real
    build must reset again.
    """
    target = appearance.target_height_m
    probe = replace(spec, name=f"{spec.name}.probe", hair=None, eyebrows=None, eyelashes=None,
                    teeth=None, tongue=None, clothes=())
    macro = float(spec.height)
    slope = 1.05
    previous: tuple[float, float] | None = None
    measured = float("nan")
    for iteration in range(1, max_iterations + 1):
        nb.reset_scene()
        probe.height = min(max(macro, 0.0), 1.0)
        built = mh_build.build_human(probe, subdiv=0, load_clothes=False)
        measured = mh_build.measure(built)["height_m"]
        if abs(measured - target) <= tolerance:
            return probe.height, measured, iteration
        if previous is not None and abs(probe.height - previous[0]) > 1e-4:
            secant = (measured - previous[1]) / (probe.height - previous[0])
            if 0.3 < secant < 3.0:
                slope = secant
        previous = (probe.height, measured)
        macro = probe.height + (target - measured) / slope
    log.warning("%s: stature solve stopped at %.3f m against a target of %.3f m after %d builds",
                spec.name, measured, target, max_iterations)
    return probe.height, measured, max_iterations


def build_npc(appearance: variety.PedAppearance, vector: tuple[float, ...], index: int) -> NpcBuild:
    """Build one pedestrian in the current scene."""
    resolved = appearance.resolve()
    # A cold body is named for the garment you actually see.  Naming it for the base layer would
    # give two bodies the same name -- npc_31_m_older_tee is a tee in one cast and a puffer over a
    # tee in the other -- and the name is the asset id the engine loads.
    worn = resolved["top_garment"]
    if appearance.season == "cold":
        worn = variety.COLD_OUTER_BY_TOP[resolved["top_garment"]]
    name = f"npc_{index:02d}_{resolved['sex'][0]}_{resolved['age_band']}_{worn}"
    spec = spec_from_appearance(appearance, name)
    macro, probe_height, iterations = solve_height_macro(appearance, spec)
    log.info("%s: stature %.3f m (target %.3f m) at height macro %.4f after %d probe builds", name,
             probe_height, appearance.target_height_m, macro, iterations)
    spec.height = macro
    outfit = appearance.outfit()
    colours = appearance.colours()
    prefix = f"{name}."
    spec.clothes = tuple(spec.clothes) + wardrobe.makehuman_assets(outfit)
    nb.reset_scene()
    built = mh_build.build_human(spec, subdiv=0, load_clothes=bool(spec.clothes))
    wardrobe.finish_makehuman(built, outfit, name_prefix=prefix, colours=colours)
    mh_build.bake_and_load_face_units(built)
    mh_build.transfer_tongue_morph(built)
    mh_build.strip_helper_geometry(built)
    mh_build.split_eyes(built)
    # UE5 rig first: everything below inherits the body's (already normalised) weights.
    rig_ue5.convert_to_ue5(built.armature, built.meshes())
    wardrobe.reweight_from_body(built, outfit, name_prefix=prefix)
    wardrobe.dress(built, outfit, name_prefix=prefix, colours=colours)
    wardrobe.cut_bottoms_at_shoe_collar(built, outfit, name_prefix=prefix)
    hidden = wardrobe.hide_covered_garments(built, outfit, name_prefix=prefix)
    wardrobe.resolve_layers(built, outfit, name_prefix=prefix)
    bad = wardrobe.verify_outfit(built, outfit, name_prefix=prefix, dropped=tuple(hidden))
    if bad:
        raise RuntimeError(f"{name}: garment verification failed: {bad}")

    hair = appearance.hair
    if hair["procedural"]:
        wardrobe.build_procedural_hair(built, hair["asset"], name_prefix=prefix)
    accessory = appearance.entry("accessory")
    if accessory["kind"] == "hat":
        wardrobe.build_hat(built, accessory["ref"], name_prefix=prefix)
    elif accessory["kind"] == "bag":
        wardrobe.build_bag(built, accessory["ref"], name_prefix=prefix)
    mh_build.hide_body_under_clothes(built)
    mh_build.setup_skin(built)
    mh_build.setup_eye_materials(built)
    mh_build.setup_alpha_materials(built)
    mh_build.set_hair_colour(built, appearance.hair_colour_rgb())
    problems = rig_ue5.verify_skeleton(built.armature)
    if problems:
        raise RuntimeError(f"{name}: UE5 skeleton verification failed: {problems}")
    build = NpcBuild(index=index, vector=vector, appearance=appearance, spec=spec, built=built,
                     resolved=resolved)
    build.stature = {"target_m": round(appearance.target_height_m, 4),
                     "probe_m": round(probe_height, 4), "height_macro": round(macro, 5),
                     "probe_builds": iterations}
    return build


def apply_gait(clips: list[anim_lib.Clip], appearance: variety.PedAppearance) -> list[anim_lib.Clip]:
    """Stamp the pedestrian's gait onto the clip set: playback rate and a spinal lean.

    Both come from :func:`variety.gait_for`, i.e. from the age band and the body mass, which are contract
    dimensions.  Nothing here is random.
    """
    from mathutils import Matrix  # noqa: PLC0415

    gait = appearance.gait()
    rate = float(gait["rate"])
    lean = float(gait["stoop_deg"])
    out: list[anim_lib.Clip] = []
    for clip in clips:
        frames = []
        for frame in clip.frames:
            new = {k: v.copy() for k, v in frame.items()}
            for bone, share in (("spine_02", 0.35), ("spine_04", 0.4), ("neck_01", -0.5)):
                base = new.get(bone, Matrix.Identity(4))
                new[bone] = base @ Matrix.Rotation(math.radians(lean * share), 4, "X")
            frames.append(new)
        speed = clip.speed_mps
        out.append(anim_lib.Clip(name=clip.name, frames=frames, fps=clip.fps * rate,
                                 method=clip.method, loop=clip.loop, additive=clip.additive,
                                 notes=clip.notes, source=clip.source,
                                 speed_mps=None if speed is None else speed * rate,
                                 extra={**clip.extra, "gait": gait["id"], "gait_rate": rate}))
    return out


def author_clip_set(built: mh_build.BuiltHuman) -> tuple[list[anim_lib.Clip], dict]:
    """The shared animation set, authored once against a given body."""
    return build_character.build_clips(built)


def generate(count: int, *, seed_base: int = 0x4E5943, export_glb: bool = True,
             season: str = "mild", first_index: int = 0, keep_existing: bool = False) -> dict:
    """Generate ``count`` pedestrians from spread contract vectors, one scene at a time.

    ``first_index`` and ``keep_existing`` are what let a second cast be added without disturbing the
    first.  :func:`variety.spread_vectors` gives index *i* the same vector whatever ``count`` is --
    the strides and offsets come from the seed alone -- so bodies 0..23 are byte-identical whether
    24 or 36 are asked for, every archetype index keeps its meaning, and no comparison sheet already
    rendered against them goes stale.  ``keep_existing`` merges the entries already in
    ``npc_variety.json`` whose index falls outside the range being built.
    """
    chenv.ensure_dirs()
    NPC_DIR.mkdir(parents=True, exist_ok=True)
    catalog: list[dict] = []
    clip_report: dict = {}
    vectors = variety.spread_vectors(first_index + count, seed=seed_base)[first_index:]
    t0 = time.time()
    for offset, vector in enumerate(vectors):
        index = first_index + offset
        nb.reset_scene()
        appearance = variety.decode(vector, season)
        npc = build_npc(appearance, vector, index)
        clips, report = author_clip_set(npc.built)
        if not clip_report:
            clip_report = report
        clips = apply_gait(clips, appearance)
        for clip in clips:
            anim_lib.push_clip(npc.built.armature, clip)
        anim_lib.set_active_clip(npc.built.armature, bpy.data.actions.get("idle"))

        measurements = mh_build.measure(npc.built)
        entry = {
            "id": npc.spec.name,
            "index": index,
            "variety_vector": [round(v, 6) for v in vector],
            "variety_levels": list(appearance.levels),
            "resolved": npc.resolved,
            "measurements_m": {k: round(v, 4) for k, v in measurements.items()},
            "stature": npc.stature,
            "meshes": {o.name: len(o.data.vertices) for o in npc.built.meshes()},
            "bone_count": len(npc.built.armature.data.bones),
            "blendshapes": len(npc.built.face_units),
            "animations": [c.name for c in clips],
        }
        if export_glb:
            extras = {"asset_id": npc.spec.name, "skeleton": "UE5_Mannequin",
                      "variety_vector": [round(v, 6) for v in vector],
                      "variety_levels": list(appearance.levels),
                      "variety_dimensions": list(variety.DIMENSION_NAMES),
                      "resolved": npc.resolved, "fps": anim_lib.FPS,
                      "animations": [c.metadata() for c in clips],
                      "blendshapes": npc.built.face_units,
                      "blendshape_standard": "ARKit-52", "max_bone_influences": 4}
            path = anim_lib.export_character(NPC_DIR / f"{npc.spec.name}.glb",
                                             [npc.built.armature, *npc.built.meshes()], extras)
            summary = anim_lib.glb_summary(path)
            entry["glb"] = str(path.relative_to(chenv.REPO_ROOT))
            entry["glb_summary"] = summary
        catalog.append(entry)
        entry["season"] = appearance.season
        log.info("npc %d/%d %s: %.2f m, %d meshes (%.0f s elapsed)", offset + 1, count, npc.spec.name,
                 measurements["height_m"], len(npc.built.meshes()), time.time() - t0)

    out = chenv.OUT_DIR / "npc_variety.json"
    if keep_existing and out.is_file():
        built = {int(e["index"]) for e in catalog}
        previous = json.loads(out.read_text()).get("npcs", [])
        catalog = sorted([e for e in previous if int(e["index"]) not in built] + catalog,
                         key=lambda e: int(e["index"]))
        if not clip_report:
            clip_report = json.loads(out.read_text()).get("clip_report", {})

    manifest = {
        "schema_version": variety.CONTRACT_VERSION,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "count": len(catalog),
        "shared_skeleton": "UE5_Mannequin",
        "variety_contract": variety.contract(),
        "wardrobe": [{"id": g.item_id, "label": g.label, "slot": g.slot, "layer": g.layer,
                      "source": g.source, "mhclo": g.mhclo, "tags": list(g.tags), "notes": g.notes}
                     for g in wardrobe.WARDROBE],
        "hairstyles": [{"id": h[0], "source": h[1], "label": h[2]} for h in wardrobe.HAIRSTYLES],
        "clip_report": clip_report,
        "cold_outer_by_top": dict(variety.COLD_OUTER_BY_TOP),
        "npcs": catalog,
    }
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=1, sort_keys=False)
    log.info("wrote %s (%d NPCs, %.0f s)", out, len(catalog), time.time() - t0)
    return manifest


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Generate NYCSim pedestrians from the variety contract")
    parser.add_argument("--count", type=int, default=24,
                        help="how many NPCs; 12 or more exercises every level of every dimension")
    parser.add_argument("--seed", type=lambda s: int(s, 0), default=0x4E5943)
    parser.add_argument("--no-glb", action="store_true", help="build and catalogue but do not export")
    parser.add_argument("--season", choices=("mild", "cold"), default="mild",
                        help="'cold' puts variety.COLD_OUTER_BY_TOP over the same base layer (J53)")
    parser.add_argument("--first-index", type=int, default=0,
                        help="archetype index of the first body; the vector for an index does not "
                             "depend on how many are asked for, so a second cast can be appended "
                             "without disturbing the first")
    parser.add_argument("--keep-existing", action="store_true",
                        help="merge with the bodies already in npc_variety.json instead of "
                             "replacing them")
    args = parser.parse_args(argv)
    manifest = generate(args.count, seed_base=args.seed, export_glb=not args.no_glb,
                        season=args.season, first_index=args.first_index,
                        keep_existing=args.keep_existing)
    heights = sorted(n["measurements_m"]["height_m"] for n in manifest["npcs"])
    print(json.dumps({"count": manifest["count"],
                      "contract_dimensions": [d["name"] for d in
                                              manifest["variety_contract"]["dimensions"]],
                      "distinguishable_appearances":
                          manifest["variety_contract"]["distinguishable_appearances"],
                      "wardrobe_items": len(manifest["wardrobe"]),
                      "height_range_m": [heights[0], heights[-1]]}, indent=1))
    return 0


if __name__ == "__main__":
    code = 1
    try:
        code = main(sys.argv[1:])
    except Exception:
        logging.exception("npc generation failed")
    chenv.hard_exit(code)
