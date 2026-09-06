#pragma once
// nycsim/traffic/Density.h — origin/destination calibration table
// (DATA_CONTRACTS §10 traffic/density.parquet, §15 runtime/density.nycb):
// NTA × hour × day-class → vehicles per lane-km, pedestrians per m² sidewalk
// and fleet shares.  Also carries the NTA polygons for assigning lanes and
// sidewalks to NTAs.  Hosts may inject cells directly (set/fill) — e.g. from
// live DOT counts — and the samplers pick them up on the next step.

#include <cstdint>
#include <string>
#include <string_view>
#include <vector>

#include "nycsim/routing/RoadGraph.h"

namespace nycsim {
namespace traffic {

struct DensityCell {
  float veh_per_km_lane = 0.f;
  float ped_per_m2 = 0.f;
  float taxi_share = 0.f;
  float truck_share = 0.f;
  float bus_share = 0.f;
  float bike_share = 0.f;
};

class DensityTable {
 public:
  static constexpr uint32_t kHours = 24, kDows = 3;

  void clear();
  uint16_t addNta(std::string_view code);        // idempotent, returns index
  uint16_t ntaIndex(std::string_view code) const;  // kNoNta if unknown
  uint16_t ntaCount() const { return static_cast<uint16_t>(codes_.size()); }
  const std::string& ntaCode(uint16_t i) const { return codes_[i]; }

  void set(uint16_t nta, uint8_t hour, uint8_t dow, const DensityCell& c);
  void fill(uint16_t nta, const DensityCell& c);  // every hour × dow
  bool has(uint16_t nta, uint8_t hour, uint8_t dow) const;
  // Missing cells fall back to the same hour on weekday, then to a zero cell.
  const DensityCell& get(uint16_t nta, uint8_t hour, uint8_t dow) const;

  // Polygons (NYC_TM metres, closed rings).
  void addPolygon(uint16_t nta, const routing::Vec3* pts, size_t n);
  size_t polygonCount() const { return polys_.size(); }
  bool pointInNta(float x, float y, uint16_t& nta) const;
  // Assigns lane.nta by the lane midpoint; returns the number assigned.
  uint32_t assignLaneNtas(routing::RoadGraph& g) const;

  bool loadFromNycb(const uint8_t* data, size_t len);
  const std::string& lastError() const { return error_; }

 private:
  struct Poly {
    uint16_t nta;
    uint32_t first, count;
    float minx, miny, maxx, maxy;
  };
  size_t slot(uint16_t nta, uint8_t hour, uint8_t dow) const {
    return (static_cast<size_t>(nta) * kDows + (dow > 2 ? 0 : dow)) * kHours + (hour % kHours);
  }
  std::vector<std::string> codes_;
  std::vector<DensityCell> cells_;
  std::vector<uint8_t> present_;
  std::vector<Poly> polys_;
  std::vector<routing::Vec3> poly_pts_;
  DensityCell zero_;
  std::string error_;
};

}  // namespace traffic
}  // namespace nycsim
