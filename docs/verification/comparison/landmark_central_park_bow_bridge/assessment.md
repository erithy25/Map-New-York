# Central Park: Bow Bridge

`landmark_central_park_bow_bridge` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Bow Bridge over the Lake, Central Park, Manhattan, New York.jpg by Christian David, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2026-04-18 08:28:54, 1920x1080. [Commons page](https://commons.wikimedia.org/wiki/File:Bow_Bridge_over_the_Lake,_Central_Park,_Manhattan,_New_York.jpg) — the photograph's own view direction is derived from the image at **high** confidence.

**Camera** — 40.77603, -73.97164 (NYC_TM -1827, 8443) at z 19.2 m NAVD88 | azimuth 200.4°, pitch +2.1° | 35 mm on 36 mm (54.4° horizontal) | 1280x720. Position and heading both come from the photograph: its own EXIF camera GPS, **177.4 m** from the item's recorded viewpoint, and 200.4° is the bearing from there to the subject. The item's recorded azimuth of 322.9° is **122.5° away** and belongs to its nominal viewpoint on the other shore. The lens stayed at 35 mm and the axis was tilted **+2.1°** to the subject's mid-height. The camera was not moved: the eye point stands on `t_-2_8_park_park_ground_grass` and there is no nominal viewpoint to walk to. The azimuth is clear for **86.8 m** against the 20.0 m needed, the nearest built thing is that grass surface **7.3 m** away at −16.1° pitch, and no simulated agent stands within 60 m. Ground under the camera reads **17.592 m** NAVD88 from 16 heightmap samples within 5.0 m, range 17.12 to 18.36 m.

**Sun** — azimuth 97.0°, elevation 24.8° at 2026-04-18T08:28:54−04:00, from the photograph's own **EXIF DateTimeOriginal**; 717.4 W/m² direct normal, sky at strength 0.0380, Filmic, **+2.14 stops and not clamped**. The linear frame's median is **0.040873** against a middle-grey target of 0.18; the physical rule would have given **+0.80 stops** (J83).

**In the scene** — 2,601,966 triangles: 6 building tiles (328,542 tris, none missing, none LOD-substituted), 7 landmark models of which 1 falls inside the 54.4° frame, 7,883 pavement polygons with **0 dropped**, 5,305 props, **140** kit pieces, 25 park-ground meshes over 704 surfaces with **2,897 faces cut** for landmark ground, 2 structures tiles (1,404 tris), **0 vehicles and 0 people**, terrain 85,944 tris at 2.0 m near / 40.0 m far with no holes.

## Verdict — the bridge is modelled well enough to recognise from its arch and balustrade, and a pale rectangular mass stands in the Lake beside it, cutting across the far abutment

**The bridge reads.** A shallow cast-iron arch springs from a stone abutment, carries a pierced balustrade, and reflects in the water — and the render even has the colour right, the pale greenish-cream that Bow Bridge is actually painted. The sightline is sound: 13 rays, **13 clear, 8 on the subject**, 3 into nothing, visible fraction **0.615**. The camera stands where the photographer stood.

**Then there is a building in the Lake.** A pale rectangular mass occupies the right of the frame, standing in the water at about the bridge's far abutment and cutting across it, with a second slab at the near abutment on the left. Nothing in the record names either: the clearance walk reports the azimuth clear for 86.8 m and the nearest built thing as a grass surface 7.3 m away, and there is no measurement anywhere in `render.json` of what occupies the frame (**J92**). The masses are drawn from a building tile — 6 tiles are imported with 328,542 triangles — and on the Lake's own surface that can only be a shell whose footprint or elevation is wrong.

**The probe found something taller than the bridge.** **8.14 m** above a ground of 16.55 m, but on only **8 of 43** rays — the lowest fabric ratio on a landmark sheet in this queue apart from Rockefeller Center — against a catalogue entry 7.2 m away carrying **3.8 m**. The bridge's own deck is about four metres over the water; 8.14 m is the height of something standing on or beside it. Because 8.14 m is still under the 12 m fan floor, the aim fell to **4.1 m**, which happens to be the right height for the bridge.

**The tonal gap is a spring morning against a flat model.** The render is brighter — mean **1.183×**, median **1.206×** — and much less colourful: chroma **0.0835** against **0.2021**, a ratio of **0.413**. The reference is new leaf green over green water at 24.8° sun elevation; the render's canopy is impostor cards and its water is a mirror.

## What matches

* **The arch, the balustrade and the abutment read at 39 m**, and the paint colour is right.
* **The sightline is sound**: 13 of 13 rays clear, 8 on the subject, clear fraction **1.0**.
* **The development is metered and unclamped**, +2.14 stops from a median linear luminance of 0.040873.
* **The woodland canopy rule carries the park**: **3,542** of the 4,814 impostor cards are procedural canopy stems placed inside mapped woodland polygons, and **0** cards were dropped.
* **Near-field ground is perfect**: within 150 m, **0.0** of 172 park-surface samples sit under the terrain, median **+0.197 m**.
* **The landmark-ground rule did real work**: **2,897** park-ground faces cut, over 704 surfaces.
* **The car-free rule works here** — **11 vehicles dropped** because the road graph put them on Central Park's East, West, Terrace or Center Drive, which have carried no private traffic since 2018 -- and this is the rule whose absence on Governors Island is recorded as J95.
* **The record is honest about the empty scene**: *the simulation put no agent on a paved surface inside the frame's radius*, with 4 vehicles and 5 pedestrians dropped for having no roadway or sidewalk under them.
* **Props were not capped**: 5,305 placed of 5,373 in range.

## What does not match

* **A pale rectangular mass stands in the Lake** and cuts across the bridge's far abutment; a second slab sits at the near one. Neither is named by any measurement in the record (J92).
* **Only 8 of 43 probe rays found built fabric**, and the 8.14 m measured is taller than the 3.8 m the catalogue entry 7.2 m away carries.
* **The water is a flat mirror.** It reflects the bank and the bridge cleanly and carries none of the reference's green depth, weed or surface texture.
* **Chroma is 0.413 of the photograph's**, 0.0835 against 0.2021.
* **The render is brighter and flatter**: mean **1.183×**, median **1.206×**, standard deviation **0.818×**, and a fifth percentile of **0.2371** against **0.1249** — no deep shade under the canopy.
* **Not one of 4,814 trees is drawn from modelled branches.** All are cards; **704** species were substituted and **9** instances scaled out of band.
* **Four of 6 structures tiles in range have no structures file**, and the 2 that exist contribute **1,404 triangles**.
* **Beyond 400 m the park surface sits under the terrain on 0.1556 of 1,080 samples**, minimum **−5.247 m**, after a redrape that moved **656,583** vertices — the largest redrape in the pass (J85).
* **Thirty-eight props across six kinds were wanted in range and have no asset**: 12 artwork, 8 drinking fountain, 7 parks building, 6 memorial, 4 parks comfort station, 1 passenger-information sign. In this part of Central Park those are Bethesda Terrace's fountain, the Ramble's rustic shelters and the statuary along the Mall.
* **140 kit pieces of 496 in range**, with 356 suppressed under landmark shells — so the skyline blocks behind the trees are bare boxes.
* **Six park-ground surface kinds fall back to the builder's flat colour** — infield dirt, sport court, park grass, recreation grass, rink ice, bare ground (J40).
* **The background skyline is plain massing**: the towers visible over the trees are boxes with flat colour, where the photograph shows glass, setbacks and reflections.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| a building mass standing in the Lake | a building shell whose footprint or ground elevation puts it on the water surface; nothing in the record measures what fills the frame, so the object is not named (J92) | **geometry — open, and unidentified because J92 is open** |
| 8 of 43 probe rays on fabric; 8.14 m against a 3.8 m catalogue entry | the probe's rays mostly pass the bridge deck, and the object it did strike is taller than the bridge itself (J94's family, on a low horizontal subject) | **verification — open** |
| the water is a flat mirror | water is a flattened surface at a single elevation with no wave, weed or depth model | **declared scope** |
| chroma 0.413×, p05 0.2371 against 0.1249, sd 0.818× | impostor-card canopy with no interior shade, and a mirror lake, against new leaf green over green water | performance + **declared scope** |
| 0 of 4,814 trees from modelled branches, 704 species substituted | the props budget spends its triangles on cards at this density, and the tree catalogue does not hold most species surveyed in the Ramble | performance + **data** |
| 4 of 6 structures tiles without a file | no structures file was built for those tiles | **data — open, four tiles unbuilt** |
| 0.1556 of far park ground under the terrain, min −5.247 m | the terrain grid coarsens to 40 m beyond the near band across Central Park's rolling survey shape (J85) | geometry — open, measured |
| 38 props across six kinds unmapped | no asset exists for those kinds, and here that kind is Bethesda Terrace's fountain and the Mall's statuary | **data — open, measured** |
| 140 kit pieces of 496 in range | 356 suppressed where landmark shells stand in place of the tile's buildings; the kit budget was not reached | declared rule |
| a plain-massing background skyline | the tile builder models massing from footprint and height, and there is no per-building facade colour (J66 remainder) | geometry — declared scope + **data, open** |
| six park surface kinds flat-coloured | the texture catalogue has no photographic set for any of them (J40) | **declared decision** |
