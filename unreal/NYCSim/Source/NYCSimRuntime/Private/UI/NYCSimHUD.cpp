#include "UI/NYCSimHUD.h"

#include "NYCSimRuntime.h"
#include "UI/NYCDrivingHudWidget.h"
#include "UI/NYCGpsWidget.h"

#include "Blueprint/UserWidget.h"
#include "GameFramework/PlayerController.h"

ANYCSimHUD::ANYCSimHUD()
{
	PrimaryActorTick.bCanEverTick = false;
}

void ANYCSimHUD::BeginPlay()
{
	Super::BeginPlay();

	APlayerController* Controller = GetOwningPlayerController();
	if (Controller == nullptr)
	{
		UE_LOG(LogNYCSim, Warning, TEXT("ANYCSimHUD has no owning player controller; no HUD shown"));
		return;
	}

	DrivingHud = CreateWidget<UNYCDrivingHudWidget>(Controller, UNYCDrivingHudWidget::StaticClass());
	if (DrivingHud != nullptr)
	{
		DrivingHud->AddToViewport(DrivingHudZOrder);
	}
	else
	{
		UE_LOG(LogNYCSim, Error, TEXT("driving HUD widget could not be created"));
	}

	// The map is built up front but kept out of the viewport: it owns a minimap that reads the road
	// network, and paying for that on the first press of M is a visible hitch in a moving car.
	MapWidget = CreateWidget<UNYCGpsWidget>(Controller, UNYCGpsWidget::StaticClass());
	if (MapWidget == nullptr)
	{
		UE_LOG(LogNYCSim, Error, TEXT("GPS map widget could not be created"));
	}
}

void ANYCSimHUD::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
	if (DrivingHud != nullptr)
	{
		DrivingHud->RemoveFromParent();
		DrivingHud = nullptr;
	}
	if (MapWidget != nullptr)
	{
		MapWidget->RemoveFromParent();
		MapWidget = nullptr;
	}
	bMapVisible = false;
	Super::EndPlay(EndPlayReason);
}

void ANYCSimHUD::SetMapVisible(bool bVisible)
{
	if (bMapVisible == bVisible || MapWidget == nullptr)
	{
		return;
	}
	bMapVisible = bVisible;
	if (bVisible)
	{
		MapWidget->AddToViewport(MapZOrder);
	}
	else
	{
		MapWidget->RemoveFromParent();
	}
	// The driving HUD stays out of the way while the map is up rather than being drawn under it.
	if (DrivingHud != nullptr)
	{
		DrivingHud->SetVisibility(bVisible ? ESlateVisibility::Collapsed
										   : ESlateVisibility::HitTestInvisible);
	}
	NotifyActivity();
}

void ANYCSimHUD::ToggleMap()
{
	SetMapVisible(!bMapVisible);
}

void ANYCSimHUD::NotifyActivity()
{
	if (DrivingHud != nullptr)
	{
		DrivingHud->NotifyActivity();
	}
}

void ANYCSimHUD::SetMinimalMode(bool bMinimal)
{
	if (DrivingHud != nullptr)
	{
		DrivingHud->SetMinimalMode(bMinimal);
	}
}
