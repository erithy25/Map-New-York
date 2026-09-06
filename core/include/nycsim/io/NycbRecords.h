// Record layouts of the NYCB runtime container (DATA_CONTRACTS §15). All records are little-endian
// and *packed* (no alignment padding) so that sizeof(record) == element_size written by the Python
// exporter (struct '<...' / numpy align=False). Packing also makes zero-copy views over an
// arbitrarily aligned buffer well-defined (alignment requirement 1). Field order is the contract's.
#pragma once

#include <cstdint>

namespace nycsim {
namespace io {

#pragma pack(push, 1)

struct NycbHeader {
  char magic[4];         ///< "NYCB"
  uint32_t version;      ///< 1
  uint32_t sectionCount;
  uint64_t indexOffset;  ///< byte offset of the NycbIndexEntry array
};
static_assert(sizeof(NycbHeader) == 20, "NYCB header is 20 bytes");

struct NycbIndexEntry {
  char name[16];         ///< NUL-padded (a 16-char name has no terminator)
  uint64_t offset;
  uint64_t size;
  uint32_t elementSize;
  uint32_t elementCount;
};
static_assert(sizeof(NycbIndexEntry) == 40, "NYCB index entry is 40 bytes");

// ---- runtime/roadgraph.nycb ------------------------------------------------------------------
struct RoadNode {
  int64_t id;
  float x, y, z;
  uint8_t control;       ///< 0 none 1 signal 2 stop 3 all-way 4 yield
  uint8_t signalSource;  ///< 0 osm 1 dot_lpi 2 dot_barnes 3 dot_retiming 4 inferred
  uint16_t pad;
};
static_assert(sizeof(RoadNode) == 24, "");

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

struct Vertex3 {
  float x, y, z;
};
static_assert(sizeof(Vertex3) == 12, "");

struct Lane {
  int64_t id;
  int64_t segmentId;
  int8_t indexFromCenter, direction, kind, pad;
  float widthM, speedMps;
  uint32_t firstVertex, vertexCount;
  uint32_t firstSucc, succCount;
};
static_assert(sizeof(Lane) == 44, "Lane is packed to 44 bytes (48 with natural alignment)");

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

struct YieldLink {
  int64_t laneId;
};

// ---- runtime/signals.nycb --------------------------------------------------------------------
struct SignalController {
  int64_t nodeId;
  int32_t controllerId;
  float cycleS, offsetS;
  uint32_t firstPhase, phaseCount;
};
static_assert(sizeof(SignalController) == 28, "SignalController is packed to 28 bytes (32 natural)");

struct SignalPhase {
  int32_t group;
  float greenS, yellowS, allredS, pedWalkS, pedFlashS, lpiS;
};
static_assert(sizeof(SignalPhase) == 28, "");

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

// ---- runtime/transit.nycb --------------------------------------------------------------------
struct BusRoute {
  uint32_t nameStr;
  uint32_t firstVertex, vertexCount;
  uint32_t firstStop, stopCount;
  uint16_t headwayMin[24];
};
static_assert(sizeof(BusRoute) == 68, "");

struct BusStop {
  int64_t id;
  float x, y, z;
  uint32_t nameStr;
};
static_assert(sizeof(BusStop) == 24, "");

struct RouteStop {
  int64_t stopId;
};

// ---- runtime/density.nycb --------------------------------------------------------------------
struct DensityCell {
  uint32_t ntaStr;
  uint8_t hour, dow;
  uint16_t pad;
  float vehPerKmLane, pedPerM2, taxiShare, truckShare, busShare, bikeShare;
};
static_assert(sizeof(DensityCell) == 32, "");

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

#pragma pack(pop)

}  // namespace io
}  // namespace nycsim
