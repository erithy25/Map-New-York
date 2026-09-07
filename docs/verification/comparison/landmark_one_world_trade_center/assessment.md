# One World Trade Center

`landmark_one_world_trade_center` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:One World Trade Center, top and spire.JPG by Opencooper, CC0 (http://creativecommons.org/publicdomain/zero/1.0/deed.en), taken 2017-09-15 17:23:28, 1920x2682. [Commons page](https://commons.wikimedia.org/wiki/File:One_World_Trade_Center,_top_and_spire.JPG)

**Camera** — camera 40.71011, -74.01164 (NYC_TM -5253, 1285) z 6.3 m NAVD88 | azimuth 333.1deg pitch +0.0deg | 18 mm on 36 mm (71.2deg horizontal, 90.0deg vertical, portrait) | 884x1234. View direction: 333.1 deg, the bearing from this photograph's own GPS position to One World Trade Center; heading and position both come from the photograph.  The item's recorded azimuth is 337.3 deg, 4.2 deg away, and belongs to its nominal viewpoint. Aim: level optical axis (the subject is 327 m away; anything that far is photographed with a level camera).

**Sun** — azimuth 257.4°, elevation 18.3° at 2017-09-15T17:23:28-04:00 (EXIF DateTimeOriginal).

**In frame** — 7/8 building tiles, 16 landmark models, 3,756 pavement polygons, 613 props, 4,930 facade-kit pieces; 3,177,476 triangles; ground mesh 221² at 2.0 m near / 40.0 m far. Frame mean 0.393, sd 0.189 (was 0.322 / 0.143).

**Camera clearance** — the recorded viewpoint is inside `lm_b_wtc_site.243` (a ray straight up from the eye point hits its roof); the camera was moved **166 m** onto the nearest real roadbed polygon in `data/processed/roads/pavement`, keeping the same eye height above the heightmap. No point within 80 m had 80 m of open air along the view azimuth with nothing inside 8 m of the lens, so the frame is closed off 96 m ahead and `prop_lamp_bishops_crook_312` stands 7.7 m in front of the camera.

**Verdict — re-rendered 2026-09-07 against the corrected World Trade Center model. The camera search moved 166 m instead of 34 m and this time it found the building: One World Trade Center's tapered shaft stands dead centre of the frame at 183 m, cut off by the top edge as the lens rule says it must be. The price is that the frame is no longer taken anywhere near where the photograph was taken**

## What changed since the last sheet, and why

The previous sheet was rendered while `b_wtc_site` stood 3.5 m too high and carried a 520 × 520 m
plaza slab; both are fixed (`docs/verification/landmarks/REPORT_B.md` §12). The camera search reacted:

| | before | now |
|---|---|---|
| clearance rule that fired | recorded viewpoint **under `verify_terrain`** | recorded viewpoint **inside `lm_b_wtc_site.243`** |
| correction | moved 34 m backwards into open air | moved **166 m** onto the nearest roadbed polygon |
| camera | (-5193, 1094, 7.21) | (-5253, 1285, 6.32) — **199.7 m** away |
| what is centred | the glazed base of a neighbouring tower | **One World Trade Center**, 183 m away on a bearing of 332.3 deg against a view azimuth of 333.1 deg |

Part of this was already pending: `docs/verification/comparison/REPORT.md` §2.7 records that this
subject's camera had moved to (-5205, 1057, 8.5) under the street-percentile void exclusion before the
model was touched at all, and that the shipped sheet predated it. The model fix is what turned that
39 m move into a 166 m one, by leaving the recorded eye point inside built geometry instead of under
terrain.

**This is a worse camera and a better picture, and both halves should be said.** 166 m is a long way
from a photographer's recorded position, and a sheet whose camera has to be moved that far is not
testing the viewpoint it claims to. What it does now test — the shaft's taper and its proportion against
7 World Trade Center beside it — it could not test before.

## What matches

* **One World Trade Center is in the frame and it is recognisable.** Its base projects to (433, 625) in
  an 884-wide frame — horizontal centre — at 183 m, and the shaft's chamfered taper reads all the way
  to the top edge. 7 World Trade Center's dark slab stands at (784, 624), 181 m away, on the right.
* The camera stands on a real roadbed polygon at the eye height the heightmap gives, and the heading
  (333.1 deg) is still the bearing from the photograph's own EXIF GPS to the tower.
* The lens rule widened 35 mm to the 18 mm floor and states its limit; at 183 m a 541 m tower needs
  71 deg of elevation and a level axis has 45 deg, so the top is cut off and the sheet says why.
* **The memorial oaks are single-canopied.** The impostor card that used to be merged into every one of
  them is gone from the exported glb (`impostor_cards_dropped: 0`, `impostor_faces_dropped: 0`), so the
  street trees and plaza oaks in the middle distance are real crowns rather than solid cones.
* A bishop's-crook lamp standard, a subway entrance with its `SUBWAY` sign and railings, benches and
  three-quarters of a block of street trees fill the near field; 3,756 pavement polygons are placed.

## What does not match

* **The frame is 166 m from the photograph's viewpoint.** The reference is a tilted-up close portrait of
  the crown and spire from Greenwich Street; the render is a level street view from a roadbed a block
  and a half away. The two are not comparable on composition at all — only on the shaft's proportion.
* **The spire is not in the frame** and neither is anything above about the 45th floor: a level axis at
  183 m from a 541 m tower cannot contain it. The item exists to test the crown and the 124 m spire.
* **The 9/11 Memorial pools are modelled but not visible from here.** (The previous assessment said they
  were "not modelled at all"; that was the plaza slab hiding them — the parapets, the 9.14 m walls, the
  water and the central voids are all in `b_wtc_site.glb` and the plaza is now cut open over both. From
  this camera the North Pool's centre projects to (144, 629) at 97 m, behind the tree line.)
* One of the eight tiles in the scene still has no building shell, so part of the west side of the site
  is empty.
* No people, no crowd, and no names on the memorial parapets.
* The lower third of the frame is a large untextured pale plane — roadbed and sidewalk polygons carry a
  flat per-kind base colour.
* The reference's sky is full of cloud with the tower's glass reflecting it; the render's Nishita sky is
  clear and its curtain wall carries no reflection.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the camera is 166 m from the recorded viewpoint | the photograph's own GPS lands inside the World Trade Center model's built geometry, and the clearance rule's only remedy is to search outward for open air on a real pavement polygon | camera |
| the spire and crown are out of frame | a level axis at 183 m cannot contain a 541 m tower; the lens is already at the 18 mm floor | camera/optics |
| the memorial pools are not visible | they are 97 m away behind the plaza's tree line, and at eye level a 61 m basin 9.14 m deep is edge-on | camera |
| one tile with no shells | no `tile_buildings.glb` exists for that tile | data |
| no people or memorial names | no crowd placement, and `MEMORIAL_NAMES` is an engine-driven texture slot the verification renderer does not bind | data / material |
| flat pale roadbed and sidewalk | pavement polygons carry a flat per-kind base colour with no texture | material |
| clear sky against a clouded photograph | the sky is a Nishita atmosphere with no cloud layer | lighting |
