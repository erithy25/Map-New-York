#include "UI/NYCDrivingHudWidget.h"

#include "Sky/NYCSkyTimeSubsystem.h"
#include "UI/NYCGpsSubsystem.h"
#include "UI/NYCGpsWidget.h"
#include "UI/NYCMinimapWidget.h"
#include "UI/NYCUiStyle.h"
#include "UI/SNYCSpeedometer.h"
#include "Vehicle/NYCVehicleDashboardComponent.h"
#include "Vehicle/NYCVehicleLightsComponent.h"
#include "Vehicle/NYCVehicleMovementComponent.h"

#include "Blueprint/WidgetTree.h"
#include "Components/CanvasPanel.h"
#include "Components/CanvasPanelSlot.h"
#include "Components/NativeWidgetHost.h"
#include "Components/TextBlock.h"
#include "Engine/World.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/PlayerController.h"

namespace
{
/** The turn-signal relay in the car clicks at 1.5 Hz; the tell-tale blinks with it. */
constexpr float BlinkHz = 1.5f;

FString FormatDistance(float Metres)
{
	if (Metres >= 1000.f)
	{
		return FString::Printf(TEXT("%.1f km"), Metres / 1000.f);
	}
	// Rounded to 10 m: a metre of precision on a turn distance is noise a driver cannot act on.
	return FString::Printf(TEXT("%d m"), FMath::Max(0, FMath::RoundToInt(Metres / 10.f) * 10));
}
}  // namespace

UNYCDrivingHudWidget::UNYCDrivingHudWidget(const FObjectInitializer& ObjectInitializer)
	: Super(ObjectInitializer)
{
	// The HUD is drawn over the world and never takes a click: every input belongs to the car.
	SetVisibility(ESlateVisibility::HitTestInvisible);
}

TSharedRef<SWidget> UNYCDrivingHudWidget::RebuildWidget()
{
	BuildTree();
	return Super::RebuildWidget();
}

void UNYCDrivingHudWidget::BuildTree()
{
	if (bTreeBuilt || WidgetTree == nullptr)
	{
		return;
	}
	bTreeBuilt = true;

	Root = WidgetTree->ConstructWidget<UCanvasPanel>(UCanvasPanel::StaticClass(), TEXT("HudRoot"));
	WidgetTree->RootWidget = Root;

	// Everything is placed against a corner with the same inset, on the same 4 px grid. Four fixed
	// anchors, no floating elements: the eye learns where to look once and is never wrong after.
	const float Inset = FNYCUiStyle::Space(8);

	auto Place = [this](UWidget* Widget, const FVector2D& Anchor, const FVector2D& Position,
					 const FVector2D& Size) {
		UCanvasPanelSlot* Slot = Root->AddChildToCanvas(Widget);
		if (Slot != nullptr)
		{
			Slot->SetAnchors(FAnchors(Anchor.X, Anchor.Y, Anchor.X, Anchor.Y));
			Slot->SetAlignment(Anchor);
			Slot->SetPosition(Position);
			Slot->SetSize(Size);
		}
		return Slot;
	};

	auto MakeText = [this](const TCHAR* Name, ENYCTextRole Role, ENYCColourRole Colour) {
		UTextBlock* Text = WidgetTree->ConstructWidget<UTextBlock>(UTextBlock::StaticClass(), Name);
		Text->SetFont(FNYCUiStyle::Font(Role));
		Text->SetColorAndOpacity(FNYCUiStyle::Slate(Colour));
		return Text;
	};

	// ---- bottom left: the minimap -------------------------------------------------------------
	Minimap = WidgetTree->ConstructWidget<UNYCMinimapWidget>(UNYCMinimapWidget::StaticClass(),
		TEXT("HudMinimap"));
	Place(Minimap, FVector2D(0.f, 1.f), FVector2D(Inset, -Inset),
		FVector2D(FNYCUiStyle::Space(52), FNYCUiStyle::Space(52)));

	// ---- bottom right: the speedometer ---------------------------------------------------------
	// A Slate leaf inside the UMG tree: the arc cannot be built out of UMG primitives, and a
	// NativeWidgetHost is the supported way to put one there without a content asset.
	{
		UNativeWidgetHost* Host = WidgetTree->ConstructWidget<UNativeWidgetHost>(
			UNativeWidgetHost::StaticClass(), TEXT("HudSpeedoHost"));
		Speedometer = SNew(SNYCSpeedometer)
			.SpeedKph_Lambda([this]() { return DisplayedSpeedKph; })
			.MaxKph(220.f)
			.RedlineKph(180.f)
			.Gear_Lambda([this]() { return GearText; })
			.Opacity_Lambda([this]() { return GaugeOpacity; });
		Host->SetContent(Speedometer.ToSharedRef());
		Place(Host, FVector2D(1.f, 1.f), FVector2D(-Inset, -Inset),
			FVector2D(FNYCUiStyle::Space(44), FNYCUiStyle::Space(44)));
	}

	// ---- top left: the turn card ---------------------------------------------------------------
	ManoeuvreGlyph = MakeText(TEXT("HudManoeuvre"), ENYCTextRole::Display, ENYCColourRole::Accent);
	Place(ManoeuvreGlyph, FVector2D(0.f, 0.f), FVector2D(Inset, Inset),
		FVector2D(FNYCUiStyle::Space(16), FNYCUiStyle::Space(16)));

	ManoeuvreDistance = MakeText(TEXT("HudTurnDistance"), ENYCTextRole::Title, ENYCColourRole::Text);
	Place(ManoeuvreDistance, FVector2D(0.f, 0.f),
		FVector2D(Inset + FNYCUiStyle::Space(18), Inset), FVector2D(FNYCUiStyle::Space(40), FNYCUiStyle::Space(8)));

	ManoeuvreStreet = MakeText(TEXT("HudTurnStreet"), ENYCTextRole::Label, ENYCColourRole::TextMuted);
	Place(ManoeuvreStreet, FVector2D(0.f, 0.f),
		FVector2D(Inset + FNYCUiStyle::Space(18), Inset + FNYCUiStyle::Space(8)),
		FVector2D(FNYCUiStyle::Space(56), FNYCUiStyle::Space(6)));

	// ---- top right: the clock and the street you are on -----------------------------------------
	ClockText = MakeText(TEXT("HudClock"), ENYCTextRole::Title, ENYCColourRole::Text);
	Place(ClockText, FVector2D(1.f, 0.f), FVector2D(-Inset, Inset),
		FVector2D(FNYCUiStyle::Space(28), FNYCUiStyle::Space(8)));

	StreetText = MakeText(TEXT("HudStreet"), ENYCTextRole::Label, ENYCColourRole::TextMuted);
	Place(StreetText, FVector2D(1.f, 0.f), FVector2D(-Inset, Inset + FNYCUiStyle::Space(8)),
		FVector2D(FNYCUiStyle::Space(56), FNYCUiStyle::Space(6)));

	// ---- bottom centre: the tell-tale strip ----------------------------------------------------
	TellTaleText = MakeText(TEXT("HudTellTales"), ENYCTextRole::Title, ENYCColourRole::Accent);
	Place(TellTaleText, FVector2D(0.5f, 1.f), FVector2D(0.f, -Inset),
		FVector2D(FNYCUiStyle::Space(40), FNYCUiStyle::Space(8)));
}

void UNYCDrivingHudWidget::NativeConstruct()
{
	Super::NativeConstruct();
	BuildTree();
	ResolveComponents();
	NotifyActivity();
}

void UNYCDrivingHudWidget::ResolveComponents()
{
	Movement = nullptr;
	Dashboard = nullptr;
	Lights = nullptr;
	const APlayerController* Controller = GetOwningPlayer();
	APawn* Pawn = Controller ? Controller->GetPawn() : nullptr;
	if (Pawn == nullptr)
	{
		return;
	}
	Movement = Pawn->FindComponentByClass<UNYCVehicleMovementComponent>();
	Dashboard = Pawn->FindComponentByClass<UNYCVehicleDashboardComponent>();
	Lights = Pawn->FindComponentByClass<UNYCVehicleLightsComponent>();
}

void UNYCDrivingHudWidget::NotifyActivity()
{
	SecondsSinceActivity = 0.f;
}

void UNYCDrivingHudWidget::SetMinimalMode(bool bMinimal)
{
	if (bMinimalMode == bMinimal)
	{
		return;
	}
	bMinimalMode = bMinimal;
	// In the interior camera the car's own cluster is on screen; a second speedometer over it is
	// clutter, and the minimap belongs on the centre screen at SKT_Screen, not floating in the cabin.
	const ESlateVisibility Hidden = ESlateVisibility::Collapsed;
	const ESlateVisibility Shown = ESlateVisibility::HitTestInvisible;
	if (Minimap)
	{
		Minimap->SetVisibility(bMinimal ? Hidden : Shown);
	}
	if (ClockText)
	{
		ClockText->SetVisibility(bMinimal ? Hidden : Shown);
	}
	if (StreetText)
	{
		StreetText->SetVisibility(bMinimal ? Hidden : Shown);
	}
	if (TellTaleText)
	{
		TellTaleText->SetVisibility(bMinimal ? Hidden : Shown);
	}
}

void UNYCDrivingHudWidget::NativeTick(const FGeometry& MyGeometry, float InDeltaTime)
{
	Super::NativeTick(MyGeometry, InDeltaTime);
	if (!Movement.IsValid() && !Dashboard.IsValid())
	{
		// The pawn can be possessed after the HUD is created; keep looking until it is there.
		ResolveComponents();
	}
	RefreshFromPawn(InDeltaTime);
}

void UNYCDrivingHudWidget::RefreshFromPawn(float DeltaSeconds)
{
	BlinkSeconds += DeltaSeconds;
	SecondsSinceActivity += DeltaSeconds;

	// ---- speed and gear -------------------------------------------------------------------------
	float TargetSpeed = 0.f;
	if (const UNYCVehicleMovementComponent* Move = Movement.Get())
	{
		TargetSpeed = FMath::Abs(Move->GetSpeedKph());
	}
	// The same 0.25 s time constant the physical needle uses, so the two never disagree on screen.
	DisplayedSpeedKph = FNYCUiStyle::Approach(DisplayedSpeedKph, TargetSpeed, DeltaSeconds, 0.25f);
	if (const UNYCVehicleDashboardComponent* Dash = Dashboard.Get())
	{
		GearText = Dash->GetGearText();
	}

	// ---- idle fade ------------------------------------------------------------------------------
	// Anything happening is activity: the car moving counts, so the HUD stays up while you drive and
	// recedes only when you stop to look at the city.
	if (TargetSpeed > 1.f)
	{
		SecondsSinceActivity = 0.f;
	}
	const float Target = SecondsSinceActivity > IdleFadeAfterSeconds ? IdleOpacity : 1.f;
	GaugeOpacity = FNYCUiStyle::Approach(GaugeOpacity, Target, DeltaSeconds, FNYCUiStyle::MotionSeconds);
	SetRenderOpacity(GaugeOpacity);

	// ---- navigation -----------------------------------------------------------------------------
	UNYCGpsSubsystem* Gps = nullptr;
	if (const UWorld* World = GetWorld())
	{
		Gps = World->GetSubsystem<UNYCGpsSubsystem>();
	}
	FNYCGpsInstruction Instruction;
	float ToManoeuvre = 0.f;
	const bool bHasTurn = Gps != nullptr && Gps->HasRoute() && Gps->GetNextInstruction(Instruction, ToManoeuvre);
	const ESlateVisibility TurnCard = bHasTurn ? ESlateVisibility::HitTestInvisible : ESlateVisibility::Collapsed;
	if (ManoeuvreGlyph)
	{
		ManoeuvreGlyph->SetVisibility(TurnCard);
		if (bHasTurn)
		{
			ManoeuvreGlyph->SetText(FText::FromString(UNYCGpsWidget::ManoeuvreGlyph(static_cast<uint8>(Instruction.Manoeuvre))));
		}
	}
	if (ManoeuvreDistance)
	{
		ManoeuvreDistance->SetVisibility(TurnCard);
		if (bHasTurn)
		{
			ManoeuvreDistance->SetText(FText::FromString(FormatDistance(ToManoeuvre)));
		}
	}
	if (ManoeuvreStreet)
	{
		ManoeuvreStreet->SetVisibility(TurnCard);
		if (bHasTurn)
		{
			ManoeuvreStreet->SetText(FText::FromString(Instruction.Street));
		}
	}
	if (StreetText && Gps != nullptr)
	{
		StreetText->SetText(FText::FromString(Gps->GetCurrentStreet()));
	}

	// ---- clock ----------------------------------------------------------------------------------
	if (ClockText)
	{
		if (const UWorld* World = GetWorld())
		{
			if (const UNYCSkyTimeSubsystem* Sky = World->GetSubsystem<UNYCSkyTimeSubsystem>())
			{
				const FDateTime Local = Sky->GetLocalTime();
				ClockText->SetText(FText::FromString(
					FString::Printf(TEXT("%02d:%02d"), Local.GetHour(), Local.GetMinute())));
			}
		}
	}

	// ---- tell-tales -----------------------------------------------------------------------------
	// One line, only what is on. An indicator that is not flashing is not shown at all; a HUD full of
	// grey icons waiting to light up is the thing this design exists to avoid.
	if (TellTaleText)
	{
		FString Tale;
		if (const UNYCVehicleLightsComponent* Lamp = Lights.Get())
		{
			const bool bLit = FMath::Fmod(BlinkSeconds * BlinkHz, 1.f) < 0.5f;
			switch (Lamp->GetTurnSignal())
			{
			case ENYCTurnSignal::Left:
				Tale = bLit ? TEXT("◀") : TEXT(" ");
				break;
			case ENYCTurnSignal::Right:
				Tale = bLit ? TEXT("▶") : TEXT(" ");
				break;
			case ENYCTurnSignal::Hazard:
				Tale = bLit ? TEXT("◀  ▶") : TEXT(" ");
				break;
			default:
				break;
			}
			if (Tale.IsEmpty() && Lamp->GetHeadlightMode() == ENYCHeadlightMode::High)
			{
				Tale = TEXT("≡");
			}
		}
		TellTaleText->SetVisibility(Tale.IsEmpty() ? ESlateVisibility::Collapsed
												   : ESlateVisibility::HitTestInvisible);
		TellTaleText->SetText(FText::FromString(Tale));
	}
}
