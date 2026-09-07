# Charging Bull

`landmark_charging_bull` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Bowling Green NYC Feb 2020 15.jpg by Epicgenius, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2020-02-05 09:35:51, 1920x1440. [Commons page](https://commons.wikimedia.org/wiki/File:Bowling_Green_NYC_Feb_2020_15.jpg)

**Camera** — camera 40.70580, -74.01341 (NYC_TM -5358, 646) z 9.0 m NAVD88 | azimuth 179.2deg pitch -2.4deg | 35 mm on 36 mm (54.4deg horizontal) | 1208x906. View direction: 179.2 deg, the bearing from this photograph's own GPS position to Charging Bull; heading and position both come from the photograph.  The item's recorded azimuth is 217.2 deg, 38.0 deg away, and belongs to its nominal viewpoint. Aim: aimed at Charging Bull 34 m away, at its mid-height (the charging_bull model's 3 m height); -2.4 deg from horizontal.

**Sun** — azimuth 139.4°, elevation 23.0° at 2020-02-05T09:35:51-05:00 (EXIF DateTimeOriginal).

**In frame** — 3/3 building tiles (39,704 tris), 10 landmark models, 1,484 pavement polygons, 727 props, 9,253 facade-kit pieces; 4,500,228 triangles; ground mesh 199² at 2.0 m near / 40.0 m far.

**Verdict — the bull is modelled and the camera is aimed at it — the subject-bearing rule overrode a recorded azimuth 38 deg out — but the sculpture reads as a small dark lump on an empty plaza, and the near half of the frame is bare ground**

## What matches

* Charging Bull exists as a landmark model and is in the frame at 34 m, at the right size (3 m high) and on the right traffic island at the north tip of Bowling Green.
* The heading is measured, not assumed: the bearing from this photograph's own GPS to the bull is 179.2 deg, the item's recorded azimuth is 217.2 deg, and the sheet states that the 38 deg disagreement was resolved in favour of the subject.
* The aim rule tilted the axis -2.4 deg to centre a 3 m subject 34 m away, inside the 8 deg limit.
* The plaza furniture is right in kind and position: benches along the island, flagpoles carrying New York City flags, bishop's-crook lamps, bare February street trees, and a green sidewalk shed on the Broadway frontage.
* 1,484 pavement polygons place the island, the roadbed and 326 crosswalk polygons correctly, and the kerb line reads across the frame.
* The Sun is from the photograph's own EXIF instant (2020-02-05 09:35:51 EST, elevation 23.0 deg), and the flat winter light matches the reference's overcast.

## What does not match

* The bull has no surface and no form to speak of at this distance: it is a dark rounded mass where the reference's own subject is polished bronze with modelled musculature, horns and a raised tail.
* The lower 45 % of the frame is bare grey ground with no texture, no granite security blocks, no bike lane, no road markings and no kerb detail — the reference's foreground is all of those.
* No people. The reference has perhaps thirty, several of them beside the bull, which is what gives the sculpture its scale.
* No vehicles, no traffic signals on their mast arms, no street signs, no wayfinding kiosk — all present and prominent in the reference.
* The buildings are flat pale solids: the reference's Cunard Building and 26 Broadway carry rusticated stone, deep window reveals and cornices, and the render has none.
* The facade kit was capped by the triangle budget at 9,253 of 13,758 records in range.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the bull has no surface | the charging_bull model is a coarse form with a flat base colour and no bronze material | material |
| bare foreground | pavement polygons carry a kind but no texture, markings or kerb detail, and there is no dataset of security blocks or bike-lane paint | material |
| no people | no crowd placement feeds the verification scene | data |
| no vehicles, signals or signs | no traffic or signage placement feeds the verification scene | data |
| flat stone buildings | shells carry a per-material base colour with no texture or mouldings | material |
| a third of the facade kit not drawn | the 4.5 M triangle budget is spent before the kit finishes | geometry |

## Re-render note, 2026-09-07

Re-rendered against the corrected `b_wtc_site` model — the World Trade Center site stood 3.5 m too high, its plaza was an unbroken 520 x 520 m quad over both memorial pools, and its 220 oaks each carried a merged impostor card (`docs/verification/landmarks/REPORT_B.md` §12). Measured against the shipped render, **0.009 %** of pixels differ by more than 8/255 and the largest single difference is **15/255**, which is Cycles sampling noise at 32 samples, not content; frame mean and standard deviation are unchanged (0.352 / 0.217). The camera did not move. Nothing in this assessment changes.
