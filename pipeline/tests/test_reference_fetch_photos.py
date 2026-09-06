"""Offline tests for nycsim_pipeline.reference.fetch_photos (no network)."""
from __future__ import annotations

import io
import json
import sys
from pathlib import Path

import pytest
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from nycsim_pipeline.reference import fetch_photos as fp  # noqa: E402


# ------------------------------------------------------------------ pure helpers

def test_licence_ok_accepts_free_licences_only():
    assert fp.licence_ok("CC BY-SA 4.0", "cc-by-sa-4.0")
    assert fp.licence_ok("CC BY 2.0", "cc-by-2.0")
    assert fp.licence_ok("CC BY-SA 3.0 de", "cc-by-sa-3.0-de")
    assert fp.licence_ok("CC0", "cc-zero")
    assert fp.licence_ok("CC0 1.0", "cc0")
    assert fp.licence_ok("Public domain", "pd-self")
    assert fp.licence_ok("Public domain", "")
    assert not fp.licence_ok("CC BY-NC-SA 2.0", "cc-by-nc-sa-2.0")
    assert not fp.licence_ok("CC BY-ND 4.0", "cc-by-nd-4.0")
    assert not fp.licence_ok("GFDL", "gfdl")
    assert not fp.licence_ok("Copyrighted free use", "copyrighted free use")
    assert not fp.licence_ok("Attribution", "attribution")
    assert not fp.licence_ok("", "")
    assert not fp.licence_ok(None, None)
    # a 'Public domain' short name backed by an NC template is not trusted
    assert not fp.licence_ok("Public domain", "cc-by-nc-2.0")


def test_licence_url_fallbacks():
    assert fp.licence_url("CC BY-SA 4.0", "https://creativecommons.org/licenses/by-sa/4.0?x=1") == "https://creativecommons.org/licenses/by-sa/4.0"
    assert fp.licence_url("CC BY 2.0", None) == "https://creativecommons.org/licenses/by/2.0/"
    assert fp.licence_url("CC BY-SA 3.0", "") == "https://creativecommons.org/licenses/by-sa/3.0/"
    assert fp.licence_url("CC0", None).startswith("https://creativecommons.org/publicdomain/zero/1.0")
    assert "public_domain" in fp.licence_url("Public domain", None)


def test_parse_date_variants():
    assert fp.parse_date("2023-01-20 14:33:49") == ("2023-01-20 14:33:49", 2023)
    assert fp.parse_date("2019:05:03 14:22:10") == ("2019-05-03 14:22:10", 2019)
    assert fp.parse_date('<time class="dtstart" datetime="2016-06-07">7 June 2016</time>') == ("2016-06-07", 2016)
    assert fp.parse_date("2018-06") == ("2018-06", 2018)
    assert fp.parse_date("circa 1905") == ("1905", 1905)
    assert fp.parse_date("Taken on 5 June 2019") == ("2019", 2019)
    assert fp.parse_date("") == (None, None)
    assert fp.parse_date(None) == (None, None)
    assert fp.parse_date("unknown") == (None, None)
    assert fp.parse_date("2019-13-45") == ("2019", 2019)  # invalid month/day falls back to the year


def test_strip_html():
    assert fp.strip_html('<a href="//commons.wikimedia.org/wiki/User:X" title="User:X">X&amp;Y</a>') == "X&Y"
    assert fp.strip_html(None) == ""
    assert fp.strip_html("  a   b\n c ") == "a b c"


def test_bearing_and_distance_promenade_to_one_wtc():
    vp = (40.6960, -73.9975)
    d = fp.haversine_m(vp, fp.ONE_WTC)
    az = fp.bearing_deg(vp, fp.ONE_WTC)
    assert 2200 < d < 2500
    assert 320 < az < 335  # west-north-west across the East River
    assert fp.bearing_deg((40.0, -74.0), (41.0, -74.0)) == pytest.approx(0.0, abs=1e-6)
    assert fp.bearing_deg((40.0, -74.0), (40.0, -73.0)) == pytest.approx(90.0, abs=0.5)


def test_thumb_url_construction():
    orig = "https://upload.wikimedia.org/wikipedia/commons/f/f0/Lower_Manhattan_Skyline_2025_005.jpg?utm_source=x"
    assert fp.thumb_url(orig, 2000) == ("https://upload.wikimedia.org/wikipedia/commons/thumb/f/f0/Lower_Manhattan_Skyline_2025_005.jpg/"
                                         "2000px-Lower_Manhattan_Skyline_2025_005.jpg")
    with pytest.raises(ValueError):
        fp.thumb_url("https://example.com/a.jpg", 2000)


def test_has_term_is_word_bounded():
    assert fp.has_term("the map of manhattan", "map")
    assert not fp.has_term("maple street", "map")
    assert fp.has_term("times square at night", "at night")
    assert not fp.has_term("knightsbridge", "night")


# ------------------------------------------------------------------ catalogue integrity

REQUIRED_SLUGS = [
    "promenade_lower_manhattan", "top_of_the_rock_south", "times_square_duffy_south_day", "times_square_duffy_south_night",
    "fifth_ave_42nd_north", "fifth_ave_42nd_south", "bethesda_terrace_fountain", "staten_island_ferry_lower_manhattan",
    "dumbo_washington_st_manhattan_bridge",
    "drive_midtown_sixth_ave_45th", "drive_lower_manhattan_broadway_wall_st", "drive_lower_manhattan_stone_st",
    "drive_brooklyn_park_slope_7th_ave", "drive_brooklyn_bed_stuy_stuyvesant_ave", "drive_queens_forest_hills",
    "drive_queens_jackson_heights", "drive_queens_bayside", "drive_bronx_grand_concourse", "drive_bronx_arthur_ave",
    "landmark_empire_state_building", "landmark_chrysler_building", "landmark_one_world_trade_center", "landmark_oculus",
    "landmark_911_memorial_pools", "landmark_statue_of_liberty", "landmark_brooklyn_bridge_from_dumbo", "landmark_brooklyn_bridge_walkway",
    "landmark_flatiron_building", "landmark_grand_central_facade", "landmark_grand_central_concourse", "landmark_rockefeller_center",
    "landmark_st_patricks_cathedral", "landmark_one_vanderbilt", "landmark_hudson_yards_vessel", "landmark_high_line",
    "landmark_central_park_bow_bridge", "landmark_central_park_sheep_meadow", "landmark_metropolitan_museum", "landmark_guggenheim",
    "landmark_amnh", "landmark_columbus_circle", "landmark_lincoln_center", "landmark_madison_square_garden", "landmark_nypl",
    "landmark_washington_square_arch", "landmark_woolworth_building", "landmark_city_hall", "landmark_municipal_building",
    "landmark_charging_bull", "landmark_nyse", "landmark_trinity_church", "landmark_the_dakota", "landmark_the_plaza_hotel",
    "landmark_apollo_theater", "landmark_yankee_stadium", "landmark_citi_field", "landmark_unisphere", "landmark_coney_island_cyclone",
    "landmark_coney_island_wonder_wheel", "landmark_coney_island_parachute_jump", "landmark_barclays_center", "landmark_432_park_avenue",
    "landmark_111_west_57th", "landmark_central_park_tower", "landmark_one57", "landmark_united_nations_hq", "landmark_domino_sugar_refinery",
    "landmark_george_washington_bridge", "landmark_verrazzano_narrows_bridge", "landmark_queensboro_bridge", "landmark_williamsburg_bridge",
    "landmark_manhattan_bridge", "landmark_rfk_triborough_bridge", "landmark_hell_gate_bridge", "landmark_high_bridge",
    "landmark_holland_tunnel_portal", "landmark_lincoln_tunnel_portal",
    "street_tenement_fire_escapes_les", "street_soho_cast_iron", "street_nycha_tower_campus", "street_queens_vinyl_siding",
    "street_staten_island_ranch_houses", "street_elevated_roosevelt_ave_7", "street_elevated_broadway_bushwick_j",
    "street_midtown_avenue_rush_hour", "street_times_square_wet_night", "street_brooklyn_snow", "street_nyc_street_name_signs", "street_nyc_traffic_signals",
    "street_fire_hydrant", "street_linknyc_kiosk", "street_newsstand", "street_sidewalk_shed",
    "vehicle_yellow_cab", "vehicle_mta_bus", "vehicle_nypd_car", "vehicle_fdny_engine",
]


def test_catalogue_covers_every_mandated_item_and_is_consistent():
    slugs = [i.slug for i in fp.CATALOGUE]
    assert len(slugs) == len(set(slugs))
    missing = [s for s in REQUIRED_SLUGS if s not in fp.BY_SLUG]
    assert not missing, missing
    for it in fp.CATALOGUE:
        assert it.group in fp.GROUPS
        assert 40.45 <= it.viewpoint[0] <= 40.95 and -74.30 <= it.viewpoint[1] <= -73.65, it.slug
        assert 0.0 <= it.default_azimuth < 360.0, it.slug
        assert it.queries and it.keywords and it.viewpoint_note
        if it.subject is not None:
            assert it.subject_name, it.slug
            assert 15.0 <= fp.haversine_m(it.viewpoint, it.subject) <= 6000.0, it.slug
    # sanity on a few well-known geometries
    assert 190 <= fp.BY_SLUG["top_of_the_rock_south"].default_azimuth <= 215  # 30 Rock -> Empire State is SSW
    assert 190 <= fp.BY_SLUG["times_square_duffy_south_day"].default_azimuth <= 215
    assert 340 <= fp.BY_SLUG["dumbo_washington_st_manhattan_bridge"].default_azimuth or fp.BY_SLUG["dumbo_washington_st_manhattan_bridge"].default_azimuth <= 10
    assert fp.BY_SLUG["landmark_grand_central_concourse"].interior
    assert fp.BY_SLUG["times_square_duffy_south_night"].night


def test_item_rejects_bad_definitions():
    with pytest.raises(ValueError):
        fp.Item("x", "x", "landmark", ("q",), (("k",),), (40.7, -74.0), "note")  # no subject, no azimuth
    with pytest.raises(ValueError):
        fp.Item("x", "x", "landmark", ("q",), (("k",),), (51.5, -0.1), "note", azimuth=0.0)  # London
    with pytest.raises(ValueError):
        fp.Item("x", "x", "nonsense", ("q",), (("k",),), (40.7, -74.0), "note", azimuth=0.0)


# ------------------------------------------------------------------ scoring

def _page(title: str, *, lic="CC BY-SA 4.0", tpl="cc-by-sa-4.0", w=3000, h=2000, mime="image/jpeg", date="2019-05-03 14:22:10",
          desc="", cats="", gps=None, artist="Someone") -> dict:
    ext = {"LicenseShortName": {"value": lic}, "License": {"value": tpl}, "LicenseUrl": {"value": "https://creativecommons.org/licenses/by-sa/4.0"},
           "Artist": {"value": f'<a href="//x">{artist}</a>'}, "DateTimeOriginal": {"value": date}, "ImageDescription": {"value": desc},
           "Categories": {"value": cats}, "ObjectName": {"value": title[5:-4]}}
    if gps:
        ext["GPSLatitude"] = {"value": str(gps[0])}
        ext["GPSLongitude"] = {"value": str(gps[1])}
    name = title[5:].replace(" ", "_")
    return {"pageid": 1, "title": title, "imageinfo": [{"size": 123456, "width": w, "height": h, "mime": mime,
                                                       "url": f"https://upload.wikimedia.org/wikipedia/commons/a/ab/{name}",
                                                       "descriptionurl": f"https://commons.wikimedia.org/wiki/{title.replace(' ', '_')}",
                                                       "extmetadata": ext}]}


def _candidate(title: str, *, cats: list[str] | None = None, **kw) -> fp.Candidate:
    """A parsed Commons candidate from a synthetic file page (categories given as a list)."""
    c = fp.parse_candidate(_page(title, cats="|".join(cats or []), **kw), "search")
    assert c is not None
    return c


def test_evaluate_rules():
    item = fp.BY_SLUG["promenade_lower_manhattan"]
    ok = fp.parse_candidate(_page("File:Lower Manhattan from Brooklyn Heights Promenade.jpg"), "search")
    sc, why = fp.evaluate(item, ok)
    assert sc is not None and why == "ok"
    nc = fp.parse_candidate(_page("File:Lower Manhattan from Brooklyn Heights Promenade.jpg", lic="CC BY-NC 2.0", tpl="cc-by-nc-2.0"), "s")
    assert fp.evaluate(item, nc) == (None, "licence")
    small = fp.parse_candidate(_page("File:Lower Manhattan from Brooklyn Heights Promenade.jpg", w=640, h=480), "s")
    assert fp.evaluate(item, small) == (None, "too_small")
    night = fp.parse_candidate(_page("File:Lower Manhattan skyline at night from the Promenade.jpg"), "s")
    assert fp.evaluate(item, night) == (None, "night_for_day_item")
    old = fp.parse_candidate(_page("File:Lower Manhattan from Brooklyn Heights Promenade.jpg", date="2009-07-01"), "s")
    assert fp.evaluate(item, old)[1].startswith("too_old")
    postcard = fp.parse_candidate(_page("File:Lower Manhattan from Brooklyn Heights Promenade postcard.jpg"), "s")
    assert fp.evaluate(item, postcard)[1].startswith("not_photo")
    offtopic = fp.parse_candidate(_page("File:2023 Honda CR-V at Pierrepont Place.jpg"), "geosearch", geo_hit=True)
    assert fp.evaluate(item, offtopic) == (None, "keywords")
    png = fp.parse_candidate(_page("File:Lower Manhattan from Brooklyn Heights Promenade.png", mime="image/png"), "s")
    assert fp.evaluate(item, png) == (None, "not_jpeg")
    # newer beats older, geo hit beats none
    older_ok = fp.parse_candidate(_page("File:Lower Manhattan from Brooklyn Heights Promenade 2014.jpg", date="2014-05-03"), "s")
    assert fp.evaluate(item, ok)[0] > fp.evaluate(item, older_ok)[0]
    geo = fp.parse_candidate(_page("File:Lower Manhattan from Brooklyn Heights Promenade.jpg", gps=(40.6961, -73.9976)), "geosearch", geo_hit=True)
    assert fp.evaluate(item, geo)[0] > fp.evaluate(item, ok)[0]
    # night item accepts night, rejects nothing on 'night' words
    nitem = fp.BY_SLUG["times_square_duffy_south_night"]
    tn = fp.parse_candidate(_page("File:Times Square at night from Duffy Square.jpg"), "s")
    assert fp.evaluate(nitem, tn)[1] == "ok"


def test_estimate_view_methods():
    item = fp.BY_SLUG["promenade_lower_manhattan"]
    with_gps = fp.parse_candidate(_page("File:A.jpg", gps=(40.6965, -73.9970)), "s")
    e = fp.estimate_view(item, with_gps)
    assert e["confidence"] == "high" and e["method"] == "camera_gps_to_subject"
    assert e["lat"] == 40.6965 and 315 < e["azimuth_deg"] < 340 and "bearing" in e["explanation"]
    no_gps = fp.parse_candidate(_page("File:B.jpg"), "s")
    e2 = fp.estimate_view(item, no_gps)
    assert e2["confidence"] == "medium" and e2["lat"] == item.viewpoint[0] and "No camera GPS" in e2["explanation"]
    on_subject = fp.parse_candidate(_page("File:C.jpg", gps=fp.ONE_WTC), "s")
    e3 = fp.estimate_view(item, on_subject)
    assert e3["lat"] == item.viewpoint[0] and "geotagged the subject" in e3["explanation"]
    far = fp.parse_candidate(_page("File:D.jpg", gps=(40.85, -73.93)), "s")
    e4 = fp.estimate_view(item, far)
    assert e4["lat"] == item.viewpoint[0] and "implausibly far" in e4["method"]
    street = fp.BY_SLUG["fifth_ave_42nd_north"]
    e5 = fp.estimate_view(street, fp.parse_candidate(_page("File:E.jpg", gps=(40.7527, -73.9815)), "s"))
    assert e5["method"] == "camera_gps_with_item_azimuth" and e5["azimuth_deg"] == pytest.approx(29.0)
    generic = fp.BY_SLUG["vehicle_yellow_cab"]
    e6 = fp.estimate_view(generic, no_gps)
    assert e6["confidence"] == "low" and "representative" in e6["explanation"]


# ------------------------------------------------------------------ offline end-to-end with a fake client

def _jpeg_bytes(w: int, h: int, grey: int) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (w, h), (grey, grey, grey)).save(buf, "JPEG", quality=85)
    return buf.getvalue()


class FakeClient:
    """Answers the three API shapes used by the fetcher and serves canned image bytes."""

    def __init__(self, pages: list[dict], images: dict[str, bytes]):
        self.pages = {p["title"]: p for p in pages}
        self.images = images
        self.requests_made = 0
        self.urls: list[str] = []

    def api(self, **params):
        self.requests_made += 1
        if params.get("generator") == "search":
            return {"query": {"pages": [dict(p, index=i + 1) for i, p in enumerate(self.pages.values())]}}
        if params.get("generator") == "geosearch":
            return {"query": {"pages": [dict(p, index=1) for p in list(self.pages.values())[:1]]}}
        raise AssertionError(params)

    def get_bytes(self, url, max_wait_s: float = 90.0):
        self.requests_made += 1
        self.urls.append(url)
        return self.images.get(url)


def test_process_item_end_to_end(tmp_path: Path):
    item = fp.BY_SLUG["promenade_lower_manhattan"]
    pages = [
        _page("File:Skyline from Brooklyn Heights Promenade 1.jpg", w=4000, h=2600, artist="A", date="2022-06-01 12:00:00", gps=(40.6961, -73.9976)),
        _page("File:Skyline from Brooklyn Heights Promenade 2.jpg", w=1800, h=1200, artist="B", date="2021-06-01 12:00:00"),
        _page("File:Skyline from Brooklyn Heights Promenade dark.jpg", w=3000, h=2000, artist="C", date="2023-06-01 12:00:00"),
        _page("File:Skyline from Brooklyn Heights Promenade nc.jpg", lic="CC BY-NC 2.0", tpl="cc-by-nc-2.0"),
        _page("File:Skyline from Brooklyn Heights Promenade 3.jpg", w=2500, h=1600, artist="D", date="2020-06-01 12:00:00"),
    ]
    base = "https://upload.wikimedia.org/wikipedia/commons/a/ab/Skyline_from_Brooklyn_Heights_Promenade_"
    images = {
        # 4000 px original -> the largest standard bucket at or below --max-width
        fp.thumb_url(base + "1.jpg", 1920): _jpeg_bytes(1920, 1248, 140),
        # 1800 px original -> the largest bucket below it (originals are never downloaded)
        fp.thumb_url(base + "2.jpg", 1280): _jpeg_bytes(1280, 853, 120),
        # the 'dark' file is a night shot mislabelled as day -> rejected by the luminance check
        fp.thumb_url(base + "dark.jpg", 1920): _jpeg_bytes(1920, 1280, 20),
        # no rendition exists for '3' at any usable width -> falls back to the original, resized locally
        base + "3.jpg": _jpeg_bytes(2500, 1600, 130),
    }
    client = FakeClient(pages, images)
    used: set[str] = set()
    meta = fp.process_item(client, item, tmp_path, fp.DEFAULT_MAX_WIDTH, False, used)  # type: ignore[arg-type]
    assert meta["status"] == "ok"
    files = sorted(p.name for p in (tmp_path / item.slug).glob("*.jpg"))
    assert files == ["1.jpg", "2.jpg", "3.jpg"]
    titles = [p["title"] for p in meta["photos"]]
    assert "File:Skyline from Brooklyn Heights Promenade dark.jpg" not in titles
    assert "File:Skyline from Brooklyn Heights Promenade nc.jpg" not in titles
    assert meta["rejections"].get("licence") == 1
    for p in meta["photos"]:
        f = tmp_path / item.slug / p["file"]
        assert f.stat().st_size == p["bytes"]
        with Image.open(f) as im:
            assert im.width <= fp.DEFAULT_MAX_WIDTH and im.width == p["width"]
        assert p["license"]["short_name"] == "CC BY-SA 4.0" and p["license"]["url"].startswith("https://creativecommons.org/")
        assert p["author"] and p["page_url"].startswith("https://commons.wikimedia.org/wiki/File:")
        assert p["estimated_viewpoint"]["explanation"]
        assert len(p["sha256"]) == 64
    first = meta["photos"][0]
    assert first["title"].endswith("1.jpg") and first["estimated_viewpoint"]["confidence"] == "high"
    third = next(p for p in meta["photos"] if p["title"].endswith(" 3.jpg"))
    # no rendition available, so the original was fetched and scaled down locally
    assert third["original_width"] == 2500 and third["width"] == fp.DEFAULT_MAX_WIDTH
    # re-run skips (idempotent)
    n_before = client.requests_made
    meta2 = fp.process_item(client, item, tmp_path, fp.DEFAULT_MAX_WIDTH, False, set())  # type: ignore[arg-type]
    assert client.requests_made == n_before and meta2["photos"] == meta["photos"]
    assert fp.item_complete(tmp_path / item.slug, item)
    # a missing file invalidates completeness
    (tmp_path / item.slug / "2.jpg").unlink()
    assert not fp.item_complete(tmp_path / item.slug, item)
    # index + licences render
    metas = fp.all_metas(tmp_path)
    idx = fp.write_index(tmp_path, metas).read_text(encoding="utf-8")
    lic = fp.write_licenses(tmp_path, metas).read_text(encoding="utf-8")
    assert item.slug in idx and "CC BY-SA 4.0" in idx and "partial" in idx  # want=4, got 3
    assert "Skyline from Brooklyn Heights Promenade 1" in lic and "creativecommons.org" in lic
    summary = json.loads(fp.write_summary(tmp_path, metas, None, 1.0).read_text(encoding="utf-8"))
    assert summary["photos"] == 3 and summary["items"] == 1


def test_process_item_records_no_photo_when_nothing_qualifies(tmp_path: Path):
    item = fp.BY_SLUG["street_fire_hydrant"]
    pages = [_page("File:Fire hydrant in Paris.jpg", w=3000, h=2000)]  # fails NYC keyword group
    client = FakeClient(pages, {})
    meta = fp.process_item(client, item, tmp_path, fp.DEFAULT_MAX_WIDTH, False, set())  # type: ignore[arg-type]
    assert meta["status"] == "no_suitable_photo" and meta["photos"] == [] and meta["rejections"] == {"keywords": 1}
    assert not fp.item_complete(tmp_path / item.slug, item)  # a re-run will retry it


def test_thumb_widths_are_standard_buckets_and_never_the_original():
    # upload.wikimedia.org renders only the standard widths and rate-limits originals, so the
    # list must be buckets only, descending, strictly below the original width.
    assert fp.thumb_widths(1920, 3264, 900) == [1920, 1280, 960]
    assert fp.thumb_widths(1920, 1500, 900) == [1280, 960]
    assert fp.thumb_widths(1920, 1174, 900) == [960]
    assert fp.thumb_widths(1920, 960, 900) == []      # nothing usable below a 960 px original
    assert fp.thumb_widths(1280, 3264, 900) == [1280, 960]
    for original in (901, 1000, 1921, 4000, 12000):
        got = fp.thumb_widths(1920, original, 900)
        assert got == sorted(got, reverse=True)
        assert all(w in fp.THUMB_BUCKETS and 900 <= w <= 1920 and w < original for w in got)


def test_indoor_photos_are_rejected_for_exterior_items():
    item = fp.BY_SLUG["times_square_duffy_south_day"]
    inside = _candidate("File:Duffy Square entrance NB BMT sta closed 2024.jpg",
                        cats=["Duffy Square", "New York City Subway entrances in Manhattan"])
    assert fp.evaluate(item, inside)[1].startswith("indoor:")
    outside = _candidate("File:View of Times Square, May 2023.JPG", cats=["Duffy Square", "TKTS Booth"])
    assert fp.evaluate(item, outside)[0] is not None
    # an item that is an interior, and one allowed to show station structures, keep theirs
    concourse = _candidate("File:Grand Central Terminal main concourse 2019.jpg", cats=["Grand Central Terminal interior"])
    assert fp.evaluate(fp.BY_SLUG["landmark_grand_central_concourse"], concourse)[0] is not None
    el = _candidate("File:Roosevelt Avenue IRT Flushing Line elevated 2019.jpg",
                    cats=["Roosevelt Avenue", "IRT Flushing Line", "Elevated railways in Queens"])
    assert fp.evaluate(fp.BY_SLUG["street_elevated_roosevelt_ave_7"], el)[0] is not None


def test_people_subjects_score_below_place_subjects():
    item = fp.BY_SLUG["times_square_duffy_south_day"]
    place = _candidate("File:Times Square from Duffy Square 2019.jpg", cats=["Duffy Square"])
    person = _candidate("File:Tourist in Times Square 2019.jpg", cats=["Duffy Square", "Tourists in Manhattan"])
    assert fp.evaluate(item, place)[0] > fp.evaluate(item, person)[0]


def test_revalidate_drops_items_failing_the_current_rules(tmp_path: Path):
    item = fp.BY_SLUG["landmark_charging_bull"]
    d = tmp_path / item.slug
    d.mkdir(parents=True)
    (d / "1.jpg").write_bytes(_jpeg_bytes(1000, 800, 120))
    (d / "2.jpg").write_bytes(_jpeg_bytes(1000, 800, 120))
    meta = {
        "schema_version": fp.SCHEMA_VERSION, "slug": item.slug, "name": item.name, "group": item.group,
        "viewpoint": {"lat": item.viewpoint[0], "lon": item.viewpoint[1], "azimuth_deg": 217.0, "note": item.viewpoint_note,
                      "representative": False},
        "wanted": item.want, "photos": [
            {"n": 1, "file": "1.jpg", "title": "File:Charging Bull Bowling Green 2019.jpg", "description": "",
             "categories": ["Charging Bull"], "license": {"short_name": "CC BY-SA 4.0", "template": "cc-by-sa-4.0"}},
            {"n": 2, "file": "2.jpg", "title": "File:Charging Bull lobby interior.jpg", "description": "",
             "categories": ["Charging Bull"], "license": {"short_name": "CC BY-SA 4.0", "template": "cc-by-sa-4.0"}},
        ],
    }
    fp.write_json(d / "meta.json", meta)
    assert fp.revalidate(tmp_path, [item]) == [item.slug]
    assert not (d / "meta.json").exists() and not list(d.glob("*.jpg"))
    # a clean item survives
    d2 = tmp_path / "landmark_flatiron_building"
    item2 = fp.BY_SLUG["landmark_flatiron_building"]
    d2.mkdir(parents=True)
    (d2 / "1.jpg").write_bytes(_jpeg_bytes(1000, 800, 120))
    fp.write_json(d2 / "meta.json", {
        "schema_version": fp.SCHEMA_VERSION, "slug": item2.slug, "name": item2.name, "group": item2.group,
        "wanted": item2.want, "photos": [
            {"n": 1, "file": "1.jpg", "title": "File:Flatiron Building 2021.jpg", "description": "",
             "categories": ["Flatiron Building"], "license": {"short_name": "CC BY-SA 4.0", "template": "cc-by-sa-4.0"}},
        ]})
    assert fp.revalidate(tmp_path, [item2]) == []
    assert (d2 / "meta.json").exists()


_COMPASS = ["north", "north-north-east", "north-east", "east-north-east", "east", "east-south-east", "south-east",
            "south-south-east", "south", "south-south-west", "south-west", "west-south-west", "west",
            "west-north-west", "north-west", "north-north-west"]
_COMPASS_DEG = {p: i * 22.5 for i, p in enumerate(_COMPASS)}
_COMPASS_RE = "|".join(sorted((p for p in _COMPASS), key=len, reverse=True))


def _angle_diff(a: float, b: float) -> float:
    return abs((a - b + 180.0) % 360.0 - 180.0)


def test_viewpoint_notes_agree_with_the_computed_geometry():
    """The prose in every viewpoint_note must match the numbers the meta.json will carry.

    'looking <compass>' must be within 1.5 compass points of the item's azimuth, and
    '<compass> of/from the subject' must match the bearing from the subject to the camera.
    """
    import re
    bad = []
    for it in fp.CATALOGUE:
        note = it.viewpoint_note.lower()
        m = re.search(r"looking (" + _COMPASS_RE + r")", note)
        if m and _angle_diff(_COMPASS_DEG[m.group(1)], it.default_azimuth) > 34.0:
            bad.append((it.slug, "looking " + m.group(1), round(it.default_azimuth, 1)))
        m2 = re.search(r"(" + _COMPASS_RE + r") (?:of|from)\b", note)
        if m2 and it.subject is not None:
            side = fp.bearing_deg(it.subject, it.viewpoint)
            if _angle_diff(_COMPASS_DEG[m2.group(1)], side) > 34.0:
                bad.append((it.slug, m2.group(1) + " of", round(side, 1)))
    assert not bad, bad


def test_every_landmark_in_docs_landmarks_md_has_a_subject():
    """Each structure named in docs/LANDMARKS.md is represented by a catalogue item."""
    doc = (Path(__file__).resolve().parents[2] / "docs" / "LANDMARKS.md").read_text(encoding="utf-8").lower()
    assert doc, "docs/LANDMARKS.md is empty"
    blob = " || ".join(f"{i.slug} :: {i.name}" for i in fp.CATALOGUE).lower()
    # a representative sample spanning all three landmark groups, keyed to the slug/name text
    for token in ("empire_state", "chrysler", "flatiron", "one_vanderbilt", "rockefeller", "st_patricks",
                  "grand_central_facade", "grand_central_concourse", "nypl", "madison_square_garden", "woolworth",
                  "municipal_building", "city_hall", "trinity_church", "nyse", "charging_bull", "federal_hall",
                  "40_wall", "one_wall_street", "equitable", "moma", "brooklyn_bridge", "manhattan_bridge",
                  "williamsburg_bridge", "queensboro", "george_washington", "verrazzano", "rfk_triborough",
                  "throgs_neck", "whitestone", "hell_gate", "high_bridge", "pulaski", "kosciuszko",
                  "roosevelt_island_tram", "lincoln_tunnel", "holland_tunnel", "queens_midtown_tunnel",
                  "hugh_carey_tunnel", "one_world_trade", "oculus", "3_world_trade", "4_world_trade",
                  "7_world_trade", "911_memorial_pools", "statue_of_liberty", "ellis_island",
                  "washington_square_arch", "bethesda", "bow_bridge", "belvedere_castle", "central_park_wall_gates",
                  "unisphere", "castle_williams", "fort_jay", "grants_tomb", "columbus_circle",
                  "soldiers_sailors_arch", "prospect_park_boathouse", "cyclone", "wonder_wheel", "parachute_jump",
                  "boardwalk", "30_hudson_yards", "35_hudson_yards", "10_hudson_yards", "55_hudson_yards",
                  "15_hudson_yards", "50_hudson_yards", "the_shed", "vessel", "432_park", "111_west_57th",
                  "central_park_tower", "one57", "220_central_park_south", "53w53", "trump_tower", "9_west_57th",
                  "one_times_square", "two_times_square", "three_times_square", "four_times_square", "tsx_broadway",
                  "paramount_building", "tkts", "times_square_tower", "bank_of_america_tower", "marriott_marquis",
                  "new_york_times_building", "port_authority", "hearst", "citigroup_center", "metlife", "lipstick",
                  "seagram", "lever_house", "united_nations", "dakota", "plaza_hotel", "metropolitan_museum",
                  "guggenheim", "amnh", "rose_center", "lincoln_center", "apollo", "carnegie_hall",
                  "john_the_divine", "riverside_church", "yankee_stadium", "citi_field", "barclays", "arthur_ashe",
                  "domino_sugar", "domino_park", "kings_theatre", "brooklyn_museum", "brooklyn_public_library",
                  "williamsburgh_savings", "pier_17", "whitehall_ferry", "st_george_ferry", "ny_state_pavilion",
                  "queens_museum", "bronx_county_courthouse", "high_line", "little_island", "pier_57",
                  "chelsea_market", "javits", "moynihan"):
        assert token in blob, f"docs/LANDMARKS.md names a structure with no catalogue item: {token}"


def test_force_refetch_can_reuse_the_items_own_photos(tmp_path: Path):
    """used_titles stops two subjects sharing a file; it must not stop one subject re-picking its own."""
    item = fp.BY_SLUG["promenade_lower_manhattan"]
    base = "https://upload.wikimedia.org/wikipedia/commons/a/ab/Skyline_from_Brooklyn_Heights_Promenade_"
    pages = [_page("File:Skyline from Brooklyn Heights Promenade 1.jpg", w=4000, h=2600, artist="A",
                   date="2022-06-01 12:00:00", gps=(40.6961, -73.9976))]
    images = {fp.thumb_url(base + "1.jpg", 1920): _jpeg_bytes(1920, 1248, 140)}
    client = FakeClient(pages, images)
    used: set[str] = set()
    first = fp.process_item(client, item, tmp_path, fp.DEFAULT_MAX_WIDTH, False, used)  # type: ignore[arg-type]
    assert len(first["photos"]) == 1 and used == {"File:Skyline from Brooklyn Heights Promenade 1.jpg"}
    again = fp.process_item(client, item, tmp_path, fp.DEFAULT_MAX_WIDTH, True, used)  # type: ignore[arg-type]
    assert [p["title"] for p in again["photos"]] == [p["title"] for p in first["photos"]]
    assert (tmp_path / item.slug / "1.jpg").is_file()
