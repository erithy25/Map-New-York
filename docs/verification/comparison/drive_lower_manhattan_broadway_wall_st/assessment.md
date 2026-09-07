# Lower Manhattan drive-through: Broadway at Wall Street

`drive_lower_manhattan_broadway_wall_st` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Wall Street sign & US Flag (May 2023).JPG by Benoît Prieur, CC0 (http://creativecommons.org/publicdomain/zero/1.0/deed.en), taken 2023-05-21 13:00:40, 1920x1693. [Commons page](https://commons.wikimedia.org/wiki/File:Wall_Street_sign_%26_US_Flag_(May_2023).JPG)

**Camera** — camera 40.70783, -74.01166 (NYC_TM -5210, 871) z 12.3 m NAVD88 | azimuth 200.0deg pitch +0.0deg | 35 mm on 36 mm (54.4deg horizontal) | 1112x980. View direction: 200.0 deg as recorded in meta.json.  This item names no subject and the reference photograph's own view direction was not derived from the image (confidence: medium), so the two halves of this sheet are not guaranteed to face the same way -- compare them on street width, storey height and material, not on composition. Aim: level optical axis (the reference names no subject to aim at).

**Sun** — azimuth 185.4°, elevation 69.5° at 2023-05-21T13:00:40-04:00 (EXIF DateTimeOriginal).

**In frame** — 4/4 building tiles (82,358 tris), 14 landmark models, 2,634 pavement polygons, 616 props, 8,734 facade-kit pieces; 4,500,041 triangles; ground mesh 211² at 2.0 m near / 40.0 m far.

**Verdict — a convincing Lower Broadway canyon — right width, right wall heights, real subway entrances, real lamps and litter baskets, deep shadow where the real street has deep shadow — held back only by having no surfaces and no life, and paired with a close-up of a street sign**

## Re-rendered 2026-09-07 — the best frame in the set, and it corrects something I wrote today

This is the first frame in this pass that reads as a photograph of a street rather than as a model of
one. Broadway looking south into the Wall Street canyon: towers rising out of frame on both sides,
two ranks of street lamps down the left kerb, three SUBWAY entrance signs with their railings, a
litter basket, a manhole cover in the roadbed, a crowd of pedestrians moving on both pavements and a
black sedan on the carriageway. 4,025 kit pieces, 455 props, 14 landmark models, 89 vehicles and 212
people.

**It corrects a generalisation I made two frames ago.** On the Bed-Stuy and Park Slope sheets I wrote
that the facade kit models everything except the opening. That is true there and it is not true here:
the left-hand tower carries deep recessed window openings with visible reveals and real shadow, from
3,714 window pieces in this frame. Whether a window reads as an opening depends on the facade class,
not on the kit as a whole, and the earlier wording was broader than the evidence. Both sheets now say
which case they are.

**What the agent counts mean here.** 212 pedestrians and 89 vehicles are placed, and unlike the Bronx
frames most of them are visible, because a straight canyon is the one geometry where a 54° wedge is
not mostly blocked by block faces. The drop record is worth reading: **1,292 pedestrians were dropped
by the triangle budget** — six times the number placed — along with 1,151 outside the radius, 227
standing in the carriageway while not crossing, 86 on no walkable surface and **31 inside a
building**. The crowd you see is the budget's share of a much larger simulated one, not the whole of
it.

## What matches

* The canyon is right. Broadway's roadbed width, both sidewalks, the setback line and the way the walls run unbroken for two blocks downtown match the real street closely.
* The camera stands on the photograph's own EXIF GPS, 56 m from the item's nominal viewpoint, on the roadway at 12.3 m NAVD88 over a 10.7 m surface.
* Two subway entrance structures with their railings stand on the west sidewalk in the right places, and a green DSNY litter basket sits at the kerb: both are real props from props.parquet at correct sizes.
* Bishop's-crook lamp standards with their globe lanterns line the kerb at the right spacing and the right height, and are the correct historic pattern for this stretch of Broadway.
* 14 landmark models are in range, so the towers closing the view downtown are modelled buildings rather than extruded boxes.
* The light is right: a 69.5 deg May Sun almost straight down the canyon leaves the street floor in shadow with a bright band on the upper west wall, which is exactly what the reference photograph's own background shows.
* 2,634 pavement polygons including 596 crosswalk and 87 median polygons put the crossing geometry where it belongs.

## What does not match

* The frames are of different things: the item looks south down Broadway toward Bowling Green, the photograph is a tight study of a Wall Street sign and a flag on a facade. The item names no subject and the photograph's direction was assumed.
* No facade has any surface. The near wall is a flat grey plane with unglazed window openings; the reference's own facade is rusticated limestone with moulded architraves, balustrades, and glass with reflections.
* No signage anywhere: no street-name signs, no subway roundels, no shopfront lettering, no flags. The photograph is entirely a sign and a flag.
* The street trees read as dark cones here. The same tree assets render correctly in the sunlit Arthur Avenue frame, so this is shading rather than geometry: an untextured branch mass in full shadow collapses to a silhouette.
* ~~No vehicles and no people on a street that in the reference's background carries both.~~ — **superseded 2026-09-07.** **212 people and 89 vehicles are in this scene** from one frame of the running simulation; what the reference still has and the render does not is recorded in the section above.
* No road markings, no crosswalk stripes, no manhole detail on the visible roadway.
* The facade kit was capped by the triangle budget at 8,734 of 15,653 records in range, so nearly half the wall detail within 120 m is not drawn.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the two halves are of different subjects | the item names no subject and the reference stage assigned it the item's own azimuth | reference |
| flat facades, no glass or stone | shells carry a per-material base colour; the kit supplies openings without glazing or mouldings | material |
| no signage of any kind | no stage produces street-name signs, subway roundels or shopfront lettering | geometry |
| trees collapse to silhouettes in shadow | the tree canopy is untextured geometry with no translucency | material |
| ~~no vehicles or people~~ superseded | agents are placed now (212 people, 89 vehicles); what remains is framing and occlusion, not absence | reporting |
| no road markings | pavement polygons carry a kind but no stripe geometry or texture | material |
| nearly half the facade kit not drawn | the 4.5 M triangle budget is spent before the kit finishes; the cap is on the sheet | geometry |

## Re-render note, 2026-09-07

Re-rendered against the corrected `b_wtc_site` model — the World Trade Center site stood 3.5 m too high, its plaza was an unbroken 520 x 520 m quad over both memorial pools, and its 220 oaks each carried a merged impostor card (`docs/verification/landmarks/REPORT_B.md` §12). Measured against the shipped render, **0.000 %** of pixels differ by more than 8/255 and the largest single difference is **4/255**, which is Cycles sampling noise at 32 samples, not content; frame mean and standard deviation are unchanged (0.401 / 0.180). The camera did not move. Nothing in this assessment changes.
