#include "World/NYCSimGameInstance.h"
#include "CoreAdapter/NYCCoreBridge.h"
#include "NYCSimRuntime.h"

void UNYCSimGameInstance::Init()
{
	Super::Init();
	NYCCoreBridge::Install();
	UE_LOG(LogNYCSim, Log, TEXT("NYCSim game instance initialised (core %s)"), *NYCCoreBridge::CoreVersion());
}

void UNYCSimGameInstance::Shutdown()
{
	Super::Shutdown();
}
