"""Live NYC weather: NWS → Open-Meteo → METAR → stale (ADR-011), writing ``live/weather.json``.

Every provider produces the same :class:`WeatherObservation` (DATA_CONTRACTS §12 ``weather.json`` plus
the §12.1 extension appended by this stage). Nothing here invents weather: a value is either taken from a
provider, derived from provider data by a documented formula (RH from T/Td, class-representative rates
for categorical intensity, forecast-anchored blending between hourly observations, snow-depth model), or
``null``. When no provider answers, the last good observation is re-emitted with ``source = "stale"`` and
its age.

Angle convention (DATA_CONTRACTS preamble): ``wind_dir_deg`` is mathematical (0 = east, counter-clockwise)
for the direction the wind blows *from*; the compass equivalents are in the extension fields
``wind_from_heading`` (meteorological) and ``wind_to_heading`` (air-motion direction).
"""
from __future__ import annotations

import datetime as _dt
import json
import logging
import math
import re
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable, Final, Iterable, Sequence

from . import metar as _metar
from . import net
from .paths import LIVE_DIR, SNOW_STATE_JSON, WEATHER_JSON, read_json, record_snapshot, write_json_atomic

log = logging.getLogger("nycsim.live.weather")

SCHEMA_VERSION: Final = 1
PRECIP_TYPES: Final = ("none", "rain", "snow", "sleet", "freezing_rain", "drizzle")
SOURCES: Final = ("nws", "open_meteo", "metar", "stale")
MAX_OBSERVATION_AGE_S: Final = 2.5 * 3600  # older observations are treated as a provider failure
BLEND_MIN_AGE_S: Final = 10 * 60  # observations younger than this are used as-is
POLL_INTERVAL_S: Final = 60.0
CENTRAL_PARK_LAT: Final = 40.7831
CENTRAL_PARK_LON: Final = -73.9712
KMH_TO_MPS: Final = 1.0 / 3.6


class ProviderError(RuntimeError):
    """A provider could not deliver a usable observation this poll (counts as one breaker failure)."""


# --------------------------------------------------------------------------- contract dataclass
@dataclass
class WeatherObservation:
    """DATA_CONTRACTS §12 ``weather.json`` (fields up to ``stale_age_s``) + §12.1 extension."""

    schema_version: int = SCHEMA_VERSION
    observed_at: str | None = None  # ISO-8601 UTC of the observation
    station: str | None = None
    source: str = "stale"  # nws | open_meteo | metar | stale
    temp_c: float | None = None
    dewpoint_c: float | None = None
    rh: float | None = None  # percent 0..100
    wind_mps: float | None = None
    wind_gust_mps: float | None = None
    wind_dir_deg: float | None = None  # mathematical convention, direction the wind blows FROM
    precip_type: str = "none"
    precip_rate_mmph: float | None = None  # liquid-equivalent
    cloud_cover: float | None = None  # 0..1
    visibility_m: float | None = None
    pressure_hpa: float | None = None  # sea-level
    snow_depth_cm: float | None = None
    thunder: bool = False
    fetched_at: str | None = None  # ISO-8601 UTC of the poll that produced this record
    stale_age_s: float | None = None  # seconds between observed_at and fetched_at
    # ---- §12.1 extension
    wind_from_heading: float | None = None  # compass, meteorological "from"
    wind_to_heading: float | None = None  # compass, direction of air motion
    snow_depth_source: str = "none"  # observed | model | none
    snowfall_rate_cmph: float | None = None  # fresh snow accumulation rate
    precip_rate_basis: str = "none"  # measured | class | trace | model | none
    obscuration: list[str] = field(default_factory=list)  # e.g. ["FG"], ["BR"], ["HZ"]
    interpolated: bool = False  # forecast-anchored blend applied (NWS only)
    raw_text: str | None = None  # provider raw report (METAR string / NWS textDescription / WMO code)
    provider_status: dict[str, str] = field(default_factory=dict)  # breaker state per provider

    def to_json_dict(self) -> dict:
        d = asdict(self)
        for k in ("temp_c", "dewpoint_c", "rh", "wind_mps", "wind_gust_mps", "wind_dir_deg", "precip_rate_mmph", "cloud_cover", "visibility_m", "pressure_hpa", "snow_depth_cm", "stale_age_s", "wind_from_heading", "wind_to_heading", "snowfall_rate_cmph"):
            if d[k] is not None:
                d[k] = round(float(d[k]), 3)
        return d

    def observed_unix(self) -> float | None:
        return parse_iso8601(self.observed_at) if self.observed_at else None


CONTRACT_KEYS: Final = ("schema_version", "observed_at", "station", "source", "temp_c", "dewpoint_c", "rh", "wind_mps", "wind_gust_mps", "wind_dir_deg", "precip_type", "precip_rate_mmph", "cloud_cover", "visibility_m", "pressure_hpa", "snow_depth_cm", "thunder", "fetched_at", "stale_age_s")
EXTENSION_KEYS: Final = ("wind_from_heading", "wind_to_heading", "snow_depth_source", "snowfall_rate_cmph", "precip_rate_basis", "obscuration", "interpolated", "raw_text", "provider_status")


# --------------------------------------------------------------------------- small numeric helpers (ported 1:1)
def parse_iso8601(s: str) -> float:
    """ISO-8601 → POSIX seconds. Accepts 'Z', ±hh:mm, fractional seconds, and Open-Meteo's tz-less minutes (UTC)."""
    s = s.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2}(\.\d+)?)?", s):
        s += "+00:00"
    return _dt.datetime.fromisoformat(s).timestamp()


def iso_utc(unix_s: float) -> str:
    return _dt.datetime.fromtimestamp(unix_s, tz=_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def compass_to_math(heading_deg: float) -> float:
    """Compass (0 = N, clockwise) → mathematical (0 = E, counter-clockwise), degrees in [0, 360)."""
    return (90.0 - heading_deg) % 360.0


def math_to_compass(math_deg: float) -> float:
    return (90.0 - math_deg) % 360.0


def relative_humidity(temp_c: float, dewpoint_c: float) -> float:
    """August–Roche–Magnus (a = 17.625, b = 243.04 °C); percent, clamped 0..100."""
    a, b = 17.625, 243.04
    rh = 100.0 * math.exp(a * dewpoint_c / (b + dewpoint_c)) / math.exp(a * temp_c / (b + temp_c))
    return max(0.0, min(100.0, rh))


def dewpoint_from_rh(temp_c: float, rh_percent: float) -> float:
    a, b = 17.625, 243.04
    rh = max(0.1, min(100.0, rh_percent)) / 100.0
    g = math.log(rh) + a * temp_c / (b + temp_c)
    return b * g / (a - g)


def set_wind(obs: WeatherObservation, from_heading: float | None) -> None:
    if from_heading is None:
        obs.wind_dir_deg = obs.wind_from_heading = obs.wind_to_heading = None
        return
    h = float(from_heading) % 360.0
    obs.wind_from_heading = h
    obs.wind_to_heading = (h + 180.0) % 360.0
    obs.wind_dir_deg = compass_to_math(h)


def clamp(x: float, lo: float, hi: float) -> float:
    return lo if x < lo else hi if x > hi else x


# --------------------------------------------------------------------------- circuit breaker
class CircuitBreaker:
    """3 consecutive failures → open for 5 min → half-open probe → closed on success (ADR-011)."""

    CLOSED, OPEN, HALF_OPEN = "closed", "open", "half_open"

    def __init__(self, name: str, failure_threshold: int = 3, open_seconds: float = 300.0):
        self.name = name
        self.failure_threshold = failure_threshold
        self.open_seconds = open_seconds
        self.state = self.CLOSED
        self.consecutive_failures = 0
        self.opened_at: float | None = None
        self.last_error: str | None = None
        self.last_success_at: float | None = None

    def allow(self, now: float) -> bool:
        if self.state == self.OPEN:
            assert self.opened_at is not None
            if now - self.opened_at >= self.open_seconds:
                self.state = self.HALF_OPEN
                return True
            return False
        return True

    def record_success(self, now: float) -> None:
        self.state = self.CLOSED
        self.consecutive_failures = 0
        self.opened_at = None
        self.last_error = None
        self.last_success_at = now

    def record_failure(self, now: float, error: str) -> None:
        self.consecutive_failures += 1
        self.last_error = error
        if self.state == self.HALF_OPEN or self.consecutive_failures >= self.failure_threshold:
            self.state = self.OPEN
            self.opened_at = now

    def status(self, now: float) -> str:
        if self.state == self.OPEN and self.opened_at is not None:
            return f"open({max(0.0, self.open_seconds - (now - self.opened_at)):.0f}s)"
        return self.state


# --------------------------------------------------------------------------- NWS
NWS_STATIONS: Final = ("KNYC", "KLGA", "KJFK")
NWS_OBS_URL: Final = "https://api.weather.gov/stations/{station}/observations/latest"
NWS_GRIDPOINT_URL: Final = "https://api.weather.gov/gridpoints/OKX/34,45"  # from /points/40.7831,-73.9712 (Central Park)
NWS_GRIDPOINT_TTL_S: Final = 30 * 60
NWS_BAD_QC: Final = frozenset({"X", "Q", "B"})  # MADIS: rejected, questioned, subjective-bad

# NWS presentWeather.weather → (precip kind, obscuration code). Kinds are the contract enum.
NWS_WEATHER_MAP: Final[dict[str, tuple[str | None, str | None]]] = {
    "rain": ("rain", None), "rain_showers": ("rain", None), "drizzle": ("drizzle", None),
    "snow": ("snow", None), "snow_showers": ("snow", None), "snow_grains": ("snow", None), "ice_crystals": ("snow", None),
    "sleet": ("sleet", None), "ice_pellets": ("sleet", None), "hail": ("sleet", None), "snow_pellets": ("sleet", None),
    "freezing_rain": ("freezing_rain", None), "freezing_drizzle": ("freezing_rain", None),
    "unknown_precipitation": ("rain", None), "unknown": (None, None),
    "thunderstorms": (None, None), "fog_mist": (None, "BR"), "fog": (None, "FG"), "freezing_fog": (None, "FG"),
    "haze": (None, "HZ"), "smoke": (None, "FU"), "dust": (None, "DU"), "sand": (None, "SA"), "volcanic_ash": (None, "VA"),
    "squalls": (None, "SQ"), "funnel_cloud": (None, "FC"), "dust_whirls": (None, "PO"), "sandstorm": (None, "SS"), "duststorm": (None, "DS"),
}
NWS_INTENSITY_CODE: Final = {"light": "-", None: "", "": "", "moderate": "", "heavy": "+"}


def _qc_value(field: dict | None) -> float | None:
    if not field or field.get("value") is None:
        return None
    if field.get("qualityControl") in NWS_BAD_QC:
        return None
    return float(field["value"])


def _duration_seconds(iso: str) -> float:
    m = re.fullmatch(r"P(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?)?", iso)
    if not m:
        raise ValueError(f"bad ISO duration {iso}")
    d, h, mi, s = (int(x) if x else 0 for x in m.groups())
    return d * 86400 + h * 3600 + mi * 60 + s


class GridSeries:
    """One NWS gridpoint layer as (start_unix, value) samples; piecewise-linear between sample starts."""

    def __init__(self, layer: dict | None, scale: float = 1.0):
        self.t: list[float] = []
        self.v: list[float] = []
        for entry in (layer or {}).get("values", []):
            if entry.get("value") is None:
                continue
            start, _, dur = entry["validTime"].partition("/")
            t0 = parse_iso8601(start)
            self.t.append(t0)
            self.v.append(float(entry["value"]) * scale)
            if dur:  # hold the value to the end of its validity so long segments do not tilt the interpolation
                self.t.append(t0 + _duration_seconds(dur) - 1)
                self.v.append(float(entry["value"]) * scale)
        pairs = sorted(zip(self.t, self.v))
        self.t = [p[0] for p in pairs]
        self.v = [p[1] for p in pairs]

    def value_at(self, unix_s: float) -> float | None:
        if len(self.t) < 2 or unix_s < self.t[0] or unix_s > self.t[-1]:
            return None
        lo, hi = 0, len(self.t) - 1
        while hi - lo > 1:
            mid = (lo + hi) // 2
            if self.t[mid] <= unix_s:
                lo = mid
            else:
                hi = mid
        if self.t[hi] == self.t[lo]:
            return self.v[lo]
        f = (unix_s - self.t[lo]) / (self.t[hi] - self.t[lo])
        return self.v[lo] + f * (self.v[hi] - self.v[lo])


class NWSForecastBlend:
    """Forecast-anchored interpolation between hourly observations.

    value(now) = obs + [F(now) − F(t_obs)], where F is the NWS gridpoint forecast layer for the same
    quantity. The observation is never replaced, only carried along the forecast trend; the correction is
    clamped (±5 °C, ±5 m/s, ±40 % sky, ±25 % RH) and only applied when the observation is older than
    ``BLEND_MIN_AGE_S``. Wind direction and precipitation are never interpolated.
    """

    LIMITS: Final = {"temp_c": 5.0, "dewpoint_c": 5.0, "wind_mps": 5.0, "wind_gust_mps": 6.0, "cloud_cover": 0.4, "rh": 25.0, "visibility_m": 8000.0}

    def __init__(self, gridpoint_json: dict):
        p = gridpoint_json["properties"]
        self.update_time = parse_iso8601(p["updateTime"]) if p.get("updateTime") else None
        self.series = {
            "temp_c": GridSeries(p.get("temperature")),
            "dewpoint_c": GridSeries(p.get("dewpoint")),
            "rh": GridSeries(p.get("relativeHumidity")),
            "wind_mps": GridSeries(p.get("windSpeed"), KMH_TO_MPS),
            "wind_gust_mps": GridSeries(p.get("windGust"), KMH_TO_MPS),
            "cloud_cover": GridSeries(p.get("skyCover"), 0.01),
            "visibility_m": GridSeries(p.get("visibility")),
        }

    def apply(self, obs: WeatherObservation, now_unix: float) -> bool:
        t_obs = obs.observed_unix()
        if t_obs is None or now_unix - t_obs < BLEND_MIN_AGE_S:
            return False
        changed = False
        for key, series in self.series.items():
            cur = getattr(obs, key)
            if cur is None:
                continue
            f_now, f_obs = series.value_at(now_unix), series.value_at(t_obs)
            if f_now is None or f_obs is None:
                continue
            delta = clamp(f_now - f_obs, -self.LIMITS[key], self.LIMITS[key])
            new = cur + delta
            if key == "cloud_cover":
                new = clamp(new, 0.0, 1.0)
            elif key == "rh":
                new = clamp(new, 0.0, 100.0)
            elif key in ("wind_mps", "wind_gust_mps", "visibility_m"):
                new = max(0.0, new)
            setattr(obs, key, new)
            changed = True
        if changed and obs.temp_c is not None and obs.dewpoint_c is not None:
            obs.dewpoint_c = min(obs.dewpoint_c, obs.temp_c)
            obs.rh = relative_humidity(obs.temp_c, obs.dewpoint_c)
        obs.interpolated = changed
        return changed


def parse_nws_observation(doc: dict, now_unix: float) -> WeatherObservation:
    """api.weather.gov ``observations/latest`` GeoJSON → observation. Raises ProviderError if unusable."""
    p = doc.get("properties") or {}
    if not p.get("timestamp"):
        raise ProviderError("NWS observation without timestamp")
    t_obs = parse_iso8601(p["timestamp"])
    if now_unix - t_obs > MAX_OBSERVATION_AGE_S:
        raise ProviderError(f"NWS observation too old ({(now_unix - t_obs) / 60:.0f} min)")
    temp = _qc_value(p.get("temperature"))
    if temp is None:
        raise ProviderError("NWS observation without temperature")
    obs = WeatherObservation(source="nws", observed_at=iso_utc(t_obs), station=p.get("stationId") or (p.get("station") or "").rsplit("/", 1)[-1] or None)
    obs.temp_c = temp
    obs.dewpoint_c = _qc_value(p.get("dewpoint"))
    rh = _qc_value(p.get("relativeHumidity"))
    if rh is None and obs.dewpoint_c is not None:
        rh = relative_humidity(temp, obs.dewpoint_c)
    obs.rh = rh
    if obs.dewpoint_c is None and rh is not None:
        obs.dewpoint_c = dewpoint_from_rh(temp, rh)
    ws = _qc_value(p.get("windSpeed"))
    obs.wind_mps = None if ws is None else ws * KMH_TO_MPS
    wg = _qc_value(p.get("windGust"))
    obs.wind_gust_mps = None if wg is None else wg * KMH_TO_MPS
    wd = _qc_value(p.get("windDirection"))
    set_wind(obs, None if (wd is None or (ws == 0.0 and wd == 0.0)) else wd)
    obs.visibility_m = _qc_value(p.get("visibility"))
    slp = _qc_value(p.get("seaLevelPressure"))
    bp = _qc_value(p.get("barometricPressure"))
    obs.pressure_hpa = (slp if slp is not None else bp) / 100.0 if (slp is not None or bp is not None) else None
    # present weather
    groups: list[_metar.WeatherGroup] = []
    obsc: set[str] = set()
    thunder = False
    for w in p.get("presentWeather") or []:
        kind, ob = NWS_WEATHER_MAP.get((w.get("weather") or "").lower(), (None, None))
        raw = w.get("rawString") or ""
        if raw:
            try:
                # a synthetic but *valid* time group: parse_metar rejects day 00, and the time is unused here
                g = _metar.parse_metar(f"XXXX 010000Z {raw}").weather
                groups.extend(g)
            except _metar.MetarParseError:
                pass
        if (w.get("weather") or "").lower() == "thunderstorms" or w.get("modifier") == "thunderstorms" or raw.startswith(("TS", "-TS", "+TS", "VCTS")):
            thunder = True
        if ob:
            obsc.add(ob)
        if kind and not raw:  # no raw group: synthesize the group from the decoded fields for classification
            code = NWS_INTENSITY_CODE.get(w.get("intensity"), "")
            phen = {"rain": ("RA",), "drizzle": ("DZ",), "snow": ("SN",), "sleet": ("PL",), "freezing_rain": ("RA",)}[kind]
            groups.append(_metar.WeatherGroup(kind, code, "FZ" if kind == "freezing_rain" else None, phen))
    obs.thunder = thunder or _metar.thunder_present(groups)
    obs.obscuration = sorted(obsc | _metar.obscuration(groups))
    kind, _ = _metar.classify_precipitation(groups, temp)
    obs.precip_type = kind
    p1h = _qc_value(p.get("precipitationLastHour"))
    rate, basis = _metar.precipitation_rate_mmph(groups, p1h, temp)
    if kind == "none" and p1h is not None and p1h > 0.0:
        # measured precipitation without a present-weather group (ASOS between showers): type from temperature
        kind = "rain" if temp > 1.0 else "snow"
        obs.precip_type, rate, basis = kind, p1h, "measured"
    obs.precip_rate_mmph, obs.precip_rate_basis = rate, basis
    layers = [_metar.CloudLayer(c["amount"], (c.get("base") or {}).get("value"), None) for c in (p.get("cloudLayers") or []) if c.get("amount") in _metar.COVER_FRACTION]
    obs.cloud_cover = _metar.cloud_cover_fraction(layers, "CLR" if (p.get("cloudLayers") == [] and p.get("textDescription")) else None)
    raw_msg = p.get("rawMessage") or ""
    if raw_msg:
        try:
            r = _metar.parse_metar(raw_msg, _dt.datetime.fromtimestamp(now_unix, tz=_dt.timezone.utc))
            if r.snow_depth_cm is not None:
                obs.snow_depth_cm, obs.snow_depth_source = r.snow_depth_cm, "observed"
            if obs.pressure_hpa is None and r.sea_level_pressure_hpa is not None:
                obs.pressure_hpa = r.sea_level_pressure_hpa
        except _metar.MetarParseError as e:
            log.debug("rawMessage not parseable: %s", e)
    obs.raw_text = raw_msg or p.get("textDescription")
    return obs


class NWSProvider:
    name = "nws"

    def __init__(self, stations: Sequence[str] = NWS_STATIONS, gridpoint_url: str = NWS_GRIDPOINT_URL, fetch: Callable[..., net.Response] = net.get, use_forecast_blend: bool = True):
        self.stations = tuple(stations)
        self.gridpoint_url = gridpoint_url
        self._fetch = fetch
        self.use_forecast_blend = use_forecast_blend
        self._blend: NWSForecastBlend | None = None
        self._blend_fetched: float = 0.0

    def _gridpoint(self, now_unix: float) -> NWSForecastBlend | None:
        if not self.use_forecast_blend:
            return None
        if self._blend is None or now_unix - self._blend_fetched > NWS_GRIDPOINT_TTL_S:
            try:
                self._blend = NWSForecastBlend(self._fetch(self.gridpoint_url, accept="application/geo+json").json())
                self._blend_fetched = now_unix
            except (net.HttpError, KeyError, ValueError) as e:
                log.warning("NWS gridpoint forecast unavailable: %s", e)
                if self._blend is not None and now_unix - self._blend_fetched > 6 * 3600:
                    self._blend = None  # do not carry a forecast older than 6 h
        return self._blend

    def fetch(self, now_unix: float) -> WeatherObservation:
        errors = []
        for st in self.stations:
            try:
                doc = self._fetch(NWS_OBS_URL.format(station=st), accept="application/geo+json").json()
                obs = parse_nws_observation(doc, now_unix)
            except (net.HttpError, ProviderError, KeyError, ValueError) as e:
                errors.append(f"{st}: {e}")
                continue
            blend = self._gridpoint(now_unix)
            if blend is not None:
                blend.apply(obs, now_unix)
            return obs
        raise ProviderError("; ".join(errors) or "no NWS station configured")


# --------------------------------------------------------------------------- Open-Meteo
OPEN_METEO_URL: Final = (
    "https://api.open-meteo.com/v1/forecast?latitude=40.7831&longitude=-73.9712"
    "&current=temperature_2m,relative_humidity_2m,dew_point_2m,precipitation,rain,showers,snowfall,weather_code,cloud_cover,pressure_msl,wind_speed_10m,wind_direction_10m,wind_gusts_10m"
    "&minutely_15=temperature_2m,precipitation,rain,snowfall,weather_code,visibility,wind_speed_10m,wind_direction_10m,wind_gusts_10m"
    "&forecast_minutely_15=12&timezone=UTC&wind_speed_unit=ms"
)

# WMO 4677 code (as used by Open-Meteo) → (precip_type, intensity code, thunder, obscuration)
WMO_CODE_MAP: Final[dict[int, tuple[str, str, bool, str | None]]] = {
    0: ("none", "", False, None), 1: ("none", "", False, None), 2: ("none", "", False, None), 3: ("none", "", False, None),
    45: ("none", "", False, "FG"), 48: ("none", "", False, "FG"),
    51: ("drizzle", "-", False, None), 53: ("drizzle", "", False, None), 55: ("drizzle", "+", False, None),
    56: ("freezing_rain", "-", False, None), 57: ("freezing_rain", "+", False, None),
    61: ("rain", "-", False, None), 63: ("rain", "", False, None), 65: ("rain", "+", False, None),
    66: ("freezing_rain", "-", False, None), 67: ("freezing_rain", "+", False, None),
    71: ("snow", "-", False, None), 73: ("snow", "", False, None), 75: ("snow", "+", False, None), 77: ("snow", "-", False, None),
    80: ("rain", "-", False, None), 81: ("rain", "", False, None), 82: ("rain", "+", False, None),
    85: ("snow", "-", False, None), 86: ("snow", "+", False, None),
    95: ("rain", "", True, None), 96: ("sleet", "", True, None), 99: ("sleet", "+", True, None),
}


def parse_open_meteo(doc: dict, now_unix: float) -> WeatherObservation:
    if doc.get("error"):
        raise ProviderError(f"Open-Meteo error: {doc.get('reason')}")
    cur = doc.get("current")
    if not cur or cur.get("temperature_2m") is None:
        raise ProviderError("Open-Meteo response without current block")
    t_obs = parse_iso8601(cur["time"])
    if now_unix - t_obs > MAX_OBSERVATION_AGE_S:
        raise ProviderError("Open-Meteo current block too old")
    interval_s = float(cur.get("interval") or 900)
    obs = WeatherObservation(source="open_meteo", observed_at=iso_utc(t_obs), station=f"open-meteo:{doc.get('latitude')},{doc.get('longitude')}")
    obs.temp_c = float(cur["temperature_2m"])
    obs.rh = None if cur.get("relative_humidity_2m") is None else float(cur["relative_humidity_2m"])
    obs.dewpoint_c = None if cur.get("dew_point_2m") is None else float(cur["dew_point_2m"])
    if obs.dewpoint_c is None and obs.rh is not None:
        obs.dewpoint_c = dewpoint_from_rh(obs.temp_c, obs.rh)
    if obs.rh is None and obs.dewpoint_c is not None:
        obs.rh = relative_humidity(obs.temp_c, obs.dewpoint_c)
    obs.wind_mps = None if cur.get("wind_speed_10m") is None else float(cur["wind_speed_10m"])
    obs.wind_gust_mps = None if cur.get("wind_gusts_10m") is None else float(cur["wind_gusts_10m"])
    set_wind(obs, None if cur.get("wind_direction_10m") is None or obs.wind_mps == 0.0 else float(cur["wind_direction_10m"]))
    obs.cloud_cover = None if cur.get("cloud_cover") is None else clamp(float(cur["cloud_cover"]) / 100.0, 0.0, 1.0)
    obs.pressure_hpa = None if cur.get("pressure_msl") is None else float(cur["pressure_msl"])
    code = int(cur.get("weather_code") or 0)
    kind, intensity, thunder, obsc = WMO_CODE_MAP.get(code, ("none", "", False, None))
    per_h = 3600.0 / interval_s
    precip = float(cur.get("precipitation") or 0.0) * per_h  # mm in the interval → mm/h
    rain = float(cur.get("rain") or 0.0) + float(cur.get("showers") or 0.0)
    snow_cm = float(cur.get("snowfall") or 0.0)  # cm in the interval
    if kind == "none" and precip > 0.0:  # code says dry but the model produced precipitation: type from partition
        kind = "sleet" if (rain > 0.0 and snow_cm > 0.0) else ("snow" if snow_cm > 0.0 else "rain")
    if kind != "none":
        if precip > 0.0:
            obs.precip_rate_mmph, obs.precip_rate_basis = precip, "measured"
        else:
            obs.precip_rate_mmph, obs.precip_rate_basis = _metar.INTENSITY_RATE_MMPH[kind][intensity], "class"
    else:
        obs.precip_rate_mmph, obs.precip_rate_basis = 0.0, "none"
    obs.precip_type = kind
    obs.thunder = thunder
    obs.obscuration = [obsc] if obsc else []
    obs.snowfall_rate_cmph = snow_cm * per_h if snow_cm > 0.0 else (0.0 if kind in ("snow", "sleet") else None)
    # visibility comes from the minutely_15 block at the current time
    m15 = doc.get("minutely_15") or {}
    times = m15.get("time") or []
    vis = m15.get("visibility") or []
    if times and vis:
        best = None
        for i, ts in enumerate(times):
            if i < len(vis) and vis[i] is not None:
                d = abs(parse_iso8601(ts) - t_obs)
                if best is None or d < best[0]:
                    best = (d, float(vis[i]))
        if best is not None and best[0] <= 15 * 60:
            obs.visibility_m = best[1]
    obs.raw_text = f"WMO {code}"
    return obs


class OpenMeteoProvider:
    name = "open_meteo"

    def __init__(self, url: str = OPEN_METEO_URL, fetch: Callable[..., net.Response] = net.get):
        self.url = url
        self._fetch = fetch

    def fetch(self, now_unix: float) -> WeatherObservation:
        try:
            return parse_open_meteo(self._fetch(self.url).json(), now_unix)
        except (net.HttpError, KeyError, ValueError) as e:
            raise ProviderError(str(e)) from e


# --------------------------------------------------------------------------- METAR
METAR_STATIONS: Final = ("KNYC", "KLGA", "KJFK", "KEWR")
METAR_AWC_URL: Final = "https://aviationweather.gov/api/data/metar?ids=KLGA,KJFK,KNYC,KEWR&format=json"
METAR_TGFTP_URL: Final = "https://tgftp.nws.noaa.gov/data/observations/metar/stations/{station}.TXT"


def observation_from_metar(rep: _metar.MetarReport, now_unix: float, obs_time_unix: float | None = None) -> WeatherObservation:
    t_obs = obs_time_unix if obs_time_unix is not None else (rep.observation_time.timestamp() if rep.observation_time else None)
    if t_obs is None:
        raise ProviderError(f"METAR {rep.station} without resolvable time")
    if now_unix - t_obs > MAX_OBSERVATION_AGE_S:
        raise ProviderError(f"METAR {rep.station} too old ({(now_unix - t_obs) / 60:.0f} min)")
    if rep.temp_c is None or rep.nil:
        raise ProviderError(f"METAR {rep.station} without temperature")
    obs = WeatherObservation(source="metar", observed_at=iso_utc(t_obs), station=rep.station)
    obs.temp_c = rep.temp_c
    obs.dewpoint_c = rep.dewpoint_c
    obs.rh = relative_humidity(rep.temp_c, rep.dewpoint_c) if rep.dewpoint_c is not None else None
    obs.wind_mps = rep.wind_speed_mps
    obs.wind_gust_mps = rep.wind_gust_mps
    set_wind(obs, None if (rep.wind_variable or rep.wind_calm) else rep.wind_dir_deg)
    obs.visibility_m = rep.visibility_m
    obs.pressure_hpa = rep.sea_level_pressure_hpa if rep.sea_level_pressure_hpa is not None else rep.altimeter_hpa
    kind, _ = _metar.classify_precipitation(rep.weather, rep.temp_c)
    obs.precip_type = kind
    obs.precip_rate_mmph, obs.precip_rate_basis = _metar.precipitation_rate_mmph(rep.weather, rep.precip_last_hour_mm, rep.temp_c)
    obs.thunder = _metar.thunder_present(rep.weather)
    obs.obscuration = sorted(_metar.obscuration(rep.weather))
    obs.cloud_cover = _metar.cloud_cover_fraction(rep.clouds, rep.sky_clear_code)
    if rep.snow_depth_cm is not None:
        obs.snow_depth_cm, obs.snow_depth_source = rep.snow_depth_cm, "observed"
    obs.raw_text = rep.raw
    return obs


class METARProvider:
    name = "metar"

    def __init__(self, stations: Sequence[str] = METAR_STATIONS, awc_url: str = METAR_AWC_URL, tgftp_url: str = METAR_TGFTP_URL, fetch: Callable[..., net.Response] = net.get):
        self.stations = tuple(stations)
        self.awc_url = awc_url
        self.tgftp_url = tgftp_url
        self._fetch = fetch

    def fetch(self, now_unix: float) -> WeatherObservation:
        errors: list[str] = []
        now_dt = _dt.datetime.fromtimestamp(now_unix, tz=_dt.timezone.utc)
        try:
            rows = self._fetch(self.awc_url).json()
            if not isinstance(rows, list):
                raise ProviderError("AWC METAR response is not a list")
            by_id = {r.get("icaoId"): r for r in rows if isinstance(r, dict)}
            for st in self.stations:
                r = by_id.get(st)
                if not r or not r.get("rawOb"):
                    errors.append(f"{st}: not in AWC response")
                    continue
                try:
                    rep = _metar.parse_metar(r["rawOb"], now_dt)
                    return observation_from_metar(rep, now_unix, float(r["obsTime"]) if r.get("obsTime") else None)
                except (_metar.MetarParseError, ProviderError, ValueError) as e:
                    errors.append(f"{st}: {e}")
        except (net.HttpError, ProviderError, ValueError) as e:
            errors.append(f"awc: {e}")
        for st in self.stations:
            try:
                txt = self._fetch(self.tgftp_url.format(station=st)).text
                rep = _metar.parse_metar(txt, now_dt)
                return observation_from_metar(rep, now_unix)
            except (net.HttpError, _metar.MetarParseError, ProviderError, ValueError) as e:
                errors.append(f"tgftp {st}: {e}")
        raise ProviderError("; ".join(errors))


# --------------------------------------------------------------------------- snow depth model
@dataclass
class SnowState:
    depth_cm: float = 0.0
    last_update_unix: float | None = None
    source: str = "none"  # observed | model | none


class SnowModel:
    """Snow depth when no station reports it (KNYC/KLGA/KJFK METARs carry 4/sss only during snow events).

    Per update with elapsed Δt (h, capped at 6):
      accumulation  += snowfall_rate_cmph·Δt where the rate is Open-Meteo's ``snowfall`` when available, else
                       liquid mm/h × SLR/10 with snow-to-liquid ratio SLR(T) = 8 (T ≥ 0 °C), 10 (−5…0),
                       13 (−10…−5), 18 (< −10) for snow and 3 for sleet (Roebber et al. 2003 climatology bands);
      melt          −= 0.06·max(0, T − 1 °C)·Δt   [cm/h per °C above 1 °C: ≈ 4 mm SWE/(°C·day) at ρ = 0.3]
      rain-on-snow  −= 0.02·rain_rate_mmph·Δt
      settling       ×= (1 − 0.02·Δt/24)            [2 %/day compaction]
    An observed depth (4/sss group) resets the model state. Depth is clamped ≥ 0 and the source is
    reported as "observed", "model" (depth > 0) or "none".
    """

    MAX_STEP_H: Final = 6.0
    MELT_CM_PER_H_PER_C: Final = 0.06
    RAIN_MELT_CM_PER_MM: Final = 0.02
    SETTLE_PER_DAY: Final = 0.02

    def __init__(self, state_path: Path | None = SNOW_STATE_JSON):
        self.state_path = state_path
        self.state = SnowState()
        if state_path is not None:
            doc = read_json(state_path)
            if doc and isinstance(doc.get("depth_cm"), (int, float)):
                self.state = SnowState(float(doc["depth_cm"]), doc.get("last_update_unix"), doc.get("source", "model"))

    @staticmethod
    def snow_liquid_ratio(temp_c: float | None, precip_type: str) -> float:
        if precip_type == "sleet":
            return 3.0
        if temp_c is None or temp_c >= 0.0:
            return 8.0
        if temp_c >= -5.0:
            return 10.0
        if temp_c >= -10.0:
            return 13.0
        return 18.0

    def update(self, obs: WeatherObservation, now_unix: float) -> None:
        s = self.state
        if obs.snow_depth_source == "observed" and obs.snow_depth_cm is not None:
            s.depth_cm, s.source = float(obs.snow_depth_cm), "observed"
        else:
            dt_h = 0.0 if s.last_update_unix is None else clamp((now_unix - s.last_update_unix) / 3600.0, 0.0, self.MAX_STEP_H)
            depth = s.depth_cm
            rate_cmph = 0.0
            if obs.precip_type in ("snow", "sleet") and (obs.precip_rate_mmph or 0.0) > 0.0:
                if obs.snowfall_rate_cmph is not None and obs.snowfall_rate_cmph > 0.0:
                    rate_cmph = obs.snowfall_rate_cmph
                else:
                    rate_cmph = (obs.precip_rate_mmph or 0.0) * self.snow_liquid_ratio(obs.temp_c, obs.precip_type) / 10.0
                    obs.snowfall_rate_cmph = rate_cmph
            depth += rate_cmph * dt_h
            if obs.temp_c is not None and obs.temp_c > 1.0:
                depth -= self.MELT_CM_PER_H_PER_C * (obs.temp_c - 1.0) * dt_h
            if obs.precip_type in ("rain", "drizzle", "freezing_rain") and (obs.precip_rate_mmph or 0.0) > 0.0:
                depth -= self.RAIN_MELT_CM_PER_MM * (obs.precip_rate_mmph or 0.0) * dt_h
            depth *= max(0.0, 1.0 - self.SETTLE_PER_DAY * dt_h / 24.0)
            s.depth_cm = max(0.0, depth)
            s.source = "model" if s.depth_cm > 0.0 else "none"
            obs.snow_depth_cm = round(s.depth_cm, 2)
            obs.snow_depth_source = s.source
        s.last_update_unix = now_unix
        if self.state_path is not None:
            try:
                write_json_atomic(self.state_path, {"schema_version": SCHEMA_VERSION, "depth_cm": s.depth_cm, "last_update_unix": s.last_update_unix, "source": s.source})
            except OSError as e:
                log.warning("cannot persist snow state: %s", e)


# --------------------------------------------------------------------------- service
class WeatherService:
    """Ordered providers, per-provider circuit breaker, stale fallback, JSON snapshot on every poll."""

    def __init__(self, providers: Iterable | None = None, out_path: Path = WEATHER_JSON, poll_interval_s: float = POLL_INTERVAL_S, clock: Callable[[], float] = time.time, snow_model: SnowModel | None = None, breaker_factory: Callable[[str], CircuitBreaker] = CircuitBreaker):
        self.providers = list(providers) if providers is not None else [NWSProvider(), OpenMeteoProvider(), METARProvider()]
        self.breakers = {p.name: breaker_factory(p.name) for p in self.providers}
        self.out_path = out_path
        self.poll_interval_s = poll_interval_s
        self.clock = clock
        self.snow_model = snow_model if snow_model is not None else SnowModel()
        self.last_good: WeatherObservation | None = None
        self.current: WeatherObservation | None = None
        self.polls = 0
        self.failures = 0
        prev = read_json(out_path)
        if prev and prev.get("source") in SOURCES and prev.get("observed_at"):
            try:
                self.last_good = WeatherObservation(**{k: v for k, v in prev.items() if k in WeatherObservation.__dataclass_fields__})
                if self.last_good.source == "stale":
                    self.last_good.source = "stale"
            except TypeError:
                self.last_good = None

    def _status(self, now: float) -> dict[str, str]:
        return {name: b.status(now) for name, b in self.breakers.items()}

    def poll(self) -> WeatherObservation:
        now = self.clock()
        self.polls += 1
        obs: WeatherObservation | None = None
        for p in self.providers:
            b = self.breakers[p.name]
            if not b.allow(now):
                log.debug("breaker %s open, skipping", p.name)
                continue
            try:
                obs = p.fetch(now)
            except ProviderError as e:
                b.record_failure(now, str(e))
                log.warning("provider %s failed (%d consecutive): %s", p.name, b.consecutive_failures, e)
                continue
            except Exception as e:  # noqa: BLE001 - a provider bug must not kill the loop; it counts as a failure
                b.record_failure(now, f"{type(e).__name__}: {e}")
                log.exception("provider %s raised", p.name)
                continue
            b.record_success(now)
            break
        if obs is not None:
            obs.fetched_at = iso_utc(now)
            t_obs = obs.observed_unix()
            obs.stale_age_s = max(0.0, now - t_obs) if t_obs is not None else None
            self.snow_model.update(obs, now)
            self.last_good = obs
        else:
            self.failures += 1
            if self.last_good is not None:
                obs = WeatherObservation(**{k: v for k, v in asdict(self.last_good).items()})
                obs.source = "stale"
                obs.fetched_at = iso_utc(now)
                t_obs = obs.observed_unix()
                obs.stale_age_s = max(0.0, now - t_obs) if t_obs is not None else None
                obs.interpolated = False
                self.snow_model.update(obs, now)  # keep melting/settling from the last known temperature
            else:
                obs = WeatherObservation(source="stale", fetched_at=iso_utc(now), stale_age_s=None)
                obs.snow_depth_source = "none"
        obs.provider_status = self._status(now)
        self.current = obs
        self.write(obs)
        return obs

    def write(self, obs: WeatherObservation) -> None:
        try:
            write_json_atomic(self.out_path, obs.to_json_dict())
        except OSError as e:
            log.error("cannot write %s: %s", self.out_path, e)

    def run(self, once: bool = False, max_polls: int | None = None) -> None:
        n = 0
        while True:
            t0 = self.clock()
            obs = self.poll()
            n += 1
            log.info("weather %s %s T=%s precip=%s rate=%s cover=%s age=%s", obs.source, obs.station, obs.temp_c, obs.precip_type, obs.precip_rate_mmph, obs.cloud_cover, obs.stale_age_s)
            if once or (max_polls is not None and n >= max_polls):
                return
            delay = self.poll_interval_s - (self.clock() - t0)
            if delay > 0:
                time.sleep(delay)


def validate_contract(doc: dict) -> list[str]:
    """Return schema violations for a weather.json document (empty list == valid)."""
    errs = []
    for k in CONTRACT_KEYS:
        if k not in doc:
            errs.append(f"missing {k}")
    if doc.get("schema_version") != SCHEMA_VERSION:
        errs.append("schema_version")
    if doc.get("source") not in SOURCES:
        errs.append(f"source {doc.get('source')!r}")
    if doc.get("precip_type") not in PRECIP_TYPES:
        errs.append(f"precip_type {doc.get('precip_type')!r}")
    cc = doc.get("cloud_cover")
    if cc is not None and not 0.0 <= cc <= 1.0:
        errs.append("cloud_cover range")
    if not isinstance(doc.get("thunder"), bool):
        errs.append("thunder not bool")
    wd = doc.get("wind_dir_deg")
    if wd is not None and not 0.0 <= wd < 360.0:
        errs.append("wind_dir_deg range")
    return errs
