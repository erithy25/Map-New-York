#!/usr/bin/env python3
"""Checks UNYCTerrainImporter's assumptions against the pipeline's real per-tile heightmaps.

    python3 docs/verification/unreal_world/check_terrain_data.py [--tiles N]

Verified on real data (not on synthetic input):
  * every terrain.png is 501 x 501 and 16-bit grayscale, every terrain.json is schema 1 with samples = 501
  * the landscape affine mapping (DrawScale.Z = z_scale_m*12800, ActorZ = (z_min_m + 32768*z_scale_m)*100)
    reproduces the contract elevation z = z_min_m + H*z_scale_m for H = 0 and H = 65535
  * neighbouring tiles carry identical elevations on their shared edge column, which is what makes the
    501 -> 505 resample watertight (the resample's edge samples come only from those columns)
  * the 501 -> 505 bilinear resample leaves the tile corners exactly where they were
"""
from __future__ import annotations

import argparse
import json
import math
import os
import random
import sys

import numpy as np
from PIL import Image

TILES = os.path.join("data", "processed", "tiles")
FAILURES: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"[{'PASS' if ok else 'FAIL'}] {name}{('  — ' + detail) if detail else ''}")
    if not ok:
        FAILURES.append(name)


def parse_tile(name: str) -> tuple[int, int]:
    body = name[2:]
    split = body.find("_", 1)
    return int(body[:split]), int(body[split + 1:])


def load(tile: str):
    array = np.asarray(Image.open(os.path.join(TILES, tile, "terrain.png")), dtype=np.uint16)
    meta = json.load(open(os.path.join(TILES, tile, "terrain.json"), encoding="utf-8"))
    return array, meta


def resample(src: np.ndarray, source_samples: int = 501, dst_samples: int = 505) -> np.ndarray:
    ratio = (source_samples - 1) / (dst_samples - 1)
    idx, weight = [], []
    for j in range(dst_samples):
        s = min(j * ratio, float(source_samples - 1))
        i0 = int(math.floor(s))
        if i0 >= source_samples - 1:
            i0 = source_samples - 2
        idx.append(i0)
        weight.append(s - i0)
    idx_a = np.array(idx)
    w = np.array(weight)
    nxt = np.minimum(idx_a + 1, source_samples - 1)
    rows = src[idx_a, :] * (1 - w)[:, None] + src[nxt, :] * w[:, None]
    return rows[:, idx_a] * (1 - w)[None, :] + rows[:, nxt] * w[None, :]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tiles", type=int, default=40, help="how many tiles to sample")
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args(argv)

    if not os.path.isdir(TILES):
        print("[SKIP] data/processed/tiles is not present")
        return 0
    names = sorted(n for n in os.listdir(TILES) if os.path.isfile(os.path.join(TILES, n, "terrain.png")))
    print(f"{len(names)} tiles carry terrain.png")
    if not names:
        print("[SKIP] no heightmaps yet")
        return 0
    random.seed(args.seed)
    sample = random.sample(names, min(args.tiles, len(names)))

    bad_size = bad_mode = bad_schema = 0
    scales, zmins, zmaxs = set(), [], []
    for tile in sample:
        image = Image.open(os.path.join(TILES, tile, "terrain.png"))
        bad_size += image.size != (501, 501)
        bad_mode += image.mode != "I;16"
        meta = json.load(open(os.path.join(TILES, tile, "terrain.json"), encoding="utf-8"))
        bad_schema += meta.get("schema_version") != 1 or meta.get("samples") != 501
        scales.add(round(float(meta["z_scale_m"]), 9))
        array = np.asarray(image, dtype=np.uint16).astype(np.float64)
        z = meta["z_min_m"] + array * meta["z_scale_m"]
        zmins.append(float(z.min()))
        zmaxs.append(float(z.max()))

    check(f"{len(sample)} sampled terrain.png are 501 x 501", bad_size == 0, f"{bad_size} wrong")
    check(f"{len(sample)} sampled terrain.png are 16-bit grayscale (PIL mode I;16)", bad_mode == 0, f"{bad_mode} wrong")
    check("terrain.json schema_version 1 and samples 501", bad_schema == 0, f"{bad_schema} wrong")
    check("z_scale_m is uniform across the sample", len(scales) == 1, f"{sorted(scales)}")
    print(f"       elevation range over the sample: {min(zmins):.2f} .. {max(zmaxs):.2f} m NAVD88")

    worst = 0.0
    for tile in sample:
        meta = json.load(open(os.path.join(TILES, tile, "terrain.json"), encoding="utf-8"))
        z_scale, z_min = meta["z_scale_m"], meta["z_min_m"]
        actor_z = (z_min + 32768.0 * z_scale) * 100.0
        for h in (0, 32768, 65535):
            world = actor_z + (h - 32768) * (z_scale * 12800.0) / 128.0
            worst = max(worst, abs(world - (z_min + h * z_scale) * 100.0))
    check("landscape affine mapping reproduces the contract elevation on real metadata", worst < 1e-6,
          f"max error {worst:.3e} cm")

    pairs = mismatch = 0
    max_dz = 0.0
    for tile in sample:
        tx, ty = parse_tile(tile)
        for neighbour, take_a, take_b in ((f"t_{tx + 1}_{ty}", (slice(None), -1), (slice(None), 0)),
                                          (f"t_{tx}_{ty + 1}", (0, slice(None)), (-1, slice(None)))):
            if neighbour not in names:
                continue
            a, ma = load(tile)
            b, mb = load(neighbour)
            za = ma["z_min_m"] + a[take_a].astype(np.float64) * ma["z_scale_m"]
            zb = mb["z_min_m"] + b[take_b].astype(np.float64) * mb["z_scale_m"]
            delta = float(np.abs(za - zb).max())
            max_dz = max(max_dz, delta)
            pairs += 1
            mismatch += delta > 1e-6
    check("neighbouring tiles share their edge elevations (landscapes are watertight)", mismatch == 0,
          f"{pairs} shared edges checked, {mismatch} differ, max |dz| = {max_dz:.6f} m")

    worst_corner = 0.0
    for tile in sample[:12]:
        array, meta = load(tile)
        src = array.astype(np.float64)
        out = resample(src)
        corner = max(abs(out[0, 0] - src[0, 0]), abs(out[0, -1] - src[0, -1]),
                     abs(out[-1, 0] - src[-1, 0]), abs(out[-1, -1] - src[-1, -1]))
        worst_corner = max(worst_corner, corner * meta["z_scale_m"])
    check("501 -> 505 resample leaves the tile corners exactly where they were", worst_corner < 1e-9,
          f"max corner error {worst_corner:.9f} m")

    print()
    print("ALL CHECKS PASSED" if not FAILURES else f"{len(FAILURES)} CHECK(S) FAILED: {', '.join(FAILURES)}")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
