#!/usr/bin/env python3
"""The header block of a comparison assessment, written from the record rather than retyped from it.

    python3 tools/assessment_header.py <slug>

Every assessment opens with the same four paragraphs -- reference, camera, sun, scene -- and every
figure in them already exists in the record ``tools/assessment_check.py`` checks a quotation
against.  **Retyping them is where the factual errors get in.**  Two are already on record: a
day-type code transcribed as Monday for a Saturday, and Bethesda's NYC_TM coordinate pasted into
the Broadway/Wall camera line.  Both were caught, one by a check and one by luck, and there are
166 assessments still to write.

So the header is generated from ``tools/sheet_facts.py`` -- the same artefact the checker reads --
plus the parts of ``render.json`` the fact sheet does not normalise (the camera's geometry, the
lighting, the material table).  Nothing here decides what a sheet *means*; it prints what the
record says so the writing can be spent on the picture.

Below the header it prints the raw blocks an assessment draws on -- landmarks in cone, props, kit,
agents, materials -- and the frame statistics as a table.  If ``frame_stats.json`` measures a
different render than the one beside it, it says so and **refuses to print its numbers** rather
than offering the statistics of a previous image (docs/DEVIATIONS.md J77).
"""
from __future__ import annotations
import json, subprocess, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
C = REPO / "docs/verification/comparison"


def main(slug: str) -> int:
    f = json.loads(subprocess.run([sys.executable, str(REPO / "tools" / "sheet_facts.py"), slug],
                                  capture_output=True, text=True, check=True).stdout)
    rec = json.loads((C / slug / "render.json").read_text())
    fp = C / slug / "frame_stats.json"
    fs = json.loads(fp.read_text()) if fp.is_file() else {}
    if fs.get("rendered_at") and fs["rendered_at"] != rec.get("rendered_at"):
        print(f"!! frame_stats.json measures the render of {fs['rendered_at']}, this render is "
              f"{rec.get('rendered_at')} -- run `python3 tools/frame_stats.py {slug}` before quoting it\n")
        fs = {}

    # `sheet_facts` normalises the scene counts; the camera's geometry, the lighting and the
    # material table are only in the record itself, so both are read and neither is retyped.
    # The reference block in `sheet_facts` carries the licence and the confidence; the title and
    # the two URLs are only in the record, so the citation is assembled from both.
    cam, ph, sun = rec["camera"], dict(f["reference"], **(rec.get("reference_photo") or {})), f["sun"]
    lt = rec.get("lighting") or {}
    print(f"# {rec.get('name') or slug}\n")
    print(f"`{slug}` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)\n")
    print(f"**Reference** — {ph.get('title')} by {ph.get('author')}, {ph.get('licence')} "
          f"({ph.get('licence_url')}), taken {ph.get('date_taken')}, {ph.get('width')}x{ph.get('height')}. "
          f"[Commons page]({ph.get('page_url')})")
    print(f"    direction confidence {ph.get('confidence')}, estimated azimuth {ph.get('estimated_azimuth_deg')}\n")
    print(f"**Camera** — {cam.get('lat')}, {cam.get('lon')} (NYC_TM {cam.get('x'):.0f}, "
          f"{cam.get('y'):.0f}) at z {cam.get('z'):.1f} m NAVD88 | azimuth {cam.get('azimuth_deg'):.1f}°, "
          f"pitch {cam.get('pitch_deg', 0.0):+.1f}° | {cam.get('focal_mm'):.0f} mm on "
          f"{cam.get('sensor_mm'):.0f} mm ({cam.get('hfov_deg'):.1f}° horizontal"
          f"{', portrait' if cam.get('portrait') else ''}) | "
          f"{cam.get('resolution', ['?', '?'])[0]}x{cam.get('resolution', ['?', '?'])[1]}.")
    for label, key in (("origin   ", "camera_origin"), ("clearance", "clearance")):
        print(f"    {label}: {json.dumps(f.get(key))}")
    for label, key in (("azimuth  ", "azimuth_reason"), ("lens     ", "lens_reason"),
                       ("pitch    ", "pitch_reason")):
        print(f"    {label}: {rec.get(key)}")
    print()

    print(f"**Sun** — azimuth {sun.get('azimuth_deg', 0):.1f}°, elevation {sun.get('elevation_deg', 0):.1f}° "
          f"at {sun.get('local')} ({sun.get('time_source')}); {lt.get('direct_normal_irradiance_w_m2')} "
          f"W/m² direct normal, sky at strength {lt.get('background_strength'):.4f}, "
          f"{lt.get('view_transform')}, {lt.get('exposure_stops'):+.2f} stops.")
    ck = f.get("crowd_clock") or {}
    if ck:
        print(f"    {ck.get('date')} is a **{ck.get('weekday')}**; the crowd was drawn for "
              f"**{ck.get('means')}**  ({ck.get('note')})")
    print()

    sub = f.get("subject") or {}
    if sub.get("name"):
        hp = sub.get("height_probe") or {}
        st = f.get("sightline") or {}
        print(f"**Subject** — {sub['name']} at {sub.get('distance_m')} m.")
        print(f"    height   : {json.dumps(hp)}")
        print(f"    sightline: {json.dumps(st)}\n")

    b, pv, pr, kit, ag = (f[k] for k in ("buildings", "pavement", "props", "kit", "agents"))
    lm, tr = f["landmarks"], f["terrain"]
    dressed = ((rec.get("scene") or {}).get("materials") or {}).get("dressed") or {}
    n_dressed = len(dressed)
    # "at the cap" is `capped_at` being present, not a large scale: red_brick is corrected by
    # 1.411 and is not capped; roof_membrane binds at 4.0 and states the residual it cannot reach.
    capped = sorted(k for k, v in dressed.items()
                    if isinstance(v, dict) and (v.get("albedo") or {}).get("capped_at") is not None)
    kinds = ", ".join(f"{v:,} {k.replace('marking_', '').replace('_', ' ')}"
                      for k, v in sorted((pv.get("per_kind") or {}).items(), key=lambda kv: -kv[1]))
    cone = (lm.get("frustum") or {}).get("in_cone")
    print(f"**In the scene**, within {pv.get('radius_m', 0):.1f} m of the camera and not all of it in "
          f"frame — {b.get('tiles')} building tiles ({b.get('triangles', 0):,} tris), "
          f"{lm.get('placed', 0)} landmark models"
          + (f" of which **{cone} can fall inside the {cam.get('hfov_deg'):.1f}° frame**" if cone is not None else "")
          + f", {pv.get('placed', 0):,} pavement polygons ({kinds}), {pr.get('placed', 0)} props of "
            f"the {pr.get('in_range', 0):,} in range, {kit.get('total', 0):,} kit pieces, "
            f"{ag.get('vehicles', 0)} vehicles and {ag.get('pedestrians', 0)} people; "
            f"{f.get('triangles', 0):,} triangles. Ground mesh {tr.get('triangles', 0):,} triangles, "
            f"{tr.get('holes', 0)} holes. {n_dressed} city "
            f"surfaces are dressed from the shared photographic catalogue.\n")
    print(f"    landmarks: {json.dumps(lm.get('frustum'))}")
    print(f"    props    : {json.dumps(pr)}")
    print(f"    kit      : {json.dumps(kit)}")
    print(f"    agents   : {json.dumps(ag)}")
    print(f"    materials: {n_dressed} dressed; at the albedo cap {capped}")
    print(f"    surfaces : {sorted(dressed)}\n")

    r, p, q = fs.get("render") or {}, fs.get("reference") or {}, fs.get("render_over_reference") or {}
    if r and p:
        print("| | render | photograph | ratio |")
        print("|---|---|---|---|")
        for k in ("mean", "sd", "p05", "p95", "chroma"):
            print(f"| {k} | **{r.get(k)}** | **{p.get(k)}** | "
                  f"{('**' + str(q[k]) + '**') if q.get(k) is not None else '—'} |")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1]))
