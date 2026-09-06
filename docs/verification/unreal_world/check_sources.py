#!/usr/bin/env python3
"""Static verification of the UE sources this stage owns, for the checks that do not need a compiler.

    python3 docs/verification/unreal_world/check_sources.py

Checked here:
  1. every reflected header includes its own .generated.h, and it is the last include
  2. no static (C) array is exposed to Blueprint (UHT rejects it)
  3. every UPROPERTY(Config) of UNYCSimWorldSettings has a line in Config/DefaultEngine.ini
  4. core headers (nycsim/**) are included only from Private/CoreAdapter, and every one of them exists
  5. braces, parentheses and #if/#endif balance in every file
  6. every out-of-line member definition in a .cpp is declared in the matching header
  7. no TODO / FIXME / stub / placeholder markers
  8. every console command and CVar registered in the sources is documented in unreal/README.md
"""
from __future__ import annotations

import os
import re
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
RUNTIME = os.path.join(REPO, "unreal/NYCSim/Source/NYCSimRuntime")
EDITOR = os.path.join(REPO, "unreal/NYCSim/Source/NYCSimEditor")

# Files this stage owns (Unreal agent 1). Agent 2's folders are excluded.
OWNED = [
    "Public/Streaming/NYCTileStreamingSubsystem.h", "Private/Streaming/NYCTileStreamingSubsystem.cpp",
    "Public/Sky/NYCSkyTimeSubsystem.h", "Private/Sky/NYCSkyTimeSubsystem.cpp",
    "Public/Weather/NYCWeatherSubsystem.h", "Private/Weather/NYCWeatherSubsystem.cpp",
    "Public/World/NYCTerrainImport.h", "Private/World/NYCTerrainImport.cpp",
    "Public/World/NYCWaterActor.h", "Private/World/NYCWaterActor.cpp",
    "Public/World/NYCInstancedMeshActor.h", "Private/World/NYCInstancedMeshActor.cpp",
    "Public/World/NYCWorldSubsystem.h", "Private/World/NYCWorldSubsystem.cpp",
    "Public/World/NYCSimWorldSettings.h", "Private/World/NYCSimWorldSettings.cpp",
    "Public/World/NYCSimGameMode.h", "Private/World/NYCSimGameMode.cpp",
    "Public/World/NYCSimGameInstance.h", "Private/World/NYCSimGameInstance.cpp",
    "Public/CoreAdapter/NYCAstro.h", "Private/CoreAdapter/NYCAstro.cpp",
    "Public/CoreAdapter/NYCWeather.h", "Private/CoreAdapter/NYCWeather.cpp",
    "Public/CoreAdapter/NYCGeo.h", "Private/CoreAdapter/NYCGeo.cpp",
    "Public/CoreAdapter/NYCNycb.h", "Private/CoreAdapter/NYCNycb.cpp",
    "Public/CoreAdapter/NYCTileScheduler.h", "Private/CoreAdapter/NYCTileScheduler.cpp",
    "Public/CoreAdapter/NYCCoreBridge.h", "Private/CoreAdapter/NYCCoreBridge.cpp",
    "Public/NYCSimRuntime.h", "Private/NYCSimRuntime.cpp",
]
OWNED_EDITOR = ["Public/NYCImportCommandlet.h", "Private/NYCImportCommandlet.cpp"]

FAILURES: list[str] = []
CHECKS = 0


def check(name: str, condition: bool, detail: str = "") -> None:
    global CHECKS
    CHECKS += 1
    if not condition:
        FAILURES.append(f"{name}{('  — ' + detail) if detail else ''}")
        print(f"[FAIL] {name}{('  — ' + detail) if detail else ''}")


def files() -> list[tuple[str, str]]:
    out = []
    for rel in OWNED:
        path = os.path.join(RUNTIME, rel)
        if os.path.isfile(path):
            out.append((rel, path))
        else:
            check(f"file exists: {rel}", False)
    for rel in OWNED_EDITOR:
        path = os.path.join(EDITOR, rel)
        if os.path.isfile(path):
            out.append((f"editor/{rel}", path))
        else:
            check(f"file exists: editor/{rel}", False)
    return out


ALL = files()
TEXT = {rel: open(path, encoding="utf-8").read() for rel, path in ALL}
print(f"{len(ALL)} owned source files, {sum(t.count(chr(10)) for t in TEXT.values())} lines")

# ---------------------------------------------------------------- 1. generated.h placement
for rel, text in TEXT.items():
    if not rel.endswith(".h"):
        continue
    reflected = re.search(r"^\s*(UCLASS|USTRUCT|UENUM)\s*\(", text, re.M) is not None
    includes = re.findall(r'^\s*#include\s+"([^"]+)"', text, re.M)
    generated = os.path.basename(rel).replace(".h", ".generated.h")
    if reflected:
        check(f"{rel}: includes {generated}", generated in includes)
        if generated in includes:
            check(f"{rel}: {generated} is the last include", includes[-1] == generated,
                  f"last is {includes[-1]}")
    else:
        check(f"{rel}: no stray generated include", generated not in includes)

# ---------------------------------------------------------------- 2. static arrays exposed to Blueprint
for rel, text in TEXT.items():
    bad = re.findall(r"UPROPERTY\([^)]*Blueprint[^)]*\)\s*\n\s*[^;\n]*\w+\s*\[\s*\d+\s*\]\s*(?:=|;)", text)
    check(f"{rel}: no static array with a Blueprint UPROPERTY", not bad, str(bad[:2]))

# ---------------------------------------------------------------- 3. Config properties vs DefaultEngine.ini
settings = TEXT.get("Public/World/NYCSimWorldSettings.h", "")
ini_path = os.path.join(REPO, "unreal/NYCSim/Config/DefaultEngine.ini")
ini = open(ini_path, encoding="utf-8").read()
section = ini.split("[/Script/NYCSimRuntime.NYCSimWorldSettings]", 1)[-1].split("\n[", 1)[0]
config_props = re.findall(r"UPROPERTY\(Config[^)]*\)\s*\n\s*[\w:<>,\s]*?(\w+)\s*(?:=|;)", settings)
missing = [p for p in config_props if not re.search(rf"^{re.escape(p)}\s*=", section, re.M)]
check("DefaultEngine.ini carries every UPROPERTY(Config) of NYCSimWorldSettings",
      not missing, f"missing: {missing}")
print(f"  {len(config_props)} config properties, {len(config_props) - len(missing)} present in DefaultEngine.ini")

# ---------------------------------------------------------------- 4. core includes only in CoreAdapter
core_include = re.compile(r'#include\s+"(nycsim/[^"]+)"')
core_root = os.path.join(REPO, "core/include")
for rel, text in TEXT.items():
    hits = core_include.findall(text)
    if hits:
        check(f"{rel}: core headers are included only under CoreAdapter", "CoreAdapter" in rel, str(hits[:3]))
    for header in hits:
        check(f"{rel}: core header {header} exists", os.path.isfile(os.path.join(core_root, header)))

# ---------------------------------------------------------------- 5. balance
def strip_comments_and_strings(text: str) -> str:
    """Left-to-right scanner: a regex cannot do this (a URL inside a string literal contains '//')."""
    out, i, n = [], 0, len(text)
    while i < n:
        c = text[i]
        if c == "/" and i + 1 < n and text[i + 1] == "/":
            while i < n and text[i] != "\n":
                i += 1
        elif c == "/" and i + 1 < n and text[i + 1] == "*":
            i += 2
            while i + 1 < n and not (text[i] == "*" and text[i + 1] == "/"):
                i += 1
            i += 2
        elif c in "\"'":
            quote = c
            i += 1
            while i < n and text[i] != quote:
                i += 2 if text[i] == "\\" else 1
            i += 1
        else:
            out.append(c)
            i += 1
    return "".join(out)


for rel, text in TEXT.items():
    stripped = strip_comments_and_strings(text)
    check(f"{rel}: braces balance", stripped.count("{") == stripped.count("}"),
          f"{stripped.count('{')} vs {stripped.count('}')}")
    check(f"{rel}: parentheses balance", stripped.count("(") == stripped.count(")"),
          f"{stripped.count('(')} vs {stripped.count(')')}")
    opens = len(re.findall(r"^\s*#\s*(if|ifdef|ifndef)\b", text, re.M))
    closes = len(re.findall(r"^\s*#\s*endif\b", text, re.M))
    check(f"{rel}: #if/#endif balance", opens == closes, f"{opens} vs {closes}")

# ---------------------------------------------------------------- 6. definitions have declarations
definition = re.compile(r"^[A-Za-z_][\w:<>,*&\s]*?\b(\w+)::(~?\w+)\s*\(", re.M)
for rel, text in TEXT.items():
    if not rel.endswith(".cpp"):
        continue
    header_rel = rel.replace("Private/", "Public/").replace(".cpp", ".h")
    header = TEXT.get(header_rel)
    if header is None:
        continue
    for cls, method in set(definition.findall(text)):
        if method.startswith("~") or method == cls:
            continue
        check(f"{rel}: {cls}::{method} is declared in {os.path.basename(header_rel)}",
              re.search(rf"\b{re.escape(method)}\s*\(", header) is not None)

# ---------------------------------------------------------------- 7. no placeholder markers
marker = re.compile(r"\b(TODO|FIXME|XXX|HACK|not implemented|placeholder|stub)\b", re.I)
for rel, text in TEXT.items():
    hits = [m.group(0) for m in marker.finditer(text)]
    check(f"{rel}: no placeholder markers", not hits, str(hits[:3]))
for name in ("import_world.py", "import_assets.py", "build_levels.py"):
    path = os.path.join(REPO, "unreal/NYCSim/Content/Python", name)
    text = open(path, encoding="utf-8").read()
    check(f"{name}: no placeholder markers", not marker.search(text))

# ---------------------------------------------------------------- 8. console surface is documented
readme = open(os.path.join(REPO, "unreal/README.md"), encoding="utf-8").read()
console = set()
for rel, text in TEXT.items():
    console.update(re.findall(r'TAutoConsoleVariable<[^>]+>\s*\w+\(\s*\n?\s*TEXT\("([^"]+)"\)', text))
    console.update(re.findall(r'FAutoConsoleCommandWithWorldArgsAndOutputDevice\s+\w+\(\s*\n?\s*TEXT\("([^"]+)"\)', text))
    console.update(re.findall(r'new FAutoConsoleCommandWithWorldArgsAndOutputDevice\(\s*\n?\s*TEXT\("([^"]+)"\)', text))
undocumented = sorted(c for c in console if c not in readme)
check("every console command/variable is documented in unreal/README.md", not undocumented,
      f"undocumented: {undocumented}")
print(f"  {len(console)} console commands / variables: {', '.join(sorted(console))}")

print()
if FAILURES:
    print(f"{len(FAILURES)} of {CHECKS} checks FAILED")
    sys.exit(1)
print(f"ALL {CHECKS} CHECKS PASSED")
