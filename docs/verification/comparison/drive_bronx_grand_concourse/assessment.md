# Bronx drive-through: Grand Concourse Art Deco apartments

`drive_bronx_grand_concourse` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:VZ E167 St exchange jeh.jpg by Jim.henderson, CC0 (http://creativecommons.org/publicdomain/zero/1.0/deed.en), taken 2012, 1920x1564. [Commons page](https://commons.wikimedia.org/wiki/File:VZ_E167_St_exchange_jeh.jpg)

**Camera** — 40.832, -73.9186 (NYC_TM 2690, 14642) at z 27.6 m NAVD88 | azimuth 25.0°, pitch +0.0° | 35 mm on 36 mm (54.4° horizontal) | 1158x944.

**Sun** — azimuth 146.0°, elevation 24.0° at 2012-11-12T09:30:00-05:00 (the photograph's own categories carries the date, and 09:30 **chosen**, not measured: of the hours that put the Sun above 20 deg it is the one whose bearing (146 deg) comes closest to the view azimuth (25 deg), 121 deg off, so the Sun is behind the camera and lights what it looks at); 707.7 W/m² direct normal, sky at strength 0.0384, Filmic, +4.33 stops.

**In the scene**, within 720.0 m of the camera and not all of it in frame — 6 building tiles (323,032 tris), 2 landmark models of which **0 can fall inside the 54.4° frame**, 29,268 pavement polygons (12,068 white, 5,530 roadbed, 4,902 sidewalk, 3,806 curb, 1,200 median, 767 crosswalk, 549 parking lot, 402 yellow, 44 plaza), 3,002 props of the 3,136 in range, 4,576 kit pieces, 89 vehicles and 404 people; 4,500,075 triangles. Ground mesh 88,200 triangles, 0 holes. 17 city surfaces are dressed from the shared photographic catalogue.

## Verdict — two pictures of two places, and neither of them is the Art Deco block the item is named for

**This sheet is not a comparison of one view; the record says so and the pictures agree.** The photograph is a four-storey red-brick telephone exchange seen across a corner, its own Commons description reading *"Looking north across 167 Street and Grandview Avenue at Verizon exchange west of Grand Concourse on a sunny early afternoon"*, its categories dating it to **2012-11-12**. Its EXIF GPS stands **290.2 m** from the item's recorded viewpoint, past the **250 m** at which it could still be the same view, so the camera was stood on the recorded viewpoint and pointed along the recorded street heading of **25.0°**, a bearing never derived from the image (confidence medium). This is the pairing DEVIATIONS **J60** was written about: the chooser's first pick for this item was a bank **3855 m** up the avenue, and the register says all three of the item's photographs stand beyond any sane radius. This sheet is not a test of whether the build's Grand Concourse looks like the Grand Concourse; at best it tests whether the build's Bronx street fabric is the same kind of thing as a street 290 m away.

**The render is of the street it says it is, from a corrected position.** The recorded viewpoint sits inside `t_2_14_roof_membrane`, so the camera was walked **44.3 m** onto the nearest roadbed polygon at the same 1.6 m eye height; from there the view azimuth is clear for **60 m** and the nearest built thing is `prop_tree_honeylocust_small_19` at **10.2 m**, **-9.1°** yaw and **+22.7°** pitch — the honeylocust crown over the left-hand pavement in the picture. The frame is a broad concrete footway on the left under a tan-brick walk-up with window air-conditioners and a fire escape, a wide empty asphalt carriageway on the right, buff-brick low blocks with street trees beyond, and a washed-out sky. The two landmarks placed, Yankee Stadium at **718.8 m** and the Bronx County Courthouse at **772.3 m**, are behind or aside.

**The date is the photograph's own now, and it is the date this assessment already named.** The previous version of this paragraph said the file carried a year only, that 21 June was assumed, and that "the photograph is a November early afternoon under a low south-western Sun". J114 made `photo_instant` read the photograph's own title, description and categories, and **the categories carry 12 November 2012** — the month the assessment had diagnosed from the picture. So the render is lit in November: the Sun at **24.0°** elevation from **146.0°**, a low south-easterly, against the assumed solstice's higher and far more easterly one.

**The hour is still chosen and it is now further off, which is the honest cost.** 09:30 is the hour whose bearing comes closest to a camera facing 25°, and in November that closest is **121°** off — where on the solstice it was 61°. A low winter Sun cannot be got behind a north-north-east view at any hour, and the rule reports the miss rather than hiding it (J80). The photograph is an early afternoon and the render a mid-morning, so shadow *direction* is still not evidence; what the real date buys is the season, the Sun's height and the crowd's day.

**The luminance comparison is a comparison of two developments.** The frame is metered (**J83**): its linear median of **0.008982** was placed at middle grey by **+4.325** stops, where the physical rule alone would have given **+0.42**; the record calls a frame under-lit only above +4. The photographer's exposure sits **1.41** stops from the same convention against the render's **0.222**, a difference of **-1.188** stops, and that is where the p50 ratio of **0.69** (**0.4955** against **0.721**) comes from before the city does.

## What matches

* **The building stock is the right kind of stock.** Both halves show mid-rise brick with punched openings over a masonry base — red brick over limestone in the photograph, tan and red brick in the render — drawn from **3,268** windows, **352** window accessories, **45** fire escapes, **106** quoins, **93** string courses and **67** cornices among the **4,576** kit pieces placed within 120 m.
* **The street furniture is the Bronx's.** A cobra-head lamp on a curved mast stands on the render's right kerb and on the photograph's corner (**116** street lamps in range); a red hydrant stands at the render's left kerb (**54** in range); a manhole cover sits in the render's carriageway (**112** in range).
* **Street trees at census height.** The honeylocust crowns over both pavements are drawn at the height their census row records: **2,607** of **2,609** trees scaled, mean scale **0.888**. The photograph carries one small kerbside tree in autumn leaf.
* **The kerb reads as a kerb**: **5,530** roadbed, **4,902** sidewalk and **3,806** curb polygons in range; the concrete footway meets the asphalt with its own shadow line.
* **The crowd is the simulation's own weekday morning**: **404** people placed (**1** LOD0, **7** LOD1, **400** LOD2), two of them in hi-visibility vests on the near left pavement and a file of walkers along the far right footway, with **no agent inside 20 m** of the lens. 12 November 2012 was a Monday, so the day type did not change with the date — the crowd grew because a 09:30 November hour asks the density table for a different frame than 08:30 in June, and it is drawn almost entirely at the cheapest LOD.

## What does not match

* **Different buildings on different streets.** The photograph's subject is the Verizon exchange at East 167th Street, **290.2 m** from the camera; the render looks up the recorded street at **25.0°**. Neither shows a Grand Concourse Art Deco apartment house — no stepped parapet, corner casement, terracotta band or cast-metal entrance surround is in either half.
* **The carriageway is empty.** The photograph's foreground holds a yellow taxi, a red SUV, a sedan and a minivan at a stop sign; the render's roadway, filling its right half, carries nothing. **88** vehicles are placed within 320 m, **11** of them taxis, and **182** more were dropped for the triangle budget; none is in this cone.
* **The ground rises in a smooth grey hump under the left-hand building**, and the shell's flat underside shows dark above it. The record says why: the DEM "carries building grades and raised plinths", which is also why the camera's own ground was taken at the 10th percentile within 12 m (**26.04 m**).
* **A green sidewalk shed stands over the left pavement at mid-distance.** **178** scaffold pieces are in the kit; the photograph, from 2012, has none.
* **The sky is near-white where the photograph's is a saturated blue with cirrus.** The sky background is at strength **0.0384** and the frame was developed **+4.325** stops; p95 **0.8822** against **0.9184** says the render's highlights sit where the photograph's do, so the sky has gone to the Filmic shoulder with the rest of the frame.
* **Chroma is about half**: **0.0770** against **0.1352**, ratio **0.570**. The photograph's brick is a warm, varied red; the render's is one tan family on the left and one buff family on the right — **J66**, second half, one material family per facade class.
* **The shadow floor is the photograph's, not the render's**: p05 **0.217** against **0.144**. The render's darkest twentieth is brighter than the photograph's: a metered frame lit from behind the camera, against a November photograph whose low Sun puts the exchange's east return into deep shade.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| different buildings on different streets | the photograph's GPS is 290.2 m from the viewpoint, past the 250 m band; the item names no subject | reference — **DEVIATIONS J60** |
| no Art Deco vocabulary in either half | the photograph is of a telephone exchange; the classifier has no source naming which block is Deco and the kit carries no Deco parapet, casement or surround | geometry |
| an empty carriageway against four queued vehicles | 88 vehicles placed within 320 m and 182 dropped to budget; the 54.4° cone holds none at this instant | verification |
| a grey hump of terrain under the left-hand building | the 1 m DEM carries building grades and raised plinths, and the shell sits on its footprint elevation rather than on the graded surface | data |
| a sidewalk shed the photograph does not have | 178 scaffold pieces are placed from the shed source for the present city; the photograph is from 2012 | reference |
| a white sky against a blue one | developed +4.325 stops so a linear median of 0.008982 reads as middle grey; the sky rides up to the Filmic shoulder | stated choice — **DEVIATIONS J83** |
| chroma 0.570 of the photograph's | one material family per facade class; the photograph's brick varies building by building | material — **DEVIATIONS J66** |
| shadow floor p05 0.217 against 0.144 | a metered frame lit from behind the camera against a November photograph with a shaded return; the Sun is a chosen instant | stated choice — **DEVIATIONS J80** |
| exposure offset -1.188 stops between the two halves | the render is metered at middle grey and the photographer exposed 1.41 stops above that convention | — (not a gap) |

## Re-read against the re-rendered record

This sheet was rendered again on the v17 pass's restart, to carry the `record_shape` stamp that
tells a reader which generation of the renderer wrote a record (**DEVIATIONS J119**). Nothing above
was rewritten, and the evidence for leaving it is stronger than a re-reading: diffing the new record
against the committed one field by field, **every measured value is identical**, and the frame it replaced is reproduced **pixel for pixel**: `render.png`'s decoded image is identical, and the only bytes that differ are the five `tEXt` chunks in which Blender records the render date and its own timings. `sheet.png` is byte-identical. What
moved is the wall clock:

`scene.agents.seconds` 640.79 -> 644.44,
`scene.seconds` 801.42 -> 787.95,
`seconds.render` 218.0 -> 324.0,
`seconds.scene` 837.9 -> 831.9,
`seconds.total` 1055.9 -> 1155.9.
The other change is the agent snapshot's provenance: the previous render simulated the crowd and
this one read the same snapshot back from the cache, which the diff proves rather than assumes --
every agent count in the record is unchanged, or that note would not be the only field beside the
clock that moved (`simulated (already built)` to
`cached 2649_14659_9_0_9eb5722d51a6d31d_1788868452.json`).


## Measured for this assessment

The wall-clock figures in the table are the **previous** render's, quoted so that "every measured value is identical" is a comparison a reader can check rather than a claim. They were read from this sheet's own `render.json` at commit `f15e47a`, its last state before the pass restarted.

| figure | where it comes from |
|---|---|
| 640.79 | `scene.agents.seconds` in the previous record; the re-render took 644.44 s |
| 801.42 | `scene.seconds` in the previous record; the re-render took 787.95 s |
| 218.0 | `seconds.render` in the previous record; the re-render took 324.0 s |
| 837.9 | `seconds.scene` in the previous record; the re-render took 831.9 s |
| 1055.9 | `seconds.total` in the previous record; the re-render took 1155.9 s |
