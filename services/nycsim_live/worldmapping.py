"""Weather observation → renderable world state (the numbers the engine actually consumes).

Every quantity below is a *derived visual/behaviour parameter*, not an observation: it is computed from
:class:`~nycsim_live.weather.WeatherObservation` fields by the closed-form rules documented here and in
``docs/LIVE_ALGORITHMS.md`` §4, and is reproduced number-for-number by ``core/weather/WorldMapping.{h,cpp}``.
Nothing is invented: when the driving observation field is ``None`` the derived value falls back to the
documented neutral value and the field is listed in :attr:`WorldState.missing`.

State that must persist between polls (wetness, puddles, snow cover) lives in ``live/world_state.json`` and
is integrated with **exact** solutions of the underlying ODEs so the result is independent of the poll
cadence (60 s in production, minutes when the process restarts):

    first-order lag  dx/dt = (x* − x)/τ            →  x' = x* + (x − x*)·exp(−Δt/τ)
    linear reservoir dx/dt = a − b                 →  x' = x + (a − b)·Δt

Angle conventions follow DATA_CONTRACTS: ``*_heading`` is compass (0 = north, clockwise), ``*_dir_deg`` is
mathematical (0 = east, counter-clockwise). Vectors are ENU metres (x = east, y = north, z = up); the UE
vector applies the ``core/geo/UECoords.h`` mapping (UE.X = east, UE.Y = −north, UE.Z = up).
"""
from __future__ import annotations

import logging
import math
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Final

from .paths import WORLD_STATE_JSON, read_json, write_json_atomic
from .weather import WeatherObservation, clamp, dewpoint_from_rh

log = logging.getLogger("nycsim.live.worldmapping")

SCHEMA_VERSION: Final = 1

# --------------------------------------------------------------------------- wetness
# Surface wetness 0 (bone dry) .. 1 (fully wet, mirror-like specular). Target from the liquid-equivalent
# precipitation rate; first-order lag towards it with separate rise and dry-out time constants.
WET_ONSET: Final = 0.25  # any measurable precipitation immediately damps the surface to at least this
WET_SATURATION_MMPH: Final = 2.5  # moderate rain; at and above this the road is fully wet
TAU_WET_BASE_S: Final = 240.0  # rise time constant at 1 mm/h (4 min: puddleless sheen forms fast)
TAU_WET_MIN_S: Final = 30.0
TAU_DRY_BASE_S: Final = 5400.0  # 90 min dry-out at the reference state: 20 °C, RH 50 %, calm, no sun
TAU_DRY_MIN_S: Final = 300.0
TAU_DRY_MAX_S: Final = 86400.0
FREEZE_DRY_FACTOR: Final = 4.0  # below 0 °C liquid water freezes instead of evaporating (sublimation only)
DEW_RH_THRESHOLD: Final = 97.0  # RH at or above which condensation alone keeps surfaces damp
DEW_WETNESS: Final = 0.10
FOG_WETNESS: Final = 0.15  # fog deposition (visibility < 1 km with FG/BR) leaves this much film
FOG_WET_VISIBILITY_M: Final = 1000.0
SNOW_WET_FRACTION: Final = 0.5  # snow melting on a warm surface delivers half the liquid film rain would

# --------------------------------------------------------------------------- puddles
PUDDLE_ONSET_WETNESS: Final = 0.85  # ponding only starts once the surface film is saturated
PUDDLE_FULL_MM: Final = 8.0  # accumulated excess depth that fills the modelled kerbside puddles
DRAIN_MMPH: Final = 1.5  # NYC catch-basin + infiltration capacity used in the reservoir balance
PUDDLE_EVAP_FACTOR: Final = 0.35  # puddles evaporate at 35 % of the film's rate (much larger water mass)

# --------------------------------------------------------------------------- snow cover
SNOW_FULL_COVER_CM: Final = 2.0  # depth at which pavement/roof texture is completely hidden
SNOW_MELT_CM_PER_H_PER_C: Final = 0.06  # identical to weather.SnowModel.MELT_CM_PER_H_PER_C
SNOW_MELT_ABOVE_C: Final = 1.0  # melting starts above +1 °C (pavement heat store), per the same model
SNOW_RAIN_MELT_CM_PER_MM: Final = 0.02  # rain-on-snow, identical to weather.SnowModel
ROAD_CLEAR_TRAFFIC_PER_H: Final = 0.15  # fraction of road cover removed per hour by traffic alone
ROAD_CLEAR_PLOW_PER_H: Final = 1.20  # additional fraction per hour once plows are out
ROAD_CLEAR_SALT_PER_H: Final = 0.40  # additional fraction per hour once spreaders are out
# DSNY operational thresholds (NYC Snow Plan): spreaders pre-treat at/below freezing whenever frozen
# precipitation falls; plows are dispatched once accumulation reaches 2 inches.
PLOW_THRESHOLD_CM: Final = 5.08  # 2.00 in
SALT_TEMP_C: Final = 1.0

# --------------------------------------------------------------------------- fog
# Koschmieder: meteorological optical range V = 3.912/β for a 2 % contrast threshold, so β = 3.912/V is the
# extinction coefficient (1/m) the engine's exponential height fog needs directly.
KOSCHMIEDER_K: Final = 3.912
FOG_VIS_CLEAR_M: Final = 10000.0  # at and above this the density is 0
FOG_VIS_DENSE_M: Final = 50.0  # at and below this the density is 1
FOG_OBSCURATIONS: Final = ("FG", "BR")  # fog, mist — water droplets
AEROSOL_OBSCURATIONS: Final = ("HZ", "FU", "DU", "SA", "VA", "PY")  # haze, smoke, dust — dry aerosol

# --------------------------------------------------------------------------- umbrellas
UMBRELLA_MAX: Final = 0.85  # fraction of pedestrians with an open umbrella in steady moderate rain
UMBRELLA_RATE_SCALE_MMPH: Final = 0.8  # e-folding rate of the saturating response
UMBRELLA_TYPE_FACTOR: Final[dict[str, float]] = {
    "rain": 1.0, "drizzle": 0.7, "freezing_rain": 0.9, "sleet": 0.6, "snow": 0.35, "none": 0.0,
}
UMBRELLA_WIND_KNEE_MPS: Final = 8.0  # below this wind has no effect
UMBRELLA_WIND_ZERO_MPS: Final = 17.0  # at this wind only the stubborn minimum remains
UMBRELLA_WIND_MIN: Final = 0.10

# --------------------------------------------------------------------------- window condensation
INDOOR_TEMP_C: Final = 21.0  # heating season set point
INDOOR_RH: Final = 40.0
INDOOR_TEMP_COOLED_C: Final = 23.0  # air-conditioning set point used above OUTDOOR_AC_C
OUTDOOR_AC_C: Final = 26.0
GLASS_SURFACE_RATIO: Final = 0.35  # R_si / R_total for typical double glazing (0.13 / 0.36)
CONDENSATION_FULL_C: Final = 3.0  # this many °C below the dew point = fully fogged pane


@dataclass
class WorldState:
    """Everything ``core/weather`` hands to the renderer and the crowd/vehicle systems."""

    schema_version: int = SCHEMA_VERSION
    updated_at_unix: float | None = None
    source: str = "stale"  # weather source that drove this update
    observation_age_s: float | None = None
    # --- surfaces
    wetness: float = 0.0  # 0..1 water film on horizontal surfaces (roads, sidewalks, roofs)
    wetness_target: float = 0.0
    tau_used_s: float = 0.0  # time constant actually applied this step (rise or dry-out)
    drying: bool = True
    puddle_level: float = 0.0  # 0..1 fill of the modelled kerbside puddles
    puddle_depth_mm: float = 0.0  # PUDDLE_FULL_MM · puddle_level
    road_ice: bool = False  # black ice: wet or damp surface at or below 0 °C
    # --- snow
    snow_depth_cm: float = 0.0
    snow_cover: float = 0.0  # 0..1 ground/roof coverage
    snow_cover_road: float = 0.0  # 0..1 carriageway coverage after traffic, plowing and salting
    snow_melting: bool = False
    plow_active: bool = False
    salt_active: bool = False
    # --- air
    fog_density: float = 0.0  # 0..1 droplet obscuration
    haze_density: float = 0.0  # 0..1 dry-aerosol obscuration
    extinction_per_m: float = 0.0  # β = 3.912/visibility, feeds exponential height fog directly
    visibility_m: float | None = None
    cloud_cover: float = 0.0
    # --- wind
    wind_speed_mps: float = 0.0
    wind_gust_mps: float = 0.0
    wind_from_heading: float | None = None  # compass, direction the wind blows FROM
    wind_to_heading: float | None = None  # compass, direction of air motion
    wind_vector_enu: list[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])  # m/s, air motion
    wind_vector_ue: list[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])  # m/s in UE axes
    # --- behaviour
    umbrella_probability: float = 0.0
    # --- glass
    window_condensation: float = 0.0  # max of the two below
    window_condensation_interior: float = 0.0  # winter: warm humid room against cold glass
    window_condensation_exterior: float = 0.0  # summer: humid outdoor air against AC-cooled glass
    # --- bookkeeping
    missing: list[str] = field(default_factory=list)  # observation fields that were null (neutral used)

    def to_json_dict(self) -> dict:
        d = asdict(self)
        for k, v in d.items():
            if isinstance(v, float):
                d[k] = round(v, 4)
            elif isinstance(v, list) and v and isinstance(v[0], float):
                d[k] = [round(x, 4) for x in v]
        return d


# --------------------------------------------------------------------------- pure helpers
def lag(current: float, target: float, dt_s: float, tau_s: float) -> float:
    """Exact solution of dx/dt = (target − x)/τ over Δt (cadence-independent)."""
    if dt_s <= 0.0:
        return current
    if tau_s <= 0.0:
        return target
    return target + (current - target) * math.exp(-dt_s / tau_s)


def wetness_target(obs: WeatherObservation) -> float:
    """Equilibrium wetness the current sky would hold a surface at.

    ``max`` of three independent sources: falling precipitation (0.25 at a trace, 1.0 at
    :data:`WET_SATURATION_MMPH`), fog deposition, and dew at very high humidity. Frozen precipitation only
    wets the surface when it can melt on it (T > 0 °C), and then at :data:`SNOW_WET_FRACTION` of the liquid
    contribution, because most of the mass stays as snow (that mass is the snow-cover model's business).
    """
    t = 0.0
    rate = obs.precip_rate_mmph or 0.0
    if obs.precip_type != "none" and rate > 0.0:
        wet = WET_ONSET + (1.0 - WET_ONSET) * min(1.0, rate / WET_SATURATION_MMPH)
        if obs.precip_type in ("snow", "sleet"):
            if obs.temp_c is None or obs.temp_c <= 0.0:
                wet = 0.0  # dry snow on a frozen surface leaves no liquid film
            else:
                wet *= SNOW_WET_FRACTION
        t = max(t, wet)
    if obs.visibility_m is not None and obs.visibility_m < FOG_WET_VISIBILITY_M and any(o in FOG_OBSCURATIONS for o in obs.obscuration):
        t = max(t, FOG_WETNESS)
    if obs.rh is not None and obs.rh >= DEW_RH_THRESHOLD:
        t = max(t, DEW_WETNESS)
    return clamp(t, 0.0, 1.0)


def tau_wet_s(rate_mmph: float) -> float:
    """Rise time constant: heavier rain wets a surface faster (τ ∝ 1/(1 + R/2))."""
    return max(TAU_WET_MIN_S, TAU_WET_BASE_S / (1.0 + max(0.0, rate_mmph) / 2.0))


def tau_dry_s(temp_c: float | None, rh: float | None, wind_mps: float | None, solar_factor: float) -> float:
    """Dry-out time constant from a bulk-aerodynamic evaporation rate, normalised to the reference state.

    E ∝ (1 − RH)·(1 + u/3)·2^((T − 20)/10)·(1 + 1.5·S):
      * ``1 − RH``      moisture deficit driving the vapour flux (floor 0.02 for saturated air);
      * ``1 + u/3``     bulk transfer coefficient grows roughly linearly with wind speed;
      * ``2^((T−20)/10)`` Clausius–Clapeyron: saturation vapour pressure roughly doubles per 10 K in 0–30 °C;
      * ``1 + 1.5·S``   direct sun more than doubles the surface energy available for evaporation, where
        S = max(0, sin(solar elevation))·(1 − 0.7·cloud) is the clear-sky-normalised insolation.
    The denominator is scaled by 2 so that the reference state (20 °C, RH 50 %, calm, dark) gives exactly
    :data:`TAU_DRY_BASE_S`. Below 0 °C the film freezes and τ is multiplied by :data:`FREEZE_DRY_FACTOR`.
    """
    deficit = 0.02 if rh is None else max(0.02, 1.0 - clamp(rh, 0.0, 100.0) / 100.0)
    if rh is None:
        deficit = 0.5  # neutral: reference humidity
    u = 0.0 if wind_mps is None else max(0.0, wind_mps)
    t = 20.0 if temp_c is None else temp_c
    e = 2.0 * deficit * (1.0 + u / 3.0) * (2.0 ** ((t - 20.0) / 10.0)) * (1.0 + 1.5 * clamp(solar_factor, 0.0, 1.0))
    tau = TAU_DRY_BASE_S / max(1e-6, e)
    if t < 0.0:
        tau *= FREEZE_DRY_FACTOR
    return clamp(tau, TAU_DRY_MIN_S, TAU_DRY_MAX_S)


def solar_factor(sun_elevation_deg: float | None, cloud_cover: float | None) -> float:
    """Clear-sky-normalised insolation S = max(0, sin(elevation))·(1 − 0.7·cloud), 0 at night."""
    if sun_elevation_deg is None:
        return 0.0
    s = math.sin(math.radians(sun_elevation_deg))
    if s <= 0.0:
        return 0.0
    return clamp(s * (1.0 - 0.7 * clamp(cloud_cover if cloud_cover is not None else 0.0, 0.0, 1.0)), 0.0, 1.0)


def fog_density_from_visibility(visibility_m: float | None) -> float:
    """Logarithmic map of visibility to a 0..1 density (extinction doubles per halving of visibility).

    d = ln(V_clear/V) / ln(V_clear/V_dense), clamped — 0 at 10 km, 1 at 50 m, 0.5 at ≈707 m.
    """
    if visibility_m is None or visibility_m <= 0.0:
        return 0.0
    if visibility_m >= FOG_VIS_CLEAR_M:
        return 0.0
    if visibility_m <= FOG_VIS_DENSE_M:
        return 1.0
    return clamp(math.log(FOG_VIS_CLEAR_M / visibility_m) / math.log(FOG_VIS_CLEAR_M / FOG_VIS_DENSE_M), 0.0, 1.0)


def extinction_per_m(visibility_m: float | None) -> float:
    """β = 3.912/V (Koschmieder, 2 % contrast threshold). 0 when visibility is unknown or unlimited."""
    if visibility_m is None or visibility_m <= 0.0:
        return 0.0
    return KOSCHMIEDER_K / visibility_m


def wind_vectors(speed_mps: float | None, from_heading_deg: float | None) -> tuple[list[float], list[float]]:
    """(ENU, UE) air-motion vectors in m/s from the meteorological "from" heading.

    Air moves towards ``from + 180``: east = −sin(θ)·U, north = −cos(θ)·U (θ = compass "from").
    UE axes (``core/geo/UECoords.h``): X = east, Y = −north, Z = up.
    """
    if speed_mps is None or from_heading_deg is None:
        return [0.0, 0.0, 0.0], [0.0, 0.0, 0.0]
    th = math.radians(from_heading_deg % 360.0)
    east = -math.sin(th) * speed_mps
    north = -math.cos(th) * speed_mps
    return [east, north, 0.0], [east, -north, 0.0]


def umbrella_probability(precip_type: str, rate_mmph: float | None, wind_mps: float | None, thunder: bool = False) -> float:
    """Fraction of pedestrians with an open umbrella.

    p = UMBRELLA_MAX · type_factor · (1 − exp(−R/0.8 mm/h)) · wind_factor, where wind_factor falls linearly
    from 1 at 8 m/s to :data:`UMBRELLA_WIND_MIN` at 17 m/s (above which umbrellas invert and are abandoned).
    Thunderstorms add nothing on their own — the rate already carries the intensity.
    """
    f = UMBRELLA_TYPE_FACTOR.get(precip_type, 0.0)
    r = rate_mmph or 0.0
    if f <= 0.0 or r <= 0.0:
        return 0.0
    p = UMBRELLA_MAX * f * (1.0 - math.exp(-r / UMBRELLA_RATE_SCALE_MMPH))
    u = wind_mps or 0.0
    if u > UMBRELLA_WIND_KNEE_MPS:
        span = UMBRELLA_WIND_ZERO_MPS - UMBRELLA_WIND_KNEE_MPS
        p *= max(UMBRELLA_WIND_MIN, 1.0 - (u - UMBRELLA_WIND_KNEE_MPS) / span * (1.0 - UMBRELLA_WIND_MIN))
    return clamp(p, 0.0, UMBRELLA_MAX)


def window_condensation(temp_c: float | None, dewpoint_c: float | None) -> tuple[float, float]:
    """(interior, exterior) condensation on double glazing, 0..1.

    Interior surface temperature of a double-glazed pane: T_si = T_in − r·(T_in − T_out) with
    r = R_si/R_total = 0.13/0.36 = 0.35. Condensation forms once T_si drops below the *indoor* dew point
    (21 °C / 40 % RH ⇒ 6.9 °C); the fraction is linear over :data:`CONDENSATION_FULL_C` degrees below it.
    Above :data:`OUTDOOR_AC_C` the building is cooled to 23 °C and the mirror case applies: the exterior
    surface T_so = T_out − r·(T_out − T_in) falls below the *outdoor* dew point and the pane fogs outside.
    """
    if temp_c is None:
        return 0.0, 0.0
    td_in = dewpoint_from_rh(INDOOR_TEMP_C, INDOOR_RH)
    t_si = INDOOR_TEMP_C - GLASS_SURFACE_RATIO * (INDOOR_TEMP_C - temp_c)
    interior = clamp((td_in - t_si) / CONDENSATION_FULL_C, 0.0, 1.0)
    exterior = 0.0
    if temp_c > OUTDOOR_AC_C and dewpoint_c is not None:
        t_so = temp_c - GLASS_SURFACE_RATIO * (temp_c - INDOOR_TEMP_COOLED_C)
        exterior = clamp((dewpoint_c - t_so) / CONDENSATION_FULL_C, 0.0, 1.0)
    return interior, exterior


def plow_and_salt(snow_depth_cm: float, temp_c: float | None, precip_type: str) -> tuple[bool, bool]:
    """DSNY dispatch flags: spreaders at/below +1 °C with frozen precipitation or lying snow; plows at 2 in."""
    t = temp_c if temp_c is not None else 0.0
    frozen = precip_type in ("snow", "sleet", "freezing_rain")
    salt = (t <= SALT_TEMP_C and (frozen or snow_depth_cm > 0.0)) or precip_type == "freezing_rain"
    plow = snow_depth_cm >= PLOW_THRESHOLD_CM and (t <= SALT_TEMP_C or frozen)
    return plow, salt


# --------------------------------------------------------------------------- the mapper
class WorldMapper:
    """Stateful map from observations to :class:`WorldState`, persisted in ``live/world_state.json``."""

    def __init__(self, state_path: Path | None = WORLD_STATE_JSON, clock=time.time):
        self.state_path = state_path
        self.clock = clock
        self.wetness = 0.0
        self.puddle = 0.0
        self.snow_cover = 0.0
        self.snow_cover_road = 0.0
        self.last_update: float | None = None
        self.state: WorldState | None = None
        doc = read_json(state_path) if state_path is not None else None
        if doc:
            try:
                self.wetness = clamp(float(doc.get("wetness", 0.0)), 0.0, 1.0)
                self.puddle = clamp(float(doc.get("puddle_level", 0.0)), 0.0, 1.0)
                self.snow_cover = clamp(float(doc.get("snow_cover", 0.0)), 0.0, 1.0)
                self.snow_cover_road = clamp(float(doc.get("snow_cover_road", 0.0)), 0.0, 1.0)
                self.last_update = doc.get("updated_at_unix")
            except (TypeError, ValueError):
                log.warning("unusable world_state.json; starting from a dry world")

    # -- individual integrators (pure given the stored state, so the C++ port is testable term by term)
    def _step_wetness(self, obs: WeatherObservation, dt_s: float, sun_factor: float) -> tuple[float, float, bool]:
        target = wetness_target(obs)
        if target > self.wetness:
            tau = tau_wet_s(obs.precip_rate_mmph or 0.0)
            drying = False
        else:
            tau = tau_dry_s(obs.temp_c, obs.rh, obs.wind_mps, sun_factor)
            drying = True
        self.wetness = clamp(lag(self.wetness, target, dt_s, tau), 0.0, 1.0)
        return target, tau, drying

    def _step_puddles(self, obs: WeatherObservation, dt_s: float, tau_dry: float) -> None:
        dt_h = dt_s / 3600.0
        rate = (obs.precip_rate_mmph or 0.0) if obs.precip_type in ("rain", "drizzle", "freezing_rain") else 0.0
        if obs.precip_type in ("snow", "sleet") and obs.temp_c is not None and obs.temp_c > SNOW_MELT_ABOVE_C:
            rate += (obs.precip_rate_mmph or 0.0)  # melting frozen precipitation still runs off
        if self.wetness >= PUDDLE_ONSET_WETNESS and rate > DRAIN_MMPH:
            self.puddle += (rate - DRAIN_MMPH) * dt_h / PUDDLE_FULL_MM
        else:
            drained = DRAIN_MMPH * dt_h / PUDDLE_FULL_MM
            # evaporation adds to draining; expressed as an equivalent first-order decay over tau_dry
            evaporated = self.puddle * (1.0 - math.exp(-dt_s / (tau_dry / PUDDLE_EVAP_FACTOR))) if tau_dry > 0 else 0.0
            self.puddle -= drained + evaporated
        self.puddle = clamp(self.puddle, 0.0, 1.0)

    def _step_snow(self, obs: WeatherObservation, dt_s: float, plow: bool, salt: bool) -> None:
        dt_h = dt_s / 3600.0
        depth = obs.snow_depth_cm or 0.0
        if obs.snow_depth_source == "observed":
            self.snow_cover = clamp(depth / SNOW_FULL_COVER_CM, 0.0, 1.0)
        else:
            accretion = (obs.snowfall_rate_cmph or 0.0) * dt_h / SNOW_FULL_COVER_CM
            melt = 0.0
            if obs.temp_c is not None and obs.temp_c > SNOW_MELT_ABOVE_C:
                melt += SNOW_MELT_CM_PER_H_PER_C * (obs.temp_c - SNOW_MELT_ABOVE_C) * dt_h / SNOW_FULL_COVER_CM
            if obs.precip_type in ("rain", "drizzle", "freezing_rain"):
                melt += SNOW_RAIN_MELT_CM_PER_MM * (obs.precip_rate_mmph or 0.0) * dt_h / SNOW_FULL_COVER_CM
            self.snow_cover = clamp(self.snow_cover + accretion - melt, 0.0, 1.0)
            # the depth model in weather.SnowModel is authoritative for depth; keep cover consistent with it
            self.snow_cover = min(self.snow_cover, clamp(depth / SNOW_FULL_COVER_CM, 0.0, 1.0)) if depth > 0.0 else (0.0 if obs.snow_depth_source == "none" else self.snow_cover)
        clear = ROAD_CLEAR_TRAFFIC_PER_H + (ROAD_CLEAR_PLOW_PER_H if plow else 0.0) + (ROAD_CLEAR_SALT_PER_H if salt else 0.0)
        road = min(self.snow_cover_road + max(0.0, self.snow_cover - self.snow_cover_road), self.snow_cover)
        self.snow_cover_road = clamp(road - clear * dt_h, 0.0, self.snow_cover)

    def update(self, obs: WeatherObservation, now_unix: float | None = None, sun_elevation_deg: float | None = None) -> WorldState:
        now = self.clock() if now_unix is None else now_unix
        dt_s = 0.0 if self.last_update is None else clamp(now - self.last_update, 0.0, 6 * 3600.0)
        s = solar_factor(sun_elevation_deg, obs.cloud_cover)
        target, tau, drying = self._step_wetness(obs, dt_s, s)
        tau_d = tau if drying else tau_dry_s(obs.temp_c, obs.rh, obs.wind_mps, s)
        self._step_puddles(obs, dt_s, tau_d)
        depth = obs.snow_depth_cm or 0.0
        plow, salt = plow_and_salt(depth, obs.temp_c, obs.precip_type)
        self._step_snow(obs, dt_s, plow, salt)
        enu, ue = wind_vectors(obs.wind_mps, obs.wind_from_heading)
        fog = fog_density_from_visibility(obs.visibility_m) if any(o in FOG_OBSCURATIONS for o in obs.obscuration) or (obs.rh or 0.0) >= 95.0 else 0.0
        haze = fog_density_from_visibility(obs.visibility_m) if any(o in AEROSOL_OBSCURATIONS for o in obs.obscuration) else 0.0
        if not obs.obscuration and obs.visibility_m is not None and obs.visibility_m < FOG_VIS_CLEAR_M and fog == 0.0:
            # visibility restricted without a reported obscuration group (e.g. heavy precipitation): treat as
            # droplet obscuration so the renderer still thickens the fog volume.
            fog = fog_density_from_visibility(obs.visibility_m)
        cond_in, cond_out = window_condensation(obs.temp_c, obs.dewpoint_c)
        missing = [k for k in ("temp_c", "dewpoint_c", "rh", "wind_mps", "wind_dir_deg", "cloud_cover", "visibility_m") if getattr(obs, k) is None]
        st = WorldState(
            updated_at_unix=now,
            source=obs.source,
            observation_age_s=obs.stale_age_s,
            wetness=self.wetness,
            wetness_target=target,
            tau_used_s=tau,
            drying=drying,
            puddle_level=self.puddle,
            puddle_depth_mm=self.puddle * PUDDLE_FULL_MM,
            road_ice=bool(obs.temp_c is not None and obs.temp_c <= 0.0 and self.wetness > 0.2),
            snow_depth_cm=depth,
            snow_cover=self.snow_cover,
            snow_cover_road=self.snow_cover_road,
            snow_melting=bool(obs.temp_c is not None and obs.temp_c > SNOW_MELT_ABOVE_C and self.snow_cover > 0.0),
            plow_active=plow,
            salt_active=salt,
            fog_density=fog,
            haze_density=haze,
            extinction_per_m=extinction_per_m(obs.visibility_m),
            visibility_m=obs.visibility_m,
            cloud_cover=obs.cloud_cover if obs.cloud_cover is not None else 0.0,
            wind_speed_mps=obs.wind_mps or 0.0,
            wind_gust_mps=obs.wind_gust_mps or (obs.wind_mps or 0.0),
            wind_from_heading=obs.wind_from_heading,
            wind_to_heading=obs.wind_to_heading,
            wind_vector_enu=enu,
            wind_vector_ue=ue,
            umbrella_probability=umbrella_probability(obs.precip_type, obs.precip_rate_mmph, obs.wind_mps, obs.thunder),
            window_condensation=max(cond_in, cond_out),
            window_condensation_interior=cond_in,
            window_condensation_exterior=cond_out,
            missing=missing,
        )
        self.last_update = now
        self.state = st
        if self.state_path is not None:
            try:
                write_json_atomic(self.state_path, st.to_json_dict())
            except OSError as e:
                log.warning("cannot persist world state: %s", e)
        return st
