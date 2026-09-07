// nycsim/traffic/BusRoutes.cpp — see BusRoutes.h.
#include "nycsim/traffic/BusRoutes.h"

#include <algorithm>
#include <unordered_map>

#include "nycsim/routing/NycbLite.h"

namespace nycsim {
namespace traffic {

using routing::kInvalidIndex;

void BusRouteTable::clear() {
  routes_.clear();
  stops_.clear();
  route_stops_.clear();
  names_.clear();
  lane_stop_index_.clear();
  lane_first_.clear();
  lane_count_.clear();
  error_.clear();
  finalized_ = false;
}

uint32_t BusRouteTable::internName(std::string_view s) {
  for (uint32_t i = 0; i < names_.size(); ++i)
    if (names_[i] == s) return i;
  names_.emplace_back(s);
  return static_cast<uint32_t>(names_.size() - 1);
}

uint32_t BusRouteTable::addRoute(std::string_view name, const uint16_t headway_min[24]) {
  BusRoute r;
  r.name = internName(name);
  r.first_stop = static_cast<uint32_t>(route_stops_.size());
  r.stop_count = 0;
  for (int h = 0; h < 24; ++h) r.headway_min[h] = headway_min != nullptr ? headway_min[h] : 0u;
  routes_.push_back(r);
  finalized_ = false;
  return static_cast<uint32_t>(routes_.size() - 1);
}

uint32_t BusRouteTable::addStop(uint32_t route, int64_t id, uint32_t lane, float s, const routing::Vec3& pos,
                                std::string_view name, bool shelter) {
  BusStop st;
  st.id = id;
  st.lane = lane;
  st.s = s;
  st.pos = pos;
  st.name = internName(name);
  st.has_shelter = shelter ? 1u : 0u;
  stops_.push_back(st);
  const uint32_t si = static_cast<uint32_t>(stops_.size() - 1);
  if (route < routes_.size()) {
    // Stops must be appended route by route: the route's slice has to stay
    // contiguous.  Appending to any route other than the last one rebuilds the
    // slice, which only happens at load time.
    if (routes_[route].first_stop + routes_[route].stop_count == route_stops_.size()) {
      route_stops_.push_back(si);
      ++routes_[route].stop_count;
    } else {
      const uint32_t at = routes_[route].first_stop + routes_[route].stop_count;
      route_stops_.insert(route_stops_.begin() + static_cast<ptrdiff_t>(at), si);
      ++routes_[route].stop_count;
      for (uint32_t r = 0; r < routes_.size(); ++r)
        if (r != route && routes_[r].first_stop >= at) ++routes_[r].first_stop;
    }
  }
  finalized_ = false;
  return si;
}

uint32_t BusRouteTable::addStopAt(const routing::RoadGraph& g, uint32_t route, int64_t id, float x, float y, float z,
                                  std::string_view name, bool shelter, float snap_m) {
  const uint32_t kinds = routing::kBusLaneKinds;
  const routing::NearestLane n = g.nearestLane(x, y, kinds, snap_m, false);
  if (n.lane == kInvalidIndex) {
    error_ = "bus stop not within snap radius of any bus-capable lane";
    return kInvalidIndex;
  }
  routing::Vec3 p{x, y, z};
  return addStop(route, id, n.lane, n.s, p, name, shelter);
}

bool BusRouteTable::loadFromNycb(const uint8_t* data, size_t len, const routing::RoadGraph& g, float snap_m) {
  clear();
  nycb::File f;
  if (!f.open(data, len)) {
    error_ = f.error != nullptr ? f.error : "nycb: open failed";
    return false;
  }
  const nycb::Section routes = f.section("bus_routes");
  const nycb::Section stops = f.section("bus_stops");
  const nycb::Section rstops = f.section("route_stops");
  const nycb::Section strtab = f.section("strtab");
  if (!routes.present || !stops.present) {
    error_ = "transit.nycb: missing bus_routes/bus_stops sections";
    return false;
  }
  if (routes.element_size < 68 || stops.element_size < 24 || (rstops.present && rstops.element_size < 8)) {
    error_ = "transit.nycb: unexpected element sizes";
    return false;
  }

  // Snap every stop once.
  std::unordered_map<int64_t, uint32_t> stop_by_id;
  struct Raw {
    int64_t id;
    routing::Vec3 pos;
    uint32_t name;
    uint32_t lane;
    float s;
  };
  std::vector<Raw> raw(stops.element_count);
  for (uint32_t i = 0; i < stops.element_count; ++i) {
    const uint8_t* p = stops.at(i);
    Raw r;
    r.id = nycb::rdI64(p);
    r.pos = routing::Vec3{nycb::rdF32(p + 8), nycb::rdF32(p + 12), nycb::rdF32(p + 16)};
    r.name = nycb::rdU32(p + 20);
    const routing::NearestLane n = g.nearestLane(r.pos.x, r.pos.y, routing::kBusLaneKinds, snap_m, false);
    r.lane = n.lane;
    r.s = n.s;
    raw[i] = r;
    stop_by_id[r.id] = i;
  }

  uint32_t unsnapped = 0;
  for (uint32_t ri = 0; ri < routes.element_count; ++ri) {
    const uint8_t* p = routes.at(ri);
    const uint32_t name_str = nycb::rdU32(p);
    const uint32_t first_stop = nycb::rdU32(p + 12);
    const uint32_t stop_count = nycb::rdU32(p + 16);
    uint16_t headway[24];
    for (int h = 0; h < 24; ++h) headway[h] = nycb::rdU16(p + 20 + 2 * h);
    const uint32_t route = addRoute(nycb::File::str(strtab, name_str), headway);
    if (!rstops.present) continue;
    for (uint32_t k = 0; k < stop_count; ++k) {
      const uint32_t at = first_stop + k;
      if (at >= rstops.element_count) break;
      const int64_t sid = nycb::rdI64(rstops.at(at));
      auto it = stop_by_id.find(sid);
      if (it == stop_by_id.end()) continue;
      const Raw& r = raw[it->second];
      if (r.lane == kInvalidIndex) {
        ++unsnapped;
        continue;
      }
      addStop(route, r.id, r.lane, r.s, r.pos, nycb::File::str(strtab, r.name), false);
    }
  }
  finalize();
  if (unsnapped != 0) {
    error_ = "transit.nycb: " + std::to_string(unsnapped) + " stops had no bus-capable lane within the snap radius";
  }
  return true;
}

void BusRouteTable::finalize() {
  lane_stop_index_.clear();
  lane_stop_index_.reserve(stops_.size());
  for (uint32_t i = 0; i < stops_.size(); ++i)
    if (stops_[i].lane != kInvalidIndex) lane_stop_index_.push_back(i);
  std::sort(lane_stop_index_.begin(), lane_stop_index_.end(), [this](uint32_t a, uint32_t b) {
    if (stops_[a].lane != stops_[b].lane) return stops_[a].lane < stops_[b].lane;
    if (stops_[a].s != stops_[b].s) return stops_[a].s < stops_[b].s;
    return stops_[a].id < stops_[b].id;
  });
  uint32_t max_lane = 0;
  for (uint32_t i : lane_stop_index_) max_lane = std::max(max_lane, stops_[i].lane);
  lane_first_.assign(static_cast<size_t>(max_lane) + 2, 0u);
  lane_count_.assign(static_cast<size_t>(max_lane) + 2, 0u);
  for (uint32_t k = 0; k < lane_stop_index_.size(); ++k) {
    const uint32_t lane = stops_[lane_stop_index_[k]].lane;
    if (lane_count_[lane] == 0) lane_first_[lane] = k;
    ++lane_count_[lane];
  }
  finalized_ = true;
}

const uint32_t* BusRouteTable::stopsOnLane(uint32_t lane, uint32_t& n) const {
  if (!finalized_ || lane >= lane_count_.size() || lane_count_[lane] == 0) {
    n = 0;
    return nullptr;
  }
  n = lane_count_[lane];
  return lane_stop_index_.data() + lane_first_[lane];
}

float BusRouteTable::headwaySeconds(uint32_t route, uint8_t hour) const {
  if (route >= routes_.size()) return 0.f;
  const uint16_t m = routes_[route].headway_min[hour % 24];
  return static_cast<float>(m) * 60.f;
}

}  // namespace traffic
}  // namespace nycsim
