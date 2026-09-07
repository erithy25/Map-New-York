# Queens residential block: Bayside

`drive_queens_bayside` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:2024-06-18 14 45 53 View south along Interstate 295 (Clearview Expressway) from the pedestrian overpass at 42nd Avenue in Queens, New York City, New York.jpg by Famartin, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2024-06-18 14:45:53, 1920x1440. [Commons page](https://commons.wikimedia.org/wiki/File:2024-06-18_14_45_53_View_south_along_Interstate_295_(Clearview_Expressway)_from_the_pedestrian_overpass_at_42nd_Avenue_in_Queens,_New_York_City,_New_York.jpg)

**Camera** — camera 40.76300, -73.77200 (NYC_TM 15028, 7047) z 25.0 m NAVD88 | azimuth 0.0deg pitch +0.0deg | 35 mm on 36 mm (54.4deg horizontal) | 1208x906. View direction: 0.0 deg as recorded in meta.json.  This item names no subject and the reference photograph's own view direction was not derived from the image (confidence: medium), so the two halves of this sheet are not guaranteed to face the same way -- compare them on street width, storey height and material, not on composition. Aim: level optical axis (the reference names no subject to aim at).

**Sun** — azimuth 241.3°, elevation 61.3° at 2024-06-18T14:45:53-04:00 (EXIF DateTimeOriginal).

**In frame** — 4/4 building tiles (200,672 tris), 0 landmark models, 2,044 pavement polygons, 337 props, 2,325 facade-kit pieces; 2,368,463 triangles; ground mesh 211² at 2.0 m near / 40.0 m far.

**Camera clearance** — the recorded viewpoint is under verify_terrain (1.5 m of ground or paving directly overhead, so the eye point is beneath the walking surface); the camera was moved 35 m onto the nearest real roadbed polygon in data/processed/roads/pavement, keeping the same eye height above the heightmap.  The view azimuth is clear for 37 m from there

**Verdict — the frame is legible for the first time — the new under-the-paving test caught an eye point 1.5 m beneath the ground surface and moved it onto a real roadbed — but what it shows is a low commercial strip against a photograph of the Clearview Expressway from an overpass 567 m away**

## Re-rendered 2026-09-07 — a frame that passed every camera check and shows a blank wall

The clearance record for this camera reads: *"the viewpoint is in open air on the ground and the
camera was not moved; the nearest solid thing in the view cone is `t_15_7_vinyl_siding` 23.6 m away,
and the view azimuth is clear for 150 m."* Every check passed. The frame is the blank side wall of a
vinyl-sided house filling the upper third, over an untextured ground plane, and **not one of the 73
vehicles and 263 pedestrians the simulation placed here is visible**, nor any of the 182 trees.

**The clearance test measures a ray, and a frame is not a ray.** `view_distance` casts a single line
along the view azimuth at eye height and reports how far it travels before a building shell stops it.
Here it travels the full 150 m probe — the camera is looking down a gap between houses — while the
rest of the frame is a wall. A ray being clear says nothing about what fills the other of the image,
which is why this sheet can satisfy `min_view_m` and still be unusable. Recorded as deviation I17.

That is separate from the two faults already recorded against this set: the camera is on a residential
street with the item's nominal azimuth of 0.0° and no named subject to aim at (I12), and it stands
where the search put it rather than where a photographer would (I14). Bayside's houses *are* the
subject, so a vinyl-sided wall is not the wrong content — it is the wrong framing of the right
content.

## What matches

* The camera correction worked and is stated: the recorded viewpoint sits 1.5 m *under* the terrain surface, and the camera was moved 35 m onto the nearest real roadbed polygon with 37 m of clear view. Before this test existed the frame was featureless (sd 0.012) and the orchestrator's sweep flagged it.
* The photograph's own EXIF GPS was rejected as mis-tagged at 567 m, so the item's viewpoint was used; the sheet says so.
* The built form is right for outer Queens: two- and three-storey flat-roofed blocks with parapets, set back behind wide sidewalks, with roof-mounted plant and no towers anywhere in the frame.
* Street trees in full June leaf are planted along the kerb with correct canopies, and 21 opaque impostor cards were dropped.
* 2,044 pavement polygons place a wide roadbed, deep sidewalks, 352 crosswalk and 99 parking-lot polygons — the correct proportions for a Queens arterial.
* The New York City flag and cobra-head lamps on davits are modelled at the right sizes.

## What does not match

* The pairing is meaningless: the item is a residential block on 215th Street; the photograph looks south along Interstate 295 from a pedestrian overpass. Nothing in one has a counterpart in the other.
* There are no houses. Bayside at this location is detached and semi-detached two-family homes with front gardens, driveways, garages, porches and fences; the render's blocks are commercial masses. The frame is 35 m from the recorded viewpoint after the correction, which is enough to leave the residential street entirely.
* ~~No vehicles anywhere, in a frame whose reference is 90 % roadway and traffic.~~ — **superseded 2026-09-07.** **263 people and 73 vehicles are in this scene** from one frame of the running simulation; what the reference still has and the render does not is recorded in the section above.
* No road markings: the reference's lane lines, edge lines and the yellow median stripe are the whole subject of its lower half, and the render's roadbed is uniform grey.
* No front gardens, hedges, fences, driveways or parked cars — the vocabulary of a Queens residential block.
* The buildings have no window glazing, no shopfront signage and no texture.
* Props were capped by the triangle budget at 337 placed.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the two halves are unrelated | the item names no subject, the photograph is a highway view 567 m away and its direction was assumed | reference |
| no houses in a residential item | the correction moved the camera 35 m to the nearest roadbed polygon, off the residential street the item names | camera |
| ~~no vehicles~~ superseded | agents are placed now (263 people, 73 vehicles); what remains is framing and occlusion, not absence | reporting |
| no road markings | pavement polygons carry a kind but no stripe geometry or texture | material |
| no gardens, fences or driveways | no dataset the scene reads carries residential lot furniture | data |
| no glazing or signage | kit windows and storefronts carry openings without glass or lettering | material |
