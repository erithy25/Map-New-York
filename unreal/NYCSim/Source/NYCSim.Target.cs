// NYCSim game target (UE 5.4). Modules: NYCSimCore (engine-agnostic core), NYCSimRuntime (world + gameplay).
using UnrealBuildTool;
using System.Collections.Generic;

public class NYCSimTarget : TargetRules
{
	public NYCSimTarget(TargetInfo Target) : base(Target)
	{
		Type = TargetType.Game;
		DefaultBuildSettings = BuildSettingsVersion.V4;
		IncludeOrderVersion = EngineIncludeOrderVersion.Unreal5_4;
		ExtraModuleNames.AddRange(new string[] { "NYCSimCore", "NYCSimRuntime" });
	}
}
