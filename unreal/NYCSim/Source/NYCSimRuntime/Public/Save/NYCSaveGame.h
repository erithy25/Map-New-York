// What a saved game is.
//
// Positions are stored in **NYC_TM metres**, not in Unreal centimetres. The project's coordinate
// contract (ARCHITECTURE §2) is UE.X = east*100, UE.Y = -north*100, and the world is 50 km across on
// large-world coordinates, so a save written in engine units is tied to wherever the world origin
// happened to be when it was written. NYC_TM is the city's own frame and does not move; a save from
// this build opens in the next one, and a position in it can be read by a human against a map.
//
// The save also records the build it came from. A save is data about a world, and if the world
// changes underneath it the honest thing is to be able to say so rather than to load a position into
// a city that no longer has a street there.
#pragma once

#include "CoreMinimal.h"
#include "GameFramework/SaveGame.h"
#include "NYCSaveGame.generated.h"

/** One entry in the slot list, cheap enough to read for every slot when drawing the load screen. */
USTRUCT(BlueprintType)
struct NYCSIMRUNTIME_API FNYCSaveSlotInfo
{
	GENERATED_BODY()

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Save")
	FString SlotName;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Save")
	FString DisplayName;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Save")
	FDateTime SavedAtUtc = FDateTime();

	/** Street the player was on, for the slot card. Empty when the GPS could not name one. */
	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Save")
	FString Street;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Save")
	float OdometerKm = 0.f;

	/** In-world local time when it was saved. */
	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Save")
	FDateTime SimLocalTime = FDateTime();

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Save")
	bool bFromThisBuild = true;
};

UCLASS()
class NYCSIMRUNTIME_API UNYCSaveGame : public USaveGame
{
	GENERATED_BODY()

public:
	/** Bumped when a field's meaning changes. A save from a newer version is refused, not guessed at. */
	static constexpr int32 CurrentVersion = 1;

	UPROPERTY(BlueprintReadWrite, Category = "NYCSim|Save")
	int32 SaveVersion = CurrentVersion;

	/** The commit the save was written by, so a slot from another world can be labelled as such. */
	UPROPERTY(BlueprintReadWrite, Category = "NYCSim|Save")
	FString GitCommit;

	UPROPERTY(BlueprintReadWrite, Category = "NYCSim|Save")
	FString DisplayName;

	UPROPERTY(BlueprintReadWrite, Category = "NYCSim|Save")
	FDateTime SavedAtUtc = FDateTime();

	// ---- where ----------------------------------------------------------------------------------
	/** Player position, NYC_TM metres (east, north, up). */
	UPROPERTY(BlueprintReadWrite, Category = "NYCSim|Save")
	FVector PlayerNycTm = FVector::ZeroVector;

	/** Compass heading of the player's facing, degrees, 0 = north. */
	UPROPERTY(BlueprintReadWrite, Category = "NYCSim|Save")
	float PlayerHeadingDeg = 0.f;

	UPROPERTY(BlueprintReadWrite, Category = "NYCSim|Save")
	bool bInVehicle = true;

	UPROPERTY(BlueprintReadWrite, Category = "NYCSim|Save")
	FString VehicleId;

	/** Vehicle position, NYC_TM metres. Equal to the player's while they are in it. */
	UPROPERTY(BlueprintReadWrite, Category = "NYCSim|Save")
	FVector VehicleNycTm = FVector::ZeroVector;

	UPROPERTY(BlueprintReadWrite, Category = "NYCSim|Save")
	FRotator VehicleRotation = FRotator::ZeroRotator;

	/** Metres per second, in NYC_TM axes. Restored so a save mid-corner does not stop the car dead. */
	UPROPERTY(BlueprintReadWrite, Category = "NYCSim|Save")
	FVector VehicleVelocityNycTm = FVector::ZeroVector;

	// ---- the car's own state --------------------------------------------------------------------
	UPROPERTY(BlueprintReadWrite, Category = "NYCSim|Save")
	float OdometerKm = 0.f;

	UPROPERTY(BlueprintReadWrite, Category = "NYCSim|Save")
	float FuelLitres = 0.f;

	/** ENYCHeadlightMode as a byte, so the save does not depend on the enum's header. */
	UPROPERTY(BlueprintReadWrite, Category = "NYCSim|Save")
	uint8 HeadlightMode = 0;

	UPROPERTY(BlueprintReadWrite, Category = "NYCSim|Save")
	bool bHazards = false;

	UPROPERTY(BlueprintReadWrite, Category = "NYCSim|Save")
	uint8 WiperMode = 0;

	/** One 0..1 value per DMG_ region, in the order of NYCVehicleMorphs. */
	UPROPERTY(BlueprintReadWrite, Category = "NYCSim|Save")
	TArray<float> DamagePerRegion;

	// ---- the world ------------------------------------------------------------------------------
	UPROPERTY(BlueprintReadWrite, Category = "NYCSim|Save")
	FString RadioStationId;

	/** Simulated UTC. The sky, the traffic's rush hour and the shop lights all follow it. */
	UPROPERTY(BlueprintReadWrite, Category = "NYCSim|Save")
	FDateTime SimUtc = FDateTime();

	UPROPERTY(BlueprintReadWrite, Category = "NYCSim|Save")
	bool bUseRealTime = true;

	UPROPERTY(BlueprintReadWrite, Category = "NYCSim|Save")
	float TimeScale = 1.f;

	UPROPERTY(BlueprintReadWrite, Category = "NYCSim|Save")
	bool bRouteActive = false;

	UPROPERTY(BlueprintReadWrite, Category = "NYCSim|Save")
	FVector RouteDestinationNycTm = FVector::ZeroVector;

	/** Street name at the save position, for the slot card. */
	UPROPERTY(BlueprintReadWrite, Category = "NYCSim|Save")
	FString Street;

	UPROPERTY(BlueprintReadWrite, Category = "NYCSim|Save")
	FDateTime SimLocalTime = FDateTime();

	FNYCSaveSlotInfo ToSlotInfo(const FString& InSlotName, const FString& BuildCommit) const;
};
