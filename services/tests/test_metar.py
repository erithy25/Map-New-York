"""METAR parser: real recorded reports plus the awkward groups the NYC stations actually emit."""
from __future__ import annotations

import datetime as dt

import pytest

from conftest import load_json, load_text
from nycsim_live import metar as M

REF = dt.datetime(2026, 9, 5, 19, 30, tzinfo=dt.timezone.utc)


# --------------------------------------------------------------------------- recorded reports
def test_parse_recorded_tgftp_knyc():
    r = M.parse_metar(load_text("metar_tgftp_KNYC.txt"), REF)
    assert r.station == "KNYC"
    assert (r.day, r.hour, r.minute) == (5, 18, 51)
    assert r.observation_time == dt.datetime(2026, 9, 5, 18, 51, tzinfo=dt.timezone.utc)
    assert r.auto is True
    assert r.wind_variable is True and r.wind_dir_deg is None
    assert r.wind_speed_mps == pytest.approx(6 * M.KT_TO_MPS, abs=1e-3)
    assert r.visibility_m == pytest.approx(M.VIS_UNLIMITED_M, abs=1.0)
    assert [c.cover for c in r.clouds] == ["SCT"]
    assert r.clouds[0].base_m == pytest.approx(8000 * M.FOOT_M, abs=1.0)
    assert r.temp_c == 25.0 and r.dewpoint_c == 13.9  # T-group refines 25/14
    assert r.altimeter_hpa == pytest.approx(29.86 * M.INHG_TO_HPA, abs=0.05)  # parser rounds to 0.1 hPa
    assert r.sea_level_pressure_hpa == pytest.approx(1010.1)
    assert r.weather == [] and r.unparsed == []


def test_parse_recorded_tgftp_klga():
    r = M.parse_metar(load_text("metar_tgftp_KLGA.txt"), REF)
    assert r.station == "KLGA"
    assert r.temp_c is not None and r.dewpoint_c is not None
    assert r.cavok is False
    assert r.unparsed == []


def test_split_reports_of_a_tgftp_file():
    parts = M.split_reports(load_text("metar_tgftp_KLGA.txt"))
    assert len(parts) == 1 and parts[0].splitlines()[0][:4] == "2026"


def test_every_recorded_awc_report_parses_without_leftovers():
    rows = load_json("metar_awc_weather_samples.json") + load_json("metar_awc_nyc.json")
    assert len(rows) >= 12
    for row in rows:
        raw = row["rawOb"]
        r = M.parse_metar(raw, REF)
        assert r.station == row["icaoId"], raw
        assert r.unparsed == [], f"unparsed {r.unparsed} in {raw}"
        if row.get("temp") is not None:
            assert r.temp_c == pytest.approx(row["temp"], abs=0.06), raw
        if row.get("dewp") is not None:
            assert r.dewpoint_c == pytest.approx(row["dewp"], abs=0.06), raw
        if row.get("wspd") is not None and not r.wind_calm:
            assert r.wind_speed_mps == pytest.approx(row["wspd"] * M.KT_TO_MPS, abs=1e-3), raw
        if row.get("wdir") not in (None, "VRB") and isinstance(row.get("wdir"), (int, float)) and row["wdir"] > 0:
            assert r.wind_dir_deg == pytest.approx(float(row["wdir"])), raw
        if row.get("visib") is not None and isinstance(row["visib"], (int, float)):
            assert r.visibility_m == pytest.approx(float(row["visib"]) * M.STATUTE_MILE_M, rel=0.02, abs=1.0), raw
        if row.get("altim") is not None:
            assert r.altimeter_hpa == pytest.approx(row["altim"], abs=0.6), raw


def test_awc_weather_string_matches_the_parsed_groups():
    for row in load_json("metar_awc_weather_samples.json"):
        if not row.get("wxString"):
            continue
        r = M.parse_metar(row["rawOb"], REF)
        parsed = {p for g in r.weather for p in g.phenomena}
        for tok in row["wxString"].split():
            core = tok.lstrip("+-").replace("VC", "")
            for i in range(0, len(core), 2):
                code = core[i : i + 2]
                if code in M.DESCRIPTORS:
                    continue
                assert code in parsed, f"{code} missing from {r.weather} for {row['rawOb']}"


# --------------------------------------------------------------------------- individual groups
@pytest.mark.parametrize(
    "token,speed_mps,direction,gust,calm,variable",
    [
        ("00000KT", 0.0, None, None, True, False),
        ("11005KT", 5 * M.KT_TO_MPS, 110.0, None, False, False),
        ("VRB06KT", 6 * M.KT_TO_MPS, None, None, False, True),
        ("34014G28KT", 14 * M.KT_TO_MPS, 340.0, 28 * M.KT_TO_MPS, False, False),
        ("18010MPS", 10.0, 180.0, None, False, False),
        ("27036KMH", 36 / 3.6, 270.0, None, False, False),
        ("/////KT", None, None, None, False, False),
    ],
)
def test_wind_groups(token, speed_mps, direction, gust, calm, variable):
    r = M.parse_metar(f"KNYC 051851Z {token} 10SM CLR 25/14 A2986", REF)
    assert r.wind_speed_mps == (None if speed_mps is None else pytest.approx(speed_mps, abs=1e-3))
    assert r.wind_dir_deg == (None if direction is None else pytest.approx(direction))
    assert r.wind_gust_mps == (None if gust is None else pytest.approx(gust, abs=1e-3))
    assert r.wind_calm is calm and r.wind_variable is variable


def test_variable_wind_range():
    r = M.parse_metar("KJFK 051851Z 24012KT 200V280 10SM CLR 25/14 A2986", REF)
    assert (r.wind_dir_from_deg, r.wind_dir_to_deg) == (200.0, 280.0)


@pytest.mark.parametrize(
    "token,metres",
    [
        ("10SM", M.VIS_UNLIMITED_M),
        ("1/2SM", 0.5 * M.STATUTE_MILE_M),
        ("2 1/2SM", 2.5 * M.STATUTE_MILE_M),
        ("M1/4SM", 0.25 * M.STATUTE_MILE_M),
        ("P6SM", 6 * M.STATUTE_MILE_M),
        ("3SM", 3 * M.STATUTE_MILE_M),
        ("0800", 800.0),
        ("9999", M.VIS_UNLIMITED_M),
    ],
)
def test_visibility_groups(token, metres):
    r = M.parse_metar(f"KNYC 051851Z 00000KT {token} CLR 25/14 A2986", REF)
    assert r.visibility_m == pytest.approx(metres, abs=1.0)


def test_visibility_qualifiers():
    assert M.parse_metar("KNYC 051851Z 00000KT M1/4SM FG 05/05 A2986", REF).visibility_less_than is True
    assert M.parse_metar("KNYC 051851Z 00000KT P6SM CLR 05/05 A2986", REF).visibility_greater_than is True


def test_cavok_sets_unlimited_visibility_and_clear_sky():
    r = M.parse_metar("EGLL 051850Z 25010KT CAVOK 20/10 Q1013", REF)
    assert r.cavok is True
    assert r.visibility_m == pytest.approx(M.VIS_UNLIMITED_M, abs=1.0)
    assert M.cloud_cover_fraction(r.clouds, r.sky_clear_code) == 0.0
    assert r.altimeter_hpa == pytest.approx(1013.0)


@pytest.mark.parametrize(
    "token,intensity,descriptor,phenomena",
    [
        ("-RA", "-", None, ("RA",)),
        ("+TSRA", "+", "TS", ("RA",)),
        ("VCTS", "VC", "TS", ()),
        ("FZRA", "", "FZ", ("RA",)),
        ("-SHRASN", "-", "SH", ("RA", "SN")),
        ("BR", "", None, ("BR",)),
        ("+BLSN", "+", "BL", ("SN",)),
        ("-FZDZ", "-", "FZ", ("DZ",)),
        ("PL", "", None, ("PL",)),
        ("TS", "", "TS", ()),
    ],
)
def test_weather_groups(token, intensity, descriptor, phenomena):
    r = M.parse_metar(f"KNYC 051851Z 00000KT 5SM {token} BKN020 02/01 A2986", REF)
    assert len(r.weather) == 1
    g = r.weather[0]
    assert (g.intensity, g.descriptor, g.phenomena) == (intensity, descriptor, phenomena)


def test_sky_groups():
    r = M.parse_metar("KJFK 051851Z 00000KT 10SM FEW015 SCT027 BKN037CB OVC250 18/15 A2994", REF)
    assert [c.cover for c in r.clouds] == ["FEW", "SCT", "BKN", "OVC"]
    assert r.clouds[2].cloud_type == "CB"
    assert r.clouds[0].base_m == pytest.approx(1500 * M.FOOT_M, abs=1.0)
    assert r.ceiling_m == pytest.approx(3700 * M.FOOT_M, abs=1.0)
    assert M.cloud_cover_fraction(r.clouds) == 1.0


def test_vertical_visibility():
    r = M.parse_metar("KNYC 051851Z 00000KT 1/4SM FG VV002 05/05 A2986", REF)
    assert r.vertical_visibility_m == pytest.approx(200 * M.FOOT_M, abs=0.1)
    assert M.cloud_cover_fraction(r.clouds, r.sky_clear_code) == 1.0


def test_negative_temperatures_and_t_group():
    r = M.parse_metar("KNYC 051851Z 00000KT 10SM CLR M05/M12 A3012 RMK AO2 T10501122", REF)
    assert r.temp_c == pytest.approx(-5.0) and r.dewpoint_c == pytest.approx(-12.2)


def test_missing_dewpoint():
    r = M.parse_metar("KNYC 051851Z 00000KT 10SM CLR 25/ A2986", REF)
    assert r.temp_c == 25.0 and r.dewpoint_c is None


def test_remark_groups():
    raw = ("KNYC 051851Z 00000KT 1SM -SN OVC008 M02/M04 A2986 RMK AO2 PK WND 31035/1825 SLP101 P0004 "
           "60012 70045 4/006 931025 933012 T10221039")
    r = M.parse_metar(raw, REF)
    assert r.sea_level_pressure_hpa == pytest.approx(1010.1)
    assert r.precip_last_hour_mm == pytest.approx(4 * M.HUNDREDTH_INCH_MM)
    assert r.precip_3_6h_mm == pytest.approx(12 * M.HUNDREDTH_INCH_MM)
    assert r.precip_24h_mm == pytest.approx(45 * M.HUNDREDTH_INCH_MM)
    assert r.snow_depth_cm == pytest.approx(6 * M.INCH_CM)
    assert r.snowfall_6h_cm == pytest.approx(2.5 * M.INCH_CM)
    assert r.snow_water_equivalent_mm == pytest.approx(1.2 * 25.4)
    assert r.peak_wind_dir_deg == 310.0 and r.peak_wind_mps == pytest.approx(35 * M.KT_TO_MPS, abs=1e-3)
    assert r.temp_c == pytest.approx(-2.2) and r.dewpoint_c == pytest.approx(-3.9)


def test_slp_wraparound():
    assert M.parse_metar("KNYC 051851Z 00000KT 10SM CLR 25/14 A2986 RMK SLP989", REF).sea_level_pressure_hpa == pytest.approx(998.9)
    assert M.parse_metar("KNYC 051851Z 00000KT 10SM CLR 25/14 A2986 RMK SLP101", REF).sea_level_pressure_hpa == pytest.approx(1010.1)


def test_trend_and_maintenance_flag():
    r = M.parse_metar("KLGA 051851Z 11005KT 10SM FEW018 19/14 A2993 NOSIG RMK AO2 $", REF)
    assert r.trend.startswith("NOSIG") and r.maintenance_flag is True


def test_nil_and_speci_and_cor():
    assert M.parse_metar("KNYC 051851Z NIL", REF).nil is True
    assert M.parse_metar("SPECI KJFK 051107Z 06004KT 10SM CLR 18/15 A2994", REF).report_type == "SPECI"
    assert M.parse_metar("METAR KNYC 051851Z COR 00000KT 10SM CLR 25/14 A2986", REF).corrected is True


def test_rvr_is_captured_not_dropped():
    r = M.parse_metar("KJFK 051851Z 04012KT 1/2SM R04R/2000FT FG OVC003 05/05 A2986", REF)
    assert r.rvr == ["R04R/2000FT"] and r.unparsed == []


@pytest.mark.parametrize("bad", ["", "   ", "KNYC", "NOT A METAR AT ALL"])
def test_malformed_reports_raise(bad):
    with pytest.raises(M.MetarParseError):
        M.parse_metar(bad, REF)


# --------------------------------------------------------------------------- observation time resolution
def test_observation_time_wraps_to_the_previous_month():
    ref = dt.datetime(2026, 10, 1, 0, 20, tzinfo=dt.timezone.utc)
    r = M.parse_metar("KNYC 302351Z 00000KT 10SM CLR 25/14 A2986", ref)
    assert r.observation_time == dt.datetime(2026, 9, 30, 23, 51, tzinfo=dt.timezone.utc)


def test_observation_time_never_lands_in_the_future():
    ref = dt.datetime(2026, 9, 5, 0, 10, tzinfo=dt.timezone.utc)
    r = M.parse_metar("KNYC 052351Z 00000KT 10SM CLR 25/14 A2986", ref)
    assert r.observation_time <= ref + dt.timedelta(minutes=15)


# --------------------------------------------------------------------------- semantics
@pytest.mark.parametrize(
    "wx,temp,kind",
    [
        ("-RA", 10.0, "rain"), ("+RA", 10.0, "rain"), ("-DZ", 10.0, "drizzle"),
        ("-SN", -3.0, "snow"), ("SN", -3.0, "snow"), ("PL", 0.0, "sleet"),
        ("-FZRA", -1.0, "freezing_rain"), ("FZDZ", -1.0, "freezing_rain"),
        ("-RASN", 1.0, "sleet"), ("GS", 5.0, "sleet"), ("UP", 5.0, "rain"), ("UP", -5.0, "snow"),
        ("BR", 10.0, "none"), ("VCSH", 10.0, "none"), ("HZ", 20.0, "none"),
    ],
)
def test_classify_precipitation(wx, temp, kind):
    r = M.parse_metar(f"KNYC 051851Z 00000KT 3SM {wx} BKN020 05/04 A2986", REF)
    assert M.classify_precipitation(r.weather, temp)[0] == kind


def test_precipitation_rate_basis_priority():
    r = M.parse_metar("KNYC 051851Z 00000KT 3SM -RA BKN020 10/09 A2986 RMK P0012", REF)
    rate, basis = M.precipitation_rate_mmph(r.weather, r.precip_last_hour_mm, 10.0)
    assert basis == "measured" and rate == pytest.approx(12 * M.HUNDREDTH_INCH_MM, abs=1e-3)
    r2 = M.parse_metar("KNYC 051851Z 00000KT 3SM -RA BKN020 10/09 A2986 RMK P0000", REF)
    assert M.precipitation_rate_mmph(r2.weather, r2.precip_last_hour_mm, 10.0) == (M.TRACE_RATE_MMPH, "trace")
    r3 = M.parse_metar("KNYC 051851Z 00000KT 3SM -RA BKN020 10/09 A2986", REF)
    assert M.precipitation_rate_mmph(r3.weather, None, 10.0) == (1.0, "class")
    r4 = M.parse_metar("KNYC 051851Z 00000KT 3SM TSRA BKN020 10/09 A2986", REF)
    assert M.precipitation_rate_mmph(r4.weather, None, 10.0) == (4.0 * M.THUNDERSTORM_RATE_FACTOR, "class")
    r5 = M.parse_metar("KNYC 051851Z 00000KT 10SM CLR 10/09 A2986", REF)
    assert M.precipitation_rate_mmph(r5.weather, None, 10.0) == (0.0, "none")


def test_obscuration_and_thunder():
    r = M.parse_metar("KNYC 051851Z 00000KT 1/4SM FG BR OVC002 05/05 A2986", REF)
    assert M.obscuration(r.weather) == {"FG", "BR"}
    assert M.thunder_present(r.weather) is False
    r2 = M.parse_metar("KNYC 051851Z 00000KT 5SM VCTS BKN030 25/20 A2986", REF)
    assert M.thunder_present(r2.weather) is True
    assert M.obscuration(r2.weather) == set()  # a vicinity group is not at the station


def test_cloud_cover_fraction_reports_none_when_the_sky_is_not_reported():
    assert M.cloud_cover_fraction([], None) is None
    assert M.cloud_cover_fraction([], "CLR") == 0.0
    assert M.cloud_cover_fraction([M.CloudLayer("FEW", 500.0, None)]) == pytest.approx(0.1875)
    assert M.cloud_cover_fraction([M.CloudLayer("FEW", 500.0, None), M.CloudLayer("BKN", 1000.0, None)]) == pytest.approx(0.75)
