"""Regenerate the pyproj ground truth embedded in core/tests/geo/test_geo.cpp.

Run:  python3 docs/verification/core/gen_geo.py            # prints the C++ tables
      python3 docs/verification/core/gen_geo.py --check    # diffs against the committed table

NYC_TM is the ADR-002 / DATA_CONTRACTS §1 CRS. sp_x/sp_y are EPSG:2263 (NY Long Island State
Plane, US survey feet) obtained as a *pure projection* from NAD83 geographic (EPSG:4269) so the
C++ LambertConformalConic (which does no datum shift) is comparable.
"""
from __future__ import annotations

import sys

from pyproj import CRS, Proj, Transformer

NYC_TM_PROJ4 = "+proj=tmerc +lat_0=40.7 +lon_0=-73.95 +k=1 +x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs"

POINTS = [
    ("Empire State Building, MN", 40.748440, -73.985664),
    ("One World Trade Center, MN", 40.712743, -74.013379),
    ("Statue of Liberty (Liberty Island), MN", 40.689247, -74.044502),
    ("Central Park Bethesda Terrace, MN", 40.774048, -73.970929),
    ("Inwood Hill Park north tip, MN", 40.874500, -73.925400),
    ("Roosevelt Island (near origin), MN", 40.760600, -73.950900),
    ("Columbia University Low Library, MN", 40.808000, -73.961900),
    ("Yankee Stadium, BX", 40.829643, -73.926175),
    ("Bronx Zoo, BX", 40.850600, -73.876000),
    ("City Island, BX", 40.847100, -73.786400),
    ("Woodlawn Cemetery, BX", 40.891700, -73.873000),
    ("Hunts Point Market, BX", 40.808500, -73.878400),
    ("Brooklyn Bridge (BK tower), BK", 40.704500, -73.994100),
    ("Prospect Park Grand Army Plaza, BK", 40.673800, -73.970100),
    ("Coney Island Wonder Wheel, BK", 40.573500, -73.978700),
    ("Barclays Center, BK", 40.682700, -73.975600),
    ("Canarsie Pier, BK", 40.626700, -73.885300),
    ("Flushing Meadows Unisphere, QN", 40.746100, -73.845000),
    ("JFK Terminal 4, QN", 40.644500, -73.782700),
    ("LaGuardia Terminal B, QN", 40.775000, -73.874200),
    ("Far Rockaway, QN", 40.605800, -73.755400),
    ("Astoria Park, QN", 40.778200, -73.923200),
    ("Jamaica Center, QN", 40.702200, -73.801100),
    ("St George Ferry Terminal, SI", 40.643700, -74.073600),
    ("Fort Wadsworth, SI", 40.605500, -74.055700),
    ("Great Kills Park, SI", 40.540400, -74.129900),
    ("Tottenville (Conference House), SI", 40.500300, -74.251500),
    ("Staten Island Mall, SI", 40.582300, -74.164000),
    ("Hoboken Terminal, NJ", 40.735100, -74.027500),
    ("George Washington Bridge (NJ tower), NJ", 40.851500, -73.958400),
]


def main() -> int:
    tm = Transformer.from_crs(CRS.from_epsg(4326), CRS.from_proj4(NYC_TM_PROJ4), always_xy=True)
    sp = Transformer.from_crs(CRS.from_epsg(4269), CRS.from_epsg(2263), always_xy=True)
    proj_tm = Proj(NYC_TM_PROJ4)
    rows = []
    for name, lat, lon in POINTS:
        x, y = tm.transform(lon, lat)
        sx, sy = sp.transform(lon, lat)
        rows.append(f'    {{"{name}", {lat:.6f}, {lon:.6f}, {x:.6f}, {y:.6f}, {sx:.6f}, {sy:.6f}}},')
    print("constexpr GroundTruth kPoints[] = {")
    print("\n".join(rows))
    print("};")
    print()
    print("constexpr FactorTruth kFactors[] = {")
    for _name, lat, lon in POINTS:
        f = proj_tm.get_factors(lon, lat)
        print(f"    {{{lat:.6f}, {lon:.6f}, {f.meridional_scale:.12f}, {f.meridian_convergence:.9f}}},")
    print("};")
    return 0


if __name__ == "__main__":
    sys.exit(main())
