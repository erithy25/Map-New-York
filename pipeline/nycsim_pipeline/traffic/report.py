"""Figures and tables for ``docs/verification/traffic_density/``.

    python -m nycsim_pipeline.traffic.report

Reads ``data/processed/traffic/density.parquet`` (+ the detail file and the build summary) and the
NTA polygons, and writes

* ``density_08.png`` / ``density_22.png`` — weekday vehicle density choropleths at 08:00 and 22:00
* ``pedestrians_13.png``                  — weekday pedestrian density at 13:00
* ``profiles.png``                        — the diurnal curves the model produces per borough
* ``tables.md``                           — the top/bottom NTA tables quoted in REPORT.md
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import polars as pl  # noqa: E402
import shapely  # noqa: E402
from matplotlib.collections import PolyCollection  # noqa: E402
from matplotlib.colors import LogNorm, Normalize  # noqa: E402

from ..paths import PROCESSED, VERIFICATION  # noqa: E402
from .geo import BOROUGH_NAMES, load_ntas  # noqa: E402

log = logging.getLogger("nycsim.traffic.report")

OUT_DIR = VERIFICATION / "traffic_density"
DENSITY_PATH = PROCESSED / "traffic" / "density.parquet"
DETAIL_PATH = PROCESSED / "traffic" / "density_detail.parquet"
SUMMARY_PATH = PROCESSED / "traffic" / "build_summary.json"


def _polys(nta) -> tuple[list[np.ndarray], list[int]]:
    verts: list[np.ndarray] = []
    owner: list[int] = []
    for i, g in enumerate(nta.geoms):
        parts = shapely.get_parts(g) if g.geom_type.startswith("Multi") else [g]
        for p in parts:
            if p.is_empty or p.area < 1000.0:
                continue
            verts.append(np.asarray(shapely.get_coordinates(shapely.get_exterior_ring(p))))
            owner.append(i)
    return verts, owner


def choropleth(nta, values: np.ndarray, title: str, subtitle: str, path: Path, *, unit: str,
               log_scale: bool = False, cmap: str = "inferno") -> Path:
    verts, owner = _polys(nta)
    v = np.asarray(values, dtype=np.float64)[owner]
    fig, ax = plt.subplots(figsize=(9.5, 10.5), dpi=140)
    finite = v[np.isfinite(v) & (v > 0)]
    if log_scale and len(finite):
        norm = LogNorm(vmin=max(finite.min(), np.percentile(finite, 2)), vmax=finite.max())
        v = np.where(v > 0, v, np.nan)
    else:
        norm = Normalize(vmin=0.0, vmax=float(np.nanpercentile(values, 99)) or 1.0)
    pc = PolyCollection(verts, array=v, cmap=cmap, norm=norm, edgecolors="#3a3a3a", linewidths=0.25)
    ax.add_collection(pc)
    allv = np.concatenate(verts)
    ax.set_xlim(allv[:, 0].min() - 500, allv[:, 0].max() + 500)
    ax.set_ylim(allv[:, 1].min() - 500, allv[:, 1].max() + 500)
    ax.set_aspect("equal")
    ax.set_facecolor("#101014")
    ax.set_xticks([])
    ax.set_yticks([])
    for s in ax.spines.values():
        s.set_visible(False)
    cb = fig.colorbar(pc, ax=ax, fraction=0.035, pad=0.01)
    cb.set_label(unit)
    ax.set_title(f"{title}\n{subtitle}", fontsize=12)
    # a 5 km scale bar
    x0, y0 = allv[:, 0].min() + 800, allv[:, 1].min() + 900
    ax.plot([x0, x0 + 5000], [y0, y0], color="w", lw=2)
    ax.text(x0 + 2500, y0 + 350, "5 km", color="w", ha="center", fontsize=9)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, facecolor="white")
    plt.close(fig)
    log.info("wrote %s (%d kB)", path, path.stat().st_size // 1024)
    return path


def profile_figure(detail: pl.DataFrame, path: Path) -> Path:
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.2), dpi=140, sharey=True)
    day_names = ["weekday", "Saturday", "Sunday"]
    for d, ax in enumerate(axes):
        for b, name in BOROUGH_NAMES.items():
            sub = (detail.filter((pl.col("dow") == d) & (pl.col("borough") == b) & (pl.col("lane_km") > 0))
                   .group_by("hour")
                   .agg(((pl.col("veh_per_km_lane") * pl.col("lane_km")).sum() / pl.col("lane_km").sum())
                        .alias("k"))
                   .sort("hour"))
            ax.plot(sub["hour"].to_numpy(), sub["k"].to_numpy(), label=name, lw=1.8)
        ax.set_title(day_names[d])
        ax.set_xlabel("hour")
        ax.set_xlim(0, 23)
        ax.grid(alpha=0.25)
    axes[0].set_ylabel("veh / km / lane (lane-km weighted)")
    axes[2].legend(fontsize=8, frameon=False)
    fig.suptitle("Modelled vehicle density by borough and hour", fontsize=12)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, facecolor="white")
    plt.close(fig)
    log.info("wrote %s (%d kB)", path, path.stat().st_size // 1024)
    return path


def _table(rows: list[dict], header: str, unit: str) -> str:
    out = [f"### {header}", "", f"| NTA | name | borough | {unit} |", "|---|---|---|---|"]
    for r in rows:
        out.append(f"| {r['nta']} | {r['name']} | {BOROUGH_NAMES.get(int(r['borough']), '?')} | {r['value']:.3f} |")
    out.append("")
    return "\n".join(out)


def write_tables(summary: dict, path: Path) -> Path:
    parts = ["# Traffic density — ranked tables", "",
             "Generated by `python -m nycsim_pipeline.traffic.report`.", ""]
    parts.append(_table(summary["density"]["weekday_17h"]["top"],
                        "Highest vehicle density, weekday 17:00", "veh/km/lane"))
    parts.append(_table(summary["density"]["weekday_17h"]["bottom"],
                        "Lowest vehicle density, weekday 17:00", "veh/km/lane"))
    parts.append(_table(summary["pedestrians"]["weekday_13h"]["top"],
                        "Highest pedestrian density, weekday 13:00", "ped/m² sidewalk"))
    parts.append(_table(summary["pedestrians"]["weekday_13h"]["bottom"],
                        "Lowest pedestrian density, weekday 13:00", "ped/m² sidewalk"))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(parts))
    log.info("wrote %s", path)
    return path


def run(out_dir: Path = OUT_DIR) -> list[Path]:
    for p in (DENSITY_PATH, DETAIL_PATH, SUMMARY_PATH):
        if not p.exists():
            raise FileNotFoundError(f"{p} missing — run `python -m nycsim_pipeline.traffic.build` first")
    nta = load_ntas()
    density = pl.read_parquet(DENSITY_PATH)
    detail = pl.read_parquet(DETAIL_PATH)
    summary = json.loads(SUMMARY_PATH.read_text())
    order = {c: i for i, c in enumerate(nta.codes)}

    def grab(df: pl.DataFrame, col: str, hour: int, dow: int = 0) -> np.ndarray:
        sub = df.filter((pl.col("hour") == hour) & (pl.col("dow") == dow))
        v = np.zeros(len(nta))
        for code, val in zip(sub["nta_code"].to_list(), sub[col].to_list()):
            v[order[code]] = val
        return v

    written = []
    for hour in (8, 22):
        written.append(choropleth(
            nta, grab(density, "veh_per_km_lane", hour),
            f"NYC vehicle density — weekday {hour:02d}:00",
            "vehicles per km of travel lane, 2020 NTAs (DOT ATR counts + CSCL + PLUTO + TLC speeds)",
            out_dir / f"density_{hour:02d}.png", unit="veh / km / lane"))
    written.append(choropleth(
        nta, grab(density, "ped_per_m2_sidewalk", 13),
        "NYC pedestrian density — weekday 13:00",
        "pedestrians per m² of walkable sidewalk (DOT bi-annual counts + PLUTO generators)",
        out_dir / "pedestrians_13.png", unit="ped / m²", cmap="viridis"))
    written.append(profile_figure(detail, out_dir / "profiles.png"))
    written.append(write_tables(summary, out_dir / "tables.md"))
    return written


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT_DIR)
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    for p in run(a.out):
        print(p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
