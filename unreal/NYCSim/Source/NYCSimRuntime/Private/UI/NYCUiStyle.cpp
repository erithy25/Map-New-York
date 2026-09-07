#include "UI/NYCUiStyle.h"

#include "Player/NYCGameplaySettings.h"

#include "Engine/Font.h"
#include "Styling/CoreStyle.h"

namespace
{
/**
 * sRGB hex to linear. The palette is written the way a designer reads it, and converted once here,
 * because FLinearColor's own constructor takes linear values and a hand-converted table is a table
 * that drifts.
 */
FLinearColor FromHex(uint32 Rgb, float Alpha = 1.f)
{
	const FColor Srgb(static_cast<uint8>((Rgb >> 16) & 0xFF), static_cast<uint8>((Rgb >> 8) & 0xFF),
		static_cast<uint8>(Rgb & 0xFF), 255);
	FLinearColor Out = FLinearColor::FromSRGBColor(Srgb);
	Out.A = Alpha;
	return Out;
}
}  // namespace

float FNYCUiStyle::EaseOut(float T)
{
	const float C = FMath::Clamp(T, 0.f, 1.f) - 1.f;
	return C * C * C + 1.f;
}

float FNYCUiStyle::Approach(float Current, float Target, float DeltaSeconds, float TimeConstantSeconds)
{
	if (TimeConstantSeconds <= 0.f || DeltaSeconds <= 0.f)
	{
		return Target;
	}
	// Exponential approach: frame-rate independent, and the same shape as the dashboard needle
	// damping in UNYCVehicleDashboardComponent, so the HUD and the physical gauge move together.
	const float Alpha = 1.f - FMath::Exp(-DeltaSeconds / TimeConstantSeconds);
	return FMath::Lerp(Current, Target, Alpha);
}

float FNYCUiStyle::Size(ENYCTextRole Role)
{
	switch (Role)
	{
	case ENYCTextRole::Display:
		return 48.f;
	case ENYCTextRole::Title:
		return 24.f;
	case ENYCTextRole::Label:
		return 15.f;
	case ENYCTextRole::Caption:
	default:
		return 12.f;
	}
}

FSlateFontInfo FNYCUiStyle::Font(ENYCTextRole Role)
{
	const int32 Points = FMath::RoundToInt(Size(Role));
	const UNYCGameplaySettings& Settings = UNYCGameplaySettings::Get();
	if (UFont* Loaded = Cast<UFont>(Settings.HudFont.TryLoad()))
	{
		return FSlateFontInfo(Loaded, Points);
	}
	return FCoreStyle::GetDefaultFontStyle("Regular", Points);
}

FLinearColor FNYCUiStyle::Colour(ENYCColourRole Role)
{
	switch (Role)
	{
	case ENYCColourRole::Panel:
		return FromHex(0x0B0D10, 0.72f);
	case ENYCColourRole::Text:
		return FromHex(0xF2F4F7);
	case ENYCColourRole::TextMuted:
		return FromHex(0x9AA3AE);
	case ENYCColourRole::Accent:
		// The taxi yellow the project already paints with (blender/vehicles/build_fusion.py).
		return FromHex(0xF7B500);
	case ENYCColourRole::Warn:
		return FromHex(0xFF6B35);
	case ENYCColourRole::Line:
	default:
		return FLinearColor(1.f, 1.f, 1.f, 0.08f);
	}
}

FLinearColor FNYCUiStyle::Colour(ENYCColourRole Role, float Opacity)
{
	FLinearColor Out = Colour(Role);
	Out.A *= FMath::Clamp(Opacity, 0.f, 1.f);
	return Out;
}

FSlateColor FNYCUiStyle::Slate(ENYCColourRole Role)
{
	return FSlateColor(Colour(Role));
}
