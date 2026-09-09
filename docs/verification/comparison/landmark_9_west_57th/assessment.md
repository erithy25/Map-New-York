# 9 West 57th Street (Solow Building)

`landmark_9_west_57th` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:W 56 St Apr 2021 54.jpg by Epicgenius, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2021-04-24 15:16:17, 1920x2560. [Commons page](https://commons.wikimedia.org/wiki/File:W_56_St_Apr_2021_54.jpg)

**Camera** — 40.763821, -73.975878 (NYC_TM -2191, 7074) at z 18.4 m NAVD88 | azimuth 85.6°, pitch +25.4° | 18 mm on 36 mm (73.7° horizontal, portrait) | 904x1206.

**Sun** — azimuth 238.7°, elevation 48.4° at 2021-04-24T15:16:17-04:00 (EXIF DateTimeOriginal); 881.9 W/m² direct normal, sky at strength 0.0322, Filmic, +4.04 stops.

**Subject** — 9 West 57th Street (Solow Building) at 105.3 m.

**In the scene**, within 713.8 m of the camera and not all of it in frame — 4 building tiles (222,112 tris), 12 landmark models of which **1 can fall inside the 73.7° frame**, 26,996 pavement polygons (11,823 white, 6,671 sidewalk, 3,866 roadbed, 3,006 curb, 618 plaza, 536 crosswalk, 371 median, 57 parking lot, 48 yellow), 1287 props of the 3,818 in range, 4,765 kit pieces, 85 vehicles and 349 people; 4,500,030 triangles. Ground mesh 88,178 triangles, 0 holes. 19 city surfaces are dressed from the shared photographic catalogue.

## Verdict — the tower is in the frame and measured off its own fabric, but the photograph is of the townhouse in front of it and the halves do not face the same way

**The pairing shares a building, not a view.** The photograph's own Commons description says what it is: *17 West 56th Street*, a three-storey red-brick house with a limestone base, arched windows, a bracketed cornice and three dormers, seen square-on from across the street, with 9 West 57th Street "in the background". The Solow Building is there, a sheer dark-glass curtain wall filling the top-left of the photograph above the house, its mullion grid legible. The render looks a different way. Its position is the photograph's own GPS, **157.1 m** from the item's recorded viewpoint, walked **14.0 m** onto the nearest sidewalk because that spot was closed off at **36 m** against the **49 m** the frame needs (J79). Its heading, **85.6°**, is the bearing from that GPS to the subject's coordinate, not a direction read from the picture: the house is not in the render at all, and the street runs away obliquely to a vanishing point in the right tenth of the width. The photograph faces the north side of the street; the render faces along it. Not J60 (the fix is inside the **250 m** band and correct): a reference chosen for a category and a position, not for what it shows.

**What the record establishes about the building is sound.** The height probe drops **43 of 43** rays onto built fabric at the coordinate and reads **214.97 m** above a ground of **12.98 m**, off `lm_c_billionaires_row.54`, a piece of the West 57th Street corridor composite. There is no catalogue height to set against it: the nearest catalogue origin, `c_the_plaza` at **67.1 m**, publishes **76.2 m** for the hotel, so the probe is the only measurement of the Solow in the record. The sightline fan, sized to that height and to a plan extent of **89.8 m** by **79.3 m**, lands **11 of 13** rays on the subject, **1** into nothing, and names no blocker: `subject_visible` true at a fraction of **0.846** (J78), and the picture agrees: the tower's south face fills the left three-fifths of the render from bottom to top, its nearest fabric **47.5 m** from the lens.

**The frame is a declared tilt and the top is still cut off.** The subject's top stands **209 m** above the lens **98 m** away, **65°** above the horizon; the lens was widened to the **18 mm** floor (**90°** vertical), the axis tilted **+25.4°** (I18, declared in `pitch_reason`), and the tower still leaves the top edge. Both halves are tilted up, differently; nothing on this sheet compares proportion. The Sun is the photograph's own instant, at **238.7°** and **48.4°** up behind the camera's right shoulder, **881.9 W/m²** direct normal — but the photograph was taken under a white sky, its top-left corner clipped to full white over every pixel I sampled, the house carrying no cast shadow; the render has a clear blue sky and hard shadows.

## What matches
* **The Solow Building's south face is in both halves**, top-left in the photograph and the left three-fifths of the render, rising out of the top of both frames.
* **The height is measured off the building**, not off a model origin: **43 of 43** rays, **214.97 m** (J74); the sightline puts **11 of 13** rays on it and nothing in front of it.
* **The Plaza Hotel is where it should be**: **149.7 m** away at **29.9°** left of the axis, its green mansard at the render's left edge a third of the way down.
* **The instant is the photograph's own**, to the second; a Saturday, and the crowd was drawn for a Saturday.
* **A Midtown Saturday street**: **85** vehicles and **349** pedestrians placed, **35** of the vehicles taxis. In frame I count ten vehicles at full size (a white van in the right third of the width, seven cars and taxis behind it, two under the tower's base at the far left) and fourteen figures, most a few pixels tall; the photograph has four people and two vehicles.

## What does not match
* **The house is missing.** The render's foreground is the subject's own base and the sidewalk across from it.
* **The curtain wall is the wrong material and pattern.** The photograph shows a sheer dark blue-black glass wall with a fine mullion grid; the render's tower is banded storey by storey, warm-grey spandrel bands alternating with dark reflective strips. By my sampling the lit near face sits a little above middle grey, barely a tenth of its pixels above 0.7.
* **The slope cannot be read.** The photograph's wall leans out towards the ground; the render's left edge leans too, but at **+25.4°** every vertical converges.
* **The base does not meet the ground.** At the tower's foot, left of centre, pavement and two vehicles show through beneath the dark plinth.
* **Three grey boxes hang in the sky above the Plaza's roof**, a tenth of the width in from the left edge and a third of the way down, sky beneath them.
* **The foreground is bare** against **4,765** kit pieces and **1,287** props placed: no banner, awning, lamp arm or construction fence.
* **Lighting, as stops.** The scene metered **+4.04** stops to place its median at middle grey (linear median **0.010966**; the physical rule alone gave **+0.00**), and the record marks the frame under-lit. The developed render sits close to the photograph in tone: mean **0.4942** against **0.5188** (ratio **0.953**), exposure offset **0.23** against **0.423** stops, a difference of **-0.193**. Contrast differs: sd **0.2004** against **0.2707** (ratio **0.74**), p05 **0.2139** against **0.0849** — well past the JPEG floor, the photograph's ironwork and dark glass going much blacker — and p95 **0.773** against **1.0**, its sky clipped white. Chroma **0.0843** against **0.0701** (ratio **1.203**): blue sky and yellow taxis against an overcast grey picture.
* **Cast shadow where the photograph has none.** By my sampling the tower's lowest band in frame, below the tree crowns, is at about half the display luminance of the lit face above it, a shadow from the block behind the camera; the cream tower at the right edge is the brightest built surface, nearly half its pixels above 0.7. The photograph's brick, limestone and glass are lit flat.

## Cause of each gap
| gap | cause | class |
|---|---|---|
| the photographed house is not in the render; the halves face different ways | the picker matched a Commons category and a GPS 98 m from the subject; the heading is the GPS-to-subject bearing, 85.6°, and the item's recorded viewpoint (azimuth 10.0°) was abandoned for it | reference |
| banded spandrels where the photograph is a sheer dark curtain wall | the corridor composite `c_billionaires_row` carries one facade treatment across its pieces; the Solow's glass is not modelled as glass | material (the shape of **DEVIATIONS J66**, on a landmark model) |
| the slope cannot be judged; the top leaves the frame | axis tilted +25.4° at the 18 mm floor to reach a top 65° up; verticals converge by construction and 90° of field is still short | stated choice — **I18**, declared |
| pavement and vehicles visible under the plinth | the landmark model's ground storey does not close to the pavement polygon beneath it | geometry |
| three grey boxes in the sky above the Plaza | most likely rooftop props (**131** cooling towers placed) left at the datum of a tile shell whose faces were suppressed under the landmark model (**3370** faces suppressed here) | data |
| clear sky and hard shadows against a white sky and flat light | the Sun is computed from the EXIF instant with a clear-sky irradiance; the record holds no weather for the day | data |
| +4.04 stops metered, under-lit by the record's own rule; p05 and p95 gaps | the development is metered on the frame (a shaded street under a Sun behind the camera), against a phone JPEG that clips its sky and crushes its shadows | verification — **DEVIATIONS J83** |
| no banner, awning, lamp arm or fence in the foreground | the kit and prop sets carry no awnings or lamppost banners; construction fences are not a dataset | data |
