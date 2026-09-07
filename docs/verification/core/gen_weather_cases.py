"""Generate core/tests/weather/weather_cases.h from services/nycsim_live/{metar,weather}.py.

Every expected value in the C++ weather tests is produced by running the Python reference over the
same fixture bytes that the C++ test reads from core/tests/data/weather/, so a divergence between
the two implementations fails the build.

Fixtures (all real, fetched live and archived in the repository):
  nws_KNYC.json / nws_KLGA.json / nws_KJFK.json   api.weather.gov observations/latest
  nws_gridpoint.json                              api.weather.gov gridpoints/OKX/34,45
  open_meteo.json                                 api.open-meteo.com /v1/forecast
  metar_*.txt                                     tgftp.nws.noaa.gov station reports
  awc_metar.json                                  aviationweather.gov METAR API
plus a curated list of METAR strings covering the whole present-weather grammar (documented FMH-1
examples and historical NYC reports).

Run: python3 docs/verification/core/gen_weather_cases.py > core/tests/weather/weather_cases.h
"""
from __future__ import annotations

import datetime as dt
import json
import math
import pathlib
import sys

sys.path.insert(0, "services")

from nycsim_live import metar as M, weather as W  # noqa: E402

DATA = pathlib.Path("core/tests/data/weather")

# Grammar coverage. Each entry: (label, report text, reference time ISO or None).
METAR_CASES: list[tuple[str, str, str]] = [
    ("calm_clear_knyc", "KNYC 061051Z 00000KT 10SM CLR 18/16 A2996 RMK AO2 SLP138 T01780156", "2026-09-06T11:00:00Z"),
    ("light_rain_bkn", "KLGA 141251Z 09012KT 4SM -RA BR BKN008 OVC015 12/11 A2985 RMK AO2 P0004 SLP108 T01220111", "2026-03-14T13:00:00Z"),
    ("heavy_thunderstorm", "KJFK 231954Z 24018G31KT 1 1/2SM +TSRA BR SCT012 BKN025CB OVC040 22/21 A2971 RMK AO2 TSB48 P0035 SLP055 T02220211", "2026-07-23T20:00:00Z"),
    ("moderate_snow", "KNYC 070851Z 03014G22KT 1/2SM SN FZFG VV006 M03/M05 A2978 RMK AO2 SNINCR 2/6 4/008 P0006 SLP086 T10281050", "2026-01-07T09:00:00Z"),
    ("freezing_rain", "KEWR 160951Z 05009KT 2SM -FZRA BR OVC006 M01/M02 A2996 RMK AO2 P0002 SLP146 T10061017", "2026-01-16T10:00:00Z"),
    ("ice_pellets_mix", "KLGA 041151Z 36011KT 3/4SM -PLSN OVC009 M01/M02 A3005 RMK AO2 P0003 SLP178 T10061017", "2026-02-04T12:00:00Z"),
    ("drizzle_fog", "KJFK 120651Z VRB03KT 1/4SM DZ FG VV002 09/09 A3011 RMK AO2 SLP196 T00890089", "2026-04-12T07:00:00Z"),
    ("vicinity_thunder", "KNYC 251851Z 20008KT 10SM VCTS SCT045CB BKN090 27/19 A2989 RMK AO2 TCU ALQDS SLP120 T02720189", "2026-06-25T19:00:00Z"),
    ("cavok_metres", "EGLL 011220Z 24008MPS CAVOK 15/07 Q1021 NOSIG", "2026-05-01T13:00:00Z"),
    ("metres_visibility", "LFPG 011230Z 27010KT 8000 -SHRA FEW012 SCT020 BKN035 14/11 Q1013 TEMPO 4000 SHRA", "2026-05-01T13:00:00Z"),
    ("rvr_and_variable", "KJFK 010851Z 31015G25KT 280V350 1/2SM R04R/2000FT FG VV002 05/05 A2970 RMK AO2 PK WND 32032/0812 SLP051 T00500050", "2026-11-01T09:00:00Z"),
    ("mixed_fraction_vis", "KEWR 020551Z 08006KT 1 3/4SM BR OVC004 07/07 A3021 RMK AO2 SLP231 T00720072", "2026-10-02T06:00:00Z"),
    ("missing_dewpoint", "KTEB 031451Z AUTO 25009KT 10SM SCT200 24/ A2999 RMK AO2", "2026-08-03T15:00:00Z"),
    ("haze_smoke", "KLGA 121751Z 22006KT 5SM HZ FU SKC 31/17 A2988 RMK AO2 SLP116 T03110172", "2026-06-12T18:00:00Z"),
    ("blowing_snow_heavy", "KJFK 291251Z 01025G38KT 1/4SM +SN BLSN VV003 M07/M10 A2951 RMK AO2 4/012 931025 933015 P0008 SLP998 T10721100", "2026-01-29T13:00:00Z"),
    ("hail_shower", "KEWR 152051Z 27020G35KT 2SM +TSRAGR SCT020 BKN035CB 24/19 A2980 RMK AO2 GR 1/2 P0045 SLP090 T02440189", "2026-05-15T21:00:00Z"),
    ("clear_q_pressure", "EDDF 011250Z 07004KT 9999 FEW035 21/09 Q1018 NOSIG", "2026-06-01T13:00:00Z"),
    ("nil_report", "KXYZ 011200Z NIL", "2026-06-01T13:00:00Z"),
    ("wind_missing_slash", "KJFK 011200Z /////KT 10SM CLR 20/10 A3000", "2026-06-01T13:00:00Z"),
    ("snow_grains_low_vis", "KNYC 050751Z 02008KT 0000 SG VV001 M05/M07 A3008 RMK AO2 4/003", "2026-02-05T08:00:00Z"),
]


def j(x):
    if x is None:
        return "kNaN"
    if isinstance(x, bool):
        return "true" if x else "false"
    if isinstance(x, float):
        if math.isnan(x):
            return "kNaN"
        return repr(x)
    return repr(x)


def s(x: str | None) -> str:
    return json.dumps(x or "")


def obsc_bits(codes) -> str:
    order = ["BR", "DS", "DU", "FC", "FG", "FU", "HZ", "PO", "PY", "SA", "SQ", "SS", "VA"]
    bits = 0
    mapping = {c: 1 << i for i, c in enumerate(["BR", "FG", "FU", "VA", "DU", "SA", "HZ", "PY", "PO", "SQ", "FC", "SS", "DS"])}
    for c in codes:
        bits |= mapping.get(c, 0)
    assert order  # keep the reference of the alphabetical order used by obscurationList
    return str(bits)


PRECIP_INDEX = {"none": 0, "rain": 1, "snow": 2, "sleet": 3, "freezing_rain": 4, "drizzle": 5}
BASIS_INDEX = {"none": 0, "measured": 1, "class": 2, "trace": 3, "model": 4}
SNOWSRC_INDEX = {"none": 0, "observed": 1, "model": 2}
SOURCE_INDEX = {"nws": 0, "open_meteo": 1, "metar": 2, "stale": 3}


def emit_state(name: str, obs: W.WeatherObservation, now: float) -> None:
    print(f"inline constexpr ExpectedState {name} = {{")
    print(f"    {s(obs.station)}, {SOURCE_INDEX[obs.source]}, {j(obs.observed_unix())},")
    print(f"    {j(obs.temp_c)}, {j(obs.dewpoint_c)}, {j(obs.rh)},")
    print(f"    {j(obs.wind_mps)}, {j(obs.wind_gust_mps)}, {j(obs.wind_dir_deg)},")
    print(f"    {j(obs.wind_from_heading)}, {j(obs.wind_to_heading)},")
    print(f"    {PRECIP_INDEX[obs.precip_type]}, {j(obs.precip_rate_mmph)}, {BASIS_INDEX[obs.precip_rate_basis]},")
    print(f"    {j(obs.cloud_cover)}, {j(obs.visibility_m)}, {j(obs.pressure_hpa)},")
    print(f"    {j(obs.snow_depth_cm)}, {SNOWSRC_INDEX[obs.snow_depth_source]}, {j(obs.snowfall_rate_cmph)},")
    print(f"    {j(obs.thunder)}, {obsc_bits(obs.obscuration)}, {j(now)},")
    print("};")


def main() -> int:
    print("// GENERATED by docs/verification/core/gen_weather_cases.py from")
    print("// services/nycsim_live/{metar,weather}.py over the fixtures in core/tests/data/weather/.")
    print("// DO NOT EDIT BY HAND.")
    print("#pragma once\n")
    print("#include <cstdint>\n#include <limits>\n")
    print("namespace nycsim_test_weather {\n")
    print("inline constexpr double kNaN = std::numeric_limits<double>::quiet_NaN();\n")
    print("struct ExpectedState {")
    print("  const char* station;\n  int32_t source;\n  double observed_at;")
    print("  double temp_c, dewpoint_c, rh;")
    print("  double wind_mps, wind_gust_mps, wind_dir_deg;")
    print("  double wind_from_heading, wind_to_heading;")
    print("  int32_t precip_type;\n  double precip_rate_mmph;\n  int32_t precip_rate_basis;")
    print("  double cloud_cover, visibility_m, pressure_hpa;")
    print("  double snow_depth_cm;\n  int32_t snow_depth_source;\n  double snowfall_rate_cmph;")
    print("  bool thunder;\n  uint16_t obscuration;\n  double now_unix;")
    print("};\n")

    # ---- METAR grammar cases
    print("struct MetarCase {")
    print("  const char* label;\n  const char* text;\n  double reference_unix;")
    print("  double observation_unix;")
    print("  const char* station;\n  bool nil;\n  bool automatic;")
    print("  double wind_dir, wind_speed, wind_gust;\n  bool wind_variable, wind_calm;")
    print("  double visibility_m;\n  bool vis_less, vis_greater, cavok;")
    print("  int32_t n_weather_groups, n_clouds, n_rvr, n_unparsed;")
    print("  double temp_c, dewpoint_c, altimeter_hpa, slp_hpa;")
    print("  double precip_1h_mm, snow_depth_cm, snowfall_6h_cm, snow_we_mm;")
    print("  double peak_wind_dir, peak_wind_mps;")
    print("  double ceiling_m, cloud_cover;")
    print("  int32_t precip_type;\n  double precip_rate;\n  int32_t precip_basis;")
    print("  bool thunder;\n  uint16_t obscuration;")
    print("  const char* trend;")
    print("};")
    print("inline constexpr MetarCase kMetarCases[] = {")
    for label, text, ref_iso in METAR_CASES:
        ref = dt.datetime.fromisoformat(ref_iso.replace("Z", "+00:00"))
        rep = M.parse_metar(text, ref)
        kind, _ = M.classify_precipitation(rep.weather, rep.temp_c)
        rate, basis = M.precipitation_rate_mmph(rep.weather, rep.precip_last_hour_mm, rep.temp_c)
        cover = M.cloud_cover_fraction(rep.clouds, rep.sky_clear_code)
        print(f"    {{{s(label)}, {s(text)}, {j(ref.timestamp())},")
        print(f"     {j(rep.observation_time.timestamp() if rep.observation_time else None)},")
        print(f"     {s(rep.station)}, {j(rep.nil)}, {j(rep.auto)},")
        print(f"     {j(rep.wind_dir_deg)}, {j(rep.wind_speed_mps)}, {j(rep.wind_gust_mps)}, "
              f"{j(rep.wind_variable)}, {j(rep.wind_calm)},")
        print(f"     {j(rep.visibility_m)}, {j(rep.visibility_less_than)}, {j(rep.visibility_greater_than)}, {j(rep.cavok)},")
        print(f"     {len(rep.weather)}, {len(rep.clouds)}, {len(rep.rvr)}, {len(rep.unparsed)},")
        print(f"     {j(rep.temp_c)}, {j(rep.dewpoint_c)}, {j(rep.altimeter_hpa)}, {j(rep.sea_level_pressure_hpa)},")
        print(f"     {j(rep.precip_last_hour_mm)}, {j(rep.snow_depth_cm)}, {j(rep.snowfall_6h_cm)}, {j(rep.snow_water_equivalent_mm)},")
        print(f"     {j(rep.peak_wind_dir_deg)}, {j(rep.peak_wind_mps)},")
        print(f"     {j(rep.ceiling_m)}, {j(cover)},")
        print(f"     {PRECIP_INDEX[kind]}, {j(rate)}, {BASIS_INDEX[basis]},")
        print(f"     {j(M.thunder_present(rep.weather))}, {obsc_bits(M.obscuration(rep.weather))},")
        print(f"     {s(rep.trend)}}},")
    print("};")
    print(f"inline constexpr int kMetarCaseCount = {len(METAR_CASES)};\n")

    # ---- live provider fixtures
    for station in ("KNYC", "KLGA", "KJFK"):
        doc = json.loads((DATA / f"nws_{station}.json").read_text())
        t_obs = W.parse_iso8601(doc["properties"]["timestamp"])
        now = t_obs + 300.0
        obs = W.parse_nws_observation(doc, now)
        emit_state(f"kNws{station}", obs, now)
        # the same observation carried along the gridpoint forecast trend
        blend = W.NWSForecastBlend(json.loads((DATA / "nws_gridpoint.json").read_text()))
        obs2 = W.parse_nws_observation(doc, t_obs + 3000.0)
        applied = blend.apply(obs2, t_obs + 3000.0)
        print(f"inline constexpr bool kNws{station}BlendApplied = {j(applied)};")
        emit_state(f"kNws{station}Blended", obs2, t_obs + 3000.0)
    om = json.loads((DATA / "open_meteo.json").read_text())
    t_om = W.parse_iso8601(om["current"]["time"])
    obs = W.parse_open_meteo(om, t_om + 120.0)
    emit_state("kOpenMeteo", obs, t_om + 120.0)

    for station in ("KNYC", "KLGA", "KJFK", "KEWR"):
        txt = (DATA / f"metar_{station}.txt").read_text()
        rep = M.parse_metar(txt, dt.datetime.now(tz=dt.timezone.utc))
        now = rep.observation_time.timestamp() + 600.0
        obs = W.observation_from_metar(rep, now)
        emit_state(f"kMetar{station}", obs, now)

    print("\n}  // namespace nycsim_test_weather")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
