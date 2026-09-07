#include "nycsim/vehicle/Friction.h"

#include <cmath>

namespace nycsim {
namespace vehicle {

namespace {

struct Row {
  SurfaceClass s;
  const char* name;
  double dry;
  double wet;
  bool normative;
};

// The first six rows are ARCHITECTURE §7 verbatim. For the entries whose name fixes the condition
// the dry and wet columns are identical so no blend can move them off the contract value.
constexpr Row kTable[] = {
    {SurfaceClass::DryAsphalt, "dry_asphalt", 1.00, 0.70, true},
    {SurfaceClass::WetAsphalt, "wet_asphalt", 0.70, 0.70, true},
    {SurfaceClass::SteelPlateWet, "steel_plate_wet", 0.55, 0.55, true},
    {SurfaceClass::PaintedMarkingWet, "painted_marking_wet", 0.60, 0.60, true},
    {SurfaceClass::Snow, "snow", 0.30, 0.30, true},
    {SurfaceClass::Ice, "ice", 0.15, 0.15, true},
    // ---- appended extension
    {SurfaceClass::Concrete, "concrete", 0.95, 0.65, false},
    {SurfaceClass::BelgianBlock, "belgian_block", 0.75, 0.50, false},
    {SurfaceClass::SteelGrate, "steel_grate", 0.75, 0.55, false},
    {SurfaceClass::Gravel, "gravel", 0.55, 0.45, false},
    {SurfaceClass::Boardwalk, "boardwalk", 0.70, 0.45, false},
    {SurfaceClass::PackedSnow, "packed_snow", 0.30, 0.25, false},
    {SurfaceClass::Slush, "slush", 0.35, 0.35, false},
};
constexpr int kRowCount = static_cast<int>(sizeof(kTable) / sizeof(kTable[0]));
static_assert(kRowCount == static_cast<int>(SurfaceClass::Count),
              "the friction table must cover every SurfaceClass");

const Row& row(SurfaceClass s) {
  const int i = static_cast<int>(s);
  if (i < 0 || i >= kRowCount) return kTable[0];
  return kTable[i];
}

double clamp01(double v) { return v < 0.0 ? 0.0 : (v > 1.0 ? 1.0 : v); }

}  // namespace

const char* surfaceClassName(SurfaceClass s) { return row(s).name; }

bool isNormativeSurface(SurfaceClass s) { return row(s).normative; }

FrictionEntry frictionTable(SurfaceClass s) {
  const Row& r = row(s);
  return FrictionEntry{r.dry, r.wet};
}

double frictionFor(SurfaceClass s, double wetness, double snowCover, double iceRisk) {
  const FrictionEntry e = frictionTable(s);
  const double w = clamp01(wetness);
  double mu = e.dry + (e.wet - e.dry) * w;
  const double cover = clamp01(snowCover);
  if (cover > 0.0) {
    // A covered road behaves as packed snow whatever is underneath; partial cover interpolates.
    const double snowMu = frictionTable(SurfaceClass::PackedSnow).dry;
    mu = mu + (snowMu - mu) * cover;
  }
  const double ice = clamp01(iceRisk);
  if (ice > 0.0) {
    const double iceMu = frictionTable(SurfaceClass::Ice).dry;
    mu = mu + (iceMu - mu) * ice;
  }
  return mu;
}

double tractionLimitedAccelMps2(double mu, double frontWeightFraction, double cgHeightM,
                               double wheelbaseM) {
  const double g = 9.80665;
  if (!(mu > 0.0) || !(wheelbaseM > 0.0)) return 0.0;
  const double wf = clamp01(frontWeightFraction);
  // Front axle load fraction under acceleration a: wf - a/g * (h / L). Solving
  //   a = mu * g * (wf - (a/g)(h/L))
  // for a gives a = mu * g * wf / (1 + mu * h / L).
  const double denom = 1.0 + mu * cgHeightM / wheelbaseM;
  return mu * g * wf / denom;
}

}  // namespace vehicle
}  // namespace nycsim
