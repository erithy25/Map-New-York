# Queens residential block: Forest Hills Gardens

`drive_queens_forest_hills` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Homes in Forest Hills Gardens 05.jpg by XanderAi, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2024-09-26 16:04:15, 1920x1081. [Commons page](https://commons.wikimedia.org/wiki/File:Homes_in_Forest_Hills_Gardens_05.jpg)

**Camera** — camera 40.71761, -73.84488 (NYC_TM 8882, 1961) z 23.4 m NAVD88 | azimuth 140.0deg pitch +0.0deg | 35 mm on 36 mm (54.4deg horizontal) | 1280x720. View direction: 140.0 deg as recorded in meta.json.  This item names no subject and the reference photograph's own view direction was not derived from the image (confidence: medium), so the two halves of this sheet are not guaranteed to face the same way -- compare them on street width, storey height and material, not on composition. Aim: level optical axis (the reference names no subject to aim at).

**Sun** — azimuth 239.6°, elevation 28.3° at 2024-09-26T16:04:15-04:00 (EXIF DateTimeOriginal).

**In frame** — 4/4 building tiles (240,420 tris), 0 landmark models, 2,193 pavement polygons, 298 props, 2,787 facade-kit pieces; 2,284,011 triangles; ground mesh 211² at 2.0 m near / 40.0 m far.

**Verdict — the single clearest demonstration in the set of what a flat-capped extruded footprint costs: Forest Hills Gardens is steep tiled roofs, half-timbering, casements and brick, and the render is white boxes with flat tops**

## What matches

* The camera stands on the photograph's own EXIF GPS, 222 m from the item's nominal viewpoint, at 23.4 m NAVD88 on a 21.8 m surface, and the new point-sample ground rule was used because the note names a terrace.
* The block layout is right: detached and semi-detached houses set back behind a continuous front boundary, with a narrow roadway and generous verges, which is the Forest Hills Gardens plan.
* A brick chimney stack rises above the roofline at the right scale, and a hedge line runs along the front boundary — both are real features of this street.
* A large street tree stands at the kerb with a correct trunk and canopy, 14 impostor cards dropped.
* 2,193 pavement polygons place the roadway, both verges and 493 crosswalk polygons at the right widths.

## What does not match

* Not one roof is pitched. Every building in the render is a flat-topped extrusion; the reference is a steeply pitched clay-tile roof with three gables, a catslide over the entry and a dormer. This is the defining feature of the neighbourhood and none of it is present.
* No brick. The walls are flat white and pale pink; the reference is a warm variegated brick with a stone plinth, timber framing to the gable and a stone-mullioned bay.
* No windows of any kind on the visible faces: no casements, no leaded lights, no sills, no reveals. The render's openings are a handful of pale dashes.
* No half-timbering, no bargeboards, no rainwater goods, no lamp brackets, no front doors.
* The green band along the boundary is a kit hedge rendered as a flat green pattern rather than planting.
* The reference's foreground — a stone garden wall with a planter and two chairs — has no counterpart; there is no garden furniture, no planting and no wall in any dataset the scene reads.
* No cars, no people.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| flat roofs where the neighbourhood is pitched | the shell builder caps footprints flat where it has no roof form; the tile manifest records fallback_flat_cap counts for exactly this | geometry |
| no brick, no timber framing | shells carry one flat base colour per material class with no texture | material |
| no windows, sills or doors | the facade kit placed 2,787 pieces in this scene but the visible faces carry none; low-rise residential facade classes are the thinnest part of the kit | geometry |
| hedge reads as a flat pattern | the kit hedge piece is an untextured card | material |
| no garden walls, planting or furniture | no dataset the scene reads carries residential lot furniture | data |
| no cars or people | no traffic or crowd placement feeds the verification scene | data |
