// Headless world import: `UnrealEditor-Cmd NYCSim.uproject -run=NYCImport [options]`.
//
// Stages (all of them by default, in this order):
//   validate  read data/processed/unreal_manifest.json, check every source file exists and every
//             import-settings id is known; report counts per kind.
//   stage     copy the raw_copy / json_copy entries (crs.json, runtime/*.nycb, live/*.json,
//             unreal_water.json) and the per-tile water masks into Content/NYCSim/{Runtime,Live}.
//   assets    Content/Python/import_assets.py  — glTF meshes, textures, fonts, materials, MPC_Weather.
//   levels    Content/Python/build_levels.py   — the NYC map, per-tile L0/L1 levels, skyline levels,
//                                                landscapes (through UNYCTerrainImporter) and actors.
//   verify    re-read crs.json and tiles.nycb from the staged content and check the level packages
//             the streaming subsystem will ask for actually exist.
//
// Options: -manifest=<path> -stages=a,b,c -tiles=t_-3_7,t_-3_8 -maxtiles=N -content=<dir> -nopython
//          -continueonerror -dryrun
// Exit code 0 only when every requested stage succeeded.
#pragma once

#include "CoreMinimal.h"
#include "Commandlets/Commandlet.h"

#include "NYCImportCommandlet.generated.h"

UCLASS()
class NYCSIMEDITOR_API UNYCImportCommandlet : public UCommandlet
{
	GENERATED_BODY()

public:
	UNYCImportCommandlet();

	virtual int32 Main(const FString& Params) override;

private:
	struct FOptions
	{
		FString ManifestPath;
		FString ContentDir;
		TArray<FString> Stages;
		TArray<FString> Tiles;
		int32 MaxTiles = 0;
		bool bPython = true;
		bool bContinueOnError = false;
		bool bDryRun = false;
	};

	bool ParseOptions(const FString& Params, FOptions& Out) const;
	bool StageValidate(const FOptions& Options, TSharedPtr<class FJsonObject>& OutManifest);
	bool StageCopy(const FOptions& Options, const TSharedPtr<class FJsonObject>& Manifest, int32& OutCopied);
	bool StageRunPython(const FOptions& Options, const FString& ScriptName, const FString& Arguments);
	bool StageVerify(const FOptions& Options, const TSharedPtr<class FJsonObject>& Manifest);

	/** Absolute path of a manifest `src` entry (they are repo-relative). */
	static FString ResolveSource(const FString& RepoRoot, const FString& Src);
	/** Content path "/Game/NYCSim/Runtime/crs.json" -> "<Project>/Content/NYCSim/Runtime/crs.json". */
	static FString ContentPathToFile(const FString& ContentDir, const FString& Dst);

	FString RepoRoot;
	int32 Errors = 0;
	int32 Warnings = 0;
};
