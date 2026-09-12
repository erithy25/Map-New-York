# TSX Broadway

`landmark_tsx_broadway` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Times Sq Sep 2022 11.jpg by Epicgenius, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2022-09-14 10:36:09, 1920x1280. [Commons page](https://commons.wikimedia.org/wiki/File:Times_Sq_Sep_2022_11.jpg) — the photograph carries no camera GPS, so the viewpoint is the item's own recorded position. The item names what it wants: *"Duffy Square about 130 m south-south-west of the building, looking north-north-east at the TSX Broadway screen and stage"* — the wraparound LED that covers the whole podium and the cantilevered stage that slides out of the facade above Broadway.

**Camera** — 40.757901, -73.985051 (NYC_TM -2989, 6438) at z 15.5 m NAVD88 | azimuth 20.0°, pitch +20.5° | 18 mm on 36 mm (90.0° horizontal) | 1280x854. The heading is the item's recorded 20.0°, which agrees with the bearing to the subject to **0.1°**. The camera was moved **29.9 m**, and the reason is one of the sharper ones in the pass: the recorded viewpoint is *"inside `t_-3_6_roof_membrane` (a ray straight up from the eye point hits its roof)"* — the item's own nominal position is indoors. The walk snapped to pavement under the rule `pavement snap with a clear frame that sees the subject`, scored candidates on the subject's sightline, and its chosen point measured **0.154**, which is what the sheet published. From there the view is clear for **78.0 m** and the nearest built thing in the frame is `t_-3_6_red_brick` **8.3 m** away — a hair inside the 8 m at which J91 counts fabric as too close to the lens, and in the render it is the brick wall filling the right third of the picture. The lens sits at the **18 mm floor**, and the record declares the verticals incomparable with the photograph on proportion. The ground under the lens reads 13.887 m NAVD88, the 10th percentile of 113 samples within 12.0 m.

**Sun** — azimuth 131.9°, elevation 41.7° at 2022-09-14T10:36:09−04:00, from the photograph's own **EXIF DateTimeOriginal**; 851.0 W/m² direct normal, sky at strength 0.0332, Filmic, **+3.56 stops**. Metered on a linear median of **0.015215**, unclamped, against a physical rule of 0.05 — under the +4 at which this build declares a frame under-lit, but only just.

**In the scene** — 4,500,004 triangles: 6 building tiles (332,446 tris), 4 landmark models, 23,209 pavement polygons, 1,687 props with **nothing dropped for budget**, 8,059 kit pieces, 22 park-ground meshes, **1 tile of structures (21,408 tris) with 5 having no file**, 50 vehicles and 367 people.

## Verdict — the height is measured almost exactly and the screen the sheet exists for is a blank face on a building the camera cannot see past

**The measurement is very good.** 43 rays cast, **39 on built fabric**, and the height is **158.27 m** above a ground of 14.71 m on `lm_c_times_square.71`, an object **61.5 by 44.2 m** in plan. The Times Square builder's own dimension for TSX Broadway is **158.0 m**, so the measured and the modelled agree to **under thirty centimetres**, off the right object. And J74's rule fired correctly: the nearest catalogue entry is the composite at **354.4 m** carrying 365.8 m — the Bank of America Tower's spire — well past the 120 m reach, so the geometry was measured rather than the entry copied.

**The item's nominal viewpoint is inside a building.** That is the finding worth carrying off this sheet: the recorded position for *"Duffy Square about 130 m south-south-west of the building"* fails the walk's own indoor test, because a ray straight up from it hits a tile roof membrane. The walk did the right thing — it moved **29.9 m** and it scored the move on the subject's sightline — and the best it could reach was **2 of 13 rays on the subject**, a fraction of **0.154**, with **4 rays meeting nothing at all** and the rest stopping at 20.3 m on a brick tile mesh.

**And it ended up 8.3 m from a wall.** `t_-3_6_red_brick` stands 8.3 m from the lens, a tenth of a metre outside the 8 m clearance J91 measures, and in the published frame it occupies the right third as a brick plane with its window pieces standing proud of it (J51). What the frame actually shows is the Broadway canyon north of 46th Street: the Marriott Marquis's curved banded flank at the left, a dark glass slab, a receding line of towers, a street lamp, a few taxis and a scatter of pedestrians on the sidewalk. **TSX Broadway's screen and its cantilevered stage are not identifiable anywhere in it.**

**The screen itself is 195 blank faces.** The kit placed **195 billboard pieces** in this frame, each with a named material slot, a defined 0..1 UV and no content, by the rule the build states about itself (B5, B15, B15a). So the single largest LED surface in the western hemisphere, which is the item's whole subject, is present as geometry and absent as an image — and the chroma ratio says it: **0.521**.

**Nothing was dropped for the props budget.** 1,687 props placed across nineteen kinds, including **1,120 trees**, 155 Citi Bike dock units, 108 cooling towers, 93 street lamps, 80 manholes and **9 newsstands**. Only 3 trees are drawn from modelled branches and **650 of the 1,120 are a substituted species** (J108).

## What matches

* **The height agrees to under thirty centimetres**: 158.27 m measured from 39 of 43 rays on fabric against the builder's 158.0 m, on a real object 61.5 by 44.2 m in plan.
* **J74's origin rule fired correctly**: the catalogue entry at 354.4 m was past the 120 m reach, so the height was measured rather than copied, and the measurement confirmed the model.
* **The heading agrees with the bearing to the subject to 0.1°.**
* **The walk detected an indoor viewpoint and said so**, then moved 29.9 m and scored the move on the subject's own sightline, publishing the fraction it settled for (J79).
* **Nothing was dropped for the props budget**: 1,687 placed across nineteen kinds.
* **Broadway is paved as Broadway**: 23,209 polygons with 7,580 white markings, 5,986 sidewalk, 4,437 roadbed, 3,256 curb, **1,327 plaza** and 403 crosswalk.
* **The fleet is a Times Square fleet**: 24 yellow taxis of 50 vehicles, with 12 sedans, 6 black cars, 5 boro taxis, 2 SUVs and a box truck.
* **The park ground is correct where the camera can see it**: 49 samples within 150 m, `under_frac` **0.0**, median clearance +0.113 m.
* **The development stayed out of the under-lit band**, at 3.564 stops on a linear median of 0.015215.
* **367 people is the largest crowd drawn on any Times Square sheet read this round**, with 345 of them at LOD2.

## What does not match

* **The screen and the stage are absent.** 195 billboard faces carry no content, so the item's entire subject is geometry without an image (B15a).
* **Two of thirteen rays land on the subject**, a fraction of **0.154**, with four meeting nothing at all and the rest stopping at 20.3 m on a joined brick tile mesh (J94).
* **The camera stands 8.3 m from a brick wall** that fills the right third of the frame, a tenth of a metre outside the 8 m clearance J91 measures.
* **The item's own nominal viewpoint is indoors** — a ray straight up from it hits a roof membrane — so the sheet could not use the position the item records.
* **The windows stand proud of the shells** (J51), which at 8.3 m is the most conspicuous instance of it in any frame read this round.
* **Chroma 0.521** against a photograph whose subject is a lit LED wall.
* **A 1.162-stop exposure gap**: the photograph sits 0.923 stops below the grey convention and the render is metered to 0.239 above it, so mean reads 1.246× and p50 **1.463×** (J83). The render holds less contrast, sd 0.879×.
* **The verticals converge** at 18 mm with a +20.5° pitch, and the record declares the two halves incomparable on proportion.
* **Structures are almost absent**: 1 tile imported for 21,408 triangles with **5 having no file**.
* **The kit was capped at 1,443,158 triangles** and spent on windows: 7,413 of them against **18 cornices**, with 883 pieces suppressed under the landmark shells.
* **650 of the 1,120 trees are a substituted species** and only 3 are drawn from modelled branches (J108).
* **367 people is still a fraction of the ask**, and the drops are the familiar list: 1,227 pedestrians outside the radius, 950 at the 1,125,000-triangle agent budget, 686 vehicles outside the radius, 516 vehicles at the budget, 285 in the carriageway without crossing, **164 not on a walkable surface** (J101), 33 above the observer, 32 riderless bodies, 17 off the carriageway and 1 inside a building.
* **The park ground sinks beyond 400 m**: 0.2172 of 663 samples, worst case −1.943 m.
* **No cloud, no lit signage.** The photograph's September sky sits above a wall of screens; the render's is a Nishita dome at strength 0.0332.

## Measured for this assessment

| figure | where it comes from |
|---|---|
| the builder's own height for TSX Broadway is 158.0 m | the `H_TSX` constant of `blender/landmarks/c_times_square.py` and its dimensions note, against this record's measured 158.27 m |
| 365.8 m is the Bank of America Tower's spire, not this subject | the same file's note — *"BofA roof 288.0 m / spire 365.8 m"* — against the catalogue entry the probe refused at 354.4 m |
| the 8 m clearance threshold | DEVIATIONS J91, which measures built fabric inside 8 m of a lens across the pass; this camera's nearest is 8.3 m |
| the billboard faces carry named slots, a defined UV and no content | the `sign_face_binding` block of the tile's own `kit_placements.json` and the signage section of DATA_CONTRACTS (B5, B15, B15a) |
| the largest crowd drawn on a Times Square sheet read this round | this sheet's 367 people against the One Times Square, Times Square Tower, TKTS booth and two Duffy Square records |

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the screen and the stage are absent | 195 billboard faces are placed with named material slots, defined UVs and no content, because no advertising copy was invented anywhere (B15a) | **declared decision — the slots exist; the content binding is the open half** |
| two of thirteen rays on the subject | the recorded viewpoint is indoors, so the walk had to move 29.9 m, and from the best point it could reach a joined brick tile mesh stops most of the fan 20.3 m out (J79, J94) | **verification — open** |
| the camera stands 8.3 m from a wall | the pavement snap takes the nearest polygon with a clear frame, and 8.3 m is a tenth of a metre outside the threshold J91 measures | verification — open |
| the item's nominal viewpoint is indoors | the recorded position for this item fails the walk's own indoor test; the item's coordinate needs correcting, which is data the repository already has | **data — open, and cheap** |
| the windows stand proud of the shells | no opening is cut into any building shell; cutting them was measured at +48 GB (J51) | **declared decision — recorded with its number** |
| chroma 0.521 and a 1.162-stop exposure gap | blank sign faces, and a photograph developed 0.923 stops under the grey convention against a metered render (B15a, J83) | declared decision + reference |
| 21,408 triangles of structures | five of the six tiles in range have no structures file (B13 remainder) | data — open |
| 18 cornices drawn | the kit triangle budget at 1,443,158 triangles, spent windows-first | performance |
| 650 substituted tree species, 3 modelled canopies | the asset set is ten species with two states, and only 3 rows fall inside the 120 m branch band (J108) | data + performance |
| 367 people against the ask | the 1,125,000-triangle agent budget plus the placement rules (J101) | performance + verification |
| park ground under the terrain beyond 400 m | the park surfaces were draped on the fine grid and the terrain coarsens to 40.0 m (J40, J96) | verification — declared |
| no cloud | nothing in this build reads a historical sky | reference — no source exists |
