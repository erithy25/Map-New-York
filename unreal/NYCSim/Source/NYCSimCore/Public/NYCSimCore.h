// NYCSimCore module interface.
//
// The module exposes <repo>/core/include (namespace nycsim) to every dependent module. UE code must not include
// core headers directly; use the adapters in NYCSimRuntime/Private/CoreAdapter so API drift is contained there.
#pragma once

#include "CoreMinimal.h"
#include "Modules/ModuleInterface.h"
#include "Logging/LogMacros.h"

NYCSIMCORE_API DECLARE_LOG_CATEGORY_EXTERN(LogNYCSimCore, Log, All);

class FNYCSimCoreModule : public IModuleInterface
{
public:
	virtual void StartupModule() override;
	virtual void ShutdownModule() override;
};
