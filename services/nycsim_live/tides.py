"""NOAA CO-OPS water level and tidal currents for the rivers (``live/tides.json``).

* Water level: The Battery (8518750), 6-minute verified/preliminary data, product ``water_level``,
  datum MLLW, metres, GMT. Converted to the world vertical datum (NAVD88, DATA_CONTRACTS §2/ARCHITECTURE §2)
  with the station datum sheet (``mdapi .../stations/8518750/datums.json?units=metric``): NAVD88 − MLLW
  = 0.846 m for the 1983–2001 epoch, so ``water_level_m = water_level_mllw_m − 0.846``.
* Currents: CO-OPS ``currents_predictions`` (30-min velocity along the principal flood/ebb axis, cm/s) for
  the harmonic current stations found via ``mdapi .../stations.json?type=currentpredictions`` inside the
  NY Harbor bbox: Hell Gate NYH1924 (East River, mean flood 045° / ebb 241°), The Narrows n03020
  (flood 328° / ebb 144°), Brooklyn Bridge NYH1920 (047°/234°), Hudson River Entrance NYH1927 (011°/183°).
  The velocity at ``now`` is linearly interpolated between the two enclosing predictions; sign > 0 is flood
  (toward meanFloodDir), < 0 is ebb (toward meanEbbDir).

Angle convention: ``current_dir_deg`` is the mathematical angle (0 = east, CCW) of the direction the water
flows *toward*; ``current_heading`` is its compass equivalent.
"""
from __future__ import annotations

import datetime as _dt
import logging
import math
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Final

from . import net
from .paths import TIDES_JSON, read_json, record_snapshot, write_json_atomic

log = logging.getLogger("nycsim.live.tides")

SCHEMA_VERSION: Final = 1
BATTERY_STATION: Final = "8518750"
COOPS_API: Final = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"
COOPS_MDAPI: Final = "https://api.tidesandcurrents.noaa.gov/mdapi/prod/webapi"
APPLICATION: Final = "NYCSim"
NAVD88_MINUS_MLLW_M_FALLBACK: Final = 0.846  # Battery datum sheet, epoch 1983-2001, fetched 2026-09-05
MAX_WATER_LEVEL_AGE_S: Final = 2 * 3600
CM_S_TO_M_S: Final = 0.01


@dataclass(frozen=True)
class CurrentStation:
    id: str
    name: str
    water_body: str
    lat: float
    lon: float


CURRENT_STATIONS: Final = (
    CurrentStation("NYH1924", "Hell Gate", "East River", 40.7783, -73.9383),
    CurrentStation("n03020", "The Narrows", "Upper Bay / Lower Bay", 40.6064, -74.0380),
    CurrentStation("NYH1920", "Brooklyn Bridge", "East River", 40.7060, -73.9977),
    CurrentStation("NYH1927", "Hudson River Entrance", "Hudson River", 40.7076, -74.0253),
)


class TidesError(RuntimeError):
    pass


def compass_to_math(heading_deg: float) -> float:
    return (90.0 - heading_deg) % 360.0


def _coops_time(s: str) -> float:
    """'2026-09-05 19:00' (GMT) → POSIX seconds."""
    return _dt.datetime.strptime(s, "%Y-%m-%d %H:%M").replace(tzinfo=_dt.timezone.utc).timestamp()


def _iso(unix_s: float) -> str:
    return _dt.datetime.fromtimestamp(unix_s, tz=_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def water_level_url(station: str = BATTERY_STATION) -> str:
    return f"{COOPS_API}?date=latest&station={station}&product=water_level&datum=MLLW&time_zone=gmt&units=metric&format=json&application={APPLICATION}"


def hilo_predictions_url(station: str, begin_utc: _dt.datetime, hours: int = 48) -> str:
    return f"{COOPS_API}?begin_date={begin_utc.strftime('%Y%m%d%%20%H:%M')}&range={hours}&station={station}&product=predictions&datum=MLLW&time_zone=gmt&units=metric&interval=hilo&format=json&application={APPLICATION}"


def currents_url(station: str, begin_utc: _dt.datetime, hours: int = 48, interval: str = "30") -> str:
    return f"{COOPS_API}?begin_date={begin_utc.strftime('%Y%m%d%%20%H:%M')}&range={hours}&station={station}&product=currents_predictions&time_zone=gmt&units=metric&interval={interval}&format=json&application={APPLICATION}"


def datums_url(station: str = BATTERY_STATION) -> str:
    return f"{COOPS_MDAPI}/stations/{station}/datums.json?units=metric"


# --------------------------------------------------------------------------- parsers (pure)
@dataclass(frozen=True)
class WaterLevel:
    station: str
    observed_unix: float
    level_mllw_m: float
    sigma_m: float | None
    flags: str
    quality: str  # p preliminary / v verified


def parse_water_level(doc: dict) -> WaterLevel:
    if "error" in doc:
        raise TidesError(f"CO-OPS error: {doc['error'].get('message')}")
    data = doc.get("data") or []
    if not data:
        raise TidesError("CO-OPS water_level: empty data")
    row = data[-1]
    if row.get("v") in (None, ""):
        raise TidesError("CO-OPS water_level: missing value")
    sigma = row.get("s")
    return WaterLevel(str(doc.get("metadata", {}).get("id", "")), _coops_time(row["t"]), float(row["v"]), float(sigma) if sigma not in (None, "") else None, row.get("f", ""), row.get("q", ""))


def parse_datum_offset(doc: dict) -> float:
    """NAVD88 − MLLW (m) from a datums.json document (values are relative to station datum STND)."""
    if "error" in doc:
        raise TidesError(f"CO-OPS datums error: {doc['error'].get('message')}")
    vals = {d.get("name"): d.get("value") for d in doc.get("datums", []) if isinstance(d, dict)}
    if vals.get("NAVD88") is None or vals.get("MLLW") is None:
        raise TidesError("datums.json without NAVD88/MLLW")
    if str(doc.get("units", "meters")).lower() not in ("meters", "metric", "m"):
        raise TidesError(f"datums.json in unexpected units {doc.get('units')!r}")
    return float(vals["NAVD88"]) - float(vals["MLLW"])


@dataclass(frozen=True)
class CurrentPrediction:
    unix: float
    velocity_cms: float  # + flood, − ebb along the principal axis
    kind: str  # "" for interval series; "flood"/"ebb"/"slack" for MAX_SLACK series


@dataclass(frozen=True)
class CurrentSeries:
    station: str
    bin: str
    depth_m: float | None
    flood_dir_deg: float  # compass
    ebb_dir_deg: float  # compass
    predictions: tuple[CurrentPrediction, ...]


def parse_currents(doc: dict, station: str) -> CurrentSeries:
    if "error" in doc:
        raise TidesError(f"CO-OPS currents error: {doc['error'].get('message')}")
    cp = (doc.get("current_predictions") or {}).get("cp") or []
    if not cp:
        raise TidesError(f"CO-OPS currents {station}: empty predictions")
    first = cp[0]
    preds = tuple(CurrentPrediction(_coops_time(r["Time"]), float(r["Velocity_Major"]), str(r.get("Type", "")).lower()) for r in cp if r.get("Velocity_Major") not in (None, ""))
    depth = first.get("Depth")
    return CurrentSeries(station, str(first.get("Bin", "")), float(depth) if depth not in (None, "") else None, float(first["meanFloodDir"]), float(first["meanEbbDir"]), tuple(sorted(preds, key=lambda p: p.unix)))


def interpolate_velocity(series: CurrentSeries, unix_s: float) -> float | None:
    """Linear interpolation of the along-axis velocity (cm/s); None outside the predicted span."""
    p = series.predictions
    if not p or unix_s < p[0].unix or unix_s > p[-1].unix:
        return None
    lo, hi = 0, len(p) - 1
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if p[mid].unix <= unix_s:
            lo = mid
        else:
            hi = mid
    if p[hi].unix == p[lo].unix:
        return p[lo].velocity_cms
    f = (unix_s - p[lo].unix) / (p[hi].unix - p[lo].unix)
    return p[lo].velocity_cms + f * (p[hi].velocity_cms - p[lo].velocity_cms)


def velocity_to_flow(series: CurrentSeries, velocity_cms: float) -> tuple[float, float, str]:
    """(speed m/s, compass heading of the flow, phase) — phase is flood/ebb/slack (|v| < 5 cm/s)."""
    speed = abs(velocity_cms) * CM_S_TO_M_S
    if abs(velocity_cms) < 5.0:
        phase = "slack"
    else:
        phase = "flood" if velocity_cms > 0 else "ebb"
    heading = series.flood_dir_deg if velocity_cms >= 0 else series.ebb_dir_deg
    return speed, heading, phase


@dataclass(frozen=True)
class TidePrediction:
    unix: float
    level_mllw_m: float
    kind: str  # H | L


def parse_hilo(doc: dict) -> list[TidePrediction]:
    if "error" in doc:
        raise TidesError(f"CO-OPS predictions error: {doc['error'].get('message')}")
    return [TidePrediction(_coops_time(r["t"]), float(r["v"]), r.get("type", "")) for r in doc.get("predictions", []) if r.get("v") not in (None, "")]


# --------------------------------------------------------------------------- snapshot
@dataclass
class TidesSnapshot:
    """DATA_CONTRACTS §12 ``tides.json`` + §12.1 extension."""

    station: str = BATTERY_STATION
    current_speed_mps: float | None = None  # Hell Gate (East River), primary river-flow station
    current_dir_deg: float | None = None  # mathematical convention, flow direction
    water_level_m: float | None = None  # NAVD88 metres (world vertical datum)
    predicted_at: str | None = None  # ISO-8601 UTC instant the currents were evaluated for
    schema_version: int = SCHEMA_VERSION
    current_station: str = "NYH1924"
    current_heading: float | None = None  # compass, flow direction
    current_phase: str | None = None  # flood | ebb | slack
    water_level_datum: str = "NAVD88"
    water_level_mllw_m: float | None = None
    water_level_observed_at: str | None = None
    water_level_quality: str | None = None
    navd88_minus_mllw_m: float = NAVD88_MINUS_MLLW_M_FALLBACK
    currents: list[dict] = field(default_factory=list)  # per station: id, name, water_body, lat, lon, speed_mps, heading, dir_deg, phase, velocity_cms
    next_tides: list[dict] = field(default_factory=list)  # upcoming H/L at The Battery (NAVD88 and MLLW)
    fetched_at: str | None = None
    stale: bool = False
    errors: list[str] = field(default_factory=list)

    def to_json_dict(self) -> dict:
        d = {
            "schema_version": self.schema_version, "station": self.station, "current_speed_mps": self.current_speed_mps, "current_dir_deg": self.current_dir_deg,
            "water_level_m": self.water_level_m, "predicted_at": self.predicted_at,
            "current_station": self.current_station, "current_heading": self.current_heading, "current_phase": self.current_phase,
            "water_level_datum": self.water_level_datum, "water_level_mllw_m": self.water_level_mllw_m, "water_level_observed_at": self.water_level_observed_at,
            "water_level_quality": self.water_level_quality, "navd88_minus_mllw_m": self.navd88_minus_mllw_m, "currents": self.currents, "next_tides": self.next_tides,
            "fetched_at": self.fetched_at, "stale": self.stale, "errors": self.errors,
        }
        for k in ("current_speed_mps", "current_dir_deg", "water_level_m", "current_heading", "water_level_mllw_m", "navd88_minus_mllw_m"):
            if d[k] is not None:
                d[k] = round(float(d[k]), 4)
        return d


class TidesService:
    """Water level every poll (6-min data), currents/hi-lo predictions cached per UTC day, datums per day."""

    def __init__(self, out_path: Path = TIDES_JSON, fetch: Callable[..., net.Response] = net.get, clock: Callable[[], float] = time.time, stations: tuple[CurrentStation, ...] = CURRENT_STATIONS, primary: str = "NYH1924"):
        self.out_path = out_path
        self._fetch = fetch
        self.clock = clock
        self.stations = stations
        self.primary = primary
        self.datum_offset: float = NAVD88_MINUS_MLLW_M_FALLBACK
        self._datum_fetched: float = 0.0
        self.currents: dict[str, CurrentSeries] = {}
        self._currents_day: str = ""
        self.hilo: list[TidePrediction] = []
        self.last_water_level: WaterLevel | None = None
        self.current: TidesSnapshot | None = None

    def _refresh_datums(self, now: float, errors: list[str]) -> None:
        if now - self._datum_fetched < 86400:
            return
        try:
            self.datum_offset = parse_datum_offset(self._fetch(datums_url(BATTERY_STATION)).json())
            self._datum_fetched = now
        except (net.HttpError, TidesError, ValueError) as e:
            errors.append(f"datums: {e} (using {self.datum_offset:.3f} m)")

    def _refresh_predictions(self, now: float, errors: list[str]) -> None:
        day = _dt.datetime.fromtimestamp(now, tz=_dt.timezone.utc).strftime("%Y%m%d")
        if day == self._currents_day and len(self.currents) == len(self.stations) and self.hilo:
            return
        begin = _dt.datetime.fromtimestamp(now, tz=_dt.timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0) - _dt.timedelta(hours=1)
        ok = True
        for st in self.stations:
            if st.id in self.currents and self.currents[st.id].predictions and self.currents[st.id].predictions[-1].unix > now + 6 * 3600:
                continue
            try:
                self.currents[st.id] = parse_currents(self._fetch(currents_url(st.id, begin)).json(), st.id)
            except (net.HttpError, TidesError, ValueError, KeyError) as e:
                ok = False
                errors.append(f"currents {st.id}: {e}")
        try:
            self.hilo = parse_hilo(self._fetch(hilo_predictions_url(BATTERY_STATION, begin)).json())
        except (net.HttpError, TidesError, ValueError, KeyError) as e:
            ok = False
            errors.append(f"hilo: {e}")
        if ok:
            self._currents_day = day

    def poll(self) -> TidesSnapshot:
        now = self.clock()
        errors: list[str] = []
        self._refresh_datums(now, errors)
        self._refresh_predictions(now, errors)
        snap = TidesSnapshot(fetched_at=_iso(now), navd88_minus_mllw_m=self.datum_offset, current_station=self.primary)
        try:
            wl = parse_water_level(self._fetch(water_level_url()).json())
            if now - wl.observed_unix > MAX_WATER_LEVEL_AGE_S:
                raise TidesError(f"water level too old ({(now - wl.observed_unix) / 60:.0f} min)")
            self.last_water_level = wl
        except (net.HttpError, TidesError, ValueError, KeyError) as e:
            errors.append(f"water_level: {e}")
            wl = self.last_water_level
            snap.stale = True
        if wl is not None:
            snap.water_level_mllw_m = wl.level_mllw_m
            snap.water_level_m = wl.level_mllw_m - self.datum_offset
            snap.water_level_observed_at = _iso(wl.observed_unix)
            snap.water_level_quality = wl.quality
        for st in self.stations:
            s = self.currents.get(st.id)
            v = interpolate_velocity(s, now) if s else None
            entry = {"id": st.id, "name": st.name, "water_body": st.water_body, "lat": st.lat, "lon": st.lon, "speed_mps": None, "heading": None, "dir_deg": None, "phase": None, "velocity_cms": None, "flood_heading": s.flood_dir_deg if s else None, "ebb_heading": s.ebb_dir_deg if s else None, "depth_m": s.depth_m if s else None}
            if s is not None and v is not None:
                speed, heading, phase = velocity_to_flow(s, v)
                entry.update({"speed_mps": round(speed, 4), "heading": heading, "dir_deg": round(compass_to_math(heading), 4), "phase": phase, "velocity_cms": round(v, 2)})
                if st.id == self.primary:
                    snap.current_speed_mps, snap.current_heading, snap.current_phase = speed, heading, phase
                    snap.current_dir_deg = compass_to_math(heading)
            elif s is None:
                snap.stale = True
            snap.currents.append(entry)
        snap.predicted_at = _iso(now)
        snap.next_tides = [{"utc": _iso(p.unix), "kind": p.kind, "level_mllw_m": p.level_mllw_m, "level_m": round(p.level_mllw_m - self.datum_offset, 4)} for p in self.hilo if p.unix >= now][:4]
        snap.errors = errors
        self.current = snap
        try:
            write_json_atomic(self.out_path, snap.to_json_dict())
        except OSError as e:
            log.error("cannot write %s: %s", self.out_path, e)
        return snap
