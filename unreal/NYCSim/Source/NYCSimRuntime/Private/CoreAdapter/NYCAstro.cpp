#include "CoreAdapter/NYCAstro.h"

#include "CoreAdapter/NYCGeo.h"

#include "Misc/DateTime.h"

#include "nycsim/Config.h"
#include "nycsim/astro/Moon.h"
#include "nycsim/astro/Spa.h"
#include "nycsim/time/NyTime.h"

namespace
{
	nycsim::astro::Observer ToCore(const FNYCObserver& O)
	{
		nycsim::astro::Observer C;
		C.latitudeDeg = O.LatitudeDeg;
		C.longitudeDeg = O.LongitudeDeg;
		C.elevationM = O.ElevationMetres;
		C.pressureMbar = O.PressureMbar;
		C.temperatureC = O.TemperatureC;
		C.atmosRefractDeg = nycsim::astro::kAtmosRefractHorizonDeg;
		return C;
	}

	FDateTime ToDateTime(const nycsim::nytime::DateTime& D)
	{
		const int32 Second = FMath::Clamp(FMath::FloorToInt32(D.second), 0, 59);
		const int32 Millisecond = FMath::Clamp(FMath::FloorToInt32((D.second - FMath::FloorToDouble(D.second)) * 1000.0), 0, 999);
		if (!FDateTime::Validate(D.year, D.month, D.day, D.hour, D.minute, Second, Millisecond))
		{
			return FDateTime(1970, 1, 1);
		}
		return FDateTime(D.year, D.month, D.day, D.hour, D.minute, Second, Millisecond);
	}

	/** Unit vector toward a body, in UE space. Compass azimuth (0 = north, clockwise), altitude above the horizon. */
	FVector DirectionFromAzEl(double AzimuthDeg, double ElevationDeg)
	{
		const double Az = FMath::DegreesToRadians(AzimuthDeg);
		const double El = FMath::DegreesToRadians(ElevationDeg);
		const double CosEl = FMath::Cos(El);
		// ENU: east = cos(el) sin(az), north = cos(el) cos(az), up = sin(el).
		const FVector Enu(CosEl * FMath::Sin(Az), CosEl * FMath::Cos(Az), FMath::Sin(El));
		return NYCGeo::DirectionToUE(Enu).GetSafeNormal();
	}
}

namespace NYCAstro
{
	double RiseSetAltitudeDeg() { return nycsim::astro::kRiseSetH0Deg; }
	double CivilTwilightAltitudeDeg() { return nycsim::astro::kCivilTwilightH0Deg; }
	double ManhattanStreetSunsetAzimuthDeg() { return nycsim::astro::kManhattanStreetSunsetAzimuthDeg; }

	double NowUnixSeconds()
	{
		// FDateTime::UtcNow() is the platform UTC clock; ToUnixTimestampDecimal keeps the sub-second part.
		return FDateTime::UtcNow().ToUnixTimestampDecimal();
	}

	bool ParseIso8601Utc(const FString& Text, double& OutUnixSeconds)
	{
		if (Text.IsEmpty())
		{
			return false;
		}
		FDateTime Parsed;
		if (FDateTime::ParseIso8601(*Text, Parsed))
		{
			OutUnixSeconds = Parsed.ToUnixTimestampDecimal();
			return true;
		}
		// NOAA CO-OPS returns "2026-09-06 11:24" (UTC, no zone marker); api.weather.gov always sends ISO-8601.
		int32 Year = 0, Month = 0, Day = 0, Hour = 0, Minute = 0, Second = 0;
		const int32 Fields = FCString::Sscanf(*Text, TEXT("%d-%d-%d %d:%d:%d"), &Year, &Month, &Day, &Hour, &Minute, &Second);
		if (Fields >= 5)
		{
			OutUnixSeconds = static_cast<double>(
				nycsim::nytime::unixFromCivilUtc(Year, Month, Day, Hour, Minute, Fields >= 6 ? Second : 0));
			return true;
		}
		return false;
	}

	FString FormatIso8601Utc(double UnixSeconds)
	{
		const nycsim::nytime::DateTime D = nycsim::nytime::civilFromUnix(UnixSeconds);
		return FString::Printf(TEXT("%04d-%02d-%02dT%02d:%02d:%02dZ"), D.year, D.month, D.day, D.hour, D.minute,
			FMath::Clamp(FMath::FloorToInt32(D.second), 0, 59));
	}

	bool ComputeSimTime(double UnixSeconds, FNYCSimTime& OutTime, FString& OutError)
	{
		const nycsim::Result<nycsim::nytime::SimTime> R = nycsim::nytime::simTime(UnixSeconds);
		if (!R)
		{
			OutError = FString::Printf(TEXT("nytime::simTime(%.3f) failed: %s (%s, detail %lld)"), UnixSeconds,
				UTF8_TO_TCHAR(R.error().message), UTF8_TO_TCHAR(nycsim::errorCodeName(R.error().code)),
				static_cast<int64>(R.error().detail));
			return false;
		}
		const nycsim::nytime::SimTime& S = R.value();
		OutTime.UnixSeconds = S.unixS;
		OutTime.Utc = ToDateTime(S.utc);
		OutTime.Local = ToDateTime(S.local);
		OutTime.UtcOffsetSeconds = S.utcOffsetS;
		OutTime.bIsDst = S.isDst;
		OutTime.TzAbbreviation = UTF8_TO_TCHAR(S.tzAbbreviation);
		OutTime.LocalHours = S.localHours();
		OutTime.LocalDayOfYear = S.dayOfYear;
		OutTime.JulianDay = S.jd;
		OutTime.JulianEphemerisDay = S.jde;
		OutTime.DeltaTSeconds = S.deltaTS;
		return true;
	}

	FNYCSunState SunAt(double UnixSeconds, const FNYCObserver& Observer)
	{
		const nycsim::astro::Observer Obs = ToCore(Observer);
		const nycsim::astro::SolarPosition P = nycsim::astro::solarPositionUnix(UnixSeconds, Obs);

		FNYCSunState Out;
		Out.AzimuthDeg = P.azimuth;
		Out.ElevationDeg = P.elevation;
		Out.ZenithDeg = P.zenith;
		Out.DeclinationDeg = P.deltaPrime;
		Out.RightAscensionDeg = P.alphaPrime;
		Out.ApparentSiderealTimeDeg = P.geocentric.nu;
		Out.LocalSiderealTimeDeg = nycsim::astro::limitDegrees(P.geocentric.nu + Observer.LongitudeDeg);
		Out.DistanceAu = P.distanceAu;
		Out.SemidiameterDeg = P.semidiameterDeg;
		Out.DirectionUE = DirectionFromAzEl(P.azimuth, P.elevation);
		return Out;
	}

	FNYCMoonState MoonAt(double UnixSeconds, const FNYCObserver& Observer)
	{
		const nycsim::astro::Observer Obs = ToCore(Observer);
		const nycsim::astro::MoonPosition M = nycsim::astro::moonPositionUnix(UnixSeconds, Obs);

		FNYCMoonState Out;
		Out.AzimuthDeg = M.azimuth;
		Out.ElevationDeg = M.elevation;
		Out.DistanceKm = M.distanceKm;
		Out.SemidiameterDeg = M.semidiameterDeg;
		Out.IlluminatedFraction = M.illuminatedFraction;
		Out.PhaseAngleDeg = M.phaseAngleDeg;
		Out.ElongationDeg = M.elongationDeg;
		Out.bWaxing = M.waxing;
		Out.PhaseIndex = static_cast<uint8>(M.phase);
		Out.PhaseName = UTF8_TO_TCHAR(nycsim::astro::moonPhaseName(M.phase));
		Out.DirectionUE = DirectionFromAzEl(M.azimuth, M.elevation);
		return Out;
	}

	bool SunEventsForInstant(double UnixSeconds, const FNYCObserver& Observer, double H0Deg,
		FNYCSunEvents& OutEvents, FString& OutError)
	{
		FNYCSimTime Time;
		if (!ComputeSimTime(UnixSeconds, Time, OutError))
		{
			return false;
		}
		nycsim::nytime::Date LocalDate;
		LocalDate.year = Time.Local.GetYear();
		LocalDate.month = Time.Local.GetMonth();
		LocalDate.day = Time.Local.GetDay();

		const nycsim::Result<nycsim::astro::SunEvents> R =
			nycsim::astro::sunEventsLocal(LocalDate, ToCore(Observer), H0Deg);
		if (!R)
		{
			OutError = FString::Printf(TEXT("astro::sunEventsLocal(%04d-%02d-%02d) failed: %s"),
				LocalDate.year, LocalDate.month, LocalDate.day, UTF8_TO_TCHAR(R.error().message));
			return false;
		}
		const nycsim::astro::SunEvents& E = R.value();
		OutEvents.bHasSunrise = E.hasSunrise;
		OutEvents.bHasSunset = E.hasSunset;
		OutEvents.SunriseUnix = E.sunriseUnix;
		OutEvents.TransitUnix = E.transitUnix;
		OutEvents.SunsetUnix = E.sunsetUnix;
		OutEvents.H0Deg = E.h0Deg;
		return true;
	}

	FVector AzimuthElevationToUE(double AzimuthDeg, double ElevationDeg)
	{
		return DirectionFromAzEl(AzimuthDeg, ElevationDeg);
	}

	FString CoreVersion()
	{
		return FString::Printf(TEXT("%d.%d.%d"), NYCSIM_CORE_VERSION_MAJOR, NYCSIM_CORE_VERSION_MINOR, NYCSIM_CORE_VERSION_PATCH);
	}
}
