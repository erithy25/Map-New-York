// The working dashboard: analogue needles, the emissive gauge faces, the warning lamps and the centre screen.
//
// The needles are real bones (Needle_Speed / Needle_RPM / Needle_Fuel / Needle_Temp) driven through
// UNYCVehicleAnimInstance with the sweep geometry of the real cluster; the gauge faces additionally receive a
// normalised GaugeValue so a shader can light the arc. The centre screen is a UWidgetComponent placed on the
// SKT_Screen socket rendering the GPS widget, and its render target is also pushed into the SCREEN_CENTER
// material so the glass reads correctly from outside the car.
//
// Needle physics: a real air-core gauge is a second-order system. The speedometer is critically damped with a
// 0.25 s time constant, the tachometer is faster (0.12 s) and the fuel/temperature gauges are heavily damped
// (2.5 s) so they do not swing with the tank. Sweep ranges are the production ones: speed 0-160 mph over 240°,
// tacho 0-7000 rpm over 220°, fuel and temperature 0-1 over 90°.
#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "NYCVehicleDashboardComponent.generated.h"

class UMaterialInstanceDynamic;
class UMeshComponent;
class UNYCVehicleAnimInstance;
class UNYCVehicleMovementComponent;
class UTextureRenderTarget2D;
class UUserWidget;
class UWidgetComponent;

/** Warning lamps that the cluster can show; drawn by the shader from a bitmask. */
UENUM(BlueprintType)
enum class ENYCWarningLamp : uint8
{
	None = 0,
	CheckEngine = 1,
	LowFuel = 2,
	Battery = 4,
	Brake = 8,
	Abs = 16,
	TractionControl = 32,
	SeatBelt = 64,
	DoorAjar = 128
};
ENUM_CLASS_FLAGS(ENYCWarningLamp);

UCLASS(ClassGroup = (NYCSim), meta = (BlueprintSpawnableComponent))
class NYCSIMRUNTIME_API UNYCVehicleDashboardComponent : public UActorComponent
{
	GENERATED_BODY()

public:
	UNYCVehicleDashboardComponent();

	virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction) override;

	/** Binds to the vehicle mesh, its movement component and its anim instance. */
	UFUNCTION(BlueprintCallable, Category = "NYCSim|Dashboard")
	void Initialise(UMeshComponent* InMesh, UNYCVehicleMovementComponent* InMovement);

	/** Creates the centre-screen widget component on SKT_Screen and returns it (nullptr when the socket is absent). */
	UFUNCTION(BlueprintCallable, Category = "NYCSim|Dashboard")
	UWidgetComponent* CreateCentreScreen(TSubclassOf<UUserWidget> WidgetClass);

	UFUNCTION(BlueprintCallable, Category = "NYCSim|Dashboard")
	void SetWarningLamps(int32 LampMask) { WarningMask = LampMask; }

	UFUNCTION(BlueprintPure, Category = "NYCSim|Dashboard")
	int32 GetWarningLamps() const { return WarningMask; }

	/** Gear letter shown on the cluster: P R N D. */
	UFUNCTION(BlueprintPure, Category = "NYCSim|Dashboard")
	FString GetGearText() const;

	/** Odometer in miles; persists for the session and is shown on the cluster. */
	UFUNCTION(BlueprintPure, Category = "NYCSim|Dashboard")
	float GetOdometerMiles() const { return OdometerMiles; }

	UFUNCTION(BlueprintPure, Category = "NYCSim|Dashboard")
	float GetTripMiles() const { return TripMiles; }

	UFUNCTION(BlueprintCallable, Category = "NYCSim|Dashboard")
	void ResetTrip() { TripMiles = 0.f; }

	/** Instantaneous consumption in miles per US gallon, damped over 5 s like the real readout. */
	UFUNCTION(BlueprintPure, Category = "NYCSim|Dashboard")
	float GetInstantMpg() const { return InstantMpg; }

	/** Cluster / centre-screen backlight 0..1 (the lights component drives the dash slot from this). */
	UFUNCTION(BlueprintPure, Category = "NYCSim|Dashboard")
	float GetBacklight() const { return Backlight; }

	UFUNCTION(BlueprintCallable, Category = "NYCSim|Dashboard")
	void SetBacklight(float Value01);

	// Production sweep geometry.
	UPROPERTY(EditAnywhere, Category = "NYCSim|Dashboard")
	float SpeedoMaxMph = 160.f;

	UPROPERTY(EditAnywhere, Category = "NYCSim|Dashboard")
	float SpeedoSweepDeg = 240.f;

	UPROPERTY(EditAnywhere, Category = "NYCSim|Dashboard")
	float TachoMaxRpm = 7000.f;

	UPROPERTY(EditAnywhere, Category = "NYCSim|Dashboard")
	float TachoSweepDeg = 220.f;

	UPROPERTY(EditAnywhere, Category = "NYCSim|Dashboard")
	float SmallGaugeSweepDeg = 90.f;

private:
	void UpdateNeedles(float DeltaTime);
	void UpdateGaugeMaterials();
	void UpdateTrip(float DeltaTime);

	UPROPERTY(Transient)
	TObjectPtr<UMeshComponent> Mesh;

	UPROPERTY(Transient)
	TObjectPtr<UNYCVehicleMovementComponent> Movement;

	UPROPERTY(Transient)
	TObjectPtr<UNYCVehicleAnimInstance> AnimInstance;

	UPROPERTY(Transient)
	TObjectPtr<UMaterialInstanceDynamic> GaugeSpeedMaterial;

	UPROPERTY(Transient)
	TObjectPtr<UMaterialInstanceDynamic> GaugeRpmMaterial;

	UPROPERTY(Transient)
	TObjectPtr<UMaterialInstanceDynamic> GaugeFuelMaterial;

	UPROPERTY(Transient)
	TObjectPtr<UMaterialInstanceDynamic> ScreenCentreMaterial;

	UPROPERTY(Transient)
	TObjectPtr<UMaterialInstanceDynamic> ScreenClusterMaterial;

	UPROPERTY(Transient)
	TObjectPtr<UWidgetComponent> CentreScreen;

	// Damped needle state (value, velocity) for the second-order gauge model.
	float SpeedNeedle = 0.f;
	float SpeedNeedleVel = 0.f;
	float RpmNeedle = 0.f;
	float RpmNeedleVel = 0.f;
	float FuelNeedle = 0.f;
	float TempNeedle = 0.f;

	float OdometerMiles = 0.f;
	float TripMiles = 0.f;
	float InstantMpg = 0.f;
	float LastFuelLitres = -1.f;
	float MpgAccumulator = 0.f;
	float MpgWindow = 0.f;
	float Backlight = 0.f;
	int32 WarningMask = 0;
};
