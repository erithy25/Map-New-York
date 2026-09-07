# Lower Manhattan drive-through: Stone Street

`drive_lower_manhattan_stone_st` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Financial District Manhattan April 2022 008.jpg by Kidfly182, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2022-04-19 13:45:47, 1920x1440. [Commons page](https://commons.wikimedia.org/wiki/File:Financial_District_Manhattan_April_2022_008.jpg)

**Camera** — camera 40.70410, -74.01070 (NYC_TM -5133, 465) z 4.0 m NAVD88 | azimuth 60.0deg pitch +0.0deg | 35 mm on 36 mm (54.4deg horizontal) | 1208x906. The camera stands on this photograph's own EXIF GPS, 20 m from the item's recorded viewpoint. View direction: 60.0 deg as recorded in meta.json — the item names no subject, so the axis is the block's own heading and not a bearing derived from the image.

**Sun** — azimuth 204.4°, elevation 58.6° at 2022-04-19T13:45:47-04:00 (EXIF DateTimeOriginal).

**In frame** — 6/6 building tiles (87,260 tris), 12 landmark models, 2,005 pavement polygons, 613 props, 10,813 facade-kit pieces; 4,500,179 triangles; ground mesh 211² at 2.0 m near / 40.0 m far, 4,493 water quads. Frame mean 0.253, sd 0.149.

**Verdict — re-rendered 2026-09-07 against a photograph that looks along the street. Both halves now run east-north-east down the Stone Street pedestrian block from its west end at William Street, between brick walls of the right height, with the awning band at the same level on both sides. The alley itself is right and everything that makes it Stone Street is missing: no cobbles, no tables, no umbrellas, no signs, no people**

## What changed, and why

The photograph this sheet used to carry was of the restaurant tables on Stone Street rather than of the
street, and the assessment's own verdict was "the two halves face different ways". It passed because
`"stone street"` is the *category* on every photograph taken on the block. The subject test now reads
the photograph's own title and description instead (`docs/verification/comparison/REPORT.md` §2.11):
15 candidates were rejected on it, and the chooser returned a view down the block from its west end,
20 m from the item's recorded viewpoint — so the camera stands on the photograph's own GPS and the two
halves face the same way for the first time.

## Re-rendered 2026-09-07, and a first impression the measurement overturned

Stone Street reads well: the narrow bend, the brick walls rising straight out of the paving with no
kerb, the continuous run of shopfront fascias and hanging blade signs down both sides, awnings, a
hydrant, a parked car at the far end and pedestrians walking the middle of the street — which is what
Stone Street is, a pedestrianised alley. 5,634 window pieces, 289 storefronts, 53 storefront
interiors, 89 vehicles and 363 people.

My first reading of this frame was that the lit fascia bands were blowing out — pure white strips
dominating a dim scene, with the signage emission calibrated on the Times Square *night* photograph
and applied unchanged to a daylight alley. **The measurement says the opposite and I was wrong.**

| | render | photograph |
|---|---|---|
| mean luminance | **0.249** | **0.404** |
| median | 0.251 | 0.298 |
| area above 0.95 | **0.02 %** | **14.66 %** |
| area above 0.90 | 0.97 % | 15.76 % |
| area below 0.20 | 35.61 % | 32.63 % |

Nothing in the render is clipping. The fascias look like the brightest thing in the frame because
everything around them is dark, and the frame as a whole is **about a stop under** the photograph it
is paired with.

The cause is not a bug but a difference in kind, and it is worth stating because it affects every
shaded frame in this set. The render is physically lit: the Sun is placed from the photograph's own
EXIF instant (13:45 on 19 April 2022, elevation 58.6°) and the exposure is a fixed 0 stops on a
Filmic transform. The photograph was taken by a camera that *metered this alley* and opened up for
it. A narrow street in shadow under a high sun is exactly where those two diverge. The render is not
wrong about the light; it is answering a different question from the one the photograph answers.

## What matches

* The alley section is right. Stone Street's 6 m pedestrian width, the walls rising 25 m either side and the way the block bends to the east all match the real street.
* The wall colours and materials are drawn from the real facade classes: red brick on the right, pale stone and grey on the left, which is what the reference block face carries.
* Sidewalk sheds with green netting run along both walls at the same height as the scaffolding in the reference, and the shopfront band is lit from within, which is the only emissive content the world has and it is in the right place.
* The camera stands on the photograph's own EXIF GPS, 40 m from the item's nominal viewpoint, on the pedestrian surface, and the clearance report states the nearest solid thing in the view cone (a brick wall 17.2 m ahead) and the free distance along the azimuth (24 m).
* The exposure is honest: a 6 m alley between 25 m walls at a 50.6 deg Sun really is this dark, and no exposure compensation was applied to flatter it.

## What does not match

* **The heading is still the block's own axis and not derived from the image.** It agrees with the
  photograph here — both run east-north-east down the alley — but nothing in the metadata proves it
  (deviation I7).
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
| ~~the two halves face different ways~~ | **fixed**: the subject test reads the photograph's own title and description, so a facade study categorised under "Stone Street (Manhattan)" no longer qualifies as a view along it | reference |
| no cobbles | pavement polygons carry a kind and a base colour, with no texture map | material |
| no tables, chairs, umbrellas or string lights | no dataset carries outdoor restaurant furniture and props.parquet has no kind for it | data |
| no people | no crowd placement feeds the verification scene | data |
| no windows, sills or fire escapes on the near walls | the facade kit was capped by the triangle budget before it reached this run of wall | geometry |
| no glass | the kit's storefront and window pieces carry no glazing material | material |
| faceted, untextured ground | the terrain material is a flat colour and the graded grid is 2 m here | material |
| a quarter of the kit not drawn | the 4.5 M triangle budget is spent before the kit finishes; the cap is recorded on the sheet | geometry |

## Re-render note, 2026-09-07

Re-rendered against the corrected `b_wtc_site` model — the World Trade Center site stood 3.5 m too high, its plaza was an unbroken 520 x 520 m quad over both memorial pools, and its 220 oaks each carried a merged impostor card (`docs/verification/landmarks/REPORT_B.md` §12). Measured against the shipped render, **0.000 %** of pixels differ by more than 8/255 and the largest single difference is **2/255**, which is Cycles sampling noise at 32 samples, not content; frame mean and standard deviation are unchanged (0.150 / 0.075). The camera did not move. Nothing in this assessment changes.
