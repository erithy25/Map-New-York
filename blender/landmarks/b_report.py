"""Generate ``docs/verification/landmarks/REPORT_B.md`` from what is actually on disk.

Every number in the report comes from the exported ``.glb`` catalog entries, the build summary and the per-landmark
verification directories, so the report cannot drift from the models.  Run it after ``b_build_all.py``:

    nice -n 10 python3 blender/landmarks/b_report.py
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "blender_out" / "landmarks"
CATALOG = OUT / "catalog"
VERIFY = REPO / "docs" / "verification" / "landmarks"
REPORT = VERIFY / "REPORT_B.md"

GROUPS = [
    ("Bridges", ["b_brooklyn_bridge", "b_manhattan_bridge", "b_williamsburg_bridge", "b_queensboro_bridge",
                 "b_george_washington_bridge", "b_verrazzano_narrows", "b_rfk_triborough", "b_throgs_neck",
                 "b_bronx_whitestone", "b_hell_gate", "b_high_bridge", "b_pulaski", "b_kosciuszko",
                 "b_roosevelt_island_tram"]),
    ("Tunnels", ["b_lincoln_tunnel_portals", "b_holland_tunnel_portals", "b_queens_midtown_portals",
                 "b_hugh_carey_portals"]),
    ("World Trade Center", ["b_one_world_trade_center", "b_wtc_site"]),
    ("Harbour", ["b_statue_of_liberty", "b_ellis_island_main", "b_governors_island"]),
    ("Parks and monuments", ["b_washington_square_arch", "b_bethesda_terrace", "b_bow_bridge", "b_belvedere_castle",
                             "b_central_park_walls_gates", "b_unisphere", "b_grants_tomb",
                             "b_columbus_circle_monument", "b_soldiers_sailors_arch", "b_prospect_park_boathouse"]),
    ("Coney Island", ["b_coney_island"]),
]

KEY_DIMS = {
    "b_brooklyn_bridge": ("main span", "main_span_m", 486.3), "b_manhattan_bridge": ("main span", "main_span_m", 451.1),
    "b_williamsburg_bridge": ("main span", "main_span_m", 487.68),
    "b_queensboro_bridge": ("longest span", "longest_span_m", 360.3),
    "b_george_washington_bridge": ("main span", "main_span_m", 1066.8),
    "b_verrazzano_narrows": ("main span", "main_span_m", 1298.4),
    "b_rfk_triborough": ("suspension main span", "suspension_main_span_m", 420.62),
    "b_throgs_neck": ("main span", "main_span_m", 548.64),
    "b_bronx_whitestone": ("main span", "main_span_m", 701.04),
    "b_hell_gate": ("arch span (outer faces)", "arch_span_outer_m", 310.0),
    "b_high_bridge": ("length", "length_m", 442.0), "b_pulaski": ("bascule span", "main_span_m", 53.95),
    "b_kosciuszko": ("main span", "main_span_m", 190.2),
    "b_roosevelt_island_tram": ("East River span", "river_span_m", 360.9),
    "b_lincoln_tunnel_portals": ("centre tube", "centre_tube_length_m", 2504.2),
    "b_holland_tunnel_portals": ("north tube", "north_tube_length_m", 2608.5),
    "b_queens_midtown_portals": ("north tube", "north_tube_length_m", 1955.0),
    "b_hugh_carey_portals": ("length", "length_m", 2779.2),
    "b_one_world_trade_center": ("spire tip", "spire_m", 541.3),
    "b_wtc_site": ("3 WTC height", "wtc3_m", 329.2),
    "b_statue_of_liberty": ("ground to torch", "ground_to_torch_m", 92.99),
    "b_ellis_island_main": ("tower height", "tower_height_m", 30.5),
    "b_governors_island": ("Castle Williams diameter", "castle_williams_diameter_m", 60.96),
    "b_washington_square_arch": ("height", "height_m", 23.47),
    "b_bethesda_terrace": ("fountain basin", "basin_diameter_m", 29.26),
    "b_bow_bridge": ("length", "length_m", 26.52),
    "b_belvedere_castle": ("tower height", "tower_height_m", 16.5),
    "b_central_park_walls_gates": ("perimeter", "perimeter_m", 9656.0),
    "b_unisphere": ("height", "height_m", 42.67), "b_grants_tomb": ("height", "height_m", 45.72),
    "b_columbus_circle_monument": ("Deutsche Bank Center", "deutsche_bank_center_m", 228.6),
    "b_soldiers_sailors_arch": ("height", "height_m", 24.38),
    "b_prospect_park_boathouse": ("arcade bays", "arcade_bays", 6),
    "b_coney_island": ("Parachute Jump", "parachute_jump_height_m", 79.86),
}


def _entry(lid: str) -> dict | None:
    p = CATALOG / f"{lid}.json"
    if not p.exists():
        return None
    try:
        return json.load(open(p))
    except (OSError, json.JSONDecodeError):
        return None


def _renders(lid: str) -> list[str]:
    d = VERIFY / lid
    return sorted(p.name for p in d.glob("*.png")) if d.exists() else []


def _pytest_summary() -> str:
    try:
        p = subprocess.run([sys.executable, "-m", "pytest", "tests/test_landmarks_b.py", "-q", "--no-header",
                            "-p", "no:cacheprovider"], cwd=str(REPO), capture_output=True, text=True, timeout=3600)
        lines = [ln for ln in (p.stdout or "").strip().splitlines() if ln.strip()]
        return "\n".join(lines[-14:]) or "(no output)"
    except Exception as e:  # the report must still be written if pytest cannot run
        return f"(pytest could not be run: {e})"


def main() -> int:
    summary_path = VERIFY / "build_summary.json"
    summary = json.load(open(summary_path)) if summary_path.exists() else {"results": []}
    by_id = {r["id"]: r for r in summary.get("results", [])}
    total_tris = 0
    total_bytes = 0
    rows: list[str] = []
    dim_rows: list[str] = []
    missing: list[str] = []
    for group, ids in GROUPS:
        rows.append(f"| **{group}** | | | | | | |")
        for lid in ids:
            e = _entry(lid)
            if e is None:
                missing.append(lid)
                rows.append(f"| `{lid}` | — | — | — | — | — | not built |")
                continue
            l0 = e["lods"].get("lod0", {})
            l1 = e["lods"].get("lod1", {})
            total_tris += l0.get("triangles", 0)
            total_bytes += l0.get("bytes", 0) + l1.get("bytes", 0)
            frac = (100.0 * l1.get("triangles", 0) / l0["triangles"]) if l0.get("triangles") else 0.0
            secs = by_id.get(lid, {}).get("seconds", "")
            rows.append(f"| `{lid}` | {e.get('name', '')} | {l0.get('triangles', 0):,} | "
                        f"{l1.get('triangles', 0):,} | {frac:.0f} % | {l0.get('bytes', 0) / 1e6:.2f} MB | "
                        f"{len(_renders(lid))} renders, {secs} s |")
            label, key, published = KEY_DIMS.get(lid, ("", "", 0))
            if key and key in e:
                got = e[key]
                err = "" if not published else f"{abs(float(got) - float(published)) / float(published) * 100.0:.2f} %"
                dim_rows.append(f"| `{lid}` | {label} | {published} | {got} | {err} | "
                                f"{e.get('alignment_source', e.get('footprint_source', 'published'))} |")

    lines = [
        "# Landmarks — agent B verification report",
        "",
        f"Bridges, tunnels, the World Trade Center site, the harbour monuments, park structures and Coney Island. "
        f"Generated {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())} by `blender/landmarks/b_report.py` from the "
        f"exported `.glb` catalog entries — every number below is read back off disk.",
        "",
        "## 1. What was built",
        "",
        f"**{len(by_id) or sum(len(i) for _, i in GROUPS)} landmark assets**, each exported at two levels of detail to "
        "`blender_out/landmarks/<id>.glb` and `<id>_lod1.glb`, with a catalog entry in "
        "`blender_out/landmarks/catalog/<id>.json` carrying the published dimensions, the alignment source and the "
        "fidelity statement.",
        "",
        "| id | name | LOD0 tris | LOD1 tris | LOD1/LOD0 | LOD0 size | verification |",
        "|---|---|---:|---:|---:|---:|---|",
        *rows,
        "",
        f"Total LOD0 geometry: **{total_tris:,} triangles**; total exported bytes (both LODs): "
        f"**{total_bytes / 1e6:.1f} MB**.",
        "",
        "## 2. Published dimension vs. what the model records",
        "",
        "| id | dimension | published | model | error | placement source |",
        "|---|---|---:|---:|---:|---|",
        *dim_rows,
        "",
        "`tests/test_landmarks_b.py` goes further than this table: it decodes each `.glb` and **measures** the "
        "geometry — the height of the model's highest point, and the centre-to-centre distance between the named "
        "tower/pier nodes — against the published figure, with a 1 % tolerance on the primary set.",
        "",
        "## 3. Test results",
        "",
        "```",
        _pytest_summary(),
        "```",
        "",
    ]
    if missing:
        lines += ["> **Not built:** " + ", ".join(f"`{m}`" for m in missing), ""]
    VERIFY.mkdir(parents=True, exist_ok=True)
    body = REPORT.read_text() if REPORT.exists() else ""
    marker = "<!-- generated-above; hand-written narrative below -->"
    narrative = body.split(marker, 1)[1] if marker in body else ""
    REPORT.write_text("\n".join(lines) + marker + "\n" + narrative)
    print(f"wrote {REPORT.relative_to(REPO)} ({REPORT.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
