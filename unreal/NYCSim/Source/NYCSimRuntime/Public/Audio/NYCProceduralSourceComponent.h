// Procedural audio sources: engine, tyres, wind, rain and wipers.
//
// ARCHITECTURE §12 asks for MetaSound graphs for these five sources. MetaSound's runtime *builder* API is
// experimental in 5.4 and cannot be exercised in this environment (ADR-001), so the DSP is written here against
// USynthComponent, which is stable, and the parameter contract is identical to the one a MetaSound source would
// expose. UNYCVehicleAudioComponent prefers a MetaSound asset whenever one exists at the configured path and
// falls back to this component otherwise, so adopting the graphs later changes nothing above this line.
//
// The parameter contract (the same names a MetaSound source must declare):
//   Engine   RPM, Load, Throttle, ElectricMix   Tyre   Speed, Roughness, Slip, Wetness
//   Wind     Speed, WindowOpen                  Rain   RainRate, WiperWet
//   Wiper    SweepPhase, Dryness                Horn   Pressed
//   Steam    Intensity, Variation               Rumble Intensity, Variation, PassStrength (+ Pass trigger)
//
// Steam and Rumble are the two street ambiences that carry no sampled asset: a Con Edison sidewalk vent is a
// steam jet, which is band-limited noise, and a subway grate is low-frequency rolling stock through concrete.
// Both are voiced by ANYCAmbienceEmitter. The zones that need a recording instead of a synthesiser (park birds,
// crowd babble, construction, waterfront) stay silent until such a recording is licensed - see the stage report.
//
// The horn is procedural for a reason: no CC0 / CC-BY car-horn recording could be licensed from the sources
// reachable here (see the stage report), and inventing provenance for one is not an option. A US dual-tone horn
// is two reeds a minor third apart around 400-500 Hz, which is exactly what GenerateHorn() produces.
//
// Every parameter is written from the game thread and read on the audio render thread, so each is a relaxed
// std::atomic<float>; no locks and no allocation in OnGenerateAudio.
#pragma once

#include "CoreMinimal.h"
#include "Components/SynthComponent.h"

#include <atomic>

#include "NYCProceduralSourceComponent.generated.h"

UENUM(BlueprintType)
enum class ENYCSourceKind : uint8
{
	Engine = 0,
	Tyre,
	Wind,
	Rain,
	Wiper,
	Horn,
	Steam,
	Rumble
};

UCLASS(ClassGroup = (NYCSim), meta = (BlueprintSpawnableComponent))
class NYCSIMRUNTIME_API UNYCProceduralSourceComponent : public USynthComponent
{
	GENERATED_BODY()

public:
	UNYCProceduralSourceComponent();

	// USynthComponent
	virtual bool Init(int32& SampleRate) override;
	virtual int32 OnGenerateAudio(float* OutAudio, int32 NumSamples) override;

	UFUNCTION(BlueprintCallable, Category = "NYCSim|Audio")
	void SetKind(ENYCSourceKind InKind) { Kind = InKind; }

	UFUNCTION(BlueprintPure, Category = "NYCSim|Audio")
	ENYCSourceKind GetKind() const { return Kind; }

	// ---- engine --------------------------------------------------------------------------------------------
	/** Crankshaft speed in rpm. The firing frequency of a four-cylinder four-stroke is rpm / 30 Hz. */
	UFUNCTION(BlueprintCallable, Category = "NYCSim|Audio")
	void SetEngine(float Rpm, float Load01, float Throttle01, float ElectricMix01);

	// ---- tyre ----------------------------------------------------------------------------------------------
	UFUNCTION(BlueprintCallable, Category = "NYCSim|Audio")
	void SetTyre(float SpeedMps, float Roughness01, float Slip01, float Wetness01);

	// ---- wind ----------------------------------------------------------------------------------------------
	UFUNCTION(BlueprintCallable, Category = "NYCSim|Audio")
	void SetWind(float SpeedMps, float WindowOpen01);

	// ---- rain ----------------------------------------------------------------------------------------------
	UFUNCTION(BlueprintCallable, Category = "NYCSim|Audio")
	void SetRain(float RainRateMmH, float ScreenWetness01);

	// ---- wiper ---------------------------------------------------------------------------------------------
	/** Fires one sweep; `Dryness01` decides how much rubber squeak the sweep carries. */
	UFUNCTION(BlueprintCallable, Category = "NYCSim|Audio")
	void TriggerWiperSweep(float Dryness01);

	/** Dual-tone city horn: two reeds (E4 and G4) with the real attack and release. */
	UFUNCTION(BlueprintCallable, Category = "NYCSim|Audio")
	void SetHornPressed(bool bPressed);

	// ---- ambience (Steam, Rumble) --------------------------------------------------------------------------
	/** `Intensity01` is the zone's strength, `Variation01` how much the source wanders around it. */
	UFUNCTION(BlueprintCallable, Category = "NYCSim|Audio")
	void SetAmbience(float Intensity01, float Variation01);

	/** Rumble only: a train passing under the grate. The swell lasts about eight seconds. */
	UFUNCTION(BlueprintCallable, Category = "NYCSim|Audio")
	void TriggerTrainPass(float Strength01);

	/** Master gain for this source, 0..2. */
	UFUNCTION(BlueprintCallable, Category = "NYCSim|Audio")
	void SetSourceGain(float Gain);

	/** Mix-bus gain, multiplied with the source gain; UNYCAudioSubsystem owns the bus values. */
	UFUNCTION(BlueprintCallable, Category = "NYCSim|Audio")
	void SetBusGain(float Gain);

private:
	float GenerateEngine();
	float GenerateTyre();
	float GenerateWind();
	float GenerateRain();
	float GenerateWiper();
	float GenerateHorn();
	float GenerateSteam();
	float GenerateRumble();

	/** White noise from a deterministic 32-bit LCG; no allocation, no libc rand. */
	float Noise();

	UPROPERTY(EditAnywhere, Category = "NYCSim|Audio")
	ENYCSourceKind Kind = ENYCSourceKind::Engine;

	// Shared render-thread state.
	int32 Rate = 48000;
	float InvRate = 1.f / 48000.f;
	uint32 NoiseState = 0x9E3779B9u;

	// Engine.
	float EnginePhase = 0.f;
	float SmoothedFiringHz = 20.f;
	float SmoothedLoad = 0.f;
	float ElectricPhase = 0.f;

	// Filter state. Only one generator runs per component, so two general-purpose one-pole low passes plus one
	// two-pole band pass cover every kind.
	float FilterA = 0.f;
	float FilterB = 0.f;
	float BandPass1 = 0.f;
	float BandPass2 = 0.f;
	float WindLp = 0.f;
	float WindLp2 = 0.f;
	float RainDropEnvelope = 0.f;

	// Horn.
	float HornPhaseA = 0.f;
	float HornPhaseB = 0.f;
	float HornEnvelope = 0.f;
	std::atomic<int32> ParamHornPressed{0};

	// Ambience (steam vent, subway grate).
	float AmbWander = 0.f;
	float PassPhase = -1.f;
	float PassStrength = 0.f;
	float RumbleLp = 0.f;
	float RumblePhase = 0.f;
	std::atomic<int32> PassTrigger{0};
	std::atomic<float> ParamIntensity{0.f};
	std::atomic<float> ParamVariation{0.f};
	std::atomic<float> ParamPassStrength{0.f};

	// Wiper.
	float WiperEnvelope = 0.f;
	float WiperPhase = 0.f;
	float WiperDryness = 0.f;
	std::atomic<int32> WiperTrigger{0};

	// Parameters (game thread -> audio render thread).
	std::atomic<float> ParamRpm{0.f};
	std::atomic<float> ParamLoad{0.f};
	std::atomic<float> ParamThrottle{0.f};
	std::atomic<float> ParamElectricMix{0.f};
	std::atomic<float> ParamSpeed{0.f};
	std::atomic<float> ParamRoughness{0.f};
	std::atomic<float> ParamSlip{0.f};
	std::atomic<float> ParamWetness{0.f};
	std::atomic<float> ParamWindowOpen{0.f};
	std::atomic<float> ParamRainRate{0.f};
	std::atomic<float> ParamScreenWetness{0.f};
	std::atomic<float> ParamGain{1.f};
	std::atomic<float> ParamBusGain{1.f};
};
