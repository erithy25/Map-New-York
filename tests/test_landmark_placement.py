"""93 landmark models were exported, imported, and never spawned.

``pipeline/nycsim_pipeline/unreal/manifest.py`` has looked for
``data/processed/landmarks/landmarks.json`` since Stage 12b.  Nothing wrote it, so
``build_levels.py`` had nothing to place landmarks from and never grew a ``place_landmarks`` at all
-- the Empire State Building, the Chrysler Building, Grand Central, the World Trade Center site and
the Statue of Liberty all import as ``SM_*`` assets into a world that spawns none of them.  927 MB
of content, invisible.

The second half of this module guards the trap in the fix.  Every catalogue entry carries
``heading_deg`` next to ``origin_tm``, and using both is the obvious reading.  It is wrong:
``blender/landmarks/common.py`` rotates each model back to NYC_TM axes before export and says so in
the file's own extras -- *"no rotation to apply on import"* -- so ``heading_deg`` is the compass
heading of the footprint's principal axis, kept as provenance.  Applying it would turn every
landmark in the city by its own facade angle.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "pipeline"))

BUILD_LEVELS = REPO_ROOT / "unreal" / "NYCSim" / "Content" / "Python" / "build_levels.py"
CATALOG_DIR = REPO_ROOT / "blender_out" / "landmarks" / "catalog"
INDEX = REPO_ROOT / "data" / "processed" / "landmarks" / "landmarks.json"


def _build_levels() -> str:
    if not BUILD_LEVELS.is_file():
        pytest.skip("build_levels.py is not present")
    return BUILD_LEVELS.read_text(encoding="utf-8", errors="replace")


def test_the_level_builder_places_landmarks_at_all():
    """The check that was missing: something in the level builder has to spawn them."""
    text = _build_levels()
    assert "def place_landmarks(" in text, (
        "build_levels.py has no place_landmarks; every landmark mesh imports into a world that "
        "never spawns it")
    body = text[text.index("def place_landmarks("):]
    body = body[:body.index("\ndef ", 1)] if "\ndef " in body[1:] else body
    assert "spawn_mesh(" in body, "place_landmarks never spawns anything"
    assert "build_tile_level" in text and "place_landmarks(" in text.split("def build_tile_level")[1], (
        "place_landmarks exists but build_tile_level never calls it")


def test_landmarks_are_placed_without_a_rotation():
    """``heading_deg`` is provenance. Using it as a yaw turns every landmark by its facade angle."""
    text = _build_levels()
    body = text[text.index("def place_landmarks("):]
    body = body[:body.index("\ndef ", 1)] if "\ndef " in body[1:] else body
    rotators = re.findall(r"unreal\.Rotator\(([^)]*)\)", body)
    assert rotators, "place_landmarks spawns without naming a rotation at all; be explicit"
    for args in rotators:
        values = [v.strip() for v in args.split(",")]
        assert all(re.fullmatch(r"0(\.0*)?f?", v) for v in values), (
            f"place_landmarks rotates a landmark by {args!r}. The models are already in NYC_TM "
            f"axes (blender/landmarks/common.py: 'no rotation to apply on import').")
    assert "heading_to_yaw" not in body and "math_angle_to_yaw" not in body, (
        "place_landmarks converts a heading to a yaw; heading_deg is the footprint's principal-axis "
        "bearing, recorded as provenance, not a placement instruction")


def test_the_index_generator_reproduces_the_catalogue():
    """Every catalogue entry with an origin has to reach the index, or it cannot be placed."""
    if not CATALOG_DIR.is_dir():
        pytest.skip("no landmark catalogue in this checkout")
    from nycsim_pipeline.unreal.landmarks_index import build_index

    doc = build_index()
    have = {r["id"] for r in doc["landmarks"]}
    expected = set()
    for path in sorted(CATALOG_DIR.glob("*.json")):
        entry = json.loads(path.read_text())
        if isinstance(entry.get("origin_tm"), list) and len(entry["origin_tm"]) == 3:
            expected.add(str(entry.get("id", path.stem)))
    missing = sorted(expected - have)
    assert not missing, f"{len(missing)} catalogue entries never reach the index: {missing[:10]}"
    assert doc["count"] == len(have)


def test_every_indexed_landmark_names_a_tile_that_contains_its_origin():
    """The tile field is what the level builder filters on; a wrong one hides the landmark."""
    if not CATALOG_DIR.is_dir():
        pytest.skip("no landmark catalogue in this checkout")
    from nycsim_pipeline.crs import TILE_SIZE_M
    from nycsim_pipeline.unreal.landmarks_index import build_index

    for row in build_index()["landmarks"]:
        x, y, _z = row["origin_tm"]
        tx, ty = (int(v) for v in row["tile"][2:].split("_", 1)[0:1] + [row["tile"][2:].split("_", 1)[1]])
        assert tx * TILE_SIZE_M <= x < (tx + 1) * TILE_SIZE_M, f"{row['id']}: x {x} not in {row['tile']}"
        assert ty * TILE_SIZE_M <= y < (ty + 1) * TILE_SIZE_M, f"{row['id']}: y {y} not in {row['tile']}"


def test_the_index_records_the_heading_under_a_name_that_cannot_be_mistaken_for_a_rotation():
    """The field is kept, because throwing provenance away is worse; it is named so it cannot be
    misused by the next reader who sees an angle beside a position."""
    from nycsim_pipeline.unreal.landmarks_index import build_index

    doc = build_index()
    if not doc["landmarks"]:
        pytest.skip("no landmarks in this checkout")
    row = doc["landmarks"][0]
    assert "heading_deg" not in row, "a bare heading_deg beside origin_tm invites exactly one bug"
    assert "heading_deg_not_a_rotation" in row
    assert "no rotation" in doc["placement"]
