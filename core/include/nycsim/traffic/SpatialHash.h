#pragma once
// nycsim/traffic/SpatialHash.h — uniform-grid spatial hash rebuilt every step
// with a counting sort.  Zero heap allocation after `configure()` as long as
// the item count stays within `max_items` (growth happens only when the host
// raises the capacity, never inside `step()`).

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
    cell_start_.assign(static_cast<size_t>(nx_) * ny_ + 1, 0u);
    items_.assign(max_items, 0u);
    item_cell_.assign(max_items, 0u);
    item_ids_.assign(max_items, 0u);
    count_ = 0;
    capacity_ = max_items;
  }

  uint32_t capacity() const { return capacity_; }
  uint32_t cellsX() const { return nx_; }
  uint32_t cellsY() const { return ny_; }
  float cellSize() const { return cell_; }

  uint32_t cellOf(float x, float y) const {
    int cx = static_cast<int>((x - minx_) * inv_cell_);
    int cy = static_cast<int>((y - miny_) * inv_cell_);
    cx = std::clamp(cx, 0, static_cast<int>(nx_) - 1);
    cy = std::clamp(cy, 0, static_cast<int>(ny_) - 1);
    return static_cast<uint32_t>(cy) * nx_ + static_cast<uint32_t>(cx);
  }

  // Build protocol: begin(); insert(id,x,y)...; end();
  void begin() {
    std::fill(cell_start_.begin(), cell_start_.end(), 0u);
    count_ = 0;
  }
  // Returns false (and drops the item) when capacity is exhausted.
  bool insert(uint32_t id, float x, float y) {
    if (count_ >= capacity_) return false;
    const uint32_t c = cellOf(x, y);
    item_cell_[count_] = c;
    item_ids_[count_] = id;
    ++cell_start_[c + 1];
    ++count_;
    return true;
  }
  void end() {
    const size_t nc = static_cast<size_t>(nx_) * ny_;
    for (size_t c = 0; c < nc; ++c) cell_start_[c + 1] += cell_start_[c];
    // scatter (uses cell_start_ as a running cursor, then restores it)
    for (uint32_t i = 0; i < count_; ++i) {
      const uint32_t c = item_cell_[i];
      items_[cell_start_[c]++] = item_ids_[i];
    }
    for (size_t c = nc; c > 0; --c) cell_start_[c] = cell_start_[c - 1];
    cell_start_[0] = 0;
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
        const uint32_t c = row + static_cast<uint32_t>(cx);
        const uint32_t b = cell_start_[c], e = cell_start_[c + 1];
        for (uint32_t k = b; k < e; ++k) fn(items_[k]);
      }
    }
  }

  // Items in one cell (for exhaustive checks / tests).
  const uint32_t* cellItems(uint32_t cell, uint32_t& n) const {
    n = cell_start_[cell + 1] - cell_start_[cell];
    return items_.data() + cell_start_[cell];
  }

 private:
  float minx_ = 0, miny_ = 0, cell_ = 1, inv_cell_ = 1;
  uint32_t nx_ = 1, ny_ = 1, count_ = 0, capacity_ = 0;
  std::vector<uint32_t> cell_start_;
  std::vector<uint32_t> items_;
  std::vector<uint32_t> item_cell_;
  std::vector<uint32_t> item_ids_;
};

}  // namespace nycsim
