// nycsim/traffic/VehicleClass.cpp — fleet parameter table.
//
// Dimensions: manufacturer specification sheets for the ADR-009 bodies
// (overall length × width × height, metres, rounded to 5 mm).  Bicycle,
// e-bike, pedicab and horse-carriage dimensions are typical values for the
// NYC fleet (Arrow 10 e-bike, Main Street Pedicabs 3-wheeler, Central Park
// vis-à-vis carriage with horse) and are marked "typical" in REPORT.md.
//
// IDM parameters follow Treiber & Kesting, "Traffic Flow Dynamics" (2013)
// Table 11.2 (cars a=1.0–1.5, b=1.5–2.0, T=1.0–1.5, s0=2) and Table 11.3 for
// trucks (a=0.7, b=1.5, T=1.7, s0=2.5), tightened for New York (shorter
// headways, higher accelerations for taxis) as documented in REPORT.md.
#include "nycsim/traffic/VehicleClass.h"

namespace nycsim {
namespace traffic {

namespace {

using routing::kBikeLaneKinds;
using routing::kBusLaneKinds;
using routing::kEmergencyLaneKinds;
using routing::kMotorLaneKinds;

constexpr float mph(float v) { return v * 0.44704f; }

// clang-format off
const VehicleClassParams kTable[kVehicleClassCount] = {
  //  name            body                          L      W      H     a     b     bmax  T     s0    v0f   vmax        p     lcT  honk  law   dp/km  kinds                hwy    emerg  bus    bike   truck  taxi
  { "sedan",          "Toyota Camry XV70",          4.885f, 1.840f, 1.445f, 1.4f, 2.0f, 8.0f, 1.1f, 2.0f, 1.10f, mph(75.f),  0.20f, 3.0f, 0.50f, 0.98f, 0.0f, kMotorLaneKinds,     true,  false, false, false, false, false },
  { "taxi",           "Toyota Camry Hybrid (yellow medallion)", 4.885f, 1.840f, 1.445f, 1.8f, 2.5f, 8.0f, 0.9f, 1.5f, 1.15f, mph(75.f), 0.10f, 2.2f, 0.90f, 0.97f, 0.6f, kMotorLaneKinds, true, false, false, false, false, true },
  { "boro_taxi",      "Toyota RAV4 Hybrid (green SHL)", 4.600f, 1.855f, 1.685f, 1.6f, 2.3f, 8.0f, 1.0f, 1.5f, 1.12f, mph(75.f), 0.12f, 2.4f, 0.85f, 0.97f, 0.5f, kMotorLaneKinds, true, false, false, false, false, true },
  { "black_car",      "Chevrolet Suburban",         5.733f, 2.057f, 1.927f, 1.5f, 2.0f, 7.5f, 1.1f, 2.0f, 1.10f, mph(75.f),  0.18f, 3.2f, 0.60f, 0.98f, 0.8f, kMotorLaneKinds,     true,  false, false, false, false, false },
  { "suv",            "Toyota RAV4 Hybrid",         4.600f, 1.855f, 1.685f, 1.3f, 2.0f, 8.0f, 1.2f, 2.0f, 1.08f, mph(75.f),  0.22f, 3.2f, 0.50f, 0.98f, 0.0f, kMotorLaneKinds,     true,  false, false, false, false, false },
  { "nypd",           "Ford Police Interceptor Utility", 5.050f, 2.004f, 1.778f, 2.5f, 3.0f, 9.0f, 1.0f, 2.0f, 1.05f, mph(90.f), 0.25f, 2.5f, 0.30f, 1.00f, 0.3f, kEmergencyLaneKinds, true, true, false, false, false, false },
  { "fdny_engine",    "Seagrave Marauder II pumper", 9.900f, 2.540f, 3.200f, 1.0f, 2.0f, 6.0f, 1.4f, 2.5f, 1.00f, mph(60.f), 0.30f, 4.0f, 0.20f, 1.00f, 0.0f, kEmergencyLaneKinds, true, true, false, false, true, false },
  { "fdny_ladder",    "Seagrave Aerialscope 75 ft tower ladder", 12.800f, 2.590f, 3.500f, 0.8f, 1.8f, 5.5f, 1.6f, 2.5f, 1.00f, mph(55.f), 0.30f, 4.5f, 0.20f, 1.00f, 0.0f, kEmergencyLaneKinds, true, true, false, false, true, false },
  { "ambulance",      "Ford F-450 Type I",          7.300f, 2.440f, 2.900f, 1.6f, 2.5f, 7.0f, 1.2f, 2.5f, 1.05f, mph(70.f),  0.25f, 3.0f, 0.20f, 1.00f, 0.0f, kEmergencyLaneKinds, true,  true,  false, false, true,  false },
  { "mta_bus",        "New Flyer XD40",             12.500f, 2.590f, 3.300f, 0.9f, 1.5f, 5.0f, 1.5f, 2.5f, 1.00f, mph(50.f), 0.30f, 4.5f, 0.30f, 1.00f, 0.0f, kBusLaneKinds,      true,  false, true,  false, false, false },
  { "box_truck",      "Isuzu NPR 16 ft box",        7.600f, 2.400f, 3.500f, 0.8f, 1.5f, 5.5f, 1.6f, 2.5f, 1.00f, mph(65.f),  0.30f, 4.0f, 0.70f, 0.98f, 2.0f, kMotorLaneKinds,     true,  false, false, false, true,  false },
  { "dsny_truck",     "Mack LR rear loader",        9.600f, 2.600f, 3.700f, 0.7f, 1.5f, 5.0f, 1.7f, 2.5f, 0.95f, mph(55.f),  0.35f, 4.5f, 0.50f, 1.00f, 1.0f, kMotorLaneKinds,     true,  false, false, false, true,  false },
  { "van",            "Mercedes-Benz Sprinter 144\"", 5.932f, 2.020f, 2.438f, 1.2f, 1.8f, 7.0f, 1.3f, 2.0f, 1.05f, mph(70.f), 0.25f, 3.2f, 0.70f, 0.97f, 3.0f, kMotorLaneKinds,    true,  false, false, false, true,  false },
  { "cyclist",        "road/hybrid bicycle (typical)", 1.750f, 0.650f, 1.800f, 1.0f, 2.0f, 4.0f, 1.0f, 1.0f, 0.60f, 7.0f,     0.10f, 1.5f, 0.10f, 0.60f, 0.0f, kBikeLaneKinds,      false, false, false, true,  false, false },
  { "ebike",          "Arrow 10 (typical)",         1.850f, 0.700f, 1.800f, 1.5f, 2.5f, 4.5f, 0.9f, 1.0f, 0.80f, 8.9f,       0.05f, 1.2f, 0.20f, 0.50f, 0.0f, kBikeLaneKinds,      false, false, false, true,  false, false },
  { "moped",          "Vespa GTS 300",              1.950f, 0.770f, 1.340f, 2.0f, 3.0f, 6.0f, 0.9f, 1.5f, 1.00f, 13.4f,      0.10f, 1.5f, 0.60f, 0.70f, 0.0f, kMotorLaneKinds,     false, false, false, false, false, false },
  { "pedicab",        "3-wheel pedicab (typical)",  2.800f, 1.200f, 1.800f, 0.8f, 1.5f, 3.0f, 1.5f, 1.5f, 0.40f, 4.5f,       0.30f, 3.0f, 0.10f, 0.90f, 0.0f, kBikeLaneKinds,      false, false, false, true,  false, false },
  { "horse_carriage", "vis-à-vis carriage + horse (typical)", 6.500f, 1.800f, 2.200f, 0.5f, 1.0f, 2.0f, 2.0f, 2.0f, 0.30f, 3.0f, 0.40f, 5.0f, 0.00f, 1.00f, 0.0f, kMotorLaneKinds,  false, false, false, false, false, false },
};
// clang-format on

}  // namespace

const VehicleClassParams& classParams(VehicleClass c) {
  const uint32_t i = static_cast<uint32_t>(c);
  return kTable[i < kVehicleClassCount ? i : 0u];
}

}  // namespace traffic
}  // namespace nycsim
