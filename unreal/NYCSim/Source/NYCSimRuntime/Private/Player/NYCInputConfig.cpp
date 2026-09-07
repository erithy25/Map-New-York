#include "Player/NYCInputConfig.h"

#include "EnhancedActionKeyMapping.h"
#include "InputAction.h"
#include "InputCoreTypes.h"
#include "InputMappingContext.h"
#include "InputModifiers.h"
#include "InputTriggers.h"
#include "NYCSimRuntime.h"
#include "Player/NYCGameplaySettings.h"

namespace
{
constexpr int32 kActionCount = static_cast<int32>(ENYCInputAction::Count);
}

UInputAction* UNYCInputConfig::MakeAction(ENYCInputAction Action, uint8 ValueType, const TCHAR* Name)
{
	UInputAction* Created = NewObject<UInputAction>(this, FName(Name));
	Created->ValueType = static_cast<EInputActionValueType>(ValueType);
	Actions[static_cast<int32>(Action)] = Created;
	return Created;
}

UInputAction* UNYCInputConfig::GetAction(ENYCInputAction Action) const
{
	const int32 Index = static_cast<int32>(Action);
	return Actions.IsValidIndex(Index) ? Actions[Index] : nullptr;
}

void UNYCInputConfig::Resolve()
{
	if (bResolved)
	{
		return;
	}
	bResolved = true;
	Actions.SetNum(kActionCount);

	// The actions themselves are always created in C++: an action asset carries nothing but a value type and a
	// name, and creating them here means the bindings below and the commandlet's assets cannot disagree.
	const uint8 Boolean = static_cast<uint8>(EInputActionValueType::Boolean);
	const uint8 Axis1D = static_cast<uint8>(EInputActionValueType::Axis1D);
	const uint8 Axis2D = static_cast<uint8>(EInputActionValueType::Axis2D);

	MakeAction(ENYCInputAction::Throttle, Axis1D, TEXT("IA_Throttle"));
	MakeAction(ENYCInputAction::Brake, Axis1D, TEXT("IA_Brake"));
	MakeAction(ENYCInputAction::Steer, Axis1D, TEXT("IA_Steer"));
	MakeAction(ENYCInputAction::Handbrake, Boolean, TEXT("IA_Handbrake"));
	MakeAction(ENYCInputAction::ToggleReverse, Boolean, TEXT("IA_ToggleReverse"));
	MakeAction(ENYCInputAction::Horn, Boolean, TEXT("IA_Horn"));
	MakeAction(ENYCInputAction::CycleHeadlights, Boolean, TEXT("IA_CycleHeadlights"));
	MakeAction(ENYCInputAction::ToggleFogLights, Boolean, TEXT("IA_ToggleFogLights"));
	MakeAction(ENYCInputAction::IndicateLeft, Boolean, TEXT("IA_IndicateLeft"));
	MakeAction(ENYCInputAction::IndicateRight, Boolean, TEXT("IA_IndicateRight"));
	MakeAction(ENYCInputAction::ToggleHazards, Boolean, TEXT("IA_ToggleHazards"));
	MakeAction(ENYCInputAction::CycleWipers, Boolean, TEXT("IA_CycleWipers"));
	MakeAction(ENYCInputAction::WindowDown, Boolean, TEXT("IA_WindowDown"));
	MakeAction(ENYCInputAction::WindowUp, Boolean, TEXT("IA_WindowUp"));
	MakeAction(ENYCInputAction::CycleCamera, Boolean, TEXT("IA_CycleCamera"));
	MakeAction(ENYCInputAction::PhotoMode, Boolean, TEXT("IA_PhotoMode"));
	MakeAction(ENYCInputAction::LookAround, Axis2D, TEXT("IA_LookAround"));
	MakeAction(ENYCInputAction::RadioNext, Boolean, TEXT("IA_RadioNext"));
	MakeAction(ENYCInputAction::RadioPrevious, Boolean, TEXT("IA_RadioPrevious"));
	MakeAction(ENYCInputAction::ExitVehicle, Boolean, TEXT("IA_ExitVehicle"));
	MakeAction(ENYCInputAction::Move, Axis2D, TEXT("IA_Move"));
	MakeAction(ENYCInputAction::Jump, Boolean, TEXT("IA_Jump"));
	MakeAction(ENYCInputAction::Sprint, Boolean, TEXT("IA_Sprint"));
	MakeAction(ENYCInputAction::Crouch, Boolean, TEXT("IA_Crouch"));
	MakeAction(ENYCInputAction::Interact, Boolean, TEXT("IA_Interact"));
	MakeAction(ENYCInputAction::ToggleMap, Boolean, TEXT("IA_ToggleMap"));
	MakeAction(ENYCInputAction::SearchDestination, Boolean, TEXT("IA_SearchDestination"));
	MakeAction(ENYCInputAction::Menu, Boolean, TEXT("IA_Menu"));
	MakeAction(ENYCInputAction::QuickSave, Boolean, TEXT("IA_QuickSave"));
	MakeAction(ENYCInputAction::QuickLoad, Boolean, TEXT("IA_QuickLoad"));

	// Contexts: prefer the authored assets when the import commandlet has produced them.
	const UNYCGameplaySettings& Settings = UNYCGameplaySettings::Get();
	DrivingContext = Cast<UInputMappingContext>(Settings.DrivingMappingContext.TryLoad());
	OnFootContext = Cast<UInputMappingContext>(Settings.OnFootMappingContext.TryLoad());
	CommonContext = Cast<UInputMappingContext>(Settings.CommonMappingContext.TryLoad());
	bFromAssets = DrivingContext != nullptr && OnFootContext != nullptr && CommonContext != nullptr;

	if (!bFromAssets)
	{
		UE_LOG(LogNYCSim, Log,
			   TEXT("Input: mapping-context assets not found; building the documented default bindings in C++."));
		BuildDefaultContexts();
	}
	else
	{
		UE_LOG(LogNYCSim, Log, TEXT("Input: using the authored mapping contexts from /Game/NYCSim/Input."));
	}
}

void UNYCInputConfig::BuildDefaultContexts()
{
	DrivingContext = NewObject<UInputMappingContext>(this, TEXT("IMC_Driving_Default"));
	OnFootContext = NewObject<UInputMappingContext>(this, TEXT("IMC_OnFoot_Default"));
	CommonContext = NewObject<UInputMappingContext>(this, TEXT("IMC_Common_Default"));

	auto Map = [](UInputMappingContext* Context, UInputAction* Action, const FKey& Key) -> FEnhancedActionKeyMapping* {
		if (Context == nullptr || Action == nullptr || !Key.IsValid())
		{
			return nullptr;
		}
		return &Context->MapKey(Action, Key);
	};
	auto Negate = [this](FEnhancedActionKeyMapping* Mapping) {
		if (Mapping != nullptr)
		{
			Mapping->Modifiers.Add(NewObject<UInputModifierNegate>(this));
		}
	};
	auto SwizzleYXZ = [this](FEnhancedActionKeyMapping* Mapping) {
		if (Mapping != nullptr)
		{
			UInputModifierSwizzleAxis* Swizzle = NewObject<UInputModifierSwizzleAxis>(this);
			Swizzle->Order = EInputAxisSwizzle::YXZ;
			Mapping->Modifiers.Add(Swizzle);
		}
	};
	auto Pressed = [this](FEnhancedActionKeyMapping* Mapping) {
		if (Mapping != nullptr)
		{
			Mapping->Triggers.Add(NewObject<UInputTriggerPressed>(this));
		}
	};
	auto DeadZone = [this](FEnhancedActionKeyMapping* Mapping, float Lower) {
		if (Mapping != nullptr)
		{
			UInputModifierDeadZone* Zone = NewObject<UInputModifierDeadZone>(this);
			Zone->LowerThreshold = Lower;
			Mapping->Modifiers.Add(Zone);
		}
	};

	// ---- driving -------------------------------------------------------------------------------------------
	Map(DrivingContext, GetAction(ENYCInputAction::Throttle), EKeys::W);
	DeadZone(Map(DrivingContext, GetAction(ENYCInputAction::Throttle), EKeys::Gamepad_RightTriggerAxis), 0.06f);
	Map(DrivingContext, GetAction(ENYCInputAction::Brake), EKeys::S);
	DeadZone(Map(DrivingContext, GetAction(ENYCInputAction::Brake), EKeys::Gamepad_LeftTriggerAxis), 0.06f);

	Map(DrivingContext, GetAction(ENYCInputAction::Steer), EKeys::D);
	Negate(Map(DrivingContext, GetAction(ENYCInputAction::Steer), EKeys::A));
	DeadZone(Map(DrivingContext, GetAction(ENYCInputAction::Steer), EKeys::Gamepad_LeftX), 0.15f);

	Pressed(Map(DrivingContext, GetAction(ENYCInputAction::Handbrake), EKeys::SpaceBar));
	Map(DrivingContext, GetAction(ENYCInputAction::Handbrake), EKeys::Gamepad_FaceButton_Right);
	Pressed(Map(DrivingContext, GetAction(ENYCInputAction::ToggleReverse), EKeys::R));
	Map(DrivingContext, GetAction(ENYCInputAction::Horn), EKeys::H);
	Map(DrivingContext, GetAction(ENYCInputAction::Horn), EKeys::Gamepad_FaceButton_Left);
	Pressed(Map(DrivingContext, GetAction(ENYCInputAction::CycleHeadlights), EKeys::L));
	Pressed(Map(DrivingContext, GetAction(ENYCInputAction::IndicateLeft), EKeys::Q));
	Pressed(Map(DrivingContext, GetAction(ENYCInputAction::IndicateRight), EKeys::E));
	Pressed(Map(DrivingContext, GetAction(ENYCInputAction::ToggleHazards), EKeys::Z));
	Pressed(Map(DrivingContext, GetAction(ENYCInputAction::CycleWipers), EKeys::K));
	Map(DrivingContext, GetAction(ENYCInputAction::WindowDown), EKeys::Comma);
	Map(DrivingContext, GetAction(ENYCInputAction::WindowUp), EKeys::Period);
	Pressed(Map(DrivingContext, GetAction(ENYCInputAction::CycleCamera), EKeys::C));
	Pressed(Map(DrivingContext, GetAction(ENYCInputAction::CycleCamera), EKeys::Gamepad_DPad_Up));
	Pressed(Map(DrivingContext, GetAction(ENYCInputAction::PhotoMode), EKeys::P));
	Pressed(Map(DrivingContext, GetAction(ENYCInputAction::RadioNext), EKeys::RightBracket));
	Pressed(Map(DrivingContext, GetAction(ENYCInputAction::RadioPrevious), EKeys::LeftBracket));
	Pressed(Map(DrivingContext, GetAction(ENYCInputAction::ExitVehicle), EKeys::F));
	Pressed(Map(DrivingContext, GetAction(ENYCInputAction::ToggleFogLights), EKeys::Semicolon));

	// Look: Mouse2D gives (X, Y) directly; the thumbstick needs one axis per key.
	Map(DrivingContext, GetAction(ENYCInputAction::LookAround), EKeys::Mouse2D);
	DeadZone(Map(DrivingContext, GetAction(ENYCInputAction::LookAround), EKeys::Gamepad_RightX), 0.2f);
	SwizzleYXZ(Map(DrivingContext, GetAction(ENYCInputAction::LookAround), EKeys::Gamepad_RightY));

	// ---- on foot -------------------------------------------------------------------------------------------
	SwizzleYXZ(Map(OnFootContext, GetAction(ENYCInputAction::Move), EKeys::W));
	{
		FEnhancedActionKeyMapping* Back = Map(OnFootContext, GetAction(ENYCInputAction::Move), EKeys::S);
		SwizzleYXZ(Back);
		Negate(Back);
	}
	Map(OnFootContext, GetAction(ENYCInputAction::Move), EKeys::D);
	Negate(Map(OnFootContext, GetAction(ENYCInputAction::Move), EKeys::A));
	Map(OnFootContext, GetAction(ENYCInputAction::Move), EKeys::Gamepad_Left2D);

	Map(OnFootContext, GetAction(ENYCInputAction::LookAround), EKeys::Mouse2D);
	DeadZone(Map(OnFootContext, GetAction(ENYCInputAction::LookAround), EKeys::Gamepad_RightX), 0.2f);
	SwizzleYXZ(Map(OnFootContext, GetAction(ENYCInputAction::LookAround), EKeys::Gamepad_RightY));

	Pressed(Map(OnFootContext, GetAction(ENYCInputAction::Jump), EKeys::SpaceBar));
	Pressed(Map(OnFootContext, GetAction(ENYCInputAction::Jump), EKeys::Gamepad_FaceButton_Bottom));
	Map(OnFootContext, GetAction(ENYCInputAction::Sprint), EKeys::LeftShift);
	Map(OnFootContext, GetAction(ENYCInputAction::Sprint), EKeys::Gamepad_LeftThumbstick);
	Pressed(Map(OnFootContext, GetAction(ENYCInputAction::Crouch), EKeys::LeftControl));
	Pressed(Map(OnFootContext, GetAction(ENYCInputAction::Interact), EKeys::F));
	Pressed(Map(OnFootContext, GetAction(ENYCInputAction::Interact), EKeys::Gamepad_FaceButton_Top));
	Pressed(Map(OnFootContext, GetAction(ENYCInputAction::CycleCamera), EKeys::C));

	// ---- common --------------------------------------------------------------------------------------------
	Pressed(Map(CommonContext, GetAction(ENYCInputAction::ToggleMap), EKeys::M));
	Pressed(Map(CommonContext, GetAction(ENYCInputAction::SearchDestination), EKeys::Tab));
	// The menu is on the common context so it opens in the car and on foot alike.
	Pressed(Map(CommonContext, GetAction(ENYCInputAction::Menu), EKeys::Escape));
	Pressed(Map(CommonContext, GetAction(ENYCInputAction::Menu), EKeys::Gamepad_Special_Right));
	Pressed(Map(CommonContext, GetAction(ENYCInputAction::QuickSave), EKeys::F5));
	Pressed(Map(CommonContext, GetAction(ENYCInputAction::QuickLoad), EKeys::F9));
}

UNYCInputConfig* UNYCInputConfig::Get(const UObject* WorldContext)
{
	// One config per module load: the actions and contexts are immutable once built.
	static TWeakObjectPtr<UNYCInputConfig> Singleton;
	if (Singleton.IsValid())
	{
		return Singleton.Get();
	}
	UNYCInputConfig* Config = NewObject<UNYCInputConfig>(GetTransientPackage(), TEXT("NYCInputConfig"));
	Config->AddToRoot();
	Config->Resolve();
	Singleton = Config;
	(void)WorldContext;
	return Config;
}
