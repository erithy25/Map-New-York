"""Resolve raw input paths through the foundation source registry (never hard-coded)."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

from ..download import _target
from ..paths import RAW
from ..sources import SOURCES

log = logging.getLogger("nycsim.roads.inputs")

REQUIRED = ("centerline", "lion", "osm_newyork_pbf")
OPTIONAL = (
    "dot_signs", "vzv_speed_limits", "vzv_lpi_signals", "barnes_dance", "signal_retiming", "bike_routes", "bus_lanes",
    "truck_routes", "ped_plazas", "street_construction_permits", "plan_roadbed", "plan_curb", "plan_sidewalk",
    "plan_median", "plan_pavement_edge", "plan_transport_structures", "plan_parking_lot", "plan_public_plazas",
)


@dataclass
class RoadInputs:
    paths: dict[str, Path] = field(default_factory=dict)
    missing: list[str] = field(default_factory=list)

    def __getitem__(self, key: str) -> Path:
        return self.paths[key]

    def get(self, key: str) -> Path | None:
        return self.paths.get(key)

    def has(self, key: str) -> bool:
        return key in self.paths


def _candidates(source_id: str) -> list[Path]:
    src = SOURCES.get(source_id)
    out: list[Path] = []
    if src is not None:
        out.append(_target(src))
        out.append(RAW / "nyc_opendata" / src.local_name)
        out.append(RAW / "roads" / src.local_name)
    return out


def resolve(overrides: dict[str, Path] | None = None) -> RoadInputs:
    """Locate every input. Required ones raise ``FileNotFoundError``; optional ones are listed in ``missing``."""
    ri = RoadInputs()
    overrides = overrides or {}
    for sid in REQUIRED + OPTIONAL:
        p = overrides.get(sid)
        if p is None:
            for c in _candidates(sid):
                if c.exists() and c.stat().st_size > 0:
                    p = c
                    break
        if p is not None and Path(p).exists():
            ri.paths[sid] = Path(p)
        elif sid in REQUIRED:
            raise FileNotFoundError(f"required input {sid!r} not found (looked in {[str(c) for c in _candidates(sid)]}); run `python -m nycsim_pipeline.download --id {sid}`")
        else:
            ri.missing.append(sid)
    if ri.missing:
        log.warning("optional inputs missing: %s", ", ".join(ri.missing))
    return ri
