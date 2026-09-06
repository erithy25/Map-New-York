"""``python -m nycsim_pipeline <stage>`` dispatcher."""
from __future__ import annotations
import importlib
import sys

STAGES = {
    "download": "nycsim_pipeline.download",
    "terrain": "nycsim_pipeline.terrain.build",
    "water": "nycsim_pipeline.water.build",
    "roads": "nycsim_pipeline.roads.build",
    "buildings": "nycsim_pipeline.buildings.build",
    "facade": "nycsim_pipeline.facade.build",
    "citygml": "nycsim_pipeline.buildings.citygml",
    "furniture": "nycsim_pipeline.furniture.build",
    "transit": "nycsim_pipeline.transit.build",
    "osm": "nycsim_pipeline.osm.extract",
    "traffic": "nycsim_pipeline.traffic.build",
    "tiles": "nycsim_pipeline.tiles.index",
    "report": "nycsim_pipeline.report.fidelity",
}


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] not in STAGES:
        print("usage: python -m nycsim_pipeline <stage> [args]\nstages: " + ", ".join(STAGES))
        return 2
    mod = importlib.import_module(STAGES[sys.argv[1]])
    return int(mod.main(sys.argv[2:]) or 0)


if __name__ == "__main__":
    sys.exit(main())
