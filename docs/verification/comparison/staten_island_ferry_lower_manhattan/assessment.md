# Staten Island Ferry deck view of Lower Manhattan

`staten_island_ferry_lower_manhattan` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Lower Manhattan from Staten Island Ferry February 2015 002.jpg by King of Hearts, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2015-02-15 13:51, 1920x840. [Commons page](https://commons.wikimedia.org/wiki/File:Lower_Manhattan_from_Staten_Island_Ferry_February_2015_002.jpg)

**Camera** — camera 40.69700, -74.01900 (NYC_TM -5832, -331) z 8.0 m NAVD88 | azimuth 15.2deg pitch +0.0deg | 28 mm on 36 mm (65.5deg horizontal) | 1280x560. View direction: 15.2 deg, the bearing from this photograph's own GPS position to One World Trade Center; heading and position both come from the photograph.  The item's recorded azimuth is 15.8 deg, 0.6 deg away, and belongs to its nominal viewpoint. Aim: level optical axis (the subject is 1811 m away; anything that far is photographed with a level camera).

**Sun** — azimuth 209.3°, elevation 31.8° at 2015-02-15T13:51:00-05:00 (EXIF DateTimeOriginal (minutes)).

**In frame** — 67/119 building tiles (951,762 tris), 34 landmark models, 492 pavement polygons, 0 props, 0 facade-kit pieces; 2,456,145 triangles; ground mesh 373² at 3.125 m near / 40.0 m far.

**Verdict — the skyline is at the right scale and in the right order, but the camera is 700 m off the ferry route and the frame is half empty water as a result; below the skyline there is nothing at all — no terminal, no piers, no boats, no ice**

## What matches

* The Lower Manhattan profile is right: One World Trade Center dominates with its spire, the Financial District ridge steps down to its right, and the low Battery buildings close the run — the same order and the same relative heights as the reference.
* The apparent size of the skyline matches the photograph closely, which is the test this viewpoint exists for: a 28 mm lens at 1,811 m puts One WTC at the same height in the frame as the reference does.
* 67 of the 119 tiles import, 11 of them by LOD fallback, and 34 landmark models are placed with their shells suppressed so nothing is drawn twice.
* The water surface is at the right level and the shoreline crosses the frame at the right height.
* The Sun is from the photograph's own EXIF instant (2015-02-15 13:51 EST, elevation 31.8 deg) and the towers are lit from the same side.

## What does not match

* The camera is in the wrong place, and the sheet says so. This photograph's own EXIF GPS is 699 m from the item's viewpoint, in the Hudson west of Battery Park City rather than on the ferry route south of Whitehall. From there the whole island lies to the right of the view axis, so the left half of the render is empty water where the reference has Battery Park City and the Hudson shore. The fix belongs at source: a ferry-deck item needs a viewpoint on the route, and a photograph whose EXIF fix is off the route should be rejected rather than trusted.
* The water is a mirror. Roughness 0.06 with no wave normal turns the Upper Bay into a perfect reflector, and the inverted skyline under the waterline is the least believable thing in the frame. The reference is February pack ice — broken, matte, almost white.
* Nothing is on the water: no ferries, no tugs, no barges, no buoys, where the reference has a moored vessel and the Battery Maritime Building's slips.
* The Whitehall ferry terminal, the Battery Maritime Building, Pier A and the Battery's seawall are all absent; the shoreline is a bare terrain edge.
* Every tower is a flat pastel solid. At 1.8 km the reference still shows glass, banding and window grids on 200 Vesey, 17 State Street and the Blue Tower; the render shows none.
* 52 of the 119 tiles have no shell at all, so the New Jersey bank behind the island is empty.
* There is no ferry under the camera: the boat is not modelled, so the eye floats free at 8 m over the water. The sheet states this.
* The sky is a clear Nishita gradient against the reference's deep winter blue with high haze; the render's horizon washes out where the photograph's stays crisp.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| camera 700 m off the ferry route | the photograph's EXIF GPS is off-route and the item's viewpoint is a route description; neither is a position on the route matching the photograph | reference |
| mirror-flat water | the water material is roughness 0.06 with no normal map and no wave displacement | material |
| no ice | no seasonal water state exists in any dataset | data |
| no vessels | no stage places boats | data |
| no terminal, piers or seawall | waterfront structures are neither building footprints nor props, so no stage builds them | geometry |
| flat pastel towers | shells carry a per-material base colour with no facade texture or glass | material |
| empty New Jersey bank | no tile_buildings.glb is built outside the five boroughs | data |
| no ferry under the camera | no vessel geometry exists; the sheet states the camera floats | geometry |
