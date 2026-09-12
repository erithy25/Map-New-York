# Williamsburgh Savings Bank Tower (One Hanson Place)

`landmark_williamsburgh_savings_bank_tower` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Williamsburgh Savings Bank Tower January 2023.jpg by Kidfly182, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2023-01-20 12:51:39, 1920x1440. [Commons page](https://commons.wikimedia.org/wiki/File:Williamsburgh_Savings_Bank_Tower_January_2023.jpg) — the photograph carries camera GPS and its viewpoint confidence is **high**, and the fetch record states where that GPS is: *"126 m from Williamsburgh Savings Bank Tower (One Hanson Place) … and 304 m from the standard viewpoint; the azimuth 244 deg is the initial great-circle bearing from that camera position to the subject."* A steep upward view of the crown from close in on a flat, sunless January noon: bare branches across the top left, the 8.2 m dial with its chapter ring and two hands, the arcaded belvedere storey above it, the ribbed dome on its drum, and antenna masts against a white sky.

**Camera** — 40.683866, -73.978589 (NYC_TM -2415, -1792) at z 14.579 m NAVD88, a 1.6 m standing eye over terrain read at 12.979 m (the 10th percentile of 113 samples within 12.0 m) | azimuth 20.0°, pitch +4.9° | 18 mm on 36 mm (90.0° horizontal) | 1208x906. The camera stands on the item's recorded viewpoint, Flatbush Avenue at Fourth Avenue, because the chosen photograph's own GPS is **303.9 m** away, past the 250 m at which it could still be the same view. The azimuth is the recorded 20.0° and agrees with the bearing to the subject to 0.1°. The lens went to the **18 mm floor** and the axis was tilted up **+4.9°** to hold a crown that stands 37° above the horizon at 200 m, and the record refuses to pretend that worked: *"the verticals converge, so this frame is not comparable with the photograph on proportion — it is here to show the subject at all."*

**Sun** — azimuth 192.0°, elevation 28.4° at 2023-01-20T12:51:39-05:00, from the photograph's own EXIF DateTimeOriginal; 755 W/m² direct normal, Nishita sky, Filmic, **+2.97 stops**. Metered: **2.967 stops** on a linear median of **0.023016**, against a physical rule of 0.6 — under the +4 threshold, so this frame is not declared under-lit. With the Sun at 192.0° and the view at 20.0°, the light comes over the photographer's shoulder and the tower's south-west elevation is fully lit.

## Verdict — the sheet shows the wrong side of the building, and the clock faces lie flat

**The two halves are of different elevations of the same tower.** The photograph was taken 126 m from the tower on the north-east side, looking back at it on bearing **244 deg**; the render stands 200 m away on the south-south-west side looking at it on **20.0°**. The record knows this — it carries the photograph's own estimated view direction as **243.9°** — and renders 20.0° anyway, because the azimuth used is the *item's* and the rule that rejected the photograph's GPS does not also reject the pairing.

**Two better photographs were in the same folder and were passed over for a clock.** The fetch kept three. Candidates 1 and 3 are both *"10 m from the standard viewpoint"* with *"the azimuth 19 deg"* — a metre-scale match to where this camera stands and a 1° match to where it looks — and both carry a fetch score of **12.6**. The chosen photograph scores **10.2** and is 304 m and 244 deg. It won on one term: its `date_taken` is `2023-01-20 12:51:39` and theirs is `2019`, so only it satisfies `has_time` in `pick_reference_photo`'s key, which for every group but `drive_through` ranks the clock **above** the viewpoint confidence and the azimuth error and has no distance term at all. J60 made that a stated judgement — *"a landmark is legitimately photographed from 1.8 km"* — and this sheet is what the judgement costs when the alternative is ten metres away. Across the pass it costs **thirteen sheets**, and this one is the worst of them on both axes.

**The clock faces are horizontal.** The builder makes each 8.2 m dial with `b.lathe(...)`, and `lathe` is documented as a *"surface of revolution about a vertical axis"*. So the dial is not a disc standing in the wall facing the street; it is a **flat 8.2 m plate 0.35 m thick lying flat**, pushed 0.3 m out of the elevation, and that is exactly what the render shows: two grey mushroom caps cantilevered off the crown where the photograph has two dials. The twelve gold hour marks and the two bronze hands *are* placed correctly, in a vertical ring in the plane of the wall — so the dial and everything written on it stand in perpendicular planes.

**And the hands read a time no clock can show.** They are two boxes at fixed angles, 1.0 and 2.4 radians off the face's tangent, so every dial on every render of this building shows the same instant whatever hour the sheet is lit at. That instant is not a time: the long hand stands **32.7 deg** from twelve, which is 5.45 minutes past the hour, and at 5.45 minutes past, a real hour hand must sit at 302.7 deg (ten o'clock) or 332.7 deg (eleven). This one sits at **312.5 deg**, **9.8 deg** from the nearer of the two. The photograph's dial, by contrast, reads a real time consistent with its own timestamp.

**The crown is a slab where the building has a campanile.** The three setbacks inset the shaft by only 1.4, 3.6 and 5.8 m from a 34.8 x 62.3 m footprint, so the clock storey is still **19.06 x 47.78 m** — a 48 m long box carrying one 8.2 m dial per elevation, which on the long faces is a dial covering a sixth of its own wall. The photograph shows a slender square tower with corner buttresses. The builder declares the setbacks inferred, and this is what the inference produced.

**The 156 m height, though, is right to within a metre.** The probe put **43 of 43 rays** on built fabric and measured **155.04 m** above a ground of 12.24 m, against a catalogued **156.0 m** from an entry **6.8 m** away — inside the 120 m radius, so J74 took the measurement, and the measurement and the catalogue agree to within a metre. The model is 41,846 triangles over 19 mesh nodes, of which the scene drew 40,930.

**The sightline says 0.154 and the picture shows the whole tower.** Two mechanisms, both measurable, both new. First, the object standing at the subject's coordinate is `lm_c_williamsburgh_savings_bank_tower.8`, which is the **gilded dome** — 14.38 m across — so the fan took **14.4 m** as the subject's width and set its half-angle at **1.93°**. The building itself presents **54.0 m** of width at this bearing, subtending 14.4°, so the fan is a quarter as wide as the thing it is testing. Second, into that 3.86°-wide slot the walk put a street lamp. The rule *"sidestep around a prop at the lens"* fired because *"prop_lamp_cobra_davit_0 stands 4.6 m from the lens on the line to the subject"*, moved the camera **2.0 m** to the right — and after the move the same lamp is the nearest obstruction at **4.4 m**, twenty centimetres *nearer* than before, and still what blocks the subject. Its pole is 0.216 m across flats and tapers to about 0.16 m at the heights these rays pass through, which at 4.4 m subtends roughly 2.5°: **wider than two thirds of the fan.** Eleven of thirteen rays die on a lamp post, and the frame contains the entire building.

**Everything else in the block is complete.** Six of six building tiles built, none missing and none LOD-substituted; 25,964 pavement polygons with none dropped; 3,176 props with none dropped for budget; 5,428 kit pieces; 88,200 triangles of terrain with no holes. This is one of the better-served scenes in the pass, and its problems are all in the two things it exists to compare.

## What matches

* **The height, measured and catalogued, agree to under a metre**: 155.04 m from 43 of 43 probe rays against a catalogued 156.0 m.
* **The tower is in the frame, whole, from base to lantern**, which is what the lens floor and the +4.9° tilt were spent on.
* **The trees are bare**, correct for 20 January, and 2,578 of the 3,176 props are trees.
* **The banking hall's arched base is modelled and reads as an arcade** at 200 m.
* **The tan brick shaft with its terracotta band courses** reads as buff brick against the photograph's Ohio sandstone and buff brick.
* **The scene is complete**: 6 building tiles, 0 missing, 0 LOD-substituted, 0 pavement polygons dropped, 0 props dropped for budget, 0 terrain holes.
* **Barclays Center stands in the same frame** at 315.0 m, 7,058 triangles, where it belongs on Flatbush Avenue.
* **The record states its own limits before this assessment does**: the converging verticals, the rejected GPS, and the lamp on the line.

## What does not match

* **The photograph is of the north-east elevation and the render is of the south-south-west one**, 243.9° against 20.0°.
* **The chooser had a photograph 10 m from this camera aimed 19 deg and took one 304 m away aimed 244 deg**, because only the far one carries a clock; the near ones score 12.6 against 10.2.
* **The clock faces lie flat**, 8.2 m plates revolved about a vertical axis, while their hour marks and hands stand upright in the wall.
* **The hands are frozen at an impossible reading**, 9.8 deg from any valid hour-and-minute pair, on every render of this building.
* **The crown is a 19.06 x 47.78 m slab**, so the dial covers a sixth of the long elevation where the photograph shows it covering most of a square tower face.
* **The belvedere storey is a solid prism.** The photograph's crown has an open arcade of tall arched openings under the dome; the model has 20 triangles of blank limestone from 125.00 to 138.00 m.
* **The dome is smooth and gold on a white sky-lit day**; the photograph's is ribbed, brown-weathered, set on a drum ringed with small arched dormers, and carries antenna masts the model does not have.
* **The sightline publishes 0.154 on a frame that contains the whole building**, because the fan is 14.4 m wide and a lamp post fills two thirds of it.
* **The sidestep moved 2.0 m and ended 0.2 m nearer the lamp it moved to avoid.**
* **The reference is a flat overcast January noon and the render is a clear blue sky with hard sun**: chroma 1.651×, contrast 0.805×, the render darker overall at p50 0.594×.
* **Nothing in the foreground.** The nearest 45 % of the frame is bare asphalt and bare concrete with no marking, no manhole, no hydrant and no sign in it, though the scene holds 10,533 white markings, 99 manholes and 60 hydrants further out.
* **No traffic signal, stop sign or street-name blade at Flatbush and Fourth**, as on every sheet in the pass (J110).
* **Seven yellow cabs to one green boro taxi in Brooklyn** (J105).
* **Five of six structures tiles have no file**, so the LIRR yard and terminal fabric behind the tower is 14,212 triangles from a single tile.

## Measured for this assessment

| figure | where it comes from |
|---|---|
| 41,846 triangles over 19 mesh nodes, of which the LOD1 is 916 and the scene drew 40,930 | node-by-node accessor bounds of `blender_out/landmarks/c_williamsburgh_savings_bank_tower.glb`, honouring each node's translation; the scene figure is the record's own |
| the clock object is 1,776 triangles running z 124.32 to 131.68 m, and the clock storey is 19.06 by 47.78 m from z 125.00 to 138.00 m | the same node measurement, against the builder's `clock` and `clock_storey` objects |
| the dome is 14.38 m across and runs z 138.00 to 156.00 m, which is the 14.4 m the fan took as the subject's width | the same node measurement; the object the height probe names is `lm_c_williamsburgh_savings_bank_tower.8` |
| the shaft setbacks inset 1.4, 3.6 and 5.8 m from a 34.8 by 62.3 m footprint | the `tiers` list in `blender/landmarks/c_williamsburgh_savings_bank_tower.py` and the bounds in `blender_out/landmarks/catalog/c_williamsburgh_savings_bank_tower.json` |
| each dial is an 8.2 m plate 0.35 m thick revolved about a vertical axis, with twelve gold hour marks and two bronze hands placed in the wall plane | the clock block of the builder against the docstring of `MeshBuilder.lathe` in `blender/landmarks/common.py`, which reads "surface of revolution about a vertical axis" |
| the hands stand 32.7 deg and 47.5 deg off vertical, giving 5.45 minutes past the hour and an hour hand at 312.5 deg where a real dial needs 302.7 or 332.7 deg, 9.8 deg away | the two fixed angles 1.0 and 2.4 radians in the builder, converted and compared against the hour-hand position a real movement puts at that minute |
| the pole is 0.216 m across flats at its base, tapering to about 0.16 m over the heights these rays cross, subtending roughly 2.5 deg at 4.4 m against a fan 3.86 deg wide | the `key_dims_m` and sweep profile of `build_cobra_davit` in `blender/props/p_lighting.py`, against the record's own fan half-angle and obstruction distance |
| the building presents 54.0 m of width at this bearing, subtending 14.4 deg at the range the record gives | the catalogue's 34.8 by 62.3 m bounds projected onto the axis perpendicular to a 20.0 deg view |
| the sidestep rule fired twice in the whole pass and both times ended nearer the lamp: Trinity Church 4.1 to 3.3 m after a 1.5 m step, this tower 4.6 to 4.4 m after a 2.0 m step, both still blocked by it | every `clearance.rule` in the 171 records of the pass, read against each record's `sightline.subject_blocked_by` |
| eight records in the pass are blocked by a prop within 10 m of the lens, five of them by a cobra-head lamp | the `sightline.subject_blocked_by` and `subject_blocked_at_m` of all 171 records |
| five records measure a fan 25 m or narrower across a subject 100 m or taller, and four of those are at the 12 m floor rather than a measured extent | the `sightline.subject_fan_m` and `subject_fan_tall_m` of all 118 records that carry a fan |
| thirteen of the 162 non-drive sheets took a photograph with a full clock over a candidate at least 50 m nearer and at least 10 deg better aimed, seven of them over a candidate with the higher fetch score; median 164 m and 108.6 deg given up, worst 901 m and 163.8 deg | every `docs/verification/reference/*/meta.json` against the `reference_photo.file` its render used, scoring each kept candidate's GPS offset from the item's viewpoint and its azimuth error, excluding the drive-through group that J60 already gates |
| nineteen of those 162 use a photograph whose own estimated view direction is more than 90 deg from the item's | the `estimated_viewpoint.azimuth_deg` of each chosen photograph against its item's recorded azimuth |
| 20 January is inside the leaf-off window | the `leaf_off` rule in `blender/verify/render_sheets.py` (J97) |

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the photograph shows the opposite elevation | `pick_reference_photo` ranks a full EXIF clock above viewpoint confidence and azimuth error and carries no distance term outside the drive-through group; two candidates 10 m away were passed over (J60's stated judgement, measured here across thirteen sheets) | **verification — open** |
| the clock faces lie flat | `lathe` revolves about a vertical axis and the builder used it for a wall-mounted dial; the hour marks and hands beside it are placed correctly, which is why the error survived review | **content — open, and a one-line fix** |
| the hands read an impossible time | two hand angles are hard-coded at 1.0 and 2.4 radians rather than derived from an hour | content — open |
| the crown is a slab | the setbacks are inferred from the published total height and floor count rather than measured, and the inference kept 48 m of the base footprint at the top; the builder declares them inferred | content — declared, and worth a source |
| the belvedere arcade and the dome's ribs, drum dormers and masts are absent | the crown is a prism plus two lathes; no source for the arcade's bay rhythm was used | content — open |
| the sightline reads 0.154 on a visible building | the fan's width is the plan extent of whatever object stands at the subject's coordinate, which here is the dome, a quarter of the building's apparent width (the mirror of J94's tile meshes) | **verification — open** |
| the sidestep ended nearer the lamp | the rule tests one line at eye level and steps to the nearest open point without re-testing the prop it moved for; it fired twice in the pass and failed twice | **verification — open** |
| a clear blue sky against a solid overcast | nothing in this build reads a historical sky, and the snapshot request carries no weather at all (J97) | reference — no source exists |
| no signage of any kind | the verification renderer never reads the sign or signal export, and its props catalogue has no kind for either (J110) | **verification — open** |
| seven yellow cabs to one boro taxi in Brooklyn | `TrafficSim::sampleClass` splits the taxi share 70/30 with no geography, so the exclusion zone is inverted (J105) | **runtime — open** |
| five of six structures tiles have no file | the B13 remainder; nineteen sheets in the pass report the same shape | data — open |
