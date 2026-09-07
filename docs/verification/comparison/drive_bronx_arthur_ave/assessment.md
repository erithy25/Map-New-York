# Bronx drive-through: Arthur Avenue (Belmont)

`drive_bronx_arthur_ave` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Arthur Avenue 09 - M&G Restaurant.jpg by Joe Mabel, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2026, 1920x1440. [Commons page](https://commons.wikimedia.org/wiki/File:Arthur_Avenue_09_-_M%26G_Restaurant.jpg)

**Camera** — camera 40.85325, -73.88915 (NYC_TM 5131, 17020) z 26.6 m NAVD88 | azimuth 190.0deg pitch +0.0deg | 35 mm on 36 mm (54.4deg horizontal) | 1208x906. View direction: 190.0 deg as recorded in meta.json.  This item names no subject and the reference photograph's own view direction was not derived from the image (confidence: medium), so the two halves of this sheet are not guaranteed to face the same way -- compare them on street width, storey height and material, not on composition. Aim: level optical axis (the reference names no subject to aim at).

**Sun** — azimuth 95.5°, elevation 43.6° at 2026-06-21T09:30:00-04:00 (photograph year only; 21 June 09:30 assumed).

**In frame** — 4/4 building tiles (259,422 tris), 0 landmark models, 2,363 pavement polygons, 356 props, 6,622 facade-kit pieces; 3,564,731 triangles; ground mesh 211² at 2.0 m near / 40.0 m far; props capped by the triangle budget. Frame mean 0.265, sd 0.186.

**Verdict — re-rendered 2026-09-07 against a photograph that is at least of Arthur Avenue. The old reference was the fence and sign of D'Auria-Murphy Triangle, a park; this one is 2472 Arthur Avenue, a restaurant frontage on the block the item names. The two halves still do not compare on composition — the photograph is a shopfront at four metres, the render is the roadway centre looking south — but they can now be compared on the thing the drive-through is for: block-face height, storey rhythm, awning band, brick and stucco**

## What changed, and why

The chooser had selected a park sign and an apartment block titled only for the neighbourhood, because
the item's single keyword group was `["arthur avenue", "belmont"]` and `"belmont"` on its own is the
name of the district. The subject test now requires the photograph's own title or description to name
`"arthur avenue"` (`docs/verification/comparison/REPORT.md` §2.11), which rejected 11 candidates and
returned three frontages on the avenue itself.

**This is an improvement in the reference, not a fix for the sheet.** Commons has essentially no free
photograph looking *along* Arthur Avenue; what it has is shopfronts on it. The rule can say a
photograph is of the right street and cannot say which way it faces, and this item names no subject
from which a bearing could be taken (deviation I7).

## What matches

* The street trees are right, and they are the first in this set that look like trees: full June canopies, visible trunk and branch structure, correct 8-12 m heights, planted at the kerb where the street-tree census puts them. The opaque impostor cards that turned every tree into a black cone are gone.
* The block face is right in kind and scale for Arthur Avenue: two- and three-storey brick and stucco buildings with flat roofs and parapets, a continuous ground-floor commercial band, and the Arthur Avenue Retail Market's shed structure running along the left.
* Sidewalk sheds with green netting are placed along both frontages, which is what this block actually carries.
* The street section is right: a wide roadbed, generous sidewalks on both sides, kerb reveal visible, and 2,377 pavement polygons including 547 crosswalk and 134 parking-lot polygons from the DoITT planimetrics.
* A fire hydrant sits at the kerb at the correct size and colour, at the position props.parquet records.

## What does not match

* **The frames are at different scales.** The item looks south down Arthur Avenue from the roadway
  centre; the photograph is a frontage at four metres. They agree on what the street is made of and
  cannot be compared on composition.
* **The Sun is a guess.** The file records only the year 2026, so the fallback puts it at 21 June
  09:30, azimuth 95.5 deg — an east-facing morning light on a street the photograph shows in flat
  shade. The frame mean is 0.265 against a photograph of a sunlit red frontage.
* The bottom 45 % of the render is empty roadway and sidewalk with no texture, no markings and nothing on it. Arthur Avenue in the photograph's own background carries parked cars along both kerbs.
* There are no people, no market stalls, no shop signs, no menu boards — the things that make Arthur Avenue what it is. The awning band *is* there, with `RESTAURANT` lettering on it, which is the one shopfront element the facade kit does supply.
* The ground-floor commercial band is a flat coloured strip. No glass, no shopfront lettering, no rolling shutters, no produce boxes on the sidewalk.
* The buildings have no window openings on the visible faces, no sills, no lintels, no cornices; the left-hand block is a plain stucco plane with a few dashes.
* No landmark models are in range, which is correct for this location but means the frame rests entirely on shells and kit.
* Props were capped by the triangle budget at 347 placed.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the two halves are of different subjects | the item names no subject and the reference stage assigned it the item's own azimuth; the photograph is a park-fence close-up | reference |
| no parked cars, no people | no traffic or crowd placement feeds the verification scene | data |
| no shopfronts, signs or awnings | the facade kit supplies openings without glazing, lettering or awnings, and no stage produces signage | material |
| no window detail on the block faces | the kit was capped by the triangle budget before it reached these runs of wall | geometry |
| no park | park fences, benches, planting and signs are in no dataset the verification scene reads | data |
| featureless roadway | the pavement material is a flat colour per kind with no texture and no markings | material |
