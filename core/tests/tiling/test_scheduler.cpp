#include <doctest/doctest.h>

#include <algorithm>
#include <cmath>
#include <map>
#include <random>
#include <set>
#include <vector>

#include "nycsim/tiling/Tile.h"
#include "nycsim/tiling/TileScheduler.h"

using namespace nycsim;
using namespace nycsim::tiling;

namespace {

// Synthetic catalogue over the whole scope (2916 tiles) with deterministic content counts.
// (Scheduler unit test fixture — not real building counts.)
std::vector<TileInfo> syntheticCatalog() {
  std::vector<TileInfo> out;
  for (const Tile& t : scopeTiles()) {
    TileInfo info;
    info.tx = t.tx;
    info.ty = t.ty;
    const uint32_t h = static_cast<uint32_t>((t.tx * 7919 + t.ty * 104729) & 0x7fffffff);
    info.nBuildings = 150 + h % 600;
    info.nProps = 80 + (h / 7) % 300;
    info.flags = TileInfo::kHasTerrain | TileInfo::kHasLand;
    info.zMin = 0.0f;
    info.zMax = 40.0f;
    out.push_back(info);
  }
  return out;
}

struct LogEntry {
  int32_t tx, ty;
  Tier from, to;
  double t;
  bool operator==(const LogEntry& o) const {
    return tx == o.tx && ty == o.ty && from == o.from && to == o.to && t == o.t;
  }
};

struct DriveResult {
  std::vector<LogEntry> log;
  uint64_t l0Loads = 0;      // transitions into L0 from a coarser tier (after warm-up)
  uint64_t protectedViolations = 0;
  uint64_t oracleViolations = 0;
  uint64_t budgetViolations = 0;
  uint64_t protectedNotL0 = 0;
  uint64_t nearestFirstViolations = 0;
  uint64_t frames = 0;
  uint64_t maxResident = 0;
  std::set<std::pair<int32_t, int32_t>> everWithinL0Load;
};

// Runs a camera path (list of segments: heading deg, speed m/s, duration s), dt seconds per frame.
struct Segment {
  double heading_deg;
  double speed_mps;
  double duration_s;
};

DriveResult drive(TileScheduler& sched, double x0, double y0, const std::vector<Segment>& path,
                  double dt, bool checkOracle) {
  DriveResult r;
  const SchedulerConfig& cfg = sched.config();
  CameraState cam;
  cam.x_m = x0;
  cam.y_m = y0;
  cam.time_s = 0.0;
  bool warm = false;
  for (const Segment& seg : path) {
    const double hx = std::sin(seg.heading_deg * 3.14159265358979323846 / 180.0);
    const double hy = std::cos(seg.heading_deg * 3.14159265358979323846 / 180.0);
    const int frames = static_cast<int>(std::llround(seg.duration_s / dt));
    for (int f = 0; f < frames; ++f) {
      cam.vx_mps = hx * seg.speed_mps;
      cam.vy_mps = hy * seg.speed_mps;
      cam.heading_deg = seg.heading_deg;
      // Reference: tiles within 300 m of the camera now (independent of the scheduler).
      std::set<std::pair<int32_t, int32_t>> protectedNow;
      std::vector<Tile> near;
      tilesInBbox(cam.x_m - 301, cam.y_m - 301, cam.x_m + 301, cam.y_m + 301, near);
      for (const Tile& t : near) {
        if (distanceToTile(t, cam.x_m, cam.y_m) <= cfg.protectRadius_m) protectedNow.insert({t.tx, t.ty});
      }
      const auto& trans = sched.update(cam);
      if (warm) {
        for (const Transition& tr : trans) {
          r.log.push_back(LogEntry{tr.tx, tr.ty, tr.from, tr.to, tr.time_s});
          if (tr.to == Tier::L0 && tr.from != Tier::L0) ++r.l0Loads;
          if (protectedNow.count({tr.tx, tr.ty})) ++r.protectedViolations;
        }
      }
      const SchedulerStats& st = sched.stats();
      r.maxResident = std::max(r.maxResident, st.residentBytes);
      if (st.residentBytes > cfg.budgetBytes && !st.overBudget) ++r.budgetViolations;
      // Per-frame oracle over all entries.
      const double px = cam.x_m + cam.vx_mps * cfg.lookahead_s;
      const double py = cam.y_m + cam.vy_mps * cfg.lookahead_s;
      double worstGrantedPriority = -1.0;
      double bestDeniedPriority = 1e300;
      for (const auto& e : sched.entries()) {
        const Tile t = e.info.tile();
        const double d = std::fmin(distanceToTile(t, cam.x_m, cam.y_m), distanceToTile(t, px, py));
        if (d < cfg.l0.load_m) r.everWithinL0Load.insert({t.tx, t.ty});
        if (protectedNow.count({t.tx, t.ty}) && e.tier != Tier::L0) ++r.protectedNotL0;
        if (checkOracle) {
          // Unlimited budget: within a load radius => at least that tier; loaded => within unload.
          if (d < cfg.l0.load_m && e.tier < Tier::L0) ++r.oracleViolations;
          if (d < cfg.l1.load_m && e.tier < Tier::L1) ++r.oracleViolations;
          if (d < cfg.l2.load_m && e.tier < Tier::L2) ++r.oracleViolations;
          if (d < cfg.l3.load_m && e.tier < Tier::L3) ++r.oracleViolations;
          if (e.tier != Tier::Unloaded && d > cfg.radii(e.tier).unload_m) ++r.oracleViolations;
        } else {
          if (e.radiiTier == Tier::L0 && !e.protectedNow) {
            if (e.tier == Tier::L0) {
              worstGrantedPriority = std::fmax(worstGrantedPriority, e.priority);
            } else {
              bestDeniedPriority = std::fmin(bestDeniedPriority, e.priority);
            }
          }
        }
      }
      if (!checkOracle && worstGrantedPriority > bestDeniedPriority) ++r.nearestFirstViolations;
      warm = true;
      ++r.frames;
      cam.x_m += cam.vx_mps * dt;
      cam.y_m += cam.vy_mps * dt;
      cam.time_s += dt;
    }
  }
  return r;
}

}  // namespace

TEST_SUITE("tiling") {
  TEST_CASE("config validation and cost model monotonicity") {
    SchedulerConfig cfg;
    CHECK(cfg.valid());
    cfg.l0.unload_m = 800.0;  // unload < load
    CHECK_FALSE(cfg.valid());
    cfg = SchedulerConfig();
    cfg.protectRadius_m = 1000.0;  // protect beyond L0 load radius
    CHECK_FALSE(cfg.valid());
    TileCostModel cost;
    TileInfo info;
    info.nBuildings = 400;
    info.nProps = 200;
    info.flags = TileInfo::kHasTerrain;
    CHECK(cost.bytes(info, Tier::Unloaded) == 0);
    CHECK(cost.bytes(info, Tier::L3) > 0);
    CHECK(cost.bytes(info, Tier::L2) > cost.bytes(info, Tier::L3));
    CHECK(cost.bytes(info, Tier::L1) > cost.bytes(info, Tier::L2));
    CHECK(cost.bytes(info, Tier::L0) > cost.bytes(info, Tier::L1));
    // 400 shells x 1.2 KB + kit + props + terrain ~ a few MB at L0.
    CHECK(cost.bytes(info, Tier::L0) > 2u * 1024u * 1024u);
    CHECK(cost.bytes(info, Tier::L0) < 8u * 1024u * 1024u);
    CHECK(tierName(Tier::L0) == std::string("L0"));
  }

  TEST_CASE("teleport: first update loads exactly the radii sets") {
    auto cat = syntheticCatalog();
    TileScheduler sched(Span<const TileInfo>(cat.data(), cat.size()));
    CHECK(sched.tileCount() == 2916);
    CHECK(sched.contains(-3, 7));
    CHECK_FALSE(sched.contains(100, 100));
    CameraState cam;
    cam.x_m = -2500.0;  // Midtown-ish tile t_-3_5
    cam.y_m = 5500.0;
    cam.heading_deg = 0.0;
    const auto& tr = sched.update(cam);
    CHECK(tr.size() > 0);
    CHECK(sched.tierOf(-3, 5) == Tier::L0);
    // Oracle by radii.
    for (const auto& e : sched.entries()) {
      const double d = distanceToTile(e.info.tile(), cam.x_m, cam.y_m);
      Tier expect = Tier::Unloaded;
      if (d < 900) expect = Tier::L0;
      else if (d < 2500) expect = Tier::L1;
      else if (d < 12000) expect = Tier::L2;
      else if (d < 40000) expect = Tier::L3;
      CHECK(e.tier == expect);
    }
    const SchedulerStats& st = sched.stats();
    CHECK(st.countByTier[tierIndex(Tier::L0)] >= 4);
    CHECK(st.countByTier[tierIndex(Tier::L0)] <= 12);
    CHECK(st.totalLoads == tr.size());
    CHECK(st.updates == 1);
    // Transitions are emitted in the scheduler's priority order: non-decreasing cone-weighted
    // effective distance, ties broken by (ty, tx). (Raw distance can decrease across a
    // cone boundary, which is why the cone-weighted priority is the invariant.)
    std::map<std::pair<int32_t, int32_t>, double> priority;
    std::map<std::pair<int32_t, int32_t>, Tile> tileOfKey;
    for (const auto& e : sched.entries()) {
      priority[{e.info.tx, e.info.ty}] = e.priority;
      tileOfKey.insert({{e.info.tx, e.info.ty}, e.info.tile()});
    }
    bool orderOk = true;
    for (size_t i = 1; i < tr.size(); ++i) {
      const double pa = priority.at({tr[i - 1].tx, tr[i - 1].ty});
      const double pb = priority.at({tr[i].tx, tr[i].ty});
      if (pa > pb) orderOk = false;
      if (pa == pb && !(tileOfKey.at({tr[i - 1].tx, tr[i - 1].ty}) < tileOfKey.at({tr[i].tx, tr[i].ty})))
        orderOk = false;
    }
    CHECK(orderOk);
    // The very first transition is the tile the camera stands in (priority 0).
    CHECK(tr.front().tx == tileOf(cam.x_m, cam.y_m).tx);
    CHECK(tr.front().ty == tileOf(cam.x_m, cam.y_m).ty);
    // Second identical update: nothing changes.
    CHECK(sched.update(cam).empty());
    sched.reset();
    CHECK(sched.tierOf(-3, 5) == Tier::Unloaded);
  }

  TEST_CASE("straight drive at 30 m/s: no tile within 300 m transitions; single load per tile") {
    auto cat = syntheticCatalog();
    TileScheduler sched(Span<const TileInfo>(cat.data(), cat.size()));
    // 120 s eastbound at 30 m/s (3.6 km) through mid-tile y.
    const auto r = drive(sched, -20000.0, -9500.0, {{90.0, 30.0, 120.0}}, 0.1, true);
    CHECK(r.frames == 1200);
    CHECK(r.protectedViolations == 0);
    CHECK(r.protectedNotL0 == 0);
    CHECK(r.oracleViolations == 0);
    CHECK(r.budgetViolations == 0);
    // Load count: every tile that ever came within the L0 load radius (current or predicted
    // position) minus the tiles already L0 after warm-up; along a straight line each loads once.
    TileScheduler fresh(Span<const TileInfo>(cat.data(), cat.size()));
    CameraState start;
    start.x_m = -20000.0;
    start.y_m = -9500.0;
    start.vx_mps = 30.0;
    start.heading_deg = 90.0;
    fresh.update(start);
    const uint64_t initialL0 = fresh.stats().countByTier[tierIndex(Tier::L0)];
    CHECK(r.l0Loads == r.everWithinL0Load.size() - initialL0);
    // A 3.6 km eastbound run at mid-tile y touches (x range 3.6 km + 2 x 0.9 km + 45 m lookahead)
    // ~ 6 columns and rows y-1..y+1: 15..21 tiles ever at L0, so 7..17 loads after warm-up.
    CHECK(r.l0Loads >= 7);
    CHECK(r.l0Loads <= 17);
    std::set<std::pair<int32_t, int32_t>> loaded;
    for (const LogEntry& e : r.log) {
      if (e.to == Tier::L0) CHECK(loaded.insert({e.tx, e.ty}).second);  // never re-loaded
    }
    // Every L0 unload happened beyond the unload radius, i.e. far behind the camera.
    for (const LogEntry& e : r.log) {
      if (e.from == Tier::L0) CHECK(e.to == Tier::L1);
    }
    CHECK(sched.stats().totalBudgetDenials == 0);
  }

  TEST_CASE("straight drive along a tile edge (degenerate distances)") {
    auto cat = syntheticCatalog();
    TileScheduler sched(Span<const TileInfo>(cat.data(), cat.size()));
    const auto r = drive(sched, 1000.0, 10000.0, {{0.0, 25.0, 80.0}}, 0.05, true);  // north on x=1000
    CHECK(r.protectedViolations == 0);
    CHECK(r.protectedNotL0 == 0);
    CHECK(r.oracleViolations == 0);
  }

  TEST_CASE("Manhattan grid path: invariants, hysteresis and determinism") {
    auto cat = syntheticCatalog();
    // North on an avenue, east on a cross street, north, west, south, with stops at lights.
    const std::vector<Segment> path = {
        {0.0, 12.0, 60.0},   {0.0, 0.0, 5.0},   {90.0, 10.0, 40.0}, {0.0, 13.0, 90.0},
        {270.0, 11.0, 120.0}, {180.0, 14.0, 150.0}, {90.0, 12.0, 60.0}, {0.0, 15.0, 30.0},
    };
    TileScheduler a(Span<const TileInfo>(cat.data(), cat.size()));
    const auto ra = drive(a, -3200.0, 3300.0, path, 0.1, true);
    CHECK(ra.protectedViolations == 0);
    CHECK(ra.protectedNotL0 == 0);
    CHECK(ra.oracleViolations == 0);
    CHECK(ra.log.size() > 0);
    // Hysteresis: a tile never flips L0 -> L1 -> L0 within a short interval.
    std::vector<std::pair<std::pair<int32_t, int32_t>, double>> lastDrop;
    for (const LogEntry& e : ra.log) {
      if (e.from == Tier::L0 && e.to == Tier::L1) lastDrop.push_back({{e.tx, e.ty}, e.t});
      if (e.to == Tier::L0) {
        for (const auto& d : lastDrop) {
          if (d.first == std::make_pair(e.tx, e.ty)) CHECK(e.t - d.second > 10.0);
        }
      }
    }
    // Determinism 1: identical replay.
    TileScheduler b(Span<const TileInfo>(cat.data(), cat.size()));
    const auto rb = drive(b, -3200.0, 3300.0, path, 0.1, true);
    REQUIRE(rb.log.size() == ra.log.size());
    CHECK(std::equal(ra.log.begin(), ra.log.end(), rb.log.begin()));
    // Determinism 2: shuffled catalogue order gives the identical transition sequence.
    auto shuffled = cat;
    std::mt19937 rng(12345);
    std::shuffle(shuffled.begin(), shuffled.end(), rng);
    TileScheduler c(Span<const TileInfo>(shuffled.data(), shuffled.size()));
    const auto rc = drive(c, -3200.0, 3300.0, path, 0.1, true);
    REQUIRE(rc.log.size() == ra.log.size());
    CHECK(std::equal(ra.log.begin(), ra.log.end(), rc.log.begin()));
    // Duplicated records are dropped.
    shuffled.push_back(shuffled.front());
    TileScheduler d(Span<const TileInfo>(shuffled.data(), shuffled.size()));
    CHECK(d.tileCount() == cat.size());
  }

  TEST_CASE("memory budget: respected every frame, protected tiles exempt, nearest-first") {
    auto cat = syntheticCatalog();
    TileCostModel cost;
    // Budget = 55 % of the L0 cost of the 9 tiles around the start -> the budget binds.
    CameraState start;
    start.x_m = -20000.0;
    start.y_m = -9500.0;
    uint64_t nineTiles = 0;
    for (const TileInfo& t : cat) {
      if (distanceToTile(t.tile(), start.x_m, start.y_m) < 900.0) nineTiles += cost.bytes(t, Tier::L0);
    }
    SchedulerConfig cfg;
    cfg.budgetBytes = static_cast<uint64_t>(static_cast<double>(nineTiles) * 0.55);
    REQUIRE(cfg.valid());
    TileScheduler sched(Span<const TileInfo>(cat.data(), cat.size()), cfg, cost);
    const auto r = drive(sched, start.x_m, start.y_m, {{90.0, 30.0, 90.0}}, 0.1, false);
    CHECK(r.budgetViolations == 0);
    CHECK(r.maxResident <= cfg.budgetBytes);
    CHECK(r.protectedNotL0 == 0);
    CHECK(r.protectedViolations == 0);
    CHECK(r.nearestFirstViolations == 0);
    CHECK(sched.stats().totalBudgetDenials > 0);
    CHECK_FALSE(sched.stats().overBudget);
    // Budget-limited transitions are flagged.
    bool sawFlag = false;
    CameraState cam = start;
    TileScheduler s2(Span<const TileInfo>(cat.data(), cat.size()), cfg, cost);
    for (const Transition& t : s2.update(cam)) sawFlag = sawFlag || t.budgetLimited;
    CHECK(sawFlag);
    // Absurdly small budget: protected tiles still load and overBudget is reported.
    cfg.budgetBytes = 1;
    TileScheduler s3(Span<const TileInfo>(cat.data(), cat.size()), cfg, cost);
    s3.update(cam);
    CHECK(s3.stats().overBudget);
    CHECK(s3.tierOf(tileOf(cam.x_m, cam.y_m).tx, tileOf(cam.x_m, cam.y_m).ty) == Tier::L0);
    CHECK(s3.stats().countByTier[tierIndex(Tier::L0)] <= 4);
  }
}
