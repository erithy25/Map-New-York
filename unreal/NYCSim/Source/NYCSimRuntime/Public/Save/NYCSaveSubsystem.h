// Saving and loading, and the one trap in doing either.
//
// **Restoring a position teleports the pawn into tiles that have not streamed in.** The world is
// 2,916 km2 loaded on demand around the player; put the car at Wall Street while the streamer still
// believes it is at Times Square and there is no ground under it, so it falls until it is deleted.
// LoadFromSlot therefore moves the streaming camera first, flushes
// (UNYCTileStreamingSubsystem::FlushStreaming, which the nycsim.Streaming.Flush console command
// already drives), and only then places the pawn and lets physics have it back. Everything else here
// is bookkeeping; that order is the part that matters.
#pragma once

#include "CoreMinimal.h"
#include "Save/NYCSaveGame.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "NYCSaveSubsystem.generated.h"

class APawn;
class UNYCSaveGame;

UENUM(BlueprintType)
enum class ENYCSaveResult : uint8
{
	Ok = 0,
	NoWorld,
	NoPlayer,
	NoSlot,
	WriteFailed,
	ReadFailed,
	/** The slot was written by a newer build; loading it would be guesswork. */
	VersionTooNew,
};

UCLASS()
class NYCSIMRUNTIME_API UNYCSaveSubsystem : public UGameInstanceSubsystem
{
	GENERATED_BODY()

public:
	/** The slot F5/F9 use. Ordinary slots are "Slot0".."Slot9". */
	static const TCHAR* QuickSlot;
	/** How many numbered slots the menu offers. */
	static constexpr int32 NumSlots = 10;

	virtual void Initialize(FSubsystemCollectionBase& Collection) override;

	UFUNCTION(BlueprintCallable, Category = "NYCSim|Save")
	ENYCSaveResult SaveToSlot(const FString& SlotName, const FString& DisplayName);

	UFUNCTION(BlueprintCallable, Category = "NYCSim|Save")
	ENYCSaveResult LoadFromSlot(const FString& SlotName);

	UFUNCTION(BlueprintCallable, Category = "NYCSim|Save")
	bool DeleteSlot(const FString& SlotName);

	UFUNCTION(BlueprintPure, Category = "NYCSim|Save")
	bool SlotExists(const FString& SlotName) const;

	/** Every slot the menu can show, newest first. Cheap: it reads the header fields only. */
	UFUNCTION(BlueprintCallable, Category = "NYCSim|Save")
	TArray<FNYCSaveSlotInfo> EnumerateSlots() const;

	UFUNCTION(BlueprintCallable, Category = "NYCSim|Save")
	ENYCSaveResult QuickSave() { return SaveToSlot(QuickSlot, TEXT("Quick save")); }

	UFUNCTION(BlueprintCallable, Category = "NYCSim|Save")
	ENYCSaveResult QuickLoad() { return LoadFromSlot(QuickSlot); }

	/** Text for the last failure, for the menu to show instead of a silent no-op. */
	UFUNCTION(BlueprintPure, Category = "NYCSim|Save")
	FString GetLastError() const { return LastError; }

	/** Fills a save object from the running world. Public so a test can call it without a slot. */
	bool Capture(UNYCSaveGame& Save) const;

	/** Applies a save object to the running world, streaming first. */
	bool Apply(const UNYCSaveGame& Save);

	static FString SlotNameForIndex(int32 Index) { return FString::Printf(TEXT("Slot%d"), Index); }

private:
	APawn* PlayerPawn() const;

	FString LastError;
};
