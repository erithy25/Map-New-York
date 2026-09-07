#include "Save/NYCSaveSubsystem.h"

#include "Audio/NYCRadioSubsystem.h"
#include "NYCSimRuntime.h"
#include "Sky/NYCSkyTimeSubsystem.h"
#include "Streaming/NYCTileStreamingSubsystem.h"
#include "UI/NYCGpsSubsystem.h"
#include "Vehicle/NYCVehicleBodyComponent.h"
#include "Vehicle/NYCVehicleDashboardComponent.h"
#include "Vehicle/NYCVehicleLightsComponent.h"
#include "Vehicle/NYCVehicleMovementComponent.h"
#include "World/NYCWorldSubsystem.h"

#include "Components/PrimitiveComponent.h"
#include "Engine/World.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/App.h"

const TCHAR* UNYCSaveSubsystem::QuickSlot = TEXT("Quick");

namespace
{
/** Heading of a yaw, in the project's compass convention: 0 = north, clockwise. */
float YawToHeading(float Yaw)
{
	return FMath::Fmod(FMath::Fmod(90.f - Yaw, 360.f) + 360.f, 360.f);
}

float HeadingToYaw(float HeadingDeg)
{
	return FMath::Fmod(FMath::Fmod(90.f - HeadingDeg, 360.f) + 360.f, 360.f);
}

/** The build this executable was made from, when it can name itself. */
FString BuildCommit()
{
	return FApp::GetBuildVersion();
}
}  // namespace

void UNYCSaveSubsystem::Initialize(FSubsystemCollectionBase& Collection)
{
	Super::Initialize(Collection);
	LastError.Reset();
}

APawn* UNYCSaveSubsystem::PlayerPawn() const
{
	const UWorld* World = GetWorld();
	if (World == nullptr)
	{
		return nullptr;
	}
	APlayerController* Controller = World->GetFirstPlayerController();
	return Controller != nullptr ? Controller->GetPawn() : nullptr;
}

bool UNYCSaveSubsystem::Capture(UNYCSaveGame& Save) const
{
	UWorld* World = GetWorld();
	APawn* Pawn = PlayerPawn();
	if (World == nullptr || Pawn == nullptr)
	{
		return false;
	}
	const UNYCWorldSubsystem* WorldSub = World->GetSubsystem<UNYCWorldSubsystem>();

	Save.SaveVersion = UNYCSaveGame::CurrentVersion;
	Save.GitCommit = BuildCommit();
	Save.SavedAtUtc = FDateTime::UtcNow();

	const FVector UELocation = Pawn->GetActorLocation();
	Save.PlayerNycTm = WorldSub ? WorldSub->UEToNycTm(UELocation) : UELocation / 100.0;
	Save.PlayerHeadingDeg = YawToHeading(Pawn->GetActorRotation().Yaw);
	Save.VehicleRotation = Pawn->GetActorRotation();

	if (Pawn->FindComponentByClass<UNYCVehicleMovementComponent>() != nullptr)
	{
		Save.bInVehicle = true;
		Save.VehicleNycTm = Save.PlayerNycTm;
		const FVector VelocityUE = Pawn->GetVelocity();
		// Velocity is a direction, not a position, so it converts by the axis mapping alone:
		// east = UE.X, north = -UE.Y, up = UE.Z, all divided by 100.
		Save.VehicleVelocityNycTm = FVector(VelocityUE.X, -VelocityUE.Y, VelocityUE.Z) / 100.0;
	}
	else
	{
		Save.bInVehicle = false;
	}
	if (const UNYCVehicleLightsComponent* Lights = Pawn->FindComponentByClass<UNYCVehicleLightsComponent>())
	{
		Save.HeadlightMode = static_cast<uint8>(Lights->GetHeadlightMode());
		Save.bHazards = Lights->GetTurnSignal() == ENYCTurnSignal::Hazard;
	}
	if (const UNYCVehicleBodyComponent* Body = Pawn->FindComponentByClass<UNYCVehicleBodyComponent>())
	{
		Save.WiperMode = static_cast<uint8>(Body->GetWiperMode());
	}
	if (const UNYCVehicleDashboardComponent* Dash = Pawn->FindComponentByClass<UNYCVehicleDashboardComponent>())
	{
		// The cluster keeps miles because the car it is modelled on does; the save keeps kilometres
		// because everything else in this project is metric, and one conversion in one place is
		// cheaper than two units in the same file.
		Save.OdometerKm = Dash->GetOdometerMiles() * 1.609344f;
	}

	if (const UNYCSkyTimeSubsystem* Sky = World->GetSubsystem<UNYCSkyTimeSubsystem>())
	{
		Save.SimUtc = FDateTime::FromUnixTimestamp(static_cast<int64>(Sky->GetSimUnixSeconds()));
		Save.SimLocalTime = Sky->GetLocalTime();
	}
	if (const UNYCGpsSubsystem* Gps = World->GetSubsystem<UNYCGpsSubsystem>())
	{
		Save.Street = Gps->GetCurrentStreet();
		Save.bRouteActive = Gps->HasRoute();
		if (Save.bRouteActive)
		{
			const FVector Destination = Gps->GetDestination();
			Save.RouteDestinationNycTm = WorldSub ? WorldSub->UEToNycTm(Destination) : Destination / 100.0;
		}
	}
	if (const UNYCRadioSubsystem* Radio = World->GetSubsystem<UNYCRadioSubsystem>())
	{
		FNYCRadioStation Station;
		if (Radio->GetStation(Radio->GetCurrentStationIndex(), Station))
		{
			Save.RadioStationId = Station.Id;
		}
	}
	return true;
}

bool UNYCSaveSubsystem::Apply(const UNYCSaveGame& Save)
{
	UWorld* World = GetWorld();
	APawn* Pawn = PlayerPawn();
	if (World == nullptr || Pawn == nullptr)
	{
		LastError = TEXT("no world or no possessed pawn");
		return false;
	}
	const UNYCWorldSubsystem* WorldSub = World->GetSubsystem<UNYCWorldSubsystem>();
	const FVector TargetUE = WorldSub ? WorldSub->NycTmToUE(Save.PlayerNycTm) : Save.PlayerNycTm * 100.0;

	// ---- the part that matters -------------------------------------------------------------------
	// Move the streamer's camera to the destination and wait for the tiles before the pawn goes
	// anywhere. Teleporting first drops the car into a hole 2,916 km2 wide: the ground it should land
	// on is a level that has not been loaded yet, and it falls until the engine kills it.
	UNYCTileStreamingSubsystem* Streaming = World->GetSubsystem<UNYCTileStreamingSubsystem>();
	if (Streaming != nullptr)
	{
		Streaming->SetCameraOverride(TargetUE, Save.PlayerHeadingDeg, FVector2D::ZeroVector);
		Streaming->FlushStreaming();
	}
	else
	{
		UE_LOG(LogNYCSim, Warning, TEXT("no tile streaming subsystem; loading a save may drop the "
			"player through unloaded ground"));
	}

	// Physics off while the pawn is moved, so the restore is a placement and not a collision.
	UPrimitiveComponent* Root = Cast<UPrimitiveComponent>(Pawn->GetRootComponent());
	const bool bWasSimulating = Root != nullptr && Root->IsSimulatingPhysics();
	if (Root != nullptr && bWasSimulating)
	{
		Root->SetSimulatePhysics(false);
	}
	Pawn->SetActorLocationAndRotation(TargetUE, Save.VehicleRotation, false, nullptr, ETeleportType::ResetPhysics);
	if (Root != nullptr && bWasSimulating)
	{
		Root->SetSimulatePhysics(true);
		// Restore the velocity in engine axes: east -> +X, north -> -Y, up -> +Z.
		const FVector V = Save.VehicleVelocityNycTm * 100.0;
		Root->SetPhysicsLinearVelocity(FVector(V.X, -V.Y, V.Z));
		Root->SetPhysicsAngularVelocityInDegrees(FVector::ZeroVector);
	}
	if (Streaming != nullptr)
	{
		// The scheduler follows the player again from here.
		Streaming->ClearCameraOverride();
	}

	if (UNYCVehicleLightsComponent* Lights = Pawn->FindComponentByClass<UNYCVehicleLightsComponent>())
	{
		Lights->SetHeadlightMode(static_cast<ENYCHeadlightMode>(Save.HeadlightMode));
		Lights->SetTurnSignal(Save.bHazards ? ENYCTurnSignal::Hazard : ENYCTurnSignal::None);
	}
	if (UNYCVehicleBodyComponent* Body = Pawn->FindComponentByClass<UNYCVehicleBodyComponent>())
	{
		Body->SetWiperMode(static_cast<ENYCWiperMode>(Save.WiperMode));
	}
	if (UNYCSkyTimeSubsystem* Sky = World->GetSubsystem<UNYCSkyTimeSubsystem>())
	{
		Sky->SetFollowRealTime(Save.bUseRealTime);
		Sky->SetTimeScale(Save.TimeScale);
		if (!Save.bUseRealTime)
		{
			Sky->SetSimTimeIso8601(Save.SimUtc.ToIso8601());
		}
	}
	if (UNYCGpsSubsystem* Gps = World->GetSubsystem<UNYCGpsSubsystem>())
	{
		if (Save.bRouteActive)
		{
			const FVector Destination = WorldSub ? WorldSub->NycTmToUE(Save.RouteDestinationNycTm)
												 : Save.RouteDestinationNycTm * 100.0;
			Gps->SetDestinationWorld(Destination);
		}
		else
		{
			Gps->ClearDestination();
		}
	}
	if (UNYCRadioSubsystem* Radio = World->GetSubsystem<UNYCRadioSubsystem>())
	{
		for (int32 i = 0; i < Radio->GetStationCount(); ++i)
		{
			FNYCRadioStation Station;
			if (Radio->GetStation(i, Station) && Station.Id == Save.RadioStationId)
			{
				Radio->SetStation(i);
				break;
			}
		}
	}
	return true;
}

ENYCSaveResult UNYCSaveSubsystem::SaveToSlot(const FString& SlotName, const FString& DisplayName)
{
	LastError.Reset();
	if (SlotName.IsEmpty())
	{
		LastError = TEXT("no slot name");
		return ENYCSaveResult::NoSlot;
	}
	UNYCSaveGame* Save = Cast<UNYCSaveGame>(UGameplayStatics::CreateSaveGameObject(UNYCSaveGame::StaticClass()));
	if (Save == nullptr)
	{
		LastError = TEXT("save object could not be created");
		return ENYCSaveResult::WriteFailed;
	}
	if (!Capture(*Save))
	{
		LastError = TEXT("nothing to save: no world or no possessed pawn");
		return ENYCSaveResult::NoPlayer;
	}
	Save->DisplayName = DisplayName;
	if (!UGameplayStatics::SaveGameToSlot(Save, SlotName, 0))
	{
		LastError = FString::Printf(TEXT("could not write slot %s"), *SlotName);
		return ENYCSaveResult::WriteFailed;
	}
	UE_LOG(LogNYCSim, Log, TEXT("saved '%s' at NYC_TM %s"), *SlotName, *Save->PlayerNycTm.ToString());
	return ENYCSaveResult::Ok;
}

ENYCSaveResult UNYCSaveSubsystem::LoadFromSlot(const FString& SlotName)
{
	LastError.Reset();
	if (!UGameplayStatics::DoesSaveGameExist(SlotName, 0))
	{
		LastError = FString::Printf(TEXT("slot %s is empty"), *SlotName);
		return ENYCSaveResult::NoSlot;
	}
	UNYCSaveGame* Save = Cast<UNYCSaveGame>(UGameplayStatics::LoadGameFromSlot(SlotName, 0));
	if (Save == nullptr)
	{
		LastError = FString::Printf(TEXT("slot %s could not be read"), *SlotName);
		return ENYCSaveResult::ReadFailed;
	}
	if (Save->SaveVersion > UNYCSaveGame::CurrentVersion)
	{
		// Refused rather than guessed at: a field whose meaning changed would be read as the old one.
		LastError = FString::Printf(TEXT("slot %s is version %d; this build reads %d"),
			*SlotName, Save->SaveVersion, UNYCSaveGame::CurrentVersion);
		return ENYCSaveResult::VersionTooNew;
	}
	if (!Apply(*Save))
	{
		return ENYCSaveResult::NoPlayer;
	}
	UE_LOG(LogNYCSim, Log, TEXT("loaded '%s'"), *SlotName);
	return ENYCSaveResult::Ok;
}

bool UNYCSaveSubsystem::DeleteSlot(const FString& SlotName)
{
	return UGameplayStatics::DeleteGameInSlot(SlotName, 0);
}

bool UNYCSaveSubsystem::SlotExists(const FString& SlotName) const
{
	return UGameplayStatics::DoesSaveGameExist(SlotName, 0);
}

TArray<FNYCSaveSlotInfo> UNYCSaveSubsystem::EnumerateSlots() const
{
	TArray<FNYCSaveSlotInfo> Out;
	const FString Commit = BuildCommit();
	TArray<FString> Names;
	Names.Add(QuickSlot);
	for (int32 i = 0; i < NumSlots; ++i)
	{
		Names.Add(SlotNameForIndex(i));
	}
	for (const FString& Name : Names)
	{
		if (!UGameplayStatics::DoesSaveGameExist(Name, 0))
		{
			continue;
		}
		const UNYCSaveGame* Save = Cast<UNYCSaveGame>(UGameplayStatics::LoadGameFromSlot(Name, 0));
		if (Save == nullptr)
		{
			continue;
		}
		Out.Add(Save->ToSlotInfo(Name, Commit));
	}
	Out.Sort([](const FNYCSaveSlotInfo& A, const FNYCSaveSlotInfo& B) { return A.SavedAtUtc > B.SavedAtUtc; });
	return Out;
}
