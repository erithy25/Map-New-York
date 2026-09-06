# Brooklyn Heights Promenade looking at Lower Manhattan

`promenade_lower_manhattan` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Brooklyn Heights Promenade January 2023 006.jpg by Kidfly182, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2023-01-20 14:33:49, 1920x1440. [Commons page](https://commons.wikimedia.org/wiki/File:Brooklyn_Heights_Promenade_January_2023_006.jpg)

**Camera** — camera 40.69616, -73.99778 (NYC_TM -4038, -426) z 21.7 m NAVD88 | azimuth 324.4deg pitch +0.0deg | 28 mm on 36 mm (65.5deg horizontal) | 1208x906. View direction: 324.4 deg, the bearing from this photograph's own GPS position to One World Trade Center; heading and position both come from the photograph.  The item's recorded azimuth is 324.3 deg, 0.1 deg away, and belongs to its nominal viewpoint. Aim: level optical axis (the subject is 2265 m away; anything that far is photographed with a level camera).

**Sun** — azimuth 216.8°, elevation 20.4° at 2023-01-20T14:33:49-05:00 (EXIF DateTimeOriginal).

**In frame** — 76/100 building tiles (1,436,772 tris), 32 landmark models, 2,124 pavement polygons, 158 props, 1,246 facade-kit pieces; 3,865,533 triangles; ground mesh 373² at 2.5 m near / 40.0 m far.

**Verdict — the Lower Manhattan silhouette is right and One World Trade Center is where it belongs; everything below the skyline — the promenade the photographer is standing on, Brooklyn Bridge Park, the piers, the river surface — is a blank grey plane**

## What matches

* The skyline profile is recognisably Lower Manhattan seen from the north-east: One World Trade Center with its spire at the centre of the frame where the subject bearing puts it, the Battery cluster stepping down to the left, the Financial District ridge and the low Seaport buildings falling away to the right.
* Relative building heights read correctly. One WTC clearly dominates; 70 Pine, 40 Wall Street and the 8 Spruce Street slab are all present at plausible proportions against it.
* The camera stands on the photograph's own EXIF GPS, 30 m from the item's nominal viewpoint, and the heading (324.4 deg) is measured from that point to One WTC — the two frames face the same way to within 0.1 deg.
* The waterline is in the right place: the Manhattan shore crosses the frame at the same height as in the photograph, and the East River occupies the same band.
* The Sun is placed from the photograph's own EXIF timestamp (2023-01-20 14:33 EST, elevation 20.4 deg, azimuth 216.8 deg), so the towers are lit from the same side as in the reference.

## What does not match

* The bottom 45 % of the render is one featureless light-grey plane. The photograph's foreground is the promenade railing, a line of bare London planes, the sloping lawn of Brooklyn Heights, then Brooklyn Bridge Park with Pier 3, the Squibb bridge and a marina. None of that is in the render: the ground mesh is bare terrain with a hard straight edge where the fill ends.
* 158 props and 1,246 kit pieces were placed within the new near-field ring and not one of them is visible in the frame. They sit at street level below and behind the promenade parapet, so the viewpoint's own furniture — railing, benches, lamps — is still absent. The promenade structure itself is not modelled at all.
* Every tower is a flat pastel solid: pale pink, pale blue, white. The photograph's towers are dark glass with strong vertical banding and a wide tonal range from near-black to specular white. The render has no glass reflectance, no spandrel banding, no visible fenestration at 2 km, so the skyline reads as a massing study rather than a city.
* The river is a mirror. Roughness 0.06 with no wave normal makes the East River a perfect reflector of the sky and the towers; the real surface at this distance is a dark, broken, largely non-reflective grey. The mirrored towers below the waterline are the most conspicuously unreal thing in the frame.
* The sky is a clear Nishita gradient; the reference is three-quarters filled with heavy winter stratocumulus. That alone accounts for most of the difference in overall tonality and for the absence of any diffuse-lit modelling on the towers' shaded faces.
* No boats, no Governors Island terminal, no piers, no vehicles on the FDR, no people on the promenade. The photograph has a ferry mid-river and cars on the elevated highway.
* 24 of the 100 tiles in the 5 km scene had no building shell on disk at all (t_-10_-1, t_-10_-2, t_-10_0, t_-7_-1, t_-7_-3 and 19 more), so the Jersey City bank behind Lower Manhattan was empty. **This finding was correct and it started the work that built New Jersey**: 231,382 shells across 486 tiles now stand there, and the verification scene loads them. Two corrections to this bullet, both established by that work and recorded here rather than quietly edited away:
  * **The photograph does not show the Newport towers at that point.** Newport lies at bearing 316.9°, 4.68 km out, subtending 1.72° against an 8.09° Manhattan skyline, so it cannot clear it from this camera. What is visible at the far left, just above the Battery Maritime Building, is the southern Jersey City / Paulus Hook cluster.
  * **Building New Jersey changes 42 pixels of this frame.** From this camera the Jersey City waterfront lies *behind* Lower Manhattan, which is half the distance and therefore angularly taller. A per-column analysis over the frame's 1,208 columns finds 13 columns (bearings 296.0–296.6°) where a New Jersey roof clears the New York skyline, by at most 5.6 px. At the towers' published heights it would be 17 columns and up to 27.8 px. The shells are real — `blender_out/verify_nj/jersey_city_bank_sheet.png` shows the same bank from the Hudson, bare before and a full skyline after — but this particular frame was never going to show them as a cluster, and the source's height truncation (deviation B11a) makes it a sliver rather than a ridge.
* A large white flat-topped slab stands on the Brooklyn shore at the right of the frame at roughly twice the height of its neighbours; it has no counterpart in the photograph. **The orchestrator checked the suspected cause and it is not a wrong height.** Every one of the 12,128 Brooklyn buildings within 2.5 km of this camera carries `height_source = SRC_LIDAR`, i.e. a measured height, and the tallest of them is 340 Flatbush Avenue Extension at 315.47 m — The Brooklyn Tower, published at 325 m, so the height is right to within the difference between its roof and its pinnacle. Nothing in that radius has an anomalous height. The remaining explanations are that the slab is a real building rendered as a flat massing box where the real one has a sculpted or setback crown, or that it is outside the 2.5 km radius checked. **Open**, with the height hypothesis eliminated.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| no promenade, no park, no piers in the foreground | the Brooklyn Heights Promenade deck, Brooklyn Bridge Park and the East River piers are structures, not buildings, and no stage produces them; the terrain heightmap flattens them into bare ground | geometry |
| no railing, benches or trees at the viewpoint | the props that exist are placed at street level from props.parquet; the promenade deck they belong on is not modelled, so they sit below the parapet line | geometry |
| flat pastel towers, no glass | building shells carry a per-material base colour only; there is no facade texture, no glass BSDF and no spandrel banding at LOD1/LOD2 | material |
| mirror-flat river | the water material is roughness 0.06 with no normal map and no wave displacement | material |
| clear sky against a clouded photograph | the sky is a Nishita atmosphere at the true Sun position with no cloud layer; the reference weather is not reproduced | lighting |
| no boats, no vehicles, no people | no stage places moving objects into a still verification frame | data |
| 24 empty tiles on the New Jersey bank | ~~no tile_buildings.glb exists for those tiles; the shell build covers the five boroughs, not New Jersey~~ **closed**: New Jersey is built (486 tiles, 231,382 shells) and the verification scene loads it. The bank is no longer empty; it contributes 13 columns of this frame because it sits behind a nearer, angularly taller Manhattan | data |
| an over-tall white slab on the Brooklyn shore | **not a height error** — checked: all 12,128 Brooklyn buildings within 2.5 km carry a measured LiDAR height and none is anomalous (tallest is The Brooklyn Tower at 315.47 m against a published 325 m). Most likely a real building whose shell is a flat massing box where the real crown is sculpted | geometry |
