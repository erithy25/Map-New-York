// The player controller, and the reason there has to be one.
//
// ANYCSimGameMode used APlayerController::StaticClass(), so nothing owned the common input context.
// NYCInputConfig has documented a "Menu Escape" row in its binding table since Stage 12b and the
// action did not exist; ToggleMap (M) and SearchDestination (Tab) did exist and had no handler
// anywhere in the codebase. Pressing any of the three did nothing at all.
//
// This class is where the input that is not driving and not walking lives: the menu, the map, quick
// save and quick load. It owns the pause, so the menu and UNYCCameraRigComponent's photo mode cannot
// fight over it.
#pragma once

#include "CoreMinimal.h"
#include "GameFramework/PlayerController.h"
#include "NYCPlayerController.generated.h"

class ANYCSimHUD;
class UInputAction;
class UNYCMenuWidget;
class UNYCSaveSubsystem;

UCLASS()
class NYCSIMRUNTIME_API ANYCPlayerController : public APlayerController
{
	GENERATED_BODY()

public:
	ANYCPlayerController();

	virtual void BeginPlay() override;
	virtual void SetupInputComponent() override;

	UFUNCTION(BlueprintCallable, Category = "NYCSim|UI")
	void ToggleMenu();

	UFUNCTION(BlueprintCallable, Category = "NYCSim|UI")
	void SetMenuOpen(bool bOpen);

	UFUNCTION(BlueprintPure, Category = "NYCSim|UI")
	bool IsMenuOpen() const { return bMenuOpen; }

	UFUNCTION(BlueprintCallable, Category = "NYCSim|UI")
	void ToggleMap();

	UFUNCTION(BlueprintCallable, Category = "NYCSim|Save")
	void QuickSave();

	UFUNCTION(BlueprintCallable, Category = "NYCSim|Save")
	void QuickLoad();

	/** The menu asks for this when the player picks Resume or Quit. */
	UFUNCTION(BlueprintCallable, Category = "NYCSim|UI")
	void RequestQuit();

protected:
	ANYCSimHUD* SimHud() const;
	UNYCSaveSubsystem* SaveSubsystem() const;

private:
	void ApplyMenuState();

	UPROPERTY(Transient)
	TObjectPtr<UNYCMenuWidget> Menu;

	bool bMenuOpen = false;
	/** So closing the menu does not unpause a world something else paused. */
	bool bPausedByMenu = false;
};
