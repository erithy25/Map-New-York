#include "CoreAdapter/GameplayTrafficSim.h"

#include <algorithm>
#include <chrono>
#include <cmath>

namespace nycsim_gameplay
{

using nycsim::Rng;
using nycsim::routing::Control;
using nycsim::routing::kInvalidIndex;
using nycsim::routing::Lane;
using nycsim::routing::LaneKind;
using nycsim::routing::LanePose;
using nycsim::routing::RwType;
using nycsim::routing::Segment;
using nycsim::routing::TurnType;
using nycsim::traffic::classParams;
using nycsim::traffic::IdmParams;
using nycsim::traffic::VehicleClass;
using nycsim::traffic::VehicleClassParams;
using nycsim::traffic::VehSignal;

namespace
{

constexpr float kBigDistance = 1.0e6f;
/// NYC "blocking the box" is illegal and common. Calibrated share of drivers who enter an intersection whose exit
/// is already occupied (DOT Don't Block the Box enforcement data; see the stage report §Calibration).
constexpr float kBlockTheBoxProbability = 0.12f;
/// Minimum seconds an agent holds at a stop sign before it may proceed.
constexpr float kStopSignHold = 1.4f;
/// Yield gap accepted when crossing or turning across a conflicting movement.
constexpr float kYieldGapSeconds = 4.0f;

float wheelRadiusForLength(float lengthM)
{
	// Passenger cars 0.32 m, buses/fire apparatus 0.55 m; linear in overall length, clamped.
	const float r = 0.30f + 0.024f * (lengthM - 4.5f);
	return std::clamp(r, 0.26f, 0.55f);
}

IdmParams idmFor(const VehicleClassParams& p, float desiredSpeed, float wetness, float snow)
{
	IdmParams idm;
	idm.a = p.max_accel;
	idm.b = p.comfort_decel;
	idm.b_max = p.max_decel;
	// Rain and snow lengthen headways: +30 % wet, +90 % snow (Highway Capacity Manual weather adjustment).
	idm.T = p.headway_T * (1.f + 0.30f * wetness + 0.90f * snow);
	idm.s0 = p.min_gap_s0;
	idm.v0 = desiredSpeed;
	return idm;
}

float angleBetween(float ax, float ay, float bx, float by)
{
	const float la = std::sqrt(ax * ax + ay * ay);
	const float lb = std::sqrt(bx * bx + by * by);
	if (la < 1e-6f || lb < 1e-6f)
	{
		return 0.f;
	}
	const float c = std::clamp((ax * bx + ay * by) / (la * lb), -1.f, 1.f);
	return std::acos(c);
}

}  // namespace

TrafficSim::TrafficSim() = default;
TrafficSim::~TrafficSim() = default;

bool TrafficSim::init(const RoadNetwork& network, const TrafficConfig& config, std::string& error)
{
	error.clear();
	network_ = nullptr;
	config_ = config;
	agents_.clear();
	freeList_.clear();
	activeOrder_.clear();
	events_.clear();
	simTime_ = 0.0;
	stats_ = TrafficStats();
	nextId_ = 1;
	spawnLanesValid_ = false;
	sinceTargetRefresh_ = 0xFFFFFFFFu;

	if (!network.loaded())
	{
		error = "traffic: road network not loaded";
		return false;
	}
	const auto& g = network.graph();
	if (g.roadLaneCount() == 0)
	{
		error = "traffic: road network has no road lanes";
		return false;
	}

	bool anyMotor = false;
	for (uint32_t i = 0; i < g.roadLaneCount(); ++i)
	{
		if (g.laneAllows(i, nycsim::routing::kMotorLaneKinds))
		{
			anyMotor = true;
			break;
		}
	}
	if (!anyMotor)
	{
		error = "traffic: road network has no drivable (travel/turn) lanes";
		return false;
	}

	network_ = &network;
	rng_.reseed(config_.seed);

	agents_.resize(config_.maxVehicles);
	freeList_.resize(config_.maxVehicles);
	for (uint32_t i = 0; i < config_.maxVehicles; ++i)
	{
		// Free list is consumed from the back, so hand out low indices first (stable actor mapping).
		freeList_[i] = config_.maxVehicles - 1 - i;
	}

	float minx = 0.f, miny = 0.f, maxx = 0.f, maxy = 0.f;
	g.bounds(minx, miny, maxx, maxy);
	hash_.configure(minx, miny, maxx, maxy, 40.f, config_.maxVehicles);
	// The pedestrian obstacle grid only ever holds the peds inside the simulated disc.
	pedHash_.configure(minx, miny, maxx, maxy, 20.f, 4096);
	pedObstacles_.clear();

	laneBucketStart_.assign(g.laneCount() + 1, 0u);
	laneAgents_.clear();
	laneAgents_.reserve(config_.maxVehicles);
	return true;
}

uint32_t TrafficSim::addBusStop(float x, float y, const std::string& name)
{
	BusStop s;
	s.x = x;
	s.y = y;
	s.name = name;
	busStops_.push_back(std::move(s));
	return static_cast<uint32_t>(busStops_.size() - 1);
}

void TrafficSim::addBusRoute(const std::string& name, const std::vector<uint32_t>& stops)
{
	if (stops.size() < 2)
	{
		return;
	}
	BusRoute r;
	r.nameIndex = static_cast<uint32_t>(routeNames_.size());
	routeNames_.push_back(name);
	r.stops.reserve(stops.size());
	for (const uint32_t s : stops)
	{
		if (s < busStops_.size())
		{
			r.stops.push_back(s);
		}
	}
	if (r.stops.size() >= 2)
	{
		busRoutes_.push_back(std::move(r));
	}
	else
	{
		routeNames_.pop_back();
	}
}

uint32_t TrafficSim::allocateAgent()
{
	if (freeList_.empty())
	{
		return kInvalidIndex;
	}
	const uint32_t idx = freeList_.back();
	freeList_.pop_back();
	agents_[idx] = Agent();
	agents_[idx].active = true;
	agents_[idx].id = nextId_++;
	return idx;
}

void TrafficSim::releaseAgent(uint32_t index)
{
	if (index >= agents_.size() || !agents_[index].active)
	{
		return;
	}
	agents_[index].active = false;
	agents_[index].lane = kInvalidIndex;
	freeList_.push_back(index);
}

bool TrafficSim::observerProtects(float x, float y) const
{
	const float dx = x - observer_.x;
	const float dy = y - observer_.y;
	const float d2 = dx * dx + dy * dy;
	if (d2 <= config_.protectRadiusM * config_.protectRadiusM)
	{
		return true;
	}
	if (d2 > config_.simRadiusM * config_.simRadiusM)
	{
		return false;
	}
	const float d = std::sqrt(d2);
	if (d < 1e-3f)
	{
		return true;
	}
	const float dot = (dx * observer_.dirX + dy * observer_.dirY) / d;
	return dot >= config_.protectConeCos;
}

void TrafficSim::raise(TrafficEvent::Kind kind, const Agent& a, float intensity)
{
	if (events_.size() >= 256)
	{
		return;
	}
	const LanePose pose = network_->graph().poseAt(a.lane, a.s, a.lateral);
	TrafficEvent e;
	e.kind = kind;
	e.vehicle = a.id;
	e.x = pose.pos.x;
	e.y = pose.pos.y;
	e.z = pose.pos.z;
	e.intensity = intensity;
	events_.push_back(e);
}

void TrafficSim::drainEvents(std::vector<TrafficEvent>& out)
{
	out.clear();
	out.swap(events_);
}

// --------------------------------------------------------------------------------------------- per-step phases

void TrafficSim::rebuildLaneBuckets()
{
	const auto& g = network_->graph();
	const size_t laneCount = g.laneCount();
	laneBucketStart_.assign(laneCount + 1, 0u);
	activeOrder_.clear();

	for (uint32_t i = 0; i < agents_.size(); ++i)
	{
		const Agent& a = agents_[i];
		if (!a.active || a.lane >= laneCount)
		{
			continue;
		}
		activeOrder_.push_back(i);
		++laneBucketStart_[a.lane + 1];
	}
	for (size_t l = 0; l < laneCount; ++l)
	{
		laneBucketStart_[l + 1] += laneBucketStart_[l];
	}
	laneAgents_.assign(activeOrder_.size(), 0u);
	std::vector<uint32_t> cursor(laneBucketStart_.begin(), laneBucketStart_.end() - 1);
	for (const uint32_t i : activeOrder_)
	{
		laneAgents_[cursor[agents_[i].lane]++] = i;
	}
	// Sort each bucket by s so leader lookup is the next element.
	for (size_t l = 0; l < laneCount; ++l)
	{
		const uint32_t b = laneBucketStart_[l];
		const uint32_t e = laneBucketStart_[l + 1];
		if (e - b > 1)
		{
			std::sort(laneAgents_.begin() + b, laneAgents_.begin() + e,
					  [this](uint32_t x, uint32_t y) { return agents_[x].s < agents_[y].s; });
		}
	}

	hash_.begin();
	for (const uint32_t i : activeOrder_)
	{
		const Agent& a = agents_[i];
		const LanePose pose = g.poseAt(a.lane, a.s, a.lateral);
		hash_.insert(i, pose.pos.x, pose.pos.y);
	}
	hash_.end();
	stats_.vehicles = static_cast<uint32_t>(activeOrder_.size());
}

bool TrafficSim::findLeader(const Agent& a, float& gap, float& leadSpeed) const
{
	const auto& g = network_->graph();
	gap = kBigDistance;
	leadSpeed = 0.f;
	bool found = false;

	const float halfSelf = params(a).length_m * 0.5f;

	const uint32_t b = laneBucketStart_[a.lane];
	const uint32_t e = laneBucketStart_[a.lane + 1];
	for (uint32_t k = b; k < e; ++k)
	{
		const Agent& o = agents_[laneAgents_[k]];
		if (o.id == a.id || o.s <= a.s)
		{
			continue;
		}
		// Buckets are sorted, so the first agent ahead is the leader.
		const float halfOther = classParams(o.cls).length_m * 0.5f;
		gap = (o.s - a.s) - halfSelf - halfOther;
		leadSpeed = o.doubleParked ? 0.f : o.v;
		found = true;
		break;
	}

	// Look into the lane the agent will enter, so it does not accelerate into a queue across the junction.
	const float toEnd = g.lane(a.lane).length_m - a.s;
	if (!found && toEnd < 55.f && a.plannedNext != kInvalidIndex && a.plannedNext < g.laneCount())
	{
		const uint32_t nb = laneBucketStart_[a.plannedNext];
		const uint32_t ne = laneBucketStart_[a.plannedNext + 1];
		float best = kBigDistance;
		for (uint32_t k = nb; k < ne; ++k)
		{
			const Agent& o = agents_[laneAgents_[k]];
			const float halfOther = classParams(o.cls).length_m * 0.5f;
			const float d = toEnd + o.s - halfSelf - halfOther;
			if (d < best)
			{
				best = d;
				leadSpeed = o.doubleParked ? 0.f : o.v;
			}
		}
		if (best < kBigDistance)
		{
			gap = best;
			found = true;
		}
	}
	return found;
}

float TrafficSim::playerObstacleDistance(const Agent& a, float& playerSpeed) const
{
	playerSpeed = 0.f;
	if (!observer_.playerVehicleValid)
	{
		return -1.f;
	}
	const auto& g = network_->graph();
	float s = 0.f, lateral = 0.f, dist = 0.f;
	if (!g.projectOnLane(a.lane, observer_.playerX, observer_.playerY, s, lateral, dist, 6.f))
	{
		return -1.f;
	}
	const float laneHalfWidth = g.lane(a.lane).width_m * 0.5f + observer_.playerWidthM * 0.5f;
	if (std::fabs(lateral - a.lateral) > laneHalfWidth)
	{
		return -1.f;
	}
	const float gap = (s - a.s) - params(a).length_m * 0.5f - observer_.playerLengthM * 0.5f;
	if (gap < -2.f || gap > 90.f)
	{
		return -1.f;
	}
	// The player's speed along this lane (a car crossing sideways contributes almost nothing longitudinally).
	const LanePose pose = g.poseAt(a.lane, std::max(0.f, s));
	playerSpeed = observer_.playerSpeedMps * (observer_.playerDirX * pose.dir.x + observer_.playerDirY * pose.dir.y);
	return std::max(0.f, gap);
}

void TrafficSim::setPedObstacles(const std::vector<PedObstacle>& obstacles)
{
	pedObstacles_ = obstacles;
	pedHash_.begin();
	const uint32_t n = std::min<uint32_t>(static_cast<uint32_t>(pedObstacles_.size()), pedHash_.capacity());
	for (uint32_t i = 0; i < n; ++i)
	{
		pedHash_.insert(i, pedObstacles_[i].x, pedObstacles_[i].y);
	}
	pedHash_.end();
}

float TrafficSim::pedObstacleDistance(const Agent& a) const
{
	if (pedObstacles_.empty())
	{
		return -1.f;
	}
	const auto& g = network_->graph();
	const LanePose here = g.poseAt(a.lane, a.s, a.lateral);
	// Look one comfortable stopping distance ahead, at least 12 m.
	const float look = std::max(12.f, nycsim::traffic::stoppingDistance(a.v, params(a).comfort_decel, 0.8f));
	const float cx = here.pos.x + here.dir.x * look * 0.5f;
	const float cy = here.pos.y + here.dir.y * look * 0.5f;

	float best = -1.f;
	const float halfWidth = g.lane(a.lane).width_m * 0.5f + 0.45f;  // ped shoulder half-width
	pedHash_.query(cx, cy, look * 0.5f + 6.f, [&](uint32_t idx) {
		if (idx >= pedObstacles_.size())
		{
			return;
		}
		const PedObstacle& ped = pedObstacles_[idx];
		float s = 0.f, lateral = 0.f, dist = 0.f;
		if (!g.projectOnLane(a.lane, ped.x, ped.y, s, lateral, dist, halfWidth + 1.f))
		{
			return;
		}
		if (std::fabs(lateral - a.lateral) > halfWidth)
		{
			return;
		}
		const float gap = (s - a.s) - params(a).length_m * 0.5f - 0.35f;
		if (gap < -1.f || gap > look)
		{
			return;
		}
		const float clamped = std::max(0.f, gap);
		if (best < 0.f || clamped < best)
		{
			best = clamped;
		}
	});
	return best;
}

bool TrafficSim::junctionClear(const Agent& a, uint32_t junctionLane) const
{
	const auto& g = network_->graph();
	if (junctionLane >= g.laneCount())
	{
		return false;
	}
	const Lane& jl = g.lane(junctionLane);
	if (jl.disabled != 0)
	{
		return false;
	}

	// 1. Signal.
	const VehSignal signal = network_->junctionSignal(junctionLane, simTime_);
	const float toEnd = g.lane(a.lane).length_m - a.s;
	if (signal == VehSignal::Red)
	{
		return false;
	}
	if (signal == VehSignal::Yellow)
	{
		// Decision zone: stop when it can be done comfortably, otherwise clear the intersection.
		const float needed = nycsim::traffic::stoppingDistance(a.v, params(a).comfort_decel, 1.0f);
		if (needed < toEnd)
		{
			return false;
		}
	}

	// 2. Stop / all-way stop control at the node.
	if (signal == VehSignal::Off && jl.node != kInvalidIndex)
	{
		const Control control = g.node(jl.node).control;
		if (control == Control::Stop || control == Control::AllWayStop)
		{
			if (a.stopSignHeld < kStopSignHold)
			{
				return false;
			}
		}
	}

	// 3. Yield set: conflicting movements that have priority (unprotected left, right on green, yield sign).
	uint32_t nYield = 0;
	const uint32_t* yields = g.yieldTo(junctionLane, nYield);
	for (uint32_t i = 0; i < nYield; ++i)
	{
		const uint32_t y = yields[i];
		if (y >= g.laneCount())
		{
			continue;
		}
		const uint32_t b = laneBucketStart_[y];
		const uint32_t e = laneBucketStart_[y + 1];
		const float yLen = g.lane(y).length_m;
		for (uint32_t k = b; k < e; ++k)
		{
			const Agent& o = agents_[laneAgents_[k]];
			if (o.doubleParked)
			{
				continue;
			}
			const float remaining = std::max(0.f, yLen - o.s);
			const float ttc = o.v > 0.5f ? remaining / o.v : (remaining < 6.f ? 0.f : kBigDistance);
			if (ttc < kYieldGapSeconds)
			{
				return false;
			}
		}
	}

	// 4. Don't block the box: refuse to enter when the exit lane's first vehicle lengths are occupied.
	const uint32_t exitLane = jl.to_lane;
	if (exitLane != kInvalidIndex && exitLane < g.laneCount())
	{
		const float needed = params(a).length_m + params(a).min_gap_s0;
		const uint32_t b = laneBucketStart_[exitLane];
		const uint32_t e = laneBucketStart_[exitLane + 1];
		for (uint32_t k = b; k < e; ++k)
		{
			const Agent& o = agents_[laneAgents_[k]];
			if (o.s < needed && o.v < 1.5f)
			{
				// Law-abiding drivers wait; the calibrated remainder blocks the box.
				Rng probe = a.rng;
				return probe.chance(kBlockTheBoxProbability);
			}
			break;  // buckets are sorted by s
		}
	}
	return true;
}

float TrafficSim::stopLineDistance(const Agent& a) const
{
	const auto& g = network_->graph();
	const Lane& lane = g.lane(a.lane);
	if (lane.is_junction != 0)
	{
		return -1.f;  // already inside the intersection: commit
	}
	if (a.plannedNext == kInvalidIndex)
	{
		// No successor at all: the lane ends (dead end / map edge). Stop at the end.
		return std::max(0.f, lane.length_m - a.s);
	}
	if (junctionClear(a, a.plannedNext))
	{
		return -1.f;
	}
	// The stop line sits at the lane end; keep a 0.5 m margin so the nose does not overhang the crosswalk.
	return std::max(0.f, lane.length_m - a.s - 0.5f);
}

float TrafficSim::laneDesiredSpeed(const Agent& a, uint32_t lane) const
{
	const auto& g = network_->graph();
	const VehicleClassParams& p = params(a);
	float v = g.lane(lane).speed_mps * p.desired_speed_factor;
	v = std::min(v, p.max_speed_mps);
	// Weather: wet −10 %, snow −35 % (NYC DOT winter operations guidance).
	v *= (1.f - 0.10f * config_.wetness - 0.35f * config_.snowCover);
	return std::max(1.5f, v);
}

bool TrafficSim::chooseNextLane(Agent& a, uint32_t& outLane) const
{
	const auto& g = network_->graph();
	outLane = kInvalidIndex;
	uint32_t n = 0;
	const uint32_t* succ = g.successors(a.lane, n);
	if (n == 0)
	{
		return false;
	}
	const VehicleClassParams& p = params(a);

	float bestScore = -kBigDistance;
	uint32_t best = kInvalidIndex;
	for (uint32_t i = 0; i < n; ++i)
	{
		const uint32_t cand = succ[i];
		if (cand >= g.laneCount())
		{
			continue;
		}
		const Lane& cl = g.lane(cand);
		if (cl.disabled != 0)
		{
			continue;
		}
		if (!g.laneAllows(cand, p.lane_kinds))
		{
			continue;
		}
		// Where does this choice put us?
		const uint32_t target = cl.is_junction != 0 ? cl.to_lane : cand;
		if (target == kInvalidIndex || target >= g.laneCount())
		{
			continue;
		}
		const Lane& tl = g.lane(target);
		if (!p.allow_highway && g.lane(target).segment != kInvalidIndex &&
			g.segment(tl.segment).attrs.rw_type == RwType::Highway)
		{
			continue;
		}

		const LanePose end = g.poseAt(target, tl.length_m);
		const float dx = a.targetX - end.pos.x;
		const float dy = a.targetY - end.pos.y;
		const float distToTarget = std::sqrt(dx * dx + dy * dy);

		// Score: closing on the destination dominates; turning and non-travel lanes cost.
		float score = -distToTarget * 0.01f;
		if (cl.is_junction != 0)
		{
			switch (cl.turn)
			{
			case TurnType::Straight: score += 1.20f; break;
			case TurnType::Right: score += 0.55f; break;
			case TurnType::Left: score += 0.15f; break;
			case TurnType::UTurn: score -= 3.00f; break;
			default: break;
			}
		}
		if (tl.kind == LaneKind::Parking || tl.kind == LaneKind::Shoulder)
		{
			score -= 4.0f;
		}
		if (p.is_bus && tl.kind == LaneKind::Bus)
		{
			score += 1.5f;
		}
		if (p.is_bike && tl.kind == LaneKind::Bike)
		{
			score += 2.0f;
		}
		score += a.rng.uniform(-0.35f, 0.35f);

		if (score > bestScore)
		{
			bestScore = score;
			best = cand;
		}
	}
	if (best == kInvalidIndex)
	{
		return false;
	}
	outLane = best;
	return true;
}

void TrafficSim::applyLaneChange(Agent& a)
{
	// MOBIL (Kesting, Treiber & Helbing 2007) with the class politeness factor: change when the own advantage plus
	// the politeness-weighted change in the neighbours' accelerations beats the threshold.
	const auto& g = network_->graph();
	const Lane& lane = g.lane(a.lane);
	if (lane.is_junction != 0 || a.doubleParked || a.dwellTimer > 0.f)
	{
		return;
	}
	if (a.sinceLaneChange < params(a).lane_change_s)
	{
		return;
	}

	const VehicleClassParams& p = params(a);
	const IdmParams idm = idmFor(p, a.desiredSpeed, config_.wetness, config_.snowCover);

	float gap = kBigDistance, leadV = 0.f;
	const bool hasLeader = findLeader(a, gap, leadV);
	const float ownAccelNow = hasLeader ? nycsim::traffic::idmAccel(idm, a.v, gap, a.v - leadV)
										: nycsim::traffic::idmFreeAccel(idm, a.v);

	const uint32_t candidates[2] = {lane.left, lane.right};
	constexpr float kThreshold = 0.25f;  // m/s² advantage required
	constexpr float kSafeBraking = 4.0f; // m/s² the new follower may be forced to
	float bestGain = kThreshold;
	uint32_t bestLane = kInvalidIndex;

	for (int side = 0; side < 2; ++side)
	{
		const uint32_t target = candidates[side];
		if (target == kInvalidIndex || target >= g.laneCount())
		{
			continue;
		}
		if (!g.laneAllows(target, p.lane_kinds))
		{
			continue;
		}
		const Lane& tl = g.lane(target);
		if (tl.direction != lane.direction || a.s > tl.length_m - 3.f)
		{
			continue;
		}

		// Neighbours in the target lane at the same s.
		float newGap = kBigDistance, newLeadV = 0.f;
		float backGap = kBigDistance, backV = 0.f;
		const uint32_t b = laneBucketStart_[target];
		const uint32_t e = laneBucketStart_[target + 1];
		for (uint32_t k = b; k < e; ++k)
		{
			const Agent& o = agents_[laneAgents_[k]];
			const float halfOther = classParams(o.cls).length_m * 0.5f;
			const float d = o.s - a.s;
			if (d >= 0.f)
			{
				newGap = std::min(newGap, d - p.length_m * 0.5f - halfOther);
				newLeadV = o.doubleParked ? 0.f : o.v;
				break;
			}
			backGap = -d - p.length_m * 0.5f - halfOther;
			backV = o.v;
		}
		if (newGap < p.min_gap_s0 || backGap < p.min_gap_s0)
		{
			continue;
		}

		const float ownAccelNew = nycsim::traffic::idmAccel(idm, a.v, newGap, a.v - newLeadV);
		// Safety criterion for the follower we would cut in front of.
		if (backGap < kBigDistance)
		{
			const float followerAccel = nycsim::traffic::idmAccel(idm, backV, backGap, backV - a.v);
			if (followerAccel < -kSafeBraking)
			{
				continue;
			}
		}
		float gain = ownAccelNew - ownAccelNow;
		// Keep-right bias for slow vehicles, and a nudge to the right when an emergency vehicle is behind.
		if (side == 1)
		{
			gain += 0.10f;
		}
		if ((a.flags & kVehHazard) != 0)
		{
			gain += side == 1 ? 0.8f : -0.8f;
		}
		gain -= p.politeness * 0.5f;
		if (gain > bestGain)
		{
			bestGain = gain;
			bestLane = target;
		}
	}

	if (bestLane != kInvalidIndex)
	{
		float s = a.s, lateral = 0.f, dist = 0.f;
		const LanePose here = g.poseAt(a.lane, a.s, a.lateral);
		if (g.projectOnLane(bestLane, here.pos.x, here.pos.y, s, lateral, dist, 12.f))
		{
			a.lane = bestLane;
			a.s = s;
			a.lateral = 0.f;
			a.lateralTarget = 0.f;
			a.plannedNext = kInvalidIndex;
			a.sinceLaneChange = 0.f;
			a.desiredSpeed = laneDesiredSpeed(a, bestLane);
			++stats_.laneChanges;
		}
	}
}

void TrafficSim::updateAgent(Agent& a)
{
	const auto& g = network_->graph();
	const float dt = config_.stepSeconds;
	const VehicleClassParams& p = params(a);
	a.sinceLaneChange += dt;

	// Dwelling agents (bus at a stop, double-parked van) hold position with hazards / doors.
	if (a.dwellTimer > 0.f)
	{
		a.dwellTimer -= dt;
		a.v = 0.f;
		a.accel = 0.f;
		a.flags |= kVehHazard;
		if (a.busRoute != kInvalidIndex)
		{
			a.flags |= kVehDoorsOpen;
		}
		if (a.dwellTimer <= 0.f)
		{
			a.flags &= static_cast<uint8_t>(~(kVehHazard | kVehDoorsOpen));
			a.doubleParked = false;
		}
		return;
	}

	// Refresh the turn choice when it is missing or stale.
	if (a.plannedNext == kInvalidIndex)
	{
		uint32_t next = kInvalidIndex;
		if (chooseNextLane(a, next))
		{
			a.plannedNext = next;
		}
	}

	const IdmParams idm = idmFor(p, a.desiredSpeed, config_.wetness, config_.snowCover);

	float accel = nycsim::traffic::idmFreeAccel(idm, a.v);

	float gap = kBigDistance, leadV = 0.f;
	if (findLeader(a, gap, leadV))
	{
		accel = std::min(accel, nycsim::traffic::idmAccel(idm, a.v, gap, a.v - leadV));
	}

	float playerSpeed = 0.f;
	const float playerGap = playerObstacleDistance(a, playerSpeed);
	if (playerGap >= 0.f)
	{
		const float dv = a.v - playerSpeed;
		accel = std::min(accel, nycsim::traffic::idmAccel(idm, a.v, playerGap, dv));
		// Honk when the player forces a hard brake or blocks a moving lane.
		const float ttc = dv > 0.2f ? playerGap / dv : kBigDistance;
		if (a.honkCooldown <= 0.f && (ttc < 1.8f || (playerGap < 8.f && a.v < 1.f && playerSpeed < 0.5f)))
		{
			if (a.rng.chance(p.honk_propensity * dt * 2.f))
			{
				a.honk = 1.f;
				a.honkCooldown = a.rng.uniform(2.5f, 6.0f);
				++stats_.honks;
				raise(TrafficEvent::Kind::Honk, a, 1.f);
			}
		}
		if (accel < -p.comfort_decel * 1.5f)
		{
			raise(TrafficEvent::Kind::HardBrake, a, std::min(1.f, -accel / p.max_decel));
		}
	}

	const float pedGap = pedObstacleDistance(a);
	if (pedGap >= 0.f)
	{
		// A pedestrian in the roadway is a stationary obstacle: brake to a stop short of them.
		accel = std::min(accel, nycsim::traffic::idmStopAccel(idm, a.v, std::max(0.3f, pedGap)));
		if (a.honkCooldown <= 0.f && pedGap < 6.f && a.v > 3.f && a.rng.chance(p.honk_propensity * dt))
		{
			a.honk = 1.f;
			a.honkCooldown = a.rng.uniform(3.f, 8.f);
			++stats_.honks;
			raise(TrafficEvent::Kind::Honk, a, 0.7f);
		}
	}

	const float stopDist = stopLineDistance(a);
	if (stopDist >= 0.f)
	{
		accel = std::min(accel, nycsim::traffic::idmStopAccel(idm, a.v, std::max(0.2f, stopDist)));
		if (a.v < 0.5f && stopDist < 4.f)
		{
			a.stopSignHeld += dt;
			++stats_.stoppedAtSignals;
		}
	}
	else
	{
		a.stopSignHeld = 0.f;
	}

	// Curve speed on the lane the agent is entering (AASHTO comfortable lateral acceleration).
	if (a.plannedNext != kInvalidIndex && a.plannedNext < g.laneCount())
	{
		const Lane& nl = g.lane(a.plannedNext);
		if (nl.is_junction != 0 && nl.turn != TurnType::Straight)
		{
			const float turnSpeed = nl.turn == TurnType::UTurn ? 2.2f : (nl.turn == TurnType::Left ? 5.0f : 4.2f);
			const float d = std::max(0.5f, g.lane(a.lane).length_m - a.s);
			if (a.v > turnSpeed)
			{
				const float required = (turnSpeed * turnSpeed - a.v * a.v) / (2.f * d);
				accel = std::min(accel, required);
			}
		}
	}

	// Yield to an emergency vehicle closing from behind: pull right and slow down.
	if (config_.allowEmergency && !p.is_emergency)
	{
		const LanePose pose = g.poseAt(a.lane, a.s, a.lateral);
		bool emergencyBehind = false;
		hash_.query(pose.pos.x, pose.pos.y, 90.f, [&](uint32_t other) {
			if (emergencyBehind || other >= agents_.size())
			{
				return;
			}
			const Agent& o = agents_[other];
			if (!o.active || !classParams(o.cls).is_emergency || (o.flags & kVehSiren) == 0)
			{
				return;
			}
			const LanePose op = g.poseAt(o.lane, o.s, o.lateral);
			const float dx = pose.pos.x - op.pos.x;
			const float dy = pose.pos.y - op.pos.y;
			if (dx * op.dir.x + dy * op.dir.y > 0.f && (dx * dx + dy * dy) < 90.f * 90.f)
			{
				emergencyBehind = true;
			}
		});
		if (emergencyBehind)
		{
			a.lateralTarget = -1.1f;  // toward the curb (lateral is +left of travel)
			a.flags |= kVehHazard;
			accel = std::min(accel, -0.8f);
		}
		else if ((a.flags & kVehHazard) != 0 && !a.doubleParked)
		{
			a.flags &= static_cast<uint8_t>(~kVehHazard);
			a.lateralTarget = 0.f;
		}
	}

	accel = std::clamp(accel, -p.max_decel, p.max_accel);
	a.accel = accel;
	a.v = std::max(0.f, a.v + accel * dt);
	if (a.v > p.max_speed_mps)
	{
		a.v = p.max_speed_mps;
	}

	// Lateral easing (lane-change slide, curb pull-in).
	const float lateralRate = 1.6f * dt;
	if (a.lateral < a.lateralTarget)
	{
		a.lateral = std::min(a.lateralTarget, a.lateral + lateralRate);
	}
	else if (a.lateral > a.lateralTarget)
	{
		a.lateral = std::max(a.lateralTarget, a.lateral - lateralRate);
	}

	// Cosmetic state.
	a.flags = static_cast<uint8_t>(a.flags & ~(kVehBrake | kVehIndicatorLeft | kVehIndicatorRight | kVehHeadlights));
	if (accel < -0.6f)
	{
		a.flags |= kVehBrake;
	}
	if (config_.headlightsOn)
	{
		a.flags |= kVehHeadlights;
	}
	if (a.plannedNext != kInvalidIndex && a.plannedNext < g.laneCount())
	{
		const Lane& nl = g.lane(a.plannedNext);
		const float toEnd = g.lane(a.lane).length_m - a.s;
		if (nl.is_junction != 0 && toEnd < 40.f)
		{
			if (nl.turn == TurnType::Left || nl.turn == TurnType::UTurn)
			{
				a.flags |= kVehIndicatorLeft;
			}
			else if (nl.turn == TurnType::Right)
			{
				a.flags |= kVehIndicatorRight;
			}
		}
	}
	if (p.is_emergency)
	{
		a.flags |= kVehSiren;
	}

	if (a.honkCooldown > 0.f)
	{
		a.honkCooldown -= dt;
	}
	a.honk = std::max(0.f, a.honk - dt * 2.f);

	const float radius = wheelRadiusForLength(p.length_m);
	a.wheelSpin = std::fmod(a.wheelSpin + a.v * dt / radius, 6.28318530718f);
	// Steering angle for the wheel meshes: bicycle model over the lane curvature the agent is following.
	const float curvature = a.v > 0.5f ? (a.steer) : 0.f;
	(void)curvature;
}

void TrafficSim::advance(Agent& a)
{
	const auto& g = network_->graph();
	const float dt = config_.stepSeconds;
	if (a.dwellTimer > 0.f)
	{
		return;
	}

	const LanePose before = g.poseAt(a.lane, a.s, a.lateral);
	a.s += a.v * dt;

	int guard = 0;
	while (a.s >= g.lane(a.lane).length_m && guard++ < 4)
	{
		const float overshoot = a.s - g.lane(a.lane).length_m;
		uint32_t next = a.plannedNext;
		if (next == kInvalidIndex || next >= g.laneCount() || !g.laneAllows(next, params(a).lane_kinds))
		{
			if (!chooseNextLane(a, next))
			{
				// Nothing to enter: the agent leaves the world here.
				a.s = g.lane(a.lane).length_m;
				a.v = 0.f;
				a.dwellTimer = 0.f;
				a.lane = kInvalidIndex;
				return;
			}
		}
		a.lane = next;
		a.s = overshoot;
		a.plannedNext = kInvalidIndex;
		a.stopSignHeld = 0.f;
		a.desiredSpeed = laneDesiredSpeed(a, a.lane);

		// Bus: arrive at the next stop of its route.
		if (a.busRoute < busRoutes_.size())
		{
			const BusRoute& route = busRoutes_[a.busRoute];
			if (!route.stops.empty())
			{
				const BusStop& stop = busStops_[route.stops[a.busNextStop % route.stops.size()]];
				const LanePose here = g.poseAt(a.lane, a.s, a.lateral);
				const float dx = here.pos.x - stop.x;
				const float dy = here.pos.y - stop.y;
				if (dx * dx + dy * dy < 25.f * 25.f)
				{
					a.dwellTimer = a.rng.uniform(12.f, 28.f);
					a.busNextStop = (a.busNextStop + 1) % static_cast<uint32_t>(route.stops.size());
					a.targetX = busStops_[route.stops[a.busNextStop]].x;
					a.targetY = busStops_[route.stops[a.busNextStop]].y;
					++stats_.busesDwelling;
				}
			}
		}
	}

	// Double parking: commercial frontage with a parking lane, at the calibrated rate per kilometre.
	if (!a.doubleParked && a.busRoute == kInvalidIndex && a.lane < g.laneCount())
	{
		const Lane& lane = g.lane(a.lane);
		if (lane.is_junction == 0 && lane.segment != kInvalidIndex)
		{
			const Segment& seg = g.segment(lane.segment);
			const bool commercial = (seg.attrs.flags & nycsim::routing::kSegCommercial) != 0;
			if (commercial && seg.attrs.park_lanes > 0)
			{
				const float perMetre = params(a).double_park_rate_per_km / 1000.f;
				const float travelled = a.v * dt;
				if (travelled > 0.f && a.rng.chance(perMetre * travelled) && !observerProtects(before.pos.x, before.pos.y))
				{
					a.doubleParked = true;
					a.dwellTimer = a.rng.uniform(25.f, 150.f);
					a.lateralTarget = -1.4f;
					a.v = 0.f;
					++stats_.doubleParked;
				}
			}
		}
	}
}

void TrafficSim::spawnPhase()
{
	const auto& g = network_->graph();

	// Refresh the candidate spawn lanes when the observer has moved a quarter of the ring.
	const float dx = observer_.x - spawnLanesX_;
	const float dy = observer_.y - spawnLanesY_;
	if (!spawnLanesValid_ || (dx * dx + dy * dy) > (config_.spawnRadiusM * 0.25f) * (config_.spawnRadiusM * 0.25f))
	{
		spawnLanes_.clear();
		scratchLanes_.assign(4096, 0u);
		const uint32_t found = g.lanesNear(observer_.x, observer_.y, config_.spawnRadiusM + 80.f, scratchLanes_.data(),
										   static_cast<uint32_t>(scratchLanes_.size()), /*include_junction*/ false);
		const uint32_t n = std::min<uint32_t>(found, static_cast<uint32_t>(scratchLanes_.size()));
		for (uint32_t i = 0; i < n; ++i)
		{
			const uint32_t lane = scratchLanes_[i];
			if (lane >= g.laneCount() || !g.laneAllows(lane, nycsim::routing::kMotorLaneKinds))
			{
				continue;
			}
			const Lane& l = g.lane(lane);
			if (l.is_junction != 0 || l.length_m < 12.f || l.segment == kInvalidIndex)
			{
				continue;
			}
			const Segment& seg = g.segment(l.segment);
			if ((seg.attrs.flags & nycsim::routing::kSegNoSpawn) != 0)
			{
				continue;
			}
			if (seg.attrs.rw_type == RwType::NonPhysical || seg.attrs.rw_type == RwType::Ferry ||
				seg.attrs.rw_type == RwType::StepStreet || seg.attrs.rw_type == RwType::Path)
			{
				continue;
			}
			spawnLanes_.push_back(lane);
		}
		spawnLanesX_ = observer_.x;
		spawnLanesY_ = observer_.y;
		spawnLanesValid_ = true;
		sinceTargetRefresh_ = 0xFFFFFFFFu;
	}

	// Target population from the calibrated density table (vehicles per lane-km) over the candidate lanes.
	if (sinceTargetRefresh_ == 0xFFFFFFFFu || ++sinceTargetRefresh_ >= 20u)
	{
		sinceTargetRefresh_ = 0;
		double laneKm = 0.0;
		double weighted = 0.0;
		for (const uint32_t lane : spawnLanes_)
		{
			const float km = g.lane(lane).length_m / 1000.f;
			laneKm += km;
			const nycsim::traffic::DensityCell& cell = network_->densityForLane(lane, config_.hour, config_.dow);
			const float perKm = cell.veh_per_km_lane > 0.f ? cell.veh_per_km_lane : config_.fallbackVehPerKmLane;
			weighted += static_cast<double>(km) * perKm;
		}
		(void)laneKm;
		const double target = weighted * static_cast<double>(config_.vehicleDensityScale);
		targetVehicles_ = static_cast<uint32_t>(std::min<double>(target, config_.maxVehicles));
	}

	if (spawnLanes_.empty() || activeOrder_.size() >= targetVehicles_)
	{
		return;
	}

	const uint32_t deficit = targetVehicles_ - static_cast<uint32_t>(activeOrder_.size());
	const uint32_t attempts = std::min<uint32_t>(deficit, 8u);
	for (uint32_t attempt = 0; attempt < attempts; ++attempt)
	{
		const uint32_t lane = spawnLanes_[rng_.below(static_cast<uint32_t>(spawnLanes_.size()))];
		const Lane& l = g.lane(lane);
		const float s = rng_.uniform(2.f, std::max(3.f, l.length_m - 2.f));
		const LanePose pose = g.poseAt(lane, s);

		const float ddx = pose.pos.x - observer_.x;
		const float ddy = pose.pos.y - observer_.y;
		const float d = std::sqrt(ddx * ddx + ddy * ddy);
		if (d < config_.protectRadiusM || d > config_.despawnRadiusM || observerProtects(pose.pos.x, pose.pos.y))
		{
			++stats_.spawnFailures;
			continue;
		}

		const VehicleClass cls = drawClass(lane);
		const VehicleClassParams& p = classParams(cls);
		if (!g.laneAllows(lane, p.lane_kinds))
		{
			++stats_.spawnFailures;
			continue;
		}

		// Free space check on the lane.
		bool blocked = false;
		const uint32_t b = laneBucketStart_[lane];
		const uint32_t e = laneBucketStart_[lane + 1];
		for (uint32_t k = b; k < e; ++k)
		{
			const Agent& o = agents_[laneAgents_[k]];
			const float clearance = (p.length_m + classParams(o.cls).length_m) * 0.5f + p.min_gap_s0 + 3.f;
			if (std::fabs(o.s - s) < clearance)
			{
				blocked = true;
				break;
			}
		}
		if (blocked)
		{
			++stats_.spawnFailures;
			continue;
		}

		const uint32_t idx = allocateAgent();
		if (idx == kInvalidIndex)
		{
			++stats_.spawnFailures;
			return;
		}
		Agent& a = agents_[idx];
		a.cls = cls;
		a.lane = lane;
		a.s = s;
		a.rng.reseed(config_.seed ^ (static_cast<uint64_t>(a.id) * 0x9E3779B97F4A7C15ull));
		a.desiredSpeed = laneDesiredSpeed(a, lane);
		a.v = a.desiredSpeed * a.rng.uniform(0.55f, 1.0f);
		a.plannedNext = kInvalidIndex;

		// Destination: a point on the far side of the simulated disc, so agents drive through rather than circle.
		const float ang = a.rng.uniform(0.f, 6.28318530718f);
		a.targetX = observer_.x + std::cos(ang) * config_.despawnRadiusM * 2.f;
		a.targetY = observer_.y + std::sin(ang) * config_.despawnRadiusM * 2.f;

		if (p.is_bus && !busRoutes_.empty())
		{
			// Attach the bus to the route whose next stop is closest to where it entered.
			uint32_t bestRoute = kInvalidIndex, bestStop = 0;
			float bestD2 = kBigDistance;
			for (uint32_t r = 0; r < busRoutes_.size(); ++r)
			{
				for (uint32_t si = 0; si < busRoutes_[r].stops.size(); ++si)
				{
					const BusStop& st = busStops_[busRoutes_[r].stops[si]];
					const float sdx = st.x - pose.pos.x;
					const float sdy = st.y - pose.pos.y;
					const float d2 = sdx * sdx + sdy * sdy;
					if (d2 < bestD2)
					{
						bestD2 = d2;
						bestRoute = r;
						bestStop = si;
					}
				}
			}
			if (bestRoute != kInvalidIndex && bestD2 < 900.f * 900.f)
			{
				a.busRoute = bestRoute;
				a.busNextStop = bestStop;
				a.targetX = busStops_[busRoutes_[bestRoute].stops[bestStop]].x;
				a.targetY = busStops_[busRoutes_[bestRoute].stops[bestStop]].y;
			}
		}
		if (p.is_emergency)
		{
			a.flags |= kVehSiren;
			raise(TrafficEvent::Kind::SirenOn, a, 1.f);
		}
		++stats_.spawnedTotal;
	}
}

void TrafficSim::despawnPhase()
{
	const auto& g = network_->graph();
	for (uint32_t i = 0; i < agents_.size(); ++i)
	{
		Agent& a = agents_[i];
		if (!a.active)
		{
			continue;
		}
		if (a.lane == kInvalidIndex || a.lane >= g.laneCount())
		{
			releaseAgent(i);
			++stats_.despawnedTotal;
			continue;
		}
		const LanePose pose = g.poseAt(a.lane, a.s, a.lateral);
		const float dx = pose.pos.x - observer_.x;
		const float dy = pose.pos.y - observer_.y;
		if ((dx * dx + dy * dy) > config_.despawnRadiusM * config_.despawnRadiusM &&
			!observerProtects(pose.pos.x, pose.pos.y))
		{
			if ((a.flags & kVehSiren) != 0)
			{
				raise(TrafficEvent::Kind::SirenOff, a, 1.f);
			}
			releaseAgent(i);
			++stats_.despawnedTotal;
		}
	}
}

VehicleClass TrafficSim::drawClass(uint32_t lane)
{
	const nycsim::traffic::DensityCell& cell = network_->densityForLane(lane, config_.hour, config_.dow);
	const auto& g = network_->graph();
	const Lane& l = g.lane(lane);

	// Bike lanes carry bikes; bus lanes bias to buses. Everything else follows the calibrated fleet shares.
	if (l.kind == LaneKind::Bike)
	{
		return rng_.chance(0.45f) ? VehicleClass::Ebike : VehicleClass::Cyclist;
	}

	float taxi = cell.taxi_share, truck = cell.truck_share, bus = cell.bus_share, bike = cell.bike_share;
	if (taxi + truck + bus + bike <= 0.f)
	{
		// Fallback mix: TLC 2023 medallion + FHV share of Manhattan traffic, DOT truck share, MTA bus share.
		taxi = 0.28f;
		truck = 0.09f;
		bus = 0.03f;
		bike = 0.06f;
	}
	if (l.kind == LaneKind::Bus)
	{
		bus = std::max(bus, 0.35f);
	}
	if (!config_.allowEmergency)
	{
		// Emergency share is drawn separately below.
	}

	const float r = rng_.uniform();
	float acc = 0.f;
	acc += bike;
	if (r < acc)
	{
		return rng_.chance(0.35f) ? VehicleClass::Ebike : VehicleClass::Cyclist;
	}
	acc += bus;
	if (r < acc)
	{
		return VehicleClass::MtaBus;
	}
	acc += truck;
	if (r < acc)
	{
		const float t = rng_.uniform();
		if (t < 0.45f)
		{
			return VehicleClass::Van;
		}
		if (t < 0.85f)
		{
			return VehicleClass::BoxTruck;
		}
		return VehicleClass::DsnyTruck;
	}
	acc += taxi;
	if (r < acc)
	{
		const float t = rng_.uniform();
		if (t < 0.55f)
		{
			return VehicleClass::Taxi;
		}
		if (t < 0.80f)
		{
			return VehicleClass::BoroTaxi;
		}
		return VehicleClass::BlackCar;
	}
	// Emergency vehicles: ~0.6 % of the fleet in view at any time (FDNY/NYPD/EMS fleet size vs. registered
	// vehicles in the five boroughs), only when the host allows them.
	if (config_.allowEmergency && rng_.chance(0.006f))
	{
		const float t = rng_.uniform();
		if (t < 0.55f)
		{
			return VehicleClass::Nypd;
		}
		if (t < 0.80f)
		{
			return VehicleClass::Ambulance;
		}
		return t < 0.93f ? VehicleClass::FdnyEngine : VehicleClass::FdnyLadder;
	}
	if (rng_.chance(0.02f))
	{
		return VehicleClass::Moped;
	}
	return rng_.chance(0.30f) ? VehicleClass::Suv : VehicleClass::Sedan;
}

void TrafficSim::step()
{
	if (network_ == nullptr)
	{
		return;
	}
	const auto t0 = std::chrono::steady_clock::now();

	rebuildLaneBuckets();

	// Deterministic order: ascending agent id.
	std::sort(activeOrder_.begin(), activeOrder_.end(),
			  [this](uint32_t a, uint32_t b) { return agents_[a].id < agents_[b].id; });

	for (const uint32_t i : activeOrder_)
	{
		updateAgent(agents_[i]);
	}
	for (const uint32_t i : activeOrder_)
	{
		applyLaneChange(agents_[i]);
	}
	for (const uint32_t i : activeOrder_)
	{
		advance(agents_[i]);
	}

	despawnPhase();
	spawnPhase();

	simTime_ += config_.stepSeconds;
	++stats_.steps;

	const auto t1 = std::chrono::steady_clock::now();
	stats_.lastStepMs = std::chrono::duration<double, std::milli>(t1 - t0).count();
	stepMsAccum_ += stats_.lastStepMs;
	stats_.avgStepMs = stepMsAccum_ / static_cast<double>(stats_.steps);
}

void TrafficSim::writeSnapshot(std::vector<VehicleSnapshot>& out) const
{
	out.clear();
	if (network_ == nullptr)
	{
		return;
	}
	const auto& g = network_->graph();
	out.reserve(activeOrder_.size());
	for (const uint32_t i : activeOrder_)
	{
		const Agent& a = agents_[i];
		if (!a.active || a.lane >= g.laneCount())
		{
			continue;
		}
		const VehicleClassParams& p = classParams(a.cls);
		const LanePose pose = g.poseAt(a.lane, a.s, a.lateral);
		VehicleSnapshot v;
		v.id = a.id;
		v.cls = static_cast<uint8_t>(a.cls);
		v.flags = a.flags;
		v.routeName = a.busRoute < busRoutes_.size()
						  ? static_cast<uint16_t>(busRoutes_[a.busRoute].nameIndex)
						  : static_cast<uint16_t>(0xFFFFu);
		v.x = pose.pos.x;
		v.y = pose.pos.y;
		v.z = pose.pos.z;
		v.headingRad = pose.heading_rad;
		v.speedMps = a.v;
		v.accelMps2 = a.accel;
		v.steerRad = a.steer;
		v.wheelSpinRad = a.wheelSpin;
		v.lengthM = p.length_m;
		v.widthM = p.width_m;
		v.honking = static_cast<uint8_t>(std::clamp(a.honk, 0.f, 1.f) * 255.f);
		out.push_back(v);
	}
}

}  // namespace nycsim_gameplay
