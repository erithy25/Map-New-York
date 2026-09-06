# One World Trade Center

`landmark_one_world_trade_center` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:One World Trade Center, top and spire.JPG by Opencooper, CC0 (http://creativecommons.org/publicdomain/zero/1.0/deed.en), taken 2017-09-15 17:23:28, 1920x2682. [Commons page](https://commons.wikimedia.org/wiki/File:One_World_Trade_Center,_top_and_spire.JPG)

**Camera** — camera 40.71011, -74.01164 (NYC_TM -5193, 1094) z 7.2 m NAVD88 | azimuth 333.1deg pitch +0.0deg | 18 mm on 36 mm (71.2deg horizontal, 90.0deg vertical, portrait) | 884x1234. View direction: 333.1 deg, the bearing from this photograph's own GPS position to One World Trade Center; heading and position both come from the photograph.  The item's recorded azimuth is 337.3 deg, 4.2 deg away, and belongs to its nominal viewpoint. Aim: level optical axis (the subject is 327 m away; anything that far is photographed with a level camera).

**Sun** — azimuth 257.4°, elevation 18.3° at 2017-09-15T17:23:28-04:00 (EXIF DateTimeOriginal).

**In frame** — 6/8 building tiles (109,350 tris), 16 landmark models, 3,756 pavement polygons, 613 props, 4,930 facade-kit pieces; 3,177,062 triangles; ground mesh 221² at 2.0 m near / 40.0 m far.

**Camera clearance** — the recorded viewpoint is under verify_terrain (0.0 m of ground or paving directly overhead, so the eye point is beneath the walking surface); the camera was moved 34 m backwards -- the nearest point in open air -- keeping the same eye height above the heightmap.  The view azimuth is clear for 96 m from there

**Verdict — the camera had to be dragged out from under the memorial plaza and what it found is the glazed base of a neighbouring tower with the memorial oaks in front of it; One World Trade Center's own tapered shaft and spire are out of frame**

## What matches

* The under-the-paving test caught a real fault: the recorded viewpoint sits beneath verify_terrain — the 1 m DEM records the memorial pool voids — and the camera was moved 34 m backwards into open air with 96 m of clear azimuth.
* The camera stands on the photograph's own EXIF GPS, 51 m from the item's nominal viewpoint, and the heading (333.1 deg) is the bearing from there to the tower.
* The lens rule widened 35 mm to the 18 mm floor and states the limit: 533 m of building above the lens at 327 m, 58 deg above the horizon, so the top is still cut off.
* The memorial plaza's swamp white oaks are modelled and correctly placed in a row, in full September leaf, and the plaza's raised paving edge is at the right height.
* The glazed tower behind them carries a real curtain wall with horizontal spandrel bands and a legible mullion grid, and 3,756 pavement polygons and 16 landmark models are in the scene.

## What does not match

* One World Trade Center is not in the frame. The item exists to test the tapering octagonal shaft, the chamfered corners and the 124 m spire, and none of it is visible.
* The 9/11 Memorial pools — the void the plaza is built around, and the reason the viewpoint exists — are not modelled at all: the plaza is a flat plane. The pools' absence is also what put the camera underground in the first place, since the DEM records them and no geometry does.
* Two of the eight tiles in the scene have no building shell (t_-7_0, t_-7_1), so the west side of the site is empty.
* No people, no memorial parapets, no names, no reflecting water.
* The lower half of the frame is a large untextured pale plane.
* The reference's sky — full of cloud, with the tower's glass reflecting it — has no counterpart under a clear Nishita sky.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the tower is not in the frame | the corrected camera is 34 m from the recorded viewpoint and a level axis cannot contain a 541 m tower at 327 m | camera |
| no memorial pools | the pools are neither building footprints nor props; no stage builds them, though the DEM records their void | geometry |
| two tiles with no shells | no tile_buildings.glb exists for t_-7_0 and t_-7_1 | data |
| no people or memorial detail | no crowd placement, and memorial structures are in no dataset the scene reads | data |
| clear sky against a clouded photograph | the sky is a Nishita atmosphere with no cloud layer | lighting |
