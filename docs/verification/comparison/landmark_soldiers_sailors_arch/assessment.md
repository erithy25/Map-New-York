# Soldiers' and Sailors' Memorial Arch (Grand Army Plaza, Brooklyn)

`landmark_soldiers_sailors_arch` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Brooklyn, NYC (2020) - 30.jpg by Another Believer, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2020-02-22 14:33:47, 1920x1080. [Commons page](https://commons.wikimedia.org/wiki/File:Brooklyn,_NYC_(2020)_-_30.jpg)

**Camera** — camera 40.67306, -73.97056 (NYC_TM -1738, -2992) z 43.6 m NAVD88 | azimuth 29.7deg pitch +5.3deg | 35 mm on 36 mm (54.4deg horizontal) | 1280x720. View direction: 29.7 deg, the bearing from this photograph's own GPS position to Soldiers' and Sailors' Memorial Arch (Grand Army Plaza, Brooklyn); heading and position both come from the photograph.  The item's recorded azimuth is 170.0 deg, 140.3 deg away, and belongs to its nominal viewpoint. Aim: aimed at Soldiers' and Sailors' Memorial Arch (Grand Army Plaza, Brooklyn) 95 m away, at its mid-height (the b_soldiers_sailors_arch model's 24 m height); +5.3 deg from horizontal.

**Sun** — azimuth 221.6°, elevation 29.2° at 2020-02-22T14:33:47-05:00 (EXIF DateTimeOriginal).

**In frame** — 4/4 building tiles (393,160 tris), 3 landmark models, 949 pavement polygons, 486 props, 2,955 facade-kit pieces; 2,794,739 triangles; ground mesh 203² at 2.0 m near / 40.0 m far.

**Verdict — the arch is not in the frame at all: the camera stands on the photograph's own GPS 231 m from the item's viewpoint, aimed at a subject 95 m away, and what it sees is an empty plaza, a flagpole and the Prospect Heights block faces behind**

## What matches

* The camera stands on the photograph's own EXIF GPS and the heading (29.7 deg) is the bearing from that point to the arch; the item's recorded azimuth of 170 deg is 140 deg away and was correctly discarded.
* The aim rule tilted +5.3 deg to centre a 24 m subject 95 m away, inside the 8 deg limit.
* Grand Army Plaza's geometry is right: the wide circulating roadway, the plaza islands, the kerb lines, and 949 pavement polygons including 216 crosswalk polygons.
* The bare February street trees along the plaza edge are correct for the date, with 23 opaque impostor cards dropped, and a flagpole stands where the reference has one.

## What does not match

* The Soldiers' and Sailors' Memorial Arch is not visible. Whether the model is out of the frame or behind the camera, the item's entire purpose is unserved.
* The reference's content — the granite arch, the bronze quadriga on top, the two sculptural groups on the piers, the traffic signals, the flag — has no counterpart.
* The plaza is a bare grey plane with no paving pattern, no benches, no planting and no fountain.
* No people, no vehicles, no signals.
* The buildings behind are flat pastel solids with no glazing.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the arch is not in the frame | the camera is 231 m from the item's viewpoint on the photograph's GPS, and the aim does not resolve onto the model; the sheet records 3 landmark models in range but none is visible | camera |
| no quadriga or sculpture | the b_soldiers_sailors_arch model carries the arch form without its bronzes | geometry |
| bare plaza | plaza paving, planting and furniture are in no dataset the scene reads | data |
| no people, vehicles or signals | no stage places any of them | data |
| flat buildings | shells carry a per-material base colour with no glazing | material |
