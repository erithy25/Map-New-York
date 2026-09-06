# MetLife Building (200 Park Avenue)

`landmark_metlife_building` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Park Av Nov 2025 05.jpg by Epicgenius, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2025-11-05 08:45:28, 1920x1440. [Commons page](https://commons.wikimedia.org/wiki/File:Park_Av_Nov_2025_05.jpg)

**Camera** — camera 40.75068, -73.97728 (NYC_TM -2229, 5640) z 14.4 m NAVD88 | azimuth 10.0deg pitch +0.0deg | 18 mm on 36 mm (90.0deg horizontal) | 1208x906. View direction: 10.0 deg as recorded; it agrees with the bearing from the camera position used to MetLife Building (200 Park Avenue) (10.0 deg) to 0.0 deg. Aim: level optical axis (the subject is 300 m away; anything that far is photographed with a level camera).

**Sun** — azimuth 135.0°, elevation 20.5° at 2025-11-05T08:45:28-05:00 (EXIF DateTimeOriginal).

**In frame** — 8/8 building tiles (260,872 tris), 11 landmark models, 3,851 pavement polygons, 412 props, 9,588 facade-kit pieces; 4,500,046 triangles; ground mesh 219² at 2.0 m near / 40.0 m far.

**Camera clearance** — the recorded viewpoint is inside t_-3_5_glass_curtain (a ray straight up from the eye point hits its roof); the camera was moved 75 m onto the nearest real sidewalk polygon in data/processed/roads/pavement, keeping the same eye height above the heightmap.  The view azimuth is clear for 96 m from there

**Verdict — the camera was pulled 75 m out of a glass curtain wall it was standing inside, and what it found is a dark Park Avenue canyon with the MetLife Building out of frame**

## What matches

* The clearance correction is the substance of this sheet and it is fully stated: the recorded viewpoint is inside t_-3_5_glass_curtain, and the camera was moved 75 m onto the nearest real sidewalk polygon with 96 m of clear view. Before that test existed this frame was mean 0.016 — effectively black — and the orchestrator's sweep flagged it.
* The photograph's own EXIF GPS was rejected as mis-tagged at 912 m; the item's viewpoint was used.
* The heading is exact: 10.0 deg recorded, 10.0 deg to the subject.
* The lens rule widened 35 mm to the 18 mm floor and says the top is still cut off: 245 m of building above the lens at 300 m, 39 deg above the horizon.
* 3,851 pavement polygons and 11 landmark models are placed, and the canyon's proportions and kerb lines are correct.

## What does not match

* The MetLife Building is not in the frame. The item exists to test the 246 m slab closing the Park Avenue vista and the render shows the sidewalk and the wall beside it.
* Mean luminance 0.222 with the whole street floor in shadow at a 20 deg November Sun: legible but not judgeable.
* The reference's content — the Park Avenue plaza, the fountain, the flagpole and flag, the honey locusts, the red shopfront band, the trucks, thirty people, and the tower itself with its MetLife sign — has no counterpart at all.
* The buildings in frame have no glazing, no spandrel, no reveal; the near wall is a flat dark plane.
* Both props and kit were capped by the triangle budget (9,588 of 19,491 kit records in range).

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the tower is not in the frame | the corrected camera has a clear azimuth but no line of sight to a subject 300 m up the avenue | camera |
| frame in shadow | a Park Avenue canyon at a 20 deg November Sun with two light bounces | lighting |
| no plaza, fountain, flag, trees or people | plaza furniture and crowds are in no dataset the scene reads | data |
| no glazing on any wall | shells carry a per-material base colour; the kit supplies openings without glass | material |
| half the facade kit not drawn | the 4.5 M triangle budget is spent before the kit finishes | geometry |
