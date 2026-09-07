// Minimal non-owning contiguous view (C++17; std::span is C++20).
#pragma once

#include <cstddef>
#include <cstdint>
#include <type_traits>

#include "nycsim/Config.h"

namespace nycsim {

template <class T>
class Span {
 public:
  using element_type = T;
  using value_type = std::remove_cv_t<T>;
  using size_type = size_t;
  using iterator = T*;

  constexpr Span() noexcept : data_(nullptr), size_(0) {}
  constexpr Span(T* data, size_t size) noexcept : data_(data), size_(size) {}
  template <size_t N>
  constexpr Span(T (&arr)[N]) noexcept : data_(arr), size_(N) {}
  template <class Container,
            class = std::enable_if_t<
                !std::is_array<Container>::value &&
                std::is_convertible<decltype(std::declval<Container&>().data()), T*>::value>>
  constexpr Span(Container& c) noexcept : data_(c.data()), size_(c.size()) {}
  template <class U, class = std::enable_if_t<std::is_convertible<U*, T*>::value>>
  constexpr Span(const Span<U>& o) noexcept : data_(o.data()), size_(o.size()) {}

  constexpr T* data() const noexcept { return data_; }
  constexpr size_t size() const noexcept { return size_; }
  constexpr size_t sizeBytes() const noexcept { return size_ * sizeof(T); }
  constexpr bool empty() const noexcept { return size_ == 0; }

  T& operator[](size_t i) const {
    NYCSIM_ASSERT(i < size_, "Span index out of range");
    return data_[i];
  }
  T& front() const { return (*this)[0]; }
  T& back() const { return (*this)[size_ - 1]; }

  constexpr iterator begin() const noexcept { return data_; }
  constexpr iterator end() const noexcept { return data_ + size_; }

  Span subspan(size_t offset, size_t count = static_cast<size_t>(-1)) const {
    NYCSIM_ASSERT(offset <= size_, "Span::subspan offset out of range");
    const size_t avail = size_ - offset;
    return Span(data_ + offset, count < avail ? count : avail);
  }
  Span first(size_t count) const { return subspan(0, count); }
  Span last(size_t count) const {
    NYCSIM_ASSERT(count <= size_, "Span::last count out of range");
    return subspan(size_ - count, count);
  }

 private:
  T* data_;
  size_t size_;
};

template <class T>
constexpr Span<T> makeSpan(T* data, size_t size) {
  return Span<T>(data, size);
}

using ByteSpan = Span<const uint8_t>;

}  // namespace nycsim
