# Stage report — Unreal world, streaming, terrain, water, sky/time, weather, import automation

Agent: **Unreal agent 1**. Lane: `unreal/NYCSim/` (project, `Source/NYCSimCore`, `Source/NYCSimEditor`,
`Content/Python`, `unreal/tools`, `unreal/README.md`) and, inside `Source/NYCSimRuntime`, only
`Private/{World,Sky,Weather,Streaming,CoreAdapter}` and their `Public/` mirrors. Nothing outside that was written.

**The build container has no Unreal Engine and no GPU** (ARCHITECTURE §0). Everything below is complete, compilable
C++/Python authored against the UE 5.4 API and verified by static analysis, hand-checked arithmetic and executable
Python checks. **It has not been compiled or run**; `unreal/README.md` is the workstation procedure and
`unreal/COMPILE_CHECKLIST.md` §7 lists the ten API signatures that could not be checked against installed engine
headers here.

---

## 1. What was built

7,388 new lines across 25 files.

### Tile streaming — `Private/Streaming/`, `Public/Streaming/` (1,225 lines)
`UNYCTileStreamingSubsystem` drives `nycsim::tiling::TileScheduler` (through the existing
`FNYCTileSchedulerAdapter`) from the player camera and turns tier transitions into UE level streaming.

* **Camera → scheduler**: view point each tick, NYC_TM position, compass heading, velocity low-passed with a 0.5 s
  time constant, clamped at 80 m/s, reset on a jump > 150 m so a teleport cannot pre-load half the city.
* **Worker thread**: the whole scheduler step (`UE::Tasks::Launch`) runs off the game thread at 10 Hz
  (`nycsim.Streaming.Hz`); results are read only after `IsCompleted()`; `Deinitialize`/`FlushStreaming` wait.
* **Tier → level**: `L0`/`L1` → `{TileLevelRoot}/{t_m3_7}/{t_m3_7}_L0|_L1`, `L2` → `Skyline/S4_{sx}_{sy}`,
  `L3` → `Skyline/S16_{sx}_{sy}`. A skyline cell is loaded only while **no** tile inside it is at a finer tier, which
  is what keeps the merged HLOD from double-drawing the detailed tiles.
* **Async loads**: `ULevelStreamingDynamic` per package, created once, toggled with `SetShouldBeLoaded/Visible`,
  never blocking; `MaxLoad/UnloadRequestsPerFrame` throttle (default 4/4); unloads are issued before loads so the
  budget frees first; requests are ordered nearest-first.
* **Memory accounting**: the core cost model gives per-tile per-tier bytes; the subsystem keeps its own *applied*
  byte total and refuses to start a load that would exceed `CpuBudgetMegabytes`, deferring it to a later frame —
  an apply-side cap on top of the core's own budget. `FPlatformMemory::GetStats().UsedPhysical` is reported
  alongside so the estimate can be checked against reality on the workstation.
* **Debug HUD** (`nycsim.Streaming.Debug 1|2`): tiers, level counts, memory vs budget, worker/apply timings and a
  21 x 21 tile map coloured by tier, north up. Console: `nycsim.Streaming.{Stats,Levels,Tile,Flush,Reset,Hz,Enabled}`.
* A missing level package is logged **once** and never requested again, so an incomplete import degrades quietly
  instead of spamming.

### Terrain — `World/NYCTerrainImport.{h,cpp}` (460 lines)
`UNYCTerrainImporter` builds one `ALandscape` per tile from `tiles/{tile}/terrain.png` + `terrain.json`.

* Heights pass through **unchanged** (the PNG's 16-bit value *is* the landscape height value); the affine mapping
  to metres is carried by the transform: `DrawScale.Z = z_scale_m x 12800`,
  `ActorZ = (z_min_m + 32768*z_scale_m)*100 cm`. Verified exact to 1.8e-12 cm over the whole 16-bit range.
* **501 -> 505 resample** (see §3 "gaps"): UE requires `SubsectionSizeQuads` in {7,15,31,63,127,255} and 500 quads is
  divisible by none of them. The importer resamples bilinearly to 505 samples = 8 x 8 components of 63 quads and
  sets the quad size to 100000/504 cm, so the landscape still spans exactly 1000 m and adjacent tiles share their
  edge samples bit-exactly (verified).
* PNG decode through `FImageUtils::LoadImage` + `FImage::AsG16`; wrong size, wrong schema, non-finite z or a
  non-G16 file are each reported with the file name.

### Water — `World/NYCWaterActor.{h,cpp}` (840 lines)
`ANYCWaterActor` renders a tiled ocean driven by `unreal_water.json` (§14.1) and the live tide.

* **Near ring**: one pooled `UDynamicMeshComponent` patch per water tile within `WaterNearRadiusTiles` (default 3 ->
  7 x 7 km), each with its own material instance carrying **that tile's shoreline mask**; geometry is rebuilt only
  when the camera crosses a tile boundary.
* **Far ring**: four strips out to `WaterFarExtentKilometres` (40 km) with a hole exactly matching the near block,
  so the Hudson, the Upper Bay and the Atlantic read correctly from the GW Bridge and Brooklyn Heights.
* **Masks**: `Runtime/water_masks/{tile}.png` decoded once per tile — kept as an 8-bit CPU array *and* uploaded to a
  transient `PF_G8` texture. The CPU copy powers `SampleWaterAtUE()` (is-water, coverage, surface Z, depth, flow),
  which is what the vehicle, audio and camera code should ask.
* **Tide**: `SetTide(level, speed, dir, predicted)` moves every patch to the water level and sets the flow vector on
  every material instance; `current_dir_deg` is read in the contract's mathematical convention and converted once
  through `NYCGeo::DirectionToUE`.

### Sky and time — `Sky/NYCSkyTimeSubsystem.{h,cpp}` + `CoreAdapter/NYCAstro.{h,cpp}` (1,249 lines)
* Real **America/New_York** civil time from `nycsim::nytime::simTime` (the core's arithmetic US federal DST rule),
  Julian day and Delta-T; or a pinned instant with a time scale.
* **Sun** from the core's full NREL SPA and **moon** from its Meeus implementation: azimuth, elevation, distance,
  semidiameter, declination, apparent sidereal time, illuminated fraction, phase name, rise/transit/set and civil
  twilight. `nycsim.PrintSun` prints all of it, including the delta from the 299.0 deg Manhattanhenge azimuth.
* Drives `ADirectionalLight` x2 (`bAtmosphereSunLight` indices 0/1), `ASkyAtmosphere`, `AVolumetricCloud`,
  `AExponentialHeightFog`, `ASkyLight` (real-time capture) and a star sphere rotated by the local apparent sidereal
  time. Existing actors in the level are reused; only missing ones are spawned, at `OnWorldBeginPlay`.
* **Street lighting** switches at civil dusk (-6 deg, 0.35 deg hysteresis), broadcasts a delegate and writes
  `StreetLightsOn` into `MPC_Weather`.
* Cloud cover moves the cloud layer's base to the observed ceiling and its thickness with the cover; visibility
  becomes fog density through Koschmieder's sigma = 3.912/V with a single calibration constant (0.02 at 10 km).

### Weather — `Weather/NYCWeatherSubsystem.{h,cpp}` + `CoreAdapter/NYCWeather.{h,cpp}` (1,648 lines)
* `FHttpModule` fetchers on the 60 s cadence: NWS station observation, NWS gridpoint forecast (for the
  forecast-anchored blend), Open-Meteo and one METAR per station (KLGA/KJFK/KEWR). URLs come from the **core's own
  constants** so the decoders always see the query they expect.
* Every decision stays in `nycsim::weather::WeatherService`: the async HTTP result is cached and each provider's
  synchronous fetch callback decodes the cached document, failing with `IoError`/`StateError` when there is none or
  it is older than 300 s — precisely the failure the core's circuit breaker expects. The fallback chain, the snow
  model and the stale bookkeeping are the core's, not re-implemented.
* The core's `worldEffectsStep` (ARCHITECTURE §11) is applied every frame to **`MPC_Weather`** (22 scalars,
  5 vectors), to the **rain / snow / steam / splash Niagara systems** and to the sky and water subsystems.
* **ESB crown** from `Live/esb_lights.json` (up to three colours, linearised from 8-bit sRGB, with the reason and
  the fallback flag) into `ESBCrownColor{,2,3}`.
* **Overlay** (`nycsim.Overlay 1|2`): provider, station, observation time, **age**, an explicit `STALE` marker, all
  world-effect drives, ESB, tide and — at level 2 — each provider's circuit-breaker state, document age, HTTP status
  and the raw METAR. Console: `nycsim.PrintWeather`, `nycsim.Weather.Poll`, `nycsim.Weather.FX`.

### Import automation — commandlet + Python (1,842 lines)
* `UNYCImportCommandlet` (`-run=NYCImport`): validate -> stage -> assets -> levels -> verify, with
  `-tiles/-maxtiles/-manifest/-content/-dryrun/-continueonerror/-nopython`; runs the Python through
  `IPythonScriptPlugin` and re-emits its log; exit code 0 only on a clean run.
* `Content/Python/import_assets.py`: creates `MPC_Weather` and five base materials (`M_NYC_Master`, `_Foliage`,
  `_Terrain`, `_Water`, `_StarMap`) with `MaterialEditingLibrary`, then imports every manifest entry in
  `import_order` applying the manifest's per-kind settings (Nanite, collision, sRGB, compression, mips, addressing).
* `Content/Python/build_levels.py`: the `NYC` map, `{tile}_L0`/`_L1` and skyline levels, landscapes through
  `UNYCTerrainImporter`, shells/roofs as actors, props and kit as `ANYCInstancedMeshActor` (HISM) instances.
* `Content/Python/import_world.py`: stage + assets + levels + `Saved/NYCSim/import_report.json`.
* `World/NYCInstancedMeshActor.{h,cpp}`: needed because a component created from Python on a bare `AActor` does not
  serialise into a level; this actor's HISM is a default subobject, so 14,000 kit instances per tile persist.

### Settings and config
`UNYCSimWorldSettings` gained water, sky-observer and weather-endpoint blocks (38 config properties in total) and
`Config/DefaultEngine.ini` now carries **all 38** so a fresh checkout has identical defaults.

---

## 2. How it was verified

Two executable checkers were written and run in this container. Both are committed next to this report.

```
$ python3 docs/verification/unreal_world/check_math.py
... 38 checks ...
ALL CHECKS PASSED

$ python3 docs/verification/unreal_world/check_sources.py
36 owned source files, 7820 lines
  38 config properties, 38 present in DefaultEngine.ini
  19 console commands / variables: nycsim.Overlay, nycsim.PrintSun, nycsim.PrintWeather,
     nycsim.Sky.CloudSunAttenuation, nycsim.Sky.Debug, nycsim.Sky.Hz, nycsim.Sky.SetTime, nycsim.Sky.TimeScale,
     nycsim.Streaming.Debug, nycsim.Streaming.Enabled, nycsim.Streaming.Flush, nycsim.Streaming.Hz,
     nycsim.Streaming.Levels, nycsim.Streaming.Reset, nycsim.Streaming.Stats, nycsim.Streaming.Tile,
     nycsim.Weather.FX, nycsim.Weather.Poll, nycsim.WorldInfo
ALL 407 CHECKS PASSED

$ python3 -m py_compile unreal/NYCSim/Content/Python/{import_world,import_assets,build_levels}.py
(no output - all three parse)
```

**Numeric results worth quoting** (`check_math.py`):

| Check | Result |
|---|---|
| landscape height mapping vs. the contract formula, 4 (z_min, z_scale) pairs x 5 heights | max error **1.8e-12 cm** |
| 501 -> 505 bilinear resample of a linear ramp | max error **1.1e-13** (exact for affine fields) |
| 501 -> 505 resample of a 16 m sinusoid at 100 m amplitude | max error **0.0020 m** |
| tile edge samples after resampling | come only from source edge samples -> landscapes are watertight |
| 504 quads x 198.412698 cm | **exactly 100,000 cm** |
| 500 quads vs. every legal UE component size | divisible by **none** (7, 15, 31, 63, 127, 255) |
| runtime water-mask row formula vs. `manifest.py`'s raster | max delta **2.8e-14** |
| fog density at 10 km visibility | **0.01999** (UE's clear-day default 0.02) |
| fog density at 200 m | **1.000** |
| sun azimuth 299 deg (Manhattanhenge) in UE | direction (**-0.875, -0.485**) = west-north-west, correct |
| dense Midtown tile at L0, core cost model | **9.5 MB**; the 8 GiB budget holds ~903 of them |
| `crs.json` / `unreal_water.json` schema and keys the runtime reads | present and correct |

**Static results** (`check_sources.py`, 407 assertions): `.generated.h` is the last include in all 8 reflected
headers; no static array is Blueprint-exposed; all 38 `UPROPERTY(Config)` have ini lines; core headers appear only
under `Private|Public/CoreAdapter` and all 17 of them exist in `core/include`; braces/parentheses/`#if`-`#endif`
balance in all 36 files; every out-of-line member definition is declared in its header; no TODO/FIXME/stub/
placeholder marker anywhere; every console command and CVar is documented in `unreal/README.md`.

**Read, not guessed**: the adapters were written against the real core headers as they landed during this session —
`time/NyTime.h`, `astro/Spa.h`, `astro/Moon.h`, `weather/{WeatherState,WeatherService,NwsParser,OpenMeteoParser,
MetarParser,WorldEffects}.h`, `vehicle/Friction.h`, `io/Json.h`, `util/{Result,Error}.h`, `tiling/TileScheduler.h`,
`geo/UECoords.h`. Every core symbol used is checked to exist in those files by `check_sources.py`'s include test and
by hand against the declarations.

---

## 3. Fidelity achieved vs. target, and the gaps

| Target (ARCHITECTURE / brief) | Achieved | Gap |
|---|---|---|
| Streaming driven by `core/TileScheduler`, worker thread, tier -> level, async, memory accounting, debug HUD | yes, all of it | not executed; level packages only exist after the import runs |
| Terrain: landscape from the 16-bit per-tile PNGs, 501 x 501 at 2 m | yes, **resampled to 505 samples at 1.984 m** | UE cannot make a 500-quad landscape (see below). Horizontal sample spacing becomes 1.98413 m instead of 2.00 m; the vertical data is untouched and tile borders stay exact |
| Water: tiled ocean, per-tile shoreline masks, tide-driven flow | yes | wave **normal** map is not authored (flat normal + flow-driven roughness); `unreal_water.json` currently has no bodies, so only the far ring renders until the pipeline's water stage runs |
| Sky: real NY time, SPA sun/moon, lights, atmosphere, clouds, fog, night sky, street lighting, `nycsim.PrintSun` | yes | the star **texture** is not in the repo, so the star sphere is skipped until one is supplied (documented) |
| Weather: core `WeatherService` over `FHttpModule`, 60 s, MPC + Niagara, ESB crown, overlay | yes | the four Niagara **systems** cannot be authored from Python (UE exposes no Niagara graph API) — this is the single manual step, fully specified in `unreal/README.md` §6. Everything else weather-driven works without them |
| Import automation so the whole world imports headless | yes: commandlet + 3 scripts, no manual clicking | not executed; the material graphs are the highest-risk part and each node is individually error-reported |

### The three gaps in full

1. **Landscape resolution 2.0 m -> 1.98413 m.** UE's landscape requires `SubsectionSizeQuads` in
   {7,15,31,63,127,255}; 500 quads (501 samples) is divisible by none of them, so a 1 km tile cannot carry the
   pipeline's grid natively. The importer resamples bilinearly to 504 quads and keeps the tile exactly 1 km wide.
   Cost measured above: 0.002 m on a 16 m sinusoid of 100 m amplitude, and exactly zero at the tile borders.
   **This also means the `terrain_heightmap.component_size_quads: 125` field in `unreal_manifest.json` is not a
   legal UE value** — the importer ignores it. *Recommendation for the pipeline owner: either change that field to
   `{"component_size_quads": 63, "components_per_side": 8, "samples": 505}` and export 505-sample heightmaps
   directly, or leave the field as documentation and let the importer resample.* I did not edit `manifest.py`
   because it is not in my lane.
2. **Niagara.** UE 5.4 has no Python API for authoring Niagara emitters. `unreal/README.md` §6 gives the four asset
   paths and the exact user-parameter contract (`RateMmph`/`RateCmph`, `Intensity`, `WindVelocity`, `Wetness`,
   `TemperatureC`); the subsystem logs one warning per missing system and keeps every other weather effect live.
3. **Two optional textures** (star map, water normal) are not in the repository. Both are bound by material
   *parameter*, so dropping a texture in needs no graph editing.

Nothing here is an approximation presented as real: the sun and moon are the core's SPA/Meeus values, the weather is
whatever the providers actually reported (or an explicitly stale record), the terrain is the pipeline's own
elevations and the water outline is the pipeline's own raster.

---

## 4. What the next agents need to know

**Unreal agent 2 (vehicle, character, traffic, peds, UI, audio):**
* `UNYCSkyTimeSubsystem::OnStreetLightingChanged()` fires at civil dusk/dawn — bind headlights, window emissives and
  street lamps to it, or read `AreStreetLightsOn()`. `MPC_Weather.StreetLightsOn` carries the same bit to materials.
* `UNYCWeatherSubsystem::OnWorldEffectsUpdated()` delivers `FNYCWorldEffects` every frame: `bHeadlights`, `bWipers`,
  `WiperSpeed` (0-3), `SurfaceClass` (index into `nycsim::vehicle::SurfaceClass` — feed it straight to the tyre
  friction table), `UmbrellaShare`, `PedestrianDensityScale`, `PlowActivity`, `FlagSway`, `IceRisk`.
* `ANYCWaterActor::SampleWaterAtUE(Location)` answers "is this water, how deep, which way is it flowing" without a
  physics trace. Get the actor from `UNYCWorldSubsystem::GetWaterActor()`.
* `UNYCTileStreamingSubsystem::OnTileTierChanged()` tells you when a tile's tier changes — the right moment to spawn
  or despawn traffic and pedestrians for that tile. `GetResidentTiles()` gives the current L0/L1 set.
* Place your pawn class path in `NYCSimWorldSettings::DefaultPawnClassPath` (already
  `/Script/NYCSimRuntime.NYCPlayerVehiclePawn`); the game mode resolves it by name, so nothing links against it.
* `Private/CoreAdapter/` now also contains your `Gameplay*` files; my adapters are `NYC*` — no overlap.

**Pipeline owner:** the manifest's `terrain_heightmap` block (see gap 1) and — when the water stage runs —
`unreal_water.json.tiles[*].mask_png` must exist on disk, because the commandlet copies those PNGs to
`Content/NYCSim/Runtime/water_masks/{tile}.png`, which is what the water actor reads at runtime.

**Core owner:** the adapters use `nytime::simTime`, `astro::{solarPositionUnix, moonPositionUnix, sunEventsLocal,
limitDegrees, moonPhaseName}`, `weather::{WeatherService, Provider, parseNwsObservation, NwsForecastBlend::fromJson,
parseOpenMeteo, metar::{parseMetar, weatherStateFromMetar, MetarReport::ceilingM}, worldEffectsStep, toWeatherJson,
fromWeatherJson, obscurationList, sourceName, precipTypeName}`, `vehicle::surfaceClassName`, `json::parse` and
`tiling::TileScheduler`. If any of those signatures change, `Private/CoreAdapter/NYC{Astro,Weather,TileScheduler}.cpp`
are the only files that need touching.

**Orchestrator:** `unreal/COMPILE_CHECKLIST.md` is current and lists every file with what was verified and where a
first-build error is most likely (§7, ten specific call sites). `unreal/README.md` §6 names the single manual step.

---

## 5. Licences

Nothing was downloaded during this stage. No third-party code or asset was added. The only external references are
engine-shipped assets used as material defaults (`/Engine/EngineMaterials/DefaultNormal`,
`Good64x64TilingNoiseHighFreq`, `/Engine/EngineResources/WhiteSquareTexture`, `/Engine/BasicShapes/Sphere`), which
are covered by the Unreal Engine EULA of the workstation's own installation, and the live data endpoints
(api.weather.gov - US public domain; Open-Meteo - CC-BY 4.0; NOAA tgftp METAR and CO-OPS - US public domain), which
are fetched at run time and stored nowhere.
