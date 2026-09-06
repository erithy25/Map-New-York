// Default game mode. Blueprint-free: pawn/controller/HUD classes are resolved from UNYCSimWorldSettings so the
// vehicle pawn (owned by Unreal agent 2) is referenced by path, not linked. When it cannot be resolved the player
// gets a fly camera (ADefaultPawn) so the world remains explorable.
#pragma once

#include "CoreMinimal.h"
#include "GameFramework/GameModeBase.h"
#include "NYCSimGameMode.generated.h"

UCLASS()
class NYCSIMRUNTIME_API ANYCSimGameMode : public AGameModeBase
{
	GENERATED_BODY()

public:
	ANYCSimGameMode();

	virtual void InitGame(const FString& MapName, const FString& Options, FString& ErrorMessage) override;
	virtual AActor* ChoosePlayerStart_Implementation(AController* Player) override;
	virtual UClass* GetDefaultPawnClassForController_Implementation(AController* InController) override;

private:
	/** Resolved on InitGame from UNYCSimWorldSettings::DefaultPawnClassPath (nullptr -> ADefaultPawn). */
	UPROPERTY(Transient)
	TSubclassOf<APawn> ResolvedPawnClass;

	/** Spawned when the level has no APlayerStart; placed at the configured NYC_TM position. */
	UPROPERTY(Transient)
	TObjectPtr<AActor> FallbackStart;
};
