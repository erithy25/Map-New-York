#!/usr/bin/env python3
"""Fetch clearly-licensed audio for the NYCSim in-car radio and sampled SFX, with a licence record per file.

Sources actually reachable from the build environment (checked 2026-09-05; see docs/verification/unreal_gameplay/REPORT.md):

* Wikimedia Commons (music stations, some SFX). Files are selected from Commons categories, the licence is read
  from the file's ``extmetadata`` and only CC0 / Public Domain / CC BY (2.0, 2.5, 3.0, 4.0) files are accepted.
  Share-alike, NC and ND variants are rejected. The Commons API and upload.wikimedia.org rate-limit aggressively
  (HTTP 429 with Retry-After up to ~60 s) so every call is paced and retried honouring Retry-After.
* Internet Archive / LibriVox (talk station). LibriVox recordings are public domain (CC PDM / CC0 per item
  ``licenseurl``); the item metadata lists every chapter file. MP3 chapters are transcoded to OGG Vorbis mono.
* OpenGameArt.org (CC0 jingles/SFX). The site has no JSON API; the advanced-search page and the node page are
  parsed for the file links and the ``License(s)`` field, which must read CC0.

NOT usable here (documented, not worked around): Free Music Archive (the ``/api/get`` endpoint answers 404 — the
public API was retired), Freesound (API key required, 401), GitHub releases (blocked).

Output layout::

    assets/audio/radio/<station_id>/<file>.ogg            runtime-decoded OGG Vorbis
    assets/audio/radio/<station_id>/<file>.ogg.license.json
    assets/audio/radio/stations.json                      consumed by URadioSubsystem (schema below)
    assets/audio/sfx/<name>.(ogg|wav) + .license.json     sampled SFX (imported as USoundWave by the editor script)
    assets/audio/CATALOG.json                             every file with licence, sha256, bytes, duration
    docs/ASSET_LICENSES.md                                appended section "Audio (radio, SFX)"

Every downloaded byte is transcoded/kept only when the licence is confirmed; nothing is invented. Stations with
fewer than ``MIN_TRACKS`` confirmed tracks are dropped and the drop is reported.

    python3 unreal/tools/fetch_radio.py --max-total-mb 300
    python3 unreal/tools/fetch_radio.py --station jazz --dry-run
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import logging
import os
import random
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any
from urllib.parse import quote, unquote, urlparse

import requests

log = logging.getLogger("nycsim.fetch_radio")

REPO_ROOT = Path(os.environ.get("NYCSIM_REPO_ROOT", Path(__file__).resolve().parents[2]))
AUDIO_ROOT = REPO_ROOT / "assets" / "audio"
RADIO_ROOT = AUDIO_ROOT / "radio"
SFX_ROOT = AUDIO_ROOT / "sfx"
CATALOG_PATH = AUDIO_ROOT / "CATALOG.json"
STATIONS_PATH = RADIO_ROOT / "stations.json"
LICENSES_MD = REPO_ROOT / "docs" / "ASSET_LICENSES.md"

USER_AGENT = ("NYCSimRadioFetch/1.0 (open-source driving simulation asset fetch; "
              "https://example.invalid/nycsim; contact: iven.thye@lokenbergcapital.com) python-requests/" + requests.__version__)
CA_BUNDLE = os.environ.get("REQUESTS_CA_BUNDLE") or os.environ.get("SSL_CERT_FILE") or True

COMMONS_API = "https://commons.wikimedia.org/w/api.php"
IA_SEARCH = "https://archive.org/advancedsearch.php"
IA_META = "https://archive.org/metadata/"
IA_DOWNLOAD = "https://archive.org/download/"
OGA_ROOT = "https://opengameart.org"

SCHEMA_VERSION = 1
MIN_TRACKS = 4

# Licences accepted for redistribution inside the game (permissive, attribution recorded). Keys are the Commons
# ``LicenseShortName`` values, normalised to lower case with whitespace collapsed.
ACCEPTED_LICENSES: dict[str, str] = {
    "cc0": "CC0-1.0",
    "cc-zero": "CC0-1.0",
    "cc0 1.0": "CC0-1.0",
    "public domain": "Public Domain",
    "pd": "Public Domain",
    "pdm": "Public Domain",
    "pd-old": "Public Domain",
    "pd-us": "Public Domain",
    "cc by 2.0": "CC-BY-2.0",
    "cc by 2.5": "CC-BY-2.5",
    "cc by 3.0": "CC-BY-3.0",
    "cc by 4.0": "CC-BY-4.0",
    "cc by 3.0 us": "CC-BY-3.0-US",
    "cc by 2.0 de": "CC-BY-2.0-DE",
    "cc by 3.0 de": "CC-BY-3.0-DE",
    "cc by": "CC-BY",
}
REJECT_MARKERS = ("sa", "nc", "nd", "gfdl", "fal", "odbl", "unknown")

AUDIO_MIMES = {"application/ogg", "audio/ogg", "audio/x-ogg", "audio/mpeg", "audio/mp3", "audio/flac", "audio/x-flac",
               "audio/webm", "audio/wav", "audio/x-wav", "audio/midi"}
KEEP_OGG_MIMES = {"application/ogg", "audio/ogg", "audio/x-ogg"}
# midi is listed so it can be *rejected* explicitly with a reason in the log rather than silently skipped.
REJECT_MIMES = {"audio/midi"}

MUSIC_MIN_S, MUSIC_MAX_S = 75.0, 540.0
MUSIC_MAX_BYTES = 14 * 1024 * 1024
TALK_MIN_S, TALK_MAX_S = 240.0, 1900.0
SFX_MAX_S = 45.0
LOUDNESS_TARGET_MUSIC_LUFS = -14.0
LOUDNESS_TARGET_TALK_LUFS = -16.0


# --------------------------------------------------------------------------------------------------- data model
@dataclass
class StationSpec:
    id: str
    name: str
    frequency_mhz: float
    kind: str  # music | talk
    genre: str
    commons_categories: list[str] = field(default_factory=list)
    commons_depth: int = 0
    ia_items: list[tuple[str, int]] = field(default_factory=list)  # (identifier, max chapters)
    target_mb: float = 30.0
    max_tracks: int = 12


# The dial is fictional: names and frequencies do not correspond to any licensed New York broadcaster.
STATIONS: list[StationSpec] = [
    StationSpec("jazz", "Hudson Jazz", 89.3, "music", "jazz / ragtime",
                ["Jazz music from Free Music Archive", "Jazz music from Incompetech", "Audio files of music by Fats Waller",
                 "Audio files of ragtime music", "Audio files of jazz music"], 1, target_mb=34, max_tracks=12),
    StationSpec("hiphop", "Boogie Down FM", 97.1, "music", "hip hop",
                ["Hip hop music from Free Music Archive"], 1, target_mb=34, max_tracks=12),
    StationSpec("rock", "Bowery Rock", 102.7, "music", "rock",
                ["Rock music from Free Music Archive"], 1, target_mb=34, max_tracks=12),
    StationSpec("electronic", "Pulse Brooklyn", 105.9, "music", "electronic",
                ["Audio files of electronic music", "Audio files of electronic music by genre"], 1, target_mb=34, max_tracks=12),
    StationSpec("classical", "Lincoln Center Classical", 91.5, "music", "classical",
                ["Musopen", "Audio files of classical music by composer", "Audio files of classical music by period"], 1,
                target_mb=34, max_tracks=10),
    StationSpec("folk", "Bleecker Street Folk", 93.7, "music", "folk / country",
                ["Audio files of folk music", "Audio files of country music", "Audio files of blues"], 1, target_mb=30, max_tracks=10),
    StationSpec("talk", "Gotham Readings", 820.0, "talk", "public-domain readings set in New York",
                ia_items=[("four_million_librivox", 3), ("bartleby_scrivener_1107_librivox", 2),
                          ("how_the_other_half_lives_1102_librivox", 1), ("washington_square_librivox", 1),
                          ("greatgatsby_2101_librivox", 1), ("age_of_innocence_librivox", 1),
                          ("maggie_0911_librivox", 1), ("leaves_of_grass_librivox", 1)],
                target_mb=48, max_tracks=11),
]

# CC0 sampled SFX wanted from OpenGameArt (search keywords → our file stem). Procedural MetaSounds cover the rest.
OGA_SFX_QUERIES: list[tuple[str, str, int]] = [
    ("car horn", "horn_sample", 2),
    ("car crash", "collision_crash", 2),
    ("glass break", "glass_break", 1),
    ("car door", "car_door", 1),
    ("seatbelt", "seatbelt_click", 1),
    ("radio static", "radio_static", 1),
    ("jingle", "radio_jingle", 3),
]
# Commons SFX (field recordings). (search string, our stem, max files)
COMMONS_SFX_QUERIES: list[tuple[str, str, int]] = [
    ("New York City Subway train arriving", "subway_arrive", 2),
    ("New York City Subway", "subway_ambience", 2),
    ("helicopter flyover", "helicopter", 2),
    ("harbor waves lapping", "waterfront", 2),
    ("city traffic ambience", "traffic_bed", 2),
    ("birds park ambience", "park_birds", 2),
    ("steam vent hiss", "steam_vent", 1),
    ("police siren", "siren_sample", 2),
]


@dataclass
class Track:
    file: str
    title: str
    artist: str
    licence: str
    licence_url: str
    source_url: str
    source_page: str
    duration_s: float
    bytes: int
    sha256: str
    loudness_lufs: float | None
    gain_db: float
    original_filename: str
    transcode: dict[str, Any] | None
    source_site: str
    attribution_note: str = ""


class FetchError(RuntimeError):
    pass


# --------------------------------------------------------------------------------------------------- http
class Http:
    # upload.wikimedia.org throttles datacenter clients fetching originals ("Too many requests - please contact
    # noc@wikimedia.org", Retry-After 600); originals are therefore requested at most once per 12 s and the
    # full Retry-After is honoured. The API host tolerates ~1 request / 1.6 s with maxlag=5.
    HOST_INTERVALS = {"upload.wikimedia.org": 12.0, "commons.wikimedia.org": 1.6, "archive.org": 1.5, "opengameart.org": 2.0}
    MAX_RETRY_AFTER_S = 660.0

    def __init__(self, min_interval_s: float = 1.6) -> None:
        self.s = requests.Session()
        self.s.headers["User-Agent"] = USER_AGENT
        self.min_interval = min_interval_s
        self._last: dict[str, float] = {}
        self.calls = 0
        self.retries = 0

    def _pace(self, host: str) -> None:
        now = time.monotonic()
        last = self._last.get(host, 0.0)
        interval = self.HOST_INTERVALS.get(host, self.min_interval)
        if host.endswith(".archive.org"):
            interval = self.HOST_INTERVALS["archive.org"]
        wait = interval - (now - last)
        if wait > 0:
            time.sleep(wait)
        self._last[host] = time.monotonic()

    def get(self, url: str, *, params: dict | None = None, stream: bool = False, timeout: int = 120,
            attempts: int = 6, headers: dict | None = None) -> requests.Response:
        host = urlparse(url).netloc
        last_err: Exception | None = None
        for i in range(attempts):
            self._pace(host)
            self.calls += 1
            try:
                r = self.s.get(url, params=params, stream=stream, timeout=timeout, verify=CA_BUNDLE, headers=headers)
            except requests.RequestException as e:
                last_err = e
                self.retries += 1
                back = min(90.0, 3.0 * 2 ** i)
                log.warning("%s: %s (retry in %.0fs)", host, e, back)
                time.sleep(back)
                continue
            if r.status_code == 429 or 500 <= r.status_code < 600:
                self.retries += 1
                ra = r.headers.get("Retry-After")
                try:
                    back = float(ra) if ra else min(90.0, 5.0 * 2 ** i)
                except ValueError:
                    back = min(90.0, 5.0 * 2 ** i)
                back = max(2.0, min(back + 1.0, self.MAX_RETRY_AFTER_S))
                log.warning("%s HTTP %d (attempt %d/%d), sleeping %.0fs", host, r.status_code, i + 1, attempts, back)
                r.close()
                time.sleep(back)
                continue
            return r
        raise FetchError(f"giving up on {url}: {last_err}")

    def json(self, url: str, params: dict | None = None) -> Any:
        r = self.get(url, params=params)
        if r.status_code >= 400:
            raise FetchError(f"HTTP {r.status_code} for {r.url}")
        try:
            return r.json()
        except ValueError as e:
            raise FetchError(f"non-JSON answer from {r.url}: {r.text[:120]!r}") from e

    def download(self, url: str, dest: Path, *, max_bytes: int, expect_prefixes: tuple[bytes, ...] = ()) -> int:
        """Stream to dest.part then rename. Rejects HTML error pages and oversize bodies."""
        dest.parent.mkdir(parents=True, exist_ok=True)
        part = dest.with_suffix(dest.suffix + ".part")
        r = self.get(url, stream=True, timeout=600)
        try:
            if r.status_code >= 400:
                raise FetchError(f"HTTP {r.status_code} for {url}")
            ctype = (r.headers.get("Content-Type") or "").lower()
            if "text/html" in ctype:
                raise FetchError(f"HTML body instead of media for {url}")
            clen = r.headers.get("Content-Length")
            if clen and int(clen) > max_bytes:
                raise FetchError(f"{url}: {clen} bytes exceeds cap {max_bytes}")
            n = 0
            head = b""
            with open(part, "wb") as f:
                for chunk in r.iter_content(chunk_size=1 << 18):
                    if not chunk:
                        continue
                    if len(head) < 16:
                        head += chunk[: 16 - len(head)]
                    f.write(chunk)
                    n += len(chunk)
                    if n > max_bytes:
                        raise FetchError(f"{url}: body exceeds cap {max_bytes}")
            if n == 0:
                raise FetchError(f"empty body for {url}")
            if expect_prefixes and not any(head.startswith(p) for p in expect_prefixes):
                raise FetchError(f"{url}: unexpected file signature {head[:8]!r}")
        except Exception:
            if part.exists():
                part.unlink()
            raise
        finally:
            r.close()
        os.replace(part, dest)
        return n


# --------------------------------------------------------------------------------------------------- ffmpeg
class Ffmpeg:
    def __init__(self) -> None:
        exe = shutil.which("ffmpeg")
        if exe is None:
            try:
                import imageio_ffmpeg  # type: ignore

                exe = imageio_ffmpeg.get_ffmpeg_exe()
            except Exception as e:  # noqa: BLE001
                raise FetchError("no ffmpeg available (install ffmpeg or `pip install imageio-ffmpeg`)") from e
        self.exe = exe
        out = subprocess.run([exe, "-hide_banner", "-encoders"], capture_output=True, text=True, timeout=60)
        if "libvorbis" not in out.stdout:
            raise FetchError(f"{exe} lacks the libvorbis encoder")

    def _run(self, args: list[str], timeout: int = 900) -> subprocess.CompletedProcess:
        cmd = ["nice", "-n", "10", self.exe, "-hide_banner", "-nostdin", "-y", *args]
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)

    def probe(self, path: Path) -> tuple[float, str, int, int]:
        """(duration_s, codec_name, sample_rate, channels) parsed from ffmpeg's stderr banner (no ffprobe shipped)."""
        p = self._run(["-i", str(path), "-f", "null", "-t", "0.01", "-"], timeout=120)
        text = p.stderr
        m = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", text)
        if not m:
            raise FetchError(f"ffmpeg could not read {path.name}: {text[-300:]}")
        dur = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))
        a = re.search(r"Audio:\s*([a-z0-9_]+)[^,]*,\s*(\d+)\s*Hz,\s*([a-z0-9.()]+)", text)
        codec = a.group(1) if a else "unknown"
        rate = int(a.group(2)) if a else 0
        ch_txt = a.group(3) if a else "stereo"
        channels = 1 if ch_txt.startswith("mono") else (2 if ch_txt.startswith("stereo") else 2)
        return dur, codec, rate, channels

    def loudness(self, path: Path) -> float | None:
        p = self._run(["-i", str(path), "-af", "ebur128=peak=none", "-f", "null", "-"], timeout=600)
        m = re.findall(r"I:\s*(-?\d+(?:\.\d+)?)\s*LUFS", p.stderr)
        if not m:
            return None
        try:
            v = float(m[-1])
        except ValueError:
            return None
        return v if v > -70.0 else None

    def to_ogg(self, src: Path, dst: Path, *, mono: bool, quality: float, sample_rate: int, max_seconds: float | None) -> dict[str, Any]:
        args = ["-i", str(src), "-vn", "-map_metadata", "-1"]
        if max_seconds:
            args += ["-t", f"{max_seconds:.2f}"]
        if mono:
            args += ["-ac", "1"]
        args += ["-ar", str(sample_rate), "-c:a", "libvorbis", "-q:a", f"{quality:g}", str(dst)]
        p = self._run(args)
        if p.returncode != 0 or not dst.exists() or dst.stat().st_size < 1000:
            if dst.exists():
                dst.unlink()
            raise FetchError(f"transcode failed for {src.name}: {p.stderr[-400:]}")
        return {"from": src.suffix.lstrip(".").lower(), "codec": "libvorbis", "quality": quality, "mono": mono,
                "sample_rate": sample_rate, "tool": "ffmpeg " + Path(self.exe).name, "trimmed_to_s": max_seconds}


# --------------------------------------------------------------------------------------------------- helpers
def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def strip_html(s: str) -> str:
    s = re.sub(r"<[^>]+>", "", s or "")
    return html.unescape(s).strip()


def safe_stem(s: str, limit: int = 64) -> str:
    s = unquote(s)
    s = re.sub(r"\.[A-Za-z0-9]{2,5}$", "", s)
    s = re.sub(r"[^A-Za-z0-9]+", "_", s).strip("_").lower()
    return (s or "track")[:limit]


def normalise_licence(short: str) -> str | None:
    key = re.sub(r"\s+", " ", (short or "").strip().lower())
    if not key:
        return None
    if key in ACCEPTED_LICENSES:
        return ACCEPTED_LICENSES[key]
    # e.g. "CC BY 3.0 US", "Public domain (US)", "PD-US-expired"
    tokens = re.split(r"[\s\-_/()]+", key)
    if any(t in REJECT_MARKERS for t in tokens):
        return None
    if key.startswith("cc by ") and not any(t in ("sa", "nc", "nd") for t in tokens):
        return "CC-BY-" + key[6:].upper().replace(" ", "-")
    if key.startswith("public domain") or key.startswith("pd"):
        return "Public Domain"
    if key.startswith("cc0"):
        return "CC0-1.0"
    return None


def write_license_record(media_path: Path, track: Track) -> Path:
    rec = {"schema_version": SCHEMA_VERSION, "file": media_path.name, **asdict(track), "recorded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    p = media_path.with_name(media_path.name + ".license.json")
    with open(p, "w") as f:
        json.dump(rec, f, indent=1, sort_keys=True)
    return p


def gain_for(lufs: float | None, target: float) -> float:
    if lufs is None:
        return 0.0
    return max(-12.0, min(12.0, round(target - lufs, 2)))


# --------------------------------------------------------------------------------------------------- Commons
class Commons:
    def __init__(self, http: Http) -> None:
        self.http = http

    def api(self, params: dict) -> dict:
        p = dict(params)
        p.update({"format": "json", "formatversion": "2", "maxlag": "5"})
        d = self.http.json(COMMONS_API, p)
        if "error" in d:
            code = d["error"].get("code")
            if code == "maxlag":
                time.sleep(6)
                d = self.http.json(COMMONS_API, p)
                if "error" in d:
                    raise FetchError(f"Commons API error {d['error']}")
            else:
                raise FetchError(f"Commons API error {d['error']}")
        return d

    def subcategories(self, category: str, limit: int = 100) -> list[str]:
        d = self.api({"action": "query", "list": "categorymembers", "cmtitle": "Category:" + category, "cmtype": "subcat", "cmlimit": limit})
        return [m["title"].split(":", 1)[1] for m in d.get("query", {}).get("categorymembers", [])]

    def category_files(self, category: str, *, max_pages: int = 6) -> list[dict]:
        """Files in a category with imageinfo + extmetadata (50 per API call)."""
        out: list[dict] = []
        cont: dict = {}
        for _ in range(max_pages):
            params = {"action": "query", "generator": "categorymembers", "gcmtitle": "Category:" + category, "gcmtype": "file",
                      "gcmlimit": 50, "prop": "imageinfo", "iiprop": "url|size|mime|extmetadata",
                      "iiextmetadatafilter": "LicenseShortName|LicenseUrl|Artist|ObjectName|Credit|Attribution|AttributionRequired|Restrictions|ImageDescription"}
            params.update(cont)
            d = self.api(params)
            for page in d.get("query", {}).get("pages", []):
                ii = page.get("imageinfo") or []
                if not ii:
                    continue
                info = ii[0]
                out.append({"title": page.get("title", ""), "pageid": page.get("pageid"), **info})
            cont = d.get("continue", {})
            if not cont:
                break
        return out

    def search_files(self, query: str, limit: int = 20) -> list[dict]:
        params = {"action": "query", "generator": "search", "gsrsearch": query + " filetype:audio", "gsrnamespace": 6, "gsrlimit": min(limit, 50),
                  "prop": "imageinfo", "iiprop": "url|size|mime|extmetadata",
                  "iiextmetadatafilter": "LicenseShortName|LicenseUrl|Artist|ObjectName|Credit|Attribution|Restrictions|ImageDescription"}
        d = self.api(params)
        out = []
        for page in d.get("query", {}).get("pages", []):
            ii = page.get("imageinfo") or []
            if ii:
                out.append({"title": page.get("title", ""), "pageid": page.get("pageid"), **ii[0]})
        return out

    @staticmethod
    def licence_of(info: dict) -> tuple[str | None, str, str, str]:
        em = info.get("extmetadata") or {}

        def val(k: str) -> str:
            v = em.get(k)
            return strip_html(v.get("value", "")) if isinstance(v, dict) else ""

        lic = normalise_licence(val("LicenseShortName"))
        if val("Restrictions"):
            lic = None
        return lic, val("LicenseUrl"), val("Artist") or val("Credit") or "unknown (Commons uploader)", val("ObjectName")


# --------------------------------------------------------------------------------------------------- selection
def candidate_ok(info: dict, *, min_s: float, max_s: float, max_bytes: int) -> tuple[bool, str]:
    mime = (info.get("mime") or "").lower()
    if mime in REJECT_MIMES:
        return False, "midi (not audio)"
    if mime not in AUDIO_MIMES:
        return False, f"mime {mime}"
    dur = info.get("duration")
    if dur is None:
        return False, "no duration"
    if not (min_s <= float(dur) <= max_s):
        return False, f"duration {float(dur):.0f}s"
    if int(info.get("size") or 0) > max_bytes:
        return False, f"size {info.get('size')}"
    # Musopen uploads include per-instrument stems ("1st violin B 02.wav"); a radio plays mixes, not stems.
    if re.search(r"\b(1st|2nd|violin|viola|cello|bass|flute|oboe|clarinet|horn|trumpet|timpani|stem)\b.*\.(wav|flac)$", info.get("title", ""), re.I):
        return False, "orchestral stem"
    return True, ""


def clean_url(u: str) -> str:
    return u.split("?", 1)[0]


# --------------------------------------------------------------------------------------------------- pipeline
class Fetcher:
    def __init__(self, *, max_total_mb: float, dry_run: bool, seed: int, only: set[str] | None) -> None:
        self.http = Http()
        self.commons = Commons(self.http)
        self.ff = None if dry_run else Ffmpeg()
        self.max_total = int(max_total_mb * 1024 * 1024)
        self.dry_run = dry_run
        self.rng = random.Random(seed)
        self.only = only
        self.total_bytes = 0
        self.catalog: list[dict] = []
        self.problems: list[str] = []
        self.stations_out: list[dict] = []
        self.tmp = AUDIO_ROOT / ".tmp"
        self.tmp.mkdir(parents=True, exist_ok=True)

    # ---- existing files are reused when their licence record matches (idempotent re-runs)
    @staticmethod
    def existing(media: Path) -> Track | None:
        rec = media.with_name(media.name + ".license.json")
        if not media.exists() or not rec.exists():
            return None
        try:
            d = json.loads(rec.read_text())
            if d.get("sha256") != sha256_of(media):
                return None
            d.pop("schema_version", None)
            d.pop("recorded_at", None)
            d.pop("file", None)
            return Track(**d)
        except (OSError, ValueError, TypeError):
            return None

    def budget_left(self) -> int:
        return self.max_total - self.total_bytes

    def _finish_track(self, media: Path, track: Track, target_lufs: float) -> Track:
        if self.ff is None:
            return track
        dur, _codec, _rate, _ch = self.ff.probe(media)
        track.duration_s = round(dur, 2)
        track.loudness_lufs = self.ff.loudness(media)
        track.gain_db = gain_for(track.loudness_lufs, target_lufs)
        track.bytes = media.stat().st_size
        track.sha256 = sha256_of(media)
        write_license_record(media, track)
        return track

    # ---- Commons music station
    def fetch_commons_station(self, spec: StationSpec) -> list[Track]:
        st_dir = RADIO_ROOT / spec.id
        st_dir.mkdir(parents=True, exist_ok=True)
        # reuse
        tracks: list[Track] = []
        for media in sorted(st_dir.glob("*.ogg")):
            t = self.existing(media)
            if t:
                tracks.append(t)
                self.total_bytes += t.bytes
        if len(tracks) >= spec.max_tracks:
            log.info("[%s] %d tracks already present, skipping fetch", spec.id, len(tracks))
            return tracks
        have_urls = {t.source_url for t in tracks}

        cats = list(spec.commons_categories)
        if spec.commons_depth > 0:
            expanded: list[str] = []
            for c in cats:
                expanded.append(c)
                try:
                    subs = self.commons.subcategories(c)
                except FetchError as e:
                    self.problems.append(f"[{spec.id}] subcategories of {c}: {e}")
                    continue
                expanded.extend(s for s in subs if not re.search(r"\b(midi|logo|sample|album|playlist|stem)s?\b", s, re.I))
            cats = list(dict.fromkeys(expanded))
        candidates: list[dict] = []
        seen = set()
        for c in cats:
            if len(candidates) > 400:
                break
            try:
                files = self.commons.category_files(c, max_pages=3)
            except FetchError as e:
                self.problems.append(f"[{spec.id}] category {c}: {e}")
                continue
            n_ok = 0
            for info in files:
                if info.get("pageid") in seen:
                    continue
                seen.add(info.get("pageid"))
                ok, why = candidate_ok(info, min_s=MUSIC_MIN_S, max_s=MUSIC_MAX_S, max_bytes=MUSIC_MAX_BYTES)
                if not ok:
                    continue
                lic, _, _, _ = Commons.licence_of(info)
                if lic is None:
                    continue
                info["_category"] = c
                candidates.append(info)
                n_ok += 1
            log.info("[%s] category %r: %d files, %d usable", spec.id, c, len(files), n_ok)
        self.rng.shuffle(candidates)
        # prefer OGG (no re-encode) then mp3/flac
        candidates.sort(key=lambda i: 0 if (i.get("mime") or "") in KEEP_OGG_MIMES else 1)
        station_bytes = sum(t.bytes for t in tracks)
        for info in candidates:
            if len(tracks) >= spec.max_tracks or station_bytes >= spec.target_mb * 1024 * 1024:
                break
            url = clean_url(info["url"])
            if url in have_urls:
                continue
            lic, lic_url, artist, obj = Commons.licence_of(info)
            title = obj or strip_html(info["title"]).removeprefix("File:")
            stem = safe_stem(Path(urlparse(url).path).name)
            media = st_dir / f"{stem}.ogg"
            if media.exists():
                stem = f"{stem}_{info['pageid']}"
                media = st_dir / f"{stem}.ogg"
            if self.dry_run:
                log.info("[%s] would fetch %s (%s, %s, %.0fs)", spec.id, title, lic, artist, float(info["duration"]))
                continue
            est = int(info.get("size") or 0)
            if est > self.budget_left():
                self.problems.append(f"[{spec.id}] budget exhausted before {title}")
                break
            raw = self.tmp / f"{spec.id}_{stem}{Path(urlparse(url).path).suffix.lower()}"
            try:
                self.http.download(url, raw, max_bytes=MUSIC_MAX_BYTES, expect_prefixes=(b"OggS", b"ID3", b"\xff\xfb", b"\xff\xf3", b"\xff\xf2", b"fLaC", b"RIFF", b"\x1a\x45\xdf\xa3"))
                assert self.ff is not None
                transcode = None
                if (info.get("mime") or "") in KEEP_OGG_MIMES and raw.read_bytes()[:4] == b"OggS":
                    # keep container as-is only when it is Vorbis (Opus/FLAC-in-Ogg are not decodable by FVorbisAudioInfo)
                    _d, codec, _r, _c = self.ff.probe(raw)
                    if codec == "vorbis":
                        shutil.move(str(raw), str(media))
                    else:
                        transcode = self.ff.to_ogg(raw, media, mono=False, quality=4.0, sample_rate=44100, max_seconds=None)
                        raw.unlink(missing_ok=True)
                else:
                    transcode = self.ff.to_ogg(raw, media, mono=False, quality=4.0, sample_rate=44100, max_seconds=None)
                    raw.unlink(missing_ok=True)
                track = Track(file=f"{spec.id}/{media.name}", title=title, artist=artist, licence=lic or "", licence_url=lic_url,
                              source_url=url, source_page=info.get("descriptionurl", ""), duration_s=float(info["duration"]), bytes=0, sha256="",
                              loudness_lufs=None, gain_db=0.0, original_filename=Path(urlparse(url).path).name, transcode=transcode,
                              source_site="commons.wikimedia.org", attribution_note=f"Category: {info.get('_category', '')}")
                track = self._finish_track(media, track, LOUDNESS_TARGET_MUSIC_LUFS)
                tracks.append(track)
                have_urls.add(url)
                station_bytes += track.bytes
                self.total_bytes += track.bytes
                log.info("[%s] + %s — %s (%s, %.0fs, %.1f MB, %.1f LUFS)", spec.id, title, artist, track.licence, track.duration_s,
                         track.bytes / 1e6, track.loudness_lufs if track.loudness_lufs is not None else float("nan"))
            except (FetchError, subprocess.TimeoutExpired, OSError) as e:
                self.problems.append(f"[{spec.id}] {title}: {e}")
                log.warning("[%s] skip %s: %s", spec.id, title, e)
                for p in (raw, media):
                    if p.exists():
                        p.unlink()
        return tracks

    # ---- LibriVox talk station
    def fetch_ia_station(self, spec: StationSpec) -> list[Track]:
        st_dir = RADIO_ROOT / spec.id
        st_dir.mkdir(parents=True, exist_ok=True)
        tracks: list[Track] = []
        for media in sorted(st_dir.glob("*.ogg")):
            t = self.existing(media)
            if t:
                tracks.append(t)
                self.total_bytes += t.bytes
        have = {t.source_url for t in tracks}
        station_bytes = sum(t.bytes for t in tracks)
        for ident, max_ch in spec.ia_items:
            if len(tracks) >= spec.max_tracks or station_bytes >= spec.target_mb * 1024 * 1024:
                break
            try:
                meta = self.http.json(IA_META + ident)
            except FetchError as e:
                self.problems.append(f"[talk] {ident}: {e}")
                continue
            md = meta.get("metadata") or {}
            lic_url = md.get("licenseurl") or ""
            lic = None
            if "publicdomain" in lic_url or "zero/1.0" in lic_url:
                lic = "Public Domain (LibriVox; CC PDM/CC0)"
            if lic is None:
                self.problems.append(f"[talk] {ident}: licence url {lic_url!r} is not public-domain; skipped")
                continue
            files = [f for f in meta.get("files", []) if f.get("name", "").lower().endswith(".mp3") and f.get("format") in ("VBR MP3", "64Kbps MP3", "128Kbps MP3")]
            # one entry per chapter, best format first
            by_chapter: dict[str, dict] = {}
            for f in files:
                key = re.sub(r"_(64kb|128kb)$", "", Path(f["name"]).stem)
                pref = {"VBR MP3": 0, "128Kbps MP3": 1, "64Kbps MP3": 2}[f["format"]]
                if key not in by_chapter or pref < by_chapter[key]["_pref"]:
                    by_chapter[key] = {**f, "_pref": pref}
            chapters = sorted(by_chapter.values(), key=lambda f: f["name"])
            picked = 0
            for f in chapters:
                if picked >= max_ch or len(tracks) >= spec.max_tracks:
                    break
                length = f.get("length")
                try:
                    dur = float(length) if length and ":" not in str(length) else sum(float(x) * 60 ** i for i, x in enumerate(reversed(str(length).split(":"))))
                except (TypeError, ValueError):
                    dur = 0.0
                if not (TALK_MIN_S <= dur <= TALK_MAX_S):
                    continue
                url = IA_DOWNLOAD + ident + "/" + quote(f["name"])
                if url in have:
                    picked += 1
                    continue
                stem = safe_stem(f["name"])
                media = st_dir / f"{stem}.ogg"
                title = f.get("title") or Path(f["name"]).stem.replace("_", " ")
                reader = md.get("creator") or "LibriVox volunteers"
                if self.dry_run:
                    log.info("[talk] would fetch %s / %s (%.0fs)", md.get("title"), title, dur)
                    picked += 1
                    continue
                raw = self.tmp / f"talk_{stem}.mp3"
                try:
                    size = int(f.get("size") or 0)
                    if size > 40 * 1024 * 1024:
                        raise FetchError("chapter file larger than 40 MB")
                    self.http.download(url, raw, max_bytes=40 * 1024 * 1024, expect_prefixes=(b"ID3", b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"))
                    assert self.ff is not None
                    transcode = self.ff.to_ogg(raw, media, mono=True, quality=1.5, sample_rate=32000, max_seconds=None)
                    raw.unlink(missing_ok=True)
                    track = Track(file=f"{spec.id}/{media.name}", title=f"{md.get('title', ident)} — {title}", artist=f"{reader}; read by LibriVox volunteers",
                                  licence=lic, licence_url=lic_url, source_url=url, source_page=f"https://archive.org/details/{ident}", duration_s=dur, bytes=0,
                                  sha256="", loudness_lufs=None, gain_db=0.0, original_filename=f["name"], transcode=transcode, source_site="archive.org (LibriVox)",
                                  attribution_note="LibriVox recordings are in the public domain; text is public domain (pre-1930 US).")
                    track = self._finish_track(media, track, LOUDNESS_TARGET_TALK_LUFS)
                    tracks.append(track)
                    have.add(url)
                    picked += 1
                    station_bytes += track.bytes
                    self.total_bytes += track.bytes
                    log.info("[talk] + %s (%.0fs, %.1f MB)", track.title, track.duration_s, track.bytes / 1e6)
                except (FetchError, subprocess.TimeoutExpired, OSError) as e:
                    self.problems.append(f"[talk] {ident}/{f['name']}: {e}")
                    log.warning("[talk] skip %s: %s", f["name"], e)
                    for p in (raw, media):
                        if p.exists():
                            p.unlink()
        return tracks

    # ---- SFX from OpenGameArt (CC0 only)
    def fetch_oga_sfx(self) -> list[Track]:
        out: list[Track] = []
        SFX_ROOT.mkdir(parents=True, exist_ok=True)
        for query, stem, want in OGA_SFX_QUERIES:
            got = 0
            for existing in sorted(SFX_ROOT.glob(f"{stem}_*.*")):
                if existing.suffix in (".ogg", ".wav"):
                    t = self.existing(existing)
                    if t:
                        out.append(t)
                        got += 1
            if got >= want:
                continue
            try:
                r = self.http.get(OGA_ROOT + "/art-search-advanced", params={"keys": query, "field_art_type_tid[]": ["13", "12"], "field_art_licenses_tid[]": "4",
                                                                            "sort_by": "count", "sort_order": "DESC"})
                if r.status_code >= 400:
                    raise FetchError(f"HTTP {r.status_code}")
                nodes = [n for n in dict.fromkeys(re.findall(r'href="(/content/[a-z0-9\-]+)"', r.text)) if n not in ("/content/faq",) and "forum" not in n]
            except FetchError as e:
                self.problems.append(f"[sfx] OGA search {query!r}: {e}")
                continue
            for node in nodes[:6]:
                if got >= want:
                    break
                try:
                    page = self.http.get(OGA_ROOT + node)
                    if page.status_code >= 400:
                        continue
                    lic_m = re.search(r"field-name-field-art-licenses.*?field-item[^>]*>(.*?)</div>", page.text, re.S)
                    lic_txt = strip_html(lic_m.group(1)) if lic_m else ""
                    if not re.fullmatch(r"\s*CC0\s*", lic_txt):
                        log.info("[sfx] %s licence %r is not CC0-only; skipped", node, lic_txt)
                        continue
                    author_m = re.search(r"Author:.*?<a[^>]*>(.*?)</a>", page.text, re.S) or re.search(r'class="username"[^>]*>(.*?)<', page.text, re.S)
                    author = strip_html(author_m.group(1)) if author_m else "unknown (OpenGameArt user)"
                    title_m = re.search(r"<title>(.*?)\s*\|\s*OpenGameArt", page.text, re.S)
                    title = strip_html(title_m.group(1)) if title_m else node.rsplit("/", 1)[-1]
                    note_m = re.search(r"field-name-field-copyright-notice.*?field-item[^>]*>(.*?)</div>", page.text, re.S)
                    note = strip_html(note_m.group(1)) if note_m else ""
                    files = [u for u in dict.fromkeys(re.findall(r'https://opengameart\.org/sites/default/files/[^"\'<> ]+\.(?:ogg|wav|flac|mp3)', page.text))
                             if "/styles/" not in u and "/audio_preview/" not in u]
                    for url in files[:2]:
                        if got >= want:
                            break
                        ext = Path(urlparse(url).path).suffix.lower()
                        media = SFX_ROOT / f"{stem}_{got + 1}{'.wav' if ext == '.wav' else '.ogg'}"
                        if self.dry_run:
                            log.info("[sfx] would fetch %s (%s) by %s", title, url, author)
                            got += 1
                            continue
                        raw = self.tmp / f"sfx_{stem}_{got + 1}{ext}"
                        self.http.download(url, raw, max_bytes=12 * 1024 * 1024, expect_prefixes=(b"OggS", b"RIFF", b"fLaC", b"ID3", b"\xff\xfb"))
                        assert self.ff is not None
                        dur, codec, _rate, _ch = self.ff.probe(raw)
                        if dur > SFX_MAX_S * 4:
                            raw.unlink(missing_ok=True)
                            continue
                        transcode = None
                        if ext == ".wav":
                            shutil.move(str(raw), str(media))
                        elif ext == ".ogg" and codec == "vorbis":
                            shutil.move(str(raw), str(media))
                        else:
                            transcode = self.ff.to_ogg(raw, media, mono=False, quality=5.0, sample_rate=44100, max_seconds=None)
                            raw.unlink(missing_ok=True)
                        track = Track(file=f"sfx/{media.name}", title=title, artist=author, licence="CC0-1.0", licence_url="https://creativecommons.org/publicdomain/zero/1.0/",
                                      source_url=url, source_page=OGA_ROOT + node, duration_s=dur, bytes=0, sha256="", loudness_lufs=None, gain_db=0.0,
                                      original_filename=Path(urlparse(url).path).name, transcode=transcode, source_site="opengameart.org", attribution_note=note)
                        track = self._finish_track(media, track, LOUDNESS_TARGET_MUSIC_LUFS)
                        out.append(track)
                        self.total_bytes += track.bytes
                        got += 1
                        log.info("[sfx] + %s <- %s by %s (%.1fs)", media.name, title, author, dur)
                except (FetchError, subprocess.TimeoutExpired, OSError) as e:
                    self.problems.append(f"[sfx] {node}: {e}")
                    log.warning("[sfx] skip %s: %s", node, e)
            if got < want:
                self.problems.append(f"[sfx] only {got}/{want} CC0 files found for {query!r}")
        return out

    # ---- SFX field recordings from Commons
    def fetch_commons_sfx(self) -> list[Track]:
        out: list[Track] = []
        SFX_ROOT.mkdir(parents=True, exist_ok=True)
        for query, stem, want in COMMONS_SFX_QUERIES:
            got = 0
            for existing in sorted(SFX_ROOT.glob(f"{stem}_*.ogg")):
                t = self.existing(existing)
                if t:
                    out.append(t)
                    got += 1
            if got >= want:
                continue
            try:
                infos = self.commons.search_files(query, limit=15)
            except FetchError as e:
                self.problems.append(f"[sfx] Commons search {query!r}: {e}")
                continue
            for info in infos:
                if got >= want:
                    break
                ok, _why = candidate_ok(info, min_s=1.0, max_s=SFX_MAX_S * 8, max_bytes=MUSIC_MAX_BYTES)
                if not ok:
                    continue
                lic, lic_url, artist, obj = Commons.licence_of(info)
                if lic is None:
                    continue
                url = clean_url(info["url"])
                title = obj or strip_html(info["title"]).removeprefix("File:")
                media = SFX_ROOT / f"{stem}_{got + 1}.ogg"
                if self.dry_run:
                    log.info("[sfx] would fetch %s (%s, %s)", title, lic, artist)
                    got += 1
                    continue
                raw = self.tmp / f"csfx_{stem}{Path(urlparse(url).path).suffix.lower()}"
                try:
                    self.http.download(url, raw, max_bytes=MUSIC_MAX_BYTES, expect_prefixes=(b"OggS", b"ID3", b"\xff\xfb", b"\xff\xf3", b"fLaC", b"RIFF", b"\x1a\x45\xdf\xa3"))
                    assert self.ff is not None
                    dur, codec, _r, _c = self.ff.probe(raw)
                    trim = SFX_MAX_S * 2 if dur > SFX_MAX_S * 2 else None
                    if codec == "vorbis" and trim is None:
                        shutil.move(str(raw), str(media))
                        transcode = None
                    else:
                        transcode = self.ff.to_ogg(raw, media, mono=False, quality=4.0, sample_rate=44100, max_seconds=trim)
                        raw.unlink(missing_ok=True)
                    track = Track(file=f"sfx/{media.name}", title=title, artist=artist, licence=lic, licence_url=lic_url, source_url=url,
                                  source_page=info.get("descriptionurl", ""), duration_s=dur, bytes=0, sha256="", loudness_lufs=None, gain_db=0.0,
                                  original_filename=Path(urlparse(url).path).name, transcode=transcode, source_site="commons.wikimedia.org",
                                  attribution_note=f"search: {query}")
                    track = self._finish_track(media, track, LOUDNESS_TARGET_MUSIC_LUFS)
                    out.append(track)
                    self.total_bytes += track.bytes
                    got += 1
                    log.info("[sfx] + %s <- %s (%s, %.0fs)", media.name, title, lic, track.duration_s)
                except (FetchError, subprocess.TimeoutExpired, OSError) as e:
                    self.problems.append(f"[sfx] {title}: {e}")
                    log.warning("[sfx] skip %s: %s", title, e)
                    for p in (raw, media):
                        if p.exists():
                            p.unlink()
            if got < want:
                self.problems.append(f"[sfx] only {got}/{want} licensed Commons files for {query!r}")
        return out

    # ---- outputs
    def write_outputs(self, stations: list[tuple[StationSpec, list[Track]]], sfx: list[Track]) -> None:
        st_docs = []
        for spec, tracks in stations:
            if len(tracks) < MIN_TRACKS:
                self.problems.append(f"[{spec.id}] only {len(tracks)} tracks (< {MIN_TRACKS}); station dropped from stations.json")
                continue
            st_docs.append({"id": spec.id, "name": spec.name, "frequency_mhz": spec.frequency_mhz, "kind": spec.kind, "genre": spec.genre,
                            "band": "AM" if spec.frequency_mhz > 200 else "FM",
                            "tracks": [{k: v for k, v in asdict(t).items() if k in ("file", "title", "artist", "licence", "licence_url", "source_url", "duration_s", "gain_db", "bytes", "sha256")}
                                       for t in sorted(tracks, key=lambda t: t.file)]})
        doc = {"schema_version": SCHEMA_VERSION, "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
               "generator": "unreal/tools/fetch_radio.py", "note": "Fictional dial; station names/frequencies are not affiliated with any broadcaster.",
               "audio_root": "assets/audio/radio", "stations": st_docs}
        RADIO_ROOT.mkdir(parents=True, exist_ok=True)
        with open(STATIONS_PATH, "w") as f:
            json.dump(doc, f, indent=1)
        all_tracks = [t for _, ts in stations for t in ts] + sfx
        cat = {"schema_version": SCHEMA_VERSION, "generated_at": doc["generated_at"], "total_bytes": sum(t.bytes for t in all_tracks),
               "files": [asdict(t) for t in sorted(all_tracks, key=lambda t: t.file)], "problems": self.problems,
               "http_calls": self.http.calls, "http_retries": self.http.retries}
        with open(CATALOG_PATH, "w") as f:
            json.dump(cat, f, indent=1)
        self.write_licenses_md(all_tracks)

    def write_licenses_md(self, tracks: list[Track]) -> None:
        marker_start = "<!-- BEGIN audio-radio-sfx (generated by unreal/tools/fetch_radio.py) -->"
        marker_end = "<!-- END audio-radio-sfx -->"
        lines = [marker_start, "", "## Audio: radio stations and sampled SFX (Unreal agent 2)", "",
                 "Fetched by `unreal/tools/fetch_radio.py`; one `*.license.json` record sits next to every file with url, licence, author, sha256.",
                 "Music/talk tracks are decoded at runtime from OGG Vorbis by `URadioSubsystem`; SFX are imported as `USoundWave` by the editor import script.",
                 "Only CC0 / Public Domain / CC BY (no SA, NC, ND) files are accepted. Radio dial names are fictional.", "",
                 "| file | title | author | licence | source |", "|---|---|---|---|---|"]
        for t in sorted(tracks, key=lambda t: t.file):
            src = t.source_page or t.source_url
            lines.append(f"| `{t.file}` | {t.title.replace('|', '/')} | {t.artist.replace('|', '/')} | [{t.licence}]({t.licence_url}) | [{t.source_site}]({src}) |"
                         if t.licence_url else f"| `{t.file}` | {t.title.replace('|', '/')} | {t.artist.replace('|', '/')} | {t.licence} | [{t.source_site}]({src}) |")
        lines += ["", f"Total: {len(tracks)} files, {sum(t.bytes for t in tracks) / 1e6:.1f} MB.", "", marker_end]
        block = "\n".join(lines)
        LICENSES_MD.parent.mkdir(parents=True, exist_ok=True)
        if LICENSES_MD.exists():
            text = LICENSES_MD.read_text()
            if marker_start in text and marker_end in text:
                pre, rest = text.split(marker_start, 1)
                _, post = rest.split(marker_end, 1)
                text = pre + block + post
            else:
                text = text.rstrip("\n") + "\n\n" + block + "\n"
        else:
            text = "# Asset licences\n\nEvery third-party asset used by NYCSim, with licence and provenance.\n\n" + block + "\n"
        LICENSES_MD.write_text(text)

    def run(self) -> int:
        stations: list[tuple[StationSpec, list[Track]]] = []
        for spec in STATIONS:
            if self.only and spec.id not in self.only:
                continue
            try:
                tracks = self.fetch_ia_station(spec) if spec.ia_items else self.fetch_commons_station(spec)
            except Exception as e:  # noqa: BLE001 — one station must never abort the others
                log.exception("[%s] station failed: %s", spec.id, e)
                self.problems.append(f"[{spec.id}] station aborted: {e}")
                tracks = []
            stations.append((spec, tracks))
            log.info("[%s] %d tracks, running total %.1f MB", spec.id, len(tracks), self.total_bytes / 1e6)
        sfx: list[Track] = []
        if not self.only or "sfx" in self.only:
            for fn in (self.fetch_oga_sfx, self.fetch_commons_sfx):
                try:
                    sfx += fn()
                except Exception as e:  # noqa: BLE001
                    log.exception("sfx stage failed: %s", e)
                    self.problems.append(f"[sfx] stage aborted: {e}")
        if not self.dry_run:
            self.write_outputs(stations, sfx)
        shutil.rmtree(self.tmp, ignore_errors=True)
        print(json.dumps({"stations": {s.id: len(t) for s, t in stations}, "sfx": len(sfx), "total_mb": round(self.total_bytes / 1e6, 1),
                          "http_calls": self.http.calls, "http_retries": self.http.retries, "problems": len(self.problems)}, indent=1))
        for p in self.problems:
            log.warning("problem: %s", p)
        return 0 if any(len(t) >= MIN_TRACKS for _, t in stations) else 1


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--max-total-mb", type=float, default=300.0)
    ap.add_argument("--station", action="append", default=[], help="restrict to station id(s) or 'sfx'")
    ap.add_argument("--dry-run", action="store_true", help="list what would be fetched; no downloads, no ffmpeg needed")
    ap.add_argument("--seed", type=int, default=20260905)
    ap.add_argument("-v", "--verbose", action="store_true")
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if a.verbose else logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    try:
        f = Fetcher(max_total_mb=a.max_total_mb, dry_run=a.dry_run, seed=a.seed, only=set(a.station) or None)
    except FetchError as e:
        log.error("%s", e)
        return 2
    return f.run()


if __name__ == "__main__":
    sys.exit(main())
