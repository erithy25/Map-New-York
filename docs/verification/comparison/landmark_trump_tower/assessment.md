# Trump Tower (725 Fifth Avenue)

`landmark_trump_tower` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Trump Tower December 2022 003.jpg by Kidfly182, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2022-12-12 12:35:38, 1280x1707. [Commons page](https://commons.wikimedia.org/wiki/File:Trump_Tower_December_2022_003.jpg) — the view direction is derived from the image. The photograph is taken from directly beneath the tower and is nothing but its curtain wall: the bronze reflective glass, the vertical sawtooth bays receding up the frame, and a strip of December sky in one corner. Its own 95th percentile is **1.0** — the highlights are clipped in the source file.

**Camera** — 40.762333, -73.974411 (NYC_TM -2070, 6930) at z 18.1 m NAVD88 | azimuth 70.2°, pitch +26.9° | 18 mm on 36 mm (73.7° horizontal, 90.0° vertical, **portrait**) | 904x1206. The camera stands on **this photograph's own EXIF GPS**, **45.4 m** from the item's recorded viewpoint, whose azimuth it agrees with to **0.2°**. It was then moved **10.3 m** onto the nearest sidewalk polygon under the rule `pavement snap with a clear frame that sees the subject` — *"boxed in: the view azimuth is closed off 20 m ahead, less than the 27 m this frame needs to show its subject"* — and the walk scored candidates on the subject's own sightline (`scored_on_subject_sightline: true`), recording what it settled for: 13 rays, 2 on the subject, a fraction of **0.154**, blocked at 19.3 m by `prop_lamp_cobra_davit_4`. From there the view is clear for **37.9 m**, the nearest built thing in the frame is `prop_steam_stack_3m_2` **14.0 m** away — the orange-and-white stack standing in the carriageway in the render — and the nearest simulated body is a yellow taxi at **8.4 m**. The lens is at the **18 mm floor**: the record says the top of the subject is still cut off and *"the verticals converge, so this frame is not comparable with the photograph on proportion"*. The ground under the lens reads 16.509 m NAVD88, the 10th percentile of 113 samples within 12.0 m.

**Sun** — azimuth 191.7°, elevation **25.3°** at 2022-12-12T12:35:38−05:00, from the photograph's own **EXIF DateTimeOriginal**; 722.4 W/m² direct normal, sky at strength 0.0378, Filmic, **+4.34 stops**. Metered, unclamped, on a linear median of **0.008891** against a physical rule of 0.77, and the record declares the consequence: *"under-lit: the scene needed +4.34 stops to read as a picture, more than the 4 a photographer recovers hand-held"*.

**In the scene** — 4,500,024 triangles: 4 building tiles (222,112 tris), 10 landmark models, 20,230 pavement polygons, 1,359 props, 5,069 kit pieces, 14 park-ground meshes, **1 tile of structures at 96 triangles** with 3 tiles having no file, 53 vehicles and 252 people.

## Verdict — the sawtooth is modelled as seven plates instead of twenty-eight bays, and the probe measured one of them

**The tower is in the frame and it reads.** The render's upper right is a bronze-mullioned dark-glass shaft with its plan stepping back at the right edge, which is what Trump Tower does. `blender/landmarks/c_billionaires_row.py` builds it from the real footprint of BIN 1035794: a 26.0 m granite plinth, then **seven stacked `cc.curtain` tiers** to `HTRUMP` = **202.0 m**, each on a plan inset 9.0 m in x and 6.0 m in y from the one below, with dark glass, **bronze** mullions on a 3.0 m module and a 0.9 m spandrel band. The builder's own note says what that simplification is: *"Trump Tower's sawtooth as 7 plates"*, against the **28 sawtooth bays** its dimensions block records from CTBUH. So a reader sees the right material, the right colour and the right stepping, at a quarter of the real bay count.

**And the height probe measured one of those seven plates.** 43 rays cast, **all 43 on built fabric**, and the answer is **128.61 m** above a ground of 15.91 m on `lm_c_billionaires_row.66`, whose plan extent is **55.5 by 49.3 m**. The tower is 202.0 m in the same file. The object standing at the subject's coordinate is a tier, not the building, so the sheet publishes about two thirds of its subject's height — J94's fault on a stepped tower, where the stepping is exactly what makes it happen. The catalogue could not help: the nearest entry is `c_the_plaza` at **223.9 m**, well past the 120 m rule, so J74 correctly took the geometry (and the geometry gave a tier).

**The two halves are not comparable and the record says so twice.** The photograph is a facade study from the pavement directly below; the render, after a 10.3 m move onto a sidewalk, is a Fifth Avenue street scene with parked cars, a steam stack, a bus-stop sign and bare trees in the foreground and the tower in the upper right. The lens note declares the verticals incomparable; the clearance note declares the viewpoint boxed in at 20 m. Both are true and together they mean this sheet tests the block rather than the curtain wall.

**The colour runs backwards here, and for a reason.** Chroma **1.823** — the render carries nearly twice the photograph's saturation — because the photograph is an almost monochrome study of dark glass and the render is a street containing a yellow cab, a green car, an orange steam stack and a blue bus-stop sign. The render also holds much **less** contrast, sd **0.725**, against a reference whose highlights are clipped at 1.0. The exposure gap is **1.145 stops**: the photograph sits 0.907 stops below the grey convention and the render is metered to 0.238 above it.

**Ninety-six triangles of structures.** One tile imported, three with no file, and what came in is **96 triangles** — the smallest non-zero structures contribution read this round, on Fifth Avenue above the Sixth Avenue line's 57th Street station.

## What matches

* **43 of 43 probe rays on built fabric**, and J74's origin rule fired correctly — the nearest catalogue entry at 223.9 m was past the 120 m reach, so the height was measured.
* **The tower's material and stepping are right.** Dark glass with bronze mullions on a 3.0 m module and a 0.9 m spandrel, on a plan that steps back seven times from a 26.0 m granite plinth to 202.0 m.
* **The camera is the photograph's own GPS** and its heading agrees with the item's recorded azimuth to **0.2°**.
* **The walk scored on the subject's sightline** (J79) and published what it settled for, both before and after the move.
* **Fifth Avenue is furnished as Fifth Avenue**: **397 Citi Bike dock units**, 161 cooling towers, 137 street lamps, 107 manholes, 68 hydrants, 32 benches, 32 vent grates, 31 bus-stop signs, 24 waste baskets, **20 flagpoles**, 14 bus shelters, 12 steam vents, 10 bike racks, 9 LinkNYC kiosks and 4 mailboxes.
* **The avenue is paved and marked**: 20,230 polygons with 7,244 white markings, 5,177 sidewalk, 3,878 roadbed, 2,806 curb, 435 crosswalk, 378 median and 274 plaza.
* **The park ground is correct where the camera can see it**: 199 samples within 150 m, `under_frac` **0.0**, median clearance +0.13 m.
* **The fleet is a Fifth Avenue fleet**: 20 yellow taxis of 53 vehicles, with 10 boro taxis, 8 sedans, 7 SUVs, 6 black cars, a box truck and an MTA bus.
* **The trees are bare**, which is right for 12 December (J97), and **28 of the 297 are drawn from modelled branches**.
* **The Sun is the real minute** of a real December midday, from EXIF.

## What does not match

* **The published height is 128.61 m for a 202.0 m tower**, because the object at the coordinate is one of seven tiers (J94).
* **Seven plates where the building has twenty-eight sawtooth bays** — declared by the builder, and a quarter of the real rhythm.
* **The frame is a street, not a facade.** The photograph is taken from under the tower; the render stands 61.5 m off after a 10.3 m move, with a steam stack 14.0 m from the lens and parked cars across the foreground.
* **The verticals converge**: 18 mm at +26.9° against a photograph made to hold a curtain wall parallel, and the record declares the two halves incomparable on proportion.
* **Three of thirteen rays are clear and two land on the subject** — a fraction of **0.154**, with a cobra-head lamp 19.3 m from the lens taking most of them (J88).
* **The development is 4.339 stops, past the under-lit threshold**, on a linear median of 0.008891.
* **Chroma 1.823 and contrast 0.725** — the render is more colourful and much flatter than a near-monochrome study whose own highlights are clipped at 1.0.
* **A 1.145-stop exposure gap**, so p50 reads **1.454×** (J83).
* **Ninety-six triangles of structures**, with 3 of the 4 tiles in range having no file.
* **Two thirds of the props in range were dropped**: 1,359 drawn at a 1,126,750-triangle budget with **909 dropped**, including 833 tree rows, 5 impostor cards dropped as opaque and 22 lost on a suppressed building.
* **The kit was capped at 1,013,603 triangles** and spent on windows: 4,681 of them against **5 cornices** and 5 string courses, with 2,500 pieces suppressed under the landmark shells. Fifth Avenue at 57th is a street of cornices.
* **252 people where the density table asked 3,668.** 1,359 vehicles and 3,668 people were wanted; 1,557 and 3,000 were simulated and **4,252 dropped** — **1,358 pedestrians at the 1,125,000-triangle agent budget**, 1,115 outside the radius, 811 vehicles outside the radius, 656 vehicles at the budget, 208 in the carriageway without crossing, 63 not on a walkable surface, 29 riderless bodies, 28 pedestrians and 8 vehicles above the observer.
* **The park ground sinks in the far field**: 0.26 of 250 samples beyond 400 m, worst case **−6.012 m**.
* **No cloud.** The photograph's corner of sky is a clear hard December blue; the render's is a Nishita dome at strength 0.0378.

## Measured for this assessment

| figure | where it comes from |
|---|---|
| the tower is seven stacked curtain tiers from a 26.0 m plinth to 202.0 m, each inset 9.0 m in x and 6.0 m in y, with dark glass, bronze mullions on a 3.0 m module and a 0.9 m spandrel | the Trump Tower block of `blender/landmarks/c_billionaires_row.py`, its `HTRUMP` constant and its `cc.curtain` calls |
| the building has 28 sawtooth bays and the model has 7 plates | the same file's dimensions block, which records *"664 ft = 202.0 m, 58 marketed storeys; 28 sawtooth bay setbacks on the two park-facing elevations, bronze reflective glass"* from Der Scutt, Swanke Hayden Connell and CTBUH, against its own fidelity note *"Trump Tower's sawtooth as 7 plates"* |
| the footprint is the real one, BIN 1035794 | the `B_TRUMP` constant in the same file |
| 202.0 m is also the catalogue's own figure for the item | the `trump_tower` entry in `blender/landmarks/c_common.py`, `height_m=202.0` |
| the smallest non-zero structures contribution read this round | this sheet's 96 triangles, against the forty-four sheets read in the preceding rounds |
| 12 December is inside the leaf-off window | the `leaf_off` rule in `blender/verify/render_sheets.py` (J97) |

## Cause of each gap

| gap | cause | class |
|---|---|---|
| 128.61 m published for a 202.0 m tower | the probe measures the object standing at the subject's coordinate, and on a seven-tier stepped tower that object is a tier. Nothing prefers the tallest member whose footprint contains the coordinate (J74, J94) | **verification — open** |
| seven plates for twenty-eight bays | a stepped plan approximates a sawtooth at a quarter of the bay count; the builder declares it | **geometry — declared** |
| the frame is a street rather than a facade | the recorded viewpoint was boxed in at 20 m against the 27.4 m the frame needs, so the walk moved 10.3 m onto a sidewalk and the subject went to 61.5 m; and 18 mm is the widest lens the build will use (J79, J88) | verification — declared |
| three of thirteen rays clear | a cobra-head lamp 19.3 m from the lens, which the walk's clearance probe cannot see because a lamp is a prop (J88) | **verification — open** |
| 4.339 stops of development | a 25.3 deg December Sun in a Midtown canyon with a procedural sky at strength 0.0378 as the only fill (J83) | **verification — declared** |
| chroma 1.823 and contrast 0.725 | a street with a yellow cab and an orange steam stack against an almost monochrome study of dark glass whose highlights are clipped (J83) | reference — declared |
| 96 triangles of structures | three of the four tiles in range have no structures file (B13 remainder) | **data — open** |
| 909 props dropped, 833 of them trees | the props triangle budget at 1,126,750 triangles | performance |
| 5 cornices drawn | the kit triangle budget at 1,013,603 triangles, spent windows-first, plus 2,500 pieces suppressed under the landmark shells | **performance** |
| 252 people where the table asked 3,668 | the 1,125,000-triangle agent budget plus the placement rules | performance + verification |
| park ground under the terrain beyond 400 m | the park surfaces were draped on the fine grid and the terrain coarsens to 40.0 m (J40, J96) | verification — declared |
| no cloud | nothing in this build reads a historical sky | reference — no source exists |
