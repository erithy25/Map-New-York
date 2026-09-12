# Seagram Building (375 Park Avenue)

`landmark_seagram_building` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Seagram Building Nov 2025 24.jpg by Epicgenius, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2025-11-05 08:44:40, 1920x1440. [Commons page](https://commons.wikimedia.org/wiki/File:Seagram_Building_Nov_2025_24.jpg) — the photograph's own view direction is derived from the image at **high** confidence. It is the plaza-level colonnade and the four storeys above it, straight on: bronze mullions and spandrels, the bronze-tinted glass **lit from inside** at 08:44 on a November morning so the whole wall reads as a lantern, people at the entrance doors, and the travertine plaza filling the foreground.

**Camera** — 40.758179, -73.972885 (NYC_TM -1932, 6461) at z 18.2 m NAVD88 | azimuth 49.4°, pitch +31.9° | 18 mm on 36 mm (90.0° horizontal, 74° vertical, landscape) | 1208x906. The camera stands on **this photograph's own EXIF GPS**, **57.5 m** from the item's recorded viewpoint; the item's recorded azimuth is 70.0°, **20.6° away**. The lens was **held at the 18 mm floor** and tilted **+31.9°**, and the record states the consequence: the top of the subject is still cut off, and the verticals converge so the frame is not comparable with the photograph on proportion. The walk did not move it: the view azimuth is clear for **65.4 m** against a **36.9 m** requirement, and the nearest built thing in the frame is **`t_-2_6_glass_curtain` 4.2 m** away — one tile's glass-curtain surfaces joined into a single object, and the camera is standing against it (J94). The ground reads 16.586 m NAVD88, the 10th percentile of 113 samples within 12 m, range 16.02 to 17.86 m.

**Sun** — azimuth 134.8°, elevation **20.4°** at 2025-11-05T08:44:40−05:00, from the photograph's own **EXIF DateTimeOriginal**; **659.3 W/m²** direct normal, sky at strength 0.0403, Filmic, **+6.00 stops** — **clamped** from a wanted 6.24, with the record's standing note: *a scene this far from a photographable level is not developed into a picture of one*. The physical rule would have given **1.09 stops**. A 20° Sun into a Park Avenue canyon at a quarter to nine in November is about as little light as a daylight frame gets.

**In the scene** — 4,500,306 triangles: 6 building tiles (309,456 tris, 0 missing, 0 LOD-substituted), 9 landmark models of which 5 can fall inside the 90.0° frame, 24,041 pavement polygons, 789 props, 5,446 kit pieces, 23 park-ground meshes, 2,920 triangles of structures, 53 vehicles and 299 people.

## Verdict — the height is right to a metre and the tone is among the closest in the pass, and the subject is two rays out of thirteen behind a joined glass mesh

**Two measurements on this sheet are as good as the pass gets.** The probe found fabric on **42 of 43 rays** and measured **155.9 m** above a ground of 16.53 m, against the catalogue's **157.0 m** for `c_seagram_building` whose origin stands 32.2 m away — agreement to about a metre on a 157 m tower. And the two halves' tone agrees almost exactly: mean **1.002**, p50 **1.012**, standard deviation **1.059**, with the photograph's median sitting **0.026 stops below** the grey convention and the render's **0.013 above** — a difference of **+0.039 stops**. Ranked over the pass, that is the **second closest** tonal agreement of any sheet and the fourth smallest exposure gap. It is worth saying why, because it is the metered development's best argument: both halves are genuinely dark scenes — a 20° November Sun in a Park Avenue canyon — and both were developed to the same convention, one by a photographer and one by J83's meter. The render needed **+6.00 clamped stops** to get there and still landed within a fortieth of a stop.

**And the subject is barely in the frame.** Of thirteen rays, **5 are clear**, **2 land on the subject**, 2 go into nothing, and the rest stop at **10.5 m** on `t_-2_6_glass_curtain` — the same joined mesh the camera is standing 4.2 m from. The visible fraction is **0.154**. The published render looks steeply up a canyon: a pale blue-grey glass wall filling the right third, dark slabs beyond, a street tree, pedestrians, a black car, and **432 Park Avenue** in the distance, its grid of square windows unmistakable. The Seagram's own bronze tower is not identifiable in it.

**The photograph's light comes from inside the building, and the render has none of it.** At 08:44 in November the Seagram's office floors are lit and the curtain wall glows amber through bronze glass; that warm wall is most of the reference frame's brightness and all of its colour. The build **does** have the pieces for it: `facade/kit_ids.py` defines a **lit twin of every window type that has an interior card**, and `facade/placements.py` records `flags` bit 0 as *lit at night*, choosing between the lit and unlit kit id at placement time. What this frame shows is no lit window at all, and the record cannot say which of two reasons that is — no window in range was baked as a lit twin, or the daylight pass draws the unlit one. Either way a tower at a quarter to nine in November comes out as dark as a tower at noon, and the sheet's own kit block reports only the category, `window`, never which twin. Measured the other way round, the render still carries **1.354×** the photograph's chroma, because a clear Nishita sky and a green street tree outweigh a monochrome bronze wall.

## What matches

* **The height, to about a metre** — 155.9 m measured against a catalogued 157.0 m, on 42 of 43 probe rays.
* **The tone, to a fortieth of a stop** — mean 1.002, p50 1.012, sd 1.059, exposure difference +0.039 stops; second closest in the pass (see *Measured*).
* **432 Park Avenue is correctly drawn and correctly placed** in the distance, and the frustum accounts for four more landmarks in the 90° frame: Lever House at 157.9 m, the Citigroup Center at 254.8 m, the Lipstick Building at 342.9 m and Billionaires' Row at 732.1 m.
* **The block is furnished for Midtown East** — **344 Citi Bike units**, 87 street lamps, 72 manholes, 49 cooling towers, 40 hydrants, 26 subway vent grates, **17 subway entrances**, 4 LinkNYC kiosks, 2 newsstands.
* **The fleet is a Park Avenue fleet** — **19 yellow taxis** and **9 boro taxis** against 12 sedans, 5 SUVs, 4 black cars, 3 vans, 1 bus.
* **24,041 pavement polygons and none dropped**, including **1,084 plaza** polygons — the Seagram plaza is a paved surface in the data.
* **69 trees are drawn from modelled branches** within 120 m against 61 impostor cards, and **0** are scaled outside the allowed band.

## What does not match

* **The subject is two rays of thirteen**, behind a joined glass-curtain tile mesh 10.5 m from the lens (J94).
* **The bronze is absent.** Mullions, spandrels and tinted glass are the building's entire character and the render's wall is pale blue-grey.
* **No window is lit.** The photograph's wall glows from inside at 08:44 in November; nothing in the render is lit from within, although the kit defines a lit twin for every window type with an interior card and the placements carry a *lit at night* flag.
* **Published at the +6.00-stop clamp**, from a wanted 6.24 — the frame is far from a photographable level and the record says so (J83).
* **The plaza's travertine is not in the picture.** The photograph's foreground is the plaza; the render's is roadway.
* **Nearly 1.4× the photograph's colour** — chroma **1.354** — from a clear sky and a street tree against a monochrome wall.
* **The frame is not comparable on proportion**, by the record's own words: 18 mm held at the floor, +31.9° of tilt, verticals converging, and the top of the tower cut off.
* **Props were capped to under a third** — **789 placed of 2,492 in range** at a **1,034,356-triangle** budget, **1,495 dropped for budget**, **992** of them tree rows, 7 dropped on a suppressed building.
* **Kit was capped to one piece in six** — **5,446 of 35,266 in range** at an **839,722-triangle** budget, the lowest kit budget on any sheet written so far, with **1,427 further pieces suppressed** under landmark shells; the openings are drawn rather than cut (Stage 34 / J51).
* **Four of six tiles in range have no structures file** — 2 imported, **4 without a file**, **2,920 triangles** — over the Lexington Avenue–53rd Street interchange.
* **6 props across four kinds in range have no asset** — 3 payphones, 1 drinking fountain, 1 memorial, 1 vending machine.
* **There is no park ground within 150 m to check** — **0 samples** — and beyond 400 m the under-fraction is **0.4538** over 130 samples, the worst far-field reading on any sheet written so far, with a worst depth of **−1.288 m**.
* **3,768 agents were dropped** — **1,259 pedestrians at the agent triangle budget**, 956 outside the radius, 746 vehicles outside the radius, 551 vehicles at the budget, 210 pedestrians in the carriageway without crossing, 33 riderless bodies, 13 off a walkable surface.
* **No cloud.** The reference's sky is a thin November overcast; nothing in this build reads a historical sky.

## Measured for this assessment

| figure | how |
|---|---|
| the second closest tonal agreement in the pass | ranked every record carrying `scene.structures` by the sum of the distances of `frame_stats.json`'s `render_over_reference.mean` and `.p50` from 1.0; the Washington Square Arch sheet is closer (mean 1.007, p50 0.995) and St John the Divine is next after this one |
| 432 Park Avenue | a building's name rather than a measurement: the slender white tower visible in the render's distance, identified by its grid of square windows |
| the fourth smallest exposure gap | ranked the same set by the absolute `exposure_offset_stops` difference: the Bronx Whitestone Bridge at +0.007, the Washington Square Arch at −0.015 and the Broadway/Wall Street drive at +0.030 are smaller |

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the subject is two rays of thirteen | eight rays stop 10.5 m out on one tile's glass-curtain surfaces joined into a single object, the same mesh the camera stands 4.2 m from (J94) | **geometry — open, the join is the fault** |
| no bronze | the shells and the landmark model carry the material palette's neutral glass, and per-building facade colour has no source in this build (J66) | data — declared, and open |
| no window is lit | the kit has a lit twin per window type and the placements carry a *lit at night* flag chosen at placement time, and this frame shows none of them; the record reports the kit category only, so it cannot say whether none was baked here or the daylight pass draws the unlit twin | **verification — open, and the record cannot answer it; it is most of the reference's brightness** |
| published at the +6.00 clamp | a 20.4° Sun into a Park Avenue canyon in November; the development is metered on the frame and clamped (J83) | verification — declared, and correct |
| chroma 1.354 | a clear Nishita sky and a green street tree against a monochrome bronze wall | reference + geometry |
| the frame is not comparable on proportion | the subject tops out 64° above the horizon at 74 m, and 18 mm with a 74° vertical field is the floor past which distortion would break the comparison | verification — declared on the sheet |
| the plaza is not in the foreground | the camera stands on the photograph's GPS 57.5 m from the recorded viewpoint, looking up a canyon rather than across the plaza | verification — the pairing |
| 789 props of 2,492, 992 tree rows dropped | the props triangle budget at 1,034,356 | performance |
| 5,446 kit pieces of 35,266, 1,427 more suppressed | the kit triangle budget at 839,722, plus the landmark shell replacing the tile's buildings | performance + declared decision |
| openings drawn on the shell | Stage 34 / J51, measured at +48 GB | declared decision — physically impossible here |
| four of six tiles without a structures file | those tiles are unbuilt, over the Lexington Avenue–53rd Street interchange | **data — open** |
| 6 props across four kinds unmapped | no asset exists for those kinds | data |
| under-fraction 0.4538 beyond 400 m | the park builder drapes on its own heightmap and the scene's differs, and only 130 samples fall in that band on this sheet (J71) | geometry — open, bounded |
| 299 people of 1,989 asked | the agent triangle budget plus the placement rules, each with its own count | performance + verification |
| no cloud | nothing in this build reads a historical sky | reference — no source exists |
