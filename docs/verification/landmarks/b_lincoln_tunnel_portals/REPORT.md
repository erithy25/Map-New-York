# Lincoln Tunnel

Script: `blender/landmarks/b_lincoln_tunnel_portals.py` · agent B · generated 2026-09-06 14:09 UTC

## Placement

frame origin NYC_TM (-5049.0, 6874.5); three bores on real OSM centrelines.

## Published dimensions

* Three bores [Wikipedia "Lincoln Tunnel", PANYNJ]: **centre tube 8,216 ft = 2,504.2 m** (the length named in the
  build brief), **south tube 8,006 ft = 2,440.2 m**, **north tube 7,482 ft = 2,280.5 m**.
* Tube diameter 31 ft = **9.45 m**; roadway width 21.5 ft = **6.55 m**, two lanes per tube (six lanes in all);
  vertical clearance 13 ft = **3.96 m**; minimum elevation **-97 ft = -29.57 m** below the surface of the Hudson.
* Ventilation: transverse, with fresh air ducted below the roadway and exhaust drawn above the ceiling.  The Manhattan
  ventilation shaft is a **145 ft = 44.2 m** steel, brick and sandstone structure; two further ventilation buildings
  were added with the third tube.  Four ventilation buildings are modelled: two at each portal.
* Interior: white glazed tile to 2.4 m, catwalk each side, luminaires every **10 m** in each ceiling cove and a
  recessed emergency door every 150 m (alternating sides).

Placement: all three tube centrelines are real OSM ``highway=motorway, tunnel=yes, name=Lincoln Tunnel`` ways —
centre ``320663777`` + ``5669566`` + ``320888283``; north ``8028104`` + ``60325671`` + ``320888292``; south
``22701977`` + ``8028096`` + ``60325668``.  Each chained centreline is trimmed or extended symmetrically along its end
tangents to its published length; ``b_tunnel_lib`` logs the measured-versus-published difference for each bore and the
model's catalog entry records it under ``tube_stats``.  ``segments.parquet`` was not available.

**The four ventilation buildings are the one part of this model that is not measured.**  OSM maps no ventilation
building for the Lincoln Tunnel (the only ventilation shaft in the extract near the portals, way ``511023293``,
belongs to the Amtrak North River Tunnels), and no published coordinates were found.  They are therefore placed
symmetrically 70 m either side of each portal on the tunnel axis — a *derived* position, +-80 m — with the published
44.2 m height on the Manhattan pair and an inferred 34 m on the Weehawken pair.

## Not modelled

the fan rooms and dampers, the Lincoln Tunnel Expressway helix in Weehawken, the exclusive bus lane and
its gantries, the Dyer Avenue approach ramps and the Port Authority Bus Terminal connection, the lane-control signals,
and the individual tile courses.

## Polycounts / outputs

* `blender_out/landmarks/b_lincoln_tunnel_portals.glb` — 57,080 triangles, 2.55 MB, bounds min ['-1169.4', '-606.0', '-28.9'] max ['1180.3', '625.8', '54.6']
* `blender_out/landmarks/b_lincoln_tunnel_portals_lod1.glb` — 9,306 triangles, 0.55 MB, bounds min ['-1169.4', '-606.0', '-28.8'] max ['1180.3', '625.5', '54.6']
