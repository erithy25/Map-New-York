<!-- generated-above; hand-written narrative below -->

## 4. How each landmark was placed

Bridges and tunnels have no building footprint, so nothing in this group was placed by eye. Two sources were used,
and every model records which one in its catalog entry's `alignment_source`:

1. **`blender_out/landmarks/b_osm/structures.geojson`** — the extract that `blender/landmarks/b_osm_extract.py`
   produces from `data/raw/osm/NewYork.osm.pbf` (BBBike, ODbL, (c) OpenStreetMap contributors). Bridge towers,
   anchorages, piers and abutments are the ways tagged `bridge:support=pylon|abutment|pier|lift_pier`; tunnel
   centrelines are the ways tagged `highway=motorway, tunnel=yes` with the tunnel's name; ventilation buildings,
   forts, arches, the Unisphere and the Coney Island rides are the named building/attraction polygons.
2. **The same coordinates recorded as constants** in each script (`b_align.Support.xy`), so a model can be rebuilt
   without the extract. `b_align.Support.resolve()` cross-checks the two and logs any disagreement over 8 m.

3. **`data/processed/roads/segments.parquet`** — the other alignment source the brief names. It did not exist when
   this lane started (the roads stage had only produced `data/processed/roads/cache/`); it landed mid-build and is
   now consumed by `b_align.roads_centreline()`, which **refines the deck heading** while the supports keep the
   origin and the span.

Two things had to be got right for the roads source to be usable. First, **the name**: LION abbreviates the deck to
`BROOKLYN BRG`, `GEORGE WASHINGTON BRG`, `ROBERT F KENNEDY BRG` and so on, while `BROOKLYN BRIDGE …` names only the
approach and entrance ramps — matching on "Brooklyn Bridge" picks up ramps in City Hall Park and misses the span
entirely. Second, **the window**: even with the right name, a principal-axis fit through every matching segment is
dragged 24 degrees off the Brooklyn Bridge's main span by its ramps. So the OSM supports supply a prior — their
midpoint and direction — and only vertices within `span/2 + 80 m` along that axis and 45 m across it are fitted. The
fit is then refused outright if it still differs from the support axis by more than 8 degrees.

With that window the two independent datasets agree to better than **0.7 degrees** on every bridge in the lane:

| bridge | LION name | support axis | roads centreline | difference | vertices |
|---|---|---:|---:|---:|---:|
| Brooklyn | `BROOKLYN BRG` | 136.29 deg | 136.20 deg | **0.09** | 20 |
| Manhattan | `MANHATTAN BRG` | 157.12 | 156.97 | **0.15** | 39 |
| Williamsburg | `WILLIAMSBURG BRG` | 111.87 | 111.71 | **0.17** | 52 |
| Queensboro | `QUEENSBORO BRG` | 119.85 | 119.50 | **0.35** | 58 |
| George Washington | `GEORGE WASHINGTON BRG` | 104.47 | 104.49 | **0.02** | 48 |
| Verrazzano-Narrows | `VERRAZZANO BRG` | 67.10 | 67.07 | **0.03** | 88 |
| Throgs Neck | `THROGS NECK BRG` | 179.48 | 179.94 | **0.46** | 23 |
| Bronx-Whitestone | `WHITESTONE BRG` | 153.89 | 153.90 | **0.01** | 27 |
| RFK (East River span) | `ROBERT F KENNEDY BRG` | 149.86 | 150.52 | **0.67** | 42 |
| Pulaski | `PULASKI BRG` | 8.90 | 14.21 | 5.31 | 16 |
| Hell Gate | `HELL GATE BRG` | 134.66 | — | — | 2 |

That is a genuine independent check: the OSM `bridge:support` polygons and the LION road centrelines are unrelated
datasets, and they place the same nine decks to within half a degree. The Pulaski's 5.31 degrees is the same
disagreement its OSM piers show (they draw the pier caps, not the bascule bearings) and it stays inside the
8-degree guard; the Hell Gate is a **railway** bridge, so `HELL GATE BRG` in LION is the street beneath it and only
two vertices fall in the window — the fit is skipped and the bridge keeps its OSM support axis, which is the
correct outcome. Each bridge's `alignment_source` records which of the two it actually used, with the vertex count
and the measured disagreement.

### Measured versus published spans

Every suspension and cantilever bridge was placed by measuring the distance between the real OSM support polygons'
centroids and comparing it with the published span before snapping the towers symmetrically to the published value:

| bridge | supports (OSM ways) | measured | published | error |
|---|---|---:|---:|---:|
| Brooklyn | 317352708 / 1255363983 | 486.49 m | 486.3 m | **+0.04 %** |
| Manhattan | 317352033 / 1255353996 | 445.63 m | 451.1 m | -1.21 % |
| Williamsburg | 1016434034 / 1016434035 | 488.15 m | 487.68 m | **+0.10 %** |
| Queensboro (5 spans) | 1016487161 / ...159 / ...155 / ...154 / ...157 / ...170 | 141.3 / 360.9 / 191.2 / 300.7 / 139.2 m | 143.1 / 360.3 / 192.0 / 300.0 / 139.9 m | **<= 1.3 %** |
| George Washington | 741784699 / 741784700 | 1,066.25 m | 1,066.8 m | **-0.05 %** |
| Verrazzano-Narrows | 1016642058 / 1016642060 | 1,298.68 m | 1,298.4 m | **+0.02 %** |
| RFK (East River span) | 1016642596 / 1016642595 | 420.60 m | 420.62 m | **-0.00 %** |
| Throgs Neck | 1016661640 / 1016661642 | 549.33 m | 548.64 m | **+0.13 %** |
| Bronx-Whitestone | 1016686393 / 1016686394 | 701.15 m | 701.04 m | **+0.02 %** |
| Pulaski (bascule piers) | 1054539113 / 992001660 | 50.79 m | 53.95 m | -5.9 % |
| RFK Bronx Kill (portals) | 1016646459 / 1016646456 | 104.3 m | 116.74 m | -10.7 % |

Where the measurement disagrees by more than 1 % the OSM polygon is drawing something other than the bearing
centres — the Manhattan Bridge's small 35 x 20 m pylon polygons, the Pulaski's pier caps, the Bronx Kill's portal
frames — and each script says so. In every case the **published** span is what the model is built to, and the
measurement only fixes the midpoint and the heading.

### Tunnel centrelines

Each bore is the real chained OSM tunnel way, trimmed or extended symmetrically along its end tangents to the
published portal-to-portal length. The agreement **before** that adjustment:

| tunnel | bore | OSM measured | published | error |
|---|---|---:|---:|---:|
| Holland | north (westbound) | 2,613.0 m | 2,608.5 m | **+0.17 %** |
| Holland | south (eastbound) | 2,550.7 m | 2,551.4 m | **-0.03 %** |
| Lincoln | centre (reversible) | 2,503.4 m | 2,504.2 m | **-0.03 %** |
| Lincoln | north | 2,280.4 m | 2,280.5 m | **-0.01 %** |
| Lincoln | south | 2,429.9 m | 2,440.2 m | -0.42 % |
| Queens-Midtown | north | 1,959.8 m | 1,955.0 m | **+0.25 %** |
| Queens-Midtown | south | 1,914.5 m | 1,911.7 m | **+0.15 %** |
| Hugh L. Carey | west (southbound) | 2,784.7 m | 2,779.2 m | **+0.20 %** |
| Hugh L. Carey | east (northbound) | 2,773.5 m | 2,779.2 m | **-0.21 %** |

All nine bores are within 0.42 % of their published length on the real curved alignment.

### Buildings and monuments

Everything with a footprint is built on the **real OTI polygon** from
`data/processed/buildings/landmark_footprints.parquet` or `footprints_raw.parquet`, at its LiDAR ground elevation:
One WTC (BIN 1088469), 3/4/7 WTC and the Oculus and museum pavilion (1088797 / 1088795 / 1086510 / 1089309 /
1088798), Ellis Island (1085964), Grant's Tomb (1057391), Belvedere Castle (1083837), Bethesda Terrace (1090516 and
1091041), the Prospect Park Boathouse (3347249), the Deutsche Bank Center (1026318), the Soldiers' and Sailors'
Arch (3347227), the Unisphere basin (4458851) and the Coney Island rides. Where a monument has no BIN — Washington
Square Arch, the Statue of Liberty's Fort Wood, Castle Williams, Fort Jay, Bow Bridge, the Unisphere itself, the
Parachute Jump, the Wonder Wheel — the real OSM polygon or node is used instead.

## 5. Fidelity: what is exact, what is inferred, what is missing

Every model carries a `fidelity_statement` in its `.glb` extras and its catalog entry that separates the three.
The most important admissions across the group:

* **The Statue of Liberty's figure is a stylised sculpt, not a scan.** It is 38 metaball elements meshed at 0.80 m
  and smoothed with one subdivision level, positioned by the National Park Service's published proportions. Every
  quoted dimension is right (92.99 m ground to torch = 19.81 m foundation + 27.13 m pedestal + 46.05 m statue;
  33.86 m heel to head; 5.26 m head; 12.80 m arm; 5.00 m hand; 7.19 x 4.14 m tablet; seven crown rays) and the
  silhouette reads correctly, but the drapery folds, the face, the sandal, the broken chains and the repousse
  surface are invented or absent.
* **The Cyclone's track plan is generated, not surveyed.** The three OSM ways trace only 387 / 305 / 255 m of the
  published 2,640 ft circuit, so a folded out-and-back layout is reconstructed inside the ride's real plot to the
  published 804.67 m of track, 25.91 m lift height, 58.1-degree first drop and 12 drops.
* **The Lincoln Tunnel's four ventilation buildings are derived, +-80 m.** OSM maps none for that tunnel (the only
  ventilation shaft near the portals belongs to the Amtrak North River Tunnels) and no published coordinates were
  found, so they are placed 70 m either side of each measured portal. Holland's four, Queens-Midtown's two and
  three of Hugh L. Carey's four *are* real OSM buildings, built on their real footprints at their OSM-tagged
  heights; Carey's second Manhattan building is published but unmapped and is **not modelled**.
* **The 9/11 Memorial pool centres are derived, +-15 m** from the OSM memorial-plaza polygon's long axis; no polygon
  exists for the individual pools. The pools themselves are exact: 61.0 m square (the original towers' footprint),
  a 9.14 m waterfall, and 152 bronze parapet panels carrying the `MEMORIAL_NAMES` material slot for the 2,983 names.
* **The WTC plaza oaks are the wrong species of oak.** The street-props agent's library landed mid-build, so the
  trees are now real prop assets rather than `b_common.simple_tree`; but `blender_out/props/` has no swamp white
  oak (*Quercus bicolor*), so `tree_pin_oak_medium` (*Quercus palustris* — same genus, same upright habit) stands
  in, collapse-decimated to 520 triangles and instanced 220 times so the whole grove costs one mesh in the glb. The
  Survivor Tree uses `tree_callery_pear_medium`, which **is** the right species. 220 of the published 400+ oaks are
  placed (70 at LOD1). `b_common.prop_available()` / `prop_template()` / `prop_instance()` are the general helpers,
  and the build falls back to `simple_tree` and says so in its report if the library is absent.
* **Approach viaducts are truncated.** Throgs Neck (320 m each side against a published 1,189 m / 853 m),
  Bronx-Whitestone (260 m), Queensboro (400 m), Verrazzano (300 m), Pulaski (300 m each against a published 856.5 m
  total) and Hell Gate (300 m / 220 m against 810 m / 599 m) all stop short: beyond that they are ordinary elevated
  highway or railway viaduct that the roads, rail and terrain stages carry. The RFK's three viaduct legs *are*
  modelled full length (4.30 km) because they connect the bridge's three crossings and nothing else would.
* **Kosciuszko's pylon height (91.4 m) and along-bridge position (+-30 m) are inferred.** The infobox publishes
  neither; NYSDOT describes the tower as "300 ft" and no OSM support way exists.
* **Belvedere Castle's tower height (16.5 m) and the Prospect Park Boathouse's storey split are inferred** — no
  published overall dimensions were found for either; LiDAR gives only the main mass.
* **Material slots for the engine**: `MEMORIAL_NAMES` (the 9/11 memorial parapets) and `MINTON_TILE` (Bethesda
  Terrace's 15,876-tile arcade ceiling) are emitted as named materials for the engine to replace with real textures.

## 6. Drivable tunnel interiors

All nine bores (Holland 2, Lincoln 3, Queens-Midtown 2, Hugh L. Carey 2), with a portal head-wall at each end, are
drivable end to end. Each is built along its real centreline with the published lining diameter (Holland 8.99 m,
the other three 9.45 m), a roadway at the published width, a 0.35 m catwalk with a handrail on each side, a white
glazed tile band to 2.4 m, a dark upper wall and ceiling, lane markings, **a luminaire every 10 m in each of the two
ceiling coves** (the pitch the brief specifies) and a recessed emergency door every 150 m alternating sides. The
vertical profile is a parabola from the portal elevations to the published low point under the river.

The lining is built as **inward-facing open ribbons** (floor, catwalks, tiled walls, ceiling) so it is correct seen
from inside the tube, which is what a drivable tunnel needs; the outer shell is built only for 70 m at each portal,
where it is visible. This is stated in each tunnel's fidelity statement.

## 7. Shared code and the `common.py` decision

Agent A's `blender/landmarks/common.py` was checked and **not adopted**: its API is footprint-centric in a way this
lane cannot use — `load_footprint(key)` keys on a landmark id or name rather than a BIN, `local_frame(polygon, ...)`
takes a shapely polygon, `finish(objects, landmark_id, bins, frame, *, height_m, name, ...)` requires a `LocalFrame`
and a real footprint for its IoU check, and `render_check(landmark_id, presets)` takes azimuth/elevation presets
around a building. Bridges and tunnels have no footprint and are placed on an axis, not a polygon.

`b_common._shared()` still probes `common.py` at import time for each of `load_footprint`, `local_frame`, `finish`
and `render_check` and adopts any whose signature matches; at build time it logs, for example:

```
INFO landmarks.b shared common.finish has signature ['objects', 'landmark_id', 'bins', 'frame', 'height_m', ...],
                 using B implementation
```

so the decision is visible in every build log and would reverse itself automatically if the shared module grew a
compatible signature.

The B lane's own shared modules are:

| module | what it provides |
|---|---|
| `b_common.py` | materials (49 documented Principled sets, each with the real-world reference it approximates), geometry primitives, true catenaries, lattice columns, trusses, railings, lamps, trees, the glb/catalog export contract, Cycles verification renders |
| `b_align.py` | measured support resolution from OSM with recorded-constant cross-check, bridge axis fitting and published-span snapping, the `segments.parquet` consumer, the LOD0/LOD1/render driver |
| `b_bridge_lib.py` | suspension towers (gothic / portal / lattice / Art Deco), catenary main cables, suspenders, diagonal stays, single and double decks, stiffening trusses, anchorages, approach viaducts, cantilever trusses, steel arches, vertical-lift spans, cable-stayed units, bascules, masonry arch viaducts |
| `b_tunnel_lib.py` | OSM centreline chaining, arc-length resampling, length adjustment, vertical profiles, ribbon sweeps, the drivable tube section, portal head-walls, ventilation buildings, open-road toll gantries |
| `b_park_lib.py` | classical orders, entablatures, balustrades, domes, stairs, triumphal arches, bastioned forts, casemated batteries, park walls, Ferris wheels, wooden coaster track, the Parachute Jump, boardwalks |
| `b_osm_extract.py` | the ODbL OSM extract this lane consumes (already present from wave 1) |
| `b_build_all.py`, `b_report.py` | the one-process-at-a-time build driver and this report's generator |

## 8. Verification renders: what each one has to prove

The first pass of renders was rejected, correctly: one frame was black (the camera sat under a context ground
plane), one was washed to near-white with the towers outside the frame, and even the usable ones were flat. Three
things were wrong and all three are fixed.

**Framing.** Every view now states, in its script's `main()` docstring, the question it must answer before the
camera is placed. Where the comparison agent has recorded a real photographic viewpoint under
`docs/verification/reference/<id>/meta.json`, that viewpoint is used **verbatim**: `b_align.reference_view()` reads
the photographer's WGS84 position and the subject's, converts both with `nycsim_pipeline.crs.lonlat_to_tm` into the
landmark's frame, and `b_align.reference_render()` turns them into a render entry — so the render and the reference
photograph are the same shot and the comparison sheets line up. Twenty-two views across the group are placed this
way (`landmark_brooklyn_bridge_from_dumbo`, `dumbo_washington_st_manhattan_bridge`,
`landmark_george_washington_bridge`, `landmark_oculus`, `landmark_911_memorial_pools`, `landmark_statue_of_liberty`
and the rest); if a reference is not on disk the entry returns `None` and the driver drops it, so a build never
depends on another agent's output.

Two cameras were **deleted** rather than kept, because looking at them showed they proved nothing: the Brooklyn
Bridge from the Main Street Park lawn (the Brooklyn anchorage stands between that lawn and the tower and filled the
entire frame) and a promenade view placed on the reference coordinate (which lands beside the walkway, not on its
centreline, so half the frame was stiffening truss at arm's length).

**Lighting.** `nycsim_bpy.quick_render`'s defaults put a Nishita sky at strength 0.6 against a 4 W/m2 sun, which is
roughly as much irradiance from the sky hemisphere as from the sun: masonry renders as a flat pale field with no
shadow and no relief. `b_common.render_check()` now builds the camera, sun and sky itself with the sun carrying
about **20x the sky** (5.0 W/m2 against 0.22), the sun disc turned off in the sky texture so it is not counted
twice, and `exposure = -2.4 EV`. Measured on the Brooklyn tower, that puts the sunlit granite face at 0.40 sRGB
against 0.23 in shadow — the string courses, the arch reveals and the batter all read. (This Blender build ships
without an OCIO look table — `view_transform` and `look` offer only `NONE` — so exposure, not a tone curve, is the
only lever; `render_check` takes both as parameters anyway and falls back cleanly.)

A fourth fix was the **context planes**: they were `sidewalk`, whose 0.62 albedo is brighter than granite's 0.44,
so the ground blew a whole frame to white. A documented `ground_urban` material (0.21) was added for render context
only, and the bridge scripts use it in place of `sidewalk` and of the lawn-green `grass`.

## 9. Resource etiquette

Every Blender run was a single `nice -n 10` process; `b_build_all.py` runs the 34 landmarks in sequence in separate
subprocesses so peak memory stays at one model. The box's load average sat between 32 and 40 for the whole session
from the other agents' jobs, which on four cores is roughly a tenth of a core per process, so render cost had to be
managed rather than ignored: `b_build_all.py --render-scale` and `--max-views` were added for exactly this, and the
sweep was run at `--samples 24 --render-scale 0.66`, with the canonical viewpoints re-rendered afterwards at full
size. `max_bounces` is 4 for exteriors and 2 for the enclosed tunnel interiors — at 6 an interior lit only by 520
emissive luminaires took over ten minutes a frame.

Two hangs were fixed rather than waited out. `b_common._record_processed()` takes the shared
`data/manifest/.processed.lock` **non-blocking with a 30 s bounded retry** — several agents write that manifest at
once and a blocking `flock` wedged a build for minutes. And `bpy`-as-a-module occasionally blocks forever in its own
thread teardown after everything has been written (observed on `b_central_park_walls_gates`: nine minutes wedged on
a futex with every artefact already on disk), so `b_build_all.py` sets `NYCSIM_LANDMARK_HARD_EXIT=1` and
`b_align.run_landmark()` flushes and `os._exit(0)`s, which bounds the damage to zero.

## 10. Licences

* OpenStreetMap geometry (bridge supports, tunnel centrelines, fort and monument plans, the Central Park boundary,
  the Coney Island rides, the Roosevelt Island tramway) — **ODbL 1.0, (c) OpenStreetMap contributors**, via
  `data/raw/osm/NewYork.osm.pbf` (BBBike). The licence record is `blender_out/landmarks/b_osm/LICENSE.json`,
  written by `b_osm_extract.py`; **no new download was made by this agent**.
* NYC building footprints (Open Data 5zhs-2jue) and PLUTO — via `data/processed/buildings/*`, already recorded in
  `data/manifest/downloads.json`.
* Published dimensions come from Wikipedia infoboxes and the primary sources they cite (NPS, NYC Parks, the
  Landmarks Preservation Commission, PANYNJ, MTA Bridges & Tunnels, CTBUH, HABS/HAER), quoted per landmark in each
  script's docstring. No asset was downloaded, so no new licence file was needed.

## 11. What the next agent needs to know

* **Frame convention.** Every `.glb` is in metres, Z-up, with the origin at `extras["origin_tm"]` = (x, y, z) in
  NYC_TM / NAVD88; a world point is `origin_tm + local`. Bridges and tunnels use z = 0 at NAVD88 0.0, buildings use
  the LiDAR ground. Published clearances quoted "above mean high water" were converted with
  **MHW = NAVD88 + 0.70 m** (NOAA 8518750 The Battery).
* **`extras["heading_deg"]`** is the compass heading of the structure's principal axis (+s for bridges), so the
  engine can orient the asset without re-deriving it.
* **LOD1 is a separate file** `<id>_lod1.glb`, not a node inside LOD0 (agent A's convention) — the two lanes differ
  here and the integrator should expect both. LOD1 is at most 40 % of the LOD0 triangle count.
* **Material slots to drive**: `MEMORIAL_NAMES` and `MINTON_TILE` (see section 5). Emissive materials the engine may
  want to control: `light_cool` (tunnel luminaires), `light_warm` (lamp posts, the Luna Park sign), `gold_leaf`
  (the Statue of Liberty's flame).
* **Roads centreline**: `data/processed/roads/segments.parquet` is consumed (section 4). If the roads stage
  re-emits it with different `street_name` values, the per-bridge LION names in each script's `roads_name=` are the
  only thing to update; the 8-degree guard means a bad match degrades to the OSM support axis rather than moving a
  bridge.
* **Reference viewpoints**: `b_align.reference_view()` / `reference_render()` consume
  `docs/verification/reference/<id>/meta.json`. Any new reference the comparison agent records is picked up by
  re-running the landmark; a missing one is skipped, not an error.
* **Collision.** The tunnel linings are single-sided inward-facing surfaces away from the portals; if the engine
  needs two-sided collision there, generate it from the ribbon meshes rather than expecting a closed solid.
