"""NYCSim pedestrian generator: 24 base bodies x the 12-dimensional variety vector.

Run headless::

    nice -n 10 python3 blender/character/npc_generator.py --count 24            # one glb per base body
    nice -n 10 python3 blender/character/npc_generator.py --lineup 12 --out ...  # a line-up scene

Design
------
Every NPC shares **one skeleton** (the same 71-bone UE5 mannequin the player uses) and **the same animation
set**, so the runtime can instance thousands of pedestrians against a single animation blueprint.  What
varies is the 12 bytes of :mod:`variety`:

* ``body_preset`` picks one of :data:`variety.BODY_PRESETS` - 24 MakeHuman macro-target combinations spread
  over gender, age, muscle, weight, height, proportions and the three ethnic axes;
* ``skin_tone`` picks one of the 18 CC0 MakeHuman skin materials;
* ``hair`` picks one of 12 styles (10 MakeHuman card-hair meshes plus two procedural ones);
* ``top``/``bottom``/``shoes``/``outerwear``/``hat``/``bag``/``glasses`` pick from the 40-item NYC wardrobe;
* ``height_scale`` scales the finished character by 0.90-1.10;
* ``walk_style`` selects the locomotion clip and its playback rate.

The animation set is built once, on the first body, and re-baked onto each subsequent body: the clips are
stored as per-bone ``matrix_basis`` maps, which are skeleton-proportion independent, so the same rotations
drive a 1.52 m child and a 1.93 m adult correctly.  The two NPC-only poses (``umbrella_hold`` and
``phone_walk``) are in that set.
"""
from __future__ import annotations

import argparse
import json
import logging
import math
import sys
import time
from dataclasses import dataclass
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

#: MakeHuman clothes assets used for the wardrobe slots that are meshes rather than tailored garments.
MH_CLOTHES = {
    "fedora01": "fedora01",
    "kwnet_at_optical_glasses": "kwnet_at_optical_glasses",
    "spamrakuen_tbm_glasses_frames_01": "spamrakuen_tbm_glasses_frames_01",
    "toigo_round_glasses_leopard": "toigo_round_glasses_leopard",
    "ews_3d_glasses": "ews_3d_glasses",
}


@dataclass
class NpcBuild:
    """One generated pedestrian."""

    index: int
    vector: variety.VarietyVector
    spec: mh_build.HumanSpec
    built: mh_build.BuiltHuman
    resolved: dict


def spec_from_vector(vector: variety.VarietyVector, name: str) -> mh_build.HumanSpec:
    """Turn 12 bytes into the MPFB macro targets and body-part choices."""
    preset = variety.BODY_PRESETS[vector.body_preset % len(variety.BODY_PRESETS)]
    resolved = vector.resolve()
    hair = resolved["hair"]
    if hair in ("buzzcut", "topknot"):
        hair_asset = "bob01" if hair == "topknot" else None
    else:
        hair_asset = hair
    female = preset["gender"] < 0.5
    accessories: list[str] = []
    if resolved["glasses"]:
        accessories.append(resolved["glasses"])
    if resolved["hat"] == "fedora01":
        accessories.append("fedora01")
    return mh_build.HumanSpec(
        name=name,
        gender=preset["gender"], age=preset["age"], muscle=preset["muscle"], weight=preset["weight"],
        height=preset["height"], proportions=preset["proportions"],
        cupsize=0.5 if female else 0.0, firmness=0.5,
        african=preset["african"], asian=preset["asian"], caucasian=preset["caucasian"],
        skin=resolved["skin_tone"],
        eyes_material=("brown", "blue", "green", "grey")[vector.skin_tone % 4],
        hair=hair_asset,
        eyebrows=mh_build.EYEBROW_ASSETS[vector.body_preset % len(mh_build.EYEBROW_ASSETS)],
        eyelashes=mh_build.EYELASH_ASSETS[vector.skin_tone % len(mh_build.EYELASH_ASSETS)],
        clothes=tuple(accessories),
    )


def outfit_from_vector(vector: variety.VarietyVector) -> tuple[str, ...]:
    resolved = vector.resolve()
    items = [resolved["top"], resolved["bottom"], resolved["shoes"]]
    if resolved["outerwear"]:
        items.append(resolved["outerwear"])
    if resolved["hat"] == "hijab_navy":
        items.append("hijab_navy")
    return tuple(items)


def build_npc(vector: variety.VarietyVector, index: int) -> NpcBuild:
    """Build one pedestrian in the current scene."""
    resolved = vector.resolve()
    name = f"npc_{index:02d}_{resolved['body_preset']}"
    spec = spec_from_vector(vector, name)
    outfit = outfit_from_vector(vector)
    spec.clothes = tuple(spec.clothes) + wardrobe.makehuman_assets(outfit)
    built = mh_build.build_human(spec, subdiv=0, load_clothes=bool(spec.clothes))
    wardrobe.finish_makehuman(built, outfit, name_prefix=f"{name}.")
    mh_build.bake_and_load_face_units(built)
    mh_build.strip_helper_geometry(built)
    mh_build.split_eyes(built)
    # UE5 rig first: everything below inherits the body's (already normalised) weights.
    rig_ue5.convert_to_ue5(built.armature, built.meshes())
    wardrobe.reweight_from_body(built, outfit, name_prefix=f"{name}.")

    wardrobe.dress(built, outfit, name_prefix=f"{name}.")
    if resolved["hair"] in ("buzzcut", "topknot"):
        wardrobe.build_procedural_hair(built, resolved["hair"], name_prefix=f"{name}.")
    if resolved["hat"] in wardrobe.HAT_SPECS:
        wardrobe.build_hat(built, resolved["hat"], name_prefix=f"{name}.")
    if resolved["bag"]:
        wardrobe.build_bag(built, resolved["bag"], name_prefix=f"{name}.")
    mh_build.setup_skin(built)
    mh_build.setup_eye_materials(built)
    mh_build.setup_alpha_materials(built)
    problems = rig_ue5.verify_skeleton(built.armature)
    if problems:
        raise RuntimeError(f"{name}: UE5 skeleton verification failed: {problems}")

    scale = vector.height_multiplier
    if abs(scale - 1.0) > 1e-4:
        built.armature.scale = (scale, scale, scale)
        bpy.context.view_layer.update()
    return NpcBuild(index=index, vector=vector, spec=spec, built=built, resolved=resolved)


def apply_walk_style(clips: list[anim_lib.Clip], vector: variety.VarietyVector,
                     rig: pose_solver.Rig) -> list[anim_lib.Clip]:
    """Stamp the pedestrian's walk style onto the clip set: playback rate and a posture offset."""
    style = variety.WALK_STYLES[vector.walk_style % len(variety.WALK_STYLES)]
    out: list[anim_lib.Clip] = []
    from mathutils import Matrix  # noqa: PLC0415
    stoop = Matrix.Rotation(math.radians(style["stoop_deg"]), 4, "X")
    for clip in clips:
        frames = []
        for frame in clip.frames:
            new = {k: v.copy() for k, v in frame.items()}
            for bone, share in (("spine_02", 0.35), ("spine_04", 0.4), ("neck_01", -0.5)):
                base = new.get(bone, Matrix.Identity(4))
                new[bone] = base @ Matrix.Rotation(math.radians(style["stoop_deg"] * share), 4, "X")
            frames.append(new)
        speed = clip.speed_mps
        out.append(anim_lib.Clip(name=clip.name, frames=frames, fps=clip.fps * style["rate"],
                                 method=clip.method, loop=clip.loop, additive=clip.additive,
                                 notes=clip.notes, source=clip.source,
                                 speed_mps=None if speed is None else speed * style["rate"],
                                 extra={**clip.extra, "walk_style": style["id"]}))
    _ = (rig, stoop)
    return out


def author_clip_set(built: mh_build.BuiltHuman) -> tuple[list[anim_lib.Clip], dict]:
    """The shared animation set, authored once against a given body."""
    return build_character.build_clips(built)


def generate(count: int, *, seed_base: int = 0x4E5943, export_glb: bool = True,
             clips_for_first_only: bool = True) -> dict:
    """Generate ``count`` pedestrians, one scene at a time, and export each as a glb."""
    chenv.ensure_dirs()
    NPC_DIR.mkdir(parents=True, exist_ok=True)
    catalog: list[dict] = []
    clip_report: dict = {}
    t0 = time.time()
    for index in range(count):
        nb.reset_scene()
        vector = variety.VarietyVector.from_seed(seed_base + index)
        vector.body_preset = index % len(variety.BODY_PRESETS)      # cover all 24 bodies exactly once
        npc = build_npc(vector, index)
        clips, report = author_clip_set(npc.built)
        if not clip_report:
            clip_report = report
        clips = apply_walk_style(clips, vector, pose_solver.Rig(npc.built.armature))
        for clip in clips:
            anim_lib.push_clip(npc.built.armature, clip)
        anim_lib.set_active_clip(npc.built.armature, bpy.data.actions.get("idle"))

        measurements = mh_build.measure(npc.built)
        entry = {
            "id": npc.spec.name,
            "index": index,
            "variety_vector": npc.vector.as_dict(),
            "variety_bytes": list(npc.vector.as_bytes()),
            "resolved": npc.resolved,
            "measurements_m": {k: round(v, 4) for k, v in measurements.items()},
            "meshes": {o.name: len(o.data.vertices) for o in npc.built.meshes()},
            "bone_count": len(npc.built.armature.data.bones),
            "blendshapes": len(npc.built.face_units),
            "animations": [c.name for c in clips],
        }
        if export_glb:
            extras = {"asset_id": npc.spec.name, "skeleton": "UE5_Mannequin",
                      "variety_vector": npc.vector.as_dict(),
                      "variety_bytes": list(npc.vector.as_bytes()),
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
        log.info("npc %d/%d %s: %.1f m, %d meshes (%.0f s elapsed)", index + 1, count, npc.spec.name,
                 measurements["height_m"], len(npc.built.meshes()), time.time() - t0)

    manifest = {
        "schema_version": 1,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "count": len(catalog),
        "shared_skeleton": "UE5_Mannequin",
        "variety_contract": variety.contract(),
        "wardrobe": [{"id": g.item_id, "label": g.label, "slot": g.slot, "layer": g.layer,
                      "tags": list(g.tags), "notes": g.notes} for g in wardrobe.WARDROBE],
        "hairstyles": [{"id": h[0], "source": h[1], "label": h[2]} for h in wardrobe.HAIRSTYLES],
        "clip_report": clip_report,
        "npcs": catalog,
    }
    out = chenv.OUT_DIR / "npc_variety.json"
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=1, sort_keys=False)
    log.info("wrote %s (%d NPCs, %.0f s)", out, len(catalog), time.time() - t0)
    return manifest


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Generate NYCSim pedestrians")
    parser.add_argument("--count", type=int, default=24, help="how many NPCs (24 covers every base body)")
    parser.add_argument("--seed", type=lambda s: int(s, 0), default=0x4E5943)
    parser.add_argument("--no-glb", action="store_true", help="build and catalogue but do not export")
    args = parser.parse_args(argv)
    manifest = generate(args.count, seed_base=args.seed, export_glb=not args.no_glb)
    print(json.dumps({"count": manifest["count"],
                      "bodies": sorted({n["resolved"]["body_preset"] for n in manifest["npcs"]}),
                      "wardrobe_items": len(manifest["wardrobe"]),
                      "hairstyles": len(manifest["hairstyles"]),
                      "dimensions": manifest["variety_contract"]["dimensions"]}, indent=1))
    return 0


if __name__ == "__main__":
    code = 1
    try:
        code = main(sys.argv[1:])
    except Exception:
        logging.exception("npc generation failed")
    chenv.hard_exit(code)
