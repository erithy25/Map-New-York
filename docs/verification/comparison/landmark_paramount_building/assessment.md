# Paramount Building (1501 Broadway)

`landmark_paramount_building` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Paramount Building Times Square.jpg by Kidfly182, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2021-08-25 12:41:13, 1920x1440. [Commons page](https://commons.wikimedia.org/wiki/File:Paramount_Building_Times_Square.jpg)

**Camera** — camera 40.75666, -73.98644 (NYC_TM -3077, 6292) z 17.4 m NAVD88 | azimuth 4.1deg pitch +0.0deg | 18 mm on 36 mm (90.0deg horizontal) | 1208x906. View direction: 4.1 deg, the bearing from this photograph's own GPS position to Paramount Building (1501 Broadway); heading and position both come from the photograph.  The item's recorded azimuth is 210.0 deg, 154.1 deg away, and belongs to its nominal viewpoint. Aim: level optical axis (Paramount Building (1501 Broadway) is 63 m away and would need +71 deg of tilt; a real frame would use a wider lens instead, and a tilted axis would stop the render being comparable on proportion).

**Sun** — azimuth 171.9°, elevation 59.5° at 2021-08-25T12:41:13-04:00 (EXIF DateTimeOriginal).

**In frame** — 4/4 building tiles (188,464 tris), 2 landmark models, 974 pavement polygons, 317 props, 4,797 facade-kit pieces; 1,894,573 triangles; ground mesh 199² at 2.0 m near / 40.0 m far.

**Verdict — the Paramount's brick shaft and stone base are in the frame with a genuine brick texture on them — one of the few textured walls in the set — and the setback ziggurat, the globe and the clock that make the building famous are all above the top of the frame**

## What matches

* The building's lower shaft is well modelled: a warm brick wall with a regular window grid over a dark stone base, the two meeting at the right height, and the corner turning correctly onto Broadway.
* The brick reads as brick. It has tonal variation and a coursed appearance rather than a flat fill, which almost nothing else in the comparison set achieves.
* The Times Square canyon behind is right: the towers stepping away to the vanishing point, a cobra-head lamp on its davit over the roadway, a hydrant at the kerb, and street trees in the middle distance.
* 1,438 pavement polygons carry the roadbed, sidewalks and crossings, and the kerb line reads across the frame.

## What does not match

* The top of the building is out of frame, and with it the whole subject: the stepped ziggurat setbacks, the four-faced clock and the glass globe.
* The lower 45 % of the frame is bare dark roadbed with no texture, no markings and nothing on it.
* No people, no vehicles, no signage — this is Times Square's own block and the render has not one sign.
* The windows are dark rectangles with no glazing, mullions or reveals.
* The frame is dark at mean 0.271; the sun is behind the buildings and the street floor is in shadow.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the ziggurat, clock and globe are out of frame | a level axis at street level cannot contain a 33-storey setback tower from this distance | camera |
| bare roadbed | pavement polygons carry a kind but no texture or markings | material |
| no people, vehicles or signage | no stage places any of them | data |
| no glazing | the kit supplies openings without glass | material |
