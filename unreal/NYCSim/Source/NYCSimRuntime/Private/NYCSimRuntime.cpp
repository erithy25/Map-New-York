// NYCSimRuntime module implementation.
#include "NYCSimRuntime.h"
#include "Modules/ModuleManager.h"

DEFINE_LOG_CATEGORY(LogNYCSim);

void FNYCSimRuntimeModule::StartupModule()
{
	UE_LOG(LogNYCSim, Log, TEXT("NYCSimRuntime module started"));
}

void FNYCSimRuntimeModule::ShutdownModule()
{
	UE_LOG(LogNYCSim, Log, TEXT("NYCSimRuntime module shut down"));
}

IMPLEMENT_PRIMARY_GAME_MODULE(FNYCSimRuntimeModule, NYCSimRuntime, "NYCSim");
