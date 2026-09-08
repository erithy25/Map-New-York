# Equitable Building (120 Broadway)

`landmark_equitable_building` · **the renderer refused to publish this frame** · render record: [`render.json`](render.json) · [`render_error.txt`](render_error.txt)

**Reference** — File:Equitable Building April 2022 001.jpg by Kidfly182, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2022-04-01 13:09:11, 1920x1440. [Commons page](https://commons.wikimedia.org/wiki/File:Equitable_Building_April_2022_001.jpg)

**Camera** — 40.70869, -74.01108 (NYC_TM -5163, 953) at z 12.2 m NAVD88 | azimuth 120.1°, pitch **+32.0°** | **18 mm** on 36 mm (90.0° horizontal) | 1208x906. The camera stands on this photograph's own GPS; the azimuth is the bearing from there to the Equitable Building, so heading and position both come from the photograph. The item's own recorded azimuth is 85.0°, **35.1° away**, and belongs to its nominal viewpoint.

**Sun** — elevation 54.0° at 2022-04-01T13:09:11−04:00, from the photograph's own **EXIF DateTimeOriginal**; 902 W/m² direct normal, **+0.00 stops**.

**Status — `rejected_unusable_frame`.** Frame mean **0.0453**, standard deviation 0.0964, against a floor of 0.06 below which the renderer will not publish. It was rendered twice: the first frame came out at the same 0.045, the clearance correction was forced, the camera was walked **12.4 m**, and the second frame was no better. There is no `sheet.png` and no `render.png` for this item, and that is the correct outcome — a black frame is not evidence and publishing one would be worse than publishing nothing.

## Verdict — a refusal, and it is the sharpest evidence in the set for what is wrong with the camera walk

**Everything about this item except the camera's position is right, and the record proves each piece separately.**

* **The model is exact.** The height probe casts 17 rays at the subject's coordinate and reads **164.61 m** above the ground there, off `lm_equitable_building.4`. The catalogue entry `equitable_building`, 23.1 m away, publishes **164.6 m**. Those agree to a centimetre — the closest agreement between measurement and catalogue anywhere in this pass (J74).
* **The heading is the photograph's own**, derived from its GPS to the subject, and it disagrees with the item's recorded azimuth by 35.1° — which the record states rather than hides.
* **The instant is the photograph's own**, to the second, with a 54° April sun and 902 W/m² of direct normal irradiance. There is plenty of light in this scene.
* **The subject blocks itself.** The sightline is closed at **26.6 m by `lm_equitable_building.8`** — a piece of the very building the sheet is a picture of. The camera is 74.4 m from the subject's coordinate and standing against the building's own flank.

**So the frame is black not because the city is dark but because the camera is in the wrong place**: pressed against a 164 m slab in a Financial District canyon, tilted 32° up into a shaft between buildings that a 54° sun does not reach. The lens was already widened to the 18 mm floor and the axis tilted the remaining 32°, because the subject stands **64° above the horizon** at 78 m and a 74°-tall frame cannot otherwise contain it. Both of those are correct responses to being too close to a tall thing, and neither of them can fix being too close.

**This is J79 in its purest form** (docs/DEVIATIONS.md). The camera walk moves a boxed-in viewpoint onto the nearest pavement and accepts it when *the view azimuth is clear at eye level* — here, 40.7 m. It never asks whether the subject can be seen. A position 74 m from a 164 m building with 40 m of level clearance passes that test and cannot possibly produce a picture of the building.

## What the record still establishes

Even without a frame, the scene was built and measured, and those numbers stand:

* **4 building tiles**, **12 landmark models**, 22,921 pavement polygons, **711 props**, **3,776 kit pieces**, 50 vehicles and 244 people; 4,500,103 triangles in 222 s.
* The Equitable Building model is present, correctly placed and correctly sized, by the probe's own measurement against the catalogue's published height.
* The clearance record names what the camera is near: `lm_equitable_building.0` **18.2 m** away in the frame, and `agent_veh_rav4_fhv_106.49` 9.6 m away.

## What this sheet cannot say

Nothing about the Equitable Building's appearance. Its H-plan slab, its 1915 massing, the setback-law argument it is famous for — none of it is testable from a frame that does not exist. **The absence of a sheet here is a gap in the evidence and is counted as one**, not quietly passed over.

## Cause

| gap | cause | class |
|---|---|---|
| the frame is near-black and was refused twice | the camera stands 74 m from a 164 m slab in a canyon, tilted 32° into a shaft a 54° sun does not reach; the walk accepted the position because the azimuth was clear at eye level and never asked whether the subject could be seen | **verification — open, DEVIATIONS J79** |
| the axis is tilted 32° and the lens is at the 18 mm floor | the subject stands 64° above the horizon at 78 m and a 74°-tall frame cannot contain it; both are declared (I18) | stated choice |
| the sightline is closed by the subject itself | `lm_equitable_building.8` at 26.6 m — the camera is against the building's flank | verification |
| no sheet, no render.png | the frame gate refuses anything below mean 0.06 as unusable as evidence; this is the rule working | — (not a gap in the city) |
| the model's fidelity is untested here | it is measured, not pictured: 164.61 m against a published 164.6 m | — (not a gap) |

**What would fix it:** J79's repair — score the camera walk's candidates on the subject's own sightline instead of on eye-level clearance. A position from which a 164 m building is actually visible is necessarily one with sky in the frame, so the same change that puts the subject in the picture is the one that gives the frame its light. This item is re-rendered when that lands.
