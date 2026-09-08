#!/usr/bin/env python3
"""Compile every plugin translation unit that does not need Unreal, and say which do.

    python3 unreal/tools/syntax_check.py            # check, print a summary
    python3 unreal/tools/syntax_check.py --list     # also list every file and its verdict

**Why this exists.** ``docs/DEFINITION_OF_DONE.md`` says Unreal compilation cannot be executed in
this container and that the plugin is therefore "authored as complete source with a per-file review
record".  That is true of the code that includes ``CoreMinimal.h`` -- and it was being said of *all*
of it.  Measured, a large part of the plugin is plain C++ that a system compiler builds without
Unreal present: the ``nycsim_gameplay`` adapter layer and the generated ``CoreUnity`` stubs that
wrap ``core/src``.  A review record is weaker evidence than a compiler, and where the compiler can
run it should.

A file is reported as needing Unreal only after following its own first-party includes: checking the
``.cpp`` alone missed headers that pull in ``CoreMinimal.h`` one level down, which is how a first
version of this script called 58 files broken when most of them were simply not for us to build.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SOURCE = REPO / "unreal" / "NYCSim" / "Source"

INCLUDE_DIRS = [
    SOURCE / "NYCSimRuntime" / "Private",
    SOURCE / "NYCSimRuntime" / "Public",
    SOURCE / "NYCSimCore" / "Private",
    SOURCE / "NYCSimCore" / "Public",
    REPO / "core" / "include",
    REPO / "core" / "src",
]

#: Headers that only exist inside an Unreal build.  A translation unit that reaches one of these,
#: directly or through its own headers, is not ours to compile here.
UNREAL_HEADERS = re.compile(
    r'#\s*include\s+[<"]('
    r'CoreMinimal|Engine/|GameFramework/|Components/|UObject/|Kismet/|Sound/|Chaos|'
    r'Modules/|Misc/|HAL/|Templates/|Containers/|Math/|Delegates/|Subsystems/|'
    r'DSP/|MetasoundFrontend|AudioDevice|.*\.generated\.h'
    r')')

INCLUDE_RE = re.compile(r'#\s*include\s+"([^"]+)"')


def resolve(name: str, near: Path) -> Path | None:
    for base in [near.parent, *INCLUDE_DIRS]:
        p = base / name
        if p.is_file():
            return p
    return None


def needs_unreal(path: Path, seen: set[Path] | None = None) -> bool:
    """True when this file, or anything first-party it includes, reaches an Unreal-only header."""
    seen = seen if seen is not None else set()
    if path in seen or not path.is_file():
        return False
    seen.add(path)
    try:
        text = path.read_text(errors="replace")
    except OSError:
        return False
    if UNREAL_HEADERS.search(text):
        return True
    for name in INCLUDE_RE.findall(text):
        target = resolve(name, path)
        if target is not None and needs_unreal(target, seen):
            return True
    return False


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--list", action="store_true", help="print every file and its verdict")
    ap.add_argument("--cxx", default="g++")
    a = ap.parse_args(argv)

    flags = ["-std=c++17", "-fsyntax-only", "-Wall", "-Wextra", "-Wno-unused-parameter"]
    flags += [f"-I{d}" for d in INCLUDE_DIRS]
    ok, failed, skipped = [], [], []
    for f in sorted(SOURCE.rglob("*.cpp")):
        rel = f.relative_to(REPO)
        if needs_unreal(f):
            skipped.append(rel)
            if a.list:
                print(f"   unreal   {rel}")
            continue
        r = subprocess.run([a.cxx, *flags, str(f)], capture_output=True, text=True)
        if r.returncode == 0:
            ok.append(rel)
            if a.list:
                print(f"   ok       {rel}")
        else:
            failed.append((rel, r.stderr.strip().splitlines()[:4]))
            print(f"   FAILED   {rel}")
            for line in r.stderr.strip().splitlines()[:4]:
                print(f"            {line}")
    total = len(ok) + len(failed) + len(skipped)
    print(f"\n{total} translation units: {len(ok)} compile clean here, {len(failed)} fail, "
          f"{len(skipped)} need Unreal and are reviewed instead")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
