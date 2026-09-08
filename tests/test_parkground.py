"""The ground under the city's open space, and the three friction classes nothing else produces.

27,493 surveyed polygons -- 130 km² of park boundary, greenstreet, court, ball field, pool, running
track, skating rink, cemetery and vacant ground -- were downloaded at the start of this build and
read by nothing since. The terrain was the only thing under a park, so Central Park, Prospect Park,
every schoolyard court and every ball field was drawn as the same material as a vacant lot.

`SurfaceClass` declares `Grass`, `Water` and `Ice`, and before this stage no surface in the world
produced any of them: three rows of the tyre friction model that could not be reached.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "pipeline"))
sys.path.insert(0, str(REPO_ROOT / "blender" / "parks"))
sys.path.insert(0, str(REPO_ROOT / "blender" / "roads"))

SURFACES = REPO_ROOT / "data" / "processed" / "parks" / "surfaces.parquet"
needs_table = pytest.mark.skipif(not SURFACES.is_file(), reason="no open-space table")


def _kinds():
    from nycsim_pipeline.parks.surfaces import KINDS

    return KINDS


def test_every_feature_code_maps_to_a_kind_and_every_kind_has_a_surface_class():
    from nycsim_pipeline.parks.surfaces import FEAT_TO_KIND, KINDS

    assert set(FEAT_TO_KIND.values()) <= set(KINDS)
    for k, v in KINDS.items():
        assert v["surface_class"] in range(0, 14), v
        assert v["name"] and v["surface"]
    # The Capture Rules' own codes, not a name match: 4980 park boundary, 4950 pool, 4970 rink.
    assert FEAT_TO_KIND[4980] == 0 and FEAT_TO_KIND[4950] == 6 and FEAT_TO_KIND[4970] == 8


def test_the_three_unreachable_friction_classes_are_now_produced():
    """Grass, Water and Ice had no producer anywhere in the world."""
    classes = {v["surface_class"] for v in _kinds().values()}
    assert {8, 10, 13} <= classes, "grass, water and ice are still unreachable"


def test_a_lift_covers_its_own_drape_tolerance():
    """A lawn draped to 0.20 m of tolerance and lifted 0.03 m is under the ground half the time.

    That was measured before these numbers were set -- 47.8 % of one Central Park tile -- and the
    rule that fixes it is this one: the lift has to be at least the tolerance the surface is draped
    to, or the terrain shows through it.
    """
    import build_parkground as bp

    for k, meta in _kinds().items():
        if meta.get("below_grade"):
            continue
        assert meta["lift_m"] >= bp.TOL_M[k] - 1e-9, (
            f"{meta['name']}: lift {meta['lift_m']} m is under its {bp.TOL_M[k]} m drape tolerance")


def test_a_below_grade_surface_is_declared_rather_than_counted_as_a_defect():
    kinds = _kinds()
    assert kinds[6].get("below_grade"), "a pool's water sits under its coping"
    assert kinds[6]["lift_m"] < 0.0


@needs_table
def test_the_table_covers_the_survey_and_carries_its_classes():
    import pyarrow.parquet as pq

    t = pq.read_table(SURFACES, columns=["kind", "kind_name", "surface_class", "area_m2", "feat_code"])
    assert t.num_rows > 25_000, t.num_rows
    area = np.asarray(t.column("area_m2"), dtype=float)
    assert area.sum() / 1e4 > 10_000, "under 10,000 ha of open space is not New York"
    kind = np.asarray(t.column("kind"), dtype=np.int16)
    cls = np.asarray(t.column("surface_class"), dtype=np.int16)
    kinds = _kinds()
    for k in np.unique(kind):
        assert cls[kind == k][0] == kinds[int(k)]["surface_class"]
    names = set(np.asarray(t.column("kind_name").to_pylist(), dtype=object).tolist())
    assert {"park_ground", "court", "pool", "skating_rink", "track"} <= names


@needs_table
def test_a_facility_is_cut_out_of_the_park_ground_it_stands_in():
    """A court and the park boundary around it are two slabs over one piece of ground."""
    import pyarrow.parquet as pq
    import shapely

    t = pq.read_table(SURFACES, columns=["kind", "geometry"])
    kind = np.asarray(t.column("kind"), dtype=np.int16)
    geoms = np.asarray(shapely.from_wkb(t.column("geometry").to_pylist()), dtype=object)
    ground = geoms[np.isin(kind, [0, 9, 10, 11])]
    facility = geoms[~np.isin(kind, [0, 9, 10, 11])]
    if not len(ground) or not len(facility):
        pytest.skip("one of the two populations is empty")
    tree = shapely.STRtree(ground)
    overlap = 0.0
    rng = np.random.default_rng(7)
    sample = facility[rng.choice(len(facility), size=min(400, len(facility)), replace=False)]
    for f in sample:
        for j in tree.query(f, predicate="intersects"):
            overlap += shapely.intersection(f, ground[int(j)]).area
    assert overlap < 1000.0, f"{overlap:.0f} m2 of facility still sits inside park ground"


def _manifests():
    return sorted((REPO_ROOT / "blender_out" / "tiles").glob("*/parkground_manifest.json"))


def test_the_park_ground_stands_over_the_terrain():
    ms = _manifests()
    if not ms:
        pytest.skip("no park ground tiles built")
    total = pierced = 0
    for p in ms:
        r = json.loads(p.read_text()).get("drape_residual_m") or {}
        if not r.get("samples"):
            continue
        total += r["samples"]
        pierced += round(r["pierced_fraction"] * r["samples"])
    assert total > 0
    assert pierced / total < 0.01, (
        f"{pierced} of {total} samples ({pierced / total:.2%}) show terrain through the open space")


def test_the_pavement_is_subtracted_so_a_park_path_has_no_kerb():
    ms = _manifests()
    if not ms:
        pytest.skip("no park ground tiles built")
    cut = sum(json.loads(p.read_text()).get("pavement_subtracted_m2", 0.0) for p in ms)
    assert cut > 0.0, "no tile subtracted its own pavement; every park path would have a 22 cm kerb"


def test_the_manifest_and_the_level_builder_carry_it():
    from nycsim_pipeline.unreal.manifest import resolve_glb

    got = resolve_glb("tiles/t_-3_7/tile_parkground.glb")
    assert got is not None and got[0].endswith("/SM_ParkGround"), got
    assert got[1] == "parkground_nanite"
    src = (REPO_ROOT / "unreal" / "NYCSim" / "Content" / "Python" / "build_levels.py").read_text()
    assert "def place_parkground(" in src and "SM_ParkGround" in src
    assert 'result["parkground"] = place_parkground(tile)' in src
