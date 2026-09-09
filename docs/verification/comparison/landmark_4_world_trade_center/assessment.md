# 4 World Trade Center

`landmark_4_world_trade_center` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:View of Manhattan from Brooklyn Bridge Park, New York City, 20231005 0914 2148.jpg by Jakub Hałun, CC BY 4.0 (https://creativecommons.org/licenses/by/4.0), taken 2023-10-05 09:14:58, 1920x1200. [Commons page](https://commons.wikimedia.org/wiki/File:View_of_Manhattan_from_Brooklyn_Bridge_Park,_New_York_City,_20231005_0914_2148.jpg)

**Camera** — 40.709726, -74.010359 (NYC_TM -5092, 1099) at z 10.9 m NAVD88 | azimuth 300.0°, pitch +34.7° | 18 mm on 36 mm (90.0° horizontal) | 1280x800.

**Sun** — azimuth 120.2°, elevation 24.0° at 2023-10-05T09:14:58-04:00 (EXIF DateTimeOriginal); 708.1 W/m² direct normal, sky at strength 0.0384, Filmic, +5.50 stops.

**Subject** — 4 World Trade Center at 150.2 m.

**In the scene**, within 640.3 m of the camera and not all of it in frame — 4 building tiles (106,490 tris), 14 landmark models of which **2 can fall inside the 90.0° frame**, 25,400 pavement polygons (10,315 white, 4,827 roadbed, 4,681 sidewalk, 3,443 curb, 1,014 plaza, 711 crosswalk, 193 yellow, 183 median, 33 parking lot), 817 props of the 4,085 in range, 5,055 kit pieces, 85 vehicles and 330 people; 4,500,047 triangles. Ground mesh 83,710 triangles, 0 holes. 20 city surfaces are dressed from the shared photographic catalogue.

## Verdict — the tower is measured right and framed at its foot, but the photograph is a Brooklyn skyline a kilometre and a half away, and the pair compares nothing like with like

**The two halves are not the same view, and the record says so before the reader has to.** The photograph is a skyline from Brooklyn Bridge Park at **09:14** on a clear October morning: a lawn, a railing, the East River, a row of shore trees, and the whole of Lower Manhattan across the upper half of the frame under a blue sky, Seaport slabs at the left and One World Trade Center's spire at the right. 4 World Trade Center is in it — the flat-topped blue-glass slab immediately left of 3 World Trade Center's braced shaft — as a strip a few dozen pixels wide. The render stands on Church Street at Liberty Street, **150.2 m** from the tower, and tilts **+34.7°** up a glass canyon. The photograph's own GPS is **1,455.5 m** from that camera, past the **250 m** at which the record allows a fix to be the same view, so `camera_origin.from_photograph_gps` is `false` and the camera was stood on the item's recorded viewpoint. That is J60's shape — a photograph of somewhere else under the subject's name — and, as on J60's own sheets, a photograph that *is* of these towers sat unused in the same folder: `1.jpg`, "3 & 4 World Trade Center Towers, May 2023", with its GPS at the west edge of the site. The recorded viewpoint was hard against `t_-6_1_metal_panel`, **1.0 m** ahead; the camera was walked **19.4 m** onto the nearest roadbed.

**The subject is in the render, and the record's fraction understates it.** The height probe lands **43 of 43** rays on built fabric at the subject's coordinate and reads **297.84 m** above a ground at **5.66 m**, off `lm_b_wtc_site.241`. The nearest catalogue origin, `b_wtc_site`, is **167.2 m** away, outside the old rule's **120 m**, so the height is measured off the geometry (J74) rather than taken from the catalogue's **329.2 m** — and it agrees with 4 WTC's published height to within a metre. That top stands **293 m** above the lens at **63°** elevation and the **18 mm** frame is only **64°** tall, so the axis was tilted (I18, declared) and the top is still cut off. The sightline fan, sized to the object's **90.9 m** plan extent and **297.2 m** height, lands **6 of 13** rays on the subject (`subject_visible_fraction` **0.462**), **5** on nearer fabric of the same site model (`lm_b_wtc_site.242` at **119.1 m**), **2** into sky, and names `prop_tree_honeylocust_large_4` at **21.7 m** as the blocker. Against the picture: the tower's sunlit shaft runs unbroken from the bottom of the frame to the top, dead centre; the honeylocust crown fills the upper left and covers the curtain wall behind it, not the subject. A street tree taking edge rays from a fan sized to a wide subject is J78's shape; the verdict to carry away is the picture's.

**What the reader must not take from this sheet.** No proportion is comparable: the render's verticals converge by declaration and the photograph's are level at a kilometre and a half. No luminance statistic compares the same scene: the photograph's pixels are sky, river, lawn and sunlit distant stone; the render's are shadowed glass and one lit face. Beyond the building itself, the two halves share only the sun.

## What matches
* **The building is at the coordinate and is the right height.** **43 of 43** probe rays on built fabric, **297.84 m** above ground, measured off the geometry and not off a model origin **167.2 m** away (J74). In both halves it is a flat-topped glass slab with 3 World Trade Center's narrower shaft to its right.
* **The aim is exact.** The recorded azimuth **300.0°** agrees with the bearing from the camera to the subject (**299.9°**) to **0.1°**; the tower stands on the frame's centre line.
* **The light is the same morning.** With the sun at **120.2°** and the camera looking at **300.0°** it is directly behind the lens; the tower's east face is lit in the render as the skyline's east faces are in the photograph.
* **The city around the tower is dressed**: **4,763** windows, **128** storefronts and **11** cornices among **5,055** kit pieces; **177** trees among **817** props; **20** catalogue surfaces.

## What does not match
* **The viewpoint.** The photograph is taken from Brooklyn, **1,455.5 m** from the render's camera, across the East River; its foreground is lawn, railing and water and its subject is a sliver of a forty-tower skyline. The render's is a street canyon with the subject filling it.
* **The proportion.** The render is tilted **+34.7°** and its verticals converge hard; the photograph's are level. `pitch_reason` states this, and it is why no shape comparison can be drawn.
* **The facade.** In the photograph 4 WTC is a smooth blue-grey mirror with a hairline grid. The render's shaft carries broad bright spandrel bands at every floor and reads as a banded office slab.
* **A honeylocust crown across the upper left of the render.** `prop_tree_honeylocust_large_4` at **17.6 m**, **-45°** yaw and **+32°** pitch, is the record's nearest obstruction and its sightline blocker at **21.7 m**. The photograph's trees are on the Brooklyn shore.
* **The right-hand fabric.** A pale stone mid-rise with punched windows and a brick block with a cornice and shopfronts fill the right third of the render. Nothing in the photograph corresponds to them, so whether they are what stands on Church Street cannot be checked here.
* **The crowd is out of frame.** **330** people and **85** vehicles were placed for a weekday, the nearest pedestrian **9.5 m** from the lens, but the tilt puts the ground below the bottom edge and none is in the picture.
* **The development.** The render needed **+5.50** stops to bring its median to middle grey where the physical rule alone gave **+0.85**; the record calls the scene under-lit, and the linear median **0.003984** says why: at **24.0°** elevation the sun is behind the blocks east of Church Street and the street and lower facades sit in their shadow. Pushed that far the lit shaft goes near white — render p95 **0.895** against the photograph's **0.7708**. The photograph is exposed **0.574** stops above the convention against the render's **0.235** (offset **-0.339**); its p05 **0.1529** against **0.2285** is a gap wider than the JPEG floor, because its darks are tree shadow and the render's are shaded glass lifted five and a half stops.
* **Chroma.** **0.1113** against **0.1643**, ratio **0.677**: blue sky, blue-green water, green lawn and trees against a frame of grey glass with one green crown.

## Cause of each gap
| gap | cause | class |
|---|---|---|
| the viewpoint, 1,455.5 m from the photograph's GPS | the chooser paired a Brooklyn skyline with a Church Street viewpoint while `1.jpg`, a photograph of these towers from the site, sat unused | reference, **DEVIATIONS J60** |
| converging verticals against a level photograph | the top is 293 m above a lens 150.2 m away and the 18 mm frame is 64° tall; tilt was chosen over losing the subject | stated choice, **DEVIATIONS I18** |
| banded spandrels where the photograph is a seamless mirror | the site model's curtain wall expresses every floor line as a bright band and reflects neither sky nor neighbours | material |
| a honeylocust crown across the upper left | a placed street tree 17.6 m from the lens; a fan sized to a 90.9 m subject sends edge rays into it | verification, **DEVIATIONS J78** |
| stone and brick blocks on the right with no counterpart | building tiles dressed by the facade classifier; the photograph shows nothing at this range | reference |
| no crowd in frame | the +34.7° tilt takes the ground out of the picture; the agents are placed | — (not a gap) |
| +5.50 stops, p95 0.895 against 0.7708, p05 0.2285 against 0.1529 | metered development of a canyon in the shadow of the blocks east of it at a 24.0° sun, against a photograph exposed for open sky and water; a different scene, not a different city | — (not a gap), **DEVIATIONS J83** |
| chroma 0.677 of the photograph's | the photograph's frame is sky, river and lawn; the render's is glass | reference |
