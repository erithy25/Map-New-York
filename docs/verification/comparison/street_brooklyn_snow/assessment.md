# Snow on a Brooklyn street

`street_brooklyn_snow` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Winter snow storm - Flickr - spurekar.jpg by spurekar, CC BY 2.0 (https://creativecommons.org/licenses/by/2.0), taken 2020, 1280x853. [Commons page](https://commons.wikimedia.org/wiki/File:Winter_snow_storm_-_Flickr_-_spurekar.jpg) — the file carries **no camera GPS**, its view direction was not derived from the image, and its viewpoint confidence is **low**, so nothing ties it to Park Slope beyond the fetch's own query. Its Commons description is one line: *"A nor'easter just before the holidays. Food delivery doesn't stop."* A courier in an orange jacket pushes a bicycle through unploughed snow with a Caviar thermal box on his back, snow falling hard enough to erase the block behind him, sodium lamps and a traffic signal burning orange through the white, parked cars buried to their sills, and no kerb line visible anywhere.

**Camera** — 40.677, -73.98 (NYC_TM -2536, -2554) at z 15.677 m NAVD88, a 1.6 m standing eye over terrain read at 14.077 m — the 10th percentile of 113 samples within 12.0 m | azimuth 30.0°, pitch 0.0° | 35 mm on 36 mm (54.432° horizontal) | 1280x852. The camera stands on the item's recorded viewpoint, Fifth Street at Seventh Avenue, which the item's own note calls a *"representative block"*. It was **not moved**: the nearest built thing is `t_-3_-3_red_brick` **13.4 m** away, no simulated agent stands within 60 m, and the view azimuth is clear for **116 m**. The axis is level because the item names no subject, so this record carries **no height probe, no sightline and no visible fraction** — `subject_note` reads *"the item names no point subject"*. The record states the comparison's terms before any assessment can: *"the two halves of this sheet are not guaranteed to face the same way -- compare them on street width, storey height and material, not on composition."*

**Sun** — azimuth 85.4°, elevation 32.1° at 2020-06-21T08:30:00-04:00. Not measured: *"photograph year only, 21 June assumed, and 08:30 **chosen**, not measured: of the hours that put the Sun above 20 deg it is the one whose bearing (85 deg) comes closest to the view azimuth (30 deg), 55 deg off, so the Sun is behind the camera and lights what it looks at"*. 788 W/m² direct normal, Nishita sky, Filmic, **+2.07 stops**. Metered: **2.073 stops** on a linear median of **0.042777** against a physical rule of 0.42 — a well-lit frame by the measurement, and not under-lit.

## Verdict — the sheet whose subject is a snow storm is rendered on the summer solstice, in full leaf, under a clear sky

**The instant is 21 June.** The photograph carries a year and nothing else, so `photo_instant` falls through to `pick(dt.date(year, 6, 21), "photograph year only, 21 June assumed")` — the longest day of the year — and J80's hour chooser then picks 08:30 to put the Sun behind the camera. **17 of the 172 sheets are lit on an assumed 21 June** for the same reason, and on sixteen of them the assumption costs only precision. Here it inverts the sheet. The item is called *Snow on a Brooklyn street*; the fetch asked for *"Brooklyn snow street brownstones"*; the photograph is titled *Winter snow storm*; and its own stored description says *"A nor'easter just before the holidays"* — late December, in the metadata this render reads, in the same file as the year it did read. Screened across the pass, **two sheets name snow, ice or winter in their item name or photograph title. The one with an EXIF timestamp gets 23 February. This one gets the solstice.**

**So the canopy is in full leaf too.** 21 June is outside the leaf-off window, so the render's street trees carry their summer crowns, big and green and shading the sidewalk, on a comparison against a street where nothing green is visible and nothing is meant to be.

**And even on the right date there would be no snow.** The render's snapshot request carries x, y, heading, hour, day type, seed and headlights and no weather at all, so `rain_mm_h` stays 0.00, `temperature_c` 15.0 and `snow_cover` 0.00 on every one of the 172 sheets (J97). This sheet is the plainest statement of that gap in the whole set: its entire subject is a weather state the renderer has no field for. The MTA bus sheet is the other one and at least gets February.

**What can still be compared is the fabric, and there the two halves agree.** Both are a low-rise Brooklyn street of four- and five-storey brick with retail at grade: the render draws **4,436 kit pieces** over its 7 building tiles, among them **2,353 windows, 385 storefronts, 369 fire escapes, 237 entrance doors, 131 quoins, 126 cornices and 82 string courses**, and the zigzag fire escapes down the left-hand elevations are the same feature the photograph shows above the awnings. Street width, storey height and material — the three things the record asks a reader to compare — hold up.

**The tone is the mirror of what a snow photograph does to a camera.** The reference's median sits **1.724 stops** above the grey convention and its 5th percentile is **0.41**: falling snow is a diffuser, so the photograph has no shadows at all and almost no dark tone. The render, metered to 0.252 above grey with real sunlight and real shadows, is **1.472 stops** darker at the median and carries **1.178×** the contrast. Chroma runs the other way and hard: **0.302**, the render carrying under a third of the photograph's colour, because the reference's picture is an orange delivery box and orange sodium lamps against white and the render's is green trees and grey asphalt. Every one of those four ratios is measuring the weather rather than the model.

**The traffic mix is right for this borough.** 62 vehicles: **10 boro taxis to 5 yellow medallion cabs**, plus 28 sedans, 11 SUVs, 3 black cars, 2 vans, an MTA bus, a box truck and an ambulance. Park Slope is outside the street-hail exclusion zone, where the green cab is the licensed fleet, and this frame draws twice as many green as yellow — the opposite of the inversion J105 measures across the pass, and worth recording as a frame where the mix reads correctly. **No agent was dropped for the triangle budget**, so this is the crowd the simulation actually produced.

**The props budget bit hard.** 792 placed of 3,305 in range against a cap of 1,129,671 triangles: **2,513 dropped, 76 per cent, the 25th largest drop fraction of the 170 records that report one**, and **2,407 of them tree rows**. 424 trees survive, 117 from modelled branches inside 120 m and 307 as six-triangle impostor cards, with 133 species substituted and 23 cards dropped.

**And the ground under the near field is clean.** Of **513** park-ground samples within 150 m, **none** sits below the terrain and the tightest clears by **0.06 m**; beyond 400 m, where the grid coarsens to 40.0 m, 19 per cent of 1,024 samples sit under it.

## What matches

* **The street is the right kind of street**: four- and five-storey brick with retail at grade, cornices, string courses and 369 fire escapes.
* **The camera was not moved** and had no reason to be: 116 m of clear azimuth, nearest built thing 13.4 m away.
* **The record declares its own limits first** — no subject, low confidence, no guarantee the halves face the same way, and an instruction on what to compare instead.
* **The instant is labelled as chosen, not measured**, with the reasoning printed in full (J80).
* **10 boro taxis to 5 yellow cabs** in Park Slope, which is the correct way round.
* **No agent dropped for the triangle budget**: 62 vehicles and 208 people as simulated.
* **Building tiles complete**: 7 of 7, 568,220 triangles, none missing, none LOD-substituted.
* **Nothing under the terrain in the near field**: 0 of 513 samples, minimum clearance +0.06 m.
* **The frame is well lit by the measurement**: 2.073 stops, comfortably under the 4-stop threshold.

## What does not match

* **The summer solstice on a snow sheet.** 21 June against a photograph titled *Winter snow storm* whose own description says *"a nor'easter just before the holidays"*.
* **Full summer canopy** on a street where the reference shows no leaf at all.
* **No snow, no falling snow, no slush, no buried cars, no snow on the roofs or the awnings** — the renderer has no weather field (J97).
* **A clear Nishita sky and hard shadows** against a photograph with no shadow anywhere in it.
* **1.472 stops darker at the median, 1.178× the contrast, and 0.302 of the chroma** — all four ratios measuring the storm rather than the city.
* **No courier, no cargo bicycle, no delivery box**: the fleet exports cyclist bodies without a rider, so 7 were dropped rather than drawn, and the reference's whole foreground is a cyclist.
* **No traffic signal, no street-name blade, no parking sign** at Fifth and Seventh, or anywhere in the pass (J110); the photograph's brightest object after the delivery box is a glowing signal head.
* **No lit lamps.** The photograph's sodium lamps are burning at midday because the storm has taken the light; the render's 82 street lamps are unlit geometry on a sunny morning.
* **76 per cent of the props in range dropped**, 2,407 of them tree rows.
* **Five of the seven structures tiles have no file**, so the scene's 26,180 triangles of structures come from two.
* **Nothing ties the photograph to this block.** It carries no GPS, its heading was not derived, and the item's own note calls the viewpoint representative rather than the photographer's.

## Measured for this assessment

| figure | where it comes from |
|---|---|
| 17 of the 172 sheets are lit on an assumed 21 June | the `sun.time_source` and `sun.local` of every record in the pass, counting those whose local date falls on 21 June with a source of "photograph year only" |
| the fallback is a literal 21 June in the code | `pick(dt.date(year, 6, 21), "photograph year only, 21 June assumed")` in `blender/verify/render_sheets.py`, with a second fallback to 21 June 2024 when no year exists either |
| two sheets in the pass name snow, ice or winter in their item name or photograph title, and this is the only one whose instant is not in the leaf-off window | screening every record's item name, slug and `reference_photo.title` for winter words, against the rendered local date and the `leaf_off` rule |
| the photograph's own description says it is a nor'easter just before the holidays | the `description` field of candidate 1 in `docs/verification/reference/street_brooklyn_snow/meta.json`, which the fetch stored and the instant chooser does not read |
| 792 props placed of 3,305 in range, 76 per cent dropped, the 25th largest drop fraction of the 170 records that report one | the `props.placed` and `props.dropped_for_budget` of every record in the pass, ranked |
| 4,436 kit pieces | the sum of this record's `scene.kit.per_category`, whose `total` is null |
| 21 June is outside the leaf-off window | the `leaf_off` rule in `blender/verify/render_sheets.py` (J97) |

## Cause of each gap

| gap | cause | class |
|---|---|---|
| a snow sheet lit on the summer solstice | `photo_instant` falls back to a fixed 21 June whenever a photograph carries only a year, and nothing checks the assumption against the item, the fetch query or the description the fetch already stored (J80's fallback, and new here) | **verification — open, and cheap: the description is in the file** |
| full summer canopy | the leaf switch reads the same assumed date (J97) | verification — consequent on the above |
| no snow at any date | the snapshot request carries no weather at all, so rain, temperature and snow cover are the defaults on all 172 sheets (J97) | **verification — open** |
| a clear sky and hard shadows | nothing in this build reads a historical sky | reference — no source exists |
| no courier on a bicycle | the fleet exports cyclist, e-bike and pedicab bodies without a rider, so the simulation's 7 were dropped rather than drawn | **runtime — open** |
| the lamps are unlit at midday | headlights and lamps follow the clock, not the light level, and an 08:30 June instant is full daylight | verification — declared |
| no signage of any kind | the verification renderer never reads the sign or signal export, and its props catalogue has no kind for either (J110) | **verification — open** |
| 76 per cent of props dropped | a 1,129,671-triangle cap against 3,305 objects in range, most of them trees; the drop is recorded per kind rather than hidden | performance — declared |
| five of seven structures tiles have no file | the B13 remainder | data — open |
| nothing ties the photograph to Park Slope | the file has no GPS and the fetch ran on text queries with a geosearch radius of 0, so the pairing rests on the query words alone (J71's family) | **verification — declared on the sheet itself** |
