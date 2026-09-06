#include <doctest/doctest.h>

#include "nycb_expected.h"

#include <cstdio>
#include <cstring>
#include <string>
#include <vector>

#include "nycsim/io/Json.h"
#include "nycsim/io/Nycb.h"
#include "nycsim/io/NycbRecords.h"
#include "nycsim/tiling/TileCatalog.h"
#if defined(NYCSIM_HAVE_ROUTING_LANE)
#include "nycsim/routing/RoadGraph.h"
#endif

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

/// Opens one of the exporter-written fixtures in core/tests/data/runtime/.
NycbReader openFixture(const char* name) {
  const std::string path = std::string(NYCSIM_TEST_DATA_DIR) + "/runtime/" + name;
  auto r = NycbReader::fromFile(path.c_str());
  REQUIRE_MESSAGE(r.ok(), "cannot open " << path << ": " << (r.ok() ? "" : r.error().message));
  return std::move(*r);
}

}  // namespace

TEST_SUITE("io") {
  TEST_CASE("record layouts match the exporter's naturally aligned sizes (DATA_CONTRACTS §15)") {
    // These are the sizes pipeline/nycsim_pipeline/runtime/nycb.py emits (numpy dtypes built with
    // align=True), recorded in data/processed/runtime/nycb_layout.json by the roads stage.
    CHECK(sizeof(NycbHeader) == 24);
    CHECK(sizeof(NycbIndexEntry) == 40);
    CHECK(sizeof(RoadNode) == 24);
    CHECK(sizeof(RoadSegment) == 48);
    CHECK(sizeof(Lane) == 48);
    CHECK(sizeof(JunctionLane) == 48);
    CHECK(sizeof(SignalController) == 32);
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
    REQUIRE(bytes.size() > 24);
    CHECK(std::memcmp(bytes.data(), "NYCB", 4) == 0);
    uint32_t version, count;
    uint64_t indexOffset;
    std::memcpy(&version, bytes.data() + 4, 4);
    std::memcpy(&count, bytes.data() + 8, 4);
    // 4 bytes of padding sit between section_count and index_offset (natural alignment), so the
    // 64-bit offset is at byte 16, exactly where runtime/nycb.py's HEADER_DTYPE puts it.
    std::memcpy(&indexOffset, bytes.data() + 16, 8);
    CHECK(version == 1);
    CHECK(count == 5);  // nodes, segments, lanes, blob, strtab
    CHECK(indexOffset % 8 == 0);
    CHECK(indexOffset + count * 40 == bytes.size());
    // First index entry: name "nodes", offset 24 (immediately after the header), size 72.
    NycbIndexEntry e;
    std::memcpy(&e, bytes.data() + indexOffset, sizeof e);
    CHECK(std::string(e.name, 5) == "nodes");
    CHECK(e.name[5] == '\0');
    CHECK(e.offset == 24);
    CHECK(e.size == 72);
    CHECK(e.elementSize == 24);
    CHECK(e.elementCount == 3);
    CHECK(e.offset % 8 == 0);
    // Little-endian int64 id 1000 at the start of the nodes section.
    CHECK(bytes[24] == 0xE8);
    CHECK(bytes[25] == 0x03);
    // Every section starts on an 8-byte boundary.
    for (uint32_t i = 0; i < count; ++i) {
      NycbIndexEntry ei;
      std::memcpy(&ei, bytes.data() + indexOffset + i * sizeof(NycbIndexEntry), sizeof ei);
      CHECK(ei.offset % 8 == 0);
      CHECK(ei.offset + ei.size <= indexOffset);
    }
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
      std::memcpy(b.data() + 16, &bogus, 8);
      CHECK(load(b).error().code == ErrorCode::Truncated);
    }
    {
      auto b = good;
      uint64_t indexOffset;
      std::memcpy(&indexOffset, b.data() + 16, 8);
      // Section 0 size beyond EOF.
      uint64_t huge = 1ull << 40;
      std::memcpy(b.data() + indexOffset + 24, &huge, 8);
      CHECK(load(b).error().code == ErrorCode::Truncated);
    }
    {
      auto b = good;
      uint64_t indexOffset;
      std::memcpy(&indexOffset, b.data() + 16, 8);
      uint32_t es = 23;  // 23 * 3 != 72
      std::memcpy(b.data() + indexOffset + 32, &es, 4);
      CHECK(load(b).error().code == ErrorCode::FormatError);
    }
    {
      auto b = good;
      uint64_t indexOffset;
      std::memcpy(&indexOffset, b.data() + 16, 8);
      // Duplicate name: rename section 1 to "nodes".
      std::memcpy(b.data() + indexOffset + 40, "nodes\0\0\0\0\0\0\0\0\0\0\0", 16);
      CHECK(load(b).error().code == ErrorCode::FormatError);
    }
    {
      auto b = good;
      uint64_t indexOffset;
      std::memcpy(&indexOffset, b.data() + 16, 8);
      // Empty name.
      std::memset(b.data() + indexOffset, 0, 16);
      CHECK(load(b).error().code == ErrorCode::FormatError);
    }
    {
      // strtab without trailing NUL.
      auto b = good;
      uint64_t indexOffset;
      std::memcpy(&indexOffset, b.data() + 16, 8);
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
    // The exporter's limit is 15 ASCII bytes so the 16-byte index field is always terminated.
    CHECK(w.addSection("sixteen_chars_ok", ByteSpan(d, 4), 2, 2).error().code ==
          ErrorCode::InvalidArgument);
    CHECK(w.addSection("fifteen_chars_o", ByteSpan(d, 4), 2, 2).ok());
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

// ---------------------------------------------------------------------------------------------
// Interoperability with the producer: pipeline/nycsim_pipeline/runtime/nycb.py.
//
// core/tests/data/runtime/*.nycb are written by that exporter itself
// (docs/verification/core/gen_nycb_fixture.py), one file per DATA_CONTRACTS §15 container, and are
// read back here with the C++ reader. If the roads stage has produced the real
// data/processed/runtime/*.nycb, those are checked too — section counts against the parquet row
// counts, and every index into another section for being in range.
// ---------------------------------------------------------------------------------------------

TEST_SUITE("io") {
  TEST_CASE("record sizes equal the exporter's numpy dtype itemsizes") {
    struct Named {
      const char* name;
      uint32_t bytes;
    };
    const Named ours[] = {
        {"header", static_cast<uint32_t>(sizeof(NycbHeader))},
        {"index_entry", static_cast<uint32_t>(sizeof(NycbIndexEntry))},
        {"nodes", static_cast<uint32_t>(sizeof(RoadNode))},
        {"segments", static_cast<uint32_t>(sizeof(RoadSegment))},
        {"vertices", static_cast<uint32_t>(sizeof(Vertex3))},
        {"lanes", static_cast<uint32_t>(sizeof(Lane))},
        {"lane_links", static_cast<uint32_t>(sizeof(LaneLink))},
        {"junction_lanes", static_cast<uint32_t>(sizeof(JunctionLane))},
        {"controllers", static_cast<uint32_t>(sizeof(SignalController))},
        {"phases", static_cast<uint32_t>(sizeof(SignalPhase))},
        {"tiles", static_cast<uint32_t>(sizeof(TileRecord))},
        {"bus_routes", static_cast<uint32_t>(sizeof(BusRoute))},
        {"bus_stops", static_cast<uint32_t>(sizeof(BusStop))},
        {"cells", static_cast<uint32_t>(sizeof(DensityCell))},
        {"nta_polys", static_cast<uint32_t>(sizeof(NtaPoly))},
        {"pois", static_cast<uint32_t>(sizeof(Poi))},
    };
    int matched = 0;
    for (const Named& o : ours) {
      for (int i = 0; i < nycsim_test_nycb::kRecordSizeN; ++i) {
        if (std::string(nycsim_test_nycb::kRecordSizes[i].name) != o.name) continue;
        INFO("record ", o.name);
        CHECK(o.bytes == nycsim_test_nycb::kRecordSizes[i].bytes);
        ++matched;
      }
    }
    CHECK(matched == 16);
  }

  TEST_CASE("files written by the Python exporter are read field-for-field") {
    // roadgraph.nycb
    NycbReader rg = openFixture("roadgraph.nycb");
    CHECK(rg.version() == 1);
    const auto nodes = rg.view<RoadNode>("nodes");
    REQUIRE(nodes.ok());
    REQUIRE(nodes.value().size() == 3);
    CHECK(nodes.value()[0].id == 1000);
    CHECK(nodes.value()[0].x == doctest::Approx(-3011.9766f).epsilon(1e-4));
    CHECK(nodes.value()[0].y == doctest::Approx(5379.805f).epsilon(1e-4));
    CHECK(nodes.value()[0].z == doctest::Approx(10.25f));
    CHECK(nodes.value()[0].control == 1);
    CHECK(nodes.value()[0].signalSource == 1);
    CHECK(nodes.value()[1].id == 2000);
    CHECK(nodes.value()[2].control == 2);

    const auto segs = rg.view<RoadSegment>("segments");
    REQUIRE(segs.ok());
    REQUIRE(segs.value().size() == 2);
    CHECK(segs.value()[0].id == 50);
    CHECK(segs.value()[0].fromNode == 1000);
    CHECK(segs.value()[0].toNode == 2000);
    CHECK(segs.value()[0].firstVertex == 0);
    CHECK(segs.value()[0].vertexCount == 2);
    CHECK(segs.value()[0].rwType == 1);
    CHECK(segs.value()[0].trafficDir == 0);
    CHECK(segs.value()[0].travelLanes == 2);
    CHECK(segs.value()[0].parkLanes == 1);
    CHECK(segs.value()[0].widthM == doctest::Approx(12.8f));
    CHECK(segs.value()[0].speedMph == 25);
    CHECK(segs.value()[0].bikeLane == 2);
    CHECK(segs.value()[0].surface == 0);
    CHECK(segs.value()[0].borough == 1);
    CHECK(segs.value()[1].rwType == 3);
    CHECK(segs.value()[1].widthM == doctest::Approx(24.4f));
    // Strings resolve through the strtab exactly as the exporter interned them.
    for (int i = 0; i < nycsim_test_nycb::kStringOffsetN; ++i) {
      const auto& so = nycsim_test_nycb::kStringOffsets[i];
      const auto s = rg.string(so.offset);
      REQUIRE(s.ok());
      CHECK(s.value() == so.text);
    }
    CHECK(rg.string(0).value().empty());
    CHECK(rg.string(segs.value()[0].nameStr).value() == "BROADWAY");
    CHECK(rg.string(segs.value()[1].nameStr).value() == "BROOKLYN BRIDGE");

    const auto lanes = rg.view<Lane>("lanes");
    REQUIRE(lanes.ok());
    REQUIRE(lanes.value().size() == 2);
    CHECK(lanes.value()[0].id == 900);
    CHECK(lanes.value()[0].segmentId == 50);
    CHECK(lanes.value()[0].indexFromCenter == 1);
    CHECK(lanes.value()[0].direction == 1);
    CHECK(lanes.value()[0].kind == 0);
    CHECK(lanes.value()[0].widthM == doctest::Approx(3.2f));
    CHECK(lanes.value()[0].speedMps == doctest::Approx(11.176f));
    CHECK(lanes.value()[1].indexFromCenter == -2);
    CHECK(lanes.value()[1].direction == -1);
    CHECK(lanes.value()[1].kind == 3);
    CHECK(lanes.value()[1].speedMps == doctest::Approx(20.1168f));

    const auto junc = rg.view<JunctionLane>("junction_lanes");
    REQUIRE(junc.ok());
    REQUIRE(junc.value().size() == 1);
    CHECK(junc.value()[0].id == 7000);
    CHECK(junc.value()[0].fromLane == 900);
    CHECK(junc.value()[0].toLane == 901);
    CHECK(junc.value()[0].turn == 1);
    CHECK(junc.value()[0].signalGroup == 2);
    CHECK(junc.value()[0].firstVertex == 1);
    CHECK(junc.value()[0].vertexCount == 3);
    CHECK(junc.value()[0].yieldCount == 1);

    const auto vtx = rg.view<Vertex3>("vertices");
    REQUIRE(vtx.ok());
    CHECK(vtx.value().size() == 5);
    CHECK(vtx.value()[4].x == doctest::Approx(300.0f));
    CHECK(rg.view<LaneLink>("lane_links").value().size() == 2);
    CHECK(rg.view<LaneLink>("lane_links").value()[0].laneId == 901);
    CHECK(rg.view<YieldLink>("yield_links").value()[0].laneId == 901);

    // signals.nycb
    NycbReader sg = openFixture("signals.nycb");
    const auto ctrl = sg.view<SignalController>("controllers");
    REQUIRE(ctrl.ok());
    REQUIRE(ctrl.value().size() == 2);
    CHECK(ctrl.value()[0].nodeId == 1000);
    CHECK(ctrl.value()[0].controllerId == 11);
    CHECK(ctrl.value()[0].cycleS == doctest::Approx(90.0f));
    CHECK(ctrl.value()[0].offsetS == doctest::Approx(0.0f));
    CHECK(ctrl.value()[0].firstPhase == 0);
    CHECK(ctrl.value()[0].phaseCount == 2);
    CHECK(ctrl.value()[1].cycleS == doctest::Approx(60.0f));
    CHECK(ctrl.value()[1].offsetS == doctest::Approx(12.5f));
    const auto ph = sg.view<SignalPhase>("phases");
    REQUIRE(ph.ok());
    REQUIRE(ph.value().size() == 3);
    CHECK(ph.value()[0].greenS == doctest::Approx(45.0f));
    CHECK(ph.value()[0].lpiS == doctest::Approx(7.0f));
    CHECK(ph.value()[1].group == 1);
    CHECK(ph.value()[2].greenS == doctest::Approx(30.0f));

    // tiles.nycb
    NycbReader tl = openFixture("tiles.nycb");
    const auto tiles = tl.view<TileRecord>("tiles");
    REQUIRE(tiles.ok());
    REQUIRE(tiles.value().size() == 2);
    CHECK(tiles.value()[0].tx == -3);
    CHECK(tiles.value()[0].ty == 5);
    CHECK(tiles.value()[0].zMax == doctest::Approx(40.0f));
    CHECK(tiles.value()[0].nBuildings == 412);
    CHECK(tiles.value()[0].nProps == 180);
    CHECK(tiles.value()[0].flags == 5);
    CHECK(tiles.value()[0].boroughMask == 1);
    CHECK(tiles.value()[1].ty == -7);
    CHECK(tiles.value()[1].zMin == doctest::Approx(-2.1f));

    // transit.nycb
    NycbReader tr = openFixture("transit.nycb");
    const auto routes = tr.view<BusRoute>("bus_routes");
    REQUIRE(routes.ok());
    REQUIRE(routes.value().size() == 1);
    CHECK(tr.string(routes.value()[0].nameStr).value() == "M15-SBS");
    CHECK(routes.value()[0].stopCount == 2);
    for (int i = 0; i < 24; ++i) CHECK(routes.value()[0].headwayMin[i] == i);
    const auto stops = tr.view<BusStop>("bus_stops");
    REQUIRE(stops.ok());
    REQUIRE(stops.value().size() == 2);
    CHECK(stops.value()[0].id == 400001);
    CHECK(tr.string(stops.value()[0].nameStr).value() == "1 AV/E 14 ST");
    CHECK(tr.string(stops.value()[1].nameStr).value() == "1 AV/E 23 ST");
    CHECK(tr.view<RouteStop>("route_stops").value()[1].stopId == 400002);

    // density.nycb
    NycbReader dn = openFixture("density.nycb");
    const auto cells = dn.view<DensityCell>("cells");
    REQUIRE(cells.ok());
    REQUIRE(cells.value().size() == 2);
    CHECK(dn.string(cells.value()[0].ntaStr).value() == "MN17");
    CHECK(cells.value()[0].hour == 8);
    CHECK(cells.value()[0].dow == 0);
    CHECK(cells.value()[0].vehPerKmLane == doctest::Approx(55.0f));
    CHECK(cells.value()[0].pedPerM2 == doctest::Approx(0.35f));
    CHECK(cells.value()[0].bikeShare == doctest::Approx(0.05f));
    CHECK(cells.value()[1].hour == 20);
    CHECK(dn.view<NtaPoly>("nta_polys").value()[0].vertexCount == 4);

    // pois.nycb
    NycbReader po = openFixture("pois.nycb");
    const auto pois = po.view<Poi>("pois");
    REQUIRE(pois.ok());
    REQUIRE(pois.value().size() == 2);
    CHECK(po.string(pois.value()[0].addrStr).value() == "350 5 AVENUE");
    CHECK(po.string(pois.value()[1].addrStr).value() == "1 CENTRE STREET");

    // Every section count matches what the exporter reported.
    for (int i = 0; i < nycsim_test_nycb::kFixtureCountN; ++i) {
      const auto& c = nycsim_test_nycb::kFixtureCounts[i];
      INFO(c.file, " / ", c.section);
      NycbReader r = openFixture(c.file);
      const NycbSection* s = r.find(c.section);
      REQUIRE(s != nullptr);
      CHECK(s->elementCount == c.count);
      CHECK(s->offset % kNycbAlign == 0);
      CHECK(static_cast<uint64_t>(s->elementSize) * s->elementCount == s->size);
    }
  }

  TEST_CASE("the real exporter output loads, decodes and matches the parquet row counts") {
    // core/tests/data/runtime/real_counts.json is written by
    // docs/verification/core/gen_nycb_fixture.py and read here at run time, so the roads stage can
    // regenerate data/processed/runtime/*.nycb without a recompilation. It records, per file, the
    // byte size, every section's count and element_size, and the parquet row counts that C++
    // cannot read itself.
    const std::string sidecarPath = std::string(NYCSIM_TEST_DATA_DIR) + "/runtime/real_counts.json";
    std::string sidecar;
    {
      std::FILE* f = std::fopen(sidecarPath.c_str(), "rb");
      if (!f) {
        MESSAGE("real_counts.json absent - run docs/verification/core/gen_nycb_fixture.py");
        return;
      }
      char buf[8192];
      size_t n = 0;
      while ((n = std::fread(buf, 1, sizeof buf, f)) > 0) sidecar.append(buf, n);
      std::fclose(f);
    }
    const Result<json::Value> doc = json::parse(sidecar);
    REQUIRE(doc.ok());
    const json::Value* files = doc.value().find("files");
    REQUIRE(files != nullptr);
    REQUIRE(files->isObject());
    if (files->size() == 0) {
      MESSAGE("no data/processed/runtime/*.nycb existed when the sidecar was generated - skipped");
      return;
    }

    // sizeof() of the C++ record type for each section name the contract defines. This is the
    // Python-writer vs C++-reader divergence check and it holds whatever the data contains.
    struct KnownSection {
      const char* name;
      uint32_t bytes;
    };
    const KnownSection known[] = {
        {"nodes", static_cast<uint32_t>(sizeof(RoadNode))},
        {"segments", static_cast<uint32_t>(sizeof(RoadSegment))},
        {"vertices", static_cast<uint32_t>(sizeof(Vertex3))},
        {"lanes", static_cast<uint32_t>(sizeof(Lane))},
        {"lane_links", static_cast<uint32_t>(sizeof(LaneLink))},
        {"junction_lanes", static_cast<uint32_t>(sizeof(JunctionLane))},
        {"yield_links", static_cast<uint32_t>(sizeof(YieldLink))},
        {"controllers", static_cast<uint32_t>(sizeof(SignalController))},
        {"phases", static_cast<uint32_t>(sizeof(SignalPhase))},
        {"tiles", static_cast<uint32_t>(sizeof(TileRecord))},
        {"bus_routes", static_cast<uint32_t>(sizeof(BusRoute))},
        {"bus_stops", static_cast<uint32_t>(sizeof(BusStop))},
        {"route_stops", static_cast<uint32_t>(sizeof(RouteStop))},
        {"cells", static_cast<uint32_t>(sizeof(DensityCell))},
        {"nta_polys", static_cast<uint32_t>(sizeof(NtaPoly))},
        {"pois", static_cast<uint32_t>(sizeof(Poi))},
    };

    int filesRead = 0;
    int sectionsChecked = 0;
    int countsChecked = 0;
    int parquetChecked = 0;
    for (const json::Member& m : files->members()) {
      const std::string path = std::string(NYCSIM_REPO_ROOT) + "/data/processed/runtime/" + m.key;
      auto r = NycbReader::fromFile(path.c_str());
      if (!r) {
        MESSAGE("skipping " << m.key << ": " << r.error().message);
        continue;
      }
      ++filesRead;
      const NycbReader& reader = *r;
      INFO("file ", m.key);
      CHECK(reader.version() == 1);

      // --- structural assertions: always run, whatever the data holds.
      for (const NycbSection& s : reader.sections()) {
        ++sectionsChecked;
        INFO("section ", s.name);
        CHECK(s.offset % kNycbAlign == 0);
        CHECK(static_cast<uint64_t>(s.elementSize) * s.elementCount == s.size);
        CHECK(s.offset + s.size <= reader.sizeBytes());
        for (const KnownSection& k : known) {
          if (s.nameView() != k.name) continue;
          // The exporter's element_size must equal our sizeof for that record type.
          CHECK(s.elementSize == k.bytes);
        }
        if (s.nameView() == kNycbStrtab) CHECK(s.elementSize == 1);
      }

      // --- counts: only while the recorded byte size still describes the file on disk.
      const json::Value* recordedBytes = m.value.find("bytes");
      REQUIRE(recordedBytes != nullptr);
      if (static_cast<uint64_t>(recordedBytes->asInt()) != reader.sizeBytes()) {
        MESSAGE(m.key << " was regenerated since real_counts.json was written ("
                      << recordedBytes->asInt() << " -> " << reader.sizeBytes()
                      << " bytes); re-run docs/verification/core/gen_nycb_fixture.py. Structural "
                         "checks still ran; count checks skipped for this file.");
        continue;
      }
      const json::Value* sections = m.value.find("sections");
      REQUIRE(sections != nullptr);
      for (const json::Member& sm : sections->members()) {
        const NycbSection* s = reader.find(sm.key);
        INFO("section ", sm.key);
        REQUIRE(s != nullptr);
        const json::Value* count = sm.value.find("count");
        const json::Value* esize = sm.value.find("element_size");
        REQUIRE(count != nullptr);
        REQUIRE(esize != nullptr);
        CHECK(static_cast<int64_t>(s->elementCount) == count->asInt());
        CHECK(static_cast<int64_t>(s->elementSize) == esize->asInt());
        ++countsChecked;
      }
      // --- the check that catches a writer/reader divergence in the data itself: the exporter
      //     must emit exactly one record per parquet row.
      const json::Value* parquet = m.value.find("parquet_rows");
      if (parquet && parquet->isObject()) {
        for (const json::Member& pm : parquet->members()) {
          const NycbSection* s = reader.find(pm.key);
          INFO("parquet cross-check ", m.key, "/", pm.key);
          REQUIRE(s != nullptr);
          CHECK(static_cast<int64_t>(s->elementCount) == pm.value.asInt());
          ++parquetChecked;
        }
      }
    }
    CHECK(filesRead > 0);
    CHECK(sectionsChecked > 0);
    MESSAGE("real NYCB files: " << filesRead << " read, " << sectionsChecked
                                << " sections structurally checked, " << countsChecked
                                << " counts, " << parquetChecked << " parquet cross-checks");

    // --- cross-section integrity of the real road graph.
    const std::string rgPath = std::string(NYCSIM_REPO_ROOT) + "/data/processed/runtime/roadgraph.nycb";
    auto rg = NycbReader::fromFile(rgPath.c_str());
    if (!rg) {
      MESSAGE("real roadgraph.nycb not readable - integrity check skipped");
      return;
    }
    const auto segs = rg->view<RoadSegment>("segments");
    const auto lanes = rg->view<Lane>("lanes");
    const auto vtx = rg->view<Vertex3>("vertices");
    const auto links = rg->view<LaneLink>("lane_links");
    const auto junc = rg->view<JunctionLane>("junction_lanes");
    const auto yields = rg->view<YieldLink>("yield_links");
    REQUIRE(segs.ok());
    REQUIRE(lanes.ok());
    REQUIRE(vtx.ok());
    REQUIRE(links.ok());
    REQUIRE(junc.ok());
    REQUIRE(yields.ok());
    const uint64_t nv = vtx.value().size();
    uint64_t badSeg = 0, badLane = 0, badJunc = 0, badString = 0, degenerate = 0;
    for (const RoadSegment& s : segs.value()) {
      if (static_cast<uint64_t>(s.firstVertex) + s.vertexCount > nv) ++badSeg;
      if (s.vertexCount < 2) ++degenerate;
      if (!rg->string(s.nameStr).ok()) ++badString;
    }
    for (const Lane& l : lanes.value()) {
      if (static_cast<uint64_t>(l.firstVertex) + l.vertexCount > nv) ++badLane;
      if (static_cast<uint64_t>(l.firstSucc) + l.succCount > links.value().size()) ++badLane;
      if (l.vertexCount < 2) ++degenerate;
    }
    for (const JunctionLane& j : junc.value()) {
      if (static_cast<uint64_t>(j.firstVertex) + j.vertexCount > nv) ++badJunc;
      if (static_cast<uint64_t>(j.firstYield) + j.yieldCount > yields.value().size()) ++badJunc;
    }
    CHECK(badSeg == 0);
    CHECK(badLane == 0);
    CHECK(badJunc == 0);
    CHECK(badString == 0);
    CHECK(degenerate == 0);
    MESSAGE("real roadgraph.nycb: " << segs.value().size() << " segments, " << lanes.value().size()
                                    << " lanes, " << nv << " vertices, " << rg->sizeBytes()
                                    << " bytes");

#if defined(NYCSIM_HAVE_ROUTING_LANE)
    // Two independent decoders must agree on the same 100 MB file: core/io's reader above, and the
    // routing lane's self-contained NycbLite reader (routing/RoadGraph.cpp::loadFromNycb).
    {
      std::FILE* f = std::fopen(rgPath.c_str(), "rb");
      REQUIRE(f != nullptr);
      std::vector<uint8_t> buf;
      uint8_t chunk[1 << 16];
      size_t n = 0;
      while ((n = std::fread(chunk, 1, sizeof chunk, f)) > 0) buf.insert(buf.end(), chunk, chunk + n);
      std::fclose(f);
      routing::RoadGraph g;
      const bool loaded = g.loadFromNycb(buf.data(), buf.size());
      CHECK_MESSAGE(loaded, "routing::RoadGraph::loadFromNycb failed: " << g.lastError());
      if (loaded) {
        const auto nodes = rg->view<RoadNode>("nodes");
        REQUIRE(nodes.ok());
        CHECK(g.nodeCount() == nodes.value().size());
        CHECK(g.segmentCount() == segs.value().size());
        MESSAGE("routing::RoadGraph agrees: " << g.nodeCount() << " nodes, " << g.segmentCount()
                                              << " segments, " << g.laneCount() << " lanes");
      }
    }
#endif
  }
}
