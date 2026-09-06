# World Trade Center Transportation Hub (Oculus)

`landmark_oculus` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Oculus (36813913993).jpg by Billie Grace Ward from New York, USA, CC BY 2.0 (https://creativecommons.org/licenses/by/2.0), taken 2017-08-15 08:32, 1920x1281. [Commons page](https://commons.wikimedia.org/wiki/File:Oculus_(36813913993).jpg)

**Camera** — camera 40.71145, -74.01030 (NYC_TM -5095, 1273) z 9.6 m NAVD88 | azimuth 274.2deg pitch -3.3deg | 35 mm on 36 mm (54.4deg horizontal) | 1280x854. View direction: 274.2 deg, the bearing from this photograph's own GPS position to the Oculus; heading and position both come from the photograph.  The item's recorded azimuth is 282.4 deg, 8.2 deg away, and belongs to its nominal viewpoint. Aim: aimed at the Oculus 76 m away, at its mid-height (a nominal 10 m subject); -3.3 deg from horizontal.

**Sun** — azimuth 94.1°, elevation 26.3° at 2017-08-15T08:32:00-04:00 (EXIF DateTimeOriginal (minutes)).

**In frame** — 4/4 building tiles (82,358 tris), 12 landmark models, 1,588 pavement polygons, 617 props, 8,287 facade-kit pieces; 3,698,131 triangles; ground mesh 201² at 2.0 m near / 40.0 m far.

**Verdict — the Oculus's rib cage is modelled and unmistakable — white steel ribs rising and curving in the right rhythm — and it sits on a plaza that is a blank grey plane, with the ribs solid where the real ones enclose a glazed spine**

## What matches

* The Oculus is recognisably itself: the row of tapering white steel ribs, their spacing, their curve away from the spine and the way they meet the ground, all at the right scale 76 m from the camera.
* The camera stands on the photograph's own EXIF GPS, 30 m from the item's nominal viewpoint, and the heading (274.2 deg) is the bearing from that point to the structure; the aim rule tilted -3.3 deg.
* The plaza's kerb line and its sweeping curve are correct, and the pale paving of the WTC plaza reads at the right width against the darker roadbed.
* 12 landmark models are in range with their shells suppressed, including One World Trade Center and the memorial-side buildings, and the glazed tower behind the Oculus at the right height.
* 1,588 pavement polygons, 617 props and 8,287 kit pieces are placed, with lamps at the right spacing along the plaza edge.

## What does not match

* The ribs are solid white where the real structure is a rib cage over a glazed spine: there is no glass between the ribs, no skylight, and the interior is closed off.
* The reference is a near-vertical view along the ribs with One World Trade Center and 7 WTC rising behind; the render's level axis gives a side elevation instead, so the two are not comparable on composition.
* The plaza is a bare grey plane: no paving pattern, no benches, no planting, no memorial pools, no security bollards.
* No people at all, in front of a station used by 250,000 people a day.
* The glass towers behind have no reflections; the reference's are all reflection.
* The lens stayed at 35 mm because the model's height is read as a nominal 10 m subject — the c_oculus entry has no published height — so the structure's own top is cut by the frame edge rather than by a measured decision.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| solid ribs, no glazed spine | the oculus landmark model carries the ribs as solid geometry with no glazing between them | geometry |
| side elevation rather than the reference's upward view | the level-axis rule; the reference is a tilted upward frame | camera |
| bare plaza | plaza paving, furniture, planting and the memorial pools are in no dataset the scene reads | data |
| no people | no crowd placement feeds the verification scene | data |
| no glass reflections | the curtain-wall material is a flat base colour | material |
| lens not sized to the subject | the landmark catalogue entry carries no height, so the lens rule fell back to a nominal 10 m subject | data |
