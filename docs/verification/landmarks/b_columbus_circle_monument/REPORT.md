# Columbus Circle Monument and Deutsche Bank Center

Script: `blender/landmarks/b_columbus_circle_monument.py` · agent B · generated 2026-09-06 13:39 UTC

## Published dimensions

* **Columbus Monument** (Gaetano Russo, unveiled 13 October 1892, the 400th anniversary of the landfall): a
  **70 ft = 21.34 m** granite rostral column carrying a **14 ft = 4.27 m** marble figure of Columbus, giving an
  overall **76 ft = 23.16 m** from the plaza; the shaft is decorated with three bronze **prows of ships** (rostra)
  and the pedestal carries a bronze relief of the Nina, Pinta and Santa Maria and a winged genius.  The point from
  which all official distances to New York City are measured [NYC Parks, Wikipedia "Columbus Monument
  (Manhattan)"].
* **Columbus Circle** itself is the real OSM way ``109269254`` (``tourism=attraction``), **65 x 65 m**; the 2005
  reconstruction laid out the fountain rings and benches around the monument.
* **Deutsche Bank Center** (David Childs / SOM, opened 2004 as the Time Warner Center): **twin towers of 750 ft =
  228.60 m**, 55 storeys, on a curved podium that follows the circle; the real OTI footprint (BIN **1026318**,
  23,629 m2, LiDAR roof **217.9 m** over ground 25.6 m NAVD88) and the real OSM polygon (way ``167923911``, tagged
  height 45 m for the podium) are both used — the podium on the footprint, the two towers as 44 x 44 m shafts
  (*inferred* plan) rising to the published 228.60 m.
  The 10.7 m difference between the published 750 ft and the LiDAR 217.9 m is the towers' glass crowns, which the
  LiDAR return misses; the published figure is used and the difference stated.

## Placement

the monument on OSM way 109269254's centroid, the Deutsche Bank Center on OTI BIN 1026318.

## Not modelled

Russo's Columbus figure and the pedestal reliefs (blocked out), the rostra beyond three bronze prow
blocks, the 2005 fountain jets and their basins, the Maine Monument at the north-west of the circle (a separate
memorial), the Deutsche Bank Center's atrium and its curtain-wall mullions, and the subway entrances.

## Polycounts / outputs

* `blender_out/landmarks/b_columbus_circle_monument.glb` — 2,856 triangles, 0.18 MB, bounds min ['-176.0', '-55.1', '-6.0'] max ['32.5', '129.8', '234.6']
* `blender_out/landmarks/b_columbus_circle_monument_lod1.glb` — 1,200 triangles, 0.09 MB, bounds min ['-176.0', '-55.1', '-6.0'] max ['32.5', '129.8', '234.6']
