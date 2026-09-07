#include "UI/SNYCSpeedometer.h"

#include "UI/NYCUiStyle.h"

#include "Fonts/FontMeasure.h"
#include "Framework/Application/SlateApplication.h"
#include "Rendering/DrawElements.h"

void SNYCSpeedometer::Construct(const FArguments& InArgs)
{
	SpeedKph = InArgs._SpeedKph;
	MaxKph = InArgs._MaxKph;
	RedlineKph = InArgs._RedlineKph;
	Gear = InArgs._Gear;
	Opacity = InArgs._Opacity;
	SetCanTick(false);
}

FVector2D SNYCSpeedometer::ComputeDesiredSize(float) const
{
	// 44 units square: the arc plus the number, on the grid like everything else.
	return FVector2D(FNYCUiStyle::Space(44), FNYCUiStyle::Space(44));
}

void SNYCSpeedometer::AppendArc(TArray<FVector2D>& OutPoints, const FVector2D& Centre, float Radius,
	float StartDegrees, float SweepDegrees, int32 Segments)
{
	OutPoints.Reset(Segments + 1);
	for (int32 i = 0; i <= Segments; ++i)
	{
		const float T = static_cast<float>(i) / static_cast<float>(FMath::Max(1, Segments));
		const float Radians = FMath::DegreesToRadians(StartDegrees + SweepDegrees * T);
		OutPoints.Add(Centre + FVector2D(FMath::Cos(Radians), FMath::Sin(Radians)) * Radius);
	}
}

int32 SNYCSpeedometer::OnPaint(const FPaintArgs& Args, const FGeometry& AllottedGeometry,
	const FSlateRect& MyCullingRect, FSlateWindowElementList& OutDrawElements, int32 LayerId,
	const FWidgetStyle& InWidgetStyle, bool bParentEnabled) const
{
	const FVector2D Size = AllottedGeometry.GetLocalSize();
	if (Size.X <= 0.f || Size.Y <= 0.f)
	{
		return LayerId;
	}
	const float Alpha = FMath::Clamp(Opacity.Get(1.f), 0.f, 1.f);
	if (Alpha <= 0.001f)
	{
		return LayerId;
	}

	const FVector2D Centre(Size.X * 0.5f, Size.Y * 0.5f);
	const float Radius = FMath::Min(Size.X, Size.Y) * 0.5f - FNYCUiStyle::Space(2);
	const float Speed = FMath::Max(0.f, SpeedKph.Get(0.f));
	const float Max = FMath::Max(1.f, MaxKph.Get(220.f));
	const float Fraction = FMath::Clamp(Speed / Max, 0.f, 1.f);
	const bool bRedline = Speed >= RedlineKph.Get(Max);

	const FPaintGeometry Geometry = AllottedGeometry.ToPaintGeometry();
	TArray<FVector2D> Points;

	// The track: the whole sweep, at hairline weight, in the line colour.
	AppendArc(Points, Centre, Radius, ArcStartDegrees, ArcSweepDegrees, ArcSegments);
	FSlateDrawElement::MakeLines(OutDrawElements, LayerId, Geometry, Points, ESlateDrawEffect::None,
		FNYCUiStyle::Colour(ENYCColourRole::Line, Alpha), true, FNYCUiStyle::Hairline * 2.f);

	// Major ticks, inward from the track. Eight of them: enough to read a speed at a glance, few
	// enough that the arc still reads as a single stroke.
	for (int32 i = 0; i <= MajorTicks; ++i)
	{
		const float T = static_cast<float>(i) / static_cast<float>(MajorTicks);
		const float Radians = FMath::DegreesToRadians(ArcStartDegrees + ArcSweepDegrees * T);
		const FVector2D Dir(FMath::Cos(Radians), FMath::Sin(Radians));
		TArray<FVector2D> Tick;
		Tick.Add(Centre + Dir * (Radius - FNYCUiStyle::Space(2)));
		Tick.Add(Centre + Dir * Radius);
		FSlateDrawElement::MakeLines(OutDrawElements, LayerId + 1, Geometry, Tick,
			ESlateDrawEffect::None, FNYCUiStyle::Colour(ENYCColourRole::Line, Alpha * 2.f), true,
			FNYCUiStyle::Hairline);
	}

	// The value: the same arc, clipped to the current fraction, in the accent -- or the warning
	// colour past the redline, which is the only place in the driving HUD that colour appears.
	if (Fraction > 0.001f)
	{
		AppendArc(Points, Centre, Radius, ArcStartDegrees, ArcSweepDegrees * Fraction,
			FMath::Max(2, FMath::RoundToInt(ArcSegments * Fraction)));
		FSlateDrawElement::MakeLines(OutDrawElements, LayerId + 2, Geometry, Points,
			ESlateDrawEffect::None,
			FNYCUiStyle::Colour(bRedline ? ENYCColourRole::Warn : ENYCColourRole::Accent, Alpha),
			true, FNYCUiStyle::Space(1));
	}

	const TSharedRef<FSlateFontMeasure> Measure = FSlateApplication::Get().GetRenderer()->GetFontMeasureService();

	// The number, centred. Integer km/h: a decimal on a speedometer is noise.
	const FSlateFontInfo BigFont = FNYCUiStyle::Font(ENYCTextRole::Display);
	const FString Number = FString::Printf(TEXT("%d"), FMath::RoundToInt(Speed));
	const FVector2D NumberSize = Measure->Measure(Number, BigFont);
	FSlateDrawElement::MakeText(OutDrawElements, LayerId + 3,
		AllottedGeometry.ToPaintGeometry(NumberSize,
			FSlateLayoutTransform(Centre - NumberSize * 0.5f - FVector2D(0.f, FNYCUiStyle::Space(1)))),
		Number, BigFont, ESlateDrawEffect::None, FNYCUiStyle::Colour(ENYCColourRole::Text, Alpha));

	// The unit, under the number and muted, so the eye lands on the digits.
	const FSlateFontInfo UnitFont = FNYCUiStyle::Font(ENYCTextRole::Caption);
	const FString Unit = TEXT("km/h");
	const FVector2D UnitSize = Measure->Measure(Unit, UnitFont);
	FSlateDrawElement::MakeText(OutDrawElements, LayerId + 3,
		AllottedGeometry.ToPaintGeometry(UnitSize, FSlateLayoutTransform(
			FVector2D(Centre.X - UnitSize.X * 0.5f,
				Centre.Y + NumberSize.Y * 0.5f - FNYCUiStyle::Space(1)))),
		Unit, UnitFont, ESlateDrawEffect::None, FNYCUiStyle::Colour(ENYCColourRole::TextMuted, Alpha));

	// The gear, at the bottom of the dial where the arc leaves a gap.
	const FString GearText = Gear.Get(FString(TEXT("N")));
	if (!GearText.IsEmpty())
	{
		const FSlateFontInfo GearFont = FNYCUiStyle::Font(ENYCTextRole::Title);
		const FVector2D GearSize = Measure->Measure(GearText, GearFont);
		FSlateDrawElement::MakeText(OutDrawElements, LayerId + 3,
			AllottedGeometry.ToPaintGeometry(GearSize, FSlateLayoutTransform(
				FVector2D(Centre.X - GearSize.X * 0.5f, Centre.Y + Radius - GearSize.Y))),
			GearText, GearFont, ESlateDrawEffect::None,
			FNYCUiStyle::Colour(ENYCColourRole::Accent, Alpha));
	}

	return LayerId + 4;
}
