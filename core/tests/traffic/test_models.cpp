// Unit properties of the behaviour models themselves: IDM, MOBIL, the fleet
// table, the social-force kernel and the player protection ring.
#include <doctest/doctest.h>

#include <cmath>

#include "nycsim/peds/SocialForce.h"
#include "nycsim/traffic/Idm.h"
#include "nycsim/traffic/Mobil.h"
#include "nycsim/traffic/PlayerProxy.h"
#include "nycsim/traffic/VehicleClass.h"

using namespace nycsim;
using namespace nycsim::traffic;

TEST_SUITE("traffic") {

TEST_CASE("IDM free flow relaxes to the desired speed") {
  IdmParams p;
  p.v0 = 11.176f;
  float v = 0.f;
  for (int i = 0; i < 4000; ++i) v += idmFreeAccel(p, v) * 0.05f;
  CHECK(v == doctest::Approx(p.v0).epsilon(0.01));
  CHECK(idmFreeAccel(p, 0.f) == doctest::Approx(p.a));
  CHECK(idmFreeAccel(p, p.v0) == doctest::Approx(0.f).epsilon(0.001));
  CHECK(idmFreeAccel(p, p.v0 * 1.2f) < 0.f);
}

TEST_CASE("IDM never lets a follower reach its leader") {
  IdmParams p;
  p.v0 = 15.f;
  // Leader brakes to a stop from 15 m/s while the follower starts 8 m behind.
  float lead_s = 8.f, lead_v = 15.f;
  float me_s = 0.f, me_v = 15.f;
  float min_gap = 1e9f;
  for (int i = 0; i < 2000; ++i) {
    const float gap = lead_s - me_s;
    min_gap = std::min(min_gap, gap);
    const float a = idmAccel(p, me_v, gap, me_v - lead_v);
    me_v = std::max(0.f, me_v + a * 0.05f);
    me_s += me_v * 0.05f;
    lead_v = std::max(0.f, lead_v - 4.f * 0.05f);  // hard braking leader
    lead_s += lead_v * 0.05f;
  }
  CHECK(min_gap > 0.f);
  CHECK(me_v == doctest::Approx(0.f).epsilon(0.01));
}

TEST_CASE("IDM stops short of a stationary obstacle") {
  for (VehicleClass c : {VehicleClass::Sedan, VehicleClass::MtaBus, VehicleClass::BoxTruck,
                         VehicleClass::Cyclist}) {
    const VehicleClassParams& cp = classParams(c);
    IdmParams p;
    p.a = cp.max_accel;
    p.b = cp.comfort_decel;
    p.b_max = cp.max_decel;
    p.T = cp.headway_T;
    p.s0 = cp.min_gap_s0;
    p.v0 = 12.f;
    float s = 0.f, v = 12.f;
    const float obstacle = 90.f;
    for (int i = 0; i < 4000; ++i) {
      const float a = idmStopAccel(p, v, obstacle - s);
      v = std::max(0.f, v + a * 0.05f);
      s += v * 0.05f;
    }
    CHECK_MESSAGE(s < obstacle, className(c));
    CHECK(v < 0.05f);
  }
}

TEST_CASE("IDM equilibrium spacing matches the analytic value") {
  IdmParams p;
  p.v0 = 11.176f;
  // At equilibrium (Δv = 0, a = 0): s = (s0 + vT) / sqrt(1 − (v/v0)^4).
  const float v = 8.f;
  const float expect = (p.s0 + v * p.T) / std::sqrt(1.f - std::pow(v / p.v0, 4.f));
  CHECK(idmAccel(p, v, expect, 0.f) == doctest::Approx(0.f).epsilon(0.02));
}

TEST_CASE("stopping distance and curve speed are physical") {
  CHECK(stoppingDistance(0.f, 3.f, 1.f) == doctest::Approx(0.f));
  CHECK(stoppingDistance(20.f, 3.4f, 1.f) == doctest::Approx(20.f + 400.f / 6.8f).epsilon(1e-4));
  CHECK(curveSpeed(9.f, 1.5f) == doctest::Approx(std::sqrt(13.5f)));
  CHECK(curveSpeed(0.f, 1.5f) > 0.f);
}

TEST_CASE("MOBIL accepts a clear lane and refuses an unsafe one") {
  MobilInput in;
  in.a_self = -1.5f;      // stuck behind a slow leader
  in.a_self_new = 0.8f;   // free in the target lane
  in.politeness = 0.2f;
  in.threshold = 0.2f;
  MobilResult r = mobilEvaluate(in);
  CHECK(r.safe);
  CHECK(r.accept);
  CHECK(r.advantage == doctest::Approx(2.3f));

  SUBCASE("safety criterion dominates") {
    in.a_new_follower_new = -6.f;  // the follower would have to brake at 6 m/s²
    r = mobilEvaluate(in);
    CHECK(!r.safe);
    CHECK(!r.accept);
  }
  SUBCASE("explicit gap acceptance") {
    in.gap_rear = 1.0f;
    r = mobilEvaluate(in);
    CHECK(!r.accept);
  }
  SUBCASE("politeness can veto a selfish change") {
    in.a_self_new = -1.3f;             // marginal gain for me
    in.a_new_follower = 0.5f;
    in.a_new_follower_new = -2.5f;     // big loss for the new follower
    in.politeness = 0.8f;
    r = mobilEvaluate(in);
    CHECK(r.safe);
    CHECK(!r.accept);
  }
  SUBCASE("bias lets a mandatory change through") {
    in.a_self_new = -1.6f;  // slightly worse than staying
    in.bias = 5.f;
    r = mobilEvaluate(in);
    CHECK(r.accept);
  }
}

TEST_CASE("fleet table covers the ADR-009 bodies with sane parameters") {
  CHECK(kVehicleClassCount == 18u);
  uint32_t emergency = 0, buses = 0, bikes = 0, trucks = 0, taxis = 0;
  for (uint32_t i = 0; i < kVehicleClassCount; ++i) {
    const VehicleClass c = static_cast<VehicleClass>(i);
    const VehicleClassParams& p = classParams(c);
    CAPTURE(p.name);
    CHECK(p.length_m > 1.0f);
    CHECK(p.length_m < 14.f);
    CHECK(p.width_m > 0.5f);
    CHECK(p.height_m > 1.0f);
    CHECK(p.max_accel > 0.f);
    CHECK(p.comfort_decel > 0.f);
    CHECK(p.max_decel >= p.comfort_decel);
    CHECK(p.headway_T > 0.5f);
    CHECK(p.min_gap_s0 >= 1.f);
    CHECK(p.max_speed_mps > 2.5f);
    CHECK(p.politeness >= 0.f);
    CHECK(p.politeness <= 1.f);
    CHECK(p.law_abiding_share >= 0.f);
    CHECK(p.law_abiding_share <= 1.f);
    CHECK(p.lane_kinds != 0u);
    if (p.is_emergency) ++emergency;
    if (p.is_bus) ++buses;
    if (p.is_bike) ++bikes;
    if (p.is_truck) ++trucks;
    if (p.is_taxi) ++taxis;
  }
  CHECK(emergency == 4u);  // NYPD, FDNY engine, FDNY ladder, ambulance
  CHECK(buses == 1u);
  CHECK(bikes == 3u);      // bicycle, e-bike, pedicab
  CHECK(trucks >= 4u);
  CHECK(taxis == 2u);      // yellow medallion + green boro taxi
  // Trucks and buses keep longer headways than cars.
  CHECK(classParams(VehicleClass::MtaBus).headway_T > classParams(VehicleClass::Sedan).headway_T);
  CHECK(classParams(VehicleClass::Taxi).headway_T < classParams(VehicleClass::Sedan).headway_T);
  CHECK(classParams(VehicleClass::Taxi).law_abiding_share < classParams(VehicleClass::Nypd).law_abiding_share);
}

TEST_CASE("player protection ring covers the view cone and the near field") {
  PlayerProxy p;
  p.valid = true;
  p.x = 0.f;
  p.y = 0.f;
  p.heading_rad = 0.f;  // facing +x
  p.no_spawn_radius_m = 250.f;
  p.near_radius_m = 60.f;
  p.view_half_angle_deg = 55.f;

  CHECK(p.inProtectedRegion(200.f, 0.f));          // straight ahead
  CHECK(p.inProtectedRegion(150.f, 150.f));        // 45° — inside the cone
  CHECK(!p.inProtectedRegion(0.f, 200.f));         // 90° to the side, beyond the near ring
  CHECK(!p.inProtectedRegion(-200.f, 0.f));        // behind
  CHECK(p.inProtectedRegion(-40.f, 0.f));          // behind but inside the near ring
  CHECK(!p.inProtectedRegion(400.f, 0.f));         // beyond the ring
  CHECK(p.inProtectedRegion(0.f, 0.f));
  p.valid = false;
  CHECK(!p.inProtectedRegion(10.f, 0.f));
}

TEST_CASE("expNegApprox is accurate enough for the social force") {
  double worst_rel = 0.0, worst_abs = 0.0;
  for (int i = 0; i <= 6000; ++i) {
    const float x = static_cast<float>(i) * 0.001f;  // [0, 6]
    const double got = static_cast<double>(peds::expNegApprox(x));
    const double want = std::exp(-static_cast<double>(x));
    worst_abs = std::max(worst_abs, std::fabs(got - want));
    if (want > 1e-4) worst_rel = std::max(worst_rel, std::fabs(got - want) / want);
  }
  MESSAGE("expNegApprox max relative error over [0,6]: " << worst_rel);
  CHECK(worst_rel < 0.01);
  CHECK(worst_abs < 0.001);
  CHECK(peds::expNegApprox(0.f) == doctest::Approx(1.f));
  CHECK(peds::expNegApprox(-1.f) == doctest::Approx(1.f));
  CHECK(peds::expNegApprox(1000.f) == doctest::Approx(0.f));
  // Monotone decreasing.
  float prev = 2.f;
  for (int i = 0; i <= 600; ++i) {
    const float y = peds::expNegApprox(static_cast<float>(i) * 0.01f);
    CHECK(y <= prev);
    prev = y;
  }
}

TEST_CASE("social force pushes bodies apart and drives towards the target") {
  peds::SocialForceParams sp;
  const peds::Force2 d = peds::drivingForce(sp, 1.4f, 1.f, 0.f, 0.f, 0.f);
  CHECK(d.x == doctest::Approx(2.8f));
  CHECK(d.y == doctest::Approx(0.f));
  // j is directly ahead of i (i at origin heading +x, j at +0.5 m).
  const peds::Force2 r = peds::pedRepulsion(sp, -0.5f, 0.f, 0.5f, 0.5f, 1.f, 0.f);
  CHECK(r.x < 0.f);  // pushed backwards
  // The same neighbour behind me pushes less (anisotropy).
  const peds::Force2 back = peds::pedRepulsion(sp, 0.5f, 0.f, 0.5f, 0.5f, 1.f, 0.f);
  CHECK(std::fabs(back.x) < std::fabs(r.x));
  CHECK(std::fabs(back.x) == doctest::Approx(std::fabs(r.x) * sp.lambda).epsilon(0.02));
  // Contact term kicks in below the body radius sum.
  const peds::Force2 touch = peds::pedRepulsion(sp, -0.2f, 0.f, 0.2f, 0.5f, 1.f, 0.f);
  CHECK(std::fabs(touch.x) > 10.f);
}

}  // TEST_SUITE
