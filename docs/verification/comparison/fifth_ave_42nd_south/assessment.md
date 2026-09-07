# Fifth Avenue at 42nd Street (NYPL), street view looking south

`fifth_ave_42nd_south` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:01-21-2017 - Women's March on NYC looking up 5th Ave (10796).jpg by Rhododendrites, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2017-01-21 13:41:25, 1920x1440. [Commons page](https://commons.wikimedia.org/wiki/File:01-21-2017_-_Women%27s_March_on_NYC_looking_up_5th_Ave_(10796).jpg)

**Camera** — camera 40.75350, -73.98087 (NYC_TM -2607, 5942) z 23.4 m NAVD88 | azimuth 209.0deg pitch +0.0deg | 35 mm on 36 mm (54.4deg horizontal) | 1208x906. View direction: 209.0 deg as recorded in meta.json.  This item names no subject and the reference photograph's own view direction was not derived from the image (confidence: medium), so the two halves of this sheet are not guaranteed to face the same way -- compare them on street width, storey height and material, not on composition. Aim: level optical axis (the reference names no subject to aim at).

**Sun** — azimuth 204.6°, elevation 25.7° at 2017-01-21T13:41:25-05:00 (EXIF DateTimeOriginal).

**In frame** — 6/6 building tiles (299,644 tris), 9 landmark models, 2,233 pavement polygons, 383 props, 10,198 facade-kit pieces; 4,500,141 triangles; ground mesh 209² at 2.0 m near / 40.0 m far; kit capped by the triangle budget (20,149 in range). Frame mean 0.390, sd 0.177.

**Verdict — re-rendered 2026-09-07 against a photograph that looks the same way the render does. Both halves now run south down Fifth Avenue between the same canyon walls, with the same bright slot of sky at the far end. What the pairing demonstrates instead is total and unchanged: the photograph is ten thousand people filling the avenue and the render is an empty grey slab with nothing alive in it at all**

## What changed, and why

The photograph this sheet used to carry is titled "Women's March on NYC **looking down 42nd**": a view
along the cross street, taken from the same corner. Its own assessment said "the two halves face
different streets", and this is one of the nine viewpoints brief §12 condition 3 names.

It passed because the item's keyword group lists the cross-street numbers, and because the category
"5th Avenue (Manhattan)" is on a photograph taken at the corner whatever it faces. Two rules now
separate them (`docs/verification/comparison/REPORT.md` §2.11): the subject test is matched against a
photograph's own title and description rather than its categories, and `not_of` rejects a title that
announces a different subject — for this item, the library beside the avenue **and a view along the
cross street** ("looking down 42nd", "along 42nd"). The photograph the chooser now returns is by the
same photographer, from the same corner, at the same minute, and is titled "**looking up 5th Ave**".

## Re-rendered 2026-09-07 — the best-populated frame in the set

Fifth Avenue at 42nd looking south is the frame where the city reads as being *in use*. Four ranks of
traffic fill the avenue — yellow medallion cabs, a black sedan, a green boro taxi, a box truck, more
receding to the horizon — with crowds on both pavements, bare winter street trees on the right,
shopfront fascias reading BANK along the left frontage, lamp standards and a bus shelter. 52 vehicles
and 248 people, nine landmark models, and nothing needed culling.

**It is also the control for its own twin.** `fifth_ave_42nd_north` stands on the same corner looking
the other way and renders at half its photograph's brightness. This one does not:

| | this sheet (south) | its twin (north) |
|---|---|---|
| render mean | **0.372** | 0.227 |
| photograph mean | 0.448 | 0.455 |
| render median | **0.341** | 0.176 |
| Sun | **EXIF `DateTimeOriginal`** | *assumed* — "photograph year only; 21 June 09:30" |

The two photographs are within 0.007 of each other in mean luminance, so the difference is on the
render side. View direction is part of it — a south-facing avenue view under a morning sun catches
sunlit facades where a north-facing one gets their shadowed backs — but the sheet whose Sun comes
from the photograph's own instant lands within 17 % of it, and the sheet whose Sun is a guessed
21 June morning lands at half. That is the sharpest evidence in the set for the second half of
deviation I16, and it comes from a pair that differ in nothing else.

**What is still weak:** the lower third is bare roadway with no texture or markings, the block faces
are flat coloured planes with dashed windows (the facade-class case), and the vehicle bodies are
smooth and untextured at this distance.

## What matches

* **Both halves look along the same street in the same direction.** That is the change: the photograph
  runs south down Fifth Avenue with the sky slot closing at the vanishing point, and so does the
  render, on the recorded 209.0 deg downtown heading.
* The camera stands on the photograph's own EXIF GPS, 40 m from the item's nominal viewpoint, at 23.4 m NAVD88 on a 21.8 m street surface.
* As a Manhattan street canyon the render is credible: the roadbed and both sidewalks are the right widths, the kerb reveal is visible along their whole length, and the wall of buildings steps back and down toward a bright sky slot at the far end exactly as the photograph's own canyon does.
* Aerial perspective is right. The far towers wash out into haze at the same rate as in the reference, which is a fair test of the Nishita sky plus Filmic transform at a 25.7 deg winter Sun.
* Street furniture is present and correctly scaled: a bus shelter on the east sidewalk, cobra-head lamps on davits over the roadway, a mailbox at the kerb, sidewalk sheds with green netting along the west wall.
* The Sun is taken from the photograph's EXIF instant (2017-01-21 13:41:25 EST, elevation 25.7 deg) and the flat overcast-free light matches the reference's grey January sky closely enough that exposure is comparable.

## What does not match

* **The heading is still assumed rather than measured.** The item names no subject, so the azimuth is
  the avenue's own downtown heading and nothing in the file proves the photograph faces it; the title
  does, and a title is not metadata the pipeline can rely on in general (deviation I7). It agrees here.
* There are no people. The reference is a crowd that fills the frame from the lens to the vanishing point, several thousand visible; the render has not one figure. No other gap in this comparison set is as large in pixel terms.
* There are no vehicles, so the roadway reads as a fresh grey slab.
* No road markings, no lane lines, no stop bar, no crosswalk stripes.
* The building walls are flat pastel with unglazed window dashes. The reference's west wall is a continuous run of glazed shopfronts, awnings, scaffolding, signs ('cafe', 'metro') and fire escapes; the render's is a plain surface with a green scaffold band.
* No shopfront signage or lettering anywhere, and no glass in any opening.
* The bare street trees still read as opaque cones (11 impostor cards dropped in this frame; the branch geometry beneath them is what remains too dense).
* The Sun is right but the render is flatter than the photograph: a 25.7 deg January sun at 204.6 deg is almost straight down the avenue behind the camera, so both frames are frontally lit, and the render has none of the reference's overcast diffusion.
* The kit was capped by the triangle budget at 10,198 of 20,149 pieces in range, so half the facade detail within 140 m is not drawn.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| ~~the two halves face different streets~~ | **fixed**: the subject test now reads the photograph's own title and description rather than its categories, and `not_of` rejects a title announcing a view along the cross street | reference |
| no people | no crowd placement feeds the verification scene | data |
| no vehicles | no traffic placement feeds the verification scene | data |
| no road markings | pavement polygons carry a kind but no stripe geometry or texture | material |
| flat facades, no glazing, no signs | shells carry a per-material base colour; the facade kit supplies openings without glass, mullions or sign faces | material |
| trees read as solid cones | the leaf-off branch model is dense and untextured | material |
| half the facade kit not drawn | the 4.5 M triangle budget is spent before the kit is finished; the sheet records the cap | geometry |
