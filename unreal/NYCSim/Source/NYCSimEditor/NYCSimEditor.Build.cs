// NYCSimEditor: editor-only module. Import commandlet (UNYCImportCommandlet), Landscape import from the pipeline's
// 16-bit PNG heightmaps, water body import from unreal_water.json, editor utilities exposed to Content/Python.
using UnrealBuildTool;

public class NYCSimEditor : ModuleRules
{
	public NYCSimEditor(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
		IncludeOrderVersion = EngineIncludeOrderVersion.Unreal5_4;
		CppStandard = CppStandardVersion.Cpp20;
		bEnableExceptions = false;
		bUseRTTI = false;

		PublicDependencyModuleNames.AddRange(new string[]
		{
			"Core",
			"CoreUObject",
			"Engine",
			"NYCSimCore",
			"NYCSimRuntime",
		});

		PrivateDependencyModuleNames.AddRange(new string[]
		{
			"UnrealEd",
			"EditorFramework",
			"EditorSubsystem",
			"EditorScriptingUtilities",
			"AssetTools",
			"AssetRegistry",
			"ContentBrowser",
			"Landscape",
			"LandscapeEditor",
			"Foliage",
			"Json",
			"JsonUtilities",
			"ImageWrapper",
			"ImageCore",
			"RenderCore",
			"RHI",
			"Slate",
			"SlateCore",
			"InputCore",
			"EnhancedInput",
			"Projects",
			"MaterialEditor",
			"Niagara",
			"NiagaraEditor",
			"MeshDescription",
			"StaticMeshDescription",
			"MeshConversion",
			"GeometryCore",
			"PythonScriptPlugin",
			"DeveloperSettings",
			"LevelEditor",
			"MainFrame",
		});

		PublicDefinitions.Add("NYCSIM_EDITOR=1");
	}
}
