// nycsim/traffic/Density.cpp — see Density.h.
#include "nycsim/traffic/Density.h"

#include <algorithm>

#include "nycsim/routing/NycbLite.h"

namespace nycsim {
namespace traffic {

void DensityTable::clear() {
  codes_.clear();
  cells_.clear();
  present_.clear();
  polys_.clear();
  poly_pts_.clear();
  error_.clear();
}

uint16_t DensityTable::addNta(std::string_view code) {
  const uint16_t existing = ntaIndex(code);
  if (existing != routing::kNoNta) return existing;
  codes_.emplace_back(code);
  cells_.resize(codes_.size() * kHours * kDows);
  present_.resize(codes_.size() * kHours * kDows, 0);
  return static_cast<uint16_t>(codes_.size() - 1);
}

uint16_t DensityTable::ntaIndex(std::string_view code) const {
  for (size_t i = 0; i < codes_.size(); ++i)
    if (codes_[i] == code) return static_cast<uint16_t>(i);
  return routing::kNoNta;
}

void DensityTable::set(uint16_t nta, uint8_t hour, uint8_t dow, const DensityCell& c) {
  if (nta >= codes_.size()) return;
  const size_t s = slot(nta, hour, dow);
  cells_[s] = c;
  present_[s] = 1;
}

void DensityTable::fill(uint16_t nta, const DensityCell& c) {
  for (uint8_t d = 0; d < kDows; ++d)
    for (uint8_t h = 0; h < kHours; ++h) set(nta, h, d, c);
}

bool DensityTable::has(uint16_t nta, uint8_t hour, uint8_t dow) const {
  return nta < codes_.size() && present_[slot(nta, hour, dow)] != 0;
}

const DensityCell& DensityTable::get(uint16_t nta, uint8_t hour, uint8_t dow) const {
  if (nta >= codes_.size()) return zero_;
  size_t s = slot(nta, hour, dow);
  if (present_[s]) return cells_[s];
  s = slot(nta, hour, 0);
  if (present_[s]) return cells_[s];
  return zero_;
}

void DensityTable::addPolygon(uint16_t nta, const routing::Vec3* pts, size_t n) {
  if (n < 3) return;
  Poly p;
  p.nta = nta;
  p.first = static_cast<uint32_t>(poly_pts_.size());
  p.count = static_cast<uint32_t>(n);
  p.minx = p.miny = 1e30f;
  p.maxx = p.maxy = -1e30f;
  for (size_t i = 0; i < n; ++i) {
    poly_pts_.push_back(pts[i]);
    p.minx = std::min(p.minx, pts[i].x);
    p.maxx = std::max(p.maxx, pts[i].x);
    p.miny = std::min(p.miny, pts[i].y);
    p.maxy = std::max(p.maxy, pts[i].y);
  }
  polys_.push_back(p);
}

bool DensityTable::pointInNta(float x, float y, uint16_t& nta) const {
  for (const Poly& p : polys_) {
    if (x < p.minx || x > p.maxx || y < p.miny || y > p.maxy) continue;
    // even-odd rule
    bool inside = false;
    const routing::Vec3* v = poly_pts_.data() + p.first;
    for (uint32_t i = 0, j = p.count - 1; i < p.count; j = i++) {
      if (((v[i].y > y) != (v[j].y > y)) && (x < (v[j].x - v[i].x) * (y - v[i].y) / (v[j].y - v[i].y) + v[i].x)) inside = !inside;
    }
    if (inside) {
      nta = p.nta;
      return true;
    }
  }
  return false;
}

uint32_t DensityTable::assignLaneNtas(routing::RoadGraph& g) const {
  uint32_t assigned = 0;
  for (uint32_t li = 0; li < g.laneCount(); ++li) {
    const routing::Vec3 mid = g.pointAt(li, 0.5f * g.lane(li).length_m);
    uint16_t nta;
    if (pointInNta(mid.x, mid.y, nta)) {
      g.setLaneNta(li, nta);
      ++assigned;
    }
  }
  return assigned;
}

bool DensityTable::loadFromNycb(const uint8_t* data, size_t len) {
  clear();
  nycb::File f;
  if (!f.open(data, len)) {
    error_ = f.error;
    return false;
  }
  const nycb::Section cells = f.section("cells");
  const nycb::Section polys = f.section("nta_polys");
  const nycb::Section verts = f.section("vertices");
  const nycb::Section strtab = f.section("strtab");
  if (!cells.present || !strtab.present) {
    error_ = "density.nycb: missing cells/strtab section";
    return false;
  }
  if (cells.element_size != 32) {
    error_ = "density.nycb: cells element_size != 32";
    return false;
  }
  for (uint32_t i = 0; i < cells.element_count; ++i) {
    const uint8_t* p = cells.at(i);
    const uint16_t nta = addNta(nycb::File::str(strtab, nycb::rdU32(p)));
    DensityCell c;
    c.veh_per_km_lane = nycb::rdF32(p + 8);
    c.ped_per_m2 = nycb::rdF32(p + 12);
    c.taxi_share = nycb::rdF32(p + 16);
    c.truck_share = nycb::rdF32(p + 20);
    c.bus_share = nycb::rdF32(p + 24);
    c.bike_share = nycb::rdF32(p + 28);
    set(nta, p[4], p[5], c);
  }
  if (polys.present) {
    if (polys.element_size != 12 || !verts.present || verts.element_size != 12) {
      error_ = "density.nycb: nta_polys/vertices element sizes must be 12/12";
      return false;
    }
    std::vector<routing::Vec3> pts;
    for (uint32_t i = 0; i < polys.element_count; ++i) {
      const uint8_t* p = polys.at(i);
      const uint32_t fv = nycb::rdU32(p + 4), vc = nycb::rdU32(p + 8);
      if (static_cast<uint64_t>(fv) + vc > verts.element_count) {
        error_ = "density.nycb: polygon vertex range out of bounds";
        return false;
      }
      pts.clear();
      for (uint32_t k = 0; k < vc; ++k) {
        const uint8_t* q = verts.at(fv + k);
        pts.push_back({nycb::rdF32(q), nycb::rdF32(q + 4), nycb::rdF32(q + 8)});
      }
      addPolygon(addNta(nycb::File::str(strtab, nycb::rdU32(p))), pts.data(), pts.size());
    }
  }
  return true;
}

}  // namespace traffic
}  // namespace nycsim
