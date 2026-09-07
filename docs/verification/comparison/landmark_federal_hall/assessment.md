# Federal Hall National Memorial

`landmark_federal_hall` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Financial District, New York, NY, USA - panoramio - Sergei Gussev (34).jpg by Sergei Gussev, CC BY 3.0 (https://creativecommons.org/licenses/by/3.0), taken 2016, 1920x1440. [Commons page](https://commons.wikimedia.org/wiki/File:Financial_District,_New_York,_NY,_USA_-_panoramio_-_Sergei_Gussev_(34).jpg)

**Camera** — camera 40.70686, -74.01024 (NYC_TM -5120, 781) z 8.2 m NAVD88 | azimuth 355.0deg pitch +0.0deg | 26 mm on 36 mm (68.7deg horizontal) | 1208x906. View direction: 355.0 deg as recorded; it agrees with the bearing from the camera position used to Federal Hall National Memorial (355.1 deg) to 0.1 deg. Aim: level optical axis (Federal Hall National Memorial is 40 m away and would need +12 deg of tilt; a real frame would use a wider lens instead, and a tilted axis would stop the render being comparable on proportion).

**Sun** — azimuth 95.3°, elevation 43.5° at 2016-06-21T09:30:00-04:00 (photograph year only; 21 June 09:30 assumed).

**In frame** — 4/4 building tiles (82,358 tris), 10 landmark models, 1,768 pavement polygons, 517 props, 11,710 facade-kit pieces; 4,500,174 triangles; ground mesh 199² at 2.0 m near / 40.0 m far.

**Camera clearance** — the recorded viewpoint is boxed in: the view azimuth is closed off 12 m ahead, less than the 29 m this frame needs to show its subject; the camera was moved 33 m onto the nearest real roadbed polygon in data/processed/roads/pavement, keeping the same eye height above the heightmap.  The view azimuth is clear for 60 m from there

**Verdict — the camera was moved 33 m to escape a wall 12 m ahead and Federal Hall is still not in the frame; what is left is an unlit Wall Street corner at mean luminance 0.099, and the reference is a sunlit Doric portico with a hundred people on its steps**

## What matches

* The origin rule chose correctly and says why: this photograph's own EXIF GPS is only 20 m away but the eye point there is inside t_-6_0_roof_membrane, while the item's recorded viewpoint is in open air, so the recorded one was used.
* The boxed-in test fired: the view azimuth was closed off 12 m ahead against the 29 m this subject needs, and the camera was moved 33 m onto the nearest real roadbed with 60 m of clear view.
* The lens rule widened 35 mm to 26 mm so that a level axis contains the 19 m building 40 m away, 24 deg above the horizon — the one case in the set where the widening is modest and exact rather than clamped at the floor.
* The heading agrees to 0.1 deg with the bearing to Federal Hall, and 10 landmark models are in range.
* A lit shopfront band and a bishop's-crook lamp are correctly placed, and 1,768 pavement polygons carry the crossing geometry.

## What does not match

* Federal Hall is not in the frame. The item exists to test its Doric portico and the Washington statue, and the render shows a building corner 30 m to the side of it.
* Mean luminance 0.099. Wall Street at Broad under 100 m walls at a 43 deg Sun is genuinely this dark, and the Sun position is itself an assumption: the photograph records only a year (2016), so the fallback of 09:30 on 21 June was used. That is stated on the sheet but it makes the lighting incomparable.
* The reference's whole content — the portico's eight Doric columns, the pediment, the banners, the statue, the steps and about a hundred people — has no counterpart.
* No people, no vehicles, no steam plume from the manhole that dominates the reference's left third.
* The facades carry no glazing, no stone and no mouldings.
* The facade kit was capped by the triangle budget at 11,710 of 23,336 records in range — half the wall detail within 120 m.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| Federal Hall not in frame | the corrected camera has a clear azimuth but no line of sight to the subject; the clearance test measures free distance, not visibility of the subject | camera |
| frame too dark, and the Sun is a guess | a 100 m canyon at street level, and a photograph with only a year recorded so the Sun is the 09:30 21 June fallback | lighting |
| no portico, statue, banners or people | the subject is out of frame, and no crowd placement feeds the verification scene | data |
| no steam plume | props.parquet carries steam_vent rows and the kit exports a stack, but no plume effect exists | geometry |
| no glazing or stone | shells carry a per-material base colour; the kit supplies openings without glass | material |
| half the facade kit not drawn | the 4.5 M triangle budget is spent before the kit finishes | geometry |

## Re-render note, 2026-09-07

Re-rendered against the corrected `b_wtc_site` model — the World Trade Center site stood 3.5 m too high, its plaza was an unbroken 520 x 520 m quad over both memorial pools, and its 220 oaks each carried a merged impostor card (`docs/verification/landmarks/REPORT_B.md` §12). Measured against the shipped render, **0.001 %** of pixels differ by more than 8/255 and the largest single difference is **20/255**, which is Cycles sampling noise at 32 samples, not content; frame mean and standard deviation are unchanged (0.099 / 0.063). The camera did not move. Nothing in this assessment changes.
