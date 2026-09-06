"""Derive the street-tree size classes used by the vegetation props from the 2015 Street Tree Census.

The ten species built by ``p_vegetation.py`` are the ten commonest *identified* species among living trees in
``data/raw/nyc_opendata/street_trees_2015.csv`` (the genus-only bucket ``Prunus`` is excluded: it is not a species).
For each species three DBH classes are taken from the census distribution of living trees of that species —
the 25th, 50th and 90th percentile of the measured trunk diameter — and the corresponding trunk height comes from
``pipeline.nycsim_pipeline.furniture.allometry`` (the same curve the props table uses, ``height_source = 1``).

Run:  python3 blender/props/census_dbh.py   ->  blender/props/dbh_classes.json
"""
from __future__ import annotations

import json
import logging
import math
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "pipeline"))
CENSUS = REPO / "data" / "raw" / "nyc_opendata" / "street_trees_2015.csv"
OUT = Path(__file__).resolve().parent / "dbh_classes.json"

log = logging.getLogger("nycsim.props.census")

# Latin name -> the census `spc_common` label, kept so the catalog entry carries the census vocabulary.
N_SPECIES = 10
CLASS_PERCENTILES = (25.0, 50.0, 90.0)
CLASS_NAMES = ("small", "medium", "large")


def build() -> dict:
    import numpy as np
    import pandas as pd
    from nycsim_pipeline.furniture import allometry

    if not CENSUS.exists():
        raise FileNotFoundError(f"street tree census missing: {CENSUS}")
    df = pd.read_csv(CENSUS, usecols=["tree_dbh", "status", "spc_latin", "spc_common"],
                     dtype={"status": "string", "spc_latin": "string", "spc_common": "string"})
    alive = df[df["status"].eq("Alive")]
    counts = alive["spc_latin"].value_counts()
    species = [s for s in counts.index if isinstance(s, str) and len(s.split()) > 1][:N_SPECIES]
    out = {"schema_version": 1, "source": "data/raw/nyc_opendata/street_trees_2015.csv",
           "source_dataset_id": "street_trees_2015", "alive_trees": int(len(alive)),
           "class_percentiles": list(CLASS_PERCENTILES), "class_names": list(CLASS_NAMES),
           "height_model": "nycsim_pipeline.furniture.allometry.height_m (height_source=1)", "species": []}
    for latin in species:
        sel = alive["spc_latin"].eq(latin)
        common = alive.loc[sel, "spc_common"].dropna()
        dbh_in = alive.loc[sel, "tree_dbh"].astype(float)
        dbh_cm = (dbh_in[(dbh_in > 0) & (dbh_in < 200)] * 2.54).to_numpy()
        q = np.percentile(dbh_cm, CLASS_PERCENTILES)
        hmax, k = allometry.params_for(latin)
        classes = []
        for name, d in zip(CLASS_NAMES, q):
            d = round(float(d), 1)
            h = allometry.height_m(latin, d)
            classes.append({"class": name, "dbh_cm": d, "height_m": round(h, 2),
                            "crown_m": round(h * (1.0 if hmax <= 10.0 else 0.6), 2)})
        out["species"].append({
            "latin": latin, "common": (common.mode().iat[0] if len(common) else latin),
            "census_count": int(counts[latin]), "dbh_cm_mean": round(float(dbh_cm.mean()), 1),
            "h_max_m": hmax, "allometry_k": k, "classes": classes})
    return out


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    doc = build()
    OUT.write_text(json.dumps(doc, indent=1) + "\n")
    for s in doc["species"]:
        log.info("%-38s n=%6d  %s", s["latin"], s["census_count"],
                 "  ".join(f"{c['class']}: {c['dbh_cm']:5.1f} cm / {c['height_m']:5.2f} m" for c in s["classes"]))
    log.info("wrote %s (%d species)", OUT, len(doc["species"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
