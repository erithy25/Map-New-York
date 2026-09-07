#pragma once
// nycsim/traffic/Mobil.h — MOBIL lane-change model (Kesting, Treiber & Helbing,
// "General lane-changing model MOBIL for car-following models",
// Transportation Research Record 1999 (2007), 86–94).
//
//   safety:    ã_new_follower ≥ −b_safe
//   incentive: (ã_self − a_self) + p·[(ã_nf − a_nf) + (ã_of − a_of)] > Δa_th − Δa_bias
//
// p is the politeness (0 = selfish, 1 = altruistic; NYCSim default 0.2, the
// per-class values in VehicleClass.cpp deviate around it), Δa_th the switching
// threshold (0.2 m/s²) and Δa_bias a signed bias used for
//   * the keep-right / stay-out-of-the-bus-lane rule,
//   * route pressure: a mandatory change onto the lane that carries the next
//     turn, which grows without bound as the junction approaches, and
//   * the cyclist preference for a bike lane.
// A mandatory change also relaxes the threshold but never the safety criterion
// or the explicit gap acceptance below.

#include <algorithm>

namespace nycsim {
namespace traffic {

struct MobilInput {
  float a_self = 0.f;      // current acceleration in the present lane
  float a_self_new = 0.f;  // acceleration if the change were made
  float a_new_follower = 0.f;
  float a_new_follower_new = 0.f;
  float a_old_follower = 0.f;
  float a_old_follower_new = 0.f;
  float politeness = 0.2f;
  float threshold = 0.2f;   // Δa_th [m/s²]
  float bias = 0.f;         // Δa_bias [m/s²], positive favours the change
  float b_safe = 4.0f;      // maximum deceleration imposed on the new follower
  // Explicit gap acceptance (metres, bumper to bumper) on top of the
  // acceleration criteria — MOBIL's safety criterion alone allows very small
  // gaps at low speed, which looks wrong on a screen.
  float gap_front = 1e9f;
  float gap_rear = 1e9f;
  float min_gap_front = 3.f;
  float min_gap_rear = 3.f;
};

struct MobilResult {
  bool safe = false;
  bool accept = false;
  float advantage = 0.f;  // the left-hand side of the incentive criterion
};

inline MobilResult mobilEvaluate(const MobilInput& in) {
  MobilResult r;
  r.safe = in.a_new_follower_new >= -in.b_safe && in.gap_front >= in.min_gap_front &&
           in.gap_rear >= in.min_gap_rear;
  r.advantage = (in.a_self_new - in.a_self) +
                in.politeness * ((in.a_new_follower_new - in.a_new_follower) +
                                 (in.a_old_follower_new - in.a_old_follower));
  r.accept = r.safe && r.advantage > (in.threshold - in.bias);
  return r;
}

}  // namespace traffic
}  // namespace nycsim
