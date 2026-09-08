"""Build every NYCSim street prop and vegetation asset to ``blender_out/props/<id>.glb`` + a catalog entry each.

Run (headless bpy, one process — the box is shared with the other asset agents)::

    nice -n 10 python3 blender/props/build_props.py                 # everything
    nice -n 10 python3 blender/props/build_props.py --module p_lighting
    nice -n 10 python3 blender/props/build_props.py --only hydrant_fdny tree_platanus_large
    python3 blender/props/build_props.py --list                     # ids, kinds, nominal sizes (no bpy work)

Conventions are in ``_core`` (metres, Z-up, origin at ground contact, +Y facing, LOD0/LOD1 with MSFT_lod).
``dataset_kind`` is the ``kind`` name of DATA_CONTRACTS §8 (``pipeline/nycsim_pipeline/furniture/catalog.py``);
props that have no §8 kind yet use a name from :data:`EXTENSION_KINDS` — those are the additions this stage
proposes to §8 and they are listed in ``docs/verification/props/REPORT.md``.
"""
from __future__ import annotations

import argparse
import importlib
import json
import logging
import sys
import time
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(_HERE.parents[0] / "common"))

log = logging.getLogger("nycsim.props.build")

MODULES: tuple[str, ...] = ("p_lighting", "p_traffic", "p_signs", "p_furniture", "p_transit", "p_construction", "p_vegetation")

# §8 kinds that already exist (pipeline/nycsim_pipeline/furniture/catalog.py, owned by the furniture stage).
CONTRACT_KINDS: tuple[str, ...] = (
    "tree", "hydrant", "bus_shelter", "linknyc", "newsstand", "bike_shelter", "bike_rack", "citibike_dock",
    "subway_entrance", "curb_ramp", "rtpi_sign", "bench", "waste_basket", "mailbox", "street_lamp", "billboard",
    "artwork", "memorial", "drinking_fountain", "payphone", "vending_machine", "flagpole", "utility_pole", "manhole",
    "bus_stop_sign", "parks_comfort_station", "parks_recreation_center", "parks_building", "cooling_tower",
    "swimming_pool", "misc_structure", "subway_vent_grate", "subway_emergency_exit", "steam_vent",
)
# Kinds this stage needs that §8 does not define yet. Signals and signs are produced by the roads stage
# (roads/signals.parquet, roads/signs.parquet — DATA_CONTRACTS §7), the rest are rule-placed street furniture.
EXTENSION_KINDS: dict[str, str] = {
    "traffic_signal": "vehicle signal assembly at a signalised node (roads/nodes.parquet is_signalized; §7)",
    "pedestrian_signal": "pedestrian signal head with countdown at a signalised crossing (§7)",
    "ped_pushbutton": "accessible pedestrian signal push-button station",
    "road_sign": "regulatory/warning sign blank; legend from roads/signs.parquet mutcd_code + text (§7)",
    "sign_post": "U-channel or square-tube sign support",
    "street_name_sign": "NYC street-name blade and bracket (roads/signs.parquet source=1)",
    "standpipe": "fire-department siamese standpipe connection",
    "bollard": "sidewalk/plaza bollard",
    "planter": "concrete street planter",
    "tree_guard": "tree-pit guard rail",
    "tree_grate": "tree-pit cast-iron grate",
    "trash_pile": "bagged refuse set out for DSNY collection",
    "food_cart": "licensed sidewalk food cart",
    "work_zone_device": "channelising device or barrier (cone, drum, jersey barrier, plate, fence)",
    "muni_meter": "DOT parking pay station (Muni-Meter)",
    "fire_alarm_box": "FDNY emergency reporting system street box",
    "fauna": "static street animal (pigeon, rat)",
    "mta_bullet": "MTA route bullet decal meshes",
}
ALL_KINDS = set(CONTRACT_KINDS) | set(EXTENSION_KINDS)


def load_specs(modules=MODULES) -> list:
    specs = []
    for name in modules:
        mod = importlib.import_module(name)
        got = mod.specs() if hasattr(mod, "specs") else list(mod.SPECS)
        for sp in got:
            sp.tags = list(sp.tags) + [f"module:{name}"]
            sp.variants = [v for v in sp.variants if v != sp.id]
        specs.extend(got)
    ids = [s.id for s in specs]
    dup = sorted({i for i in ids if ids.count(i) > 1})
    if dup:
        raise SystemExit(f"duplicate prop ids: {dup}")
    bad = sorted({s.dataset_kind for s in specs} - ALL_KINDS)
    if bad:
        raise SystemExit(f"dataset_kind not in DATA_CONTRACTS §8 nor EXTENSION_KINDS: {bad}")
    missing = sorted({v for s in specs for v in s.variants} - set(ids))
    if missing:
        raise SystemExit(f"variants reference unknown prop ids: {missing}")
    return specs


def _write_asset_catalog() -> int:
    """Re-aggregate ``props_asset_catalog.json`` from the per-asset catalogue files.

    The aggregate is what every consumer reads -- ``furniture/assets.py`` groups it by
    ``dataset_kind`` to decide which asset a placement resolves to -- and nothing wrote it, so a
    ``--only`` build left a new asset on disk and invisible to the city.  The MTA bus stop sign was
    exported, catalogued per asset, and still absent from the aggregate the placer reads
    (docs/DEVIATIONS.md J58).  Written on every run, including a partial one.
    """
    import _core as C

    entries = []
    for f in sorted(C.CATALOG_DIR.glob("*.json")):
        try:
            entries.append(json.loads(f.read_text()))
        except (OSError, ValueError) as exc:
            log.warning("catalogue entry %s unreadable: %s", f.name, exc)
    entries.sort(key=lambda e: e.get("id") or "")
    doc = {"schema_version": 1, "count": len(entries), "entries": entries}
    (C.PROPS_OUT / "props_asset_catalog.json").write_text(json.dumps(doc, indent=1) + "\n")
    log.info("asset catalogue: %d entries", len(entries))
    return len(entries)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--module", action="append", default=None, choices=list(MODULES))
    ap.add_argument("--only", nargs="*", default=None, help="build just these prop ids")
    ap.add_argument("--skip-existing", action="store_true", help="skip ids whose glb is already newer than its builder module")
    ap.add_argument("--list", action="store_true", help="print the registry and exit (no bpy)")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO, format="%(levelname).1s %(message)s")

    specs = load_specs(tuple(args.module) if args.module else MODULES)
    if args.only:
        want = set(args.only)
        unknown = sorted(want - {s.id for s in specs})
        if unknown:
            raise SystemExit(f"unknown prop ids: {unknown}")
        specs = [s for s in specs if s.id in want]
    if args.list:
        for s in specs:
            print(f"{s.id:34s} {s.category:12s} {s.dataset_kind:20s} {tuple(round(v, 2) for v in s.nominal)}")
        print(f"{len(specs)} props; kinds used: {len(sorted({s.dataset_kind for s in specs}))}")
        return 0

    import _core as C
    C.PROPS_OUT.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    built, failed = [], []
    for i, sp in enumerate(specs, 1):
        glb = C.PROPS_OUT / f"{sp.id}.glb"
        if args.skip_existing and glb.exists():
            log.info("[%3d/%3d] %-34s skip (exists)", i, len(specs), sp.id)
            continue
        try:
            entry = C.build_and_export(sp)
            built.append(entry)
            log.info("[%3d/%3d] %-34s %6d/%5d tris  %8.1f kB  %s", i, len(specs), sp.id,
                     entry["polycount"]["lod0_tris"], entry["polycount"]["lod1_tris"], entry["glb_bytes"] / 1024,
                     [round(v, 2) for v in entry["size_m"]])
        except Exception:
            log.exception("[%3d/%3d] %-34s FAILED", i, len(specs), sp.id)
            failed.append(sp.id)
    summary = {
        "schema_version": 1, "built": len(built), "failed": failed, "seconds": round(time.time() - t0, 1),
        "texture_source": C.texture_source(),
        "total_lod0_tris": sum(e["polycount"]["lod0_tris"] for e in built),
        "total_glb_bytes": sum(e["glb_bytes"] for e in built),
        "extension_kinds": EXTENSION_KINDS,
        "kinds_used": sorted({e["dataset_kind"] for e in built}),
    }
    (C.PROPS_OUT / "build_summary.json").write_text(json.dumps(summary, indent=1, sort_keys=True) + "\n")
    _write_asset_catalog()
    log.info("built %d props in %.1f s (%.1f MB, %d tris); failed: %s", len(built), summary["seconds"],
             summary["total_glb_bytes"] / 1e6, summary["total_lod0_tris"], failed or "none")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
