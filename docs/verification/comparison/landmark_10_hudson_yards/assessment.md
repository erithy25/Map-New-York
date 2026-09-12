# 10 Hudson Yards

`landmark_10_hudson_yards` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:10 Hudson Yards 2018-07 jeh.jpg by Jim.henderson, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2018-07-08 09:55:04, 1920x4134. [Commons page](https://commons.wikimedia.org/wiki/File:10_Hudson_Yards_2018-07_jeh.jpg) — the photograph's own view direction is derived from the image at **high** confidence.

**Camera** — 40.75153, -73.99750 (NYC_TM -4011, 5723) at z 14.0 m NAVD88 | azimuth 290.1°, pitch +0.0° | 35 mm on 36 mm (54.4° horizontal, 26.9° vertical, portrait) | 712x1534. Position and heading both come from the photograph: its own EXIF camera GPS, **114.3 m** from the item's recorded viewpoint, and 290.1° is the bearing from there to the subject — **0.1°** from the item's own recorded azimuth. **The lens stayed at the default 35 mm and the axis stayed level**, and the record says why: nothing built stands within 6 m of the subject's coordinate, so there was no measured height to widen the frame around. The camera was **not moved** — the view azimuth is clear for **115.5 m** against the 80.0 m this frame needs — and the nearest built thing in the frame is `prop_lamp_cobra_davit_0` **1.9 m** away at 13.4°. Ground under the camera reads **12.373 m** NAVD88 from 16 heightmap samples within 5.0 m, range 12.36 to 12.44 m; the viewpoint note names the raised surface the photographer stood on, so the heightmap height at the point itself is used.

**Sun** — azimuth 100.7°, elevation 47.0° at 2018-07-08T09:55:04−04:00, from the photograph's own **EXIF DateTimeOriginal**; 875.9 W/m² direct normal, sky at strength 0.0323, Filmic, **+3.84 stops and not clamped**. The linear frame's median is **0.01257** against a middle-grey target of 0.18 (J83); the physical rule would have given **0.0 stops**.

**In the scene** — 4,500,041 triangles: 8 building tiles (304,270 tris, none missing, none LOD-substituted), 8 landmark models of which 2 fall inside the 26.9° frame, 36,876 pavement polygons with **0 dropped**, 1,160 props, 5,042 kit pieces, 22 park-ground meshes over 220 surfaces, 4 structures tiles (65,356 tris), 73 vehicles and 304 people, terrain 99,948 tris at 2.0 m near / 40.0 m far with no holes.

## Verdict — the item's subject coordinate sits 11.1 m off the fabric it names, so no height was measured, no sightline was tested, and this sheet carries no visible-fraction verdict at all

**The chain stopped before it started.** The height probe cast 43 rays and **0** landed on built fabric. The record states the reason in its own words: *nothing built stands within 6 m of the subject's coordinate; the nearest built thing is `lm_c_hudson_yards.3`, 11 m away at bearing 292 deg, so the coordinate the item records is that far off the fabric it names*. Because there was no measured subject height, the lens was not widened and the axis was not tilted, and because there was no subject object, **no sightline was tested** — this is the one sheet in the queue with no `subject_visible_fraction` of any value, not even 0.000.

**So the render is a street, and the tower in it is incidental.** The frame looks west-north-west down West 30th Street: a tan brick warehouse block filling the left, a pale slab on the right, a slim blue-glass tower in the middle distance, and **the bottom two fifths of the frame is unmarked grey roadbed** with a single dashed lane line and a soft grey mound in the corner where the terrain grid meets the road surface. The photograph is 10 Hudson Yards alone, filling a 1920x4134 portrait frame against a deep blue July sky, its faceted glass crown cut at a diagonal.

**Where the tower does appear, it is an extruded slab.** The photograph's subject is a sculpted form: the shear at the base, the tapering plan, the raked top. The render's glass tower at 314.7 m is a straight prism with a uniform window grid. Chroma **0.0724** against the photograph's **0.2944**, a ratio of **0.246**, and most of that gap is one deep blue sky and one blue-glass curtain wall that reflects it.

**The median tone is nonetheless close.** Median **0.4965** against **0.4569** (**1.087×**), mean **0.5035** against **0.4858** (**1.036×**), with the two development offsets **0.258 stops** apart — the metered development doing what it is for (J83).

## What matches

* **The camera geometry is the best-agreeing in the queue**: the photograph's own GPS, and a bearing to the subject **0.1°** from the item's recorded azimuth.
* **The development is metered and unclamped**, +3.84 stops from a median linear luminance of 0.01257, against a physical rule that would have given 0.0.
* **The day type is right and was read, not assumed**: the crowd clock reads **Sunday** for 2018-07-08, which was a Sunday.
* **The pavement is the largest complete set in this queue**: 36,876 polygons, **0 dropped**, including **20,448** white markings, 5,265 sidewalk, 4,994 roadbed, 3,791 curb, 826 crosswalk and 613 median.
* **The record refuses to invent a height.** Rather than reading 387.1 m off the `c_hudson_yards` catalogue entry 114.0 m away, it reports 0 of 43 rays and names the 11.1 m offset (J74).
* **Trees are scaled from their own rows**: 283 placed, mean scale **0.961**, **0** out of band, 54 of them drawn from modelled branches.
* **Agents carry mixed detail**: 4 vehicles at LOD1, and of 304 people **40 at LOD1 and 1 at LOD0**.

## What does not match

* **The subject coordinate is 11.1 m off the fabric**, so there is no measured height, no widened lens, no tilt and no sightline test on this sheet.
* **The tower is an extruded prism** where the photograph's is a sheared, tapering, raked form.
* **Chroma is 0.246 of the photograph's**, 0.0724 against 0.2944.
* **Contrast is 0.758 of the photograph's**, standard deviation 0.1588 against 0.2095, and the render's fifth percentile is **0.3235** against the photograph's **0.1176** — the render has no deep shadow anywhere, because a level 35 mm frame of a street at 47° sun elevation has nothing in it that is properly dark.
* **All 4 structures tiles in range have no structures file** — 4 of 4 — over the Hudson Yards rail throat and the 7-train extension.
* **The near-field ground is under the terrain on 0.1679 of 554 samples** within 150 m, minimum **−3.711 m**, and the redrape had already moved **100,422** vertices by up to 3.288 m (J85). This is the worst near-band figure in the queue.
* **28,580 kit records were in range and 5,042 were drawn**, capped at a 961,182-triangle budget.
* **2,823 tree rows did not fit** the props budget of 1,100,629 triangles, **0** of the 229 impostor cards are procedural canopy stems, and 9 cards were dropped.
* **Twenty-seven props across seven kinds were wanted in range and have no asset**: 10 misc structure, 5 artwork, 4 drinking fountain, 3 memorial, 3 vending machine, 1 billboard, 1 parks comfort station.
* **Seven park-ground surface kinds fall back to the builder's flat colour** — cemetery grass, sport court, greenstreet grass, park grass, pool water, recreation grass, bare ground (J40).
* **A cobra-head mast stands 1.9 m from the lens.** It does not block the subject, because no sightline was tested, but it is inside the 8 m of nothing-built the walk is supposed to enforce.
* **The frustum finds only the Hudson Yards composite at 430.9 m, 18.4° off axis**, and the High Line at 674.5 m, 56.1° off — neither is the subject, and the subject has no model of its own to find.
* **The crowd is a third of the ask**: the table wanted 308 vehicles and 986 people; 381 and 1,262 were simulated and **1,266** dropped — 535 pedestrians and 179 vehicles outside the radius, 227 pedestrians and 111 vehicles at the agent triangle budget, 98 pedestrians in the carriageway without crossing, 86 not on a walkable surface, 8 above the observer, 4 inside a building, and **14 riderless bodies**.
* **No cloud and no sky colour.** The reference's July sky is the strongest thing in it; the render's is a Nishita dome at strength 0.0323.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| no height, no sightline, no visible fraction | the item's stored subject coordinate is 11.1 m from the nearest built fabric, and the probe's reach is 6 m; the chain reports the miss and then has nothing to test. This is J90's family — a stored coordinate that cannot be used as it stands — on the subject rather than the viewpoint | **data — open, one coordinate wrong** |
| the tower is an extruded prism | the Hudson Yards composite models massing from footprint and height; a sheared, tapering form is not a shape this build authors | geometry — declared scope |
| chroma 0.246×, sd 0.758×, p05 0.3235 against 0.1176 | a level 35 mm street frame with no sky and no reflective curtain wall in it, against a portrait of one tower against deep blue | reference + consequence of the row above |
| 4 of 4 structures tiles without a file | no structures file was built for any tile in range | **data — open, four tiles unbuilt** |
| 0.1679 of near-field ground under the terrain, min −3.711 m | the Hudson Yards platform sits above a 2013 bare-earth DEM and the redrape cannot close the gap (J85) | geometry — open, measured |
| 28,580 kit records in range, 5,042 drawn | the kit triangle budget at 961,182 | performance |
| 2,823 tree rows dropped, 0 canopy stems | the props triangle budget at 1,100,629 triangles; no mapped woodland polygon in this radius | performance + declared rule |
| a mast 1.9 m from the lens | the 8 m nothing-built rule is applied where the walk moves the camera, and this camera was not moved | **verification — open** |
| 27 props across seven kinds unmapped | no asset exists for those kinds | data |
| seven park surface kinds flat-coloured | the texture catalogue has no photographic set for any of them (J40) | **declared decision** |
| 304 people where the table asked 986 | the agent triangle budget plus the placement rules, each with its count | performance + verification |
| no cloud | nothing in this build reads a historical sky | reference — no source exists |
