// Game instance: binds the core library's log/fatal hooks to UE before any world exists.
#pragma once

#include "CoreMinimal.h"
#include "Engine/GameInstance.h"
#include "NYCSimGameInstance.generated.h"

UCLASS()
class NYCSIMRUNTIME_API UNYCSimGameInstance : public UGameInstance
{
	GENERATED_BODY()

public:
	virtual void Init() override;
	virtual void Shutdown() override;
};
