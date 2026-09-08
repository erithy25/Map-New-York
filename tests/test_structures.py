"""The elevated railways and the waterfront: what the stage builds, and what it deliberately does not.

986 km of rail structure and 166 ha of pier, seawall and jetty were surveyed, measured, written to
parquet and consumed by nothing. The checks here are about the two ways this stage could be wrong in
a way nobody would see: building geometry the terrain already has (an embankment berm on top of the
berm in the DEM), and building geometry a landmark already has (a second subway deck across the
Manhattan Bridge).
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "blender" / "structures"))
sys.path.insert(0, str(REPO_ROOT / "pipeline"))

import stlib  # noqa: E402

RAIL = REPO_ROOT / "data" / "processed" / "transit" / "rail_structures.parquet"
WATER = REPO_ROOT / "data" / "processed" / "water" / "structures.parquet"
LANDMARKS = REPO_ROOT / "data" / "processed" / "landmarks" / "landmarks.json"

needs_rail = pytest.mark.skipif(not RAIL.is_file(), reason="no rail structures table")


# --------------------------------------------------------------------------------- geometry

def test_a_deck_is_a_closed_box_of_the_right_width():
    buf = stlib.MeshBuffer("el_steel")
    line = np.array([[0.0, 0.0], [100.0, 0.0]])
    stlib.deck_ribbon(buf, line, 11.34, 20.0, 1.2)
    v = np.asarray(buf.verts)
    assert len(buf.faces) == 6 * 2, "a straight two-vertex deck is six quads"
    assert v[:, 1].max() - v[:, 1].min() == pytest.approx(11.34), "deck width"
    assert v[:, 2].max() == pytest.approx(20.0)
    assert v[:, 2].min() == pytest.approx(18.8), "soffit is the deck thickness below the top"


def test_a_mitred_deck_keeps_its_width_through_a_bend():
    """A bend taken with the segment normals alone pinches the deck; the mitre is what stops it."""
    buf = stlib.MeshBuffer("el_steel")
    line = np.array([[0.0, 0.0], [50.0, 0.0], [100.0, 50.0]])   # a 45-degree turn
    stlib.deck_ribbon(buf, line, 12.0, 10.0, 1.0)
    v = np.asarray(buf.verts)
    top = v[np.isclose(v[:, 2], 10.0)]
    left, right = top[:3, :2], top[3:6, :2]
    # The invariant is not the distance between the two mitre points -- at a bend that is
    # width / cos(half the turn), which is what a mitre is -- but that each offset **edge** runs
    # parallel to its centreline segment at exactly half the width.
    for i in range(2):
        a, b = line[i], line[i + 1]
        d = (b - a) / np.linalg.norm(b - a)
        n = np.array([-d[1], d[0]])
        for edge, sign in ((left, +1.0), (right, -1.0)):
            for k in (i, i + 1):
                assert float((edge[k] - a) @ n) == pytest.approx(sign * 6.0, abs=1e-9), (
                    "the deck edge is not parallel to the track at half the width")


def test_bents_stand_on_the_ground_they_are_given():
    buf = stlib.MeshBuffer("el_steel")
    line = np.array([[0.0, 0.0], [100.0, 0.0]])
    n = stlib.bents(buf, line, 11.34, 18.8, 5.0, 13.72, 0.45, 1.3, 0.9)
    v = np.asarray(buf.verts)
    assert n >= 2 and n % 2 == 0, "a wide structure gets two columns per bent"
    assert v[:, 2].min() == pytest.approx(5.0), "columns reach the ground"
    assert v[:, 2].max() == pytest.approx(18.8), "the cap girder reaches the soffit"


def test_a_narrow_structure_gets_one_line_of_columns():
    buf = stlib.MeshBuffer("el_steel")
    line = np.array([[0.0, 0.0], [40.0, 0.0]])
    n = stlib.bents(buf, line, 4.83, 12.0, 2.0, 13.72, 0.45, 1.3, 0.9)
    v = np.asarray(buf.verts)
    assert n >= 1
    assert abs(v[:, 1]).max() == pytest.approx(0.225, abs=1e-6), (
        "a single-track deck is carried on one central column, not a two-column bent")


def test_a_column_never_hangs_in_the_air_over_missing_terrain():
    buf = stlib.MeshBuffer("el_steel")
    line = np.array([[0.0, 0.0], [100.0, 0.0]])

    def ground(xs, ys):
        return np.where(np.asarray(xs) < 50.0, 3.0, np.nan)

    n = stlib.bents(buf, line, 11.34, 18.8, ground, 13.72, 0.45, 1.3, 0.9)
    v = np.asarray(buf.verts)
    assert n > 0
    assert v[:, 0].max() < 55.0, "no column was placed where the terrain is unknown"
    assert v[:, 2].min() == pytest.approx(3.0)


def test_a_deck_too_close_to_the_ground_gets_no_columns():
    buf = stlib.MeshBuffer("el_steel")
    line = np.array([[0.0, 0.0], [100.0, 0.0]])
    n = stlib.bents(buf, line, 11.34, 5.2, 5.0, 13.72, 0.45, 1.3, 0.9)
    assert n == 0, "a soffit 0.2 m over the ground is a portal, not a structure on columns"


def test_piles_stay_inside_the_deck_they_hold_up():
    ring = np.array([[0.0, 0.0], [30.0, 0.0], [30.0, 12.0], [0.0, 12.0]])
    pts = stlib.pile_grid(ring, stlib.PILE_SPACING_M)
    assert len(pts) > 0
    assert stlib.point_in_ring(pts, ring).all()
    assert stlib.distance_to_ring(pts, ring).min() >= 1.0


def test_ear_clip_covers_the_polygon_it_is_given():
    ring = np.array([[0.0, 0.0], [10.0, 0.0], [10.0, 4.0], [4.0, 4.0], [4.0, 9.0], [0.0, 9.0]])
    tris = stlib.ear_clip(ring)
    assert len(tris) == len(ring) - 2
    area = sum(abs(stlib.ring_area(ring[t])) for t in tris)
    assert area == pytest.approx(abs(stlib.ring_area(ring)), rel=1e-9)


# --------------------------------------------------------------------------------- what is not built

@needs_rail
def test_only_the_classes_that_stand_in_the_air_are_built():
    """An embankment and an open cut are in the terrain; building them again doubles them.

    The measurement behind this is in the stage's own docstring: sampling the landscape across 200
    structures of each class, an embankment centreline stands 3.69 m above its flanks and an open cut
    3.32 m below, while an elevated one is level with them.
    """
    import build_structures as bs

    assert set(bs.BUILT_RAIL_KINDS) == {"elevated", "viaduct"}
    doc = (REPO_ROOT / "blender" / "structures" / "build_structures.py").read_text()
    assert "the terrain already carries the berm" in doc
    assert "the terrain already carries the cutting" in doc


@needs_rail
def test_a_bridge_that_models_its_own_tracks_keeps_them():
    """The Manhattan, Williamsburg and Hell Gate bridges carry rail and are modelled as landmarks."""
    if not LANDMARKS.is_file():
        pytest.skip("no landmark index")
    doc = json.loads(LANDMARKS.read_text())
    rail = {r["stem"] for r in doc["landmarks"] if r.get("rail_tracks")}
    assert {"b_manhattan_bridge", "b_williamsburg_bridge", "b_hell_gate"} <= rail

    import build_structures as bs

    boxes, names = bs.landmark_boxes()
    assert set(names) == rail, "only the rail-carrying landmarks may take structures away"
    assert len(boxes) == len(names)


def test_every_landmark_has_bounds_now():
    """34 of 93 catalogues publish none, so the index reads them out of the glb instead."""
    if not LANDMARKS.is_file():
        pytest.skip("no landmark index")
    doc = json.loads(LANDMARKS.read_text())
    without = [r["stem"] for r in doc["landmarks"] if not (r.get("bounds_local_m") or {}).get("min")]
    assert not without, f"{len(without)} landmarks have no plan bounds: {without[:6]}"


# --------------------------------------------------------------------------------- the measured table

@needs_rail
def test_the_deck_width_is_measured_from_parallel_tracks():
    import pyarrow.parquet as pq

    t = pq.read_table(RAIL, columns=["kind", "deck_width_m", "track_count", "deck_width_source", "name"])
    kind = np.asarray(t.column("kind").to_pylist(), dtype=object)
    w = np.asarray(t.column("deck_width_m"), dtype=float)
    built = np.isin(kind, np.asarray(["elevated", "viaduct"], dtype=object))
    assert np.isfinite(w[built]).all(), "every built structure needs a width"
    assert not np.isfinite(w[~built]).any(), "an earthwork has no deck width"
    # A three-track elevated at the standard 3.9 m track spacing plus the overhang is about 11.3 m.
    assert 10.0 <= float(np.median(w[built])) <= 13.0, float(np.median(w[built]))


@needs_rail
def test_the_deck_profile_is_continuous_and_within_grade():
    """Adjacent structures used to disagree by more than a metre at 31.5 % of their shared ends."""
    import pyarrow.parquet as pq
    import shapely

    t = pq.read_table(RAIL)
    kind = np.asarray(t.column("kind").to_pylist(), dtype=object)
    built = np.isin(kind, np.asarray(["elevated", "viaduct"], dtype=object))
    z0 = np.asarray(t.column("deck_z_start"), dtype=float)
    z1 = np.asarray(t.column("deck_z_end"), dtype=float)
    L = np.asarray(t.column("length_m"), dtype=float)
    assert np.isfinite(z0[built]).all() and np.isfinite(z1[built]).all()

    grade = np.abs(z1[built] - z0[built]) / np.maximum(L[built], 1.0)
    assert grade.max() <= 0.0401, f"deck grade {grade.max():.3f} exceeds what rail can climb"

    geoms = np.asarray(shapely.from_wkb(t.column("geometry").to_pylist()), dtype=object)
    ends: dict[tuple[int, int], list[float]] = {}
    for j in np.nonzero(built)[0]:
        c = np.asarray(geoms[j].coords)[:, :2]
        for p, z in ((c[0], z0[j]), (c[-1], z1[j])):
            ends.setdefault((round(p[0] / 0.05), round(p[1] / 0.05)), []).append(float(z))
    jumps = [max(v) - min(v) for v in ends.values() if len(v) > 1]
    assert jumps, "no shared endpoints found"
    assert max(jumps) < 1e-3, f"the deck steps by {max(jumps):.3f} m where two structures meet"


@needs_rail
def test_every_built_structure_has_an_absolute_deck_elevation():
    """The class-median fallback filled the height and not the elevation; 1,441 rows had no deck_z."""
    import pyarrow.parquet as pq

    t = pq.read_table(RAIL, columns=["kind", "deck_z", "ground_z", "deck_height_m"])
    kind = np.asarray(t.column("kind").to_pylist(), dtype=object)
    built = np.isin(kind, np.asarray(["elevated", "viaduct"], dtype=object))
    z = np.asarray(t.column("deck_z"), dtype=float)
    assert np.isfinite(z[built]).all(), (
        f"{int((~np.isfinite(z[built])).sum())} built structures have no deck elevation")


# --------------------------------------------------------------------------------- the built tiles

def _manifests():
    return sorted((REPO_ROOT / "blender_out" / "tiles").glob("*/structures_manifest.json"))


def test_the_built_tiles_stand_over_the_ground():
    """A deck whose soffit is under the terrain is a structure buried in a hill."""
    ms = _manifests()
    if not ms:
        pytest.skip("no structure tiles built")
    worst = 0.0
    buried = 0
    samples = 0
    for p in ms:
        c = json.loads(p.read_text()).get("soffit_clearance_m") or {}
        if not c.get("samples"):
            continue
        samples += c["samples"]
        buried += round(c["below_ground_fraction"] * c["samples"])
        worst = max(worst, c["below_ground_fraction"])
    assert samples > 0
    assert buried / samples < 0.02, (
        f"{buried} of {samples} deck samples ({buried / samples:.2%}) sit below the terrain")


def test_the_structure_meshes_carry_a_surface_class():
    ms = _manifests()
    if not ms:
        pytest.skip("no structure tiles built")
    for p in ms[:40]:
        for m in json.loads(p.read_text())["meshes"]:
            assert m["material"] == f"struct_{m['part']}", "the slot name must not carry the tile"
            assert m["surface_class"] == stlib.SURFACE_CLASS[m["part"]]


def test_the_manifest_has_a_rule_for_the_structure_file():
    from nycsim_pipeline.unreal.manifest import resolve_glb

    got = resolve_glb("tiles/t_-4_4/tile_structures.glb")
    assert got is not None, "tile_structures.glb has no import rule"
    dst, settings = got[0], got[1]
    assert dst.endswith("/SM_Structures"), dst
    assert settings == "structure_nanite", settings


def test_the_level_builder_spawns_them():
    src = (REPO_ROOT / "unreal" / "NYCSim" / "Content" / "Python" / "build_levels.py").read_text()
    assert "def place_structures(" in src
    assert 'SM_Structures' in src
    assert 'result["structures"] = place_structures(tile)' in src
