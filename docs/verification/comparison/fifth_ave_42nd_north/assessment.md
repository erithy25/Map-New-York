# Fifth Avenue at 42nd Street (NYPL), street view looking north

`fifth_ave_42nd_north` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:NYPL main Feb 2017 4.jpg by Epicgenius, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2017-02-16 16:24:37, 1920x1434. [Commons page](https://commons.wikimedia.org/wiki/File:NYPL_main_Feb_2017_4.jpg)

**Camera** — camera 40.75266, -73.98159 (NYC_TM -2668, 5848) z 25.0 m NAVD88 | azimuth 29.0deg pitch +0.0deg | 35 mm on 36 mm (54.4deg horizontal) | 1208x902. View direction: 29.0 deg as recorded in meta.json.  This item names no subject and the reference photograph's own view direction was not derived from the image (confidence: medium), so the two halves of this sheet are not guaranteed to face the same way -- compare them on street width, storey height and material, not on composition. Aim: level optical axis (the reference names no subject to aim at).

**Sun** — azimuth 243.3°, elevation 11.2° at 2017-02-16T16:24:37-05:00 (EXIF DateTimeOriginal).

**In frame** — 6/6 building tiles (222,804 tris), 8 landmark models, 2,262 pavement polygons, 383 props, 11,520 facade-kit pieces; 4,500,432 triangles; ground mesh 209² at 2.0 m near / 40.0 m far.

**Verdict — the two halves face different ways and cannot be compared on composition — the item says 'looking north up Fifth Avenue' and all three photographs collected for it are pictures of the library facade looking west. What the render can be judged on — street width, storey height, kerb line, furniture — is right; everything that makes the photograph a photograph is missing**

## What matches

* The camera stands on the photograph's own EXIF GPS, 17 m from the item's nominal viewpoint, at 25.0 m NAVD88 on a 23.4 m street surface.
* The street section is right. Fifth Avenue's roadbed width, the west and east sidewalk widths, the kerb reveal and the crosswalk positions all match the photograph's foreground where the two overlap.
* Storey heights and setback lines up the avenue are plausible: the block faces step from six to twelve storeys with the right rhythm and the towers behind them are at the right distance.
* The New York Public Library model is placed and 81.6 m from the camera, along with seven other landmark models (One Vanderbilt at 259 m, Grand Central at 368 m, the Chrysler Building at 538 m, the Empire State Building at 582 m). The earlier report that the library was missing no longer holds.
* Real street furniture in real places: 383 props including 49 hydrants, 79 manhole covers, 22 bus-stop signs, 9 bus shelters and 17 flagpoles; 11,520 facade-kit pieces including 188 storefronts and 52 scaffold bays.
* The Sun is placed from the photograph's own EXIF instant (2017-02-16 16:24:37 EST, elevation 11.2 deg, azimuth 243.3 deg) and the low winter light and long shadows in the render match the reference's.

## What does not match

* The frame is of a different thing. The reference is the library's Fifth Avenue portico across the avenue: six Corinthian columns, the pediment, Patience and Fortitude on their plinths, the banner. The render looks north-north-east up the avenue. All three photographs the reference stage collected for this item are library facade shots and every one of them carries estimated_viewpoint.method = camera_gps_with_item_azimuth, meaning the direction was copied from the item and never measured, so no choice among them fixes it.
* No people. The reference has about forty, including a group crossing the frame at 8 m; the render has none, so the near-foreground crosswalk reads as empty grey.
* No vehicles anywhere on the avenue.
* No road markings. The crosswalk in the reference is a broad zebra with a stop bar and lane lines; the render's crosswalk polygons are flat light-grey rectangles with no stripes.
* The bare street trees are still near-solid dark cones. The opaque impostor cards are dropped (12 in this frame) but the branch geometry itself reads as a mass rather than as winter branches, and there are eleven of them lining the avenue.
* A street lamp column stands about 1.5 m from the lens and runs the full height of the frame. That is where props.parquet puts a lamp and where the photograph's own GPS puts the camera, but a photographer would have stepped around it.
* The buildings have unglazed window dashes and no cornice, sill or reveal shadow — the storefront band on the right is a flat green stripe with no glass, no lettering and no awning.
* The bottom 40 % of the frame is bare grey sidewalk and roadbed with no texture, no expansion joints, no gratings, no litter and no tonal variation.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the two halves face different ways | the item names no subject and every photograph collected for it faces the library rather than up the avenue; the reference stage assigned the item's own azimuth to each photo instead of measuring it. Fix at source: collect a photograph looking north up Fifth Avenue, or give the item a subject and rename it | reference |
| no people, no vehicles | no crowd or traffic placement feeds the verification scene | data |
| no road markings | pavement polygons carry a kind but no stripe geometry and no texture | material |
| trees read as solid cones | the leaf-off branch model is dense and untextured | material |
| a lamp column across the lens | the photograph's GPS puts the camera within 1.5 m of a real lamp post; nothing moves an unblocked camera off one | camera |
| flat facades, no glass or lettering | shells carry a per-material base colour and the kit supplies openings without glazing, mullions or signage | material |
| featureless pavement | the pavement material is a flat base colour per kind with no texture map | material |
