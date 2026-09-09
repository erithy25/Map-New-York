# Bethesda Terrace and Fountain

`bethesda_terrace_fountain` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Bethesda Fountain and the Lake, Central Park, Manhattan, New York.jpg by Christian David, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2026-04-18 08:04:45, 1920x1280. [Commons page](https://commons.wikimedia.org/wiki/File:Bethesda_Fountain_and_the_Lake,_Central_Park,_Manhattan,_New_York.jpg)

**Camera** — 40.773882, -73.971046 (NYC_TM -1777, 8205) at z 22.8 m NAVD88 | azimuth 20.4°, pitch +2.4° | 28 mm on 36 mm (65.5° horizontal) | 1280x854.

**Sun** — azimuth 92.9°, elevation 20.3° at 2026-04-18T08:04:45-04:00 (EXIF DateTimeOriginal); 657.2 W/m² direct normal, sky at strength 0.0404, Filmic, +0.73 stops.

**Subject** — Bethesda Fountain (Angel of the Waters) at 51.4 m.

**In the scene**, within 742.7 m of the camera and not all of it in frame — 4 building tiles (231,192 tris), 8 landmark models of which **5 can fall inside the 65.5° frame**, 14,791 pavement polygons (5,686 white, 5,224 sidewalk, 1,957 roadbed, 1,334 curb, 230 crosswalk, 164 yellow, 141 median, 29 parking lot, 26 plaza), 224 props of the 258 in range, 100 kit pieces, 0 vehicles and 11 people; 1,634,662 triangles. Ground mesh 86,028 triangles, 0 holes. 20 city surfaces are dressed from the shared photographic catalogue.

## Verdict — the same view at last, with the fountain in the middle of it, over a park that is bare grey terrain

**This is now a comparison of Bethesda Terrace, which the previous render of this sheet was not.** The camera stands on the photograph's own EXIF GPS, **42.7 m** from the item's recorded viewpoint and **51.4 m** from the fountain, on the upper deck: the eye sat **1.83 m** under `verify_pavement`, the paved level at **21.19 m** NAVD88, and was lifted to **22.8 m**. That is J65's fix, applied — the earlier render stood on the terrace roof and drew a road. The heading is the bearing from that GPS to the fountain, **20.4°**, against the reference's own estimate of **20.3°**; the instant is the photograph's EXIF, to the second.

**The fountain is in the frame and the record says so as a fraction.** Of **13** rays cast at the subject, **8** land on it, **5** go into nothing, none is blocked: `subject_visible_fraction` **0.615**, `subject_clear_fraction` **1.0** (J78: the verdict rule is one ray; read the fraction). The fan is the **12 m** floor because the fountain measures **8.6 m** tall and **3.3 m** across. The height probe lands **43 of 43** rays on built fabric and reads **8.64 m** above a ground of **17.16 m**, off `lm_b_bethesda_terrace.2` — a **3.3 m** by **0.3 m** slab, the angel's wings; the catalogue's `b_bethesda_terrace` origin, **0.1 m** away, publishes **7.92 m**. Under a metre between a measured top and a published height.

**What the reader must not read into it: the picture is right about where things are and wrong about what they are made of.** The photograph is the Angel of the Waters on a dark stone fountain in a wide basin, a red-brick plaza crowded with people, a green Lake, and the Ramble in April leaf filling the upper half. The render is a salmon-pink disc and pedestal carrying three grey-green angel boxes and the smaller cherub boxes below them, two people beside it, a flat grey-blue Lake, a bare faceted grey hillside with no tree on it, and clear sky over the upper half. The framing is looser: the photograph looks down from the balustrade with a longer lens and its basin spans nearly the full width; the render tilts **+2.4°** up from **25.3 m** behind the terrace edge (`lm_b_bethesda_terrace.16`, **-11.6°** below the axis) and draws the fountain at half that size, with the deck's paving across the lower third.

## What matches

* **The viewpoint and the axis.** Camera on the photograph's GPS, heading **20.4°** against the reference's estimated **20.3°**, sun at azimuth **92.9°** and elevation **20.3°** from the photograph's own timestamp. Low light from the east-right in both; the render's left-foreground shadow falls the way the photograph's tree shadows do, though it is thrown by the pink terrace block at the right edge.
* **The plan of the terrace.** Upper deck, balustrade as a dark band across the frame, staircase descending at right, fountain centred on the axis in a round basin on the lower plaza, the Lake behind. The model stands on the terrace's real footprints and the fountain on its OSM way, own ground **4,286.5 m²** at **0.42 m** above the heightmap's median of **17.28 m**.
* **The subject's height is measured, not looked up**: **8.64 m** off the fabric against **7.92 m** published **0.1 m** away (J74's rule).
* **The Lake exists as water.** The terrain record names `THE LAKE` at **16.55 m** among **3,737** water quads; the render draws a flat reflective surface between plaza and far shore — B16's one inland-water viewpoint, with the Lake in it.
* **The empty carriageways are correct.** 0 vehicles: **46** dropped on a car-free park drive, **5** off a carriageway. The photograph's one vehicle is a Parks cart on the plaza paving, a placement the simulation refuses.
* **The exposure is not a fault.** The scene needed **+0.73** stops to read at middle grey, against a physical rule of **+1.10** — a normally lit morning. The photographer exposed **-0.771** stops against the same convention, the render sits at **0.239**; the **1.01**-stop ratio is that difference, not the city (J83).

## What does not match

* **The Ramble is a bare grey hillside.** The photograph's upper half is continuous canopy in fresh leaf; the render's is faceted grey terrain with no tree in frame, though **76** were placed within **342.7 m** (all **76** species-substituted, mean scale **0.946**, none out of band). D10 records this: Central Park's OSM trees are where a mapper walked, and this sightline crosses none. Grass is a flat colour, not a texture (J40); why the slope reads grey, not green, the record does not say. Without the canopy, Belvedere Castle (**636.9 m**, **-4.9°** off axis) and the museum blocks at the frame edges stand on a skyline that in the photograph is trees.
* **Chroma is half the photograph's and there is no shadow.** Chroma **0.074** against **0.1435** (ratio **0.516**): the photograph's colour is canopy, green water and red brick; the render's only saturated things are the pink fountain and terrace block at the right edge. p05 **0.2847** against **0.0933** — far above the JPEG floor — and sd **0.126** against **0.2089** (ratio **0.603**): the photograph's darks are canopy shade, stone, bronze and wet basin; the render has none. p95 runs the other way, **0.6645** against **0.7919**: sunlit brick and spray outshine anything in the render.
* **The fountain is pink blocks.** `sandstone_red` reads as salmon on rim, pedestal, upper basin and stem; the real fountain is near-black stone with a bronze angel and cherubs. The angel is three `bronze_green` boxes — body, wings, arm — and the four cherubs four more around the stem, three visible below the angel in the render; none is sculpted, there is no jet, no water legible in the basin, and the rim is one flat disc. The docstring says "blocked out, not sculpted: the angel and the cherubs".
* **The plaza and the deck are pale grey, not red brick and bluestone.** Both are one pale speckled surface.
* **Half the frame is sky and the fountain is half the size.** The sightline block aims at the subject's mid-height, **4.3 m** above its ground; a **+2.4°** tilt over **51.4 m** rises only a fraction of the fountain's **8.64 m**, so the pitch was computed to that, and the pitch note's "top of `lm_b_bethesda_terrace.2` … **9 m** above the ground" is stale wording. The horizon sits at mid-frame. The photograph looks down from the balustrade with no deck paving in its foreground; the GPS stands **25.3 m** behind that edge, and the **28 mm** lens was chosen so "the terrace, fountain and the Lake" fit — smaller than the picture's.
* **Eleven people where the photograph has dozens.** The Saturday 08:00 table asks for **13.2** pedestrians over the whole ring; **27** were simulated, **11** stand inside the **200 m** cut — two by the basin, a few across the plaza. The simulation's crowd, not the photograph's.
* **34 point props in range have no asset** — **11** artworks, **9** drinking fountains, **6** parks buildings, **5** memorials, **3** comfort stations — and **3** impostor cards dropped; the Angel is an artwork.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the Ramble is bare grey terrain, no tree in frame | park trees are OSM nodes a mapper recorded, none on this sightline; no canopy source; grass is a flat colour, not a texture (D10, J40) | data |
| chroma 0.516 of the photograph's; no darks (p05 0.2847 vs 0.0933); sd 0.603 | no foliage, green water, brick, dark stone or bronze; the exposure is metered at +0.73 stops and is not the cause (J83) | material |
| pink blocks for a dark stone and bronze fountain | basin, pedestal and stem are `sandstone_red`; the angel is three `bronze_green` boxes and the cherubs four; the docstring says blocked out, not sculpted | geometry |
| plaza and deck pale grey, not brick and bluestone | flat model colours; brick paving is not in the catalogue | material |
| horizon at mid-frame, fountain half the photograph's size | the pitch aims at the subject's mid-height and the lens widens to fit the Lake; the GPS stands 25.3 m behind the balustrade of the picture | stated choice |
| eleven people against a full plaza | the simulation's Saturday 08:00 crowd, not the photograph's | — (not a gap) |
| 34 point props unplaced, 3 impostor cards dropped | these five kinds resolve to no asset (J23) | geometry |
| 0 vehicles | 46 dropped on a car-free park drive, 5 not on a carriageway — correct | — (not a gap) |
