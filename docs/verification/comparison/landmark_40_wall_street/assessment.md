# 40 Wall Street (Trump Building)

`landmark_40_wall_street` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:View of Manhattan from Liberty Island ferry, NYC, 20231003 1627 2026.jpg by Jakub Hałun, CC BY 4.0 (https://creativecommons.org/licenses/by/4.0), taken 2023-10-03 16:27:26, 1920x909. [Commons page](https://commons.wikimedia.org/wiki/File:View_of_Manhattan_from_Liberty_Island_ferry,_NYC,_20231003_1627_2026.jpg)

**Camera** — camera 40.70629, -74.01193 (NYC_TM -5180, 698) z 5.7 m NAVD88 | azimuth 70.0deg pitch +0.0deg | 35 mm on 36 mm (54.4deg horizontal) | 1280x606. View direction: 70.0 deg as recorded; it agrees with the bearing from the camera position used to 40 Wall Street (Trump Building) (70.1 deg) to 0.1 deg. Aim: level optical axis (40 Wall Street (Trump Building) is 200 m away and would need +35 deg of tilt; a real frame would use a wider lens instead, and a tilted axis would stop the render being comparable on proportion).

**Sun** — azimuth 242.9°, elevation 22.4° at 2023-10-03T16:27:26-04:00 (EXIF DateTimeOriginal).

**In frame** — 5/5 building tiles (83,670 tris), 13 landmark models, 2,385 pavement polygons, 623 props, 10,650 facade-kit pieces; 4,500,745 triangles; ground mesh 211² at 2.0 m near / 40.0 m far.

**Camera clearance** — the recorded viewpoint is rendered as an unusable frame from this eye point, so it is treated as blocked even though no ray test caught it; the camera was moved 52 m onto the nearest real roadbed polygon in data/processed/roads/pavement, keeping the same eye height above the heightmap.  The view azimuth is clear for 96 m from there

**Verdict — an unusable pair on both sides: the only photograph the reference stage found for 40 Wall Street is a harbour panorama taken 1.5 km away on the Liberty Island ferry, and the render is a dark corner of a Wall Street canyon with the tower out of frame**

## What matches

* The photograph's own EXIF GPS was correctly rejected as mis-tagged at 1,535 m, and the item's viewpoint used instead; the sheet states it.
* The camera's own guard worked: the first frame from the recorded eye point was unusable, so the clearance correction was forced and the camera moved 52 m onto the nearest real roadbed polygon, from which the view azimuth is clear for 96 m.
* The heading is right: 70.0 deg as recorded, agreeing with the bearing from the camera to 40 Wall Street (70.1 deg) to 0.1 deg.
* 13 landmark models are in range and 2,385 pavement polygons are placed, so the scene content around the camera is correct even though the frame does not show it.
* The sheet is honest about the framing: it states that the tower is 200 m away and would need +35 deg of tilt, that a level axis is kept to preserve proportion, and that the frame therefore shows the street rather than the crown.

## What does not match

* 40 Wall Street is not in the frame. The item exists to test the tower's pyramidal green crown; a level 35 mm axis at 200 m puts the crown far above the top of the frame, and the sheet says so, but that leaves nothing to compare.
* The frame is nearly black: mean luminance 0.122 and standard deviation 0.056, which is above the 0.06 / 0.025 evidence floor but far below anything a person can judge. Wall Street at Broad is a 12 m canyon between 60-100 m walls with a 22 deg October Sun; the geometry is right and the frame is genuinely that dark.
* The two halves have no subject in common. The reference is the whole Lower Manhattan skyline from the water; the render is one corner of one street.
* What can be made out — the wall on the right, the pavement on the left — has no texture, no window glazing and no detail of any kind.
* The facade kit was capped by the triangle budget at 10,650 of 18,999 records in range.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the tower is not in the frame | a 200 m subject 227 m tall cannot be contained by a level 35 mm axis; the lens rule keeps verticals vertical at the cost of the subject | camera |
| the reference is a photograph of somewhere else | no photograph of 40 Wall Street from its own viewpoint was collected; the one chosen has an EXIF fix 1.5 km away and was rejected for position but still used for the image | reference |
| frame too dark to read | a 12 m canyon between 60-100 m walls at a 22 deg Sun, rendered with two light bounces | lighting |
| no texture or glazing on what is visible | shells carry a per-material base colour; the kit supplies openings without glass | material |
| nearly half the facade kit not drawn | the 4.5 M triangle budget is spent before the kit finishes | geometry |
