# Museum of Modern Art

`landmark_moma` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Museum of Modern Art (MoMA) (51395759113).jpg by ajay_suresh, CC BY 2.0 (https://creativecommons.org/licenses/by/2.0), taken 2021-08-21 15:18, 1920x1920. [Commons page](https://commons.wikimedia.org/wiki/File:Museum_of_Modern_Art_(MoMA)_(51395759113).jpg)

**Camera** — camera 40.76129, -73.97775 (NYC_TM -2379, 6823) z 21.4 m NAVD88 | azimuth 24.6deg pitch +0.0deg | 18 mm on 36 mm (90.0deg horizontal) | 1044x1044. View direction: 24.6 deg, the bearing from this photograph's own GPS position to Museum of Modern Art; heading and position both come from the photograph.  The item's recorded azimuth is 0.0 deg, 24.6 deg away, and belongs to its nominal viewpoint. Aim: level optical axis (Museum of Modern Art is 50 m away and would need +36 deg of tilt; a real frame would use a wider lens instead, and a tilted axis would stop the render being comparable on proportion).

**Sun** — azimuth 236.5°, elevation 48.0° at 2021-08-21T15:18:00-04:00 (EXIF DateTimeOriginal (minutes)).

**In frame** — 4/4 building tiles (163,194 tris), 9 landmark models, 959 pavement polygons, 511 props, 14,262 facade-kit pieces; 4,371,973 triangles; ground mesh 199² at 2.0 m near / 40.0 m far.

**Camera clearance** — the recorded viewpoint is inside lm_moma.15 (a ray straight up from the eye point hits its roof); the camera was moved 40 m to the left -- the nearest point in open air -- keeping the same eye height above the heightmap.  The view azimuth is clear for 37 m from there

**Verdict — raised from pure black (0.005) to barely legible (0.079) by pulling the camera out of the building it was standing inside; what is now visible is a fire hydrant, a sidewalk and the diagonal bracing of a tower in deep shadow — the museum itself is not identifiable**

## What matches

* The camera correction worked and is stated: the recorded viewpoint sits inside a building shell, and the camera was moved onto the nearest real pavement polygon with 37 m of clear view against the 25 m this subject needs. The orchestrator's sweep had this frame at mean 0.005.
* What can be seen is real: the diagonal steel bracing and curtain-wall grid of the tower behind MoMA, the museum's own block edge, a fire hydrant at the correct 0.75 m height and colour, and the sidewalk with its kerb reveal.
* The heading and the lens are both derived rather than assumed, and 9 landmark models are in range with their shells suppressed.
* 977 pavement polygons carry the West 53rd Street geometry.

## What does not match

* Mean luminance 0.079 against a 0.06 floor. West 53rd Street is a 20 m canyon between 200 m towers and the Sun is behind them; the render is honest and almost unreadable.
* MoMA's own facade — the glass and black granite screen, the entrance canopy, the museum's name in steel letters — is not identifiable in the frame.
* No people, no vehicles, no banners, no signage, and none of the street life the reference carries.
* Nothing in the frame has any surface: the walls are unlit flat planes and the glazing has no reflectance.
* The reference and the render are of different things again: the item names no measured direction for the photograph.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| frame almost unreadable | a 20 m canyon between 200 m towers with the Sun behind them and two light bounces | lighting |
| the museum facade is not identifiable | the moma landmark model carries massing without the screen wall, canopy or lettering | geometry |
| no people, vehicles or banners | no stage places any of them | data |
| no reflectance on the glazing | the curtain-wall material is a flat base colour | material |
