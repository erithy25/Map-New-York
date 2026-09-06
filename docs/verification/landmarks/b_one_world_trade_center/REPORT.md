# One World Trade Center

Script: `blender/landmarks/b_one_world_trade_center.py` · agent B · generated 2026-09-06 12:46 UTC

## Placement

real OTI footprint BIN 1088469, centroid NYC_TM (-5338.11, 1446.55), LiDAR ground 1.524 m NAVD88; principal axis 119.36 deg (the World Trade Center site grid).

## Published dimensions

* **541.3 m (1,776 ft) to the tip of the spire**, **417.0 m (1,368 ft) to the roof/parapet** — the roof height is
  deliberately that of the original North Tower.  The spire is therefore **124.3 m** tall.  104 storeys
  [CTBUH, SOM, PANYNJ; both figures are named in the build brief].
* **Base: a 200 ft = 61.0 m square**, the same plan as the original North Tower.  The real OTI footprint (BIN
  1088469) measures **3,858 m2**, against 3,721 m2 for a true 61.0 m square — 3.7 % larger because the footprint
  includes the podium's entrance canopies; the podium is built on the **real footprint** and the tower shaft on the
  published square (stated).
* **Form: a chamfered square that becomes a regular octagon at mid-height and a 145 ft = 44.2 m square rotated 45
  degrees at the roof.**  The shaft is therefore eight flat isosceles triangles.  Interpolating the two plans
  linearly puts the perfect octagon at **58 % of the shaft height** — the published "midpoint" of the tower.
* **Podium**: 185 ft = **56.4 m** tall, a windowless reinforced-concrete cube clad (in the 2011 redesign) in
  vertical **prismatic glass fins** rather than the cancelled prismatic-glass panels.  This model builds 4 x 46 = 184
  fins at a 1.32 m pitch, each 0.55 m deep (fin count and pitch *inferred* from the 61 m face; the published figure
  is "about 4,000 prismatic glass panels" over the whole podium).
* **Spire**: a 124.3 m communications mast on a circular platform, with the cable-stayed ring at its base and a
  beacon at the tip.
* Curtain wall: about 13,000 panes of low-iron glass; modelled as a floor-band rhythm of 3.7 m storeys with a
  spandrel band, not as individual panes (stated gap).

## Not modelled

the individual curtain-wall panes and their mullion detail, the sky lobby and observatory interiors,
the 2 World Trade Center site to the north-east (a separate landmark), the below-grade PATH and retail concourses,
the spire's radome (removed from the design in 2012 — correctly absent), the window-washing rig, and the plaza
paving and bollards.

## Polycounts / outputs

* `blender_out/landmarks/b_one_world_trade_center.glb` — 6,044 triangles, 0.36 MB, bounds min ['-42.3', '-42.4', '-6.0'] max ['42.1', '42.4', '542.8']
