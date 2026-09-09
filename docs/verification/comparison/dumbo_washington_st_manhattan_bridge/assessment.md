# Washington Street in DUMBO with the Manhattan Bridge

`dumbo_washington_st_manhattan_bridge` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Manhatten Bridge - taken from Washington Street.jpg by David Kernan, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2024-11-23 14:17:56, 1920x3413. [Commons page](https://commons.wikimedia.org/wiki/File:Manhatten_Bridge_-_taken_from_Washington_Street.jpg)

**Camera** — 40.703061, -73.989602 (NYC_TM -3347, 341) at z 5.1 m NAVD88 | azimuth 1.4°, pitch +0.0° | 28 mm on 36 mm (39.8° horizontal, portrait) | 784x1394.

**Sun** — azimuth 218.4°, elevation 18.9° at 2024-11-23T14:17:56-05:00 (EXIF DateTimeOriginal); 636.0 W/m² direct normal, sky at strength 0.0417, Filmic, +5.00 stops.

**Subject** — Manhattan Bridge Brooklyn tower at 220.9 m.

**In the scene**, within 900.0 m of the camera and not all of it in frame — 9 building tiles (246,176 tris), 3 landmark models of which **1 can fall inside the 39.8° frame**, 28,793 pavement polygons (13,999 white, 4,944 curb, 4,076 sidewalk, 4,054 roadbed, 733 crosswalk, 282 yellow, 255 median, 226 parking lot, 224 plaza), 843 props of the 5,251 in range, 3,172 kit pieces, 85 vehicles and 376 people; 4,500,045 triangles. Ground mesh 96,800 triangles, 0 holes. 20 city surfaces are dressed from the shared photographic catalogue.

| | render | photograph | ratio |
|---|---|---|---|
| mean | **0.5799** | **0.5499** | **1.055** |
| sd | **0.1881** | **0.2506** | **0.751** |
| p05 | **0.3429** | **0.1424** | — |
| p50 | **0.4986** | **0.5812** | **0.858** |
| p95 | **0.9298** | **0.8803** | — |
| chroma | **0.069** | **0.1791** | **0.385** |
| exposure_offset_stops | **0.241** | **0.723** | **-0.482** |

## Verdict — the same view down the same street; the tower is measured right and modelled as a box truss; the record's `subject_visible: false` contradicts the picture and the record does not say why

**This is the view the item names, and both halves agree on that.** The camera stands on the photograph's own EXIF GPS, **34.6 m** from the nominal viewpoint, and looks along **1.4°**, the bearing to the Brooklyn tower; Washington Street's centreline bears **2.6°** from the same point, so the axis runs up the street as the photographer's did. The instant is the photograph's EXIF. In both halves the tower stands centred between two brick warehouse blocks, sky either side. The frames hold different amounts of it: the reference is a longer lens tilted up, so its bottom edge is street level at the tower's foot — the lower arch with the Empire State Building in it, autumn trees, a sidewalk shed, a stop sign, pedestrians — and it holds no roadway; the render is **28 mm** and level, so its lower half is asphalt. That is a declared choice, and the render's roadway must not be read as a mismatch of the city.

**The tower is measured off its own steel and is the right height; it is also a massing where the photograph is architecture.** The probe lands **43 of 43 rays** on built fabric and reads **107.38 m** off `lm_b_manhattan_bridge.214`; the catalogue publishes **106.68 m**, its origin **226.3 m** away, so the height comes from the geometry, as J74 asked. What that geometry is, the picture shows: a pale grey-blue portal of two plain box legs with two X-braces between them — a large one in the upper half, a smaller one just above the deck — a flat cap, two cables and a lattice deck. The photograph is the Beaux-Arts tower: a pointed arch between four finial-capped columns, tiered lattice bracing, riveted plates, the steel's south-west faces gilded by the sun, the Empire State Building framed in the opening. None of that is in the model, and beneath the render's deck the street ends in a pale untextured slab where the photograph shows trees and Manhattan through the arch.

**The record says the subject is not visible; the picture shows it filling the upper middle of the frame.** This is the post-J78 probe: the fan is **12.0 m** across (horizontal half-angle **1.52°**; the object measures **11.1 m**) and **107.4 m** up (vertical half-angle **13.35°**), aimed at mid-height **53.7 m** above the tower's ground at **226.2 m**, thirteen rays as a centre ray and three steps along four arms. A fan that narrow sits well inside Washington Street at the tower's range, so the canyon walls cannot take rays by construction as they did before J78. Yet **0 of 13** land on the tower; the record names only the nearest blocker, `prop_lamp_cobra_davit_1` at **5.5 m**, and does not say what stopped the rest. `false` must not be read as the tower being absent, and no cause is supplied here that the record lacks. Two other fields disagree with the picture: the lens reasoning speaks of a **102 m** tower at **172 m**, nominal-viewpoint figures against the probe's **107.38 m** at **220.9 m**; and the clearance probe reports no simulated agent within **60 m**, while a green boro taxi stands in the render's near right, a few metres from the lens.

**The light is metered, and the number to read it by is +5.00 stops.** The physical rule alone would have given **+1.20**; the linear median sat at **0.005639** and needed **+5.00** to reach middle grey, which the record flags as under-lit — more than the four a photographer recovers hand-held. That is a level camera on a shaded canyon floor with an 18.9° sun behind it, not a fault of the city. The photographer exposed **0.723** stops above the same convention, the render sits at **0.241**; that difference is the exposure choice first.

## What matches

* **The alignment, which is the whole of this viewpoint.** The subject coordinate sits on the tower centre, **1.9 m** from the bridge's carriageway; the one it replaced stood **62 m** from the tower (J75).
* **The height of the tower**: **107.38 m** measured against **106.68 m** published, on **43 of 43** rays.
* **The street is a DUMBO street**: five- and six-storey brick warehouse blocks, a black fire escape zig-zagging down the left wall as one does down the photograph's right wall, window rows, cornices, storefronts. **3,172 kit pieces**: **2,674 windows**, 242 storefronts, 31 cornices, 31 string courses, 35 scaffold pieces, 9 fire escapes.
* **The brick is photographic**: red on the left, tan on the right, courses and mortar, from the 20 dressed surfaces.
* **The road is drawn and marked**: a white dashed lane line, a manhole in the near carriageway; **4,054 roadbed, 4,944 curb and 4,076 sidewalk** polygons.
* **The trees are bare, correctly**: `leaf_off` from the photograph's date; **276 trees** at a mean scale of **0.903**, none out of band.
* **The crowd and fleet are the simulation's own**: 85 vehicles and 376 people for a Saturday at 14:17; a boro taxi, a sedan, a van and a few pedestrians in frame.

## What does not match

* **The tower has no arch, columns, finials or rivets.** The photograph is a portal; the model is two box legs, two X-braces and a flat cap.
* **Nothing is seen through the tower**, and the street beyond the deck ends in a flat pale slab.
* **The frame is flatter and far greyer.** Standard deviation **0.1881** against **0.2506** (**0.751×**); p05 **0.3429** against **0.1424**, far above the JPEG floor, so the render has no deep shadow; chroma **0.069** against **0.1791** (**0.385×**). Near-white haze against saturated cyan sky; grey against warm steel. Two surfaces still bind the albedo cap; one material family per facade class (J66).
* **The raking light barely reads.** A sun at **218.4°**, **18.9°** up, lights the right-hand block's upper storeys and the tower's south-west faces in the photograph and shades the left block; the render's two walls sit at almost one tone, as a **+5.00**-stop development does to a shaded canyon.
* **28 mm level against a longer tilted lens**, so half the render is roadway and none of the photograph is.
* **843 of 5,251 props placed** (budget 1,079,588 triangles), kit capped at 922,807, **10 impostor cards** dropped; 16 point props have no asset; **185 of 276 trees** species-substituted.
* **594 pedestrians dropped for standing in the carriageway**, 254 for not being on a walkable surface, 509 for budget; 68 vehicles for having no rider, 313 for budget.
* **The green sidewalk shed** runs along the render's left frontage; the photograph's stands at the foot of the right-hand block.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| no arch, columns, finials or rivets | `b_manhattan_bridge` is built to published dimensions without architectural detail | **geometry — the largest gap on this sheet** |
| nothing seen through the tower; a slab closes the street | the same simplification; an untextured block beneath the deck | geometry |
| flatter, greyer frame: sd 0.751×, chroma 0.385×, p05 0.3429 against 0.1424 | a +5.00-stop development lifts the shadow floor (J83); albedo cap and one family per facade class (J66) | material + **DEVIATIONS J83** |
| the raking light barely reads | a shaded canyon floor developed +5.00 stops | **DEVIATIONS J83** |
| 28 mm level rather than a long tilted lens | a level axis keeps the verticals comparable; 28 mm is the longest normal lens that holds the tower | stated choice |
| `subject_visible: false` on a frame the tower fills | 0 of 13 rays from a fan 12.0 m across, 107.4 m up; one blocker named, a lamp at 5.5 m; the rest unaccounted for | verification — **DEVIATIONS J78**'s rule, still against the picture |
| lens reasoning 102 m at 172 m against 107.38 m at 220.9 m | the lens string is written from the nominal viewpoint and catalogue, not the probe | verification |
| no agent within 60 m reported; a boro taxi in the near frame | the clearance probe and the agent snapshot do not describe the same test | verification |
| most props and part of the kit unplaced; 10 cards dropped; 16 props with no asset; 185 of 276 trees substituted | triangle budgets 1,079,588 and 922,807; no asset for 16 kinds, left unplaced; nearest species by size and taxon | performance + data |
| agents dropped in their hundreds | placement rules, each declared in the record | performance + stated choice |
| the sidewalk shed on the other side | permit data at the render's date against the photograph's November 2024 | data |
