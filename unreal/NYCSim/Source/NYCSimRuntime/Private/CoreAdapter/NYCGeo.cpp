#include "CoreAdapter/NYCGeo.h"

#include "nycsim/geo/UECoords.h"
#include "nycsim/geo/NycTm.h"

namespace NYCGeo
{
	FVector NycTmToUE(const FVector& P)
	{
		const nycsim::geo::UEVector V = nycsim::geo::toUE(P.X, P.Y, P.Z);
		return FVector(V.x_cm, V.y_cm, V.z_cm);
	}

	FVector UEToNycTm(const FVector& UE)
	{
		const nycsim::geo::WorldPos W = nycsim::geo::fromUE(nycsim::geo::UEVector{UE.X, UE.Y, UE.Z});
		return FVector(W.east_m, W.north_m, W.up_m);
	}

	FVector DirectionToUE(const FVector& D)
	{
		const nycsim::geo::UEVector V = nycsim::geo::directionToUE(D.X, D.Y, D.Z);
		return FVector(V.x_cm, V.y_cm, V.z_cm);
	}

	FVector DirectionFromUE(const FVector& D)
	{
		return FVector(D.X, -D.Y, D.Z);
	}

	double HeadingToUEYaw(double HeadingDeg) { return nycsim::geo::headingToUEYaw(HeadingDeg); }
	double UEYawToHeading(double YawDeg) { return nycsim::geo::ueYawToHeading(YawDeg); }
	double MathAngleToUEYaw(double AngleDeg) { return nycsim::geo::mathAngleToUEYaw(AngleDeg); }
	double UEYawToMathAngle(double YawDeg) { return nycsim::geo::ueYawToMathAngle(YawDeg); }

	bool LonLatToNycTm(double LonDeg, double LatDeg, double& OutX, double& OutY)
	{
		const nycsim::Result<nycsim::geo::XY> R = nycsim::geo::lonLatToTm(LonDeg, LatDeg);
		if (!R)
		{
			return false;
		}
		OutX = R.value().x;
		OutY = R.value().y;
		return true;
	}

	bool NycTmToLonLat(double X, double Y, double& OutLon, double& OutLat)
	{
		const nycsim::Result<nycsim::geo::LatLon> R = nycsim::geo::tmToLonLat(X, Y);
		if (!R)
		{
			return false;
		}
		OutLat = R.value().lat_deg;
		OutLon = R.value().lon_deg;
		return true;
	}

	bool LonLatToUE(double LonDeg, double LatDeg, double AltMetres, FVector& OutUE)
	{
		double X = 0.0, Y = 0.0;
		if (!LonLatToNycTm(LonDeg, LatDeg, X, Y))
		{
			return false;
		}
		OutUE = NycTmToUE(FVector(X, Y, AltMetres));
		return true;
	}

	bool UEToLonLat(const FVector& UE, double& OutLon, double& OutLat, double& OutAlt)
	{
		const FVector P = UEToNycTm(UE);
		OutAlt = P.Z;
		return NycTmToLonLat(P.X, P.Y, OutLon, OutLat);
	}

	FString CoreProj4()
	{
		return FString(UTF8_TO_TCHAR(nycsim::geo::kNycTmProj4));
	}

	FBox2D ScopeBoxMetres()
	{
		return FBox2D(FVector2D(nycsim::geo::kScopeXMin, nycsim::geo::kScopeYMin), FVector2D(nycsim::geo::kScopeXMax, nycsim::geo::kScopeYMax));
	}

	bool InScope(double X, double Y) { return nycsim::geo::inScope(X, Y); }

	FIntPoint TileOfNycTm(double X, double Y)
	{
		return FIntPoint(static_cast<int32>(FMath::FloorToInt64(X / TileSizeMetres)), static_cast<int32>(FMath::FloorToInt64(Y / TileSizeMetres)));
	}

	FIntPoint TileOfUE(const FVector& UE)
	{
		const FVector P = UEToNycTm(UE);
		return TileOfNycTm(P.X, P.Y);
	}

	FString TileName(const FIntPoint& Tile)
	{
		return FString::Printf(TEXT("t_%d_%d"), Tile.X, Tile.Y);
	}

	bool ParseTileName(const FString& Name, FIntPoint& OutTile)
	{
		// "t_" <int> "_" <int>
		if (!Name.StartsWith(TEXT("t_")))
		{
			return false;
		}
		FString Rest = Name.Mid(2);
		// The second underscore separates tx from ty; tx may start with '-'.
		int32 Split = INDEX_NONE;
		for (int32 i = 1; i < Rest.Len(); ++i)
		{
			if (Rest[i] == TEXT('_'))
			{
				Split = i;
				break;
			}
		}
		if (Split == INDEX_NONE)
		{
			return false;
		}
		const FString A = Rest.Left(Split);
		const FString B = Rest.Mid(Split + 1);
		if (A.IsEmpty() || B.IsEmpty() || !A.IsNumeric() || !B.IsNumeric())
		{
			return false;
		}
		OutTile.X = FCString::Atoi(*A);
		OutTile.Y = FCString::Atoi(*B);
		return true;
	}

	FString TileAssetName(const FIntPoint& Tile)
	{
		return TileName(Tile).Replace(TEXT("-"), TEXT("m"));
	}

	FVector2D TileOriginMetres(const FIntPoint& Tile)
	{
		return FVector2D(Tile.X * TileSizeMetres, Tile.Y * TileSizeMetres);
	}

	FBox TileBoundsUE(const FIntPoint& Tile, double ZMin, double ZMax)
	{
		const FVector2D O = TileOriginMetres(Tile);
		// north is -Y in UE: the tile's north edge (O.Y + 1000) maps to the smaller UE Y.
		const FVector A = NycTmToUE(FVector(O.X, O.Y, ZMin));
		const FVector B = NycTmToUE(FVector(O.X + TileSizeMetres, O.Y + TileSizeMetres, ZMax));
		return FBox(FVector(FMath::Min(A.X, B.X), FMath::Min(A.Y, B.Y), FMath::Min(A.Z, B.Z)), FVector(FMath::Max(A.X, B.X), FMath::Max(A.Y, B.Y), FMath::Max(A.Z, B.Z)));
	}

	FVector TileCentreUE(const FIntPoint& Tile, double ZMetres)
	{
		const FVector2D O = TileOriginMetres(Tile);
		return NycTmToUE(FVector(O.X + TileSizeMetres * 0.5, O.Y + TileSizeMetres * 0.5, ZMetres));
	}

	FIntPoint ParentTile(const FIntPoint& Tile, int32 Level)
	{
		const int32 F = 1 << (2 * FMath::Clamp(Level, 0, 8)); // 4^Level
		return FIntPoint(FMath::FloorToInt32(static_cast<float>(Tile.X) / F), FMath::FloorToInt32(static_cast<float>(Tile.Y) / F));
	}
}
