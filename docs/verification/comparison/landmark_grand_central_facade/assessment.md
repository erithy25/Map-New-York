# Grand Central Terminal facade

`landmark_grand_central_facade` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Grand Central Terminal December 2022 004.jpg by Kidfly182, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2022-12-12 11:51:16, 1920x1440. [Commons page](https://commons.wikimedia.org/wiki/File:Grand_Central_Terminal_December_2022_004.jpg) — the photograph's own view direction is derived from the image at **high** confidence.

**Camera** — 40.752117, -73.977783 (NYC_TM -2346, 5788) at z 18.1 m NAVD88 | azimuth 67.6°, pitch +0.5° | 19 mm on 36 mm (87.3° horizontal) | 1208x906. The camera stands on **this photograph's own EXIF GPS**, 80.2 m from the item's recorded viewpoint, and was **not moved**. The heading is the bearing from that position to the facade; the item's recorded azimuth is 30.5°, **37.1° away**, and belongs to its nominal viewpoint on Pershing Square. The lens was **widened from 35 mm to 19 mm** so a level axis could contain a subject that tops out **32° above the horizon** at 53 m, and the record declares that the verticals converge and the frame is therefore not comparable on proportion. The view azimuth is clear for 49 m; the nearest built thing in the frame is `prop_lamp_cobra_davit_97` 33.7 m away and the nearest simulated agent is `agent_veh_camry_black_car_1442.44` **8.7 m** from the lens at 29.1° off axis.

**Sun** — azimuth 180.4°, elevation 26.2° at 2022-12-12T11:51:16−05:00, from the photograph's own **EXIF DateTimeOriginal**; 732.4 W/m² direct normal, sky at strength 0.0374, Filmic, **+5.35 stops** — the largest recovery on any sheet in this pass. The linear frame's median is **0.004411** against the middle-grey target, and the record marks it **under-lit**: *"the scene needed +5.35 stops to read as a picture, more than the 4 a photographer recovers hand-held; the frame is published and this is the number to read it by."* The physical rule would have given **0.72 stops**.

**In the scene** — 4,500,236 triangles: 4 building tiles (197,492 tris), 6 landmark models of which 3 fall inside the 87.3° frame, 25,653 pavement polygons, 1,497 props, 5,932 kit pieces, 14 park-ground meshes, 53 vehicles and 250 people.

## Verdict — the closest colour agreement in the set, on a facade whose entire sculptural programme is missing

**Chroma **0.0513** against **0.0491**, a ratio of **1.045** — the two halves agree on colour to within five per cent, the best match measured anywhere in this pass.** Both are grey limestone under a flat winter light, which is the one condition in which authored base colours are not the limiting factor. It is also the least interesting thing about this pairing, because what the photograph is *of* is not in the render.

**The photograph's subject is the Glory of Commerce.** Mercury, Hercules and Minerva over the central arch, the thirteen-foot clock below them, `GRAND CENTRAL TERMINAL` incised across the entablature, the arched window with its iron grille, and a Christmas wreath with a red bow hung in the opening. **The render has a grey wall with paired engaged columns and a plain cornice.** No sculpture, no clock, no lettering, no grille, no wreath. The classical order is there in outline and nothing that is carved on it is.

**The measurement is honest about what it measured.** The height probe casts **43 rays** of which **41 land on built fabric**, giving **34.86 m** above a ground of 16.59 m — against a catalogue height of **45.8 m** for a terminal whose own origin sits **47.9 m** from the recorded coordinate. The object measured, `lm_grand_central_terminal.3`, has a plan extent of **124.6 m by 124.5 m**: the facade item's coordinate is standing on a block-sized piece of the terminal rather than on the 42nd Street front itself. The sightline then casts 13 rays, **11 clear**, **10 on the subject**, for a visible fraction of **0.769**, with the two blocked rays stopping at **24.7 m** on `prop_lamp_cobra_davit_37` — a street lamp. That verdict is right: the wall is visible. It certifies the wall, not the sculpture.

## What matches

* **The classical order is in the right place at the right size.** Paired engaged columns, entablature and cornice close the top right of the render as the facade fills the photograph, at 53.3 m on the photograph's own bearing.
* **The colour is the photograph's colour** — 1.045× on chroma, grey limestone against grey limestone.
* **The camera is the photographer's.** Its own EXIF GPS, 80.2 m from the nominal viewpoint, and the heading derived from that position rather than the item's 30.5°.
* **The camera stands on the traffic surface.** The ground under it reads 16.484 m NAVD88, the **10th percentile of 113 samples within 12 m**, range 16.37 to 16.89 m, because the viewpoint note places the photographer in the street and the 1 m DEM carries plinths that would lift the lens off it.
* **Three landmarks are inside the frame and all three belong there**: Grand Central at **83.1 m** (32.9° off axis), the MetLife Building at **184.3 m** (35.7°) and the Chrysler Building at **212.3 m** (36.6°).
* **42nd Street is dressed as 42nd Street.** 25,653 pavement polygons — **10,055** white markings, 5,477 roadbed, 4,717 sidewalk, 3,573 curb, 804 plaza, 621 crosswalk — and the crossing bars in the render's foreground are surveyed geometry.
* **Pershing Square's Citi Bike is a station, not a bicycle**: **623 dock units** in range, the largest count on any sheet, which is what this block actually carries (Stage 40).
* **The trees are bare and the date is why.** The reference is 12 December and the bare-canopy variants are selected from the photograph's own date.
* **The kerb-side furniture faces the kerb.** 150 street lamps, 22 bus-stop signs, 34 waste baskets, 22 subway entrances and 24 vent grates stand along the frontages with the kerb's heading (J84).

## What does not match

* **The sculptural group, the clock, the incised lettering, the window grilles and the wreath are all absent.** The facade is the subject and its ornament is the facade. **2 artwork props** were wanted in range and had no asset; architectural sculpture is not a class this build models at all.
* **The composition is inverted.** The photograph is filled by the facade; the render gives more than half its frame to the roadway, because a 1.6 m eye with a 19 mm lens at 53 m sees mostly asphalt. The photograph was taken looking up from closer in.
* **A manhole cover stands proud of the roadway** in the render's middle distance, a disc lying on the surface rather than set into it. 155 manholes are placed in this scene.
* **The frame needed +5.35 stops.** That is the record's own number and the largest in the pass. A 26.2° December sun at azimuth 180.4° behind a view pointing 67.6° leaves the Park Avenue canyon in shade, and the scene as lit is roughly forty times darker than the frame that was published from it.
* **Half the photograph's contrast.** Standard deviation **0.1510** against **0.2757** (**0.548×**), median **0.4997** against **0.4433** (**1.127×**), mean **0.5316** against **0.4786** (**1.111×**), 95th percentile **0.8044** against **1.0**. The photograph holds a blown highlight; the recovered render holds nothing near white.
* **No hard light anywhere.** Both halves are shade-lit, so this is not a sun-direction gap — but the render has no cast shadow to give the columns depth, which is part of why the wall reads flat.
* **The wall is a wall.** Rustication, the deep coffering of the arches, the bronze spandrels and the stone carving of the window heads are absent; the shells are extrusions with openings and a generic column profile.
* **Both triangle budgets were hit, and the kit budget hard.** Props were capped at **1,265,281** triangles and kit at **1,268,322** with **42,595 pieces in range** — this frame wanted more than seven times the kit it could draw. At the **1,125,000-triangle agent budget** a further **617 vehicles and 1,096 people** were dropped.
* **The crowd is a fraction of what was asked for.** The density table wanted **1,333 vehicles and 3,324 people** over the simulated ring; **1,564 and 3,000** were simulated and **4,261** dropped, leaving 53 vehicles and 250 people in frame. Midday at Grand Central is one of the densest pedestrian places in the city.
* **442 people were dropped for standing in the roadway without crossing**, 205 for no sidewalk, 50 vehicles for no roadway in the planimetric data, and **30 cyclists, e-bikes and pedicabs were not drawn** because the fleet exports those bodies without a rider.
* **1,164 tree rows did not fit the props budget**, and of the trees that did, only **12** are drawn from modelled branches within 120 m against **186** impostor cards out to 580 m.
* **Twelve vending machines, 4 drinking fountains, 3 misc structures and 2 passenger-information signs** were wanted in range and had no asset.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| no sculptural group, clock, lettering, grille or wreath | architectural sculpture and applied ornament are not classes this build models; the 2 artwork props in range had no asset. The shell carries the order and nothing carved on it | **geometry — open, no source for modelled ornament** |
| the subject's height reads 34.86 m against a catalogue 45.8 m | the recorded coordinate stands on `lm_grand_central_terminal.3`, a piece 124.6 m across, and the terminal's own origin is 47.9 m away; the probe measured the block, not the 42nd Street front | **verification — open, the item's coordinate** |
| the composition gives half the frame to the roadway | a 1.6 m eye at 53 m with a 19 mm lens; the photograph was taken closer and looking up | verification — declared |
| the frame needed +5.35 stops | a 26.2° December sun at 180.4° leaves a view along 67.6° in canyon shade; published under-lit and marked so (J83) | reference + verification — declared |
| sd 0.548×, no highlight near white | a frame recovered by more than five stops has no headroom left; the photograph holds a blown sky | reference |
| a manhole cover lies on the roadway rather than in it | the prop is placed at the surface without being inset | **geometry — open** |
| the wall has no rustication, coffering or carved heads | shells are extruded footprints with openings cut and a generic column profile | geometry |
| props and kit capped, 42,595 kit pieces in range against a 1,268,322-triangle budget | the per-frame triangle budgets, each named with what it dropped | performance |
| 53 vehicles and 250 people where the table asked for 1,333 and 3,324 | the agent budget plus the placement rules, each with its count | performance + verification |
| 30 cyclists not drawn | the fleet exports bicycle, e-bike and pedicab bodies without a rider | geometry |
| 1,164 tree rows dropped | the props triangle budget | performance |
| vending machines, drinking fountains, information signs unmapped | no asset exists for those kinds | data |
