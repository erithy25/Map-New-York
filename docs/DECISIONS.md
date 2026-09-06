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
Consequences: Storage ≈ 1.3 GB shells + < 1 GB placements. Visual variety comes from parameters (materials, weathering seeds, kit variants), not from unique geometry. Landmarks are excluded from this and hand-scripted.

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

## ADR-013 CityGML LOD2 gives real massing, not roof shape; pitched roofs are inferred and flagged
*Proposed by the CityGML stage, 2026-09-06. Evidence: `docs/verification/citygml/REPORT.md`, `roof_evidence_da4_queens.json`, `roof_sloped_buildings.json`.*

Context: DATA_CONTRACTS §5 expects `roof_type` (flat/gable/hip/mansard/shed/sawtooth/complex/dome/barrel) and the `ROOF_REAL` fidelity bit to come from the NYC 3-D Building Model (DoITT, 2014 LiDAR, `DA_WISE_GML.zip`, 13.8 GB). Measured on the raw source rings, **before any unit or datum transform**, every `bldg:RoofSurface` polygon in the delivery is exactly horizontal: unit normal (0, 0, 1), zero z-range in EPSG:2263 feet. DA4 (Queens, 16,665 buildings, 21,956 roof faces): max slope 0.000000°, no face sloped ≥ 1°. Sampled again in Staten Island (DA17) and Manhattan (DA12): identical. Across all delivery areas exactly 7 buildings out of 1,065,000 carry sloped geometry, and they are the hand-modelled landmarks (Statue of Liberty, Brooklyn Museum, Barclays Center, Litchfield Villa, Williamsburgh Savings Bank Tower, Audubon Boathouse). Twenty named one-family houses on 87 Street, Howard Beach — gabled and hipped in reality — are modelled as one to four stacked horizontal slabs. The model is therefore multi-level *flat massing* with semantic Ground/Wall/Roof tagging, not a roof-shape model.

Decision:
1. `ROOF_REAL` means *the real LOD2 massing solid exists for this BIN* — real roof outline, real stepped roof levels, real roof height — and is set from `citygml_match` in `buildings/roof_attrs.parquet`. The LOD2 mesh remains the building shell source; nothing about it is inferred.
2. `roof_type` is **not** taken from CityGML for ordinary buildings, because CityGML carries no evidence about it. It is resolved by precedence, and the precedence is recorded per row in `roof_type_source`: `citygml` (the 7 landmarks) → `osm` (a real `roof:shape` tag, 4,038 BINs) → `inferred` (PLUTO class + footprint/lot shape) → `default` flat. `roof_inferred` is true for the last two.
3. The inference fires only for detached one/two-family stock: PLUTO class in A0–A9/B1–B3/B9/R1/R3, `bldg_frontage / lot_frontage < 0.80` (a side yard exists, so no party wall), minimum-rotated-rectangle short side ≤ 14 m, ≤ 3 floors, footprint ≤ 400 m². Measured against the 4,038 OSM-`roof:shape`-tagged NYC buildings that match a footprint: precision 0.830, recall 0.305, accuracy 0.922 — deliberately conservative (reproduce with `citygml_validate.roof_inference_calibration`).
4. Gable vs hip is **not** decidable from the available attributes (on the 347 buildings OSM tags `gabled` or `hipped`, the best footprint-aspect threshold scores 0.617 accuracy against a 0.637 majority-class baseline — worse than always saying gable), so every inferred pitched roof is emitted as `gable` with its ridge along the long axis, and that limitation is stated in the data (`roof_type_conf`) and in the report.
5. The inferred roof keeps the measured mean roof height: eave at `z_roof_max + roof_eave_dz_m`, ridge at `z_roof_max + roof_ridge_dz_m`, symmetric about the LiDAR plane, nominal pitch 30° with the rise clamped to [0.9, 3.0] m.

Consequences: 44.9 % of NYC buildings get a pitched roof (Manhattan 0.5 %, Bronx 33 %, Brooklyn 25 %, Queens 58 %, Staten Island 72 % — the expected borough profile), every one of them flagged `roof_inferred`. Roughly 17 % of them are wrong (mostly flat roofs turned pitched) and about 70 % of genuinely pitched roofs are missed and stay flat. A later stage with a better source (a roof-shape classifier on the 2014 LiDAR point cloud, or bulk OSM `roof:shape` mapping) can replace source 2 without touching the contract. `roof_type == complex` still means "use the CityGML mesh" as §5 says; it now occurs only for the hand-modelled landmarks.

## ADR-013 The city 3-D model carries roof *massing*, not roof *pitch* — pitched roofs are inferred and flagged
Context: The NYC 3-D Building Model (`DA_WISE`, CityGML LOD2 from 2014 LiDAR) was adopted in ADR-003 as the source of real roof geometry. Measured over 395,891 parsed buildings across six delivery areas, only **28 buildings (0.007 %)** have any roof surface sloped more than 2°, while `n_roof_levels` averages 1.2–2.1 with maxima of 25–38. The dataset therefore represents every building as a stack of horizontal plates: setbacks, bulkheads, penthouses and mechanical levels are real and measured, but a gabled Queens house is modelled as a flat-topped prism.

Decision:
* Keep the dataset as the source of truth for roof **height, massing steps and setbacks**, and set `ROOF_REAL` for those buildings — that part is genuinely measured.
* Do **not** claim measured roof shape. `roof_type` from CityGML is `flat` almost everywhere because the source says flat, not because the classifier failed.
* For building classes that really have pitched roofs (PLUTO A0–A9 one-family, B1–B9 two-family, C0 walk-up, and detached S-class houses — concentrated in Queens, Staten Island and outer Brooklyn), derive the roof shape from building class, footprint aspect ratio and era, generate it in the shell mesh, and flag it `ROOF_INFERRED`. The measured `z_roof_max` is kept as the ridge height, so the building's overall height stays real.
* Report both numbers separately in the fidelity report: buildings with measured roof massing, and buildings whose roof *shape* is inferred.

Consequences: roof silhouettes in the outer boroughs are typologically correct rather than individually measured, and the report says so. The alternative — shipping half a million flat-topped boxes where real houses have gables — would be visually wrong and would misrepresent the data as complete. Closing this gap needs a source with real roof planes (an aerial photogrammetric mesh, or a re-derivation from the raw 2017 topobathymetric LiDAR point cloud).
