# Barclays Center

`landmark_barclays_center` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Barclays Center (54458684337).jpg by Eden, Janine and Jim from New York City, CC BY 2.0 (https://creativecommons.org/licenses/by/2.0), taken 2025-04-17 18:23, 1920x1080. [Commons page](https://commons.wikimedia.org/wiki/File:Barclays_Center_(54458684337).jpg)

**Camera** — camera 40.68387, -73.97745 (NYC_TM -2321, -1791) z 15.6 m NAVD88 | azimuth 130.4deg pitch +5.2deg | 35 mm on 36 mm (54.4deg horizontal) | 1280x720. View direction: 130.4 deg, the bearing from this photograph's own GPS position to Barclays Center; heading and position both come from the photograph.  The item's recorded azimuth is 144.8 deg, 14.4 deg away, and belongs to its nominal viewpoint. Aim: aimed at Barclays Center 217 m away, at its mid-height (the c_barclays_center model's 42 m height); +5.2 deg from horizontal.

**Sun** — azimuth 273.1°, elevation 13.2° at 2025-04-17T18:23:00-04:00 (EXIF DateTimeOriginal (minutes)).

**In frame** — 6/6 building tiles (409,110 tris), 2 landmark models, 2,118 pavement polygons, 430 props, 3,702 facade-kit pieces; 2,721,756 triangles; ground mesh 213² at 2.0 m near / 40.0 m far.

**Verdict — right place, right footprint, right colour, wrong shape: the arena is a plain banded box where the building is a sculpted weathering-steel shell with a cantilevered canopy and an oculus, and the corner it stands on is empty of everything that fills the photograph**

## What matches

* The camera stands on the photograph's own EXIF GPS, 57 m from the item's nominal viewpoint, and the heading (130.4 deg) is the bearing from there to the arena — heading and position both from the photograph.
* The arena is in the right place at the right footprint, 217 m from the camera on the Flatbush/Atlantic corner, and it is the right height relative to the towers behind it.
* The material colour is right: the render's rust-brown skin is the weathering-steel palette of the real facade, and the horizontal banding echoes its panel courses.
* The aim rule worked as intended: the subject is 217 m away and needed +5.2 deg of tilt to centre, inside the 8 deg limit, so the axis is tilted rather than the lens widened.
* Street furniture is right and well placed: cobra-head lamps with lit heads, a LinkNYC kiosk on the corner, a hydrant, street trees in full April leaf, and 2,118 pavement polygons with 518 crosswalk polygons at the crossing.

## What does not match

* The shape is wrong in the way that matters. Barclays Center is a curved, tapering, three-lobed shell with a deep cantilevered canopy over an oculus at the corner entrance; the render is a rectangular box with flat faces and square corners. The item exists to test that form and none of it is present.
* The green roof is missing: the reference's most distinctive feature from this angle is the planted roof reading as a grass-green cap, and the render's roof is a flat grey slab.
* No signage. 'BARCLAYS CENTER' in blue letters across the canopy, the sponsor boards and the marquee are the second thing the eye reads in the photograph and there is nothing in the render.
* No people and no vehicles, on a corner where the reference shows perhaps forty pedestrians and thirty vehicles queued at the signal.
* No traffic signals, no street-name signs, no bus shelter, no pedestrian barriers.
* The towers behind the arena are flat pastel solids where the reference has glass curtain wall and red-brick spandrels.
* The ground plane is untextured and the crosswalk has no stripes.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the arena is a box, not a shell | the c_barclays_center landmark model is a simplified prism; the curved shell, canopy and oculus are not modelled | geometry |
| no green roof | the model's roof carries no planted surface or material | material |
| no signage | no stage produces sign geometry | geometry |
| no people, vehicles or signals | no crowd, traffic or signal placement feeds the verification scene | data |
| flat towers behind | shells carry a per-material base colour with no glass | material |
| untextured ground, unstriped crosswalk | pavement polygons carry a kind but no texture or markings | material |
