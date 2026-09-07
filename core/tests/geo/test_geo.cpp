#include <doctest/doctest.h>

#include <cmath>

#include "nycsim/geo/Ellipsoid.h"
#include "nycsim/geo/LambertConformalConic.h"
#include "nycsim/geo/NycTm.h"
#include "nycsim/geo/StatePlaneLI.h"
#include "nycsim/geo/TransverseMercator.h"
#include "nycsim/geo/UECoords.h"
#include "nycsim/geo/Units.h"

using namespace nycsim;
using namespace nycsim::geo;

namespace {

// Ground truth generated with pyproj 3.7.2 / PROJ 9.5.1 (scratch script docs/verification/core/
// gen_geo.py):  Transformer.from_crs(EPSG:4326, NYC_TM) for tm_x/tm_y and
// Transformer.from_crs(EPSG:4269, EPSG:2263) (pure projection, NAD83 geographic in) for sp_x/sp_y.
struct GroundTruth {
  const char* name;
  double lat, lon;
  double tm_x, tm_y;      // NYC_TM metres
  double sp_x, sp_y;      // EPSG:2263 US survey feet
};
constexpr GroundTruth kPoints[] = {
    {"Empire State Building, MN", 40.748440, -73.985664, -3011.976602, 5379.805153, 988222.209661, 211953.853484},
    {"One World Trade Center, MN", 40.712743, -74.013379, -5355.487648, 1417.019725, 980540.968906, 198948.279887},
    {"Statue of Liberty (Liberty Island), MN", 40.689247, -74.044502, -7988.169239, -1189.804339, 971908.458854, 190390.838870},
    {"Central Park Bethesda Terrace, MN", 40.774048, -73.970929, -1766.864904, 8223.154384, 992301.877569, 221284.699194},
    {"Inwood Hill Park north tip, MN", 40.874500, -73.925400, 2073.646414, 19378.481063, 1004881.004050, 257890.473058},
    {"Roosevelt Island (near origin), MN", 40.760600, -73.950900, -75.994983, 6729.551517, 997852.112511, 216387.623194},
    {"Columbia University Low Library, MN", 40.808000, -73.961900, -1004.108426, 11993.376992, 994797.285023, 233655.540352},
    {"Yankee Stadium, BX", 40.829643, -73.926175, 2009.673040, 14397.046001, 1004680.447579, 241547.181479},
    {"Bronx Zoo, BX", 40.850600, -73.876000, 6240.041087, 16726.700570, 1018555.140788, 249198.271403},
    {"City Island, BX", 40.847100, -73.786400, 13796.278376, 16348.268845, 1043346.442171, 247970.859406},
    {"Woodlawn Cemetery, BX", 40.891700, -73.873000, 6489.001990, 21291.132498, 1019363.393233, 264173.792798},
    {"Hunts Point Market, BX", 40.808500, -73.878400, 6041.481207, 12051.300961, 1017912.463324, 233858.778974},
    {"Brooklyn Bridge (BK tower), BK", 40.704500, -73.994100, -3726.883121, 500.652079, 985885.846458, 195944.878333},
    {"Prospect Park Grand Army Plaza, BK", 40.673800, -73.970100, -1699.427110, -2909.259675, 992543.954779, 184761.330993},
    {"Coney Island Wonder Wheel, BK", 40.573500, -73.978700, -2430.177680, -14047.036129, 990167.288107, 148218.683013},
    {"Barclays Center, BK", 40.682700, -73.975600, -2164.156652, -1920.814315, 991017.407770, 188003.383874},
    {"Canarsie Pier, BK", 40.626700, -73.885300, 5474.142939, -8137.762403, 1016089.069772, 167620.932438},
    {"Flushing Meadows Unisphere, QN", 40.746100, -73.845000, 8868.008420, 5124.642287, 1027198.786633, 211138.989533},
    {"JFK Terminal 4, QN", 40.644500, -73.782700, 14151.176071, -6149.683224, 1044553.221811, 174159.903546},
    {"LaGuardia Terminal B, QN", 40.775000, -73.874200, 6399.085163, 8331.427253, 1019092.674419, 221655.227730},
    {"Far Rockaway, QN", 40.605800, -73.755400, 16469.868739, -10442.442866, 1052168.633932, 160080.495013},
    {"Astoria Park, QN", 40.778200, -73.923200, 2262.364737, 8684.367082, 1005520.185885, 222805.400496},
    {"Jamaica Center, QN", 40.702200, -73.801100, 12583.947223, 254.969206, 1039399.289315, 195169.476040},
    {"St George Ferry Terminal, SI", 40.643700, -74.073600, -10454.907787, -6244.633030, 963824.899358, 173802.226089},
    {"Fort Wadsworth, SI", 40.605500, -74.055700, -8945.902075, -10488.589952, 968783.566760, 159881.289011},
    {"Great Kills Park, SI", 40.540400, -74.129900, -15240.572698, -17707.481337, 948145.006866, 136185.603404},
    {"Tottenville (Conference House), SI", 40.500300, -74.251500, -25557.385567, -22132.251910, 914305.078864, 121649.884603},
    {"Staten Island Mall, SI", 40.582300, -74.164000, -18118.120910, -13048.217861, 938695.688213, 151466.665859},
    {"Hoboken Terminal, NJ", 40.735100, -74.027500, -6546.512879, 3900.689904, 976628.791984, 207094.538666},
    {"George Washington Bridge (NJ tower), NJ", 40.851500, -73.958400, -708.319375, 16824.044715, 995758.669115, 249504.627732},
};
constexpr int kNumPoints = static_cast<int>(sizeof(kPoints) / sizeof(kPoints[0]));

// pyproj Proj.get_factors(): meridional_scale and meridian_convergence (deg) for the same points.
struct FactorTruth {
  double lat, lon, scale, convergence_deg;
};
constexpr FactorTruth kFactors[] = {
    {40.748440, -73.985664, 1.000000111628, -0.023279290},
    {40.712743, -74.013379, 1.000000352881, -0.041340040},
    {40.689247, -74.044502, 1.000000785099, -0.061611189},
    {40.774048, -73.970929, 1.000000038420, -0.013668263},
    {40.874500, -73.925400, 1.000000052913, 0.016098348},
    {40.760600, -73.950900, 1.000000000080, -0.000587610},
    {40.808000, -73.961900, 1.000000012416, -0.007776963},
    {40.829643, -73.926175, 1.000000049701, 0.015577075},
    {40.850600, -73.876000, 1.000000479064, 0.048402593},
    {40.847100, -73.786400, 1.000002341714, 0.107001549},
    {40.891700, -73.873000, 1.000000518046, 0.050406629},
    {40.808500, -73.878400, 1.000000449070, 0.046792970},
    {40.704500, -73.994100, 1.000000170902, -0.028760169},
    {40.673800, -73.970100, 1.000000035533, -0.013100209},
    {40.573500, -73.978700, 1.000000072674, -0.018667140},
    {40.682700, -73.975600, 1.000000057623, -0.016687859},
    {40.626700, -73.885300, 1.000000368703, 0.042127990},
    {40.746100, -73.845000, 1.000000967548, 0.068534404},
    {40.644500, -73.782700, 1.000002463864, 0.108973332},
    {40.775000, -73.874200, 1.000000503802, 0.049504257},
    {40.605800, -73.755400, 1.000003337444, 0.126655903},
    {40.778200, -73.923200, 1.000000062982, 0.017503953},
    {40.702200, -73.801100, 1.000001948312, 0.097101914},
    {40.643700, -74.073600, 1.000001344842, -0.080507320},
    {40.605500, -74.055700, 1.000000984656, -0.068794584},
    {40.540400, -74.129900, 1.000002857874, -0.116932357},
    {40.500300, -74.251500, 1.000008036697, -0.195810844},
    {40.582300, -74.164000, 1.000004038890, -0.139215859},
    {40.735100, -74.027500, 1.000000527283, -0.050573629},
    {40.851500, -73.958400, 1.000000006182, -0.005494446},
};

// Metres per degree of latitude / longitude on the WGS84 ellipsoid at a latitude.
void metresPerDegree(double lat_deg, double& mLat, double& mLon) {
  const double phi = lat_deg * kDegToRad;
  const double s = std::sin(phi), c = std::cos(phi);
  const double e2 = kWGS84.e2();
  const double w = std::sqrt(1.0 - e2 * s * s);
  const double M = kWGS84.a * (1.0 - e2) / (w * w * w);
  const double N = kWGS84.a / w;
  mLat = M * kDegToRad;
  mLon = N * c * kDegToRad;
}

}  // namespace

TEST_SUITE("geo") {
  TEST_CASE("NYC_TM matches pyproj ground truth to < 2 mm at 30 points across the five boroughs") {
    const TransverseMercator& tm = nycTm();
    double worst = 0.0;
    for (int i = 0; i < kNumPoints; ++i) {
      const GroundTruth& g = kPoints[i];
      auto r = tm.forward(LatLon{g.lat, g.lon});
      REQUIRE_MESSAGE(r.ok(), g.name);
      const double d = std::hypot(r->x - g.tm_x, r->y - g.tm_y);
      worst = std::fmax(worst, d);
      CHECK_MESSAGE(d < 0.002, g.name, " dx=", r->x - g.tm_x, " dy=", r->y - g.tm_y);
      auto inv = tm.inverse(XY{g.tm_x, g.tm_y});
      REQUIRE(inv.ok());
      double mLat, mLon;
      metresPerDegree(g.lat, mLat, mLon);
      const double dInv = std::hypot((inv->lat_deg - g.lat) * mLat, (inv->lon_deg - g.lon) * mLon);
      CHECK_MESSAGE(dInv < 0.002, g.name, " inverse error m=", dInv);
    }
    MESSAGE("worst NYC_TM forward disagreement with pyproj: ", worst * 1000.0, " mm");
    CHECK(worst < 0.002);
    CHECK(kNumPoints >= 20);
  }

  TEST_CASE("NYC_TM forward/inverse round trip < 1e-6 m over the whole scope") {
    const TransverseMercator& tm = nycTm();
    double worst = 0.0;
    for (double x = kScopeXMin; x <= kScopeXMax + 1e-9; x += 500.0) {
      for (double y = kScopeYMin; y <= kScopeYMax + 1e-9; y += 500.0) {
        auto ll = tm.inverse(XY{x, y});
        REQUIRE(ll.ok());
        auto xy = tm.forward(*ll);
        REQUIRE(xy.ok());
        worst = std::fmax(worst, std::hypot(xy->x - x, xy->y - y));
      }
    }
    MESSAGE("worst round-trip error over the scope grid: ", worst, " m");
    CHECK(worst < 1e-6);
    // Geographic-first round trip, expressed in metres.
    double worstGeo = 0.0;
    for (double lat = 40.45; lat <= 40.95; lat += 0.025) {
      for (double lon = -74.30; lon <= -73.65; lon += 0.025) {
        auto xy = tm.forward(LatLon{lat, lon});
        REQUIRE(xy.ok());
        auto ll = tm.inverse(*xy);
        REQUIRE(ll.ok());
        double mLat, mLon;
        metresPerDegree(lat, mLat, mLon);
        worstGeo = std::fmax(worstGeo, std::hypot((ll->lat_deg - lat) * mLat, (ll->lon_deg - lon) * mLon));
      }
    }
    CHECK(worstGeo < 1e-6);
  }

  TEST_CASE("NYC_TM origin, scale distortion and convergence (ADR-002: <= 1.2 cm/km)") {
    const TransverseMercator& tm = nycTm();
    auto o = tm.forward(LatLon{40.7, -73.95});
    REQUIRE(o.ok());
    CHECK(std::fabs(o->x) < 1e-9);
    CHECK(std::fabs(o->y) < 1e-9);
    // Scale factor and convergence against pyproj get_factors().
    for (const FactorTruth& f : kFactors) {
      auto r = tm.factors(LatLon{f.lat, f.lon});
      REQUIRE(r.ok());
      CHECK(std::fabs(r->scale - f.scale) < 1e-9);
      CHECK(std::fabs(r->convergence_deg - f.convergence_deg) < 1e-6);
      CHECK(std::fabs(r->scale - 1.0) < 12e-6);  // 1.2 cm/km
    }
    // Every scope corner is below the 1.2 cm/km distortion bound.
    const double xs[2] = {kScopeXMin, kScopeXMax};
    const double ys[2] = {kScopeYMin, kScopeYMax};
    for (double x : xs) {
      for (double y : ys) {
        auto ll = tm.inverse(XY{x, y});
        REQUIRE(ll.ok());
        auto f = tm.factors(*ll);
        REQUIRE(f.ok());
        CHECK(std::fabs(f->scale - 1.0) < 12e-6);
      }
    }
  }

  TEST_CASE("Transverse Mercator generic behaviour (UTM 18N sanity, domain errors)") {
    TmParams utm18;
    utm18.lon0_deg = -75.0;
    utm18.k0 = 0.9996;
    utm18.x0_m = 500000.0;
    TransverseMercator tm(utm18);
    // Empire State Building in UTM 18N (EPSG:32618), pyproj 3.7.2: (585631.3970, 4511326.9229) m.
    auto r = tm.forward(LatLon{40.748440, -73.985664});
    REQUIRE(r.ok());
    CHECK(std::fabs(r->x - 585631.3970) < 0.001);
    CHECK(std::fabs(r->y - 4511326.9229) < 0.001);
    CHECK_FALSE(tm.forward(LatLon{95.0, 0.0}).ok());
    CHECK_FALSE(tm.forward(LatLon{40.0, 100.0}).ok());
    CHECK_FALSE(tm.forward(LatLon{std::nan(""), 0.0}).ok());
    CHECK_FALSE(tm.inverse(XY{1e12, 0.0}).ok());
    // Poles and equator are handled.
    auto pole = tm.forward(LatLon{90.0, -75.0});
    REQUIRE(pole.ok());
    CHECK(std::fabs(pole->x - 500000.0) < 1e-6);
    CHECK(std::fabs(pole->y - 0.9996 * tm.rectifyingRadius() * kPi / 2.0) < 1e-6);
    CHECK(std::fabs(pole->y - 9997964.943021) < 0.001);  // pyproj EPSG:32618 north pole
    auto eq = tm.forward(LatLon{0.0, -75.0});
    REQUIRE(eq.ok());
    CHECK(std::fabs(eq->y) < 1e-9);
  }

  TEST_CASE("EPSG:2263 Lambert Conformal Conic matches pyproj to < 2 mm (pure projection)") {
    double worst = 0.0;
    for (int i = 0; i < kNumPoints; ++i) {
      const GroundTruth& g = kPoints[i];
      auto r = lonLatToStatePlaneFt(g.lon, g.lat);
      REQUIRE_MESSAGE(r.ok(), g.name);
      const double dft = std::hypot(r->x - g.sp_x, r->y - g.sp_y);
      const double dm = units::usFtToM(dft);
      worst = std::fmax(worst, dm);
      CHECK_MESSAGE(dm < 0.002, g.name, " d=", dm, " m");
      auto inv = statePlaneFtToLonLat(g.sp_x, g.sp_y);
      REQUIRE(inv.ok());
      double mLat, mLon;
      metresPerDegree(g.lat, mLat, mLon);
      const double dInv = std::hypot((inv->lat_deg - g.lat) * mLat, (inv->lon_deg - g.lon) * mLon);
      CHECK_MESSAGE(dInv < 0.002, g.name, " inverse error m=", dInv);
    }
    MESSAGE("worst EPSG:2263 disagreement with pyproj: ", worst * 1000.0, " mm");
    // 984250 ftUS false easting is exactly 300000 m.
    CHECK(units::usFtToM(984250.0) == doctest::Approx(300000.0).epsilon(1e-15));
    CHECK(statePlaneLI().coneConstant() == doctest::Approx(std::sin((40.0 + 51.0 / 60.0) * kDegToRad)).epsilon(1e-4));
  }

  TEST_CASE("EPSG:2263 -> NYC_TM composition matches pyproj (null NAD83 shift) to < 2 mm") {
    // pyproj's Transformer.from_crs(2263, NYC_TM) selects "NAD83 to WGS 84 (1)" (null shift),
    // so the composition must agree with the direct WGS84 values from the same lat/lon.
    for (int i = 0; i < kNumPoints; ++i) {
      const GroundTruth& g = kPoints[i];
      auto r = statePlaneFtToTm(g.sp_x, g.sp_y);
      REQUIRE(r.ok());
      CHECK_MESSAGE(std::hypot(r->x - g.tm_x, r->y - g.tm_y) < 0.002, g.name);
      auto back = tmToStatePlaneFt(g.tm_x, g.tm_y);
      REQUIRE(back.ok());
      CHECK(units::usFtToM(std::hypot(back->x - g.sp_x, back->y - g.sp_y)) < 0.002);
    }
  }

  TEST_CASE("LCC round trip and scale") {
    const LambertConformalConic& lcc = statePlaneLI();
    double worst = 0.0;
    for (double lat = 40.45; lat <= 41.0; lat += 0.05) {
      for (double lon = -74.3; lon <= -73.6; lon += 0.05) {
        auto xy = lcc.forward(LatLon{lat, lon});
        REQUIRE(xy.ok());
        auto ll = lcc.inverse(*xy);
        REQUIRE(ll.ok());
        double mLat, mLon;
        metresPerDegree(lat, mLat, mLon);
        worst = std::fmax(worst, std::hypot((ll->lat_deg - lat) * mLat, (ll->lon_deg - lon) * mLon));
      }
    }
    CHECK(worst < 1e-6);
    // Scale is exactly 1 on both standard parallels and < 1 between them.
    CHECK(lcc.scale(LatLon{40.0 + 40.0 / 60.0, -74.0}).value() == doctest::Approx(1.0).epsilon(1e-12));
    CHECK(lcc.scale(LatLon{41.0 + 2.0 / 60.0, -74.0}).value() == doctest::Approx(1.0).epsilon(1e-12));
    CHECK(lcc.scale(LatLon{40.85, -74.0}).value() < 1.0);
    CHECK_FALSE(lcc.forward(LatLon{90.0, 0.0}).ok());
    CHECK_FALSE(lcc.inverse(XY{std::nan(""), 0.0}).ok());
  }

  TEST_CASE("UE coordinate mapping (ARCHITECTURE §2)") {
    constexpr UEVector v = toUE(1.5, 2.0, 3.25);
    static_assert(v.x_cm == 150.0 && v.y_cm == -200.0 && v.z_cm == 325.0, "UE mapping");
    constexpr WorldPos back = fromUE(v);
    static_assert(back.east_m == 1.5 && back.north_m == 2.0 && back.up_m == 3.25, "UE inverse");
    // Headings: north -> yaw -90, east -> 0, south -> 90, west -> 180 (wrapped to -180).
    CHECK(headingToUEYaw(0.0) == doctest::Approx(-90.0));
    CHECK(headingToUEYaw(90.0) == doctest::Approx(0.0));
    CHECK(headingToUEYaw(180.0) == doctest::Approx(90.0));
    CHECK(headingToUEYaw(270.0) == doctest::Approx(-180.0));
    CHECK(ueYawToHeading(-90.0) == doctest::Approx(0.0));
    CHECK(ueYawToHeading(90.0) == doctest::Approx(180.0));
    // Math angle: east 0 -> yaw 0; north 90 -> yaw -90.
    CHECK(mathAngleToUEYaw(90.0) == doctest::Approx(-90.0));
    CHECK(ueYawToMathAngle(-90.0) == doctest::Approx(90.0));
    CHECK(mathAngleToHeading(90.0) == doctest::Approx(0.0));
    CHECK(headingToMathAngle(0.0) == doctest::Approx(90.0));
    CHECK(wrapDeg360(-30.0) == doctest::Approx(330.0));
    CHECK(wrapDeg360(720.0) == doctest::Approx(0.0));
    CHECK(wrapDeg180(180.0) == doctest::Approx(-180.0));
    // A heading of 45 deg (north-east) points to +X, -Y in UE.
    const double yaw = headingToUEYaw(45.0) * kDegToRad;
    CHECK(std::cos(yaw) > 0.0);
    CHECK(std::sin(yaw) < 0.0);
    // Direction vectors flip north.
    constexpr UEVector d = directionToUE(0.0, 1.0, 0.0);
    static_assert(d.y_cm == -1.0, "north maps to -Y");
  }

  TEST_CASE("Units") {
    CHECK(units::kUsSurveyFootM == doctest::Approx(0.3048006096012192).epsilon(1e-16));
    CHECK(units::mphToMps(60.0) == doctest::Approx(26.8224));
    CHECK(units::mpsToMph(units::mphToMps(30.0)) == doctest::Approx(30.0));
    CHECK(units::usFtToM(units::mToUsFt(123.456)) == doctest::Approx(123.456));
  }
}
