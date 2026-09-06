# World Trade Center site

Script: `blender/landmarks/b_wtc_site.py` · agent B · generated 2026-09-06 12:48 UTC

## Placement

frame origin NYC_TM (-5338.0, 1285.0) on the memorial plaza, site grid 160.6 deg; every building on its real OTI footprint; pool centres derived from OSM way 129835611.

## Published dimensions

* **Oculus** (Santiago Calatrava, WTC Transportation Hub, opened 4 March 2016): the arched elliptical body is
  **350 ft = 106.7 m long**, **115 ft = 35.1 m wide** at its widest, and rises **96 ft = 29.3 m above grade at the
  apex**; the structural steel ribs continue upward as a pair of canopies reaching **168 ft = 51.2 m above grade**;
  between the two 350 ft arches a **330 ft = 100.6 m operable skylight** runs the length of the building; the
  concourse is column-free and 11,500 tons of structural steel were used [Calatrava, PANYNJ, explorewtc.com].
  This model builds **2 x 56 = 112 ribs** — the rib count is *inferred* from the published 350 ft length and the
  photographed rib pitch (about 1.9 m), not from a published figure.
* **3 World Trade Center** (Rogers Stirk Harbour, 2018): **329.2 m** (1,079 ft), 80 storeys; **4 World Trade Center**
  (Maki, 2013): **297.7 m** (977 ft), 72 storeys; **7 World Trade Center** (SOM, 2006): **226.1 m** (741.7 ft), 52
  storeys, a parallelogram plan over a Con Edison substation podium.
* **National September 11 Memorial** (Michael Arad / Peter Walker, 2011): **two pools, each set in the 200 ft =
  61.0 m footprint of one of the original towers**, "each pool nearly an acre"; the water falls **9.1 m (30 ft)**
  down the pool walls to a second, smaller void; the names of the **2,983 victims are inscribed on 152 bronze
  parapets** around the pools.  The parapets carry the material slot ``MEMORIAL_NAMES`` so the engine can drive the
  incised-name texture.
* **Plaza trees**: more than **400 swamp white oaks** (*Quercus bicolor*) and one Callery pear (the Survivor Tree).
  ``blender_out/props/`` contained no tree asset when this model was built (only ``_smoke.glb``), so the oaks are
  built with ``b_common.simple_tree`` — a low-poly trunk-plus-three-lobes tree, **not** a prop-library asset
  (stated gap).  **220 oaks** are placed on the modelled part of the plaza on a 7.3 m grid clipped to the plaza
  polygon, not the full 400+ (the rest stand on the parts of the plaza south and east of this model's extent).

## Not modelled

the below-grade PATH platforms, the memorial museum's underground galleries (only the pavilion above
grade is built), 2 World Trade Center (never built above the below-grade box), the Liberty Park elevated garden and
St Nicholas Greek Orthodox Church, the individual curtain-wall panes, and the Oculus's marble interior floor.

## Polycounts / outputs

* `blender_out/landmarks/b_wtc_site.glb` — 40,254 triangles, 1.45 MB, bounds min ['-260.0', '-260.0', '-14.6'] max ['260.0', '260.0', '334.1']
