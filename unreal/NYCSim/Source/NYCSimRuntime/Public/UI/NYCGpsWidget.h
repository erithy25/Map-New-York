// The GPS screen: the minimap, the turn card, the ETA strip and the destination search.
//
// Built entirely in C++ — RebuildWidget() populates the widget tree with a canvas, the minimap, and the text
// blocks, so the same class works on the car's centre screen (through a UWidgetComponent) and on the HUD without
// a UMG asset existing. Text is Overpass when the font asset is present (the same face the street signs use) and
// the engine's default otherwise.
#pragma once

#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "NYCGpsWidget.generated.h"

class UNYCMinimapWidget;
class UCanvasPanel;
class UEditableTextBox;
class UTextBlock;
class UVerticalBox;

UCLASS()
class NYCSIMRUNTIME_API UNYCGpsWidget : public UUserWidget
{
	GENERATED_BODY()

public:
	UNYCGpsWidget(const FObjectInitializer& ObjectInitializer);

	virtual void NativeConstruct() override;
	virtual void NativeTick(const FGeometry& MyGeometry, float InDeltaTime) override;

	/** Opens/closes the destination search panel. */
	UFUNCTION(BlueprintCallable, Category = "NYCSim|UI")
	void ToggleSearch();

	UFUNCTION(BlueprintPure, Category = "NYCSim|UI")
	bool IsSearchOpen() const { return bSearchOpen; }

	/** Runs the search and repopulates the result list. */
	UFUNCTION(BlueprintCallable, Category = "NYCSim|UI")
	void RunSearch(const FString& Query);

	/** Routes to the n-th result of the last search. */
	UFUNCTION(BlueprintCallable, Category = "NYCSim|UI")
	bool ChooseResult(int32 Index);

	UFUNCTION(BlueprintCallable, Category = "NYCSim|UI")
	void ZoomIn();

	UFUNCTION(BlueprintCallable, Category = "NYCSim|UI")
	void ZoomOut();

	UFUNCTION(BlueprintCallable, Category = "NYCSim|UI")
	void ToggleNorthUp();

protected:
	virtual TSharedRef<SWidget> RebuildWidget() override;

private:
	void BuildTree();
	void UpdateTexts();
	static FString FormatDistance(float Metres);
	static FString FormatEta(float Seconds);
	static FString ManoeuvreGlyph(uint8 Manoeuvre);

	UPROPERTY(Transient)
	TObjectPtr<UCanvasPanel> Root;

	UPROPERTY(Transient)
	TObjectPtr<UNYCMinimapWidget> Minimap;

	UPROPERTY(Transient)
	TObjectPtr<UTextBlock> TurnGlyph;

	UPROPERTY(Transient)
	TObjectPtr<UTextBlock> TurnText;

	UPROPERTY(Transient)
	TObjectPtr<UTextBlock> TurnDistance;

	UPROPERTY(Transient)
	TObjectPtr<UTextBlock> EtaText;

	UPROPERTY(Transient)
	TObjectPtr<UTextBlock> StreetText;

	UPROPERTY(Transient)
	TObjectPtr<UEditableTextBox> SearchBox;

	UPROPERTY(Transient)
	TObjectPtr<UVerticalBox> ResultsBox;

	UPROPERTY(Transient)
	TArray<TObjectPtr<UTextBlock>> ResultLines;

	TArray<FVector> LastResultLocations;
	bool bSearchOpen = false;
	bool bTreeBuilt = false;
	float RefreshAccumulator = 0.f;
};
