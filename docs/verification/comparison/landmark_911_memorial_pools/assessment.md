# National September 11 Memorial pools

`landmark_911_memorial_pools` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:National September 11 Memorial South Pool - 04.jpg by Oleg Yunakov, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2025-09-11 17:01:35, 1920x2560. [Commons page](https://commons.wikimedia.org/wiki/File:National_September_11_Memorial_South_Pool_-_04.jpg)

**Camera** — camera 40.71116, -74.01263 (NYC_TM -5293, 1241) z 5.8 m NAVD88 | azimuth 314.3deg pitch +0.0deg | 18 mm on 36 mm (73.7deg horizontal, 90.0deg vertical, portrait) | 904x1206. View direction: 314.3 deg, the bearing from this photograph's own GPS position to the North Pool as the reference metadata records it; heading and position both come from the photograph, 37 m from the item's recorded viewpoint. Aim: level optical axis; the lens was widened from 35 mm to the 18 mm floor and the top of the subject is still cut off. **The camera was not moved** — it stands on the memorial plaza at the height the heightmap gives (4.195 m + 1.6 m eye).

**Sun** — azimuth 254.4°, elevation 23.6° at 2025-09-11T17:01:35-04:00 (EXIF DateTimeOriginal).

**In frame** — 4/4 building tiles, 10 landmark models, 1,649 pavement polygons, 554 props, 264 facade-kit pieces; 1,839,874 triangles; ground mesh 203² at 2.0 m near / 40.0 m far, with **8,113 quads and 414 pavement triangles cut out under the memorial plaza**. Frame mean 0.383, sd 0.181.

**Verdict — the model defect that made this frame black is fixed and the frame is now taken where the photograph was taken: the camera stands at the South Pool's bronze parapet on ground the heightmap and the model agree about, the plaza is cut open over the pool and the opening reads as a void beyond the coping. What is still not there is the water: the level-axis rule cannot see over a 1.07 m parapet into a basin 9.14 m down, and the scene's terrain is drawn across the opening 2.5 m below the deck**

## What changed since the last sheet, and why

The previous sheet of this subject was made after the comparison stage worked around three faults in
`blender/landmarks/b_wtc_site.py` rather than fixing them. All three are now fixed in the model
(`docs/verification/landmarks/REPORT_B.md` §12) and this frame was re-rendered against it.

| was | now | measured |
|---|---|---|
| the plaza deck stood at **7.000 m NAVD88** where the heightmap reads 4.19 m, so the recorded eye point sat 1.21 m *underneath* it and the frame was black until the camera was raised 2.81 m onto the model's own deck | the deck is at **4.40 m** — 0.21 m above the heightmap — and the camera stands on it at the eye height the heightmap gives, **not moved at all** | camera z 8.60 m → **5.795 m** |
| the plaza was one unbroken 520 × 520 m quad drawn across both 61 m pool openings, so no camera anywhere on the plaza could see a pool | the plaza is the real 8-acre memorial plaza with both pool squares cut out of it | the `plaza` mesh carries 116 triangles, **none** of them inside either pool square |
| all 220 memorial oaks carried a merged impostor card and were drawn with two canopies; `scene.py` stripped 12 card faces on 2 template meshes at import | the glb carries no `IMPOSTOR_*` material at all | `impostor_cards_dropped: 0`, `impostor_faces_dropped: 0` |
| the pool centres were derived ±85 m along the plaza polygon's axis | they are measured from OSM ways 697722178 / 697722181 | the derived centres were **31.8 m** and **30.1 m** out, with the squares **41.4 deg** out of rotation |

One consequence needed a change in this stage rather than in the model. `camera._walk_to_parapet`
treated the memorial plaza as ground only because the old 520 × 520 m slab still carried the eye at the
end of a 250 m probe; once the plaza was clipped to its real outline the walk started dragging this
camera **26 m** off the photographer's position and into a frame of benches and street trees. The rule
now asks what it actually depends on: the parapet walk exists because an observation-deck viewpoint is
*one nominal lat/lon standing for a whole deck*, so it is applied only when the camera position is that
— and refused when the position came from the photograph's own EXIF GPS, which is a measurement of
where the photographer stood and not a point to be guessed away from. This camera is the photographic
case (`camera_origin.from_photograph_gps: true`) and stays put; Bethesda Terrace is the nominal case
and still walks 12 m to its balustrade, re-rendered to a bit-identical frame to check that.

Two rules that looked more principled were tried against both scenes and rejected on measurement: a
deck within 2 m of the heightmap is ground (the memorial reads 1.33 m and Bethesda's terrace 1.6 m —
they do not separate), and a parapet needs a drop beyond its edge (the memorial reads 1.10 m and
Bethesda 0.90 m — the same). Both would have moved a mandated viewpoint's camera.

## What matches

* **The camera is where the photographer stood, at the parapet.** In the pool's own axes it sits
  30.68 m along the square's edge direction and 26.18 m across from the South Pool's measured centre —
  **0.18 m outside the 61 m square**, i.e. standing at the coping, which is exactly what the
  photograph's own GPS describes. Nothing raised, walked or searched for it.
* **The plaza is open and the opening is in the frame.** The South Pool's bronze `MEMORIAL_NAMES`
  parapet runs away from the lens down the left of the frame with its 2.3 m panel joints visible, and
  beyond it the plaza stops: the dark wedge in the lower left is the cut, not a shadow. The far corner
  of the same opening projects to (287, 618) at 55 m, in frame.
* **The memorial oaks are single-canopied.** They read as the dark green band across the middle of the
  frame with sky and tower behind, rather than the solid cones the impostor card used to draw.
* 3, 4 and 7 World Trade Center stand behind the grove at the right relative heights, and the memorial
  museum pavilion's canted glass mass fills the right of the frame.
* The Sun is placed from the photograph's own timestamp — 11 September 2025 at 17:01, elevation 23.6°,
  azimuth 254.4° — so both frames are lit from the west-south-west late in the afternoon.

## What does not match

* **There is still no water and no waterfall, and this is geometry, not a missing model.** The basin is
  modelled (parapet 0.15–1.07 m, walls to −9.14 m, water at −8.79 m, the central void to −18.14 m, all
  measured in the glb). From an eye 1.6 m above the deck standing at a 1.07 m coping, the sight line
  that grazes the coping's inner edge falls **0.137 m per metre**, so it needs **74.6 m** of run to
  reach water **10.19 m** below the eye — and the basin is **56.6 m** across inside the parapet. The
  water cannot be seen from this camera, and would not be seen by a person standing there either. The
  reference photograph solves it the way visitors do, by leaning over the coping and tilting about 40°
  down; the level-axis rule that keeps a render comparable on proportion forbids that.
* ~~**The scene's terrain is drawn across the opening.**~~ **Fixed in the scene builder on 2026-09-07**
  (`docs/verification/comparison/REPORT.md` §2.9). Where a landmark models its own ground, the terrain
  and the pavement are no longer drawn inside that surface's outer plan outline, openings included:
  this frame cuts **8,113 terrain quads and 414 pavement triangles** out of the 33,039 m² memorial
  plaza outline, and the published heightmap — a median **1.98 m** NAVD88 inside the South Pool square
  over 961 samples at 2 m, 2.4 m below the deck — no longer crosses the basin.
  **This changes almost nothing in *this* frame, and the reason is the optics above, not the fix.**
  Cropped to the pool opening the render differs from the shipped one by 0 % of pixels above 8/255
  (maximum single-pixel difference 15). From an eye 0.33 m above the coping the sight line into the
  opening never reaches down to 1.98 m before it meets the far wall, so the terrain that was removed
  was never visible from here in the first place. It was visible in principle to any camera that could
  look into the pool, and the landmark's own `memorial_plaza.png` — taken 12 m above the deck with no
  context ground — is where the basin, the water and the central void can actually be seen.
* **The frame is aimed at a different pool from the one the photograph shows.** The reference records
  its subject as "the North Pool" at 40.7118, -74.0135, and the azimuth is the bearing from the camera
  to that point. Measured against OSM way 697722178, that recorded point is **46.6 m** from the real
  North Pool's centre; and the photograph itself is titled, categorised and framed as the *South Pool*,
  which is at the photographer's feet at bearing 249.7°, behind the lens. The North Pool the render is
  aimed at is 118.4 m away at bearing 337.3°, 23° right of the frame centre and edge-on. The subject
  coordinate is reference metadata, not photographic evidence, and it has not been edited here.
* **The framing is not the photograph's framing**, for the same reason as before: the reference is a
  close-up tilted down the coping with the incised names, roses and flags legible; the render's level
  axis shows the coping as tan plates seen from 0.28 m above them.
* **The names are not there.** `MEMORIAL_NAMES` is a material slot for an engine texture and the
  verification renderer does not drive it, so the parapets are plain bronze. The photograph's subject is
  the lettering.
* **No flowers, no flags, no people.** The photograph is a 9/11 anniversary picture: roses on every
  name, small flags, and a crowd along the far parapet.
* The towers are flat pale-blue and white massing with no glass reflectance, no spandrel banding and no
  visible fenestration.
* The museum pavilion renders as a large near-white translucent mass; its `b_glass_clear` material is
  alpha-blended with a 0.5 base alpha, which reads as frosted plastic rather than glass.
* The paved plaza is one flat tone: no granite paving pattern, no joints, no kerb line around the pools.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| ~~the frame was black from the recorded viewpoint~~ | **fixed in the model**: `GRND` was both the local datum and the frame origin's NAVD88 z, so the plaza level was counted twice. The plaza now measures 4.40 m NAVD88 in the exported glb and the camera is no longer corrected at all | geometry |
| ~~no pool water, waterfall or void visible from anywhere on the plaza~~ | **fixed in the model**: the plaza is cut open over both pools. What remains is the two entries below | geometry |
| ~~the opening reads as a shallow inset, not a 9.14 m fall~~ | **fixed**: the terrain and pavement are cut out under a landmark's own ground plane, openings included. It makes no visible difference from *this* camera, whose sight line never reaches the depth the terrain was drawn at | scene assembly |
| no water visible over the parapet | the sight line from a 1.6 m eye over a 1.07 m coping cannot reach 10.19 m down inside a 56.6 m basin; the photograph tilts 40 deg down and the level-axis rule cannot | camera/optics |
| the frame is aimed at the North Pool while the photograph is of the South Pool | the reference `subject` coordinate, which is 46.6 m from the real North Pool and not what this photograph shows | reference metadata |
| the parapets carry no names | `MEMORIAL_NAMES` is a material slot for an engine-driven texture; the verification renderer has no texture to bind to it | material |
| no roses, flags or people | no stage places people or temporary objects into a still verification frame | data |
| flat pale towers, no glass | building and landmark shells carry a per-material base colour only | material |
| the museum pavilion reads as frosted plastic | `b_glass_clear` is an alpha-blended 0.5-alpha material with no transmission or roughness model | material |
| plain paved plaza with no granite pattern or joints | pavement and landmark paving carry a flat per-kind base colour with no texture | material |
