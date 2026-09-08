# Chrysler Building

`landmark_chrysler_building` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Chrysler Building October 2022 001.jpg by Kidfly182, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2022-10-08 14:36:16, 1920x1440. [Commons page](https://commons.wikimedia.org/wiki/File:Chrysler_Building_October_2022_001.jpg) — the photograph's own view direction is derived from the image at **high** confidence.

**Camera** — 40.75, -73.9767 (NYC_TM -2278, 5560) at z 16.7 m NAVD88 | azimuth 29.6°, pitch **+20.8°** | **18 mm** on 36 mm (90.0° horizontal) | 1208x906. The camera stands on the item's recorded viewpoint — this photograph's own EXIF GPS is 136.8 m away and the eye point there is **inside** `t_-3_5_roof_membrane`, so it was not used — and was then **moved 22.9 m onto the nearest crosswalk**, because the recorded viewpoint is boxed in: the view azimuth is closed off 13 m ahead, less than the 80 m this frame needs. From the new point the view azimuth is clear for 96 m, the nearest built thing in the frame is `prop_lamp_cobra_davit_209` 9.0 m away and the nearest simulated agent is `agent_veh_camry_black_car_478` 4.0 m away.

**Sun** — from 2022-10-08T14:36:16−04:00, the photograph's own **EXIF DateTimeOriginal**. That date is a **Saturday** and the crowd was drawn for one.

**In the scene** — 20 city surfaces are dressed from the shared photographic catalogue; the subject is 210.9 m from the camera and the sightline is closed at 24.0 m.

## Verdict — the Chrysler Building is not in this frame, and the model is not why

**The photograph is the crown**: the stainless-steel arch tiers, the triangular windows, the spire, filling the frame against a deep blue October sky. **The render is a canyon of curtain-wall slabs with no Chrysler Building in it at all.**

**The model is not the reason.** `chrysler` is among the most detailed entries in the catalogue and its fidelity statement is specific: *"real footprint, setbacks at floors 16/24/31/61/71, tip 318.9 m, crown top 282.0 m, a 71st-floor observation deck, seven Nirosta arch tiers with triangular windows, 31st-floor hubcap frieze with corner radiator-cap gargoyles, eight 61st-floor eagles, white-glazed-brick walls with dark grey brick trim."* The height probe confirms the model is standing where the subject is: **17 of 17 rays** land on built fabric at the subject's coordinate and the highest is `lm_chrysler.2` at **280.22 m** above the ground there, against the catalogue's published 318.9 m to the tip — the difference being the spire above the point the rays meet (J74).

**The reason is the camera placement, and it is a fault in the rule rather than in this sheet.** The walk moved the camera onto a crosswalk and accepted it because *the view azimuth is clear for 96 m* — a probe that looks **level**. The subject is 249.8 m away and **20.8° up**, so the ray that matters climbs into a building the level probe passes under: the sightline is closed at **24.0 m** by `t_-3_5_glass_curtain`, whose face fills the near frame. The clearance the placement optimised is not the clearance the frame needed. Measured across the nine v15 sheets that name a subject, **seven report a blocked sightline and six of those had a clearance probe reporting more than twice the blocker's distance as clear** (docs/DEVIATIONS.md J79).

**Nothing below should be read as a comparison of the Chrysler Building.** What the sheet does compare is Midtown fabric, and it compares it in deep shadow.

## What matches

* **The model is present, complete and correctly placed.** The probe lands 17 of 17 rays on it and reads 280 m of building at the subject's own coordinate. Nothing about this sheet is evidence against the Chrysler model; the sheet simply does not point at it.
* **The instant is the photograph's own**, to the second, and the crowd was drawn for the Saturday that date is.
* **The rejection of the photograph's GPS is correct behaviour and is declared**: the eye point there is inside a building, and the record says which one and how it was tested.
* **The street is a Midtown street** — a canyon of setback towers with cars at the kerb, a street tree, LinkNYC kiosks and a cobra-head lamp, all in their right places.

## What does not match

* **The subject is absent from the frame.** Not simplified, not distant — absent. A curtain-wall tower 24 m from the lens stands between the camera and it.
* **The frame is a third of the photograph's brightness and carries an eighth of its colour**: mean **0.1089** against **0.3247** (**0.335×**), standard deviation **0.11** against **0.245** (**0.449×**), chroma **0.0295** against **0.2208** (**0.134×**), 95th percentile **0.3422** against **0.9363**, 5th percentile **0.0076** against **0.0773**. The photograph is a sunlit steel crown against deep blue sky; the render is a shaded canyon floor with a strip of sky at the top. The chroma ratio is the lowest in the set so far and this sheet cannot apportion it between the pairing and J66, because the two halves have almost no surface in common.
* **The verticals converge by 20.8°** and the lens is at the **18 mm** floor. The sheet declares both: past that floor a level axis cannot contain a subject this tall this close, so the frame is **not comparable with the photograph on proportion**. Here it buys nothing, because the tilt aims at a wall.
* **`subject_visible` is `false` with 1 of 5 rays clear and 0 landing on the subject** — and on this sheet, unlike DUMBO, the boolean is **right**. The blocker is a building, not a lamp taking rays from an over-wide fan.
* **The photograph's whole content — the arch tiers, the triangular windows, the eagles, the hubcap frieze — is untestable from this frame.** The sheet proves nothing about the one part of this build that was modelled to a published description.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the subject is not in the frame | the camera walk scores candidates on eye-level azimuth clearance and never on the subject's own sightline; the axis is 20.8° up and a curtain-wall tower 24 m away closes it | **verification — open, DEVIATIONS J79** |
| mean 0.335×, chroma 0.134× | a sunlit steel crown against deep blue sky versus a shaded canyon floor; the two halves share almost no surface, so this sheet cannot apportion the gap between the pairing and J66 | reference |
| verticals converge by 20.8° | the subject tops out far above a level 18 mm frame at 250 m; past the lens floor the axis must tilt and the sheet declares it (I18) | stated choice |
| the crown, the tiers, the eagles are untestable | they are modelled and the frame does not reach them; this is not evidence about the model | verification |
| the photograph's GPS was not used | the eye point there is inside `t_-3_5_roof_membrane`; the record names the test and the building | verification — correct behaviour |
