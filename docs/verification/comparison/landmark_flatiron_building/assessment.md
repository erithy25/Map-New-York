# Flatiron Building

`landmark_flatiron_building` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Flatiron Building, Fifth Avenue, Manhattan, New York.jpg by Christian David, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2026-04-17 17:39:37, 1920x2880. [Commons page](https://commons.wikimedia.org/wiki/File:Flatiron_Building,_Fifth_Avenue,_Manhattan,_New_York.jpg) — the photograph's own view direction is derived from the image at **high** confidence.

**Camera** — 40.7423, -73.989094 (NYC_TM -3302, 4698) at z 14.0 m NAVD88 | azimuth 198.5°, pitch +0.4° | 27 mm on 36 mm (47.8° horizontal, portrait) | 852x1278. The camera stands on **this photograph's own EXIF GPS**, 40.0 m from the item's recorded viewpoint, and was **not moved**: the viewpoint is in open air on the ground, the view azimuth is clear for 110.1 m, the nearest built thing in the frame is `t_-4_4_limestone` 48.3 m away and the nearest simulated agent is `agent_veh_suburban_black_car_278.0` 8.0 m away. The azimuth is the bearing from that GPS to the Flatiron, so **heading and position both come from the photograph**; the item's own recorded azimuth is 206.3°, 7.8° away.

**Sun** — at 2026-04-17T17:39:37−04:00, the photograph's own **EXIF DateTimeOriginal**. That date is a **Friday** and the crowd was drawn for a weekday.

**In the scene** — 5,343 kit pieces, 51 vehicles and 216 people; 20 city surfaces are dressed from the shared photographic catalogue. The subject stands 145.2 m from the camera.

## Verdict — the building is right, the frame is right, and the record's own verdict on it is wrong

**This is among the best landmark pairings in the set.** The Flatiron's wedge stands at the centre of both halves at close to the same scale, tapering from its wide Fifth Avenue flank to the narrow prow at Twenty-third Street, with the cornice reading as a cornice at the top and the two avenues falling away either side. Nothing about the camera is assumed: the position is the photograph's own GPS, the heading is the bearing from that GPS to the building, and the instant is the photograph's own EXIF, to the second.

**The measurement of the building agrees with its catalogue.** The height probe lands **17 of 17 rays** on built fabric at the subject's coordinate and reads **85.35 m** above the ground there, off `lm_flatiron.9`; the catalogue entry `flatiron`, 4.5 m away, publishes **86.9 m**. A metre and a half between a measured surface and a published height, on a building whose top is a cornice rather than a point.

**And the record says `subject_visible: false`, blocked at 111.3 m by `lm_flatiron.2` — by the Flatiron.** That is the sightline probe reporting that the building blocked the view of itself. The arithmetic is the whole of it: the probe calls a hit closer than the subject's distance minus 25 m a blocker, the subject's distance is measured to its **recorded coordinate** — the centroid, at 151.0 m — and the prow the ray actually meets is at **111.3 m**, forty metres nearer. A ray that lands squarely on the building is counted as stopped by something. **A ray that lands on the subject's own model has found the subject**, and until that is fixed this field must be read against the picture rather than instead of it (docs/DEVIATIONS.md J78).

## What matches

* **The massing is the massing.** The triangular plan, the sharp prow, the flank running back along Fifth Avenue, the vertical proportion and the crowning cornice all read correctly, and at the same size in the frame as the photograph's.
* **The position, the heading and the instant are all the photograph's own.** No fallback, no assumption, no walk.
* **The height agrees with the catalogue to 1.55 m** on a 17-of-17 measurement.
* **The street furniture and fabric are right**: 5,343 kit pieces including **4,515 windows**, 356 storefronts, 70 scaffold pieces, **52 cornices**, 67 pilasters, 51 string courses and 13 water towers — a Flatiron-district block face, not a bare extrusion.
* **The fleet is a Manhattan fleet at rush hour**: **20 yellow taxis**, 11 boro taxis, 8 black cars, 8 sedans, 2 MTA buses, 2 SUVs.
* **The camera is where a photographer stands** — on the roadway looking down the wedge, with traffic passing in front of it, which is what the reference shows too.

## What does not match

* **The frame is 43 % of the photograph's brightness**: mean **0.2385** against **0.5615**, standard deviation **0.1943** against **0.334** (**0.582×**), 95th percentile **0.5917** against **0.9496**, 5th percentile **0.0221** against **0.0782**. Both are the same instant, so this is not the clock. The photograph's upper half is a bright blue sky with sunlit cloud and its subject is a sunlit limestone facade; the render's sky is a clear gradient with no cloud at all and its facade is in the shade the 17:39 sun actually casts. **This build models no cloud**, and on a portrait frame whose top half is sky that is most of the difference.
* **A black SUV eight metres from the lens fills the lower left of the render.** It is a correctly placed simulated vehicle and it is where a car would be; it is also a third of the frame, and the photograph's foreground is open roadway. This is the closest agent to a lens on any sheet so far.
* **Chroma is 0.594×** — **0.0681** against **0.1147**. Part is the missing sky colour; part is J66's remainder, one material family stated per facade class where the Flatiron's limestone, terracotta and rusticated base are three.
* **The facade is a window grid where the photograph is carved stone.** The Flatiron's Renaissance-revival front carries a rusticated base, quoined corners, string courses, spandrel panels and a heavy modillioned cornice. The kit places 52 cornices, 67 pilasters and 51 string courses across the whole scene, and at this distance the building reads as a regular grid of openings.
* **The prow is blunter than the real one.** The photograph's corner narrows almost to a knife edge; the render's has a visible face.
* **Pedestrians were dropped in their thousands** — **1,546** for the triangle budget alone, 864 for being outside the radius, 338 for standing in the carriageway without crossing, 31 for not being on a walkable surface and 5 for standing over the observer. The busiest pedestrian corner in the district is drawn with 216 people.
* **`subject_visible: false`, and it is wrong**, for the reason the verdict gives.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| `subject_visible: false` on a frame the building fills | the probe measures to the subject's recorded centroid at 151.0 m and calls the prow at 111.3 m a blocker; a hit on the subject's own model is finding it, not being stopped by it | **verification — open, DEVIATIONS J78** |
| mean 0.425×, and a sky with no cloud | the photograph's upper half is sunlit cloud over blue; this build models no cloud at all, and the frame is portrait so the sky is half of it | **data — no source exists** |
| chroma 0.594× | the missing sky colour, plus one material family stated per facade class where the Flatiron carries limestone, terracotta and a rusticated base (J66) | reference + material |
| a black SUV filling the lower left | a correctly placed simulated vehicle 8.0 m from the lens; placement is city-wide and the frame is not | verification |
| a window grid where the photograph is carved stone | the shell is extruded from a footprint; rustication, quoins, spandrel panels and a modillioned cornice are not in the kit and the classifier has no source for them | geometry |
| the prow is blunter than the real one | the footprint is simplified at its sharpest corner | geometry |
| pedestrians and vehicles dropped in their thousands | the placement rules — over the triangle budget, outside the radius, in the carriageway, not on a walkable surface, over the observer — each named with its count in the record | performance + verification |
