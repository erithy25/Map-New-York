// NYCSimRuntime: primary game module.
//
// Ownership inside this module (both agents keep to their own sub-folders, this file is shared and lists every
// dependency either side needs so nobody has to edit it):
//   Unreal agent 1: Public/World, Public/Streaming, Public/Sky, Public/Weather, Public/CoreAdapter and the matching
//                   Private/ folders (world subsystem, tile streaming, terrain/water, sky/time, weather, core adapters).
//   Unreal agent 2: Public/Vehicle, Public/Character, Public/Traffic, Public/UI, Public/Audio, Public/Cameras, Public/GPS
//                   and the matching Private/ folders.
using UnrealBuildTool;

public class NYCSimRuntime : ModuleRules
{
	public NYCSimRuntime(ReadOnlyTargetRules Target) : base(Target)
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
			"InputCore",
			"EnhancedInput",
			"NYCSimCore",
			// world / streaming / terrain / water / sky / weather (agent 1)
			"Landscape",
			"Niagara",
			"NiagaraCore",
			"HTTP",
			"Json",
			"JsonUtilities",
			"RenderCore",
			"RHI",
			"DeveloperSettings",
			"Projects",
			"GeometryCore",
			"GeometryFramework",
			"MeshDescription",
			"StaticMeshDescription",
			// vehicle / character / cameras / traffic / UI / audio (agent 2)
			"ChaosVehicles",
			"ChaosVehiclesCore",
			"PhysicsCore",
			"Chaos",
			"AIModule",
			"NavigationSystem",
			"GameplayTasks",
			"CinematicCamera",
			"UMG",
			"Slate",
			"SlateCore",
			"AudioMixer",
			"AudioExtensions",
			"MetasoundEngine",
			"MetasoundFrontend",
			"MetasoundGraphCore",
			"SignalProcessing",
			"MovieScene",
			"AnimGraphRuntime",
		});

		PrivateDependencyModuleNames.AddRange(new string[]
		{
			"ApplicationCore",
			"ImageWrapper",
			"ImageCore",
			"Renderer",
		});

		if (Target.bBuildEditor)
		{
			PrivateDependencyModuleNames.AddRange(new string[] { "UnrealEd" });
		}

		PublicDefinitions.Add("NYCSIM_RUNTIME=1");
	}
}
