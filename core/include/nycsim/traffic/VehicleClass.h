#pragma once
// nycsim/traffic/VehicleClass.h — the AI fleet (ADR-009 bodies) with
// published dimensions and driver-model parameters.  See REPORT.md §Calibration
// for every source; values marked "assumed" in the table are stated as such.

#include <cstdint>

#include "nycsim/routing/RoadGraph.h"

namespace nycsim {
namespace traffic {

enum class VehicleClass : uint8_t {
  Sedan = 0,
  Taxi,
  BoroTaxi,
  BlackCar,
  Suv,
  Nypd,
  FdnyEngine,
  FdnyLadder,
  Ambulance,
  MtaBus,
  BoxTruck,
  DsnyTruck,
  Van,
  Cyclist,
  Ebike,
  Moped,
  Pedicab,
  HorseCarriage,
  Count
};
constexpr uint32_t kVehicleClassCount = static_cast<uint32_t>(VehicleClass::Count);

struct VehicleClassParams {
  const char* name;
  const char* body;  // ADR-009 body the Blender vehicles agent produces
  // Published overall dimensions of that body, metres.
  float length_m, width_m, height_m;
  // Longitudinal model (IDM, Treiber/Hennecke/Helbing 2000) — class specific.
  float max_accel;      // a   [m/s²]
  float comfort_decel;  // b   [m/s²]
  float max_decel;      // emergency braking cap [m/s²]
  float headway_T;      // T   [s]
  float min_gap_s0;     // s0  [m]  (bumper-to-bumper standing gap)
  float desired_speed_factor;  // v0 = factor × posted speed
  float max_speed_mps;         // hard cap (legal or physical)
  // Lateral model (MOBIL, Kesting/Treiber/Helbing 2007): politeness p and
  // lane-change duration.
  float politeness;
  float lane_change_s;
  // Behavioural shares / rates (calibratable at runtime through TrafficConfig).
  float honk_propensity;         // probability a blocked/cut-off event produces a honk
  float law_abiding_share;       // share of agents that never enter on red
  float double_park_rate_per_km; // commercial segments with a parking lane
  // Capabilities.
  uint32_t lane_kinds;  // routing lane-kind mask
  bool allow_highway;
  bool is_emergency;
  bool is_bus;
  bool is_bike;   // cyclists / e-bikes: bike lanes, filtering
  bool is_truck;  // commercial vehicles (truck route rules, wider turning)
  bool is_taxi;   // roof-light / hail behaviour
};

const VehicleClassParams& classParams(VehicleClass c);
inline const char* className(VehicleClass c) { return classParams(c).name; }

}  // namespace traffic
}  // namespace nycsim
