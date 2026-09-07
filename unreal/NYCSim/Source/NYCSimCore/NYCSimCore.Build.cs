// NYCSimCore: compiles the engine-agnostic C++17 library that lives in <repo>/core into a UE module.
//
// UBT only compiles source files located under the module directory, so the core sources are pulled in through
// generated wrapper translation units in Private/CoreUnity/ (one .cpp per core/src/**/*.cpp) or a single
// Private/CoreUnity.cpp, both produced by <repo>/unreal/tools/gen_core_unity.py. Re-run that script whenever a
// file is added to core/src.
using System.IO;
using UnrealBuildTool;

public class NYCSimCore : ModuleRules
{
	public NYCSimCore(ReadOnlyTargetRules Target) : base(Target)
	{
		// Pure standard C++: no engine PCH, no UE headers in the core sources.
		PCHUsage = PCHUsageMode.NoPCHs;
		IncludeOrderVersion = EngineIncludeOrderVersion.Unreal5_4;
		CppStandard = CppStandardVersion.Cpp17;
		// The wrapper .cpp files must each stay their own translation unit (anonymous-namespace helpers in the
		// core sources are not unity-safe by contract), so UBT's own unity concatenation is disabled here.
		bUseUnity = false;
		bEnableExceptions = false;
		bUseRTTI = false;
		// The core is -Wall -Wextra -Werror clean under GCC/Clang; MSVC-only analysis warnings (C4996 on the C
		// string functions, C4267 size_t narrowing) must not break the build.
		bWarningsAsErrors = false;
		ShadowVariableWarningLevel = WarningLevel.Off;
		UnsafeTypeCastWarningLevel = WarningLevel.Off;
		bEnableUndefinedIdentifierWarnings = false;

		// <repo>/unreal/NYCSim/Source/NYCSimCore -> <repo>
		string RepoRoot = Path.GetFullPath(Path.Combine(ModuleDirectory, "..", "..", "..", ".."));
		string CoreRoot = Path.Combine(RepoRoot, "core");
		string CoreInclude = Path.Combine(CoreRoot, "include");
		string CoreSrc = Path.Combine(CoreRoot, "src");
		if (!Directory.Exists(CoreInclude))
		{
			throw new BuildException("NYCSimCore: core include directory not found at " + CoreInclude +
				" (the UE project must live at <repo>/unreal/NYCSim so that ../../../../core resolves)");
		}

		PublicIncludePaths.Add(CoreInclude);
		PrivateIncludePaths.Add(CoreSrc);
		PublicIncludePaths.Add(Path.Combine(ModuleDirectory, "Public"));

		PublicDependencyModuleNames.AddRange(new string[] { "Core" });

		PublicDefinitions.Add("NYCSIM_CORE_IN_UNREAL=1");
		// Core sources are compiled without UE's TCHAR/UNICODE assumptions in mind; the definitions below keep
		// MSVC's CRT from turning strncpy/sprintf/localtime into errors.
		if (Target.Platform == UnrealTargetPlatform.Win64)
		{
			PrivateDefinitions.Add("_CRT_SECURE_NO_WARNINGS=1");
			PrivateDefinitions.Add("_CRT_NONSTDC_NO_WARNINGS=1");
		}
	}
}
