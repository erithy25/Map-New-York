#pragma once
// nycsim/util/RegionSampler.h — weighted sampling over a population of placed
// items, restricted to a disc.
//
// Why this exists (ADR-021).  Both simulations used to draw origins and
// destinations from a cumulative distribution over the whole city.  On the real
// graph that is 851,725 lanes and 46 x 45 km, so a spawner that samples
// city-wide and then rejects what falls outside the player's 900 m ring accepts
// about one lane in a thousand, and an agent in Brooklyn is routed to Staten
// Island.  Restricting the draw to the streamed region fixes both: the ring can
// be filled, and the router settles a neighbourhood instead of a borough.
//
// Contract:
//   * build() indexes the population into a uniform grid and computes the
//     whole-population cumulative distribution;
//   * refresh() re-restricts a Region to a disc.  It is a no-op while the disc
//     the Region was built for still covers the requested one, so a moving
//     player rebuilds every few seconds rather than every step;
//   * a Region whose disc contains the whole population is flagged `all` and
//     samples the whole-population distribution, so a host with no streaming
//     ring keeps exactly the numbers it had before — same weights, same
//     accumulation order, bit-identical draws;
//   * a restricted Region keeps the population's own order, so its cumulative
//     sums are the same floats the global one would have produced over that
//     subset;
//   * reserveRegions() sizes the region buffers once, so refresh() does not
//     allocate inside a simulation step.
//
// An item carries a `reach` (half its length): an item is a candidate when its
// position is within radius + reach of the centre, so a long lane that crosses
// the ring boundary is not lost.  Exact acceptance stays with the caller, which
// knows what it is really testing (a pose, a protected cone).

#include <algorithm>
#include <cstddef>
#include <cstdint>
#include <vector>

namespace nycsim {

class RegionSampler {
 public:
  static constexpr uint32_t kInvalid = 0xFFFFFFFFu;

  /// One restricted view.  Several may share a sampler (different radii).
  struct Region {
    std::vector<uint32_t> items;  // indices into the population, ascending
    std::vector<float> cdf;       // running sum of the items' weights
    float cx = 0.f, cy = 0.f, radius = -1.f;
    uint32_t stamp = 0xFFFFFFFFu;
    bool all = false;  // the disc covers the whole population
  };

  void clear() {
    ids_.clear();
    x_.clear();
    y_.clear();
    w_.clear();
    reach_.clear();
    cdf_.clear();
    grid_start_.clear();
    grid_items_.clear();
    nx_ = ny_ = 1;
    ++stamp_;
  }

  void reserve(size_t n) {
    ids_.reserve(n);
    x_.reserve(n);
    y_.reserve(n);
    w_.reserve(n);
    reach_.reserve(n);
    cdf_.reserve(n);
  }

  /// `id` is opaque to the sampler and is what sample() returns.
  void add(uint32_t id, float x, float y, float weight, float reach) {
    ids_.push_back(id);
    x_.push_back(x);
    y_.push_back(y);
    w_.push_back(weight);
    reach_.push_back(reach);
  }

  size_t size() const { return ids_.size(); }
  bool empty() const { return ids_.empty(); }

  /// Builds the cumulative distribution and the uniform grid.  `cell_m` is the
  /// grid pitch; the population extent decides the grid dimensions.
  void build(float cell_m = 250.f) {
    cdf_.assign(ids_.size(), 0.f);
    float acc = 0.f;
    for (size_t i = 0; i < ids_.size(); ++i) {
      acc += w_[i];
      cdf_[i] = acc;
    }
    minx_ = miny_ = 1e30f;
    maxx_ = maxy_ = -1e30f;
    for (size_t i = 0; i < ids_.size(); ++i) {
      minx_ = std::min(minx_, x_[i]);
      maxx_ = std::max(maxx_, x_[i]);
      miny_ = std::min(miny_, y_[i]);
      maxy_ = std::max(maxy_, y_[i]);
    }
    if (ids_.empty()) {
      minx_ = miny_ = maxx_ = maxy_ = 0.f;
    }
    max_reach_ = 0.f;
    for (float r : reach_) max_reach_ = std::max(max_reach_, r);
    cell_ = std::max(1.f, cell_m);
    gx0_ = minx_ - 1.f;
    gy0_ = miny_ - 1.f;
    nx_ = static_cast<uint32_t>((maxx_ - minx_ + 2.f) / cell_) + 1u;
    ny_ = static_cast<uint32_t>((maxy_ - miny_ + 2.f) / cell_) + 1u;
    const size_t nc = static_cast<size_t>(nx_) * ny_;
    grid_start_.assign(nc + 1, 0u);
    for (size_t i = 0; i < ids_.size(); ++i) ++grid_start_[cellOf(x_[i], y_[i]) + 1u];
    for (size_t i = 0; i < nc; ++i) grid_start_[i + 1] += grid_start_[i];
    grid_items_.assign(grid_start_[nc], 0u);
    std::vector<uint32_t> cur(grid_start_.begin(), grid_start_.end() - 1);
    for (size_t i = 0; i < ids_.size(); ++i)
      grid_items_[cur[cellOf(x_[i], y_[i])]++] = static_cast<uint32_t>(i);
    ++stamp_;
  }

  /// Sizes a region's buffers to the worst case so refresh() never allocates.
  void reserveRegion(Region& r) const {
    r.items.reserve(ids_.size());
    r.cdf.reserve(ids_.size());
  }

  /// Restricts `r` to the disc of `radius` around (cx, cy).  Rebuilds only when
  /// the cached disc no longer covers the requested one; `slack` is the extra
  /// radius the rebuild takes, so a centre that drifts by up to `slack` stays
  /// covered.  Returns false when the region holds nothing.
  bool refresh(Region& r, float cx, float cy, float radius, float slack) const {
    if (r.stamp == stamp_ && r.radius >= radius) {
      const float dx = cx - r.cx, dy = cy - r.cy;
      if (dx * dx + dy * dy <= (r.radius - radius) * (r.radius - radius))
        return r.all || !r.items.empty();
    }
    r.stamp = stamp_;
    r.cx = cx;
    r.cy = cy;
    r.radius = radius + std::max(0.f, slack);
    r.items.clear();
    r.cdf.clear();
    r.all = coversAll(cx, cy, r.radius);
    if (r.all) return !ids_.empty();
    const float reach = r.radius + max_reach_;
    const int cx0 = clampCol(cx - reach), cx1 = clampCol(cx + reach);
    const int cy0 = clampRow(cy - reach), cy1 = clampRow(cy + reach);
    for (int gy = cy0; gy <= cy1; ++gy) {
      for (int gx = cx0; gx <= cx1; ++gx) {
        const size_t cell = static_cast<size_t>(gy) * nx_ + static_cast<size_t>(gx);
        for (uint32_t k = grid_start_[cell]; k < grid_start_[cell + 1]; ++k) {
          const uint32_t i = grid_items_[k];
          const float dx = x_[i] - cx, dy = y_[i] - cy;
          const float lim = r.radius + reach_[i];
          if (dx * dx + dy * dy > lim * lim) continue;
          r.items.push_back(i);
        }
      }
    }
    // Population order, so the cumulative sums are the same floats the whole
    // population's distribution would have produced over this subset.
    std::sort(r.items.begin(), r.items.end());
    float acc = 0.f;
    for (uint32_t i : r.items) {
      acc += w_[i];
      r.cdf.push_back(acc);
    }
    return !r.items.empty();
  }

  /// Draws one item from `r`; kInvalid when there is nothing to draw.  `u` is a
  /// uniform draw in [0, 1) — the caller owns the random stream, so this header
  /// stays free of any dependency on the simulation's PRNG.
  uint32_t sample(const Region& r, float u) const {
    if (r.all || r.radius < 0.f) return sampleAll(u);
    if (r.cdf.empty()) return kInvalid;
    const float total = r.cdf.back();
    if (total <= 0.f) return kInvalid;
    const float pick = u * total;
    const auto it = std::lower_bound(r.cdf.begin(), r.cdf.end(), pick);
    const size_t ix = std::min(static_cast<size_t>(it - r.cdf.begin()), r.items.size() - 1);
    return ids_[r.items[ix]];
  }

  /// Draws one item from the whole population; kInvalid when it is empty.
  uint32_t sampleAll(float u) const {
    if (cdf_.empty()) return kInvalid;
    const float total = cdf_.back();
    if (total <= 0.f) return kInvalid;
    const float pick = u * total;
    const auto it = std::lower_bound(cdf_.begin(), cdf_.end(), pick);
    const size_t ix = std::min(static_cast<size_t>(it - cdf_.begin()), ids_.size() - 1);
    return ids_[ix];
  }

  /// Items a region holds; size() when it covers the whole population.
  size_t regionSize(const Region& r) const { return r.all ? ids_.size() : r.items.size(); }

  /// Total weight inside a region — what a caller that reads weights as a
  /// quantity (vehicles per lane-km x lane length) needs in order to size a
  /// population to the region instead of to the whole city.
  float regionWeight(const Region& r) const {
    if (r.all || r.radius < 0.f) return cdf_.empty() ? 0.f : cdf_.back();
    return r.cdf.empty() ? 0.f : r.cdf.back();
  }
  /// True while `r` is restricted to less than the whole population.
  bool regionIsRestricted(const Region& r) const { return !(r.all || r.radius < 0.f); }

 private:
  size_t cellOf(float x, float y) const {
    return static_cast<size_t>(clampRow(y)) * nx_ + static_cast<size_t>(clampCol(x));
  }
  int clampCol(float x) const {
    const int c = static_cast<int>((x - gx0_) / cell_);
    return c < 0 ? 0 : (c >= static_cast<int>(nx_) ? static_cast<int>(nx_) - 1 : c);
  }
  int clampRow(float y) const {
    const int c = static_cast<int>((y - gy0_) / cell_);
    return c < 0 ? 0 : (c >= static_cast<int>(ny_) ? static_cast<int>(ny_) - 1 : c);
  }
  // Conservative: every item's *position* is inside the disc, so every item is
  // a candidate whatever its reach.  Erring late costs one grid walk; erring
  // early would silently drop items.
  bool coversAll(float cx, float cy, float radius) const {
    if (ids_.empty()) return true;
    const float ax = std::max(cx - minx_, maxx_ - cx);
    const float ay = std::max(cy - miny_, maxy_ - cy);
    return ax * ax + ay * ay <= radius * radius;
  }

  std::vector<uint32_t> ids_;
  std::vector<float> x_, y_, w_, reach_, cdf_;
  std::vector<uint32_t> grid_start_, grid_items_;
  float gx0_ = 0.f, gy0_ = 0.f, cell_ = 250.f;
  float minx_ = 0.f, miny_ = 0.f, maxx_ = 0.f, maxy_ = 0.f;
  float max_reach_ = 0.f;
  uint32_t nx_ = 1, ny_ = 1;
  uint32_t stamp_ = 0;
};

}  // namespace nycsim
