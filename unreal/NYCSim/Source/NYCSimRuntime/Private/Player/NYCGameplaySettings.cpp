#include "Player/NYCGameplaySettings.h"

#include "Misc/Paths.h"

UNYCGameplaySettings::UNYCGameplaySettings()
{
	CategoryName = FName(TEXT("Project"));
	SectionName = FName(TEXT("NYCSim Gameplay"));
}

const UNYCGameplaySettings& UNYCGameplaySettings::Get()
{
	const UNYCGameplaySettings* Settings = GetDefault<UNYCGameplaySettings>();
	check(Settings != nullptr);
	return *Settings;
}

FString UNYCGameplaySettings::ResolvePath(const FString& InPath)
{
	if (InPath.IsEmpty())
	{
		return FString();
	}
	if (FPaths::IsRelative(InPath))
	{
		return FPaths::ConvertRelativePathToFull(FPaths::ProjectDir() / InPath);
	}
	return InPath;
}
