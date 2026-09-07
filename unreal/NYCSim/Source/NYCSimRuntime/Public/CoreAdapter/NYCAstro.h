// Adapter over nycsim::nytime (America/New_York civil time, Julian day, Delta-T) and nycsim::astro
// (NREL SPA sun, Meeus moon). Nothing else in the runtime includes nycsim/time/*.h or nycsim/astro/*.h.
//
// Angles: `AzimuthDeg` is compass (0 = north, 90 = east) exactly as the core returns it; `ElevationDeg` is the
// apparent (refracted, topocentric) altitude above the horizon. Directions handed back in UE space already carry the
// NYC_TM -> UE handedness flip (NYCGeo::DirectionToUE), so they can be fed straight into a light's rotation.
#pragma once

#include "CoreMinimal.h"

/** Observer for the ephemeris (defaults to Central Park / the NWS KNYC site, which is the core's default too). */
struct FNYCObserver
{
	double LatitudeDeg = 40.7831;
	double LongitudeDeg = -73.9712;
	double ElevationMetres = 40.0;
	double PressureMbar = 1013.25;
	double TemperatureC = 15.0;
};

/** One clock reading: UTC, New York wall clock and the quantities the ephemeris needs. */
struct FNYCSimTime
{
	double UnixSeconds = 0.0;
	FDateTime Utc = FDateTime(1970, 1, 1);
	FDateTime Local = FDateTime(1970, 1, 1);
	int32 UtcOffsetSeconds = -18000;
	bool bIsDst = false;
	FString TzAbbreviation = TEXT("EST");
	/** Local hours since midnight, fractional. */
	double LocalHours = 0.0;
	int32 LocalDayOfYear = 1;
	double JulianDay = 0.0;
	double JulianEphemerisDay = 0.0;
	double DeltaTSeconds = 0.0;
};

struct FNYCSunState
{
	double AzimuthDeg = 0.0;
	double ElevationDeg = 0.0;
	double ZenithDeg = 90.0;
	double DeclinationDeg = 0.0;
	double RightAscensionDeg = 0.0;
	/** Apparent sidereal time at Greenwich, degrees (SPA nu). */
	double ApparentSiderealTimeDeg = 0.0;
	/** Local apparent sidereal time = nu + observer longitude, wrapped to [0, 360). */
	double LocalSiderealTimeDeg = 0.0;
	double DistanceAu = 1.0;
	double SemidiameterDeg = 0.26667;
	/** Unit vector from the observer toward the sun, in UE space. */
	FVector DirectionUE = FVector::UpVector;
};

struct FNYCMoonState
{
	double AzimuthDeg = 0.0;
	double ElevationDeg = 0.0;
	double DistanceKm = 384400.0;
	double SemidiameterDeg = 0.259;
	/** Illuminated fraction k, 0..1. */
	double IlluminatedFraction = 0.0;
	double PhaseAngleDeg = 180.0;
	double ElongationDeg = 0.0;
	bool bWaxing = false;
	/** 0 New .. 7 WaningCrescent (nycsim::astro::MoonPhase). */
	uint8 PhaseIndex = 0;
	FString PhaseName = TEXT("New");
	FVector DirectionUE = FVector::UpVector;
};

struct FNYCSunEvents
{
	bool bHasSunrise = false;
	bool bHasSunset = false;
	double SunriseUnix = 0.0;
	double TransitUnix = 0.0;
	double SunsetUnix = 0.0;
	/** Horizon altitude the events were solved for (-0.8333 rise/set, -6 civil twilight, ...). */
	double H0Deg = 0.0;
};

namespace NYCAstro
{
	/** Sun altitude used for sunrise/sunset (upper limb on the horizon, USNO convention). */
	NYCSIMRUNTIME_API double RiseSetAltitudeDeg();
	NYCSIMRUNTIME_API double CivilTwilightAltitudeDeg();
	/** Compass azimuth of a Manhattanhenge sunset: 299.0 deg (grid rotated 29 deg from east-west). */
	NYCSIMRUNTIME_API double ManhattanStreetSunsetAzimuthDeg();

	/** Current POSIX time from the platform clock (UTC, no leap seconds). */
	NYCSIMRUNTIME_API double NowUnixSeconds();

	/** Parses "2026-07-12T00:20:00Z" (and the forms api.weather.gov and NOAA return) to POSIX seconds. */
	NYCSIMRUNTIME_API bool ParseIso8601Utc(const FString& Text, double& OutUnixSeconds);
	NYCSIMRUNTIME_API FString FormatIso8601Utc(double UnixSeconds);

	/** Civil time for an instant. False (with OutError) before 1967, which the core's DST rule rejects. */
	NYCSIMRUNTIME_API bool ComputeSimTime(double UnixSeconds, FNYCSimTime& OutTime, FString& OutError);

	NYCSIMRUNTIME_API FNYCSunState SunAt(double UnixSeconds, const FNYCObserver& Observer);
	NYCSIMRUNTIME_API FNYCMoonState MoonAt(double UnixSeconds, const FNYCObserver& Observer);

	/** Rise/transit/set for the New York local calendar date containing UnixSeconds. */
	NYCSIMRUNTIME_API bool SunEventsForInstant(double UnixSeconds, const FNYCObserver& Observer, double H0Deg,
		FNYCSunEvents& OutEvents, FString& OutError);

	/** Direction from a compass azimuth and an altitude, in UE space (unit length). */
	NYCSIMRUNTIME_API FVector AzimuthElevationToUE(double AzimuthDeg, double ElevationDeg);

	/** Core library version of the astronomy code path (nycsim/Config.h). */
	NYCSIMRUNTIME_API FString CoreVersion();
}
