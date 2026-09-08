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
import json
from pathlib import Path

COMPARISON = Path("/home/user/Map-New-York/docs/verification/comparison")


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
        "triangles": sc.get("triangles"),
        "buildings": {"tiles": len(b.get("imported") or []), "triangles": b.get("triangles"),
                      "missing": b.get("missing"), "lod_substituted": b.get("lod_substituted"),
                      "new_jersey": b.get("new_jersey")},
        "landmarks": {"placed": lm.get("placed"), "names": [x.get("name") if isinstance(x, dict) else x
                                                            for x in (lm.get("landmarks") or [])],
                      "skipped": lm.get("skipped"), "own_ground_m2": lm.get("own_ground_m2")},
        "pavement": {"placed": pav.get("placed"), "per_kind": pav.get("per_kind"),
                     "dropped": pav.get("dropped_polygons"), "radius_m": pav.get("radius_m")},
        "props": {"placed": props.get("placed"), "in_range": props.get("rows_in_range"),
                  "capped": props.get("capped"), "per_kind": props.get("per_kind"),
                  "unmapped": props.get("unmapped_kinds"),
                  "built_elsewhere": props.get("kinds_built_elsewhere"),
                  "impostor_cards_dropped": props.get("impostor_cards_dropped"),
                  "tree_species_substituted": props.get("tree_species_substituted"),
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
