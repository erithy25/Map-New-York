// 1 km tile grid over NYC_TM — mirrors pipeline/nycsim_pipeline/tiling.py exactly
// (ARCHITECTURE §3, DATA_CONTRACTS §2). Tile (tx, ty) = (floor(x/1000), floor(y/1000)),
// name "t_{tx}_{ty}" (signed), south-west corner (tx*1000, ty*1000).
#pragma once

#include <cstddef>
#include <cstdint>
#include <string>
#include <string_view>
#include <vector>

#include "nycsim/Config.h"
#include "nycsim/util/Result.h"

namespace nycsim {
namespace tiling {

inline constexpr double kTileSizeM = 1000.0;

struct TileBounds {
  double xmin, ymin, xmax, ymax;
};

struct Tile {
  int32_t tx = 0;
  int32_t ty = 0;

  constexpr double x0() const { return static_cast<double>(tx) * kTileSizeM; }
  constexpr double y0() const { return static_cast<double>(ty) * kTileSizeM; }
  constexpr TileBounds bounds() const {
    return TileBounds{x0(), y0(), x0() + kTileSizeM, y0() + kTileSizeM};
  }
  constexpr double centreX() const { return x0() + kTileSizeM * 0.5; }
  constexpr double centreY() const { return y0() + kTileSizeM * 0.5; }

  /// Writes "t_{tx}_{ty}" into buf (NUL-terminated, needs <= 26 bytes). Returns the length or -1
  /// if the buffer is too small.
  int name(char* buf, size_t cap) const;
  std::string name() const;
  /// Parses "t_{tx}_{ty}" (same grammar as tiling.py: ^t_(-?\d+)_(-?\d+)$, int32 range).
  static Result<Tile> parse(std::string_view name);

  constexpr bool operator==(const Tile& o) const { return tx == o.tx && ty == o.ty; }
  constexpr bool operator!=(const Tile& o) const { return !(*this == o); }
  /// Row-major order (ty, then tx) — the order tiles_in_bbox yields.
  constexpr bool operator<(const Tile& o) const { return ty != o.ty ? ty < o.ty : tx < o.tx; }
};

/// Tile containing (x, y). Inputs are clamped to the int32 grid range.
NYCSIM_API Tile tileOf(double x_m, double y_m);

/// Tiles intersecting the box, ty-major then tx (mirrors tiling.tiles_in_bbox, including its
/// 1e-9 upper-edge exclusion so a box ending exactly on a tile edge does not include the next
/// tile). Appends to `out`, returns the number appended.
NYCSIM_API size_t tilesInBbox(double xmin, double ymin, double xmax, double ymax,
                              std::vector<Tile>& out);

/// All tiles of the project scope box (crs.py SCOPE_*): 54 x 54 = 2916 tiles.
NYCSIM_API std::vector<Tile> scopeTiles();

/// Coarser LOD parent index: level 1 = 4 km cells, level 2 = 16 km cells (4^level).
struct ParentIndex {
  int32_t px, py;
};
NYCSIM_API ParentIndex parentTile(Tile tile, int level);

/// Euclidean distance from a point to the tile square (0 inside).
NYCSIM_API double distanceToTile(Tile tile, double x_m, double y_m);

}  // namespace tiling
}  // namespace nycsim
