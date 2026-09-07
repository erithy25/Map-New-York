# Manhattan Bridge

`landmark_manhattan_bridge` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:View from the Manhattan Bridge 012.jpg by Kidfly182, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2023-01-18 12:00:51, 1920x1440. [Commons page](https://commons.wikimedia.org/wiki/File:View_from_the_Manhattan_Bridge_012.jpg)

**Camera** — camera 40.70405, -73.99104 (NYC_TM -3468, 451) z 1.6 m NAVD88 | azimuth 66.3deg pitch +2.9deg | 35 mm on 36 mm (54.4deg horizontal) | 1208x906. View direction: 66.3 deg, the bearing from this photograph's own GPS position to Manhattan Bridge Brooklyn tower; heading and position both come from the photograph.  The item's recorded azimuth is 74.0 deg, 7.7 deg away, and belongs to its nominal viewpoint. Aim: aimed at Manhattan Bridge Brooklyn tower 123 m away, at its mid-height (a nominal 10 m subject); +2.9 deg from horizontal.

**Sun** — azimuth 178.5°, elevation 28.8° at 2023-01-18T12:00:51-05:00 (EXIF DateTimeOriginal).

**In frame** — 5/5 building tiles (152,890 tris), 2 landmark models, 1,386 pavement polygons, 483 props, 2,495 facade-kit pieces; 2,159,599 triangles; ground mesh 205² at 2.0 m near / 40.0 m far.

**Verdict — the bridge's approach truss, deck and tower pier are modelled and correctly placed, seen from a camera standing at the waterline — and the reference is an aerial photograph taken from the bridge itself, of a tanker, so the two have nothing in common**

## What matches

* The Manhattan Bridge's Brooklyn approach is modelled with real structure: a Warren truss with correct diagonal web members, the deck it carries, the lamp standards along its edge, and the masonry pier taking it down to the ground.
* The camera stands on the photograph's own EXIF GPS, 82 m from the item's nominal viewpoint, and the heading (66.3 deg) is the bearing from there to the Brooklyn tower 123 m away.
* The eye height is correct for the shoreline: 1.6 m above a 0.0 m NAVD88 ground, which is the waterline at Pebble Beach.
* The water surface reaches the right level and the shoreline crosses the frame where the terrain says it does.
* 1,386 pavement polygons and 483 props are placed, with lamps along the esplanade and 11 opaque impostor cards dropped.

## What does not match

* The two halves are unrelated. The item looks at the bridge from the park; the photograph is taken *from* the bridge, looking down at an oil tanker on the East River. There is no comparison to make.
* The tower pier is a plain grey block: no granite courses, no arched openings, no cornice, no detail of any kind.
* The truss has no rivets, no gusset plates, no paint variation and no rust; it is one flat colour.
* The water is a mirror with no waves, no wake, no vessels, and no ice. The reference's water is the entire subject of its lower half.
* Brooklyn Bridge Park is a blank plane: no shingle beach, no railings, no planting, no people.
* The buildings behind are flat pastel solids with no glazing.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the two halves are unrelated | the reference stage paired a from-the-park item with a from-the-bridge photograph and assumed its direction | reference |
| plain tower pier, undetailed truss | the b_manhattan_bridge model carries the structural form with a flat base colour and no architectural or fabrication detail | geometry |
| mirror water, no vessels | the water material has no wave normal, and no stage places boats | material |
| no park surfacing, railings, planting or people | park structures and crowds are in no dataset the scene reads | data |
| flat buildings | shells carry a per-material base colour with no glass | material |
