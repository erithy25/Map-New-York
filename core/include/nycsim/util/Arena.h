// Bump (arena) allocator for per-frame / per-tick scratch memory. No per-allocation free; reset()
// releases everything at once. Only trivially destructible objects may be created in it.
#pragma once

#include <cstddef>
#include <cstdint>
#include <new>
#include <type_traits>
#include <utility>

#include "nycsim/Config.h"
#include "nycsim/util/Span.h"

namespace nycsim {

class NYCSIM_API Arena {
 public:
  static constexpr size_t kDefaultChunkBytes = 64 * 1024;

  explicit Arena(size_t chunkBytes = kDefaultChunkBytes);
  ~Arena();
  Arena(const Arena&) = delete;
  Arena& operator=(const Arena&) = delete;
  Arena(Arena&& o) noexcept;
  Arena& operator=(Arena&& o) noexcept;

  /// Returns `bytes` of storage aligned to `align` (power of two), or nullptr if the system
  /// allocator fails. Zero-byte requests return a valid non-null pointer.
  void* allocate(size_t bytes, size_t align = alignof(std::max_align_t));

  /// Constructs a trivially destructible T in the arena; nullptr on allocation failure.
  template <class T, class... Args>
  T* create(Args&&... args) {
    static_assert(std::is_trivially_destructible<T>::value,
                  "Arena only stores trivially destructible types (no destructor is ever run)");
    void* p = allocate(sizeof(T), alignof(T));
    if (!p) return nullptr;
    return new (p) T(std::forward<Args>(args)...);
  }

  /// Allocates an uninitialised array of n trivially destructible T (value-initialised).
  template <class T>
  Span<T> createArray(size_t n) {
    static_assert(std::is_trivially_destructible<T>::value,
                  "Arena only stores trivially destructible types (no destructor is ever run)");
    if (n == 0) return Span<T>();
    if (n > (static_cast<size_t>(-1) / sizeof(T))) return Span<T>();
    void* p = allocate(n * sizeof(T), alignof(T));
    if (!p) return Span<T>();
    T* arr = static_cast<T*>(p);
    for (size_t i = 0; i < n; ++i) new (arr + i) T();
    return Span<T>(arr, n);
  }

  /// Rewinds every chunk; the first chunk is kept, later chunks are released.
  void reset();
  /// Frees all memory.
  void release();

  size_t bytesUsed() const { return used_; }
  size_t bytesReserved() const { return reserved_; }
  size_t chunkCount() const { return chunkCount_; }
  size_t allocationCount() const { return allocations_; }

 private:
  struct Chunk {
    Chunk* next;
    size_t capacity;
    size_t offset;
    // payload follows
  };
  Chunk* newChunk(size_t minBytes);

  Chunk* head_ = nullptr;
  Chunk* current_ = nullptr;
  size_t chunkBytes_;
  size_t used_ = 0;
  size_t reserved_ = 0;
  size_t chunkCount_ = 0;
  size_t allocations_ = 0;
};

}  // namespace nycsim
