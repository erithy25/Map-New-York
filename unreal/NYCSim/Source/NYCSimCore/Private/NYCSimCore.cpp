// NYCSimCore module implementation. This is the only translation unit in the module that includes UE headers.
#include "NYCSimCore.h"
#include "Modules/ModuleManager.h"

DEFINE_LOG_CATEGORY(LogNYCSimCore);

void FNYCSimCoreModule::StartupModule()
{
	UE_LOG(LogNYCSimCore, Log, TEXT("NYCSimCore (engine-agnostic core library) loaded"));
}

void FNYCSimCoreModule::ShutdownModule()
{
}

IMPLEMENT_MODULE(FNYCSimCoreModule, NYCSimCore);
