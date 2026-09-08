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
from pathlib import Path

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
