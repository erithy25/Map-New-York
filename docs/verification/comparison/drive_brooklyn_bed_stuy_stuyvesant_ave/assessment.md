# Brooklyn brownstone block: Bed-Stuy, Stuyvesant Avenue

`drive_brooklyn_bed_stuy_stuyvesant_ave` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Bed-Stuy 20191130 - 27 - Nostrand @ Greene.jpg by Andre Carrotflower, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2019-11-30 10:22:34, 1920x1439. [Commons page](https://commons.wikimedia.org/wiki/File:Bed-Stuy_20191130_-_27_-_Nostrand_@_Greene.jpg)

**Camera** — camera 40.68170, -73.93300 (NYC_TM 1438, -2050) z 19.3 m NAVD88 | azimuth 13.0deg pitch +0.0deg | 35 mm on 36 mm (54.4deg horizontal) | 1208x906. Moved **17.4 m** onto the nearest roadbed polygon because the recorded eye point was inside `t_1_-3_roof_membrane`.

**Sun** — azimuth 159.0°, elevation 24.9° at 2019-11-30T10:22:34-05:00 (EXIF DateTimeOriginal).

**In frame** — 6/6 building tiles (670,572 tris), 0 landmarks, 1,138 pavement polygons, 365 props, 3,563 kit pieces, 88 vehicles, 378 people; 4,344,884 triangles. Props capped at 365 of 719. Frame mean 0.4067, sd 0.1323.

**Verdict — the render is a brownstone stoop at a few metres and contains no street at all, while the item is "Stuyvesant Avenue at Decatur Street, roadway centre, looking north". The stoop itself is good: two flights with railings, an areaway fence, arched window heads, a plausible brownstone colour. It is simply not the picture this sheet was supposed to take, and the clearance rule that exists to prevent that reported the view clear for 60 m**

## Why the render is a wall

The recorded eye point was inside a roof membrane, so the pavement snap moved the camera **17.4 m**
onto the nearest roadbed polygon and re-checked it. It passed on both of its thresholds:

* the **view axis** is clear for 60 m against a 20 m requirement;
* the **nearest opaque thing inside a 6° cone** about that axis is 10.7 m away, against an 8 m floor.

Both are true, and neither says anything about the 95 % of the frame outside that cone. A 54.4°
frame is ±27.2° wide and the cone is ±6°, so the constraint covers 5.8 % of its solid angle. The
facade that fills this picture is outside it. Recorded as J47, with `drive_bronx_grand_concourse` as
the second case of the same morning.

Two things follow that are worth separating. The position is one the stage **chose** — it moved the
camera 17.4 m — so this is not an inherited bad viewpoint. And the failure is invisible to every
number the sheet prints: `view_m: 60.0`, `nearest_obstruction_m: 10.7`, `frame.usable: true`, frame
mean 0.4067 with a healthy standard deviation. Nothing in the record says "this is a picture of a
wall".

## What matches

At the range this camera ended up at, these are right:

* **The stoop is a Brooklyn stoop.** Two flights rising to a parlour-floor entrance, thin metal
  railings on both sides and along the areaway, the areaway itself dropped below the sidewalk, and
  a cheek wall of the same stone. That is the element the reference photograph is also about.
* The arched window heads on the upper floors are the right motif for the block, and there are
  **278 door-entry pieces, 153 fire escapes, 152 cornices, 134 bulkheads and 92 fence pieces** among
  the 3,563 kit pieces in range — the vocabulary of a brownstone row rather than of a commercial
  street.
* The wall colour is a credible brownstone: a warm mid-brown-red rather than the grey a shell
  default would give.
* **227 of the 365 props are trees**, in bare-canopy form, which is right for 30 November — the leaf
  test puts the city into winter foliage between 15 November and 15 April and the reference
  photograph shows exactly that, bare plane trees against a blue sky.
* 24 hydrants, 53 street lamps, 52 manholes, 1 waste basket and 1 Citi Bike dock are placed. No prop
  kind in range failed to resolve: `unmapped_kinds` is empty for this frame.
* 88 vehicles and 378 people are placed from the simulation — 46 sedans, 22 SUVs, 8 taxis, 4 boro
  taxis, 3 black cars, 3 vans, 1 MTA bus, 1 DSNY truck. None of them is in this frame, because the
  frame is a wall.

## What does not match

* **The frame shows no street** (J47). Everything the item exists to compare — street width, kerb
  line, block-face rhythm, canopy over a roadway — is absent from the render half.
* **The reference is 1.7 km away.** The photograph is Nostrand Avenue at Greene; the viewpoint is
  Stuyvesant at Decatur. The sheet says so: the photograph's EXIF GPS was rejected as mis-tagged at
  1,712 m, past the 250 m at which it could still be the same view. It is a Bed-Stuy brownstone row
  photographed in the same week of the same season, and that is the most the reference chooser can
  claim for it.
* The facade has no relief at all: the window heads are applied arcs with no reveal, no sill, no
  lintel, no brownstone coursing, and the wall between them is a flat plane. The reference's own
  building carries a heavy bracketed cornice, a projecting bay, moulded surrounds and construction
  netting.
* 1,138 pavement polygons is the smallest count of the drive set — 384 crosswalk, 328 roadbed, 175
  curb, 172 sidewalk, 50 parking-lot, 27 median, 2 plaza — and none of it is visible here.
* 343 people and 191 vehicles were dropped for being outside the radius, 40 for standing in the
  carriageway without crossing, 29 for not being on a walkable surface, 12 for being a body with no
  rider, 11 at the agent triangle budget.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the frame is a facade at a few metres with no street in it | the pavement snap ranks candidates on a 6° axis cone, not on the frame; 95 % of the picture is unconstrained (J47) | verification |
| the reference is 1.7 km from the viewpoint | the photograph's own GPS was rejected as mis-tagged and the item names no subject, so no bearing can be derived | reference |
| no brownstone relief, coursing, bays or cornice | building shells carry massing and a flat opening grid; the kit supplies the arch and not the surround | geometry |
| no visible street | consequence of the camera position, not of missing data — 1,138 pavement polygons are loaded | verification |
