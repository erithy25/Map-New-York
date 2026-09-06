# Kosciuszko Bridge

Script: `blender/landmarks/b_kosciuszko.py` · agent B · generated 2026-09-06 14:18 UTC

## Placement

origin NYC_TM (1730.0, 3070.0), heading 42.10 deg from the two OSM BQE deck ways; the two structures are offset +-15.34 m across the axis (measured between the OSM deck-polygon centroids). The pylons' along-bridge position is inferred, +-30 m.

## Published dimensions

* **Cable-stayed**, longest span 624 ft = **190.20 m**; clearance below 90 ft = **27.43 m**; **9 lanes** in total
  (5 eastbound, 4 westbound) plus a bicycle and pedestrian path on the westbound span; **56 stay cables** in total
  [Wikipedia "Kosciuszko Bridge (New York City)", NYSDOT].
* 56 cables over two structures, each with a single pylon and stays fanning in both directions from two planes
  (one per deck edge): 2 structures x 2 directions x 2 planes x **7 stays** = 56.
* Pylon height **91.4 m** (300 ft) above the deck — *inferred* from NYSDOT's description of the main tower; the
  infobox gives no figure.  Stated as an inference.
* Deck widths: eastbound (5 lanes + shoulders) **21.5 m**, westbound (4 lanes + shoulders + the 6.1 m shared-use
  path) **24.5 m** — *inferred* from the lane counts.
* The 1939 truss bridge it replaced (6,021 ft long, 300 ft main span, 125 ft clearance, 6 lanes) is **not** modelled;
  it no longer exists.

## Not modelled

the stay anchor boxes and dampers, the LED architectural lighting, the shared-use path's ramps and
overlook, the BQE interchange ramps at Meeker Avenue and the Long Island Expressway, and the noise walls.

## Polycounts / outputs

* `blender_out/landmarks/b_kosciuszko.glb` — 33,560 triangles, 1.63 MB, bounds min ['-332.2', '-362.5', '-3.4'] max ['284.3', '311.7', '122.0']
* `blender_out/landmarks/b_kosciuszko_lod1.glb` — 6,404 triangles, 0.25 MB, bounds min ['-332.2', '-362.5', '-3.4'] max ['284.3', '311.7', '122.0']
