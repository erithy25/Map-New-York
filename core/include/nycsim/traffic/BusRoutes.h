#pragma once
// nycsim/traffic/BusRoutes.h — MTA bus routes and stops for the traffic AI
// (DATA_CONTRACTS §9 transit/bus_routes.parquet + bus_stops.parquet, §15
// runtime/transit.nycb).  Stops are snapped onto the lane graph once, at load
// time, so the driving loop only ever compares metres along a lane.

#include <cstdint>
#include <string>
#include <string_view>
#include <vector>

#include "nycsim/routing/RoadGraph.h"

namespace nycsim {
namespace traffic {

struct BusStop {
  int64_t id = 0;
  uint32_t lane = routing::kInvalidIndex;  // curb-side travel or bus lane
  float s = 0.f;                           // metres along that lane
  routing::Vec3 pos;
  uint32_t name = 0;  // index into names()
  uint8_t has_shelter = 0;
};

struct BusRoute {
  uint32_t name = 0;
  uint32_t first_stop = 0, stop_count = 0;  // into routeStops()
  uint16_t headway_min[24] = {0};
};

class BusRouteTable {
 public:
  void clear();
  uint32_t addRoute(std::string_view name, const uint16_t headway_min[24]);
  // Adds a stop and appends it to `route`.  `lane` must already be resolved;
  // use addStopAt() to snap from a world position.
  uint32_t addStop(uint32_t route, int64_t id, uint32_t lane, float s, const routing::Vec3& pos,
                   std::string_view name, bool shelter = false);
  // Snaps (x,y) to the nearest lane a bus may use (travel or bus lane) within
  // `snap_m`; returns kInvalidIndex when nothing is close enough.
  uint32_t addStopAt(const routing::RoadGraph& g, uint32_t route, int64_t id, float x, float y, float z,
                     std::string_view name, bool shelter = false, float snap_m = 25.f);
  // §15 runtime/transit.nycb (`bus_routes`, `bus_stops`, `route_stops`,
  // `vertices`, `strtab`).  Stops are snapped against `g`.
  bool loadFromNycb(const uint8_t* data, size_t len, const routing::RoadGraph& g, float snap_m = 25.f);

  size_t routeCount() const { return routes_.size(); }
  size_t stopCount() const { return stops_.size(); }
  const BusRoute& route(uint32_t i) const { return routes_[i]; }
  const BusStop& stop(uint32_t i) const { return stops_[i]; }
  const uint32_t* routeStops(uint32_t route, uint32_t& n) const {
    n = routes_[route].stop_count;
    return route_stops_.data() + routes_[route].first_stop;
  }
  std::string_view name(uint32_t i) const { return i < names_.size() ? std::string_view(names_[i]) : std::string_view(); }
  // Stops sorted by (lane, s) so the driving loop can find "the next stop on
  // this lane after s" without scanning the whole table.
  const uint32_t* stopsOnLane(uint32_t lane, uint32_t& n) const;
  // Headway [s] for the route at the given hour; 0 when the route does not run.
  float headwaySeconds(uint32_t route, uint8_t hour) const;
  const std::string& lastError() const { return error_; }
  // Call after the last addStop/addStopAt (loadFromNycb does it internally).
  void finalize();

 private:
  uint32_t internName(std::string_view s);
  std::vector<BusRoute> routes_;
  std::vector<BusStop> stops_;
  std::vector<uint32_t> route_stops_;
  std::vector<std::string> names_;
  std::vector<uint32_t> lane_stop_index_;  // stop indices sorted by (lane, s)
  std::vector<uint32_t> lane_first_, lane_count_;
  std::string error_;
  bool finalized_ = false;
};

}  // namespace traffic
}  // namespace nycsim
