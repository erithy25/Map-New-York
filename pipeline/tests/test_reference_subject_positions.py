"""Does each reference item point at the thing it names?

Every other guard on these items asks about the *camera*: is the viewpoint on a street
(``tools/audit_viewpoint_aim.py``), is the subject inside the frame's cone
(``tools/audit_subject_aim.py``), is the line to it clear (``camera.subject_sightline``). All of
them take the subject's coordinate as given, and none of them ever asked whether that coordinate is
where the subject is.

``landmark_kings_theatre`` is what that costs. Its subject stood at 40.6497, -73.9578 -- **414.6 m
north of the Kings Theatre**, four blocks up Flatbush Avenue. Every downstream check passed: the
viewpoint sat on a real sidewalk 60 m from that point, the azimuth pointed at it, the frame
contained it, and the photographs were geosearched in a 250 m circle around it. The sheet would
have been a picture of the wrong street, labelled with the theatre's name (docs/DEVIATIONS.md J57).

The test is deliberately narrow so that it cannot itself become the kind of fuzzy matcher it exists
to catch: it compares a subject only against an OSM feature whose **name matches exactly** after
case, punctuation and parentheticals are normalised away. A looser matcher was tried first and
paired "New York State Pavilion" with "Staten Island Skating Pavilion" 39 km away -- a correct
measurement of something other than the thing it stood for, in the audit written to catch exactly
that. So: 43 of the 138 subjects are covered here, and the other 95 are not claimed to be checked.
"""
from __future__ import annotations

import json
import math
import re
import struct
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from nycsim_pipeline.crs import lonlat_to_tm
from nycsim_pipeline.paths import PROCESSED

REFERENCE = Path(__file__).resolve().parents[2] / "docs" / "verification" / "reference"
POIS = PROCESSED / "osm" / "pois.parquet"

#: Past this, the subject cannot be standing on the feature that shares its name. NYC's largest
#: named subjects are a couple of city blocks across -- Chelsea Market's block runs 250 m, the Port
#: Authority Bus Terminal covers two -- so an OSM node at one end and a hand-picked aim point at the
#: other are legitimately 100 m or more apart. 150 m is past any of them and is a **choice**: it is
#: the distance at which "the same building" stops being a possible explanation.
MAX_M = 150.0

#: Reported but not failed: far enough to be worth a reader's eye, near enough that the size of the
#: subject explains it.
REPORT_M = 30.0


def _norm(name: str) -> str:
    name = re.sub(r"\((.*?)\)", " ", str(name).lower())
    return " ".join(re.sub(r"[^a-z0-9 ]", " ", name).split())


def _osm_by_name() -> dict[str, list[tuple[float, float]]]:
    df = pd.read_parquet(POIS, columns=["x", "y", "name"])
    df = df[df["name"].astype(str).str.len() > 2]
    out: dict[str, list[tuple[float, float]]] = {}
    for n, x, y in zip(df["name"].astype(str), df["x"], df["y"]):
        out.setdefault(_norm(n), []).append((float(x), float(y)))
    return out


def _items() -> list[tuple[str, str, float, float]]:
    got = []
    for meta in sorted(REFERENCE.glob("*/meta.json")):
        doc = json.loads(meta.read_text())
        sub = doc.get("subject") or {}
        if sub.get("lat") is None or sub.get("lon") is None:
            continue
        x, y = (float(v) for v in lonlat_to_tm(sub["lon"], sub["lat"]))
        got.append((doc["slug"], str(sub.get("name") or ""), x, y))
    return got


@pytest.mark.skipif(not POIS.is_file(), reason="the OSM extract has not been built")
def test_every_subject_that_names_an_osm_feature_stands_on_it():
    osm = _osm_by_name()
    checked, far, report = 0, [], []
    for slug, name, x, y in _items():
        cands = osm.get(_norm(name))
        if not cands:
            continue
        checked += 1
        d = min(math.hypot(px - x, py - y) for px, py in cands)
        if d > MAX_M:
            far.append((d, slug, name))
        elif d > REPORT_M:
            report.append((d, slug, name))
    assert checked >= 40, f"only {checked} subjects matched an OSM name exactly; the audit lost its reach"
    if report:
        print("\nsubjects 30-150 m from the OSM feature they name (a large subject explains this):")
        for d, slug, name in sorted(report, reverse=True):
            print(f"   {d:7.1f} m  {slug:44} {name}")
    assert not far, "subject coordinates too far from the feature they name:\n" + "\n".join(
        f"   {d:7.1f} m  {slug:44} {name}" for d, slug, name in sorted(far, reverse=True))


@pytest.mark.skipif(not POIS.is_file(), reason="the OSM extract has not been built")
def test_the_kings_theatre_subject_is_on_the_kings_theatre():
    """The case that found this, kept as its own test so the number is in the record."""
    osm = _osm_by_name()
    cands = osm.get("kings theatre")
    assert cands, "OSM way 250132955 'Kings Theatre' is missing from the extract"
    got = {slug: (x, y) for slug, _n, x, y in _items()}
    x, y = got["landmark_kings_theatre"]
    d = min(math.hypot(px - x, py - y) for px, py in cands)
    assert d < 40.0, f"the subject stands {d:.1f} m from the Kings Theatre (it was 414.6 m)"


@pytest.mark.skipif(not POIS.is_file(), reason="the OSM extract has not been built")
def test_the_bethesda_subject_is_in_the_fountain_basin():
    """The basin is 29.26 m across, so the aim point has to be inside 14.63 m of its centre."""
    osm = _osm_by_name()
    cands = osm.get("bethesda fountain")
    assert cands, "OSM way 958635828 'Bethesda Fountain' is missing from the extract"
    got = {slug: (x, y) for slug, _n, x, y in _items()}
    x, y = got["bethesda_terrace_fountain"]
    d = min(math.hypot(px - x, py - y) for px, py in cands)
    assert d < 14.63, f"the subject stands {d:.1f} m from the fountain, outside its own basin"


# ------------------------------------------------------- a bridge subject stands on its bridge (J75)

#: Slug -> the fragment of ``street_name`` that names that bridge's own carriageway in
#: ``segments.parquet``. Written out rather than matched, for the reason the module docstring gives:
#: a fuzzy matcher in the audit that exists to catch fuzzy matching is how J57 nearly slipped
#: through. Only bridges whose deck carries a named roadway are here -- Hell Gate is a rail bridge
#: and the High Bridge an aqueduct, so neither has a carriageway to stand on and neither is claimed.
BRIDGE_CARRIAGEWAY = {
    "dumbo_washington_st_manhattan_bridge": "MANHATTAN BR",
    "landmark_manhattan_bridge": "MANHATTAN BR",
    "landmark_williamsburg_bridge": "WILLIAMSBURG BR",
    "landmark_brooklyn_bridge_from_dumbo": "BROOKLYN BR",
    "landmark_brooklyn_bridge_walkway": "BROOKLYN BR",
    "landmark_bronx_whitestone_bridge": "WHITESTONE",
    "landmark_george_washington_bridge": "GEORGE WASHINGTON",
    "landmark_kosciuszko_bridge": "KOSCIUSZKO",
    "landmark_queensboro_bridge": "QUEENSBORO",
    "landmark_throgs_neck_bridge": "THROGS NECK",
}

#: A bridge tower is a couple of lanes wide and the carriageway centreline runs between its legs,
#: so a correct coordinate lands within a few metres. The six that were already right measured
#: 0.9 to 6.5 m; the three that were wrong measured 24.2, 29.7 and 47.5 m. 15 m sits in the gap
#: and is a **choice**, not a tolerance anything derives.
BRIDGE_MAX_M = 15.0

SEGMENTS = PROCESSED / "roads" / "segments.parquet"


@pytest.mark.skipif(not SEGMENTS.is_file(), reason="the road network has not been built")
def test_a_subject_that_names_a_bridge_stands_on_that_bridges_own_carriageway():
    """The same defect as J57, found by a different measurement.

    Three subject coordinates named a bridge tower and stood off the bridge: the Manhattan
    Bridge's Brooklyn tower 29.7 m off its own carriageway, the Williamsburg's 24.2 m, the Throgs
    Neck's 47.5 m. Nothing caught them, because the item's recorded azimuth pointed at the wrong
    coordinate too -- to within 0.1 deg on all three -- so every check that compared the two agreed
    with itself. The road network is the independent source: a bridge tower stands on the bridge.
    """
    import geopandas as gpd
    from shapely.geometry import Point

    rd = gpd.read_parquet(SEGMENTS, columns=["street_name", "geometry"])
    names = rd["street_name"].astype(str).str.upper()
    subjects = {slug: (x, y) for slug, _n, x, y in _items()}

    off = []
    for slug, frag in BRIDGE_CARRIAGEWAY.items():
        if slug not in subjects:
            continue
        sel = rd[names.str.contains(frag, na=False)]
        assert len(sel), f"no segment carries {frag!r}; the audit lost its reach for {slug}"
        d = float(sel.geometry.distance(Point(*subjects[slug])).min())
        if d > BRIDGE_MAX_M:
            off.append((d, slug, frag))
    assert not off, "bridge subjects standing off their own carriageway:\n" + "\n".join(
        f"   {d:7.1f} m  {slug:44} ({frag})" for d, slug, frag in sorted(off, reverse=True))


@pytest.mark.skipif(not SEGMENTS.is_file(), reason="the road network has not been built")
def test_a_corrected_subject_says_what_it_was_and_why():
    """A coordinate that moved has to carry its own evidence, or the next reader cannot check it."""
    moved_the_azimuth_too = ("dumbo_washington_st_manhattan_bridge", "landmark_manhattan_bridge",
                             "landmark_williamsburg_bridge", "landmark_throgs_neck_bridge")
    for slug in moved_the_azimuth_too + ("landmark_soldiers_sailors_arch",):
        doc = json.loads((REFERENCE / slug / "meta.json").read_text())
        sub, vp = doc["subject"], doc["viewpoint"]
        assert sub.get("lat_was") is not None and sub.get("lon_was") is not None, \
            f"{slug}: the coordinate moved without recording what it was"
        assert "J75" in str(sub.get("source", "")), f"{slug}: the move carries no reason"
        if slug in moved_the_azimuth_too:
            assert vp.get("azimuth_deg_was") is not None, \
                f"{slug}: the subject moved and the azimuth derived from it did not"
        else:
            # The arch's recorded azimuth already agrees with the corrected subject to 1.8 deg, so
            # it is left alone -- and the reason has to be written down, or the next reader will
            # take the missing `azimuth_deg_was` for an oversight.
            assert "unchanged" in str(sub.get("source", "")), \
                f"{slug}: an azimuth left alone beside a moved subject, with no reason given"


#: Slug -> the landmark model that stands for the bridge that slug's subject names. Written out for
#: the reason the module docstring gives. Only bridges whose model actually carries tower geometry
#: are here: the Queensboro is a cantilever bridge whose model names no tower, and the Bronx
#: Whitestone, Kosciuszko and Throgs Neck have no hand-built model at all, so none of those four is
#: claimed by this test.
BRIDGE_TOWER_MODEL = {
    "dumbo_washington_st_manhattan_bridge": "b_manhattan_bridge",
    "landmark_manhattan_bridge": "b_manhattan_bridge",
    "landmark_williamsburg_bridge": "b_williamsburg_bridge",
    "landmark_brooklyn_bridge_from_dumbo": "b_brooklyn_bridge",
    "landmark_brooklyn_bridge_walkway": "b_brooklyn_bridge",
    "landmark_george_washington_bridge": "b_george_washington_bridge",
}

#: The two subjects that are **known** to stand off the tower they name, with the distance measured
#: at the time they were recorded, and the band this test holds them in. They are not corrected, for
#: the reason J75 gives about its own six: the only anchor for a suspension tower is the model built
#: to stand for it, and moving a reference onto a model is validating the render against itself.
#: They are pinned here instead, so that the fault stays visible, cannot silently get worse, and
#: cannot be silently repaired without this test and docs/DEVIATIONS.md J82 disagreeing.
KNOWN_OFF_THEIR_TOWER = {
    "landmark_brooklyn_bridge_from_dumbo": 105.2,
    "landmark_brooklyn_bridge_walkway": 103.6,
}

#: A suspension tower is a few tens of metres across and a correct coordinate lands on it. The four
#: that are right measure 1.2, 1.2, 3.7 and 9.7 m; the two that are not measure 103.6 and 105.2 m.
#: 30 m sits in that gap and is a **choice**, not a tolerance anything derives.
TOWER_MAX_M = 30.0

#: How far a pinned distance may drift before this test wants a human. A coordinate that has not
#: moved measures the same number every run; this band exists only so that rebuilding a bridge model
#: with slightly different tower geometry does not fail the suite on a metre.
TOWER_PIN_BAND_M = 5.0

LANDMARK_GLB = Path(__file__).resolve().parents[2] / "blender_out" / "landmarks"


def _tower_centres_tm(landmark_id: str) -> list[tuple[float, float]]:
    """NYC_TM centres of every mesh in ``<landmark_id>.glb`` whose node name says 'tower'.

    Reads the exported artefact rather than the build script, like ``tests/test_landmarks_c.py``.
    glTF is Y-up and the landmark frames are parallel to NYC_TM with no rotation to apply
    (``blender/landmarks/common.py``), so local x is east and local north is -z.
    """
    glb = LANDMARK_GLB / f"{landmark_id}.glb"
    cat = LANDMARK_GLB / "catalog" / f"{landmark_id}.json"
    if not glb.is_file() or not cat.is_file():
        return []
    raw = glb.read_bytes()
    if len(raw) < 12 or raw[:4] != b"glTF":
        return []
    off, chunks = 12, {}
    while off + 8 <= len(raw):
        length, kind = struct.unpack_from("<II", raw, off)
        chunks[kind] = raw[off + 8:off + 8 + length]
        off += 8 + length
    doc = json.loads(chunks[0x4E4F534A].decode("utf-8"))
    ox, oy = json.loads(cat.read_text())["origin_tm"][:2]
    out = []
    for node in doc.get("nodes", []):
        name = str(node.get("name", ""))
        if node.get("mesh") is None or "tower" not in name.lower() or "LOD1" in name:
            continue
        lo = [float("inf")] * 3
        hi = [float("-inf")] * 3
        for prim in doc["meshes"][node["mesh"]]["primitives"]:
            acc = doc["accessors"][prim["attributes"]["POSITION"]]
            if not acc.get("min") or not acc.get("max"):
                continue
            for k in range(3):
                lo[k] = min(lo[k], acc["min"][k])
                hi[k] = max(hi[k], acc["max"][k])
        if lo[0] > hi[0]:
            continue
        out.append((ox + (lo[0] + hi[0]) / 2.0, oy - (lo[2] + hi[2]) / 2.0))
    return out


@pytest.mark.skipif(not LANDMARK_GLB.is_dir(), reason="the landmark models have not been exported")
def test_a_subject_that_names_a_bridge_tower_stands_on_that_tower():
    """The carriageway test passes for a coordinate on the deck a hundred metres from the tower.

    ``test_a_subject_that_names_a_bridge_stands_on_that_bridges_own_carriageway`` asks whether the
    subject is on the bridge, which is the right question for a coordinate that fell into the river
    and the wrong one for a coordinate that fell onto the main span. Both Brooklyn Bridge subjects
    are on the carriageway to well within its 15 m and stand **over a hundred metres** from the
    tower they name, out where the model's fabric is the deck at 44 m rather than the tower at 85 m
    (docs/DEVIATIONS.md J82). This test asks the other question.

    It compares a reference coordinate with the model built to stand for it, so it can say the two
    disagree and it cannot say which is wrong -- that is the point, and it is why the two failures
    are pinned rather than corrected.
    """
    subjects = {slug: (x, y) for slug, _n, x, y in _items()}
    off, missing = [], []
    for slug, model in BRIDGE_TOWER_MODEL.items():
        if slug not in subjects:
            continue
        towers = _tower_centres_tm(model)
        if not towers:
            missing.append((slug, model))
            continue
        sx, sy = subjects[slug]
        d = min(math.hypot(sx - tx, sy - ty) for tx, ty in towers)
        pin = KNOWN_OFF_THEIR_TOWER.get(slug)
        if pin is not None:
            assert abs(d - pin) <= TOWER_PIN_BAND_M, (
                f"{slug}: recorded as standing {pin:.1f} m from its tower (J82) and now measures "
                f"{d:.1f} m. Either the coordinate moved or the model did; whichever it was, "
                f"docs/DEVIATIONS.md J82 and KNOWN_OFF_THEIR_TOWER have to say so.")
            continue
        if d > TOWER_MAX_M:
            off.append((d, slug, model))
    assert not missing, (
        "a bridge whose subject this test claims to check has no tower geometry to check it "
        "against:\n" + "\n".join(f"   {slug:44} ({model})" for slug, model in missing))
    assert not off, "bridge-tower subjects standing off the tower they name:\n" + "\n".join(
        f"   {d:7.1f} m  {slug:44} ({model})" for d, slug, model in sorted(off, reverse=True))


@pytest.mark.skipif(not LANDMARK_GLB.is_dir(), reason="the landmark models have not been exported")
def test_a_subject_pinned_off_its_tower_is_declared_rather_than_hidden():
    """A pinned fault that is not written down is a fault that has been forgotten."""
    deviations = (Path(__file__).resolve().parents[2] / "docs" / "DEVIATIONS.md").read_text()
    for slug in KNOWN_OFF_THEIR_TOWER:
        assert slug in deviations, f"{slug} is pinned as off its tower and DEVIATIONS.md never says so"
    assert "J82" in deviations, "the pin cites J82 and DEVIATIONS.md has no J82"


# ------------------------------------------------- a viewpoint that names a crossing stands at it (J85)

#: Slug -> the road-network intersection the item's viewpoint note names, as (street, cross street) fragments
#: that both have to appear in the node's ``names`` list.  Written out, not matched, for the reason the module
#: docstring gives.  Only items whose note names a crossing are here; a note that names a plaza, a park or a
#: bridge walkway has no node to stand at and is not claimed.
VIEWPOINT_NAMED_NODE = {
    "landmark_15_hudson_yards": ("10 AVE", "W 30 ST"),
}

#: A camera at a crossing stands on its sidewalk or in its carriageway, a few metres from the centreline node.
#: 15 m is the distance J75 uses for a subject on its own carriageway and is a **choice**, not a tolerance
#: anything derives; the one coordinate that was wrong measured 130.2 m.
VIEWPOINT_NODE_MAX_M = 15.0

#: Viewpoints that were moved (J85), and so have to carry what they were and why, like a moved subject.
MOVED_VIEWPOINTS = ("landmark_15_hudson_yards", "landmark_hudson_yards_vessel", "landmark_the_shed")

#: Viewpoints that **stood** inside the OTI footprint of a building the landmark model builds as a solid plinth,
#: with the distance measured when they were recorded (J85: 52.1 m and 8.3 m inside the Shops / 30 Hudson Yards
#: podium, BIN 1088961).  J85 published them unmoved on J82's rule -- the position along the open strip beside
#: the podium was a choice -- and named a real polygon as the candidate: the DoITT planimetric public-plaza
#: polygon of the Hudson Yards public square (feat_code 6000, 1,571 m2, source_id 0 -- the id the planimetric
#: datasets give every record of status 'New', so the polygon is named here by its area and centroid).  The
#: landmark-datum decision (J85, I11b third amendment) moved both onto that polygon's centroid, because the
#: centroid of a surveyed polygon is a measurement and the strip was not.  The old distance stays pinned against
#: ``lat_was``/``lon_was`` so the fault that was found cannot be quietly rewritten either way.
MOVED_OUT_OF_A_FOOTPRINT = {
    "landmark_hudson_yards_vessel": (1088961, 52.1),
    "landmark_the_shed": (1088961, 8.3),
}
FOOTPRINT_PIN_BAND_M = 2.0
PLAZA_FEAT_CODE = 6000
PLAZA_AREA_M2 = 1571.0
PLAZA_CENTROID_TM = (-4394.66, 5895.14)
#: The polygon is 1,571 m2 and its centroid is 10.5 m inside its own boundary; a coordinate rounded to six
#: decimals of a degree moves 0.05 m.  1 m is a **choice** that is far inside the first and far outside the second.
PLAZA_CENTROID_MAX_M = 1.0

NODES = PROCESSED / "roads" / "nodes.parquet"
FOOTPRINTS = PROCESSED / "buildings" / "footprints_raw.parquet"
PAVEMENT_T_5_5 = PROCESSED / "roads" / "pavement" / "t_-5_5.parquet"


def _viewpoints() -> dict[str, tuple[dict, float, float]]:
    got = {}
    for meta in sorted(REFERENCE.glob("*/meta.json")):
        doc = json.loads(meta.read_text())
        vp = doc.get("viewpoint") or {}
        if vp.get("lat") is None or vp.get("lon") is None:
            continue
        x, y = (float(v) for v in lonlat_to_tm(vp["lon"], vp["lat"]))
        got[doc["slug"]] = (vp, x, y)
    return got


@pytest.mark.skipif(not NODES.is_file(), reason="the road network has not been built")
def test_a_viewpoint_that_names_a_crossing_stands_at_that_crossings_node():
    """The same shape as J75, one step back: the camera, not the subject.

    ``landmark_15_hudson_yards`` said 'Tenth Avenue at West 30th Street' and stood 130.2 m from that
    crossing, inside the Eastern Rail Yard, where the heightmap read -0.90 m (docs/DEVIATIONS.md J85).
    Nothing caught it, because the recorded azimuth pointed at the subject from the wrong place to
    within 0.1 deg and every check that compared the two agreed with itself.  The road network is the
    independent source: a camera at a crossing stands at that crossing.
    """
    nodes = pd.read_parquet(NODES, columns=["node_id", "x", "y", "names"])
    vps = _viewpoints()
    off = []
    for slug, (street, cross) in VIEWPOINT_NAMED_NODE.items():
        if slug not in vps:
            continue
        names = nodes["names"].apply(lambda n: set(str(v) for v in (n if n is not None else [])))
        sel = nodes[names.apply(lambda s: street in s and cross in s)]
        assert len(sel), f"no node carries both {street!r} and {cross!r}; the audit lost its reach for {slug}"
        _vp, x, y = vps[slug]
        d = float(np.hypot(sel["x"].values - x, sel["y"].values - y).min())
        if d > VIEWPOINT_NODE_MAX_M:
            off.append((d, slug, f"{street} & {cross}"))
    assert not off, "viewpoints standing off the crossing their note names:\n" + "\n".join(
        f"   {d:7.1f} m  {slug:44} ({name})" for d, slug, name in sorted(off, reverse=True))


def test_a_corrected_viewpoint_says_what_it_was_and_why():
    """A moved camera carries its own evidence, exactly as a moved subject does (J75's convention)."""
    for slug in MOVED_VIEWPOINTS:
        vp = json.loads((REFERENCE / slug / "meta.json").read_text())["viewpoint"]
        assert vp.get("lat_was") is not None and vp.get("lon_was") is not None, \
            f"{slug}: the viewpoint moved without recording what it was"
        assert "J75" in str(vp.get("source", "")) and "J85" in str(vp.get("source", "")), \
            f"{slug}: the move carries no reason"
        assert vp.get("azimuth_deg_was") is not None and vp.get("azimuth_source"), \
            f"{slug}: the viewpoint moved and the azimuth derived from it did not say so"
        # the new azimuth is the bearing from the new viewpoint to the subject, to 0.1 deg
        doc = json.loads((REFERENCE / slug / "meta.json").read_text())
        vx, vy = (float(v) for v in lonlat_to_tm(vp["lon"], vp["lat"]))
        sx, sy = (float(v) for v in lonlat_to_tm(doc["subject"]["lon"], doc["subject"]["lat"]))
        bearing = math.degrees(math.atan2(sx - vx, sy - vy)) % 360.0
        assert abs((bearing - float(vp["azimuth_deg"]) + 180.0) % 360.0 - 180.0) <= 0.1, (bearing, vp["azimuth_deg"])


@pytest.mark.skipif(not (FOOTPRINTS.is_file() and PAVEMENT_T_5_5.is_file()),
                    reason="the footprints or the pavement tables have not been built")
def test_a_viewpoint_moved_out_of_a_footprint_stands_on_the_plaza_polygon_and_says_where_it_was():
    """The two Hudson Yards square viewpoints stand on the DoITT plaza polygon, outside the podium, and say so.

    This is the inverse of the test it replaces, which pinned them 52.1 m and 8.3 m *inside* BIN 1088961.
    Three things are held: the camera is inside the plaza polygon at its centroid and outside the podium
    footprint; the coordinate it replaced (``lat_was``/``lon_was``) still measures the pinned distance inside
    the footprint, so the record of the fault cannot drift; and the audit block says the move and its source.
    """
    import geopandas as gpd
    from shapely.geometry import Point

    fp = gpd.read_parquet(FOOTPRINTS, columns=["bin", "geometry"])
    pav = gpd.read_parquet(PAVEMENT_T_5_5, columns=["feat_code", "area_m2", "geometry"])
    plazas = pav[(pav["feat_code"] == PLAZA_FEAT_CODE) & ((pav["area_m2"] - PLAZA_AREA_M2).abs() < 5.0)]
    assert len(plazas) == 1, f"expected one {PLAZA_AREA_M2} m2 plaza polygon in t_-5_5, found {len(plazas)}"
    plaza = plazas.geometry.iloc[0]
    c = plaza.centroid
    assert math.hypot(c.x - PLAZA_CENTROID_TM[0], c.y - PLAZA_CENTROID_TM[1]) < 0.1, (c.x, c.y)
    vps = _viewpoints()
    deviations = (Path(__file__).resolve().parents[2] / "docs" / "DEVIATIONS.md").read_text()
    for slug, (bin_, pin) in MOVED_OUT_OF_A_FOOTPRINT.items():
        if slug not in vps:
            continue
        vp, x, y = vps[slug]
        geom = fp.loc[fp["bin"] == bin_, "geometry"]
        assert len(geom) == 1, f"BIN {bin_} is not in the footprints"
        g = geom.iloc[0]
        p = Point(x, y)
        assert not g.contains(p), f"{slug}: moved out of BIN {bin_} (J85) and stands inside it again"
        assert plaza.contains(p), f"{slug}: stands outside the plaza polygon it was moved onto"
        assert math.hypot(x - c.x, y - c.y) <= PLAZA_CENTROID_MAX_M, \
            f"{slug}: {math.hypot(x - c.x, y - c.y):.2f} m from the plaza centroid it is recorded at"
        wx, wy = (float(v) for v in lonlat_to_tm(vp["lon_was"], vp["lat_was"]))
        w = Point(wx, wy)
        assert g.contains(w), f"{slug}: lat_was/lon_was no longer stands inside BIN {bin_}; the record of the fault moved"
        d = float(g.boundary.distance(w))
        assert abs(d - pin) <= FOOTPRINT_PIN_BAND_M, f"{slug}: was pinned {pin} m inside, lat_was/lon_was measures {d:.1f} m"
        audit = vp.get("position_audit", {})
        assert audit.get("moved") is True and audit.get("moved_because"), f"{slug}: moved and its meta.json does not say so"
        assert audit.get("was_inside_footprint", {}).get("bin") == bin_ and \
            abs(float(audit["was_inside_footprint"]["distance_inside_m"]) - pin) <= FOOTPRINT_PIN_BAND_M, \
            f"{slug}: the audit lost the distance it was found at"
        on = audit.get("on_polygon", {})
        assert on.get("feat_code") == PLAZA_FEAT_CODE and abs(float(on.get("area_m2", 0.0)) - PLAZA_AREA_M2) < 5.0, \
            f"{slug}: the audit does not name the plaza polygon"
        assert slug in deviations and "J85" in deviations
