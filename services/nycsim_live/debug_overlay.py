"""The exact text block the Unreal live-data debug overlay draws (toggled with F9 in-game).

``core/live/DebugOverlay.cpp`` builds the same string character for character from the same structs, so a
screenshot of the running game can be diffed against ``live/overlay.txt`` written here. The rules:

* one section per subsystem, in a fixed order, each headed by ``== NAME ==`` padded to :data:`WIDTH` with ``=``;
* one field per line, ``label`` left-padded to :data:`LABEL_W`, then ``: ``, then the value;
* **every** field of every snapshot appears, including nulls — a missing value renders as ``—`` (U+2014) and
  never as 0, so an operator can always tell "no data" from "zero";
* floats use a fixed number of decimals per field (never scientific notation), so the block never reflows;
* the header line carries the provider, the observation age and, when the data is stale, ``STALE`` plus the
  age in ``h m s``; a stale block is additionally marked by ``!`` in column 1 of every weather line.

The block is pure text with no ANSI escapes: Unreal draws it with a monospace font through
``UCanvas::DrawText``, and the same string is written to ``data/processed/live/overlay.txt`` for verification.
"""
from __future__ import annotations

import datetime as _dt
import math
from typing import Any, Final, Sequence

from . import astronomy, timesync
from .paths import OVERLAY_TXT, write_json_atomic  # noqa: F401 - OVERLAY_TXT is the documented sink
from .weather import WeatherObservation
from .worldmapping import WorldState

WIDTH: Final = 62
LABEL_W: Final = 22
NONE_TEXT: Final = "—"
STALE_LIMIT_S: Final = 3600.0  # older than this and the header shouts STALE even for a live provider
_COMPASS: Final = ("N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW")


# --------------------------------------------------------------------------- formatting primitives
def compass_point(heading_deg: float | None) -> str:
    """16-point compass abbreviation for a heading (each point spans 22.5°)."""
    if heading_deg is None:
        return NONE_TEXT
    return _COMPASS[int((heading_deg % 360.0) / 22.5 + 0.5) % 16]


def fmt_num(value: float | None, decimals: int = 1, unit: str = "", *, plus: bool = False) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return NONE_TEXT
    s = f"{value:+.{decimals}f}" if plus else f"{value:.{decimals}f}"
    return f"{s} {unit}".rstrip()


def fmt_bool(value: bool | None, true_text: str = "yes", false_text: str = "no") -> str:
    if value is None:
        return NONE_TEXT
    return true_text if value else false_text


def fmt_duration(seconds: float | None) -> str:
    """``1h 04m 09s`` / ``4m 09s`` / ``9s``; negative ages (clock skew) are shown with a leading ``-``."""
    if seconds is None:
        return NONE_TEXT
    sign = "-" if seconds < 0 else ""
    s = int(abs(seconds))
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    if h:
        return f"{sign}{h}h {m:02d}m {sec:02d}s"
    if m:
        return f"{sign}{m}m {sec:02d}s"
    return f"{sign}{sec}s"


def header(title: str) -> str:
    return f"== {title} ".ljust(WIDTH, "=")


def line(label: str, value: Any, mark: str = " ") -> str:
    return f"{mark}{label:<{LABEL_W}}: {value}"


def fmt_list(values: Sequence[Any] | None, empty: str = "none") -> str:
    if not values:
        return empty
    return ", ".join(str(v) for v in values)


# --------------------------------------------------------------------------- sections
def time_section(t: timesync.SimTime) -> list[str]:
    return [
        header("TIME"),
        line("utc", t.utc.strftime("%Y-%m-%d %H:%M:%S") + "Z"),
        line("local", t.local.strftime("%Y-%m-%d %H:%M:%S") + f" {t.tz_abbreviation}"),
        line("utc offset", f"{t.utc_offset_s / 3600:+.0f} h  dst={fmt_bool(t.is_dst)}"),
        line("julian day (UT)", f"{t.jd:.6f}"),
        line("julian day (TT)", f"{t.jde:.6f}"),
        line("delta T", fmt_num(t.delta_t_s, 3, "s")),
        line("day of year", str(t.day_of_year)),
    ]


def sun_section(sun: astronomy.SolarPosition, events: astronomy.SunEvents | None) -> list[str]:
    def t(x: _dt.datetime | None) -> str:
        return NONE_TEXT if x is None else x.astimezone(timesync.NYC_TZ).strftime("%H:%M:%S") if timesync.NYC_TZ else x.strftime("%H:%M:%SZ")

    out = [
        header("SUN (NREL SPA)"),
        line("azimuth", f"{fmt_num(sun.azimuth, 4, 'deg')}  {compass_point(sun.azimuth)}"),
        line("elevation", fmt_num(sun.elevation, 4, "deg", plus=True)),
        line("zenith", fmt_num(sun.zenith, 4, "deg")),
        line("refraction", fmt_num(sun.refraction, 4, "deg")),
        line("declination", fmt_num(sun.geocentric.delta, 4, "deg", plus=True)),
        line("right ascension", fmt_num(sun.geocentric.alpha, 4, "deg")),
        line("distance", fmt_num(sun.distance_au, 6, "AU")),
        line("semidiameter", fmt_num(sun.semidiameter, 4, "deg")),
    ]
    if events is not None:
        out += [
            line("sunrise / transit", f"{t(events.sunrise)} / {t(events.transit)}"),
            line("sunset", t(events.sunset)),
        ]
    return out


def moon_section(moon: astronomy.MoonPosition) -> list[str]:
    return [
        header("MOON (Meeus 47/48)"),
        line("azimuth", f"{fmt_num(moon.azimuth, 4, 'deg')}  {compass_point(moon.azimuth)}"),
        line("elevation", fmt_num(moon.elevation, 4, "deg", plus=True)),
        line("phase", f"{moon.phase_name} ({'waxing' if moon.waxing else 'waning'})"),
        line("illuminated", fmt_num(moon.illuminated_fraction * 100.0, 1, "%")),
        line("phase angle", fmt_num(moon.phase_angle, 2, "deg")),
        line("elongation", fmt_num(moon.elongation, 2, "deg")),
        line("distance", fmt_num(moon.distance_km, 0, "km")),
        line("semidiameter", fmt_num(moon.semidiameter, 4, "deg")),
    ]


def weather_section(obs: WeatherObservation, now_unix: float | None = None) -> list[str]:
    """Every field of ``weather.json`` (contract + extension), with the staleness marker in column 1."""
    stale = obs.source == "stale" or (obs.stale_age_s is not None and obs.stale_age_s > STALE_LIMIT_S)
    m = "!" if stale else " "
    age = obs.stale_age_s
    if now_unix is not None and obs.observed_unix() is not None:
        age = now_unix - (obs.observed_unix() or 0.0)
    head = f"{obs.source.upper()}  age {fmt_duration(age)}"
    if stale:
        head += "  ** STALE **"
    wind = NONE_TEXT
    if obs.wind_mps is not None:
        gust = "" if obs.wind_gust_mps is None else f" G{obs.wind_gust_mps:.1f}"
        d = NONE_TEXT if obs.wind_from_heading is None else f"{obs.wind_from_heading:.0f} deg {compass_point(obs.wind_from_heading)}"
        wind = f"{obs.wind_mps:.1f}{gust} m/s from {d}"
    return [
        header("WEATHER"),
        line("provider", head, m),
        line("station", obs.station or NONE_TEXT, m),
        line("observed at", obs.observed_at or NONE_TEXT, m),
        line("fetched at", obs.fetched_at or NONE_TEXT, m),
        line("stale age", fmt_duration(obs.stale_age_s), m),
        line("schema version", str(obs.schema_version), m),
        line("temperature", fmt_num(obs.temp_c, 1, "C", plus=True), m),
        line("dewpoint", fmt_num(obs.dewpoint_c, 1, "C", plus=True), m),
        line("relative humidity", fmt_num(obs.rh, 0, "%"), m),
        line("wind", wind, m),
        line("wind dir (math)", fmt_num(obs.wind_dir_deg, 1, "deg"), m),
        line("wind to", fmt_num(obs.wind_to_heading, 0, "deg"), m),
        line("precipitation", f"{obs.precip_type} {fmt_num(obs.precip_rate_mmph, 2, 'mm/h')} [{obs.precip_rate_basis}]", m),
        line("snowfall rate", fmt_num(obs.snowfall_rate_cmph, 2, "cm/h"), m),
        line("snow depth", f"{fmt_num(obs.snow_depth_cm, 1, 'cm')} [{obs.snow_depth_source}]", m),
        line("cloud cover", fmt_num(None if obs.cloud_cover is None else obs.cloud_cover * 100.0, 0, "%"), m),
        line("visibility", fmt_num(obs.visibility_m, 0, "m"), m),
        line("pressure (MSL)", fmt_num(obs.pressure_hpa, 1, "hPa"), m),
        line("thunder", fmt_bool(obs.thunder), m),
        line("obscuration", fmt_list(obs.obscuration), m),
        line("interpolated", fmt_bool(obs.interpolated), m),
        line("raw", (obs.raw_text or NONE_TEXT)[: WIDTH - LABEL_W - 3], m),
    ]


def providers_section(status: dict[str, str] | None) -> list[str]:
    out = [header("PROVIDERS")]
    if not status:
        return out + [line("state", NONE_TEXT)]
    for name in sorted(status):
        state = status[name]
        out.append(line(name, state, "!" if state.startswith("open") else " "))
    return out


def world_section(w: WorldState) -> list[str]:
    return [
        header("WORLD MAPPING"),
        line("wetness", f"{w.wetness:.3f} -> {w.wetness_target:.3f}  tau {w.tau_used_s:.0f}s {'dry' if w.drying else 'wet'}"),
        line("puddles", f"{w.puddle_level:.3f} ({w.puddle_depth_mm:.1f} mm)"),
        line("road ice", fmt_bool(w.road_ice)),
        line("snow cover", f"ground {w.snow_cover:.3f}  road {w.snow_cover_road:.3f}  depth {w.snow_depth_cm:.1f} cm"),
        line("snow melting", fmt_bool(w.snow_melting)),
        line("plow / salt", f"{fmt_bool(w.plow_active)} / {fmt_bool(w.salt_active)}"),
        line("fog density", f"{w.fog_density:.3f}  haze {w.haze_density:.3f}"),
        line("extinction", f"{w.extinction_per_m:.6f} 1/m"),
        line("wind vector ENU", "[" + ", ".join(f"{v:+.2f}" for v in w.wind_vector_enu) + "] m/s"),
        line("wind vector UE", "[" + ", ".join(f"{v:+.2f}" for v in w.wind_vector_ue) + "] m/s"),
        line("umbrella prob.", fmt_num(w.umbrella_probability * 100.0, 0, "%")),
        line("window condensation", f"single {w.window_condensation:.2f}  double {w.window_condensation_double:.2f}"),
        line("missing fields", fmt_list(w.missing)),
    ]


def esb_section(esb: dict | None) -> list[str]:
    out = [header("ESB TOWER LIGHTS")]
    if not esb:
        return out + [line("state", NONE_TEXT)]
    colors = esb.get("colors") or []
    rgb = esb.get("rgb") or []
    out += [
        line("date", esb.get("date") or NONE_TEXT),
        line("colors", fmt_list(colors)),
        line("rgb", fmt_list([f"({r},{g},{b})" for r, g, b in rgb]) if rgb else NONE_TEXT),
        line("hours", esb.get("hours") or NONE_TEXT),
        line("reason", (esb.get("reason") or NONE_TEXT)[: WIDTH - LABEL_W - 3]),
        line("fallback", fmt_bool(esb.get("fallback"))),
        line("fetched at", esb.get("fetched_at") or NONE_TEXT),
    ]
    return out


def tides_section(t: dict | None) -> list[str]:
    out = [header("TIDES / CURRENTS")]
    if not t:
        return out + [line("state", NONE_TEXT)]
    mark = "!" if t.get("stale") else " "
    out += [
        line("station", str(t.get("station")), mark),
        line("water level", f"{fmt_num(t.get('water_level_m'), 3, 'm')} NAVD88 ({fmt_num(t.get('water_level_mllw_m'), 3, 'm')} MLLW)", mark),
        line("observed at", t.get("water_level_observed_at") or NONE_TEXT, mark),
        line("current station", str(t.get("current_station")), mark),
        line("current", f"{fmt_num(t.get('current_speed_mps'), 3, 'm/s')} {compass_point(t.get('current_heading'))} [{t.get('current_phase') or NONE_TEXT}]", mark),
        line("current dir (math)", fmt_num(t.get("current_dir_deg"), 1, "deg"), mark),
    ]
    for n in (t.get("next_tides") or [])[:2]:
        out.append(line(f"next {n.get('kind')}", f"{n.get('utc')}  {fmt_num(n.get('level_m'), 3, 'm')}", mark))
    if t.get("errors"):
        out.append(line("errors", fmt_list(t["errors"])[: WIDTH - LABEL_W - 3], "!"))
    return out


# --------------------------------------------------------------------------- assembly
def render(
    sim_time: timesync.SimTime,
    obs: WeatherObservation,
    world: WorldState | None = None,
    sun: astronomy.SolarPosition | None = None,
    moon: astronomy.MoonPosition | None = None,
    sun_events: astronomy.SunEvents | None = None,
    esb: dict | None = None,
    tides: dict | None = None,
    observer: astronomy.Observer = astronomy.CENTRAL_PARK,
) -> str:
    """Build the whole overlay. Sun/moon are computed from ``sim_time`` when not supplied."""
    if sun is None:
        sun = astronomy.solar_position(sim_time.utc, observer)
    if moon is None:
        moon = astronomy.moon_position(sim_time.utc, observer)
    if sun_events is None:
        sun_events = astronomy.sun_events_local(_dt.date(*sim_time.local_date), observer)
    lines: list[str] = [f"NYCSim live data  {sim_time.utc.strftime('%Y-%m-%dT%H:%M:%SZ')}".ljust(WIDTH)]
    lines += time_section(sim_time)
    lines += sun_section(sun, sun_events)
    lines += moon_section(moon)
    lines += weather_section(obs, sim_time.unix_s)
    if world is not None:
        lines += world_section(world)
    lines += providers_section(obs.provider_status)
    lines += esb_section(esb)
    lines += tides_section(tides)
    lines.append("=" * WIDTH)
    return "\n".join(lines) + "\n"


def write(text: str, path=OVERLAY_TXT) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)
