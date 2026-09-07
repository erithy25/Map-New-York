#include "CoreAdapter/NYCCoreBridge.h"
#include "NYCSimCore.h"

#include "nycsim/Config.h"
#include "nycsim/util/Log.h"

namespace
{
	class FUELogSink final : public nycsim::ILogSink
	{
	public:
		void write(nycsim::LogLevel Level, const char* Module, const char* Message) noexcept override
		{
			const FString Text = FString::Printf(TEXT("[%s] %s"), UTF8_TO_TCHAR(Module ? Module : ""), UTF8_TO_TCHAR(Message ? Message : ""));
			switch (Level)
			{
			case nycsim::LogLevel::Trace:
				UE_LOG(LogNYCSimCore, VeryVerbose, TEXT("%s"), *Text);
				break;
			case nycsim::LogLevel::Debug:
				UE_LOG(LogNYCSimCore, Verbose, TEXT("%s"), *Text);
				break;
			case nycsim::LogLevel::Info:
				UE_LOG(LogNYCSimCore, Log, TEXT("%s"), *Text);
				break;
			case nycsim::LogLevel::Warn:
				UE_LOG(LogNYCSimCore, Warning, TEXT("%s"), *Text);
				break;
			case nycsim::LogLevel::Error:
				UE_LOG(LogNYCSimCore, Error, TEXT("%s"), *Text);
				break;
			case nycsim::LogLevel::Off:
			default:
				break;
			}
		}
	};

	// Constant-initialised storage; no static constructor runs (module load order safe).
	FUELogSink* GSink = nullptr;
	bool GInstalled = false;

	[[noreturn]] void UEFatalHandler(const char* Message, const char* File, int Line)
	{
		// UE_LOG Fatal never returns (it crashes with a callstack), which satisfies the core's contract that the
		// handler must not return.
		UE_LOG(LogNYCSimCore, Fatal, TEXT("nycsim_core fatal: %s (%s:%d)"), UTF8_TO_TCHAR(Message ? Message : ""), UTF8_TO_TCHAR(File ? File : ""), Line);
		// Unreachable in practice; keeps the [[noreturn]] contract explicit for every compiler.
		for (;;)
		{
			FPlatformMisc::RequestExit(true);
		}
	}
}

void NYCCoreBridge::Install()
{
	if (GInstalled)
	{
		return;
	}
	if (!GSink)
	{
		GSink = new FUELogSink();
	}
	nycsim::setLogSink(GSink);
	nycsim::setLogLevel(UE_BUILD_SHIPPING ? nycsim::LogLevel::Warn : nycsim::LogLevel::Info);
	nycsim::setFatalHandler(&UEFatalHandler);
	GInstalled = true;
	UE_LOG(LogNYCSimCore, Log, TEXT("nycsim_core %s bound to UE logging"), *CoreVersion());
}

void NYCCoreBridge::Uninstall()
{
	if (!GInstalled)
	{
		return;
	}
	nycsim::setLogSink(nullptr);
	nycsim::setFatalHandler(nullptr);
	delete GSink;
	GSink = nullptr;
	GInstalled = false;
}

bool NYCCoreBridge::IsInstalled()
{
	return GInstalled;
}

FString NYCCoreBridge::CoreVersion()
{
	return FString::Printf(TEXT("%d.%d.%d"), NYCSIM_CORE_VERSION_MAJOR, NYCSIM_CORE_VERSION_MINOR, NYCSIM_CORE_VERSION_PATCH);
}
