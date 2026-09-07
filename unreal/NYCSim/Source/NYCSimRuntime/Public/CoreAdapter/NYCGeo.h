// Coordinate adapter: NYC_TM (east, north, up; metres) <-> UE (cm, left-handed) and WGS84 <-> NYC_TM.
// Wraps nycsim/geo/UECoords.h and nycsim/geo/NycTm.h; nothing else in the runtime includes those headers.
// Tile arithmetic follows DATA_CONTRACTS §2 / ARCHITECTURE §3: (tx, ty) = (floor(x/1000), floor(y/1000)), "t_{tx}_{ty}".
#pragma once

#include "CoreMinimal.h"

namespace NYCGeo
{
	inline constexpr double TileSizeMetres = 1000.0;
	inline constexpr double MetresToUE = 100.0;

	/** NYC_TM (east_m, north_m, up_m) -> UE world position (cm). */
	NYCSIMRUNTIME_API FVector NycTmToUE(const FVector& EastNorthUpMetres);
	/** UE world position (cm) -> NYC_TM (east_m, north_m, up_m). */
	NYCSIMRUNTIME_API FVector UEToNycTm(const FVector& UECentimetres);
	/** Unit direction in ENU -> unit direction in UE (no scaling). */
	NYCSIMRUNTIME_API FVector DirectionToUE(const FVector& EastNorthUp);
	NYCSIMRUNTIME_API FVector DirectionFromUE(const FVector& UEDirection);

	/** Compass heading (0 = north, clockwise, degrees) -> UE yaw in [-180, 180). */
	NYCSIMRUNTIME_API double HeadingToUEYaw(double HeadingDeg);
	NYCSIMRUNTIME_API double UEYawToHeading(double YawDeg);
	/** Mathematical angle (0 = east, counter-clockwise) -> UE yaw. */
	NYCSIMRUNTIME_API double MathAngleToUEYaw(double AngleDeg);
	NYCSIMRUNTIME_API double UEYawToMathAngle(double YawDeg);

	/** WGS84 (degrees) -> NYC_TM metres. False when the core projection rejects the input (non-finite, out of domain). */
	NYCSIMRUNTIME_API bool LonLatToNycTm(double LonDeg, double LatDeg, double& OutXMetres, double& OutYMetres);
	NYCSIMRUNTIME_API bool NycTmToLonLat(double XMetres, double YMetres, double& OutLonDeg, double& OutLatDeg);
	/** WGS84 -> UE (Z from the supplied altitude in metres NAVD88). */
	NYCSIMRUNTIME_API bool LonLatToUE(double LonDeg, double LatDeg, double AltMetres, FVector& OutUE);
	NYCSIMRUNTIME_API bool UEToLonLat(const FVector& UE, double& OutLonDeg, double& OutLatDeg, double& OutAltMetres);

	/** Proj4 string of the project CRS as compiled into the core (used to validate crs.json). */
	NYCSIMRUNTIME_API FString CoreProj4();
	/** Project scope box in NYC_TM metres (kScope*). */
	NYCSIMRUNTIME_API FBox2D ScopeBoxMetres();
	NYCSIMRUNTIME_API bool InScope(double XMetres, double YMetres);

	// ---- tiles ----------------------------------------------------------------------------------------------------
	NYCSIMRUNTIME_API FIntPoint TileOfNycTm(double XMetres, double YMetres);
	NYCSIMRUNTIME_API FIntPoint TileOfUE(const FVector& UE);
	NYCSIMRUNTIME_API FString TileName(const FIntPoint& Tile);
	/** Parses "t_{tx}_{ty}" (negative indices allowed). */
	NYCSIMRUNTIME_API bool ParseTileName(const FString& Name, FIntPoint& OutTile);
	/** Content-safe form of the tile name ("t_-3_7" -> "t_m3_7"), matching pipeline/nycsim_pipeline/unreal/manifest.py. */
	NYCSIMRUNTIME_API FString TileAssetName(const FIntPoint& Tile);
	/** South-west corner in NYC_TM metres. */
	NYCSIMRUNTIME_API FVector2D TileOriginMetres(const FIntPoint& Tile);
	/** Axis-aligned UE box of the tile between the given elevations (metres NAVD88). */
	NYCSIMRUNTIME_API FBox TileBoundsUE(const FIntPoint& Tile, double ZMinMetres, double ZMaxMetres);
	/** Tile centre in UE at the given elevation. */
	NYCSIMRUNTIME_API FVector TileCentreUE(const FIntPoint& Tile, double ZMetres);
	/** Coarser index: Level 1 = 4 km parent, Level 2 = 16 km parent (pipeline tiling.parent_tile). */
	NYCSIMRUNTIME_API FIntPoint ParentTile(const FIntPoint& Tile, int32 Level);
}
