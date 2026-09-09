# Citigroup Center (601 Lexington Avenue)

`landmark_citigroup_center` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:601 Lexington Avenue 001.jpg by Kidfly182, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2022-12-12 12:16:34, 1280x1707. [Commons page](https://commons.wikimedia.org/wiki/File:601_Lexington_Avenue_001.jpg)

**Camera** — 40.758164, -73.971253 (NYC_TM -1795, 6459) at z 13.6 m NAVD88 | azimuth 58.9°, pitch +30.9° | 18 mm on 36 mm (73.7° horizontal, portrait) | 904x1206.

**Sun** — azimuth 186.9°, elevation 25.9° at 2022-12-12T12:16:34-05:00 (EXIF DateTimeOriginal); 729.0 W/m² direct normal, sky at strength 0.0376, Filmic, +5.33 stops.

**Subject** — Citigroup Center (601 Lexington Avenue) at 96.1 m.

**In the scene**, within 692.5 m of the camera and not all of it in frame — 6 building tiles (292,118 tris), 12 landmark models of which **3 can fall inside the 73.7° frame**, 28,588 pavement polygons (13,990 white, 5,125 sidewalk, 4,050 roadbed, 3,363 curb, 963 plaza, 738 crosswalk, 316 median, 40 yellow, 3 parking lot), 1011 props of the 3,987 in range, 5,207 kit pieces, 54 vehicles and 323 people; 4,500,081 triangles. Ground mesh 85,666 triangles, 0 holes. 19 city surfaces are dressed from the shared photographic catalogue.

## Verdict — the tower is in its own frame at the right height, and its skin carries diagonals the photograph shows are not there

**This is the same tower from the same side of it, and not the same picture.** The camera stands on the photograph's own EXIF GPS, **138.7 m** from the item's nominal viewpoint on Lexington at 52nd; its heading of **58.9°** is the bearing from that GPS to the subject coordinate — derived from the position, not read off the image; the item's recorded **20.0°** belongs to the nominal viewpoint and is not used. The instant is the photograph's EXIF to the second, a December Monday noon, Sun at **186.9°** and **25.9°** up. From there the photographer pointed a phone steeply up the tower's near corner: two faces of aluminium-and-glass banding meeting at a vertical edge a little under two-thirds of the way across, the black soffit of the tower's underside filling the bottom fifth, cloud-streaked blue sky either side. The render was widened to the **18 mm** floor and tilted **+30.9°** to hold a subject whose top stands **271 m** above the lens at **96 m**, **70°** above the horizon; the record says the verticals converge and the frame is not comparable on proportion (I18's rule, applied and declared). So the render shows what the photograph does not — Lexington Avenue, the four stilts, the neighbours, a black car and a kiosk in the foreground — with the tower filling the middle two-fifths of the width and its near corner, measured off the pixels, a little under two-thirds of the way across, where the photograph's corner also sits.

**The measurement of the building agrees with its catalogue.** The height probe lands **43 of 43** rays on built fabric at the subject's coordinate and reads **275.09 m** above a ground of **8.7 m**, off `lm_c_citigroup_center.7`; the catalogue origin `c_citigroup_center`, **38.3 m** away, publishes **278.9 m**. The sightline fan is sized from that measured height and a **65.0 m** plan extent (J74/J76): of **13** rays aimed at mid-height **137.1 m** up, **9** land on the subject, **3** go into the sky above it, one is stopped at **81.2 m** by `t_-2_6_metal_panel`, and **7** meet the tower's own base parts (`lm_c_citigroup_center.6` at **82.2 m**) nearer than the recorded distance: `subject_visible_fraction` **0.692**, `subject_clear_fraction` **0.923**. The verdict rule is one ray (J78); the fraction is what to read, and the picture agrees with it: the shaft rises from the stilts to a crown whose near-corner apex sits a few pixels under the top edge, the west gable's pale triangle beside it. The whole tower is in frame; the lens note's "still cut off" describes the level-axis case the tilt then resolved.

**What the reader must not take from the sheet: the render's tower wears its structure on the outside and the photograph says it does not.** The model's fidelity statement calls the chevron braces "expressed every eighth floor", and the render draws them — white diagonals crossing the shaft in bands on both visible faces. The photograph covers some forty floors of both faces at close range and shows continuous horizontal banding with no diagonal anywhere: an "Exact" claim refuted by the evidence it is paired with, and the register has no row for it. The under-lighting is not a fault of the city: **+5.33** stops against a physical rule of **+0.74**, marked under-lit in the record (J83), over a frame whose pixels are mostly a December noon street in the shadow of the blocks to the south.

## What matches

* **The massing.** A square shaft lifted clear of the ground on four mid-face stilts, a sloped crown, a low base block beneath; the photograph's near corner and black soffit are that corner and that underside from below.
* **The height.** **275.09 m** measured off the fabric with **43 of 43** rays against **278.9 m** published **38.3 m** away.
* **Camera and light are the photograph's own.** GPS position, bearing **58.9°** against the reference's estimated **58.8°**, EXIF instant, **729.0 W/m²** direct normal. Sampled on `render.png` (display luminance, PIL): the tower's right face, on the Sun's side, has a median above the **0.7** sunlit level, the left face just over it on the strength of its white grid; stilts and roadway read at about a third of that, and the soffit is the darkest built surface in both halves.
* **The nearest agent is where the record puts it.** `agent_veh_nova_lfs_mta_528.36` at **8.5 m**, **36.9°** right, is the grey MTA bus cut by the right edge of a **73.7°** frame; `prop_lamp_cobra_davit_0` at **3.2 m** is recorded at the same angle, behind the bus.
* **The neighbours are in the record.** The rounded red-banded tower at the right edge is consistent with the Lipstick Building at **205.8 m**, **39.4°** off axis with a **7.5°** half-width.

## What does not match

* **Diagonal braces on the skin.** White chevrons in bands up both faces of the render; none in the photograph over the forty-odd floors it shows. The model states them as exact.
* **The elevation's material and rhythm.** The photograph is flat brushed-aluminium spandrels alternating with dark ribbon glass, reflecting cloud; the render is a bright white mullion grid over blue-grey glass. The stilts are a dark textured grey-green, the catalogue's `concrete`; the photograph does not show them.
* **The frame.** Photograph: tower, soffit, sky. Render: **+30.9°** tilt at **18 mm** puts street, stilts, base, kiosk, car, bus and two curtain-wall neighbours in.
* **Which face is broad.** In the photograph the face left of the corner is the wider and the brighter — its median about half again the right face's (PIL); in the render the right face is the wider and the brighter. From bearing **58.9°** the right, Sun-side face should present more squarely, as the render has it; the photograph presents the other. The record holds one position, the GPS, and no second source to test it against.
* **Lighting as stops.** Development **+5.33** against the physical **+0.74**, more than the **4** a photographer recovers hand-held; linear median **0.004482**, p95 **0.146479**. The photographer exposed **0.406** stops above the middle-grey convention, the render sits at **0.239** (ratio **-0.167**); mean **0.5484** against **0.4942** (**1.11**), p50 **0.4983** against **0.5257** (**0.948**), p95 **0.9653** against **0.918**. p05 **0.1524** against **0.0348** is far above the JPEG floor and is framing: the photograph's bottom fifth is near-black soffit, the render's darkest pixels are shaded roadway.
* **Colour.** Chroma **0.0825** against **0.1416** (**0.583**). The photograph's colour is blue sky and glass reflecting it; the render's sky, pushed **+5.33** stops, is a pale near-grey against which only two taxis and the red-banded tower are saturated.
* **The crowd is the simulation's.** **54** vehicles and **323** people placed for a weekday noon; in frame I count ten vehicles (white truck, taxi, two dark cars at left; the black car and one behind it at centre; dark sedan, taxi, white van at right; the bus), five or six figures at the left kerb and four or five at the right. The photograph has no street.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| chevron braces expressed on the skin | the generator draws the bracing on the elevation and calls it exact; the photograph shows a smooth banded skin — not in the register | geometry |
| elevation material and rhythm | one `aluminium` and one `glass_blue` slot over a proud spandrel; no brushed-metal reflectance, spandrel-to-glass ratio not taken from the building | material |
| the frame holds the street and the neighbours | a **275 m** subject **96 m** away needs **70°** of elevation; the lens stops at **18 mm** and the axis is tilted **+30.9°**, declared (I18) | stated choice |
| which face is broad and bright | the GPS position and the heading derived from it; a GPS displaced across the corner faces the tower from a bearing the photographer did not | reference |
| **+5.33** stops of development | metered at middle grey over a December noon frame whose median pixel is shadowed street (**DEVIATIONS J83**) | verification |
| chroma **0.583** of the photograph's | grey sky after the push; one material family per facade class (**DEVIATIONS J66**) | material |
| a simulated crowd on a street the photograph does not show | agents are the simulation's for the hour, city-wide; the frame is not | verification |
