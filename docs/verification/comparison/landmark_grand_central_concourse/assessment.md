# Grand Central Terminal Main Concourse

`landmark_grand_central_concourse` · **no sheet** · render record: [`render.json`](render.json)

**Reference** — File:Grand Central (11).jpg by PortableNYCTours, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0). [Commons page](https://commons.wikimedia.org/wiki/File:Grand_Central_(11).jpg)

**Viewpoint** — 40.7528, -73.9776, azimuth 119.0°: *the west balcony of the Main Concourse, looking east across the concourse to the east balcony and the Apple Store stair*.

## Verdict — declined, and the declining is the right answer

**There is no sheet for this item and there should not be.** The record's `status` reads **`not_renderable_interior`** and `interior` reads **true**, and the runner refused it before rendering rather than producing a frame of whatever stands at that coordinate on the outside. Of the 172 items, this is the **only** one declined this way: 171 rendered, 0 failed, 1 declined.

**The reason is a scope decision taken at the start and recorded twice.** B10: *multi-part complexes are one row per BIN, and interiors do not exist — every building is a shell; the brief asks for a drivable exterior city*. I5: *no interiors anywhere, except volumes visible from the street through glass*. The Main Concourse is an interior room 84 m long under a painted ceiling vault, reached from a balcony inside the building. Nothing in this build models it, and nothing in this build could render a comparable frame from the coordinate the item names, because the coordinate is inside a shell.

**What is worth recording is that three other items with interior photographs were *not* declined.** `landmark_moynihan_train_hall`, `landmark_queens_museum` and `landmark_rose_center` are each paired with an interior photograph, each had the same evidence available — the record on all three states that the eye point at the photograph's own GPS is **inside a landmark model's roof** — and each was rendered from outside and published with four comparison ratios against a room (J100, J104). This item was declined because its **item definition** carries `interior: true`; the other three were not, because their definitions do not. So the gate exists and works, and it reads the item's own flag rather than the evidence in front of it.

**The honest form of this entry is therefore a cross-reference.** The declining is correct. The inconsistency is that the same decision was not reached on the three sheets where the record had the evidence to reach it.

## Measured for this assessment

| figure | how |
|---|---|
| 172 items, 171 rendered, 0 failed, 1 declined | `blender_out/render_all_state.json` at the end of the v16 pass, whose `done`, `failed` and `declined` lists are the pass's own account of itself |

## What this item establishes

* **The runner will refuse to render rather than publish a frame of the wrong thing**, and says so in the record's own status field.
* **The refusal is counted** — 171 rendered, 0 failed, **1 declined** — so a reader of the index sees 171 sheets and one stated absence, not 172 sheets with one that quietly shows a street corner.
* **The scope decision behind it is recorded twice** (B10, I5) and predates this pass.

## What is missing, and what it would take

* **No comparison of the concourse exists**, and none can while the build has no interiors. Modelling it is not a variation on the exterior work: it needs the room, the vault and its ceiling painting, the balconies, the stairs, the clock and the information booth, none of which is a class this build carries.
* **The photograph is retained in the record** with its licence and Commons page, so the pairing is documented even though no sheet was made from it.

## Cause

| gap | cause | class |
|---|---|---|
| no sheet | the item declares `interior: true` and this build has no interiors (B10, I5); the runner declined it before rendering | **declared decision — and the correct behaviour** |
| three other interior pairings were rendered anyway | the gate reads the item's own `interior` flag, not the evidence in the record that a photograph's GPS lies inside a landmark model's roof (J100, J104) | **verification — open (J100, J104)** |
