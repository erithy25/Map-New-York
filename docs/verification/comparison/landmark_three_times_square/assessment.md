# 3 Times Square (Thomson Reuters Building)

`landmark_three_times_square` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Times Sq Sep 2021 76.jpg by Epicgenius, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2021-09-21 10:33:19, 1920x1280. [Commons page](https://commons.wikimedia.org/wiki/File:Times_Sq_Sep_2021_76.jpg) — the photograph's own view direction is derived from the image at **medium** confidence, and the sheet bears that out. It is a close-up of the podium: the **CHASE** sign twice over, a large blue LED wall of hexagonal cells, a red neon *Subway* sign, glazed bays and their reveals, all from a few metres away looking up.

**Camera** — 40.757835, -73.986054 (NYC_TM -3010, 6433) at z 15.3 m NAVD88 | azimuth 210.0°, pitch +17.5° | 18 mm on 36 mm (90.0° horizontal, 67° vertical, landscape) | 1280x854. The camera stands on **the item's recorded viewpoint**, because **this photograph carries no camera GPS**, and the recorded azimuth agrees with the bearing to the subject to **0.1°**. The walk then **moved it 34.1 m** onto the nearest surveyed crosswalk polygon, because *the recorded viewpoint is inside `t_-4_6_roof_membrane`* — the third sheet written so far where a joined roof-membrane tile mesh swallows a street-level viewpoint (J94). From there the view azimuth is clear for **89.9 m** against a **75.0 m** requirement, the nearest built thing is `t_-4_6_glass_curtain` **14.5 m** away, and the note records a car **0.8 m** from the lens, which the cull over the observer then removed. The ground reads 13.716 m NAVD88, the 10th percentile of 113 samples within 12 m, range 13.62 to 14.97 m.

**Sun** — azimuth 133.9°, elevation 39.4° at 2021-09-21T10:33:19−04:00, from the photograph's own **EXIF DateTimeOriginal**; 837.9 W/m² direct normal, sky at strength 0.0336, Filmic, **+3.41 stops** metered and unclamped against a linear median of **0.016882** and a target of **0.18**. The physical rule would have given **0.13 stops**.

**In the scene** — 4,204,551 triangles: 6 building tiles (315,108 tris, 0 missing, 0 LOD-substituted), 4 landmark models of which 1 can fall inside the 90.0° frame, 25,103 pavement polygons, 1,654 props, 7,471 kit pieces, 22 park-ground meshes, 21,408 triangles of structures, 51 vehicles and 372 people.

## Verdict — a good Times Square street frame whose subject is two rays of thirteen, because a LinkNYC kiosk stands seven metres from the lens

**This is one of the better street frames in the pass.** Seventh Avenue runs away south between towers of the right heights and glazing types, a yellow taxi and two cars stand at the lights, pedestrians cross the near kerb, and a **LinkNYC kiosk carries legible text** — *LinkNYC*, *FREE GIGABIT Wi-Fi* — which is worth naming because the billboards two blocks away carry none. The kiosk's own display is a modelled sign face with content, so the build's refusal to invent copy is specific to advertising rather than general (B5, B15a).

**And that kiosk is what hides the subject.** Of thirteen rays, **4 are clear**, **2 land on the subject**, 2 pass into nothing, and the rest stop at **7.1 m** on `prop_linknyc_kiosk_4`. The visible fraction is **0.154**, and the walk's own score at the point it chose was the same 0.154, so nothing drifted between the decision and the render — this was the best of the candidates. A 1.4 m-wide kiosk seven metres from a 90° lens covers a large solid angle, and the subject is 177 m away.

**The probe measured the member, not the composite, and that is the rule working.** It found fabric on **43 of 43 rays** and reported **162.1 m** above a ground of 16.08 m on `lm_c_times_square.60`, a **61.6 m by 51.3 m** mass. The catalogue's nearest origin is `c_times_square` itself at **61.5 m**, carrying **365.8 m** — the composite's tallest member. Had that figure been used, a 162 m tower would have been framed as a 366 m one (J74, J94).

**The two halves are at different distances again.** The photograph is a few metres from the podium's signage; the render is 177 m up the avenue. Nothing in the reference — the Chase sign, the LED wall, the neon — has a counterpart, and the reference's own confidence is recorded as **medium**.

**The measured gap is mostly exposure and signage.** p50 **1.708**, mean **1.283**, with the photograph's median **1.382 stops below** the grey convention (a frame exposed for a bright LED wall) against the render's **0.236 above** — a **+1.618-stop** difference (J83). Chroma **0.482**: the reference's blue LED cells and red neon are half its colour, and the render's equivalents are dark glass.

## What matches

* **The street reads as Times Square** — tower heights, glazing, kerb line, a taxi at the lights and a crowd on the sidewalk.
* **The LinkNYC kiosk carries its own legible content**, so the build's no-invented-copy rule is specific to advertising rather than blanket (B5, B15a).
* **The height was measured off the member** — 162.1 m on **43 of 43** probe rays, rather than the composite's catalogued 365.8 m (J74).
* **The aim** — the recorded azimuth agrees with the measured bearing to **0.1°**.
* **Nothing was capped** — props **1,654 of 1,754 in range**, kit **7,471 of 11,831**, **0 dropped for budget**.
* **The block is furnished for Times Square** — **11 subway entrances**, 107 cooling towers, 87 street lamps, 75 manholes, 50 hydrants, 19 subway vent grates, 6 LinkNYC kiosks, 5 newsstands, and an **FDNY engine** in the fleet.
* **104 billboard kit pieces** are placed and lit, and **25,103 pavement polygons** with **0 dropped**, including **1,493 plaza**.
* **The park ground is nearly exact in the middle distance** — between 150 and 400 m, an under-fraction of **0.0135** over 74 samples.

## What does not match

* **The subject is two rays of thirteen**, behind a LinkNYC kiosk 7.1 m from the lens.
* **The reference is a close-up of the podium's signage** and the render is a street view from 177 m. Different distances, at **medium** reference confidence.
* **No Chase sign, no LED wall, no neon.** The billboards in the render are blank by the declared rule (B5, B15, B15a), and the kiosk is the only sign face in the frame with content.
* **The recorded viewpoint tested as inside a joined roof-membrane tile mesh**, forcing a 34.1 m move (J94).
* **4,360 kit pieces were suppressed** under landmark shells — more than half of what was in range — so the tile's own facades give way to the composite.
* **Five of six tiles in range have no structures file** — 1 imported, **5 without a file** — over the Times Square–42nd Street interchange, the same shortfall as the One Times Square and Marriott Marquis sheets.
* **Only 3 trees are drawn from modelled branches** against 1,237 impostor cards, and **636** of the 1,240 trees are a substituted species; 16 props were dropped on a suppressed building.
* **The render is brighter at the midtone** — p50 **1.708**, mean **1.283** — and flatter, sd **0.828**. The photograph's median sits **1.382 stops below** the grey convention and the render's **0.236 above** (J83).
* **Under half the photograph's colour** — chroma **0.482**.
* **15 props across five kinds in range have no asset** — 9 misc structures, 3 artworks, 1 drinking fountain, 1 memorial, 1 real-time information sign.
* **There is no park ground within 150 m to check** — **0 samples** — and beyond 400 m the under-fraction is **0.2616** over 1,009 samples.
* **3,618 agents were dropped** — 1,122 pedestrians outside the radius, 894 at the agent triangle budget, 626 vehicles outside the radius, 553 at the budget, 198 in the carriageway without crossing, **169 off a walkable surface** (J101), 32 riderless bodies, 23 vehicles off the carriageway, 8 pedestrians and 2 vehicles over the observer, 1 pedestrian inside a building.
* **The clearance note and field disagree about the nearest agent** — the note names a car at **0.8 m**, the field a pedestrian at 9.9 m after the cull, and nothing in the note says it was measured before the cull (J98).
* **No cloud.** The reference has almost no sky in it; nothing in this build reads a historical sky.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the subject is two rays of thirteen | a LinkNYC kiosk 7.1 m from a 90° lens covers a large solid angle, and the walk's best candidate scored the same 0.154 (J79) | verification — the best available from a surveyed viewpoint |
| the reference is a podium close-up | the photograph carries no GPS, so the item's recorded viewpoint 177 m out was used; the chooser accepted it at medium confidence | **verification — open, the pairing** |
| no Chase sign, LED wall or neon | no advertising copy is invented anywhere; the billboards are placed and blank (B5, B15, B15a) | declared decision |
| the viewpoint tested as inside a roof | one tile's roof-membrane surfaces are joined into a single object whose extent covers a street-level point (J94) | **geometry — open, the join is the fault** |
| 4,360 kit pieces suppressed | the landmark shell replaces the tile's buildings and takes their kit with it | declared decision |
| five of six tiles without a structures file | those tiles are unbuilt, over the Times Square–42nd Street interchange | **data — open, five tiles** |
| 3 trees from modelled branches, 636 substituted | the modelled-branch radius is 120 m and the species lists do not cover this stock | performance + data |
| p50 1.708, chroma 0.482 | the photograph is developed 1.382 stops below the grey convention for a bright LED wall, and its blue and red signage has no counterpart (J83) | reference + declared decision |
| 15 props across five kinds unmapped | no asset exists for those kinds | data |
| no park-ground samples within 150 m | there is no park within 150 m of this camera (J71) | verification — nothing to check |
| 372 people of 2,283 asked | the agent triangle budget plus the placement rules, each with its own count | performance + verification |
| the note names a 0.8 m car the frame does not contain | the note is written before the cull over the observer and the field after it, and the note does not say so (J91, J98) | **verification — open, a record inconsistency** |
