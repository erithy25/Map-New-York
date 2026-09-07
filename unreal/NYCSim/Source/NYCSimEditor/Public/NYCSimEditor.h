// NYCSimEditor module interface.
#pragma once

#include "CoreMinimal.h"
#include "Modules/ModuleInterface.h"
#include "Logging/LogMacros.h"

NYCSIMEDITOR_API DECLARE_LOG_CATEGORY_EXTERN(LogNYCSimEditor, Log, All);

class FNYCSimEditorModule : public IModuleInterface
{
public:
	virtual void StartupModule() override;
	virtual void ShutdownModule() override;
};
