"""METAR / SPECI parser (FMH-1 chapter 12, ICAO Annex 3) — reference for ``core/live/Metar.cpp``.

Handles the body groups: report type, station, day/time, AUTO/COR, wind (KT/MPS/KMH, VRB, gusts,
direction variation), visibility (statute miles incl. mixed fractions and M/P prefixes, metres with
direction, CAVOK), RVR, present-weather groups (intensity/vicinity, descriptors MI BC PR DR BL SH TS FZ,
precipitation DZ RA SN SG IC PL GR GS UP, obscurations BR FG FU VA DU SA HZ PY, other PO SQ FC SS DS),
sky (SKC CLR NSC NCD FEW SCT BKN OVC VV, heights in hundreds of feet, CB/TCU), temperature/dew point
(M prefix, missing dew point), altimeter (A inHg, Q hPa), and the remarks used by the simulation:
SLP, T-group (0.1 °C), P-group (hourly precipitation, 0.01 in), 4/sss snow depth (in), 931/933 snow
groups, PK WND. Trend groups (NOSIG/TEMPO/BECMG/FM) terminate body parsing.

Units are converted to SI at parse time: m/s, metres, °C, hPa, mm, cm.
"""
from __future__ import annotations

import datetime as _dt
import re
from dataclasses import dataclass, field
from typing import Final

KT_TO_MPS: Final = 0.514444  # 1852 m / 3600 s
KMH_TO_MPS: Final = 1.0 / 3.6
STATUTE_MILE_M: Final = 1609.344
FOOT_M: Final = 0.3048
INHG_TO_HPA: Final = 33.86389
HUNDREDTH_INCH_MM: Final = 0.254
INCH_CM: Final = 2.54
VIS_UNLIMITED_M: Final = 16093.44  # "10SM"/"10+" as reported by ASOS; also used for 9999 / CAVOK caps (>= 10 km)

DESCRIPTORS: Final = ("MI", "BC", "PR", "DR", "BL", "SH", "TS", "FZ")
PRECIPITATION: Final = ("DZ", "RA", "SN", "SG", "IC", "PL", "GR", "GS", "UP")
OBSCURATION: Final = ("BR", "FG", "FU", "VA", "DU", "SA", "HZ", "PY")
OTHER: Final = ("PO", "SQ", "FC", "SS", "DS")
_PHENOMENA: Final = PRECIPITATION + OBSCURATION + OTHER

_RE_TIME = re.compile(r"^(\d{2})(\d{2})(\d{2})Z$")
_RE_WIND = re.compile(r"^(\d{3}|VRB|///)(\d{2,3}|//)(?:G(\d{2,3}))?(KT|MPS|KMH)$")
_RE_WIND_VAR = re.compile(r"^(\d{3})V(\d{3})$")
_RE_VIS_SM = re.compile(r"^([MP])?(\d{1,2})?(?:(\d)/(\d{1,2}))?SM$")
_RE_VIS_M = re.compile(r"^(\d{4})(NDV|N|NE|E|SE|S|SW|W|NW)?$")
_RE_RVR = re.compile(r"^R\d{2}[LCR]?/[PM]?\d{4}(?:V[PM]?\d{4})?(?:FT)?[UDN]?$")
_RE_WX = re.compile(r"^([+-])?(VC)?((?:MI|BC|PR|DR|BL|SH|TS|FZ)?)((?:DZ|RA|SN|SG|IC|PL|GR|GS|UP|BR|FG|FU|VA|DU|SA|HZ|PY|PO|SQ|FC|SS|DS)+)?$")
_RE_SKY = re.compile(r"^(FEW|SCT|BKN|OVC|VV)(\d{3}|///)(CB|TCU|///)?$")
_RE_TEMP = re.compile(r"^(M?\d{2})/(M?\d{2})?$")
_RE_ALT_A = re.compile(r"^A(\d{4})$")
_RE_ALT_Q = re.compile(r"^Q(\d{4})$")
_RE_SLP = re.compile(r"^SLP(\d{3})$")
_RE_TGROUP = re.compile(r"^T([01])(\d{3})([01])(\d{3})$")
_RE_PGROUP = re.compile(r"^P(\d{4})$")
_RE_SNOWDEPTH = re.compile(r"^4/(\d{3})$")
_RE_SNOW6H = re.compile(r"^931(\d{3})$")
_RE_SNOW_WE = re.compile(r"^933(\d{3})$")
_RE_PRECIP_6H = re.compile(r"^6(\d{4})$")
_RE_PRECIP_24H = re.compile(r"^7(\d{4})$")
_RE_PKWND = re.compile(r"^(\d{3})(\d{2,3})/(\d{2})?(\d{2})$")
_TREND_START: Final = ("NOSIG", "TEMPO", "BECMG", "NSW", "RMK")


class MetarParseError(ValueError):
    pass


@dataclass(frozen=True)
class WeatherGroup:
    raw: str
    intensity: str  # "-" light, "" moderate, "+" heavy, "VC" in the vicinity
    descriptor: str | None  # MI BC PR DR BL SH TS FZ
    phenomena: tuple[str, ...]  # e.g. ("RA",), ("SN", "RA"), ("BR",)

    @property
    def precipitating(self) -> bool:
        return self.intensity != "VC" and any(p in PRECIPITATION for p in self.phenomena)

    @property
    def thunderstorm(self) -> bool:
        return self.descriptor == "TS"


@dataclass(frozen=True)
class CloudLayer:
    cover: str  # FEW SCT BKN OVC VV
    base_m: float | None  # None when reported as ///
    cloud_type: str | None  # CB, TCU or None


@dataclass
class MetarReport:
    raw: str
    report_type: str = "METAR"
    station: str = ""
    day: int | None = None
    hour: int | None = None
    minute: int | None = None
    observation_time: _dt.datetime | None = None
    auto: bool = False
    corrected: bool = False
    nil: bool = False
    wind_dir_deg: float | None = None  # None when variable/calm/missing
    wind_variable: bool = False
    wind_calm: bool = False
    wind_speed_mps: float | None = None
    wind_gust_mps: float | None = None
    wind_dir_from_deg: float | None = None
    wind_dir_to_deg: float | None = None
    visibility_m: float | None = None
    visibility_less_than: bool = False
    visibility_greater_than: bool = False
    cavok: bool = False
    rvr: list[str] = field(default_factory=list)
    weather: list[WeatherGroup] = field(default_factory=list)
    clouds: list[CloudLayer] = field(default_factory=list)
    sky_clear_code: str | None = None  # SKC CLR NSC NCD
    vertical_visibility_m: float | None = None
    temp_c: float | None = None
    dewpoint_c: float | None = None
    altimeter_hpa: float | None = None
    sea_level_pressure_hpa: float | None = None
    precip_last_hour_mm: float | None = None  # P group (0.0 = trace)
    precip_3_6h_mm: float | None = None
    precip_24h_mm: float | None = None
    snow_depth_cm: float | None = None  # 4/sss
    snowfall_6h_cm: float | None = None  # 931sss
    snow_water_equivalent_mm: float | None = None  # 933sss
    peak_wind_dir_deg: float | None = None
    peak_wind_mps: float | None = None
    remarks: str = ""
    trend: str = ""
    unparsed: list[str] = field(default_factory=list)
    maintenance_flag: bool = False  # "$"

    # ---- derived
    @property
    def ceiling_m(self) -> float | None:
        bases = [c.base_m for c in self.clouds if c.cover in ("BKN", "OVC", "VV") and c.base_m is not None]
        return min(bases) if bases else None

    @property
    def thunder(self) -> bool:
        return any(g.thunderstorm for g in self.weather)


COVER_FRACTION: Final = {"SKC": 0.0, "CLR": 0.0, "NSC": 0.0, "NCD": 0.0, "FEW": 0.1875, "SCT": 0.4375, "BKN": 0.75, "OVC": 1.0, "VV": 1.0}


def cloud_cover_fraction(layers: list[CloudLayer], sky_clear_code: str | None = None) -> float | None:
    """Total cover 0..1 = the largest layer amount (layers are cumulative in METAR, so the topmost
    reported amount already includes lower layers). Okta midpoints: FEW 1–2/8 → 0.1875, SCT 3–4/8 →
    0.4375, BKN 5–7/8 → 0.75, OVC/VV → 1.0. Returns None if the sky was not reported."""
    if layers:
        return max(COVER_FRACTION[c.cover] for c in layers)
    if sky_clear_code:
        return 0.0
    return None


def _signed_temp(tok: str) -> float:
    return -float(tok[1:]) if tok.startswith("M") else float(tok)


def resolve_observation_time(day: int, hour: int, minute: int, reference: _dt.datetime) -> _dt.datetime:
    """Most recent UTC instant with the given day-of-month/hour/minute at or before ``reference`` (+ 2 h slack for
    reports time-stamped slightly ahead of the receiving clock)."""
    ref = reference.astimezone(_dt.timezone.utc)
    y, m = ref.year, ref.month
    for _ in range(3):
        try:
            cand = _dt.datetime(y, m, day, hour, minute, tzinfo=_dt.timezone.utc)
        except ValueError:
            cand = None
        if cand is not None and cand <= ref + _dt.timedelta(hours=2):
            return cand
        m -= 1
        if m == 0:
            m, y = 12, y - 1
    raise MetarParseError(f"cannot place day {day} relative to {reference.isoformat()}")


def parse_metar(text: str, reference_time: _dt.datetime | None = None) -> MetarReport:
    """Parse one METAR/SPECI. ``text`` may carry the tgftp two-line format (date line + report) and a trailing '='."""
    lines = [ln.strip() for ln in text.strip().splitlines() if ln.strip()]
    if not lines:
        raise MetarParseError("empty METAR text")
    header_time: _dt.datetime | None = None
    m_hdr = re.match(r"^(\d{4})/(\d{2})/(\d{2}) (\d{2}):(\d{2})$", lines[0])
    if m_hdr:
        header_time = _dt.datetime(*(int(g) for g in m_hdr.groups()), tzinfo=_dt.timezone.utc)
        lines = lines[1:]
        if not lines:
            raise MetarParseError("header without report body")
    raw = " ".join(lines).rstrip("=").strip()
    rep = MetarReport(raw=raw)
    body, _, remarks = raw.partition(" RMK ")
    if raw.endswith(" RMK"):
        body = raw[:-4]
    rep.remarks = remarks.strip()
    toks = body.split()
    i = 0
    if toks and toks[0] in ("METAR", "SPECI"):
        rep.report_type = toks[0]
        i += 1
    if i < len(toks) and toks[i] == "COR":
        rep.corrected = True
        i += 1
    if i >= len(toks) or not re.match(r"^[A-Z][A-Z0-9]{3}$", toks[i]):
        raise MetarParseError(f"missing station identifier in {raw!r}")
    rep.station = toks[i]
    i += 1
    if i < len(toks):
        mt = _RE_TIME.match(toks[i])
        if mt:
            rep.day, rep.hour, rep.minute = (int(g) for g in mt.groups())
            if not (1 <= rep.day <= 31 and rep.hour <= 24 and rep.minute <= 59):
                raise MetarParseError(f"invalid time group {toks[i]}")
            i += 1
            ref = header_time or reference_time
            if ref is not None:
                rep.observation_time = resolve_observation_time(rep.day, rep.hour % 24, rep.minute, ref)
    while i < len(toks) and toks[i] in ("AUTO", "COR", "NIL", "RTD", "CCA", "CCB", "CCC"):
        if toks[i] == "AUTO":
            rep.auto = True
        elif toks[i] == "NIL":
            rep.nil = True
        else:
            rep.corrected = True
        i += 1
    seen_temp = False
    while i < len(toks):
        tok = toks[i]
        if tok in _TREND_START or re.match(r"^FM\d{4,6}$", tok):
            rep.trend = " ".join(toks[i:])
            break
        if tok == "$":
            rep.maintenance_flag = True
            i += 1
            continue
        mw = _RE_WIND.match(tok)
        if mw and rep.wind_speed_mps is None and not seen_temp:
            d, s, g, unit = mw.groups()
            f = {"KT": KT_TO_MPS, "MPS": 1.0, "KMH": KMH_TO_MPS}[unit]
            if s != "//":
                rep.wind_speed_mps = round(int(s) * f, 3)
            if g:
                rep.wind_gust_mps = round(int(g) * f, 3)
            if d == "VRB":
                rep.wind_variable = True
            elif d != "///":
                rep.wind_dir_deg = float(int(d))
            if rep.wind_speed_mps == 0.0 and (d == "000" or d == "VRB"):
                rep.wind_calm = True
                rep.wind_dir_deg = None
            i += 1
            continue
        mv = _RE_WIND_VAR.match(tok)
        if mv and rep.wind_speed_mps is not None and rep.wind_dir_from_deg is None:
            rep.wind_dir_from_deg, rep.wind_dir_to_deg = float(mv.group(1)), float(mv.group(2))
            i += 1
            continue
        if tok == "CAVOK":
            rep.cavok = True
            rep.visibility_m = VIS_UNLIMITED_M
            rep.visibility_greater_than = True
            rep.sky_clear_code = rep.sky_clear_code or "NSC"
            i += 1
            continue
        # statute-mile visibility, possibly "1 1/2SM" (two tokens)
        if rep.visibility_m is None and not seen_temp:
            if re.fullmatch(r"^\d{1,2}$", tok) and i + 1 < len(toks) and re.fullmatch(r"^\d/\d{1,2}SM$", toks[i + 1]):
                whole = int(tok)
                fr = re.match(r"^(\d)/(\d{1,2})SM$", toks[i + 1])
                rep.visibility_m = round((whole + int(fr.group(1)) / int(fr.group(2))) * STATUTE_MILE_M, 1)
                i += 2
                continue
            ms = _RE_VIS_SM.match(tok)
            if ms and (ms.group(2) or ms.group(3)):
                pre, whole, num, den = ms.groups()
                v = float(whole or 0) + (int(num) / int(den) if num else 0.0)
                rep.visibility_m = round(v * STATUTE_MILE_M, 1)
                rep.visibility_less_than = pre == "M"
                rep.visibility_greater_than = pre == "P" or v >= 10.0
                i += 1
                continue
            mm = _RE_VIS_M.match(tok)
            if mm and rep.wind_speed_mps is not None or (mm and i >= 2 and _RE_TIME.match(toks[i - 1] if i - 1 < len(toks) else "")):
                v = int(mm.group(1))
                if v == 9999:
                    rep.visibility_m = VIS_UNLIMITED_M
                    rep.visibility_greater_than = True
                else:
                    rep.visibility_m = float(v)
                    if v == 0:
                        rep.visibility_less_than = True
                        rep.visibility_m = 50.0  # "0000" means < 50 m
                i += 1
                continue
        if _RE_RVR.match(tok):
            rep.rvr.append(tok)
            i += 1
            continue
        mx = _RE_WX.match(tok)
        if mx and (mx.group(3) or mx.group(4)) and not seen_temp and tok not in ("SKC", "CLR", "NSC", "NCD"):
            sign, vc, desc, phen = mx.groups()
            phenomena = tuple(re.findall(r"DZ|RA|SN|SG|IC|PL|GR|GS|UP|BR|FG|FU|VA|DU|SA|HZ|PY|PO|SQ|FC|SS|DS", phen or ""))
            intensity = "VC" if vc else (sign or "")
            rep.weather.append(WeatherGroup(tok, intensity, desc or None, phenomena))
            i += 1
            continue
        if tok in ("SKC", "CLR", "NSC", "NCD"):
            rep.sky_clear_code = tok
            i += 1
            continue
        msky = _RE_SKY.match(tok)
        if msky:
            cover, h, typ = msky.groups()
            base = None if h == "///" else round(int(h) * 100 * FOOT_M, 1)
            if cover == "VV":
                rep.vertical_visibility_m = base
            rep.clouds.append(CloudLayer(cover, base, None if typ in (None, "///") else typ))
            i += 1
            continue
        mtd = _RE_TEMP.match(tok)
        if mtd and not seen_temp:
            rep.temp_c = _signed_temp(mtd.group(1))
            rep.dewpoint_c = _signed_temp(mtd.group(2)) if mtd.group(2) else None
            seen_temp = True
            i += 1
            continue
        ma = _RE_ALT_A.match(tok)
        if ma:
            rep.altimeter_hpa = round(int(ma.group(1)) / 100.0 * INHG_TO_HPA, 1)
            i += 1
            continue
        mq = _RE_ALT_Q.match(tok)
        if mq:
            rep.altimeter_hpa = float(int(mq.group(1)))
            i += 1
            continue
        rep.unparsed.append(tok)
        i += 1
    _parse_remarks(rep)
    return rep


def _parse_remarks(rep: MetarReport) -> None:
    toks = rep.remarks.split()
    for j, tok in enumerate(toks):
        if tok == "$":
            rep.maintenance_flag = True
            continue
        m = _RE_SLP.match(tok)
        if m:
            v = int(m.group(1)) / 10.0  # tenths of hPa, leading 9 or 10 dropped
            rep.sea_level_pressure_hpa = 1000.0 + v if v < 50.0 else 900.0 + v
            continue
        m = _RE_TGROUP.match(tok)
        if m:
            st, t, sd, d = m.groups()
            rep.temp_c = (-1 if st == "1" else 1) * int(t) / 10.0
            rep.dewpoint_c = (-1 if sd == "1" else 1) * int(d) / 10.0
            continue
        m = _RE_PGROUP.match(tok)
        if m:
            rep.precip_last_hour_mm = round(int(m.group(1)) * HUNDREDTH_INCH_MM, 3)
            continue
        m = _RE_SNOWDEPTH.match(tok)
        if m:
            rep.snow_depth_cm = round(int(m.group(1)) * INCH_CM, 2)
            continue
        m = _RE_SNOW6H.match(tok)
        if m:
            rep.snowfall_6h_cm = round(int(m.group(1)) / 10.0 * INCH_CM, 2)
            continue
        m = _RE_SNOW_WE.match(tok)
        if m:
            rep.snow_water_equivalent_mm = round(int(m.group(1)) / 10.0 * 25.4, 2)
            continue
        m = _RE_PRECIP_6H.match(tok)
        if m:
            rep.precip_3_6h_mm = round(int(m.group(1)) * HUNDREDTH_INCH_MM, 3)
            continue
        m = _RE_PRECIP_24H.match(tok)
        if m:
            rep.precip_24h_mm = round(int(m.group(1)) * HUNDREDTH_INCH_MM, 3)
            continue
        if tok == "WND" and j >= 1 and toks[j - 1] == "PK" and j + 1 < len(toks):
            mp = _RE_PKWND.match(toks[j + 1])
            if mp:
                rep.peak_wind_dir_deg = float(mp.group(1))
                rep.peak_wind_mps = round(int(mp.group(2)) * KT_TO_MPS, 3)


# --------------------------------------------------------------------------- weather-group semantics
# Representative liquid-equivalent precipitation rates (mm/h) per intensity class, used only when the
# report carries no measured hourly amount (P group). FMH-1 §8.5: light rain ≤ 2.5 mm/h, moderate
# 2.6–7.6 mm/h, heavy > 7.6 mm/h; class representatives are chosen inside each band. Snow classes are
# defined by visibility in FMH-1, the liquid-equivalent values below are the corresponding typical rates.
INTENSITY_RATE_MMPH: Final[dict[str, dict[str, float]]] = {
    "rain": {"-": 1.0, "": 4.0, "+": 10.0},
    "drizzle": {"-": 0.2, "": 0.5, "+": 1.0},
    "snow": {"-": 0.5, "": 1.5, "+": 3.0},
    "sleet": {"-": 1.0, "": 3.0, "+": 6.0},
    "freezing_rain": {"-": 0.5, "": 2.0, "+": 4.0},
}
TRACE_RATE_MMPH: Final = 0.1
THUNDERSTORM_RATE_FACTOR: Final = 1.5


def classify_precipitation(groups: list[WeatherGroup], temp_c: float | None = None) -> tuple[str, str]:
    """Map present-weather groups to DATA_CONTRACTS ``precip_type`` and the governing intensity code.

    Priority (highest first): freezing_rain (FZRA, FZDZ), sleet (PL, GS, GR, or SN together with RA/DZ),
    snow (SN, SG, IC), rain (RA, or UP with temp > 1 °C), drizzle (DZ), none. Vicinity (VC) groups do not
    count as precipitation at the station.
    """
    best = ("none", "")
    rank = {"none": 0, "drizzle": 1, "rain": 2, "snow": 3, "sleet": 4, "freezing_rain": 5}
    for g in groups:
        if not g.precipitating:
            continue
        ph = set(g.phenomena)
        if g.descriptor == "FZ" and (ph & {"RA", "DZ"}):
            kind = "freezing_rain"
        elif ph & {"PL", "GS", "GR"} or ("SN" in ph and ph & {"RA", "DZ"}):
            kind = "sleet"
        elif ph & {"SN", "SG", "IC"}:
            kind = "snow"
        elif "RA" in ph:
            kind = "rain"
        elif "UP" in ph:
            kind = "rain" if (temp_c is None or temp_c > 1.0) else "snow"
        elif "DZ" in ph:
            kind = "drizzle"
        else:
            continue
        if rank[kind] > rank[best[0]] or (kind == best[0] and _int_rank(g.intensity) > _int_rank(best[1])):
            best = (kind, g.intensity)
    return best


def _int_rank(code: str) -> int:
    return {"-": 0, "": 1, "+": 2}.get(code, 0)


def precipitation_rate_mmph(groups: list[WeatherGroup], precip_last_hour_mm: float | None, temp_c: float | None = None) -> tuple[float, str]:
    """(rate mm/h liquid-equivalent, basis) — basis is "measured" (P group), "trace", "class" or "none".

    A measured hourly amount is authoritative when present and > 0. A P0000 (trace) with precipitating
    weather yields 0.1 mm/h. Without a P group the intensity class representative is used, ×1.5 when
    the precipitation is thunderstorm-driven.
    """
    kind, intensity = classify_precipitation(groups, temp_c)
    if kind == "none":
        return 0.0, "none"
    if precip_last_hour_mm is not None:
        if precip_last_hour_mm > 0.0:
            return round(precip_last_hour_mm, 3), "measured"
        return TRACE_RATE_MMPH, "trace"
    rate = INTENSITY_RATE_MMPH[kind][intensity]
    if any(g.thunderstorm and g.precipitating for g in groups):
        rate *= THUNDERSTORM_RATE_FACTOR
    return rate, "class"


def obscuration(groups: list[WeatherGroup]) -> set[str]:
    """Obscuration/other phenomena present at the station (e.g. {"FG"}, {"BR"}, {"HZ"})."""
    out: set[str] = set()
    for g in groups:
        if g.intensity == "VC":
            continue
        out.update(p for p in g.phenomena if p in OBSCURATION or p in OTHER)
    return out


def thunder_present(groups: list[WeatherGroup]) -> bool:
    """TS at the station or in the vicinity (VCTS) — both produce audible thunder in the world."""
    return any(g.descriptor == "TS" for g in groups)


# --------------------------------------------------------------------------- multi-report text (tgftp / cycle files)
def split_reports(text: str) -> list[str]:
    """Split a tgftp-style text (date line + report, possibly several) into individual report strings."""
    out: list[str] = []
    cur: list[str] = []
    for ln in text.splitlines():
        s = ln.strip()
        if not s:
            continue
        if re.match(r"^\d{4}/\d{2}/\d{2} \d{2}:\d{2}$", s):
            if cur:
                out.append("\n".join(cur))
            cur = [s]
        else:
            cur.append(s)
    if cur:
        out.append("\n".join(cur))
    return out
