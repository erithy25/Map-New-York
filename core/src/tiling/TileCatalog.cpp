#include "nycsim/tiling/TileCatalog.h"

namespace nycsim {
namespace tiling {

TileInfo toTileInfo(const io::TileRecord& r) {
  TileInfo t;
  t.tx = r.tx;
  t.ty = r.ty;
  t.zMin = r.zMin;
  t.zMax = r.zMax;
  t.nBuildings = r.nBuildings;
  t.nProps = r.nProps;
  t.flags = r.flags;
  t.boroughMask = r.boroughMask;
  return t;
}

io::TileRecord toTileRecord(const TileInfo& t) {
  io::TileRecord r;
  r.tx = t.tx;
  r.ty = t.ty;
  r.zMin = t.zMin;
  r.zMax = t.zMax;
  r.nBuildings = t.nBuildings;
  r.nProps = t.nProps;
  r.flags = t.flags;
  r.boroughMask = t.boroughMask;
  r.pad = 0;
  return r;
}

Result<std::vector<TileInfo>> readTileCatalog(const io::NycbReader& reader) {
  NYCSIM_TRY(records, reader.view<io::TileRecord>("tiles"));
  std::vector<TileInfo> out;
  out.reserve(records.size());
  for (const io::TileRecord& r : records) out.push_back(toTileInfo(r));
  return out;
}

Result<std::vector<TileInfo>> readTileCatalog(const char* path) {
  NYCSIM_TRY(reader, io::NycbReader::fromFile(path));
  return readTileCatalog(reader);
}

}  // namespace tiling
}  // namespace nycsim
