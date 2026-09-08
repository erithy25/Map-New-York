"""Put a frame of the running simulation into the verification scene.

Every comparison sheet before this showed an empty city (`docs/DEVIATIONS.md` I13): 51 of the 57
written assessments record that there are no people in the frame and 37 that there are no vehicles.
That was never a statement about the world -- the traffic and pedestrian simulations exist, are
tested and hold their invariants -- but about the *verification path*, which loaded terrain,
buildings, pavement, props, kit and landmarks and no agent of any kind.

This module closes that.  What it places is **one frame of the shipped simulation**, not a
scattering:

* ``blender/verify/agent_snapshot.cpp`` steps ``nycsim_gameplay::TrafficSim`` and
  ``nycsim_gameplay::PedSim`` -- the very code the Unreal traffic subsystem steps on its worker
  thread -- over the real city read from ``data/processed/runtime/*.nycb`` (79,291 nodes, 381,971
  road lanes, the 262-cell neighbourhood density calibration bound to 848,116 lanes), and writes the
  same ``VehicleSnapshot`` / ``PedSnapshot`` records ``UNYCTrafficSubsystem`` reads out of the
  worker's double buffer.  ``unreal/tools/gameplay_selftest.cpp`` compiles those same four adapter
  files against a synthetic grid; this tool compiles them against the shipped road graph, and that
  is the only difference between the two.
* the agents are then placed at the *scene's own* ground: a vehicle sits on the roadbed polygon it
  is standing on, at the heightmap height plus that surface's own lift, facing along its lane; a
  pedestrian stands on a sidewalk, plaza, median or crosswalk polygon.  An agent that is not on a
  surface of the right kind, or that falls inside a real building footprint, is **dropped and
  counted** rather than drawn floating or in a wall.

The honesty rule this module exists under: what lands in the frame is *a* frame of the simulation
at a stated timestamp and seed, calibrated to that neighbourhood's own density table.  It is not
the traffic in the reference photograph and it must never be captioned as though it were.  The
report this returns carries the seed, the clock, the density-table target, the counts reached and
every drop with its reason, and ``render_sheets.py`` prints all of it on the sheet.

Run standalone to check the tool and the asset mapping::

    python3 blender/verify/agents.py --audit
    python3 blender/verify/agents.py --x -2932 --y 6566 --hour 12 --dow 0 --json -
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import math
import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]

LOG = logging.getLogger("nycsim.verify.agents")

PROCESSED = REPO_ROOT / "data" / "processed"
RUNTIME_DIR = PROCESSED / "runtime"
BLENDER_OUT = REPO_ROOT / "blender_out"
VEHICLE_DIR = BLENDER_OUT / "vehicles"
VEHICLE_CATALOG = VEHICLE_DIR / "catalog"
NPC_DIR = BLENDER_OUT / "character" / "npc"
NPC_VARIETY = BLENDER_OUT / "character" / "npc_variety.json"
PAVEMENT_DIR = PROCESSED / "roads" / "pavement"
TILES_DATA = PROCESSED / "tiles"

SNAPSHOT_SRC = REPO_ROOT / "blender" / "verify" / "agent_snapshot.cpp"
SNAPSHOT_BIN = BLENDER_OUT / "verify" / "agent_snapshot"
SNAPSHOT_CACHE = BLENDER_OUT / "verify" / "agents"

#: The four adapter translation units the snapshot tool compiles against, plus the core sources
#: they need.  Kept here rather than in a script so a build failure names exactly what was missing.
ADAPTER_DIR = REPO_ROOT / "unreal" / "NYCSim" / "Source" / "NYCSimRuntime" / "Private" / "CoreAdapter"
CORE_INCLUDE = REPO_ROOT / "core" / "include"
CORE_SRC = REPO_ROOT / "core" / "src"

TILE_SIZE_M = 1000.0

#: Pavement kinds (``data/processed/roads/pavement/{tile}.parquet``) and the lift
#: :func:`scene.add_pavement` draws each one at, so an agent stands on the surface the render
#: actually has rather than on the bare heightmap.  Duplicated from ``scene.PAVEMENT_KINDS``
#: deliberately: ``tests/test_agents.py`` asserts the two agree, so a change to one is a test
#: failure rather than a silent 0.15 m float.
#: The paint (kinds 10 and 11) is deliberately **not** here.  It is 4 mm of thermoplastic laid on
#: a surface that is in this table, not a surface of its own: a car crossing a lane line is on the
#: roadbed and a walker on a crossing bar is on the crossing.  Listing it would make an agent that
#: happened to stand over a line "not on a walkable surface" and drop it.
PAVEMENT_LIFT_M = {0: 0.10, 1: 0.25, 2: 0.25, 3: 0.25, 4: 0.25, 5: 0.101, 6: 0.10}
PAVEMENT_NAME = {0: "roadbed", 1: "sidewalk", 2: "median", 3: "plaza", 4: "curb", 5: "crosswalk",
                 6: "parking_lot"}
#: A vehicle belongs on the carriageway: the roadbed, the crosswalk painted across it, or a
#: parking lot.  Not on a median, a sidewalk or a plaza.
VEHICLE_SURFACES = (0, 5, 6)
#: A pedestrian belongs on a walking surface.  The roadbed is included only for a walker the
#: simulation says is in the carriageway (crossing or jaywalking) -- see :func:`_ped_surface_ok`.
PED_SURFACES = (1, 2, 3, 5)
PED_ROAD_SURFACES = (0, 5)

#: Distance bands for the fleet's own LOD files.  A car costs about 38,000 triangles at LOD0,
#: 27,000 at LOD1 and 5,700 at LOD2, so the bands are tight: at 45 m a 4.9 m car is under 100 px
#: long in a 1,280 px frame and LOD2's body shell (no wheels, no lamps) is what it should cost.
VEHICLE_LOD_M = (8.0, 35.0)
#: Distance bands for the pedestrian LODs this module derives from the shipped rigged asset.
PED_LOD_M = (8.0, 30.0)
#: Decimate ratios for those two derived levels, and the meshes each level drops.  The NPC assets
#: ship no LOD of their own (one 35 k-triangle mesh set per body), so a crowd is unaffordable
#: without one; this is an LOD of the shipped asset, not new geometry.  0.25 and 0.05 give about
#: 17,000, 5,000 and 1,400 triangles a person.  Even the nearest level is decimated: a crowd
#: member is never worth the 35,000 triangles the rigged body carries for close-up work, and a
#: single un-decimated figure at 3 m would take a twentieth of the whole scene budget.  The teeth
#: and tongue (7,100 triangles, a fifth of the body) are inside a closed mouth at every level.
PED_LOD_RATIO = (0.50, 0.15, 0.04)
PED_LOD_DROP = (("teeth", "tongue"), ("teeth", "tongue"),
                ("teeth", "tongue", "cornea", "eyeball", "eyelash", "eyebrow"))
#: How the agents' share of the triangle budget is split.  Neither half may eat the other: the
#: first version gave vehicles and people one counter and twenty-one cars took all of it, leaving
#: a frame with traffic and nobody on the pavement.
VEHICLE_BUDGET_SHARE = 0.45
#: ...and neither may the near field eat the far field.  A car in the 8-35 m band costs 27,000
#: triangles and one at 60 m costs 5,700, so nearest-first alone spends everything on the first
#: dozen and leaves an avenue that is full for 60 m and empty for the next 250: measured, 14
#: vehicles reaching 60 m where the same budget reaches 150 m with 50.  At most this share of each
#: half may go to agents inside the coarsest LOD's boundary; the rest is held for the distance.
NEAR_BAND_SHARE = 0.55

#: The simulation's fleet classes (``nycsim::traffic::VehicleClass``) against the exported bodies in
#: ``blender_out/vehicles/``.  Nothing here is invented: every row names the body the fleet table
#: itself publishes for that class, and :func:`audit_vehicle_assets` measures the asset's published
#: dimensions against the class's and reports the deviation, so a substitution cannot hide.
VEHICLE_ASSETS: dict[str, tuple[str, str]] = {
    "sedan": ("camry_black_car", "Toyota Camry XV70, the body the fleet table names; the one Camry "
                                 "livery without a medallion roof light"),
    "taxi": ("camry_taxi_yellow", "yellow medallion Camry with the TAXI_ROOF light, the fleet "
                                  "table's own body"),
    "boro_taxi": ("camry_boro_taxi", "green Street Hail Livery.  The fleet table names a RAV4 for "
                                     "this class and the only green SHL body exported is a Camry, "
                                     "so the livery is right and the body is 0.29 m long and "
                                     "0.24 m tall out"),
    "black_car": ("suburban_black_car", "Chevrolet Suburban, the body the fleet table names"),
    "suv": ("rav4_fhv", "Toyota RAV4 XA50, the body the fleet table names"),
    "nypd": ("explorer_nypd", "Ford Police Interceptor Utility, the body the fleet table names"),
    "fdny_engine": ("seagrave_engine_fdny", "Seagrave Marauder II pumper"),
    "fdny_ladder": ("seagrave_tower_fdny", "Seagrave Aerialscope 75 ft tower ladder"),
    "ambulance": ("ambulance_type1_fdny", "Ford F-450 Type I ambulance"),
    "mta_bus": ("nova_lfs_mta", "40 ft MTA local bus (Nova LFS where the fleet table names a New "
                                "Flyer XD40; both are 40 ft)"),
    "box_truck": ("isuzu_npr_box", "Isuzu NPR box truck"),
    "dsny_truck": ("mack_lr_dsny", "Mack LR rear loader in DSNY livery"),
    "van": ("sprinter_van", "Mercedes-Benz Sprinter, the body the fleet table names"),
    "cyclist": ("citibike_cruiser", "bike-share bicycle"),
    "ebike": ("arrow_ebike", "delivery e-bike"),
    "moped": ("moped_scooter", "Vespa-class scooter"),
    "pedicab": ("pedicab", "licensed three-wheel pedicab"),
    "horse_carriage": ("horse_carriage", "vis-a-vis carriage with horse"),
}
#: How much room the observer needs.  The comparison cameras stand where the photographer stood,
#: and for a Manhattan street view that is often *in the carriageway*: the photograph's own GPS at
#: Fifth Avenue and 42nd lands on the roadbed, and camera.py's clearance search snaps a blocked
#: viewpoint to the nearest paved surface, which is usually the road.  The simulation therefore
#: drives vehicles straight through the eye point -- the first agent render was the inside of a
#: black van.  A person standing in the street is not driven over, so any agent whose body comes
#: within these distances of the eye is not drawn and the count is reported.  The vehicle rule is
#: skipped when the eye stands higher than the vehicle's roof (the Duffy Square camera is 4.6 m up
#: on the TKTS steps and looks over the traffic, which is the whole point of that viewpoint).
#:
#: The pedestrian radius answers a second question as well, and 1.5 m answered only the first.
#: 1.5 m keeps a person from being rendered *inside* the lens, which is a rendering question; it
#: does nothing about a person standing close enough to *be* the picture.  On
#: ``drive_midtown_sixth_ave_45th`` the nearest pedestrian stood at 1 m and the whole frame was one
#: NPC's torso -- no street, no buildings, no Sixth Avenue.  The number now comes from the frame
#: instead: at this set's 1.6 m eye and its 35 mm lens the vertical field is about 38 deg, so the
#: frame is ``2 * d * tan(19 deg) = 0.69 * d`` metres tall, and a 1.8 m person fills all of it at
#: 2.6 m.  3.5 m puts that person at 74 % of frame height -- close, which a street photograph often
#: is, but no longer the entire picture.  It stays a radius rather than a forward wedge because a
#: pedestrian behind the camera is invisible either way and the placement runs before the final view
#: azimuth is known (``render_sheets.py`` derives that after ``build_scene``).
CAMERA_CLEAR_VEHICLE_M = 6.0
CAMERA_CLEAR_PED_M = 3.5
#: What ``CAMERA_CLEAR_PED_M`` is derived from, kept beside it so the number can be re-derived for a
#: different lens rather than re-guessed: (body height, vertical field of view, share of frame height).
CAMERA_CLEAR_PED_BASIS = (1.8, 38.0, 0.74)

#: Where the exported body is not the size the fleet table publishes for that class, with the
#: measured deviation (length, width, height, per cent) and why.  ``audit_vehicle_assets`` measures
#: the same numbers from the catalogue and ``tests/test_agents.py`` asserts both that nothing else
#: deviates by more than 5 % and that these rows still measure what they say -- so neither the
#: fleet table nor a re-exported body can drift without a test failing.
VEHICLE_ASSET_DEVIATIONS: dict[str, tuple[tuple[float, float, float], str]] = {
    "horse_carriage": ((-44.62, -8.33, 0.0),
                       "the fleet table's 6.500 m is the carriage plus the horse; the exported "
                       "body measures 3.600 m"),
    "ebike": ((0.0, -5.71, -38.89),
              "the fleet table's 1.800 m height is a bicycle with a rider on it; the exported body "
              "is the 1.100 m bicycle and carries no rider, which is why this class is not drawn"),
    "cyclist": ((8.57, 1.54, -37.78),
                "same: the fleet table's height includes the rider and the exported body is the "
                "1.120 m bicycle alone"),
    "van": ((0.0, 0.0, 15.67),
            "the fleet table's Sprinter 144 in is the 2.438 m standard roof; the exported body is "
            "the 2.820 m high roof"),
    "moped": ((-4.62, -4.55, -14.93),
              "the fleet table's Vespa GTS 300 is 1.340 m to the top of the screen; the exported "
              "Primavera body is 1.140 m and carries no rider"),
    "boro_taxi": ((6.2, -0.81, -14.24),
                  "the fleet table names a RAV4 for the green Street Hail Livery and the only "
                  "green SHL body exported is a Camry, so the livery is right and the body is one "
                  "class larger in plan and one class lower"),
    "dsny_truck": ((4.79, -0.35, -6.76),
                   "the fleet table's Mack LR rear loader is 9.600 x 3.700 m; the exported body is "
                   "the 10.060 x 3.450 m DSNY configuration"),
    "fdny_ladder": ((-2.34, 0.04, -4.29),
                    "the fleet table's Aerialscope is 12.800 x 3.500 m over the ladder; the "
                    "exported body measures 12.500 x 3.350 m"),
    "box_truck": ((-4.74, -11.25, -8.57),
                  "the fleet table's 16 ft box body is 2.400 x 3.500 m; the exported Isuzu NPR-HD "
                  "body is 2.130 x 3.200 m"),
}

#: Central Park's carriage drives, closed to private motor traffic on 27 June 2018 (NYC DOT /
#: Central Park Conservancy) and to all motor traffic except emergency and park vehicles since.
#: The road graph still models East, West, Terrace and Center Drive as ordinary streets with travel
#: lanes, so the traffic simulation drives commuter traffic round the park -- 52 vehicles inside
#: 320 m of Bethesda Terrace, all of them on Terrace Drive, East Drive or the Bow Bridge path.
#: That is a defect in the road data, and drawing those cars would put a fabrication in the one
#: park frame of the set, so they are refused here and the count is reported.  The four transverse
#: roads (65th, 79th, 85th and 97th) *are* open and are deliberately not matched: the test is the
#: drive's own name inside the park's own boundary, which is 59th Street, 110th Street, Fifth
#: Avenue and Central Park West.
CAR_FREE_PARK_DRIVES = ("EAST DR", "WEST DR", "TERRACE DR", "CENTER DR", "CENTRE DR")
#: The park's four street corners in NYC_TM metres, from their published intersections.
CENTRAL_PARK_TM = ((-2693.3, 7562.9), (-2001.1, 7151.8), (50.6, 10749.5), (-683.5, 11171.6))

#: Classes whose exported body carries no rider.  A bicycle travelling at 6 m/s with nobody on it
#: is a visibly broken object, so these are dropped by default and the count is reported rather
#: than drawn.  ``place_riderless`` turns them back on.
RIDERLESS_CLASSES = ("cyclist", "ebike", "moped", "pedicab")


# --------------------------------------------------------------------------- the snapshot tool


def _adapter_sources() -> list[Path]:
    return sorted(ADAPTER_DIR.glob("Gameplay*.cpp"))


def _core_sources() -> list[Path]:
    out: list[Path] = []
    for sub in ("routing", "traffic", "vehicle"):
        out.extend(sorted((CORE_SRC / sub).glob("*.cpp")))
    return out


def _build_inputs() -> list[Path]:
    return [SNAPSHOT_SRC, *_adapter_sources(), *_core_sources()]


def build_snapshot_tool(*, force: bool = False) -> tuple[Path | None, str]:
    """Compile ``agent_snapshot.cpp`` if it is missing or older than any source it is built from.

    Returns ``(path, note)``; ``(None, reason)`` when the tool cannot be built, which is not fatal
    -- the scene then places no agents and says so.
    """
    srcs = _build_inputs()
    missing = [str(p.relative_to(REPO_ROOT)) for p in srcs if not p.exists()]
    if missing:
        return None, f"sources missing: {', '.join(missing[:4])}"
    if SNAPSHOT_BIN.exists() and not force:
        newest = max(p.stat().st_mtime for p in srcs)
        if SNAPSHOT_BIN.stat().st_mtime >= newest:
            return SNAPSHOT_BIN, "already built"
    SNAPSHOT_BIN.parent.mkdir(parents=True, exist_ok=True)
    # Compile to a private path and move it into place.  A comparison pass runs several render
    # processes at once over disjoint slug lists, and every one of them reaches this function on
    # its first scene; two compilers writing the same output file would leave a truncated binary
    # that fails silently in one of them.  os.replace is atomic on the same filesystem.
    tmp = SNAPSHOT_BIN.with_name(f"{SNAPSHOT_BIN.name}.{os.getpid()}")
    cmd = ["g++", "-std=c++17", "-O2", "-o", str(tmp),
           f"-I{CORE_INCLUDE}", f"-I{ADAPTER_DIR.parent}", *(str(p) for p in srcs)]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
    except FileNotFoundError:
        return None, "no g++ on this machine"
    except subprocess.TimeoutExpired:
        tmp.unlink(missing_ok=True)
        return None, "compile timed out"
    if proc.returncode != 0:
        tmp.unlink(missing_ok=True)
        tail = (proc.stderr or "").strip().splitlines()[-4:]
        return None, "compile failed: " + " | ".join(tail)
    try:
        os.replace(tmp, SNAPSHOT_BIN)
    except OSError as exc:
        tmp.unlink(missing_ok=True)
        return None, f"could not install the compiled tool: {exc}"
    return SNAPSHOT_BIN, "compiled"


@dataclass
class SnapshotRequest:
    """Everything that decides which frame of the simulation this is."""
    x: float
    y: float
    heading_deg: float = 0.0
    hour: int = 8
    dow: int = 0
    seed: int = 20260907
    warmup_s: float = 120.0
    vehicle_radius_m: float = 420.0
    ped_radius_m: float = 220.0
    max_vehicles: int = 2400
    max_peds: int = 3000
    rain_mm_h: float = 0.0
    temperature_c: float = 15.0
    snow_cover: float = 0.0
    headlights: bool = False

    def key(self) -> str:
        h = hashlib.sha1(json.dumps(self.__dict__, sort_keys=True).encode()).hexdigest()[:16]
        return f"{int(round(self.x))}_{int(round(self.y))}_{self.hour}_{self.dow}_{h}"

    def argv(self) -> list[str]:
        a = ["--x", f"{self.x:.3f}", "--y", f"{self.y:.3f}",
             "--heading-deg", f"{self.heading_deg:.2f}", "--hour", str(int(self.hour)),
             "--dow", str(int(self.dow)), "--seed", str(int(self.seed)),
             "--warmup-s", f"{self.warmup_s:.1f}",
             "--vehicle-radius", f"{self.vehicle_radius_m:.1f}",
             "--ped-radius", f"{self.ped_radius_m:.1f}",
             "--max-vehicles", str(int(self.max_vehicles)),
             "--max-peds", str(int(self.max_peds)),
             "--rain-mm-h", f"{self.rain_mm_h:.2f}",
             "--temperature-c", f"{self.temperature_c:.1f}",
             "--snow-cover", f"{self.snow_cover:.2f}", "--quiet"]
        if self.headlights:
            a.append("--headlights")
        return a


def simulation_snapshot(req: SnapshotRequest, *, use_cache: bool = True) -> tuple[dict | None, str]:
    """Run (or read from cache) one frame of the simulation around ``req``.

    The simulation is deterministic in its seed and inputs, so the cache is a speed-up and never a
    different answer; the cache key covers every argument and the tool's own mtime.
    """
    if not RUNTIME_DIR.is_dir():
        return None, f"no runtime container directory at {RUNTIME_DIR}"
    need = ["roadgraph.nycb", "signals.nycb", "density.nycb"]
    absent = [n for n in need if not (RUNTIME_DIR / n).exists()]
    if absent:
        return None, f"runtime container(s) missing: {', '.join(absent)}"
    tool, note = build_snapshot_tool()
    if tool is None:
        return None, f"agent_snapshot tool unavailable ({note})"
    cache = SNAPSHOT_CACHE / f"{req.key()}_{int(tool.stat().st_mtime)}.json"
    if use_cache and cache.exists():
        try:
            return json.loads(cache.read_text()), f"cached {cache.name}"
        except Exception:
            pass
    SNAPSHOT_CACHE.mkdir(parents=True, exist_ok=True)
    tmp = cache.with_name(f"{cache.name}.{os.getpid()}")
    cmd = [str(tool), "--runtime", str(RUNTIME_DIR), "--out", str(tmp), *req.argv()]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=1800, cwd=str(REPO_ROOT))
    except subprocess.TimeoutExpired:
        tmp.unlink(missing_ok=True)
        return None, "agent_snapshot timed out"
    if proc.returncode != 0:
        tmp.unlink(missing_ok=True)
        return None, "agent_snapshot failed: " + (proc.stderr or "").strip()[-200:]
    try:
        snap = json.loads(tmp.read_text())
    except Exception as exc:
        tmp.unlink(missing_ok=True)
        return None, f"agent_snapshot wrote unreadable JSON: {exc}"
    try:
        os.replace(tmp, cache)          # same reason as the compile above
    except OSError:
        tmp.unlink(missing_ok=True)
    return snap, f"simulated ({note})"


# --------------------------------------------------------------------------- surfaces


def _tiles_in_radius(cx: float, cy: float, radius_m: float) -> list[tuple[int, int]]:
    out = []
    for tx in range(int(math.floor((cx - radius_m) / TILE_SIZE_M)),
                    int(math.floor((cx + radius_m) / TILE_SIZE_M)) + 1):
        for ty in range(int(math.floor((cy - radius_m) / TILE_SIZE_M)),
                        int(math.floor((cy + radius_m) / TILE_SIZE_M)) + 1):
            out.append((tx, ty))
    return out


class Surfaces:
    """Which paved surface, if any, is under a point -- and whether it is inside a building.

    Both answers come from the same data the scene is drawn from: the DoITT pavement polygons
    ``scene.add_pavement`` drapes over the terrain, and the real footprints in
    ``data/processed/tiles/{tile}/buildings.parquet``.
    """

    def __init__(self, cx: float, cy: float, radius_m: float) -> None:
        self.ok = False
        self.reason = ""
        self.pavement_polygons = 0
        self.footprints = 0
        try:
            import pyarrow.parquet as pq
            import shapely
            from shapely import STRtree
        except Exception as exc:  # pragma: no cover - environment without shapely
            self.reason = f"pyarrow/shapely unavailable: {exc}"
            return
        self._shapely = shapely
        geoms, kinds = [], []
        for tx, ty in _tiles_in_radius(cx, cy, radius_m):
            p = PAVEMENT_DIR / f"t_{tx}_{ty}.parquet"
            if not p.exists():
                continue
            try:
                t = pq.read_table(p, columns=["kind", "geometry"])
            except Exception as exc:
                LOG.warning("pavement tile t_%d_%d unreadable: %s", tx, ty, exc)
                continue
            for k, blob in zip(t.column("kind").to_pylist(), t.column("geometry").to_pylist()):
                try:
                    g = shapely.from_wkb(blob)
                except Exception:
                    continue
                geoms.append(g)
                kinds.append(int(k))
        self._pave = geoms
        self._kind = kinds
        self.pavement_polygons = len(geoms)
        self._pave_tree = STRtree(geoms) if geoms else None

        foot = []
        for tx, ty in _tiles_in_radius(cx, cy, radius_m):
            p = TILES_DATA / f"t_{tx}_{ty}" / "buildings.parquet"
            if not p.exists():
                continue
            try:
                t = pq.read_table(p, columns=["footprint"])
            except Exception:
                continue
            for blob in t.column("footprint").to_pylist():
                try:
                    foot.append(shapely.from_wkb(blob))
                except Exception:
                    continue
        self._foot = foot
        self.footprints = len(foot)
        self._foot_tree = STRtree(foot) if foot else None
        self.ok = True

    def surface_at(self, x: float, y: float) -> int | None:
        """The pavement kind under ``(x, y)``, preferring the most specific surface, or None."""
        if self._pave_tree is None:
            return None
        pt = self._shapely.Point(x, y)
        hits = self._pave_tree.query(pt, predicate="intersects")
        found = {self._kind[int(i)] for i in np.atleast_1d(hits)}
        if not found:
            return None
        for pref in (5, 1, 3, 2, 0, 6, 4):
            if pref in found:
                return pref
        return None

    def inside_building(self, x: float, y: float) -> bool:
        if self._foot_tree is None:
            return False
        pt = self._shapely.Point(x, y)
        return bool(len(np.atleast_1d(self._foot_tree.query(pt, predicate="intersects"))))


class CarFreeDrives:
    """Segments a vehicle must not be drawn on, however drivable the road graph thinks they are.

    Built only when the scene reaches into a park whose drives are closed to traffic, so an
    ordinary street scene pays nothing for it.
    """

    def __init__(self, cx: float, cy: float, radius_m: float) -> None:
        self.active = False
        self.matched = 0
        self._names: list[str] = []
        try:
            import pyarrow.parquet as pq
            import shapely
            from shapely import STRtree
        except Exception:
            return
        park = shapely.Polygon(CENTRAL_PARK_TM)
        if not park.buffer(float(radius_m)).contains(shapely.Point(cx, cy)):
            return
        seg_p = PROCESSED / "roads" / "segments.parquet"
        if not seg_p.exists():
            return
        try:
            t = pq.read_table(seg_p, columns=["street_name", "geometry"])
        except Exception:
            return
        geoms = shapely.from_wkb(t.column("geometry").to_pylist())
        names = t.column("street_name").to_pylist()
        minx, miny, maxx, maxy = shapely.bounds(geoms).T
        pad = float(radius_m) + 60.0
        keep = []
        for i in np.where((minx < cx + pad) & (maxx > cx - pad)
                          & (miny < cy + pad) & (maxy > cy - pad))[0]:
            nm = (names[int(i)] or "").strip().upper()
            if nm in CAR_FREE_PARK_DRIVES and park.intersects(geoms[int(i)]):
                keep.append(geoms[int(i)])
        if not keep:
            return
        self._shapely = shapely
        self._tree = STRtree(keep)
        self._geoms = keep
        self.active = True

    def forbids(self, x: float, y: float) -> bool:
        """Is this point on one of those drives?  A lane is at most a carriageway half-width away."""
        if not self.active:
            return False
        hit = self._tree.query(self._shapely.Point(x, y), predicate="dwithin", distance=9.0)
        if len(np.atleast_1d(hit)):
            self.matched += 1
            return True
        return False


def _ped_surface_ok(kind: int | None, state: int, flags: int) -> bool:
    """A walker may stand on a walking surface; it may stand in the road only while crossing."""
    if kind is None:
        return False
    if kind in PED_SURFACES:
        return True
    # PedState: 0 Walking, 1 WaitingToCross, 2 Crossing, 3 Idle.  kPedJaywalking = 1 << 4.
    in_road = state == 2 or (flags & (1 << 4)) != 0
    return in_road and kind in PED_ROAD_SURFACES


# --------------------------------------------------------------------------- asset audit


def _vehicle_catalog(asset_id: str) -> dict | None:
    p = VEHICLE_CATALOG / f"{asset_id}.json"
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text())
    except Exception:
        return None


def audit_vehicle_assets(classes: list[dict] | None = None) -> dict:
    """Measure every mapped body against the dimensions its simulation class publishes.

    ``classes`` is the ``vehicle_classes`` block of a snapshot (the fleet table's own published
    length/width/height per class).  Without one the audit only checks that each asset and its
    LOD files are on disk.
    """
    by_name = {c["name"]: c for c in (classes or [])}
    rows, worst = [], 0.0
    missing = []
    for cls, (asset_id, why) in sorted(VEHICLE_ASSETS.items()):
        cat = _vehicle_catalog(asset_id)
        row: dict = {"class": cls, "asset": asset_id, "reason": why}
        if cat is None:
            row["error"] = f"no catalogue entry {asset_id}.json"
            missing.append(asset_id)
            rows.append(row)
            continue
        files = [VEHICLE_DIR / f"{asset_id}.glb", VEHICLE_DIR / f"{asset_id}_LOD1.glb",
                 VEHICLE_DIR / f"{asset_id}_LOD2.glb"]
        absent = [f.name for f in files if not f.exists()]
        if absent:
            row["error"] = f"missing glb: {', '.join(absent)}"
            missing.append(asset_id)
        pub = cat.get("published_dimensions_mm") or {}
        row["asset_lwh_m"] = [round(pub.get("length_mm", 0) / 1000.0, 3),
                              round(pub.get("width_mm", 0) / 1000.0, 3),
                              round(pub.get("height_mm", 0) / 1000.0, 3)]
        row["triangles"] = [lod.get("triangles") for lod in cat.get("lods", [])]
        c = by_name.get(cls)
        if c is not None:
            row["class_lwh_m"] = [round(c["length_m"], 3), round(c["width_m"], 3),
                                  round(c["height_m"], 3)]
            dev = []
            for a, b in zip(row["asset_lwh_m"], row["class_lwh_m"]):
                dev.append(0.0 if b == 0 else round(100.0 * (a - b) / b, 2))
            row["deviation_pct"] = dev
            worst = max(worst, max(abs(d) for d in dev))
        rows.append(row)
    return {"rows": rows, "worst_abs_deviation_pct": round(worst, 2),
            "assets_missing": sorted(set(missing)),
            "classes_mapped": len(VEHICLE_ASSETS),
            "classes_in_snapshot": len(by_name)}


_VEHICLE_LOD_TRIS: dict[tuple[str, int], int] = {}


def vehicle_lod_triangles(asset_id: str, lod: int) -> int:
    """Triangles the fleet catalogue publishes for one body at one LOD.

    Read from ``blender_out/vehicles/catalog/<id>.json`` rather than measured after import, so the
    triangle budget can be spent before anything is loaded.  The measured count replaces it once
    the template exists (:func:`add_agents` phase C).
    """
    key = (asset_id, int(lod))
    if key in _VEHICLE_LOD_TRIS:
        return _VEHICLE_LOD_TRIS[key]
    cat = _vehicle_catalog(asset_id) or {}
    n = 0
    for entry in cat.get("lods", []):
        if int(entry.get("level", -1)) == int(lod):
            n = int(entry.get("triangles") or 0)
            break
    if n == 0:
        n = int(cat.get("triangles") or 40_000)
    _VEHICLE_LOD_TRIS[key] = n
    return n


_NPC_POLYGONS: dict[int, dict[str, int]] | None = None


def _npc_polygons() -> dict[int, dict[str, int]]:
    """Per-mesh polygon counts from ``npc_variety.json``, indexed by archetype."""
    global _NPC_POLYGONS
    if _NPC_POLYGONS is not None:
        return _NPC_POLYGONS
    out: dict[int, dict[str, int]] = {}
    if NPC_VARIETY.exists():
        try:
            v = json.loads(NPC_VARIETY.read_text())
            for entry in v.get("npcs", []):
                out[int(entry.get("index", 0))] = {k: int(n) for k, n in
                                                   (entry.get("meshes") or {}).items()}
        except Exception:
            out = {}
    _NPC_POLYGONS = out
    return out


def npc_archetype_assets() -> list[Path]:
    """Every baked NPC body, indexed by ``PedSnapshot.archetype``.

    The count is whatever ``npc_variety.json`` published, never a literal.  It was a literal 24
    until the cast grew to 36 and twelve coats became unrenderable (docs/DEVIATIONS.md J62).
    """
    if not NPC_VARIETY.exists():
        return sorted(NPC_DIR.glob("npc_*.glb"))
    try:
        v = json.loads(NPC_VARIETY.read_text())
    except Exception:
        return sorted(NPC_DIR.glob("npc_*.glb"))
    out: list[Path] = []
    for entry in sorted(v.get("npcs", []), key=lambda e: e.get("index", 0)):
        out.append(NPC_DIR / f"{entry['id']}.glb")
    return out


# --------------------------------------------------------------------------- placement


@dataclass
class AgentPlacement:
    """What went into the frame and what did not, in the shape ``render.json`` records."""
    placed_vehicles: int = 0
    placed_pedestrians: int = 0
    triangles: int = 0
    triangle_budget: int = 0
    vehicle_triangles: int = 0
    pedestrian_triangles: int = 0
    vehicle_triangle_budget: int = 0
    pedestrian_triangle_budget: int = 0
    vehicle_radius_m: float = 0.0
    ped_radius_m: float = 0.0
    vehicle_lods: dict[str, int] = field(default_factory=dict)
    ped_lods: dict[str, int] = field(default_factory=dict)
    per_class: dict[str, int] = field(default_factory=dict)
    dropped: dict[str, int] = field(default_factory=dict)
    snapshot: dict = field(default_factory=dict)
    reason: str | None = None
    seconds: float = 0.0

    def as_dict(self) -> dict:
        return {"placed_vehicles": self.placed_vehicles,
                "placed_pedestrians": self.placed_pedestrians,
                "triangles": self.triangles, "triangle_budget": self.triangle_budget,
                "vehicle_triangles": self.vehicle_triangles,
                "pedestrian_triangles": self.pedestrian_triangles,
                "vehicle_triangle_budget": self.vehicle_triangle_budget,
                "pedestrian_triangle_budget": self.pedestrian_triangle_budget,
                "vehicle_radius_m": self.vehicle_radius_m, "ped_radius_m": self.ped_radius_m,
                "vehicle_lods": self.vehicle_lods, "ped_lods": self.ped_lods,
                "per_class": dict(sorted(self.per_class.items(), key=lambda kv: -kv[1])),
                "dropped": {k: v for k, v in sorted(self.dropped.items()) if v},
                "snapshot": self.snapshot, "reason": self.reason,
                "seconds": round(self.seconds, 2)}

    def caption(self) -> str:
        """One line for the sheet.  It must never read as the photograph's own traffic."""
        if self.reason and not (self.placed_vehicles or self.placed_pedestrians):
            return f"Agents: none placed - {self.reason}"
        s = self.snapshot or {}
        bits = [f"{self.placed_vehicles} vehicles within {self.vehicle_radius_m:.0f} m and "
                f"{self.placed_pedestrians} people within {self.ped_radius_m:.0f} m, from one "
                f"frame of the traffic and pedestrian simulations"]
        if s.get("clock"):
            bits.append(f"at {s['clock']}")
        if s.get("seed") is not None:
            bits.append(f"seed {s['seed']}")
        if s.get("sim_seconds"):
            bits.append(f"after {s['sim_seconds']:.0f} s of simulated time")
        head = ", ".join(bits)
        tail = ""
        tgt = s.get("density_target_vehicles")
        if tgt:
            tail = (f"; the density table asks for {tgt:.0f} vehicles and "
                    f"{s.get('density_target_pedestrians', 0):.0f} people over the whole "
                    f"simulated ring, of which {s.get('vehicles_in_snapshot', 0)} and "
                    f"{s.get('peds_in_snapshot', 0)} were simulated")
        drop = sum(self.dropped.values())
        if drop:
            tail += f"; {drop} dropped (see render.json)"
        return (f"Agents: {head}{tail}.  This is the simulation's own traffic and crowd for that "
                f"hour and neighbourhood, not the people and vehicles in the photograph.")


def _decimate_mesh(mesh, ratio: float, name: str):
    """Return a decimated copy of ``mesh``.  Material slots and indices survive the modifier."""
    import bpy
    if ratio >= 1.0:
        return mesh
    tmp_ob = bpy.data.objects.new(f"_dec_{name}", mesh)
    bpy.context.scene.collection.objects.link(tmp_ob)
    md = tmp_ob.modifiers.new("decimate", "DECIMATE")
    md.decimate_type = "COLLAPSE"
    md.ratio = float(ratio)
    dg = bpy.context.evaluated_depsgraph_get()
    out = bpy.data.meshes.new_from_object(tmp_ob.evaluated_get(dg), depsgraph=dg)
    bpy.data.objects.remove(tmp_ob, do_unlink=True)
    return out


class PedLibrary:
    """Baked, instanceable pedestrian templates derived from the shipped rigged NPC bodies.

    ``blender_out/character/npc/*.glb`` are rigged characters with 25 animation clips and no LOD.
    A still frame needs neither a rig nor a clip: it needs the mesh *in a pose*.  So for each
    (archetype, pose phase, LOD) actually asked for, the armature is put on the walk or idle clip
    at that phase, the skinned result is evaluated once, and the evaluated mesh is kept as a static
    datablock that every pedestrian of that combination instances.  The two coarser levels are the
    same mesh through a collapse decimator, because 35,000 triangles a person is unaffordable for a
    crowd and the assets ship no LOD of their own.  No geometry is authored here.
    """

    def __init__(self, *, archetypes: int | None = None, phases: int = 3) -> None:
        self._paths = npc_archetype_assets()
        # The cast is however many bodies were baked, not a number written here.  This clamp read
        # ``min(24, ...)`` while the wardrobe baked 36, so archetypes 24 to 35 -- every trench
        # coat, wool coat, puffer, leather, denim and field jacket the J53 fix added -- folded onto
        # bodies 0 to 11 and could not appear in any comparison render, while those twelve bodies
        # were drawn at twice the rate of the rest.  The simulation emits all 36: 989 of the 2,999
        # people in the Broadway/Wall St snapshot carry one of the twelve (docs/DEVIATIONS.md J62).
        available = len(self._paths) or 1
        want = available if archetypes is None else int(archetypes)
        self.archetypes = max(1, min(available, want))
        self.phases = max(1, int(phases))
        self._sources: dict[int, dict] = {}
        self._templates: dict[tuple[int, str, int, int], object] = {}
        self.failed: dict[str, str] = {}
        #: Archetypes the snapshot asked for that this library has no body for.  A fold is a
        #: silent substitution of one person for another, so it is counted and published rather
        #: than left to be discovered in a rendered frame.
        self.folded: dict[int, int] = {}
        self.imported = 0
        self.baked = 0

    def body_for(self, arch: int) -> int:
        """The body index used for snapshot archetype ``arch``, counting any substitution.

        Call this once per *placed* person.  ``built`` and ``template`` take an index this has
        already returned, so folding again there would count one person several times.
        """
        arch = int(arch)
        if arch >= self.archetypes or arch < 0:
            self.folded[arch] = self.folded.get(arch, 0) + 1
        return arch % self.archetypes

    def estimate(self, arch: int, lod: int) -> int:
        """Triangles one baked template will cost, before it is built.

        ``npc_variety.json`` publishes each body's per-mesh polygon count; the bodies are quad
        meshes, so triangles are twice that, and the decimator hits its ratio to within a few per
        cent.  Only an estimate is available at budget time because the pose has to be evaluated
        before the real count exists.
        """
        arch = int(arch) % self.archetypes
        lod = max(0, min(2, int(lod)))
        meshes = _npc_polygons().get(arch)
        if not meshes:
            return int(35_000 * PED_LOD_RATIO[lod])
        drop = PED_LOD_DROP[lod]
        polys = sum(n for name, n in meshes.items() if not any(d in name.lower() for d in drop))
        return int(2 * polys * PED_LOD_RATIO[lod])

    def built(self, arch: int, clip: str, phase: int, lod: int):
        """The template :meth:`template` made for this combination, or None."""
        key = (int(arch) % self.archetypes, clip, int(phase) % self.phases,
               max(0, min(2, int(lod))))
        return self._templates.get(key)

    def _source(self, arch: int):
        import bpy
        if arch in self._sources:
            return self._sources[arch]
        if arch >= len(self._paths) or not self._paths[arch].exists():
            self.failed[f"archetype {arch}"] = "no glb on disk"
            self._sources[arch] = None
            return None
        before = set(bpy.data.objects)
        try:
            bpy.ops.import_scene.gltf(filepath=str(self._paths[arch]))
        except Exception as exc:
            self.failed[f"archetype {arch}"] = f"import failed: {exc}"
            self._sources[arch] = None
            return None
        created = [ob for ob in bpy.data.objects if ob not in before]
        arms = [ob for ob in created if ob.type == "ARMATURE"]
        if not arms:
            for ob in created:
                bpy.data.objects.remove(ob, do_unlink=True)
            self.failed[f"archetype {arch}"] = "glb carries no armature"
            self._sources[arch] = None
            return None
        arm = arms[0]
        # Only the meshes this armature actually skins: the export also carries a helper
        # icosphere that is not part of the body and must not be drawn.
        meshes = [ob for ob in created if ob.type == "MESH"
                  and any(m.type == "ARMATURE" and m.object is arm for m in ob.modifiers)]
        if not meshes:
            for ob in created:
                bpy.data.objects.remove(ob, do_unlink=True)
            self.failed[f"archetype {arch}"] = "glb carries no skinned mesh"
            self._sources[arch] = None
            return None
        if arm.animation_data is None:
            arm.animation_data_create()
        self.imported += 1
        got = {"arm": arm, "meshes": meshes, "created": created}
        self._sources[arch] = got
        return got

    def template(self, arch: int, clip: str, phase: int, lod: int, *,
                 _phase_is_index: bool = False):
        """A ``(parts, triangles, z_lift)`` template, built on demand."""
        import bpy
        from mathutils import Matrix
        arch = int(arch) % self.archetypes
        phase = int(phase) if _phase_is_index else int(phase) % self.phases
        phase = phase % self.phases
        lod = max(0, min(2, int(lod)))
        key = (arch, clip, phase, lod)
        if key in self._templates:
            return self._templates[key]
        src = self._source(arch)
        if src is None:
            self._templates[key] = None
            return None
        arm = src["arm"]
        act = bpy.data.actions.get(clip)
        if act is None:
            act = next((a for a in bpy.data.actions if a.name == clip), None)
        if act is not None:
            arm.animation_data.action = act
            f0, f1 = act.frame_range
            fr = float(f0) + (float(f1) - float(f0)) * (phase / float(self.phases))
            bpy.context.scene.frame_set(int(math.floor(fr)), subframe=float(fr - math.floor(fr)))
        bpy.context.view_layer.update()
        dg = bpy.context.evaluated_depsgraph_get()
        drop = PED_LOD_DROP[lod]
        parts, tris, min_z = [], 0, 1e9
        for ob in src["meshes"]:
            low = ob.name.lower()
            if any(d in low for d in drop):
                continue
            me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg), depsgraph=dg)
            me.transform(ob.matrix_world)
            me = _decimate_mesh(me, PED_LOD_RATIO[lod], f"{arch}_{lod}")
            if len(me.polygons) == 0:
                continue
            co = np.empty(len(me.vertices) * 3, dtype=np.float64)
            me.vertices.foreach_get("co", co)
            min_z = min(min_z, float(co.reshape(-1, 3)[:, 2].min()))
            tris += sum(len(p.vertices) - 2 for p in me.polygons)
            parts.append((me, Matrix.Identity(4)))
        if not parts:
            self._templates[key] = None
            return None
        self.baked += 1
        # A mid-stride pose can put the swing foot a few centimetres under the origin plane; lift
        # the template so the planted foot sits on the pavement rather than in it.
        lift = -min_z if min_z < 0.0 else 0.0
        tpl = (parts, tris, lift)
        self._templates[key] = tpl
        return tpl

    def build_many(self, needed: "dict[int, set]") -> None:
        """Bake every template asked for, one archetype at a time.

        One archetype is imported, every pose and level it needs is baked, and it is removed again
        before the next is imported.  That ordering is what makes this affordable: posing a rigged
        body means moving the scene's frame, which re-evaluates *every* animated object in the
        scene, so leaving all 24 bodies loaded made each bake cost about 1.5 s instead of 0.1 s.
        """
        for arch in sorted(needed):
            if self._source(arch) is None:
                continue
            for clip, phase, lod in sorted(needed[arch]):
                self.template(arch, clip, phase, lod, _phase_is_index=True)
            self.release_source(arch)

    def release_source(self, arch: int) -> None:
        import bpy
        got = self._sources.pop(arch, None)
        if not got:
            return
        for ob in got["created"]:
            try:
                bpy.data.objects.remove(ob, do_unlink=True)
            except Exception:
                pass

    def release_sources(self) -> None:
        """Drop the rigged imports once every template is baked."""
        import bpy
        for got in self._sources.values():
            if not got:
                continue
            for ob in got["created"]:
                try:
                    bpy.data.objects.remove(ob, do_unlink=True)
                except Exception:
                    pass
        self._sources.clear()


def _instance(parts, name: str, matrix, col) -> None:
    import bpy
    for k, (mesh, local) in enumerate(parts):
        ob = bpy.data.objects.new(f"{name}.{k}" if len(parts) > 1 else name, mesh)
        ob.matrix_world = matrix @ local
        col.objects.link(ob)


def add_agents(lib, cx: float, cy: float, snapshot: dict, sampler, *,
               vehicle_radius_m: float = 320.0, ped_radius_m: float = 200.0,
               triangle_budget: int = 900_000, max_vehicles: int = 400, max_peds: int = 900,
               npc_archetypes: int | None = None, ped_phases: int = 3,
               place_riderless: bool = False,
               camera_eye_height_m: float = 1.6, col=None) -> AgentPlacement:
    """Place one simulation frame's vehicles and pedestrians, nearest to the camera first.

    ``lib`` is the scene's :class:`scene.AssetLibrary` so the fleet glbs are imported once and
    every placement is a linked instance of the same mesh datablocks.  ``sampler`` is the scene's
    :class:`scene.TerrainSampler`: an agent's height comes from the same heightmap the pavement is
    draped on, plus that surface's own lift, so a car sits on the asphalt the render actually
    draws and not on the bare terrain 0.10 m below it.

    The work is in three phases -- decide, build, instance -- and the order is not cosmetic.
    Evaluating a posed character costs a depsgraph pass over everything already in the scene, so
    baking templates *while* instancing made the pedestrian pass take 264 s instead of 21 s.  The
    triangle budget is therefore spent against the counts the fleet catalogue and the NPC variety
    file publish, and reconciled against the measured counts once the templates exist.
    """
    import time
    import bpy
    from mathutils import Euler, Matrix
    t0 = time.time()
    rep = AgentPlacement(triangle_budget=int(triangle_budget))
    col = col or bpy.context.scene.collection
    if not snapshot:
        rep.reason = "no simulation snapshot"
        return rep

    classes = snapshot.get("vehicle_classes") or []
    cls_name = {int(c["index"]): c["name"] for c in classes}
    cls_height = {c["name"]: float(c.get("height_m") or 1.6) for c in classes}
    st = snapshot.get("traffic_stats") or {}
    ps = snapshot.get("ped_stats") or {}
    dt = snapshot.get("density_target") or {}
    rep.snapshot = {
        "produced_by": snapshot.get("produced_by"),
        "records": snapshot.get("snapshot_records"),
        "runtime_dir": snapshot.get("runtime_dir"),
        "synthetic_network": snapshot.get("synthetic_network"),
        "network": snapshot.get("network"),
        "seed": snapshot.get("seed"), "hour": snapshot.get("hour"), "dow": snapshot.get("dow"),
        "sim_seconds": snapshot.get("sim_seconds"),
        "vehicles_in_snapshot": snapshot.get("vehicle_count"),
        "peds_in_snapshot": snapshot.get("ped_count"),
        "density_target_vehicles": dt.get("vehicles"),
        "density_target_pedestrians": dt.get("pedestrians"),
        "density_lane_km": dt.get("lane_km"), "density_sidewalk_m2": dt.get("sidewalk_m2"),
        "lanes_with_nta": dt.get("lanes_with_nta"), "lanes_considered": dt.get("lanes"),
        "red_light_entries": st.get("red_light_entries"),
        "min_leader_gap_m": st.get("min_leader_gap_m"),
        "unsafe_crossing_starts": ps.get("unsafe_crossing_starts"),
        "vehicle_spawn_radius_m": (snapshot.get("config") or {}).get("vehicle_spawn_radius_m"),
        "ped_spawn_radius_m": (snapshot.get("config") or {}).get("ped_spawn_radius_m"),
        "protected_region": (snapshot.get("config") or {}).get("protected_region"),
    }

    surf = Surfaces(cx, cy, max(vehicle_radius_m, ped_radius_m) + 30.0)
    if not surf.ok:
        rep.reason = f"paved surfaces unavailable: {surf.reason}"
        return rep
    car_free = CarFreeDrives(cx, cy, vehicle_radius_m)
    rep.snapshot["pavement_polygons_tested"] = surf.pavement_polygons
    rep.snapshot["building_footprints_tested"] = surf.footprints

    def ground(x: float, y: float) -> float | None:
        z, _ = sampler.grid(np.array([[float(x)]]), np.array([[float(y)]]))
        v = float(z[0, 0])
        return None if math.isnan(v) else v

    drop = rep.dropped
    veh_budget = int(triangle_budget * VEHICLE_BUDGET_SHARE)
    ped_budget = int(triangle_budget) - veh_budget
    rep.vehicle_triangle_budget = veh_budget
    rep.pedestrian_triangle_budget = ped_budget
    rep.vehicle_radius_m = float(vehicle_radius_m)
    rep.ped_radius_m = float(ped_radius_m)

    # ------------------------------------------------------- phase A: decide, vehicles
    # The surface and footprint tests come *before* the caps, so the counts they report are the
    # simulation's real agreement with the planimetric data and not an artefact of where the
    # budget ran out.
    veh_plan: list[tuple[str, int, object, str, int]] = []
    est = est_near = 0
    for dist, v in sorted(((math.hypot(v["x"] - cx, v["y"] - cy), v)
                           for v in (snapshot.get("vehicles") or [])), key=lambda q: q[0]):
        if dist > vehicle_radius_m:
            drop["vehicle_outside_radius"] = drop.get("vehicle_outside_radius", 0) + 1
            continue
        name = cls_name.get(int(v["cls"]), "")
        if not place_riderless and name in RIDERLESS_CLASSES:
            drop["vehicle_body_has_no_rider"] = drop.get("vehicle_body_has_no_rider", 0) + 1
            continue
        height = cls_height.get(name, 1.6)
        if (camera_eye_height_m <= height + 0.5
                and vehicle_body_clearance(v, cx, cy) < CAMERA_CLEAR_VEHICLE_M):
            drop["vehicle_over_the_observer"] = drop.get("vehicle_over_the_observer", 0) + 1
            continue
        if car_free.forbids(v["x"], v["y"]):
            drop["vehicle_on_a_car_free_park_drive"] = (
                drop.get("vehicle_on_a_car_free_park_drive", 0) + 1)
            continue
        kind = surf.surface_at(v["x"], v["y"])
        if kind not in VEHICLE_SURFACES:
            drop["vehicle_not_on_carriageway"] = drop.get("vehicle_not_on_carriageway", 0) + 1
            continue
        if surf.inside_building(v["x"], v["y"]):
            drop["vehicle_inside_building"] = drop.get("vehicle_inside_building", 0) + 1
            continue
        mapping = VEHICLE_ASSETS.get(name)
        if mapping is None:
            drop["vehicle_class_unmapped"] = drop.get("vehicle_class_unmapped", 0) + 1
            continue
        if len(veh_plan) >= max_vehicles:
            drop["vehicle_instance_cap"] = drop.get("vehicle_instance_cap", 0) + 1
            continue
        lod = 0 if dist < VEHICLE_LOD_M[0] else (1 if dist < VEHICLE_LOD_M[1] else 2)
        cost = vehicle_lod_triangles(mapping[0], lod)
        if lod < 2 and est_near + cost > veh_budget * NEAR_BAND_SHARE and veh_plan:
            drop["vehicle_triangle_budget"] = drop.get("vehicle_triangle_budget", 0) + 1
            continue
        if est + cost > veh_budget and veh_plan:
            drop["vehicle_triangle_budget"] = drop.get("vehicle_triangle_budget", 0) + 1
            continue
        gz = ground(v["x"], v["y"])
        if gz is None:
            drop["vehicle_no_terrain"] = drop.get("vehicle_no_terrain", 0) + 1
            continue
        m = (Matrix.Translation((float(v["x"]), float(v["y"]), float(gz + PAVEMENT_LIFT_M[kind])))
             @ Euler((0.0, 0.0, float(v["heading_rad"]))).to_matrix().to_4x4())
        veh_plan.append((mapping[0], lod, m, name, int(v["id"])))
        est += cost
        if lod < 2:
            est_near += cost

    # --------------------------------------------------- phase A: decide, pedestrians
    peds = PedLibrary(archetypes=npc_archetypes, phases=ped_phases)
    ped_plan: list[tuple[int, str, int, int, object]] = []
    est_p = est_p_near = 0
    for dist, p in sorted(((math.hypot(p["x"] - cx, p["y"] - cy), p)
                           for p in (snapshot.get("pedestrians") or [])), key=lambda q: q[0]):
        if dist > ped_radius_m:
            drop["pedestrian_outside_radius"] = drop.get("pedestrian_outside_radius", 0) + 1
            continue
        if dist < CAMERA_CLEAR_PED_M:
            drop["pedestrian_over_the_observer"] = drop.get("pedestrian_over_the_observer", 0) + 1
            continue
        state = int(p.get("state", 0))
        flags = int(p.get("flags", 0))
        kind = surf.surface_at(p["x"], p["y"])
        if not _ped_surface_ok(kind, state, flags):
            key = ("pedestrian_not_on_walkable_surface" if kind is None or kind not in (0, 4, 6)
                   else "pedestrian_in_the_carriageway_not_crossing")
            drop[key] = drop.get(key, 0) + 1
            continue
        if surf.inside_building(p["x"], p["y"]):
            drop["pedestrian_inside_building"] = drop.get("pedestrian_inside_building", 0) + 1
            continue
        if len(ped_plan) >= max_peds:
            drop["pedestrian_instance_cap"] = drop.get("pedestrian_instance_cap", 0) + 1
            continue
        arch = peds.body_for(p.get("archetype", 0))
        lod = 0 if dist < PED_LOD_M[0] else (1 if dist < PED_LOD_M[1] else 2)
        cost = peds.estimate(arch, lod)
        if lod < 2 and est_p_near + cost > ped_budget * NEAR_BAND_SHARE and ped_plan:
            drop["pedestrian_triangle_budget"] = drop.get("pedestrian_triangle_budget", 0) + 1
            continue
        if est_p + cost > ped_budget and ped_plan:
            drop["pedestrian_triangle_budget"] = drop.get("pedestrian_triangle_budget", 0) + 1
            continue
        gz = ground(p["x"], p["y"])
        if gz is None:
            drop["pedestrian_no_terrain"] = drop.get("pedestrian_no_terrain", 0) + 1
            continue
        # A standing walker gets the idle clip, a moving one the walk clip; the phase is drawn
        # from the agent's own id so a crowd is not in lockstep.
        clip = "idle" if (state in (1, 3) or float(p.get("speed_mps", 0.0)) < 0.25) else "walk"
        # Every character body is authored facing -Y (blender_out/character/catalog/player.json
        # "forward_axis_blender"), so a walker heading along ``heading_rad`` is yawed a quarter
        # turn past it.
        yaw = float(p["heading_rad"]) + math.pi / 2.0
        m = (Matrix.Translation((float(p["x"]), float(p["y"]),
                                 float(gz + PAVEMENT_LIFT_M[kind])))
             @ Euler((0.0, 0.0, yaw)).to_matrix().to_4x4())
        ped_plan.append((arch, clip, int(p["id"]), lod, m))
        est_p += cost
        if lod < 2:
            est_p_near += cost

    # --------------------------------------------------------- phase B: build templates
    veh_tpl: dict[tuple[str, int], object] = {}
    for asset_id, lod, _m, _name, _id in veh_plan:
        if (asset_id, lod) in veh_tpl:
            continue
        suffix = "" if lod == 0 else f"_LOD{lod}"
        tpl = lib.get(VEHICLE_DIR / f"{asset_id}{suffix}.glb", key=f"veh:{asset_id}:{lod}",
                      max_lod=0, keep=_keep_vehicle_part)
        if tpl is None and lod != 2:
            tpl = lib.get(VEHICLE_DIR / f"{asset_id}_LOD2.glb", key=f"veh:{asset_id}:2",
                          max_lod=0, keep=_keep_vehicle_part)
        veh_tpl[(asset_id, lod)] = tpl
    needed: dict[int, set] = {}
    for arch, clip, pid, lod, _m in ped_plan:
        needed.setdefault(arch, set()).add((clip, int(pid) % peds.phases, lod))
    peds.build_many(needed)

    # ------------------------------------------------------------- phase C: instance
    veh_tris = veh_near = 0
    for asset_id, lod, m, name, vid in veh_plan:
        tpl = veh_tpl.get((asset_id, lod))
        if tpl is None:
            drop["vehicle_asset_unloadable"] = drop.get("vehicle_asset_unloadable", 0) + 1
            continue
        if lod < 2 and veh_near + tpl.triangles > veh_budget * NEAR_BAND_SHARE and rep.placed_vehicles:
            drop["vehicle_triangle_budget"] = drop.get("vehicle_triangle_budget", 0) + 1
            continue
        if veh_tris + tpl.triangles > veh_budget and rep.placed_vehicles:
            drop["vehicle_triangle_budget"] = drop.get("vehicle_triangle_budget", 0) + 1
            continue
        tpl.instance(f"agent_veh_{asset_id}_{vid}", m, col)
        rep.placed_vehicles += 1
        veh_tris += tpl.triangles
        if lod < 2:
            veh_near += tpl.triangles
        rep.vehicle_lods[f"LOD{lod}"] = rep.vehicle_lods.get(f"LOD{lod}", 0) + 1
        rep.per_class[name] = rep.per_class.get(name, 0) + 1

    ped_tris = ped_near = 0
    for arch, clip, pid, lod, m in ped_plan:
        tpl = peds.built(arch, clip, pid, lod)
        if tpl is None:
            drop["pedestrian_asset_unloadable"] = drop.get("pedestrian_asset_unloadable", 0) + 1
            continue
        parts, ptris, lift = tpl
        if lod < 2 and ped_near + ptris > ped_budget * NEAR_BAND_SHARE and rep.placed_pedestrians:
            drop["pedestrian_triangle_budget"] = drop.get("pedestrian_triangle_budget", 0) + 1
            continue
        if ped_tris + ptris > ped_budget and rep.placed_pedestrians:
            drop["pedestrian_triangle_budget"] = drop.get("pedestrian_triangle_budget", 0) + 1
            continue
        _instance(parts, f"agent_ped_{pid}", Matrix.Translation((0.0, 0.0, lift)) @ m, col)
        rep.placed_pedestrians += 1
        ped_tris += ptris
        if lod < 2:
            ped_near += ptris
        rep.ped_lods[f"LOD{lod}"] = rep.ped_lods.get(f"LOD{lod}", 0) + 1
    if peds.failed:
        rep.snapshot["npc_failures"] = peds.failed
    rep.snapshot["npc_archetypes_available"] = peds.archetypes
    if peds.folded:
        # A fold means the snapshot asked for a person this library cannot draw and someone else
        # was drawn instead.  It is never acceptable silently.
        rep.snapshot["npc_archetypes_folded"] = {str(k): v for k, v in sorted(peds.folded.items())}
    if car_free.active:
        rep.snapshot["car_free_park_drives_matched"] = car_free.matched
    rep.snapshot["npc_bodies_imported"] = peds.imported
    rep.snapshot["npc_templates_baked"] = peds.baked

    rep.triangles = veh_tris + ped_tris
    rep.vehicle_triangles = veh_tris
    rep.pedestrian_triangles = ped_tris
    rep.seconds = time.time() - t0
    if not (rep.placed_vehicles or rep.placed_pedestrians):
        rep.reason = ("the simulation put no agent on a paved surface inside the frame's radius"
                      if (snapshot.get("vehicles") or snapshot.get("pedestrians"))
                      else "the simulation frame is empty here")
    return rep


def _point_segment_distance(px: float, py: float, ax: float, ay: float, bx: float,
                            by: float) -> float:
    dx, dy = bx - ax, by - ay
    n = dx * dx + dy * dy
    tt = 0.0 if n <= 1e-9 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / n))
    return math.hypot(px - (ax + tt * dx), py - (ay + tt * dy))


def cull_near_camera(col, cam_x: float, cam_y: float, cam_z: float) -> dict[str, int]:
    """Remove agents standing within the clearance radii of the *final* camera position.

    ``add_agents`` measures its clearance from the point the scene was built around, and that is not
    always where the camera ends up: ``render_sheets.py`` builds the scene at the recorded view
    origin, then ``camera.probe_origin`` may switch to the nominal viewpoint and
    ``camera.clear_of_geometry`` may walk the eye onto the nearest paved surface.  Measured over the
    57 comparison scenes, **26 of them have the camera away from the scene centre** -- 5.4 m on
    `drive_bronx_grand_concourse`, 11 m on `drive_bronx_arthur_ave`, 166 m on
    `landmark_one_world_trade_center`.  So the clearance was guarding the wrong point, which is why
    `drive_bronx_grand_concourse` reported *no* pedestrian dropped over the observer while four stood
    between 1.44 m and 2.57 m of the lens.

    This runs after the camera is final and removes what the placement could not know about.  It is a
    cull rather than a re-placement: the agents that were never near the camera are already correct,
    and re-drawing the crowd around the moved eye would need the snapshot and the budget again.
    """
    import bpy  # noqa: F401  (imported here so the module stays importable without Blender)

    removed = {"pedestrian_over_the_observer": 0, "vehicle_over_the_observer": 0}
    if col is None:
        return removed
    doomed = []
    for ob in list(col.all_objects):
        name = ob.name
        if name.startswith("agent_ped"):
            r, key = CAMERA_CLEAR_PED_M, "pedestrian_over_the_observer"
        elif name.startswith("agent_veh"):
            r, key = CAMERA_CLEAR_VEHICLE_M, "vehicle_over_the_observer"
        else:
            continue
        px, py, pz = ob.matrix_world.translation
        if math.hypot(px - cam_x, py - cam_y) >= r:
            continue
        # A vehicle the eye stands above is not in the way (the Duffy Square camera is up on the
        # TKTS steps and looks over the traffic), matching the rule add_agents applies.
        if key == "vehicle_over_the_observer" and cam_z > pz + 2.2:
            continue
        doomed.append((ob, key))
    seen: set[str] = set()
    for ob, key in doomed:
        stem = ob.name.split(".")[0]
        if stem not in seen:
            seen.add(stem)
            removed[key] += 1
        bpy.data.objects.remove(ob, do_unlink=True)
    return removed


def vehicle_body_clearance(v: dict, cx: float, cy: float) -> float:
    """Plan distance from ``(cx, cy)`` to the vehicle's body, in metres (negative when inside).

    ``VehicleSnapshot`` gives the pivot at the ground under the rear-axle centre, so the body runs
    from about a quarter of a length behind it to about four fifths ahead; the body is treated as
    that axis swept by half its width, which is exact enough for a "would this be in the lens"
    test and needs nothing the snapshot does not carry.
    """
    L = float(v.get("length_m") or 4.9)
    W = float(v.get("width_m") or 1.8)
    h = float(v.get("heading_rad") or 0.0)
    ux, uy = math.cos(h), math.sin(h)
    x, y = float(v["x"]), float(v["y"])
    d = _point_segment_distance(cx, cy, x - 0.25 * L * ux, y - 0.25 * L * uy,
                                x + 0.85 * L * ux, y + 0.85 * L * uy)
    return d - 0.5 * W


def _keep_vehicle_part(name: str) -> bool:
    """Drop the convex collision proxies the fleet glbs carry beside their visible geometry."""
    return not name.startswith("UCX_")


# --------------------------------------------------------------------------- standalone


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--x", type=float, default=-2932.0)
    ap.add_argument("--y", type=float, default=6566.0)
    ap.add_argument("--heading-deg", type=float, default=0.0)
    ap.add_argument("--hour", type=int, default=12)
    ap.add_argument("--dow", type=int, default=0)
    ap.add_argument("--seed", type=int, default=20260907)
    ap.add_argument("--warmup-s", type=float, default=120.0)
    ap.add_argument("--radius", type=float, default=300.0)
    ap.add_argument("--audit", action="store_true", help="check the tool and the asset mapping only")
    ap.add_argument("--json", default="-")
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")

    if a.audit:
        tool, note = build_snapshot_tool()
        report = {"tool": None if tool is None else str(tool.relative_to(REPO_ROOT)),
                  "tool_note": note,
                  "npc_bodies": len([p for p in npc_archetype_assets() if p.exists()]),
                  "vehicles": audit_vehicle_assets()}
        print(json.dumps(report, indent=1, sort_keys=True))
        return 0 if tool is not None and not report["vehicles"]["assets_missing"] else 1

    req = SnapshotRequest(x=a.x, y=a.y, heading_deg=a.heading_deg, hour=a.hour, dow=a.dow,
                          seed=a.seed, warmup_s=a.warmup_s)
    snap, note = simulation_snapshot(req)
    if snap is None:
        print(json.dumps({"error": note}, indent=1))
        return 1
    out = {"note": note, "vehicles": snap["vehicle_count"], "pedestrians": snap["ped_count"],
           "density_target": snap["density_target"], "traffic_stats": snap["traffic_stats"],
           "ped_stats": snap["ped_stats"],
           "vehicle_audit": audit_vehicle_assets(snap.get("vehicle_classes"))}
    text = json.dumps(out, indent=1, sort_keys=True)
    if a.json in ("-", None):
        print(text)
    else:
        Path(a.json).write_text(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
