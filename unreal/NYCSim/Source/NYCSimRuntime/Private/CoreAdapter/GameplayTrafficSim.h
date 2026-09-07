// GameplayTrafficSim — the host-side traffic world the Unreal traffic subsystem steps at 20 Hz on a worker thread.
//
// Pure C++ (std + nycsim_core only, no Unreal headers) so it can be compiled and executed outside the editor;
// unreal/tools/gameplay_selftest.cpp does exactly that against a SyntheticGrid network.
//
// What comes from `core/` (authoritative, not re-implemented here):
//   * the lane graph, lane geometry, successors, turn types and yield sets  — nycsim::routing::RoadGraph
//   * the signal plans and their pure time functions                        — nycsim::traffic::SignalTable
//   * the fleet table (dimensions, IDM/MOBIL parameters, capabilities)      — nycsim::traffic::VehicleClass
//   * the IDM equations                                                     — nycsim::traffic::Idm
//   * the O/D density calibration                                           — nycsim::traffic::DensityTable
//   * the PRNG (bit-reproducible across platforms)                          — nycsim::Rng
//   * the uniform-grid spatial hash                                         — nycsim::SpatialHash
//
// What this file owns: the agent pool, the spawn/despawn ring around the observer, the per-step scheduling of the
// above, MOBIL lane changing, junction admission (signals, stop signs, yielding), bus route following with real
// stops, double parking on commercial frontage, and the reaction to the player's car. When
// `nycsim/traffic/World.h` lands in the core, `TrafficSim::step()` is the single function that delegates to it —
// nothing outside this file and GameplayPedSim.cpp knows how agents move.
#pragma once

#include <cstdint>
#include <string>
#include <vector>

#include "CoreAdapter/GameplayRoadNetwork.h"
#include "nycsim/traffic/Idm.h"
#include "nycsim/traffic/Random.h"
#include "nycsim/traffic/SpatialHash.h"
#include "nycsim/traffic/VehicleClass.h"

namespace nycsim_gameplay
{

/// Fleet metadata the Unreal side needs without including nycsim/traffic/VehicleClass.h itself.
/// `classIndex` is VehicleSnapshot::cls.
struct VehicleClassInfo
{
	const char* name = "sedan";   ///< stable id used for the asset name SK_<name>
	const char* body = "";        ///< the ADR-009 body the Blender vehicles agent produces
	float lengthM = 4.5f, widthM = 1.8f, heightM = 1.5f;
	bool isEmergency = false;
	bool isBus = false;
	bool isBike = false;
	bool isTruck = false;
	bool isTaxi = false;
};

/// Metadata for one fleet class (clamped to a valid class).
VehicleClassInfo vehicleClassInfo(uint8_t classIndex);
/// Number of fleet classes.
uint8_t vehicleClassCount();

/// Bits of VehicleSnapshot::flags — read by the pooled Unreal actor to drive lights, doors and sound.
enum : uint8_t
{
	kVehBrake = 1u << 0,
	kVehIndicatorLeft = 1u << 1,
	kVehIndicatorRight = 1u << 2,
	kVehHazard = 1u << 3,
	kVehSiren = 1u << 4,
	kVehDoorsOpen = 1u << 5,
	kVehReversing = 1u << 6,
	kVehHeadlights = 1u << 7,
};

/// One vehicle as the render side sees it. Plain data, copied wholesale between the double buffers.
struct VehicleSnapshot
{
	uint32_t id = 0;
	uint8_t cls = 0;        ///< nycsim::traffic::VehicleClass
	uint8_t flags = 0;
	uint16_t routeName = 0xFFFFu;  ///< index into TrafficSim::routeNames(); bus destination sign
	float x = 0.f, y = 0.f, z = 0.f;  ///< NYC_TM metres, at the ground under the rear-axle centre
	float headingRad = 0.f;  ///< mathematical (0 = +x east, counter-clockwise)
	float speedMps = 0.f;
	float accelMps2 = 0.f;
	float steerRad = 0.f;     ///< front wheel steer angle
	float wheelSpinRad = 0.f; ///< accumulated wheel rotation for wheel meshes
	float lengthM = 4.5f, widthM = 1.8f;
	uint8_t honking = 0;      ///< 0..255, decays; the audio side triggers a horn on the rising edge
};

/// A honk / collision / siren event raised during a step (drained by the host once per frame).
struct TrafficEvent
{
	enum class Kind : uint8_t
	{
		Honk = 0,
		HardBrake = 1,
		SirenOn = 2,
		SirenOff = 3,
	};
	Kind kind = Kind::Honk;
	uint32_t vehicle = 0;
	float x = 0.f, y = 0.f, z = 0.f;
	float intensity = 1.f;
};

struct TrafficConfig
{
	uint64_t seed = 20260906ull;
	float stepSeconds = 0.05f;      ///< 20 Hz (ARCHITECTURE §9)
	float spawnRadiusM = 420.f;     ///< agents appear on this ring
	float despawnRadiusM = 640.f;   ///< and are recycled past this one
	float protectRadiusM = 250.f;   ///< never create or destroy inside this radius of the observer (§9)
	float protectConeCos = 0.20f;   ///< ... nor anywhere inside a ±78° cone ahead within simRadius
	float simRadiusM = 620.f;
	uint32_t maxVehicles = 900;
	float vehicleDensityScale = 1.f;
	uint8_t hour = 8;
	uint8_t dow = 0;                ///< 0 weekday, 1 Saturday, 2 Sunday
	float wetness = 0.f;            ///< 0..1 from MPC_Weather: lowers desired speeds and lengthens headways
	float snowCover = 0.f;          ///< 0..1
	bool headlightsOn = false;      ///< driven by the sky subsystem (civil twilight) and by rain
	bool allowEmergency = true;
	/// Fallback vehicles per lane-km when density.nycb is missing (Midtown weekday peak ≈ 60).
	float fallbackVehPerKmLane = 22.f;
};

/// A pedestrian standing in the carriageway (crossing, jaywalking, stepping off the curb) that vehicles must not
/// drive through. Fed in by the host from the previous pedestrian step (one 50 ms lag, documented in the report).
struct PedObstacle
{
	float x = 0.f, y = 0.f;
};

/// Observer (the player's camera / car) that the spawn ring follows.
struct TrafficObserver
{
	float x = 0.f, y = 0.f, z = 0.f;
	float dirX = 1.f, dirY = 0.f;  ///< unit forward, NYC_TM
	float speedMps = 0.f;
	/// The player's own vehicle: AI agents brake for it and honk at it.
	bool playerVehicleValid = false;
	float playerX = 0.f, playerY = 0.f;
	float playerDirX = 1.f, playerDirY = 0.f;
	float playerSpeedMps = 0.f;
	float playerLengthM = 4.872f;
	float playerWidthM = 1.852f;
};

/// Counters the host prints with `nycsim.traffic.stats`.
struct TrafficStats
{
	uint32_t vehicles = 0;
	uint32_t spawnedTotal = 0;
	uint32_t despawnedTotal = 0;
	uint32_t spawnFailures = 0;
	uint32_t laneChanges = 0;
	uint32_t honks = 0;
	uint32_t stoppedAtSignals = 0;
	uint32_t doubleParked = 0;
	uint32_t busesDwelling = 0;
	/// Invariants checked by unreal/tools/gameplay_selftest.cpp.
	/// Entries into a junction lane whose group was red *without* having committed inside the yellow dilemma
	/// zone. Running the tail of a yellow is legal and modelled; entering a red from a standstill is a bug.
	uint32_t redLightEntries = 0;
	uint32_t dilemmaZoneEntries = 0;  ///< legal yellow-tail entries (diagnostic, not an error)
	uint32_t emergencyHolds = 0;      ///< reached a stop line that turned out to be blocked and braked hard
	float minLeaderGapM = 1.0e6f;  ///< smallest bumper-to-bumper gap observed in a lane — must stay >= 0
	uint64_t steps = 0;
	double lastStepMs = 0.0;
	double avgStepMs = 0.0;
};

class TrafficSim
{
public:
	TrafficSim();
	~TrafficSim();

	TrafficSim(const TrafficSim&) = delete;
	TrafficSim& operator=(const TrafficSim&) = delete;

	/// Binds the simulation to a loaded network. Fails when the network has no motor lanes.
	bool init(const RoadNetwork& network, const TrafficConfig& config, std::string& error);
	bool ready() const { return network_ != nullptr; }

	void setConfig(const TrafficConfig& config) { config_ = config; }
	const TrafficConfig& config() const { return config_; }
	void setObserver(const TrafficObserver& observer) { observer_ = observer; }

	/// Pedestrians currently in the roadway. Replaces the previous set; call once per step before step().
	void setPedObstacles(const std::vector<PedObstacle>& obstacles);

	/// One fixed step. `dt` is ignored except as a sanity bound: the model always advances config().stepSeconds
	/// so the simulation is reproducible for a given seed and observer path.
	void step();

	double simTime() const { return simTime_; }
	uint64_t stepCount() const { return stats_.steps; }
	const TrafficStats& stats() const { return stats_; }

	/// Copies the current agent set into `out` (cleared first). Called on the sim thread at the end of a step.
	void writeSnapshot(std::vector<VehicleSnapshot>& out) const;
	/// Moves the accumulated events out (clears the internal list).
	void drainEvents(std::vector<TrafficEvent>& out);

	/// Bus destination-sign strings, index-stable for the lifetime of the sim.
	const std::vector<std::string>& routeNames() const { return routeNames_; }

	/// Adds a bus route: `stops` are indices into the stop table built by addBusStop().
	/// Used by the host after loading transit.nycb; safe to call only before the first step().
	void addBusRoute(const std::string& name, const std::vector<uint32_t>& stops);
	uint32_t addBusStop(float x, float y, const std::string& name);
	uint32_t busStopCount() const { return static_cast<uint32_t>(busStops_.size()); }

private:
	struct Agent
	{
		uint32_t id = 0;
		nycsim::traffic::VehicleClass cls = nycsim::traffic::VehicleClass::Sedan;
		uint32_t lane = nycsim::routing::kInvalidIndex;
		float s = 0.f;          ///< metres along the lane
		float v = 0.f;          ///< m/s
		float accel = 0.f;
		float lateral = 0.f;    ///< metres left of the lane centre (lane change / double park)
		float lateralTarget = 0.f;
		float steer = 0.f;
		float wheelSpin = 0.f;
		float desiredSpeed = 11.176f;
		float honkCooldown = 0.f;
		float honk = 0.f;
		float dwellTimer = 0.f;      ///< bus stop dwell / double-park duration
		float sinceLaneChange = 0.f;
		float targetX = 0.f, targetY = 0.f;  ///< destination bias for turn choice
		uint32_t busRoute = 0xFFFFFFFFu;
		uint32_t busNextStop = 0;
		uint32_t plannedNext = nycsim::routing::kInvalidIndex;  ///< cached turn choice for the current lane
		float stopSignHeld = 0.f;   ///< seconds already spent stopped at a stop sign
		bool committed = false;     ///< passed the point of no return on a yellow; may finish on red
		uint8_t flags = 0;
		bool doubleParked = false;
		bool active = false;
		nycsim::Rng rng;
	};

	struct BusStop
	{
		float x = 0.f, y = 0.f;
		std::string name;
	};

	struct BusRoute
	{
		uint32_t nameIndex = 0xFFFFFFFFu;
		std::vector<uint32_t> stops;
	};

	// ---- per-step phases ------------------------------------------------------------------------------------
	void rebuildLaneBuckets();
	/// Final safety pass: clamps every agent so it can never occupy the same metre of lane as its leader.
	/// Runs after the advance/spawn phases and is what guarantees stats().minLeaderGapM >= 0.
	void resolveOverlaps();
	void updateAgent(Agent& a);
	void applyLaneChange(Agent& a);
	void advance(Agent& a);
	bool chooseNextLane(Agent& a, uint32_t& outLane) const;
	void spawnPhase();
	void despawnPhase();

	// ---- helpers --------------------------------------------------------------------------------------------
	/// Gap and closing speed to the leader on `a`'s lane (and, when close to the end, on its successor).
	bool findLeader(const Agent& a, float& gap, float& leadSpeed) const;
	/// Distance to the point where the agent must stop (red light, stop sign, blocked junction), or -1.
	float stopLineDistance(Agent& a) const;
	/// Distance to the player's car in `a`'s path (-1 when the player is not ahead in this lane).
	float playerObstacleDistance(const Agent& a, float& playerSpeed) const;
	/// Distance to the nearest pedestrian standing in `a`'s lane ahead (-1 when there is none).
	float pedObstacleDistance(const Agent& a) const;
	/// Junction admission: false while the agent must wait at the stop line.
	bool junctionClear(Agent& a, uint32_t junctionLane) const;
	/// True when `lane` has room for `a` at arc length `s` (no overlap with an agent already in it).
	bool laneEntryClear(const Agent& a, uint32_t lane, float s) const;
	nycsim::traffic::VehicleClass drawClass(uint32_t lane);
	float laneDesiredSpeed(const Agent& a, uint32_t lane) const;
	uint32_t allocateAgent();
	void releaseAgent(uint32_t index);
	bool observerProtects(float x, float y) const;
	void raise(TrafficEvent::Kind kind, const Agent& a, float intensity);
	const nycsim::traffic::VehicleClassParams& params(const Agent& a) const
	{
		return nycsim::traffic::classParams(a.cls);
	}

	const RoadNetwork* network_ = nullptr;
	TrafficConfig config_;
	TrafficObserver observer_;
	TrafficStats stats_;

	std::vector<Agent> agents_;
	std::vector<uint32_t> freeList_;
	std::vector<uint32_t> activeOrder_;  ///< active agent indices, ascending id (determinism)

	/// Agents bucketed by lane and sorted by s: laneAgents_[laneBucketStart_[lane] .. start_[lane+1]).
	std::vector<uint32_t> laneBucketStart_;
	std::vector<uint32_t> laneAgents_;

	/// Candidate spawn lanes near the observer, refreshed as the observer moves.
	std::vector<uint32_t> spawnLanes_;
	float spawnLanesX_ = 0.f, spawnLanesY_ = 0.f;
	bool spawnLanesValid_ = false;

	nycsim::SpatialHash hash_;
	nycsim::SpatialHash pedHash_;
	std::vector<PedObstacle> pedObstacles_;
	std::vector<TrafficEvent> events_;
	std::vector<BusStop> busStops_;
	std::vector<BusRoute> busRoutes_;
	std::vector<std::string> routeNames_;

	nycsim::Rng rng_;
	double simTime_ = 0.0;
	uint32_t nextId_ = 1;
	double stepMsAccum_ = 0.0;
	uint32_t targetVehicles_ = 0;
	uint32_t sinceTargetRefresh_ = 0xFFFFFFFFu;
	std::vector<uint32_t> scratchLanes_;
};

}  // namespace nycsim_gameplay
