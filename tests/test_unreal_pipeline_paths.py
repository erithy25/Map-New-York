"""Where the pipeline writes an asset and where the engine looks for it must be the same place.

Every one of these was broken and none of them could fail visibly. An asset imported to a content
path nothing reads is present in the content browser, correctly built, and absent from the game; a
lamp whose material slot the runtime cannot find is dark; a file with no manifest rule is never
listed and so never imported at all. Between them they accounted for the player's car, the player's
body, the whole traffic fleet, the whole crowd, all 74 audio files, the HUD font and every landmark.

The checks read the engine sources as text on purpose: there is no compiler here, and the point is to
compare two documents that no compiler compares anyway.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "pipeline"))

RUNTIME = REPO_ROOT / "unreal" / "NYCSim" / "Source" / "NYCSimRuntime"
GAMEPLAY_SETTINGS = RUNTIME / "Public" / "Player" / "NYCGameplaySettings.h"
RADIO_CPP = RUNTIME / "Private" / "Audio" / "NYCRadioSubsystem.cpp"
DEFAULT_GAME_INI = REPO_ROOT / "unreal" / "NYCSim" / "Config" / "DefaultGame.ini"
IMPORT_ASSETS = REPO_ROOT / "unreal" / "NYCSim" / "Content" / "Python" / "import_assets.py"


def _rules():
    """The manifest's own resolver, not a copy of it.

    A test that reimplements the rule it is checking passes against its own copy of the bug, which is
    exactly how three copies of the vehicle contract came to agree with each other and with nothing
    else.
    """
    from nycsim_pipeline.unreal.manifest import resolve_glb

    def resolve(rel: str) -> tuple[str, str, str]:
        got = resolve_glb(rel)
        assert got is not None, f"no import rule matches {rel}"
        return got

    return resolve


def _settings_paths() -> dict[str, str]:
    """Every ``/Game/NYCSim/...`` string the gameplay settings hardcode, by the field that holds it."""
    if not GAMEPLAY_SETTINGS.is_file():
        pytest.skip("NYCGameplaySettings.h is not present")
    text = GAMEPLAY_SETTINGS.read_text(encoding="utf-8", errors="replace")
    out: dict[str, str] = {}
    for field, value in re.findall(r"(\w+)\s*=\s*(?:FSoftObjectPath\()?\s*TEXT\(\"(/Game/NYCSim/[^\"]+)\"\)", text):
        out[field] = value
    return out


def test_the_player_vehicle_imports_where_the_settings_look_for_it():
    """``PlayerVehicleMesh`` names one exact asset path; the manifest has to produce that path."""
    resolve = _rules()
    dst, settings, kind = resolve("vehicles/fusion_hybrid.glb")
    want = _settings_paths().get("PlayerVehicleMesh", "")
    assert want, "NYCGameplaySettings declares no PlayerVehicleMesh"
    want_asset = want.split(".")[0]
    assert dst == want_asset, (
        f"fusion_hybrid.glb imports to {dst} but UNYCGameplaySettings::PlayerVehicleMesh is "
        f"{want_asset}. The car would be in the content browser and not in the game.")
    assert kind == "vehicle" and settings == "vehicle_skeletal"


def test_the_player_character_imports_where_the_settings_look_for_it():
    resolve = _rules()
    dst, _settings, _kind = resolve("character/player.glb")
    want = _settings_paths().get("PlayerCharacterMesh", "")
    assert want, "NYCGameplaySettings declares no PlayerCharacterMesh"
    assert dst == want.split(".")[0], (
        f"player.glb imports to {dst} but the settings say {want.split('.')[0]} -- note Characters, "
        f"plural, which the manifest used to spell Character")


def test_the_fleet_and_the_crowd_import_under_the_roots_the_settings_scan():
    """``TrafficVehicleMeshRoot`` and ``PedestrianMeshRoot`` are directories the subsystems scan."""
    resolve = _rules()
    paths = _settings_paths()
    fleet_root = paths.get("TrafficVehicleMeshRoot", "")
    crowd_root = paths.get("PedestrianMeshRoot", "")
    assert fleet_root and crowd_root, "the settings declare no fleet or crowd root"
    fleet, _s, _k = resolve("vehicles/taxi_nv200.glb")
    crowd, _s2, _k2 = resolve("character/npc/npc_00_f_child_scrubs.glb")
    assert fleet.startswith(fleet_root + "/"), f"a fleet vehicle imports to {fleet}, outside {fleet_root}"
    assert crowd.startswith(crowd_root + "/"), f"an NPC imports to {crowd}, outside {crowd_root}"


def test_the_hud_font_imports_under_the_name_the_settings_name():
    """``safe_asset_name`` maps '-' to 'm', so overpass-bold became F_overpassmbold.

    The settings ask for ``/Game/NYCSim/Fonts/F_Overpass``. With three separately named font assets
    and none of them called that, every piece of HUD text falls back to the engine default and
    nothing reports it.
    """
    from nycsim_pipeline.unreal.manifest import ManifestBuilder

    want = _settings_paths().get("HudFont", "")
    assert want, "the settings declare no HudFont"
    builder = ManifestBuilder(REPO_ROOT / "data" / "processed", REPO_ROOT / "blender_out", REPO_ROOT,
                              hash_files=False)
    builder.add_runtime()
    fonts = [e for e in builder.entries if e["kind"] == "font"]
    if not fonts:
        pytest.skip("no font assets in this checkout")
    assert len(fonts) == 1, f"expected one UFont, got {[e['dst'] for e in fonts]}"
    assert fonts[0]["dst"] == want.split(".")[0], (
        f"the font imports as {fonts[0]['dst']} but the settings ask for {want.split('.')[0]}")
    assert len(fonts[0].get("typefaces", [])) >= 2, "the weights were dropped instead of becoming typefaces"


def test_every_audio_file_has_a_rule_and_lands_where_the_radio_looks():
    """74 licensed .ogg files had no rule at all, so the car had no radio and no sound effects.

    ``UNYCRadioSubsystem`` builds a track's content path as ``<RadioContentRoot>/<genre>/<stem>``;
    the manifest has to produce exactly that, or every track resolves to nothing.
    """
    from nycsim_pipeline.unreal.manifest import ManifestBuilder

    audio_dir = REPO_ROOT / "assets" / "audio"
    if not audio_dir.is_dir():
        pytest.skip("no audio in this checkout")
    on_disk = sorted(audio_dir.rglob("*.ogg"))
    builder = ManifestBuilder(REPO_ROOT / "data" / "processed", REPO_ROOT / "blender_out", REPO_ROOT,
                              hash_files=False)
    builder.add_audio()
    sounds = [e for e in builder.entries if e["kind"] == "sound"]
    assert len(sounds) == len(on_disk), (
        f"{len(on_disk)} .ogg files on disk, {len(sounds)} in the manifest; the difference is "
        f"audio that is never imported and never cooked")

    paths = _settings_paths()
    radio_root = paths.get("RadioContentRoot", "")
    sfx_root = paths.get("SfxContentRoot", "")
    assert radio_root and sfx_root, "the settings declare no audio roots"
    for e in sounds:
        assert e["dst"].startswith((radio_root + "/", sfx_root + "/")), (
            f"{e['src']} imports to {e['dst']}, under neither {radio_root} nor {sfx_root}")


def test_every_track_in_the_station_index_names_an_asset_the_manifest_imports():
    """The index carries the content path the manifest assigned, so nothing has to derive it twice.

    Both sides used to derive ``<root>/<genre>/<stem>`` independently, and they disagreed: the
    manifest's ``safe_asset_name`` puts an underscore in front of a leading digit because a UE asset
    name may not begin with one, so ``01_gunther_freischutz.ogg`` imports as
    ``_01_gunther_freischutz`` while the engine looked for ``01_gunther_freischutz`` and found
    silence. Now ``add_audio`` writes ``sound_path`` into the index it copies, and the subsystem
    prefers it.
    """
    import json

    from nycsim_pipeline.unreal.manifest import ManifestBuilder

    if not (REPO_ROOT / "assets" / "audio" / "radio" / "stations.json").is_file():
        pytest.skip("no stations.json in this checkout")
    builder = ManifestBuilder(REPO_ROOT / "data" / "processed", REPO_ROOT / "blender_out", REPO_ROOT,
                              hash_files=False)
    builder.add_audio()
    index = next(e for e in builder.entries if e["kind"] == "audio_index")
    doc = json.loads((REPO_ROOT / index["src"]).read_text())
    assets = {e["dst"] for e in builder.entries if e["kind"] == "sound"}
    tracks = [t for st in doc.get("stations", []) for t in st.get("tracks", [])]
    assert tracks, "the index lists no tracks"
    for track in tracks:
        path = track.get("sound_path", "")
        assert path, f"track {track.get('file')} has no sound_path; the engine would have to guess"
        assert path.rsplit(".", 1)[0] in assets, (
            f"track {track.get('file')} names {path}, which the manifest does not import")
    assert doc.get("resolved_tracks") == len(tracks)


def test_the_radio_subsystem_prefers_the_resolved_path():
    """The C++ half of the same agreement."""
    if not RADIO_CPP.is_file():
        pytest.skip("NYCRadioSubsystem.cpp is not present")
    src = RADIO_CPP.read_text(encoding="utf-8", errors="replace")
    assert "sound_path" in src, (
        "the radio subsystem does not read sound_path, so it is back to deriving a content path the "
        "manifest may not have written")


def test_the_station_index_is_copied_to_the_file_path_the_settings_read():
    """``RadioStationsJson`` is a file path under the project directory, not a content path."""
    from nycsim_pipeline.unreal.manifest import ManifestBuilder

    if not (REPO_ROOT / "assets" / "audio" / "radio" / "stations.json").is_file():
        pytest.skip("no stations.json in this checkout")
    text = GAMEPLAY_SETTINGS.read_text(encoding="utf-8", errors="replace")
    want = re.search(r'RadioStationsJson\s*=\s*TEXT\("([^"]+)"\)', text)
    assert want is not None, "the settings declare no RadioStationsJson"
    builder = ManifestBuilder(REPO_ROOT / "data" / "processed", REPO_ROOT / "blender_out", REPO_ROOT,
                              hash_files=False)
    builder.add_audio()
    index = [e for e in builder.entries if e["kind"] == "audio_index"]
    assert len(index) == 1, "the station index is not in the manifest"
    assert index[0]["dst"] == want.group(1), (
        f"stations.json is copied to {index[0]['dst']}, the engine reads {want.group(1)}")


def test_everything_reached_by_path_at_runtime_is_cooked():
    """``bCookMapsOnly=True`` means the cooker follows map references and takes nothing else.

    The vehicles, the characters, the audio, the physical materials and the landmarks are all reached
    by a *path string* at runtime, so none of them is referenced by a map and a packaged build would
    ship without any of them.
    """
    if not DEFAULT_GAME_INI.is_file():
        pytest.skip("DefaultGame.ini is not present")
    text = DEFAULT_GAME_INI.read_text(encoding="utf-8", errors="replace")
    if "bCookMapsOnly=True" not in text:
        pytest.skip("the cooker is not in maps-only mode")
    cooked = set(re.findall(r'\+DirectoriesToAlwaysCook=\(Path="([^"]+)"\)', text))
    for needed in ("/Game/NYCSim/Vehicles", "/Game/NYCSim/Characters", "/Game/NYCSim/Audio",
                   "/Game/NYCSim/Physics", "/Game/NYCSim/Landmarks"):
        assert needed in cooked, (
            f"{needed} is reached only by a runtime path string and is not in "
            f"DirectoriesToAlwaysCook; a packaged build loses it. Cooked: {sorted(cooked)}")


def test_the_import_settings_the_manifest_names_are_all_built():
    """A master material named in the manifest and built by nobody makes every parameter write a no-op.

    ``M_NYC_Vehicle`` and ``M_NYC_Character`` were named as the vehicle and character masters from
    Stage 12b and ``ensure_materials`` built neither, so every ``SetScalarParameterValue`` the
    vehicle components make -- ``EmissiveScale``, ``GaugeValue``, ``PaintColor``, ``WindowDown`` --
    was called on a material with no such parameter. In Unreal that is silent.
    """
    from nycsim_pipeline.unreal.manifest import IMPORT_SETTINGS

    if not IMPORT_ASSETS.is_file():
        pytest.skip("import_assets.py is not present")
    src = IMPORT_ASSETS.read_text(encoding="utf-8", errors="replace")
    named = {s["material_master"] for s in IMPORT_SETTINGS.values() if s.get("material_master")}
    built = set(re.findall(r'create_material\("(\w+)"', src))
    missing = sorted(named - built)
    assert not missing, f"master material(s) named by the manifest and never built: {missing}"

    ensured = re.search(r"def ensure_materials\([^)]*\)[^{]*?\n(?:.*?\n)*?    return result", src)
    assert ensured is not None, "ensure_materials no longer returns a result dict"
    for name in sorted(named):
        assert name in ensured.group(0), f"{name} is built but ensure_materials does not call it"


def test_the_vehicle_material_declares_every_parameter_the_runtime_writes():
    """``NYCVehicleParams`` is the list of names the components set; the master has to have them."""
    contract = RUNTIME / "Public" / "Vehicle" / "NYCVehicleContract.h"
    if not contract.is_file() or not IMPORT_ASSETS.is_file():
        pytest.skip("sources not present")
    text = contract.read_text(encoding="utf-8", errors="replace")
    block = re.search(r"namespace NYCVehicleParams\s*\{(.*?)\n\}", text, re.S)
    assert block is not None, "NYCVehicleParams is gone"
    params = set(re.findall(r'TEXT\("(\w+)"\)', block.group(1)))
    src = IMPORT_ASSETS.read_text(encoding="utf-8", errors="replace")
    builder = src[src.index("def build_vehicle_material("):]
    builder = builder[:builder.index("\ndef ", 1)]
    declared = set(re.findall(r'parameter_name="(\w+)"', builder))
    missing = sorted(params - declared)
    assert not missing, (
        f"{len(missing)} parameter(s) the vehicle components write are not on M_NYC_Vehicle: "
        f"{missing}. Writing to a parameter a material does not have is silent in Unreal.")


def test_the_runtime_containers_are_all_listed():
    """Seven .nycb files carry the world the simulation runs on; all seven were dropped.

    ``_nycb_header`` unpacked the 24-byte header as 20 bytes with no padding, so it read
    ``index_offset`` out of the padding, seeked to nonsense and declared every container invalid.
    The road graph the traffic drives on, the signals, the POIs the GPS searches, the tile index, the
    transit and the density -- 130 MB of the world -- were reported "not a valid NYCB container" and
    left out of the manifest. The writer (``pipeline/nycsim_pipeline/runtime/nycb.py``) asserts the
    header is 24 bytes; this reads a real container back through the manifest's reader.
    """
    from nycsim_pipeline.unreal.manifest import _NYCB_HEADER, _nycb_header

    assert _NYCB_HEADER.size == 24, (
        f"the manifest reads a {_NYCB_HEADER.size}-byte NYCB header; DATA_CONTRACTS 15 and "
        f"runtime/nycb.py both say 24 (4 bytes of padding before the 8-aligned index_offset)")
    runtime = REPO_ROOT / "data" / "processed" / "runtime"
    containers = sorted(runtime.glob("*.nycb")) if runtime.is_dir() else []
    if not containers:
        pytest.skip("no runtime containers in this checkout")
    for p in containers:
        header = _nycb_header(p)
        assert header is not None, f"{p.name} does not parse; it is 130 MB of world that never ships"
        assert header["sections"], f"{p.name} parses but has no sections"


def test_the_skyline_cells_import_where_the_level_builder_loads_them():
    """838 MB of merged skyline had no import rule and was skipped with a warning.

    ``build_skyline_level`` loads ``SM_S4_<x>_<y>`` for a 4 km cell and ``SM_S16_<x>_<y>`` for 16 km,
    writing a negative index as ``m<n>``. That last detail is why the index may not go through
    ``safe_asset_name``: it would leave ``m1`` alone but turn a positive ``0`` into ``_0``.
    """
    from nycsim_pipeline.unreal.manifest import cell_part

    resolve = _rules()
    merged = REPO_ROOT / "blender_out" / "tiles" / "_merged"
    if not merged.is_dir():
        pytest.skip("no merged skyline in this checkout")

    build_levels = REPO_ROOT / "unreal" / "NYCSim" / "Content" / "Python" / "build_levels.py"
    src = build_levels.read_text(encoding="utf-8", errors="replace")
    assert "SM_S4_" in src and "SM_S16_" in src, "build_levels.py no longer loads skyline cells"

    for level, prefix in ((2, "SM_S4_"), (3, "SM_S16_")):
        for glb in sorted((merged / f"l{level}").glob("*.glb"))[:6]:
            rel = glb.relative_to(REPO_ROOT / "blender_out").as_posix()
            dst, settings, kind = resolve(rel)
            sx, sy = glb.stem.split("_")[1:3]
            want = f"/Game/NYCSim/Skyline/{prefix}{cell_part(sx)}_{cell_part(sy)}"
            assert dst == want, f"{rel} imports to {dst}, build_levels.py loads {want}"
            assert kind == "skyline" and settings == "skyline_nanite"

    assert cell_part(-1) == "m1" and cell_part(0) == "0" and cell_part(3) == "3"


def test_the_manifest_has_no_unroutable_asset_left():
    """Any blender_out glb with no rule is content that silently never reaches the engine."""
    from nycsim_pipeline.unreal.manifest import GLB_RULES

    blender_out = REPO_ROOT / "blender_out"
    if not blender_out.is_dir():
        pytest.skip("no blender_out in this checkout")
    unrouted = []
    for glb in blender_out.rglob("*.glb"):
        rel = glb.relative_to(blender_out).as_posix()
        if not any(rx.match(rel) for rx, _s, _t, _k in GLB_RULES):
            unrouted.append(rel)
    assert not unrouted, (
        f"{len(unrouted)} exported mesh(es) have no import rule and are skipped: {unrouted[:8]}")
