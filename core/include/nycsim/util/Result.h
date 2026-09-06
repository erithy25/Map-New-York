// Result<T, E>: value-or-error without exceptions. Usable across the Unreal boundary.
//
//   Result<int> parse(...);           // returns either an int or an Error
//   auto r = parse(...);
//   if (!r) { log(r.error().message); return r.error(); }   // Error converts to any Result<U>
//   use(r.value());                   // value() on an error is a fatal precondition violation
//
// `fail(code, message, detail)` builds an Error that converts implicitly to any Result<T>.
#pragma once

#include <new>
#include <type_traits>
#include <utility>

#include "nycsim/Config.h"
#include "nycsim/util/Error.h"

namespace nycsim {

/// Wraps an error so that it converts to Result<T> for any T (including T == E).
template <class E>
struct Failure {
  E error;
};

inline constexpr Failure<Error> fail(ErrorCode code, const char* message, int64_t detail = 0) {
  return Failure<Error>{Error{code, message, detail}};
}

template <class E>
constexpr Failure<E> failWith(E e) {
  return Failure<E>{std::move(e)};
}

template <class T, class E = Error>
class Result {
  static_assert(!std::is_reference<T>::value, "Result<T&> is not supported");
  static_assert(!std::is_same<T, void>::value, "use the Result<void, E> specialisation");

 public:
  using value_type = T;
  using error_type = E;

  // Implicit from a value.
  Result(const T& v) : ok_(true) { new (&val_) T(v); }
  Result(T&& v) : ok_(true) { new (&val_) T(std::move(v)); }
  // Implicit from a wrapped error.
  Result(Failure<E> f) : ok_(false) { new (&err_) E(std::move(f.error)); }
  // Implicit from a bare error when T and E differ.
  template <class U = E, class = std::enable_if_t<!std::is_same<std::decay_t<U>, T>::value>>
  Result(const E& e) : ok_(false) {
    new (&err_) E(e);
  }

  Result(const Result& o) : ok_(o.ok_) {
    if (ok_) {
      new (&val_) T(o.val_);
    } else {
      new (&err_) E(o.err_);
    }
  }
  Result(Result&& o) noexcept(std::is_nothrow_move_constructible<T>::value &&
                              std::is_nothrow_move_constructible<E>::value)
      : ok_(o.ok_) {
    if (ok_) {
      new (&val_) T(std::move(o.val_));
    } else {
      new (&err_) E(std::move(o.err_));
    }
  }
  Result& operator=(const Result& o) {
    if (this != &o) {
      destroy();
      ok_ = o.ok_;
      if (ok_) {
        new (&val_) T(o.val_);
      } else {
        new (&err_) E(o.err_);
      }
    }
    return *this;
  }
  Result& operator=(Result&& o) noexcept(std::is_nothrow_move_constructible<T>::value &&
                                         std::is_nothrow_move_constructible<E>::value) {
    if (this != &o) {
      destroy();
      ok_ = o.ok_;
      if (ok_) {
        new (&val_) T(std::move(o.val_));
      } else {
        new (&err_) E(std::move(o.err_));
      }
    }
    return *this;
  }
  ~Result() { destroy(); }

  bool ok() const { return ok_; }
  explicit operator bool() const { return ok_; }

  T& value() & {
    NYCSIM_CHECK(ok_, "Result::value() called on an error");
    return val_;
  }
  const T& value() const& {
    NYCSIM_CHECK(ok_, "Result::value() called on an error");
    return val_;
  }
  T&& value() && {
    NYCSIM_CHECK(ok_, "Result::value() called on an error");
    return std::move(val_);
  }
  T* operator->() { return &value(); }
  const T* operator->() const { return &value(); }
  T& operator*() & { return value(); }
  const T& operator*() const& { return value(); }

  const E& error() const {
    NYCSIM_CHECK(!ok_, "Result::error() called on a success");
    return err_;
  }

  template <class U>
  T valueOr(U&& fallback) const& {
    return ok_ ? val_ : static_cast<T>(std::forward<U>(fallback));
  }
  template <class U>
  T valueOr(U&& fallback) && {
    return ok_ ? std::move(val_) : static_cast<T>(std::forward<U>(fallback));
  }

  /// Pointer to the value or nullptr on error (no precondition).
  T* ptr() { return ok_ ? &val_ : nullptr; }
  const T* ptr() const { return ok_ ? &val_ : nullptr; }

 private:
  void destroy() {
    if (ok_) {
      val_.~T();
    } else {
      err_.~E();
    }
  }
  union {
    T val_;
    E err_;
  };
  bool ok_;
};

template <class E>
class Result<void, E> {
 public:
  using value_type = void;
  using error_type = E;

  Result() : ok_(true), err_() {}
  Result(Failure<E> f) : ok_(false), err_(std::move(f.error)) {}
  Result(const E& e) : ok_(false), err_(e) {}

  bool ok() const { return ok_; }
  explicit operator bool() const { return ok_; }
  const E& error() const {
    NYCSIM_CHECK(!ok_, "Result::error() called on a success");
    return err_;
  }

 private:
  bool ok_;
  E err_;
};

/// Convenience: a successful Result<void>.
inline Result<void> okResult() { return Result<void>(); }

}  // namespace nycsim

/// Propagate an error from a Result expression inside a function returning a Result.
#define NYCSIM_TRY(var, expr)                    \
  auto var##_result_ = (expr);                   \
  if (!var##_result_) return var##_result_.error(); \
  auto& var = var##_result_.value()

#define NYCSIM_TRY_VOID(expr)               \
  do {                                      \
    auto r_ = (expr);                       \
    if (!r_) return r_.error();             \
  } while (0)
