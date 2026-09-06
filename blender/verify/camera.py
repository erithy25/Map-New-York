"""Place the verification camera at a reference photograph's viewpoint.

The camera is never framed by eye.  Its position is the ``viewpoint`` lat/lon recorded in
``docs/verification/reference/<slug>/meta.json`` converted with
:func:`nycsim_pipeline.crs.lonlat_to_tm`, its heading is that entry's ``azimuth_deg``
(compass degrees, 0 = north, clockwise), and its height is the terrain surface under that
point plus an eye height taken from the viewpoint note:

* a person standing on the ground, a sidewalk, a roadway or a promenade -> 1.60 m
  (mean adult eye height; the photographs are hand-held, not tripod-on-a-ladder);
* a named structure the photographer stood on -> the published height of that structure
  plus 1.60 m (Top of the Rock's 70th-floor deck, the TKTS steps at Duffy Square);
* a vessel -> the published deck height above the waterline (Staten Island Ferry).

``EYE_OVERRIDES`` below carries one entry per such case with the source of the number, so
the caption strip on each sheet can state where the height came from.

Field of view: the default lens is **35 mm on a 36 mm full-frame sensor** -- 54.4 deg
horizontal, the standard "normal wide" reportage framing that most of the reference
photographs sit near.  Views whose note implies a wider lens (a street canyon shot from the
roadway, an observation deck panorama) get an explicit entry in ``LENS_OVERRIDES`` with the
reason.  Nothing here changes the camera position; only the angle of view.
"""
from __future__ import annotations

import argparse
import json
import logging
import math
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "blender" / "common"))
sys.path.insert(0, str(REPO_ROOT / "pipeline"))

import bpy  # noqa: E402
from mathutils import Euler  # noqa: E402

LOG = logging.getLogger("nycsim.verify.camera")

DEFAULT_EYE_HEIGHT_M = 1.60
DEFAULT_FOCAL_MM = 35.0
SENSOR_WIDTH_MM = 36.0

REFERENCE_DIR = REPO_ROOT / "docs" / "verification" / "reference"

#: Objects that count as solid world: tile building shells and placed landmark models.
_TILE_MESH = re.compile(r"^t_-?\d+_-?\d+_")


@dataclass(frozen=True)
class EyeRule:
    """How high above the local ground (or above the water) the photographer's eye sat."""
    height_m: float
    datum: str            # "terrain" or "sea"
    source: str


#: Keyed by reference slug.  Everything not listed here uses the terrain surface + 1.60 m.
EYE_OVERRIDES: dict[str, EyeRule] = {
    "top_of_the_rock_south": EyeRule(
        259.1 + 1.6, "terrain",
        "Top of the Rock outdoor deck, 70th floor of 30 Rockefeller Plaza: roof/deck level "
        "259.1 m above the plaza (blender_out/landmarks/catalog/30_rockefeller_plaza.json, "
        "CTBUH 850 ft), plus 1.6 m eye height"),
    "times_square_duffy_south_day": EyeRule(
        4.6 + 1.6, "terrain",
        "top landing of the TKTS red steps at Duffy Square, 4.6 m above the plaza "
        "(Perkins Eastman/Choi Ropiha structure, 16 ft to the top of the glazed stair), "
        "plus 1.6 m eye height"),
    "times_square_duffy_south_night": EyeRule(
        4.6 + 1.6, "terrain",
        "top landing of the TKTS red steps at Duffy Square, 4.6 m above the plaza, "
        "plus 1.6 m eye height"),
    "staten_island_ferry_lower_manhattan": EyeRule(
        8.0, "sea",
        "open bow deck of a Molinari/Barberi-class Staten Island Ferry: upper (promenade) "
        "deck about 6.4 m above the waterline, plus 1.6 m eye height; the boat is not "
        "modelled, so the camera floats free at that height over the Upper Bay"),
    "landmark_brooklyn_bridge_walkway": EyeRule(
        16.0, "sea",
        "Brooklyn Bridge promenade at the Brooklyn tower approach, deck about 14.4 m above "
        "the water at that chainage, plus 1.6 m eye height"),
    "landmark_high_line": EyeRule(
        9.1 + 1.6, "terrain",
        "High Line deck, 30 ft (9.1 m) above the street on the West Side Line viaduct, "
        "plus 1.6 m eye height"),
    "landmark_roosevelt_island_tram": EyeRule(
        1.6, "terrain",
        "Tramway Plaza at Second Avenue and 59th Street, street level, 1.6 m eye height"),
}


@dataclass(frozen=True)
class LensRule:
    focal_mm: float
    reason: str


#: Keyed by reference slug.  The default is 35 mm full-frame equivalent (54.4 deg horizontal).
LENS_OVERRIDES: dict[str, LensRule] = {
    "top_of_the_rock_south": LensRule(
        24.0, "observation-deck panorama: the reference frames span the whole Midtown-to-"
              "Lower-Manhattan skyline, which needs 74 deg horizontal (24 mm)"),
    "times_square_duffy_south_day": LensRule(
        24.0, "the bowtie is photographed wide from the TKTS steps; both building walls and "
              "One Times Square fit only at 74 deg horizontal"),
    "times_square_duffy_south_night": LensRule(
        24.0, "same framing as the daylight view"),
    "promenade_lower_manhattan": LensRule(
        28.0, "promenade skyline: the reference photographs carry the whole Lower Manhattan "
              "ridge plus the East River foreground, about 65 deg horizontal"),
    "staten_island_ferry_lower_manhattan": LensRule(
        28.0, "ferry-deck skyline, same wide framing as the promenade"),
    "dumbo_washington_st_manhattan_bridge": LensRule(
        28.0, "the 102 m Manhattan Bridge tower stands 172 m from the viewpoint, so its top sits "
              "31 deg above a level optical axis: 28 mm is the longest normal lens that still "
              "contains it without tilting the camera and skewing the verticals.  The reference "
              "photographs are longer (about 60 mm equivalent) and tilted up, so the render frames "
              "more of Washington Street than they do"),
    "bethesda_terrace_fountain": LensRule(
        28.0, "the terrace, fountain and the Lake behind it need a wide frame from the upper "
              "level"),
}


def focal_for(slug: str) -> tuple[float, str]:
    rule = LENS_OVERRIDES.get(slug)
    if rule is None:
        return DEFAULT_FOCAL_MM, "default 35 mm full-frame equivalent (54.4 deg horizontal)"
    return rule.focal_mm, rule.reason


def horizontal_fov_deg(focal_mm: float, sensor_mm: float = SENSOR_WIDTH_MM) -> float:
    return math.degrees(2.0 * math.atan(sensor_mm / (2.0 * focal_mm)))


@dataclass
class CameraPlacement:
    slug: str
    lat: float
    lon: float
    x: float
    y: float
    z: float
    azimuth_deg: float
    pitch_deg: float
    focal_mm: float
    sensor_mm: float
    hfov_deg: float
    eye_height_m: float
    eye_datum: str
    eye_source: str
    terrain_z_m: float | None
    resolution: tuple[int, int]
    portrait: bool = False
    long_side_fov_deg: float = 0.0
    ground_mode: str = "local"
    ground_source: str = ""
    ground_detail: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        d = asdict(self)
        for k in ("x", "y", "z", "hfov_deg", "long_side_fov_deg", "terrain_z_m"):
            if d[k] is not None:
                d[k] = round(d[k], 3)
        d["resolution"] = list(self.resolution)
        return d

    def caption(self) -> str:
        return (f"camera {self.lat:.5f}, {self.lon:.5f} (NYC_TM {self.x:.0f}, {self.y:.0f}) "
                f"z {self.z:.1f} m NAVD88 | azimuth {self.azimuth_deg:.1f}deg "
                f"pitch {self.pitch_deg:+.1f}deg | {self.focal_mm:.0f} mm on {self.sensor_mm:.0f} mm "
                f"({self.hfov_deg:.1f}deg horizontal"
                + (f", {self.long_side_fov_deg:.1f}deg vertical, portrait" if self.portrait else "")
                + f") | {self.resolution[0]}x{self.resolution[1]}")


def eye_rule_for(slug: str) -> EyeRule:
    return EYE_OVERRIDES.get(slug, EyeRule(DEFAULT_EYE_HEIGHT_M, "terrain",
                                           "standing observer, 1.6 m eye height above the terrain surface"))


#: Words in a viewpoint note that mean the photographer stood on the traffic surface rather than
#: on a raised structure.  The 1 m heightmap carries building grades and plinths, so a viewpoint
#: recorded on a sidewalk must be measured against the low ground nearby, not the terrace beside it.
_STREET_WORDS = ("roadway", "sidewalk", "street", "avenue", "curb", "crosswalk", "intersection",
                 "pavement", "plaza")
_RAISED_WORDS = ("terrace", "promenade", "deck", "observation", "steps", "walkway", "bridge",
                 "pier", "boardwalk", "platform", "parapet", "railing", "roof", "balcony",
                 "overlook", "viaduct", "ferry", "high line")


def ground_mode_for(slug: str, note: str | None) -> tuple[str, float, str]:
    """(mode, radius_m, why) for :meth:`scene.TerrainSampler.ground_z` at this viewpoint."""
    n = (note or "").lower()
    if any(w in n for w in _RAISED_WORDS):
        return ("local", 5.0,
                "the viewpoint note names the raised surface the photographer stood on, so the "
                "heightmap median within 5 m is the ground")
    if any(w in n for w in _STREET_WORDS):
        return ("street", 12.0,
                "the viewpoint note places the photographer on the traffic surface, so the 10th "
                "percentile of the heightmap within 12 m is used -- the 1 m DEM carries building "
                "grades and raised plinths that would otherwise lift the camera off the street")
    return ("local", 5.0, "no surface named in the note; heightmap median within 5 m")


def place_camera(*, slug: str, lat: float, lon: float, azimuth_deg: float, sampler,
                 resolution: tuple[int, int] = (1280, 853), pitch_deg: float = 0.0,
                 focal_mm: float | None = None, eye_rule: EyeRule | None = None,
                 note: str | None = None, clip_end: float = 60000.0) -> CameraPlacement:
    """Create and activate the scene camera for a reference viewpoint.

    ``pitch_deg`` is positive upwards from horizontal; the default 0 keeps the optical axis
    level, which is what a hand-held frame with vertical building edges implies.
    """
    from nycsim_pipeline.crs import lonlat_to_tm
    x, y = (float(v) for v in lonlat_to_tm(lon, lat))
    rule = eye_rule or eye_rule_for(slug)
    mode, mode_radius, mode_why = ground_mode_for(slug, note)
    terrain_z, ground_detail = (None, {})
    if sampler is not None:
        terrain_z, ground_detail = sampler.ground_z(x, y, mode=mode, radius_m=mode_radius)
    if rule.datum == "sea":
        base = 0.0
    elif terrain_z is None:
        base = 0.0
        LOG.warning("%s: no terrain heightmap under the viewpoint; eye height measured from 0 m NAVD88", slug)
    else:
        base = terrain_z
    z = base + rule.height_m

    f = focal_mm if focal_mm is not None else focal_for(slug)[0]
    cam = bpy.data.cameras.new(f"verify_cam_{slug}")
    # A focal length is quoted against the sensor's long side.  A portrait reference photograph
    # was taken with the camera turned, so the 36 mm dimension is vertical there; fitting the
    # lens to the short side instead would silently widen the frame.
    portrait = resolution[1] > resolution[0]
    cam.sensor_fit = "VERTICAL" if portrait else "HORIZONTAL"
    cam.sensor_width = SENSOR_WIDTH_MM
    cam.sensor_height = SENSOR_WIDTH_MM if portrait else SENSOR_WIDTH_MM * 2.0 / 3.0
    cam.lens = f
    cam.clip_start = 0.10
    cam.clip_end = clip_end
    ob = bpy.data.objects.new(f"verify_cam_{slug}", cam)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = (x, y, z)
    # Blender camera looks down -Z with +Y up.  rot_x = 90 deg puts it on the horizon looking
    # along +Y (north); rot_z = -azimuth swings it clockwise onto the compass bearing.
    ob.rotation_euler = Euler((math.radians(90.0 + pitch_deg), 0.0, math.radians(-azimuth_deg)), "XYZ")
    bpy.context.scene.camera = ob
    bpy.context.view_layer.update()   # so matrix_world reflects the transform just assigned

    sc = bpy.context.scene
    sc.render.resolution_x, sc.render.resolution_y = resolution
    sc.render.resolution_percentage = 100
    sc.render.pixel_aspect_x = sc.render.pixel_aspect_y = 1.0

    long_fov = horizontal_fov_deg(f)          # along the sensor's 36 mm side
    if portrait:
        hfov = math.degrees(2.0 * math.atan(math.tan(math.radians(long_fov) / 2.0)
                                            * resolution[0] / resolution[1]))
    else:
        hfov = long_fov
    return CameraPlacement(slug=slug, lat=lat, lon=lon, x=x, y=y, z=z, azimuth_deg=azimuth_deg,
                           pitch_deg=pitch_deg, focal_mm=f, sensor_mm=SENSOR_WIDTH_MM,
                           hfov_deg=hfov, eye_height_m=rule.height_m,
                           eye_datum=rule.datum, eye_source=rule.source, terrain_z_m=terrain_z,
                           resolution=resolution, portrait=portrait, long_side_fov_deg=long_fov,
                           ground_mode=mode, ground_source=mode_why, ground_detail=ground_detail)


def _blocked(x: float, y: float, z: float, azimuth_deg: float) -> tuple[bool, str]:
    """Is this eye point inside a building shell, or hard against a wall?

    A ray straight up from a street, a park or a promenade hits nothing.  One that hits a shell
    means the eye is under that building's roof, i.e. inside it -- which happens because the
    reference viewpoints are recorded to about 0.0001 deg (roughly 10 m) and several of them land
    on the wrong side of a facade.  A second ray along the view direction catches an eye point
    that is outside but pressed against a wall.
    """
    from mathutils import Vector
    dg = bpy.context.evaluated_depsgraph_get()
    sc = bpy.context.scene
    def is_shell(ob) -> bool:
        # Building shells are named ``t_<tx>_<ty>_<material>`` and landmarks ``lm_<id>``.  Kit and
        # prop instances (a sidewalk shed, a bus shelter) are legitimate things to stand under.
        return ob is not None and (_TILE_MESH.match(ob.name) or ob.name.startswith("lm_"))

    hit, _, _, _, ob, _ = sc.ray_cast(dg, Vector((x, y, z)), Vector((0.0, 0.0, 1.0)))
    if hit and is_shell(ob):
        return True, f"inside {ob.name} (a ray straight up from the eye point hits its roof)"
    a = math.radians(azimuth_deg)
    fwd = Vector((math.sin(a), math.cos(a), 0.0))
    hit, loc, _, _, ob, _ = sc.ray_cast(dg, Vector((x, y, z)), fwd, distance=2.0)
    if hit and is_shell(ob):
        return True, (f"hard against {ob.name} ({(Vector(loc) - Vector((x, y, z))).length:.1f} m "
                      f"ahead along the view azimuth)")
    return False, ""


def _standing_on(x: float, y: float, z: float, reach_m: float = 4.0):
    """The object holding this eye point up, if it is a building roof rather than the ground."""
    from mathutils import Vector
    dg = bpy.context.evaluated_depsgraph_get()
    hit, loc, _, _, ob, _ = bpy.context.scene.ray_cast(
        dg, Vector((x, y, z)), Vector((0.0, 0.0, -1.0)), distance=reach_m)
    if hit and ob is not None and (_TILE_MESH.match(ob.name) or ob.name.startswith("lm_")):
        return ob, float(loc.z)
    return None, None


def _walk_to_parapet(placement: "CameraPlacement", max_m: float = 250.0,
                     step_m: float = 2.0) -> dict:
    """An eye point standing on a roof belongs at that roof's edge, not in the middle of it.

    Observation-deck viewpoints (Top of the Rock, the High Line) are recorded as one lat/lon for
    the whole deck, which lands in the middle of the slab; the photographs are all taken at the
    parapet on the side the view faces.  Left alone the render is a picture of a roof.  This walks
    the eye forward along the view azimuth while the roof still supports it and stops at the last
    supported point -- the parapet.
    """
    ob, _ = _standing_on(placement.x, placement.y, placement.z)
    if ob is None:
        return {"moved": False, "offset_m": 0.0,
                "note": "the recorded viewpoint is in open air on the ground; the camera was not moved"}
    a = math.radians(placement.azimuth_deg)
    dx, dy = math.sin(a), math.cos(a)
    t, last_good = step_m, 0.0
    while t <= max_m:
        nx, ny = placement.x + dx * t, placement.y + dy * t
        on, _ = _standing_on(nx, ny, placement.z)
        if on is None:
            break
        last_good = t
        t += step_m
    if last_good < step_m:
        return {"moved": False, "offset_m": 0.0, "standing_on": ob.name,
                "note": (f"the eye point stands on {ob.name} and is already at its {placement.azimuth_deg:.0f} deg "
                         f"edge; the camera was not moved")}
    nx, ny = placement.x + dx * last_good, placement.y + dy * last_good
    cam = bpy.context.scene.camera
    cam.location = (nx, ny, placement.z)
    bpy.context.view_layer.update()
    placement.x, placement.y = nx, ny
    return {"moved": True, "offset_m": round(last_good, 1), "direction": "along the view azimuth",
            "standing_on": ob.name,
            "note": (f"the eye point stands on the roof of {ob.name}, which the reference viewpoint "
                     f"records as a single lat/lon for the whole deck; the camera was walked "
                     f"{last_good:.0f} m along the view azimuth to the parapet, the last point the "
                     f"roof still supports, which is where the reference photographs are taken")}


def clear_of_geometry(placement: "CameraPlacement", sampler, *, max_m: float = 80.0,
                      step_m: float = 2.0) -> dict:
    """Move an eye point that landed inside a building out to the first clear spot, and say so.

    The camera is only moved when it is demonstrably inside geometry.  It is walked along the
    recorded view azimuth first (a viewpoint recorded on the wrong side of a facade is nearly
    always a few metres short of the open space it names -- a promenade railing, a plaza), then
    backwards, then sideways.  The eye height is re-measured from the heightmap at the new point,
    and the offset is reported so the sheet can state it instead of hiding it.
    """
    blocked, why = _blocked(placement.x, placement.y, placement.z, placement.azimuth_deg)
    if not blocked:
        return _walk_to_parapet(placement)
    a = math.radians(placement.azimuth_deg)
    fwd = (math.sin(a), math.cos(a))
    dirs = [("along the view azimuth", fwd), ("backwards", (-fwd[0], -fwd[1])),
            ("to the left", (-fwd[1], fwd[0])), ("to the right", (fwd[1], -fwd[0]))]
    rise = placement.z - (placement.terrain_z_m if placement.terrain_z_m is not None else placement.z)
    for label, d in dirs:
        t = step_m
        while t <= max_m:
            nx, ny = placement.x + d[0] * t, placement.y + d[1] * t
            gz, detail = (sampler.ground_z(nx, ny, mode=placement.ground_mode,
                                           radius_m=placement.ground_detail.get("radius_m", 5.0))
                          if sampler is not None else (placement.terrain_z_m, {}))
            nz = (gz if gz is not None else placement.terrain_z_m or 0.0) + rise
            if not _blocked(nx, ny, nz, placement.azimuth_deg)[0]:
                ob = bpy.context.scene.camera
                ob.location = (nx, ny, nz)
                bpy.context.view_layer.update()
                placement.x, placement.y, placement.z = nx, ny, nz
                placement.terrain_z_m = gz
                placement.ground_detail = detail or placement.ground_detail
                return {"moved": True, "offset_m": round(t, 1), "direction": label,
                        "reason": why,
                        "note": (f"the recorded viewpoint is {why}; the camera was moved {t:.0f} m "
                                 f"{label} to the first point in open air, keeping the same eye "
                                 f"height above the heightmap")}
            t += step_m
    return {"moved": False, "offset_m": 0.0, "reason": why,
            "note": (f"the recorded viewpoint is {why} and no clear point was found within "
                     f"{max_m:.0f} m, so the frame is rendered from inside the shell and is dark")}


def load_reference(slug: str) -> dict:
    p = REFERENCE_DIR / slug / "meta.json"
    if not p.exists():
        raise FileNotFoundError(f"no reference metadata for {slug}: {p}")
    return json.loads(p.read_text())


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Print the camera placement for a reference slug.")
    ap.add_argument("slug")
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    import scene as vscene  # noqa: E402  (same directory)
    meta = load_reference(a.slug)
    vp = meta["viewpoint"]
    sampler = vscene.TerrainSampler()
    p = place_camera(slug=a.slug, lat=vp["lat"], lon=vp["lon"], azimuth_deg=vp["azimuth_deg"],
                     sampler=sampler)
    print(json.dumps(p.as_dict(), indent=1))
    print(p.caption())
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    raise SystemExit(main())
