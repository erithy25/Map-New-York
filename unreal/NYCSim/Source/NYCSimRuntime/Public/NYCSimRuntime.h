// NYCSimRuntime module interface. Primary game module of NYCSim.
#pragma once

#include "CoreMinimal.h"
#include "Modules/ModuleInterface.h"
#include "Logging/LogMacros.h"

NYCSIMRUNTIME_API DECLARE_LOG_CATEGORY_EXTERN(LogNYCSim, Log, All);

class FNYCSimRuntimeModule : public IModuleInterface
{
public:
	virtual void StartupModule() override;
	virtual void ShutdownModule() override;
	virtual bool IsGameModule() const override { return true; }
};
