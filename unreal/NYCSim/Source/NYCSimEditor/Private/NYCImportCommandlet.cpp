#include "NYCImportCommandlet.h"

#include "NYCSimEditor.h"

#include "CoreAdapter/NYCGeo.h"
#include "CoreAdapter/NYCNycb.h"
#include "World/NYCSimWorldSettings.h"

#include "Dom/JsonObject.h"
#include "HAL/FileManager.h"
#include "HAL/PlatformFileManager.h"
#include "IPythonScriptPlugin.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/PackageName.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"

UNYCImportCommandlet::UNYCImportCommandlet()
{
	IsClient = false;
	IsEditor = true;
	IsServer = false;
	LogToConsole = true;
	ShowErrorCount = true;
	HelpDescription = TEXT("Imports the NYCSim world from data/processed/unreal_manifest.json (headless).");
	HelpUsage = TEXT("-run=NYCImport [-manifest=<file>] [-stages=validate,stage,assets,levels,verify] ")
		TEXT("[-tiles=t_-3_7,...] [-maxtiles=N] [-content=<dir>] [-nopython] [-continueonerror] [-dryrun]");
}

// ------------------------------------------------------------------------------------------------- options

bool UNYCImportCommandlet::ParseOptions(const FString& Params, FOptions& Out) const
{
	TArray<FString> Tokens;
	TArray<FString> Switches;
	TMap<FString, FString> Values;
	UCommandlet::ParseCommandLine(*Params, Tokens, Switches, Values);

	// <Project>/Content -> <Project> -> unreal/NYCSim -> unreal -> repo root
	const FString ProjectDir = FPaths::ConvertRelativePathToFull(FPaths::ProjectDir());
	const FString DefaultRepoRoot = FPaths::ConvertRelativePathToFull(FPaths::Combine(ProjectDir, TEXT("../..")));

	Out.ContentDir = Values.Contains(TEXT("content"))
		? FPaths::ConvertRelativePathToFull(Values[TEXT("content")])
		: FPaths::ConvertRelativePathToFull(FPaths::ProjectContentDir());
	Out.ManifestPath = Values.Contains(TEXT("manifest"))
		? FPaths::ConvertRelativePathToFull(Values[TEXT("manifest")])
		: FPaths::Combine(DefaultRepoRoot, TEXT("data/processed/unreal_manifest.json"));

	if (Values.Contains(TEXT("stages")))
	{
		Values[TEXT("stages")].ParseIntoArray(Out.Stages, TEXT(","), true);
		for (FString& Stage : Out.Stages)
		{
			Stage.TrimStartAndEndInline();
			Stage.ToLowerInline();
		}
	}
	else
	{
		Out.Stages = {TEXT("validate"), TEXT("stage"), TEXT("assets"), TEXT("levels"), TEXT("verify")};
	}
	if (Values.Contains(TEXT("tiles")))
	{
		Values[TEXT("tiles")].ParseIntoArray(Out.Tiles, TEXT(","), true);
		for (FString& Tile : Out.Tiles)
		{
			Tile.TrimStartAndEndInline();
		}
	}
	if (Values.Contains(TEXT("maxtiles")))
	{
		Out.MaxTiles = FCString::Atoi(*Values[TEXT("maxtiles")]);
	}
	Out.bPython = !Switches.Contains(TEXT("nopython"));
	Out.bContinueOnError = Switches.Contains(TEXT("continueonerror"));
	Out.bDryRun = Switches.Contains(TEXT("dryrun"));
	return true;
}

FString UNYCImportCommandlet::ResolveSource(const FString& InRepoRoot, const FString& Src)
{
	if (FPaths::IsRelative(Src))
	{
		return FPaths::ConvertRelativePathToFull(FPaths::Combine(InRepoRoot, Src));
	}
	return FPaths::ConvertRelativePathToFull(Src);
}

FString UNYCImportCommandlet::ContentPathToFile(const FString& ContentDir, const FString& Dst)
{
	FString Relative = Dst;
	if (Relative.StartsWith(TEXT("/Game/")))
	{
		Relative = Relative.RightChop(6);
	}
	return FPaths::Combine(ContentDir, Relative);
}

// ------------------------------------------------------------------------------------------------- stages

bool UNYCImportCommandlet::StageValidate(const FOptions& Options, TSharedPtr<FJsonObject>& OutManifest)
{
	FString Text;
	if (!FFileHelper::LoadFileToString(Text, *Options.ManifestPath))
	{
		UE_LOG(LogNYCSimEditor, Error, TEXT("manifest %s cannot be read"), *Options.ManifestPath);
		++Errors;
		return false;
	}
	const TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(Text);
	if (!FJsonSerializer::Deserialize(Reader, OutManifest) || !OutManifest.IsValid())
	{
		UE_LOG(LogNYCSimEditor, Error, TEXT("manifest %s is not valid JSON"), *Options.ManifestPath);
		++Errors;
		return false;
	}
	FString Schema;
	OutManifest->TryGetStringField(TEXT("schema"), Schema);
	if (Schema != TEXT("unreal_manifest/1"))
	{
		UE_LOG(LogNYCSimEditor, Error, TEXT("manifest schema '%s' unsupported (expected unreal_manifest/1)"), *Schema);
		++Errors;
		return false;
	}
	OutManifest->TryGetStringField(TEXT("repo_root"), RepoRoot);
	if (RepoRoot.IsEmpty() || !IFileManager::Get().DirectoryExists(*RepoRoot))
	{
		// The manifest may have been generated elsewhere; fall back to the path relative to the project.
		RepoRoot = FPaths::ConvertRelativePathToFull(FPaths::Combine(FPaths::ProjectDir(), TEXT("../..")));
		UE_LOG(LogNYCSimEditor, Warning, TEXT("manifest repo_root not usable; using %s"), *RepoRoot);
		++Warnings;
	}

	const TArray<TSharedPtr<FJsonValue>>* Entries = nullptr;
	if (!OutManifest->TryGetArrayField(TEXT("entries"), Entries) || !Entries)
	{
		UE_LOG(LogNYCSimEditor, Error, TEXT("manifest has no entries array"));
		++Errors;
		return false;
	}
	const TSharedPtr<FJsonObject>* SettingsObject = nullptr;
	OutManifest->TryGetObjectField(TEXT("import_settings"), SettingsObject);

	TMap<FString, int32> ByKind;
	int32 Missing = 0;
	for (const TSharedPtr<FJsonValue>& Value : *Entries)
	{
		const TSharedPtr<FJsonObject>* Entry = nullptr;
		if (!Value.IsValid() || !Value->TryGetObject(Entry) || !Entry)
		{
			continue;
		}
		FString Kind, Src, Settings;
		(*Entry)->TryGetStringField(TEXT("kind"), Kind);
		(*Entry)->TryGetStringField(TEXT("src"), Src);
		(*Entry)->TryGetStringField(TEXT("import_settings"), Settings);
		ByKind.FindOrAdd(Kind)++;
		if (SettingsObject && SettingsObject->IsValid() && !(*SettingsObject)->HasField(Settings))
		{
			UE_LOG(LogNYCSimEditor, Error, TEXT("entry %s: unknown import_settings id '%s'"), *Src, *Settings);
			++Errors;
		}
		const FString Absolute = ResolveSource(RepoRoot, Src);
		if (!IFileManager::Get().FileExists(*Absolute))
		{
			UE_LOG(LogNYCSimEditor, Error, TEXT("entry source missing: %s"), *Absolute);
			++Missing;
			++Errors;
		}
	}
	FString Summary;
	for (const TPair<FString, int32>& Pair : ByKind)
	{
		Summary += FString::Printf(TEXT("%s=%d "), *Pair.Key, Pair.Value);
	}
	UE_LOG(LogNYCSimEditor, Display, TEXT("manifest %s: %d entries (%s), %d missing sources"),
		*Options.ManifestPath, Entries->Num(), *Summary.TrimEnd(), Missing);

	const TArray<TSharedPtr<FJsonValue>>* ManifestWarnings = nullptr;
	if (OutManifest->TryGetArrayField(TEXT("warnings"), ManifestWarnings) && ManifestWarnings)
	{
		for (const TSharedPtr<FJsonValue>& W : *ManifestWarnings)
		{
			FString Message;
			if (W.IsValid() && W->TryGetString(Message))
			{
				UE_LOG(LogNYCSimEditor, Warning, TEXT("manifest warning: %s"), *Message);
				++Warnings;
			}
		}
	}
	return Missing == 0;
}

bool UNYCImportCommandlet::StageCopy(const FOptions& Options, const TSharedPtr<FJsonObject>& Manifest, int32& OutCopied)
{
	OutCopied = 0;
	if (!Manifest.IsValid())
	{
		return false;
	}
	const TArray<TSharedPtr<FJsonValue>>* Entries = nullptr;
	if (!Manifest->TryGetArrayField(TEXT("entries"), Entries) || !Entries)
	{
		return false;
	}
	IPlatformFile& File = FPlatformFileManager::Get().GetPlatformFile();
	bool bOk = true;
	for (const TSharedPtr<FJsonValue>& Value : *Entries)
	{
		const TSharedPtr<FJsonObject>* Entry = nullptr;
		if (!Value.IsValid() || !Value->TryGetObject(Entry) || !Entry)
		{
			continue;
		}
		FString Kind, Src, Dst, Settings, Tile;
		(*Entry)->TryGetStringField(TEXT("kind"), Kind);
		(*Entry)->TryGetStringField(TEXT("src"), Src);
		(*Entry)->TryGetStringField(TEXT("dst"), Dst);
		(*Entry)->TryGetStringField(TEXT("import_settings"), Settings);
		(*Entry)->TryGetStringField(TEXT("tile"), Tile);

		FString Target;
		if (Settings == TEXT("raw_copy") || Settings == TEXT("json_copy"))
		{
			Target = ContentPathToFile(Options.ContentDir, Dst);
		}
		else if (Kind == TEXT("water_mask") && !Tile.IsEmpty())
		{
			// The runtime reads the mask pixels from disk (ANYCWaterActor), independent of the imported texture.
			Target = FPaths::Combine(Options.ContentDir, TEXT("NYCSim/Runtime/water_masks"), Tile + TEXT(".png"));
		}
		else
		{
			continue;
		}
		if (!Options.Tiles.IsEmpty() && !Tile.IsEmpty() && !Options.Tiles.Contains(Tile))
		{
			continue;
		}
		const FString Source = ResolveSource(RepoRoot, Src);
		if (Options.bDryRun)
		{
			UE_LOG(LogNYCSimEditor, Display, TEXT("[dry run] copy %s -> %s"), *Source, *Target);
			++OutCopied;
			continue;
		}
		File.CreateDirectoryTree(*FPaths::GetPath(Target));
		if (!File.CopyFile(*Target, *Source))
		{
			UE_LOG(LogNYCSimEditor, Error, TEXT("copy failed: %s -> %s"), *Source, *Target);
			++Errors;
			bOk = false;
			continue;
		}
		++OutCopied;
	}
	UE_LOG(LogNYCSimEditor, Display, TEXT("staged %d files under %s"), OutCopied, *Options.ContentDir);
	return bOk;
}

bool UNYCImportCommandlet::StageRunPython(const FOptions& Options, const FString& ScriptName, const FString& Arguments)
{
	if (!Options.bPython)
	{
		UE_LOG(LogNYCSimEditor, Display, TEXT("-nopython: skipping %s"), *ScriptName);
		return true;
	}
	IPythonScriptPlugin* Python = IPythonScriptPlugin::Get();
	if (!Python || !Python->IsPythonAvailable())
	{
		UE_LOG(LogNYCSimEditor, Error,
			TEXT("the Python script plugin is not available; enable PythonScriptPlugin (it is in NYCSim.uproject) ")
			TEXT("or pass -nopython"));
		++Errors;
		return false;
	}
	const FString ScriptPath = FPaths::Combine(FPaths::ProjectContentDir(), TEXT("Python"), ScriptName);
	if (!IFileManager::Get().FileExists(*ScriptPath))
	{
		UE_LOG(LogNYCSimEditor, Error, TEXT("python script not found: %s"), *ScriptPath);
		++Errors;
		return false;
	}
	FPythonCommandEx Command;
	Command.Command = FString::Printf(TEXT("\"%s\" %s"), *ScriptPath, *Arguments);
	Command.ExecutionMode = EPythonCommandExecutionMode::ExecuteFile;
	Command.Flags |= EPythonCommandFlags::Unattended;
	UE_LOG(LogNYCSimEditor, Display, TEXT("python: %s"), *Command.Command);
	const bool bOk = Python->ExecPythonCommandEx(Command);
	for (const FPythonLogOutputEntry& Entry : Command.LogOutput)
	{
		if (Entry.Type == EPythonLogOutputType::Error)
		{
			UE_LOG(LogNYCSimEditor, Error, TEXT("  %s"), *Entry.Output);
		}
		else
		{
			UE_LOG(LogNYCSimEditor, Display, TEXT("  %s"), *Entry.Output);
		}
	}
	if (!bOk)
	{
		UE_LOG(LogNYCSimEditor, Error, TEXT("%s failed"), *ScriptName);
		++Errors;
	}
	return bOk;
}

bool UNYCImportCommandlet::StageVerify(const FOptions& Options, const TSharedPtr<FJsonObject>& Manifest)
{
	bool bOk = true;

	const FString CrsPath = FPaths::Combine(Options.ContentDir, TEXT("NYCSim/Runtime/crs.json"));
	FString CrsText;
	if (!FFileHelper::LoadFileToString(CrsText, *CrsPath))
	{
		UE_LOG(LogNYCSimEditor, Error, TEXT("verify: %s missing (run the stage step)"), *CrsPath);
		++Errors;
		bOk = false;
	}
	else
	{
		TSharedPtr<FJsonObject> Crs;
		const TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(CrsText);
		FString Proj4;
		if (!FJsonSerializer::Deserialize(Reader, Crs) || !Crs.IsValid() || !Crs->TryGetStringField(TEXT("proj4"), Proj4))
		{
			UE_LOG(LogNYCSimEditor, Error, TEXT("verify: %s is not a crs.json document"), *CrsPath);
			++Errors;
			bOk = false;
		}
		else
		{
			auto Normalise = [](const FString& S)
			{
				TArray<FString> Parts;
				S.ParseIntoArrayWS(Parts);
				Parts.Sort();
				return FString::Join(Parts, TEXT(" "));
			};
			if (Normalise(Proj4) != Normalise(NYCGeo::CoreProj4()))
			{
				UE_LOG(LogNYCSimEditor, Error, TEXT("verify: staged crs.json proj4 differs from the core's"));
				++Errors;
				bOk = false;
			}
		}
	}

	const FString TilesPath = FPaths::Combine(Options.ContentDir, TEXT("NYCSim/Runtime/tiles.nycb"));
	FNYCNycbFile TilesFile;
	FNYCTilesTable Tiles;
	FString Error;
	if (!TilesFile.Load(TilesPath, Error) || !Tiles.Parse(TilesFile, Error))
	{
		UE_LOG(LogNYCSimEditor, Warning,
			TEXT("verify: tiles.nycb not usable (%s). The streaming subsystem needs it; run the pipeline's ")
			TEXT("runtime export stage."), *Error);
		++Warnings;
	}
	else
	{
		const UNYCSimWorldSettings& Settings = UNYCSimWorldSettings::Get();
		int32 Present = 0;
		int32 Absent = 0;
		for (const FNYCTileRecord& Record : Tiles.Records())
		{
			if (!Record.HasLand())
			{
				continue;
			}
			const FString Name = NYCGeo::TileAssetName(Record.Tile());
			const FString Package = FString::Printf(TEXT("%s/%s/%s_L0"), *Settings.TileLevelRoot, *Name, *Name);
			if (FPackageName::DoesPackageExist(Package))
			{
				++Present;
			}
			else
			{
				++Absent;
			}
		}
		UE_LOG(LogNYCSimEditor, Display, TEXT("verify: %d tiles with land, %d L0 levels present, %d absent"),
			Tiles.Num(), Present, Absent);
		if (Absent > 0 && Present == 0)
		{
			UE_LOG(LogNYCSimEditor, Warning, TEXT("verify: no per-tile level exists yet; run the levels stage"));
			++Warnings;
		}
	}
	return bOk;
}

// --------------------------------------------------------------------------------------------------- main

int32 UNYCImportCommandlet::Main(const FString& Params)
{
	FOptions Options;
	ParseOptions(Params, Options);
	Errors = 0;
	Warnings = 0;
	const double Start = FPlatformTime::Seconds();

	UE_LOG(LogNYCSimEditor, Display, TEXT("NYCSim import: manifest %s, content %s, stages %s%s"),
		*Options.ManifestPath, *Options.ContentDir, *FString::Join(Options.Stages, TEXT(",")),
		Options.bDryRun ? TEXT(" [dry run]") : TEXT(""));

	TSharedPtr<FJsonObject> Manifest;
	bool bOk = true;

	auto Wants = [&Options](const TCHAR* Stage) { return Options.Stages.Contains(FString(Stage)); };
	auto Continue = [&](bool bStageOk)
	{
		bOk = bOk && bStageOk;
		return bStageOk || Options.bContinueOnError;
	};

	// The manifest is needed by every stage, so it is always read (validate additionally checks the sources).
	TSharedPtr<FJsonObject> Loaded;
	const bool bManifestOk = StageValidate(Options, Loaded);
	Manifest = Loaded;
	if (Wants(TEXT("validate")) && !Continue(bManifestOk))
	{
		UE_LOG(LogNYCSimEditor, Error, TEXT("validate failed; stopping"));
		return 1;
	}

	FString PythonArgs;
	if (!Options.Tiles.IsEmpty())
	{
		PythonArgs += FString::Printf(TEXT(" --tiles %s"), *FString::Join(Options.Tiles, TEXT(",")));
	}
	if (Options.MaxTiles > 0)
	{
		PythonArgs += FString::Printf(TEXT(" --max-tiles %d"), Options.MaxTiles);
	}
	PythonArgs += FString::Printf(TEXT(" --manifest \"%s\""), *Options.ManifestPath);
	if (Options.bDryRun)
	{
		PythonArgs += TEXT(" --dry-run");
	}

	if (Wants(TEXT("stage")))
	{
		int32 Copied = 0;
		if (!Continue(StageCopy(Options, Manifest, Copied)))
		{
			return 1;
		}
	}
	if (Wants(TEXT("assets")) && !Continue(StageRunPython(Options, TEXT("import_assets.py"), PythonArgs)))
	{
		return 1;
	}
	if (Wants(TEXT("levels")) && !Continue(StageRunPython(Options, TEXT("build_levels.py"), PythonArgs)))
	{
		return 1;
	}
	if (Wants(TEXT("world")) && !Continue(StageRunPython(Options, TEXT("import_world.py"), PythonArgs)))
	{
		return 1;
	}
	if (Wants(TEXT("verify")) && !Continue(StageVerify(Options, Manifest)))
	{
		return 1;
	}

	const double Seconds = FPlatformTime::Seconds() - Start;
	UE_LOG(LogNYCSimEditor, Display, TEXT("NYCSim import finished in %.1f s: %d errors, %d warnings"),
		Seconds, Errors, Warnings);
	return (bOk && Errors == 0) ? 0 : 1;
}
