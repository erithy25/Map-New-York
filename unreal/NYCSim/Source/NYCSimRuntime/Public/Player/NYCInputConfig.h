// Enhanced Input actions and mapping contexts for NYCSim, resolvable without any content.
//
// Config/DefaultInput.ini expects IMC_Driving, IMC_OnFoot and IMC_Common under /Game/NYCSim/Input, created by the
// editor import commandlet. This environment cannot run the editor (ADR-001), so the config is *also* able to
// build the identical contexts as transient objects at runtime: UNYCInputConfig::Resolve() loads the assets if
// they exist and otherwise constructs them in C++ from the default bindings table below. The game is therefore
// fully playable from a fresh clone, and identical once the assets exist.
//
// Default bindings (also the table the import commandlet writes into the assets):
//
//   Driving   Throttle      W / Gamepad Right Trigger          Brake         S / Gamepad Left Trigger
//             Steer         A D / Gamepad Left Thumbstick X    Handbrake     Space Bar / Gamepad Face Button Right
//             Reverse       R                                  Horn          H / Gamepad Face Button Left
//             Headlights    L                                  Fog lights    Shift+L
//             Indicate L    Q                                  Indicate R    E
//             Hazards       Z                                  Wipers        K
//             Window down   Comma                              Window up     Period
//             Camera        C                                  Photo mode    P
//             Look          Mouse XY / Gamepad Right Thumbstick
//             Radio next    Right Bracket                      Radio prev    Left Bracket
//             Exit vehicle  F
//   On foot   Move          W A S D / Gamepad Left Thumbstick  Look          Mouse XY / Gamepad Right Thumbstick
//             Jump          Space Bar                          Sprint        Left Shift
//             Crouch        Left Control                       Interact      F
//             Camera        C
//   Common    Map           M                                  Search        Tab
//             Menu          Escape
#pragma once

#include "CoreMinimal.h"
#include "UObject/Object.h"
#include "NYCInputConfig.generated.h"

class UInputAction;
class UInputMappingContext;

/** Every action the gameplay lane binds. */
UENUM(BlueprintType)
enum class ENYCInputAction : uint8
{
	// Driving
	Throttle = 0,
	Brake,
	Steer,
	Handbrake,
	ToggleReverse,
	Horn,
	CycleHeadlights,
	ToggleFogLights,
	IndicateLeft,
	IndicateRight,
	ToggleHazards,
	CycleWipers,
	WindowDown,
	WindowUp,
	CycleCamera,
	PhotoMode,
	LookAround,
	RadioNext,
	RadioPrevious,
	ExitVehicle,
	// On foot
	Move,
	Jump,
	Sprint,
	Crouch,
	Interact,
	// Common
	ToggleMap,
	SearchDestination,
	Count UMETA(Hidden)
};

UCLASS()
class NYCSIMRUNTIME_API UNYCInputConfig : public UObject
{
	GENERATED_BODY()

public:
	/** Builds (or loads) every action and context. Idempotent. */
	void Resolve();

	UFUNCTION(BlueprintPure, Category = "NYCSim|Input")
	UInputAction* GetAction(ENYCInputAction Action) const;

	UFUNCTION(BlueprintPure, Category = "NYCSim|Input")
	UInputMappingContext* GetDrivingContext() const { return DrivingContext; }

	UFUNCTION(BlueprintPure, Category = "NYCSim|Input")
	UInputMappingContext* GetOnFootContext() const { return OnFootContext; }

	UFUNCTION(BlueprintPure, Category = "NYCSim|Input")
	UInputMappingContext* GetCommonContext() const { return CommonContext; }

	/** True when the contexts came from content assets rather than from the built-in defaults. */
	UFUNCTION(BlueprintPure, Category = "NYCSim|Input")
	bool UsingContentAssets() const { return bFromAssets; }

	/** Singleton owned by the game instance; created on first use. */
	static UNYCInputConfig* Get(const UObject* WorldContext);

private:
	UInputAction* MakeAction(ENYCInputAction Action, uint8 ValueType, const TCHAR* Name);
	void BuildDefaultContexts();

	UPROPERTY(Transient)
	TArray<TObjectPtr<UInputAction>> Actions;

	UPROPERTY(Transient)
	TObjectPtr<UInputMappingContext> DrivingContext;

	UPROPERTY(Transient)
	TObjectPtr<UInputMappingContext> OnFootContext;

	UPROPERTY(Transient)
	TObjectPtr<UInputMappingContext> CommonContext;

	bool bResolved = false;
	bool bFromAssets = false;
};
