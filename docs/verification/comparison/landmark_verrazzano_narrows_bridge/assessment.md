# Verrazzano-Narrows Bridge

`landmark_verrazzano_narrows_bridge` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:I-278 wb HOV lane at start of Verrazzano Bridge, Brooklyn, July 2025.jpg by Mr. Matté, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2025-07-09 15:17:06, 1920x1446. [Commons page](https://commons.wikimedia.org/wiki/File:I-278_wb_HOV_lane_at_start_of_Verrazzano_Bridge,_Brooklyn,_July_2025.jpg) — the photograph is exactly what its title says: the westbound HOV lane of the Staten Island Expressway approach, between concrete barriers, under two overhead sign gantries, with a cobra-head lamp standard, traffic in the adjacent lanes and a July sky full of cumulus. **The bridge is not in it.**

**Camera** — 40.614, -74.0372 (NYC_TM -7379, -9546) at z 22.8 m NAVD88 | azimuth 222.1°, pitch 0.0° | 35 mm on 36 mm (54.4° horizontal) | 1204x906. The camera stands on the item's recorded viewpoint — the Shore Parkway greenway near 92nd Street — and the record refuses the photograph's own fix with the careful wording it uses for this case: the EXIF GPS is **929.7 m** away, *"past the 250 m at which it could still be the same view, so the camera was not stood on it. That is a statement about this pairing and not about the photograph: a fix this far out is usually correct and simply of somewhere else."* The heading agrees with the bearing to the subject to **0.1°**. It was **not moved**: view azimuth clear for **150.0 m** against an 80.0 m requirement, no simulated agent within 60 m, nearest built thing `prop_tree_honeylocust_medium_1` **9.2 m** away. The axis is level: *"the subject is 1109 m away; anything that far is photographed with a level camera"*.

**Sun** — azimuth 247.6°, elevation **56.1°** at 2025-07-09T15:17:06−04:00, from the photograph's own **EXIF DateTimeOriginal**; 908.1 W/m² direct normal, sky at strength 0.0314, Filmic, **+0.04 stops**. The linear frame's median is **0.174622** against the 0.18 target, so the metered development is **0.044 stops** — the **second-smallest of the 169 metered frames in the pass**, after Top of the Rock. The physical rule would have given 0.0. A July afternoon over open water arrives at a photographable level on its own.

**In the scene** — 1,829,633 triangles: 18 of 23 building tiles (541,056 tris) with **5 not built and 2 substituted by a lower LOD**, 1 landmark model, 15,823 pavement polygons, 3,661 props with **nothing dropped for budget**, 926 kit pieces, **0 park-ground meshes and 0 surfaces**, **13 tiles of structures (12,204 tris) with 10 having no file**, 8 vehicles and 75 people. The water table names 14 bodies, with 24,069 quads on the flattened surface.

## Verdict — the render is a good picture of the bridge and the photograph is a picture of a highway lane, and the instrument measured nothing at all

**The render contains its subject and reads well.** The suspension span crosses the frame with its deck, both towers and the sag of the main cables, seen across the Narrows from the Bay Ridge shore, with a tree in the near right, the greenway's concrete parapet across the middle distance and the water beyond. A reader looking at the right half alone would name the bridge.

**The left half is the approach roadway.** The chooser kept a photograph of the I-278 HOV lane: concrete barriers, sign gantries, a lamp standard and traffic. Nothing about the span's proportions, its tower form, its cable geometry or its deck depth can be compared, because none of it is in the reference. This is J71's family — `pick_reference_photo` tests licence, size, date, the Sun's height and a derivable heading, and nothing tests what a photograph is a picture of — and it is the reverse of the usual failure: **here the render is the better evidence of the two halves.**

**And the instrument found nothing.** The height probe cast 43 rays and **0 landed on built fabric**. The record says why: *"nothing built stands within 6 m of the subject's coordinate"*, so **no sightline was tested** — there is no visible fraction, no ray count and no verdict on this record. The catalogue entry sits **55.5 m** from the coordinate and carries **211.2 m**, the towers' own height, and it was not used. So a sheet whose picture is dominated by its subject publishes no measurement of it, which is the exact mirror of the Chrysler sheet, where the record measured the building with 43 of 43 rays and then declared it absent.

**The subject's ground is the tidal datum.** `probe.ground_z_m` is **0.0**, because every tidal water body in this build is flattened to 0.0 m NAVD88 (J103). The Narrows is 0.0 m and the bridge's towers stand in it.

**Two data gaps on this sheet are large and both are about what was never built.** **Five of the twenty-three building tiles in range have no shell file at all** and two more were drawn at a lower LOD than their distance asks, so part of Bay Ridge and the Staten Island shore is simply missing. And the park-ground count is **0 meshes and 0 surfaces**: the record also names **nine tiles in the 900 m ground radius with no park ground built**, which on a viewpoint inside Shore Road Park means the park the camera stands in has no ground geometry of its own (J102). What the render's foreground shows instead is bare terrain wearing the roadway's own materials.

**The tone is the largest gap here and it is exposure plus colour.** The photograph sits **1.056 stops above** the grey convention — a bright July frame — and the render is metered to 0.240 above it, a **−0.816-stop** gap, so mean reads 0.779× and p50 0.772×. The render carries **0.233** of the photograph's chroma and **0.614** of its contrast, which is a hazy procedural sky and a flat specular water plane against real cumulus over a real channel.

## What matches

* **The bridge is modelled and legible**: deck, both towers and the cable sag across a 1.1 km span, from a single landmark model in a 1.8-million-triangle scene.
* **The development is the second-smallest of the 169 metered frames**: 0.044 stops on a linear median of 0.174622, so the frame is published essentially as the scene arrived.
* **The heading agrees with the bearing to the subject to 0.1°**, from the item's own recorded viewpoint.
* **The reference chooser refused a 929.7 m fix and argued the refusal** in terms that separate the pairing from the photograph.
* **Nothing was dropped for the props budget**: 3,661 placed, of which **3,604 are trees** — **54 of them drawn from modelled branches** — and the Shore Road planting is what the render's foreground and right edge carry.
* **The axis is level and the reason is stated**: at 1,109 m a subject is photographed with a level camera.
* **Eight vehicles and 75 people is defensible** on a greenway beside the Belt Parkway: only 288 vehicles and 661 pedestrians were dropped for being outside the radius, and 41 for not standing on a walkable surface.
* **The water is comprehensive as a surface**: 14 named bodies and 24,069 quads on the flattened plane.

## What does not match

* **The reference is a photograph of a highway lane, not of the bridge** (J71).
* **The instrument measured nothing**: 0 of 43 probe rays on fabric, no height, no sightline, no verdict, with a catalogue entry carrying 211.2 m 55.5 m away and unused.
* **The subject's ground is 0.0 m NAVD88**, the tidal datum (J103).
* **Five of twenty-three building tiles were never built**, and two more were drawn at a lower LOD than their distance asks.
* **There is no park ground at all**: 0 meshes, 0 surfaces, and nine tiles in the 900 m radius with none built, on a viewpoint inside a park (J102).
* **The water is a mirror.** Open water is a flat specular plane with no wave state and no turbidity (J103), so the Narrows reflects the span cleanly where a July channel is choppy.
* **Chroma 0.233 and contrast 0.614**, the render carrying under a quarter of the photograph's colour and under two thirds of its range.
* **A −0.816-stop exposure gap**, so mean reads 0.779× and p50 0.772× (J83).
* **No cloud.** The reference's sky is half cumulus and is most of its picture; the render's is a hazy Nishita dome at strength 0.0314 that pales toward the horizon.
* **Ten of the thirteen structures tiles have no file**, and what came in is 12,204 triangles.
* **The kit is thin**: 926 pieces, of which 687 windows against **5 cornices**, 48 parapets and 16 string courses — Bay Ridge's row houses are cornice-and-stoop buildings.
* **Only 3,550 of the 3,604 trees are cards** rather than branches, and 202 of the cards are procedural canopy stems placed by rule inside mapped woodland rather than surveyed positions (J86's closure working, and still inferred).

## Measured for this assessment

| figure | where it comes from |
|---|---|
| the second-smallest metered development of the 169 metered frames | ranked over every record whose `lighting.development.metered` is true, on the absolute value of `stops`; Top of the Rock's -0.021 is smaller and this sheet's +0.044 is next |
| 211.2 m is the towers' own height | the record's own `nearest_catalogue_origin.height_m` for the `b_verrazzano_narrows` entry 55.5 m from the subject's coordinate |
| nine tiles in the 900 m radius have no park ground built | the record's own gaps line, which names them |
| 5 of 23 building tiles were never built and 2 were LOD-substituted | the record's `scene.buildings.missing` and `lod_substituted` lists |

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the reference is a photograph of a highway lane | `pick_reference_photo` ranks licence, size, date, the Sun's height and a derivable heading, and nothing tests what a photograph is a picture of (J71) | **verification — open; here it makes the render the better half** |
| 0 of 43 probe rays on fabric, and no sightline | the item's subject coordinate stands more than 6 m from any bridge geometry, so the probe correctly returns nothing and the sightline is not tested; the catalogue's 211.2 m was 55.5 m away and unused (J72, J74) | **verification — open; the coordinate needs correcting, and the model is 1.1 km of geometry that would answer** |
| the subject's ground is the tidal datum | every tidal water body is flattened to 0.0 m NAVD88 (J103) | declared decision |
| 5 building tiles never built, 2 at a lower LOD | those tiles have no shell file; the LOD substitution is the streaming rule working at this range | data + performance |
| no park ground at all, on a viewpoint inside a park | 85 per cent of the city's mapped open space has no ground geometry, and nine tiles here are among it (J102) | **data — open** |
| the water is a mirror | open water is a flat specular plane with no wave state or turbidity (J103) | declared decision |
| chroma 0.233, contrast 0.614, and 0.816 stops of exposure difference | a hazy procedural sky and a flat water plane against real cumulus, and a photograph developed 1.056 stops above the grey convention (J83) | **reference — no source exists for the sky** |
| 10 of 13 structures tiles have no file | those tiles were not built (B13 remainder) | data — open |
| 5 cornices drawn | 926 kit pieces in a scene whose triangles went to 18 building tiles at 541,056 | performance |
| 202 procedural canopy stems among the tree cards | woodland canopy is placed by rule inside mapped polygons rather than surveyed, which is J86's closure and is inferred by construction | data — declared |
