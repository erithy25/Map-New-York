# Hugh L. Carey Tunnel

Script: `blender/landmarks/b_hugh_carey_portals.py` · agent B · generated 2026-09-06 12:31 UTC

## Placement

frame origin NYC_TM (-5105.0, -714.5); both bores on real OSM centrelines; three of the four ventilation buildings on their real OSM footprints.

## Published dimensions

* Length **9,117 ft = 2,779.2 m** (the length named in the build brief); **4 lanes** in two bores; vertical
  clearance 12 ft 1 in = **3.68 m**; vehicles wider than 8 ft 6 in are prohibited [Wikipedia "Hugh L. Carey Tunnel",
  MTA Bridges & Tunnels].
* **Four ventilation buildings: two in Manhattan, one in Brooklyn and one on Governors Island** — the Governors
  Island one, mid-river, is the tunnel's signature structure.  Three of the four are real OSM buildings with tagged
  heights and are built on their real polygon footprints: ``278396317`` Governors Island (32.8 m), ``278053475``
  Battery/Manhattan (26.2 m) and ``278370550`` Brooklyn (20.4 m).  **The second Manhattan building is not mapped in
  OSM and is not modelled** (stated gap).
* Tube diameter is **not published** for this tunnel; 31 ft = **9.45 m** is used, the figure published for its
  contemporaries the Lincoln and Queens-Midtown tunnels by the same engineer (*inferred*).  Roadway width 6.55 m is
  inferred the same way.
* The roadway's low point is **not published**; it is modelled 30.0 m below mean high water (*inferred*, +-4 m).
* Interior: white glazed tile to 2.4 m, raised catwalk each side, a **luminaire every 10 m** in each ceiling cove and
  a recessed emergency door every 150 m, alternating sides.

Placement: both tube centrelines are real OSM ``highway=motorway, tunnel=yes, name=Brooklyn-Battery Tunnel`` ways —
``5681925`` (Manhattan to Brooklyn, 61 vertices) and ``413749473`` (Brooklyn to Manhattan, 54 vertices).  Each is
trimmed or extended symmetrically along its end tangents to the published 2,779.2 m; the measured-versus-published
difference is logged and recorded in the catalog entry under ``tube_stats``.  ``segments.parquet`` was not available.

## Not modelled

the second Manhattan ventilation building (unmapped), the fan rooms and dampers, the Battery Park
approach and its 1950s ramps over the Battery, the Gowanus Expressway connection, the lane-control signals, and the
individual tile courses.

## Polycounts / outputs

* `blender_out/landmarks/b_hugh_carey_portals.glb` — 43,880 triangles, 2.04 MB, bounds min ['-461.1', '-1337.3', '-29.3'] max ['430.4', '1335.3', '41.2']
