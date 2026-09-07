# Brooklyn brownstone block: Park Slope, Seventh Avenue / Garfield Place

`drive_brooklyn_park_slope_7th_ave` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Park Slope - Brooklyn (55268725540).jpg by ajay_suresh, CC BY 4.0 (https://creativecommons.org/licenses/by/4.0), taken 2026-04-23 13:09, 1920x1080. [Commons page](https://commons.wikimedia.org/wiki/File:Park_Slope_-_Brooklyn_(55268725540).jpg)

**Camera** — camera 40.67250, -73.97820 (NYC_TM -2390, -3064) z 26.9 m NAVD88 | azimuth 30.0deg pitch +0.0deg | 35 mm on 36 mm (54.4deg horizontal) | 1280x720. View direction: 30.0 deg as recorded in meta.json.  This item names no subject and the reference photograph's own view direction was not derived from the image (confidence: medium), so the two halves of this sheet are not guaranteed to face the same way -- compare them on street width, storey height and material, not on composition. Aim: level optical axis (the reference names no subject to aim at).

**Sun** — azimuth 187.7°, elevation 61.8° at 2026-04-23T13:09:00-04:00 (EXIF DateTimeOriginal (minutes)).

**In frame** — 6/6 building tiles (447,580 tris), 1 landmark models, 1,799 pavement polygons, 288 props, 3,574 facade-kit pieces; 3,098,644 triangles; ground mesh 211² at 2.0 m near / 40.0 m far.

**Camera clearance** — the recorded viewpoint is boxed in: the view azimuth is closed off 9 m ahead, less than the 12 m below which a frame shows nothing but wall; the camera was moved 12 m backwards -- the nearest point in open air -- keeping the same eye height above the heightmap.  The view azimuth is clear for 21 m from there

**Verdict — the camera was rescued from a nine-metre wall and put in front of a twenty-metre one: the item's own azimuth points across Seventh Avenue at the opposite block face, so the frame is two party walls and a strip of sidewalk, and the brownstone street the item exists to test is off to the left**

## Re-rendered 2026-09-07, and a defect I went looking for and did not find

This is the weakest frame in the drive-through set. The camera stands at a 1.6 m eye on a 54.4° lens
with the nearest building 28 m dead ahead and every other building within 60 m *behind* it (116-175°
off the view axis), so the frame is two large blank wall planes carrying sill bars and three
window-unit air conditioners, over a featureless ground plane. Nothing in it can be compared with a
photograph of a Park Slope shopping street except the wall colour.

The dark line where the wall meets the ground looked like a floating building, so I measured it
rather than writing it up. **It is not one.** Sampling 1,871 buildings across 40 tiles and comparing
each footprint's `ground_z` against the terrain heightmap beneath its centroid:

| | value |
|---|---|
| median `ground_z` − terrain | **+0.00 m** |
| p05 / p95 | −0.04 m / +0.02 m |
| more than 0.5 m above the terrain | 0.3 % |
| more than 0.5 m below | 0.1 % |

Buildings sit on the ground. The line is a contact shadow, not a gap, and the city-wide check that
would have caught a systematic problem says there is not one. Recorded because a negative result from
a check worth running is worth keeping — the next person to see that line should not have to measure
it again.

What the frame *does* show is the same gap as `drive_brooklyn_bed_stuy_stuyvesant_ave`: sills and
HVAC units placed on a wall with no window openings between them. Here it is starker, because there
is nothing else in the frame.

*Later note:* the same qualification applies here as on the Bed-Stuy sheet — the Wall Street canyon frame shows the window kit producing real recessed openings, so this is a facade-class case rather than a kit-wide one.

## What matches

* The boxed-in test fired and is stated: the recorded eye point had the view closed off 9 m ahead, and the camera was moved 12 m backwards to a point with 21 m of clear view.
* The photograph's own EXIF GPS was rejected as mis-tagged at 737 m; the item's viewpoint was used.
* What the wall does carry is right for the block: window air-conditioner units on their sills at the correct size and spacing, projecting stone string courses at each floor level, and a party-wall junction between two buildings of slightly different colour and height.
* The storey heights read correctly at about 3.2 m, and the two buildings meet at a clean vertical joint as adjacent brownstone-era buildings do.
* 1,799 pavement polygons are placed, including 417 crosswalk polygons, and the kerb line runs across the frame at the right height.

## What does not match

* The frame is a wall. The item's recorded azimuth of 30 deg points across Seventh Avenue rather than along it, so the render shows the opposite block face at 20 m instead of the street toward Flatbush Avenue that the note describes.
* The reference photograph is the whole street corner: brownstone rows with stoops in spring foliage, a traffic signal on its mast arm, an 8 AV street sign, parked cars along both kerbs, a crosswalk with a pram crossing it, and a red car mid-frame. Not one of those has a counterpart.
* There is not one window opening on either wall, only sills and air-conditioners floating on a blank plane.
* No street trees appear in the frame although 279 props were placed; no signal, no signs, no cars, no people.
* The ground is a smooth untextured plane with visible facets from the graded terrain grid.
* Props were capped by the triangle budget.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the frame is a wall across the street | the item's recorded azimuth points across the avenue rather than along it; no correction in this stage can invent the intended view | reference |
| no window openings | the facade kit placed 3,574 pieces in this scene but this facade class carries no window piece on the visible run | geometry |
| no signal, signs, cars or people | no traffic, signage or crowd placement feeds the verification scene | data |
| no visible street trees | the trees that exist are outside this narrow frame | data |
| faceted, untextured ground | the terrain material is a flat colour; the pavement material has no texture | material |
