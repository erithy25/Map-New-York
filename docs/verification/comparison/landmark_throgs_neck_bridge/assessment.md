# Throgs Neck Bridge

`landmark_throgs_neck_bridge` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:MTA Bridges & Tunnels, NYPD, Law Enforcement Partners Interagency Taskforce Enforcement at George Washington & Throgs Neck Bridges 4-19-24 (53668714208).jpg by the Metropolitan Transportation Authority, CC BY 2.0 (https://creativecommons.org/licenses/by/2.0), taken 2024-04-19 17:37, 1920x1440. [Commons page](https://commons.wikimedia.org/wiki/File:MTA_Bridges_%26_Tunnels,_NYPD,_Law_Enforcement_Partners_Interagency_Taskforce_Enforcement_at_George_Washington_%26_Throgs_Neck_Bridges_4-19-24_(53668714208).jpg) — the photograph's own view direction is derived from the image at **high** confidence, which on this pairing is beside the point. **The photograph is of an arrest.** Two officers, one in a TBTA Special Operations Division jacket, are handcuffing a third person behind a Cadillac Escalade with a New Jersey plate. There is no bridge in it, no water, no tower, no cable — the frame is three people and a car tailgate at close range.

**Camera** — 40.793849, -73.798021 (NYC_TM 12860, 10444) at z 7.9 m NAVD88 | azimuth 21.0°, pitch 0.0° | 35 mm on 36 mm (54.4° horizontal, landscape) | 1208x906. The camera stands on **the item's recorded viewpoint** — Little Bay Park's shoreline in Bayside — because the photograph's own EXIF GPS is **955.2 m** away, far past the 250 m at which it could be the same view. The recorded azimuth agrees with the bearing to the subject to **0.0°**. The walk then **moved it 34.6 m** onto the nearest surveyed crosswalk polygon, the recorded viewpoint being boxed in at **46 m** against the **80.0 m** the frame needs. From there the view is clear for **96.0 m**, the nearest built thing is a littleleaf linden **14.9 m** away, and the note records a black car **2.3 m** from the lens, which the cull over the observer then removed. The ground reads 6.287 m NAVD88 from the 2 m heightmap, 16 samples within 5 m, range 6.04 to 6.54 m.

**Sun** — azimuth 266.3°, elevation 22.1° at 2024-04-19T17:37:00−04:00, from the photograph's own **EXIF DateTimeOriginal** to the minute; 683.4 W/m² direct normal, sky at strength 0.0394, Filmic, **+2.32 stops** metered and unclamped against a linear median of **0.036011** and a target of **0.18**. The physical rule would have given **0.97 stops**.

**In the scene** — 1,516,782 triangles: **20 building tiles** (371,182 tris, **3 missing**, **3 LOD-substituted**), 1 landmark model, in cone at **4.5° off axis**, 12,813 pavement polygons, 5,873 props, 1,342 kit pieces, 4 park-ground meshes, 31,264 triangles of structures, 31 vehicles and 39 people.

## Verdict — the render shows the bridge and the reference shows an arrest

**The bridge is in the render and it is recognisable.** Across the middle distance the suspension span runs from tower to tower with its cable sag and deck line, a kilometre out over Little Neck Bay, with a brick building at the left, a linden at the right and a crosswalk in the near foreground. The probe found fabric on **43 of 43 rays** and measured **99.16 m** above a ground of **0.0 m** — the tidal datum, correct for a tower footing over water — against the catalogue's **105.5 m** for `b_throgs_neck`, whose origin stands **264.4 m** away and therefore past the 120 m the old rule looked in, so the height came from the geometry (J74). Ten of thirteen rays are clear, **seven land on the subject** at **989.6 m**, three pass into open sky, and the visible fraction is **0.538**. The tone agrees closely too: mean **1.097**, p50 **1.089**, and the photograph's own median sitting **0.018 stops** from the grey convention, a **+0.265-stop** difference.

**And the reference cannot be compared, on two counts.** It is not a photograph of the subject: its filename says it is enforcement activity at two bridges, and its frame is three people and a car. And it depicts **identifiable individuals in a law-enforcement action**, one of them being handcuffed, which a published comparison sheet embeds in full. The measured ratios above are therefore statistics across a bridge view and an arrest, and they happen to look good, which is the clearest possible demonstration that a tonal match is not a fidelity result. This pairing should be replaced — the chooser has other MTA photographs of this bridge to draw on, and nothing about verification is served by embedding this one.

**The probe measured one linear member, and the record's own extent says so.** `lm_b_throgs_neck.35` is **887.1 m by 1.5 m** in plan. That is a cable or a stiffening chord, not a structure, and the sheet's plan extent is therefore not a footprint. The record does not flag it the way it flags a tile mesh, and it should: a 1.5 m narrow dimension is a member, and any reader comparing extents needs to know that (J94's neighbour).

**Two build gaps this sheet exposes.** **Three of twenty building tiles have no shells** (`t_13_12`, `t_14_11`, `t_14_12`), and **three more were drawn at the wrong level of detail** — `t_10_11`, `t_10_9` and `t_14_8` had no mesh at the LOD their distance asks for and fell back from LOD2 to LOD1. This is the first sheet in the pass to report a LOD substitution at all, and the record names each tile. **Ten of thirteen structure tiles have no file.** And **no park ground was built for six tiles** in the 900 m radius (J102).

## What matches

* **The bridge reads as the bridge** — tower spacing, cable sag and deck line at a kilometre.
* **The height** — 99.16 m on **43 of 43** rays above a tidal datum of 0.0 m, against a catalogued 105.5 m taken from the geometry rather than the catalogue (J74).
* **The aim** — the recorded azimuth agrees with the measured bearing to **0.0°**, and the frustum puts the subject **4.5° off axis** at 779.9 m.
* **The tone** — mean 1.097, p50 1.089, and the reference's own median **0.018 stops** from the grey convention, the closest any reference in the pass sits to it.
* **Nothing was capped** — props **5,873 of 5,891 in range**, kit **1,342 of 1,342**, **0 dropped for budget**.
* **The shoreline is named in the terrain** — seven water bodies in range: the East River, Fort Totten Lake, Little Neck Bay, Long Island Sound, a marsh, a pond and a river.
* **12,813 pavement polygons and none dropped**, including **2,130 parking-lot** polygons, which is what Bayside's waterfront is.
* **The record names every substituted tile and every missing one**, rather than drawing them silently.

## What does not match

* **The reference is a photograph of an arrest**, not of the bridge, and it shows identifiable people in a law-enforcement action.
* **The published ratios compare a bridge view with that photograph** and look good, which means nothing.
* **The plan extent is a single member** — 887.1 m by 1.5 m — and the record does not flag it as unusable the way it flags a tile mesh.
* **Three of twenty building tiles have no shells**, and **three more fell back from LOD2 to LOD1** for want of a mesh at the required level — the first LOD substitution reported in the pass.
* **Ten of thirteen structure tiles have no file**, with **31,264 triangles** drawn from the three that do.
* **No park ground was built for six tiles** in range, and the scene carries only **4 meshes over 11 surfaces** (J102).
* **2,030 of the 5,810 trees are a substituted species** and **21 are scaled outside the allowed band** — the highest out-of-band count on any sheet written so far — at a mean scale of **0.88**. **1,861** of the 5,780 impostor cards are procedural canopy stems (Stage 55).
* **Two thirds of the photograph's colour** — chroma **0.663** — and **0.866** of its contrast, both meaningless across this pairing.
* **The z-fighting fraction is 0.0484** over 1,633 park-ground samples, the highest on any sheet written so far, with an under-fraction of **0.1623**; every sample falls beyond 400 m.
* **Thirty-nine people and thirty-one vehicles** — this is a low-density outer-borough frame, and 354 agents were dropped, 14 of them in the carriageway without crossing and 4 where the planimetric data has no sidewalk.
* **No cloud.** The reference's sky is barely in frame; nothing in this build reads a historical sky.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the reference is a photograph of an arrest | the chooser selected an MTA enforcement photograph whose title names the bridge; nothing tests whether the frame contains the subject, and nothing tests whether a reference is appropriate to embed | **verification — open, and this pairing should be replaced** |
| the plan extent is 887.1 m by 1.5 m | the probe measured one linear member of the bridge; the record flags a tile mesh's extent as unusable and has no equivalent flag for a member this slender (J94) | **verification — open, a missing flag** |
| three tiles with no shells, three drawn at the wrong LOD | those tiles are unbuilt or have no mesh at the level their distance asks for; the record names each | **data — open, and honestly reported** |
| ten of thirteen structure tiles without a file | those tiles are unbuilt | data — open |
| no park ground for six tiles | 85 % of the city's mapped open space was never draped (J102) | data — open (J102) |
| 2,030 substituted species, 21 out of band, 1,861 procedural stems | the species lists do not cover Bayside's stock and woodland polygons are filled by rule (Stage 55) | data — declared, counted |
| chroma 0.663, sd 0.866 | statistics across two unrelated images | reference — void here |
| a z-fighting fraction of 0.0484 | the park builder drapes on its own heightmap and the scene's coarsens to 40 m at this distance; every sample on this sheet is beyond 400 m (J71) | geometry — open, bounded |
| 39 people in the frame | a low-density outer-borough neighbourhood, correctly reflected, plus the placement rules' own counts | verification — correct |
| no cloud | nothing in this build reads a historical sky | reference — no source exists |
