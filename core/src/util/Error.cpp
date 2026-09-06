#include "nycsim/util/Error.h"

namespace nycsim {

const char* errorCodeName(ErrorCode code) {
  switch (code) {
    case ErrorCode::None: return "None";
    case ErrorCode::InvalidArgument: return "InvalidArgument";
    case ErrorCode::OutOfRange: return "OutOfRange";
    case ErrorCode::ParseError: return "ParseError";
    case ErrorCode::FormatError: return "FormatError";
    case ErrorCode::BadMagic: return "BadMagic";
    case ErrorCode::UnsupportedVersion: return "UnsupportedVersion";
    case ErrorCode::Truncated: return "Truncated";
    case ErrorCode::NotFound: return "NotFound";
    case ErrorCode::IoError: return "IoError";
    case ErrorCode::Unsupported: return "Unsupported";
    case ErrorCode::NoConvergence: return "NoConvergence";
    case ErrorCode::StateError: return "StateError";
    case ErrorCode::BudgetExceeded: return "BudgetExceeded";
    case ErrorCode::Misaligned: return "Misaligned";
    case ErrorCode::Internal: return "Internal";
  }
  return "Unknown";
}

}  // namespace nycsim
