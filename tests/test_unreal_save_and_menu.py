"""Saving, loading, and the input that reaches either.

Three things this guards, all of which were absent rather than broken:

* ``ANYCSimGameMode`` used the base ``APlayerController``, so nothing owned the common input context.
  ``NYCInputConfig``'s own header has documented a "Menu Escape" row since Stage 12b and the action
  did not exist; ``ToggleMap`` (M) and ``SearchDestination`` (Tab) existed with no handler anywhere.
  All three keys did nothing.
* A save that stores engine centimetres is tied to wherever the world origin was when it was written.
  The project has a coordinate contract for exactly this reason, and the save has to use it.
* Restoring a position teleports the pawn into tiles that have not streamed, and the car falls
  through the world. The load path has to move the streaming camera and flush **before** it places
  anything.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
RUNTIME = REPO_ROOT / "unreal" / "NYCSim" / "Source" / "NYCSimRuntime"
INPUT_H = RUNTIME / "Public" / "Player" / "NYCInputConfig.h"
INPUT_CPP = RUNTIME / "Private" / "Player" / "NYCInputConfig.cpp"
CONTROLLER_CPP = RUNTIME / "Private" / "Player" / "NYCPlayerController.cpp"
GAME_MODE_CPP = RUNTIME / "Private" / "World" / "NYCSimGameMode.cpp"
SAVE_H = RUNTIME / "Public" / "Save" / "NYCSaveGame.h"
SAVE_SUB_CPP = RUNTIME / "Private" / "Save" / "NYCSaveSubsystem.cpp"
MENU_CPP = RUNTIME / "Private" / "UI" / "NYCMenuWidget.cpp"


def _read(path: Path) -> str:
    if not path.is_file():
        pytest.skip(f"{path.relative_to(REPO_ROOT)} is not present")
    return path.read_text(encoding="utf-8", errors="replace")


def _strip_comments(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    return re.sub(r"//[^\n]*", "", text)


# --------------------------------------------------------------------------- input


def test_every_common_input_action_is_created_bound_and_handled():
    """An action that exists, is bound to a key and has no handler is a key that does nothing.

    That was true of ToggleMap and SearchDestination for four stages, and there was no Menu action at
    all despite the binding table in the header naming one.
    """
    header, config, controller = _read(INPUT_H), _read(INPUT_CPP), _read(CONTROLLER_CPP)
    block = re.search(r"\n\t*//\s*Common\n(.*?)Count\s+UMETA", header, re.S)
    assert block is not None, "the common section of ENYCInputAction is gone"
    common = re.findall(r"^\s*(\w+),", block.group(1), re.M)
    assert {"Menu", "ToggleMap", "QuickSave", "QuickLoad"} <= set(common), (
        f"the common actions are {common}; the menu and the quick slots need to be among them")

    created = set(re.findall(r"MakeAction\(ENYCInputAction::(\w+)", config))
    bound = set(re.findall(r"CommonContext, GetAction\(ENYCInputAction::(\w+)\)", config))
    handled = set(re.findall(r"Bind\(ENYCInputAction::(\w+)", controller))
    for action in common:
        assert action in created, f"{action} is declared and never created as a UInputAction"
        assert action in bound, f"{action} is created and bound to no key"
    for action in ("Menu", "ToggleMap", "QuickSave", "QuickLoad"):
        assert action in handled, (
            f"{action} is bound to a key and nothing handles it, so pressing that key does nothing")


def test_the_game_mode_uses_the_project_player_controller():
    """The common context is added by the controller, so the base class means no menu and no map."""
    text = _strip_comments(_read(GAME_MODE_CPP))
    assigned = re.search(r"PlayerControllerClass\s*=\s*(\w+)::StaticClass\(\)", text)
    assert assigned is not None, "the game mode assigns no PlayerControllerClass"
    assert assigned.group(1) == "ANYCPlayerController", (
        f"the game mode uses {assigned.group(1)}; the common input context, the menu, the map and "
        f"the quick slots all live on ANYCPlayerController")


def test_the_menu_owns_its_pause_and_gives_it_back():
    """Photo mode pauses too. Whoever paused has to be the one to unpause."""
    text = _read(CONTROLLER_CPP)
    assert "bPausedByMenu" in text, "the controller does not track whether it was the one that paused"
    assert "IsGamePaused" in text, (
        "the controller pauses without checking whether something else already had; closing the menu "
        "would then unpause photo mode")


# --------------------------------------------------------------------------- the save


def test_the_save_stores_the_city_frame_and_not_engine_units():
    """A save in centimetres is a save tied to the world origin it was written under.

    ARCHITECTURE 2 fixes UE.X = east*100 and UE.Y = -north*100 in a 50 km large-world map. NYC_TM is
    the city's own frame and does not move, so a save written in it survives an origin change, opens
    in the next build, and can be read against a map by a person.
    """
    header = _read(SAVE_H)
    positions = re.findall(r"FVector\s+(\w+)\s*=\s*FVector::ZeroVector", header)
    assert positions, "the save carries no positions at all"
    for name in positions:
        assert name.endswith("NycTm"), (
            f"{name} is a position that does not say which frame it is in; every position in the "
            f"save is NYC_TM metres and is named so")


def test_loading_flushes_the_streamer_before_it_moves_the_pawn():
    """The one ordering that matters in the whole save system.

    Place the pawn first and it lands in a level that has not been loaded: the ground it should stand
    on does not exist yet and the car falls until the engine deletes it.
    """
    text = _strip_comments(_read(SAVE_SUB_CPP))
    apply_body = text[text.index("bool UNYCSaveSubsystem::Apply("):]
    apply_body = apply_body[:apply_body.index("\nENYCSaveResult UNYCSaveSubsystem::SaveToSlot")]
    flush = apply_body.find("FlushStreaming")
    place = apply_body.find("SetActorLocationAndRotation")
    assert flush != -1, "Apply never flushes the tile streamer"
    assert place != -1, "Apply never places the pawn"
    assert flush < place, (
        "Apply moves the pawn before the streamer has finished; the car will fall through unloaded "
        "ground")
    assert apply_body.find("SetCameraOverride") < flush, (
        "Apply flushes before telling the streamer where to load; it would load the old position")


def test_a_save_from_a_newer_build_is_refused_rather_than_guessed_at():
    text = _read(SAVE_SUB_CPP)
    assert "VersionTooNew" in text, (
        "a save whose version is ahead of this build is read anyway; a field whose meaning changed "
        "would be interpreted as the old one")


def test_physics_is_off_while_the_pawn_is_moved():
    """A teleport into a wall with physics live is a collision, not a placement."""
    text = _strip_comments(_read(SAVE_SUB_CPP))
    assert "SetSimulatePhysics(false)" in text and "SetSimulatePhysics(true)" in text, (
        "Apply moves the pawn with physics running")


# --------------------------------------------------------------------------- the menu


def test_the_menu_is_built_from_the_design_system_only():
    """Same rule as the HUD: no colour literal and no font size outside NYCUiStyle."""
    text = _strip_comments(_read(MENU_CPP))
    colours = re.findall(r"FLinearColor\s*\([^)]*\d[^)]*\)", text)
    # A colour rebuilt from an existing role's channels is not a new colour.
    colours = [c for c in colours if "Base.R" not in c]
    assert not colours, f"colour literals in the menu: {colours}"
    assert not re.findall(r"FSlateFontInfo\s*\([^)]*,\s*\d+", text), "font sizes in the menu"
    assert "FNYCUiStyle::Font(" in text and "FNYCUiStyle::Space(" in text


def test_every_menu_page_is_reachable_and_built():
    """A page in the nav with no builder is a dead row."""
    header = _read(REPO_ROOT / "unreal" / "NYCSim" / "Source" / "NYCSimRuntime" / "Public" / "UI"
                   / "NYCMenuWidget.h")
    block = re.search(r"enum class ENYCMenuPage\s*:\s*\w+\s*\{(.*?)\}", header, re.S)
    assert block is not None
    pages = [p for p in re.findall(r"^\s*(\w+)", block.group(1), re.M) if p]
    pages = [p.split(" ")[0].rstrip(",") for p in pages]
    text = _read(MENU_CPP)
    nav = re.search(r"NavPages\(\)(.*?)return Pages;", text, re.S)
    assert nav is not None, "NavPages is gone"
    for page in pages:
        assert f"ENYCMenuPage::{page}" in nav.group(1), f"{page} is not in the nav"
        assert f"ENYCMenuPage::{page}" in text[text.index("void UNYCMenuWidget::RebuildDetail"):], (
            f"{page} is in the nav and RebuildDetail does not handle it")
