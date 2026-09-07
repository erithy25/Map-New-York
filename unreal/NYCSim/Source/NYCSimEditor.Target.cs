// NYCSim editor target (UE 5.4). Adds the NYCSimEditor module (import commandlet, terrain/water import, editor tooling).
using UnrealBuildTool;
using System.Collections.Generic;

public class NYCSimEditorTarget : TargetRules
{
	public NYCSimEditorTarget(TargetInfo Target) : base(Target)
	{
		Type = TargetType.Editor;
		DefaultBuildSettings = BuildSettingsVersion.V4;
		IncludeOrderVersion = EngineIncludeOrderVersion.Unreal5_4;
		ExtraModuleNames.AddRange(new string[] { "NYCSimCore", "NYCSimRuntime", "NYCSimEditor" });
	}
}
