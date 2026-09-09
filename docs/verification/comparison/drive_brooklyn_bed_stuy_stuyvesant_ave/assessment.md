# Brooklyn brownstone block: Bed-Stuy, Stuyvesant Avenue

`drive_brooklyn_bed_stuy_stuyvesant_ave` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Decatur Stuyvesant Heights HD 2.JPG by Smallbones, CC BY-SA 3.0 (https://creativecommons.org/licenses/by-sa/3.0), taken 2013, 1920x1440. [Commons page](https://commons.wikimedia.org/wiki/File:Decatur_Stuyvesant_Heights_HD_2.JPG)

**Camera** — 40.6815, -73.932306 (NYC_TM 1496, -2054) at z 19.8 m NAVD88 | azimuth 351.4°, pitch +0.0° | 35 mm on 36 mm (54.4° horizontal) | 1208x906.

**Sun** — azimuth 284.2°, elevation 20.1° at 2013-06-21T18:30:00-04:00 (photograph year only, 21 June assumed, and 18:30 **chosen**, not measured: of the hours that put the Sun above 20 deg it is the one whose bearing (284 deg) comes closest to the view azimuth (351 deg), 67 deg off, so the Sun is behind the camera and lights what it looks at); 654.3 W/m² direct normal, sky at strength 0.0405, Filmic, +4.78 stops.

**In the scene**, within 766.3 m of the camera and not all of it in frame — 6 building tiles (670,572 tris), 0 landmark models, 19,150 pavement polygons (7,648 white, 4,326 sidewalk, 3,340 roadbed, 2,895 curb, 451 crosswalk, 212 parking lot, 192 yellow, 63 median, 23 plaza), 3097 props of the 3,204 in range, 4,122 kit pieces, 77 vehicles and 375 people; 4,500,015 triangles. Ground mesh 89,888 triangles, 0 holes. 18 city surfaces are dressed from the shared photographic catalogue.

## Verdict — the right street and kind of row, square-on where the photograph is oblique, lit from behind the camera by a lamp opposite the Sun the record names

**The two halves are the same street and not the same view.** The camera stands on the photograph's own EXIF GPS, **46.3 m** from the recorded viewpoint at the Stuyvesant Avenue and Decatur Street crossing. That GPS is on Decatur Street; the azimuth is **351.4°**, Stuyvesant Avenue's bearing from `meta.json`, because the item names no subject. So the render looks north across Decatur Street at its north-side row, clear for **23.2 m**: four stoops, four arched doorways, no roofline. The photograph is an oblique down the same row under a blown overcast sky, three SUVs at the kerb. Compare on street width, storey height and material, not composition; the previous reference was a photograph of a different corner (J60).

**The row is in direct sun, and the Sun the record prints is not the lamp that lights it.** The facade sits near the top of the tonal range, every window box and door surround throws a hard-edged shadow down and to the left, and the ginkgo at **15.6 m** lays crisp leaf shadows on the wall left of its trunk. That is light from high on the right, behind a north-facing camera — what the record's gloss promises. The recorded Sun at **284.2°** stands west-north-west, ahead of the camera, and would light nothing on a wall facing south. The lamp in `setup_world_and_sun` (`render_sheets.py`) is rotated tilt-then-yaw, which sends its beam *toward* the recorded azimuth, so light arrives from the opposite bearing; the Nishita sky takes the azimuth as given, so sky and lamp disagree by half a turn. The hour chooser's comment (J80) inverts the hemisphere the same way; the two cancel, and the row is lit as intended by a mechanism that contradicts its record. Neither inversion is in the register.

**The metering (J83) developed the road, not the row.** Linear median **0.006574**, **+4.78 stops** where the physical rule gave **+1.11**; the record calls the frame under-lit. The median pixel is the carriageway, two fifths of the frame in shade thrown from behind the camera; the sunlit wall sits near the linear p95 of **0.084786**, on the shoulder. Under-lit is true of the road, not the facade.

## What matches

* **Typology and storey rhythm.** Raised basement, a stoop to a parlour door under a round arch, windows in rows above, at the same scale in both halves. **267** door entries, **2,639** windows and **330** window accessories out of **4,122** kit pieces.
* **Row-house furniture**: white areaway railings (**83** fence pieces), greenery at the base (**42** vegetation pieces), air-conditioners in the openings.
* **Street width and eye height.** The camera is **1.6 m** above the traffic surface; the facade is one carriageway and a pavement away in both halves.
* **Nothing missing on the record's side**: **3097** of **3,204** prop rows placed, **2610** trees at mean scale **0.908** (J70); **375** people and **77** vehicles on a weekday.

## What does not match

* **One stone where the photograph has four colours**: a chocolate-painted brownstone, a cream one, a plum-red brick house with terracotta bands and an orange-brick house on a rusticated base. The render's row is `brownstone`, dressed from `Travertine005` at albedo scale **2.682**, lifting the scan's **0.0882** to the class target **0.2367**: pale pink-beige travertine with wavy veining, not brown sandstone (J66). **Chroma 0.045 against 0.1381, ratio 0.326** is the same fact measured.
* **Windows sit proud of a plain wall.** Each window is a tan box standing off the shell, casting its own shadow. The photograph's openings are cut in, with arched parlour-floor heads and moulded string courses (J51). **45** string courses and **56** quoins are in the scene and none on the wall in frame.
* **No roofline.** The level axis and 35 mm lens cut the frame through the third-storey windows; the photograph's deep bracketed cornice cannot be judged against the **175** cornice pieces in the scene.
* **The doors are a green-and-salmon livery repeated four times**; the photograph's are dark panelled wood and glass.
* **The carriageway is empty**, bare grey asphalt where the photograph's foreground is three SUVs. None of the 77 vehicles falls inside this **54.4°** cone.
* **Three simulated figures, none in the photograph**: `agent_ped_936.0` at **16.2 m** with an orange box, a grey figure at the left edge, a third cut by the right edge.
* **The trees are the wrong trees.** The ginkgo top right is nearly bare in June; the photograph has a full street tree and a tall conifer. **707** of the **2610** trees are species-substituted, **12** outside the scale band.
* **Hard light from the wrong bearing.** Shadows fall down-left from high on the right; the recorded Sun at **284.2°** is ahead-left of the camera, and the overcast photograph has no cast shadows.
* **The lighting, in the record's terms**: **+4.78 stops**, under-lit; the photograph sits at **-1.202** stops from the metering convention and the render at **0.248**, **1.45** stops apart. Mean **0.583** against **0.3992** is that gap first. p05 **0.217** against **0.0583** is shaded road lifted towards middle grey against black under the photograph's cars; p95 **0.9055** against **0.9972** is sunlit wall on the shoulder against blown sky.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| one pale stone for four house colours; chroma 0.326× | one material family per facade class; `shellmat` varies tone, never hue | data, **DEVIATIONS J66** |
| windows proud of a plain wall; no arched heads or string courses | an extrusion with no openings cut; no source for the ornament | geometry, **DEVIATIONS J51** |
| no roofline or cornice in frame | level axis, 35 mm lens, no subject to tilt to | stated choice |
| doors in a repeated green-and-salmon livery | one door asset per entry class, livery authored not measured | material |
| carriageway empty, three SUVs in the photograph | placement is city-wide and the frame is not | verification |
| three simulated figures, none in the photograph | the simulation's own weekday crowd | — (not a gap) |
| a bare ginkgo for a full plane and a conifer | 707 of 2610 trees species-substituted | data |
| light from behind-right where the record's Sun is ahead-left; hard shadows against an overcast photograph | the lamp in `setup_world_and_sun` is rotated tilt-then-yaw and its beam goes toward the azimuth, so light comes from its opposite; the sky takes the azimuth itself; the chosen instant is clear, the photograph overcast | verification, not in the register; **DEVIATIONS J80** |
| under-lit at +4.78 stops, exposure 1.45 stops apart, p05 0.217 against 0.0583 | the median pixel is the shaded carriageway, metered to middle grey; the sunlit facade is pushed onto the shoulder | stated choice, **DEVIATIONS J83** |
| a square view across Decatur Street on an item named for Stuyvesant Avenue | camera on the photograph's GPS, 46.3 m down Decatur Street, looking along the avenue's bearing | reference |
