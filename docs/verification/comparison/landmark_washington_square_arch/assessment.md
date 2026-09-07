# Washington Square Arch from the fountain

`landmark_washington_square_arch` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Washington Square Arch and the Empire State Building, Greenwich Village, Manhattan, New York.jpg by Christian David, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2026-04-16 18:16:58, 1920x2560. [Commons page](https://commons.wikimedia.org/wiki/File:Washington_Square_Arch_and_the_Empire_State_Building,_Greenwich_Village,_Manhattan,_New_York.jpg)

**Camera** — camera 40.73093, -73.99733 (NYC_TM -3998, 3435) z 10.2 m NAVD88 | azimuth 44.7deg pitch +0.0deg | 19 mm on 36 mm (70.0deg horizontal, 86.1deg vertical, portrait) | 904x1206. View direction: 44.7 deg, the bearing from this photograph's own GPS position to the Arch; heading and position both come from the photograph, 14 m from the item's recorded viewpoint.

**Sun** — azimuth 271.7°, elevation 14.1° at 2026-04-16T18:16:58-04:00 (EXIF DateTimeOriginal), with the view transform opened 1.61 stops as the light falls off.

**In frame** — 4/4 building tiles (424,964 tris), 1 landmark model, 1,210 pavement polygons, 708 props, 2,457 facade-kit pieces; 2,428,928 triangles; ground mesh 199² at 2.0 m near / 40.0 m far. Frame mean 0.697, sd 0.129.

**Verdict — the reference is now a photograph of the Arch. The sheet is no longer comparing two different views: the photograph is the Arch centred from the fountain plaza, looking north up Fifth Avenue with the Empire State Building through the opening, which is exactly what the item's viewpoint note describes. The render is still not that picture, because the heading is the bearing to a recorded subject coordinate that stands 15.0 m from the Arch model's own origin — at 39 m that is 15.8 deg, enough to swing the Arch off the frame centre and show it edge-on**

## What changed, and what it did not fix

The chooser had selected three photographs for this item — skateboarders at the fountain, a
balloon-animal seller and a distant view of 30 Hudson Yards — none of which contains the Arch. All
three satisfied the item's only keyword group, `"washington square"`, which names the *park*: 40,000 m²
of photographs that are not of the Arch. Each was then *aimed* at the Arch, because a camera GPS 27 m
from the recorded subject was read as a bearing to it.

The chooser now applies a subject test (`pipeline/nycsim_pipeline/reference/fetch_photos.py:
subject_named`): a photograph must name what the item is a view *of*, in its own title or description
and not in its categories, which record where a photograph *is* rather than what it is of. This item
declares `subject_terms=("arch", "washington arch")`. Re-running the chooser rejected **68** candidates
as `subject_not_named` and returned three that do name the Arch; the one this sheet uses is the best of
them by the existing preference order.

Measured before the change: a dry run of the same test over all 172 stored subjects dropped this one
and, with the street-view items fixed in the same pass, six in all — no photograph anywhere else in the
set moved silently.

**What it did not fix is the aim.** The item's recorded `subject` is 40.7311, -73.9971, and the
`b_washington_square_arch` model's own origin is 40.73123, -73.99710 — **15.0 m** apart. From this
camera the recorded point bears **44.7 deg** and the model bears **28.9 deg**, so the render is aimed
15.8 deg to the right of the thing it is a picture of, at 39 m. Aiming at the nearest landmark model
instead was measured across the 43 rendered subjects that have one in range and rejected: it would
swing 10 of them by more than 10 deg, including **174.8 deg** for the Hudson Yards Vessel and
**174.3 deg** for the Paramount Building, where the nearest model is a multi-building model whose
origin is not the subject. A correct fix needs a per-subject aim point, which is a pass of its own.

## What matches

The two frames are now of the same thing, from the same place, in the same light:

* **The camera stands where the photographer stood.** It is on the photograph's own EXIF GPS, 14 m from the item's nominal viewpoint, on the paved rim of the fountain plaza, in open air, with 77 m of clear view along the azimuth and the nearest solid thing — a bishop's-crook lamp standard — 17 m away. The clearance search left it untouched, correctly.
* **The light matches.** The Sun is placed from the photograph's own timestamp: 14.3 deg elevation, azimuth 271.5, a late-afternoon April sun almost due west, with the view transform opened 1.60 stops to hold it. Both frames are bright, low-contrast and raking, and of the five sheets written in this pass this is the closest tonal match.
* **The park's plane trees render correctly.** Irregular green crowns with visible leaf clumps and gaps between them, correctly scaled against the lamp standards. This is the near-field, sunlit case; the same library's trees at 200 m and in shade read as opaque dark cones (see the Williamsburg Bridge sheet), so the assets are right and the reading depends on distance and light.
* **The Arch is in the frame**, left of centre where the 15.8 deg aim error puts it: the model's west pier and the marble mass above it, seen from the south-west and nearly edge-on, so the opening the photograph looks through is turned away from the lens.

## What does not match

* **The Arch is 15.8 deg off centre and turned edge-on**, because the heading is the bearing to a
  recorded subject coordinate 15.0 m from where the model stands (see above). The photograph is
  square-on to the south face with the opening dead centre; the render sees the south-west corner.
  The two frames are of the same object and not of the same face of it.
* **The frame cannot contain the Arch's top.** The model's published 23 m stands 22 m above the lens at
  27 m, which needs 38 deg of elevation; the lens was widened to 19 mm and a level axis gives 43 deg
  vertically from centre, so the attic is in frame but the Empire State Building the photograph frames
  through the opening is not, because the opening is not facing the camera.
* **The fountain is not in either the render or the model.** It is the whole foreground of the photograph — a 30 m granite basin with a raised centre plinth, ringed by stepped seating full of people. The render's foreground is an unbroken pale plane: the fountain and its steps are neither a building nor a road polygon, so no stage produces them.
* The bottom 55 % of the render is that blank plane. Pavement polygons carry a flat per-kind colour, so the plaza's radial paving pattern — which is the strongest graphic element in the photograph — is absent.
* No people. The photograph has upwards of a hundred, and they are the subject.
* The buildings around the square are flat pastel massing blocks. The photograph's are brick, glass and metal screen with strong modelling; the render has no facade texture and no glass. The terracotta-pink mass filling the render's left half has no counterpart in the photograph at all, because the two frames are looking at different quadrants of the park.
* **Even the part of the Arch that is in frame is truncated.** The model's published height is 23 m and it stands 22 m above the lens at 27 m, which needs 38 deg of elevation against the 36.9 deg the 18 mm frame gives vertically.
* The pier is plain white marble with a simple cornice. The real Arch carries the spandrel figures, the two Washington reliefs, the frieze and inscription, an egg-and-dart cornice and a full attic. None of that is modelled.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| ~~the reference photograph does not contain the subject~~ | **fixed**: the chooser now requires a photograph to name what the item is a view of, in its own title or description; 68 candidates were rejected on it here | camera/reference metadata |
| the render is aimed 15.8 deg off the Arch | the item's recorded `subject` coordinate is 15.0 m from the Arch model's own origin, and the heading is the bearing to the coordinate | reference metadata |
| the top of the Arch is cut off | the level-axis rule at the 18 mm floor: 23 m of Arch at 27 m needs 38 deg and the frame gives 36.9 deg vertically | camera/reference metadata |
| the Arch has no reliefs, frieze, inscription or attic | the `b_washington_square_arch` model is a massing model in marble; no stage carves sculpture | geometry |
| no fountain, no stepped seating, no radial paving | the fountain is neither a building footprint nor a DoITT pavement polygon, so no stage produces it; the plaza is drawn as one flat polygon | geometry |
| flat pastel buildings around the square | building shells carry a per-material base colour with no facade texture and no glass BSDF | material |
| no people | no stage places people into a still verification frame | data |
