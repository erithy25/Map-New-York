"""The vehicle armature: the thing that makes a car a car in Unreal rather than a lump of geometry.

``fusion_hybrid.glb`` shipped with ``skins: 0`` and ``animations: 0`` -- 77 unskinned nodes and not
one bone -- while its catalogue entry reported ``contract_profile: "full"`` and ``missing_nodes: []``.
Both statements were true of what they measured.  ``rig.finalise`` checks that a *node* named
``Wheel_FL`` exists, and one does.  Chaos Vehicles needs a ``USkeletalMesh`` with a *bone* named
``Wheel_FL``, and without a skin Unreal's importer produces a ``UStaticMesh``: the pawn becomes an
invisible physics body with no wheels to drive.  This module is the missing half.

Why every bone is built with an identity rest orientation
---------------------------------------------------------
``NYCVehicleContract.h`` states the axes the engine drives, as *bone-local* axes: a wheel rolls about
local Y and steers about local Z, a door swings about local Z, a bonnet lifts about local Y, a window
drops along local -Z.  Getting those right through Blender bone roll -> glTF node rotation -> Unreal
reference pose is two conversions deep and is the single most likely thing in this rig to be wrong,
because none of it can be tested without the engine.

So the rig removes the conversions instead of trying to survive them.  Every bone that can be is
built with its local frame equal to the vehicle frame itself -- local X forward, local Y left, local
Z up -- which in Blender means a bone pointing along +Y with zero roll, and which is the *identity*
rotation.  Its glTF node then carries a translation and no rotation at all, and in Unreal its
reference-pose local axes are the component's own: X forward, Y right, Z up.  Read against the
contract's table, that single orientation satisfies the wheels (roll about Y, steer about Z), all
four doors (swing about Z), the bonnet and boot (lift about Y), the wipers (sweep about Z), the
windows (drop along -Z) and the mirrors (fold about Z) -- seven of its ten rows -- with nothing left
to convert and nothing to get backwards.

Three bones cannot be identity because the contract asks for rotation about local **X**: the steering
wheel turns about the column, which is raked; the gauge needles sweep about their face normals; the
gear selector turns about its own axis.  Those get an explicit orthonormal frame built from the car's
own geometry -- the column direction measured from the steering wheel and the dash, the needle normal
measured from the gauge faces -- rather than a typed-in angle.

**What this cannot settle here.** The axes are removed from doubt; the *signs* are not.  Blender's
+Y is left and Unreal's +Y is right, so the glTF importer's handedness flip decides whether "+Y is
forward roll" and "positive is open" come out with the sign the contract names.  That is one
comparison on a running engine and a sign flip in ``UNYCVehicleAnimInstance`` if it is wrong; it is
recorded in ``docs/DEVIATIONS.md`` rather than guessed at.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Sequence

import numpy as np

from . import contract, env, geom as g

bpy = env.bpy
log = env.log

#: Default bone length. Long enough to see in Blender, short enough not to reach into another part.
BONE_LENGTH_M = 0.12
#: Socket leaf bones are shorter still; they are points, and their length means nothing.
SOCKET_LENGTH_M = 0.05

#: The vehicle frame, and therefore the rest frame of every bone that has no reason to differ.
#: Columns are the bone's local X, Y, Z. Y is the bone direction (Blender's convention).
IDENTITY_FRAME = ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))

#: Object name -> bone name. Where the two differ it is because ``NYCVehicleContract.h`` says so:
#: the engine looks up ``Door_Hood``, ``Door_Trunk``, ``GearSelector`` and ``Mirror_Interior`` where
#: the Blender build has historically written ``Hood``, ``Trunk``, ``Shifter`` and ``Interior_Mirror``.
#: The objects keep their names -- ``tests/test_vehicles.py`` and the catalogue are built on them --
#: and the bone carries the name the engine will ask for.
BONE_OF_OBJECT: dict[str, str] = {
    "Wheel_FL": "Wheel_FL", "Wheel_FR": "Wheel_FR", "Wheel_RL": "Wheel_RL", "Wheel_RR": "Wheel_RR",
    "Wheel_F": "Wheel_F", "Wheel_R": "Wheel_R",
    "Door_FL": "Door_FL", "Door_FR": "Door_FR", "Door_RL": "Door_RL", "Door_RR": "Door_RR",
    "Hood": "Door_Hood", "Trunk": "Door_Trunk", "FuelFlap": "Door_FuelFlap",
    "SteeringWheel": "SteeringWheel",
    "Wiper_L": "Wiper_L", "Wiper_R": "Wiper_R", "Wiper_Rear": "Wiper_Rear",
    "Window_FL": "Window_FL", "Window_FR": "Window_FR",
    "Window_RL": "Window_RL", "Window_RR": "Window_RR",
    "Mirror_L": "Mirror_L", "Mirror_R": "Mirror_R", "Interior_Mirror": "Mirror_Interior",
    "Shifter": "GearSelector",
    "Needle_Speed": "Needle_Speed", "Needle_RPM": "Needle_RPM",
    "Needle_Fuel": "Needle_Fuel", "Needle_Temp": "Needle_Temp",
    "Stalk_Turn": "Stalk_Turn", "Stalk_Wiper": "Stalk_Wiper",
}

#: Bones whose local X must be an axis of their own rather than the vehicle's forward direction
#: (contract: "rotation about local X"). The frame is measured, never typed.
X_AXIS_BONES = ("SteeringWheel", "GearSelector", "Needle_Speed", "Needle_RPM",
                "Needle_Fuel", "Needle_Temp")

ROOT_BONE = "Body"


@dataclass
class BoneSpec:
    """One bone: where it is, which way its local axes point, and whether it deforms geometry."""

    name: str
    head: tuple[float, float, float]
    #: Columns of the bone's local frame: (local X, local Y, local Z). local Y is the bone direction.
    frame: tuple = IDENTITY_FRAME
    parent: str | None = ROOT_BONE
    length: float = BONE_LENGTH_M
    deform: bool = True
    #: Free-form note carried into the catalogue, so the rig explains itself where it is unusual.
    note: str = ""


def _mat(head, frame, length):
    from mathutils import Matrix, Vector

    x, y, z = (Vector(a).normalized() for a in frame)
    # Re-orthonormalise: a frame measured from geometry is only nearly orthogonal.
    z = x.cross(y).normalized() if abs(x.dot(y)) > 1e-6 else z
    x = y.cross(z).normalized()
    m = Matrix(((x.x, y.x, z.x), (x.y, y.y, z.y), (x.z, y.z, z.z))).to_4x4()
    m.translation = Vector(head)
    return m


def build_armature(name: str, specs: Sequence[BoneSpec], *,
                   collection: "bpy.types.Collection | None" = None):
    """Create the armature object and its rest pose. Data API only; no operators, so this runs headless."""
    from mathutils import Vector

    arm_data = bpy.data.armatures.new(f"{name}_armature")
    arm = bpy.data.objects.new(name, arm_data)
    (collection or bpy.context.scene.collection).objects.link(arm)

    view = bpy.context.view_layer
    prev = view.objects.active
    view.objects.active = arm
    bpy.ops.object.mode_set(mode="EDIT")
    try:
        made: dict[str, object] = {}
        # Parents first: an edit bone's parent must already exist.
        ordered = sorted(specs, key=lambda s: (s.parent is not None, s.name != ROOT_BONE))
        for spec in ordered:
            eb = arm_data.edit_bones.new(spec.name)
            eb.head = Vector(spec.head)
            eb.tail = Vector(spec.head) + Vector((0.0, spec.length, 0.0))
            eb.matrix = _mat(spec.head, spec.frame, spec.length)
            eb.use_deform = bool(spec.deform)
            # Never connected: a connected bone is forced to start at its parent's tail, which would
            # move every pivot in the car to the root.
            eb.use_connect = False
            made[spec.name] = eb
        for spec in ordered:
            if spec.parent and spec.parent in made and spec.parent != spec.name:
                made[spec.name].parent = made[spec.parent]
    finally:
        bpy.ops.object.mode_set(mode="OBJECT")
        view.objects.active = prev
    return arm


def bind_rigid(objects: dict, arm, bone_of: dict[str, str]) -> dict:
    """Skin every object rigidly to one bone: one vertex group, weight 1, no blending.

    Every part of this car is already its own object with its own origin on its own pivot -- the
    build separates by material and ``rig.hinge_door`` / ``pivot_bottom_centre`` have already placed
    those origins. So skinning is a lookup, not weight painting, and a vertex belongs entirely to one
    bone. Anything not named in ``bone_of`` rides the body, which is the right answer for a badge, a
    seat or a wheel arch.

    ``matrix_parent_inverse`` is what keeps the geometry where it was: the part origins are not at
    the vehicle origin, so parenting without it would move every panel by its own offset. The
    regression this guards is exact and is asserted in ``tests/test_vehicle_rig.py``: the skinned
    export must reproduce the unskinned world-space vertex positions.
    """
    from mathutils import Matrix

    report = {"skinned": 0, "to_body": 0, "skipped_collision": 0, "by_bone": {}}
    bones = {b.name for b in arm.data.bones}
    for obj_name, ob in sorted(objects.items()):
        if ob is None or ob.type != "MESH":
            continue
        if obj_name.startswith("UCX_"):
            # Collision proxies are consumed by the importer and never rendered; skinning them would
            # put convex hulls into the skeletal mesh.
            report["skipped_collision"] += 1
            continue
        bone = bone_of.get(obj_name, ROOT_BONE)
        if bone not in bones:
            bone = ROOT_BONE
        if bone == ROOT_BONE and obj_name not in bone_of:
            report["to_body"] += 1
        for vg in list(ob.vertex_groups):
            ob.vertex_groups.remove(vg)
        vg = ob.vertex_groups.new(name=bone)
        vg.add(list(range(len(ob.data.vertices))), 1.0, "REPLACE")
        ob.parent = arm
        ob.matrix_parent_inverse = arm.matrix_world.inverted()
        for mod in list(ob.modifiers):
            if mod.type == "ARMATURE":
                ob.modifiers.remove(mod)
        mod = ob.modifiers.new("Armature", "ARMATURE")
        mod.object = arm
        mod.use_vertex_groups = True
        report["skinned"] += 1
        report["by_bone"][bone] = report["by_bone"].get(bone, 0) + 1
    return report


# --------------------------------------------------------------------------- measured frames


def _bounds(ob):
    pts = g.mesh_points(ob, world=True)
    return pts.min(axis=0), pts.max(axis=0)


def _centre(ob):
    lo, hi = _bounds(ob)
    return (lo + hi) * 0.5


#: Below this an object's origin is taken to be *unset* rather than deliberately at the vehicle origin.
ORIGIN_UNSET_M = 1e-4


def _origin(ob) -> tuple[float, float, float]:
    """The part's pivot, or its own centre when the build never gave it one.

    Most parts have had ``g.set_origin`` put their origin on the axis they turn about -- a door on
    its hinge, a window at the bottom of its glass. Some never did, and their origin is still the
    vehicle origin: the gear selector is one, and a bone there would rotate the shifter about a point
    on the road under the rear axle. An origin at (0, 0, 0) for a part whose geometry is nowhere near
    it is not a pivot, it is an absence, and the part's own centre is the better answer.
    """
    t = ob.matrix_world.translation
    if abs(t.x) > ORIGIN_UNSET_M or abs(t.y) > ORIGIN_UNSET_M or abs(t.z) > ORIGIN_UNSET_M:
        return (float(t.x), float(t.y), float(t.z))
    if ob.type != "MESH" or len(ob.data.vertices) == 0:
        return (0.0, 0.0, 0.0)
    c = _centre(ob)
    if float(np.linalg.norm(c)) <= ORIGIN_UNSET_M:
        return (0.0, 0.0, 0.0)
    return tuple(float(v) for v in c)


def _material_face_frame(ob, slot_name: str):
    """``(centre, normal)`` of the faces on ``ob`` that use material ``slot_name``, in world metres.

    Used for the two screen sockets and the gauge needles: the contract wants their axis to be the
    face normal, and the face is right there in the mesh. Reading it beats typing an angle that
    stops being true the next time the dashboard is rebuilt.
    """
    me = ob.data
    idx = [i for i, m in enumerate(me.materials)
           if m is not None and m.name.split(".")[0] == slot_name]
    if not idx:
        return None
    want = set(idx)
    m = np.array(ob.matrix_world, dtype=np.float64).reshape(4, 4)
    rot, off = m[:3, :3], m[:3, 3]
    n = len(me.polygons)
    if n == 0:
        return None
    nor = np.empty(n * 3, dtype=np.float32)
    cen = np.empty(n * 3, dtype=np.float32)
    area = np.empty(n, dtype=np.float32)
    me.polygons.foreach_get("normal", nor)
    me.polygons.foreach_get("center", cen)
    me.polygons.foreach_get("area", area)
    mats = np.empty(n, dtype=np.int32)
    me.polygons.foreach_get("material_index", mats)
    sel = np.array([i for i in range(n) if int(mats[i]) in want], dtype=np.int64)
    if sel.size == 0:
        return None
    w = area[sel].astype(np.float64)
    if w.sum() <= 0.0:
        w = np.ones_like(w)
    centre = ((cen.reshape(n, 3)[sel].astype(np.float64) @ rot.T + off) * w[:, None]).sum(axis=0) / w.sum()
    normal = (nor.reshape(n, 3)[sel].astype(np.float64) @ rot.T * w[:, None]).sum(axis=0)
    norm = np.linalg.norm(normal)
    if norm < 1e-9:
        return None
    return centre, normal / norm


def _frame_from_x(x_axis) -> tuple:
    """An orthonormal frame whose local X is ``x_axis`` and whose local Z is as near vertical as it can be."""
    x = np.asarray(x_axis, dtype=np.float64)
    x = x / max(float(np.linalg.norm(x)), 1e-9)
    up = np.array([0.0, 0.0, 1.0])
    if abs(float(np.dot(x, up))) > 0.99:
        up = np.array([1.0, 0.0, 0.0])
    y = np.cross(up, x)
    y = y / max(float(np.linalg.norm(y)), 1e-9)
    z = np.cross(x, y)
    return (tuple(x), tuple(y), tuple(z))


# --------------------------------------------------------------------------- the spec list


def bone_specs(objects: dict, dims) -> tuple[list[BoneSpec], dict]:
    """Every bone the car's own geometry supports, positioned from that geometry.

    Nothing here is a typed-in coordinate: a bone's head is the origin of the part it moves, which
    the build has already put on that part's pivot, and the three bones that need a measured axis
    take it from the mesh.
    """
    specs: list[BoneSpec] = [BoneSpec(ROOT_BONE, (0.0, 0.0, 0.0), parent=None,
                                      note="root; the mesh origin is the ground under the rear-axle centre")]
    detail: dict = {"from_object": {}, "measured_frames": {}, "absent": []}

    for obj_name, bone in BONE_OF_OBJECT.items():
        ob = objects.get(obj_name)
        if ob is None:
            detail["absent"].append(bone)
            continue
        head = _origin(ob)
        frame = IDENTITY_FRAME
        note = ""
        if bone in X_AXIS_BONES:
            axis = _measured_x_axis(bone, objects, ob)
            if axis is not None:
                frame = _frame_from_x(axis)
                detail["measured_frames"][bone] = [round(float(v), 5) for v in axis]
                note = "local X measured from the car's own geometry (contract: rotation about local X)"
            else:
                note = ("contract wants rotation about local X but the axis could not be measured; "
                        "left in the vehicle frame")
        specs.append(BoneSpec(bone, head, frame=frame, note=note))
        detail["from_object"][bone] = obj_name

    socket_list, socket_detail = socket_specs(objects, dims)
    specs.extend(socket_list)
    detail["sockets"] = socket_detail
    return specs, detail


def _measured_x_axis(bone: str, objects: dict, ob):
    """The axis the contract wants this bone to rotate about, taken from the mesh."""
    if bone == "SteeringWheel":
        # The column runs from the wheel's centre back and down into the dash. Measure it as the
        # wheel's own face normal: the rim is a lathe about the column, so the disc it spans is
        # perpendicular to the column and its normal is the column axis.
        pts = g.mesh_points(ob, world=True)
        if len(pts) < 4:
            return None
        centred = pts - pts.mean(axis=0)
        # Smallest principal direction of a disc is its normal.
        try:
            _u, _s, vt = np.linalg.svd(centred, full_matrices=False)
        except np.linalg.LinAlgError:
            return None
        axis = vt[-1]
        # Point it forward-and-up, away from the driver, so every car agrees on the sign.
        if axis[0] < 0.0:
            axis = -axis
        return axis
    if bone == "GearSelector":
        # A shifter is either a lever, which turns about the axis across its throw, or a rotary dial,
        # which turns about its own normal. Both are the *smallest* principal direction of the point
        # cloud when the part is disc-like and the *largest* when it is a lever, so the shape decides:
        # a disc has two comparable extents and one small one.
        pts = g.mesh_points(ob, world=True)
        if len(pts) < 4:
            return None
        centred = pts - pts.mean(axis=0)
        try:
            _u, sv, vt = np.linalg.svd(centred, full_matrices=False)
        except np.linalg.LinAlgError:
            return None
        disc_like = sv[1] > 0.55 * sv[0]
        axis = vt[-1] if disc_like else vt[0]
        if axis[2] < 0.0:
            axis = -axis
        return axis
    if bone.startswith("Needle_"):
        # All four, not the two round dials only: the fuel and coolant needles sweep over their own
        # faces and had no axis at all, so they would have been left in the vehicle frame and swept
        # about the car's forward axis instead of about the face they sit on.
        gauge = contract.GAUGE_OF_NEEDLE.get(bone)
        dash = objects.get("Interior_Dash")
        if gauge and dash is not None:
            got = _material_face_frame(dash, gauge)
            if got is not None:
                # Point it forward, away from the driver, exactly as the steering column above and
                # as ``interior.needle_axis`` does. The gauge face itself looks *at* the driver, so
                # its normal is the other way round; taking it unflipped gave a bone axis
                # antiparallel to the axis the needle geometry was built around, and a needle whose
                # rest peg is at eight o'clock sweeping the wrong way reads its scale backwards --
                # a gauge that lies, which is worse than a gauge that does not move.
                axis = np.asarray(got[1], dtype=np.float64)
                return -axis if axis[0] < 0.0 else axis
    return None


def socket_specs(objects: dict, dims) -> tuple[list[BoneSpec], dict]:
    """Attachment points, as non-deforming leaf bones.

    glTF has no socket concept, and it does not need one:
    ``USkeletalMeshComponent::DoesSocketExist`` and ``GetSocketTransform`` resolve **bones as well as
    sockets**, and every consumer in this project uses exactly those two calls
    (``NYCCameraRigComponent``, ``NYCPlayerVehicle``, ``NYCVehicleDashboardComponent``). So a leaf
    bone with ``use_deform`` off is a socket, and it survives the glTF round trip natively.

    Every position below is derived from a part the car already has, so a change to the seats or the
    dash moves the camera and the driver with them instead of leaving them behind.
    """
    specs: list[BoneSpec] = []
    detail: dict = {}

    def add(name: str, head, frame=IDENTITY_FRAME, note: str = "", source: str = ""):
        specs.append(BoneSpec(name, tuple(float(v) for v in head), frame=frame, parent=ROOT_BONE,
                              length=SOCKET_LENGTH_M, deform=False, note=note))
        detail[name] = {"head_m": [round(float(v), 4) for v in head], "from": source}

    seat_l = objects.get("Seat_FL")
    seat_r = objects.get("Seat_FR")
    body = objects.get("Body")
    door_l = objects.get("Door_FL")

    h_point = None
    if seat_l is not None:
        lo, hi = _bounds(seat_l)
        # The H-point is the hip: the seat's own centre in plan, at the top of the cushion, which is
        # the lowest quarter of the seat's height.
        h_point = np.array([(lo[0] + hi[0]) * 0.5, (lo[1] + hi[1]) * 0.5, lo[2] + (hi[2] - lo[2]) * 0.25])
        add("SKT_DriverSeat", h_point, note="H-point: seat centre in plan, top of the cushion",
            source="Seat_FL")
        # Eye point: 620 mm above the H-point and 100 mm forward of it, the SAE eyellipse centre for
        # a 50th-percentile driver.
        add("SKT_CamInterior", h_point + np.array([0.10, 0.0, 0.62]),
            note="driver eye point, H-point + 0.62 m up and 0.10 m forward", source="Seat_FL")
    if seat_r is not None:
        lo, hi = _bounds(seat_r)
        add("SKT_PassengerSeat",
            [(lo[0] + hi[0]) * 0.5, (lo[1] + hi[1]) * 0.5, lo[2] + (hi[2] - lo[2]) * 0.25],
            note="H-point of the front passenger seat", source="Seat_FR")
    if door_l is not None:
        hinge = _origin(door_l)
        lo, hi = _bounds(door_l)
        # Where a driver stands to get in: level with the door, 0.9 m outboard of its outer face,
        # on the ground.
        add("SKT_DriverEntry", [(lo[0] + hi[0]) * 0.5, hi[1] + 0.9, 0.0],
            note="standing position beside the open driver's door, at ground level", source="Door_FL")
        detail.setdefault("SKT_DriverEntry", {})["door_hinge_m"] = [round(float(v), 4) for v in hinge]

    if body is not None:
        lo, hi = _bounds(body)
        add("SKT_CamChase", [lo[0] - 1.2, 0.0, hi[2] + 0.55],
            note="chase camera anchor behind and above the roof; the spring arm extends from here",
            source="Body")
        add("SKT_CamHood", [hi[0] - 0.55, 0.0, hi[2] * 0.62],
            note="bonnet camera, just behind the leading edge", source="Body")
        add("SKT_CamBumper", [hi[0] - 0.05, 0.0, 0.45],
            note="bumper camera at the front face", source="Body")
        add("SKT_EngineBay", [hi[0] - 0.85, 0.0, hi[2] * 0.55],
            note="under the bonnet, where the engine audio emitter sits", source="Body")
        add("SKT_RoofLight", [(lo[0] + hi[0]) * 0.5, 0.0, hi[2]],
            note="roof centre; taxi and emergency fittings attach here", source="Body")
        add("SKT_DestSign", [lo[0] + 0.10, 0.0, hi[2] - 0.25],
            note="rear roofline, for a bus destination sign", source="Body")

    exhaust = objects.get("Exhaust")
    if exhaust is not None:
        lo, hi = _bounds(exhaust)
        add("SKT_Exhaust_L", [lo[0], (lo[1] + hi[1]) * 0.5 + (hi[1] - lo[1]) * 0.25, (lo[2] + hi[2]) * 0.5],
            note="tailpipe exit, left", source="Exhaust")
        add("SKT_Exhaust_R", [lo[0], (lo[1] + hi[1]) * 0.5 - (hi[1] - lo[1]) * 0.25, (lo[2] + hi[2]) * 0.5],
            note="tailpipe exit, right", source="Exhaust")

    for socket, part in (("SKT_Plate_F", "Plate_F"), ("SKT_Plate_R", "Plate_R")):
        ob = objects.get(part)
        if ob is not None:
            add(socket, _centre(ob), note="number plate centre", source=part)

    wheel = objects.get("SteeringWheel")
    if wheel is not None:
        add("SKT_Horn", _centre(wheel), note="steering wheel boss", source="SteeringWheel")

    # The two screens: origin at the face centre, +X out of the glass, which the contract names
    # explicitly because UNYCVehicleDashboardComponent rotates the widget component against it.
    dash = objects.get("Interior_Dash")
    if dash is not None:
        for socket, slot in (("SKT_Screen", "SCREEN_CENTER"), ("SKT_Cluster", "GAUGE_SPEED")):
            got = _material_face_frame(dash, slot)
            if got is None:
                continue
            centre, normal = got
            add(socket, centre, frame=_frame_from_x(normal),
                note=f"centre and normal of the {slot} faces; +X out of the glass", source="Interior_Dash")
            detail[socket]["normal"] = [round(float(v), 5) for v in normal]

    return specs, detail


# --------------------------------------------------------------------------- entry point


def rig_vehicle(v, *, name: str | None = None) -> tuple[dict, object]:
    """Build the armature for a :class:`rig.Vehicle`, skin every part to it, and report what happened.

    Returns ``(record, armature)``. The record goes into the catalogue entry, so a reader sees the
    rig that shipped rather than the rig that was intended: how many bones, which objects went to which bone, which
    contract bones the car does not have geometry for, and which frames were measured rather than
    taken from the vehicle axes.
    """
    specs, detail = bone_specs(v.objects, v.dims)
    arm = build_armature(name or f"{v.id}_rig", specs)
    bind = bind_rigid(v.objects, arm, BONE_OF_OBJECT)
    g.sync()
    return {
        "armature": arm.name,
        "bones": [s.name for s in specs],
        "bone_count": len(specs),
        "deform_bones": sorted(s.name for s in specs if s.deform),
        "socket_bones": sorted(s.name for s in specs if not s.deform),
        "rest_frame": ("identity (vehicle frame: local X forward, local Y left, local Z up) for every "
                       "bone except those the contract turns about local X"),
        "measured_frames": detail["measured_frames"],
        "bone_from_object": detail["from_object"],
        "contract_bones_without_geometry": sorted(detail["absent"]),
        "sockets": detail["sockets"],
        "skinning": {"mode": "rigid, one bone per object, weight 1.0", **bind},
        "notes": [s.note for s in specs if s.note],
    }, arm
