# Bronx County Courthouse

`landmark_bronx_county_courthouse` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Bronx County Courthouse, Concourse Village, Bronx - 20220616.jpg by Andre Carrotflower, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2022-06-16 13:12:25, 1920x1920. [Commons page](https://commons.wikimedia.org/wiki/File:Bronx_County_Courthouse,_Concourse_Village,_Bronx_-_20220616.jpg)

**Camera** — 40.825711, -73.925619 (NYC_TM 2100, 14000) at z 17.0 m NAVD88 | azimuth 70.0°, pitch +0.0° | 35 mm on 36 mm (54.4° horizontal) | 1044x1044.

**Sun** — azimuth 192.1°, elevation 72.2° at 2022-06-16T13:12:25-04:00 (EXIF DateTimeOriginal); 941.4 W/m² direct normal, sky at strength 0.0304, Filmic, +4.16 stops.

**Subject** — Bronx County Courthouse at 79.8 m.

**In the scene**, within 608.5 m of the camera and not all of it in frame — 4 building tiles (162,882 tris), 2 landmark models of which **1 can fall inside the 54.4° frame**, 24,013 pavement polygons (7,335 white, 6,715 sidewalk, 5,386 roadbed, 2,666 curb, 446 crosswalk, 436 parking lot, 413 plaza, 402 median, 214 yellow), 1402 props of the 1,486 in range, 6,890 kit pieces, 89 vehicles and 430 people; 4,500,159 triangles. Ground mesh 83,232 triangles, 0 holes. 16 city surfaces are dressed from the shared photographic catalogue.

## Verdict — the render is a street under an elevated railway with the courthouse a grey sliver at the top of it; the photograph is the courthouse filling its frame from the other side of the building

**These are not the same view, and the record says why before the picture does.** The photograph carries no camera GPS; its viewpoint is the item's "standard photographer position" at medium confidence, and the azimuth of **70.0°** is the bearing from that position to the subject coordinate, not a direction derived from the image. The photograph's own description places the photographer *at the south end of the Grand Concourse*, and the picture agrees: it looks up at a corner of the block from across a parked-up kerb, short flank left, long flank receding right, tilted enough that the cornice converges. The item's note says *the Grand Concourse at East 161st Street*, and the recorded coordinate is not on the Grand Concourse at all: the clearance probe found it **inside `t_2_13_roof_membrane`** and walked the camera **57.3 m** onto the nearest roadbed. The two halves face different ways from different sides of a building, and nothing on this sheet tests the courthouse's proportions.

**Where the camera ended up is under an elevated railway, and that is what the render is of.** A green-painted steel column fills the right quarter of the width from top to bottom (PIL over `render.png`: the columns from about **73 %** of the width to the right edge are green on more than four fifths of their pixels), a green box girder on X-braced bents crosses the frame between a third and a half of the height, and the lower half is sunlit roadbed with one yellow dash. This is the structures stage's elevated rail (B13/J24), **24,688** triangles over **4** tiles; the record does not name the line, and neither does this assessment. The clearance probe is satisfied — the axis clear for **78.2 m**, the nearest built thing `prop_tree_littleleaf_linden_small_54` at **8.3 m**, **-27.2°** yaw, **+27.2°** pitch (the canopy at top left), no agent within the **20 m** probe — because none of that asks about the girder or the column: the J79 shape.

**The subject is in the frame, barely, and the record's verdict is true in the J78 sense.** The fan, sized from the measured height (J74) at **25.42°** half-angle across and **13.3°** up, puts **9 of 13** rays on the subject, fraction **0.692**, the central ray landing at **64.2 m** on `lm_c_bronx_county_courthouse.0`; the rays that fail stop at **16.1 m** on `t_2_14_tan_brick`, the orange-brick block at top left. The landmark cone agrees: the Mario Merola Building is the one model in the cone, **109.1 m** off, **8.7°** off axis. In the picture it is the grey building with vertical piers, recessed window strips and a projecting band, wedged between the brick block and the column with its base behind the girder. The axis is level on purpose: the subject *would need +12 deg of tilt* (I18).

**The height probe measured the thing, and measured a low part of it.** All **43 of 43** rays land on `lm_c_bronx_county_courthouse.6` and read **39.94 m** above ground; the catalogue origin **35.4 m** away publishes **58.5 m**. The photograph shows why: a tall central block on lower wings, and the coordinate sits on a low part of an object **79.9 m** by **74.0 m** in plan — the J74 remainder.

## What matches

* **The courthouse model is where the courthouse is**, **8.7°** off axis, and the surface the probe measured is the landmark's own fabric (**43 of 43** rays), not a tile shell. Its pier-and-band elevation matches the photograph's fluted piers and window strips in kind.
* **The recorded azimuth and the bearing to the subject agree to 0.1°** (**70.0°** recorded, **70.1°** from the camera used): the render frames what the item aims at, however little shows.
* **The instant is the photograph's own** (EXIF), a Thursday drawn as a weekday crowd; the Sun at **72.2°** elevation is near-overhead in both halves; the photograph's shadows are short and the render's tree shadows fall almost straight down.
* **The street fabric is there**: **1,072** trees, **100** street lamps, **5** flagpoles, and **6,890** kit pieces including **4,779** windows, **119** quoins and **102** string courses. None of it is in this frame.

## What does not match

* **The whole composition.** The photograph is one building from base to cornice, ten parked vehicles along its kerb (counted at full size: a white estate, two silver SUVs, a black saloon, a dark SUV, a dark crossover, a white SUV, two white cars and a white box truck), one pedestrian between the cars three fifths of the way across, four street trees at the base. The render has no vehicle, and its people are fragments: about six pairs of legs behind the bents under the deck, at half height and three quarters of the way across, and one figure in blue jeans and a green top cut in half by the column at the right edge. The **89** vehicles and **430** people are elsewhere in the radius.
* **The elevated railway.** A column occupying the right quarter, a green girder across the middle with a plank-coloured band beneath it and X-braced bents under that. The photograph has no elevated structure.
* **A hand through the girder.** About two thirds of the way across and two fifths down, a pale hand and dark cuff protrude from the girder face with no body attached.
* **Hard sun against an overcast photograph.** The scene needed **+4.16** stops to read as a picture (the physical rule alone would give **+0.00**), which the record marks *under-lit*, above the **4** a photographer recovers hand-held. Developed so, the sunlit road tops the range (PIL: the lower-left roadbed exceeds display 0.7 on almost every pixel) and p95 is **0.8829** against the photograph's **0.7641**, while the median **0.4962** sits below the photograph's **0.5949** (ratio **0.834**) because girder, column and shaded road hold the middle. The photographer exposed **0.796** stops over the metered convention, the render **0.226**: **-0.57** stops apart. The p05 gap (**0.2163** against **0.1415**) is sun-versus-cloud, not a fault of the city.
* **Chroma at half**: **0.068** against **0.1224**, ratio **0.556**, green steel, orange brick and grey concrete against warm limestone and yellow spandrels.
* **No sky.** The photograph is two fifths cloud; the render's sky is confined to slits beside the column.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the whole composition: different side, different direction, the subject a sliver | no GPS, so the item's standard viewpoint; its coordinate is inside `t_2_13_roof_membrane` and was walked **57.3 m** to a roadbed under the railway; the photographer stood at the south end of the Grand Concourse | reference; **DEVIATIONS J57** (a viewpoint coordinate off the place it names) |
| the elevated railway filling the right quarter and the middle | the walk scores eye-level clearance (**78.2 m**) and the subject fan (**9 of 13**), neither of which the column or girder intersects; a correct structure in the wrong frame | verification; **DEVIATIONS J79** |
| the courthouse read at **39.94 m** where the catalogue holds **58.5 m** | the coordinate sits on a lower wing of a **79.9 × 74.0 m** object and the probe measures what stands above the coordinate | verification; **DEVIATIONS J74** |
| no vehicles, fragments of people | agents placed city-wide by density profile; the nearest is beyond the **20 m** probe | verification |
| a hand through the girder face | a pedestrian body placed inside the volume of the elevated structure; placement tests walkable surface, not the structures' solids | verification |
| hard sun against cloud; p05 **0.2163** against **0.1415**, p95 **0.8829** against **0.7641** | the Sun is computed from the EXIF instant at **941.4 W/m²**; the record holds no weather and the day was overcast | reference |
| developed at **+4.16** stops, over the hand-held limit | metered development puts the median at middle grey; a frame half green steel and shaded road meters dark and is pushed | **DEVIATIONS J83** |
| chroma **0.068** against **0.1224** | one material family per facade class at authored albedo | material; **DEVIATIONS J66** |
| no sky | the column and deck close the upper frame at a level axis | — (not a gap; a consequence of the viewpoint) |
