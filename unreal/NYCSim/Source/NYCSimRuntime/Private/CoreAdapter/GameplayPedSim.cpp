#include "CoreAdapter/GameplayPedSim.h"

#include <algorithm>
#include <chrono>
#include <cmath>

namespace nycsim_gameplay
{

using nycsim::routing::kInvalidIndex;
using nycsim::routing::Node;
using nycsim::routing::Segment;
using nycsim::routing::Vec3;
using nycsim::traffic::PedSignal;

namespace
{

/// Point and unit tangent at arc length `s` along a polyline, plus the interpolated z.
void polylineAt(const Vec3* pts, uint32_t n, float s, float& x, float& y, float& z, float& dx, float& dy)
{
	x = y = z = 0.f;
	dx = 1.f;
	dy = 0.f;
	if (n == 0)
	{
		return;
	}
	if (n == 1)
	{
		x = pts[0].x;
		y = pts[0].y;
		z = pts[0].z;
		return;
	}
	float travelled = 0.f;
	for (uint32_t i = 0; i + 1 < n; ++i)
	{
		const float ex = pts[i + 1].x - pts[i].x;
		const float ey = pts[i + 1].y - pts[i].y;
		const float ez = pts[i + 1].z - pts[i].z;
		const float len = std::sqrt(ex * ex + ey * ey);
		if (len < 1e-4f)
		{
			continue;
		}
		if (s <= travelled + len || i + 2 == n)
		{
			const float t = std::clamp((s - travelled) / len, 0.f, 1.f);
			x = pts[i].x + ex * t;
			y = pts[i].y + ey * t;
			z = pts[i].z + ez * t;
			dx = ex / len;
			dy = ey / len;
			return;
		}
		travelled += len;
	}
	x = pts[n - 1].x;
	y = pts[n - 1].y;
	z = pts[n - 1].z;
}

}  // namespace

PedSim::PedSim() = default;
PedSim::~PedSim() = default;

bool PedSim::init(const RoadNetwork& network, const PedConfig& config, std::string& error)
{
	error.clear();
	network_ = nullptr;
	config_ = config;
	peds_.clear();
	freeList_.clear();
	activeOrder_.clear();
	stats_ = PedStats();
	simTime_ = 0.0;
	nextId_ = 1;
	spawnSegmentsValid_ = false;
	sinceTargetRefresh_ = 0xFFFFFFFFu;

	if (!network.loaded())
	{
		error = "peds: road network not loaded";
		return false;
	}
	if (network.graph().segmentCount() == 0)
	{
		error = "peds: road network has no segments to derive sidewalks from";
		return false;
	}
	network_ = &network;
	rng_.reseed(config_.seed ^ 0xA5A5A5A5A5A5A5A5ull);

	peds_.resize(config_.maxPeds);
	freeList_.resize(config_.maxPeds);
	for (uint32_t i = 0; i < config_.maxPeds; ++i)
	{
		freeList_[i] = config_.maxPeds - 1 - i;
	}

	float minx = 0.f, miny = 0.f, maxx = 0.f, maxy = 0.f;
	network_->graph().bounds(minx, miny, maxx, maxy);
	vehicleHash_.configure(minx, miny, maxx, maxy, 25.f, 4096);
	pedHash_.configure(minx, miny, maxx, maxy, 15.f, config_.maxPeds);
	return true;
}

float PedSim::segmentLength(uint32_t segment) const
{
	const Segment& seg = network_->graph().segment(segment);
	return seg.length_m > 0.5f ? seg.length_m : 0.5f;
}

float PedSim::sidewalkOffset(uint32_t segment) const
{
	const Segment& seg = network_->graph().segment(segment);
	return seg.attrs.width_m * 0.5f + kSidewalkOffsetM;
}

void PedSim::walkPoint(uint32_t segment, uint8_t side, float s, float jitter, float& x, float& y, float& z,
					   float& dirX, float& dirY) const
{
	const auto& g = network_->graph();
	uint32_t n = 0;
	const Vec3* pts = g.segmentVertices(segment, n);
	float cx = 0.f, cy = 0.f, cz = 0.f, dx = 1.f, dy = 0.f;
	polylineAt(pts, n, s, cx, cy, cz, dx, dy);
	// Left of the direction of travel is (-dy, dx).
	const float sign = side == 0 ? 1.f : -1.f;
	const float off = sidewalkOffset(segment) + jitter;
	x = cx + (-dy) * off * sign;
	y = cy + (dx)*off * sign;
	z = cz;
	dirX = dx;
	dirY = dy;
}

PedSignal PedSim::crossingSignal(uint32_t node, float dx, float dy) const
{
	const auto& g = network_->graph();
	if (node >= g.nodeCount())
	{
		return PedSignal::Off;
	}
	if (g.node(node).control != nycsim::routing::Control::Signal)
	{
		return PedSignal::Off;
	}
	uint32_t n = 0;
	const uint32_t* jls = g.nodeJunctionLanes(node, n);
	// Pedestrians crossing a street walk parallel to the vehicle movement along the other street; pick the
	// junction lane whose direction is most parallel to the crossing direction and read its parallel WALK phase.
	float bestDot = -1.f;
	uint32_t bestLane = kInvalidIndex;
	for (uint32_t i = 0; i < n; ++i)
	{
		const uint32_t jl = jls[i];
		if (jl >= g.laneCount() || g.lane(jl).signal_group < 0)
		{
			continue;
		}
		const float len = g.lane(jl).length_m;
		const nycsim::routing::LanePose pose = g.poseAt(jl, len * 0.5f);
		const float d = std::fabs(pose.dir.x * dx + pose.dir.y * dy);
		if (d > bestDot)
		{
			bestDot = d;
			bestLane = jl;
		}
	}
	if (bestLane == kInvalidIndex)
	{
		return PedSignal::Off;
	}
	return network_->pedSignal(bestLane, simTime_);
}

void PedSim::updateVehicles(const std::vector<VehicleSnapshot>& vehicles)
{
	vehicles_.clear();
	vehicles_.reserve(vehicles.size());
	vehicleHash_.begin();
	for (const VehicleSnapshot& v : vehicles)
	{
		if (vehicles_.size() >= vehicleHash_.capacity())
		{
			break;
		}
		VehicleProbe p;
		p.x = v.x;
		p.y = v.y;
		p.dx = std::cos(v.headingRad);
		p.dy = std::sin(v.headingRad);
		p.speed = v.speedMps;
		p.halfLength = v.lengthM * 0.5f;
		vehicleHash_.insert(static_cast<uint32_t>(vehicles_.size()), p.x, p.y);
		vehicles_.push_back(p);
	}
	vehicleHash_.end();
}

bool PedSim::crossingGapSafe(float x0, float y0, float x1, float y1, float horizonSeconds) const
{
	if (vehicles_.empty())
	{
		return true;
	}
	const float mx = (x0 + x1) * 0.5f;
	const float my = (y0 + y1) * 0.5f;
	const float half = std::sqrt((x1 - x0) * (x1 - x0) + (y1 - y0) * (y1 - y0)) * 0.5f;
	bool safe = true;
	vehicleHash_.query(mx, my, half + 45.f, [&](uint32_t idx) {
		if (!safe || idx >= vehicles_.size())
		{
			return;
		}
		const VehicleProbe& v = vehicles_[idx];
		const float rx = mx - v.x;
		const float ry = my - v.y;
		const float along = rx * v.dx + ry * v.dy;
		if (along < -v.halfLength)
		{
			return;  // already past the crossing
		}
		const float lateral = std::fabs(-rx * v.dy + ry * v.dx);
		if (lateral > half + 3.0f)
		{
			return;  // not aimed at this crossing
		}
		const float distance = std::max(0.f, along - v.halfLength);
		const float ttc = v.speed > 0.5f ? distance / v.speed : (distance < 3.f ? 0.f : 1.0e6f);
		if (ttc < horizonSeconds)
		{
			safe = false;
		}
	});
	return safe;
}

uint32_t PedSim::allocatePed()
{
	if (freeList_.empty())
	{
		return kInvalidIndex;
	}
	const uint32_t idx = freeList_.back();
	freeList_.pop_back();
	peds_[idx] = Ped();
	peds_[idx].active = true;
	peds_[idx].id = nextId_++;
	return idx;
}

void PedSim::releasePed(uint32_t index)
{
	if (index >= peds_.size() || !peds_[index].active)
	{
		return;
	}
	peds_[index].active = false;
	peds_[index].segment = kInvalidIndex;
	freeList_.push_back(index);
}

bool PedSim::observerProtects(float x, float y) const
{
	const float dx = x - observer_.x;
	const float dy = y - observer_.y;
	return (dx * dx + dy * dy) <= config_.protectRadiusM * config_.protectRadiusM;
}

bool PedSim::pickNextEdge(Ped& p, uint32_t node, uint32_t& outSegment, uint8_t& outSide, int8_t& outDir) const
{
	const auto& g = network_->graph();
	outSegment = kInvalidIndex;
	if (node >= g.nodeCount())
	{
		return false;
	}
	uint32_t n = 0;
	const uint32_t* segs = g.nodeSegments(node, n);
	if (n == 0)
	{
		return false;
	}

	// Current heading, so continuing straight is preferred over turning back.
	float cx = 0.f, cy = 0.f, cz = 0.f, cdx = 1.f, cdy = 0.f;
	walkPoint(p.segment, p.side, p.s, p.lateralJitter, cx, cy, cz, cdx, cdy);
	const float headX = cdx * static_cast<float>(p.dir);
	const float headY = cdy * static_cast<float>(p.dir);

	float bestScore = -1.0e9f;
	for (uint32_t i = 0; i < n; ++i)
	{
		const uint32_t seg = segs[i];
		if (seg >= g.segmentCount())
		{
			continue;
		}
		const Segment& s = g.segment(seg);
		// A pedestrian never walks along a highway, tunnel bore or ferry line.
		if (s.attrs.rw_type == nycsim::routing::RwType::Highway ||
			s.attrs.rw_type == nycsim::routing::RwType::Tunnel ||
			s.attrs.rw_type == nycsim::routing::RwType::Ferry ||
			s.attrs.rw_type == nycsim::routing::RwType::NonPhysical ||
			s.attrs.rw_type == nycsim::routing::RwType::Ramp)
		{
			continue;
		}
		const bool startsHere = s.from_node == node;
		if (!startsHere && s.to_node != node)
		{
			continue;
		}
		for (uint8_t side = 0; side < 2; ++side)
		{
			const int8_t dir = startsHere ? static_cast<int8_t>(1) : static_cast<int8_t>(-1);
			const float sAt = startsHere ? 0.f : segmentLength(seg);
			float wx = 0.f, wy = 0.f, wz = 0.f, wdx = 1.f, wdy = 0.f;
			walkPoint(seg, side, sAt, p.lateralJitter, wx, wy, wz, wdx, wdy);
			const float outX = wdx * static_cast<float>(dir);
			const float outY = wdy * static_cast<float>(dir);
			float score = 1.4f * (headX * outX + headY * outY);  // prefer going straight on
			if (seg == p.segment && side == p.side)
			{
				score -= 3.0f;  // do not immediately turn around on the same sidewalk
			}
			// Crossing has a cost: pedestrians prefer the corner that keeps them on their side.
			const float ddx = wx - cx;
			const float ddy = wy - cy;
			if (std::sqrt(ddx * ddx + ddy * ddy) > sidewalkOffset(seg) * 1.6f)
			{
				score -= 0.8f;
			}
			score += p.rng.uniform(-0.5f, 0.5f);
			if (score > bestScore)
			{
				bestScore = score;
				outSegment = seg;
				outSide = side;
				outDir = dir;
			}
		}
	}
	return outSegment != kInvalidIndex;
}

void PedSim::beginTransition(Ped& p)
{
	const auto& g = network_->graph();
	const Segment& seg = g.segment(p.segment);
	const uint32_t node = p.dir > 0 ? seg.to_node : seg.from_node;

	uint32_t nextSeg = kInvalidIndex;
	uint8_t nextSide = 0;
	int8_t nextDir = 1;
	if (!pickNextEdge(p, node, nextSeg, nextSide, nextDir))
	{
		// Dead end: turn around on the same sidewalk.
		p.dir = static_cast<int8_t>(-p.dir);
		p.s = std::clamp(p.s, 0.f, segmentLength(p.segment));
		return;
	}

	float fromX = 0.f, fromY = 0.f, fromZ = 0.f, fdx = 1.f, fdy = 0.f;
	walkPoint(p.segment, p.side, p.dir > 0 ? segmentLength(p.segment) : 0.f, p.lateralJitter, fromX, fromY, fromZ,
			  fdx, fdy);
	float toX = 0.f, toY = 0.f, toZ = 0.f, tdx = 1.f, tdy = 0.f;
	const float toS = nextDir > 0 ? 0.f : segmentLength(nextSeg);
	walkPoint(nextSeg, nextSide, toS, p.lateralJitter, toX, toY, toZ, tdx, tdy);

	const float dx = toX - fromX;
	const float dy = toY - fromY;
	const float dist = std::sqrt(dx * dx + dy * dy);

	// Does the path between the two sidewalk points run through the carriageway? The node sits on the centreline,
	// so a corner walk stays outside max(width)/2 of it while a crossing passes right over it.
	uint32_t nSegs = 0;
	const uint32_t* incident = g.nodeSegments(node, nSegs);
	float maxHalfWidth = 3.f;
	for (uint32_t i = 0; i < nSegs; ++i)
	{
		maxHalfWidth = std::max(maxHalfWidth, g.segment(incident[i]).attrs.width_m * 0.5f);
	}
	const float midX = (fromX + toX) * 0.5f;
	const float midY = (fromY + toY) * 0.5f;
	const Node& nd = g.node(node);
	const float midToNode = std::sqrt((midX - nd.pos.x) * (midX - nd.pos.x) + (midY - nd.pos.y) * (midY - nd.pos.y));
	const bool isCrossing = dist > 3.0f && midToNode < maxHalfWidth + 1.0f;

	p.nextSegment = nextSeg;
	p.nextSide = nextSide;
	p.nextDir = nextDir;
	p.crossNode = node;
	p.fromX = fromX;
	p.fromY = fromY;
	p.fromZ = fromZ;
	p.toX = toX;
	p.toY = toY;
	p.toZ = toZ;
	p.crossLength = std::max(0.5f, dist);
	p.crossT = 0.f;

	if (!isCrossing)
	{
		// Walk around the corner: no signal, no gap check.
		p.state = PedState::Crossing;
		p.flags = static_cast<uint8_t>(p.flags & ~kPedJaywalking);
		return;
	}
	p.state = PedState::WaitingToCross;
	p.timer = 0.f;
	p.v = 0.f;
}

void PedSim::updatePed(Ped& p)
{
	const auto& g = network_->graph();
	const float dt = config_.stepSeconds;

	switch (p.state)
	{
	case PedState::Idle:
	{
		p.timer -= dt;
		p.v = 0.f;
		if (p.timer <= 0.f)
		{
			p.state = PedState::Walking;
		}
		return;
	}
	case PedState::WaitingToCross:
	{
		p.timer += dt;
		p.v = 0.f;
		++stats_.waiting;
		const float dx = (p.toX - p.fromX) / p.crossLength;
		const float dy = (p.toY - p.fromY) / p.crossLength;
		p.headingRad = std::atan2(dy, dx);
		const PedSignal signal = crossingSignal(p.crossNode, dx, dy);
		bool go = false;
		bool jay = false;
		if (signal == PedSignal::Walk)
		{
			// Even on WALK, do not step in front of a vehicle already inside the crossing.
			go = crossingGapSafe(p.fromX, p.fromY, p.toX, p.toY, 1.2f);
		}
		else if (signal == PedSignal::Off)
		{
			// Unsignalized crossing: accept a gap.
			go = crossingGapSafe(p.fromX, p.fromY, p.toX, p.toY, p.crossLength / std::max(0.8f, p.desiredSpeed) + 1.5f);
		}
		else
		{
			// DON'T WALK / flashing: the jaywalking share crosses when the gap is comfortable.
			if (p.rng.chance(config_.jaywalkShare) &&
				crossingGapSafe(p.fromX, p.fromY, p.toX, p.toY,
								p.crossLength / std::max(0.8f, p.desiredSpeed) + 2.5f))
			{
				go = true;
				jay = true;
			}
		}
		if (go)
		{
			p.state = PedState::Crossing;
			p.crossT = 0.f;
			if (jay)
			{
				p.flags |= kPedJaywalking;
				++stats_.jaywalking;
			}
			else if (signal == PedSignal::DontWalk || signal == PedSignal::Flash)
			{
				++stats_.unsafeCrossingStarts;
			}
		}
		return;
	}
	case PedState::Crossing:
	{
		++stats_.crossing;
		// Crossing pace: 1.2× the walking speed when jaywalking or when the flashing phase has started.
		const float hurry = (p.flags & kPedJaywalking) != 0 ? 1.25f : 1.0f;
		p.v = p.desiredSpeed * hurry;
		p.crossT += p.v * dt / p.crossLength;
		const float dx = (p.toX - p.fromX) / p.crossLength;
		const float dy = (p.toY - p.fromY) / p.crossLength;
		p.headingRad = std::atan2(dy, dx);
		if (p.crossT >= 1.f)
		{
			p.segment = p.nextSegment;
			p.side = p.nextSide;
			p.dir = p.nextDir;
			p.s = p.dir > 0 ? 0.f : segmentLength(p.segment);
			p.state = PedState::Walking;
			p.flags = static_cast<uint8_t>(p.flags & ~kPedJaywalking);
			p.crossT = 0.f;
		}
		return;
	}
	case PedState::Walking:
	default:
		break;
	}

	// Free walking along the sidewalk, with a simple density-based slowdown from the neighbours ahead.
	float x = 0.f, y = 0.f, z = 0.f, dx = 1.f, dy = 0.f;
	walkPoint(p.segment, p.side, p.s, p.lateralJitter, x, y, z, dx, dy);
	const float headX = dx * static_cast<float>(p.dir);
	const float headY = dy * static_cast<float>(p.dir);
	p.headingRad = std::atan2(headY, headX);

	float speedFactor = 1.f;
	pedHash_.query(x + headX * 1.5f, y + headY * 1.5f, 2.2f, [&](uint32_t idx) {
		if (idx >= peds_.size())
		{
			return;
		}
		const Ped& o = peds_[idx];
		if (!o.active || o.id == p.id || o.state != PedState::Walking)
		{
			return;
		}
		float ox = 0.f, oy = 0.f, oz = 0.f, odx = 0.f, ody = 0.f;
		walkPoint(o.segment, o.side, o.s, o.lateralJitter, ox, oy, oz, odx, ody);
		const float rx = ox - x;
		const float ry = oy - y;
		const float ahead = rx * headX + ry * headY;
		const float lateral = std::fabs(-rx * headY + ry * headX);
		if (ahead > 0.f && ahead < 2.0f && lateral < 0.6f)
		{
			// Fruin level-of-service: pace collapses as the personal buffer closes.
			speedFactor = std::min(speedFactor, std::max(0.15f, ahead / 2.0f));
		}
	});
	// Weather: rain and snow slow walking (Fruin/highway capacity weather factors).
	const float weather = 1.f - 0.10f * std::min(1.f, config_.rainRateMmH / 5.f) - 0.25f * config_.snowCover;
	p.v = p.desiredSpeed * speedFactor * std::max(0.4f, weather);

	p.s += p.v * dt * static_cast<float>(p.dir);
	const float len = segmentLength(p.segment);
	if (p.s <= 0.f || p.s >= len)
	{
		p.s = std::clamp(p.s, 0.f, len);
		beginTransition(p);
		return;
	}

	// Occasionally stop: storefront window, phone call, waiting for someone.
	if (p.rng.chance(0.0006f))
	{
		p.state = PedState::Idle;
		p.timer = p.rng.uniform(2.f, 14.f);
	}
	(void)g;
}

void PedSim::assignAppearance(Ped& p, float x, float y)
{
	// ARCHITECTURE §10: no duplicate (archetype, variant) pair within 60 m. Eight draws are enough in practice;
	// the last draw is accepted so spawning never fails on appearance alone.
	for (int attempt = 0; attempt < 8; ++attempt)
	{
		const uint8_t archetype = static_cast<uint8_t>(p.rng.below(kArchetypeCount));
		const uint8_t variant = static_cast<uint8_t>(p.rng.below(256u));
		bool clash = false;
		pedHash_.query(x, y, 60.f, [&](uint32_t idx) {
			if (clash || idx >= peds_.size())
			{
				return;
			}
			const Ped& o = peds_[idx];
			if (o.active && o.archetype == archetype && o.variant == variant)
			{
				clash = true;
			}
		});
		p.archetype = archetype;
		p.variant = variant;
		if (!clash)
		{
			break;
		}
	}

	p.flags = 0;
	if (config_.rainRateMmH > 0.3f && p.rng.chance(std::min(0.85f, 0.25f + config_.rainRateMmH * 0.12f)))
	{
		p.flags |= kPedUmbrella;
	}
	if (config_.temperatureC < 12.f)
	{
		p.flags |= kPedCoat;
	}
	if (p.rng.chance(0.32f))
	{
		p.flags |= kPedPhone;
	}
	if (p.rng.chance(0.40f))
	{
		p.flags |= kPedBag;
	}
	if (p.rng.chance(0.28f))
	{
		p.flags |= kPedHeadphones;
	}
	if (p.rng.chance(0.05f))
	{
		p.flags |= kPedDog;
	}
}

void PedSim::spawnPhase()
{
	const auto& g = network_->graph();

	const float mdx = observer_.x - spawnSegmentsX_;
	const float mdy = observer_.y - spawnSegmentsY_;
	if (!spawnSegmentsValid_ || (mdx * mdx + mdy * mdy) > (config_.spawnRadiusM * 0.25f) * (config_.spawnRadiusM * 0.25f))
	{
		spawnSegments_.clear();
		scratchLanes_.assign(2048, 0u);
		const uint32_t found = g.lanesNear(observer_.x, observer_.y, config_.spawnRadiusM + 40.f, scratchLanes_.data(),
										   static_cast<uint32_t>(scratchLanes_.size()), false);
		const uint32_t n = std::min<uint32_t>(found, static_cast<uint32_t>(scratchLanes_.size()));
		for (uint32_t i = 0; i < n; ++i)
		{
			const uint32_t lane = scratchLanes_[i];
			if (lane >= g.laneCount())
			{
				continue;
			}
			const uint32_t seg = g.lane(lane).segment;
			if (seg == kInvalidIndex || seg >= g.segmentCount())
			{
				continue;
			}
			const Segment& s = g.segment(seg);
			if (s.attrs.rw_type == nycsim::routing::RwType::Highway ||
				s.attrs.rw_type == nycsim::routing::RwType::Tunnel ||
				s.attrs.rw_type == nycsim::routing::RwType::Ferry ||
				s.attrs.rw_type == nycsim::routing::RwType::NonPhysical ||
				s.attrs.rw_type == nycsim::routing::RwType::Ramp)
			{
				continue;
			}
			if (std::find(spawnSegments_.begin(), spawnSegments_.end(), seg) == spawnSegments_.end())
			{
				spawnSegments_.push_back(seg);
			}
		}
		spawnSegmentsX_ = observer_.x;
		spawnSegmentsY_ = observer_.y;
		spawnSegmentsValid_ = true;
		sinceTargetRefresh_ = 0xFFFFFFFFu;
	}

	if (sinceTargetRefresh_ == 0xFFFFFFFFu || ++sinceTargetRefresh_ >= 20u)
	{
		sinceTargetRefresh_ = 0;
		double total = 0.0;
		for (const uint32_t seg : spawnSegments_)
		{
			// Two sidewalks per segment; density is per m² of sidewalk.
			const float area = 2.f * segmentLength(seg) * config_.sidewalkWidthM;
			uint32_t nLanes = 0;
			const uint32_t* lanes = g.segmentLanes(seg, nLanes);
			float perM2 = config_.fallbackPedPerM2;
			if (nLanes > 0)
			{
				const nycsim::traffic::DensityCell& cell =
					network_->densityForLane(lanes[0], config_.hour, config_.dow);
				if (cell.ped_per_m2 > 0.f)
				{
					perM2 = cell.ped_per_m2;
				}
			}
			total += static_cast<double>(area) * perM2;
		}
		targetPeds_ = static_cast<uint32_t>(std::min<double>(total * config_.densityScale, config_.maxPeds));
	}

	if (spawnSegments_.empty() || activeOrder_.size() >= targetPeds_)
	{
		return;
	}

	const uint32_t attempts = std::min<uint32_t>(targetPeds_ - static_cast<uint32_t>(activeOrder_.size()), 12u);
	for (uint32_t attempt = 0; attempt < attempts; ++attempt)
	{
		const uint32_t seg = spawnSegments_[rng_.below(static_cast<uint32_t>(spawnSegments_.size()))];
		const uint8_t side = static_cast<uint8_t>(rng_.below(2));
		const float len = segmentLength(seg);
		const float s = rng_.uniform(0.5f, std::max(1.f, len - 0.5f));

		const uint32_t idx = allocatePed();
		if (idx == kInvalidIndex)
		{
			return;
		}
		Ped& p = peds_[idx];
		p.rng.reseed(config_.seed ^ (static_cast<uint64_t>(p.id) * 0xD1B54A32D192ED03ull));
		p.segment = seg;
		p.side = side;
		p.s = s;
		p.dir = p.rng.chance(0.5f) ? static_cast<int8_t>(1) : static_cast<int8_t>(-1);
		p.lateralJitter = p.rng.uniform(-config_.sidewalkWidthM * 0.35f, config_.sidewalkWidthM * 0.35f);
		// Free-flow walking speed: Fruin's 1.34 m/s mean with 0.21 m/s spread, floored at the MUTCD 1.07 m/s
		// design speed used for the flashing DON'T WALK interval.
		p.desiredSpeed = p.rng.normalClamped(1.34f, 0.21f, 0.80f, 1.95f);
		p.state = PedState::Walking;

		float x = 0.f, y = 0.f, z = 0.f, dx = 0.f, dy = 0.f;
		walkPoint(seg, side, s, p.lateralJitter, x, y, z, dx, dy);
		if (observerProtects(x, y))
		{
			releasePed(idx);
			continue;
		}
		const float ddx = x - observer_.x;
		const float ddy = y - observer_.y;
		if ((ddx * ddx + ddy * ddy) > config_.despawnRadiusM * config_.despawnRadiusM)
		{
			releasePed(idx);
			continue;
		}
		assignAppearance(p, x, y);
		++stats_.spawnedTotal;
	}
}

void PedSim::despawnPhase()
{
	for (uint32_t i = 0; i < peds_.size(); ++i)
	{
		Ped& p = peds_[i];
		if (!p.active)
		{
			continue;
		}
		if (p.segment == kInvalidIndex || p.segment >= network_->graph().segmentCount())
		{
			releasePed(i);
			++stats_.despawnedTotal;
			continue;
		}
		float x = 0.f, y = 0.f, z = 0.f, dx = 0.f, dy = 0.f;
		walkPoint(p.segment, p.side, p.s, p.lateralJitter, x, y, z, dx, dy);
		const float ddx = x - observer_.x;
		const float ddy = y - observer_.y;
		if ((ddx * ddx + ddy * ddy) > config_.despawnRadiusM * config_.despawnRadiusM && !observerProtects(x, y) &&
			p.state != PedState::Crossing)
		{
			releasePed(i);
			++stats_.despawnedTotal;
		}
	}
}

void PedSim::step()
{
	if (network_ == nullptr)
	{
		return;
	}
	const auto t0 = std::chrono::steady_clock::now();

	activeOrder_.clear();
	pedHash_.begin();
	for (uint32_t i = 0; i < peds_.size(); ++i)
	{
		Ped& p = peds_[i];
		if (!p.active || p.segment >= network_->graph().segmentCount())
		{
			continue;
		}
		activeOrder_.push_back(i);
		float x = 0.f, y = 0.f, z = 0.f, dx = 0.f, dy = 0.f;
		walkPoint(p.segment, p.side, p.s, p.lateralJitter, x, y, z, dx, dy);
		pedHash_.insert(i, x, y);
	}
	pedHash_.end();
	std::sort(activeOrder_.begin(), activeOrder_.end(),
			  [this](uint32_t a, uint32_t b) { return peds_[a].id < peds_[b].id; });

	stats_.crossing = 0;
	stats_.waiting = 0;
	for (const uint32_t i : activeOrder_)
	{
		updatePed(peds_[i]);
	}

	despawnPhase();
	spawnPhase();

	stats_.peds = static_cast<uint32_t>(activeOrder_.size());
	simTime_ += config_.stepSeconds;
	++stats_.steps;

	const auto t1 = std::chrono::steady_clock::now();
	stats_.lastStepMs = std::chrono::duration<double, std::milli>(t1 - t0).count();
	stepMsAccum_ += stats_.lastStepMs;
	stats_.avgStepMs = stepMsAccum_ / static_cast<double>(stats_.steps);
}

void PedSim::writeSnapshot(std::vector<PedSnapshot>& out) const
{
	out.clear();
	if (network_ == nullptr)
	{
		return;
	}
	out.reserve(activeOrder_.size());
	for (const uint32_t i : activeOrder_)
	{
		const Ped& p = peds_[i];
		if (!p.active)
		{
			continue;
		}
		PedSnapshot s;
		s.id = p.id;
		if (p.state == PedState::Crossing)
		{
			const float t = std::clamp(p.crossT, 0.f, 1.f);
			s.x = p.fromX + (p.toX - p.fromX) * t;
			s.y = p.fromY + (p.toY - p.fromY) * t;
			s.z = p.fromZ + (p.toZ - p.fromZ) * t;
		}
		else if (p.state == PedState::WaitingToCross)
		{
			s.x = p.fromX;
			s.y = p.fromY;
			s.z = p.fromZ;
		}
		else
		{
			float dx = 0.f, dy = 0.f;
			walkPoint(p.segment, p.side, p.s, p.lateralJitter, s.x, s.y, s.z, dx, dy);
		}
		s.headingRad = p.headingRad;
		s.speedMps = p.v;
		s.state = static_cast<uint8_t>(p.state);
		s.archetype = p.archetype;
		s.variant = p.variant;
		s.flags = p.flags;
		out.push_back(s);
	}
}

void PedSim::writeObstacles(std::vector<PedObstacle>& out) const
{
	out.clear();
	if (network_ == nullptr)
	{
		return;
	}
	for (const uint32_t i : activeOrder_)
	{
		const Ped& p = peds_[i];
		if (!p.active || p.state != PedState::Crossing)
		{
			continue;
		}
		// Only the part of the crossing that is actually inside the carriageway matters; the first and last metre
		// are the kerb ramps.
		const float t = std::clamp(p.crossT, 0.f, 1.f);
		if (p.crossLength > 3.f && (t * p.crossLength < 1.f || (1.f - t) * p.crossLength < 1.f))
		{
			continue;
		}
		PedObstacle o;
		o.x = p.fromX + (p.toX - p.fromX) * t;
		o.y = p.fromY + (p.toY - p.fromY) * t;
		out.push_back(o);
	}
}

}  // namespace nycsim_gameplay
