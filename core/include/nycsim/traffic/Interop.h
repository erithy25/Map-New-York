#pragma once
// nycsim/traffic/Interop.h — the two POD callback tables that let the traffic
// and pedestrian simulations see each other without either module depending on
// the other's types.  Plain function pointers: no virtual dispatch, no
// exceptions, no allocation; either side may be left empty (all queries then
// answer "nothing there", which degrades gracefully).
//
// The host wires them once:
//   traffic.setPedProbe(peds.pedProbe());
//   peds.setVehicleProbe(traffic.vehicleProbe());

#include <cstdint>

namespace nycsim {
namespace traffic {

// Pedestrians as seen by drivers.
struct PedProbe {
  const void* ctx = nullptr;
  // Number of pedestrians inside the disc of radius `r` around (x,y) that are
  // on the roadway (crosswalk or jaywalking).  Drivers must yield to them.
  uint32_t (*road_peds)(const void* ctx, float x, float y, float r) = nullptr;

  uint32_t roadPeds(float x, float y, float r) const {
    return road_peds != nullptr ? road_peds(ctx, x, y, r) : 0u;
  }
  bool valid() const { return road_peds != nullptr; }
};

// Vehicles as seen by pedestrians.
struct TaxiSighting {
  uint32_t agent = 0xFFFFFFFFu;
  float x = 0.f, y = 0.f;
  float distance = 0.f;
};

struct VehicleProbe {
  void* ctx = nullptr;
  // Shortest time-to-arrival, in seconds, of any vehicle that will reach the
  // disc of radius `r` around (x,y) — used for jaywalking gap acceptance.
  // Returns a large value when the road is clear.
  float (*time_to_arrival)(const void* ctx, float x, float y, float r) = nullptr;
  // Nearest taxi with its roof light on (available for hire) within `r`.
  bool (*free_taxi)(const void* ctx, float x, float y, float r, TaxiSighting& out) = nullptr;
  // Hail it: the taxi pulls to the curb at (x,y) and clears its roof light.
  bool (*hail)(void* ctx, uint32_t agent, float x, float y) = nullptr;

  float timeToArrival(float x, float y, float r) const {
    return time_to_arrival != nullptr ? time_to_arrival(ctx, x, y, r) : 1e9f;
  }
  bool freeTaxi(float x, float y, float r, TaxiSighting& out) const {
    return free_taxi != nullptr && free_taxi(ctx, x, y, r, out);
  }
  bool hailTaxi(uint32_t agent, float x, float y) const {
    return hail != nullptr && hail(ctx, agent, x, y);
  }
  bool valid() const { return time_to_arrival != nullptr; }
};

}  // namespace traffic
}  // namespace nycsim
