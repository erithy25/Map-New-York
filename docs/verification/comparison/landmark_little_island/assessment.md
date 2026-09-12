# Little Island at Pier 55

`landmark_little_island` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Hudson River Park td (2024-08-08) 061 - Gansevoort Park Athletic Field.jpg by Tdorante10, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2024-08-08 15:10:14, 1920x1080. [Commons page](https://commons.wikimedia.org/wiki/File:Hudson_River_Park_td_(2024-08-08)_061_-_Gansevoort_Park_Athletic_Field.jpg) — the photograph's own view direction is derived from the image at **high** confidence. The file names the athletic field as its subject and the item names Little Island; the pairing works because the park's white tulip piles stand across the field in the mid-distance, and a reader should know that the green foreground of the left-hand frame is the photograph's own subject.

**Camera** — 40.742312, -74.007662 (NYC_TM -4890, 4712) at z 4.5 m NAVD88 | azimuth 260.0°, pitch −0.3° | 35 mm on 36 mm (54.4° horizontal, landscape) | 1280x720. The camera stands on **the item's recorded viewpoint, not the photograph's**: this photograph's own EXIF GPS is **388.3 m** away, past the 250 m at which it could still be the same view, and the record says plainly that this is a statement about the pairing and not about the photograph. The recorded azimuth of 260.0° agrees with the bearing to the subject from the position used to **0.1°**. The walk then **moved the camera 22.2 m**: the recorded viewpoint is **inside `t_-5_4_roof_membrane`** — a ray straight up from the eye point hits its roof — so the eye was snapped onto the nearest surveyed roadbed polygon, keeping the same height above the heightmap. From there the view azimuth is clear for **96.0 m** against an **80.0 m** requirement, the nearest built thing in the frame is `prop_lamp_cobra_davit_8` **10.3 m** away, and **the nearest simulated agent is `agent_veh_camry_taxi_yellow_414.36` 6.7 m away**, against an agent probe of **20.0 m**. The ground under it reads 2.874 m NAVD88, the 10th percentile of 113 samples within 12 m, range 2.75 to 3.4 m.

**Sun** — azimuth 237.6°, elevation 52.7° at 2024-08-08T15:10:14−04:00, from the photograph's own **EXIF DateTimeOriginal**; 897.5 W/m² direct normal, sky at strength 0.0317, Filmic, **+1.39 stops** metered, unclamped, against a linear median of **0.068652** and a target of **0.18**. The physical rule would have given **0.0 stops**. This is one of the better-lit frames in the pass and the development is a small correction rather than a rescue.

**In the scene** — 3,580,303 triangles: 6 building tiles (202,176 tris, 0 missing, 0 LOD-substituted), 4 landmark models of which 2 can fall inside the 54.4° frame, 23,143 pavement polygons, 2,378 props, 4,221 kit pieces, 22 park-ground meshes, 79,848 triangles of structures over 5 tiles, 50 vehicles and 416 people.

## Verdict — the sightline scored 0.231 by measuring through the traffic, and the published frame is a photograph of a taxi's flank

**Nothing of Little Island is in the render.** The right-hand frame is filled, corner to corner, by a yellow taxi at close range with a van, an SUV and a green sedan stacked behind it, street trees closing over the top, a brick wall down the left edge and a striped steam stack on the kerb. There is no water, no row of tulip piles, no park. The subject stands **183.6 m** away at **0.9° off axis** and the frame is **54.4°** wide, so the aim is right and the picture is of something else.

**The record predicted 0.231 visible and it is the measurement that is wrong, not the aim.** The subject sightline casts 13 rays and reports **3 clear**, **3 on the subject**, **0 into nothing**, blocked at **18.4 m** by `prop_lamp_cobra_davit_33` — a street lamp. A taxi standing **6.7 m** from the lens does not appear in that list, and cannot: `subject_sightline` in `blender/verify/camera.py` casts through `_ray_past(..., _opaque, ...)`, and `_opaque` counts building shells, landmark models and props while `_is_agent` excludes everything `add_agents` places. So the sightline steps past every simulated vehicle and every pedestrian. **This is J49's declared decision working exactly as written** — the rule that moves the camera counts built fabric only, on purpose, so that a viewpoint does not move because a pedestrian walked past and the sheet stops being a comparison of one view — and this sheet is what that decision costs when the walk's own ranking (J79) is scored with the same blind predicate. The walk recorded its choice with `subject_visible_fraction 0.231` at the point it picked, and the frame it then rendered shows **none** of the subject.

**The clearance record is honest about the taxi and the walk still stood on it.** `nearest_agent_m` reads **6.7** against `nearest_agent_probe_m` **20.0**; the note names the vehicle by its object name. The number is measured, published and not acted on. That is the gap worth fixing: not the sightline's predicate, which has a good reason, but the absence of any rule that says a frame whose nearest agent is a quarter of the probe distance away is not a comparison frame.

**The height is half the catalogue's and the probe is right about the piece it found.** It measures **10.19 m** above a ground of −1.23 m on `lm_c_little_island.1`, against the catalogue's **18.9 m** for `c_little_island` whose origin stands **52.3 m** away — the deck at the coordinate, not the park's high point. **37 of 43** probe rays found fabric. The plan extent, **132.6 m by 132.0 m** and **not a tile mesh**, is the park's own footprint and is the figure on this sheet that most deserves trust. Because 10.19 m is under the pass's 12 m floor, the ray fan was built from the floor rather than from the subject, which the record states.

## What matches

* **The footprint.** 132.6 m by 132.0 m, measured off the landmark model itself rather than off a catalogue row (J74).
* **The aim.** Recorded azimuth 260.0° against a measured bearing of 260.1°, and the frustum puts the subject **0.9° off axis** at 243.0 m — the closest agreement between a recorded heading and a measured one on any sheet written so far.
* **The piers are built.** **79,848 triangles** of structures over 5 tiles in range, the largest structures figure on any sheet in this batch, on a stretch of waterfront that is nothing but piers.
* **Nothing was capped.** Props **2,378 placed of 2,527 in range**, kit **4,221 of 4,646**, **0 dropped for budget** — one of the few sheets in the pass that drew everything the budget allowed and still failed for another reason.
* **The park ground is exact where it can be checked.** Within 150 m, **591 samples**, an under-fraction of **0.0**, a median clearance of **0.2 m**, a minimum of **0.057 m** and **no** z-fighting at all. That is the best near-field park-ground reading in the pass.
* **The trees are real trees here.** **1,740** placed, **58** drawn from modelled branches within 120 m and **1,682** as impostor cards out to 721 m, **18** of the cards procedural canopy stems inside mapped woodland, at a mean scale of **0.93**.
* **The crowd is a Hudson River Park crowd** — **416 people** against 50 vehicles, the highest pedestrian-to-vehicle ratio in this batch, which is what an esplanade on a Thursday afternoon in August looks like.
* **The exposure needed almost nothing.** **+1.39 stops** metered and unclamped, and the two frames' means agree to **0.991**.

## What does not match

* **The subject is not in the picture.** A simulated taxi **6.7 m** from a 35 mm lens fills the frame.
* **The recorded visible fraction is a fiction for this frame.** **0.231** from 3 of 13 rays, measured with agents excluded from the ray test by design (J49).
* **The camera is not where the photograph was taken.** The item's recorded viewpoint, **388.3 m** from the photograph's own EXIF GPS, then moved **22.2 m** by the walk. Two frames of two places.
* **The recorded viewpoint was inside a tile mesh.** `t_-5_4_roof_membrane` is every roof-membrane surface in that tile joined into one object, so a ray straight up from the Hudson River Park esplanade hits "its roof" and the walk had to move (J94).
* **The photograph's athletic field is not in the render either** — no mown pitch, no ball-field fence, no floodlight mast. The reference's own foreground subject has no counterpart in the frame.
* **The render is darker at the midtone** — p50 **0.4997** against **0.6537**, a ratio of **0.764** — and flatter, sd **0.1946** against **0.2391** (**0.814×**). The photograph's median sits **1.096 stops** above the grey convention against the render's **0.248**, a **−0.848-stop** difference (J83). The reference is a flat overcast frame developed for a white sky.
* **Slightly less colour than the photograph** — chroma **0.1119** against **0.1266**, a ratio of **0.884**.
* **No cloud.** The reference is wholly overcast; nothing in this build reads a historical sky.
* **The catalogue height and the measured height disagree by nearly half** — 10.19 m measured against 18.9 m catalogued, because the coordinate sits over the low deck and the park's high point is elsewhere on a 132 m footprint (J94).
* **425 kit pieces were suppressed under landmark shells** and **63 props were dropped on a suppressed building** — the tile's own buildings give way to the landmark model, and their windows and street furniture go with them.
* **11 props across five kinds in range have no asset** — 5 drinking fountains, 3 misc structures, 1 artwork, 1 parks comfort station, 1 real-time information sign. A waterfront park's drinking fountains are exactly the furniture a reader would look for.
* **Eight park surface kinds keep the builder's flat colour** — cemetery grass, hard sport court, field grass, greenstreet grass, park grass, **pool water**, recreation grass and bare ground, because the texture catalogue holds walls, roofs, roadway and floors and no photographic set for any of them (J40).
* **The park ground sinks away from the camera.** Beyond 400 m the under-fraction is **0.2024** over 835 samples with a worst reading of **−5.61 m**, and between 150 and 400 m it is **0.2559** over 469 samples. The redrape moved **126,578** vertices, up to **3.288 m** up and **3.503 m** down.
* **One of five tiles in range has no structures file.**
* **2,769 agents were dropped** — 947 pedestrians outside the radius, 797 at the agent triangle budget, 368 in the carriageway without crossing, 342 vehicles at the budget, 205 vehicles outside the radius, 64 pedestrians not on a walkable surface, 24 vehicles where the planimetric data has no roadway, **13 pedestrians inside a building**, 9 riderless bodies.
* **578 trees are a substituted species** and **4** are scaled outside the allowed band.

## Derived

| figure | how |
|---|---|
| a quarter | the nearest agent at 6.7 m against the 20.0 m agent probe, both quoted from the clearance record above |

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the subject is not in the frame at all | a simulated taxi stands 6.7 m from the lens; the walk measured it, published it as `nearest_agent_m`, and did not act on it, because by J49 the rule that moves the camera counts built fabric only — deliberately, so a viewpoint is not moved by a passing pedestrian | **verification — open (J98), and the measurement is already in the record** |
| the visible fraction reads 0.231 | `subject_sightline` casts through `_opaque`, which excludes every `agent_veh_*` and `agent_ped_*`, so the ray fan measures the built city and the frame shows the traffic (J49, J79) | **verification — open (J98)** |
| the camera is 388.3 m from the photograph | the photograph's EXIF GPS is past the 250 m at which it could be the same view, so the item's recorded viewpoint was used; the record says so rather than pretending otherwise | verification — declared, and the honest choice |
| the walk had to move at all | the recorded viewpoint tests as inside `t_-5_4_roof_membrane`, one tile's roof-membrane surfaces joined into a single object (J94) | **geometry — open, the join is the fault** |
| 10.19 m against a catalogued 18.9 m | the probe measures the object at the coordinate and the coordinate sits over the low deck of a 132 m park (J74, J94) | verification — declared, and correct about what it measured |
| p50 0.764, sd 0.814 | the photograph is developed 1.096 stops above the grey convention for its overcast sky and the render 0.248 above (J83) | reference |
| no cloud | nothing in this build reads a historical sky | reference — no source exists |
| 425 kit pieces and 63 props suppressed | the landmark shell replaces the tile's buildings and takes their kit and kerb furniture with it | declared decision |
| 11 props across five kinds unmapped | no asset exists for those kinds | data |
| eight park surface kinds flat | the texture catalogue has no photographic set for grass, court, pool water or bare ground (J40) | data — declared, named on the sheet |
| under-fraction 0.2559 mid-range, 0.2024 far | the park builder drapes on its own heightmap and the scene's differs; the redrape closes the near field to 0.0 and leaves a −5.61 m tail in the far one (J71) | geometry — open, bounded |
| 416 people of 2,077 asked | the agent triangle budget plus the placement rules, each with its own count | performance + verification |
| 1 of 5 tiles without a structures file | that tile is unbuilt | data — open |
