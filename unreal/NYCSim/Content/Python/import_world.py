"""NYCSim world import — the single entry point that turns ``data/processed`` into a playable UE world.

    UnrealEditor-Cmd <path>/NYCSim.uproject -run=NYCImport                        # C++ driver (recommended)
    UnrealEditor-Cmd <path>/NYCSim.uproject -run=pythonscript -script="import_world.py"
    (in the editor)  import import_world; import_world.main([])

Stages, in order:
  1. stage    copy crs.json, runtime/*.nycb, live/*.json, unreal_water.json and the per-tile water masks into
              Content/NYCSim/{Runtime,Live} so the packaged game ships them (the C++ commandlet does the same
              work; this implementation exists so the script also runs standalone).
  2. assets   import_assets.main() — meshes, textures, fonts, MPC_Weather and the base materials.
  3. levels   build_levels.main()  — the NYC map, per-tile L0/L1 levels, skyline levels, landscapes.
  4. report   Saved/NYCSim/import_report.json with counts, timings and every skip with its reason.

Nothing here invents content: every asset comes from a manifest entry whose source file exists on disk. Missing
inputs are reported, never faked.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time

import unreal

import build_levels
import import_assets

LOG = unreal.log
WARN = unreal.log_warning
ERROR = unreal.log_error

RAW_SETTINGS = {"raw_copy", "json_copy"}


def project_dir() -> str:
    return unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())


def content_dir() -> str:
    return unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_content_dir())


def default_manifest_path() -> str:
    return os.path.normpath(os.path.join(project_dir(), "..", "..", "data", "processed", "unreal_manifest.json"))


def content_path_to_file(dst: str) -> str:
    relative = dst[len("/Game/"):] if dst.startswith("/Game/") else dst.lstrip("/")
    return os.path.join(content_dir(), *relative.split("/"))


def stage_files(manifest: dict, repo_root: str, tiles: set | None, dry_run: bool) -> dict:
    copied, missing = 0, []
    for entry in manifest.get("entries", []):
        settings = entry.get("import_settings", "")
        kind = entry.get("kind", "")
        tile = entry.get("tile")
        if tiles is not None and tile and tile not in tiles:
            continue
        if settings in RAW_SETTINGS:
            target = content_path_to_file(entry["dst"])
        elif kind == "water_mask" and tile:
            target = os.path.join(content_dir(), "NYCSim", "Runtime", "water_masks", f"{tile}.png")
        else:
            continue
        source = entry["src"]
        if not os.path.isabs(source):
            source = os.path.join(repo_root, source)
        if not os.path.isfile(source):
            missing.append(source)
            continue
        if dry_run:
            LOG(f"[dry run] stage {source} -> {target}")
            copied += 1
            continue
        os.makedirs(os.path.dirname(target), exist_ok=True)
        shutil.copyfile(source, target)
        copied += 1
    return {"copied": copied, "missing": missing}


def write_report(report: dict) -> str:
    saved = os.path.join(project_dir(), "Saved", "NYCSim")
    os.makedirs(saved, exist_ok=True)
    path = os.path.join(saved, "import_report.json")
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=1, sort_keys=False)
    return path


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="NYCSim world import")
    parser.add_argument("--manifest", default=None)
    parser.add_argument("--tiles", default="")
    parser.add_argument("--max-tiles", type=int, default=0)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--skip-stage", action="store_true")
    parser.add_argument("--skip-assets", action="store_true")
    parser.add_argument("--skip-levels", action="store_true")
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    manifest_path = args.manifest or default_manifest_path()
    if not os.path.isfile(manifest_path):
        ERROR(f"manifest not found: {manifest_path} (run `python -m nycsim_pipeline.unreal.manifest` first)")
        return 1
    with open(manifest_path, "r", encoding="utf-8") as handle:
        manifest = json.load(handle)
    if manifest.get("schema") != "unreal_manifest/1":
        ERROR(f"unsupported manifest schema {manifest.get('schema')!r}")
        return 1
    repo_root = manifest.get("repo_root") or os.path.dirname(os.path.dirname(os.path.dirname(manifest_path)))
    tiles = {t.strip() for t in args.tiles.split(",") if t.strip()} or None

    started = time.time()
    report = {
        "manifest": manifest_path,
        "manifest_generated_at": manifest.get("generated_at"),
        "manifest_git_commit": manifest.get("git_commit"),
        "repo_root": repo_root,
        "content_dir": content_dir(),
        "entries": manifest.get("counts", {}),
        "manifest_warnings": manifest.get("warnings", []),
        "stages": {},
    }

    forwarded = ["--manifest", manifest_path]
    if args.tiles:
        forwarded += ["--tiles", args.tiles]
    if args.max_tiles:
        forwarded += ["--max-tiles", str(args.max_tiles)]
    if args.force:
        forwarded += ["--force"]
    if args.dry_run:
        forwarded += ["--dry-run"]

    status = 0
    if not args.skip_stage:
        report["stages"]["stage"] = stage_files(manifest, repo_root, tiles, args.dry_run)
        if report["stages"]["stage"]["missing"]:
            WARN(f"stage: {len(report['stages']['stage']['missing'])} sources missing")
    if not args.skip_assets:
        code = import_assets.main(forwarded)
        report["stages"]["assets"] = {"exit": code}
        status = status or code
    if not args.skip_levels:
        code = build_levels.main([a for a in forwarded if a != "--force"])
        report["stages"]["levels"] = {"exit": code}
        status = status or code

    report["seconds"] = round(time.time() - started, 1)
    report["exit"] = status
    path = write_report(report)
    LOG(f"import_world: finished in {report['seconds']} s, report at {path}")
    return status


if __name__ == "__main__":
    sys.exit(main())
