// GameplayRoadNetwork — the single place where the gameplay lane (traffic, pedestrians, GPS, minimap) touches
// nycsim_core's routing/traffic headers.
//
// Rationale (unreal/COMPILE_CHECKLIST_GAMEPLAY.md §"core isolation"): `core/` is written concurrently by other
// agents, so every use of `nycsim::routing` / `nycsim::traffic` lives in Private/CoreAdapter/Gameplay*.{h,cpp}.
// Those files contain **no Unreal headers at all** (std + core only), which has two consequences:
//   * API drift in the core is a compile error in four files, not across the runtime module;
//   * the files can be compiled and executed outside Unreal — see unreal/tools/gameplay_selftest.cpp, which is what
//     verifies this code in an environment without UE.
//
// Coordinates here are NYC_TM metres (east, north, up), exactly as the core uses them. Conversion to Unreal
// centimetres happens in the UE-facing wrappers (NYCGeo).
#pragma once

#include <cstdint>
#include <memory>
#include <string>
#include <vector>

#include "nycsim/routing/RoadGraph.h"
#include "nycsim/routing/Router.h"
#include "nycsim/traffic/Density.h"
#include "nycsim/traffic/Signals.h"

namespace nycsim_gameplay
{

namespace routing = nycsim::routing;
namespace traffic = nycsim::traffic;

/// One entry of the GPS destination index (address, street, bus stop, landmark).
struct SearchEntry
{
	enum class Kind : uint8_t
	{
		Address = 0,   ///< runtime/pois.nycb — PLUTO/PAD address point
		Street = 1,    ///< a street name from the road graph (centroid of its segments)
		BusStop = 2,   ///< runtime/transit.nycb bus stop
		Landmark = 3,  ///< runtime/landmarks.nycb (optional file, see loadLandmarks())
	};

	std::string label;   ///< display text, e.g. "350 5 Ave" or "Grand Central Terminal"
	std::string folded;  ///< lower-case, punctuation-stripped, single-spaced form used for matching
	float x = 0.f;       ///< NYC_TM east, metres
	float y = 0.f;       ///< NYC_TM north, metres
	Kind kind = Kind::Address;
};

/// A scored search result (the index is immutable; results reference entries by index).
struct SearchHit
{
	uint32_t entry = 0xFFFFFFFFu;
	float score = 0.f;  ///< higher is better; prefix matches outrank substring matches
};

/// Statistics filled by load(); reported by the traffic subsystem's console command.
struct RoadNetworkStats
{
	uint32_t nodes = 0;
	uint32_t segments = 0;
	uint32_t roadLanes = 0;
	uint32_t junctionLanes = 0;
	uint32_t signalPlans = 0;
	uint32_t defaultSignalPlans = 0;
	uint32_t ntaCells = 0;
	uint32_t addresses = 0;
	uint32_t busStops = 0;
	uint32_t landmarks = 0;
	uint32_t lanesWithNta = 0;
	double loadSeconds = 0.0;
	float minX = 0.f, minY = 0.f, maxX = 0.f, maxY = 0.f;
};

/// Immutable-after-load road network: graph + signal plans + density table + destination index.
///
/// Thread-safety: after load() returns true nothing mutates, so the graph, signals and density table may be read
/// from any number of threads. Routers are *not* shared — call makeRouter() once per thread that routes.
class RoadNetwork
{
public:
	RoadNetwork();
	~RoadNetwork();

	RoadNetwork(const RoadNetwork&) = delete;
	RoadNetwork& operator=(const RoadNetwork&) = delete;

	/// Reads a whole file into `out`. Returning false must leave a reason in `error`; a *missing* file must set
	/// `error` to the exact text kMissingFile so the loader can treat optional files as absent rather than broken.
	using FileReader = bool (*)(void* context, const std::string& path, std::vector<uint8_t>& out, std::string& error);
	static const char* const kMissingFile;

	/// Loads runtime/{roadgraph,signals,density,pois,transit,landmarks}.nycb from `runtimeDir`.
	/// roadgraph.nycb is mandatory; every other file is optional and its absence is recorded as a note (the call
	/// still returns true). Returns false only when the network is unusable.
	///
	/// `reader` defaults to a std::ifstream reader (used by the standalone self-test); the Unreal subsystem passes
	/// a reader backed by FFileHelper so packaged builds read through the engine's platform file layer.
	bool load(const std::string& runtimeDir, std::string& error, FileReader reader = nullptr, void* context = nullptr);

	bool loaded() const { return loaded_; }
	const RoadNetworkStats& stats() const { return stats_; }
	/// Non-fatal notes accumulated by load() (missing optional files, unbound signal nodes, ...).
	const std::vector<std::string>& notes() const { return notes_; }

	const routing::RoadGraph& graph() const { return graph_; }
	const traffic::SignalTable& signals() const { return signals_; }
	const traffic::DensityTable& density() const { return density_; }

	/// A router attached to this graph. `landmarks == 0` selects plain bidirectional Dijkstra (no preprocessing,
	/// used by the traffic AI whose queries are short); the GPS uses 8 landmarks (ALT) for city-wide routes.
	/// Returns nullptr when the network is not loaded or attach() failed (reason in `error`).
	std::unique_ptr<routing::Router> makeRouter(uint32_t landmarks, std::string& error) const;

	// ---- destination index ---------------------------------------------------------------------------------
	uint32_t searchEntryCount() const { return static_cast<uint32_t>(entries_.size()); }
	const SearchEntry& searchEntry(uint32_t i) const { return entries_[i]; }
	/// Ranked lookup. Writes at most `cap` hits, returns the number written. Empty query → 0 hits.
	uint32_t search(const std::string& query, SearchHit* out, uint32_t cap) const;
	/// Nearest indexed entry to a point (any kind), or 0xFFFFFFFF when the index is empty.
	uint32_t nearestEntry(float x, float y, float maxDistanceM) const;

	// ---- helpers used by GPS / traffic / peds --------------------------------------------------------------
	/// Street name of a lane ("" when the lane has none). Junction lanes report the street they lead onto.
	std::string laneStreetName(uint32_t lane) const;
	/// Signal state of a junction lane at absolute simulation time `t` (Off when it is not signal-controlled).
	traffic::VehSignal junctionSignal(uint32_t junctionLane, double t) const;
	/// Pedestrian signal parallel to a junction lane's group (Off when unknown).
	traffic::PedSignal pedSignal(uint32_t junctionLane, double t) const;
	/// Seconds until that junction lane's group turns green (0 when it is green now, -1 when uncontrolled).
	float timeToGreen(uint32_t junctionLane, double t) const;
	/// Density cell for a lane at (hour, dow); returns the zero cell when the lane has no NTA.
	const traffic::DensityCell& densityForLane(uint32_t lane, uint8_t hour, uint8_t dow) const;

	/// Case/punctuation-insensitive fold used by the index and by search().
	static std::string fold(const std::string& s);

private:
	bool loadFile(const std::string& path, std::vector<uint8_t>& out, std::string& error) const;
	void buildStreetIndex();
	bool loadPois(const std::vector<uint8_t>& bytes);
	bool loadTransit(const std::vector<uint8_t>& bytes);
	bool loadLandmarks(const std::vector<uint8_t>& bytes);
	void addEntry(std::string label, float x, float y, SearchEntry::Kind kind);
	void finishIndex();

	FileReader reader_ = nullptr;
	void* readerContext_ = nullptr;

	routing::RoadGraph graph_;
	traffic::SignalTable signals_;
	traffic::DensityTable density_;
	std::vector<SearchEntry> entries_;
	/// Sorted by `folded` so prefix queries are a binary-search range.
	std::vector<uint32_t> order_;
	/// Uniform grid over the index for nearestEntry(); cell size 250 m.
	std::vector<uint32_t> gridStart_;
	std::vector<uint32_t> gridItems_;
	float gridMinX_ = 0.f, gridMinY_ = 0.f;
	uint32_t gridNx_ = 1, gridNy_ = 1;
	static constexpr float kGridCell = 250.f;

	RoadNetworkStats stats_;
	std::vector<std::string> notes_;
	bool loaded_ = false;
};

}  // namespace nycsim_gameplay
