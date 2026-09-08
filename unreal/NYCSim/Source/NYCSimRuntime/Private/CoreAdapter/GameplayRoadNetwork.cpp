#include "CoreAdapter/GameplayRoadNetwork.h"

#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstring>
#include <fstream>

#include "nycsim/routing/NycbLite.h"
#include "nycsim/traffic/SyntheticGrid.h"

namespace nycsim_gameplay
{

const char* const RoadNetwork::kMissingFile = "file-not-found";

namespace
{

bool defaultFileReader(void* /*context*/, const std::string& path, std::vector<uint8_t>& out, std::string& error)
{
	std::ifstream in(path.c_str(), std::ios::binary | std::ios::ate);
	if (!in)
	{
		error = RoadNetwork::kMissingFile;
		return false;
	}
	const std::streamoff size = in.tellg();
	if (size < 0)
	{
		error = "cannot determine size of " + path;
		return false;
	}
	out.resize(static_cast<size_t>(size));
	in.seekg(0, std::ios::beg);
	if (size > 0 && !in.read(reinterpret_cast<char*>(out.data()), size))
	{
		error = "short read on " + path;
		return false;
	}
	return true;
}

std::string joinPath(const std::string& dir, const char* leaf)
{
	if (dir.empty())
	{
		return std::string(leaf);
	}
	const char last = dir[dir.size() - 1];
	if (last == '/' || last == '\\')
	{
		return dir + leaf;
	}
	return dir + "/" + leaf;
}

/// Score a folded query against a folded label. -1 when it does not match at all.
/// Prefix of the whole label > prefix of a word > substring; shorter labels win ties.
float scoreMatch(const std::string& label, const std::string& query)
{
	if (query.empty() || label.empty())
	{
		return -1.f;
	}
	const size_t pos = label.find(query);
	if (pos == std::string::npos)
	{
		return -1.f;
	}
	float score = 100.f;
	if (pos == 0)
	{
		score += 60.f;
	}
	else if (label[pos - 1] == ' ')
	{
		score += 30.f;
	}
	// Prefer labels that are not much longer than the query (exact-ish match).
	score += 40.f * static_cast<float>(query.size()) / static_cast<float>(label.size());
	return score;
}

}  // namespace

RoadNetwork::RoadNetwork() = default;
RoadNetwork::~RoadNetwork() = default;

std::string RoadNetwork::fold(const std::string& s)
{
	std::string out;
	out.reserve(s.size());
	bool lastSpace = true;  // trims leading space
	for (const char raw : s)
	{
		const unsigned char c = static_cast<unsigned char>(raw);
		char ch;
		if (c >= 'A' && c <= 'Z')
		{
			ch = static_cast<char>(c - 'A' + 'a');
		}
		else if ((c >= 'a' && c <= 'z') || (c >= '0' && c <= '9'))
		{
			ch = static_cast<char>(c);
		}
		else
		{
			ch = ' ';
		}
		if (ch == ' ')
		{
			if (lastSpace)
			{
				continue;
			}
			lastSpace = true;
		}
		else
		{
			lastSpace = false;
		}
		out.push_back(ch);
	}
	while (!out.empty() && out.back() == ' ')
	{
		out.pop_back();
	}
	return out;
}

bool RoadNetwork::loadFile(const std::string& path, std::vector<uint8_t>& out, std::string& error) const
{
	const FileReader r = reader_ != nullptr ? reader_ : &defaultFileReader;
	out.clear();
	error.clear();
	return r(readerContext_, path, out, error);
}

bool RoadNetwork::load(const std::string& runtimeDir, std::string& error, FileReader reader, void* context)
{
	const auto t0 = std::chrono::steady_clock::now();
	reader_ = reader;
	readerContext_ = context;
	loaded_ = false;
	synthetic_ = false;
	notes_.clear();
	entries_.clear();
	order_.clear();
	gridStart_.clear();
	gridItems_.clear();
	stats_ = RoadNetworkStats();
	graph_.clear();
	signals_.clear();
	density_.clear();
	error.clear();

	std::vector<uint8_t> bytes;
	std::string ioError;

	// ---- roadgraph.nycb (mandatory) -------------------------------------------------------------------------
	if (!loadFile(joinPath(runtimeDir, "roadgraph.nycb"), bytes, ioError))
	{
		error = "roadgraph.nycb: " + (ioError == kMissingFile ? std::string("not found in ") + runtimeDir : ioError);
		return false;
	}
	if (!graph_.loadFromNycb(bytes.data(), bytes.size()))
	{
		error = "roadgraph.nycb: " + graph_.lastError();
		return false;
	}
	if (graph_.laneCount() == 0)
	{
		error = "roadgraph.nycb contains no lanes";
		return false;
	}

	stats_.nodes = static_cast<uint32_t>(graph_.nodeCount());
	stats_.segments = static_cast<uint32_t>(graph_.segmentCount());
	stats_.roadLanes = static_cast<uint32_t>(graph_.roadLaneCount());
	stats_.junctionLanes = static_cast<uint32_t>(graph_.junctionLaneCount());
	graph_.bounds(stats_.minX, stats_.minY, stats_.maxX, stats_.maxY);

	// ---- signals.nycb (optional: default plans are synthesized for every signalized node) --------------------
	if (loadFile(joinPath(runtimeDir, "signals.nycb"), bytes, ioError))
	{
		if (!signals_.loadFromNycb(bytes.data(), bytes.size()))
		{
			notes_.push_back("signals.nycb rejected (" + signals_.lastError() + "); default plans used instead");
			signals_.clear();
		}
	}
	else if (ioError == kMissingFile)
	{
		notes_.push_back("signals.nycb not present; default NYC DOT plans synthesized for every signalized node");
	}
	else
	{
		notes_.push_back("signals.nycb: " + ioError);
	}

	if (!signals_.bind(graph_))
	{
		notes_.push_back("signal bind: " + signals_.lastError());
	}
	const uint32_t loadedPlans = static_cast<uint32_t>(signals_.planCount());
	traffic::DefaultPlanParams planParams;  // 90 s cycle, 3 s yellow, 2 s all-red, 7 s LPI (ARCHITECTURE §6)
	stats_.defaultSignalPlans = signals_.addDefaultPlans(graph_, planParams);
	if (stats_.defaultSignalPlans > 0 && !signals_.bind(graph_))
	{
		notes_.push_back("signal re-bind after default plans: " + signals_.lastError());
	}
	stats_.signalPlans = static_cast<uint32_t>(signals_.planCount());
	if (stats_.signalPlans != loadedPlans + stats_.defaultSignalPlans)
	{
		notes_.push_back("signal plan count is not loaded + defaults; the table de-duplicated some nodes");
	}

	// ---- density.nycb (optional) ----------------------------------------------------------------------------
	if (loadFile(joinPath(runtimeDir, "density.nycb"), bytes, ioError))
	{
		if (!density_.loadFromNycb(bytes.data(), bytes.size()))
		{
			notes_.push_back("density.nycb rejected (" + density_.lastError() + "); traffic falls back to the "
							 "per-segment lane capacity model");
			density_.clear();
		}
		else
		{
			stats_.ntaCells = density_.ntaCount();
			stats_.lanesWithNta = density_.assignLaneNtas(graph_);
		}
	}
	else if (ioError == kMissingFile)
	{
		notes_.push_back("density.nycb not present; traffic falls back to the per-segment lane capacity model");
	}
	else
	{
		notes_.push_back("density.nycb: " + ioError);
	}

	// ---- destination index ----------------------------------------------------------------------------------
	buildStreetIndex();

	if (loadFile(joinPath(runtimeDir, "pois.nycb"), bytes, ioError))
	{
		if (!loadPois(bytes))
		{
			notes_.push_back("pois.nycb: unreadable section layout; address search unavailable");
		}
	}
	else if (ioError == kMissingFile)
	{
		notes_.push_back("pois.nycb not present; address search falls back to street names only");
	}
	else
	{
		notes_.push_back("pois.nycb: " + ioError);
	}

	if (loadFile(joinPath(runtimeDir, "transit.nycb"), bytes, ioError))
	{
		if (!loadTransit(bytes))
		{
			notes_.push_back("transit.nycb: unreadable section layout; bus stops are not searchable");
		}
	}
	else if (ioError == kMissingFile)
	{
		notes_.push_back("transit.nycb not present; bus stops are not searchable");
	}
	else
	{
		notes_.push_back("transit.nycb: " + ioError);
	}

	if (loadFile(joinPath(runtimeDir, "landmarks.nycb"), bytes, ioError))
	{
		if (!loadLandmarks(bytes))
		{
			notes_.push_back("landmarks.nycb present but carries no `points` section in the {float x, float y, "
							 "uint32 name_str} layout; landmark search unavailable");
		}
	}
	else if (ioError == kMissingFile)
	{
		notes_.push_back("landmarks.nycb not present; landmark search unavailable");
	}
	else
	{
		notes_.push_back("landmarks.nycb: " + ioError);
	}

	finishIndex();

	const auto t1 = std::chrono::steady_clock::now();
	stats_.loadSeconds = std::chrono::duration<double>(t1 - t0).count();
	loaded_ = true;
	return true;
}

bool RoadNetwork::buildSyntheticGrid(int avenues, int streets, float originX, float originY, std::string& error)
{
	const auto t0 = std::chrono::steady_clock::now();
	loaded_ = false;
	synthetic_ = false;
	notes_.clear();
	entries_.clear();
	order_.clear();
	gridStart_.clear();
	gridItems_.clear();
	stats_ = RoadNetworkStats();
	graph_.clear();
	signals_.clear();
	density_.clear();
	error.clear();

	traffic::SyntheticGridSpec spec;
	spec.avenues = avenues > 1 ? avenues : 2;
	spec.streets = streets > 1 ? streets : 2;
	spec.origin_x = originX;
	spec.origin_y = originY;
	if (!traffic::SyntheticGrid::build(spec, graph_, signals_, &error))
	{
		if (error.empty())
		{
			error = "synthetic grid build failed";
		}
		return false;
	}

	stats_.nodes = static_cast<uint32_t>(graph_.nodeCount());
	stats_.segments = static_cast<uint32_t>(graph_.segmentCount());
	stats_.roadLanes = static_cast<uint32_t>(graph_.roadLaneCount());
	stats_.junctionLanes = static_cast<uint32_t>(graph_.junctionLaneCount());
	stats_.signalPlans = static_cast<uint32_t>(signals_.planCount());
	graph_.bounds(stats_.minX, stats_.minY, stats_.maxX, stats_.maxY);

	buildStreetIndex();
	finishIndex();

	notes_.push_back("synthetic Manhattan-like grid (nycsim::traffic::SyntheticGrid); no real street data loaded");
	stats_.loadSeconds = std::chrono::duration<double>(std::chrono::steady_clock::now() - t0).count();
	loaded_ = true;
	synthetic_ = true;
	return true;
}

void RoadNetwork::buildStreetIndex()
{
	// One entry per distinct street name, positioned at the length-weighted centroid of its segments. Names are
	// taken from the graph itself (DATA_CONTRACTS §7 `full_street_name`), so they are the real signed names.
	struct Acc
	{
		double sx = 0.0, sy = 0.0, w = 0.0;
		std::string name;
	};
	std::vector<Acc> acc;
	std::vector<uint32_t> nameToAcc;

	const size_t segCount = graph_.segmentCount();
	for (uint32_t s = 0; s < segCount; ++s)
	{
		const std::string_view nameView = graph_.segmentName(s);
		if (nameView.empty())
		{
			continue;
		}
		const routing::Segment& seg = graph_.segment(s);
		if (seg.name >= nameToAcc.size())
		{
			nameToAcc.resize(seg.name + 1, 0xFFFFFFFFu);
		}
		uint32_t slot = nameToAcc[seg.name];
		if (slot == 0xFFFFFFFFu)
		{
			slot = static_cast<uint32_t>(acc.size());
			nameToAcc[seg.name] = slot;
			acc.emplace_back();
			acc.back().name.assign(nameView.data(), nameView.size());
		}
		uint32_t n = 0;
		const routing::Vec3* pts = graph_.segmentVertices(s, n);
		if (n == 0)
		{
			continue;
		}
		const double weight = seg.length_m > 0.f ? static_cast<double>(seg.length_m) : 1.0;
		const routing::Vec3& mid = pts[n / 2];
		acc[slot].sx += static_cast<double>(mid.x) * weight;
		acc[slot].sy += static_cast<double>(mid.y) * weight;
		acc[slot].w += weight;
	}

	entries_.reserve(entries_.size() + acc.size());
	for (const Acc& a : acc)
	{
		if (a.w <= 0.0)
		{
			continue;
		}
		addEntry(a.name, static_cast<float>(a.sx / a.w), static_cast<float>(a.sy / a.w), SearchEntry::Kind::Street);
	}
}

bool RoadNetwork::loadPois(const std::vector<uint8_t>& bytes)
{
	nycsim::nycb::File f;
	if (!f.open(bytes.data(), bytes.size()))
	{
		return false;
	}
	const nycsim::nycb::Section pois = f.section("pois");
	const nycsim::nycb::Section strtab = f.section("strtab");
	if (!pois.present || pois.element_size < 12)
	{
		return false;
	}
	// The "places" section is the 85,023 named OpenStreetMap places -- shops, restaurants, schools,
	// hospitals, stations, parks. Same record as "pois" and the same string table, because it is the
	// same kind of thing: a point with a label to search for. Until it existed the GPS could find
	// "350 5 Ave" and could not find "Katz's Delicatessen", because the only thing feeding its index
	// was the address list. An older pois.nycb has no such section and still loads.
	const nycsim::nycb::Section places = f.section("places");
	const uint32_t placeCount = (places.present && places.element_size >= 12) ? places.element_count : 0u;
	entries_.reserve(entries_.size() + pois.element_count + placeCount);
	for (uint32_t i = 0; i < pois.element_count; ++i)
	{
		const uint8_t* rec = pois.at(i);
		const float x = nycsim::nycb::rdF32(rec);
		const float y = nycsim::nycb::rdF32(rec + 4);
		const uint32_t addr = nycsim::nycb::rdU32(rec + 8);
		const std::string_view label = nycsim::nycb::File::str(strtab, addr);
		if (label.empty())
		{
			continue;
		}
		addEntry(std::string(label), x, y, SearchEntry::Kind::Address);
		++stats_.addresses;
	}
	for (uint32_t i = 0; i < placeCount; ++i)
	{
		const uint8_t* rec = places.at(i);
		const float x = nycsim::nycb::rdF32(rec);
		const float y = nycsim::nycb::rdF32(rec + 4);
		const uint32_t name = nycsim::nycb::rdU32(rec + 8);
		const std::string_view label = nycsim::nycb::File::str(strtab, name);
		if (label.empty())
		{
			continue;
		}
		addEntry(std::string(label), x, y, SearchEntry::Kind::Place);
		++stats_.places;
	}
	return true;
}

bool RoadNetwork::loadTransit(const std::vector<uint8_t>& bytes)
{
	nycsim::nycb::File f;
	if (!f.open(bytes.data(), bytes.size()))
	{
		return false;
	}
	const nycsim::nycb::Section stops = f.section("bus_stops");
	const nycsim::nycb::Section strtab = f.section("strtab");
	if (!stops.present || stops.element_size < 24)
	{
		return false;
	}
	for (uint32_t i = 0; i < stops.element_count; ++i)
	{
		const uint8_t* rec = stops.at(i);
		const float x = nycsim::nycb::rdF32(rec + 8);
		const float y = nycsim::nycb::rdF32(rec + 12);
		const uint32_t nameOff = nycsim::nycb::rdU32(rec + 20);
		const std::string_view label = nycsim::nycb::File::str(strtab, nameOff);
		if (label.empty())
		{
			continue;
		}
		addEntry(std::string(label), x, y, SearchEntry::Kind::BusStop);
		++stats_.busStops;
	}
	return true;
}

bool RoadNetwork::loadLandmarks(const std::vector<uint8_t>& bytes)
{
	// DATA_CONTRACTS §15 names runtime/landmarks.nycb but does not yet fix its section layout. This reader accepts
	// the same shape as `pois` — a `points` section of {float x, float y, uint32 name_str} plus `strtab` — and
	// reports absence rather than guessing any other layout (see docs/verification/unreal_gameplay/REPORT.md,
	// "contract extension requested").
	nycsim::nycb::File f;
	if (!f.open(bytes.data(), bytes.size()))
	{
		return false;
	}
	nycsim::nycb::Section pts = f.section("points");
	if (!pts.present)
	{
		pts = f.section("landmarks");
	}
	const nycsim::nycb::Section strtab = f.section("strtab");
	if (!pts.present || pts.element_size < 12 || !strtab.present)
	{
		return false;
	}
	for (uint32_t i = 0; i < pts.element_count; ++i)
	{
		const uint8_t* rec = pts.at(i);
		const float x = nycsim::nycb::rdF32(rec);
		const float y = nycsim::nycb::rdF32(rec + 4);
		const uint32_t nameOff = nycsim::nycb::rdU32(rec + 8);
		const std::string_view label = nycsim::nycb::File::str(strtab, nameOff);
		if (label.empty())
		{
			continue;
		}
		addEntry(std::string(label), x, y, SearchEntry::Kind::Landmark);
		++stats_.landmarks;
	}
	return true;
}

void RoadNetwork::addEntry(std::string label, float x, float y, SearchEntry::Kind kind)
{
	SearchEntry e;
	e.folded = fold(label);
	if (e.folded.empty())
	{
		return;
	}
	e.label = std::move(label);
	e.x = x;
	e.y = y;
	e.kind = kind;
	entries_.push_back(std::move(e));
}

void RoadNetwork::finishIndex()
{
	order_.resize(entries_.size());
	for (uint32_t i = 0; i < order_.size(); ++i)
	{
		order_[i] = i;
	}
	std::sort(order_.begin(), order_.end(), [this](uint32_t a, uint32_t b) {
		const int cmp = entries_[a].folded.compare(entries_[b].folded);
		if (cmp != 0)
		{
			return cmp < 0;
		}
		return static_cast<uint8_t>(entries_[a].kind) < static_cast<uint8_t>(entries_[b].kind);
	});

	// Uniform grid for nearestEntry().
	if (entries_.empty())
	{
		gridStart_.assign(2, 0u);
		gridNx_ = gridNy_ = 1;
		return;
	}
	float minx = entries_[0].x, miny = entries_[0].y, maxx = entries_[0].x, maxy = entries_[0].y;
	for (const SearchEntry& e : entries_)
	{
		minx = std::min(minx, e.x);
		miny = std::min(miny, e.y);
		maxx = std::max(maxx, e.x);
		maxy = std::max(maxy, e.y);
	}
	gridMinX_ = minx;
	gridMinY_ = miny;
	gridNx_ = static_cast<uint32_t>((maxx - minx) / kGridCell) + 1u;
	gridNy_ = static_cast<uint32_t>((maxy - miny) / kGridCell) + 1u;
	const size_t cells = static_cast<size_t>(gridNx_) * gridNy_;
	gridStart_.assign(cells + 1, 0u);
	std::vector<uint32_t> cellOf(entries_.size(), 0u);
	for (size_t i = 0; i < entries_.size(); ++i)
	{
		const uint32_t cx = std::min(gridNx_ - 1u, static_cast<uint32_t>((entries_[i].x - gridMinX_) / kGridCell));
		const uint32_t cy = std::min(gridNy_ - 1u, static_cast<uint32_t>((entries_[i].y - gridMinY_) / kGridCell));
		cellOf[i] = cy * gridNx_ + cx;
		++gridStart_[cellOf[i] + 1];
	}
	for (size_t c = 0; c < cells; ++c)
	{
		gridStart_[c + 1] += gridStart_[c];
	}
	gridItems_.assign(entries_.size(), 0u);
	std::vector<uint32_t> cursor(gridStart_.begin(), gridStart_.end() - 1);
	for (uint32_t i = 0; i < entries_.size(); ++i)
	{
		gridItems_[cursor[cellOf[i]]++] = i;
	}
}

uint32_t RoadNetwork::search(const std::string& query, SearchHit* out, uint32_t cap) const
{
	if (out == nullptr || cap == 0)
	{
		return 0;
	}
	const std::string q = fold(query);
	if (q.empty() || entries_.empty())
	{
		return 0;
	}

	// Prefix range first (binary search over the sorted order), then a bounded scan for substring hits so that
	// "grand central" also finds "Grand Central Terminal" typed as "central".
	std::vector<SearchHit> hits;
	hits.reserve(cap * 4);

	const auto lower = std::lower_bound(order_.begin(), order_.end(), q, [this](uint32_t a, const std::string& key) {
		return entries_[a].folded.compare(key) < 0;
	});
	for (auto it = lower; it != order_.end(); ++it)
	{
		const SearchEntry& e = entries_[*it];
		if (e.folded.compare(0, std::min(e.folded.size(), q.size()), q) != 0)
		{
			break;
		}
		SearchHit h;
		h.entry = *it;
		h.score = scoreMatch(e.folded, q);
		hits.push_back(h);
		if (hits.size() >= cap * 8u)
		{
			break;
		}
	}

	if (hits.size() < cap)
	{
		for (uint32_t i = 0; i < entries_.size(); ++i)
		{
			const float s = scoreMatch(entries_[i].folded, q);
			if (s < 0.f)
			{
				continue;
			}
			bool already = false;
			for (const SearchHit& h : hits)
			{
				if (h.entry == i)
				{
					already = true;
					break;
				}
			}
			if (already)
			{
				continue;
			}
			SearchHit h;
			h.entry = i;
			h.score = s;
			hits.push_back(h);
			if (hits.size() >= cap * 8u)
			{
				break;
			}
		}
	}

	std::sort(hits.begin(), hits.end(), [this](const SearchHit& a, const SearchHit& b) {
		if (a.score != b.score)
		{
			return a.score > b.score;
		}
		return entries_[a.entry].label < entries_[b.entry].label;
	});

	const uint32_t n = static_cast<uint32_t>(std::min<size_t>(hits.size(), cap));
	for (uint32_t i = 0; i < n; ++i)
	{
		out[i] = hits[i];
	}
	return n;
}

uint32_t RoadNetwork::nearestEntry(float x, float y, float maxDistanceM) const
{
	if (entries_.empty() || maxDistanceM <= 0.f)
	{
		return 0xFFFFFFFFu;
	}
	const int rings = static_cast<int>(maxDistanceM / kGridCell) + 1;
	const int cx = static_cast<int>((x - gridMinX_) / kGridCell);
	const int cy = static_cast<int>((y - gridMinY_) / kGridCell);
	float best = maxDistanceM * maxDistanceM;
	uint32_t bestIdx = 0xFFFFFFFFu;
	for (int dy = -rings; dy <= rings; ++dy)
	{
		const int gy = cy + dy;
		if (gy < 0 || gy >= static_cast<int>(gridNy_))
		{
			continue;
		}
		for (int dx = -rings; dx <= rings; ++dx)
		{
			const int gx = cx + dx;
			if (gx < 0 || gx >= static_cast<int>(gridNx_))
			{
				continue;
			}
			const uint32_t cell = static_cast<uint32_t>(gy) * gridNx_ + static_cast<uint32_t>(gx);
			for (uint32_t k = gridStart_[cell]; k < gridStart_[cell + 1]; ++k)
			{
				const uint32_t idx = gridItems_[k];
				const float ex = entries_[idx].x - x;
				const float ey = entries_[idx].y - y;
				const float d2 = ex * ex + ey * ey;
				if (d2 < best)
				{
					best = d2;
					bestIdx = idx;
				}
			}
		}
	}
	return bestIdx;
}

std::unique_ptr<routing::Router> RoadNetwork::makeRouter(uint32_t landmarks, std::string& error) const
{
	error.clear();
	if (!loaded_)
	{
		error = "road network not loaded";
		return nullptr;
	}
	std::unique_ptr<routing::Router> r(new routing::Router());
	if (!r->attach(graph_, landmarks, /*seed*/ 20260906ull))
	{
		error = r->lastError();
		return nullptr;
	}
	return r;
}

std::string RoadNetwork::laneStreetName(uint32_t lane) const
{
	if (!loaded_ || lane >= graph_.laneCount())
	{
		return std::string();
	}
	const std::string_view v = graph_.laneStreetName(lane);
	return std::string(v.data(), v.size());
}

traffic::VehSignal RoadNetwork::junctionSignal(uint32_t junctionLane, double t) const
{
	if (!loaded_ || junctionLane >= graph_.laneCount())
	{
		return traffic::VehSignal::Off;
	}
	const routing::Lane& l = graph_.lane(junctionLane);
	if (l.is_junction == 0 || l.signal_group < 0 || l.node == routing::kInvalidIndex)
	{
		return traffic::VehSignal::Off;
	}
	const uint32_t plan = signals_.planForNode(l.node);
	if (plan == routing::kInvalidIndex)
	{
		return traffic::VehSignal::Off;
	}
	return signals_.vehicleState(plan, l.signal_group, t);
}

traffic::PedSignal RoadNetwork::pedSignal(uint32_t junctionLane, double t) const
{
	if (!loaded_ || junctionLane >= graph_.laneCount())
	{
		return traffic::PedSignal::Off;
	}
	const routing::Lane& l = graph_.lane(junctionLane);
	if (l.node == routing::kInvalidIndex || l.signal_group < 0)
	{
		return traffic::PedSignal::Off;
	}
	const uint32_t plan = signals_.planForNode(l.node);
	if (plan == routing::kInvalidIndex)
	{
		return traffic::PedSignal::Off;
	}
	return signals_.pedState(plan, l.signal_group, t);
}

float RoadNetwork::timeToGreen(uint32_t junctionLane, double t) const
{
	if (!loaded_ || junctionLane >= graph_.laneCount())
	{
		return -1.f;
	}
	const routing::Lane& l = graph_.lane(junctionLane);
	if (l.is_junction == 0 || l.signal_group < 0 || l.node == routing::kInvalidIndex)
	{
		return -1.f;
	}
	const uint32_t plan = signals_.planForNode(l.node);
	if (plan == routing::kInvalidIndex)
	{
		return -1.f;
	}
	return signals_.timeToGreen(plan, l.signal_group, t);
}

const traffic::DensityCell& RoadNetwork::densityForLane(uint32_t lane, uint8_t hour, uint8_t dow) const
{
	static const traffic::DensityCell kZero;
	if (!loaded_ || lane >= graph_.laneCount())
	{
		return kZero;
	}
	const uint16_t nta = graph_.lane(lane).nta;
	if (nta == routing::kNoNta || nta >= density_.ntaCount())
	{
		return kZero;
	}
	return density_.get(nta, hour, dow);
}

}  // namespace nycsim_gameplay
