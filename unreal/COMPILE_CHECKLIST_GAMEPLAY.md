# UE 5.4 compile checklist — player vehicle, character, cameras, traffic, pedestrians, GPS, audio

**There is no Unreal Engine in this container** (ARCHITECTURE ADR-001): no UBT, no UHT, no engine headers. Every
file below was written against the UE 5.4 API and then *self-reviewed by reading*: include order, module
dependencies, `.generated.h` last, `TObjectPtr` for every reflected UObject reference, garbage-collection
ownership of everything created at runtime, LWC doubles on world positions, UHT restrictions, thread ownership of
every shared buffer, and the exact spelling of every engine call.

**"Verified" in this file means checked by reading the code and the contracts it must satisfy — never compiled.**
The first workstation build is the first compile. §7 is the honest list of calls whose exact signature could not
be checked against installed engine headers; that is where a first-build error, if there is one, will be.

Two things *are* executed here, and they are the reason this lane is more than a paper review:

| Checker | What it does | Result |
|---|---|---|
| `docs/verification/unreal_gameplay/check_gameplay_sources.py` | 1,037 static assertions over the 72 files this lane owns (UHT rules, GC ownership, include resolution, declaration/definition pairing, placeholder ban, adapter purity, licence coverage) | **1,037 checks, 0 failures** |
| `unreal/tools/gameplay_selftest.cpp` | compiles the four core-facing adapter files with `g++ -std=c++17 -O2 -Wall -Wextra` against the **real** `core/` sources and *runs* three 60-second simulations, and asserts the player-car spec and friction table against core's authoritative ones | **74 checks, 0 failures** |

Owner: Unreal agent 2. Files under `Private/{World,Sky,Weather,Streaming}` and `CoreAdapter/NYC*` belong to
Unreal agent 1 and are in `unreal/COMPILE_CHECKLIST.md`, not here. `NYCSimRuntime.Build.cs` is shared: **this
stage added no line to it** — every module these files need was already listed (§1).

---

## 1. Module dependencies actually used by these files

| Header included | Module | In `NYCSimRuntime.Build.cs`? |
|---|---|---|
| `WheeledVehiclePawn.h`, `ChaosWheeledVehicleMovementComponent.h`, `ChaosVehicleWheel.h` | ChaosVehicles | yes (Public) |
| `PhysicalMaterials/PhysicalMaterial.h`, `PhysicsEngine/PhysicsSettings.h` | PhysicsCore / Engine | yes |
| `Components/{SkeletalMesh,StaticMesh,Audio,SpotLight,RectLight,PointLight,Text,Widget,SceneCapture2D,Capsule,SkyLight}Component.h` | Engine | yes |
| `Animation/{AnimInstance,AnimSequence,AnimInstanceProxy}.h`, `BonePose.h`, `AnimationRuntime.h` | Engine | yes |
| `AnimationRuntime.h` (`FAnimationRuntime::BlendTwoPosesTogether`) | Engine | yes |
| `GameFramework/{Character,CharacterMovementComponent,PlayerController,SpringArmComponent}.h` | Engine | yes |
| `EnhancedInputComponent.h`, `EnhancedInputSubsystems.h`, `InputMappingContext.h`, `InputAction.h` | EnhancedInput | yes |
| `CineCameraComponent.h` | CinematicCamera | yes |
| `NavigationSystem.h`, `NavMesh/RecastNavMesh.h`, `NavAreas/NavArea.h`, `NavModifierComponent.h`, `NavMesh/NavMeshBoundsVolume.h` | NavigationSystem | yes |
| `Blueprint/UserWidget.h`, `Components/{CanvasPanel,TextBlock,EditableTextBox,Image,Border,VerticalBox}.h`, `Blueprint/WidgetTree.h` | UMG | yes |
| `Widgets/SLeafWidget.h`, `Rendering/DrawElements.h`, `Fonts/FontMeasure.h` | SlateCore / Slate | yes |
| `Components/SynthComponent.h` | AudioMixer | yes |
| `Sound/{SoundBase,SoundWave,SoundAttenuation}.h`, `Components/AudioComponent.h` | Engine | yes |
| `Kismet/{GameplayStatics,KismetMaterialLibrary}.h`, `Materials/MaterialParameterCollection.h` | Engine | yes |
| `Subsystems/WorldSubsystem.h`, `Engine/World.h`, `EngineUtils.h`, `TimerManager.h` | Engine | yes |
| `Engine/DeveloperSettings.h` | DeveloperSettings | yes |
| `Dom/JsonObject.h`, `Serialization/JsonReader.h`, `Serialization/JsonSerializer.h` | Json | yes |
| `HAL/{Runnable,RunnableThread,PlatformProcess,CriticalSection}.h`, `Async/Async.h`, `HAL/IConsoleManager.h` | Core | yes |
| `Misc/FileHelper.h`, `Misc/Paths.h` | Core | yes |

`MetasoundEngine` / `MetasoundFrontend` are listed in the Build.cs by agent 1 and are **not** included by any file
in this lane: the MetaSound *builder* API is experimental in 5.4 and could not be exercised here, so the audio
sources are `USynthComponent` DSP with a MetaSound-asset preference path that only ever needs `USoundBase`
(§7.6). Nothing in this lane forces the MetaSound modules to be loaded.

---

## 2. Files, and what was checked in each

Line counts are `wc -l`. Every file in this table opens with a comment saying what it is and which contract or
document it implements.

### `Public/Vehicle` · `Private/Vehicle` — the player's car (1,608 + 3,257 lines)

| File | Review notes |
|---|---|
| `NYCVehicleContract.{h,cpp}` (261 + 249) | The Blender ↔ Unreal naming contract: bones (`Body`, `Wheel_FL…`, `Door_*`, `SteeringWheel`, `Wiper_*`, `Window_*`, `Mirror_*`), material slots (`LIGHT_*`, `GAUGE_SPEED`, `GAUGE_RPM`, `SCREEN_CENTER`, `MIRROR_GLASS*`, `PLATE_FACE`), morphs (`DMG_*`), sockets, and the per-bone rotation-axis table. Namespaced `constexpr const TCHAR*`, never `FName` at file scope (an `FName` global would run before `FName`'s allocator exists). `Validate()` reports every missing bone and slot in one pass instead of failing on the first. |
| `NYCVehicleWheels.{h,cpp}` (41 + 74) | `UNYCVehicleWheelBase/Front/Rear : UChaosVehicleWheel`. Only fields that exist on 5.4's `UChaosVehicleWheel` are set (`WheelRadius`, `WheelWidth`, `FrictionForceMultiplier`, `CorneringStiffness`, `MaxSteerAngle`, `AxleType`, `bAffectedByBrake/Handbrake/Engine/Steering`, `SuspensionMaxRaise/Drop`, `SpringRate`, `SuspensionSmoothing`). |
| `NYCVehicleMovementComponent.{h,cpp}` (209 + 576) | Chaos configuration from `PlayerVehicleSpec` (2015 Fusion Hybrid geometry and mass). Per-wheel line trace each substep for `EPhysicalSurface`; friction from `TyreFrictionModel` (ARCHITECTURE §7 values) and MPC_Weather wetness. `ApplyWheelFriction` goes through the `THasSetWheelFrictionMultiplier` detector (§7.1). Road roughness is deterministic value noise, not `FMath::Rand`. Driver input is cached in the component (`SetDriverInput`) rather than read back from the base class, whose getters are version-sensitive. |
| `NYCVehicleAnimInstance.{h,cpp}` (142 + 170) | `FNYCVehicleAnimProxy : FAnimInstanceProxy`. `Evaluate()` resets to the reference pose and applies **local-space** deltas; every bone index goes through `BoneContainer.MakeCompactPoseIndex(FMeshPoseBoneIndex(Index))` and is tested `IsValid()` first. The proxy reads a plain `FNYCVehicleAnimState` copied under the game thread's write, never a UObject pointer. |
| `NYCVehicleLightsComponent.{h,cpp}` (179 + 462) | FMVSS 108: 85 flashes/min, 50 % duty, hyperflash to 130/min on a failed bulb, 180/250 ms halogen rise/fall vs 20/25 ms LED, self-cancelling stalk at 45° of unwind. Real `USpotLightComponent`/`URectLightComponent` for the beams plus emissive parameters on the `LIGHT_*` slots. |
| `NYCVehicleDashboardComponent.{h,cpp}` (161 + 260) | Second-order needle damping (ζ = 0.7, ω = 18 rad/s) so the needles overshoot like real steppers; odometer/trip/instant-MPG maths in US units; `ENYCWarningLamp` is a plain `enum` bitmask, **not** a `UENUM`, because UHT rejects a `uint32` flag enum used as a mask in a `UPROPERTY`. |
| `NYCVehicleBodyComponent.{h,cpp}` (212 + 332) | Wipers (110° arc, 45/70 cycles/min, five intermittent detents, AUTO from rain rate), power windows (4.2 s front / 4.8 s rear), doors (0.55 s to 62°), mirror fold, horn. All timings are on real hardware, all are named constants. |
| `NYCVehicleMirrorComponent.{h,cpp}` (95 + 173) | One `USceneCaptureComponent2D` per mirror at 30 Hz (interior 10 Hz), `SCS_FinalColorLDR`, `bCaptureEveryFrame=false` with explicit `CaptureScene()` so the cost is bounded. Falls back from `MIRROR_GLASS_L/_R/_I` to a single shared `MIRROR_GLASS` slot. Convex wing mirrors get the real 1,400 mm radius distortion parameter. |
| `NYCVehicleDamageComponent.{h,cpp}` (114 + 267) | Five `DMG_*` regions driven by impact impulse and direction; morph targets for deformation, `LIGHT_*` breakage with the lights component's bulb-failure path, glass crack parameter, wheel damage that feeds back into steering pull. |
| `NYCPlayerVehicle.{h,cpp}` (194 + 694) | `AWheeledVehiclePawn` with `ObjectInitializer.SetDefaultSubobjectClass<UNYCVehicleMovementComponent>(AWheeledVehiclePawn::VehicleMovementComponentName)`. Enhanced Input bindings, `NotifyHit` → damage, `FNYCExitVehicleRequested OnExitRequested`. `ANYCPlayerVehiclePawn` is a thin alias subclass so `DefaultEngine.ini`'s `DefaultPawnClassPath` (agent 1's file) resolves without either agent editing the other's. |

### `Public/Character` · `Private/Character` — the player on foot (730 + 1,649 lines)

| File | Review notes |
|---|---|
| `NYCCharacterContract.{h,cpp}` (165 + 98) | UE5 Mannequin bone names, the 40 animation clip ids (`AS_<id>`), material parameters and the ARKit morph list. Same `constexpr const TCHAR*` discipline as the vehicle contract. |
| `NYCCharacterAnimInstance.{h,cpp}` (226 + 482) | Full locomotion state machine inside `FNYCCharacterAnimProxy`. Pose evaluation uses `FPoseContext` + `FAnimationPoseData` + `FAnimationRuntime::BlendTwoPosesTogether` (§7.3). **No `FPoseContext` is ever copied or assigned** — each one is constructed from `Output` and filled in place, because `FPoseContext` has no copy assignment. |
| `NYCPlayerCharacter.{h,cpp}` (91 + 340) | Real speeds (walk 1.4, jog 3.4, sprint 6.0 m/s), 34 cm radius / 176 cm capsule, first- and third-person camera hand-off, and the `UNYCVehicleInteractionComponent` hook. |
| `NYCVehicleInteractionComponent.{h,cpp}` (127 + 370) | Five-beat enter/exit sequence (approach → door → sit → door shut → possess), with the possession swap on the controller and `UFUNCTION() void HandleExitRequested()` bound to the vehicle's delegate — a dynamic delegate target **must** be a `UFUNCTION`, checked. |
| `NYCNavigationSubsystem.{h,cpp}` (121 + 359) | Runtime navmesh over sidewalks, plazas, parks and bridge walkways. `UNYCNavArea_Sidewalk/Park/Roadbed` with real traversal costs; a moving `ANavMeshBoundsVolume` that follows the player; the actor-tag contract (`NYCSidewalk`, `NYCPlaza`, `NYCPark`, `NYCBridgeWalkway`, `NYCRoadbed`, `NYCNotWalkable`). Area assignment is through `UNavModifierComponent`, never `UPrimitiveComponent::AreaClass` (§8). Dynamic generation goes through the `THasSetRuntimeGenerationMode` detector (§7.2). |

### `Public/Traffic` · `Private/Traffic` — the simulated city (423 + 1,578 lines)

| File | Review notes |
|---|---|
| `NYCRoadNetworkSubsystem.{h,cpp}` (97 + 178) | Loads `runtime/*.nycb` on a background task (`AsyncTask(ENamedThreads::AnyBackgroundThreadNormalTask, …)`) with a `TWeakObjectPtr` captured, never `this`; completion hops back to the game thread. After the load the network is immutable, which is what makes it safe to read from the traffic worker. |
| `NYCTrafficWorker.{h,cpp}` (119 + 193) | `FRunnable` stepping the adapter simulation at a fixed 20 Hz on `TPri_BelowNormal`. Double-buffered snapshot behind `SnapshotLock`; config and observer behind `InputLock`; counters are `TAtomic`. `Stop()` sets the flag, `Exit()` joins — no detached thread outlives the subsystem. |
| `NYCTrafficSubsystem.{h,cpp}` (183 + 812) | Actor pools for vehicles and pedestrians keyed by agent id, four LOD bands, the NYC fleet paint palette, and `nycsim.traffic.{stats,density,pause}`. Pool acquisition returns **indices, not pointers**, so a `TArray` reallocation cannot leave a dangling reference. `GetLocalTraffic()` (added this stage) measures the live fleet for the ambience bed. |
| `NYCTrafficVehicle.{h,cpp}` (143 + 276) | Pooled actor: lights, `UTextRenderComponent` destination sign, taxi roof light, siren `UAudioComponent`. The siren registers with `UNYCAudioSubsystem` for Doppler when it starts and unregisters on stop *and* on `Release()` — both paths checked, so a pooled actor never leaves a dangling registration. |

### `Public/Peds` · `Private/Peds` — the crowd (110 + 202 lines)

| File | Review notes |
|---|---|
| `NYCPedestrian.{h,cpp}` | Pooled crowd actor. The walk clip is authored at 1.34 m/s, so play rate is `Speed / 1.34` — the standard foot-sliding fix, and the constant is named. Props (umbrella in rain, bag, phone) attach to the Mannequin hand sockets. |

### `Public/UI` · `Private/UI` — GPS and minimap (340 + 1,263 lines)

| File | Review notes |
|---|---|
| `NYCGpsSubsystem.{h,cpp}` (180 + 443) | Routing off the game thread; the `routing::Router` lives behind an opaque `FNYCGpsRouterState` declared only in the .cpp, so no core type appears in a public header. Turn-by-turn text comes from the road graph's real street names. Off-route detection re-routes at 35 m of lateral error. |
| `SNYCMinimap.{h,cpp}` (73 + 280) | `SLeafWidget`: `OnPaint` draws cached lane polylines, the route, the player arrow, a north needle and a scale bar with `FSlateDrawElement::MakeLines`. `ComputeDesiredSize` returns a fixed size — a leaf widget must not measure children it does not have. |
| `NYCMinimapWidget.{h,cpp}` (62 + 122) | UMG wrapper. `RebuildWidget()` returns the `SNYCMinimap`, `ReleaseSlateResources` clears it — the pair UMG requires. Zoom detents {60, 120, 220, 450, 900, 1800} m. |
| `NYCGpsWidget.{h,cpp}` (98 + 345) | The whole widget tree is built in C++ in `RebuildWidget()` through `WidgetTree->ConstructWidget<…>()`, so the HUD needs no .uasset. US units throughout (miles, feet). |

### `Public/Audio` · `Private/Audio` — everything you hear (889 + 2,527 lines)

| File | Review notes |
|---|---|
| `NYCProceduralSourceComponent.{h,cpp}` (183 + 403) | Eight generators on `USynthComponent`: engine, tyre, wind, rain, wiper, horn, steam vent, subway rumble. Every parameter is a relaxed `std::atomic<float>` written by the game thread and read on the audio render thread; `OnGenerateAudio` allocates nothing, takes no lock, calls no UObject method and touches no `FName`. Noise is a 32-bit xorshift, not `rand()`. |
| `NYCVehicleAudioComponent.{h,cpp}` (133 + 379) | Six sources on the car at the right sockets. Prefers a MetaSound asset when one resolves at the configured path and otherwise instantiates the synthesiser — identical parameter names either way, so the swap is invisible above this component. Pushes the vehicle bus gain every tick. |
| `NYCAudioSubsystem.{h,cpp}` (280 + 1,055) | Ambience zones (actor tags + explicit registration + the live traffic bed), a pooled emitter set, pooled horn and screech voices, Doppler on registered emitters, the on-foot weather bed from MPC_Weather, and six mix buses. Console: `nycsim.audio.{stats,zones,rescan,bus}`. |
| `NYCAmbienceEmitter.{h,cpp}` (125 + 234) | One pooled ambience voice. Root, loop and synth components are all explicitly `EComponentMobility::Movable` because the actor is teleported between zones. Zone kinds with neither a licensed recording nor a generator start no voice at all and are counted, never faked. |
| `NYCRadioSubsystem.{h,cpp}` (164 + 435) | Reads `stations.json` (schema 1) from the fetcher, maps `"jazz/x.ogg"` → `/Game/NYCSim/Audio/Radio/jazz/x.x`, applies the measured `gain_db`, keeps every station's playhead running while it is not tuned, and shows title/artist/licence from the licence records. Console: `nycsim.radio.{list,tune}`. |

### `Public/Player` · `Private/Player` — settings, input, cameras (483 + 675 lines)

| File | Review notes |
|---|---|
| `NYCGameplaySettings.{h,cpp}` (180 + 29) | This lane's own `UDeveloperSettings` (`Config=Game`), so agent 1's settings object is never edited. Holds the MPC path and parameter names, asset roots, traffic caps, audio roots and MetaSound paths, and the input contexts. |
| `NYCInputConfig.{h,cpp}` (120 + 213) | `UInputAction` objects are always created in C++; an `IMC` asset is used when it exists and a transient context with the documented default bindings is built when it does not. The game is therefore playable with an empty Content directory. |
| `NYCCameraRigComponent.{h,cpp}` (183 + 433) | Chase, hood, bumper, interior (head look, lateral lean under lateral g, steering glance, roughness shake), cinematic (five shots on a timer) and photo mode (free-fly `UCineCameraComponent`, focal length, aperture, focus distance, time pause). |

### `Private/CoreAdapter/Gameplay*` — the only place gameplay touches `core` (4,290 lines)

`GameplayRoadNetwork`, `GameplayTrafficSim`, `GameplayPedSim`, `GameplayVehicleDynamics`. **These four contain no
Unreal API at all** — no `CoreMinimal.h`, no `FString`, no `TArray`, no `UE_LOG` — which is asserted mechanically
by the source checker and proved by the fact that `g++` compiles and runs them against the real `core/` sources.
API drift in `core` therefore lands in these four files and nowhere else.

---

## 3. UHT rules checked in every reflected header

* `.generated.h` is the **last** include in all 29 reflected public headers (checked mechanically).
* `GENERATED_BODY()` in every `UCLASS`/`USTRUCT`/`UINTERFACE` (checked mechanically).
* Every `UENUM(BlueprintType)` has an explicit `: uint8` (checked mechanically).
* No C array is exposed to Blueprint: `FNYCTrafficStats`, `FNYCAudioStats`, `FNYCRoadNetworkInfo` use scalars and
  `TArray`, never `int32 X[5]`, which UHT rejects with `BlueprintReadOnly`.
* No `UPROPERTY` inside a non-reflected struct: `FLamp`, `FMirror`, `FZoneRecord`, `FDopplerSource` and
  `FNYCSimSnapshot` are plain C++ and hold no `UPROPERTY` (§5 covers their GC ownership).
* Dynamic-delegate targets are `UFUNCTION()`: `UNYCVehicleInteractionComponent::HandleExitRequested`,
  `UNYCVehicleAudioComponent::HandleHorn/HandleWiperSweep/HandleIndicatorRelay/HandleImpact`.
* `NYCSIMRUNTIME_API` on every public type another translation unit constructs or calls.
* Nested `USTRUCT`s are never declared inside a `UCLASS` (UHT cannot reflect them): `FNYCOneShotVoice` and
  `FNYCAmbienceVoiceSpec` are file-scope `USTRUCT`s.

## 4. LWC (large world coordinates)

Every world position is `FVector` (double) end to end. The four places metres and centimetres meet — the camera
rig, the minimap, the GPS and the audio subsystem — each define a single `constexpr float kCmPerMetre = 100.f`
and cast **explicitly** where a double meets a float, because `FMath::Clamp(double, float, float)` does not
deduce. Every such call site was read individually; the audio subsystem's actor-bounds radius and zone-distance
maths were changed to `static_cast<float>(…)` for exactly this reason.

## 5. Garbage-collection ownership of everything created at runtime

| Object | Created by | Kept alive by |
|---|---|---|
| Pooled traffic vehicles / pedestrians / ambience emitters | `World->SpawnActor` | `UPROPERTY(Transient) TArray<TObjectPtr<…>>` on the owning subsystem |
| Synth and audio components with no owner (horn, screech, world rain/wind voices) | `NewObject<…>(World)` + `RegisterComponentWithWorld` | `UPROPERTY(Transient)` arrays / members on the subsystem |
| `USoundAttenuation` objects built at runtime | `NewObject<USoundAttenuation>(this)` | `UPROPERTY(Transient) TMap<int32, TObjectPtr<USoundAttenuation>>` |
| `UInputAction` objects built in C++ | `NewObject<UInputAction>` | `UPROPERTY` on `UNYCInputConfig`'s holder |
| **`FLamp::Material`** (plain struct, not a `UPROPERTY`) | `UMeshComponent::CreateDynamicMaterialInstance` | the mesh component's own `OverrideMaterials` `UPROPERTY` — the MID is registered on the component that created it, so it cannot be collected while the mesh lives |
| **`FMirror::Material`** (plain struct) | `UMeshComponent::CreateDynamicMaterialInstance` | same as above |
| **`FMirror::Capture`** (plain struct) | `NewObject<USceneCaptureComponent2D>(Owner)` + `RegisterComponent()` | the owning actor's `OwnedComponents` set |
| **`FMirror::Target`** (plain struct) | `NewObject<UTextureRenderTarget2D>(Owner)` | `USceneCaptureComponent2D::TextureTarget`, a `UPROPERTY` on the capture component above |

The source checker enforces that any plain struct holding UObject pointers is named in this section.

## 6. Threading

| Thread | What runs there | How the data is protected |
|---|---|---|
| Traffic worker (`FNYCTrafficWorker`) | `TrafficSim::step()` + `PedSim::step()` at 20 Hz | double-buffered snapshot under `SnapshotLock`; inputs under `InputLock`; counters `TAtomic`; the road network is immutable after load |
| Background task | roadgraph load, route solve | `TWeakObjectPtr` captured (never `this`), result delivered with `AsyncTask(ENamedThreads::GameThread, …)` |
| Audio render thread | `UNYCProceduralSourceComponent::OnGenerateAudio` | every parameter a relaxed `std::atomic`; no allocation, no lock, no UObject access in the callback |
| Game thread | everything else | — |

## 7. Engine calls whose exact signature could not be checked here (the risk list)

1. **`UChaosWheeledVehicleMovementComponent::SetWheelFrictionMultiplier(int32, float)`** — wrapped in the
   `THasSetWheelFrictionMultiplier` SFINAE detector; when the method does not exist the build falls back to
   setting `FrictionForceMultiplier` on the wheel setup, which exists in every 5.x. *Cannot fail to compile.*
2. **`ARecastNavMesh::SetRuntimeGenerationMode(ERuntimeGenerationType)`** — wrapped in
   `THasSetRuntimeGenerationMode`; the fallback assigns `RuntimeGeneration` directly. *Cannot fail to compile.*
3. **`UAnimSequenceBase::GetAnimationPose(FAnimationPoseData&, const FAnimExtractContext&)`** — the 5.1+ form is
   used. If 5.4 kept only the deprecated `GetAnimationPose(FCompactPose&, FBlendedCurve&, …)` overload this is a
   one-line change in `EvaluateClip()`, which is the only call site.
4. **`FAnimationRuntime::BlendTwoPosesTogether(const FAnimationPoseData&, const FAnimationPoseData&, float,
   FAnimationPoseData&)`** — three call sites, all in `NYCCharacterAnimInstance.cpp`.
5. **`FBoneContainer::MakeCompactPoseIndex(const FMeshPoseBoneIndex&)`** — used by both anim proxies; the result
   is always tested with `IsValid()` before indexing.
6. **`USynthComponent::AttenuationSettings`** — assigned on the ambience and one-shot voices. If the member is
   named differently in 5.4 the fallback is `bOverrideAttenuation` + `AttenuationOverrides`, both on the same
   class. `USynthComponent::IsPlaying()` was deliberately **not** used — `ANYCAmbienceEmitter` tracks
   `bSynthRunning` itself — because that accessor is the one most likely to have moved.
7. **`UWidgetTree::ConstructWidget<T>()` and `UUserWidget::RebuildWidget()`** — the C++-built HUD depends on both.
8. **`UAudioComponent::SetPitchMultiplier` / `SetVolumeMultiplier` / `SetSubmixSend`** — the first two are used
   (Doppler and bus gain). `SetSubmixSend` is deliberately **not** used: submix assets are content this stage
   does not author, so the mix is applied as per-source gain, which needs no asset and no submix registration.
9. **`FSoundAttenuationSettings`** — only the fields that have existed unchanged since 4.20 are set
   (`bAttenuate`, `bSpatialize`, `DistanceAlgorithm`, `dBAttenuationAtMax`, `AttenuationShape`,
   `AttenuationShapeExtents`, `FalloffDistance`, `bAttenuateWithLPF`, `LPFRadiusMin/Max`). `OmniRadius` was
   avoided because it was renamed to `NonSpatializedRadius` in the 5.x line.

## 8. Engine APIs deliberately avoided, and why

| Avoided | Reason | Used instead |
|---|---|---|
| `EAllowShrinking` | UE 5.5 API; 5.4 takes a `bool` | `RemoveAtSwap(Index)` / `SetNum(N)` with the default |
| `UPrimitiveComponent::AreaClass`, `SetNavigationRelevancy` | not a stable public path for area assignment | `UNavModifierComponent` |
| `UE_LOG` with a runtime verbosity variable | the verbosity is a compile-time token | explicit `if`/`else` on two `UE_LOG` lines |
| `FPoseContext` copy/assignment | the type has no copy assignment | construct from `Output` and fill in place |
| `MaxWheelspinRotation`, `ExternalTorqueCombineMethod`, `SweepType` on the Chaos component | present in some 5.x versions only | left at their defaults |
| `USynthComponent::IsPlaying()` | most likely accessor to have moved | the emitter tracks its own `bSynthRunning` |
| `FAudioDevice::RegisterSoundSubmix` | runtime submix registration is not a supported content-free path | per-source gain buses |
| `IsTickable()` override on a world subsystem | overriding it wrong stops the subsystem ticking forever (this bug was written and removed) | the base implementation |

## 9. What the checkers actually assert

`python3 docs/verification/unreal_gameplay/check_gameplay_sources.py` — **1,037 checks, 0 failures**, over 72
files (64 Unreal, 8 adapter), 29 reflected public headers:

* no `TODO`/`FIXME`/`XXX`/`HACK` token and no "placeholder"/"not implemented"/"stub" phrase anywhere in the lane;
* balanced braces and parentheses with comments and string literals stripped (catches a truncated file);
* `#pragma once` and an opening comment in every header;
* `.generated.h` present and last; `GENERATED_BODY()` count ≥ reflected type count; `UENUM(BlueprintType) : uint8`;
* every `TObjectPtr` member is either a `UPROPERTY` or belongs to a plain struct named in §5;
* every in-module `#include` resolves to a file that exists;
* every method declared in a lane header has a definition in the matching `Private` folder (this is the check
  that would have caught `UNYCAudioSubsystem` being called before it was written);
* the four adapter files contain no Unreal API;
* every engine call on the §7 risk list appears in this document;
* every fetched SFX file has a licence record, and every `FindSfx()` stem is either a fetched file or a
  documented optional asset (`amb_*`).

`unreal/tools/gameplay_selftest.cpp` — **74 checks, 0 failures**; see
`docs/verification/unreal_gameplay/REPORT.md` for the full output.
