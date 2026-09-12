# Bronx-Whitestone Bridge

`landmark_bronx_whitestone_bridge` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:New York City Sheriff conducting traffic stop on Bronx-Whitestone Bridge.jpg by the Metropolitan Transportation Authority, CC BY 2.0 (https://creativecommons.org/licenses/by/2.0), taken 2024-07-08 08:53:31, 1920x1440. [Commons page](https://commons.wikimedia.org/wiki/File:New_York_City_Sheriff_conducting_traffic_stop_on_Bronx-Whitestone_Bridge.jpg) — the photograph's own view direction is derived from the image at **high** confidence.

**Camera** — 40.80872, -73.83282 (NYC_TM 9880, 12077) at z 5.2 m NAVD88 | azimuth 160.0°, pitch +0.0° | 35 mm on 36 mm (54.4° horizontal) | 1208x906. The camera stands on **the item's recorded viewpoint**: this photograph's own EXIF GPS is **1,047.9 m** away, past the 250 m at which it could still be the same view. The recorded azimuth of 160.0° agrees with the bearing to the subject to **0.1°**. The lens stayed at 35 mm and the axis level, because the subject is 899 m away. The recorded viewpoint was **boxed in** — the azimuth closed **41 m** ahead against the **80 m** needed — so the camera was **moved 8.0 m to the right**, the nearest point in open air, and the destination was scored on the subject's sightline. From there the azimuth is clear for **96 m**, **nothing built stands within 20 m of the lens** and no simulated agent either. Ground under the camera reads **3.612 m** NAVD88 from 16 heightmap samples within 5.0 m, range 3.51 to 3.68 m.

**Sun** — azimuth 89.8°, elevation 35.5° at 2024-07-08T08:53:31−04:00, from the photograph's own **EXIF DateTimeOriginal**; 813.1 W/m² direct normal, sky at strength 0.0345, Filmic, **+1.13 stops and not clamped**. The linear frame's median is **0.082336** against a middle-grey target of 0.18; the physical rule would have given **+0.28 stops** (J83).

**In the scene** — 1,021,828 triangles: 16 building tiles (188,964 tris, none missing, none LOD-substituted), 1 landmark model, in the frame, 7,540 pavement polygons with **0 dropped**, 3,856 props, **no kit at all**, 16 park-ground meshes over 115 surfaces, 14 structures tiles (20,260 tris), 14 vehicles and 1 pedestrian, terrain 141,512 tris at 2.0 m near / 40.0 m far with no holes.

## Verdict — the render is a better picture of this bridge than its own reference photograph, which is a photograph of a Sheriff's patrol car

**The reference does not show the subject.** It is an MTA image of a traffic stop: a Dodge Charger marked SHERIFF filling the lower two thirds, a deputy beside it, queued traffic, a variable-message gantry and a fence. The bridge is the place it was taken, not the thing it depicts. The chooser matched the phrase *Bronx-Whitestone Bridge* in the title, which is the same blind spot recorded as **J93** — it has no evidence of what a photograph is *of*, only where it was taken.

**The render, by contrast, is a creditable suspension bridge.** Both towers stand with the main cable slung between them and suspenders dropped to a deck; the deck runs level across the frame; the approach viaduct comes in from the right on piers. The subject is **899.3 m** away and reads at that distance. For a 1:1 model built from planimetric data this is one of the better landmark results in the pass, and the sheet it sits on cannot demonstrate it.

**The measurements are the closest pairing in the whole pass, and they are a coincidence.** Median **0.4981** against **0.4970** (**1.002×**), the two development offsets **0.007 stops** apart, chroma **0.829×**. A hazy July morning over water and a hazy July morning on a roadway happen to develop to the same grey. The figure that gives it away is contrast: standard deviation **0.451×**, and a fifth percentile of **0.3743** against the photograph's **0.0264** — the reference has a black car interior and hard shadow in it, and the render has nothing darker than pale grass.

**The probe measured the deck, not the towers.** **44.84 m** above a ground of 0.0 m, **43 of 43** rays, on `lm_b_bronx_whitestone.39`, extent **1,040.8 m by 523.5 m** — the deck and its approaches — against a catalogue entry **115.3 m away** carrying **114.9 m**, which is tower height. The aim went to **22.4 m**, half the deck height, and the sightline then reports 13 rays with **11 clear, 9 into nothing and 2 on the subject**: visible fraction **0.154** for a bridge that fills the middle of the picture. Nine rays passing into nothing at a 1,040 m wide subject is the fan spreading across open water either side of the deck.

**One ray is blocked by a golf course.** `t_9_12_park_golf_grass` at **41.4 m** — the Ferry Point golf links between the camera and the water, a park-ground surface standing up into the sightline.

## What matches

* **The bridge is modelled and recognisable at 899 m**: towers, main cable, suspenders, deck and approach viaduct, and the only landmark in range is in the frame, **0.0° off axis**.
* **The development is metered and unclamped**, +1.13 stops from a median linear luminance of 0.082336.
* **The median tone and the development offsets match almost exactly** — 1.002× and 0.007 stops (J83) — even though the two frames show different things.
* **Chroma is 0.829 of the photograph's**, the closest colour match in this queue.
* **The camera walk was minimal and honest**: 8.0 m to the right, and the record names the 41 m closure that forced it and the 96 m clearance that resulted.
* **The clearance is genuinely clear**: nothing built within 20 m of the lens and no agent either — the 8 m rule satisfied with room on both counts.
* **The woodland canopy rule is doing most of the greenery**: **2,195** of the 3,832 impostor cards are procedural canopy stems placed inside mapped woodland polygons.
* **Near-field ground is perfect**: within 150 m, **0.0** of 893 park-surface samples sit under the terrain, median **+0.20 m**.
* **Fourteen structures tiles are imported** with 20,260 triangles, and only 2 of the 16 lack a file — the best structures coverage in this queue.
* **Props were not capped**: 3,856 placed of 3,857 in range, with 1 unmapped.

## What does not match

* **The reference is a photograph of a patrol car.** No render can match it, and no tonal figure on this sheet means anything about the bridge.
* **The probe measured the deck at 44.84 m** where the catalogue entry 115.3 m away carries 114.9 m for the towers, and aimed the frame at 22.4 m (J94).
* **Visible fraction 0.154 with 9 of 13 rays into nothing** — the fan spreads 27.2° across a 1,040 m subject and most of it crosses open water.
* **A golf-course grass surface blocks the sightline at 41.4 m.**
* **Contrast is 0.451 of the photograph's** and the fifth percentile is **0.3743** against **0.0264**: the render has no dark value anywhere in the frame.
* **There is no kit at all.** The record says why in its own words: *kit not placed: no kit_placements.bin in range*. Sixteen building tiles are imported and not one carries a facade-kit file, so every building in the Bronx and Queens shoreline here is a bare shell.
* **Not one of 3,832 trees is drawn from modelled branches.** All are six-triangle cards, **1,031** species were substituted and **7** instances scaled out of band.
* **Fourteen vehicles and one pedestrian.** The table asked for 38 vehicles and 50 people; 73 and 49 were simulated. The reference's own subject is a queue of traffic, and the render's expressway carries almost none.
* **Two of 16 structures tiles have no structures file.**
* **Beyond 400 m the park surface sits under the terrain on 0.205 of 2,971 samples**, minimum **−3.896 m**, after a redrape that moved **305,637** vertices (J85).
* **Seven park-ground surface kinds fall back to the builder's flat colour** — infield dirt, sport court, golf grass, grass field, park grass, recreation grass, bare ground (J40) — and the golf grass is the surface in the foreground of the frame.
* **The foreground is a large featureless grey roadbed** with no markings drawn in the near field, and the park surface behind it breaks into flat facets where the terrain grid coarsens.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the reference is a photograph of a patrol car | the chooser matches the subject's name in a title and has no evidence of what the photograph depicts (J93) | **verification — open, J93** |
| probe 44.84 m against a 114.9 m catalogue entry; aim at 22.4 m | the probe takes the object standing at the subject's coordinate, and on a suspension bridge that object is the deck (J94) | **verification — open, J94** |
| 9 of 13 rays into nothing, visible fraction 0.154 | the fan's width comes from the measured plan extent, 1,040.8 m, so at 27.2° half-angle most rays cross open water beside the deck. J78's fraction is sound; the extent feeding it is a bridge's whole span | **verification — open** |
| a golf-course surface blocking at 41.4 m | the Ferry Point links stand between the viewpoint and the water and the walk's radial search accepted the point anyway | verification — open |
| sd 0.451×, p05 0.3743 against 0.0264 | nothing in the render's frame is dark; the reference's is half car body and shadow | consequence of the reference |
| no kit at all on 16 building tiles | no `kit_placements.bin` exists for any tile in range, and the record says so rather than rendering bare shells silently | **data — open, sixteen tiles without a kit file** |
| 0 of 3,832 trees from modelled branches, 1,031 species substituted | the props budget spends its triangles on cards at this density, and the tree catalogue does not hold most species surveyed here | performance + **data** |
| 14 vehicles, 1 pedestrian | the density table's own figures are small for this shoreline, and the expressway carrying the real traffic is outside the drawn radius | verification |
| 2 of 16 structures tiles without a file | no structures file was built for those two tiles | data — open |
| 0.205 of far park ground under the terrain, min −3.896 m | the terrain grid coarsens to 40 m beyond the near band across Ferry Point's survey shape (J85) | geometry — open, measured |
| seven park surface kinds flat-coloured, golf grass among them | the texture catalogue has no photographic set for any of them (J40) | **declared decision** |
| a featureless foreground roadbed | the near field here is a service road with no surveyed markings, and the pavement set for this tile carries 1,060 white markings placed further out | data |

## What this sheet is good for

It verifies nothing, because its reference is a photograph of a car. It does show that the bridge itself is one of the better pieces of geometry in the build, and it is the clearest case in the pass for the second half of J93's repair: a chooser that can tell a photograph *of* a bridge from a photograph taken *on* one. Two other candidates were fetched for this item and are on disk: `File:Ferry Point Park Boulder, Bronx, NY, USA.jpg`, which is a rock, and `File:LED Lights Installed at Bronx-Whitestone Bridge (26383711714).jpg`, which is a photograph of the bridge itself. The third is the one this sheet should be using.
