// nycsim_core configuration: export macro, version, fatal-error hook.
// Engine-agnostic. Safe to include from an Unreal module (no exceptions, no RTTI, no std::filesystem,
// no static initialisers with side effects).
#pragma once

#include <cstdint>

#ifndef NYCSIM_API
#define NYCSIM_API
#endif

#define NYCSIM_CORE_VERSION_MAJOR 1
#define NYCSIM_CORE_VERSION_MINOR 0
#define NYCSIM_CORE_VERSION_PATCH 0

#if defined(__GNUC__) || defined(__clang__)
#define NYCSIM_PRINTF_LIKE(fmtIndex, firstArg) __attribute__((format(printf, fmtIndex, firstArg)))
#else
#define NYCSIM_PRINTF_LIKE(fmtIndex, firstArg)
#endif

namespace nycsim {

/// Handler invoked on an unrecoverable precondition violation (e.g. Result::value() on an error).
/// The default handler writes to stderr and calls std::abort(). Unreal can route it to checkf().
/// The handler must not return.
using FatalHandler = void (*)(const char* message, const char* file, int line);

NYCSIM_API void setFatalHandler(FatalHandler handler);
NYCSIM_API FatalHandler fatalHandler();

/// Invokes the fatal handler; never returns.
[[noreturn]] NYCSIM_API void fatalError(const char* message, const char* file, int line);

}  // namespace nycsim

/// Precondition check that is always active (programmer errors, not data errors).
#define NYCSIM_CHECK(cond, message) \
  ((cond) ? static_cast<void>(0) : ::nycsim::fatalError((message), __FILE__, __LINE__))

/// Debug-only assertion (compiled out when NDEBUG is defined).
#if defined(NDEBUG)
#define NYCSIM_ASSERT(cond, message) static_cast<void>(0)
#else
#define NYCSIM_ASSERT(cond, message) NYCSIM_CHECK(cond, message)
#endif
