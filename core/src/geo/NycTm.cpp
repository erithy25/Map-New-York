#include "nycsim/geo/NycTm.h"

namespace nycsim {
namespace geo {

const TransverseMercator& nycTm() {
  // Function-local static: constructed on first use (pure arithmetic, no I/O), thread-safe per
  // C++11. Deliberately not a namespace-scope object to avoid static initialisation order issues
  // in engine modules.
  static const TransverseMercator tm(kNycTmParams);
  return tm;
}

Result<XY> lonLatToTm(double lon_deg, double lat_deg) {
  return nycTm().forward(LatLon{lat_deg, lon_deg});
}

Result<LatLon> tmToLonLat(double x_m, double y_m) { return nycTm().inverse(XY{x_m, y_m}); }

}  // namespace geo
}  // namespace nycsim
