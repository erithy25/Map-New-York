# Holland Tunnel

Script: `blender/landmarks/b_holland_tunnel_portals.py` · agent B · generated 2026-09-06 13:22 UTC

## Placement

frame origin NYC_TM (-6063.5, 3019.0); both tube centrelines are the real OSM tunnel ways, extended to the published lengths.

## Published dimensions

* **North tube** (westbound, New York to New Jersey) 8,558 ft = **2,608.5 m**; **south tube** (eastbound)
  8,371 ft = **2,551.4 m**.  The build brief names 2,608 m for "the Holland tunnel", which is the north tube.
* Internal lining diameter 29 ft 6 in = **8.99 m**; roadway width 20 ft = **6.10 m**, two lanes per tube; vertical
  clearance 12 ft 6 in = 3.81 m; the roadway reaches **93 ft = 28.35 m below mean high water** at its lowest point
  [Wikipedia "Holland Tunnel", PANYNJ, HAER NJ-59].
* **Transverse ventilation** (Singstad's invention): fresh air is blown into a duct under the roadway and drawn out
  through a plenum above the ceiling, changing the air completely every 90 seconds; **four ventilation buildings**,
  two on each shore — a river tower and a land building on either side — with 84 fans.
* Interior finish: white glazed tile to 2.4 m over a dark base, a raised catwalk each side, and continuous luminaire
  rows.  This model places a **luminaire every 10 m** in each cove (the figure named in the build brief) and a
  recessed emergency door every 150 m, alternating sides.

Placement (all four ventilation buildings and both tube centrelines are real OSM geometry)
* North tube: OSM ways ``46613913`` + ``415877358``; south tube: ``22927390`` + ``415882710`` — all
  ``highway=motorway, tunnel=yes, name=Holland Tunnel``.  The chained OSM centrelines measure **2,613.0 m** and
  **2,550.7 m** against the published 2,608.5 m and 2,551.4 m — **+0.17 %** and **-0.03 %**; each is then trimmed or
  extended symmetrically along its end tangents to exactly the published length.
* Ventilation buildings, with the heights OSM records: ``249664800`` Manhattan river tower (39.3 m),
  ``249664802`` Manhattan land building (35.5 m), ``331072217`` New Jersey river tower (34.0 m, height not tagged —
  taken from its twin), ``320431782`` New Jersey land building (33.0 m, height not tagged).  Their real polygon
  footprints are used, not boxes.

## Not modelled

the fan rooms, ducts and dampers inside the ventilation buildings, the tiled wall's individual courses,
the overhead lane-control signals and jet fans, the police booths and the Manhattan and Jersey City approach plazas
and their ramp networks, and the cast-iron lining segment bolts.

## Polycounts / outputs

* `blender_out/landmarks/b_holland_tunnel_portals.glb` — 40,892 triangles, 1.87 MB, bounds min ['-1260.7', '-439.3', '-27.6'] max ['1281.9', '396.1', '42.9']
* `blender_out/landmarks/b_holland_tunnel_portals_lod1.glb` — 6,654 triangles, 0.42 MB, bounds min ['-1260.7', '-439.3', '-27.6'] max ['1281.9', '396.1', '42.9']
