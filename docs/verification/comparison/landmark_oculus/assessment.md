# World Trade Center Transportation Hub (Oculus)

`landmark_oculus` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Oculus (36813913993).jpg by Billie Grace Ward from New York, USA, CC BY 2.0 (https://creativecommons.org/licenses/by/2.0), taken 2017-08-15 08:32, 1920x1281. [Commons page](https://commons.wikimedia.org/wiki/File:Oculus_(36813913993).jpg)

**Camera** — camera 40.71145, -74.01030 (NYC_TM -5095, 1273) z 9.6 m NAVD88 | azimuth 274.2deg pitch -0.3deg | 35 mm on 36 mm (54.4deg horizontal) | 1280x854. View direction: 274.2 deg, the bearing from this photograph's own GPS position to the Oculus; heading and position both come from the photograph.  The item's recorded azimuth is 282.4 deg, 8.2 deg away, and belongs to its nominal viewpoint. Aim: aimed at the Oculus 76 m away, at its mid-height (a nominal 10 m subject); -0.3 deg from horizontal.

**Sun** — azimuth 94.1°, elevation 26.3° at 2017-08-15T08:32:00-04:00 (EXIF DateTimeOriginal (minutes)).

**In frame** — 4/4 building tiles, 12 landmark models, 1,588 pavement polygons, 617 props, 8,287 facade-kit pieces; 3,713,979 triangles; ground mesh 201² at 2.0 m near / 40.0 m far. Frame mean 0.368, sd 0.165 (0.381 / 0.157 before this pass; 46.7 % of pixels differ by more than 8/255).

**Verdict — re-rendered 2026-09-07 with the Oculus on its own footprint's axis. The building is now the right shape in plan and is seen the way it is seen from Church Street: end-on, its near end 57 m from the camera and its far end 142 m away, the rib cage running back and away instead of standing across the view. It is still unmistakably the Oculus, still solid where the real one encloses a glazed spine, and still standing on a blank grey plane**

## What moved in this frame, and why

**The Oculus was rotated 32.4 deg onto its own footprint.** The model built the 106.7 m ribbed body on
`PLAZA_AXIS_DEG = 160.6`; the long axis of BIN 1089309, the footprint it is centred on, measures
**128.2 deg** (minimum rotated rectangle 110.0 × 33.3 m; the polygon's area-weighted principal axis
gives 128.8 deg). The camera stands 93.7 m from the footprint centroid on bearing 275.6 deg, so the
rotation is not a subtlety here — it moves both ends of the building:

| | on 160.6 deg | on 128.2 deg |
|---|---|---|
| near end | bearing 241.4 deg, **86.0 m** away | bearing 245.1 deg, **56.6 m** away |
| far end | bearing 298.2 deg, 126.0 m away | bearing 287.3 deg, **141.6 m** away |

The body therefore reads as running back and away from the camera rather than lying across the view,
and the frame's near end is 29 m closer than it was. **46.7 %** of pixels differ from the shipped
render by more than 8/255. In plan the correction takes the body from **58.0 %** of its area over its
own footprint (IoU 0.41, both ends about 17 m outside it, 231 m² of the base prism inside 3 WTC's
footprint) to **94.2 %** (IoU 0.90, no overlap with 3 WTC or 4 WTC at all).

Not all of the change is the Oculus: the building-shell stage rebuilt its stepped massing during the
same window, and the skyline behind the Oculus moves with it. What is attributable to this pass is
the geometry above, which is measured from the footprint parquet and the exported glb rather than
from pixels.

The camera has not moved: it is still the photograph's own EXIF GPS, 30 m from the item's nominal
viewpoint, at 9.60 m NAVD88, azimuth 274.2 deg, pitch −0.28 deg.

## What matches

* The Oculus is recognisably itself: the row of tapering white steel ribs, their spacing, their curve away from the spine and the way they meet the ground, at the right scale for a body whose near end is 57 m from the camera and whose far end is 142 m away.
* The camera stands on the photograph's own EXIF GPS, 30 m from the item's nominal viewpoint, and the heading (274.2 deg) is the bearing from that point to the structure; the aim rule tilted -0.3 deg.
* The plaza's kerb line and its sweeping curve are correct, and the pale paving of the WTC plaza reads at the right width against the darker roadbed.
* 12 landmark models are in range with their shells suppressed, including One World Trade Center and the memorial-side buildings, and the glazed tower behind the Oculus at the right height.
* 1,588 pavement polygons, 617 props and 8,287 kit pieces are placed, with lamps at the right spacing along the plaza edge.

## What does not match

* The ribs are solid white where the real structure is a rib cage over a glazed spine: there is no glass between the ribs, no skylight, and the interior is closed off.
* The body is a swept ellipse of the published 106.7 × 35.1 m on the footprint's axis, not the footprint's own outline, so **6 % of its plan still falls outside BIN 1089309**. That is the remaining approximation in the Oculus's plan; it was 42 % before this pass.
* The reference is a near-vertical view along the ribs with One World Trade Center and 7 WTC rising behind; the render's level axis gives a ground-level three-quarter view instead, so the two are not comparable on composition — they agree on the structure and not on the framing.
* The plaza is a bare grey plane: no paving pattern, no benches, no planting, no memorial pools, no security bollards.
* No people at all, in front of a station used by 250,000 people a day.
* The glass towers behind have no reflections; the reference's are all reflection.
* The lens stayed at 35 mm because the subject height is read as a nominal 10 m from the reference metadata rather than from the model, so the framing is not the result of a measured decision about the structure's real 51.2 m canopy tips.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| solid ribs, no glazed spine | the oculus landmark model carries the ribs as solid geometry with no glazing between them | geometry |
| ground-level three-quarter view rather than the reference's upward view | the level-axis rule; the reference is a tilted upward frame | camera |
| bare plaza | plaza paving, furniture, planting and the memorial pools are in no dataset the scene reads | data |
| no people | no crowd placement feeds the verification scene | data |
| no glass reflections | the curtain-wall material is a flat base colour | material |
| lens not sized to the subject | the reference metadata carries no subject height, so the lens rule fell back to a nominal 10 m subject | data |
| 6 % of the body's plan outside its footprint | the body is a swept ellipse of the published dimensions on the footprint's axis, not the footprint outline | geometry |
