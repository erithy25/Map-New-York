# 432 Park Avenue (Billionaires' Row)

`landmark_432_park_avenue` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Park Av Nov 2025 03.jpg by Epicgenius, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2025-11-05 08:43:50, 1920x1440. [Commons page](https://commons.wikimedia.org/wiki/File:Park_Av_Nov_2025_03.jpg)

**Camera** — 40.758178, -73.972882 (NYC_TM -1932, 6461) at z 18.2 m NAVD88 | azimuth 18.2°, pitch +0.0° | 35 mm on 36 mm (54.4° horizontal) | 1208x906.

**Sun** — azimuth 134.7°, elevation 20.3° at 2025-11-05T08:43:50-05:00 (EXIF DateTimeOriginal); 657.6 W/m² direct normal, sky at strength 0.0404, Filmic, +5.54 stops.

**Subject** — 432 Park Avenue at 400.1 m.

**In the scene**, within 900.0 m of the camera and not all of it in frame — 8 building tiles (324,428 tris), 20 landmark models of which **5 can fall inside the 54.4° frame**, 37,770 pavement polygons (21,440 white, 4,950 sidewalk, 4,444 roadbed, 4,049 curb, 1,143 plaza, 1,077 crosswalk, 548 median, 112 yellow, 7 parking lot), 512 props of the 6,132 in range, 2,473 kit pieces, 58 vehicles and 306 people; 4,500,286 triangles. Ground mesh 102,984 triangles, 0 holes. 19 city surfaces are dressed from the shared photographic catalogue.

| | render | photograph | ratio |
|---|---|---|---|
| mean | **0.4481** | **0.4714** | **0.951** |
| sd | **0.218** | **0.2781** | **0.784** |
| p05 | **0.1133** | **0.0445** | — |
| p50 | **0.4985** | **0.4821** | **1.034** |
| p95 | **0.786** | **0.9211** | — |
| chroma | **0.0979** | **0.0732** | **1.337** |
| exposure_offset_stops | **0.240** | **0.136** | **0.104** |

## Verdict — the same avenue from nearly the same spot, but the tower the sheet is named for is not in the render, and the record's verdicts that say it is were measured on its neighbour

**The render does not contain this tower, and the record says so in a figure nobody reads.** The
height probe cast **43 rays** and found built fabric on **5**, at **120.89 m** above a ground of
14.17 m, on `t_-2_6_glass_curtain` — a **tile mesh**, which is every glass-curtain building in that
square kilometre rather than one building. The landmark catalogue's **93** entries do not include
432 Park Avenue, so the subject has no model of its own; what the probe found is whatever
glass-curtain mass stands near the coordinate, 121 m up, and the sheet cannot say whether that is
the tower's own shell or a neighbour's roof. The nearest catalogue origin is `c_lever_house`
**253.3 m** away and was correctly refused (J74).

**Then the sightline tested that mass, and the arithmetic of the fan is the whole story.** With no
usable plan extent — the record's own note: *"a tile mesh is every building of one material in the
tile, so its extent is not the subject's and is not used"*, the measured 1,327.4 m being the widest
extent in the corpus — the fan falls to the **12 m floor** at a range of **404.1 m**. That is a
horizontal half-angle of **0.85°**, and at the **16.5 m** where `prop_lamp_cobra_davit_1` stands the
fan is **0.49 m wide**. A lamp mast covers most of half a metre. Twelve of thirteen rays stop there
and the published fraction is **0.077**.

**That is not this sheet's bad luck, it is the shape of the test.** Across the corpus, **35 of the
93** records that name what stopped the subject rays name a cobra-head street lamp — more than tile
shells (27), trees (19) and landmark parts (11) — because a fan sized for a distant subject is a
few tens of centimetres wide where the lamps are, and every kerb has one. On sheets whose fraction
is high the lamp is harmless bookkeeping: `landmark_port_authority_bus_terminal` names one at 21.3 m
with **0.923** of its rays arriving. On the eight sheets that report one ray or none — this one, the
DUMBO Manhattan Bridge view at **0.000**, the Brooklyn Public Library, the NYPL, One57, Madison
Square Garden, Carnegie Hall and Lever House — the lamp is most of the loss. J111 named this in its
headline (*"a single lamp post accounts for 11 of 13 rays"*) and repaired the sidestep's ranking;
the sidestep only runs when a prop stands at the lens **on the view axis**, and here `moved` is
false because the view azimuth is clear for **150 m**. Nothing moves the camera for a lamp that
stands beside the axis and across the fan.

**This is a pairing of Park Avenue, not of 432 Park Avenue.** Both halves look north up the avenue from the Seagram block at 52nd Street: the photograph from the Seagram plaza (its sunken pool and fountain are at the bottom right), the render from the photograph's own GPS, **25.3 m** from the item's recorded viewpoint on the median, and the picture shows the camera in the roadway with the Seagram's dark curtain wall filling the right third. The heading, **18.2°**, is the bearing from that GPS to the subject's coordinate; the item's own **14.6°** is **3.6°** off. In the photograph the tower is unmistakable: a white concrete shaft ruled into a square grid, rising through the top of the frame above the blue-green slab on the left. In the render, at that bearing, there is a stack of overlapping grey and navy glass slabs cut by the top edge of the frame, and nothing that reads as a slender white gridded tube. **Nobody should cite this sheet as evidence that the build contains 432 Park Avenue.** It does — the Billionaires' Row composite models the tower on its real footprints, with its square tube and six-a-side window grid — but that model is not what this frame shows.

**The record's height and sightline verdicts are true of the wrong building.** The height probe casts **43** rays about the subject's coordinate, lands **5** on built fabric, and reads **120.89 m** off `t_-2_6_glass_curtain` — a tile mesh, every glass-curtain building in the tile, whose plan extent (**1063.5 × 1047.1 m**) the record declares unusable. The subject coordinate stands east of the tower's footprint, on the Park Avenue frontage, so the probe measured a neighbouring glass block; the nearest catalogue origin was **253.3 m** off, so nothing checked the reading against the composite's published height, several times larger. This is the J57/J75/J82 shape — a correct measurement of something other than the thing it stands for — and J74 lists 432 Park Avenue among the subjects whose coordinate falls off any model origin. The sightline inherits it: **1 of 13** rays lands at **386.5 m** on the same tile mesh, so `subject_visible` is true by the J78 rule at a fraction of **0.077**, with the fan **120.1 m** tall and the **12 m** floor across. The blocker named for the other rays, `prop_lamp_cobra_davit_1` at **16.5 m**, is the lamp standard just right of centre; a lamp is not a wall and is not why the tower is missing.

**Why it is missing is the composition of three rules.** The axis is level because anything 400 m away is photographed level; the photograph is not — its verticals converge hard, because the photographer tilted up to hold the tower. The lens stayed at **35 mm** because the containment logic was given a 120.89 m subject that fits a level frame (vertical half-angle **8.45°**, aimed at a mid-height of **60.1 m**). And the tube, mid-block between Park and Madison, stands behind the taller avenue frontage; at the top of the render there is only a pale sliver just left of centre where it would be, with no grid resolved. With the true height, I18's rule would have widened the lens and declared a tilt; the composite's presence in the frame's cone (**732.3 m** to its origin) is not a visibility test.

**The lighting is metered and the number to read is +5.54 stops.** A November sun at azimuth **134.7°**, elevation **20.3°**, puts the west roadway in the shadow of the east-side blocks; the linear median was **0.003868** and the scene needed **+5.54** stops against **+1.10** for the physical rule alone: under-lit, the record says. The photograph was taken under full overcast — white sky, no shadow — and its exposure sits **0.136** stops from the same convention, the render's **0.240**. The ratios (**0.951** mean, **1.034** median) are the metering agreeing with itself, not evidence about the city.

## What matches

* **The street and the vantage.** North up Park Avenue from the Seagram block in both halves: the avenue's width, the dark curtain-wall tower at the right (the Seagram model at **69.3 m**, **45.2°** off axis), a crosswalk at the left, a wall of glass towers closing the view.
* **The kind of fabric.** Dark bronze-black glass on the right, blue-green and grey slabs on the left, a brown-brick block with a street tree at the far left; **2,471** kit windows.
* **A weekday morning crowd.** **306** people and **58** vehicles drawn for a weekday at 08:00, on the crosswalk, the median and in a lane.

## What does not match

* **The tower is not in the render.** The photograph's subject rises out of the top of its frame; the render's centre is anonymous glass slabs, and the record's 120.89 m belongs to a neighbour (**5 of 43** rays, on a tile mesh).
* **The pitch.** The photograph's verticals converge; the render's axis is **+0.0°** by rule, so its top edge sits far lower on the skyline.
* **The foreground.** The photographer stood at full height on the Seagram plaza, its paving and pool below the eye. The render's eye is at **18.19 m** over a ground chosen at **16.59 m** (10th percentile, street mode) while the DEM at the point reads **17.58 m**, so the median's raised surface sits barely half a metre under the lens and fills the lower half of the frame as a featureless pale plane.
* **Sky and light.** Overcast in the photograph (p95 **0.9211**), clear in the render (p95 **0.786**, sun on the brick block at the left); chroma **0.0979** against **0.0732**. Exposure offsets **0.240** against **0.136**; the p05 gap (**0.1133** against **0.0445**) is the shadow floor lifted by the **+5.54** stop development, just above the photographs' JPEG floor.
* **The season.** The photograph's trees are in autumn colour on 5 November and everyone wears a coat; the render's **117** trees (42 species substituted) are in full leaf and the crowd includes shorts and a sleeveless top.
* **The traffic.** A queue of taxis and cars fills the photograph's roadway; the render has one sedan (**558** vehicles dropped for budget, **208** pedestrians as in the carriageway).
* **Facade detail.** The photograph's right-hand tower has planted setback terraces and a lit shopfront base; the kit placed **2,471** windows, **2** quoins, nothing else.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the tower is not in the render | the subject coordinate stands off the tower's footprint, so the probe measured a neighbouring tile block at 120.89 m and the lens, aim and sightline all worked from that; the real tube is in the Billionaires' Row composite, behind the frontage at level pitch | **DEVIATIONS J57/J75/J82** shape, via **J74**; verification |
| `subject_visible: true` for a tower not in the picture | one of 13 rays lands on the tile mesh the height came from; the rule tested the neighbour | **DEVIATIONS J78**; verification |
| level pitch against a tilted photograph | the pitch rule assumes a distant subject is photographed level; a true height would have widened the lens and declared a tilt | **DEVIATIONS I18**; stated choice |
| the median's surface fills the lower half of the frame | street-mode ground takes the 10th percentile of a heightmap that carries the raised median; the GPS put the camera in the roadway, the picture was taken from the plaza | verification; reference |
| clear sky against an overcast photograph | the instant is lit under a clear sky; the record carries no weather | data |
| development at +5.54 stops | a shaded avenue canyon at 08:43 in November; the stops are the measurement | **DEVIATIONS J83** — (not a gap) |
| summer trees and a summer-dressed crowd | no season in the tree instancing; the snapshot request carries hour, day type and seed but no temperature for J53's wardrobe rule | data |
| one sedan where the photograph has a queue | placement is city-wide and the frame is not; the budget dropped 558 vehicles | performance |
| a window grid where the photograph has terraces and shopfronts | the shell is extruded from a footprint; the kit here is windows and two quoins | geometry |

## Measured for this assessment

Three figures above are not in this render record and cannot be: two are other sheets', quoted
because the finding they support is a corpus finding and one sheet cannot size it, and one is the
count of sheets that share it.

| figure | where it comes from |
|---|---|
| 0.923 | `sightline.subject_visible_fraction` in `landmark_port_authority_bus_terminal`'s record, beside a lamp named at 21.3 m — the counter-example that shows a named lamp is not by itself a loss |
| 21.3 | `sightline.subject_blocked_at_m` in that same record |
| 35 | the count of records whose `sightline.subject_blocked_by` names a `prop_lamp_*`, over the 93 that name a blocker at all: 27 name a tile shell, 19 a tree, 11 a landmark part and 1 another prop |
