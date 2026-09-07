#pragma once
// nycsim/traffic/SpatialHash.h — uniform-grid spatial hash rebuilt every step
// with a counting sort.  Zero heap allocation after `configure()` as long as
// the item count stays within `max_items` (growth happens only when the host
// raises the capacity, never inside `step()`).
//
// The grid is *sparse*: only the cells that actually hold an item exist, in an
// open-addressed table keyed by the cell index and validated by a build stamp.
// Every operation therefore costs O(items) or O(cells visited), never O(grid).
// That matters because the grid is sized by the world, not by the crowd: a
// 15 m grid over the whole of New York is 28 million cells, and the previous
// dense layout cleared and prefix-summed all of them on every rebuild — a cost
// the city-scale step cannot pay (docs/verification/performance/REPORT.md).
//
// Enumeration order is unchanged: `query` walks cells in (cy, cx) order and the
// items inside a cell in insertion order, so a caller whose result depends on
// visit order (TrafficSim::separateBodies) sees exactly the same sequence as
// before.

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <vector>

namespace nycsim {

class SpatialHash {
 public:
  // World bounds and cell size.  Points outside the bounds are clamped into
  // the border cells (they still participate in queries, just less precisely).
  void configure(float minx, float miny, float maxx, float maxy, float cell_size, uint32_t max_items) {
    minx_ = minx;
    miny_ = miny;
    cell_ = cell_size > 0.01f ? cell_size : 0.01f;
    inv_cell_ = 1.0f / cell_;
    nx_ = std::max(1u, static_cast<uint32_t>(std::ceil((maxx - minx) * inv_cell_)) + 1u);
    ny_ = std::max(1u, static_cast<uint32_t>(std::ceil((maxy - miny) * inv_cell_)) + 1u);
    capacity_ = max_items;
    items_.assign(max_items, 0u);
    pending_.assign(max_items, Pending{0u, 0u});
    buckets_arr_.assign(static_cast<size_t>(max_items) + 1u, Bucket{0u, 0u, 0u});
    // Open addressing with a load factor of at most 0.5, so the linear probe
    // always terminates and stays short.
    uint32_t slots = 16u;
    while (slots < (max_items + 1u) * 2u) slots <<= 1;
    mask_ = slots - 1u;
    slots_.assign(slots, Slot{0u, 0u, 0u});
    // The build stamp must never equal the value the slots are initialised to,
    // or a query issued before the first begin() would read every slot as live
    // and probe for ever.  Start at 1 so a freshly configured hash is empty.
    stamp_ = 1;
    count_ = 0;
    buckets_ = 0;
  }

  uint32_t capacity() const { return capacity_; }
  uint32_t cellsX() const { return nx_; }
  uint32_t cellsY() const { return ny_; }
  float cellSize() const { return cell_; }
  /// Number of non-empty cells in the current build (diagnostics).
  uint32_t occupiedCells() const { return buckets_; }

  uint32_t cellOf(float x, float y) const {
    int cx = static_cast<int>((x - minx_) * inv_cell_);
    int cy = static_cast<int>((y - miny_) * inv_cell_);
    cx = std::clamp(cx, 0, static_cast<int>(nx_) - 1);
    cy = std::clamp(cy, 0, static_cast<int>(ny_) - 1);
    return static_cast<uint32_t>(cy) * nx_ + static_cast<uint32_t>(cx);
  }

  // Build protocol: begin(); insert(id,x,y)...; end();
  void begin() {
    ++stamp_;
    if (stamp_ == 0u) {  // wrap: every stored stamp becomes stale again
      for (Slot& sl : slots_) sl.stamp = 0u;
      stamp_ = 1u;
    }
    count_ = 0;
    buckets_ = 0;
  }

  // Returns false (and drops the item) when capacity is exhausted.
  bool insert(uint32_t id, float x, float y) {
    if (count_ >= capacity_) return false;
    const uint32_t b = bucketFor(cellOf(x, y));
    pending_[count_] = Pending{id, b};
    ++buckets_arr_[b].count;
    ++count_;
    return true;
  }

  void end() {
    uint32_t acc = 0;
    for (uint32_t b = 0; b < buckets_; ++b) {
      Bucket& k = buckets_arr_[b];
      k.first = acc;
      k.cursor = acc;
      acc += k.count;
    }
    for (uint32_t i = 0; i < count_; ++i) {
      const Pending& p = pending_[i];
      items_[buckets_arr_[p.bucket].cursor++] = p.id;
    }
  }

  uint32_t count() const { return count_; }

  // Visit every item whose cell intersects the square of half-size `radius`
  // around (x,y).  `fn(uint32_t id)` — the caller does the exact distance test.
  template <class Fn>
  void query(float x, float y, float radius, Fn&& fn) const {
    int cx0 = static_cast<int>((x - radius - minx_) * inv_cell_);
    int cy0 = static_cast<int>((y - radius - miny_) * inv_cell_);
    int cx1 = static_cast<int>((x + radius - minx_) * inv_cell_);
    int cy1 = static_cast<int>((y + radius - miny_) * inv_cell_);
    cx0 = std::clamp(cx0, 0, static_cast<int>(nx_) - 1);
    cx1 = std::clamp(cx1, 0, static_cast<int>(nx_) - 1);
    cy0 = std::clamp(cy0, 0, static_cast<int>(ny_) - 1);
    cy1 = std::clamp(cy1, 0, static_cast<int>(ny_) - 1);
    for (int cy = cy0; cy <= cy1; ++cy) {
      const uint32_t row = static_cast<uint32_t>(cy) * nx_;
      for (int cx = cx0; cx <= cx1; ++cx) {
        const uint32_t b = findBucket(row + static_cast<uint32_t>(cx));
        if (b == kNoBucket) continue;
        const Bucket& k = buckets_arr_[b];
        const uint32_t e = k.first + k.count;
        for (uint32_t j = k.first; j < e; ++j) fn(items_[j]);
      }
    }
  }

  // Items in one cell (for exhaustive checks / tests).
  const uint32_t* cellItems(uint32_t cell, uint32_t& n) const {
    const uint32_t b = findBucket(cell);
    if (b == kNoBucket) {
      n = 0;
      return items_.data();
    }
    n = buckets_arr_[b].count;
    return items_.data() + buckets_arr_[b].first;
  }

 private:
  static constexpr uint32_t kNoBucket = 0xFFFFFFFFu;

  // Fibonacci hashing of the cell index; the grid is row-major, so neighbouring
  // cells must not land in neighbouring slots or the probe chains collide.
  static uint32_t mix(uint32_t c) {
    uint32_t h = c * 2654435761u;
    return h ^ (h >> 15);
  }

  // The table holds at most `capacity_` live entries in at least
  // 2 * (capacity_ + 1) slots, so a free slot always exists; the probe bound is
  // belt and braces against a future capacity change breaking that invariant.
  uint32_t findBucket(uint32_t cell) const {
    if (slots_.empty()) return kNoBucket;  // never configured
    uint32_t s = mix(cell) & mask_;
    for (uint32_t probe = 0; probe <= mask_; ++probe) {
      const Slot& sl = slots_[s];
      if (sl.stamp != stamp_) return kNoBucket;
      if (sl.cell == cell) return sl.bucket;
      s = (s + 1u) & mask_;
    }
    return kNoBucket;
  }

  uint32_t bucketFor(uint32_t cell) {
    uint32_t s = mix(cell) & mask_;
    for (uint32_t probe = 0; probe <= mask_ && slots_[s].stamp == stamp_; ++probe) {
      if (slots_[s].cell == cell) return slots_[s].bucket;
      s = (s + 1u) & mask_;
    }
    slots_[s] = Slot{stamp_, cell, buckets_};
    buckets_arr_[buckets_].count = 0;
    return buckets_++;
  }

  float minx_ = 0, miny_ = 0, cell_ = 1, inv_cell_ = 1;
  uint32_t nx_ = 1, ny_ = 1, count_ = 0, capacity_ = 0;
  uint32_t buckets_ = 0, stamp_ = 0, mask_ = 0;
  // Fields that are read together live together: one cache line per probe
  // rather than three.
  struct Slot {
    uint32_t stamp, cell, bucket;
  };
  struct Bucket {
    uint32_t first, count, cursor;
  };
  struct Pending {
    uint32_t id, bucket;
  };
  std::vector<uint32_t> items_;      ///< ids, grouped by bucket
  std::vector<Pending> pending_;     ///< ids in insertion order, with their bucket
  std::vector<Bucket> buckets_arr_;
  std::vector<Slot> slots_;          ///< open-addressed cell -> bucket table
};

}  // namespace nycsim
