// The link between the widgets and the screen.
//
// UNYCGpsWidget and SNYCMinimap have been finished C++ and Slate since Stage 12b, and neither has
// ever been displayed: AddToViewport and CreateWidget appeared nowhere in unreal/, there was no AHUD
// subclass, and ANYCSimGameMode never set HUDClass -- although its own header said the HUD class was
// resolved from the world settings. So there was no speedometer, no minimap, no GPS and no clock,
// not because they were unwritten but because nothing asked for them.
//
// This class is that ask. It owns the widget stack: the always-on driving HUD, and the full-screen
// GPS map that the existing UNYCGpsWidget already is. Blueprint-free, like the rest of the project.
#pragma once

#include "CoreMinimal.h"
#include "GameFramework/HUD.h"
#include "NYCSimHUD.generated.h"

class UNYCDrivingHudWidget;
class UNYCGpsWidget;

UCLASS()
class NYCSIMRUNTIME_API ANYCSimHUD : public AHUD
{
	GENERATED_BODY()

public:
	ANYCSimHUD();

	virtual void BeginPlay() override;
	virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;

	/** Opens or closes the full-screen map. Bound to ToggleMap (M) by the player controller. */
	UFUNCTION(BlueprintCallable, Category = "NYCSim|UI")
	void SetMapVisible(bool bVisible);

	UFUNCTION(BlueprintCallable, Category = "NYCSim|UI")
	void ToggleMap();

	UFUNCTION(BlueprintPure, Category = "NYCSim|UI")
	bool IsMapVisible() const { return bMapVisible; }

	/** Tell the HUD the player did something; it un-fades. */
	UFUNCTION(BlueprintCallable, Category = "NYCSim|UI")
	void NotifyActivity();

	/** Interior camera: hide everything the car's own dashboard already shows. */
	UFUNCTION(BlueprintCallable, Category = "NYCSim|UI")
	void SetMinimalMode(bool bMinimal);

	UFUNCTION(BlueprintPure, Category = "NYCSim|UI")
	UNYCDrivingHudWidget* GetDrivingHud() const { return DrivingHud; }

	/** Z-orders. The map covers the driving HUD; nothing else is layered. */
	static constexpr int32 DrivingHudZOrder = 10;
	static constexpr int32 MapZOrder = 20;

private:
	UPROPERTY(Transient)
	TObjectPtr<UNYCDrivingHudWidget> DrivingHud;

	UPROPERTY(Transient)
	TObjectPtr<UNYCGpsWidget> MapWidget;

	bool bMapVisible = false;
};
