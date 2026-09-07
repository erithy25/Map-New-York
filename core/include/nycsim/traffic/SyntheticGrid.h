#pragma once
// nycsim/traffic/SyntheticGrid.h — a Manhattan-like test network: one-way
// avenues alternating north/south (1st Ave north, 2nd Ave south, …), one-way
// cross streets alternating east/west (even streets eastbound), avenue blocks
// ≈ 280 m, street blocks ≈ 80 m, 3 travel lanes + parking on avenues, 1 travel
// lane + parking on streets, optional parking-protected bike lanes, pretimed
// two-phase signals with LPI and northbound progression offsets.
//
// Used by the routing/traffic/pedestrian tests and the benchmark; also usable
// by the UE debug map before real data is loaded.

#include <cstdint>
#include <string>

#include "nycsim/routing/RoadGraph.h"
#include "nycsim/traffic/Signals.h"

namespace nycsim {
namespace traffic {

struct SyntheticGridSpec {
  int avenues = 6;
  int streets = 12;
  float avenue_spacing_m = 280.f;  // Manhattan long block (≈ 920 ft between avenues)
  float street_spacing_m = 80.f;   // Manhattan short block (≈ 264 ft)
  int avenue_travel_lanes = 3;
  int street_travel_lanes = 1;
  bool parking_lanes = true;
  int bike_lane_every = 3;        // every k-th avenue (0 = none) gets a parking-protected bike lane
  int two_way_avenue_every = 0;   // every k-th avenue two-way (0 = none)
  int stop_sign_every = 0;        // every k-th cross street stop-controlled instead of signalized (0 = none)
  float avenue_speed_mph = 25.f;
  float street_speed_mph = 25.f;
  float lane_width_m = 3.0f;
  float parking_width_m = 2.5f;
  float bike_width_m = 1.8f;
  float cycle_s = 90.f;
  float yellow_s = 3.f;
  float allred_s = 2.f;
  float lpi_s = 7.f;
  float progression_speed_mps = 11.2f;  // offsets along the avenue direction
  bool commercial_avenues = true;
  bool allow_uturns = false;
  float origin_x = 0.f;
  float origin_y = 0.f;
  int first_street_number = 34;  // "W 34th St" …
};

class SyntheticGrid {
 public:
  // Builds the graph (finalized) and the signal plans (bound).  All lanes get
  // NTA index 0.  Returns false with `error` on failure.
  static bool build(const SyntheticGridSpec& spec, routing::RoadGraph& g, SignalTable& signals, std::string* error = nullptr);

  static routing::NodeId nodeId(int i, int j) { return 1 + static_cast<int64_t>(j) * 1000 + i; }
  static routing::SegmentId avenueSegmentId(int i, int j) { return 100000 + static_cast<int64_t>(j) * 1000 + i; }  // avenue i, street j → j+1
  static routing::SegmentId streetSegmentId(int i, int j) { return 200000 + static_cast<int64_t>(j) * 1000 + i; }  // street j, avenue i → i+1
  static routing::LaneId laneId(routing::SegmentId seg, int index, int direction) {
    return seg * 100 + index + (direction < 0 ? 50 : 0);
  }
  static bool avenueTwoWay(const SyntheticGridSpec& s, int i) {
    return s.two_way_avenue_every > 0 && (i % s.two_way_avenue_every) == s.two_way_avenue_every - 1;
  }
  static bool avenueNorthbound(int i) { return (i % 2) == 0; }
  static bool streetEastbound(int j) { return (j % 2) == 0; }
  static bool avenueHasBikeLane(const SyntheticGridSpec& s, int i) { return s.bike_lane_every > 0 && (i % s.bike_lane_every) == 0; }
  static bool streetStopControlled(const SyntheticGridSpec& s, int j) {
    return s.stop_sign_every > 0 && (j % s.stop_sign_every) == s.stop_sign_every - 1;
  }
  static void avenueName(int i, char* buf, size_t n);
  static void streetName(const SyntheticGridSpec& s, int j, char* buf, size_t n);
};

}  // namespace traffic
}  // namespace nycsim
