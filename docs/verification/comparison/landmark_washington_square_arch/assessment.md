# Washington Square Arch from the fountain

`landmark_washington_square_arch` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Skateboarders at the central fountain, Washington Square Park, Manhattan, New York.jpg by Christian David, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2026-04-16 18:15:53, 1920x1440. [Commons page](https://commons.wikimedia.org/wiki/File:Skateboarders_at_the_central_fountain,_Washington_Square_Park,_Manhattan,_New_York.jpg)

**Camera** — camera 40.73093, -73.99733 (NYC_TM -3998, 3435) z 10.2 m NAVD88 | azimuth 44.7deg pitch +0.0deg | 18 mm on 36 mm (90.0deg horizontal) | 1208x906. View direction: 44.7 deg, the bearing from this photograph's own GPS position to the Arch; heading and position both come from the photograph, 14 m from the item's recorded viewpoint. The item's recorded azimuth is 26.8 deg, 17.9 deg away. Aim: level optical axis; the lens was widened from 35 mm to the 18 mm floor and the top of the subject is still cut off.

**Sun** — azimuth 271.5°, elevation 14.3° at 2026-04-16T18:15:53-04:00 (EXIF DateTimeOriginal), with the view transform opened 1.60 stops as the light falls off.

**In frame** — 4/4 building tiles (315,354 tris), 1 landmark model, 1,210 pavement polygons, 717 props, 2,457 facade-kit pieces; 2,357,850 triangles; ground mesh 199² at 2.0 m near / 40.0 m far. The props were capped by the 1,404,555-triangle budget.

**Verdict — this sheet compares two different views. The photograph does not contain the Washington Square Arch: it looks the other way, across the fountain at Judson Memorial Church's campanile and the NYU blocks on Washington Square South. The render is aimed at the Arch because the azimuth was derived by assuming the photographer faced the item's subject, and that assumption is false here**

## What matches

Little, because the two frames face different ways. Three things can still be checked, and all three are right:

* **The camera stands where the photographer stood.** It is on the photograph's own EXIF GPS, 14 m from the item's nominal viewpoint, on the paved rim of the fountain plaza, in open air, with 77 m of clear view along the azimuth and the nearest solid thing — a bishop's-crook lamp standard — 17 m away. The clearance search left it untouched, correctly.
* **The light matches.** The Sun is placed from the photograph's own timestamp: 14.3 deg elevation, azimuth 271.5, a late-afternoon April sun almost due west, with the view transform opened 1.60 stops to hold it. Both frames are bright, low-contrast and raking, and of the five sheets written in this pass this is the closest tonal match.
* **The park's plane trees render correctly.** Irregular green crowns with visible leaf clumps and gaps between them, correctly scaled against the lamp standards. This is the near-field, sunlit case; the same library's trees at 200 m and in shade read as opaque dark cones (see the Williamsburg Bridge sheet), so the assets are right and the reading depends on distance and light.
* Aimed at 44.7 deg the render does contain part of its nominal subject: the Arch's **east pier seen almost edge-on from the south-east**, with the springing of the vault and one fluted column behind it. It is the right pier in the right place.

## What does not match

* **The subject is absent from the reference.** The photograph is a wide view across the fountain basin at skateboarders, with Judson Memorial Church's brick campanile and the Washington Square South blocks behind. The Arch stands behind and to the left of the photographer. The comparison therefore cannot test the Arch at all.
* **The azimuth is wrong for this photograph and the metadata cannot know it.** `estimated_viewpoint.azimuth_deg` is computed as `camera_gps_to_subject` — the bearing from the camera's GPS to the item's recorded subject (44.5 deg, and the render's own recomputation gives 44.7 deg). That is a sound rule for a photograph *of* the subject. This photograph is of the fountain, so the rule produces a heading roughly 130 deg from where the camera actually pointed. The item's own recorded azimuth (26.8 deg) is no better: it also faces the Arch.
* **The fountain is not in either the render or the model.** It is the whole foreground of the photograph — a 30 m granite basin with a raised centre plinth, ringed by stepped seating full of people. The render's foreground is an unbroken pale plane: the fountain and its steps are neither a building nor a road polygon, so no stage produces them.
* The bottom 55 % of the render is that blank plane. Pavement polygons carry a flat per-kind colour, so the plaza's radial paving pattern — which is the strongest graphic element in the photograph — is absent.
* No people. The photograph has upwards of a hundred, and they are the subject.
* The buildings around the square are flat pastel massing blocks. The photograph's are brick, glass and metal screen with strong modelling; the render has no facade texture and no glass. The terracotta-pink mass filling the render's left half has no counterpart in the photograph at all, because the two frames are looking at different quadrants of the park.
* **Even the part of the Arch that is in frame is truncated.** The model's published height is 23 m and it stands 22 m above the lens at 27 m, which needs 38 deg of elevation against the 36.9 deg the 18 mm frame gives vertically.
* The pier is plain white marble with a simple cornice. The real Arch carries the spandrel figures, the two Washington reliefs, the frieze and inscription, an egg-and-dart cornice and a full attic. None of that is modelled.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the reference photograph does not contain the subject | the reference chooser scores photographs by licence, size, date and geosearch proximity, not by whether the subject is in the frame; this file scored 14.2 on a subject it does not show | camera/reference metadata |
| the render's heading is ~130 deg from where the photographer actually pointed | `camera_gps_to_subject` assumes a photograph taken at a viewpoint is a photograph *of* that viewpoint's subject. There is no EXIF field for heading in this file, so nothing in the pipeline can detect the failure | camera/reference metadata |
| the top of the Arch is cut off | the level-axis rule at the 18 mm floor: 23 m of Arch at 27 m needs 38 deg and the frame gives 36.9 deg vertically | camera/reference metadata |
| the Arch has no reliefs, frieze, inscription or attic | the `b_washington_square_arch` model is a massing model in marble; no stage carves sculpture | geometry |
| no fountain, no stepped seating, no radial paving | the fountain is neither a building footprint nor a DoITT pavement polygon, so no stage produces it; the plaza is drawn as one flat polygon | geometry |
| flat pastel buildings around the square | building shells carry a per-material base colour with no facade texture and no glass BSDF | material |
| no people | no stage places people into a still verification frame | data |
