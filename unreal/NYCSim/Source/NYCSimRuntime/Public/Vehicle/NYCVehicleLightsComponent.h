// Exterior and interior lighting for the player car and for any traffic actor that wants real lamps.
//
// Two layers:
//   * every LIGHT_* material slot in the mesh gets a dynamic material instance whose EmissiveScale is driven with
//     the correct lamp physics — an LED reaches full output in ~25 ms, a halogen filament takes ~180 ms to heat
//     and ~250 ms to cool, which is why real brake lights snap on and real headlights glow up;
//   * a small number of real light sources (two headlight spots, one reverse spot, one interior rect) so the road
//     is actually lit. The rest of the lamps are emissive only, which is what keeps 900 traffic cars affordable.
//
// Flasher timing follows FMVSS 108: turn signals flash at 85 cycles/min (0.706 s period) with a 50 % duty cycle,
// hazards run the same relay, and a failed bulb on the flashing side doubles the rate ("hyperflash") because the
// thermal relay sees less load. The relay click is published as an event so the audio subsystem can play it in
// sync instead of guessing.
#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "Vehicle/NYCVehicleContract.h"
#include "NYCVehicleLightsComponent.generated.h"

class UMaterialInstanceDynamic;
class UMeshComponent;
class USpotLightComponent;
class URectLightComponent;

UENUM(BlueprintType)
enum class ENYCHeadlightMode : uint8
{
	Off = 0,
	DaytimeRunning,
	Low,
	High,
	Automatic
};

UENUM(BlueprintType)
enum class ENYCTurnSignal : uint8
{
	None = 0,
	Left,
	Right,
	Hazard
};

DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FNYCRelayClick, bool, bOn);

UCLASS(ClassGroup = (NYCSim), meta = (BlueprintSpawnableComponent))
class NYCSIMRUNTIME_API UNYCVehicleLightsComponent : public UActorComponent
{
	GENERATED_BODY()

public:
	UNYCVehicleLightsComponent();

	virtual void BeginPlay() override;
	virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction) override;

	/** Binds to a mesh: creates one dynamic material instance per LIGHT_* slot present and spawns the lamps. */
	UFUNCTION(BlueprintCallable, Category = "NYCSim|Lights")
	void Initialise(UMeshComponent* InMesh, bool bSpawnRealLights);

	UFUNCTION(BlueprintCallable, Category = "NYCSim|Lights")
	void SetHeadlightMode(ENYCHeadlightMode Mode);

	UFUNCTION(BlueprintPure, Category = "NYCSim|Lights")
	ENYCHeadlightMode GetHeadlightMode() const { return HeadlightMode; }

	/** Cycles Off -> DRL -> Low -> High -> Off (the stalk's real detents). */
	UFUNCTION(BlueprintCallable, Category = "NYCSim|Lights")
	void CycleHeadlights();

	UFUNCTION(BlueprintCallable, Category = "NYCSim|Lights")
	void SetTurnSignal(ENYCTurnSignal Signal);

	UFUNCTION(BlueprintPure, Category = "NYCSim|Lights")
	ENYCTurnSignal GetTurnSignal() const { return TurnSignal; }

	/** Toggles the hazard switch; restores the previous indicator state when switched off. */
	UFUNCTION(BlueprintCallable, Category = "NYCSim|Lights")
	void ToggleHazards();

	/** Self-cancelling indicator: call with the steering input so a completed turn cancels the stalk. */
	UFUNCTION(BlueprintCallable, Category = "NYCSim|Lights")
	void UpdateSelfCancel(float SteeringInput, float DeltaTime);

	UFUNCTION(BlueprintCallable, Category = "NYCSim|Lights")
	void SetBrake(bool bBraking);

	UFUNCTION(BlueprintCallable, Category = "NYCSim|Lights")
	void SetReverse(bool bReversing);

	UFUNCTION(BlueprintCallable, Category = "NYCSim|Lights")
	void SetFogLights(bool bOn);

	UFUNCTION(BlueprintCallable, Category = "NYCSim|Lights")
	void SetInteriorLight(bool bOn);

	/** 0..1 dash backlight, normally tied to the headlight state and the driver's dimmer. */
	UFUNCTION(BlueprintCallable, Category = "NYCSim|Lights")
	void SetDashBrightness(float Brightness01);

	/** Breaks a lamp: 0 = intact, 1 = dead. Broken lamps stop emitting and hyperflash the indicator side. */
	UFUNCTION(BlueprintCallable, Category = "NYCSim|Lights")
	void SetLampBroken(FName SlotName, float Broken01);

	UFUNCTION(BlueprintPure, Category = "NYCSim|Lights")
	bool AreHeadlightsOn() const;

	/** True on the frame the flasher relay changes state (for the audible click). */
	UPROPERTY(BlueprintAssignable, Category = "NYCSim|Lights")
	FNYCRelayClick OnRelayClick;

	/** Emissive multiplier applied to every lamp; the sky subsystem lowers it in daylight so lamps do not bloom. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "NYCSim|Lights", meta = (ClampMin = "0.0"))
	float EmissiveScale = 1.f;

	UPROPERTY(EditAnywhere, Category = "NYCSim|Lights", meta = (ClampMin = "0.0"))
	float HeadlightIntensityLumens = 1200.f;

	UPROPERTY(EditAnywhere, Category = "NYCSim|Lights", meta = (ClampMin = "0.0"))
	float HighBeamIntensityLumens = 2600.f;

private:
	/** One driven lamp. */
	struct FLamp
	{
		FName Slot;
		TObjectPtr<UMaterialInstanceDynamic> Material = nullptr;
		float Target = 0.f;   ///< commanded 0..1
		float Current = 0.f;  ///< filtered output
		float RiseSeconds = 0.025f;
		float FallSeconds = 0.030f;
		float Broken = 0.f;
	};

	void AddLamp(FName Slot, float RiseSeconds, float FallSeconds);
	FLamp* Find(FName Slot);
	void SetTarget(FName Slot, float Value);
	void UpdateFlasher(float DeltaTime);
	void PushToMaterials(float DeltaTime);
	void UpdateRealLights();
	bool IsSideBroken(bool bLeft) const;

	UPROPERTY(Transient)
	TObjectPtr<UMeshComponent> Mesh;

	UPROPERTY(Transient)
	TArray<TObjectPtr<UMaterialInstanceDynamic>> OwnedMaterials;

	UPROPERTY(Transient)
	TObjectPtr<USpotLightComponent> HeadlightLeft;

	UPROPERTY(Transient)
	TObjectPtr<USpotLightComponent> HeadlightRight;

	UPROPERTY(Transient)
	TObjectPtr<USpotLightComponent> ReverseLight;

	UPROPERTY(Transient)
	TObjectPtr<URectLightComponent> InteriorLight;

	TArray<FLamp> Lamps;

	ENYCHeadlightMode HeadlightMode = ENYCHeadlightMode::Off;
	ENYCTurnSignal TurnSignal = ENYCTurnSignal::None;
	ENYCTurnSignal PreHazardSignal = ENYCTurnSignal::None;
	bool bBrakeOn = false;
	bool bReverseOn = false;
	bool bFogOn = false;
	bool bInteriorOn = false;
	float DashBrightness = 0.f;

	// Flasher relay state.
	float FlasherTime = 0.f;
	bool bFlasherOn = false;
	/** Steering integral used to self-cancel the stalk after a completed turn. */
	float SelfCancelIntegral = 0.f;
	bool bSelfCancelArmed = false;
};
