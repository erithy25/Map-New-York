# Carnegie Hall

`landmark_carnegie_hall` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:W 57th St Dec 2020 52.jpg by Epicgenius, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2020-12-06 14:05:26, 1920x1440. [Commons page](https://commons.wikimedia.org/wiki/File:W_57th_St_Dec_2020_52.jpg)

**Camera** — 40.766202, -73.981713 (NYC_TM -2680, 7372) at z 25.2 m NAVD88 | azimuth 128.7°, pitch +7.0° | 35 mm on 36 mm (54.4° horizontal) | 1208x906.

**Sun** — azimuth 213.6°, elevation 19.0° at 2020-12-06T14:05:26-05:00 (EXIF DateTimeOriginal); 637.1 W/m² direct normal, sky at strength 0.0416, Filmic, +5.73 stops.

**Subject** — Carnegie Hall at 210.8 m.

**In the scene**, within 900.0 m of the camera and not all of it in frame — 9 building tiles (422,470 tris), 11 landmark models of which **5 can fall inside the 54.4° frame**, 30,501 pavement polygons (15,155 white, 5,406 sidewalk, 4,596 roadbed, 3,225 curb, 747 crosswalk, 652 median, 590 plaza, 92 yellow, 38 parking lot), 1141 props of the 6,395 in range, 2,523 kit pieces, 73 vehicles and 243 people; 4,500,072 triangles. Ground mesh 98,210 triangles, 0 holes. 20 city surfaces are dressed from the shared photographic catalogue.

## Verdict — Carnegie Hall is in neither half: the photograph is of the Argonaut Building, and the render holds one ray's worth of the hall behind a slab

**The two halves are not a pairing of the subject.** The photograph's own Commons description says what it is: *224 West 57th Street (the Argonaut Building)*, with *Carnegie Hall Tower, 888 Seventh Avenue and 220 West 57th Street* at the left. That is the picture: a cream limestone corner block filling the frame from shopfront transom to gabled parapets, a small ornate house and a dark glass tower to its left, a tan brick tower at the top-left edge. Carnegie Hall is not in it. The chooser found the file by the search *"Carnegie Hall" building 57th Street*; its GPS lies **196 m** from the hall, inside the **250 m** geosearch, and the azimuth **128.7°** is the bearing from that GPS to the hall (`camera_gps_to_subject`): the "high" confidence is about the GPS, not about what the picture contains, and the direction is not derived from the image. The photographer stood on Broadway north of 57th Street and tilted up at a building across the corner; the render stands on the same GPS walked **19.4 m** onto a crosswalk, aimed **+7.0°** down a street canyon at a subject **210.8 m** off.

**The record puts the hall in the render, barely, and the picture agrees with the fraction, not the boolean.** The model is there: the height probe lands **43 of 43** rays on `lm_c_carnegie_hall.7` and reads **55.31 m**, against **55.2 m** published by `c_carnegie_hall` **10.8 m** away. The fan, sized from that height and a **45.3 m** plan extent, sends **13** rays; **1** lands on the subject at **228.5 m**, so `subject_visible: true` on the J78 rule, fraction **0.077**. The central ray is stopped at **23.1 m** by `prop_lamp_cobra_davit_4`, the cobra-head arm crossing the axis in the middle of the render (the prop-blocker shape of J78); the walk was scored on this sightline (J79) and accepted it. At **6.0°** right of the axis, where the record places the hall at **217.2 m**, the render shows a windowless dark-brown slab running out of the top of the frame, a white mid-rise with three columns of punched windows below and right of it, and the lamp arm in front; nothing there reads as Roman brick and terracotta arches. Twelve rays did not reach the hall; the record names only the lamp, and not where the one hit falls.

**What the reader must not take from this sheet** is a judgement of Carnegie Hall's model, of the Argonaut's carving, or of the tone level. The render is developed at **+5.73 stops** where the physical rule alone gives **+1.19**, on a linear median of **0.003385**, and the record's own note calls the scene under-lit — a canyon under a Sun at **19.0°** almost square to the view. The photographer exposed **0.163** stops above the middle-grey convention, the render sits at **0.234**, **0.071** apart; the matched means, **0.5304** against **0.5068**, are the metering's doing (J83). The scene's own difference is contrast: standard deviation **0.2025** against **0.289**.

## What matches

* **Position, heading and instant are the photograph's own**: GPS, bearing-to-subject, EXIF second. The item's nominal viewpoint, **233 m** away with its **30.0°** azimuth, is not used, and the sheet says so.
* **The general direction.** Both halves look east-south-east along the 57th Street corridor with tall slabs closing the middle distance; the render's vanishing point sits in the left third of its frame, a little right of the street's axis, as the bearing requires.
* **Sunday, December, and the furniture of the street.** The crowd is drawn for the Sunday profile, the trees are leafless (**211**), and the render has cobra-head lamps (**119** in the scene), a hydrant, lane lines, a construction barrel and a yellow taxi in the queue ahead.
* **The palette.** Chroma **0.0668** against **0.0742** (**0.9**): a grey December street of limestone, brick and glass.
* **A BANK sign on the render's nearest left storefront**, where the Argonaut's ground floor is a TD Bank; the record does not say what placed it or on which building, so noted, not claimed.

## What does not match

* **The subject.** Left, the Argonaut Building; right, a canyon in which the hall is **1** ray of **13**.
* **Pitch and framing.** The photograph is tilted up hard enough that the Argonaut's verticals converge; the render is pitched **+7.0°** at the subject's mid-height **27.3 m** up, its lower half pavement and roadway.
* **Carved limestone against brick with proud frames.** The photograph's facade carries arched top-storey windows under three gabled parapets, pinnacled pilasters and a modillioned cornice. The render's nearest facade, at the left edge, is red brick with pale window surrounds standing proud of an unbroken wall (J51); across the whole scene the kit places **2,311** windows, **8** cornices, **5** pilasters and **8** string courses.
* **Light and shade, measured.** Sampled with PIL on `render.png`: the sky, the foreground pavement, the roadbed and one pale tower near the vanishing point are the only surfaces whose display luminance exceeds **0.7**; the near facades on both sides sit under half that, and the pavement beside the nearest figure's feet and the hydrant carries no cast shadow: the foreground is in the canyon's shade, lifted by the development. In the photograph the Sun flares the upper right of the sky and the glass towers reflect it.
* **The development, as stops**: **+5.73** metered against **+1.19** physical; exposure offsets **0.234** against **0.163**. The photograph's blacks — the dark glass of 888 Seventh Avenue, the shaded shopfronts — have no counterpart in a render whose p05 is **0.2301** against **0.0834**; p95 **0.9313** against **1.0**.
* **The crowd and the traffic.** The photograph holds no people and no vehicles. The render's lower half holds seventeen figures and six vehicles, counted at full size: seven on the near pavement, two at the kerb by the barrel, eight under the far shed. The nearest is a bare-armed figure in a sleeveless hi-vis vest at the centre of the foreground, on a December afternoon; `nearest_agent` is null after the cull, the walk's note named `agent_ped_3160.2` at **2.5 m**, and **8** pedestrians were culled over the observer after the move. The record carries no temperature for J53's wardrobe rule.
* **A sidewalk shed the length of the far block** (**69** scaffold pieces in the scene); the photograph's block has none, and the record carries no source or date for it.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the photograph is of the Argonaut Building | chosen by search term and a 250 m GPS radius, azimuth by bearing-to-subject, no test of what the picture contains — the shape of **DEVIATIONS J60**, inside its radius | reference |
| the hall is 1 ray of 13 in the render | a lamp at 23.1 m takes the central ray (**DEVIATIONS J78**), nearer fabric the rest; the walk scored on this sightline (**DEVIATIONS J79**) from the photographer's own position | verification |
| the photograph tilted, the render at +7.0° | I18: pitch aimed at the subject's mid-height and declared; the tilt is the photographer's, at another building | stated choice |
| carved limestone against brick with proud frames | tile shells are extruded footprints; kit windows stand proud of an uncut wall (**DEVIATIONS J51**); gables, pinnacles and a modillioned cornice have no source in the kit | geometry |
| foreground in shade, no cast shadows | a Sun at 19.0° almost square to the view, in a canyon | — (not a gap) |
| +5.73 stops against +1.19, offsets 0.234 / 0.163; a floor of 0.2301 where the photograph has blacks | metered development (**DEVIATIONS J83**), lifting diffuse shade to mid-grey in a frame with no dark glass: a statement of the light, not a fault of the city | — (not a gap) |
| seventeen figures and six vehicles against none | the simulation's own Sunday crowd and traffic for the hour; placement is city-wide and the frame is not | verification |
| a sleeveless figure in December | no temperature in the record to check the wardrobe rule (**DEVIATIONS J53**) against | verification |
| a sidewalk shed on the far block | scaffold placed from the kit's own records, undated in this record | data |
