#include "UI/SNYCMinimap.h"

#include "CoreAdapter/GameplayRoadNetwork.h"
#include "CoreAdapter/NYCGeo.h"
#include "Rendering/DrawElements.h"
#include "Styling/CoreStyle.h"

namespace
{
constexpr float kCmPerMetre = 100.f;
/// Rebuild the cache once the player has moved this fraction of the range.
constexpr float kCacheMoveFraction = 0.25f;
/// Hard cap on the number of lanes gathered per rebuild; Midtown at 220 m is about 900.
constexpr uint32 kMaxLanes = 4096;

FLinearColor RoadColour(nycsim::routing::RwType Type, bool bBusLane)
{
	using nycsim::routing::RwType;
	switch (Type)
	{
	case RwType::Highway: return FLinearColor(0.98f, 0.72f, 0.25f);
	case RwType::Bridge: return FLinearColor(0.78f, 0.80f, 0.86f);
	case RwType::Tunnel: return FLinearColor(0.40f, 0.42f, 0.48f);
	case RwType::Ramp: return FLinearColor(0.86f, 0.66f, 0.35f);
	case RwType::Boardwalk:
	case RwType::Path:
	case RwType::StepStreet: return FLinearColor(0.55f, 0.75f, 0.55f);
	case RwType::Ferry: return FLinearColor(0.35f, 0.55f, 0.80f);
	default: return bBusLane ? FLinearColor(0.55f, 0.70f, 0.90f) : FLinearColor(0.82f, 0.84f, 0.88f);
	}
}

float RoadThickness(nycsim::routing::RwType Type, uint8 TravelLanes)
{
	using nycsim::routing::RwType;
	if (Type == RwType::Highway)
	{
		return 5.f;
	}
	if (Type == RwType::Bridge || Type == RwType::Tunnel || Type == RwType::Ramp)
	{
		return 3.5f;
	}
	return TravelLanes >= 3 ? 3.f : (TravelLanes == 2 ? 2.2f : 1.6f);
}
}  // namespace

void SNYCMinimap::Construct(const FArguments& InArgs)
{
	RangeMetres = InArgs._RangeMetres;
	NorthUp = InArgs._NorthUp;
	SetCanTick(false);
}

void SNYCMinimap::SetRange(float Metres)
{
	RangeMetres = FMath::Clamp(Metres, 40.f, 4000.f);
	bCacheValid = false;
}

void SNYCMinimap::UpdateState(const nycsim_gameplay::RoadNetwork* InNetwork, const FVector& InPlayerWorld,
							  float InHeadingDeg, const TArray<FVector>& InRoutePolyline,
							  const FVector& InDestinationWorld, bool bInHasRoute)
{
	Network = InNetwork;
	PlayerWorld = InPlayerWorld;
	HeadingDeg = InHeadingDeg;
	RoutePolyline = InRoutePolyline;
	DestinationWorld = InDestinationWorld;
	bHasRoute = bInHasRoute;

	const FVector Tm = NYCGeo::UEToNycTm(PlayerWorld);
	PlayerTm = FVector2f(static_cast<float>(Tm.X), static_cast<float>(Tm.Y));

	const float Range = RangeMetres.Get(220.f);
	if (!bCacheValid || !FMath::IsNearlyEqual(CacheRangeMetres, Range, 1.f) ||
		FVector2f::Distance(PlayerTm, CacheCentreTm) > Range * kCacheMoveFraction)
	{
		RebuildCache();
	}
}

void SNYCMinimap::RebuildCache()
{
	CachedLines.Reset();
	CacheCentreTm = PlayerTm;
	CacheRangeMetres = RangeMetres.Get(220.f);
	bCacheValid = true;
	if (Network == nullptr || !Network->loaded())
	{
		return;
	}

	const nycsim::routing::RoadGraph& Graph = Network->graph();
	TArray<uint32> Lanes;
	Lanes.SetNumUninitialized(kMaxLanes);
	// A square of side 2 * range fits in a circle of radius range * sqrt(2).
	const float Radius = CacheRangeMetres * 1.45f;
	const uint32 Found = Graph.lanesNear(PlayerTm.X, PlayerTm.Y, Radius, Lanes.GetData(), kMaxLanes, false);
	const uint32 Count = FMath::Min(Found, kMaxLanes);

	// Only the lane nearest the centreline of each segment is drawn: a minimap shows streets, not lanes.
	TSet<uint32> DrawnSegments;
	DrawnSegments.Reserve(static_cast<int32>(Count));

	for (uint32 i = 0; i < Count; ++i)
	{
		const uint32 LaneIndex = Lanes[static_cast<int32>(i)];
		if (LaneIndex >= Graph.laneCount())
		{
			continue;
		}
		const nycsim::routing::Lane& Lane = Graph.lane(LaneIndex);
		if (Lane.is_junction != 0 || Lane.segment == nycsim::routing::kInvalidIndex)
		{
			continue;
		}
		if (DrawnSegments.Contains(Lane.segment))
		{
			continue;
		}
		DrawnSegments.Add(Lane.segment);

		const nycsim::routing::Segment& Segment = Graph.segment(Lane.segment);
		uint32 VertexCount = 0;
		const nycsim::routing::Vec3* Vertices = Graph.segmentVertices(Lane.segment, VertexCount);
		if (VertexCount < 2)
		{
			continue;
		}

		FCachedLine Line;
		Line.Points.Reserve(static_cast<int32>(VertexCount));
		for (uint32 v = 0; v < VertexCount; ++v)
		{
			Line.Points.Add(FVector2f(Vertices[v].x, Vertices[v].y));
		}
		Line.Colour = RoadColour(Segment.attrs.rw_type,
								 (Segment.attrs.flags & nycsim::routing::kSegBusLane) != 0);
		Line.Thickness = RoadThickness(Segment.attrs.rw_type, Segment.attrs.travel_lanes);
		CachedLines.Add(MoveTemp(Line));
	}
}

FVector2D SNYCMinimap::WorldToWidget(const FVector2f& TmPoint, const FGeometry& Geometry) const
{
	const FVector2D Size = Geometry.GetLocalSize();
	const float Range = FMath::Max(1.f, RangeMetres.Get(220.f));
	const float PixelsPerMetre = static_cast<float>(FMath::Min(Size.X, Size.Y)) * 0.5f / Range;

	// NYC_TM is east/north; the widget is x-right / y-down, so north maps to -y.
	float Dx = TmPoint.X - PlayerTm.X;
	float Dy = TmPoint.Y - PlayerTm.Y;

	if (!NorthUp.Get(false))
	{
		// Rotate so the player's heading points up. Heading is a compass bearing (0 = north, clockwise).
		const float Rad = FMath::DegreesToRadians(HeadingDeg);
		const float S = FMath::Sin(Rad);
		const float C = FMath::Cos(Rad);
		const float Rx = Dx * C - Dy * S;
		const float Ry = Dx * S + Dy * C;
		Dx = Rx;
		Dy = Ry;
	}

	return FVector2D(Size.X * 0.5 + Dx * PixelsPerMetre, Size.Y * 0.5 - Dy * PixelsPerMetre);
}

int32 SNYCMinimap::OnPaint(const FPaintArgs& Args, const FGeometry& AllottedGeometry, const FSlateRect& MyCullingRect,
						   FSlateWindowElementList& OutDrawElements, int32 LayerId, const FWidgetStyle& InWidgetStyle,
						   bool bParentEnabled) const
{
	const ESlateDrawEffect Effects = bParentEnabled ? ESlateDrawEffect::None : ESlateDrawEffect::DisabledEffect;
	const FVector2D Size = AllottedGeometry.GetLocalSize();
	const FSlateBrush* Brush = FCoreStyle::Get().GetBrush(TEXT("WhiteBrush"));

	// Background.
	FSlateDrawElement::MakeBox(OutDrawElements, LayerId, AllottedGeometry.ToPaintGeometry(), Brush, Effects,
							   FLinearColor(0.06f, 0.07f, 0.09f, 0.92f));
	int32 Layer = LayerId + 1;

	// Roads.
	TArray<FVector2D> Points;
	for (const FCachedLine& Line : CachedLines)
	{
		Points.Reset(Line.Points.Num());
		bool bAnyInside = false;
		for (const FVector2f& Point : Line.Points)
		{
			const FVector2D Local = WorldToWidget(Point, AllottedGeometry);
			Points.Add(Local);
			if (Local.X > -32.0 && Local.Y > -32.0 && Local.X < Size.X + 32.0 && Local.Y < Size.Y + 32.0)
			{
				bAnyInside = true;
			}
		}
		if (!bAnyInside || Points.Num() < 2)
		{
			continue;
		}
		FSlateDrawElement::MakeLines(OutDrawElements, Layer, AllottedGeometry.ToPaintGeometry(), Points, Effects,
									 Line.Colour, /*bAntialias*/ true, Line.Thickness);
	}
	++Layer;

	// Route.
	if (bHasRoute && RoutePolyline.Num() >= 2)
	{
		Points.Reset(RoutePolyline.Num());
		for (const FVector& WorldPoint : RoutePolyline)
		{
			const FVector Tm = NYCGeo::UEToNycTm(WorldPoint);
			Points.Add(WorldToWidget(FVector2f(static_cast<float>(Tm.X), static_cast<float>(Tm.Y)), AllottedGeometry));
		}
		FSlateDrawElement::MakeLines(OutDrawElements, Layer, AllottedGeometry.ToPaintGeometry(), Points, Effects,
									 FLinearColor(0.20f, 0.62f, 1.0f), true, 5.f);
		++Layer;

		// Destination marker.
		const FVector DestTm = NYCGeo::UEToNycTm(DestinationWorld);
		const FVector2D Dest =
			WorldToWidget(FVector2f(static_cast<float>(DestTm.X), static_cast<float>(DestTm.Y)), AllottedGeometry);
		const FVector2D MarkerSize(12.f, 12.f);
		FSlateDrawElement::MakeBox(
			OutDrawElements, Layer,
			AllottedGeometry.ToPaintGeometry(MarkerSize, FSlateLayoutTransform(Dest - MarkerSize * 0.5)), Brush,
			Effects, FLinearColor(1.0f, 0.35f, 0.25f));
		++Layer;
	}

	// Player arrow: a triangle pointing up (the map is heading-up unless NorthUp is set).
	{
		const FVector2D Centre(Size.X * 0.5, Size.Y * 0.5);
		const float Rotation = NorthUp.Get(false) ? FMath::DegreesToRadians(-HeadingDeg) : 0.f;
		const float S = FMath::Sin(Rotation);
		const float C = FMath::Cos(Rotation);
		auto Rotate = [&](const FVector2D& P) {
			return Centre + FVector2D(P.X * C - P.Y * S, P.X * S + P.Y * C);
		};
		TArray<FVector2D> Arrow;
		Arrow.Add(Rotate(FVector2D(0.0, -11.0)));
		Arrow.Add(Rotate(FVector2D(7.5, 8.0)));
		Arrow.Add(Rotate(FVector2D(0.0, 4.0)));
		Arrow.Add(Rotate(FVector2D(-7.5, 8.0)));
		Arrow.Add(Rotate(FVector2D(0.0, -11.0)));
		FSlateDrawElement::MakeLines(OutDrawElements, Layer, AllottedGeometry.ToPaintGeometry(), Arrow, Effects,
									 FLinearColor(1.f, 0.85f, 0.2f), true, 2.5f);
		++Layer;
	}

	// North indicator: a short needle that always points to true north.
	{
		const FVector2D Corner(Size.X - 22.0, 22.0);
		const float Rad = NorthUp.Get(false) ? 0.f : FMath::DegreesToRadians(HeadingDeg);
		const FVector2D Needle(FMath::Sin(Rad) * 12.0, -FMath::Cos(Rad) * 12.0);
		TArray<FVector2D> Line;
		Line.Add(Corner - Needle * 0.4);
		Line.Add(Corner + Needle);
		FSlateDrawElement::MakeLines(OutDrawElements, Layer, AllottedGeometry.ToPaintGeometry(), Line, Effects,
									 FLinearColor(0.95f, 0.3f, 0.3f), true, 2.f);
		++Layer;
	}

	// Scale bar: 50 m at the current zoom.
	{
		const float Range = FMath::Max(1.f, RangeMetres.Get(220.f));
		const float PixelsPerMetre = static_cast<float>(FMath::Min(Size.X, Size.Y)) * 0.5f / Range;
		const float BarMetres = Range > 400.f ? 200.f : (Range > 150.f ? 50.f : 20.f);
		const float BarPixels = BarMetres * PixelsPerMetre;
		TArray<FVector2D> Bar;
		Bar.Add(FVector2D(12.0, Size.Y - 14.0));
		Bar.Add(FVector2D(12.0 + BarPixels, Size.Y - 14.0));
		FSlateDrawElement::MakeLines(OutDrawElements, Layer, AllottedGeometry.ToPaintGeometry(), Bar, Effects,
									 FLinearColor(0.85f, 0.87f, 0.9f), true, 2.f);
		++Layer;
	}

	return Layer;
}
