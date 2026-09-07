// Record layouts of the NYCB runtime container (DATA_CONTRACTS §15).
//
// The producer is pipeline/nycsim_pipeline/runtime/nycb.py, which builds every record type as a
// numpy structured dtype with `align=True` — i.e. **natural C alignment**, exactly what a C++17
// compiler lays these structs out as without any packing pragma. The container header is likewise
// naturally aligned (24 bytes: 4 bytes of padding after `section_count` so `index_offset` is
// 8-aligned) and every section starts on an 8-byte boundary.
//
// Consequently these structs must NOT be packed: a packed layout would give Lane 44 instead of 48
// bytes, SignalController 28 instead of 32 and the header 20 instead of 24, and the reader would
// mis-decode the exporter's files. Every size and every field offset below is asserted against the
// exporter's own `describe_layout()` output (data/processed/runtime/nycb_layout.json), and
// core/tests/io/test_nycb.cpp re-checks them against a real file written by that exporter.
//
// All fields are little-endian; coordinates are NYC_TM metres; floats are float32 unless noted.
#pragma once

#include <cstddef>
#include <cstdint>

namespace nycsim {
namespace io {

/// Asserts that a record has the exporter's size and that a field sits at the exporter's offset.
#define NYCSIM_NYCB_FIELD(Type, field, offset) \
  static_assert(offsetof(Type, field) == (offset), #Type "::" #field " moved")

struct NycbHeader {
  char magic[4];         ///< "NYCB"
  uint32_t version;      ///< 1
  uint32_t sectionCount;
  // 4 bytes of padding here (natural alignment), matching the exporter's HEADER_DTYPE.
  uint64_t indexOffset;  ///< byte offset of the NycbIndexEntry array
};
static_assert(sizeof(NycbHeader) == 24, "NYCB header is 24 bytes (naturally aligned)");
NYCSIM_NYCB_FIELD(NycbHeader, magic, 0);
NYCSIM_NYCB_FIELD(NycbHeader, version, 4);
NYCSIM_NYCB_FIELD(NycbHeader, sectionCount, 8);
NYCSIM_NYCB_FIELD(NycbHeader, indexOffset, 16);

struct NycbIndexEntry {
  char name[16];  ///< NUL-padded; the exporter limits names to 15 bytes so it is always terminated
  uint64_t offset;
  uint64_t size;
  uint32_t elementSize;
  uint32_t elementCount;
};
static_assert(sizeof(NycbIndexEntry) == 40, "NYCB index entry is 40 bytes");
NYCSIM_NYCB_FIELD(NycbIndexEntry, name, 0);
NYCSIM_NYCB_FIELD(NycbIndexEntry, offset, 16);
NYCSIM_NYCB_FIELD(NycbIndexEntry, size, 24);
NYCSIM_NYCB_FIELD(NycbIndexEntry, elementSize, 32);
NYCSIM_NYCB_FIELD(NycbIndexEntry, elementCount, 36);

// ---- runtime/roadgraph.nycb ------------------------------------------------------------------
struct RoadNode {
  int64_t id;
  float x, y, z;
  uint8_t control;       ///< 0 none 1 signal 2 stop 3 all-way 4 yield
  uint8_t signalSource;  ///< 0 osm 1 dot_lpi 2 dot_barnes 3 dot_retiming 4 inferred
  uint16_t pad;
};
static_assert(sizeof(RoadNode) == 24, "");
NYCSIM_NYCB_FIELD(RoadNode, id, 0);
NYCSIM_NYCB_FIELD(RoadNode, x, 8);
NYCSIM_NYCB_FIELD(RoadNode, control, 20);
NYCSIM_NYCB_FIELD(RoadNode, signalSource, 21);
NYCSIM_NYCB_FIELD(RoadNode, pad, 22);

struct RoadSegment {
  int64_t id;
  int64_t fromNode, toNode;
  uint32_t firstVertex, vertexCount;
  uint8_t rwType, trafficDir, travelLanes, parkLanes;
  float widthM;
  uint8_t speedMph, bikeLane, surface, borough;
  uint32_t nameStr;
};
static_assert(sizeof(RoadSegment) == 48, "");
NYCSIM_NYCB_FIELD(RoadSegment, fromNode, 8);
NYCSIM_NYCB_FIELD(RoadSegment, toNode, 16);
NYCSIM_NYCB_FIELD(RoadSegment, firstVertex, 24);
NYCSIM_NYCB_FIELD(RoadSegment, vertexCount, 28);
NYCSIM_NYCB_FIELD(RoadSegment, rwType, 32);
NYCSIM_NYCB_FIELD(RoadSegment, widthM, 36);
NYCSIM_NYCB_FIELD(RoadSegment, speedMph, 40);
NYCSIM_NYCB_FIELD(RoadSegment, nameStr, 44);

struct Vertex3 {
  float x, y, z;
};
static_assert(sizeof(Vertex3) == 12, "");
NYCSIM_NYCB_FIELD(Vertex3, y, 4);
NYCSIM_NYCB_FIELD(Vertex3, z, 8);

struct Lane {
  int64_t id;
  int64_t segmentId;
  int8_t indexFromCenter, direction, kind, pad;
  float widthM, speedMps;
  uint32_t firstVertex, vertexCount;
  uint32_t firstSucc, succCount;
};
static_assert(sizeof(Lane) == 48, "Lane is naturally aligned to 48 bytes (44 if packed)");
NYCSIM_NYCB_FIELD(Lane, segmentId, 8);
NYCSIM_NYCB_FIELD(Lane, indexFromCenter, 16);
NYCSIM_NYCB_FIELD(Lane, direction, 17);
NYCSIM_NYCB_FIELD(Lane, kind, 18);
NYCSIM_NYCB_FIELD(Lane, pad, 19);
NYCSIM_NYCB_FIELD(Lane, widthM, 20);
NYCSIM_NYCB_FIELD(Lane, speedMps, 24);
NYCSIM_NYCB_FIELD(Lane, firstVertex, 28);
NYCSIM_NYCB_FIELD(Lane, vertexCount, 32);
NYCSIM_NYCB_FIELD(Lane, firstSucc, 36);
NYCSIM_NYCB_FIELD(Lane, succCount, 40);

struct LaneLink {
  int64_t laneId;
};
static_assert(sizeof(LaneLink) == 8, "");

struct JunctionLane {
  int64_t id;
  int64_t fromLane, toLane;
  uint8_t turn;  ///< 0 straight 1 left 2 right 3 uturn
  uint8_t pad[3];
  int32_t signalGroup;
  uint32_t firstVertex, vertexCount;
  uint32_t firstYield, yieldCount;
};
static_assert(sizeof(JunctionLane) == 48, "");
NYCSIM_NYCB_FIELD(JunctionLane, fromLane, 8);
NYCSIM_NYCB_FIELD(JunctionLane, toLane, 16);
NYCSIM_NYCB_FIELD(JunctionLane, turn, 24);
NYCSIM_NYCB_FIELD(JunctionLane, pad, 25);
NYCSIM_NYCB_FIELD(JunctionLane, signalGroup, 28);
NYCSIM_NYCB_FIELD(JunctionLane, firstVertex, 32);
NYCSIM_NYCB_FIELD(JunctionLane, vertexCount, 36);
NYCSIM_NYCB_FIELD(JunctionLane, firstYield, 40);
NYCSIM_NYCB_FIELD(JunctionLane, yieldCount, 44);

struct YieldLink {
  int64_t laneId;
};
static_assert(sizeof(YieldLink) == 8, "");

// ---- runtime/signals.nycb --------------------------------------------------------------------
struct SignalController {
  int64_t nodeId;
  int32_t controllerId;
  float cycleS, offsetS;
  uint32_t firstPhase, phaseCount;
};
static_assert(sizeof(SignalController) == 32,
              "SignalController is naturally aligned to 32 bytes (28 if packed)");
NYCSIM_NYCB_FIELD(SignalController, controllerId, 8);
NYCSIM_NYCB_FIELD(SignalController, cycleS, 12);
NYCSIM_NYCB_FIELD(SignalController, offsetS, 16);
NYCSIM_NYCB_FIELD(SignalController, firstPhase, 20);
NYCSIM_NYCB_FIELD(SignalController, phaseCount, 24);

struct SignalPhase {
  int32_t group;
  float greenS, yellowS, allredS, pedWalkS, pedFlashS, lpiS;
};
static_assert(sizeof(SignalPhase) == 28, "");
NYCSIM_NYCB_FIELD(SignalPhase, greenS, 4);
NYCSIM_NYCB_FIELD(SignalPhase, lpiS, 24);

// ---- runtime/tiles.nycb ----------------------------------------------------------------------
struct TileRecord {
  int32_t tx, ty;
  float zMin, zMax;
  uint32_t nBuildings, nProps;
  uint8_t flags;  ///< has_terrain=1, has_water=2, has_land=4
  uint8_t boroughMask;
  uint16_t pad;
};
static_assert(sizeof(TileRecord) == 28, "");
NYCSIM_NYCB_FIELD(TileRecord, ty, 4);
NYCSIM_NYCB_FIELD(TileRecord, zMin, 8);
NYCSIM_NYCB_FIELD(TileRecord, nBuildings, 16);
NYCSIM_NYCB_FIELD(TileRecord, flags, 24);
NYCSIM_NYCB_FIELD(TileRecord, boroughMask, 25);

// ---- runtime/transit.nycb --------------------------------------------------------------------
struct BusRoute {
  uint32_t nameStr;
  uint32_t firstVertex, vertexCount;
  uint32_t firstStop, stopCount;
  uint16_t headwayMin[24];
};
static_assert(sizeof(BusRoute) == 68, "");
NYCSIM_NYCB_FIELD(BusRoute, firstVertex, 4);
NYCSIM_NYCB_FIELD(BusRoute, headwayMin, 20);

struct BusStop {
  int64_t id;
  float x, y, z;
  uint32_t nameStr;
};
static_assert(sizeof(BusStop) == 24, "");
NYCSIM_NYCB_FIELD(BusStop, x, 8);
NYCSIM_NYCB_FIELD(BusStop, nameStr, 20);

struct RouteStop {
  int64_t stopId;
};
static_assert(sizeof(RouteStop) == 8, "");

// ---- runtime/density.nycb --------------------------------------------------------------------
struct DensityCell {
  uint32_t ntaStr;
  uint8_t hour, dow;
  uint16_t pad;
  float vehPerKmLane, pedPerM2, taxiShare, truckShare, busShare, bikeShare;
};
static_assert(sizeof(DensityCell) == 32, "");
NYCSIM_NYCB_FIELD(DensityCell, hour, 4);
NYCSIM_NYCB_FIELD(DensityCell, dow, 5);
NYCSIM_NYCB_FIELD(DensityCell, pad, 6);
NYCSIM_NYCB_FIELD(DensityCell, vehPerKmLane, 8);
NYCSIM_NYCB_FIELD(DensityCell, bikeShare, 28);

struct NtaPoly {
  uint32_t ntaStr;
  uint32_t firstVertex, vertexCount;
};
static_assert(sizeof(NtaPoly) == 12, "");

// ---- runtime/pois.nycb -----------------------------------------------------------------------
struct Poi {
  float x, y;
  uint32_t addrStr;
};
static_assert(sizeof(Poi) == 12, "");

#undef NYCSIM_NYCB_FIELD

}  // namespace io
}  // namespace nycsim
