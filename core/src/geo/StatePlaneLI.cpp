#include "nycsim/geo/StatePlaneLI.h"

#include "nycsim/geo/NycTm.h"
#include "nycsim/geo/Units.h"

namespace nycsim {
namespace geo {

const LambertConformalConic& statePlaneLI() {
  static const LambertConformalConic lcc(kStatePlaneLIParams);
  return lcc;
}

Result<XY> lonLatToStatePlaneFt(double lon_deg, double lat_deg) {
  auto r = statePlaneLI().forward(LatLon{lat_deg, lon_deg});
  if (!r) return r.error();
  return XY{units::mToUsFt(r->x), units::mToUsFt(r->y)};
}

Result<LatLon> statePlaneFtToLonLat(double x_ft, double y_ft) {
  return statePlaneLI().inverse(XY{units::usFtToM(x_ft), units::usFtToM(y_ft)});
}

Result<XY> statePlaneFtToTm(double x_ft, double y_ft) {
  auto ll = statePlaneFtToLonLat(x_ft, y_ft);
  if (!ll) return ll.error();
  // NAD83 ~ WGS84 (null shift), see header.
  return nycTm().forward(*ll);
}

Result<XY> tmToStatePlaneFt(double x_m, double y_m) {
  auto ll = nycTm().inverse(XY{x_m, y_m});
  if (!ll) return ll.error();
  return lonLatToStatePlaneFt(ll->lon_deg, ll->lat_deg);
}

}  // namespace geo
}  // namespace nycsim
