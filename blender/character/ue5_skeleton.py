"""UE5-Mannequin ("Manny"/SK_Mannequin) skeleton definition for the NYCSim character lane.

The body is rigged by MPFB2 with its ``game_engine`` rig, whose bone names are already the Unreal
mannequin's UE4 set (``pelvis``, ``spine_01..03``, ``clavicle_l`` ... ``pinky_03_r``, ``thigh_l`` ...
``ball_r``, plus a ``Root``).  UE5 differs in three ways, all handled by :mod:`rig_ue5`:

* the spine is five bones (``spine_01`` .. ``spine_05``) instead of three;
* the neck is two bones (``neck_01``, ``neck_02``) instead of one;
* there is a metacarpal bone in front of every finger except the thumb, and a set of IK bones
  (``ik_foot_root``/``ik_foot_l``/``ik_foot_r``, ``ik_hand_root``/``ik_hand_gun``/``ik_hand_l``/``ik_hand_r``).

This module holds the *names and hierarchy only* - the geometry comes from the MakeHuman joint helper cubes
through MPFB, so bone positions follow the actual body shape of each character.
"""
from __future__ import annotations

# --------------------------------------------------------------------------------------------- bone names
FINGERS = ("thumb", "index", "middle", "ring", "pinky")
SIDES = ("l", "r")

#: The three spine bones MPFB's ``game_engine`` rig creates, in order pelvis -> chest.
MPFB_SPINE = ("spine_01", "spine_02", "spine_03")
#: The five UE5 spine bones. ``spine_01``/``spine_02`` come from MPFB's ``spine_01``, ``spine_03``/``spine_04``
#: from MPFB's ``spine_02`` and ``spine_05`` from MPFB's ``spine_03`` (see :func:`spine_split_plan`).
UE5_SPINE = ("spine_01", "spine_02", "spine_03", "spine_04", "spine_05")
UE5_NECK = ("neck_01", "neck_02")


def spine_split_plan() -> list[tuple[str, list[str]]]:
    """(MPFB bone, [UE5 bones it is subdivided into]) - the 3 -> 5 spine map, root-to-chest."""
    return [("spine_01", ["spine_01", "spine_02"]),
            ("spine_02", ["spine_03", "spine_04"]),
            ("spine_03", ["spine_05"])]


def neck_split_plan() -> list[tuple[str, list[str]]]:
    """(MPFB bone, [UE5 bones]) - the 1 -> 2 neck map."""
    return [("neck_01", ["neck_01", "neck_02"])]


def finger_bones(side: str) -> list[str]:
    """Full UE5 finger chain for one hand, parent-first."""
    out: list[str] = []
    for f in FINGERS:
        if f != "thumb":
            out.append(f"{f}_metacarpal_{side}")
        out.extend(f"{f}_0{i}_{side}" for i in (1, 2, 3))
    return out


IK_BONES: tuple[tuple[str, str], ...] = (
    ("ik_foot_root", "root"),
    ("ik_foot_l", "ik_foot_root"),
    ("ik_foot_r", "ik_foot_root"),
    ("ik_hand_root", "root"),
    ("ik_hand_gun", "ik_hand_root"),
    ("ik_hand_l", "ik_hand_gun"),
    ("ik_hand_r", "ik_hand_gun"),
)

#: Which FK bone each IK bone copies at bake time (UE convention: ``ik_hand_gun`` follows the right hand,
#: ``ik_hand_l`` follows the left hand, the roots stay at the actor origin).
IK_FOLLOW: dict[str, str | None] = {
    "ik_foot_root": None, "ik_hand_root": None,
    "ik_foot_l": "foot_l", "ik_foot_r": "foot_r",
    "ik_hand_gun": "hand_r", "ik_hand_r": "hand_r", "ik_hand_l": "hand_l",
}


def ue5_bone_names() -> list[str]:
    """Every bone of the delivered skeleton, parents before children."""
    names = ["root", "pelvis", *UE5_SPINE]
    for side in SIDES:
        names.append(f"clavicle_{side}")
        names += [f"upperarm_{side}", f"lowerarm_{side}", f"hand_{side}"]
        names += finger_bones(side)
    names += [*UE5_NECK, "head"]
    for side in SIDES:
        names += [f"thigh_{side}", f"calf_{side}", f"foot_{side}", f"ball_{side}"]
    names += [b for b, _ in IK_BONES]
    return names


def ue5_parents() -> dict[str, str | None]:
    """bone -> parent name (``None`` for ``root``)."""
    p: dict[str, str | None] = {"root": None, "pelvis": "root"}
    prev = "pelvis"
    for s in UE5_SPINE:
        p[s] = prev
        prev = s
    chest = UE5_SPINE[-1]
    p[UE5_NECK[0]] = chest
    p[UE5_NECK[1]] = UE5_NECK[0]
    p["head"] = UE5_NECK[1]
    for side in SIDES:
        p[f"clavicle_{side}"] = chest
        p[f"upperarm_{side}"] = f"clavicle_{side}"
        p[f"lowerarm_{side}"] = f"upperarm_{side}"
        p[f"hand_{side}"] = f"lowerarm_{side}"
        for f in FINGERS:
            if f == "thumb":
                p[f"thumb_01_{side}"] = f"hand_{side}"
            else:
                p[f"{f}_metacarpal_{side}"] = f"hand_{side}"
                p[f"{f}_01_{side}"] = f"{f}_metacarpal_{side}"
            p[f"{f}_02_{side}"] = f"{f}_01_{side}"
            p[f"{f}_03_{side}"] = f"{f}_02_{side}"
        p[f"thigh_{side}"] = "pelvis"
        p[f"calf_{side}"] = f"thigh_{side}"
        p[f"foot_{side}"] = f"calf_{side}"
        p[f"ball_{side}"] = f"foot_{side}"
    for b, par in IK_BONES:
        p[b] = par
    return p


# ------------------------------------------------------------------------------------ CMU mocap retarget map
#: CMU ASF bone -> UE5 bone.  The CMU skeleton is coarser than the mannequin: it has one bone per spine third
#: and lumps the four fingers into ``lfingers``/``rfingers``.  The spine and neck fan-out is applied by
#: :data:`CMU_SPINE_FANOUT`; the fingers are driven as a uniform curl by :data:`CMU_FINGER_DRIVERS`.
CMU_TO_UE5: dict[str, str] = {
    "root": "pelvis",
    "lowerback": "spine_01",
    "upperback": "spine_03",
    "thorax": "spine_05",
    "lowerneck": "neck_01",
    "upperneck": "neck_02",
    "head": "head",
    "lclavicle": "clavicle_l", "rclavicle": "clavicle_r",
    "lhumerus": "upperarm_l", "rhumerus": "upperarm_r",
    "lradius": "lowerarm_l", "rradius": "lowerarm_r",
    "lwrist": "hand_l", "rwrist": "hand_r",
    "lfemur": "thigh_l", "rfemur": "thigh_r",
    "ltibia": "calf_l", "rtibia": "calf_r",
    "lfoot": "foot_l", "rfoot": "foot_r",
    "ltoes": "ball_l", "rtoes": "ball_r",
}

#: UE5 bones with no direct CMU counterpart that are interpolated between the two named CMU-mapped UE5 bones
#: with the given blend factor (0 = fully the first, 1 = fully the second), in *world rotation* space.
CMU_SPINE_FANOUT: dict[str, tuple[str, str, float]] = {
    "spine_02": ("spine_01", "spine_03", 0.5),
    "spine_04": ("spine_03", "spine_05", 0.5),
}

#: CMU bone -> (UE5 finger bones, gain).  ``lfingers``/``rfingers`` is a single curl channel for the four
#: fingers; the metacarpals stay at rest.
CMU_FINGER_DRIVERS: dict[str, tuple[tuple[str, ...], float]] = {
    "lfingers": (tuple(f"{f}_0{i}_l" for f in ("index", "middle", "ring", "pinky") for i in (1, 2, 3)), 1.0),
    "rfingers": (tuple(f"{f}_0{i}_r" for f in ("index", "middle", "ring", "pinky") for i in (1, 2, 3)), 1.0),
    "lthumb": (("thumb_01_l", "thumb_02_l", "thumb_03_l"), 1.0),
    "rthumb": (("thumb_01_r", "thumb_02_r", "thumb_03_r"), 1.0),
}

#: CMU bones used to measure the source subject's leg length (hip -> ankle) for the speed rescale.
CMU_LEG_CHAIN = ("lfemur", "ltibia")
UE5_LEG_CHAIN = ("thigh_l", "calf_l")
