// Loads the tile catalogue (runtime/tiles.nycb, section "tiles") into TileInfo records for the
// TileScheduler.
#pragma once

#include <vector>

#include "nycsim/Config.h"
#include "nycsim/io/Nycb.h"
#include "nycsim/tiling/TileScheduler.h"
#include "nycsim/util/Result.h"

namespace nycsim {
namespace tiling {

NYCSIM_API TileInfo toTileInfo(const io::TileRecord& r);
NYCSIM_API io::TileRecord toTileRecord(const TileInfo& t);
/// Reads every record of the "tiles" section.
NYCSIM_API Result<std::vector<TileInfo>> readTileCatalog(const io::NycbReader& reader);
/// Convenience: opens the file and reads the catalogue.
NYCSIM_API Result<std::vector<TileInfo>> readTileCatalog(const char* path);

}  // namespace tiling
}  // namespace nycsim
