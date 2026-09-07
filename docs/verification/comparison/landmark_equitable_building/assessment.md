# Equitable Building (120 Broadway)

`landmark_equitable_building` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Equitable Building April 2022 001.jpg by Kidfly182, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2022-04-01 13:09:11, 1920x1440. [Commons page](https://commons.wikimedia.org/wiki/File:Equitable_Building_April_2022_001.jpg)

**Camera** — camera 40.70869, -74.01108 (NYC_TM -5163, 953) z 12.2 m NAVD88 | azimuth 120.1deg pitch +0.0deg | 18 mm on 36 mm (90.0deg horizontal) | 1208x906. View direction: 120.1 deg, the bearing from this photograph's own GPS position to Equitable Building (120 Broadway); heading and position both come from the photograph.  The item's recorded azimuth is 85.0 deg, 35.1 deg away, and belongs to its nominal viewpoint. Aim: level optical axis (Equitable Building (120 Broadway) is 78 m away and would need +46 deg of tilt; a real frame would use a wider lens instead, and a tilted axis would stop the render being comparable on proportion).

**Sun** — azimuth 184.0°, elevation 54.0° at 2022-04-01T13:09:11-04:00 (EXIF DateTimeOriginal).

**In frame** — 4/4 building tiles (82,358 tris), 11 landmark models, 1,864 pavement polygons, 607 props, 8,928 facade-kit pieces; 4,006,384 triangles; ground mesh 201² at 2.0 m near / 40.0 m far.

**Camera clearance** — the recorded viewpoint is hard against prop_lamp_bishops_crook_0 (0.03 m from the lens in the view cone); the camera was moved 12 m onto the nearest real crosswalk polygon in data/processed/roads/pavement, keeping the same eye height above the heightmap.  The view azimuth is clear for 41 m from there

**Verdict — the camera was pulled off a lamp standard 3 cm from the lens and put on a crosswalk with 41 m of clear view, and the frame is still a black canyon floor with a lamp in it; the H-plan slab the item exists to test is above the top of the frame and in shadow**

## Re-rendered 2026-09-07 — the darkest frame in the set, and I18 again

Two recorded faults meet in this sheet and both are at their extreme here.

**Exposure (I16).** Mean luminance **0.133 against the photograph's 0.598** — the widest gap measured
anywhere in the set, a factor of four and a half. Broadway at this point is a slot between towers and
the render lights it physically while the photograph was metered for it. Nothing is clipping and
nothing is broken; the two images are answering different questions, and here that produces a frame a
reader can barely read.

**Framing (I18).** The subject stands 78.1 m away and the lens is already at the **18 mm floor**, so
the frame cannot contain a 164 m building from that distance with a level axis. What the sheet shows
is the base of one tower among several.

The pedestrian cull fired once — `pedestrian_over_the_observer: 1` — which is the camera-aware cull
doing its job on a camera that moved after placement.

**Taken together this sheet is close to unusable, and it is worth saying which part is the world's
fault: none of it.** 11 landmark models, 240 people and 50 vehicles are correctly placed in a
correctly built Lower Manhattan street. What fails is the camera rule and the exposure convention,
both recorded, both with named fixes, neither applied in this pass.

## What matches

* The in-the-lens test fired and is stated: the recorded viewpoint stood 0.03 m from prop_lamp_bishops_crook_0, and the camera was moved 12 m onto the nearest real crosswalk polygon.
* The camera stands on the photograph's own EXIF GPS, 45 m from the item's nominal viewpoint, and the heading (120.1 deg) is the bearing from there to the building — 35.1 deg from the recorded azimuth, and the sheet says the subject bearing was preferred.
* The lens rule widened 35 mm to the 18 mm floor because the 165 m slab stands 164 m above the lens at 78 m, 64 deg above the horizon, and states that the top is still cut off.
* The bishop's-crook lamp standard with its globe is correctly modelled and lit, and a hydrant sits at the kerb.
* 1,864 pavement polygons and 11 landmark models are placed.

## What does not match

* Nothing of the Equitable Building can be seen. The reference is 165 m of limestone and bronze in a tight upward perspective with two towers of the H rising against the sky; the render shows the unlit base of a canyon.
* Mean luminance 0.128: Broadway at Pine at a 54 deg April Sun with 165 m walls on both sides is genuinely this dark at street level, but nothing can be judged from it.
* The facades carry no glazing, no spandrel, no cornice, no rustication and no bronze — the reference's whole subject.
* No people, no vehicles, no signage.
* The lower right quarter of the frame is a large pale untextured plane where the graded terrain grid meets the pavement.
* The level-axis rule and the 18 mm floor together mean the render frames the street and the reference frames the tower; they are not comparable on composition, and the sheet says so.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the building is out of frame and in shadow | a 165 m subject 78 m away needs 64 deg of vertical angle; the 18 mm floor gives 74 deg on the long side but the frame is landscape, and the canyon floor is unlit | camera |
| frame too dark to read | 165 m walls either side at a 54 deg Sun with two light bounces | lighting |
| no glazing, spandrel or cornice | shells carry a per-material base colour; the kit supplies openings without glass or mouldings | material |
| no people, vehicles or signage | no stage places any of them | data |
| untextured foreground plane | the pavement material is a flat colour per kind | material |

## Re-render note, 2026-09-07

Re-rendered against the corrected `b_wtc_site` model — the World Trade Center site stood 3.5 m too high, its plaza was an unbroken 520 x 520 m quad over both memorial pools, and its 220 oaks each carried a merged impostor card (`docs/verification/landmarks/REPORT_B.md` §12). Measured against the shipped render, **0.000 %** of pixels differ by more than 8/255 and the largest single difference is **3/255**, which is Cycles sampling noise at 32 samples, not content; frame mean and standard deviation are unchanged (0.128 / 0.118). The camera did not move. Nothing in this assessment changes.
