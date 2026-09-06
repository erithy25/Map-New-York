"""Build the NYCSim player character and its animation set, and export it as ``character/player.glb``.

Run headless with the ``bpy`` module::

    nice -n 10 python3 blender/character/build_character.py

Outputs
-------
``blender_out/character/player.glb``            rig + 25 glTF animations + 52 ARKit morph targets
``blender_out/character/catalog/player.json``   catalog entry (bones, clips, assets, licences, measurements)
``blender_out/character/player.blend``          the scene, so the verification renders do not rebuild it
"""
from __future__ import annotations

import json
import logging
import math
import sys
import time
from pathlib import Path

import chenv

chenv.setup_logging()

import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

import anim_lib  # noqa: E402
import anim_procedural  # noqa: E402
import car_ref  # noqa: E402
import mh_build  # noqa: E402
import nycsim_bpy as nb  # noqa: E402
import pose_solver  # noqa: E402
import retarget  # noqa: E402
import rig_ue5  # noqa: E402
import wardrobe  # noqa: E402

log = logging.getLogger("nycsim.character.build")

# --------------------------------------------------------------------------------------------- the person
#: The player character.  The home address is a real residential building: BIN 4006653 / BBL 4005690038,
#: PLUTO building class C1 (walk-up apartments, six families or more, no stores), land use 2 (multi-family
#: walk-up), four storeys, built 1926, tile t_1_7 of `data/processed/buildings/buildings_base.parquet`.
PLAYER = {
    "name": "Nikos Vlahos",
    "short_name": "Nick",
    "age": 34,
    "home_address": "23-22 31st Avenue, Apt 3R, Astoria, Queens, NY 11106",
    "home_bin": 4006653,
    "home_bbl": 4005690038,
    "home_bldg_class": "C1",
    "home_land_use": 2,
    "home_year_built": 1926,
    "home_floors": 4,
    "home_tile": "t_1_7",
    "home_nta": "QN0103",
    "home_centroid_nyctm": [1859.8641015472576, 7345.275265067614],
    "occupation": "TLC-licensed for-hire driver, nights; MTA bus mechanic's apprentice by day",
}

PLAYER_SPEC = mh_build.HumanSpec(
    name="nikos_vlahos",
    gender=0.93, age=0.44, muscle=0.60, weight=0.52, height=0.60, proportions=0.62,
    cupsize=0.0, firmness=0.5,
    african=0.06, asian=0.14, caucasian=0.80,
    skin="middleage_caucasian_male",
    eyes_material="brown",
    hair="short01", eyebrows="eyebrow006", eyelashes="eyelashes02",
)

#: The player's outfit: three layers, all real tailored MakeHuman CC0 meshes - a crew tee under a knit
#: pullover, wool trousers and low sneakers - plus a procedural hood on the pullover and a procedural
#: wristwatch.  Only two garments cover the torso: `LAYER_MH_PUSH` can stand one fitted layer off another
#: cleanly, but three MakeHuman torso shells fitted to the same body cannot all clear each other, and the
#: middle one is the one that then shows through.
PLAYER_WARDROBE = ("tee_white", "jeans_indigo", "hoodie_grey", "sneakers_black")

# ----------------------------------------------------------------------------------------------- mocap map
#: Which CMU trial drives which locomotion clip, chosen by *measuring* the mean root speed of all nine
#: downloaded AMC files (see `docs/verification/character/REPORT.md`), not by trusting the trial numbering.
MOCAP_CLIPS = (
    {"clip": "walk", "subject": "07", "trial": "07_01", "target_speed": 1.4},
    {"clip": "jog", "subject": "16", "trial": "16_35", "target_speed": 2.8},
    {"clip": "run", "subject": "09", "trial": "09_01", "target_speed": 5.0},
)
IDLE_SOURCE = {"subject": "07", "trial": "07_01"}


# --------------------------------------------------------------------------------------------- build steps
def build_body(spec: mh_build.HumanSpec, outfit: tuple[str, ...], *, watch: bool = True) -> mh_build.BuiltHuman:
    """MPFB body -> ARKit blendshapes -> helper strip -> eye split -> UE5 rig -> clothing -> materials."""
    prefix = f"{spec.name}."
    spec.clothes = tuple(spec.clothes) + wardrobe.makehuman_assets(outfit)
    built = mh_build.build_human(spec, subdiv=0, load_clothes=bool(spec.clothes))
    wardrobe.finish_makehuman(built, outfit, name_prefix=prefix)
    mh_build.bake_and_load_face_units(built)
    mh_build.transfer_tongue_morph(built)
    mh_build.strip_helper_geometry(built)
    mh_build.split_eyes(built)
    # The rig is converted before the procedural layer is cut, so its regions and inherited weights are
    # already in UE5 bone names.
    rig_ue5.convert_to_ue5(built.armature, built.meshes())
    wardrobe.reweight_from_body(built, outfit, name_prefix=prefix)
    if outfit:
        wardrobe.dress(built, outfit, name_prefix=prefix)
    wardrobe.resolve_layers(built, outfit, name_prefix=prefix)
    if watch:
        wardrobe.build_watch(built, side="l", name_prefix=prefix)
    # Last geometry step: the skin under the clothes is removed only once every garment - MakeHuman and
    # procedural - is in place, so the "is this vertex actually covered?" test sees the finished outfit and
    # the KD-tree weight transfers above still see a complete body.
    mh_build.hide_body_under_clothes(built)
    mh_build.setup_skin(built)
    mh_build.setup_eye_materials(built)
    mh_build.setup_alpha_materials(built)
    problems = rig_ue5.verify_skeleton(built.armature)
    if problems:
        raise RuntimeError(f"UE5 skeleton verification failed: {problems}")
    return built


def build_clips(built: mh_build.BuiltHuman) -> tuple[list[anim_lib.Clip], dict]:
    """Retarget the CMU locomotion clips and author everything else. Returns (clips, report)."""
    anim_lib.set_scene_fps()          # one key per frame at 30 fps, in the .blend as well as the .glb
    rig = pose_solver.Rig(built.armature)
    bad = rig.check_inheritance()
    if bad:
        raise RuntimeError(f"bones with non-standard inheritance would break the pose solver: {bad}")
    body = anim_procedural.BodyRef(rig)
    forward_yaw = math.degrees(math.atan2(body.forward.y, body.forward.x))
    log.info("character forward is %s (yaw %.1f deg), leg %.3f m, arm %.3f m",
             [round(v, 3) for v in body.forward], forward_yaw, body.leg_length, body.arm_length)

    report = {"forward_axis_blender": _axis_name(body.forward), "forward_yaw_deg": round(forward_yaw, 2),
              "leg_length_m": round(body.leg_length, 4), "arm_length_m": round(body.arm_length, 4),
              "mocap": [], "source_speeds_mps": {}}

    clips: list[anim_lib.Clip] = []
    walk_frames: list[dict] = []
    for entry in MOCAP_CLIPS:
        source = retarget.load_source(chenv.MOCAP_DIR / f"{entry['subject']}.asf",
                                      chenv.MOCAP_DIR / f"{entry['trial']}.amc")
        result = retarget.retarget(source, rig, name=entry["clip"],
                                   target_speed_mps=entry["target_speed"], forward_yaw_deg=forward_yaw)
        clip = anim_lib.Clip(name=entry["clip"], frames=result.frames, loop=True,
                             method="cmu-mocap-retarget", speed_mps=entry["target_speed"],
                             source=f"CMU {result.source}",
                             notes=f"source {result.source_speed_mps:.2f} m/s on a "
                                   f"{source.leg_length_m:.3f} m leg; scaled to this character's "
                                   f"{body.leg_length:.3f} m leg gives {result.equivalent_speed_mps:.2f} m/s, "
                                   f"played at {1.0 / result.time_scale:.3f}x to reach "
                                   f"{entry['target_speed']:.1f} m/s",
                             extra={"cycle_frames_source": result.cycle_frames_source,
                                    "time_scale": round(result.time_scale, 4),
                                    "equivalent_speed_mps": round(result.equivalent_speed_mps, 3)})
        clips.append(clip)
        report["mocap"].append({"clip": entry["clip"], "source": result.source,
                                "source_speed_mps": round(result.source_speed_mps, 3),
                                "source_leg_m": round(source.leg_length_m, 3),
                                "equivalent_speed_mps": round(result.equivalent_speed_mps, 3),
                                "target_speed_mps": entry["target_speed"],
                                "playback_rate": round(1.0 / result.time_scale, 4),
                                "frames": len(result.frames),
                                "cycle_s": round(len(result.frames) / anim_lib.FPS, 4)})
        if entry["clip"] == "walk":
            walk_frames = result.frames[:-1]

    idle_source = retarget.load_source(chenv.MOCAP_DIR / f"{IDLE_SOURCE['subject']}.asf",
                                       chenv.MOCAP_DIR / f"{IDLE_SOURCE['trial']}.amc")
    standing = retarget.standing_pose_from_locomotion(idle_source, rig, forward_yaw_deg=forward_yaw)

    # CMU's single finger-curl channel leaves the MakeHuman rest hand almost flat, which reads as splayed
    # fingers; the resting curl is composed on at 60 % so the mocap curl still shows through.
    curl = anim_procedural.finger_curl_sign(rig)
    for clip in clips:
        clip.frames = [anim_procedural.with_relaxed_hands(rig, frame, curl, scale=0.6)
                       for frame in clip.frames]
    walk_frames = [dict(f) for f in clips[0].frames[:-1]] if clips else []

    package = car_ref.driver_package()
    author = anim_procedural.ProceduralClips(rig, body, package, standing, walk_frames,
                                             fps=float(anim_lib.FPS))
    clips.extend(author.build_all())
    report["driver_package"] = package.as_dict()
    return clips, report


def _axis_name(v: Vector) -> str:
    axes = {"+X": Vector((1, 0, 0)), "-X": Vector((-1, 0, 0)), "+Y": Vector((0, 1, 0)), "-Y": Vector((0, -1, 0))}
    return max(axes, key=lambda k: axes[k].dot(v))


def export(built: mh_build.BuiltHuman, clips: list[anim_lib.Clip], report: dict, *,
           asset_id: str = "player") -> dict:
    """Bake every clip onto the rig, export the glb and write the catalog entry."""
    chenv.ensure_dirs()
    armature = built.armature
    for clip in clips:
        anim_lib.push_clip(armature, clip)
    anim_lib.set_active_clip(armature, bpy.data.actions.get("idle"))

    measurements = mh_build.measure(built)
    bones = [b.name for b in armature.data.bones]
    extras = {
        "asset_id": asset_id,
        "character": PLAYER if asset_id == "player" else {"id": asset_id},
        "skeleton": "UE5_Mannequin",
        "bone_count": len(bones),
        "forward_axis_blender": report["forward_axis_blender"],
        "up_axis_blender": "Z",
        "origin": "ground between the feet",
        "fps": anim_lib.FPS,
        "animations": [c.metadata() for c in clips],
        "blendshapes": built.face_units,
        "blendshape_standard": "ARKit-52",
        "skin": report.get("skin", {}),
        "eyes": report.get("eyes", {}),
        "max_bone_influences": 4,
        "car_attach": {
            "vehicle": "fusion_hybrid",
            "socket_car_local_m": [round(report["driver_package"]["hip_point"][0], 4),
                                   round(report["driver_package"]["hip_point"][1], 4), 0.0],
            "note": "for the seated clips, put the character's origin at this point in the car's frame, "
                    "aligned with the car's +X",
        },
    }
    path = anim_lib.export_character(chenv.OUT_DIR / f"{asset_id}.glb", [armature, *built.meshes()], extras)
    summary = anim_lib.glb_summary(path)

    entry = {
        "id": asset_id,
        "glb": str(path.relative_to(chenv.REPO_ROOT)),
        "schema_version": nb.SCHEMA_VERSION,
        "skeleton": "UE5_Mannequin",
        "bones": bones,
        "bone_count": len(bones),
        "blendshapes": built.face_units,
        "animations": [c.metadata() for c in clips],
        "measurements_m": {k: round(v, 4) for k, v in measurements.items()},
        "meshes": {o.name: len(o.data.vertices) for o in built.meshes()},
        "glb": summary,
        "character": PLAYER if asset_id == "player" else {"id": asset_id},
        "assets": asset_licences(built),
        **{k: v for k, v in report.items() if k not in ("skin", "eyes")},
    }
    entry["glb"] = str(path.relative_to(chenv.REPO_ROOT))
    entry["glb_summary"] = summary
    anim_lib.write_catalog(entry)
    log.info("exported %s (%.1f MB): %d animations, %d morph targets, %d joints",
             path.name, summary["bytes"] / 1e6, len(summary["animations"]), summary["morph_targets"],
             summary["skin_joints"][0] if summary["skin_joints"] else 0)
    return entry


def asset_licences(built: mh_build.BuiltHuman) -> dict:
    """Which MakeHuman/CMU assets went into this character, with their licences."""
    spec = built.spec
    used = {
        "mpfb2": {"version": "2.0.17", "licence": "GPL-3.0-or-later (add-on code); bundled hm08 base mesh "
                                                  "and targets CC0-1.0", "role": "base mesh, macro targets, "
                                                                                 "game_engine rig, weights"},
        "faceunits01": {"licence": "CC0-1.0", "author": "Mika Suominen",
                        "role": f"{len(built.face_units)} ARKit face-unit blendshapes",
                        **mh_build.face_unit_licences()},
        "makehuman_system_assets": {"licence": "CC0-1.0", "author": "MakeHuman team / Data Collection AB",
                                    "role": f"eyes ({mh_build.EYES_ASSET}), teeth ({spec.teeth}), "
                                            f"tongue ({spec.tongue}), hair ({spec.hair}), "
                                            f"skin ({spec.skin})"},
        "eyebrows01": {"licence": "CC0-1.0", "author": "Mindfront et al.", "role": f"eyebrows ({spec.eyebrows})"},
        "eyelashes01": {"licence": "CC0-1.0", "author": "Mindfront et al.",
                        "role": f"eyelashes ({spec.eyelashes})"},
        "cmu_mocap": {"licence": "CMU Graphics Lab Motion Capture Database - free for all uses",
                      "author": "Carnegie Mellon University Graphics Lab",
                      "role": "walk / jog / run retarget sources and the idle base posture"},
        "procedural": {"licence": "this repository", "role": "wardrobe, watch, bags, hats, all non-locomotion "
                                                             "animation"},
    }
    return used


def main() -> int:
    t0 = time.time()
    chenv.ensure_dirs()
    nb.reset_scene()
    built = build_body(PLAYER_SPEC, PLAYER_WARDROBE)
    skin = mh_build.setup_skin(built)
    eyes = mh_build.setup_eye_materials(built)
    log.info("body built in %.1f s", time.time() - t0)

    clips, report = build_clips(built)
    report["skin"] = skin
    report["eyes"] = eyes
    log.info("%d clips authored in %.1f s", len(clips), time.time() - t0)

    entry = export(built, clips, report)
    blend_path = chenv.OUT_DIR / "player.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
    log.info("saved %s", blend_path)

    print(json.dumps({"asset": entry["id"], "bones": entry["bone_count"],
                      "blendshapes": len(entry["blendshapes"]),
                      "animations": [c["name"] for c in entry["animations"]],
                      "glb_bytes": entry["glb_summary"]["bytes"],
                      "measurements_m": entry["measurements_m"],
                      "seconds": round(time.time() - t0, 1)}, indent=1))
    return 0


if __name__ == "__main__":
    code = 1
    try:
        code = main()
    except Exception:
        logging.exception("character build failed")
    chenv.hard_exit(code)
