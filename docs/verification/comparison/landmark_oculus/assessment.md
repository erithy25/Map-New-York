# World Trade Center Transportation Hub (Oculus)

`landmark_oculus` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Oculus (36813913993).jpg by Billie Grace Ward from New York, USA, CC BY 2.0 (https://creativecommons.org/licenses/by/2.0), taken 2017-08-15 08:32, 1920x1281. [Commons page](https://commons.wikimedia.org/wiki/File:Oculus_(36813913993).jpg)

**Camera** — camera 40.71145, -74.01030 (NYC_TM -5095, 1273) z 9.6 m NAVD88 | azimuth 274.2deg pitch -0.3deg | 35 mm on 36 mm (54.4deg horizontal) | 1280x854. View direction: 274.2 deg, the bearing from this photograph's own GPS position to the Oculus; heading and position both come from the photograph.  The item's recorded azimuth is 282.4 deg, 8.2 deg away, and belongs to its nominal viewpoint. Aim: aimed at the Oculus 76 m away, at its mid-height (a nominal 10 m subject); -0.3 deg from horizontal.

**Sun** — azimuth 94.1°, elevation 26.3° at 2017-08-15T08:32:00-04:00 (EXIF DateTimeOriginal (minutes)).

**In frame** — 4/4 building tiles (82,358 tris), 12 landmark models, 1,588 pavement polygons, 617 props, 8,287 facade-kit pieces; 3,698,245 triangles; ground mesh 201² at 2.0 m near / 40.0 m far. Frame mean 0.381, sd 0.157 (was 0.369 / 0.151).

**Verdict — re-rendered 2026-09-07 against the corrected World Trade Center model: the rib cage now stands clear of the top of the frame with sky above its arch, where it used to be cut off. It is still unmistakably the Oculus — white steel ribs rising and curving in the right rhythm — still solid where the real ones enclose a glazed spine, and still standing on a blank grey plane**

## What moved in this frame, and why

Two changes of roughly equal size, only one of them from the World Trade Center model:

* **The model dropped 3.5 m.** `b_wtc_site` was built with `GRND = 3.5` doing duty both as its local datum and as its frame origin's NAVD88 z, so `scene.py`'s `world = local + origin` counted the plaza level twice (`docs/verification/landmarks/REPORT_B.md` §12.1). At 76 m, 3.5 m subtends 2.6 deg — the structure sits that much lower in the frame.
* **The aim moved 3.0 deg.** Pitch goes from -3.3 deg to -0.3 deg. That is the street-percentile void exclusion recorded in `docs/verification/comparison/REPORT.md` §2.6, which changes the ground read at the subject point; it was already pending before this pass and is not a consequence of the model fix. The camera position is identical to the metre.

Together they lift the Oculus about 5.6 deg (roughly 130 px) further down the frame, which is why the crown of the near arch and the sky behind it are now in shot. The plaza clip in the same model pass has no effect here: the old 520 m slab stood at 7.00 m NAVD88 and the ground under this camera reads 8.00 m, so it was buried, and the pale paving in both frames comes from `data/processed/roads/pavement`, not from the landmark.

## What matches

* The Oculus is recognisably itself: the row of tapering white steel ribs, their spacing, their curve away from the spine and the way they meet the ground, all at the right scale 76 m from the camera.
* The camera stands on the photograph's own EXIF GPS, 30 m from the item's nominal viewpoint, and the heading (274.2 deg) is the bearing from that point to the structure; the aim rule tilted -0.3 deg.
* The plaza's kerb line and its sweeping curve are correct, and the pale paving of the WTC plaza reads at the right width against the darker roadbed.
* 12 landmark models are in range with their shells suppressed, including One World Trade Center and the memorial-side buildings, and the glazed tower behind the Oculus at the right height.
* 1,588 pavement polygons, 617 props and 8,287 kit pieces are placed, with lamps at the right spacing along the plaza edge.

## What does not match

* The ribs are solid white where the real structure is a rib cage over a glazed spine: there is no glass between the ribs, no skylight, and the interior is closed off.
* **The body is 32 deg off its own footprint.** The model orients the 106.7 m ellipse on `PLAZA_AXIS_DEG = 160.6`, while the long axis of the real OTI footprint it is built on (BIN 1089309, 110.0 m) measures **128.2 deg**. That is not visible as a wrong shape from this viewpoint — the rib rhythm and the arch profile still read — but it is a wrong plan, and it puts the east end of the body inside 3 WTC's footprint. Found and measured in the landmarks pass of 2026-09-07 and deliberately left unfixed there, because it moves this frame and belongs to a pass that re-renders it against the reference.
* The reference is a near-vertical view along the ribs with One World Trade Center and 7 WTC rising behind; the render's level axis gives a side elevation instead, so the two are not comparable on composition.
* The plaza is a bare grey plane: no paving pattern, no benches, no planting, no memorial pools, no security bollards.
* No people at all, in front of a station used by 250,000 people a day.
* The glass towers behind have no reflections; the reference's are all reflection.
* The lens stayed at 35 mm because the subject height is read as a nominal 10 m from the reference metadata rather than from the model, so the framing is not the result of a measured decision about the structure's real 51.2 m canopy tips.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| solid ribs, no glazed spine | the oculus landmark model carries the ribs as solid geometry with no glazing between them | geometry |
| side elevation rather than the reference's upward view | the level-axis rule; the reference is a tilted upward frame | camera |
| bare plaza | plaza paving, furniture, planting and the memorial pools are in no dataset the scene reads | data |
| no people | no crowd placement feeds the verification scene | data |
| no glass reflections | the curtain-wall material is a flat base colour | material |
| lens not sized to the subject | the reference metadata carries no subject height, so the lens rule fell back to a nominal 10 m subject | data |
| the body is rotated 32 deg off its real footprint | `b_wtc_site.py` orients the Oculus on `PLAZA_AXIS_DEG = 160.6`; the footprint's long axis is 128.2 deg | geometry |
