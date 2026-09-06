// NYCB container reader/writer (DATA_CONTRACTS §15).
//   header {magic "NYCB", u32 version=1, u32 section_count, u64 index_offset}
//   index  = section_count x {char name[16]; u64 offset; u64 size; u32 element_size; u32 element_count}
//   strings live in the "strtab" section: NUL-separated blob addressed by u32 byte offsets.
// The reader is buffered (whole file in memory) or wraps caller-owned memory (e.g. an Unreal
// bulk-data buffer); no std::filesystem, no exceptions. Every offset is validated before use.
#pragma once

#include <cstddef>
#include <cstdint>
#include <string_view>
#include <vector>

#include "nycsim/Config.h"
#include "nycsim/io/NycbRecords.h"
#include "nycsim/util/Result.h"
#include "nycsim/util/Span.h"

namespace nycsim {
namespace io {

inline constexpr uint32_t kNycbVersion = 1;
inline constexpr size_t kNycbMaxSections = 4096;
inline constexpr std::string_view kNycbStrtab = "strtab";

struct NycbSection {
  char name[17];  ///< NUL-terminated copy of the index name
  uint64_t offset;
  uint64_t size;
  uint32_t elementSize;
  uint32_t elementCount;
  std::string_view nameView() const { return std::string_view(name); }
};

class NYCSIM_API NycbReader {
 public:
  NycbReader() = default;
  NycbReader(NycbReader&& o) noexcept;
  NycbReader& operator=(NycbReader&& o) noexcept;
  NycbReader(const NycbReader&) = delete;
  NycbReader& operator=(const NycbReader&) = delete;

  /// Wraps caller-owned memory which must outlive the reader.
  static Result<NycbReader> fromMemory(ByteSpan bytes);
  /// Takes ownership of the buffer.
  static Result<NycbReader> fromBuffer(std::vector<uint8_t>&& bytes);
  /// Reads the whole file into memory (C stdio; path in the platform's native encoding).
  static Result<NycbReader> fromFile(const char* path);

  uint32_t version() const { return version_; }
  size_t sizeBytes() const { return data_.size(); }
  Span<const NycbSection> sections() const {
    return Span<const NycbSection>(sections_.data(), sections_.size());
  }
  const NycbSection* find(std::string_view name) const;
  bool has(std::string_view name) const { return find(name) != nullptr; }

  /// Raw bytes of a section (empty span if absent).
  ByteSpan bytes(std::string_view name) const;

  /// Zero-copy typed view; fails if the section is absent or its element_size != sizeof(T).
  /// T must be one of the packed record types (alignment 1) or a byte type.
  template <class T>
  Result<Span<const T>> view(std::string_view name) const {
    static_assert(alignof(T) == 1, "NYCB typed views require packed (alignment-1) record types");
    const NycbSection* s = find(name);
    if (!s) return fail(ErrorCode::NotFound, "NYCB: section not found");
    if (s->elementSize != sizeof(T)) {
      return fail(ErrorCode::FormatError, "NYCB: section element_size does not match the record type",
                  static_cast<int64_t>(s->elementSize));
    }
    return Span<const T>(reinterpret_cast<const T*>(data_.data() + s->offset), s->elementCount);
  }

  bool hasStrtab() const { return strtab_ >= 0; }
  /// String at a strtab byte offset (up to the next NUL). Fails if absent or out of range.
  Result<std::string_view> string(uint32_t offset) const;

 private:
  Result<void> parse();

  std::vector<uint8_t> owned_;
  ByteSpan data_;
  std::vector<NycbSection> sections_;
  uint32_t version_ = 0;
  int strtab_ = -1;
};

/// Builds NYCB files (tests, tools). Sections are 16-byte aligned; the string table is emitted as
/// section "strtab" when any string was added (offset 0 is always the empty string).
class NYCSIM_API NycbWriter {
 public:
  NycbWriter();

  /// Adds a raw section. Name: 1..16 bytes, unique; size must equal elementSize*elementCount when
  /// elementSize > 0.
  Result<void> addSection(std::string_view name, ByteSpan data, uint32_t elementSize,
                          uint32_t elementCount);
  template <class T>
  Result<void> addRecords(std::string_view name, Span<const T> records) {
    return addSection(name, ByteSpan(reinterpret_cast<const uint8_t*>(records.data()), records.sizeBytes()),
                      static_cast<uint32_t>(sizeof(T)), static_cast<uint32_t>(records.size()));
  }
  /// Interns a string; returns its strtab offset (deduplicated). Empty string -> 0.
  uint32_t addString(std::string_view s);
  /// Serialises the container. Fails if a section named "strtab" was added manually while strings
  /// were also interned, or if the file would exceed 4 GiB of index-able content.
  Result<std::vector<uint8_t>> finish() const;
  Result<void> writeFile(const char* path) const;

 private:
  struct Pending {
    char name[17];
    std::vector<uint8_t> data;
    uint32_t elementSize;
    uint32_t elementCount;
  };
  std::vector<Pending> sections_;
  std::vector<uint8_t> strtab_;
};

/// True on little-endian hosts (NYCB is little-endian; big-endian hosts are rejected by the reader).
NYCSIM_API bool hostIsLittleEndian();

}  // namespace io
}  // namespace nycsim
