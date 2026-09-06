# Bethesda Terrace and Fountain

`bethesda_terrace_fountain` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Bethesda Fountain and the Lake, Central Park, Manhattan, New York.jpg by Christian David, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2026-04-18 08:04:45, 1920x1280. [Commons page](https://commons.wikimedia.org/wiki/File:Bethesda_Fountain_and_the_Lake,_Central_Park,_Manhattan,_New_York.jpg)

**Camera** — camera 40.77350, -73.97110 (NYC_TM -1778, 8174) z 24.2 m NAVD88 | azimuth 14.2deg pitch -2.5deg | 28 mm on 36 mm (65.5deg horizontal) | 1280x854. View direction: 14.2 deg as recorded; it agrees with the bearing from the camera position used to Bethesda Fountain (Angel of the Waters) (14.2 deg) to 0.0 deg. Aim: aimed at Bethesda Fountain (Angel of the Waters) 69 m away, at its mid-height (the b_bethesda_terrace model's 8 m height); -2.5 deg from horizontal.

**Sun** — azimuth 92.9°, elevation 20.3° at 2026-04-18T08:04:45-04:00 (EXIF DateTimeOriginal).

**In frame** — 4/4 building tiles (159,580 tris), 7 landmark models, 969 pavement polygons, 120 props, 0 facade-kit pieces; 808,298 triangles; ground mesh 209² at 2.0 m near / 40.0 m far.

**Camera clearance** — the eye point stands on the roof of lm_b_bethesda_terrace.26, which the reference viewpoint records as a single lat/lon for the whole deck; the camera was walked 12 m along the view azimuth to the parapet, the last point the roof still supports, which is where the reference photographs are taken

**Verdict — the camera now stands on the right structure — the terrace's own balustrade runs across the frame where the photograph has it — and everything the photograph is actually of is missing: no fountain, no Angel of the Waters, no Lake, no trees, no people, no brick paving**

## What matches

* The Bethesda Terrace model is placed and the camera stands on it. The balustrade with its turned balusters runs across the middle of the frame at the right height and the right position relative to the viewpoint, and it is recognisably the terrace's own parapet.
* The camera height is right: 24.2 m NAVD88, being the terrace's upper level at 22.6 m from the 2 m heightmap plus a 1.6 m standing eye.
* The heading is right: 14.2 deg as recorded, which agrees with the bearing from the camera to the Angel of the Waters 27 m away.
* Belvedere Castle is visible on the ridge to the north at the correct bearing and distance (637 m), which is a genuine check that the park's landmark models sit in the right places relative to one another.
* The Sun is placed from the photograph's own EXIF instant (2026-04-18 08:04:45 EDT, elevation 20.3 deg, azimuth 92.9 deg) and the low morning light from the east matches the reference's.

## What does not match

* The Bethesda Fountain is not in the frame at all. Neither the basin, nor the tiered fountain, nor the Angel of the Waters — the named subject, 27 m away — is modelled by any stage, so the centre of the photograph has no counterpart.
* The Lake is not there. Central Park's water bodies are not in the terrain heightmap's water mask at this location, so the sheet of water that fills the upper third of the reference is dry ground.
* There is no vegetation. The reference is a wall of spring foliage across its whole width; the render's park is bare grey-white ground with not one tree, because Central Park's interior planting is not in props.parquet (which carries the street-tree census, not park planting).
* The lower plaza, its brick paving pattern, the stairs down from the terrace and the arcade below are all absent from the frame; the terrace model stops at the balustrade.
* There are no people. The reference has roughly eighty visible around the fountain.
* The ground is untextured: a flat pale grey plane with visible triangulation facets from the graded terrain grid, where the photograph has red brick paving in a radial pattern.
* The camera stands on the terrace's roof slab, so the parapet occludes the drop to the plaza; the photograph is taken leaning over that parapet with the fountain filling the lower half. A level axis cannot reproduce that framing, and the sheet says so.
* The two blocks visible over the balustrade at the left are Fifth Avenue apartment houses about 500 m away, which is right, but they are flat pastel solids.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| no fountain and no Angel of the Waters | no stage models park fountains or statuary; props.parquet classes them as 'artwork'/'memorial', kinds with no exported asset | geometry |
| no Lake | the terrain heightmap's water mask does not cover Central Park's water bodies at this tile | data |
| no trees or planting | props.parquet is the street-tree census; park interior planting is not in any dataset the scene reads | data |
| no lower plaza, stairs or arcade | the b_bethesda_terrace model carries the upper terrace and its balustrade only | geometry |
| no people | no crowd placement feeds the verification scene | data |
| untextured, faceted ground | the terrain material is a flat base colour and the graded grid is 2 m here; no paving texture exists | material |
| the fountain is below the parapet and out of frame | a level optical axis is required to compare proportion; the reference leans over the parapet | camera |
