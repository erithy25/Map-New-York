# Apollo Theater

`landmark_apollo_theater` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Prince memorial at Apollo Theater. Harlem, NY. (26902543512).jpg by Kathy Drasky from San Francisco, United States, CC BY 2.0 (https://creativecommons.org/licenses/by/2.0), taken 2016-04-24 16:26, 1920x1440. [Commons page](https://commons.wikimedia.org/wiki/File:Prince_memorial_at_Apollo_Theater._Harlem,_NY._(26902543512).jpg)

**Camera** — 40.809733, -73.95025 (NYC_TM -21, 12186) at z 10.3 m NAVD88 | azimuth 35.4°, pitch +0.4° | 26 mm on 36 mm (69.3° horizontal) | 1208x906.

**Sun** — azimuth 254.9°, elevation 36.3° at 2016-04-24T16:26:00-04:00 (EXIF DateTimeOriginal (minutes)); 819.0 W/m² direct normal, sky at strength 0.0343, Filmic, +4.79 stops.

**Subject** — Apollo Theater marquee at 36.4 m.

**In the scene**, within 505.6 m of the camera and not all of it in frame — 4 building tiles (370,680 tris), 1 landmark models of which **1 can fall inside the 69.3° frame**, 19,761 pavement polygons (6,979 white, 5,119 sidewalk, 3,870 roadbed, 2,703 curb, 392 crosswalk, 302 parking lot, 219 median, 132 yellow, 45 plaza), 2065 props of the 2,188 in range, 4,442 kit pieces, 85 vehicles and 371 people; 4,077,848 triangles. Ground mesh 80,000 triangles, 0 holes. 20 city surfaces are dressed from the shared photographic catalogue.

## Verdict — the same theatre, from opposite sides of the street, and neither half shows a marquee

**The two halves are not the same view, and the record's camera is on the wrong sidewalk for the photograph it quotes.** The photograph is a memorial three days after Prince's death: a camera at the theatre's own doorstep on the north sidewalk of 125th Street, tilted down at candles, flowers, portraits and a purple-draped table with a boombox, seven people standing or walking along the brushed-metal shuttered base of the Apollo's front, a limestone pier at the right edge. No marquee, no blade sign and no upper storey is in it; the top edge cuts through the roller shutters. The render stands where the photograph's EXIF GPS says the camera was — **6 m** from the item's nominal south-sidewalk viewpoint, so across the street — and looks level over the carriageway at the whole front of the block. The heading, **35.4°**, is the bearing from that GPS to the subject coordinate, "not derived from the image"; the picture itself looks squarely into the theatre's base from a few metres off it. A phone GPS in a street canyon put the photographer across the road from where the photograph plainly stands, and the placement rule trusted the number. No register row covers a wrong-sidewalk GPS at this range (J60 begins at 250 m).

**What the record measures is the theatre block, and the picture agrees that a block is there.** The height probe lands **43 of 43 rays** on built fabric at the subject coordinate and reads **17.97 m** above ground off `lm_c_apollo_theater.8`, a **37.3 m** by **29.4 m** object; the catalogue entry `c_apollo_theater`, 20.7 m away, publishes **20.0 m**. The sightline gets **13 of 13 rays** to the subject's own fabric, landing at **20.9 m** on `lm_c_apollo_theater.6`, and the clearance probe names the same object as the nearest built thing at **20.8 m**, 11.5° left of the axis. Read those two distances together: the front is 20.8 m from the lens and the point named "marquee" is **36.4 m** from it, which puts the coordinate inside the auditorium, not over the pavement where a marquee hangs. The measurement is correct and it is of the building; nothing in this record measures the marquee, and the subject name should not be read as if it did (the J57/J82 shape, at metres rather than a hundred).

**The lens rule sized the frame to the coordinate and the front wall is nearer than the coordinate.** The record widened to 26 mm so that the top of `.8`, "18 m above the ground there", would sit **24°** above the horizon at 36 m; the front of the block stands at 20.8 m, and in the render the tan brick runs off the top edge across the theatre's whole width (my PIL scan of the column through its middle finds no horizontal edge above the black panel). The pitch is **+0.4°**, flagged by the record as converging verticals; invisible at that angle, but declared (I18).

**Do not read the crowd, the colour or the dark base as verdicts on the city.** The seven people, balloons and purple are a one-off event; the simulation drew its **371** pedestrians from the Sunday density profile (a day type, not the date), three of them in frame. The chroma ratio **0.563** is the memorial's purple against brick and asphalt. The black base is a material on the model, not shade: the tan brick directly above it measures about seven-tenths display luminance on my PIL sample and the panel about one-seventh, under the same Sun.

## What matches

* **The subject is the Apollo Theater and it is in the frame**: 43 of 43 height rays and 13 of 13 sightline rays on its fabric, the landmark model in the cone at **57.0 m** to its origin and **0.8°** off axis.
* **The instant is the photograph's own EXIF**, to the minute: Sun at azimuth **254.9°** and elevation **36.3°**, behind and to the left of the camera. The south-facing front reads flat and bright — my PIL sample across the tan brick shows no left-to-right gradient, nearly three-quarters of it above the seven-tenths threshold.
* **The street is a 125th Street cross-section**: asphalt with a white lane dash and a double yellow centre line, kerbs, a sidewalk, a storefront band with a green fascia and a green double door right of the theatre, one street tree; **6,979** white and **132** yellow markings in the pavement set.
* **The neighbours have the block's character** — cream masonry with sash windows over a shopfront on the right, red brick with grey-framed windows on the left: **3,453** windows and **592** storefronts placed across the scene.

## What does not match

* **There is no marquee and no blade sign in the render.** The Apollo's front carries a marquee over the sidewalk and the vertical neon "APOLLO" sign; the photograph's base is brushed-metal panels, roller shutters, a limestone pier with a display window and a hydrant. The render's ground floor is one recessed black panel with a faint mottled texture, from about an eighth to two-thirds of the frame width and from a quarter to just over half its height — about an eighth of the frame by my PIL measurement — with a thin lighter plinth at its foot and no door, shutter or lettering.
* **The halves look in different directions from different places.** Nothing in the photograph's lower two-thirds (the memorial, the Walk of Fame plaques in the pavement) can appear in the render, and nothing in the render's lower two-fifths (carriageway) appears in the photograph.
* **Seven people against three.** The render's three are one at a fifth of the frame width and one just past the middle, both on the far sidewalk against the black panel, and one at the right storefront. No simulated agent stands within **60 m** of the lens; no vehicle is in frame though **85** are in the scene.
* **The lighting, as stops.** The render was developed at **+4.79** stops (the physical rule alone would have given **+0.24**), and the record says under-lit: more than the four a photographer recovers hand-held. The photograph's median sits **-0.23** stops from the middle-grey convention, the render's **0.245**; p50 **0.4992** against **0.4282**, p95 **0.8537** against **0.9481**. The p05 pair, **0.1054** against **0.0972**, is within the photographs' JPEG floor.
* **Chroma 0.0617 against 0.1095**: purple flowers and portraits against brick, asphalt and one green fascia.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| no marquee, no blade sign, a black panel for the whole ground floor | the landmark model `c_apollo_theater` (7,049 triangles) is the block and a dark ground-floor plane; marquee, neon sign, metal panelling and shutters are not modelled and the kit has no source for them | geometry |
| the halves look in different directions from different places | the camera is on the photograph's EXIF GPS, on the south sidewalk 6 m from the nominal viewpoint, heading the bearing to the coordinate; the photograph was taken at the theatre's base, tilted down, and the direction is "not derived from the image" | reference |
| the coordinate named "marquee" is 36.4 m off when the front is 20.8 m off | the subject point sits inside the block; the probe measured the block standing there (J74), not a marquee — the J57/J82 shape at metres | data; **DEVIATIONS J74** |
| the front wall runs off the top of the frame | the lens was sized to the top of `.8` at the coordinate's 36 m, not to the front face at 20.8 m; pitch +0.4° declared (I18) | verification; **DEVIATIONS I18** |
| seven people against three, memorial absent | the crowd is a Sunday density profile for the hour, not the event; the memorial is a one-day object no dataset holds | stated choice |
| +4.79 stops of development, under-lit by the record's own note | metered at middle grey (J83); black panel and asphalt take most of the frame and the linear median was 0.006484 before development | **DEVIATIONS J83** |
| chroma 0.563 of the photograph's | the photograph is a purple memorial with a VSCO preset; the render is masonry and asphalt — a subject difference, not J66 | — (not a gap) |
