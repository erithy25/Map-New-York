#include <doctest/doctest.h>

#include <algorithm>
#include <cmath>

#include "nycsim/tiling/Tile.h"

using namespace nycsim;
using namespace nycsim::tiling;

// Reference values produced by pipeline/nycsim_pipeline/tiling.py (same inputs).
TEST_SUITE("tiling") {
  TEST_CASE("tileOf mirrors tiling.tile_of") {
    CHECK(tileOf(-0.5, 999.9) == Tile{-1, 0});
    CHECK(tileOf(1000.0, -1000.0) == Tile{1, -1});
    CHECK(tileOf(0.0, 0.0) == Tile{0, 0});
    CHECK(tileOf(-3000.0, 7999.999) == Tile{-3, 7});
    CHECK(tileOf(std::nan(""), 1e300) == Tile{0, 2147483647});  // clamped, never UB
  }
  TEST_CASE("names and parsing mirror tiling.Tile") {
    Tile t{-3, 7};
    CHECK(t.name() == "t_-3_7");
    char buf[8];
    CHECK(t.name(buf, sizeof buf) == 6);
    CHECK(Tile{-2147483647 - 1, 2147483647}.name(buf, sizeof buf) == -1);
    auto p = Tile::parse("t_-3_7");
    REQUIRE(p.ok());
    CHECK(*p == t);
    CHECK(Tile::parse("t_0_0").value() == Tile{0, 0});
    CHECK(Tile::parse("t_23_26").value() == Tile{23, 26});
    for (const char* bad : {"t_3_", "t_a_1", "x_1_2", "t_1_2_3", "t_+1_2", " t_1_2", "", "t_", "t_-_1",
                            "t_99999999999_1", "t_1_-"}) {
      CHECK_MESSAGE(!Tile::parse(bad).ok(), bad);
    }
    const TileBounds b = t.bounds();
    CHECK(b.xmin == -3000.0);
    CHECK(b.ymin == 7000.0);
    CHECK(b.xmax == -2000.0);
    CHECK(b.ymax == 8000.0);
    CHECK(t.centreX() == -2500.0);
  }
  TEST_CASE("tilesInBbox and scopeTiles mirror tiling.tiles_in_bbox / scope_tiles") {
    std::vector<Tile> v;
    CHECK(tilesInBbox(0, 0, 1000, 1000, v) == 1);
    CHECK(v[0] == Tile{0, 0});
    v.clear();
    CHECK(tilesInBbox(-1500.5, 200, 2300, 1000.0, v) == 5);
    CHECK(v.front() == Tile{-2, 0});
    CHECK(v.back() == Tile{2, 0});
    v.clear();
    CHECK(tilesInBbox(500, 500, 500, 500, v) == 1);
    v.clear();
    CHECK(tilesInBbox(999.9999999999, 0, 1000.0000001, 1, v) == 2);
    CHECK(v[1] == Tile{1, 0});
    v.clear();
    // Inverted box: tiling.py clamps the upper edge with max(xmax - 1e-9, xmin), so an inverted
    // box degenerates to the single tile containing (xmin, ymin). Verified against
    // list(tiles_in_bbox(10, 10, 0, 0)) == [Tile(0, 0)].
    CHECK(tilesInBbox(10, 10, 0, 0, v) == 1);
    CHECK(v[0] == Tile{0, 0});
    v.clear();
    CHECK(tilesInBbox(std::nan(""), 0, 1, 1, v) == 0);
    auto scope = scopeTiles();
    CHECK(scope.size() == 2916);
    CHECK(scope.front() == Tile{-30, -27});
    CHECK(scope.back() == Tile{23, 26});
    CHECK(std::is_sorted(scope.begin(), scope.end()));
    // Row-major order: second tile is (-29, -27).
    CHECK(scope[1] == Tile{-29, -27});
  }
  TEST_CASE("parentTile mirrors tiling.parent_tile") {
    CHECK(parentTile(Tile{-3, 7}, 1).px == -1);
    CHECK(parentTile(Tile{-3, 7}, 1).py == 1);
    CHECK(parentTile(Tile{-3, 7}, 2).px == -1);
    CHECK(parentTile(Tile{-3, 7}, 2).py == 0);
    CHECK(parentTile(Tile{15, -1}, 1).px == 3);
    CHECK(parentTile(Tile{15, -1}, 1).py == -1);
    CHECK(parentTile(Tile{-17, 16}, 2).px == -2);
    CHECK(parentTile(Tile{-17, 16}, 2).py == 1);
    CHECK(parentTile(Tile{-17, 16}, 0).px == -17);
  }
  TEST_CASE("distanceToTile is the box distance") {
    Tile t{0, 0};
    CHECK(distanceToTile(t, 500, 500) == 0.0);
    CHECK(distanceToTile(t, 1000, 500) == 0.0);
    CHECK(distanceToTile(t, 1300, 500) == doctest::Approx(300.0));
    CHECK(distanceToTile(t, -300, -400) == doctest::Approx(500.0));
    CHECK(distanceToTile(t, 500, 1250) == doctest::Approx(250.0));
  }
}
