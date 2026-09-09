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
          str(REPO_ROOT / "services"), str(REPO_ROOT / "tools"), str(REPO_ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)

# The frustum arithmetic behind the caption's landmark count.  ``sheet_facts`` is plain Python and
# imports no Blender, so the composer can use it on a machine that only has the rendered PNG.
import sheet_facts  # noqa: E402

LOG = logging.getLogger("nycsim.verify.render")

REFERENCE_DIR = REPO_ROOT / "docs" / "verification" / "reference"
COMPARISON_DIR = REPO_ROOT / "docs" / "verification" / "comparison"
FONT_DIR = REPO_ROOT / "assets" / "fonts" / "Overpass"

NY_TZ = "America/New_York"

# Lighting model constants.  SUN_CALIBRATION and REFERENCE_KEY_W were measured with
# blender/verify/ test renders of a 0.26-albedo ground: they put a clear-midday sunlit ground at
# about 150/255 through Filmic, which is where a correctly exposed photograph of concrete sits.
#: One seed for every agent frame in the set.  The traffic and pedestrian simulations are
#: deterministic in their seed and inputs, so a fixed seed means a re-render reproduces the same
#: frame; the seed is printed on every sheet so it can be changed and the frame re-checked.
AGENT_SEED = 20260907
#: How far agents are placed.  Beyond these the figures are a few pixels and the triangles are
#: better spent on the facades behind them.
AGENT_VEHICLE_RADIUS_M = 320.0
AGENT_PED_RADIUS_M = 200.0
#: Distinct NPC bodies imported per frame.  ``None`` means every body the wardrobe baked.
#:
#: This read 12, under the reasoning that "the 24 exported bodies through three walk phases already
#: give more distinct figures than a frame ever holds".  Both halves were wrong.  The wardrobe bakes
#: **36** bodies, not 24, and a frame holds **229 people**, not 36: at 12 bodies each one stands in
#: the same frame about nineteen times, two of the twelve wear medical scrubs, and archetypes 12 to
#: 35 -- including every coat the J53 fix added -- could not appear at all (DEVIATIONS J62).
AGENT_NPC_ARCHETYPES: int | None = None

SOLAR_CONSTANT_W = 1361.0
ATMOSPHERIC_TRANSMITTANCE = 0.7
#: Divides the direct normal irradiance to put a clear midday frame where a correctly exposed
#: photograph lands -- the docstring of :func:`setup_world_and_sun` states the target as a
#: 0.26-albedo sunlit ground at about 150/255 through Filmic, and that target has not changed.
#:
#: It read 540 and had been solved with the sky delivering 1.6 times the Sun's light (J67).  With
#: the sky corrected, 540 puts that patch at **118/255** and the whole city two stops under.  Solved
#: again against the same target, with Sun and sky exactly as the renderer now configures them:
#: 540 -> 118, 300 -> 147, 200 -> 167, 140 -> 183, 100 -> 197, 70 -> 211, 50 -> 221, crossing
#: 150/255 at **286**.  The sky strength is derived from this constant, so the direct-to-diffuse
#: ratio is unchanged by the re-solve -- only the overall level moves.
SUN_CALIBRATION = 286.0
DIFFUSE_KEY_W = 90.0
REFERENCE_KEY_W = 681.0
SKY_STRENGTH_NIGHT = 0.5

#: The exposure a daylight frame is developed at is **metered on the frame**, the way every camera
#: that took a reference photograph metered its own: the median scene luminance of the linear
#: render is placed at middle grey.  It is not the fixed physical rule above, and this is why
#: (docs/DEVIATIONS.md J83).  Measured over the 164 daylight sheets of the v15 pass, the render sat
#: below the photograph by a near-constant display factor of 0.5-0.65 at *every* quantile -- the
#: brightest 5 % (0.62), the sky (0.47-0.66), the median pixel (0.52) -- and a per-sheet fit of
#: render = gain * photo^gamma gave gamma 1.07 and gain 0.59: a level, not a contrast.  The level
#: was set by SUN_CALIBRATION, solved so that a sunlit 0.26-albedo ground lands at 150/255, and the
#: renders do land there (p95 0.592 on the fourteen best-lit frames); the photographs put their
#: median pixel at 0.454 in display -- 0.18 in linear light, middle grey, which is what average
#: metering does -- and their brightest 5 % at 0.875.  So the physical Sun and sky are kept exactly
#: as calibrated (the direct-to-diffuse balance matches the photographs: sky/sunlit 0.58 against
#: 0.61), and the *development* is metered.  The stops the metering needs are published on every
#: sheet: they are the physical measurement -- a canyon that needs +4 stops to read as a picture
#: is a canyon four stops darker than the one photographed -- and the assessments read them.
METER_TARGET_LINEAR = 0.18
#: Clamps, so a frame from inside a wall cannot be developed into a picture: +6 stops is a scene
#: sixty-four times darker than a photographable one, and no reference photograph in the set was
#: taken in one.  -3 stops is the corresponding ceiling for a frame that is mostly sky.
METER_MIN_STOPS = -3.0
METER_MAX_STOPS = 6.0
#: Above this the frame is published with a warning in the record: the picture is readable but the
#: scene was under-lit by more than a photographer could recover without a tripod.
METER_UNDERLIT_STOPS = 4.0


def meter_exposure(lin_rgb) -> dict:
    """The stops that put a linear frame's median luminance at middle grey, and the evidence.

    ``lin_rgb`` is an (H, W, 3+) float array of scene-linear Rec.709 values.  Returns the metered
    stops (clamped, with the unclamped value beside it), the median and log-average luminance the
    decision was made on, and the linear percentiles a reader needs to see the physical frame
    before any development touched it.  Pure, so that it can be tested without a render.
    """
    import numpy as np
    a = np.asarray(lin_rgb, dtype=np.float64)
    lum = 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]
    lum = lum[np.isfinite(lum)]
    if lum.size == 0:
        return {"stops": 0.0, "stops_unclamped": 0.0, "median_linear": None, "log_average_linear": None,
                "note": "no finite pixels to meter"}
    median = float(np.median(lum))
    logavg = float(np.exp(np.mean(np.log(np.clip(lum, 1e-6, None)))))
    raw = math.log2(METER_TARGET_LINEAR / max(median, 1e-6))
    stops = min(METER_MAX_STOPS, max(METER_MIN_STOPS, raw))
    out = {"stops": round(stops, 3), "stops_unclamped": round(raw, 3),
           "target_linear": METER_TARGET_LINEAR,
           "median_linear": round(median, 6), "log_average_linear": round(logavg, 6),
           "linear_p05": round(float(np.percentile(lum, 5)), 6),
           "linear_p50": round(median, 6),
           "linear_p95": round(float(np.percentile(lum, 95)), 6),
           "rule": "median scene luminance of the linear frame placed at middle grey (0.18); "
                   "the stops are the measurement, the development is the consequence"}
    if raw > METER_MAX_STOPS or raw < METER_MIN_STOPS:
        out["note"] = (f"the frame wanted {raw:+.2f} stops and was held at {stops:+.2f}: a scene this "
                       f"far from a photographable level is not developed into a picture of one")
    elif raw > METER_UNDERLIT_STOPS:
        out["note"] = (f"under-lit: the scene needed {raw:+.2f} stops to read as a picture, more than "
                       f"the {METER_UNDERLIT_STOPS:.0f} a photographer recovers hand-held; the frame "
                       f"is published and this is the number to read it by")
    return out

#: Horizontal irradiance a **strength 1.0** Nishita sky delivers, in the same Blender units the Sun
#: lamp uses, by Sun elevation.  Measured rather than assumed: a 0.18-albedo lambertian plane, sky
#: only, no bounces, Standard view transform, four stops down so nothing clips, and the irradiance
#: read back as ``mean * pi / albedo``.  The Sun path checks out against the same method to four
#: decimal places, which is what makes the sky reading trustworthy.
SKY_IRRADIANCE_AT_UNIT_STRENGTH: tuple[tuple[float, float], ...] = (
    (5.0, 3.8359), (10.0, 5.7250), (20.0, 7.7634), (30.0, 8.8130),
    (45.0, 9.6758), (60.0, 10.1528), (69.5, 10.3250), (80.0, 10.4308))


def sky_strength_for(sun_elevation_deg: float) -> float:
    """Sky strength that delivers ``DIFFUSE_KEY_W`` of diffuse light, as the exposure model assumes.

    This was the constant ``SKY_STRENGTH_DAY = 0.25``, and it was carrying no calibration while
    setting the one thing that decides how much contrast a frame has.  Measured on a white plane,
    the renderer was configuring a **direct-to-diffuse ratio of 0.63 : 1** at a 69.5 deg Sun and
    **0.04 : 1** at 5 deg -- every daylight frame in the project lit like an overcast day, with no
    highlights and shadows the sky filled in from every direction.

    The correct number is not a matter of taste and it is not fitted to a photograph: two lines
    above, the exposure this same function computes reads ``key = dni * sin(elevation) +
    DIFFUSE_KEY_W`` with ``DIFFUSE_KEY_W = 90`` W/m2 -- so the model already states that diffuse
    light is 90 W/m2 against roughly 880 direct at high Sun, a ratio near 10 : 1, and the sky was
    delivering 1.6 times the Sun instead.  This makes the sky deliver what the rest of the function
    already assumes it delivers (docs/DEVIATIONS.md J67).
    """
    e = max(0.0, float(sun_elevation_deg))
    tbl = SKY_IRRADIANCE_AT_UNIT_STRENGTH
    if e <= tbl[0][0]:
        unit = tbl[0][1]
    elif e >= tbl[-1][0]:
        unit = tbl[-1][1]
    else:
        unit = tbl[-1][1]
        for (e0, v0), (e1, v1) in zip(tbl, tbl[1:]):
            if e0 <= e <= e1:
                unit = v0 + (v1 - v0) * (e - e0) / (e1 - e0)
                break
    return (DIFFUSE_KEY_W / SUN_CALIBRATION) / unit
# Calibrated against the reference photograph's own histogram, in an A/B where only this constant
# moved (blender/verify -- times_square_duffy_south_night, the one subject of the 57 whose Sun is
# below the horizon, so nothing else in the set can move with it).  The measure is the mean gap
# between the render's and the photograph's luminance CDFs, which is a distance in luma units and
# not a single statistic that can be gamed.  Sixteen exposures from -3.0 to +2.5 stops: the gap
# falls from 0.271 at the +2.0 this used to be to a flat minimum of 0.072 between -1.5 and -1.0,
# reached at -1.25.  The frame's median luminance goes 0.541 -> 0.176 against the photograph's
# 0.151, and the share of the frame below 0.20 goes 0.132 -> 0.535 against its 0.622.
#
# What this does *not* fix, stated because the number moves the wrong way: the photograph clips
# 5.07 % of its area above 0.95 and the render clips 0.31 % at +2.0 and 0.00 % here.  Stopping
# down cannot buy highlights.  The render has no clipped highlights because the Filmic shoulder
# only reaches 1.0 asymptotically and the signage emission is calibrated on the *daylight* frame
# (deliberately, by the stage that set it), so no lit sign in the frame is bright enough to cross.
# Getting both would take a different view transform or a night-specific emission, and neither is
# an exposure.  SKY_STRENGTH_NIGHT was A/B'd in the same pass and is very nearly inert here: 0.5
# against 0.1 -- a five-fold change -- moves the median by 0.0026 and the CDF gap by 0.002, because
# at a Sun elevation of -9.5 deg the Nishita sky is dim and this portrait frame is filled with
# buildings rather than sky.  It is left where it was rather than tuned to no effect.
NIGHT_EXPOSURE_STOPS = -1.25
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


#: Distance bands, in metres, for choosing a ``drive_through`` item's reference photograph.
#:
#: A drive-through sheet is a comparison of *one block*, and the chooser's key had no distance term
#: at all -- so a photograph 3,854 m up the same avenue, of the Dollar Savings Bank at East Fordham
#: Road, outranked every photograph of Grand Concourse at East 165th Street because it carried a
#: full EXIF timestamp.  A binary gate does not fix that on its own: all three of that item's
#: photographs are beyond any sane radius, so the gate ties them and the timestamp decides again.
#:
#: So the distance is **graded**, and the band ranks above the timestamp for this group.  That is a
#: stated judgement: a photograph of the wrong block cannot be repaired by a precise clock, while an
#: assumed hour is an approximation the sheet already declares.  The first edge, 250 m, is the same
#: ``PHOTO_GPS_SANITY_M`` the render uses to decide a GPS fix is too far to stand the camera on, so
#: there is one definition of "the same view" rather than two (docs/DEVIATIONS.md J60).
DRIVE_THROUGH_PHOTO_BANDS_M = (250.0, 600.0, 1500.0)

#: Band for a photograph that carries no GPS at all.  **Not 0.** An unknown position is not evidence
#: of nearness, and scoring it as though it were picked a FreshDirect delivery truck over a
#: photograph taken 46 m from the Stuyvesant Avenue viewpoint, purely because the truck had a full
#: EXIF timestamp and the streetscape carried only a year.  Ranking it third of four says what is
#: true: worse than a photograph known to be on the block, better than one known to be a mile away.
DRIVE_THROUGH_PHOTO_UNKNOWN_BAND = 2


def _photo_offset_m(vp: dict, photo: dict) -> float | None:
    """Metres from a photograph's own EXIF GPS to the item's viewpoint, or None when it carries no fix."""
    g = (photo or {}).get("camera_gps") or {}
    if g.get("lat") is None or g.get("lon") is None:
        return None
    from nycsim_pipeline.crs import lonlat_to_tm

    vx, vy = (float(v) for v in lonlat_to_tm(vp["lon"], vp["lat"]))
    px, py = (float(v) for v in lonlat_to_tm(g["lon"], g["lat"]))
    return math.hypot(px - vx, py - vy)


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
        # The gate is evaluated at the instant the render will actually be lit at -- the chosen
        # hour for a photograph without a time, a night hour for a night item -- and not at the old
        # fixed 09:30, which could pass a photograph the render then lit at a different hour.
        when, _ = photo_instant(p, lat=vp["lat"], lon=vp["lon"], azimuth_deg=az, night=night)
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
        # A drive-through sheet is a comparison of *this block*, and the key above has no distance
        # term at all -- so a photograph 3,854 m up the same avenue, of the Dollar Savings Bank at
        # East Fordham Road, outranked every photograph of Grand Concourse at East 165th Street
        # because it carried a better timestamp.  Distance is a *gate* rather than another sort
        # term, and only for the group where it means something: a landmark is legitimately
        # photographed from 1.8 km and a fire hydrant from anywhere in the city, so those groups
        # keep the old ordering exactly (docs/DEVIATIONS.md J60).
        # A landmark is legitimately photographed from 1.8 km and a fire hydrant from anywhere in
        # the city, so every other group keeps the old ordering exactly.
        band = 0
        if str(meta.get("group") or "") == "drive_through":
            off = _photo_offset_m(vp, p)
            band = (DRIVE_THROUGH_PHOTO_UNKNOWN_BAND if off is None
                    else sum(1 for edge in DRIVE_THROUGH_PHOTO_BANDS_M if off > edge))
        key = (lit_bad, band, 0 if has_time else 1, lit_tier, conf, err)
        if best_key is None or key < best_key:
            best, best_key = p, key
    return best


#: Hours an assumed instant may be chosen from, local.  Civil daylight in New York on 21 June runs
#: well past these, but a sheet wants the Sun *up* rather than grazing: below about 20 deg of
#: elevation the whole street is shadow whatever the bearing, which is the condition this rule
#: exists to avoid.
ASSUMED_HOUR_RANGE = (8, 18)


#: The hour a **night** item with no recorded time is given.  22:00 local is after civil dusk on
#: every date of the year in New York (the latest civil dusk, at the June solstice, is about 21:05
#: EDT), so the Sun is below -6 deg and no lamp is added -- which is what a night frame is for.
NIGHT_ASSUMED_HOUR = 22


def _lit_hour(lat: float, lon: float, day: dt.date, azimuth_deg: float | None, tz,
              *, night: bool = False) -> tuple[int, int, str]:
    """The hour of ``day`` whose Sun best lights a camera looking along ``azimuth_deg``.

    **Why this is chosen rather than fixed.** When a photograph carries no time, the hour is an
    assumption either way -- there is nothing to measure.  It was fixed at 09:30, and 09:30 on
    21 June puts the Sun at azimuth 95 deg: almost due east, which is the worst bearing there is
    for Manhattan's north-south grid.  Measured over the sheets rendered so far, a frame on an
    assumed instant has a median luminance of **0.12** against **0.29** for one on the
    photograph's own instant, and the fallback has produced outright refusals -- Federal Hall at
    mean 0.021 on Wall Street (docs/DEVIATIONS.md J80).  A sheet whose street is in shadow tests
    the shadow and not the city.

    So the *same* assumption is made more usefully: keep the date, and pick the hour whose solar
    azimuth is nearest to shining **along the view direction** -- lighting what the camera looks
    at -- while the Sun is high enough to reach a street floor at all.  The record says the hour
    was chosen and why, and every assessment of such a sheet states that its luminance comparison
    is therefore not evidence about the render.  Choosing an informative arbitrary value and
    declaring it beats choosing an uninformative one and declaring it.

    With no azimuth to aim at, the hour that puts the Sun highest is used, which is noon.
    """
    if night:
        # A night item is not lit by the Sun at all.  The hour chooser below has no business here:
        # it once handed a night item an 08:30 Sun at 32 deg, with the night sky strength and a Sun
        # lamp both switched on (docs/DEVIATIONS.md J80, amendment).
        return NIGHT_ASSUMED_HOUR, 0, (f"and {NIGHT_ASSUMED_HOUR:02d}:00 **chosen**, not measured: a night "
                                        f"item, given an hour after civil dusk on every date of the year "
                                        f"in New York, so the Sun is down and nothing but the city's own "
                                        f"emissive content lights the frame")
    from nycsim_live import astronomy
    obs = astronomy.Observer(lat, lon, 20.0)
    best = None
    for hour in range(ASSUMED_HOUR_RANGE[0], ASSUMED_HOUR_RANGE[1] + 1):
        when = dt.datetime.combine(day, dt.time(hour, 30), tzinfo=tz)
        pos = astronomy.solar_position(when.astimezone(dt.timezone.utc), obs)
        if pos.elevation < 20.0:
            continue
        if azimuth_deg is None:
            score = -pos.elevation                      # highest Sun
        else:
            # The Sun lights what the camera looks at when it is *behind* the camera, i.e. its
            # azimuth is near the view azimuth.  Ties break towards the higher Sun.
            off = abs((pos.azimuth - float(azimuth_deg) + 180.0) % 360.0 - 180.0)
            score = (off, -pos.elevation)
        if best is None or score < best[0]:
            best = (score, hour, pos)
    if best is None:                                    # no hour clears 20 deg: keep the old fixed one
        return 9, 30, "and 09:30 kept because no hour on that date puts the Sun above 20 deg"
    _, hour, pos = best
    if azimuth_deg is None:
        why = (f"and {hour:02d}:30 chosen as the highest Sun of that day ({pos.elevation:.0f} deg), "
               f"because the item names no view direction to light")
    else:
        off = abs((pos.azimuth - float(azimuth_deg) + 180.0) % 360.0 - 180.0)
        why = (f"and {hour:02d}:30 **chosen**, not measured: of the hours that put the Sun above "
               f"20 deg it is the one whose bearing ({pos.azimuth:.0f} deg) comes closest to the "
               f"view azimuth ({float(azimuth_deg):.0f} deg), {off:.0f} deg off, so the Sun is "
               f"behind the camera and lights what it looks at")
    return hour, 30, why


def photo_instant(photo: dict, *, lat: float | None = None, lon: float | None = None,
                  azimuth_deg: float | None = None, night: bool = False) -> tuple[dt.datetime, str]:
    """Local New York datetime for a photo, plus a note on where it came from.

    Where the photograph carries a time, that time is used and nothing here is a choice.  Where it
    does not, the hour is chosen to light the view rather than fixed at 09:30, and the note says
    so in as many words (:func:`_lit_hour`, docs/DEVIATIONS.md J80).
    """
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

    def pick(day: dt.date, prefix: str) -> tuple[dt.datetime, str]:
        if night:
            hour, minute, why = _lit_hour(lat or 0.0, lon or 0.0, day, azimuth_deg, tz, night=True)
            return dt.datetime.combine(day, dt.time(hour, minute), tzinfo=tz), f"{prefix}, {why}"
        if lat is None or lon is None:
            return dt.datetime.combine(day, dt.time(9, 30), tzinfo=tz), f"{prefix}; 09:30 assumed"
        hour, minute, why = _lit_hour(lat, lon, day, azimuth_deg, tz)
        return dt.datetime.combine(day, dt.time(hour, minute), tzinfo=tz), f"{prefix}, {why}"

    try:
        return pick(dt.datetime.strptime(raw, "%Y-%m-%d").date(), "photograph date, no time")
    except ValueError:
        pass
    year = photo.get("year")
    if isinstance(year, int):
        return pick(dt.date(year, 6, 21), "photograph year only, 21 June assumed")
    return pick(dt.date(2024, 6, 21), "no date recorded, 21 June 2024 assumed")


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
    bg.inputs["Strength"].default_value = (SKY_STRENGTH_NIGHT if night
                                          else sky_strength_for(sun_elevation_deg))

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

    # Zeroing the Alpha *default* does nothing when that socket is linked, and `mat_light_cone()`
    # links it to the gradient PNG's alpha channel -- so the cone stayed opaque, and with its
    # emission zeroed it rendered as a solid dark wedge standing in the street.  It shipped that way:
    # `drive_bronx_arthur_ave` had two of them filling a quarter of the frame, and the sheet's own
    # assessment said the black cones were gone.  Deleting the faces is what the props contact sheets
    # already do (`blender/props/contact_sheets.py:_light_cone_slots`) and it cannot fail the same
    # way, because there is no material state left to get wrong.
    cone_faces = _delete_light_cone_faces()
    return {"night": False, "cones_hidden": cones, "cone_faces_deleted": cone_faces,
            "lamps_switched_off": lamps,
            "note": "daylight frame: the modelled light-cone faces are deleted (their alpha is "
                    "texture-linked, so making the material transparent does not work) and "
                    "street-lamp lenses switched off (dusk-to-dawn control); signals and shopfront "
                    "emissives left on"}


def _delete_light_cone_faces() -> int:
    """Remove every polygon whose material is ``LIGHT_CONE`` from every mesh in the scene.

    The beam under a street lamp is a night-time visualisation, not an object, and it has no place
    in a daylight frame.  Faces rather than objects, because the lamp is one joined mesh: dropping
    the object would take the pole and the luminaire with it.  The importer suffixes duplicate
    material names (``LIGHT_CONE.003``), so the match is on the stem.
    """
    import bmesh
    import bpy
    removed = 0
    for me in bpy.data.meshes:
        if not me.materials:
            continue
        slots = {i for i, m in enumerate(me.materials)
                 if m is not None and (m.name or "").split(".")[0].upper() == "LIGHT_CONE"}
        if not slots:
            continue
        bm = bmesh.new()
        bm.from_mesh(me)
        doomed = [f for f in bm.faces if f.material_index in slots]
        if doomed:
            bmesh.ops.delete(bm, geom=doomed, context="FACES")
            removed += len(doomed)
            bm.to_mesh(me)
            me.update()
        bm.free()
    return removed


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


#: How far the chosen photograph's own EXIF GPS may sit from the item's recorded viewpoint before
#: it is treated as unreliable rather than as the better measurement.  The reference collector
#: searches Commons within ~120 m of each item, so a photograph whose GPS is a quarter of a
#: kilometre away is either mis-tagged or is not a picture of that viewpoint at all.
PHOTO_GPS_SANITY_M = 250.0

#: A view *of* a subject also accepts a photograph's GPS beyond that radius, when the photograph
#: stands on the same side of the subject to within this many degrees.  See :func:`view_origin`.
SAME_SIDE_DEG = 45.0

#: Slugs whose viewpoint is not a fixed place, with the radius their photographs' GPS may sit
#: inside and the reason.  Nothing is listed at present.  The Staten Island Ferry viewpoint was
#: tried here -- the deck of a moving vessel is a route, not a position -- and the result was
#: worse, not better: the chosen photograph's GPS puts the camera in the Hudson west of Battery
#: Park City, 699 m from the item's point, and from there Lower Manhattan spreads entirely to the
#: right of the frame while the reference photograph has the island on both sides of the axis.
#: The photograph's fix is wrong, or was taken at a different moment of the crossing; the item's
#: "about 1 nautical mile south of Whitehall Terminal" reproduces the reference and the EXIF fix
#: does not.  Measured beats assumed only when the measurement is right.
MOVING_VIEWPOINTS: dict[str, tuple[float, str]] = {}


def view_origin(meta: dict, photo: dict | None) -> tuple[float, float, str, float | None, bool]:
    """Where the camera stands: (lat, lon, why, metres from the recorded viewpoint, from_photo).

    The item's ``viewpoint`` is a nominal position typed by the reference collector; the chosen
    photograph usually carries the GPS position its own camera recorded.  Where both exist and
    agree to within :data:`PHOTO_GPS_SANITY_M`, the photograph's is the measurement and the item's
    is the estimate, so the render stands where the picture was taken.

    **Beyond that radius the test depends on what defines the view**, because the sanity radius
    measures the wrong thing for half the catalogue.  A ``landmark`` item is a view *of* something:
    its viewpoint is only an estimate of where such a photograph is taken from -- the catalogue
    generates it as a bearing and a distance from the subject -- so a photograph that stands
    **nearer to the subject** than that estimate, and **on the same side** of it (its bearing to the
    subject within :data:`SAME_SIDE_DEG` of the recorded view's), is the same view of the same thing
    and its own GPS is the better position however far it is from the estimate.  A ``viewpoint`` or
    ``drive_through`` item is a view *from* somewhere -- a ferry deck, a promenade railing, a named
    block -- and there the recorded position *is* the view, so the radius stands.

    That distinction is what the Williamsburg Bridge sheet needed: its photograph's GPS is 117 m
    from the Brooklyn tower and the item's viewpoint is 506 m from it, and the 389 m between the two
    put the camera half a kilometre too far back.  It is also why the Staten Island Ferry keeps its
    recorded position: that photograph's GPS is nearer the aim point too, but the item is a view
    from the bow deck of a vessel, and from the photograph's fix Lower Manhattan spreads entirely to
    one side of the frame while the reference has the island on both sides of the axis (measured
    when :data:`MOVING_VIEWPOINTS` was tried and left empty).

    Position and heading have to come from the same place.  The earlier version of this module
    took the *heading* from the photograph's GPS ("camera_gps_to_subject") while leaving the
    *position* at the item's viewpoint, which for Washington Street in DUMBO aimed a camera 46 m
    south-east of the photographer along the bearing that only works from the photographer's own
    spot -- the two halves of the sheet then face different ways, which is exactly the fault this
    is meant to prevent.
    """
    vp = meta["viewpoint"]
    g = (photo or {}).get("camera_gps") or {}
    if g.get("lat") is None or g.get("lon") is None:
        return (float(vp["lat"]), float(vp["lon"]),
                "the item's recorded viewpoint (this photograph carries no camera GPS)",
                None, False)
    from nycsim_pipeline.crs import lonlat_to_tm
    vx, vy = (float(v) for v in lonlat_to_tm(vp["lon"], vp["lat"]))
    px, py = (float(v) for v in lonlat_to_tm(g["lon"], g["lat"]))
    d = math.hypot(px - vx, py - vy)
    limit, why_limit = MOVING_VIEWPOINTS.get(meta.get("slug", ""), (PHOTO_GPS_SANITY_M, ""))
    subject_rule = ""
    if d > limit:
        subject_rule = _nearer_the_subject(meta, vx, vy, px, py)
        if not subject_rule:
            return (float(vp["lat"]), float(vp["lon"]),
                    (f"the item's recorded viewpoint; this photograph's own EXIF GPS is {d:,.0f} m "
                     f"away, past the {limit:,.0f} m at which it could still be the same view, so "
                     f"the camera was not stood on it.  That is a statement about this pairing and "
                     f"not about the photograph: a fix this far out is usually correct and simply "
                     f"of somewhere else"), d, False)
    return (float(g["lat"]), float(g["lon"]),
            (f"this photograph's own EXIF camera GPS ({g['lat']:.5f}, {g['lon']:.5f}), {d:,.0f} m "
             f"from the item's recorded viewpoint -- the position the picture was taken from"
             + (f" ({why_limit})" if why_limit else "") + subject_rule),
            d, True)


def _nearer_the_subject(meta: dict, vx: float, vy: float, px: float, py: float) -> str:
    """Why a landmark photograph's GPS is kept past the sanity radius, or "" if it is not.

    Only for an item that is a view *of* a point subject.  Two tests, both against the subject
    rather than against the viewpoint estimate: the photograph must stand no farther from the
    subject than the estimate does, and on the same side of it.
    """
    if str(meta.get("group") or "") != "landmark":
        return ""
    subject = meta.get("subject") or {}
    if subject.get("lat") is None or subject.get("lon") is None:
        return ""
    from nycsim_pipeline.crs import lonlat_to_tm
    sx, sy = (float(v) for v in lonlat_to_tm(subject["lon"], subject["lat"]))
    d_vp = math.hypot(vx - sx, vy - sy)
    d_ph = math.hypot(px - sx, py - sy)
    if d_ph > d_vp:
        return ""
    b_vp = math.degrees(math.atan2(sx - vx, sy - vy)) % 360.0
    b_ph = math.degrees(math.atan2(sx - px, sy - py)) % 360.0
    delta = abs((b_ph - b_vp + 180.0) % 360.0 - 180.0)
    if delta > SAME_SIDE_DEG:
        return ""
    name = subject.get("name") or "the subject"
    return (f".  It is past the {PHOTO_GPS_SANITY_M:,.0f} m sanity radius, but this item is a view "
            f"*of* {name} and the photograph stands {d_ph:,.0f} m from it against the recorded "
            f"viewpoint's {d_vp:,.0f} m, on the same side to {delta:.1f} deg, so the measurement is "
            f"kept and the estimate is not")


def view_azimuth(slug: str, meta: dict, photo: dict, lat: float, lon: float, *,
                 origin_is_photo: bool = False) -> tuple[float, str]:
    """The compass bearing the render should face from (lat, lon), and why.

    Two sources, in order of authority:

    1. the bearing from the camera position actually used to the item's ``subject`` coordinate --
       the subject is what the photograph is of, so this is measured rather than assumed.  When
       the camera stands on the photograph's own GPS this bearing is used unconditionally, because
       position and heading then come from the same measurement; when the camera stands on the
       item's nominal viewpoint the recorded azimuth is kept unless the subject bearing disagrees
       with it by more than 20 deg, which means the recorded azimuth points somewhere the subject
       is not.
    2. the item's recorded ``azimuth_deg``.

    The bearing is always recomputed from the position the camera ends up at, never copied from
    the metadata, so heading and position can never come from different places.
    """
    recorded = float(meta["viewpoint"]["azimuth_deg"])
    subject = meta.get("subject") or {}
    if subject.get("lat") is not None and subject.get("lon") is not None:
        from nycsim_pipeline.crs import lonlat_to_tm
        vx, vy = (float(v) for v in lonlat_to_tm(lon, lat))
        sx, sy = (float(v) for v in lonlat_to_tm(subject["lon"], subject["lat"]))
        bearing = math.degrees(math.atan2(sx - vx, sy - vy)) % 360.0
        delta = abs((bearing - recorded + 180.0) % 360.0 - 180.0)
        name = subject.get("name") or "the subject"
        if origin_is_photo:
            return bearing, (f"{bearing:.1f} deg, the bearing from this photograph's own GPS "
                             f"position to {name}; heading and position both come from the "
                             f"photograph.  The item's recorded azimuth is {recorded:.1f} deg, "
                             f"{delta:.1f} deg away, and belongs to its nominal viewpoint")
        if delta > 20.0:
            return bearing, (f"{bearing:.1f} deg, the bearing from the camera position used to "
                             f"{name}; the item's recorded azimuth of {recorded:.1f} deg is "
                             f"{delta:.0f} deg away from its own subject and was not used")
        return recorded, (f"{recorded:.1f} deg as recorded; it agrees with the bearing from the "
                          f"camera position used to {name} ({bearing:.1f} deg) to {delta:.1f} deg")
    ev = (photo or {}).get("estimated_viewpoint") or {}
    conf = ev.get("confidence") or "unknown"
    return recorded, (f"{recorded:.1f} deg as recorded in meta.json.  This item names no subject "
                      f"and the reference photograph's own view direction was not derived from the "
                      f"image (confidence: {conf}), so the two halves of this sheet are not "
                      f"guaranteed to face the same way -- compare them on street width, storey "
                      f"height and material, not on composition")


def subject_top(meta: dict, cam_x: float, cam_y: float, sampler,
                landmarks: Sequence[dict], out: dict | None = None) -> tuple[float, float, str] | None:
    """(distance, **absolute NYC_TM elevation** of the subject's top, source).

    The second element is a world z, not a height above the camera: ``choose_lens`` reads it as one
    (``rise = top_z - cam_z``) and always has.  This line used to say "above the camera's own eye
    level", and the sightline probe believed it and added the camera's elevation to an absolute one
    (docs/DEVIATIONS.md J57).

    The height is **measured off the thing that stands there**, by dropping rays onto a small ring
    about the subject's own coordinate (:func:`camera.subject_height_probe`).  Two rules preceded
    that and both are recorded, because each was a correct measurement of something other than the
    subject:

    * a nominal 10 m where no model was found, which aimed the Manhattan Bridge's Brooklyn tower --
      106.68 m of steel -- at 4.8 m above the water and reported it invisible over a frame with the
      tower in the middle of it (J72);
    * the height published by the nearest landmark model **origin** within 120 m, which is a
      model's own centre and so is nowhere near the part of a long or wide model a photograph is
      of.  38 of the 138 reference items that name a subject have no origin within 120 m while
      standing inside the model's own **bounding box**; for at least 19 of them a model's actual
      mesh is within 60 m (J74).

    Matching by *name* was tried and is worse: the catalogue's 93 entries include district and site
    models, so "Central Park Tower" matches ``b_central_park_walls_gates`` -- a **3 m** park wall
    2,368 m away -- and "Queens Museum" matches ``c_brooklyn_museum`` in another borough.  Matching
    by *bounding box* is worse still: ``b_brooklyn_bridge``'s box contains the Manhattan Bridge's
    tower and ``c_times_square``'s contains the TKTS booth, which would hand a 5 m kiosk 365.8 m.
    A confident wrong height is worse than none.

    Where nothing built stands at the coordinate this returns ``None`` for the height and every
    caller says so rather than working from a number nobody measured.  Returns ``None`` outright
    when the item names no subject at all.  ``out``, when given, is filled with the probe's own
    record -- what it hit, how many rays found built fabric, and what the landmark catalogue would
    have said -- so the sheet can publish the measurement rather than only its conclusion.
    """
    subject = meta.get("subject") or {}
    if subject.get("lat") is None or subject.get("lon") is None:
        return None
    import camera as vcam
    from nycsim_pipeline.crs import lonlat_to_tm
    sx, sy = (float(v) for v in lonlat_to_tm(subject["lon"], subject["lat"]))
    dist = math.hypot(sx - cam_x, sy - cam_y)
    ground, _ = sampler.ground_z(sx, sy, mode="street", radius_m=15.0) if sampler else (None, {})
    base = ground if ground is not None else 0.0
    probe = vcam.subject_height_probe(sx, sy, base)
    # What the old origin rule would have said, kept beside the measurement rather than used.  A
    # reader comparing the two can see for themselves which of the 38 items J74 names this is.
    nearest = None
    for e in landmarks:
        ox, oy = float(e["origin_tm"][0]), float(e["origin_tm"][1])
        d = math.hypot(ox - sx, oy - sy)
        h = e.get("height_m") or (e.get("bounds_local_m") or {}).get("max", [0, 0, 0])[2]
        if h and (nearest is None or d < nearest[0]):
            nearest = (d, float(h), e["id"])
    if out is not None:
        out.update(probe)
        if nearest is not None:
            out["nearest_catalogue_origin"] = {
                "id": nearest[2], "distance_m": round(nearest[0], 1), "height_m": round(nearest[1], 2),
                "within_120_m": bool(nearest[0] <= 120.0),
            }
            if probe.get("z") is not None and nearest[0] > 120.0:
                out["note_origin_rule"] = (
                    f"the nearest landmark model origin is {nearest[0]:.0f} m away, past the 120 m "
                    f"the old rule looked in, so this height comes from the geometry and not from "
                    f"the catalogue (J74)")
    if probe.get("z") is None:
        # The probe distinguishes two ways of having no usable height and so must this: nothing
        # built at the coordinate at all, or something built that is too low to aim or frame by --
        # the 9/11 memorial pools are the second, where 16 of 17 rays land on the plaza deck 0.1 m
        # above its own ground.  Saying "nothing built stands here" of a pool's own coping would
        # be false about the world rather than honest about the measurement.
        return dist, None, (probe.get("note")
                            or f"nothing built stands within {vcam.SUBJECT_PROBE_RINGS[-1]:.0f} m "
                               f"of the subject's coordinate, so its height is not measured here")
    return dist, float(probe["z"]), (
        f"the top of {probe['object']}, the built thing standing at the subject's coordinate, "
        f"{probe['height_above_ground_m']:.0f} m above the ground there")


def choose_lens(slug: str, top: tuple[float, float, str] | None, cam_z: float,
                portrait: bool, aspect: float) -> tuple[float, str]:
    """The focal length, widened where a level axis cannot otherwise contain the subject.

    The rule that keeps the optical axis level is what makes a render comparable with a
    photograph on proportion, but held to a 35 mm lens it puts the crown of a 227 m tower 200 m
    away far above the top of the frame -- and a sheet whose subject is out of shot proves
    nothing.  A photographer in that position reaches for a wider lens, and so does this: the
    focal length is reduced until the subject's top sits inside the frame with 12 % headroom,
    down to a floor of 18 mm (90 deg on the long side), below which the distortion would make the
    comparison meaningless.  It is never lengthened, and the reason is printed on the sheet.
    """
    import camera as vcam
    base, why = vcam.focal_for(slug)
    if top is None:
        return base, why
    dist, top_z, src = top
    if top_z is None:
        # The subject's height is not known here, so there is nothing to widen the lens *to*.
        # Widening on half of an invented 10 m is how a 106.68 m bridge tower came to be framed
        # as a 9.6 m object (J72).
        return base, f"{why}; {src}, so the lens was not widened to contain it"
    rise = top_z - cam_z
    if dist < 1.0 or rise <= 0.0:
        return base, why
    theta = math.atan(rise / dist) * 1.12
    if theta >= math.radians(88.0):
        return 18.0, (f"{why}; widened to the 18 mm floor because {src} tops out {rise:.0f} m "
                      f"above the lens only {dist:.0f} m away and no normal lens contains it")
    # Sensor dimension that maps to the vertical axis of the frame.
    sensor_v = vcam.SENSOR_WIDTH_MM if portrait else vcam.SENSOR_WIDTH_MM / max(aspect, 1e-6)
    needed = sensor_v / (2.0 * math.tan(theta))
    if needed >= base:
        return base, why
    f = max(18.0, needed)
    fov = math.degrees(2.0 * math.atan(sensor_v / (2.0 * f)))
    note = (f"widened from {base:.0f} mm to {f:.0f} mm ({fov:.0f} deg vertical) so that a level "
            f"axis contains the subject: {src} stands {rise:.0f} m above the lens at {dist:.0f} m, "
            f"{math.degrees(theta / 1.12):.0f} deg above the horizon")
    if f > needed + 0.01:
        note += ("; held at the 18 mm floor, so the top of the subject is still cut off -- past "
                 "that point the distortion would stop the two frames being comparable")
    return f, note


#: Fraction of the frame's half-height the subject's top is placed inside when the camera has to
#: tilt to contain it. 0.88 leaves 12 % headroom, the same margin :func:`choose_lens` uses when it
#: widens the lens instead.
TILT_HEADROOM = 0.88

#: The most the optical axis will tilt, degrees. Past 70 deg the frame is looking at sky and the
#: subject's own base is so far outside it that the picture stops being a comparison of anything.
MAX_TILT_DEG = 70.0


def vertical_half_fov_deg(focal_mm: float, portrait: bool, aspect: float) -> float:
    """Half the frame's vertical field of view, for the sensor fit :func:`camera.place_camera` uses."""
    import camera as vcam

    sensor_v = vcam.SENSOR_WIDTH_MM if portrait else vcam.SENSOR_WIDTH_MM / max(aspect, 1e-6)
    return math.degrees(math.atan(sensor_v / (2.0 * max(focal_mm, 1e-6))))


def containment_pitch(top: "tuple[float, float, str] | None", cam_z: float, focal_mm: float,
                      portrait: bool, aspect: float, *, slug: str | None = None) -> tuple[float, str]:
    """The tilt needed to put the subject's top inside the frame, and why -- 0 if it already is.

    Three individually sensible rules composed into a sheet that could not contain its own subject:
    a level optical axis for proportional comparability, an 18 mm lens floor against distortion, and
    an aspect ratio taken from the reference photograph. Twelve of the twenty landmark sheets that
    can be matched to a catalogue entry failed on it -- the Chrysler Building at 72 m needs 77.1 deg
    of elevation and a level frame reaches 36.9, so that sheet showed an anonymous Midtown street.

    So the camera does what the photographer does: it tilts up, past the 18 mm floor's reach, and
    the sheet says the verticals converge and that the frame is therefore not comparable on
    proportion. A frame that shows its subject with a caveat beats a frame that does not show it.
    """
    if top is None:
        return 0.0, ""
    if slug is not None and slug in {v for ss in MANDATED_VIEWPOINTS.values() for v in ss}:
        # The seven the brief names are the frames the whole comparison is judged on, and they are
        # judged on proportion. A tilt would buy a taller subject at the cost of the one property
        # those frames exist to have, so they stay level and the lens rule is all they get.
        return 0.0, ""
    dist, top_z, src = top
    if top_z is None:
        # Nothing to contain: the subject's height is not known here (J72).
        return 0.0, ""
    rise = top_z - cam_z
    if dist < 1.0 or rise <= 0.0:
        return 0.0, ""
    half = vertical_half_fov_deg(focal_mm, portrait, aspect)
    need = math.degrees(math.atan(rise / dist))
    if need <= half * TILT_HEADROOM:
        return 0.0, ""
    pitch = min(MAX_TILT_DEG, need - half * TILT_HEADROOM)
    note = (f"tilted {pitch:+.1f} deg to contain the subject: {src} tops out {rise:.0f} m above the "
            f"lens {dist:.0f} m away, {need:.0f} deg above the horizon, and the frame is only "
            f"{2 * half:.0f} deg tall at {focal_mm:.0f} mm. **The verticals converge, so this frame "
            f"is not comparable with the photograph on proportion** -- it is here to show the "
            f"subject at all")
    if pitch >= MAX_TILT_DEG - 1e-6:
        note += (f"; held at the {MAX_TILT_DEG:.0f} deg tilt cap, so the top is still cut off")
    return pitch, note


def aim_pitch(slug: str, meta: dict, cam_x: float, cam_y: float, cam_z: float,
              top: "tuple[float, float, str] | None", ground_z: float | None) -> tuple[float, str]:
    """How far the optical axis tilts off horizontal, and why.

    The default is level: a level axis keeps vertical building edges vertical, which is the
    convention every architectural photograph follows and the only way a render and a photograph
    can be compared on proportion.  The single exception is a subject standing close to the camera
    and clearly below or above eye level -- the Bethesda fountain 69 m away and 6 m below the
    terrace, say -- where a level axis would push it to the edge of the frame.  For a subject
    inside 250 m the axis is aimed at its mid-height, taken from :func:`subject_top`'s measurement
    of what actually stands there; if that aim exceeds 8 deg it is discarded and the axis stays
    level, because past that point a real photograph would be taken with a wider lens rather than
    a tilted camera.
    """
    subject = meta.get("subject") or {}
    name = subject.get("name") or "the subject"
    if top is None:
        return 0.0, "level optical axis (the reference names no subject to aim at)"
    dist, top_z, _src = top
    if dist > 250.0 or dist < 1.0:
        return 0.0, (f"level optical axis (the subject is {dist:.0f} m away; anything that far is "
                     f"photographed with a level camera)")
    if top_z is None:
        # The axis is tilted only to hold a subject whose height is *measured*.  Tilting towards
        # half of an invented 10 m aimed the Manhattan Bridge's Brooklyn tower at the water (J72).
        return 0.0, (f"level optical axis (nothing built stands at {name}'s coordinate, so its "
                     f"mid-height is not known and there is nothing to tilt towards)")
    ground = ground_z if ground_z is not None else cam_z - 1.6
    target_z = (ground + float(top_z)) / 2.0
    pitch = math.degrees(math.atan2(target_z - cam_z, dist))
    if abs(pitch) > 8.0:
        return 0.0, (f"level optical axis ({name} is {dist:.0f} m away and would need "
                     f"{pitch:+.0f} deg of tilt; a real frame would use a wider lens instead, and "
                     f"a tilted axis would stop the render being comparable on proportion)")
    return pitch, (f"aimed at {name} {dist:.0f} m away, at its mid-height ({_src}); "
                   f"{pitch:+.1f} deg from horizontal")


#: A render that is black, blown out or featureless proves nothing, so it is refused rather than
#: written to a sheet.  Thresholds match
#: ``tests/test_world_integration.py::test_verification_renders_can_actually_serve_as_evidence``.
FRAME_MEAN_MIN = 0.06
FRAME_MEAN_MAX = 0.94
FRAME_SD_MIN = 0.025
FRAME_BLOWN_SD = 0.05


#: Only one Cycles render runs at a time across concurrent sheet processes.  A scene build is
#: single-threaded and holds one to three gigabytes; the render that follows uses every core and
#: peaks near eight gigabytes (the Charging Bull scene: 4.5 M triangles, 88 vehicles, 309 people,
#: killed at 7.7 GB resident when three renders overlapped inside a memory cgroup).  Serialising
#: the renders costs no throughput -- Cycles already saturates the cores -- and lets the builds,
#: which are 73 % of a sheet's time, overlap.
RENDER_LOCK = REPO_ROOT / "blender_out" / ".render_lock"


class _render_lock:
    """An inter-process lock held for the duration of one render; a no-op where fcntl is missing."""

    def __enter__(self):
        self._fh = None
        try:
            import fcntl
            RENDER_LOCK.parent.mkdir(parents=True, exist_ok=True)
            self._fh = open(RENDER_LOCK, "w")
            fcntl.flock(self._fh, fcntl.LOCK_EX)
        except Exception as exc:                          # pragma: no cover - platform without flock
            LOG.warning("render lock unavailable (%s); rendering without it", exc)
            self._fh = None
        return self

    def __exit__(self, *exc):
        if self._fh is not None:
            try:
                import fcntl
                fcntl.flock(self._fh, fcntl.LOCK_UN)
            finally:
                self._fh.close()
        return False


def render_and_develop(render_path: Path, *, meter: bool, fallback_stops: float) -> dict:
    """Render the frame in linear light, meter it, develop it at the metered exposure, write PNG.

    The physical Sun and sky are already configured; what this decides is only the exposure the
    view transform is applied at.  With ``meter`` the stops come from :func:`meter_exposure` on the
    linear frame; without (a night frame) ``fallback_stops`` is used unchanged.  The linear EXR is
    deleted once the PNG is written -- at 172 sheets it would not fit the disk -- and everything
    the decision was made on is returned for the record.
    """
    import bpy
    import numpy as np
    sc = bpy.context.scene
    exr_path = render_path.with_suffix(".exr")
    img_settings = sc.render.image_settings
    img_settings.file_format = "OPEN_EXR"
    img_settings.color_mode = "RGB"
    img_settings.color_depth = "16"
    img_settings.exr_codec = "ZIP"
    sc.render.filepath = str(exr_path)
    with _render_lock():
        bpy.ops.render.render(write_still=True)
    metered: dict = {"metered": False, "stops": float(fallback_stops)}
    if meter:
        img = bpy.data.images.load(str(exr_path), check_existing=False)
        try:
            w, h = img.size
            buf = np.empty(w * h * 4, dtype=np.float32)
            img.pixels.foreach_get(buf)
            metered = {"metered": True, **meter_exposure(buf.reshape(h, w, 4)[..., :3])}
        finally:
            bpy.data.images.remove(img)
    sc.view_settings.exposure = float(metered["stops"])
    # Develop: the scene's view transform and the metered exposure applied to the linear frame.
    img = bpy.data.images.load(str(exr_path), check_existing=False)
    try:
        img_settings.file_format = "PNG"
        img_settings.color_mode = "RGB"
        img_settings.color_depth = "8"
        sc.render.filepath = str(render_path)
        img.save_render(str(render_path), scene=sc)
    finally:
        bpy.data.images.remove(img)
        exr_path.unlink(missing_ok=True)
    metered["view_transform"] = sc.view_settings.view_transform
    return metered


def frame_metrics(path: Path) -> dict:
    """Mean and standard deviation of a rendered frame's luminance, and whether it is evidence."""
    from PIL import Image
    import numpy as np
    try:
        a = np.asarray(Image.open(path).convert("L"), dtype=np.float32) / 255.0
    except Exception as exc:
        return {"mean": None, "sd": None, "usable": False, "reason": f"unreadable ({exc})"}
    mean, sd = float(a.mean()), float(a.std())
    reason = None
    if mean < FRAME_MEAN_MIN:
        reason = f"near-black (mean {mean:.3f})"
    elif mean > FRAME_MEAN_MAX and sd < FRAME_BLOWN_SD:
        reason = f"blown out (mean {mean:.3f}, sd {sd:.3f})"
    elif sd < FRAME_SD_MIN:
        reason = f"featureless (sd {sd:.3f})"
    return {"mean": round(mean, 4), "sd": round(sd, 4), "usable": reason is None, "reason": reason}


def render_subject(slug: str, *, samples: int = DEFAULT_SAMPLES, threads: int | None = None,
                   width: int = RENDER_WIDTH, dry_run: bool = False,
                   with_agents: bool = True) -> dict:
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

    if meta.get("interior"):
        # This build models no building interiors, and the only thing a camera inside one can
        # render is the inside of a shell -- the Grand Central concourse came out at mean 0.058
        # and was refused as a black frame after a four-minute scene build, which recorded the
        # right outcome for the wrong reason.  An interior viewpoint is declined *before* the scene
        # is built, with the reason, and leaves nothing behind that could be read as a frame.
        reason = ("interior view: this build models no building interiors, so there is nothing to "
                  "render from a viewpoint inside one; the item is declined before a scene is built "
                  "rather than rendered black and refused")
        for name in ("render.png", "sheet.png", "frame_stats.json", "render_error.txt"):
            (outdir / name).unlink(missing_ok=True)
        rec = {"slug": slug, "name": meta.get("name"), "group": meta.get("group"),
               "interior": True, "night": bool(meta.get("night")),
               "status": "not_renderable_interior", "reason": reason,
               "viewpoint": {"lat": vp["lat"], "lon": vp["lon"], "azimuth_deg": vp["azimuth_deg"],
                             "note": vp.get("note")},
               "reference_photo": None if photo is None else {
                   "file": photo["file"], "author": photo.get("author"),
                   "licence": (photo.get("license") or {}).get("short_name"),
                   "licence_url": (photo.get("license") or {}).get("url"),
                   "page_url": photo.get("page_url"), "title": photo.get("title")},
               "rendered_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")}
        (outdir / "render.json").write_text(json.dumps(rec, indent=1, sort_keys=True))
        LOG.warning("%s declined: %s", slug, reason)
        return rec

    cam_lat, cam_lon, origin_why, origin_offset_m, origin_is_photo = view_origin(meta, photo)
    x, y = (float(v) for v in lonlat_to_tm(cam_lon, cam_lat))
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
    # A skyline scene still has a foreground.  The reference photographs from the Brooklyn Heights
    # Promenade and Washington Street carry a railing, benches, litter baskets and street trees
    # inside 60 m of the lens, and a frame that drops them for being part of a 5 km scene is
    # missing the half of the picture the eye reads first.  Ground-level long-range viewpoints
    # therefore keep a near-field ring of props and facade kit; from an observation deck 260 m up
    # the same props are sub-pixel, so the eye height decides.
    # The scene is gathered around the origin chosen *before* the eye point there has been probed,
    # and that probe can reject it: at the Chrysler Building the render then moved 136.8 m to the
    # item's own viewpoint, leaving a 250 m prop disc centred 136.8 m behind the camera, so more
    # than half of it fell behind the lens and the props 113 to 250 m ahead were never gathered.
    # Rebuilding the scene after the move is not possible -- the probe needs the scene to probe --
    # so every radius is widened by the distance between the two candidate origins, which covers
    # whichever one is used (docs/DEVIATIONS.md J59).
    if origin_is_photo and origin_offset_m:
        spare = float(origin_offset_m)
        radius += spare
        prop_r += spare if prop_r > 0.0 else 0.0
        kit_r += spare if kit_r > 0.0 else 0.0
    eye_height_m = vcam.eye_rule_for(slug).height_m
    if prop_r <= 0.0 and eye_height_m <= 20.0:
        prop_r, kit_r = 150.0, 70.0

    # Agents follow the same rule as the props: they belong at eye level, and from an observation
    # deck 260 m up a person is a fraction of a pixel.  DEVIATIONS I13 is about street-level
    # frames, and this is where it is closed.
    agents_off_reason = None
    if eye_height_m > 20.0:
        agent_veh_r = agent_ped_r = 0.0
        agents_off_reason = (f"the eye stands {eye_height_m:.0f} m above the ground, where a person "
                             f"is a fraction of a pixel and a car a few, so the simulation's crowd "
                             f"and traffic are not drawn")
    elif radius > 1500.0:
        agent_veh_r, agent_ped_r = 150.0, 120.0
    else:
        agent_veh_r, agent_ped_r = AGENT_VEHICLE_RADIUS_M, AGENT_PED_RADIUS_M
    if not with_agents:
        agent_veh_r = agent_ped_r = 0.0
        agents_off_reason = "agents switched off for this render (--no-agents)"

    if photo is None:
        return {"slug": slug, "status": "no_reference_photo",
                "reason": "meta.json lists no photograph that exists on disk"}

    # The aim used to choose an assumed hour is the item's own **recorded** azimuth, not the one
    # the camera ends up with: the final azimuth is not known until after the clearance walk, and
    # a Sun that moved with the walk would make the instant depend on where the camera happened to
    # stand.  The recorded azimuth is declared, deterministic and within a few degrees of the final
    # one on every sheet where both exist.  Where the photograph carries a time, none of this runs.
    when, when_note = photo_instant(
        photo, lat=cam_lat, lon=cam_lon,
        azimuth_deg=(meta.get("viewpoint") or {}).get("azimuth_deg"),
        night=bool(meta.get("night")))
    sun = sun_for(cam_lat, cam_lon, when)

    # Match the render aspect to the reference photograph so the two halves compare like for like,
    # under a fixed pixel budget.  A landscape frame renders at the full 1280 px width; a portrait
    # reference (a quarter of the set, some as tall as 1:2.2) would otherwise cost three times the
    # samples of a landscape frame for the same content, so its width is reduced to keep the frame
    # the same size in pixels.  The angle of view is unchanged -- only the sampling density is.
    pw, ph = int(photo.get("width") or 1600), int(photo.get("height") or 1067)
    aspect = pw / ph if ph else 1.5
    budget = width * int(round(width / 1.5))
    w = min(width, int(round(math.sqrt(budget * aspect))))
    width = max(480, int(round(w / 2) * 2))
    height = max(360, int(round(width / aspect / 2) * 2))

    record = {
        "slug": slug, "name": meta.get("name"), "group": meta.get("group"),
        "night": bool(meta.get("night")), "interior": bool(meta.get("interior")),
        "viewpoint": {"lat": vp["lat"], "lon": vp["lon"], "azimuth_deg": vp["azimuth_deg"],
                      "note": vp.get("note")},
        "camera_origin": {"lat": cam_lat, "lon": cam_lon, "source": origin_why,
                          "from_photograph_gps": origin_is_photo,
                          "offset_from_recorded_m": None if origin_offset_m is None
                          else round(origin_offset_m, 1)},
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
        "scene_request": {"radius_m": radius, "prop_radius_m": prop_r, "kit_radius_m": kit_r,
                          "agent_vehicle_radius_m": agent_veh_r, "agent_ped_radius_m": agent_ped_r},
        "samples": samples,
        "resolution_note": (f"{width}x{height}; the reference photograph is {pw}x{ph} "
                            f"({aspect:.2f}:1), and the render is held to the same pixel budget as "
                            f"a 1280 px landscape frame"),
    }
    if dry_run:
        record["status"] = "dry_run"
        # The containment tilt is decided from the built scene -- it needs the subject's measured
        # top and the terrain under the lens -- and a dry run deliberately builds no scene. So the
        # plan carries no pitch rather than a zero that the real run would quietly overrule.
        record["pitch_note"] = ("undecided: the containment tilt is measured from the built scene, "
                                "which a dry run does not build")
        return record

    t0 = time.time()
    # NYC street trees are bare from about mid-November to mid-April; the props kit exports a
    # bare-canopy variant of every species, so a winter reference gets winter trees.
    leaf_off = (when.month, when.day) >= (11, 15) or (when.month, when.day) <= (4, 15)
    # The simulation frame is taken at the reference photograph's own hour and day class, so the
    # density table is asked for the traffic and the crowd that neighbourhood has at that time.
    # It is *that* hour's traffic, not the traffic in the photograph, and the caption says so.
    import agents as vagents
    agent_req = vagents.SnapshotRequest(
        x=float(x), y=float(y), heading_deg=float(vp.get("azimuth_deg") or 0.0),
        hour=int(when.hour), dow=(0 if when.weekday() <= 4 else (1 if when.weekday() == 5 else 2)),
        seed=AGENT_SEED, headlights=bool(meta.get("night")))
    record["agent_request"] = {"hour": agent_req.hour, "dow": agent_req.dow, "seed": agent_req.seed,
                               "warmup_s": agent_req.warmup_s,
                               "local_clock": when.strftime("%Y-%m-%d %H:%M %Z")}
    rep, sampler = vscene.build_scene(
        x, y, radius, prop_radius_m=prop_r, kit_radius_m=kit_r,
        with_props=prop_r > 0, with_kit=kit_r > 0,
        terrain_max_side=300 if radius <= 1500 else 380,
        lod0_radius_m=1200.0, leaf_off=leaf_off,
        with_agents=agent_veh_r > 0 or agent_ped_r > 0, agent_request=agent_req,
        agent_vehicle_radius_m=agent_veh_r, agent_ped_radius_m=agent_ped_r,
        agent_npc_archetypes=AGENT_NPC_ARCHETYPES, agent_eye_height_m=eye_height_m)
    if agents_off_reason and rep.agents.get("reason") == "disabled":
        rep.agents["reason"] = agents_off_reason
    azimuth, azimuth_why = view_azimuth(slug, meta, photo, cam_lat, cam_lon,
                                        origin_is_photo=origin_is_photo)
    # A hand-held GPS fix is the better *measurement* of where the picture was taken, but it has
    # metres of error and the world it lands in is not always renderable.  At Bethesda Terrace the
    # photograph's GPS falls on the lower plaza, where the plaza polygons bridge the 5 m step up
    # to the upper level and seal the eye 1.6 m beneath the paving; the item's own viewpoint, 43 m
    # away, is on the upper terrace in open air.  So the photograph's GPS is used unless the eye
    # point there is blocked and the nominal viewpoint is not.
    if origin_is_photo:
        probe = vcam.probe_origin(slug, cam_lat, cam_lon, azimuth, sampler, vp.get("note"))
        if probe["blocked"]:
            alt_az, alt_az_why = view_azimuth(slug, meta, photo, float(vp["lat"]), float(vp["lon"]),
                                              origin_is_photo=False)
            alt = vcam.probe_origin(slug, float(vp["lat"]), float(vp["lon"]), alt_az, sampler,
                                    vp.get("note"))
            if not alt["blocked"]:
                origin_why = (f"the item's recorded viewpoint.  This photograph's own EXIF GPS is "
                              f"{origin_offset_m:.0f} m away, but the eye point there is "
                              f"{probe['why']}, while the recorded viewpoint is in open air")
                cam_lat, cam_lon = float(vp["lat"]), float(vp["lon"])
                origin_is_photo = False
                x, y = alt["x"], alt["y"]
                azimuth, azimuth_why = alt_az, alt_az_why
                record["camera_origin"] = {"lat": cam_lat, "lon": cam_lon, "source": origin_why,
                                           "from_photograph_gps": False,
                                           "offset_from_recorded_m": 0.0,
                                           "photograph_gps_offset_m": round(origin_offset_m, 1)}
    # The distance to the subject has to be re-measured from wherever the camera ended up.
    #
    # It was taken at the top of this function from the origin `view_origin` first returned, and the
    # block above can reject that origin and fall back to the item's own viewpoint -- 43 m away at
    # Bethesda Terrace.  Nothing re-measured, so the record and the caption printed 51 m, which is
    # the distance from the *photograph's* GPS to the fountain and from nowhere the camera stood,
    # while the aim line five rows below printed 93 m from the position actually used.  It also fed
    # `min_view_m`, so the frame was required to be clear for half of the wrong distance
    # (docs/DEVIATIONS.md J54, J59).
    if subj_dist is not None:
        sx0, sy0 = (float(v) for v in lonlat_to_tm(subject["lon"], subject["lat"]))
        moved = math.hypot(sx0 - x, sy0 - y)
        if abs(moved - subj_dist) > 0.05:
            record["subject"]["rejected_origin_distance_m"] = round(subj_dist, 1)
            subj_dist = moved
    eye_z = (sampler.ground_z(x, y)[0] or 0.0) + vcam.eye_rule_for(slug).height_m
    # The subject's height is measured once, off the geometry standing at its coordinate, and the
    # aim, the lens and the sightline all read that one measurement.  Before J74 the aim and the
    # lens each ran their own copy of a *proxy* for it -- the nearest catalogue origin within
    # 120 m -- which for 38 of the 138 items that name a subject is nowhere near the model.
    height_probe: dict = {}
    top = subject_top(meta, x, y, sampler, vscene.load_landmark_catalog(), out=height_probe)
    subject_ground = None
    if top is not None and height_probe.get("ground_z_m") is not None:
        subject_ground = float(height_probe["ground_z_m"])
    pitch, pitch_why = aim_pitch(slug, meta, x, y, eye_z, top, subject_ground)
    if height_probe:
        record.setdefault("subject", {})["height_probe"] = height_probe
    focal_mm, lens_why = choose_lens(slug, top, eye_z, height > width, width / height)
    # The lens is widened first, because a level axis is what makes the two frames comparable on
    # proportion. Only where the widest lens this build will use still cannot contain the subject
    # does the camera tilt -- and then the sheet says so (I18).
    tilt, tilt_why = containment_pitch(top, eye_z, focal_mm, height > width, width / height,
                                       slug=slug)
    if tilt > 0.0:
        pitch, pitch_why = tilt, tilt_why
    placement = vcam.place_camera(slug=slug, lat=cam_lat, lon=cam_lon,
                                  azimuth_deg=azimuth, sampler=sampler, focal_mm=focal_mm,
                                  resolution=(width, height), note=vp.get("note"), pitch_deg=pitch)
    # What the clearance walk scores its candidates on (J79): the subject's coordinate, the aim
    # height the sightline probe uses, and the measured extent of the thing standing there -- the
    # same one measurement the aim and the lens were decided from, not a second copy of it.  The
    # plan extent comes from the probed object's own bounding box, and only for a landmark model:
    # a tile mesh is every building of one material in a kilometre, and its box is the tile.
    subject_for_walk = None
    if (subj_dist is not None and top is not None and top[1] is not None
            and height_probe.get("ground_z_m") is not None):
        wsx, wsy = (float(v) for v in lonlat_to_tm(subject["lon"], subject["lat"]))
        wbase, wtop = float(height_probe["ground_z_m"]), float(top[1])
        extent = vcam.object_extent_xy(height_probe.get("object"))
        subject_for_walk = {"x": wsx, "y": wsy, "z_aim": 0.5 * (wbase + wtop),
                            "height_m": wtop - wbase, "ground_z": wbase,
                            "object": height_probe.get("object"),
                            "width_m": (None if not extent or extent["is_tile_mesh"]
                                        else float(extent["width_m"]))}
        record.setdefault("subject", {})["plan_extent"] = (
            None if not extent else {"width_m": round(extent["width_m"], 1),
                                     "narrow_m": round(extent["narrow_m"], 1),
                                     "object": height_probe.get("object"),
                                     "is_tile_mesh": extent["is_tile_mesh"],
                                     "note": ("a tile mesh is every building of one material in the "
                                              "tile, so its extent is not the subject's and is not used"
                                              if extent["is_tile_mesh"] else
                                              "the bounding box of the object the height was measured off")})
    # How much open air the corrected viewpoint has to have along the view azimuth before it is
    # accepted.  A frame whose subject is 170 m away is worthless from a spot with a wall (or a
    # street tree) ten metres in front of the lens, so the requirement scales with the subject
    # distance; with no subject named, 20 m is enough to be standing in a street rather than in a
    # light well.
    min_view_m = 20.0 if subj_dist is None else max(20.0, min(0.5 * subj_dist, 80.0))
    clearance = vcam.clear_of_geometry(placement, sampler, min_view_m=min_view_m, origin_is_photo=origin_is_photo,
                                       has_subject=subj_dist is not None, subject=subject_for_walk)
    clearance["min_view_m"] = round(min_view_m, 1)
    # "N m from the camera" has to mean the camera in the picture.  `subj_dist` is measured from the
    # origin the aim was decided at, and `clear_of_geometry` has just walked the eye onto the nearest
    # paved surface -- 12 m at Bethesda Terrace -- mutating `placement` as it goes.  So the record
    # carries both, each labelled, instead of one number that matches neither position.  The first
    # attempt at this fix measured before the call and labelled the result "after the clearance
    # walk", which is the same fault it exists to correct (docs/DEVIATIONS.md J54, J59).
    def _remeasure_subject_distance(label: str) -> None:
        if subj_dist is None:
            return
        sx1, sy1 = (float(v) for v in lonlat_to_tm(subject["lon"], subject["lat"]))
        record["subject"]["distance_m"] = round(math.hypot(sx1 - placement.x, sy1 - placement.y), 1)
        record["subject"]["distance_from"] = label
        record["subject"]["origin_distance_m"] = round(subj_dist, 1)

    _remeasure_subject_distance("the placed camera, after the clearance walk")

    def _cull_and_reread(clearance_rec: dict, label: str) -> None:
        # The scene, and its agents, were built around the recorded view origin. The camera may
        # have moved since -- probe_origin can switch to the nominal viewpoint and clear_of_geometry
        # walks the eye onto the nearest paved surface -- and on 26 of the 57 scenes it did. Cull
        # anything now standing on the lens, and fold the count into the placement record so a
        # reader sees one number for agents dropped over the observer rather than two.
        #
        # A function, because it has to run **again** after a forced retry walk: on Trinity Church
        # the retry moved the camera 24.6 m onto a crosswalk and left a simulated Camry 0.1 m from
        # the lens, and the second frame was darker than the first.
        cam_ob = bpy.context.scene.camera
        if cam_ob is None or not rep.agents.get("placed_pedestrians"):
            return
        cam_w = cam_ob.matrix_world.translation
        culled = vagents.cull_near_camera(bpy.data.collections.get("agents"),
                                          float(cam_w.x), float(cam_w.y), float(cam_w.z))
        if not any(culled.values()):
            return
        drop = dict(rep.agents.get("dropped") or {})
        for k, n in culled.items():
            if n:
                drop[k] = drop.get(k, 0) + n
        rep.agents["dropped"] = drop
        rep.agents["placed_pedestrians"] = max(
            0, int(rep.agents.get("placed_pedestrians", 0)) - culled["pedestrian_over_the_observer"])
        rep.agents["placed_vehicles"] = max(
            0, int(rep.agents.get("placed_vehicles", 0)) - culled["vehicle_over_the_observer"])
        prior = rep.agents.get("culled_after_camera_move") or {}
        rep.agents["culled_after_camera_move"] = {k: int(prior.get(k, 0)) + int(v) for k, v in culled.items()}
        # The clearance record was written before this cull, so its ``nearest_agent`` can name
        # somebody the cull has just removed -- on Grand Concourse it named a pedestrian 1.5 m
        # from the lens who is not in the frame.  A true measurement of a state that no longer
        # holds is the fault J49 exists to record, so the reading is taken again against the
        # crowd the render will actually contain.
        h_half, pitches, yaws = vcam.frame_fan(placement)
        again = vcam.frame_clearance(placement.x, placement.y, placement.z,
                                     placement.azimuth_deg,
                                     probe_m=float(clearance_rec.get("nearest_agent_probe_m")
                                                   or max(min_view_m, 20.0)),
                                     half_angle_deg=h_half, pitches_deg=pitches, yaw_steps=yaws)
        clearance_rec["nearest_agent"] = again["agent_what"]
        clearance_rec["nearest_agent_m"] = (round(again["agent_m"], 1) if again["agent_what"] else None)
        if again["agent_what"]:
            clearance_rec["nearest_agent_at_deg"] = [round(v, 1) for v in again["agent_at"]]
        else:
            clearance_rec.pop("nearest_agent_at_deg", None)
        clearance_rec["nearest_agent_measured"] = label

    _cull_and_reread(clearance, "after the cull over the observer")
    # Can the camera see the thing this sheet is a comparison *of*?  Every other check asks whether
    # the camera is somewhere sensible; none asked whether the subject is in the picture, and
    # Bethesda Terrace is what that costs -- 69 m from its fountain, the fountain inside the frame's
    # cone, the model in the scene, and the terrace's own arcade wall between the two.  One ray.
    def _sightline_now() -> dict:
        """The sightline from where the camera stands *now* -- taken again after a forced retry."""
        if subject.get("lat") is None or subject.get("lon") is None:
            return {"subject_visible": None, "subject_note": "the item names no point subject"}
        ssx, ssy = (float(v) for v in lonlat_to_tm(subject["lon"], subject["lat"]))
        sgz = sampler.ground_z(ssx, ssy)[0]
        # Aim at the subject's **mid-height**, in absolute NYC_TM elevation.
        #
        # Two corrections in one line.  ``subject_top`` returns an absolute z -- its own docstring
        # said "above the camera's own eye level" and ``choose_lens`` has always read it as absolute
        # (``rise = top_z - cam_z``) -- so adding ``placement.z`` to it aimed the rays 25 m above the
        # Bethesda fountain, into open sky, and the probe reported nothing at the subject's
        # coordinate over a scene that has the fountain exactly there.  And aiming at the *top* is
        # wrong even with the right datum: a ray sent at the highest point of a subject grazes it, so
        # a 7.92 m fountain with a 2.44 m angel on a thin stem is missed by a ray that is a
        # centimetre high.  Mid-height is what ``aim_pitch`` already uses for the camera's own tilt.
        base = sgz if sgz is not None else placement.z
        stop = float(top[1]) if top and top[1] is not None else None
        if stop is None:
            # No model of the subject stands here, so there is no mid-height to aim at and no
            # sightline to report.  Saying `false` would be a claim that the subject is hidden;
            # saying nothing, with the reason, is the truth (J72).
            return {"subject_visible": None,
                    "subject_note": (top[2] if top else "the subject's height is unknown")
                    + "; no sightline was tested"}
        else:
            sz = (base + stop) * 0.5
            # The fan is sized to the subject's own measured height (J74/J76), so a 107 m tower
            # is not declared invisible because a lamp standard 5.6 m from the lens covers the
            # 0.30 m a flat 12 m fan spans there.
            # The fan is the subject's measured width across and its measured height up, clipped
            # to the frame, and a hit on the subject's own fabric is a ray that has found it (J78).
            sight = vcam.subject_sightline(placement.x, placement.y, placement.z, ssx, ssy, float(sz),
                                           subject_height_m=(float(stop) - base) if stop else None,
                                           subject_width_m=(subject_for_walk or {}).get("width_m"),
                                           subject_object=height_probe.get("object"),
                                           subject_ground_z=base,
                                           frame_half_angles_deg=vcam.frame_half_angles(placement))
            sight["subject_aimed_at"] = f"the subject's mid-height, {sz - base:.1f} m above its ground"
            return sight

    record_subject = _sightline_now()

    light = setup_world_and_sun(sun["azimuth_deg"], sun["elevation_deg"], night=bool(meta.get("night")))
    light["emissive"] = apply_time_of_day_materials(bool(meta.get("night")))
    configure_cycles(samples, threads)

    render_path = outdir / "render.png"
    bpy.context.scene.render.filepath = str(render_path)
    t1 = time.time()
    # The physical rule's stops are kept in the record beside the metered ones, so a reader can see
    # what the calibration alone would have done (J83).
    physical_stops = float(light.get("exposure_stops") or 0.0)
    developed = render_and_develop(render_path, meter=not bool(meta.get("night")),
                                   fallback_stops=physical_stops)
    light["physical_rule_stops"] = round(physical_stops, 2)
    light["exposure_stops"] = round(float(developed["stops"]), 2)
    light["development"] = developed
    t2 = time.time()

    # A frame that is black, blown out or featureless is not evidence of anything.  Measure it
    # here rather than letting it sit in the directory looking like a result.  The overwhelmingly
    # likely cause at street level is an eye point the ray tests did not catch -- inside a light
    # well, under a slab, hard against a wall -- so the first response is to force the same
    # correction a detected block would get and render once more.
    frame = frame_metrics(render_path)
    retry = None
    if not frame["usable"]:
        LOG.warning("%s: first frame is %s; forcing the clearance correction and re-rendering",
                    slug, frame["reason"])
        # The retry also demands sky.  Nothing in the ordinary placement rule looks up, so a camera
        # under a closed street canopy passes every test and renders a frame with no light in it --
        # Sixth Avenue at 45th Street stood under a pin oak with 150 m of clear street ahead of it
        # and came out at mean 0.033 (DEVIATIONS J69).  The requirement is confined to this path,
        # where the luminance gate has already said the frame is not evidence, so a street that is
        # genuinely in canopy shade keeps its shade.
        forced = vcam.clear_of_geometry(placement, sampler, min_view_m=min_view_m, origin_is_photo=origin_is_photo, force=True,
                                        has_subject=subj_dist is not None, need_sky=True,
                                        subject=subject_for_walk)
        forced["min_view_m"] = round(min_view_m, 1)
        if forced.get("moved"):
            retry = {"first_frame": frame, "clearance": clearance, "sightline": record_subject,
                     "subject_distance_m": (record.get("subject") or {}).get("distance_m")}
            clearance = forced
            # The camera has moved: what stands at the lens, how far the subject is and whether it
            # can be seen are all measured again from where the retry frame is actually taken.
            _cull_and_reread(clearance, "after the cull over the observer, on the forced retry")
            _remeasure_subject_distance("the placed camera, after the forced retry walk")
            record_subject = _sightline_now()
            developed = render_and_develop(render_path, meter=not bool(meta.get("night")),
                                           fallback_stops=physical_stops)
            light["exposure_stops"] = round(float(developed["stops"]), 2)
            light["development"] = developed
            t2 = time.time()
            frame = frame_metrics(render_path)
        else:
            retry = {"first_frame": frame,
                     "note": "no clear eye point was found within 80 m, so the frame stands as it is"}

    record.update({
        "status": "rendered" if frame["usable"] else "rejected_unusable_frame",
        "frame": frame,
        "frame_retry": retry,
        "camera": placement.as_dict(),
        "camera_caption": placement.caption(),
        "lens_reason": lens_why,
        "pitch_reason": pitch_why,
        "azimuth_reason": azimuth_why,
        "clearance": clearance,
        "sightline": record_subject,
        "lighting": light,
        "scene": rep.as_dict(),
        "render_png": str(render_path.relative_to(REPO_ROOT)),
        "seconds": {"scene": round(t1 - t0, 1), "render": round(t2 - t1, 1), "total": round(t2 - t0, 1)},
        "rendered_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
    })
    (outdir / "render.json").write_text(json.dumps(record, indent=1, sort_keys=True))
    err = outdir / "render_error.txt"
    if frame["usable"]:
        err.unlink(missing_ok=True)
        LOG.info("%s rendered in %.0f s (scene %.0f s, %d triangles; frame mean %.3f sd %.3f)",
                 slug, t2 - t0, t1 - t0, rep.triangles, frame["mean"], frame["sd"])
    else:
        # Leave no unusable PNG behind: a black render.png is indistinguishable from evidence in a
        # directory listing, and the project-wide gate scans every PNG under docs/verification.
        render_path.unlink(missing_ok=True)
        (outdir / "sheet.png").unlink(missing_ok=True)
        err.write_text(
            f"{slug}: the render cannot serve as evidence -- {frame['reason']}.\n"
            f"camera: {placement.caption()}\n"
            f"clearance: {clearance.get('note')}\n"
            f"view along the azimuth: {clearance.get('view_m')} m; nearest built thing in the "
            f"frame: {clearance.get('nearest_obstruction_m')} m; nearest simulated agent: "
            f"{clearance.get('nearest_agent_m')} m\n"
            f"sun: elevation {sun['elevation_deg']:.1f} deg, direct normal irradiance "
            f"{light.get('direct_normal_irradiance_w_m2', 0):.0f} W/m2, exposure "
            f"{light.get('exposure_stops', 0):+.2f} stops\n"
            f"retry: {json.dumps(retry)}\n")
        LOG.error("%s rejected: %s (camera %s)", slug, frame["reason"], placement.caption())
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
    ag = scene.get("agents", {})

    caption_lines: list[tuple[str, object]] = []
    caption_lines.append((f"Viewpoint: {record['viewpoint'].get('note') or '-'} "
                          f"({record['viewpoint']['lat']:.5f}, {record['viewpoint']['lon']:.5f}, "
                          f"azimuth {record['viewpoint']['azimuth_deg']:.1f} deg)", f_body))
    org = record.get("camera_origin") or {}
    if org.get("source"):
        caption_lines.append((f"Camera stands at: {org['source']}", f_body))
    subj = record.get("subject", {})
    if subj.get("name"):
        caption_lines.append((f"Subject: {subj['name']}"
                              + (f", {subj['distance_m']:.0f} m from the camera" if subj.get("distance_m") else ""), f_body))
    caption_lines.append((f"Photograph: {ph.get('title') or ph.get('file')} - {ph.get('author')}, "
                          f"{ph.get('licence')} ({ph.get('licence_url')}), taken {ph.get('date_taken')}; "
                          f"via Wikimedia Commons {ph.get('page_url')}", f_small))
    caption_lines.append((f"Render: {record.get('camera_caption', '')}", f_small))
    caption_lines.append((f"Lens: {record.get('lens_reason','')}", f_small))
    if record.get("azimuth_reason"):
        caption_lines.append((f"View direction: {record['azimuth_reason']}", f_small))
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
        if gd.get("mode") == "landmark deck":
            # The height did not come from the heightmap, so do not caption it as if it had.
            caption_lines.append((
                f"Ground under the camera: {cam.get('terrain_z_m')} m NAVD88, the landmark model's "
                f"own deck; the 2 m heightmap under the same point reads "
                f"{gd.get('heightmap_m')} m - {cam.get('ground_source','')}", f_small))
        else:
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
    pv = scene.get("pavement", {})
    tr = scene.get("terrain", {})
    if tr.get("built"):
        caption_lines.append((
            f"Ground mesh: {tr.get('samples', 0)}x{tr.get('samples', 0)} graded grid over "
            f"{2 * scene.get('radius_m', 0):.0f} m - {tr.get('near_spacing_m', tr.get('spacing_m'))} m "
            f"spacing within {tr.get('near_m', 0)} m of the viewpoint (the heightmap's own "
            f"resolution), coarsening to {tr.get('far_spacing_m', '?')} m at the edge of the scene; "
            f"{tr.get('water_quads', 0):,} quads on the flattened water surface", f_small))
    # "In frame" was the wrong word for every number that followed it.  All of these are counts
    # over the scene's own radius, which reaches kilometres, and the landmark count is the worst of
    # them: over the sheets that carry landmarks at all, 449 models are placed and 180 can fall
    # inside a frame.  So the line now says what the numbers are counts of, and the landmark count
    # carries the in-cone figure beside it (docs/DEVIATIONS.md J61).
    in_cone = sheet_facts.landmarks_in_cone(cam, lm.get("landmarks") or [])
    lm_text = f"{lm.get('placed', 0)} landmark models"
    if in_cone:
        lm_text += (f" of which {in_cone['in_cone']} can fall inside the "
                    f"{in_cone['cone_deg']:.1f} deg frame")
    caption_lines.append((
        f"Built into the scene within {scene.get('radius_m', 0):.0f} m of the camera, not all of "
        f"it in frame: {b.get('tiles_imported', 0)}/{b.get('tiles_wanted', 0)} building tiles "
        f"({b.get('triangles', 0):,} tris), {lm_text}, "
        f"{pv.get('placed', 0)} pavement polygons ("
        + ", ".join(f"{v:,} {k}" for k, v in list((pv.get('per_kind') or {}).items())[:6])
        + f"), {pr.get('placed', 0)} props"
        + (" (bare-canopy trees)" if pr.get("leaf_off") else "")
        + (f", {pr['impostor_cards_dropped']} opaque impostor cards dropped"
           if pr.get("impostor_cards_dropped") else "")
        + f", {kt.get('placed', 0)} kit pieces"
        + f", {ag.get('placed_vehicles', 0)} vehicles, {ag.get('placed_pedestrians', 0)} people"
        + f"; {scene.get('triangles', 0):,} triangles total",
        f_small))
    ma = scene.get("materials") or {}
    if ma.get("dressed"):
        worn = ", ".join(f"{k} ({v.get('asset_id')}, {v.get('physical_size_m')} m)"
                         for k, v in sorted(ma["dressed"].items()))
        line = (f"City surfaces: {ma.get('slots', 0)} material slots on the shells and the roadway "
                f"resolved their own name against the shared CC0 texture catalogue at "
                f"{ma.get('resolution')} -- {worn}. The tile files carry the material name and a "
                f"flat colour; the surface is resolved on import (docs/DEVIATIONS.md J63)")
        if ma.get("flat"):
            line += (". Left as the flat colour the tile carries: "
                     + ", ".join(f"{k} ({v})" for k, v in sorted(ma["flat"].items())))
        caption_lines.append((line, f_small))
    if ag.get("caption"):
        caption_lines.append((ag["caption"], f_small))
    elif ag.get("reason") and ag.get("reason") != "disabled":
        caption_lines.append((f"Agents: none placed - {ag['reason']}", f_small))
    gaps = []
    if b.get("tiles_missing"):
        miss = b["missing"][:8]
        gaps.append(f"building shells not built for {b['tiles_missing']} tile(s): " + ", ".join(miss)
                    + (" ..." if b["tiles_missing"] > len(miss) else ""))
    if b.get("tiles_lod_substituted"):
        sub = b["lod_substituted"][:6]
        gaps.append(f"{b['tiles_lod_substituted']} tile(s) had no mesh at the LOD their distance "
                    f"asks for and were drawn at the nearest LOD present: " + ", ".join(sub)
                    + (" ..." if b["tiles_lod_substituted"] > len(sub) else ""))
    if b.get("tiles_dropped_for_budget"):
        gaps.append(f"{b['tiles_dropped_for_budget']} of the furthest tiles dropped at the "
                    f"{b.get('triangle_budget', 0):,}-triangle shell budget")
    if pr.get("capped"):
        gaps.append(f"props capped by {pr['capped']}")
    if kt.get("capped"):
        gaps.append(f"kit capped by {kt['capped']} ({kt.get('records_in_range',0):,} in range)")
    if kt.get("reason"):
        gaps.append(f"kit not placed: {kt['reason']}")
    if pr.get("reason"):
        gaps.append(f"props not placed: {pr['reason']}")
    if pv.get("reason"):
        gaps.append(f"pavement not placed: {pv['reason']}")
    if ag.get("reason") and ag.get("reason") != "disabled":
        gaps.append(f"agents not placed: {ag['reason']}")
    elif ag.get("reason") == "disabled":
        gaps.append("no agents in this frame")
    for key, label in (("vehicle_triangle_budget", "vehicles"),
                       ("pedestrian_triangle_budget", "people")):
        n = (ag.get("dropped") or {}).get(key)
        if n:
            gaps.append(f"{n} further {label} the simulation has in range were dropped at the "
                        f"{ag.get('triangle_budget', 0):,}-triangle agent budget")
    for key, label in (("vehicle_not_on_carriageway",
                        "vehicles the simulation put where the planimetric data has no roadway"),
                       ("pedestrian_not_on_walkable_surface",
                        "people the simulation put where the planimetric data has no sidewalk"),
                       ("pedestrian_in_the_carriageway_not_crossing",
                        "people the simulation put in the roadway while not crossing"),
                       ("vehicle_body_has_no_rider",
                        "cyclists, e-bikes and pedicabs not drawn because the fleet exports those "
                        "bodies without a rider"),
                       ("vehicle_on_a_car_free_park_drive",
                        "vehicles the road graph put on Central Park's East, West, Terrace or "
                        "Center Drive, which have carried no private traffic since 2018")):
        n = (ag.get("dropped") or {}).get(key)
        if n:
            gaps.append(f"{n} {label}, dropped rather than drawn")
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
    write_frame_stats(slug, outdir)
    return out


def write_frame_stats(slug: str, outdir: Path) -> None:
    """Measure both halves of the sheet **now**, beside the sheet this call just wrote.

    ``frame_stats.json`` holds the two comparisons every assessment reaches for first -- how much
    darker the render is than its photograph, how much less colour it carries -- and it used to be
    written only when somebody ran ``tools/frame_stats.py`` by hand.  A re-render left it in place
    with its old numbers and its old ``rendered_at``, and because ``tools/assessment_check.py``
    checks a quoted figure against it, an assessment could quote the luminance of a **previous
    image** and pass (docs/DEVIATIONS.md J77).  Measuring it here makes one render and one
    measurement the same event.
    """
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "nycsim_frame_stats", str(REPO_ROOT / "tools" / "frame_stats.py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        doc = mod.measure(slug)
        if "error" in doc:
            LOG.warning("%s frame_stats not written: %s", slug, doc["error"])
            return
        (outdir / "frame_stats.json").write_text(json.dumps(doc, indent=1) + "\n")
        LOG.info("%s frame_stats written (render mean %s, reference mean %s)", slug,
                 (doc.get("render") or {}).get("mean"), (doc.get("reference") or {}).get("mean"))
    except Exception as exc:                       # a sheet is still evidence without its statistics
        LOG.warning("%s frame_stats not written: %s", slug, exc)


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
        if rec.get("status") == "not_renderable_interior":
            return "not rendered", str(rec.get("reason") or "interior view; no interiors are modelled")
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
    rendered = {cov["slug"] for cov, st, _ in rows if st == "rendered"}

    def covered(groups: dict[str, list[str]]) -> tuple[int, list[str]]:
        hit = [name for name, ss in groups.items() if any(s in rendered for s in ss)]
        return len(hit), sorted(set(groups) - set(hit))

    m_done, m_left = covered(MANDATED_VIEWPOINTS)
    d_done, d_left = covered(DRIVE_THROUGH_AREAS)

    lines = [
        "# Comparison sheets — index",
        "",
        f"Every subject in `docs/verification/reference/` with its comparison status. "
        f"{done} of {len(rows)} subjects have a sheet at "
        f"`docs/verification/comparison/<slug>/sheet.png`, each with its own `assessment.md`, "
        f"the raw `render.png` and the `render.json` that records the camera, the Sun and every "
        f"piece of world data that went into the frame.",
        "",
        f"* **Mandated viewpoints: {m_done} of {len(MANDATED_VIEWPOINTS)} covered.**"
        + ("" if not m_left else "  Not covered: " + ", ".join(m_left) + "."),
        f"* **Drive-through areas: {d_done} of {len(DRIVE_THROUGH_AREAS)} covered.**"
        + ("" if not d_left else "  Not covered: " + ", ".join(d_left) + "."),
        "",
        "Generated by `python3 blender/verify/render_sheets.py --write-index`.",
        "",
        "| subject | group | status | sheet | assessment | what is in the frame / why not |",
        "|---|---|---|---|---|---|",
    ]
    for cov, status, note in rows:
        slug = cov["slug"]
        tag = ""
        if slug in mandated:
            tag = f" **[mandated: {mandated[slug]}]**"
        elif slug in drive:
            tag = f" *[drive-through: {drive[slug]}]*"
        sheet = f"[sheet]({slug}/sheet.png)" if status == "rendered" else "—"
        assessed = ("[assessment]({0}/assessment.md)".format(slug)
                    if (COMPARISON_DIR / slug / "assessment.md").exists() else "—")
        name = (cov.get("name") or slug).replace("|", "/")
        lines.append(f"| [{name}](../reference/{slug}/meta.json){tag} | {cov['group']} | "
                     f"{status} | {sheet} | {assessed} | {note.replace('|', '/')} |")
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
    photo0 = pick_reference_photo(meta)
    cam_lat, cam_lon, _, _, _ = view_origin(meta, photo0)
    x, y = (float(v) for v in lonlat_to_tm(cam_lon, cam_lat))
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
    photo = photo0
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
    ap.add_argument("--no-agents", action="store_true",
                    help="do not place the simulation's vehicles and pedestrians")
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

    done, failed, declined = [], [], []
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
                                 dry_run=a.dry_run, with_agents=not a.no_agents)
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
        if rec.get("status") == "not_renderable_interior":
            declined.append(slug)
            continue
        if rec.get("status") != "rendered":
            failed.append(slug)
            err = outdir / "render_error.txt"
            # render_subject writes a diagnostic for a frame it rejected; do not overwrite it.
            if not err.exists():
                err.write_text(json.dumps(rec, indent=1))
            continue
        compose_sheet(slug, rec)
        done.append(slug)
    LOG.info("done: %d, failed: %d%s, declined as interior: %d%s", len(done), len(failed),
             (" (" + ", ".join(failed) + ")") if failed else "", len(declined),
             (" (" + ", ".join(declined) + ")") if declined else "")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
