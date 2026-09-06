# Times Square centre: Duffy Square looking south, daylight

`times_square_duffy_south_day` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Times Square 3 2023-05-17.jpeg by F ASTILY, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2023-05-12 12:18:49, 1920x2560. [Commons page](https://commons.wikimedia.org/wiki/File:Times_Square_3_2023-05-17.jpeg)

**Camera** — camera 40.75912, -73.98472 (NYC_TM -2932, 6566) z 21.2 m NAVD88 | azimuth 203.6deg pitch +0.0deg | 24 mm on 36 mm (58.7deg horizontal, 73.7deg vertical, portrait) | 904x1206. View direction: 203.6 deg, the bearing from this photograph's own GPS position to One Times Square; heading and position both come from the photograph.  The item's recorded azimuth is 203.2 deg, 0.4 deg away, and belongs to its nominal viewpoint. Aim: level optical axis (the subject is 354 m away; anything that far is photographed with a level camera).

**Sun** — azimuth 159.9°, elevation 66.3° at 2023-05-12T12:18:49-04:00 (EXIF DateTimeOriginal).

**In frame** — 6/6 building tiles (235,792 tris), 10 landmark models, 2,422 pavement polygons, 339 props, 14,626 facade-kit pieces; 4,500,022 triangles; ground mesh 215² at 2.0 m near / 40.0 m far.

**Verdict — the street is right and Times Square is absent: correct canyon, correct roadbed and sidewalk widths, correct sidewalk sheds — and not one illuminated sign, not one person, not one vehicle, in the one place in New York that is nothing but signs, people and traffic**

## What matches

* The camera stands on the photograph's own EXIF GPS, 9 m from the item's nominal viewpoint, at 21.2 m NAVD88 — the 4.6 m TKTS top landing plus 1.6 m eye height over a 15 m plaza — and the heading (203.6 deg) is the bearing from that point to One Times Square. The two frames look down the same axis.
* The canyon proportions are right. Seventh Avenue's roadbed width, the setback line of the walls either side and the way the buildings step down toward the bowtie all match the photograph's geometry closely enough to overlay.
* The paved surface is real and reads correctly: 430 roadbed, 252 sidewalk, 468 crosswalk, 149 median and 79 plaza polygons from the DoITT planimetrics, with the 0.15 m curb reveal visible along both kerb lines and a manhole cover sitting proud in the roadway where props.parquet puts one.
* Sidewalk sheds with green netting run along both walls, which is exactly what the reference photograph shows at street level on the west side.
* Street furniture is in the right places and at the right scale: bishop's-crook and cobra-head lamps along both kerbs, a hydrant on the west sidewalk, a bench on the east plaza, bus-stop and regulatory signs.
* The far end of the canyon carries a tapered dark tower that reads as the Times Square cluster; 4 Times Square and One Vanderbilt-era massing beyond it is plausible.

## What does not match

* There is no signage of any kind. Not a screen, not a billboard, not a shopfront sign, not a lit letter. The photograph is 60 % illuminated advertising by area — the FOX and T-Mobile screens, the Marriott Marquis marquee, the tower-wrapping LED bands. This single absence is the difference between 'a Midtown avenue' and 'Times Square', and it is the largest gap in the whole comparison set.
* There are no people. The reference has upwards of two hundred visible; the render has none, and with nothing of known size in the frame every object's scale has to be inferred from the geometry rather than read.
* There are no vehicles. Seventh Avenue in the photograph carries taxis, buses and a police van; in the render it is bare asphalt.
* The TKTS red steps the camera is standing on are not modelled, so the camera floats 4.6 m above the plaza with nothing under it, and the photograph's whole lower third — the steps and the people sitting on them — has no counterpart.
* The Duffy Square plaza furniture is missing: no café tables and chairs, no planters, no Father Duffy statue, no granite bollards. The plaza polygons are there but they are bare grey.
* The buildings are flat pastel solids with windows cut as small unglazed dashes. There is no glass, no mullion, no spandrel, no cornice shadow, so the walls read as extruded card.
* The bare street trees render as near-solid dark cones. The impostor billboard cards are now dropped (9 of them in this frame) but the remaining branch geometry is dense enough at 32 samples to read as an opaque mass rather than as winter branches.
* The roadway has no markings — no lane lines, no stop bars, no crosswalk stripes. The crosswalk polygons are present but painted as flat light grey rather than as zebra stripes.
* The photograph was taken in late May with the trees in full leaf; the render's leaf-off decision is right for the date it was given but the trees themselves are the wrong species mass.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| no illuminated signage anywhere | no stage produces billboard, screen or shopfront-sign geometry; the c_times_square landmark model placed 359 m away carries none either | geometry |
| no people | no crowd or character placement stage feeds the verification scene | data |
| no vehicles | no traffic or parked-vehicle placement feeds the verification scene | data |
| TKTS steps not modelled | the structure is neither a building footprint nor a prop, so no stage builds it | geometry |
| bare plaza, no tables, chairs, planters or statue | props.parquet carries no plaza furniture for Duffy Square and the memorial/artwork kinds it does carry have no exported asset | data |
| flat walls, unglazed window dashes | shells carry a per-material base colour; the facade kit supplies openings but no glass, mullions or sign faces | material |
| trees read as solid cones | the leaf-off branch model is dense and untextured; at 32 samples with denoising it fills rather than breaks up | material |
| no road markings | the pavement polygons carry a kind but no line or stripe geometry and no texture | material |
