# Flatiron Building

`landmark_flatiron_building` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Flatiron Building, Fifth Avenue, Manhattan, New York.jpg by Christian David, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2026-04-17 17:39:37, 1920x2880. [Commons page](https://commons.wikimedia.org/wiki/File:Flatiron_Building,_Fifth_Avenue,_Manhattan,_New_York.jpg)

**Camera** — 40.7423, -73.989094 (NYC_TM -3302, 4698) at z 14.0 m NAVD88 | azimuth 198.5°, pitch +0.4° | 27 mm on 36 mm (47.8° horizontal, portrait) | 852x1278.

**Sun** — azimuth 265.9°, elevation 21.3° at 2026-04-17T17:39:37-04:00 (EXIF DateTimeOriginal); 672.4 W/m² direct normal, sky at strength 0.0398, Filmic, +4.51 stops.

**Subject** — Flatiron Building at 145.2 m.

**In the scene**, within 672.4 m of the camera and not all of it in frame — 4 building tiles (295,276 tris), 2 landmark models of which **1 can fall inside the 47.8° frame**, 28,796 pavement polygons (11,033 white, 7,253 sidewalk, 4,636 roadbed, 3,413 curb, 1,281 plaza, 654 crosswalk, 376 median, 106 parking lot, 44 yellow), 514 props of the 1,133 in range, 5,343 kit pieces, 51 vehicles and 216 people; 4,500,165 triangles. Ground mesh 86,528 triangles, 0 holes. 20 city surfaces are dressed from the shared photographic catalogue.

## Verdict — the right building from the right spot, and this time the record agrees with the picture

**The two halves are the same view.** The camera stands on the photograph's own EXIF GPS, **40 m** from the item's nominal viewpoint on the Worth Monument island; the heading, **198.5°**, is the bearing from that GPS to the building, and the direction estimated from the photograph itself is **198.4°**. The instant is the EXIF second, Sun low in the west at **265.9° / 21.3°**. In both halves the Flatiron's prow stands at the centre of the frame (**1.6°** off-axis), Broadway flank left and Fifth Avenue flank right, a dark rusticated base under a pale shaft, the cornice lines sloping away from the prow so the wedge reads as an arrowhead from below.

**The measurement agrees with the catalogue, and the sightline now finds the building instead of being stopped by it.** The height probe lands **43 of 43** rays on built fabric at the subject's coordinate and reads **85.35 m** above the ground, off `lm_flatiron.9`; the catalogue entry `flatiron`, **4.5 m** away, publishes **86.9 m** — a metre and a half apart on a building that ends in a cornice. The fan is drawn from that height and the measured plan extent, **66.4 m** across and **31.3 m** on the narrow side: **13** rays, **13** clear, **9** on the subject, **4** into nothing, visible fraction **0.692**. Six of the nine land on `lm_flatiron.0` at **110.2 m**, nearer than the **151.0 m** recorded range: that is the prow, the coordinate being the plan centroid some forty metres behind it. The previous render of this sheet reported the Flatiron blocking its own sightline for exactly that reason (DEVIATIONS J78); the record now counts a hit on the subject's own model as finding it. The four empty rays are the corners of a **66.4 m** by **85.2 m** rectangle drawn round a triangle; a wedge does not fill its bounding box.

**What the reader must not take from this sheet is proportion, or the tone level.** The render is level at **+0.4°**, the lens widened from **35 mm to 27 mm** to hold a top **30°** above the horizon at **145 m**; the photograph is tilted hard upward, its verticals converge and its prow tops out under sky, while the render's prow runs to the top edge. On light: the render is developed at **+4.51 stops** where the physical rule alone gives **+1.03**, on a linear median of **0.007889**, and the record's own note calls the scene under-lit. The photographer exposed **1.363** stops above the middle-grey convention, the render sits at **0.233**; the **-1.13** between them is that choice, and the matching means, **0.567** against **0.5615**, are the metering's doing rather than the scenes'.

## What matches

* **The massing and the orientation.** A wedge with its prow to the camera, the wider face on the Fifth Avenue side, a rounded prow, a dentil cornice at the head of both flanks, a rusticated base of about five storeys and a pale shaft above — in both halves, at the same place in the frame.
* **Position, heading and instant are the photograph's own**: GPS, bearing-to-subject, EXIF second. Azimuth **198.5°** against **198.4°** estimated from the image; the item's nominal **206.3°**, **7.8°** off, is not used.
* **The height**: **85.35 m** on **43 of 43** rays against **86.9 m** published; model `lm_flatiron.9` at lod 0, **38,253** triangles.
* **The sightline**: **9 of 13** rays on the subject, fraction **0.692**, nothing between lens and building; the nearest built thing in frame is `t_-4_4_limestone` at **48.3 m** to the side.
* **The facade palette.** Cream shaft with terracotta-coloured courses at every floor over a dark grey rusticated base; the real building is limestone and glazed terracotta over rusticated limestone.
* **The street.** A continental crosswalk in the foreground, white lane lines, taxis in the distance, street lamps down Fifth Avenue, pedestrians clustered on the right-hand pavement at the wedge's foot. **51** vehicles — **20** yellow taxis, **11** boro taxis, **8** black cars, **8** sedans, **2** MTA buses, **2** SUVs — and **216** people.
* **The block faces carry fabric**: **5,343** kit pieces — **4,515** windows, **356** storefronts, **52** cornices, **67** pilasters, **51** string courses.

## What does not match

* **The sky.** The photograph's upper half is blue with sunlit cumulus; the render's is a clear pale gradient. This is most of the tone gap: median **0.4973** against **0.7105** (ratio **0.7**), standard deviation **0.2542** against **0.334** (**0.761**).
* **The development, as stops.** Render **+4.51** metered against **+1.03** physical; exposure offset **0.233** against the photograph's **1.363**, **-1.13** apart. The render's floor is *above* the photograph's — p05 **0.1325** against **0.0782** — because the photograph's lower half is black scaffold netting and shaded street, and the render's darkest things are the SUV's tyres. The tops agree: p95 **0.9328** against **0.9496**.
* **The shade line.** In the photograph the buildings west of Fifth Avenue throw a shadow diagonally across the lower half of the shaft, the top in sun. The render's shaft is lit evenly from cornice to base; the west-side tiles are in the scene and the Sun is at the recorded **21.3°**, so the record does not say why.
* **Carved terracotta against a window grid.** The real prow carries stacked bay windows, colonnettes, a cartouche above the cornice and a heavy modillioned crown; the render's is a rounded corner with a regular grid of openings and one dentil band. The photograph's black netting over the lower storeys is a construction wrap, not a fault of the model.
* **A black SUV at 8.0 m fills the lower left of the render**, its roof cutting the Flatiron's base, and a yellow taxi enters from the lower right. The photograph's foreground is open roadway with pedestrians in the crosswalk and a cyclist.
* **The plaza is roadway.** The photograph's left third is the Broadway pedestrian plaza behind concrete barriers, with planters and a sculpture; the render carries the carriageway across it. The record lists **5** artwork props and **7** memorials the placer could not map.
* **The right-hand skyline.** The photograph has a gilded dome, a cupola and a cast-iron sidewalk clock; the render has a flat-roofed tan slab and a red-brick walk-up with a green storefront band.
* **Chroma 0.0852 against 0.1147** (**0.743**): the missing sky colour, and one material family per facade class (J66).
* **The crowd is thin for this corner**: **216** drawn, **1,546** dropped for the triangle budget, **864** outside the radius, **338** standing in the carriageway without crossing, **31** off any walkable surface, **5** over the observer.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| a clear gradient where the photograph has cumulus | the build models no cloud; on a portrait frame that is half sky, this sets the median | data |
| +4.51 stops against +1.03, exposure offsets 0.233 / 1.363 | metered development (**DEVIATIONS J83**): a Sun at 21.3° over a street shaded by its west wall needed +4.51 stops to read; the photographer exposed above the convention — a statement of the light, not a fault of the city | — (not a gap) |
| no shade line across the shaft | not established by the record; the west-side tiles are present and the Sun is on the EXIF second, so those tiles' heights or the diffuse term is where to look | verification |
| a window grid where the photograph is carved terracotta | the landmark model carries massing, a rusticated base and a dentil cornice; bays, colonnettes and the cartouche are not in it or in the kit | geometry |
| a black SUV at 8.0 m across the lower left | a correctly placed simulated vehicle; placement is city-wide and the frame is not | verification |
| plaza rendered as carriageway | barriers, planters and sculpture are unmapped (5 artwork, 7 memorial) and the surface under them reads as roadbed | data |
| gilded dome and sidewalk clock absent | tile shells are extruded footprints; a dome, a cupola and a street clock have no source in kit or prop map | geometry |
| chroma 0.743 | no sky colour; one material family per facade class (**DEVIATIONS J66**) | material |
| a thin crowd | triangle budget and placement rules, each named with its count in the record | performance |
| the render level, the photograph tilted | I18: lens widened to 27 mm before any tilt, pitch +0.4° declared; the tilt is the photographer's | stated choice |
