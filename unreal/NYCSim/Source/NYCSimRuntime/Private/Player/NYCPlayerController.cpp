#include "Player/NYCPlayerController.h"

#include "NYCSimRuntime.h"
#include "Player/NYCInputConfig.h"
#include "Save/NYCSaveSubsystem.h"
#include "UI/NYCMenuWidget.h"
#include "UI/NYCSimHUD.h"

#include "Blueprint/UserWidget.h"
#include "Engine/LocalPlayer.h"
#include "Engine/World.h"
#include "EnhancedInputComponent.h"
#include "EnhancedInputSubsystems.h"
#include "Kismet/GameplayStatics.h"
#include "Kismet/KismetSystemLibrary.h"

ANYCPlayerController::ANYCPlayerController()
{
	bShowMouseCursor = false;
	// The menu pauses the world, so its widgets have to keep ticking while it is paused.
	PrimaryActorTick.bTickEvenWhenPaused = true;
}

void ANYCPlayerController::BeginPlay()
{
	Super::BeginPlay();
	// The common context lives here rather than on the pawn: the menu, the map, quick save and quick
	// load are the player's, not the car's, and the pawn is swapped whenever they get in or out.
	if (UEnhancedInputLocalPlayerSubsystem* Input =
			ULocalPlayer::GetSubsystem<UEnhancedInputLocalPlayerSubsystem>(GetLocalPlayer()))
	{
		Input->AddMappingContext(UNYCInputConfig::Get(this)->GetCommonContext(), 10);
	}
}

void ANYCPlayerController::SetupInputComponent()
{
	Super::SetupInputComponent();
	UEnhancedInputComponent* Input = Cast<UEnhancedInputComponent>(InputComponent);
	if (Input == nullptr)
	{
		UE_LOG(LogNYCSim, Error, TEXT("the player controller has no EnhancedInputComponent; the menu, "
			"the map and quick save are unreachable"));
		return;
	}
	UNYCInputConfig* Config = UNYCInputConfig::Get(this);
	auto Bind = [&](ENYCInputAction Action, void (ANYCPlayerController::*Handler)()) {
		if (UInputAction* Object = Config->GetAction(Action))
		{
			Input->BindAction(Object, ETriggerEvent::Triggered, this, Handler);
		}
	};
	Bind(ENYCInputAction::Menu, &ANYCPlayerController::ToggleMenu);
	Bind(ENYCInputAction::ToggleMap, &ANYCPlayerController::ToggleMap);
	Bind(ENYCInputAction::QuickSave, &ANYCPlayerController::QuickSave);
	Bind(ENYCInputAction::QuickLoad, &ANYCPlayerController::QuickLoad);
}

ANYCSimHUD* ANYCPlayerController::SimHud() const
{
	return Cast<ANYCSimHUD>(GetHUD());
}

UNYCSaveSubsystem* ANYCPlayerController::SaveSubsystem() const
{
	const UWorld* World = GetWorld();
	UGameInstance* Instance = World != nullptr ? World->GetGameInstance() : nullptr;
	return Instance != nullptr ? Instance->GetSubsystem<UNYCSaveSubsystem>() : nullptr;
}

void ANYCPlayerController::ToggleMenu()
{
	SetMenuOpen(!bMenuOpen);
}

void ANYCPlayerController::SetMenuOpen(bool bOpen)
{
	if (bMenuOpen == bOpen)
	{
		return;
	}
	bMenuOpen = bOpen;
	if (bOpen && Menu == nullptr)
	{
		Menu = CreateWidget<UNYCMenuWidget>(this, UNYCMenuWidget::StaticClass());
		if (Menu == nullptr)
		{
			UE_LOG(LogNYCSim, Error, TEXT("the menu widget could not be created"));
			bMenuOpen = false;
			return;
		}
	}
	ApplyMenuState();
}

void ANYCPlayerController::ApplyMenuState()
{
	if (Menu != nullptr)
	{
		if (bMenuOpen)
		{
			Menu->SetOwningController(this);
			Menu->AddToViewport(ANYCSimHUD::MapZOrder + 10);
			Menu->ShowRoot();
		}
		else
		{
			Menu->RemoveFromParent();
		}
	}
	bShowMouseCursor = bMenuOpen;
	if (bMenuOpen)
	{
		FInputModeGameAndUI Mode;
		Mode.SetLockMouseToViewportBehavior(EMouseLockMode::DoNotLock);
		Mode.SetHideCursorDuringCapture(false);
		SetInputMode(Mode);
	}
	else
	{
		SetInputMode(FInputModeGameOnly());
	}
	// Pause ownership: the menu pauses only a world it found running, and unpauses only a world it
	// paused itself. UNYCCameraRigComponent's photo mode pauses too, and the two must not undo each
	// other's state when they happen to overlap.
	if (bMenuOpen)
	{
		if (!UGameplayStatics::IsGamePaused(this))
		{
			bPausedByMenu = UGameplayStatics::SetGamePaused(this, true);
		}
	}
	else if (bPausedByMenu)
	{
		UGameplayStatics::SetGamePaused(this, false);
		bPausedByMenu = false;
	}
	if (ANYCSimHUD* Hud = SimHud())
	{
		Hud->NotifyActivity();
	}
}

void ANYCPlayerController::ToggleMap()
{
	if (bMenuOpen)
	{
		return;
	}
	if (ANYCSimHUD* Hud = SimHud())
	{
		Hud->ToggleMap();
	}
}

void ANYCPlayerController::QuickSave()
{
	UNYCSaveSubsystem* Save = SaveSubsystem();
	if (Save == nullptr)
	{
		return;
	}
	const ENYCSaveResult Result = Save->QuickSave();
	if (Result != ENYCSaveResult::Ok)
	{
		UE_LOG(LogNYCSim, Warning, TEXT("quick save failed: %s"), *Save->GetLastError());
	}
}

void ANYCPlayerController::QuickLoad()
{
	UNYCSaveSubsystem* Save = SaveSubsystem();
	if (Save == nullptr)
	{
		return;
	}
	const ENYCSaveResult Result = Save->QuickLoad();
	if (Result != ENYCSaveResult::Ok)
	{
		UE_LOG(LogNYCSim, Warning, TEXT("quick load failed: %s"), *Save->GetLastError());
	}
}

void ANYCPlayerController::RequestQuit()
{
	SetMenuOpen(false);
	UKismetSystemLibrary::QuitGame(this, this, EQuitPreference::Quit, false);
}
