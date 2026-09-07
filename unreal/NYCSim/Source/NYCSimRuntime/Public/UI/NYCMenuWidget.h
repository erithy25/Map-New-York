// The pause menu: one widget, seven pages, no content assets.
//
// Left nav, right detail, over a blur of the paused city. Everything it draws comes from
// FNYCUiStyle, so it is the same object as the driving HUD rather than a second interface that
// happens to be in the same game.
//
// There is no separate main-menu map. DefaultEngine.ini names /Game/NYCSim/Maps/Transition and
// nothing creates it; more to the point, loading a second map to show a background costs an 8 GB
// card more than the background is worth. The game boots into the city and opens this over it.
#pragma once

#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "Save/NYCSaveGame.h"
#include "NYCMenuWidget.generated.h"

class ANYCPlayerController;
class UBorder;
class UCanvasPanel;
class UNYCSaveSubsystem;
class UTextBlock;
class UVerticalBox;

UENUM(BlueprintType)
enum class ENYCMenuPage : uint8
{
	Root = 0,
	Graphics,
	Audio,
	Controls,
	Save,
	Load,
	Quit,
};

UCLASS()
class NYCSIMRUNTIME_API UNYCMenuWidget : public UUserWidget
{
	GENERATED_BODY()

public:
	UNYCMenuWidget(const FObjectInitializer& ObjectInitializer);

	virtual void NativeConstruct() override;
	virtual void NativeTick(const FGeometry& MyGeometry, float InDeltaTime) override;

	UFUNCTION(BlueprintCallable, Category = "NYCSim|UI")
	void SetOwningController(ANYCPlayerController* Controller) { Owner = Controller; }

	UFUNCTION(BlueprintCallable, Category = "NYCSim|UI")
	void ShowPage(ENYCMenuPage Page);

	UFUNCTION(BlueprintCallable, Category = "NYCSim|UI")
	void ShowRoot() { ShowPage(ENYCMenuPage::Root); }

	UFUNCTION(BlueprintPure, Category = "NYCSim|UI")
	ENYCMenuPage GetPage() const { return CurrentPage; }

	/** The pages, in nav order. Public so the nav and a test agree on one list. */
	static const TArray<ENYCMenuPage>& NavPages();
	static FText PageTitle(ENYCMenuPage Page);

protected:
	virtual TSharedRef<SWidget> RebuildWidget() override;

private:
	void BuildTree();
	void RebuildDetail();
	void BuildGraphicsPage();
	void BuildAudioPage();
	void BuildControlsPage();
	void BuildSavePage(bool bLoading);
	void BuildQuitPage();
	UNYCSaveSubsystem* SaveSubsystem() const;

	/** A styled button. The only button factory in the menu, so they cannot drift apart. */
	class UButton* AddRow(UVerticalBox* Into, const FText& Label, const FText& Detail,
						  TFunction<void()> OnClicked, bool bAccent = false);
	void AddHeading(UVerticalBox* Into, const FText& Text);
	void AddNote(UVerticalBox* Into, const FText& Text);

	UFUNCTION()
	void HandleNavClicked();

	UPROPERTY(Transient)
	TObjectPtr<UCanvasPanel> Root;

	UPROPERTY(Transient)
	TObjectPtr<UVerticalBox> NavBox;

	UPROPERTY(Transient)
	TObjectPtr<UVerticalBox> DetailBox;

	UPROPERTY(Transient)
	TObjectPtr<UTextBlock> TitleText;

	UPROPERTY(Transient)
	TObjectPtr<UTextBlock> StatusText;

	UPROPERTY(Transient)
	TWeakObjectPtr<ANYCPlayerController> Owner;

	/** Handlers by button, because UMG's OnClicked carries no payload. */
	TMap<TWeakObjectPtr<class UButton>, TFunction<void()>> Handlers;

	ENYCMenuPage CurrentPage = ENYCMenuPage::Root;
	bool bTreeBuilt = false;
	float OpenSeconds = 0.f;
	FString Status;
};
