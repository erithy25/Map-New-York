"""One compact brief per comparison sheet: everything an assessment may cite, and nothing else.

Every figure an assessment quotes has to be in that sheet's own record -- tools/assessment_check.py
rejects the rest, and it has already caught a coordinate pasted in from another sheet.  So this
prints the record's numbers in the form they will be quoted in, rather than leaving them to be
re-derived by hand each time.
"""
import json
import subprocess
import sys
from pathlib import Path

REPO = Path("/home/user/Map-New-York")
slug = sys.argv[1]
d = json.loads((REPO / "docs/verification/comparison" / slug / "render.json").read_text())
facts = json.loads(subprocess.run([sys.executable, "tools/sheet_facts.py", slug], cwd=REPO,
                                  capture_output=True, text=True).stdout)
subprocess.run([sys.executable, "tools/frame_stats.py", slug], cwd=REPO, capture_output=True)
fs = json.loads((REPO / "docs/verification/comparison" / slug / "frame_stats.json").read_text())

print(f"=== {slug} :: {facts['name']}")
print(f"caption   {d['camera_caption']}")
print(f"rendered  {d['rendered_at']}   status {d['status']}   frame {d['frame']}")
r, p, q = fs["render"], fs["reference"], fs["render_over_reference"]
print(f"render    mean {r['mean']} sd {r['sd']} p05 {r['p05']} p95 {r['p95']} chroma {r['chroma']}")
print(f"photo     mean {p['mean']} sd {p['sd']} p05 {p['p05']} p95 {p['p95']} chroma {p['chroma']}  ({p['width']}x{p['height']})")
print(f"ratios    {q}")
ref = facts["reference"]
print(f"ref       {ref['file']} by {ref['author']}, {ref['licence']}, {ref['date_taken']}; "
      f"confidence {ref['confidence']}, estimated azimuth {ref['estimated_azimuth_deg']}")
print(f"page      {d['reference_photo'].get('page_url')}")
print(f"title     {d['reference_photo'].get('title')}")
print(f"sun       {json.dumps(facts['sun'])}")
print(f"clock     {json.dumps(facts['crowd_clock'])}")
print(f"lighting  {json.dumps({k: d['lighting'][k] for k in ('direct_normal_irradiance_w_m2', 'background_strength', 'exposure_stops', 'view_transform')})}")
print(f"origin    {json.dumps(facts['camera_origin'])}")
print(f"clearance {json.dumps(facts['clearance'])}")
if facts.get("subject", {}).get("name"):
    print(f"subject   {json.dumps(facts['subject'])}")
    print(f"sightline {json.dumps(facts['sightline'])}")
print(f"azimuth   {facts['azimuth_reason']}")
for key in ("triangles", "buildings", "terrain"):
    print(f"{key:9s} {json.dumps(facts[key])}")
lm = facts["landmarks"]
print(f"landmarks placed {lm['placed']}, own ground {lm['own_ground_m2']} m2")
if lm.get("frustum"):
    f = lm["frustum"]
    print(f"          in cone {f['in_cone']}, behind/aside {f['behind_or_aside']}")
    for n in f["in_cone_names"]:
        print(f"            IN  {n['name']}  {n['distance_m']:.1f} m, off-axis {n['off_axis_deg']:.1f}")
    for n in f["behind_or_aside_names"]:
        print(f"            OUT {n}")
print(f"pavement  {json.dumps(facts['pavement'])}")
print(f"props     {json.dumps(facts['props'])}")
print(f"kit       {json.dumps(facts['kit'])}")
print(f"agents    {json.dumps(facts['agents'])}")
m = d["scene"]["materials"]["dressed"]
capped = [k for k, v in m.items() if v.get("albedo", {}).get("capped_at")]
print(f"materials {len(m)} dressed; at the albedo cap: {capped}")
sn = d["scene"]["agents"].get("snapshot") or {}
print(f"npc       archetypes available {sn.get('npc_archetypes_available')}, "
      f"bodies imported {sn.get('npc_bodies_imported')}, folded {sn.get('npc_archetypes_folded')}")
