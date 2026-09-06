#include <doctest/doctest.h>

#include <cstring>
#include <string>
#include <vector>

#include "nycsim/io/Nycb.h"
#include "nycsim/io/NycbRecords.h"
#include "nycsim/tiling/TileCatalog.h"

using namespace nycsim;
using namespace nycsim::io;

namespace {

std::vector<uint8_t> buildSample(std::vector<uint32_t>* nameOffsets = nullptr) {
  NycbWriter w;
  std::vector<RoadNode> nodes(3);
  for (size_t i = 0; i < nodes.size(); ++i) {
    nodes[i].id = static_cast<int64_t>(1000 + i);
    nodes[i].x = 1.5f * static_cast<float>(i);
    nodes[i].y = -2.0f;
    nodes[i].z = 3.25f;
    nodes[i].control = 1;
    nodes[i].signalSource = 4;
    nodes[i].pad = 0;
  }
  REQUIRE(w.addRecords<RoadNode>("nodes", Span<const RoadNode>(nodes.data(), nodes.size())).ok());
  std::vector<RoadSegment> segs(2);
  std::memset(segs.data(), 0, sizeof(RoadSegment) * segs.size());
  segs[0].id = 7;
  segs[0].fromNode = 1000;
  segs[0].toNode = 1001;
  segs[0].nameStr = w.addString("BROADWAY");
  segs[1].id = 8;
  segs[1].nameStr = w.addString("WEST 42 STREET");
  segs[1].widthM = 18.3f;
  segs[1].speedMph = 25;
  if (nameOffsets) *nameOffsets = {segs[0].nameStr, segs[1].nameStr};
  REQUIRE(w.addRecords<RoadSegment>("segments", Span<const RoadSegment>(segs.data(), segs.size())).ok());
  std::vector<Lane> lanes(1);
  std::memset(lanes.data(), 0, sizeof(Lane));
  lanes[0].id = 99;
  lanes[0].speedMps = 11.176f;
  REQUIRE(w.addRecords<Lane>("lanes", Span<const Lane>(lanes.data(), lanes.size())).ok());
  const uint8_t blob[5] = {1, 2, 3, 4, 5};
  REQUIRE(w.addSection("blob", ByteSpan(blob, 5), 0, 0).ok());
  auto r = w.finish();
  REQUIRE(r.ok());
  return *r;
}

}  // namespace

TEST_SUITE("io") {
  TEST_CASE("record layouts match DATA_CONTRACTS §15 (packed sizes)") {
    CHECK(sizeof(NycbHeader) == 20);
    CHECK(sizeof(NycbIndexEntry) == 40);
    CHECK(sizeof(RoadNode) == 24);
    CHECK(sizeof(RoadSegment) == 48);
    CHECK(sizeof(Lane) == 44);
    CHECK(sizeof(JunctionLane) == 48);
    CHECK(sizeof(SignalController) == 28);
    CHECK(sizeof(SignalPhase) == 28);
    CHECK(sizeof(TileRecord) == 28);
    CHECK(sizeof(BusRoute) == 68);
    CHECK(sizeof(BusStop) == 24);
    CHECK(sizeof(DensityCell) == 32);
    CHECK(sizeof(NtaPoly) == 12);
    CHECK(sizeof(Poi) == 12);
    CHECK(hostIsLittleEndian());
  }

  TEST_CASE("writer produces the contract byte layout") {
    std::vector<uint32_t> offs;
    const auto bytes = buildSample(&offs);
    REQUIRE(bytes.size() > 20);
    CHECK(std::memcmp(bytes.data(), "NYCB", 4) == 0);
    uint32_t version, count;
    uint64_t indexOffset;
    std::memcpy(&version, bytes.data() + 4, 4);
    std::memcpy(&count, bytes.data() + 8, 4);
    std::memcpy(&indexOffset, bytes.data() + 12, 8);
    CHECK(version == 1);
    CHECK(count == 5);  // nodes, segments, lanes, blob, strtab
    CHECK(indexOffset + count * 40 == bytes.size());
    // First index entry: name "nodes", offset 32 (header padded to 16), size 72, es 24, ec 3.
    NycbIndexEntry e;
    std::memcpy(&e, bytes.data() + indexOffset, sizeof e);
    CHECK(std::string(e.name, 5) == "nodes");
    CHECK(e.name[5] == '\0');
    CHECK(e.offset == 32);
    CHECK(e.size == 72);
    CHECK(e.elementSize == 24);
    CHECK(e.elementCount == 3);
    CHECK(e.offset % 16 == 0);
    // Little-endian int64 id 1000 at the start of the nodes section.
    CHECK(bytes[32] == 0xE8);
    CHECK(bytes[33] == 0x03);
    CHECK(offs[0] == 1);  // first interned string follows the "" at offset 0
    CHECK(offs[1] == 1 + 9);
  }

  TEST_CASE("reader round trip: typed views, strings, raw sections") {
    std::vector<uint32_t> offs;
    auto bytes = buildSample(&offs);
    auto r = NycbReader::fromMemory(ByteSpan(bytes.data(), bytes.size()));
    REQUIRE(r.ok());
    NycbReader& reader = *r;
    CHECK(reader.version() == 1);
    CHECK(reader.sections().size() == 5);
    CHECK(reader.has("nodes"));
    CHECK(reader.has("strtab"));
    CHECK_FALSE(reader.has("missing"));
    auto nodes = reader.view<RoadNode>("nodes");
    REQUIRE(nodes.ok());
    REQUIRE(nodes->size() == 3);
    CHECK((*nodes)[2].id == 1002);
    CHECK((*nodes)[2].x == doctest::Approx(3.0f));
    CHECK((*nodes)[0].signalSource == 4);
    auto segs = reader.view<RoadSegment>("segments");
    REQUIRE(segs.ok());
    CHECK(reader.string((*segs)[0].nameStr).value() == "BROADWAY");
    CHECK(reader.string((*segs)[1].nameStr).value() == "WEST 42 STREET");
    CHECK(reader.string(0).value() == "");
    CHECK((*segs)[1].widthM == doctest::Approx(18.3f));
    auto lanes = reader.view<Lane>("lanes");
    REQUIRE(lanes.ok());
    CHECK((*lanes)[0].id == 99);
    CHECK((*lanes)[0].speedMps == doctest::Approx(11.176f));
    // Wrong record type for a section -> FormatError, not UB.
    auto wrong = reader.view<Lane>("nodes");
    CHECK_FALSE(wrong.ok());
    CHECK(wrong.error().code == ErrorCode::FormatError);
    CHECK(reader.view<RoadNode>("missing").error().code == ErrorCode::NotFound);
    auto blob = reader.bytes("blob");
    REQUIRE(blob.size() == 5);
    CHECK(blob[4] == 5);
    CHECK(reader.bytes("missing").empty());
    CHECK_FALSE(reader.string(1u << 30).ok());
    // Owned-buffer and move semantics.
    auto owned = NycbReader::fromBuffer(std::vector<uint8_t>(bytes));
    REQUIRE(owned.ok());
    NycbReader moved = std::move(*owned);
    CHECK(moved.view<RoadNode>("nodes").value().size() == 3);
    CHECK(moved.sizeBytes() == bytes.size());
  }

  TEST_CASE("reader rejects corrupt containers with typed errors") {
    const auto good = buildSample();
    auto load = [](std::vector<uint8_t> b) { return NycbReader::fromMemory(ByteSpan(b.data(), b.size())); };
    {
      auto b = good;
      b[0] = 'X';
      CHECK(load(b).error().code == ErrorCode::BadMagic);
    }
    {
      auto b = good;
      b[4] = 2;
      CHECK(load(b).error().code == ErrorCode::UnsupportedVersion);
    }
    {
      std::vector<uint8_t> b(good.begin(), good.begin() + 10);
      CHECK(load(b).error().code == ErrorCode::Truncated);
    }
    {
      auto b = good;
      b.resize(b.size() - 1);  // index cut short
      CHECK(load(b).error().code == ErrorCode::Truncated);
    }
    {
      auto b = good;
      uint64_t bogus = b.size() + 100;
      std::memcpy(b.data() + 12, &bogus, 8);
      CHECK(load(b).error().code == ErrorCode::Truncated);
    }
    {
      auto b = good;
      uint64_t indexOffset;
      std::memcpy(&indexOffset, b.data() + 12, 8);
      // Section 0 size beyond EOF.
      uint64_t huge = 1ull << 40;
      std::memcpy(b.data() + indexOffset + 24, &huge, 8);
      CHECK(load(b).error().code == ErrorCode::Truncated);
    }
    {
      auto b = good;
      uint64_t indexOffset;
      std::memcpy(&indexOffset, b.data() + 12, 8);
      uint32_t es = 23;  // 23 * 3 != 72
      std::memcpy(b.data() + indexOffset + 32, &es, 4);
      CHECK(load(b).error().code == ErrorCode::FormatError);
    }
    {
      auto b = good;
      uint64_t indexOffset;
      std::memcpy(&indexOffset, b.data() + 12, 8);
      // Duplicate name: rename section 1 to "nodes".
      std::memcpy(b.data() + indexOffset + 40, "nodes\0\0\0\0\0\0\0\0\0\0\0", 16);
      CHECK(load(b).error().code == ErrorCode::FormatError);
    }
    {
      auto b = good;
      uint64_t indexOffset;
      std::memcpy(&indexOffset, b.data() + 12, 8);
      // Empty name.
      std::memset(b.data() + indexOffset, 0, 16);
      CHECK(load(b).error().code == ErrorCode::FormatError);
    }
    {
      // strtab without trailing NUL.
      auto b = good;
      uint64_t indexOffset;
      std::memcpy(&indexOffset, b.data() + 12, 8);
      NycbIndexEntry e;
      std::memcpy(&e, b.data() + indexOffset + 4 * 40, sizeof e);
      REQUIRE(std::string(e.name) == "strtab");
      b[static_cast<size_t>(e.offset + e.size - 1)] = 'x';
      CHECK(load(b).error().code == ErrorCode::FormatError);
    }
    CHECK(NycbReader::fromFile("/nonexistent/dir/file.nycb").error().code == ErrorCode::IoError);
    CHECK(NycbReader::fromFile("").error().code == ErrorCode::InvalidArgument);
  }

  TEST_CASE("writer validation") {
    NycbWriter w;
    const uint8_t d[4] = {0, 0, 0, 0};
    CHECK(w.addSection("", ByteSpan(d, 4), 4, 1).error().code == ErrorCode::InvalidArgument);
    CHECK(w.addSection("seventeen_chars__", ByteSpan(d, 4), 4, 1).error().code == ErrorCode::InvalidArgument);
    CHECK(w.addSection("a", ByteSpan(d, 4), 3, 1).error().code == ErrorCode::InvalidArgument);
    CHECK(w.addSection("a", ByteSpan(d, 4), 0, 1).error().code == ErrorCode::InvalidArgument);
    CHECK(w.addSection("a", ByteSpan(d, 4), 4, 1).ok());
    CHECK(w.addSection("a", ByteSpan(d, 4), 4, 1).error().code == ErrorCode::InvalidArgument);
    CHECK(w.addSection("sixteen_chars_ok", ByteSpan(d, 4), 2, 2).ok());
    CHECK(w.addString("dup") == w.addString("dup"));
    CHECK(w.addString("") == 0);
    // Manual strtab plus interned strings is rejected.
    CHECK(w.addSection("strtab", ByteSpan(d, 1), 1, 1).ok());
    CHECK(w.finish().error().code == ErrorCode::StateError);
    // Empty container round-trips.
    NycbWriter empty;
    auto bytes = empty.finish();
    REQUIRE(bytes.ok());
    auto r = NycbReader::fromMemory(ByteSpan(bytes->data(), bytes->size()));
    REQUIRE(r.ok());
    CHECK(r->sections().empty());
    CHECK_FALSE(r->hasStrtab());
    CHECK(r->string(0).error().code == ErrorCode::NotFound);
  }

  TEST_CASE("file round trip and tile catalogue") {
    const std::string path = std::string(NYCSIM_TEST_DATA_DIR) + "/../../build/test_tiles.nycb";
    NycbWriter w;
    std::vector<TileRecord> tiles(3);
    std::memset(tiles.data(), 0, sizeof(TileRecord) * tiles.size());
    tiles[0].tx = -3;
    tiles[0].ty = 7;
    tiles[0].nBuildings = 412;
    tiles[0].nProps = 88;
    tiles[0].flags = 5;
    tiles[0].boroughMask = 1 << 1;
    tiles[1].tx = 0;
    tiles[1].ty = 0;
    tiles[1].flags = 2;
    tiles[2].tx = 23;
    tiles[2].ty = 26;
    tiles[2].zMin = -1.5f;
    tiles[2].zMax = 12.25f;
    REQUIRE(w.addRecords<TileRecord>("tiles", Span<const TileRecord>(tiles.data(), tiles.size())).ok());
    auto wr = w.writeFile(path.c_str());
    if (!wr) {
      // Build directory may not exist in odd layouts; fall back to an in-memory check.
      MESSAGE("could not write ", path, ": ", wr.error().message);
      auto bytes = w.finish();
      REQUIRE(bytes.ok());
      auto rd = NycbReader::fromBuffer(std::move(*bytes));
      REQUIRE(rd.ok());
      auto cat = tiling::readTileCatalog(*rd);
      REQUIRE(cat.ok());
      CHECK(cat->size() == 3);
      return;
    }
    auto cat = tiling::readTileCatalog(path.c_str());
    REQUIRE(cat.ok());
    REQUIRE(cat->size() == 3);
    CHECK((*cat)[0].tx == -3);
    CHECK((*cat)[0].ty == 7);
    CHECK((*cat)[0].nBuildings == 412);
    CHECK((*cat)[0].flags == 5);
    CHECK((*cat)[0].boroughMask == 2);
    CHECK((*cat)[2].zMax == doctest::Approx(12.25f));
    const TileRecord back = tiling::toTileRecord((*cat)[0]);
    CHECK(std::memcmp(&back, &tiles[0], sizeof back) == 0);
    std::remove(path.c_str());
    // A container without a "tiles" section is a NotFound error.
    NycbWriter other;
    const uint8_t d[4] = {1, 2, 3, 4};
    REQUIRE(other.addSection("blob", ByteSpan(d, 4), 0, 0).ok());
    auto bytes = other.finish();
    REQUIRE(bytes.ok());
    auto rd = NycbReader::fromBuffer(std::move(*bytes));
    REQUIRE(rd.ok());
    CHECK(tiling::readTileCatalog(*rd).error().code == ErrorCode::NotFound);
  }
}
