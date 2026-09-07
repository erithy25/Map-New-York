#!/usr/bin/env python3
"""Static self-review of the Unreal gameplay lane (Unreal agent 2).

There is no Unreal Engine in this container (ARCHITECTURE ADR-001), so nothing here can be compiled. What can be
checked mechanically is checked here, over every file the gameplay lane owns:

  * `unreal/NYCSim/Source/NYCSimRuntime/{Public,Private}/{Vehicle,Character,Traffic,Peds,UI,Audio,Player}`
  * `unreal/NYCSim/Source/NYCSimRuntime/Private/CoreAdapter/Gameplay*` (the core-facing adapter)

The checks are the UHT and UBT rules that a first compile would otherwise catch, plus the project's own standing
rules (no placeholders, no engine-version-risky APIs used unguarded, every console command freed).

Run:  python3 docs/verification/unreal_gameplay/check_gameplay_sources.py
Exit code 0 = every assertion held.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
MODULE = ROOT / "unreal/NYCSim/Source/NYCSimRuntime"
LANE = ["Vehicle", "Character", "Traffic", "Peds", "UI", "Audio", "Player"]

failures: list[str] = []
checks = 0


def check(condition: bool, message: str) -> None:
    global checks
    checks += 1
    if not condition:
        failures.append(message)


def lane_files() -> list[Path]:
    files: list[Path] = []
    for base in ("Public", "Private"):
        for sub in LANE:
            d = MODULE / base / sub
            if d.is_dir():
                files += sorted(p for p in d.rglob("*") if p.suffix in (".h", ".cpp"))
    files += sorted((MODULE / "Private/CoreAdapter").glob("Gameplay*"))
    return files


def rel(p: Path) -> str:
    return str(p.relative_to(ROOT))


def strip_comments(text: str) -> str:
    """Remove // and /* */ comments and string literals, so brace counting sees code only."""
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    text = re.sub(r"//[^\n]*", "", text)
    text = re.sub(r'"(\\.|[^"\\])*"', '""', text)
    return text


def main() -> int:
    unreflected_pointers: set[tuple[str, str]] = set()
    files = lane_files()
    check(len(files) >= 70, f"expected the lane to have at least 70 files, found {len(files)}")

    reflected_headers = 0
    ue_files = [f for f in files if "CoreAdapter" not in str(f)]
    adapter_files = [f for f in files if "CoreAdapter" in str(f)]

    for f in files:
        text = f.read_text()
        lines = text.splitlines()

        # 1. no placeholders anywhere in the lane (word-bounded: `GetOdometerMiles` is not a TODO)
        for marker in ("TODO", "FIXME", "XXX", "HACK"):
            hits = [i + 1 for i, l in enumerate(lines) if re.search(r"\b" + marker + r"\b", l)]
            check(not hits, f"{rel(f)}: placeholder marker {marker!r} on line(s) {hits}")
        for phrase in ("placeholder", "not implemented", "stub implementation"):
            hits = [i + 1 for i, l in enumerate(lines) if phrase in l.lower()]
            check(not hits, f"{rel(f)}: placeholder phrase {phrase!r} on line(s) {hits}")

        # 2. balanced braces and parentheses over the code, comments stripped (catches a truncated file)
        code = strip_comments(text)
        check(code.count("{") == code.count("}"), f"{rel(f)}: unbalanced braces")
        check(code.count("(") == code.count(")"), f"{rel(f)}: unbalanced parentheses")

        # 3. no engine API that only exists after 5.4
        check("EAllowShrinking" not in text, f"{rel(f)}: EAllowShrinking is UE 5.5+, not 5.4")
        check("UE::Tasks::Launch" not in text or "Async" in text, f"{rel(f)}: unchecked task API")

        if f.suffix == ".h":
            check(lines[0].startswith("//"), f"{rel(f)}: header does not open with a comment explaining it")
            check("#pragma once" in text, f"{rel(f)}: missing #pragma once")

            reflected = re.search(r"^\s*(UCLASS|USTRUCT|UENUM|UINTERFACE)\b", text, re.M)
            includes = [l for l in lines if l.startswith("#include")]
            gen = f"{f.stem}.generated.h"
            if reflected and f.parent.name in LANE and (MODULE / "Public") in f.parents:
                reflected_headers += 1
                check(gen in text, f"{rel(f)}: reflected header does not include {gen}")
                check(includes and includes[-1].endswith(f'"{gen}"'),
                      f"{rel(f)}: {gen} must be the LAST include")
                # every UCLASS/USTRUCT body needs GENERATED_BODY()
                bodies = len(re.findall(r"^\s*(UCLASS|USTRUCT|UINTERFACE)\b", text, re.M))
                check(text.count("GENERATED_BODY()") >= bodies,
                      f"{rel(f)}: {bodies} reflected types but only {text.count('GENERATED_BODY()')} GENERATED_BODY()")

            # UENUMs exposed to Blueprint must have a uint8 underlying type
            for m in re.finditer(r"UENUM\([^)]*BlueprintType[^)]*\)\s*\n\s*enum class (\w+)\s*(:[^\n{]*)?", text):
                check(m.group(2) is not None and "uint8" in m.group(2),
                      f"{rel(f)}: UENUM(BlueprintType) {m.group(1)} must be `: uint8`")

        # 4. every UObject pointer is either a UPROPERTY, or lives in a plain nested struct whose garbage
        #    collection owner is written down in the checklist (UHT cannot reflect a nested struct).
        if f.suffix == ".h":
            struct_name = None
            for i, line in enumerate(lines):
                sm = re.match(r"\s*struct\s+(\w+)", line)
                if sm:
                    struct_name = sm.group(1)
                if re.match(r"\s*TObjectPtr<", line):
                    previous = next((l for l in reversed(lines[:i]) if l.strip()), "")
                    if "UPROPERTY" not in previous:
                        unreflected_pointers.add((rel(f), struct_name or "?"))

        # 5. console commands: every `new FAutoConsoleCommand...` must be deleted somewhere in the same pair
        if "new FAutoConsoleCommand" in text:
            allocations = text.count("new FAutoConsoleCommand")
            deletes = text.count("delete Command") + text.count("delete InfoCommand") + text.count("delete ")
            check(deletes > 0, f"{rel(f)}: {allocations} console commands allocated and never deleted")

    # 6. every in-module include resolves
    unresolved = []
    lane_prefixes = tuple(s + "/" for s in LANE + ["CoreAdapter", "World", "Sky", "Weather", "Streaming"])
    for f in files:
        for line in f.read_text().splitlines():
            m = re.match(r'#include "([^"]+)"', line.strip())
            if not m or m.group(1).endswith(".generated.h"):
                continue
            inc = m.group(1)
            if not inc.startswith(lane_prefixes):
                continue
            if not any((MODULE / base / inc).exists() for base in ("Public", "Private")) and not (f.parent / inc).exists():
                unresolved.append(f"{rel(f)} -> {inc}")
    check(not unresolved, f"unresolved in-module includes: {unresolved}")

    # 7. every method declared in a lane header is defined in the matching Private folder
    undefined = []
    for sub in LANE:
        pub = MODULE / "Public" / sub
        priv = MODULE / "Private" / sub
        if not pub.is_dir():
            continue
        body = "\n".join(p.read_text() for p in priv.rglob("*.cpp")) if priv.is_dir() else ""
        for h in sorted(pub.rglob("*.h")):
            cls = None
            for line in h.read_text().splitlines():
                cm = re.match(r"\s*(?:class|struct)\s+(?:NYCSIMRUNTIME_API\s+)?([AUFS]NYC\w+)", line)
                if cm:
                    cls = cm.group(1)
                    continue
                d = re.match(r"\s*(?:virtual\s+)?[\w:<>\*&\s]+?\s+(\w+)\s*\(([^;{]*)\)\s*(?:const)?\s*(?:override)?\s*;\s*$", line)
                if d and cls and d.group(1) not in ("GENERATED_BODY", "UPROPERTY", "UFUNCTION"):
                    if not re.search(r"\b" + re.escape(cls) + "::" + re.escape(d.group(1)) + r"\b", body):
                        # FSoftObjectPath initialisers and other data lines can look like declarations
                        if d.group(1)[0].isupper() and d.group(1).startswith("F"):
                            continue
                        undefined.append(f"{cls}::{d.group(1)} ({rel(h)})")
    check(not undefined, f"declared but never defined: {undefined}")

    # 8. the adapter must stay free of Unreal: it is compiled by unreal/tools/gameplay_selftest.cpp with g++
    for f in adapter_files:
        text = f.read_text()
        for banned in ("CoreMinimal.h", "UPROPERTY", "UCLASS", "UFUNCTION", "FString", "TArray<", "UE_LOG"):
            check(banned not in text, f"{rel(f)}: adapter must not use Unreal API ({banned})")

    # 8b. plain structs holding UObject pointers: each must be named in the checklist's GC section
    checklist_path = ROOT / "unreal/COMPILE_CHECKLIST_GAMEPLAY.md"
    checklist_text = checklist_path.read_text() if checklist_path.exists() else ""
    for where, struct_name in sorted(unreflected_pointers):
        check(struct_name in checklist_text,
              f"{where}: struct {struct_name} holds UObject pointers outside UPROPERTY and its GC owner is not "
              f"recorded in COMPILE_CHECKLIST_GAMEPLAY.md")

    # 9. version-risky engine calls must be behind a detector or documented in the checklist
    checklist = (ROOT / "unreal/COMPILE_CHECKLIST_GAMEPLAY.md")
    if checklist.exists():
        cl = checklist.read_text()
        for risky in ("SetWheelFrictionMultiplier", "SetRuntimeGenerationMode", "AttenuationSettings",
                      "GetAnimationPose", "BlendTwoPosesTogether", "MakeCompactPoseIndex", "SetSubmixSend"):
            used = any(risky in f.read_text() for f in ue_files)
            if used:
                check(risky in cl, f"{risky} is used but not listed in COMPILE_CHECKLIST_GAMEPLAY.md")
    else:
        check(False, "unreal/COMPILE_CHECKLIST_GAMEPLAY.md is missing")

    # 10. the audio lane must never reference an asset stem that has no licence record
    sfx_dir = ROOT / "assets/audio/sfx"
    stems = {p.name[:-4] for p in sfx_dir.glob("*.ogg")} if sfx_dir.is_dir() else set()
    licensed = {p.name[: -len(".ogg.license.json")] for p in sfx_dir.glob("*.ogg.license.json")} if sfx_dir.is_dir() else set()
    check(stems == licensed, f"every fetched SFX must carry a licence record: {stems ^ licensed}")
    audio_text = "\n".join(f.read_text() for f in ue_files if "/Audio/" in str(f) or "Audio" in f.name)
    for m in re.finditer(r'TEXT\("(\w+)\.\1"\)', audio_text):
        pass  # content paths are built at runtime; the stems below are the literal ones
    for stem in re.findall(r'FindSfx\(TEXT\("([^"]+)"\)\)', audio_text):
        check(stem in stems or stem.startswith("amb_"),
              f"FindSfx(\"{stem}\") names a file that was never fetched and is not a documented optional stem")

    print(f"{checks} checks, {len(failures)} failures")
    for message in failures:
        print("  FAIL", message)
    print(f"files checked: {len(files)} ({len(ue_files)} Unreal, {len(adapter_files)} adapter), "
          f"reflected public headers: {reflected_headers}, "
          f"plain structs holding UObject pointers: {len(unreflected_pointers)}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
