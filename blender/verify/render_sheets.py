"""Render each reference viewpoint and compose the photograph-vs-simulation comparison sheets.

For every slug under ``docs/verification/reference/`` this script

1. reads the licensed reference photographs and their metadata (viewpoint, azimuth, author,
   licence, date the photograph was taken);
2. assembles the world around that viewpoint with :mod:`scene`;
3. places the camera with :mod:`camera`;
4. puts the Sun where it actually was at the moment the reference photograph was taken -- the
   real date and local time run through ``services/nycsim_live/astronomy.py`` (the same SPA
   implementation the live services use) -- falling back to 09:30 local on the photograph's date
   (or on the summer solstice when only a year is recorded);
5. renders 1280 px wide with Cycles on the CPU to
   ``docs/verification/comparison/<slug>/render.png``;
6. composes ``docs/verification/comparison/<slug>/sheet.png``: reference left, render right,
   caption strip underneath naming the subject, the viewpoint, the photograph's author and
   licence, and the render's camera parameters and scene contents.

Usage::

    python3 blender/verify/render_sheets.py --slugs promenade_lower_manhattan
    python3 blender/verify/render_sheets.py --group viewpoint --samples 64
    python3 blender/verify/render_sheets.py --compose-only --slugs top_of_the_rock_south
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import logging
import math
import sys
import time
from pathlib import Path
from typing import Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
for p in (str(HERE), str(REPO_ROOT / "blender" / "common"), str(REPO_ROOT / "pipeline"),
          str(REPO_ROOT / "services"), str(REPO_ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)

LOG = logging.getLogger("nycsim.verify.render")

REFERENCE_DIR = REPO_ROOT / "docs" / "verification" / "reference"
COMPARISON_DIR = REPO_ROOT / "docs" / "verification" / "comparison"
FONT_DIR = REPO_ROOT / "assets" / "fonts" / "Overpass"

NY_TZ = "America/New_York"

# Lighting model constants.  SUN_CALIBRATION and REFERENCE_KEY_W were measured with
# blender/verify/ test renders of a 0.26-albedo ground: they put a clear-midday sunlit ground at
# about 150/255 through Filmic, which is where a correctly exposed photograph of concrete sits.
SOLAR_CONSTANT_W = 1361.0
ATMOSPHERIC_TRANSMITTANCE = 0.7
SUN_CALIBRATION = 540.0
DIFFUSE_KEY_W = 90.0
REFERENCE_KEY_W = 681.0
SKY_STRENGTH_DAY = 0.25
SKY_STRENGTH_NIGHT = 0.5
NIGHT_EXPOSURE_STOPS = 2.0
RENDER_WIDTH = 1280
DEFAULT_SAMPLES = 64

#: Slug -> (scene radius m, prop radius m, kit radius m).  A skyline view needs kilometres of
#: world and no facade detail; a street view needs the opposite.
RADIUS_OVERRIDES: dict[str, tuple[float, float, float]] = {
    "promenade_lower_manhattan": (5000.0, 0.0, 0.0),
    "staten_island_ferry_lower_manhattan": (5500.0, 0.0, 0.0),
    "top_of_the_rock_south": (4500.0, 0.0, 0.0),
    "times_square_duffy_south_day": (800.0, 250.0, 130.0),
    "times_square_duffy_south_night": (800.0, 250.0, 130.0),
    "fifth_ave_42nd_north": (700.0, 250.0, 140.0),
    "fifth_ave_42nd_south": (700.0, 250.0, 140.0),
    "dumbo_washington_st_manhattan_bridge": (900.0, 250.0, 140.0),
    "bethesda_terrace_fountain": (700.0, 300.0, 120.0),
}

#: The seven viewpoints the project brief mandates, mapped to the reference slugs that cover them.
MANDATED_VIEWPOINTS: dict[str, list[str]] = {
    "Brooklyn Heights Promenade": ["promenade_lower_manhattan"],
    "Top of the Rock": ["top_of_the_rock_south"],
    "Times Square from Duffy Square": ["times_square_duffy_south_day", "times_square_duffy_south_night"],
    "Fifth Avenue at 42nd Street": ["fifth_ave_42nd_north", "fifth_ave_42nd_south"],
    "Bethesda Terrace": ["bethesda_terrace_fountain"],
    "Staten Island Ferry deck": ["staten_island_ferry_lower_manhattan"],
    "Washington Street, DUMBO": ["dumbo_washington_st_manhattan_bridge"],
}

DRIVE_THROUGH_AREAS: dict[str, list[str]] = {
    "Midtown Manhattan": ["drive_midtown_sixth_ave_45th"],
    "Lower Manhattan": ["drive_lower_manhattan_broadway_wall_st", "drive_lower_manhattan_stone_st"],
    "Brooklyn brownstones": ["drive_brooklyn_park_slope_7th_ave", "drive_brooklyn_bed_stuy_stuyvesant_ave"],
    "Queens residential": ["drive_queens_jackson_heights", "drive_queens_forest_hills", "drive_queens_bayside"],
    "The Bronx": ["drive_bronx_grand_concourse", "drive_bronx_arthur_ave"],
}


# --------------------------------------------------------------------------- reference metadata


def list_slugs() -> list[str]:
    out = []
    for d in sorted(REFERENCE_DIR.iterdir()):
        if d.is_dir() and (d / "meta.json").exists():
            out.append(d.name)
    return out


def load_meta(slug: str) -> dict:
    return json.loads((REFERENCE_DIR / slug / "meta.json").read_text())


def pick_reference_photo(meta: dict) -> dict | None:
    """The photograph that gives the fairest comparison for this item.

    Preference order: the file exists on disk; the Sun at the moment it was taken agrees with
    whether the item is a day or a night view (a daylight item photographed after sunset would
    force a black render); a full date *and* time is recorded, so the Sun can be placed from the
    real instant instead of an assumption; then the estimated-viewpoint confidence and the
    azimuth error against the item's canonical viewpoint.
    """
    slug = meta["slug"]
    vp = meta["viewpoint"]
    az = float(vp["azimuth_deg"])
    night = bool(meta.get("night"))
    best, best_key = None, None
    for p in meta.get("photos", []):
        f = REFERENCE_DIR / slug / p["file"]
        if not f.exists():
            continue
        ev = p.get("estimated_viewpoint") or {}
        pa = ev.get("azimuth_deg", az)
        err = abs((float(pa) - az + 180.0) % 360.0 - 180.0)
        has_time = bool(p.get("date_taken") and len(str(p["date_taken"])) >= 16)
        conf = {"high": 0, "medium": 1, "low": 2}.get(ev.get("confidence", "low"), 2)
        when, _ = photo_instant(p)
        elev = sun_for(vp["lat"], vp["lon"], when)["elevation_deg"]
        # Hard gate first: a daylight item must not be paired with an after-dark frame, and vice
        # versa.  Then a real EXIF timestamp, because it fixes the Sun exactly.  Only then the
        # softer preference for a well-lit hour.
        if night:
            lit_bad = 0 if elev < 0.0 else 1
            lit_tier = 0 if elev <= -6.0 else 1
        else:
            lit_bad = 0 if elev > 3.0 else 1
            lit_tier = 0 if elev >= 12.0 else 1
        key = (lit_bad, 0 if has_time else 1, lit_tier, conf, err)
        if best_key is None or key < best_key:
            best, best_key = p, key
    return best


def photo_instant(photo: dict) -> tuple[dt.datetime, str]:
    """Local New York datetime for a photo, plus a note on where it came from."""
    from zoneinfo import ZoneInfo
    tz = ZoneInfo(NY_TZ)
    raw = str(photo.get("date_taken") or "").strip()
    for fmt, note in (("%Y-%m-%d %H:%M:%S", "EXIF DateTimeOriginal"),
                      ("%Y-%m-%d %H:%M", "EXIF DateTimeOriginal (minutes)"),
                      ("%Y-%m-%dT%H:%M:%S", "EXIF DateTimeOriginal")):
        try:
            return dt.datetime.strptime(raw, fmt).replace(tzinfo=tz), note
        except ValueError:
            pass
    try:
        d = dt.datetime.strptime(raw, "%Y-%m-%d").date()
        return dt.datetime.combine(d, dt.time(9, 30), tzinfo=tz), "photograph date, mid-morning 09:30 assumed"
    except ValueError:
        pass
    year = photo.get("year")
    if isinstance(year, int):
        return dt.datetime(year, 6, 21, 9, 30, tzinfo=tz), "photograph year only; 21 June 09:30 assumed"
    return dt.datetime(2024, 6, 21, 9, 30, tzinfo=tz), "no date recorded; 21 June 2024 09:30 assumed"


def sun_for(lat: float, lon: float, when_local: dt.datetime, elevation_m: float = 20.0) -> dict:
    from nycsim_live import astronomy
    obs = astronomy.Observer(lat, lon, elevation_m)
    pos = astronomy.solar_position(when_local.astimezone(dt.timezone.utc), obs)
    return {"azimuth_deg": pos.azimuth, "elevation_deg": pos.elevation,
            "utc": pos.utc.isoformat().replace("+00:00", "Z"),
            "local": when_local.isoformat()}


# --------------------------------------------------------------------------- rendering


def setup_world_and_sun(sun_azimuth_deg: float, sun_elevation_deg: float, *, night: bool) -> dict:
    """Nishita sky at the real Sun position, a matching directional light, and an exposure.

    The Sun's strength follows the direct normal irradiance for the Sun's actual elevation --
    1361 W/m2 at the top of the atmosphere, Kasten-Young air mass, 0.7 atmospheric transmittance
    per air mass -- divided by a single calibration constant so that a clear midday frame lands
    where a correctly exposed photograph lands (a 0.26-albedo sunlit ground at about 150/255
    through the Filmic view transform).  The view exposure then opens up by as much as three
    stops as the light falls off, the way a photographer would; it never stops down, so a bright
    scene stays bright.

    Below the horizon the sky node is clamped to civil twilight and no directional light is
    added.  Nothing artificial stands in for street lighting, so a night frame shows exactly how
    much emissive content the world currently has -- which is the point of the check.
    """
    import bpy
    sc = bpy.context.scene
    world = bpy.data.worlds.get("World") or bpy.data.worlds.new("World")
    sc.world = world
    world.use_nodes = True
    nt = world.node_tree
    bg = nt.nodes.get("Background")
    if bg is None:
        bg = nt.nodes.new("ShaderNodeBackground")
        out = nt.nodes.get("World Output") or nt.nodes.new("ShaderNodeOutputWorld")
        nt.links.new(bg.outputs["Background"], out.inputs["Surface"])
    sky = nt.nodes.new("ShaderNodeTexSky")
    sky.sky_type = "NISHITA"
    sky_elev = max(sun_elevation_deg, -4.0)
    sky.sun_elevation = math.radians(sky_elev)
    sky.sun_rotation = math.radians(sun_azimuth_deg)
    sky.sun_intensity = 0.0
    sky.altitude = 0.0
    nt.links.new(sky.outputs["Color"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = SKY_STRENGTH_NIGHT if night else SKY_STRENGTH_DAY

    dni = 0.0
    lamp = None
    if sun_elevation_deg > 0.5:
        e = math.radians(sun_elevation_deg)
        air_mass = 1.0 / (math.sin(e) + 0.50572 * (sun_elevation_deg + 6.07995) ** -1.6364)
        dni = SOLAR_CONSTANT_W * (ATMOSPHERIC_TRANSMITTANCE ** (air_mass ** 0.678))
        light = bpy.data.lights.new("verify_sun", "SUN")
        light.energy = dni / SUN_CALIBRATION
        light.angle = math.radians(0.53)
        lamp = bpy.data.objects.new("verify_sun", light)
        sc.collection.objects.link(lamp)
        lamp.rotation_euler = (math.radians(90.0 - sun_elevation_deg), 0.0,
                               math.radians(-sun_azimuth_deg))
        key = dni * math.sin(e) + DIFFUSE_KEY_W
        exposure = min(3.0, max(0.0, math.log2(REFERENCE_KEY_W / key)))
    else:
        exposure = NIGHT_EXPOSURE_STOPS
    sc.view_settings.exposure = exposure
    for want in ("Filmic", "AgX", "Standard"):
        try:
            sc.view_settings.view_transform = want
            break
        except (TypeError, ValueError):
            continue
    return {"sky_elevation_deg": round(sky_elev, 3), "sky_azimuth_deg": round(sun_azimuth_deg, 3),
            "sun_lamp": lamp is not None,
            "direct_normal_irradiance_w_m2": round(dni, 1),
            "sun_strength_blender": round(dni / SUN_CALIBRATION, 3),
            "background_strength": bg.inputs["Strength"].default_value,
            "view_transform": sc.view_settings.view_transform,
            "exposure_stops": round(exposure, 2)}


def apply_time_of_day_materials(night: bool) -> dict:
    """Switch the world's emissive content to match the hour of the reference photograph.

    Three cases, and only the first two change anything:

    * ``LIGHT_CONE`` -- the prop kit models the beam under each street lamp as a cone of emissive
      geometry.  That is a night-time visualisation, not a physical object, so in a daylight frame
      it is made fully transparent; left on it hangs a glowing cone under every lamp at noon.
    * ``LAMP_EMISSIVE`` -- NYC street lighting is dusk-to-dawn, so the lamp lens is off in a
      daylight frame.  Its authored material is pure emission over a black base, which would
      render as a black hole once the emission is zeroed, so the base colour is set to a pale
      diffuser grey at the same time.
    * everything else (``LED_*`` on traffic signals, lit shopfronts and screens) is left exactly
      as the kit authored it: those run in daylight too, and a night frame must show the emissive
      content the world really has.
    """
    import bpy
    if night:
        return {"night": True, "cones_hidden": 0, "lamps_switched_off": 0,
                "note": "night frame: every emissive material left as the kit authored it"}
    cones = lamps = 0
    for mat in bpy.data.materials:
        name = (mat.name or "").upper()
        is_cone = "LIGHT_CONE" in name
        is_lamp = "LAMP_EMISSIVE" in name
        if not (is_cone or is_lamp) or not mat.use_nodes:
            continue
        for node in mat.node_tree.nodes:
            if node.type == "EMISSION" and "Strength" in node.inputs:
                node.inputs["Strength"].default_value = 0.0
            elif node.type == "BSDF_PRINCIPLED":
                if "Emission Strength" in node.inputs:
                    node.inputs["Emission Strength"].default_value = 0.0
                if is_cone and "Alpha" in node.inputs:
                    node.inputs["Alpha"].default_value = 0.0
                if is_lamp and "Base Color" in node.inputs:
                    c = node.inputs["Base Color"].default_value
                    if max(c[0], c[1], c[2]) < 0.05:
                        node.inputs["Base Color"].default_value = (0.62, 0.61, 0.58, 1.0)
        if is_cone:
            mat.blend_method = "BLEND"
            cones += 1
        else:
            lamps += 1
    return {"night": False, "cones_hidden": cones, "lamps_switched_off": lamps,
            "note": "daylight frame: modelled light cones made transparent and street-lamp lenses "
                    "switched off (dusk-to-dawn control); signals and shopfront emissives left on"}


def configure_cycles(samples: int, threads: int | None) -> None:
    import bpy
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = samples
    sc.cycles.use_denoising = True
    sc.cycles.use_adaptive_sampling = True
    sc.cycles.adaptive_threshold = 0.03
    sc.cycles.adaptive_min_samples = max(8, samples // 8)
    sc.cycles.max_bounces = 2
    sc.cycles.diffuse_bounces = 2
    sc.cycles.glossy_bounces = 1
    sc.cycles.transmission_bounces = 1
    sc.cycles.transparent_max_bounces = 2
    sc.cycles.volume_bounces = 0
    sc.cycles.caustics_reflective = False
    sc.cycles.caustics_refractive = False
    sc.render.film_transparent = False
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGB"
    if threads:
        sc.render.threads_mode = "FIXED"
        sc.render.threads = threads


def aim_pitch(slug: str, meta: dict, cam_x: float, cam_y: float, cam_z: float,
              sampler, landmarks: Sequence[dict]) -> tuple[float, str]:
    """How far the optical axis tilts off horizontal, and why.

    The default is level: a level axis keeps vertical building edges vertical, which is the
    convention every architectural photograph follows and the only way a render and a photograph
    can be compared on proportion.  The single exception is a subject standing close to the camera
    and clearly below or above eye level -- the Bethesda fountain 69 m away and 6 m below the
    terrace, say -- where a level axis would push it to the edge of the frame.  For a subject
    inside 250 m the axis is aimed at its mid-height, taken from the landmark model that stands
    there when there is one; if that aim exceeds 8 deg it is discarded and the axis stays level,
    because past that point a real photograph would be taken with a wider lens rather than a
    tilted camera.
    """
    subject = meta.get("subject") or {}
    if subject.get("lat") is None or subject.get("lon") is None:
        return 0.0, "level optical axis (the reference names no subject to aim at)"
    from nycsim_pipeline.crs import lonlat_to_tm
    sx, sy = (float(v) for v in lonlat_to_tm(subject["lon"], subject["lat"]))
    dist = math.hypot(sx - cam_x, sy - cam_y)
    if dist > 250.0 or dist < 1.0:
        return 0.0, (f"level optical axis (the subject is {dist:.0f} m away; anything that far is "
                     f"photographed with a level camera)")
    ground, _ = sampler.ground_z(sx, sy, mode="street", radius_m=15.0) if sampler else (None, {})
    if ground is None:
        ground = cam_z - 1.6
    height, src = 10.0, "a nominal 10 m subject"
    best = None
    for e in landmarks:
        ox, oy = float(e["origin_tm"][0]), float(e["origin_tm"][1])
        d = math.hypot(ox - sx, oy - sy)
        h = e.get("height_m") or (e.get("bounds_local_m") or {}).get("max", [0, 0, 0])[2]
        if d <= 120.0 and h and (best is None or d < best[0]):
            best = (d, float(h), e["id"])
    if best is not None:
        height, src = best[1], f"the {best[2]} model's {best[1]:.0f} m height"
    target_z = ground + height / 2.0
    pitch = math.degrees(math.atan2(target_z - cam_z, dist))
    if abs(pitch) > 8.0:
        return 0.0, (f"level optical axis ({subject.get('name') or 'the subject'} is {dist:.0f} m "
                     f"away and would need {pitch:+.0f} deg of tilt; a real frame would use a wider "
                     f"lens instead, and a tilted axis would stop the render being comparable on "
                     f"proportion)")
    return pitch, (f"aimed at {subject.get('name') or 'the subject'} {dist:.0f} m away, at its "
                   f"mid-height ({src}); {pitch:+.1f} deg from horizontal")


def render_subject(slug: str, *, samples: int = DEFAULT_SAMPLES, threads: int | None = None,
                   width: int = RENDER_WIDTH, dry_run: bool = False) -> dict:
    """Build, aim, light and render one subject.  Returns the record written to render.json."""
    import bpy
    import scene as vscene
    import camera as vcam
    from nycsim_pipeline.crs import lonlat_to_tm

    meta = load_meta(slug)
    vp = meta["viewpoint"]
    photo = pick_reference_photo(meta)
    outdir = COMPARISON_DIR / slug
    outdir.mkdir(parents=True, exist_ok=True)

    x, y = (float(v) for v in lonlat_to_tm(vp["lon"], vp["lat"]))
    subject = meta.get("subject") or {}
    subj_dist = None
    if subject.get("lat") is not None and subject.get("lon") is not None:
        sx, sy = (float(v) for v in lonlat_to_tm(subject["lon"], subject["lat"]))
        subj_dist = math.hypot(sx - x, sy - y)
    if slug in RADIUS_OVERRIDES:
        radius, prop_r, kit_r = RADIUS_OVERRIDES[slug]
    else:
        radius = max(500.0, min(3000.0, (subj_dist or 200.0) * 1.6 + 400.0))
        prop_r = 0.0 if radius > 1500.0 else 250.0
        kit_r = 0.0 if radius > 1500.0 else 120.0

    if photo is None:
        return {"slug": slug, "status": "no_reference_photo",
                "reason": "meta.json lists no photograph that exists on disk"}

    when, when_note = photo_instant(photo)
    sun = sun_for(vp["lat"], vp["lon"], when)

    # Match the render aspect to the reference photograph so the two halves compare like for like.
    pw, ph = int(photo.get("width") or 1600), int(photo.get("height") or 1067)
    aspect = pw / ph if ph else 1.5
    height = max(360, int(round(width / aspect / 2) * 2))

    record = {
        "slug": slug, "name": meta.get("name"), "group": meta.get("group"),
        "night": bool(meta.get("night")), "interior": bool(meta.get("interior")),
        "viewpoint": {"lat": vp["lat"], "lon": vp["lon"], "azimuth_deg": vp["azimuth_deg"],
                      "note": vp.get("note")},
        "subject": {"name": subject.get("name"), "distance_m": None if subj_dist is None else round(subj_dist, 1)},
        "reference_photo": {
            "file": photo["file"], "author": photo.get("author"),
            "licence": (photo.get("license") or {}).get("short_name"),
            "licence_url": (photo.get("license") or {}).get("url"),
            "page_url": photo.get("page_url"), "title": photo.get("title"),
            "date_taken": photo.get("date_taken"), "width": pw, "height": ph,
            "estimated_azimuth_deg": (photo.get("estimated_viewpoint") or {}).get("azimuth_deg"),
            "confidence": (photo.get("estimated_viewpoint") or {}).get("confidence"),
        },
        "sun": {**sun, "time_source": when_note},
        "scene_request": {"radius_m": radius, "prop_radius_m": prop_r, "kit_radius_m": kit_r},
        "samples": samples,
    }
    if dry_run:
        record["status"] = "dry_run"
        return record

    t0 = time.time()
    rep, sampler = vscene.build_scene(
        x, y, radius, prop_radius_m=prop_r, kit_radius_m=kit_r,
        with_props=prop_r > 0, with_kit=kit_r > 0,
        terrain_max_side=300 if radius <= 1500 else 380,
        lod0_radius_m=1200.0)
    pitch, pitch_why = aim_pitch(slug, meta, x, y,
                                 (sampler.ground_z(x, y)[0] or 0.0) + vcam.eye_rule_for(slug).height_m,
                                 sampler, vscene.load_landmark_catalog())
    placement = vcam.place_camera(slug=slug, lat=vp["lat"], lon=vp["lon"],
                                  azimuth_deg=float(vp["azimuth_deg"]), sampler=sampler,
                                  resolution=(width, height), note=vp.get("note"), pitch_deg=pitch)
    clearance = vcam.clear_of_geometry(placement, sampler)
    light = setup_world_and_sun(sun["azimuth_deg"], sun["elevation_deg"], night=bool(meta.get("night")))
    light["emissive"] = apply_time_of_day_materials(bool(meta.get("night")))
    configure_cycles(samples, threads)

    render_path = outdir / "render.png"
    bpy.context.scene.render.filepath = str(render_path)
    t1 = time.time()
    bpy.ops.render.render(write_still=True)
    t2 = time.time()

    record.update({
        "status": "rendered",
        "camera": placement.as_dict(),
        "camera_caption": placement.caption(),
        "lens_reason": vcam.focal_for(slug)[1],
        "pitch_reason": pitch_why,
        "clearance": clearance,
        "lighting": light,
        "scene": rep.as_dict(),
        "render_png": str(render_path.relative_to(REPO_ROOT)),
        "seconds": {"scene": round(t1 - t0, 1), "render": round(t2 - t1, 1), "total": round(t2 - t0, 1)},
        "rendered_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
    })
    (outdir / "render.json").write_text(json.dumps(record, indent=1, sort_keys=True))
    LOG.info("%s rendered in %.0f s (scene %.0f s, %d triangles)", slug, t2 - t0, t1 - t0, rep.triangles)
    return record


# --------------------------------------------------------------------------- sheet composition


def _font(size: int, bold: bool = False):
    from PIL import ImageFont
    name = "overpass-semibold.otf" if bold else "overpass-regular.otf"
    p = FONT_DIR / name
    if p.exists():
        try:
            return ImageFont.truetype(str(p), size)
        except Exception:
            pass
    return ImageFont.load_default()


def _wrap(draw, text: str, font, max_w: int) -> list[str]:
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = f"{cur} {w}".strip()
        if draw.textlength(t, font=font) <= max_w or not cur:
            cur = t
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def compose_sheet(slug: str, record: dict | None = None) -> Path | None:
    """Reference photograph left, render right, caption strip below."""
    from PIL import Image, ImageDraw
    outdir = COMPARISON_DIR / slug
    rec_path = outdir / "render.json"
    if record is None:
        if not rec_path.exists():
            LOG.warning("%s: no render.json, nothing to compose", slug)
            return None
        record = json.loads(rec_path.read_text())
    render_png = outdir / "render.png"
    if not render_png.exists():
        LOG.warning("%s: no render.png, nothing to compose", slug)
        return None
    ref_png = REFERENCE_DIR / slug / record["reference_photo"]["file"]
    if not ref_png.exists():
        LOG.warning("%s: reference photo %s missing", slug, ref_png)
        return None

    panel_w = RENDER_WIDTH
    ref = Image.open(ref_png).convert("RGB")
    ren = Image.open(render_png).convert("RGB")
    ref_h = int(round(ref.height * panel_w / ref.width))
    ren_h = int(round(ren.height * panel_w / ren.width))
    panel_h = max(ref_h, ren_h)
    ref = ref.resize((panel_w, ref_h), Image.LANCZOS)
    ren = ren.resize((panel_w, ren_h), Image.LANCZOS)

    gap, margin, label_h = 16, 24, 34
    sheet_w = margin * 2 + panel_w * 2 + gap
    header_h = 56

    f_title = _font(26, bold=True)
    f_label = _font(19, bold=True)
    f_body = _font(16)
    f_small = _font(14)

    scene = record.get("scene", {})
    cam = record.get("camera", {})
    ph = record.get("reference_photo", {})
    b = scene.get("buildings", {})
    lm = scene.get("landmarks", {})
    pr = scene.get("props", {})
    kt = scene.get("kit", {})

    caption_lines: list[tuple[str, object]] = []
    caption_lines.append((f"Viewpoint: {record['viewpoint'].get('note') or '-'} "
                          f"({record['viewpoint']['lat']:.5f}, {record['viewpoint']['lon']:.5f}, "
                          f"azimuth {record['viewpoint']['azimuth_deg']:.1f} deg)", f_body))
    subj = record.get("subject", {})
    if subj.get("name"):
        caption_lines.append((f"Subject: {subj['name']}"
                              + (f", {subj['distance_m']:.0f} m from the camera" if subj.get("distance_m") else ""), f_body))
    caption_lines.append((f"Photograph: {ph.get('title') or ph.get('file')} - {ph.get('author')}, "
                          f"{ph.get('licence')} ({ph.get('licence_url')}), taken {ph.get('date_taken')}; "
                          f"via Wikimedia Commons {ph.get('page_url')}", f_small))
    caption_lines.append((f"Render: {record.get('camera_caption', '')}", f_small))
    caption_lines.append((f"Lens: {record.get('lens_reason','')}", f_small))
    if record.get("pitch_reason"):
        caption_lines.append((f"Aim: {record['pitch_reason']}", f_small))
    cl = record.get("clearance") or {}
    if cl.get("note"):
        caption_lines.append((f"Camera clearance: {cl['note']}", f_small))
    caption_lines.append((f"Eye height: {cam.get('eye_height_m')} m above "
                          f"{'sea level' if cam.get('eye_datum') == 'sea' else 'the terrain surface'} - "
                          f"{cam.get('eye_source','')}", f_small))
    if cam.get("eye_datum") != "sea":
        gd = cam.get("ground_detail") or {}
        caption_lines.append((
            f"Ground under the camera: {cam.get('terrain_z_m')} m NAVD88 from the 2 m heightmap "
            f"({gd.get('samples', 0)} samples in {gd.get('radius_m', 0)} m, range "
            f"{gd.get('min_m')}-{gd.get('max_m')} m) - {cam.get('ground_source','')}", f_small))
    sun = record.get("sun", {})
    lit = record.get("lighting", {})
    caption_lines.append((f"Sun: azimuth {sun.get('azimuth_deg', 0):.1f} deg, elevation "
                          f"{sun.get('elevation_deg', 0):.1f} deg at {sun.get('local','')} "
                          f"({sun.get('time_source','')}); direct normal irradiance "
                          f"{lit.get('direct_normal_irradiance_w_m2', 0):.0f} W/m2, Nishita sky, "
                          f"{lit.get('view_transform','')} view transform "
                          f"{lit.get('exposure_stops', 0):+.2f} stops; Cycles CPU, "
                          f"{record.get('samples')} samples max, adaptive, denoised", f_small))
    caption_lines.append((
        f"In frame: {b.get('tiles_imported', 0)}/{b.get('tiles_wanted', 0)} building tiles "
        f"({b.get('triangles', 0):,} tris), {lm.get('placed', 0)} landmarks, "
        f"{pr.get('placed', 0)} props, {kt.get('placed', 0)} kit pieces; "
        f"{scene.get('triangles', 0):,} triangles total", f_small))
    gaps = []
    if b.get("tiles_missing"):
        miss = b["missing"][:8]
        gaps.append(f"building shells not built for {b['tiles_missing']} tile(s): " + ", ".join(miss)
                    + (" ..." if b["tiles_missing"] > len(miss) else ""))
    if pr.get("capped"):
        gaps.append(f"props capped by {pr['capped']}")
    if kt.get("capped"):
        gaps.append(f"kit capped by {kt['capped']} ({kt.get('records_in_range',0):,} in range)")
    if kt.get("reason"):
        gaps.append(f"kit not placed: {kt['reason']}")
    if pr.get("reason"):
        gaps.append(f"props not placed: {pr['reason']}")
    if not scene.get("terrain", {}).get("built", True):
        gaps.append("terrain not built: " + str(scene["terrain"].get("reason")))
    if gaps:
        caption_lines.append(("Gaps: " + "; ".join(gaps), f_small))
    caption_lines.append((
        f"This sheet embeds the photograph above and is therefore a derivative work distributed "
        f"under the same licence ({ph.get('licence')}); the right-hand image is NYCSim output "
        f"(blender/verify/render_sheets.py).", f_small))

    tmp = Image.new("RGB", (10, 10))
    d0 = ImageDraw.Draw(tmp)
    max_w = sheet_w - margin * 2
    wrapped: list[tuple[str, object]] = []
    for text, font in caption_lines:
        for ln in _wrap(d0, text, font, max_w):
            wrapped.append((ln, font))
    line_h = 22
    caption_h = 16 + line_h * len(wrapped) + 12
    sheet_h = header_h + label_h + panel_h + caption_h + margin

    sheet = Image.new("RGB", (sheet_w, sheet_h), (250, 249, 246))
    d = ImageDraw.Draw(sheet)
    d.rectangle([0, 0, sheet_w, header_h], fill=(24, 26, 30))
    d.text((margin, 15), f"{record.get('name') or slug}", font=f_title, fill=(245, 245, 245))
    d.text((sheet_w - margin - d.textlength(slug, font=f_small), 22), slug, font=f_small, fill=(160, 165, 175))

    y0 = header_h + label_h
    d.text((margin, header_h + 8), "REFERENCE PHOTOGRAPH", font=f_label, fill=(40, 44, 52))
    d.text((margin + panel_w + gap, header_h + 8), "NYCSIM RENDER", font=f_label, fill=(40, 44, 52))
    sheet.paste(ref, (margin, y0))
    sheet.paste(ren, (margin + panel_w + gap, y0))
    d.rectangle([margin - 1, y0 - 1, margin + panel_w, y0 + ref_h], outline=(200, 200, 200))
    d.rectangle([margin + panel_w + gap - 1, y0 - 1, margin + panel_w * 2 + gap, y0 + ren_h],
                outline=(200, 200, 200))

    ty = y0 + panel_h + 14
    d.line([margin, ty - 6, sheet_w - margin, ty - 6], fill=(210, 210, 210))
    for text, font in wrapped:
        d.text((margin, ty), text, font=font, fill=(35, 38, 44))
        ty += line_h

    out = outdir / "sheet.png"
    sheet.save(out)
    LOG.info("%s sheet written (%dx%d)", slug, sheet_w, sheet_h)
    return out


# --------------------------------------------------------------------------- index


GROUP_ORDER = {"viewpoint": 0, "drive_through": 1, "landmark": 2}


def _index_status(slug: str, cov: dict) -> tuple[str, str]:
    """(status, note) for one subject: what happened, and why if nothing did."""
    rec_path = COMPARISON_DIR / slug / "render.json"
    if rec_path.exists():
        try:
            rec = json.loads(rec_path.read_text())
        except Exception as exc:
            return "error", f"render.json unreadable: {exc}"
        if rec.get("status") == "rendered":
            b = rec["scene"]["buildings"]
            bits = [f"{b['tiles_imported']}/{b['tiles_wanted']} building tiles",
                    f"{rec['scene']['landmarks']['placed']} landmarks"]
            if rec["scene"].get("props", {}).get("placed"):
                bits.append(f"{rec['scene']['props']['placed']} props")
            if rec["scene"].get("kit", {}).get("placed"):
                bits.append(f"{rec['scene']['kit']['placed']} kit pieces")
            return "rendered", ", ".join(bits)
        return "error", str(rec.get("reason") or rec.get("status"))
    err = COMPARISON_DIR / slug / "render_error.txt"
    if err.exists():
        return "error", err.read_text().strip().splitlines()[0][:160]
    if cov.get("photos", 0) == 0:
        return "not rendered", "no licensed reference photograph on disk for this subject"
    if cov["tiles_built"] == 0 and not cov["landmarks"]:
        return "not rendered", (f"no world geometry in frame: none of the {cov['tiles_wanted']} "
                                f"tiles in the {cov['radius_m']:.0f} m radius has a building shell "
                                f"yet and no landmark model reaches the frame")
    if cov.get("interior"):
        return "not rendered", "interior view; no interiors are modelled"
    return "not rendered", (f"queued: {cov['tiles_built']}/{cov['tiles_wanted']} building tiles and "
                            f"{len(cov['landmarks'])} landmark model(s) available, not yet rendered")


def write_index(slugs: Sequence[str]) -> Path:
    """Rebuild ``docs/verification/comparison/INDEX.md`` from what is on disk."""
    rows = []
    for slug in slugs:
        cov = coverage(slug)
        status, note = _index_status(slug, cov)
        rows.append((cov, status, note))
    rows.sort(key=lambda r: (GROUP_ORDER.get(r[0]["group"], 9), r[0]["slug"]))

    mandated = {s: name for name, ss in MANDATED_VIEWPOINTS.items() for s in ss}
    drive = {s: name for name, ss in DRIVE_THROUGH_AREAS.items() for s in ss}
    done = sum(1 for _, st, _ in rows if st == "rendered")

    lines = [
        "# Comparison sheets — index",
        "",
        f"Every subject in `docs/verification/reference/` with its comparison status. "
        f"{done} of {len(rows)} subjects have a sheet at "
        f"`docs/verification/comparison/<slug>/sheet.png`, each with its own `assessment.md`, "
        f"the raw `render.png` and the `render.json` that records the camera, the Sun and every "
        f"piece of world data that went into the frame.",
        "",
        "Generated by `python3 blender/verify/render_sheets.py --write-index`.",
        "",
        "| subject | group | status | sheet | what is in the frame / why not |",
        "|---|---|---|---|---|",
    ]
    for cov, status, note in rows:
        slug = cov["slug"]
        tag = ""
        if slug in mandated:
            tag = f" **[mandated: {mandated[slug]}]**"
        elif slug in drive:
            tag = f" *[drive-through: {drive[slug]}]*"
        sheet = f"[sheet]({slug}/sheet.png)" if status == "rendered" else "—"
        name = (cov.get("name") or slug).replace("|", "/")
        lines.append(f"| [{name}](../reference/{slug}/meta.json){tag} | {cov['group']} | "
                     f"{status} | {sheet} | {note.replace('|', '/')} |")
    lines += ["", f"Rebuilt {dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')}.", ""]
    COMPARISON_DIR.mkdir(parents=True, exist_ok=True)
    out = COMPARISON_DIR / "INDEX.md"
    out.write_text("\n".join(lines))
    LOG.info("INDEX.md written: %d subjects, %d rendered", len(rows), done)
    return out


# --------------------------------------------------------------------------- CLI


def coverage(slug: str) -> dict:
    """What world data exists for a subject, without building anything.

    Answers the question the INDEX has to answer: can this viewpoint be rendered at all, and if
    the answer is "only partly", which tiles of building shells are missing.
    """
    import scene as vscene
    from nycsim_pipeline.crs import lonlat_to_tm

    meta = load_meta(slug)
    vp = meta["viewpoint"]
    x, y = (float(v) for v in lonlat_to_tm(vp["lon"], vp["lat"]))
    subject = meta.get("subject") or {}
    subj_dist = None
    if subject.get("lat") is not None:
        sx, sy = (float(v) for v in lonlat_to_tm(subject["lon"], subject["lat"]))
        subj_dist = math.hypot(sx - x, sy - y)
    if slug in RADIUS_OVERRIDES:
        radius = RADIUS_OVERRIDES[slug][0]
    else:
        radius = max(500.0, min(3000.0, (subj_dist or 200.0) * 1.6 + 400.0))

    # The near field decides whether a frame is meaningful; count shells within 600 m as well
    # as over the whole scene radius.
    def tile_stats(r):
        want = vscene.tiles_in_radius(x, y, r)
        built = [t for t in want if (vscene.TILES_GLB / vscene.tile_name(*t) / "tile_buildings.glb").exists()]
        return len(want), len(built)

    want_all, built_all = tile_stats(radius)
    want_near, built_near = tile_stats(min(radius, 600.0))
    terr = vscene.tiles_in_radius(x, y, radius)
    terr_built = sum(1 for t in terr
                     if (vscene.TILES_DATA / vscene.tile_name(*t) / "terrain.png").exists())

    lms = []
    for e in vscene.load_landmark_catalog():
        ox, oy = float(e["origin_tm"][0]), float(e["origin_tm"][1])
        b = e.get("bounds_local_m") or {}
        bmin, bmax = b.get("min", [0, 0, 0]), b.get("max", [0, 0, 0])
        nx = min(max(x, ox + bmin[0]), ox + bmax[0])
        ny = min(max(y, oy + bmin[1]), oy + bmax[1])
        if math.hypot(nx - x, ny - y) <= radius:
            lms.append(e["id"])
    photo = pick_reference_photo(meta)
    return {"slug": slug, "name": meta.get("name"), "group": meta.get("group"),
            "night": bool(meta.get("night")), "interior": bool(meta.get("interior")),
            "radius_m": radius, "subject_distance_m": None if subj_dist is None else round(subj_dist, 1),
            "tiles_wanted": want_all, "tiles_built": built_all,
            "tiles_wanted_near": want_near, "tiles_built_near": built_near,
            "terrain_tiles": len(terr), "terrain_built": terr_built,
            "landmarks": sorted(lms), "photos": len([p for p in meta.get("photos", [])
                                                     if (REFERENCE_DIR / slug / p["file"]).exists()]),
            "reference_photo": None if photo is None else photo["file"]}


def resolve_slugs(args) -> list[str]:
    known = list_slugs()
    if args.slugs:
        want = [s.strip() for s in args.slugs.split(",") if s.strip()]
        bad = [s for s in want if s not in known]
        if bad:
            raise SystemExit(f"unknown slug(s): {', '.join(bad)}")
        return want
    if args.mandated:
        return [s for v in MANDATED_VIEWPOINTS.values() for s in v if s in known]
    if args.drive:
        return [s for v in DRIVE_THROUGH_AREAS.values() for s in v if s in known]
    if args.group:
        return [s for s in known if load_meta(s).get("group") == args.group]
    return known


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--slugs", default=None, help="comma-separated reference slugs")
    ap.add_argument("--group", default=None, choices=["viewpoint", "drive_through", "landmark"])
    ap.add_argument("--mandated", action="store_true", help="the seven brief-mandated viewpoints")
    ap.add_argument("--drive", action="store_true", help="the five drive-through areas")
    ap.add_argument("--samples", type=int, default=DEFAULT_SAMPLES)
    ap.add_argument("--width", type=int, default=RENDER_WIDTH)
    ap.add_argument("--threads", type=int, default=None)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--skip-existing", action="store_true", help="skip slugs that already have a render.png")
    ap.add_argument("--compose-only", action="store_true", help="rebuild sheets from existing renders")
    ap.add_argument("--dry-run", action="store_true", help="print the plan without rendering")
    ap.add_argument("--coverage", action="store_true",
                    help="report what world data exists per subject and exit")
    ap.add_argument("--write-index", action="store_true",
                    help="rebuild docs/verification/comparison/INDEX.md and exit")
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s",
                        datefmt="%H:%M:%S")
    slugs = resolve_slugs(a)
    if a.limit:
        slugs = slugs[:a.limit]
    if a.coverage:
        print(json.dumps([coverage(s) for s in slugs], indent=1))
        return 0
    if a.write_index:
        write_index(slugs)
        return 0
    LOG.info("%d subject(s): %s", len(slugs), ", ".join(slugs))

    done, failed = [], []
    for slug in slugs:
        outdir = COMPARISON_DIR / slug
        if a.compose_only:
            if compose_sheet(slug) is not None:
                done.append(slug)
            else:
                failed.append(slug)
            continue
        if a.skip_existing and (outdir / "render.png").exists() and (outdir / "sheet.png").exists():
            LOG.info("%s already rendered, skipping", slug)
            done.append(slug)
            continue
        try:
            rec = render_subject(slug, samples=a.samples, threads=a.threads, width=a.width,
                                 dry_run=a.dry_run)
        except Exception as exc:
            LOG.exception("%s failed", slug)
            outdir.mkdir(parents=True, exist_ok=True)
            (outdir / "render_error.txt").write_text(f"{type(exc).__name__}: {exc}\n")
            failed.append(slug)
            continue
        if a.dry_run:
            print(json.dumps(rec, indent=1, sort_keys=True))
            done.append(slug)
            continue
        if rec.get("status") != "rendered":
            failed.append(slug)
            (outdir / "render_error.txt").write_text(json.dumps(rec, indent=1))
            continue
        compose_sheet(slug, rec)
        done.append(slug)
    LOG.info("done: %d, failed: %d%s", len(done), len(failed),
             (" (" + ", ".join(failed) + ")") if failed else "")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
