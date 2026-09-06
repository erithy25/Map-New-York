#include "World/NYCSimWorldSettings.h"
#include "Misc/Paths.h"

UNYCSimWorldSettings::UNYCSimWorldSettings()
{
	CategoryName = TEXT("Project");
	SectionName = TEXT("NYCSim World");
}

const UNYCSimWorldSettings& UNYCSimWorldSettings::Get()
{
	const UNYCSimWorldSettings* Settings = GetDefault<UNYCSimWorldSettings>();
	check(Settings);
	return *Settings;
}

FString UNYCSimWorldSettings::ResolveProjectPath(const FString& InPath)
{
	if (InPath.IsEmpty())
	{
		return InPath;
	}
	if (FPaths::IsRelative(InPath))
	{
		return FPaths::ConvertRelativePathToFull(FPaths::Combine(FPaths::ProjectDir(), InPath));
	}
	return FPaths::ConvertRelativePathToFull(InPath);
}
