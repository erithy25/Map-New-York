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
import sys
from dataclasses import dataclass, asdict
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
        28.0, "narrow Washington Street canyon: the bridge tower and both cornice lines only "
              "fit at about 65 deg horizontal"),
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

    def as_dict(self) -> dict:
        d = asdict(self)
        for k in ("x", "y", "z", "hfov_deg", "terrain_z_m"):
            if d[k] is not None:
                d[k] = round(d[k], 3)
        d["resolution"] = list(self.resolution)
        return d

    def caption(self) -> str:
        return (f"camera {self.lat:.5f}, {self.lon:.5f} (NYC_TM {self.x:.0f}, {self.y:.0f}) "
                f"z {self.z:.1f} m NAVD88 | azimuth {self.azimuth_deg:.1f}deg "
                f"pitch {self.pitch_deg:+.1f}deg | {self.focal_mm:.0f} mm on {self.sensor_mm:.0f} mm "
                f"({self.hfov_deg:.1f}deg horizontal) | {self.resolution[0]}x{self.resolution[1]}")


def eye_rule_for(slug: str) -> EyeRule:
    return EYE_OVERRIDES.get(slug, EyeRule(DEFAULT_EYE_HEIGHT_M, "terrain",
                                           "standing observer, 1.6 m eye height above the terrain surface"))


def place_camera(*, slug: str, lat: float, lon: float, azimuth_deg: float, sampler,
                 resolution: tuple[int, int] = (1280, 853), pitch_deg: float = 0.0,
                 focal_mm: float | None = None, eye_rule: EyeRule | None = None,
                 clip_end: float = 60000.0) -> CameraPlacement:
    """Create and activate the scene camera for a reference viewpoint.

    ``pitch_deg`` is positive upwards from horizontal; the default 0 keeps the optical axis
    level, which is what a hand-held frame with vertical building edges implies.
    """
    from nycsim_pipeline.crs import lonlat_to_tm
    x, y = (float(v) for v in lonlat_to_tm(lon, lat))
    rule = eye_rule or eye_rule_for(slug)
    terrain_z = sampler.z_at(x, y) if sampler is not None else None
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
    cam.sensor_fit = "HORIZONTAL"
    cam.sensor_width = SENSOR_WIDTH_MM
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

    sc = bpy.context.scene
    sc.render.resolution_x, sc.render.resolution_y = resolution
    sc.render.resolution_percentage = 100
    sc.render.pixel_aspect_x = sc.render.pixel_aspect_y = 1.0

    return CameraPlacement(slug=slug, lat=lat, lon=lon, x=x, y=y, z=z, azimuth_deg=azimuth_deg,
                           pitch_deg=pitch_deg, focal_mm=f, sensor_mm=SENSOR_WIDTH_MM,
                           hfov_deg=horizontal_fov_deg(f), eye_height_m=rule.height_m,
                           eye_datum=rule.datum, eye_source=rule.source, terrain_z_m=terrain_z,
                           resolution=resolution)


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
    nb_scene = bpy.context.scene  # noqa: F841 (ensure bpy is live)
    p = place_camera(slug=a.slug, lat=vp["lat"], lon=vp["lon"], azimuth_deg=vp["azimuth_deg"],
                     sampler=sampler)
    print(json.dumps(p.as_dict(), indent=1))
    print(p.caption())
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    raise SystemExit(main())
