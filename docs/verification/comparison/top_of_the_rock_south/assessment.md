# Top of the Rock looking south (Empire State Building centred)

`top_of_the_rock_south` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:View-from-Empire-State-Building.jpg by Sebring12Hrs, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2018-10-25 13:05:58, 1920x1440. [Commons page](https://commons.wikimedia.org/wiki/File:View-from-Empire-State-Building.jpg)

**Camera** — camera 40.75930, -73.97890 (NYC_TM -2440, 6586) z 281.0 m NAVD88 | azimuth 205.2deg pitch +0.0deg | 24 mm on 36 mm (73.7deg horizontal) | 1208x906. View direction: 205.2 deg as recorded; it agrees with the bearing from the camera position used to Empire State Building (205.4 deg) to 0.2 deg. Aim: level optical axis (the subject is 1334 m away; anything that far is photographed with a level camera).

**Sun** — azimuth 187.9°, elevation 36.7° at 2018-10-25T13:05:58-04:00 (EXIF DateTimeOriginal).

**In frame** — 65/83 building tiles (1,174,626 tris), 46 landmark models, 3,371 pavement polygons, 0 props, 0 facade-kit pieces; 3,597,724 triangles; ground mesh 381² at 2.0 m near / 40.0 m far.

**Verdict — the frame is a picture of a roof: the camera stands 2 m above the shell of 30 Rockefeller Plaza in the middle of its slab, and the parapet hides everything the photograph is of**

## What matches

* The eye height is right and its source is published: 259.1 m deck level from blender_out/landmarks/catalog/30_rockefeller_plaza.json (CTBUH 850 ft) plus 1.6 m, giving 281.0 m NAVD88 against the terrain's 20.3 m.
* The heading is right: 205.2 deg as recorded, and the bearing from the viewpoint to the Empire State Building 1,334 m away is 205.4 deg — 0.2 deg apart.
* The lens is right for the subject: 24 mm / 73.7 deg horizontal, which is what the reference frame's Midtown-to-Harbour span needs.
* What can be seen over the parapet is correct in kind: the Midtown towers step down to the south, One Vanderbilt's tapered mass and its spire are at the left of the far ridge, and the low-rise carpet between them has the right grain and the right roof colours (tar, membrane, red brick).
* 65 of the 83 tiles in the 4.5 km scene now import, 28 of them by falling back from LOD2 to LOD1; before the fallback only 37 tiles came in and half the skyline was missing.

## What does not match

* More than half the frame is the flat white roof the camera is standing on, and the parapet across the middle cuts off everything from the horizon down. The reference photograph is a near-vertical view over Midtown from the deck's edge with the Empire State Building centred, the Hudson on the right and the Harbour beyond; the render shows none of that.
* The Empire State Building — the named subject, 1,334 m away and 381 m tall, which should stand a third of the way up the frame dead centre — is entirely hidden behind the parapet.
* The camera-to-parapet correction did not fire. camera.py walks a rooftop eye point forward to the edge of whatever supports it, but it probed only 4 m downward for support; the shell roof here is further below the published deck level than that, so the probe found nothing, concluded the camera was standing on open ground, and left it in the middle of the slab. The probe distance has been raised to 30 m and this subject needs re-rendering.
* The 30 Rockefeller Plaza landmark model and the tile shell of the same building are both in the scene. 67 of the 93 landmark catalogue entries name 121 BINs that blender_out/tiles also builds, so every one of those buildings is drawn twice.
* There is no observation deck: no glass screens, no deck floor, no railings, no antennae or radio masts on the roof. The photograph's foreground furniture is entirely absent.
* The towers are flat pastel solids with no glass and no fenestration, so the mid-distance carpet of Midtown reads as a massing model rather than as a city seen from 260 m.
* 18 of the 83 tiles have no shell at all, so the New Jersey bank across the Hudson — visible in the reference — is empty.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the frame is a roof slab, not the view | the rooftop parapet walk probed only 4 m for support and missed the shell roof under a deck height taken from the published deck level; fixed in camera.py, this subject needs re-rendering | camera |
| Empire State Building not visible | consequence of the camera standing in the middle of the roof rather than at the south parapet | camera |
| 30 Rockefeller Plaza drawn twice | the landmark catalogue names the BINs it replaces (bins: [1076262]) but the shell loader does not suppress them; the same is true for 121 BINs across 67 landmarks | geometry |
| no observation deck, screens or masts | the deck structure is not modelled by any stage; the landmark model stops at the roof slab | geometry |
| flat pastel towers | shells carry a per-material base colour only, with no facade texture and no glass BSDF | material |
| empty New Jersey bank | no tile_buildings.glb is built outside the five boroughs | data |
