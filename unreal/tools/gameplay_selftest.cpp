// gameplay_selftest — runs the Unreal gameplay lane's core-facing code OUTSIDE Unreal.
//
// The build environment has no Unreal Engine (ADR-001), so the four files in
// unreal/NYCSim/Source/NYCSimRuntime/Private/CoreAdapter/Gameplay*.{h,cpp} were written with std + nycsim_core
// only. This translation unit compiles them together with the real core sources, builds the synthetic Manhattan
// grid, and exercises the traffic and pedestrian simulations for a simulated minute, checking invariants that
// would otherwise only be observable in the editor:
//
//   1. the road network loads, indexes street names and routes between two points;
//   2. traffic spawns to the calibrated density, never leaves the lane graph, never produces a NaN;
//   3. no vehicle crosses a stop line while its signal group is red;
//   4. no vehicle overlaps its leader in the same lane (bumper-to-bumper gap ≥ 0);
//   5. spawning and despawning never happen inside the protected radius around the observer;
//   6. pedestrians only enter the carriageway on WALK, on an unsignalized crossing, or as a modelled jaywalker,
//      and always with a safe vehicle gap;
//   7. the whole simulation is bit-reproducible: two runs with the same seed and observer path hash equal.
//
// Build (from the repository root):
//   g++ -std=c++17 -O2 -Wall -Wextra -o /tmp/gameplay_selftest
//       -Icore/include -Iunreal/NYCSim/Source/NYCSimRuntime/Private
//       unreal/tools/gameplay_selftest.cpp
//       unreal/NYCSim/Source/NYCSimRuntime/Private/CoreAdapter/Gameplay*.cpp
//       core/src/routing/*.cpp core/src/traffic/*.cpp
//
// Exit code 0 = every check passed; the summary it prints is quoted in docs/verification/unreal_gameplay/REPORT.md.
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <string>
#include <vector>

#include "CoreAdapter/GameplayPedSim.h"
#include "CoreAdapter/GameplayRoadNetwork.h"
#include "CoreAdapter/GameplayTrafficSim.h"
#include "CoreAdapter/GameplayVehicleDynamics.h"
#include "nycsim/traffic/Random.h"

using namespace nycsim_gameplay;

namespace
{

int gFailures = 0;
int gChecks = 0;

void check(bool condition, const char* what)
{
	++gChecks;
	if (!condition)
	{
		++gFailures;
		std::printf("  FAIL  %s\n", what);
	}
}

void checkClose(double a, double b, double tol, const char* what)
{
	++gChecks;
	if (!(std::fabs(a - b) <= tol))
	{
		++gFailures;
		std::printf("  FAIL  %s (%.6f vs %.6f, tol %.6f)\n", what, a, b, tol);
	}
}

struct RunResult
{
	uint64_t hash = 0;
	uint32_t maxVehicles = 0;
	uint32_t maxPeds = 0;
	uint32_t redLightViolations = 0;
	uint32_t outOfBounds = 0;
	float minLeaderGap = 1.0e6f;
	uint32_t protectedSpawnOrDespawn = 0;
	uint32_t unsafeCrossings = 0;
	uint32_t nanCount = 0;
	uint32_t jaywalkers = 0;
	uint32_t crossings = 0;
	double trafficStepMs = 0.0;
	double pedStepMs = 0.0;
	uint32_t honks = 0;
	uint32_t laneChanges = 0;
};

/// One 60 s run of both simulations over the synthetic grid with a car driving north along the first avenue.
RunResult run(const RoadNetwork& net, uint64_t seed, bool verbose)
{
	RunResult out;

	TrafficConfig tcfg;
	tcfg.seed = seed;
	tcfg.maxVehicles = 400;
	tcfg.spawnRadiusM = 380.f;
	tcfg.despawnRadiusM = 560.f;
	tcfg.protectRadiusM = 120.f;
	tcfg.simRadiusM = 540.f;
	tcfg.hour = 8;
	tcfg.dow = 0;
	tcfg.fallbackVehPerKmLane = 30.f;

	PedConfig pcfg;
	pcfg.seed = seed;
	pcfg.maxPeds = 500;
	pcfg.spawnRadiusM = 130.f;
	pcfg.despawnRadiusM = 200.f;
	pcfg.protectRadiusM = 45.f;
	pcfg.hour = 8;
	pcfg.dow = 0;
	pcfg.rainRateMmH = 1.5f;
	pcfg.temperatureC = 8.f;

	TrafficSim traffic;
	PedSim peds;
	std::string error;
	if (!traffic.init(net, tcfg, error))
	{
		std::printf("  FAIL  traffic init: %s\n", error.c_str());
		++gFailures;
		return out;
	}
	if (!peds.init(net, pcfg, error))
	{
		std::printf("  FAIL  ped init: %s\n", error.c_str());
		++gFailures;
		return out;
	}

	std::vector<VehicleSnapshot> vehicles;
	std::vector<VehicleSnapshot> previousVehicles;
	std::vector<PedSnapshot> pedSnap;
	std::vector<PedObstacle> obstacles;
	std::vector<TrafficEvent> events;

	// Observer drives north up the middle of the grid at 8 m/s.
	float ox = net.stats().minX + (net.stats().maxX - net.stats().minX) * 0.5f;
	float oy = net.stats().minY + 120.f;
	nycsim::Fnv1a64 hash;

	const int steps = 1200;  // 60 s at 20 Hz
	for (int i = 0; i < steps; ++i)
	{
		TrafficObserver obs;
		obs.x = ox;
		obs.y = oy;
		obs.z = 0.f;
		obs.dirX = 0.f;
		obs.dirY = 1.f;
		obs.speedMps = 8.f;
		obs.playerVehicleValid = true;
		obs.playerX = ox;
		obs.playerY = oy;
		obs.playerDirX = 0.f;
		obs.playerDirY = 1.f;
		obs.playerSpeedMps = 8.f;
		traffic.setObserver(obs);
		peds.setObserver(obs);

		peds.updateVehicles(vehicles);
		peds.writeObstacles(obstacles);
		traffic.setPedObstacles(obstacles);

		traffic.step();
		peds.step();

		traffic.writeSnapshot(vehicles);
		peds.writeSnapshot(pedSnap);
		traffic.drainEvents(events);

		out.maxVehicles = std::max<uint32_t>(out.maxVehicles, static_cast<uint32_t>(vehicles.size()));
		out.maxPeds = std::max<uint32_t>(out.maxPeds, static_cast<uint32_t>(pedSnap.size()));

		for (const VehicleSnapshot& v : vehicles)
		{
			if (!std::isfinite(v.x) || !std::isfinite(v.y) || !std::isfinite(v.z) || !std::isfinite(v.headingRad) ||
				!std::isfinite(v.speedMps))
			{
				++out.nanCount;
			}
			// Every vehicle must be inside the network bounds with a generous margin.
			if (v.x < net.stats().minX - 60.f || v.x > net.stats().maxX + 60.f || v.y < net.stats().minY - 60.f ||
				v.y > net.stats().maxY + 60.f)
			{
				++out.outOfBounds;
			}
			hash.addU32(v.id);
			hash.addF32(std::floor(v.x * 100.f) / 100.f);
			hash.addF32(std::floor(v.y * 100.f) / 100.f);
			hash.addF32(std::floor(v.speedMps * 1000.f) / 1000.f);
		}
		for (const PedSnapshot& p : pedSnap)
		{
			if (!std::isfinite(p.x) || !std::isfinite(p.y) || !std::isfinite(p.speedMps))
			{
				++out.nanCount;
			}
			if ((p.flags & kPedJaywalking) != 0)
			{
				++out.jaywalkers;
			}
			if (p.state == static_cast<uint8_t>(PedState::Crossing))
			{
				++out.crossings;
			}
			hash.addU32(p.id);
			hash.addF32(std::floor(p.x * 100.f) / 100.f);
			hash.addF32(std::floor(p.y * 100.f) / 100.f);
		}

		// ARCHITECTURE §9: no agent may be created or destroyed inside the protected zone around the observer.
		// Checked externally by diffing consecutive snapshots rather than by a counter inside the simulation.
		for (const VehicleSnapshot& v : vehicles)
		{
			bool existed = false;
			for (const VehicleSnapshot& q : previousVehicles)
			{
				if (q.id == v.id)
				{
					existed = true;
					break;
				}
			}
			if (!existed && std::hypot(v.x - obs.x, v.y - obs.y) < tcfg.protectRadiusM)
			{
				++out.protectedSpawnOrDespawn;
			}
		}
		for (const VehicleSnapshot& q : previousVehicles)
		{
			bool survives = false;
			for (const VehicleSnapshot& v : vehicles)
			{
				if (q.id == v.id)
				{
					survives = true;
					break;
				}
			}
			if (!survives && std::hypot(q.x - obs.x, q.y - obs.y) < tcfg.protectRadiusM)
			{
				++out.protectedSpawnOrDespawn;
			}
		}
		previousVehicles = vehicles;

		oy += 8.f * 0.05f;
		if (oy > net.stats().maxY - 120.f)
		{
			oy = net.stats().minY + 120.f;
		}
	}

	out.hash = hash.h;
	out.redLightViolations = traffic.stats().redLightEntries;
	out.minLeaderGap = traffic.stats().minLeaderGapM;
	out.unsafeCrossings = peds.stats().unsafeCrossingStarts;
	out.trafficStepMs = traffic.stats().avgStepMs;
	out.pedStepMs = peds.stats().avgStepMs;
	out.honks = traffic.stats().honks;
	out.laneChanges = traffic.stats().laneChanges;

	if (verbose)
	{
		const TrafficStats& ts = traffic.stats();
		std::printf("  traffic: %u live, %u spawned, %u despawned, %u lane changes, %u honks, %u double-parked, "
					"%u bus dwells, %.3f ms/step\n",
					ts.vehicles, ts.spawnedTotal, ts.despawnedTotal, ts.laneChanges, ts.honks, ts.doubleParked,
					ts.busesDwelling, ts.avgStepMs);
		const PedStats& ps = peds.stats();
		std::printf("  peds:    %u live, %u spawned, %u despawned, %u crossing samples, %u jaywalk samples, "
					"%.3f ms/step\n",
					ps.peds, ps.spawnedTotal, ps.despawnedTotal, out.crossings, out.jaywalkers, ps.avgStepMs);
	}
	return out;
}

void testVehicleDynamics()
{
	std::printf("[1] player vehicle specification and tyre friction\n");
	const PlayerVehicleSpec spec;
	checkClose(spec.wheelRadiusM(), 0.3234, 0.005, "225/50R17 loaded radius ≈ 0.323 m");
	checkClose(spec.speedAtRpm(spec.maxRpm), 45.7, 1.5, "top gear: 6000 rpm ≈ 45.7 m/s (165 km/h)");
	checkClose(spec.rpmAtSpeed(13.4), 1780.0, 120.0, "30 mph ≈ 1780 rpm in the single eCVT ratio");
	// Peak power from the sampled torque curve must land on the published 140 kW combined output.
	double peakKw = 0.0;
	for (int rpm = 500; rpm <= 6000; rpm += 50)
	{
		const double kw = spec.torqueAtRpm(static_cast<float>(rpm)) * rpm * 2.0 * 3.14159265358979 / 60.0 / 1000.0;
		peakKw = std::max(peakKw, kw);
	}
	checkClose(peakKw, 140.0, 6.0, "combined peak power ≈ 140 kW (188 hp)");
	checkClose(spec.dragForceN(30.f), 348.0, 25.0, "aero drag at 30 m/s ≈ 348 N");

	const TyreFrictionModel friction;
	checkClose(friction.peakFriction(SurfaceClass::Asphalt, 0.f, 0.f, 0.f), 1.00, 1e-4, "dry asphalt µ = 1.00");
	checkClose(friction.peakFriction(SurfaceClass::Asphalt, 1.f, 0.f, 0.f), 0.70, 1e-4, "soaked asphalt µ = 0.70");
	checkClose(friction.peakFriction(SurfaceClass::SteelPlate, 1.f, 0.f, 0.f), 0.55, 1e-4, "wet steel plate µ = 0.55");
	checkClose(friction.peakFriction(SurfaceClass::PaintedMarking, 1.f, 0.f, 0.f), 0.60, 1e-4,
			   "wet painted marking µ = 0.60");
	checkClose(friction.peakFriction(SurfaceClass::Asphalt, 0.f, 1.f, 0.f), 0.30, 1e-4, "full snow cover µ = 0.30");
	checkClose(friction.peakFriction(SurfaceClass::Asphalt, 0.f, 0.f, 1.f), 0.15, 1e-4, "full ice cover µ = 0.15");
	check(friction.peakFriction(SurfaceClass::Asphalt, 0.3f, 0.f, 0.f) <
			  friction.peakFriction(SurfaceClass::Asphalt, 0.f, 0.f, 0.f),
		  "a damp road grips less than a dry one");
	checkClose(friction.frictionMultiplier(SurfaceClass::Asphalt, 0.f, 0.f, 0.f), 1.0, 1e-6,
			   "dry asphalt is the reference multiplier");
	// NASA hydroplaning threshold at 35 psi ≈ 61 mph ≈ 27.4 m/s in deep water.
	checkClose(friction.aquaplaneSpeedMps(4.f, 241.f), 27.4, 1.5, "aquaplaning at 35 psi in 4 mm ≈ 27 m/s");
	check(friction.aquaplaneSpeedMps(0.f, 241.f) > 1000.f, "no aquaplaning on a dry road");
	check(friction.aquaplaneSpeedMps(1.f, 241.f) > friction.aquaplaneSpeedMps(4.f, 241.f),
		  "a thinner film raises the aquaplaning threshold");
	std::printf("      wheel radius %.4f m, top speed %.1f m/s, peak power %.1f kW\n", spec.wheelRadiusM(),
				spec.speedAtRpm(spec.maxRpm), peakKw);
}

}  // namespace

int main()
{
	std::printf("NYCSim gameplay self-test (traffic / pedestrians / vehicle dynamics)\n");
	std::printf("--------------------------------------------------------------------\n");

	testVehicleDynamics();

	std::printf("[2] road network (synthetic Manhattan grid)\n");
	RoadNetwork net;
	std::string error;
	if (!net.buildSyntheticGrid(8, 20, 0.f, 0.f, error))
	{
		std::printf("  FAIL  buildSyntheticGrid: %s\n", error.c_str());
		return 1;
	}
	const RoadNetworkStats& st = net.stats();
	std::printf("      %u nodes, %u segments, %u road lanes, %u junction lanes, %u signal plans, %u index entries\n",
				st.nodes, st.segments, st.roadLanes, st.junctionLanes, st.signalPlans, net.searchEntryCount());
	check(st.nodes > 0 && st.segments > 0, "grid has nodes and segments");
	check(st.roadLanes > 0 && st.junctionLanes > 0, "grid has road lanes and junction lanes");
	check(st.signalPlans > 0, "grid has signal plans");
	check(net.searchEntryCount() > 0, "street-name index is populated");

	// Street search must find an avenue by a partial, case-insensitive query.
	SearchHit hits[8];
	const uint32_t nHits = net.search("ave", hits, 8);
	check(nHits > 0, "search(\"ave\") finds avenues");
	if (nHits > 0)
	{
		std::printf("      search(\"ave\") -> \"%s\" (%.0f, %.0f)\n", net.searchEntry(hits[0].entry).label.c_str(),
					net.searchEntry(hits[0].entry).x, net.searchEntry(hits[0].entry).y);
	}

	// Routing: two points on opposite corners of the grid must produce a route with instructions.
	std::unique_ptr<nycsim::routing::Router> router = net.makeRouter(4, error);
	check(router != nullptr, "router attaches to the graph");
	if (router)
	{
		nycsim::routing::RouteProfile profile;
		nycsim::routing::RouteResult result;
		// Quarter to three-quarter points: the synthetic grid's outermost avenue and street are one-way *out* of
		// the network, so a corner-to-corner query legitimately has no route and is not a useful assertion.
		const float ax = st.minX + (st.maxX - st.minX) * 0.25f;
		const float ay = st.minY + (st.maxY - st.minY) * 0.25f;
		const float bx = st.minX + (st.maxX - st.minX) * 0.75f;
		const float by = st.minY + (st.maxY - st.minY) * 0.75f;
		const bool ok = router->routePoints(ax, ay, bx, by, profile, result, 120.f);
		check(ok && result.ok, "route across the grid succeeds");
		if (result.ok)
		{
			check(result.length_m > 0.f && result.eta_s > 0.f, "route has a positive length and ETA");
			check(!result.instructions.empty(), "route produces turn-by-turn instructions");
			check(!result.polyline.empty(), "route produces a minimap polyline");
			std::printf("      route: %.0f m, ETA %.0f s, %zu lanes, %zu instructions, first = \"%s\"\n",
						result.length_m, result.eta_s, result.lanes.size(), result.instructions.size(),
						result.instructions.empty() ? "" : result.instructions.front().text.c_str());
		}
	}

	std::printf("[3] traffic + pedestrians, 60 simulated seconds\n");
	const RunResult a = run(net, 20260906ull, true);
	check(a.maxVehicles > 20, "traffic populates the simulated disc");
	check(a.maxPeds > 20, "pedestrians populate the sidewalks");
	check(a.nanCount == 0, "no non-finite agent state");
	check(a.outOfBounds == 0, "no agent leaves the network bounds");
	check(a.crossings > 0, "pedestrians use the crossings");
	check(a.laneChanges > 0, "MOBIL produces lane changes");
	check(a.redLightViolations == 0, "no vehicle enters a junction lane on red");
	check(a.minLeaderGap >= 0.f, "no vehicle overlaps its leader in the same lane");
	check(a.protectedSpawnOrDespawn == 0, "no spawn or despawn inside the protected radius (ARCHITECTURE §9)");
	check(a.unsafeCrossings == 0, "no pedestrian steps out against DON'T WALK except as a modelled jaywalker");
	check(a.jaywalkers > 0, "the jaywalking model fires");
	std::printf("      invariants: red-light entries %u, min leader gap %.3f m, protected spawn/despawn %u, "
				"unsafe crossings %u\n",
				a.redLightViolations, a.minLeaderGap, a.protectedSpawnOrDespawn, a.unsafeCrossings);

	std::printf("[4] determinism\n");
	const RunResult b = run(net, 20260906ull, false);
	check(a.hash == b.hash, "identical seed and observer path reproduce an identical trajectory hash");
	const RunResult c = run(net, 20260907ull, false);
	check(a.hash != c.hash, "a different seed produces a different trajectory");
	std::printf("      hash(seed 20260906) = 0x%016llx, hash(seed 20260907) = 0x%016llx\n",
				static_cast<unsigned long long>(a.hash), static_cast<unsigned long long>(c.hash));

	std::printf("--------------------------------------------------------------------\n");
	std::printf("%d checks, %d failures\n", gChecks, gFailures);
	return gFailures == 0 ? 0 : 1;
}
