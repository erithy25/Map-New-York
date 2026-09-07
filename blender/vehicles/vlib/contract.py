"""The Blender side of the vehicle naming contract, with no ``bpy`` in it.

``NYCVehicleContract.h`` is the single authority; this module is the exporter's copy of it, kept
apart from ``rig.py`` for one reason: ``rig.py`` imports ``bpy``, so nothing that runs under plain
pytest could ever read it, and ``tests/test_vehicles.py`` grew a **third** hardcoded copy of the same
lists to work around that. Two copies of a contract drift; three cannot help it. This is the one the
exporter writes from and the one the tests compare against, and
``tests/test_vehicle_contract_agreement.py`` compares it against the engine headers name by name.
"""
from __future__ import annotations

PIVOT_CONVENTION = "ground under rear-axle centre, +X forward, +Y left, +Z up (DATA_CONTRACTS §13)"

#: The lamp slots, named exactly as ``NYCVehicleContract.cpp`` ``LightSlots()`` names them.
#:
#: They did not use to be. The exporter wrote ``LIGHT_TURN_FL/FR/RL/RR`` where the engine drives
#: ``LIGHT_IND_*``, one ``LIGHT_HIGH`` and one ``LIGHT_DRL`` where the engine drives left/right pairs,
#: ``LIGHT_BRAKE_CHMSL`` for ``LIGHT_BRAKE_C``, and nothing at all for the fog lamps, the side
#: repeaters, the courtesy light and the instrument backlight. ``UNYCVehicleLightsComponent`` finds
#: its lamps by material-slot name, so all fifteen of those were dead: every indicator, both high
#: beams, both daytime running lights and the centre brake light included.
#: ``tests/test_vehicle_contract_agreement.py`` compares the two lists name by name so it cannot
#: drift again.
LIGHT_SLOTS_FULL = (
    "LIGHT_HEAD_L", "LIGHT_HEAD_R", "LIGHT_HIGH_L", "LIGHT_HIGH_R", "LIGHT_DRL_L", "LIGHT_DRL_R",
    "LIGHT_FOG_L", "LIGHT_FOG_R", "LIGHT_TAIL_L", "LIGHT_TAIL_R", "LIGHT_BRAKE_L", "LIGHT_BRAKE_R",
    "LIGHT_BRAKE_C", "LIGHT_REVERSE_L", "LIGHT_REVERSE_R", "LIGHT_IND_FL", "LIGHT_IND_FR",
    "LIGHT_IND_RL", "LIGHT_IND_RR", "LIGHT_IND_SL", "LIGHT_IND_SR", "LIGHT_PLATE",
    "LIGHT_INTERIOR", "LIGHT_DASH",
)

#: Lamps the car really has that the engine has no slot for. Declared rather than dropped: the
#: geometry is real and a reader should see why it carries a LIGHT_ name nothing drives.
LIGHT_SLOTS_EXTRA = ("LIGHT_LOW",)

#: The parts a full-profile vehicle must exist as separate **objects**, because each of them is a
#: bone the engine moves or a surface it needs to find on its own.
PART_NODES_FULL = (
    "Body", "Wheel_FL", "Wheel_FR", "Wheel_RL", "Wheel_RR",
    "Door_FL", "Door_FR", "Door_RL", "Door_RR",
    "SteeringWheel", "Hood", "Trunk", "Wiper_L", "Wiper_R",
    "Window_WS", "Window_BACK", "Window_FL", "Window_FR", "Window_RL", "Window_RR",
    "Mirror_L", "Mirror_R", "Interior_Dash", "Shifter", "Pedals", "Plate_F", "Plate_R",
)

#: The lamps that are their own object. Not every lamp is, and it was a mistake to require that they
#: all be: ``UNYCVehicleLightsComponent`` finds a lamp by its **material slot** and never by node, so
#: a side repeater moulded into the mirror cap, a courtesy light in the headliner and the instrument
#: backlight on the dash are lamps that correctly have no object of their own. Requiring a node for
#: each of the 24 slots would force three pieces of geometry to exist that no real car has as a
#: separate part.
LIGHT_NODES_FULL = tuple(s for s in LIGHT_SLOTS_FULL
                         if s not in ("LIGHT_IND_SL", "LIGHT_IND_SR", "LIGHT_INTERIOR", "LIGHT_DASH")
                         ) + LIGHT_SLOTS_EXTRA

CONTRACT_FULL = PART_NODES_FULL + LIGHT_NODES_FULL

#: ``InstrumentSlots()`` names five, not three: the cluster's own strip display (``SCREEN_CLUSTER``)
#: and the fuel gauge (``GAUGE_FUEL``) were missing along with the lamps above.
MATERIAL_SLOTS_FULL = ("MIRROR_GLASS", "GAUGE_SPEED", "GAUGE_RPM", "GAUGE_FUEL", "SCREEN_CENTER",
                       "SCREEN_CLUSTER", "PLATE_FACE") + LIGHT_SLOTS_FULL

DMG_REGIONS = ("FRONT", "REAR", "LEFT", "RIGHT", "ROOF")


#: Bones the engine looks up that need geometry this build does not have. Named here so the gap is a
#: statement rather than a silence; ``blender/vehicles/vlib/skel.py`` reports the same set per car.
BONES_WITHOUT_GEOMETRY = ("Door_FuelFlap", "Wiper_Rear", "Stalk_Turn", "Stalk_Wiper",
                          "Needle_Speed", "Needle_RPM", "Needle_Fuel", "Needle_Temp")
