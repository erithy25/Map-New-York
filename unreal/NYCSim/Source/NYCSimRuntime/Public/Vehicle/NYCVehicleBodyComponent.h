// Body controls: wipers, power windows, doors, folding mirrors and the horn.
//
// Everything here moves a bone through UNYCVehicleAnimInstance and follows the real mechanism's timing:
//   * Wipers: park position 0°, sweep to 110°, low speed 45 cycles/min, high 70 cycles/min, five intermittent
//     delay settings (0.8 - 12 s) and a mist wipe that performs exactly one sweep. In AUTO the rain sensor uses
//     the weather rain rate: the wiper only runs when there is water on the glass, and the interval shortens as
//     the rate rises, which is what makes the wipers feel connected to the weather rather than to a switch.
//   * Windows: 4.2 s for the full travel of a front glass (measured on the real motor), 4.8 s for the rear,
//     express-down on a long press, and an obstruction stop.
//   * Doors: 0.55 s to swing to 62°, held open until closed; a door left ajar drives the cluster warning and
//     stops the car being driven above walking pace.
//   * Mirrors: 1.4 s power fold.
//   * Horn: a dual-tone (Fa/Fa#) city horn; the component publishes the event and the audio subsystem plays it.
#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "NYCVehicleBodyComponent.generated.h"

class UMeshComponent;
class UNYCVehicleAnimInstance;

UENUM(BlueprintType)
enum class ENYCWiperMode : uint8
{
	Off = 0,
	Intermittent,
	Low,
	High,
	Automatic
};

DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FNYCHornChanged, bool, bPressed);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_TwoParams(FNYCDoorChanged, int32, DoorIndex, bool, bOpen);
/** Fires at each end of a wiper sweep so the audio can play the rubber-on-glass squeak in sync. */
DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FNYCWiperSweep, float, DryFactor);

UCLASS(ClassGroup = (NYCSim), meta = (BlueprintSpawnableComponent))
class NYCSIMRUNTIME_API UNYCVehicleBodyComponent : public UActorComponent
{
	GENERATED_BODY()

public:
	UNYCVehicleBodyComponent();

	virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction) override;

	UFUNCTION(BlueprintCallable, Category = "NYCSim|Body")
	void Initialise(UMeshComponent* InMesh);

	// ---- wipers --------------------------------------------------------------------------------------------
	UFUNCTION(BlueprintCallable, Category = "NYCSim|Body")
	void SetWiperMode(ENYCWiperMode Mode);

	UFUNCTION(BlueprintCallable, Category = "NYCSim|Body")
	void CycleWiperMode();

	/** One single sweep (the stalk's mist position). */
	UFUNCTION(BlueprintCallable, Category = "NYCSim|Body")
	void MistWipe();

	UFUNCTION(BlueprintPure, Category = "NYCSim|Body")
	ENYCWiperMode GetWiperMode() const { return WiperMode; }

	/** 1 of 5 intermittent delay settings (0 = shortest). */
	UFUNCTION(BlueprintCallable, Category = "NYCSim|Body")
	void SetIntermittentSetting(int32 Setting);

	/** Rain rate in mm/h driving the AUTO mode and the windscreen wetness; set by the weather sampler. */
	UFUNCTION(BlueprintCallable, Category = "NYCSim|Body")
	void SetRainRate(float MillimetresPerHour);

	UFUNCTION(BlueprintPure, Category = "NYCSim|Body")
	float GetWiperAngleDeg() const { return WiperAngle; }

	/** 0..1 water on the windscreen; the glass material and the wiper audio both read it. */
	UFUNCTION(BlueprintPure, Category = "NYCSim|Body")
	float GetScreenWetness() const { return ScreenWetness; }

	UPROPERTY(BlueprintAssignable, Category = "NYCSim|Body")
	FNYCWiperSweep OnWiperSweep;

	// ---- windows -------------------------------------------------------------------------------------------
	/** Target 0 (closed) .. 1 (fully down) for one window; index 0=FL 1=FR 2=RL 3=RR. */
	UFUNCTION(BlueprintCallable, Category = "NYCSim|Body")
	void SetWindowTarget(int32 WindowIndex, float Target01);

	UFUNCTION(BlueprintCallable, Category = "NYCSim|Body")
	void NudgeWindow(int32 WindowIndex, float Direction);

	/** Express down / up: runs the glass to its stop without holding the switch. */
	UFUNCTION(BlueprintCallable, Category = "NYCSim|Body")
	void ExpressWindow(int32 WindowIndex, bool bDown);

	UFUNCTION(BlueprintPure, Category = "NYCSim|Body")
	float GetWindowOpen(int32 WindowIndex) const;

	/** Mean opening of the two front windows: the wind and city ambience get louder with it. */
	UFUNCTION(BlueprintPure, Category = "NYCSim|Body")
	float GetCabinOpenness() const;

	// ---- doors ---------------------------------------------------------------------------------------------
	UFUNCTION(BlueprintCallable, Category = "NYCSim|Body")
	void SetDoorOpen(int32 DoorIndex, bool bOpen);

	UFUNCTION(BlueprintPure, Category = "NYCSim|Body")
	bool IsDoorOpen(int32 DoorIndex) const;

	UFUNCTION(BlueprintPure, Category = "NYCSim|Body")
	bool IsAnyDoorAjar() const;

	UFUNCTION(BlueprintCallable, Category = "NYCSim|Body")
	void SetHoodOpen(bool bOpen) { HoodTarget = bOpen ? 1.f : 0.f; }

	UFUNCTION(BlueprintCallable, Category = "NYCSim|Body")
	void SetTrunkOpen(bool bOpen) { TrunkTarget = bOpen ? 1.f : 0.f; }

	UPROPERTY(BlueprintAssignable, Category = "NYCSim|Body")
	FNYCDoorChanged OnDoorChanged;

	// ---- mirrors -------------------------------------------------------------------------------------------
	UFUNCTION(BlueprintCallable, Category = "NYCSim|Body")
	void SetMirrorsFolded(bool bFolded) { MirrorFoldTarget = bFolded ? 1.f : 0.f; }

	UFUNCTION(BlueprintPure, Category = "NYCSim|Body")
	bool AreMirrorsFolded() const { return MirrorFoldTarget > 0.5f; }

	// ---- horn ----------------------------------------------------------------------------------------------
	UFUNCTION(BlueprintCallable, Category = "NYCSim|Body")
	void SetHorn(bool bPressed);

	UFUNCTION(BlueprintPure, Category = "NYCSim|Body")
	bool IsHornPressed() const { return bHorn; }

	UPROPERTY(BlueprintAssignable, Category = "NYCSim|Body")
	FNYCHornChanged OnHornChanged;

	// ---- tuning (real mechanism timings) --------------------------------------------------------------------
	UPROPERTY(EditAnywhere, Category = "NYCSim|Body")
	float WiperSweepDeg = 110.f;

	UPROPERTY(EditAnywhere, Category = "NYCSim|Body")
	float WiperLowCyclesPerMinute = 45.f;

	UPROPERTY(EditAnywhere, Category = "NYCSim|Body")
	float WiperHighCyclesPerMinute = 70.f;

	UPROPERTY(EditAnywhere, Category = "NYCSim|Body")
	float FrontWindowTravelSeconds = 4.2f;

	UPROPERTY(EditAnywhere, Category = "NYCSim|Body")
	float RearWindowTravelSeconds = 4.8f;

	/** Glass height, centimetres: the drop the anim state applies at full open. */
	UPROPERTY(EditAnywhere, Category = "NYCSim|Body")
	float WindowGlassHeightCm = 48.f;

	UPROPERTY(EditAnywhere, Category = "NYCSim|Body")
	float DoorOpenDeg = 62.f;

	UPROPERTY(EditAnywhere, Category = "NYCSim|Body")
	float DoorSwingSeconds = 0.55f;

	UPROPERTY(EditAnywhere, Category = "NYCSim|Body")
	float MirrorFoldDeg = 78.f;

	UPROPERTY(EditAnywhere, Category = "NYCSim|Body")
	float MirrorFoldSeconds = 1.4f;

private:
	void UpdateWipers(float DeltaTime);
	void UpdateWindows(float DeltaTime);
	void UpdateDoors(float DeltaTime);
	void PushAnimState();
	float CurrentSweepSeconds() const;
	float IntermittentDelaySeconds() const;

	UPROPERTY(Transient)
	TObjectPtr<UMeshComponent> Mesh;

	UPROPERTY(Transient)
	TObjectPtr<UNYCVehicleAnimInstance> AnimInstance;

	// Wipers.
	ENYCWiperMode WiperMode = ENYCWiperMode::Off;
	int32 IntermittentSetting = 2;
	float WiperPhase = 0.f;     ///< 0..2, one full there-and-back cycle
	float WiperAngle = 0.f;
	float WiperDelayTimer = 0.f;
	bool bWiperRunning = false;
	bool bMistPending = false;
	float RainRateMmH = 0.f;
	float ScreenWetness = 0.f;
	int32 LastSweepHalf = -1;

	// Windows.
	float WindowOpen[4] = {0.f, 0.f, 0.f, 0.f};
	float WindowTarget[4] = {0.f, 0.f, 0.f, 0.f};

	// Doors.
	float DoorOpen[4] = {0.f, 0.f, 0.f, 0.f};
	float DoorTarget[4] = {0.f, 0.f, 0.f, 0.f};
	float HoodOpen = 0.f;
	float HoodTarget = 0.f;
	float TrunkOpen = 0.f;
	float TrunkTarget = 0.f;

	float MirrorFold = 0.f;
	float MirrorFoldTarget = 0.f;

	bool bHorn = false;
};
