#!/usr/bin/env python3
"""The forty lines of a sheet's record that an assessment is written from.

    python3 tools/sheet_brief.py <slug>

``sheet_facts.py`` prints everything the render recorded, which is four hundred lines and the right
thing for an audit.  Writing the assessment needs a different cut: where the camera stands and why,
which instant lit it and where that came from, what the height probe and the sightline actually
measured, how the two halves of the sheet compare when measured, and what the scene could not draw.
This prints that, with every figure exactly as the record has it so the prose can quote it and
``assessment_check.py`` can find it again.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
COMPARISON = REPO / "docs" / "verification" / "comparison"


def load(slug: str) -> tuple[dict, dict, dict]:
    facts = subprocess.run(
        [sys.executable, str(REPO / "tools" / "sheet_facts.py"), slug],
        capture_output=True, text=True, check=False)
    if facts.returncode != 0:
        raise SystemExit(f"sheet_facts.py failed for {slug}: {facts.stderr.strip()[:400]}")
    try:
        f = json.loads(facts.stdout)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"sheet_facts.py wrote no JSON for {slug}: {exc}") from exc

    d = COMPARISON / slug
    render = json.loads((d / "render.json").read_text()) if (d / "render.json").is_file() else {}
    stats_path = d / "frame_stats.json"
    stats = json.loads(stats_path.read_text()) if stats_path.is_file() else {}
    return f, render, stats


def section(title: str) -> None:
    print(f"\n--- {title}")


def kv(label: str, value) -> None:
    if value is None or value == {} or value == []:
        return
    print(f"  {label}: {value}")


def top(counts: dict | None, limit: int = 14) -> str:
    if not counts:
        return ""
    ordered = sorted(counts.items(), key=lambda kv: -kv[1] if isinstance(kv[1], (int, float)) else 0)
    return ", ".join(f"{k} {v}" for k, v in ordered[:limit])


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if len(args) != 1:
        print(__doc__.strip())
        return 2
    slug = args[0]
    if not (COMPARISON / slug).is_dir():
        print(f"no sheet at {COMPARISON / slug}")
        return 2

    f, render, stats = load(slug)

    print(f"=== {f.get('name', slug)}  [{slug}]  group={f.get('group')}  night={f.get('night')}")

    section("reference")
    ref = f.get("reference") or {}
    for key in ("file", "author", "licence", "license", "date_taken", "width", "height", "confidence"):
        kv(key, ref.get(key))

    section("camera")
    cam = f.get("camera") or {}
    origin = f.get("camera_origin") or {}
    for key in ("azimuth_deg", "pitch_deg", "focal_mm", "eye_height_m", "eye_datum", "eye_source"):
        kv(key, cam.get(key))
    for key in ("lat", "lon", "from_photograph_gps", "offset_from_recorded_m", "source"):
        kv(key, origin.get(key))
    kv("azimuth_reason", f.get("azimuth_reason"))
    kv("lens_reason", f.get("lens_reason"))
    kv("pitch_reason", f.get("pitch_reason"))

    section("clearance")
    for key, value in (f.get("clearance") or {}).items():
        kv(key, value)

    section("sun and development")
    sun = f.get("sun") or {}
    for key in ("azimuth_deg", "elevation_deg", "local", "time_source"):
        kv(key, sun.get(key))
    light = render.get("lighting") or {}
    for key in ("direct_normal_irradiance_w_m2", "background_strength", "exposure_stops",
                "physical_rule_stops", "view_transform"):
        kv(key, light.get(key))
    for key, value in (light.get("development") or {}).items():
        kv(f"development.{key}", value)
    for key, value in (light.get("emissive") or {}).items():
        kv(f"emissive.{key}", value)

    section("subject and sightline")
    subject = f.get("subject") or {}
    for key in ("name", "distance_from", "distance_m", "origin_distance_m"):
        kv(key, subject.get(key))
    for key, value in (subject.get("height_probe") or {}).items():
        kv(f"probe.{key}", value)
    for key, value in (subject.get("plan_extent") or {}).items():
        kv(f"extent.{key}", value)
    for key, value in (f.get("sightline") or {}).items():
        kv(key, value)

    section("the two halves, measured")
    for half in ("render", "reference", "render_over_reference"):
        block = stats.get(half) or {}
        if block:
            print(f"  {half}: " + ", ".join(f"{k} {v}" for k, v in block.items()))

    section("what is in the scene")
    kv("triangles", f.get("triangles"))
    buildings = f.get("buildings") or {}
    kv("building tiles", f"{buildings.get('tiles')} tiles, {buildings.get('triangles')} tris, "
                        f"missing {len(buildings.get('missing') or [])}, "
                        f"lod_substituted {len(buildings.get('lod_substituted') or [])}")
    landmarks = f.get("landmarks") or {}
    frustum = landmarks.get("frustum") or {}
    kv("landmarks", f"{landmarks.get('placed')} placed, {frustum.get('in_cone')} in a "
                    f"{frustum.get('cone_deg')} deg cone, {landmarks.get('skipped')} skipped")
    for entry in (frustum.get("in_cone_names") or [])[:6]:
        kv("  in cone", f"{entry.get('name')} at {entry.get('distance_m')} m, "
                        f"off axis {entry.get('off_axis_deg')} deg")
    pavement = f.get("pavement") or {}
    kv("pavement", f"{pavement.get('placed')} polygons ({top(pavement.get('per_kind'))}), "
                   f"dropped {pavement.get('dropped')}")
    props = f.get("props") or {}
    kv("props", f"{props.get('placed')} placed ({top(props.get('per_kind'))})")
    kv("props unmapped", top(props.get("unmapped")))
    for key in ("tree_species_substituted", "tree_instances_scaled", "tree_mean_scale",
                "tree_scale_out_of_band", "impostor_cards_dropped"):
        kv(f"props.{key}", props.get(key))
    kit = f.get("kit") or {}
    kv("kit", f"{kit.get('total')} pieces ({top(kit.get('per_category'))})")
    terrain = f.get("terrain") or {}
    kv("terrain", f"{terrain.get('triangles')} tris, {terrain.get('spacing_m')} m near / "
                  f"{terrain.get('far_spacing_m')} m far, holes {terrain.get('holes')}")
    kv("water bodies", ", ".join(sorted(set(terrain.get("water_bodies") or []))) or None)
    structures = f.get("structures") or {}
    kv("structures", f"{structures.get('tiles_imported')} tile(s), "
                     f"{structures.get('tiles_without_a_file')} without a file, "
                     f"{structures.get('triangles')} tris")

    park = f.get("parkground") or {}
    if park:
        kv("park ground", f"{park.get('meshes')} meshes, {park.get('surfaces')} surfaces, "
                          f"{park.get('faces_cut_for_landmark_ground')} faces cut for landmark ground")
        for kind, reason in (park.get("flat_with_reason") or {}).items():
            kv("  flat", f"{kind}: {reason[:120]}")
        clearance = ((park.get("terrain_clearance") or {}).get("bands") or {})
        for band, values in clearance.items():
            kv(f"  clearance {band}", ", ".join(f"{k} {v}" for k, v in values.items()))
        redrape = park.get("redraped_on_scene_heightmap") or {}
        if redrape:
            kv("  redraped", ", ".join(f"{k} {v}" for k, v in redrape.items() if k != "what"))

    section("agents")
    agents = f.get("agents") or {}
    kv("vehicles", agents.get("vehicles"))
    kv("pedestrians", agents.get("pedestrians"))
    kv("per_class", top(agents.get("per_class")))
    kv("vehicle_lods", top(agents.get("vehicle_lods")))
    kv("ped_lods", top(agents.get("ped_lods")))
    kv("dropped", top(agents.get("dropped"), limit=20))
    kv("reason", agents.get("reason"))
    kv("crowd_clock", f.get("crowd_clock"))

    frame = f.get("frame") or {}
    if frame:
        section("frame verdict from the runner")
        for key, value in frame.items():
            kv(key, value)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
