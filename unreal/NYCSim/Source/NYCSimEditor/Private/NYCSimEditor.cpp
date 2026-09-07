// NYCSimEditor module implementation.
#include "NYCSimEditor.h"
#include "Modules/ModuleManager.h"

DEFINE_LOG_CATEGORY(LogNYCSimEditor);

void FNYCSimEditorModule::StartupModule()
{
	UE_LOG(LogNYCSimEditor, Log, TEXT("NYCSimEditor module started (import commandlet: -run=NYCImport)"));
}

void FNYCSimEditorModule::ShutdownModule()
{
}

IMPLEMENT_MODULE(FNYCSimEditorModule, NYCSimEditor);
