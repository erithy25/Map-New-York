#include "Audio/NYCProceduralSourceComponent.h"

#include "NYCSimRuntime.h"

namespace
{
constexpr float kTwoPi = 6.28318530718f;

float Clamp01(float V)
{
	return V < 0.f ? 0.f : (V > 1.f ? 1.f : V);
}

/// One-pole low pass; `Cutoff` in Hz.
float LowPass(float& State, float Input, float Cutoff, float SampleRate)
{
	const float Alpha = 1.f - FMath::Exp(-kTwoPi * FMath::Max(1.f, Cutoff) / SampleRate);
	State += Alpha * (Input - State);
	return State;
}
}  // namespace

UNYCProceduralSourceComponent::UNYCProceduralSourceComponent()
{
	bAutoActivate = false;
	// The vehicle's own sources are heard from the driver's seat; the traffic ones are spatialised by their
	// attenuation settings, which the audio subsystem assigns.
	bAllowSpatialization = true;
	PrimaryComponentTick.bCanEverTick = false;
	NumChannels = 1;
}

bool UNYCProceduralSourceComponent::Init(int32& SampleRate)
{
	Rate = SampleRate > 0 ? SampleRate : 48000;
	InvRate = 1.f / static_cast<float>(Rate);
	NumChannels = 1;
	NoiseState = 0x9E3779B9u ^ static_cast<uint32>(static_cast<uint8>(Kind)) * 0x85EBCA6Bu;
	return true;
}

void UNYCProceduralSourceComponent::SetEngine(float Rpm, float Load01, float Throttle01, float ElectricMix01)
{
	ParamRpm.store(FMath::Max(0.f, Rpm), std::memory_order_relaxed);
	ParamLoad.store(Clamp01(Load01), std::memory_order_relaxed);
	ParamThrottle.store(Clamp01(Throttle01), std::memory_order_relaxed);
	ParamElectricMix.store(Clamp01(ElectricMix01), std::memory_order_relaxed);
}

void UNYCProceduralSourceComponent::SetTyre(float SpeedMps, float Roughness01, float Slip01, float Wetness01)
{
	ParamSpeed.store(FMath::Max(0.f, SpeedMps), std::memory_order_relaxed);
	ParamRoughness.store(Clamp01(Roughness01), std::memory_order_relaxed);
	ParamSlip.store(Clamp01(Slip01), std::memory_order_relaxed);
	ParamWetness.store(Clamp01(Wetness01), std::memory_order_relaxed);
}

void UNYCProceduralSourceComponent::SetWind(float SpeedMps, float WindowOpen01)
{
	ParamSpeed.store(FMath::Max(0.f, SpeedMps), std::memory_order_relaxed);
	ParamWindowOpen.store(Clamp01(WindowOpen01), std::memory_order_relaxed);
}

void UNYCProceduralSourceComponent::SetRain(float RainRateMmH, float ScreenWetness01)
{
	ParamRainRate.store(FMath::Max(0.f, RainRateMmH), std::memory_order_relaxed);
	ParamScreenWetness.store(Clamp01(ScreenWetness01), std::memory_order_relaxed);
}

void UNYCProceduralSourceComponent::TriggerWiperSweep(float Dryness01)
{
	ParamWetness.store(Clamp01(1.f - Dryness01), std::memory_order_relaxed);
	WiperTrigger.fetch_add(1, std::memory_order_relaxed);
}

void UNYCProceduralSourceComponent::SetHornPressed(bool bPressed)
{
	ParamHornPressed.store(bPressed ? 1 : 0, std::memory_order_relaxed);
}

void UNYCProceduralSourceComponent::SetAmbience(float Intensity01, float Variation01)
{
	ParamIntensity.store(Clamp01(Intensity01), std::memory_order_relaxed);
	ParamVariation.store(Clamp01(Variation01), std::memory_order_relaxed);
}

void UNYCProceduralSourceComponent::TriggerTrainPass(float Strength01)
{
	ParamPassStrength.store(Clamp01(Strength01), std::memory_order_relaxed);
	PassTrigger.fetch_add(1, std::memory_order_relaxed);
}

void UNYCProceduralSourceComponent::SetSourceGain(float Gain)
{
	ParamGain.store(FMath::Clamp(Gain, 0.f, 2.f), std::memory_order_relaxed);
}

float UNYCProceduralSourceComponent::Noise()
{
	// 32-bit xorshift: uniform in [-1, 1), cheap enough for five voices at 48 kHz.
	NoiseState ^= NoiseState << 13;
	NoiseState ^= NoiseState >> 17;
	NoiseState ^= NoiseState << 5;
	return static_cast<float>(NoiseState >> 8) * (1.f / 8388608.f) - 1.f;
}

float UNYCProceduralSourceComponent::GenerateEngine()
{
	const float Rpm = ParamRpm.load(std::memory_order_relaxed);
	const float Load = ParamLoad.load(std::memory_order_relaxed);
	const float Throttle = ParamThrottle.load(std::memory_order_relaxed);
	const float ElectricMix = ParamElectricMix.load(std::memory_order_relaxed);

	// Firing frequency of a four-cylinder four-stroke: two firings per revolution.
	const float TargetHz = FMath::Clamp(Rpm / 30.f, 8.f, 800.f);
	// 40 ms smoothing keeps a gear change from zipper-noising the oscillator.
	SmoothedFiringHz += (TargetHz - SmoothedFiringHz) * FMath::Min(1.f, InvRate / 0.04f);
	SmoothedLoad += (Load - SmoothedLoad) * FMath::Min(1.f, InvRate / 0.08f);

	EnginePhase += SmoothedFiringHz * InvRate;
	if (EnginePhase >= 1.f)
	{
		EnginePhase -= FMath::FloorToFloat(EnginePhase);
	}

	// Harmonic stack. Under load the higher harmonics come up, which is what makes a labouring engine sound
	// harsher than a coasting one.
	float Sample = 0.f;
	const float Harshness = 0.35f + 0.65f * SmoothedLoad;
	for (int32 H = 1; H <= 10; ++H)
	{
		const float Amplitude = (1.f / static_cast<float>(H)) * FMath::Pow(Harshness, static_cast<float>(H - 1) * 0.5f);
		// Half-order harmonics (0.5, 1.5, ...) are what give a four-cylinder its characteristic burble.
		Sample += Amplitude * FMath::Sin(kTwoPi * (EnginePhase * static_cast<float>(H)));
		Sample += 0.35f * Amplitude * FMath::Sin(kTwoPi * (EnginePhase * (static_cast<float>(H) - 0.5f)));
	}
	Sample *= 0.13f;

	// Intake / exhaust noise, opened by the throttle.
	const float IntakeCutoff = 400.f + 2200.f * Throttle;
	Sample += LowPass(FilterA, Noise(), IntakeCutoff, static_cast<float>(Rate)) * (0.05f + 0.20f * Throttle);

	// Electric drive: a 2 kHz whine from the reduction gear, rising with road speed, mixed in when the ICE is off.
	if (ElectricMix > 0.001f)
	{
		const float Speed = ParamSpeed.load(std::memory_order_relaxed);
		const float WhineHz = FMath::Clamp(320.f + Speed * 78.f, 200.f, 4000.f);
		ElectricPhase += WhineHz * InvRate;
		if (ElectricPhase >= 1.f)
		{
			ElectricPhase -= FMath::FloorToFloat(ElectricPhase);
		}
		const float Whine = 0.5f * FMath::Sin(kTwoPi * ElectricPhase) + 0.25f * FMath::Sin(kTwoPi * ElectricPhase * 2.f);
		Sample = FMath::Lerp(Sample, Whine * 0.10f, ElectricMix);
	}

	// The engine is quiet at idle and loud under power.
	const float Level = 0.25f + 0.75f * FMath::Max(SmoothedLoad, Throttle);
	return Sample * Level;
}

float UNYCProceduralSourceComponent::GenerateTyre()
{
	const float Speed = ParamSpeed.load(std::memory_order_relaxed);
	const float Roughness = ParamRoughness.load(std::memory_order_relaxed);
	const float Slip = ParamSlip.load(std::memory_order_relaxed);
	const float Wetness = ParamWetness.load(std::memory_order_relaxed);

	if (Speed < 0.4f && Slip < 0.05f)
	{
		return 0.f;
	}

	// Rolling noise: broadband, centred higher on a rough surface, louder with speed (roughly v^1.5).
	const float Cutoff = 300.f + 1800.f * Roughness + 30.f * Speed;
	const float Rolling = LowPass(FilterA, Noise(), Cutoff, static_cast<float>(Rate));
	float Sample = Rolling * FMath::Clamp(FMath::Pow(Speed / 20.f, 1.5f), 0.f, 1.2f) * (0.5f + 0.5f * Roughness);

	// Water spray adds hiss that grows with the film depth.
	if (Wetness > 0.01f)
	{
		Sample += Noise() * 0.12f * Wetness * FMath::Clamp(Speed / 12.f, 0.f, 1.f);
	}

	// Slip screech: a resonant band around 1.1 kHz driven by the slip ratio (a two-pole state-variable filter).
	if (Slip > 0.05f)
	{
		const float F = 2.f * FMath::Sin(kTwoPi * 1100.f * InvRate * 0.5f);
		const float Q = 0.06f;
		const float Input = Noise();
		BandPass1 += F * BandPass2;
		const float High = Input - BandPass1 - Q * BandPass2;
		BandPass2 += F * High;
		Sample += BandPass2 * Slip * 0.55f;
	}
	return Sample * 0.5f;
}

float UNYCProceduralSourceComponent::GenerateWind()
{
	const float Speed = ParamSpeed.load(std::memory_order_relaxed);
	const float WindowOpen = ParamWindowOpen.load(std::memory_order_relaxed);
	if (Speed < 1.f && WindowOpen < 0.02f)
	{
		return 0.f;
	}

	// Two cascaded low passes give a -12 dB/octave slope, which reads as air rather than as hiss.
	const float Cutoff = 200.f + 55.f * Speed + 900.f * WindowOpen;
	float Sample = LowPass(WindLp, Noise(), Cutoff, static_cast<float>(Rate));
	Sample = LowPass(WindLp2, Sample, Cutoff * 1.6f, static_cast<float>(Rate));

	// Aerodynamic noise goes with the square of the speed; an open window roughly triples it and adds buffeting.
	const float Level = FMath::Clamp((Speed * Speed) / 900.f, 0.f, 1.2f) * (1.f + 2.2f * WindowOpen);
	return Sample * Level * 0.55f;
}

float UNYCProceduralSourceComponent::GenerateRain()
{
	const float RainRate = ParamRainRate.load(std::memory_order_relaxed);
	if (RainRate < 0.05f)
	{
		return 0.f;
	}
	// Drops on the roof: a Poisson-ish impulse train whose density follows the rate, each impulse a short
	// exponentially decaying click, over a steady hiss.
	const float DropsPerSecond = FMath::Clamp(RainRate * 260.f, 4.f, 12000.f);
	const float Probability = DropsPerSecond * InvRate;
	if (Noise() * 0.5f + 0.5f < Probability)
	{
		RainDropEnvelope = 1.f;
	}
	RainDropEnvelope *= FMath::Exp(-InvRate / 0.004f);
	const float Impacts = Noise() * RainDropEnvelope;
	const float Hiss = LowPass(FilterB, Noise(), 3200.f, static_cast<float>(Rate)) * 0.35f;
	const float Level = FMath::Clamp(RainRate / 8.f, 0.f, 1.2f);
	return (Impacts * 0.6f + Hiss) * Level * 0.5f;
}

float UNYCProceduralSourceComponent::GenerateWiper()
{
	// A sweep is a 0.6 s envelope; the motor hum runs through it and the rubber squeaks when the glass is dry.
	if (WiperTrigger.exchange(0, std::memory_order_relaxed) > 0)
	{
		WiperEnvelope = 1.f;
		WiperPhase = 0.f;
		WiperDryness = 1.f - ParamWetness.load(std::memory_order_relaxed);
	}
	if (WiperEnvelope <= 0.0005f)
	{
		return 0.f;
	}
	WiperPhase += InvRate / 0.6f;
	WiperEnvelope = FMath::Max(0.f, 1.f - WiperPhase);

	// Motor: a 62 Hz hum with its harmonics.
	const float Hum = FMath::Sin(kTwoPi * 62.f * WiperPhase * 0.6f) * 0.3f +
					  FMath::Sin(kTwoPi * 124.f * WiperPhase * 0.6f) * 0.12f;
	// Rubber on glass: filtered noise, quiet on a wet screen and a squeal on a dry one.
	const float Friction = LowPass(FilterB, Noise(), 900.f + 2600.f * WiperDryness, static_cast<float>(Rate));
	const float Squeak = WiperDryness > 0.55f
							 ? FMath::Sin(kTwoPi * (1800.f + 600.f * WiperDryness) * WiperPhase * 0.6f) *
								   (WiperDryness - 0.55f) * 0.6f
							 : 0.f;
	// The sweep is loudest in the middle of the arc where the blade is fastest.
	const float ArcGain = FMath::Sin(FMath::Clamp(WiperPhase, 0.f, 1.f) * PI);
	return (Hum + Friction * 0.35f + Squeak) * ArcGain * WiperEnvelope * 0.35f;
}

float UNYCProceduralSourceComponent::GenerateHorn()
{
	// A US dual-tone horn is two reeds a minor third apart. E4 (329.6 Hz) and G4 (392.0 Hz) is the interval most
	// production horns use; the beating between them is what makes it sound like a car and not like a sine.
	const bool bPressed = ParamHornPressed.load(std::memory_order_relaxed) != 0;
	// 25 ms to full pressure, 60 ms to release: the reeds have mass.
	const float Target = bPressed ? 1.f : 0.f;
	const float Tau = bPressed ? 0.025f : 0.060f;
	HornEnvelope += (Target - HornEnvelope) * FMath::Min(1.f, InvRate / Tau);
	if (HornEnvelope < 0.0005f)
	{
		return 0.f;
	}

	HornPhaseA += 329.63f * InvRate;
	HornPhaseB += 392.00f * InvRate;
	if (HornPhaseA >= 1.f)
	{
		HornPhaseA -= FMath::FloorToFloat(HornPhaseA);
	}
	if (HornPhaseB >= 1.f)
	{
		HornPhaseB -= FMath::FloorToFloat(HornPhaseB);
	}

	// Each reed is rich in odd harmonics; six terms is enough to read as brass rather than as a sine.
	float Sample = 0.f;
	for (int32 H = 1; H <= 6; ++H)
	{
		const float Amplitude = 1.f / static_cast<float>(H * H);
		Sample += Amplitude * FMath::Sin(kTwoPi * HornPhaseA * static_cast<float>(H));
		Sample += Amplitude * FMath::Sin(kTwoPi * HornPhaseB * static_cast<float>(H));
	}
	return Sample * 0.16f * HornEnvelope;
}

float UNYCProceduralSourceComponent::GenerateSteam()
{
	// A sidewalk steam vent is a subsonic jet: broadband noise with the low end rolled off by the aperture and a
	// slow amplitude wander as the plume breathes. Con Edison runs about 105 miles of steam main under Manhattan,
	// and what you hear at a vent is the pressure release, not the boiler.
	const float Intensity = ParamIntensity.load(std::memory_order_relaxed);
	if (Intensity < 0.002f)
	{
		return 0.f;
	}
	const float Variation = ParamVariation.load(std::memory_order_relaxed);

	const float N = Noise();
	// Band pass by subtraction: everything above 700 Hz, then band-limited again at 6 kHz.
	const float Low = LowPass(FilterA, N, 700.f, static_cast<float>(Rate));
	const float Hiss = LowPass(FilterB, N - Low, 6000.f, static_cast<float>(Rate));

	// The plume wanders on a ~1 s time constant; Variation decides how much.
	AmbWander = LowPass(WindLp, Noise(), 1.f, static_cast<float>(Rate));
	const float Envelope = 1.f + FMath::Clamp(AmbWander * 6.f, -0.8f, 0.8f) * Variation;

	return Hiss * Intensity * Envelope * 0.42f;
}

float UNYCProceduralSourceComponent::GenerateRumble()
{
	// A subway grate: a constant low hum of ventilation, plus the swell of a train passing beneath. An R160 on
	// the express track takes roughly eight seconds to pass a grate at 30 mph, and what reaches the street is
	// almost entirely below 200 Hz because the concrete is a low-pass filter.
	const float Intensity = ParamIntensity.load(std::memory_order_relaxed);
	const float Variation = ParamVariation.load(std::memory_order_relaxed);
	if (PassTrigger.exchange(0, std::memory_order_relaxed) > 0)
	{
		PassPhase = 0.f;
		PassStrength = ParamPassStrength.load(std::memory_order_relaxed);
	}

	// Ventilation bed.
	float Sample = LowPass(RumbleLp, Noise(), 120.f, static_cast<float>(Rate)) * Intensity * 0.9f;

	if (PassPhase >= 0.f)
	{
		PassPhase += InvRate / 8.f;
		if (PassPhase >= 1.f)
		{
			PassPhase = -1.f;
		}
		else
		{
			// Raised cosine swell: quiet, loud in the middle of the pass, quiet again.
			const float Swell = 0.5f - 0.5f * FMath::Cos(kTwoPi * PassPhase);
			// Rolling stock: a 34 Hz drone from the trucks with rail joints beating against it.
			RumblePhase += 34.f * InvRate;
			if (RumblePhase >= 1.f)
			{
				RumblePhase -= FMath::FloorToFloat(RumblePhase);
			}
			const float Drone = FMath::Sin(kTwoPi * RumblePhase) * 0.5f + FMath::Sin(kTwoPi * RumblePhase * 2.f) * 0.2f;
			const float Wheels = LowPass(FilterA, Noise(), 260.f + 340.f * Swell, static_cast<float>(Rate));
			Sample += (Drone * 0.55f + Wheels * 0.45f) * Swell * PassStrength;
		}
	}

	// The grate itself rattles a little when the pass is strong.
	if (Variation > 0.01f)
	{
		Sample += LowPass(FilterB, Noise(), 1800.f, static_cast<float>(Rate)) * Variation * 0.06f * Intensity;
	}
	return Sample * 0.5f;
}

int32 UNYCProceduralSourceComponent::OnGenerateAudio(float* OutAudio, int32 NumSamples)
{
	const float Gain = ParamGain.load(std::memory_order_relaxed);
	for (int32 i = 0; i < NumSamples; ++i)
	{
		float Sample = 0.f;
		switch (Kind)
		{
		case ENYCSourceKind::Engine: Sample = GenerateEngine(); break;
		case ENYCSourceKind::Tyre: Sample = GenerateTyre(); break;
		case ENYCSourceKind::Wind: Sample = GenerateWind(); break;
		case ENYCSourceKind::Rain: Sample = GenerateRain(); break;
		case ENYCSourceKind::Wiper: Sample = GenerateWiper(); break;
		case ENYCSourceKind::Horn: Sample = GenerateHorn(); break;
		case ENYCSourceKind::Steam: Sample = GenerateSteam(); break;
		case ENYCSourceKind::Rumble: Sample = GenerateRumble(); break;
		default: break;
		}
		OutAudio[i] = FMath::Clamp(Sample * Gain, -1.f, 1.f);
	}
	return NumSamples;
}
