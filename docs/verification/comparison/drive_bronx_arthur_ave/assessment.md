# Bronx drive-through: Arthur Avenue (Belmont)

`drive_bronx_arthur_ave` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:NYC Parks D’Auria-Murphy Triangle IMG 0677 HLG.jpg by Hugo L. González, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2019-06-15 15:04:31, 1920x1440. [Commons page](https://commons.wikimedia.org/wiki/File:NYC_Parks_D%E2%80%99Auria-Murphy_Triangle_IMG_0677_HLG.jpg)

**Camera** — camera 40.85325, -73.88915 (NYC_TM 5131, 17020) z 26.6 m NAVD88 | azimuth 190.0deg pitch +0.0deg | 35 mm on 36 mm (54.4deg horizontal) | 1208x906. View direction: 190.0 deg as recorded in meta.json.  This item names no subject and the reference photograph's own view direction was not derived from the image (confidence: medium), so the two halves of this sheet are not guaranteed to face the same way -- compare them on street width, storey height and material, not on composition. Aim: level optical axis (the reference names no subject to aim at).

**Sun** — azimuth 246.8°, elevation 57.9° at 2019-06-15T15:04:31-04:00 (EXIF DateTimeOriginal).

**In frame** — 4/4 building tiles (232,178 tris), 0 landmark models, 2,401 pavement polygons, 354 props, 4,498 facade-kit pieces; 3,120,722 triangles; ground mesh 211² at 2.0 m near / 40.0 m far.

**Verdict — as a piece of Belmont streetscape this is the best street-level frame in the set — real London planes in leaf, real market sheds, real brick and stucco block faces at the right heights — and it is paired with a photograph of a park fence, so the two halves cannot be compared on composition at all**

## What matches

* The street trees are right, and they are the first in this set that look like trees: full June canopies, visible trunk and branch structure, correct 8-12 m heights, planted at the kerb where the street-tree census puts them. The opaque impostor cards that turned every tree into a black cone are gone.
* The block face is right in kind and scale for Arthur Avenue: two- and three-storey brick and stucco buildings with flat roofs and parapets, a continuous ground-floor commercial band, and the Arthur Avenue Retail Market's shed structure running along the left.
* Sidewalk sheds with green netting are placed along both frontages, which is what this block actually carries.
* The street section is right: a wide roadbed, generous sidewalks on both sides, kerb reveal visible, and 2,377 pavement polygons including 547 crosswalk and 134 parking-lot polygons from the DoITT planimetrics.
* A fire hydrant sits at the kerb at the correct size and colour, at the position props.parquet records.
* The Sun is from the photograph's own EXIF instant (2019-06-15 15:04:31 EDT, elevation 57.9 deg) and the high summer light and short shadows match the reference's.

## What does not match

* The frames are of different things. The item looks south down Arthur Avenue; the photograph is a close-up of the fence and sign of D'Auria-Murphy Triangle, taken from inside the park looking out. The item names no subject and the photograph's direction was assumed, so nothing could reconcile them.
* The bottom 45 % of the render is empty roadway and sidewalk with no texture, no markings and nothing on it. Arthur Avenue in the photograph's own background carries parked cars along both kerbs.
* There are no people, no market stalls, no awnings, no shop signs, no menu boards — the things that make Arthur Avenue what it is.
* The ground-floor commercial band is a flat coloured strip. No glass, no shopfront lettering, no rolling shutters, no produce boxes on the sidewalk.
* The buildings have no window openings on the visible faces, no sills, no lintels, no cornices; the left-hand block is a plain stucco plane with a few dashes.
* There is no park. D'Auria-Murphy Triangle, the subject of the photograph, is 4 tiles' worth of green in the reference and bare ground in the render: its fence, benches, planting and sign are not in any dataset the scene reads.
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
