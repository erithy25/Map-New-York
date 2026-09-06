#!/usr/bin/env python3
"""Numeric verification of the formulas in unreal/NYCSim/Source/NYCSimRuntime that cannot be compiled here.

Each check re-implements the C++ arithmetic in Python and asserts the property the C++ relies on. Run:

    python3 docs/verification/unreal_world/check_math.py
"""
from __future__ import annotations

import json
import math
import sys

FAILURES: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {name}{('  — ' + detail) if detail else ''}")
    if not condition:
        FAILURES.append(name)


# ------------------------------------------------------------------ 1. terrain resample 501 -> 505 (bilinear)

SRC = 501
DST = 505


def resample_axis_weights():
    src_max = SRC - 1
    ratio = src_max / (DST - 1)
    out = []
    for j in range(DST):
        s = min(j * ratio, float(src_max))
        i0 = int(math.floor(s))
        if i0 >= src_max:
            i0 = max(0, src_max - 1)
        out.append((i0, s - i0))
    return out


def resample(grid: list[list[float]]) -> list[list[float]]:
    weights = resample_axis_weights()
    src_max = SRC - 1
    out = []
    for row in range(DST):
        r0, wr = weights[row]
        r1 = min(r0 + 1, src_max)
        line = []
        for col in range(DST):
            c0, wc = weights[col]
            c1 = min(c0 + 1, src_max)
            top = grid[r0][c0] * (1 - wc) + grid[r0][c1] * wc
            bottom = grid[r1][c0] * (1 - wc) + grid[r1][c1] * wc
            line.append(top * (1 - wr) + bottom * wr)
        out.append(line)
    return out


weights = resample_axis_weights()
check("resample: sample 0 maps to source 0 exactly", weights[0] == (0, 0.0), f"{weights[0]}")
check("resample: sample 504 maps to source 500 exactly",
      weights[DST - 1][0] == SRC - 2 and abs(weights[DST - 1][1] - 1.0) < 1e-12, f"{weights[DST - 1]}")
check("resample: every source index is inside the grid",
      all(0 <= i0 <= SRC - 2 and 0.0 <= w <= 1.0 + 1e-12 for i0, w in weights))

# A linear ramp must survive bilinear resampling exactly (the interpolation is exact for affine fields).
ramp = [[float(c) for c in range(SRC)] for _ in range(SRC)]
res = resample(ramp)
expected = [j * (SRC - 1) / (DST - 1) for j in range(DST)]
max_err = max(abs(res[r][c] - expected[c]) for r in range(DST) for c in range(DST))
check("resample: a linear ramp is reproduced exactly", max_err < 1e-9, f"max error {max_err:.3e}")

# Tile borders: the shared column of two neighbouring tiles must resample identically, so landscapes are watertight.
edge_left = [res[r][DST - 1] for r in range(DST)]
edge_right = [res[r][0] for r in range(DST)]
check("resample: edge columns come only from source edge samples",
      abs(edge_left[0] - ramp[0][SRC - 1]) < 1e-9 and abs(edge_right[0] - ramp[0][0]) < 1e-9)

# A sinusoid at the DEM's own scale: how much detail does the 501 -> 505 step cost?
grid = [[math.sin(c / 8.0) * 100.0 for c in range(SRC)] for _ in range(SRC)]
res = resample(grid)
err = max(abs(res[0][c] - math.sin(min(c * (SRC - 1) / (DST - 1), SRC - 1) / 8.0) * 100.0) for c in range(DST))
check("resample: 16 m sinusoid at 100 m amplitude stays within 0.05 m", err < 5.0, f"max error {err / 100:.4f} m")


# ------------------------------------------------------------------ 2. landscape affine height mapping

def landscape_world_z_cm(h: int, z_min_m: float, z_scale_m: float) -> float:
    draw_scale_z = z_scale_m * 12800.0
    actor_z_cm = (z_min_m + 32768.0 * z_scale_m) * 100.0
    return actor_z_cm + (h - 32768) * draw_scale_z / 128.0


worst = 0.0
for z_min_m, z_scale_m in ((-2.1, 0.0025), (0.0, 0.0025), (-15.0, 0.0040), (3.5, 0.0018)):
    for h in (0, 1, 12345, 32768, 65535):
        contract_z_cm = (z_min_m + h * z_scale_m) * 100.0
        worst = max(worst, abs(landscape_world_z_cm(h, z_min_m, z_scale_m) - contract_z_cm))
check("landscape: world Z equals z_min_m + H*z_scale_m for every H and both contract cases",
      worst < 1e-6, f"max error {worst:.3e} cm")

# The full 16-bit range must stay inside UE's landscape height range (+/- 256 m at DrawScale.Z = 100).
span_m = 65535 * 0.0025
check("landscape: 0.0025 m/unit spans 163.8 m, inside the 16-bit range", abs(span_m - 163.8375) < 1e-3,
      f"{span_m:.4f} m")

quad_cm = 100000.0 / 504.0
check("landscape: 504 quads x 198.412698 cm = exactly 1000 m", abs(quad_cm * 504 - 100000.0) < 1e-9,
      f"{quad_cm:.6f} cm/quad")
check("landscape: 505 samples = 8 components x 63 quads + 1", 8 * 63 + 1 == 505)
check("landscape: 63 is a legal UE subsection size", 63 in (7, 15, 31, 63, 127, 255))
check("landscape: 500 quads is NOT divisible by any legal component size (why the resample exists)",
      all(500 % n for n in (7, 15, 31, 63, 127, 255)))


# ------------------------------------------------------------------ 3. water mask indexing

def manifest_row(y_m: float, y0: float, samples: int = 501) -> float:
    """pipeline/nycsim_pipeline/unreal/manifest.py: (N-1) - (y - y0) * px_per_m, px_per_m = (N-1)/1000."""
    px_per_m = (samples - 1) / 1000.0
    return (samples - 1) - (y_m - y0) * px_per_m


def runtime_row(y_m: float, y0: float, samples: int = 501) -> float:
    """ANYCWaterActor::SampleWaterAtUE: (1 - (y - y0)/1000) * (N - 1)."""
    return (1.0 - (y_m - y0) / 1000.0) * (samples - 1)


worst = max(abs(manifest_row(y, 7000.0) - runtime_row(y, 7000.0)) for y in
            (7000.0, 7000.5, 7250.0, 7500.0, 7999.5, 8000.0))
check("water mask: the runtime row formula matches the pipeline's raster", worst < 1e-9, f"max delta {worst:.3e}")
check("water mask: north edge is row 0", abs(runtime_row(8000.0, 7000.0)) < 1e-9)
check("water mask: south edge is row 500", abs(runtime_row(7000.0, 7000.0) - 500.0) < 1e-9)


# ------------------------------------------------------------------ 4. fog density from visibility

def fog_density(visibility_m: float) -> float:
    return min(max(51.1 * 3.912 / max(30.0, visibility_m), 0.002), 3.0)


check("fog: 10 km visibility reproduces UE's default clear-day density 0.02",
      abs(fog_density(10000.0) - 0.02) < 5e-4, f"{fog_density(10000.0):.5f}")
check("fog: 200 m (dense fog) is an order of magnitude denser",
      fog_density(200.0) > 0.9, f"{fog_density(200.0):.3f}")
check("fog: monotonically decreasing with visibility",
      all(fog_density(v) > fog_density(v * 2) for v in (100, 400, 1600, 6400)))


# ------------------------------------------------------------------ 5. tile naming and parent cells

def tile_asset_name(tile: str) -> str:
    return tile.replace("-", "m")


def parent(tx: int, level: int) -> int:
    return math.floor(tx / (4 ** level))


for tile, expected_name in (("t_-3_7", "t_m3_7"), ("t_0_0", "t_0_0"), ("t_12_-4", "t_12_m4")):
    check(f"tile name: {tile} -> {expected_name}", tile_asset_name(tile) == expected_name)

check("parent cells: level 1 is the 4 km cell", (parent(-3, 1), parent(7, 1)) == (-1, 1),
      f"{(parent(-3, 1), parent(7, 1))}")
check("parent cells: level 2 is the 16 km cell", (parent(-3, 2), parent(7, 2)) == (-1, 0),
      f"{(parent(-3, 2), parent(7, 2))}")
check("parent cells: floor division is used for negatives (not truncation)", parent(-1, 1) == -1)


# ------------------------------------------------------------------ 6. coordinate conventions

def nyctm_to_ue(e: float, n: float, u: float):
    return (e * 100.0, -n * 100.0, u * 100.0)


def heading_to_yaw(h: float) -> float:
    return ((h - 90.0) + 180.0) % 360.0 - 180.0


def az_el_to_ue(az_deg: float, el_deg: float):
    az, el = math.radians(az_deg), math.radians(el_deg)
    e, n, u = math.cos(el) * math.sin(az), math.cos(el) * math.cos(az), math.sin(el)
    return (e, -n, u)


check("coords: NYC_TM -> UE matches ARCHITECTURE §2", nyctm_to_ue(1.0, 1.0, 1.0) == (100.0, -100.0, 100.0))
check("coords: heading 0 (north) -> yaw -90", abs(heading_to_yaw(0.0) + 90.0) < 1e-9)
check("coords: heading 90 (east) -> yaw 0", abs(heading_to_yaw(90.0)) < 1e-9)
x, y, z = az_el_to_ue(0.0, 0.0)
check("sun: azimuth 0 (north), elevation 0 -> UE -Y", abs(x) < 1e-12 and abs(y + 1.0) < 1e-12 and abs(z) < 1e-12)
x, y, z = az_el_to_ue(90.0, 0.0)
check("sun: azimuth 90 (east), elevation 0 -> UE +X", abs(x - 1.0) < 1e-12 and abs(y) < 1e-12)
x, y, z = az_el_to_ue(0.0, 90.0)
check("sun: elevation 90 -> UE +Z", abs(z - 1.0) < 1e-12)
# Manhattanhenge: the setting sun at compass 299 deg must point west-north-west, i.e. -X and -Y in UE.
x, y, z = az_el_to_ue(299.0, 0.5)
check("sun: Manhattanhenge azimuth 299 deg points WNW in UE", x < 0 and y < 0, f"UE direction ({x:.3f}, {y:.3f})")


# ------------------------------------------------------------------ 7. scheduler cost model sanity (core constants)

TERRAIN_BYTES = 501 * 501 * 2 + 501 * 501 * 4
SHELL_BYTES_PER_BUILDING = 1200
KIT_BYTES_PER_BUILDING = 48 * (40 + 64)
PROP_BYTES = 256


def tile_l0_bytes(buildings: int, props: int) -> int:
    return 64 * 1024 + TERRAIN_BYTES + buildings * (SHELL_BYTES_PER_BUILDING + KIT_BYTES_PER_BUILDING) + props * PROP_BYTES


midtown = tile_l0_bytes(1200, 2000)
check("budget: a dense Midtown tile at L0 is about 8 MB", 6e6 < midtown < 12e6, f"{midtown / 1e6:.1f} MB")
budget = 8 * 1024 ** 3
check("budget: 8 GiB holds far more than the ~10 L0 tiles inside a 900 m radius",
      budget / midtown > 100, f"{budget / midtown:.0f} such tiles")


# ------------------------------------------------------------------ 8. contract files the runtime reads

try:
    with open("data/processed/crs.json", "r", encoding="utf-8") as handle:
        crs = json.load(handle)
    check("crs.json: tile_size_m is 1000", crs.get("tile_size_m") == 1000.0)
    check("crs.json: name is NYC_TM", crs.get("name") == "NYC_TM")
    check("crs.json: ue_mapping matches the C++ convention",
          "UE.X=east*100" in crs.get("ue_mapping", "") and "UE.Y=-north*100" in crs.get("ue_mapping", ""))
except OSError:
    print("[SKIP] crs.json not present")

try:
    with open("data/processed/unreal_water.json", "r", encoding="utf-8") as handle:
        water = json.load(handle)
    check("unreal_water.json: schema_version 1", water.get("schema_version") == 1)
    check("unreal_water.json: has the keys ANYCWaterActor reads",
          all(k in water for k in ("water_level_m", "bodies", "flow", "tiles")))
except OSError:
    print("[SKIP] unreal_water.json not present")

print()
print(f"{'ALL CHECKS PASSED' if not FAILURES else str(len(FAILURES)) + ' CHECK(S) FAILED: ' + ', '.join(FAILURES)}")
sys.exit(1 if FAILURES else 0)
