"""Fetch openly licensed reference photographs from Wikimedia Commons.

    python -m nycsim_pipeline.reference.fetch_photos [--only SLUG|GROUP ...] [--force]
                                                     [--max-width 1920] [--out DIR] [--list]
                                                     [--index-only]

For every item in ``CATALOGUE`` (the mandated verification viewpoints, five drive-through areas,
every landmark in docs/LANDMARKS scope and a set of generic streetscape/vehicle references) the
script

1. collects candidate files with the Commons search API (``list=search``, relevance and
   newest-first) and, where the item has a fixed photographer position, the geosearch API
   (``list=geosearch`` on namespace 6, which indexes the *camera* position of a file);
2. fetches ``prop=imageinfo`` (url, size, mime, extmetadata) in batches of 50;
3. keeps only JPEGs under CC0 / CC BY / CC BY-SA / public domain, rejects non-photographs
   (maps, drawings, postcards, renders), rejects night shots for daylight items (and vice
   versa), rejects anything older than the item's ``min_year`` and prefers >= 2015;
4. downloads the best-scoring candidates at <= ``--max-width`` px (server-side thumbnail at the
   nearest standard Commons width bucket, or the original,
   verified and if necessary resized locally with Pillow), checks mean luminance so a
   "daylight" item really is daylight, and writes ``<slug>/<n>.jpg``;
5. writes ``<slug>/meta.json`` (title, page URL, file URL, author, licence short name + URL,
   date taken, camera GPS, sha256, and the estimated WGS84 viewpoint + azimuth with a
   sentence explaining the estimate) and regenerates ``INDEX.md`` / ``LICENSES.md``.

Re-runnable: a slug whose ``meta.json`` is complete and whose files are present is skipped.
API etiquette: descriptive User-Agent with a contact URL, <= 2 requests/s across all hosts,
``maxlag=5``, exponential back-off on 429/5xx honouring ``Retry-After``.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import io
import json
import logging
import math
import os
import re
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import requests
from PIL import Image, ImageOps, ImageStat

from ..paths import VERIFICATION

log = logging.getLogger("nycsim.reference.fetch_photos")

API_URL = "https://commons.wikimedia.org/w/api.php"
UPLOAD_HOST = "https://upload.wikimedia.org/wikipedia/commons"
# Contact per https://meta.wikimedia.org/wiki/User-Agent_policy. Deliberately a project URL,
# never a personal e-mail address (override with NYCSIM_CONTACT).
CONTACT = os.environ.get("NYCSIM_CONTACT", "https://github.com/erithy25/Map-New-York")
USER_AGENT = f"NYCSim-reference-fetch/1.0 ({CONTACT}) python-requests/{requests.__version__}"
CA_BUNDLE = os.environ.get("REQUESTS_CA_BUNDLE") or os.environ.get("SSL_CERT_FILE") or True
MIN_INTERVAL_S = float(os.environ.get("NYCSIM_MIN_INTERVAL", "0.5"))  # <= 2 requests/s, API and downloads combined
DEFAULT_MAX_WIDTH = 1920
# Standard thumbnail widths served by upload.wikimedia.org; any other width returns HTTP 400.
THUMB_BUCKETS = (250, 500, 960, 1280, 1920)
MIN_USABLE_WIDTH = 900  # a reference photo narrower than this is not worth keeping
MAX_DOWNLOAD_BYTES = 80 << 20
MAX_INFO_TITLES = 100  # imageinfo lookups per item (2 batches of 50)
SCHEMA_VERSION = 1
OUT_ROOT = VERIFICATION / "reference"

EXTMETA_FIELDS = (
    "LicenseShortName", "LicenseUrl", "License", "Artist", "Credit", "DateTimeOriginal", "DateTime",
    "GPSLatitude", "GPSLongitude", "ImageDescription", "ObjectName", "Categories", "Assessments",
    "Restrictions",
)

# ----------------------------------------------------------------------------------------------
# Catalogue
# ----------------------------------------------------------------------------------------------

GROUPS = ("viewpoint", "drive_through", "landmark", "streetscape", "vehicle")

# Manhattan street grid: avenues run 29 deg (uptown) / 209 deg (downtown), streets 119 / 299.
UPTOWN, DOWNTOWN, CROSSTOWN_E, CROSSTOWN_W = 29.0, 209.0, 119.0, 299.0


@dataclass(frozen=True)
class Item:
    slug: str
    name: str
    group: str
    queries: tuple[str, ...]
    # Each inner tuple is a group of alternatives; a candidate must match >= 1 term of every group
    # (matched against title + description + categories, case-insensitive, word-bounded).
    keywords: tuple[tuple[str, ...], ...]
    viewpoint: tuple[float, float]  # WGS84 lat, lon of the standard photographer position
    viewpoint_note: str  # one sentence: where the photographer stands
    subject: tuple[float, float] | None = None  # WGS84 lat, lon of what the camera points at
    subject_name: str = ""
    azimuth: float | None = None  # explicit compass azimuth when the view is "along a street"
    geosearch_radius_m: int = 0  # 0 = no geosearch
    want: int = 3
    night: bool = False
    interior: bool = False
    representative: bool = False  # generic subject: viewpoint is a representative block only
    exclude: tuple[str, ...] = ()
    allow: tuple[str, ...] = ()  # INDOOR_WORDS this item is allowed to match (e.g. a rail viaduct street)
    min_year: int = 2010
    gps_subject_max_m: float = 2500.0  # camera GPS farther than this from the subject is distrusted
    min_luma: float | None = None
    max_luma: float | None = None

    def __post_init__(self) -> None:
        if self.group not in GROUPS:
            raise ValueError(f"{self.slug}: unknown group {self.group}")
        if self.subject is None and self.azimuth is None:
            raise ValueError(f"{self.slug}: needs a subject or an explicit azimuth")
        if not (40.45 <= self.viewpoint[0] <= 40.95 and -74.30 <= self.viewpoint[1] <= -73.65):
            raise ValueError(f"{self.slug}: viewpoint outside NYC bbox")
        if self.subject is not None and not (40.45 <= self.subject[0] <= 40.95 and -74.30 <= self.subject[1] <= -73.65):
            raise ValueError(f"{self.slug}: subject outside NYC bbox")
        if not 1 <= self.want <= 4:
            raise ValueError(f"{self.slug}: want must be 1..4")
        if not self.keywords or not self.queries or not self.viewpoint_note:
            raise ValueError(f"{self.slug}: queries, keywords and viewpoint_note are required")

    @property
    def default_azimuth(self) -> float:
        if self.azimuth is not None:
            return self.azimuth
        assert self.subject is not None
        return bearing_deg(self.viewpoint, self.subject)

    def luma_bounds(self) -> tuple[float, float]:
        if self.night:
            return (self.min_luma if self.min_luma is not None else 8.0, self.max_luma if self.max_luma is not None else 105.0)
        lo = self.min_luma if self.min_luma is not None else (30.0 if self.interior else 55.0)
        return (lo, self.max_luma if self.max_luma is not None else 250.0)


def _it(slug: str, name: str, group: str, queries: list[str], keywords: list[list[str]], vp: tuple[float, float], note: str, **kw: Any) -> Item:
    return Item(slug, name, group, tuple(queries), tuple(tuple(k) for k in keywords), vp, note, **kw)


def offset_point(origin: tuple[float, float], bearing: float, dist_m: float) -> tuple[float, float]:
    """WGS84 point ``dist_m`` metres from ``origin`` on compass ``bearing`` (0 = north).

    Equirectangular step on the WGS84 mean-radius sphere. Over the <= 1.5 km offsets used in the
    catalogue the deviation from the exact geodesic is under 0.2 m -- three orders of magnitude
    below the uncertainty of the viewpoint estimate itself.
    """
    r = 6371008.8
    lat = origin[0] + math.degrees(dist_m * math.cos(math.radians(bearing)) / r)
    lon = origin[1] + math.degrees(dist_m * math.sin(math.radians(bearing)) / (r * math.cos(math.radians(origin[0]))))
    return (round(lat, 6), round(lon, 6))


def _lmk(slug: str, name: str, queries: list[str], keywords: list[list[str]], subject: tuple[float, float],
         side: float, dist_m: float, note: str, **kw: Any) -> Item:
    """Landmark item whose photographer position is ``dist_m`` from ``subject`` on bearing ``side``.

    ``side`` is the compass bearing *from the subject to the camera* (which side of the building
    the photographer stands on); the item's azimuth is then the reverse bearing, computed by
    ``Item.default_azimuth``. ``note`` must describe that same position in words.
    """
    return _it(slug, name, "landmark", queries, keywords, offset_point(subject, side, dist_m), note,
               subject=subject, subject_name=kw.pop("subject_name", name), **kw)


NYC_WORDS = ["new york", "manhattan", "brooklyn", "queens", "bronx", "staten island", "nyc"]
NIGHT_WORDS = ["night", "nighttime", "at night", "dusk", "evening", "sunset", "twilight", "blue hour", "after dark",
               "illuminated", "light show", "fireworks", "new year's eve", "christmas lights", "nightscape"]
DAWN_WORDS = ["sunrise", "dawn"]
NOT_PHOTO_WORDS = ["map", "painting", "drawing", "engraving", "lithograph", "postcard", "poster", "logo", "diagram",
                   "floor plan", "site plan", "sketch", "illustration", "3d model", "scale model", "model of", "rendering",
                   "render", "stereograph", "stereoscopic", "black and white", "black-and-white", "monochrome", "b&w",
                   "sepia", "photochrom", "lego", "miniature", "screenshot", "video game", "cartoon", "clip art",
                   "coat of arms", "flag of", "infrared", "hdr composite", "collage", "montage", "cgi", "artist's impression"]
AERIAL_WORDS = ["aerial", "from above", "helicopter", "drone", "from the air", "bird's-eye", "birds-eye"]
# Rejected for every item that is not explicitly an interior: transit interiors and building
# insides look nothing like the outdoor view a render is compared against, and they share
# categories ("Times Square", "Grand Central") with the views we do want.
INDOOR_WORDS = ["interior", "inside", "subway entrance", "subway station", "subway platform", "station platform",
                "platform", "turnstile", "mezzanine", "token booth", "escalator", "waiting room", "concourse",
                "bmt", "irt", "ind", "staircase", "stairwell", "lobby", "hallway", "corridor", "elevator"]
# Not rejected outright (a street scene has people in it) but scored down: the subject of these
# files is a person, not the place.
PEOPLE_WORDS = ["tourist", "tourists", "selfie", "portrait", "cosplay", "costumed", "busker", "street performer",
                "naked cowboy", "wedding", "proposal", "protest", "rally", "demonstration", "parade", "marathon",
                "santacon", "halloween parade"]

ONE_WTC = (40.71274, -74.01339)
EMPIRE_STATE = (40.74844, -73.98566)

CATALOGUE: list[Item] = [
    # ---------------------------------------------------------------- 1-7 mandated viewpoints
    _it("promenade_lower_manhattan", "Brooklyn Heights Promenade looking at Lower Manhattan", "viewpoint",
        ['"Brooklyn Heights Promenade" Lower Manhattan skyline', 'Lower Manhattan skyline from Brooklyn Heights'],
        [["promenade", "brooklyn heights"], ["manhattan", "skyline", "financial district"]],
        (40.6960, -73.9975), "Brooklyn Heights Promenade at the Montague Street entrance, standing at the railing",
        subject=ONE_WTC, subject_name="One World Trade Center", geosearch_radius_m=300, want=4, min_year=2014,
        gps_subject_max_m=3500, exclude=AERIAL_WORDS),
    _it("top_of_the_rock_south", "Top of the Rock looking south (Empire State Building centred)", "viewpoint",
        ['"Top of the Rock" Empire State Building view south', 'view from Top of the Rock Empire State Building Midtown'],
        [["top of the rock", "rockefeller"], ["empire state"]],
        (40.7593, -73.9789), "Top of the Rock observation deck (70th floor of 30 Rockefeller Plaza), south parapet",
        subject=EMPIRE_STATE, subject_name="Empire State Building", geosearch_radius_m=80, want=4, min_year=2014,
        exclude=["from the empire state", "from empire state"]),
    _it("times_square_duffy_south_day", "Times Square centre: Duffy Square looking south, daylight", "viewpoint",
        ['"Duffy Square" Times Square', '"TKTS" Times Square looking south'],
        [["times square", "duffy"]],
        (40.7592, -73.9847), "top of the TKTS red steps at Duffy Square (47th Street), looking down the bowtie toward One Times Square",
        subject=(40.7562, -73.9864), subject_name="One Times Square", geosearch_radius_m=120, want=4, min_year=2016,
        min_luma=80, exclude=AERIAL_WORDS + ["new year", "ball drop", "protest", "parade"]),
    _it("times_square_duffy_south_night", "Times Square centre: Duffy Square looking south, night", "viewpoint",
        ['"Times Square" night Duffy Square', '"Times Square" night TKTS red steps'],
        [["times square", "duffy"], NIGHT_WORDS],
        (40.7592, -73.9847), "top of the TKTS red steps at Duffy Square (47th Street), looking down the bowtie toward One Times Square",
        subject=(40.7562, -73.9864), subject_name="One Times Square", geosearch_radius_m=120, want=4, night=True, min_year=2016,
        exclude=AERIAL_WORDS + ["new year", "ball drop", "protest", "parade"]),
    _it("fifth_ave_42nd_north", "Fifth Avenue at 42nd Street (NYPL), street view looking north", "viewpoint",
        ['"Fifth Avenue" "42nd Street" looking north', 'New York Public Library Fifth Avenue street traffic'],
        [["fifth avenue", "5th avenue"], ["42nd", "41st", "40th", "43rd", "public library", "nypl", "bryant park"]],
        (40.7526, -73.9814), "Fifth Avenue west sidewalk in front of the New York Public Library (between 40th and 42nd), looking uptown",
        azimuth=UPTOWN, geosearch_radius_m=150, exclude=AERIAL_WORDS + ["looking south", "south from", "interior", "reading room", "parade"]),
    _it("fifth_ave_42nd_south", "Fifth Avenue at 42nd Street (NYPL), street view looking south", "viewpoint",
        ['"Fifth Avenue" "42nd Street" looking south', '"Fifth Avenue" 42nd Street Manhattan street'],
        [["fifth avenue", "5th avenue"], ["42nd", "41st", "40th", "43rd", "public library", "nypl", "bryant park"]],
        (40.7538, -73.9806), "Fifth Avenue at 43rd Street, looking downtown past the New York Public Library",
        azimuth=DOWNTOWN, geosearch_radius_m=150, exclude=AERIAL_WORDS + ["looking north", "north from", "interior", "reading room", "parade"]),
    _it("bethesda_terrace_fountain", "Bethesda Terrace and Fountain", "viewpoint",
        ['"Bethesda Terrace" fountain Central Park', '"Bethesda Fountain" Central Park Angel of the Waters'],
        [["bethesda"]],
        (40.7735, -73.9711), "upper level of Bethesda Terrace (72nd Street transverse), looking north over the fountain to the Lake",
        subject=(40.7741, -73.9709), subject_name="Bethesda Fountain (Angel of the Waters)", geosearch_radius_m=120, want=4,
        gps_subject_max_m=400, exclude=AERIAL_WORDS + ["arcade ceiling", "minton tile"]),
    _it("staten_island_ferry_lower_manhattan", "Staten Island Ferry deck view of Lower Manhattan", "viewpoint",
        ['"Staten Island Ferry" Lower Manhattan skyline', 'Lower Manhattan from the Staten Island Ferry'],
        [["ferry"], ["manhattan", "skyline", "financial district", "battery"]],
        (40.6910, -74.0215), "open bow deck of a Manhattan-bound Staten Island Ferry, about 1 nautical mile south of Whitehall Terminal",
        subject=ONE_WTC, subject_name="One World Trade Center", geosearch_radius_m=900, want=4, min_year=2014,
        gps_subject_max_m=6000, exclude=AERIAL_WORDS + ["interior", "inside the ferry", "terminal"]),
    _it("dumbo_washington_st_manhattan_bridge", "Washington Street in DUMBO with the Manhattan Bridge", "viewpoint",
        ['"Washington Street" DUMBO "Manhattan Bridge"', 'DUMBO Manhattan Bridge Washington Street Empire State Building framed'],
        [["washington street", "dumbo"], ["manhattan bridge"]],
        (40.7030, -73.9892), "Washington Street between Front and Water Streets, DUMBO, centred on the roadway",
        subject=(40.7045, -73.9897), subject_name="Manhattan Bridge Brooklyn tower", geosearch_radius_m=120, want=4,
        gps_subject_max_m=600, exclude=AERIAL_WORDS),
    # ---------------------------------------------------------------- 8 drive-through areas
    _it("drive_midtown_sixth_ave_45th", "Midtown drive-through: Sixth Avenue at 45th Street", "drive_through",
        ['"Sixth Avenue" "45th Street" Manhattan', '"Avenue of the Americas" Midtown street 45th 46th 47th'],
        [["sixth avenue", "6th avenue", "avenue of the americas"]],
        (40.7566, -73.9822), "Sixth Avenue at West 45th Street, roadway centre, looking uptown",
        azimuth=UPTOWN, geosearch_radius_m=150, exclude=AERIAL_WORDS + ["parade", "protest"]),
    _it("drive_lower_manhattan_broadway_wall_st", "Lower Manhattan drive-through: Broadway at Wall Street", "drive_through",
        ['"Broadway" "Wall Street" Trinity Church street', 'Wall Street Broadway intersection Lower Manhattan'],
        [["wall street", "broadway"]],
        (40.7079, -74.0110), "Broadway at Wall Street, roadway centre, looking downtown toward Bowling Green",
        azimuth=200.0, geosearch_radius_m=120, exclude=AERIAL_WORDS + ["parade", "protest", "occupy", "1920", "1929", "interior"]),
    _it("drive_lower_manhattan_stone_st", "Lower Manhattan drive-through: Stone Street", "drive_through",
        ['"Stone Street" Manhattan', '"Stone Street" Financial District restaurants'],
        [["stone street"]],
        (40.7040, -74.0105), "west end of the Stone Street pedestrian block at William Street, looking east-north-east",
        azimuth=60.0, geosearch_radius_m=120, exclude=["night", "interior", "inside"]),
    _it("drive_brooklyn_park_slope_7th_ave", "Brooklyn brownstone block: Park Slope, Seventh Avenue / Garfield Place", "drive_through",
        ['"Seventh Avenue" "Park Slope"', '"Garfield Place" Brooklyn', '"Park Slope" brownstones street'],
        [["park slope", "garfield place", "seventh avenue"]],
        (40.6725, -73.9782), "Seventh Avenue at Garfield Place, Park Slope, roadway centre, looking north-east toward Flatbush Avenue",
        azimuth=30.0, geosearch_radius_m=250, exclude=AERIAL_WORDS + ["night", "interior", "inside", "prospect park"]),
    _it("drive_brooklyn_bed_stuy_stuyvesant_ave", "Brooklyn brownstone block: Bed-Stuy, Stuyvesant Avenue", "drive_through",
        ['"Stuyvesant Avenue" Brooklyn', '"Bedford-Stuyvesant" brownstones street', '"Stuyvesant Heights" brownstones'],
        [["stuyvesant", "bedford"]],
        (40.6817, -73.9330), "Stuyvesant Avenue at Decatur Street, Stuyvesant Heights, roadway centre, looking north",
        azimuth=13.0, geosearch_radius_m=300, exclude=AERIAL_WORDS + ["night", "interior", "inside", "peter stuyvesant", "stuyvesant town", "stuyvesant high"]),
    _it("drive_queens_forest_hills", "Queens residential block: Forest Hills Gardens", "drive_through",
        ['"Forest Hills Gardens" houses', '"Forest Hills" Queens street houses Tudor'],
        [["forest hills"]],
        (40.7196, -73.8447), "Greenway Terrace at Station Square, Forest Hills Gardens, looking south-east",
        azimuth=140.0, geosearch_radius_m=400, exclude=AERIAL_WORDS + ["night", "interior", "inside", "stadium", "tennis", "subway", "station platform"]),
    _it("drive_queens_jackson_heights", "Queens residential block: Jackson Heights side street with two-family homes", "drive_through",
        ['"Jackson Heights" Queens houses residential street', '"Jackson Heights" two-family houses'],
        [["jackson heights"]],
        (40.7520, -73.8830), "84th Street between 35th and 37th Avenues, Jackson Heights, looking south",
        azimuth=165.0, geosearch_radius_m=500, exclude=AERIAL_WORDS + ["night", "interior", "inside", "station", "train", "subway", "roosevelt avenue", "parade"]),
    _it("drive_queens_bayside", "Queens residential block: Bayside", "drive_through",
        ['Bayside Queens houses residential street', '"Bayside, Queens" house'],
        [["bayside"]],
        (40.7630, -73.7720), "215th Street near 42nd Avenue, Bayside, looking north",
        azimuth=0.0, geosearch_radius_m=800, exclude=AERIAL_WORDS + ["night", "interior", "inside", "station", "train", "marina", "bay terrace", "fort totten", "wisconsin", "california"]),
    _it("drive_bronx_grand_concourse", "Bronx drive-through: Grand Concourse Art Deco apartments", "drive_through",
        ['"Grand Concourse" Art Deco apartment building', '"Grand Concourse" Bronx street view'],
        [["grand concourse"]],
        (40.8320, -73.9186), "Grand Concourse at East 165th Street, main roadway, looking north toward the 167th Street Art Deco blocks",
        azimuth=25.0, geosearch_radius_m=500, exclude=AERIAL_WORDS + ["night", "interior", "inside", "subway", "station platform", "1930", "1940"]),
    _it("drive_bronx_arthur_ave", "Bronx drive-through: Arthur Avenue (Belmont)", "drive_through",
        ['"Arthur Avenue" Bronx', '"Arthur Avenue" Belmont Little Italy Bronx street'],
        [["arthur avenue", "belmont"]],
        (40.8551, -73.8878), "Arthur Avenue at East 187th Street, roadway centre, looking south",
        azimuth=190.0, geosearch_radius_m=250, exclude=["night", "interior", "inside", "belmont park", "belmont stakes", "belmont, ma", "belmont shore"]),
    # ---------------------------------------------------------------- 9 landmarks
    _it("landmark_empire_state_building", "Empire State Building", "landmark",
        ['"Empire State Building" from Fifth Avenue street', '"Empire State Building" 34th Street exterior'],
        [["empire state"]],
        (40.7460, -73.9876), "Fifth Avenue at 30th Street, east sidewalk, looking uptown at the full height of the tower",
        subject=EMPIRE_STATE, subject_name="Empire State Building", geosearch_radius_m=250, gps_subject_max_m=3000,
        exclude=AERIAL_WORDS + ["top of the rock", "observation deck", "lobby", "interior", "view from the empire", "from the empire state"]),
    _it("landmark_chrysler_building", "Chrysler Building", "landmark",
        ['"Chrysler Building" Lexington Avenue', '"Chrysler Building" exterior street level 42nd Street'],
        [["chrysler"]],
        (40.7500, -73.9767), "Lexington Avenue at East 40th Street, west sidewalk, looking uptown at the crown",
        subject=(40.7516, -73.9755), subject_name="Chrysler Building", geosearch_radius_m=250,
        exclude=AERIAL_WORDS + ["lobby", "interior", "from the empire", "top of the rock", "observation deck", "car", "automobile"]),
    _it("landmark_one_world_trade_center", "One World Trade Center", "landmark",
        ['"One World Trade Center" from the memorial plaza', '"One World Trade Center" street level exterior'],
        [["one world trade", "1 world trade", "freedom tower", "one wtc", "1 wtc"]],
        (40.7104, -74.0121), "south-east corner of the 9/11 Memorial plaza (Greenwich and Liberty Streets), looking north-north-west",
        subject=ONE_WTC, subject_name="One World Trade Center", geosearch_radius_m=300, gps_subject_max_m=3000, min_year=2014,
        exclude=AERIAL_WORDS + ["observatory", "interior", "under construction", "construction", "tribute in light"]),
    _it("landmark_oculus", "World Trade Center Transportation Hub (Oculus)", "landmark",
        ['"Oculus" World Trade Center Transportation Hub exterior', 'World Trade Center Transportation Hub Oculus Calatrava'],
        [["oculus", "transportation hub"]],
        (40.7113, -74.0100), "Church Street at Dey/Fulton Street, east sidewalk, looking west across the plaza",
        subject=(40.7115, -74.0112), subject_name="the Oculus", geosearch_radius_m=200, min_year=2016,
        exclude=AERIAL_WORDS + ["construction", "rendering"]),
    _it("landmark_911_memorial_pools", "National September 11 Memorial pools", "landmark",
        ['"9/11 Memorial" reflecting pool', 'National September 11 Memorial pool waterfall names'],
        [["9/11 memorial", "september 11 memorial", "memorial pool", "reflecting pool", "national september 11", "9-11 memorial"]],
        (40.7112, -74.0122), "memorial plaza between the two pools on the Greenwich Street side, looking north-west across the North Pool",
        subject=(40.7118, -74.0135), subject_name="the North Pool", geosearch_radius_m=200, gps_subject_max_m=500, min_year=2012,
        exclude=AERIAL_WORDS + ["museum interior", "inside the museum", "tribute in light", "night", "survivor tree only"]),
    _it("landmark_statue_of_liberty", "Statue of Liberty", "landmark",
        ['"Statue of Liberty" Liberty Island', '"Statue of Liberty" from the ferry New York Harbor'],
        [["statue of liberty", "liberty enlightening"]],
        (40.6884, -74.0434), "flagpole plaza on Liberty Island south-east of the pedestal, looking north-west at the statue",
        subject=(40.68925, -74.0445), subject_name="Statue of Liberty", geosearch_radius_m=400, gps_subject_max_m=4000,
        exclude=AERIAL_WORDS + ["replica", "las vegas", "paris", "tokyo", "odaiba", "crown interior", "inside the", "museum", "torch closeup", "colmar", "bordeaux"]),
    _it("landmark_brooklyn_bridge_from_dumbo", "Brooklyn Bridge seen from DUMBO / Brooklyn Bridge Park", "landmark",
        ['"Brooklyn Bridge" from Brooklyn Bridge Park', '"Brooklyn Bridge" DUMBO Pebble Beach Main Street'],
        [["brooklyn bridge"]],
        (40.7040, -73.9920), "Pebble Beach at Main Street Park (Brooklyn Bridge Park), water's edge, looking west at the Brooklyn tower",
        subject=(40.7048, -73.9952), subject_name="Brooklyn Bridge Brooklyn tower", geosearch_radius_m=300, gps_subject_max_m=1500,
        exclude=AERIAL_WORDS + ["walkway", "promenade", "pedestrian path", "night", "on the bridge", "1883", "construction"]),
    _it("landmark_brooklyn_bridge_walkway", "Brooklyn Bridge from the pedestrian walkway", "landmark",
        ['"Brooklyn Bridge" walkway pedestrian promenade', '"Brooklyn Bridge" promenade cables tower boardwalk'],
        [["brooklyn bridge"], ["walkway", "promenade", "pedestrian", "on the bridge", "cables", "tower", "boardwalk"]],
        (40.7060, -73.9968), "centre of the elevated pedestrian promenade between the Brooklyn tower and mid-span, looking toward the Manhattan tower",
        subject=(40.7080, -73.9991), subject_name="Brooklyn Bridge Manhattan tower", geosearch_radius_m=200, gps_subject_max_m=900,
        exclude=AERIAL_WORDS + ["night", "from brooklyn bridge park", "from dumbo", "from the water", "ferry", "1883", "construction"]),
    _it("landmark_flatiron_building", "Flatiron Building", "landmark",
        ['"Flatiron Building" Fifth Avenue Broadway', '"Flatiron Building" Madison Square 23rd Street'],
        [["flatiron"]],
        (40.7425, -73.9887), "Fifth Avenue at 24th Street (Worth Monument traffic island), looking downtown at the prow",
        subject=(40.74106, -73.98964), subject_name="Flatiron Building", geosearch_radius_m=250,
        exclude=AERIAL_WORDS + ["night", "scaffold", "restoration", "1903", "1905", "toronto", "atlanta", "san francisco"]),
    _it("landmark_grand_central_facade", "Grand Central Terminal facade", "landmark",
        ['"Grand Central Terminal" facade 42nd Street', '"Grand Central Terminal" exterior Park Avenue Viaduct clock'],
        [["grand central"]],
        (40.7514, -73.9779), "Pershing Square plaza on Park Avenue at East 41st Street, looking north at the 42nd Street facade",
        subject=(40.7523, -73.9772), subject_name="Grand Central Terminal 42nd Street facade", geosearch_radius_m=200,
        exclude=AERIAL_WORDS + ["concourse", "interior", "inside", "ceiling", "platform", "dining", "oyster bar", "apple store", "night", "whispering", "track"]),
    _it("landmark_grand_central_concourse", "Grand Central Terminal Main Concourse", "landmark",
        ['"Grand Central Terminal" Main Concourse', '"Grand Central" concourse interior clock ceiling'],
        [["grand central"], ["concourse", "interior", "inside", "ceiling", "clock"]],
        (40.7528, -73.9776), "west balcony of the Main Concourse, looking east across the concourse to the east balcony and the Apple Store stair",
        azimuth=CROSSTOWN_E, interior=True, geosearch_radius_m=150,
        exclude=["facade", "exterior", "platform", "dining concourse", "oyster bar", "track", "42nd street from"]),
    _it("landmark_rockefeller_center", "Rockefeller Center (30 Rockefeller Plaza)", "landmark",
        ['"Rockefeller Center" 30 Rockefeller Plaza from Fifth Avenue Channel Gardens', '"30 Rockefeller Plaza" Comcast Building exterior'],
        [["rockefeller"]],
        (40.7588, -73.9776), "Fifth Avenue at the Channel Gardens (between 49th and 50th Streets), looking west up the axis to 30 Rockefeller Plaza",
        subject=(40.7593, -73.9789), subject_name="30 Rockefeller Plaza", geosearch_radius_m=200,
        exclude=AERIAL_WORDS + ["christmas", "tree lighting", "night", "top of the rock", "view from", "interior", "lobby", "rainbow room", "studio"]),
    _it("landmark_st_patricks_cathedral", "St. Patrick's Cathedral", "landmark",
        ["\"St. Patrick's Cathedral\" Fifth Avenue exterior", "\"Saint Patrick's Cathedral\" Manhattan facade"],
        [["patrick"], ["new york", "manhattan", "fifth avenue", "5th avenue", "midtown"]],
        (40.7590, -73.9779), "Rockefeller Plaza at Fifth Avenue (by the Atlas statue), looking east at the west front",
        subject=(40.7585, -73.9762), subject_name="St. Patrick's Cathedral", geosearch_radius_m=200,
        exclude=AERIAL_WORDS + ["interior", "nave", "altar", "inside", "organ", "dublin", "armagh", "melbourne", "night", "scaffold"]),
    _it("landmark_one_vanderbilt", "One Vanderbilt", "landmark",
        ['"One Vanderbilt" 42nd Street skyscraper', '"One Vanderbilt" Grand Central exterior'],
        [["one vanderbilt", "1 vanderbilt"]],
        (40.7514, -73.9779), "Pershing Square plaza on Park Avenue at East 41st Street, looking north-north-west past Grand Central",
        subject=(40.7529, -73.9786), subject_name="One Vanderbilt", geosearch_radius_m=250, min_year=2020,
        exclude=AERIAL_WORDS + ["summit", "interior", "construction", "rendering", "night"]),
    _it("landmark_hudson_yards_vessel", "Hudson Yards and the Vessel", "landmark",
        ['"Vessel" Hudson Yards public square', 'Hudson Yards Vessel 30 Hudson Yards exterior'],
        [["vessel", "hudson yards"]],
        (40.7535, -74.0010), "east side of the Hudson Yards public square, looking west at the Vessel with 30/35 Hudson Yards behind",
        subject=(40.7538, -74.0022), subject_name="the Vessel", geosearch_radius_m=250, min_year=2019,
        exclude=AERIAL_WORDS + ["interior", "inside the vessel", "edge observation", "night", "construction", "rendering"]),
    _it("landmark_high_line", "High Line", "landmark",
        ['"High Line" park Chelsea walkway planting', '"High Line" New York elevated park'],
        [["high line", "highline"]],
        (40.7461, -74.0060), "on the High Line at West 20th Street (Chelsea Grasslands), centre of the path, looking north",
        azimuth=UPTOWN, geosearch_radius_m=400, min_year=2012,
        exclude=AERIAL_WORDS + ["night", "abandoned", "before", "construction", "paris", "london", "coulée", "rendering", "seoul", "rotterdam"]),
    _it("landmark_central_park_bow_bridge", "Central Park: Bow Bridge", "landmark",
        ['"Bow Bridge" Central Park', '"Bow Bridge" Central Park Lake San Remo'],
        [["bow bridge"]],
        (40.7746, -73.9707), "east shore of the Lake near Bethesda Terrace, looking north-west at Bow Bridge",
        subject=(40.7757, -73.9718), subject_name="Bow Bridge", geosearch_radius_m=250, gps_subject_max_m=600,
        exclude=AERIAL_WORDS + ["night"]),
    _it("landmark_central_park_sheep_meadow", "Central Park: Sheep Meadow with the Midtown skyline", "landmark",
        ['"Sheep Meadow" Central Park skyline', '"Sheep Meadow" Central Park Billionaires Row'],
        [["sheep meadow"]],
        (40.7722, -73.9755), "north end of Sheep Meadow, looking south at the Central Park South / 57th Street skyline",
        subject=(40.7649, -73.9774), subject_name="111 West 57th Street (Billionaires' Row skyline)", geosearch_radius_m=300,
        gps_subject_max_m=1500, min_year=2019, exclude=AERIAL_WORDS + ["night", "snow", "concert"]),
    _it("landmark_metropolitan_museum", "Metropolitan Museum of Art", "landmark",
        ['"Metropolitan Museum of Art" facade Fifth Avenue', '"Metropolitan Museum of Art" exterior steps'],
        [["metropolitan museum", "the met"]],
        (40.7789, -73.9622), "Fifth Avenue at East 82nd Street, east sidewalk, looking west at the Fifth Avenue facade and steps",
        subject=(40.7794, -73.9632), subject_name="Metropolitan Museum of Art Fifth Avenue facade", geosearch_radius_m=200,
        exclude=AERIAL_WORDS + ["interior", "gallery", "inside", "cloisters", "breuer", "painting", "sculpture", "exhibit", "night", "roof garden", "gala"]),
    _it("landmark_guggenheim", "Solomon R. Guggenheim Museum", "landmark",
        ['"Solomon R. Guggenheim Museum" exterior', '"Guggenheim Museum" New York Fifth Avenue'],
        [["guggenheim"], ["new york", "manhattan", "fifth avenue", "5th avenue", "solomon"]],
        (40.7826, -73.9585), "Fifth Avenue at East 88th Street, Central Park side, looking north-west at the rotunda",
        subject=(40.7830, -73.9590), subject_name="Guggenheim Museum", geosearch_radius_m=200,
        exclude=AERIAL_WORDS + ["bilbao", "venice", "abu dhabi", "interior", "rotunda interior", "inside", "atrium", "night", "helsinki"]),
    _it("landmark_amnh", "American Museum of Natural History", "landmark",
        ['"American Museum of Natural History" Central Park West facade', '"American Museum of Natural History" exterior Roosevelt'],
        [["natural history"]],
        (40.7810, -73.9727), "Central Park West at West 79th Street, park side, looking west at the Roosevelt Memorial entrance",
        subject=(40.7813, -73.9739), subject_name="American Museum of Natural History (Central Park West entrance)", geosearch_radius_m=250,
        exclude=AERIAL_WORDS + ["interior", "hall of", "dinosaur", "skeleton", "diorama", "whale", "inside", "exhibit", "london", "smithsonian", "night", "planetarium interior", "gilder"]),
    _it("landmark_columbus_circle", "Columbus Circle", "landmark",
        ['"Columbus Circle" Manhattan', '"Columbus Circle" Time Warner Center Deutsche Bank Center'],
        [["columbus circle"]],
        (40.7686, -73.9810), "Merchants' Gate (south-west corner of Central Park), looking south-west across the circle to the twin towers",
        subject=(40.7683, -73.9830), subject_name="Deutsche Bank Center (formerly Time Warner Center)", geosearch_radius_m=200,
        exclude=AERIAL_WORDS + ["night", "subway", "station", "interior", "mall"]),
    _it("landmark_lincoln_center", "Lincoln Center", "landmark",
        ['"Lincoln Center" plaza Metropolitan Opera House', '"Lincoln Center for the Performing Arts" fountain plaza'],
        [["lincoln center"]],
        (40.7720, -73.9828), "top of the Josie Robertson Plaza steps at Columbus Avenue and West 64th Street, looking west at the Metropolitan Opera House",
        subject=(40.7728, -73.9843), subject_name="Metropolitan Opera House", geosearch_radius_m=200,
        exclude=AERIAL_WORDS + ["interior", "inside", "auditorium", "stage", "chandelier", "night", "rendering"]),
    _it("landmark_madison_square_garden", "Madison Square Garden", "landmark",
        ['"Madison Square Garden" exterior Seventh Avenue', '"Madison Square Garden" Pennsylvania Station exterior'],
        [["madison square garden"]],
        (40.7497, -73.9915), "Seventh Avenue at West 32nd Street, east sidewalk, looking west at the arena drum",
        subject=(40.7505, -73.9934), subject_name="Madison Square Garden", geosearch_radius_m=250,
        exclude=AERIAL_WORDS + ["interior", "inside", "arena floor", "game", "concert", "knicks", "rangers", "court", "ice", "night", "1890", "1925", "1968", "old madison"]),
    _it("landmark_nypl", "New York Public Library (Stephen A. Schwarzman Building)", "landmark",
        ['"New York Public Library" Main Branch facade Fifth Avenue', '"Stephen A. Schwarzman Building" exterior lions'],
        [["public library", "schwarzman"]],
        (40.7527, -73.9806), "Fifth Avenue at East 41st Street, east sidewalk, looking west-north-west at the portico and lions",
        subject=(40.7532, -73.9822), subject_name="New York Public Library main entrance", geosearch_radius_m=200,
        exclude=AERIAL_WORDS + ["interior", "inside", "reading room", "hall", "night", "ceiling", "boston"]),
    _it("landmark_washington_square_arch", "Washington Square Arch", "landmark",
        ['"Washington Square Arch"', '"Washington Square Park" arch fountain'],
        [["washington square"]],
        (40.7308, -73.9973), "south rim of the Washington Square fountain, looking north through the Arch up Fifth Avenue",
        subject=(40.7311, -73.9971), subject_name="Washington Square Arch", geosearch_radius_m=200, gps_subject_max_m=500,
        exclude=AERIAL_WORDS + ["night", "protest", "1890", "1895"]),
    _it("landmark_woolworth_building", "Woolworth Building", "landmark",
        ['"Woolworth Building" exterior', '"Woolworth Building" City Hall Park Broadway'],
        [["woolworth"]],
        (40.7127, -74.0066), "City Hall Park by the fountain, looking west-south-west at the Woolworth Building",
        subject=(40.7124, -74.0084), subject_name="Woolworth Building", geosearch_radius_m=250,
        exclude=AERIAL_WORDS + ["lobby", "interior", "inside", "night", "1913", "store", "five and dime"]),
    _it("landmark_city_hall", "New York City Hall", "landmark",
        ['"New York City Hall" exterior', '"City Hall" Manhattan City Hall Park building'],
        [["city hall"], ["new york", "manhattan", "city hall park"]],
        (40.7117, -74.0075), "south apex of City Hall Park (Broadway at Park Row), looking north-east at the south front",
        subject=(40.7128, -74.0060), subject_name="New York City Hall", geosearch_radius_m=200,
        exclude=AERIAL_WORDS + ["interior", "inside", "chamber", "rotunda", "philadelphia", "borough hall", "subway", "station", "night", "san francisco", "los angeles", "protest", "rally"]),
    _it("landmark_municipal_building", "Manhattan Municipal Building", "landmark",
        ['"Manhattan Municipal Building"', '"David N. Dinkins Municipal Building"'],
        [["municipal building"]],
        (40.7140, -74.0058), "Chambers Street at Broadway (Tweed Courthouse), looking east down Chambers Street at the arch",
        subject=(40.7128, -74.0040), subject_name="Manhattan Municipal Building", geosearch_radius_m=250,
        exclude=AERIAL_WORDS + ["interior", "inside", "night", "civic fame closeup"]),
    _it("landmark_charging_bull", "Charging Bull", "landmark",
        ['"Charging Bull" Bowling Green', '"Charging Bull" Wall Street bull sculpture Broadway'],
        [["charging bull", "wall street bull", "bowling green bull"]],
        (40.7058, -74.0131), "Broadway traffic island at the north tip of Bowling Green, looking south-west at the bull's head",
        subject=(40.7055, -74.0134), subject_name="Charging Bull", geosearch_radius_m=150, gps_subject_max_m=300,
        exclude=["shanghai", "amsterdam", "replica", "night"]),
    _it("landmark_nyse", "New York Stock Exchange", "landmark",
        ['"New York Stock Exchange" building facade Broad Street', '"New York Stock Exchange" exterior flag columns'],
        [["stock exchange"]],
        (40.7071, -74.0104), "Broad Street at Wall Street (Federal Hall side), looking west-south-west at the Broad Street facade",
        subject=(40.7069, -74.0112), subject_name="New York Stock Exchange (11 Broad Street)", geosearch_radius_m=150, gps_subject_max_m=400,
        exclude=["trading floor", "interior", "inside", "night", "1900", "1910", "bell", "traders"]),
    _it("landmark_trinity_church", "Trinity Church", "landmark",
        ['"Trinity Church" Wall Street', '"Trinity Church" Manhattan Broadway spire'],
        [["trinity church"], ["wall street", "manhattan", "broadway", "new york"]],
        (40.7065, -74.0095), "Wall Street at William Street, looking west up Wall Street at the spire",
        subject=(40.7081, -74.0121), subject_name="Trinity Church", geosearch_radius_m=250, gps_subject_max_m=600,
        exclude=AERIAL_WORDS + ["boston", "interior", "inside", "altar", "grave", "tomb", "night", "copley"]),
    _it("landmark_the_dakota", "The Dakota", "landmark",
        ['"The Dakota" Central Park West', '"Dakota" apartment building 72nd Street Manhattan'],
        [["dakota"]],
        (40.7760, -73.9752), "Central Park West at West 72nd Street, park side, looking west-north-west at the 72nd Street front",
        subject=(40.7765, -73.9761), subject_name="The Dakota", geosearch_radius_m=200, gps_subject_max_m=400,
        exclude=AERIAL_WORDS + ["north dakota", "south dakota", "fargo", "territory", "night", "interior", "inside", "lennon memorial", "strawberry fields"]),
    _it("landmark_the_plaza_hotel", "The Plaza Hotel", "landmark",
        ['"Plaza Hotel" Fifth Avenue Grand Army Plaza', '"The Plaza Hotel" New York exterior'],
        [["plaza hotel"]],
        (40.7642, -73.9736), "Grand Army Plaza by the Pulitzer Fountain, looking west at the Fifth Avenue front",
        subject=(40.7645, -73.9744), subject_name="The Plaza Hotel", geosearch_radius_m=200, gps_subject_max_m=400,
        exclude=AERIAL_WORDS + ["interior", "inside", "lobby", "palm court", "night", "boston", "copley", "eloise"]),
    _it("landmark_apollo_theater", "Apollo Theater", "landmark",
        ['"Apollo Theater" Harlem 125th Street', '"Apollo Theater" marquee Harlem'],
        [["apollo theater", "apollo theatre"]],
        (40.8097, -73.9503), "south sidewalk of West 125th Street opposite the theatre, looking north at the marquee",
        subject=(40.8100, -73.9500), subject_name="Apollo Theater marquee", geosearch_radius_m=150, gps_subject_max_m=200,
        exclude=["interior", "inside", "stage", "night", "chicago", "oberhausen", "düsseldorf", "victoria", "london", "shaftesbury", "hammersmith"]),
    _it("landmark_yankee_stadium", "Yankee Stadium", "landmark",
        ['"Yankee Stadium" exterior 161st Street', '"Yankee Stadium" facade River Avenue limestone'],
        [["yankee stadium"]],
        (40.8282, -73.9265), "East 161st Street at River Avenue, under the elevated 4 train, looking north at the Gate 4 facade",
        subject=(40.8296, -73.9264), subject_name="Yankee Stadium (2009)", geosearch_radius_m=300, min_year=2009,
        exclude=AERIAL_WORDS + ["interior", "inside", "outfield", "infield", "game", "old yankee stadium", "original yankee", "1923", "demolition", "night", "monument park", "seats"]),
    _it("landmark_citi_field", "Citi Field", "landmark",
        ['"Citi Field" exterior rotunda', '"Citi Field" Jackie Robinson Rotunda exterior facade'],
        [["citi field"]],
        (40.7547, -73.8458), "Mets-Willets Point station ramp / 126th Street plaza, looking north at the Jackie Robinson Rotunda",
        subject=(40.7571, -73.8458), subject_name="Citi Field (Jackie Robinson Rotunda)", geosearch_radius_m=300, min_year=2009,
        exclude=AERIAL_WORDS + ["interior", "inside", "game", "night", "field view", "scoreboard", "seats", "outfield", "infield"]),
    _it("landmark_unisphere", "Unisphere", "landmark",
        ['"Unisphere" Flushing Meadows', '"Unisphere" Queens fountain'],
        [["unisphere"]],
        (40.7452, -73.8465), "fountain-plaza paving west-south-west of the Unisphere, Flushing Meadows-Corona Park, looking north-east",
        subject=(40.7460, -73.8450), subject_name="Unisphere", geosearch_radius_m=300, gps_subject_max_m=600,
        exclude=AERIAL_WORDS + ["night", "replica", "1964", "1965", "world's fair"]),
    _it("landmark_coney_island_cyclone", "Coney Island Cyclone", "landmark",
        ['"Coney Island Cyclone" roller coaster', '"Cyclone" roller coaster Coney Island Luna Park'],
        [["cyclone"], ["coney"]],
        (40.5754, -73.9772), "Surf Avenue at West 10th Street, north sidewalk, looking south-west at the lift hill",
        subject=(40.5748, -73.9780), subject_name="Cyclone roller coaster", geosearch_radius_m=300, gps_subject_max_m=500,
        exclude=AERIAL_WORDS + ["night", "1920", "1930", "hurricane", "storm", "tropical cyclone"]),
    _it("landmark_coney_island_wonder_wheel", "Deno's Wonder Wheel", "landmark",
        ['"Wonder Wheel" Coney Island', "\"Deno's Wonder Wheel\" boardwalk"],
        [["wonder wheel"]],
        (40.5727, -73.9790), "Riegelmann Boardwalk at West 12th Street, looking north at the wheel",
        subject=(40.5740, -73.9787), subject_name="Wonder Wheel", geosearch_radius_m=300, gps_subject_max_m=500,
        exclude=AERIAL_WORDS + ["night"]),
    _it("landmark_coney_island_parachute_jump", "Coney Island Parachute Jump", "landmark",
        ['"Parachute Jump" Coney Island', '"Parachute Jump" boardwalk Brooklyn tower'],
        [["parachute jump"]],
        (40.5729, -73.9818), "Riegelmann Boardwalk at West 15th Street, looking west at the tower",
        subject=(40.5735, -73.9840), subject_name="Parachute Jump", geosearch_radius_m=400, gps_subject_max_m=800,
        exclude=AERIAL_WORDS + ["night", "1940", "1941", "world's fair"]),
    _it("landmark_barclays_center", "Barclays Center", "landmark",
        ['"Barclays Center" exterior Atlantic Avenue Flatbush', '"Barclays Center" oculus entrance plaza'],
        [["barclays center", "barclays centre"]],
        (40.6840, -73.9768), "north-west corner of Flatbush and Atlantic Avenues, looking south-east at the oculus entrance",
        subject=(40.6826, -73.9755), subject_name="Barclays Center", geosearch_radius_m=250, min_year=2012,
        exclude=AERIAL_WORDS + ["interior", "inside", "arena floor", "game", "concert", "nets", "night", "construction", "rendering"]),
    _it("landmark_432_park_avenue", "432 Park Avenue (Billionaires' Row)", "landmark",
        ['"432 Park Avenue" skyscraper', '"432 Park Avenue" from Park Avenue street'],
        [["432 park"]],
        (40.7581, -73.9726), "Park Avenue median at East 52nd Street, looking north at the tower",
        subject=(40.7616, -73.9714), subject_name="432 Park Avenue", geosearch_radius_m=400, gps_subject_max_m=3000, min_year=2016,
        exclude=AERIAL_WORDS + ["construction", "night", "interior", "rendering"]),
    _it("landmark_111_west_57th", "111 West 57th Street (Steinway Tower, Billionaires' Row)", "landmark",
        ['"111 West 57th Street" Steinway Tower', '"Steinway Tower" Central Park skyscraper'],
        [["111 west 57", "111 w 57", "steinway tower"]],
        (40.7683, -73.9748), "Central Park at Wollman Rink / the Pond, looking south-south-west at the tower",
        subject=(40.7649, -73.9774), subject_name="111 West 57th Street", geosearch_radius_m=400, gps_subject_max_m=3000, min_year=2020,
        exclude=AERIAL_WORDS + ["construction", "night", "interior", "rendering", "steinway hall interior"]),
    _it("landmark_central_park_tower", "Central Park Tower (Billionaires' Row)", "landmark",
        ['"Central Park Tower" 57th Street skyscraper', '"Central Park Tower" Nordstrom Tower Broadway'],
        [["central park tower", "nordstrom tower"]],
        (40.7651, -73.9828), "south-west corner of West 57th Street and Broadway, looking north-east at the tower",
        subject=(40.7664, -73.9809), subject_name="Central Park Tower", geosearch_radius_m=400, gps_subject_max_m=3000, min_year=2020,
        exclude=AERIAL_WORDS + ["construction", "night", "interior", "rendering"]),
    _it("landmark_one57", "One57 (Billionaires' Row)", "landmark",
        ['"One57" 57th Street skyscraper', '"One57" Carnegie 57 Manhattan Sixth Avenue'],
        [["one57", "one 57", "carnegie 57"]],
        (40.7639, -73.9776), "south-east corner of West 57th Street and Sixth Avenue, looking north-west at the tower",
        subject=(40.7655, -73.9791), subject_name="One57", geosearch_radius_m=400, gps_subject_max_m=3000, min_year=2014,
        exclude=AERIAL_WORDS + ["construction", "night", "interior", "rendering", "crane", "sandy"]),
    _it("landmark_united_nations_hq", "United Nations Headquarters", "landmark",
        ['"United Nations Headquarters" Secretariat Building First Avenue flags', '"United Nations Headquarters" New York exterior'],
        [["united nations", "un headquarters", "secretariat"]],
        (40.7495, -73.9698), "First Avenue at East 43rd Street, west sidewalk, looking east at the flag row and the Secretariat",
        subject=(40.7489, -73.9680), subject_name="UN Secretariat Building", geosearch_radius_m=300,
        exclude=AERIAL_WORDS + ["geneva", "vienna", "nairobi", "interior", "inside", "general assembly hall", "security council", "chamber", "night"]),
    _it("landmark_domino_sugar_refinery", "Domino Sugar Refinery", "landmark",
        ['"Domino Sugar Refinery" Williamsburg', '"Domino Park" refinery building Brooklyn'],
        [["domino"]],
        (40.7150, -73.9672), "Domino Park esplanade at South 2nd Street, looking south at the refinery building",
        subject=(40.7143, -73.9675), subject_name="Domino Sugar Refinery", geosearch_radius_m=300, gps_subject_max_m=1500, min_year=2018,
        exclude=AERIAL_WORDS + ["baltimore", "interior", "inside", "night", "demolition", "kara walker", "sugar baby"]),
    _it("landmark_george_washington_bridge", "George Washington Bridge", "landmark",
        ['"George Washington Bridge" from Fort Washington Park', '"George Washington Bridge" Little Red Lighthouse'],
        [["george washington bridge", "gwb"]],
        (40.8472, -73.9450), "Hudson River Greenway in Fort Washington Park just south of the bridge, looking north at the New York tower",
        subject=(40.8506, -73.9466), subject_name="George Washington Bridge New York tower", geosearch_radius_m=600, gps_subject_max_m=4000,
        exclude=AERIAL_WORDS + ["night", "bus station", "bus terminal", "construction", "1931"]),
    _it("landmark_verrazzano_narrows_bridge", "Verrazzano-Narrows Bridge", "landmark",
        ['"Verrazzano-Narrows Bridge" from Bay Ridge', '"Verrazano-Narrows Bridge" Shore Road Brooklyn'],
        [["verrazzano", "verrazano"]],
        (40.6140, -74.0372), "Shore Parkway greenway near 92nd Street, Bay Ridge, looking south-west at the span",
        subject=(40.6066, -74.0460), subject_name="Verrazzano-Narrows Bridge", geosearch_radius_m=1000, gps_subject_max_m=5000,
        exclude=AERIAL_WORDS + ["night", "marathon", "under construction", "1964"]),
    _it("landmark_queensboro_bridge", "Ed Koch Queensboro Bridge", "landmark",
        ['"Queensboro Bridge" Sutton Place', '"Ed Koch Queensboro Bridge" from Manhattan'],
        [["queensboro", "59th street bridge", "ed koch"]],
        (40.7576, -73.9598), "Sutton Place Park at East 57th Street, looking east along the span toward Roosevelt Island",
        subject=(40.7565, -73.9540), subject_name="Queensboro Bridge (west channel span)", geosearch_radius_m=600, gps_subject_max_m=3000,
        exclude=AERIAL_WORDS + ["night", "tram interior", "1909", "construction"]),
    _it("landmark_williamsburg_bridge", "Williamsburg Bridge", "landmark",
        ['"Williamsburg Bridge" from Domino Park', '"Williamsburg Bridge" Brooklyn waterfront Kent Avenue'],
        [["williamsburg bridge"]],
        (40.7165, -73.9668), "north end of Domino Park (Grand Street pier), looking south at the Brooklyn tower",
        subject=(40.7122, -73.9688), subject_name="Williamsburg Bridge Brooklyn tower", geosearch_radius_m=600, gps_subject_max_m=3000,
        exclude=AERIAL_WORDS + ["night", "1903", "construction"]),
    _it("landmark_manhattan_bridge", "Manhattan Bridge", "landmark",
        ['"Manhattan Bridge" from Brooklyn Bridge Park', '"Manhattan Bridge" Main Street Park DUMBO waterfront'],
        [["manhattan bridge"]],
        (40.7040, -73.9920), "Pebble Beach at Main Street Park (Brooklyn Bridge Park), looking east-north-east at the Brooklyn tower",
        subject=(40.7045, -73.9897), subject_name="Manhattan Bridge Brooklyn tower", geosearch_radius_m=300, gps_subject_max_m=2500,
        exclude=AERIAL_WORDS + ["washington street", "night", "1909", "construction"]),
    _it("landmark_rfk_triborough_bridge", "Robert F. Kennedy (Triborough) Bridge", "landmark",
        ['"Robert F. Kennedy Bridge" Astoria Park', '"Triborough Bridge" suspension span Astoria'],
        [["robert f. kennedy bridge", "rfk bridge", "triborough", "triboro"]],
        (40.7795, -73.9255), "Astoria Park shore path midway between the two bridges, looking south-west at the RFK suspension span",
        subject=(40.7770, -73.9270), subject_name="RFK Bridge East River suspension span", geosearch_radius_m=700, gps_subject_max_m=3000,
        exclude=AERIAL_WORDS + ["night", "1936", "toll plaza"]),
    _it("landmark_hell_gate_bridge", "Hell Gate Bridge", "landmark",
        ['"Hell Gate Bridge" Astoria Park', '"Hell Gate Bridge" East River arch'],
        [["hell gate"]],
        (40.7800, -73.9250), "Astoria Park shore path, looking north-west at the arch",
        subject=(40.7823, -73.9290), subject_name="Hell Gate Bridge", geosearch_radius_m=700, gps_subject_max_m=3000,
        exclude=AERIAL_WORDS + ["night", "1916", "1917", "construction"]),
    _it("landmark_high_bridge", "High Bridge", "landmark",
        ['"High Bridge" Harlem River aqueduct', '"High Bridge" Highbridge Park Manhattan Bronx'],
        [["high bridge", "highbridge"]],
        (40.8418, -73.9322), "Highbridge Park overlook on the Manhattan side, looking east along the deck",
        subject=(40.8424, -73.9285), subject_name="High Bridge", geosearch_radius_m=500, gps_subject_max_m=2000, min_year=2015,
        exclude=AERIAL_WORDS + ["night", "1848", "1900", "water tower"]),
    _it("landmark_holland_tunnel_portal", "Holland Tunnel Manhattan portal", "landmark",
        ['"Holland Tunnel" entrance Manhattan Canal Street', '"Holland Tunnel" portal New York side'],
        [["holland tunnel"]],
        (40.7250, -74.0068), "Canal Street at Hudson Street, looking north-west at the Manhattan entrance plaza",
        subject=(40.7258, -74.0081), subject_name="Holland Tunnel Manhattan portal", geosearch_radius_m=400, gps_subject_max_m=1500,
        exclude=AERIAL_WORDS + ["jersey city", "new jersey side", "inside the tunnel", "interior of the tunnel", "ventilation", "1927", "night"]),
    _it("landmark_lincoln_tunnel_portal", "Lincoln Tunnel Manhattan portal", "landmark",
        ['"Lincoln Tunnel" entrance Manhattan portal', '"Lincoln Tunnel" New York side Dyer Avenue'],
        [["lincoln tunnel"]],
        (40.7590, -73.9982), "West 39th Street at Tenth Avenue, looking west at the Manhattan portals",
        subject=(40.7597, -74.0000), subject_name="Lincoln Tunnel Manhattan portals", geosearch_radius_m=400, gps_subject_max_m=1500,
        exclude=AERIAL_WORDS + ["weehawken", "helix", "new jersey", "inside the tunnel", "interior", "1937", "night", "bus terminal"]),
    # -------------------------------------------- 9b landmarks (rest of docs/LANDMARKS.md)
    # Group A - civic and downtown towers
    _lmk("landmark_federal_hall", "Federal Hall National Memorial",
         ['"Federal Hall" Wall Street', '"Federal Hall National Memorial" exterior columns'],
         [["federal hall"]], (40.707222, -74.010278), 175.0, 40.0,
         "Wall Street south sidewalk opposite 26 Wall Street, looking north at the Doric portico and the Washington statue",
         geosearch_radius_m=150, exclude=AERIAL_WORDS + ["interior", "rotunda", "inside"]),
    _lmk("landmark_40_wall_street", "40 Wall Street (Trump Building)",
         ['"40 Wall Street" building', '"Trump Building" 40 Wall Street Manhattan'],
         [["40 wall", "trump building", "bank of manhattan"]], (40.7069, -74.0097), 250.0, 200.0,
         "Wall Street at Broad Street, about 200 m west-south-west of the tower, looking east-north-east at the pyramidal crown",
         geosearch_radius_m=250, exclude=AERIAL_WORDS + ["interior", "lobby", "protest"]),
    _lmk("landmark_one_wall_street", "One Wall Street (Irving Trust Building)",
         ['"1 Wall Street" building Manhattan', '"One Wall Street" Irving Trust Building'],
         [["1 wall street", "one wall street", "irving trust"]], (40.707222, -74.011667), 255.0, 60.0,
         "Broadway east sidewalk at Wall Street, about 60 m west-south-west of the building, looking east-north-east at the fluted limestone facade",
         geosearch_radius_m=200, exclude=AERIAL_WORDS + ["interior", "lobby", "red room", "mosaic"]),
    _lmk("landmark_equitable_building", "Equitable Building (120 Broadway)",
         ['"Equitable Building" 120 Broadway', '"120 Broadway" Manhattan building'],
         [["equitable building", "120 broadway"], NYC_WORDS], (40.708333, -74.010278), 265.0, 60.0,
         "Broadway west sidewalk opposite 120 Broadway, about 60 m from the facade, looking east at the H-plan slab",
         geosearch_radius_m=200, exclude=AERIAL_WORDS + ["interior", "lobby", "des moines", "atlanta", "portland", "chicago", "1915", "1920"]),
    _lmk("landmark_moma", "Museum of Modern Art",
         ['"Museum of Modern Art" New York 53rd Street facade', 'MoMA New York exterior building'],
         [["museum of modern art", "moma"], NYC_WORDS], (40.7617, -73.9775), 180.0, 30.0,
         "West 53rd Street south sidewalk between Fifth and Sixth Avenues, looking north at the museum's 53rd Street front",
         geosearch_radius_m=150, exclude=AERIAL_WORDS + ["interior", "gallery", "exhibition", "san francisco", "sfmoma", "tokyo", "warsaw", "medellin"]),
    _lmk("landmark_rockefeller_rink", "Rockefeller Center Lower Plaza and rink (Prometheus)",
         ['"Rockefeller Center" Lower Plaza Prometheus rink', '"Rockefeller Center" skating rink Channel Gardens'],
         [["rockefeller"], ["rink", "skating", "prometheus", "lower plaza", "channel gardens"]],
         (40.75873, -73.97865), 80.0, 70.0,
         "east end of the Channel Gardens promenade above the Lower Plaza, looking west across the rink to Prometheus and 30 Rockefeller Plaza",
         geosearch_radius_m=180, gps_subject_max_m=600, exclude=AERIAL_WORDS + ["christmas tree lighting", "tree lighting", "interior"]),

    # Group B - bridges, tunnels, WTC, islands, parks, monuments
    _lmk("landmark_throgs_neck_bridge", "Throgs Neck Bridge",
         ['"Throgs Neck Bridge"', '"Throgs Neck Bridge" East River span'],
         [["throgs neck", "throg's neck"]], (40.802, -73.793), 205.0, 1000.0,
         "Little Bay Park shoreline in Bayside, Queens, about 1 km south-west of the main span, looking north-east along the bridge",
         geosearch_radius_m=1500, gps_subject_max_m=6000, exclude=["interior", "toll plaza sign"]),
    _lmk("landmark_bronx_whitestone_bridge", "Bronx-Whitestone Bridge",
         ['"Bronx-Whitestone Bridge"', '"Whitestone Bridge" East River suspension'],
         [["whitestone bridge"]], (40.801111, -73.829167), 340.0, 900.0,
         "Ferry Point Park shoreline in the Bronx, about 900 m north-north-west of the main span, looking south-south-east along the bridge",
         geosearch_radius_m=1500, gps_subject_max_m=6000, exclude=["interior"]),
    _lmk("landmark_pulaski_bridge", "Pulaski Bridge",
         ['"Pulaski Bridge" Newtown Creek', '"Pulaski Bridge" Greenpoint Long Island City'],
         [["pulaski bridge"]], (40.739167, -73.9525), 160.0, 350.0,
         "McGuinness Boulevard in Greenpoint, about 350 m south-south-east of the bascule span, looking north-north-west across Newtown Creek",
         geosearch_radius_m=600, gps_subject_max_m=3000, exclude=["chicago", "pulaski road", "casimir pulaski day", "pulaski skyway"]),
    _lmk("landmark_kosciuszko_bridge", "Kosciuszko Bridge",
         ['"Kosciuszko Bridge" cable-stayed', '"Kosciuszko Bridge" Newtown Creek Brooklyn Queens Expressway'],
         [["kosciuszko", "kosciuszko bridge"]], (40.7277, -73.9291), 200.0, 500.0,
         "Meeker Avenue in East Williamsburg, about 500 m south-south-west of the main span, looking north-north-east at the cable-stayed tower",
         geosearch_radius_m=900, gps_subject_max_m=3000, min_year=2017,
         exclude=["demolition", "implosion", "old bridge", "truss span", "1939"]),
    _lmk("landmark_roosevelt_island_tram", "Roosevelt Island Tramway",
         ['"Roosevelt Island Tramway" cabin East River', '"Roosevelt Island Tram" Queensboro Bridge'],
         [["tram", "tramway", "aerial tramway"], ["roosevelt island"]], (40.7614, -73.964), 120.0, 900.0,
         "Tramway Plaza on Roosevelt Island, about 900 m east-south-east of the Manhattan station, looking west-north-west at a cabin crossing the East River",
         geosearch_radius_m=800, gps_subject_max_m=3000, exclude=AERIAL_WORDS + ["interior of the cabin", "portland", "wellington"]),
    _lmk("landmark_queens_midtown_tunnel_portal", "Queens-Midtown Tunnel Manhattan portal",
         ['"Queens-Midtown Tunnel" entrance Manhattan', '"Queens Midtown Tunnel" portal toll'],
         [["queens-midtown tunnel", "queens midtown tunnel", "midtown tunnel"]], (40.7462, -73.9717), 300.0, 120.0,
         "East 37th Street at Tunnel Exit Street in Murray Hill, about 120 m north-west of the Manhattan portal, looking south-east into the tunnel mouth",
         geosearch_radius_m=400, gps_subject_max_m=2000, exclude=["inside the tunnel", "tube", "queens portal"]),
    _lmk("landmark_hugh_carey_tunnel_portal", "Hugh L. Carey (Brooklyn-Battery) Tunnel Manhattan portal",
         ['"Hugh L. Carey Tunnel" entrance Manhattan', '"Brooklyn-Battery Tunnel" Manhattan portal ventilation building'],
         [["hugh l. carey tunnel", "hugh carey tunnel", "brooklyn-battery tunnel", "brooklyn battery tunnel"]],
         (40.7008, -74.0157), 20.0, 150.0,
         "Battery Place near West Street, about 150 m north-north-east of the Manhattan portal, looking south-south-west at the tunnel mouth and ventilation building",
         geosearch_radius_m=400, gps_subject_max_m=2500, exclude=["inside the tunnel", "tube", "brooklyn portal", "governors island vent"]),
    _lmk("landmark_3_world_trade_center", "3 World Trade Center",
         ['"3 World Trade Center" tower', '"175 Greenwich Street" tower'],
         [["3 world trade", "three world trade", "175 greenwich"]], (40.710923, -74.011608), 100.0, 130.0,
         "Church Street opposite Cortlandt Way, about 130 m east of the tower, looking west at 3 World Trade Center",
         geosearch_radius_m=300, gps_subject_max_m=3000, min_year=2018,
         exclude=AERIAL_WORDS + ["under construction", "construction", "crane", "rendering", "interior"]),
    _lmk("landmark_4_world_trade_center", "4 World Trade Center",
         ['"4 World Trade Center" tower Maki', '"150 Greenwich Street" tower'],
         [["4 world trade", "four world trade", "150 greenwich"]], (40.7104, -74.0119), 120.0, 150.0,
         "Church Street at Liberty Street, about 150 m east-south-east of the tower, looking west-north-west at 4 World Trade Center",
         geosearch_radius_m=300, gps_subject_max_m=3000, min_year=2014,
         exclude=AERIAL_WORDS + ["under construction", "construction", "crane", "rendering", "interior"]),
    _lmk("landmark_7_world_trade_center", "7 World Trade Center",
         ['"7 World Trade Center" tower Greenwich Street', '"250 Greenwich Street" 7 WTC'],
         [["7 world trade", "seven world trade", "250 greenwich"]], (40.7133, -74.012), 110.0, 150.0,
         "Church Street at Barclay Street, about 150 m east-south-east of the tower, looking west-north-west at 7 World Trade Center",
         geosearch_radius_m=300, gps_subject_max_m=3000, min_year=2010,
         exclude=AERIAL_WORDS + ["collapse", "september 11, 2001", "2001", "destroyed", "rubble", "interior", "lobby"]),
    _lmk("landmark_ellis_island", "Ellis Island Main Building",
         ['"Ellis Island" main building immigration station', '"Ellis Island" immigration museum exterior'],
         [["ellis island"]], (40.699444, -74.039722), 350.0, 250.0,
         "the ferry basin north of the Main Building, about 250 m from the entrance canopy, looking south at the four-turreted immigration building",
         geosearch_radius_m=600, gps_subject_max_m=3000,
         exclude=AERIAL_WORDS + ["interior", "registry room", "great hall", "museum exhibit", "1900", "1910", "1920", "immigrants arriving"]),
    _lmk("landmark_belvedere_castle", "Belvedere Castle",
         ['"Belvedere Castle" Central Park', '"Belvedere Castle" Turtle Pond'],
         [["belvedere castle"]], (40.779447, -73.96906), 120.0, 150.0,
         "the north shore of Turtle Pond, about 150 m east-south-east of the castle, looking west-north-west at Belvedere Castle on Vista Rock",
         geosearch_radius_m=250, gps_subject_max_m=800, exclude=AERIAL_WORDS + ["interior", "inside"]),
    _lmk("landmark_central_park_wall_gates", "Central Park perimeter wall and gates",
         ['"Central Park" perimeter wall Manhattan schist', "\"Scholars' Gate\" Central Park entrance"],
         [["central park"], ["perimeter wall", "park wall", "scholars' gate", "merchants' gate", "artists' gate", "gate", "entrance"]],
         (40.7645, -73.9735), 100.0, 60.0,
         "Grand Army Plaza at Fifth Avenue and 60th Street, about 60 m east of Scholars' Gate, looking west at the schist perimeter wall and gate piers",
         geosearch_radius_m=400, gps_subject_max_m=1500,
         exclude=AERIAL_WORDS + ["gateway arch", "snow", "winter", "1900", "1910", "carriage horse"]),
    _lmk("landmark_castle_williams", "Castle Williams (Governors Island)",
         ['"Castle Williams" Governors Island', '"Castle Williams" fort New York Harbor'],
         [["castle williams"]], (40.692778, -74.019167), 90.0, 200.0,
         "the Governors Island esplanade about 200 m east of the fort, looking west at the circular red-sandstone casemates",
         geosearch_radius_m=400, gps_subject_max_m=2000, exclude=AERIAL_WORDS + ["interior", "cell", "prison cell"]),
    _lmk("landmark_fort_jay", "Fort Jay (Governors Island)",
         ['"Fort Jay" Governors Island', '"Fort Jay" sally port trophy'],
         [["fort jay"]], (40.691358, -74.016008), 180.0, 150.0,
         "the parade ground south of the fort, about 150 m from the sally port, looking north at the Fort Jay gate and its sculpted trophy",
         geosearch_radius_m=350, gps_subject_max_m=2000, exclude=AERIAL_WORDS + ["interior", "barracks interior"]),
    _lmk("landmark_grants_tomb", "General Grant National Memorial (Grant's Tomb)",
         ["\"Grant's Tomb\" Riverside Drive", '"General Grant National Memorial" exterior'],
         [["grant's tomb", "general grant national memorial", "grant national memorial", "grant memorial"]],
         (40.813333, -73.963056), 180.0, 120.0,
         "the Riverside Drive plaza south of the mausoleum, about 120 m from the portico, looking north at the granite dome and colonnade",
         geosearch_radius_m=300, gps_subject_max_m=1500, exclude=AERIAL_WORDS + ["interior", "crypt", "sarcophagus", "washington, d.c."]),
    _lmk("landmark_soldiers_sailors_arch", "Soldiers' and Sailors' Memorial Arch (Grand Army Plaza, Brooklyn)",
         ["\"Soldiers' and Sailors' Memorial Arch\" Brooklyn", '"Grand Army Plaza" Brooklyn arch'],
         [["soldiers' and sailors'", "soldiers and sailors", "memorial arch"], ["brooklyn", "grand army plaza", "prospect park"]],
         (40.6738, -73.97), 350.0, 150.0,
         "the plaza island north of the arch at Grand Army Plaza, about 150 m from it, looking south at the Soldiers' and Sailors' Memorial Arch",
         geosearch_radius_m=350, gps_subject_max_m=1500, exclude=AERIAL_WORDS + ["hartford", "connecticut", "indianapolis", "interior"]),
    _lmk("landmark_prospect_park_boathouse", "Prospect Park Boathouse",
         ['"Prospect Park" Boathouse Lullwater', '"Prospect Park Boathouse" Brooklyn'],
         [["boathouse"], ["prospect park"]], (40.660833, -73.965278), 120.0, 80.0,
         "the Lullwater bank about 80 m east-south-east of the Boathouse, looking west-north-west at the terracotta facade above the water",
         geosearch_radius_m=250, gps_subject_max_m=800, exclude=AERIAL_WORDS + ["interior", "central park", "loeb boathouse"]),
    _it("landmark_coney_island_boardwalk", "Riegelmann Boardwalk, Coney Island", "landmark",
        ['"Riegelmann Boardwalk" Coney Island', '"Coney Island" boardwalk amusement'],
        [["boardwalk"], ["coney island", "brighton beach", "riegelmann"]],
        (40.5727, -73.9789), "on the Riegelmann Boardwalk at West 12th Street, looking east-north-east along the deck toward the Wonder Wheel and the aquarium",
        azimuth=70.0, geosearch_radius_m=700, min_year=2014,
        exclude=AERIAL_WORDS + ["night", "hurricane", "sandy", "damage", "1920", "1930", "1940", "snow"]),

    # Group C - Hudson Yards
    _lmk("landmark_30_hudson_yards", "30 Hudson Yards",
         ['"30 Hudson Yards" tower', '"30 Hudson Yards" Edge observation deck exterior'],
         [["30 hudson yards"]], (40.7541, -74.0008), 120.0, 250.0,
         "Tenth Avenue at West 30th Street, about 250 m east-south-east of the tower, looking west-north-west at 30 Hudson Yards and the Edge deck",
         geosearch_radius_m=400, gps_subject_max_m=4000, min_year=2019,
         exclude=AERIAL_WORDS + ["under construction", "construction", "crane", "rendering", "interior", "from the edge", "view from"]),
    _lmk("landmark_35_hudson_yards", "35 Hudson Yards",
         ['"35 Hudson Yards" tower', '"35 Hudson Yards" limestone Hudson Yards'],
         [["35 hudson yards"]], (40.75455, -74.0024), 90.0, 200.0,
         "Tenth Avenue at West 33rd Street, about 200 m east of the tower, looking west at 35 Hudson Yards",
         geosearch_radius_m=400, gps_subject_max_m=4000, min_year=2019,
         exclude=AERIAL_WORDS + ["under construction", "construction", "crane", "rendering", "interior"]),
    _lmk("landmark_10_hudson_yards", "10 Hudson Yards",
         ['"10 Hudson Yards" tower', '"10 Hudson Yards" High Line Coach building'],
         [["10 hudson yards", "coach tower"]], (40.7525, -74.001), 110.0, 200.0,
         "West 30th Street at Tenth Avenue, about 200 m east-south-east of the tower, looking west-north-west at 10 Hudson Yards over the High Line",
         geosearch_radius_m=400, gps_subject_max_m=4000, min_year=2016,
         exclude=AERIAL_WORDS + ["under construction", "construction", "crane", "rendering", "interior"]),
    _lmk("landmark_55_hudson_yards", "55 Hudson Yards",
         ['"55 Hudson Yards" tower', '"55 Hudson Yards" Kohn Pedersen Fox'],
         [["55 hudson yards"]], (40.755278, -74.001667), 100.0, 200.0,
         "West 34th Street at Tenth Avenue, about 200 m east of the tower, looking west at 55 Hudson Yards",
         geosearch_radius_m=400, gps_subject_max_m=4000, min_year=2018,
         exclude=AERIAL_WORDS + ["under construction", "construction", "crane", "rendering", "interior"]),
    _lmk("landmark_15_hudson_yards", "15 Hudson Yards",
         ['"15 Hudson Yards" residential tower', '"15 Hudson Yards" Diller Scofidio'],
         [["15 hudson yards"]], (40.7535, -74.0032), 100.0, 250.0,
         "Tenth Avenue at West 30th Street, about 250 m east of the tower, looking west at the curved shaft of 15 Hudson Yards",
         geosearch_radius_m=400, gps_subject_max_m=4000, min_year=2019,
         exclude=AERIAL_WORDS + ["under construction", "construction", "crane", "rendering", "interior"]),
    _lmk("landmark_50_hudson_yards", "50 Hudson Yards",
         ['"50 Hudson Yards" tower', '"50 Hudson Yards" Foster Partners'],
         [["50 hudson yards"]], (40.754339, -74.000001), 90.0, 200.0,
         "Tenth Avenue at West 33rd Street, about 200 m east of the tower, looking west at 50 Hudson Yards",
         geosearch_radius_m=400, gps_subject_max_m=4000, min_year=2022,
         exclude=AERIAL_WORDS + ["under construction", "construction", "crane", "rendering", "interior"]),
    _lmk("landmark_the_shed", "The Shed",
         ['"The Shed" Hudson Yards building', '"The Shed" Bloomberg Building telescoping shell'],
         [["the shed"], ["hudson yards", "new york", "manhattan"]], (40.753328, -74.002898), 110.0, 180.0,
         "the Hudson Yards public square about 180 m east-south-east of the building, looking west-north-west at The Shed and its telescoping shell",
         geosearch_radius_m=350, gps_subject_max_m=3000, min_year=2019,
         exclude=AERIAL_WORDS + ["under construction", "construction", "rendering", "interior", "performance"]),

    # Group C - Billionaires' Row and Midtown towers
    _lmk("landmark_220_central_park_south", "220 Central Park South",
         ['"220 Central Park South" tower', '"220 Central Park South" Robert A. M. Stern'],
         [["220 central park south"]], (40.766944, -73.980833), 190.0, 200.0,
         "Central Park South at Seventh Avenue, about 200 m south of the tower, looking north at 220 Central Park South",
         geosearch_radius_m=400, gps_subject_max_m=4000, min_year=2019,
         exclude=AERIAL_WORDS + ["under construction", "construction", "crane", "rendering", "interior"]),
    _lmk("landmark_53w53", "53W53 (MoMA Tower)",
         ['"53W53" tower Manhattan', '"53 West 53rd Street" tower Jean Nouvel'],
         [["53w53", "53 west 53rd", "moma tower", "tower verre"]], (40.761667, -73.978333), 170.0, 150.0,
         "West 53rd Street at Fifth Avenue, about 150 m south-south-east of the tower, looking north-north-west at the tapering diagrid of 53W53",
         geosearch_radius_m=400, gps_subject_max_m=4000, min_year=2019,
         exclude=AERIAL_WORDS + ["under construction", "construction", "crane", "rendering", "interior"]),
    _lmk("landmark_trump_tower", "Trump Tower (725 Fifth Avenue)",
         ['"Trump Tower" Fifth Avenue New York', '"Trump Tower" 725 Fifth Avenue exterior'],
         [["trump tower"], ["new york", "manhattan", "fifth avenue"]], (40.7625, -73.9738), 250.0, 100.0,
         "Fifth Avenue west sidewalk opposite 725 Fifth Avenue, about 100 m west-south-west of the entrance, looking east-north-east at the sawtooth curtain wall",
         geosearch_radius_m=300, gps_subject_max_m=3000,
         exclude=AERIAL_WORDS + ["chicago", "las vegas", "toronto", "istanbul", "manila", "vancouver", "protest", "rally", "demonstration", "interior", "atrium"]),
    _lmk("landmark_9_west_57th", "9 West 57th Street (Solow Building)",
         ['"9 West 57th Street" building', '"Solow Building" 9 West 57th Street'],
         [["9 west 57th", "nine west 57th", "solow building"]], (40.763889, -73.974722), 190.0, 150.0,
         "West 57th Street at Fifth Avenue, about 150 m south of the tower, looking north at the sloped curtain wall of 9 West 57th Street",
         geosearch_radius_m=350, gps_subject_max_m=3000,
         exclude=AERIAL_WORDS + ["interior", "lobby", "sculpture only"]),

    # Group C - Times Square buildings
    _lmk("landmark_one_times_square", "One Times Square",
         ['"One Times Square" building', '"One Times Square" ball drop building Times Tower'],
         [["one times square", "1 times square", "times tower"]], (40.756421, -73.986488), 20.0, 180.0,
         "the Times Square bowtie at West 45th Street, about 180 m north-north-east of the building, looking south-south-west at One Times Square",
         geosearch_radius_m=300, gps_subject_max_m=2000, min_year=2014,
         exclude=AERIAL_WORDS + ["new year", "ball drop", "1904", "1920", "under renovation", "interior"]),
    _lmk("landmark_two_times_square", "Two Times Square (714 Seventh Avenue)",
         ['"Two Times Square" building', '"2 Times Square" Seventh Avenue signage'],
         [["two times square", "2 times square", "714 seventh avenue"]], (40.7597, -73.9848), 200.0, 130.0,
         "Duffy Square about 130 m south-south-west of the building, looking north-north-east at the wedge of Two Times Square and its signage",
         geosearch_radius_m=250, gps_subject_max_m=1500, min_year=2012,
         exclude=AERIAL_WORDS + ["new year", "ball drop", "interior"]),
    _lmk("landmark_three_times_square", "3 Times Square (Thomson Reuters Building)",
         ['"3 Times Square" building', '"Thomson Reuters Building" Times Square'],
         [["3 times square", "three times square", "thomson reuters building", "reuters building"]],
         (40.756667, -73.986944), 30.0, 150.0,
         "Seventh Avenue at West 44th Street, about 150 m north-north-east of the tower, looking south-south-west at 3 Times Square",
         geosearch_radius_m=250, gps_subject_max_m=1500,
         exclude=AERIAL_WORDS + ["interior", "newsroom", "under construction"]),
    _lmk("landmark_four_times_square", "4 Times Square (Conde Nast Building)",
         ['"4 Times Square" building', '"Conde Nast Building" Times Square tower'],
         [["4 times square", "four times square", "conde nast building", "condé nast building"]],
         (40.756111, -73.985833), 20.0, 150.0,
         "Broadway at West 44th Street, about 150 m north-north-east of the tower, looking south-south-west at 4 Times Square",
         geosearch_radius_m=250, gps_subject_max_m=1500,
         exclude=AERIAL_WORDS + ["interior", "under construction", "crane"]),
    _lmk("landmark_tsx_broadway", "TSX Broadway",
         ['"TSX Broadway" building', '"TSX Broadway" Times Square stage Palace Theatre'],
         [["tsx broadway", "tsx"], ["times square", "broadway"]], (40.759, -73.984523), 200.0, 130.0,
         "Duffy Square about 130 m south-south-west of the building, looking north-north-east at the TSX Broadway screen and stage",
         geosearch_radius_m=250, gps_subject_max_m=1500, min_year=2022,
         exclude=AERIAL_WORDS + ["under construction", "crane", "rendering", "interior", "new year", "ball drop"]),
    _lmk("landmark_paramount_building", "Paramount Building (1501 Broadway)",
         ['"Paramount Building" Times Square 1501 Broadway', '"Paramount Building" clock tower New York'],
         [["paramount building", "1501 broadway"], ["times square", "broadway", "new york", "manhattan"]],
         (40.757222, -73.986389), 30.0, 130.0,
         "Broadway at West 44th Street, about 130 m north-north-east of the building, looking south-south-west at the setback clock tower and globe",
         geosearch_radius_m=250, gps_subject_max_m=1500,
         exclude=AERIAL_WORDS + ["los angeles", "hollywood", "studio lot", "oakland", "paramount pictures", "interior", "1930", "1940"]),
    _lmk("landmark_tkts_booth", "TKTS booth and red steps, Duffy Square",
         ['"TKTS" Duffy Square red steps', '"TKTS booth" Times Square'],
         [["tkts"]], (40.759, -73.9847), 190.0, 60.0,
         "Duffy Square about 60 m south of the booth, looking north at the red glass steps over the TKTS booth",
         geosearch_radius_m=200, gps_subject_max_m=800, min_year=2010,
         exclude=AERIAL_WORDS + ["new year", "ball drop", "protest", "london", "leicester square"]),
    _lmk("landmark_times_square_tower", "Times Square Tower (7 Times Square)",
         ['"Times Square Tower" 7 Times Square', '"7 Times Square" building'],
         [["times square tower", "7 times square", "seven times square"]], (40.7555, -73.9867), 20.0, 150.0,
         "Broadway at West 42nd Street, about 150 m north-north-east of the tower, looking south-south-west at Times Square Tower",
         geosearch_radius_m=250, gps_subject_max_m=1500,
         exclude=AERIAL_WORDS + ["interior", "under construction", "crane"]),
    _lmk("landmark_bank_of_america_tower", "Bank of America Tower at One Bryant Park",
         ['"Bank of America Tower" "One Bryant Park"', '"One Bryant Park" tower New York'],
         [["bank of america tower", "one bryant park"], ["new york", "manhattan", "bryant park", "sixth avenue"]],
         (40.75546, -73.98444), 250.0, 200.0,
         "Broadway at West 42nd Street, about 200 m west-south-west of the tower, looking east-north-east at the Bank of America Tower's crystalline crown",
         geosearch_radius_m=400, gps_subject_max_m=4000,
         exclude=AERIAL_WORDS + ["charlotte", "atlanta", "houston", "dallas", "seattle", "san francisco", "st. louis", "under construction", "interior"]),
    _lmk("landmark_marriott_marquis", "New York Marriott Marquis",
         ['"Marriott Marquis" Times Square hotel exterior', '"New York Marriott Marquis" Broadway'],
         [["marriott marquis"], ["new york", "times square", "broadway", "manhattan"]],
         (40.758611, -73.986111), 20.0, 150.0,
         "Broadway at West 47th Street, about 150 m north-north-east of the hotel, looking south-south-west at the Marriott Marquis front",
         geosearch_radius_m=250, gps_subject_max_m=1500,
         exclude=AERIAL_WORDS + ["atlanta", "san francisco", "san diego", "houston", "washington", "interior", "atrium", "lobby", "elevator"]),
    _lmk("landmark_new_york_times_building", "The New York Times Building (620 Eighth Avenue)",
         ['"New York Times Building" 620 Eighth Avenue', '"New York Times Building" Renzo Piano tower'],
         [["new york times building", "620 eighth avenue"]], (40.756111, -73.99), 250.0, 150.0,
         "Eighth Avenue at West 40th Street, about 150 m west-south-west of the tower, looking east-north-east at the ceramic-rod facade",
         geosearch_radius_m=350, gps_subject_max_m=3000,
         exclude=AERIAL_WORDS + ["one times square", "times tower", "1913", "interior", "newsroom", "under construction", "climber"]),
    _lmk("landmark_port_authority_bus_terminal", "Port Authority Bus Terminal",
         ['"Port Authority Bus Terminal" exterior', '"Port Authority Bus Terminal" Eighth Avenue'],
         [["port authority bus terminal"]], (40.756667, -73.991111), 250.0, 120.0,
         "Ninth Avenue at West 41st Street, about 120 m west-south-west of the terminal, looking east-north-east at the Port Authority Bus Terminal",
         geosearch_radius_m=350, gps_subject_max_m=2500,
         exclude=AERIAL_WORDS + ["interior", "gate", "concourse", "george washington bridge bus station", "newark"]),
    _lmk("landmark_hearst_tower", "Hearst Tower",
         ['"Hearst Tower" New York diagrid', '"Hearst Tower" 300 West 57th Street'],
         [["hearst tower", "hearst building"], ["new york", "manhattan", "eighth avenue", "57th"]],
         (40.7666, -73.9836), 200.0, 150.0,
         "Eighth Avenue at West 56th Street, about 150 m south-south-west of the tower, looking north-north-east at the diagrid above the Art Deco base",
         geosearch_radius_m=350, gps_subject_max_m=3000,
         exclude=AERIAL_WORDS + ["charlotte", "interior", "atrium", "lobby", "icefall"]),
    _lmk("landmark_citigroup_center", "Citigroup Center (601 Lexington Avenue)",
         ['"Citigroup Center" New York angled roof', '"601 Lexington Avenue" tower Citicorp'],
         [["citigroup center", "citicorp center", "601 lexington"]], (40.758611, -73.970278), 200.0, 200.0,
         "Lexington Avenue at East 52nd Street, about 200 m south-south-west of the tower, looking north-north-east at the angled crown of Citigroup Center",
         geosearch_radius_m=400, gps_subject_max_m=3000,
         exclude=AERIAL_WORDS + ["chicago", "interior", "atrium", "under construction", "st. peter's interior"]),
    _lmk("landmark_metlife_building", "MetLife Building (200 Park Avenue)",
         ['"MetLife Building" Park Avenue', '"Pan Am Building" 200 Park Avenue New York'],
         [["metlife building", "pan am building", "200 park avenue"]], (40.753333, -73.976667), 190.0, 300.0,
         "Park Avenue at East 45th Street south of the Helmsley Building, about 300 m south of the tower, looking north up Park Avenue at the MetLife Building",
         geosearch_radius_m=500, gps_subject_max_m=4000,
         exclude=AERIAL_WORDS + ["interior", "helicopter crash", "1963", "1970", "stadium"]),
    _lmk("landmark_lipstick_building", "Lipstick Building (885 Third Avenue)",
         ['"Lipstick Building" Third Avenue', '"885 Third Avenue" elliptical tower'],
         [["lipstick building", "885 third avenue"]], (40.757778, -73.968889), 200.0, 130.0,
         "Third Avenue at East 52nd Street, about 130 m south-south-west of the tower, looking north-north-east at the elliptical setbacks",
         geosearch_radius_m=300, gps_subject_max_m=2500, exclude=AERIAL_WORDS + ["interior", "lobby"]),
    _lmk("landmark_seagram_building", "Seagram Building (375 Park Avenue)",
         ['"Seagram Building" Park Avenue plaza', '"375 Park Avenue" Mies van der Rohe'],
         [["seagram building", "375 park avenue"]], (40.758611, -73.972222), 250.0, 120.0,
         "Park Avenue west sidewalk at East 52nd Street, about 120 m west-south-west of the tower, looking east-north-east across the Seagram plaza",
         geosearch_radius_m=300, gps_subject_max_m=2500,
         exclude=AERIAL_WORDS + ["interior", "four seasons restaurant", "montreal", "lobby"]),
    _lmk("landmark_lever_house", "Lever House (390 Park Avenue)",
         ['"Lever House" Park Avenue', '"Lever House" curtain wall New York'],
         [["lever house"]], (40.759722, -73.972778), 250.0, 100.0,
         "Park Avenue west sidewalk at East 54th Street, about 100 m west-south-west of the building, looking east-north-east at the green curtain wall over its plaza",
         geosearch_radius_m=300, gps_subject_max_m=2500, exclude=AERIAL_WORDS + ["interior", "lobby", "london", "port sunlight"]),

    # Group C - culture, museums, stadiums, outer boroughs
    _lmk("landmark_carnegie_hall", "Carnegie Hall",
         ['"Carnegie Hall" exterior Seventh Avenue', '"Carnegie Hall" building 57th Street'],
         [["carnegie hall"]], (40.7651, -73.9799), 210.0, 100.0,
         "Seventh Avenue at West 56th Street, about 100 m south-south-west of the building, looking north-north-east at the corner facade and marquee",
         geosearch_radius_m=250, gps_subject_max_m=2000,
         exclude=AERIAL_WORDS + ["interior", "auditorium", "stage", "concert", "pittsburgh", "dunfermline", "library"]),
    _lmk("landmark_st_john_the_divine", "Cathedral of St. John the Divine",
         ['"Cathedral of St. John the Divine" west front', '"St. John the Divine" Amsterdam Avenue cathedral'],
         [["john the divine"]], (40.803888, -73.96208), 260.0, 130.0,
         "Amsterdam Avenue at West 112th Street, about 130 m west of the cathedral, looking east at the west front and rose window",
         geosearch_radius_m=300, gps_subject_max_m=2000,
         exclude=AERIAL_WORDS + ["interior", "nave", "crossing", "peacock", "choir"]),
    _lmk("landmark_riverside_church", "Riverside Church",
         ['"Riverside Church" tower Riverside Drive', '"Riverside Church" New York exterior'],
         [["riverside church"]], (40.811944, -73.963056), 250.0, 130.0,
         "Riverside Drive at West 120th Street, about 130 m west-south-west of the church, looking east-north-east at the carillon tower",
         geosearch_radius_m=300, gps_subject_max_m=2000, exclude=AERIAL_WORDS + ["interior", "nave", "carillon bell", "organ"]),
    _lmk("landmark_arthur_ashe_stadium", "Arthur Ashe Stadium",
         ['"Arthur Ashe Stadium" exterior', '"Arthur Ashe Stadium" USTA Billie Jean King National Tennis Center'],
         [["arthur ashe"]], (40.749889, -73.847028), 300.0, 250.0,
         "the plaza north-west of the stadium at the USTA Billie Jean King National Tennis Center, about 250 m from it, looking south-east at Arthur Ashe Stadium",
         geosearch_radius_m=500, gps_subject_max_m=3000,
         exclude=AERIAL_WORDS + ["interior", "court", "match", "player", "serve", "trophy", "statue only"]),
    _lmk("landmark_domino_park", "Domino Park",
         ['"Domino Park" Williamsburg waterfront', '"Domino Park" East River esplanade Brooklyn'],
         [["domino park"]], (40.715, -73.967778), 300.0, 120.0,
         "the East River esplanade at the north end of Domino Park, about 120 m north-west of the park's centre, looking south-east along the elevated walkway",
         geosearch_radius_m=350, gps_subject_max_m=1500, min_year=2018,
         exclude=AERIAL_WORDS + ["interior", "night", "under construction"]),
    _lmk("landmark_kings_theatre", "Kings Theatre (Flatbush)",
         ['"Kings Theatre" Flatbush Brooklyn', '"Kings Theatre" Flatbush Avenue marquee'],
         [["kings theatre", "kings theater"], ["brooklyn", "flatbush", "new york"]],
         (40.6497, -73.9578), 250.0, 60.0,
         "Flatbush Avenue west sidewalk opposite the theatre, about 60 m from the front, looking east at the marquee and terracotta facade",
         geosearch_radius_m=250, gps_subject_max_m=1500, min_year=2014,
         exclude=AERIAL_WORDS + ["london", "hammersmith", "glasgow", "edinburgh", "southsea", "portsmouth", "interior", "auditorium", "lobby"]),
    _lmk("landmark_brooklyn_museum", "Brooklyn Museum",
         ['"Brooklyn Museum" Eastern Parkway entrance', '"Brooklyn Museum" building exterior'],
         [["brooklyn museum"]], (40.671306, -73.96375), 260.0, 130.0,
         "the Eastern Parkway sidewalk opposite the museum, about 130 m west of the entrance pavilion, looking east at the glass entrance and Beaux-Arts front",
         geosearch_radius_m=300, gps_subject_max_m=1500,
         exclude=AERIAL_WORDS + ["interior", "gallery", "exhibition", "mummy", "painting"]),
    _lmk("landmark_brooklyn_public_library", "Brooklyn Public Library, Central Library",
         ['"Brooklyn Public Library" Central Library Grand Army Plaza', '"Brooklyn Public Library" gilded entrance Art Deco'],
         [["brooklyn public library", "central library"], ["brooklyn", "grand army plaza", "eastern parkway"]],
         (40.6725, -73.9683), 320.0, 120.0,
         "Grand Army Plaza north-west of the library, about 120 m from the entrance, looking south-east at the gilded Art Deco portal",
         geosearch_radius_m=300, gps_subject_max_m=1500, exclude=AERIAL_WORDS + ["interior", "reading room", "stacks"]),
    _lmk("landmark_williamsburgh_savings_bank_tower", "Williamsburgh Savings Bank Tower (One Hanson Place)",
         ['"Williamsburgh Savings Bank Tower" Brooklyn', '"One Hanson Place" Brooklyn tower clock'],
         [["williamsburgh savings", "one hanson place", "1 hanson place"]], (40.685556, -73.977778), 200.0, 200.0,
         "Flatbush Avenue at Fourth Avenue, about 200 m south-south-west of the tower, looking north-north-east at the clock tower and dome",
         geosearch_radius_m=400, gps_subject_max_m=3000, exclude=AERIAL_WORDS + ["interior", "banking room", "1930", "1929"]),
    _lmk("landmark_pier_17", "Pier 17, South Street Seaport",
         ['"Pier 17" South Street Seaport building', '"Pier 17" Seaport rooftop East River'],
         [["pier 17"], ["seaport", "south street", "new york", "manhattan"]], (40.706, -74.002), 300.0, 150.0,
         "the South Street Seaport waterfront near Fulton Street, about 150 m north-west of the pier building, looking south-east at Pier 17",
         geosearch_radius_m=350, gps_subject_max_m=2000, min_year=2018,
         exclude=AERIAL_WORDS + ["interior", "concert", "1985", "1990", "old pavilion", "demolition"]),
    _lmk("landmark_whitehall_ferry_terminal", "Staten Island Ferry Whitehall Terminal",
         ['"Whitehall Terminal" Staten Island Ferry Manhattan', '"Whitehall Ferry Terminal" exterior'],
         [["whitehall terminal", "whitehall ferry terminal"], ["ferry", "staten island", "manhattan", "new york"]],
         (40.701409, -74.013131), 20.0, 150.0,
         "Whitehall Street at South Street, about 150 m north-north-east of the terminal, looking south-south-west at the Whitehall Terminal front",
         geosearch_radius_m=350, gps_subject_max_m=2000,
         exclude=AERIAL_WORDS + ["interior", "waiting room", "st. george", "1905", "1950"]),
    _lmk("landmark_st_george_ferry_terminal", "St. George Ferry Terminal",
         ['"St. George Terminal" Staten Island ferry', '"St. George Ferry Terminal" exterior Staten Island'],
         [["st. george terminal", "st george terminal", "st. george ferry", "st george ferry"]],
         (40.643333, -74.074167), 170.0, 150.0,
         "Bay Street south of the terminal, about 150 m away, looking north-north-west at the St. George Terminal front",
         geosearch_radius_m=350, gps_subject_max_m=2000,
         exclude=AERIAL_WORDS + ["interior", "waiting room", "whitehall", "bermuda", "utah", "grenada"]),
    _lmk("landmark_ny_state_pavilion", "New York State Pavilion",
         ['"New York State Pavilion" Flushing Meadows', '"Tent of Tomorrow" New York State Pavilion towers'],
         [["new york state pavilion", "state pavilion", "tent of tomorrow"], ["flushing meadows", "queens", "world's fair", "new york"]],
         (40.744028, -73.844417), 200.0, 150.0,
         "the Flushing Meadows path south-south-west of the pavilion, about 150 m away, looking north-north-east at the Tent of Tomorrow and observation towers",
         geosearch_radius_m=400, gps_subject_max_m=2000,
         exclude=AERIAL_WORDS + ["1964", "1965", "world's fair postcard", "interior", "restoration rendering"]),
    _lmk("landmark_queens_museum", "Queens Museum (New York City Building)",
         ['"Queens Museum" Flushing Meadows building', '"New York City Building" Flushing Meadows Queens Museum'],
         [["queens museum"]], (40.745833, -73.846667), 250.0, 120.0,
         "the Flushing Meadows walkway west-south-west of the museum, about 120 m away, looking east-north-east at the 1939 New York City Building",
         geosearch_radius_m=350, gps_subject_max_m=2000,
         exclude=AERIAL_WORDS + ["interior", "panorama", "gallery", "exhibition"]),
    _lmk("landmark_bronx_county_courthouse", "Bronx County Courthouse",
         ['"Bronx County Courthouse" Grand Concourse', '"Bronx County Building" courthouse exterior'],
         [["bronx county courthouse", "bronx county building"]], (40.826111, -73.924167), 250.0, 130.0,
         "the Grand Concourse at East 161st Street, about 130 m west-south-west of the building, looking east-north-east at the limestone facade and friezes",
         geosearch_radius_m=350, gps_subject_max_m=2000, exclude=AERIAL_WORDS + ["interior", "courtroom", "lobby"]),
    _lmk("landmark_little_island", "Little Island at Pier 55",
         ['"Little Island" Pier 55 Hudson River Park', '"Little Island" Manhattan tulip piles park'],
         [["little island"], ["pier 55", "hudson river park", "manhattan", "new york", "chelsea"]],
         (40.742, -74.01), 80.0, 200.0,
         "the Hudson River Park esplanade near West 13th Street, about 200 m east of the park, looking west at Little Island on its tulip-shaped piles",
         geosearch_radius_m=400, gps_subject_max_m=2000, min_year=2021,
         exclude=AERIAL_WORDS + ["under construction", "crane", "rendering", "night"]),
    _lmk("landmark_pier_57", "Pier 57 (Hudson River Park)",
         ['"Pier 57" Hudson River Park Manhattan', '"Pier 57" Chelsea Google building rooftop park'],
         [["pier 57"], ["manhattan", "new york", "hudson river", "chelsea"]], (40.7434, -74.0102), 60.0, 200.0,
         "the Hudson River Park esplanade near West 16th Street, about 200 m north-east of the pier, looking south-west at the Pier 57 shed",
         geosearch_radius_m=400, gps_subject_max_m=2000,
         exclude=AERIAL_WORDS + ["under construction", "crane", "rendering", "interior", "san francisco"]),
    _lmk("landmark_chelsea_market", "Chelsea Market",
         ['"Chelsea Market" Ninth Avenue building', '"Chelsea Market" Manhattan exterior brick'],
         [["chelsea market"]], (40.7425, -74.006111), 190.0, 100.0,
         "Ninth Avenue at West 15th Street, about 100 m south of the building, looking north at the Chelsea Market brick facade",
         geosearch_radius_m=300, gps_subject_max_m=1500,
         exclude=AERIAL_WORDS + ["interior", "concourse", "food hall", "inside", "london", "milan"]),
    _lmk("landmark_javits_center", "Jacob K. Javits Convention Center",
         ['"Javits Center" glass exterior Eleventh Avenue', '"Jacob K. Javits Convention Center" building'],
         [["javits"]], (40.7575, -74.0025), 110.0, 250.0,
         "Eleventh Avenue at West 36th Street, about 250 m east-south-east of the building, looking west-north-west at the space-frame glass wall",
         geosearch_radius_m=500, gps_subject_max_m=3000,
         exclude=AERIAL_WORDS + ["interior", "convention", "comic con", "auto show", "hospital", "vaccination"]),
    _lmk("landmark_moynihan_train_hall", "Moynihan Train Hall",
         ['"Moynihan Train Hall" exterior Farley Building', '"Moynihan Train Hall" Eighth Avenue entrance'],
         [["moynihan"]], (40.751111, -73.995278), 250.0, 130.0,
         "Ninth Avenue at West 32nd Street, about 130 m west-south-west of the building, looking east-north-east at the Moynihan entrance in the Farley Post Office",
         geosearch_radius_m=350, gps_subject_max_m=2000, min_year=2021,
         exclude=AERIAL_WORDS + ["under construction", "rendering", "penn station platform"]),
    _lmk("landmark_rose_center", "Rose Center for Earth and Space",
         ['"Rose Center for Earth and Space" glass cube', '"Hayden Planetarium" Rose Center exterior'],
         [["rose center", "hayden planetarium"]], (40.781536, -73.973247), 290.0, 130.0,
         "Columbus Avenue at West 81st Street, about 130 m west-north-west of the building, looking east-south-east at the glass cube",
         geosearch_radius_m=300, gps_subject_max_m=1500,
         exclude=AERIAL_WORDS + ["interior", "sphere inside", "show", "exhibit", "meteorite"]),
    # ---------------------------------------------------------------- 10 generic streetscapes
    _it("street_tenement_fire_escapes_les", "Tenement with fire escapes (East Village / Lower East Side)", "streetscape",
        ['tenement "fire escape" "Lower East Side"', '"East Village" tenement fire escapes', '"Orchard Street" Lower East Side tenement'],
        [["tenement", "fire escape", "orchard street", "lower east side", "east village"], ["manhattan", "new york", "lower east side", "east village"]],
        (40.7200, -73.9887), "Orchard Street at Rivington Street, roadway centre, looking north (representative block)",
        azimuth=UPTOWN, geosearch_radius_m=400, representative=True,
        exclude=AERIAL_WORDS + ["museum interior", "interior", "inside", "night", "1900", "1930", "chicago", "san francisco", "hoboken"]),
    _it("street_soho_cast_iron", "SoHo cast-iron block", "streetscape",
        ['SoHo "cast-iron" building Greene Street', '"SoHo Cast Iron Historic District" street'],
        [["soho", "greene street", "cast-iron", "cast iron"], ["manhattan", "new york", "soho"]],
        (40.7218, -74.0020), "Greene Street at Grand Street, roadway centre, looking north (representative block)",
        azimuth=UPTOWN, geosearch_radius_m=400, representative=True,
        exclude=AERIAL_WORDS + ["night", "interior", "inside", "london", "hong kong"]),
    _it("street_nycha_tower_campus", "NYCHA tower-in-the-park campus", "streetscape",
        ['NYCHA houses towers "New York City Housing Authority"', '"Alfred E. Smith Houses"', '"Queensbridge Houses"'],
        [["nycha", "housing authority", "houses"]],
        (40.7098, -73.9990), "South Street at the Brooklyn Bridge approach, looking north at the Alfred E. Smith Houses (representative campus)",
        subject=(40.7115, -73.9985), subject_name="Alfred E. Smith Houses", geosearch_radius_m=400, representative=True, gps_subject_max_m=3000,
        exclude=AERIAL_WORDS + ["night", "interior", "inside", "1940", "1950", "rendering", "plan"]),
    _it("street_queens_vinyl_siding", "Queens vinyl-sided houses", "streetscape",
        ['Queens "vinyl siding" house', '"Woodside, Queens" houses street', '"Ridgewood, Queens" houses', 'Astoria Queens detached house siding'],
        [["queens", "woodside", "ridgewood", "astoria", "maspeth", "glendale", "middle village", "elmhurst", "corona"]],
        (40.7440, -73.9060), "60th Street near 39th Avenue, Woodside, looking north (representative block)",
        azimuth=0.0, representative=True,
        exclude=AERIAL_WORDS + ["night", "interior", "inside", "subway", "station", "train", "church", "school", "cemetery"]),
    _it("street_staten_island_ranch_houses", "Staten Island ranch houses", "streetscape",
        ['"Staten Island" ranch house street', '"Staten Island" suburban houses New Dorp', '"Staten Island" residential street houses Great Kills'],
        [["staten island"]],
        (40.5480, -74.1450), "Great Kills / New Dorp Beach residential street, looking north (representative block)",
        azimuth=0.0, representative=True,
        exclude=AERIAL_WORDS + ["ferry", "night", "interior", "inside", "church", "school", "fort", "beach", "boardwalk", "zoo", "mall", "landfill", "bridge", "1900", "mansion", "victorian", "historic"]),
    _it("street_elevated_roosevelt_ave_7", "Elevated subway street: Roosevelt Avenue under the 7", "streetscape",
        ['"Roosevelt Avenue" elevated 7 train Jackson Heights street', '"Roosevelt Avenue" under the elevated Queens'],
        [["roosevelt avenue", "roosevelt ave"], ["queens", "jackson heights", "woodside", "corona", "elmhurst", "flushing", "sunnyside", "74th", "82nd", "90th", "103rd"]],
        (40.7466, -73.8912), "Roosevelt Avenue at 74th Street, roadway centre under the 7 train structure, looking east",
        azimuth=75.0, geosearch_radius_m=500,
        exclude=["night", "platform", "mezzanine", "interior", "inside", "1917", "1920"]),
    _it("street_elevated_broadway_bushwick_j", "Elevated subway street: Broadway (Brooklyn) under the J", "streetscape",
        ['"Broadway" Bushwick elevated J train street', '"Broadway" Brooklyn elevated BMT Jamaica Line street level'],
        [["broadway"], ["bushwick", "bedford", "brooklyn", "jamaica line", "myrtle", "kosciuszko", "gates avenue", "halsey"]],
        (40.6978, -73.9355), "Broadway at Myrtle Avenue, Bushwick, roadway centre under the J/M/Z structure, looking south-east",
        azimuth=127.0, geosearch_radius_m=600,
        exclude=["night", "platform", "mezzanine", "interior", "inside", "manhattan", "1900", "1910", "1920"]),
    _it("street_midtown_avenue_rush_hour", "Midtown avenue at rush hour", "streetscape",
        ['Manhattan avenue traffic rush hour taxis', 'Midtown Manhattan street traffic taxis pedestrians avenue'],
        [["manhattan", "midtown", "avenue"], ["traffic", "rush hour", "taxis", "cabs", "crowd", "pedestrians"]],
        (40.7576, -73.9866), "Seventh Avenue at West 44th Street, roadway centre, looking downtown (representative avenue)",
        azimuth=DOWNTOWN, representative=True,
        exclude=AERIAL_WORDS + ["night", "1970", "1980", "1990", "protest", "parade", "marathon"]),
    _it("street_times_square_wet_night", "Times Square on a wet night", "streetscape",
        ['"Times Square" rain night', '"Times Square" rainy night reflections wet'],
        [["times square"], ["rain", "wet", "rainy", "umbrella", "reflection", "puddle"]],
        (40.7568, -73.9862), "Broadway at West 44th Street, roadway centre, looking north up the bowtie",
        azimuth=UPTOWN, geosearch_radius_m=200, night=True, min_year=2012),
    _it("street_brooklyn_snow", "Snow on a Brooklyn street", "streetscape",
        ['Brooklyn snow street brownstones', '"Park Slope" snow street', '"Bedford-Stuyvesant" snow street'],
        [["brooklyn"], ["snow", "blizzard", "snowstorm", "winter storm", "nor'easter"]],
        (40.6770, -73.9800), "Park Slope side street (5th Street at Seventh Avenue), looking north-east (representative block)",
        azimuth=30.0, representative=True,
        exclude=AERIAL_WORDS + ["night", "prospect park", "1888", "1947", "1996", "coney island", "beach", "bridge"]),
    _it("street_nyc_street_name_signs", "NYC street name signs (close-ups)", "streetscape",
        ['New York City street name sign green blade', '"street sign" Manhattan intersection green blade'],
        [["street sign", "street name sign", "street signs", "signpost", "one way sign"], NYC_WORDS],
        (40.7550, -73.9840), "typical Midtown intersection corner (representative; close-up references, not a view)",
        azimuth=0.0, representative=True, want=4,
        exclude=["night", "1950", "1960", "subway sign", "station sign", "poster", "map", "mural", "traffic light", "protest"]),
    _it("street_nyc_traffic_signals", "NYC traffic signals and pedestrian signals (close-ups)", "streetscape",
        ['New York City traffic light signal mast arm', 'New York City pedestrian signal countdown walk'],
        [["traffic light", "traffic signal", "pedestrian signal", "walk signal", "countdown signal", "signal head"], NYC_WORDS],
        (40.7550, -73.9840), "typical Midtown intersection corner (representative; close-up references, not a view)",
        azimuth=0.0, representative=True, want=4,
        exclude=["night", "1950", "1960", "subway", "station", "poster", "map", "mural", "railway signal", "railroad signal", "protest"]),
    _it("street_fire_hydrant", "NYC fire hydrant (close-up)", "streetscape",
        ['New York City fire hydrant', 'fire hydrant Manhattan sidewalk'],
        [["hydrant"], NYC_WORDS],
        (40.7550, -73.9840), "Midtown sidewalk (representative; close-up reference, not a view)",
        azimuth=0.0, representative=True, want=2, exclude=["night", "patent"]),
    _it("street_linknyc_kiosk", "LinkNYC kiosk (close-up)", "streetscape",
        ['LinkNYC kiosk', 'LinkNYC Link kiosk sidewalk Manhattan'],
        [["linknyc", "link nyc"]],
        (40.7550, -73.9840), "Midtown sidewalk (representative; close-up reference, not a view)",
        azimuth=0.0, representative=True, min_year=2016,
        exclude=["night", "interior", "rendering", "render", "logo", "screenshot", "map"]),
    _it("street_newsstand", "NYC newsstand (close-up)", "streetscape",
        ['New York City newsstand sidewalk', 'newsstand Manhattan sidewalk Cemusa'],
        [["newsstand", "news stand", "newspaper stand"], NYC_WORDS],
        (40.7550, -73.9840), "Midtown sidewalk (representative; close-up reference, not a view)",
        azimuth=0.0, representative=True, exclude=["night", "interior", "1930", "1940", "1950", "1960", "1970", "1980"]),
    _it("street_sidewalk_shed", "Sidewalk shed (scaffolding)", "streetscape",
        ['"sidewalk shed" New York scaffolding', 'scaffolding sidewalk shed Manhattan sidewalk'],
        [["sidewalk shed", "scaffold", "scaffolding", "sidewalk bridge"], NYC_WORDS],
        (40.7550, -73.9840), "Midtown sidewalk under a shed (representative; close-up reference, not a view)",
        azimuth=0.0, representative=True, exclude=["night", "collapse", "rendering"] + AERIAL_WORDS),
    # ---------------------------------------------------------------- vehicles
    _it("vehicle_yellow_cab", "NYC yellow cab", "vehicle",
        ['New York City taxi yellow cab Toyota Camry', 'NYC yellow taxi cab street Toyota', 'New York yellow cab Nissan NV200 Taxi of Tomorrow'],
        [["taxi", "cab"], NYC_WORDS],
        (40.7550, -73.9840), "Midtown street (representative; vehicle reference, viewpoint not meaningful)",
        azimuth=0.0, representative=True, want=4, min_year=2014,
        exclude=["night", "checker", "crown victoria", "toy", "model", "medallion", "logo", "interior", "meter"]),
    _it("vehicle_mta_bus", "MTA New York City Bus", "vehicle",
        ['MTA New York City Bus New Flyer XD40', 'MTA bus Nova Bus LFS New York City Transit', 'MTA New York City Bus street'],
        [["mta", "new york city bus", "new york city transit", "nyct"], ["bus"]],
        (40.7550, -73.9840), "Midtown street (representative; vehicle reference, viewpoint not meaningful)",
        azimuth=0.0, representative=True, want=4, min_year=2014,
        exclude=["night", "interior", "inside", "depot", "rts", "orion", "toy", "model", "bus terminal", "greyhound", "school bus", "tour bus", "double-decker", "map", "logo"]),
    _it("vehicle_nypd_car", "NYPD patrol car", "vehicle",
        ['NYPD Ford Explorer police car', 'NYPD police car Ford Police Interceptor Utility', 'NYPD patrol car street Manhattan'],
        [["nypd", "new york city police", "new york police"]],
        (40.7550, -73.9840), "Midtown street (representative; vehicle reference, viewpoint not meaningful)",
        azimuth=0.0, representative=True, want=4, min_year=2014,
        exclude=["night", "crown victoria", "impala", "toy", "model", "helicopter", "boat", "horse", "motorcycle", "van", "truck", "smart car", "badge", "patch", "logo", "officer portrait", "funeral", "protest"]),
    _it("vehicle_fdny_engine", "FDNY engine (pumper)", "vehicle",
        ['FDNY engine Seagrave pumper', 'FDNY fire engine Seagrave street', 'FDNY Engine Company apparatus'],
        [["fdny", "new york city fire department", "new york fire department"], ["engine", "pumper"]],
        (40.7550, -73.9840), "Midtown street (representative; vehicle reference, viewpoint not meaningful)",
        azimuth=0.0, representative=True, want=4, min_year=2012,
        exclude=["night", "antique", "museum", "toy", "model", "fireboat", "ambulance", "helmet", "patch", "logo", "badge", "1900", "1920", "1930", "1940", "1950", "1960", "1970", "1980", "1990", "funeral", "9/11", "september 11"]),
]

_SLUGS = [i.slug for i in CATALOGUE]
if len(set(_SLUGS)) != len(_SLUGS):
    raise RuntimeError("duplicate slug in CATALOGUE")
BY_SLUG: dict[str, Item] = {i.slug: i for i in CATALOGUE}


# ----------------------------------------------------------------------------------------------
# Small pure helpers (unit-tested)
# ----------------------------------------------------------------------------------------------

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def strip_html(s: Any) -> str:
    """Plain text from an extmetadata value.

    Commons returns most values as strings, but multilingual fields can still arrive as a
    ``{"en": "...", "fr": "..."}`` map (or a list of such) even with ``multilang=0``, so
    normalise anything that is not a string before stripping tags.
    """
    if s is None or s == "":
        return ""
    if isinstance(s, dict):
        for key in ("en", "value", "_"):
            if s.get(key):
                return strip_html(s[key])
        for v in s.values():
            if v:
                return strip_html(v)
        return ""
    if isinstance(s, (list, tuple)):
        parts = [strip_html(v) for v in s]
        return " | ".join(p for p in parts if p)
    if not isinstance(s, str):
        s = str(s)
    return _WS_RE.sub(" ", html.unescape(_TAG_RE.sub(" ", s))).strip()


def haversine_m(a: tuple[float, float], b: tuple[float, float]) -> float:
    r = 6371008.8
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


def bearing_deg(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Initial great-circle bearing from a to b, compass degrees (0 = north, clockwise)."""
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    dlon = lo2 - lo1
    x = math.sin(dlon) * math.cos(la2)
    y = math.cos(la1) * math.sin(la2) - math.sin(la1) * math.cos(la2) * math.cos(dlon)
    return (math.degrees(math.atan2(x, y)) + 360.0) % 360.0


_LICENSE_OK_RE = re.compile(r"^(CC0(?: 1\.0)?|CC BY \d\.\d(?: [a-z]{2,3}(?:-[a-z]+)?)?|CC BY-SA \d\.\d(?: [a-z]{2,3}(?:-[a-z]+)?)?|Public domain)$", re.I)


def licence_ok(short_name: str | None, template: str | None = None) -> bool:
    """CC0, CC BY x.y, CC BY-SA x.y (any port) or Public domain. Everything else (NC, ND, GFDL-only,
    'Copyrighted free use', 'Attribution' without CC) is rejected."""
    s = strip_html(short_name)
    if not s or not _LICENSE_OK_RE.match(s):
        return False
    if s.lower() == "public domain":
        t = (template or "").lower()
        # a PD short name backed by a non-PD template (e.g. a mis-tagged NC file) is not trusted
        return t == "" or t.startswith("pd") or t.startswith("cc0") or "public domain" in t
    return True


def licence_url(short_name: str, url: str | None) -> str:
    if url:
        return url.split("?", 1)[0]
    s = short_name.lower()
    if s.startswith("cc0"):
        return "https://creativecommons.org/publicdomain/zero/1.0/"
    m = re.match(r"cc by(-sa)? (\d\.\d)", s)
    if m:
        return f"https://creativecommons.org/licenses/by{'-sa' if m.group(1) else ''}/{m.group(2)}/"
    return "https://commons.wikimedia.org/wiki/Commons:Licensing#Material_in_the_public_domain"


_DATE_FULL_RE = re.compile(r"(\d{4})[-:](\d{2})[-:](\d{2})(?:[ T](\d{2}):(\d{2})(?::(\d{2}))?)?")
_DATE_YM_RE = re.compile(r"\b(\d{4})-(\d{2})\b")
_YEAR_RE = re.compile(r"\b(1[89]\d{2}|20\d{2})\b")


def parse_date(raw: str | None) -> tuple[str | None, int | None]:
    """Return (ISO-ish date string, year) from a Commons date field (may contain HTML, EXIF colons,
    'circa 1900', month names). Unparseable -> (None, None)."""
    t = strip_html(raw)
    if not t:
        return None, None
    m = _DATE_FULL_RE.search(t)
    if m:
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if 1826 <= y <= 2100 and 1 <= mo <= 12 and 1 <= d <= 31:
            s = f"{y:04d}-{mo:02d}-{d:02d}"
            if m.group(4):
                s += f" {m.group(4)}:{m.group(5)}" + (f":{m.group(6)}" if m.group(6) else "")
            return s, y
    m = _DATE_YM_RE.search(t)
    if m and 1 <= int(m.group(2)) <= 12 and 1826 <= int(m.group(1)) <= 2100:
        return f"{m.group(1)}-{m.group(2)}", int(m.group(1))
    m = _YEAR_RE.search(t)
    if m:
        return m.group(1), int(m.group(1))
    return None, None


def clean_url(u: str | None) -> str:
    return (u or "").split("?", 1)[0]


_ORIG_RE = re.compile(r"^(https://upload\.wikimedia\.org/wikipedia/commons)/([0-9a-f])/([0-9a-f]{2})/([^/?]+)$")


def thumb_url(original_url: str, width: int) -> str:
    """Build the server-side scaled rendition URL for a Commons original (width in px)."""
    m = _ORIG_RE.match(clean_url(original_url))
    if not m:
        raise ValueError(f"not a Commons original URL: {original_url}")
    base, a, ab, name = m.groups()
    return f"{base}/thumb/{a}/{ab}/{name}/{width}px-{name}"


def thumb_widths(max_width: int, original_width: int, min_width: int = 0) -> list[int]:
    """Thumbnail widths worth requesting for this file, largest first.

    Two server-side constraints shape this list:

    * upload.wikimedia.org renders only the standard "bucket" widths and answers any other width
      with HTTP 400 ("Use thumbnail sizes listed on https://w.wiki/GHai"), so an arbitrary
      ``--max-width`` has to be rounded down to a bucket;
    * original-resolution files are rate-limited hard for unauthenticated clients (HTTP 429 with
      ``Retry-After: 600``), so a rendition is requested even when the original is already within
      ``max_width``. The original is only a last resort, for a file too narrow to have a usable
      bucket below it.
    """
    ceiling = min(max_width, original_width - 1)
    return sorted((w for w in THUMB_BUCKETS if min_width <= w <= ceiling), reverse=True)


def _term_re(term: str) -> re.Pattern[str]:
    return re.compile(r"(?<![a-z0-9])" + re.escape(term.lower()) + r"(?![a-z0-9])")


_TERM_CACHE: dict[str, re.Pattern[str]] = {}


def has_term(hay: str, term: str) -> bool:
    p = _TERM_CACHE.get(term)
    if p is None:
        p = _TERM_CACHE[term] = _term_re(term)
    return p.search(hay) is not None


# ----------------------------------------------------------------------------------------------
# Candidates
# ----------------------------------------------------------------------------------------------

@dataclass
class Candidate:
    title: str
    pageid: int
    url: str
    page_url: str
    width: int
    height: int
    mime: str
    bytes: int
    author: str
    credit: str
    license_short: str
    license_url: str
    license_template: str
    date_taken: str | None
    date_source: str
    year: int | None
    gps: tuple[float, float] | None
    description: str
    object_name: str
    categories: list[str]
    assessments: str
    restrictions: str
    provenance: str
    geo_hit: bool = False
    score: float = 0.0

    @property
    def haystack(self) -> str:
        return " | ".join([self.title, self.object_name, self.description, " | ".join(self.categories)]).lower()


def parse_candidate(page: dict[str, Any], provenance: str, geo_hit: bool = False) -> Candidate | None:
    infos = page.get("imageinfo") or []
    if page.get("missing") or not infos:
        return None
    ii = infos[0]
    ext = {k: (v.get("value") if isinstance(v, dict) else v) for k, v in (ii.get("extmetadata") or {}).items()}
    date_taken, year = parse_date(strip_html(ext.get("DateTimeOriginal")))
    date_source = "DateTimeOriginal"
    if date_taken is None:
        date_taken, year = parse_date(strip_html(ext.get("DateTime")))
        date_source = "DateTime(file)" if date_taken else "none"
    gps = None
    lat_s, lon_s = strip_html(ext.get("GPSLatitude")), strip_html(ext.get("GPSLongitude"))
    try:
        if lat_s and lon_s:
            gps = (float(lat_s), float(lon_s))
            if not (-90.0 <= gps[0] <= 90.0 and -180.0 <= gps[1] <= 180.0):
                gps = None
    except (TypeError, ValueError):
        gps = None
    author = strip_html(ext.get("Artist"))
    credit = strip_html(ext.get("Credit"))
    if not author:
        author = credit or "unknown (see file page)"
    short = strip_html(ext.get("LicenseShortName"))
    cats = [c.strip() for c in strip_html(ext.get("Categories")).split("|") if c.strip()]
    return Candidate(
        title=page["title"], pageid=int(page.get("pageid") or 0), url=clean_url(ii.get("url")),
        page_url=clean_url(ii.get("descriptionurl")) or "https://commons.wikimedia.org/wiki/" + page["title"].replace(" ", "_"),
        width=int(ii.get("width") or 0), height=int(ii.get("height") or 0), mime=ii.get("mime") or "", bytes=int(ii.get("size") or 0),
        author=author[:300], credit=credit[:300], license_short=short, license_url=licence_url(short, ext.get("LicenseUrl")) if short else "",
        license_template=strip_html(ext.get("License")), date_taken=date_taken, date_source=date_source, year=year, gps=gps,
        description=strip_html(ext.get("ImageDescription"))[:2000], object_name=strip_html(ext.get("ObjectName")), categories=cats,
        assessments=strip_html(ext.get("Assessments")), restrictions=strip_html(ext.get("Restrictions")), provenance=provenance, geo_hit=geo_hit,
    )


def evaluate(item: Item, c: Candidate, min_width: int = MIN_USABLE_WIDTH) -> tuple[float | None, str]:
    """Return (score, reason). score None => rejected, reason names the rule."""
    if c.mime != "image/jpeg":
        return None, "not_jpeg"
    if not licence_ok(c.license_short, c.license_template):
        return None, "licence"
    if c.width < min_width or c.height < 500:
        return None, "too_small"
    hay = c.haystack
    for w in NOT_PHOTO_WORDS:
        if has_term(hay, w):
            return None, f"not_photo:{w}"
    if any("black and white" in cat.lower() for cat in c.categories):
        return None, "not_photo:b&w category"
    for w in item.exclude:
        if has_term(hay, w):
            return None, f"excluded:{w}"
    if not item.interior:
        for w in INDOOR_WORDS:
            if has_term(hay, w) and w not in item.allow:
                return None, f"indoor:{w}"
    for group in item.keywords:
        if not any(has_term(hay, k) for k in group):
            return None, "keywords"
    night_hit = any(has_term(hay, w) for w in NIGHT_WORDS)
    if night_hit and not item.night:
        return None, "night_for_day_item"
    if c.year is not None and c.year < item.min_year:
        return None, f"too_old:{c.year}"
    score = 0.0
    if c.year is None:
        score -= 1.0
    elif c.year >= 2015:
        score += 4.0 + min(c.year - 2015, 8) * 0.15  # newest wins ties
    elif c.year >= 2010:
        score += 1.0
    if c.width >= 2000:
        score += 1.5
    elif c.width >= 1200:
        score += 0.5
    hits = sum(1 for group in item.keywords for k in group if has_term(hay, k))
    score += min(hits, 3)
    if c.geo_hit:
        score += 3.0
    if c.gps is not None:
        score += 0.5
        d = haversine_m(c.gps, item.viewpoint)
        if item.geosearch_radius_m and d <= 1.5 * item.geosearch_radius_m:
            score += 2.0
    if c.assessments:
        score += 1.5
    if item.night:
        score += 2.0 if night_hit else -1.0
    if any(has_term(hay, w) for w in DAWN_WORDS) and not item.night:
        score -= 3.0
    if any(has_term(hay, w) for w in AERIAL_WORDS):
        score -= 4.0
    if any(has_term(hay, w) for w in PEOPLE_WORDS):
        score -= 3.0
    aspect = c.width / max(c.height, 1)
    if aspect > 3.0 or has_term(hay, "panorama") or has_term(hay, "panoramic"):
        score -= 2.0
    if "commons:featured pictures" in hay or "quality images" in hay or "valued images" in hay:
        score += 1.0
    return score, "ok"


def estimate_view(item: Item, c: Candidate) -> dict[str, Any]:
    """Estimated photographer position (WGS84) and azimuth for one photo, with the reasoning."""
    default_az = item.default_azimuth
    subj_txt = f"{item.subject_name} ({item.subject[0]:.5f}, {item.subject[1]:.5f})" if item.subject else None
    if c.gps is not None:
        d_vp = haversine_m(c.gps, item.viewpoint)
        if item.subject is not None:
            d_subj = haversine_m(c.gps, item.subject)
            if d_subj < 20.0:
                return {
                    "lat": item.viewpoint[0], "lon": item.viewpoint[1], "azimuth_deg": round(default_az, 1), "confidence": "medium",
                    "method": "standard_viewpoint (camera GPS coincides with subject)",
                    "explanation": (f"The file's GPS ({c.gps[0]:.5f}, {c.gps[1]:.5f}) lies within {d_subj:.0f} m of {subj_txt}, so the uploader "
                                    f"geotagged the subject rather than the camera; the viewpoint is therefore the standard photographer position "
                                    f"for this view ({item.viewpoint_note}) and the azimuth {default_az:.0f} deg is the bearing from there to the subject."),
                }
            if d_subj <= item.gps_subject_max_m:
                az = bearing_deg(c.gps, item.subject)
                return {
                    "lat": c.gps[0], "lon": c.gps[1], "azimuth_deg": round(az, 1), "confidence": "high", "method": "camera_gps_to_subject",
                    "explanation": (f"Camera GPS from the Commons file description ({c.gps[0]:.5f}, {c.gps[1]:.5f}) is {d_subj:.0f} m from {subj_txt} "
                                    f"and {d_vp:.0f} m from the standard viewpoint; the azimuth {az:.0f} deg is the initial great-circle bearing from "
                                    f"that camera position to the subject."),
                }
            return {
                "lat": item.viewpoint[0], "lon": item.viewpoint[1], "azimuth_deg": round(default_az, 1), "confidence": "medium",
                "method": "standard_viewpoint (camera GPS implausibly far)",
                "explanation": (f"The file carries GPS ({c.gps[0]:.5f}, {c.gps[1]:.5f}) but it is {d_subj / 1000:.1f} km from {subj_txt}, beyond the "
                                f"{item.gps_subject_max_m / 1000:.1f} km plausibility limit for this view, so it is ignored; the viewpoint is the "
                                f"standard photographer position ({item.viewpoint_note}) and the azimuth {default_az:.0f} deg is the bearing from there to the subject."),
            }
        # explicit-azimuth item (view along a street or a generic subject)
        conf = "low" if item.representative else "medium"
        return {
            "lat": c.gps[0], "lon": c.gps[1], "azimuth_deg": round(default_az, 1), "confidence": conf, "method": "camera_gps_with_item_azimuth",
            "explanation": (f"Camera GPS from the Commons file description ({c.gps[0]:.5f}, {c.gps[1]:.5f}), {d_vp:.0f} m from the reference position "
                            f"({item.viewpoint_note}); this item is a view along a street rather than at a point subject, so the azimuth {default_az:.0f} deg "
                            f"is the street heading of the reference view, not derived from the photo."
                            + (" The subject is generic, so the position is only representative of where such a photo is taken." if item.representative else "")),
        }
    conf = "low" if item.representative else "medium"
    if item.subject is not None:
        why = f"the azimuth {default_az:.0f} deg is the bearing from there to {subj_txt}"
    else:
        why = f"the azimuth {default_az:.0f} deg is the heading of the street/view axis at that position"
    return {
        "lat": item.viewpoint[0], "lon": item.viewpoint[1], "azimuth_deg": round(default_az, 1), "confidence": conf, "method": "standard_viewpoint",
        "explanation": (f"No camera GPS in the file metadata; the viewpoint is the standard photographer position for this view ({item.viewpoint_note}) and {why}."
                        + (" The subject is generic, so this position is representative of the type of scene, not where this specific photo was taken." if item.representative else "")),
    }


# ----------------------------------------------------------------------------------------------
# HTTP client (rate-limited, retrying)
# ----------------------------------------------------------------------------------------------

class CommonsError(RuntimeError):
    pass


class Client:
    def __init__(self, session: requests.Session | None = None, min_interval: float = MIN_INTERVAL_S, timeout: int = 60, attempts: int = 6):
        self.s = session or requests.Session()
        self.s.headers["User-Agent"] = USER_AGENT
        self.min_interval = min_interval
        self.timeout = timeout
        self.attempts = attempts
        self._last = 0.0
        self.requests_made = 0

    def _wait(self) -> None:
        dt = time.monotonic() - self._last
        if dt < self.min_interval:
            time.sleep(self.min_interval - dt)
        self._last = time.monotonic()
        self.requests_made += 1

    @staticmethod
    def _retry_after(r: requests.Response, attempt: int) -> float:
        ra = r.headers.get("Retry-After")
        if ra:
            try:
                return min(float(ra), 120.0)
            except ValueError:
                pass
        return min(2.0 ** (attempt + 1), 60.0)

    def api(self, **params: Any) -> dict[str, Any]:
        params.update(format="json", formatversion=2, maxlag=5)
        last: str = ""
        for attempt in range(self.attempts):
            self._wait()
            try:
                r = self.s.get(API_URL, params=params, timeout=self.timeout, verify=CA_BUNDLE)
            except requests.RequestException as e:
                last = f"network: {e}"
                log.warning("api attempt %d failed: %s", attempt + 1, e)
                time.sleep(min(2.0 ** (attempt + 1), 60.0))
                continue
            if r.status_code in (429, 500, 502, 503, 504):
                wait = self._retry_after(r, attempt)
                last = f"HTTP {r.status_code}"
                log.warning("api HTTP %d, waiting %.0fs", r.status_code, wait)
                time.sleep(wait)
                continue
            if r.status_code >= 400:
                raise CommonsError(f"HTTP {r.status_code}: {r.text[:200]}")
            try:
                doc = r.json()
            except ValueError as e:
                raise CommonsError(f"non-JSON API response: {e}") from e
            if "error" in doc:
                code = doc["error"].get("code")
                if code == "maxlag":
                    wait = self._retry_after(r, attempt)
                    log.warning("maxlag, waiting %.0fs", wait)
                    time.sleep(wait)
                    last = "maxlag"
                    continue
                raise CommonsError(f"API error {code}: {doc['error'].get('info')}")
            return doc
        raise CommonsError(f"giving up on API call after {self.attempts} attempts ({last})")

    def get_bytes(self, url: str, max_wait_s: float = 90.0) -> bytes | None:
        """Download a file.

        Returns None when the rendition is not available (HTTP 400/404) or when the server asks
        for a back-off longer than ``max_wait_s`` -- the caller then tries a smaller rendition or
        another candidate instead of blocking the whole run. Other failures raise ``CommonsError``.
        """
        last = ""
        for attempt in range(self.attempts):
            self._wait()
            try:
                with self.s.get(url, stream=True, timeout=self.timeout, verify=CA_BUNDLE) as r:
                    if r.status_code in (400, 404):
                        # 404: no such rendition. 400: a thumbnail width the servers refuse to
                        # render. Both mean "try something else", not "the run is broken".
                        return None
                    if r.status_code in (429, 500, 502, 503, 504):
                        wait = self._retry_after(r, attempt)
                        last = f"HTTP {r.status_code}"
                        if wait > max_wait_s:
                            log.warning("download HTTP %d asks for a %.0fs back-off, giving this file up: %s",
                                        r.status_code, wait, url)
                            return None
                        log.warning("download HTTP %d, waiting %.0fs", r.status_code, wait)
                        time.sleep(wait)
                        continue
                    if r.status_code >= 400:
                        raise CommonsError(f"HTTP {r.status_code} for {url}")
                    buf = io.BytesIO()
                    n = 0
                    for chunk in r.iter_content(chunk_size=1 << 18):
                        if chunk:
                            n += len(chunk)
                            if n > MAX_DOWNLOAD_BYTES:
                                raise CommonsError(f"file exceeds {MAX_DOWNLOAD_BYTES} bytes: {url}")
                            buf.write(chunk)
                    expected = r.headers.get("Content-Length")
                    if expected and int(expected) != n:
                        last = f"short read {n} != {expected}"
                        log.warning("%s for %s", last, url)
                        continue
                    if n == 0:
                        last = "empty body"
                        continue
                    return buf.getvalue()
            except requests.RequestException as e:
                last = f"network: {e}"
                log.warning("download attempt %d failed: %s", attempt + 1, e)
                time.sleep(min(2.0 ** (attempt + 1), 60.0))
        raise CommonsError(f"giving up on {url} ({last})")


# ----------------------------------------------------------------------------------------------
# Search / imageinfo
# ----------------------------------------------------------------------------------------------

def search_titles(client: Client, query: str, sort: str = "relevance", limit: int = 50) -> list[str]:
    doc = client.api(action="query", list="search", srsearch=f"{query} filemime:image/jpeg", srnamespace=6, srlimit=limit,
                     srsort=sort, srinfo="", srprop="")
    return [h["title"] for h in doc.get("query", {}).get("search", []) if h.get("title", "").startswith("File:")]


def geosearch_titles(client: Client, lat: float, lon: float, radius_m: int, limit: int = 100) -> list[str]:
    doc = client.api(action="query", list="geosearch", gscoord=f"{lat}|{lon}", gsradius=min(max(radius_m, 10), 10000),
                     gsnamespace=6, gslimit=min(limit, 500), gsprimary="primary")
    return [h["title"] for h in doc.get("query", {}).get("geosearch", []) if h.get("title", "").startswith("File:")]


def fetch_imageinfo(client: Client, titles: list[str]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for i in range(0, len(titles), 50):
        chunk = titles[i:i + 50]
        doc = client.api(action="query", prop="imageinfo", titles="|".join(chunk), iiprop="url|size|mime|extmetadata",
                         iiextmetadatafilter="|".join(EXTMETA_FIELDS), iiextmetadatalanguage="en", iiextmetadatamultilang=0)
        q = doc.get("query", {})
        norm = {n["from"]: n["to"] for n in q.get("normalized", [])}
        rev = {v: k for k, v in norm.items()}
        for p in q.get("pages", []):
            t = p.get("title", "")
            out[t] = p
            if t in rev:
                out[rev[t]] = p
    return out


def gather_candidates(client: Client, item: Item) -> list[tuple[str, str, bool]]:
    """Ordered, de-duplicated (title, provenance, geo_hit) seeds: geosearch hits whose title matches a
    keyword first, then relevance results, then newest-first results, then remaining geosearch hits."""
    seen: set[str] = set()
    ordered: list[tuple[str, str, bool]] = []
    geo: list[str] = []
    if item.geosearch_radius_m > 0:
        try:
            geo = geosearch_titles(client, item.viewpoint[0], item.viewpoint[1], item.geosearch_radius_m)
        except CommonsError as e:
            log.warning("%s: geosearch failed: %s", item.slug, e)
    kw_terms = [k for group in item.keywords for k in group]
    geo_matched = [t for t in geo if any(has_term(t.lower(), k) for k in kw_terms)]
    geo_rest = [t for t in geo if t not in geo_matched]

    def add(titles: list[str], prov: str, is_geo: bool) -> None:
        for t in titles:
            if t not in seen:
                seen.add(t)
                ordered.append((t, prov, is_geo))

    add(geo_matched, "geosearch", True)
    for q in item.queries:
        try:
            add(search_titles(client, q, "relevance", 50), f"search:{q}", False)
        except CommonsError as e:
            log.warning("%s: search failed for %r: %s", item.slug, q, e)
    for q in item.queries:
        try:
            add(search_titles(client, q, "create_timestamp_desc", 25), f"search_recent:{q}", False)
        except CommonsError as e:
            log.warning("%s: recent search failed for %r: %s", item.slug, q, e)
    add(geo_rest[:30], "geosearch", True)
    # a geosearch hit that also came from text search keeps geo_hit=True
    geo_set = set(geo)
    return [(t, p, g or (t in geo_set)) for t, p, g in ordered]


# ----------------------------------------------------------------------------------------------
# Download + verify
# ----------------------------------------------------------------------------------------------

def mean_luminance(im: Image.Image) -> float:
    """Mean 8-bit luminance of the image, used to sanity-check "daylight" vs "night"."""
    g = im.convert("L").resize((64, 64), Image.BILINEAR)
    return float(ImageStat.Stat(g).mean[0])


def fetch_image(client: Client, c: Candidate, max_width: int) -> tuple[bytes, int, int, float, str] | None:
    """Download <= max_width px wide. Returns (jpeg bytes, width, height, mean luminance, url used) or None."""
    data: bytes | None = None
    url = c.url
    for w in thumb_widths(max_width, c.width, min_width=MIN_USABLE_WIDTH):
        url = thumb_url(c.url, w)
        data = client.get_bytes(url)
        if data is not None:
            break
        log.info("no %dpx rendition for %s", w, c.title)
    if data is None:
        if c.bytes > MAX_DOWNLOAD_BYTES:
            log.warning("no usable rendition and original too large (%d bytes): %s", c.bytes, c.title)
            return None
        url = c.url
        # Only reached for a file with no standard rendition at a usable width. Originals are
        # rate-limited, so make one polite attempt and otherwise move on to the next candidate.
        log.info("no usable rendition for %s (%d px), trying the original", c.title, c.width)
        data = client.get_bytes(url, max_wait_s=0.0)
    if data is None:
        return None
    try:
        im = Image.open(io.BytesIO(data))
        im.load()
    except (OSError, Image.DecompressionBombError) as e:
        log.warning("undecodable image %s: %s", c.title, e)
        return None
    orient = 1
    try:
        orient = int(im.getexif().get(0x0112, 1) or 1)
    except Exception:  # noqa: BLE001 - corrupt EXIF must not kill the run
        orient = 1
    reencode = False
    if orient != 1:
        im = ImageOps.exif_transpose(im) or im
        reencode = True
    if im.width > max_width:
        im = im.resize((max_width, max(1, round(im.height * max_width / im.width))), Image.LANCZOS)
        reencode = True
    if im.mode != "RGB":
        im = im.convert("RGB")
        reencode = True
    if im.format != "JPEG":
        reencode = True
    if reencode:
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=90, optimize=True)
        data = buf.getvalue()
    return data, im.width, im.height, mean_luminance(im), url


def item_dir(out_root: Path, item: Item) -> Path:
    return out_root / item.slug


def load_meta(d: Path) -> dict[str, Any] | None:
    p = d / "meta.json"
    if not p.exists():
        return None
    try:
        with open(p, encoding="utf-8") as f:
            doc = json.load(f)
    except (OSError, ValueError):
        return None
    return doc if isinstance(doc, dict) else None


def item_complete(d: Path, item: Item) -> bool:
    """True when meta.json exists, every listed file is present with its recorded size, and either
    the wanted count was reached or the candidate pool was exhausted with >= 1 photo."""
    meta = load_meta(d)
    if not meta:
        return False
    photos = meta.get("photos") or []
    if not photos:
        return False
    for p in photos:
        f = d / p.get("file", "")
        if not f.is_file() or f.stat().st_size != p.get("bytes"):
            return False
    return len(photos) >= item.want or bool(meta.get("exhausted"))


def write_json(path: Path, doc: dict[str, Any]) -> None:
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=1, ensure_ascii=False, sort_keys=False)
    os.replace(tmp, path)


def process_item(client: Client, item: Item, out_root: Path, max_width: int, force: bool, used_titles: set[str]) -> dict[str, Any]:
    d = item_dir(out_root, item)
    if not force and item_complete(d, item):
        meta = load_meta(d) or {}
        for p in meta.get("photos", []):
            used_titles.add(p["title"])
        log.info("present  %-45s %d photo(s)", item.slug, len(meta.get("photos", [])))
        return meta
    d.mkdir(parents=True, exist_ok=True)
    for old in d.glob("*.jpg"):
        old.unlink()
    if (d / "meta.json").exists():
        (d / "meta.json").unlink()

    seeds = gather_candidates(client, item)
    infos = fetch_imageinfo(client, [t for t, _, _ in seeds][:MAX_INFO_TITLES])
    rejects: dict[str, int] = {}
    cands: list[Candidate] = []
    for title, prov, geo in seeds:
        page = infos.get(title)
        if page is None:
            continue
        c = parse_candidate(page, prov, geo)
        if c is None:
            continue
        sc, why = evaluate(item, c)
        if sc is None:
            key = why.split(":", 1)[0]
            rejects[key] = rejects.get(key, 0) + 1
            continue
        c.score = sc
        cands.append(c)
    log.info("%-45s %d seeds, %d info, %d eligible, rejects=%s", item.slug, len(seeds), len(infos), len(cands), rejects)

    photos: list[dict[str, Any]] = []
    chosen_authors: list[str] = []
    chosen_dates: list[str] = []
    luma_lo, luma_hi = item.luma_bounds()
    attempts = 0
    pool = [c for c in cands if c.title not in used_titles]
    exhausted = False
    while len(photos) < item.want:
        if not pool or attempts >= item.want + 8:
            exhausted = not pool
            break
        # diversity: penalise a second photo by the same author / same day
        def eff(c: Candidate) -> float:
            return c.score - (2.5 if c.author in chosen_authors else 0.0) - (1.0 if (c.date_taken or "")[:10] in chosen_dates else 0.0)
        pool.sort(key=lambda c: (eff(c), c.year or 0, c.width), reverse=True)
        c = pool.pop(0)
        attempts += 1
        try:
            got = fetch_image(client, c, max_width)
        except (CommonsError, ValueError) as e:
            log.warning("%s: download failed for %s: %s", item.slug, c.title, e)
            continue
        if got is None:
            continue
        data, w, h, luma, used_url = got
        if not (luma_lo <= luma <= luma_hi):
            log.info("%s: luminance %.0f outside [%.0f, %.0f], skipping %s", item.slug, luma, luma_lo, luma_hi, c.title)
            continue
        n = len(photos) + 1
        fname = f"{n}.jpg"
        with open(d / fname, "wb") as f:
            f.write(data)
        sha = hashlib.sha256(data).hexdigest()
        rec = {
            "n": n, "file": fname, "title": c.title, "page_url": c.page_url, "file_url": c.url, "download_url": used_url,
            "author": c.author, "credit": c.credit,
            "license": {"short_name": c.license_short, "url": c.license_url, "template": c.license_template},
            "date_taken": c.date_taken, "date_source": c.date_source, "year": c.year,
            "camera_gps": {"lat": c.gps[0], "lon": c.gps[1]} if c.gps else None,
            "original_width": c.width, "original_height": c.height, "width": w, "height": h, "bytes": len(data), "sha256": sha,
            "mean_luminance": round(luma, 1), "description": c.description[:600], "categories": c.categories[:25],
            "assessments": c.assessments, "restrictions": c.restrictions, "provenance": c.provenance, "score": round(c.score, 2),
            "estimated_viewpoint": estimate_view(item, c),
            "attribution": f'"{c.title[5:]}" by {c.author}, {c.license_short} ({c.license_url}), via Wikimedia Commons {c.page_url}',
        }
        photos.append(rec)
        chosen_authors.append(c.author)
        if c.date_taken:
            chosen_dates.append(c.date_taken[:10])
        used_titles.add(c.title)
        log.info("saved    %s/%s  %dx%d  %s  %s  %s", item.slug, fname, w, h, c.license_short, c.date_taken or "no date", c.title)
    if not pool and len(photos) < item.want:
        exhausted = True
    meta = {
        "schema_version": SCHEMA_VERSION,
        "slug": item.slug, "name": item.name, "group": item.group,
        "viewpoint": {"lat": item.viewpoint[0], "lon": item.viewpoint[1], "azimuth_deg": round(item.default_azimuth, 1), "note": item.viewpoint_note,
                      "representative": item.representative},
        "subject": {"lat": item.subject[0], "lon": item.subject[1], "name": item.subject_name} if item.subject else None,
        "night": item.night, "interior": item.interior, "min_year": item.min_year, "wanted": item.want,
        "queries": list(item.queries), "geosearch_radius_m": item.geosearch_radius_m,
        "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "max_width": max_width,
        "source": "Wikimedia Commons API (action=query list=search / list=geosearch / prop=imageinfo)",
        "candidates_seen": len(seeds), "candidates_eligible": len(cands), "rejections": rejects,
        "exhausted": exhausted, "status": "ok" if photos else "no_suitable_photo",
        "photos": photos,
    }
    write_json(d / "meta.json", meta)
    if not photos:
        log.warning("%s: NO suitably licensed photo found (seeds=%d, rejects=%s)", item.slug, len(seeds), rejects)
    return meta


# ----------------------------------------------------------------------------------------------
# Index / licences
# ----------------------------------------------------------------------------------------------

def all_metas(out_root: Path) -> list[dict[str, Any]]:
    order = {s: i for i, s in enumerate(_SLUGS)}
    metas: list[dict[str, Any]] = []
    if not out_root.exists():
        return metas
    for d in sorted(out_root.iterdir()):
        if d.is_dir():
            m = load_meta(d)
            if m:
                metas.append(m)
    metas.sort(key=lambda m: order.get(m.get("slug", ""), 10_000))
    return metas


def write_index(out_root: Path, metas: list[dict[str, Any]]) -> Path:
    total_photos = sum(len(m.get("photos", [])) for m in metas)
    total_bytes = sum(p.get("bytes", 0) for m in metas for p in m.get("photos", []))
    lic_counts: dict[str, int] = {}
    for m in metas:
        for p in m.get("photos", []):
            k = p["license"]["short_name"]
            lic_counts[k] = lic_counts.get(k, 0) + 1
    lines = [
        "# Reference photographs — index",
        "",
        "Openly licensed photographs from Wikimedia Commons used as ground truth for the visual checks in ARCHITECTURE.md §14 / ADR-012.",
        f"Generated by `python -m nycsim_pipeline.reference.fetch_photos`; {len(metas)} items, {total_photos} photos, "
        f"{total_bytes / 1e6:.1f} MB. Per-photo provenance (author, licence, date, camera GPS, estimated viewpoint) is in each `<slug>/meta.json`; "
        "attribution for every file is in `LICENSES.md`.",
        "",
        "Licence mix: " + ", ".join(f"{k} × {v}" for k, v in sorted(lic_counts.items(), key=lambda kv: -kv[1])) + ".",
        "",
        "Viewpoint = standard photographer position (WGS84) and compass azimuth of the reference view; `high` confidence means the photo carried "
        "camera GPS and the azimuth was computed from it to the subject, `medium` a fixed known viewpoint, `low` a representative location for a generic subject.",
        "",
        "| slug | group | item | photos | licences | years | viewpoint lat, lon | az° | confidence | status |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for m in metas:
        photos = m.get("photos", [])
        lics = sorted({p["license"]["short_name"] for p in photos})
        years = sorted({str(p.get("year")) for p in photos if p.get("year")})
        confs = [p.get("estimated_viewpoint", {}).get("confidence", "") for p in photos]
        conf = "/".join(sorted(set(confs), key=["high", "medium", "low", ""].index)) if confs else ""
        vp = m.get("viewpoint", {})
        status = m.get("status", "")
        if status == "ok" and len(photos) < m.get("wanted", 0):
            status = f"partial ({len(photos)}/{m.get('wanted')})"
        lines.append(
            f"| [{m['slug']}]({m['slug']}/meta.json) | {m.get('group', '')} | {m.get('name', '')} | {len(photos)} | {', '.join(lics)} | "
            f"{years[0] + ('–' + years[-1] if len(years) > 1 else '') if years else ''} | {vp.get('lat', 0):.5f}, {vp.get('lon', 0):.5f} | "
            f"{vp.get('azimuth_deg', 0):.0f} | {conf} | {status} |"
        )
    missing = [m["slug"] for m in metas if not m.get("photos")]
    lines += ["", f"Items with no suitably licensed photo: {', '.join(missing) if missing else 'none'}.", ""]
    p = out_root / "INDEX.md"
    p.write_text("\n".join(lines), encoding="utf-8")
    return p


def write_licenses(out_root: Path, metas: list[dict[str, Any]]) -> Path:
    lines = [
        "# Reference photographs — licences and attribution",
        "",
        "Every photograph under `docs/verification/reference/` is from Wikimedia Commons and is CC0, CC BY, CC BY-SA or public domain. "
        "They are used only as visual references for verification (comparison sheets), not shipped as game assets. "
        "Files were downloaded at ≤ 2,000 px wide (server-side scaled rendition or locally resized); the `sha256` of the stored file is in `meta.json`. "
        "For CC BY / CC BY-SA files reproduce the attribution line below; CC BY-SA derivatives (e.g. side-by-side comparison sheets) must carry the same licence.",
        "",
    ]
    for m in metas:
        photos = m.get("photos", [])
        lines.append(f"## {m['slug']} — {m.get('name', '')}")
        lines.append("")
        if not photos:
            lines.append("_No suitably licensed photograph found._")
            lines.append("")
            continue
        lines.append("| file | title | author | licence | date taken | camera GPS |")
        lines.append("|---|---|---|---|---|---|")
        for p in photos:
            gps = p.get("camera_gps")
            gps_s = f"{gps['lat']:.5f}, {gps['lon']:.5f}" if gps else "—"
            title = p["title"][5:].replace("|", "\\|")
            author = (p.get("author") or "").replace("|", "\\|")
            lines.append(f"| [{p['file']}]({m['slug']}/{p['file']}) | [{title}]({p['page_url']}) | {author} | "
                         f"[{p['license']['short_name']}]({p['license']['url']}) | {p.get('date_taken') or 'unknown'} | {gps_s} |")
        lines.append("")
    p = out_root / "LICENSES.md"
    p.write_text("\n".join(lines), encoding="utf-8")
    return p


def write_summary(out_root: Path, metas: list[dict[str, Any]], client: Client | None, elapsed_s: float) -> Path:
    per_item = []
    for m in metas:
        photos = m.get("photos", [])
        per_item.append({"slug": m["slug"], "group": m.get("group"), "count": len(photos), "wanted": m.get("wanted"),
                         "bytes": sum(p.get("bytes", 0) for p in photos), "licences": sorted({p["license"]["short_name"] for p in photos}),
                         "status": m.get("status"), "rejections": m.get("rejections", {})})
    doc = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "items": len(metas), "items_in_catalogue": len(CATALOGUE),
        "photos": sum(i["count"] for i in per_item), "bytes": sum(i["bytes"] for i in per_item),
        "items_without_photo": [i["slug"] for i in per_item if i["count"] == 0],
        "items_partial": [f"{i['slug']} ({i['count']}/{i['wanted']})" for i in per_item if 0 < i["count"] < (i["wanted"] or 0)],
        "http_requests_this_run": client.requests_made if client else 0, "elapsed_s": round(elapsed_s, 1),
        "per_item": per_item,
    }
    p = out_root / "summary.json"
    write_json(p, doc)
    return p


# ----------------------------------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------------------------------

def select_items(only: list[str]) -> list[Item]:
    if not only:
        return list(CATALOGUE)
    sel: list[Item] = []
    for key in only:
        if key in BY_SLUG:
            sel.append(BY_SLUG[key])
        elif key in GROUPS:
            sel.extend(i for i in CATALOGUE if i.group == key)
        else:
            raise SystemExit(f"unknown slug/group: {key}")
    seen: set[str] = set()
    return [i for i in sel if not (i.slug in seen or seen.add(i.slug))]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", action="append", default=[], help="slug or group (repeatable)")
    ap.add_argument("--force", action="store_true", help="re-fetch selected items even if complete")
    ap.add_argument("--max-width", type=int, default=DEFAULT_MAX_WIDTH)
    ap.add_argument("--min-interval", type=float, default=MIN_INTERVAL_S,
                    help="seconds between HTTP requests (>= 0.5 keeps the run inside the 2 req/s etiquette limit)")
    ap.add_argument("--out", type=Path, default=OUT_ROOT)
    ap.add_argument("--list", action="store_true", help="print the catalogue and exit")
    ap.add_argument("--index-only", action="store_true", help="regenerate INDEX.md/LICENSES.md/summary.json from existing meta.json files, no network")
    ap.add_argument("-v", "--verbose", action="store_true")
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if a.verbose else logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    if a.max_width < 250 or a.max_width > 2000:
        ap.error("--max-width must be within 250..2000 (brief: <= 2,000 px wide)")
    if a.min_interval < 0.5:
        ap.error("--min-interval must be >= 0.5 s (Wikimedia etiquette: at most 2 requests per second)")
    items = select_items(a.only)
    if a.list:
        for i in items:
            print(f"{i.slug:45s} {i.group:13s} want={i.want} vp={i.viewpoint[0]:.5f},{i.viewpoint[1]:.5f} az={i.default_azimuth:.0f} {i.name}")
        return 0
    a.out.mkdir(parents=True, exist_ok=True)
    t0 = time.monotonic()
    client: Client | None = None
    failures: list[tuple[str, str]] = []
    if not a.index_only:
        client = Client(min_interval=a.min_interval)
        used: set[str] = set()
        for m in all_metas(a.out):  # never pick a photo already used by another slug
            for p in m.get("photos", []):
                used.add(p["title"])
        for it in items:
            try:
                process_item(client, it, a.out, a.max_width, a.force, used)
            except CommonsError as e:
                log.error("FAILED %s: %s", it.slug, e)
                failures.append((it.slug, str(e)))
            except OSError as e:
                log.error("FAILED %s (I/O): %s", it.slug, e)
                failures.append((it.slug, str(e)))
    metas = all_metas(a.out)
    write_index(a.out, metas)
    write_licenses(a.out, metas)
    summary_path = write_summary(a.out, metas, client, time.monotonic() - t0)
    with open(summary_path, encoding="utf-8") as f:
        s = json.load(f)
    print(json.dumps({k: s[k] for k in ("items", "items_in_catalogue", "photos", "bytes", "items_without_photo", "items_partial",
                                        "http_requests_this_run", "elapsed_s")}, indent=1))
    if failures:
        print(json.dumps({"failures": failures}, indent=1))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
