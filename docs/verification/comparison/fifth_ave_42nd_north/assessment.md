# Fifth Avenue at 42nd Street (NYPL), street view looking north

`fifth_ave_42nd_north` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:43rd St 5th Av td (2018-05-18) 21.jpg by Tdorante10, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), 2018, 1920x1280. [Commons page](https://commons.wikimedia.org/wiki/File:43rd_St_5th_Av_td_(2018-05-18)_21.jpg) — the photograph's own view direction was **not** derived from the image (confidence medium).

**Camera** — 40.754156, -73.980559 (NYC_TM -2581, 6014) at z 22.2 m NAVD88 | azimuth 29.0°, pitch +0.0° | 35 mm on 36 mm (54.4° horizontal) | 1280x854. The camera stands on **this photograph's own EXIF GPS** and was **not moved**: the viewpoint is in open air on the ground, the view azimuth is clear for 150 m, the nearest built thing in the frame is `prop_sign_mta_bus_stop_5` 17.5 m away and the nearest simulated agent is `agent_ped_748.10` 3.3 m away. That GPS is **186.8 m** from the item's recorded viewpoint — inside the 250 m at which it can still be the same view, and far enough that the two are not the same corner.

**Sun** — azimuth 95.4°, elevation 43.5° at 2018-06-21T09:30−04:00; 860.0 W/m² direct normal, sky at strength 0.0328, Filmic, **+0.00 stops**. The photograph carries a **year only**, so 21 June 09:30 is assumed. That date is a **Thursday** and the crowd was drawn for a weekday. **This is the weakest input on the sheet and it decides most of what follows.**

**In the scene**, within 886.8 m of the camera and not all of it in frame — 6 building tiles (339,572 tris), 13 landmark models of which **6 can fall inside the 54.4° frame**, 36,632 pavement polygons (20,683 white marking, 5,800 sidewalk, 4,522 roadbed, 3,981 curb, 927 crosswalk, 324 median, 282 plaza, 100 yellow marking, 13 parking lot), 436 props of the 2,477 in range, 3,903 kit pieces, 54 vehicles and 250 people; 4,500,130 triangles. Ground mesh 95,026 triangles, 0 holes. 20 city surfaces are dressed from the shared photographic catalogue.

## Verdict — the street is populated, marked and textured, and it is rendered at a quarter of the photograph's brightness because the file records only a year

**Both halves look north up Fifth Avenue between the same kind of walls, and the render is no longer the empty slab this sheet used to show.** A continental crosswalk runs across the foreground with pedestrians on it — a man in a tan coat mid-stride, a child, a figure in a hi-vis vest at the kerb — a red hydrant stands on the near sidewalk, a scaffold shed runs along the left frontage, an MTA bus-stop sign stands at the right kerb, and vehicles are drawn up at the far kerb where the avenue recedes between towers. An earlier version of this assessment said the frame had "no vehicles, no people, no markings, no shopfronts". Every one of those four is now false, and the record says by how much: **20,683 white and 100 yellow marking polygons**, **54 vehicles and 250 people**, **72 storefront pieces**, **927 crosswalk polygons**.

**The frame is a quarter of the photograph's brightness — mean 0.113 against 0.4557 — and the cause is one stated choice.** The photograph carries a year and nothing finer, so the Sun falls back to 21 June at 09:30, bearing **95.4°**. Fifth Avenue runs 29°. A morning sun almost due east puts the whole west-side canyon this camera stands in into its own shadow, and the reference was taken under a bright overcast that has no shadow anywhere. The render is not dark because the city is dark; it is dark because the instant is assumed and the assumed instant is the wrong one for this view.

## What matches

* **The street type is right.** A wide avenue between a continuous masonry wall on the left and setback towers on the right, receding to a bright slot of sky. That is Fifth Avenue north of 42nd Street and it is what both halves show.
* **The crossing is drawn as a crossing.** Bold separate white bars with asphalt between them — a continental crosswalk, not a painted slab — with **927 crosswalk polygons** in range and pedestrians standing on it.
* **The sidewalk shed is there and it is in the photograph too.** A dark green scaffold band runs along the left frontage at ground level in both halves; the reference's carries Urban Outfitters signage over the same structure.
* **The crowd is the simulation's own** — 250 people at 09:30 on a weekday, 5 at LOD0, 44 at LOD1 and 201 at LOD2, with 105 dropped for standing in the carriageway without crossing and 830 for the triangle budget.
* **The fleet is a Midtown fleet**: 13 yellow taxis, 12 boro taxis, 9 black cars, 9 sedans, 5 box trucks, 4 SUVs, an MTA bus and a van.
* **The street furniture is the right street furniture**: 53 street lamps, 33 hydrants, 12 bus-stop signs, 12 flagpoles, 5 bus shelters, 5 newsstands, 19 bike racks, 2 LinkNYC kiosks, 3 subway entrances, 6 steam vents and 86 rooftop cooling towers.
* **Six landmark models can fall inside the frame** — 30 Rockefeller Plaza at 554 m, St Patrick's at 608 m, MoMA at 853 m, the Seagram Building at 856 m, Lever House at 888.5 m and the Billionaires' Row corridor at 1,166 m. The count on the caption is a scene count and the record distinguishes the two (J61).
* Nothing was dropped for being missing: 6 building tiles, 0 LOD substitutions, 0 pavement polygons dropped, 0 holes in the ground.

## What does not match

* **The frame is four times darker than the photograph and the assumed instant is why**: mean **0.113** against **0.4557** (**0.248×**), standard deviation **0.117** against **0.236** (**0.496×**), 5th percentile **0.016** against **0.0625**, 95th percentile **0.4136** against **0.7463**. The photograph is a bright overcast with no shadow in it; the render is a 43.5° sun bearing 95.4° down an avenue running 29°, which is grazing incidence on the wall that fills the left half and full shadow on the pavement the camera stands on. **No part of this gap is a claim about the city's materials** — it is a claim about a date nobody recorded.
* **Chroma is the closest of any sheet in the set and still short**: **0.0303** against **0.0432**, a ratio of **0.701**. The photograph is itself nearly colourless — a grey overcast over grey stone — which is why the ratio flatters here; on a sunlit reference the same surfaces read far lower.
* **The camera is 186.8 m from the item's recorded viewpoint.** It stands where the photograph's own GPS says the picture was taken, which is the better of the two, but 187 m up Fifth Avenue is a different block: the reference looks across 42nd Street at the library's corner and the render looks up the avenue from nearer 43rd.
* **No vehicle stands in the near foreground.** The photograph's subject is effectively a yellow taxi crossing the frame at ten metres; the render's 54 vehicles are all further up the avenue. Placement is city-wide and the frame is not.
* **2,041 props in range were not placed** — triangle budget 953,045 — along with part of the kit (cap 683,120) and 9 opaque impostor cards. **10 point props have no asset at all**: 7 artworks, a parks building, a comfort station and an RTPI sign.
* **114 of the 137 trees are species-substituted**, drawn at the height their own rows record (mean scale **0.926**, none outside the band) but as the nearest species by size and taxon.
* **The facades are flatter than the avenue is.** 3,903 kit pieces stand in range and only 3 cornices, 6 parapets and 3 string courses among them: the towers on the right are extrusions with windows, where the photograph's masonry carries a cornice, a belt course and a modelled shopfront band.
* **No sign, awning text or shop name is legible**, and the photograph's own middle ground is a shopfront band under a shed with lettering across it.
* **The two halves are not guaranteed to face the same way.** The item names no subject and the photograph's direction was never derived from the image, so this sheet supports a comparison of street width, storey height and material — not of composition.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| mean 0.248×, 5th percentile 0.016 against 0.0625 | the photograph carries a year and nothing finer, so the Sun is assumed at 21 June 09:30 bearing 95.4°, which puts an avenue running 29° into its own shadow; the reference is a shadowless overcast | **reference — the largest single cause on this sheet** |
| chroma 0.701× | one material family is stated per facade class, and the reference is itself nearly colourless so the ratio flatters (J66) | material |
| camera 186.8 m from the recorded viewpoint | it stands on the photograph's own EXIF GPS, which is the better of the two positions and is a different block | reference |
| no vehicle in the near foreground | placement is city-wide and the frame is not; none of the 54 falls in the near carriageway | verification |
| 2,041 props and part of the kit unplaced | triangle budgets 953,045 and 683,120, declared on the sheet | performance |
| 10 point props with no asset | artworks, a parks building, a comfort station and an RTPI sign have no modelled asset; they stay unplaced rather than become the wrong object (J22, J23) | geometry |
| 114 of 137 trees species-substituted | no modelled species matched exactly; the nearest by size and taxon was used | data |
| flat facades, almost no cornice or belt course | the shell is extruded from a footprint and the kit's cornice is a generic profile; the classifier has no source for a modelled one | geometry |
| no legible signage | shopfront signage carries real business names as data but nothing resolves them to geometry at this distance (B15a) | geometry |
| the two halves may not face the same way | the item names no subject and the photograph's direction was never derived from the image (confidence medium) | reference |
