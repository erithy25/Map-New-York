# Flatiron Building

`landmark_flatiron_building` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Flatiron Building, Fifth Avenue, Manhattan, New York.jpg by Christian David, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2026-04-17 17:39:37, 1920x2880. [Commons page](https://commons.wikimedia.org/wiki/File:Flatiron_Building,_Fifth_Avenue,_Manhattan,_New_York.jpg)

**Camera** — camera 40.74230, -73.98909 (NYC_TM -3302, 4698) z 14.0 m NAVD88 | azimuth 198.5deg pitch +0.0deg | 27 mm on 36 mm (48.6deg horizontal, 68.3deg vertical, portrait) | 852x1278. View direction: 198.5 deg, the bearing from this photograph's own GPS position to Flatiron Building; heading and position both come from the photograph.  The item's recorded azimuth is 206.3 deg, 7.8 deg away, and belongs to its nominal viewpoint. Aim: level optical axis (Flatiron Building is 145 m away and would need +16 deg of tilt; a real frame would use a wider lens instead, and a tilted axis would stop the render being comparable on proportion).

**Sun** — azimuth 265.9°, elevation 21.3° at 2026-04-17T17:39:37-04:00 (EXIF DateTimeOriginal).

**In frame** — 4/4 building tiles (217,974 tris), 1 landmark models, 1,920 pavement polygons, 477 props, 3,873 facade-kit pieces; 2,351,201 triangles; ground mesh 207² at 2.0 m near / 40.0 m far.

**Verdict — the best single-building match in the whole set: the prow, the taper, the storey count, the cornice and the position on the traffic island are all right, and the difference is entirely surface — a pale untextured grid where the reference is dark rusticated limestone**

## What matches

* The Flatiron is unmistakably itself. The 25 deg wedge prow, the way the two elevations converge, the 22 storeys, the projecting cornice at the top and the heavier base course are all modelled at the published 87 m height, 145 m from the camera.
* The lens rule worked exactly as intended here: 35 mm widened to 27 mm, which is enough to contain a subject standing 85 m above the lens at 145 m without going anywhere near the 18 mm floor, and the whole building including its cornice is in the frame.
* The camera stands on the photograph's own EXIF GPS, 40 m from the item's nominal viewpoint, and the heading (198.5 deg) is the bearing from there to the building.
* The street geometry around it is right: Fifth Avenue and Broadway converging on the island, the roadbed widths, the kerb lines, 1,920 pavement polygons with 425 crosswalk polygons, and white directional arrows painted on the roadbed.
* The block faces flanking the avenue step down at the right heights, and a newsstand, litter basket, street trees and lamps are placed correctly along the kerb.

## What does not match

* The facade has no relief. The reference's Flatiron is limestone and terracotta with rusticated courses, projecting bay windows on every floor, a heavy modillion cornice and deep shadow; the render is a flat pale grid of window openings with no reveal, no bay, no course line and no glass.
* The colour is wrong: pale beige-grey against the reference's dark warm grey-brown.
* The reference's scaffolding wrapping the base — the building's actual state in 2026 — is absent.
* No people, no vehicles, no traffic signals, no Fifth Avenue clock, no bike lane, no bollards, no newsstand awnings. The reference's lower third is entirely these.
* The lower 40 % of the render is bare roadbed with no texture beyond the arrows.
* The sky is a clear gradient against the reference's broken cumulus, which changes the whole tonality.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| no facade relief, bays or cornice modelling | the flatiron landmark model carries the massing and a flat window grid; the rustication, bays and mouldings are not modelled | geometry |
| wrong facade colour | the model's base colour is lighter than the building's limestone | material |
| no scaffolding | temporary works are in no dataset | data |
| no people, vehicles, signals or clock | no crowd, traffic or street-furniture placement covers them | data |
| bare roadbed | pavement polygons carry a kind and a few markings but no texture | material |
| clear sky against broken cloud | the sky is a Nishita atmosphere with no cloud layer | lighting |
