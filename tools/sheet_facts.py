#!/usr/bin/env python3
"""Every measured number a comparison assessment should quote, for one slug or for all of them.

An assessment is a judgement about a picture, and judgements go wrong when the writer is also
transcribing forty numbers out of a JSON file by hand. This prints the numbers so the writing can be
about the picture. It invents nothing and rounds nothing: every figure is read straight out of
``render.json``, which is what the render itself wrote.

    python3 sheet_facts.py drive_bronx_arthur_ave
    python3 sheet_facts.py --all --rendered-after 2026-09-08
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import math
from pathlib import Path

COMPARISON = Path("/home/user/Map-New-York/docs/verification/comparison")
#: What the renders actually place from: one JSON per built model, each carrying ``origin_tm`` and
#: ``bounds_local_m``.  The processed catalogue is the fallback for a checkout with no build in it.
BUILT_CATALOGUE = Path("/home/user/Map-New-York/blender_out/landmarks/catalog")
LANDMARK_CATALOGUE = Path("/home/user/Map-New-York/data/processed/landmarks/landmarks.json")

#: ``agent_request.dow`` is not a day of the week.  It is the simulation's day *type*, and
#: ``DensityTable::kDows`` is 3: the density table holds one profile for weekdays, one for Saturday
#: and one for Sunday.  A writer reading ``"dow": 2`` next to a Sunday date will call the frame a
#: Tuesday, which is how an assessment ends up naming the wrong day.  So the name is spelled out
#: here and checked against the render's own clock rather than left as a number to be guessed at.
DAY_TYPE_NAMES = {0: "a weekday", 1: "Saturday", 2: "Sunday"}


def day_type(agent_req: dict) -> dict | None:
    """Spell out the day type the crowd was drawn for, and check it against the frame's date."""
    if not agent_req or agent_req.get("dow") is None:
        return None
    code = int(agent_req["dow"])
    out = {"code": code, "means": DAY_TYPE_NAMES.get(code, f"unknown day-type code {code}"),
           "note": "the simulation holds three density profiles -- weekday, Saturday, Sunday -- "
                   "so this is a day *type*, not a day of the week"}
    clock = agent_req.get("local_clock") or ""
    try:
        day = dt.date.fromisoformat(clock.split()[0])
    except (ValueError, IndexError):
        return out
    out["date"] = day.isoformat()
    out["weekday"] = day.strftime("%A")
    wanted = 0 if day.weekday() <= 4 else (1 if day.weekday() == 5 else 2)
    if wanted != code:
        out["disagrees"] = (f"{day:%A} {day.isoformat()} is day type {wanted} "
                            f"({DAY_TYPE_NAMES[wanted]}) but the crowd was drawn for {code}")
    return out


def load_catalogue() -> list[dict]:
    """The landmark models that were built, as entries carrying ``origin_tm``.

    This reads the same per-model catalogue the renderer places from, so the geometry here is the
    geometry that stands in the scene.  It needs no Blender, which is what lets the sheet composer
    use it too.
    """
    out: list[dict] = []
    if BUILT_CATALOGUE.is_dir():
        for f in sorted(BUILT_CATALOGUE.glob("*.json")):
            try:
                e = json.loads(f.read_text())
            except (OSError, ValueError):
                continue
            if isinstance(e, dict) and e.get("id") and e.get("origin_tm") is not None:
                out.append(e)
    if out:
        return out
    try:
        cat = json.loads(LANDMARK_CATALOGUE.read_text())
    except (OSError, ValueError):
        return []
    items = cat.get("landmarks") if isinstance(cat, dict) else cat
    return [it for it in (items or []) if isinstance(it, dict) and it.get("id")]


def landmarks_in_cone(cam: dict, placed: list, catalogue: list | None = None) -> dict | None:
    """How many of the placed landmarks can actually fall inside this camera's horizontal cone.

    ``scene.landmarks.placed`` counts what was *built into the scene*, over a radius that reaches
    kilometres.  Nine of the fourteen on the Broadway/Wall St sheet stand behind the camera, and
    over the 52 sheets that carry landmarks at all, 449 are placed and 180 can fall in a frame.  A
    caption or an assessment that quotes the placed count as what the frame shows is wrong about
    the picture by a factor of two and a half, so the in-frame count is worked out here from the
    catalogue's own footprints.

    ``catalogue`` lets the caller supply the entries it actually placed from; it defaults to the
    processed catalogue on disk.
    """
    if not placed or cam.get("x") is None or cam.get("hfov_deg") is None:
        return None
    items = catalogue if catalogue is not None else load_catalogue()
    by = {it["id"]: it for it in items if isinstance(it, dict) and it.get("id")}
    if not by:
        return None
    cx, cy = float(cam["x"]), float(cam["y"])
    az, half = float(cam["azimuth_deg"]), float(cam["hfov_deg"]) / 2.0
    inside, aside, unknown = [], [], []
    for e in placed:
        if not isinstance(e, dict):
            continue
        it = by.get(e.get("id"))
        origin = (it or {}).get("origin_tm")
        if not it or not origin:
            unknown.append(e.get("name") or e.get("id"))
            continue
        ox, oy = (origin["x"], origin["y"]) if isinstance(origin, dict) else (origin[0], origin[1])
        bounds = it.get("bounds_local_m") or {}
        lo = bounds.get("min") or [0.0, 0.0, 0.0]
        hi = bounds.get("max") or [0.0, 0.0, 0.0]
        px = ox + (lo[0] + hi[0]) / 2.0
        py = oy + (lo[1] + hi[1]) / 2.0
        dx, dy = px - cx, py - cy
        dist = math.hypot(dx, dy)
        off = (math.degrees(math.atan2(dx, dy)) - az + 180.0) % 360.0 - 180.0
        # The footprint has width, so a landmark whose centre is outside the cone can still show an
        # edge in it.  Half the longer plan dimension, as an angle at this distance.
        span = math.degrees(math.atan2(max(hi[0] - lo[0], hi[1] - lo[1]) / 2.0, max(dist, 1.0)))
        row = {"name": e.get("name") or e.get("id"), "distance_m": round(dist, 1),
               "off_axis_deg": round(off, 1), "half_width_deg": round(span, 1)}
        (inside if abs(off) - span <= half else aside).append(row)
    inside.sort(key=lambda r: r["distance_m"])
    aside.sort(key=lambda r: r["distance_m"])
    return {"cone_deg": round(half * 2.0, 3), "in_cone": len(inside), "behind_or_aside": len(aside),
            "not_in_catalogue": unknown, "in_cone_names": inside,
            "behind_or_aside_names": [r["name"] for r in aside],
            "note": "in_cone means the footprint's angular span crosses the horizontal field of "
                    "view; it is not a visibility test -- a nearer building can still hide it"}


def facts(slug: str) -> dict:
    rec = COMPARISON / slug / "render.json"
    if not rec.is_file():
        return {"slug": slug, "error": "no render.json"}
    d = json.loads(rec.read_text())
    sc = d.get("scene") or {}
    cam = d.get("camera") or {}
    props = sc.get("props") or {}
    kit = sc.get("kit") or {}
    pav = sc.get("pavement") or {}
    ag = sc.get("agents") or {}
    b = sc.get("buildings") or {}
    lm = sc.get("landmarks") or {}
    ter = sc.get("terrain") or {}
    out = {
        "slug": slug,
        "name": d.get("name"),
        "group": d.get("group"),
        "rendered_at": d.get("rendered_at"),
        "seconds": (d.get("seconds") or {}).get("total") if isinstance(d.get("seconds"), dict) else d.get("seconds"),
        "night": d.get("night"),
        "camera": {k: cam.get(k) for k in ("azimuth_deg", "pitch_deg", "focal_mm", "eye_height_m",
                                           "eye_datum", "eye_source")},
        "frame": d.get("frame"),
        "sun": {k: (d.get("sun") or {}).get(k) for k in ("azimuth_deg", "elevation_deg", "local",
                                                          "time_source")},
        "reference": {k: (d.get("reference_photo") or {}).get(k)
                      for k in ("file", "author", "licence", "license", "date_taken", "width",
                                "height", "confidence", "estimated_azimuth_deg")},
        "subject": d.get("subject"),
        # The two questions an assessment must not have to guess at: can this camera see the thing
        # the sheet is a comparison of, and what is standing in its frame.  Both are measurements
        # the render already took (docs/DEVIATIONS.md J49, J54, J55, J57) and neither was reaching
        # the writer, so an assessment could describe a frame it had no numbers for.
        "sightline": d.get("sightline"),
        "clearance": d.get("clearance"),
        "camera_origin": d.get("camera_origin"),
        "azimuth_reason": d.get("azimuth_reason"),
        "triangles": sc.get("triangles"),
        "buildings": {"tiles": len(b.get("imported") or []), "triangles": b.get("triangles"),
                      "missing": b.get("missing"), "lod_substituted": b.get("lod_substituted"),
                      "new_jersey": b.get("new_jersey")},
        "landmarks": {"placed": lm.get("placed"), "names": [x.get("name") if isinstance(x, dict) else x
                                                            for x in (lm.get("landmarks") or [])],
                      "skipped": lm.get("skipped"), "own_ground_m2": lm.get("own_ground_m2"),
                      "frustum": landmarks_in_cone(cam, lm.get("landmarks") or [])},
        "pavement": {"placed": pav.get("placed"), "per_kind": pav.get("per_kind"),
                     "dropped": pav.get("dropped_polygons"), "radius_m": pav.get("radius_m")},
        "props": {"placed": props.get("placed"), "in_range": props.get("rows_in_range"),
                  "capped": props.get("capped"), "per_kind": props.get("per_kind"),
                  "unmapped": props.get("unmapped_kinds"),
                  "built_elsewhere": props.get("kinds_built_elsewhere"),
                  "impostor_cards_dropped": props.get("impostor_cards_dropped"),
                  "tree_species_substituted": props.get("tree_species_substituted"),
                  # J70: a tree is drawn at the height its own row records, not at the height the
                  # kit exported its size class at.  A sheet that says how dense its canopy is has
                  # to be able to say what sized it.
                  "tree_instances_scaled": props.get("tree_instances_scaled"),
                  "tree_mean_scale": props.get("tree_mean_scale"),
                  "tree_scale_out_of_band": props.get("tree_scale_out_of_band"),
                  "radius_m": props.get("radius_m")},
        "kit": {"total": sum((kit.get("per_category") or {}).values()) or None,
                "per_category": kit.get("per_category"), "capped": kit.get("capped")},
        "terrain": {"triangles": ter.get("triangles"), "spacing_m": ter.get("spacing_m"),
                    "far_spacing_m": ter.get("far_spacing_m"), "holes": ter.get("holes"),
                    "water_bodies": [w.get("name") for w in (ter.get("water_bodies") or [])]},
        "structures": sc.get("structures"),
        "parkground": sc.get("parkground"),
        "agents": {"vehicles": ag.get("placed_vehicles"), "pedestrians": ag.get("placed_pedestrians"),
                   "per_class": ag.get("per_class"), "dropped": ag.get("dropped"),
                   "vehicle_lods": ag.get("vehicle_lods"), "ped_lods": ag.get("ped_lods"),
                   "reason": ag.get("reason")},
        "clearance": d.get("clearance"),
        "crowd_clock": day_type(d.get("agent_request") or {}),
        "lens_reason": d.get("lens_reason"),
        "pitch_reason": d.get("pitch_reason"),
        "azimuth_reason": d.get("azimuth_reason"),
    }
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("slug", nargs="*")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--rendered-after", default=None)
    ap.add_argument("--brief", action="store_true", help="one line per slug")
    a = ap.parse_args()
    slugs = a.slug or (sorted(p.name for p in COMPARISON.iterdir()
                              if p.is_dir() and (p / "render.json").is_file()) if a.all else [])
    if not slugs:
        ap.error("name a slug or pass --all")
    for s in slugs:
        f = facts(s)
        if a.rendered_after and (f.get("rendered_at") or "") < a.rendered_after:
            continue
        if a.brief:
            print(f"{s:46s} {f.get('rendered_at','')} tris={f.get('triangles')} "
                  f"props={f['props']['placed']}/{f['props']['in_range']} "
                  f"kit={f['kit']['total']} pav={f['pavement']['placed']} "
                  f"veh={f['agents']['vehicles']} ped={f['agents']['pedestrians']}")
        else:
            print(json.dumps(f, indent=1, sort_keys=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
