// The speedometer: a 240-degree arc and one large number.
//
// A leaf widget that paints, in the same way SNYCMinimap does, because the alternative -- a UMG tree
// of progress bars and images -- would need content assets and would still not draw an arc. Nothing
// here is skinnable; everything it draws comes from FNYCUiStyle.
#pragma once

#include "CoreMinimal.h"
#include "Widgets/DeclarativeSyntaxSupport.h"
#include "Widgets/SLeafWidget.h"

class NYCSIMRUNTIME_API SNYCSpeedometer : public SLeafWidget
{
public:
	SLATE_BEGIN_ARGS(SNYCSpeedometer)
		: _SpeedKph(0.f)
		, _MaxKph(220.f)
		, _RedlineKph(180.f)
		, _Gear(TEXT("N"))
		, _Opacity(1.f)
	{}
		/** Displayed speed. The caller damps it; this widget draws what it is given. */
		SLATE_ATTRIBUTE(float, SpeedKph)
		/** Full-scale deflection. */
		SLATE_ATTRIBUTE(float, MaxKph)
		/** Above this the arc turns to the warning colour. */
		SLATE_ATTRIBUTE(float, RedlineKph)
		/** "P", "R", "N", "D", or a manual gear number. */
		SLATE_ATTRIBUTE(FString, Gear)
		/** Whole-widget opacity, for the idle fade. */
		SLATE_ATTRIBUTE(float, Opacity)
	SLATE_END_ARGS()

	void Construct(const FArguments& InArgs);

	virtual int32 OnPaint(const FPaintArgs& Args, const FGeometry& AllottedGeometry,
		const FSlateRect& MyCullingRect, FSlateWindowElementList& OutDrawElements, int32 LayerId,
		const FWidgetStyle& InWidgetStyle, bool bParentEnabled) const override;

	virtual FVector2D ComputeDesiredSize(float LayoutScaleMultiplier) const override;

private:
	/** Arc geometry: 240 degrees opening downward, so the needle sweeps left to right across the top. */
	static constexpr float ArcStartDegrees = 150.f;
	static constexpr float ArcSweepDegrees = 240.f;
	static constexpr int32 ArcSegments = 96;
	static constexpr int32 MajorTicks = 8;

	static void AppendArc(TArray<FVector2D>& OutPoints, const FVector2D& Centre, float Radius,
		float StartDegrees, float SweepDegrees, int32 Segments);

	TAttribute<float> SpeedKph;
	TAttribute<float> MaxKph;
	TAttribute<float> RedlineKph;
	TAttribute<FString> Gear;
	TAttribute<float> Opacity;
};
