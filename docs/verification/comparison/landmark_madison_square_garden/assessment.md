# Madison Square Garden

`landmark_madison_square_garden` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Madison Square Garden 112.jpg by Zakarie Faibis, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2018-08-06 17:20:06, 1920x1440. [Commons page](https://commons.wikimedia.org/wiki/File:Madison_Square_Garden_112.jpg) — the photograph's own view direction is derived from the image at **high** confidence.

**Camera** — 40.750272, -73.991478 (NYC_TM -3491, 5607) at z 13.2 m NAVD88 | azimuth 278.9°, pitch +6.2° | 35 mm on 36 mm (54.4° horizontal) | 1208x906. The camera stands on **this photograph's own EXIF GPS**, 63.5 m from the item's recorded viewpoint, and was then **moved 25 m onto the nearest real sidewalk polygon** in `data/processed/roads/pavement`, because the recorded viewpoint was **boxed in**: the view azimuth closed off **17 m ahead** against the 80 m this frame needs. Candidates were ranked on how much of the subject each saw (J79). From the point chosen the view is clear for 96 m, and the nearest built thing in the frame is `prop_lamp_cobra_davit_5` **17.5 m** away at −9° yaw. The ground under it reads 11.649 m NAVD88, the **10th percentile of 113 samples within 12 m**, range 11.54 to 12.06 m.

**Sun** — azimuth 266.5°, elevation 29.9° at 2018-08-06T17:20:06−04:00, from the photograph's own **EXIF DateTimeOriginal**; 768.8 W/m² direct normal, sky at strength 0.0358, Filmic, **+1.27 stops**, measured from the linear frame's median of **0.074821** (J83). The physical rule would have given **0.53 stops**.

**In the scene** — 4,500,047 triangles: 7 building tiles (358,462 tris), 6 landmark models of which 4 fall inside the 54.4° frame, 27,399 pavement polygons, 2,285 props, 4,597 kit pieces, 22 park-ground meshes, **40,632 triangles of structures**, 53 vehicles and 276 people.

## Verdict — the best height agreement in the set, and a street lamp 18 m from the lens hides twelve of thirteen rays

**The arena's measured height and its catalogue height agree to within a tenth of a metre.** The probe casts **43 rays, all 43 landing on built fabric**, and reports **44.51 m** above a ground of 10.54 m against a catalogue height of **44.4 m** for a model whose origin sits **0.9 m** from the recorded coordinate. Nothing else in this pass agrees that closely. The drum is modelled, it is where it should be, and it is the right height.

**The sightline reports a visible fraction of 0.077, and that number is the sheet's most useful output.** Of 13 rays, **1 lands on the subject**; the other 12 stop at **18.0 m** on `prop_lamp_cobra_davit_5` — a cobra-head street lamp, which stands in the middle of the delivered frame with its mast across the arena's flank. The verdict is `subject_visible: true` on the strength of that single ray. Under the old rule this would have read as a clean pass; the fraction (J78) says instead that the view exists through a gap. That is the honest reading and the render shows exactly it.

**What the photograph is about is not in the render at all.** The reference is a view from under the marquee: a black canopy carrying `MADISON SQUARE GARDEN` in silver twice over, recessed downlights, the MSG Network sign, and a full-height advertising panel. **The render has a blank pale wall with a band of small square windows and a dark recessed slot where the entrance is.** No marquee, no lettering, no signage, no advertisement. Two **billboard** props were wanted in range and had no asset, along with 6 artwork and 15 vending machines.

## What matches

* **The height agrees with the catalogue** — — 44.51 m measured against 44.4 m recorded, from a model origin 0.9 m from the coordinate.
* **The view is the photograph's own.** Azimuth **278.9°** is the bearing from the photograph's GPS to the arena; the item's recorded azimuth is 299.1°, **20.2° away**, and was not used.
* **The arena is in the frame** at **169.8 m**, 7.7° off axis, and its flank fills the middle distance where the photograph's canopy is.
* **The neighbourhood's landmarks are all where they belong**: Moynihan Train Hall at **392.9 m** (7.6° off axis), Hudson Yards at **940.4 m** (15.3°) and the High Line at **1,102.5 m** (23.6°).
* **The rail infrastructure under this block is built.** **40,632 triangles of structures** — the largest structures count on any sheet in the set — which is what Penn Station's throat and the yard approaches actually are.
* **The camera was snapped to a real sidewalk.** Not to a heuristic offset but to a surveyed sidewalk polygon, keeping the eye height above the heightmap.
* **Seventh Avenue is dressed.** 27,399 pavement polygons — **11,976** white markings, 5,618 sidewalk, 4,355 roadbed, 3,317 curb, 1,039 plaza, 595 crosswalk — plus **33 subway entrances and 69 vent grates**, which is what the block above Penn Station carries.
* **The fleet is a Penn Station fleet on a weekday**: **25 yellow taxis, 9 black cars, 8 sedans, 7 boro taxis, 2 SUVs, an ambulance and an MTA bus**, with the crowd clock reporting **a weekday** for 2018-08-06, which was a Monday.
* **The crowd stands on the sidewalk in groups** rather than spread evenly, and the kerb-side furniture faces the kerb (J84).
* **Citi Bike is a station**: 568 dock units in range (Stage 40).
* **The tree by the kerb is drawn from modelled branches**, one of **13** within 120 m; 978 more are impostor cards out to 726 m.

## What does not match

* **The marquee, the signage and the advertising panel are all absent.** The photograph is of a sign; the render has a wall. 2 billboard props had no asset, and applied lettering is not a class this build models on a landmark shell.
* **The median is more than twice the photograph's** — **0.4993** against **0.2280**, a ratio of **2.19**, and the mean **0.4847** against **0.3618** (**1.34×**). Almost all of that is development: the photograph's own median sits **2.082 stops** below the middle-grey convention and the render's **0.245** above it, a difference of **2.327 stops** (J83). The photograph is dark because it was taken under a canopy in shade; the render is on an open sidewalk.
* **Two-thirds of the photograph's contrast.** Standard deviation **0.1952** against **0.3080** (**0.634×**), 95th percentile **0.7513** against **0.9855**. The reference holds a bright sky beside a black soffit; the render has neither extreme.
* **No traffic in frame** despite 53 vehicles in the scene: the view crosses a plaza and the carriageway is out of the cone.
* **The wall is undifferentiated.** **4,114 of 4,597 kit pieces are windows**, against **13 cornices, 13 string courses and 6 pilasters** in the whole scene. Kit was capped by a **1,107,721-triangle** budget with **14,808 pieces in range** — a fifth of what the frame wanted.
* **The crowd and fleet are a fraction of the table's ask.** The density table wanted **922 vehicles and 3,961 people** over the simulated ring; **1,083 and 2,999** were simulated and **3,751** dropped — **1,109 pedestrians and 432 vehicles at the agent triangle budget**, 1,137 and 533 outside the radius, 243 pedestrians for not being on a walkable surface, 232 for standing in the carriageway without crossing, 13 vehicles for not being on a carriageway and 2 pedestrians for being above the observer.
* **52 riderless bodies were dropped** — bicycles, e-bikes and pedicabs the fleet exports without a rider, the largest such count in the pass. Seventh Avenue at 32nd has a bike lane.
* **225 of 276 people and 44 of 53 vehicles are at LOD2**, their coarsest form.
* **There is no park ground within 150 m to check** — **0 samples** in the near band. Beyond 400 m, **0.2783 of 909 samples sit under the terrain**, minimum clearance **−8.083 m**.
* **5 of the 7 tiles in range have no structures file.**
* **The ground reads as one pale plane** across the near half of the frame, where 27,399 pavement polygons are recorded. The geometry is surveyed; at this grazing angle the authored base colours flatten it.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| no marquee, no lettering, no advertising panel | applied signage is not a class this build models on a landmark shell, and the 2 billboard props in range had no asset | **geometry + data — open** |
| 12 of 13 rays blocked by a street lamp 18 m from the lens | the clearance walk tests the view azimuth for obstruction and a lamp mast beside that axis passes; the fraction then reports 0.077 rather than a clean pass. The number is right and the viewpoint is poor | **verification — open, the walk should weigh near props** |
| p50 2.19×, mean 1.34× | the photograph is developed 2.082 stops under the grey convention and the render 0.245 over it, a 2.327-stop difference; the reference is a shaded frame under a canopy and the render is on an open sidewalk (J83) | reference |
| sd 0.634×, no highlight near white | the photograph holds sky beside a black soffit; the render has neither | reference |
| no traffic in frame | the carriageway falls outside the 54.4° cone from the point the walk chose | verification |
| 4,114 windows against 13 cornices | shells are extruded footprints with openings cut; kit capped at 1,107,721 triangles with 14,808 pieces in range | geometry + performance |
| 53 vehicles and 276 people against a table asking 922 and 3,961 | the agent triangle budget plus the placement rules, each with its count | performance + verification |
| 52 riderless bodies dropped | the fleet exports bicycle, e-bike and pedicab bodies without a rider | geometry |
| the near ground reads as one plane | surveyed pavement geometry with authored base colours at a grazing angle | data |
| 0.2783 of far park-ground samples under the terrain | surfaces draped on the 2 m heightmap against a scene edge coarsened to 40 m | verification |
