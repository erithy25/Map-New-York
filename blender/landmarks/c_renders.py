"""Canonical viewpoint renders for landmark agent C.

Builds one Cycles scene per viewpoint from the **exported** ``blender_out/landmarks/*.glb`` files — nothing is
re-modelled here — places each glb at its catalog ``origin_tm`` and renders at 64 samples to
``docs/verification/landmarks/canonical_<view>.png``.

The four viewpoints are the ones the brief names:

* ``times_square_from_duffy_square``  — eye level on Father Duffy Square looking south down the bowtie.
* ``billionaires_row_from_sheep_meadow`` — from the Sheep Meadow lawn in Central Park looking south.
* ``guggenheim_from_fifth_avenue`` — from the Fifth Avenue sidewalk opposite the rotunda.
* ``top_of_the_rock_south`` — from the 30 Rockefeller Plaza observation deck (259 m above the street) looking
  south; ``empire_state.glb`` (agent A) is imported into this scene when it exists, because it is the subject.

Camera positions are given in each landmark's own local frame (reconstructed from the catalog's ``origin_tm`` and
``heading_deg``) or directly in NYC_TM, so they stay correct if a model is rebuilt.

Run: ``python3 blender/landmarks/c_renders.py [view ...]``  (default: all four).
"""
from __future__ import annotations

import json
import math
import os
import sys
from pathlib import Path

_HERE = Path(__file__).resolve()
sys.path.insert(0, str(_HERE.parent))
sys.path.insert(0, str(_HERE.parents[1] / "common"))

import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Vector  # noqa: E402

import common as C  # noqa: E402
import nycsim_bpy as nb  # noqa: E402

OUT = C.OUT_DIR
CATALOG = C.CATALOG_DIR
VERIFY = C.VERIFY_DIR
SAMPLES = int(os.environ.get("NYCSIM_RENDER_SAMPLES", "64"))
SIZE = (1600, 900)


def catalog(landmark_id: str) -> dict:
    p = CATALOG / f"{landmark_id}.json"
    if not p.exists():
        raise FileNotFoundError(p)
    return json.loads(p.read_text())


def local_to_tm(landmark_id: str, x: float, y: float, z: float = 0.0) -> tuple[float, float, float]:
    """A point in a landmark's local build frame -> NYC_TM (using the catalog's origin and heading)."""
    e = catalog(landmark_id)
    ox, oy, oz = e["origin_tm"]
    ang = math.radians((90.0 - float(e["heading_deg"])) % 360.0)
    c, s = math.cos(ang), math.sin(ang)
    return (ox + c * x - s * y, oy + s * x + c * y, oz + z)


def import_glb(path: Path, origin_tm, scene_origin) -> list[bpy.types.Object]:
    """Import one exported landmark and shift it from its own origin to the shared scene origin."""
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(path))
    new = [o for o in bpy.data.objects if o not in before]
    dx = origin_tm[0] - scene_origin[0]
    dy = origin_tm[1] - scene_origin[1]
    dz = origin_tm[2] - scene_origin[2]
    for o in new:
        if o.parent is None:
            o.location = Vector((o.location.x + dx, o.location.y + dy, o.location.z + dz))
        if o.type == "MESH" and o.name.endswith("_LOD1"):
            o.hide_render = True
    return new


def scene_from(ids, scene_origin, *, extra: dict | None = None) -> list[bpy.types.Object]:
    """Fresh scene containing the given landmark ids (skipping any that have not been exported)."""
    nb.reset_scene()
    objs: list[bpy.types.Object] = []
    for lid in ids:
        glb = OUT / f"{lid}.glb"
        if not glb.exists():
            print(f"  (skipping {lid}: {glb.name} not exported)")
            continue
        e = catalog(lid)
        objs += import_glb(glb, e["origin_tm"], scene_origin)
        print(f"  + {lid} at {e['origin_tm']}")
    for lid, origin in (extra or {}).items():
        glb = OUT / f"{lid}.glb"
        if glb.exists():
            objs += import_glb(glb, origin, scene_origin)
            print(f"  + {lid} at {origin}")
    return objs


def ground(scene_origin, z: float, size: float = 12000.0) -> bpy.types.Object:
    b = C.MeshBuilder()
    b.box((0.0, 0.0, z - scene_origin[2] - 0.05), (size, size, 0.1), C.mat("asphalt"))
    return b.build("_render_ground")


def render(name: str, eye_tm, target_tm, scene_origin, *, fov: float = 55.0, sun_az: float = 200.0,
           sun_el: float = 40.0, exposure: float = -0.5) -> Path:
    VERIFY.mkdir(parents=True, exist_ok=True)
    path = VERIFY / f"canonical_{name}.png"
    sc = bpy.context.scene
    sc.view_settings.view_transform = "AgX"
    sc.view_settings.exposure = exposure
    eye = tuple(eye_tm[i] - scene_origin[i] for i in range(3))
    target = tuple(target_tm[i] - scene_origin[i] for i in range(3))
    nb.quick_render(path, camera_location=eye, camera_target=target, fov_deg=fov, size=SIZE, samples=SAMPLES,
                    sun_azimuth_deg=(sun_az + 180.0) % 360.0, sun_elevation_deg=sun_el)
    print(f"  -> {path}")
    return path


# ------------------------------------------------------------------------------------------------------- views
def view_times_square():
    """Father Duffy Square, eye level, looking south down the bowtie past One Times Square."""
    eye = local_to_tm("c_times_square", 132.0, 374.0, 6.0)          # the top of the TKTS red steps
    target = local_to_tm("c_times_square", 176.0, 20.0, 55.0)       # One Times Square's screen wall
    origin = (round(eye[0]), round(eye[1]), round(eye[2] - 6.0))
    scene_from(["c_times_square"], origin)
    ground(origin, eye[2] - 6.0)
    return render("times_square_from_duffy_square", eye, target, origin, fov=62.0, sun_az=170.0, sun_el=52.0,
                  exposure=-0.35)


def view_billionaires_row():
    """The Sheep Meadow lawn in Central Park, looking south at the West 57th Street towers."""
    eye = (-2056.0, 7979.0, 28.0)                                   # Sheep Meadow, NYC_TM; ground ~26 m NAVD88
    target = local_to_tm("c_billionaires_row", -60.0, 20.0, 230.0)
    origin = (round(eye[0]), round(eye[1]), 26)
    scene_from(["c_billionaires_row", "c_the_plaza", "c_carnegie_hall", "c_hearst_tower"], origin)
    ground(origin, 26.0)
    return render("billionaires_row_from_sheep_meadow", eye, target, origin, fov=48.0, sun_az=205.0, sun_el=34.0)


def view_guggenheim():
    """The Fifth Avenue sidewalk opposite the rotunda, looking east."""
    eye = local_to_tm("c_guggenheim", -47.0, -12.0, 1.7)
    target = local_to_tm("c_guggenheim", -6.0, -14.0, 17.0)
    origin = (round(eye[0]), round(eye[1]), round(eye[2] - 1.7))
    scene_from(["c_guggenheim", "c_metropolitan_museum"], origin)
    ground(origin, eye[2] - 1.7)
    return render("guggenheim_from_fifth_avenue", eye, target, origin, fov=64.0, sun_az=250.0, sun_el=45.0)


def view_top_of_the_rock():
    """The 30 Rockefeller Plaza observation deck, 259 m above the street, looking south."""
    deck_ground = 20.0                                              # street level at 30 Rock, NAVD88
    eye = (-2478.0, 6591.0, deck_ground + 259.0)
    target = (-2900.0, 5500.0, 180.0)
    origin = (round(eye[0]), round(eye[1]), 15)
    ids = ["c_times_square", "c_billionaires_row", "c_hudson_yards", "c_metlife_building", "c_citigroup_center",
           "c_seagram_building", "c_lever_house", "c_lipstick_building", "c_hearst_tower", "c_javits_center",
           "c_moynihan_train_hall", "c_chelsea_market", "c_high_line", "c_pier_57", "c_little_island"]
    scene_from(ids, origin)
    esb = OUT / "empire_state.glb"
    if esb.exists():
        e = json.loads((CATALOG / "empire_state.json").read_text())
        import_glb(esb, e["origin_tm"], origin)
        print(f"  + empire_state at {e['origin_tm']} (agent A)")
    else:
        print("  (empire_state.glb not exported by agent A yet — rendering without it)")
    ground(origin, 12.0, size=40000.0)
    return render("top_of_the_rock_south", eye, target, origin, fov=58.0, sun_az=215.0, sun_el=30.0, exposure=-0.4)


VIEWS = {
    "times_square": view_times_square,
    "billionaires_row": view_billionaires_row,
    "guggenheim": view_guggenheim,
    "top_of_the_rock": view_top_of_the_rock,
}


def main(argv=None):
    args = list(argv if argv is not None else sys.argv[1:])
    names = [a for a in args if a in VIEWS] or list(VIEWS)
    for n in names:
        print(f"=== canonical view: {n}")
        VIEWS[n]()
    return 0


if __name__ == "__main__":
    sys.exit(main())
