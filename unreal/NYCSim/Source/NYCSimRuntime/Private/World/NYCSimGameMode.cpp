#include "World/NYCSimGameMode.h"
#include "World/NYCSimWorldSettings.h"
#include "World/NYCWorldSubsystem.h"
#include "NYCSimRuntime.h"

#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/DefaultPawn.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/PlayerStart.h"
#include "GameFramework/SpectatorPawn.h"
#include "UObject/UObjectGlobals.h"

ANYCSimGameMode::ANYCSimGameMode()
{
	DefaultPawnClass = ADefaultPawn::StaticClass();
	PlayerControllerClass = APlayerController::StaticClass();
	SpectatorClass = ASpectatorPawn::StaticClass();
	bStartPlayersAsSpectators = false;
}

void ANYCSimGameMode::InitGame(const FString& MapName, const FString& Options, FString& ErrorMessage)
{
	Super::InitGame(MapName, Options, ErrorMessage);

	const UNYCSimWorldSettings& Settings = UNYCSimWorldSettings::Get();
	ResolvedPawnClass = nullptr;
	if (Settings.DefaultPawnClassPath.IsValid())
	{
		UClass* Loaded = Settings.DefaultPawnClassPath.TryLoadClass<APawn>();
		if (Loaded)
		{
			ResolvedPawnClass = Loaded;
			UE_LOG(LogNYCSim, Log, TEXT("Player pawn class: %s"), *Loaded->GetPathName());
		}
		else
		{
			UE_LOG(LogNYCSim, Warning, TEXT("Player pawn class '%s' not found; using fly camera (ADefaultPawn)"),
				*Settings.DefaultPawnClassPath.ToString());
		}
	}
	if (!ResolvedPawnClass)
	{
		ResolvedPawnClass = ADefaultPawn::StaticClass();
	}
	DefaultPawnClass = ResolvedPawnClass;
}

UClass* ANYCSimGameMode::GetDefaultPawnClassForController_Implementation(AController* InController)
{
	return ResolvedPawnClass ? ResolvedPawnClass.Get() : Super::GetDefaultPawnClassForController_Implementation(InController);
}

AActor* ANYCSimGameMode::ChoosePlayerStart_Implementation(AController* Player)
{
	AActor* Start = Super::ChoosePlayerStart_Implementation(Player);
	if (Start)
	{
		return Start;
	}
	UWorld* World = GetWorld();
	if (!World)
	{
		return nullptr;
	}
	if (FallbackStart)
	{
		return FallbackStart;
	}

	const UNYCSimWorldSettings& Settings = UNYCSimWorldSettings::Get();
	FVector Location(0.0, 0.0, 200.0);
	if (const UNYCWorldSubsystem* WorldSys = World->GetSubsystem<UNYCWorldSubsystem>())
	{
		Location = WorldSys->NycTmToUE(Settings.DefaultSpawnNycTm) + FVector(0.0, 0.0, 150.0);
	}
	else
	{
		// UECoords contract: X = east*100, Y = -north*100, Z = up*100
		Location = FVector(Settings.DefaultSpawnNycTm.X * 100.0, -Settings.DefaultSpawnNycTm.Y * 100.0, Settings.DefaultSpawnNycTm.Z * 100.0 + 150.0);
	}
	FActorSpawnParameters Params;
	Params.Name = TEXT("NYCFallbackPlayerStart");
	Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
	APlayerStart* Spawned = World->SpawnActor<APlayerStart>(APlayerStart::StaticClass(), Location, FRotator(0.f, Settings.DefaultSpawnHeadingDeg - 90.f, 0.f), Params);
	FallbackStart = Spawned;
	UE_LOG(LogNYCSim, Log, TEXT("No PlayerStart in map; spawned fallback at NYC_TM (%.1f, %.1f, %.1f)"),
		Settings.DefaultSpawnNycTm.X, Settings.DefaultSpawnNycTm.Y, Settings.DefaultSpawnNycTm.Z);
	return FallbackStart;
}
