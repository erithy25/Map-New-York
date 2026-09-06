// UMG wrapper around SNYCMinimap.
//
// The Slate widget does the drawing; this class is the UMG-side handle that the GPS widget places on its canvas
// and feeds once per frame. It is a plain UWidget (not a UUserWidget) so it can be constructed in C++ inside any
// widget tree without an asset.
#pragma once

#include "CoreMinimal.h"
#include "Components/Widget.h"
#include "NYCMinimapWidget.generated.h"

class SNYCMinimap;

UCLASS()
class NYCSIMRUNTIME_API UNYCMinimapWidget : public UWidget
{
	GENERATED_BODY()

public:
	UNYCMinimapWidget();

	/** Pulls the player transform, the road network and the route from the world and pushes them to Slate. */
	UFUNCTION(BlueprintCallable, Category = "NYCSim|UI")
	void RefreshFromWorld();

	UFUNCTION(BlueprintCallable, Category = "NYCSim|UI")
	void SetRangeMetres(float Metres);

	UFUNCTION(BlueprintPure, Category = "NYCSim|UI")
	float GetRangeMetres() const { return RangeMetres; }

	/** Zooms one step in the sequence 60, 120, 220, 450, 900, 1800 m. */
	UFUNCTION(BlueprintCallable, Category = "NYCSim|UI")
	void ZoomIn();

	UFUNCTION(BlueprintCallable, Category = "NYCSim|UI")
	void ZoomOut();

	UFUNCTION(BlueprintCallable, Category = "NYCSim|UI")
	void SetNorthUp(bool bInNorthUp);

	UFUNCTION(BlueprintPure, Category = "NYCSim|UI")
	bool IsNorthUp() const { return bNorthUp; }

	// UWidget
	virtual void ReleaseSlateResources(bool bReleaseChildren) override;
#if WITH_EDITOR
	virtual const FText GetPaletteCategory() override;
#endif

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "NYCSim|UI", meta = (ClampMin = "40.0", ClampMax = "4000.0"))
	float RangeMetres = 220.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "NYCSim|UI")
	bool bNorthUp = false;

protected:
	virtual TSharedRef<SWidget> RebuildWidget() override;

private:
	TSharedPtr<SNYCMinimap> Minimap;
};
