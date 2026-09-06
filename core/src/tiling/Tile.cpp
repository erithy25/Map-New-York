#include "nycsim/tiling/Tile.h"

#include <cmath>
#include <cstdio>
#include <limits>

#include "nycsim/geo/NycTm.h"

namespace nycsim {
namespace tiling {

namespace {

int32_t floorToIndex(double v) {
  const double f = std::floor(v / kTileSizeM);
  if (!(f == f)) return 0;  // NaN
  if (f >= static_cast<double>(std::numeric_limits<int32_t>::max())) return std::numeric_limits<int32_t>::max();
  if (f <= static_cast<double>(std::numeric_limits<int32_t>::min())) return std::numeric_limits<int32_t>::min();
  return static_cast<int32_t>(f);
}

// Parses an optionally negative decimal int32 from [p, end); returns false on any deviation.
bool parseInt(std::string_view s, int32_t& out) {
  if (s.empty()) return false;
  size_t i = 0;
  bool neg = false;
  if (s[0] == '-') {
    neg = true;
    i = 1;
    if (s.size() == 1) return false;
  }
  int64_t v = 0;
  for (; i < s.size(); ++i) {
    const char c = s[i];
    if (c < '0' || c > '9') return false;
    v = v * 10 + (c - '0');
    if (v > static_cast<int64_t>(std::numeric_limits<int32_t>::max()) + 1) return false;
  }
  if (neg) v = -v;
  if (v < std::numeric_limits<int32_t>::min() || v > std::numeric_limits<int32_t>::max()) return false;
  out = static_cast<int32_t>(v);
  return true;
}

}  // namespace

int Tile::name(char* buf, size_t cap) const {
  if (!buf || cap == 0) return -1;
  const int n = std::snprintf(buf, cap, "t_%d_%d", tx, ty);
  if (n < 0 || static_cast<size_t>(n) >= cap) {
    buf[0] = '\0';
    return -1;
  }
  return n;
}

std::string Tile::name() const {
  char buf[32];
  const int n = name(buf, sizeof buf);
  return n > 0 ? std::string(buf, static_cast<size_t>(n)) : std::string();
}

Result<Tile> Tile::parse(std::string_view s) {
  if (s.size() < 5 || s[0] != 't' || s[1] != '_') {
    return fail(ErrorCode::ParseError, "Tile::parse: expected t_{tx}_{ty}");
  }
  // Split at the last '_' (the first two chars are "t_").
  const size_t sep = s.rfind('_');
  if (sep == std::string_view::npos || sep < 3 || sep + 1 >= s.size()) {
    return fail(ErrorCode::ParseError, "Tile::parse: expected t_{tx}_{ty}");
  }
  Tile t;
  if (!parseInt(s.substr(2, sep - 2), t.tx) || !parseInt(s.substr(sep + 1), t.ty)) {
    return fail(ErrorCode::ParseError, "Tile::parse: tile indices must be int32 decimals");
  }
  return t;
}

Tile tileOf(double x_m, double y_m) { return Tile{floorToIndex(x_m), floorToIndex(y_m)}; }

size_t tilesInBbox(double xmin, double ymin, double xmax, double ymax, std::vector<Tile>& out) {
  if (!(xmin == xmin) || !(ymin == ymin) || !(xmax == xmax) || !(ymax == ymax)) return 0;
  const int32_t tx0 = floorToIndex(xmin);
  const int32_t ty0 = floorToIndex(ymin);
  const int32_t tx1 = floorToIndex(std::fmax(xmax - 1e-9, xmin));
  const int32_t ty1 = floorToIndex(std::fmax(ymax - 1e-9, ymin));
  if (tx1 < tx0 || ty1 < ty0) return 0;
  const size_t before = out.size();
  const size_t count = static_cast<size_t>(static_cast<int64_t>(tx1) - tx0 + 1) *
                       static_cast<size_t>(static_cast<int64_t>(ty1) - ty0 + 1);
  out.reserve(before + count);
  for (int64_t ty = ty0; ty <= ty1; ++ty) {
    for (int64_t tx = tx0; tx <= tx1; ++tx) {
      out.push_back(Tile{static_cast<int32_t>(tx), static_cast<int32_t>(ty)});
    }
  }
  return out.size() - before;
}

std::vector<Tile> scopeTiles() {
  std::vector<Tile> v;
  tilesInBbox(geo::kScopeXMin, geo::kScopeYMin, geo::kScopeXMax, geo::kScopeYMax, v);
  return v;
}

ParentIndex parentTile(Tile tile, int level) {
  if (level < 0) level = 0;
  if (level > 15) level = 15;
  const double f = std::pow(4.0, level);
  return ParentIndex{static_cast<int32_t>(std::floor(static_cast<double>(tile.tx) / f)),
                     static_cast<int32_t>(std::floor(static_cast<double>(tile.ty) / f))};
}

double distanceToTile(Tile tile, double x_m, double y_m) {
  const TileBounds b = tile.bounds();
  const double dx = x_m < b.xmin ? b.xmin - x_m : (x_m > b.xmax ? x_m - b.xmax : 0.0);
  const double dy = y_m < b.ymin ? b.ymin - y_m : (y_m > b.ymax ? y_m - b.ymax : 0.0);
  return std::hypot(dx, dy);
}

}  // namespace tiling
}  // namespace nycsim
