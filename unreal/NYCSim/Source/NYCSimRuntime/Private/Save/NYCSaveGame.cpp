#include "Save/NYCSaveGame.h"

FNYCSaveSlotInfo UNYCSaveGame::ToSlotInfo(const FString& InSlotName, const FString& BuildCommit) const
{
	FNYCSaveSlotInfo Info;
	Info.SlotName = InSlotName;
	Info.DisplayName = DisplayName.IsEmpty() ? InSlotName : DisplayName;
	Info.SavedAtUtc = SavedAtUtc;
	Info.Street = Street;
	Info.OdometerKm = OdometerKm;
	Info.SimLocalTime = SimLocalTime;
	// An empty commit on either side means "unknown", which is not the same as "different": a build
	// that cannot name itself must not label every existing save as foreign.
	Info.bFromThisBuild = GitCommit.IsEmpty() || BuildCommit.IsEmpty() || GitCommit == BuildCommit;
	return Info;
}
