# Brooklyn brownstone block: Bed-Stuy, Stuyvesant Avenue

`drive_brooklyn_bed_stuy_stuyvesant_ave` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Decatur Stuyvesant Heights HD 2.JPG by Smallbones, CC BY-SA 3.0 (https://creativecommons.org/licenses/by-sa/3.0), taken 2013, 1920x1440. [Commons page](https://commons.wikimedia.org/wiki/File:Decatur_Stuyvesant_Heights_HD_2.JPG)

**Camera** — 40.6815, -73.932306 (NYC_TM 1496, -2054) at z 19.8 m NAVD88 | azimuth 351.4°, pitch +0.0° | 35 mm on 36 mm (54.4° horizontal) | 1208x906.

**Sun** — azimuth 284.2°, elevation 20.1° at 2013-06-21T18:30:00-04:00 (photograph year only, 21 June assumed, and 18:30 **chosen**, not measured: of the hours that put the Sun above 20 deg it is the one whose bearing (284 deg) comes closest to the view azimuth (351 deg), 67 deg off, so the Sun is behind the camera and lights what it looks at); 654.3 W/m² direct normal, sky at strength 0.0405, Filmic, +4.78 stops.

**In the scene**, within 766.3 m of the camera and not all of it in frame — 6 building tiles (670,572 tris), 0 landmark models, 19,150 pavement polygons (7,648 white, 4,326 sidewalk, 3,340 roadbed, 2,895 curb, 451 crosswalk, 212 parking lot, 192 yellow, 63 median, 23 plaza), 3097 props of the 3,204 in range, 4,122 kit pieces, 77 vehicles and 375 people; 4,500,015 triangles. Ground mesh 89,888 triangles, 0 holes. 18 city surfaces are dressed from the shared photographic catalogue.

## Verdict — the right street and the right kind of row, seen square-on where the photograph is oblique, under a Sun the record calls behind the camera and the picture shows in front of it

**The two halves are the same street and not the same view.** The camera stands on the photograph's own EXIF GPS, **46.3 m** from the recorded viewpoint at the Stuyvesant Avenue and Decatur Street crossing, not moved. That GPS is on Decatur Street; the azimuth is **351.4°**, Stuyvesant Avenue's bearing from `meta.json`, because the item names no subject and the photograph's direction was never derived from the image (confidence medium). So the render looks north from Decatur Street square across the carriageway at the north-side row, clear for **23.2 m** to the facade: four stoops, four arched doorways, the wall filling the frame to its top edge. The photograph is an oblique down the same row, houses receding left, three parked SUVs in the foreground, a blown overcast sky above. The record says to compare on street width, storey height and material, not composition. The reader must not take the render for a view along Stuyvesant Avenue: the item is named for the avenue and the picture is Decatur Street's north side. The previous reference was a photograph of a different corner (J60); this is the one taken 46 m from the viewpoint that J60 said sat unused.

**The Sun is chosen (J80) and the record's gloss on the choice is inverted.** The photograph carries a year only, so 21 June is assumed and 18:30 is picked as the hour whose solar bearing, **284°**, is nearest the view azimuth, **67°** off; the record then says "the Sun is behind the camera and lights what it looks at". A solar bearing within a right angle of the view axis puts the Sun ahead of the camera, low beyond the left edge of the frame, and the facade faces back down the view axis, away from it. The picture agrees with the geometry, not the gloss: nothing in frame is in direct sun. The wall is lit by the bright western sky low on the left, which is why every window box throws a soft shadow down and to the right, why the ginkgo at **15.6 m** (27.2° right, 21.1° up) lays a soft shadow over the right third of the facade, and why the record reads **under-lit**: linear median **0.006574**, **+4.78 stops** of development where the physical rule alone gave **+1.11**. A south-facing row at half past six on a June evening is in its own shade, and the metering (J83) has developed that shade to middle grey. The luminance figures below are the development, not the city.

**The kit is right and the colour is not.** Stoops, arched entry surrounds, garden-level openings, air-conditioners, areaway fences: the elements of this block. But the photograph's subject is that four adjacent houses are four colours, and the render's row is one pale veined stone.

## What matches

* **Typology and storey rhythm.** Raised basement, a stoop of about nine risers to a parlour door under a round arch, a row of windows to each storey above; the photograph's houses are built the same way at the same scale. **267** door entries, **2,639** windows and **330** window accessories stand in the scene out of **4,122** kit pieces.
* **The furniture of a row-house block**: white areaway railings at the kerb line (**83** fence pieces), greenery against the base (**42** vegetation pieces), air-conditioners in the openings, which the photograph carries too.
* **Street width and eye height.** The camera stands **1.6 m** above the traffic surface on the photograph's own position, and the facade is one carriageway and a pavement away in both halves.
* **Nothing missing on the record's side**: no tile missing, **3097** of **3,204** prop rows placed, **2610** of them trees at a mean scale of **0.908** (J70).
* **A weekday crowd on a weekday**: 21 June 2013 is a Friday; **375** people within 200 m and **77** vehicles within 320 m.

## What does not match

* **One stone where the photograph has four colours.** Left to right the reference shows a chocolate-painted brownstone, a cream one, a plum-red brick house with terracotta bands and an orange-brick house on a rusticated base. The render's row is `brownstone`, dressed from `Travertine005` at an albedo scale of **2.682** to lift the scan's **0.0882** to the class target **0.2367**: a pale pink-beige travertine with wavy horizontal veining, not a brown sandstone. Only the stoops read as brownstone-coloured. J66: one material family per facade class, and no source records an individual house's colour.
* **Chroma 0.045 against 0.1381, ratio 0.326** — the same fact measured: a third of the photograph's colour.
* **Windows sit proud of a plain wall.** Each window is a tan box standing off the shell; the photograph's openings are cut in, with arched parlour-floor heads and moulded string courses (J51). **45** string courses and **56** quoins are in the scene and none is on the wall in frame.
* **No roofline.** The level axis and the 35 mm lens put the top of the frame below the third-storey window heads, so the deep bracketed cornice that dominates the photograph's row cannot be judged; **175** cornice pieces are in the scene.
* **The doors are a green-and-salmon livery repeated four times**; the photograph's are dark panelled wood and glass.
* **The carriageway is empty.** The lower two fifths of the render is bare grey asphalt with a black band along the kerb line; the photograph's foreground is three SUVs nose to tail at the kerb. None of the 77 vehicles falls inside this **54.4°** cone.
* **Three simulated figures, none in the photograph**: `agent_ped_936.0` at **16.2 m**, 18.1° right, in a yellow shirt carrying an orange box; a grey figure at the left edge holding a bare rectangular outline; a third cut by the right edge.
* **The trees are the wrong trees.** The ginkgo top right is nearly bare in June; the photograph has a full street tree and a tall conifer in a front garden. **707** of the **2610** trees are species-substituted, **12** outside the scale band.
* **The lighting, in the record's terms**: the render needed **+4.78 stops** and is under-lit; the photograph sits at **-1.202** stops from the metering convention and the render at **0.248**, **1.45** stops apart. Mean **0.583** against **0.3992** and p50 **0.4997** against **0.3099** are that gap first and the scene second. p05 **0.217** against **0.0583** is all-shade lifted to middle grey beside a frame with black under its cars; p95 **0.9055** against **0.9972** is the photograph's blown sky, which is outside the render's frame entirely.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| one pale stone where the photograph has four house colours; chroma 0.326× | one material family per facade class, `brownstone` dressed from `Travertine005`, a different stone; `shellmat` varies tone, never hue; no source records a house's colour | data, **DEVIATIONS J66** |
| windows proud of a plain wall, no arched heads or string courses in frame | the shell is an extrusion with no openings cut; the classifier has no source for the ornament | geometry, **DEVIATIONS J51** |
| no roofline or cornice in frame | level axis, 35 mm lens, no subject to tilt to | stated choice |
| doors in a repeated green-and-salmon livery | one door asset per entry class, livery authored not measured | material |
| carriageway empty, three SUVs in the photograph | placement is city-wide over a 320 m ring and the frame is not | verification |
| three simulated figures, none in the photograph | the simulation's own weekday crowd, not the photograph's | — (not a gap) |
| a bare ginkgo for a full plane and a conifer | 707 of 2610 trees species-substituted | data |
| under-lit at +4.78 stops, exposure 1.45 stops apart, p05 0.217 against 0.0583 | the chosen instant puts the Sun ahead of the camera, the south-facing row is in its own shade, and the metering develops the shade to middle grey | stated choice, **DEVIATIONS J80 / J83** |
| the record says the Sun is behind the camera; it is in front | the hour chooser scores a solar azimuth *near* the view azimuth as "behind the camera", which is the opposite hemisphere; the picture follows the geometry | verification, **DEVIATIONS J80** |
| the render looks square across Decatur Street; the item is named for Stuyvesant Avenue | the camera stands on the photograph's GPS, 46.3 m down Decatur Street from the recorded crossing, and looks along the avenue's bearing from off the avenue | reference |
