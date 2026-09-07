#include "UI/NYCMenuWidget.h"

#include "Audio/NYCRadioSubsystem.h"
#include "NYCSimRuntime.h"
#include "Player/NYCGameplaySettings.h"
#include "Player/NYCInputConfig.h"
#include "Player/NYCPlayerController.h"
#include "Save/NYCSaveSubsystem.h"
#include "UI/NYCUiStyle.h"
#include "World/NYCSimWorldSettings.h"

#include "Blueprint/WidgetTree.h"
#include "Components/BackgroundBlur.h"
#include "Components/Border.h"
#include "Components/Button.h"
#include "Components/CanvasPanel.h"
#include "Components/CanvasPanelSlot.h"
#include "Components/HorizontalBox.h"
#include "Components/HorizontalBoxSlot.h"
#include "Components/TextBlock.h"
#include "Components/VerticalBox.h"
#include "Components/VerticalBoxSlot.h"
#include "Engine/World.h"
#include "GameFramework/GameUserSettings.h"
#include "Kismet/GameplayStatics.h"

const TArray<ENYCMenuPage>& UNYCMenuWidget::NavPages()
{
	static const TArray<ENYCMenuPage> Pages = {
		ENYCMenuPage::Root, ENYCMenuPage::Graphics, ENYCMenuPage::Audio,
		ENYCMenuPage::Controls, ENYCMenuPage::Save, ENYCMenuPage::Load, ENYCMenuPage::Quit,
	};
	return Pages;
}

FText UNYCMenuWidget::PageTitle(ENYCMenuPage Page)
{
	switch (Page)
	{
	case ENYCMenuPage::Graphics:
		return NSLOCTEXT("NYCSim", "MenuGraphics", "Graphics");
	case ENYCMenuPage::Audio:
		return NSLOCTEXT("NYCSim", "MenuAudio", "Audio");
	case ENYCMenuPage::Controls:
		return NSLOCTEXT("NYCSim", "MenuControls", "Controls");
	case ENYCMenuPage::Save:
		return NSLOCTEXT("NYCSim", "MenuSave", "Save");
	case ENYCMenuPage::Load:
		return NSLOCTEXT("NYCSim", "MenuLoad", "Load");
	case ENYCMenuPage::Quit:
		return NSLOCTEXT("NYCSim", "MenuQuit", "Quit");
	case ENYCMenuPage::Root:
	default:
		return NSLOCTEXT("NYCSim", "MenuRoot", "Paused");
	}
}

UNYCMenuWidget::UNYCMenuWidget(const FObjectInitializer& ObjectInitializer)
	: Super(ObjectInitializer)
{
	SetVisibility(ESlateVisibility::Visible);
	// The world is paused while this is up, so it has to keep ticking to animate and to read the
	// clock; without this the menu appears frozen at whatever opacity it opened with.
	SetIsFocusable(true);
}

TSharedRef<SWidget> UNYCMenuWidget::RebuildWidget()
{
	BuildTree();
	return Super::RebuildWidget();
}

UNYCSaveSubsystem* UNYCMenuWidget::SaveSubsystem() const
{
	const UWorld* World = GetWorld();
	UGameInstance* Instance = World != nullptr ? World->GetGameInstance() : nullptr;
	return Instance != nullptr ? Instance->GetSubsystem<UNYCSaveSubsystem>() : nullptr;
}

void UNYCMenuWidget::BuildTree()
{
	if (bTreeBuilt || WidgetTree == nullptr)
	{
		return;
	}
	bTreeBuilt = true;

	Root = WidgetTree->ConstructWidget<UCanvasPanel>(UCanvasPanel::StaticClass(), TEXT("MenuRoot"));
	WidgetTree->RootWidget = Root;

	// The city stays visible behind an 8 px blur. Depth in this interface comes from the blur, not
	// from shadows or gradients, which is the whole of the shape rule in FNYCUiStyle.
	UBackgroundBlur* Blur = WidgetTree->ConstructWidget<UBackgroundBlur>(UBackgroundBlur::StaticClass(),
																		TEXT("MenuBlur"));
	Blur->SetBlurStrength(8.f);
	if (UCanvasPanelSlot* Slot = Root->AddChildToCanvas(Blur))
	{
		Slot->SetAnchors(FAnchors(0.f, 0.f, 1.f, 1.f));
		Slot->SetOffsets(FMargin(0.f));
	}

	UBorder* Panel = WidgetTree->ConstructWidget<UBorder>(UBorder::StaticClass(), TEXT("MenuPanel"));
	Panel->SetBrushColor(FNYCUiStyle::Colour(ENYCColourRole::Panel));
	Panel->SetPadding(FMargin(FNYCUiStyle::Space(8)));
	Blur->AddChild(Panel);

	UHorizontalBox* Columns = WidgetTree->ConstructWidget<UHorizontalBox>(UHorizontalBox::StaticClass(),
																		 TEXT("MenuColumns"));
	Panel->AddChild(Columns);

	NavBox = WidgetTree->ConstructWidget<UVerticalBox>(UVerticalBox::StaticClass(), TEXT("MenuNav"));
	if (UHorizontalBoxSlot* Slot = Columns->AddChildToHorizontalBox(NavBox))
	{
		Slot->SetPadding(FMargin(0.f, 0.f, FNYCUiStyle::Space(8), 0.f));
		Slot->SetSize(FSlateChildSize(ESlateSizeRule::Fill));
	}

	UVerticalBox* Right = WidgetTree->ConstructWidget<UVerticalBox>(UVerticalBox::StaticClass(),
																   TEXT("MenuRight"));
	if (UHorizontalBoxSlot* Slot = Columns->AddChildToHorizontalBox(Right))
	{
		Slot->SetSize(FSlateChildSize(ESlateSizeRule::Fill));
	}

	TitleText = WidgetTree->ConstructWidget<UTextBlock>(UTextBlock::StaticClass(), TEXT("MenuTitle"));
	TitleText->SetFont(FNYCUiStyle::Font(ENYCTextRole::Title));
	TitleText->SetColorAndOpacity(FNYCUiStyle::Slate(ENYCColourRole::Text));
	if (UVerticalBoxSlot* Slot = Right->AddChildToVerticalBox(TitleText))
	{
		Slot->SetPadding(FMargin(0.f, 0.f, 0.f, FNYCUiStyle::Space(4)));
	}

	DetailBox = WidgetTree->ConstructWidget<UVerticalBox>(UVerticalBox::StaticClass(), TEXT("MenuDetail"));
	if (UVerticalBoxSlot* Slot = Right->AddChildToVerticalBox(DetailBox))
	{
		Slot->SetSize(FSlateChildSize(ESlateSizeRule::Fill));
	}

	StatusText = WidgetTree->ConstructWidget<UTextBlock>(UTextBlock::StaticClass(), TEXT("MenuStatus"));
	StatusText->SetFont(FNYCUiStyle::Font(ENYCTextRole::Caption));
	StatusText->SetColorAndOpacity(FNYCUiStyle::Slate(ENYCColourRole::TextMuted));
	Right->AddChildToVerticalBox(StatusText);

	// The panel occupies the middle of the screen with the standard safe inset kept clear.
	if (UCanvasPanelSlot* Slot = Cast<UCanvasPanelSlot>(Blur->Slot))
	{
		const float Inset = FNYCUiStyle::SafeInset;
		Slot->SetAnchors(FAnchors(Inset, Inset, 1.f - Inset, 1.f - Inset));
		Slot->SetOffsets(FMargin(0.f));
	}

	for (ENYCMenuPage Page : NavPages())
	{
		AddRow(NavBox, PageTitle(Page), FText::GetEmpty(),
			   [this, Page]() { ShowPage(Page); }, Page == ENYCMenuPage::Root);
	}
	ShowPage(ENYCMenuPage::Root);
}

void UNYCMenuWidget::NativeConstruct()
{
	Super::NativeConstruct();
	BuildTree();
	OpenSeconds = 0.f;
}

void UNYCMenuWidget::NativeTick(const FGeometry& MyGeometry, float InDeltaTime)
{
	Super::NativeTick(MyGeometry, InDeltaTime);
	// One curve for everything that appears: 120 ms cubic out, the same as the HUD's.
	OpenSeconds += InDeltaTime;
	SetRenderOpacity(FNYCUiStyle::EaseOut(OpenSeconds / FNYCUiStyle::MotionSeconds));
	if (StatusText != nullptr)
	{
		StatusText->SetText(FText::FromString(Status));
	}
}

UButton* UNYCMenuWidget::AddRow(UVerticalBox* Into, const FText& Label, const FText& Detail,
								TFunction<void()> OnClicked, bool bAccent)
{
	if (Into == nullptr || WidgetTree == nullptr)
	{
		return nullptr;
	}
	UButton* Button = WidgetTree->ConstructWidget<UButton>(UButton::StaticClass());
	FButtonStyle Style = Button->GetStyle();
	// Flat: a filled rectangle at three opacities, no bevel and no gradient. The accent is reserved
	// for the one row that matters on a page.
	const FLinearColor Base = bAccent ? FNYCUiStyle::Colour(ENYCColourRole::Accent, 0.16f)
									  : FNYCUiStyle::Colour(ENYCColourRole::Line);
	Style.Normal.TintColor = FSlateColor(Base);
	Style.Hovered.TintColor = FSlateColor(FLinearColor(Base.R, Base.G, Base.B, FMath::Min(1.f, Base.A * 2.2f)));
	Style.Pressed.TintColor = FSlateColor(FNYCUiStyle::Colour(ENYCColourRole::Accent, 0.32f));
	Button->SetStyle(Style);

	UVerticalBox* Inner = WidgetTree->ConstructWidget<UVerticalBox>(UVerticalBox::StaticClass());
	UTextBlock* LabelText = WidgetTree->ConstructWidget<UTextBlock>(UTextBlock::StaticClass());
	LabelText->SetText(Label);
	LabelText->SetFont(FNYCUiStyle::Font(ENYCTextRole::Label));
	LabelText->SetColorAndOpacity(FNYCUiStyle::Slate(bAccent ? ENYCColourRole::Accent : ENYCColourRole::Text));
	Inner->AddChildToVerticalBox(LabelText);
	if (!Detail.IsEmpty())
	{
		UTextBlock* DetailText = WidgetTree->ConstructWidget<UTextBlock>(UTextBlock::StaticClass());
		DetailText->SetText(Detail);
		DetailText->SetFont(FNYCUiStyle::Font(ENYCTextRole::Caption));
		DetailText->SetColorAndOpacity(FNYCUiStyle::Slate(ENYCColourRole::TextMuted));
		Inner->AddChildToVerticalBox(DetailText);
	}
	Button->AddChild(Inner);
	if (UVerticalBoxSlot* Slot = Into->AddChildToVerticalBox(Button))
	{
		Slot->SetPadding(FMargin(0.f, 0.f, 0.f, FNYCUiStyle::Space(2)));
	}
	Handlers.Add(Button, MoveTemp(OnClicked));
	Button->OnClicked.AddDynamic(this, &UNYCMenuWidget::HandleNavClicked);
	return Button;
}

void UNYCMenuWidget::HandleNavClicked()
{
	// UMG's OnClicked carries no payload, so the pressed button is found by asking each one.
	for (const TPair<TWeakObjectPtr<UButton>, TFunction<void()>>& Pair : Handlers)
	{
		if (Pair.Key.IsValid() && Pair.Key->IsPressed())
		{
			Pair.Value();
			return;
		}
	}
}

void UNYCMenuWidget::AddHeading(UVerticalBox* Into, const FText& Text)
{
	if (Into == nullptr)
	{
		return;
	}
	UTextBlock* Block = WidgetTree->ConstructWidget<UTextBlock>(UTextBlock::StaticClass());
	Block->SetText(Text);
	Block->SetFont(FNYCUiStyle::Font(ENYCTextRole::Label));
	Block->SetColorAndOpacity(FNYCUiStyle::Slate(ENYCColourRole::TextMuted));
	if (UVerticalBoxSlot* Slot = Into->AddChildToVerticalBox(Block))
	{
		Slot->SetPadding(FMargin(0.f, FNYCUiStyle::Space(3), 0.f, FNYCUiStyle::Space(1)));
	}
}

void UNYCMenuWidget::AddNote(UVerticalBox* Into, const FText& Text)
{
	if (Into == nullptr)
	{
		return;
	}
	UTextBlock* Block = WidgetTree->ConstructWidget<UTextBlock>(UTextBlock::StaticClass());
	Block->SetText(Text);
	Block->SetFont(FNYCUiStyle::Font(ENYCTextRole::Caption));
	Block->SetColorAndOpacity(FNYCUiStyle::Slate(ENYCColourRole::TextMuted));
	Block->SetAutoWrapText(true);
	Into->AddChildToVerticalBox(Block);
}

void UNYCMenuWidget::ShowPage(ENYCMenuPage Page)
{
	CurrentPage = Page;
	if (TitleText != nullptr)
	{
		TitleText->SetText(PageTitle(Page));
	}
	RebuildDetail();
}

void UNYCMenuWidget::RebuildDetail()
{
	if (DetailBox == nullptr)
	{
		return;
	}
	// Drop the handlers of the page being replaced, or a stale entry keeps answering IsPressed().
	for (int32 i = DetailBox->GetChildrenCount() - 1; i >= 0; --i)
	{
		if (UButton* Button = Cast<UButton>(DetailBox->GetChildAt(i)))
		{
			Handlers.Remove(Button);
		}
	}
	DetailBox->ClearChildren();
	switch (CurrentPage)
	{
	case ENYCMenuPage::Graphics:
		BuildGraphicsPage();
		break;
	case ENYCMenuPage::Audio:
		BuildAudioPage();
		break;
	case ENYCMenuPage::Controls:
		BuildControlsPage();
		break;
	case ENYCMenuPage::Save:
		BuildSavePage(false);
		break;
	case ENYCMenuPage::Load:
		BuildSavePage(true);
		break;
	case ENYCMenuPage::Quit:
		BuildQuitPage();
		break;
	case ENYCMenuPage::Root:
	default:
		AddRow(DetailBox, NSLOCTEXT("NYCSim", "Resume", "Resume"),
			   NSLOCTEXT("NYCSim", "ResumeHint", "Escape"),
			   [this]() { if (Owner.IsValid()) { Owner->SetMenuOpen(false); } }, true);
		AddRow(DetailBox, NSLOCTEXT("NYCSim", "QuickSaveRow", "Quick save"),
			   NSLOCTEXT("NYCSim", "QuickSaveHint", "F5"),
			   [this]() {
				   if (UNYCSaveSubsystem* Save = SaveSubsystem())
				   {
					   Status = Save->QuickSave() == ENYCSaveResult::Ok ? TEXT("Saved.") : Save->GetLastError();
				   }
			   });
		AddRow(DetailBox, NSLOCTEXT("NYCSim", "QuickLoadRow", "Quick load"),
			   NSLOCTEXT("NYCSim", "QuickLoadHint", "F9"),
			   [this]() {
				   if (UNYCSaveSubsystem* Save = SaveSubsystem())
				   {
					   Status = Save->QuickLoad() == ENYCSaveResult::Ok ? TEXT("Loaded.") : Save->GetLastError();
					   if (Owner.IsValid()) { Owner->SetMenuOpen(false); }
				   }
			   });
		break;
	}
}

void UNYCMenuWidget::BuildGraphicsPage()
{
	UGameUserSettings* Settings = GEngine != nullptr ? GEngine->GetGameUserSettings() : nullptr;
	if (Settings == nullptr)
	{
		AddNote(DetailBox, NSLOCTEXT("NYCSim", "NoSettings", "Graphics settings are unavailable."));
		return;
	}
	AddHeading(DetailBox, NSLOCTEXT("NYCSim", "Quality", "Quality"));
	static const TCHAR* const Names[] = {TEXT("Low"), TEXT("Medium"), TEXT("High"), TEXT("Epic")};
	for (int32 Level = 0; Level < 4; ++Level)
	{
		const bool bCurrent = Settings->GetOverallScalabilityLevel() == Level;
		AddRow(DetailBox, FText::FromString(Names[Level]),
			   bCurrent ? NSLOCTEXT("NYCSim", "Current", "current") : FText::GetEmpty(),
			   [this, Level]() {
				   if (UGameUserSettings* S = GEngine ? GEngine->GetGameUserSettings() : nullptr)
				   {
					   S->SetOverallScalabilityLevel(Level);
					   S->ApplySettings(false);
					   S->SaveSettings();
					   Status = TEXT("Applied.");
					   RebuildDetail();
				   }
			   }, bCurrent);
	}
	AddHeading(DetailBox, NSLOCTEXT("NYCSim", "Vsync", "Vertical sync"));
	AddRow(DetailBox, Settings->IsVSyncEnabled() ? NSLOCTEXT("NYCSim", "VsyncOn", "On")
												 : NSLOCTEXT("NYCSim", "VsyncOff", "Off"),
		   FText::GetEmpty(),
		   [this]() {
			   if (UGameUserSettings* S = GEngine ? GEngine->GetGameUserSettings() : nullptr)
			   {
				   S->SetVSyncEnabled(!S->IsVSyncEnabled());
				   S->ApplySettings(false);
				   S->SaveSettings();
				   RebuildDetail();
			   }
		   });
	// The number that decides whether this runs at all on an 8 GB card. Surfacing it turns a
	// limitation into something the player can act on rather than something they only feel.
	const UNYCSimWorldSettings& World = UNYCSimWorldSettings::Get();
	AddHeading(DetailBox, NSLOCTEXT("NYCSim", "Budget", "Streaming budget"));
	AddNote(DetailBox, FText::FromString(FString::Printf(
		TEXT("GPU %d MB, CPU %d MB. Tiles load within %.0f m and unload past %.0f m."),
		World.GpuBudgetMegabytes, World.CpuBudgetMegabytes,
		World.LoadRadiusL0Metres, World.UnloadRadiusL0Metres)));
}

void UNYCMenuWidget::BuildAudioPage()
{
	const UWorld* World = GetWorld();
	UNYCRadioSubsystem* Radio = World != nullptr ? World->GetSubsystem<UNYCRadioSubsystem>() : nullptr;
	AddHeading(DetailBox, NSLOCTEXT("NYCSim", "Radio", "Radio"));
	if (Radio == nullptr || Radio->GetStationCount() == 0)
	{
		AddNote(DetailBox, NSLOCTEXT("NYCSim", "NoStations",
			"No stations are loaded. The station index is Content/NYCSim/Audio/stations.json."));
		return;
	}
	for (int32 i = 0; i < Radio->GetStationCount(); ++i)
	{
		FNYCRadioStation Station;
		if (!Radio->GetStation(i, Station))
		{
			continue;
		}
		const bool bCurrent = Radio->GetCurrentStationIndex() == i;
		AddRow(DetailBox, FText::FromString(Station.Name),
			   FText::FromString(FString::Printf(TEXT("%.1f FM"), Station.FrequencyMhz)),
			   [this, i]() {
				   const UWorld* W = GetWorld();
				   if (UNYCRadioSubsystem* R = W ? W->GetSubsystem<UNYCRadioSubsystem>() : nullptr)
				   {
					   R->SetStation(i);
					   RebuildDetail();
				   }
			   }, bCurrent);
	}
	AddNote(DetailBox, FText::FromString(Radio->GetAttributionText()));
}

void UNYCMenuWidget::BuildControlsPage()
{
	AddHeading(DetailBox, NSLOCTEXT("NYCSim", "Driving", "Driving"));
	static const TCHAR* const Rows[][2] = {
		{TEXT("Throttle / brake"), TEXT("W / S, right and left trigger")},
		{TEXT("Steer"), TEXT("A / D, left stick")},
		{TEXT("Handbrake"), TEXT("Space")},
		{TEXT("Indicators"), TEXT("Q / E, hazards Z")},
		{TEXT("Headlights"), TEXT("L, fog lights K")},
		{TEXT("Wipers"), TEXT("V")},
		{TEXT("Camera"), TEXT("C, photo mode P")},
		{TEXT("Radio"), TEXT("[ and ]")},
		{TEXT("Leave the car"), TEXT("F")},
		{TEXT("Map"), TEXT("M, search Tab")},
		{TEXT("Menu"), TEXT("Escape")},
		{TEXT("Quick save / load"), TEXT("F5 / F9")},
	};
	for (const auto& Row : Rows)
	{
		AddRow(DetailBox, FText::FromString(Row[0]), FText::FromString(Row[1]), []() {});
	}
	AddNote(DetailBox, NSLOCTEXT("NYCSim", "Rebind",
		"Rebinding is not in this build. The bindings above are built in C++ in NYCInputConfig."));
}

void UNYCMenuWidget::BuildSavePage(bool bLoading)
{
	UNYCSaveSubsystem* Save = SaveSubsystem();
	if (Save == nullptr)
	{
		AddNote(DetailBox, NSLOCTEXT("NYCSim", "NoSaveSub", "The save subsystem is unavailable."));
		return;
	}
	const TArray<FNYCSaveSlotInfo> Slots = Save->EnumerateSlots();
	if (bLoading && Slots.Num() == 0)
	{
		AddNote(DetailBox, NSLOCTEXT("NYCSim", "NoSaves", "There are no saved games yet."));
		return;
	}
	for (int32 i = 0; i < UNYCSaveSubsystem::NumSlots; ++i)
	{
		const FString Name = UNYCSaveSubsystem::SlotNameForIndex(i);
		const FNYCSaveSlotInfo* Existing = Slots.FindByPredicate(
			[&Name](const FNYCSaveSlotInfo& S) { return S.SlotName == Name; });
		if (bLoading && Existing == nullptr)
		{
			continue;
		}
		FText Detail = NSLOCTEXT("NYCSim", "EmptySlot", "empty");
		if (Existing != nullptr)
		{
			Detail = FText::FromString(FString::Printf(
				TEXT("%s  %s  %.0f km%s"),
				*Existing->SavedAtUtc.ToString(TEXT("%Y-%m-%d %H:%M")),
				Existing->Street.IsEmpty() ? TEXT("somewhere in the city") : *Existing->Street,
				Existing->OdometerKm,
				Existing->bFromThisBuild ? TEXT("") : TEXT("  (another build)")));
		}
		AddRow(DetailBox, FText::FromString(FString::Printf(TEXT("Slot %d"), i + 1)), Detail,
			   [this, Name, bLoading]() {
				   UNYCSaveSubsystem* S = SaveSubsystem();
				   if (S == nullptr)
				   {
					   return;
				   }
				   if (bLoading)
				   {
					   Status = S->LoadFromSlot(Name) == ENYCSaveResult::Ok ? TEXT("Loaded.") : S->GetLastError();
					   if (Owner.IsValid()) { Owner->SetMenuOpen(false); }
				   }
				   else
				   {
					   Status = S->SaveToSlot(Name, Name) == ENYCSaveResult::Ok ? TEXT("Saved.") : S->GetLastError();
					   RebuildDetail();
				   }
			   });
	}
}

void UNYCMenuWidget::BuildQuitPage()
{
	AddNote(DetailBox, NSLOCTEXT("NYCSim", "QuitWarning",
		"Anything since the last save is lost."));
	AddRow(DetailBox, NSLOCTEXT("NYCSim", "SaveAndQuit", "Save and quit"), FText::GetEmpty(),
		   [this]() {
			   if (UNYCSaveSubsystem* Save = SaveSubsystem())
			   {
				   Save->QuickSave();
			   }
			   if (Owner.IsValid())
			   {
				   Owner->RequestQuit();
			   }
		   }, true);
	AddRow(DetailBox, NSLOCTEXT("NYCSim", "QuitNow", "Quit without saving"), FText::GetEmpty(),
		   [this]() { if (Owner.IsValid()) { Owner->RequestQuit(); } });
	AddRow(DetailBox, NSLOCTEXT("NYCSim", "Back", "Back"), FText::GetEmpty(),
		   [this]() { ShowPage(ENYCMenuPage::Root); });
}
