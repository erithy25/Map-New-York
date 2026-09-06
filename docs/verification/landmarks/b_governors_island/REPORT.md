# Governors Island: Castle Williams and Fort Jay

Script: `blender/landmarks/b_governors_island.py` · agent B · generated 2026-09-06 14:10 UTC

## Published dimensions

* **Castle Williams** (Lt. Col. Jonathan Williams, 1807-1811): a circular casemated battery of red sandstone,
  **200 ft = 60.96 m in outside diameter**, its walls **40 ft = 12.19 m high** and **8 ft = 2.44 m thick**, with
  **three tiers of casemates** carrying **26 guns per tier** plus a barbette tier on the roof [NPS, HABS NY-6396,
  Wikipedia "Castle Williams"].  Its real OSM plan (way ``278396567``) measures **63 x 62 m** — 3 % over the
  published 200 ft, the difference being the modern parapet and the entrance sally-port block; the model uses the
  published 60.96 m diameter centred on the OSM polygon and states the difference.  The inner court is OSM way
  ``278396580`` (37 x 35 m).
* **Fort Jay** (1794, rebuilt 1806-1809): a **four-bastioned star fort** of earth faced in stone, with a dry ditch
  and a sandstone gate with the 1790s sculpted arms of the United States.  Its real OSM plan (way ``1388461669``,
  ``historic=fort``) spans **188 x 201 m**, which is the covered way; the scarp is modelled inside it.  Fort Jay
  Theatre inside the fort is OSM way ``278396529`` (43 x 47 m, tagged height 10.6 m).
* Ground level on the island is taken as **4.0 m NAVD88** (the LiDAR ground of the island's building footprints runs
  3.7-5.2 m).

## Placement

both forts are built on their **real OSM plans**; nothing is placed by hand.

## Not modelled

the casemate interiors and the gun carriages, the sally-port and its sculpted arms, Fort Jay's
barracks buildings and the officers' quarters inside the walls, the dry ditch's counterscarp masonry, the island's
other buildings (Nolan Park, Colonels Row, the Admiral's House), Hills park and the ferry landings.

## Polycounts / outputs

* `blender_out/landmarks/b_governors_island.glb` — 4,122 triangles, 0.24 MB, bounds min ['-175.8', '-537.4', '-6.0'] max ['232.7', '110.9', '13.5']
* `blender_out/landmarks/b_governors_island_lod1.glb` — 1,644 triangles, 0.11 MB, bounds min ['-175.6', '-537.4', '-6.0'] max ['232.7', '110.9', '13.5']
