# Trinity Church from Wall Street

`landmark_trinity_church` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Trinity Church Wall St (6217334552).jpg by Tony Hisgett from Birmingham, UK, CC BY 2.0 (https://creativecommons.org/licenses/by/2.0), taken 2011-09-16 14:43, 1920x3089. [Commons page](https://commons.wikimedia.org/wiki/File:Trinity_Church_Wall_St_(6217334552).jpg)

**Camera** — camera 40.70657, -74.00981 (NYC_TM -5055, 732) z 9.4 m NAVD88 | azimuth 311.3deg pitch +0.0deg | 35 mm on 36 mm (35.4deg horizontal, 54.4deg vertical, portrait) | 824x1326. View direction: 311.3 deg, the bearing from this photograph's own GPS position to Trinity Church; heading and position both come from the photograph. The item's recorded azimuth is 309.1 deg, 2.2 deg away, and belongs to its nominal viewpoint. Aim: level optical axis (the subject is 257 m away; anything that far is photographed with a level camera).

**Sun** — azimuth 220.9°, elevation 44.3° at 2011-09-16T14:43:00-04:00 (EXIF DateTimeOriginal, to the minute).

**In frame** — 6/6 building tiles (86,930 tris), 16 landmark models, 3,000 pavement polygons, 526 props, 10,186 facade-kit pieces; 4,500,232 triangles; ground mesh 215² at 2.0 m near / 40.0 m far. The kit was capped by the 2,324,290-triangle budget.

**Verdict — the frame is the right frame: the Wall Street canyon closes on the spire exactly as the photograph does, and Federal Hall's portico stands where it should. But it is far too dark to compare on anything but shape, and the church itself is a smooth cone on a plain brown box with no Gothic detail at all**

## What matches

* The composition is the photograph's composition. The street runs away WNW between two tall walls, the gap between them narrows to about a fifth of the frame width, and Trinity's spire stands in that gap at the vanishing point. Both frames put the spire slightly left of centre.
* The spire's proportion against the canyon is close. In the reference the tower and spire occupy the middle third of the frame's height; in the render they occupy roughly the same band, ending about a tenth of the frame lower — consistent with the reference being tilted up a few degrees while the render's axis is held level.
* Federal Hall is in the right place and at the right size. Its model stands 92 m away and 18.4 m above the lens, which puts the top of its pediment 11.3 deg above the optical axis, i.e. 275 px above the frame centre; the portico in the render sits at y ≈ 350–390 of 1326, which is where that calculation lands it. The reference shows the same colonnade on the same side, mostly hidden behind the crowd and the banners.
* The facade kit is doing real work. The building on the left carries punched window reveals in four bands and the tower behind it a curtain-wall grid; the right-hand wall carries a spandrel grid. At 10,186 pieces this is the densest kit placement of the five sheets written in this pass, and it is the reason the walls read as buildings rather than as slabs.
* The camera stands on the photograph's own EXIF GPS, 28 m from the item's nominal viewpoint, and the heading is measured from that point to the church, so the two frames face the same way to within 2.2 deg of the recorded azimuth.

## What does not match

* **The render is far darker than the photograph, and the bottom 45 % of it is a featureless dark plane.** Frame mean is 0.125 against a reference that is bright, flat, overcast light. The Sun is placed correctly (44.3 deg elevation, 220.9 deg azimuth, from the photograph's own timestamp) and a 20 m street between 100 m towers genuinely is in deep shade at that hour, so the geometry of the shadow is not wrong — but the reference was taken under heavy cloud, where the sky dome is the key light and the canyon floor is only about a stop below the facades. The render's clear Nishita sky at 0.25 strength cannot produce that, and no exposure compensation was applied (0.00 stops) because the direct normal irradiance is high.
* **Trinity Church is a brown box with a smooth cone on it.** The model's spire is a plain tapered cone with a small green tip; the reference's is an octagonal crocketed spire with finials at every setback and a cross on top, standing on a louvred belfry stage. Below it the render shows a flat brown mass where the photograph has the great west window, the clock, the arcaded porch, the buttresses and the pinnacled corner turrets. Nothing of the church's Gothic articulation is present.
* The tall pale slab immediately right of the spire is a flat untextured grey-white column for the whole height of the frame. In the photograph the same slot is filled by a blue-glass tower with clear floor banding and sky reflections. Building shells carry a per-material base colour and no glass BSDF, so every reflective facade in the frame reads as matte paint.
* **No people, no vehicles, no street furniture that is not a prop.** The photograph's lower third is a crowd of perhaps two hundred people, a Sabrett cart, a white event marquee, banner poles, flags, barriers and a statue on a plinth. The render has a handful of lamp standards and a rail, and the roadway is an unbroken grey plane. This is the largest single difference in the frame by area and it is entirely the "no moving objects" gap.
* Trinity's churchyard — the walled burying ground that fills the space in front of the church in the photograph, with its trees and headstones — is not modelled at all. In the render the ground simply runs up to the church.
* The banners, flags and signage hung off the right-hand facades (NYSC, "FINANCIAL", bgc, Equinox) are absent; the kit has no signage category.
* The reference was taken in 2011 and the world is built from current data, so the buildings are not the same set. This is not a fault of the render, but it limits how far a facade-by-facade comparison can be pushed.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the frame is much darker than the reference | the reference is an overcast photograph; the render lights every frame with a clear Nishita sky at the true Sun position and has no cloud layer, so a shaded street canyon falls much further below the sunlit facades than it does under cloud | lighting |
| Trinity's spire is a smooth cone; no tracery, crockets, clock or west window | the `trinity_church` landmark model is a massing model with a coned spire; the stage that builds it does not carve Gothic detail | geometry |
| flat pale slab where the photograph has a glass tower | building shells carry a per-material base colour only — no glass BSDF, no reflection, no spandrel banding | material |
| no crowd, no cart, no marquee, no vehicles | no stage places people, vehicles or temporary structures into a still verification frame | data |
| no churchyard, no headstones, no railing | the burying ground is neither a building nor a road polygon, so no stage produces it; the terrain flattens it | geometry |
| no banners, flags or facade signage | the facade kit has no signage or banner category | geometry |
| the reference is a 2011 photograph against a current-data world | the reference set is chosen for licence and viewpoint, not for date; this subject's best-scoring photograph is fourteen years old | camera/reference metadata |

## Re-render note, 2026-09-07

Re-rendered against the corrected `b_wtc_site` model — the World Trade Center site stood 3.5 m too high, its plaza was an unbroken 520 x 520 m quad over both memorial pools, and its 220 oaks each carried a merged impostor card (`docs/verification/landmarks/REPORT_B.md` §12). Measured against the shipped render, **0.000 %** of pixels differ by more than 8/255 and the largest single difference is **4/255**, which is Cycles sampling noise at 32 samples, not content; frame mean and standard deviation are unchanged (0.125 / 0.086). The camera did not move. Nothing in this assessment changes.
