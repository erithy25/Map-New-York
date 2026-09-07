// The always-on driving HUD.
//
// Four fixed anchors and nothing floating: speedometer bottom-right, minimap bottom-left, turn card
// top-left, clock and street top-right. Everything it shows is a value the simulation already
// computes and, until now, threw away -- UNYCVehicleMovementComponent::GetSpeedKph,
// UNYCVehicleDashboardComponent::GetGearText, UNYCVehicleLightsComponent's turn signal and headlight
// mode, UNYCGpsSubsystem's next manoeuvre and street, UNYCSkyTimeSubsystem's local time. This widget
// adds no gameplay; it is the first thing in the project that puts any of it on a screen.
//
// Restraint is a feature: the HUD fades to a low opacity after a few seconds without input and
// returns instantly when the player touches anything, and in the interior camera it hides all but
// the turn card, because the car's own dashboard is right there and two speedometers is one too many.
#pragma once

#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "NYCDrivingHudWidget.generated.h"

class SNYCSpeedometer;
class UCanvasPanel;
class UNYCMinimapWidget;
class UNYCVehicleDashboardComponent;
class UNYCVehicleLightsComponent;
class UNYCVehicleMovementComponent;
class UTextBlock;

UCLASS()
class NYCSIMRUNTIME_API UNYCDrivingHudWidget : public UUserWidget
{
	GENERATED_BODY()

public:
	UNYCDrivingHudWidget(const FObjectInitializer& ObjectInitializer);

	virtual void NativeConstruct() override;
	virtual void NativeTick(const FGeometry& MyGeometry, float InDeltaTime) override;

	/** Call on any player input; restores full opacity and restarts the idle timer. */
	UFUNCTION(BlueprintCallable, Category = "NYCSim|UI")
	void NotifyActivity();

	/** Hides everything except the turn card, for the interior camera. */
	UFUNCTION(BlueprintCallable, Category = "NYCSim|UI")
	void SetMinimalMode(bool bMinimal);

	UFUNCTION(BlueprintPure, Category = "NYCSim|UI")
	bool IsMinimalMode() const { return bMinimalMode; }

	/** Displayed speed, damped. Exposed so a test or the self-test can read what is on screen. */
	UFUNCTION(BlueprintPure, Category = "NYCSim|UI")
	float GetDisplayedSpeedKph() const { return DisplayedSpeedKph; }

protected:
	virtual TSharedRef<SWidget> RebuildWidget() override;

private:
	void BuildTree();
	void RefreshFromPawn(float DeltaSeconds);
	void ResolveComponents();

	/** Seconds of no input before the HUD fades back. */
	static constexpr float IdleFadeAfterSeconds = 4.f;
	/** Opacity the HUD rests at once faded. Still legible, no longer competing with the city. */
	static constexpr float IdleOpacity = 0.15f;

	UPROPERTY(Transient)
	TObjectPtr<UCanvasPanel> Root;

	UPROPERTY(Transient)
	TObjectPtr<UNYCMinimapWidget> Minimap;

	UPROPERTY(Transient)
	TObjectPtr<UTextBlock> ManoeuvreGlyph;

	UPROPERTY(Transient)
	TObjectPtr<UTextBlock> ManoeuvreDistance;

	UPROPERTY(Transient)
	TObjectPtr<UTextBlock> ManoeuvreStreet;

	UPROPERTY(Transient)
	TObjectPtr<UTextBlock> ClockText;

	UPROPERTY(Transient)
	TObjectPtr<UTextBlock> StreetText;

	UPROPERTY(Transient)
	TObjectPtr<UTextBlock> TellTaleText;

	UPROPERTY(Transient)
	TWeakObjectPtr<UNYCVehicleMovementComponent> Movement;

	UPROPERTY(Transient)
	TWeakObjectPtr<UNYCVehicleDashboardComponent> Dashboard;

	UPROPERTY(Transient)
	TWeakObjectPtr<UNYCVehicleLightsComponent> Lights;

	TSharedPtr<SNYCSpeedometer> Speedometer;

	bool bTreeBuilt = false;
	bool bMinimalMode = false;
	float DisplayedSpeedKph = 0.f;
	float GaugeOpacity = 1.f;
	float SecondsSinceActivity = 0.f;
	FString GearText = TEXT("N");
	/** Blink phase for the turn-signal tell-tale; the real relay is 1.5 Hz. */
	float BlinkSeconds = 0.f;
};
