#include "nycsim/util/Arena.h"

#include <cstdlib>
#include <cstring>

namespace nycsim {

namespace {
constexpr size_t kHeaderBytes = ((sizeof(void*) * 3 + alignof(std::max_align_t) - 1) /
                                 alignof(std::max_align_t)) * alignof(std::max_align_t);
inline uintptr_t alignUp(uintptr_t v, size_t align) { return (v + (align - 1)) & ~(uintptr_t)(align - 1); }
}  // namespace

Arena::Arena(size_t chunkBytes) : chunkBytes_(chunkBytes < 256 ? 256 : chunkBytes) {}

Arena::~Arena() { release(); }

Arena::Arena(Arena&& o) noexcept
    : head_(o.head_), current_(o.current_), chunkBytes_(o.chunkBytes_), used_(o.used_),
      reserved_(o.reserved_), chunkCount_(o.chunkCount_), allocations_(o.allocations_) {
  o.head_ = o.current_ = nullptr;
  o.used_ = o.reserved_ = o.chunkCount_ = o.allocations_ = 0;
}

Arena& Arena::operator=(Arena&& o) noexcept {
  if (this != &o) {
    release();
    head_ = o.head_;
    current_ = o.current_;
    chunkBytes_ = o.chunkBytes_;
    used_ = o.used_;
    reserved_ = o.reserved_;
    chunkCount_ = o.chunkCount_;
    allocations_ = o.allocations_;
    o.head_ = o.current_ = nullptr;
    o.used_ = o.reserved_ = o.chunkCount_ = o.allocations_ = 0;
  }
  return *this;
}

Arena::Chunk* Arena::newChunk(size_t minBytes) {
  size_t capacity = chunkBytes_;
  if (minBytes > capacity) capacity = minBytes;
  void* mem = std::malloc(kHeaderBytes + capacity);
  if (!mem) return nullptr;
  Chunk* c = static_cast<Chunk*>(mem);
  c->next = nullptr;
  c->capacity = capacity;
  c->offset = 0;
  reserved_ += capacity;
  ++chunkCount_;
  return c;
}

void* Arena::allocate(size_t bytes, size_t align) {
  if (align == 0 || (align & (align - 1)) != 0) return nullptr;  // not a power of two
  if (align > alignof(std::max_align_t)) {
    // Over-aligned requests: pad so the payload can be realigned manually.
    bytes += align;
  }
  const size_t need = bytes == 0 ? 1 : bytes;
  if (!current_) {
    head_ = current_ = newChunk(need + align);
    if (!current_) return nullptr;
  }
  for (;;) {
    uintptr_t base = reinterpret_cast<uintptr_t>(current_) + kHeaderBytes;
    uintptr_t start = alignUp(base + current_->offset, align);
    uintptr_t end = start + need;
    if (end <= base + current_->capacity) {
      used_ += static_cast<size_t>(end - (base + current_->offset));
      current_->offset = static_cast<size_t>(end - base);
      ++allocations_;
      return reinterpret_cast<void*>(start);
    }
    if (current_->next && current_->next->offset == 0) {
      current_ = current_->next;  // reuse a chunk kept after reset()
      if (current_->capacity >= need + align) continue;
    }
    Chunk* c = newChunk(need + align);
    if (!c) return nullptr;
    c->next = current_->next;
    current_->next = c;
    current_ = c;
  }
}

void Arena::reset() {
  if (!head_) return;
  // Keep the first chunk, free the rest.
  Chunk* c = head_->next;
  while (c) {
    Chunk* n = c->next;
    reserved_ -= c->capacity;
    --chunkCount_;
    std::free(c);
    c = n;
  }
  head_->next = nullptr;
  head_->offset = 0;
  current_ = head_;
  used_ = 0;
  allocations_ = 0;
}

void Arena::release() {
  Chunk* c = head_;
  while (c) {
    Chunk* n = c->next;
    std::free(c);
    c = n;
  }
  head_ = current_ = nullptr;
  used_ = reserved_ = chunkCount_ = allocations_ = 0;
}

}  // namespace nycsim
