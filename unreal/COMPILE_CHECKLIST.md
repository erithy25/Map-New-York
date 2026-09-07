# UE 5.4 compile checklist — world, streaming, terrain, water, sky, weather, import

**There is no Unreal Engine in the build container** (ARCHITECTURE §0): no UBT, no UHT, no headers to compile
against. Every file below was therefore written against the UE 5.4 API and then *self-reviewed by reading*: include
order, module dependencies, `.generated.h` last, `TObjectPtr`/`TWeakObjectPtr` for UObject references, LWC doubles on
world positions, const-correctness, UHT restrictions (no static arrays exposed to Blueprint, no `UPROPERTY` inside
non-reflected structs), and lifetime of everything handed to a worker thread.

“Verified” in this file means *checked by reading the code and the contracts it must satisfy*, never *compiled*.
The first workstation build is the first compile. §7 lists the API calls whose exact signature could not be checked
against installed engine headers here — those are where a first-build error, if any, will be.

Three executable checkers back this file up and are re-runnable at any time:
`check_sources.py` (523 static assertions over the 36 owned files), `check_math.py` (38 numeric assertions over
every formula below) and `check_terrain_data.py` (the importer's assumptions against the 2,337 real heightmaps),
all under `docs/verification/unreal_world/`. All three pass.

Owner: Unreal agent 1. Files under `Private/{Vehicle,Character,Traffic,Peds,UI,Audio,Player}` and their `Public/`
mirrors belong to Unreal agent 2 and are not listed here. `NYCSimRuntime.Build.cs` is shared; this stage added no
line to it (every module it needs was already listed).

---

## 1. Module dependencies actually used by these files

| Header included | Module | In `NYCSimRuntime.Build.cs`? |
|---|---|---|
| `Subsystems/WorldSubsystem.h`, `Engine/World.h`, `Engine/Canvas.h`, `Engine/Engine.h`, `Engine/Font.h` | Engine | yes (Public) |
| `Engine/LevelStreamingDynamic.h`, `Engine/Level.h` | Engine | yes |
| `Debug/DebugDrawService.h` | Engine | yes |
| `Kismet/KismetMaterialLibrary.h`, `Materials/MaterialParameterCollection.h` | Engine | yes |
| `Components/{DirectionalLight,ExponentialHeightFog,SkyAtmosphere,SkyLight,VolumetricCloud,StaticMesh,HierarchicalInstancedStaticMesh}Component.h` | Engine | yes |
| `Engine/{DirectionalLight,ExponentialHeightFog,SkyLight,StaticMeshActor,StaticMesh,Texture2D}.h`, `EngineUtils.h` | Engine | yes |
| `ImageUtils.h` (`FImageUtils::LoadImage`) | Engine | yes |
| `ImageCore.h` (`FImage`, `ERawImageFormat`) | ImageCore | yes (Private) |
| `Landscape.h`, `LandscapeProxy.h`, `LandscapeInfo.h` | Landscape | yes (Public) |
| `Components/DynamicMeshComponent.h` | GeometryFramework | yes |
| `DynamicMesh/DynamicMesh3.h`, `Generators/RectangleMeshGenerator.h` | GeometryCore | yes |
| `HttpModule.h`, `Interfaces/IHttpRequest.h`, `Interfaces/IHttpResponse.h` | HTTP | yes |
| `NiagaraComponent.h`, `NiagaraSystem.h` | Niagara | yes |
| `Dom/JsonObject.h`, `Serialization/Json*.h` | Json | yes |
| `Tasks/Task.h`, `HAL/PlatformMemory.h`, `Misc/PackageName.h`, `HAL/IConsoleManager.h` | Core / CoreUObject | yes |
| `Commandlets/Commandlet.h` | CoreUObject | editor module, yes |
| `IPythonScriptPlugin.h` | PythonScriptPlugin | `NYCSimEditor.Build.cs`, yes |

`Landscape.h` / `LandscapeInfo.h` are included **inside `#if WITH_EDITOR`** because `ALandscape::Import` and
`ULandscapeInfo::UpdateLayerInfoMap` are editor-only; the rest of `NYCTerrainImport.cpp` compiles in every
configuration.

---

## 2. Files added by this stage

### `Public/Streaming/NYCTileStreamingSubsystem.h` · `Private/Streaming/NYCTileStreamingSubsystem.cpp` (251 + 974 lines)
* `UTickableWorldSubsystem`: overrides `ShouldCreateSubsystem`, `Initialize`, `Deinitialize`, `Tick`, `IsTickable`,
  `GetStatId` (`RETURN_QUICK_DECLARE_CYCLE_STAT`, `STATGROUP_Tickables` comes from `Tickable.h` via
  `WorldSubsystem.h`). `IsAllowedToTick()` is `final` in the base and is not overridden.
* `FNYCStreamingStats::TilesPerTier` is a **`TArray<int32>` with five entries, not a C array**: UHT rejects static
  arrays with `BlueprintReadOnly`. Verified: every index used is `static_cast<int32>(ENYCTier::…)` ∈ [0, 4].
* GC: the `ULevelStreamingDynamic` objects are held by `UPROPERTY(Transient) TArray<TObjectPtr<…>>
  ManagedStreamingLevels` (strong) and referenced from the non-reflected `Levels` map as `TWeakObjectPtr`
  (`FManagedLevel`). `UWorld::AddStreamingLevel` also keeps them alive, but the array is the guarantee.
* Threading: `UE::Tasks::Launch` runs `FNYCTileSchedulerAdapter::Update`; the game thread only touches
  `WorkerTransitions`/`WorkerStats` after `SchedulerTask.IsCompleted()`, and `Deinitialize` and `FlushStreaming`
  `Wait()` before touching the adapter. `Camera` is captured by value, `this` and the adapter pointer outlive the
  task because of that wait.
* `TArray::RemoveAt(Index, 1, false)` is used, **not** the 5.5 `EAllowShrinking` overload.
* Console objects are file-scope `FAutoConsoleCommandWithWorldArgsAndOutputDevice` statics that resolve the
  subsystem from the `UWorld*` the console passes, so PIE and the editor world cannot cross-talk and nothing is
  registered twice.
* LWC: camera positions are `FVector` (double); tile arithmetic is in metres as `double`.

### `Public/World/NYCTerrainImport.h` · `Private/World/NYCTerrainImport.cpp` (145 + 315 lines)
* **Landscape geometry decision, verified against UE's constraint** that `SubsectionSizeQuads ∈ {7,15,31,63,127,255}`:
  500 quads (501 samples) is divisible by none of them, so the 501-sample grid is resampled to 505 samples =
  504 quads = 8 × 8 components of 63 quads, and the quad size becomes 100000/504 = 198.412698 cm so the landscape
  still spans exactly 1000 m. Edge samples map exactly (j=0 → s=0, j=504 → s=500), so adjacent tiles stay watertight.
  *The `terrain_heightmap` block of `unreal_manifest.json` says `component_size_quads: 125`, which UE cannot use;
  the importer ignores it. Flagged to the pipeline owner in the report.*
* Height mapping is exact and needs no requantisation: `DrawScale.Z = z_scale_m × 12800`,
  `ActorZ = (z_min_m + 32768 × z_scale_m) × 100 cm`, heights passed through as the PNG's 16-bit values.
  Checked algebraically: world Z = ActorZ + (H − 32768) × DrawScale.Z/128 = (z_min_m + H × z_scale_m) × 100.
* Landscape actor sits on the tile's **north-west** corner (`UE.Y = −north`), which is where landscape local (0,0) is.
* `FMath::RoundToInt32` (not `RoundToInt`, whose double overload returns `int64` and would break `FMath::Clamp`
  template deduction).
* PNG decode uses `FImageUtils::LoadImage` + `FImage::AsG16()`; a non-G16 file is converted with `ChangeFormat` and
  the conversion is logged rather than silently accepted.
* `UFUNCTION`s deliberately carry **no** `WorldContext` meta so the `UWorld*` stays an explicit Python argument.

### `Public/World/NYCWaterActor.h` · `Private/World/NYCWaterActor.cpp` (178 + 662 lines)
* Near ring: one `UDynamicMeshComponent` per water tile inside `WaterNearRadiusTiles`, pooled and reused, each with
  its own `UMaterialInstanceDynamic` carrying that tile's shoreline mask. Far ring: four strips whose sizes are
  constant, so crossing a tile boundary only moves them.
* Masks are read from `Content/NYCSim/Runtime/water_masks/{tile}.png` (staged by the commandlet), kept as an 8-bit
  CPU array for `SampleWaterAtUE` **and** uploaded to a transient `PF_G8` `UTexture2D` for the material. One decode
  per tick at most.
* Transient textures are anchored by `UPROPERTY(Transient) TArray<TObjectPtr<UTexture2D>> MaskTextures` (not
  `AddToRoot`, which would leak them past the actor).
* Mask sampling matches the raster the pipeline writes: row 0 = north, 1 texel = 2 m, inclusive edges.
* The actor never moves; every patch is positioned in world space, so the tide changes only the components' Z.
* `bReplicates` is **not** assigned (private in UE 5); the default is already false.

### `Public/World/NYCInstancedMeshActor.h` · `Private/World/NYCInstancedMeshActor.cpp` (52 + 72 lines)
* Exists because a component created from Python on a bare `AActor` does not serialise into a level. The HISM is a
  `CreateDefaultSubobject` root, so `build_levels.py` can place 14 000 kit instances per tile in one call and have
  them saved.
* `AddInstances(Transforms, /*bShouldReturnIndices*/ true, /*bWorldSpace*/ true)` — the 4th parameter
  (`bUpdateNavigation`) is left at its default.

### `Public/CoreAdapter/NYCAstro.h` · `Private/CoreAdapter/NYCAstro.cpp` (113 + 190 lines)
* Wraps `nycsim::nytime` (America/New_York, Julian day, ΔT) and `nycsim::astro` (SPA sun, Meeus moon). Read against
  the **real** core headers (`core/include/nycsim/time/NyTime.h`, `astro/Spa.h`, `astro/Moon.h`) as they stand:
  `simTime()` → `Result<SimTime>`, `solarPositionUnix()`, `moonPositionUnix()`, `sunEventsLocal()`,
  `limitDegrees()`, `moonPhaseName()`, `kRiseSetH0Deg`, `kCivilTwilightH0Deg`,
  `kManhattanStreetSunsetAzimuthDeg`, `unixFromCivilUtc()`, `civilFromUnix()`.
* `Result<T>` is consumed through `explicit operator bool`, `.value()`, `.error().message/.code/.detail` — matching
  `core/include/nycsim/util/Result.h` and `Error.h`.
* Azimuth/elevation → UE direction goes through `NYCGeo::DirectionToUE`, so the handedness flip lives in one place.

### `Public/Sky/NYCSkyTimeSubsystem.h` · `Private/Sky/NYCSkyTimeSubsystem.cpp` (211 + 729 lines)
* Finds the level's existing sky actors first (`TActorIterator`) and only spawns what is missing, in
  `OnWorldBeginPlay` (**not** `Initialize`: world subsystems initialise before the world can spawn actors).
* Sun light rotation is `FRotationMatrix::MakeFromX(-SunDirectionUE).Rotator()` — the light's +X is the direction
  light travels.
* `bAtmosphereSunLight` + `AtmosphereSunLightIndex` 0/1 (UE 5 names; the UE 4 `bUsedAsAtmosphereSunLight` is gone).
* Mobility is set on the *component* (`GetLightComponent()->SetMobility`), because `AActor` has no `SetMobility`.
* Fog density ← visibility uses Koschmieder σ = 3.912/V with one calibration constant tying UE's density 0.02 to the
  WMO “clear day” 10 km. Stated in the code, not hidden.
* Star sphere: engine sphere mesh at 200 000 × scale (100 km radius), oriented by
  `FQuat::FindBetweenNormals(Up, PoleDirection)` then spun by the local apparent sidereal time the SPA returns.
  Skipped with one log line when either the mesh or `M_NYC_StarMap` is missing.
* `nycsim.PrintSun` prints clock, ΔT, JD, sun az/el, sidereal time, Manhattanhenge delta, moon phase and
  illumination, rise/transit/set, civil twilight, street-light state and which actors were found.

### `Public/CoreAdapter/NYCWeather.h` · `Private/CoreAdapter/NYCWeather.cpp` (297 + 375 lines)
* Wraps `nycsim::weather::{WeatherService, WeatherState, WorldEffects, metar::*, parseNwsObservation,
  NwsForecastBlend, parseOpenMeteo, toWeatherJson, fromWeatherJson}` as read from the real core headers.
* The core's `Provider::fetch` is synchronous, Unreal's HTTP is not: each provider callback decodes the **cached**
  document the subsystem stored, and returns `ErrorCode::IoError`/`StateError` when there is none or it is older
  than 300 s — which is exactly the failure the core's circuit breaker is designed for. No behaviour is duplicated.
* `nycsim::json::parse` (core) is used for the provider documents, so the decoders see the value type they expect;
  UE's own JSON reader is used only for the ESB/tides snapshots, which have no core parser.
* `TUniquePtr` members of incomplete core types with an out-of-line `~FNYCWeatherService()` in the .cpp.
* NaN discipline: `WeatherState::has()` decides every `bHas*` flag; a missing value never becomes 0.

### `Public/Weather/NYCWeatherSubsystem.h` · `Private/Weather/NYCWeatherSubsystem.cpp` (190 + 786 lines)
* `FHttpModule` fetchers on the 60 s cadence for NWS observation, NWS gridpoint, Open-Meteo and one METAR per
  station; `BindUObject(this, &…::OnHttpComplete, Provider, Station)` payload binding matches the 5-parameter
  handler. A `User-Agent` is always set (api.weather.gov requires one).
* The poll runs when the round's last response lands, so the world is never a cadence behind.
* Applies the core mapping to `MPC_Weather` (17 scalars + 5 vectors), to the four Niagara systems, to the sky
  (`ApplyAtmosphere`) and to the water actor (`SetTide`).
* ESB crown from `Live/esb_lights.json` (`rgb` is 8-bit sRGB → `FLinearColor(FColor)` linearises it).
* Overlay on `UDebugDrawService` (`nycsim.Overlay 1|2`) showing provider, station, observation time, age, staleness,
  every world-effect drive, ESB, tide and — at level 2 — each provider's circuit-breaker state, document age, HTTP
  status and the raw METAR.

### `Public/World/NYCWorldSubsystem.h` · `Private/World/NYCWorldSubsystem.cpp` (additive edit)
* Added `OnWorldBeginPlay` → `EnsureWaterActor` (reuses a level-placed `ANYCWaterActor`, else spawns one when
  `bSpawnWaterActor`), and `GetWaterActor()`. Nothing existing was changed.

### `Public/World/NYCSimWorldSettings.h` (additive edit) and `Config/DefaultEngine.ini`
* Added the Water, Sky-observer and Weather-endpoint blocks. Every new `UPROPERTY(Config)` has a matching line in
  `[/Script/NYCSimRuntime.NYCSimWorldSettings]` so a fresh checkout has the same defaults.

### `Source/NYCSimEditor/{Public,Private}/NYCImportCommandlet.{h,cpp}` (57 + 380 lines)
* `UCommandlet` with `IsEditor = true`; parses `-manifest -stages -tiles -maxtiles -content -nopython
  -continueonerror -dryrun` through `UCommandlet::ParseCommandLine`.
* Stages: validate (schema, unknown settings ids, missing sources, manifest warnings) → stage (raw/json copies plus
  the per-tile water masks) → assets (`import_assets.py`) → levels (`build_levels.py`) → verify (staged `crs.json`
  proj4 against the core's, `tiles.nycb` parse, per-tile level packages present).
* Python is run through `IPythonScriptPlugin::ExecPythonCommandEx` with `ExecuteFile` + `Unattended`, and every
  captured log line is re-emitted through `LogNYCSimEditor`.

### `Content/Python/{import_world,import_assets,build_levels}.py` (163 + 686 + 454 lines)
* Syntax-checked here with `python3 -m py_compile` (the only executable check possible without the editor).
* `import_assets.py` creates `MPC_Weather` and the five base materials with `unreal.MaterialEditingLibrary`, each
  node creation wrapped so one unsupported node reports itself instead of aborting the import, then imports every
  manifest entry in `import_order` and applies the manifest's per-kind settings (nanite, collision, sRGB,
  compression, mip generation, address mode).
* `build_levels.py` creates `/Game/NYCSim/Maps/NYC`, `{tile}_L0` / `{tile}_L1` and the skyline levels, calls
  `unreal.NYCTerrainImporter.import_tile_landscape` for the landscape and `unreal.NYCInstancedMeshActor` for props
  and kit. Tile names are converted to the content-safe form (`t_-3_7` → `t_m3_7`) exactly as
  `NYCGeo::TileAssetName` and the pipeline's `safe_asset_name` do.
* `import_world.py` stages, then calls the other two, then writes `Saved/NYCSim/import_report.json`.

---

## 3. Cross-checks against the contracts

| Contract | Where it is enforced |
|---|---|
| ARCHITECTURE §2 `UE.X = east·100, UE.Y = −north·100, UE.Z = up·100` | only in `core/geo/UECoords.h` via `NYCGeo`; every file here calls `NYCGeo::` |
| §3 tile grid, tiers, hysteresis, budget, 1.5 s lookahead | `FNYCTileSchedulerAdapter` → `nycsim::tiling::TileScheduler`; the subsystem never re-implements a radius test |
| §3 “no building < 300 m is ever unloaded” | core `protectRadius_m`, untouched here |
| DATA_CONTRACTS §3 terrain PNG/JSON | `UNYCTerrainImporter::LoadTerrainMeta` rejects `samples ≠ 501` and non-finite z |
| §4/§14.1 water | `ANYCWaterActor::LoadWaterJson` reads `water_fraction`, `dominant_kind`, `tidal`, `shoreline_m`, `structures`, `flow` |
| §12 `weather.json` | the core owns the record; the adapter only converts NaN → `bHas*` |
| §12 `tides.json` angle convention (`current_dir_deg` mathematical, flow *toward*) | `ANYCWaterActor::SetTide` comment and `NYCGeo::DirectionToUE` |
| §12 `esb_lights.json` | `UNYCWeatherSubsystem::ReadEsbLights` (`colors`, `rgb`, `reason`, `fallback`) |
| §14 manifest | commandlet validate/stage; `import_assets.py` `import_order` |
| §15 NYCB | unchanged `FNYCNycbFile`/`FNYCTilesTable` |
| ADR-008 tiers/hysteresis, ADR-011 provider chain | both delegated to `core`, not re-implemented |

---

## 4. UHT rules checked file by file

* `.generated.h` is the **last** include in every reflected header: `NYCTileStreamingSubsystem.h`,
  `NYCTerrainImport.h`, `NYCWaterActor.h`, `NYCInstancedMeshActor.h`, `NYCWeather.h`, `NYCSkyTimeSubsystem.h`,
  `NYCWeatherSubsystem.h`, `NYCImportCommandlet.h`.
* No `UPROPERTY` inside a non-reflected struct; no static array exposed to Blueprint; every `UENUM(BlueprintType)`
  has an explicit `: uint8`.
* Every `UFUNCTION` parameter type is reflectable (`FString`, `FIntPoint`, `FVector`, USTRUCTs, UObject pointers,
  `TArray` of those). `ENYCTier` is a plain `enum class` and is deliberately **not** exposed — the Blueprint-facing
  accessor is `GetTileTierIndex()`.
* Delegates that carry non-reflected types (`FNYCOnTileTierChanged`, `FNYCOnStreetLightingChanged`,
  `FNYCOnSkyUpdated`, `FNYCOnWeatherUpdated`, `FNYCOnWorldEffectsUpdated`) are native `DECLARE_MULTICAST_DELEGATE_*`,
  not dynamic.
* Forward declarations (`class ULevelStreamingDynamic;` …) instead of includes wherever only a pointer is needed.

## 5. Thread-safety and lifetime

* One scheduler step in flight at a time; the adapter is never touched concurrently.
* HTTP completion delegates run on the game thread (UE guarantee), so `FNYCWeatherService` needs no lock; this is
  stated in its header.
* `UDebugDrawService` handles are unregistered in `Deinitialize`.
* Every spawned actor is `RF_Transient` and dies with the world; nothing is added to the root set.

## 6. Numerical review (done by hand, no compiler)

* Landscape affine mapping — algebra shown in §2, exact.
* 501 → 505 resample: `Ratio = 500/504`; `j=0 → s=0`, `j=504 → s=500`; the interior weight is in [0,1) and `I0` is
  clamped to `SrcMax−1`, so the row/column pair is always valid.
* Water mask lookup: `Fy = (1 − (y−y0)/1000) × (N−1)` reproduces `manifest.py`'s `(N−1) − (y−y0)·px_per_m`.
* Fog: σ = 3.912/V; scale 51.1 from 0.02 = scale·3.912/10000. 200 m visibility → 1.0, clamped to [0.002, 3].
* Sun/moon intensity: sun is set to the extraterrestrial illuminance (120 000 lx) and the `SkyAtmosphere`
  transmittance does the attenuation; the moon is 0.25 lx × illuminated fraction (the measured full-moon value).

## 7. Where a first-build error is most likely (API signatures that could not be checked here)

1. `FRectangleMeshGenerator` member names (`Origin`, `Normal`, `Width`, `Height`, `WidthVertexCount`,
   `HeightVertexCount`) — `NYCWaterActor.cpp::SetPatchGeometry`, 8 lines. If they differ, only that function changes.
2. `UDynamicMeshComponent::SetMesh(FDynamicMesh3&&)` + `NotifyMeshUpdated()` — same function.
3. `UVolumetricCloudComponent::Material` (read directly, not through a getter) and
   `SetLayerBottomAltitude/SetLayerHeight/SetTracingMaxDistance` — `NYCSkyTimeSubsystem.cpp::ApplyAtmosphere`.
4. `UExponentialHeightFogComponent::SetSecondFogDensity/SetSecondFogHeightOffset/SetSecondFogHeightFalloff`.
5. `UNiagaraComponent::SetVariableFloat/SetVariableVec3` (the alternative spelling is
   `SetFloatParameter`/`SetVectorParameter`).
6. `ALandscape::Import(Guid, MinX, MinY, MaxX, MaxY, NumSubsections, SubsectionSizeQuads, HeightData, FileName,
   MaterialLayerData, ELandscapeImportAlphamapType)` argument order.
7. `FImageUtils::LoadImage` / `FImage::AsG16` / `AsG8` availability outside the editor (they are Engine + ImageCore,
   so they should be, but this is the one runtime path that reads a PNG).
8. `UTexture2D::CreateTransient(..., PF_G8, FName)` and `GetPlatformData()->Mips[0].BulkData` locking.
9. `IPythonScriptPlugin`'s `FPythonCommandEx` field names (`Command`, `ExecutionMode`, `Flags`, `LogOutput`).
10. The `unreal.*` Python API surface used by the three scripts — in particular
    `unreal.MaterialEditingLibrary.connect_material_expressions` pin names, `LevelEditorSubsystem.new_level`,
    `EditorActorSubsystem.spawn_actor_from_class` and `MaterialParameterCollection`'s
    `scalar_parameters`/`vector_parameters`. Every node/property write in `import_assets.py` is individually wrapped
    and reported, so a mismatch degrades one material instead of failing the import.

Nothing in this list changes the design; each is a local edit of a handful of lines.
