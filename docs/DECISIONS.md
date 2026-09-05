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
