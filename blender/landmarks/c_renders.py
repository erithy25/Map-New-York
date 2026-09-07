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

Camera positions are given in NYC_TM, anchored where possible to a catalog ``origin_tm`` (which is a measured
footprint centroid), so they stay correct if a model is rebuilt.

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
SIZE = (1280, 720)


def catalog(landmark_id: str) -> dict:
    p = CATALOG / f"{landmark_id}.json"
    if not p.exists():
        raise FileNotFoundError(p)
    return json.loads(p.read_text())


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
    """Father Duffy Square, eye level, looking south down the bowtie past One Times Square.

    Father Duffy Square is NYC_TM (-2952, 6576) — the north point of the bowtie, measured from the TKTS steps'
    own footprint (BIN 1085637). The camera stands on the top of the red steps, 6 m above the pavement, and looks
    at One Times Square, whose catalog origin is the aiming point."""
    e = catalog("c_times_square")
    gz = e["origin_tm"][2]
    eye = (-2952.0, 6576.0, gz + 6.0)
    target = (e["origin_tm"][0], e["origin_tm"][1], gz + 55.0)
    origin = (round(eye[0]), round(eye[1]), round(gz))
    scene_from(["c_times_square"], origin)
    ground(origin, gz)
    return render("times_square_from_duffy_square", eye, target, origin, fov=62.0, sun_az=170.0, sun_el=52.0,
                  exposure=-0.35)


def view_billionaires_row():
    """The Sheep Meadow lawn in Central Park, looking south at the West 57th Street towers."""
    eye = (-2056.0, 7979.0, 27.7)                                   # Sheep Meadow, NYC_TM; ground ~26 m NAVD88
    target = (-2400.0, 7220.0, 230.0)                               # the middle of the West 57th Street row
    origin = (round(eye[0]), round(eye[1]), 26)
    scene_from(["c_billionaires_row", "c_the_plaza", "c_carnegie_hall", "c_hearst_tower"], origin)
    ground(origin, 26.0)
    return render("billionaires_row_from_sheep_meadow", eye, target, origin, fov=48.0, sun_az=205.0, sun_el=34.0)


def view_guggenheim():
    """The Fifth Avenue sidewalk opposite the rotunda, looking east."""
    # the rotunda's catalog origin is its own centroid; Fifth Avenue is 47 m to its west (local -x, which is
    # world (-0.875, +0.483) for the Manhattan grid angle used by every C script)
    e = catalog("c_guggenheim")
    ox, oy, gz = e["origin_tm"]
    wx, wy = -0.875, 0.483
    eye = (ox + 47.0 * wx, oy + 47.0 * wy, gz + 1.7)
    target = (ox + 4.0 * wx, oy + 4.0 * wy, gz + 16.0)
    origin = (round(eye[0]), round(eye[1]), round(gz))
    scene_from(["c_guggenheim", "c_metropolitan_museum"], origin)
    ground(origin, gz)
    return render("guggenheim_from_fifth_avenue", eye, target, origin, fov=64.0, sun_az=250.0, sun_el=45.0)


def view_top_of_the_rock():
    """The 30 Rockefeller Plaza observation deck, 259 m above the street, looking south."""
    deck_ground = 20.0                                              # street level at 30 Rock, NAVD88
    eye = (-2478.0, 6591.0, deck_ground + 259.0)
    target = (-2900.0, 5500.0, 180.0)
    origin = (round(eye[0]), round(eye[1]), 15)
    # only what is actually in shot looking south from the deck (and small enough to keep the scene under ~3 GB)
    ids = ["c_times_square", "c_hudson_yards", "c_metlife_building", "c_javits_center", "c_moynihan_train_hall",
           "c_chelsea_market", "c_high_line"]
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
