// nycsim/vehicle/Friction.h — tyre / road-surface friction.
//
// The six coefficients of ARCHITECTURE §7 are normative:
//   dry asphalt 1.00, wet asphalt 0.70, steel plate (wet) 0.55, painted marking (wet) 0.60,
//   snow 0.30, ice 0.15.
// The remaining entries are an APPENDED EXTENSION covering the other surfaces the road stage emits
// (DATA_CONTRACTS §7 `surface` enum: concrete, Belgian block, steel grate, gravel, boardwalk) and
// the dry counterparts of the wet-only entries. They are marked in the table and listed in
// docs/verification/core/REPORT.md.
//
// `frictionFor(surface, wetness, snowDepth, iceRisk)` blends the dry and wet coefficients with the
// weather module's wetness drive, so the world's live weather feeds the vehicle physics directly.
#pragma once

#include <cstdint>

#include "nycsim/Config.h"

namespace nycsim {
namespace vehicle {

/// Road surface classes. The first six lines of the table are the ARCHITECTURE §7 values.
enum class SurfaceClass : uint8_t {
  DryAsphalt = 0,     ///< normative 1.00
  WetAsphalt,         ///< normative 0.70
  SteelPlateWet,      ///< normative 0.55 (NYC construction plates)
  PaintedMarkingWet,  ///< normative 0.60
  Snow,               ///< normative 0.30
  Ice,                ///< normative 0.15
  // ---- appended extension (see the header comment)
  Concrete,
  BelgianBlock,       ///< cobble / granite setts (Meatpacking, DUMBO)
  SteelGrate,         ///< bridge decks
  Gravel,
  Boardwalk,          ///< timber (Coney Island, Rockaway)
  PackedSnow,
  Slush,
  Count
};
NYCSIM_API const char* surfaceClassName(SurfaceClass s);
/// True for the six ARCHITECTURE §7 entries.
NYCSIM_API bool isNormativeSurface(SurfaceClass s);

/// Peak longitudinal friction coefficient of a surface in its dry and fully wet states.
struct FrictionEntry {
  double dry;
  double wet;
};
/// Table lookup. For the four normative entries whose name already fixes a wetness
/// (SteelPlateWet, PaintedMarkingWet, Snow, Ice) `dry` and `wet` are both the normative value, so
/// blending cannot move them off the contract.
NYCSIM_API FrictionEntry frictionTable(SurfaceClass s);

/// Peak friction coefficient given the live weather drives.
///   wetness   0..1 from weather::WorldEffects
///   snowCover 0..1 (a covered road behaves as Snow / PackedSnow regardless of the surface below)
///   iceRisk   0..1 (freezing rain or a refreeze: interpolates towards Ice)
NYCSIM_API double frictionFor(SurfaceClass s, double wetness, double snowCover, double iceRisk);

/// The maximum acceleration a front-drive car can put down: mu * g * front weight fraction, with the
/// longitudinal load transfer that acceleration itself causes solved for.
NYCSIM_API double tractionLimitedAccelMps2(double mu, double frontWeightFraction, double cgHeightM,
                                           double wheelbaseM);

}  // namespace vehicle
}  // namespace nycsim
