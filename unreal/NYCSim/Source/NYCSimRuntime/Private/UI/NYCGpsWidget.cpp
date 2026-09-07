#include "UI/NYCGpsWidget.h"

#include "Blueprint/WidgetTree.h"
#include "Components/CanvasPanel.h"
#include "Components/CanvasPanelSlot.h"
#include "Components/EditableTextBox.h"
#include "Components/TextBlock.h"
#include "Components/VerticalBox.h"
#include "Components/VerticalBoxSlot.h"
#include "Engine/Font.h"
#include "Engine/World.h"
#include "NYCSimRuntime.h"
#include "Player/NYCGameplaySettings.h"
#include "Styling/CoreStyle.h"
#include "UI/NYCGpsSubsystem.h"
#include "UI/NYCMinimapWidget.h"

namespace
{
constexpr int32 kMaxResults = 8;
const FLinearColor kInk(0.92f, 0.94f, 0.97f);
const FLinearColor kDim(0.62f, 0.66f, 0.72f);
const FLinearColor kAccent(0.25f, 0.68f, 1.0f);

FSlateFontInfo MakeFont(int32 Size)
{
	const UNYCGameplaySettings& Settings = UNYCGameplaySettings::Get();
	if (UFont* Font = Cast<UFont>(Settings.HudFont.TryLoad()))
	{
		return FSlateFontInfo(Font, Size);
	}
	// Falls back to the engine's font so the screen is readable before the font import stage has run.
	return FCoreStyle::GetDefaultFontStyle("Regular", Size);
}
}  // namespace

UNYCGpsWidget::UNYCGpsWidget(const FObjectInitializer& ObjectInitializer)
	: Super(ObjectInitializer)
{
	SetVisibility(ESlateVisibility::SelfHitTestInvisible);
}

TSharedRef<SWidget> UNYCGpsWidget::RebuildWidget()
{
	BuildTree();
	return Super::RebuildWidget();
}

void UNYCGpsWidget::BuildTree()
{
	if (bTreeBuilt || WidgetTree == nullptr)
	{
		return;
	}
	bTreeBuilt = true;

	Root = WidgetTree->ConstructWidget<UCanvasPanel>(UCanvasPanel::StaticClass(), TEXT("GpsRoot"));
	WidgetTree->RootWidget = Root;

	auto Place = [this](UWidget* Widget, const FVector2D& Position, const FVector2D& Size, const FVector2D& Anchor) {
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

	// Minimap fills the screen; everything else sits on top of it.
	Minimap = WidgetTree->ConstructWidget<UNYCMinimapWidget>(UNYCMinimapWidget::StaticClass(), TEXT("Minimap"));
	if (UCanvasPanelSlot* Slot = Root->AddChildToCanvas(Minimap))
	{
		Slot->SetAnchors(FAnchors(0.f, 0.f, 1.f, 1.f));
		Slot->SetOffsets(FMargin(0.f));
	}

	auto MakeText = [this](const TCHAR* Name, int32 Size, const FLinearColor& Colour) {
		UTextBlock* Text = WidgetTree->ConstructWidget<UTextBlock>(UTextBlock::StaticClass(), Name);
		Text->SetFont(MakeFont(Size));
		Text->SetColorAndOpacity(FSlateColor(Colour));
		return Text;
	};

	TurnGlyph = MakeText(TEXT("TurnGlyph"), 34, kAccent);
	Place(TurnGlyph, FVector2D(14.f, 12.f), FVector2D(48.f, 44.f), FVector2D(0.f, 0.f));

	TurnText = MakeText(TEXT("TurnText"), 15, kInk);
	TurnText->SetAutoWrapText(true);
	Place(TurnText, FVector2D(66.f, 12.f), FVector2D(210.f, 40.f), FVector2D(0.f, 0.f));

	TurnDistance = MakeText(TEXT("TurnDistance"), 20, kAccent);
	Place(TurnDistance, FVector2D(66.f, 50.f), FVector2D(140.f, 26.f), FVector2D(0.f, 0.f));

	StreetText = MakeText(TEXT("StreetText"), 13, kDim);
	Place(StreetText, FVector2D(14.f, -34.f), FVector2D(260.f, 22.f), FVector2D(0.f, 1.f));

	EtaText = MakeText(TEXT("EtaText"), 14, kInk);
	Place(EtaText, FVector2D(14.f, -12.f), FVector2D(260.f, 22.f), FVector2D(0.f, 1.f));

	SearchBox = WidgetTree->ConstructWidget<UEditableTextBox>(UEditableTextBox::StaticClass(), TEXT("SearchBox"));
	SearchBox->SetHintText(FText::FromString(TEXT("Search an address, street, stop or landmark")));
	SearchBox->SetVisibility(ESlateVisibility::Collapsed);
	Place(SearchBox, FVector2D(0.f, 10.f), FVector2D(320.f, 30.f), FVector2D(0.5f, 0.f));

	ResultsBox = WidgetTree->ConstructWidget<UVerticalBox>(UVerticalBox::StaticClass(), TEXT("ResultsBox"));
	ResultsBox->SetVisibility(ESlateVisibility::Collapsed);
	Place(ResultsBox, FVector2D(0.f, 44.f), FVector2D(320.f, 200.f), FVector2D(0.5f, 0.f));

	ResultLines.Reset();
	for (int32 i = 0; i < kMaxResults; ++i)
	{
		UTextBlock* Line = MakeText(*FString::Printf(TEXT("Result_%d"), i), 13, kInk);
		Line->SetVisibility(ESlateVisibility::Collapsed);
		if (UVerticalBoxSlot* Slot = ResultsBox->AddChildToVerticalBox(Line))
		{
			Slot->SetPadding(FMargin(4.f, 2.f));
		}
		ResultLines.Add(Line);
	}
}

void UNYCGpsWidget::NativeConstruct()
{
	Super::NativeConstruct();
	UpdateTexts();
}

FString UNYCGpsWidget::FormatDistance(float Metres)
{
	// US navigation units: feet under 0.1 mile, then miles to one decimal.
	const float Feet = Metres * 3.28084f;
	if (Feet < 528.f)
	{
		const int32 Rounded = FMath::RoundToInt(Feet / 10.f) * 10;
		return FString::Printf(TEXT("%d ft"), FMath::Max(10, Rounded));
	}
	return FString::Printf(TEXT("%.1f mi"), Metres / 1609.344f);
}

FString UNYCGpsWidget::FormatEta(float Seconds)
{
	const int32 Total = FMath::Max(0, FMath::RoundToInt(Seconds));
	const int32 Hours = Total / 3600;
	const int32 Minutes = (Total % 3600) / 60;
	if (Hours > 0)
	{
		return FString::Printf(TEXT("%d h %02d min"), Hours, Minutes);
	}
	return FString::Printf(TEXT("%d min"), FMath::Max(1, Minutes));
}

FString UNYCGpsWidget::ManoeuvreGlyph(uint8 Manoeuvre)
{
	switch (static_cast<ENYCManoeuvre>(Manoeuvre))
	{
	case ENYCManoeuvre::TurnLeft: return TEXT("←");
	case ENYCManoeuvre::TurnRight: return TEXT("→");
	case ENYCManoeuvre::SlightLeft: return TEXT("↖");
	case ENYCManoeuvre::SlightRight: return TEXT("↗");
	case ENYCManoeuvre::SharpLeft: return TEXT("↰");
	case ENYCManoeuvre::SharpRight: return TEXT("↱");
	case ENYCManoeuvre::UTurn: return TEXT("↶");
	case ENYCManoeuvre::Arrive: return TEXT("◉");
	case ENYCManoeuvre::Depart: return TEXT("▲");
	case ENYCManoeuvre::Ramp: return TEXT("↗");
	case ENYCManoeuvre::Bridge: return TEXT("≡");
	case ENYCManoeuvre::Tunnel: return TEXT("⊓");
	case ENYCManoeuvre::Continue:
	default: return TEXT("↑");
	}
}

void UNYCGpsWidget::UpdateTexts()
{
	const UWorld* World = GetWorld();
	const UNYCGpsSubsystem* Gps = World != nullptr ? World->GetSubsystem<UNYCGpsSubsystem>() : nullptr;
	if (Gps == nullptr)
	{
		return;
	}

	if (StreetText != nullptr)
	{
		const FString Street = Gps->GetCurrentStreet();
		StreetText->SetText(FText::FromString(Street.IsEmpty() ? TEXT("off the road network") : Street));
	}

	FNYCGpsInstruction Instruction;
	float DistanceMetres = 0.f;
	const bool bHasNext = Gps->GetNextInstruction(Instruction, DistanceMetres);

	if (TurnGlyph != nullptr)
	{
		TurnGlyph->SetText(FText::FromString(bHasNext ? ManoeuvreGlyph(static_cast<uint8>(Instruction.Manoeuvre))
													  : FString()));
	}
	if (TurnText != nullptr)
	{
		TurnText->SetText(FText::FromString(bHasNext ? Instruction.Text : FString()));
	}
	if (TurnDistance != nullptr)
	{
		TurnDistance->SetText(FText::FromString(bHasNext ? FormatDistance(DistanceMetres) : FString()));
	}
	if (EtaText != nullptr)
	{
		if (Gps->HasRoute())
		{
			EtaText->SetText(FText::FromString(FString::Printf(TEXT("%s  ·  %s to go"),
															   *FormatEta(Gps->GetEtaSeconds()),
															   *FormatDistance(Gps->GetRemainingMetres()))));
		}
		else if (!Gps->IsReady())
		{
			EtaText->SetText(FText::FromString(TEXT("GPS acquiring the road network...")));
		}
		else
		{
			EtaText->SetText(FText::FromString(TEXT("No destination set")));
		}
	}
}

void UNYCGpsWidget::ToggleSearch()
{
	bSearchOpen = !bSearchOpen;
	const ESlateVisibility Visibility = bSearchOpen ? ESlateVisibility::Visible : ESlateVisibility::Collapsed;
	if (SearchBox != nullptr)
	{
		SearchBox->SetVisibility(Visibility);
	}
	if (ResultsBox != nullptr)
	{
		ResultsBox->SetVisibility(Visibility);
	}
	if (!bSearchOpen)
	{
		LastResultLocations.Reset();
		for (UTextBlock* Line : ResultLines)
		{
			if (Line != nullptr)
			{
				Line->SetVisibility(ESlateVisibility::Collapsed);
			}
		}
	}
}

void UNYCGpsWidget::RunSearch(const FString& Query)
{
	LastResultLocations.Reset();
	const UWorld* World = GetWorld();
	const UNYCGpsSubsystem* Gps = World != nullptr ? World->GetSubsystem<UNYCGpsSubsystem>() : nullptr;
	if (Gps == nullptr)
	{
		return;
	}
	const TArray<FNYCGpsSearchResult> Results = Gps->Search(Query, kMaxResults);
	for (int32 i = 0; i < ResultLines.Num(); ++i)
	{
		UTextBlock* Line = ResultLines[i];
		if (Line == nullptr)
		{
			continue;
		}
		if (Results.IsValidIndex(i))
		{
			Line->SetText(FText::FromString(FString::Printf(TEXT("%d.  %s   [%s, %s]"), i + 1, *Results[i].Label,
															*Results[i].Kind,
															*FormatDistance(Results[i].DistanceMetres))));
			Line->SetVisibility(ESlateVisibility::Visible);
			LastResultLocations.Add(Results[i].WorldLocation);
		}
		else
		{
			Line->SetVisibility(ESlateVisibility::Collapsed);
		}
	}
}

bool UNYCGpsWidget::ChooseResult(int32 Index)
{
	if (!LastResultLocations.IsValidIndex(Index))
	{
		return false;
	}
	UWorld* World = GetWorld();
	UNYCGpsSubsystem* Gps = World != nullptr ? World->GetSubsystem<UNYCGpsSubsystem>() : nullptr;
	if (Gps == nullptr)
	{
		return false;
	}
	const bool bRouted = Gps->SetDestinationWorld(LastResultLocations[Index]);
	if (bRouted && bSearchOpen)
	{
		ToggleSearch();
	}
	return bRouted;
}

void UNYCGpsWidget::ZoomIn()
{
	if (Minimap != nullptr)
	{
		Minimap->ZoomIn();
	}
}

void UNYCGpsWidget::ZoomOut()
{
	if (Minimap != nullptr)
	{
		Minimap->ZoomOut();
	}
}

void UNYCGpsWidget::ToggleNorthUp()
{
	if (Minimap != nullptr)
	{
		Minimap->SetNorthUp(!Minimap->IsNorthUp());
	}
}

void UNYCGpsWidget::NativeTick(const FGeometry& MyGeometry, float InDeltaTime)
{
	Super::NativeTick(MyGeometry, InDeltaTime);

	if (Minimap != nullptr)
	{
		Minimap->RefreshFromWorld();
	}

	// The text only has to keep up with a driver reading it; four times a second is plenty and saves the
	// per-frame FText churn.
	RefreshAccumulator += InDeltaTime;
	if (RefreshAccumulator >= 0.25f)
	{
		RefreshAccumulator = 0.f;
		UpdateTexts();
	}
}
