# Queens vinyl-sided houses

`street_queens_vinyl_siding` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:60th Lane Ridgewood.jpg by Kidfly182, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2022-04-09 11:53:20, 1920x1440. [Commons page](https://commons.wikimedia.org/wiki/File:60th_Lane_Ridgewood.jpg) — the file's viewpoint confidence is **low** and its own GPS puts it on 60th Lane in **Ridgewood**. A row of brick houses with rounded two-storey bay fronts, limestone banding and carved panels between the floors, striped canvas awnings over the parlour windows, iron-railed stoops, an American flag, wheelie bins at the kerb, a cherry in **blossom** across the top of the frame, and a blue sky with cumulus behind.

**Camera** — 40.744, -73.906 (NYC_TM 3728, 4933) at z 19.518 m NAVD88, a 1.6 m standing eye over terrain read at 17.918 m — the 10th percentile of 113 samples within 12.0 m | azimuth 0.0°, pitch 0.0° | 35 mm on 36 mm (54.432° horizontal) | 1208x906. The camera stands on the item's recorded viewpoint, 60th Street near 39th Avenue in **Woodside**, because *"this photograph's own EXIF GPS is 5,176 m away, past the 250 m at which it could still be the same view"* — **the largest such gap of any item in the pass that names a place**, and five kilometres between the two halves. The walk then moved **46.1 m** onto a crosswalk polygon: *"inside `t_3_4_roof_membrane` (a ray straight up from the eye point hits its roof)"*, the fourth sheet in the pass whose camera was placed or moved by that test (J115). From there the view is clear for 60 m and the nearest built thing is `t_3_4_red_brick` **13.1 m** away. `scored_on_subject_sightline` is **false**; this item names no subject, so there is no probe, no sightline and no visible fraction.

**Sun** — azimuth 152.3°, elevation 54.1° at 2022-04-09T11:53:20-04:00, from the photograph's own EXIF DateTimeOriginal; 902 W/m² direct normal, Nishita sky, Filmic, **+0.95 stops**. Metered: **0.950 stops** on a linear median of **0.093192** against a physical rule of 0.0 — one of the smallest developments in the pass, because a 54° April Sun on a wide low-rise street is close to a photographable level already.

## Verdict — no vinyl siding in either half, five kilometres between them, and a cherry in bloom the build cannot render

**Neither half shows a vinyl-sided house.** The item asks for the vernacular that covers most of eastern Queens: two-family houses re-clad in vinyl clapboard. The photograph is of Ridgewood's brick row houses — bay-fronted, limestone-banded, awninged, among the most consistently *un*-clad blocks in the borough. The render is of a Woodside corner where the frame is filled by a red-brick flank wall and the buildings behind it are brick too. The tile's material list does carry **`vinyl_siding` (WoodSiding009, 1.626 m)**, so the surface exists in this build and is used on the tile; it is simply not in this frame, and the reference could not have shown it in any case.

**And the two blocks are five kilometres apart.** Ridgewood and Woodside are both Queens and neither is the other. `pick_reference_photo` gates distance only for the drive-through group (J60, measured across the pass in J112), so a streetscape item takes the best-lit, best-clocked photograph wherever it was taken. This is the widest that gate has opened for a place-naming item anywhere in the pass.

**The cherry is in bloom and this build has no blossom.** The photograph was taken on 9 April with a Prunus flowering directly over the camera, and the render's trees are correctly bare, because `leaf_off` is true through 15 April and the canopy is a **binary switch with two appearances per species, in leaf and out of it**. There is no bloom state, no bud, no leaf-out, no autumn. Prunus is the fourth commonest genus in the 2015 street-tree census at 41,653 trees, and it has no asset (J108). This is the second sheet in the pass whose reference shows a flowering cherry and whose render cannot; the City Hall sheet is the other.

**The render is a stop brighter than the photograph and the reason is the sky.** The reference's median sits **0.998 stops below** the grey convention — a narrow street with a canopy over it, dark brick, deep shade under the awnings — and the render is metered to 0.235 above. That is a **1.233-stop** gap and a p50 ratio of **1.499**: the render's median is half again the photograph's. Contrast is **0.882** and chroma **0.641**, the render carrying two thirds of the photograph's colour, which is what happens when awnings, a flag, blossom and blue sky with cumulus are replaced by brick, concrete and a clear procedural dome.

**The row-house vocabulary is in the kit.** **5,457 pieces with nothing capped and nothing suppressed**: 3,748 windows, 648 window accessories, **391 parapets**, **320 entrance doors**, 79 bulkheads, 69 storefronts, 50 rooftop units, **43 fences**, 37 cornices and 33 string courses. A parapet and an entrance door on every house is the correct rhythm for this kind of block. What the kit has no piece for is the thing the photograph is made of: the **rounded bay front**. Every shell in this build is a straight prism on its footprint, so a bay window is a flat wall wherever it occurs.

**The trees are the scene's largest expense and none was cut.** 2,334 props placed with **nothing dropped for budget**, of which **1,901 are trees** — 53 drawn from modelled branches within 120 m and 1,848 as six-triangle impostor cards out to 720 m. **710 had their species substituted**, 37 per cent, just under the pass-wide 39.19 per cent (J108).

**Structures are complete here**: 5 tiles, **none without a file**, **83,736 triangles** — the 7 train's Roosevelt Avenue elevated and its neighbours, correctly present for Woodside.

**No park ground at all**: 0 meshes and 0 surfaces, with 5 tiles in the 720 m radius carrying no park-ground file.

**And every agent is at its lowest detail.** All **88 vehicles** and all **443 pedestrians** are LOD2, with no LOD0 or LOD1 anywhere in the frame, which is unusual: most sheets carry a handful of near agents at higher detail. The one figure crossing in the foreground of the render is therefore the simplest body the fleet exports.

## What matches

* **The street type is right**: a low-rise two-family block with parapets, stoops and entrance doors at a consistent rhythm.
* **The trees are bare**, correct for 9 April by the build's own rule, and none was dropped for budget.
* **Structures complete**: 5 tiles, none without a file, 83,736 triangles.
* **Building tiles complete**: 5 of 5, 285,636 triangles, none missing, none LOD-substituted.
* **The pavement is complete**: 24,076 polygons with 11,559 white markings, 704 parking lot and 656 crosswalk, none dropped.
* **Nothing dropped from the props budget**, 2,334 placed.
* **The development is small and honest**: 0.950 stops, one of the least corrected frames in the pass.
* **The record states its own limits**: no subject, a low-confidence heading, a reference five kilometres away, and the instruction to compare fabric rather than composition.

## What does not match

* **No vinyl siding in either half**, on the sheet named for it.
* **Five kilometres between the two blocks** — Ridgewood against Woodside — the largest such gap for any place-naming item in the pass.
* **The cherry is in bloom and this build has no blossom state**; the canopy is bare or in leaf and nothing else (J108).
* **No rounded bay fronts**: every shell is a straight prism on its footprint, and the bay is the photograph's defining form.
* **No awnings, no flag, no wheelie bins, no stoop rails** — the objects that make the reference a lived-in street.
* **1.233 stops brighter with a p50 ratio of 1.499**, because the reference is a shaded canyon of dark brick and the render is an open corner under a clear sky.
* **Chroma 0.641**: two thirds of the photograph's colour.
* **No park ground**: 0 meshes and 0 surfaces over 5 tiles with no file.
* **No signage of any kind** (J110), and the photograph carries a parking sign, a street-name blade and a one-way sign at its left edge.
* **Every agent at LOD2**, so the one figure near the camera is the coarsest body in the fleet.
* **The clearance note and its own fields name different nearest agents**, 3.4 m against 13.2 m; the note is what the sheet prints (J117).

## Measured for this assessment

| figure | where it comes from |
|---|---|
| 5,176 m is the largest gap between a rejected photograph GPS and the viewpoint used, among items that name a place | the `camera_origin.offset_from_recorded_m` of every record whose `from_photograph_gps` is false, excluding the ten showcase items that name an object type rather than a location |
| the canopy has two appearances per species and no bloom state, and Prunus is the fourth commonest genus at 41,653 trees with no asset | DEVIATIONS J108, whose measurement this is |
| 39.19 per cent of the trees drawn across the pass had their species substituted | DEVIATIONS J108, whose measurement this is |
| 5,457 kit pieces | the sum of the record's `scene.kit.per_category`, whose `total` is null |
| there is no bay-front or curved-wall piece in the kit, and every building shell is a straight prism on its footprint | the categories of `data/processed/kit_catalog.json` against the shell builder's own massing |
| 9 April is inside the leaf-off window | the `leaf_off` rule in `blender/verify/render_sheets.py` (J97) |

## Cause of each gap

| gap | cause | class |
|---|---|---|
| no vinyl siding in either half | the fetch returned a Ridgewood brick row for a Woodside vinyl item and nothing tests what a photograph is a picture of (J71) | **verification — open** |
| five kilometres between the blocks | the distance band applies only to the drive-through group, so a streetscape item takes the best-lit, best-clocked photograph wherever it was taken (J60, measured in J112) | **verification — declared for this group, and at its widest here** |
| no cherry blossom | the canopy is ten species with two appearances each, in leaf and out of it, and no flowering state exists (J108) | content — open |
| no rounded bay fronts | building shells are straight prisms extruded on their footprints; there is no curved-wall or bay piece in the kit | content — declared, and the limit of the massing |
| no awnings, flags, bins or stoop rails | the props catalogue has 34 kinds and only 20 appear anywhere in the pass; none of these four is among them (J110's family) | content — open |
| 1.233 stops brighter, chroma 0.641 | a shaded brick canyon under a canopy against an open corner under a clear procedural sky | reference — the pairing, not the render |
| no park ground | 5 tiles in range carry no park-ground file | data — open |
| no signage | the verification renderer never reads the sign or signal export (J110) | **verification — open** |
| the note and the fields disagree about the nearest agent | the fields are measured after the cull of agents over the observer and the note is written before it (J117) | **verification — open** |
