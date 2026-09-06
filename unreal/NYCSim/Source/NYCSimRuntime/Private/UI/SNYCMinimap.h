// The minimap's Slate widget: it paints the real lane graph, the route and the player, with nothing but lines.
//
// Drawing the city on a 256 px screen is a culling problem, not a rendering one. The widget keeps a cache of the
// lane polylines within its range in NYC_TM metres, rebuilt when the player has moved a quarter of the range, and
// paints them with FSlateDrawElement::MakeLines. Street classes get different widths and colours (highway,
// arterial, street, bridge, park path) exactly as a real navigation display does.
#pragma once

#include "CoreMinimal.h"
#include "Widgets/SLeafWidget.h"

namespace nycsim_gameplay
{
class RoadNetwork;
}

class SNYCMinimap : public SLeafWidget
{
public:
	SLATE_BEGIN_ARGS(SNYCMinimap)
		: _RangeMetres(220.f)
		, _NorthUp(false)
	{
	}
		/** Half-width of the visible area in metres. */
		SLATE_ATTRIBUTE(float, RangeMetres)
		/** True: north stays up. False: the map rotates so the player's heading is up. */
		SLATE_ATTRIBUTE(bool, NorthUp)
	SLATE_END_ARGS()

	void Construct(const FArguments& InArgs);

	// SWidget
	virtual int32 OnPaint(const FPaintArgs& Args, const FGeometry& AllottedGeometry, const FSlateRect& MyCullingRect,
						  FSlateWindowElementList& OutDrawElements, int32 LayerId, const FWidgetStyle& InWidgetStyle,
						  bool bParentEnabled) const override;
	virtual FVector2D ComputeDesiredSize(float) const override { return FVector2D(256.f, 256.f); }

	/** Called by the owning UMG widget each tick with the live state. */
	void UpdateState(const nycsim_gameplay::RoadNetwork* InNetwork, const FVector& InPlayerWorld, float InHeadingDeg,
					 const TArray<FVector>& InRoutePolyline, const FVector& InDestinationWorld, bool bInHasRoute);

	void SetRange(float Metres);
	float GetRange() const { return RangeMetres.Get(220.f); }

private:
	/** One cached polyline in NYC_TM metres with the style it should be drawn in. */
	struct FCachedLine
	{
		TArray<FVector2f> Points;
		FLinearColor Colour = FLinearColor::White;
		float Thickness = 1.f;
	};

	void RebuildCache();
	FVector2D WorldToWidget(const FVector2f& TmPoint, const FGeometry& Geometry) const;

	TAttribute<float> RangeMetres;
	TAttribute<bool> NorthUp;

	const nycsim_gameplay::RoadNetwork* Network = nullptr;
	FVector PlayerWorld = FVector::ZeroVector;
	FVector2f PlayerTm = FVector2f::ZeroVector;
	float HeadingDeg = 0.f;
	TArray<FVector> RoutePolyline;
	FVector DestinationWorld = FVector::ZeroVector;
	bool bHasRoute = false;

	mutable TArray<FCachedLine> CachedLines;
	FVector2f CacheCentreTm = FVector2f::ZeroVector;
	float CacheRangeMetres = 0.f;
	bool bCacheValid = false;
};
