"""The interface has to reach the screen, and it has to come from one design system.

Two failures this module exists to prevent, both of which had already happened:

* ``UNYCGpsWidget`` and ``SNYCMinimap`` were finished C++ and Slate from Stage 12b onwards and were
  never displayed.  ``AddToViewport`` and ``CreateWidget`` appeared **nowhere** in ``unreal/``, there
  was no ``AHUD`` subclass, and ``ANYCSimGameMode`` never assigned ``HUDClass`` -- while its own
  header said the HUD class was resolved from the world settings.  Nothing was broken; nothing had
  been asked for.  A widget nobody adds to a viewport is indistinguishable from a widget that does
  not exist, and no compiler will say so.

* A design system is only a design system while nothing goes around it.  The moment one widget picks
  its own grey, the interface stops looking like one object.  So the UI sources may not contain
  colour literals or font sizes of their own.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
RUNTIME = REPO_ROOT / "unreal" / "NYCSim" / "Source" / "NYCSimRuntime"
UI_PUBLIC = RUNTIME / "Public" / "UI"
UI_PRIVATE = RUNTIME / "Private" / "UI"
GAME_MODE_CPP = RUNTIME / "Private" / "World" / "NYCSimGameMode.cpp"

#: Written after the design system existed, so held to it. UNYCGpsWidget and SNYCMinimap predate it
#: and are not rewritten here; that they still carry their own sizes is recorded, not asserted.
STYLED_SOURCES = ("NYCUiStyle.cpp", "NYCDrivingHudWidget.cpp", "SNYCSpeedometer.cpp", "NYCSimHUD.cpp")


def _sources() -> dict[str, str]:
    out: dict[str, str] = {}
    for d in (UI_PUBLIC, UI_PRIVATE):
        if not d.is_dir():
            continue
        for p in sorted(d.iterdir()):
            if p.suffix in (".h", ".cpp"):
                out[p.name] = p.read_text(encoding="utf-8", errors="replace")
    return out


def _all_runtime_sources() -> dict[Path, str]:
    if not RUNTIME.is_dir():
        pytest.skip("the Unreal runtime module is not present")
    return {p: p.read_text(encoding="utf-8", errors="replace")
            for p in RUNTIME.rglob("*") if p.suffix in (".h", ".cpp")}


def _strip_comments(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    return re.sub(r"//[^\n]*", "", text)


# --------------------------------------------------------------------------- reaching the screen


def test_some_hud_class_exists_and_the_game_mode_uses_it():
    """``AGameModeBase::HUDClass`` must name a concrete ``AHUD`` in this module.

    Without it the engine spawns the base ``AHUD``, which draws nothing, and every widget in
    ``Source/NYCSimRuntime/*/UI`` is dead code that compiles.
    """
    sources = _all_runtime_sources()
    huds = set()
    for text in sources.values():
        huds |= set(re.findall(r"class\s+NYCSIMRUNTIME_API\s+(\w+)\s*:\s*public\s+AHUD\b", text))
    assert huds, "no AHUD subclass anywhere in NYCSimRuntime; nothing can put a widget on screen"

    assert GAME_MODE_CPP.is_file(), f"{GAME_MODE_CPP} is missing"
    game_mode = _strip_comments(GAME_MODE_CPP.read_text(encoding="utf-8", errors="replace"))
    assigned = re.search(r"HUDClass\s*=\s*(\w+)::StaticClass\(\)", game_mode)
    assert assigned is not None, (
        f"{GAME_MODE_CPP.name} never assigns HUDClass, so the engine uses the base AHUD and no "
        f"widget is ever shown. Candidates in this module: {sorted(huds)}")
    assert assigned.group(1) in huds, (
        f"HUDClass is set to {assigned.group(1)}, which is not one of this module's AHUD "
        f"subclasses {sorted(huds)}")


def test_the_hud_actually_adds_a_widget_to_the_viewport():
    """Creating a widget is not showing it: something has to call ``AddToViewport``."""
    sources = _all_runtime_sources()
    creators = {p.name for p, text in sources.items() if "CreateWidget<" in _strip_comments(text)}
    adders = {p.name for p, text in sources.items() if "AddToViewport(" in _strip_comments(text)}
    assert creators, "CreateWidget is never called in NYCSimRuntime"
    assert adders, (
        "no source in NYCSimRuntime calls AddToViewport, so every widget the module creates is "
        "constructed and then dropped")
    assert creators & adders, (
        f"widgets are created in {sorted(creators)} and added to the viewport in {sorted(adders)}, "
        f"but no single file does both; check the created widget is the one being shown")


def test_every_user_widget_in_the_ui_folder_is_constructed_somewhere():
    """A ``UUserWidget`` subclass nobody instantiates is a screen that will never appear."""
    sources = _all_runtime_sources()
    declared = set()
    for text in sources.values():
        declared |= set(re.findall(
            r"class\s+NYCSIMRUNTIME_API\s+(U\w+)\s*:\s*public\s+U(?:UserWidget|Widget)\b", text))
    assert declared, "no widget classes found; has the UI module moved?"
    blob = "\n".join(_strip_comments(t) for t in sources.values())
    orphaned = sorted(name for name in declared
                      if f"CreateWidget<{name}>" not in blob
                      and f"ConstructWidget<{name}>" not in blob)
    assert not orphaned, (
        f"{len(orphaned)} widget class(es) are declared and never constructed: {orphaned}. "
        f"They will not appear on any screen no matter how complete they are.")


# --------------------------------------------------------------------------- one design system


def test_the_styled_ui_sources_declare_no_colours_of_their_own():
    """Colour comes from ``FNYCUiStyle::Colour``, in six roles, and from nowhere else."""
    sources = _sources()
    offenders: dict[str, list[str]] = {}
    for name in STYLED_SOURCES:
        text = sources.get(name)
        if text is None or name == "NYCUiStyle.cpp":     # the palette itself lives there
            continue
        found = re.findall(r"FLinearColor\s*\([^)]*\d[^)]*\)", _strip_comments(text))
        if found:
            offenders[name] = found
    assert not offenders, (
        "colour literals outside the palette: "
        + "; ".join(f"{k}: {v}" for k, v in offenders.items())
        + ". Add a role to ENYCColourRole instead.")


def test_the_styled_ui_sources_declare_no_font_sizes_of_their_own():
    """Four type sizes, chosen by role. A fifth size picked inline is how a UI stops being one."""
    sources = _sources()
    offenders: dict[str, list[str]] = {}
    for name in STYLED_SOURCES:
        text = sources.get(name)
        if text is None or name == "NYCUiStyle.cpp":
            continue
        found = re.findall(r"FSlateFontInfo\s*\([^)]*,\s*\d+", _strip_comments(text))
        found += re.findall(r"GetDefaultFontStyle\([^)]*,\s*\d+", _strip_comments(text))
        if found:
            offenders[name] = found
    assert not offenders, (
        "font sizes outside the type scale: "
        + "; ".join(f"{k}: {v}" for k, v in offenders.items())
        + ". Use FNYCUiStyle::Font(ENYCTextRole::...).")


def test_the_type_scale_and_the_palette_stay_small():
    """The restriction is the design. Four sizes, six colours; growth needs a deliberate edit here."""
    header = (UI_PUBLIC / "NYCUiStyle.h").read_text(encoding="utf-8", errors="replace")
    roles = re.search(r"enum class ENYCTextRole\s*:\s*\w+\s*\{(.*?)\}", header, re.S)
    colours = re.search(r"enum class ENYCColourRole\s*:\s*\w+\s*\{(.*?)\}", header, re.S)
    assert roles and colours, "the style header no longer declares its two role enums"
    n_type = len(re.findall(r"^\s*(\w+),", roles.group(1), re.M))
    n_colour = len(re.findall(r"^\s*(\w+),", colours.group(1), re.M))
    assert n_type == 4, f"the type scale has grown to {n_type} sizes; it is meant to be four"
    assert n_colour == 6, f"the palette has grown to {n_colour} roles; it is meant to be six"


def test_the_spacing_grid_has_exactly_one_base_unit():
    """Every margin in the UI is a whole multiple of one number, so nothing is ever nearly aligned."""
    header = (UI_PUBLIC / "NYCUiStyle.h").read_text(encoding="utf-8", errors="replace")
    unit = re.search(r"constexpr float Unit\s*=\s*([\d.]+)f?\s*;", header)
    assert unit is not None, "FNYCUiStyle::Unit is gone"
    assert float(unit.group(1)) == 4.0, f"the spacing unit is {unit.group(1)}, expected 4"
    sources = _sources()
    for name in ("NYCDrivingHudWidget.cpp", "SNYCSpeedometer.cpp"):
        text = sources.get(name)
        if text is None:
            continue
        # Positions and sizes go through Space(); a bare pixel margin is the thing being prevented.
        assert "FNYCUiStyle::Space(" in text, f"{name} lays out without the spacing grid"
