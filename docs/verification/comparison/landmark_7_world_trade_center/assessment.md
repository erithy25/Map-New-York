# 7 World Trade Center

`landmark_7_world_trade_center` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:7 World Trade Center April 2022 001.jpg by Kidfly182, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2022-04-30 13:02:58, 1920x2560. [Commons page](https://commons.wikimedia.org/wiki/File:7_World_Trade_Center_April_2022_001.jpg)

**Camera** — 40.712989, -74.011108 (NYC_TM -5158, 1471) at z 5.7 m NAVD88 | azimuth 294.7°, pitch +30.3° | 18 mm on 36 mm (73.7° horizontal, portrait) | 904x1206.

**Sun** — azimuth 185.4°, elevation 64.1° at 2022-04-30T13:02:58-04:00 (EXIF DateTimeOriginal); 927.9 W/m² direct normal, sky at strength 0.0308, Filmic, +3.37 stops.

**Subject** — 7 World Trade Center at 81.1 m.

**In the scene**, within 600.6 m of the camera and not all of it in frame — 6 building tiles (156,982 tris), 10 landmark models of which **1 can fall inside the 73.7° frame**, 22,694 pavement polygons (8,699 white, 4,311 roadbed, 4,220 sidewalk, 2,875 curb, 1,516 plaza, 575 crosswalk, 285 median, 162 yellow, 51 parking lot), 1658 props of the 4,766 in range, 5,099 kit pieces, 63 vehicles and 367 people; 4,500,161 triangles. Ground mesh 78,244 triangles, 0 holes. 20 city surfaces are dressed from the shared photographic catalogue.

## Verdict — the right tower from the photographer's own spot, in a frame that is tilted and cropped differently from the photograph's

**Both halves are of 7 World Trade Center, and the render's is the modelled building rather than a stand-in.** The photograph is a look straight up one curtain-wall face: blue-tinted glass, a spandrel line at every floor, the parapet and its window-washing rig at the top edge, sky either side, and a slender stepped tower reflected in the glass. The render is the same slab from the same side of the street, its horizontal banding at the same rhythm, its parallelogram footprint reading as a flat face with a sharp corner, its top cut off by the frame as the photograph's is. The camera is the photograph's own EXIF GPS, **68.0 m** from the item's nominal viewpoint on Church Street; the heading is the bearing from that GPS to the subject, **294.7°**, against the item's recorded **290.0°**; the instant is the EXIF second. The clearance walk found the GPS point inside `t_-6_1_tan_brick` and moved the camera **26.2 m** onto the nearest crosswalk, scoring on the subject sightline as J79 requires: **10 of 13** rays landed on the subject from the chosen point.

**The height is measured off the building, not a catalogue origin, and here that mattered.** The nearest catalogue origin to the subject's coordinate is `b_one_world_trade_center` at **104.3 m**, publishing **541.3 m**; the rule J74 replaced would have framed this sheet for a 541 m tower. The probe instead dropped **43 of 43** rays onto built fabric at the coordinate and reads **229.15 m** above a ground at **2.75 m**, off `lm_b_wtc_site.244`. That is the height of 7 World Trade Center to within a few metres. There is no catalogue figure to set against it: 7 WTC has no entry of its own and lives inside the composite `b_wtc_site`, whose one published height belongs to the composite's tallest part, not to this tower, so the probe is the only measurement of this building in the record.

**What the reader must not do is compare the two halves on proportion or on framing.** The subject's top stands **226 m** above a lens **83 m** away, **70°** above the horizon; the lens was widened from **35 mm** to the **18 mm** floor and the axis tilted **+30.3°**, and the record says the verticals converge (I18, tilt declared). The photographer tilted much further: the photograph contains no street, no podium and no neighbour, only the face and the sky. The render's bottom half is Barclay Street — a boro taxi, a street tree, lamp standards, a brown-brick block on the right — none of which the photograph was pointed at. The sightline record's `subject_visible` is J78's "at least one ray" rule; the fraction to read is **0.769**, with **3** rays into nothing above the parapet and **8** landing on `lm_b_wtc_site.245`, the same composite's fabric at **68.6 m**, nearer than the **138.1 m** range to the coordinate.

## What matches

* **The massing.** A tall, flat-faced glass slab with a sharp vertical arris, banded at every floor, and no setback — the render's tower has the same silhouette and the same band spacing as the photograph's face, and the top leaves the frame in both.
* **The plan extent is credible for the building.** The probed object's bounding box is **87.5 m** by **57.2 m**; the fan across the subject spans a half-angle of **17.58°** at **81.1 m**, and the face in the render is the width the photograph's face suggests from closer in.
* **The camera is the photograph's.** Position from EXIF GPS, heading derived from it, instant from EXIF; Sun at azimuth **185.4°**, elevation **64.1°**, **927.9 W/m²** direct normal, which is high midday light on a clear day, as the photograph's sky says.
* **The street is dressed as Lower Manhattan.** 5,099 kit pieces including **4,597** windows and **187** storefronts, **506** trees, **178** street lamps, **494** Citi Bike docks, **63** vehicles of which **5** are boro taxis and **367** people drawn for a Saturday at 13:00.

## What does not match

* **The glass.** The photograph's curtain wall is a saturated blue mirror carrying the sky and a reflected tower; the render's is a grey-blue diffuse surface with a pale frosted podium and a hard diagonal shadow across its lower third. Chroma **0.1312** against **0.3126**, a ratio of **0.42**, and most of that gap is the tower, which is most of the photograph.
* **The base.** 7 WTC's lower floors are the substation, clad in prismatic stainless steel; the render's base is a light translucent band with no such articulation.
* **The framing.** Pitch **+30.3°** against a photograph tilted steeply enough to exclude the ground; the render's lower half is street, taxi at **5.3 m**, tree and neighbouring brick, and none of it is in the reference.
* **The lighting, as stops.** The scene metered at **+3.37** stops (median linear **0.017445**; the physical rule alone would have given **+0.00**), below the +4 at which the record calls a scene under-lit. The photographer exposed **-0.779** stops from middle grey, the render sits at **0.222**; the p50 ratio of **1.387** and mean ratio of **1.29** are that difference in exposure convention first. The p05 gap, **0.196** against **0.1311**, is above the JPEG floor and is the render's open sky and pale podium where the photograph's shadows are the dark reflected cityscape.
* **The reflection.** The photograph's face carries a mirrored stepped tower to the east; the render's glass reflects nothing legible.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| a grey-blue diffuse curtain wall where the photograph is a blue mirror | the landmark model's glass material is a tinted diffuse surface, not a low-roughness reflector; the chroma the photograph measures is reflected sky | material |
| a translucent podium where the building has a stainless-steel substation base | the composite `b_wtc_site` model carries no base articulation for 7 WTC | geometry |
| the render's lower half is street and the photograph's is not | the lens was held at the 18 mm floor and tilted +30.3°, the least tilt that shows the subject at all; the photographer tilted further and framed the face alone | stated choice (I18, tilt declared) |
| render brighter at every percentile | metered development at +3.37 stops against a photograph exposed -0.779 stops from the same convention; not a fault of the city | — (not a gap) (**DEVIATIONS J83**) |
| no reflected tower in the render's glass | follows from the material: a diffuse surface cannot carry the Woolworth-direction reflection the photograph shows | material |
| 3 of 13 sightline rays into nothing, 8 on nearer fabric | the fan is sized to the measured 229 m height and 87.5 m width; rays above the parapet and onto `lm_b_wtc_site.245` are counted as the same fabric under the J78 continuity rule | verification (**DEVIATIONS J78**) |
