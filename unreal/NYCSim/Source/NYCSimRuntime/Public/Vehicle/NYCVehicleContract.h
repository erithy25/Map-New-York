// The vehicle mesh naming contract between Blender (blender/vehicles/**) and Unreal.
//
// Everything the runtime binds to on a vehicle mesh is found by NAME, never by index, so the Blender side can add
// or reorder geometry without breaking the game. Two namespaces are involved:
//
//   * BONE / SOCKET names on the skeletal mesh — the parts that move (wheels, doors, wipers, windows, mirrors,
//     the steering wheel) plus the attachment points the runtime needs (camera positions, exhaust, plate).
//   * MATERIAL SLOT names — the surfaces the runtime drives (emissive lamp slots, gauges, screens, mirror glass,
//     number plate, damage regions).
//
// Blender writes these names (see blender/vehicles/vlib/materials.py, whose helpers name the material after the
// slot). This header is the single authority; the Blender vehicle build script and the UE import script both
// validate against the lists below, and UNYCVehicleContract::Validate() reports anything missing at runtime with
// the exact name it looked for.
//
// Naming rules
//   * suffix `_L` / `_R`  — left / right in the vehicle's own frame (driver's left when seated).
//   * suffix `_F` / `_R`  — front / rear axle. Wheels use `Wheel_FL, Wheel_FR, Wheel_RL, Wheel_RR`.
//   * `UCX_<part>_NN`     — convex collision hulls, consumed by the importer, never by gameplay.
#pragma once

#include "CoreMinimal.h"
#include "NYCVehicleContract.generated.h"

class USkeletalMeshComponent;
class UStaticMeshComponent;
class UMeshComponent;

/** Wheels, in the order the Chaos wheel setup expects them (front axle first, left before right). */
namespace NYCVehicleBones
{
	inline const TCHAR* const Body = TEXT("Body");
	inline const TCHAR* const WheelFrontLeft = TEXT("Wheel_FL");
	inline const TCHAR* const WheelFrontRight = TEXT("Wheel_FR");
	inline const TCHAR* const WheelRearLeft = TEXT("Wheel_RL");
	inline const TCHAR* const WheelRearRight = TEXT("Wheel_RR");

	inline const TCHAR* const DoorFrontLeft = TEXT("Door_FL");
	inline const TCHAR* const DoorFrontRight = TEXT("Door_FR");
	inline const TCHAR* const DoorRearLeft = TEXT("Door_RL");
	inline const TCHAR* const DoorRearRight = TEXT("Door_RR");
	inline const TCHAR* const Hood = TEXT("Door_Hood");
	inline const TCHAR* const Trunk = TEXT("Door_Trunk");
	inline const TCHAR* const FuelFlap = TEXT("Door_FuelFlap");

	inline const TCHAR* const SteeringWheel = TEXT("SteeringWheel");
	inline const TCHAR* const WiperLeft = TEXT("Wiper_L");
	inline const TCHAR* const WiperRight = TEXT("Wiper_R");
	inline const TCHAR* const WiperRear = TEXT("Wiper_Rear");

	inline const TCHAR* const WindowFrontLeft = TEXT("Window_FL");
	inline const TCHAR* const WindowFrontRight = TEXT("Window_FR");
	inline const TCHAR* const WindowRearLeft = TEXT("Window_RL");
	inline const TCHAR* const WindowRearRight = TEXT("Window_RR");

	inline const TCHAR* const MirrorLeft = TEXT("Mirror_L");
	inline const TCHAR* const MirrorRight = TEXT("Mirror_R");
	inline const TCHAR* const MirrorInterior = TEXT("Mirror_Interior");

	inline const TCHAR* const NeedleSpeed = TEXT("Needle_Speed");
	inline const TCHAR* const NeedleRpm = TEXT("Needle_RPM");
	inline const TCHAR* const NeedleFuel = TEXT("Needle_Fuel");
	inline const TCHAR* const NeedleTemp = TEXT("Needle_Temp");
	inline const TCHAR* const GearSelector = TEXT("GearSelector");
	inline const TCHAR* const TurnStalk = TEXT("Stalk_Turn");
	inline const TCHAR* const WiperStalk = TEXT("Stalk_Wiper");

	// Sockets (attachment points; may be sockets on the mesh rather than bones).
	inline const TCHAR* const SocketDriverSeat = TEXT("SKT_DriverSeat");
	inline const TCHAR* const SocketPassengerSeat = TEXT("SKT_PassengerSeat");
	inline const TCHAR* const SocketDriverEntry = TEXT("SKT_DriverEntry");
	inline const TCHAR* const SocketCameraChase = TEXT("SKT_CamChase");
	inline const TCHAR* const SocketCameraHood = TEXT("SKT_CamHood");
	inline const TCHAR* const SocketCameraInterior = TEXT("SKT_CamInterior");
	inline const TCHAR* const SocketCameraBumper = TEXT("SKT_CamBumper");
	inline const TCHAR* const SocketExhaustLeft = TEXT("SKT_Exhaust_L");
	inline const TCHAR* const SocketExhaustRight = TEXT("SKT_Exhaust_R");
	inline const TCHAR* const SocketEngineBay = TEXT("SKT_EngineBay");
	inline const TCHAR* const SocketPlateFront = TEXT("SKT_Plate_F");
	inline const TCHAR* const SocketPlateRear = TEXT("SKT_Plate_R");
	inline const TCHAR* const SocketHorn = TEXT("SKT_Horn");
	inline const TCHAR* const SocketRoofLight = TEXT("SKT_RoofLight");
	inline const TCHAR* const SocketDestinationSign = TEXT("SKT_DestSign");
}

/** Material slot names. Each is a distinct slot on the mesh so the runtime can create a dynamic instance for it. */
namespace NYCVehicleSlots
{
	inline const TCHAR* const BodyPaint = TEXT("BODY_PAINT");
	inline const TCHAR* const Glass = TEXT("GLASS");
	inline const TCHAR* const MirrorGlass = TEXT("MIRROR_GLASS");
	inline const TCHAR* const PlateFace = TEXT("PLATE_FACE");

	// Emissive lamp slots. Every one is driven through the scalar parameter NYCVehicleParams::Emissive.
	inline const TCHAR* const HeadLeft = TEXT("LIGHT_HEAD_L");
	inline const TCHAR* const HeadRight = TEXT("LIGHT_HEAD_R");
	inline const TCHAR* const HighBeamLeft = TEXT("LIGHT_HIGH_L");
	inline const TCHAR* const HighBeamRight = TEXT("LIGHT_HIGH_R");
	inline const TCHAR* const DrlLeft = TEXT("LIGHT_DRL_L");
	inline const TCHAR* const DrlRight = TEXT("LIGHT_DRL_R");
	inline const TCHAR* const FogLeft = TEXT("LIGHT_FOG_L");
	inline const TCHAR* const FogRight = TEXT("LIGHT_FOG_R");
	inline const TCHAR* const TailLeft = TEXT("LIGHT_TAIL_L");
	inline const TCHAR* const TailRight = TEXT("LIGHT_TAIL_R");
	inline const TCHAR* const BrakeLeft = TEXT("LIGHT_BRAKE_L");
	inline const TCHAR* const BrakeRight = TEXT("LIGHT_BRAKE_R");
	inline const TCHAR* const BrakeCentre = TEXT("LIGHT_BRAKE_C");
	inline const TCHAR* const ReverseLeft = TEXT("LIGHT_REVERSE_L");
	inline const TCHAR* const ReverseRight = TEXT("LIGHT_REVERSE_R");
	inline const TCHAR* const IndicatorFrontLeft = TEXT("LIGHT_IND_FL");
	inline const TCHAR* const IndicatorFrontRight = TEXT("LIGHT_IND_FR");
	inline const TCHAR* const IndicatorRearLeft = TEXT("LIGHT_IND_RL");
	inline const TCHAR* const IndicatorRearRight = TEXT("LIGHT_IND_RR");
	inline const TCHAR* const IndicatorSideLeft = TEXT("LIGHT_IND_SL");
	inline const TCHAR* const IndicatorSideRight = TEXT("LIGHT_IND_SR");
	inline const TCHAR* const PlateLight = TEXT("LIGHT_PLATE");
	inline const TCHAR* const InteriorLight = TEXT("LIGHT_INTERIOR");
	inline const TCHAR* const DashBacklight = TEXT("LIGHT_DASH");
	inline const TCHAR* const TaxiRoofLight = TEXT("LIGHT_TAXI_ROOF");
	inline const TCHAR* const EmergencyBarLeft = TEXT("LIGHT_EMERG_L");
	inline const TCHAR* const EmergencyBarRight = TEXT("LIGHT_EMERG_R");

	// Instrument and screen slots (render targets / material parameters).
	inline const TCHAR* const GaugeSpeed = TEXT("GAUGE_SPEED");
	inline const TCHAR* const GaugeRpm = TEXT("GAUGE_RPM");
	inline const TCHAR* const GaugeFuel = TEXT("GAUGE_FUEL");
	inline const TCHAR* const ScreenCentre = TEXT("SCREEN_CENTER");
	inline const TCHAR* const ScreenCluster = TEXT("SCREEN_CLUSTER");
	inline const TCHAR* const DestinationSign = TEXT("SIGN_DEST");

	// Damage regions: the deformation mask and crack overlay are driven per region.
	inline const TCHAR* const DamageFront = TEXT("DMG_FRONT");
	inline const TCHAR* const DamageRear = TEXT("DMG_REAR");
	inline const TCHAR* const DamageLeft = TEXT("DMG_LEFT");
	inline const TCHAR* const DamageRight = TEXT("DMG_RIGHT");
	inline const TCHAR* const DamageRoof = TEXT("DMG_ROOF");
}

/** Material scalar/vector parameter names the runtime writes on the slots above. */
namespace NYCVehicleParams
{
	inline const TCHAR* const Emissive = TEXT("EmissiveScale");
	inline const TCHAR* const EmissiveColor = TEXT("EmissiveColor");
	inline const TCHAR* const Broken = TEXT("Broken");          ///< 0..1 lamp lens breakage
	inline const TCHAR* const GaugeValue = TEXT("GaugeValue");  ///< 0..1 normalised needle / arc position
	inline const TCHAR* const CrackAmount = TEXT("CrackAmount");
	inline const TCHAR* const DentAmount = TEXT("DentAmount");
	inline const TCHAR* const Wetness = TEXT("Wetness");
	inline const TCHAR* const Dirt = TEXT("Dirt");
	inline const TCHAR* const ScreenTexture = TEXT("ScreenTexture");
	inline const TCHAR* const PlateTexture = TEXT("PlateTexture");
	inline const TCHAR* const MirrorTexture = TEXT("MirrorTexture");
	inline const TCHAR* const PaintColor = TEXT("PaintColor");
	inline const TCHAR* const WindowDown = TEXT("WindowDown");
}

/** Morph target names for damage deformation (one per DMG_ region, authored in Blender as shape keys). */
namespace NYCVehicleMorphs
{
	inline const TCHAR* const DentFront = TEXT("DMG_FRONT_dent");
	inline const TCHAR* const DentRear = TEXT("DMG_REAR_dent");
	inline const TCHAR* const DentLeft = TEXT("DMG_LEFT_dent");
	inline const TCHAR* const DentRight = TEXT("DMG_RIGHT_dent");
	inline const TCHAR* const DentRoof = TEXT("DMG_ROOF_dent");
}

/** Damage regions in the order the runtime indexes them. */
UENUM(BlueprintType)
enum class ENYCDamageRegion : uint8
{
	Front = 0,
	Rear,
	Left,
	Right,
	Roof,
	Count UMETA(Hidden)
};

/** Result of checking a mesh against the contract. */
USTRUCT(BlueprintType)
struct NYCSIMRUNTIME_API FNYCVehicleContractReport
{
	GENERATED_BODY()

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Vehicle")
	TArray<FString> MissingBones;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Vehicle")
	TArray<FString> MissingSockets;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Vehicle")
	TArray<FString> MissingSlots;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Vehicle")
	int32 FoundBones = 0;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Vehicle")
	int32 FoundSlots = 0;

	bool IsComplete() const
	{
		return MissingBones.Num() == 0 && MissingSockets.Num() == 0 && MissingSlots.Num() == 0;
	}

	FString ToText() const;
};

/** Static helpers shared by the player vehicle, the traffic actors and the editor validation commandlet. */
class NYCSIMRUNTIME_API FNYCVehicleContract
{
public:
	/** Bones the runtime requires on any drivable vehicle (missing ones are reported, never assumed). */
	static const TArray<FName>& RequiredBones();
	/** Bones that are used when present but are optional (rear wiper, fuel flap, taxi roof light...). */
	static const TArray<FName>& OptionalBones();
	static const TArray<FName>& RequiredSockets();
	static const TArray<FName>& OptionalSockets();
	/** Material slots the runtime drives; missing ones simply disable that feature and are reported. */
	static const TArray<FName>& LightSlots();
	static const TArray<FName>& InstrumentSlots();
	static const TArray<FName>& DamageSlots();

	static FName WheelBone(int32 WheelIndex);
	static FName DoorBone(int32 DoorIndex);
	static FName DamageSlot(ENYCDamageRegion Region);
	static FName DamageMorph(ENYCDamageRegion Region);

	/** True when `Name` is a `UCX_` collision hull that must never be rendered or bound to. */
	static bool IsCollisionName(FName Name);

	/** Checks a mesh component against the contract. Never modifies anything. */
	static FNYCVehicleContractReport Validate(const USkeletalMeshComponent* Mesh);

	/** Index of a named material slot, or INDEX_NONE. */
	static int32 SlotIndex(const UMeshComponent* Mesh, FName SlotName);
};
