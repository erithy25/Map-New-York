// Everything the player's car sounds like.
//
// Six sources sit on the car: engine (engine bay), tyres (rear axle), wind (cabin), rain on the roof (cabin),
// wipers (windscreen) and the horn (front bumper). Each is a UNYCProceduralSourceComponent unless a MetaSound
// source asset exists at the configured path, in which case a UAudioComponent playing that MetaSound is used and
// driven through the same parameter names — the swap is invisible to everything above this component.
//
// The component also carries the events the rest of the car raises: the indicator relay click, the wiper sweep,
// a collision, and the head unit's station changes.
#pragma once

#include "CoreMinimal.h"
#include "Components/SceneComponent.h"
#include "NYCVehicleAudioComponent.generated.h"

class UAudioComponent;
class UNYCProceduralSourceComponent;
class UNYCVehicleBodyComponent;
class UNYCVehicleLightsComponent;
class UNYCVehicleMovementComponent;
class USoundBase;
class UMeshComponent;

UCLASS(ClassGroup = (NYCSim), meta = (BlueprintSpawnableComponent))
class NYCSIMRUNTIME_API UNYCVehicleAudioComponent : public USceneComponent
{
	GENERATED_BODY()

public:
	UNYCVehicleAudioComponent();

	virtual void BeginPlay() override;
	virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction) override;

	UFUNCTION(BlueprintCallable, Category = "NYCSim|Audio")
	void Initialise(UMeshComponent* InMesh, UNYCVehicleMovementComponent* InMovement, UNYCVehicleBodyComponent* InBody,
					UNYCVehicleLightsComponent* InLights);

	// ---- event handlers bound by the pawn -------------------------------------------------------------------
	UFUNCTION()
	void HandleHorn(bool bPressed);

	UFUNCTION()
	void HandleWiperSweep(float DryFactor);

	UFUNCTION()
	void HandleIndicatorRelay(bool bOn);

	UFUNCTION()
	void HandleImpact(FVector WorldLocation, float Severity, uint8 Region);

	// ---- radio ---------------------------------------------------------------------------------------------
	UFUNCTION(BlueprintCallable, Category = "NYCSim|Audio")
	void NextRadioStation();

	UFUNCTION(BlueprintCallable, Category = "NYCSim|Audio")
	void PreviousRadioStation();

	UFUNCTION(BlueprintCallable, Category = "NYCSim|Audio")
	void ToggleRadioPower();

	/** The head unit's display line, for the centre screen. */
	UFUNCTION(BlueprintPure, Category = "NYCSim|Audio")
	FString GetRadioText() const;

	/** True when a MetaSound source is being used instead of the C++ synthesiser (per source kind). */
	UFUNCTION(BlueprintPure, Category = "NYCSim|Audio")
	bool IsUsingMetaSounds() const { return bUsingMetaSounds; }

private:
	UNYCProceduralSourceComponent* MakeSource(const TCHAR* Name, uint8 Kind, FName Socket, float Gain);
	UAudioComponent* TryMakeMetaSound(const TCHAR* Name, const FSoftObjectPath& Path, FName Socket);
	void PushParameters(float DeltaTime);
	void SetMetaSoundFloat(UAudioComponent* Component, FName Parameter, float Value);

	UPROPERTY(Transient)
	TObjectPtr<UMeshComponent> Mesh;

	UPROPERTY(Transient)
	TObjectPtr<UNYCVehicleMovementComponent> Movement;

	UPROPERTY(Transient)
	TObjectPtr<UNYCVehicleBodyComponent> Body;

	UPROPERTY(Transient)
	TObjectPtr<UNYCVehicleLightsComponent> Lights;

	UPROPERTY(Transient)
	TObjectPtr<UNYCProceduralSourceComponent> EngineSource;

	UPROPERTY(Transient)
	TObjectPtr<UNYCProceduralSourceComponent> TyreSource;

	UPROPERTY(Transient)
	TObjectPtr<UNYCProceduralSourceComponent> WindSource;

	UPROPERTY(Transient)
	TObjectPtr<UNYCProceduralSourceComponent> RainSource;

	UPROPERTY(Transient)
	TObjectPtr<UNYCProceduralSourceComponent> WiperSource;

	UPROPERTY(Transient)
	TObjectPtr<UNYCProceduralSourceComponent> HornSource;

	UPROPERTY(Transient)
	TObjectPtr<UAudioComponent> EngineMetaSound;

	UPROPERTY(Transient)
	TObjectPtr<UAudioComponent> TyreMetaSound;

	UPROPERTY(Transient)
	TObjectPtr<UAudioComponent> WindMetaSound;

	UPROPERTY(Transient)
	TObjectPtr<UAudioComponent> RainMetaSound;

	UPROPERTY(Transient)
	TObjectPtr<UAudioComponent> WiperMetaSound;

	/** One-shots: indicator relay click, impacts, seat-belt chime. */
	UPROPERTY(Transient)
	TObjectPtr<UAudioComponent> OneShot;

	UPROPERTY(Transient)
	TObjectPtr<USoundBase> ImpactSound;

	UPROPERTY(Transient)
	TObjectPtr<USoundBase> GlassSound;

	bool bUsingMetaSounds = false;
	bool bInitialised = false;
};
