# Washington Street in DUMBO with the Manhattan Bridge

`dumbo_washington_st_manhattan_bridge` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Manhatten Bridge - taken from Washington Street.jpg by David Kernan, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2024-11-23 14:17:56, 1920x3413. [Commons page](https://commons.wikimedia.org/wiki/File:Manhatten_Bridge_-_taken_from_Washington_Street.jpg)

**Camera** — camera 40.70306, -73.98960 (NYC_TM -3347, 341) z 5.1 m NAVD88 | azimuth 357.1deg pitch +0.9deg | 28 mm on 36 mm (39.8deg horizontal, 65.5deg vertical, portrait) | 784x1394. View direction: 357.1 deg, the bearing from this photograph's own GPS position to Manhattan Bridge Brooklyn tower; heading and position both come from the photograph.  The item's recorded azimuth is 345.8 deg, 11.3 deg away, and belongs to its nominal viewpoint. Aim: aimed at Manhattan Bridge Brooklyn tower 160 m away, at its mid-height (a nominal 10 m subject); +0.9 deg from horizontal.

**Sun** — azimuth 218.4°, elevation 18.9° at 2024-11-23T14:17:56-05:00 (EXIF DateTimeOriginal).

**In frame** — 8/8 building tiles (183,786 tris), 2 landmark models, 2,762 pavement polygons, 606 props, 8,917 facade-kit pieces; 4,289,064 triangles; ground mesh 219² at 2.0 m near / 40.0 m far.

**Verdict — the right street, the right walls and the right bridge in the right place — and the bridge is a plain blue box truss where the photograph is a riveted Beaux-Arts portal, so the one thing the view exists for is the thing least well modelled**

## Re-rendered 2026-09-07 — a mandated viewpoint, and it is recognisable

Washington Street framing the Manhattan Bridge's Brooklyn tower is one of the seven viewpoints the
brief names, and this frame is the thing it is a picture of. The tower stands centred in the gap
between the warehouse blocks at its recorded 160 m, with the truss, the portal bracing and the
suspender cables reading correctly; `b_manhattan_bridge` and `b_brooklyn_bridge` are both in the
scene. The brick blocks flank it with their fire escapes zig-zagging down, a sidewalk shed runs along
the left frontage, a white van stands at the far kerb and a hydrant beside it. 28 mm on a portrait
frame, azimuth 357.1° — very nearly due north, which is what Washington Street runs.

The street trees are **bare**, correctly: `leaf_off` is set from the reference photograph's own date,
so the 223 trees here carry the kit's winter variants.

**What is weak is the bottom half of the frame.** The eye is 1.6 m over a roadway at z 5.07 m and
the lens is portrait, so roughly the lower 45 % is empty asphalt with no texture and no markings.
The real photograph of this view is famous partly for the cobbled street leading the eye to the
tower; here the street is a flat grey plane. That is the pavement-material gap, not a camera fault.

**And a correction to something I wrote an hour ago.** In deviation I17 I said the 2.6 m object in
this camera's view cone was a zelkova, taking the example from `view_distance`'s docstring rather
than from this scene's own record. It is `prop_lamp_cobra_davit_1`, a lamp standard. Both are stepped
past by the same rule — it counts only building shells and landmark models — but the record says
which, and I should have read it.

## What matches

* The camera stands on the photograph's own EXIF GPS, 35 m from the item's nominal viewpoint, which is what put it on Washington Street's roadbed rather than on Water Street. Before that correction this frame was a picture of a brick wall.
* The street is right: Washington Street's roadbed width, the kerb line, the sidewalk on the east side and the way the block faces close in toward the bridge all match the photograph.
* The warehouse walls are the right height, the right mass and the right colour family — deep red brick on the left, pale brick on the right — and they carry modelled fire escapes on the left wall in the same position and rhythm as the reference's.
* A sidewalk shed with green netting runs along the left wall at ground level, matching the scaffolding in the photograph's left foreground.
* The Manhattan Bridge is present as a placed landmark model 160 m away, at the right height, crossing the street at the right skew, with its suspension cables and stiffening truss visible.
* The Sun is from the photograph's own EXIF instant (2024-11-23 14:17:56 EST, elevation 18.9 deg, azimuth 218.4 deg), and the low warm afternoon light raking the right-hand wall matches the reference's.

## What does not match

* The bridge tower is wrong in kind. The reference shows the Brooklyn tower's steel portal — a pointed arch, four finial-capped columns, lattice bracing, riveted plate — filling the top half of the frame. The render's model is a smooth pale-blue box truss with a single X-brace and no arch, no columns, no finials, no rivets.
* The tower does not frame the street. In the photograph the arch straddles Washington Street with the Empire State Building visible through its opening 5 km away; in the render the bridge crosses to the right of the axis and no opening is presented, so the composition the viewpoint exists for cannot happen.
* The lens is honest but different: 28 mm level, against the reference's roughly 60 mm tilted up. That is stated on the sheet — a level axis is the only way to compare proportion — but it means the render gives about twice as much roadway and half as much tower.
* The brick walls have no texture. They are flat base colours with window openings cut as unglazed dashes: no mortar, no sill, no lintel, no reveal shadow, no glass, no variation between units.
* A bare street tree renders as an opaque black cone in the middle of the roadway. 17 impostor cards were dropped in this frame; what remains is branch geometry dense enough to read as a solid.
* The reference's autumn trees at the end of the street, the parked cars, the pedestrians, the One Way sign, the traffic signal and the standing scaffolding at the far corner are all absent.
* The roadway is bare: no lane lines, no crosswalk stripes, no manhole rings visible at this angle, no tyre polish, no patching.
* The bottom 40 % of the frame is flat dark asphalt with no texture at all.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the bridge tower has no portal, arch or riveted detail | the b_manhattan_bridge landmark model is a simplified truss; its towers carry no architectural detail | geometry |
| the tower does not frame the street | consequence of the simplified model: the arch opening is not modelled at all | geometry |
| wider, level framing than the reference | a level optical axis is required to compare proportion; the reference is a tilted long lens. Stated on the sheet | camera |
| untextured brick, unglazed windows | shells carry a per-material base colour; no facade texture, no glazing, no sill or lintel geometry | material |
| tree reads as a solid cone | the leaf-off branch model is dense and untextured | material |
| no cars, no people, no signs | no traffic, crowd or street-sign placement feeds the verification scene | data |
| featureless asphalt | the pavement material is a flat colour per kind with no texture map and no markings | material |
