#pragma once
// nycsim/traffic/PlayerProxy.h — everything the AI needs to know about the
// player, pushed by the host once per simulation step.  The traffic and
// pedestrian modules never see an Unreal type; the adapter fills this struct
// from the pawn transform (NYC_TM metres, +x east, +y north — see
// docs/ARCHITECTURE.md §2).
//
// Two independent jobs:
//   1. behaviour — drivers treat the player car as a first-class obstacle
//      (IDM leader, TTC braking, in-lane swerve) and stop for the player on
//      foot;
//   2. streaming — the spawn/despawn ring: no agent may be created or removed
//      inside `no_spawn_radius_m` of the player *within the view cone*, nor
//      inside `near_radius_m` in any direction (the player can turn round).

#include <cmath>

namespace nycsim {
namespace traffic {

struct PlayerProxy {
  bool valid = false;
  float x = 0.f, y = 0.f, z = 0.f;
  float heading_rad = 0.f;  // mathematical convention: 0 = +x (east), CCW
  float speed_mps = 0.f;    // signed along heading
  float half_length_m = 2.44f;  // 2019 Ford Fusion Hybrid: 4.87 m long,
  float half_width_m = 0.94f;   // 1.88 m wide (ADR-009)
  bool on_foot = false;         // player is a pedestrian standing in the road

  // View cone / streaming ring.
  float view_half_angle_deg = 55.f;  // 110° horizontal FOV covers 16:9 at 90° VFOV
  float no_spawn_radius_m = 250.f;   // ARCHITECTURE §9
  float near_radius_m = 60.f;        // behind the player too (mirrors, quick turns)

  float dirX() const { return std::cos(heading_rad); }
  float dirY() const { return std::sin(heading_rad); }

  // True when (px,py) is inside the protected region: within near_radius_m in
  // any direction, or within no_spawn_radius_m and inside the view cone.
  bool inProtectedRegion(float px, float py) const {
    if (!valid) return false;
    const float dx = px - x, dy = py - y;
    const float d2 = dx * dx + dy * dy;
    if (d2 <= near_radius_m * near_radius_m) return true;
    if (d2 > no_spawn_radius_m * no_spawn_radius_m) return false;
    const float d = std::sqrt(d2);
    if (d < 1e-3f) return true;
    const float cos_a = (dx * dirX() + dy * dirY()) / d;
    const float cos_lim = std::cos(view_half_angle_deg * 0.01745329252f);
    return cos_a >= cos_lim;
  }
};

}  // namespace traffic
}  // namespace nycsim
