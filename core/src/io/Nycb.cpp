#include "nycsim/io/Nycb.h"

#include <algorithm>
#include <cstdio>
#include <cstring>

namespace nycsim {
namespace io {

bool hostIsLittleEndian() {
  const uint32_t probe = 0x01020304u;
  uint8_t b[4];
  std::memcpy(b, &probe, 4);
  return b[0] == 0x04;
}

namespace {

constexpr uint64_t kAlign = 16;

uint64_t alignUp(uint64_t v, uint64_t a) { return (v + a - 1) / a * a; }

void copyName(const char* src, size_t n, char* dst17) {
  size_t len = 0;
  while (len < n && len < 16 && src[len] != '\0') ++len;
  std::memcpy(dst17, src, len);
  dst17[len] = '\0';
}

}  // namespace

// ---- reader --------------------------------------------------------------------------------------

NycbReader::NycbReader(NycbReader&& o) noexcept
    : owned_(std::move(o.owned_)), data_(o.data_), sections_(std::move(o.sections_)),
      version_(o.version_), strtab_(o.strtab_) {
  if (!owned_.empty()) data_ = ByteSpan(owned_.data(), owned_.size());
  o.data_ = ByteSpan();
  o.strtab_ = -1;
}

NycbReader& NycbReader::operator=(NycbReader&& o) noexcept {
  if (this != &o) {
    owned_ = std::move(o.owned_);
    data_ = o.data_;
    sections_ = std::move(o.sections_);
    version_ = o.version_;
    strtab_ = o.strtab_;
    if (!owned_.empty()) data_ = ByteSpan(owned_.data(), owned_.size());
    o.data_ = ByteSpan();
    o.strtab_ = -1;
  }
  return *this;
}

Result<NycbReader> NycbReader::fromMemory(ByteSpan bytes) {
  NycbReader r;
  r.data_ = bytes;
  NYCSIM_TRY_VOID(r.parse());
  return r;
}

Result<NycbReader> NycbReader::fromBuffer(std::vector<uint8_t>&& bytes) {
  NycbReader r;
  r.owned_ = std::move(bytes);
  r.data_ = ByteSpan(r.owned_.data(), r.owned_.size());
  NYCSIM_TRY_VOID(r.parse());
  return r;
}

Result<NycbReader> NycbReader::fromFile(const char* path) {
  if (!path || !*path) return fail(ErrorCode::InvalidArgument, "NYCB: empty path");
  std::FILE* f = std::fopen(path, "rb");
  if (!f) return fail(ErrorCode::IoError, "NYCB: cannot open file");
  std::vector<uint8_t> buf;
  uint8_t chunk[1 << 16];
  for (;;) {
    const size_t n = std::fread(chunk, 1, sizeof chunk, f);
    if (n > 0) buf.insert(buf.end(), chunk, chunk + n);
    if (n < sizeof chunk) {
      if (std::ferror(f)) {
        std::fclose(f);
        return fail(ErrorCode::IoError, "NYCB: read error");
      }
      break;
    }
  }
  std::fclose(f);
  return fromBuffer(std::move(buf));
}

Result<void> NycbReader::parse() {
  if (!hostIsLittleEndian()) return fail(ErrorCode::Unsupported, "NYCB: big-endian host not supported");
  const size_t size = data_.size();
  if (size < sizeof(NycbHeader)) return fail(ErrorCode::Truncated, "NYCB: file shorter than the header", static_cast<int64_t>(size));
  NycbHeader h;
  std::memcpy(&h, data_.data(), sizeof h);
  if (std::memcmp(h.magic, "NYCB", 4) != 0) return fail(ErrorCode::BadMagic, "NYCB: bad magic");
  if (h.version != kNycbVersion) return fail(ErrorCode::UnsupportedVersion, "NYCB: unsupported version", h.version);
  if (h.sectionCount > kNycbMaxSections) return fail(ErrorCode::FormatError, "NYCB: implausible section count", h.sectionCount);
  const uint64_t indexBytes = static_cast<uint64_t>(h.sectionCount) * sizeof(NycbIndexEntry);
  if (h.indexOffset < sizeof(NycbHeader) || h.indexOffset > size || indexBytes > size - h.indexOffset) {
    return fail(ErrorCode::Truncated, "NYCB: index outside the file", static_cast<int64_t>(h.indexOffset));
  }
  version_ = h.version;
  sections_.clear();
  sections_.reserve(h.sectionCount);
  for (uint32_t i = 0; i < h.sectionCount; ++i) {
    NycbIndexEntry e;
    std::memcpy(&e, data_.data() + h.indexOffset + static_cast<size_t>(i) * sizeof e, sizeof e);
    NycbSection s;
    copyName(e.name, 16, s.name);
    if (s.name[0] == '\0') return fail(ErrorCode::FormatError, "NYCB: empty section name", i);
    s.offset = e.offset;
    s.size = e.size;
    s.elementSize = e.elementSize;
    s.elementCount = e.elementCount;
    if (s.offset < sizeof(NycbHeader) || s.offset > size || s.size > size - s.offset) {
      return fail(ErrorCode::Truncated, "NYCB: section outside the file", i);
    }
    // Sections must not overlap the index.
    const uint64_t sEnd = s.offset + s.size;
    const uint64_t iEnd = h.indexOffset + indexBytes;
    if (s.size > 0 && indexBytes > 0 && s.offset < iEnd && h.indexOffset < sEnd) {
      return fail(ErrorCode::FormatError, "NYCB: section overlaps the index", i);
    }
    if (s.elementSize > 0) {
      if (static_cast<uint64_t>(s.elementSize) * s.elementCount != s.size) {
        return fail(ErrorCode::FormatError, "NYCB: element_size * element_count != size", i);
      }
    } else if (s.elementCount != 0) {
      return fail(ErrorCode::FormatError, "NYCB: element_count without element_size", i);
    }
    for (const NycbSection& prev : sections_) {
      if (std::strcmp(prev.name, s.name) == 0) return fail(ErrorCode::FormatError, "NYCB: duplicate section name", i);
    }
    sections_.push_back(s);
  }
  strtab_ = -1;
  for (size_t i = 0; i < sections_.size(); ++i) {
    if (sections_[i].nameView() == kNycbStrtab) {
      const NycbSection& s = sections_[i];
      if (s.size > 0 && data_[static_cast<size_t>(s.offset + s.size - 1)] != 0) {
        return fail(ErrorCode::FormatError, "NYCB: strtab is not NUL-terminated");
      }
      strtab_ = static_cast<int>(i);
    }
  }
  return okResult();
}

const NycbSection* NycbReader::find(std::string_view name) const {
  for (const NycbSection& s : sections_) {
    if (s.nameView() == name) return &s;
  }
  return nullptr;
}

ByteSpan NycbReader::bytes(std::string_view name) const {
  const NycbSection* s = find(name);
  if (!s) return ByteSpan();
  return ByteSpan(data_.data() + s->offset, static_cast<size_t>(s->size));
}

Result<std::string_view> NycbReader::string(uint32_t offset) const {
  if (strtab_ < 0) return fail(ErrorCode::NotFound, "NYCB: no strtab section");
  const NycbSection& s = sections_[static_cast<size_t>(strtab_)];
  if (offset >= s.size) return fail(ErrorCode::OutOfRange, "NYCB: string offset beyond strtab", offset);
  const char* base = reinterpret_cast<const char*>(data_.data() + s.offset);
  const size_t avail = static_cast<size_t>(s.size - offset);
  const void* nul = std::memchr(base + offset, 0, avail);
  if (!nul) return fail(ErrorCode::FormatError, "NYCB: unterminated string", offset);
  return std::string_view(base + offset, static_cast<size_t>(static_cast<const char*>(nul) - (base + offset)));
}

// ---- writer --------------------------------------------------------------------------------------

NycbWriter::NycbWriter() { strtab_.push_back(0); }  // offset 0 == ""

Result<void> NycbWriter::addSection(std::string_view name, ByteSpan data, uint32_t elementSize,
                                    uint32_t elementCount) {
  if (name.empty() || name.size() > 16) return fail(ErrorCode::InvalidArgument, "NYCB: section name must be 1..16 bytes");
  if (name.find('\0') != std::string_view::npos) return fail(ErrorCode::InvalidArgument, "NYCB: section name contains NUL");
  if (elementSize > 0 && static_cast<uint64_t>(elementSize) * elementCount != data.size()) {
    return fail(ErrorCode::InvalidArgument, "NYCB: data size != element_size * element_count");
  }
  if (elementSize == 0 && elementCount != 0) return fail(ErrorCode::InvalidArgument, "NYCB: element_count without element_size");
  if (sections_.size() >= kNycbMaxSections) return fail(ErrorCode::OutOfRange, "NYCB: too many sections");
  for (const Pending& p : sections_) {
    if (std::string_view(p.name) == name) return fail(ErrorCode::InvalidArgument, "NYCB: duplicate section name");
  }
  Pending p;
  copyName(name.data(), name.size(), p.name);
  p.data.assign(data.begin(), data.end());
  p.elementSize = elementSize;
  p.elementCount = elementCount;
  sections_.push_back(std::move(p));
  return okResult();
}

uint32_t NycbWriter::addString(std::string_view s) {
  if (s.empty()) return 0;
  // Deduplicate by scanning existing entries (string tables here are small: names, addresses).
  size_t pos = 1;
  while (pos < strtab_.size()) {
    const char* cur = reinterpret_cast<const char*>(strtab_.data() + pos);
    const size_t len = std::strlen(cur);
    if (len == s.size() && std::memcmp(cur, s.data(), len) == 0) return static_cast<uint32_t>(pos);
    pos += len + 1;
  }
  const size_t off = strtab_.size();
  strtab_.insert(strtab_.end(), s.begin(), s.end());
  strtab_.push_back(0);
  return static_cast<uint32_t>(off);
}

Result<std::vector<uint8_t>> NycbWriter::finish() const {
  const bool haveStrings = strtab_.size() > 1;
  bool manualStrtab = false;
  for (const Pending& p : sections_) manualStrtab = manualStrtab || std::string_view(p.name) == kNycbStrtab;
  if (haveStrings && manualStrtab) return fail(ErrorCode::StateError, "NYCB: both interned strings and a manual strtab section");
  const size_t count = sections_.size() + (haveStrings ? 1 : 0);
  if (count > kNycbMaxSections) return fail(ErrorCode::OutOfRange, "NYCB: too many sections");

  std::vector<uint8_t> out;
  out.resize(alignUp(sizeof(NycbHeader), kAlign), 0);
  std::vector<NycbIndexEntry> index;
  index.reserve(count);
  auto emit = [&](const char* name, const std::vector<uint8_t>& data, uint32_t es, uint32_t ec) {
    NycbIndexEntry e;
    std::memset(&e, 0, sizeof e);
    std::memcpy(e.name, name, std::strlen(name));
    e.offset = out.size();
    e.size = data.size();
    e.elementSize = es;
    e.elementCount = ec;
    out.insert(out.end(), data.begin(), data.end());
    out.resize(alignUp(out.size(), kAlign), 0);
    index.push_back(e);
  };
  for (const Pending& p : sections_) emit(p.name, p.data, p.elementSize, p.elementCount);
  if (haveStrings) emit("strtab", strtab_, 1, static_cast<uint32_t>(strtab_.size()));
  if (haveStrings && strtab_.size() > 0xffffffffull) return fail(ErrorCode::OutOfRange, "NYCB: strtab exceeds 4 GiB");

  NycbHeader h;
  std::memcpy(h.magic, "NYCB", 4);
  h.version = kNycbVersion;
  h.sectionCount = static_cast<uint32_t>(count);
  h.indexOffset = out.size();
  for (const NycbIndexEntry& e : index) {
    const uint8_t* b = reinterpret_cast<const uint8_t*>(&e);
    out.insert(out.end(), b, b + sizeof e);
  }
  std::memcpy(out.data(), &h, sizeof h);
  return out;
}

Result<void> NycbWriter::writeFile(const char* path) const {
  if (!path || !*path) return fail(ErrorCode::InvalidArgument, "NYCB: empty path");
  NYCSIM_TRY(bytes, finish());
  std::FILE* f = std::fopen(path, "wb");
  if (!f) return fail(ErrorCode::IoError, "NYCB: cannot create file");
  const size_t n = std::fwrite(bytes.data(), 1, bytes.size(), f);
  const bool ok = n == bytes.size() && std::fclose(f) == 0;
  if (!ok) return fail(ErrorCode::IoError, "NYCB: write error");
  return okResult();
}

}  // namespace io
}  // namespace nycsim
