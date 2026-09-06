// GameplayPedSim — pedestrian crowd stepped alongside the traffic world at 20 Hz on the same worker thread.
//
// Pure C++ (std + nycsim_core only). The walkable network is derived from the lane graph rather than from the
// planimetric sidewalk polygons: DATA_CONTRACTS §15 does not ship sidewalks in any runtime/*.nycb, so each road
// segment contributes two walk edges offset from its centreline by (width_m / 2 + kSidewalkOffsetM). Crossings are
// generated at nodes and gated by the real signal plan's pedestrian phase (WALK / flashing DON'T WALK, including
// the leading pedestrian interval) with an explicit jaywalking model on top. The gap versus ARCHITECTURE §10
// (planimetric sidewalk navmesh) is stated in docs/verification/unreal_gameplay/REPORT.md.
//
// The player character does *not* use this graph — it walks on the runtime navmesh built by
// UNYCNavigationSubsystem over the real sidewalk, plaza, park and bridge-walkway geometry.
#pragma once

#include <cstdint>
#include <string>
#include <vector>

#include "CoreAdapter/GameplayRoadNetwork.h"
#include "CoreAdapter/GameplayTrafficSim.h"
#include "nycsim/traffic/Random.h"
#include "nycsim/traffic/SpatialHash.h"

namespace nycsim_gameplay
{

enum : uint8_t
{
	kPedUmbrella = 1u << 0,
	kPedPhone = 1u << 1,
	kPedBag = 1u << 2,
	kPedDog = 1u << 3,
	kPedJaywalking = 1u << 4,
	kPedHeadphones = 1u << 5,
	kPedCoat = 1u << 6,
};

enum class PedState : uint8_t
{
	Walking = 0,
	WaitingToCross = 1,
	Crossing = 2,
	Idle = 3,
};

struct PedSnapshot
{
	uint32_t id = 0;
	float x = 0.f, y = 0.f, z = 0.f;  ///< NYC_TM metres at the ground
	float headingRad = 0.f;
	float speedMps = 0.f;
	uint8_t state = 0;      ///< PedState
	uint8_t archetype = 0;  ///< body / clothing archetype index (see kArchetypeCount)
	uint8_t variant = 0;    ///< per-archetype colour seed
	uint8_t flags = 0;
};

struct PedConfig
{
	uint64_t seed = 20260906ull;
	float stepSeconds = 0.05f;
	float spawnRadiusM = 140.f;
	float despawnRadiusM = 220.f;
	float protectRadiusM = 60.f;
	uint32_t maxPeds = 1400;
	float densityScale = 1.f;
	uint8_t hour = 8;
	uint8_t dow = 0;
	float rainRateMmH = 0.f;   ///< umbrellas above 0.3 mm/h
	float snowCover = 0.f;
	float temperatureC = 15.f; ///< coats below 12 °C
	/// Fallback pedestrians per m² of sidewalk when density.nycb is missing (NYC DOT counts: quiet street 0.02,
	/// Midtown peak 0.35 — ARCHITECTURE §10).
	float fallbackPedPerM2 = 0.035f;
	float sidewalkWidthM = 3.5f;
	/// Share of pedestrians who will cross against the signal when a safe gap exists (NYC observational studies
	/// put mid-block and against-signal crossing near 45–60 % in Manhattan).
	float jaywalkShare = 0.5f;
};

struct PedStats
{
	uint32_t peds = 0;
	uint32_t spawnedTotal = 0;
	uint32_t despawnedTotal = 0;
	uint32_t crossing = 0;
	uint32_t waiting = 0;
	uint32_t jaywalking = 0;
	/// Invariant checked by unreal/tools/gameplay_selftest.cpp: a crossing that started against a DON'T WALK /
	/// flashing phase without being flagged as a modelled jaywalker. Must stay 0.
	uint32_t unsafeCrossingStarts = 0;
	uint64_t steps = 0;
	double lastStepMs = 0.0;
	double avgStepMs = 0.0;
};

class PedSim
{
public:
	static constexpr uint8_t kArchetypeCount = 24;
	/// Sidewalk centreline offset from the kerb line (kerb sits at width_m / 2 from the centreline).
	static constexpr float kSidewalkOffsetM = 1.9f;

	PedSim();
	~PedSim();

	PedSim(const PedSim&) = delete;
	PedSim& operator=(const PedSim&) = delete;

	bool init(const RoadNetwork& network, const PedConfig& config, std::string& error);
	bool ready() const { return network_ != nullptr; }

	void setConfig(const PedConfig& config) { config_ = config; }
	const PedConfig& config() const { return config_; }
	void setObserver(const TrafficObserver& observer) { observer_ = observer; }

	/// Vehicle positions from the traffic step, used for gap acceptance and for stepping back off the kerb.
	void updateVehicles(const std::vector<VehicleSnapshot>& vehicles);

	void step();

	double simTime() const { return simTime_; }
	const PedStats& stats() const { return stats_; }

	void writeSnapshot(std::vector<PedSnapshot>& out) const;
	/// Pedestrians currently inside the carriageway, for TrafficSim::setPedObstacles().
	void writeObstacles(std::vector<PedObstacle>& out) const;

private:
	struct Ped
	{
		uint32_t id = 0;
		uint32_t segment = nycsim::routing::kInvalidIndex;
		uint8_t side = 0;    ///< 0 = left of the segment's geometric direction, 1 = right
		int8_t dir = 1;      ///< +1 walking along the segment geometry, -1 against
		float s = 0.f;       ///< metres along the segment centreline
		float v = 0.f;
		float desiredSpeed = 1.34f;
		float lateralJitter = 0.f;  ///< personal offset inside the sidewalk width
		PedState state = PedState::Walking;
		float timer = 0.f;
		// Crossing interpolation.
		float fromX = 0.f, fromY = 0.f, fromZ = 0.f;
		float toX = 0.f, toY = 0.f, toZ = 0.f;
		float crossT = 0.f;
		float crossLength = 0.f;
		uint32_t crossNode = nycsim::routing::kInvalidIndex;
		uint32_t nextSegment = nycsim::routing::kInvalidIndex;
		uint8_t nextSide = 0;
		int8_t nextDir = 1;
		float headingRad = 0.f;
		uint8_t archetype = 0;
		uint8_t variant = 0;
		uint8_t flags = 0;
		bool active = false;
		nycsim::Rng rng;
	};

	struct VehicleProbe
	{
		float x = 0.f, y = 0.f, dx = 1.f, dy = 0.f, speed = 0.f, halfLength = 2.f;
	};

	void updatePed(Ped& p);
	void beginTransition(Ped& p);
	bool pickNextEdge(Ped& p, uint32_t node, uint32_t& outSegment, uint8_t& outSide, int8_t& outDir) const;
	void walkPoint(uint32_t segment, uint8_t side, float s, float jitter, float& x, float& y, float& z,
				   float& dirX, float& dirY) const;
	float segmentLength(uint32_t segment) const;
	float sidewalkOffset(uint32_t segment) const;
	/// Pedestrian signal for a crossing at `node` heading (dx, dy); Off when the node is not signalized.
	nycsim::traffic::PedSignal crossingSignal(uint32_t node, float dx, float dy) const;
	/// True when no vehicle will reach the crossing path within `horizonSeconds`.
	bool crossingGapSafe(float x0, float y0, float x1, float y1, float horizonSeconds) const;
	uint32_t allocatePed();
	void releasePed(uint32_t index);
	bool observerProtects(float x, float y) const;
	void spawnPhase();
	void despawnPhase();
	void assignAppearance(Ped& p, float x, float y);

	const RoadNetwork* network_ = nullptr;
	PedConfig config_;
	TrafficObserver observer_;
	PedStats stats_;

	std::vector<Ped> peds_;
	std::vector<uint32_t> freeList_;
	std::vector<uint32_t> activeOrder_;

	std::vector<VehicleProbe> vehicles_;
	nycsim::SpatialHash vehicleHash_;
	nycsim::SpatialHash pedHash_;

	std::vector<uint32_t> spawnSegments_;
	float spawnSegmentsX_ = 0.f, spawnSegmentsY_ = 0.f;
	bool spawnSegmentsValid_ = false;
	uint32_t targetPeds_ = 0;
	uint32_t sinceTargetRefresh_ = 0xFFFFFFFFu;
	std::vector<uint32_t> scratchLanes_;

	nycsim::Rng rng_;
	double simTime_ = 0.0;
	uint32_t nextId_ = 1;
	double stepMsAccum_ = 0.0;
};

}  // namespace nycsim_gameplay
