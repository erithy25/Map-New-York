# Port Authority Bus Terminal

`landmark_port_authority_bus_terminal` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Stairs to downtown A C E platform at 42nd Street Port Authority Bus Terminal.jpg by 4300streetcar, CC BY 4.0 (https://creativecommons.org/licenses/by/4.0), taken 2025-01-18 11:56:44, 1920x1280. [Commons page](https://commons.wikimedia.org/wiki/File:Stairs_to_downtown_A_C_E_platform_at_42nd_Street_Port_Authority_Bus_Terminal.jpg) — the photograph's own view direction is derived from the image at **high** confidence. **It is a subway mezzanine.** The frame is the stair down to the downtown A/C/E platform: a *Downtown & Brooklyn* sign with the three bullets, blue-painted steel columns, turnstiles beyond, a tiled floor, a mosaic wall of coloured discs at the left, fluorescent fittings and exposed conduit overhead, and thirty-odd people waiting.

**Camera** — 40.756298, -73.99245 (NYC_TM -3568, 6280) at z 12.6 m NAVD88 | azimuth 70.0°, pitch +0.3° | 31 mm on 36 mm (59.8° horizontal, 42° vertical, landscape) | 1280x854. The camera stands on **the item's recorded viewpoint**, the photograph's own EXIF GPS being **252.9 m** away — three metres past the 250 m at which it could be the same view. The recorded azimuth agrees with the bearing to the subject to **0.1°**. The walk then **moved it 31.2 m** onto the nearest surveyed roadbed polygon, the recorded viewpoint being boxed in at **6 m** against the **60.1 m** the frame needs. From there the view is clear for **72.2 m**, the nearest built thing is `lm_c_times_square.33` **14.5 m** away, and no simulated agent stands within 20 m. The ground reads 11.007 m NAVD88, the 10th percentile of 113 samples within 12 m, range 10.91 to 11.25 m.

**Sun** — azimuth 177.4°, elevation 28.8° at 2025-01-18T11:56:44−05:00, from the photograph's own **EXIF DateTimeOriginal**; 759.4 W/m² direct normal, sky at strength 0.0362, Filmic, **+6.00 stops** — **clamped** from a wanted **6.99**, with the record's standing note. The physical rule would have given **0.58 stops**.

**In the scene** — 4,500,057 triangles: 5 building tiles (228,796 tris, 0 missing, 0 LOD-substituted), 4 landmark models of which 1 can fall inside the 59.8° frame, 25,558 pavement polygons, 1,622 props, 10,764 kit pieces, 14 park-ground meshes, 40,632 triangles of structures, 88 vehicles and 423 people.

## Verdict — a sheet that used to be refused now renders, and the reference is a subway mezzanine

**This is the second of the two frames the luminance gate used to reject**, alongside Federal Hall: it was published as `rejected_unusable_frame` at mean **0.034**, *near-black*. It now renders at mean **0.339** with `usable: true` and no retry. The mechanism is the same as on the Federal Hall sheet — the walk scores its candidates on the subject's own sightline (J79) and moved 31.2 m onto a roadbed with 72.2 m of clear view, where the recorded viewpoint had 6 m. **Both sheets the gate refused in the earlier pass now stand**, and the pass closes at 171 rendered, 0 failed, 1 declined.

**The measurements are strong and the picture is not.** The probe found fabric on **43 of 43 rays** and measured **41.67 m** above a ground of 11.91 m on `lm_c_times_square.36`, whose plan extent is **279.3 m by 235.4 m** — the terminal's own two-block footprint. The nearest catalogue origin is the composite's own at **389.0 m**, past the 120 m the old rule looked in, so the height came from the geometry (J74). Twelve of thirteen sightline rays are clear and **twelve land on the subject**, giving **0.923** — one of the highest fractions in the pass. And the published frame is a large dark wedge of the terminal's flank seen from close below, a pale textured band above it, a thin lit strip carrying a line of pedestrians, and a wide grey roadway. Eleven of the twelve rays meet the subject's own fabric nearer than the recorded distance, first at **15.8 m**, which is what a visible fraction of 0.923 means here: the camera is up against the building.

**And the reference is an interior, for the fourth time in the pass.** A subway mezzanine under the terminal, with wayfinding, turnstiles and a mosaic wall, none of which an exterior-only build carries (B10, I5, J100, J104). Its own median sits **2.285 stops below** the grey convention — a dim mezzanine exposed for its fluorescents — against the render's **0.676 below**, a **+1.609-stop** difference and a p50 ratio of **1.745**.

## Measured for this assessment

| figure | how |
|---|---|
| mean 0.034 before, mean 0.339 now | the earlier figure is this record's own previous `frame` block, which read `rejected_unusable_frame` with reason *near-black (mean 0.034)*; the current one is its `frame.mean` with `usable: true` and `frame_retry: null` |
| 171 rendered, 0 failed, 1 declined | `blender_out/render_all_state.json` at the end of the v16 pass |

## What matches

* **The sheet exists at all.** mean **0.339**, sd **0.1839**, `usable: true`, against the **0.034** that got it rejected before (J79's fix).
* **The height and the footprint** — 41.67 m on **43 of 43** rays, 279.3 m by 235.4 m in plan, taken from the geometry rather than the composite's 365.8 m catalogue figure (J74).
* **The aim** — the recorded azimuth agrees with the measured bearing to **0.1°**, and the frustum puts the composite **4.6° off axis** at 318.8 m.
* **Nothing was capped in the props** — **1,622 placed of 1,734 in range**, **0 dropped for budget** — and the kit came within a fifth of complete, **10,764 of 13,423** against a **1,888,168-triangle** budget, the second largest kit budget in the pass.
* **The kit inventory is varied** — 10,095 windows, 244 storefronts, 75 window accessories, 55 bulkheads, 48 entry doors, **45 fire escapes**, 45 scaffold pieces, 40 parapets, 37 HVAC units, 20 cornices, 11 water towers.
* **The block is furnished** — **264 Citi Bike units**, 104 cooling towers, 96 street lamps, 85 manholes, 55 hydrants, 20 subway vent grates, **6 subway entrances**, 8 LinkNYC kiosks, 3 newsstands, 2 bus shelters.
* **25,558 pavement polygons and none dropped**, including 10,733 white markings and 557 crosswalk.
* **The park ground is exact near the camera** — within 150 m, 72 samples, an under-fraction of **0.0**, a median clearance of **0.126 m**, no z-fighting.

## What does not match

* **The reference is a subway mezzanine**, and this build has no interiors (B10, I5, J100, J104).
* **The frame is the terminal's flank from 15.8 m**, so a visible fraction of 0.923 describes a wall at close range rather than a building.
* **Published at the +6.00-stop clamp** from a wanted 6.99, and still **0.676 stops** below the grey convention (J83).
* **p50 1.745, mean 1.119** — the photograph's median sits **2.285 stops** below the convention, the second deepest of any reference in the pass. Read as an exposure comparison, not a scene one.
* **Three of five structure tiles have no file** — 2 imported, **3 without a file** — over the Eighth Avenue line and the terminal's own bus ramps, although **40,632 triangles** came from the two that do.
* **18 props across two kinds in range have no asset** — 17 misc structures, 1 artwork.
* **Only 33 trees are drawn from modelled branches** against 923 impostor cards, **260** of the 956 trees are a substituted species, 2 are out of band, and **52** of the cards are procedural canopy stems (Stage 55).
* **Beyond 400 m the park ground reads under the terrain on 0.4979 of 699 samples**, with a worst of **−9.831 m** — the deepest under-reading on any sheet written so far — and a median clearance of **0.001 m**, meaning half those samples sit exactly on the terrain and half below it.
* **3,348 agents were dropped** — 699 pedestrians at the agent triangle budget, 345 vehicles at the budget, **164 in the carriageway without crossing**, 63 where the planimetric data has no sidewalk (J101), 20 cyclists the fleet exports without a rider, 15 vehicles where there is no roadway.
* **Three quarters of the photograph's colour** — chroma **0.758** — and **0.722** of its contrast, both across unrelated images.
* **No cloud.** The reference has no sky in it; nothing in this build reads a historical sky.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the reference is a subway mezzanine | the chooser paired an interior photograph with an exterior-only build; the fourth such pairing in the pass (B10, I5, J100, J104) | **verification — open (J104)** |
| a visible fraction of 0.923 on a wall at 15.8 m | the walk's best candidate has the camera against the terminal's flank, and the sightline counts fabric rather than resemblance (J78, J79) | verification — true and misleading |
| published at the clamp, 0.676 stops under | a January frame in a Midtown canyon with a 28.8° Sun; the meter asked for 6.99 stops and the clamp refused (J83) | verification — declared, and correct |
| p50 1.745 | the photograph is developed 2.285 stops below the grey convention for a dim mezzanine (J83) | reference |
| three of five structure tiles without a file | those tiles are unbuilt, over the Eighth Avenue line and the bus ramps | **data — open** |
| 18 props across two kinds unmapped | no asset exists for those kinds | data |
| 33 trees from modelled branches, 260 substituted, 52 procedural stems | the modelled-branch radius is 120 m, the species lists do not cover this stock, and woodland polygons are filled by rule (Stage 55) | performance + data |
| a −9.831 m far-field tail, median clearance 0.001 m | the park builder drapes on its own heightmap and the scene's coarsens to 40 m at the edge; the redrape closes the near field to 0.0 and leaves this (J71) | **geometry — open, and deepest here of any sheet written so far** |
| 423 people of 1,874 asked | the agent triangle budget plus the placement rules, each with its own count | performance + verification |
| no cloud | nothing in this build reads a historical sky | reference — no source exists |
