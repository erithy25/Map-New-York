# NYCSim in Unreal Engine 5.4 — workstation guide

This project is **authored** in a headless Linux container with no Unreal Engine and no GPU
(`docs/ARCHITECTURE.md` §0). Everything under `unreal/` is complete C++ source, configuration, editor Python and
content manifests. It is **compiled, imported and run on a workstation**, following this file. Nothing below has been
executed in the authoring container; where a number is an estimate rather than a measurement it says so.

---

## 1. What you need

| | Minimum | Recommended | Why |
|---|---|---|---|
| Unreal Engine | **5.4** (5.4.4 tested API surface) | 5.4.4 | `EngineAssociation` in `NYCSim.uproject`; 5.5 renamed `TArray::RemoveAt`'s shrink flag and other APIs |
| OS | Windows 10/11 x64 or Linux x64 | Windows 11 + VS 2022 (17.8+) | `DefaultGraphicsRHI_DX12`, `Compiler=VisualStudio2022` in `DefaultEngine.ini` |
| CPU | 8 cores | 16 cores | UBT and the asset import are both parallel |
| RAM | 32 GB | 64 GB | Nanite build of the per-tile shells; the streaming budget alone is 8 GB |
| GPU | **RTX 3060 Ti 8 GB** | RTX 4070 12 GB or better | `DefaultEngine.ini` is now tuned for 8 GB: software Lumen, ray tracing off, a 1500 MB texture pool, a 2048-page shadow atlas, TSR history at 100 %. On a 12 GB card those can go back up — the lines say what each costs |
| Disk | **80 GB free** for the first drivable region | 250–400 GB free SSD for the whole city | Engine 38 GB (Win64 only, no editor debug symbols), VS 2022 **Build Tools** 9 GB — not the 25 GB full workload — repo and content package 4 GB, `Intermediate`+`Binaries` 12 GB, DDC 10 GB, imported content 3 GB |

**On the 8 GB target.** Nanite stays on: for 5.6 GB of building shells it is a net VRAM *win* and it
is the reason a 1:1 city fits on this card at all. What went off is hardware ray tracing (the BVH for
a Nanite city is hundreds of megabytes and a second-generation RT core does not earn it back), the
skin cache (it exists to ray-trace skinned meshes), volumetric clouds and real-time sky capture
(1–2 ms each, until the frame time on the real machine is measured rather than guessed), and the
three mirror scene-captures on the car, which are the single most expensive feature on it.

Also needed on the workstation: the repository itself (this file lives at `unreal/README.md`) and
`data/processed/` produced by the pipeline. The UE project reads the pipeline output through
`data/processed/unreal_manifest.json`, whose `src` paths are relative to the repository root.

---

## 2. Directory expectations

```
<repo>/core/                     compiled into the NYCSimCore module (path is ../../../../core from the module)
<repo>/data/processed/           pipeline output; the manifest points into it
<repo>/unreal/NYCSim/            the UE project
<repo>/unreal/tools/             gen_core_unity.py, fetch_radio.py
```

`NYCSimCore.Build.cs` throws a `BuildException` if `<repo>/core/include` is not where it expects it, so the project
must stay at `<repo>/unreal/NYCSim`.

---

## 3. Build (first time: 25–60 min, incremental: 1–5 min)

The 38 wrapper translation units that pull `core/src` into the `NYCSimCore` module are **committed**,
so step 1 is a check rather than a prerequisite. Run it after changing anything under `core/src`.

```bash
# 1. re-check the wrapper translation units (they are already in the repository)
python3 unreal/tools/gen_core_unity.py --check    # ~2 min; compiles each one as UBT will

# 2. generate project files
#    Windows
"C:\Program Files\Epic Games\UE_5.4\Engine\Build\BatchFiles\Build.bat" -projectfiles -project="%CD%\unreal\NYCSim\NYCSim.uproject" -game -rocket -progress
#    Linux
"$UE_ROOT/Engine/Build/BatchFiles/Linux/GenerateProjectFiles.sh" -project="$PWD/unreal/NYCSim/NYCSim.uproject" -game

# 3. build the editor target
#    Windows
"C:\Program Files\Epic Games\UE_5.4\Engine\Build\BatchFiles\Build.bat" NYCSimEditor Win64 Development -project="%CD%\unreal\NYCSim\NYCSim.uproject" -waitmutex
#    Linux
"$UE_ROOT/Engine/Build/BatchFiles/Linux/Build.sh" NYCSimEditor Linux Development -project="$PWD/unreal/NYCSim/NYCSim.uproject" -waitmutex
```

Expected: **NYCSimCore** ~30 translation units (one per `core/src/**/*.cpp`, unity disabled by contract),
**NYCSimRuntime** ~30, **NYCSimEditor** ~2, plus UHT. Estimated 25–60 min cold on 16 cores including UHT and the
engine's own modules if the engine was installed from source; 5–10 min against a binary engine install.

If the compiler stops in one of the places listed in `unreal/COMPILE_CHECKLIST.md` §7, that section names the file
and the handful of lines involved.

---

## 4. Import the world (headless, no manual clicking)

The pipeline must have produced `data/processed/unreal_manifest.json` first:

```bash
python3 -m nycsim_pipeline.unreal.manifest        # minutes; longer with --no-hash off on a full data set
```

Then, from the repository root:

```bash
# Windows
"C:\Program Files\Epic Games\UE_5.4\Engine\Binaries\Win64\UnrealEditor-Cmd.exe" ^
   "%CD%\unreal\NYCSim\NYCSim.uproject" -run=NYCImport -unattended -nosplash -nopause -stdout

# Linux
"$UE_ROOT/Engine/Binaries/Linux/UnrealEditor-Cmd" \
   "$PWD/unreal/NYCSim/NYCSim.uproject" -run=NYCImport -unattended -nosplash -nopause -stdout
```

Useful options (all optional):

```
-stages=validate,stage,assets,levels,verify   subset of the pipeline
-tiles=t_-3_7,t_-3_8                          import only these tiles (smoke run)
-maxtiles=8                                   import only the first N tiles of the manifest
-manifest=<path>                              a manifest elsewhere
-dryrun                                       print what would happen, touch nothing
-continueonerror                              do not stop at the first failing stage
-nopython                                     C++ stages only (validate/stage/verify)
```

What each stage does and roughly how long it takes (estimates — the container could not run them):

| Stage | Work | Estimate on the recommended machine |
|---|---|---|
| `validate` | reads the manifest, checks every source file and settings id | seconds |
| `stage` | copies `crs.json`, `runtime/*.nycb`, `live/*.json`, `unreal_water.json` and ~900 water masks into `Content/NYCSim/{Runtime,Live}` | < 1 min (≈ 250 MB) |
| `assets` | `import_assets.py`: MPC + 5 materials, then every glb / png / otf in the manifest, with Nanite builds | **3–8 h for the full city**, ~1 min for `-maxtiles=4`; dominated by Nanite + DDC |
| `levels` | `build_levels.py`: the map, 2 levels per tile, landscapes, shells, props, kit | **1–3 h for ~920 tiles**, seconds per tile |
| `verify` | staged `crs.json` proj4 vs. the core's, `tiles.nycb` parse, level packages present | seconds |

The run writes `unreal/NYCSim/Saved/NYCSim/import_report.json` (counts, timings, every skip with its reason) and
exits non-zero if any stage failed.

**Smoke run first.** Four tiles take about a minute and prove the whole chain:

```bash
UnrealEditor-Cmd NYCSim.uproject -run=NYCImport -maxtiles=4 -unattended -nosplash -stdout
```

---

## 5. Run it

Open `unreal/NYCSim/NYCSim.uproject`, load `/Game/NYCSim/Maps/NYC`, press Play. Or headless-ish:

```bash
UnrealEditor NYCSim.uproject /Game/NYCSim/Maps/NYC -game -windowed -resx=2560 -resy=1440
```

Console commands provided by this stage:

| Command | Effect |
|---|---|
| `nycsim.WorldInfo` | CRS, tile count and extent, camera position in NYC_TM and WGS84 |
| `nycsim.Streaming.Stats` | tiles per tier, level counts, memory estimate vs. budget, scheduler timing |
| `nycsim.Streaming.Levels` | every managed streaming level and its wanted/loaded/visible state |
| `nycsim.Streaming.Tile t_-3_7` | one tile: tier, per-tier cost estimate, level package and load state |
| `nycsim.Streaming.Flush` / `nycsim.Streaming.Reset` | block until quiet / unload everything and re-issue |
| `nycsim.Streaming.Debug 1` (`2`) | on-screen streaming HUD (`2` adds a 21 × 21 tile tier map) |
| `nycsim.Streaming.Hz 10` / `nycsim.Streaming.Enabled 0` | scheduler cadence (Hz) / freeze the tier map |
| `nycsim.PrintSun` | clock, ΔT, sun and moon, sunrise/transit/sunset, civil twilight, street-light state |
| `nycsim.Sky.SetTime 2026-07-12T00:20:00Z` | pin the clock (this instant is the 2026 Manhattanhenge sunset) |
| `nycsim.Sky.SetTime now` / `nycsim.Sky.TimeScale 60` | back to real time / 60× |
| `nycsim.Sky.Debug 1` | log the ephemeris at every update |
| `nycsim.Sky.Hz 5` | ephemeris/sky update rate |
| `nycsim.Sky.CloudSunAttenuation 0` | stop cloud cover dimming the direct sun (set 0 when volumetric cloud shadows are on) |
| `nycsim.PrintWeather` | observation, provider, age, circuit breakers, world effects, ESB, tide |
| `nycsim.Overlay 1` (`2`) | weather overlay; `2` adds provider breakers and the raw METAR |
| `nycsim.Weather.Poll` | fetch every provider now |
| `nycsim.Weather.FX 0` | disable the precipitation Niagara systems (materials stay live) |

Everything the sky and weather show is real: the clock is the system clock in America/New_York with the full US
federal DST rule, the sun and moon come from the core's NREL SPA / Meeus implementations, and the weather is
`api.weather.gov` → Open-Meteo → METAR (KLGA/KJFK/KEWR) → last known good marked *stale*. With no network the
overlay says `STALE` and shows the age; it never invents weather.

---

## 6. The one manual step: the four Niagara systems

Everything else in this project is created by script. Niagara systems cannot be: UE 5.4 exposes no Python API for
authoring Niagara emitter graphs, so the four particle systems have to be built once in the editor (or dropped in
from another project) at these paths:

| Asset | Purpose | User parameters the runtime sets |
|---|---|---|
| `/Game/NYCSim/FX/NS_Rain` | rain volume around the camera | `RateMmph` (float, liquid mm/h), `Intensity` (0..1), `WindVelocity` (vector, UE cm/s), `Wetness` (0..1), `TemperatureC` |
| `/Game/NYCSim/FX/NS_Snow` | snow volume | `RateCmph` (float, cm/h), `Intensity`, `WindVelocity`, `Wetness`, `TemperatureC` |
| `/Game/NYCSim/FX/NS_RainSplash` | splash-back on wet ground | `RateMmph`, `Intensity`, `WindVelocity`, `Wetness`, `TemperatureC` |
| `/Game/NYCSim/FX/NS_Steam` | manhole / district-steam plumes | `Intensity` (0..1, rises as the air gets colder), `WindVelocity`, `TemperatureC` |

Create each as an empty Niagara System, add the user parameters with exactly those names and types (User namespace),
and emit inside a box around the component's own location — the runtime keeps the system's actor on the camera.

If a system is missing the game still runs: `UNYCWeatherSubsystem` logs one warning naming the asset, and rain
still darkens the roads, fills the puddles, drives the wipers and headlights, thickens the fog and changes the tyre
friction class. Only the particles are absent. Set `nycsim.Weather.FX 0` to silence the path entirely.

Two optional (not required) assets improve fidelity if you have them:

* `/Game/NYCSim/Sky/T_StarMap` + `M_NYC_StarMap`'s `StarMap` texture parameter — an equirectangular star map.
  Without it the star sphere is skipped and the night sky is the sky atmosphere's own night luminance.
  `M_NYC_StarMap` is created by the import; only the texture is missing. If the map's right-ascension origin
  differs from the code's assumption, rotate it with the material's UVs — the sphere's spin is driven by the local
  apparent sidereal time the SPA returns.
* A tiling water normal map assigned to `M_NYC_Water`'s `WaterNormal` texture parameter. The material is created
  with the engine's flat normal, so water is currently smooth with flow-driven roughness variation but no wave
  normal.

---

## 7. Live data

`services/nycsim_live` writes the snapshots the runtime reads. Run it alongside the game (or before it) so
`Content/NYCSim/Live/` stays fresh:

```bash
python3 -m nycsim_live.weather      # live/weather.json     (also fetched directly by the game over HTTP)
python3 -m nycsim_live.tides        # live/tides.json       -> water level and current
python3 -m nycsim_live.esb_lights   # live/esb_lights.json  -> Empire State Building crown
```

The game fetches weather itself over HTTP; tides and the ESB crown come from those JSON files (re-read every
`TidePollSeconds` / `EsbPollSeconds`), because deriving flood/ebb direction needs the CO-OPS station metadata the
Python service already handles and the ESB page is HTML.

Set `bUseLiveWeather=False` in `Config/DefaultEngine.ini` for a fully offline run: the game then uses
`Content/NYCSim/Live/weather.json` alone and marks it stale as it ages.

---

## 8. Settings worth knowing

`Config/DefaultEngine.ini`, section `[/Script/NYCSimRuntime.NYCSimWorldSettings]`:

| Setting | Default | Notes |
|---|---|---|
| `LoadRadiusL0Metres` / `UnloadRadiusL0Metres` | 900 / 1300 | ADR-008; the core rejects an inconsistent set and logs it |
| `CpuBudgetMegabytes` | 8192 | the scheduler's hard cap; also the apply-side cap |
| `MaxLoadRequestsPerFrame` | 4 | raise for a faster fly-through, lower to cut hitching |
| `bUseRealTime` / `FixedUtcTimeIso8601` / `TimeScale` | true / — / 1 | pin the clock for reproducible captures |
| `ObserverLatitudeDeg` / `LongitudeDeg` | 40.7794 / −73.9692 | Belvedere Castle, Central Park (the KNYC site) |
| `StreetLightSunAltitudeDeg` | −6 | civil dusk; 0.35° of hysteresis |
| `WaterNearRadiusTiles` / `WaterPatchQuads` | 3 / 64 | 7 × 7 km of masked water around the camera |
| `WaterFarExtentKilometres` | 40 | far ocean ring; covers the horizon from the GW Bridge |
| `WeatherPollSeconds` | 60 | ADR-011 cadence |
| `HttpUserAgent` | NYCSim/1.0 … | **change the contact** before running against api.weather.gov at scale |

---

## 9. Packaging (2–6 h, estimated)

```bash
"$UE_ROOT/Engine/Build/BatchFiles/RunUAT.sh" BuildCookRun -project="$PWD/unreal/NYCSim/NYCSim.uproject" \
  -noP4 -platform=Win64 -clientconfig=Development -cook -build -stage -pak -archive \
  -archivedirectory="$PWD/unreal/Build"
```

`Content/NYCSim/Runtime` and `Content/NYCSim/Live` are plain files, not assets: add them as *Additional Non-Asset
Directories to Package* in Project Settings → Packaging (or `+DirectoriesToAlwaysStageAsUFS` in
`DefaultGame.ini`) so `crs.json`, `tiles.nycb`, the water masks and the live snapshots ship with the build.

---

## 9b. Getting the world onto this machine

`data/processed/` and `blender_out/` are gitignored — they are tens of gigabytes of derived
artefacts — so a clone of this repository has all the code and none of the city.

**The first-drive region is already built and pushed.** It is at the tip of the branch
`dist/first-drive` as **update-03**: 35 numbered `.tar.gz` parts, **1.39 GB packed / 2.96 GB
unpacked**, 1,543 files across the 45-tile Manhattan region. It is **complete in itself** -- unlike
update-01 and update-02, which were deltas and which the branch tip no longer carries, it is
unpacked alone and nothing is laid over it. It stands at the state of the metered development
(DEVIATIONS J83), the kerb-side props facing their own kerb (J84), the Hudson Yards platform as a
terrain deck (J85), the woodland canopy declared procedural (J86) and the Citi Bike stations
(Stage 40).

Fetch it into a clone of its own, so the code checkout stays untouched and no history travels:

```bash
git clone --depth 1 --single-branch --branch dist/first-drive <this repository> nyc-content
```

**Do not use `--filter=blob:none`.** A partial clone cannot serve `git checkout <ref> -- <path>` for
these blobs: every part is fetched and then reported as `unable to read sha1 file`.

Each part is a complete archive and no file is ever split across two of them, so they are unpacked
one after another from the repository root -- no concatenation, no temporary file, no elevated
rights:

```bash
# Linux / macOS
for p in ../nyc-content/dist/first-drive/update-03/part_*.tar.gz; do tar -xzf "$p"; done
```

```powershell
# Windows PowerShell.  Do NOT use `cat`: it is text-based and corrupts the archives.
Get-ChildItem ..\nyc-content\dist\first-drive\update-03\part_*.tar.gz |
  Sort-Object Name | ForEach-Object { tar -xzf $_.FullName }
```

Concatenating them into one file also works (`copy /b` on Windows, `cat` on a real shell), but then
`tar` needs `--ignore-zeros` to read past the first archive's end-of-file marker, and the
destination must be a directory you may write to -- the root of `C:` is not.

Each package has an `index.json` naming every file and every part's SHA-256, and an `UNPACK.md`
beside it repeating its own commands. To check what arrived, or to build a package for another
region:

```bash
python3 tools/package_content.py --verify dist/first-drive                        # the base
python3 tools/package_content.py --verify dist/first-drive/update-02              # an update
python3 tools/package_content.py --tile-list <tiles>.txt --out dist/<region>      # to build one
cat dist/<region>/part_*.tar.gz | tar -xzvf - -i -C .                            # to unpack one
```

`tar` ships with Git for Windows, so nothing extra is installed. The `-i` matters: `cat` of several
gzip members is a valid stream and `tar` needs telling to read past the first end-of-archive marker.

What goes in is decided by `unreal_manifest.json` rather than by a hand-written list, so a manifest
that gains an entry gains a file in the package without anyone remembering. The 47-tile Manhattan
region — Times Square, Midtown, the Empire State Building, Grand Central, the Financial District and
the World Trade Center site — is **4.09 GB unpacked**, of which 1.88 GB is tiles (shells, pavement
and the elevated structures), 0.64 GB the 53 landmarks inside the region, 0.51 GB the crowd, 0.42 GB
processed data, 0.25 GB the licensed radio, 0.17 GB the facade kit, 0.14 GB the vehicles and 0.08 GB
the props. It packs to 2.15 GB.

---

## 10. Troubleshooting

| Symptom | Cause and fix |
|---|---|
| `TileStreaming: world data not ready` | `Content/NYCSim/Runtime/{crs.json,tiles.nycb}` missing — run `-run=NYCImport -stages=stage` |
| The car is invisible and falls | The physics asset simulates every bone. `import_assets.py` makes all but `Body` kinematic; if the editor's Python refused, it says so in the log — open `PHYS_FusionHybrid`, delete every body except `Body`, save. This is the one step that may need a human |
| The car has no wheels and no doors move | The skeletal import produced a static mesh. Check `fusion_hybrid.glb` has `skins: 1` (`pytest tests/test_vehicle_rig.py`) and that the Interchange glTF path is enabled |
| Indicators, high beams or DRLs do nothing | The lamp is found by material-slot name. `pytest tests/test_vehicle_contract_agreement.py` compares the exporter's names against `NYCVehicleContract.cpp` |
| A door opens the wrong way, or the wheels roll backwards | The **sign**, not the axis. The rig is built with identity rest orientations so the axes survive the Blender → glTF → Unreal conversion, but Blender's +Y is left and Unreal's is right. Flip the sign in `UNYCVehicleAnimInstance`; deviation J6 |
| The world is bare ground with no roads | `SM_Pavement` did not import or is not placed. Check the manifest lists `tile_pavement.glb` for the tile and that `build_levels.py` ran its `place_pavement` |
| No landmarks anywhere | `data/processed/landmarks/landmarks.json` is missing — regenerate the manifest, which writes it |
| No radio, no sirens | The 74 `.ogg` files are in the manifest as kind `sound`; check they were staged and that `Content/NYCSim/Audio/stations.json` exists |
| Every HUD label is in the engine's default font | The font imported under the wrong name. It must be exactly `/Game/NYCSim/Fonts/F_Overpass` |
| `crs.json: proj4 … differs from the core's` | the pipeline and the core disagree on the CRS; do not edit either by hand, re-run the pipeline's CRS stage |
| `level package … does not exist` (once per tile) | that tile's levels have not been built; run `-stages=levels` |
| Water is grey | `M_NYC_Water` missing — run `-stages=assets`; the actor falls back to the engine default material on purpose |
| Water is missing entirely near the camera | `unreal_water.json` has no `tiles` (the pipeline's water stage has not run); the far ocean ring still renders |
| No landscape | that tile has no `terrain.png`/`terrain.json` in `data/processed/tiles/{tile}` |
| `the manifest lists no tiles; falling back to N tiles found under …` | the manifest predates the terrain/buildings stages; `build_levels.py` scans `data/processed/tiles` instead. Re-run `python -m nycsim_pipeline.unreal.manifest` to refresh it |
| Sky is black at noon | check `nycsim.PrintSun`: a clock before 1967 is rejected by the core's DST rule and logged |
| Weather overlay says `STALE` forever | no network, or `api.weather.gov` refusing the `User-Agent`; `nycsim.Overlay 2` shows the HTTP status per provider |
| Hitching while driving | lower `MaxLoadRequestsPerFrame`, raise `nycsim.Streaming.Hz`, or check `nycsim.Streaming.Stats` for `budget denials` |
