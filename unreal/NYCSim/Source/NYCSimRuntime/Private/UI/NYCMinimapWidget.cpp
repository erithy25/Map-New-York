#include "UI/NYCMinimapWidget.h"

#include "CoreAdapter/GameplayRoadNetwork.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "Traffic/NYCRoadNetworkSubsystem.h"
#include "UI/NYCGpsSubsystem.h"
#include "UI/SNYCMinimap.h"

namespace
{
/// Zoom detents, metres of half-width, the way a real navigation display steps.
const float kZoomSteps[] = {60.f, 120.f, 220.f, 450.f, 900.f, 1800.f};
}  // namespace

UNYCMinimapWidget::UNYCMinimapWidget()
{
	bIsVariable = true;
	SetVisibilityInternal(ESlateVisibility::HitTestInvisible);
}

TSharedRef<SWidget> UNYCMinimapWidget::RebuildWidget()
{
	Minimap = SNew(SNYCMinimap)
				  .RangeMetres_Lambda([this]() { return RangeMetres; })
				  .NorthUp_Lambda([this]() { return bNorthUp; });
	return Minimap.ToSharedRef();
}

void UNYCMinimapWidget::ReleaseSlateResources(bool bReleaseChildren)
{
	Super::ReleaseSlateResources(bReleaseChildren);
	Minimap.Reset();
}

#if WITH_EDITOR
const FText UNYCMinimapWidget::GetPaletteCategory()
{
	return NSLOCTEXT("NYCSim", "NYCSimPalette", "NYCSim");
}
#endif

void UNYCMinimapWidget::SetRangeMetres(float Metres)
{
	RangeMetres = FMath::Clamp(Metres, 40.f, 4000.f);
	if (Minimap.IsValid())
	{
		Minimap->SetRange(RangeMetres);
	}
}

void UNYCMinimapWidget::ZoomIn()
{
	for (int32 i = UE_ARRAY_COUNT(kZoomSteps) - 1; i >= 0; --i)
	{
		if (kZoomSteps[i] < RangeMetres - 1.f)
		{
			SetRangeMetres(kZoomSteps[i]);
			return;
		}
	}
	SetRangeMetres(kZoomSteps[0]);
}

void UNYCMinimapWidget::ZoomOut()
{
	for (int32 i = 0; i < static_cast<int32>(UE_ARRAY_COUNT(kZoomSteps)); ++i)
	{
		if (kZoomSteps[i] > RangeMetres + 1.f)
		{
			SetRangeMetres(kZoomSteps[i]);
			return;
		}
	}
	SetRangeMetres(kZoomSteps[UE_ARRAY_COUNT(kZoomSteps) - 1]);
}

void UNYCMinimapWidget::SetNorthUp(bool bInNorthUp)
{
	bNorthUp = bInNorthUp;
}

void UNYCMinimapWidget::RefreshFromWorld()
{
	if (!Minimap.IsValid())
	{
		return;
	}
	const UWorld* World = GetWorld();
	if (World == nullptr)
	{
		return;
	}

	const UNYCRoadNetworkSubsystem* Roads = World->GetSubsystem<UNYCRoadNetworkSubsystem>();
	const UNYCGpsSubsystem* Gps = World->GetSubsystem<UNYCGpsSubsystem>();
	const nycsim_gameplay::RoadNetwork* Network = Roads != nullptr ? Roads->GetNetwork() : nullptr;

	FVector PlayerLocation = FVector::ZeroVector;
	float HeadingDeg = 0.f;
	if (const APlayerController* PlayerController = World->GetFirstPlayerController())
	{
		if (const APawn* Pawn = PlayerController->GetPawn())
		{
			PlayerLocation = Pawn->GetActorLocation();
			// Compass heading: UE yaw 0 is +X (east), and the map wants 0 = north, clockwise.
			HeadingDeg = static_cast<float>(FRotator::ClampAxis(90.0 - Pawn->GetActorRotation().Yaw));
		}
		else
		{
			FRotator ViewRotation;
			PlayerController->GetPlayerViewPoint(PlayerLocation, ViewRotation);
			HeadingDeg = static_cast<float>(FRotator::ClampAxis(90.0 - ViewRotation.Yaw));
		}
	}

	static const TArray<FVector> EmptyRoute;
	Minimap->UpdateState(Network, PlayerLocation, HeadingDeg,
						 Gps != nullptr ? Gps->GetRoutePolyline() : EmptyRoute,
						 Gps != nullptr ? Gps->GetDestination() : FVector::ZeroVector,
						 Gps != nullptr && Gps->HasRoute());
}
