"""Tests for the visual-comparison stage (`blender/verify/`, `docs/verification/comparison/`).

These cover the parts of the comparison pipeline that can be checked without spending a Cycles
render: the tile/radius arithmetic, the terrain sampler against the published heightmap contract,
the binary kit-placement record layout, the camera geometry (position, heading, field of view),
the Sun placement against the live-services SPA implementation, and the shape of whatever sheets
have been produced so far.

    PYTHONPATH=pipeline:services pytest tests/test_comparison.py -q
"""
from __future__ import annotations

import datetime as dt
import json
import math
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
VERIFY_DIR = REPO_ROOT / "blender" / "verify"
REFERENCE_DIR = REPO_ROOT / "docs" / "verification" / "reference"
COMPARISON_DIR = REPO_ROOT / "docs" / "verification" / "comparison"

for _p in (str(VERIFY_DIR), str(REPO_ROOT / "pipeline"), str(REPO_ROOT / "services"),
           str(REPO_ROOT / "blender" / "common")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

pytest.importorskip("numpy")
import numpy as np  # noqa: E402


def _skip_without_bpy():
    return pytest.importorskip("bpy", reason="Blender's bpy module is required for the verify scene")


# --------------------------------------------------------------------------- tiling arithmetic


def test_tiles_in_radius_covers_exactly_the_intersecting_tiles():
    _skip_without_bpy()
    import scene as vscene

    # A point in the middle of t_0_0 with a 100 m radius touches only that tile.
    assert vscene.tiles_in_radius(500.0, 500.0, 100.0) == [(0, 0)]
    # On the corner of four tiles every one of them is inside the disc.
    got = set(vscene.tiles_in_radius(1000.0, 1000.0, 50.0))
    assert got == {(0, 0), (0, 1), (1, 0), (1, 1)}
    # A 1.2 km radius from the centre of a tile reaches two tiles out along the axes but the
    # far diagonal corner tiles stay out (their nearest point is 1.27 km away).
    got = set(vscene.tiles_in_radius(500.0, 500.0, 1200.0))
    assert (2, 0) in got and (-2, 0) in got
    assert (2, 2) not in got
    for tx, ty in got:
        nx = min(max(500.0, tx * 1000.0), tx * 1000.0 + 1000.0)
        ny = min(max(500.0, ty * 1000.0), ty * 1000.0 + 1000.0)
        assert math.hypot(nx - 500.0, ny - 500.0) <= 1200.0 + 1e-9


# --------------------------------------------------------------------------- terrain sampler


def _some_terrain_tile() -> tuple[str, dict]:
    tiles = sorted((REPO_ROOT / "data" / "processed" / "tiles").glob("*/terrain.json"))
    if not tiles:
        pytest.skip("no terrain tiles produced yet")
    for p in tiles:
        meta = json.loads(p.read_text())
        if meta.get("has_land") and meta.get("z_max_m", 0) > meta.get("z_min_m", 0):
            return p.parent.name, meta
    pytest.skip("no terrain tile with relief produced yet")


def test_terrain_sampler_reproduces_the_published_height_range():
    _skip_without_bpy()
    import scene as vscene

    tile, meta = _some_terrain_tile()
    tx, ty = int(meta["tx"]), int(meta["ty"])
    s = vscene.TerrainSampler()
    xs, ys = np.meshgrid(np.linspace(tx * 1000.0 + 1.0, tx * 1000.0 + 999.0, 61),
                         np.linspace(ty * 1000.0 + 1.0, ty * 1000.0 + 999.0, 61))
    z, water = s.grid(xs, ys)
    assert not np.isnan(z).any(), f"{tile} sampled to NaN inside its own footprint"
    lo, hi = float(meta["z_min_m"]), float(meta["z_max_m"])
    assert z.min() >= lo - 0.01, (z.min(), lo)
    assert z.max() <= hi + 0.01, (z.max(), hi)
    assert water.shape == z.shape
    if not meta.get("has_water"):
        assert not water.any()


def test_terrain_sampler_orientation_matches_the_north_first_png_row():
    """PNG row 0 is the north edge, so sampling near y_max must read the first image row."""
    _skip_without_bpy()
    from PIL import Image
    import scene as vscene

    tile, meta = _some_terrain_tile()
    tx, ty = int(meta["tx"]), int(meta["ty"])
    with Image.open(REPO_ROOT / "data" / "processed" / "tiles" / tile / "terrain.png") as im:
        arr = np.asarray(im).astype(np.float64)
    z_north_row = float(meta["z_min_m"]) + arr[0, 250] * float(meta["z_scale_m"])
    z_south_row = float(meta["z_min_m"]) + arr[500, 250] * float(meta["z_scale_m"])
    s = vscene.TerrainSampler()
    got_north = s.z_at(tx * 1000.0 + 500.0, ty * 1000.0 + 1000.0)
    got_south = s.z_at(tx * 1000.0 + 500.0, ty * 1000.0 + 0.0)
    assert got_north == pytest.approx(z_north_row, abs=0.02)
    assert got_south == pytest.approx(z_south_row, abs=0.02)


def test_terrain_sampler_reports_missing_tiles_instead_of_inventing_ground():
    _skip_without_bpy()
    import scene as vscene

    s = vscene.TerrainSampler()
    # Far outside the project scope: no tile can exist there.
    z, _ = s.grid(np.array([[900000.0]]), np.array([[900000.0]]))
    assert np.isnan(z[0, 0])
    assert s.z_at(900000.0, 900000.0) is None
    assert s.missing


# --------------------------------------------------------------------------- kit record layout


def test_kit_record_matches_the_data_contract_header():
    _skip_without_bpy()
    import scene as vscene

    assert vscene.KIT_RECORD.itemsize == 40
    headers = sorted((REPO_ROOT / "data" / "processed" / "tiles").glob("*/kit_placements.json"))
    if not headers:
        pytest.skip("no kit placements produced yet")
    h = json.loads(headers[0].read_text())
    assert h["record_bytes"] == vscene.KIT_RECORD.itemsize
    assert h["byte_order"] == "little"
    assert [f["name"] for f in h["fields"]] == list(vscene.KIT_RECORD.names)
    binary = headers[0].with_suffix(".bin")
    a = np.fromfile(binary, dtype=vscene.KIT_RECORD)
    assert a.size == h["count"], (a.size, h["count"])
    # Every placement must sit inside the tile it is filed under, +- a piece's own reach.
    tile = h["tile"]
    tx, ty = (int(v) for v in tile.split("_")[1:3])
    assert a["x"].min() >= tx * 1000.0 - 60.0
    assert a["x"].max() <= tx * 1000.0 + 1060.0
    assert a["y"].min() >= ty * 1000.0 - 60.0
    assert a["y"].max() <= ty * 1000.0 + 1060.0


def test_kit_ids_resolve_to_files_or_are_reported_as_unresolved():
    _skip_without_bpy()
    import scene as vscene

    kit_map, why = vscene.load_kit_map()
    if not kit_map:
        pytest.skip(f"kit registry not resolvable yet: {why}")
    missing = [e["glb"] for e in kit_map.values()
               if not (REPO_ROOT / "blender_out" / e["glb"]).exists()]
    assert not missing, f"{len(missing)} registry entries point at files that do not exist: {missing[:5]}"


# --------------------------------------------------------------------------- camera


def test_focal_length_to_field_of_view():
    _skip_without_bpy()
    import camera as vcam

    assert vcam.horizontal_fov_deg(35.0, 36.0) == pytest.approx(54.43, abs=0.02)
    assert vcam.horizontal_fov_deg(24.0, 36.0) == pytest.approx(73.74, abs=0.02)
    assert vcam.horizontal_fov_deg(50.0, 36.0) == pytest.approx(39.60, abs=0.02)


@pytest.mark.parametrize("azimuth,expect", [
    (0.0, (0.0, 1.0)),      # north
    (90.0, (1.0, 0.0)),     # east
    (180.0, (0.0, -1.0)),   # south
    (270.0, (-1.0, 0.0)),   # west
])
def test_camera_points_along_the_reference_azimuth(azimuth, expect):
    bpy = _skip_without_bpy()
    import camera as vcam
    import nycsim_bpy as nb

    nb.reset_scene()
    p = vcam.place_camera(slug="_unit_test", lat=40.75, lon=-73.98, azimuth_deg=azimuth,
                          sampler=None, resolution=(320, 200))
    cam = bpy.context.scene.camera
    fwd = cam.matrix_world.to_quaternion() @ __import__("mathutils").Vector((0.0, 0.0, -1.0))
    assert fwd.x == pytest.approx(expect[0], abs=1e-6)
    assert fwd.y == pytest.approx(expect[1], abs=1e-6)
    assert fwd.z == pytest.approx(0.0, abs=1e-6)
    assert p.hfov_deg == pytest.approx(vcam.horizontal_fov_deg(p.focal_mm), abs=1e-9)


def test_camera_sits_at_the_reference_viewpoint_in_nyc_tm():
    _skip_without_bpy()
    import camera as vcam
    import nycsim_bpy as nb
    from nycsim_pipeline.crs import lonlat_to_tm

    meta = json.loads((REFERENCE_DIR / "fifth_ave_42nd_north" / "meta.json").read_text())
    vp = meta["viewpoint"]
    nb.reset_scene()
    p = vcam.place_camera(slug="fifth_ave_42nd_north", lat=vp["lat"], lon=vp["lon"],
                          azimuth_deg=vp["azimuth_deg"], sampler=None, resolution=(320, 200))
    x, y = lonlat_to_tm(vp["lon"], vp["lat"])
    assert p.x == pytest.approx(x, abs=1e-6)
    assert p.y == pytest.approx(y, abs=1e-6)
    assert p.azimuth_deg == pytest.approx(vp["azimuth_deg"])


def test_eye_height_is_the_standing_default_unless_the_note_says_otherwise():
    _skip_without_bpy()
    import camera as vcam

    # A sidewalk view gets the standing default.
    assert vcam.eye_rule_for("fifth_ave_42nd_north").height_m == pytest.approx(1.60)
    # The three viewpoints whose note names a structure or a vessel do not.
    tall = vcam.eye_rule_for("top_of_the_rock_south")
    assert tall.height_m > 250.0 and "30 Rockefeller" in tall.source
    ferry = vcam.eye_rule_for("staten_island_ferry_lower_manhattan")
    assert ferry.datum == "sea" and 5.0 < ferry.height_m < 15.0
    steps = vcam.eye_rule_for("times_square_duffy_south_day")
    assert 5.0 < steps.height_m < 8.0 and "TKTS" in steps.source
    for rule in vcam.EYE_OVERRIDES.values():
        assert rule.source.strip(), "every non-default eye height must state where the number came from"
        assert rule.datum in ("terrain", "sea")


# --------------------------------------------------------------------------- sun placement


def test_sun_position_matches_the_live_services_spa():
    pytest.importorskip("bpy", reason="render_sheets imports the Blender scene builder")
    import render_sheets as rs
    from nycsim_live import astronomy

    when = dt.datetime(2023, 5, 12, 12, 18, 49, tzinfo=dt.timezone.utc).astimezone(
        __import__("zoneinfo").ZoneInfo("America/New_York"))
    got = rs.sun_for(40.7592, -73.9847, when)
    ref = astronomy.solar_position(when.astimezone(dt.timezone.utc),
                                   astronomy.Observer(40.7592, -73.9847, 20.0))
    assert got["azimuth_deg"] == pytest.approx(ref.azimuth, abs=1e-9)
    assert got["elevation_deg"] == pytest.approx(ref.elevation, abs=1e-9)


def test_photo_instant_prefers_the_exif_timestamp_and_says_when_it_guessed():
    pytest.importorskip("bpy", reason="render_sheets imports the Blender scene builder")
    import render_sheets as rs

    when, note = rs.photo_instant({"date_taken": "2023-05-12 12:18:49"})
    assert (when.year, when.hour, when.minute) == (2023, 12, 18)
    assert "EXIF" in note
    when, note = rs.photo_instant({"date_taken": "2017"})
    assert when.hour == 9 and "assumed" in note
    when, note = rs.photo_instant({"date_taken": "", "year": 2019})
    assert when.year == 2019 and "assumed" in note


def test_a_daylight_subject_is_never_paired_with_an_after_dark_photograph():
    pytest.importorskip("bpy", reason="render_sheets imports the Blender scene builder")
    import render_sheets as rs

    checked = 0
    for slug in rs.list_slugs():
        meta = rs.load_meta(slug)
        photo = rs.pick_reference_photo(meta)
        if photo is None:
            continue
        when, _ = rs.photo_instant(photo)
        elev = rs.sun_for(meta["viewpoint"]["lat"], meta["viewpoint"]["lon"], when)["elevation_deg"]
        others = []
        for p in meta.get("photos", []):
            if not (REFERENCE_DIR / slug / p["file"]).exists():
                continue
            w, _ = rs.photo_instant(p)
            others.append(rs.sun_for(meta["viewpoint"]["lat"], meta["viewpoint"]["lon"], w)["elevation_deg"])
        if not others:
            continue
        checked += 1
        if meta.get("night"):
            assert elev <= min(others) + 1e-6 or elev < 0.0
        elif max(others) > 12.0:
            assert elev > 3.0, f"{slug} picked a photo with the Sun at {elev:.1f} deg"
    assert checked > 10


# --------------------------------------------------------------------------- produced artefacts


def _rendered_slugs() -> list[str]:
    if not COMPARISON_DIR.is_dir():
        return []
    return sorted(d.name for d in COMPARISON_DIR.iterdir()
                  if d.is_dir() and (d / "render.json").exists())


def test_every_render_record_names_its_photograph_licence_and_camera():
    slugs = _rendered_slugs()
    if not slugs:
        pytest.skip("no comparison renders produced yet")
    for slug in slugs:
        rec = json.loads((COMPARISON_DIR / slug / "render.json").read_text())
        assert rec["status"] == "rendered", slug
        ph = rec["reference_photo"]
        for key in ("file", "author", "licence", "page_url"):
            assert ph.get(key), f"{slug}: reference photo record is missing {key}"
        assert (REFERENCE_DIR / slug / ph["file"]).exists(), f"{slug}: {ph['file']} is gone"
        cam = rec["camera"]
        for key in ("x", "y", "z", "azimuth_deg", "focal_mm", "hfov_deg", "eye_height_m", "eye_source"):
            assert cam.get(key) is not None, f"{slug}: camera record is missing {key}"
        assert rec["camera"]["azimuth_deg"] == pytest.approx(rec["viewpoint"]["azimuth_deg"])
        assert rec["sun"]["elevation_deg"] is not None
        assert rec["scene"]["triangles"] > 0


def test_every_render_has_a_sheet_and_a_written_assessment():
    slugs = _rendered_slugs()
    if not slugs:
        pytest.skip("no comparison renders produced yet")
    for slug in slugs:
        d = COMPARISON_DIR / slug
        assert (d / "render.png").exists(), f"{slug}: render.png missing"
        assert (d / "sheet.png").exists(), f"{slug}: sheet.png missing"
        a = d / "assessment.md"
        assert a.exists(), f"{slug}: assessment.md missing"
        text = a.read_text()
        assert len(text) > 400, f"{slug}: assessment is too short to be a real judgement"
        for heading in ("What matches", "What does not", "Cause"):
            assert heading.lower() in text.lower(), f"{slug}: assessment has no '{heading}' section"


def test_sheet_is_a_two_panel_image_wider_than_it_is_tall_per_panel():
    pytest.importorskip("PIL")
    from PIL import Image
    slugs = _rendered_slugs()
    if not slugs:
        pytest.skip("no comparison renders produced yet")
    for slug in slugs:
        p = COMPARISON_DIR / slug / "sheet.png"
        if not p.exists():
            continue
        with Image.open(p) as im:
            w, h = im.size
        assert w >= 2 * 1280, f"{slug}: sheet is only {w} px wide, expected two 1280 px panels"
        assert h > 400


def test_index_and_report_exist_once_any_sheet_does():
    slugs = _rendered_slugs()
    if not slugs:
        pytest.skip("no comparison renders produced yet")
    index = COMPARISON_DIR / "INDEX.md"
    report = COMPARISON_DIR / "REPORT.md"
    assert index.exists(), "docs/verification/comparison/INDEX.md missing"
    assert report.exists(), "docs/verification/comparison/REPORT.md missing"
    idx = index.read_text()
    for slug in slugs:
        assert slug in idx, f"{slug} is rendered but not listed in INDEX.md"
    rep = report.read_text()
    for name in ("Brooklyn Heights Promenade", "Top of the Rock", "Duffy Square",
                 "Bethesda Terrace", "Staten Island Ferry", "DUMBO"):
        assert name in rep, f"REPORT.md does not account for {name}"
