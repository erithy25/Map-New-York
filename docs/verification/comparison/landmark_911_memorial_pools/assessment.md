# National September 11 Memorial pools

`landmark_911_memorial_pools` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:National September 11 Memorial South Pool - 04.jpg by Oleg Yunakov, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2025-09-11 17:01:35, 1920x2560. [Commons page](https://commons.wikimedia.org/wiki/File:National_September_11_Memorial_South_Pool_-_04.jpg)

**Camera** — camera 40.71116, -74.01263 (NYC_TM -5293, 1241) z 8.6 m NAVD88 | azimuth 314.3deg pitch +0.0deg | 18 mm on 36 mm (73.7deg horizontal, 90.0deg vertical, portrait) | 904x1206. View direction: 314.3 deg, the bearing from this photograph's own GPS position to the North Pool; heading and position both come from the photograph, 37 m from the item's recorded viewpoint. Aim: level optical axis; the lens was widened from 35 mm to the 18 mm floor and the top of the subject is still cut off. The eye was raised 2.81 m onto the World Trade Center model's own plaza deck — see below.

**Sun** — azimuth 254.4°, elevation 23.6° at 2025-09-11T17:01:35-04:00 (EXIF DateTimeOriginal), with the view transform opened 0.88 stops.

**In frame** — 4/4 building tiles (82,358 tris), 10 landmark models, 1,649 pavement polygons, 554 props, 264 facade-kit pieces; 1,836,206 triangles; ground mesh 203² at 2.0 m near / 40.0 m far. Frame mean 0.475, sd 0.137.

**Verdict — this frame renders at all only because the camera was raised onto the WTC model's plaza deck, which stands 2.74 m above the ground the heightmap reports; the two frames both stand at the South Pool parapet but the photograph tilts down along it in close-up while the render's level axis looks across the plaza, and neither pool's water or void is visible in the render because the model's plaza is drawn as one unbroken plane across both openings**

## Why this frame was black, and what was done about it

This was the last of the 57 subjects without a usable render (mean 0.0003). The cause was measured, not guessed:

* `lm_b_wtc_site.232` — the object a ray straight up from the eye point hit — is the World Trade Center model's **plaza**: a two-triangle, four-vertex 520 × 520 m quad on material `b_sidewalk`, every vertex at exactly **7.000 m NAVD88**. It is not a tree and not a roof.
* The camera stood at **5.795 m**, i.e. **1.21 m underneath it**, with the South Pool's granite wall 0.15 m ahead. Sampling 400 directions over the sky hemisphere from that point, **400 of 400 were blocked** — 113 by the plaza quad and 287 by the pool wall. There was nothing to see.
* The plaza is 2.74 m above the ground the camera's height was measured from: the 1 m DEM reads **4.26 m NAVD88** at the same point. The reason is in `blender/landmarks/b_wtc_site.py`: `GRND = 3.5` is used both as the model's local plaza level *and* as the frame origin's NAVD88 z, and the catalogue's `origin_tm` is added to the local geometry on import, so the plaza level is counted twice. Across the other 92 catalogue entries the median |origin z − DEM| is 0.07 m, so this is one model's fault and not the convention. **It is a landmarks-stage defect and is left for that stage; nothing in this pass edits the model.**
* The comparison stage now raises an eye point that lands under a *landmark's own* level deck onto that deck, because a landmark carries ground the DEM knows nothing about and where they disagree the modelled deck is what a visitor walks on. The camera moved from 5.795 m to **8.60 m** and the frame came up at mean 0.475.

Two consequences worth stating plainly. First, **every metre in this frame is 3.5 m higher above sea level than it should be**, uniformly, so nothing inside the frame is distorted but the world's datum is wrong here. Second, the earlier diagnosis in `render_error.txt` — that the eye point was inside an oak canopy — was wrong: the nearest oak is **93.3 m** away, and all 220 of them lie between −1.0 deg and +5.7 deg of the horizon from this camera.

## What matches

* **Both frames stand at the South Pool parapet.** The photograph's own GPS puts the camera about 3 m inside the pool's rim, which is hand-held error on a 61 m square, and the render's foreground is the same thing the photograph's is: the bronze `MEMORIAL_NAMES` parapet running away from the lens. The model carries 152 parapet panels at 7.15–8.07 m with the material slot for the 2,983 incised names.
* The North Pool is where the heading points, 102 m away, and its parapet ring is visible across the frame at y ≈ 600 of 1206 — a brown band at the right elevation for a 1.07 m coping seen from 1.6 m up at 100 m.
* **The plaza oaks read correctly.** The grove appears as a continuous green band immediately above the North Pool's parapet. Projecting the 220 oak nodes through this camera puts the nearest at 93.3 m with canopy tops 5.6 deg above the horizon and trunk bases 1.0 deg below it, which is exactly the band the render shows. 217 of the 220 fall inside the horizontal field of view.
* 3, 4 and 7 World Trade Center stand behind the grove as pale slabs at the right relative heights, and the memorial museum pavilion's canted glass mass fills the right of the frame at 46 m.
* The Sun is placed from the photograph's own timestamp — 11 September 2025 at 17:01, elevation 23.6 deg, azimuth 254.4 — so both frames are lit from the west-south-west late in the afternoon. The render's exposure opened 0.88 stops to hold that low sun.

## What does not match

* **Neither pool's water, waterfall or void is visible in the render, and the photograph's is the whole left half of its frame.** The model's plaza is a single flat quad spanning ±260 m with no opening cut for either pool (four vertices, two triangles, measured from the exported glb), so it is drawn straight across both 61 m openings. The pool walls, the 9.14 m fall and the water surface are all modelled and all sealed underneath it. From this camera the openings are edge-on at −0.9 deg so nothing would be seen into them anyway, but the geometry means no camera anywhere on the plaza can see a pool.
* **The framing is not the photograph's framing.** The reference is aimed about 40 deg down along the parapet from roughly 1.2 m above it, so the bronze coping fills the frame in perspective, with the incised names, roses and flags legible and the pool water and far wall in the top left. The render's optical axis is level, by the rule that keeps verticals vertical, so the same parapets appear as flat tan plates seen from 0.5 m above and the frame is dominated by plaza and sky. The two cannot be compared on the thing the photograph is of.
* **The names are not there.** `MEMORIAL_NAMES` is a material slot for an engine texture and the verification renderer does not drive it, so the parapets are plain bronze. The photograph's subject is the lettering.
* **No flowers, no flags, no people.** The photograph is a 9/11 anniversary picture: roses on every name, small flags, and a crowd along the far parapet and the walkway. The render has none of it.
* The parapets read as flat plates rather than as a 1.07 m coping, because the camera is only 0.53 m above their top surface and the level axis shows only that surface.
* The towers are flat pale-blue and white massing with no glass reflectance, no spandrel banding and no visible fenestration; the photograph's reflection in the pool water shows a real curtain wall.
* The museum pavilion renders as a large, near-white translucent mass on the right. Its `b_glass_clear` material is alpha-blended with a 0.5 base alpha, which at this distance and angle reads as frosted plastic rather than glass.
* The paved plaza is one flat tone: no granite paving pattern, no joints, no kerb line around the pools.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the frame was black from the recorded viewpoint | the `b_wtc_site` model's plaza deck stands at 7.00 m NAVD88 where the DEM reads 4.26 m, because `GRND = 3.5` is counted both as the model's local plaza level and as its frame origin's NAVD88 z. **Corrected in the comparison stage by standing the camera on the modelled deck; the model itself is still 3.5 m too high** | geometry |
| no pool water, waterfall or void visible from anywhere on the plaza | `bc.ground_plane("plaza", 260.0, GRND, "sidewalk")` builds one unbroken 520 m quad with no opening cut for the two pools, so it is drawn across both | geometry |
| the render is level where the photograph is tilted 40 deg down | the level-axis rule, which is what makes a render and a photograph comparable on proportion. A close-up down a horizontal surface cannot be reproduced under it | camera/reference metadata |
| the parapets carry no names | `MEMORIAL_NAMES` is a material slot for an engine-driven texture; the verification renderer has no texture to bind to it | material |
| no roses, flags or people | no stage places people or temporary objects into a still verification frame | data |
| flat pale towers, no glass | building and landmark shells carry a per-material base colour only | material |
| the museum pavilion reads as frosted plastic | `b_glass_clear` is an alpha-blended 0.5-alpha material with no transmission or roughness model | material |
| plain paved plaza with no granite pattern or joints | pavement and landmark paving carry a flat per-kind base colour with no texture | material |
