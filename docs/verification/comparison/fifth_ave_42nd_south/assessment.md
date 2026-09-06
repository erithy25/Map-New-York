# Fifth Avenue at 42nd Street (NYPL), street view looking south

`fifth_ave_42nd_south` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:01-21-2017 - Women's March on NYC looking down 42nd (10794).jpg by Rhododendrites, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2017-01-21 13:41:20, 1920x1163. [Commons page](https://commons.wikimedia.org/wiki/File:01-21-2017_-_Women%27s_March_on_NYC_looking_down_42nd_(10794).jpg)

**Camera** — camera 40.75350, -73.98087 (NYC_TM -2607, 5942) z 23.4 m NAVD88 | azimuth 209.0deg pitch +0.0deg | 35 mm on 36 mm (54.4deg horizontal) | 1280x776. View direction: 209.0 deg as recorded in meta.json.  This item names no subject and the reference photograph's own view direction was not derived from the image (confidence: medium), so the two halves of this sheet are not guaranteed to face the same way -- compare them on street width, storey height and material, not on composition. Aim: level optical axis (the reference names no subject to aim at).

**Sun** — azimuth 204.6°, elevation 25.7° at 2017-01-21T13:41:20-05:00 (EXIF DateTimeOriginal).

**In frame** — 6/6 building tiles (232,584 tris), 9 landmark models, 2,233 pavement polygons, 383 props, 12,775 facade-kit pieces; 4,500,231 triangles; ground mesh 209² at 2.0 m near / 40.0 m far.

**Verdict — the two halves face different streets, and the one thing the pairing does demonstrate is total: the photograph is ten thousand people filling 42nd Street and the render is an empty grey avenue with nothing alive in it at all**

## What matches

* The camera stands on the photograph's own EXIF GPS, 40 m from the item's nominal viewpoint, at 23.4 m NAVD88 on a 21.8 m street surface.
* As a Manhattan street canyon the render is credible: the roadbed and both sidewalks are the right widths, the kerb reveal is visible along their whole length, and the wall of buildings steps back and down toward a bright sky slot at the far end exactly as the photograph's own canyon does.
* Aerial perspective is right. The far towers wash out into haze at the same rate as in the reference, which is a fair test of the Nishita sky plus Filmic transform at a 25.7 deg winter Sun.
* Street furniture is present and correctly scaled: a bus shelter on the east sidewalk, cobra-head lamps on davits over the roadway, a mailbox at the kerb, sidewalk sheds with green netting along the west wall.
* The Sun is taken from the photograph's EXIF instant (2017-01-21 13:41:20 EST, elevation 25.7 deg) and the flat overcast-free light matches the reference's grey January sky closely enough that exposure is comparable.

## What does not match

* The frames face different streets. The item looks south-south-west down Fifth Avenue past the library; the photograph — 'Women's March on NYC looking down 42nd' — looks west along 42nd Street. As with the northward view, every photograph collected for this item carries estimated_viewpoint.method = camera_gps_with_item_azimuth, so its direction was assumed rather than measured and no choice among them fixes the mismatch.
* There are no people. The reference is a crowd that fills the frame from the lens to the vanishing point, several thousand visible; the render has not one figure. No other gap in this comparison set is as large in pixel terms.
* There are no vehicles, so the roadway reads as a fresh grey slab.
* No road markings, no lane lines, no stop bar, no crosswalk stripes.
* The building walls are flat pastel with unglazed window dashes. The reference's west wall is a continuous run of glazed shopfronts, awnings, scaffolding, signs ('cafe', 'metro') and fire escapes; the render's is a plain surface with a green scaffold band.
* No shopfront signage or lettering anywhere, and no glass in any opening.
* The bare street trees still read as opaque cones (11 impostor cards dropped in this frame; the branch geometry beneath them is what remains too dense).
* The kit was capped by the triangle budget at 12,775 of 19,975 pieces in range, so about a third of the facade detail within 140 m is not drawn.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the two halves face different streets | the item names no subject and the reference stage assigned the item's azimuth to each photograph rather than measuring it; the chosen photograph looks west along 42nd Street | reference |
| no people | no crowd placement feeds the verification scene | data |
| no vehicles | no traffic placement feeds the verification scene | data |
| no road markings | pavement polygons carry a kind but no stripe geometry or texture | material |
| flat facades, no glazing, no signs | shells carry a per-material base colour; the facade kit supplies openings without glass, mullions or sign faces | material |
| trees read as solid cones | the leaf-off branch model is dense and untextured | material |
| a third of the facade kit not drawn | the 4.5 M triangle budget is spent before the kit is finished; the sheet records the cap | geometry |
