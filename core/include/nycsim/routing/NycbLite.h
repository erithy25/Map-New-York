#pragma once
// nycsim/routing/NycbLite.h — minimal, dependency-free reader for the NYCB
// container (DATA_CONTRACTS §15).  Header: {char magic[4]="NYCB"; uint32
// version=1; uint32 section_count; uint64 index_offset}; index entries:
// {char name[16]; uint64 offset; uint64 size; uint32 element_size; uint32
// element_count}.  Little-endian, read byte-wise (no type punning, works on
// any host endianness).  Used by RoadGraph, SignalTable and DensityTable so
// the traffic lane does not depend on core/io.

#include <cstddef>
#include <cstdint>
#include <cstring>
#include <string_view>

namespace nycsim {
namespace nycb {

inline uint32_t rdU32(const uint8_t* p) {
  return static_cast<uint32_t>(p[0]) | (static_cast<uint32_t>(p[1]) << 8) | (static_cast<uint32_t>(p[2]) << 16) |
         (static_cast<uint32_t>(p[3]) << 24);
}
inline uint16_t rdU16(const uint8_t* p) { return static_cast<uint16_t>(p[0] | (p[1] << 8)); }
inline uint64_t rdU64(const uint8_t* p) { return static_cast<uint64_t>(rdU32(p)) | (static_cast<uint64_t>(rdU32(p + 4)) << 32); }
inline int64_t rdI64(const uint8_t* p) { return static_cast<int64_t>(rdU64(p)); }
inline int32_t rdI32(const uint8_t* p) { return static_cast<int32_t>(rdU32(p)); }
inline int8_t rdI8(const uint8_t* p) { return static_cast<int8_t>(p[0]); }
inline float rdF32(const uint8_t* p) {
  const uint32_t u = rdU32(p);
  float f;
  std::memcpy(&f, &u, 4);
  return f;
}

struct Section {
  const uint8_t* data = nullptr;
  uint64_t size = 0;
  uint32_t element_size = 0;
  uint32_t element_count = 0;
  bool present = false;
  const uint8_t* at(uint32_t i) const { return data + static_cast<size_t>(i) * element_size; }
};

struct File {
  const uint8_t* base = nullptr;
  size_t len = 0;
  uint32_t section_count = 0;
  uint64_t index_offset = 0;
  const char* error = nullptr;

  // Parses the header and validates the index; false + error on failure.
  bool open(const uint8_t* data, size_t n) {
    base = data;
    len = n;
    error = nullptr;
    if (data == nullptr || n < 24) return failWith("nycb: buffer too small for header");
    if (std::memcmp(data, "NYCB", 4) != 0) return failWith("nycb: bad magic");
    if (rdU32(data + 4) != 1) return failWith("nycb: unsupported version");
    section_count = rdU32(data + 8);
    index_offset = rdU64(data + 12);
    if (section_count > 64) return failWith("nycb: implausible section count");
    const uint64_t index_size = static_cast<uint64_t>(section_count) * 40u;
    if (index_offset > n || index_size > n - index_offset) return failWith("nycb: section index out of bounds");
    for (uint32_t i = 0; i < section_count; ++i) {
      const uint8_t* e = data + index_offset + static_cast<size_t>(i) * 40u;
      const uint64_t off = rdU64(e + 16), size = rdU64(e + 24);
      const uint32_t es = rdU32(e + 32), ec = rdU32(e + 36);
      if (off > n || size > n - off) return failWith("nycb: section out of bounds");
      if (static_cast<uint64_t>(es) * ec > size) return failWith("nycb: section element extent exceeds size");
    }
    return true;
  }

  Section section(const char* name) const {
    Section s;
    for (uint32_t i = 0; i < section_count; ++i) {
      const uint8_t* e = base + index_offset + static_cast<size_t>(i) * 40u;
      char nm[17];
      std::memcpy(nm, e, 16);
      nm[16] = '\0';
      if (std::strcmp(nm, name) != 0) continue;
      s.data = base + rdU64(e + 16);
      s.size = rdU64(e + 24);
      s.element_size = rdU32(e + 32);
      s.element_count = rdU32(e + 36);
      s.present = true;
      return s;
    }
    return s;
  }

  // NUL-terminated string at `off` inside the strtab section (empty if out of range).
  static std::string_view str(const Section& strtab, uint32_t off) {
    if (!strtab.present || off >= strtab.size) return std::string_view();
    const char* p = reinterpret_cast<const char*>(strtab.data) + off;
    size_t k = 0;
    while (off + k < strtab.size && p[k] != '\0') ++k;
    return std::string_view(p, k);
  }

 private:
  bool failWith(const char* msg) {
    error = msg;
    return false;
  }
};

}  // namespace nycb
}  // namespace nycsim
