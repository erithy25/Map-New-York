# Midtown drive-through: Sixth Avenue at 45th Street

`drive_midtown_sixth_ave_45th` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:45th St 6th Av td 06 - 1156 Sixth Avenue.jpg by Tdorante10, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2018, 1920x1280. [Commons page](https://commons.wikimedia.org/wiki/File:45th_St_6th_Av_td_06_-_1156_Sixth_Avenue.jpg)

**Camera** — camera 40.75678, -73.98255 (NYC_TM -2748, 6306) z 20.1 m NAVD88 | azimuth 29.0deg pitch +0.0deg | 35 mm on 36 mm (54.4deg horizontal) | 1280x854. View direction: 29.0 deg as recorded in meta.json.  This item names no subject and the reference photograph's own view direction was not derived from the image (confidence: medium), so the two halves of this sheet are not guaranteed to face the same way -- compare them on street width, storey height and material, not on composition. Aim: level optical axis (the reference names no subject to aim at).

**Sun** — azimuth 95.4°, elevation 43.5° at 2018-06-21T09:30:00-04:00 (photograph year only; 21 June 09:30 assumed).

**In frame** — 5/5 building tiles (198,148 tris), 9 landmark models, 2,133 pavement polygons, 335 props, 14,173 facade-kit pieces; 4,500,130 triangles; ground mesh 211² at 2.0 m near / 40.0 m far.

**Verdict — the geometry is all there and none of it can be seen: a correct Sixth Avenue canyon with 14,173 kit pieces and 335 props, rendered at mean luminance 0.11 from under a pin oak in a shadowed canyon at a Sun position guessed from a year with no month or day**

## Re-rendered 2026-09-07 — this frame is why the agent clearance changed

**Before this pass it was one NPC's torso.** A pedestrian stood 1 m from the lens, which at a 1.6 m
eye and this set's 38° vertical field is **261 % of frame height**, so the picture was a woman in a
yellow top and nothing of Sixth Avenue. The clearance was 1.5 m and answered only "is a person inside
the lens".

It is now 3.5 m, derived from the frame — a 1.8 m body fills all of it at 2.6 m and 74 % of it at
3.5 m. **9 pedestrians were dropped over the observer** here, against 2 before, and **25.26 % of the
frame changed**. What was a torso is a group of people walking a sidewalk under the plane trees, with
the block face on the left and the avenue behind them.

**It is still a weak sheet, and for reasons the clearance does not touch.** The camera stands on the
pavement under a closed tree canopy: mean luminance **0.089**, which is deviation I16 (the render is
physically lit from the photograph's EXIF instant while the photograph was metered by its
photographer) compounded by foliage overhead. Sixth Avenue itself — the roadway, the traffic, the
storefronts the item names — is behind the trees and the crowd, so what the sheet compares is a
sidewalk. Of the 50 vehicles the simulation placed here, none is visible.

## What matches

* The camera stands on the photograph's own EXIF GPS, 35 m from the item's nominal viewpoint, on the roadway at 20.1 m NAVD88.
* The canyon geometry is right: Sixth Avenue's exceptional roadbed width, the deep sidewalks either side, the kerb line and the setback towers all match the avenue.
* The street trees are correct pin oaks in full leaf with proper canopies and trunks, planted along the east kerb where the census puts them.
* A bus shelter with its glazed side panels stands on the east sidewalk in the right place and at the right size.
* 2,133 pavement polygons place the crossing geometry (440 crosswalk, 107 median, 86 plaza) correctly for this intersection, and the kerb reveal is visible along the whole run.
* 9 landmark models are in range, so the towers closing the view uptown are modelled buildings.

## What does not match

* The frame is far too dark to read: mean luminance 0.109 against a 0.06 floor, so it passes the evidence gate by a small margin and still shows almost nothing. The cause is compound — a deep canyon, a camera under a tree canopy, and a Sun position taken from a photograph that records only the year (2018), for which the fallback is 09:30 on 21 June. The reference photograph is a flat overcast midday frame.
* The pairing is wrong again: the item looks uptown along Sixth Avenue, the photograph is a square-on study of the shopfronts at 1156 Sixth Avenue.
* The reference is dominated by things the model has none of: a Citi Bike dock with twenty bikes in it, Wells Fargo and La Bleu Optique shopfront signs, plate glass with interiors behind it, a poster in a window, a fire hydrant with its chain, and painted road markings.
* The Citi Bike dock is the sharpest single miss. props.parquet carries citibike_dock rows and the props kit exports citibike_dock_unit, citibike_kiosk and citibike_bike assets, so the data and the assets both exist, yet no dock is visible in this frame.
* No people, no vehicles, no traffic signals visible.
* The facade kit was capped by the triangle budget at 14,173 of 18,910 records in range.
* The photograph carries no time, only a year, so the sheet's Sun is an assumption rather than a measurement. That is stated on the sheet but it makes this pair unusable for any judgement about light.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| frame far too dark to read | a shadowed canyon plus a camera under a tree canopy plus a Sun taken from a year-only date; the reference is flat overcast | lighting |
| the two halves are of different subjects | the item names no subject and the reference stage assigned it the item's own azimuth | reference |
| no shopfront glass, signs or interiors | kit storefronts carry openings without glazing, lettering or interiors | material |
| no Citi Bike dock in a frame whose data has one | the dock rows are outside the 250 m prop radius or lost to the prop triangle cap; the assets exist | data |
| no people, vehicles or road markings | no traffic or crowd placement, and pavement polygons carry no stripe geometry | data |
| a quarter of the facade kit not drawn | the 4.5 M triangle budget is spent before the kit finishes | geometry |
