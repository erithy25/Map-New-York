"""Empire State Building tower-light colours for the night (``live/esb_lights.json``).

Source: https://www.esbnyc.com/about/tower-lights (Drupal page with a three-day block — yesterday /
today / tomorrow) and the monthly calendar https://www.esbnyc.com/about/tower-lights/calendar[/YYYYMM]
(one ``<article class="lse" data-date=YYYY-MM-DD>`` per scheduled lighting). Parsing uses the standard
library only; the markup fingerprints are checked by tests against a captured copy of both pages.

Colour names are mapped to sRGB through :data:`COLOR_RGB` (the building's palette names as they appear
on the site). ESB does not publish RGB values; the table is the best-effort rendering of each name and
is flagged as such in docs/LIVE_ALGORITHMS.md §5. Unknown names are kept in ``colors`` but listed in
``unknown_colors``. When no lighting is scheduled for the date or the site is unreachable the building
shows its signature white — the JSON says so with ``fallback = true`` and ``reason``.
"""
from __future__ import annotations

import datetime as _dt
import html as _html
import logging
import re
import time
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from typing import Callable, Final

from . import net
from .paths import ESB_LIGHTS_JSON, read_json, record_snapshot, write_json_atomic

log = logging.getLogger("nycsim.live.esb")

SCHEMA_VERSION: Final = 1
TOWER_LIGHTS_URL: Final = "https://www.esbnyc.com/about/tower-lights"
CALENDAR_URL: Final = "https://www.esbnyc.com/about/tower-lights/calendar"
CALENDAR_MONTH_URL: Final = "https://www.esbnyc.com/about/tower-lights/calendar/{yyyymm}"
DEFAULT_HOURS: Final = "sunset to 02:00"  # ESB standard schedule when no field_hours is published

SIGNATURE_WHITE_NAME: Final = "Signature White"
# Warm white (~4000 K LED) — ESB's signature white reads as a warm, slightly amber white against the sky.
SIGNATURE_WHITE_RGB: Final = (255, 228, 206)

COLOR_RGB: Final[dict[str, tuple[int, int, int]]] = {
    "signature white": SIGNATURE_WHITE_RGB,
    "white": (255, 255, 255),
    "warm white": (255, 228, 206),
    "cool white": (230, 240, 255),
    "red": (230, 20, 20),
    "dark red": (150, 10, 10),
    "crimson": (200, 20, 40),
    "scarlet": (255, 36, 0),
    "maroon": (128, 0, 32),
    "burgundy": (128, 0, 48),
    "pink": (255, 105, 180),
    "hot pink": (255, 20, 147),
    "light pink": (255, 182, 193),
    "rose": (255, 0, 127),
    "magenta": (255, 0, 255),
    "fuchsia": (255, 0, 255),
    "orange": (255, 110, 0),
    "dark orange": (255, 80, 0),
    "amber": (255, 170, 0),
    "peach": (255, 190, 140),
    "coral": (255, 110, 80),
    "gold": (255, 200, 40),
    "yellow": (255, 230, 0),
    "lemon": (255, 240, 60),
    "lime": (180, 255, 0),
    "lime green": (140, 255, 0),
    "green": (0, 200, 60),
    "kelly green": (40, 200, 60),
    "emerald": (0, 180, 90),
    "emerald green": (0, 180, 90),
    "dark green": (0, 110, 40),
    "forest green": (20, 110, 40),
    "mint": (150, 255, 200),
    "mint green": (150, 255, 200),
    "teal": (0, 150, 150),
    "turquoise": (30, 220, 200),
    "aqua": (0, 230, 230),
    "cyan": (0, 230, 255),
    "light blue": (110, 190, 255),
    "sky blue": (120, 200, 255),
    "baby blue": (150, 200, 255),
    "blue": (0, 70, 255),
    "royal blue": (30, 60, 220),
    "dark blue": (0, 30, 150),
    "navy": (0, 20, 100),
    "navy blue": (0, 20, 100),
    "indigo": (75, 0, 130),
    "purple": (140, 30, 220),
    "dark purple": (90, 0, 150),
    "violet": (150, 60, 255),
    "lavender": (200, 160, 255),
    "lilac": (200, 160, 230),
    "silver": (220, 225, 235),
    "gray": (160, 165, 170),
    "grey": (160, 165, 170),
    "bronze": (205, 127, 50),
    "copper": (200, 110, 60),
    "brown": (140, 80, 30),
    "black": (0, 0, 0),  # "dark"/"lights out" nights
    "dark": (0, 0, 0),
    "rainbow": (255, 0, 0),  # expanded by RAINBOW_SEQUENCE
}
RAINBOW_SEQUENCE: Final = (("red", (230, 20, 20)), ("orange", (255, 110, 0)), ("yellow", (255, 230, 0)), ("green", (0, 200, 60)), ("blue", (0, 70, 255)), ("purple", (140, 30, 220)))
_STRIP_SUFFIXES: Final = ("colors", "color", "colours", "colour", "lights", "light")


class ESBParseError(ValueError):
    pass


@dataclass
class ESBLighting:
    date: str  # local (New York) calendar date YYYY-MM-DD of the evening
    colors: list[str]  # canonical colour names as displayed
    reason: str
    source_url: str
    rgb: list[list[int]] = field(default_factory=list)
    unknown_colors: list[str] = field(default_factory=list)
    hours: str = DEFAULT_HOURS
    fallback: bool = False  # true when signature white was substituted (no schedule / fetch failure)
    fetched_at: str | None = None
    schema_version: int = SCHEMA_VERSION

    def to_json_dict(self) -> dict:
        return {"schema_version": self.schema_version, "date": self.date, "colors": self.colors, "reason": self.reason, "source_url": self.source_url, "rgb": self.rgb, "unknown_colors": self.unknown_colors, "hours": self.hours, "fallback": self.fallback, "fetched_at": self.fetched_at}


# --------------------------------------------------------------------------- colour names
def canonical_color_name(name: str) -> str:
    s = re.sub(r"\s+", " ", _html.unescape(name)).strip(" .:-")
    low = s.lower()
    for suf in _STRIP_SUFFIXES:
        if low.endswith(" " + suf):
            s = s[: -(len(suf) + 1)].rstrip()
            low = s.lower()
    return " ".join(w.capitalize() if w.lower() != "and" else w for w in s.split())


def split_color_names(text: str) -> list[str]:
    """'Red, White, and Blue COLOR' → ['Red', 'White', 'Blue']; 'Blue & Orange' → ['Blue', 'Orange']."""
    t = _html.unescape(text)
    t = re.sub(r"\b(COLORS?|COLOURS?)\b\.?$", "", t.strip(), flags=re.I).strip()
    parts = re.split(r",|/|&|\+|\band\b|\bwith\b", t, flags=re.I)
    out: list[str] = []
    for p in parts:
        c = canonical_color_name(p)
        if c and c.lower() not in ("", "and"):
            out.append(c)
    return out


def colors_to_rgb(names: list[str]) -> tuple[list[list[int]], list[str]]:
    rgb: list[list[int]] = []
    unknown: list[str] = []
    for n in names:
        key = n.lower()
        if key == "rainbow" or key.endswith(" rainbow") or key == "pride":
            rgb.extend(list(c) for _, c in RAINBOW_SEQUENCE)
            continue
        if key in COLOR_RGB:
            rgb.append(list(COLOR_RGB[key]))
            continue
        # try the last word ("Giants Blue" → blue, "Bright Green" → green)
        last = key.split()[-1] if key.split() else ""
        if last in COLOR_RGB:
            rgb.append(list(COLOR_RGB[last]))
            continue
        unknown.append(n)
    return rgb, unknown


# --------------------------------------------------------------------------- HTML parsing (stdlib only)
class _Node:
    __slots__ = ("tag", "attrs", "children", "text", "parent")

    def __init__(self, tag: str, attrs: dict[str, str], parent: "_Node | None"):
        self.tag = tag
        self.attrs = attrs
        self.children: list[_Node] = []
        self.text: list[str] = []
        self.parent = parent

    def classes(self) -> set[str]:
        return set((self.attrs.get("class") or "").split())

    def all_text(self) -> str:
        parts = list(self.text)
        for c in self.children:
            parts.append(c.all_text())
        return re.sub(r"\s+", " ", " ".join(parts)).strip()

    def find_all(self, pred) -> list["_Node"]:
        out = []
        stack = list(self.children)
        while stack:
            n = stack.pop(0)
            if pred(n):
                out.append(n)
            stack = n.children + stack
        return out

    def find_first(self, pred) -> "_Node | None":
        r = self.find_all(pred)
        return r[0] if r else None


_VOID = {"img", "br", "hr", "meta", "link", "input", "source", "area", "base", "col", "embed", "param", "track", "wbr"}


class _TreeBuilder(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = _Node("root", {}, None)
        self.cur = self.root

    def handle_starttag(self, tag, attrs):
        node = _Node(tag, {k: (v or "") for k, v in attrs}, self.cur)
        self.cur.children.append(node)
        if tag not in _VOID:
            self.cur = node

    def handle_startendtag(self, tag, attrs):
        self.cur.children.append(_Node(tag, {k: (v or "") for k, v in attrs}, self.cur))

    def handle_endtag(self, tag):
        n = self.cur
        while n is not None and n.tag != tag:
            n = n.parent
        if n is not None and n.parent is not None:
            self.cur = n.parent

    def handle_data(self, data):
        if data.strip():
            self.cur.text.append(data)


def parse_html(text: str) -> _Node:
    tb = _TreeBuilder()
    tb.feed(text)
    tb.close()
    return tb.root


_MONTHS = {m: i for i, m in enumerate(("january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"), 1)}


def _parse_today_heading(h2: str) -> _dt.date | None:
    m = re.search(r"Today,\s*([A-Za-z]+)\s+(\d{1,2}),\s*(\d{4})", h2)
    if not m or m.group(1).lower() not in _MONTHS:
        return None
    return _dt.date(int(m.group(3)), _MONTHS[m.group(1).lower()], int(m.group(2)))


def parse_tower_lights_page(html_text: str) -> dict[str, ESBLighting | None]:
    """Parse the three-day block. Returns {'yesterday': ..., 'today': ..., 'tomorrow': ...} (None where the
    site shows nothing). The 'today' entry carries the page's own date; 'yesterday'/'tomorrow' are dated
    relative to it. Raises ESBParseError if the block is missing (markup changed)."""
    root = parse_html(html_text)
    wrapper = root.find_first(lambda n: "three-days-lights-wrapper" in n.classes())
    if wrapper is None:
        raise ESBParseError("three-days-lights-wrapper not found")
    today_node = wrapper.find_first(lambda n: "is-today" in n.classes())
    if today_node is None:
        raise ESBParseError("is-today block not found")
    h2 = today_node.find_first(lambda n: n.tag == "h2")
    h3 = today_node.find_first(lambda n: n.tag == "h3")
    if h2 is None or h3 is None:
        raise ESBParseError("today block without h2/h3")
    today = _parse_today_heading(h2.all_text())
    if today is None:
        raise ESBParseError(f"cannot parse today's date from {h2.all_text()!r}")
    desc = today_node.find_first(lambda n: "field_description" in n.classes())
    hours = today_node.find_first(lambda n: "field_hours" in n.classes())
    out: dict[str, ESBLighting | None] = {"today": _make(today, h3.all_text(), desc.all_text() if desc else "", hours.all_text() if hours else None, TOWER_LIGHTS_URL)}
    others = wrapper.find_all(lambda n: "not-today" in n.classes())
    for node in others:
        h2o = node.find_first(lambda n: n.tag == "h2")
        h3o = node.find_first(lambda n: n.tag == "h3")
        if h2o is None or h3o is None:
            continue
        label = h2o.all_text().lower()
        d = node.find_first(lambda n: "field_description" in n.classes())
        hh = node.find_first(lambda n: "field_hours" in n.classes())
        if "yesterday" in label:
            out["yesterday"] = _make(today - _dt.timedelta(days=1), h3o.all_text(), d.all_text() if d else "", hh.all_text() if hh else None, TOWER_LIGHTS_URL)
        elif "tomorrow" in label:
            out["tomorrow"] = _make(today + _dt.timedelta(days=1), h3o.all_text(), d.all_text() if d else "", hh.all_text() if hh else None, TOWER_LIGHTS_URL)
    out.setdefault("yesterday", None)
    out.setdefault("tomorrow", None)
    return out


def parse_calendar_page(html_text: str, source_url: str = CALENDAR_URL) -> dict[_dt.date, ESBLighting]:
    """Parse ``<article class="lse" data-date=YYYY-MM-DD>`` entries of a calendar month page."""
    root = parse_html(html_text)
    view = root.find_first(lambda n: "lights-calendar-view" in n.classes())
    if view is None:
        raise ESBParseError("lights-calendar-view not found")
    out: dict[_dt.date, ESBLighting] = {}
    for art in view.find_all(lambda n: n.tag == "article" and "lse" in n.classes()):
        ds = art.attrs.get("data-date", "")
        try:
            d = _dt.date.fromisoformat(ds.strip().strip('"'))
        except ValueError:
            continue
        name = art.find_first(lambda n: "name" in n.classes())
        desc = art.find_first(lambda n: "field_description" in n.classes())
        hours = art.find_first(lambda n: "field_hours" in n.classes())
        if name is None:
            continue
        out[d] = _make(d, name.all_text(), desc.all_text() if desc else "", hours.all_text() if hours else None, source_url)
    return out


def _make(date: _dt.date, color_text: str, reason: str, hours: str | None, url: str) -> ESBLighting:
    """Build a lighting record. Colour names are kept verbatim as published; only names in
    :data:`COLOR_RGB` (or whose last word is) get an RGB triple, and the rest are listed in
    ``unknown_colors`` rather than guessed. If *nothing* resolved, signature white is used so the tower is
    still lit with a real ESB colour — the published names stay in ``colors`` and ``unknown_colors``."""
    names = split_color_names(color_text) or [SIGNATURE_WHITE_NAME]
    rgb, unknown = colors_to_rgb(names)
    if not rgb:
        rgb = [list(SIGNATURE_WHITE_RGB)]
    return ESBLighting(date=date.isoformat(), colors=names, reason=reason.strip(), source_url=url, rgb=rgb, unknown_colors=unknown, hours=(hours or DEFAULT_HOURS).strip())


def signature_white(date: _dt.date, reason: str, fallback: bool = True) -> ESBLighting:
    return ESBLighting(date=date.isoformat(), colors=[SIGNATURE_WHITE_NAME], reason=reason, source_url=TOWER_LIGHTS_URL, rgb=[list(SIGNATURE_WHITE_RGB)], fallback=fallback)


# --------------------------------------------------------------------------- service
class ESBLightsService:
    """Daily fetch (cached per local date) with signature-white fallback and JSON snapshot."""

    def __init__(self, out_path: Path = ESB_LIGHTS_JSON, fetch: Callable[..., net.Response] = net.get, clock: Callable[[], float] = time.time, refresh_s: float = 3600.0):
        self.out_path = out_path
        self._fetch = fetch
        self.clock = clock
        self.refresh_s = refresh_s
        self.current: ESBLighting | None = None
        self._last_fetch: float = 0.0
        self.calendar_cache: dict[_dt.date, ESBLighting] = {}
        prev = read_json(out_path)
        if prev and prev.get("date") and isinstance(prev.get("colors"), list):
            try:
                self.current = ESBLighting(**{k: v for k, v in prev.items() if k in ESBLighting.__dataclass_fields__})
            except TypeError:
                self.current = None

    def lighting_for(self, local_date: _dt.date) -> ESBLighting:
        """Today's lighting from the tower-lights page, cross-checked/completed with the calendar."""
        errors: list[str] = []
        result: ESBLighting | None = None
        try:
            page = parse_tower_lights_page(self._fetch(TOWER_LIGHTS_URL).text)
            for key in ("today", "yesterday", "tomorrow"):
                e = page.get(key)
                if e is not None and e.date == local_date.isoformat():
                    result = e
                    break
            if result is None and page["today"] is not None:
                errors.append(f"tower-lights page is for {page['today'].date}, not {local_date}")
        except (net.HttpError, ESBParseError) as ex:
            errors.append(f"tower-lights: {ex}")
        try:
            url = CALENDAR_MONTH_URL.format(yyyymm=local_date.strftime("%Y%m"))
            cal = parse_calendar_page(self._fetch(url).text, url)
            self.calendar_cache.update(cal)
        except (net.HttpError, ESBParseError) as ex:
            errors.append(f"calendar: {ex}")
        cal_entry = self.calendar_cache.get(local_date)
        if result is None and cal_entry is not None:
            result = cal_entry
        if result is not None:
            if cal_entry is not None and [c.lower() for c in cal_entry.colors] != [c.lower() for c in result.colors]:
                log.warning("ESB three-day block (%s) and calendar (%s) disagree for %s; using the three-day block", result.colors, cal_entry.colors, local_date)
            return result
        if not errors or all(e.startswith("tower-lights page is for") for e in errors):
            # both pages parsed and neither lists the date: no special lighting → signature white (not a failure)
            return signature_white(local_date, "No scheduled lighting; Empire State Building signature white", fallback=True)
        raise ESBParseError("; ".join(errors))

    def poll(self, local_date: _dt.date) -> ESBLighting:
        now = self.clock()
        if self.current is not None and self.current.date == local_date.isoformat() and now - self._last_fetch < self.refresh_s and not self.current.fallback:
            return self.current
        try:
            e = self.lighting_for(local_date)
        except ESBParseError as ex:
            log.warning("ESB lights unavailable: %s", ex)
            if self.current is not None and self.current.date == local_date.isoformat():
                e = self.current
            else:
                e = signature_white(local_date, f"unavailable: {ex}")
        e.fetched_at = _dt.datetime.fromtimestamp(now, tz=_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        self._last_fetch = now
        self.current = e
        try:
            write_json_atomic(self.out_path, e.to_json_dict())
        except OSError as ex:
            log.error("cannot write %s: %s", self.out_path, ex)
        return e
