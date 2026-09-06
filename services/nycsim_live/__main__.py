"""CLI for the live services: ``python -m nycsim_live [--once] [--polls N] [--interval S]``.

Drives one polling loop over every live subsystem and writes the snapshots the engine reads:
``live/weather.json``, ``live/world_state.json``, ``live/esb_lights.json``, ``live/tides.json`` and
``live/overlay.txt``. Each subsystem fails independently: a provider outage degrades that snapshot to its
documented stale/fallback state and never stops the loop.

Sub-commands: ``manhattanhenge YEAR`` prints and writes the henge table, ``spa-check`` prints the NREL SPA
reference case, ``overlay`` re-renders the overlay from the snapshots already on disk.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import logging
import sys
import time

from . import astronomy, debug_overlay, timesync
from .esb_lights import ESBLightsService
from .paths import ESB_LIGHTS_JSON, LIVE_DIR, OVERLAY_TXT, TIDES_JSON, WEATHER_JSON, read_json, record_snapshot, write_json_atomic
from .tides import TidesService
from .weather import POLL_INTERVAL_S, WeatherService
from .worldmapping import WorldMapper

log = logging.getLogger("nycsim.live")


def poll_once(weather: WeatherService, mapper: WorldMapper, esb: ESBLightsService, tides: TidesService, observer: astronomy.Observer) -> dict:
    """One pass over every subsystem; returns the values needed for the overlay."""
    t = timesync.sim_time_now()
    obs = weather.poll()
    sun = astronomy.solar_position(t.utc, observer)
    world = mapper.update(obs, t.unix_s, sun.elevation)
    try:
        esb_doc = esb.poll(_dt.date(*t.local_date)).to_json_dict()
    except Exception as e:  # noqa: BLE001 - one subsystem must never take the loop down
        log.error("ESB lights poll failed: %s", e)
        esb_doc = read_json(ESB_LIGHTS_JSON)
    try:
        tides_doc = tides.poll().to_json_dict()
    except Exception as e:  # noqa: BLE001
        log.error("tides poll failed: %s", e)
        tides_doc = read_json(TIDES_JSON)
    moon = astronomy.moon_position(t.utc, observer)
    events = astronomy.sun_events_local(_dt.date(*t.local_date), observer)
    text = debug_overlay.render(t, obs, world, sun, moon, events, esb_doc, tides_doc, observer)
    debug_overlay.write(text, OVERLAY_TXT)
    return {"sim_time": t, "weather": obs, "world": world, "sun": sun, "moon": moon, "events": events, "esb": esb_doc, "tides": tides_doc, "overlay": text}


def cmd_run(args: argparse.Namespace) -> int:
    observer = astronomy.CENTRAL_PARK
    weather = WeatherService(poll_interval_s=args.interval)
    mapper = WorldMapper()
    esb = ESBLightsService()
    tides = TidesService()
    n = 0
    while True:
        t0 = time.time()
        r = poll_once(weather, mapper, esb, tides, observer)
        n += 1
        if args.print_overlay:
            print(r["overlay"], end="")
        obs = r["weather"]
        log.info("poll %d: %s %s T=%s precip=%s age=%s", n, obs.source, obs.station, obs.temp_c, obs.precip_type, obs.stale_age_s)
        if args.once or (args.polls is not None and n >= args.polls):
            break
        delay = args.interval - (time.time() - t0)
        if delay > 0:
            time.sleep(delay)
    if args.record:
        record_snapshot("live/weather", WEATHER_JSON, ["api.weather.gov", "api.open-meteo.com", "aviationweather.gov", "tgftp.nws.noaa.gov"], "live/weather/1")
        record_snapshot("live/esb_lights", ESB_LIGHTS_JSON, ["esbnyc.com"], "live/esb_lights/1")
        record_snapshot("live/tides", TIDES_JSON, ["api.tidesandcurrents.noaa.gov"], "live/tides/1")
    return 0


def cmd_manhattanhenge(args: argparse.Namespace) -> int:
    obs = astronomy.TUDOR_CITY_42ND
    events = astronomy.manhattanhenge(args.year, obs)
    doc = {
        "year": args.year,
        "observer": {"latitude_deg": obs.latitude_deg, "longitude_deg": obs.longitude_deg, "elevation_m": obs.elevation_m, "pressure_mbar": obs.pressure_mbar, "temperature_c": obs.temperature_c, "atmos_refract_deg": obs.atmos_refract_deg},
        "grid_azimuth_deg": astronomy.MANHATTAN_STREET_SUNSET_AZIMUTH_DEG,
        "full_sun_elevation_deg": astronomy.FULL_SUN_ELEVATION_DEG,
        "half_sun_elevation_deg": astronomy.HALF_SUN_ELEVATION_DEG,
        "events": [
            {"kind": e.kind, "local_date": e.local_date.isoformat(), "utc": e.utc.isoformat().replace("+00:00", "Z"), "azimuth_deg": round(e.azimuth_deg, 4), "delta_from_grid_deg": round(e.delta_from_grid_deg, 4), "best_in_season": e.best_in_season}
            for e in events
        ],
    }
    for e in events:
        star = " *" if e.best_in_season else ""
        local = e.utc.astimezone(timesync.NYC_TZ) if timesync.NYC_TZ else e.utc
        print(f"{e.local_date} {e.kind:>4}  {local:%H:%M:%S} local  az {e.azimuth_deg:8.4f}  delta {e.delta_from_grid_deg:+.4f}{star}")
    if args.out:
        write_json_atomic(args.out, doc)
        print(f"wrote {args.out}")
    return 0


def cmd_spa_check(_args: argparse.Namespace) -> int:
    """NREL SPA (Reda & Andreas 2004/2008) Appendix A.5 reference case."""
    o = astronomy.Observer(39.742476, -105.1786, 1830.14, pressure_mbar=820.0, temperature_c=11.0)
    utc = _dt.datetime(2003, 10, 17, 19, 30, 30, tzinfo=_dt.timezone.utc)  # 12:30:30 local at UTC-7
    p = astronomy.solar_position(utc, o, delta_t_s=67.0)
    rows = [
        ("julian day", p.jd, 2452930.312847, 1e-6),
        ("delta psi (deg)", p.geocentric.delta_psi, -0.00399840, 1e-8),
        ("delta epsilon (deg)", p.geocentric.delta_epsilon, 0.00166657, 1e-8),
        ("epsilon (deg)", p.geocentric.epsilon, 23.440465, 1e-6),
        ("apparent lon (deg)", p.geocentric.lamda, 204.0085519, 1e-6),
        ("app. sidereal time", p.geocentric.nu, 318.5119, 1e-4),
        ("right ascension", p.geocentric.alpha, 202.22741, 1e-5),
        ("declination", p.geocentric.delta, -9.31434, 1e-5),
        ("hour angle", p.hour_angle, 11.105900, 1e-5),
        ("topocentric elev", p.elevation, 39.888378, 1e-6),
        ("zenith", p.zenith, 50.111622, 1e-6),
        ("azimuth", p.azimuth, 194.340241, 1e-6),
    ]
    ok = True
    for name, got, want, tol in rows:
        good = abs(got - want) <= tol
        ok &= good
        print(f"{name:<22} {got:>16.7f} {want:>16.7f} {'OK' if good else 'FAIL'}  (|d|={abs(got-want):.2e} tol={tol:g})")
    return 0 if ok else 1


def cmd_overlay(_args: argparse.Namespace) -> int:
    from .weather import WeatherObservation

    doc = read_json(WEATHER_JSON)
    if doc is None:
        print(f"no {WEATHER_JSON}; run `python -m nycsim_live --once` first", file=sys.stderr)
        return 1
    obs = WeatherObservation(**{k: v for k, v in doc.items() if k in WeatherObservation.__dataclass_fields__})
    world_doc = read_json(LIVE_DIR / "world_state.json")
    from .worldmapping import WorldState

    world = WorldState(**{k: v for k, v in (world_doc or {}).items() if k in WorldState.__dataclass_fields__}) if world_doc else None
    text = debug_overlay.render(timesync.sim_time_now(), obs, world, esb=read_json(ESB_LIGHTS_JSON), tides=read_json(TIDES_JSON))
    print(text, end="")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="nycsim_live", description=__doc__)
    ap.add_argument("-v", "--verbose", action="store_true")
    sub = ap.add_subparsers(dest="cmd")
    ap.add_argument("--once", action="store_true", help="one poll, then exit")
    ap.add_argument("--polls", type=int, default=None, help="stop after N polls")
    ap.add_argument("--interval", type=float, default=POLL_INTERVAL_S, help="seconds between polls (default 60)")
    ap.add_argument("--print-overlay", action="store_true", help="print the debug overlay after each poll")
    ap.add_argument("--record", action="store_true", help="record the snapshots in data/manifest/processed.json")
    mh = sub.add_parser("manhattanhenge", help="compute the Manhattanhenge dates for a year")
    mh.add_argument("year", type=int)
    mh.add_argument("--out", type=lambda s: __import__("pathlib").Path(s), default=None)
    mh.set_defaults(func=cmd_manhattanhenge)
    sp = sub.add_parser("spa-check", help="verify the NREL SPA reference case")
    sp.set_defaults(func=cmd_spa_check)
    ov = sub.add_parser("overlay", help="render the overlay from the snapshots on disk")
    ov.set_defaults(func=cmd_overlay)
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    fn = getattr(args, "func", cmd_run)
    return fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
