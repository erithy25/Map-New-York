# Lower Manhattan drive-through: Stone Street

`drive_lower_manhattan_stone_st` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Financial District Manhattan March 2025 107.jpg by Kidfly182, CC BY 4.0 (https://creativecommons.org/licenses/by/4.0), taken 2025-03-29 14:00:14, 1920x863. [Commons page](https://commons.wikimedia.org/wiki/File:Financial_District_Manhattan_March_2025_107.jpg)

**Camera** — camera 40.70435, -74.01035 (NYC_TM -5100, 484) z 5.4 m NAVD88 | azimuth 60.0deg pitch +0.0deg | 35 mm on 36 mm (54.4deg horizontal) | 1280x576. View direction: 60.0 deg as recorded in meta.json.  This item names no subject and the reference photograph's own view direction was not derived from the image (confidence: medium), so the two halves of this sheet are not guaranteed to face the same way -- compare them on street width, storey height and material, not on composition. Aim: level optical axis (the reference names no subject to aim at).

**Sun** — azimuth 203.9°, elevation 50.6° at 2025-03-29T14:00:14-04:00 (EXIF DateTimeOriginal).

**In frame** — 6/6 building tiles (93,470 tris), 12 landmark models, 2,070 pavement polygons, 673 props, 11,167 facade-kit pieces; 4,500,006 triangles; ground mesh 211² at 2.0 m near / 40.0 m far.

**Verdict — a real alley of the right width between walls of the right height and colour, rendered legibly at last (mean 0.151 against 0.001 before the camera corrections) — but it is a bare corridor: no cobbles, no tables, no signs, no people, and the two halves face different ways**

## What matches

* The alley section is right. Stone Street's 6 m pedestrian width, the walls rising 25 m either side and the way the block bends to the east all match the real street.
* The wall colours and materials are drawn from the real facade classes: red brick on the right, pale stone and grey on the left, which is what the reference block face carries.
* Sidewalk sheds with green netting run along both walls at the same height as the scaffolding in the reference, and the shopfront band is lit from within, which is the only emissive content the world has and it is in the right place.
* The camera stands on the photograph's own EXIF GPS, 40 m from the item's nominal viewpoint, on the pedestrian surface, and the clearance report states the nearest solid thing in the view cone (a brick wall 17.2 m ahead) and the free distance along the azimuth (24 m).
* The exposure is honest: a 6 m alley between 25 m walls at a 50.6 deg Sun really is this dark, and no exposure compensation was applied to flatter it.

## What does not match

* The frames face different ways. The item looks east-north-east down the alley; the reference is a facade study of the brick block face, shot across the alley and tilted up. The item names no subject and the photograph's direction was assumed, not measured, so nothing in the pipeline could correct it.
* Stone Street's defining surface — Belgian block cobbles — is a flat dark grey plane. The pavement kind is 'plaza' with a base colour and no texture.
* The street's other defining feature is missing entirely: the restaurant tables, chairs, umbrellas and heaters that fill it from April to October, and the hanging signs and string lights above them.
* No people, no bicycles, no delivery carts.
* The walls have no window openings visible along the near run, no sills, no lintels, no fire escapes, where the reference's block face carries a fire escape, six window bays, stone lintels and a cornice.
* There is no glass anywhere: the shopfront band is a flat coloured strip with a light behind it, not a window.
* The near foreground is a large pale faceted plane where the graded terrain grid meets the pavement, with visible triangulation and no texture.
* Both props and kit were capped by the triangle budget (673 of the props in range, 11,167 of 15,484 kit records), so about a quarter of the facade detail within 120 m is not drawn.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the two halves face different ways | the item names no subject and the reference stage assigned it the item's own azimuth; the photograph is a facade study | reference |
| no cobbles | pavement polygons carry a kind and a base colour, with no texture map | material |
| no tables, chairs, umbrellas or string lights | no dataset carries outdoor restaurant furniture and props.parquet has no kind for it | data |
| no people | no crowd placement feeds the verification scene | data |
| no windows, sills or fire escapes on the near walls | the facade kit was capped by the triangle budget before it reached this run of wall | geometry |
| no glass | the kit's storefront and window pieces carry no glazing material | material |
| faceted, untextured ground | the terrain material is a flat colour and the graded grid is 2 m here | material |
| a quarter of the kit not drawn | the 4.5 M triangle budget is spent before the kit finishes; the cap is recorded on the sheet | geometry |

## Re-render note, 2026-09-07

Re-rendered against the corrected `b_wtc_site` model — the World Trade Center site stood 3.5 m too high, its plaza was an unbroken 520 x 520 m quad over both memorial pools, and its 220 oaks each carried a merged impostor card (`docs/verification/landmarks/REPORT_B.md` §12). Measured against the shipped render, **0.000 %** of pixels differ by more than 8/255 and the largest single difference is **2/255**, which is Cycles sampling noise at 32 samples, not content; frame mean and standard deviation are unchanged (0.150 / 0.075). The camera did not move. Nothing in this assessment changes.
