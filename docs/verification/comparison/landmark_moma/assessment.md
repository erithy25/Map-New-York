# Museum of Modern Art

`landmark_moma` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Museum of Modern Art (MoMA) (51395759113).jpg by ajay_suresh, CC BY 2.0 (https://creativecommons.org/licenses/by/2.0), taken 2021-08-21 15:18, 1920x1920. [Commons page](https://commons.wikimedia.org/wiki/File:Museum_of_Modern_Art_(MoMA)_(51395759113).jpg) — the photograph's own view direction is derived from the image at **high** confidence.

**Camera** — 40.761288, -73.977748 (NYC_TM -2383, 6825) at z 21.3 m NAVD88 | azimuth 24.6°, pitch +15.6° | 18 mm on 36 mm (90.0° horizontal) | 1044x1044. The camera stands on **this photograph's own EXIF GPS**, 26.2 m from the item's recorded viewpoint — and then two separate rules moved it. The recorded viewpoint was **boxed in**, the view azimuth closed off **4 m ahead** against the 25 m the frame needs, so the clearance walk moved the camera **44 m to the left**, ranking candidates on how much of the subject each one sees (J79). At that new point the eye sat **7.95 m under `lm_moma.15`**, the landmark model's own level deck at 29.73 m NAVD88, so it was **raised onto that deck** and now stands at **31.33 m NAVD88** (J65). The nearest built thing in the frame is `lm_moma.5` **9.3 m** away.

**Sun** — azimuth 236.5°, elevation 48.0° at 2021-08-21T15:18:00−04:00, from the photograph's own **EXIF DateTimeOriginal (minutes)**; 880.1 W/m² direct normal, sky at strength 0.0322, Filmic, **+6.00 stops** — and held there. The record's note is the sharpest in the set: *"the frame wanted +7.56 stops and was held at +6.00: a scene this far from a photographable level is not developed into a picture of one."* The linear median is **0.000955**. The physical rule would have given **0.0 stops**.

**In the scene** — 4,500,007 triangles: 4 building tiles (222,112 tris), 9 landmark models of which 5 fall inside the 90.0° frame, 20,949 pavement polygons, 1,152 props, 6,730 kit pieces, 14 park-ground meshes, 68 vehicles and 333 people.

## Verdict — two repairs each did exactly what they were written to do, and together they produced a frame with no museum in it

**This is the worst sheet in the set, and nothing in it is a modelling failure.** The render is a slot between two wall planes over a pale ground plane, with a diagrid frame receding up the middle and a fire hydrant at the right edge. MoMA's 53rd Street front — the dark glass wall, the cantilevered entrance canopy, the white vertical `MoMA` banner, the street tree — is not in the picture. Neither is a single one of the 68 vehicles or 333 people the scene holds.

**The chain that produced it is legible line by line.** The recorded viewpoint was closed off 4 m ahead, so the clearance walk went looking for open air and found it **44 m to the left**. That point happens to lie over MoMA's own elevated deck, so the deck rule raised the camera onto it, out of the **7.95 m** it was sitting below it. From a terrace 9.3 m from the museum's flank, with a 90° lens tilted 15.6° up, the frame contains that flank, the neighbour across the slot, and the deck underfoot. Each rule is right. The composition of the two is not.

**The sightline then certifies the result as a success.** 13 rays, **12 clear**, **12 on the subject**, visible fraction **0.923** — and every one of those 12 lands on **MoMA's own fabric nearer than the recorded coordinate**, at **9.1 m** on `lm_moma.5`, against a subject recorded **66.8 m** away. The self-fabric rule (J78) exists so that a building does not count as hiding itself; here it accepts a blank wall at arm's length as a view of the museum. The frustum test says the rest: **MoMA is 66.8° off axis** at 74.3 m, while what sits **1.4° off axis** is Billionaires' Row at **337.2 m** — the diagrid in the middle of the frame. The camera is not pointed at the subject.

**The one thing the sheet proves is the height.** The probe casts **43 rays, all 43 on built fabric**, measuring **73.45 m** above a ground of 20.78 m against a catalogue **74.7 m** whose origin sits **13.6 m** from the recorded coordinate. The museum is modelled and it is the right height. This frame is not evidence of it.

## What matches

* **The subject's height is measured and agrees with the catalogue** — 73.45 m from 43 rays, all landing on fabric, against 74.7 m recorded.
* **The camera stands on a real surface.** The deck it was raised onto is `lm_moma.15`, the landmark model's own level deck at 29.73 m NAVD88, and the eye is 1.6 m above the drawn surface rather than 7.95 m below it.
* **Five landmarks are inside the frame and all five belong to this neighbourhood**: MoMA at 74.3 m, Billionaires' Row at **337.2 m** (1.4° off axis), Carnegie Hall at **419.6 m**, The Plaza Hotel at **459.9 m** and the Central Park perimeter wall at **2,733.4 m**, dead on axis.
* **The walls are the right materials.** 201 material slots resolved against the shared photographic catalogue, and the near wall reads as stone rather than as flat colour.
* **The crowd clock is right.** **Saturday** for 2021-08-21, which was a Saturday, and the fleet is a Midtown Saturday fleet: **30 yellow taxis, 15 boro taxis, 13 sedans, 8 black cars, 3 SUVs**.
* **Citi Bike is a station**: 513 dock units in range (Stage 40).
* **The agents above the camera were culled for being above it.** **8 pedestrians and 2 vehicles over the observer** were dropped — the cull that exists because the camera is on a deck and the street agents are below it.

## What does not match

* **The subject is absent from its own sheet.** No glass curtain wall, no canopy, no banner, no entrance, no street tree. The photograph is of a building front; the render is of a gap between two buildings.
* **No people and no traffic in frame** despite 333 people and 68 vehicles in the scene. They are on the street 10 m below and behind the camera.
* **The frame is nearly monochrome.** Chroma **0.0268** against **0.0772**, a ratio of **0.347** — the render holds a third of the photograph's colour, because a shadowed slot of grey stone has almost none to hold.
* **The exposure was clamped, not met.** The frame wanted **+7.56 stops** and got **+6.00**, so it is published **below its own metered target**. The record says why in as many words: a scene this far from a photographable level is not developed into a picture of one.
* **The means agree and that agreement is meaningless.** Mean **0.3539** against **0.3380** (**1.047×**), median **0.3008** against **0.2747** (**1.095×**), standard deviation **0.2394** against **0.2590** (**0.924×**). Two dark frames of different things.
* **6,269 of 6,730 kit pieces are windows**, against **6 cornices, 6 quoins, 9 string courses and 1 pilaster** in the whole scene. On a modernist glass front that ratio is less wrong than elsewhere, but the frame shows no fenestration at all.
* **Both budgets were hit.** Props capped at **1,155,385** triangles, kit at **1,063,618** with **22,577 pieces in range** — a fifth of what the frame wanted. At the agent budget a further **303 vehicles and 1,210 people** were dropped, on top of 789 vehicles and 1,279 people outside the radius.
* **MoMA's sculpture garden is not in the scene.** **9 artwork props** were wanted in range and had no asset, along with 1 memorial, 1 drinking fountain and 1 misc structure.
* **476 tree rows did not fit the props budget**, and of the 214 trees placed only **60** are drawn from modelled branches within 120 m.
* **There is no park ground within 150 m to check** — **0 samples** in the near band. Beyond 400 m, **0.4278 of 187 samples sit under the terrain**, the highest near-far under-fraction measured in this pass over a small sample.
* **3 of the 4 tiles in range have no structures file**, leaving 96 triangles of structures.
* **28 riderless bodies were dropped** — bicycles, e-bikes and pedicabs the fleet exports without a rider.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the museum is not in its own frame | the clearance walk moved the camera 44 m to the only open air it found, and the deck rule then raised it out of the 7.95 m it sat below MoMA's own terrace; from there the subject is a flank 9.3 m away and Billionaires' Row is what sits on axis at 337 m | **verification — open, the two rules compose badly** |
| the sightline reports 0.923 visible | all 12 hits are on MoMA's own fabric nearer than the recorded coordinate, at 9.1 m against a subject 66.8 m out; the self-fabric rule (J78) accepts them | **verification — open, the rule needs a distance test** |
| the camera points 66.8° away from the subject | the azimuth is the bearing from the photograph's GPS to the subject, computed before the walk moved the camera 44 m; the heading was not recomputed from the point actually used | **verification — open** |
| published below its own metered target | the frame wanted +7.56 stops and the clamp holds at +6.00, by the rule that a scene this far from a photographable level is not developed into a picture of one (J83) | verification — declared |
| chroma 0.347 | a shadowed slot of grey stone has little colour to hold | reference |
| no sculpture garden | 9 artwork props had no asset; sculpture is not a class this build models | data |
| props and kit capped, 22,577 kit pieces in range against a 1,063,618-triangle budget | the per-frame triangle budgets, each named with what it dropped | performance |
| 476 tree rows dropped | the props triangle budget | performance |
| 0.4278 of far park-ground samples under the terrain | surfaces draped on the 2 m heightmap against a scene edge coarsened to 40 m, over only 187 samples | verification |
| 28 riderless bodies dropped | the fleet exports bicycle, e-bike and pedicab bodies without a rider | geometry |
