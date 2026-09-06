// Bridge between nycsim_core's host hooks (log sink, fatal handler) and Unreal (UE_LOG, checkf).
// Installed once by UNYCSimGameInstance::Init (and by the editor module for commandlets).
// This is the only place in the runtime that touches nycsim/Config.h and nycsim/util/Log.h directly.
#pragma once

#include "CoreMinimal.h"

namespace NYCCoreBridge
{
	/** Routes nycsim::logMessage to LogNYCSimCore and nycsim::fatalError to UE's fatal log. Idempotent. */
	NYCSIMRUNTIME_API void Install();

	/** Restores the core's default handlers (stderr / abort). Safe to call without Install(). */
	NYCSIMRUNTIME_API void Uninstall();

	NYCSIMRUNTIME_API bool IsInstalled();

	/** Core library version string "major.minor.patch" from nycsim/Config.h. */
	NYCSIMRUNTIME_API FString CoreVersion();
}
