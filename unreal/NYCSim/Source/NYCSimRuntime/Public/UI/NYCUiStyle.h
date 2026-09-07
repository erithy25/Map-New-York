// One place that owns what the interface looks like.
//
// A screen reads as a real game when it is systematic, not when it is decorated. Everything visible
// in NYCSim's UI comes from the eleven constants below: one spacing unit, four type sizes, six
// colour roles, one corner radius, one easing curve. Nothing anywhere else picks a margin, a grey or
// a duration of its own. That restriction is the design: it is what makes a speedometer, a turn card
// and a settings page look like parts of the same object rather than three things that happen to be
// on the same screen.
//
// Blueprint-free and asset-free, like the rest of the project: this is a header and a cpp, not a
// USlateWidgetStyleAsset, so the look is under version control and diffable.
#pragma once

#include "CoreMinimal.h"
#include "Fonts/SlateFontInfo.h"
#include "Styling/SlateColor.h"

/** Type roles. Four sizes, and never more than three of them on screen at once. */
enum class ENYCTextRole : uint8
{
	/** 48 px. The speed, and nothing else. */
	Display,
	/** 24 px. A turn distance, a menu heading. */
	Title,
	/** 15 px. Labels, street names, values. */
	Label,
	/** 12 px. Units, secondary detail, the things you read only when you look for them. */
	Caption,
};

/** Colour roles. Six, so that "which grey" is never a decision anyone makes twice. */
enum class ENYCColourRole : uint8
{
	/** Panel ground. Near-black, translucent, meant to sit over a blur. */
	Panel,
	/** Primary text on Panel. */
	Text,
	/** Secondary text: units, captions, anything the eye should skip. */
	TextMuted,
	/** The one accent. NYC taxi yellow, the same colour the project paints its cabs. */
	Accent,
	/** Warnings and tell-tales that mean stop. */
	Warn,
	/** Hairlines and separators. */
	Line,
};

struct NYCSIMRUNTIME_API FNYCUiStyle
{
	// ---- spacing -------------------------------------------------------------------------------
	/** The base unit. Every margin, gap and inset in the UI is a whole multiple of it. */
	static constexpr float Unit = 4.f;

	/** ``Space(3)`` is 12 px. Use this instead of typing a number. */
	static constexpr float Space(int32 Steps) { return Unit * static_cast<float>(Steps); }

	/** Panel corner radius. One value; the speedometer arc is the only square-ended thing. */
	static constexpr float CornerRadius = 4.f;

	/** Hairline thickness for separators and gauge ticks. */
	static constexpr float Hairline = 1.f;

	/** Fraction of the viewport kept clear at every edge, before the platform's own safe zone. */
	static constexpr float SafeInset = 0.05f;

	// ---- motion --------------------------------------------------------------------------------
	/** Every appearance, disappearance and value change in the UI takes this long. */
	static constexpr float MotionSeconds = 0.12f;

	/** The single easing curve: cubic out. Nothing in this interface pops. */
	static float EaseOut(float T);

	/** Frame-rate independent approach of Current towards Target over ``MotionSeconds``. */
	static float Approach(float Current, float Target, float DeltaSeconds,
		float TimeConstantSeconds = MotionSeconds);

	// ---- type ----------------------------------------------------------------------------------
	static float Size(ENYCTextRole Role);

	/**
	 * Overpass at the role's size. Overpass is the project's own typeface -- it is what the street
	 * signs in the world are set in -- so the interface and the city agree. Falls back to the engine
	 * font when the font import stage has not run, so the screen is never blank.
	 */
	static FSlateFontInfo Font(ENYCTextRole Role);

	// ---- colour --------------------------------------------------------------------------------
	static FLinearColor Colour(ENYCColourRole Role);
	static FSlateColor Slate(ENYCColourRole Role);

	/** The same colour at a different opacity, for fades and disabled states. */
	static FLinearColor Colour(ENYCColourRole Role, float Opacity);
};
