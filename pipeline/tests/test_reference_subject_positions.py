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
