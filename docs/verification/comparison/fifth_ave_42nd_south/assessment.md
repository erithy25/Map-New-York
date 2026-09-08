# Fifth Avenue at 42nd Street (NYPL), street view looking south

`fifth_ave_42nd_south` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:01-21-2017 - Women's March on NYC looking up 5th Ave (10796).jpg by Rhododendrites, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2017-01-21 13:41:25, 1920x1440. [Commons page](https://commons.wikimedia.org/wiki/File:01-21-2017_-_Women%27s_March_on_NYC_looking_up_5th_Ave_(10796).jpg) — the photograph's own view direction was **not** derived from the image (confidence medium).

**Camera** — 40.753505, -73.980874 (NYC_TM -2607, 5942) at z 23.4 m NAVD88 | azimuth 209.0°, pitch +0.0° | 35 mm on 36 mm (54.4° horizontal) | 1208x906. The camera stands on **this photograph's own EXIF GPS**, 40.1 m from the item's recorded viewpoint, and was **not moved**: the viewpoint is in open air on the ground, the view azimuth is clear for 150 m, the nearest built thing in the frame is `prop_lamp_cobra_davit_2` 8.3 m away and the nearest simulated agent is `agent_ped_1105.9` 12.1 m away.

**Sun** — azimuth 204.6°, elevation 25.7° at 2017-01-21T13:41:25−05:00, from the photograph's own **EXIF DateTimeOriginal**; 727.4 W/m² direct normal, sky at strength 0.0376, Filmic, **+0.75 stops**. That date is a **Saturday** and the crowd was drawn for one. Both the instant and the position are the photograph's own.

**In the scene**, within 740.1 m of the camera and not all of it in frame — 6 building tiles (300,026 tris), 9 landmark models of which **2 can fall inside the 54.4° frame**, 28,814 pavement polygons (14,594 white marking, 5,267 sidewalk, 4,173 roadbed, 3,464 curb, 717 crosswalk, 269 median, 231 plaza, 88 yellow marking, 11 parking lot), 535 props of the 1,249 in range, 4,623 kit pieces, 53 vehicles and 258 people; 4,500,229 triangles. Ground mesh 88,186 triangles, 0 holes. 20 city surfaces are dressed from the shared photographic catalogue.

## Verdict — the same street, the same afternoon, and an event the simulation has no notion of

**The photograph is the Women's March.** Fifth Avenue on 21 January 2017 filled kerb to kerb with a demonstration, shot from inside it: placards fill the lower two thirds of the frame and the avenue itself is visible only as a slot of towers above the heads. The render is the same avenue at the same instant of the clock — the Sun is from the photograph's own EXIF, the crowd was drawn for the Saturday that date is — carrying an ordinary Saturday afternoon's traffic: yellow taxis, a green boro taxi, black cars, people on a marked crossing.

**Read as a comparison of the street it holds up, and read as a comparison of the pictures it cannot.** The canyon walls, the far tower slot, the winter-bare trees and the light all correspond. The crowd does not, and no version of this simulation would produce it: a march is a scheduled event, and this build has no source of scheduled events. That is the honest statement of this pairing, and it is a different thing from the render being empty. An earlier version of this assessment called the render "an empty grey slab with nothing alive in it at all"; the record says **53 vehicles and 258 people**, and the frame shows them.

## What matches

* **The canyon is the same canyon.** Setback masonry on the left, a taller slab on the right, and the avenue narrowing to a bright slot of towers at the far end — the same slot, in the same place in the frame, in both halves.
* **The trees are bare and the date is why.** The reference is 21 January and the leaf-off variants are selected from the photograph's own date; **236 trees** stand within 290.1 m at a mean scale of **0.906**, none outside the declared band. The reference's own street trees, above the placards on the left, are bare in the same way.
* **The light is the photograph's own light** — a 25.7° January sun bearing 204.6°, almost straight down the avenue's 209°, which is why the far end is bright in both halves and the near walls are not.
* **The road is drawn and marked.** 4,173 roadbed, 3,464 curb and 5,267 sidewalk polygons carry asphalt and concrete from their own material names; **14,594 white and 88 yellow marking polygons** are in range, with a lane line running up the middle of the frame and a continental crossing across it.
* **The fleet is a Fifth Avenue fleet**: **22 yellow taxis**, 13 boro taxis, 9 black cars, 5 sedans, 2 vans, an SUV and a DSNY truck.
* **The crowd is the simulation's own** — 258 people on a Saturday afternoon, 62 at LOD1 and 196 at LOD2, with 168 dropped for standing in the carriageway without crossing and 1,299 for the triangle budget.
* **Both landmark models that can fall inside the frame are the right two**: the New York Public Library at 122 m and the Empire State Building at 697 m, the latter 7.3° off axis — and the reference's own far slot is the Midtown towers south of 40th Street.
* Nothing was dropped for being missing: 6 building tiles, 0 LOD substitutions, 0 pavement polygons dropped, 0 holes in the ground.

## What does not match

* **The photograph's subject is a crowd of tens of thousands and the render's street is open.** This is not a fidelity gap in the city; it is the absence of a scheduled-event source. The simulation places a Saturday afternoon's pedestrians from its own model and has nothing that says "on this date this avenue was closed and filled".
* **The frame is darker and less colourful than the photograph**: mean **0.2789** against **0.434** (**0.643×**), standard deviation **0.1946** against **0.2586** (**0.753×**), chroma **0.0504** against **0.086** (**0.586×**), 95th percentile **0.7362** against **0.8681**, 5th percentile **0.0403** against **0.0566**. Part of that is the crowd itself — a mass of coats, skin and painted placards a metre from the lens carries colour a street surface does not — and part is J66's remainder, one material family stated per facade class.
* **The two halves are not guaranteed to face the same way.** The item names no subject and the photograph's direction was never derived from the image, so this sheet supports a comparison of street width, storey height and material rather than of composition. That both halves happen to look down the same slot is a good outcome, not a guaranteed one.
* **714 props in range were not placed** — triangle budget 1,106,185 — along with part of the kit (cap 970,651) and 9 opaque impostor cards. **17 point props have no asset at all**: 7 artworks, 4 memorials, 2 parks buildings, a drinking fountain, a comfort station, an RTPI sign and a vending machine.
* **207 of the 236 trees are species-substituted**, drawn at the height their own rows record but as the nearest species by size and taxon.
* **The facades are flatter than the avenue is.** 4,623 kit pieces stand in range, of which **4,466 are windows** and only 5 cornices, 7 parapets and 5 string courses: the walls are extrusions with openings where the photograph's carry cornices, belt courses and modelled bases.
* **No placard, banner, sign or shopfront lettering is legible** anywhere in the render, and the photograph is almost entirely made of lettering.
* **11 vehicles were dropped for being over the observer** and 33 for not being on a carriageway — the record names each rule, and a Saturday on Fifth Avenue has more traffic than the 53 that survived them.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the photograph is a mass demonstration and the render is an ordinary Saturday | there is no source of scheduled events in this build; the crowd model produces a day-type's pedestrians and nothing that closes an avenue | **data — no source exists** |
| mean 0.643×, chroma 0.586× | a crowd of coats and painted placards a metre from the lens carries colour a street surface does not, plus one material family stated per facade class (J66) | reference + material |
| the two halves may not face the same way | the item names no subject and the photograph's direction was never derived from the image (confidence medium) | reference |
| 714 props and part of the kit unplaced | triangle budgets 1,106,185 and 970,651, declared on the sheet | performance |
| 17 point props with no asset | artworks, memorials, parks buildings, a drinking fountain, a comfort station, an RTPI sign and a vending machine have no modelled asset; they stay unplaced rather than become the wrong object (J22, J23) | geometry |
| 207 of 236 trees species-substituted | no modelled species matched exactly; the nearest by size and taxon was used | data |
| flat facades, almost no cornice or belt course | the shell is extruded from a footprint and the kit's cornice is a generic profile; the classifier has no source for a modelled one | geometry |
| no legible lettering anywhere | shopfront signage carries real business names as data but nothing resolves them to geometry at this distance (B15a), and placards are not a thing this build models at all | geometry |
| 44 vehicles dropped by rule | over the observer, or not on a carriageway; each rule is named in the record | verification |
