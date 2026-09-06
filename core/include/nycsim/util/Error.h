// Error codes shared by every nycsim_core module. Errors are trivially copyable, allocation free
// and carry a static message plus an integer detail (byte offset, index, code, ...).
#pragma once

#include <cstdint>

#include "nycsim/Config.h"

namespace nycsim {

enum class ErrorCode : uint16_t {
  None = 0,
  InvalidArgument,
  OutOfRange,
  ParseError,
  FormatError,
  BadMagic,
  UnsupportedVersion,
  Truncated,
  NotFound,
  IoError,
  Unsupported,
  NoConvergence,
  StateError,
  BudgetExceeded,
  Misaligned,
  Internal,
};

struct Error {
  ErrorCode code = ErrorCode::None;
  const char* message = "";  ///< static-storage string, never owned
  int64_t detail = 0;        ///< context: byte offset, index, HTTP status, ...

  constexpr Error() = default;
  constexpr Error(ErrorCode c, const char* m, int64_t d = 0) : code(c), message(m), detail(d) {}
  constexpr bool isNone() const { return code == ErrorCode::None; }
};

NYCSIM_API const char* errorCodeName(ErrorCode code);

}  // namespace nycsim
