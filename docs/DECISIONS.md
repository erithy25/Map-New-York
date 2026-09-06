# Architecture Decision Records

Format: **Context → Decision → Consequences**. Numbered, never deleted; superseded ADRs are marked.

## ADR-001 Runtime engine is Unreal Engine 5.4; content is authored in Blender 4.5
Context: The brief mandates Blender for every asset and Unreal for assembly. The build environment cannot run the UE editor (no Epic download, no GPU).
Decision: Author the UE project as complete source (C++ modules, config, Python editor automation, content manifest). Keep every piece of logic that can be verified here in an engine-agnostic C++17 library (`core/`) compiled both standalone (tests) and into the UE module. Blender runs headless via `bpy`.
Consequences: UE-specific code (actors, components, materials, Niagara, MetaSounds) is verified by static review only in this environment; compile/cook/play verification is a documented workstation step. `core/` carries the testable behaviour (routing, traffic rules, signals, streaming, astronomy, tz, weather parsing).

## ADR-002 World CRS is a local Transverse Mercator with k=1
Context: UTM 18N has 0.028 % scale error at NYC (28 cm/km); State Plane is in feet with 1:10,000 distortion.
Decision: `+proj=tmerc +lat_0=40.7 +lon_0=-73.95 +k=1`. Max distortion 1.2 cm/km inside scope.
Consequences: One extra pyproj definition; every consumer reads it from `crs.json`; never hard-code.

## ADR-003 Building detail = real shell + instanced kit, not unique meshes
Context: 1.08 M buildings × detailed unique facade meshes exceed disk (> 50 GB) and cannot stream at 60 fps.
Decision: Generate a unique shell (real footprint, real roof) per building in Blender; generate a detailed facade kit once in Blender; compute per-building kit placements deterministically in the pipeline from real attributes (floors, windows, storefronts, fire escapes, rooftop equipment).
Consequences: storage measured on real output is **≈ 5.7 GB of shells and ≈ 1.7 GB of placements**. The shell figure comes from 76 built tiles holding 66,559 buildings at 5,266 bytes each, against the 1.2 KB this ADR assumed: the level-of-detail chain adds about 80 % and the per-vertex attributes are 62 % of the base mesh's bytes. Draco compression reaches the original figure at 4.7× but costs 65 to 90 seconds a tile here and breaks the glTF reader used in the tests, so it is documented as a workstation option rather than enabled. The placement figure is (42,068,609 records at 40 bytes, 38.8 per building). The original estimate of under 1 GB for placements was low because it did not account for window accessories, trim runs and rooftop equipment being individually placed rather than derived in the shader. Visual variety comes from parameters (materials, weathering seeds, kit variants), not from unique geometry. Landmarks are excluded from this and hand-scripted.

## ADR-004 Facade appearance is inferred from real attributes and flagged
Context: No lawful, feasible source of per-building street-level imagery for 1.08 M buildings in this environment.
Decision: Rule-based classifier (versioned, auditable) from year, class, floors, landmark/historic status, neighbourhood and OSM material tags. Every such building carries `FACADE_INFERRED`. OSM `building:material`/`building:colour` and LPC designation-report typologies override rules and set `MATERIAL_REAL`.
Consequences: The fidelity report states exactly how many facades are inferred (expected: the overwhelming majority) and where. This is the single largest fidelity gap versus the brief and is stated as such.

## ADR-005 Terrain from 3DEP 1/9″ + LiDAR ground points, not the 26.6 GB 1-ft DEM
Context: Disk allowance 30 GB; 1-ft DEM zip 26.6 GB (3.2 GB integer variant expands to > 20 GB).
Decision: 3DEP 1/9 arc-second (LiDAR-derived, ~3.4 m) mosaic, densified with 1.08 M building ground elevations and planimetric spot elevations, hydro-flattened, resampled to 2 m.
Consequences: Terrain vertical accuracy ≈ 0.15 m (stated), horizontal ≈ 2–3 m. Upgrade path documented: swap in 1-ft DEM on a workstation with the same pipeline stage.

## ADR-006 Roads from CSCL/LION, not OSM; OSM used for signals, turn restrictions, names of shops, rail structures
Context: CSCL carries real lane counts, parking lanes, widths, posted speeds, traffic direction and grade-separation codes; OSM NYC coverage of these is partial.
Decision: CSCL is the authority for geometry and attributes; OSM supplements where CSCL has no field.
Consequences: Road km in the fidelity report come from CSCL. Turn restrictions are OSM + topology + NYC default law (no right on red).

## ADR-007 Signals: union of DOT datasets and OSM, gaps inferred and flagged
Context: DOT does not publish a plain "all traffic signals" dataset on Socrata; it publishes LPI, Barnes Dance, retiming lists; OSM has `highway=traffic_signals` nodes.
Decision: Union with provenance per node; infer signals only where two streets with ≥ 2 travel lanes meet and no source says otherwise; flag `signal_source=4`.
Consequences: Signal count and inferred share reported.

## ADR-008 Tile size 1 km, four LOD tiers, hysteresis streaming
See ARCHITECTURE §3. Alternative 500 m tiles rejected (4× tile count, more scheduler overhead, no visual gain at 60 fps budgets).

## ADR-009 Player car is a 2019 Ford Fusion Hybrid
Context: Need a real car with known dimensions that is common on NYC streets and doubles as taxi/black-car livery.
Decision: Fusion Hybrid (real dimensions in `core/vehicle/VehicleSpec.h`). Additional fleet bodies for the AI: Toyota Camry (yellow cab), Toyota RAV4 hybrid (cab/FHV), Nissan NV200 (cab), Ford Explorer (NYPD), Chevrolet Suburban (black car), Nova Bus LFS and New Flyer XD40 (MTA), Seagrave engine/ladder (FDNY), Ford F-450 Type I ambulance, Isuzu NPR box truck, Mack LR (DSNY), Mercedes Sprinter and Ford Transit (delivery), Freightliner MT55 (UPS/FedEx), bicycles, e-bikes (Arrow), Vespa-class mopeds, pedicab, horse carriage.
Consequences: Bodies are procedural Blender builds with real published dimensions; no licensed manufacturer CAD is used; fidelity is "recognisable silhouette + correct proportions + correct livery", stated in the report.

## ADR-010 Character built from MakeHuman (MPFB2) assets, CC0
Context: Need a detailed rigged human without proprietary sources; Mixamo needs an Adobe login.
Decision: MPFB2 extension + MakeHuman CC0 system assets, headless; facial blendshapes from MPFB; clothing from MPFB CC0 library plus procedural tailoring; animations authored procedurally plus CMU mocap (free for all uses) where the archive is reachable.
Consequences: Photo-real skin/hair depends on UE shading (Substrate hair/skin) at runtime, which is authored but not previewed here.

## ADR-011 Live weather: NWS → Open-Meteo → METAR → stale
Context: Brief demands live NYC weather with graceful failure.
Decision: Ordered providers with per-provider circuit breakers, 60 s cadence, stale age surfaced in overlay, never synthetic.
Consequences: Tested with recorded fixtures in `core/tests/live`.

## ADR-012 Verification renders use Cycles CPU in Blender, not UE
Context: No UE here. Visual checks against photographs must still happen before delivery.
Decision: Cycles CPU renders of generated tiles at the seven mandated viewpoints and the five drive-through areas, with the same PBR materials the kit exports. Reference photographs from Wikimedia Commons with licence and author recorded.
Consequences: Lighting/GI differs from UE Lumen; geometry, materials, composition and massing are what is compared.

## ADR-013 The city 3-D model carries roof *massing*, not roof *pitch* — pitched roofs are inferred and flagged
Context: The NYC 3-D Building Model (`DA_WISE`, CityGML LOD2 from 2014 LiDAR) was adopted in ADR-003 as the source of real roof geometry. Measured over 395,891 parsed buildings across six delivery areas, only **28 buildings (0.007 %)** have any roof surface sloped more than 2°, while `n_roof_levels` averages 1.2–2.1 with maxima of 25–38. The dataset therefore represents every building as a stack of horizontal plates: setbacks, bulkheads, penthouses and mechanical levels are real and measured, but a gabled Queens house is modelled as a flat-topped prism.

Decision:
* Keep the dataset as the source of truth for roof **height, massing steps and setbacks**, and set `ROOF_REAL` for those buildings — that part is genuinely measured.
* Do **not** claim measured roof shape. `roof_type` from CityGML is `flat` almost everywhere because the source says flat, not because the classifier failed.
* For building classes that really have pitched roofs (PLUTO A0–A9 one-family, B1–B9 two-family, C0 walk-up, and detached S-class houses — concentrated in Queens, Staten Island and outer Brooklyn), derive the roof shape from building class, footprint aspect ratio and era, generate it in the shell mesh, and flag it `ROOF_INFERRED`. The measured `z_roof_max` is kept as the ridge height, so the building's overall height stays real.
* Report both numbers separately in the fidelity report: buildings with measured roof massing, and buildings whose roof *shape* is inferred.

Consequences: roof silhouettes in the outer boroughs are typologically correct rather than individually measured, and the report says so. The alternative — shipping half a million flat-topped boxes where real houses have gables — would be visually wrong and would misrepresent the data as complete. Closing this gap needs a source with real roof planes (an aerial photogrammetric mesh, or a re-derivation from the raw 2017 topobathymetric LiDAR point cloud).

### ADR-013 addendum — measurement and implementation (CityGML stage, 2026-09-06)
*Evidence: `docs/verification/citygml/REPORT.md`, `roof_evidence_da4_queens.json`, `roof_sloped_buildings.json`, `roof_inference_calibration.json`.*

Independent measurement on the **raw source rings**, before any unit or datum transform: every `bldg:RoofSurface` polygon in DA4 (Queens, 16,665 buildings, 21,956 roof faces) has unit normal exactly (0, 0, 1) and zero z-range in EPSG:2263 feet — max slope 0.000000°, no face sloped ≥ 1°. Re-sampled in Staten Island (DA17) and Manhattan (DA12): identical. Twenty named one-family houses on 87 Street, Howard Beach — gabled and hipped in reality — are stacks of one to four horizontal slabs. City-wide, the only buildings with *any* sloped roof face are the hand-modelled landmarks (Statue of Liberty, Brooklyn Museum, Barclays Center, Litchfield Villa, Williamsburgh Savings Bank Tower, Audubon Boathouse). This corroborates the 0.007 % figure in the ADR.

Implementation in `buildings/citygml_join.py` -> `buildings/roof_attrs.parquet` (contract §5.3):
* `citygml_match` carries `ROOF_REAL`: the measured massing solid exists (real roof outline, real height).
* `roof_shape_measured` is a **separate** boolean, true only where the source really carries sloped roof geometry — i.e. essentially nowhere. `n_roof_levels`, `roof_level_z` and `roof_level_area` are first-class columns: they are the genuinely measured signal (real setbacks, bulkheads, penthouses).
* `roof_type` precedence, stamped per row in `roof_type_source`: `citygml` (only the hand-modelled landmarks) -> `osm` (a real `roof:shape` tag, 4,038 BINs) -> `inferred` -> `default` flat. `roof_inferred` is true for the last two.
* Inference rule: PLUTO class in A0–A9 / B1–B9 / C0 / S0–S2 / S9 / R1 / R3, `bldg_frontage / lot_frontage < 0.80` (a side yard exists, so no party wall — this is what separates a gabled Queens house from a flat-roofed Brooklyn row house), minimum-rotated-rectangle short side ≤ 14 m, ≤ 3 floors, footprint ≤ 400 m². Measured against the 4,038 real OSM `roof:shape` tags matched to a footprint: precision 0.805, recall 0.456, accuracy 0.932 (Queens precision 1.00 on n=28, Brooklyn 0.79 on n=204) — reproduce with `citygml_validate.roof_inference_calibration`.
* Gable vs hip is **not** decidable from the available attributes (on the 347 buildings OSM tags `gabled` or `hipped`, the best footprint-aspect threshold scores 0.617 accuracy against a 0.637 majority-class baseline — worse than always saying gable), so every inferred pitched roof is emitted as `gable` with its ridge along the long axis. `roof_type_conf` records the confidence.
* Per the ADR, the measured `z_roof_max` is kept as the **ridge** height: `roof_ridge_dz_m = 0`, `roof_eave_dz_m = -rise`, nominal pitch 30° (7:12) with the rise clamped to [0.9, 3.0] m and the pitch recomputed when the clamp bites. Overall building height therefore stays exactly the published LiDAR height.


## ADR-014 Weather provider order stays fixed; freshness preference is available but off by default
Context: ADR-011 fixed the provider order NWS → Open-Meteo → METAR. Measurement during the live-services stage found that `api.weather.gov` lags roughly one hour behind `aviationweather.gov` for station KNYC: at 12:03 UTC on 2026-09-06 the NWS observation was the 10:51Z report while METAR already carried 11:51Z. A forecast-blend correction that carried the older observation forward made the sample *worse* (−1.06 °C against the independent METAR, versus −0.50 °C for the uncorrected stale value).

Decision: keep the fixed order of ADR-011 as the default. Implement and test an opt-in `WeatherService(prefer_freshest_age_s=N)` that selects the freshest successful provider once the leading provider's observation is older than N seconds, but ship it disabled. Every published record carries `stale_age_s` and an `interpolated` flag so a consumer can see exactly what it is getting.

Consequences: default behaviour stays predictable and matches the documented ordering; the observed lag is visible in the data rather than hidden by a silent re-ordering; enabling freshness preference is a one-line change once there is more than a single sample to justify it. Tuning the forecast blend on n = 1 was explicitly refused.

## ADR-015 Heightmaps stay on the 2 m / 501-sample grid; the Unreal importer resamples to Landscape's legal size
Context: Unreal Landscape only accepts component sizes of 7, 15, 31, 63, 127 or 255 quads, so a 1 km tile cannot be built from 500 quads. The pipeline emits 501 inclusive samples at exactly 2.0 m, which is the natural grid for the source DEM and keeps tile edges shared exactly between neighbours.

Decision: keep the pipeline contract at 501 samples / 2.0 m. The Unreal terrain importer bilinearly resamples each tile to 505 samples (8 components of 63 quads at 198.412698 cm), which is still exactly 1,000 m wide, with the tile borders taken from the source unchanged.

Consequences: interpolation error measured at 0.0020 m on a 16 m sinusoid and 1.1 × 10⁻¹³ m on affine ground, against a terrain product whose own vertical accuracy is about 0.15 m — two orders of magnitude below the noise floor, and exactly zero at tile borders, so tiles still meet watertight. The `component_size_quads: 125` field in `unreal_manifest.json` is not a legal Unreal value and is ignored by the importer; it is corrected to the pair the importer actually uses. The alternative, exporting 505-sample heightmaps, was rejected because it would put the whole pipeline on a non-round 1.98 m grid to suit one consumer.

## ADR-016 `taxi_share` means all for-hire traffic, and the shares are fractions of the road-user stream
Context: DATA_CONTRACTS §10 names the share columns but does not say what counts as a taxi in a city where medallion cabs are a minority of for-hire vehicles, nor whether the shares are fractions of motor traffic or of all road users including cyclists.

Decision: `taxi_share` covers **all street-hail and app-hail for-hire traffic** — yellow medallion, green boro and high-volume for-hire together. The four share columns are fractions of the **road-user stream**, motor vehicles plus bicycles, while `veh_per_km_lane` counts motor vehicles only. The split inside the for-hire group lives in `fleet_mix.json`, measured from trip records rather than assumed: in the central business district at midday it is 24.0 % yellow, 0.07 % green and 76.0 % high-volume for-hire, and on Staten Island 0.48 / 0.03 / 99.5 %.

Consequences: a spawner reads the group share from the density cell and then the class within the group from the fleet mix, so the two files are consistent by construction. Anyone wanting medallions only can read `within_group.taxi`, which already carries the numbers, without a rebuild. Reporting a "taxi share" that excluded app-hail would understate for-hire traffic in New York by roughly a factor of three and would be misleading.

## ADR-017 City terrain comes from 3DEP 1 m LiDAR, not the 1/9 arc-second product (supersedes part of ADR-005)
Context: ADR-005 chose the USGS 3DEP 1/9 arc-second product (about 3.4 m) because the city's own 1-foot DEM is a 26.6 GB download against a ~30 GB disk allowance. On ingest the terrain stage found that **the 1/9 arc-second dataset has no data over the five boroughs at all**: all eighteen products intersecting the scope carry data only in New Jersey, Nassau, Fairfield and a sliver of Westchester.

Decision: use the 3DEP **1 m** LiDAR product for the city, falling back to 1/3 arc-second only where neither the 1 m nor the planimetric sources reach. The 1 m product is finer than the original plan and comes from the same 2013–14 acquisition as the CityGML building model, so terrain and buildings share a vintage.

Consequences: the terrain is better than ADR-005 promised, not worse — 99.97 % of land samples in every borough come from the 1 m product, and the accuracy statement in the fidelity report is raised accordingly. ADR-005's disk reasoning stands; only its choice of product is superseded. The upgrade path to the city's 1-foot DEM is unchanged.

## ADR-018 A land sample below −2 m that no survey point corroborates is a source artefact and is repaired
Context: A city-wide scan found 16,243 samples below −2 m NAVD88 across 42 tiles, with a minimum of −26.97 m. Four causes, only one of them real: LiDAR returning the water surface inside pier slips and dry docks, rail tunnel mouths, construction pits from the 2013–14 flight that have since been built over (the West Side Yard before the Hudson Yards platform, the World Trade Center site), and genuine below-datum ground such as the Battery Underpass.

Decision: a sub-datum sample is **kept** when a survey ground point within 15 m sits below the same floor — a sharp test, since only 23 of 376,133 spot elevations lie below −2 m. Otherwise it is repaired: to the nearest water surface within 30 m of open water, else by inverse-distance interpolation from the pit rim, else from the eight nearest survey points out to 240 m. Every branch is counted per tile in `terrain.json` under `sub_datum`, together with the value before the edit, so no source value is lost and every repair is auditable.

Consequences: the Battery Underpass and the other genuine cuts survive; a driver does not fall into a 27 m hole where a tunnel portal was scanned in 2013. Because every input to a repair lies inside the 32 m tile margin or comes from the global point index, the edit is seam-identical — the 5,724 adjacent tile pairs still match to 2.8 × 10⁻¹⁴ m.

## ADR-019 OpenStreetMap water is clipped against the elevation surface; surveyed polygons never are
Context: The coastline-derived sea face from OpenStreetMap claimed a 1,003 km² "bay" covering the New Jersey Palisades and the Watchung ridges, flattening ground standing between 47 m and 167 m to sea level in three tiles.

Decision: OpenStreetMap water is cut against the New York City land boundary, and every remaining body is clipped back to where the elevation surface stands no higher than that body's own level plus 1 m. Planimetric hydrography is surveyed and is never clipped; it remains the authority inside the city.

Consequences: 1,139.7 km² of falsely claimed water removed. The Palisades, the Watchungs, Hoboken, Jersey City, Midtown, Todt Hill and Kennedy Airport read as land; the mid-Hudson, Upper Bay, the Narrows, Newark Bay, Long Island Sound, the Atlantic and Jamaica Bay read as water; the Central Park reservoir reads as water at 34.52 m. Using OpenStreetMap water unclipped would have put the New Jersey skyline under the sea.

## ADR-020 Reference photographs stay tracked in the repository
Context: The reference set is 519 photographs, 410 MB, under `docs/verification/reference/`. Every file carries its source URL and SHA-256 in the subject's `meta.json`, so the set is exactly re-fetchable and could be git-ignored like the texture downloads, keeping only the 2.8 MB of metadata.

Decision: keep the photographs tracked.

Consequences: the repository carries about 410 MB it could avoid. Against that, these images are not an input the build regenerates — they are the *evidence* the finished work is judged against, and condition 3 of the definition of done is a side-by-side comparison. Wikimedia has already begun refusing original-resolution downloads to unauthenticated clients, so a set that is re-fetchable today may not be next year; a comparison that cannot be reproduced later is not much of a comparison. Textures are different: they are re-derivable inputs with a stable licence and no evidentiary role, which is why ADR-scoped ignoring applies to them and not here.


## ADR-021 Agent destinations and spawn points must be drawn from the streamed region
Context: Measured against the real 122,235-segment graph, a simulation step costs **777 ms**, of which **96 % is path finding** — about 399 ms for eight vehicle route queries and 310 ms for 96 pedestrian paths. The router is not slow: the same eight queries cost roughly 0.1 ms each on a synthetic grid. The cost comes from sampling destinations uniformly over all 851,725 lanes, so an agent in Brooklyn is routed to Staten Island and the search settles a large fraction of the city. Separately, the spawner samples a lane from a city-wide distribution and *then* rejects it if it falls outside the player's 900 m ring, accepting about one lane in a thousand: after a prefill of 6,000 vehicles the ring held **86** against a density-table target of **304,878**, so the city cannot be populated at all.

Decision: both the vehicle spawner and the pedestrian goal chooser must draw from the streamed region rather than from the whole city, using a spatial index over the spawn distribution restricted to the ring. Genuine long trips need a hierarchy in the router and are a separate piece of work.

Consequences: about 709 ms of the 777 ms step disappears, and the player's surroundings can actually be populated. This **changes behaviour**: agents no longer take cross-city trips, and the sequence and order of lanes drawn changes, which moves the spawn counts the traffic suite asserts (910 spawns, 909 despawns) and the trajectory hashes locked in `tests/test_performance.py`. That is why it is an ADR and not a patch — the performance stage deliberately left it undone rather than silently altering behaviour under the banner of optimisation. Whoever implements it must re-baseline those tests in the same commit and say so.
